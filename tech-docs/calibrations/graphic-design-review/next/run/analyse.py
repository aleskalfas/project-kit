# /// script
# requires-python = ">=3.11"
# dependencies = ["jsonschema==4.26.0", "referencing==0.37.0", "ruamel.yaml==0.19.1"]
# ///
"""Compute what the next calibration's plan fixes, from the review's documents and the outside
judges' (project-kit#3397).

Usage, from the repository's root:

    uv run --script analyse.py control --reference R --blind-key K --judges KEYS REPORTS
        --out control.md --json control.json
    uv run --script analyse.py run --reference R --blind-key K --judges KEYS REPORTS
        --control control.json --runs KEYS REPORTS [--folders DIR] [--judge-folders DIR]
        --out readings.md --json readings.json

`control` runs before the run, on the judges' documents alone, and its JSON is committed with
the plan. `run` runs once the run's reports are kept. It computes the control again, and stops
where it differs from the committed one. Each reads:

- `--reference`: what plan.md section 1 fixes, in `dev/reference.json`'s form.
- `--blind-key`: the judges' blind key, `key.json`, which names the decks each blind image
  stands in. A page design is read in the first deck it names for it, its *home* deck.
- `--judges`: the keys `layout.py` wrote for the judges' folders, `judge-<n>.json`, and the
  judges' documents, `judge-<n>/<CODE>.yaml`, in `judge.schema.json`'s form.
- `--runs`: the run keys, `run-<n>.json`, and the review's reports, `run-<n>/<CODE>.yaml` (the
  document alone) or `run-<n>/<CODE>.md` (the whole report, whose first fenced YAML block is
  the document). A run's `dispatch.json`, where its coordinator kept one, names the model and
  the effort it dispatched with.
- `--folders`, `--judge-folders`: where `layout.py` laid out the folders, `run-<n>/<CODE>/` and
  `judge-<n>/<CODE>/`, so the head can say what each held.

What it reads, as plan.md section 2 fixes it:

- **The bar.** It stops where the reference's bar does not stand against the rule sets at the
  root, by the capability's own check: a covered rule the review does not grade, or a set's
  major other than the one the reference names. So the rules' own words it reads are those of
  the majors the run grades by.
- **No reading.** A document that is not kept, does not parse, or that its schema refuses gives
  no reading on any page, nor on the piece. A covered rule that a page neither grades nor lists
  as not graded gives that page no reading; the piece has none where it does the same for a
  rule graded on the piece, or where a page has none. No reading enters no verdict, order, pair
  or stability. A condition that rests on one is not met, and the head counts each by its cause.
- **The verdict,** by `pkit visual verdict`'s own code, on each page and on the piece.
- **The control.** A counterpart enters a condition only where the maintainer and both judges
  put it on the same side of the bar. A clause enters only where its counterparts do, and each
  judge, read as the review is, meets it. A per-rule reference stands only where both judges
  agree with it, and each grade below professional it rests on names the rule's own words.
- **The order,** by the method the reference names.
- **The head,** where each claim the report makes about its inputs comes from: the documents
  read, the model by its name alone, every file a document lists against an allowlist, what
  each folder held, and the plan's commit. The model's name is the model id the document's
  name for it holds, as `reference.json` pins it, such as `claude-fable-5-2` in "Fable 5.2,
  model ID claude-fable-5-2". A file named by its path in the main checkout, or in the
  checkout at the root, is read as the allowlist's file of that path. A file a list names only
  to say it was not handed, as in "No piece.yaml was handed", is no read.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from itertools import combinations
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
CAPABILITY = ".pkit/capabilities/visual-communication"

GRADES = ("below competent", "competent", "professional", "excellent")
VALUE = {word: n for n, word in enumerate(GRADES, 1)}
WORD = dict(enumerate(GRADES, 1))
PROFESSIONAL = VALUE["professional"]
FENCE = re.compile(r"```ya?ml\n(.*?)```", re.S)
#: The fewest words a passage must hold to stand as a rule's own words.
FEWEST_WORDS = 3


# --- the order's methods ------------------------------------------------------------------------


def _counting(values: list[int]) -> tuple[float, ...]:
    return (-values.count(1), -values.count(2), values.count(4))


def _counting_weak(values: list[int]) -> tuple[float, ...]:
    return (-values.count(1), -values.count(2))


def _lowest(values: list[int]) -> tuple[float, ...] | None:
    return (min(values),) if values else None


def _average(values: list[int]) -> tuple[float, ...] | None:
    return (sum(values) / len(values),) if values else None


def _lowest_then_average(values: list[int]) -> tuple[float, ...] | None:
    return (min(values), sum(values) / len(values)) if values else None


#: Each method of ordering two designs by their unmarked grades on the covered rules. A higher
#: score ranks higher, and equal scores tie. A grade listed as not graded counts in none.
METHODS = {
    "counting": _counting,
    "counting-weak": _counting_weak,
    "lowest": _lowest,
    "average": _average,
    "lowest-then-average": _lowest_then_average,
}


# --- the capability's own code ------------------------------------------------------------------


class Capability:
    """The capability's code at `root`: its schema check, its verdict, its check of a bar and
    a rule's text."""

    def __init__(self, root: Path) -> None:
        sys.path.insert(0, str(root / CAPABILITY / "scripts"))
        from _lib import bar, files, verdicts

        self._root = root
        self._bar, self._files, self._verdicts = bar, files, verdicts
        self._sets = sorted((root / CAPABILITY / "rule-sets").glob("*.md"))

    def bar_problems(self, data: dict) -> list[str]:
        """Why the bar `data` gives, in the configuration's shape, does not stand against the
        rule sets at the root: a cover the review does not grade, or a major other than its
        set's. So the rules' words the analysis reads are those of the majors the run grades
        by."""
        return [each.message for each in self._bar.findings(self._root, data)]

    def review_problems(self, doc: Any) -> list[str]:
        return self._files.shape_problems(doc, "review")

    def verdict(self, doc: dict, rules: list[str], at_least: str) -> Any:
        return self._verdicts.give(doc, rules, at_least)

    def rule_text(self, rule: str) -> str:
        for path in self._sets:
            text = self._bar.rule_text(path, rule)
            if text:
                return text
        return ""


#: Curly quotes and dashes, as straight ones.
_TYPOGRAPHY = str.maketrans(
    {"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u2013": "-", "\u2014": "-"}
)


def plain(text: str) -> str:
    """`text` as the words check compares it: one case, straight quotes, no marks of emphasis
    or code, one space between words."""
    text = unicodedata.normalize("NFKC", text).translate(_TYPOGRAPHY)
    return " ".join(text.replace("**", "").replace("`", "").casefold().split())


def names_the_words(words: tuple[str, ...], rule_text: str) -> bool:
    """Whether every passage of `words` is the rule's own words: at least FEWEST_WORDS words
    that its text holds, word for word."""
    body = plain(rule_text)
    passages = [plain(each).strip(" \"'.,;:") for each in words]
    return bool(passages) and all(
        len(each.split()) >= FEWEST_WORDS and each in body for each in passages
    )


# --- the reference ------------------------------------------------------------------------------


def _set_of(rule: str) -> str:
    """The set a rule's id names, such as `GRAPHIC` for `RS-GRAPHIC-009`."""
    return rule.split("-")[1]


