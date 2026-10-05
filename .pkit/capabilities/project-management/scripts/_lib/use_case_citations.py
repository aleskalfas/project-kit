"""The use-case point, and the use cases an issue body cites (DEC-054).

`pkit::work-tracking:use-cases` is the data point this capability defines as
the provider of the `pkit::work-tracking` role (COR-052, COR-053): the use cases
settled on the default branch, each `{id, title, status, path?}` (its companion
schema, `schemas/use-cases.schema.json`). Whatever keeps a project's use cases
fills it — a capability's contribution, or the project's own filler file. This
capability holds none, and knows no keeper: it reads the point and nothing
else.

Four parts, so the validators that call them stay pure:

- **The rule as the body-format schema carries it** (`rule_of`): its severity,
  the rule's token there and never a constant here, and the issue types whose
  bodies carry a `## Use cases` section. A body of any other type is not read:
  a `## Use cases` heading there is ordinary content.
- **What a body cites** (`cited`): the ids in its `## Use cases` section that
  match the point's id pattern, which is read from the companion schema, so the
  matcher and the point never disagree. An id anywhere else in the body is not
  a citation.
- **Reading the point** (`read_point`): through the backbone's read command,
  `pkit connections resolve <point> --json`. Which of four states the reading
  is in is decided on the document's `outcome` and its fillers' `state`, never
  on `why`, which is only shown to people:
  - `Off` — `undefined` or `unfilled`: nothing defines or fills the point, and
    nothing is said about use cases;
  - `NotChecked` — any other unresolved `outcome`, one this reading does not
    know, a document of a version it does not know, or no document at all:
    there is no set to judge against, and it is never read as `Off`;
  - `Held` with `missing` — `resolved` with an inert filler: partly checked;
  - `Held` — `resolved` with no inert filler: the whole set, empty or not.
- **The rule** (`findings`): the point is read only for a body that cites. A
  cited id the whole set does not hold is reported, naming what the set was
  read against. It checks existence only. A withdrawn use case passes, since
  its id is never reused. What could not be checked is one notice about the
  check, at the same severity and under its own label: the ids a partly
  checked set lacks are named as not checked, and an unread point says why.
  Nothing here refuses or changes a verb's exit.
"""

from __future__ import annotations

import functools
import json
import re
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from _lib import provenance

POINT = "pkit::work-tracking:use-cases"

#: The companion schema the citation matcher is derived from.
SCHEMA = Path(__file__).resolve().parents[2] / "schemas" / "use-cases.schema.json"

#: The rule's id in `body-format.yaml` — the label a cited use case the point
#: does not hold is reported under — and the label of the notice that citations
#: were not checked, which is about the check and not against the body.
LABEL = "body.use-case-citation"
UNCHECKED = "body.use-cases-unchecked"

#: The section a body cites use cases in: its heading as `body-format.yaml`
#: lists it for the types that carry it, and its title as a body is read.
HEADING = "## Use cases"
SECTION = "use cases"

#: The backbone's read command, how long it may take, and the version of its
#: document this reading understands — another is not read. A document without
#: the key comes from a backbone that predates it: version 1.
ARGV = ("pkit", "connections", "resolve", POINT, "--json")
TIMEOUT = 120
DOCUMENT_VERSION = 1

#: The outcomes that turn the rule off, the one that gives a set, and those that
#: leave nothing to check against (DEC-054 point 3) — beside which an outcome this
#: reading does not know leaves nothing to check against too.
OFF = frozenset({"undefined", "unfilled"})
RESOLVED = "resolved"
UNREAD = frozenset(
    {
        "no-answer",
        "inert-fail",
        "collision",
        "selection-needed",
        "selection-unmatched",
        "definer-defect",
    }
)

#: A filler's state, its source, and the state it reads the default branch as.
INERT = "inert"
TAKEN = "taken"
PROJECT_FILLER = "project filler"
SETTLED = "settled"

#: A severity as a schema writes it, `[validation-severity:<id>]`.
_SEVERITY = re.compile(r"^\[validation-severity:(?P<id>[a-z-]+)\]$")

#: A line opening a level-1 or level-2 heading, and its title; and a code fence,
#: inside which no line is a heading.
_HEADING = re.compile(r"^#{1,2}[ \t]+(?P<title>.*?)(?:[ \t]+#+)?[ \t]*$")
_FENCE = re.compile(r"^(?:`{3,}|~{3,})")

Runner = Callable[..., subprocess.CompletedProcess[str]]

#: A finding as the validators take one: `(severity, label, detail)`.
Finding = tuple[str, str, str]


# --- the rule as the schema carries it -------------------------------------------------


@dataclass(frozen=True)
class Rule:
    """The rule as `body-format.yaml` carries it: the severity its findings are
    reported at, and the issue types whose bodies carry the section."""

    severity: str
    types: frozenset[str]


