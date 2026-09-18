# Vessel registry report

Built by `analysis/build_registry.rb` from `tsv/Science.tsv` and `tsv/Yachts.tsv`.

## Counts

| metric | value |
|---|---|
| rows in (Science / Yachts / total) | 251 / 190 / 441 |
| header rows skipped | 1 |
| blank rows | 135 |
| continuation rows folded into the vessel above (Science / Yachts) | 90 / 47 |
| noise rows (fragment with no vessel above) | 0 |
| vessels out (rows in vessels.csv) | 168 |
| of which named vessels | 166 |
| of which unnamed (LOA-spec-only) groups | 2 |
| vessels with a length (trailing NN' or LOA) | 168 |
| vessels with a separately stated LOA | 5 |
| vessels with a draft | 5 |
| vessels with an operator | 63 |
| vessels with no contact at all | 13 |
| vessels with notes | 40 |
| distinct name_keys | 164 |
| duplicate name_keys (appearing 2+ times) | 2 |
| length conflicts among duplicates | 2 |
| Science vessels / Yachts vessels | 97 / 71 |

Type prefix distribution: Barge=7, F/V=11, M/V=39, M/Y=25, OSV=8, R/V=47, S/V=20, S/Y=5, Tug=4, other=2

Flag distribution: approved=5, confirmed=5, contact_captain_on_arrival=5, insurance_pending=6, length_loa_mismatch=3, multiple_operators=6, no_contact=13, no_overnight_crew=8, rafts_ok=3, see_schedule_file=7, short_visit=9, tentative=2, unnamed=2

## Duplicates

- rv high reef: Science row 92 (R/V High Reef 32') ; Science row 207 (R/V High Reef 72')
- mv deep reef: Yachts row 96 (M/V Deep Reef 24') ; Yachts row 114 (M/V Deep Reef 100')

## Length conflicts

- rv high reef: lengths 32' vs 72' -- Science row 92 (R/V High Reef 32') ; Science row 207 (R/V High Reef 72')
- mv deep reef: lengths 24' vs 100' -- Yachts row 96 (M/V Deep Reef 24') ; Yachts row 114 (M/V Deep Reef 100')

`vessel_length_lookup.csv` keeps ONE row per name_key; when duplicates disagree on length the MAXIMUM is used (conservative for berth-fit purposes).

## Noise rows

none

## Messiness patterns handled

### Email under a non-EMAIL column (46 occurrences)
- Science row 33 col 3: "marley.garland@example.com"
- Science row 37 col 4: "noel.kendrick@example.com"
- Science row 39 col 3: "reese.fairweather@example.com"
- Science row 39 col 5: "cameron.norwood@example.com"
- Science row 39 col 7: "logan.garland@example.com"

### Continuation row with a lone phone/email/captain in the VESSEL column (42 occurrences)
- Science row 6: "Cell: 555-0198"
- Science row 19: "Cell: 555-0101"
- Science row 31: "Cell: 555-0106"
- Science row 32: "Cell: 555-0153"
- Science row 49: "Cell: 555-0153"

### Phone number under a non-phone column (OPERATOR/CONTACT/EMAIL) (39 occurrences)
- Science row 2 col 3: "Cell: 555-0103"
- Science row 37 col 6: "Cell: 555-0113"
- Science row 37 col 7: "Cell: 555-0103"
- Science row 43 col 3: "Cell: 555-0183"
- Science row 43 col 9: "Cell: 555-0146"

### Placeholder URL cell (dropped from contacts, counted) (20 occurrences)
- Science row 68 R/V Iron Ketch 46'
- Science row 102 S/V Quiet Sound 24'
- Science row 110 R/V Clear Strand 145'
- Science row 125 F/V Coral Ketch 120'
- Science row 142 M/V IRON HERON 100'

### Free-text note under CONTACT/WORK#/CELL# instead of NOTES (16 occurrences)
- Science row 43 col 6: "Short visit only"
- Science row 81 col 4: "See scheduling file for specs"
- Science row 85 col 5: "Contact captain on arrival"
- Science row 102 col 5: "Approved by operations"
- Science row 102 col 6: "Confirmed by marine ops"

### Multiple different operator organizations attached to one vessel (6 occurrences)
- Science row 95 R/V Amber Marlin 145': Tidewater Marine Services / Harbor Institute
- Science row 106 M/V Green Kestrel 100': Bayline Charters / Tidewater Marine Services
- Science row 165 M/V Northern Gannet 85': Estuary Foundation / Gulf Coast University
- Science row 176 R/V Bright Fathom 46': Regional Fisheries Agency / Estuary Foundation / State Marine Academy
- Science row 209 OS/V Silver Skua 24': Seaway Education Trust / Regional Fisheries Agency

### Continuation fragment separated from its vessel by a blank row (6 occurrences)
- Science row 140: "sage.ingram@example.com | blake.abbott@example.com"
- Science row 146: "riley.bexley@example.com"
- Science row 148: "Cell: 555-0147"
- Science row 196: "blake.garland@example.com | Coastal Survey Partners"
- Science row 239: "Cell: 555-0109"

### Vessel name in ALL CAPS while others are Title Case (4 occurrences)
- Science row 25: "M/V CORAL DRIFT 100'"
- Science row 136: "Barge NORTHERN MARLIN 24'"
- Science row 142: "M/V IRON HERON 100'"
- Yachts row 146: "M/Y CORAL WIND 40'"

### "LOA: NN', Draft: NN'" spec in a secondary column of a named vessel (3 occurrences)
- Science row 33 col 2: "LOA: 65', Draft: 4'"
- Science row 136 col 5: "LOA: 65', Draft: 8'"
- Yachts row 1 col 2: "LOA: 65', Draft: 4'"

### Identical note repeated in several cells of one row (3 occurrences)
- Science row 194: "Cell: 555-0191" x2
- Yachts row 177: "Will raft alongside if needed" x2
- Yachts row 178: "Short visit only" x2

### Prefix variant "OS/V" instead of "OSV" (2 occurrences)
- Science row 190: "OS/V High Petrel 170'"
- Science row 209: "OS/V Silver Skua 24'"

### LOA/Draft spec in the VESSEL column with no vessel name (headless group) (2 occurrences)
- Yachts row 6: "LOA: 145', Draft: 12'"
- Yachts row 83: "LOA: 145', Draft: 12'"

## Assumptions

1. A row starts a new vessel iff its first cell carries a type prefix (R/V, M/V, F/V, S/V, M/Y, S/Y, OSV, OS/V, USCG, Tug, Barge), ends in a length mark NN', or is an `LOA:` spec. Every other non-blank row is a continuation of the vessel above, regardless of which column its content sits in.
2. Blank rows do NOT close a group: fragments after a blank row (e.g. Science rows 140, 146, 148, 196, 239; Yachts row 94) are attached to the vessel above them rather than discarded, because in this data the same pattern (blank row then phone/email) also appears where the attribution is unambiguous.
3. An `LOA: NN', Draft: NN'` cell in the VESSEL column (Yachts rows 6 and 83) starts an UNNAMED group (flag `unnamed`, empty vessel_name/name_key) rather than being merged into the previous yacht, because merging would contradict that yacht's own stated length (52' / 24' vs LOA 145').
4. length_ft is taken from the trailing NN' of the name; when a named vessel also carries an `LOA:` spec (e.g. M/Y Western Strand 52' with LOA: 65'), length_ft keeps the name's value, loa_ft records the LOA, and the flag `length_loa_mismatch` is set. The lookup file uses length_ft.
5. Cells are classified by shape, not by column: `Cell:/Work:` + digits = phone, `x@y.z` = email, `Capt.` or `Firstname Lastname` = person, text containing an organisation word (Institute, Charters, Academy, University, Partners, Group, Agency, Services, Trust, School, Foundation, Offshore, ...) = operator, everything else = note. Persons, phones and emails are all folded into `contacts`.
6. Placeholder cells `https://www.example.org/vessel` are treated as noise and dropped from contacts/notes (counted in the report).
7. Several distinct operator organisations in one row group are all kept, joined by ` / `, with flag `multiple_operators`; no attempt is made to decide which is primary.
8. name_key includes the type prefix with punctuation removed (`rv iron ketch` vs `fv iron ketch` are different vessels); `OS/V` is normalised to `OSV` before keying so both spellings match. Case is ignored, so `M/V CORAL DRIFT` and `M/V Coral Drift` would match. Duplicate vessels are kept as separate rows in vessels.csv (one per occurrence) and only collapsed in vessel_length_lookup.csv.
