"""Domain objects for the dock scheduler.

Plain, immutable data classes: no database, no web framework. Everything the
rules engine (rules.py) needs in order to decide whether a booking is allowed
lives here, so the rules can be tested with nothing but Python.

Vocabulary
----------
Berth        a place a vessel ties up, with a length in feet and a capacity mode
Vessel       a named craft whose length may be unknown
Reservation  a berth occupied for an inclusive range of days by a vessel,
             an event (community sail day) or a closure (maintenance)
Finding      one reason a reservation is refused, cannot be judged, or is
             worth a warning; produced by rules.check()
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Iterator


class CapacityMode(str, Enum):
    """How a berth is shared.

    LINEAR: a pier face. Several vessels tie up end to end; their lengths plus
    clearance between them must not exceed the face. This is how the 410-foot
    North Pier West is used in the legacy schedule.

    EXCLUSIVE: a slip. One occupant at a time, whatever its length.
    """

    LINEAR = "linear"
    EXCLUSIVE = "exclusive"


class ReservationKind(str, Enum):
    VESSEL = "vessel"  # a named craft occupying part of a berth
    EVENT = "event"  # community sail day, campus event...; takes the whole berth
    CLOSURE = "closure"  # maintenance; nothing may use the berth


class Severity(str, Enum):
    ERROR = "error"  # the booking breaks a rule
    UNKNOWN = "unknown"  # a rule could not be evaluated (a length is missing)
    WARNING = "warning"
    INFO = "info"


class Verdict(str, Enum):
    OK = "ok"
    CONFLICT = "conflict"
    UNKNOWN = "unknown"


class FindingCode(str, Enum):
    INACTIVE_BERTH = "inactive_berth"
    CLOSURE = "closure"
    FIT = "fit"
    UNKNOWN_VESSEL_LENGTH = "unknown_vessel_length"
    UNKNOWN_BERTH_LENGTH = "unknown_berth_length"
    UNKNOWN_OCCUPANT_LENGTH = "unknown_occupant_length"
    CAPACITY = "capacity"
    RAFTING_NOTE = "rafting_note"
    CANCELLED = "cancelled"


def fmt_ft(value: float) -> str:
    """Format feet the way the schedule writes them: 410'."""
    return f"{value:g}'"


def _checked_length(value: float | None, what: str) -> float | None:
    """A length is None (unknown) or a finite positive number of feet.

    NaN, zero and negative numbers would pass every comparison silently, so
    they are refused here, at the edge, once.
    """
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{what} must be a number of feet or None, not {value!r}")
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{what} must be a finite positive number of feet, not {value!r}")
    return float(value)


def name_key(name: str) -> str:
    """Identity of a vessel name: case-insensitive and punctuation-free.

    'Barge SALT DORY' and 'Barge Salt Dory' -> 'barge salt dory'
    'OS/V Silver Skua' and 'OSV Silver Skua' -> 'osv silver skua'
    'R/V Quiet Tern' and 'R/V Quiet Heron' stay different.
    """
    flat = name.lower().replace("/", "")
    return re.sub(r"[^a-z0-9]+", " ", flat).strip()


@dataclass(frozen=True, order=True)
class DayRange:
    """An inclusive range of calendar days: the 3rd to the 5th is three days.

    Inclusive because that is how the legacy grid reads: a name in the cells
    for the 3rd, 4th and 5th means the vessel was there on all three days.
    """

    start: date
    end: date

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError(f"end {self.end} is before start {self.start}")

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1

    def contains(self, day: date) -> bool:
        return self.start <= day <= self.end

    def overlaps(self, other: DayRange) -> bool:
        """True when the two ranges share at least one day."""
        return self.start <= other.end and other.start <= self.end

    def intersection(self, other: DayRange) -> DayRange | None:
        if not self.overlaps(other):
            return None
        return DayRange(max(self.start, other.start), min(self.end, other.end))

    def each_day(self) -> Iterator[date]:
        day = self.start
        while day <= self.end:
            yield day
            day += timedelta(days=1)

    def __str__(self) -> str:
        if self.start == self.end:
            return self.start.isoformat()
        return f"{self.start.isoformat()}..{self.end.isoformat()}"


@dataclass(frozen=True)
class Berth:
    """A place to tie up.

    length_ft is None when nobody has measured it yet (the finger-pier slips
    in the legacy data); the rules then answer UNKNOWN rather than guessing.
    Berths are effective-dated (active_from / active_to) because the set of
    berths changed over the 23 years of history.
    """

    name: str
    length_ft: float | None
    capacity_mode: CapacityMode = CapacityMode.LINEAR
    clearance_ft: float = 10.0
    active_from: date | None = None
    active_to: date | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        # Values arrive from SQLite as plain strings and numbers; make them
        # real enums and real lengths here so every rule can trust them.
        object.__setattr__(self, "capacity_mode", CapacityMode(self.capacity_mode))
        object.__setattr__(self, "length_ft", _checked_length(self.length_ft, "berth length"))
        if not math.isfinite(self.clearance_ft) or self.clearance_ft < 0:
            raise ValueError(f"clearance must be a finite number of feet >= 0, not {self.clearance_ft!r}")
        if self.active_from and self.active_to and self.active_to < self.active_from:
            raise ValueError("active_to is before active_from")

    def is_active_on(self, day: date) -> bool:
        if self.active_from is not None and day < self.active_from:
            return False
        if self.active_to is not None and day > self.active_to:
            return False
        return True

    @property
    def label(self) -> str:
        if self.length_ft is None:
            return self.name
        return f"{self.name} ({fmt_ft(self.length_ft)})"


