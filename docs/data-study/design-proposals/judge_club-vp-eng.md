# Judge: Club VP of Engineering — Dock Scheduling take-home, four proposals

Reviewer persona: VP Eng at Columbia Software Solutions, reading twenty submissions this week. I will clone the repo, run the commands in the README, run the tests, click the demo, and then ask the applicant eight questions for fifteen minutes. I do not reward code the applicant cannot explain, I do not reward a demo whose backend is a facade, and I score "unique" only when the unusual thing also shows engineering judgment.

Constraints I hold every proposal to: Baron has ~6 hours of his own attention, no dev tooling installed today, and must be able to explain every decision. Claude types; Baron's hours are reading, running, verifying and rehearsing.

---

## Scorecard (1-10 per criterion, total out of 60)

| Proposal | Works / feasible | Structure | Assumptions | Explainability | Uniqueness | Club fit | Total |
|---|---|---|---|---|---|---|---|
| Berthbook | 5 | 9 | 9 | 5 | 7 | 7 | **42** |
| Harbormaster | 4 | 6 | 8 | 4 | 9 | 5 | **36** |
| Berthline | 9 | 8 | 9 | 9 | 5 | 9 | **49** |
| Dock Ledger | 6 | 8 | 9 | 6 | 8 | 8 | **45** |

Recommended winner: **Berthline**, with grafts from Dock Ledger (audit-first framing, look-at-the-data phase, hand-verified findings) and one visual from Berthbook/Harbormaster (proportional pier-load bar driven by the API).

---

## Berthbook — 42/60

One-line verdict: the best domain model of the four and the least honest schedule; it would score highest if it shipped, and it will not ship in six Baron-hours.

**Works / feasible: 5.** Count what Phase 4 promises in 0.5 h: twelve endpoints plus eight API tests. Phase 5 promises four UI panels plus an SVG load strip in 0.75 h. Phase 6 promises the static export, a Pages copy of the web app, and the README in 0.5 h. Phase 3 promises the registry, three layout eras, fill-colour inference, cross-month joins, the reconciliation table, and four test files in 1.25 h. Those numbers are Claude-typing-time, not Baron-understanding-time. The proposal also builds things the data does not need: an O(n log n) sweep line plus a 500-case fuzz test to prove it equals brute force, when Berthline correctly notes brute force on 2,660 bookings is ~15,000 day checks and runs in under a second. Effective-dated berths with `parent_id` child slips, a `rafted` flag with its own capacity semantics, per-berth `clearance_ft`, and invariants enforced twice (Python and SQLite CHECK, with a test proving they agree) are each defensible in a product; together, in six hours, they are scope creep dressed as rigor.

**Structure: 9.** The one-way dependency graph (domain imports nothing; importer, storage, api import domain; web sees JSON) is exactly what I would hand to a client team. `Note` as a separate table so "Fuel truck" is not an occupancy, `ImportIssue` as an honesty ledger, and `override_reason` non-null only on a knowing save are all right.

**Assumptions clarity: 9.** Fourteen numbered assumptions, each traceable to a rule or an issue code. The `clearance*(n-1)` justification ("gaps are between boats, not at ends") is the kind of one-liner a reviewer remembers.

**Explainability for Baron: 5.** The interview points are excellent prose, but they are Claude's prose. Baron would have to explain a sweep line, a seeded fuzz equivalence test, SQLite CHECK constraints mirroring `__post_init__`, effective-dating, and seven ADRs he "wrote in his own words" in a total of 0.4 h. A beginner who typed none of it and read it once will not survive "walk me through how find_conflicts decides where the active set changes."

**Uniqueness: 7.** Three-valued verdicts (OK/CONFLICT/UNKNOWN) and reconciling against the 8YR summary demonstrate real judgment. The fuzz test is clever but is the kind of uniqueness that shows off rather than shows skill relevant to the client.

