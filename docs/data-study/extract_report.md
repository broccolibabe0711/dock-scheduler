# Dock schedule extraction report

Generated 2026-09-18 16:06 by `extract_bookings.rb`. Output: `bookings.csv` (2244 records from 23 year sheets), `unlabeled_cells.csv` (334 text cells found in rows without a berth label), `summary_comparison.csv`.

## 1. Per-sheet extraction statistics

Candidate = non-empty, non-formula, non-numeric cell in a labelled berth/group row (columns B onward). Records < candidates only when adjacent identical cells were collapsed (`repeat`).

| sheet | blocks | candidates | records | merge | fill_run | repeat | single | outside day cols | bare numbers skipped | unlabeled-row text cells | header junk |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1997 | 5 | 33 | 33 | 0 | 25 | 0 | 8 | 0 | 0 | 1 | 0 |
| 1998 | 12 | 73 | 73 | 0 | 65 | 0 | 8 | 0 | 0 | 0 | 0 |
| 1999 | 12 | 65 | 65 | 0 | 44 | 0 | 21 | 0 | 0 | 0 | 0 |
| 2000 | 12 | 80 | 80 | 1 | 56 | 1 | 22 | 0 | 0 | 0 | 0 |
| 2001 | 12 | 106 | 106 | 0 | 51 | 2 | 53 | 0 | 0 | 0 | 0 |
| 2002 | 13 | 150 | 150 | 0 | 71 | 7 | 72 | 0 | 0 | 9 | 0 |
| 2003 | 13 | 109 | 109 | 0 | 67 | 6 | 36 | 0 | 0 | 5 | 0 |
| 2004 | 13 | 85 | 85 | 0 | 58 | 0 | 27 | 0 | 0 | 0 | 0 |
| 2005 | 12 | 70 | 70 | 0 | 51 | 0 | 19 | 0 | 0 | 1 | 0 |
| 2006 | 12 | 58 | 58 | 0 | 40 | 1 | 17 | 0 | 0 | 3 | 0 |
| 2007 | 12 | 56 | 56 | 0 | 47 | 0 | 9 | 0 | 0 | 0 | 0 |
| 2008 | 12 | 50 | 50 | 0 | 38 | 0 | 12 | 0 | 0 | 2 | 0 |
| 2009 | 12 | 97 | 97 | 35 | 13 | 8 | 41 | 1 | 0 | 1 | 0 |
| 2010 | 12 | 167 | 167 | 80 | 16 | 6 | 65 | 2 | 1 | 77 | 12 |
| 2011 | 12 | 169 | 169 | 64 | 7 | 13 | 85 | 14 | 0 | 43 | 0 |
| 2012 | 12 | 62 | 62 | 38 | 4 | 0 | 20 | 10 | 0 | 19 | 0 |
| 2013 | 12 | 120 | 120 | 58 | 13 | 3 | 46 | 14 | 0 | 44 | 0 |
| 2014 | 12 | 143 | 143 | 65 | 8 | 4 | 66 | 15 | 0 | 23 | 0 |
| 2015 | 12 | 133 | 133 | 58 | 11 | 3 | 61 | 8 | 0 | 22 | 0 |
| 2016 | 12 | 143 | 143 | 85 | 11 | 0 | 47 | 3 | 0 | 30 | 0 |
| 2017 | 12 | 136 | 136 | 59 | 15 | 3 | 59 | 4 | 0 | 15 | 0 |
| 2018 | 12 | 86 | 86 | 34 | 18 | 0 | 34 | 4 | 0 | 27 | 0 |
| 2019 | 12 | 53 | 53 | 30 | 4 | 0 | 19 | 3 | 0 | 12 | 0 |
| **all** | 272 | 2244 | 2244 | 607 | 733 | 57 | 847 | 78 | 1 | 334 | 12 |

### Blocks found per sheet (label [day-1 column, days in header])

