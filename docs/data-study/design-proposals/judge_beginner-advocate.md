# Judge: Beginner Advocate (mentor for first-year take-homes)

Question I am answering: can Baron, who as of today has no git, Python, Node or Homebrew on the Mac, finish THIS plan in about six of his own hours with Claude Code typing, understand it, and defend every decision in an interview?

Scoring lens: I score down anything Baron could not explain after doing it, anything whose phases have no exit criteria, and anything that hides a time sink (tool installs, environment debugging, data-cleaning rabbit holes). I score up plans that build understanding step by step and that keep a buffer and a protected rehearsal.

## Scores (1-10 each)

| Proposal | works_feasible | structure | assumptions | explainability | uniqueness | club_fit | total |
|---|---|---|---|---|---|---|---|
| Berthbook | 5 | 9 | 9 | 5 | 6 | 7 | 41 |
| Harbormaster | 5 | 7 | 9 | 5 | 10 | 7 | 43 |
| Berthline | 8 | 8 | 9 | 9 | 4 | 9 | 47 |
| Dock Ledger | 6 | 8 | 9 | 6 | 7 | 8 | 44 |

Recommended winner: **Berthline**, with grafts listed below. It is the only plan that a beginner can actually finish AND defend, because it is the only one with a mid-point "working system" milestone (3.0 h), an explicit 0.5 h buffer, a protected 1.0 h rehearsal, and no component Baron would have to say "Claude suggested it" about.

---

## Berthbook (domain-model purist) - 41

**One line:** The best-structured and most honest plan, but it is a senior engineer's six hours, not a first-year's.

**works_feasible 5.** Phases sum to exactly 6.0 h with zero buffer, and the scope is the largest of the four: ten test files, seven ADRs, a sweep-line audit plus a 500-case fuzz test, effective-dated berths with an as-of picker, invariants enforced in both Python and SQLite, an eleven-endpoint Flask API, a four-panel UI, a static Pages export, AND an importer that covers all three eras including fill-colour inference, a 60-value golden table, eight span tests and reconciliation, all in "Phase 3 (1.25 h)". That importer phase alone is what the other proposals budget 1.0-1.5 h for with fewer deliverables. "Phase 6 ... 0.5 h" covers export, a read-only copy of the web app, Pages setup and a README with the exact rule, assumptions and report summary. None of this fits.

**structure 9.** The one-way dependency graph (domain imports nothing; importer, storage, api import domain; web knows only JSON) is the clearest structural story in the set and is a genuinely good interview answer. Module layout is precise.

**assumptions_clarity 9.** Fourteen numbered assumptions, each tied to a rule branch or an issue code. The `clearance*(n-1)` note ("gaps are between boats, not at ends") is exactly the kind of detail a reviewer likes.

**explainability_for_baron 5.** This is where it falls down. Count what Baron must explain from memory: three-valued verdicts (fine), a sweep line over (start,+1)/(end+1,-1) points (hard), a fuzz test asserting sweep == brute force (Baron will be asked "so why have the sweep at all with 2,660 bookings?" and the honest answer is that brute force is under a second, i.e. the sweep is complexity for its own sake), effective-dated berths, canonical_key normalisation, SQLite CHECK constraints, 409-with-findings, provenance rows, reconciliation, tightest-fit ranking, plus seven ADRs "in his own words" at 0.4 h total (about 3.5 minutes each). Phase 1 asks him to read every field of three files, hand-verify 17 tests AND write two ADRs in 0.75 h. Phase 7 rehearsal is 0.75 h for nine unique features. A first-year cannot internalise this much in the time given.

Technical nit that becomes an interview trap: "range within berth effective window ... all as SQLite CHECK constraints" is not possible. SQLite CHECK constraints cannot reference another table (no subqueries), so that invariant needs a trigger or Python-only enforcement. If Baron repeats the "enforced twice" claim and an interviewer opens schema.sql, it will not be there.

**uniqueness 6.** Rigor a reviewer rarely sees from a student, yes; but Baron asked for "think big think wild", and this plan explicitly cuts animation first. The pier load strip is a good picture of the computation.

**club_fit 7.** Structure, assumptions and explanation are all exactly what the club asked for. "Whether it works" is at real risk because there is no buffer and the importer phase is under-budgeted.

**Hidden time sinks:** fill-colour span inference (0 h budgeted separately, buried in Phase 3); test_spans.py on hand-built openpyxl workbooks (each tiny workbook is 15+ lines of setup); the fuzz test will surface real disagreements between sweep and brute force that need debugging Baron cannot do.

---

## Harbormaster (showman) - 43

