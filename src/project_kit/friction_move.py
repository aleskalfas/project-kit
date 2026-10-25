"""The plan of the move: a project's answers out of the artefacts' blocks, into answer files
(COR-062 point 11; ADR-068 points 1 and 7).

A project's existing answers move out of the blocks once. This module only plans the
move, and writes nothing: `pkit friction move-plan` prints the plan, and the backbone
migration that makes the move writes its bytes, importing no backbone (the lifecycle
README, "Script contract").

- **What moves** (`plan_move`): each artefact whose block holds an answer, a
  `revalidated` block or a `revisited` list (`answer_files.block_holds_answers`). Its
  answers go to an answer file of their own, named `moved-<hash>.yaml` for its
  location and its answers (`answer_files.moved_name`), so a second run over one state
  plans the same file. The entry names no file in `read`, so each answer it holds is a
  moved one, which asks nobody (COR-062 point 3). Every value is written as the block
  writes it, so each keeps its point (point 6).
- **What it leaves:** an artefact the project receives by sync, whose answers are its
  source's (point 9), and one whose answers would not read back in the answer files'
  shape or whose block cannot be edited exactly. Each is listed with why, and its file
  is left as it is. A block keeps its anchors, its reason for having none and
  `last-check`.
- **The artefact's file** loses the answer keys of its block, every other byte kept,
  in the line endings it is written with. One file's artefacts move together, and its
  new text is read back: its front matter must hold exactly what it held without them.

Run again over a state already moved, it plans nothing: no block holds an answer.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from project_kit import answer_files as af
from project_kit import backbone_schemas as bs
from project_kit.document_parts import split_front_matter
from project_kit.friction_check import printable
from project_kit.friction_discovery import (
    FRICTION_KEY,
    REVISITED_KEY,
    Artefact,
    discover_artefacts,
    line_break,
)
from project_kit.friction_write import (
    DEFERRAL_KEYS,
    REVALIDATED,
    REVISIT_KEYS,
    answer_file_text,
    carrier_keys,
    in_order,
    ordered_revalidation,
    without_key,
)
from project_kit.line_breaks import universal_newlines

#: The version of the plan's machine-readable document (`render_json`).
MOVE_PLAN_SCHEMA_VERSION = 1

#: The keys of a block that hold answers, in the order an entry writes them.
_ANSWER_KEYS = (REVALIDATED, REVISITED_KEY)

_safe: Any = YAML(typ="safe")


@dataclass(frozen=True)
class MovedAnswers:
    """One artefact's answers as the move writes them: an answer file of their own."""

    artefact: str  # its location
    path: str  # the answer file's path, relative to the project root
    text: str  # its content


@dataclass(frozen=True)
class MovedFile:
    """One artefact file the move rewrites: its bytes as read (`sha256`), its new text,
    and the answer files its artefacts' answers go to."""

    path: str
    sha256: str
    text: str
    answers: tuple[MovedAnswers, ...]


@dataclass(frozen=True)
class LeftAnswers:
    """An artefact whose answers the move leaves in its block, and why."""

    artefact: str
    path: str
    reason: str


@dataclass(frozen=True)
class MovePlan:
    """What the move would write, and what it would leave."""

    files: tuple[MovedFile, ...]
    left: tuple[LeftAnswers, ...]

    @property
    def answer_files(self) -> int:
        return sum(len(f.answers) for f in self.files)


# --- the plan -----------------------------------------------------------------------


def plan_move(target_root: Path) -> MovePlan:
    """The move over the working tree: each artefact file whose blocks hold answers, its
    new text, and the answer files its answers go to (see the module docstring). The
    answers are checked against the tree's answer-file schema; a tree without one plans
    the move with no shape check, as validation skips it."""
    schema, _why = af.load_schema(target_root)
    discovery = discover_artefacts(target_root)
    by_file: dict[str, list[Artefact]] = {}
    left: list[LeftAnswers] = []
    for artefact in discovery.artefacts:
        if not af.block_holds_answers(artefact):
            continue
        if artefact.received:
            left.append(
                LeftAnswers(
                    artefact.location,
                    artefact.path,
                    "the project receives it by sync: its answers move where it is authored "
                    "(COR-062 point 9)",
                )
            )
            continue
        by_file.setdefault(artefact.path, []).append(artefact)
    files: list[MovedFile] = []
    for rel in sorted(by_file):
        moved, kept = _plan_file(target_root, rel, by_file[rel], schema)
        left.extend(kept)
        if moved is not None:
            files.append(moved)
    return MovePlan(tuple(files), tuple(left))