- **1997**: AUGUST 1997 [day1=B, 31d]; SEPTEMBER 1997 [day1=B, 30d]; OCTOBER 1997 [day1=B, 31d]; NOVEMBER 1997 [day1=B, 30d]; DECEMBER 1997 [day1=B, 31d]
- **1998**: JANUARY 1998 [day1=B, 31d]; FEBRUARY 1998 [day1=B, 28d]; MARCH 1998 [day1=B, 31d]; APRIL 1998 [day1=B, 30d]; MAY 1998 [day1=B, 31d]; JUNE 1998 [day1=B, 30d]; JULY 1998 [day1=B, 31d]; AUGUST 1998 [day1=B, 31d]; SEPTEMBER 1998 [day1=B, 30d]; OCTOBER 1998 [day1=B, 31d]; NOVEMBER 1998 [day1=B, 30d]; DECEMBER 1998 [day1=B, 31d]
- **1999**: JANUARY 1999 [day1=B, 31d]; FEBRUARY 1999 [day1=B, 28d]; MARCH 1999 [day1=B, 31d]; APRIL 1999 [day1=B, 30d]; MAY 1999 [day1=B, 31d]; JUNE 1999 [day1=B, 30d]; JULY 1999 [day1=B, 31d]; AUGUST 1999 [day1=B, 31d]; SEPTEMBER 1999 [day1=B, 30d]; OCTOBER 1999 [day1=B, 31d]; NOVEMBER 1999 [day1=B, 30d]; DECEMBER 1999 [day1=B, 31d]
- **2000**: JANUARY 2000 [day1=B, 31d]; FEBRUARY 2000 [day1=B, 29d]; MARCH 2000 [day1=B, 31d]; APRIL 2000 [day1=B, 30d]; MAY 2000 [day1=B, 31d]; JUNE 2000 [day1=B, 30d]; JULY 2000 [day1=B, 31d]; AUGUST 2000 [day1=B, 31d]; SEPTEMBER 2000 [day1=B, 30d]; OCTOBER 2000 [day1=B, 31d]; NOVEMBER 2000 [day1=B, 30d]; DECEMBER 2000 [day1=B, 31d]
- **2001**: JANUARY 2001 [day1=B, 31d]; FEBRUARY 2001 [day1=B, 28d]; MARCH 2001 [day1=B, 31d]; APRIL 2001 [day1=B, 30d]; MAY 2001 [day1=B, 31d]; JUNE 2001 [day1=B, 30d]; JULY 2001 [day1=B, 31d]; AUGUST 2001 [day1=B, 31d]; SEPTEMBER 2001 [day1=B, 30d]; OCTOBER 2001 [day1=B, 31d]; NOVEMBER 2001 [day1=B, 30d]; DECEMBER 2001 [day1=B, 31d]
- **2002**: DECEMBER 2001 [day1=B, 31d]; JANUARY 2002 [day1=B, 31d]; FEBRUARY 2002 [day1=B, 28d]; MARCH 2002 [day1=B, 31d]; APRIL 2002 [day1=B, 30d]; MAY 2002 [day1=B, 31d]; JUNE 2002 [day1=B, 30d]; JULY 2002 [day1=B, 31d]; AUGUST 2002 [day1=B, 31d]; SEPTEMBER 2002 [day1=B, 30d]; OCTOBER 2002 [day1=B, 31d]; NOVEMBER 2002 [day1=B, 30d]; DECEMBER 2002 [day1=B, 31d]
- **2003**: DECEMBER 2002 [day1=B, 31d]; JANUARY 2003 [day1=B, 31d]; FEBRUARY 2003 [day1=B, 28d]; MARCH 2003 [day1=B, 31d]; APRIL 2003 [day1=B, 30d]; MAY 2003 [day1=B, 31d]; JUNE 2003 [day1=B, 30d]; JULY 2003 [day1=B, 31d]; AUGUST 2003 [day1=B, 31d]; SEPTEMBER 2003 [day1=B, 30d]; OCTOBER 2003 [day1=B, 31d]; NOVEMBER 2003 [day1=B, 30d]; DECEMBER 2003 [day1=B, 31d]
- **2004**: DECEMBER 2003 [day1=B, 31d]; JANUARY 2004 [day1=B, 31d]; FEBRUARY 2004 [day1=B, 29d]; MARCH 2004 [day1=B, 31d]; APRIL 2004 [day1=B, 30d]; MAY 2004 [day1=B, 31d]; JUNE 2004 [day1=B, 30d]; JULY 2004 [day1=B, 31d]; AUGUST 2004 [day1=B, 31d]; SEPTEMBER 2004 [day1=B, 30d]; OCTOBER 2004 [day1=B, 31d]; NOVEMBER 2004 [day1=B, 30d]; DECEMBER 2004 [day1=B, 31d]
- **2005**: JANUARY 2005 [day1=B, 31d]; FEBRUARY 2005 [day1=B, 28d]; MARCH 2005 [day1=B, 31d]; APRIL 2005 [day1=B, 30d]; MAY 2005 [day1=B, 31d]; JUNE 2005 [day1=B, 30d]; JULY 2005 [day1=B, 31d]; AUGUST 2005 [day1=B, 31d]; SEPTEMBER 2005 [day1=B, 30d]; OCTOBER 2005 [day1=B, 31d]; NOVEMBER 2005 [day1=B, 30d]; DECEMBER 2005 [day1=B, 31d]
- **2006**: JANUARY 2006 [day1=B, 31d]; FEBRUARY 2006 [day1=B, 28d]; MARCH 2006 [day1=B, 31d]; APRIL 2006 [day1=B, 30d]; MAY 2006 [day1=B, 31d]; JUNE 2006 [day1=B, 30d]; JULY 2006 [day1=B, 31d]; AUGUST 2006 [day1=B, 31d]; SEPTEMBER 2006 [day1=B, 30d]; OCTOBER 2006 [day1=B, 31d]; NOVEMBER 2006 [day1=B, 30d]; DECEMBER 2006 [day1=B, 31d]
- **2007**: JANUARY 2007 [day1=B, 31d]; FEBRUARY 2007 [day1=B, 28d]; MARCH 2007 [day1=B, 31d]; APRIL 2007 [day1=B, 30d]; MAY 2007 [day1=B, 31d]; JUNE 2007 [day1=B, 30d]; JULY 2007 [day1=B, 31d]; AUGUST 2007 [day1=B, 31d]; SEPTEMBER 2007 [day1=B, 30d]; OCTOBER 2007 [day1=B, 31d]; NOVEMBER 2007 [day1=B, 30d]; DECEMBER 2007 [day1=B, 31d]
- **2008**: JANUARY 2008 [day1=B, 31d]; FEBRUARY 2008 [day1=B, 29d]; MARCH 2008 [day1=B, 31d]; APRIL 2008 [day1=B, 30d]; MAY 2008 [day1=B, 31d]; JUNE 2008 [day1=B, 31d]; JULY 2008 [day1=B, 31d]; AUGUST 2008 [day1=B, 31d]; SEPTEMBER 2008 [day1=B, 30d]; OCTOBER 2008 [day1=B, 31d]; NOVEMBER 2008 [day1=B, 30d]; DECEMBER 2008 [day1=B, 31d]
- **2009**: JANUARY 2009 [day1=B, 31d]; FEBRUARY 2009 [day1=B, 29d]; MARCH 2009 [day1=B, 31d]; APRIL 2009 [day1=B, 30d]; MAY 2009 [day1=B, 31d]; JUNE 2009 [day1=B, 30d]; JULY 2009 [day1=B, 31d]; AUGUST 2009 [day1=B, 31d]; SEPTEMBER 2009 [day1=B, 30d]; OCTOBER 2009 [day1=B, 31d]; NOVEMBER 2009 [day1=B, 30d]; DECEMBER 2009 [day1=B, 31d]
- **2010**: JANUARY 2010 [day1=E, 31d]; FEBRUARY 2010 [day1=B, 28d]; MARCH 2010 [day1=B, 31d]; APRIL 2010 [day1=B, 30d]; MAY 2010 [day1=B, 31d]; JUNE 2010 [day1=B, 30d]; JULY 2010 [day1=B, 31d]; AUGUST 2010 [day1=B, 31d]; SEPTEMBER 2010 [day1=B, 30d]; OCTOBER 2010 [day1=B, 31d]; NOVEMBER 2018 [day1=C, 30d]; DECEMBER 2018 [day1=B, 31d]
- **2011**: JANUARY 2011 [day1=F, 31d]; FEBRUARY 2011 [day1=C, 28d]; MARCH 2011 [day1=C, 29d]; APRIL 2011 [day1=C, 30d]; MAY 2011 [day1=C, 31d]; JUNE 2011 [day1=C, 30d]; JULY 2011 [day1=C, 31d]; AUGUST 2011 [day1=C, 31d]; SEPTEMBER 2011 [day1=C, 30d]; OCTOBER 2011 [day1=C, 31d]; NOVEMBER 2011 [day1=C, 30d]; DECEMBER 2011 [day1=C, 31d]
- **2012**: JANUARY 2012 [day1=G, 30d]; FEBRUARY 2012 [day1=D, 29d]; MARCH 2012 [day1=E, 31d]; APRIL 2012 [day1=E, 30d]; MAY 2012 [day1=E, 31d]; JUNE 2012 [day1=E, 30d]; JULY 2012 [day1=E, 31d]; AUGUST 2012 [day1=E, 31d]; SEPTEMBER 2012 [day1=E, 30d]; OCTOBER 2012 [day1=E, 31d]; NOVEMBER 2012 [day1=E, 30d]; DECEMBER 2012 [day1=E, 31d]
- **2013**: JANUARY 2013 [day1=B, 31d]; FEBRUARY 2013 [day1=F, 28d]; MARCH 2013 [day1=F, 29d]; APRIL 2013 [day1=F, 30d]; MAY 2013 [day1=F, 31d]; JUNE 2013 [day1=F, 30d]; JULY 2013 [day1=F, 31d]; AUGUST 2013 [day1=F, 31d]; SEPTEMBER 2013 [day1=F, 30d]; OCTOBER 2013 [day1=F, 31d]; NOVEMBER 2013 [day1=F, 30d]; DECEMBER 2013 [day1=F, 31d]
- **2014**: January [day1=C, 31d]; February [day1=G, 28d]; March [day1=G, 31d]; April [day1=G, 30d]; May [day1=G, 31d]; June [day1=G, 30d]; July [day1=G, 31d]; August [day1=G, 31d]; September [day1=G, 30d]; October [day1=G, 31d]; November [day1=G, 30d]; December [day1=G, 31d]
- **2015**: January [day1=D, 31d]; February [day1=H, 28d]; March [day1=H, 31d]; April [day1=H, 30d]; May [day1=H, 31d]; June [day1=H, 30d]; July [day1=H, 31d]; August [day1=H, 31d]; September [day1=H, 30d]; October [day1=H, 31d]; November [day1=H, 30d]; December [day1=H, 31d]
- **2016**: January [day1=C, 31d]; February [day1=C, 29d]; March [day1=C, 31d]; April [day1=C, 30d]; May [day1=C, 31d]; June [day1=C, 30d]; July [day1=C, 31d]; August [day1=C, 31d]; September [day1=C, 30d]; October [day1=C, 31d]; November [day1=C, 30d]; December [day1=C, 31d]
- **2017**: January [day1=C, 31d]; February [day1=C, 28d]; March [day1=C, 31d]; April [day1=C, 30d]; May [day1=C, 31d]; June [day1=C, 30d]; July [day1=C, 31d]; August [day1=C, 31d]; September [day1=C, 30d]; October [day1=C, 31d]; November [day1=C, 30d]; December [day1=C, 31d]
- **2018**: January [day1=C, 31d]; February [day1=C, 28d]; March [day1=C, 31d]; April [day1=C, 30d]; May [day1=C, 31d]; June [day1=C, 30d]; July [day1=C, 31d]; August [day1=C, 31d]; September [day1=C, 30d]; October [day1=C, 31d]; November [day1=C, 30d]; December [day1=C, 31d]
- **2019**: January [day1=C, 31d]; February [day1=C, 28d]; March [day1=C, 31d]; April [day1=C, 30d]; May [day1=C, 31d]; June [day1=C, 30d]; July [day1=C, 31d]; August [day1=C, 31d]; September [day1=C, 30d]; October [day1=C, 31d]; November [day1=C, 30d]; December [day1=C, 31d]

