"""Documents, configuration and history for the friction tests (COR-050).

Shared by the change-check, whole-repository-check and report tests: a
backbone configuration with a `friction` key, Markdown documents whose front
matter carries the `friction` block, and a `Timeline` laying down dated
commits. Front matter is written as JSON — valid YAML, and exact about
strings — so a test says precisely what an artefact holds.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Any

from tests.adopter_repo import HISTORY_EPOCH, AdopterRepo, Author

CONFIG = ".pkit/project/config.yaml"
T1 = "2026-10-01T09:00:00Z"
T2 = "2026-10-02T09:40:12Z"
SOURCE = {"src/cli/main.py": "print('cli')\n", "src/core/engine.py": "ENGINE = 1\n"}


def friction_config(
    mode: str = "warning", places: tuple[str, ...] = ("docs",), **friction: Any
) -> str:
    """The backbone configuration file with a `friction` key: mode, places, and the rest."""
    block: dict[str, Any] = {"mode": mode, "places": list(places), **friction}
    return json.dumps({"name": "adopter", "friction": block}, indent=2) + "\n"


def document(
    artefact_id: str | None,
    *,
    anchors: dict[str, list[str]] | None = None,
    at: str | None = None,
    outcome: str | None = None,
    because: str | None = None,
    deferred: list[tuple[str, str, str]] | None = None,
    unanchored_because: str | None = None,
    body: str = "Body.",
    **fields: Any,
) -> str:
    """A document whose front matter carries the `friction` block, as JSON."""
    front: dict[str, Any] = {} if artefact_id is None else {"id": artefact_id}
    front.update(fields)
    revalidated: dict[str, Any] = {}
    if at is not None:
        revalidated["at"] = at
    if outcome is not None:
        revalidated["outcome"] = outcome
    if because is not None:
        revalidated["unchanged-because"] = because
    if deferred:
        revalidated["deferred"] = [
            {"anchor": {"kind": kind, "value": value}, "reason": reason}
            for kind, value, reason in deferred
        ]
    block: dict[str, Any] = {}
    if anchors is not None:
        block["anchors"] = anchors
    if unanchored_because is not None:
        block["unanchored-because"] = unanchored_because
    if revalidated:
        block["revalidated"] = revalidated
    front["pkit"] = {"friction": block}
    return f"---\n{json.dumps(front, indent=2)}\n---\n\n{body}\n"


def guide(**overrides: Any) -> str:
    """The workhorse artefact: `guide`, anchored to the CLI sources, revalidated at T1."""
    values: dict[str, Any] = {
        "anchors": {"path": ["src/cli/**"]},
        "at": T1,
        "outcome": "unchanged",
        "because": "the CLI surface is as described",
    }
    values.update(overrides)
    return document("guide", **values)


#: A project record whose points are headings, for anchors on one point (COR-050 point 2).
POINTED = ".pkit/decisions/project/PRJ-900-pointed.md"

#: Its points, in written order: id, title and text.
POINTS: tuple[tuple[str, str, str], ...] = (
    ("1", "First", "The first point."),
    ("2", "Second", "The second point."),
    ("3", "Third", "The third point."),
)


def pointed_record(
    points: tuple[tuple[str, str, str], ...] = POINTS,
    *,
    status: str = "accepted",
    title: str = "A pointed record",
    lead: str = "The record decides three things.",
    retired: Mapping[str, list[str]] | None = None,
    context: str = "Why it came up.",
    rationale: str = "Why this way.",
    preamble: str = "",
) -> str:
    """`PRJ-900`, its points written as headings in the order given (COR-058 point 1).

    A point whose title is `Retired` is a stub: give its text as the sentence
    its entry in `retired` gives (COR-058 point 4).
    """
    front: dict[str, Any] = {
        "id": "PRJ-900",
        "title": title,
        "status": status,
        "date": "2026-10-13",
        "author": "A. Author <a@example.com>",
    }
    if retired:
        front["retired-points"] = dict(retired)
    sections = "".join(f"### {pid}. {name}\n\n{text}\n\n" for pid, name, text in points)
    opening = f"{preamble}\n\n" if preamble else ""
    return (
        f"---\n{json.dumps(front, indent=2)}\n---\n\n{opening}## Context\n\n{context}\n\n"
        f"## Decision\n\n{lead}\n\n{sections}## Rationale\n\n{rationale}\n\n"
        f"## Implications\n\nNone.\n"
    )


#: A project record not yet converted, its points a numbered list (COR-058 point 2).
LISTED = ".pkit/decisions/project/PRJ-910-listed.md"


def listed_record() -> str:
    """`PRJ-910`, the points of `POINTS` written as a numbered list in its Decision's lead.

    An anchor on one of its points names nothing it can stand on, since a list's
    numbers are not permanent (COR-050 point 7).
    """
    items = "\n".join(f"{pid}. **{name}.** {text}" for pid, name, text in POINTS)
    return pointed_record((), title="A listed record", lead=items).replace("PRJ-900", "PRJ-910")


class Timeline:
    """Commits on an adopter repository, each a day after the last, so origins have known dates."""

    def __init__(self, adopter: AdopterRepo) -> None:
        self.adopter = adopter
        self.days = 0

    def _next(self) -> datetime:
        self.days += 1
        return HISTORY_EPOCH + timedelta(days=self.days)

    def start(self, files: Mapping[str, str], config: str | None = None) -> str:
        """The base commit on `main`: the install, the configuration, the sources and `files`."""
        self.adopter.write({CONFIG: config or friction_config(), **SOURCE, **files})
        return self.commit("base")

    def commit(
        self,
        message: str,
        files: Mapping[str, str | None] | None = None,
        *,
        author: Author | None = None,
    ) -> str:
        return self.adopter.commit(message, files, author=author, date=self._next())

    def commit_index(self, message: str) -> str:
        """Commit what the index holds — a gitlink staged with `git update-index`, say,
        which `commit` would stage away, having no checkout — dated as the next commit."""
        self.adopter.git("commit", "-q", "-m", message, date=self._next())
        return self.adopter.head()

    def rename(self, src: str, dst: str) -> str:
        return self.adopter.rename(src, dst, date=self._next())

    def merge(self, branch: str) -> str:
        return self.adopter.merge(branch, date=self._next())

    def squash_merge(self, branch: str) -> str:
        return self.adopter.squash_merge(branch, date=self._next())

    def revert(self, commit: str, *, mainline: int | None = None) -> str:
        """`git revert` of `commit`, dated as the next commit: what it changed, undone — for
        a merge commit, against its parent number `mainline`."""
        parent = () if mainline is None else ("-m", str(mainline))
        self.adopter.git("revert", "--no-edit", *parent, commit, date=self._next())
        return self.adopter.head()

    def cherry_pick(self, commit: str) -> str:
        """`git cherry-pick` of `commit` onto the current branch, dated as the next commit."""
        self.adopter.git("cherry-pick", commit, date=self._next())
        return self.adopter.head()
