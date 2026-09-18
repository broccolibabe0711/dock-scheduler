"""The static snapshot: same facts as the API, and flags from the same day loads."""
from datetime import date

import pytest

from dock.export import snapshot
from dock.importer import import_workbook
from dock.models import DayRange
from dock.rules import day_loads
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
