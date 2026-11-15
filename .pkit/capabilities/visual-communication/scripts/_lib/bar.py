"""The project's bar, read against the rule sets the review grades (visual-communication
DEC-042 point 3).

The configuration's schema fixes the bar's shape and refuses a grade below `professional`
(`bar` in `config.schema.json`). This module holds what a schema cannot: the check that a
bar covers only what the review grades, and in the major its set's pin says.

- **What the review grades.** Each rule of the rule sets the capability ships that it does
  not load into sessions, and each rule of a project's own set that inherits one of them
  (DEC-030 point 6). A set of the project's own covers only its own rules, never those it
  inherits. A rule withdrawn or superseded is not graded.
- **A cover** is a set's id, or one rule's id, with the set's major: `COMM@1`,
  `RS-COMM-003@1`. A cover naming nothing the review grades fails (`bar-ungraded`).
- **The major** a cover names must be the major the project pins for the set, as a project
  set's `inherits` writes it, or the set's own major where no set of the project pins it
  (`bar-major`), as a pin behind its set fails (COR-051 point 7).

Reads only. The project's own sets are those in the `rule-sets/` folder of its internal
documentation root, where the backbone finds them without configuration (COR-051 point 6).
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from _lib.findings import FAILS, Finding
from _lib.reading import ReadError, load_yaml, read_yaml
from _lib.root import CAPABILITY, CONFIG, SHIPPED

#: The configuration's key of the bar, and its two keys.
KEY = "bar"
COVERS = "covers"

#: The findings' codes.
UNGRADED = "bar-ungraded"
MAJOR = "bar-major"

#: Where the capability's rule sets lie, in the code that runs.
SHIPPED_SETS = SHIPPED / "rule-sets"

#: The folder of a project's own rule sets under its internal documentation root, and the
#: root the backbone takes where the project's configuration names none (COR-051 point 6).
RULE_SETS = "rule-sets"
BACKBONE_CONFIG = ".pkit/project/config.yaml"
DEFAULT_ROOT = "docs"

#: A rule's status that takes it out of the review's reading.
GONE = {"withdrawn", "superseded"}

_COVER = re.compile(
    r"^(?:(?P<set>[A-Z][A-Z0-9]*)|(?P<rule>RS-(?P<of>[A-Z][A-Z0-9]*)-[0-9]{3,}))"
    r"@(?P<major>0|[1-9][0-9]*)$"
)
_INHERIT = re.compile(
    rf"^(?:{re.escape(CAPABILITY)}:)?(?P<set>[A-Z][A-Z0-9]*)@(?P<major>0|[1-9][0-9]*)$"
)
_FRONT = re.compile(r"\A---\r?\n(?P<front>.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.DOTALL)


@dataclass(frozen=True)
class RuleSet:
    """A rule set as its front matter gives it: its name, its major, its rules' ids with
    each one's status, and what it inherits as written."""

    name: str
    major: int
    rules: Mapping[str, str]
    inherits: tuple[str, ...]
    loaded: bool


def findings(root: Path, data: Any) -> list[Finding]:
    """What is wrong with the bar the configuration `data` holds, or none where it holds
    no bar or one the schema refuses, which the core's data validation reports."""
    covers = _covers(data)
    if not covers:
        return []
    shipped = [each for each in _read_folder(SHIPPED_SETS) if not each.loaded]
    project = _read_folder(_project_folder(root))
    graded = {each.name: each for each in shipped}
    for each in project:
        if _inherits_graded(each, project, set(graded)):
            graded[each.name] = each
    pins = _pins(project)
    found: list[Finding] = []
    for cover in covers:
        found.extend(_judge(cover, graded, pins))
    return found


def _covers(data: Any) -> list[str]:
    """The covers a configuration holds, or none where its bar is not of the schema's
    shape."""
    bar = data.get(KEY) if isinstance(data, Mapping) else None
    covers = bar.get(COVERS) if isinstance(bar, Mapping) else None
    if not isinstance(covers, list):
        return []
    return [each for each in covers if isinstance(each, str)]


