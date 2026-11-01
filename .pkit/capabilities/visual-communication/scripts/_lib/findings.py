"""Findings and their levels (visual-communication DEC-002 point 7).

A finding states one thing a check found. Its *level* is the policy's: it fails,
it asks for attention, or it states a fact. Whether a finding fails depends on
where it lies: in a file the project can correct, it takes the level its record
sets; in a released library version, which only its owner corrects, a failing
finding asks for attention instead. So the level is computed when a finding is
read (`severity`), never stored with it.

The validator document maps the levels onto the backbone's severities:
fails -> `error`, attention -> `warning`, fact -> `info`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

FAILS = "fails"
ATTENTION = "attention"
FACT = "fact"
LEVELS = (FAILS, ATTENTION, FACT)

SEVERITY = {FAILS: "error", ATTENTION: "warning", FACT: "info"}


@dataclass(frozen=True)
class Finding:
    """One finding.

    - `code`: a short stable name of what was found, such as `text-overflow`.
    - `level`: the level its record sets, where the project can correct it.
    - `message`: what was found, in plain words.
    - `file`: the file it lies in, relative to the project root, or "".
    - `where`: the field, item, token path or trace id within the file, or "".
    - `fix`: the file, field or item to change, and the command that mends it.
    - `library`: `<name>@<version>` when it lies in a library version, else "".
    - `who`: for a finding that asks for attention, who is expected to act.
    """

    code: str
    level: str
    message: str
    file: str = ""
    where: str = ""
    fix: str = ""
    library: str = ""
    who: str = ""
    extra: dict = field(default_factory=dict, compare=False)

    def __post_init__(self) -> None:
        if self.level not in LEVELS:
            raise ValueError(f"unknown level {self.level!r}")


def level_where(finding: Finding, released: bool) -> str:
    """The level a finding takes where it lies (DEC-002 point 7).

    A finding that would fail, in a released library version, asks for
    attention instead: only the library's owner corrects it, in a new release.
    """
    if finding.level == FAILS and finding.library and released:
        return ATTENTION
    return finding.level
