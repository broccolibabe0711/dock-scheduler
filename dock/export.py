"""Write the read-only snapshot that GitHub Pages serves.

    python -m dock.export "data/Dock Schedule - Synthetic Sample.xlsx" --out site/data

The static site shows history, the audit and the harbor view from these
JSON files; it cannot judge new bookings because the rules run in Python.
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from .audit import build_report
from .importer import ImportResult, import_workbook


def snapshot(result: ImportResult, generated_on: date) -> dict[str, object]:
    report, audit_data = build_report(result)
    berths = [
        {"id": b.id, "name": b.name, "length_ft": b.length_ft, "capacity_mode": b.capacity_mode.value,
         "clearance_ft": b.clearance_ft,
         "active_from": b.active_from.isoformat() if b.active_from else None,
         "active_to": b.active_to.isoformat() if b.active_to else None}
        for b in result.berths
    ]
    vessels = [
        {"id": v.id, "name": v.name, "length_ft": v.length_ft, "type_prefix": v.type_prefix,
         "draft_ft": v.draft_ft, "operator": v.operator, "rafts_ok": v.rafts_ok, "notes": v.notes}
        for v in result.vessels
    ]
    reservations = [
        {"id": r.id, "berth_id": r.berth_id, "kind": r.kind.value, "vessel_id": r.vessel.id if r.vessel else None,
         "name": r.display_name, "length_ft": r.vessel.length_ft if r.vessel else None, "title": r.title,
         "start": r.days.start.isoformat(), "end": r.days.end.isoformat(), "status": r.status,
         "source": r.source, "legacy_ref": r.legacy_ref, "notes": r.notes}
        for r in result.reservations
    ]
    annotations = [
        {"berth_id": a.berth_id, "day": a.day.isoformat() if a.day else None, "text": a.text,
         "label": a.label, "legacy_ref": a.legacy_ref}
        for a in result.annotations
    ]
    issues = [{"kind": i.kind, "severity": i.severity, "sheet": i.sheet, "cell": i.cell, "message": i.message}
              for i in result.issues]
    # flags per reservation for the harbor view: no rules run in the browser
    misfit_ids = sorted({r.id for r, _ in report.misfits})
    unknown_ids = sorted({r.id for r in report.unknown_length})
    over_days = [{"berth_id": l.berth.id, "day": l.day.isoformat()} for l in report.over_capacity]
    unverifiable_days = [{"berth_id": l.berth.id, "day": l.day.isoformat()} for l in report.unverifiable]
    active = [r for r in result.reservations if r.is_active]
    meta = {"generated_on": generated_on.isoformat(), "source": result.stats.get("source", ""),
            "totals": result.stats["totals"], "mode": "static",
            "first_day": min(r.days.start for r in active).isoformat() if active else None,
            "last_day": max(r.days.end for r in active).isoformat() if active else None,
            "reservations": len(active),
            "note": "Read-only snapshot generated from the sample workbook. Run the app locally to book."}
    return {
        "meta.json": meta,
        "berths.json": berths,
        "vessels.json": vessels,
        "reservations.json": reservations,
        "annotations.json": annotations,
        "issues.json": {"counts": result.issue_counts(), "issues": issues},
        "audit.json": audit_data,
        "flags.json": {"misfits": misfit_ids, "unknown_length": unknown_ids,
                       "over_capacity_days": over_days, "unverifiable_days": unverifiable_days},
    }


def write_snapshot(workbook: str | Path, out_dir: str | Path, generated_on: date | None = None) -> Path:
    result = import_workbook(workbook)
    result.stats["source"] = Path(workbook).name
    files = snapshot(result, generated_on or date.today())
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        (out / name).write_text(json.dumps(data, default=str, separators=(",", ":")))
    return out


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("workbook")
    ap.add_argument("--out", default="site/data")
    args = ap.parse_args(argv)
    out = write_snapshot(args.workbook, args.out)
    sizes = {p.name: p.stat().st_size for p in sorted(out.glob("*.json"))}
    print(json.dumps(sizes, indent=1))


if __name__ == "__main__":
    main()
