#!/usr/bin/ruby
# build_taxonomy.rb - classify every distinct booking-cell value of the 23 year grids.
# Usage: ruby build_taxonomy.rb <scratch_dir>
# Reads  <S>/all_cells.txt, <S>/tsv/Science.tsv, <S>/tsv/Yachts.tsv
# Writes <S>/analysis/value_taxonomy.csv
require 'csv'
require 'set'

S = ARGV[0] or abort "usage: build_taxonomy.rb <scratch_dir>"
A = File.join(S, 'analysis')

# ---------------------------------------------------------------- rules
# 1. Vessel type prefixes (case-insensitive match, canonical spelling on the right).
PREFIXES = {
  'r/v' => 'R/V', 'm/v' => 'M/V', 'f/v' => 'F/V', 's/v' => 'S/V',
  'm/y' => 'M/Y', 's/y' => 'S/Y', 'osv' => 'OSV', 'os/v' => 'OSV',
  'tug' => 'Tug', 'barge' => 'Barge', 'uscg' => 'USCG', 'uscgc' => 'USCG',
}
PREFIX_RE = /\A(#{PREFIXES.keys.map { |k| Regexp.escape(k) }.join('|')})\s+(.+)\z/i

# 2. Hand-curated overrides for non-vessel values (exact match, case-insensitive).
#    kind, normalized label, confidence, rationale
OVERRIDES = {
  'bunker barge'                        => ['vessel',  'Bunker barge', 'medium', 'unnamed service craft occupying berth'],
  'emergency port call'                 => ['event',   'Emergency port call', 'medium', 'unnamed vessel visit occupies berth'],
  'fuel truck'                          => ['note',    'Fuel truck', 'medium', 'shoreside service, annotation not booking'],
  'wire spooling'                       => ['note',    'Wire spooling', 'medium', 'deck operation on berthed vessel'],
  'returns from sea trials'             => ['note',    'Returns from sea trials', 'high', 'movement annotation'],
  'dock inspection'                     => ['closure', 'Dock inspection', 'medium', 'inspection restricts berth use'],
  'crane access - berth closed'         => ['closure', 'Crane access - berth closed', 'high', 'explicitly says berth closed'],
  'science stroll'                      => ['event',   'Science stroll', 'high', 'public outreach activity'],
  'film crew on dock'                   => ['event',   'Film crew on dock', 'high', 'non-vessel activity on dock'],
  'donor reception'                     => ['event',   'Donor reception', 'high', 'institutional function'],
  'public open house'                   => ['event',   'Public open house', 'high', 'public activity'],
  'dive training'                       => ['event',   'Dive training', 'high', 'training activity'],
  'safety training (ribs)'              => ['event',   'Safety training (RIBs)', 'high', 'training activity'],
  'rescue drill'                        => ['event',   'Rescue drill', 'high', 'drill activity'],
  'holiday'                             => ['event',   'Holiday', 'high', 'calendar event, no vessel'],
  'community sail day'                  => ['event',   'Community sail day', 'high', 'community activity'],
  'campus event'                        => ['event',   'Campus event', 'high', 'institutional activity'],
  'student tour'                        => ['event',   'Student tour', 'high', 'tour activity'],
  'road race - access limited'          => ['event',   'Road race - access limited', 'high', 'external event limits access'],
  'float rebuild - no usage permitted'  => ['closure', 'Float rebuild', 'high', 'maintenance, usage forbidden'],
  'bollard replacement, west face'      => ['closure', 'Bollard replacement', 'high', 'maintenance work on berth'],
  'dock maintenance - restricted access'=> ['closure', 'Dock maintenance', 'high', 'maintenance restricts access'],
  'ultrasonic pier test'                => ['closure', 'Ultrasonic pier test', 'high', 'structural testing of pier'],
  'concrete work near test wells'       => ['closure', 'Concrete work', 'high', 'construction work'],
  'utility work on pier face'           => ['closure', 'Utility work', 'high', 'utility work on berth'],
  'pier repair - no docking'            => ['closure', 'Pier repair', 'high', 'repair, docking forbidden'],
  'paving near dock entrance'           => ['closure', 'Paving near dock entrance', 'medium', 'works near dock, access limited'],
}

# 3. Generic note patterns (operational annotations).
NOTE_PATTERNS = [
  [/\A(eta|etd|arrival|arrives|departs|departure)\b/i,   'arrival/departure time annotation'],
  [/\A(fueling|bunkering|provisioning|load equipment|water\/slops pumping)\b/i, 'service operation annotation'],
  [/\A(delayed|touch and go)\b/i,                        'schedule/movement annotation'],
]
# Note normalization: strip trailing times/modifiers so "Bunkering 1000" -> "Bunkering".
def note_label(v)
  base = v.sub(/\s*@?\s*\d{3,4}\z/, '').sub(/\s+(am|pm)\z/i, '')
  base = 'Fueling' if base =~ /\Afueling/i
  base = 'Bunkering' if base =~ /\Abunkering/i
  base = 'ETA' if base =~ /\Aeta\b/i
  base = 'ETD' if base =~ /\Aetd\b/i
  base = 'Arrival' if base =~ /\A(arrival|arrives)\b/i
  base = 'Departure' if base =~ /\A(departure|departs)\b/i
  base
end

def title_case(s)
  s.split(/\s+/).map { |w| w.split('-').map { |p| p[0].upcase + p[1..-1].downcase }.join('-') }.join(' ')
end

# ---------------------------------------------------------------- registry (lengths)
registry = Hash.new { |h, k| h[k] = Set.new }
%w[Science Yachts].each do |sheet|
  path = File.join(S, 'tsv', "#{sheet}.tsv")
  next unless File.exist?(path)
  File.foreach(path) do |line|
    line.split("\t").each do |cell|
      if cell.strip =~ /\A(#{PREFIXES.keys.map { |k| Regexp.escape(k) }.join('|')})\s+(.+?)\s+(\d+)'\s*\z/i
        registry["#{PREFIXES[$1.downcase]} #{title_case($2)}"] << $3.to_i
      end
    end
  end
end

# ---------------------------------------------------------------- classify
counts = Hash.new(0)
File.foreach(File.join(S, 'all_cells.txt')) { |l| v = l.chomp; counts[v] += 1 unless v.strip.empty? }

rows = []
counts.sort_by { |v, c| [-c, v] }.each do |raw, n|
  key = raw.strip.downcase
  kind = norm = prefix = length = conf = why = nil
  if (o = OVERRIDES[key])
    kind, norm, conf, why = o
    prefix = 'Barge' if key == 'bunker barge'
  elsif raw.strip =~ PREFIX_RE
    kind = 'vessel'; prefix = PREFIXES[$1.downcase]; name = title_case($2.strip)
    norm = "#{prefix} #{name}"; conf = 'high'; why = 'recognized vessel type prefix'
    lens = registry[norm]
    if lens.size == 1 then length = lens.first
    elsif lens.size > 1 then why = "registry length conflict #{lens.to_a.sort.join('/')}'"; conf = 'medium'
    end
  elsif (np = NOTE_PATTERNS.find { |re, _| raw.strip =~ re })
    kind = 'note'; norm = note_label(raw.strip); conf = 'high'; why = np[1]
  elsif raw =~ /\b(training|drill|tour|event|day|reception|open house)\b/i
    kind = 'event'; norm = raw.strip; conf = 'low'; why = 'event keyword, not curated'
  elsif raw =~ /\b(repair|maintenance|closed|rebuild|replacement|work|test|inspection)\b/i
    kind = 'closure'; norm = raw.strip; conf = 'low'; why = 'closure keyword, not curated'
  else
    kind = 'other'; norm = raw.strip; conf = 'low'; why = 'no rule matched'
  end
  rows << [raw, n, kind, norm, prefix, length, conf, why]
end

CSV.open(File.join(A, 'value_taxonomy.csv'), 'w') do |csv|
  csv << %w[raw_value occurrences kind normalized_name type_prefix length_ft confidence rationale]
  rows.each { |r| csv << r }
end

# ---------------------------------------------------------------- stats to stdout
by_kind = Hash.new { |h, k| h[k] = [0, 0] }
rows.each { |r| by_kind[r[2]][0] += 1; by_kind[r[2]][1] += r[1] }
puts "kind\tdistinct\toccurrences"
by_kind.sort.each { |k, (d, o)| puts "#{k}\t#{d}\t#{o}" }
vraw = rows.select { |r| r[2] == 'vessel' }
puts "vessels raw distinct: #{vraw.size}; after normalization: #{vraw.map { |r| r[3] }.uniq.size}"
puts "low confidence rows: #{rows.count { |r| r[6] == 'low' }}"
rows.select { |r| r[6] != 'high' }.each { |r| puts "  #{r[6]}\t#{r[0]}\t-> #{r[2]} / #{r[3]} (#{r[7]})" }
puts "with length: #{rows.count { |r| r[5] }}"
