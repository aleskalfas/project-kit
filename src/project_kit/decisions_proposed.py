"""Proposed records: the one condition each waits on, and which are due for a person.

A proposed record may name, in its front matter's `waits-on`, the one condition
its acceptance waits on (`.pkit/decisions/README.md`, "Schema" and "Statuses"),
as a mapping of one kind to its value:

- `issue: 795` — an issue of the project's own repository closes; an issue of
  another is written `owner/repo#795`
- `date: 2026-12-01` — the date comes
- `record: ADR-071` — that record is accepted; a capability's decision is
  written `<capability>:DEC-NNN`, as in an anchor's value

**The field's shape** (`read_condition`, `check_waits_on`) is held in the
`decisions` member of validation. A field it cannot read is an error. A field
on a record that is not proposed is a warning, which never fails, since such a
record waits on nothing and accepting a record stays a one-line flip.

**The report** (`report`, for `pkit decisions proposed`) gives each of the
project's own proposed records a standing:

- **due** — its condition has passed: the issue is closed, the date has come,
  the record it waits on is accepted, or superseded since. A record it names
  that no record here holds is due too, since only a person can mend the name.
  A record that names no condition is due once its `date` is more than
  `older_than` days ago. A status only moves forward, so a proposed record has
  been proposed since its date.
- **unread** — what it waits on could not be read: an issue `gh` gave no state
  for, a field of the wrong shape, a front matter or a date that does not parse.
- **waiting** — the rest.

It reads GitHub only for an issue, once for each issue, and everything else
from the working tree, so all but an issue reads offline. An issue is read
through the backbone's one issue reader, `github_issues.read_issue`, from the
project's root. That read is live and pull-only, stores nothing, and gives an
issue it cannot read as unknown, with why, never blocking (COR-043 point 5).
The condition is tied to GitHub, through `gh`, under a label naming it,
provisionally, as ADR-061 point 3 places the backbone's landing of a pull
request, while #1222 raises the question for a core decision. The report's answer moves with the date and the tracker, so it
is a command of its own, never a member of validation (COR-055 point 2). A
synced copy is not listed, since it is settled where it is authored (COR-055
point 1), though a record of the project's may wait on one.
"""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import click

from project_kit import cli_render, document_parts, github_issues
from project_kit.github_issues import IssueReading
from project_kit.validators import Finding, Severity

WAITS_ON_KEY = "waits-on"

# The kinds of condition, in the order the README gives them.
KINDS = ("issue", "date", "record")

# Days after its date that a proposed record naming no condition is due.
DEFAULT_OLDER_THAN = 30

# The standings, in the order the report gives them.
DUE = "due"
UNREAD = "unread"
WAITING = "waiting"
STANDINGS = (DUE, UNREAD, WAITING)

# A date as written, `2026-12-01`; whether it is a real date is asked apart.
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# A record's id, its slug allowed: `ADR-071`, `ADR-071-slug`, `<capability>:DEC-059`.
_RECORD = re.compile(
    r"^(?:(?P<capability>[a-z][a-z0-9-]*[a-z0-9]):)?"
    r"(?P<id>(?P<prefix>COR|PRJ|ADR|DEC)-\d+)(?:-[a-z0-9][a-z0-9-]*)?$"
)

# `waits-on` written as a key of the front matter, quoted or not. It is read from the
# front matter's text when that does not parse, so a field nothing can read still fails.
_KEY_LINE = re.compile(r"""^["']?waits-on["']?[ \t]*:""", re.MULTILINE)

# `status: proposed` in a front matter that does not parse.
_PROPOSED_LINE = re.compile(r"^status:[ \t]*proposed[ \t]*$", re.MULTILINE)

# Where a finding on the field points.
_POINTER = f":/{WAITS_ON_KEY}"

# The field's shape, as a message gives it.
_SHAPE = "`{issue: 795}`, `{date: 2026-12-01}` or `{record: ADR-071}`"


