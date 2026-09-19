# Assumptions

Numbered so they can be cited. The website links to these rules through its guide.

1. A reservation's day range is **end-inclusive**: "3rd to 5th" occupies three days. (`DayRange`, decision 0001)
2. There are no times on reservations; arrivals and departures are annotations, never rules.
3. A berth's length is the number in its spreadsheet label. Rows without a number ("North Finger Piers:", "Small craft slips") are berths with an unknown length, so shared days on them come out *unverifiable* rather than fine.
4. The six named faces and floats are **linear** berths: several vessels tie up end to end. (decision 0002)
5. Each vessel on a shared berth is charged its length plus **10 feet** of clearance; a lone vessel is only checked for fit. The clearance is a per-berth setting.
6. An **event** occupies the whole berth; a **closure** occupies the whole berth and refuses to displace or be displaced. Two closures may overlap.
7. Initial vessel lengths come from the registry sheets. Disagreements leave the length unknown. A person may correct a length; affected active bookings are rechecked, blocking findings require a recorded review reason, and the correction and review are stored together.
8. Vessel identity is the case-folded name including its type prefix: "Barge SALT DORY" and "Barge Salt Dory" are one vessel; "R/V Quiet Tern" and "R/V Quiet Heron" are two; "OS/V" and "OSV" are the same prefix.
9. **Unknown is not OK**: a missing vessel, neighbour or berth length gives the verdict UNKNOWN, which blocks saving like a conflict until a length or an override reason is entered. If the known lengths alone already overflow, that is a CONFLICT regardless. (decision 0003)
10. Stays before 2009, whose end dates are inferred from cell colouring or repeated names, are imported with the inference recorded in `legacy_ref` (`:fill_run`, `:repeat`).
11. A stay that ends on the last day of a month block and continues on day 1 of the next block for the same berth and name is one reservation ("stitched").
12. The "NOVEMBER 2018" and "DECEMBER 2018" blocks on the 2010 sheet are November and December 2010; the only place the importer corrects a label, and it logs it.
13. A month block that repeats a month already read from another sheet (the sheets that begin with the previous December) is skipped and logged.
14. Text in header rows, in rows without a berth label, or outside the day columns is an issue, never a reservation.
15. Notes such as "ETA 1200", "Fuel truck", "Delayed due to weather" are annotations; text the classifier has never seen is kept as an annotation with a low-confidence issue.
16. The "8YR Dock Summary" sheet is reference material, not ground truth; the audit prints it beside what the grids contain.
17. Tours are visits linked to a vessel; they do not occupy berths and carry no rules.
18. The site is a shared synthetic demo with no authentication. Database write locks protect booking decisions across simultaneous requests. General reservation edits do not have per-user ownership or a complete edit history; measurement corrections do have a recorded review and stale-preview protection.
19. Draft and water depth are not modelled (WHOI's 19-foot channel limit would be a later rule).
20. Cancelling a reservation never needs a check: a cancelled reservation occupies nothing.