**One line:** The plan Baron wants, and the one most likely to leave him at hour six with a half-working SVG harbor and no rehearsal.

**works_feasible 5.** No buffer (phases sum to 6.0). "Phase 3 - The show (1.25 h)" is the single riskiest block in any proposal: a to-scale SVG map with `map_x, map_y, map_angle` per berth, hull paths, a packing function, CSS transform transitions, a range input over 8,401 days with play, a per-berth conflict strip, tests.html, AND a JS mirror of the rules with a live parity badge. SVG layout debugging is a classic beginner sink and here it is on the critical path to the demo. Phase 4 then writes `suggest` twice (Python and JS) plus a stdlib http.server with JSON POST handling in 0.75 h.

Concrete gotcha: STACK says `python3.12 -m pip install --user openpyxl` with no venv. Homebrew's Python 3.12 is marked externally managed (PEP 668) and refuses `pip install --user` with an "externally-managed-environment" error. Baron's very first install step will fail and he will not know why. Needs a venv like the other three proposals.

**structure 7.** Clean module list and a good static/live mode switch. But the rules exist twice (rules.py and rules.js), the UI has two data paths, and demo bookings live in localStorage in one mode and SQLite in the other. The parity badge is a clever answer to the obvious objection, but it is an answer to a problem the plan created.

**assumptions_clarity 9.** Eighteen numbered assumptions, each mapped to an issue kind or a constant; "keep the larger registry length because over-estimating is the safe error" is a good, defensible choice. Assumption 12 (do not read fills) is the right call and the only proposal to make it up front.

**explainability_for_baron 5.** In favour: the packing function IS the capacity rule drawn, which helps Baron explain the rule. Against: Baron must be able to explain SVG viewBox and coordinate units, CSS transforms and transitions, ES modules, localStorage, a `BaseHTTPRequestHandler` subclass with do_GET/do_POST and Content-Length parsing (more concepts than a Flask route, despite the install saving), why the rules are duplicated, and how the parity badge works. That is a lot of frontend for someone who has never run `python` before. The per-phase "explain-back with two follow-ups" is the best rehearsal mechanic in the set, but it is undercut by Phase 5 combining README, ASSUMPTIONS.md, audit panel wiring, a fresh-clone run AND the eight-question rehearsal in 1.0 h.

**uniqueness 10.** Nobody else lets the reviewer watch 23 years animate. This is Baron's own wish done properly, and interview point 7 ("isn't that just polish?") has a good answer.

**club_fit 7.** The club said polish is "welcome but not the point". The backend is real and the importer is honest, so this is not empty polish; but if Phase 3 overruns, what gets cut is exactly the parts the club grades (audit drawer, override, README time).

**Hidden time sinks:** SVG layout; two rule engines drifting during Phase 4; http.server JSON plumbing; Safari and Chrome checks; the `pip --user` failure.

---

## Berthline (pragmatic MVP) - 47

**One line:** Boring on purpose, finishable, and the only plan where Baron can explain every line; it needs one visual graft so it does not look like everyone else's submission.

**works_feasible 8.** The only proposal with a buffer (0.5 h), a mid-point milestone ("Milestone at 3.0 h: working system"), a protected 1.0 h rehearsal, "start Phase 0 the evening before", a 20-minute time box on fill detection with a stated fallback, and an ordered cut list whose first cut (Pages snapshot) does not touch the working system. Weak spot: Phase 3 "API and UI (0.5 h)" is thin for a month grid, a form and a findings panel even with Claude typing; expect 0.75 h and take it from the buffer. Phase 2 (db + classify + importer in 1.0 h) is tight but its fallback is explicit.

**structure 8.** app.py = routes only, rules.py imports only datetime and models, the browser never computes rules. Simple and correct. Loses a point for the Pages fallback being an afterthought and for no data-exploration step before coding.

**assumptions_clarity 9.** Fourteen numbered assumptions; the `span_source` ladder gives an honest error bar on pre-2009 statistics; conflicting registry lengths become NULL plus an issue (more conservative than "keep max", and easier to defend). Assumption 4 (same-day turnovers appear as overridable conflicts) is the kind of "here is what I chose to get wrong" that reviewers respect.

**explainability_for_baron 9.** Every component is one Baron can read top to bottom: 11 named rule tests, a 30-line capacity_check, Flask routes that are parse-call-return. Interview point 6 ("a sweep line would be O(n log n) and harder to read; with 2,600 bookings, readable wins, so the optimisation is written down, not implemented") is the best single answer in any proposal for a first-year to give. Phase 7 has Baron read rules.py and importer.py aloud and write the Decisions section himself.

