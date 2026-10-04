"""The numbering setting: commits by which the default branch lost artefacts, freeing their numbers.

A number the default branch's history gave a file is never used again (DEC-001
point 3). The one exception is the project's to declare, in its configuration
of this capability — `numbering.freed-by` in
`.pkit/capabilities/software-analysis/project/config.yaml`: a commit by which
the default branch lost artefacts nothing still relies on, a pilot abandoned
before its analysis was established, say. Nothing else frees a number through
the stamp. The stamp and the number comparison read the rule here, and the
history's judge applies it (`_lib/history.py`), so the two never disagree:

- **the setting.** Its shape is its companion's, `schemas/config.schema.json`:
  each entry is a commit's full id. One that is no commit's id here, or lies
  off the default branch's history, is a problem and frees nothing; so is a
  commit that frees no number — the parent of the right one, say, or a root
  commit. The stamp refuses to number on a problem, and the number comparison
  fails on it. No file is a setting naming none.
- **the files a named commit frees.** A file of a use-case or journey place
  whose name carries a number, which the commit deleted against its first
  parent — git's rename detection on over the whole tree, so a file it moved,
  within the places or out of them, is not deleted, while one it moved and
  edited past git's likeness is, and one it deleted that git pairs with a
  similar file it added is not — and by which the default branch lost the path
  last: the newest commit of the default branch's first-parent line at which
  the path went is the named commit, or the merge that brought it onto that
  line. So a merge that brought the default branch in frees nothing it lost
  before, and a file a merge kept or brought back, and another commit removed
  since, is not freed. The file is the one the history added under the path
  before the commit; a path added there more than once is reported and not
  freed, since which of those files the commit removed cannot be told.
- **the numbers that are free.** A number is free when every file the history
  before a named commit gave it is a file the setting frees. One that history
  gave any other file still counts — a file another commit removed, or the
  name a file had before it was moved: only a file's last name is freed — as
  does a number the history gave a file since, reusing it or on another line
  of work, and a number a file in the working tree or on the default branch
  holds: the setting speaks for the history alone.

Git answers which commit an entry names, whether the default branch's history
holds it, which paths it deleted, and where the default branch's first-parent
line lost each last; the paths a history added, and the commit that added each,
are read as the history reads them (`_lib/backbone.py`, `_lib/history.py`).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ruamel.yaml.error import YAMLError

from _lib import backbone, history, markdown, schemas
from _lib.findings import ERROR, REPORT, Finding, at
from _lib.model import id_in_name, number_of

#: This capability's project configuration, relative to the project root.
CONFIG = ".pkit/capabilities/software-analysis/project/config.yaml"

#: Where in it the setting lies, as a JSON Pointer.
FREED_BY = "/numbering/freed-by"

#: What the stamp and the number comparison call the setting in what they say.
NAME = "the project's numbering setting"


@dataclass(frozen=True)
class Setting:
    """The numbering setting: each entry of the commit-id shape, with its index, as
    written; each problem with it, as a finding; and — once resolved — the commits
    it names."""

    entries: tuple[tuple[int, str], ...] = ()
    problems: tuple[Finding, ...] = ()
    commits: tuple[str, ...] = ()

    @property
    def unset(self) -> bool:
        """It names nothing, and nothing is wrong with it."""
        return not self.entries and not self.problems

    def where(self, commit: str) -> str:
        """The location of the entry naming `commit`."""
        index = next((i for i, entry in self.entries if entry == commit), None)
        return at(CONFIG, FREED_BY if index is None else f"{FREED_BY}/{index}")


@dataclass(frozen=True)
class Freed:
    """A file whose number is free again: the number the history gave it, its path, the
    commit that added it, and the commit of the setting that freed it."""

    id: str
    path: str
    added_by: str
    freed_by: str

    def as_json(self) -> dict[str, str]:
        return {
            "id": self.id,
            "path": self.path,
            "added_by": self.added_by,
            "freed_by": self.freed_by,
        }


@dataclass(frozen=True)
class Freeing:
    """What the setting frees: each file whose number is free again, by kind, number
    and path; an error for each commit of the setting that frees no number; and a
    report for each path one removed that its history added more than once."""

    freed: tuple[Freed, ...] = ()
    problems: tuple[Finding, ...] = ()
    reports: tuple[Finding, ...] = ()

    @property
    def files(self) -> Mapping[tuple[str, str], str]:
        """Each file freed as the history names a file — its path and the commit that
        added it — with the commit of the setting that freed it, as the history's judge
        reads it."""
        return {(f.path, f.added_by): f.freed_by for f in self.freed}


def read(root: Path) -> Setting:
    """The setting as the project's configuration writes it, held to its companion's
    shape; git is not asked. No file names nothing."""
    path = root / CONFIG
    if not path.is_file():
        return Setting()
    try:
        config: Any = markdown.load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, YAMLError) as exc:
        return Setting(problems=(Finding(ERROR, CONFIG, _unparsed(exc)),))
    problems = tuple(
        Finding(ERROR, at(CONFIG, pointer), message)
        for pointer, message in schemas.config_errors(config)
    )
    numbering = config.get("numbering") if isinstance(config, dict) else None
    named = numbering.get("freed-by") if isinstance(numbering, dict) else None
    shape = schemas.commit_id_pattern()
    entries = tuple(
        (index, entry)
        for index, entry in enumerate(named if isinstance(named, list) else [])
        if isinstance(entry, str) and shape.match(entry)
    )
    return Setting(entries, problems)


def resolve(root: Path, setting: Setting, branch: backbone.Branch) -> Setting:
    """`setting` with each entry as one of its commits when it is a commit's id here, on
    the history of the default branch `branch`; a problem for each that is not."""
    if not setting.entries:
        return setting
    problems = list(setting.problems)
    if branch.commit is None:
        reason = branch.problem or f"the default branch {branch.name!r} resolves nowhere"
        message = (
            f"no commit it names can be checked against the default branch's history: {reason}"
        )
        return Setting(setting.entries, (*problems, Finding(ERROR, at(CONFIG, FREED_BY), message)))
    commits: list[str] = []
    for index, entry in setting.entries:
        where = at(CONFIG, f"{FREED_BY}/{index}")
        if backbone.commit_of(root, entry) != entry:
            problems.append(
                Finding(
                    ERROR,
                    where,
                    f"{entry} is no commit's id here: name a commit of the default branch's "
                    f"history by its full id, or remove the entry{_shallow(root)}",
                )
            )
        elif not backbone.is_ancestor(root, entry, branch.commit):
            problems.append(
                Finding(
                    ERROR,
                    where,
                    f"{entry} is not on the history of the default branch, {branch.ref}: only "
                    f"a commit by which the default branch lost artefacts frees their numbers "
                    f"(DEC-001 point 3)",
                )
            )
        else:
            commits.append(entry)
    return Setting(setting.entries, tuple(problems), tuple(dict.fromkeys(commits)))


def freeing(root: Path, setting: Setting, default: str | None, folders: Iterable[str]) -> Freeing:
    """What the commits `setting` names free on the default branch, whose commit is
    `default`: each file under `folders` whose number is free again, an error for each
    commit that frees none, and a report for each path one removed that was added more
    than once before it."""
    if not setting.commits or default is None:
        return Freeing()
    places = sorted(set(folders))
    removed: dict[str, list[history.Given]] = {}
    earlier: dict[str, set[history.Given]] = defaultdict(set)
    reports: list[Finding] = []
    for commit in setting.commits:
        removed[commit], before, kept = _removed_by(root, commit, default, places)
        numbers = {number.id for number in removed[commit]}
        for number in before:
            if number.id in numbers:
                earlier[number.id].add(number)
        reports += [Finding(REPORT, setting.where(commit), message) for message in kept]
    candidates = {number for numbers in removed.values() for number in numbers}
    free = {number for number in candidates if earlier[number.id] <= candidates}
    freed = sorted(
        {
            Freed(number.id, number.path, number.commit, commit)
            for commit, numbers in removed.items()
            for number in numbers
            if number in free
        },
        key=lambda f: (f.id.split("-", 1)[0], number_of(f.id), f.path, f.freed_by),
    )
    problems = tuple(
        Finding(ERROR, setting.where(commit), _frees_none(root, commit))
        for commit, numbers in removed.items()
        if not free.intersection(numbers)
    )
    return Freeing(tuple(freed), problems, tuple(reports))


def _removed_by(
    root: Path, commit: str, default: str, places: list[str]
) -> tuple[list[history.Given], list[history.Given], list[str]]:
    """Each file under `places` that `commit` removed and by which the default branch,
    at `default`, lost it last, as the history gave it its number — its path and the
    commit that added it; every number the history before `commit` gave a file under
    `places`; and why each path it removed so, but which was added more than once
    before it, is not among the first."""
    gone = {
        path
        for path in backbone.removed(root, commit)
        if id_in_name(path) is not None and any(path.startswith(f"{p}/") for p in places)
    }
    if not gone:
        return [], [], []
    lost = backbone.lost(root, default, gone)
    brought = {last: _brought(root, commit, last) for last in set(lost.values())}
    lost_by_it = {path for path, last in lost.items() if path in gone and brought[last]}
    before = history.given(root, f"{commit}^", places)
    adds: dict[str, list[history.Given]] = defaultdict(list)
    for number in before:
        if number.path in lost_by_it:
            adds[number.path].append(number)
    numbers: list[history.Given] = []
    kept: list[str] = []
    for path, added in sorted(adds.items()):
        if len(added) == 1:
            numbers += added
        else:
            kept.append(_added_more_than_once(commit, path, added))
    return numbers, before, kept


def _brought(root: Path, commit: str, last: str) -> bool:
    """Whether `last`, a commit of the default branch's first-parent line, is `commit`
    or the merge that brought it onto that line: `commit` is in its history and not in
    its first parent's. Not, when git cannot say."""
    parent = backbone.commit_of(root, f"{last}^")
    return (
        parent is not None
        and backbone.is_ancestor(root, commit, last)
        and not backbone.is_ancestor(root, commit, parent)
    )


