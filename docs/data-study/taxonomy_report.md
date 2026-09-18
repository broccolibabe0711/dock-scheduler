# Booking-cell value taxonomy (23 year grids, 1997-2019)

Input: `all_cells.txt` (2663 cell values, 573 distinct). Script: `analysis/build_taxonomy.rb`
(`ruby build_taxonomy.rb <scratch_dir>`), output `analysis/value_taxonomy.csv`.
No cell was left as `other`: every value matched a vessel prefix or a curated non-vessel label.

## Counts per kind

| kind    | distinct | occurrences |
|---------|---------:|------------:|
| vessel  | 532      | 2440        |
| note    | 18       | 103         |
| event   | 13       | 67          |
| closure | 10       | 53          |
| other   | 0        | 0           |

Distinct vessels: **532 raw -> 504 after normalization** (28 groups collapsed, all pure case variants).
19 normalized vessels found a length in the Science/Yachts registry; 2 of those (M/V Deep Reef 24'/100', and
R/V High Reef in the registry only) have conflicting registry lengths and get no `length_ft`.

## Normalization rules (plain English)

1. **Vessel detection**: a value is a vessel if it starts with a recognized type prefix, matched case-insensitively:
   R/V, M/V, F/V, S/V, M/Y, S/Y, OSV, OS/V, Tug, Barge, USCG/USCGC. The prefix is rewritten to canonical
   spelling (OS/V -> OSV; USCGC -> USCG) and the remainder is Title-Cased word by word
   ("Barge SALT DORY" and "Barge Salt Dory" -> "Barge Salt Dory"). `type_prefix` = the canonical prefix.
2. **Lengths**: every cell of the Science and Yachts registry sheets matching `<prefix> <name> <N>'` is indexed by the
   same normalized name; if exactly one length is known it is copied to `length_ft`, if several conflict the row is
   marked medium confidence with the candidates in `rationale`. Grid cells never carry lengths themselves.
3. **Non-vessels** are resolved from an exact-match override table (27 entries, case-insensitive) which fixes kind,
   canonical label and confidence. Labels drop qualifiers ("Float rebuild - no usage permitted" -> "Float rebuild",
   "Bollard replacement, west face" -> "Bollard replacement").
4. **Notes** not in the override table match generic patterns: ETA/ETD/Arrival/Arrives/Departs/Departure ...,
   Fueling/Bunkering/Provisioning/Load equipment/Water-slops pumping, Delayed .../Touch and go. Trailing times and
   AM/PM are stripped so "Bunkering 1000" -> "Bunkering", "ETD PM" -> "ETD", "Departs 0600"/"Departure 0800" -> "Departure",
   "Arrival 1400"/"Arrives AM" -> "Arrival".
5. Fallback keyword rules (training/tour/event -> event; repair/maintenance/closed/test -> closure) exist for future data
   and are flagged low confidence; nothing in the current file reaches them.

## Ambiguous cases and decisions

- **Bunker barge** (12): unnamed craft, but it physically occupies the berth -> `vessel`, normalized "Bunker barge",
  prefix Barge, medium. An extractor should count it as a booking; it is not one identifiable vessel.
- **Fuel truck** (9): a shoreside service to a berthed vessel; the berth is occupied by whatever it is fueling ->
  `note`, medium. Same logic for **Wire spooling** (2): deck operation, `note`.
- **Emergency port call** (4): an unnamed vessel visit that does occupy the berth -> `event`, medium (it is a booking
  but has no vessel identity; treat like a vessel of unknown name when counting usage-days).
- **Dock inspection** (2): could be an event; it restricts use of the berth -> `closure`, medium.
- **Paving near dock entrance** (4): works adjacent to the berth; grouped with `closure` (access limited), medium.
- **Road race - access limited** (6): external event, berth stays usable but access limited -> `event`, high.
- **Holiday** (7): no vessel, no work -> `event`. Usage-day computations should probably ignore it.
- **Returns from sea trials** (2), **Touch and go** (7), **Delayed due to weather** (7): movement annotations of a
  vessel booked elsewhere in the row -> `note`.
- **Science stroll**, **Film crew on dock**, **Donor reception**, **Public open house**, **Dive training**,
  **Safety training (RIBs)**, **Rescue drill** -> `event` (activities using the dock, no vessel name).
- **Ultrasonic pier test**, **Concrete work near test wells**, **Utility work on pier face**, **Crane access - berth closed**
  -> `closure`.
- **OS/V Silver Skua / OS/V Golden Osprey**: prefix variant of OSV; collapsed to OSV.

## Near-duplicate vessel names for human review

Case-only variants (auto-merged, 28 groups; the largest by occurrences):
Barge Salt Dory (59+42), R/V Long Anchor (80+8), M/V Northern Harbor (77+4), R/V Clear Sextant (63+18),
S/V Far Horizon (28+22), M/V Grey Compass (42+5), M/V Quiet Petrel (29+13), Barge Silver Voyager (22+15),
S/V Golden Heron (20+15), OSV Wild Star (21+3), Tug Western Current (13+8), Tug Blue Fathom (15+6),
M/V Deep Reef (14+6), OSV Silver Tide (13+6), S/V Iron Petrel, Tug Wild Gannet, Tug Golden Sound, M/Y Blue Tide,
R/V Iron Harbor, M/V Coral Lantern, Barge Western Cove, F/V Iron Sextant, M/V Deep Ledge, R/V Northern Meridian,
S/V Green Osprey, R/V Clear Fathom, R/V Wild Dory, S/V Golden Fathom.

NOT merged, but within edit distance 2 of each other (kept separate: the names are built from a small
adjective+noun vocabulary, so these look like distinct synthetic vessels, not typos; confirm):
- R/V Quiet Tern ~ R/V Quiet Heron
- M/V Iron Heron ~ M/V Iron Tern
- M/V Coral Kestrel ~ M/V Coral Petrel
- M/V Northern Petrel ~ M/V Northern Kestrel
- R/V Green Sextant ~ R/V Grey Sextant
- R/V Grey Wind ~ R/V Green Wind
- R/V Green Marlin ~ R/V Grey Marlin
- S/V Green Skua ~ S/V Grey Skua

No two normalized names share the same name with different prefixes (e.g. no "R/V X" vs "M/V X").
Deliberately different: R/V Golden Horizon vs R/V GOLDEN COMPASS; M/V Deep Reef vs M/V Deep Ledge vs M/V Deep Sound.

## Assumptions
- The grid is the only source for kind; lengths come solely from the registry tabs and are missing for most vessels.
- Title Case is applied blindly (e.g. "RIBs" is only preserved because it sits in an override label).
- The 8YR Dock Summary was not used here; it is relevant for the extractor step, not for classification.
