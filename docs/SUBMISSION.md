# Dock Scheduler — submission guide

Baron Zhang · Columbia Software Solutions take-home · 22 September 2026

[Open the live app](https://dock-scheduler-henna.vercel.app/) · [Source repository](https://github.com/broccolibabe0711/dock-scheduler) · [Full engineering explanation](https://github.com/broccolibabe0711/dock-scheduler/blob/main/docs/ENGINEERING_WALKTHROUGH.md) · [Test evidence](https://github.com/broccolibabe0711/dock-scheduler/blob/main/docs/SUBMISSION_VERIFICATION.md)

## What this delivers

Dock Scheduler turns the supplied scheduling workbook into an operable reservation website. It manages vessels, events and closures, checks every occupied day for individual fit and conflicting use, suggests alternative berths, and saves bookings in persistent PostgreSQL on Vercel. The default Harbor view makes the reason for a finding visible; Grid and Side by side retain the familiar calendar context.

The central design choice is shared linear capacity. A long pier face can hold several vessels end to end, so the system evaluates occupied length and clearance. Missing measurements produce an explicit UNKNOWN result. Booking checks, suggestions and the historical audit reuse one Python rule engine.

## A three-minute review

1. Open the live app and choose **Fit example · 2010** in Schedule. On 29 July 2010, **R/V Clear Tern** is 120 ft long on **North Pier Face**, a 75 ft berth. The hull and written finding show the same **45 ft** overhang.
2. Choose **Side by side**. Select another day number in Grid; Harbor follows it. Open a reservation to see its dates, source reference and edit controls.
3. Open **Book**. Choose **R/V Clear Tern**, **North Pier Face**, and 1–2 July 2035. Press **Check**: the vessel is too long. **Suggest a berth** offers alternatives evaluated by the same engine. These actions do not save. Availability can change in the shared live demo.
4. Open **Audit**, choose **OSV Amber Reef** from the name suggestions and **Closure overlap** as the finding type. The historical finding identifies **Utility work**, **South Float East**, and **11–15 July 2017**. Clear the filters to restore the full evidence.
5. Open **Vessel registries**, find **Clear Tern**, and choose **Review length**. Preview a proposed 130 ft measurement to see the affected bookings; close without saving. The source workbook and assumptions are linked from the interface.

To test saving, create a clearly labelled event on an otherwise empty future berth-day, refresh to see it persist, then cancel it in its details. Use a fresh local database for extensive or destructive experiments. The final release verification already exercised create/read/conflicting-save refusal/edit/read/cancel on production.

## Requirements and evidence

| Review criterion | Implementation | Where to inspect |
|---|---|---|
| It works | Persistent reservations, vessel/event/closure handling, fit and capacity decisions, alternatives, edits and cancellation. | Live app; API documentation at /docs; verification record and automated tests. |
| Clear structure | Domain models → pure rules → storage → FastAPI → vanilla HTML/JS. Booking decisions are checked and saved in one write transaction. | README file map; dock/models.py, rules.py, db.py, postgres.py and api.py. |
| Explicit assumptions | Inclusive dates, shared-face clearance, whole-berth events, missing measurements and import inferences are stated. | docs/ASSUMPTIONS.md; eleven decision records; visible Issues and source references. |
| Explainable decisions | Before/after measurement previews, arithmetic in findings, a schematic Harbor view, and documentation connecting the interface to the code. | docs/ENGINEERING_WALKTHROUGH.md; website guide; this review sequence. |

## Decisions and tradeoffs

- **Dates and capacity:** both endpoints occupy the berth. Shared vessels each use their length plus 10 ft clearance; a lone vessel is checked for fit without that shared allowance. Events take the whole berth. Closures prohibit vessel/event use; two closures may overlap. These are stated product assumptions, not confirmed operating policy from the facility.
- **Uncertainty:** missing required measurements yield UNKNOWN and block normal saving. An explicit override records an exception without removing the underlying finding. A changed booking needs a fresh reason when still blocked. Measurement corrections preview affected bookings and neighbours, reject stale acknowledgements, and store the correction and review together.
- **Data provenance:** the import contains 1,982 reservations, 46 annotations and 479 recorded issues. Nine reservation records fail individual fit, twelve shared berth-days are unverifiable, and one stay overlaps a closure. Of 1,927 vessel stays, 1,894 lack a known length (98.3%); zero detected arithmetic overloads therefore does not prove historical capacity was safe.
- **One rules engine:** the API, berth suggestions and historical audit share Python logic. The browser presents results and handles interaction. PostgreSQL write locking keeps concurrent check-and-save operations consistent; SQLite makes local setup simple.
- **Interface:** Schedule offers Harbor, Grid and Side by side. Known vessel/berth lengths share a drawing scale, while layout, widths and unknown hulls are schematic. Audit supports combined filters and optional remembered preferences. All 19 typed fields have native suggestion menus and retain custom entry.
- **History versus live data:** Audit describes the original workbook. Grid, Harbor and the registry use the editable ledger. GitHub Pages is a separate read-only snapshot; the submitted live URL is Vercel.

## Scope and AI assistance

This is a shared synthetic-data demo without sign-in. It does not implement production permissions, a complete attributed reservation edit log, water-depth/draft rules, physical rafting constraints or hour-level scheduling. Measurement reviews are recorded, but they are not a substitute for a full user audit trail. Extensive independent usability testing and a formal accessibility audit have not been completed.

Development used Claude and Codex for substantial code generation, debugging, tests and documentation. Baron directed the product requirements and iterations, including the Harbor emphasis, linked layouts, audit filters and input suggestions. The documentation and verification evidence are provided to make the result inspectable. The source, decision records and executable tests are included for review.

## Run and verify locally

Use Python 3.12. From the repository root:

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn dock.api:app
```

Open http://127.0.0.1:8000. A new local SQLite database imports the included synthetic sample on first startup. The public repository README has the clone command and deployment details.

```bash
.venv/bin/python -m pytest -q
node --test tests/frontend.test.cjs
.venv/bin/python scripts/verify_deployment.py --base-url https://dock-scheduler-henna.vercel.app
```

Node 22 or later runs the frontend tests; the website has no JavaScript build step. Set TEST_DATABASE_URL only to a disposable PostgreSQL database to run both database suites. Its test fixtures replace its contents. Do not point the tests or the workbook-import command at production storage.

[Detailed acceptance scenarios](https://dock-scheduler-henna.vercel.app/acceptance.html) separate reproducible tasks from completed verification. [Rules and assumptions](https://dock-scheduler-henna.vercel.app/guide.html#rules-and-assumptions) explain the boundaries of each verdict.
