"""What meets each requirement (DEC-002 point 7): computed, never stored.

A use case lists in `requirements` each requirement it must meet, and a journey
those that bind its whole path. What meets a requirement is the use cases and
journeys in force that list it, worked out from those lists each time. The
requirement stores none of it, so it never goes stale. A page that shows a
requirement reads it here, through `pkit analysis met-by`.

- **Which requirements.** Every requirement the analysis holds, of the three
  kinds, withdrawn ones included with their status, or the one asked for.
- **Which listers.** Each use case and journey in force whose `requirements`
  holds the requirement's id, as `identity` spells it. A withdrawn one is
  history and meets nothing. One in force that lists a withdrawn requirement is
  shown under it, and `pkit analysis validate` refuses it.
- **Complete, or no answer.** A file in the places of the use cases, the
  journeys or the requirements that holds no artefact of its kind, such as one
  whose front matter does not parse, is no answer: what it lists, or which
  requirement it is, cannot be told, so a shorter answer would read as a true
  one. The check says what is wrong with the file.

The analysis is read through the backbone's reading, `pkit friction artefacts
--json` (`backbone.read_analysis`), of the working tree. Nothing is written.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from _lib.model import (
    JOURNEY,
    MUST_MEET,
    NOUN,
    REQUIREMENT,
    REQUIREMENTS,
    USE_CASE,
    Analysis,
    Artefact,
    identity,
    number_in,
)

#: The version of the document `--json` prints.
SCHEMA_VERSION = 1

#: The kinds that list the requirements they must meet, in the order they are shown.
LISTERS = (USE_CASE, JOURNEY)


class NoAnswer(Exception):
    """What meets a requirement cannot be told in full; the message says why."""


@dataclass(frozen=True)
class Met:
    """One requirement, and the use cases and journeys in force that list it."""

    requirement: Artefact
    by: tuple[Artefact, ...]


def met_by(analysis: Analysis, only: str | None = None) -> list[Met]:
    """Each requirement the analysis holds, or only `only`, with what lists it, ordered
    by number then path. Raises NoAnswer when a file of the places it reads cannot be
    read as its kind, or when `only` is no requirement the analysis holds."""
    unread = sorted(
        {
            *(s.path for s in analysis.strays if s.kind in (*LISTERS, *REQUIREMENTS)),
            *(
                path
                for path in analysis.unreadable
                if analysis.files.get(path) in (*LISTERS, *REQUIREMENTS)
            ),
        }
    )
    if unread:
        raise NoAnswer(
            f"{', '.join(unread)} cannot be read as {_one_of(unread)}, so what it lists, or "
            f"which requirement it is, cannot be told; `pkit analysis validate` says why"
        )
    requirements = [a for a in analysis.artefacts if a.kind in REQUIREMENTS and a.id]
    if only is not None:
        requirements = [a for a in requirements if identity(str(a.id)) == identity(only)]
        if not requirements:
            raise NoAnswer(f"no {REQUIREMENT} {only} in the analysis")
    listers = [a for a in analysis.artefacts if a.kind in LISTERS and not a.withdrawn]
    return [
        Met(requirement, tuple(_listing(listers, str(requirement.id))))
        for requirement in sorted(requirements, key=_order)
    ]


def _listing(listers: Sequence[Artefact], requirement_id: str) -> list[Artefact]:
    """The use cases, then the journeys, among `listers` whose `requirements` holds
    `requirement_id`, each ordered by number then path."""
    wanted = identity(requirement_id)
    found = [
        a
        for a in listers
        if any(isinstance(v, str) and identity(v) == wanted for v in _list(a.fields))
    ]
    return sorted(found, key=lambda a: (LISTERS.index(a.kind), *_order(a)))


def _list(fields: Mapping[str, Any]) -> list[Any]:
    listed = fields.get(MUST_MEET)
    return listed if isinstance(listed, list) else []


def _order(artefact: Artefact) -> tuple[int, str, str]:
    """By number, a number spelt otherwise as `identity` spells it, then by id and path."""
    spelt = number_in(str(artefact.id))
    number = int(spelt.split("-", 1)[1]) if spelt else 0
    return number, str(artefact.id), artefact.path


def _one_of(paths: Sequence[str]) -> str:
    return "an artefact of its place" if len(paths) == 1 else "artefacts of their places"


def document(found: Sequence[Met], shown_as: Mapping[str, str]) -> dict[str, Any]:
    """The `--json` document: `{schema_version, requirements}`, each requirement as
    `{id, kind, shown_as, title, status, path, met_by}`, and each entry of `met_by` as
    `{id, kind, title, path}`."""
    return {
        "schema_version": SCHEMA_VERSION,
        "requirements": [
            {
                **_entry(met.requirement),
                "shown_as": shown_as.get(met.requirement.kind),
                "status": met.requirement.fields.get("status"),
                "met_by": [_entry(lister) for lister in met.by],
            }
            for met in found
        ],
    }


def _entry(artefact: Artefact) -> dict[str, Any]:
    title = artefact.fields.get("title")
    return {
        "id": artefact.id,
        "kind": artefact.kind,
        "title": title if isinstance(title, str) else None,
        "path": artefact.path,
    }


def lines(found: Sequence[Met], shown_as: Mapping[str, str]) -> list[str]:
    """The answer for a person: each requirement's heading, `REQ-004 · Quality ·
    <title>`, marked when withdrawn, then what meets it, one line each, or `none`."""
    said: list[str] = []
    for met in found:
        requirement = met.requirement
        title = requirement.fields.get("title")
        heading = f"{requirement.id} · {shown_as.get(requirement.kind, NOUN[requirement.kind])}"
        heading += f" · {title}" if isinstance(title, str) else ""
        said.append(heading + (" (withdrawn)" if requirement.withdrawn else ""))
        if not met.by:
            said.append("  Met by: none")
            continue
        said.append("  Met by:")
        for lister in met.by:
            name = lister.fields.get("title")
            said.append(
                f"    {lister.id} — {name}" if isinstance(name, str) else f"    {lister.id}"
            )
    return said
