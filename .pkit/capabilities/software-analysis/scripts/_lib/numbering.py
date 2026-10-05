"""The numbering setting: the ids a project declares free again, with the commit that removed them.

An id names one artefact for good (DEC-001 point 3). The one exception is the
project's to declare, in the capability's settings file —
`.pkit/capabilities/software-analysis/project/config.yaml`, apart from the
recorded location beside it, `docs-locations.yaml` — as `numbering.freed-by`:
each entry names a commit by its full id, and the use-case and journey ids it
frees. Only a listed id is freed; none is inferred. The README's
"Configuration" section states the rule for a project; this module applies it.
The stamp and the number comparison read it here, and the history's judge
applies it (`_lib/history.py`), so the two never disagree:

- **the setting.** Its shape is its companion's, `schemas/config.schema.json`.
  An entry whose commit is no commit's id here, or lies off the default
  branch's history, is a problem and frees nothing. No file is a setting naming
  none.
- **the files a named commit can free.** A file of a use-case or journey place
  whose name carries an id; which the commit deleted against its first parent,
  git's rename detection on over the whole tree; which the default branch lost
  last by it — the newest commit of the default branch's first-parent line at
  which its path was removed is the named commit, or the merge that brought it
  onto that line; and whose path the history before the commit added once.
- **the ids an entry frees.** A listed id the commit deleted a file of, every
  such file one it can free, and every file the history before it gave the id
  one the setting frees. A listed id the commit does not free so is an error
  naming the id and why. An id it would free that no entry lists for it stays
  taken, and is reported.
- **faults that are not the setting's.** A clone too shallow to hold the
  commit's parent, or a git too old to read where the default branch lost a
  path, is said as such, with its fix — `git fetch --unshallow`, or git 2.31
  or later — never as an entry that frees nothing.

Git answers which commit an entry names, whether the default branch's history
holds it, which paths it deleted, and where the default branch's first-parent
line lost each last; the paths a history added, and the commit that added each,
are read as the history reads them (`_lib/backbone.py`, `_lib/history.py`).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ruamel.yaml.error import YAMLError

from _lib import backbone, history, markdown, schemas
from _lib.findings import ERROR, REPORT, Finding, at
from _lib.model import JOURNEY, USE_CASE, id_in_name, number_of

#: The capability's settings file, relative to the project root.
CONFIG = ".pkit/capabilities/software-analysis/project/config.yaml"

#: Where in it the setting lies, as a JSON Pointer.
FREED_BY = "/numbering/freed-by"

#: What the stamp and the number comparison call the setting in what they say.
NAME = "the project's numbering setting"

#: The oldest git that reads where a branch's first-parent line lost a path
#: (`git log --diff-merges`).
GIT_FLOOR = "2.31"


@dataclass(frozen=True)
class Entry:
    """One entry of the setting, of the shape its companion asks: where it lies, the
    commit it names, and the ids it lists."""

    index: int
    commit: str
    ids: tuple[str, ...]

    @property
    def where(self) -> str:
        """The entry's location."""
        return at(CONFIG, f"{FREED_BY}/{self.index}")

    def where_id(self, listed: str) -> str:
        """The location of `listed`, an id the entry lists."""
        return at(CONFIG, f"{FREED_BY}/{self.index}/ids/{self.ids.index(listed)}")


