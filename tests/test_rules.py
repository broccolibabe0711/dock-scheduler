"""Tests for the rules engine, written as sentences.

Each test states one rule as a fact about a small, hand-made harbor. If a
test name reads wrong to a dockmaster, the rule is wrong.
"""
from datetime import date

import pytest

from dock.models import (
    Berth,
    CapacityMode,
    DayRange,
    FindingCode,
    Reservation,
    ReservationKind,
    Severity,
    Verdict,
    Vessel,
    name_key,
)
from dock.rules import audit, check, day_loads, suggest_berths

# --- a small harbor ---------------------------------------------------------
WEST = Berth("North Pier West", 410, id=1)
FACE = Berth("North Pier Face", 75, id=2)
EAST = Berth("North Pier East", 240, id=3)
FLOAT = Berth("South Float East", 90, id=4)
SLIP = Berth("North Finger Pier 2", 40, capacity_mode=CapacityMode.EXCLUSIVE, id=5)
UNMEASURED = Berth("Small craft slip", None, capacity_mode=CapacityMode.EXCLUSIVE, id=6)
BERTHS = [WEST, FACE, EAST, FLOAT, SLIP, UNMEASURED]

ATLANTIS = Vessel("R/V Atlantis", 274, "R/V", id=1)
TIOGA = Vessel("R/V Tioga", 60, "R/V", id=2)
BARGE = Vessel("Barge Salt Dory", 100, "Barge", id=3)
MYSTERY = Vessel("F/V Grey Strand", None, "F/V", id=4)  # no length on file
RAFTER = Vessel("S/V Far Horizon", 55, "S/V", rafts_ok=True, id=5)
TINY = Vessel("F/V Tiny", 20, "F/V", id=6)


def d(text):
    return date.fromisoformat(text)


def days(a, b):
    return DayRange(d(a), d(b))


_ids = iter(range(100, 10_000))


def stay(berth, vessel, a, b, **kw):
    return Reservation(
        berth.id, ReservationKind.VESSEL, days(a, b), vessel=vessel, id=kw.pop("id", next(_ids)), **kw
    )


def event(berth, title, a, b, **kw):
    return Reservation(
        berth.id, ReservationKind.EVENT, days(a, b), title=title, id=kw.pop("id", next(_ids)), **kw
    )


def closure(berth, title, a, b, **kw):
    return Reservation(
        berth.id, ReservationKind.CLOSURE, days(a, b), title=title, id=kw.pop("id", next(_ids)), **kw
    )


def codes(result):
    return [f.code for f in result.findings]


# --- day ranges -------------------------------------------------------------
def test_adjacent_days_do_not_overlap():
    assert not days("2026-07-01", "2026-07-03").overlaps(days("2026-07-04", "2026-07-06"))


def test_sharing_one_day_overlaps():
    assert days("2026-07-01", "2026-07-03").overlaps(days("2026-07-03", "2026-07-06"))


def test_a_range_counts_its_days_inclusively():
    assert days("2026-07-03", "2026-07-05").days == 3


def test_end_before_start_is_rejected():
    with pytest.raises(ValueError):
        days("2026-07-05", "2026-07-03")


# --- fit --------------------------------------------------------------------
def test_a_vessel_exactly_as_long_as_the_berth_fits():
    r = check(stay(FACE, Vessel("M/V Exact", 75, id=9), "2026-07-01", "2026-07-02"), FACE, [])
    assert r.verdict is Verdict.OK and r.findings == ()


def test_one_foot_too_long_is_refused_with_the_numbers():
    r = check(stay(FACE, Vessel("M/V Long", 76, id=9), "2026-07-01", "2026-07-02"), FACE, [])
    assert r.verdict is Verdict.CONFLICT
    [f] = r.findings
    assert f.code is FindingCode.FIT and f.numbers["over_ft"] == 1
    assert "76'" in f.message and "75'" in f.message and "is 1' longer" in f.message


def test_unknown_vessel_length_is_unknown_even_on_an_empty_berth():
    r = check(stay(WEST, MYSTERY, "2026-07-01", "2026-07-02"), WEST, [])
    assert r.verdict is Verdict.UNKNOWN and r.blocking
    assert codes(r) == [FindingCode.UNKNOWN_VESSEL_LENGTH]