def _added_more_than_once(commit: str, path: str, added: list[history.Given]) -> str:
    short = commit[: backbone.SHORT]
    adds = ", ".join(number.commit[: backbone.SHORT] for number in added)
    return (
        f"{path}, which {short} removed, was added {len(added)} times before it ({adds}): "
        f"which of those files {short} removed cannot be told, so it frees none of them, "
        f"and {added[0].id} still counts (DEC-001 point 3)"
    )


def _frees_none(root: Path, commit: str) -> str:
    return (
        f"{commit} frees no number: it removed no use case or journey the default branch "
        f"lost last by it whose number no other file was given before it — name the commit "
        f"by which the default branch lost the artefacts, or remove the entry (DEC-001 "
        f"point 3){_shallow(root)}"
    )


def _shallow(root: Path) -> str:
    """What a shallow clone adds to a problem: its history stops early."""
    if not backbone.is_shallow(root):
        return ""
    return "; this clone is shallow — `git fetch --unshallow` reads the whole history"


def _unparsed(exc: Exception) -> str:
    """Why the configuration does not parse, and where."""
    reason = getattr(exc, "problem", None) or str(exc)
    mark = getattr(exc, "problem_mark", None)
    line = f", line {mark.line + 1}" if mark is not None else ""
    return f"it does not parse as YAML{line}: {reason} — fix it, or remove the file"