@dataclass(frozen=True)
class Setting:
    """The numbering setting: each entry of the shape its companion asks, as written;
    each problem with it, as a finding; and — once resolved — the entries whose commit
    is one of the default branch's history."""

    entries: tuple[Entry, ...] = ()
    problems: tuple[Finding, ...] = ()
    resolved: tuple[Entry, ...] = ()

    @property
    def unset(self) -> bool:
        """It names nothing, and nothing is wrong with it."""
        return not self.entries and not self.problems


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
    and path; the ids each entry frees, with its commit, in the setting's order; an
    error for each listed id an entry does not free, and for each entry whose commit's
    removals cannot be read; and a report for each entry whose commit would free an id
    no entry lists for it."""

    freed: tuple[Freed, ...] = ()
    ids: tuple[tuple[str, tuple[str, ...]], ...] = ()
    problems: tuple[Finding, ...] = ()
    reports: tuple[Finding, ...] = ()

    @property
    def files(self) -> Mapping[tuple[str, str], str]:
        """Each file freed as the history names a file — its path and the commit that
        added it — with the commit of the setting that freed it, as the history's judge
        reads it."""
        return {(f.path, f.added_by): f.freed_by for f in self.freed}


def read(root: Path) -> Setting:
    """The setting as the settings file writes it, held to its companion's shape; git
    is not asked. No file names nothing."""
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
    entries = tuple(
        Entry(index, item["commit"], tuple(item["ids"]))
        for index, item in enumerate(named if isinstance(named, list) else [])
        if _of_shape(item)
    )
    return Setting(entries, problems)


def resolve(root: Path, setting: Setting, branch: backbone.Branch) -> Setting:
    """`setting` with each entry resolved when its commit is a commit here, on the
    history of the default branch `branch`; a problem for each that is not."""
    if not setting.entries:
        return setting
    problems = list(setting.problems)
    if branch.commit is None:
        reason = branch.problem or f"the default branch {branch.name!r} resolves nowhere"
        message = (
            f"no commit it names can be checked against the default branch's history: {reason}"
        )
        return Setting(setting.entries, (*problems, Finding(ERROR, at(CONFIG, FREED_BY), message)))
    resolved: list[Entry] = []
    for entry in setting.entries:
        if backbone.commit_of(root, entry.commit) != entry.commit:
            problems.append(
                Finding(
                    ERROR,
                    entry.where,
                    f"{entry.commit} is no commit's id here: name a commit of the default "
                    f"branch's history by its full id, or remove the entry{_shallow(root)}",
                )
            )
        elif not backbone.is_ancestor(root, entry.commit, branch.commit):
            problems.append(
                Finding(
                    ERROR,
                    entry.where,
                    f"{entry.commit} is not on the history of the default branch, {branch.ref}: "
                    f"only a commit by which the default branch lost artefacts frees their ids "
                    f"(DEC-001 point 3)",
                )
            )
        else:
            resolved.append(entry)
    return Setting(setting.entries, tuple(problems), tuple(resolved))


def freeing(root: Path, setting: Setting, default: str | None, folders: Iterable[str]) -> Freeing:
    """What the entries `setting` resolved free on the default branch, whose commit is
    `default`, among the files under `folders`."""
    if not setting.resolved or default is None:
        return Freeing()
    places = sorted(set(folders))
    removals: dict[str, _Removal] = {}
    faults: dict[str, str] = {}
    for commit in dict.fromkeys(entry.commit for entry in setting.resolved):
        try:
            removals[commit] = _removal(root, commit, default, places)
        except _Fault as fault:
            faults[commit] = str(fault)
    listed: dict[str, set[str]] = defaultdict(set)
    for entry in setting.resolved:
        listed[entry.commit].update(entry.ids)
    # The files the setting frees, should every listed id hold.
    candidates = {
        number
        for commit, removal in removals.items()
        for listed_id in listed[commit] - set(removal.blocked)
        for number in removal.files.get(listed_id, ())
    }
    earlier: dict[str, set[history.Given]] = defaultdict(set)
    for removal in removals.values():
        for number in removal.before:
            if number.id in removal.ids:
                earlier[number.id].add(number)

    freed: set[Freed] = set()
    ids: list[tuple[str, tuple[str, ...]]] = []
    problems: list[Finding] = []
    for entry in setting.resolved:
        if entry.commit in faults:
            problems.append(Finding(ERROR, entry.where, faults[entry.commit]))
            continue
        removal = removals[entry.commit]
        held: list[str] = []
        for listed_id in entry.ids:
            reason = removal.why_not(listed_id, earlier[listed_id] - candidates)
            if reason is not None:
                message = _not_freed(entry.commit, listed_id, reason)
                problems.append(Finding(ERROR, entry.where_id(listed_id), message))
                continue
            held.append(listed_id)
            freed.update(
                Freed(number.id, number.path, number.commit, entry.commit)
                for number in removal.files.get(listed_id, ())
            )
        ids.append((entry.commit, tuple(sorted(held, key=_order))))

    reports: list[Finding] = []
    for commit, removal in removals.items():
        # An id no entry lists for the commit, which it would free were it listed.
        unlisted = [
            number
            for number in removal.ids - listed[commit]
            if removal.why_not(number, earlier[number] - candidates - removal.own(number)) is None
        ]
        if unlisted:
            first = next(entry for entry in setting.resolved if entry.commit == commit)
            reports.append(Finding(REPORT, first.where, _unlisted(commit, unlisted)))
    return Freeing(
        tuple(sorted(freed, key=lambda f: (*_order(f.id), f.path, f.freed_by))),
        tuple(ids),
        tuple(problems),
        tuple(reports),
    )


def joined(items: Iterable[str]) -> str:
    """`a`, `a and b`, `a, b and c`."""
    listed = list(items)
    return listed[0] if len(listed) == 1 else f"{', '.join(listed[:-1])} and {listed[-1]}"


@dataclass(frozen=True)
class _Removal:
    """What a named commit removed, as git reads it: the ids of the files it deleted
    under the places; for each, the files it can free — the default branch lost each
    last by it, and the history before it added each path once — as the history gave
    them; why it cannot free one, for each id it deleted such a file of; and every
    number the history before it gave a file under the places."""

    ids: frozenset[str] = frozenset()
    files: Mapping[str, tuple[history.Given, ...]] = field(default_factory=dict)
    blocked: Mapping[str, str] = field(default_factory=dict)
    before: tuple[history.Given, ...] = ()

    def own(self, listed: str) -> set[history.Given]:
        """The files of `listed` the commit can free."""
        return set(self.files.get(listed, ()))

    def why_not(self, listed: str, others: set[history.Given]) -> str | None:
        """Why the commit does not free `listed`, or `None` when it does — `others`
        being the files the history before it gave the id that the setting does not
        free."""
        if listed not in self.ids:
            return (
                f"it deleted no use case or journey numbered {listed}; a file it moved, rather "
                f"than deleted, keeps its id"
            )
        if listed in self.blocked:
            return self.blocked[listed]
        if others:
            other = min(others, key=lambda number: (number.path, number.commit))
            return (
                f"the history before it gave {listed} to {other.path} too (commit "
                f"{other.commit[: backbone.SHORT]}), which the setting does not free"
            )
        return None


class _Fault(Exception):
    """What a named commit removed cannot be read, for a reason the entry may not be at
    fault for."""


def _removal(root: Path, commit: str, default: str, places: list[str]) -> _Removal:
    """What `commit` removed under `places`, as the default branch, at `default`, lost
    it. Raises `_Fault` when git cannot say."""
    short = commit[: backbone.SHORT]
    if backbone.commit_of(root, f"{commit}^") is None:
        if backbone.is_shallow(root):
            raise _Fault(
                f"this clone is shallow and does not hold the parent of {short}, so what it "
                f"removed cannot be read: `git fetch --unshallow` reads the whole history"
            )
        raise _Fault(
            f"{commit} is the history's first commit: it removed nothing — name the commit by "
            f"which the default branch lost the artefacts, or remove the entry (DEC-001 point 3)"
        )
    try:
        deleted = backbone.removed(root, commit)
    except backbone.GitFailed as exc:
        raise _Fault(f"git could not list what {short} removed: {exc}") from exc
    gone = {
        path: number
        for path in deleted
        if (number := id_in_name(path)) is not None
        and any(path.startswith(f"{place}/") for place in places)
    }
    if not gone:
        return _Removal()
    try:
        lost = backbone.lost(root, default, gone)
    except backbone.GitFailed as exc:
        raise _Fault(
            f"git could not read where the default branch lost the files {short} removed — "
            f"that needs git {GIT_FLOOR} or later: {exc}"
        ) from exc
    before = tuple(history.given(root, f"{commit}^", places))
    adds: dict[str, list[history.Given]] = defaultdict(list)
    for number in before:
        if number.path in gone:
            adds[number.path].append(number)
    files: dict[str, list[history.Given]] = defaultdict(list)
    blocked: dict[str, str] = {}
    for path, number in sorted(gone.items()):
        last = lost.get(path)
        if last is None:
            blocked.setdefault(number, f"the default branch's own line never lost {path}")
        elif not _brought(root, commit, last):
            blocked.setdefault(
                number,
                f"the default branch lost {path} last by {last[: backbone.SHORT]}, not by it",
            )
        elif len(adds[path]) > 1:
            blocked.setdefault(number, _added_more_than_once(path, adds[path]))
        else:
            files[number] += adds[path]
    return _Removal(
        frozenset(gone.values()),
        {number: tuple(given) for number, given in files.items()},
        blocked,
        before,
    )


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


def _of_shape(item: object) -> bool:
    """Whether an entry names a commit by its full id and lists one id or more, each a
    use case's or a journey's — the shape its companion asks."""
    if not isinstance(item, dict):
        return False
    commit, ids = item.get("commit"), item.get("ids")
    return (
        isinstance(commit, str)
        and schemas.commit_id_pattern().match(commit) is not None
        and isinstance(ids, list)
        and bool(ids)
        and all(isinstance(listed, str) and _numbered(listed) for listed in ids)
    )


def _numbered(listed: str) -> bool:
    return any(schemas.id_pattern(kind).match(listed) for kind in (USE_CASE, JOURNEY))


def _order(listed: str) -> tuple[str, int]:
    """Journeys, then use cases, each by number."""
    return listed.split("-", 1)[0], number_of(listed)


def _not_freed(commit: str, listed: str, reason: str) -> str:
    return (
        f"{listed} is not freed by {commit[: backbone.SHORT]}: {reason} — remove it from the "
        f"entry, or list it under the commit that frees it (DEC-001 point 3)"
    )


def _unlisted(commit: str, unlisted: list[str]) -> str:
    ids = sorted(unlisted, key=_order)
    stays = "it stays" if len(ids) == 1 else "they stay"
    return (
        f"{commit[: backbone.SHORT]} also removed {joined(ids)}, which no entry lists for it: "
        f"{stays} taken (DEC-001 point 3)"
    )


def _added_more_than_once(path: str, added: list[history.Given]) -> str:
    adds = ", ".join(number.commit[: backbone.SHORT] for number in added)
    return (
        f"{path} was added {len(added)} times before it ({adds}), and which of those files "
        f"it removed cannot be told"
    )


def _shallow(root: Path) -> str:
    """What a shallow clone adds to a problem: its history stops early."""
    if not backbone.is_shallow(root):
        return ""
    return "; this clone is shallow — `git fetch --unshallow` reads the whole history"


def _unparsed(exc: Exception) -> str:
    """Why the settings file does not parse, and where."""
    reason = getattr(exc, "problem", None) or str(exc)
    mark = getattr(exc, "problem_mark", None)
    line = f", line {mark.line + 1}" if mark is not None else ""
    return f"it does not parse as YAML{line}: {reason} — fix it, or remove the file"