def test_unknown_berth_length_is_unknown():
    r = check(stay(UNMEASURED, TINY, "2026-07-01", "2026-07-02"), UNMEASURED, [])
    assert r.verdict is Verdict.UNKNOWN
    assert codes(r) == [FindingCode.UNKNOWN_BERTH_LENGTH]


# --- capacity on a pier face ------------------------------------------------
def test_two_vessels_share_a_long_face():
    existing = [stay(WEST, ATLANTIS, "2026-07-01", "2026-07-10")]
    r = check(stay(WEST, BARGE, "2026-07-05", "2026-07-08"), WEST, existing)
    assert r.verdict is Verdict.OK  # (274 + 10) + (100 + 10) = 394 <= 410


def test_a_third_vessel_that_overflows_is_refused_naming_the_others():
    existing = [
        stay(WEST, ATLANTIS, "2026-07-01", "2026-07-10", id=1),
        stay(WEST, BARGE, "2026-07-01", "2026-07-10", id=2),
    ]
    r = check(stay(WEST, TIOGA, "2026-07-05", "2026-07-06", id=3), WEST, existing)
    assert r.verdict is Verdict.CONFLICT
    [f] = [f for f in r.findings if f.code is FindingCode.CAPACITY]
    assert set(f.related) == {1, 2}
    assert f.numbers["used_ft"] == 464 and f.numbers["capacity_ft"] == 410  # 284 + 110 + 70
    assert "R/V Atlantis" in f.message and "Barge Salt Dory" in f.message
    assert "2026-07-05..2026-07-06" in f.message


def test_clearance_counts_toward_capacity():
    # two 200' vessels are 400' of hull but 420' once each gets 10' of clearance
    existing = [stay(WEST, Vessel("M/V Alpha", 200, id=11), "2026-07-01", "2026-07-02")]
    r = check(stay(WEST, Vessel("M/V Beta", 200, id=12), "2026-07-01", "2026-07-02"), WEST, existing)
    assert r.verdict is Verdict.CONFLICT and codes(r) == [FindingCode.CAPACITY]


def test_capacity_is_checked_day_by_day_and_reported_as_one_run():
    # the barge leaves on the 3rd, so only the 1st..3rd are over capacity
    existing = [
        stay(WEST, ATLANTIS, "2026-07-01", "2026-07-10", id=1),
        stay(WEST, BARGE, "2026-07-01", "2026-07-03", id=2),
    ]
    r = check(stay(WEST, Vessel("M/V Big", 100, id=13), "2026-07-01", "2026-07-06", id=3), WEST, existing)
    caps = [f for f in r.findings if f.code is FindingCode.CAPACITY]
    assert len(caps) == 1 and "2026-07-01..2026-07-03" in caps[0].message
    assert caps[0].numbers["over_ft"] == 94  # 284 + 110 + 110 - 410


# --- slips ------------------------------------------------------------------
def test_a_slip_refuses_any_co_occupant_even_with_unknown_lengths():
    existing = [stay(SLIP, MYSTERY, "2026-07-01", "2026-07-05", id=1)]
    r = check(stay(SLIP, TINY, "2026-07-03", "2026-07-04", id=2), SLIP, existing)
    assert r.verdict is Verdict.CONFLICT
    assert codes(r) == [FindingCode.CAPACITY] and r.findings[0].related == (1,)
    assert "one occupant at a time" in r.findings[0].message


# --- events and closures ----------------------------------------------------
def test_an_event_takes_the_whole_berth():
    ev = event(FLOAT, "Community sail day", "2026-07-04", "2026-07-04")
    r = check(stay(FLOAT, TIOGA, "2026-07-03", "2026-07-05"), FLOAT, [ev])
    assert r.verdict is Verdict.CONFLICT
    [f] = r.findings
    assert f.code is FindingCode.CAPACITY and "'Community sail day' takes the whole of South Float East" in f.message
    # and the other way round: the event cannot be booked over the vessel
    r2 = check(ev, FLOAT, [stay(FLOAT, TIOGA, "2026-07-03", "2026-07-05")])
    assert r2.verdict is Verdict.CONFLICT and codes(r2) == [FindingCode.CAPACITY]


def test_a_closure_refuses_everything_and_refuses_to_displace_anyone():
    cl = closure(FACE, "Bollard replacement", "2026-07-01", "2026-07-07")
    r = check(stay(FACE, TIOGA, "2026-07-05", "2026-07-06"), FACE, [cl])
    assert r.verdict is Verdict.CONFLICT and codes(r) == [FindingCode.CLOSURE]
    r2 = check(cl, FACE, [stay(FACE, TIOGA, "2026-07-05", "2026-07-06")])
    assert r2.verdict is Verdict.CONFLICT and codes(r2) == [FindingCode.CLOSURE]
    assert "R/V Tioga" in r2.findings[0].message


