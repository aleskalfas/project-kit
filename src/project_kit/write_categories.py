"""A capability's write categories, and the defaults written for them (COR-073, ADR-088).

A capability declares, in an optional `write_categories` block of its package
file, each overlay category it introduces for its agents' writes: the category's
whole name (the capability's name, a dot, a word), the one agent that owns it,
and optionally a `default-query`, a query command of the capability's that
answers the paths the agent works in (ADR-088 point 1). This module holds what
every writer of such a default shares:

- **the declarations** of the installed capabilities, or of one capability's
  package (`installed`, `declared_in`), and the agents a capability ships with
  the categories each owns (`capability_agents`, `owned_placeholders`), which
  package validation reads;
- **the query** (`ask`): run as a validator's command runs, with `--json`
  alone, offline-marked and bounded, from the project root, its answer one
  document `{"paths": [...]}` with an optional one-line `note` (point 2);
- **the check of an answer** (`refusal`): each path inside the repository once
  links are followed, clear of the capability's folder, not refused by the
  lifecycle layer's test of what a grant may not reach, and overlapping no
  path another agent owns (point 3);
- **the written line** (`OverlayDocument`): the line a writer writes, at the
  overlay's top level, in flow form, ending with `# pkit-written:` and the same
  value again, with a comment above it; whether a line is still as written;
  and the one-line text edits a write and a move make (point 4).

The writers themselves are the fill commands (`agents_overlay`) and a
capability's install (`cli`).
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, cast

from ruamel.yaml import YAML

from project_kit import validators
from project_kit.command_runner import Ending, registered_commands, resolve_command, run_command
from project_kit.manifest import read_backbone_manifest

#: The package-file key a capability declares its write categories under.
WRITE_CATEGORIES_KEY = "write_categories"
#: The key naming a category's one owning agent.
OWNER_KEY = "owner"
#: The key naming the command that answers a category's default.
DEFAULT_QUERY_KEY = "default-query"
#: What separates a capability's name from the word of a category it declares.
SEPARATOR = "."
#: A word, the part of a category's name after the dot.
WORD = re.compile(r"^[a-z][a-z0-9-]*$")

#: The mark that ends a written line: a comment, then the value written again.
WRITTEN_MARK = "# pkit-written:"
#: The comment line a writer puts above the line it writes. It does not open
#: with the category's name, so no reader takes it for a commented stub.
WRITTEN_COMMENT = (
    "# Written as a capability's default for the category below. While it stays as "
    "written, `pkit agents reconcile` may move it; edit it and it is the project's."
)

# The answer's keys (point 2): a key the document does not define makes another shape.
_PATHS = "paths"
_NOTE = "note"
_GLOB_CHARACTERS = frozenset("*?[]{}")

_FRONT_MATTER = re.compile(r"^---\n(.*?\n)---\n", re.DOTALL)
_yaml: Any = YAML(typ="safe")


# --- the declarations (point 1) ------------------------------------------------


@dataclass(frozen=True)
class WriteCategory:
    """One category a capability declares for its agents' writes."""

    name: str  # the whole name, `<capability>.<word>`
    capability: str
    owner: str
    default_query: str | None  # a leaf of the capability's `commands:`, or None
    component_dir: Path

    @property
    def folder(self) -> str:
        """The capability's folder, as an overlay entry names a path."""
        return f".pkit/capabilities/{self.capability}"


def declared_in(capability: str, component_dir: Path) -> list[WriteCategory]:
    """The write categories the package file at *component_dir* declares, in the
    block's order. A block or entry that does not read declares nothing:
    package validation reports why."""
    try:
        raw: Any = _yaml.load((component_dir / "package.yaml").read_text(encoding="utf-8"))
    except Exception:  # absent, unreadable, or ruamel's own hierarchy
        return []
    block: Any = (
        cast("Mapping[str, Any]", raw).get(WRITE_CATEGORIES_KEY)
        if isinstance(raw, Mapping)
        else None
    )
    if not isinstance(block, Mapping):
        return []
    found: list[WriteCategory] = []
    for key, entry in cast("Mapping[Any, Any]", block).items():
        if not isinstance(entry, Mapping):
            continue
        fields = cast("Mapping[str, Any]", entry)
        owner = fields.get(OWNER_KEY)
        query = fields.get(DEFAULT_QUERY_KEY)
        if not isinstance(owner, str):
            continue
        found.append(
            WriteCategory(
                name=str(key),
                capability=capability,
                owner=owner,
                default_query=query if isinstance(query, str) else None,
                component_dir=component_dir,
            )
        )
    return found


