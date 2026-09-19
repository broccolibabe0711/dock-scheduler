# 0008: Operable Vercel deployment uses PostgreSQL

The requested deliverable is a live site that saves bookings. A static Pages
snapshot cannot do that, and SQLite on a serverless filesystem cannot reliably
keep edits between instances. Keep the existing rules, importer, API, and UI;
add a small psycopg adapter using the same parameterized SQL and a persistent
`DATABASE_URL`. SQLite remains the local default. Database initialization imports
only an empty ledger while holding a write lock; PostgreSQL identity sequences
advance past imported IDs. A transaction-scoped advisory lock protects the full
read/check/write sequence across instances. Every mutating API route obtains this
lock, including vessel edits, so facts cannot change during a booking decision.
Vercel refuses to start without PostgreSQL rather than offer temporary saves.
This adds one dependency and a database to provision. Tests cover both engines.