class Reference:
    """What plan.md section 1 fixes, read from its JSON."""

    def __init__(self, data: dict) -> None:
        self.data = data
        self.covers: list[str] = list(data["bar"]["covers"])
        self.at_least: str = data["bar"]["at-least"]
        majors = data["bar"]["majors"]
        unpinned = sorted({_set_of(rule) for rule in self.covers} - set(majors))
        if unpinned:
            sys.exit(f"error: the reference gives no major for {', '.join(unpinned)}")
        #: The bar in the configuration's shape: each covered rule with its set's major.
        self.bar = {
            "bar": {
                "covers": [f"{rule}@{majors[_set_of(rule)]}" for rule in self.covers],
                "at-least": self.at_least,
            }
        }
        places = data["places"]
        unplaced = [rule for rule in self.covers if rule not in places]
        if unplaced:
            sys.exit(f"error: the reference places no covered rule {', '.join(unplaced)}")
        self.page_rules = {rule for rule in self.covers if "page" in places[rule]}
        self.piece_rules = {rule for rule in self.covers if "piece" in places[rule]}
        self.pages = [str(n) for n in range(1, len(data["page-ids"]) + 1)]
        self.places = [*self.pages, "deck"]
        self.method: str = data["order"]
        if self.method not in METHODS:
            sys.exit(f"error: the reference names no known order, {self.method!r}")

    def side(self, place: str, design: str) -> str | None:
        """The maintainer's reading of `design` on the bar's rules: pass, fail, or None for no
        reading."""
        lists = self.data["decks"] if place == "deck" else self.data["pages"][place]
        if design in lists["pass"]:
            return "pass"
        if design in lists["fail"]:
            return "fail"
        return None

    def order(self, page: str) -> list[str]:
        """The maintainer's order of `page`'s designs with a reading, best first."""
        listed = self.data["pages"][page]
        return [code for code in listed["order"] if self.side(page, code) is not None]

    def no_reading(self, place: str) -> list[str]:
        lists = self.data["decks"] if place == "deck" else self.data["pages"][place]
        return list(lists["no-reading"])

    def designs(self, place: str) -> list[str]:
        """Every design of `place` with a reading in the reference."""
        lists = self.data["decks"] if place == "deck" else self.data["pages"][place]
        return [*lists["pass"], *lists["fail"]]


# --- the documents ------------------------------------------------------------------------------


READ_LISTS = ("read-before-grading", "read-after-grading", "read")


@dataclass(frozen=True)
class Front:
    """What a document says of itself before its grades: the model it names and its lists of
    what it read. The head's checks read it even where the grades give no reading."""

    model: str | None
    reads: list[tuple[str, str, str]]


def front_of(doc: Any) -> Front:
    reads = []
    for list_name in READ_LISTS:
        items = doc.get(list_name) if isinstance(doc, dict) else None
        for item in items if isinstance(items, list) else []:
            if isinstance(item, dict):
                what = " ".join(str(item.get("what", "")).split())
                reads.append((list_name, str(item.get("kind")), what))
    model = doc.get("model") if isinstance(doc, dict) else None
    name = model.get("name") if isinstance(model, dict) else None
    return Front(str(name) if name is not None else None, reads)


def front_of_unparsed(text: str) -> Front | None:
    """The front of a document that does not parse, from its text before its grades; None
    where that does not parse either. Nothing of its grades is read."""
    try:
        return front_of(YAML(typ="safe").load(text.split("\ngrades:", 1)[0]))
    except YAMLError:
        return None


def read_document(
    path: Path | None, kind: str, ref: Reference, cap: Capability, judge_schema: Any
) -> tuple[dict | None, str | None, Front | None]:
    """The document kept at `path`, or None with why it gives no reading; and its front, None
    where it cannot be read."""
    if path is None:
        return None, "no report was kept", None
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".md":
        found = FENCE.search(text)
        if not found:
            return None, "the report holds no fenced YAML document", None
        text = found.group(1)
    try:
        doc = YAML(typ="safe").load(text)
    except YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        where = f" at line {mark.line + 1}" if mark is not None else ""
        why = f"the document does not parse{where}: {getattr(exc, 'problem', None) or exc}"
        return None, why, front_of_unparsed(text)
    if kind == "review":
        problems = cap.review_problems(doc)
    else:
        problems = [
            f"/{'/'.join(map(str, error.absolute_path))}: {error.message}"
            for error in judge_schema.iter_errors(doc)
        ]
    if problems:
        more = f" (and {len(problems) - 3} more)" if len(problems) > 3 else ""
        return None, "its schema refuses it: " + "; ".join(problems[:3]) + more, front_of(doc)
    if kind == "review" and (doc["piece"] != ref.data["piece"] or doc["round"] != 1):
        return None, f"the document is of round {doc['round']} of `{doc['piece']}`", front_of(doc)
    return doc, None, front_of(doc)


@dataclass(frozen=True)
class Grade:
    value: int
    marked: bool
    words: tuple[str, ...]


class Reading:
    """One document's grades of one deck version: a run's review, or a judge's."""

    def __init__(
        self,
        source: str,
        code: str,
        entry: dict,
        doc: dict | None,
        problem: str | None,
        front: Front | None,
        ref: Reference,
        cap: Capability,
    ) -> None:
        self.source, self.code, self.ref = source, code, ref
        #: The model the document names and what it lists as read, read even where its
        #: grades give no reading; None where neither can be read.
        self.front = front
        self.version: str = entry["version"]
        self.problem = problem
        self.ids = {int(n): page["id"] for n, page in entry["pages"].items()}
        self.image = {int(n): page.get("image") for n, page in entry["pages"].items()}
        self.pages: dict[int, dict[str, Grade]] = {n: {} for n in self.ids}
        self.page_not: dict[int, set[str]] = {n: set() for n in self.ids}
        self.piece: dict[str, Grade] = {}
        self.piece_not: set[str] = set()
        self.unknown_pages: set[str] = set()
        self._verdict: Any = None
        if doc is None:
            return
        by_id = {page: n for n, page in self.ids.items()}
        for each in doc.get("grades") or []:
            grade = Grade(VALUE[each["grade"]], "mark" in each, tuple(each.get("words") or ()))
            self._put(each, grade, by_id)
        for each in doc.get("not-graded") or []:
            self._put(each, None, by_id)
        self._verdict = cap.verdict(doc, ref.covers, ref.at_least)

    def _put(self, each: dict, grade: Grade | None, by_id: dict[str, int]) -> None:
        rule, on = each["rule"], each["on"]
        if on.get("piece"):
            grades, nots = self.piece, self.piece_not
        elif on.get("page") in by_id:
            n = by_id[on["page"]]
            grades, nots = self.pages[n], self.page_not[n]
        else:
            self.unknown_pages.add(str(on.get("page")))
            return
        if grade is None:
            nots.add(rule)
        elif rule not in grades or grade.value < grades[rule].value:
            grades[rule] = grade

    def gap(self, n: int | None) -> str | None:
        """Why page `n`, or the piece where `n` is None, has no reading; None where it has one."""
        if self.problem:
            return self.problem
        if n is None:
            left = sorted(self.ref.piece_rules - self.piece.keys() - self.piece_not)
            if left:
                return "the piece neither grades nor lists as not graded " + ", ".join(left)
            without = [str(m) for m in self.ids if self.gap(m)]
            return f"page {', '.join(without)} has no reading" if without else None
        left = sorted(self.ref.page_rules - self.pages[n].keys() - self.page_not[n])
        if left:
            return f"page {n} neither grades nor lists as not graded {', '.join(left)}"
        return None

    def verdict(self, n: int | None) -> str | None:
        """The verdict on page `n`, or on the piece where `n` is None; None for no reading."""
        if self.gap(n):
            return None
        if n is None:
            whole = not self._verdict.whole
            return "pass" if whole and all(self.verdict(m) == "pass" for m in self.ids) else "fail"
        page = next((each for each in self._verdict.pages if each.page == self.ids[n]), None)
        return "pass" if page is None or page.meets else "fail"

    def grade(self, rule: str, n: int | None) -> Grade | None:
        """The grade of `rule` on page `n`, or on the piece; None where it has none, or no
        reading."""
        if self.gap(n):
            return None
        return (self.piece if n is None else self.pages[n]).get(rule)

    def score(self, n: int | None, method: str) -> tuple[float, ...] | None:
        """The order's score of page `n`, or of the deck where `n` is None, over its unmarked
        covered grades; None for no reading."""
        if self.gap(n):
            return None
        places = [*self.pages.values(), self.piece] if n is None else [self.pages[n]]
        values = [
            grade.value
            for grades in places
            for rule, grade in grades.items()
            if rule in self.ref.covers and not grade.marked
        ]
        return METHODS[method](values)