## 2. Usage-days comparison against the 8YR Dock Summary (block_year 2006-2013)

Values are per `berth_name` (label without the length) and `block_year`, counting only records with valid dates. Interpretations:
- A: sum span_days (merge+fill_run+repeat+single)
- B: merges count span, everything else 1 day
- C: one day per record (ignore spans)
- D: merge+repeat spans, fill_run = 1 day
- E: distinct calendar days occupied (union of A)

| berth | year | summary | A | B | C | D | E |
|---|---|---|---|---|---|---|---|
| North Pier West | 2006 | 127 | 128 | 24 | 24 | 24 | 128 |
| North Pier West | 2007 | 219 | 365 | 12 | 12 | 12 | 365 |
| North Pier West | 2008 | 116 | 196 | 21 | 21 | 21 | 196 |
| North Pier West | 2009 | 193 | 135 | 104 | 21 | 104 | 135 |
| North Pier West | 2010 | 136 | 154 | 115 | 30 | 116 | 154 |
| North Pier West | 2011 | 337 | 141 | 139 | 28 | 139 | 141 |
| North Pier West | 2012 | 648 | 185 | 182 | 21 | 182 | 185 |
| North Pier West | 2013 | 470 | 213 | 155 | 23 | 155 | 213 |
| North Pier Face | 2006 | 0 | 7 | 2 | 2 | 2 | 7 |
| North Pier Face | 2007 | 3 | 4 | 3 | 3 | 3 | 4 |
| North Pier Face | 2008 | 3 | 4 | 3 | 3 | 3 | 4 |
| North Pier Face | 2009 | 16 | 31 | 13 | 8 | 13 | 31 |
| North Pier Face | 2010 | 29 | 45 | 18 | 13 | 18 | 45 |
| North Pier Face | 2011 | 6 | 46 | 13 | 12 | 14 | 46 |
| North Pier Face | 2012 | 3 | 12 | 5 | 4 | 5 | 12 |
| North Pier Face | 2013 | 21 | 33 | 19 | 10 | 19 | 33 |
| North Pier East | 2006 | 85 | 89 | 14 | 14 | 17 | 89 |
| North Pier East | 2007 | 176 | 179 | 29 | 29 | 29 | 179 |
| North Pier East | 2008 | 51 | 47 | 14 | 14 | 14 | 47 |
| North Pier East | 2009 | 36 | 60 | 44 | 15 | 45 | 60 |
| North Pier East | 2010 | 112 | 79 | 76 | 30 | 76 | 79 |
| North Pier East | 2011 | 85 | 72 | 72 | 46 | 72 | 72 |
| North Pier East | 2012 | 78 | 62 | 54 | 13 | 54 | 62 |
| North Pier East | 2013 | 631 | 201 | 185 | 23 | 185 | 201 |
| North Finger Piers | 2006 | 348 | 0 | 0 | 0 | 0 | 0 |
| North Finger Piers | 2007 | 431 | 0 | 0 | 0 | 0 | 0 |
| North Finger Piers | 2008 | 298 | 0 | 0 | 0 | 0 | 0 |
| North Finger Piers | 2009 | 434 | 0 | 0 | 0 | 0 | 0 |
| North Finger Piers | 2010 | 363 | 0 | 0 | 0 | 0 | 0 |
| North Finger Piers | 2011 | 415 | 0 | 0 | 0 | 0 | 0 |
| North Finger Piers | 2012 | 511 | 0 | 0 | 0 | 0 | 0 |
| North Finger Piers | 2013 | 334 | 0 | 0 | 0 | 0 | 0 |
| Marsh Landing | 2006 | 64 | 0 | 0 | 0 | 0 | 0 |
| Marsh Landing | 2007 | 118 | 0 | 0 | 0 | 0 | 0 |
| Marsh Landing | 2008 | 67 | 0 | 0 | 0 | 0 | 0 |
| Marsh Landing | 2009 | 88 | 0 | 0 | 0 | 0 | 0 |
| Marsh Landing | 2010 | 89 | 0 | 0 | 0 | 0 | 0 |
| Marsh Landing | 2011 | 118 | 0 | 0 | 0 | 0 | 0 |
| Marsh Landing | 2012 | 116 | 0 | 0 | 0 | 0 | 0 |
| Marsh Landing | 2013 | 120 | 0 | 0 | 0 | 0 | 0 |
| South Float West | 2006 | 3 | 4 | 3 | 3 | 3 | 4 |
| South Float West | 2007 | 1 | 32 | 2 | 2 | 2 | 32 |
| South Float West | 2008 | 5 | 96 | 4 | 4 | 4 | 96 |
| South Float West | 2009 | 23 | 17 | 13 | 8 | 17 | 17 |
| South Float West | 2010 | 66 | 101 | 94 | 40 | 101 | 101 |
| South Float West | 2011 | 67 | 71 | 54 | 45 | 71 | 71 |
| South Float West | 2012 | 26 | 23 | 23 | 5 | 23 | 23 |
| South Float West | 2013 | 37 | 108 | 75 | 29 | 77 | 108 |
| South Float East | 2006 | 12 | 23 | 9 | 9 | 9 | 23 |
| South Float East | 2007 | 25 | 35 | 10 | 10 | 10 | 35 |
| South Float East | 2008 | 20 | 25 | 7 | 7 | 7 | 25 |
| South Float East | 2009 | 113 | 82 | 70 | 36 | 79 | 82 |
| South Float East | 2010 | 74 | 115 | 115 | 20 | 115 | 115 |
| South Float East | 2011 | 17 | 64 | 58 | 15 | 58 | 64 |
| South Float East | 2012 | 138 | 109 | 109 | 8 | 109 | 109 |
| South Float East | 2013 | 62 | 85 | 84 | 19 | 85 | 85 |