def _judge(
    cover: str, graded: Mapping[str, RuleSet], pins: Mapping[str, set[int]]
) -> list[Finding]:
    parsed = _COVER.match(cover)
    if parsed is None:
        return []  # the schema refuses the shape
    name = parsed["set"] or parsed["of"]
    major = int(parsed["major"])
    held = graded.get(name)
    where = f"{KEY}.{COVERS}"
    if held is None:
        said = (
            f"the bar covers `{cover}`, which the review does not grade: no rule set the "
            f"capability ships and loads no session with, and none of the project's own that "
            f"inherits one, is named `{name}`"
        )
        fix = f"in `{where}`, cover a set the review grades, or take `{cover}` out"
        return [Finding(UNGRADED, FAILS, said, file=CONFIG, where=where, fix=fix)]
    if parsed["rule"] is not None and held.rules.get(parsed["rule"], "withdrawn") in GONE:
        said = (
            f"the bar covers `{cover}`, which the review does not grade: the rule set "
            f"`{name}` holds no such rule, or has withdrawn or superseded it"
        )
        fix = f"in `{where}`, cover a rule the review grades, or take `{cover}` out"
        return [Finding(UNGRADED, FAILS, said, file=CONFIG, where=where, fix=fix)]
    pinned = sorted(pins.get(name, ()))
    expected = pinned or [held.major]
    if expected == [major]:
        return []
    by = "pinned by a rule set of the project's" if pinned else "the set's own"
    said = (
        f"the bar covers `{cover}` at major {major}, but the major {by} for `{name}` is "
        f"{_shown(expected)}"
    )
    written = f"{cover.rsplit('@', 1)[0]}@{expected[0]}"
    fix = f"in `{where}`, write `{written}`, once the project has reviewed it"
    return [Finding(MAJOR, FAILS, said, file=CONFIG, where=where, fix=fix)]


def _shown(majors: list[int]) -> str:
    return " and ".join(str(each) for each in majors)


def _inherits_graded(each: RuleSet, project: Iterable[RuleSet], graded: set[str]) -> bool:
    """Whether the project's set `each` inherits, directly or not, a set the review grades
    from the capability."""
    by_name = {one.name: one for one in project}
    seen: set[str] = set()
    pending = [each]
    while pending:
        current = pending.pop()
        for text in current.inherits:
            parsed = _INHERIT.match(text)
            if parsed is None or parsed["set"] in seen:
                continue
            seen.add(parsed["set"])
            if parsed["set"] in graded and text.startswith(f"{CAPABILITY}:"):
                return True
            if parsed["set"] in by_name:
                pending.append(by_name[parsed["set"]])
    return False


def _pins(project: Iterable[RuleSet]) -> dict[str, set[int]]:
    """The majors the project's sets pin, for each set name."""
    pins: dict[str, set[int]] = {}
    for each in project:
        for text in each.inherits:
            parsed = _INHERIT.match(text)
            if parsed is not None:
                pins.setdefault(parsed["set"], set()).add(int(parsed["major"]))
    return pins


def _project_folder(root: Path) -> Path:
    """The folder of the project's own rule sets: `rule-sets/` under the internal
    documentation root its backbone configuration names, `docs/` by default."""
    internal = DEFAULT_ROOT
    try:
        data = read_yaml(root / BACKBONE_CONFIG) if (root / BACKBONE_CONFIG).is_file() else None
    except ReadError:
        data = None
    docs = data.get("docs") if isinstance(data, Mapping) else None
    named = docs.get("internal") if isinstance(docs, Mapping) else None
    if isinstance(named, str) and named.strip("/"):
        internal = named.strip("/")
    return root / internal / RULE_SETS


def _read_folder(folder: Path) -> list[RuleSet]:
    """Each rule set the Markdown files directly in `folder` hold, in name order; a file
    that holds none, or cannot be read, is left out, as the backbone's validation reports
    it."""
    if not folder.is_dir():
        return []
    found = []
    for path in sorted(folder.glob("*.md")):
        read = _read_set(path)
        if read is not None:
            found.append(read)
    return found


def _read_set(path: Path) -> RuleSet | None:
    try:
        matched = _FRONT.match(path.read_text(encoding="utf-8"))
        front = load_yaml(matched["front"], path.name) if matched else None
    except (OSError, ReadError, UnicodeDecodeError):
        return None
    if not isinstance(front, Mapping) or not isinstance(front.get("rule-set"), str):
        return None
    major = re.match(r"^(0|[1-9][0-9]*)\.", str(front.get("version", "")))
    rules = front.get("rules")
    inherits = front.get("inherits")
    return RuleSet(
        name=front["rule-set"],
        major=int(major[1]) if major else 0,
        rules={
            rule: str(body.get("status", "accepted")) if isinstance(body, Mapping) else "accepted"
            for rule, body in (rules.items() if isinstance(rules, Mapping) else ())
        },
        inherits=tuple(each for each in inherits if isinstance(each, str))
        if isinstance(inherits, list)
        else (),
        loaded=front.get("loaded") is True,
    )
