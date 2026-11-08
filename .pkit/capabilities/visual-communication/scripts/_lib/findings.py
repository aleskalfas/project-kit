"""Findings and their levels (visual-communication DEC-002 point 7, DEC-013 point 6).

A finding states one thing a check found. Its *level* is the policy's: it fails,
it asks for attention, or it states a fact. Whether a finding fails depends on
where it lies: in a file the project can correct, it takes the level its record
sets. In a library version the project does not correct, a failing finding asks
for attention instead, and names who corrects it (DEC-002 point 7):

- in a released version, still as it was released, the library's owner, in a new
  release;
- in a copy of a library the capability ships, released or not, whoever maintains
  the capability, since the command that brings the library in writes it as it is
  authored (DEC-013 point 6). A released copy whose files no longer match its hash
  is the project's to restore, so a finding in it keeps its level.

So the level, and that `who`, are worked out when a finding is read (`as_read`),
never stored with it. A finding the project corrects whether the version is
released or not names no version, so it keeps its level: a version that needs a
newer release of the capability is one (DEC-014 point 5).

The validator document maps the levels onto the backbone's severities:
fails -> `error`, attention -> `warning`, fact -> `info`.

A plugin's loss that nobody accepted is one finding, `loss`, whichever kind of
plugin reports it (DEC-005 point 9): `loss_finding` words it, and `accepted`
says whether an entry of `accept-losses` accepts it.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any

from _lib.plugins import seam

FAILS = "fails"
ATTENTION = "attention"
FACT = "fact"
LEVELS = (FAILS, ATTENTION, FACT)

SEVERITY = {FAILS: "error", ATTENTION: "warning", FACT: "info"}

#: What a plugin did with a loss, in words.
DID = {
    seam.APPROXIMATED: "approximates",
    seam.PICTURE: "draws as a picture",
    seam.LEFT_OUT: "leaves out",
    seam.REFUSED: "refuses",
}

#: Who a loss nobody accepted asks for attention (DEC-005 point 14).
AUTHOR = "the piece's author"

#: Who a finding names where the project corrects it, though it lies in a library folder.
PROJECT = "the project"


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
    - `who`: who is expected to act, for a finding that asks for attention, or for a
      failing one whose file lies in a library version but that the project corrects.
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


def level_where(finding: Finding, released: bool, *, shipped: bool = False) -> str:
    """The level a finding takes where it lies (DEC-002 point 7, DEC-013 point 6).

    A finding that would fail asks for attention instead in a library version the
    project does not correct: a released one (`released`), which only the library's
    owner corrects, in a new release; or a copy of a library the capability ships
    (`shipped`), which only whoever maintains the capability corrects.
    """
    if finding.level == FAILS and finding.library and (released or shipped):
        return ATTENTION
    return finding.level


def owner_of(library: str, *, shipped: bool = False) -> str:
    """Who corrects a finding in the library version `library` (`<name>@<version>`)
    that the project does not correct: whoever maintains the capability, in a copy of
    a library it ships (`shipped`); else the library's owner, in a new release."""
    name = library.partition("@")[0]
    if shipped:
        return f"whoever maintains the capability, who corrects `{name}` where it is authored"
    return f"the owner of `{name}`, who corrects it in a new release"


def as_read(finding: Finding, released: bool, *, shipped: bool = False) -> tuple[Finding, str]:
    """A finding as it reads where it lies, with its level there (`level_where`).
    A failing finding that asks for attention instead names who corrects it
    (`owner_of`, DEC-002 point 7, DEC-005 point 14, DEC-013 point 6). `released`
    says whether its version is released and still as it was released; `shipped`,
    whether it is a copy of a library the capability ships, other than a released
    copy whose files no longer match its hash."""
    level = level_where(finding, released, shipped=shipped)
    if level != finding.level:
        return replace(finding, who=owner_of(finding.library, shipped=shipped)), level
    return finding, level


def accepted(loss: seam.Loss, accepting: Sequence[Mapping[str, Any]]) -> bool:
    """Whether an entry of `accept-losses` accepts a loss: it names the plugin and what it
    loses."""
    return any(
        entry.get("plugin") == loss.plugin and entry.get("what") == loss.what for entry in accepting
    )


def loss_said(loss: seam.Loss, kind: str) -> str:
    """A loss in words: the plugin, its `kind` (`renderer`, `producer`), what it did, with
    what, and why."""
    return f"the {loss.plugin} {kind} {DID[loss.did]} `{loss.what}`: {loss.why}"


def loss_finding(loss: seam.Loss, kind: str, *, file: str, where: str) -> Finding:
    """A loss nobody accepted, which asks the piece's author for attention (DEC-005 points
    9 and 14). It is accepted where the output is declared, in the piece."""
    return Finding(
        "loss",
        ATTENTION,
        loss_said(loss, kind),
        file=file,
        where=where,
        fix=f"accept it under `accept-losses` with `plugin: {loss.plugin}`, `what: {loss.what}` "
        f"and a reason, or change what draws it",
        who=AUTHOR,
    )
