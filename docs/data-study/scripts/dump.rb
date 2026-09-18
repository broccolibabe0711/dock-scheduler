y, a, b = ARGV[0], ARGV[1].to_i, ARGV[2].to_i
rows = File.readlines("#{y}.tsv").map{|l| l.chomp("\n").split("\t",-1)}
st = File.readlines("#{y}.styles.tsv").map{|l| l.chomp("\n").split("\t",-1)}
styles = {}
File.readlines("_styles.tsv").drop(1).each{|l| f=l.chomp.split("\t",-1); styles[f[0]] = f[4].to_s.sub(/\|bg=.*/,'').sub('solid|fg=indexed=','S').gsub('"','').strip }
def cn(i); s=""; n=i; while n>0; n-=1; s=(65+n%26).chr+s; n/=26; end; s; end
(a..b).each do |r|
  row = rows[r-1] || []; srow = st[r-1] || []
  cells = row.each_with_index.select{|v,i| !v.to_s.empty?}.map{|v,i| "#{cn(i+1)}=#{v}#{ENV['ST'] ? "{#{styles[srow[i]]}}" : ''}"}
  puts "R#{r}: #{cells.join(' | ')}"
end
