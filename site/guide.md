# Dock Scheduler: how it works

Dock Scheduler manages vessels, events and closures across berths of different lengths. It checks the requested days, explains fit and capacity problems, and keeps the reason for an accepted exception. The Harbor view makes known dimensions visible; the Grid retains the familiar month schedule. The live app saves bookings in PostgreSQL through a Python API on Vercel.

## Start here

1. Open Schedule (Harbor is the default layout) and choose **Fit example · 2010**. R/V Clear Tern is 120 ft long on the 75 ft North Pier Face: it overhangs by 45 ft.
2. Choose **Sample history** for 12 July 2017. Utility work closes South Float East while OSV Amber Reef is scheduled there.
3. Open Book to check a proposed reservation or ask for alternatives. Check and Suggest do not save anything.
4. Use Vessel registries to find dimensions and open the source workbook. Review length previews a correction and shows its impact on existing bookings.

## The website, side by side

| View or action | What happens underneath |
|---|---|
| Harbor | The default Schedule layout. Python supplies occupants and findings. SVG draws known vessel and berth lengths on one scale. Location and hull width are illustrative; unknown lengths use a dashed 40 ft drawing placeholder. |
| Grid | Choose Grid in the Schedule layout switch. Reservations appear as month bars. Select a bar to inspect, edit or cancel it. Use arrow keys within the day cells, then Enter to start a booking. Imported notes appear below the grid. |
| Side by side | Grid and Harbor share one selected day. Choose a day number in Grid or change the Harbor date; both follow. Changing months clamps the selected day to the month’s last day. The views sit next to each other on wide screens and stack on phones. |
| Book | FastAPI validates the input; one Python rules engine returns OK, CONFLICT or UNKNOWN. Saving repeats the decision inside a write transaction. A blocking result requires an override reason. |
| Suggestions | The same rules evaluate available alternatives, ranked by berth length. An UNKNOWN option still needs measurements or an explicit override. |
| Reservation editing | Dates, berth and status are rechecked. A reason from an earlier booking does not cover a new conflicting edit. Notes-only changes can be saved even when historical dimensions are missing. |
| Vessel registries | Search names, length, draft, operator and notes. A length correction previews affected stays and neighbours. Blocking outcomes require a review reason, saved alongside the measurement and findings. A changed schedule invalidates an old acknowledgement. |
| Measurement history | The registry's Review length dialog shows previous corrections and reasons. A reservation's details show its own vessel's measurement reviews. This is a focused measurement record, not a complete user-attributed edit log. |
| Audit | Filter the original workbook’s findings by vessel/event name, berth, inclusive dates and finding type. Counts describe matching findings. Remember filters on this browser is optional. A separate whole-workbook reference retains the global totals. Later live edits appear in Grid and Harbor, not this historical report. |
| Issues | Source locations and explanations for ambiguous or malformed workbook data. Imported operational notes remain context rather than reservations. |

## Personalizing Audit

Combine any of the five filters to answer a specific question. For example, choose **South Float East**, **Closure overlap**, and **11–15 July 2017** to isolate Utility work and OSV Amber Reef. Search accepts either vessel or event names. Confirmed conflicts and Missing evidence provide quick shortcuts; **Clear filters** resets the entire selection.

Check **Remember my filters on this browser** to restore your selection after reloading. Uncheck it to forget the saved selection. A storage restriction does not stop filtering. An invalid date range displays an explanation and retains the last valid results.

Findings have different units: a fit finding describes a stay, while a shared-capacity finding describes a berth-day. One stay can have more than one finding. The whole-workbook reference is intentionally unaffected by filters. **Open these dates in Grid + Harbor** opens the current ledger for comparison; later live edits can differ from the original historical evidence.

## Why the rules use three answers

**OK** means the modeled checks pass with the necessary evidence. **CONFLICT** means a definite rule is violated. **UNKNOWN** means a required measurement is missing. Unknown does not mean free or safe. If known measurements already prove an overload, the answer remains CONFLICT even when another measurement is absent.

A long pier can hold multiple vessels. On a 410 ft face, 274 ft and 100 ft vessels use `(274 + 10) + (100 + 10) = 394 ft` together. Adding a 60 ft vessel raises use to 464 ft, exceeding capacity by 54 ft. A lone vessel is checked against berth length without the shared-occupancy clearance allowance.

## Correcting a measurement

Choose Review length in the registry, enter the corrected length (or leave it blank for unknown), then Preview impact. The list shows each affected booking's before/after verdict. If blocking findings remain, explain the source of the correction and how the bookings will be handled. Save reviewed measurement records both the fact and its review atomically. It does not cancel, move or approve those reservations automatically; resolve them through the reservation editor. If another edit changes the relevant schedule, review the refreshed findings before saving.

## Rules and assumptions