def installed(target_root: Path) -> list[WriteCategory]:
    """The write categories every registered capability declares, in manifest order."""
    manifest = read_backbone_manifest(target_root)
    if manifest is None:
        return []
    found: list[WriteCategory] = []
    for entry in manifest.components:
        if entry.kind != "capability":
            continue
        component_dir = target_root / ".pkit" / "capabilities" / entry.name
        found += declared_in(entry.name, component_dir)
    return found


def capability_agents(component_dir: Path) -> dict[str, Path]:
    """The agents a capability ships, by name, as the deploy finds them:
    `agents/<name>.md`, else `agents/<name>/<name>.md`."""
    folder = component_dir / "agents"
    if not folder.is_dir():
        return {}
    found: dict[str, Path] = {}
    for entry in sorted(folder.iterdir()):
        name = entry.stem if entry.is_file() else entry.name
        for source in (folder / f"{name}.md", folder / name / f"{name}.md"):
            if source.is_file():
                found.setdefault(name, source)
                break
    return found


def owned_placeholders(source: Path) -> set[str]:
    """The categories `<category>` placeholders name in a definition's `owns`."""
    try:
        match = _FRONT_MATTER.match(source.read_text(encoding="utf-8"))
        front: Any = _yaml.load(match.group(1)) if match else None
    except Exception:  # unreadable, or ruamel's own hierarchy
        return set()
    owns: Any = cast("Mapping[str, Any]", front).get("owns") if isinstance(front, Mapping) else None
    if not isinstance(owns, list):
        return set()
    return {
        item[1:-1]
        for item in cast("list[Any]", owns)
        if isinstance(item, str) and item.startswith("<") and item.endswith(">")
    }


# --- the query (point 2) -------------------------------------------------------


@dataclass(frozen=True)
class Answer:
    """What a default query answered: its paths, and the note it gave, if any."""

    paths: tuple[str, ...]
    note: str = ""


@dataclass(frozen=True)
class NoAnswer:
    """Why a default query gave no answer."""

    reason: str


def ask(target_root: Path, category: WriteCategory) -> Answer | NoAnswer:
    """Run the category's default query afresh and read its answer.

    It runs as a validator's command runs: from the project root, with `--json`
    alone, offline-marked and bounded, through the runner the query commands
    share. An exit other than 0, a timeout, a command that did not start, or a
    document of another shape is no answer. Nothing keeps an answer from one
    run to the next.
    """
    reference = category.default_query
    if reference is None:
        return Answer(paths=())
    command = resolve_command(registered_commands(category.component_dir), reference)
    if command is None:
        return NoAnswer(
            f"`{DEFAULT_QUERY_KEY}` names {reference!r}, which is no command of the capability's"
        )
    if command.entry.get(validators.QUERY_CONTRACT_KEY) is not True:
        return NoAnswer(f"command {reference!r} does not declare the query contract")
    if validators.READS_KEY in command.entry:
        return NoAnswer(f"command {reference!r} declares `{validators.READS_KEY}`")
    if not command.script.is_file():
        return NoAnswer(f"command {reference!r} names a script that does not exist")
    run = run_command(
        command.script,
        [validators.QUERY_FLAG],
        cwd=target_root,
        extra_env=validators.OFFLINE_MARKER,
        drop_env=validators.QUERY_DROPPED_ENV,
    )
    if run.ending is not Ending.ANSWERED:
        return NoAnswer(validators.why_no_answer(run, reference))
    return read_answer(run.document, reference)


