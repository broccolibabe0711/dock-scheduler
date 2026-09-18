# Proposal: **Berthbook** (angle: Domain-model purist)

## Name

**Berthbook** - a ledger of who is on which berth on which day, with a conflict engine that never lies about what it does not know. Repo folder stays `dock-scheduler`; "Berthbook" is the package name (`berthbook/`).

## Angle

Correctness and clean structure first. The domain (effective-dated berths, end-inclusive day intervals, linear capacity vs exclusive slips, vessels vs events vs closures vs notes, unknown lengths) is modelled precisely in one pure Python module with explicit invariants and an exhaustively tested conflict engine. The UI is deliberately plain: a list, a form, a check button, and one honest SVG that draws the capacity computation. Uniqueness comes from rigor a reviewer rarely sees from a student: three-valued verdicts, provenance on every imported cell, an importer that reconciles itself against the workbook's own summary sheet, and a fuzz test that proves the fast conflict check equals the slow one.

## Pitch

The facility's two pains are "did we double-book a day?" and "does this boat actually fit that berth?" Both are questions with a precise answer once you write down what a berth, a day, and a booking are. Berthbook does exactly that: a 300-line pure-Python domain module defines berths as either *linear* (a 410' pier face holds vessels end-to-end with clearance between them) or *exclusive* (a small slip holds one thing), bookings as end-inclusive day ranges, and every check returns OK, CONFLICT or UNKNOWN with a reason - UNKNOWN because the 23-year workbook gives lengths for only some vessels and the system refuses to pretend otherwise. A separate importer reads all 23 grid years across their three layout eras, classifies the 573 distinct cell values into vessel / event / closure / note, records every ambiguity it resolved (mislabelled 2010 months, cross-month splits, fill-inferred spans) in an issues table, and then checks its own output against the workbook's "8YR Dock Summary". A small Flask API and a vanilla-JS page sit on top; a read-only copy of the engine's output is published to GitHub Pages so a reviewer can see the historical conflict audit without installing anything.

## Stack (and why)

| Layer | Choice | Why | Install |
|---|---|---|---|
| Language | Python 3.12 | Club default; Baron can read it; stdlib has `dataclasses`, `datetime.date`, `sqlite3`, `unittest`, `json`, `http`. | `brew install python@3.12` (already planned) |
| Domain + engine | Pure Python, stdlib only | The core must be importable with zero dependencies so tests run anywhere and nothing hides the logic. | none |
| Workbook reading | `openpyxl` | Only mature pure-Python `.xlsx` reader that exposes `merged_cells.ranges` and cell fills, both needed for the pre-2009 span inference. | `pip install openpyxl` |
| Storage | SQLite via stdlib `sqlite3`, schema in `schema.sql` with CHECK constraints | Zero install, single file, and CHECK constraints let the invariants be enforced twice (Python and DB), which is a talking point. | none |
| API | Flask | Smallest readable web framework; a route is a decorated function Baron can explain line by line. FastAPI would add pydantic + uvicorn and async concepts for no gain here. | `pip install flask` |
| Frontend | Vanilla HTML/CSS/JS, one `fetch()` per action, one inline SVG | No build step; the club said polish is not the point; every line is explainable. | none |
| Tests | `pytest` | Plain `assert` tests; readable failures. | `pip install pytest` |
| Static demo | GitHub Pages serving `docs/demo/` with a pre-computed `export.json` | Reviewer sees the historical audit and the pier-load diagram with no install; no logic is duplicated in JS because the page only renders engine output. | none |
| Hosting of backend | none (run locally: `python -m berthbook.api.app`) | A public write-capable backend needs auth; out of scope. | none |

Total installs: Homebrew, python@3.12, gh (already planned) + three pip packages inside `.venv`. `requirements.txt` pins them.

## Architecture