@dataclass
class Source:
    """One run of the review, or one judge: its readings, by deck version."""

    name: str
    kind: str
    key: dict
    readings: dict[str, Reading]


def _number(path: Path) -> int:
    return int(path.stem.split("-")[1])


def load_sources(
    keys: Path,
    reports: Path,
    prefix: str,
    kind: str,
    ref: Reference,
    cap: Capability,
    judge_schema: Any,
) -> dict[str, Source]:
    sources: dict[str, Source] = {}
    for key_path in sorted(keys.glob(f"{prefix}-*.json"), key=_number):
        key = json.loads(key_path.read_text())
        name = key_path.stem
        readings: dict[str, Reading] = {}
        for code, entry in key["folders"].items():
            kept = [reports / name / f"{code}{ext}" for ext in (".yaml", ".md")]
            path = next((each for each in kept if each.is_file()), None)
            doc, problem, front = read_document(path, kind, ref, cap, judge_schema)
            readings[entry["version"]] = Reading(name, code, entry, doc, problem, front, ref, cap)
        sources[name] = Source(name, kind, key, readings)
    return sources


class Ladder:
    """Where each design is read: a page design in its home deck, a deck as itself."""

    def __init__(self, blind_key: dict) -> None:
        self.home: dict[tuple[str, str], str] = {}
        for page, codes in blind_key["pages"].items():
            for code, versions in codes.items():
                decks = [each for each in versions if not each.startswith("anchor")]
                if decks:
                    self.home[(page, code)] = decks[0]

    def reading(self, source: Source, place: str, design: str) -> tuple[Reading, int | None]:
        if place == "deck":
            return source.readings[design], None
        return source.readings[self.home[(place, design)]], int(place)

    def verdict(self, source: Source, place: str, design: str) -> str | None:
        reading, n = self.reading(source, place, design)
        return reading.verdict(n)

    def score(self, source: Source, place: str, design: str, method: str) -> Any:
        reading, n = self.reading(source, place, design)
        return reading.score(n, method)

    def grade(self, source: Source, place: str, design: str, rule: str) -> Grade | None:
        reading, n = self.reading(source, place, design)
        return reading.grade(rule, n)

    def gap(self, source: Source, place: str, design: str) -> str | None:
        reading, n = self.reading(source, place, design)
        return reading.gap(n)


# --- the conditions' clauses --------------------------------------------------------------------


@dataclass(frozen=True)
class Clause:
    condition: int
    place: str
    text: str
    kind: str
    designs: tuple[str, ...]

    @property
    def label(self) -> str:
        where = "the deck" if self.place == "deck" else f"page {self.place}"
        return f"condition {self.condition}, {where}: {self.text} ({', '.join(self.designs)})"


def clauses(ref: Reference) -> list[Clause]:
    """Each clause of conditions 1, 2 and 4 for the bar, on its counterparts."""
    out: list[Clause] = []
    for place in ref.places:
        cp = ref.data["counterparts"][place]
        draft, failed, passed, polished = (
            cp["first-draft"],
            cp["last-failed"],
            cp["first-passed"],
            cp["last-polished"],
        )
        if draft != failed:
            out.append(Clause(1, place, "first draft below last failed", "below", (draft, failed)))
        out.append(Clause(1, place, "last failed below first passed", "below", (failed, passed)))
        if passed != polished:
            text = "first passed about equal to last polished"
            out.append(Clause(1, place, text, "equal", (passed, polished)))
        text = "last failed fails and first passed passes"
        out.append(Clause(2, place, text, "line", (failed, passed)))
    weak = ref.data["weak-deck"]
    for page, code in weak["pages"].items():
        out.append(Clause(4, page, "the weak deck's page fails", "fails", (code,)))
    out.append(Clause(4, "deck", "the weak deck fails", "fails", (weak["deck"],)))
    return out


def held(clause: Clause, source: Source, ladder: Ladder, method: str) -> bool | None:
    """Whether `source`'s readings meet `clause`; None where a counterpart has no reading."""
    place = clause.place
    if clause.kind == "below":
        low, high = (ladder.score(source, place, each, method) for each in clause.designs)
        return None if low is None or high is None else low < high
    verdicts = [ladder.verdict(source, place, each) for each in clause.designs]
    if None in verdicts:
        return None
    if clause.kind == "equal":
        return verdicts == ["pass", "pass"]
    if clause.kind == "line":
        return verdicts == ["fail", "pass"]
    return verdicts == ["fail"]


def said(value: bool | None) -> str:
    return "no reading" if value is None else ("holds" if value else "does not hold")


# --- the control, on the judges' grades ---------------------------------------------------------


def agreement(
    ref: Reference, ladder: Ladder, judges: dict[str, Source], place: str, design: str
) -> dict:
    """Whether the maintainer and both judges put `design` on the same side of the bar."""
    maintainer = ref.side(place, design)
    seen = {name: ladder.verdict(src, place, design) for name, src in judges.items()}
    if maintainer is None:
        status = "no reading in the reference"
    elif all(each == maintainer for each in seen.values()):
        status = "entered"
    elif None in seen.values():
        status = "no reading from a judge"
    else:
        status = "contested"
    return {
        "design": design,
        "maintainer": maintainer or "no reading",
        "judges": {name: each or "no reading" for name, each in seen.items()},
        "status": status,
    }


def _judged(name: str, grade: Grade | None, what: str) -> str:
    return (
        f"{name} gives {what} no grade"
        if grade is None
        else f"{name} grades {what} " + (WORD[grade.value])
    )


def rule_control(
    rule: str, ref: Reference, ladder: Ladder, judges: dict[str, Source], cap: Capability
) -> dict:
    """Which of `rule`'s references stand: its pairs, the designs the maintainer passes, and the
    weak deck's pages."""
    text = cap.rule_text(rule)

    def below(place: str, design: str, what: str) -> list[str]:
        why = []
        for name, src in judges.items():
            grade = ladder.grade(src, place, design, rule)
            if grade is None and ladder.gap(src, place, design):
                why.append(f"{name} gives {what} no reading")
            elif grade is None or grade.value >= PROFESSIONAL:
                why.append(_judged(name, grade, what))
            elif not names_the_words(grade.words, text):
                why.append(f"{name} names none of the rule's own words behind its grade of {what}")
        return why

    def at_least(place: str, design: str, what: str, ungraded: bool = False) -> list[str]:
        """Why a judge does not hold `design` at professional or above on the rule. Where
        `ungraded`, a rule the judge lists as not graded there stands with it."""
        why = []
        for name, src in judges.items():
            grade = ladder.grade(src, place, design, rule)
            if grade is None and ladder.gap(src, place, design):
                why.append(f"{name} gives {what} no reading")
            elif grade is None and ungraded:
                continue
            elif grade is None or grade.value < PROFESSIONAL:
                why.append(_judged(name, grade, what))
        return why

    pairs = []
    for pair in ref.data["pairs"].get(rule, []):
        place = "deck" if pair["on"] == "piece" else pair["on"]
        why = []
        if ref.side(place, pair["base"]) != "pass":
            why.append(f"the maintainer does not pass the base {pair['base']}")
        if ref.side(place, pair["variant"]) != "fail":
            why.append(f"the maintainer does not fail the variant {pair['variant']}")
        why += at_least(place, pair["base"], f"the base {pair['base']}")
        why += below(place, pair["variant"], f"the variant {pair['variant']}")
        pairs.append({**pair, "status": "contested" if why else "entered", "why": why})

    on_pages = rule in ref.page_rules
    on_piece = rule in ref.piece_rules
    passed = []
    for place in ref.places:
        if (place == "deck" and not on_piece) or (place != "deck" and not on_pages):
            continue
        listed = ref.data["decks"] if place == "deck" else ref.data["pages"][place]
        for design in listed["pass"]:
            why = at_least(place, design, design, ungraded=True)
            status = "contested" if why else "entered"
            passed.append({"place": place, "design": design, "status": status, "why": why})

    weak = []
    targets = [(page, code) for page, code in ref.data["weak-deck"]["pages"].items() if on_pages]
    if on_piece:
        targets.append(("deck", ref.data["weak-deck"]["deck"]))
    for place, design in targets:
        why = below(place, design, design)
        status = "not a reference" if why else "entered"
        weak.append({"place": place, "design": design, "status": status, "why": why})
    return {"pairs": pairs, "passed": passed, "weak": weak}


