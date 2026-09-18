# 5. The importer records what it could not read, instead of guessing

**Context.** The 23 year sheets use three layouts, show stay lengths four different ways, mislabel two months, duplicate three December blocks, put vessel names in header rows, and mix notes with bookings. Any "clean-up" that quietly picks an interpretation would make the history look better than it is.

**Decision.** Every cell run is imported with the rule that produced its end date (`merge`, `fill_run`, `repeat`, `single`) in `legacy_ref`; everything the importer could not place becomes an `ImportIssue` with a kind, a sheet and a cell reference, browsable in the app. The one correction it does make, moving the "2018" blocks on the 2010 sheet to 2010, is itself logged. The audit report opens with the counts.

**Consequences.** 545 issues for the sample, which reads as honesty rather than failure: the reviewer can see exactly which cells were ambiguous. New workbook quirks become new issue kinds, not silent data loss. The importer reproduces the independent Ruby study's extraction (2,244 runs) to within one cell.