```
dock-scheduler/
  berthbook/
    __init__.py
    domain/
      models.py      # Berth, Vessel, Booking, Note, DayRange (frozen dataclasses) + invariant checks
      verdict.py     # Verdict enum (OK, CONFLICT, UNKNOWN) and Finding dataclass
      rules.py       # overlaps(), fit_check(), day_load(), find_conflicts() - the conflict engine, pure
      suggest.py     # suggest_berths(): ranks berths for a vessel over a range using rules.py
    importer/
      classify.py    # classify_cell(text) -> CellKind + payload; the rules table for 573 values
      registry.py    # parse "Science"/"Yachts" sheets into Vessel rows (LOA/draft extraction)
      grid.py        # locate month blocks, berth rows, day columns per layout era; emit raw runs
      spans.py       # merge runs: merged cells, repeated names, fill continuity, cross-month joins
      reconcile.py   # compare imported usage-days vs "8YR Dock Summary"
      run.py         # python -m berthbook.importer.run data/Dock\ Schedule*.xlsx -> data/berthbook.sqlite + import_report.md
    storage/
      schema.sql     # tables + CHECK constraints
      db.py          # open_db(), load_bookings(berth_id, day_range), insert_booking(), ... thin repository
    api/
      app.py         # Flask routes; converts rows <-> domain objects; calls rules.py; returns JSON
    export.py        # dumps berths, bookings, conflict audit to docs/demo/export.json for Pages
  web/
    index.html, app.js, styles.css, pier.js (SVG load strip)
  docs/
    decisions/0001-end-inclusive-days.md ... 0007-unknown-is-not-ok.md
    demo/            # GitHub Pages: copy of web/ + export.json, read-only
    GITHUB_GUIDE.md
  tests/
    test_models.py test_rules.py test_suggest.py test_classify.py test_spans.py
    test_importer_smoke.py test_reconcile.py test_db_constraints.py test_api.py test_fuzz.py
  data/
    Dock Schedule - Synthetic Sample.xlsx
    berthbook.sqlite        # generated (gitignored); import_report.md is committed
  requirements.txt  README.md
```

Data flow: `xlsx -> importer -> sqlite` (once). `browser -> fetch /api/... -> Flask -> db.py rows -> domain objects -> rules.py -> JSON -> browser`. The dependency arrows point one way: `domain` imports nothing from the project; `importer` and `api` import `domain`; `storage` imports `domain` only for dataclass conversion; `web` knows only JSON. Why: the club grades structure; a one-way dependency graph is the clearest structural decision to explain, and it is what lets `rules.py` be tested with no database or server.

## Data model

All dates are `datetime.date`; there is no time-of-day anywhere in the schedule (times appear only inside Notes as text). Every range is **end-inclusive**: a stay `2015-06-03 .. 2015-06-05` occupies three grid cells, matches how the spreadsheet is read, and `nights = days - 1` is never needed. Overlap is `a.start <= b.end and b.start <= a.end`.

**Berth** (`berths`): `id`, `name` ("North Pier West"), `length_ft` (nullable; null for Marsh Landing and group rows whose length is not in the workbook), `mode` in {`linear`, `exclusive`}, `clearance_ft` (default 10, per-berth so the facility can tune it), `parent_id` (nullable; finger-pier slips belong to the "North Finger Piers" group), `effective_from`, `effective_to` (nullable = still active), `source` ("grid", "summary-only").
Invariants: `length_ft is null or > 0`; `effective_from <= effective_to`; a berth with `mode = exclusive` ignores clearance; a group row (`parent_id` null and children exist) is never bookable itself.

**Vessel** (`vessels`): `id`, `canonical_key` (unique; casefolded, prefix-normalised, length suffix stripped), `display_name` (most frequent spelling in the grid), `prefix` (R/V, M/V, F/V, S/V, M/Y, OSV, Tug, Barge, null), `loa_ft` (nullable), `draft_ft` (nullable), `rafts_ok` (bool, from registry note "Will raft alongside if needed"), `source` in {registry-science, registry-yachts, grid-only}, `registry_note` text.
Invariant: `loa_ft is null or > 0`. No invariant says `loa_ft` must exist - unknown length is a first-class state.

**Booking** (`bookings`): `id`, `berth_id`, `kind` in {`vessel`, `event`, `closure`}, `vessel_id` (required iff kind = vessel), `title` (required iff kind != vessel; "Community sail day"), `start_day`, `end_day`, `rafted` (bool; true means it lies alongside another vessel and consumes no linear length), `needs_review` (bool; set by importer on unclassified cells), `override_reason` (nullable text; non-null only if a user knowingly saved a CONFLICT), `source_sheet`, `source_cell` (e.g. "2010!F23"), `span_confidence` in {exact, inferred, single}.
Invariants: `start_day <= end_day`; `(kind = 'vessel') = (vessel_id is not null)`; `[start_day, end_day]` within the berth's effective window; `rafted` only when `kind = vessel`. These are CHECK constraints in `schema.sql` and `Booking.__post_init__` raises `InvariantError` with the same messages.

