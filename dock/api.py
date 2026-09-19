"""The HTTP layer: parse the request, ask the referee, return JSON.

    .venv/bin/uvicorn dock.api:app --reload      then open http://127.0.0.1:8000

Every write goes through rules.check(). A blocking verdict (CONFLICT or
UNKNOWN) is refused with 409 unless the request carries an override_reason,
which is then stored on the reservation. Routes never compute rules
themselves, and the front end only renders the findings they return.
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Iterator, Literal

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from . import db, rules
from .models import Berth, CheckResult, DayLoad, DayRange, Finding, Reservation, ReservationKind, Vessel

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.environ.get("DOCK_DB", ROOT / "dock.db"))
SAMPLE = ROOT / "data" / "Dock Schedule - Synthetic Sample.xlsx"
SITE = ROOT / "site"
log = logging.getLogger("dock")

def ensure_data() -> None:
    """First run: import the sample so the app is never empty."""
    conn = db.connect(DB_PATH)
    try:
        empty = conn.execute("SELECT COUNT(*) FROM berths").fetchone()[0] == 0
    finally:
        conn.close()
    if not empty:
        return
    if not SAMPLE.exists():
        log.warning("database %s is empty and no workbook found at %s; starting with no data", DB_PATH, SAMPLE)
        return
    data = db.import_workbook_into(DB_PATH, SAMPLE)
    log.info("imported %s into %s: %s", SAMPLE.name, DB_PATH, data["totals"])


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_data()
    yield


app = FastAPI(title="Dock Scheduler", version="0.1.0", lifespan=lifespan,
              description="Berth reservations with conflict and fit checking. Every write passes rules.check().")


def get_db() -> Iterator:
    conn = db.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


def iso(value: date | None) -> str | None:
    """Dates travel as ISO strings, also inside 409 bodies which bypass FastAPI's encoder."""
    return value.isoformat() if value is not None else None


# ---------------------------------------------------------------- JSON shapes
def berth_json(b: Berth) -> dict:
    return {"id": b.id, "name": b.name, "length_ft": b.length_ft, "capacity_mode": b.capacity_mode.value,
            "clearance_ft": b.clearance_ft, "active_from": iso(b.active_from), "active_to": iso(b.active_to)}


def vessel_json(v: Vessel) -> dict:
    return {"id": v.id, "name": v.name, "length_ft": v.length_ft, "type_prefix": v.type_prefix,
            "draft_ft": v.draft_ft, "operator": v.operator, "rafts_ok": v.rafts_ok, "notes": v.notes}


def reservation_json(r: Reservation) -> dict:
    return {"id": r.id, "berth_id": r.berth_id, "kind": r.kind.value, "vessel": vessel_json(r.vessel) if r.vessel else None,
            "title": r.title, "name": r.display_name, "start": iso(r.days.start), "end": iso(r.days.end), "days": r.days.days,
            "status": r.status, "override_reason": r.override_reason, "source": r.source,
            "legacy_ref": r.legacy_ref, "notes": r.notes}


def finding_json(f: Finding) -> dict:
    return {"code": f.code.value, "severity": f.severity.value, "message": f.message, "day": iso(f.day),
            "related": list(f.related), "numbers": f.numbers}


def result_json(res: CheckResult) -> dict:
    return {"verdict": res.verdict.value, "blocking": res.blocking, "findings": [finding_json(f) for f in res.findings]}


def _fit(r: Reservation, berth: Berth) -> str:
    """'ok', 'misfit' or 'unknown' for one occupant, from the same fit rule the form uses."""
    if r.kind is not ReservationKind.VESSEL or r.vessel is None:
        return "ok"
    findings = rules.fit_check(r.vessel, berth)
    if not findings:
        return "ok"
    return "misfit" if findings[0].severity.value == "error" else "unknown"


def load_json(load: DayLoad) -> dict:
    return {"berth_id": load.berth.id, "day": iso(load.day), "known_ft": load.known_ft, "unknown_count": load.unknown_count,
            "used_ft": load.used_ft, "capacity_ft": load.capacity_ft, "over_by_ft": load.over_by_ft,
            "over_capacity": load.over_capacity, "unverifiable": load.unverifiable,
            "occupants": [{**reservation_json(r), "fit": _fit(r, load.berth)} for r in load.occupants]}


# ---------------------------------------------------------------- request bodies
class ReservationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")  # a misspelt field is an error, not a silent no-op
    berth_id: int
    kind: Literal["vessel", "event", "closure"] = "vessel"
    vessel_id: int | None = None
    title: str = ""
    start: date
    end: date
    status: Literal["planned", "confirmed", "cancelled"] = "planned"
    override_reason: str | None = None
    notes: str = ""
    id: int | None = Field(default=None, description="set when re-checking an existing reservation")


class ReservationPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    berth_id: int | None = None
    start: date | None = None
    end: date | None = None
    status: Literal["planned", "confirmed", "cancelled"] | None = None
    override_reason: str | None = None
    notes: str | None = None


class VesselIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    length_ft: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    type_prefix: str | None = None
    draft_ft: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    operator: str | None = None
    rafts_ok: bool = False
    notes: str = ""


class VesselPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = None
    length_ft: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    type_prefix: str | None = None
    draft_ft: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    operator: str | None = None
    rafts_ok: bool | None = None
    notes: str | None = None


def _candidate(conn, body: ReservationIn) -> tuple[Reservation, Berth]:
    berth = db.berth(conn, body.berth_id)
    if berth is None:
        raise HTTPException(404, f"no berth with id {body.berth_id}")
    vessel = None
    if body.kind == "vessel":
        if body.vessel_id is None:
            raise HTTPException(422, "a vessel reservation needs vessel_id")
        vessel = db.vessel(conn, body.vessel_id)
        if vessel is None:
            raise HTTPException(404, f"no vessel with id {body.vessel_id}")
    elif body.vessel_id is not None:
        raise HTTPException(422, f"a {body.kind} does not have a vessel; leave vessel_id out")
    try:
        candidate = Reservation(
            berth_id=body.berth_id, kind=ReservationKind(body.kind), days=DayRange(body.start, body.end),
            vessel=vessel, title=body.title, status=body.status, override_reason=body.override_reason,
            notes=body.notes, id=body.id,
        )
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    return candidate, berth


def _judge(conn, candidate: Reservation, berth: Berth) -> CheckResult:
    existing = db.reservations(conn, berth_id=berth.id, start=candidate.days.start, end=candidate.days.end)
    return rules.check(candidate, berth, existing)


# ---------------------------------------------------------------- routes
@app.get("/api/meta")
def get_meta(conn=Depends(get_db)) -> dict:
    """What the front end needs to orient itself: mode, date span, totals."""
    row = conn.execute("SELECT MIN(start_date) AS first_day, MAX(end_date) AS last_day, COUNT(*) AS n"
                       " FROM reservations WHERE status <> 'cancelled'").fetchone()
    stats = db.meta(conn, "import_stats") or {}
    return {"mode": "api", "first_day": row["first_day"], "last_day": row["last_day"],
            "reservations": row["n"], "totals": stats.get("totals", {}), "source": stats.get("source", "")}


@app.get("/api/berths")
def list_berths(conn=Depends(get_db)) -> list[dict]:
    return [berth_json(b) for b in db.berths(conn)]


@app.get("/api/vessels")
def list_vessels(q: str = "", limit: int = Query(50, le=1000), conn=Depends(get_db)) -> list[dict]:
    return [vessel_json(v) for v in db.vessels(conn, q, limit)]


@app.post("/api/vessels", status_code=201)
def create_vessel(body: VesselIn, conn=Depends(get_db)) -> dict:
    if db.vessel_by_name(conn, body.name) is not None:
        raise HTTPException(409, f"a vessel named like {body.name!r} already exists")
    try:
        v = Vessel(body.name, body.length_ft, body.type_prefix, body.draft_ft, body.operator, body.rafts_ok, body.notes)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    return vessel_json(db.insert_vessel(conn, v))


@app.patch("/api/vessels/{vessel_id}")
def patch_vessel(vessel_id: int, body: VesselPatch, conn=Depends(get_db)) -> dict:
    """Change vessel facts. Sending a field as null clears it (a length can go back to unknown)."""
    if db.vessel(conn, vessel_id) is None:
        raise HTTPException(404, f"no vessel with id {vessel_id}")
    changes = {k: getattr(body, k) for k in body.model_fields_set}
    if not changes:
        raise HTTPException(422, "no changes given")
    if "name" in changes:
        if not changes["name"] or not changes["name"].strip():
            raise HTTPException(422, "a vessel needs a name")
        other = db.vessel_by_name(conn, changes["name"])
        if other is not None and other.id != vessel_id:
            raise HTTPException(409, f"a vessel named like {changes['name']!r} already exists")
    v = db.update_vessel(conn, vessel_id, changes)
    return vessel_json(v)  # type: ignore[arg-type]


@app.get("/api/reservations")
def list_reservations(
    start: date | None = None, end: date | None = None, berth_id: int | None = None,
    include_cancelled: bool = False, conn=Depends(get_db),
) -> list[dict]:
    return [reservation_json(r) for r in db.reservations(conn, berth_id, start, end, include_cancelled)]


@app.get("/api/reservations/{reservation_id}")
def get_reservation(reservation_id: int, conn=Depends(get_db)) -> dict:
    r = db.reservation(conn, reservation_id)
    if r is None:
        raise HTTPException(404, f"no reservation with id {reservation_id}")
    return reservation_json(r)


@app.post("/api/check")
def check_reservation(body: ReservationIn, conn=Depends(get_db)) -> dict:
    """Judge a booking without saving it."""
    candidate, berth = _candidate(conn, body)
    return result_json(_judge(conn, candidate, berth))


