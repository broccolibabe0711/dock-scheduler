"""Run the rules over an imported history and write the audit report.

    python -m dock.audit "data/Dock Schedule - Synthetic Sample.xlsx" \
        --report docs/AUDIT_REPORT.md --json site/data/history.json

The report is the argument for the product: the same check() that guards
the booking form, applied to 23 years of the facility's own schedule.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from .importer import ImportResult, import_workbook
from .models import Berth, DayLoad, Reservation, ReservationKind, fmt_ft
from .rules import AuditReport, audit, fit_check, occupancy


def usage_days(result: ImportResult) -> dict[tuple[str, int], int]:
    """Distinct occupied days per berth name and calendar year, from our reservations."""
    out: dict[tuple[str, int], int] = defaultdict(int)
    for berth in result.berths:
        for day in occupancy(berth, result.reservations):
            out[(berth.name, day.year)] += 1
    return dict(out)


def _compress(loads: list[DayLoad]) -> list[dict]:
    """Consecutive over-capacity days with the same occupants become one row."""
    rows: list[dict] = []
    for load in sorted(loads, key=lambda l: (l.berth.id or 0, l.day)):
        names = tuple(sorted(r.display_name for r in load.occupants))
        last = rows[-1] if rows else None
        if last and last["berth"] == load.berth.name and last["_names"] == names and last["_end"] == load.day.toordinal() - 1:
            last["end"] = load.day.isoformat()
            last["_end"] = load.day.toordinal()
            last["days"] += 1
            continue
        rows.append({
            "berth": load.berth.name,
            "start": load.day.isoformat(),
            "end": load.day.isoformat(),
            "days": 1,
            "occupants": [_occupant(r, load.berth) for r in load.occupants],
            "used_ft": load.used_ft,
            "capacity_ft": load.capacity_ft,
            "over_ft": load.over_by_ft,
            "_names": names,
            "_end": load.day.toordinal(),
        })
    for row in rows:
        row.pop("_names")
        row.pop("_end")
    return rows


def _occupant(r: Reservation, berth: Berth) -> dict:
    return {
        "id": r.id,
        "name": r.display_name,
        "kind": r.kind.value,
        "length_ft": r.vessel.length_ft if r.vessel else berth.length_ft,
        "start": r.days.start.isoformat(),
        "end": r.days.end.isoformat(),
    }


def finding_rows(result: ImportResult, report: AuditReport) -> list[dict]:
    """Portable evidence for filtering. Classification and measurements come from the rules.

    Capacity/uncertainty rows represent individual berth-days; fit rows represent
    stays. A closure row spans only the actual overlap, not either full booking.
    """
    berths = {b.id: b for b in result.berths}
    rows = []

    def add(category, severity, berth_id, start, end, reservations, message):
        rows.append({
            "category": category, "severity": severity, "berth_id": berth_id,
            "berth": berths[berth_id].name if berth_id in berths else f"Unknown berth #{berth_id}",
            "start": start.isoformat(), "end": end.isoformat(),
            "names": [r.display_name for r in reservations],
            "reservation_ids": [r.id for r in reservations], "message": message,
            "sources": [r.legacy_ref for r in reservations if r.legacy_ref],
        })

    for category, pairs in (("fit", report.misfits), ("inactive", report.inactive)):
        for r, finding in pairs:
            add(category, "conflict", r.berth_id, r.days.start, r.days.end, [r], finding.message)
    for r in report.unknown_length:
        messages = [f.message for f in fit_check(r.vessel, berths[r.berth_id])]
        add("unknown_fit", "unknown", r.berth_id, r.days.start, r.days.end, [r], " ".join(messages))
    for category, loads in (("capacity", report.over_capacity), ("unverifiable", report.unverifiable)):
        for load in loads:
            message = (f"Shared use cannot be verified on {load.day}: a required length is missing."
                       if category == "unverifiable" else
                       f"Over capacity under the berth's sharing rules on {load.day}. "
                       f"Known occupied length {fmt_ft(load.known_ft)}; "
                       f"capacity {fmt_ft(load.capacity_ft) if load.capacity_ft is not None else 'unknown'}.")
            add(category, "unknown" if category == "unverifiable" else "conflict",
                load.berth.id, load.day, load.day, load.occupants, message)
    for closure, r in report.closure_conflicts:
        start, end = max(closure.days.start, r.days.start), min(closure.days.end, r.days.end)
        add("closure", "conflict", r.berth_id, start, end, [closure, r],
            f"{r.display_name} overlaps {closure.title} on {start} through {end} (inclusive).")
    for r in report.orphaned:
        add("orphaned", "conflict", r.berth_id, r.days.start, r.days.end, [r],
            "This reservation refers to a berth absent from the imported berth list.")
    return sorted(rows, key=lambda r: (r["severity"] != "conflict", r["start"], r["berth"], r["category"]))


def build_report(result: ImportResult) -> tuple[AuditReport, dict]:
    """Audit the history and gather everything the markdown and JSON need."""
    report = audit(result.berths, result.reservations)
    vessel_stays = [r for r in result.reservations if r.kind is ReservationKind.VESSEL]
    with_length = [r for r in vessel_stays if r.vessel and r.vessel.length_ft is not None]
    years = sorted({r.days.start.year for r in result.reservations})
    per_year = Counter(r.days.start.year for r in result.reservations)
    per_kind = Counter(r.kind.value for r in result.reservations)
    over_rows = _compress(list(report.over_capacity))
    usage = usage_days(result)
    summary_years = sorted({y for _, y in result.usage_summary})
    summary_rows = []
    for name in sorted({n for n, _ in result.usage_summary}):
        summary_rows.append({
            "berth": name,
            "summary": [result.usage_summary.get((name, y)) for y in summary_years],
            "ours": [usage.get((name, y), 0) for y in summary_years],
        })
    data = {
        "generated_from": str(result.stats.get("source", "")),
        "years": years,
        "totals": result.stats["totals"],
        "stitched": result.stats.get("stitched", 0),
        "reservations_by_kind": dict(per_kind),
        "reservations_by_year": {str(y): per_year[y] for y in years},
        "vessel_stays": len(vessel_stays),
        "vessel_stays_with_length": len(with_length),
        "audit_counts": report.counts,
        "findings": finding_rows(result, report),
        "over_capacity": over_rows,
        "misfits": [
            {"reservation": _occupant(r, next(b for b in result.berths if b.id == r.berth_id)),
             "berth": next(b.name for b in result.berths if b.id == r.berth_id),
             "berth_ft": next(b.length_ft for b in result.berths if b.id == r.berth_id),
             "message": f.message}
            for r, f in report.misfits
        ],
        "closure_conflicts": [
            {"closure": c.title, "berth": next(b.name for b in result.berths if b.id == c.berth_id),
             "closure_days": str(c.days), "displaced": r.display_name, "displaced_days": str(r.days)}
            for c, r in report.closure_conflicts
        ],
        "unverifiable_days": len(report.unverifiable),
        "inactive": [{"reservation": _occupant(r, next(b for b in result.berths if b.id == r.berth_id)), "message": f.message}
                     for r, f in report.inactive],
        "orphaned": [{"id": r.id, "name": r.display_name, "berth_id": r.berth_id, "start": r.days.start.isoformat(), "end": r.days.end.isoformat()}
                     for r in report.orphaned],
        "summary_years": summary_years,
        "summary_comparison": summary_rows,
        "issues_by_kind": result.issue_counts(),
        "issue_examples": {
            kind: [f"{i.sheet}!{i.cell}: {i.message}" if i.cell else f"{i.sheet}: {i.message}"
                   for i in result.issues if i.kind == kind][:3]
            for kind in result.issue_counts()
        },
    }
    return report, data


def render_markdown(data: dict) -> str:
    t = data["totals"]
    lines = [
        "# Audit of the legacy dock schedule",
        "",
        "Generated by `python -m dock.audit` from the sample workbook. The rules that produced",
        "these numbers are the same `dock/rules.py` functions that check every new booking.",
        "",
        "## Headline numbers",
        "",
        "| What | Value |",
        "|---|---|",
        f"| Years covered | {f"{data['years'][0]}–{data['years'][-1]}" if data['years'] else '(no reservations)'} |",
        f"| Cell runs read from the grids | {t['raw_stays']} |",
        f"| Reservations after stitching month-split stays | {t['reservations']} ({data['stitched']} stitched) |",
        f"| Of which vessel / event / closure | {data['reservations_by_kind'].get('vessel', 0)} / {data['reservations_by_kind'].get('event', 0)} / {data['reservations_by_kind'].get('closure', 0)} |",
        f"| Notes kept as annotations, not bookings | {t['annotations']} |",
        f"| Distinct vessels (grid and registries) | {t['vessels']}, {t['vessels_with_length']} with a known length |",
        f"| Vessel stays whose vessel has a known length | {data['vessel_stays_with_length']} of {data['vessel_stays']} |",
        f"| Berth-days over capacity | {data['audit_counts']['over_capacity_days']} |",
        f"| Reservation records with a vessel longer than its berth | {data['audit_counts']['misfits']} |",
        f"| Shared berth-days that cannot be verified (a length is missing) | {data['audit_counts']['unverifiable_days']} |",
        f"| Stays overlapping a closure | {data['audit_counts']['closure_conflicts']} |",
        f"| Issues the importer logged instead of guessing | {t['issues']} |",
        "",
        "## What \"over capacity\" means here",
        "",
        "On a pier face several vessels tie up end to end; each needs its length plus 10 feet",
        "of clearance, and the total may not exceed the face. Events and closures take the",
        "whole berth. A slip holds one occupant. Days are inclusive. When any occupant's length",
        "is unknown the day is *unverifiable*, never silently fine.",
        "",
        "## Over-capacity runs (first 25)",
        "",
        "| Berth | Days | Occupants | Used | Capacity |",
        "|---|---|---|---|---|",
    ]
    for row in data["over_capacity"][:25]:
        occ = ", ".join(
            f"{o['name']} ({fmt_ft(o['length_ft']) if o['length_ft'] is not None else '?'})" for o in row["occupants"]
        )
        when = row["start"] if row["start"] == row["end"] else f"{row['start']}..{row['end']}"
        used = fmt_ft(row["used_ft"]) if row["used_ft"] is not None else "?"
        cap = fmt_ft(row["capacity_ft"]) if row["capacity_ft"] is not None else "?"
        lines.append(f"| {row['berth']} | {when} | {occ} | {used} | {cap} |")
    if not data["over_capacity"]:
        lines.append("| (none) | | | | |")
    lines += ["", f"{len(data['over_capacity'])} runs in total.", "", "## Vessels that do not fit their berth", ""]
    if data["misfits"]:
        lines += ["| Vessel | Berth | Dates | Finding |", "|---|---|---|---|"]
        for m in data["misfits"]:
            r = m["reservation"]
            lines.append(f"| {r['name']} | {m['berth']} | {r['start']}..{r['end']} | {m['message']} |")
    else:
        lines.append("None among the stays whose vessel length is known.")
    if data["inactive"] or data["orphaned"]:
        lines += ["", "## Stays on berths out of service or unknown", ""]
        for x in data["inactive"]:
            lines.append(f"- {x['reservation']['name']} {x['reservation']['start']}..{x['reservation']['end']}: {x['message']}")
        for x in data["orphaned"]:
            lines.append(f"- {x['name']} {x['start']}..{x['end']}: berth id {x['berth_id']} is unknown")
    lines += ["", "## Stays overlapping a closure", ""]
    if data["closure_conflicts"]:
        lines += ["| Closure | Berth | Closure days | Displaced | Their days |", "|---|---|---|---|---|"]
        for c in data["closure_conflicts"]:
            lines.append(f"| {c['closure']} | {c['berth']} | {c['closure_days']} | {c['displaced']} | {c['displaced_days']} |")
    else:
        lines.append("None.")
    lines += ["", "## Usage-days: the workbook's own summary vs. what the grids contain", ""]
    if data["summary_comparison"]:
        years = data["summary_years"]
        lines.append("| Berth | " + " | ".join(f"{y} (sheet / grids)" for y in years) + " |")
        lines.append("|---|" + "---|" * len(years))
        for row in data["summary_comparison"]:
            cells = [f"{s if s is not None else '–'} / {o}" for s, o in zip(row["summary"], row["ours"])]
            lines.append(f"| {row['berth']} | " + " | ".join(cells) + " |")
        lines += [
            "",
            "The \"8YR Dock Summary\" sheet cannot be reproduced from the grids: it lists usage for",
            "\"North Finger Piers\" and \"Marsh Landing\" in years when no grid row carries those",
            "names, and some of its values exceed the number of days in a year. It is treated as",
            "reference material, not as ground truth.",
        ]
    lines += ["", "## Reservations per year", "", "| Year | Reservations |", "|---|---|"]
    for y, n in data["reservations_by_year"].items():
        lines.append(f"| {y} | {n} |")
    lines += ["", "## What the importer logged instead of guessing", "", "| Issue | Count | Examples |", "|---|---|---|"]
    for kind, n in data["issues_by_kind"].items():
        ex = "<br>".join(e.replace("|", "\\|") for e in data["issue_examples"][kind])
        lines.append(f"| `{kind}` | {n} | {ex} |")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("workbook")
    ap.add_argument("--report", default="docs/AUDIT_REPORT.md")
    ap.add_argument("--json", default=None)
    args = ap.parse_args(argv)
    result = import_workbook(args.workbook)
    result.stats["source"] = Path(args.workbook).name
    report, data = build_report(result)
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(render_markdown(data))
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(data, indent=1, default=str))
    c = data["audit_counts"]
    print(f"{data['totals']['reservations']} reservations; over capacity on {c['over_capacity_days']} berth-days; "
          f"{c['misfits']} misfits; {c['unverifiable_days']} unverifiable shared days; "
          f"{data['totals']['issues']} issues -> {args.report}")


if __name__ == "__main__":
    main()
