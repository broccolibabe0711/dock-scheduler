"""Read the messy "Science" and "Yachts" contact sheets into vessels.

Those sheets are the only place the workbook records vessel lengths
("R/V High Drift 120'", "LOA: 65', Draft: 4'"). They are contact lists that
drifted: many rows are continuation fragments (a lone phone number, an
email, a captain's name) that belong to the vessel row above, and values sit
under whatever column was handy. So cells are classified by their shape, not
by their column, and every non-vessel row is folded into the vessel above it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

from .classify import vessel_name
from .models import Vessel, name_key

_PREFIX_RE = re.compile(r"^(R/V|M/V|F/V|S/V|M/Y|S/Y|OS/V|OSV|USCGC|USCG|Tug|Barge)\b", re.I)
_LEN_RE = re.compile(r"\s+(\d+(?:\.\d+)?)\s*'\s*$")  # trailing 120'
_LOA_RE = re.compile(r"\bLOA:?\s*(\d+(?:\.\d+)?)\s*'", re.I)
_DRAFT_RE = re.compile(r"\bDraft:?\s*(\d+(?:\.\d+)?)\s*'", re.I)
_PHONE_RE = re.compile(r"^(?:(?:Cell|Work|Office|Tel|Phone|Fax|Mobile)\s*:?\s*)?(\+?\d[\d\s().-]{6,}\d)$", re.I)
_EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")
_URL_RE = re.compile(r"^https?://", re.I)
_CAPT_RE = re.compile(r"^(Capt\.?|Captain|Mr\.?|Ms\.?|Dr\.?)\s+\S", re.I)
_PERSON_RE = re.compile(r"^[A-Z][a-z]+(?:\s+[A-Z][a-z'-]+){1,2}$")
_ORG_WORDS = re.compile(
    r"\b(Institute|Charters?|Academy|Partners|Group|University|College|Agency|Services?|Trust|"
    r"School|Foundation|Offshore|Marine|Research|Fisheries|Inc\.?|LLC|Ltd\.?|Corp\.?|Company|Co\.|"
    r"Authority|Department|Laboratory|Lab)\b",
    re.I,
)
FLAG_RULES = [
    (re.compile(r"raft", re.I), "rafts_ok"),
    (re.compile(r"short visit", re.I), "short_visit"),
    (re.compile(r"shore power", re.I), "shore_power"),
    (re.compile(r"insurance", re.I), "insurance_pending"),
    (re.compile(r"no overnight crew", re.I), "no_overnight_crew"),
    (re.compile(r"scheduling file", re.I), "see_schedule_file"),
    (re.compile(r"contact captain", re.I), "contact_captain_on_arrival"),
    (re.compile(r"confirmed", re.I), "confirmed"),
    (re.compile(r"approved", re.I), "approved"),
    (re.compile(r"tentative|awaiting confirmation", re.I), "tentative"),
]
REGISTRY_SHEETS = ("Science", "Yachts")


@dataclass
class RegistryEntry:
    """One vessel row group from a registry sheet, before merging duplicates."""

    sheet: str
    row: int
    raw_name: str
    name: str = ""  # canonical, without the trailing length
    key: str = ""
    type_prefix: str | None = None
    length_ft: float | None = None
    loa_ft: float | None = None
    draft_ft: float | None = None
    operators: list[str] = field(default_factory=list)
    contacts: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    flags: set[str] = field(default_factory=set)
    unnamed: bool = False

    def add(self, cell: str) -> None:
        """File one cell's text under the right heading by its shape."""
        text = " ".join(str(cell).split())
        if not text:
            return
        if _URL_RE.match(text):
            return  # placeholder links carry no information
        if _EMAIL_RE.match(text) or _PHONE_RE.match(text) or _CAPT_RE.match(text):
            self._append(self.contacts, text)
        elif _LOA_RE.search(text) or _DRAFT_RE.search(text):
            m = _LOA_RE.search(text)
            if m and self.loa_ft is None:
                self.loa_ft = float(m.group(1))
            m = _DRAFT_RE.search(text)
            if m and self.draft_ft is None:
                self.draft_ft = float(m.group(1))
        elif any(rule.search(text) for rule, _ in FLAG_RULES):
            self._append(self.notes, text)
            self.flags.update(flag for rule, flag in FLAG_RULES if rule.search(text))
        elif _ORG_WORDS.search(text):
            self._append(self.operators, text)
        elif _PERSON_RE.match(text):
            self._append(self.contacts, text)
        else:
            self._append(self.notes, text)

    @staticmethod
    def _append(bucket: list[str], value: str) -> None:
        if value not in bucket:
            bucket.append(value)


