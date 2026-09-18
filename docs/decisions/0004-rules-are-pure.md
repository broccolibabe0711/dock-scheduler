# 4. The rules live in one pure module

**Context.** The booking form, the API, the importer's audit of history and the harbor drawing all need the same answers, and a beginner must be able to read the rules end to end.

**Decision.** `dock/rules.py` imports nothing beyond the standard library and `dock/models.py`. It takes plain objects and returns `Finding`s with a message for people and numbers for the UI. Storage, HTTP and drawing code call it; they never re-implement it.

**Consequences.** The rule tests run in milliseconds with no database or server. The audit report and the live form cannot disagree, because they are the same function. The front end only renders findings, which keeps it small and keeps the demo honest.
