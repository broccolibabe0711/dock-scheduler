# 2. Pier faces have linear capacity; slips are exclusive

**Context.** The 410-foot North Pier West cannot be "one vessel per berth": the sample's own grids put two vessels on it on the same day by duplicating the berth row (27 duplicated rows across the years), and WHOI's real 430-foot Iselin pier is described as docking two large ships and several small ones.

**Decision.** A berth has a `capacity_mode`. On a `linear` berth, each vessel occupies its length plus a per-berth clearance (10 feet by default), events and closures occupy the whole berth, and the occupied feet on any day must not exceed the berth's length. On an `exclusive` slip, any second occupant is a conflict regardless of lengths.

**Consequences.** "Double-booked" becomes arithmetic the system can show ("284' + 110' + 70' = 464' > 410'"). The clearance is a setting, not a constant, because it is a guess; changing it is one number per berth. Rafting (vessels tied alongside each other) is not modelled and surfaces only as a note when an override is being considered.

**Clearance, precisely.** Each vessel is charged its length plus the berth's clearance, so two vessels pay two clearances for one gap between them; that is deliberate (fender room at both ends of each hull) and it is the number to change if the dockmaster disagrees. A vessel alone on a face is judged by the fit rule only; clearance matters when the face is shared. When some lengths are unknown, the known lengths are still summed: if that partial sum already exceeds the face, the day is a conflict; if it fits, the day is "unverifiable" until the missing length is entered.
