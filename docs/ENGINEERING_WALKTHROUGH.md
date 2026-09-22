# Dock Scheduler: the website and its engineering

Prepared for Baron Zhang · Updated 22 September 2026 for submission

[Use the live website](https://dock-scheduler-henna.vercel.app/) · [Explore the source](https://github.com/broccolibabe0711/dock-scheduler) · [Run the acceptance guide](ACCEPTANCE_TESTS.md)

## A paragraph you can use in the submission

Dock Scheduler turns a marine research facility's spreadsheet into a working reservation website. It manages vessels, events and closures across berths of different lengths, checks each requested day for fit and conflicting use, and explains its decisions with names and measurements. The central design choice is to treat a long pier face as shared linear space: several vessels may fit end to end, so overlapping dates alone do not always mean a double booking. Missing measurements produce an explicit UNKNOWN result, and saving a blocked booking requires a recorded override reason. One Python rules engine supports booking checks, berth suggestions and an audit of 23 years of sample history. The website combines a month grid, a searchable vessel registry and an animated Harbor view that draws known vessel lengths to scale. FastAPI connects the interface to SQLite for local development and persistent PostgreSQL for the live Vercel deployment. The project includes tests, documented assumptions and an import issue log so its behavior and limitations can be inspected.

The follow-up release adds reservation editing, operational notes and reviewed measurement corrections. If asked about authorship, explain the AI assistance honestly and identify the decisions and code you have personally reviewed. Use the acceptance guide to rehearse and record your own results.

## The website, side by side

| What the user sees or does | What the engineering does, and why |
|---|---|
| **Harbor:** the default layout inside Schedule and the normal landing view. Step through dates, press Play, or choose Sample history. | The browser requests the day's occupants and findings. `harbor.js` draws SVG hulls and berth faces. Known lengths share a scale of one SVG unit per foot. Dashed hulls identify missing lengths; their 40 ft drawing size is a placeholder, never a measured value used to approve a booking. The layout and hull widths are illustrative. |
| **Grid:** inspect a month, select a reservation, or click an empty berth-day to begin a booking. | The same reservations are arranged into date bars. Server-provided flags mark fit/capacity problems and unknown measurements. This retains the familiar spreadsheet layout while removing the need to judge all conflicts by eye. |
| **Book:** select a vessel, berth and inclusive date range; choose vessel, event or closure. | FastAPI validates the request and constructs domain objects. A vessel reservation refers to a vessel; an event or closure uses a title. Reversed dates, invalid lengths and unexpected fields are rejected. |
| **Check:** ask whether the proposed booking works. | `/api/check` returns OK, CONFLICT or UNKNOWN with structured findings. It does not create a reservation or vessel. The browser renders the explanation rather than implementing a second rule system. |
| **Suggest a berth:** see suitable alternatives. | The Python rules evaluate alternatives over the requested dates and rank fitting choices by berth size. A 120 ft vessel can be offered the 240 ft North Pier East before the 410 ft North Pier West. |
| **Save / override / cancel:** record a booking, explain an exception or free the berth. | Saving acquires a database write lock, reloads the relevant state, checks the booking and either refuses it with HTTP 409 or commits it. A nonempty override reason allows an exception and is stored. Cancellation removes occupancy without needing a fit check. The details dialog now edits berth, dates, status and notes. A newly conflicting edit needs a fresh reason. |
| **Vessel registries:** search names, inspect length/draft/operator information and open the original Science & Yachts workbook. | The registry combines names from the sample's contact sheets, historical schedule and live additions. Missing dimensions remain unknown. The original import contains 575 vessels, 158 with known length; later live edits may change these totals. |
| **Review length:** preview a corrected measurement, inspect affected bookings and record the decision. | The API compares before/after results for the vessel and overlapping neighbours. A fingerprint detects a stale acknowledgement. The measurement and review record commit together; the bookings remain visible for repair. |
| **Guide and annotations:** see assumptions, import notes and inferred-date explanations. | Operational annotations appear beside the relevant day or month. The guide connects UI actions to implementation and lists the rules explicitly. |
| **Audit:** see what the rules found in the historical import. | Python runs the shared rule logic over the extracted reservations and stores a report. This is the import-time history audit, not a continuously recalculated audit of later live edits. |
| **Issues:** inspect ambiguous or malformed source data. | The importer preserves a sheet/cell reference and an explanation when it skips, corrects or cannot confidently interpret material. The sample produces 479 issues; an issue is a recorded data problem, not automatically a scheduling conflict. |
| **API documentation:** open `/docs`. | FastAPI exposes the accepted request fields and response shapes. This lets a reviewer inspect the contract between browser and server and try a read-only check directly. |

Source map: [page structure](https://github.com/broccolibabe0711/dock-scheduler/blob/main/site/index.html), [browser behavior](https://github.com/broccolibabe0711/dock-scheduler/blob/main/site/app.js), [Harbor drawing](https://github.com/broccolibabe0711/dock-scheduler/blob/main/site/harbor.js), [API](https://github.com/broccolibabe0711/dock-scheduler/blob/main/dock/api.py).

## The engineering process, step by step

This is a reconstruction of the implemented process from the source, commit history, decision records and supplied handoff. It explains what each stage produced and why; it does not certify every historical tool run or time estimate in the handoff.

### 1. Turn the brief into observable behavior

The brief asks for berth reservations, varying vessel and berth lengths, day ranges, non-vessel events and automatic detection of scheduling problems. That becomes a concrete acceptance flow: enter a booking, get a comprehensible verdict, save a valid booking, reject an invalid one unless an explicit exception is recorded, and see the result later. A live link, tests and explainable design support the four review criteria: works, structure, assumptions and reasoning.

Output: the [project framework](https://github.com/broccolibabe0711/dock-scheduler/blob/main/FRAMEWORK.md) and a bounded first version. Authentication, depth, times of day and a complete rafting model were deferred.

### 2. Study the workbook before choosing a data model

The sample contains 27 sheets: 23 year grids covering 1997–2019, two vessel registries, a summary and a tours sheet. The grids change layout over time. Merged cells, repeated names and colored runs can all represent multi-day stays. Duplicate berth rows can represent multiple vessels on one face. Some text is an operational note rather than an occupation of the berth.

The study exposed the two most consequential facts: long faces can hold multiple vessels, and measurements are missing for most historical bookings. Only 33 of 1,927 vessel stays have a known vessel length. A model that assumes “one berth, one boat” or invents missing lengths would give misleading answers.

Output: [data-study scripts and reports](https://github.com/broccolibabe0711/dock-scheduler/tree/main/docs/data-study), preserved so another person can inspect the analysis. The early study used Ruby; the application importer uses Python and openpyxl.

### 3. Write assumptions before encoding them

The system uses inclusive dates, so the 3rd through the 5th occupies three days. Each vessel on a shared face uses its length plus 10 ft of clearance; a lone vessel is checked against berth length without that shared-occupancy allowance. Events take the entire berth. Closures prohibit other use, while two closures may overlap. A missing required measurement yields UNKNOWN.

These are explicit product choices, not established operating rules of the real facility. The sample's aggregate finger-pier and small-craft rows have unknown capacity rather than invented individual slip dimensions. The engine supports an exclusive-slip mode, but the imported berth rows use the linear model.

Output: [20 assumptions](https://github.com/broccolibabe0711/dock-scheduler/blob/main/docs/ASSUMPTIONS.md) and [decision records](https://github.com/broccolibabe0711/dock-scheduler/tree/main/docs/decisions). They make later requirement changes identifiable and testable.

### 4. Define the vocabulary in domain objects

`Berth` describes a place and its capacity; `Vessel` describes a craft and known dimensions; `DayRange` represents occupied days; `Reservation` joins a use to a berth and dates. A `Finding` carries an explanation and numbers, and `CheckResult` carries the verdict. `DayLoad` describes the occupants and known capacity use for one berth on one day.

The constructors validate values, including finite positive dimensions. Vessel identity normalizes names so trivial case or prefix punctuation differences do not create duplicate vessels. Keeping these concepts explicit makes both rules and tests read like the domain. [Domain models](https://github.com/broccolibabe0711/dock-scheduler/blob/main/dock/models.py)

### 5. Build one rule engine independent of the website

The rule engine receives objects and returns findings. It has no HTTP calls, database connection or clock. It checks dates, berth availability, individual fit, exclusive occupancy, shared capacity and closures. Suggestions and historical auditing reuse the same logic.

The three verdicts mean: **OK**, the modeled checks pass; **CONFLICT**, a definite rule is violated; **UNKNOWN**, necessary evidence is absent. A known partial sum already exceeding capacity remains CONFLICT even when another vessel's length is missing. This prevents uncertainty from hiding a definite failure. [Rules](https://github.com/broccolibabe0711/dock-scheduler/blob/main/dock/rules.py)

### 6. Convert the spreadsheet while preserving uncertainty

The importer identifies month blocks and actual day columns, then determines each stay's span using merged cells, fill runs, repeated names or a single day. It classifies text as vessel, event, closure or annotation; joins registry measurements; and stitches matching stays across month boundaries. Source references preserve how a span was interpreted.

It skips duplicate month blocks and records unlabelled text, damaged headers and out-of-range cells. It explicitly logs the correction of two wrongly labeled 2018 month headers on the 2010 sheet. Conflicting registry dimensions remain unknown. The summary sheet is retained for comparison rather than forced to agree with the reconstructed grids.

Output: **1,982 reservations, 46 annotations and 479 issues**. The extraction encountered 2,244 cell runs, excluded 80 outside day columns and read 2,164. Removing fourteen runs from repeated month blocks left 2,150. Separating 46 annotations left 2,104 reservation fragments; 122 month-boundary joins reduced those to 1,982 reservations. [Importer](https://github.com/broccolibabe0711/dock-scheduler/blob/main/dock/importer.py), [registry parser](https://github.com/broccolibabe0711/dock-scheduler/blob/main/dock/registry.py)

### 7. Audit the history with the same rules

The audit found nine reservation records involving five distinct vessel names that were too long for their assigned berth, twelve unverifiable shared berth-days and one vessel stay overlapping a closure. It detected zero over-capacity berth-days with the available dimensions. That does not prove historical capacity was always sufficient: 98.3% of vessel stays lack a known length.

The audit also compares usage-days reconstructed from the grids against the workbook's summary and exposes disagreement. The product's value is an honest, reproducible explanation, even when the answer is “we cannot determine this from the source.” [Audit report](https://github.com/broccolibabe0711/dock-scheduler/blob/main/docs/AUDIT_REPORT.md)

### 8. Add durable storage and an HTTP interface

SQLite keeps local setup simple: one database file, automatically seeded when empty. Tables store vessels, berths, reservations, annotations, import issues, tours and measurement reviews. SQL constraints provide another boundary against invalid data. The storage layer translates rows into the same domain objects the rules already understand.

FastAPI validates incoming JSON, loads the relevant objects, asks the rules engine and returns structured JSON. New reservations are checked inside a write transaction. Booking-sensitive reservation edits are checked again and require a fresh override if still blocked. Notes-only edits and cancellation have deliberate exceptions. A length correction rechecks existing affected bookings, requires an explicit review of blocking outcomes, and records the evidence with the change. An additive schema migration creates this history table without reimporting or deleting the existing ledger. [Storage](https://github.com/broccolibabe0711/dock-scheduler/blob/main/dock/db.py), [schema](https://github.com/broccolibabe0711/dock-scheduler/blob/main/dock/schema.sql), [API](https://github.com/broccolibabe0711/dock-scheduler/blob/main/dock/api.py)

### 9. Build the interface and adapt the Harbor prototype

The frontend uses HTML, CSS, JavaScript and inline SVG without a frontend build pipeline. A small data adapter reads either live API responses or exported JSON. The Grid preserves the familiar planning view; Book exposes checks and suggestions; Harbor turns measurements and findings into a visual explanation.

Browser code handles presentation, dates, searches and animation. It does not decide whether a reservation is allowed. Request sequencing prevents late responses from replacing a newer search or selected day. The implementation includes keyboard tab navigation, a native details dialog, accessible hull controls and reduced-motion styles; these features have not been subjected to a comprehensive accessibility audit in this review.

Output: the [frontend](https://github.com/broccolibabe0711/dock-scheduler/tree/main/site) and [original Harbor prototype](https://github.com/broccolibabe0711/dock-scheduler/blob/main/prototypes/harbor.html).

### 10. Test behavior and preserve regressions

Rules tests cover meaningful cases such as inclusive boundaries, unknown dimensions, fit failures, closures, cancelled bookings and shared capacity. Importer tests use a small fixture workbook spanning layout eras plus checks against the real sample's totals. API tests cover refusals, overrides, editing, invalid inputs, concurrent bookings and persistence across application starts. Export tests check that static flags agree with the Python calculations.

The follow-up adds PostgreSQL adapter and failure-recovery coverage, concurrent cold-start checks, reviewed measurement tests, stale-review refusal, atomic rollback and non-destructive schema initialization. The accompanying release verification records the final run totals and deployment checks. Browser exercises cover the complete correction-and-repair flow. Passing these checks provides evidence for those behaviors; the acceptance guide separates automated results from independent usability and cross-browser work still to perform. [Tests](https://github.com/broccolibabe0711/dock-scheduler/tree/main/tests)

### 11. Publish a static history snapshot

Python exports the imported data and rule flags as JSON for GitHub Pages. That makes the historical Grid, Harbor, registry and audit available without running Python in the visitor's browser. Booking is disabled in this mode because no server is available to judge and save a request.

The snapshot is regenerated from the sample workbook. It is not a mirror of the editable production database. [Exporter](https://github.com/broccolibabe0711/dock-scheduler/blob/main/dock/export.py), [read-only site](https://broccolibabe0711.github.io/dock-scheduler/)

### 12. Deploy an operable site on Vercel

The live requirement added a FastAPI deployment on Vercel and a persistent Neon PostgreSQL database. `app.py` exports the application; configuration and dependencies are in the repository. Vercel supports FastAPI applications and these entrypoint conventions. [Vercel FastAPI documentation](https://vercel.com/docs/frameworks/backend/fastapi)

`DATABASE_URL` selects PostgreSQL. The application refuses to start on Vercel without that persistent database configuration. A small adapter preserves the existing storage interface. Its transaction-scoped advisory lock serializes cooperating writes across application instances so two conflicting saves cannot both be approved against the same old state. Imported IDs are followed by corrected identity sequences, and startup imports only into an empty ledger.

Output: the [live app](https://dock-scheduler-henna.vercel.app/), [deployment guide](https://github.com/broccolibabe0711/dock-scheduler/blob/main/docs/DEPLOY_VERCEL.md) and [deployment decision](https://github.com/broccolibabe0711/dock-scheduler/blob/main/docs/decisions/0008-persistent-vercel-deployment.md). The global lock favors straightforward correctness over high write throughput, which is a reasonable tradeoff for this small demo.

### 13. Verify the deployment and improve discoverability

The repeatable deployment script reads the live API, checks a 45 ft fit conflict and invalid dates, proves that measurement preview does not save, and checks that notes and review storage are available. Its optional write smoke creates a labelled test event, reads it back, refuses a competing event, edits its notes and cancels it in a cleanup step.

Harbor is the default landing view. “Fit example · 2010” and “Sample history” make meaningful examples easy to find. Five top-level tabs include a searchable vessel registry; the registry links to the original workbook, while Schedule provides Harbor, Grid and Side by side layouts. The guide, footer and Harbor caption now expose the assumptions and explain the schematic. Keyboard grid navigation uses one day-cell tab stop with arrow keys, and edits invalidate stale check results.

### 14. Close the handoff and rehearse

The storage hardening is integrated. The length-edit gap is addressed with impact preview and history; the reservation editor, annotations, provenance and documentation corrections complete the smaller follow-through items. The next applicant step is to trace one booking through the code and explain the tradeoffs aloud. Use the acceptance guide to test rules and persistence, then ask another person to complete the uncoached tasks.

The highest-value optional feature is a closure impact planner: preview displaced bookings and candidate berths without silently moving them. A data-confidence inbox and a printable daily operations brief follow. Keep authentication and a full edit log as requirements for real operational use, while the current site remains a shared synthetic demonstration.

## Follow one booking through the system

| Stage | Concrete example |
|---|---|
| Browser | A coordinator selects R/V Clear Tern, North Pier Face and 1–2 July 2030, then presses Check. |
| API | The request contains vessel ID, berth ID and ISO dates. FastAPI validates its shape; the server loads the vessel's 120 ft length and berth's 75 ft length. |
| Rules | Individual fit computes **120 − 75 = 45 ft too long** and returns CONFLICT with a fit finding. |
| Response | The browser displays the explanation. Check has saved nothing. A Save request would check again inside a write transaction and refuse a blocking verdict without a reason. |
| Alternatives | Suggest evaluates other berths for those dates. In this review's live check it offered the 240 ft North Pier East before the 410 ft North Pier West. |
| Persistence | A successful Save commits a reservation to PostgreSQL, and later reads draw it in the Grid and Harbor. An override preserves the reason as well as the booking. |

A separate shared-capacity example explains why overlap alone is not enough. On a 410 ft face, vessels of 274 ft and 100 ft use `(274 + 10) + (100 + 10) = 394 ft`, so they fit together. Adding a 60 ft vessel raises use to **464 ft**, exceeding capacity by **54 ft**. On an exclusive slip, the presence of another occupant would instead be sufficient to cause a conflict. Dates are inclusive: a stay ending on the 5th conflicts with one starting on the 5th; one starting on the 6th does not overlap.

## A repeatable two-minute demo

1. Open [Harbor](https://dock-scheduler-henna.vercel.app/#harbor). Choose **Fit example · 2010** (29 July 2010). Point out **R/V Clear Tern**, 120 ft on the 75 ft North Pier Face, and the **+45 ft** overhang.
2. Press **Sample history** to jump to **12 July 2017**. Explain that **Utility work** closes South Float East while **OSV Amber Reef** is scheduled there.
3. Open **Audit**. State the precise findings: nine too-long reservation records, twelve unverifiable shared berth-days and one closure overlap. Explain why zero detected capacity overloads does not prove the history was safe.
4. Open **Book**. Select **R/V Clear Tern**, **North Pier Face**, **1–2 July 2030**. Press **Check**, then **Suggest a berth**. These actions do not save a booking. Explain the 45 ft refusal and the smallest-fitting-first result; live edits can change future suggestions.
5. Open **Vessel registries**, search **Clear Tern**, and show the original workbook link. Finish at [API docs](https://dock-scheduler-henna.vercel.app/docs) or the source to connect the visible result to the implementation.

If demonstrating Save or an override, use a clearly labeled demo record and cancel it afterward. The live site is shared and editable.

## Eight questions to rehearse

| Question | An answer you should be able to explain in your own words |
|---|---|
| Why shared linear capacity? | Duplicate berth rows show that simultaneous occupancy can be legitimate. A 410 ft face can hold several shorter vessels, so capacity depends on lengths and clearance. |
| How do you detect a double booking? | Compare inclusive date ranges, examine the occupants of each affected day and apply the berth's capacity model. Events and closures reserve the full berth. |
| What if a length is missing? | Return UNKNOWN when the decision needs that measurement. Require a measurement or an explicit override reason. Most historical stays are in this situation. |
| How did you import the spreadsheet? | Detect the layout and day columns; infer spans using a stated priority; classify the text; join registries; stitch month boundaries; retain provenance and log ambiguities. |
| Which assumptions might change? | Inclusive dates, whole-berth events, 10 ft shared clearance and name-based identity. Confirm these with the operator before using the system for real scheduling. |
| Why this stack? | Python keeps parsing and rules together; FastAPI provides validated requests and API docs; SQLite simplifies local setup; PostgreSQL provides persistent shared storage for the Vercel deployment. Plain JavaScript keeps the interface small. |
| What are the limitations? | No accounts, per-user permissions or complete edit history; no depth, times or full rafting model; incomplete measurements; a fixed historical audit rather than a live audit dashboard. Measurement reviews cover dimension corrections, not all edits. |
| What would you do next? | Rehearse the demo, run uncoached usability tests and consider a closure impact planner. For real operations, add access controls and validate rules with users. |

## A small glossary

| Term | Meaning here |
|---|---|
| Domain model | The objects and vocabulary of the problem: berth, vessel, reservation and finding. |
| Pure function | A calculation whose result depends on its supplied inputs, without reading a database or changing outside state. |
| API | The agreed requests and responses the browser uses to communicate with Python. |
| Transaction | A unit of database work that either commits together or rolls back. |
| Advisory lock | A PostgreSQL coordination mechanism the application's writers agree to acquire before checking and saving. |
| CI | Automated checks run by GitHub Actions when code is pushed or a pull request changes. |
| Provenance | A record of where imported information came from and how it was interpreted. |
| Deployment | Publishing the application code and configuration so people can use it at a URL. The database stores the lasting booking data separately. |

## Update: personal audit and one schedule, 20 September 2026

Python exports detailed historical finding evidence so the browser can combine name, berth, date and type filters without rerunning or weakening the rules. A capacity finding keeps all occupants, even when a name search selects it. Closure dates are restricted to their actual overlap. Counts explicitly describe findings, and the original whole-workbook report remains separate. Optional browser storage remembers validated filter values; no account or shared preference record is required.

Schedule now has a Harbor / Grid / Side by side switch. The layouts share a selected ISO day and month. Changing months clamps the day to the target month, and date headers support keyboard selection. A finding can open both current views at its historical dates; the interface explains that later live edits may have changed what appears. The paired layout stacks on phones. Python tests reconcile exported findings to the audit, frontend tests cover combined and inclusive filters, and browser checks cover saved preferences and linked layouts.

## Suggested input throughout the website

The input-assistance module adds native suggestion menus beside all typed fields, including Audit and the edit dialogs. Registry lookups are debounced and discard late responses; errors are visible without disabling manual entry. Calendar shortcuts respect inclusive stays. Only a selected vessel’s own recorded length is suggested. Note/reason templates append to existing text and require their prompts to be completed. Choices dispatch the existing input/change events, preserving booking invalidation, measurement previews and server checks. Decision 0011 explains the native-control choice. Acceptance cases I01–I12 cover the behavior, with Node checks for name matching, inclusive dates, template preservation and measurement provenance.
