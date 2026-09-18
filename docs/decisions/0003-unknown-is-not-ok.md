# 3. A missing length gives the verdict UNKNOWN, never OK

**Context.** Vessel lengths live only in the registry sheets, and only 19 of the 504 vessel names found in the grids have one. Some slips have no recorded length either.

**Decision.** `check()` returns one of three verdicts. `OK` means every rule passed with real numbers. `CONFLICT` means a rule failed. `UNKNOWN` means a rule could not be evaluated because a vessel's, a neighbour's or the berth's length is missing. `UNKNOWN` blocks saving exactly like `CONFLICT`; the operator either enters the length or records an override reason.

**Consequences.** The system never silently approves a booking it could not check. Most imported history will be marked "could not verify" rather than "fine", which is the honest description of that history and a strong argument for maintaining the registry. The UI treats UNKNOWN as a prompt for a number, not as an error.