@dataclass(frozen=True)
class Vessel:
    """A named craft.

    length_ft is None when the registry has no length for it, which is the
    common case in the legacy data (19 of 504 names had one).
    """

    name: str
    length_ft: float | None = None
    type_prefix: str | None = None  # R/V, M/V, F/V, S/V, M/Y, S/Y, OSV, Tug, Barge...
    draft_ft: float | None = None
    operator: str | None = None
    rafts_ok: bool = False  # the registry note "Will raft alongside if needed"
    notes: str = ""
    id: int | None = None

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("a vessel needs a name")
        object.__setattr__(self, "length_ft", _checked_length(self.length_ft, "vessel length"))
        object.__setattr__(self, "draft_ft", _checked_length(self.draft_ft, "vessel draft"))

    @property
    def key(self) -> str:
        return name_key(self.name)

    @property
    def label(self) -> str:
        if self.length_ft is None:
            return f"{self.name} (length unknown)"
        return f"{self.name} ({fmt_ft(self.length_ft)})"


@dataclass(frozen=True)
class Reservation:
    """A berth occupied for a range of days.

    kind VESSEL needs a vessel; EVENT and CLOSURE need a title and take the
    whole berth. status 'cancelled' keeps the row but removes it from every
    rule. override_reason records a human decision to save despite findings.
    legacy_ref points at the spreadsheet cell an imported row came from.
    """

    berth_id: int
    kind: ReservationKind
    days: DayRange
    vessel: Vessel | None = None
    title: str = ""
    status: str = "planned"  # planned | confirmed | cancelled
    override_reason: str | None = None
    source: str = "manual"  # manual | import
    legacy_ref: str | None = None
    notes: str = ""
    id: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", ReservationKind(self.kind))
        if isinstance(self.berth_id, bool) or not isinstance(self.berth_id, int):
            raise ValueError(f"a reservation needs a berth id, not {self.berth_id!r}")
        if self.kind is ReservationKind.VESSEL and self.vessel is None:
            raise ValueError("a vessel reservation needs a vessel")
        if self.kind is not ReservationKind.VESSEL and self.vessel is not None:
            raise ValueError(f"a {self.kind.value} reservation cannot have a vessel")
        if self.kind is not ReservationKind.VESSEL and not self.title:
            raise ValueError(f"a {self.kind.value} reservation needs a title")
        if self.status not in ("planned", "confirmed", "cancelled"):
            raise ValueError(f"unknown status {self.status!r}")

    @property
    def display_name(self) -> str:
        return self.vessel.name if self.vessel is not None else self.title

    @property
    def is_active(self) -> bool:
        return self.status != "cancelled"

    def occupied_ft(self, berth: Berth) -> float | None:
        """Feet of the berth this reservation uses on each of its days.

        Events and closures take the whole berth. A vessel takes its length
        plus the berth's clearance (fender room to its neighbour). None means
        unknown: a length is missing, and the rules refuse to guess.
        """
        if self.kind is not ReservationKind.VESSEL:
            return berth.length_ft
        if self.vessel.length_ft is None:
            return None
        return self.vessel.length_ft + berth.clearance_ft


@dataclass(frozen=True)
class Finding:
    """One reason. `message` is for people; `numbers` and `related` are for the UI.

    `numbers` by code: FIT has vessel_ft, berth_ft, over_ft. CAPACITY always
    has days; on a pier face it also has used_ft, capacity_ft, over_ft.
    INACTIVE_BERTH has inactive_days. Other codes carry no numbers.
    """

    code: FindingCode
    severity: Severity
    message: str
    day: date | None = None
    related: tuple[int | None, ...] = ()  # ids of the other reservations involved
    numbers: dict[str, float] = field(default_factory=dict, compare=False, hash=False)


@dataclass(frozen=True)
class CheckResult:
    verdict: Verdict
    findings: tuple[Finding, ...]

    @property
    def blocking(self) -> bool:
        """True unless the verdict is OK; saving then needs an override reason."""
        return self.verdict is not Verdict.OK

    def with_severity(self, severity: Severity) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.severity is severity)


@dataclass(frozen=True)
class DayLoad:
    """What sits on one berth on one day, and whether it fits.

    known_ft is the sum of the occupants whose length is known; unknown_count
    says how many are missing a length. If the known part alone exceeds the
    berth, the day is over capacity whatever the unknowns measure.
    """

    berth: Berth
    day: date
    occupants: tuple[Reservation, ...]
    known_ft: float
    unknown_count: int

    @property
    def used_ft(self) -> float | None:
        """The exact total, or None when a length is missing."""
        return self.known_ft if self.unknown_count == 0 else None

    @property
    def capacity_ft(self) -> float | None:
        return self.berth.length_ft

    @property
    def over_by_ft(self) -> float | None:
        """How far over the berth is (a lower bound when a length is missing)."""
        if self.capacity_ft is None:
            return None
        return max(0.0, self.known_ft - self.capacity_ft)

    @property
    def shared(self) -> bool:
        return len(self.occupants) > 1

    @property
    def over_capacity(self) -> bool:
        if not self.shared:
            return False
        if self.berth.capacity_mode is CapacityMode.EXCLUSIVE:
            return True
        if any(r.kind is not ReservationKind.VESSEL for r in self.occupants):
            return True  # an event or closure takes the whole berth
        return self.capacity_ft is not None and self.known_ft > self.capacity_ft

    @property
    def unverifiable(self) -> bool:
        """Shared, not provably over, but a length is missing so nobody can say."""
        if not self.shared or self.over_capacity:
            return False
        return self.capacity_ft is None or self.unknown_count > 0