**uniqueness 4.** This is the cost. A spreadsheet-look-alike grid plus an audit page is what a competent applicant submits. The load strip is a good start on "the diagram" but is deliberately the ceiling. And cutting the Pages snapshot first means a club reviewer skimming twenty repos sees nothing without installing.

**club_fit 9.** Works, structure, assumptions, explanation: all four boxes, with the lowest risk of the "works" box being empty.

**Hidden time sinks:** fewer than the others; the month grid rendering in vanilla JS is the main one, and the "day-1 column from formula cells" logic will need a fixture test that takes longer to write than the code.

---

## Dock Ledger (data archaeologist) - 44

**One line:** The best narrative ("your own schedule contains N over-capacity days") and the best data insights, dragged down by FastAPI and a starved rehearsal.

**works_feasible 6.** Importer gets the most honest estimate (1.5 h) and Phase 1 "Look at the data before coding (0.5 h)" is excellent practice. But the total is 6.0 with no buffer, and Phase 6 crams export_static, Pages setup, README with headline numbers, and rehearsal of the demo and eight answers "aloud once" into 0.75 h. Once is not rehearsal.

**structure 8.** rules.py is the only place rules live; audit.py and api.py call the same function, so "the app would have caught this" is literally true. Good issue-code vocabulary. The `exclusive=0` flag mentioned for Holiday/Road race does not exist in the listed reservations schema; small inconsistency an interviewer might poke.

**assumptions_clarity 9.** Fourteen assumptions, plus the sharpest data observation in any proposal: the 8YR summary's 648 for a 410' berth in 2012 exceeds 366, so the summary counts vessel-days, not occupied days. That single sentence will save whoever builds the reconciliation an hour of confusion and is a superb interview story. Also the only plan to name the 2010 Nov/Dec blocks' names-in-header-rows problem (HEADER_CORRUPTION / OUT_OF_GRID_CELL).

**explainability_for_baron 6.** FastAPI + uvicorn is the wrong call for this applicant: two extra installs against a brief that says "fewest installs", and Baron must be ready to explain pydantic request models, `async def`, uvicorn, and why rule violations return 422 (a validation-error code; 409 is the conventional answer and an interviewer may ask). The "/docs page" benefit is real but it is a benefit for the reviewer, not for Baron's understanding. Everything else (taxonomy, registry, reconcile, audit) is explainable, and Phase 1 builds understanding the right way.

**uniqueness 7.** "Prove the problem in their data before selling the fix" is a strong angle that a reviewer will remember; confidence-labelled spans yield a number nobody else has; the play-button timeline is a cheap version of Baron's wish.

**club_fit 8.** Strong on all four criteria; loses a point for the extra installs and the thin rehearsal.

**Hidden time sinks:** FastAPI/uvicorn install and first-run errors; Tours import "if time allows" (it never does); a parametrized taxonomy test over 573 values that must reach zero unclassified (any new value breaks the build).

---

## Best ideas to graft into Berthline

1. **Harbormaster: the booking form that refuses with a drawing.** A single SVG bar per berth: berth length as the bar, one segment per occupant, clearance gaps, the candidate segment, overflow spilling past the end in red, unknown-length vessels dashed. This is Berthline's load strip promoted into the form, costs about 0.5 h inside Berthline's Phase 5 budget, satisfies Baron's "boats and berths diagram" wish, and shows the reviewer the rule as a picture. Skip the harbor map, hull paths, angles and the 23-year play button.
2. **Harbormaster: un-cut the GitHub Pages snapshot and make it cheap.** Commit `docs/demo.json` (audit findings + one month of bookings per berth + issue counts), have index.html fall back to it when `/api` is absent, add a `?v=<stamp>` cache-buster. Move it from "cut first" to "cut third". A reviewer with twenty repos to read must see something without installing.
3. **Dock Ledger: Phase 1 "look at the data before coding".** Add a 30-line `dump` helper that prints one month block as text; Baron opens 1999, 2006, 2012 and the 2010 November block and points at the three header styles. 0.25-0.5 h taken from Berthline's buffer. This is how Baron learns to explain the importer instead of reciting it.
4. **Dock Ledger: vessel-days vs occupied-days in the 8YR reconciliation.** Report both; the 648 > 366 observation is the explanation. Prevents a debugging rabbit hole and gives Baron a memorable interview answer.
5. **Dock Ledger: headline numbers at the top of the README** ("your own 1997-2019 schedule contains N over-capacity days, M does-not-fit assignments, 2 mislabelled headers, K inferred spans, J unknown lengths"). Zero extra code; it is the audit output rephrased.
6. **Dock Ledger: HEADER_CORRUPTION / OUT_OF_GRID_CELL issue kinds** for values found outside day columns (the 2010 Nov/Dec blocks). Berthline's importer "never raises"; give it a name for this case so it is a report row, not a mystery.
7. **Berthbook: the three-valued verdict vocabulary.** Berthline already has error/warning; name the codes (DOES_NOT_FIT, CAPACITY_EXCEEDED, LENGTH_UNKNOWN...) and adopt Berthbook's phrasing "UNKNOWN is never OK" for interview point 3.
8. **Berthbook: era order that banks value early** (2014-2019 first, then 2009-2013 merged cells, then pre-2009) so if Phase 2 overruns the clean years are already in.
9. **Harbormaster: explain-back with two follow-ups at the end of every phase**, and the risk-list rule "anything Baron cannot explain after two tries is cut". Berthline has "Explain:" items; add the follow-up drill.
10. **Harbormaster: the "synthetic data may contain zero conflicts" fallback** (README "try it" links to the form that create one). Berthline should plan for this too.

