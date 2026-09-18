"""The referee: every rule about whether a reservation may exist.

Pure functions over the objects in models.py: no database, no HTTP, no
clock. The API, the importer's audit and the harbor view all call these, so
the rules live in one place and one set of tests proves them.

The two questions the facility used to answer by staring at a grid:

    Does it fit?          fit_check()   vessel length vs berth length
    Is it double-booked?  check()       per day, occupied feet vs berth length
                                        (or "is anyone else there?" on a slip)

check() answers both for a candidate reservation and returns a verdict: OK,
CONFLICT, or UNKNOWN when a length a rule needs is missing. UNKNOWN is
deliberately not OK; the person booking is asked for the length instead.
A conflict that is certain without lengths (an event over a vessel, two
boats in one slip, a known sum that already overflows) is CONFLICT even when
other lengths are missing.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import date, timedelta
from typing import Iterable, Sequence

from .models import (
    Berth,
    CapacityMode,
    CheckResult,
    DayLoad,
    DayRange,
    Finding,
    FindingCode,
    Reservation,
    ReservationKind,
    Severity,
    Verdict,
    Vessel,
    fmt_ft,
)


def overlapping(candidate: Reservation, existing: Iterable[Reservation]) -> list[Reservation]:
    """Active reservations on the candidate's berth that share a day with it.

    The candidate itself is excluded (the same object, or the same saved id)
    so that editing a reservation never conflicts with its own old version.
    Two unsaved reservations (both id None) are never mistaken for each other.
    """
    return [
        r
        for r in existing
        if r.berth_id == candidate.berth_id
        and r.is_active
        and r is not candidate
        and not (candidate.id is not None and r.id == candidate.id)
        and r.days.overlaps(candidate.days)
    ]


def _vessel_of(r: Reservation) -> Vessel:
    if r.vessel is None:
        raise ValueError(f"vessel reservation {r.id} ({r.legacy_ref or r.display_name}) has no vessel")
    return r.vessel


def _both(a: Reservation, b: Reservation) -> DayRange:
    both = a.days.intersection(b.days)
    if both is None:
        raise RuntimeError("overlapping() returned a reservation that does not overlap")
    return both


def day_load(berth: Berth, occupants: Sequence[Reservation], day: date) -> DayLoad:
    """Add up the feet used by the occupants of one berth on one day."""
    known, unknown = 0.0, 0
    for r in occupants:
        ft = r.occupied_ft(berth)
        if ft is None:
            unknown += 1
        else:
            known += ft
    return DayLoad(berth=berth, day=day, occupants=tuple(occupants), known_ft=known, unknown_count=unknown)


def occupancy(berth: Berth, reservations: Iterable[Reservation]) -> dict[date, list[Reservation]]:
    """Map every day with at least one active occupant to its occupants.

    Built by walking each reservation's days once, so 23 years of history
    costs about (number of stays x average stay length) steps.
    """
    if berth.id is None:
        raise ValueError(f"berth {berth.name!r} has no id")
    by_day: dict[date, list[Reservation]] = defaultdict(list)
    for r in reservations:
        if r.berth_id != berth.id or not r.is_active:
            continue
        for day in r.days.each_day():
            by_day[day].append(r)
    return dict(by_day)


def day_loads(berth: Berth, reservations: Iterable[Reservation], days: DayRange) -> list[DayLoad]:
    """One DayLoad per day of the range, including empty days (for drawing)."""
    occ = occupancy(berth, (r for r in reservations if r.days.overlaps(days)))
    return [day_load(berth, occ.get(day, []), day) for day in days.each_day()]


def inactive_days(berth: Berth, days: DayRange) -> list[date]:
    return [d for d in days.each_day() if not berth.is_active_on(d)]


def fit_check(vessel: Vessel, berth: Berth) -> list[Finding]:
    """Does the vessel fit the berth? Unknown lengths give UNKNOWN, not a guess."""
    if vessel.length_ft is None:
        return [
            Finding(
                FindingCode.UNKNOWN_VESSEL_LENGTH,
                Severity.UNKNOWN,
                f"the length of {vessel.name} is not on file, so the fit cannot be "
                f"checked; enter its length overall",
            )
        ]
    if berth.length_ft is None:
        return [
            Finding(
                FindingCode.UNKNOWN_BERTH_LENGTH,
                Severity.UNKNOWN,
                f"{berth.name} has no recorded length, so the fit cannot be checked",
            )
        ]
    if vessel.length_ft > berth.length_ft:
        over = vessel.length_ft - berth.length_ft
        return [
            Finding(
                FindingCode.FIT,
                Severity.ERROR,
                f"{vessel.name} ({fmt_ft(vessel.length_ft)}) is {fmt_ft(over)} longer "
                f"than {berth.name} ({fmt_ft(berth.length_ft)})",
                numbers={"vessel_ft": vessel.length_ft, "berth_ft": berth.length_ft, "over_ft": over},
            )
        ]
    return []


def check(candidate: Reservation, berth: Berth, existing: Iterable[Reservation]) -> CheckResult:
    """Judge one candidate reservation against a berth and its other reservations.

    Rules, in order:
      1. the berth must be in service on every day (INACTIVE_BERTH)
      2. closures: a closed berth refuses everything, and a closure refuses
         to displace anyone (CLOSURE)
      3. fit: a vessel must not be longer than the berth (FIT); a missing
         length gives UNKNOWN_*_LENGTH instead of a guess
      4. capacity, per day: on a slip nobody else may be there; an event or
         closure takes the whole berth; on a pier face the occupied feet
         must not exceed the berth's length (CAPACITY)
      5. if capacity fails and a vessel involved is happy to raft, say so
         (RAFTING_NOTE): that is when an override is reasonable
    A cancelled candidate occupies nothing and is always OK.
    """
    if berth.id is None:
        raise ValueError("the berth has no id; save it before checking reservations against it")
    if candidate.berth_id != berth.id:
        raise ValueError("candidate is for a different berth")
    if not candidate.is_active:
        note = Finding(FindingCode.CANCELLED, Severity.INFO, "a cancelled reservation occupies nothing")
        return CheckResult(Verdict.OK, (note,))

    findings: list[Finding] = []

    # 1. in service?
    off = inactive_days(berth, candidate.days)
    if off:
        findings.append(
            Finding(
                FindingCode.INACTIVE_BERTH,
                Severity.ERROR,
                f"{berth.name} is not in service on {off[0].isoformat()} "
                f"({len(off)} of {candidate.days.days} day(s))",
                day=off[0],
                numbers={"inactive_days": len(off)},
            )
        )

    others = overlapping(candidate, existing)

    # 2. closures
    if candidate.kind is ReservationKind.CLOSURE:
        for r in others:
            if r.kind is ReservationKind.CLOSURE:
                continue  # two closures may overlap
            both = _both(candidate, r)
            findings.append(
                Finding(
                    FindingCode.CLOSURE,
                    Severity.ERROR,
                    f"closing {berth.name} for '{candidate.title}' would displace "
                    f"{r.display_name} ({both})",
                    day=both.start,
                    related=(r.id,),
                )
            )
    else:
        for r in others:
            if r.kind is ReservationKind.CLOSURE:
                both = _both(candidate, r)
                findings.append(
                    Finding(
                        FindingCode.CLOSURE,
                        Severity.ERROR,
                        f"{berth.name} is closed for '{r.title}' {r.days} (overlap {both})",
                        day=both.start,
                        related=(r.id,),
                    )
                )

    # 3. fit
    if candidate.kind is ReservationKind.VESSEL:
        findings.extend(fit_check(_vessel_of(candidate), berth))

    # 4. capacity
    co_occupants = [r for r in others if r.kind is not ReservationKind.CLOSURE]
    if co_occupants and candidate.kind is not ReservationKind.CLOSURE:
        capacity = _capacity_findings(candidate, berth, co_occupants)
        if any(f.code is FindingCode.UNKNOWN_BERTH_LENGTH for f in findings):
            # the fit check already said the berth has no length; say it once
            capacity = [f for f in capacity if f.code is not FindingCode.UNKNOWN_BERTH_LENGTH]
        findings.extend(capacity)

    # 5. rafting
    if candidate.kind is ReservationKind.VESSEL and any(f.code is FindingCode.CAPACITY for f in findings):
        rafters = [r for r in co_occupants if r.vessel is not None and r.vessel.rafts_ok]
        if _vessel_of(candidate).rafts_ok:
            rafters.append(candidate)
        if rafters:
            names = ", ".join(r.display_name for r in rafters)
            findings.append(
                Finding(
                    FindingCode.RAFTING_NOTE,
                    Severity.INFO,
                    f"{names} can raft alongside; an override with a reason may be appropriate",
                    related=tuple(r.id for r in rafters),
                )
            )

    return CheckResult(verdict=_verdict(findings), findings=tuple(findings))


def _capacity_findings(
    candidate: Reservation, berth: Berth, co_occupants: Sequence[Reservation]
) -> list[Finding]:
    findings: list[Finding] = []

    # A slip: anyone else there is a conflict, no lengths needed.
    if berth.capacity_mode is CapacityMode.EXCLUSIVE:
        for r in co_occupants:
            both = _both(candidate, r)
            findings.append(
                Finding(
                    FindingCode.CAPACITY,
                    Severity.ERROR,
                    f"{berth.name} holds one occupant at a time and {r.display_name} is there {both}",
                    day=both.start,
                    related=(r.id,),
                    numbers={"days": both.days},
                )
            )
        return findings

    # An event or closure takes the whole berth: a conflict without arithmetic.
    if candidate.kind is not ReservationKind.VESSEL:
        for r in co_occupants:
            both = _both(candidate, r)
            findings.append(
                Finding(
                    FindingCode.CAPACITY,
                    Severity.ERROR,
                    f"'{candidate.title}' takes the whole of {berth.name}, and {r.display_name} is there {both}",
                    day=both.start,
                    related=(r.id,),
                    numbers={"days": both.days},
                )
            )
        return findings
    vessels_present: list[Reservation] = []
    for r in co_occupants:
        if r.kind is ReservationKind.VESSEL:
            vessels_present.append(r)
            continue
        both = _both(candidate, r)
        findings.append(
            Finding(
                FindingCode.CAPACITY,
                Severity.ERROR,
                f"'{r.title}' takes the whole of {berth.name} {both}",
                day=both.start,
                related=(r.id,),
                numbers={"days": both.days},
            )
        )
    if not vessels_present:
        return findings

    if berth.length_ft is None:
        names = ", ".join(r.display_name for r in vessels_present)
        findings.append(
            Finding(
                FindingCode.UNKNOWN_BERTH_LENGTH,
                Severity.UNKNOWN,
                f"{berth.name} has no recorded length, so its capacity cannot be checked against {names}",
                related=tuple(r.id for r in vessels_present),
            )
        )
        return findings

    # A pier face: per-day arithmetic. The known lengths are summed; if that
    # sum already exceeds the face it is a conflict whatever the unknown
    # neighbours measure. Only when the known part fits and something is
    # unknown do we answer UNKNOWN. Consecutive days with the same neighbours
    # are reported as one finding.
    unknown_reported: set[int] = set()  # id() of the reservation object
    runs: list[list] = []  # [first_day, last_day, neighbours, known_ft, unknown_count]
    for day in candidate.days.each_day():
        present = [r for r in vessels_present if r.days.contains(day)]
        if not present:
            continue
        load = day_load(berth, [*present, candidate], day)
        if load.known_ft > berth.length_ft:
            neighbours = tuple(present)
            if runs and runs[-1][1] == day - timedelta(days=1) and runs[-1][2] == neighbours:
                runs[-1][1] = day
            else:
                runs.append([day, day, neighbours, load.known_ft, load.unknown_count])
        elif load.unknown_count:
            for r in present:
                if r.occupied_ft(berth) is None and id(r) not in unknown_reported:
                    unknown_reported.add(id(r))
                    findings.append(
                        Finding(
                            FindingCode.UNKNOWN_OCCUPANT_LENGTH,
                            Severity.UNKNOWN,
                            f"{r.display_name} is on {berth.name} the same days and its "
                            f"length is not on file, so the total cannot be checked",
                            day=day,
                            related=(r.id,),
                        )
                    )

    for first, last, neighbours, known, unknown in runs:
        parts = " + ".join(_part(r, berth) for r in neighbours) + f" + {_part(candidate, berth)}"
        at_least = "at least " if unknown else ""
        tail = f" ({unknown} length(s) not on file, so the real total is higher)" if unknown else ""
        findings.append(
            Finding(
                FindingCode.CAPACITY,
                Severity.ERROR,
                f"{berth.name} over capacity on {DayRange(first, last)}: {parts} = "
                f"{at_least}{fmt_ft(known)} > {fmt_ft(berth.length_ft)}{tail}",
                day=first,
                related=tuple(r.id for r in neighbours),
                numbers={
                    "days": (last - first).days + 1,
                    "used_ft": known,
                    "capacity_ft": berth.length_ft,
                    "over_ft": known - berth.length_ft,
                },
            )
        )
    return findings


def _part(r: Reservation, berth: Berth) -> str:
    """How one occupant appears in a capacity sum: 'R/V Tioga (60' + 10')'."""
    if r.kind is not ReservationKind.VESSEL:
        if berth.length_ft is None:
            return f"{r.title} (whole berth, length unknown)"
        return f"{r.title} (whole berth, {fmt_ft(berth.length_ft)})"
    vessel = _vessel_of(r)
    if vessel.length_ft is None:
        return f"{vessel.name} (length unknown)"
    return f"{vessel.name} ({fmt_ft(vessel.length_ft)} + {fmt_ft(berth.clearance_ft)})"


def _verdict(findings: Sequence[Finding]) -> Verdict:
    if any(f.severity is Severity.ERROR for f in findings):
        return Verdict.CONFLICT
    if any(f.severity is Severity.UNKNOWN for f in findings):
        return Verdict.UNKNOWN
    return Verdict.OK


@dataclass(frozen=True)
class Suggestion:
    berth: Berth
    result: CheckResult


def suggest_berths(
    candidate: Reservation,
    berths: Iterable[Berth],
    existing: Iterable[Reservation],
    include_unknown: bool = False,
) -> list[Suggestion]:
    """Rank the berths where the candidate could go instead.

    The candidate's own berth is not offered. Smallest fitting berth first,
    so the long faces stay free for the ships that need them; then the
    fewest findings. Berths whose verdict is UNKNOWN are left out unless
    asked for, because "maybe" is not a suggestion.
    """
    existing = list(existing)
    out: list[Suggestion] = []
    for berth in berths:
        if berth.id is None:
            raise ValueError(f"berth {berth.name!r} has no id; only saved berths can be suggested")
        if berth.id == candidate.berth_id:
            continue
        result = check(replace(candidate, berth_id=berth.id), berth, existing)
        if result.verdict is Verdict.OK or (include_unknown and result.verdict is Verdict.UNKNOWN):
            out.append(Suggestion(berth, result))
    out.sort(
        key=lambda s: (
            s.result.verdict is not Verdict.OK,
            s.berth.length_ft if s.berth.length_ft is not None else float("inf"),
            len(s.result.findings),
        )
    )
    return out


@dataclass(frozen=True)
class AuditReport:
    """The rules run over a whole history (the imported 23 years, for one)."""

    over_capacity: tuple[DayLoad, ...]  # one per berth-day over capacity
    unverifiable: tuple[DayLoad, ...]  # shared days where a length is missing
    misfits: tuple[tuple[Reservation, Finding], ...]  # vessel longer than its berth
    unknown_length: tuple[Reservation, ...]  # vessel stays whose fit could not be checked
    closure_conflicts: tuple[tuple[Reservation, Reservation], ...]  # (closure, displaced)
    inactive: tuple[tuple[Reservation, Finding], ...]  # stays on a berth out of service
    orphaned: tuple[Reservation, ...]  # stays whose berth is not in the list given

    @property
    def counts(self) -> dict[str, int]:
        return {
            "over_capacity_days": len(self.over_capacity),
            "misfits": len(self.misfits),
            "unknown_length": len(self.unknown_length),
            "closure_conflicts": len(self.closure_conflicts),
            "unverifiable_days": len(self.unverifiable),
            "inactive": len(self.inactive),
            "orphaned": len(self.orphaned),
        }


def audit(berths: Iterable[Berth], reservations: Iterable[Reservation]) -> AuditReport:
    """Run every rule over every active reservation, berth by berth.

    Output order is fixed (berth id, then date) so reports are reproducible.
    A reservation whose berth is not in `berths` is reported as orphaned,
    never silently skipped.
    """
    berth_by_id: dict[int, Berth] = {}
    for b in berths:
        if b.id is None:
            raise ValueError(f"berth {b.name!r} has no id")
        if b.id in berth_by_id:
            raise ValueError(f"duplicate berth id {b.id}: {berth_by_id[b.id].name!r} and {b.name!r}")
        berth_by_id[b.id] = b

    by_berth: dict[int, list[Reservation]] = defaultdict(list)
    orphaned: list[Reservation] = []
    for r in reservations:
        if not r.is_active:
            continue
        if r.berth_id in berth_by_id:
            by_berth[r.berth_id].append(r)
        else:
            orphaned.append(r)

    over: list[DayLoad] = []
    unverifiable: list[DayLoad] = []
    misfits: list[tuple[Reservation, Finding]] = []
    unknown: list[Reservation] = []
    closure_conflicts: list[tuple[Reservation, Reservation]] = []
    inactive: list[tuple[Reservation, Finding]] = []

    def order(r: Reservation):
        return (r.days.start, r.id if r.id is not None else 0, r.display_name)

    for berth_id in sorted(by_berth):
        berth = berth_by_id[berth_id]
        rs = sorted(by_berth[berth_id], key=order)
        for r in rs:
            off = inactive_days(berth, r.days)
            if off:
                inactive.append((r, Finding(
                    FindingCode.INACTIVE_BERTH, Severity.ERROR,
                    f"{berth.name} is not in service on {off[0].isoformat()} ({len(off)} of {r.days.days} day(s))",
                    day=off[0], numbers={"inactive_days": len(off)},
                )))
            if r.kind is ReservationKind.VESSEL:
                for f in fit_check(_vessel_of(r), berth):
                    if f.severity is Severity.ERROR:
                        misfits.append((r, f))
                    elif f.severity is Severity.UNKNOWN:
                        unknown.append(r)
        for closure in (r for r in rs if r.kind is ReservationKind.CLOSURE):
            for r in rs:
                if r.kind is not ReservationKind.CLOSURE and r.days.overlaps(closure.days):
                    closure_conflicts.append((closure, r))
        occ = occupancy(berth, [r for r in rs if r.kind is not ReservationKind.CLOSURE])
        for day in sorted(occ):
            load = day_load(berth, occ[day], day)
            if load.over_capacity:
                over.append(load)
            elif load.unverifiable:
                unverifiable.append(load)

    return AuditReport(
        over_capacity=tuple(over),
        unverifiable=tuple(unverifiable),
        misfits=tuple(misfits),
        unknown_length=tuple(unknown),
        closure_conflicts=tuple(closure_conflicts),
        inactive=tuple(inactive),
        orphaned=tuple(sorted(orphaned, key=order)),
    )