Total absolute deviation from the summary (lower is better), all rows / only the six grid berths:

- A: sum span_days (merge+fill_run+repeat+single): all rows 6200, grid berths only 2286, exact matches 0/56
- B: merges count span, everything else 1 day: all rows 6518, grid berths only 2604, exact matches 3/56
- C: one day per record (ignore spans): all rows 7525, grid berths only 3611, exact matches 3/56
- D: merge+repeat spans, fill_run = 1 day: all rows 6504, grid berths only 2590, exact matches 3/56
- E: distinct calendar days occupied (union of A): all rows 6200, grid berths only 2286, exact matches 0/56

**Best-fitting interpretation on the grid berths: A: sum span_days (merge+fill_run+repeat+single)** -- but see the discussion below; no interpretation reproduces the summary.

Summary rows with no matching grid row label in any year sheet: 'Marsh Landing'. 'North Finger Piers' first appears as a grid row label in 2014, so its 2006-2013 summary values (298-511 days/yr) cannot come from these grids at all.

## 3. Overlapping records on the same berth (candidate legacy double-bookings)

Pairs of records with the same `sheet_year` and `berth_label`, valid dates, and overlapping [start_date, end_date]: **5 pairs**.

| sheet | berth | A: value | A: dates (row/col, source) | B: value | B: dates (row/col, source) |
|---|---|---|---|---|---|
| 1998 | North Pier West - 410' | Barge Salt Dory | 1998-09-14..1998-09-20 (R93/O, fill_run) | OSV Wild Star | 1998-09-16..1998-09-21 (R92/Q, fill_run) |
| 1998 | North Pier West - 410' | Tug Blue Fathom | 1998-09-24..1998-09-26 (R93/Y, fill_run) | OSV Wild Star | 1998-09-25..1998-09-27 (R92/Z, fill_run) |
| 2017 | South Float East - 90' | OSV AMBER REEF | 2017-07-09..2017-07-18 (R85/K, merge) | Utility work on pier face | 2017-07-11..2017-07-15 (R88/M, fill_run) |
| 2017 | South Float East - 90' | R/V Blue Star | 2017-09-07..2017-09-12 (R110/I, fill_run) | ETD PM | 2017-09-09..2017-09-10 (R113/K, fill_run) |
| 2017 | Small craft slips (institution boats) | R/V Silver Petrel | 2017-09-01..2017-09-10 (R114/C, merge) | M/V HIGH COVE | 2017-09-04..2017-09-08 (R112/F, merge) |

