"""The static snapshot: same facts as the API, and flags from the same day loads."""
from datetime import date

import pytest

from dock.export import snapshot
from dock.importer import import_workbook
from dock.models import DayRange
from dock.rules import day_loads
from dock.audit import build_report
from tests.fixtures.make_fixture import build


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    return import_workbook(build(tmp_path_factory.mktemp("wb") / "tiny.xlsx"))


def test_snapshot_carries_occupied_feet_and_per_day_flags(result):
    files = snapshot(result, date(2026, 9, 18))
    assert set(files) == {"meta.json", "berths.json", "vessels.json", "reservations.json", "annotations.json",
                          "issues.json", "audit.json", "flags.json"}
    [dory] = [r for r in files["reservations.json"] if r["name"] == "F/V Swift Dory"]
    assert dory["occupied_ft"] == 42  # 32' + 10' clearance, computed by the model
    float_east = next(b for b in files["berths.json"] if b["name"] == "South Float East")
    # the event on Jan 4-5 shares Jan 4 with M/V Second Boat: flagged, with no rule in the browser
    assert {"berth_id": float_east["id"], "day": "2014-01-04"} in files["flags.json"]["over_capacity_days"]
    assert files["meta.json"]["mode"] == "static" and files["meta.json"]["first_day"] == "1998-08-02"


def test_snapshot_flags_match_what_the_api_would_serve(result):
    files = snapshot(result, date(2026, 9, 18))
    flagged = {(f["berth_id"], f["day"]) for f in files["flags.json"]["over_capacity_days"]}
    active = [r for r in result.reservations if r.is_active]
    span = DayRange(min(r.days.start for r in active), max(r.days.end for r in active))
    served = {(b.id, l.day.isoformat()) for b in result.berths for l in day_loads(b, active, span) if l.over_capacity}
    assert flagged == served


def test_filterable_findings_reconcile_to_every_audit_category(result):
    from collections import Counter
    report, data = build_report(result)
    counts = Counter(r["category"] for r in data["findings"])
    assert counts == Counter({
        "fit": len(report.misfits), "unknown_fit": len(report.unknown_length),
        "capacity": len(report.over_capacity), "unverifiable": len(report.unverifiable),
        "closure": len(report.closure_conflicts), "inactive": len(report.inactive),
        "orphaned": len(report.orphaned),
    })
    assert all(r["start"] <= r["end"] and r["names"] for r in data["findings"])


def test_closure_filters_use_actual_overlap_and_keep_both_names(result):
    from dataclasses import replace
    from dock.models import Reservation, ReservationKind
    berth_id = result.berths[0].id
    closure = Reservation(berth_id, ReservationKind.CLOSURE, DayRange(date(2027, 1, 5), date(2027, 1, 10)),
                          title="Utility work", id=1001)
    displaced = Reservation(berth_id, ReservationKind.VESSEL, DayRange(date(2027, 1, 8), date(2027, 1, 20)),
                            vessel=result.vessels[0], id=1002)
    report, data = build_report(replace(result, reservations=[closure, displaced]))
    rows = [r for r in data["findings"] if r["category"] == "closure"]
    assert rows
    for row, (closure, displaced) in zip(sorted(rows, key=lambda r: r["reservation_ids"]),
                                        sorted(report.closure_conflicts, key=lambda pair: [r.id for r in pair])):
        assert row["start"] == max(closure.days.start, displaced.days.start).isoformat()
        assert row["end"] == min(closure.days.end, displaced.days.end).isoformat()
        assert row["names"] == [closure.display_name, displaced.display_name]


def test_shared_capacity_details_keep_individual_days_for_date_filters(result):
    report, data = build_report(result)
    rows = [r for r in data["findings"] if r["category"] == "capacity"]
    assert rows
    assert {(r["berth_id"], r["start"]) for r in rows} == {
        (load.berth.id, load.day.isoformat()) for load in report.over_capacity}
    assert all(r["start"] == r["end"] for r in rows)
