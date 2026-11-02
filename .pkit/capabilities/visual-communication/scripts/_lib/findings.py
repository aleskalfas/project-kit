"""Findings and their levels (visual-communication DEC-002 point 7).

A finding states one thing a check found. Its *level* is the policy's: it fails,
it asks for attention, or it states a fact. Whether a finding fails depends on
where it lies: in a file the project can correct, it takes the level its record
sets; in a released library version, which only its owner corrects, a failing
finding asks for attention instead, and names the library's owner as who is to
act (DEC-002 point 7). So the level, and that `who`, are worked out when a
finding is read (`as_read`), never stored with it.

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


def owner_of(library: str) -> str:
    """Who corrects a finding in the released library version `library`
    (`<name>@<version>`): the library's owner, in a new release."""
    name = library.partition("@")[0]
    return f"the owner of `{name}`, who corrects it in a new release"


def as_read(finding: Finding, released: bool) -> tuple[Finding, str]:
    """A finding as it reads where it lies, with its level there (`level_where`).
    A failing finding that asks for attention instead, in a released library
    version, names the library's owner as who is to act (DEC-002 point 7, DEC-005
    point 14). `released` says whether its version is released and still as it was
    released."""
    level = level_where(finding, released)
    if level != finding.level:
        return replace(finding, who=owner_of(finding.library)), level
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