**Note** (`notes`): `id`, `berth_id`, `day`, `text` ("ETA 1200"), `source_cell`, optional `booking_id` when the note sat in a cell that also named a vessel. Notes never take capacity. Why a separate table rather than a booking kind: "Fuel truck" is not an occupancy, and mixing it in would make every capacity query filter it out.

**ImportIssue** (`import_issues`): `id`, `code` (enum below), `sheet`, `cell`, `raw_text`, `resolution` (what the importer decided), `booking_id` (nullable). This table is the importer's honesty ledger and is shown in the UI as provenance.

Capacity semantics per booking kind:
- `vessel` on a linear berth: consumes `loa_ft` (plus one clearance gap between neighbours) unless `rafted`; if `loa_ft` is null the day is UNKNOWN.
- `vessel` on an exclusive berth: consumes the whole berth.
- `event`: consumes the whole berth regardless of mode (a community sail day needs the float).
- `closure`: consumes the whole berth; any other booking on that berth that day is a CONFLICT; two closures overlapping is OK (repair notes can overlap).

## Algorithms

**Exact conflict rule.** For berth `b` and day `d`, let `A` be the bookings on `b` active on `d` (end-inclusive overlap). Then:
1. If `A` contains a `closure` and any non-closure booking: CONFLICT (`CLOSED_BERTH`).
2. Else if `A` contains an `event` and `|A| > 1`: CONFLICT (`EVENT_EXCLUSIVE`).
3. Else if `b.mode == exclusive` and `|A| > 1`: CONFLICT (`SLIP_DOUBLE_BOOKED`).
4. Else if `b.mode == linear`: let `V` = non-rafted vessel bookings in `A`, `n = |V|`. If any vessel in `V` has `loa_ft` null: UNKNOWN (`LENGTH_UNKNOWN`, listing which). Else `load = sum(loa) + clearance * max(n - 1, 0)`; if `b.length_ft` is null: UNKNOWN (`BERTH_LENGTH_UNKNOWN`); if `load > b.length_ft`: CONFLICT (`CAPACITY_EXCEEDED`, with load and length); else OK with `slack = length - load`.
5. Else OK.

Why `clearance * (n-1)` rather than `clearance * n`: one vessel alone on a 90' float that is exactly 90' fits; the clearance is between boats, not at the ends. This is a stated assumption (see Assumptions) and a one-line change if the facility disagrees.

**Fit check** `fit_check(vessel, berth) -> Finding`: UNKNOWN if `vessel.loa_ft` or `berth.length_ft` is null; CONFLICT `DOES_NOT_FIT` if `loa_ft > length_ft` (rafting does not help: a 120' boat cannot raft on a 90' float); else OK. O(1). Runs before the day check so the error message says "does not fit" rather than "capacity exceeded".

**Day load / single booking check** `check_booking(candidate, existing, berth) -> list[Finding]`: fit check, effective-window check, then for each day in the candidate's range compute the rule above with `A = active(existing + [candidate], day)`. Complexity O(D * k) with D = days in range and k = bookings on that berth in the window (both small: k rarely exceeds 8). Adjacent findings with the same code on consecutive days are collapsed into one Finding with a day range so the UI shows "CAPACITY_EXCEEDED 2015-06-03..06-05 (load 530' > 410')" not three lines.

**Historical audit** `find_conflicts(bookings, berths) -> list[Finding]`: sweep line per berth. Sort event points `(start_day, +1, booking)` and `(end_day + 1 day, -1, booking)`; walk them maintaining the active set; evaluate the rule once per distinct point (not per day) because the active set only changes at points; findings are emitted for the interval between consecutive points. O(n log n) for n bookings. Why a sweep: 2,660 bookings * 23 years of days would be fine brute-force too, but the sweep is the correct algorithm and the fuzz test proves it agrees with brute force, which is exactly the kind of thing an interviewer probes.