# --- berths that come and go ------------------------------------------------
def test_a_berth_not_yet_in_service_is_refused():
    later = Berth("Marsh Landing", 120, active_from=d("2027-01-01"), id=7)
    r = check(stay(later, TIOGA, "2026-12-30", "2027-01-02"), later, [])
    assert r.verdict is Verdict.CONFLICT and codes(r) == [FindingCode.INACTIVE_BERTH]
    assert r.findings[0].numbers["inactive_days"] == 2


# --- bookkeeping ------------------------------------------------------------
def test_cancelled_reservations_do_not_count():
    gone = stay(FACE, ATLANTIS, "2026-07-01", "2026-07-10", status="cancelled")
    r = check(stay(FACE, TIOGA, "2026-07-02", "2026-07-03"), FACE, [gone])
    assert r.verdict is Verdict.OK


def test_editing_a_reservation_does_not_conflict_with_its_old_self():
    old = stay(SLIP, TINY, "2026-07-01", "2026-07-03", id=42)
    edited = stay(SLIP, TINY, "2026-07-01", "2026-07-05", id=42)
    assert check(edited, SLIP, [old]).verdict is Verdict.OK


def test_an_unknown_length_on_the_berth_makes_the_verdict_unknown_not_ok():
    existing = [stay(WEST, MYSTERY, "2026-07-01", "2026-07-10", id=1)]
    r = check(stay(WEST, TIOGA, "2026-07-05", "2026-07-06", id=2), WEST, existing)
    assert r.verdict is Verdict.UNKNOWN and r.blocking
    assert codes(r) == [FindingCode.UNKNOWN_OCCUPANT_LENGTH] and r.findings[0].related == (1,)


def test_rafting_is_mentioned_when_a_neighbour_allows_it():
    existing = [stay(FLOAT, RAFTER, "2026-07-01", "2026-07-05", id=1)]  # 55 + 10
    r = check(stay(FLOAT, TIOGA, "2026-07-02", "2026-07-03", id=2), FLOAT, existing)  # + 60 + 10 = 135 > 90
    assert r.verdict is Verdict.CONFLICT
    notes = [f for f in r.findings if f.code is FindingCode.RAFTING_NOTE]
    assert len(notes) == 1 and notes[0].severity is Severity.INFO and "S/V Far Horizon" in notes[0].message


# --- suggestions ------------------------------------------------------------
def test_suggestions_offer_the_smallest_fitting_berth_first():
    wanted = stay(FACE, Vessel("M/V Visitor", 120, id=20), "2026-07-01", "2026-07-03")
    out = suggest_berths(wanted, BERTHS, [])
    assert [s.berth.name for s in out] == ["North Pier East", "North Pier West"]
    # the candidate's own berth is never offered as an alternative to itself
    assert "North Pier Face" not in [s.berth.name for s in suggest_berths(stay(FACE, TINY, "2026-07-01", "2026-07-01"), BERTHS, [])]


def test_suggestions_skip_berths_that_are_closed_or_full():
    existing = [
        closure(EAST, "Float rebuild", "2026-06-01", "2026-08-31"),
        stay(WEST, ATLANTIS, "2026-07-01", "2026-07-10"),
        stay(WEST, BARGE, "2026-07-01", "2026-07-10"),
    ]
    wanted = stay(FACE, Vessel("M/V Visitor", 120, id=20), "2026-07-01", "2026-07-03")
    assert suggest_berths(wanted, BERTHS, existing) == []  # East closed, West full (524 > 410)
    maybe = suggest_berths(wanted, BERTHS, existing, include_unknown=True)
    assert [s.berth.name for s in maybe] == ["Small craft slip"]


