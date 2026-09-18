# Proposal: "Harbormaster" (angle: Showman)

## Name
Harbormaster - a dock scheduling system whose front page is a to-scale, animated harbor.

## Angle
Showman. The reviewer opens one public GitHub Pages link and, without installing anything, watches 23 years of bookings play across a to-scale harbor: boats slide into berths, boats that are too long stick out past the end of the pier in red, days where a berth is over capacity glow, and a booking form refuses bad bookings with a picture of why. The backend is thin but real: a Python importer that turns the messy workbook into SQLite + JSON, a Python rules module that is the single source of truth, and a zero-dependency Python HTTP server for the "live" mode. The browser carries a mirror of the rules in JavaScript, and the two implementations are held to the same golden test file so the demo is never faking the logic.

## Pitch
The facility's two pains are "I have to eyeball a grid for double-bookings" and "I have to remember whether a 120-foot vessel fits a 75-foot face". Harbormaster replaces the grid with a drawing of the actual waterfront where length is the visual unit: every berth is drawn at its true length, every vessel at its registered length, so a boat that does not fit visibly overhangs and a pier packed past its linear capacity visibly overflows. A timeline scrubber runs from January 1997 to December 2019 so the reviewer can see the whole imported history animate, and every conflict the rules find is a glowing berth you can click to read the exact numbers. New bookings go through the same rule (sum of lengths plus clearance versus berth length, one boat per small slip, closures and events block a berth) and are refused with an explanation drawn as a bar that overflows the berth. Under the demo sits a Python importer that documents every ambiguity it met in the workbook instead of silently guessing, a SQLite schema, and a stdlib HTTP API, so the same code base runs for real at the facility.

## Stack
- Python 3.12 (via Homebrew, already planned). Why: the default for the backend, readable by a beginner, and it is the only runtime Baron will install. Used for the importer, the rules module, SQLite storage, JSON export, tests and the API server.
- openpyxl (the one pip install: `python3.12 -m pip install --user openpyxl`). Why: it reads `.xlsx` including `ws.merged_cells.ranges`, which is how spans are encoded from 2009 on. pandas would be a heavier install and hides the cell-level detail (merges, fills) the importer needs.
- sqlite3 (Python stdlib). Why: the brief mentions "databases"; a real schema with foreign keys and an end-inclusive date invariant is more explainable than JSON blobs, and it ships with Python. No ORM: the schema is four tables and Baron must be able to read every query.
- http.server (Python stdlib) for `dock/server.py`. Why: FastAPI/Flask would be a second install and 200 lines of concepts Baron would have to explain; the API is five routes and stdlib handles it in about 120 lines. Trade-off stated in README: not production-grade, single-threaded, fine for one harbormaster on one laptop.
- unittest (Python stdlib) instead of pytest. Why: zero installs; `python3 -m unittest -v` is one command.
- Frontend: vanilla HTML/CSS/JS, one `index.html`, ES modules, inline SVG. No build step, no framework, no npm. Why: GitHub Pages serves it directly, Node is not installed, and a beginner can read `harbor.js` top to bottom. SVG over Canvas because each boat is a DOM element that can carry a tooltip, a click handler and a CSS transition for the sliding animation, which is exactly the "rudimentary animation" Baron asked for with no animation library.
- No chart library. The two charts (berth load bar, usage-days reconciliation) are plain SVG rectangles.
- GitHub Pages serving the `web/` folder from `main`. Why: free, public, static, one click in repo settings.
- Installs required, total: Homebrew, python@3.12, gh (already planned), openpyxl. Nothing else.

## Architecture
Folder layout (repo root `/Users/baronzhang/Developer/dock-scheduler`):

```
dock-scheduler/
  README.md                 # what it is, demo link, how to run, how to test
  ASSUMPTIONS.md            # numbered assumptions, same list as below, kept in sync
  data/
    Dock Schedule - Synthetic Sample.xlsx
    generated/              # gitignored: dock.db, import_report.json
  dock/                     # Python package, the "backend"
    __init__.py
    model.py                # dataclasses Berth, Vessel, Booking, Note, ImportIssue
    rules.py                # THE rules: overlaps, day_load, check_booking, find_conflicts, suggest
    classify.py             # cell text -> kind (vessel|event|closure|note) + name normalisation
    importer.py             # workbook -> lists of model objects + issues
    db.py                   # SQLite schema, save_all, load_all
    export_json.py          # db -> web/data/schedule.json (includes precomputed conflicts)
    server.py               # stdlib HTTP API for live mode
  tests/
    rule_cases.json         # golden cases shared by Python and JS
    test_rules.py
    test_classify.py
    test_importer.py
  web/                      # GitHub Pages root
    index.html
    css/app.css
    js/data.js              # loads schedule.json, or /api/* if a server answers
    js/rules.js             # mirror of rules.py, same function names
    js/harbor.js            # SVG harbor: berth geometry, boat packing, animation
    js/timeline.js          # scrubber, play/pause, day index
    js/booking.js           # form, live check, explanation bar, suggestions
    js/audit.js             # import issues panel
    tests.html              # runs rule_cases.json against rules.js in the browser
    data/schedule.json      # committed output of export_json.py
  scripts/
    import.sh               # python3 -m dock.importer && python3 -m dock.export_json
    serve.sh                # python3 -m dock.server  (http://localhost:8000)
```

