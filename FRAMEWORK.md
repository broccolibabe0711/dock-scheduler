# Dock Scheduling System — Project Framework

**Deployment update, 19 September 2026:** The requested operable website is at
<https://dock-scheduler-henna.vercel.app>. Vercel runs FastAPI with persistent Neon
PostgreSQL; local development keeps SQLite. The deployment work and verification
are documented in `docs/DEPLOY_VERCEL.md` and decisions 0008–0009. The test suite
includes API and storage workflows on both databases. The older Pages sections below describe
the historical read-only demo, which remains available separately.

**For:** Baron Zhang's take-home for Columbia Software Solutions
**Written:** 18 September 2026 (before any application code exists)
**Budget:** about 6 hours of Baron's own time, working with Claude Code as a pair
**Status of this document:** the plan, written before any code. The build followed it; the section right below records where reality differed. Every later decision is in `docs/decisions/`.

**Current product documentation:** `docs/ENGINEERING_WALKTHROUGH.md` explains the implemented website and `docs/ACCEPTANCE_TESTS.md` provides reproducible acceptance tasks. The original proposals below are retained as design history.

---

## Implementation status (19 September 2026)

| Phase | Planned | What happened |
|---|---|---|
| 0 Setup and GitHub | 0.5 h | Done. Repo public at github.com/broccolibabe0711/dock-scheduler; CI runs the tests on every push; Pages deploys `site/` from a workflow. |
| 1 Assumptions | 0.5 h | Done as `docs/ASSUMPTIONS.md` (20 numbered items) with the defaults from Section 8.2. |
| 2 Rules engine | 1.0 h | Done. `dock/rules.py` + `dock/models.py`; 60 sentence-named tests; three review passes found real gaps (string enums, NaN lengths, orphaned stays, known sums downgraded to UNKNOWN) that became decision 0007 and tests. |
| 3 Importer and audit | 1.0 h | Done. Reproduces the independent data study's extraction; 479 issues logged on the sample; `docs/AUDIT_REPORT.md` generated. A review found the damaged 2010 blocks' true day-1 row sits above the header; fixed and tested. |
| 4 Storage and API | 0.5 h | Done. SQLite/PostgreSQL with constraints and atomic booking checks; occupancy edits need fresh overrides; measurement edits preview and record affected bookings. |
| 5 UI and harbor view | 1.0 h | Done. Harbor is the landing view; six tabs including Vessel registries. Reservation editing, measurement review, imported notes and assumptions are accessible from the website. |
| 6 Static demo, README | 0.75 h | Done. `python -m dock.export` writes the snapshot; the same front end runs on it; conflict flags come from the same function the API serves. |
| 7 Review and rehearsal | 0.75 h | Regression suites cover both databases; browser acceptance checks cover edits and measurement reviews. Current results are recorded with the release. Rehearsal remains Baron's. |
| 8 Operable deployment (added) | — | FastAPI on Vercel with Neon PostgreSQL; missing persistent configuration prevents startup. |

**Where the plan changed, and why.**

- The audit found **0 detected berth-days over capacity** with the available measurements. Missing lengths limit that conclusion. Nine reservation records fail the individual fit check, twelve shared berth-days are unverifiable and one stay overlaps a closure. Duplicate berth rows support the shared-face model.
- Only **33 of 1,927** vessel stays have a known length, so "UNKNOWN is not OK" (decision 0003) is the common case in history, not an edge case, and the audit reports "unverifiable" days rather than pretending.
- The harbor view and the audit page label a **closure-shared day** differently by design: the audit counts feet arithmetic and lists closures separately; the grid and harbor paint any day the referee would refuse. The audit page says so.
- Six review passes were run instead of one per phase, because the first pass on the rules engine paid for itself immediately (Section 7 gate, decision 0007).
- Hosting expanded to a persistent Vercel deployment at the user's request. Measurement correction now includes a preview, a reason for blocking outcomes, protection against stale acknowledgement, and a durable review record (decision 0009). The pending PostgreSQL hardening was integrated; concurrent startup testing now includes actual seeding.

---

## 0. The plan in ten lines

1. Build a small, real reservation system for a research-facility waterfront: berths of different lengths, vessels and events that occupy them for day ranges.
2. The two questions it must answer instantly, which the client answers today by staring at a grid: *is this berth double-booked?* and *does this vessel fit here?*
3. Stack: Python 3.12, a pure-Python rules engine, SQLite, FastAPI, and a vanilla HTML/JS front end with an inline SVG harbor view. No build step, four pip packages.
4. The legacy workbook (23 years, 2,244 bookings) is imported by an importer that records every ambiguity instead of hiding it, and produces a data-quality report on the client's own history.
5. Berths are modelled with **linear capacity** (several vessels can share a 410-foot pier face if their lengths fit) or **exclusive** occupancy (a small slip holds one boat). That is what the data shows the facility actually does.
6. A vessel with an unknown length gets the verdict **UNKNOWN**, never OK. Only 19 of the 504 vessel names in the grid have a known length.
7. The stand-out piece is a to-scale, animated harbor view with a timeline scrubber: boats slide into berths, overhangs and over-capacity days glow.
8. Seven phases, each with an exit criterion and a "what Baron must be able to explain" line; the first working system exists at the 3-hour mark.
9. Every phase ends with tests, an automated review pass (the three installed review plugins), a commit, and a one-paragraph decision record.
10. Deliverable: a public GitHub repo with a README, this framework, the audit report, and a read-only GitHub Pages demo.

