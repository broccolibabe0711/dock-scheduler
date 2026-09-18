# 6. The GitHub Pages demo is a snapshot; the rules never run in JavaScript

**Context.** A reviewer should see the project work without installing anything, but Pages cannot run Python and the rules must have one source of truth (decision 0004).

**Decision.** `python -m dock.export` writes JSON files (berths, vessels, reservations, annotations, issues, the audit, and per-day conflict flags). The same front end runs in two modes: against the API when it is there, otherwise against the snapshot. In snapshot mode the booking form is disabled with a note; the grid, harbor view, audit and issues work fully, and the conflict flags they show were computed by the Python audit at export time.

**Consequences.** Nothing on the demo can disagree with the local app. The only arithmetic in the browser is for drawing (positions, feet used). A live "try to refuse a booking" demo would need the Python rules in the browser (Pyodide) and is a stretch goal, not a fake.