**Club fit: 7.** Matches "how you structured it" and "assumptions" superbly; fails "does it work" if it is half-built at hour six, and the club will notice an unfinished importer with "unfinished sheets listed as not imported."

Factual concern: interview point 3 says "about half the grid vessels have no registry length." Berthline's data read says roughly 19 of 504 grid vessels have a known length. If Berthline is right, almost every historical linear-berth day is UNKNOWN and the 23-year "conflict audit" headline is mostly amber. Whoever writes the final plan should count this first, before promising audit numbers in a README.

---

## Harbormaster — 36/60

One-line verdict: the demo I would most enjoy for ninety seconds and the plan I would least trust to be finished, because it implements the rules twice and budgets two hours for five JavaScript modules plus animation.

**Works / feasible: 4.** Phase 3 (1.25 h): data.js, rules.js (a line-for-line port of rules.py), harbor.js with `packBerth()` and CSS-transition sliding, timeline.js with an 8,401-day scrubber and play, tests.html, and a parity badge that recomputes every conflict on load. Phase 4 (0.75 h): booking.js with a live berth bar, suggestions in two languages, and a hand-rolled `http.server` API with five routes and static file serving. That is not 2.0 Baron-hours of reading and verifying; it is not 2.0 hours of Claude typing either once debugging starts in two browsers. The `map_x, map_y, map_angle` berth coordinates are a whole small design task nobody budgeted.

**Structure: 6.** The package layout is clean and the golden `rule_cases.json` shared by both languages is a genuinely good idea. But the core structural decision — two implementations of the rule — is a self-inflicted maintenance liability, and the parity badge is a bandage on a wound the author chose to make. The stdlib `http.server` route table is more code for Baron to read than a Flask app, not less; "zero installs" saved one `pip install` and cost ~120 lines of request parsing.

**Assumptions clarity: 8.** Eighteen assumptions, well phrased; the `untracked` capacity mode for group rows is the most honest handling of "North Finger Piers:" in the set. "Keep the larger registry length because over-estimating is the safe error" is a good, explainable call.

**Explainability for Baron: 4.** Baron would need to explain SVG coordinate systems, CSS transform transitions, ES modules, `packBerth()` offsets, why JS and Python agree, `localStorage` demo bookings, and a hand-written HTTP server. The plan's own mitigation ("anything Baron cannot explain after two tries is cut") is an admission that much of Phase 3 is at risk of being cut after it was built.

**Uniqueness: 9.** The to-scale harbor with overhang drawn in red is the best single realisation of Baron's own idea, and the parity badge is a memorable answer to a hard question.

**Club fit: 5.** The club wrote "polish and visual design are welcome but not the point." Harbormaster makes them the point. The static demo's writes go to `localStorage`; the header is honest about the mode, so it is not a hidden fake backend, but a reviewer clicking Submit on Pages is still interacting with a JS-only path that the Python backend never sees.

---

## Berthline — 49/60

One-line verdict: boring in the way I want a client deliverable to be boring; the only plan with a working system at hour three, a buffer, and a rehearsal hour that nobody can steal.

**Works / feasible: 9.** Phases 0-4 deliver models, rules, importer, API, UI and a README in 3.0 h with a fresh-clone check as the exit criterion. Then one extra (audit page + load strip, 1.0 h), the issues tab and cross-check (0.5 h), a full rehearsal hour, and a 0.5 h buffer explicitly reserved for Homebrew slowness or a fill-colour surprise. The fill inference is time-boxed to 20 minutes with a stated fallback (`single + span_ambiguous`). The "sweep line is documented, not implemented" call is exactly the judgment I look for. Only soft spot: Phase 3 at 0.5 h for app.py plus grid, form and findings panel is tight; if it slips, the buffer absorbs it.

