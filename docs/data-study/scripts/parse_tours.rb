#!/usr/bin/ruby
# Parses Tours.tsv and "8YR Dock Summary.tsv" (produced by xlsx2tsv.rb) into CSVs + a report.
# Usage: ruby parse_tours.rb <tsv_dir> <out_dir>
require 'csv'; require 'date'; require 'fileutils'
tsv_dir, out = ARGV[0], ARGV[1]
FileUtils.mkdir_p(out)
EXCEL_EPOCH = Date.new(1899, 12, 30)   # serial 1 = 1900-01-01, incl. Lotus leap-year bug

rows = File.readlines(File.join(tsv_dir, 'Tours.tsv')).map { |l| l.chomp("\n").split("\t", -1) }
BANNER = 'Tours are now tracked in a separate workbook; this tab is kept for reference.'
HEADER = %w[Date Time Guide Guest People Dock/\ Ship Notes]

tours = []; banners = []; blanks = []; strays = []; header_row = nil
odd = Hash.new { |h, k| h[k] = [] }
rows.each_with_index do |r, i|
  idx = i + 1
  a = (r[0] || '').strip
  if a == BANNER then banners << idx; next end
  if r.all? { |c| c.to_s.strip.empty? } then blanks << idx; next end
  if a == 'Date' then header_row = idx; next end
  unless a =~ /\A\d+(\.0+)?\z/
    strays << [idx, a]; next     # e.g. "Requires shore power" alone in col A (row 18)
  end
  date_iso = (EXCEL_EPOCH + a.to_i).iso8601
  time_raw = (r[1] || '').strip
  time_valid = if time_raw =~ /\A(\d{1,2})(\d{2})\z/ && $1.to_i < 24 && $2.to_i < 60
                 format('%02d:%02d', $1.to_i, $2.to_i)
               else
                 odd[:time_invalid] << [idx, time_raw]; ''
               end
  guide = (r[2] || '').strip
  guest = (r[3] || '').strip
  if guest =~ /\A(.*?)\s*\((.*)\)\s*\z/ then gname, gorg = $1, $2
  else gname, gorg = guest, ''; odd[:guest_no_org] << [idx, guest] end
  people_raw = (r[4] || '').strip
  approx = people_raw.start_with?('~')
  people_num = people_raw.sub(/\A~/, '') =~ /\A\d+\z/ ? people_raw.sub(/\A~/, '').to_i : nil
  odd[:people_unparsed] << [idx, people_raw] if people_num.nil?
  odd[:people_large] << [idx, people_raw] if people_num && people_num >= 40
  odd[:people_approx] << [idx, people_raw] if approx
  dock = (r[5] || '').strip
  notes = (r[6] || '').strip
  odd[:no_notes] << idx if notes.empty?
  tours << [date_iso, time_raw, time_valid, guide, gname, gorg, people_raw, people_num, approx, dock, notes, idx]
end

CSV.open(File.join(out, 'tours.csv'), 'w') do |c|
  c << %w[date_iso time_raw time_valid guide guest_name guest_org people_raw people_num people_approx dock_or_ship notes row_index]
  tours.each { |t| c << t }
end

# ---- 8YR summary ----
sum = File.readlines(File.join(tsv_dir, '8YR Dock Summary.tsv')).map { |l| l.chomp("\n").split("\t", -1) }
years = sum[0][1..-1].map(&:to_i)
formula_rows = []
CSV.open(File.join(out, 'usage_summary.csv'), 'w') do |c|
  c << %w[berth year days]
  sum[1..-1].each do |r|
    berth = r[0].strip
    if r[1..-1].any? { |v| v.to_s.start_with?('=') }
      formula_rows << [berth, r[1..-1]]; next
    end
    years.each_with_index { |y, j| c << [berth, y, r[j + 1].to_i] }
  end
end
totals = years.each_with_index.map { |y, j| [y, sum[1..7].sum { |r| r[j + 1].to_i }] }

