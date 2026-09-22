# Submission verification

22 September 2026 · Application revision 0162e7cb9f41d52652de6fb5b1c211155c544d8c

## Completed checks

| Check | Result |
|---|---|
| Public repository and deployed app | Repository is public; Vercel reports the application revision deployed successfully. The live API responds without authentication and reports persistent PostgreSQL. |
| Python regression suite | 157 passed, 1 intentionally skipped, using SQLite and a disposable local PostgreSQL database. Two dependency deprecation warnings remain. |
| Frontend regression suite | 10 passed. Includes combined audit filtering, inclusive date shortcuts, note-template preservation, name normalization and measurement suggestion provenance. |
| Current live workflow | Create, read, conflicting-save refusal, edit and read-back passed for labelled test event #1988. It was then cancelled and the cancellation was read back. The cancelled record remains as verification evidence. |
| Live rule and data checks | Oversized vessel refused; reversed dates rejected; measurement preview left the vessel unchanged; operational annotations and historical audit evidence available. |
| Historical evidence | Nine fit findings, twelve unverifiable shared berth-days and the closure overlap of 11–15 July 2017 reconcile to the exported evidence. |
| Prior release browser checks | All 19 typed fields had suggestions; booking, audit, edit and measurement workflows, keyboard selection, and 390 px phone layouts were exercised on 20 September. |

The test suite was rerun for submission preparation. [Application CI](https://github.com/broccolibabe0711/dock-scheduler/actions/runs/35557986650) records the deployed application revision. The repository's Actions and Vercel status record the subsequent submission-documentation release.

## Interpretation

These checks support the implemented behavior; they are not a claim that every item in the acceptance plan has been completed by an independent user. Cross-browser coverage is limited, and no formal accessibility or penetration audit has been performed. Personal rehearsal and any application-specific disclosure requirements remain for the applicant to review.

The supplied handoff is a historical development record. Its old test totals and original navigation descriptions are superseded by the current source, guides and verification results. This release used manual review and executable tests; the handoff's named review-agent plugins were not available in this session.