def control(ref: Reference, ladder: Ladder, judges: dict[str, Source], cap: Capability) -> dict:
    """The control: each condition on each judge's grades, and what enters the conditions."""
    out_clauses = []
    for clause in clauses(ref):
        agreed = [agreement(ref, ladder, judges, clause.place, each) for each in clause.designs]
        by_judge = {name: held(clause, src, ladder, ref.method) for name, src in judges.items()}
        left = sorted({each["status"] for each in agreed} - {"entered"})
        if left:
            status = "contested" if "contested" in left else " and ".join(left)
        elif not all(by_judge.values()):
            missed = [name for name, each in by_judge.items() if not each]
            status = f"not met by {' and '.join(missed)}"
        else:
            status = "entered"
        out_clauses.append(
            {
                "condition": clause.condition,
                "place": clause.place,
                "text": clause.text,
                "kind": clause.kind,
                "designs": list(clause.designs),
                "agreement": agreed,
                "judges": {name: said(each) for name, each in by_judge.items()},
                "status": status,
            }
        )
    contested = []
    for place in ref.places:
        for design in ref.designs(place):
            found = agreement(ref, ladder, judges, place, design)
            if found["status"] != "entered":
                contested.append({"place": place, **found})
    rules = {rule: rule_control(rule, ref, ladder, judges, cap) for rule in ref.covers}
    return {"method": ref.method, "clauses": out_clauses, "contested": contested, "rules": rules}


# --- the readings of a run ----------------------------------------------------------------------


def tau_b(xs: list[Any], ys: list[Any]) -> float:
    concordant = discordant = tied_x = tied_y = 0
    for i, j in combinations(range(len(xs)), 2):
        a = (xs[i] > xs[j]) - (xs[i] < xs[j])
        b = (ys[i] > ys[j]) - (ys[i] < ys[j])
        if a == 0 and b == 0:
            continue
        if a == 0:
            tied_x += 1
        elif b == 0:
            tied_y += 1
        elif a == b:
            concordant += 1
        else:
            discordant += 1
    den = ((concordant + discordant + tied_x) * (concordant + discordant + tied_y)) ** 0.5
    return (concordant - discordant) / den if den else 0.0


def kept_in_order(scores: list[Any]) -> float:
    """The share of the reference's ordered pairs, best first, the scores keep strictly in
    order."""
    pairs = list(combinations(range(len(scores)), 2))
    return sum(1 for i, j in pairs if scores[i] > scores[j]) / len(pairs) if pairs else 0.0


def images(ref: Reference, runs: dict[str, Source], page: str) -> dict[str, list]:
    """Each image of `page` with a reading in the reference, with its verdict in each deck of
    each run: (run, deck, verdict, why none)."""
    n = int(page)
    left_out = set(ref.no_reading(page))
    seen: dict[str, list] = {}
    for name, src in runs.items():
        for version, reading in src.readings.items():
            code = reading.image.get(n)
            if code is None or code in left_out:
                continue
            seen.setdefault(code, []).append((name, version, reading.verdict(n), reading.gap(n)))
    return seen


def stability_line(code: str, entries: list) -> tuple[str, str]:
    """`code`'s state across the runs and its decks, and how it reads. It is unstable where
    two of its readings differ, not read where they agree but one is missing, and stable
    where every reading is given and agrees."""
    read = [(run, deck, verdict) for run, deck, verdict, _ in entries if verdict is not None]
    unread = [(run, deck) for run, deck, verdict, _ in entries if verdict is None]
    verdicts = {verdict for _, _, verdict in read}
    if len(verdicts) == 1 and not unread:
        return "stable", f"{code} ({read[0][2]})"
    parts = []
    for run in sorted({run for run, _, _ in read}, key=lambda name: _number(Path(name))):
        counts = Counter(verdict for name, _, verdict in read if name == run)
        common = counts.most_common(1)[0][0]
        part = f"{run} {common}" + (f" ×{counts[common]}" if counts[common] > 1 else "")
        rest = [f"{v} in {deck}" for name, deck, v in read if name == run and v != common]
        parts.append(part + (", " + ", ".join(rest) if rest else ""))
    if unread:
        runs = Counter(run for run, _ in unread)
        decks = sorted({deck for _, deck in unread})
        said_runs = ", ".join(f"{run} ×{n}" for run, n in sorted(runs.items()))
        parts.append(f"no reading in {said_runs} ({', '.join(decks)})")
    state = "unstable" if len(verdicts) > 1 else "not read"
    return state, f"{code}: {'; '.join(parts)}"


def run_readings(
    ref: Reference,
    ladder: Ladder,
    runs: dict[str, Source],
    fixed: dict,
    cap: Capability,
) -> dict:
    """The four conditions for the bar and each covered rule's readings, on the runs."""
    method = ref.method
    result: dict[str, Any] = {"clauses": [], "places": {}, "evidence": {}, "false": {}}
    by_place: dict[tuple[int, str], list[bool]] = {}
    for entry in fixed["clauses"]:
        clause = Clause(
            entry["condition"],
            entry["place"],
            entry["text"],
            entry["kind"],
            tuple(entry["designs"]),
        )
        if entry["status"] != "entered":
            result["clauses"].append({**_brief(entry), "status": entry["status"], "runs": {}})
            continue
        outcome = {name: held(clause, src, ladder, method) for name, src in runs.items()}
        scores = {}
        if clause.kind == "below":
            scores = {
                name: [
                    str(ladder.score(src, clause.place, each, method)) for each in clause.designs
                ]
                for name, src in runs.items()
            }
        result["clauses"].append(
            {
                **_brief(entry),
                "status": "entered",
                "runs": {name: said(each) for name, each in outcome.items()},
                "scores": scores,
            }
        )
        by_place.setdefault((clause.condition, clause.place), []).extend(
            each is True for each in outcome.values()
        )
    for condition in (1, 2, 4):
        cells = {}
        for place in ref.places:
            got = by_place.get((condition, place))
            cells[place] = "no counterpart" if got is None else ("met" if all(got) else "not met")
        result["places"][condition] = cells

    # Condition 3, stability: each image with a reading in the reference, in every run and deck.
    stability: dict[str, Any] = {}
    for page in ref.pages:
        lines: dict[str, list[str]] = {"stable": [], "unstable": [], "not read": []}
        for code, entries in sorted(images(ref, runs, page).items()):
            state, line = stability_line(code, entries)
            lines[state].append(line)
        stability[page] = {**lines, "left out": ref.no_reading(page)}
    lines = {"stable": [], "unstable": [], "not read": []}
    for version in ref.designs("deck"):
        entries = [
            (name, version, src.readings[version].verdict(None), src.readings[version].gap(None))
            for name, src in runs.items()
        ]
        state, line = stability_line(version, entries)
        lines[state].append(line)
    stability["deck"] = {**lines, "left out": ref.no_reading("deck")}
    result["stability"] = stability
    result["places"][3] = {
        place: "met" if not (cell["unstable"] or cell["not read"]) else "not met"
        for place, cell in stability.items()
    }

    # The evidence: the review's order against the maintainer's, by one rule on every page.
    for page in ref.pages:
        order = ref.order(page)
        his = [-i for i in range(len(order))]
        per_run = {}
        for name, src in runs.items():
            scores = [ladder.score(src, page, code, method) for code in order]
            kept = [i for i, score in enumerate(scores) if score is not None]
            ours = [scores[i] for i in kept]
            theirs = [his[i] for i in kept]
            per_run[name] = {
                "designs": len(kept),
                "no reading in the run": [order[i] for i, s in enumerate(scores) if s is None],
                "tau-b": round(tau_b(ours, theirs), 2),
                "kept in order": round(kept_in_order(ours), 2),
            }
        result["evidence"][page] = {"left out": ref.no_reading(page), "runs": per_run}

    # Reported, counting toward no acceptance: the verdict against the reference everywhere.
    contested = {(each["place"], each["design"]) for each in fixed["contested"]}
    for name, src in runs.items():
        false_pass, false_fail, no_reading = [], [], []
        for version, reading in sorted(src.readings.items()):
            places = [(str(n), reading.image.get(n), n) for n in reading.ids]
            places.append(("deck", version, None))
            for place, design, n in places:
                if design is None:
                    continue
                want = ref.side(place, design)
                got = reading.verdict(n)
                where = f"p{place} {design} in {version}" if n is not None else f"deck {version}"
                where += " (contested)" if (place, design) in contested else ""
                if want and got is None:
                    no_reading.append(where)
                elif want and got != want:
                    (false_pass if got == "pass" else false_fail).append(where)
        result["false"][name] = {
            "false passes": false_pass,
            "false fails": false_fail,
            "no reading": no_reading,
        }

    result["rules"] = {
        rule: rule_readings(rule, ref, ladder, runs, fixed["rules"][rule]) for rule in ref.covers
    }
    bar = {}
    for condition in (1, 2, 3, 4):
        cells = list(result["places"][condition].values())
        read = [each for each in cells if each != "no counterpart"]
        if not read:
            bar[condition] = "no counterpart"
        elif all(each == "met" for each in read):
            bar[condition] = f"met on the {len(read)} of {len(cells)} places with a counterpart"
        else:
            bar[condition] = "not met"
    result["bar"] = bar
    return result