# ---- report ----
dates = tours.map { |t| t[0] }
by_dock = tours.group_by { |t| t[9] }.map { |k, v| "#{k}: #{v.size}" }.sort
by_org = tours.group_by { |t| t[5] }.map { |k, v| "#{k}: #{v.size}" }.sort
dup_dates = tours.group_by { |t| t[0] }.select { |_, v| v.size > 1 }.map { |k, v| "#{k} (#{v.size})" }
md = []
md << "# Tours sheet parse report\n"
md << "Source: `Tours.tsv` (sheet27). Output: `tours.csv`.\n"
md << "## Row counts\n"
md << "- Physical rows in sheet: #{rows.size}"
md << "- Banner rows: #{banners.size} (rows #{banners.join(', ')}); the top two and the bottom two are each merged A:G (mergeCell A1:G1, A2:G2, A41:G41, A42:G42 -- those are the only 4 merges in sheet27.xml)"
md << "- Header row: #{header_row}"
md << "- Blank rows: #{blanks.size} (rows #{blanks.join(', ')}) -- visual separators between months"
md << "- Stray note fragments (non-numeric col A, skipped): #{strays.size} #{strays.inspect}"
md << "- Parsed tour rows: **#{tours.size}**\n"
md << "## Date range\n"
md << "- #{dates.min} to #{dates.max} (serials #{tours.map{|t|t[11]}.size} rows; converted as 1899-12-30 + serial)"
md << "- Dates with multiple tours: #{dup_dates.join(', ')}\n"
md << "## Oddities and handling\n"
md << "- Time not HHMM (kept in `time_raw`, `time_valid` empty): #{odd[:time_invalid].size} rows -- 'tbd' x#{odd[:time_invalid].count{|_,v|v=='tbd'}}, '1175' x#{odd[:time_invalid].count{|_,v|v=='1175'}} (minute 75 is impossible; rows #{odd[:time_invalid].select{|_,v|v=='1175'}.map(&:first).join(', ')}). Valid 3-digit times like '930' are zero-padded to 09:30."
md << "- People with '~' prefix (approximate): #{odd[:people_approx].size} rows -> `people_approx=true`, `people_num` = stripped integer."
md << "- People unparseable: #{odd[:people_unparsed].size}."
md << "- Unusually large party: #{odd[:people_large].inspect} (row 34, 54 people; kept as-is, flagged here)."
md << "- Guest without '(Org)': #{odd[:guest_no_org].size}."
md << "- Empty Notes: rows #{odd[:no_notes].join(', ')}."
md << "- Row 18 'Requires shore power' sits alone in col A directly under row 17 which already has that note: treated as a stray duplicate fragment and dropped."
md << "- Row 26: guide 'Elliot' hosts guest 'Elliot Bramble' -- coincidence in synthetic data, no action."
md << "- The sheet is not sorted strictly (rows 4-6 have descending times on the same date); order preserved via `row_index`.\n"
md << "## Distribution\n"
md << "- By vessel: #{by_dock.join('; ')}"
md << "- By organisation: #{by_org.join('; ')}\n"
md << "## Assumptions\n"
md << "1. Date serials use the 1900 date system (epoch 1899-12-30), so 43219 = 2018-04-29; no 1904-system check was possible because there are no cached values."
md << "2. Times are 24h local HHMM; a 3-digit value means H:MM; anything with minutes >= 60 or hours >= 24 is invalid rather than a typo to be corrected."
md << "3. '~N' means an estimated headcount and the integer N is usable for capacity planning."
md << "4. Guest format 'Name (Organization)' is universal; the last parenthesised group is the org."
md << "5. Non-data rows (banners, blanks, a lone note in col A) carry no tour information and can be dropped without loss; the trailing banner rows 41-42 duplicate rows 1-2."
md << "\n## Implications for a scheduling system\n"
md << "- Tours are point-in-time events (date + optional time), not berth occupancy: they never span a day range and do not consume a berth slot."
md << "- They reference vessels by free-text name ('R/V Silver Tern'); a scheduler needs a vessel registry so a tour can be linked to the vessel *and* to wherever that vessel is berthed that day (the join is via vessel, not via dock)."
md << "- Fields needed: date, time (nullable / 'tbd' state), guide (staff), guest contact, guest org, headcount (with approximate flag), vessel, status-like notes (Confirmed / Pending insurance / Approved) which are really a workflow status and should be an enum plus free text."
md << "- Validation the sheet lacks: time format, headcount type, required notes, no stray rows. Multiple tours per vessel per day (e.g. 3 on 2018-04-29) are normal, so vessel+date is not a unique key."
md << "- The banner says tours moved to a separate workbook: treat this tab as a legacy sample, not the system of record.\n"
md << "## 8YR Dock Summary\n"
md << "- Transcribed to `usage_summary.csv` (#{years.size} years x 7 berths = #{7*years.size} rows)."
md << "- The 'Total Days' row is an uncached formula (#{formula_rows.map{|b,v| v.first}.first} ...) with no <v> value in the XML, so it was NOT transcribed; recomputed sums: #{totals.map{|y,t| "#{y}=#{t}"}.join(', ')}."
md << "- 'Marsh Landing' appears here but not as a grid row label in the year sheets; 'Inner Channel 55'' appears in the grid but not here -- possibly the same berth under a different name (to investigate)."
File.write(File.join(out, 'tours_report.md'), md.join("\n") + "\n")
puts "tours=#{tours.size} range=#{dates.min}..#{dates.max}"
