"""The result lines of a fixer run, read by the grammar of the run's contract.

project-management DEC-056 point 3 sets what a fixer's final message ends with: one
line for each artefact the brief names, in one of three forms, a `none` line carrying
one of a fixed list of reasons. The command that reads the lines is not shipped yet,
so the tests of each fixer — the living-docs agent and software-analysis'
analysis-resolver (#1801) — read their lines here, by a grammar built from the
record's own text, never restated:

- **the forms** are the record's fenced `text` block under "The result.", their
  placeholders `<agent>`, `<artefact>`, `<the question>`, `<reason>` and `<the reason
  in words>`. A placeholder this module does not know fails loudly, so a change to
  the record's forms reaches every fixer's tests;
- **the reasons** are the codes the record's "The `none` reasons" names, each in
  backticks and glossed after a comma;
- **which lines count**: each line of the message that, stripped of the whitespace
  around it, starts with `Fixer result (`, a fence's own lines aside. A line behind a
  quote's `>` does not count.

`test_pm_fixer_answer.py` holds project-management's README to the same forms and
reasons.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RECORD = (
    REPO / ".pkit" / "capabilities" / "project-management" / "decisions" / "DEC-056-drift-fixers.md"
)

#: What a result line starts with, once the whitespace around it is stripped.
LEAD = "Fixer result ("

#: An artefact's name: no backtick, and no character that ends or breaks a line.
_NAME = "[^`\x00-\x1f\x7f\x85\u2028\u2029]+"

_PLACEHOLDER = re.compile(r"<[^<>]+>")


@dataclass(frozen=True)
class Result:
    """One line read by the grammar."""

    state: str  # proposed, held or none
    artefact: str
    answer: str | None = None  # a proposed line's answer file
    reason: str | None = None  # a none line's code
    words: str | None = None  # a held line's question, or a none line's reason in words


@cache
def _record() -> str:
    return RECORD.read_text(encoding="utf-8")


@cache
def forms() -> tuple[str, ...]:
    """The record's three line forms, in its order."""
    text = _record().split("- **The result.**", 1)[1]
    block = text.split("```text\n", 1)[1].split("```", 1)[0]
    return tuple(line.strip() for line in block.splitlines() if line.strip())


@cache
def reasons() -> tuple[str, ...]:
    """The record's `none` reasons, in its order."""
    text = _record().split("**The `none` reasons**", 1)[1].split("\n### ", 1)[0]
    named = re.findall(r"`([a-z]+(?:-[a-z]+)*)`, ", text)
    return tuple(code for code in named if code != "none")


def _state(form: str) -> str:
    return form.split("): ", 1)[1].split(" ", 1)[0]


@cache
def _patterns(agent: str) -> tuple[tuple[str, re.Pattern[str]], ...]:
    """Each form as a pattern for `agent`, keyed by the state it gives."""
    reason = "|".join(re.escape(code) for code in reasons())
    patterns = []
    for form in forms():
        parts, seen, at = [], set(), 0
        for found in _PLACEHOLDER.finditer(form):
            parts.append(re.escape(form[at : found.start()]))
            at = found.end()
            name = found.group(0)
            if name == "<agent>":
                parts.append(re.escape(agent))
            elif name == "<artefact>":
                # A proposed line's answer lies in its own artefact's folder.
                parts.append("(?P=artefact)" if name in seen else f"(?P<artefact>{_NAME})")
            elif name == "<reason>":
                parts.append(f"(?P<reason>{reason})")
            elif name in ("<the question>", "<the reason in words>"):
                parts.append(r"(?P<words>\S.*)")
            else:
                raise AssertionError(f"the record's form holds {name}, which this grammar lacks")
            seen.add(name)
        parts.append(re.escape(form[at:]))
        patterns.append((_state(form), re.compile("".join(parts))))
    return tuple(patterns)


def read(line: str, agent: str) -> Result | None:
    """The result `line` gives for `agent`, or None for a line off the grammar."""
    for state, pattern in _patterns(agent):
        matched = pattern.fullmatch(line.strip())
        if matched:
            groups = matched.groupdict()
            answer = None
            if state == "proposed":
                answer = f"{groups['artefact']}/answer.json"
            return Result(
                state=state,
                artefact=groups["artefact"],
                answer=answer,
                reason=groups.get("reason"),
                words=groups.get("words"),
            )
    return None


def counted(message: str) -> list[str]:
    """The lines of `message` the command reads as result lines, stripped."""
    lines = (line.strip() for line in message.splitlines())
    return [line for line in lines if line.startswith(LEAD)]


def fill(form: str, values: dict[str, str]) -> str:
    """`form` with each placeholder `values` names filled; any other left in place."""
    return _PLACEHOLDER.sub(lambda found: values.get(found.group(0), found.group(0)), form)
