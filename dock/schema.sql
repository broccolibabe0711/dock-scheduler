-- The ledger. The rules live in Python (dock/rules.py); these CHECK constraints
-- are the second line of defence, so a bad row cannot get in behind the rules.
CREATE TABLE IF NOT EXISTS berths (
    id            INTEGER PRIMARY KEY,
    name          TEXT    NOT NULL UNIQUE,
    length_ft     REAL    CHECK (length_ft IS NULL OR length_ft > 0),
    capacity_mode TEXT    NOT NULL CHECK (capacity_mode IN ('linear', 'exclusive')),
    clearance_ft  REAL    NOT NULL DEFAULT 10 CHECK (clearance_ft >= 0),
    active_from   TEXT,                       -- ISO date or NULL (always)
    active_to     TEXT,
    CHECK (active_from IS NULL OR active_to IS NULL OR active_to >= active_from)
);

CREATE TABLE IF NOT EXISTS vessels (
    id          INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL,
    name_key    TEXT    NOT NULL UNIQUE,      -- case-folded identity, see models.name_key
    type_prefix TEXT,
    length_ft   REAL    CHECK (length_ft IS NULL OR length_ft > 0),
    draft_ft    REAL    CHECK (draft_ft IS NULL OR draft_ft > 0),
    operator    TEXT,
    rafts_ok    INTEGER NOT NULL DEFAULT 0,
    notes       TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS reservations (
    id              INTEGER PRIMARY KEY,
    berth_id        INTEGER NOT NULL REFERENCES berths(id),
    kind            TEXT    NOT NULL CHECK (kind IN ('vessel', 'event', 'closure')),
    vessel_id       INTEGER REFERENCES vessels(id),
    title           TEXT    NOT NULL DEFAULT '',
    start_date      TEXT    NOT NULL,          -- ISO dates; inclusive on both ends
    end_date        TEXT    NOT NULL CHECK (end_date >= start_date),
    status          TEXT    NOT NULL DEFAULT 'planned' CHECK (status IN ('planned', 'confirmed', 'cancelled')),
    override_reason TEXT,
    source          TEXT    NOT NULL DEFAULT 'manual' CHECK (source IN ('manual', 'import')),
    legacy_ref      TEXT,
    notes           TEXT    NOT NULL DEFAULT '',
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    CHECK ((kind = 'vessel') = (vessel_id IS NOT NULL)),
    CHECK (kind = 'vessel' OR title <> '')
);
CREATE INDEX IF NOT EXISTS ix_reservations_berth_dates ON reservations (berth_id, start_date, end_date);

CREATE TABLE IF NOT EXISTS annotations (
    id         INTEGER PRIMARY KEY,
    berth_id   INTEGER REFERENCES berths(id),
    day        TEXT,
    text       TEXT NOT NULL,
    label      TEXT NOT NULL,
    legacy_ref TEXT
);

CREATE TABLE IF NOT EXISTS import_issues (
    id       INTEGER PRIMARY KEY,
    kind     TEXT NOT NULL,
    severity TEXT NOT NULL,
    sheet    TEXT NOT NULL,
    cell     TEXT NOT NULL,
    message  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tours (
    id           INTEGER PRIMARY KEY,
    day          TEXT,
    time_raw     TEXT,
    guide        TEXT,
    guest        TEXT,
    organisation TEXT,
    people       INTEGER,
    approximate  INTEGER NOT NULL DEFAULT 0,
    vessel_name  TEXT,
    notes        TEXT
);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