# --- the audit over history -------------------------------------------------
def test_audit_finds_the_over_capacity_days_the_misfits_and_the_unknowns():
    history = [
        stay(WEST, ATLANTIS, "2017-07-01", "2017-07-10", id=1),
        stay(WEST, BARGE, "2017-07-01", "2017-07-10", id=2),
        stay(WEST, Vessel("M/V Big", 100, id=30), "2017-07-09", "2017-07-12", id=3),  # 504 > 410 on the 9th, 10th
        stay(FACE, ATLANTIS, "2017-08-01", "2017-08-02", id=4),  # 274' on a 75' face
        stay(SLIP, MYSTERY, "2017-08-01", "2017-08-02", id=5),  # unknown length
        closure(EAST, "Ultrasonic pier test", "2017-09-01", "2017-09-03", id=6),
        stay(EAST, TIOGA, "2017-09-02", "2017-09-02", id=7),
        stay(FLOAT, MYSTERY, "2017-10-01", "2017-10-02", id=8),  # shared day with a missing length
        stay(FLOAT, TINY, "2017-10-02", "2017-10-03", id=9),
    ]
    report = audit(BERTHS, history)
    assert [(l.day.isoformat(), l.over_by_ft) for l in report.over_capacity] == [
        ("2017-07-09", 94),
        ("2017-07-10", 94),
    ]
    assert [r.id for r, _ in report.misfits] == [4]
    assert sorted(r.id for r in report.unknown_length) == [5, 8]
    assert [(c.title, r.id) for c, r in report.closure_conflicts] == [("Ultrasonic pier test", 7)]
    assert [l.day.isoformat() for l in report.unverifiable] == ["2017-10-02"]
    assert report.counts == {
        "over_capacity_days": 2,
        "misfits": 1,
        "unknown_length": 2,
        "closure_conflicts": 1,
        "unverifiable_days": 1,
        "inactive": 0,
        "orphaned": 0,
    }


def test_day_loads_include_empty_days_for_drawing():
    loads = day_loads(FLOAT, [stay(FLOAT, TIOGA, "2026-07-02", "2026-07-03")], days("2026-07-01", "2026-07-04"))
    assert [len(l.occupants) for l in loads] == [0, 1, 1, 0]
    assert loads[0].used_ft == 0 and loads[1].used_ft == 70


# --- names and construction -------------------------------------------------
def test_name_key_folds_case_and_slashes_but_keeps_different_names_apart():
    assert name_key("Barge SALT DORY") == name_key("Barge Salt Dory")
    assert name_key("OS/V Silver Skua") == name_key("OSV Silver Skua")
    assert name_key("R/V Quiet Tern") != name_key("R/V Quiet Heron")


def test_a_vessel_reservation_needs_a_vessel_and_an_event_needs_a_title():
    with pytest.raises(ValueError):
        Reservation(1, ReservationKind.VESSEL, days("2026-07-01", "2026-07-01"))
    with pytest.raises(ValueError):
        Reservation(1, ReservationKind.EVENT, days("2026-07-01", "2026-07-01"))


# --- what the reviewers asked for ------------------------------------------
def test_an_event_conflicts_with_a_vessel_whatever_its_length():
    # the event takes the whole berth, so no length could make this fit
    ev = event(FLOAT, "Community sail day", "2026-07-04", "2026-07-04", id=1)
    r = check(ev, FLOAT, [stay(FLOAT, MYSTERY, "2026-07-03", "2026-07-05", id=2)])
    assert r.verdict is Verdict.CONFLICT and FindingCode.CAPACITY in codes(r)
    r2 = check(stay(FLOAT, MYSTERY, "2026-07-03", "2026-07-05", id=2), FLOAT, [ev])
    assert r2.verdict is Verdict.CONFLICT and FindingCode.CAPACITY in codes(r2)


def test_audit_counts_an_event_over_a_mystery_vessel_as_over_capacity():
    history = [event(FLOAT, "Sail day", "2017-07-04", "2017-07-04", id=1),
               stay(FLOAT, MYSTERY, "2017-07-03", "2017-07-05", id=2)]
    report = audit(BERTHS, history)
    assert [l.day.isoformat() for l in report.over_capacity] == ["2017-07-04"]
    assert report.unverifiable == ()


def test_known_lengths_that_already_overflow_are_a_conflict_even_with_an_unknown_neighbour():
    existing = [stay(WEST, ATLANTIS, "2026-07-01", "2026-07-10", id=1),  # 284
                stay(WEST, BARGE, "2026-07-01", "2026-07-10", id=2),  # 110
                stay(WEST, MYSTERY, "2026-07-01", "2026-07-10", id=3)]  # ?
    r = check(stay(WEST, TIOGA, "2026-07-05", "2026-07-06", id=4), WEST, existing)  # + 70 = 464 known
    assert r.verdict is Verdict.CONFLICT
    [f] = [f for f in r.findings if f.code is FindingCode.CAPACITY]
    assert "at least 464'" in f.message and f.numbers["used_ft"] == 464 and f.numbers["days"] == 2