**Structure: 8.** `dock/rules.py` imports only `datetime` and `models`; `app.py` routes are parse-call-return; the browser never computes rules, so the form and audit cannot disagree. Per-berth `capacity_mode` column so staff can flip a float without a code change. I would only ask for `Finding` to carry a per-day load so the UI can draw something (see grafts).

**Assumptions clarity: 9.** Fourteen assumptions, each mapped to an issue kind or a constant. Says up front that only ~19 of 504 grid vessels have a known length. Explains why unknown length is neither zero nor full-berth (interview point 3) — that is the best single paragraph in the whole set. Assumption 9 (edit-distance-2 names are distinct) is oddly specific for something the system does not do; drop or rephrase.

**Explainability for Baron: 9.** Every phase has a must-explain list; Baron breaks the clearance constant to watch a test fail; Baron writes the Decisions section; Phase 7 is a protected hour with a fresh-clone run and timed answers. `rules.py` at ~30 lines for `capacity_check` with six tests is something a beginner can hold in his head.

**Uniqueness: 5.** The historical audit with source cells is good but Dock Ledger does the same thing with more conviction. The load strip is the minimum honest diagram. Baron asked for "think big"; this plan says no, politely.

**Club fit: 9.** Matches all four things the club listed, in the club's own priority order.

---

## Dock Ledger — 45/60

One-line verdict: the strongest story ("your own schedule contains N over-capacity days, computed by the same rules that guard the form") and the sharpest data observations, held back by FastAPI and a rehearsal squeezed into the last 45 minutes.

**Works / feasible: 6.** The importer gets the most realistic budget of the four (1.5 h) and is built in the right order with fill inference last and cut first. But FastAPI + uvicorn adds two installs and three concepts (pydantic models, ASGI, async) for a `/docs` page the club will not grade. Phase 5 (1.0 h) has to deliver the API, three tabs, an SVG timeline with play, and a live-checking form. Phase 6 (0.75 h) has to do the static export, Pages, README and the entire rehearsal ("aloud once"). Six phases sum to 6.0 h with no buffer, and the rehearsal is the thing that gets eaten.

**Structure: 8.** `rules.py` is pure and called by both `audit.py` and `api.py`; imported history is read-only so the audit is reproducible; `annotations` separate from `reservations`; `audit_findings` regenerated, never hand-edited. Good. FastAPI is the one structural choice I would reverse for this applicant.

**Assumptions clarity: 9.** Fourteen assumptions plus fourteen issue codes. Two observations here are the best in the set: (a) the 8YR summary's 648 for North Pier West in 2012 exceeds 366, so the summary counts vessel-days, not occupied days — reconcile both definitions; (b) the 2010 Nov/Dec blocks have names inside header rows and left of day 1, so record `HEADER_CORRUPTION` / `OUT_OF_GRID_CELL` rather than guess. "Holiday and Road race do not consume capacity" is a nuance nobody else caught. Assumption 3 ("75' or less, or unknown, is single; longer is linear") is a clean, explainable rule.

**Explainability for Baron: 6.** Phase 1 "look at the data before coding" (0.5 h, `python -m dockledger.dump 2010`) is the single best explainability investment in any proposal — Baron will have seen the three eras with his own eyes. Phase 4's "verify three findings by hand in Excel and cite the cell refs in the README" is how a reviewer becomes convinced it works. Against that: pydantic/FastAPI, and a rehearsal that is one pass in a shared 0.75 h.

**Uniqueness: 8.** Audit-first framing, confidence-labelled spans yielding a number ("38% of pre-2009 stays are inferred"), the vessel-days vs occupied-days reconciliation. This is uniqueness that demonstrates skill.

**Club fit: 8.** "Does it work" is answered on the client's own data with hand-verified citations; assumptions are exhaustive; structure is sound. Loses a point for FastAPI and the thin rehearsal.

---

## Fatal flaws