def read_answer(document: Any, reference: str) -> Answer | NoAnswer:
    """The answer *document* gives, or why it is of another shape (point 2)."""
    shape = f'command {reference!r} answered with no document of the shape {{"paths": [...]}}'
    if not isinstance(document, Mapping):
        return NoAnswer(f"{shape}: it printed no JSON object")
    fields = cast("Mapping[Any, Any]", document)
    unknown = sorted(str(key) for key in fields if key not in (_PATHS, _NOTE))
    if unknown:
        return NoAnswer(f"{shape}: it has the key(s) {', '.join(unknown)}")
    paths: Any = fields.get(_PATHS)
    if not isinstance(paths, list):
        return NoAnswer(f"{shape}: `{_PATHS}` is no list")
    note: Any = fields.get(_NOTE, "")
    if not isinstance(note, str) or "\n" in note:
        return NoAnswer(f"{shape}: `{_NOTE}` is no line of text")
    read: list[str] = []
    for path in cast("list[Any]", paths):
        problem = _path_problem(path)
        if problem is not None:
            return NoAnswer(f"{shape}: {problem}")
        read.append(cast("str", path))
    return Answer(paths=tuple(read), note=note)


def _path_problem(path: Any) -> str | None:
    """Why *path* is no path an answer may hold, or None (point 2)."""
    if not isinstance(path, str) or not path.strip():
        return f"{path!r} is no path"
    if path.startswith("/") or "\\" in path:
        return f"{path!r} is not relative to the repository's root, written with `/`"
    if ".." in path.split("/"):
        return f"{path!r} holds a `..` segment"
    if _GLOB_CHARACTERS.intersection(path):
        return f"{path!r} holds a glob character"
    return None


# --- the check of an answer (point 3) ------------------------------------------


def normalised(path: str) -> str:
    """A path as the exactly-one-owner check compares it: no leading `./`, no
    trailing `/` (ADR-051 point 3)."""
    text = path.strip()
    while text.startswith("./"):
        text = text[2:]
    return text.rstrip("/")


def overlap(left: str, right: str) -> bool:
    """True when two normalised paths are equal or one contains the other."""
    return left == right or left.startswith(right + "/") or right.startswith(left + "/")


def refusal(
    target_root: Path,
    category: WriteCategory,
    paths: Iterable[str],
    others: Sequence[tuple[str, str]],
    ownership: ModuleType | None,
) -> str | None:
    """Why the answer *paths* may not be written for *category*, or None (point 3).

    Each path must lie inside the repository once links are followed, clear of
    the capability's folder (neither inside it nor holding it), unrefused by the
    lifecycle layer's test of what a grant may not reach, and overlap no path of
    *others*, each `(agent, normalised path)` another agent owns. One path that
    fails refuses the answer whole: the reason names it.
    """
    root = target_root.resolve()
    folder = (target_root / category.folder).resolve()
    for path in paths:
        resolved = (target_root / path).resolve()
        if resolved != root and root not in resolved.parents:
            return f"{path!r} lies outside the repository once links are followed"
        if resolved == folder or folder in resolved.parents or resolved in folder.parents:
            return (
                f"{path!r} reaches the capability's own folder, {category.folder}/, which "
                "uninstall removes while the overlay keeps the line"
            )
        if ownership is None:
            return (
                "the tree has no .pkit/lifecycle/ownership.py to test what a grant may not "
                "reach; run `pkit sync`"
            )
        if ownership.grant_reaches(target_root, path):
            return f"{path!r} reaches content `pkit sync` overwrites"
        for agent, owned in others:
            if overlap(normalised(path), owned):
                return f"{path!r} overlaps {owned!r}, which agent {agent!r} owns"
    return None


def holds_content(target_root: Path, path: str) -> bool:
    """True when *path* holds content: a file, or a folder with any entry."""
    place = target_root / path
    if place.is_file():
        return True
    return place.is_dir() and any(place.iterdir())


# --- the written line (point 4) ------------------------------------------------


def flow(paths: Sequence[str]) -> str:
    """A value in flow form, each path a double-quoted string as JSON writes it."""
    return json.dumps(list(paths), ensure_ascii=False)


def written_line(category: str, paths: Sequence[str]) -> str:
    """The top-level line a writer writes, ending with its written mark."""
    value = flow(paths)
    return f"{category}: {value}  {WRITTEN_MARK} {value}"


class OverlayDoesNotRead(Exception):
    """The overlay's text does not parse as a mapping, so no writer writes it."""


