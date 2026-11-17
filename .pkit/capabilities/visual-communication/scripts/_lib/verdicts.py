"""The verdict against a project's bar, from a round's review report, and whether it ends the
designer's loop (visual-communication DEC-042 points 1, 9 and 10).

- **What it reads.** The document a round's review opens its report with, as whoever
  dispatched the reviewer kept it alone: `round-<n>.yaml` in the piece's folder of
  `reviews/` in the clone's local folder, the highest round kept unless one is named. And
  the bar, from the capability's configuration alone (DEC-042 point 3), with the rule sets
  it covers, so anyone gives the same verdict again from the same report. To tell whether
  the verdict ends the loop, it also reads what `calibration` compares.
- **The verdict.** A page meets the bar where each of its unmarked grades on the rules the
  bar covers reaches the bar's grade. The piece meets it where every page does, and each
  unmarked grade it takes as a whole does. A marked grade is left out, and named apart. The
  verdict names each grade that fails the bar, and the rules the bar covers.
- **No verdict** where the configuration holds no bar (DEC-042 point 3), or where the report
  grades a rule the bar covers nowhere and lists it nowhere as not graded: a verdict that
  passed such a rule would rest on no grade of it.
- **Whether it ends the loop:** only with a verdict, and only where the hold is on
  (`calibration`). Otherwise the verdict informs, and the designer's loop ends as DEC-030
  point 2 says.
- **Refused,** so that no verdict rests on what cannot be read: a piece's name that is no
  name, no report kept, a report that cannot be read, that its schema refuses, or that is of
  another piece or round than where it is kept; and a configuration that cannot be read, is
  not bound as the configuration, or holds a bar its schema refuses or the capability's
  check fails. A report whose document does not parse is named as such, with the line and
  column where the reading stopped.

Reads only, and needs no network.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from _lib import bar, calibration, files, names
from _lib.reading import ParseError, ReadError, read_yaml
from _lib.root import CONFIG, LOCAL

#: Where the review's reports of each piece are kept, relative to the project root.
REVIEWS = f"{LOCAL}/reviews"

#: The grades, lowest first (DEC-042 point 1).
GRADES = ("below competent", "competent", "professional", "excellent")

#: Where the designer's loop ends when the verdict does not end it.
OTHERWISE = "the designer's loop ends as DEC-030 point 2 says"

_KEPT = re.compile(r"^round-([1-9][0-9]*)\.yaml$")


class Refused(Exception):
    """What the verdict would rest on cannot be read; the message says why."""


@dataclass(frozen=True)
class Grade:
    """One grade of the report: its rule, its page or None for the piece as a whole, the
    grade, its evidence, and the kind of its mark, or None where it carries none."""

    rule: str
    page: str | None
    grade: str
    evidence: str
    mark: str | None

    @property
    def place(self) -> str:
        """Where the grade lies, in words."""
        return f"page `{self.page}`" if self.page is not None else "the piece as a whole"

    def as_data(self) -> dict[str, Any]:
        on = {"page": self.page} if self.page is not None else {"piece": True}
        shown: dict[str, Any] = {"rule": self.rule, "on": on, "grade": self.grade}
        shown["evidence"] = self.evidence
        if self.mark is not None:
            shown["mark"] = self.mark
        return shown


@dataclass(frozen=True)
class Page:
    """A page the report names, with each unmarked grade of it that fails the bar."""

    page: str
    failing: tuple[Grade, ...]

    @property
    def meets(self) -> bool:
        return not self.failing


@dataclass(frozen=True)
class Verdict:
    """Whether each page meets the bar, and the piece: each page the report names, each
    unmarked grade the piece takes as a whole that fails the bar, and each marked grade left
    out."""

    pages: tuple[Page, ...]
    whole: tuple[Grade, ...]
    marked: tuple[Grade, ...]

    @property
    def meets(self) -> bool:
        return not self.whole and all(page.meets for page in self.pages)

    def as_data(self) -> dict[str, Any]:
        return {
            "meets": self.meets,
            "pages": [
                {
                    "page": page.page,
                    "meets": page.meets,
                    "failing": [each.as_data() for each in page.failing],
                }
                for page in self.pages
            ],
            "piece": {
                "meets": not self.whole,
                "failing": [each.as_data() for each in self.whole],
            },
            "marked": [each.as_data() for each in self.marked],
        }


@dataclass(frozen=True)
class Answer:
    """What the command answers: the report it read, the bar, the rules it covers, the
    verdict, and the reading the hold was compared on. `why` says why no verdict is given,
    or why the verdict ends no loop; it is empty where the verdict ends the loop."""

    piece: str
    round: int
    report: str
    bar: Mapping[str, Any] | None
    rules: tuple[str, ...] = ()
    verdict: Verdict | None = None
    why: tuple[str, ...] = ()
    reading: calibration.Reading | None = None

    @property
    def ends_the_loop(self) -> bool:
        return self.verdict is not None and not self.why

    def as_data(self) -> dict[str, Any]:
        return {
            "piece": self.piece,
            "round": self.round,
            "report": self.report,
            "bar": dict(self.bar) if self.bar is not None else None,
            "rules": list(self.rules),
            "verdict": self.verdict.as_data() if self.verdict is not None else None,
            "ends-the-loop": self.ends_the_loop,
            "why": list(self.why),
            "reading": self.reading.as_data() if self.reading is not None else None,
        }


def answer(root: Path, piece: str, round: int | None = None) -> Answer:
    """The verdict on the report of `piece`'s round `round`, or its highest round kept,
    against the bar of the project at `root`. Raises Refused where what it rests on cannot
    be read."""
    if not names.is_name(piece):
        raise Refused(f"`{piece}` is no piece's name")
    number = round if round is not None else _highest(root, piece)
    kept = f"{REVIEWS}/{piece}/round-{number}.yaml"
    report = _report(root / kept, piece, number)
    config = _bar_of(root)
    if config is None:
        none = "the configuration holds no bar, so no verdict is given (DEC-042 point 3)"
        return Answer(piece, number, kept, None, why=(f"{none}, and {OTHERWISE}",))
    held = config[bar.KEY]
    covered = bar.covered(root, config)
    rules = tuple(each.rule for each in covered)
    left_out = _left_out(report, rules)
    if left_out:
        none = (
            f"the bar covers rules the report neither grades nor lists as not graded, "
            f"{', '.join(f'`{rule}`' for rule in left_out)}: no verdict is given, and "
            f"{OTHERWISE}"
        )
        return Answer(piece, number, kept, held, rules, why=(none,))
    verdict = give(report, rules, held[bar.AT_LEAST])
    reading = calibration.read(root, covered, report["model"])
    try:
        off = calibration.off(reading, calibration.accepted())
    except calibration.Unreadable as exc:
        off = [f"the accepted calibration's data cannot be read: {exc} (DEC-042 point 9)"]
    return Answer(piece, number, kept, held, rules, verdict, tuple(off), reading)


def give(report: Mapping[str, Any], rules: Sequence[str], at_least: str) -> Verdict:
    """The verdict on `report`'s grades of `rules`, against the grade `at_least`."""
    covered = set(rules)
    floor = GRADES.index(at_least)
    pages: dict[str, list[Grade]] = {page: [] for page in _pages(report)}
    whole: list[Grade] = []
    marked: list[Grade] = []
    for each in map(_grade, report["grades"]):
        if each.rule not in covered:
            continue
        if each.mark is not None:
            marked.append(each)
        elif GRADES.index(each.grade) < floor:
            (pages[each.page] if each.page is not None else whole).append(each)
    return Verdict(
        tuple(Page(page, tuple(failing)) for page, failing in pages.items()),
        tuple(whole),
        tuple(marked),
    )