def test_a_new_reservation_does_not_mistake_another_unsaved_one_for_itself():
    other = stay(SLIP, TINY, "2026-07-01", "2026-07-03", id=None)
    new = stay(SLIP, TINY, "2026-07-01", "2026-07-03", id=None)
    assert check(new, SLIP, [other]).verdict is Verdict.CONFLICT
    assert check(new, SLIP, [new]).verdict is Verdict.OK  # the very same object is itself


def test_two_unknown_neighbours_are_both_named_even_before_they_are_saved():
    existing = [stay(WEST, MYSTERY, "2026-07-01", "2026-07-02", id=None),
                stay(WEST, Vessel("F/V Pale Strand", None, id=7), "2026-07-01", "2026-07-02", id=None)]
    r = check(stay(WEST, TIOGA, "2026-07-01", "2026-07-02", id=None), WEST, existing)
    assert codes(r) == [FindingCode.UNKNOWN_OCCUPANT_LENGTH] * 2


def test_audit_flags_a_double_booked_slip_without_needing_lengths():
    history = [stay(SLIP, TINY, "2017-08-01", "2017-08-02", id=1),
               stay(SLIP, MYSTERY, "2017-08-02", "2017-08-03", id=2)]
    report = audit(BERTHS, history)
    [load] = report.over_capacity
    assert load.day == d("2017-08-02") and load.over_capacity and report.unverifiable == ()


def test_audit_reports_reservations_on_unknown_berths_instead_of_dropping_them():
    ghost = Berth("Ghost pier", 50, id=99)
    history = [stay(ghost, ATLANTIS, "2017-07-01", "2017-07-02", id=1)]
    report = audit([FACE], history)
    assert [r.id for r in report.orphaned] == [1] and report.counts["orphaned"] == 1


def test_audit_reports_stays_on_berths_out_of_service():
    old = Berth("Old float", 80, active_to=d("2020-01-01"), id=8)
    report = audit([old], [stay(old, TINY, "2026-07-01", "2026-07-02", id=1)])
    assert [(r.id, f.code) for r, f in report.inactive] == [(1, FindingCode.INACTIVE_BERTH)]


def test_audit_refuses_duplicate_or_missing_berth_ids():
    with pytest.raises(ValueError):
        audit([FACE, Berth("Twin", 10, id=FACE.id)], [])
    with pytest.raises(ValueError):
        audit([Berth("Unsaved", 10)], [])


def test_a_definite_conflict_outranks_a_missing_length():
    cl = closure(FACE, "Bollard replacement", "2026-07-01", "2026-07-07", id=1)
    r = check(stay(FACE, MYSTERY, "2026-07-05", "2026-07-06"), FACE, [cl])
    assert r.verdict is Verdict.CONFLICT
    assert codes(r) == [FindingCode.CLOSURE, FindingCode.UNKNOWN_VESSEL_LENGTH]


def test_over_capacity_days_are_reported_once_per_run():
    # the barge leaves after the 2nd, another arrives on the 4th: two runs, the 3rd is fine
    existing = [stay(WEST, ATLANTIS, "2026-07-01", "2026-07-10", id=1),
                stay(WEST, BARGE, "2026-07-01", "2026-07-02", id=2),
                stay(WEST, Vessel("Barge Two", 100, id=31), "2026-07-04", "2026-07-05", id=3)]
    r = check(stay(WEST, Vessel("M/V Big", 100, id=13), "2026-07-01", "2026-07-05", id=4), WEST, existing)
    caps = [f for f in r.findings if f.code is FindingCode.CAPACITY]
    assert [(f.day.isoformat(), f.related) for f in caps] == [("2026-07-01", (1, 2)), ("2026-07-04", (1, 3))]


def test_a_retired_berth_refuses_days_after_its_last_day_in_service():
    old = Berth("Old float", 80, active_to=d("2026-06-30"), id=8)
    r = check(stay(old, TINY, "2026-06-29", "2026-07-02"), old, [])
    assert codes(r) == [FindingCode.INACTIVE_BERTH]
    assert r.findings[0].numbers["inactive_days"] == 2 and r.findings[0].day == d("2026-07-01")
    assert old.is_active_on(d("2026-06-30"))  # the last day still counts


