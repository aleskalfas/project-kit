"""What the capability's checks answer with: summary lines and findings.

Both the validator (`_lib/check.py`, the `software-analysis:artefacts` member of
`pkit validate`) and the number comparison (`_lib/numbers.py`, `pkit analysis
check-numbers`) answer in this shape: a finding is a severity, a location —
a path, `path:/json/pointer`, or `path#id` for an entry — and a message
(ADR-058 point 1). An `error` fails; a `warning` asks for attention and a
`report` states what an owning record says is reported rather than judged —
both are said and never fail (ADR-058 point 2).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

ERROR, WARNING, REPORT = "error", "warning", "report"


@dataclass(frozen=True)
class Finding:
    severity: str
    location: str
    message: str

    def as_json(self) -> dict[str, str]:
        return {"severity": self.severity, "location": self.location, "message": self.message}


@dataclass
class Outcome:
    """What a check answers: summary lines and findings."""

    summary: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == ERROR]

    def document(self) -> dict[str, Any]:
        """The findings document a validator answers with (ADR-058)."""
        return {"summary": self.summary, "findings": [f.as_json() for f in self.findings]}

    def lines(self) -> list[str]:
        """The read view: the summary, then each finding under its location."""
        out = list(self.summary)
        for finding in self.findings:
            out.append(f"  {finding.severity:<7}{finding.location}")
            out.append(f"    → {finding.message}")
        return out


def at(location: str, pointer: str) -> str:
    """A location, and a JSON Pointer into what it holds."""
    return f"{location}:{pointer}" if pointer else location
