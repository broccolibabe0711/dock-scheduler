# Tours sheet parse report

Source: `Tours.tsv` (sheet27). Output: `tours.csv`.

## Row counts

- Physical rows in sheet: 42
- Banner rows: 4 (rows 1, 2, 41, 42); the top two and the bottom two are each merged A:G (mergeCell A1:G1, A2:G2, A41:G41, A42:G42 -- those are the only 4 merges in sheet27.xml)
- Header row: 3
- Blank rows: 4 (rows 32, 33, 37, 38) -- visual separators between months
- Stray note fragments (non-numeric col A, skipped): 1 [[18, "Requires shore power"]]
- Parsed tour rows: **32**

## Date range

- 2018-04-29 to 2018-07-24 (serials 32 rows; converted as 1899-12-30 + serial)
- Dates with multiple tours: 2018-04-29 (3), 2018-05-02 (2), 2018-05-05 (3), 2018-05-21 (2), 2018-05-22 (3), 2018-06-04 (2), 2018-07-24 (2)

## Oddities and handling

- Time not HHMM (kept in `time_raw`, `time_valid` empty): 12 rows -- 'tbd' x10, '1175' x2 (minute 75 is impossible; rows 17, 24). Valid 3-digit times like '930' are zero-padded to 09:30.
- People with '~' prefix (approximate): 8 rows -> `people_approx=true`, `people_num` = stripped integer.
- People unparseable: 0.
- Unusually large party: [[34, "54"]] (row 34, 54 people; kept as-is, flagged here).
- Guest without '(Org)': 0.
- Empty Notes: rows 23, 29, 30, 34.
- Row 18 'Requires shore power' sits alone in col A directly under row 17 which already has that note: treated as a stray duplicate fragment and dropped.
- Row 26: guide 'Elliot' hosts guest 'Elliot Bramble' -- coincidence in synthetic data, no action.
- The sheet is not sorted strictly (rows 4-6 have descending times on the same date); order preserved via `row_index`.

## Distribution

- By vessel: R/V Blue Heron: 12; R/V Northern Gannet: 12; R/V Silver Tern: 8
- By organisation: Bayline Charters: 4; Coastal Survey Partners: 2; Estuary Foundation: 2; Gulf Coast University: 4; Harbor Institute: 1; Lakeshore Research Group: 4; Northwind Offshore: 1; Open Water Sailing School: 2; Regional Fisheries Agency: 5; Seaway Education Trust: 2; State Marine Academy: 4; Tidewater Marine Services: 1

## Assumptions

1. Date serials use the 1900 date system (epoch 1899-12-30), so 43219 = 2018-04-29; no 1904-system check was possible because there are no cached values.
2. Times are 24h local HHMM; a 3-digit value means H:MM; anything with minutes >= 60 or hours >= 24 is invalid rather than a typo to be corrected.
3. '~N' means an estimated headcount and the integer N is usable for capacity planning.
4. Guest format 'Name (Organization)' is universal; the last parenthesised group is the org.
5. Non-data rows (banners, blanks, a lone note in col A) carry no tour information and can be dropped without loss; the trailing banner rows 41-42 duplicate rows 1-2.

## Implications for a scheduling system

- Tours are point-in-time events (date + optional time), not berth occupancy: they never span a day range and do not consume a berth slot.
- They reference vessels by free-text name ('R/V Silver Tern'); a scheduler needs a vessel registry so a tour can be linked to the vessel *and* to wherever that vessel is berthed that day (the join is via vessel, not via dock).
- Fields needed: date, time (nullable / 'tbd' state), guide (staff), guest contact, guest org, headcount (with approximate flag), vessel, status-like notes (Confirmed / Pending insurance / Approved) which are really a workflow status and should be an enum plus free text.
- Validation the sheet lacks: time format, headcount type, required notes, no stray rows. Multiple tours per vessel per day (e.g. 3 on 2018-04-29) are normal, so vessel+date is not a unique key.
- The banner says tours moved to a separate workbook: treat this tab as a legacy sample, not the system of record.

## 8YR Dock Summary

- Transcribed to `usage_summary.csv` (8 years x 7 berths = 56 rows).
- The 'Total Days' row is an uncached formula (=SUM(B2:B8) ...) with no <v> value in the XML, so it was NOT transcribed; recomputed sums: 2006=639, 2007=973, 2008=560, 2009=903, 2010=869, 2011=1045, 2012=1520, 2013=1675.
- 'Marsh Landing' appears here but not as a grid row label in the year sheets; 'Inner Channel 55'' appears in the grid but not here -- possibly the same berth under a different name (to investigate).