---

## 1. The brief, and what the club is really testing

The club's text, verbatim:

> A WHOI marine research facility needs to manage berths of varying lengths. Vessels reserve a berth for specific ranges of days. The waterfront also hosts non-vessel events such as community sail days that also occupy a berth. A sample schedule is attached to this email, containing 23 years of bookings. Some issues include the need to manually check for double-bookings by looking at a grid and verifying that a vessel actually fits the berth it has been assigned to. Build a system to manage these reservations.

> They are deliberately left open ended. Some things we're looking for on our end include whether it works, how you structured it, any assumptions you made, and how clearly you can explain your decisions. Polish and visual design are welcome but not the point.

Read that second paragraph as the rubric. Four things are graded, in this order:

| Criterion | What it means for this project | Where it shows up |
|---|---|---|
| **Works** | Clone, run, book, get refused for the right reasons, see history. | Tests, a 3-command quickstart, a live demo link. |
| **Structure** | Someone could hand this to a client team. Clear layers, one place where the rules live. | Section 4 (architecture), the file map. |
| **Assumptions** | Written down, numbered, and visible in the product, not just in a doc. | Section 8 and the importer's issue log. |
| **Explains decisions** | Baron can defend each choice in a 15-minute conversation. | Every "Why" in this document, `docs/decisions/`, Section 11. |

"Polish is not the point" is not a ban on the harbor animation. It is a warning about order: the animation comes *after* the rules are tested, and it must render the rules engine's output, never its own guesses.

### 1.1 The client, and the real thing behind the sample

