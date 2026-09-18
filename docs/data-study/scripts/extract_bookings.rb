#!/usr/bin/ruby
# extract_bookings.rb -- normalise the 23 year sheets of "Dock Schedule - Synthetic Sample.xlsx"
# into one bookings table and validate it.
#
#   ruby extract_bookings.rb <xlsx_dir> <tsv_dir> <out_dir>
#
# Inputs : <xlsx_dir>/xl/workbook.xml, xl/_rels/workbook.xml.rels, xl/worksheets/sheetN.xml (merges)
#          <tsv_dir>/<Year>.tsv, <Year>.styles.tsv, _styles.tsv, "8YR Dock Summary.tsv"
# Outputs: <out_dir>/bookings.csv, extract_report.md, unlabeled_cells.csv, summary_comparison.csv
# Ruby 2.6 stdlib only.
require 'csv'
require 'date'
require 'fileutils'
require 'set'

XLSX, TSV, OUT = ARGV
abort "usage: ruby extract_bookings.rb <xlsx_dir> <tsv_dir> <out_dir>" unless XLSX && TSV && OUT
FileUtils.mkdir_p(OUT)

MONTHS = %w[january february march april may june july august september october november december]
MONTH_RE = /\A\s*(#{MONTHS.join('|')})\b\s*(\d{4})?\s*\z/i
WEEKDAY_RE = /\A(M|T|W|TR|TH|F|S|SU|SA|MO|TU|WE|FR)\z/
NUMBER_RE = /\A-?\d+(\.\d+)?\z/
GROUP_RE = /\A(North Finger Piers|Small craft slips)/i
CANONICAL = ['North Pier West', 'North Pier Face', 'North Pier East', 'Inner Channel', 'South Float West', 'South Float East']
HEADER = %w[sheet_year block_label block_month block_year berth_label berth_name berth_length_ft group_label row_index
            start_col start_day end_day span_days span_source start_date end_date date_valid raw_value fill]

def col2num(c); n = 0; c.each_char { |ch| n = n * 26 + (ch.ord - 64) }; n; end
def num2col(i); s = ''; n = i; while n > 0; n -= 1; s = (65 + n % 26).chr + s; n /= 26; end; s; end
def unesc(s); s.to_s.gsub('&lt;', '<').gsub('&gt;', '>').gsub('&quot;', '"').gsub('&apos;', "'").gsub('&amp;', '&'); end

# ---------------------------------------------------------------- workbook / merges
wb = File.read("#{XLSX}/xl/workbook.xml")
rels = File.read("#{XLSX}/xl/_rels/workbook.xml.rels")
rid2file = {}
rels.scan(/<Relationship ([^>]*?)\/>/) { |a| a = a[0]; rid2file[a[/Id="([^"]+)"/, 1]] = a[/Target="([^"]+)"/, 1] }
sheet_files = {}
wb.scan(/<sheet ([^>]*?)\/>/) do |a|
  a = a[0]
  name = unesc(a[/name="([^"]+)"/, 1]); target = rid2file[a[/r:id="([^"]+)"/, 1]]
  sheet_files[name] = target.start_with?('/') ? "#{XLSX}#{target}" : "#{XLSX}/xl/#{target}"
end
year_sheets = sheet_files.keys.select { |n| n =~ /\A(19|20)\d\d\z/ }.sort

def read_merges(path)
  xml = File.read(path)
  xml.scan(/<mergeCell ref="([A-Z]+)(\d+):([A-Z]+)(\d+)"/).map do |c1, r1, c2, r2|
    { c1: col2num(c1), r1: r1.to_i, c2: col2num(c2), r2: r2.to_i, ref: "#{c1}#{r1}:#{c2}#{r2}" }
  end
end

# ---------------------------------------------------------------- styles
STYLE_FILL = {}
File.readlines("#{TSV}/_styles.tsv").drop(1).each do |l|
  f = l.chomp("\n").split("\t", -1)
  STYLE_FILL[f[0]] = f[4].to_s.strip
end
# default (non-informative) fills: none, plain white
def default_fill?(fill)
  return true if fill.nil? || fill.empty? || fill.start_with?('none')
  return true if fill =~ /fg=theme="0"\s*\|/          # theme 0 (white) without tint
  return true if fill =~ /fg=rgb="FFFFFFFF"/
  false
end
def fill_out(fill); default_fill?(fill) ? '' : fill; end

def read_tsv(path)
  File.readlines(path).map { |l| l.chomp("\n").split("\t", -1) }
end

def days_in_month(y, m)
  Date.new(y, m, -1).day
rescue ArgumentError
  31
end

# ---------------------------------------------------------------- per-block helpers
# Find the day-number row inside rows h..h+2: the row holding the longest run of consecutive
# integers / "=...+1" formulas. Returns [row_index0, day1_col0, first_day, last_day] or nil.
def find_day_row(rows, h)
  best = nil
  (h..[h + 2, rows.size - 1].min).each do |r|
    row = rows[r]
    c = 1
    while c < row.size
      v = row[c].to_s
      if v =~ /\A\d+\z/
        start = c; first = v.to_i; expect = first; last = first
        while c < row.size
          v2 = row[c].to_s
          if v2 =~ /\A\d+\z/ && v2.to_i == expect
            last = expect; expect += 1; c += 1
          elsif v2.start_with?('=') && v2 =~ /\+\s*1\)?\z/
            last = expect; expect += 1; c += 1
          else
            break
          end
        end
        len = last - first + 1
        if best.nil? || len > best[:len]
          best = { len: len, row: r, day1col: start - (first - 1), first: first, last: last }
        end
      else
        c += 1
      end
    end
  end
  return nil unless best && best[:len] >= 3
  [best[:row], best[:day1col], best[:first], best[:last]]
end

def parse_berth(label)
  if label =~ /\A(.*?)\s*-\s*(\d+(?:\.\d+)?)\s*'\s*\z/
    [$1.strip, $2]
  else
    [label.strip.sub(/:\s*\z/, ''), '']
  end
end

# ---------------------------------------------------------------- extraction
records = []
unlabeled = []
anomalies = Hash.new { |h, k| h[k] = [] }   # category -> list of strings
sheet_stats = {}
label_years = Hash.new { |h, k| h[k] = Set.new }

year_sheets.each do |sheet|
  sheet_year = sheet.to_i
  rows = read_tsv("#{TSV}/#{sheet}.tsv")
  styles = read_tsv("#{TSV}/#{sheet}.styles.tsv")
  merges = read_merges(sheet_files[sheet])
  merge_at = {}
  merges.each do |m|
    merge_at[[m[:r1], m[:c1]]] = m
    anomalies['multi_row_merge'] << "#{sheet}: merge #{m[:ref]} spans #{m[:r2] - m[:r1] + 1} rows" if m[:r2] != m[:r1]
  end
  cell = ->(r0, c0) { (rows[r0] || [])[c0].to_s }
  fill_of = ->(r0, c0) { STYLE_FILL[((styles[r0] || [])[c0]).to_s].to_s }

  hdr_idx = rows.each_index.select { |i| rows[i][0].to_s =~ MONTH_RE }
  st = { blocks: [], candidates: 0, records: 0, sources: Hash.new(0), outside: 0, numeric_skipped: 0,
         unlabeled_cells: 0, header_junk: 0, merge_clamped: 0, fill_clamped: 0, invalid_dates: 0 }
  sheet_stats[sheet_year] = st

  hdr_idx.each_with_index do |h, k|
    stop = hdr_idx[k + 1] || rows.size
    label = rows[h][0].to_s.strip
    m = label.match(MONTH_RE)
    block_month = MONTHS.index(m[1].downcase) + 1
    block_year = m[2] ? m[2].to_i : sheet_year
    cal_days = days_in_month(block_year, block_month)
    anomalies['block_year_differs_from_sheet'] << "#{sheet}: block '#{label}' (row #{h + 1}) labelled year #{block_year} on the #{sheet} sheet" if block_year != sheet_year

    dr = find_day_row(rows, h)
    if dr
      day_row, day1col, first_day, last_day = dr
      if first_day != 1
        anomalies['day_row_does_not_start_at_1'] << "#{sheet}: block '#{label}' day numbers run #{first_day}..#{last_day} (row #{day_row + 1}); day-1 column inferred as #{num2col(day1col + 1)}"
      end
    else
      era_c = m[2].nil?
      day_row = nil; day1col = era_c ? 2 : 1; first_day = 1; last_day = cal_days
      anomalies['no_day_row_found'] << "#{sheet}: block '#{label}' (row #{h + 1}) has no day-number row; assumed day 1 at column #{num2col(day1col + 1)}"
    end
    last_col = day1col + last_day - 1
    if last_day != cal_days
      anomalies['header_days_ne_calendar'] << "#{sheet}: block '#{label}' header lists #{last_day} days, calendar has #{cal_days}"
    end
    st[:blocks] << "#{label} [day1=#{num2col(day1col + 1)}, #{last_day}d]"

    # header / weekday rows: anything non-numeric, non-weekday there is junk
    header_rows = [h, h + 1, h + 2].select { |r| r < stop && r < rows.size && (r == h || r == day_row || (rows[r][0].to_s.empty? && rows[r][1..-1].to_a.count { |v| v =~ WEEKDAY_RE } >= 5)) }
    header_rows.each do |r|
      rows[r].each_with_index do |v, c|
        next if c == 0 || v.to_s.empty? || v =~ NUMBER_RE || v.start_with?('=') || v =~ WEEKDAY_RE
        st[:header_junk] += 1
        anomalies['values_in_header_or_weekday_row'] << "#{sheet}: row #{r + 1} col #{num2col(c + 1)} = '#{v}' (block '#{label}')"
      end
    end

    group_label = ''
    ((h + 1)...stop).each do |r|
      next if header_rows.include?(r)
      row = rows[r] || []
      a = row[0].to_s.strip
      if a.empty?
        # unlabeled row: collect any text cells as anomalies (not records)
        row.each_with_index do |v, c|
          next if c == 0 || v.to_s.strip.empty? || v =~ NUMBER_RE || v.start_with?('=') || v =~ WEEKDAY_RE
          st[:unlabeled_cells] += 1
          day = c - day1col + 1
          unlabeled << [sheet_year, label, r + 1, num2col(c + 1), day, v, fill_out(fill_of.call(r, c))]
        end
        next
      end
      berth_name, berth_len = parse_berth(a)
      label_years[a] << sheet_year
      is_group = a =~ GROUP_RE
      if is_group
        group_label = a if a =~ /\ANorth Finger Piers/i || group_label.empty?
      end
      this_group = is_group ? group_label : ''
      unless is_group || CANONICAL.include?(berth_name)
        anomalies['non_canonical_berth_label'] << "#{sheet}: row #{r + 1} label '#{a}'"
      end
      c = 1
      while c < row.size
        v = row[c].to_s
        if v.strip.empty? || v.start_with?('=')
          c += 1; next
        end
        if v =~ NUMBER_RE
          st[:numeric_skipped] += 1
          anomalies['bare_number_in_berth_row'] << "#{sheet}: row #{r + 1} col #{num2col(c + 1)} = #{v} (skipped)"
          c += 1; next
        end
        st[:candidates] += 1
        start_day = c - day1col + 1
        fill = fill_of.call(r, c)
        end_col = c
        source = 'single'
        consumed = 0
        if (mg = merge_at[[r + 1, c + 1]])
          source = 'merge'
          end_col = mg[:c2] - 1
          if end_col > last_col
            anomalies['merge_beyond_month'] << "#{sheet}: merge #{mg[:ref]} ('#{v}', block '#{label}') extends #{end_col - last_col} col(s) past the last day column #{num2col(last_col + 1)}; clamped"
            st[:merge_clamped] += 1
            end_col = [last_col, c].max   # never move the end left of the start cell
          end
        elsif !default_fill?(fill)
          e = c
          while e + 1 <= last_col && cell.call(r, e + 1).strip.empty? && fill_of.call(r, e + 1) == fill
            e += 1
          end
          if e > c
            source = 'fill_run'; end_col = e
            if e == last_col && e + 1 < (row.size) && cell.call(r, e + 1).strip.empty? && fill_of.call(r, e + 1) == fill
              st[:fill_clamped] += 1
            end
          end
        end
        if source == 'single'
          e = c
          while e + 1 < row.size && cell.call(r, e + 1) == v
            e += 1
          end
          if e > c
            source = 'repeat'; end_col = e; consumed = e - c
          end
        end
        end_day = end_col - day1col + 1
        span = end_day - start_day + 1
        # dates
        sd = (Date.new(block_year, block_month, start_day) rescue nil) if start_day >= 1
        ed = (Date.new(block_year, block_month, end_day) rescue nil) if end_day >= 1
        valid = !(sd.nil? || ed.nil?)
        if start_day < 1 || start_day > last_day
          st[:outside] += 1
          anomalies['cell_outside_day_columns'] << "#{sheet}: row #{r + 1} col #{num2col(c + 1)} '#{v}' -> day #{start_day} (block '#{label}' day columns #{num2col(day1col + 1)}..#{num2col(last_col + 1)})"
        end
        st[:invalid_dates] += 1 unless valid
        records << [sheet_year, label, block_month, block_year, a, berth_name, berth_len, this_group, r + 1,
                    num2col(c + 1), start_day, end_day, span, source,
                    sd ? sd.iso8601 : '', ed ? ed.iso8601 : '', valid, v, fill_out(fill)]
        st[:records] += 1
        st[:sources][source] += 1
        c = end_col + 1
      end
    end
  end
end

# duplicate labels within a block
records.group_by { |r| [r[0], r[1], r[4]] }.each do |(y, blk, lab), rs|
  rows_ = rs.map { |r| r[8] }.uniq
  anomalies['duplicate_berth_row_in_block'] << "#{y}: '#{lab}' appears on rows #{rows_.join(', ')} in block '#{blk}'" if rows_.size > 1
end
# labels also from rows with no records: re-scan quickly for duplicate labelled rows per block
year_sheets.each do |sheet|
  rows = read_tsv("#{TSV}/#{sheet}.tsv")
  hdr_idx = rows.each_index.select { |i| rows[i][0].to_s =~ MONTH_RE }
  hdr_idx.each_with_index do |h, k|
    stop = hdr_idx[k + 1] || rows.size
    seen = Hash.new { |hh, kk| hh[kk] = [] }
    ((h + 1)...stop).each { |r| a = rows[r][0].to_s.strip; seen[a] << r + 1 unless a.empty? }
    seen.each { |lab, rr| anomalies['duplicate_label_rows_in_block'] << "#{sheet}: '#{lab}' on rows #{rr.join(', ')} (block '#{rows[h][0]}')" if rr.size > 1 }
  end
end

# ---------------------------------------------------------------- write CSVs
CSV.open("#{OUT}/bookings.csv", 'w') do |csv|
  csv << HEADER
  records.each { |r| csv << r }
end
CSV.open("#{OUT}/unlabeled_cells.csv", 'w') do |csv|
  csv << %w[sheet_year block_label row_index col day_if_in_block raw_value fill]
  unlabeled.each { |r| csv << r }
end

# ---------------------------------------------------------------- validation 2: 8YR summary
summary = {}
sum_rows = read_tsv("#{TSV}/8YR Dock Summary.tsv")
sum_years = sum_rows[0][1..-1].map(&:to_i)
sum_rows.drop(1).each do |r|
  next if r[0].to_s =~ /total/i || r[0].to_s.empty?
  sum_years.each_with_index { |y, i| summary[[r[0].strip, y]] = r[i + 1].to_i if r[i + 1].to_s =~ /\A\d+\z/ }
end
sum_berths = summary.keys.map(&:first).uniq

# interpretations
interp = {
  'A: sum span_days (merge+fill_run+repeat+single)' => ->(rs) { rs.sum { |r| r[12] } },
  'B: merges count span, everything else 1 day' => ->(rs) { rs.sum { |r| r[13] == 'merge' ? r[12] : 1 } },
  'C: one day per record (ignore spans)' => ->(rs) { rs.size },
  'D: merge+repeat spans, fill_run = 1 day' => ->(rs) { rs.sum { |r| r[13] == 'fill_run' ? 1 : r[12] } },
  'E: distinct calendar days occupied (union of A)' => ->(rs) {
    days = Set.new
    rs.each { |r| next unless r[16]; (Date.parse(r[14])..Date.parse(r[15])).each { |d| days << d } }
    days.size },
}
by_by = records.group_by { |r| [r[5], r[3]] }   # berth_name, block_year
comp = []   # [berth, year, summary, {interp=>value}]
sum_berths.each do |b|
  sum_years.each do |y|
    rs = (by_by[[b, y]] || []).select { |r| r[16] }   # valid dates only
    vals = interp.map { |name, f| [name, rs.empty? ? 0 : f.call(rs)] }.to_h
    comp << [b, y, summary[[b, y]], vals]
  end
end
CSV.open("#{OUT}/summary_comparison.csv", 'w') do |csv|
  csv << ['berth', 'year', 'summary'] + interp.keys
  comp.each { |b, y, s, vals| csv << [b, y, s] + interp.keys.map { |k| vals[k] } }
end

# ---------------------------------------------------------------- validation 3: overlaps
overlaps = []
records.select { |r| r[16] }.group_by { |r| [r[0], r[4]] }.each do |(y, lab), rs|
  rs2 = rs.map { |r| [Date.parse(r[14]), Date.parse(r[15]), r] }.sort_by { |a| a[0] }
  rs2.each_with_index do |(s1, e1, r1), i|
    ((i + 1)...rs2.size).each do |j|
      s2, e2, r2 = rs2[j]
      break if s2 > e1
      overlaps << [r1, r2] if s2 <= e1 && s1 <= e2
    end
  end
end

# ---------------------------------------------------------------- report
rep = []
rep << "# Dock schedule extraction report"
rep << ""
rep << "Generated #{Time.now.strftime('%Y-%m-%d %H:%M')} by `extract_bookings.rb`. Output: `bookings.csv` (#{records.size} records from #{year_sheets.size} year sheets), `unlabeled_cells.csv` (#{unlabeled.size} text cells found in rows without a berth label), `summary_comparison.csv`."
rep << ""
rep << "## 1. Per-sheet extraction statistics"
rep << ""
rep << "Candidate = non-empty, non-formula, non-numeric cell in a labelled berth/group row (columns B onward). Records < candidates only when adjacent identical cells were collapsed (`repeat`)."
rep << ""
rep << "| sheet | blocks | candidates | records | merge | fill_run | repeat | single | outside day cols | bare numbers skipped | unlabeled-row text cells | header junk |"
rep << "|---|---|---|---|---|---|---|---|---|---|---|---|"
tot = Hash.new(0)
sheet_stats.sort.each do |y, s|
  rep << "| #{y} | #{s[:blocks].size} | #{s[:candidates]} | #{s[:records]} | #{s[:sources]['merge']} | #{s[:sources]['fill_run']} | #{s[:sources]['repeat']} | #{s[:sources]['single']} | #{s[:outside]} | #{s[:numeric_skipped]} | #{s[:unlabeled_cells]} | #{s[:header_junk]} |"
  tot[:blocks] += s[:blocks].size; tot[:cand] += s[:candidates]; tot[:rec] += s[:records]
  %w[merge fill_run repeat single].each { |k| tot[k] += s[:sources][k] }
  tot[:out] += s[:outside]; tot[:num] += s[:numeric_skipped]; tot[:unl] += s[:unlabeled_cells]; tot[:hj] += s[:header_junk]
end
rep << "| **all** | #{tot[:blocks]} | #{tot[:cand]} | #{tot[:rec]} | #{tot['merge']} | #{tot['fill_run']} | #{tot['repeat']} | #{tot['single']} | #{tot[:out]} | #{tot[:num]} | #{tot[:unl]} | #{tot[:hj]} |"
rep << ""
rep << "### Blocks found per sheet (label [day-1 column, days in header])"
rep << ""
sheet_stats.sort.each { |y, s| rep << "- **#{y}**: #{s[:blocks].join('; ')}" }
rep << ""

rep << "## 2. Usage-days comparison against the 8YR Dock Summary (block_year 2006-2013)"
rep << ""
rep << "Values are per `berth_name` (label without the length) and `block_year`, counting only records with valid dates. Interpretations:"
interp.keys.each { |k| rep << "- #{k}" }
rep << ""
rep << "| berth | year | summary | " + interp.keys.map { |k| k[0, 1] }.join(' | ') + " |"
rep << "|---|---|---|" + interp.keys.map { '---' }.join('|') + "|"
comp.each do |b, y, s, vals|
  rep << "| #{b} | #{y} | #{s} | " + interp.keys.map { |k| vals[k] }.join(' | ') + " |"
end
rep << ""
rep << "Total absolute deviation from the summary (lower is better), all rows / only the six grid berths:"
rep << ""
grid_b = sum_berths.select { |b| CANONICAL.include?(b) }
interp.keys.each do |k|
  dev_all = comp.sum { |b, y, s, vals| (vals[k] - s.to_i).abs }
  dev_grid = comp.select { |b, _, _, _| grid_b.include?(b) }.sum { |b, y, s, vals| (vals[k] - s.to_i).abs }
  exact = comp.count { |b, y, s, vals| vals[k] == s.to_i }
  rep << "- #{k}: all rows #{dev_all}, grid berths only #{dev_grid}, exact matches #{exact}/#{comp.size}"
end
best = interp.keys.min_by { |k| comp.select { |b, _, _, _| grid_b.include?(b) }.sum { |b, y, s, vals| (vals[k] - s.to_i).abs } }
rep << ""
rep << "**Best-fitting interpretation on the grid berths: #{best}** -- but see the discussion below; no interpretation reproduces the summary."
rep << ""
missing = sum_berths - label_years.keys.map { |l| parse_berth(l)[0] }
rep << "Summary rows with no matching grid row label in any year sheet: #{missing.map { |x| "'#{x}'" }.join(', ')}. 'North Finger Piers' first appears as a grid row label in #{label_years.select { |l, _| l =~ /Finger/ }.values.map(&:min).min || 'never'}, so its 2006-2013 summary values (298-511 days/yr) cannot come from these grids at all."
rep << ""

rep << "## 3. Overlapping records on the same berth (candidate legacy double-bookings)"
rep << ""
rep << "Pairs of records with the same `sheet_year` and `berth_label`, valid dates, and overlapping [start_date, end_date]: **#{overlaps.size} pairs**."
rep << ""
if overlaps.any?
  rep << "| sheet | berth | A: value | A: dates (row/col, source) | B: value | B: dates (row/col, source) |"
  rep << "|---|---|---|---|---|---|"
  overlaps.first(10).each do |r1, r2|
    rep << "| #{r1[0]} | #{r1[4]} | #{r1[17]} | #{r1[14]}..#{r1[15]} (R#{r1[8]}/#{r1[9]}, #{r1[13]}) | #{r2[17]} | #{r2[14]}..#{r2[15]} (R#{r2[8]}/#{r2[9]}, #{r2[13]}) |"
  end
  rep << ""
  by_src = Hash.new(0)
  overlaps.each { |r1, r2| by_src[[r1[13], r2[13]].sort.join('+')] += 1 }
  rep << "Overlap pairs by span-source combination: " + by_src.map { |k, v| "#{k}=#{v}" }.join(', ')
  by_reason = Hash.new(0)
  overlaps.each { |r1, r2| by_reason[r1[8] == r2[8] ? 'same row' : 'different rows with the same label'] += 1 }
  rep << ""
  rep << "Overlap pairs by cause: " + by_reason.map { |k, v| "#{k}=#{v}" }.join(', ') + ". Within a single row a span can never run past another value (fill runs and repeats stop at the next non-empty cell, merges cannot contain values), so overlaps arise only from duplicated berth rows inside one block."
end
rep << ""

rep << "## 4. Anomalies"
rep << ""
order = %w[block_year_differs_from_sheet merge_beyond_month multi_row_merge no_day_row_found day_row_does_not_start_at_1 header_days_ne_calendar values_in_header_or_weekday_row cell_outside_day_columns bare_number_in_berth_row duplicate_label_rows_in_block non_canonical_berth_label]
(order + (anomalies.keys - order)).each do |cat|
  list = anomalies[cat]
  next if list.empty?
  rep << "### #{cat} (#{list.size})"
  rep << ""
  list.first(cat == 'cell_outside_day_columns' || cat == 'bare_number_in_berth_row' ? 15 : 40).each { |x| rep << "- #{x}" }
  rep << "- ... (#{list.size - 40} more)" if list.size > 40 && !%w[cell_outside_day_columns bare_number_in_berth_row].include?(cat)
  rep << "- ... (#{list.size - 15} more)" if list.size > 15 && %w[cell_outside_day_columns bare_number_in_berth_row].include?(cat)
  rep << ""
end
rep << "### Text cells in rows without a berth label (#{unlabeled.size}; full list in `unlabeled_cells.csv`)"
rep << ""
rep << "These sit in the blank rows between the last berth row of a block and the next month header (or, in 2013/2014, in the row above the first header). They are not emitted as bookings. Per sheet: " + sheet_stats.sort.map { |y, s| "#{y}=#{s[:unlabeled_cells]}" }.join(', ') + "."
rep << ""
legend = unlabeled.select { |u| u[5] == 'F/V Western Sound' }
rep << "- A recurring row 'F/V Western Sound | R/V Long Ketch | M/V GREY COMPASS | Barge SILVER VOYAGER | OSV AMBER REEF | OSV Silver Tide | M/V NORTHERN HARBOR | R/V GOLDEN COMPASS ...' appears #{legend.size} times (sheets #{legend.map { |u| u[0] }.uniq.join(', ')}); it looks like a colour legend/key row, not bookings."
rep << "- Other unlabeled-row cells are a mix of vessel names, events and operational notes (e.g. #{unlabeled.reject { |u| u[5] =~ /Western Sound|Long Ketch|GREY COMPASS|SILVER VOYAGER|AMBER REEF|Silver Tide|NORTHERN HARBOR|GOLDEN COMPASS/ }.map { |u| u[5] }.uniq.first(8).map { |x| "'#{x}'" }.join(', ') }); in 2011-2013 they occupy the three rows under 'South Float East' where later sheets put the 'North Finger Piers:' / 'Small craft slips' rows, so some may be unlabelled finger-pier bookings."
rep << ""
rep << "### Berth labels and the years they appear in"
rep << ""
label_years.sort_by { |l, ys| ys.min }.each { |l, ys| rep << "- '#{l}': #{ys.min}-#{ys.max} (#{ys.size} sheets)" }
rep << ""
rep << "### Other observations"
rep << ""
rep << "- Every cell in the day grid carries thin borders on all four sides in every era, so borders carry no span information and were not used."
rep << "- Fills are used both as span indicators (e.g. 2005 'R/V CLEAR SEXTANT' green fill across 12 empty cells) and as row-wide shading (e.g. the whole 'North Pier Face' row grey in 2015/2019, whole 'Small craft slips' row white); fill runs starting from a shaded row therefore extend to the next value or the month end. Fill runs that reached the last day column with the same fill continuing: #{sheet_stats.values.sum { |s| s[:fill_clamped] }}."
rep << "- In several pre-2009 blocks the coloured fill starts one cell left of the named cell (e.g. 1997 'Tug WESTERN CURRENT' AB6 with AA6 also filled); the rule only extends to the right, so such leading cells are ignored."
rep << "- The 2010 sheet's 'NOVEMBER 2018'/'DECEMBER 2018' blocks are also structurally broken: the header row holds vessel names in C..H before the day numbers (which run 7..30/31), the weekday row holds 25 vessel names, and a stray '1..6' sits in the unlabeled row above the header."
rep << "- Day-number rows are shifted right in 2010 Jan (E), 2011 (C/F), 2012 (D/E/G), 2013 (F), 2014 (G), 2015 (D/H) while several values (notably 'R/V GOLDEN COMPASS' and 'R/V Golden Horizon' on the 1st) still sit in column B, i.e. left of day 1; those records are kept with day <= 0 and date_valid=false."
rep << ""

rep << "## 5. Assumptions"
rep << ""
assumptions = [
  "A block starts at any row whose column A matches a month name optionally followed by a four-digit year; the block ends at the next such row or the sheet end.",
  "block_year is the year in the header when present, else the sheet year; the mislabelled 'NOVEMBER 2018'/'DECEMBER 2018' blocks in the 2010 sheet are kept as labelled (block_year 2018).",
  "The day-number row is the row among the header row and the two following rows that holds the longest run of consecutive integers or '=...+1' formulas; the day-1 column is derived from that run (column of value N minus N-1), so runs that start above 1 still yield a day-1 column.",
  "If no day-number run of at least 3 cells exists, day 1 is assumed at column B for 'MONTH YYYY' headers and column C for plain 'Month' headers, and the block is listed as an anomaly.",
  "The block's last day column is the last number in the day-number row (not the calendar), and date_valid uses the real calendar of block_year/block_month.",
  "A berth row is any row inside a block whose column A is non-empty and is not a month header; rows with an empty column A are never berth rows, and their text cells go to unlabeled_cells.csv instead of bookings.csv.",
  "berth_name/berth_length_ft are parsed from \"<name> - <n>'\"; labels without a length (group rows) get an empty length and a name with any trailing colon removed.",
  "group_label is set only on group rows: 'North Finger Piers:' gets itself, 'Small craft slips (institution boats)' gets the nearest preceding 'North Finger Piers:' in the block (or itself when none precedes it); the six canonical berths always get an empty group_label even when a duplicate berth row sits below a group row.",
  "Every non-empty cell in a berth row from column B onward is a record unless it is a formula ('=...') or a bare number; cells left of day 1 or right of the last day column are still emitted (with the computed day) and flagged.",
  "Span precedence is merge, then fill_run, then repeat, then single; a fill run requires a solid fill that is not 'none', not theme 0 without tint and not rgb FFFFFFFF (white), and extends only over empty cells with the identical fill string up to the block's last day column.",
  "A repeat run collapses only exactly identical strings in immediately adjacent cells (case-sensitive), consuming those cells.",
  "Merges are read from the sheet XML; a merge whose right edge passes the last day column is clamped and flagged; a merge is honoured only when the value sits in its top-left cell.",
  "date_valid is true only when both start_day and end_day exist in block_year/block_month; invalid ISO dates are left blank rather than raising.",
  "The fill column holds the raw _styles.tsv fill summary of the start cell for non-default solid fills and is blank otherwise.",
  "The 8YR summary comparison matches on berth_name (label without length) and block_year, counting only records with valid dates; nothing was tuned to improve the match.",
  "Weekday-letter rows are recognised by having an empty column A and at least five single-letter weekday cells; text found in header or weekday rows is reported as junk, not extracted.",
  "Borders are ignored for span detection because every grid cell carries thin borders.",
  "Values in registry sheets (Science/Yachts/Tours) are not used; classification of raw_value (vessel vs event vs note) is out of scope.",
]
assumptions.each_with_index { |a, i| rep << "#{i + 1}. #{a}" }
rep << ""
File.write("#{OUT}/extract_report.md", rep.join("\n"))

# console summary for the caller
srcs = Hash.new(0); records.each { |r| srcs[r[13]] += 1 }
puts "records=#{records.size} sources=#{srcs.map { |k, v| "#{k}=#{v}" }.join(', ')} unlabeled_cells=#{unlabeled.size} overlaps=#{overlaps.size}"
puts "best interpretation: #{best}"
