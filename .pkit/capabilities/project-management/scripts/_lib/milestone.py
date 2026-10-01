"""Milestone resolution helper for pm scripts.

`--milestone` arguments in pm scripts accept either the milestone's
NUMBER (e.g. `6`) or its exact TITLE (e.g. `Milestone 1: Self-host
project-kit pm capability cleanly`). This matches `gh issue create
--milestone` and `gh issue edit --milestone` behaviour at the gh CLI
layer.

Per #217: prior to this lib, `create-issue.py` accepted only number
(argparse `type=int`) and `promote-issue.py` accepted only title.
Cross-script inconsistency surfaced repeatedly during the session.
This module exposes a single resolver each script calls; downstream
code receives a normalised `(number, title)` pair regardless of
input form.

The resolver lists OPEN milestones via `gh api` (paginated, robust
to concatenated-array output per `_parse_concatenated_arrays`) and
matches by number or title. If the arg is numeric and matches no
open milestone, the resolver returns None (the script reports the
error and exits). Closed milestones are out of scope — pm operations
attach to open milestones only.

The module also holds the reads that decide whether a Milestone may close,
so `close-milestone` (which closes it) and `close-issue`'s closure cascade
(which says when it became closeable, #414) read a Milestone the same way:
its close-trigger ([project-management:DEC-016-time-bound-containers]) and
its child issues. And it holds the reads a date-triggered close rolls the open
children forward by (#1175): whether the date trigger fired, the Milestone's
`Rollforward target:` line, and the next-numbered open Milestone of its
category.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import sys
from dataclasses import dataclass
from typing import Any

from _lib import containment
from _lib.gh import gh_run
from _lib.structural_type import infer_structural_type

# The close-triggers whose close fires when the last child closes
# (schemas/time-containers.yaml): `content-based`, and `either`, which closes
# on whichever of date or content fires first. A `date-based` Milestone closes
# on its date, however many children are still open.
CONTENT_TRIGGERS = frozenset({"content-based", "either"})

# The DEC-016 `Close trigger: <value>` marker, on the description's first line.
_CLOSE_TRIGGER_LINE = re.compile(r"^Close trigger:\s+(date-based|content-based|either)$")

# The textual milestone-ref create-issue writes into an issue body:
# `Milestone: [#<N>](../milestone/<N>)` (see body_parent_ref.milestone_line).
# The number is back-referenced, so a link whose text and target disagree is
# not a ref.
_MILESTONE_REF = re.compile(
    r"^Milestone:\s+\[#(?P<number>\d+)\]\(\.\./milestone/(?P=number)\)\s*$",
    re.MULTILINE,
)

# The DEC-016 `Rollforward target: <Milestone>` line: where a date-triggered
# close moves the Milestone's open children.
_ROLLFORWARD_TARGET_LINE = re.compile(r"^Rollforward target:\s+(?P<value>.+?)\s*$")

# A Milestone named by number: `#7`, `7`, or the `[#7](../milestone/7)` link an
# issue's first line uses.
_MILESTONE_NUMBER_REF = re.compile(
    r"^(?:\[#(?P<link>\d+)\]\(\.\./milestone/(?P=link)\)|#?(?P<plain>\d+))$"
)

# The fields a milestone-children read needs from the issue corpus.
_CHILDREN_FIELDS = "number,title,state,body,milestone"


@dataclass(frozen=True)
class Milestone:
    """Normalised representation of a GitHub milestone."""

    number: int
    title: str


def list_open_milestones(config: dict[str, Any]) -> list[dict] | None:
    """Fetch every open milestone in the current repo via `gh api`.

    Returns the parsed list of milestone dicts, or None if `gh` is
    missing or the API call fails. Each dict carries at minimum
    `number: int` and `title: str`.
    """
    try:
        proc = gh_run(
            [
                "gh",
                "api",
                "--paginate",
                "repos/{owner}/{repo}/milestones?state=open",
            ],
            config,
            check=False,
        )
    except FileNotFoundError:
        return None
    if proc.returncode != 0:
        return None
    try:
        text = proc.stdout.strip()
        if not text:
            return []
        return _parse_concatenated_arrays(text)
    except (ValueError, KeyError, TypeError):
        return None


def resolve_milestone(arg: str, config: dict[str, Any]) -> Milestone | None:
    """Resolve a `--milestone` argument to a `(number, title)` pair.

    Accepts the milestone number (string of digits, e.g. `"6"`) or its
    exact title (any other string, e.g. `"Milestone 1: ..."`).

    Returns the matched `Milestone` dataclass on success; `None` if no
    open milestone matches the input. Callers should print an error
    and exit when None is returned. Numeric args are matched against
    the milestone's `number` field; non-numeric args against `title`.
    """
    if not arg:
        return None
    milestones = list_open_milestones(config)
    if milestones is None:
        return None
    if arg.lstrip("-").isdigit():
        target_number = int(arg)
        for ms in milestones:
            if isinstance(ms, dict) and ms.get("number") == target_number:
                return Milestone(
                    number=int(ms["number"]),
                    title=str(ms.get("title", "")),
                )
        return None
    for ms in milestones:
        if isinstance(ms, dict) and ms.get("title") == arg:
            return Milestone(
                number=int(ms["number"]),
                title=str(ms["title"]),
            )
    return None


# ---- close-trigger (DEC-016) ----------------------------------------


def parse_close_trigger(description: str) -> str | None:
    """Return the declared close-trigger from the description's first line.

    Matches the DEC-016 `Close trigger: <value>` marker on the first
    non-blank line; returns None when the marker is absent (an inherited
    Milestone) so the caller can fall back to inference.
    """
    for line in description.splitlines():
        s = line.strip()
        if not s:
            continue
        m = _CLOSE_TRIGGER_LINE.match(s)
        return m.group(1) if m else None
    return None


def infer_close_trigger(due_on: object) -> str:
    """Infer the close-trigger for an inherited Milestone with no marker.

    Per time-containers.yaml fallback_inference: a native due date present
    ⇒ date-based; none ⇒ content-based.
    """
    return "date-based" if due_on else "content-based"


def resolve_close_trigger(description: str, due_on: object) -> tuple[str, bool]:
    """Resolve (close_trigger, inferred): declared marker wins, else inferred."""
    declared = parse_close_trigger(description)
    if declared is not None:
        return declared, False
    return infer_close_trigger(due_on), True


# ---- a Milestone and its children ------------------------------------


def fetch_milestone(number: int, config: dict[str, Any]) -> dict | None:
    """GET a single milestone, open or closed, via `gh api` (the `_lib.gh`
    seam). Returns the milestone payload, or None — with the reason on
    stderr — when it cannot be read."""
    try:
        proc = gh_run(
            ["gh", "api", f"repos/{{owner}}/{{repo}}/milestones/{number}"],
            config,
            check=False,
        )
    except FileNotFoundError:
        print("error: `gh` not on PATH.", file=sys.stderr)
        return None
    if proc.returncode != 0:
        print(
            f"error: could not fetch milestone #{number} "
            f"(gh exit {proc.returncode}).\nstderr: {proc.stderr.strip()}",
            file=sys.stderr,
        )
        return None
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        print(f"error: gh returned non-JSON for milestone #{number}.", file=sys.stderr)
        return None
    return data if isinstance(data, dict) else None


def list_milestone_children(
    number: int,
    title: str,
    config: dict[str, Any],
    issue_types: dict,
    classification: dict | None = None,
) -> list[dict] | None:
    """Resolve the milestone's child issues — the union of native + textual.

    A child is any issue that either (a) carries the native GitHub Milestone
    field for this milestone (matched on number or title, the same field
    show-tree reads) or (b) carries the textual `Milestone: [#<n>](../
    milestone/<n>)` body ref create-issue writes. `gh issue list` returns
    issues only (PRs excluded), so no PR filtering is needed.

    The issues are read through the containment seam's corpus fetch, which
    says whether it saw every issue. A fetch that reached the seam's ceiling
    is refused rather than answered from: a child past the ceiling may be
    open, and a list short of it would call the Milestone closeable.

    Returns a list of `{number, title, state, type, milestone}` dicts (state
    lower-cased, type inferred from the title prefix, milestone the native
    Milestone payload or None, sorted by number), or None — with the reason on
    stderr — on a gh failure or a truncated corpus.
    """
    corpus = containment.fetch_issue_corpus(config, fields=_CHILDREN_FIELDS)
    if corpus is None:
        print("error: gh issue list failed.", file=sys.stderr)
        return None
    if not corpus.complete:
        print(
            f"error: cannot list milestone #{number}'s children — the issue "
            f"list reached its {containment.CORPUS_CEILING}-issue ceiling, so a "
            "child may sit past it.",
            file=sys.stderr,
        )
        return None

    children: list[dict] = []
    for row in corpus.rows:
        num = row.get("number")
        if not isinstance(num, int):
            continue
        body = str(row.get("body") or "")
        if not (
            native_milestone_matches(row.get("milestone"), number, title)
            or number in body_milestone_refs(body)
        ):
            continue
        row_title = str(row.get("title", ""))
        native = row.get("milestone")
        children.append(
            {
                "number": num,
                "title": row_title,
                "state": str(row.get("state", "")).lower(),
                "type": infer_structural_type(
                    row_title, issue_types, classification=classification
                ),
                "milestone": native if isinstance(native, dict) else None,
            }
        )
    children.sort(key=lambda c: c["number"])
    return children


def issue_milestones(issue: dict) -> list[int]:
    """The milestones an issue counts as a child of, sorted.

    The same two substrates :func:`list_milestone_children` reads: the
    issue's native Milestone field, and each `Milestone: [#<n>](../
    milestone/<n>)` ref its body carries. The two normally agree
    (`edit-issue` keeps them in step); where they do not, both are named.
    """
    numbers = set(body_milestone_refs(str(issue.get("body") or "")))
    native = issue.get("milestone")
    if isinstance(native, dict) and isinstance(native.get("number"), int):
        numbers.add(native["number"])
    return sorted(numbers)


def body_milestone_refs(body: str) -> list[int]:
    """The milestone numbers an issue body links as `Milestone: [#<n>](../
    milestone/<n>)` lines."""
    return [int(m.group("number")) for m in _MILESTONE_REF.finditer(body)]


def native_milestone_matches(milestone: object, number: int, title: str) -> bool:
    """True when an issue's native milestone field names this milestone.

    Matched on number OR title — gh's `--json milestone` payload may carry
    either depending on the field set; either identifying this milestone
    counts.
    """
    if not isinstance(milestone, dict):
        return False
    if milestone.get("number") == number:
        return True
    return bool(title) and milestone.get("title") == title


# ---- rollforward (DEC-016) -------------------------------------------


def date_trigger_fired(close_trigger: str, due_on: object, today: dt.date) -> bool:
    """Whether closing the Milestone today is a date-triggered close — the close
    that rolls its open children forward (time-containers.yaml).

    A `date-based` Milestone's close always is: the date is its trigger, and an
    early close is the manual form of it. An `either` Milestone's is from its due
    date on; before it, only its content closes it, and one without a due date
    has no date to fire. A `content-based` Milestone's never is.
    """
    if close_trigger == "date-based":
        return True
    if close_trigger != "either":
        return False
    due = due_date(due_on)
    return due is not None and today >= due


def due_date(due_on: object) -> dt.date | None:
    """The calendar date of a Milestone's native `due_on` (`2026-07-01T07:00:00Z`),
    or None when it has none or it does not read as one."""
    if not isinstance(due_on, str):
        return None
    try:
        return dt.date.fromisoformat(due_on.strip()[:10])
    except ValueError:
        return None


def parse_rollforward_target(description: str) -> str | None:
    """The Milestone a `Rollforward target:` line names, as a
    :func:`resolve_milestone` argument; None when the description has no such
    line.

    DEC-016 puts the line second, under the `Close trigger:` marker; it is read
    wherever it stands. A number — `#7`, `7`, or the `[#7](../milestone/7)` link
    an issue's first line uses — comes back as the number; anything else as the
    title it is matched on.
    """
    for line in description.splitlines():
        declared = _ROLLFORWARD_TARGET_LINE.match(line.strip())
        if declared is None:
            continue
        value = declared.group("value")
        ref = _MILESTONE_NUMBER_REF.match(value)
        if ref is None:
            return value
        return ref.group("link") or ref.group("plain")
    return None


def next_numbered_milestones(
    title: str, open_milestones: list[dict], categories: object
) -> list[Milestone]:
    """The open Milestones a date-triggered close of `title` may roll forward to
    when the Milestone names no target: the next-numbered of its category.

    Numbers count per category (DEC-016), so the category is the one in the
    project's `milestone_categories:` whose `title_format` the closing title
    matches, and the candidates are its open Milestones carrying the lowest
    number above the closing one's. One candidate is the target. None — the
    title matches no declared category, or no later Milestone of its category is
    open — or more than one — two open Milestones share the next number, or the
    title matches two categories that each offer one — leave the choice to the
    operator.
    """
    found: dict[int, Milestone] = {}
    for title_format in _numbered_title_formats(categories):
        try:
            regex = title_format_regex(title_format)
        except re.error:  # a malformed format, e.g. `{name}` twice
            continue
        own = regex.match(title)
        if own is None:
            continue
        own_number = int(own.group("n"))
        later: list[tuple[int, Milestone]] = []
        for ms in open_milestones:
            if not isinstance(ms, dict) or not isinstance(ms.get("number"), int):
                continue
            ms_title = str(ms.get("title", ""))
            match = regex.match(ms_title)
            if match is not None and int(match.group("n")) > own_number:
                later.append((int(match.group("n")), Milestone(ms["number"], ms_title)))
        if later:
            lowest = min(n for n, _ in later)
            found.update((ms.number, ms) for n, ms in later if n == lowest)
    return sorted(found.values(), key=lambda ms: ms.number)


def title_format_regex(title_format: str) -> re.Pattern[str]:
    """A category's `title_format` as a regex with named `n` and `name` groups.

    Input: "Milestone {n}: {name}"
    Output: regex compiled from "^Milestone (?P<n>\\d+): (?P<name>.+)$"
    """
    # re.escape() escapes literal braces too — un-escape them so we can
    # substitute placeholders.
    escaped = re.escape(title_format)
    escaped = escaped.replace(r"\{n\}", r"(?P<n>\d+)")
    escaped = escaped.replace(r"\{name\}", r"(?P<name>.+)")
    return re.compile(f"^{escaped}$")


def _numbered_title_formats(categories: object) -> list[str]:
    """The declared categories' title formats that number their Milestones."""
    if not isinstance(categories, dict):
        return []
    formats: list[str] = []
    for entry in categories.values():
        if not isinstance(entry, dict):
            continue
        title_format = entry.get("title_format")
        if isinstance(title_format, str) and title_format.count("{n}") == 1:
            formats.append(title_format)
    return formats


def _parse_concatenated_arrays(text: str) -> list:
    """gh --paginate may emit concatenated JSON arrays; merge them.

    Equivalent to promote-issue.py's `_parse_concatenated_json_arrays`
    — extracted here so create-issue.py can share the parser without
    a cross-script import. Future cleanup: promote-issue should
    re-export from this module instead of carrying its own copy.
    """
    decoder = json.JSONDecoder()
    out: list = []
    idx = 0
    while idx < len(text):
        while idx < len(text) and text[idx].isspace():
            idx += 1
        if idx >= len(text):
            break
        try:
            obj, end = decoder.raw_decode(text, idx)
        except ValueError:
            break
        if isinstance(obj, list):
            out.extend(obj)
        idx = end
    return out