Overlap pairs by span-source combination: fill_run+fill_run=3, fill_run+merge=1, merge+merge=1

Overlap pairs by cause: different rows with the same label=5. Within a single row a span can never run past another value (fill runs and repeats stop at the next non-empty cell, merges cannot contain values), so overlaps arise only from duplicated berth rows inside one block.

## 4. Anomalies

### block_year_differs_from_sheet (5)

- 2002: block 'DECEMBER 2001' (row 1) labelled year 2001 on the 2002 sheet
- 2003: block 'DECEMBER 2002' (row 1) labelled year 2002 on the 2003 sheet
- 2004: block 'DECEMBER 2003' (row 5) labelled year 2003 on the 2004 sheet
- 2010: block 'NOVEMBER 2018' (row 117) labelled year 2018 on the 2010 sheet
- 2010: block 'DECEMBER 2018' (row 128) labelled year 2018 on the 2010 sheet

### merge_beyond_month (3)

- 2009: merge AD63:AF63 ('M/V NORTHERN HARBOR', block 'JUNE 2009') extends 1 col(s) past the last day column AE; clamped
- 2014: merge B8:AJ8 ('R/V GOLDEN COMPASS', block 'January') extends 3 col(s) past the last day column AG; clamped
- 2016: merge AF23:AG23 ('Touch and go', block 'February') extends 2 col(s) past the last day column AE; clamped