1. **Harbormaster: two implementations of the rules.** A beginner cannot defend maintaining `rules.py` and `rules.js` in lockstep, and the parity badge is a permanent integration test of a problem the plan created. Combined with 2.0 h for the entire frontend (map, timeline, animation, form, tests.html, server), the plan does not fit the budget. Not recoverable without becoming Berthline plus a picture.
2. **Berthbook: scope.** Twelve endpoints, ten test files, seven ADRs, sweep line plus fuzz, effective-dated berths with parent slips, rafting semantics, per-berth clearance, invariants twice — in phase budgets of 0.5-1.25 h each. At hour six this is a beautiful domain package with an unfinished importer and an unrehearsed applicant.
3. **Dock Ledger: no buffer and a squeezed rehearsal.** Not fatal, fixable by swapping FastAPI for Flask (saves an install and a concept) and moving 0.5 h from Phase 5/6 features into rehearsal.
4. **Shared across all four: the audit headline may be mostly "unverified".** If only ~19 of 504 grid vessels have a registry length (Berthline's figure), then "N over-capacity days across 23 years" may be N = 0 or a handful, and every plan's demo script promises a red finding on a specific berth. Count before promising. Dock Ledger's fallback headline ("0 provable double-bookings, but X% of stays are inferred and N vessels have unknown length, so the grid cannot prove it") is the right framing.
5. **Shared: the proposals disagree on berth modes** (South Floats 90' are linear in Berthbook and Dock Ledger, single in Harbormaster and Berthline). Any choice is fine because all four make mode a per-berth column; the final plan should state the rule (Dock Ledger's "<= 75' or unknown -> single" is the cleanest) and move on.

---

## Best ideas to graft into the winner (Berthline spine)

- **Phase 1 "look at the data before coding" with a `dump` helper** (Dock Ledger, Phases): 0.5 h where Baron sees 1999, 2006, 2012 and the 2010 November block on screen. Take it from Berthline's buffer plus Phase 7; it repays itself in every interview answer about the importer.
- **Hand-verify three audit findings in Excel and cite the cell refs in the README** (Dock Ledger, Phase 4 / Testing): the single cheapest way to answer "did it work?".
- **Audit-first README headline** (Dock Ledger, Pitch): lead with counts computed from the client's own history "by the same rules that guard the booking form", with Dock Ledger's honest fallback wording if over-capacity count is zero.
- **Reconcile both vessel-days and occupied-days against the 8YR summary** (Dock Ledger, Importer step 9): the 648 > 366 observation shows the summary counts vessel-days; print both, explain nothing away.
- **`HEADER_CORRUPTION` / `OUT_OF_GRID_CELL` issue codes for the 2010 Nov/Dec blocks** (Dock Ledger, Importer step 7): report, do not guess.
- **"Holiday" and "Road race - access limited" as non-capacity events** (Dock Ledger, Assumption 7): a nuance a real dockmaster would ask about.
- **Known overflow beats unknown** (Berthbook, Algorithms step 4; Harbormaster, check_day): if the known lengths already exceed the berth, it is an error even with unknown-length vessels present. Berthline's `capacity_check` already does this implicitly; make it an explicit named test.
- **Proportional pier-load bar in the booking form, drawn from `load_by_day` returned by `POST /api/check`** (Harbormaster, Unique feature 4; Berthbook, Unique feature 5): boats as rectangles at one foot per unit, overflow spilling past the berth end in red, unknown-length hatched. This is Baron's diagram, computed by Python, rendered by ~40 lines of vanilla JS. No JS rules, no animation library. Replaces Berthline's shaded-cell load strip.
- **Reason codes on findings** (Berthbook, Verdict/Finding): `DOES_NOT_FIT`, `CAPACITY_EXCEEDED`, `LENGTH_UNKNOWN`, `BERTH_CLOSED`, `EVENT_EXCLUSIVE`, `DOUBLE_BOOKED` — Berthline has these in spirit; make the code a field so the audit can de-duplicate and count by code.
- **`untracked` / `unchecked` capacity mode is already in Berthline**; keep Harbormaster's phrasing "recorded and drawn, no verdict, logged as a limitation".
- **Read-only Pages export of the Audit tab from precomputed JSON, no JS rules** (Dock Ledger, `export_static.py`; Berthbook, `docs/demo/`): do it last, 0.25 h, only if the fresh-clone milestone is green. Berthline cuts this first; I would cut the fill-colour inference first and keep the Pages audit page, because twenty reviewers will click a link before they clone.
- **"Break the clearance constant and watch which test fails"** (Berthline Phase 1; Harbormaster Phase 1): keep, it is the best five-minute rehearsal exercise.
- **`?v=<build stamp>` on the exported JSON** (Harbormaster, Risks): trivial, saves a stale-Pages embarrassment.

Do not graft: the JS rules mirror and parity badge (Harbormaster); the sweep line and fuzz test (Berthbook); effective-dated berths with `parent_id` (Berthbook); rafting arithmetic (Berthbook); FastAPI (Dock Ledger); the 23-year play scrubber (Harbormaster) — a per-berth month view with a day stepper (Dock Ledger feature 4) is enough.

---

## Recommended winner and rationale

**Berthline.** It is the only proposal whose schedule I believe: a working, cloneable, tested system at 3.0 h, a single extra feature the client would value (the historical audit), a protected rehearsal hour, and a buffer. Its rule is thirty lines Baron can write on a whiteboard; its assumptions are numbered and each maps to a constant or an issue kind; its structure (pure rules module, thin Flask, browser renders findings only) is what I would hand a client team. Its weakness — modest uniqueness — is exactly the weakness that is cheap to fix by grafting Dock Ledger's audit-first framing and hand-verified findings, plus one proportional load bar drawn from API output. Dock Ledger is a close second and would win with Flask instead of FastAPI and a real rehearsal hour; the final plan should feel like Berthline's schedule telling Dock Ledger's story. Berthbook is the model I would want in production and the plan I would not let a beginner attempt in six hours. Harbormaster is the demo I would remember and the codebase I would not want to inherit.

---

## Time reality check

- **Berthline fits as written.** Its 3.0 h milestone, 1.0 h rehearsal and 0.5 h buffer are the only credible time accounting in the set. Adding the Dock Ledger grafts costs ~0.75 h (data-look phase 0.5 h, hand verification 0.25 h): take 0.25 h from the buffer, cut the 20-minute fill-colour time-box entirely (pre-2009 stays are `repeat` or `single + span_ambiguous`), and reduce the Issues tab to counts-by-kind plus a table. The load bar replaces, not adds to, the load strip.
- **Dock Ledger fits only with cuts:** swap FastAPI/uvicorn for Flask (saves ~0.25 h of install and explanation), drop fill inference and the Tours sheet (already cut-first), drop the play button, and move 0.5 h from Phase 5 into a standalone rehearsal phase. Then it is roughly Berthline with a different README.
- **Berthbook needs roughly 9-10 Baron-hours as written.** To fit six: drop the sweep line and fuzz test (brute force per day), drop effective-dated berths and `parent_id` (group rows become `unchecked`), drop `rafted` and per-berth clearance (one constant), cut endpoints from twelve to six, cut ADRs from seven to three, and make the UI two panels. What remains is Berthline with better verdict naming.
- **Harbormaster needs roughly 10-12 Baron-hours as written**, and more if Safari and Chrome disagree about SVG transitions. To fit six: delete `rules.js`, the parity badge, `tests.html`, the 23-year scrubber and `map_*` coordinates; make the static page read-only; keep the booking form's overflow bar driven by the Python API; replace `http.server` with Flask. What remains is Berthline with a nicer bar.
- **For every plan:** Phase 0 (Homebrew, Python, gh) should start the evening before and run while Baron reads the workbook, because a slow Homebrew install is the most likely way to lose the first hour.