def _brief(entry: dict) -> dict:
    keys = ("condition", "place", "text", "designs")
    return {key: entry[key] for key in keys}


def _word(grade: Grade | None) -> str:
    if grade is None:
        return "no grade"
    return WORD[grade.value] + (" (marked)" if grade.marked else "")


def rule_readings(
    rule: str, ref: Reference, ladder: Ladder, runs: dict[str, Source], fixed: dict
) -> dict:
    """`rule`'s readings on the runs: its pairs, the designs it must pass, its stability and the
    weak deck."""
    out: dict[str, Any] = {"pairs": [], "passed": [], "weak": []}
    order_ok: list[bool] = []
    line_ok: list[bool] = []
    for pair in fixed["pairs"]:
        place = "deck" if pair["on"] == "piece" else pair["on"]
        entry = {key: pair[key] for key in ("on", "base", "variant")}
        if pair["status"] != "entered":
            out["pairs"].append({**entry, "status": pair["status"], "why": pair["why"]})
            continue
        per_run = {}
        for name, src in runs.items():
            base = ladder.grade(src, place, pair["base"], rule)
            variant = ladder.grade(src, place, pair["variant"], rule)
            a = base is not None and base.value >= PROFESSIONAL
            b = variant is not None and variant.value < PROFESSIONAL
            c = base is not None and variant is not None and variant.value < base.value
            order_ok.append(c)
            line_ok.append(a and b)
            per_run[name] = {
                "base": _word(base),
                "variant": _word(variant),
                "(a)": a,
                "(b)": b,
                "(c)": c,
            }
        out["pairs"].append({**entry, "status": "entered", "runs": per_run})
    for item in fixed["passed"]:
        if item["status"] != "entered":
            out["passed"].append({**item})
            continue
        below, unread = [], Counter()
        for name, src in runs.items():
            for reading, n in _everywhere(ladder, src, item["place"], item["design"]):
                grade = reading.grade(rule, n)
                if reading.gap(n):
                    unread[name] += 1
                elif grade is not None and not grade.marked and grade.value < PROFESSIONAL:
                    below.append(f"{name} in {reading.version}: {WORD[grade.value]}")
        line_ok.append(not below and not unread)
        out["passed"].append({**item, "below": below, "no reading": dict(unread)})
    weak_ok: list[bool] = []
    for item in fixed["weak"]:
        if item["status"] != "entered":
            out["weak"].append({**item})
            continue
        missed = []
        for name, src in runs.items():
            grade = ladder.grade(src, item["place"], item["design"], rule)
            if grade is None or grade.value >= PROFESSIONAL:
                missed.append(f"{name} {_word(grade)}")
        weak_ok.append(not missed)
        out["weak"].append({**item, "not below": missed})

    # Stability: each image, or deck, with a reading in the reference, on one side of
    # professional in every run and every deck.
    sides: dict[str, list[int | None]] = {}
    on_piece = rule in ref.piece_rules
    for src in runs.values():
        for version, reading in src.readings.items():
            if on_piece and version in ref.designs("deck"):
                grade = reading.grade(rule, None)
                sides.setdefault(version, []).append(None if reading.gap(None) else _value(grade))
            if rule not in ref.page_rules:
                continue
            for n, code in reading.image.items():
                if code is None or code in ref.no_reading(str(n)):
                    continue
                grade = reading.grade(rule, n)
                sides.setdefault(f"p{n} {code}", []).append(
                    None if reading.gap(n) else _value(grade)
                )
    crossing = sorted(
        key
        for key, values in sides.items()
        if len({each >= PROFESSIONAL for each in values if each}) > 1
    )
    not_read = sorted(key for key, values in sides.items() if None in values)
    graded = {key: [each for each in values if each] for key, values in sides.items()}
    exact = sum(1 for values in graded.values() if values and len(set(values)) == 1)
    spread = max((max(v) - min(v) for v in graded.values() if v), default=0)
    out["stability"] = {
        "places": len(sides),
        "one grade": exact,
        "widest spread": spread,
        "crossing professional": crossing,
        "no reading": not_read,
    }
    out["matrix"] = {
        1: _cell(order_ok),
        2: _cell(line_ok),
        3: "met" if not crossing and not not_read else "not met",
        4: _cell(weak_ok),
    }
    return out


def _value(grade: Grade | None) -> int:
    """A grade's value, 0 where the rule is listed as not graded."""
    return 0 if grade is None else grade.value


def _cell(checks: list[bool]) -> str:
    return "no counterpart" if not checks else ("met" if all(checks) else "not met")


def _everywhere(
    ladder: Ladder, source: Source, place: str, design: str
) -> list[tuple[Reading, int | None]]:
    """Every reading of `design` in `source`: a deck as itself, a page image in each deck it
    stands in."""
    if place == "deck":
        return [(source.readings[design], None)]
    n = int(place)
    return [(r, n) for r in source.readings.values() if r.image.get(n) == design]


# --- the head: each claim about the inputs, from a check ----------------------------------------

PATH = re.compile(r"[\w.\-/]+")
NAMED = re.compile(r"\.(?:md|json|ya?ml|png|jpe?g|svg|py|txt|html|css|js)$")


def named_files(text: str) -> list[str]:
    """Each path or file name `text` names."""
    out = []
    for token in PATH.findall(text):
        token = token.rstrip(".,;:")
        if NAMED.search(token) or ("/" in token.strip("/") and any(c.isalpha() for c in token)):
            out.append(token)
    return out


#: A word of a thing a list may say was not handed: any but the clause's verb.
_NOT_HANDED_WORD = r"(?!(?:was|were|handed)\b)[\w.\-/]+"
#: One thing a list may say was not handed, such as `piece.yaml` or `source file`: up to three
#: words.
_NOT_HANDED_ITEM = rf"{_NOT_HANDED_WORD}(?:[ \t]+{_NOT_HANDED_WORD}){{0,2}}"
#: A clause that names things only to say they were not handed, such as "No piece.yaml was
#: handed", "No piece.yaml and no component was handed" or "No piece.yaml, brand or source
#: file was handed".
NOT_HANDED = re.compile(
    rf"\b[Nn]o\s+{_NOT_HANDED_ITEM}"
    rf"(?:(?:\s*,\s*(?:(?:and|or|nor)\s+)?|\s+(?:and|or|nor)\s+)(?:no\s+)?{_NOT_HANDED_ITEM})*"
    r"\s+(?:was|were)\s+handed\b"
)