class OverlayDocument:
    """The overlay's text, read and edited a line at a time.

    Whether a category has a value is read from the parsed overlay; the line a
    writer writes, and whether it is still as written, from the text. A write
    and a move each change one line of the text, and leave every other byte as
    it was.
    """

    def __init__(self, text: str) -> None:
        self.text = text

    def data(self) -> Mapping[str, Any]:
        """The parsed overlay; raises `OverlayDoesNotRead`."""
        try:
            loaded: Any = _yaml.load(self.text) if self.text.strip() else {}
        except Exception as exc:  # ruamel's own hierarchy
            raise OverlayDoesNotRead(str(exc)) from exc
        if loaded is None:
            return {}
        if not isinstance(loaded, Mapping):
            raise OverlayDoesNotRead("its top level is no mapping")
        return cast("Mapping[str, Any]", loaded)

    def gives_value(self, category: str, owner: str) -> bool:
        """Whether the top level, or the owner's override, gives *category* a value.
        A bare key gives none."""
        data = self.data()
        if data.get(category) is not None:
            return True
        overrides: Any = data.get("overrides")
        block: Any = (
            cast("Mapping[str, Any]", overrides).get(owner)
            if isinstance(overrides, Mapping)
            else None
        )
        return (
            isinstance(block, Mapping)
            and cast("Mapping[str, Any]", block).get(category) is not None
        )

    def still_as_written(self, category: str) -> list[str] | None:
        """The value of *category*'s top-level line while it is still as written,
        else None: its own line holds the value in flow form and ends with the
        written mark, and the two values, read as YAML, are equal, in order."""
        found = self._top_line(category)
        if found is None:
            return None
        _index, rest = found
        before, mark, after = rest.rpartition(WRITTEN_MARK)
        value_text = before.strip()
        if not mark or not value_text.startswith("["):
            return None
        try:
            value = _yaml.load(value_text)
            kept = _yaml.load(after.strip())
        except Exception:  # ruamel's own hierarchy: a line a person broke
            return None
        if not isinstance(value, list) or value != kept:
            return None
        items = cast("list[Any]", value)
        if not all(isinstance(item, str) for item in items):
            return None
        return [str(item) for item in items]

    def write(self, category: str, paths: Sequence[str]) -> None:
        """Write *category*'s line: over a bare top-level key's line, else at the end,
        with the comment line above it. Leaves a commented stub as it is."""
        lines = self.text.splitlines(keepends=True)
        block = f"{WRITTEN_COMMENT}\n{written_line(category, paths)}\n"
        data = self.data()
        found = self._top_line(category) if category in data else None
        if found is not None:
            index, _rest = found
            lines[index] = block
            text = "".join(lines)
        else:
            text = self.text
            if text and not text.endswith("\n"):
                text += "\n"
            text += ("\n" if text.strip() else "") + block
        self._replace(text, category, paths)

    def move(self, category: str, paths: Sequence[str]) -> None:
        """Rewrite *category*'s top-level line, its value and its mark, to *paths*."""
        found = self._top_line(category)
        if found is None:
            raise OverlayDoesNotRead(f"no top-level line of {category}")
        index, _rest = found
        lines = self.text.splitlines(keepends=True)
        ending = lines[index][len(lines[index].rstrip("\r\n")) :] or "\n"
        lines[index] = written_line(category, paths) + ending
        self._replace("".join(lines), category, paths)

    def _replace(self, text: str, category: str, paths: Sequence[str]) -> None:
        """Take *text* only where it reads back with *category* at *paths*."""
        before = self.text
        self.text = text
        try:
            value = self.data().get(category)
        except OverlayDoesNotRead:
            value = None
        if value != list(paths):
            self.text = before
            raise OverlayDoesNotRead(f"the line written for {category} does not read back")

    def _top_line(self, category: str) -> tuple[int, str] | None:
        """The index of *category*'s top-level line, and the text after its colon."""
        pattern = re.compile(rf"^{re.escape(category)}[ \t]*:(?P<rest>.*?)\r?\n?$")
        for index, line in enumerate(self.text.splitlines(keepends=True)):
            match = pattern.match(line)
            if match:
                return index, match.group("rest")
        return None
