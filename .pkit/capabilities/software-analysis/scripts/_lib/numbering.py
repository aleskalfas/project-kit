"""The numbering setting: the commits whose removed files' numbers are free again.

A number the default branch's history gave a file is never used again (DEC-001
point 3), unless the project names the commit that removed the file in its
configuration of this capability — `numbering.freed-by` in
`.pkit/capabilities/software-analysis/project/config.yaml`: a pilot cleared
before its analysis is established, say. Nothing else frees a number. The
stamp and the number comparison read the rule here, and the history's judge
applies it (`_lib/history.py`), so the two never disagree:

- **the setting.** Its shape is its companion's, `schemas/config.schema.json`.
  Each entry names a commit by its full id or by an abbreviation that names
  it alone, on the default branch's history. One that names no commit here,
  is ambiguous, or lies off that history is a problem, and frees nothing: the
  stamp refuses to number, and the number comparison fails on it. No file is
  a setting naming none.
- **what a named commit frees.** The numbers of the files it removed: deleted
  there, against its first parent, git's rename detection on over the whole
  tree — so a file it renamed, within the places or out of them, is not
  removed, and keeps its number. Of the files the history added under a path
  it deleted, the one removed is the last added before it. A number the
  history gave any other file still counts — one another commit removed, or a
  name a file had before another commit renamed it — and a number a file in
  the working tree or on the default branch holds always does: the setting
  speaks for the history alone.

Git answers which commit an entry names, whether the default branch's history
holds it, and which paths it deleted; the paths the history added, and the
commit that added each, are read as the history reads them (`_lib/backbone.py`).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ruamel.yaml.error import YAMLError

from _lib import backbone, markdown, schemas
from _lib.findings import ERROR, Finding, at

#: This capability's project configuration, relative to the project root.
CONFIG = ".pkit/capabilities/software-analysis/project/config.yaml"

#: Where in it the setting lies, as a JSON Pointer.
FREED_BY = "/numbering/freed-by"

#: What the stamp and the number comparison call the setting in what they say.
NAME = "the project's numbering setting"


@dataclass(frozen=True)
class Setting:
    """The numbering setting: each entry of the commit-name shape, with its index, as
    written; each problem with it, as a finding; and — once resolved — the commits
    it frees by, by their full ids."""

    entries: tuple[tuple[int, str], ...] = ()
    problems: tuple[Finding, ...] = ()
    commits: tuple[str, ...] = ()

    @property
    def unset(self) -> bool:
        """It names nothing, and nothing is wrong with it."""
        return not self.entries and not self.problems


def read(root: Path) -> Setting:
    """The setting as the project's configuration writes it, held to its companion's
    shape; git is not asked. No file names nothing."""
    path = root / CONFIG
    if not path.is_file():
        return Setting()
    try:
        config: Any = markdown.load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, YAMLError) as exc:
        reason = getattr(exc, "problem", None) or exc
        return Setting(problems=(Finding(ERROR, CONFIG, f"it does not parse: {reason}"),))
    problems = tuple(
        Finding(ERROR, at(CONFIG, pointer), message)
        for pointer, message in schemas.config_errors(config)
    )
    numbering = config.get("numbering") if isinstance(config, dict) else None
    named = numbering.get("freed-by") if isinstance(numbering, dict) else None
    shape = schemas.commit_name_pattern()
    entries = tuple(
        (index, entry)
        for index, entry in enumerate(named if isinstance(named, list) else [])
        if isinstance(entry, str) and shape.match(entry)
    )
    return Setting(entries, problems)


def resolve(root: Path, setting: Setting, branch: backbone.Branch) -> Setting:
    """`setting` with each entry's commit, by its full id, when it names one commit
    here on the history of the default branch `branch`; a problem for each that does
    not."""
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
        commit = backbone.commit_of(root, entry)
        if commit is None:
            problems.append(Finding(ERROR, where, _unresolved(root, entry)))
        elif not backbone.is_ancestor(root, commit, branch.commit):
            problems.append(
                Finding(
                    ERROR,
                    where,
                    f"{entry} is not on the history of the default branch, {branch.ref}: only "
                    f"a commit of it frees the numbers of the files it removed (DEC-001 point 3)",
                )
            )
        else:
            commits.append(commit)
    return Setting(setting.entries, tuple(problems), tuple(dict.fromkeys(commits)))


def freed(root: Path, commits: Iterable[str], folders: Iterable[str]) -> dict[tuple[str, str], str]:
    """Each file under `folders` one of `commits` removed, as the history names a file —
    its path and the commit that added it — with the commit that removed it."""
    places = sorted(set(folders))
    found: dict[tuple[str, str], str] = {}
    for commit in commits:
        gone = {
            path
            for path in backbone.removed(root, commit)
            if any(path.startswith(f"{place}/") for place in places)
        }
        if not gone:
            continue
        for added_by, path in backbone.added(root, f"{commit}^", places):
            if path in gone:  # newest first: the file the commit removed
                found.setdefault((path, added_by), commit)
                gone.discard(path)
    return found


def _unresolved(root: Path, entry: str) -> str:
    """Why `entry` names no commit: it is ambiguous, or names none here."""
    candidates = backbone.objects_named(root, entry)
    if len(candidates) > 1:
        return (
            f"{entry} is ambiguous: {len(candidates)} objects' ids start with it — write more "
            f"of the commit's id"
        )
    shallow = (
        "; this clone is shallow — `git fetch --unshallow` reads the whole history"
        if backbone.is_shallow(root)
        else ""
    )
    return (
        f"{entry} names no commit here: name a commit of the default branch's history by its "
        f"id, or remove the entry{shallow}"
    )
