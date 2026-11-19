"""The check's findings, each with a severity from validation's shared set (COR-055 point 4).

A finding says one thing the check found: its severity, where it lies (a file relative to
the project root, with `#` and a JSON Pointer into it where it lies within), what was
found, in plain words, and its label, a short stable name of the kind of finding, which the
capability's README lists. The record that owns a check decides its severity
(lean-business DEC-002 point 14): a broken invariant is an `error`, the one severity that
fails validation; a guideline of the book, or a judgement gone stale, a `warning`.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

ERROR = "error"
WARNING = "warning"
INFO = "info"

#: The order findings print in, the failing first.
ORDER = {ERROR: 0, WARNING: 1, INFO: 2}


@dataclass(frozen=True)
class Finding:
    severity: str
    location: str
    message: str
    label: str

    def __post_init__(self) -> None:
        if self.severity not in ORDER:
            raise ValueError(f"unknown severity {self.severity!r}")

    def as_data(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "location": self.location,
            "message": self.message,
            "label": self.label,
        }


def at(rel: str, pointer: str = "") -> str:
    """Where a finding lies: the file `rel`, and the place `pointer` within it, such as
    `/verdicts/viability`."""
    return f"{rel}#{pointer}" if pointer else rel


def ordered(found: Iterable[Finding]) -> list[Finding]:
    """`found`, the failing first, then by where each lies, each kept once."""
    unique = list(dict.fromkeys(found))
    return sorted(unique, key=lambda f: (ORDER[f.severity], f.location, f.label, f.message))


def document(summary: list[str], found: Iterable[Finding]) -> dict[str, Any]:
    """The findings document validation reads: `{"summary": [...], "findings": [...]}`."""
    return {"summary": summary, "findings": [f.as_data() for f in ordered(found)]}