### multi_row_merge (1)

- 2014: merge G124:T125 spans 2 rows

### day_row_does_not_start_at_1 (2)

- 2010: block 'NOVEMBER 2018' day numbers run 7..30 (row 117); day-1 column inferred as C
- 2010: block 'DECEMBER 2018' day numbers run 7..31 (row 128); day-1 column inferred as B

### header_days_ne_calendar (5)

- 2008: block 'JUNE 2008' header lists 31 days, calendar has 30
- 2009: block 'FEBRUARY 2009' header lists 29 days, calendar has 28
- 2011: block 'MARCH 2011' header lists 29 days, calendar has 31
- 2012: block 'JANUARY 2012' header lists 30 days, calendar has 31
- 2013: block 'MARCH 2013' header lists 29 days, calendar has 31

### values_in_header_or_weekday_row (12)

- 2010: row 117 col C = 'F/V GREY STRAND' (block 'NOVEMBER 2018')
- 2010: row 117 col D = 'M/V SILVER HORIZON' (block 'NOVEMBER 2018')
- 2010: row 117 col E = 'OSV CLEAR OSPREY' (block 'NOVEMBER 2018')
- 2010: row 117 col F = 'OSV CLEAR OSPREY' (block 'NOVEMBER 2018')
- 2010: row 117 col G = 'R/V CLEAR HARBOR' (block 'NOVEMBER 2018')
- 2010: row 117 col H = 'Barge SWIFT HARBOR' (block 'NOVEMBER 2018')
- 2010: row 128 col B = 'OSV CLEAR OSPREY' (block 'DECEMBER 2018')
- 2010: row 128 col C = 'OSV CLEAR OSPREY' (block 'DECEMBER 2018')
- 2010: row 128 col D = 'R/V CLEAR HARBOR' (block 'DECEMBER 2018')
- 2010: row 128 col E = 'Barge SWIFT HARBOR' (block 'DECEMBER 2018')
- 2010: row 128 col F = 'S/V FAR LANTERN' (block 'DECEMBER 2018')
- 2010: row 128 col G = 'F/V GREY STRAND' (block 'DECEMBER 2018')

### cell_outside_day_columns (78)

- 2009: row 65 col AF 'R/V CORAL TERN' -> day 31 (block 'JUNE 2009' day columns B..AE)
- 2010: row 44 col AF 'R/V Grey Kestrel' -> day 31 (block 'APRIL 2010' day columns B..AE)
- 2010: row 121 col B 'R/V Golden Horizon' -> day 0 (block 'NOVEMBER 2018' day columns C..AF)
- 2011: row 8 col B 'R/V GOLDEN COMPASS' -> day -3 (block 'JANUARY 2011' day columns F..AJ)
- 2011: row 19 col B 'R/V GOLDEN COMPASS' -> day 0 (block 'FEBRUARY 2011' day columns C..AD)
- 2011: row 30 col B 'R/V GOLDEN COMPASS' -> day 0 (block 'MARCH 2011' day columns C..AE)
- 2011: row 41 col B 'R/V GOLDEN COMPASS' -> day 0 (block 'APRIL 2011' day columns C..AF)
- 2011: row 55 col B 'R/V Golden Horizon' -> day 0 (block 'MAY 2011' day columns C..AG)
- 2011: row 65 col B 'M/V GREY COMPASS' -> day 0 (block 'JUNE 2011' day columns C..AF)
- 2011: row 66 col B 'R/V Golden Horizon' -> day 0 (block 'JUNE 2011' day columns C..AF)
- 2011: row 77 col B 'R/V Golden Horizon' -> day 0 (block 'JULY 2011' day columns C..AG)
- 2011: row 85 col B 'R/V Wild Ledge' -> day 0 (block 'AUGUST 2011' day columns C..AG)
- 2011: row 86 col B 'M/V DEEP SOUND' -> day 0 (block 'AUGUST 2011' day columns C..AG)
- 2011: row 112 col B 'R/V Golden Horizon' -> day 0 (block 'OCTOBER 2011' day columns C..AG)
- 2011: row 123 col B 'R/V Golden Horizon' -> day 0 (block 'NOVEMBER 2011' day columns C..AF)
- ... (63 more)