1. Dates are inclusive: the 3rd through the 5th occupies three days. Two reservations sharing the 5th overlap.
2. Reservations have dates, not times. Arrival/departure times are annotations.
3. Initial berth lengths come from the spreadsheet labels. Group rows without dimensions keep an unknown capacity.
4. The six named faces and floats use shared linear capacity: vessels can tie up end to end. The imported group rows also use linear capacity with unknown lengths; the engine separately supports exclusive slips.
5. Shared occupancy charges each vessel its length plus 10 ft clearance. A lone vessel is checked for fit only.
6. Events occupy a whole berth. Closures prohibit other use; two closures may overlap.
7. Initial vessel lengths come from Science and Yachts. Conflicting measurements remain unknown. Human corrections use the reviewed measurement workflow.
8. Vessel identity uses normalized names and type prefixes, not an official global vessel identifier. Case and equivalent OS/V punctuation are folded together.
9. Missing required measurements block saving as UNKNOWN until corrected or explicitly overridden. A known overload is always a conflict.
10. Historical spans inferred from color or repeated names retain source references and an explanation in the reservation details.
11. Matching stays continuing across a month boundary are stitched into one reservation.
12. The two 2018-labelled blocks on the 2010 sheet are interpreted as November and December 2010, with the correction logged.
13. Repeated month blocks are skipped and logged.
14. Text in headers, unlabelled rows or outside day columns is logged instead of becoming a reservation.
15. Operational notes and unclassified text become annotations; uncertainty is recorded in Issues.
16. The 8YR Dock Summary is reference material because it cannot be reproduced exactly from the grids.
17. Tours are stored as visits and do not consume berth capacity; there is no separate tours screen.
18. This is a shared synthetic demo without sign-in. Writes are serialized for consistent booking decisions. General reservation edits have no per-user ownership or full edit history.
19. Draft, water depth, times of day and a physical rafting model are outside this version's rules. Actual operations need these assumptions validated with the dock coordinator.
20. A cancelled reservation occupies nothing. Restoring it to an active status is checked again.

## What the imported history proves

The workbook covers 1997–2019. The importer encountered 2,244 runs, excluded 80 outside day columns and read 2,164. It skipped fourteen repeated-month runs, separated 46 annotations and performed 122 joins, leaving 1,982 reservations. There are 1,927 vessel stays, 33 events and 22 closures.

Only 33 vessel stays have a known vessel length: 98.3% are unknown. Nine reservation records involving five distinct vessels fail individual fit; twelve shared berth-days are unverifiable and one vessel stay overlaps a closure. Zero detected arithmetic overloads does not prove the historical schedule was valid. The 575-vessel registry initially contains 158 known lengths; live corrections may change that count.

## Engineering sequence

| Stage | Work and reason |
|---|---|
| Understand the brief | Translate the request into book/check/save/reject/history behavior and documented assumptions. |
| Inspect the source | Study layout eras, duplicated berth rows, notes, missing dimensions and inconsistent summary totals. |
| Model the domain | Define berth, vessel, date range, reservation, finding and verdict as explicit validated objects. |
| Implement the rules | Keep checks in pure Python, independent of database, web requests and drawing code. |
| Import and reconcile | Infer spans by a documented priority, normalize names, stitch months and keep issues/provenance. |
| Audit | Apply the same rules to the historical import and report unknowns as unknowns. |
| Store and expose | Save the ledger in SQLite locally, expose validated FastAPI endpoints, and check writes atomically. |
| Build the interface | Adapt the Harbor prototype and add Grid, Book, registries, Audit and Issues without a frontend build pipeline. |
| Test and review | Cover rules, messy workbook layouts, HTTP errors, overrides, concurrency, storage failure and reviewed corrections. |
| Publish | Export a read-only Pages snapshot; deploy the operable app to Vercel with persistent PostgreSQL. |
| Verify | Check live responses, create/read/edit/cancel a labelled test event, and verify new schema initialization preserves records. |
| Improve and explain | Add reviewed measurements, the reservation editor, notes and visible assumptions; use a repeatable acceptance checklist and demo. |

## Links

[Return to Harbor](index.html#harbor) · [Live app](https://dock-scheduler-henna.vercel.app/) · [Source and decisions](https://github.com/broccolibabe0711/dock-scheduler) · [API documentation](https://dock-scheduler-henna.vercel.app/docs) · [Acceptance checklist](acceptance.html)

## Input suggestions

Every field that accepts typing also has a suggestion menu. You can browse names before typing, or type part of a vessel/event name to narrow the list. Booking and Vessel registries use current vessel records; Audit uses the original sample’s finding names. You can still enter custom names and text.

Date and month fields offer shortcuts alongside their calendars. The To menu can use the From date, a seven-day stay or a thirty-day stay; these counts include both arrival and departure. The shortcuts update when you open the menu. Audit also offers the first/last finding dates and closure examples.

Titles offer event or closure examples. Notes and exception/review reasons offer templates that append to your existing text. Replace every bracketed prompt before saving. A template does not approve an exception, and choosing any suggestion does not save a booking.

Length menus offer only the selected vessel’s recorded measurement or unknown. Enter a different verified measurement directly and preview its impact before saving. A newly typed vessel name does not inherit the previous vessel’s length.