def said_read(text: str) -> tuple[list[str], list[str]]:
    """The files `text` names as read, and those it names only to say they were not handed. A
    file named in a clause that says it was not handed is no read; the same file named
    anywhere else in `text` still is."""
    not_handed = [token for found in NOT_HANDED.finditer(text) for token in named_files(found[0])]
    return named_files(NOT_HANDED.sub(" ", text)), not_handed


#: A model's id, as a harness names it: lower-case words and numbers joined by hyphens, such as
#: `claude-fable-5-2`.
MODEL_ID = re.compile(r"(?<![\w.-])[a-z][a-z0-9]*(?:[-.][a-z0-9]+)+(?![\w-])")


def model_id(name: str) -> str | None:
    """The model id the name a document gives its model holds, such as `claude-fable-5-2` in
    "Fable 5.2, model ID claude-fable-5-2"; None where it holds none, or more than one."""
    ids = {each for each in MODEL_ID.findall(name) if "-" in each and re.search(r"\d", each)}
    return next(iter(ids)) if len(ids) == 1 else None


def allowed_paths(root: Path, prefixes: list[str]) -> list[str]:
    """Every file the allowlist's entries name: a file, or each file under a folder."""
    out: list[str] = []
    for prefix in prefixes:
        target = root / prefix
        if target.is_file():
            out.append(prefix)
        elif target.is_dir():
            out += [
                p.relative_to(root).as_posix() for p in sorted(target.rglob("*")) if p.is_file()
            ]
    return out


def checkout_starts(root: Path) -> list[str]:
    """The starts of a path that name a checkout of this repository, longest first: the main
    checkout, from which the coordinators dispatch, by its absolute path, and the checkout at
    `root`, by its absolute path and, for a worktree, by its path in the main checkout. A
    document may name a file of the allowlist so, such as the judges' schema, which lies in
    the worktree that holds the plan."""
    top = root.resolve()
    starts = {top.as_posix().strip("/") + "/"}
    common = git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if common.returncode == 0:
        main = Path(common.stdout.strip()).parent
        starts.add(main.as_posix().strip("/") + "/")
        if top != main and top.is_relative_to(main):
            starts.add(top.relative_to(main).as_posix() + "/")
    return sorted(starts, key=len, reverse=True)


def placed(
    token: str, own: str, own_files: set[str], allowed: list[str], starts: list[str]
) -> bool:
    """Whether `token` names the document's own folder, a file in it, or a file the allowlist
    holds, in the checkout the analysis reads or the one the coordinators dispatch from. A
    path in another checkout, such as another worktree, names no file of the allowlist."""
    name = token.strip("/")
    start = next((each for each in starts if name.startswith(each)), "")
    name = name[len(start) :]
    if f"/{own}/" in f"/{name}/" or name in own_files:
        return True
    return any(p == name or p.endswith("/" + name) or f"/{name}/" in f"/{p}" for p in allowed)


def folder_files(folders: Path | None, source: Source, code: str) -> dict[str, str] | None:
    if folders is None:
        return None
    folder = folders / source.name / code
    if not folder.is_dir():
        return None
    return {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(folder.iterdir())
        if p.is_file()
    }


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)


def head(
    ref: Reference,
    root: Path,
    sources: dict[str, Source],
    folders: dict[str, Path | None],
    reports: dict[str, Path],
) -> dict:
    """Each claim the report may make about its inputs, each from a check."""
    out: dict[str, Any] = {"documents": {}, "no reading": {}, "reads": {}, "folders": {}}
    allowed = {kind: allowed_paths(root, ref.data["reads"][kind]) for kind in ("review", "judge")}
    starts = checkout_starts(root)
    #: The model ids the documents name, and their names for the model as they write them.
    ids: dict[str, Counter] = {"review": Counter(), "judge": Counter()}
    written: dict[str, Counter] = {"review": Counter(), "judge": Counter()}
    for name, src in sources.items():
        readings = list(src.readings.values())
        problems = [(r.code, r.version, r.problem) for r in readings if r.problem]
        out["documents"][name] = {
            "folders": len(readings),
            "kept": sum(1 for r in readings if r.problem != "no report was kept"),
            "read": sum(1 for r in readings if not r.problem),
            "not read": [f"{code} ({version}): {why}" for code, version, why in problems],
        }
        pages: Counter = Counter()
        causes: dict[str, list[str]] = {}
        for r in readings:
            for n in [*r.ids, None]:
                why = r.gap(n)
                if why:
                    pages["the piece" if n is None else "pages"] += 1
                if why and not r.problem:
                    # Name the cause without its page, so causes alike group together.
                    cause = re.sub(r"^page \d+ ", "the page ", why)
                    where = "the piece" if n is None else f"page {n}"
                    causes.setdefault(cause, []).append(f"{r.code} ({r.version}) {where}")
            if r.unknown_pages:
                cause = f"grades pages the key does not name, {sorted(r.unknown_pages)}"
                causes.setdefault(cause, []).append(f"{r.code} ({r.version})")
        out["no reading"][name] = {
            "pages": pages["pages"],
            "pieces": pages["the piece"],
            "causes beside an unread document": causes,
        }
        for r in readings:
            if r.front is None:
                said = "(its front does not parse)"
            elif r.front.model is None:
                said = "(no name)"
            else:
                written[src.kind][r.front.model] += 1
                said = model_id(r.front.model) or f"{r.front.model} (no one model id)"
            ids[src.kind][said] += 1
        reads, named = [], Counter()
        for r in readings:
            if r.front is None:
                reads.append({"code": r.code, "version": r.version, "unreadable": True})
                continue
            own_files = set(src.key["folders"][r.code].get("digests") or {})
            own_files |= set(folder_files(folders.get(src.kind), src, r.code) or ())
            outside = {}
            for _, _, what in r.front.reads:
                read, not_handed = said_read(what)
                named["not handed"] += len(not_handed)
                for token in read:
                    named["files"] += 1
                    own = f"{name}/{r.code}"
                    if not placed(token, own, own_files, allowed[src.kind], starts):
                        outside.setdefault(token, what)
            early = [
                what
                for list_name, kind, what in r.front.reads
                if list_name == "read-before-grading" and kind in ("brief-file", "earlier-reports")
            ]
            if outside or early:
                reads.append(
                    {
                        "code": r.code,
                        "version": r.version,
                        "names outside the allowlist": outside,
                        "lists before grading a brief file or earlier reports": early,
                        "from the head of a document that does not parse": bool(r.problem),
                    }
                )
        out["reads"][name] = {
            "documents": len(readings),
            "files named": named["files"],
            "files named as not handed": named["not handed"],
            "flagged": reads,
        }
        if src.kind == "judge":
            without = sum(
                1
                for r in readings
                for grades in [*r.pages.values(), r.piece]
                for grade in grades.values()
                if grade.value < PROFESSIONAL and not grade.words
            )
            out.setdefault("judges' words", {})[name] = {
                "grades below professional without words": without
            }
    pinned = ref.data.get("model")
    review_ids = sorted(ids["review"])  # a front that names none, or does not parse, counts
    out["model"] = {
        "review ids": dict(ids["review"]),
        "judge ids": dict(ids["judge"]),
        "review names as written": dict(written["review"]),
        "judge names as written": dict(written["judge"]),
        "pinned": pinned,
        "one id": len(review_ids) == 1,
        "the pinned id": (review_ids == [pinned]) if pinned and review_ids else None,
    }
    out["dispatch"] = {}
    for name, path in reports.items():
        record = path / name / "dispatch.json"
        out["dispatch"][name] = (
            json.loads(record.read_text()) if record.is_file() else "no dispatcher's record kept"
        )
    for name, src in sources.items():
        held: dict[str, list[str]] = {}
        for code, entry in src.key["folders"].items():
            recorded = entry.get("digests") or {}
            found = folder_files(folders.get(src.kind), src, code)
            if found is None:
                held.setdefault("no folder given", []).append(code)
                continue
            extra = sorted(set(found) - set(recorded))
            missing = sorted(set(recorded) - set(found))
            differ = sorted(k for k in set(found) & set(recorded) if found[k] != recorded[k])
            state = (
                f"holds files the key does not record {extra}, lacks {missing}, "
                f"differs from it in {differ}"
                if extra or missing or differ
                else "holds exactly the files the key records, byte for byte"
            )
            held.setdefault(state, []).append(code)
        out["folders"][name] = held
    out["handed alike"] = handed_alike(sources)
    out["laid out"] = laid_out(root, sources)
    return out


