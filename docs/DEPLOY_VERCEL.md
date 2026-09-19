# Deploy the operable app on Vercel

Live production URL: <https://dock-scheduler-henna.vercel.app>.
The connected Neon resource is `dock-scheduler-db` on the Free plan in US East.
Only the Production environment is connected. Configure separate preview storage
before using a preview deployment for bookings.

The Vercel app runs the Python API and the existing front end together. Bookings
are stored in PostgreSQL. The GitHub Pages site remains a separate read-only
history snapshot.

1. Import this GitHub repository into Vercel. Select the repository root and the
   **FastAPI** framework. No front-end build command or output directory is needed.
2. Connect a **Neon Postgres** database from Vercel's Storage / Marketplace panel.
   Set `DATABASE_URL` to its pooled PostgreSQL connection string for the intended
   environment. Keep the database and app in the same region where possible.
3. Deploy. The first application start creates the schema and imports the sample
   workbook once. Subsequent deployments keep existing reservations. Initialization
   is protected by a database lock, including concurrent cold starts.
4. Open `/api/meta`: expect `mode: api`, `storage: postgres`, `persistent: true`.
5. In Book, create an event on a free date, refresh, and confirm it remains in the
   grid. A second whole-berth event on that date must be refused. Cancel the test
   reservation through its detail dialog when finished.

Deployment uses [Vercel's FastAPI support](https://vercel.com/docs/frameworks/backend/fastapi).
`app.py` exports the ASGI app; `vercel.json` selects FastAPI and the US East region.
Python 3.12 and pinned dependencies match the local environment.

## Storage and environments

The deployment fails with an actionable error if PostgreSQL is not configured.
Vercel's temporary filesystem is not used as a ledger. Local development still
defaults to `dock.db`, or another file configured with `DOCK_DB`.

Use separate databases for preview and production if both accept edits. Do not
point a test run at a deployed database: `TEST_DATABASE_URL` is **disposable test
storage** and the test fixtures replace its contents.

The sample is synthetic. This version is a shared demo without user accounts;
anyone with access can add, update, or cancel reservations. Use real operational
data only after adding access controls. Production deployment status and its URL
must be verified on Vercel; source configuration alone is not a deployment.

## Verification

```bash
python -m pytest -q
TEST_DATABASE_URL=postgresql://localhost/dock_test python -m pytest -q
```

With `TEST_DATABASE_URL` present, every API workflow runs against both SQLite and
PostgreSQL, including persistence and simultaneous conflicting writes. CI supplies
an isolated PostgreSQL service automatically. PostgreSQL write transactions use a
shared advisory lock, suitable for this small coordinator application.
