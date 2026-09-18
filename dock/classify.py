"""Classify the text found in a schedule cell.

A cell in the legacy grid can hold a vessel name, a non-vessel event, a
closure of the berth, or an operational note that is not a booking at all.
The importer needs to know which, and it needs "Barge SALT DORY" and
"Barge Salt Dory" to be the same vessel.

Rules, in order: a recognised vessel prefix wins; then a curated table of the
non-vessel phrases found in 23 years of the sample; then generic patterns for
notes; then keyword fallbacks marked low confidence. A value the rules have
never seen still gets an answer, with confidence "low", so a person can find
it in the issue list.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class CellKind(str, Enum):
    VESSEL = "vessel"
    EVENT = "event"
    CLOSURE = "closure"
    NOTE = "note"
    OTHER = "other"


@dataclass(frozen=True)
class CellClass:
    kind: CellKind
    label: str  # canonical: "Barge Salt Dory", "Community sail day", "ETA"
    type_prefix: str | None = None
    confidence: str = "high"  # high | medium | low
    rationale: str = ""


# Vessel type prefixes as they appear in the sheets (lower case) -> canonical.
PREFIXES: dict[str, str] = {
    "r/v": "R/V",
    "m/v": "M/V",
    "f/v": "F/V",
    "s/v": "S/V",
    "m/y": "M/Y",
    "s/y": "S/Y",
    "osv": "OSV",
    "os/v": "OSV",
    "tug": "Tug",
    "barge": "Barge",
    "uscgc": "USCG",
    "uscg": "USCG",
}
_PREFIX_RE = re.compile(
    r"^(" + "|".join(re.escape(k) for k in PREFIXES) + r")\s+(.+)$", re.IGNORECASE
)

# Non-vessel phrases seen in the sample, curated by hand: kind, label, confidence, why.
OVERRIDES: dict[str, tuple[CellKind, str, str, str]] = {
    "bunker barge": (CellKind.VESSEL, "Bunker barge", "medium", "unnamed service craft occupying the berth"),
    "emergency port call": (CellKind.EVENT, "Emergency port call", "medium", "unnamed vessel visit occupies the berth"),
    "fuel truck": (CellKind.NOTE, "Fuel truck", "medium", "shoreside service; annotation, not a booking"),
    "wire spooling": (CellKind.NOTE, "Wire spooling", "medium", "deck operation on a berthed vessel"),
    "returns from sea trials": (CellKind.NOTE, "Returns from sea trials", "high", "movement annotation"),
    "dock inspection": (CellKind.CLOSURE, "Dock inspection", "medium", "inspection restricts berth use"),
    "crane access - berth closed": (CellKind.CLOSURE, "Crane access - berth closed", "high", "says berth closed"),
    "science stroll": (CellKind.EVENT, "Science stroll", "high", "public outreach activity"),
    "film crew on dock": (CellKind.EVENT, "Film crew on dock", "high", "non-vessel activity on the dock"),
    "donor reception": (CellKind.EVENT, "Donor reception", "high", "institutional function"),
    "public open house": (CellKind.EVENT, "Public open house", "high", "public activity"),
    "dive training": (CellKind.EVENT, "Dive training", "high", "training activity"),
    "safety training (ribs)": (CellKind.EVENT, "Safety training (RIBs)", "high", "training activity"),
    "rescue drill": (CellKind.EVENT, "Rescue drill", "high", "drill activity"),
    "holiday": (CellKind.EVENT, "Holiday", "high", "calendar event, no vessel"),
    "community sail day": (CellKind.EVENT, "Community sail day", "high", "community activity"),
    "campus event": (CellKind.EVENT, "Campus event", "high", "institutional activity"),
    "student tour": (CellKind.EVENT, "Student tour", "high", "tour activity"),
    "road race - access limited": (CellKind.EVENT, "Road race - access limited", "high", "external event limits access"),
    "float rebuild - no usage permitted": (CellKind.CLOSURE, "Float rebuild", "high", "maintenance, usage forbidden"),
    "bollard replacement, west face": (CellKind.CLOSURE, "Bollard replacement", "high", "maintenance work on the berth"),
    "dock maintenance - restricted access": (CellKind.CLOSURE, "Dock maintenance", "high", "maintenance restricts access"),
    "ultrasonic pier test": (CellKind.CLOSURE, "Ultrasonic pier test", "high", "structural testing of the pier"),
    "concrete work near test wells": (CellKind.CLOSURE, "Concrete work", "high", "construction work"),
    "utility work on pier face": (CellKind.CLOSURE, "Utility work", "high", "utility work on the berth"),
    "pier repair - no docking": (CellKind.CLOSURE, "Pier repair", "high", "repair, docking forbidden"),
    "paving near dock entrance": (CellKind.CLOSURE, "Paving near dock entrance", "medium", "works near the dock, access limited"),
}

_NOTE_PATTERNS = [
    (re.compile(r"^(eta|etd|arrival|arrives|departs|departure)\b", re.I), "arrival/departure time annotation"),
    (re.compile(r"^(fueling|bunkering|provisioning|load equipment|water/slops pumping)\b", re.I), "service operation annotation"),
    (re.compile(r"^(delayed|touch and go)\b", re.I), "schedule/movement annotation"),
]
_EVENT_WORDS = re.compile(r"\b(training|drill|tour|event|day|reception|open house)\b", re.I)
_CLOSURE_WORDS = re.compile(r"\b(repair|maintenance|closed|rebuild|replacement|work|test|inspection)\b", re.I)


def title_case(text: str) -> str:
    """'SALT DORY' -> 'Salt Dory'; keeps hyphenated words tidy."""
    return " ".join(
        "-".join(part[:1].upper() + part[1:].lower() for part in word.split("-"))
        for word in text.split()
    )


def vessel_name(text: str) -> tuple[str, str] | None:
    """('R/V', 'R/V Golden Compass') for 'R/V GOLDEN COMPASS'; None if no prefix."""
    m = _PREFIX_RE.match(text.strip())
    if not m:
        return None
    prefix = PREFIXES[m.group(1).lower()]
    return prefix, f"{prefix} {title_case(m.group(2).strip())}"


def _note_label(text: str) -> str:
    base = re.sub(r"\s*@?\s*\d{3,4}$", "", text)  # "Bunkering 1000" -> "Bunkering"
    base = re.sub(r"\s+(am|pm)$", "", base, flags=re.I)
    low = base.lower()
    if low.startswith("fueling"):
        return "Fueling"
    if low.startswith("bunkering"):
        return "Bunkering"
    if re.match(r"eta\b", low):
        return "ETA"
    if re.match(r"etd\b", low):
        return "ETD"
    if re.match(r"(arrival|arrives)\b", low):
        return "Arrival"
    if re.match(r"(departure|departs)\b", low):
        return "Departure"
    return base


def classify_cell(text: str) -> CellClass:
    """Decide what a grid cell's text is. Never raises; unknown text is OTHER/low."""
    raw = " ".join(text.split())
    key = raw.lower()
    if key in OVERRIDES:
        kind, label, confidence, why = OVERRIDES[key]
        prefix = "Barge" if key == "bunker barge" else None
        return CellClass(kind, label, prefix, confidence, why)
    named = vessel_name(raw)
    if named:
        prefix, label = named
        return CellClass(CellKind.VESSEL, label, prefix, "high", "recognised vessel type prefix")
    for pattern, why in _NOTE_PATTERNS:
        if pattern.match(raw):
            return CellClass(CellKind.NOTE, _note_label(raw), None, "high", why)
    if _EVENT_WORDS.search(raw):
        return CellClass(CellKind.EVENT, raw, None, "low", "event keyword, not curated")
    if _CLOSURE_WORDS.search(raw):
        return CellClass(CellKind.CLOSURE, raw, None, "low", "closure keyword, not curated")
    return CellClass(CellKind.OTHER, raw, None, "low", "no rule matched")