### bare_number_in_berth_row (1)

- 2010: row 120 col AA = 1400 (skipped)

### duplicate_label_rows_in_block (27)

- 1998: 'North Pier West - 410'' on rows 92, 93 (block 'SEPTEMBER 1998')
- 2014: 'Small craft slips (institution boats)' on rows 75, 76 (block 'June')
- 2014: 'Small craft slips (institution boats)' on rows 87, 88 (block 'July')
- 2016: 'Small craft slips (institution boats)' on rows 76, 77 (block 'June')
- 2016: 'Small craft slips (institution boats)' on rows 88, 89 (block 'July')
- 2016: 'Small craft slips (institution boats)' on rows 100, 101 (block 'August')
- 2017: 'South Float East - 90'' on rows 49, 52 (block 'April')
- 2017: 'Small craft slips (institution boats)' on rows 51, 53 (block 'April')
- 2017: 'South Float East - 90'' on rows 61, 64 (block 'May')
- 2017: 'Small craft slips (institution boats)' on rows 63, 65 (block 'May')
- 2017: 'South Float East - 90'' on rows 73, 76 (block 'June')
- 2017: 'Small craft slips (institution boats)' on rows 75, 77 (block 'June')
- 2017: 'South Float East - 90'' on rows 85, 88 (block 'July')
- 2017: 'Small craft slips (institution boats)' on rows 87, 89 (block 'July')
- 2017: 'South Float East - 90'' on rows 97, 100 (block 'August')
- 2017: 'Small craft slips (institution boats)' on rows 99, 101 (block 'August')
- 2017: 'South Float East - 90'' on rows 110, 113 (block 'September')
- 2017: 'Small craft slips (institution boats)' on rows 112, 114 (block 'September')
- 2017: 'South Float East - 90'' on rows 122, 125 (block 'October')
- 2017: 'South Float East - 90'' on rows 134, 137 (block 'November')
- 2017: 'Small craft slips (institution boats)' on rows 136, 138 (block 'November')
- 2017: 'South Float East - 90'' on rows 146, 149 (block 'December')
- 2017: 'Small craft slips (institution boats)' on rows 148, 150 (block 'December')
- 2018: 'Small craft slips (institution boats)' on rows 76, 77 (block 'June')
- 2018: 'Small craft slips (institution boats)' on rows 100, 101 (block 'August')
- 2018: 'Small craft slips (institution boats)' on rows 113, 114 (block 'September')
- 2018: 'Small craft slips (institution boats)' on rows 125, 126 (block 'October')

### duplicate_berth_row_in_block (5)

- 1998: 'North Pier West - 410'' appears on rows 92, 93 in block 'SEPTEMBER 1998'
- 2014: 'Small craft slips (institution boats)' appears on rows 75, 76 in block 'June'
- 2017: 'South Float East - 90'' appears on rows 85, 88 in block 'July'
- 2017: 'South Float East - 90'' appears on rows 110, 113 in block 'September'
- 2017: 'Small craft slips (institution boats)' appears on rows 112, 114 in block 'September'

### Text cells in rows without a berth label (334; full list in `unlabeled_cells.csv`)

These sit in the blank rows between the last berth row of a block and the next month header (or, in 2013/2014, in the row above the first header). They are not emitted as bookings. Per sheet: 1997=1, 1998=0, 1999=0, 2000=0, 2001=0, 2002=9, 2003=5, 2004=0, 2005=1, 2006=3, 2007=0, 2008=2, 2009=1, 2010=77, 2011=43, 2012=19, 2013=44, 2014=23, 2015=22, 2016=30, 2017=15, 2018=27, 2019=12.

- A recurring row 'F/V Western Sound | R/V Long Ketch | M/V GREY COMPASS | Barge SILVER VOYAGER | OSV AMBER REEF | OSV Silver Tide | M/V NORTHERN HARBOR | R/V GOLDEN COMPASS ...' appears 8 times (sheets 2010, 2012, 2013, 2015, 2016, 2017, 2018, 2019); it looks like a colour legend/key row, not bookings.
- Other unlabeled-row cells are a mix of vessel names, events and operational notes (e.g. 'R/V Amber Tide', 'OSV Golden Tern', 'Barge Bright Sound', 'R/V Amber Heron', 'R/V Golden Meridian', 'M/Y LONG PETREL', 'S/V Golden Heron', 'S/V Far Current'); in 2011-2013 they occupy the three rows under 'South Float East' where later sheets put the 'North Finger Piers:' / 'Small craft slips' rows, so some may be unlabelled finger-pier bookings.