def rule_of(body_format: Mapping[str, Any]) -> Rule | None:
    """The rule in `body_format`: its entry among the universal body rules, by its
    id, and the types that list the section. None when the schema carries no such
    rule, or gives it no severity: there is then no rule to apply."""
    entry = next(
        (
            rule
            for rule in body_format.get("universal_body_rules") or []
            if isinstance(rule, Mapping) and rule.get("id") == LABEL
        ),
        None,
    )
    token = _SEVERITY.match(str(entry.get("severity") or "")) if entry is not None else None
    if token is None:
        return None
    bodies = body_format.get("bodies") or {}
    types = frozenset(
        str(issue_type)
        for issue_type, shape in bodies.items()
        if isinstance(shape, Mapping)
        and HEADING in (shape.get("optional_section_recommendations") or [])
    )
    return Rule(token["id"], types)


# --- the states --------------------------------------------------------------------


@dataclass(frozen=True)
class Off:
    """Nothing defines the point, or nothing fills it: the rule says nothing."""


@dataclass(frozen=True)
class NotChecked:
    """The point could not be read: there is no set to judge against, and why."""

    why: str


@dataclass(frozen=True)
class Held:
    """The use cases the point holds, withdrawn ones included.

    `source` says what they were read against, for a finding: the default
    branch at a commit, the project's filler file, or the filler that answered.
    `fetch` is whether the answer was read from the default branch, so a fetch
    may bring a use case that landed since. `missing` names each filler that
    was meant to answer and did not, with why: non-empty, the set may be
    incomplete — partly checked."""

    ids: frozenset[str]
    source: str
    fetch: bool = False
    missing: tuple[str, ...] = ()


Reading = Off | NotChecked | Held

#: What reads the point for a validator: `read_point`, or a test's stand-in.
Reader = Callable[[], Reading]


# --- what a body cites ---------------------------------------------------------------


@functools.cache
def citation() -> re.Pattern[str]:
    """A citation in running text, derived from the point's id pattern: the pattern
    without its anchors, standing alone as a word."""
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    pattern = str(schema["$defs"]["use-case"]["properties"]["id"]["pattern"])
    core = pattern.removeprefix("^").removesuffix("$")
    return re.compile(rf"(?<![\w-])(?:{core})(?!\w)")


def section(body: str) -> str | None:
    """The text of the body's `## Use cases` section — every such section, joined —
    or None when the body has none. A section runs to the next level-1 or level-2
    heading; the provenance footer is never part of it."""
    found: list[str] | None = None
    inside = fenced = False
    for line in provenance.strip_footer(body).splitlines():
        stripped = line.strip()
        if _FENCE.match(stripped):
            fenced = not fenced
        heading = None if fenced else _HEADING.match(stripped)
        if heading is not None:
            inside = heading["title"].lower() == SECTION
            if inside and found is None:
                found = []
        elif inside and found is not None:
            found.append(line)
    return None if found is None else "\n".join(found)


def cited(body: str) -> list[str]:
    """The use cases `body` cites in its `## Use cases` section, each once, in the
    order first cited."""
    text = section(body)
    if text is None:
        return []
    return list(dict.fromkeys(citation().findall(text)))


# --- reading the point ---------------------------------------------------------------


def read_point(run: Runner = subprocess.run) -> Reading:
    """The point through `pkit connections resolve --json`. The command exits 1 on
    an unresolved point and still prints its document, so the document decides,
    never the exit code. No document at all — `pkit` absent, a backbone without
    the command, a crash, no answer in time — is NotChecked, never Off."""
    argv = list(ARGV)
    try:
        proc = run(argv, capture_output=True, text=True, check=False, timeout=TIMEOUT)
    except FileNotFoundError:
        return NotChecked("`pkit` is not on PATH")
    except subprocess.TimeoutExpired:
        return NotChecked(f"`{' '.join(argv)}` did not answer within {TIMEOUT}s")
    try:
        document = json.loads(proc.stdout or "")
    except ValueError:
        document = None
    if not isinstance(document, Mapping):
        detail = (proc.stderr or "").strip().splitlines()
        return NotChecked(
            f"`{' '.join(argv)}` exited {proc.returncode} without its document"
            + (f": {detail[-1]}" if detail else "")
        )
    return reading_of(document)