# --- the field's shape ----------------------------------------------------------------


@dataclass(frozen=True)
class Condition:
    """The one condition a proposed record waits on."""

    kind: str  # "issue" | "date" | "record"
    # "795" or "owner/repo#795"; "2026-12-01"; "ADR-071" or "<capability>:DEC-NNN", no slug
    value: str

    def __str__(self) -> str:
        if self.kind == "issue":
            return f"issue {self.value}" if "#" in self.value else f"issue #{self.value}"
        if self.kind == "date":
            return f"the date {self.value}"
        return f"record {self.value}"


def read_condition(value: Any) -> tuple[Condition | None, str]:
    """The condition a `waits-on` value names, with `""`, or `None` with why it names none.

    `value` is the field as `document_parts.parse_front_matter` reads it, a date
    rendered back to its written form.
    """
    if not isinstance(value, Mapping):
        return None, f"is not a mapping of one kind to its value, such as {_SHAPE}"
    fields = cast("Mapping[object, Any]", value)
    unknown = [str(key) for key in fields if key not in KINDS]
    if unknown:
        named = ", ".join(f"`{key}`" for key in unknown)
        return None, (
            f"names {named}, no kind of condition: the kinds are `issue`, `date` and `record`"
        )
    if len(fields) != 1:
        named = "no condition" if not fields else f"{len(fields)} conditions"
        return None, f"names {named}, and a record waits on one, such as {_SHAPE}"
    kind, given = next(iter(fields.items()))
    if kind == "issue":
        return _issue(given)
    if kind == "date":
        return _date(given)
    return _record(given)


def _issue(given: Any) -> tuple[Condition | None, str]:
    """An issue's number, or `owner/repo#N` for an issue of another repository."""
    if isinstance(given, int) and not isinstance(given, bool) and given > 0:
        return Condition("issue", str(given)), ""
    if isinstance(given, str) and github_issues.ELSEWHERE.match(given):
        return Condition("issue", given), ""
    if given is None:
        return None, (
            "names no issue. Write the number alone, `issue: 795`, since `#` opens a comment "
            "in YAML"
        )
    return None, (
        f"`issue: {given}` names no issue: write its number, `issue: 795`, or "
        "`owner/repo#795` for an issue of another repository"
    )


def _date(given: Any) -> tuple[Condition | None, str]:
    """A real date, written `YYYY-MM-DD`."""
    if isinstance(given, str) and _DATE.match(given):
        try:
            dt.date.fromisoformat(given)
        except ValueError:
            pass
        else:
            return Condition("date", given), ""
    return None, f"`date: {given}` is no date: write it `YYYY-MM-DD`, such as `date: 2026-12-01`"


def _record(given: Any) -> tuple[Condition | None, str]:
    """A record's id, a capability's decision with its capability in front."""
    match = _RECORD.match(given) if isinstance(given, str) else None
    if match is not None and (match["capability"] is None) == (match["prefix"] != "DEC"):
        capability = match["capability"]
        key = match["id"] if capability is None else f"{capability}:{match['id']}"
        return Condition("record", key), ""
    return None, (
        f"`record: {given}` names no record: write its id, such as `ADR-071`, and a "
        "capability's decision with its capability, such as `project-management:DEC-059`"
    )


