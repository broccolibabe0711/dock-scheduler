"""SQLite storage: one file, plain SQL, rows turned into the model objects.

    python -m dock.db import "data/Dock Schedule - Synthetic Sample.xlsx" --db dock.db

Nothing here decides whether a booking is allowed; that is rules.py. This
module only reads and writes rows and hydrates Berth / Vessel / Reservation
objects for the rules to judge.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import date
from pathlib import Path
from typing import Iterable

from .models import Berth, CapacityMode, DayRange, Reservation, ReservationKind, Vessel, name_key

SCHEMA = Path(__file__).with_name("schema.sql").read_text()


def connect(path: str | Path = "dock.db"):
    if str(path).startswith(("postgres://", "postgresql://")):
        from .postgres import PostgresConnection
        return PostgresConnection(str(path))
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    return conn


def initialize(conn) -> None:
    if hasattr(conn, "initialize"):
        conn.initialize(SCHEMA)


def begin_write(conn) -> None:
    if hasattr(conn, "begin_write"):
        conn.begin_write()
    else:
        conn.execute("BEGIN IMMEDIATE")


# ---------------------------------------------------------------- rows -> objects
def _date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def berth_from_row(row: sqlite3.Row) -> Berth:
    return Berth(
        name=row["name"],
        length_ft=row["length_ft"],
        capacity_mode=CapacityMode(row["capacity_mode"]),
        clearance_ft=row["clearance_ft"],
        active_from=_date(row["active_from"]),
        active_to=_date(row["active_to"]),
        id=row["id"],
    )


def vessel_from_row(row: sqlite3.Row) -> Vessel:
    return Vessel(
        name=row["name"],
        length_ft=row["length_ft"],
        type_prefix=row["type_prefix"],
        draft_ft=row["draft_ft"],
        operator=row["operator"],
        rafts_ok=bool(row["rafts_ok"]),
        notes=row["notes"],
        id=row["id"],
    )


def reservation_from_row(row: sqlite3.Row, vessel: Vessel | None) -> Reservation:
    return Reservation(
        berth_id=row["berth_id"],
        kind=ReservationKind(row["kind"]),
        days=DayRange(date.fromisoformat(row["start_date"]), date.fromisoformat(row["end_date"])),
        vessel=vessel,
        title=row["title"],
        status=row["status"],
        override_reason=row["override_reason"],
        source=row["source"],
        legacy_ref=row["legacy_ref"],
        notes=row["notes"],
        id=row["id"],
    )


# ---------------------------------------------------------------- readers
def berths(conn: sqlite3.Connection) -> list[Berth]:
    return [berth_from_row(r) for r in conn.execute("SELECT * FROM berths ORDER BY id")]


def berth(conn: sqlite3.Connection, berth_id: int) -> Berth | None:
    row = conn.execute("SELECT * FROM berths WHERE id = ?", (berth_id,)).fetchone()
    return berth_from_row(row) if row else None


def vessels(conn: sqlite3.Connection, query: str = "", limit: int = 500) -> list[Vessel]:
    if query:
        rows = conn.execute(
            "SELECT * FROM vessels WHERE name_key LIKE ? ORDER BY name LIMIT ?",
            (f"%{name_key(query)}%", limit),
        )
    else:
        rows = conn.execute("SELECT * FROM vessels ORDER BY name LIMIT ?", (limit,))
    return [vessel_from_row(r) for r in rows]


def vessel(conn: sqlite3.Connection, vessel_id: int) -> Vessel | None:
    row = conn.execute("SELECT * FROM vessels WHERE id = ?", (vessel_id,)).fetchone()
    return vessel_from_row(row) if row else None


def vessel_by_name(conn: sqlite3.Connection, name: str) -> Vessel | None:
    row = conn.execute("SELECT * FROM vessels WHERE name_key = ?", (name_key(name),)).fetchone()
    return vessel_from_row(row) if row else None


def reservations(
    conn: sqlite3.Connection,
    berth_id: int | None = None,
    start: date | None = None,
    end: date | None = None,
    include_cancelled: bool = False,
) -> list[Reservation]:
    """Reservations overlapping [start, end] (inclusive), optionally on one berth."""
    where, params = [], []
    if berth_id is not None:
        where.append("r.berth_id = ?")
        params.append(berth_id)
    if start is not None:
        where.append("r.end_date >= ?")
        params.append(start.isoformat())
    if end is not None:
        where.append("r.start_date <= ?")
        params.append(end.isoformat())
    if not include_cancelled:
        where.append("r.status <> 'cancelled'")
    sql = "SELECT r.*, v.id AS v_id FROM reservations r LEFT JOIN vessels v ON v.id = r.vessel_id"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY r.start_date, r.berth_id, r.id"
    rows = conn.execute(sql, params).fetchall()
    vessel_ids = {r["vessel_id"] for r in rows if r["vessel_id"] is not None}
    vessel_map = {}
    if vessel_ids:
        marks = ",".join("?" * len(vessel_ids))
        for vr in conn.execute(f"SELECT * FROM vessels WHERE id IN ({marks})", tuple(vessel_ids)):
            vessel_map[vr["id"]] = vessel_from_row(vr)
    return [reservation_from_row(r, vessel_map.get(r["vessel_id"])) for r in rows]


def reservation(conn: sqlite3.Connection, reservation_id: int) -> Reservation | None:
    row = conn.execute("SELECT * FROM reservations WHERE id = ?", (reservation_id,)).fetchone()
    if row is None:
        return None
    v = vessel(conn, row["vessel_id"]) if row["vessel_id"] is not None else None
    return reservation_from_row(row, v)


def annotations(conn: sqlite3.Connection, start: date | None = None, end: date | None = None) -> list[dict]:
    where, params = [], []
    if start is not None:
        where.append("day >= ?")
        params.append(start.isoformat())
    if end is not None:
        where.append("day <= ?")
        params.append(end.isoformat())
    sql = "SELECT * FROM annotations" + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY day, id"
    return [dict(r) for r in conn.execute(sql, params)]


def issues(conn: sqlite3.Connection, kind: str | None = None, sheet: str | None = None, limit: int = 2000) -> list[dict]:
    where, params = [], []
    if kind:
        where.append("kind = ?")
        params.append(kind)
    if sheet:
        where.append("sheet = ?")
        params.append(sheet)
    sql = "SELECT * FROM import_issues" + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY id LIMIT ?"
    return [dict(r) for r in conn.execute(sql, (*params, limit))]


def issue_counts(conn: sqlite3.Connection) -> dict[str, int]:
    rows = conn.execute("SELECT kind, COUNT(*) AS n FROM import_issues GROUP BY kind ORDER BY n DESC")
    return {r["kind"]: r["n"] for r in rows}


def meta(conn: sqlite3.Connection, key: str) -> dict | None:
    row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return json.loads(row["value"]) if row else None


# ---------------------------------------------------------------- writers
def insert_vessel(conn: sqlite3.Connection, v: Vessel) -> Vessel:
    cur = conn.execute(
        "INSERT INTO vessels (name, name_key, type_prefix, length_ft, draft_ft, operator, rafts_ok, notes)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?) RETURNING id",
        (v.name, v.key, v.type_prefix, v.length_ft, v.draft_ft, v.operator, int(v.rafts_ok), v.notes),
    )
    inserted_id = cur.fetchone()["id"]
    conn.commit()
    return Vessel(v.name, v.length_ft, v.type_prefix, v.draft_ft, v.operator, v.rafts_ok, v.notes, id=inserted_id)


def update_vessel(conn: sqlite3.Connection, vessel_id: int, fields: dict) -> Vessel | None:
    """Apply the given fields; a None value clears the column (length back to unknown)."""
    allowed = {"name", "length_ft", "draft_ft", "type_prefix", "operator", "rafts_ok", "notes"}
    changes = {k: v for k, v in fields.items() if k in allowed}
    if "name" in changes:
        changes["name_key"] = name_key(changes["name"])
    if "rafts_ok" in changes:
        changes["rafts_ok"] = int(changes["rafts_ok"])
    if changes:
        sets = ", ".join(f"{k} = ?" for k in changes)
        conn.execute(f"UPDATE vessels SET {sets} WHERE id = ?", (*changes.values(), vessel_id))
        conn.commit()
    return vessel(conn, vessel_id)


def insert_reservation(conn: sqlite3.Connection, r: Reservation) -> Reservation:
    cur = conn.execute(
        "INSERT INTO reservations (berth_id, kind, vessel_id, title, start_date, end_date, status,"
        " override_reason, source, legacy_ref, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING id",
        (
            r.berth_id, r.kind.value, r.vessel.id if r.vessel else None, r.title,
            r.days.start.isoformat(), r.days.end.isoformat(), r.status,
            r.override_reason, r.source, r.legacy_ref, r.notes,
        ),
    )
    inserted_id = cur.fetchone()["id"]
    conn.commit()
    return reservation(conn, inserted_id)  # type: ignore[return-value]


def update_reservation(conn: sqlite3.Connection, r: Reservation) -> Reservation:
    """Write back a reservation object (its id must exist)."""
    conn.execute(
        "UPDATE reservations SET berth_id = ?, kind = ?, vessel_id = ?, title = ?, start_date = ?, end_date = ?,"
        " status = ?, override_reason = ?, notes = ? WHERE id = ?",
        (
            r.berth_id, r.kind.value, r.vessel.id if r.vessel else None, r.title,
            r.days.start.isoformat(), r.days.end.isoformat(), r.status, r.override_reason, r.notes, r.id,
        ),
    )
    conn.commit()
    return reservation(conn, r.id)  # type: ignore[arg-type,return-value]


# ---------------------------------------------------------------- loading an import
def load_import(conn: sqlite3.Connection, result, audit_data: dict | None = None) -> None:
    """Replace everything in the database with an ImportResult, all or nothing.

    One transaction: if any row is refused by a constraint, the previous
    contents survive untouched instead of leaving an empty ledger."""
    begin_write(conn)
    try:
        _load_import_rows(conn, result, audit_data)
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def _load_import_rows(conn: sqlite3.Connection, result, audit_data: dict | None) -> None:
    for table in ("annotations", "reservations", "tours", "import_issues", "vessels", "berths", "meta"):
        conn.execute(f"DELETE FROM {table}")
    conn.executemany(
        "INSERT INTO berths (id, name, length_ft, capacity_mode, clearance_ft, active_from, active_to)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            (b.id, b.name, b.length_ft, b.capacity_mode.value, b.clearance_ft,
             b.active_from.isoformat() if b.active_from else None, b.active_to.isoformat() if b.active_to else None)
            for b in result.berths
        ],
    )
    conn.executemany(
        "INSERT INTO vessels (id, name, name_key, type_prefix, length_ft, draft_ft, operator, rafts_ok, notes)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [(v.id, v.name, v.key, v.type_prefix, v.length_ft, v.draft_ft, v.operator, int(v.rafts_ok), v.notes)
         for v in result.vessels],
    )
    conn.executemany(
        "INSERT INTO reservations (id, berth_id, kind, vessel_id, title, start_date, end_date, status,"
        " override_reason, source, legacy_ref, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (r.id, r.berth_id, r.kind.value, r.vessel.id if r.vessel else None, r.title,
             r.days.start.isoformat(), r.days.end.isoformat(), r.status, r.override_reason,
             r.source, r.legacy_ref, r.notes)
            for r in result.reservations
        ],
    )
    conn.executemany(
        "INSERT INTO annotations (berth_id, day, text, label, legacy_ref) VALUES (?, ?, ?, ?, ?)",
        [(a.berth_id, a.day.isoformat() if a.day else None, a.text, a.label, a.legacy_ref) for a in result.annotations],
    )
    conn.executemany(
        "INSERT INTO import_issues (kind, severity, sheet, cell, message) VALUES (?, ?, ?, ?, ?)",
        [(i.kind, i.severity, i.sheet, i.cell, i.message) for i in result.issues],
    )
    conn.executemany(
        "INSERT INTO tours (day, time_raw, guide, guest, organisation, people, approximate, vessel_name, notes)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [(t.day.isoformat() if t.day else None, t.time_raw, t.guide, t.guest, t.organisation, t.people,
          int(t.approximate), t.vessel_name, t.notes) for t in result.tours],
    )
    conn.execute("INSERT INTO meta (key, value) VALUES ('import_stats', ?)", (json.dumps(result.stats, default=str),))
    if audit_data is not None:
        conn.execute("INSERT INTO meta (key, value) VALUES ('audit', ?)", (json.dumps(audit_data, default=str),))
    if hasattr(conn, "reset_sequences"):
        conn.reset_sequences()


def import_workbook_into(db_path: str | Path, workbook: str | Path) -> dict:
    """Import a workbook, audit it, and fill the database. Returns the audit data."""
    from .audit import build_report
    from .importer import import_workbook

    result = import_workbook(workbook)
    result.stats["source"] = Path(workbook).name
    _, data = build_report(result)
    conn = connect(db_path)
    try:
        initialize(conn)
        load_import(conn, result, data)
    finally:
        conn.close()
    return data


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Load a legacy workbook into the SQLite ledger.")
    sub = ap.add_subparsers(dest="command", required=True)
    imp = sub.add_parser("import", help="import a workbook (replaces the database contents)")
    imp.add_argument("workbook")
    imp.add_argument("--db", default="dock.db")
    args = ap.parse_args(argv)
    if args.command == "import":
        data = import_workbook_into(args.db, args.workbook)
        t = data["totals"]
        print(f"{t['reservations']} reservations, {t['vessels']} vessels, {t['berths']} berths, "
              f"{t['issues']} issues -> {args.db}")


if __name__ == "__main__":
    main()