def reading_of(document: Mapping[str, Any]) -> Reading:
    """The state a `pkit connections resolve --json` document puts the point in
    (DEC-054 point 3), from its `outcome` and its fillers' `state` alone. A
    document of a version this reading does not know, or one that does not say
    how the point resolved — a backbone that predates `outcome` — is NotChecked."""
    version = document.get("schema_version", DOCUMENT_VERSION)
    if version != DOCUMENT_VERSION:
        return NotChecked(
            f"the backbone answered a document at version {version!r}; this reading "
            f"understands {DOCUMENT_VERSION}"
        )
    outcome = document.get("outcome")
    fillers = [f for f in document.get("fillers") or [] if isinstance(f, Mapping)]
    inert = [f for f in fillers if f.get("state") == INERT]
    if outcome in OFF:
        return Off()
    if outcome != RESOLVED:
        return NotChecked(_unresolved(outcome, document, inert))
    value = document.get("value")
    if not isinstance(value, list):
        return NotChecked("the point resolved to a value that is no list of use cases")
    ids = frozenset(
        str(entry["id"]) for entry in value if isinstance(entry, Mapping) and "id" in entry
    )
    taken = next((f for f in fillers if f.get("state") == TAKEN), None)
    source, fetch = _source(taken, str(document.get("origin") or ""))
    return Held(ids, source, fetch, tuple(_filler(f) for f in inert))


def _unresolved(
    outcome: Any, document: Mapping[str, Any], inert: Sequence[Mapping[str, Any]]
) -> str:
    """Why an unresolved point gave no set: its sentence for people and each inert
    filler with its reason — or, for an outcome this reading does not know, that."""
    if not isinstance(outcome, str):
        return (
            "the backbone's document does not say how the point resolved (it predates "
            "`outcome`; upgrade the backbone)"
        )
    why = str(document.get("why") or "").strip() or outcome
    if outcome not in UNREAD:
        return f"it ended as {outcome!r}, which this reading does not know ({why})"
    return "; ".join([why, *(_filler(f) for f in inert)])


def _filler(filler: Mapping[str, Any]) -> str:
    """A filler as a notice names it: who, and why it gave no answer."""
    reason = str(filler.get("reason") or "").strip()
    name = str(filler.get("name") or "a filler")
    return f"{name} ({reason})" if reason else name


def _source(taken: Mapping[str, Any] | None, origin: str) -> tuple[str, bool]:
    """What the set was read against, for a finding, and whether a fetch may help:
    the default branch at the commit a settled-state filler read; the project's
    filler file; else whoever answered."""
    if taken is None:
        return (f"that {origin} gave" if origin else "the point holds"), False
    if taken.get("source") == PROJECT_FILLER:
        return f"in the project's filler file {taken.get('name')}", False
    for read in taken.get("reads") or []:
        if not isinstance(read, Mapping) or read.get("state") != SETTLED:
            continue
        ref, commit = read.get("ref"), read.get("commit")
        if isinstance(commit, str) and commit:
            return f"settled on the default branch (read at {ref} {commit[:12]})", True
        if isinstance(ref, str) and ref:
            return f"settled on the default branch ({ref}, which has no commit yet)", False
    return f"that {taken.get('name') or origin} gave", False


# --- the rule ----------------------------------------------------------------------


def findings(
    body: str,
    issue_type: str | None,
    body_format: Mapping[str, Any],
    read: Reader | None,
) -> list[Finding]:
    """What the rule reports on `body`, the body of an issue of `issue_type`.

    Nothing — and the point is not read, so no filler starts — where no reader
    is given, the schema carries no such rule, the type's bodies carry no
    `## Use cases` section, or the body cites no use case."""
    rule = rule_of(body_format)
    if read is None or rule is None or issue_type not in rule.types:
        return []
    ids = cited(body)
    if not ids:
        return []
    return judge(ids, read(), rule.severity)


def judge(ids: Sequence[str], reading: Reading, severity: str) -> list[Finding]:
    """What the rule says of the cited `ids`, read against `reading` (DEC-054 points
    3 and 4): nothing while the point is off; one notice when it could not be
    read, or for the ids a partly checked set lacks; one finding for the ids the
    whole set does not hold."""
    if isinstance(reading, Off) or not ids:
        return []
    if isinstance(reading, NotChecked):
        detail = (
            f"use-case citations not checked ({_enumerate(ids)}): the use cases could "
            f"not be read — {reading.why}. None is reported as unknown on that ground."
        )
        return [(severity, UNCHECKED, detail)]
    lacked = [uc for uc in ids if uc not in reading.ids]
    if not lacked:
        return []
    if reading.missing:
        detail = (
            f"{_enumerate(lacked)} not checked: the use-case point answered without "
            f"{'; '.join(reading.missing)}, so the set it holds may be incomplete."
        )
        return [(severity, UNCHECKED, detail)]
    hint = (
        " If the use case has landed since, fetch the default branch and validate again."
        if reading.fetch
        else ""
    )
    detail = (
        f"cites {_enumerate(lacked)}, not among the use cases {reading.source}. The check "
        f"is of existence only.{hint}"
    )
    return [(severity, LABEL, detail)]


def _enumerate(ids: Sequence[str]) -> str:
    if len(ids) == 1:
        return ids[0]
    return f"{', '.join(ids[:-1])} and {ids[-1]}"