Columbia Software Solutions is a student-run nonprofit at Columbia University that builds free custom software (websites, apps, databases, automation, AI tools) for NYC nonprofits and small businesses ([columbiasoftwaresolutions.com](https://www.columbiasoftwaresolutions.com/)). The take-home imitates their real work: a small organisation with a spreadsheet that has outgrown itself.

The sample is a renamed copy of a real document. WHOI (Woods Hole Oceanographic Institution) publishes its dock schedule as an Excel-made PDF ([April 2020 edition](https://www.whoi.edu/wp-content/uploads/2020/04/4_24_20_DOCK-Schedule.pdf)). Its rows are "Iselin Pier West - 430'", "Iselin Pier Face", "Iselin Pier East - 256'", "Eel Pond Channel - 60'", "Dyer's Dock West" and "Dyer's Dock East"; its cells hold R/V Atlantis, R/V Neil Armstrong, S/V Corwith Cramer, a NOAA ship, and non-vessel entries such as "CMR Entrepreneurs Event Iselin" and "Stroll". The sample's "North Pier West - 410'", "North Pier Face - 75'", "North Pier East - 240'", "Inner Channel - 55'", "South Float West/East - 90'" map onto those one to one. WHOI's own page says the pier has "two principal berths, one 430 feet long and the second 256 feet long" and a 19-foot draft limit ([Iselin Marine Facility](https://www.whoi.edu/what-we-do/explore/ships/marine-facilities-operations/iselin-marine-facility/)).

Why this matters: it proves the problem statement is real (events really do sit on the same grid as ships), it gives the harbor drawing a plausible geography, and it is the kind of thing a reviewer remembers.

---

## 2. What the data study found

Before designing anything, the workbook was taken apart with scripts (kept in `docs/data-study/`, with the reports and CSVs they produced). The numbers below come from those reports, not from eyeballing.

### 2.1 Shape of the workbook

| Fact | Value |
|---|---|
| Sheets | 27: one grid per year 1997–2019, "8YR Dock Summary", "Science" and "Yachts" registries, "Tours" |
| Month blocks in the grids | 272 |
| Booking records extracted | 2,244 |
| Filled cells in berth rows | 2,663 (the difference is repeated names and cells outside day columns) |
| Distinct raw cell values | 573 |
| Vessel names, raw → after case normalisation | 532 → 504 |
| Cells that are vessels / notes / events / closures | 2,440 / 103 / 67 / 53 |
| Vessels in the registries (all with a length) | 168, in two messy contact-list sheets |
| Grid vessel names that match a registry length | **19 of 504** |
| Tours logged | 32, from 29 Apr to 24 Jul 2018, all on three vessels |

### 2.2 How a booking is encoded (three eras, one grid idea)

Every year sheet is a stack of month blocks: one row per berth, one column per day, the vessel or event name written in the first day's cell. How the *length* of the stay is shown changed over time:

| Era | Years | Header convention | How a multi-day stay is shown |
|---|---|---|---|
| A | 1997–2003 | "AUGUST 1997" in column A, weekday letters, then day numbers as formulas with no cached values | A solid fill or thin border run to the right of the name, or the name repeated on separate days |
| B | 2004–2013 | Title rows, then "JANUARY 2009" with day numbers on the same row | Merged cells from 2009 on; fills before that |
| C | 2014–2019 | Plain "January", day numbers starting in column C | Merged cells |

Span sources across all 2,244 records: 607 merged ranges, 733 fill runs, 57 repeated names, 847 single days. So for a third of history the length of a stay is an *inference* from cell colouring, not a recorded fact. The importer must say so per record.

### 2.3 Things in the cells that are not bookings

The same cells hold four different kinds of thing:

- **Vessels** (2,440 cells): "R/V GOLDEN COMPASS", "Barge Salt Dory", "Tug BLUE FATHOM", "OSV AMBER REEF". Capitalisation is inconsistent (28 names appear in two casings), and "OS/V" appears next to "OSV".
- **Events** (67): "Community sail day", "Campus event", "Student tour", "Holiday", "Road race - access limited", "Donor reception", "Safety training (RIBs)".
- **Closures** (53): "Float rebuild - no usage permitted", "Bollard replacement, west face", "Dock maintenance - restricted access", "Ultrasonic pier test".
- **Notes** (103): "ETA 1200", "Departs 0600", "Fueling @0800", "Delayed due to weather", "Touch and go", "Fuel truck". These annotate a stay; they do not occupy a berth.

A system that treats every cell as a reservation would invent 103 phantom bookings. A system that ignores non-vessels would lose 120 real occupancies.

### 2.4 Defects in the workbook (the importer's job is to surface these, not fix them silently)

| Defect | Count | Example |
|---|---|---|
| Blocks whose label year differs from the sheet | 5 | The 2010 sheet ends with "NOVEMBER 2018" and "DECEMBER 2018"; 2002–2004 start with the previous December |
| Month headers with the wrong number of days | 5 | "JUNE 2008" lists 31 days; "MARCH 2011" lists 29 |
| Day-1 column drifting between blocks | many | Column B in most years, E/F/G/H in 2010–2015 |
| Merged ranges running past the month's last day | 3 | "R/V GOLDEN COMPASS" merged B8:AJ8 in January 2014 |
| A merge spanning two berth rows | 1 | 2014, G124:T125 |
| Cells outside the day columns | 78 | Vessel names in column B, before day 1 |
| Berth label duplicated inside one block | 27 | "South Float East - 90'" on two rows in July 2017, each with a different vessel |
| Text in rows with no berth label | 334 | Eight of them are colour-legend rows; others sit where the finger-pier rows later appear |
| Values written into the header row | 12 | The mislabelled 2010 blocks |
| Same-berth overlapping stays in the legacy data | 5 pairs | All caused by duplicated berth rows |

Two findings change the design:

1. **The duplicated berth rows are how the spreadsheet expresses two vessels on one berth at the same time.** A 410-foot pier face genuinely holds several vessels end to end. The grid has no way to say that, so operators inserted a second row with the same label. The model must allow shared berths with a capacity rule, or it will refuse bookings the facility routinely makes.
2. **The "8YR Dock Summary" cannot be reproduced from the grids.** It reports 298–511 usage-days per year for "North Finger Piers" in 2006–2013, but those rows only appear in the grids from 2014, and "Marsh Landing" never appears at all. The summary was kept by hand from something else, and several of its values exceed the number of days in a year (North Pier West 2012 = 648), so it cannot be single-berth usage-days under any reading of the grid. The importer will compute its own usage-days, show them next to the summary, and state the gap rather than tune the numbers to match.

### 2.5 The registries

"Science" and "Yachts" are contact lists that drifted: 137 of 441 rows are continuation fragments (a lone phone number, an email, a captain's name), values sit under the wrong column, and two vessels appear twice with different lengths ("R/V High Reef" 32' and 72'). Lengths come only from these sheets ("R/V High Drift 120'", "LOA: 65', Draft: 4'"). Notes such as "Will raft alongside if needed", "Short visit only", "Requires shore power", "Pending insurance paperwork" are really workflow flags.

### 2.6 Tours

Point-in-time visits (date, time, guide, guest organisation, headcount, vessel), with times like "tbd" and "1175" and counts like "~17". They reference a vessel, not a berth, so they are a separate entity linked through the vessel, and they are out of scope for the 6-hour build beyond an import into a table.

---

## 3. Product decisions

**Users.** One dock coordinator (the person who today edits the grid), occasionally a colleague reading it. No public users, no accounts in v1.

**The system is a ledger with a referee.** Reservations are the ledger; the rules engine judges new bookings and changes to occupancy. Measurement corrections review affected bookings. Notes-only edits and cancellations have explicit exceptions. Import, UI, reports and Harbor read from the ledger or the rule results.

**The two questions, made precise.**

- *Double-booked?* For every day of a proposed reservation, the occupied length on that berth (existing reservations plus this one) must not exceed the berth's length. For an exclusive berth, "occupied length" is simply "anything else present".
- *Fits?* The vessel's length must be no greater than the berth's length; if the vessel's length is unknown, the answer is UNKNOWN, and UNKNOWN blocks the booking until someone types a length or records an override with a reason.

**What is deliberately not a reservation.** Notes ("ETA 1200") are annotations attached to a reservation or a berth-day. Tours are visits linked to a vessel. Neither consumes berth length.

**Overrides exist.** Real operators raft vessels alongside each other and squeeze things in. A reservation may be saved despite a CONFLICT verdict only with an `override_reason`, which is stored and shown. The system never silently allows; it never absolutely forbids.

---

## 4. Design decisions

Each decision has the choice, the reason, and what was rejected. These are also written, one per file, as short decision records in `docs/decisions/` as the code lands.

### 4.1 Stack

| Layer | Choice | Why | Rejected |
|---|---|---|---|
| Language | Python 3.12 (Homebrew) | Readable for a beginner; the club builds Python back ends; `sqlite3`, `dataclasses`, `datetime` are in the standard library; the security plugin needs 3.10+. | Node/TypeScript: one more toolchain to install on a machine that had none; a bundler is the riskiest install. |
| Rules engine | Pure Python module `rules.py`, no imports beyond `datetime` and the models | Testable in isolation, explainable line by line, and the single source of truth the UI and importer both call. | Rules inside SQL or inside route handlers: untestable without a database or server. |
| Storage | SQLite via the standard library, schema in `schema.sql` with CHECK constraints | Zero install, one file, real date-range queries; CHECK constraints enforce invariants a second time. | JSON files (no range queries); Postgres (a server to run). |
| Workbook reading | `openpyxl` | The only mature pure-Python reader that exposes merged ranges and cell fills, both needed for the pre-2009 span inference. | pandas: hides merges and fills, heavier install. |
| API | FastAPI + uvicorn, synchronous route functions | Typed request models double as validation and documentation; the auto-generated `/docs` page lets a reviewer try `POST /api/check` without the UI. | Flask: one fewer package and simpler, but no interactive docs; kept as the fallback if pydantic proves confusing. |
| Front end | One `index.html`, `app.js`, `style.css`, inline SVG; no framework, no build | The brief prefers substance; every line is readable; GitHub Pages serves it as-is. | React/Vite: build step, install risk, nothing the UI needs. |
| Tests | `pytest` | Plain `assert`; failures read like sentences. | `unittest`: more ceremony. |
| Hosting | Local run for the full app; GitHub Pages for a read-only demo built from exported JSON | Pages cannot run Python; the demo shows the engine's precomputed output rather than duplicating rules in JavaScript. | Deploying the API publicly: needs auth and hosting, out of scope. |

Installs, in order: Homebrew; `brew install python@3.12 gh`; a virtual environment; `pip install openpyxl fastapi uvicorn pytest` pinned in `requirements.txt`. Nothing else.

### 4.2 Architecture

```
dock-scheduler/
  README.md                  what, why, quickstart, links (the reviewer's front page)
  FRAMEWORK.md               this document
  requirements.txt
  data/
    Dock Schedule - Synthetic Sample.xlsx      the input, committed (synthetic, no secrets)
  dock/                      the Python package
    models.py                Berth, Vessel, Reservation, Annotation, Finding (frozen dataclasses)
    rules.py                 overlaps(), fit_check(), day_load(), check(), suggest_berths()   <- the referee
    classify.py              classify_cell(text) -> kind + canonical name; the taxonomy table
    registry.py              Science/Yachts sheets -> vessels with lengths and flags
    importer.py              23 grids -> reservations + annotations + issues; era detection; span inference
    reconcile.py             usage-days per berth-year vs the 8YR summary
    audit.py                 runs rules over all history -> docs/AUDIT_REPORT.md + site/data/audit.json
    db.py                    connect(), schema load, insert/select helpers
    api.py                   FastAPI routes: parse -> call rules -> return JSON; serves site/ statically
    export.py                writes site/data/*.json for GitHub Pages
    schema.sql
  site/
    index.html  app.js  style.css  harbor.js      grid view, booking form, findings, harbor view
    data/                    generated JSON, committed so Pages works
  tests/
    test_rules.py  test_classify.py  test_importer.py  test_api.py
    fixtures/make_fixture.py           builds a tiny workbook with one block per era
  docs/
    decisions/               0001-end-inclusive-days.md ... one paragraph each
    AUDIT_REPORT.md          generated; the headline numbers about the client's history
    ASSUMPTIONS.md           Section 8 of this file, kept current
    GITHUB_GUIDE.md          beginner setup guide
    data-study/              the scripts, reports and CSVs behind Section 2
```

Data flow: `importer.py` reads the workbook once and fills `dock.db`. `api.py` opens the database per request. Every mutation calls `rules.check()` first and refuses to save when any finding is an error, unless the request carries `override_reason`. The front end never computes rules; it renders `Finding` objects from the API, so the booking form, the audit page and the harbor view show identical messages for identical situations.

### 4.3 Data model

| Entity | Fields | Invariants |
|---|---|---|
| **Berth** | id, name, length_ft (nullable), capacity_mode `linear` or `exclusive`, clearance_ft (default 10), active_from, active_to (nullable) | A berth is only bookable on days inside its active range. Berths are effective-dated because the set changed over 23 years (finger piers appear in 2014; "Marsh Landing" exists only in the summary). |
| **Vessel** | id, name, name_key (case-folded, punctuation-free), type_prefix, length_ft (nullable), draft_ft (nullable), operator, flags (rafts_ok, short_visit, shore_power, insurance_pending), notes | name_key is unique; length may be unknown and that is a first-class state. |
| **Reservation** | id, berth_id, kind `vessel`/`event`/`closure`, vessel_id (required iff kind = vessel), title, start_date, end_date, status `planned`/`confirmed`/`cancelled`, override_reason (nullable), source `manual`/`import`, legacy_ref (sheet, row, column, span_source), notes | start ≤ end; days are **end-inclusive** (a stay from the 3rd to the 5th occupies three days, which is how the grid reads). Events and closures occupy the berth's full length. |
| **Annotation** | id, berth_id, date, reservation_id (nullable), text | "ETA 1200" lives here, never as a reservation. |
| **ImportIssue** | id, kind, severity, sheet, cell, message, reservation_id (nullable) | One row per anomaly the importer met; browsable in the UI. |
| **Tour** | id, date, time (nullable), guide, guest, organisation, headcount, approximate, vessel_id | Imported for completeness; no rules apply. |

### 4.4 The rules (the part to be able to write on a whiteboard)

```
overlaps(a, b):        a.start <= b.end and b.start <= a.end          # end-inclusive
occupied_ft(r, berth): berth.length_ft if r.kind in (event, closure)
                       else r.vessel.length_ft + berth.clearance_ft   # None if length unknown
day_load(berth, day):  sum of occupied_ft over active reservations covering day

check(candidate) -> list[Finding]:
  INACTIVE_BERTH  error    berth not active on some day of the range
  CLOSURE         error    a closure reservation overlaps the range
  FIT             error    vessel.length_ft > berth.length_ft
  UNKNOWN_LENGTH  blocking vessel.length_ft is None (verdict UNKNOWN, not OK)
  CAPACITY        error    exclusive: any other reservation shares a day
                           linear: day_load + occupied_ft(candidate) > berth.length_ft on some day
                           (finding lists the day and the co-occupants with their lengths)
  RAFTING_NOTE    info     co-occupant flagged rafts_ok, so an override is plausible

suggest_berths(vessel, start, end): run check() for every active berth, keep those with no errors,
  sort by smallest berth length first (leave the big pier for big ships), then fewest warnings.
```

Complexity is proportional to (overlapping reservations × days in the range); a busy year has a few hundred reservations, so this is instant. The engine is pure, so the tests are tables of named cases: "adjacent days do not overlap", "exact length fits", "one foot over fails", "two 150-foot vessels share a 410-foot face", "a third 150-foot vessel is refused with the other two named", "unknown length is UNKNOWN even on an empty berth", "closure beats everything", "berth inactive in 2005 refuses a 2005 booking".

### 4.5 The importer

The importer is the second product, and the one with the most decisions:

1. **Era detection per block, not per sheet.** Find the month header (a month name, with or without a year), then find the day-1 column by locating the cell whose value or formula chain starts at 1. Never assume a column.
2. **Span inference, in this priority:** merged range → run of identical fill to the right → identical name in adjacent cells → single day. Each record stores which rule produced its end date.
3. **Stitching across month blocks.** A stay that ends on the last day of a block and reappears on day 1 of the next block for the same berth and name is one reservation.
4. **Classification** through `classify.py`, using the taxonomy built in the data study (573 values, four kinds). Notes become annotations. Case is normalised; "OS/V" becomes "OSV".
5. **Lengths** join from the registry by name_key; conflicts (two lengths for one name) are recorded as issues and the vessel keeps no length rather than a guessed one.
6. **Duplicated berth rows** import as separate reservations on the same berth. The capacity rule then evaluates them; if they exceed the berth, that is a genuine finding about history.
7. **Mislabelled 2010 blocks** import as November and December 2010 (they follow October 2010 on the 2010 sheet) with an issue recording the original label. This is the one place the importer corrects rather than preserves, and it says so.
8. **Wrong day counts in headers**: the calendar wins; an issue is recorded.
9. **Cells outside the day columns, legend rows, text in unlabelled rows**: recorded as issues with the raw text, never as reservations. Unlabelled rows that sit where finger-pier rows later appear are noted as "probably North Finger Piers" but not assigned.
10. **Reconciliation** against the 8YR summary is computed and printed side by side, with the explanation from Section 2.4.

The importer's verified output is 1,982 reservations, 46 annotations and 479 issues. It reads 2,164 of 2,244 encountered runs, excludes fourteen repeated-month runs, separates annotations and stitches 122 month-boundary fragments. Of 1,927 vessel stays, 1,894 (98.3%) lack a known length. The generated `docs/AUDIT_REPORT.md` records findings with their denominators.

### 4.6 The user interface

Three views, one page:

- **Grid**: the familiar month grid (berth rows × day columns), because the coordinator should recognise it, with reservations as coloured bars and conflicts outlined. Clicking a bar opens it; clicking an empty cell starts a booking there.
- **Book**: vessel (with type-ahead from the registry, and a length field that is required when unknown), berth, dates, kind. Submitting calls `/api/check` first and shows findings in words; "Suggest a berth" lists alternatives; saving with errors requires an override reason.
- **Harbor**: the to-scale SVG plan of the waterfront (Section 5.1), with a date scrubber and play button.

Plus an **Audit** tab that renders the audit report and lets the issue list be filtered by kind and year.

---

## 5. What makes this stand out (ranked, with cost)

1. **The audit of the client's own history** (part of Phase 3, ~0.5 h extra). The README opens with facts about the workbook: how many stays, how many inferred, how many days a berth was over capacity, how many mislabelled months. It turns "I built a CRUD app" into "I found what was wrong with your process and here is the tool that prevents it".
2. **The to-scale harbor view** (Phase 5, ~1 h). An SVG plan of the piers at one shared feet-to-pixels scale, vessels drawn as hulls of their real length, a timeline scrubber that animates arrivals and departures day by day, overhangs drawn as the hull sticking out past the berth with a "+45 ft" badge, over-capacity days pulsing. It is Baron's own idea from the brief, made rigorous: the picture is drawn from the same numbers the rules use, so if it looks wrong the rule is wrong.
3. **Linear capacity instead of one-vessel-per-berth** (free; it is the model). Most submissions will model a berth as a slot. The data shows the facility shares long faces, and the duplicated rows prove it. Modelling this correctly is a domain insight a reviewer will notice.
4. **UNKNOWN is a verdict** (free). Refusing to say OK when the length is missing is honest engineering, and it maps to a real workflow: "call the captain, get the LOA".
5. **Findings that explain themselves** (free). "South Float East over capacity on 2017-07-12: OSV Amber Reef (100') + candidate (60') = 160' > 90'". The same text appears in the API, the form and the audit.
6. **Decision records** (~10 minutes per phase). One paragraph per decision in `docs/decisions/`, which is also the interview prep.
7. **Stretch, only if time remains:** run the very same `rules.py` in the browser through Pyodide so the Pages demo can refuse a booking live without duplicating rules in JavaScript; or an intake helper that turns a pasted dock-request email into a draft reservation (the club has AI credits; it would be clearly labelled as optional).

Things cut first if time runs short, in order: the stretch items; the Tours import; the Audit tab's filters (the report file stays); play-button animation (the scrubber stays); suggest-a-berth.

---

## 6. Phases, time, steps, exit criteria

Hours are **Baron's hours**: the time to read, run, verify and be able to explain. Claude does most of the typing, but code Baron cannot explain does not count as done. Total: 6.0 h.

### Phase 0 — Set up the machine and GitHub (0.5 h, mostly waiting)

Steps: follow `docs/GITHUB_GUIDE.md` Parts 1–2 (Homebrew, Python 3.12, gh, GitHub account, `gh auth login`, git identity). Then Claude runs `git init`, the first commit, and `gh repo create dock-scheduler --public --source=. --push`.
Exit: `git --version`, `python3.12 --version`, `gh auth status` all succeed; the repo is visible at github.com.
Explain afterwards: what a repo, commit, push and README are (glossary in the guide).
Why first: nothing else can be verified without Python, and the club will look at commit history, so history should start at the start.

### Phase 1 — Understand the problem and fix the assumptions (0.5 h)

Steps: read Sections 1–4 of this document; open the workbook and find one example of each thing in Section 2.3; read `docs/data-study/extract_report.md` sections 2–4; decide the answers to the open questions in Section 8.2 and write them into `docs/ASSUMPTIONS.md`.
Exit: `docs/ASSUMPTIONS.md` exists with numbered assumptions Baron agrees with.
Explain afterwards: why notes are not bookings; why a 410-foot berth needs a capacity rule; why the 8YR summary cannot be trusted.

### Phase 2 — Domain model and rules engine, tested (1.0 h)

Steps: Claude writes `models.py`, `rules.py`, `tests/test_rules.py` with the named cases from 4.4. Baron runs `pytest`, reads every test name, changes one expected value to see a test fail and understand the message, then restores it. Together, write `docs/decisions/0001-end-inclusive-days.md`, `0002-linear-capacity.md`, `0003-unknown-is-not-ok.md`.
Exit: all rule tests green; Baron can draw the overlap rule and the capacity rule on paper.
Explain afterwards: the three decision records, and why the engine imports nothing.
Why before storage or UI: the rules are the product; everything else is plumbing around them.

### Phase 3 — Importer and audit (1.0 h)

Steps: Claude writes `classify.py`, `registry.py`, `importer.py`, `reconcile.py`, `audit.py`, a fixture workbook builder and tests. Run the import on the real sample; read `docs/AUDIT_REPORT.md` top to bottom; spot-check five issues against the workbook by hand (open Excel, find the cell). Commit the report.
Exit: import completes with the record count within the documented range; the audit report exists; five spot checks pass.
Explain afterwards: the span-inference priority, what happens to the mislabelled 2010 months, why the summary is not reproduced.
Why timeboxed: the workbook is a rabbit hole. Anything not handled by the end of the hour becomes an issue row, not a code path.

### Phase 4 — Storage and API (0.5 h)

Steps: `schema.sql`, `db.py`, `api.py` with `GET /api/berths`, `GET/POST /api/vessels`, `GET /api/reservations?from&to`, `POST /api/check`, `POST /api/reservations`, `GET /api/suggest`, `GET /api/issues`; `tests/test_api.py`. Run `uvicorn`, open `/docs`, try `POST /api/check` with a vessel that does not fit and read the response.
Exit: API tests green; a bad booking is refused at `/docs` with a readable finding.
Explain afterwards: why the route only parses, calls the referee and returns; what the CHECK constraints protect against.

### Phase 5 — User interface and harbor view (1.0 h)

Steps: Claude writes `site/` (grid, book form with findings, harbor view with scrubber). Baron uses it: books a real-looking stay, gets refused, uses suggest-a-berth, saves with an override, scrubs the harbor through a busy month, finds one overhang.
Exit: the three views work in a browser against the local API; the harbor view shows a conflict the audit also lists.
Explain afterwards: why the front end never computes rules; how feet map to pixels; what an overhang badge means.

### Phase 6 — Static demo, README, decision records (0.75 h)

Steps: `export.py` writes `site/data/*.json`; enable GitHub Pages on the `site/` folder; write the README (headline audit numbers, 3-command quickstart, screenshots, links to this framework and the audit report, assumptions, known limits); finish decision records.
Exit: the Pages link works in a private browser window and shows history, audit and harbor view; `README.md` answers "what, why, how to run, what I assumed" in under two screens.
Explain afterwards: what the Pages demo can and cannot do, and why.

### Phase 7 — Review, rehearse, submit (0.75 h)

Steps: run the full review gate (Section 7) one more time on the whole repo; fix or consciously document what it finds; read `git log --oneline` and make sure it tells the story; rehearse the eight interview answers in Section 11 out loud; send the link.
Exit: the checklist in Section 12 is all ticked.

---

## 7. Testing and quality gates

**Automated tests** at three levels: rules (pure, table-driven), importer (tiny fixture workbook with one block per era, plus a golden count on the real sample), API (FastAPI test client; the refusal path and the override path).

**The review gate, run at the end of every phase and before every reply that touched code**, using the three plugins installed for this project:

- `pr-review-toolkit`: `code-reviewer` (conventions and bugs), `silent-failure-hunter` (swallowed exceptions, silent fallbacks, exactly the importer's risk), `pr-test-analyzer` (coverage gaps), `code-simplifier` (readability, which matters more than usual here because Baron must read it).
- `security-guidance`: pattern warnings on every edit and an automatic review of each commit and push; it needs Python 3.10+ on the machine, which Phase 0 provides.
- `feature-dev`: `/feature-dev` for any feature added after Phase 5, so the architecture step happens before the code.

What "passes" means: no error-level findings left unaddressed; each accepted finding is fixed in the same commit; each rejected finding gets a one-line reason in the commit message.

**Manual checks**: five hand spot-checks of import issues (Phase 3); one end-to-end booking refusal and override (Phase 5); the Pages link in a private window (Phase 6).

---

## 8. Assumptions

### 8.1 Made now, documented in the product

1. A reservation's day range is end-inclusive; "3rd to 5th" occupies three days.
2. Days are calendar days at the facility; there are no times on reservations. Arrival and departure times are annotations.
3. A berth's length is the number in its label; berths without a number (finger piers, small craft slips) are `exclusive` slips of unknown length until told otherwise.
4. "North Pier West/Face/East" are `linear` berths; "Inner Channel", "South Float West/East" are `linear` too (they hold more than one small boat); finger piers and small craft slips are `exclusive`.
5. Clearance between vessels on a linear berth is 10 feet (a placeholder; configurable per berth).
6. Events and closures occupy the berth's full length; a closure additionally refuses everything.
7. A vessel's length comes from the registry sheets; when two lengths disagree, the vessel has no length until a person chooses.
8. Vessel identity is the case-folded name with its type prefix; "Barge SALT DORY" and "Barge Salt Dory" are one vessel; "R/V Quiet Tern" and "R/V Quiet Heron" are two.
9. Pre-2009 spans inferred from fills, borders or repeated names are recorded as inferred and shown with a marker in the UI.
10. The two "2018" blocks on the 2010 sheet are November and December 2010.
11. Cells outside the day columns, legend rows and text in unlabelled rows are issues, not reservations.
12. The 8YR summary is reference material, not ground truth; the importer reports the gap.
13. Tours do not occupy berths and carry no rules.
14. There is one coordinator; no authentication, no multi-user editing, in v1.
15. Draft and water depth are not modelled (WHOI's 19-foot limit is noted as a future rule).

### 8.2 Open questions for Baron to decide in Phase 1

- Should events (community sail days) occupy the whole berth, or a configurable length? (Default: whole berth.)
- Should an UNKNOWN verdict block saving, or save as `planned` with a warning? (Default: block, allow override with reason.)
- Should the harbor view show one day or a rolling week? (Default: one day, with the scrubber.)

---

## 9. Risks and mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Machine setup eats the budget (Homebrew, Python, gh) | Medium | Phase 0 is done first and is mostly waiting; the guide has the exact commands; if `brew` fails, python.org's installer plus GitHub Desktop is the fallback. |
| Importer rabbit hole | High | Hard timebox; every unhandled case becomes an issue row; the golden count test stops regressions. |
| Visuals before substance | Medium | Harbor view is Phase 5, after tests, API and import; it renders engine output only. |
| Baron cannot explain something | Medium | Every phase has an "explain afterwards" line; decision records; Phase 7 rehearsal; anything not explainable gets simplified or cut. |
| Pages demo misleads (looks live, is static) | Low | Labelled "read-only snapshot generated on <date>"; quickstart for the live app is three commands. |
| Wrong domain guess (capacity, clearance) | Medium | Numbers are per-berth settings, not constants; assumptions are listed in the README; the interview answer is "here is where you change it". |

---

## 10. Resources

- The sample workbook: `data/Dock Schedule - Synthetic Sample.xlsx`; the study of it: `docs/data-study/` (start with `extract_report.md`, `taxonomy_report.md`, `registry_report.md`).
- Four independent design proposals that fed this plan: `docs/data-study/design-proposals/`.
- WHOI Iselin Marine Facility: <https://www.whoi.edu/what-we-do/explore/ships/marine-facilities-operations/iselin-marine-facility/> and the real schedule PDF linked in Section 1.1.
- openpyxl (merged cells, fills): <https://openpyxl.readthedocs.io/>
- FastAPI: <https://fastapi.tiangolo.com/> (the tutorial's first three pages are enough)
- SQLite date functions: <https://sqlite.org/lang_datefunc.html>
- GitHub Pages from a folder: <https://docs.github.com/en/pages>
- Beginner Git/GitHub: `docs/GITHUB_GUIDE.md` in this repo.
- Review plugins (already installed for the user account): pr-review-toolkit, security-guidance, feature-dev from `anthropics/claude-plugins-official`.

---

## 11. Demo script and interview preparation

**The first two minutes for a reviewer.** Open the Pages link: the harbor view is playing through a busy summer month, boats sliding in and out, one hull overhanging a float with a "+30 ft" badge. Click Audit: "2,244 stays from 23 years; 733 with inferred end dates; N days over capacity; N vessels longer than their berth; 5 mislabelled months". Open the README: three commands, run locally, open `/docs`, post a 120-foot vessel to the 75-foot Pier Face, read the refusal, click suggest, see the 240-foot East face offered first because the 410-foot West face should stay free.

**Eight questions to expect, with the shape of the answer.**

1. *Why did you model berths with linear capacity?* Because the data shows two vessels on one 410-foot berth on the same day, expressed by duplicated rows; a slot model would refuse what the facility does every summer.
2. *How do you detect a double booking?* Per day, sum the occupied lengths on the berth; compare with the berth length; for exclusive slips, any co-occupant is a conflict. End-inclusive overlap test on dates.
3. *What happens when you do not know a vessel's length?* The verdict is UNKNOWN and the booking is blocked until a length or an override reason is entered. Only 19 of 504 historical vessel names had a known length, so this is the common case, not an edge case.
4. *How did you import 23 years of a messy spreadsheet?* Era detection per month block, span inference with a stated priority, classification of cell text into four kinds, and an issue log for everything that did not fit. The audit report lists the counts.
5. *What assumptions did you make?* Section 8; the top three are end-inclusive days, linear capacity with a 10-foot clearance, and treating notes as annotations.
6. *Why FastAPI and SQLite?* Smallest thing that gives typed validation, interactive docs and real date queries with no server to run; everything is one file to clone.
7. *Where would this break at scale or in production?* Single user, no auth, SQLite; the rules are O(overlaps × days) which is fine for thousands of stays; next steps would be accounts, an audit trail of edits, and depth/draft rules.
8. *What would you do with two more days?* Pyodide demo with live refusals, email intake, a rafting model (vessels alongside each other count against width, not length), and the tours module.

---

## 12. Definition of done

- [ ] `git clone`, three commands, app runs; `pytest` green.
- [ ] A vessel that does not fit is refused with a sentence that names the numbers.
- [ ] A shared berth over capacity is refused with the co-occupants named.
- [ ] Unknown length gives UNKNOWN, and an override with a reason is stored and visible.
- [ ] The importer runs on the sample and the audit report is committed.
- [ ] Harbor view animates and shows at least one real conflict from history.
- [ ] GitHub Pages link works in a private window and says it is a snapshot.
- [ ] README: what, why, quickstart, assumptions, known limits, links.
- [ ] `docs/decisions/` has at least six one-paragraph records.
- [ ] Every phase's review gate ran; findings fixed or explained in commit messages.
- [ ] Baron has rehearsed the eight answers out loud.

---

## Appendix A — Glossary

**Berth**: a place a vessel ties up; here identified by name and length in feet. **LOA**: length overall, the vessel's full length. **Draft**: how deep the hull sits; not modelled in v1. **Rafting**: mooring a vessel alongside another vessel instead of the pier. **Linear capacity**: the rule that vessels along a pier face may not add up to more than its length. **Exclusive berth**: one occupant at a time. **End-inclusive**: the end date counts as occupied. **Finding**: one machine-readable reason a booking is refused or warned about. **Override**: saving despite a finding, with a recorded reason. **Importer**: the code that turns the workbook into database rows. **Audit**: the rules engine run over all history.

## Appendix B — What already exists in the repo today

- `data/Dock Schedule - Synthetic Sample.xlsx`: the input.
- `docs/GITHUB_GUIDE.md`: setup and GitHub instructions for a first-timer.
- `docs/data-study/`: the Ruby scripts used to take the workbook apart on a machine that had no Python yet, the CSVs they produced (`bookings.csv` with 2,244 rows, `vessels.csv`, `value_taxonomy.csv`, `tours.csv`, `usage_summary.csv`), and the reports quoted in Section 2. The Python importer built in Phase 3 supersedes these scripts; they stay as evidence of the study.
- `docs/data-study/design-proposals/`: four independent plans (domain-model purist, showman, pragmatic MVP, data archaeologist) written from different angles before this synthesis; the reasons for choosing between them are the "Rejected" columns above.
- `.gitignore`, this file.