Data flow: `xlsx -> importer.py -> (dock.db, import_report.json) -> export_json.py -> web/data/schedule.json -> browser`. In static mode (GitHub Pages) the browser reads the JSON, runs `rules.js` for new bookings, and keeps demo bookings in `localStorage` (clearly labelled "demo bookings, this browser only"). In live mode (`scripts/serve.sh`) `data.js` detects that `GET /api/schedule` answers and switches: every check and booking goes to Python, and the JS rules are only used for the instant preview while typing. The UI is the same file in both modes; the mode is shown in the header so nobody is misled.

How UI talks to logic: `booking.js` builds a candidate `{berth_id, vessel_id|title, kind, start, end}`, calls `rules.check_booking(candidate, state)` (JS in static mode, `POST /api/check` in live mode) and receives a verdict object `{status, reasons[], load_by_day[], suggestions[]}`. The verdict object shape is identical in both languages and is what the explanation bar draws from.

API routes in `server.py` (JSON in, JSON out):
- `GET /api/schedule` -> berths, vessels, bookings, notes, issues, conflicts (same shape as schedule.json)
- `POST /api/check` body = candidate -> verdict, never writes
- `POST /api/bookings` body = candidate -> 201 with booking, or 409 with the verdict when status is not `ok` (a `force: true` field overrides with a recorded override reason, because a harbormaster sometimes knows better)
- `DELETE /api/bookings/<id>` -> 204 (only bookings with `status='manual'`; imported history is read-only by design)
- `GET /api/conflicts?from=&to=` -> conflict intervals
- `GET /api/suggest?berth=&start=&end=&vessel=` -> alternatives
Static files are served from `web/` by the same process so live mode is one command.

## Data model
Entities (SQLite tables, mirrored as dataclasses in `model.py` and as plain objects in JSON):