**Suggestion** `suggest_berths(vessel, day_range, berths, bookings) -> list[Suggestion]`: for each berth effective over the whole range, run `check_booking`; keep OK and UNKNOWN; rank OK by ascending `min_slack` over the range (tightest fit first, so a 55' boat is sent to Inner Channel, not to the 410' face), then UNKNOWN. Berths that yield CONFLICT are returned in a separate list with the reason so the user sees why. O(B * D * k).

Edge cases covered by tests: one-day booking (start == end); bookings that touch but do not overlap (end = other.start - 1 day) are OK; a booking crossing Dec 31; a booking starting the day a berth's `effective_to` ends; rafted vessel plus two non-rafted vessels; vessel longer than a linear berth alone (fit fails before capacity); closure overlapping closure (OK); closure overlapping event (CONFLICT); event on a linear berth with one small vessel (CONFLICT); unknown-length vessel alone (UNKNOWN, not OK); known vessels already over capacity plus an unknown one (CONFLICT wins over UNKNOWN - the check evaluates known load first and reports both); leap day 2016-02-29; empty berth list; `needs_review` bookings counted as exclusive.

## Importer

Entry point `python -m berthbook.importer.run "data/Dock Schedule - Synthetic Sample.xlsx"`. Idempotent: drops and rebuilds `berthbook.sqlite`, writes `data/import_report.md`. Order of work is chosen to bank value early: era 3 (2014-2019, cleanest) first, then 2009-2013 (merged cells), then 1997-2008 (inferred spans). If the pre-2009 era is not done by the phase deadline, it ships with those sheets listed as "not imported" in the report - honesty over coverage.