def handed_alike(sources: dict[str, Source]) -> list[str] | str:
    """Whether every run's review and every judge were handed the same files for each version,
    by the digests each key records."""
    per_version: dict[str, dict[str, dict]] = {}
    for name, src in sources.items():
        for entry in src.key["folders"].values():
            per_version.setdefault(entry["version"], {})[name] = entry.get("digests") or {}
    if not any(d for versions in per_version.values() for d in versions.values()):
        return "no key records what was handed"
    differing = []
    for version, by_source in sorted(per_version.items()):
        recorded = {name: d for name, d in by_source.items() if d}
        unrecorded = sorted(name for name, d in by_source.items() if not d)
        if len({json.dumps(d, sort_keys=True) for d in recorded.values()}) > 1:
            differing.append(f"{version}: the handed files differ between {sorted(recorded)}")
        if unrecorded:
            differing.append(f"{version}: {', '.join(unrecorded)} record nothing handed")
    return differing or "every source was handed the same files for each version"


def laid_out(root: Path, sources: dict[str, Source]) -> dict[str, str]:
    """For each source, whether its folders were laid out from a committed plan, unchanged
    since."""
    out = {}
    for name, src in sources.items():
        stamp = src.key.get("laid-out")
        if not stamp:
            out[name] = "the key records no plan commit"
            continue
        commit, at, plan = stamp["commit"], stamp["at"], stamp["plan"]
        dated = git(root, "log", "-1", "--format=%cI", commit)
        if dated.returncode:
            out[name] = f"the key's plan commit {commit} is not in this repository"
            continue
        when = dated.stdout.strip()
        if git(root, "cat-file", "-e", f"{commit}:{plan}").returncode:
            out[name] = f"laid out at {at} from {commit[:12]} ({when}), WHICH HOLDS NO {plan}"
            continue
        # Against the working tree, so an uncommitted edit since counts as a change.
        changed = git(root, "diff", "--quiet", commit, "--", plan).returncode
        before = datetime.fromisoformat(when) < datetime.fromisoformat(at)
        out[name] = (
            f"laid out at {at} from {plan} at {commit[:12]} ({when}); "
            + ("committed before it was laid out" if before else "COMMITTED AFTER")
            + ("; unchanged since" if changed == 0 else "; CHANGED SINCE")
            + ("" if stamp.get("clean") else "; THE PLAN'S FOLDER HELD UNCOMMITTED CHANGES")
        )
    return out


# --- the report ---------------------------------------------------------------------------------


def lines_of_head(found: dict) -> list[str]:
    say: list[str] = ["## The head: each claim about the inputs, from a check", ""]
    for name, d in found["documents"].items():
        say.append(
            f"- **{name}:** {d['folders']} folders, {d['kept']} documents kept, "
            f"{d['read']} read, {len(d['not read'])} giving no reading"
        )
        say += [f"  - {line}" for line in d["not read"]]
    say += ["", "**No reading, by page and piece** (read as no reading in every condition):"]
    for name, d in found["no reading"].items():
        say.append(f"- {name}: {d['pages']} pages and {d['pieces']} pieces with no reading")
        for cause, where in d["causes beside an unread document"].items():
            say.append(f"  - {len(where)} where {cause}: {', '.join(where)}")
    model = found["model"]
    say += [
        "",
        "**The model, by its name alone,** the model id each document's name for it holds: "
        f"the reviews name {model['review ids'] or 'none'}; one id: {model['one id']}; "
        f"the reference pins {model['pinned'] or 'none'}; the pinned id: "
        f"{model['the pinned id']}. The judges name {model['judge ids'] or 'none'}. "
        f"As written, the reviews name {model['review names as written'] or 'none'}, and the "
        f"judges {model['judge names as written'] or 'none'}.",
        "",
        "**The effort, from the dispatcher's record:**",
    ]
    say += [f"- {name}: {record}" for name, record in found["dispatch"].items()]
    say += ["", "**Reads outside the allowlist,** by every file each document lists:"]
    for name, d in found["reads"].items():
        flagged = d["flagged"]
        say.append(
            f"- {name}: {d['files named']} files named as read over {d['documents']} documents, "
            f"and {d['files named as not handed']} named only as not handed; "
            f"{len(flagged)} documents flagged"
        )
        for each in flagged:
            where = f"  - {each['code']} ({each['version']})"
            if each.get("unreadable"):
                say.append(f"{where}: its lists of what it read do not parse")
                continue
            for token, what in each["names outside the allowlist"].items():
                say.append(f"{where}: `{token}`, in “{what}”")
            for what in each["lists before grading a brief file or earlier reports"]:
                say.append(f"{where}: before grading, a brief file or earlier reports: “{what}”")
    if "judges' words" in found:
        say += ["", "**The judges' words:**"]
        say += [
            f"- {name}: {d['grades below professional without words']} grades below "
            "professional name no words"
            for name, d in found["judges' words"].items()
        ]
    say += ["", "**What each folder held,** against its key:"]
    for name, held in found["folders"].items():
        for state, codes in held.items():
            say.append(f"- {name}: {len(codes)} {state}")
    alike = found["handed alike"]
    say += ["", "**Handed alike:** " + (alike if isinstance(alike, str) else "")]
    if not isinstance(alike, str):
        say += [f"- {line}" for line in alike]
    say += ["", "**Laid out:**"]
    say += [f"- {name}: {line}" for name, line in found["laid out"].items()]
    say.append("")
    return say


def lines_of_control(found: dict) -> list[str]:
    say = [f"## The control, on the judges' grades (order: {found['method']})", ""]
    say.append(
        "Each clause, its counterparts' agreement, each judge read as the review, and "
        "whether it enters:"
    )
    say.append("")
    for each in found["clauses"]:
        where = "the deck" if each["place"] == "deck" else f"page {each['place']}"
        agreed = "; ".join(
            f"{a['design']} maintainer {a['maintainer']}, "
            + ", ".join(f"{n} {v}" for n, v in a["judges"].items())
            for a in each["agreement"]
        )
        judged = ", ".join(f"{n} {v}" for n, v in each["judges"].items())
        say.append(
            f"- condition {each['condition']}, {where}, {each['text']}: **{each['status']}**. "
            f"{agreed}. As the review: {judged}."
        )
    say += ["", "**Contested designs, and those a judge gives no reading, reported apart:**"]
    say += [
        f"- {'the deck' if c['place'] == 'deck' else 'page ' + c['place']} {c['design']}: "
        f"maintainer {c['maintainer']}, "
        + ", ".join(f"{n} {v}" for n, v in c["judges"].items())
        + f" ({c['status']})"
        for c in found["contested"]
    ]
    say += ["", "**Each covered rule's references:**", ""]
    for rule, d in found["rules"].items():
        say.append(f"- **{rule}**")
        for pair in d["pairs"]:
            say.append(
                f"  - pair {pair['base']} → {pair['variant']} ({pair['on']}): {pair['status']}"
                + (f"; {'; '.join(pair['why'])}" if pair["why"] else "")
            )
        entered = [i["design"] for i in d["passed"] if i["status"] == "entered"]
        contested = [
            f"{i['design']} ({'; '.join(i['why'])})"
            for i in d["passed"]
            if i["status"] != "entered"
        ]
        say.append(
            f"  - passed designs entered: {entered or 'none'}; contested: {contested or 'none'}"
        )
        weak = [
            f"{i['design']} {i['status']}" + (f" ({'; '.join(i['why'])})" if i["why"] else "")
            for i in d["weak"]
        ]
        say.append(f"  - the weak deck: {weak or 'no counterpart'}")
    say.append("")
    return say


