y, a, b = ARGV[0], ARGV[1].to_i, ARGV[2].to_i
rows = File.readlines("#{y}.tsv").map{|l| l.chomp("\n").split("\t",-1)}
st = File.readlines("#{y}.styles.tsv").map{|l| l.chomp("\n").split("\t",-1)}
styles = {}; borders={}
File.readlines("_styles.tsv").drop(1).each{|l| f=l.chomp.split("\t",-1); styles[f[0]] = f[4].to_s }
File.readlines("_borders.tsv").drop(1).each{|l| f=l.chomp.split("\t",-1); borders[f[0]] = f[2].to_s }
codes = {}; 
def cn(i); s=""; n=i; while n>0; n-=1; s=(65+n%26).chr+s; n/=26; end; s; end
(a..b).each do |r|
  row = rows[r-1] || []; srow = st[r-1] || []
  n = [row.size, srow.size].max
  out = (1...n).map do |i|
    f = styles[srow[i].to_s].to_s.sub(/\|bg=.*/,'').sub('solid|fg=','').gsub('"','').strip
    f = '.' if f == 'none|fg=' || f.empty?
    codes[f] ||= (codes.size).to_s(36).upcase
    code = f=='.' ? '.' : codes[f]
    bd = borders[srow[i].to_s].to_s
    v = row[i].to_s
    "#{cn(i+1)}#{code}#{bd.empty? ? '' : '#'}#{v.empty? ? '' : '='+v[0,14]}"
  end
  puts "R#{r} A=#{row[0].to_s[0,22]} | #{out.join(' ')}"
end
puts "codes: " + codes.map{|k,v| "#{v}=#{k}"}.join("  ")