Steps:
1. **Registry** (`registry.py`): for each row in Science and Yachts, extract a name and length with two regexes: trailing `(\d+)'` on the name ("R/V High Drift 120'") and `LOA:\s*(\d+)'` / `Draft:\s*(\d+)'` anywhere in the row. Build `Vessel` with `canonical_key`. Rows with no vessel-looking name are skipped and logged `REGISTRY_ROW_SKIPPED`. Duplicate keys with different lengths: keep the first, log `REGISTRY_LENGTH_CONFLICT`.
2. **Block detection** (`grid.py`): scan each year sheet for cells matching `^([A-Z]+)\s+(\d{4})$` (month header). Below each header, the first row containing at least 20 integers 1..31 is the day row; the column of "1" anchors day 1. Berth rows are the rows below whose first non-empty cell matches a known berth name or `(\d+)'` suffix; a trailing colon marks a group header whose following unlabelled rows become child slips (`North Finger Piers` -> `North Finger Piers slip 1..k`, exclusive, effective from that year). Era differences (header row offsets, label columns) are handled by searching rather than by fixed coordinates, so one code path serves all three eras; the era is recorded per sheet only for the report.
3. **Cell classification** (`classify.py`): a list of `(regex, kind)` rules applied in order: note patterns first (`\bETA\b`, `\bDeparts?\b`, `Fueling`, `Fuel truck`, `Delayed`, `Touch and go`, `^\d{4}$`), then closure keywords (`rebuild`, `replacement`, `maintenance`, `restricted`, `no usage`, `closed`), then event keywords (`sail day`, `campus event`, `tour`, `holiday`, `road race`), then vessel prefixes (`^(R/V|RV|M/V|MV|F/V|S/V|M/Y|OSV|Tug|Barge)\b`), then a fallback: if the text matches a registry `canonical_key` it is a vessel. A cell that matches both a vessel and a note pattern ("R/V Foo ETA 1200") yields a vessel booking plus a linked Note, logged `SPLIT_VESSEL_AND_NOTE`. A cell with two vessel prefixes separated by `/`, `&`, `+` yields two bookings, logged `SPLIT_MULTI_VESSEL`. Anything unmatched becomes `kind = event`, `needs_review = true`, logged `UNCLASSIFIED` - conservative, because a missed occupancy is the failure the facility fears most. `test_classify.py` holds a golden table of ~60 real values from the workbook.
4. **Spans** (`spans.py`), in priority order: (a) a merged range from `ws.merged_cells.ranges` is an exact span (`span_confidence = exact`); (b) consecutive day cells in the same berth row with equal `canonical_key` are one run (`exact`); (c) pre-2009 only: an empty cell whose fill colour equals the fill of the run to its left, and which is not the last day of the month, extends the run (`inferred`, logged `SPAN_INFERRED_FROM_FILL` with the colour); (d) otherwise a single day (`single`). Then **cross-month join**: a run ending on the last day of a month and a run starting on the 1st of the next month, same berth, same key, become one booking (logged `JOINED_ACROSS_MONTH`). Runs never join across a different key, so "Barge SALT DORY" and "Barge Salt Dory" do join (same key) but "R/V A" and "R/V B" do not.
5. **Dates**: the year comes from the **sheet name**, never the header; a header year that disagrees (the 2010 sheet's "NOVEMBER 2018") is logged `HEADER_YEAR_MISMATCH` and the month is taken from the header. A December block appearing before the January block in sheet Y is assigned year Y-1 and logged `LEADING_DECEMBER`; if sheet Y-1 also has that December, identical `(berth, day, key)` cells are deduplicated silently and differing ones are logged `DUPLICATE_BLOCK_DIFFERS` with the earlier sheet winning.
6. **Berth effective dates**: `effective_from` = Jan 1 of the first sheet year the berth row appears, `effective_to` = Dec 31 of the last, null if present in 2019. Lengths are parsed from the row label (`North Pier West 410'`). Berths that appear only in the 8YR summary (Marsh Landing) are created with `length_ft = null`, `source = summary-only`, effective over the summary years, logged `BERTH_ONLY_IN_SUMMARY`.
7. **Vessel naming**: `canonical_key = casefold(collapse_ws(strip_length_suffix(normalise_prefix(text))))`; `display_name` is the most frequent raw spelling. Unmatched grid vessels get `source = grid-only`, `loa_ft = null`. The report lists how many vessels have lengths and how many bookings are therefore UNKNOWN.
8. **Reconciliation** (`reconcile.py`): for 2006-2013 and each berth in the 8YR summary, `usage_days = count of (day, berth) pairs with at least one vessel/event/closure booking`; compare with the sheet's number; write a table of expected/actual/delta to the report. A delta is not a failure (the synthetic summary may count differently) but every delta is explained or listed as open. Why: the workbook contains its own checksum; using it is the cheapest possible proof the importer works.
9. **Tours sheet**: not imported (it is a visitor log, not occupancy); noted in the report.

## Unique features (ranked)

1. **Three-valued verdicts (OK / CONFLICT / UNKNOWN) with reason codes** - the system never reports "fits" for a vessel whose length it does not have. Why it impresses: most submissions silently treat missing data as zero. Cost 0.5 h. Depends on: domain model.
2. **Importer self-reconciliation against the "8YR Dock Summary"** - a table in `import_report.md` and in the UI's Import tab showing expected vs imported usage-days per berth per year. Cost 0.5 h. Depends on: importer.
3. **Fuzz equivalence test** (`test_fuzz.py`): seeded `random` generates 500 schedules; asserts the sweep-line audit equals a brute-force per-day check. Cost 0.4 h (stdlib only; `hypothesis` optional, not installed). Depends on: rules.py.
4. **Provenance everywhere**: every booking links to `sheet!cell` and to its import issues; clicking a booking shows "from 2010!F23, span inferred from fill #FFC000, header said NOVEMBER 2018 - corrected to 2010". Cost 0.3 h. Depends on: importer, UI.
5. **Pier load strip** (`pier.js`): one SVG per linear berth for the selected day: a bar of `length_ft`, vessels drawn end-to-end in proportion with clearance gaps, overflow drawn in red past the end, unknown-length vessels hatched. This is Baron's "boats and berths diagram" in its purist form - a picture of the exact computation, not decoration. Cost 0.5 h. Depends on: API `/api/day`.
6. **Effective-dated berths with an as-of date** in the UI; berths that did not exist in 1999 do not appear when the as-of date is 1999. Cost 0.3 h. Depends on: domain model.
7. **Tightest-fit berth suggestion** with slack shown in feet. Cost 0.4 h. Depends on: rules.py.
8. **Invariants enforced twice** (Python `InvariantError` and SQLite CHECK), with `test_db_constraints.py` proving the DB rejects what Python rejects. Cost 0.3 h. Depends on: schema.
9. **Architecture Decision Records** (`docs/decisions/0001..0007`): one page each, "context / decision / alternatives / consequences". Cost 0.4 h (Baron reads and edits them). Depends on: nothing; written as decisions are made.

## Phases (Baron-hours = time to understand, run, verify, rehearse; Claude types)

**Phase 0 - Tooling and skeleton (0.5 h).** Goal: a runnable repo. Steps: Baron installs Homebrew, python@3.12, gh per `docs/GITHUB_GUIDE.md`; Claude creates `.venv`, `requirements.txt`, package skeleton, `pytest` with one passing test, `git init`, first commit, `gh repo create`. Exit: `pytest` prints 1 passed; repo visible on GitHub. Baron can explain: what a venv is, why `.gitignore` excludes `*.sqlite`, why the domain package is separate.

**Phase 1 - Domain model and invariants (0.75 h).** Goal: `models.py`, `verdict.py`, `schema.sql`. Steps: Claude writes the dataclasses and CHECK constraints; Baron reads every field and its comment; `test_models.py` (12 tests: each invariant violated once, each satisfied once) and `test_db_constraints.py` (5 tests). Exit: 17 tests pass; Baron writes ADR 0001 (end-inclusive days) and 0002 (linear vs exclusive) in his own words. Baron can explain: why dates not datetimes, why end-inclusive, why `loa_ft` may be null, why events consume the whole berth.

**Phase 2 - Conflict engine (1.0 h).** Goal: `rules.py`, `suggest.py`. Steps: Claude writes `overlaps`, `fit_check`, `day_verdict`, `check_booking`, `find_conflicts`, `suggest_berths`; `test_rules.py` (about 30 named tests covering the edge-case list), `test_suggest.py` (5), `test_fuzz.py` (1 test, 500 cases). Baron traces three tests by hand on paper: a capacity overflow, a rafted vessel, an unknown length. Exit: all pass; Baron can state the exact rule from memory and explain `clearance * (n-1)` and why UNKNOWN is not OK (ADR 0003, 0004).

**Phase 3 - Importer and reconciliation (1.25 h).** Goal: `berthbook.sqlite` and `import_report.md` from the real workbook. Steps: registry first (Baron checks five vessels' lengths against the sheet by eye), then era 3 grids, then 2009-2013, then pre-2009; `test_classify.py` golden table (Baron supplies 10 of the values himself), `test_spans.py` (8 tests incl. cross-month join and leading December), `test_importer_smoke.py` (runs on the real file, asserts count ranges), `test_reconcile.py`. Exit: report shows bookings per era, issue counts per code, reconciliation table; Baron can name each issue code and what the importer did. ADR 0005 (year from sheet name), 0006 (unclassified = exclusive, needs_review).

**Phase 4 - Storage and API (0.5 h).** Goal: Flask routes over SQLite. Endpoints: `GET /api/berths?as_of=`, `GET /api/vessels?q=`, `GET /api/bookings?from=&to=&berth_id=`, `GET /api/day?date=` (per-berth active bookings + load, for the strip), `GET /api/check?vessel_id=&berth_id=&start=&end=&rafted=` (dry run, returns findings), `POST /api/bookings` (returns 201, or 409 with findings; body may include `override_reason` to store a CONFLICT knowingly - never silently), `DELETE /api/bookings/<id>`, `GET /api/bookings/<id>/provenance`, `GET /api/suggest?vessel_id=&start=&end=`, `GET /api/audit?year=`, `GET /api/import-report`. `test_api.py` (8 tests using Flask's test client on a temp DB). Exit: `curl` each endpoint; Baron can explain the 409-with-findings choice and why the API never contains a rule.

**Phase 5 - UI (0.75 h).** Goal: `web/index.html` with four panels: (1) day view: as-of date picker, berth list with active bookings and the pier load strip; (2) new booking form: vessel (searchable), berth, start, end, rafted, "Check" button showing findings in colour (green/red/amber), "Save" disabled while CONFLICT unless an override reason is typed; (3) suggest: vessel + range -> ranked berths with slack; (4) audit: year -> historical findings with provenance links; import report rendered from Markdown as `<pre>`. Exit: Baron performs the demo script below without help.

**Phase 6 - Static demo, README, ADRs (0.5 h).** Goal: `python -m berthbook.export` writes `docs/demo/export.json`; `docs/demo/index.html` reuses `web/` in read-only mode (form hidden, data from JSON); GitHub Pages enabled on `/docs`. README: what it does, how to run in four commands, the exact conflict rule, assumptions, the import report summary, link to ADRs and Pages. Exit: Pages URL renders the 2015 audit; README read aloud makes sense.

**Phase 7 - Rehearsal (0.75 h).** Baron runs the demo twice, answers the eight interview questions below out loud, and makes one deliberate change (set clearance to 20') to watch tests fail and the audit change - so he has personally seen the system respond to a rule change. Exit: Baron can do the demo in under 3 minutes and answer every question without notes.

Total: **6.0 Baron-hours.**

## Testing

- `pytest -q` runs everything in under 10 s; the importer smoke test is skipped if the workbook is absent.
- Unit (pure, no I/O): `test_models.py` (invariants), `test_rules.py` (rule table above: one test per row of the rule and per edge case, e.g. `test_touching_bookings_do_not_overlap`, `test_rafted_vessel_takes_no_length`, `test_unknown_length_is_unknown_not_ok`, `test_known_overflow_beats_unknown`, `test_closure_over_closure_ok`, `test_event_on_linear_berth_excludes_vessel`, `test_leap_day`, `test_cross_year_booking`), `test_suggest.py` (`test_tightest_fit_first`, `test_unknown_after_ok`), `test_fuzz.py` (sweep == brute force, seeded).
- Importer: `test_classify.py` golden table; `test_spans.py` on hand-built tiny `openpyxl` workbooks (merged cell, repeated name, fill continuity, cross-month join, leading December, header year mismatch); `test_reconcile.py` on a synthetic pair.
- Integration: `test_db_constraints.py` (each CHECK rejects), `test_api.py` (201 on OK, 409 with findings on CONFLICT, 201 with `override_reason`, provenance shape).
- Manual: demo script; `import_report.md` reviewed by Baron.

## Risks

1. **Pre-2009 span inference eats the importer budget.** Mitigation: era order banks clean years first; the report states coverage honestly; `SPAN_INFERRED_FROM_FILL` bookings carry `span_confidence = inferred` so the UI can show them hatched. Cut first: fill inference (fall back to repeated-name runs only).
2. **Baron cannot explain code Claude wrote.** Mitigation: every phase ends with Baron writing an ADR in his own words and tracing tests by hand; Phase 7 is protected time.
3. **Homebrew or Python install stalls.** Mitigation: python.org installer as fallback; `GITHUB_GUIDE.md` already covers it; Phase 0 is the first thing done, not the last.
4. **Reconciliation deltas are large** (synthetic summary uses a different counting rule). Mitigation: report both "any booking" and "vessel-only" counts; state the discrepancy rather than tune the importer to match.
5. **Clearance assumption disputed.** Mitigation: per-berth `clearance_ft` column and one ADR; the demo shows changing it.
6. **Time-of-day operations (ETA 1200, touch-and-go) look like they should affect capacity.** Mitigation: ADR 0007 explains the day-granularity choice and where sub-day booking would plug in (a `slot` column) if needed.

## Assumptions

1. The day is the unit of scheduling; a booking that departs at 0600 still occupies its berth that day.
2. Day ranges are end-inclusive, matching the grid.
3. A linear berth's capacity is `sum(LOA) + clearance * (vessels - 1) <= length`, clearance 10' by default, per berth.
4. North Pier West 410', North Pier Face 75', North Pier East 240', South Float West 90', South Float East 90' are linear; Inner Channel 55' and every finger-pier / small-craft slip are exclusive (one occupant).
5. Events and closures occupy the whole berth; closures conflict with everything except other closures.
6. A rafted vessel consumes no linear length but must still fit the berth's length and counts as an occupant of an exclusive slip.
7. Unknown vessel length or berth length yields UNKNOWN, never OK.
8. The sheet name is the authoritative year; a leading December block belongs to the previous year.
9. Vessel identity is the normalised name; two spellings with the same key are the same vessel.
10. Registry lengths are LOA in feet; draft is stored but not used (no depth data for berths).
11. Operational notes are not occupancies.
12. Unclassified cells are treated as exclusive events flagged for review.
13. The Tours sheet is a visitor log, not a berth occupancy source.
14. Single user, local run, no authentication; the public Pages demo is read-only.

## Out of scope (cut first, in order)

Animation of boats; drag-and-drop on a grid; fill-colour span inference (keep repeated-name runs); the Tours sheet; draft/depth and tide checks; sub-day time slots; recurring events; editing berth definitions in the UI (edit `berths` via SQL or a JSON seed); multi-user auth and a hosted backend; undo; email or calendar export; `hypothesis`-based property tests (seeded `random` is enough); a JS port of the engine for a live static demo (would duplicate the rule).

## Demo script (first two minutes for a reviewer)

0:00 Open the Pages URL. Top: "Historical audit 1997-2019: N CONFLICT, M UNKNOWN findings across 2,6xx imported bookings; coverage per era." Click 2015; see a CAPACITY_EXCEEDED finding on North Pier East: "2015-06-03..06-05 load 265' > 240'" with three vessel names and their lengths.
0:30 Click the finding; the pier load strip draws 240' with three boats end-to-end and the third spilling past the end in red; provenance panel lists `2015!K41`, `2015!L41`, `2015!M41` (merged range), "span exact".
0:50 Locally (`python -m berthbook.api.app`, same page with the form): pick "R/V High Drift" (120'), berth Inner Channel 55', tomorrow; press Check: red "DOES_NOT_FIT: LOA 120' > berth 55'". Change berth to North Pier West; amber "LENGTH_UNKNOWN: Barge Salt Dory on this berth has no length in the registry"; the strip shows a hatched box. Press Suggest: ranked list with slack in feet.
1:30 Open Audit > Import report: issue counts per code (HEADER_YEAR_MISMATCH 2, JOINED_ACROSS_MONTH n, UNCLASSIFIED n) and the reconciliation table against the 8YR summary.
1:50 Open `tests/` in the repo: `pytest -q` output pinned in the README, `test_fuzz.py` visible.

## Interview points (the eight questions and one-paragraph answers)

1. **Why end-inclusive day ranges and no times?** The source of truth is a grid with one cell per day; times appear only as notes ("ETA 1200"). Modelling the day as the atom matches the facility's practice and makes overlap a two-comparison rule (`a.start <= b.end and b.start <= a.end`). If sub-day scheduling is ever needed, a `slot` column is the extension point; I documented that in ADR 0007 rather than building it.
2. **What exactly is a double-booking here?** It depends on berth mode. An exclusive slip is double-booked when two bookings share a day. A linear pier is double-booked when the sum of vessel lengths plus one clearance gap per neighbour exceeds the pier length on any day. Events and closures take the whole berth. The rule is one function, `day_verdict`, with a test per branch.
3. **Why three verdicts instead of true/false?** Roughly half the vessels in the grid have no length in the registry. Treating missing length as zero would report OK for a berth that might be overloaded - the exact failure the facility asked us to catch. UNKNOWN is shown in amber with the vessel named so a person can fill in the length; the check is rerun and becomes OK or CONFLICT.
4. **How did you handle the messy 23-year workbook?** The importer searches for month headers and day rows rather than assuming coordinates, so the three layout eras share one code path. Spans come from merged cells when available, else repeated names, else (pre-2009) fill continuity, each tagged with a confidence. Every decision that resolved an ambiguity - the 2010 sheet labelled 2018, leading Decembers, cross-month joins, unclassified cells - is a row in `import_issues` that the UI shows as provenance.
5. **How do you know the importer is right?** Three ways: a golden test of about 60 real cell values for the classifier; span tests on tiny hand-built workbooks; and reconciliation against the workbook's own "8YR Dock Summary", which is effectively a checksum the client provided without meaning to. The deltas are printed, not hidden.
6. **How do you know the conflict engine is right?** Thirty named unit tests, one per rule branch and edge case, plus a fuzz test that generates 500 random schedules and asserts the O(n log n) sweep-line audit gives the same findings as a brute-force per-day check. The two implementations would have to share a bug to pass.
7. **Why is the structure the way it is?** The domain package imports nothing from the rest of the project; importer, storage and API depend on it, never the reverse. So the rule can be tested with no database or server, the importer can be replaced when the facility moves off spreadsheets, and the same invariants are enforced by Python and by SQLite CHECK constraints. Flask and vanilla JS were chosen because they add nothing to explain.
8. **What would you do next?** Let the facility edit berths and clearances in the UI, add draft-vs-depth checks once berth depths exist, and let a scheduler resolve UNKNOWN findings by entering a length in place. I would not add animation before those; the pier strip already shows the computation, which is the picture that matters.