- `berth(id, name, length_ft INTEGER NULL, capacity_mode TEXT, active_from INTEGER, active_to INTEGER, map_x, map_y, map_angle)`. `capacity_mode` is one of `linear` (a pier face: several vessels end to end, constraint is total length), `single` (one occupant at a time: Inner Channel 55', the two South Floats), `untracked` (group rows like "North Finger Piers", "Small craft slips", "Marsh Landing": the sheet does not say how many slips exist, so bookings are recorded and drawn but no capacity verdict is issued; this is logged as a limitation, not hidden). `map_*` are drawing coordinates in feet.
- `vessel(id, canonical_key TEXT UNIQUE, display_name, prefix, length_ft INTEGER NULL, draft_ft INTEGER NULL, raft_ok BOOL, short_visit BOOL, source TEXT)`. `canonical_key` is the casefolded, whitespace-collapsed, length-stripped name so "Barge SALT DORY" and "Barge Salt Dory" are one vessel; `display_name` is the most frequent spelling. `source` is `science`, `yachts`, or `grid-only` (seen in the grid but not in a registry, so length is NULL).
- `booking(id, berth_id FK, kind TEXT, vessel_id FK NULL, title, start_date TEXT, end_date TEXT, occupies_full BOOL, source_sheet, source_cells, confidence TEXT, status TEXT, override_reason TEXT NULL, created_at)`. `kind` is `vessel`, `event` or `closure`. `confidence` is `merged` (from a merged cell), `inferred-run` (same text on consecutive days before 2009), `single-day`, or `stitched` (joined across a month boundary). `status` is `imported` or `manual`.
- `note(id, berth_id, date, text, source_sheet, source_cell)`: operational annotations ("ETA 1200") that are not bookings but are shown as small flags on the map so no information is lost.
- `import_issue(id, sheet, cell, kind, message, resolution)`: every ambiguity the importer resolved, with the rule it applied.

Invariants (enforced in `db.py` with CHECK constraints and in `rules.py`):
- Dates are ISO `YYYY-MM-DD` whole days; `end_date >= start_date`; a booking occupies every day from start to end INCLUSIVE. A vessel arriving Monday and leaving Wednesday has three occupied days; the sample grid marks days, not hours, so day granularity is the truth of the source. Times in notes ("Departs 0600") are kept as notes, not used to shorten a stay.
- Two bookings overlap iff `a.start <= b.end and b.start <= a.end`. Adjacent stays (one ends the 3rd, the next starts the 4th) do not overlap.
- Events and closures set `occupies_full = true`: they take the whole berth regardless of length. Vessels set it false.
- A vessel booking whose vessel has `length_ft IS NULL` can never be `ok`; the best it can be is `unverified`.
- Imported bookings are never modified by the app; a reviewer can always regenerate them from the workbook with `scripts/import.sh` and get byte-identical JSON (the exporter sorts deterministically), which is how the import is proven repeatable.

## Algorithms
All live in `rules.py` and are mirrored line for line in `rules.js`.

Constants: `CLEARANCE_FT = 10` (fender/line room between vessels moored end to end; a stated assumption, editable in one place), `DEFAULT_UNKNOWN_DRAW_FT = 40` (drawing only, never used in a verdict).

1. `overlaps(a, b)`: the inclusive interval test above. O(1).

2. `day_load(berth, bookings_on_day)`: returns `{n, known_sum, unknown_count, closure, event, load}` where `load = known_sum + CLEARANCE_FT * (n - 1)` for vessels. O(k) in occupants.

3. `check_day(berth, bookings_on_day)` -> one status for that berth-day, evaluated in this order and the first match wins:
   - any closure present and anything else present -> `closure` conflict (a closure with nothing else is fine; a closure alone is just a closed berth)
   - any event present and more than one booking -> `capacity` conflict (an event is the whole berth)
   - `capacity_mode == single` and `n > 1` -> `capacity` conflict
   - `capacity_mode == untracked` -> `untracked` (no verdict, drawn grey)
   - `linear`: if `known_sum + CLEARANCE_FT*(n-1) > berth.length_ft` -> `capacity` conflict (even with unknowns, the known part alone already overflows, so this is certain); else if `unknown_count > 0` -> `unverified`; else `ok`.
   The exact conflict rule in one sentence, for the interview: "On any day, a berth is double-booked if it has a closure plus anything, an event plus anything, more than one occupant in a single-occupancy berth, or, on a pier face, if the sum of the vessel lengths plus 10 feet of clearance between each pair exceeds the face length."

4. `fits(vessel, berth)`: `vessel.length_ft <= berth.length_ft` -> `ok`; greater -> `over-length`; either NULL -> `unverified`. This is checked independently of the day load because a 120-foot vessel alone on a 75-foot face is wrong even with nobody else there. Complexity O(1).

5. `find_conflicts(berths, bookings)`: sweep per berth. For each berth, collect breakpoints = every `start_date` and every `end_date + 1 day` of its bookings, sorted, deduplicated. Between consecutive breakpoints the occupant set is constant, so evaluate `check_day` once per segment (occupants found by scanning the berth's bookings, sorted by start, with a pointer that only moves forward). Consecutive segments with the same status and same occupant set are merged into one conflict interval `{berth_id, from, to, status, booking_ids, load, capacity}`. Complexity O(B_i log B_i + S * k) per berth where S is number of segments; for 2,660 bookings this runs in well under 100 ms in Python and is imperceptible in JS. A naive day-by-day loop (8,400 days x 6 berths) would also be fine, and the sweep is chosen because the output is naturally intervals, which is what the UI glows.

6. `check_booking(candidate, state)`: returns the verdict object. Steps: validate dates and berth existence; `fits`; then for every day in the candidate range compute `check_day` with the candidate added to the existing occupants (the candidate range is short, so per-day is fine here, O(days * k)). Status is the worst across days in the order `closure > capacity > over-length > unverified > ok`. `reasons[]` are human sentences with numbers ("2010-11-03: 240' face would hold 180' + 120' + 20' clearance = 320'"). `load_by_day[]` feeds the explanation bar.

7. `suggest(candidate, state)`: only called when status is not `ok`. Two searches, capped at 5 results total: (a) same berth, shift the whole range by +-1..14 days, keep the first windows that come back `ok`, nearest first; (b) same dates, every other berth in ascending `berth.length_ft - vessel.length_ft` (tightest fit first, because parking a 55-foot boat on the 410-foot face wastes the scarce long berth), keep those that are `ok`. Each suggestion is `{berth_id, start, end, why}`. Complexity O((28 + B) * days * k).

Edge cases handled and tested: single-day booking (start == end); booking spanning a year boundary; vessel with unknown length on an otherwise full face (result `capacity` if known part overflows, else `unverified`); two closures on the same berth (not a conflict, both are "closed"); event on an `untracked` group row (recorded, drawn, no verdict); booking on a berth that was not active that year (`active_from/to` violated -> `reasons` says "berth not in service in 2001", status `capacity`); candidate that exactly fills the face (`==` is ok, `>` is not); vessel in registry twice with different lengths (importer keeps the larger and logs an issue, because over-estimating length is the safe error for a fit check).

## Importer
`dock/importer.py`, run as `python3 -m dock.importer "data/Dock Schedule - Synthetic Sample.xlsx"`. It is written as small pure functions (`find_month_blocks`, `column_dates`, `berth_rows`, `cells_to_bookings`, `stitch_months`) so each can be unit-tested against a tiny hand-made workbook created in the test with openpyxl.

Strategy:
- Sheet routing by name: `^\d{4}$` -> year grid; `Science`, `Yachts` -> registry; `8YR Dock Summary` -> cross-check only; `Tours` -> skipped (logged as "not a berth booking source"; the dock tours are visits, not berth reservations, and the brief does not ask for them).
- Year grid parsing: walk rows; a cell matching `^(JANUARY|FEBRUARY|...|DECEMBER)\s*(\d{4})?$` (case-insensitive) starts a month block; the next row containing at least 20 integers in 1..31 is the day-number row and gives the column -> date map; following rows whose first non-empty cell matches a berth label regex `^(.*?)\s*(\d+)'\s*$` or a known group label are berth rows, until the next month header or an empty run of 3 rows. Layout eras (1997-2003, 2004-2013, 2014-2019) differ in where the header sits and whether the year is in the month cell; the parser is written to search rather than assume fixed offsets, and a test per era pins this down.
- Month header year disagreeing with the sheet name (2010's "NOVEMBER 2018"): the sheet name wins; issue kind `header-year-mismatch` with resolution "used sheet year 2010". Reason: the block position (11th and 12th in the 2010 sheet) and the day-of-week columns match 2010, and the 2018 sheet has its own November.
- Sheet whose first block is December: dated as `sheet_year - 1`; bookings from that block are compared to the previous year's sheet and dropped as duplicates when berth, dates and normalised title match; both the duplicate and any disagreement are logged (`dec-carryover-duplicate`, `dec-carryover-conflict`). If the two sheets disagree, the sheet that owns the year wins.
- Spans, 2009 onward: `ws.merged_cells.ranges` intersected with a berth row give `[first_col, last_col]` -> one booking, `confidence=merged`. Pre-2009: consecutive cells in the same berth row whose normalised text is identical are one booking, `confidence=inferred-run`; a single cell is `single-day`. Fill and border hints are NOT read, and this is an explicit assumption: the workbook is synthetic, its fills are inconsistent, and a run of identical names encodes the same information more reliably. A run that is broken by a note cell (e.g. "ETA 1200" in the middle) is still joined, because notes are removed before the run pass.
- Month-boundary splits: after all blocks of a sheet (and the December carry-over) are parsed, `stitch_months` joins bookings on the same berth with the same normalised title where `a.end + 1 day == b.start`, marks `confidence=stitched`, and logs `stitched-across-month`. The same pass also stitches across the year boundary, because every sheet is loaded before stitching.
- Cell classification (`classify.py`), ordered rules, first match wins, all case-insensitive:
  1. Note (not a booking): matches `\bETA\b|\bETD\b|departs?|arriv|fuel|delayed|weather|touch and go|^\d{3,4}$|@\s*\d{3,4}` -> `note` table, attached to the berth and day. The row is still parsed for other bookings.
  2. Closure: `rebuild|replacement|maintenance|restricted|no usage|closed|dredg` -> `closure`, `occupies_full`.
  3. Event: `sail day|campus|tour|holiday|road race|open house|regatta|event` -> `event`, `occupies_full`.
  4. Vessel: prefix regex `^(R/V|M/V|F/V|S/V|M/Y|OSV|Tug|Barge|USCG|NOAA|RV|MV)\b` -> `vessel`.
  5. Anything else -> `vessel` with issue `unclassified-text` so a human can reclassify; the demo's audit panel lists these first because they are the honest unknowns.
- Vessel identity: `canonical_key = casefold(collapse_ws(strip_len(strip_punct(text))))`; the display name is the most frequent raw spelling; every merge of two spellings is logged once (`name-variant-merged`).
- Registry parsing (`Science`, `Yachts`): for each row, join all string cells; length = first of `LOA:\s*(\d+)\s*'` or `(\d{2,3})\s*'` ; draft = `Draft:\s*(\d+)`; `raft_ok = 'raft' in text`; `short_visit = 'short visit' in text`; vessel matched to grid vessels by `canonical_key`. Registry vessels never seen in the grid are kept (they can be booked in the form). Grid vessels with no registry match get `length_ft = NULL`, `source=grid-only`, and one issue `length-unknown` each; this is the biggest honest gap and the UI draws them dashed.
- Berths: the six recurring labels are canonicalised by regex; lengths from the labels; `active_from/to` set to the first and last year the label appears; group rows become `untracked` berths. Rows in the 8YR summary that never appear in a grid (e.g. "Marsh Landing" if so) become `untracked` berths with an issue `berth-only-in-summary`.
- Cross-check: `import_report.json` includes, for 2006-2013, imported usage-days per berth per year next to the 8YR summary figures and the difference. It is a test with a tolerance (assert within 10% or list the berth-years that miss) and a small bar chart in the audit panel. Reason: it is the only independent number in the workbook, so it is the closest thing to a ground truth for the importer.
- Every issue has `sheet`, `cell` (e.g. `2010!F214`), `kind`, `message`, `resolution`. Counts by kind are printed at the end of the run and shown in the demo header ("2,6xx bookings, 1xx notes, 5x issues").

## Unique features
Ranked by impact per Baron-hour; each lists cost in Baron's time (understand, verify, be able to explain) and what it depends on.

1. To-scale harbor map with sliding boats and visible overhang. SVG whose unit is one foot: the 410' face is literally 410 units long, the 55' channel 55. Each vessel is a hull path scaled to its length and packed end to end with 10 ft gaps; a vessel longer than its berth is drawn past the end with the overhanging part hatched red; unknown-length vessels are dashed at 40 ft with a "?". Position changes animate with a CSS `transform` transition (400 ms), so scrubbing days makes boats slide in and out. Why it impresses: the reviewer sees the fit check instead of reading it, and it is exactly Baron's own "diagram or animation" idea done to scale. Cost: 1.25 h. Depends on: schedule.json, berth `map_*` coordinates.
2. 23-year timeline scrubber with play button. A range input over 8,401 days, a play/pause that advances one day every 80 ms (so a year takes about 30 s), keyboard arrows for single days, a date label and a per-berth occupancy strip under the slider showing where conflicts are so the reviewer can jump to them. Why: nobody else will let the reviewer watch 1997-2019 go by. Cost: 0.5 h. Depends on 1.
3. Conflicts glow and explain. Every interval from `find_conflicts` makes its berth pulse red (capacity/closure), amber (unverified) on the days it covers; clicking opens a card with the arithmetic ("180 + 120 + 20 clearance = 320 > 240"). Why: this is the facility's stated pain, shown as a picture and a sum. Cost: 0.5 h. Depends on rules.py output in JSON.
4. Booking form that refuses with a drawing. Pick berth, vessel (or event/closure title), dates; as you type, a horizontal "berth bar" shows the berth length with coloured segments for each occupant plus clearance and your candidate; overflow spills past the bar edge in red; the verdict sentence and suggestion chips ("South Float West, same dates: fits with 35' to spare") appear under it; the submit button is disabled unless ok (with an "override with reason" checkbox for realism). Why: converts the rule into an instrument the harbormaster would actually use. Cost: 0.75 h. Depends on rules.js, suggest.
5. Rules parity badge. On load, `rules.js` recomputes `find_conflicts` over the full imported dataset and compares it with the Python-computed list embedded in schedule.json; the header shows "Rules parity: Python 57 / JS 57 conflicts, identical". `tests.html` runs the same golden `rule_cases.json` the Python tests use. Why: it answers the obvious interview question "your demo runs JS but your backend is Python, how do you know they agree?" with a live proof. Cost: 0.25 h. Depends on 3 and the golden file.
6. Import audit panel. A side drawer listing every `import_issue` grouped by kind; clicking one jumps the timeline to that day and highlights the booking; the 8YR summary reconciliation bar chart lives at the bottom. Why: the club grades "assumptions you made", and this makes each assumption a visible, clickable record instead of a paragraph. Cost: 0.5 h. Depends on importer issues in JSON.
7. Shareable URL state. `#day=2010-11-03&berth=np-east` reproduces a view, so Baron can put links to specific conflicts in the README. Cost: 0.1 h. Depends on 2.
8. Live mode switch. The same page against `server.py` shows "Live: SQLite" instead of "Demo: static JSON"; bookings persist in the database. Why: proves the backend is not decorative. Cost: 0.25 h (mostly running it once and reading server.py). Depends on server.py.

## Phases
Baron-hours are for understanding, running, verifying and rehearsing; Claude Code types. Each phase ends with an "explain-back": Baron explains the phase to Claude in their own words and Claude asks two follow-ups, because the interview will.

Phase 0 - Tooling and repo skeleton (0.75 h, mostly waiting on downloads).
Goal: a working `git`, `python3.12`, `gh`, `openpyxl`, an empty public repo with README, the folder layout above, and GitHub Pages enabled on `main:/web`.
Steps: follow `docs/GITHUB_GUIDE.md` parts 1-2; `python3.12 -m pip install --user openpyxl`; `gh repo create dock-scheduler --public --source . --push`; enable Pages; push a placeholder `web/index.html` that says "Harbormaster - loading" and confirm the public URL renders.
Exit criteria: `git --version && python3.12 -c "import openpyxl"` succeeds; Pages URL returns the placeholder.
Baron must be able to explain: what a commit, push and Pages deployment are; why `.gitignore` excludes `dock.db` but not `web/data/schedule.json` (one is regenerable local state, the other is the demo's data and must be served).

Phase 1 - Look at the data, fix the rules and the model (1.0 h).
Goal: Claude writes `scripts/explore_workbook.py` that prints, for three sheets (1999, 2010, 2016), the first 15 rows and any merged ranges; Baron reads the output next to the workbook in Numbers/Excel and confirms the three eras and the 2010 mislabel with their own eyes. Then `model.py`, `rules.py`, `tests/rule_cases.json` and `tests/test_rules.py` are written and pass.
Steps: run the explorer; agree the conflict rule sentence and the constants; read `rules.py` line by line (it is under 150 lines); run `python3 -m unittest tests.test_rules -v`; deliberately change `CLEARANCE_FT` to 0 and watch which test fails, then restore.
Exit criteria: all rule tests green; Baron can say the conflict rule from memory.
Baron must be able to explain: end-inclusive days, why events occupy the whole berth, why unknown length is "unverified" not "ok", the sweep-by-breakpoints idea.

Phase 2 - Importer (1.25 h).
Goal: `python3 -m dock.importer` produces `dock.db`, `import_report.json`, and `export_json.py` produces `web/data/schedule.json`; `tests/test_importer.py` and `tests/test_classify.py` pass on tiny synthetic workbooks built inside the tests.
Steps: Claude writes it in the order find_month_blocks -> column_dates -> berth_rows -> classify -> cells_to_bookings -> stitch -> registry -> db; after each function Baron runs the importer and reads the issue counts; Baron spot-checks five bookings against the workbook by cell address (the JSON keeps `source_cells`), including one from 1999 (inferred run), one merged 2015 stay, one stitched across a month, the 2010 mislabel, and one December carry-over.
Exit criteria: about 2,600+ bookings, notes separated, the 8YR reconciliation within tolerance for most berth-years, deterministic output (run twice, `diff` is empty).
Baron must be able to explain: each ambiguity and the rule chosen for it, why notes are not bookings, why the sheet name beats the header year, what `confidence` means and why a reviewer should care.

Phase 3 - The show: harbor map, timeline, conflicts (1.25 h).
Goal: `index.html` renders the harbor from `schedule.json`; scrubbing shows boats sliding; conflicts glow; clicking a berth shows the arithmetic; parity badge shows identical counts.
Steps: Claude writes `data.js`, `rules.js`, `harbor.js`, `timeline.js`, `tests.html`; Baron opens `tests.html` and sees the golden cases pass in JS; Baron scrubs to the known conflicts found in Phase 2 and confirms they glow; Baron reads `harbor.js`'s `packBerth()` (the function that turns a list of vessels into x offsets) because it is the visual expression of the rule.
Exit criteria: Pages URL shows the animated harbor; parity badge identical; no console errors; works in Safari and Chrome.
Baron must be able to explain: how one foot maps to one SVG unit, how packing computes offsets, why the JS rules mirror the Python and how parity is proven, why a per-day filter of 2,660 bookings is fast enough.

Phase 4 - Booking form, suggestions, live server (0.75 h).
Goal: the form refuses bad bookings with the berth bar; suggestions appear; `scripts/serve.sh` runs live mode where a booking persists in SQLite.
Steps: Claude writes `booking.js`, `suggest` in both languages, `server.py`; Baron tries the three canonical failures (over-length vessel on the 75' face, three vessels on the 240' face, a vessel on a closure day) and one success; runs live mode, books, restarts the server, confirms it is still there; reads `server.py`'s route table.
Exit criteria: the 409 verdict from Python and the JS verdict for the same candidate are identical (Baron compares them once in the browser network tab).
Baron must be able to explain: why the server is stdlib, what a 409 is, what "override with reason" is for, how suggestions are ranked.

Phase 5 - README, assumptions, audit panel, rehearsal (1.0 h).
Goal: README with demo link, screenshots (or a 10-second GIF recorded with QuickTime), run/test instructions, architecture diagram (a text diagram is fine); `ASSUMPTIONS.md`; audit panel wired; a rehearsal of the eight interview questions.
Steps: Claude drafts, Baron edits in their own voice (the README must sound like Baron); Baron runs the full path from a fresh clone in a temporary folder (`git clone`, `pip install`, `scripts/import.sh`, `python3 -m unittest`, `scripts/serve.sh`) to prove the instructions are true; Baron answers the eight questions out loud with a timer.
Exit criteria: fresh-clone run works; every assumption in ASSUMPTIONS.md corresponds to an importer issue kind or a rules constant; Baron answers all eight questions without notes.
Baron must be able to explain: everything above, plus what they would do next with more time (the out-of-scope list).

Total: 6.0 Baron-hours.

## Testing
Python (`python3 -m unittest -v`, stdlib):
- `tests/rule_cases.json`: golden cases, each `{name, berths, bookings, candidate?, expect}`; both `test_rules.py` and `web/tests.html` load this file, so a rule change must update one file and both implementations.
- `test_rules.py`: `test_overlap_inclusive_end`, `test_adjacent_days_do_not_overlap`, `test_single_berth_two_vessels_conflict`, `test_linear_two_vessels_fit_exactly` (180 + 50 + 10 == 240 is ok), `test_linear_three_vessels_over_by_clearance` (100+100+30 = 230, plus 20 clearance = 250 > 240), `test_unknown_length_is_unverified_not_ok`, `test_unknown_length_but_known_part_overflows_is_capacity`, `test_event_blocks_berth`, `test_closure_blocks_vessel`, `test_two_closures_not_a_conflict`, `test_vessel_longer_than_berth_alone_is_over_length`, `test_untracked_berth_gives_no_verdict`, `test_berth_inactive_year_rejected`, `test_find_conflicts_merges_adjacent_segments`, `test_suggest_prefers_tightest_fit`, `test_suggest_nearest_dates_first`, `test_check_booking_worst_status_wins`.
- `test_classify.py`: notes vs bookings for every example string in the brief ("ETA 1200", "Departs 0600", "Fueling @0800", "Delayed due to weather", "Touch and go", "Fuel truck" -> note; "Float rebuild - no usage permitted", "Bollard replacement, west face", "Dock maintenance - restricted access" -> closure; "Community sail day", "Campus event", "Student tour", "Holiday", "Road race - access limited" -> event; "R/V High Drift", "Barge SALT DORY" -> vessel); `test_canonical_key_merges_capitalisation`; `test_length_parsed_from_name_and_loa`.
- `test_importer.py`: builds tiny workbooks with openpyxl in `setUp`: `test_berth_label_length`, `test_month_header_year_mismatch_uses_sheet_year`, `test_first_block_december_is_previous_year`, `test_december_carryover_deduplicated`, `test_merged_cells_become_one_booking`, `test_pre2009_identical_run_becomes_one_booking`, `test_note_inside_run_does_not_split_it`, `test_stitch_across_month_boundary`, `test_unclassified_text_logged`, `test_export_is_deterministic`.
- `test_reconciliation.py` (runs on the real workbook, skipped if the file is missing): imported usage-days vs 8YR summary within 10% for at least 80% of berth-years, printing the misses.
JavaScript: `web/tests.html` runs `rule_cases.json` through `rules.js` and prints a table; the parity badge on `index.html` is a permanent integration test on real data.
Manual: Phase 4's three canonical failures and the fresh-clone run in Phase 5. Browser check in Safari and Chrome on the Mac only.

## Risks
- Importer eats the budget (most likely). Mitigation: a hard cap of 1.25 h; any sheet or block that fails to parse is logged as an issue and skipped, never crashes; the demo works with whatever imported. The README says which sheets imported cleanly.
- Two implementations of the rules drift. Mitigation: shared golden file, parity badge, and the rules are deliberately kept under 150 lines with identical function names in both languages.
- Baron cannot explain something Claude typed. Mitigation: explain-back at the end of each phase; the interview_points section is rehearsed with a timer; anything Baron cannot explain after two tries is cut, not kept.
- Homebrew install stalls (network, password prompts). Mitigation: python.org's macOS installer as fallback; the project only needs python3 and pip.
- openpyxl merged-cell edge cases (merges spanning a month header, or vertical merges). Mitigation: importer only honours horizontal merges within a berth row and logs others.
- SVG performance with many boats. Mitigation: only the boats present on the current day are in the DOM (at most a few dozen); a full-history heatmap strip under the slider is one rect per conflict interval, not per day.
- GitHub Pages caching a stale schedule.json. Mitigation: `data.js` appends `?v=<build stamp>` written by `export_json.py`.
- Reviewer opens on a phone. Mitigation: the SVG scales with viewBox; the form stacks; nothing else is promised.
- Synthetic data may contain no real over-length or over-capacity cases. Mitigation: the importer report counts them; if zero, the README's "try it" links point the reviewer at the form to create one, and the audit panel still shows the importer's work.

## Assumptions
1. A booking occupies whole days, end date inclusive; the grid records days, not hours.
2. Two vessels moored end to end on a pier face need 10 feet of clearance between them; this constant is editable in one place and the demo says so.
3. North Pier West (410'), North Pier Face (75') and North Pier East (240') are linear-capacity berths; Inner Channel (55') and the two South Floats (90') hold one occupant at a time.
4. "North Finger Piers", "Small craft slips" and "Marsh Landing" are groups of unknown slip count, so they are recorded and drawn but receive no capacity verdict.
5. Events and closures occupy the whole berth for their whole date range.
6. A vessel whose length is unknown can be booked but the verdict is "unverified", never "ok".
7. Vessel lengths come only from the Science and Yachts sheets; a vessel listed twice keeps the larger length because over-estimating is the safe error for a fit check.
8. Draft, tide and water depth are not modelled; the workbook has draft for a few vessels but no depths for berths.
9. Rafting alongside ("Will raft alongside if needed") is recorded as a vessel flag but does not relax the capacity rule; the harbormaster may use the override with a reason.
10. Names that differ only in case, spacing or punctuation are the same vessel.
11. Cells such as "ETA 1200" or "Fuel truck" are operational notes, not bookings, and are kept as notes.
12. Pre-2009 spans are inferred from identical text on consecutive days; fills and borders are not read.
13. When a month header's year disagrees with the sheet name, the sheet name is correct.
14. A December block at the top of a sheet belongs to the previous year and duplicates of the previous sheet are dropped.
15. The 8YR Dock Summary is treated as an independent check on the importer, not as a source of bookings.
16. The Tours sheet records dock visits, not berth reservations, and is not imported.
17. Imported history is read-only in the app; new bookings are the only writes.
18. The static demo stores new bookings in the browser only; the live mode stores them in SQLite; both apply the same rules.

## Out of scope
Cut first if time runs short, in this order: the 8YR reconciliation chart in the UI (keep it as a test); the shareable URL; the audit panel drawer (keep the issue counts in the header and the JSON file); the "override with reason" checkbox; suggestions across dates (keep other-berth suggestions). Not attempted at all: user accounts or authentication; editing or deleting imported bookings; rafting arithmetic; draft, depth and tides; the Tours sheet; hourly arrivals and departures; multi-user concurrency; hosting the Python server anywhere but a laptop; mobile-specific layout; printing or PDF export; reading fill and border hints in pre-2009 sheets; a database migration story.

## Demo script
Minute 0:00 - The reviewer clicks the Pages link in the README. The header reads "Harbormaster - 2,6xx bookings imported from 23 sheets - Rules parity: Python 57 / JS 57 - Demo: static JSON". Below is the harbor drawn to scale: the long north pier across the top with its three faces labelled 410', 75', 240', the 55' Inner Channel, the two 90' South Floats. The date reads 1997-01-01 and a few boats sit at berths.
0:15 - They press Play. Days tick by at 80 ms each; boats slide in, sit for their stay, slide out. A tug and a barge pack end to end along the 240' face with visible gaps. A small "Community sail day" banner appears on a South Float and blocks it.
0:40 - The strip under the slider has red ticks. They click one; the timeline jumps to that day; the 240' face pulses red; the card says "Capacity: 180' + 120' + 20' clearance = 320' > 240'. Bookings: R/V ..., M/V ... Source: 2010!F214, 2010!F215". A grey note flag on the same day reads "ETA 1200".
1:00 - They scrub to a dashed boat with a "?" and hover: "Length unknown - not in Science or Yachts registry - verdict unverified". They open the audit drawer: issues grouped by kind, "header-year-mismatch: sheet 2010, cell B201, 'NOVEMBER 2018' -> used 2010".
1:20 - They open the booking form, choose North Pier Face 75', pick "R/V High Drift 120'", and any dates. Before they click anything, the berth bar shows a 120' segment spilling 45' past the 75' bar in red, the sentence "Does not fit: 120' vessel, 75' berth", and chips: "North Pier East 240' - fits, 120' spare", "North Pier West 410'". They click a chip; the form switches berth, the bar turns green, Submit enables. They submit; the boat slides into the map on those dates.
1:50 - They open `tests.html` in a new tab: 17 golden cases, all green in JS, and the README shows the same cases green in Python. They scroll the README to "How it works" and "Assumptions" and see the numbered list matching what they just clicked.

## Interview points
1. "How do you define a double-booking?" On any day a berth is over-booked if it has a closure plus anything else, an event plus anything else, more than one occupant in a single-occupancy berth, or, on a pier face, if the sum of vessel lengths plus 10 feet of clearance per gap exceeds the face length. I chose per-day evaluation because the workbook records days, and I chose linear capacity for the long faces because a 410-foot face obviously holds several vessels end to end, so "two bookings overlap" alone would produce false alarms.

2. "How do you check that a vessel fits?" Independently of who else is there: vessel length must be less than or equal to the berth length. Lengths come from the registry sheets; when a length is unknown the result is "unverified", never "ok", because a scheduling tool that says yes when it does not know is worse than the grid it replaces. The map draws unknown-length vessels dashed so the gap is visible.

3. "Your demo runs in JavaScript but your backend is Python; how do you know they agree?" The rules are about 150 lines and implemented twice with the same function names, and both implementations run the same golden file `tests/rule_cases.json`. On top of that the page recomputes every conflict over the full dataset in JS at load and compares with the Python-computed list embedded in the JSON; the header shows the two counts. If I had one language on both sides I would not need this, but Python in the browser (Pyodide) is a 10 MB download and a static demo was the point.

4. "How did you handle the messy spreadsheet?" I wrote the importer as small functions that search for structure (month header, day-number row, berth rows) rather than assume fixed offsets, because there are three layout eras. Every ambiguity has a written rule and produces a logged issue: the sheet name beats a mislabelled month header, a leading December belongs to the previous year and duplicates are dropped, merged cells are spans from 2009, before that identical text on consecutive days is a span, and stays are stitched across month boundaries. The 8YR summary sheet is used as an independent check of usage-days.

5. "What did you decide was not a booking?" Cells like "ETA 1200", "Departs 0600", "Fuel truck" are operational notes. They are kept in a notes table and drawn as flags so nothing is lost, but they do not occupy a berth. I keyed this on a regex list that I tested against every example I found; anything the classifier cannot place is kept as a vessel and flagged "unclassified" so a person reviews it.

6. "Why SQLite and a stdlib server instead of a framework?" The facility's need is one harbormaster on one machine; the schema is four tables; SQLite ships with Python and enforces the date invariant with a CHECK constraint. A framework would add an install and concepts without adding a feature I use. I say in the README that the server is single-threaded and would be swapped for FastAPI if the facility needed multiple users.

7. "Why the animated map, isn't that just polish?" Length is the whole problem: the two failure modes are "too long for the berth" and "too much total length on the face". Drawing everything at one foot per unit makes both failures visible without reading a number, and the same packing function that positions boats is the capacity arithmetic. The animation is a CSS transition on a transform, about ten lines; the timeline is a range input. The cost was low and it doubles as a visual test of the importer, because a mis-parsed date shows up as a boat in the wrong month.

8. "What would you do next?" Model rafting (vessels alongside each other count once for length), read draft against berth depth, add the Tours sheet as a separate visits view, replace the stdlib server with FastAPI and add users, and get real vessel lengths from the facility for the grid-only vessels, which is the biggest source of "unverified" verdicts.