def lines_of_run(ref: Reference, found: dict) -> list[str]:
    say = ["## The conditions for the bar, on the runs", ""]
    for each in found["clauses"]:
        where = "the deck" if each["place"] == "deck" else f"page {each['place']}"
        runs = ", ".join(f"{n} {v}" for n, v in each["runs"].items())
        scores = (
            "; scores " + "; ".join(f"{n} {v}" for n, v in each["scores"].items())
            if each.get("scores")
            else ""
        )
        say.append(
            f"- condition {each['condition']}, {where}, {each['text']} "
            f"({', '.join(each['designs'])}): {each['status']}"
            + (f": {runs}{scores}" if runs else "")
        )
    say += [
        "",
        "**Condition 3, stability.** Each image with a reading in the reference, in every "
        "run and every deck it stands in:",
        "",
    ]
    for place, cell in found["stability"].items():
        where = "the deck" if place == "deck" else f"page {place}"
        total = len(cell["stable"]) + len(cell["unstable"]) + len(cell["not read"])
        say.append(
            f"- {where}: {len(cell['stable'])} of {total} stable; "
            f"{len(cell['unstable'])} unstable; {len(cell['not read'])} not read in every run"
        )
        if cell["stable"]:
            say.append(f"  - stable: {', '.join(cell['stable'])}")
        say += [f"  - unstable: {line}" for line in cell["unstable"]]
        say += [f"  - not read: {line}" for line in cell["not read"]]
        if cell["left out"]:
            say.append(f"  - left out, no reading in the reference: {', '.join(cell['left out'])}")
    say += [
        "",
        "**The evidence,** the review's order against the maintainer's, counting toward "
        "no acceptance (designs with no reading in the reference, or in the run, left out):",
        "",
    ]
    for page, cell in found["evidence"].items():
        left = ", ".join(cell["left out"]) or "none"
        say.append(f"- page {page} (left out, no reading in the reference: {left}):")
        for name, d in cell["runs"].items():
            missing = (
                f"; no reading in the run: {', '.join(d['no reading in the run'])}"
                if d["no reading in the run"]
                else ""
            )
            say.append(
                f"  - {name}: over {d['designs']} designs, tau-b {d['tau-b']:+.2f}, "
                f"his ordered pairs kept in order {d['kept in order']:.0%}{missing}"
            )
    say += [
        "",
        "**The verdict against the reference on every version with a reading,** counting "
        "toward no acceptance:",
        "",
    ]
    for name, d in found["false"].items():
        say.append(
            f"- {name}: {len(d['false passes'])} false passes, "
            f"{len(d['false fails'])} false fails, {len(d['no reading'])} with no reading"
        )
        say.append(f"  - false passes: {d['false passes']}")
        say.append(f"  - false fails: {d['false fails']}")
    say += ["", "## Each covered rule", ""]
    for rule, d in found["rules"].items():
        say.append(f"### {rule}")
        say.append("")
        for pair in d["pairs"]:
            if pair["status"] != "entered":
                why = "; ".join(pair["why"])
                say.append(f"- pair {pair['base']} → {pair['variant']}: {pair['status']} ({why})")
                continue
            for name, r in pair["runs"].items():
                say.append(
                    f"- pair {pair['base']} → {pair['variant']}, {name}: base {r['base']}, "
                    f"variant {r['variant']}: (a) {said(r['(a)'])}, (b) {said(r['(b)'])}, "
                    f"(c) {said(r['(c)'])}"
                )
        for item in d["passed"]:
            if item["status"] != "entered":
                continue
            below, unread = item["below"], item["no reading"]
            text = "; ".join(below) if below else "professional or above wherever read"
            if unread:
                text += "; no reading in " + ", ".join(f"{n} ×{k}" for n, k in unread.items())
            say.append(f"- passed design {item['design']}: {text}")
        for item in d["weak"]:
            if item["status"] != "entered":
                continue
            say.append(
                f"- weak deck {item['design']}: "
                + (
                    "not below in " + "; ".join(item["not below"])
                    if item["not below"]
                    else "below professional in every run"
                )
            )
        s = d["stability"]
        say.append(
            f"- stability: one grade on {s['one grade']} of {s['places']}; widest spread "
            f"{s['widest spread']} step(s); "
            f"crossing professional: {s['crossing professional'] or 'none'}; "
            f"no reading: {s['no reading'] or 'none'}"
        )
        say.append("")
    say += ["## The covered rules against the four conditions", ""]
    say += ["| Rule | 1 order | 2 pass line | 3 stability | 4 weak deck |", "|---|---|---|---|---|"]
    for rule, d in found["rules"].items():
        say.append(f"| {rule} | " + " | ".join(d["matrix"][c] for c in (1, 2, 3, 4)) + " |")
    say.append("| **For the bar** | " + " | ".join(found["bar"][c] for c in (1, 2, 3, 4)) + " |")
    say += ["", "For the bar, by place:", ""]
    say += ["| Condition | " + " | ".join(ref.places) + " |", "|---|" + "---|" * len(ref.places)]
    for c in (1, 2, 3, 4):
        say.append(f"| {c} | " + " | ".join(found["places"][c][p] for p in ref.places) + " |")
    say.append("")
    return say


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("mode", choices=("control", "run"))
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--blind-key", type=Path, required=True)
    parser.add_argument("--judges", type=Path, nargs=2, required=True, metavar=("KEYS", "REPORTS"))
    parser.add_argument("--runs", type=Path, nargs=2, metavar=("KEYS", "REPORTS"))
    parser.add_argument("--control", type=Path)
    parser.add_argument("--folders", type=Path)
    parser.add_argument("--judge-folders", type=Path)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--json", type=Path, required=True)
    args = parser.parse_args()
    if args.mode == "run" and (args.runs is None or args.control is None):
        parser.error("run needs --runs and --control")

    from jsonschema import Draft202012Validator

    judge_schema = Draft202012Validator(json.loads((HERE / "judge.schema.json").read_text()))
    cap = Capability(args.root)
    ref = Reference(json.loads(args.reference.read_text()))
    problems = cap.bar_problems(ref.bar)
    if problems:
        sys.exit(f"error: the reference's bar does not stand at {args.root}: {'; '.join(problems)}")
    ladder = Ladder(json.loads(args.blind_key.read_text()))
    judges = load_sources(*args.judges, "judge", "judge", ref, cap, judge_schema)
    if [*judges] != ref.data["judges"]:
        sys.exit(
            f"error: the judges' keys are {[*judges]}, the reference names {ref.data['judges']}"
        )
    found_control = control(ref, ladder, judges, cap)
    sources: dict[str, Source] = dict(judges)
    reports = {}
    report: dict[str, Any] = {"control": found_control}
    if args.mode == "run":
        fixed = json.loads(args.control.read_text())["control"]
        if json.dumps(fixed, sort_keys=True) != json.dumps(found_control, sort_keys=True):
            sys.exit(
                "error: the judges' documents give another control than the one fixed before "
                f"the run, {args.control}"
            )
        runs = load_sources(*args.runs, "run", "review", ref, cap, judge_schema)
        if len(runs) != ref.data["runs"]:
            print(f"warning: {len(runs)} runs read, the reference fixes {ref.data['runs']}")
        sources.update(runs)
        reports = {name: args.runs[1] for name in runs}
        report["run"] = run_readings(ref, ladder, runs, fixed, cap)
    folders = {"review": args.folders, "judge": args.judge_folders}
    report["head"] = head(ref, args.root, sources, folders, reports)
    say = [f"# The calibration's {'control' if args.mode == 'control' else 'readings'}", ""]
    say.append(f"- bar: {ref.covers} at least {ref.at_least}; order: {ref.method}")
    say.append("")
    say += lines_of_head(report["head"])
    say += lines_of_control(found_control)
    if args.mode == "run":
        say += lines_of_run(ref, report["run"])
    args.out.write_text("\n".join(say) + "\n")
    args.json.write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str) + "\n")
    print(f"wrote {args.out} and {args.json}")


if __name__ == "__main__":
    main()
