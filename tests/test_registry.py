"""The registry reader, run against the real sample workbook."""
from pathlib import Path

import openpyxl
import pytest

from dock.registry import read_registry, registry_vessels

SAMPLE = Path(__file__).resolve().parents[1] / "data" / "Dock Schedule - Synthetic Sample.xlsx"


@pytest.fixture(scope="module")
def entries():
    wb = openpyxl.load_workbook(SAMPLE, read_only=True)
    return read_registry(wb)


def test_every_named_entry_has_a_length(entries):
    named = [e for e in entries if not e.unnamed]
    assert len(entries) == 168 and len(named) == 166
    assert all(e.length_ft is not None for e in named)


def test_a_known_vessel_reads_correctly(entries):
    [drift] = [e for e in entries if e.name == "R/V High Drift"]
    assert drift.length_ft == 120 and drift.type_prefix == "R/V"
    assert "Coastal Survey Partners" in drift.operators
    assert any("@example.com" in c for c in drift.contacts)


def test_fragments_fold_into_the_vessel_above(entries):
    # Science row 4 is R/V High Drift; rows 5-7 are lone phones/emails/captains
    [drift] = [e for e in entries if e.name == "R/V High Drift"]
    assert len(drift.contacts) >= 5


def test_conflicting_lengths_leave_the_vessel_unknown(entries):
    vessels, issues = registry_vessels(entries)
    by_name = {v.name: v for v in vessels}
    assert by_name["R/V High Reef"].length_ft is None
    assert by_name["M/V Deep Reef"].length_ft is None
    assert len(issues) == 2 and len(vessels) == 164


def test_notes_become_flags(entries):
    vessels, _ = registry_vessels(entries)
    assert any(v.rafts_ok for v in vessels)
