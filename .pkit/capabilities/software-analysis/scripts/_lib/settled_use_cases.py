"""This capability's contribution to the work-tracking role's use-case point (DEC-001 point 8).

`pkit::work-tracking:use-cases` is the data point the provider of the
`pkit::work-tracking` role defines: the use cases settled on the default
branch, one entry per use case — its `id`, its `title`, `active` or
`withdrawn`, and the `path` of the document that describes it (version 1 of
the point's companion schema, which its provider ships). The capability maps
its use cases onto that shape and keeps its own model to itself:

- **settled state, and nothing else**: the use cases the default branch holds
  at the commit the backbone resolves it to (`pkit repository base --json`, its
  `default_branch` and never its `base`), read through the backbone's reading
  of that commit (`pkit friction artefacts --at <commit> --json`). The working
  tree and the branch at hand are never read, and the filler asks git nothing
  itself;
- **every use case that settled, withdrawn ones included, but none whose id
  the project freed**: a withdrawn use case stays in its file, and its id
  names it for good — the project frees only an id it declares nothing cites,
  of a use case no file holds any longer (DEC-001 point 3). It is given with
  `status: withdrawn`; any other use case is `active`;
- **its id as the analysis writes it**: `UC-007` is `UC-007` in the point, so
  a citation of the id is a citation of the use case.

**Complete, or no answer.** The point's fillers answer in full or not at all,
and a command filler fails closed whatever the point's policy (COR-052 point
6): a shorter list would read as use cases that do not exist. So each of these
is no answer — raised, and the command exits non-zero with nothing on standard
output:

- the backbone gives no reading of the default branch, or none of its commit;
- the default branch resolves to no commit here, though it has one;
- a file in the use cases' place at that commit cannot be read as a use case:
  its front matter does not parse, it has none, or it holds no document of the
  kind;
- a use case there carries no id or title of the shape its schema asks, or two
  hold one id.

**Empty is an answer.** A default branch nothing has been committed to holds
no use case, and neither does a commit with no use cases in it: the filler
answers the empty list, which says there are none yet.
"""

from __future__ import annotations

import subprocess
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from _lib import backbone, schemas
from _lib.model import USE_CASE, Analysis, Unreadable, number_of

#: The point, and the version of its companion schema this contribution targets —
#: the package's `contributes` entry declares the same, and a test holds the two equal.
POINT = "pkit::work-tracking:use-cases"
POINT_VERSION = 1

#: The point's two statuses; every lifecycle value but `withdrawn` maps to `active`.
ACTIVE = "active"
WITHDRAWN = "withdrawn"


class NoAnswer(Exception):
    """The settled use cases cannot be read in full: the filler gives no answer."""


def read(root: Path, run: backbone.Runner = subprocess.run) -> list[dict[str, str]]:
    """The use cases the default branch holds at its commit, as the point's entries.
    Empty where the default branch has no commit yet. Raises NoAnswer when a
    reading fails or a use case there cannot be read in full."""
    try:
        branch = backbone.settled(root, run=run).default_branch
        if branch.unborn:
            return []
        if branch.commit is None:
            raise NoAnswer(
                branch.problem or f"the default branch {branch.name!r} resolves to no commit"
            )
        return use_cases(backbone.read_analysis(root, at=branch.commit, run=run))
    except Unreadable as exc:
        raise NoAnswer(str(exc)) from exc


def use_cases(analysis: Analysis) -> list[dict[str, str]]:
    """The point's entries for the use cases of `analysis`, in the order of their
    numbers. Raises NoAnswer when a file of the use cases' place cannot be read as
    a use case, or a use case carries no id or title of its schema's shape, or two
    hold one id."""
    for path, kind in sorted(analysis.files.items()):
        if kind == USE_CASE and path in analysis.unreadable:
            raise NoAnswer(f"{path}'s front matter does not parse")
    for stray in analysis.strays:
        if stray.kind == USE_CASE:
            raise NoAnswer(f"{stray.path} {stray.why}")
    pattern = schemas.id_pattern(USE_CASE)
    held: dict[str, dict[str, str]] = {}
    for artefact in analysis.of_kind(USE_CASE):
        title = artefact.fields.get("title")
        if artefact.id is None or not pattern.match(artefact.id):
            raise NoAnswer(f"{artefact.path} gives no use-case id")
        if not isinstance(title, str) or not title.strip():
            raise NoAnswer(f"{artefact.path} ({artefact.id}) gives no title")
        if artefact.id in held:
            raise NoAnswer(
                f"{held[artefact.id]['path']} and {artefact.path} both hold {artefact.id}"
            )
        held[artefact.id] = {
            "id": artefact.id,
            "title": title.strip(),
            "status": WITHDRAWN if artefact.withdrawn else ACTIVE,
            "path": artefact.path,
        }
    return [held[use_case_id] for use_case_id in sorted(held, key=number_of)]


def envelope(value: Iterable[Mapping[str, str]]) -> dict[str, Any]:
    """The filler envelope the command prints (COR-052 point 6)."""
    return {"schema_version": POINT_VERSION, "value": list(value)}