def test_suggestions_for_an_event_need_no_lengths_and_put_unmeasured_berths_last():
    ev = event(FACE, "Community sail day", "2026-07-01", "2026-07-01")
    out = suggest_berths(ev, BERTHS, [stay(SLIP, TINY, "2026-07-01", "2026-07-01")])
    assert [s.berth.name for s in out] == ["South Float East", "North Pier East", "North Pier West", "Small craft slip"]


def test_suggestions_rank_a_sure_berth_above_a_smaller_uncertain_one():
    existing = [stay(EAST, MYSTERY, "2026-07-01", "2026-07-02")]  # makes the 240' face UNKNOWN
    out = suggest_berths(stay(FACE, TINY, "2026-07-01", "2026-07-02"), BERTHS, existing, include_unknown=True)
    assert [s.berth.name for s in out][:2] == ["North Finger Pier 2", "South Float East"]
    assert [s.berth.name for s in out if s.result.verdict is Verdict.UNKNOWN] == ["North Pier East", "Small craft slip"]


def test_two_closures_may_overlap_but_a_closure_displaces_an_event():
    divers = closure(FACE, "Divers", "2026-07-05", "2026-07-09", id=1)
    assert check(closure(FACE, "Bollards", "2026-07-01", "2026-07-07"), FACE, [divers]).verdict is Verdict.OK
    r = check(closure(FACE, "Bollards", "2026-07-01", "2026-07-07"), FACE,
              [event(FACE, "Regatta", "2026-07-05", "2026-07-05", id=2)])
    assert codes(r) == [FindingCode.CLOSURE] and "Regatta" in r.findings[0].message
    assert audit(BERTHS, [divers, closure(FACE, "Bollards", "2026-07-01", "2026-07-07", id=3)]).closure_conflicts == ()


def test_an_event_on_a_slip_is_refused_like_any_second_occupant():
    r = check(event(SLIP, "Dinghy race", "2026-07-03", "2026-07-04"), SLIP,
              [stay(SLIP, TINY, "2026-07-01", "2026-07-03", id=1)])
    assert codes(r) == [FindingCode.CAPACITY] and r.findings[0].numbers == {"days": 1}
    r2 = check(event(UNMEASURED, "Dinghy race", "2026-07-03", "2026-07-04"), UNMEASURED,
               [stay(UNMEASURED, MYSTERY, "2026-07-01", "2026-07-03", id=2)])
    assert r2.verdict is Verdict.CONFLICT  # not UNKNOWN: no length is needed


def test_a_pier_face_filled_to_the_foot_is_not_over_capacity():
    existing = [stay(WEST, ATLANTIS, "2026-07-01", "2026-07-01", id=1)]  # 274 + 10
    fits = check(stay(WEST, Vessel("M/V Snug", 116, id=40), "2026-07-01", "2026-07-01"), WEST, existing)  # + 126 = 410
    over = check(stay(WEST, Vessel("M/V Snug", 117, id=40), "2026-07-01", "2026-07-01"), WEST, existing)
    assert fits.verdict is Verdict.OK
    assert over.verdict is Verdict.CONFLICT and over.findings[0].numbers["over_ft"] == 1


def test_a_lone_vessel_close_to_the_berth_length_is_a_fit_question_not_a_capacity_one():
    loads = day_loads(FACE, [stay(FACE, Vessel("M/V Snug", 70, id=41), "2026-07-01", "2026-07-01")], days("2026-07-01", "2026-07-01"))
    assert not loads[0].over_capacity and not loads[0].unverifiable


def test_suggestions_see_every_existing_reservation_for_every_berth():
    existing = iter([closure(EAST, "Float rebuild", "2026-06-01", "2026-08-31"),
                     stay(WEST, ATLANTIS, "2026-07-01", "2026-07-10"), stay(WEST, BARGE, "2026-07-01", "2026-07-10")])
    wanted = stay(FACE, Vessel("M/V Visitor", 120, id=20), "2026-07-01", "2026-07-03")
    assert suggest_berths(wanted, BERTHS, existing) == []


def test_audit_ignores_cancelled_reservations():
    history = [stay(FACE, ATLANTIS, "2017-07-01", "2017-07-02", id=1, status="cancelled"),
               closure(FACE, "Bollards", "2017-07-01", "2017-07-02", id=2, status="cancelled"),
               stay(FACE, TIOGA, "2017-07-01", "2017-07-02", id=3)]
    assert audit(BERTHS, history).counts["misfits"] == 0
    assert audit(BERTHS, history).counts["closure_conflicts"] == 0