def check_waits_on(rel: str, text: str) -> list[Finding]:
    """One record's `waits-on`, held to its shape, each finding at `<rel>:/waits-on`.

    An error when the field cannot be read: the front matter does not parse, or
    the value names no one condition of a known kind. A warning, which never
    fails, when a record that is not proposed carries the field, since it waits
    on nothing. A record without the field yields nothing.
    """
    raw, _body = document_parts.split_front_matter(text)
    if raw is None or not _KEY_LINE.search(raw):
        return []
    where = rel + _POINTER
    front_matter, _body, problem = document_parts.parse_front_matter(text)
    if problem is not None:
        return [
            Finding(
                where,
                f"`{WAITS_ON_KEY}` cannot be read: the front matter does not parse ({problem}).",
            )
        ]
    if front_matter is None or WAITS_ON_KEY not in front_matter:
        return []
    found: list[Finding] = []
    condition, why = read_condition(front_matter[WAITS_ON_KEY])
    if condition is None:
        found.append(Finding(where, f'`{WAITS_ON_KEY}` {why} (the decisions README, "Schema").'))
    status = front_matter.get("status")
    if status != "proposed":
        found.append(
            Finding(
                where,
                f"`{WAITS_ON_KEY}` sits on a record whose status is `{status}`, and only a "
                f'proposed record waits on anything. Remove it (the decisions README, "Statuses").',
                severity=Severity.WARNING,
            )
        )
    return found


# --- reading an issue -----------------------------------------------------------------


# Reads one issue from the project's root, given the root and the issue's value.
IssueReader = Callable[[Path, str], IssueReading]


def read_issue(target_root: Path, issue: str) -> IssueReading:
    """One issue's state, read by the backbone's issue reader from the project's root.

    `gh` finds the project's own repository from its remote there, and
    `owner/repo#N` names another (`github_issues.read_issue`).
    """
    return github_issues.read_issue(issue, cwd=target_root)


# --- the report -----------------------------------------------------------------------


@dataclass(frozen=True)
class Proposed:
    """One proposed record of the project's own, with its standing and why."""

    path: str  # relative to the root
    record_id: str  # `PRJ-001`, or `<capability>:DEC-NNN` for a capability's decision
    since: str | None  # its `date` as written, or `None` when it cannot be read
    standing: str  # one of `STANDINGS`
    reason: str  # a sentence, saying what it waits on and how that stands


@dataclass(frozen=True)
class ProposedReport:
    """Every proposed record of the project's own, due first, oldest first in each standing."""

    records: tuple[Proposed, ...]
    older_than: int

    def of(self, standing: str) -> tuple[Proposed, ...]:
        return tuple(record for record in self.records if record.standing == standing)


def report(
    target_root: Path,
    *,
    older_than: int = DEFAULT_OLDER_THAN,
    today: dt.date | None = None,
    read: IssueReader | None = None,
) -> ProposedReport:
    """The project's own proposed records, each with its standing (see the module docstring).

    `today` defaults to the date now, and `read` to `read_issue`, asked once for
    each issue a record waits on and never otherwise.
    """
    from project_kit.decisions_validate import discover_decision_records, synced_record_test

    today = today if today is not None else dt.date.today()
    reader: IssueReader = read if read is not None else read_issue
    asked: dict[str, IssueReading] = {}

    def issue_state(issue: str) -> IssueReading:
        if issue not in asked:
            asked[issue] = reader(target_root, issue)
        return asked[issue]

    is_synced = synced_record_test(target_root)
    statuses: dict[str, str] = {}
    own: list[tuple[str, str, str]] = []  # (rel, key, text) of each record of the project's
    for record in discover_decision_records(target_root):
        try:
            text = record.path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        rel = record.path.relative_to(target_root).as_posix()
        capability = record.id_space.partition("capability:")[2]
        if record.record_id is None:
            key = rel
        else:
            key = f"{capability}:{record.record_id}" if capability else record.record_id
        front_matter, _body, _problem = document_parts.parse_front_matter(text)
        status = front_matter.get("status") if front_matter is not None else None
        if isinstance(status, str):
            statuses[key] = status
        if not is_synced(rel):
            own.append((rel, key, text))

    found: list[Proposed] = []
    for rel, key, text in own:
        entry = _proposed(rel, key, text, statuses, today, older_than, issue_state)
        if entry is not None:
            found.append(entry)
    found.sort(key=lambda r: (STANDINGS.index(r.standing), r.since or "9999-99-99", r.path))
    return ProposedReport(tuple(found), older_than)