def _plan_file(
    target_root: Path,
    rel: str,
    artefacts: Sequence[Artefact],
    schema: Mapping[str, Any] | None,
) -> tuple[MovedFile | None, list[LeftAnswers]]:
    """The move of one file's artefacts: its new text and their answer files, or why each
    is left."""

    def left_all(reason: str) -> tuple[None, list[LeftAnswers]]:
        return None, [LeftAnswers(a.location, rel, reason) for a in artefacts]

    path = target_root / rel
    try:
        raw = path.read_bytes()
        written = raw.decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return left_all(f"its file cannot be read ({exc})")
    newline = line_break(written)
    if newline is None:
        return left_all("its file mixes line endings, which no one line ending would keep")
    text = universal_newlines(written)
    front_matter, _body = split_front_matter(text)
    if front_matter is None:
        return left_all("its file's front matter cannot be told")
    offset = text.index("\n") + 1
    original = _parsed(front_matter)
    if original is None:
        return left_all("its file's front matter does not parse")

    edited = front_matter
    expected = copy.deepcopy(original)
    moved: list[MovedAnswers] = []
    left: list[LeftAnswers] = []
    for artefact in artefacts:
        found = _move_artefact(artefact, edited, expected, schema)
        if isinstance(found, str):
            left.append(LeftAnswers(artefact.location, rel, found))
            continue
        edited, expected, answers = found
        if answers is not None:
            moved.append(answers)
    if edited == front_matter:
        return None, left
    after = text[:offset] + edited + text[offset + len(front_matter) :]
    after = after if newline == "\n" else after.replace("\n", newline)
    return (
        MovedFile(rel, hashlib.sha256(raw).hexdigest(), after, tuple(moved)),
        left,
    )


def _move_artefact(
    artefact: Artefact,
    front_matter: str,
    expected: dict[str, Any],
    schema: Mapping[str, Any] | None,
) -> tuple[str, dict[str, Any], MovedAnswers | None] | str:
    """One artefact's answers moved out of `front_matter`: the edited text, the front matter
    it must read as, and the answer file its answers go to (`None` where its answer keys
    hold nothing). Else why it is left, and `expected` is as it was: the keys are taken out
    of a copy, so an artefact left changes nothing the file's other artefacts are judged
    against."""
    friction: Any = artefact.friction
    if not isinstance(friction, Mapping):
        return "its friction block is not a mapping"
    block = cast(Mapping[str, Any], friction)
    entry: dict[str, Any] = {af.ARTEFACT_KEY: artefact.location}
    revalidated: Any = block.get(REVALIDATED)
    if isinstance(revalidated, Mapping) and revalidated:
        written: dict[str, Any] = {}
        for k, v in cast(Mapping[str, Any], revalidated).items():
            written[k] = _ordered_entries(v, DEFERRAL_KEYS) if k == "deferred" else v
        entry[REVALIDATED] = ordered_revalidation(written)
    elif revalidated not in (None, {}):
        return "its `revalidated` is not a mapping"
    revisited: Any = block.get(REVISITED_KEY)
    if isinstance(revisited, list) and revisited:
        entry[REVISITED_KEY] = _ordered_entries(revisited, REVISIT_KEYS)
    elif revisited not in (None, []):
        return "its `revisited` is not a list"

    answers: MovedAnswers | None = None
    if len(entry) > 1:
        text, _first, _last = answer_file_text([entry])
        name = af.moved_name(text)
        read = af.read_answer_file(name, text.encode("utf-8"))
        raw: Any = read.document
        document: Mapping[str, Any] = (
            cast(Mapping[str, Any], raw) if isinstance(raw, Mapping) else {}
        )
        if read.problem is not None or document.get(af.ANSWERS_KEY) != [entry]:
            return "its answers would not read back as an answer file writes them"
        if schema is not None:
            problems = "; ".join(
                f"{p or '(file)'}: {m}" for p, m in af.shape_findings(read, schema)
            )
            if problems:
                return f"its answers depart from the answer files' schema ({problems})"
        answers = MovedAnswers(artefact.location, af.path_of(name), text)

    keys = (*carrier_keys(artefact), bs.CONTAINER_KEY, FRICTION_KEY)
    edited = front_matter
    expected = copy.deepcopy(expected)
    holder = _holder(expected, keys)
    if holder is None:
        return "its friction block is not written where the file's front matter reads it"
    for key in _ANSWER_KEYS:
        if key not in holder:
            continue
        after = without_key(edited, keys, key)
        if after is None:
            return (
                f"its `{key}` cannot be taken out of the block exactly (written through an "
                f"alias, not starting its line, or the block's only key)"
            )
        edited = after
        del holder[key]
    if _parsed(edited) != expected:
        return "its block could not be rewritten without changing anything else"
    return edited, expected, answers