@app.post("/api/reservations", status_code=201)
def create_reservation(body: ReservationIn, conn=Depends(get_db)) -> dict:
    """Save a booking. Blocking verdicts are refused (409) unless override_reason is given."""
    if body.id is not None:
        raise HTTPException(422, "id is only accepted by /api/check; a new booking has no id yet")
    candidate, berth = _candidate(conn, body)
    # judge and save inside one write transaction, so two coordinators booking the
    # same berth at the same moment cannot both pass the check
    conn.execute("BEGIN IMMEDIATE")
    try:
        result = _judge(conn, candidate, berth)
        if result.blocking and not (candidate.override_reason or "").strip():
            conn.rollback()
            raise HTTPException(409, detail=result_json(result))
        saved = db.insert_reservation(conn, candidate)
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise
    return {"reservation": reservation_json(saved), "check": result_json(result)}


@app.patch("/api/reservations/{reservation_id}")
def patch_reservation(reservation_id: int, body: ReservationPatch, conn=Depends(get_db)) -> dict:
    """Change dates, berth, status or notes.

    Only a change of berth, dates or status is judged; a note or an override
    reason on its own is saved as it is. Cancelling never needs a check."""
    current = db.reservation(conn, reservation_id)
    if current is None:
        raise HTTPException(404, f"no reservation with id {reservation_id}")
    changes = body.model_dump(exclude_none=True)
    if not changes:
        raise HTTPException(422, "no changes given")
    judged = any(k in changes for k in ("berth_id", "start", "end", "status"))
    try:
        days = DayRange(changes.get("start", current.days.start), changes.get("end", current.days.end))
        updated = Reservation(
            berth_id=changes.get("berth_id", current.berth_id), kind=current.kind, days=days, vessel=current.vessel,
            title=current.title, status=changes.get("status", current.status),
            override_reason=changes.get("override_reason", current.override_reason), source=current.source,
            legacy_ref=current.legacy_ref, notes=changes.get("notes", current.notes), id=current.id,
        )
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    berth = db.berth(conn, updated.berth_id)
    if berth is None:
        raise HTTPException(404, f"no berth with id {updated.berth_id}")
    if not judged:
        saved = db.update_reservation(conn, updated)
        return {"reservation": reservation_json(saved), "check": None}
    conn.execute("BEGIN IMMEDIATE")
    try:
        result = _judge(conn, updated, berth)
        # a blocking verdict needs a reason given in THIS request; one stored earlier
        # was about a different situation and must not exempt the change
        if result.blocking and not (body.override_reason or "").strip():
            conn.rollback()
            raise HTTPException(409, detail=result_json(result))
        saved = db.update_reservation(conn, updated)
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise
    return {"reservation": reservation_json(saved), "check": result_json(result)}


@app.get("/api/suggest")
def suggest(
    start: date, end: date, vessel_id: int | None = None, kind: Literal["vessel", "event", "closure"] = "vessel",
    title: str = "requested booking", include_unknown: bool = False, conn=Depends(get_db),
) -> list[dict]:
    """Berths where this booking would be accepted, smallest fitting first."""
    vessel = None
    if kind == "vessel":
        if vessel_id is None:
            raise HTTPException(422, "vessel_id is required for a vessel booking")
        vessel = db.vessel(conn, vessel_id)
        if vessel is None:
            raise HTTPException(404, f"no vessel with id {vessel_id}")
    try:
        wanted = Reservation(berth_id=0, kind=ReservationKind(kind), days=DayRange(start, end), vessel=vessel, title=title)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    existing = db.reservations(conn, start=start, end=end)
    out = rules.suggest_berths(wanted, db.berths(conn), existing, include_unknown=include_unknown)
    return [{"berth": berth_json(s.berth), "check": result_json(s.result)} for s in out]


@app.get("/api/loads")
def loads(start: date, end: date, berth_id: int | None = None, conn=Depends(get_db)) -> list[dict]:
    """Per-berth, per-day occupancy for drawing; the harbor view reads this."""
    if end < start:
        raise HTTPException(422, "end is before start")
    if (end - start).days > 400:
        raise HTTPException(422, "ask for at most 400 days at a time")
    berths = [b for b in db.berths(conn) if berth_id is None or b.id == berth_id]
    if berth_id is not None and not berths:
        raise HTTPException(404, f"no berth with id {berth_id}")
    existing = db.reservations(conn, start=start, end=end)
    days = DayRange(start, end)
    return [load_json(l) for b in berths for l in rules.day_loads(b, existing, days)]


@app.get("/api/annotations")
def list_annotations(start: date | None = None, end: date | None = None, conn=Depends(get_db)) -> list[dict]:
    return db.annotations(conn, start, end)


@app.get("/api/issues")
def list_issues(kind: str | None = None, sheet: str | None = None, limit: int = Query(500, le=5000), conn=Depends(get_db)) -> dict:
    return {"counts": db.issue_counts(conn), "issues": db.issues(conn, kind, sheet, limit)}


@app.get("/api/audit")
def get_audit(conn=Depends(get_db)) -> dict:
    """The audit of the imported history, as computed at import time."""
    data = db.meta(conn, "audit")
    if data is None:
        raise HTTPException(404, "no import has been loaded")
    return data


if SITE.exists():
    app.mount("/", StaticFiles(directory=SITE, html=True), name="site")