def _highest(root: Path, piece: str) -> int:
    folder = root / REVIEWS / piece
    rounds = (
        [int(found[1]) for path in folder.iterdir() if (found := _KEPT.match(path.name))]
        if folder.is_dir()
        else []
    )
    if not rounds:
        raise Refused(
            f"no report of a round of `{piece}` is kept in {REVIEWS}/{piece}/: keep each "
            f"round's document as `round-<n>.yaml` there"
        )
    return max(rounds)


def _report(path: Path, piece: str, number: int) -> dict[str, Any]:
    if not path.is_file():
        raise Refused(f"no report of round {number} of `{piece}` is kept: {path.name} is missing")
    try:
        report = files.read_bound(path, "review")
    except ParseError as exc:
        raise Refused(_unparsed(path, exc)) from exc
    except (files.FileError, ReadError) as exc:
        raise Refused(str(exc)) from exc
    problems = files.shape_problems(report, "review")
    if problems:
        raise Refused(f"{path}: its schema refuses it: {'; '.join(problems)}")
    if report["piece"] != piece or report["round"] != number:
        raise Refused(
            f"{path}: the report is of round {report['round']} of `{report['piece']}`, yet is "
            f"kept as round {number} of `{piece}`"
        )
    return report


def _unparsed(path: Path, exc: ParseError) -> str:
    """The refusal of a report whose document does not parse, naming where the reading
    stopped."""
    said = f"{path}: the report's document does not parse as YAML, so no verdict is read from it"
    if exc.line is None:
        return f"{said}: {exc.problem}"
    return f"{said}: the reading stopped at line {exc.line}, column {exc.column}: {exc.problem}"


def _bar_of(root: Path) -> dict[str, Any] | None:
    """The configuration, where it holds a bar, or None where it holds none. Raises Refused
    where it cannot be read, or its bar is refused."""
    path = root / CONFIG
    if not path.is_file():
        return None
    try:
        config = read_yaml(path)
    except ReadError as exc:
        raise Refused(str(exc)) from exc
    problem = files.binding_problem(config, "config")
    if problem is not None:
        raise Refused(f"{CONFIG}: the configuration {problem}")
    if config.get(bar.KEY) is None:
        return None
    refused = [
        each for each in files.shape_problems(config, "config") if each.startswith(f"/{bar.KEY}")
    ]
    if refused:
        raise Refused(f"{CONFIG}: the schema refuses its bar: {'; '.join(refused)}")
    failed = bar.findings(root, config)
    if failed:
        said = "; ".join(f"{each.message} ({each.code}): {each.fix}" for each in failed)
        raise Refused(f"{CONFIG}: the bar fails the capability's check: {said}")
    return config


def _left_out(report: Mapping[str, Any], rules: Sequence[str]) -> list[str]:
    """Each rule of `rules` that `report` neither grades nor lists as not graded."""
    named = {each["rule"] for each in (*report["grades"], *report.get("not-graded", ()))}
    return [rule for rule in rules if rule not in named]


def _pages(report: Mapping[str, Any]) -> list[str]:
    """Each page the report names, in the order it first names it."""
    found: dict[str, None] = {}
    for each in (*report["grades"], *report.get("not-graded", ())):
        page = each["on"].get("page")
        if page is not None:
            found.setdefault(page, None)
    return list(found)


def _grade(entry: Mapping[str, Any]) -> Grade:
    mark = entry.get("mark")
    return Grade(
        rule=entry["rule"],
        page=entry["on"].get("page"),
        grade=entry["grade"],
        evidence=entry["evidence"],
        mark=mark["kind"] if mark is not None else None,
    )
