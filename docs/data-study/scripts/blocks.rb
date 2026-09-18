MON=/\A(january|february|march|april|may|june|july|august|september|october|november|december)\b/i
BERTH=/\A(North Pier|Inner Channel|South Float|North Finger|Small craft)/
def cn(i); s=""; n=i; while n>0; n-=1; s=(65+n%26).chr+s; n/=26; end; s; end
(1997..2019).each do |y|
  rows = File.readlines("#{y}.tsv").map{|l| l.chomp("\n").split("\t",-1)}
  hdrs = rows.each_index.select{|i| rows[i][0].to_s =~ MON}
  hdrs.each_with_index do |h, k|
    stop = hdrs[k+1] || rows.size
    # find day-number row: header row or one of next 2 rows containing a cell == "1" or formula
    dayrow=nil; d1col=nil; ndays=nil
    (h..h+2).each do |r|
      row = rows[r] || []
      idx = row.each_index.find{|c| c>0 && row[c]=="1"}
      if idx
        dayrow=r; d1col=idx
        # count consecutive numeric/formula cells from idx
        n=0; c=idx
        while c<row.size && (row[c]=~/\A\d+\z/ || row[c].to_s.start_with?("="))
          n+=1; c+=1
        end
        ndays=n; break
      end
    end
    mins=[]; maxs=[]; left=0; right=0; tot=0; unl=0; unl_cells=0
    (h+1...stop).each do |r|
      row=rows[r]||[]
      a=row[0].to_s
      next if r==dayrow
      isb = a=~BERTH
      next if !isb && !a.empty?
      vals = row.each_index.select{|c| c>0 && !row[c].to_s.empty? && !(row[c]=~/\A\d+\z/) && !row[c].start_with?("=") && !(row[c]=~/\A(F|S|M|T|W|TR)\z/)}
      next if vals.empty?
      if !isb then unl+=1; unl_cells+=vals.size; next end
      tot+=vals.size
      mins<<vals.min; maxs<<vals.max
      vals.each{|c| left+=1 if d1col && c<d1col; right+=1 if d1col && c>d1col+ndays-1}
    end
    printf "%s %-15s hdr=R%-3d dayrow=%s d1=%s(%s) nd=%s berthcells=%d colrange=%s-%s leftOf1=%d beyond=%d unlabeledRows=%d(%d cells)\n", y, rows[h][0], h+1, dayrow ? "R#{dayrow+1}" : "-", d1col ? cn(d1col+1) : "-", d1col.to_s, ndays.to_s, tot, mins.min ? cn(mins.min+1) : "-", maxs.max ? cn(maxs.max+1) : "-", left, right, unl, unl_cells
  end
end
