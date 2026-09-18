#!/usr/bin/ruby
# build_registry.rb -- build a clean vessel registry from the messy
# "Science" and "Yachts" contact sheets (TSV exports of the workbook).
#
# usage: ruby build_registry.rb [TSV_DIR] [OUT_DIR]
# Inputs : TSV_DIR/Science.tsv, TSV_DIR/Yachts.tsv
# Outputs: OUT_DIR/vessels.csv, OUT_DIR/vessel_length_lookup.csv, OUT_DIR/registry_report.md
require 'csv'

BASE    = File.expand_path('..', __dir__)
TSV_DIR = ARGV[0] || File.join(BASE, 'tsv')
OUT_DIR = ARGV[1] || __dir__

# ---------------------------------------------------------------- classifiers
PREFIX_RE = %r{\A(R/V|M/V|F/V|S/V|M/Y|S/Y|OS/V|OSV|USCG|Tug|Barge)\b}i
LEN_RE    = /\s+(\d+(?:\.\d+)?)\s*'\s*\z/           # trailing  NN'
LOA_RE    = /\bLOA:?\s*(\d+(?:\.\d+)?)\s*'/i
DRAFT_RE  = /\bDraft:?\s*(\d+(?:\.\d+)?)\s*'/i
PHONE_RE  = /\A(?:(Cell|Work|Office|Tel|Phone|Fax|Mobile)\s*:?\s*)?(\+?\d[\d\s().-]{6,}\d)\z/i
EMAIL_RE  = /\A[\w.+-]+@[\w-]+(\.[\w-]+)+\z/
URL_RE    = %r{\Ahttps?://}i
CAPT_RE   = /\A(Capt\.?|Captain|Mr\.?|Ms\.?|Dr\.?)\s+\S/i
PERSON_RE = /\A[A-Z][a-z]+(?:\s+[A-Z][a-z'-]+){1,2}\z/   # "Jesse Marsh"
ORG_WORDS = /\b(Institute|Charters?|Academy|Partners|Group|University|College|Agency|Services?|Trust|School|Foundation|Offshore|Marine|Research|Fisheries|Inc\.?|LLC|Ltd\.?|Corp\.?|Company|Co\.|Authority|Department|Laboratory|Lab)\b/i

FLAG_RULES = [
  [/raft/i,                         'rafts_ok'],
  [/short visit/i,                  'short_visit'],
  [/shore power/i,                  'shore_power'],
  [/insurance/i,                    'insurance_pending'],
  [/no overnight crew/i,            'no_overnight_crew'],
  [/scheduling file/i,              'see_schedule_file'],
  [/contact captain/i,              'contact_captain_on_arrival'],
  [/confirmed/i,                    'confirmed'],
  [/approved/i,                     'approved'],
  [/tentative|awaiting confirmation/i, 'tentative'],
]

def norm_ws(s) s.to_s.gsub(/[[:space:]]+/, ' ').strip end

def vessel_name_cell?(s)
  s = norm_ws(s)
  return false if s.empty?
  return true if s =~ PREFIX_RE
  return true if s =~ LEN_RE            # "Something 40'"
  return true if s =~ LOA_RE            # "LOA: 145', Draft: 12'" (length mark, unnamed)
  false
end

def classify(cell)
  s = norm_ws(cell)
  return nil if s.empty?
  return [:url, s]            if s =~ URL_RE
  return [:email, s.downcase] if s =~ EMAIL_RE
  return [:phone, s]          if s =~ PHONE_RE
  return [:spec, s]           if s =~ LOA_RE || s =~ DRAFT_RE
  return [:note, s]           if FLAG_RULES.any? { |re, _| s =~ re }
  return [:person, s]         if s =~ CAPT_RE
  return [:org, s]            if s =~ ORG_WORDS
  return [:person, s]         if s =~ PERSON_RE
  [:note, s]
end

def type_prefix_of(name)
  m = name.match(PREFIX_RE) or return 'other'
  p = m[1].upcase
  p = 'OSV' if p == 'OS/V'
  p = 'Tug' if p == 'TUG'
  p = 'Barge' if p == 'BARGE'
  p
end

def name_key(name)
  name.downcase.gsub(/[^a-z0-9\s]+/, '').strip.gsub(/\s+/, ' ')
end

# ---------------------------------------------------------------- parse
Vessel = Struct.new(:source_sheet, :row, :raw_name, :vessel_name, :name_key, :type_prefix,
                    :length_ft, :loa_ft, :draft_ft, :operators, :contacts, :notes, :flags,
                    :urls, :unnamed) do
  def add_cell(kind, val)
    case kind
    when :url    then urls << val
    when :email, :phone, :person then contacts << val unless contacts.include?(val)
    when :org    then operators << val unless operators.include?(val)
    when :spec
      if (m = val.match(LOA_RE))   then self.loa_ft   ||= m[1].to_f end
      if (m = val.match(DRAFT_RE)) then self.draft_ft ||= m[1].to_f end
    when :note   then notes << val unless notes.include?(val)
    end
  end
end

stats = Hash.new(0)
patterns = Hash.new { |h, k| h[k] = [] }   # pattern -> example strings
vessels = []
noise_rows = []

%w[Science Yachts].each do |sheet|
  path = File.join(TSV_DIR, "#{sheet}.tsv")
  lines = File.read(path).split(/\r?\n/, -1)
  lines.pop if lines.last == ''
  current = nil
  lines.each_with_index do |line, i|
    rownum = i + 1
    cells = line.split("\t", -1).map { |c| norm_ws(c) }
    stats["rows_in_#{sheet}"] += 1
    next if cells.all?(&:empty?).tap { |b| stats["blank_rows_#{sheet}"] += 1 if b }
    first = cells[0]
    if sheet == 'Science' && rownum == 1 && first.upcase == 'VESSEL'
      stats['header_rows'] += 1
      next
    end
    if vessel_name_cell?(first)
      raw = first
      unnamed = !(raw =~ PREFIX_RE) && !!(raw =~ LOA_RE)
      v = Vessel.new(sheet, rownum, raw, '', '', 'other', nil, nil, nil, [], [], [], [], [], unnamed)
      if unnamed
        v.vessel_name = ''
        v.name_key    = ''
        v.add_cell(:spec, raw)
        patterns['LOA/Draft spec in the VESSEL column with no vessel name (headless group)'] << "#{sheet} row #{rownum}: #{raw.inspect}"
      else
        name = raw.dup
        if (m = name.match(LEN_RE))
          v.length_ft = m[1].to_f
          name = name.sub(LEN_RE, '')
        end
        name = name.sub(%r{\AOS/V\b}i, 'OSV')
        v.vessel_name = norm_ws(name)
        v.name_key    = name_key(v.vessel_name)
        v.type_prefix = type_prefix_of(raw)
        patterns['Prefix variant "OS/V" instead of "OSV"'] << "#{sheet} row #{rownum}: #{raw.inspect}" if raw =~ %r{\AOS/V}i
        patterns['Vessel name in ALL CAPS while others are Title Case'] << "#{sheet} row #{rownum}: #{raw.inspect}" if v.vessel_name.sub(PREFIX_RE, '').strip =~ /\A[A-Z\s]+\z/
      end
      vessels << v
      current = v
      cells[1..-1].each_with_index do |c, j|
        k = classify(c) or next
        col = j + 2
        if sheet == 'Science'
          patterns['Phone number under a non-phone column (OPERATOR/CONTACT/EMAIL)'] << "Science row #{rownum} col #{col}: #{c.inspect}" if k[0] == :phone && ![4, 5].include?(col)
          patterns['Email under a non-EMAIL column'] << "Science row #{rownum} col #{col}: #{c.inspect}" if k[0] == :email && col != 6
          patterns['Free-text note under CONTACT/WORK#/CELL# instead of NOTES'] << "Science row #{rownum} col #{col}: #{c.inspect}" if k[0] == :note && col < 7
          patterns['Organization (operator) under CONTACT column'] << "Science row #{rownum} col #{col}: #{c.inspect}" if k[0] == :org && col != 2
        end
        patterns['"LOA: NN\', Draft: NN\'" spec in a secondary column of a named vessel'] << "#{sheet} row #{rownum} col #{col}: #{c.inspect}" if k[0] == :spec
        current.add_cell(*k)
      end
    else
      # continuation fragment
      if current.nil?
        noise_rows << "#{sheet} row #{rownum}: #{cells.reject(&:empty?).join(' | ')}"
        stats['noise_rows'] += 1
        next
      end
      stats["continuation_rows_#{sheet}"] += 1
      prev_blank = i > 0 && lines[i - 1].split("\t", -1).all? { |c| norm_ws(c).empty? }
      patterns['Continuation fragment separated from its vessel by a blank row'] << "#{sheet} row #{rownum}: #{cells.reject(&:empty?).join(' | ').inspect}" if prev_blank
      patterns['Continuation row with a lone phone/email/captain in the VESSEL column'] << "#{sheet} row #{rownum}: #{first.inspect}" unless first.empty?
      cells.each_with_index do |c, j|
        k = classify(c) or next
        patterns['"LOA: NN\', Draft: NN\'" spec in a secondary column of a named vessel'] << "#{sheet} row #{rownum} col #{j + 1}: #{c.inspect}" if k[0] == :spec
        current.add_cell(*k)
      end
    end
  end
end

# ---------------------------------------------------------------- derive
vessels.each do |v|
  v.length_ft ||= v.loa_ft
  fl = []
  v.notes.each { |n| FLAG_RULES.each { |re, f| fl << f if n =~ re } }
  fl << 'unnamed' if v.unnamed
  fl << 'no_contact' if v.contacts.empty?
  fl << 'multiple_operators' if v.operators.size > 1
  fl << 'length_loa_mismatch' if v.loa_ft && v.length_ft && v.loa_ft != v.length_ft
  v.flags = fl.uniq
  patterns['Multiple different operator organizations attached to one vessel'] << "#{v.source_sheet} row #{v.row} #{v.raw_name}: #{v.operators.join(' / ')}" if v.operators.size > 1
end
# repeated notes pattern (count raw repeats)
%w[Science Yachts].each do |sheet|
  File.read(File.join(TSV_DIR, "#{sheet}.tsv")).split(/\r?\n/).each_with_index do |line, i|
    cs = line.split("\t").map { |c| norm_ws(c) }.reject(&:empty?)
    dup = cs.group_by { |x| x }.select { |_, a| a.size > 1 }.keys
    patterns['Identical note repeated in several cells of one row'] << "#{sheet} row #{i + 1}: #{dup.first.inspect} x#{cs.count(dup.first)}" unless dup.empty?
  end
end
vessels.each { |v| patterns['Placeholder URL cell (dropped from contacts, counted)'] << "#{v.source_sheet} row #{v.row} #{v.raw_name}" unless v.urls.empty? }

# duplicates & conflicts
dups = []; conflicts = []
by_key = vessels.reject(&:unnamed).group_by(&:name_key)
by_key.each do |k, vs|
  next if vs.size < 2
  where = vs.map { |v| "#{v.source_sheet} row #{v.row} (#{v.raw_name})" }.join(' ; ')
  dups << "#{k}: #{where}"
  lens = vs.map(&:length_ft).compact.uniq
  conflicts << "#{k}: lengths #{lens.map { |l| l.to_i.to_s + "'" }.join(' vs ')} -- #{where}" if lens.size > 1
end

# ---------------------------------------------------------------- write vessels.csv
fmt = ->(x) { x.nil? ? '' : (x == x.to_i ? x.to_i.to_s : x.to_s) }
CSV.open(File.join(OUT_DIR, 'vessels.csv'), 'w') do |csv|
  csv << %w[source_sheet raw_name vessel_name name_key type_prefix length_ft loa_ft draft_ft operator contacts notes flags]
  vessels.each do |v|
    csv << [v.source_sheet, v.raw_name, v.vessel_name, v.name_key, v.type_prefix,
            fmt[v.length_ft], fmt[v.loa_ft], fmt[v.draft_ft],
            v.operators.join(' / '), v.contacts.join(' | '), v.notes.join(' | '), v.flags.join(',')]
  end
end

# ---------------------------------------------------------------- write lookup (max length on conflict)
CSV.open(File.join(OUT_DIR, 'vessel_length_lookup.csv'), 'w') do |csv|
  csv << %w[name_key length_ft]
  by_key.keys.sort.each do |k|
    lens = by_key[k].map(&:length_ft).compact
    csv << [k, lens.empty? ? '' : fmt[lens.max]]
  end
end

# ---------------------------------------------------------------- report
named = vessels.reject(&:unnamed)
rows_in = stats['rows_in_Science'] + stats['rows_in_Yachts']
r = []
r << "# Vessel registry report"
r << ""
r << "Built by `analysis/build_registry.rb` from `tsv/Science.tsv` and `tsv/Yachts.tsv`."
r << ""
r << "## Counts"
r << ""
r << "| metric | value |"
r << "|---|---|"
r << "| rows in (Science / Yachts / total) | #{stats['rows_in_Science']} / #{stats['rows_in_Yachts']} / #{rows_in} |"
r << "| header rows skipped | #{stats['header_rows']} |"
r << "| blank rows | #{stats['blank_rows_Science'] + stats['blank_rows_Yachts']} |"
r << "| continuation rows folded into the vessel above (Science / Yachts) | #{stats['continuation_rows_Science']} / #{stats['continuation_rows_Yachts']} |"
r << "| noise rows (fragment with no vessel above) | #{stats['noise_rows']} |"
r << "| vessels out (rows in vessels.csv) | #{vessels.size} |"
r << "| of which named vessels | #{named.size} |"
r << "| of which unnamed (LOA-spec-only) groups | #{vessels.count(&:unnamed)} |"
r << "| vessels with a length (trailing NN' or LOA) | #{vessels.count(&:length_ft)} |"
r << "| vessels with a separately stated LOA | #{vessels.count(&:loa_ft)} |"
r << "| vessels with a draft | #{vessels.count(&:draft_ft)} |"
r << "| vessels with an operator | #{vessels.count { |v| !v.operators.empty? }} |"
r << "| vessels with no contact at all | #{vessels.count { |v| v.contacts.empty? }} |"
r << "| vessels with notes | #{vessels.count { |v| !v.notes.empty? }} |"
r << "| distinct name_keys | #{by_key.size} |"
r << "| duplicate name_keys (appearing 2+ times) | #{dups.size} |"
r << "| length conflicts among duplicates | #{conflicts.size} |"
r << "| Science vessels / Yachts vessels | #{vessels.count { |v| v.source_sheet == 'Science' }} / #{vessels.count { |v| v.source_sheet == 'Yachts' }} |"
r << ""
r << "Type prefix distribution: " + vessels.group_by(&:type_prefix).map { |k, a| "#{k}=#{a.size}" }.sort.join(', ')
r << ""
r << "Flag distribution: " + vessels.flat_map(&:flags).group_by { |x| x }.map { |k, a| "#{k}=#{a.size}" }.sort.join(', ')
r << ""
r << "## Duplicates"
r << ""
dups.empty? ? r << "none" : dups.each { |d| r << "- #{d}" }
r << ""
r << "## Length conflicts"
r << ""
conflicts.empty? ? r << "none" : conflicts.each { |d| r << "- #{d}" }
r << ""
r << "`vessel_length_lookup.csv` keeps ONE row per name_key; when duplicates disagree on length the MAXIMUM is used (conservative for berth-fit purposes)."
r << ""
r << "## Noise rows"
r << ""
noise_rows.empty? ? r << "none" : noise_rows.each { |d| r << "- #{d}" }
r << ""
r << "## Messiness patterns handled"
r << ""
patterns.sort_by { |_, ex| -ex.size }.each do |name, ex|
  r << "### #{name} (#{ex.size} occurrence#{ex.size == 1 ? '' : 's'})"
  ex.first(5).each { |e| r << "- #{e}" }
  r << ""
end
r << "## Assumptions"
r << ""
[
  "A row starts a new vessel iff its first cell carries a type prefix (R/V, M/V, F/V, S/V, M/Y, S/Y, OSV, OS/V, USCG, Tug, Barge), ends in a length mark NN', or is an `LOA:` spec. Every other non-blank row is a continuation of the vessel above, regardless of which column its content sits in.",
  "Blank rows do NOT close a group: fragments after a blank row (e.g. Science rows 140, 146, 148, 196, 239; Yachts row 94) are attached to the vessel above them rather than discarded, because in this data the same pattern (blank row then phone/email) also appears where the attribution is unambiguous.",
  "An `LOA: NN', Draft: NN'` cell in the VESSEL column (Yachts rows 6 and 83) starts an UNNAMED group (flag `unnamed`, empty vessel_name/name_key) rather than being merged into the previous yacht, because merging would contradict that yacht's own stated length (52' / 24' vs LOA 145').",
  "length_ft is taken from the trailing NN' of the name; when a named vessel also carries an `LOA:` spec (e.g. M/Y Western Strand 52' with LOA: 65'), length_ft keeps the name's value, loa_ft records the LOA, and the flag `length_loa_mismatch` is set. The lookup file uses length_ft.",
  "Cells are classified by shape, not by column: `Cell:/Work:` + digits = phone, `x@y.z` = email, `Capt.` or `Firstname Lastname` = person, text containing an organisation word (Institute, Charters, Academy, University, Partners, Group, Agency, Services, Trust, School, Foundation, Offshore, ...) = operator, everything else = note. Persons, phones and emails are all folded into `contacts`.",
  "Placeholder cells `https://www.example.org/vessel` are treated as noise and dropped from contacts/notes (counted in the report).",
  "Several distinct operator organisations in one row group are all kept, joined by ` / `, with flag `multiple_operators`; no attempt is made to decide which is primary.",
  "name_key includes the type prefix with punctuation removed (`rv iron ketch` vs `fv iron ketch` are different vessels); `OS/V` is normalised to `OSV` before keying so both spellings match. Case is ignored, so `M/V CORAL DRIFT` and `M/V Coral Drift` would match. Duplicate vessels are kept as separate rows in vessels.csv (one per occurrence) and only collapsed in vessel_length_lookup.csv.",
].each_with_index { |a, i| r << "#{i + 1}. #{a}" }
r << ""
File.write(File.join(OUT_DIR, 'registry_report.md'), r.join("\n"))

puts "vessels=#{vessels.size} named=#{named.size} with_length=#{vessels.count(&:length_ft)} with_draft=#{vessels.count(&:draft_ft)} dups=#{dups.size} conflicts=#{conflicts.size} noise=#{stats['noise_rows']}"
