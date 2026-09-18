# Working rules for this repository

## What this is
Baron's take-home for Columbia Software Solutions: a dock/berth reservation system. The plan is `FRAMEWORK.md`; follow it, and when a decision changes, update it and add a one-paragraph record in `docs/decisions/`.

## Review gate (non-negotiable)
Before every reply that changed code, run the review pass: `pr-review-toolkit` agents (`code-reviewer`, `silent-failure-hunter`, `pr-test-analyzer`, `code-simplifier`) on the diff, plus `pytest`. Fix real findings in the same change; state in the reply what was reviewed and what was found or consciously rejected. `security-guidance` hooks run automatically on edits, commits and pushes.

## Stack and constraints
Python 3.12, standard-library `sqlite3`, `openpyxl`, FastAPI + uvicorn, `pytest`; front end is vanilla HTML/CSS/JS with inline SVG and no build step. Do not add dependencies without a decision record. The rules engine (`dock/rules.py`) must import nothing beyond the standard library and `dock/models.py`; the front end never computes rules.

## Explainability
Baron must be able to explain every line in an interview. Prefer the readable version over the clever one; name things after the domain (berth, vessel, reservation, finding); keep functions short; put the "why" in a docstring or a decision record, not in chat.

## Commits
Small commits with messages that say why. Attribution line as configured by the session.