def _proposed(
    rel: str,
    key: str,
    text: str,
    statuses: Mapping[str, str],
    today: dt.date,
    older_than: int,
    issue_state: Callable[[str], IssueReading],
) -> Proposed | None:
    """One record's entry, or `None` when it is not proposed."""
    front_matter, _body, problem = document_parts.parse_front_matter(text)
    if front_matter is None:
        raw, _rest = document_parts.split_front_matter(text)
        if problem is None or raw is None or not _PROPOSED_LINE.search(raw):
            return None
        return Proposed(rel, key, None, UNREAD, f"its front matter does not parse ({problem}).")
    if front_matter.get("status") != "proposed":
        return None
    written = front_matter.get("date")
    since = written if isinstance(written, str) and _is_date(written) else None
    if WAITS_ON_KEY in front_matter:
        condition, why = read_condition(front_matter[WAITS_ON_KEY])
        if condition is None:
            return Proposed(rel, key, since, UNREAD, f"its `{WAITS_ON_KEY}` {why}.")
        standing, how = _standing(condition, statuses, today, issue_state)
        return Proposed(rel, key, since, standing, f"waits on {condition}, {how}.")
    if since is None:
        return Proposed(
            rel,
            key,
            None,
            UNREAD,
            "names no condition, and its `date` cannot be read, so its age is unknown.",
        )
    age = (today - dt.date.fromisoformat(since)).days
    reason = f"names no condition, and has been proposed since {since}, {age} day(s)"
    if age > older_than:
        return Proposed(
            rel, key, since, DUE, f"{reason}, more than the {older_than} the report allows."
        )
    return Proposed(rel, key, since, WAITING, f"{reason}.")


def _standing(
    condition: Condition,
    statuses: Mapping[str, str],
    today: dt.date,
    issue_state: Callable[[str], IssueReading],
) -> tuple[str, str]:
    """A condition's standing, and how it stands, as a clause."""
    if condition.kind == "issue":
        reading = issue_state(condition.value)
        if reading.state == github_issues.CLOSED:
            return DUE, "which is closed"
        if reading.state == github_issues.OPEN:
            return WAITING, "which is open"
        return UNREAD, f"which could not be read: {reading.reason}"
    if condition.kind == "date":
        ahead = (dt.date.fromisoformat(condition.value) - today).days
        return (DUE, "which has come") if ahead <= 0 else (WAITING, f"{ahead} day(s) ahead")
    status = statuses.get(condition.value)
    if status is None:
        return DUE, "which no record here holds"
    if status == "proposed":
        return WAITING, "which is still proposed"
    return DUE, f"which is {status}"


def _is_date(text: str) -> bool:
    if not _DATE.match(text):
        return False
    try:
        dt.date.fromisoformat(text)
    except ValueError:
        return False
    return True


_TITLES = {
    DUE: "Due for a person to settle",
    UNREAD: "Could not be read",
    WAITING: "Waiting",
}


def print_report(found: ProposedReport) -> None:
    """Render the report: a count, then each standing that holds a record, due first."""
    if not found.records:
        click.echo("  No proposed record of the project's own.")
        return
    counts = ", ".join(f"{len(found.of(standing))} {standing}" for standing in STANDINGS)
    click.echo(
        "  "
        + cli_render.style(
            "strong", f"{len(found.records)} proposed record(s) of the project's own: {counts}."
        )
    )
    for standing in STANDINGS:
        _print_group(_TITLES[standing], found.of(standing))


def _print_group(title: str, records: Iterable[Proposed]) -> None:
    listed = list(records)
    if not listed:
        return
    click.echo("  " + cli_render.style("strong", f"{title} ({len(listed)}):"))
    for record in listed:
        click.echo(f"    {record.record_id}  {record.path}")
        click.echo(f"      → {record.reason}")