## Fatal flaws

- **Berthbook:** zero buffer with the largest scope of the four; the sweep line + fuzz test is complexity a first-year cannot justify when brute force is under a second; "range within berth effective window" cannot be an SQLite CHECK constraint (no subqueries), so the "invariants enforced twice" claim is partly false and is an interview trap; seven ADRs in 0.4 h is not writing, it is signing.
- **Harbormaster:** `python3.12 -m pip install --user openpyxl` fails on Homebrew Python 3.12 (PEP 668 externally-managed-environment); the plan's very first command does not work without a venv. Two rule engines plus an SVG harbor on the critical path with no buffer means the demo is the first casualty of any overrun, and the demo is the whole pitch.
- **Dock Ledger:** FastAPI + uvicorn contradict the "fewest installs, beginner can read" brief and add concepts (pydantic, async, 422) Baron cannot yet explain; rehearsal "aloud once" inside a 0.75 h phase shared with README and Pages is not a rehearsal.
- **Berthline:** no fatal flaw; two weaknesses to fix by grafting: Pages snapshot cut first (reviewer sees nothing without installing) and no visual beyond the load strip (Baron's stated wish unmet).

## Time reality check

**Phase 0 is under-budgeted everywhere.** On a Mac with no developer tooling, installing Homebrew first pulls the Xcode Command Line Tools (a multi-GB download, commonly 15-40 minutes on its own), then Homebrew itself, then python@3.12 and gh, then `gh auth login` through a browser, then a venv and pip. Every proposal budgets 0.5-0.75 h; real elapsed time is 0.75-1.5 h, most of it waiting. Only Berthline says "start Phase 0 the evening before"; do that, and treat it as outside the six hours.

**The importer is the second sink.** All four budget 1.0-1.5 h for three layout eras plus registry plus classification plus cross-month joins plus reconciliation. Fill-colour span inference should be cut up front in every plan (Harbormaster already does); repeated-name runs carry the same information and are explainable. With fill cut and the era order from Berthbook, 1.0-1.25 h of Baron-time is credible.

**Which plans fit six Baron-hours as written:**
- Berthline: yes, and with 0.5 h buffer. Expect Phase 3 to take 0.75 h instead of 0.5; the buffer absorbs it. Adding grafts 1-3 above costs roughly 0.75 h, which means cutting the buffer to zero and trimming Phase 6 (Issues tab filters) or taking the 23-year data-exploration step to 0.25 h. Realistic total with grafts: 6.0-6.5 h.
- Dock Ledger: fits only if FastAPI is swapped for Flask (saves an install and a phase of confusion), Tours and fill inference are cut, and the play button is dropped; then rehearsal can grow to 1.0 h.
- Berthbook: does not fit. To fit, cut the sweep line and fuzz test (brute force per day), effective-dated berths (a `first_year/last_year` pair is enough), the dual-invariant test, four of seven ADRs, fill inference and the 60-value golden table (use 20). Even then it is 6.0 with no buffer.
- Harbormaster: does not fit. To fit, drop the harbor map (keep one bar per berth), drop the 8,401-day play (keep a month picker), drop the JS `suggest`, fix the venv, and accept that live mode is a stretch goal. At that point it has become Berthline plus a berth bar, which is the recommendation above.

**What must be true at hour three:** a fresh clone runs `pip install -r requirements.txt`, the importer, `pytest -q` and `python app.py`, and the four demo clicks work. Berthline is the only proposal that names this checkpoint. Everything after hour three is optional and should be judged by one test: can Baron explain it to Claude with two follow-ups? If not, it goes in README "Next steps".
