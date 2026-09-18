# 1. Reservations are inclusive ranges of calendar days

**Context.** The legacy grid has one column per day and a vessel's name in every day it was present, so "3rd to 5th" means three occupied days. Vessels arrive and leave at times of day ("ETA 1200", "Departs 0600" appear as notes), but the facility plans in days.

**Decision.** A reservation is `DayRange(start, end)` with both ends inclusive; two ranges overlap when `a.start <= b.end and b.start <= a.end`. Times are annotations, never part of the rule.

**Consequences.** Adjacent stays (one ends the 3rd, the next starts the 4th) never conflict; same-day turnarounds (one leaves the 3rd, the next arrives the 3rd) do conflict and need an override with a reason. That is the conservative reading, and it matches how the grid was read by eye.