### Berth labels and the years they appear in

- 'North Pier West - 410'': 1997-2019 (23 sheets)
- 'North Pier Face - 75'': 1997-2019 (23 sheets)
- 'North Pier East - 240'': 1997-2019 (23 sheets)
- 'Inner Channel - 55'': 1997-2019 (23 sheets)
- 'South Float West - 90'': 1997-2019 (23 sheets)
- 'South Float East - 90'': 1997-2019 (23 sheets)
- 'Small craft slips (institution boats)': 2011-2019 (7 sheets)
- 'North Finger Piers:': 2014-2019 (6 sheets)

### Other observations

- Every cell in the day grid carries thin borders on all four sides in every era, so borders carry no span information and were not used.
- Fills are used both as span indicators (e.g. 2005 'R/V CLEAR SEXTANT' green fill across 12 empty cells) and as row-wide shading (e.g. the whole 'North Pier Face' row grey in 2015/2019, whole 'Small craft slips' row white); fill runs starting from a shaded row therefore extend to the next value or the month end. Fill runs that reached the last day column with the same fill continuing: 2.
- In several pre-2009 blocks the coloured fill starts one cell left of the named cell (e.g. 1997 'Tug WESTERN CURRENT' AB6 with AA6 also filled); the rule only extends to the right, so such leading cells are ignored.
- The 2010 sheet's 'NOVEMBER 2018'/'DECEMBER 2018' blocks are also structurally broken: the header row holds vessel names in C..H before the day numbers (which run 7..30/31), the weekday row holds 25 vessel names, and a stray '1..6' sits in the unlabeled row above the header.
- Day-number rows are shifted right in 2010 Jan (E), 2011 (C/F), 2012 (D/E/G), 2013 (F), 2014 (G), 2015 (D/H) while several values (notably 'R/V GOLDEN COMPASS' and 'R/V Golden Horizon' on the 1st) still sit in column B, i.e. left of day 1; those records are kept with day <= 0 and date_valid=false.

## 5. Assumptions

1. A block starts at any row whose column A matches a month name optionally followed by a four-digit year; the block ends at the next such row or the sheet end.
2. block_year is the year in the header when present, else the sheet year; the mislabelled 'NOVEMBER 2018'/'DECEMBER 2018' blocks in the 2010 sheet are kept as labelled (block_year 2018).
3. The day-number row is the row among the header row and the two following rows that holds the longest run of consecutive integers or '=...+1' formulas; the day-1 column is derived from that run (column of value N minus N-1), so runs that start above 1 still yield a day-1 column.
4. If no day-number run of at least 3 cells exists, day 1 is assumed at column B for 'MONTH YYYY' headers and column C for plain 'Month' headers, and the block is listed as an anomaly.
5. The block's last day column is the last number in the day-number row (not the calendar), and date_valid uses the real calendar of block_year/block_month.
6. A berth row is any row inside a block whose column A is non-empty and is not a month header; rows with an empty column A are never berth rows, and their text cells go to unlabeled_cells.csv instead of bookings.csv.
7. berth_name/berth_length_ft are parsed from "<name> - <n>'"; labels without a length (group rows) get an empty length and a name with any trailing colon removed.
8. group_label is set only on group rows: 'North Finger Piers:' gets itself, 'Small craft slips (institution boats)' gets the nearest preceding 'North Finger Piers:' in the block (or itself when none precedes it); the six canonical berths always get an empty group_label even when a duplicate berth row sits below a group row.
9. Every non-empty cell in a berth row from column B onward is a record unless it is a formula ('=...') or a bare number; cells left of day 1 or right of the last day column are still emitted (with the computed day) and flagged.
10. Span precedence is merge, then fill_run, then repeat, then single; a fill run requires a solid fill that is not 'none', not theme 0 without tint and not rgb FFFFFFFF (white), and extends only over empty cells with the identical fill string up to the block's last day column.
11. A repeat run collapses only exactly identical strings in immediately adjacent cells (case-sensitive), consuming those cells.
12. Merges are read from the sheet XML; a merge whose right edge passes the last day column is clamped and flagged; a merge is honoured only when the value sits in its top-left cell.
13. date_valid is true only when both start_day and end_day exist in block_year/block_month; invalid ISO dates are left blank rather than raising.
14. The fill column holds the raw _styles.tsv fill summary of the start cell for non-default solid fills and is blank otherwise.
15. The 8YR summary comparison matches on berth_name (label without length) and block_year, counting only records with valid dates; nothing was tuned to improve the match.
16. Weekday-letter rows are recognised by having an empty column A and at least five single-letter weekday cells; text found in header or weekday rows is reported as junk, not extracted.
17. Borders are ignored for span detection because every grid cell carries thin borders.
18. Values in registry sheets (Science/Yachts/Tours) are not used; classification of raw_value (vessel vs event vs note) is out of scope.