def test_a_cancelled_candidate_is_always_fine():
    r = check(stay(SLIP, ATLANTIS, "2026-07-01", "2026-07-02", status="cancelled"), SLIP,
              [stay(SLIP, TINY, "2026-07-01", "2026-07-02", id=1)])
    assert r.verdict is Verdict.OK and codes(r) == [FindingCode.CANCELLED]


def test_a_candidate_that_rafts_is_named_in_the_note():
    r = check(stay(FLOAT, RAFTER, "2026-07-02", "2026-07-03", id=2), FLOAT,
              [stay(FLOAT, TIOGA, "2026-07-01", "2026-07-05", id=1)])
    [note] = [f for f in r.findings if f.code is FindingCode.RAFTING_NOTE]
    assert note.related == (2,) and "S/V Far Horizon" in note.message


def test_reservations_on_other_berths_are_not_in_the_way():
    elsewhere = [stay(WEST, ATLANTIS, "2026-07-01", "2026-07-02"), closure(WEST, "Bollards", "2026-07-01", "2026-07-02")]
    assert check(stay(FACE, TIOGA, "2026-07-01", "2026-07-02"), FACE, elsewhere).verdict is Verdict.OK


def test_disjoint_ranges_have_no_intersection_and_touching_ones_share_one_day():
    assert days("2026-07-01", "2026-07-03").intersection(days("2026-07-04", "2026-07-06")) is None
    both = days("2026-07-01", "2026-07-03").intersection(days("2026-07-03", "2026-07-06"))
    assert both == days("2026-07-03", "2026-07-03") and str(both) == "2026-07-03"


def test_only_saved_berths_can_be_checked_or_suggested():
    with pytest.raises(ValueError):
        check(stay(WEST, TINY, "2026-07-01", "2026-07-01"), FACE, [])  # different berth
    with pytest.raises(ValueError):
        suggest_berths(stay(FACE, TINY, "2026-07-01", "2026-07-01"), [Berth("Unsaved pier", 500)], [])
    with pytest.raises(ValueError):
        check(Reservation(0, ReservationKind.VESSEL, days("2026-07-01", "2026-07-01"), vessel=TINY), Berth("Unsaved", 50), [])


def test_an_unknown_candidate_is_asked_for_its_length_once():
    r = check(stay(WEST, MYSTERY, "2026-07-01", "2026-07-02"), WEST, [stay(WEST, TIOGA, "2026-07-01", "2026-07-02", id=1)])
    assert codes(r) == [FindingCode.UNKNOWN_VESSEL_LENGTH]


def test_a_berth_with_no_length_is_reported_once_when_shared():
    channel = Berth("Unmeasured face", None, id=9)  # linear, no length
    r = check(stay(channel, TINY, "2026-07-01", "2026-07-02"), channel, [stay(channel, TIOGA, "2026-07-01", "2026-07-02", id=1)])
    assert r.verdict is Verdict.UNKNOWN and codes(r) == [FindingCode.UNKNOWN_BERTH_LENGTH]


def test_values_from_a_database_row_are_made_real_enums_and_real_lengths():
    slip = Berth("Slip 3", 40.0, capacity_mode="exclusive", id=1)
    assert slip.capacity_mode is CapacityMode.EXCLUSIVE
    r = check(Reservation(1, "vessel", days("2026-07-01", "2026-07-01"), vessel=TINY), slip,
              [stay(slip, TINY, "2026-07-01", "2026-07-01", id=5)])
    assert r.verdict is Verdict.CONFLICT
    for bad in (float("nan"), 0, -5, float("inf")):
        with pytest.raises(ValueError):
            Vessel("Bad", bad)
        with pytest.raises(ValueError):
            Berth("Bad", bad)
    with pytest.raises(ValueError):
        Berth("Bad", 10, clearance_ft=-1)
    with pytest.raises(ValueError):
        Berth("Bad", 10, capacity_mode="sideways")


def test_an_event_cannot_carry_a_vessel_and_a_reservation_needs_a_berth_id():
    with pytest.raises(ValueError):
        Reservation(1, ReservationKind.EVENT, days("2026-07-01", "2026-07-01"), title="Sail day", vessel=TINY)
    with pytest.raises(ValueError):
        Reservation(None, ReservationKind.VESSEL, days("2026-07-01", "2026-07-01"), vessel=TINY)
