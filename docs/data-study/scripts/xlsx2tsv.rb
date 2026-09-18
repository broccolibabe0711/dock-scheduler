#!/usr/bin/ruby
require 'fileutils'
src, out = ARGV
FileUtils.mkdir_p(out)
def unesc(s); s.to_s.gsub('&lt;','<').gsub('&gt;','>').gsub('&quot;','"').gsub('&apos;',"'").gsub('&#10;',' ').gsub('&amp;','&'); end
def col2num(c); n=0; c.each_char{|ch| n=n*26+(ch.ord-64)}; n; end
wb = File.read("#{src}/xl/workbook.xml")
rels = File.read("#{src}/xl/_rels/workbook.xml.rels")
rid2file = {}
rels.scan(/<Relationship ([^>]*?)\/>/) { |a| a=a[0]; id=a[/Id="([^"]+)"/,1]; t=a[/Target="([^"]+)"/,1]; rid2file[id]=t if id&&t }
sheets = []
wb.scan(/<sheet ([^>]*?)\/>/) { |a| a=a[0]; sheets << [a[/name="([^"]+)"/,1], rid2file[a[/r:id="([^"]+)"/,1]]] }
st = File.read("#{src}/xl/styles.xml")
fills = st[/<fills[^>]*>(.*?)<\/fills>/m, 1].to_s.scan(/<fill\s*\/>|<fill>(.*?)<\/fill>/m).map { |x| x[0].to_s }
fonts = st[/<fonts[^>]*>(.*?)<\/fonts>/m, 1].to_s.scan(/<font\s*\/>|<font>(.*?)<\/font>/m).map { |x| x[0].to_s }
numfmts = {}
st.scan(/<numFmt ([^>]*?)\/>/) { |a| a=a[0]; numfmts[a[/numFmtId="(\d+)"/,1]] = unesc(a[/formatCode="([^"]*)"/,1]) }
xfs = st[/<cellXfs[^>]*>(.*?)<\/cellXfs>/m, 1].to_s.scan(/<xf ([^>]*?)\/?>/).map { |x| x[0] }
def fillsum(f)
  return 'none' if f.empty?
  pt = f[/patternType="([^"]+)"/,1] || 'none'
  fg = f[/<fgColor ([^>]*?)\/>/,1]; bg = f[/<bgColor ([^>]*?)\/>/,1]
  "#{pt}|fg=#{fg}|bg=#{bg}"
end
File.open("#{out}/_styles.tsv",'w') do |o|
  o.puts %w[xf numFmtId numFmt fillId fill fontId font].join("\t")
  xfs.each_with_index do |a,i|
    nf = a[/numFmtId="(\d+)"/,1]; fi = a[/fillId="(\d+)"/,1].to_i; fo = a[/fontId="(\d+)"/,1].to_i
    font = fonts[fo].to_s
    fs = [font[/<b\s*\/>/] ? 'B' : nil, font[/<i\s*\/>/] ? 'I' : nil, font[/<color ([^>]*?)\/>/,1]].compact.join(',')
    o.puts [i, nf, numfmts[nf].to_s, fi, fillsum(fills[fi].to_s), fo, fs].join("\t")
  end
end
puts "fills=#{fills.size} fonts=#{fonts.size} xfs=#{xfs.size} numfmts=#{numfmts.size}"
sheets.each do |name, file|
  xml = File.read(file.start_with?("/") ? "#{src}#{file}" : "#{src}/xl/#{file}")
  grid = {}; sgrid = {}; maxc = 0; maxr = 0
  xml.scan(/<c r="([A-Z]+)(\d+)"([^>]*?)(?:\/>|>(.*?)<\/c>)/m) do |col, row, attrs, inner|
    r = row.to_i; c = col2num(col)
    s = attrs[/s="(\d+)"/,1]; t = attrs[/t="(\w+)"/,1]
    val = nil
    if inner
      if t == 'inlineStr'
        val = inner.scan(/<t[^>]*>(.*?)<\/t>/m).map { |x| unesc(x[0]) }.join
      else
        v = inner[/<v>(.*?)<\/v>/m, 1]; f = inner[/<f[^>]*>(.*?)<\/f>/m, 1]
        if v && !v.empty? then val = unesc(v) elsif f then val = '=' + unesc(f) end
      end
    end
    next if val.nil? && s.nil?
    (grid[r] ||= {})[c] = val if val
    (sgrid[r] ||= {})[c] = s if s
    maxc = c if c > maxc; maxr = r if r > maxr
  end
  safe = name.gsub(/[^\w\- ]/,'_')
  File.open("#{out}/#{safe}.tsv",'w') { |o| (1..maxr).each { |r| o.puts (1..maxc).map { |c| (grid[r]||{})[c].to_s.gsub(/[\t\n\r]/,' ') }.join("\t") } }
  File.open("#{out}/#{safe}.styles.tsv",'w') { |o| (1..maxr).each { |r| o.puts (1..maxc).map { |c| (sgrid[r]||{})[c].to_s }.join("\t") } }
  puts "#{name}: #{maxr} rows x #{maxc} cols, #{grid.values.map(&:size).sum} values"
end