def _is_vessel_cell(text: str) -> bool:
    return bool(_PREFIX_RE.match(text) or _LEN_RE.search(text) or _LOA_RE.search(text))


def read_registry(workbook) -> list[RegistryEntry]:
    """Walk the registry sheets of an openpyxl workbook and group rows into vessels."""
    entries: list[RegistryEntry] = []
    for sheet_name in REGISTRY_SHEETS:
        if sheet_name not in workbook.sheetnames:
            continue
        current: RegistryEntry | None = None
        for row_index, row in enumerate(workbook[sheet_name].iter_rows(values_only=True), start=1):
            cells = [" ".join(str(c).split()) if c is not None else "" for c in row]
            if not any(cells):
                continue  # blank rows do not end a group; fragments below still belong above
            first = cells[0]
            if row_index == 1 and first.upper() == "VESSEL":
                continue  # header row
            if _is_vessel_cell(first):
                current = _start_entry(sheet_name, row_index, first)
                entries.append(current)
                rest = cells[1:]
            else:
                rest = cells  # a continuation row: every cell belongs to the vessel above
            if current is not None:
                for cell in rest:
                    current.add(cell)
    return entries


def _start_entry(sheet: str, row: int, raw: str) -> RegistryEntry:
    entry = RegistryEntry(sheet=sheet, row=row, raw_name=raw)
    named = vessel_name(re.sub(_LEN_RE, "", raw))
    if named is None:
        # "LOA: 145', Draft: 12'" in the name column: a spec with no name
        entry.unnamed = True
        entry.add(raw)
        return entry
    entry.type_prefix, entry.name = named
    entry.key = name_key(entry.name)
    m = _LEN_RE.search(raw)
    if m:
        entry.length_ft = float(m.group(1))
    return entry


def registry_vessels(entries: Iterable[RegistryEntry]) -> tuple[list[Vessel], list[str]]:
    """Collapse entries into one Vessel per name.

    When two entries disagree on the length, the vessel keeps NO length and
    the disagreement is returned as an issue, because guessing which is right
    would defeat the fit check.
    """
    by_key: dict[str, list[RegistryEntry]] = {}
    for e in entries:
        if e.unnamed:
            continue
        by_key.setdefault(e.key, []).append(e)
    vessels: list[Vessel] = []
    issues: list[str] = []
    for key, group in by_key.items():
        lengths = sorted({e.length_ft for e in group if e.length_ft is not None})
        length = lengths[0] if len(lengths) == 1 else None
        if len(lengths) > 1:
            where = "; ".join(f"{e.sheet} row {e.row} ({e.raw_name})" for e in group)
            issues.append(f"{group[0].name}: registry lengths disagree {lengths}; left unknown. {where}")
        operators = [o for e in group for o in e.operators]
        notes = [n for e in group for n in e.notes]
        flags = set().union(*(e.flags for e in group))
        vessels.append(
            Vessel(
                name=group[0].name,
                length_ft=length,
                type_prefix=group[0].type_prefix,
                draft_ft=next((e.draft_ft for e in group if e.draft_ft is not None), None),
                operator=" / ".join(dict.fromkeys(operators)) or None,
                rafts_ok="rafts_ok" in flags,
                notes="; ".join(dict.fromkeys(notes)),
            )
        )
    return vessels, issues
