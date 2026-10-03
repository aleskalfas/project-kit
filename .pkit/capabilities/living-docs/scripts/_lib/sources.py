"""living-docs' checks over the captured sources (DEC-001 point 4).

A page anchors a source outside the repository by its name, and the source is
captured as one file of this capability's project tier (`source_layout`).
What is checked:

- **The layout** — errors. Every entry of the sources folder is a captured
  source: a regular file named `<name>.yaml`, the name of the grammar. A
  `.yaml` file of any other name, a folder or a link captures nothing, since a
  name answers only its exact file; so does the folder when it, or a folder on
  its path, is not a real folder of exactly its name. A regular file whose
  name does not end in `.yaml` — notes, an editor's backup — captures nothing
  either, and is only reported; a hidden entry is left alone (`source_layout`).
  A captured source's *shape* — its fields — is `schemas/source.schema.json`,
  which `pkit validate` applies under `data`, bound by the file's path
  (COR-023), and is not judged here.
- **What names a source** — reports, never failed. A `source` anchor, or a
  rule's origin citing a `source`, that no captured file answers: the
  whole-repository check reports the anchor dead, and rule-set validation
  fails the citation, so this only says where. And a captured source nothing
  anchors or cites.

The anchors and the rules' origins are read from the backbone's artefact
discovery, the reading the space checks already hold (`artefacts`); where a
name leads is `source_layout.answer`, the resolver's own answer.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from _lib import source_layout
from _lib.artefacts import Artefact

#: The anchor kind this capability registers, as an anchor block and a rule's
#: cited source write it.
KIND = "source"

ANCHOR_POINTER = f"/pkit/friction/anchors/{KIND}"
ORIGIN_POINTER = "/origin/source"


@dataclass(frozen=True)
class Problem:
    """One finding of these checks: an error, or a report never failed."""

    error: bool
    location: str
    message: str


@dataclass(frozen=True)
class Checked:
    """The findings, and the summary's line about the captured sources."""

    problems: tuple[Problem, ...]
    summary: str


@dataclass(frozen=True)
class _Citation:
    """A source an artefact names: an anchor of its friction block, or a rule's origin."""

    location: str
    value: str
    origin: bool


def check(root: Path, artefacts: Sequence[Artefact]) -> Checked:
    """The layout of the sources folder in the project at `root`, and what of the
    `artefacts` names a source no file captures, or a captured source nothing names."""
    folder = source_layout.folder_path()
    try:
        entries = source_layout.entries(root)
    except source_layout.Unreadable as exc:
        message = (
            f"the captured sources cannot be read — {exc}. Every `{KIND}` anchor gives no "
            f"answer, and its page is not judged, until they can: the resolver reads them "
            f"from {folder}/ (DEC-001 point 4)."
        )
        return Checked(
            (Problem(True, folder, message),),
            f"sources: {folder}/ cannot be read, so no source is checked.",
        )

    problems = [
        Problem(entry.error, entry.path, _layout_message(entry))
        for entry in entries
        if entry.problem
    ]
    captured = sorted(entry.name for entry in entries if entry.name is not None)
    citations = _citations(artefacts)
    answers: dict[str, bool] = {}
    dead = 0
    for citation in citations:
        if citation.value not in answers:
            try:
                answers[citation.value] = bool(source_layout.answer(root, citation.value))
            except source_layout.Unreadable:
                answers[citation.value] = True  # no answer is not "none": nothing to report
        if not answers[citation.value]:
            dead += 1
            problems.append(Problem(False, citation.location, _dead_message(citation)))
    named = {citation.value for citation in citations}
    unused = [name for name in captured if name not in named]
    problems.extend(
        Problem(False, source_layout.file_path(name), _unused_message(name)) for name in unused
    )
    return Checked(
        tuple(problems),
        f"sources (DEC-001 point 4): {len(captured)} captured in {folder}/; {dead} anchor(s) "
        f"or citation(s) naming none, {len(unused)} captured source(s) nothing anchors or cites.",
    )


def _citations(artefacts: Sequence[Artefact]) -> list[_Citation]:
    """Every source the artefacts name, by where it is named."""
    found: list[_Citation] = []
    for artefact in artefacts:
        where = f"{artefact.path}#{artefact.id}" if artefact.entry else artefact.path
        found.extend(
            _Citation(f"{where}:{ANCHOR_POINTER}", value, origin=False)
            for value in (artefact.anchors or {}).get(KIND, ())
        )
        if artefact.rule:
            value = _cited_source(artefact.fields)
            if value is not None:
                found.append(_Citation(f"{where}:{ORIGIN_POINTER}", value, origin=True))
    return sorted(found, key=lambda citation: (citation.location, citation.value))


def _cited_source(fields: Mapping[str, object] | None) -> str | None:
    """The source a rule's origin cites by this capability's kind (COR-051 point 5), if any."""
    origin = fields.get("origin") if fields is not None else None
    cited = origin.get("source") if isinstance(origin, Mapping) else None
    if not isinstance(cited, Mapping) or cited.get("kind") != KIND:
        return None
    value = cited.get("value")
    return value if isinstance(value, str) else None


def _layout_message(entry: source_layout.Entry) -> str:
    folder = source_layout.folder_path()
    if entry.path != folder and entry.path.startswith(f"{folder}/"):
        return (
            f"{entry.path} {entry.problem}, so it captures no source: {folder}/ holds one "
            f"regular file per source, `<name>{source_layout.SUFFIX}`, and a name answers only "
            f"its exact file — rename it or remove it (DEC-001 point 4)."
        )
    return (
        f"{entry.path} {entry.problem}. Captured sources are read only from {folder}/, "
        f"through real folders of exactly those names — correct it, or remove it "
        f"(DEC-001 point 4)."
    )


def _dead_message(citation: _Citation) -> str:
    where = source_layout.file_path(citation.value)
    named = (
        f"the rule's origin cites source `{citation.value}`"
        if citation.origin
        else f"anchor `{KIND}: {citation.value}`"
    )
    return (
        f"{named}, and no captured file answers it ({where}; a name is "
        f"{source_layout.GRAMMAR}), so it is dead — capture the source there, or correct "
        f"the name (DEC-001 point 4)."
    )


def _unused_message(name: str) -> str:
    return (
        f"captured source `{name}` is anchored by no artefact and cited by no rule's origin — "
        f"anchor it from the pages that rest on it, or remove the file (DEC-001 point 4)."
    )