def _ordered_entries(value: Any, keys: tuple[str, ...]) -> Any:
    """A list of deferral or revisit entries, each mapping's keys in the schema's order;
    any other value as it is, for the read-back to judge."""
    if not isinstance(value, list):
        return value
    return [
        in_order(cast(Mapping[str, Any], item), keys) if isinstance(item, Mapping) else item
        for item in cast(list[Any], value)
    ]


def _parsed(front_matter: str) -> dict[str, Any] | None:
    try:
        loaded: Any = bs.as_written(_safe.load(front_matter or ""))
    except YAMLError:
        return None
    return cast(dict[str, Any], loaded) if isinstance(loaded, dict) else None


def _holder(document: dict[str, Any], keys: Sequence[str]) -> dict[str, Any] | None:
    holder: Any = document
    for step in keys:
        holder = cast(dict[str, Any], holder).get(step) if isinstance(holder, dict) else None
    return cast(dict[str, Any], holder) if isinstance(holder, dict) else None


# --- rendering ----------------------------------------------------------------------


def render_json(plan: MovePlan) -> str:
    """The plan as one stable document, keys sorted: what the migration writes."""
    document = {
        "schema_version": MOVE_PLAN_SCHEMA_VERSION,
        "report": "move-plan",
        "folder": af.FOLDER,
        "files": [
            {
                "path": f.path,
                "sha256": f.sha256,
                "text": f.text,
                "answers": [
                    {"artefact": a.artefact, "path": a.path, "text": a.text} for a in f.answers
                ],
            }
            for f in plan.files
        ],
        "left": [{"artefact": x.artefact, "path": x.path, "reason": x.reason} for x in plan.left],
    }
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def render_human(plan: MovePlan) -> str:
    """What the move would write and leave, one line each, escaped as the change check's
    human view is (`printable`): a path and a reason are the project's text, so they
    cannot move the cursor or start a line of their own."""
    lines: list[str] = []
    if not plan.files and not plan.left:
        return "No block holds an answer: the move has nothing to do.\n"
    lines.append(
        f"The move would add {plan.answer_files} answer file(s) in {af.FOLDER}/ and rewrite "
        f"{len(plan.files)} artefact file(s), taking each answer out of its block "
        f"(COR-062 point 11). Nothing is written here."
    )
    for moved in plan.files:
        lines.append(f"  {printable(moved.path)}")
        lines.extend(f"    {printable(a.artefact)} → {printable(a.path)}" for a in moved.answers)
    if plan.left:
        lines.append(f"Left in their blocks: {len(plan.left)}")
        lines.extend(f"  {printable(x.artefact)}: {printable(x.reason)}" for x in plan.left)
    return "\n".join(lines) + "\n"


__all__ = [
    "MOVE_PLAN_SCHEMA_VERSION",
    "LeftAnswers",
    "MovePlan",
    "MovedAnswers",
    "MovedFile",
    "plan_move",
    "render_human",
    "render_json",
]
