# Dock Scheduler

A reservation system for a marine research waterfront: berths of different lengths, vessels and events that occupy them for day ranges, and a **referee** that answers, with reasons, the two questions the facility used to answer by staring at a spreadsheet grid:

- **Is this berth double-booked?** On a pier face several vessels tie up end to end, so the question is arithmetic: do the lengths plus clearance fit the face on every day? On a slip: is anyone else there?
- **Does this vessel fit here?** Vessel length against berth length, and **UNKNOWN**, never OK, when a length is not on file.

It also imports the facility's 23-year legacy schedule, records every ambiguity in it instead of guessing, and audits that history with the same rules that guard new bookings.

**Live app:** [dock-scheduler-henna.vercel.app](https://dock-scheduler-henna.vercel.app) · **Read-only history:** [GitHub Pages](https://broccolibabe0711.github.io/dock-scheduler/) · **Deployment guide:** [Vercel](docs/DEPLOY_VERCEL.md) · **Plan:** [FRAMEWORK.md](FRAMEWORK.md) · **Audit:** [docs/AUDIT_REPORT.md](docs/AUDIT_REPORT.md)

The live app saves bookings in PostgreSQL. It is a shared synthetic demo without
sign-in. Use **Book** to make a reservation, **Today** to view the current month,
or **Sample history** to explore July 2017.

Built as a take-home for Columbia Software Solutions.

**Understand and test it:** [Website guide and assumptions](https://dock-scheduler-henna.vercel.app/guide.html) · [Engineering walkthrough](docs/ENGINEERING_WALKTHROUGH.md) · [Acceptance tests and rehearsal questions](docs/ACCEPTANCE_TESTS.md).

## What the legacy data says

Numbers from `python -m dock.audit` on the sample workbook:

| | |
|---|---|
| Month grids read | 272 blocks across 23 sheets, three layout eras |
| Cell runs | 2,244 encountered; 80 outside day columns excluded; 2,164 read |
| Reservations after stitching month-split stays | 1,982 (122 stitched) |
| Notes kept as annotations, not bookings | 46 ("ETA 1200", "Fuel truck"…) |
| Vessel names, after case normalisation | 504 in the grids; only 33 of 1,927 vessel stays have a known length (98.3% of stays unknown) |
| Reservations with vessels longer than their berth | 9 records involving 5 distinct vessel names |
| Stays over a closed berth | 1 |
| Anomalies logged instead of silently fixed | 479 (mislabelled months, merges past the month end, duplicated rows, text in header rows…) |

The grid could never put two names in one cell, so it contains no within-row double bookings; where two vessels shared a face, operators inserted a second row with the same berth label. That is why the model uses linear capacity instead of one vessel per berth.

## Run it locally

```bash
git clone https://github.com/broccolibabe0711/dock-scheduler.git && cd dock-scheduler
```

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

```bash
.venv/bin/uvicorn dock.api:app
```

Open <http://127.0.0.1:8000>. The sample workbook is imported into `dock.db` on first start. The interactive API documentation is at <http://127.0.0.1:8000/docs>: try `POST /api/check` with a 120-foot vessel on the 75-foot North Pier Face and read the refusal.

Tests (SQLite by default; set `TEST_DATABASE_URL` to a disposable PostgreSQL database to test both engines; CI supplies one):

```bash
.venv/bin/python -m pytest -q
```

Regenerate the audit report and the static snapshot:

```bash
.venv/bin/python -m dock.audit "data/Dock Schedule - Synthetic Sample.xlsx" && .venv/bin/python -m dock.export "data/Dock Schedule - Synthetic Sample.xlsx"
```

## What you can do in it

- **Harbor is the default landing view.** Sample history opens the July 2017 closure overlap; Fit example opens the July 2010 overhang. Known lengths share a scale; geometry and widths are schematic, and unknown hulls use a labelled 40 ft placeholder.
- **Grid**: the month grid the coordinator already knows, with bars for stays, red underlines on days a berth is over capacity, amber where a length is missing. Click an empty day to start a booking there.
- **Book**: pick a vessel (or type a new one), berth and dates. *Check* returns a verdict and findings in words and numbers; *Suggest a berth* ranks alternatives, smallest fitting berth first; *Save* refuses blocking verdicts unless you write an override reason, which is kept on the record.
- **Harbor**: a plan of the waterfront drawn to one scale. Hulls are sized to their real length; step or play through days; over-capacity berths pulse, over-length hulls overhang with a "+45 ft" badge, unknown lengths are dashed.
- **Audit** and **Issues**: the legacy history judged by the same rules, and everything the importer logged.
- **Vessel registries**: search dimensions, inspect notes, open the source workbook, and preview a length correction before saving. Blocking impacts require a reason tied to the current preview. The measurement, its before/after findings and the reason are saved together.
- **Edit reservations** from a Grid bar or Harbor hull: change dates, berth, status or notes. The API rechecks changes to occupancy. A previous override does not authorize a new conflicting edit.
- **Operational notes and provenance**: imported annotations appear under Grid and Harbor. Details explain when a historical span was inferred from cell colour or repeated names.

## How it is built

```
dock/models.py    Berth, Vessel, Reservation, DayRange, Finding      plain, validated, immutable
dock/rules.py     check(), suggest_berths(), audit()                 the only place rules live
dock/classify.py  what a grid cell's text is (vessel/event/closure/note)
dock/registry.py  the messy Science/Yachts sheets -> vessels with lengths
dock/importer.py  23 year grids -> reservations + annotations + issues
dock/audit.py     the rules over history -> docs/AUDIT_REPORT.md
dock/db.py        SQLite locally, PostgreSQL on Vercel; rows <-> objects
dock/postgres.py  PostgreSQL adapter, schema initialization and transaction lock
dock/api.py       FastAPI: parse -> call the referee -> return findings
dock/export.py    JSON snapshot for the static demo
site/             vanilla HTML/CSS/JS, no build step; runs on the API or on the snapshot
tests/            rules (table-driven, sentence-named), importer (fixture + real sample), API
docs/decisions/   one paragraph per decision; docs/ASSUMPTIONS.md; docs/data-study/ the analysis behind it all
```

Python 3.12, standard-library `sqlite3`, `openpyxl`, FastAPI, `psycopg`, `pytest`. No JavaScript toolchain.

On Vercel, `DATABASE_URL` selects persistent PostgreSQL. Missing database configuration
stops startup instead of losing edits in temporary storage. See [deployment instructions](docs/DEPLOY_VERCEL.md)
and [decision 8](docs/decisions/0008-persistent-vercel-deployment.md). CI runs API workflows
against both storage engines, including simultaneous booking conflicts and restart persistence.

New bookings and edits to occupancy go `request -> rules.check() -> 409 with findings, or saved`. Notes-only edits and cancellations are allowed. Measurement corrections recheck affected bookings, including neighbours, and store an explicit review when blocking findings remain. The front end renders server decisions. The GitHub Pages snapshot uses the same Python rules but reflects the original workbook, not later live edits ([decision 6](docs/decisions/0006-static-demo-without-rules-in-javascript.md)).

The **Audit tab is a historical import snapshot**. Grid, Harbor and the registry use current live data. The additive `vessel_changes` table keeps measurement reviews; it is not a complete, authenticated edit log. See [decision 9](docs/decisions/0009-reviewed-measurement-changes.md).

## The rules in one screen

```
overlaps(a, b):        a.start <= b.end and b.start <= a.end            days are inclusive
occupied(r, berth):    berth.length if r is an event or closure
                       else r.vessel.length + berth.clearance            None if unknown
per day on a face:     sum(occupied) must not exceed berth.length
                       known lengths already over  -> CONFLICT
                       fits so far but one unknown -> UNKNOWN
on a slip:             anyone else there            -> CONFLICT
fit:                   vessel.length > berth.length -> CONFLICT; missing -> UNKNOWN
closure:               refuses everything and refuses to displace anyone
```

## Assumptions and limits

The numbered list is in [docs/ASSUMPTIONS.md](docs/ASSUMPTIONS.md). The biggest: end-inclusive days; 10 feet of clearance per vessel on a shared face; events take the whole berth; unknown lengths block. Not in v1: users and authentication, draft and water depth, rafting as a model (it appears as a note when an override is being considered), times of day.

## Decisions

[docs/decisions/](docs/decisions/): end-inclusive days, linear capacity, unknown is not OK, rules in one pure module, an importer that records rather than guesses, a static demo without rules in JavaScript, validation at the edge.
