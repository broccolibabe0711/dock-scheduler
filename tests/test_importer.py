"""The importer, on a tiny fixture with one block per era, and on the real sample."""
from datetime import date
from pathlib import Path

import pytest

from dock.importer import import_workbook
from dock.models import ReservationKind
from tests.fixtures.make_fixture import build

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "Dock Schedule - Synthetic Sample.xlsx"


@pytest.fixture(scope="module")
def tiny(tmp_path_factory):
    return import_workbook(build(tmp_path_factory.mktemp("wb") / "tiny.xlsx"))


def by_name(result, name):
    return [r for r in result.reservations if r.display_name == name]


def test_spans_come_from_fills_repeats_and_merges(tiny):
    [dory] = by_name(tiny, "F/V Swift Dory")
    assert (dory.days.start, dory.days.end) == (date(1998, 8, 2), date(1998, 8, 4))
    assert dory.legacy_ref.endswith(":fill_run") and dory.vessel.length_ft == 32
    [horizon] = by_name(tiny, "S/V Far Horizon")  # case normalised
    assert horizon.days.days == 2 and horizon.legacy_ref.endswith(":repeat")
    [compass] = by_name(tiny, "R/V Golden Compass")
    assert (compass.days.start, compass.days.end) == (date(2009, 1, 2), date(2009, 1, 5))
    assert compass.legacy_ref.endswith(":merge") and compass.vessel.length_ft == 120


def test_a_merge_past_the_month_end_is_cut_and_logged(tiny):
    [harbor] = by_name(tiny, "M/V Northern Harbor")
    assert harbor.days.end == date(2009, 1, 31)
    assert any(i.kind == "merge_beyond_month" for i in tiny.issues)


def test_month_split_stays_are_stitched(tiny):
    [long_stay] = by_name(tiny, "R/V Long Stay")
    assert (long_stay.days.start, long_stay.days.end) == (date(1998, 8, 31), date(1998, 9, 1))
    assert "stitched" in long_stay.notes and tiny.stats["stitched"] == 1


def test_notes_become_annotations_not_reservations(tiny):
    assert by_name(tiny, "ETA 1200") == []
    [note] = [a for a in tiny.annotations if a.text == "ETA 1200"]
    assert note.label == "ETA" and note.day == date(1998, 8, 10)


def test_events_and_closures_keep_their_kind(tiny):
    [sail] = by_name(tiny, "Community sail day")
    assert sail.kind is ReservationKind.EVENT and sail.days.days == 2
    [bollard] = by_name(tiny, "Bollard replacement")
    assert bollard.kind is ReservationKind.CLOSURE and bollard.days.days == 3


def test_a_mislabelled_month_is_moved_to_its_sheet_year(tiny):
    [tug] = by_name(tiny, "Tug Blue Fathom")
    assert tug.days.start == date(2010, 11, 3)
    assert any(i.kind == "mislabelled_month" and i.sheet == "2010" for i in tiny.issues)


def test_the_explicit_day_one_row_wins_and_the_disagreement_is_logged(tiny):
    # the header row implies day 1 in column C; the row above says D; D is used and the conflict logged
    [conflict] = [i for i in tiny.issues if i.kind == "day_row_conflict"]
    assert "day 1 at D" in conflict.message and "day 1 at C" in conflict.message and "using row 11" in conflict.message
    assert sum(1 for i in tiny.issues if i.kind == "header_junk") == 2  # the two vessel names in the header


def test_a_tour_row_without_a_date_is_logged_not_dropped(tiny):
    [issue] = [i for i in tiny.issues if i.kind == "unreadable_tour_row"]
    assert "Requires shore power" in issue.message and len(tiny.tours) == 2


def test_group_rows_are_berths_without_a_length(tiny):
    finger = next(b for b in tiny.berths if b.name == "North Finger Piers")
    assert finger.length_ft is None and finger.active_from == date(2014, 1, 1)
    [tiny_one] = by_name(tiny, "F/V Tiny One")
    assert tiny_one.berth_id == finger.id


def test_duplicate_rows_and_stray_text_are_logged_not_guessed(tiny):
    kinds = tiny.issue_counts()
    assert kinds["duplicate_berth_row"] == 1 and kinds["unlabelled_row_text"] == 1
    assert by_name(tiny, "M/V Second Boat")  # the second row still imports


def test_tours_and_summary_are_read(tiny):
    assert [(t.day, t.people, t.approximate, t.organisation) for t in tiny.tours] == [
        (date(2018, 4, 29), 6, True, "Regional Fisheries Agency"),
        (date(2018, 5, 2), 4, False, "Harbor Institute"),
    ]
    assert tiny.usage_summary[("North Pier West", 2009)] == 4


@pytest.mark.slow
def test_the_real_sample_matches_the_data_study():
    r = import_workbook(SAMPLE)
    sources = {}
    for s in r.raw_stays:
        sources[s.source] = sources.get(s.source, 0) + 1
    # The Ruby study counted 2,244 cell runs including 78 outside the day columns;
    # those are logged, not read, and the damaged 2010 blocks now use their
    # explicit day-1 row, which moves a few runs. Everything else agrees.
    assert len(r.raw_stays) == 2164 and sources == {"single": 785, "fill_run": 732, "merge": 591, "repeat": 56}
    assert r.stats["totals"]["reservations"] == 1982 and r.stats["stitched"] == 122
    assert r.issue_counts()["cell_outside_day_columns"] == 80 and r.issue_counts()["day_row_conflict"] == 2
    assert [b.name for b in r.berths] == [
        "North Pier West", "North Pier Face", "North Pier East", "Inner Channel",
        "South Float West", "South Float East", "Small craft slips (institution boats)", "North Finger Piers",
    ]
    counts = r.issue_counts()
    assert counts["mislabelled_month"] == 2 and counts["duplicate_block"] == 3 and counts["merge_beyond_month"] == 3
    assert len(r.tours) == 32 and r.usage_summary[("North Pier West", 2012)] == 648
