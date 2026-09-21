# Dock Scheduler: acceptance tests and interview questions

Prepared for Baron Zhang · 19 September 2026

**Release standard:** no known silent data loss, no unexplained booking decision, passing critical scenarios, and clear recovery from mistakes. Automated checks support this standard; independent users still need to try the interface. Keep actual results separate from this test plan.

[Open the live app](https://dock-scheduler-henna.vercel.app/) · [Read the website guide](https://dock-scheduler-henna.vercel.app/guide.html)

## 1. What can distinguish this submission

The strongest story is the connection between messy evidence, explainable rules and a usable decision. I cannot know what other applicants will submit. These are recommendations based on this application's strengths, not claims of uniqueness.

| Capability | Why it is worth showing | Status and next step |
|---|---|---|
| Measurement impact preview | Changing a boat from 30 ft to 120 ft shows exactly which bookings and neighbours are affected. The coordinator reviews the outcome, records a reason and can reschedule the boat. | **Implemented in this update.** Show the before/after verdict, the preserved review and a successful move to a larger berth. |
| Visual explanation tied to evidence | A hull overhang is backed by the same 120 − 75 = 45 ft calculation as the API, while source references explain where historical spans came from. | **Implemented.** Pair Harbor's Fit example with the booking check and the imported record's provenance. |
| Closure impact planner | Select a berth and proposed closure; see displaced bookings and suitable alternatives together before committing a plan. | **Best next feature.** Extend existing closure checks and suggestions into a read-only planning screen. Test that trying several plans changes no live booking. |
| Data-confidence inbox | Prioritize missing lengths that affect upcoming bookings, show their sources and route corrections through the measurement review. | **Second choice.** Use explicit categories such as measured, missing and conflicting. Avoid an invented numerical confidence score. |
| Daily operations brief | A printable date-based list of arrivals, departures, closures, notes and unresolved findings is useful during a handover. | **Small practical addition.** Export from current data with a generated-at time; check that the brief matches the ledger and marks unknowns. |

Keep the next release focused. A complete closure-planning workflow would demonstrate more than several unfinished tabs. For real operations, accounts, permissions, an attributed edit log and validated depth/rafting rules are prerequisites, rather than presentation extras.

## 2. Set up a fair test

Use a fresh local database for the full test plan. Use the public site for read-only checks and a small, clearly labelled booking smoke test. Prefix manual test records with `QA —` and cancel them afterward. Do not change the measurements of historical sample vessels in production just to test a failure. The live demo is shared, so counts and future availability can change.

For every case record: **case ID, date, deployment/version, browser/device, expected outcome, observed outcome, pass/fail, and evidence**. Screenshots or the returned reservation ID are enough for most cases. A failure needs reproduction steps and severity: blocked core task, misleading outcome, or minor presentation issue.

Local setup and regression tests, from the repository:

```bash
.venv/bin/python -m pytest -q
DOCK_DB=acceptance.db .venv/bin/python -m uvicorn dock.api:app
```

Open `http://127.0.0.1:8000`. Set `TEST_DATABASE_URL` only to a disposable PostgreSQL database when running the database suite; its fixtures replace that database's contents.

Read-only deployment check:

```bash
.venv/bin/python scripts/verify_deployment.py --base-url https://dock-scheduler-henna.vercel.app
```

Optional live write check adds one clearly labelled event, verifies it, and cancels it:

```bash
.venv/bin/python scripts/verify_deployment.py --base-url https://dock-scheduler-henna.vercel.app --write-smoke
```

## 3. Ten-minute smoke test

| ID | Do this | Passing result |
|---|---|---|
| S01 | Open the root URL in a fresh tab. Then open a link ending in `#grid`. | Root opens Schedule in Harbor mode; the explicit Grid link opens Grid mode. The badge says Live · bookings saved. |
| S02 | Press Fit example · 2010. Inspect R/V Clear Tern on 29 July 2010. | A 120 ft vessel exceeds the 75 ft North Pier Face by 45 ft; the drawing and written finding agree. |
| S03 | Press Sample history. | The date is 12 July 2017; Utility work and OSV Amber Reef overlap on South Float East, with a visible problem. |
| S04 | Search the registry for Clear Tern and open the source workbook link. | The intended vessel and dimensions are readable, the source opens, and clearing the search restores the list. |
| S05 | In a fresh local ledger, check R/V Clear Tern on North Pier Face for 1–2 July 2032. | CONFLICT explains the 45 ft mismatch; nothing is saved. |
| S06 | Ask for suggestions on those dates. | North Pier East (240 ft) precedes North Pier West (410 ft) when both are available. Any UNKNOWN alternatives are labelled. |
| S07 | Book a QA event on a free local berth-day. Reload the page. | It has a reservation ID, remains visible and occupies the whole berth. |
| S08 | Try a second event at the same place and date without an override. | It is refused, the reason is readable, and there is only one saved event. |
| S09 | Open the first event, edit its dates/notes, save, then cancel it. | The edit survives reload; cancellation is visible in Grid and frees the berth. The record is retained. |
| S10 | Open Audit, Issues, Rules & assumptions and How it works. | Audit is explicitly historical; Issues has source locations; the guide explains rules and limitations. Links work. |

## 4. Rules and failure cases

These cases use controlled local records so historical occupancy cannot obscure the result. Create vessels with the specified lengths through Book, using a free future period. For an unknown vessel, choose an existing registry entry marked Unknown or add one through `/docs` without a length.

| ID | Scenario | Passing result |
|---|---|---|
| R01 | On a 410 ft face, book 274 ft and 100 ft vessels together; then try adding 60 ft. | Two use 394 ft and fit. Three use 464 ft and are refused by 54 ft. |
| R02 | Put a single 75 ft vessel on the 75 ft face. | It fits. The shared clearance allowance is not added to a lone vessel. |
| R03 | An event ends on the 5th; another begins on the 5th, then try the 6th. | Same-day overlap is refused; the 6th is available when otherwise empty. |
| R04 | Use an unknown-length vessel or an unknown-length berth. | UNKNOWN is distinct from OK; Save requires a measurement or a reason. |
| R05 | Try a closure across existing vessel use and a vessel during a closure. | Both directions expose the conflict. Two closures may overlap by the stated assumption. |
| R06 | Enter reversed dates, missing required fields, zero or negative length. | A useful validation message appears; no invalid booking is created. |
| R07 | Save a refused booking with a reason, then move it into another conflict without a new reason. | First override is preserved; the later edit is refused until a fresh reason is supplied. |
| R08 | Edit only notes on an imported unknown-length stay. | Notes save. Adding context does not require inventing a length. |
| R09 | Double-click Save while a request is pending. | The control prevents a second in-flight save; one request creates one booking. |
| R10 | Two sessions simultaneously attempt whole-berth events for the same free day. | Exactly one is accepted without an override. The other gets a conflict, not a silent duplicate. Automated tests cover this on both databases. |
| R11 | Try Check, Suggest and measurement Preview repeatedly, then reload. | These actions create no reservations, vessels or measurement changes. |
| R12 | Disconnect during a read, or stop the local server. | An error or explicit read-only state appears. No failed write is presented as saved. If a response is lost after Save, inspect the ledger before retrying. |

## 5. Measurement correction and recovery

Create **QA — Measurement**, length 30 ft, and book it on North Pier Face for 1–2 January 2033 in the local ledger.

| ID | Do this | Passing result |
|---|---|---|
| M01 | In the registry, review a proposed length of 120 ft. | Preview shows the existing reservation changing from OK to CONFLICT, with 45 ft overhang. Nothing changes in storage yet. |
| M02 | Try saving without a reason. | The form asks for a reason; the API also refuses a missing/blank reason. |
| M03 | Explain the correction and planned reschedule, then save. | The new length and review record save together. The affected booking remains visibly flagged. |
| M04 | Reload and inspect the measurement history and reservation details. | Old/new lengths, the review reason and the affected booking are still available. |
| M05 | Move the booking to North Pier East using Edit reservation. | Check returns OK, Save succeeds and Harbor shows the updated location. |
| M06 | Preview clearing the length to unknown. | The impact becomes UNKNOWN; it requires review before saving. |
| M07 | Preview a blocking change in one tab; change an affected reservation's dates in another; return and save the old preview with a reason. | The old acknowledgement is refused and current findings are shown. Review again before saving. |
| M08 | Cancel the test stay and repeat a length correction. | The cancelled stay does not count as occupied or block the correction. |

The automated suite also tests neighbouring boats, failure to record the review, concurrent first starts and upgrading the schema without losing existing reservations.

## 6. Usability tasks for another person

Ask someone who has not seen the project to try these tasks. Let them describe what they are thinking. Give the goal without naming the button to press; record where they hesitate and whether they finish without help. This follows established guidance to use realistic tasks without giving away the interface route. [Nielsen Norman Group: task scenarios](https://www.nngroup.com/articles/task-scenarios-usability-testing/)

1. “A 120 ft research vessel needs a berth next week. Find a suitable place and tell me why it fits.”
2. “A scheduled boat has been measured again and is much longer than recorded. Find out what changes before you commit the correction.”
3. “A community event is moving by one day. Update the reservation and verify the result.”
4. “You are taking over the waterfront on a historical day. Find any closures and operational notes you should know about.”
5. “This record was imported from a spreadsheet. How certain are you about its dates and length? Show the evidence.”
6. “Undo the occupation of the berth for a cancelled visit, while keeping evidence that the visit existed.”

Use these as **your proposed targets**, not industry benchmarks: a new tester identifies the app's purpose within 20 seconds, completes a routine booking within two minutes without coaching, and can distinguish OK, CONFLICT and UNKNOWN in their own words. For each task record completion, assistance, time and the tester's explanation. One confused tester is actionable evidence; a small informal test is not a statistical claim about all users.

## 7. Accessibility and presentation checks

| ID | Check | Passing result |
|---|---|---|
| U01 | Use only Tab, Shift+Tab, arrow keys, Enter and Escape. | Every action is reachable; focus is visible; dialogs close with Escape and return focus sensibly. Grid day cells use arrow navigation rather than hundreds of Tab stops. |
| U02 | Check the form and both dialogs at a 390 px phone width and 200% zoom. | Labels, errors and primary actions remain readable and reachable. Horizontal scrolling is confined to the dense grid/map/table, not the entire page. |
| U03 | View a fit problem without relying on color. | Text and numbers explain it; color is supplementary. Unknowns have labels and dashed styling. |
| U04 | Turn on reduced motion; try Play. | The stop control remains clear, and animated transitions/pulsing respect the preference. |
| U05 | Use a screen reader to inspect a date, a reservation bar and a form error. | Names and status are meaningful; error text is announced or easy to locate. |
| U06 | Search quickly, switch dates while loading, and navigate between tabs. | An older response does not overwrite the newer selection. Failure leaves a useful message. |
| U07 | Repeat core tasks in Chrome, Safari and Firefox. | Date inputs, dialogs, layout, saving and cancellation work in each tested browser. Record the versions actually tested. |
| U08 | Open the GitHub Pages snapshot and compare a sample date. | It is visibly read-only, uses the same historical flags, displays annotations and links to the live app for booking. |

Keyboard access, focus, reflow, contrast and understandable input errors are grounded in the [W3C WCAG quick reference](https://www.w3.org/WAI/WCAG22/quickref/). These checks are a practical review, not a claim of complete WCAG conformance.

## 8. Questions you should be able to answer

1. Can I trace one booking from the browser, through request validation and the rules, to the committed row?
2. Why can two vessels on one berth be legitimate? Can I calculate 394 ft and 464 ft without looking at the code?
3. Why does a 75 ft vessel fit alone on a 75 ft face, while shared occupancy includes clearance?
4. What is the difference between a fit failure, a capacity failure and UNKNOWN?
5. Why do arrival and departure dates overlap on the same day? What would change if the facility needed hours?
6. What did the importer infer, correct or skip? Can I show a source cell and explain the choice?
7. Why does “zero detected overloads” not prove the original schedule was valid?
8. What exactly is counted by nine fit failures, 1,982 reservations and 98.3% unknown lengths?
9. Why are the Python rules independent of FastAPI, the database and the animation?
10. Why is PostgreSQL needed for the deployed app while SQLite is convenient locally?
11. What prevents two concurrent conflicting saves from both succeeding? What is the throughput tradeoff of the global write lock?
12. Why is a corrected measurement allowed to be saved even when it exposes problems? What is recorded, and what still needs action?
13. Why can an old measurement acknowledgement become invalid? Can I demonstrate the stale-preview refusal?
14. What happens if the measurement saves but writing its review fails? Why must they share a transaction?
15. Which decisions live in the browser, and which must remain on the server?
16. How do the live ledger, historical Audit and Pages snapshot differ?
17. What is still outside scope, and which assumption would I confirm first with a real coordinator?
18. Which parts were produced with AI assistance, which decisions have I checked myself, and which code can I explain line by line?

## 9. Submission readiness

- All core smoke cases pass on the deployed URL.
- Critical rule and correction cases pass locally; both database suites are green.
- The record from the live write smoke test has been cancelled.
- The README, website guide, assumptions and actual behavior agree.
- At least one independent person has completed the usability tasks; observed blockers have been fixed or stated clearly.
- The demo can be repeated in two minutes, with exact vessel names, dates and calculations.
- Auth, depth, time-of-day and full change-history limitations are described honestly. The synthetic demo is not presented as ready for a real harbor's operations.

**Result log template:** Case ID · build/version · browser/device · expected · observed · pass/fail · issue/evidence · retest result.

## 10. Audit filters and linked layouts

| ID | Do this | Passing result |
|---|---|---|
| A01 | In Audit choose South Float East, Closure overlap, and 15 July 2017 in both date fields; search Amber. | Exactly one finding, with Utility work and OSV Amber Reef. A closure’s final occupied day is included. |
| A02 | Change the dates to 16 July 2017. | No closure overlap; the empty state explains how to widen or clear filters. |
| A03 | Enter From later than To. | An error appears; the last valid results and their applied scope remain visible. |
| A04 | Select Shared capacity unknown with the other filters clear. | Twelve historical berth-day findings. Fit unknown is a separate category. |
| A05 | Set a useful filter combination, check Remember my filters, reload, then uncheck it and reload again. | The first reload restores the combination; the second starts with all findings. Tab switching within a session retains the current selection. |
| A06 | Use Next 25, then change a filter or press Clear filters. | Pagination stays within the matching results and returns to the first page after filter changes. |
| A07 | Open a filtered finding in Grid + Harbor. | Side by side opens at a day inside the selected overlap, and both views share that day. The audit is historical; the opened ledger is current. |
| A08 | In Side by side choose a grid day number, then change the Harbor date to another month. | Both the selected grid day/month and Harbor date follow each change. |
| A09 | Select 31 January 2028 in Harbor, then choose Next month in Grid. Repeat for 2027. | Both show 29 February 2028 and 28 February 2027 respectively. No date rolls into March. |
| A10 | Switch Harbor → Grid → Side by side; leave for Audit and return to Schedule. | Date and selected layout stay consistent. The old #grid/#harbor links and new #split link select the intended layout. |
| A11 | Use arrow keys in the layout radio group and the grid’s date header. | Layout changes and selected dates work without a mouse. There is one date-header tab stop and one berth-day cell tab stop. |
| A12 | Try Audit and Side by side at phone width. | Filter fields remain usable; paired views stack, with wide grids/maps scrolling within their own panels. The whole page has no horizontal overflow. |

## 11. Dropdowns and suggested input

| ID | Do this | Passing result |
|---|---|---|
| I01 | Open Book and choose R/V Clear Tern from Vessel suggestions without typing. Then type Amber to narrow the list. | Choices use registry names and show recorded lengths or unknown. The exact chosen vessel is used for Check. |
| I02 | Choose Clear Tern and North Pier Face; press Check. | The 120 ft vessel still produces the 45 ft fit failure. Dropdowns do not bypass rules or save automatically. |
| I03 | In Vessel registries choose a name from its suggestion menu. In Audit choose OSV Amber Reef. | Each search updates immediately; Audit offers only historical finding names. Custom partial searches and zero results still work. |
| I04 | Change Book From to 27 February 2028, then open To suggestions and choose the seven-day stay. | To becomes 4 March 2028. Same as From gives a one-day stay. Both calendars and custom dates remain usable. |
| I05 | Choose date/month shortcuts in Side by side. | Grid and Harbor remain synchronized. Audit date menus can clear either limit and still reject reversed ranges. |
| I06 | Switch Kind between Event and Closure, then open Title suggestions. | Relevant title examples appear; a custom title is accepted. |
| I07 | Enter an existing note and select an arrival template. | Existing text remains; the prompt is appended and selected for editing. Unfinished bracketed prompts block Save until filled or removed. |
| I08 | Use an override template after a blocking Check. Then change a date. | The template needs real details. Changing a booking field clears the old override, including its template validation message. |
| I09 | Select a known vessel, then type a new name. Open its length menu. | The new name has no inherited length. The menu offers unknown; known vessels offer only their own recorded length. |
| I10 | Open a measurement review and an existing reservation editor. Inspect all date, note, length and reason fields. | Every typed field has a labeled menu; choices trigger the usual preview/check requirements. Close without saving when testing production. |
| I11 | Tab to a suggestion menu and use arrow keys/Enter. Repeat Book and Audit at phone width. | Menus work with keyboard and native mobile controls; fields and long option labels do not widen the page. |
| I12 | Rapidly change a vessel search. If possible, interrupt its request in a local test. | Late results never replace the latest query; failed suggestions explain the problem and leave typing available. |
