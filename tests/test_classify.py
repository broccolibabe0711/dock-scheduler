"""The cell classifier: what a grid cell's text means."""
from dock.classify import CellKind, classify_cell, title_case, vessel_name


def test_vessel_names_normalise_case_and_prefix():
    assert vessel_name("Barge SALT DORY") == ("Barge", "Barge Salt Dory")
    assert vessel_name("OS/V Silver Skua") == ("OSV", "OSV Silver Skua")
    assert vessel_name("r/v golden compass") == ("R/V", "R/V Golden Compass")
    assert vessel_name("Community sail day") is None


def test_curated_phrases_win_over_keywords():
    assert classify_cell("Float rebuild - no usage permitted").kind is CellKind.CLOSURE
    assert classify_cell("Community sail day").label == "Community sail day"
    assert classify_cell("Bunker barge").kind is CellKind.VESSEL
    assert classify_cell("Fuel truck").kind is CellKind.NOTE


def test_notes_drop_their_times():
    assert classify_cell("ETA 1200").label == "ETA"
    assert classify_cell("Departs 0600").label == "Departure"
    assert classify_cell("Bunkering 1000").label == "Bunkering"
    assert classify_cell("Delayed due to weather").kind is CellKind.NOTE


def test_unseen_text_is_low_confidence_not_an_error():
    c = classify_cell("Something nobody has written before")
    assert c.kind is CellKind.OTHER and c.confidence == "low"
    assert classify_cell("Crane test").kind is CellKind.CLOSURE  # keyword fallback


def test_title_case_keeps_hyphens():
    assert title_case("WESTERN-CURRENT dory") == "Western-Current Dory"
