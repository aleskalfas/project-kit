"""Friction debt, and one artefact's friction: `pkit friction debt` and `pkit friction explain`.

Two reading commands of the anchors-and-friction functionality (COR-050
points 9 and 13). Both are views of the whole-repository check, never a
second computation of it (ADR-057 point 2); both read HEAD and its history,
never the working tree, as the check does; neither writes anything.

- **`debt`** lists the check's *stale* and *deferred* findings — the debt
  derived from git, never kept in a ledger (point 9) — oldest first by the
  author date of their origin: for stale debt the oldest change to the
  anchor since its revalidation point that no commit put back (or the move
  of the artefact), for deferred debt the deferral point. Each entry carries its kind, the
  artefact, the anchor, the origin — commit, author, date, change — and, for
  a deferral, its reason. The entries are exactly those `pkit friction check
  --all` reports (`run_repository_check`); ties keep the check's order,
  upstream first. Artefacts the check did not judge are named apart, each
  kind by itself: those whose points lie beyond a shallow clone, whose debt
  cannot be told, and those with an anchor that cannot be resolved, whose
  debt is told only for their other anchors. An artefact under an excluded
  path is never judged stale or deferred (COR-050 point 7), so it is not
  listed. After the debt, the check's unanchored measure (point 8): the
  artefacts with no anchors and no reason, the only ones counted, and apart
  from them those whose block gives the reason a person accepted them with
  none (`unanchored-because`, point 1), each with its reason.
- **`explain`** judges one artefact through `run_artefact_check` — the
  check's own judgment of it, with the commits behind each finding — and
  shows its anchors, its revalidation and deferral points, what changed since
  each, and for each finding what clears it: the writer command that gives
  the answer (`pkit friction revalidate … --outcome …`, `pkit friction defer
  … --anchor … --reason …`), or the edit it needs where no writer answers
  it. The artefact is named as the writers name one (`friction_write.
  find_artefact`): its location — `path`, or `path#id` for a collection
  entry — or an id; here it is looked up at HEAD. An artefact under an
  excluded path is `excluded`, with the `friction.exclude` entry that leaves
  it out, and shows only what the check reports of its declarations. The
  reason its block gives for having no anchors (`unanchored-because`, point
  1) is shown with its state. Its
  document also carries what a capability's reader would otherwise compute
  again (ADR-057 point 2): each path anchor's files at the revalidation point
  and at HEAD, matched as the check decides a dead anchor, `friction.exclude`
  applied, and the files it leaves out; each commit's paths behind its
  finding, what the check read as the change (`fr.CommitBehind`); where a
  dead path anchor's files went; and the artefact's body as discovery reads
  it — for a collection entry, the section headed by its id.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import click

from project_kit import cli_render
from project_kit import friction_repository as fr
from project_kit.friction_check import (
    SHORT,
    CommitTree,
    HeadState,
    anchors_of,
    counted,
    deferral_reason,
)
from project_kit.friction_discovery import (
    Anchor,
    Artefact,
    Discovery,
    ResolverCommand,
    SettingsPath,
    discover_artefacts,
    held_message,
)
from project_kit.friction_write import command_line

_Kind = fr.RepositoryFindingKind

#: The findings that are debt (COR-050 point 9), in the order the summary names them.
DEBT_KINDS: tuple[fr.RepositoryFindingKind, ...] = (_Kind.STALE, _Kind.DEFERRED)

#: What a person supplies in an answer: shown in the command, never guessed.
BECAUSE = "<why the content still holds>"
REASON = "<why it can wait>"

#: An artefact the check passes over — no anchors, no deferrals — has this state here.
UNANCHORED = "unanchored"

#: An artefact under a `friction.exclude` path, never judged stale or deferred (COR-050
#: point 7), has this state here, whatever it declares.
EXCLUDED = "excluded"


class FrictionReportError(click.ClickException):
    """A reading command could not answer: the artefact is not named, or not at HEAD."""


def _anchor_json(anchor: Anchor | None) -> dict[str, str] | None:
    return None if anchor is None else {"kind": anchor.kind, "value": anchor.value}


def _setting_json(setting: SettingsPath | None) -> dict[str, str] | None:
    """A setting as written — its value, its file and the JSON Pointer to it — or `None`."""
    if setting is None:
        return None
    return {"value": setting.value, "file": setting.file, "pointer": setting.pointer}


def _setting_cell(setting: SettingsPath) -> str:
    """A `friction.exclude` entry as a person finds it: its value, then where it is written."""
    return f"friction.exclude {setting.value!r} ({setting.file}, {setting.pointer})"


def _label(anchor: Anchor) -> str:
    """An anchor as the writers take it on the command line: `kind:value`."""
    return f"{anchor.kind}:{anchor.value}"


def _cell(anchor: Anchor | None) -> str:
    return "—" if anchor is None else f"{anchor.kind} {anchor.value}"


def _age(now: datetime, then: datetime) -> str:
    days = (now.astimezone(UTC) - then.astimezone(UTC)).days
    return "today" if days <= 0 else f"{counted(days, 'day', 'days')} ago"


def _commit_row(commit: fr.Commit, author_width: int) -> str:
    return f"{commit.short}  {commit.day}  {commit.author:{author_width}}  {commit.subject}"


def _header_lines(head: HeadState, shallow: bool) -> list[str]:
    lines = [f"  Head: {head.commit[:SHORT]}"]
    if head.uncommitted:
        lines.append(
            f"  ⚠ {counted(head.uncommitted, 'uncommitted path', 'uncommitted paths')} not "
            f"read: this reads HEAD and its history — commit first to include them"
        )
    if shallow:
        lines.append(
            "  History: shallow clone — a point beyond it is reported as unreachable, never guessed"
        )
    else:
        lines.append("  History: full")
    return lines


# --- the debt listing ----------------------------------------------------------------


@dataclass(frozen=True)
class DebtEntry:
    """One debt: a stale or deferred finding of the whole-repository check, and its origin."""

    finding: fr.RepositoryFinding
    origin: fr.Commit
    reason: str | None  # a deferral's reason as HEAD writes it; `None` for stale debt

    def as_json(self) -> dict[str, Any]:
        return {
            "kind": self.finding.kind.value,
            "artefact": self.finding.artefact,
            "location": self.finding.location,
            "anchor": _anchor_json(self.finding.anchor),
            "origin": self.origin.as_json(),
            "reason": self.reason,
            "message": self.finding.message,
        }


@dataclass(frozen=True)
class DebtListing:
    """The debt of every artefact at HEAD, oldest first, and the unanchored measure. It
    never fails.

    `unanchored` and `accepted_unanchored` are the check's measure (COR-050
    point 8): the artefacts with no anchors and no reason, the only ones
    counted, and apart from them those whose block gives the reason a person
    accepted them with none (point 1).
    """

    dormant: bool
    head: HeadState | None  # `None` only while dormant
    shallow: bool | None  # `None` only while dormant
    entries: tuple[DebtEntry, ...]  # oldest first
    unreachable: tuple[fr.ArtefactReport, ...]  # not judged: a point beyond a shallow clone
    unresolved: tuple[fr.ArtefactReport, ...] = ()  # not judged: an anchor cannot be resolved
    unanchored: tuple[str, ...] = ()  # locations, in walk order
    accepted_unanchored: tuple[fr.AcceptedUnanchored, ...] = ()  # in walk order

    def count(self, kind: fr.RepositoryFindingKind) -> int:
        return sum(1 for e in self.entries if e.finding.kind is kind)


def run_debt(
    target_root: Path, *, registry: Mapping[str, ResolverCommand] | None = None
) -> DebtListing:
    """The stale and deferred findings of the whole-repository check, oldest first.

    Sorted by the author date of each origin; the sort is stable, so ties keep
    the check's order. Raises `FrictionCheckError` when the check cannot run.
    """
    check = fr.run_repository_check(target_root, registry=registry)
    if check.dormant or check.head is None:
        return DebtListing(True, None, None, (), ())
    debt = [
        (finding, finding.origin)
        for finding in check.findings
        if finding.kind in DEBT_KINDS and finding.origin is not None
    ]
    reasons = _deferral_reasons(target_root, check.head.commit, [f for f, _ in debt])
    entries = [
        DebtEntry(
            finding,
            origin,
            reasons.get((finding.location, finding.anchor))
            if finding.kind is _Kind.DEFERRED
            else None,
        )
        for finding, origin in debt
    ]
    entries.sort(key=lambda entry: entry.origin.date)

    def in_state(state: fr.ArtefactState) -> tuple[fr.ArtefactReport, ...]:
        return tuple(r for r in check.artefact_reports if r.state is state)

    return DebtListing(
        False,
        check.head,
        bool(check.shallow),
        tuple(entries),
        in_state(fr.ArtefactState.UNREACHABLE),
        in_state(fr.ArtefactState.UNRESOLVED),
        check.unanchored,
        check.accepted_unanchored,
    )


def _deferral_reasons(
    target_root: Path, head: str, findings: Sequence[fr.RepositoryFinding]
) -> dict[tuple[str | None, Anchor | None], str]:
    """The reason each deferred finding's entry carries at HEAD, by location and anchor."""
    deferred = [f for f in findings if f.kind is _Kind.DEFERRED and f.anchor is not None]
    if not deferred:
        return {}
    discovery = discover_artefacts(target_root, tree=CommitTree(target_root, head))
    by_location = {artefact.location: artefact for artefact in discovery.artefacts}
    reasons: dict[tuple[str | None, Anchor | None], str] = {}
    for finding in deferred:
        artefact = by_location.get(finding.location or "")
        if artefact is not None and finding.anchor is not None:
            reasons[(finding.location, finding.anchor)] = deferral_reason(artefact, finding.anchor)
    return reasons


#: The version of the document `render_debt_json` returns. A change a reader could
#: break against — a key removed, renamed or given another meaning — raises it; a key
#: added does not. A document without it comes from a backbone that predates it:
#: version 1.
DEBT_SCHEMA_VERSION = 1


def render_debt_json(listing: DebtListing) -> str:
    """The stable machine-readable listing: keys sorted, no ages."""
    document = {
        "schema_version": DEBT_SCHEMA_VERSION,
        "report": "debt",
        "dormant": listing.dormant,
        "head": (
            None
            if listing.head is None
            else {"commit": listing.head.commit, "uncommitted_paths": listing.head.uncommitted}
        ),
        "history": None if listing.shallow is None else {"shallow": listing.shallow},
        "counts": {
            **{kind.value: listing.count(kind) for kind in DEBT_KINDS},
            "unreachable": len(listing.unreachable),
            "unresolved": len(listing.unresolved),
            "unanchored": len(listing.unanchored),
        },
        "debt": [entry.as_json() for entry in listing.entries],
        "unreachable": [
            {"artefact": r.artefact, "location": r.location} for r in listing.unreachable
        ],
        "unresolved": [
            {"artefact": r.artefact, "location": r.location} for r in listing.unresolved
        ],
        "unanchored": list(listing.unanchored),
        "accepted_unanchored": [entry.as_json() for entry in listing.accepted_unanchored],
    }
    return json.dumps(document, indent=2, sort_keys=True) + "\n"


_DEBT_LEGEND: dict[fr.RepositoryFindingKind, str] = {
    _Kind.STALE: (
        "an anchor differs from what it stood on at the revalidation point, or the artefact "
        "moved, with no answer — since the oldest change not put back"
    ),
    _Kind.DEFERRED: (
        "friction deliberately postponed — since the commit that introduced the deferral"
    ),
}


def render_debt_human(listing: DebtListing, *, now: datetime | None = None) -> str:
    """The read view: header, the debt oldest first with its age, what was not judged."""
    now = datetime.now(UTC) if now is None else now
    title = cli_render.style("title", "Friction debt")
    if listing.dormant or listing.head is None:
        return f"{title} — dormant\n\n  no places declared; dormant.\n"
    summary = ", ".join(
        f"{listing.count(kind)} {kind.value}" for kind in DEBT_KINDS if listing.count(kind)
    )
    summary = summary or "nothing stale or deferred"
    if listing.unanchored:
        summary += f"; {len(listing.unanchored)} unanchored"
    lines = [
        f"{title} — {summary}"
        + cli_render.style("muted", "   (the whole report: pkit friction check --all)"),
        "",
        *_header_lines(listing.head, bool(listing.shallow)),
        "",
        cli_render.style("heading", "DEBT")
        + cli_render.style("muted", " — oldest first, by the author date of its origin"),
    ]
    if not listing.entries:
        lines.append("  nothing stale or deferred")
    rows = [
        (
            entry.origin.day,
            entry.finding.kind.value,
            entry.finding.location or "",
            _cell(entry.finding.anchor),
            entry.origin.short,
            entry.origin.author,
            f'"{entry.origin.subject}"',
            _age(now, entry.origin.date) + (f" — {entry.reason}" if entry.reason else ""),
        )
        for entry in listing.entries
    ]
    widths = [max((len(row[i]) for row in rows), default=0) for i in range(7)]
    for row in rows:
        cells = "  ".join(f"{cell:{widths[i]}}" for i, cell in enumerate(row[:7]))
        lines.append(f"  {cells}  {row[7]}")
    if listing.unreachable:
        lines.extend(
            [
                "",
                cli_render.style("heading", "NOT JUDGED")
                + cli_render.style(
                    "muted", " — a point beyond this shallow clone: git fetch --unshallow"
                ),
                *(f"  {report.location}" for report in listing.unreachable),
            ]
        )
    if listing.unresolved:
        lines.extend(
            [
                "",
                cli_render.style("heading", "NOT JUDGED")
                + cli_render.style(
                    "muted",
                    " — an anchor that cannot be resolved: pkit friction explain <artefact>",
                ),
                *(f"  {report.location}" for report in listing.unresolved),
            ]
        )
    lines.extend(_unanchored_lines(listing))
    shown = [kind for kind in DEBT_KINDS if listing.count(kind)]
    if shown:
        width = max(len(kind.value) for kind in shown)
        lines.extend(["", cli_render.style("heading", "Legend")])
        lines.extend(f"  {kind.value:{width}}  {_DEBT_LEGEND[kind]}" for kind in shown)
    lines.extend(
        [
            "",
            cli_render.style("heading", "Commands"),
            "  pkit friction explain <artefact>   one artefact: what changed, and what clears it",
            "  pkit friction debt --json          the same listing, machine-readable",
            "  pkit friction check --all          the whole report: dead anchors, measures",
        ]
    )
    return "\n".join(lines) + "\n"


def _unanchored_lines(listing: DebtListing) -> list[str]:
    """The unanchored measure (COR-050 point 8): the forgotten artefacts, counted, then
    apart from them those accepted with a reason (point 1), each with its reason."""
    lines: list[str] = []
    if listing.unanchored:
        lines.extend(
            [
                "",
                cli_render.style("heading", "UNANCHORED")
                + cli_render.style(
                    "muted",
                    " — no anchors and no reason: anchor it, or write its unanchored-because",
                ),
                *(f"  {location}" for location in listing.unanchored),
            ]
        )
    accepted = listing.accepted_unanchored
    if accepted:
        width = max(len(entry.location) for entry in accepted)
        lines.extend(
            [
                "",
                cli_render.style("heading", "ACCEPTED UNANCHORED")
                + cli_render.style("muted", " — not counted: the reason a person gave for none"),
                *(f"  {entry.location:{width}}  {entry.reason}" for entry in accepted),
            ]
        )
    return lines


# --- one artefact, explained ---------------------------------------------------------


@dataclass(frozen=True)
class Answer:
    """One answer of COR-050 point 5 that clears a finding, as the writer command giving it."""

    answer: str  # `updated`, `unchanged` or `deferred`
    command: str

    def as_json(self) -> dict[str, str]:
        return {"answer": self.answer, "command": self.command}


@dataclass(frozen=True)
class ExplainedFinding:
    """A finding with the commits behind it, and what clears it.

    `clears` says how, in one line; `answers` are the writer commands that
    give it — none where no writer answers the finding (a dead anchor needs
    an edit of the anchor list, an unreachable point a fuller clone).
    """

    finding: fr.RepositoryFinding
    commits: tuple[fr.CommitBehind, ...]  # oldest first, each with the paths behind it
    clears: str
    answers: tuple[Answer, ...]

    def as_json(self) -> dict[str, Any]:
        return {
            "kind": self.finding.kind.value,
            "anchor": _anchor_json(self.finding.anchor),
            "origin": None if self.finding.origin is None else self.finding.origin.as_json(),
            "message": self.finding.message,
            "commits": [commit.as_json() for commit in self.commits],
            "clears": self.clears,
            "answers": [answer.as_json() for answer in self.answers],
        }


@dataclass(frozen=True)
class ExplainedAnchor:
    """One anchor the artefact declares at HEAD, and what the check found about it.

    `files`, for a path anchor, are the files it stands on at the revalidation
    point and at HEAD, as the check decides a dead anchor, and those its glob
    covers at HEAD that `friction.exclude` leaves out (`fr.AnchorFiles`);
    `None` for another kind.
    """

    anchor: Anchor
    # A finding kind — `unresolved-kind` and `no-answer` among them — or `current`, or
    # `unreachable` when a shallow clone keeps the artefact from being judged.
    state: str
    # Commits behind its staleness only: a dead anchor's commits say where its files went.
    changes: int
    over_broad: bool
    files: fr.AnchorFiles | None = None

    def as_json(self) -> dict[str, Any]:
        return {
            "kind": self.anchor.kind,
            "value": self.anchor.value,
            "state": self.state,
            "changes": self.changes,
            "over_broad": self.over_broad,
            "files": None if self.files is None else self.files.as_json(),
        }


@dataclass(frozen=True)
class Explanation:
    """One artefact's friction at HEAD, as `explain` shows it."""

    head: HeadState
    shallow: bool
    artefact: Artefact
    report: fr.ArtefactReport | None  # `None`: nothing judged — no anchors, no deferrals, excluded
    anchors: tuple[ExplainedAnchor, ...]  # in written order
    findings: tuple[ExplainedFinding, ...]  # in the check's order

    @property
    def state(self) -> str:
        if self.artefact.excluded:
            return EXCLUDED
        return UNANCHORED if self.report is None else self.report.state.value

    @property
    def deferred(self) -> tuple[Anchor, ...]:
        """The anchors the artefact defers, as written."""
        return tuple(d.anchor for d in self.artefact.deferrals)


def run_explain(
    target_root: Path,
    reference: str,
    *,
    registry: Mapping[str, ResolverCommand] | None = None,
) -> Explanation:
    """Explain the artefact `reference` names at HEAD.

    Raises `FrictionReportError` when no place is declared or the reference
    names no artefact at HEAD (or more than one), and `FrictionCheckError`
    when the check cannot run.
    """
    check = fr.run_artefact_check(target_root, _named(reference), registry=registry)
    if check is None:
        raise FrictionReportError(
            "no places are declared at HEAD (`friction.places` in .pkit/project/config.yaml, or "
            "a capability's), so there is no artefact to explain."
        )
    location = check.artefact.location
    declared = anchors_of(check.artefact)
    findings = tuple(
        _explained(traced, location, declared, check.artefact) for traced in check.findings
    )
    unjudged: str | None = None  # what an anchor with no finding shows, when not judged
    if check.artefact.excluded:
        unjudged = EXCLUDED
    elif check.report is not None and check.report.state is fr.ArtefactState.UNREACHABLE:
        unjudged = fr.ArtefactState.UNREACHABLE.value
    anchors = tuple(
        _anchor_state(anchor, findings, unjudged, check.files.get(anchor)) for anchor in declared
    )
    return Explanation(
        head=check.head,
        shallow=check.shallow,
        artefact=check.artefact,
        report=check.report,
        anchors=anchors,
        findings=findings,
    )


def _named(reference: str) -> Callable[[Discovery], Artefact]:
    """The artefact `reference` names among HEAD's, by the writers' rule (`find_artefact`).

    Its location first — `path` for a document, `path#id` for a collection
    entry — then any identifier an artefact anchor may use: its id, a
    document's path, a method rule's `<component>:<id>`. A document a component
    holds is named with its owner, as the writers name it.
    """

    def select(discovery: Discovery) -> Artefact:
        file_part = reference.split("#", 1)[0]
        held = discovery.holding(file_part)
        if held is not None:  # a component's document, not an artefact (COR-050 point 1)
            raise FrictionReportError(f"{held_message(held)} There is nothing to explain.")
        for unreadable in discovery.unreadable:
            if unreadable.path == file_part:
                raise FrictionReportError(
                    f"{unreadable.path}: front matter does not parse at HEAD "
                    f"({unreadable.reason}); fix it first — `pkit validate` reports it."
                )
        matches = [a for a in discovery.artefacts if a.location == reference] or [
            a for a in discovery.artefacts if reference in a.identifiers
        ]
        if len(matches) > 1:
            listed = ", ".join(a.location for a in matches)
            raise FrictionReportError(
                f"{reference!r} names {len(matches)} artefacts at HEAD ({listed}); name one by "
                f"its location."
            )
        if not matches:
            in_file = [a.location for a in discovery.artefacts if a.path == file_part]
            hint = f" The file holds {', '.join(in_file)}." if in_file else ""
            raise FrictionReportError(
                f"no artefact at HEAD is named {reference!r} — give its location (`path`, or "
                f"`path#id` for a collection entry) or its id. The explanation reads HEAD, like "
                f"`pkit friction check --all`: commit a new artefact first.{hint}"
            )
        return matches[0]

    return select


def _explained(
    traced: fr.TracedFinding, location: str, declared: Sequence[Anchor], artefact: Artefact
) -> ExplainedFinding:
    """A finding with what clears it (COR-050 points 3, 4, 5 and 7)."""
    finding = traced.finding
    anchor = finding.anchor
    revalidate = (
        Answer(
            "updated",
            command_line("pkit", "friction", "revalidate", location, "--outcome", "updated"),
        ),
        Answer(
            "unchanged",
            command_line(
                "pkit",
                "friction",
                "revalidate",
                location,
                "--outcome",
                "unchanged",
                "--because",
                BECAUSE,
            ),
        ),
    )
    answers: tuple[Answer, ...] = ()
    kind = finding.kind
    if kind is _Kind.STALE and anchor is None and finding.message.startswith(fr.LET_BACK_IN):
        clears = "revalidate the artefact: letting it back in cannot be deferred"
        answers = revalidate
    elif kind is _Kind.STALE and anchor is None:
        clears, answers = "revalidate the artefact: a move cannot be deferred", revalidate
    elif kind is _Kind.STALE and anchor is not None:
        defer = command_line(
            "pkit", "friction", "defer", location, "--anchor", _label(anchor), "--reason", REASON
        )
        clears = "revalidate the artefact, or defer the anchor"
        answers = (*revalidate, Answer("deferred", defer))
    elif kind is _Kind.DEFERRED and anchor is not None and anchor not in declared:
        clears = (
            f"any revalidation: the artefact no longer declares {_label(anchor)}, so the entry "
            f"dangles (`pkit validate` fails on it)"
        )
        answers = revalidate
    elif kind is _Kind.DEFERRED and anchor is not None:
        clears = f"a revalidation that does not keep it (`--keep {_label(anchor)}` keeps it)"
        answers = revalidate
    elif kind is _Kind.LEFT_OUT and anchor is not None:
        clears = (
            "nothing is owed; a revalidation reads the anchor under HEAD's `friction.exclude`, "
            "which ends the report"
        )
        answers = revalidate[1:]
    elif kind is _Kind.DEAD_ANCHOR and anchor is not None:
        clears = (
            f"correct {_label(anchor)} or remove it from the block, then revalidate (the "
            f"writers do not edit anchors, and a changed anchor list needs a revalidation)"
        )
    elif kind is _Kind.UNRESOLVED_KIND and anchor is not None:
        clears = (
            f"install the capability that resolves `{anchor.kind}` anchors, or mend its "
            f"registration where the finding says it is refused, or remove {_label(anchor)} from "
            f"the block and revalidate"
        )
    elif kind is _Kind.NO_ANSWER and anchor is not None:
        clears = (
            "run again; if its resolver gives no answer again, run `pkit sync`, or the resolver "
            "needs mending"
        )
    elif kind is _Kind.OVER_BROAD and anchor is not None:
        clears = (
            f"narrow {_label(anchor)} in the block, then revalidate (a changed anchor list "
            f"needs a revalidation)"
        )
    elif kind is _Kind.UNREACHABLE:
        clears = "fetch the full history (`git fetch --unshallow`) and run again"
    else:
        clears = f"see `pkit friction check --all` on {artefact.location}"
    return ExplainedFinding(finding, traced.commits, clears, answers)


# The state an anchor shows: the first of these kinds a finding about it has.
_ANCHOR_STATES = (
    _Kind.DEAD_ANCHOR,
    _Kind.UNRESOLVED_KIND,
    _Kind.NO_ANSWER,
    _Kind.STALE,
    _Kind.DEFERRED,
)


def _anchor_state(
    anchor: Anchor,
    findings: Sequence[ExplainedFinding],
    unjudged: str | None,
    files: fr.AnchorFiles | None,
) -> ExplainedAnchor:
    """An anchor's state: its first finding's kind, else `unjudged` — why the artefact
    was not judged — else `current`."""
    about = [f for f in findings if f.finding.anchor == anchor]
    kinds = {f.finding.kind for f in about}
    state = next((k.value for k in _ANCHOR_STATES if k in kinds), None)
    if state is None:
        state = unjudged or "current"
    changes = sum(len(f.commits) for f in about if f.finding.kind is _Kind.STALE)
    return ExplainedAnchor(anchor, state, changes, _Kind.OVER_BROAD in kinds, files)


#: The version of the document `render_explain_json` returns. A change a reader could
#: break against — a key removed, renamed or given another meaning — raises it; a key
#: added does not. A document without it comes from a backbone that predates it:
#: version 1.
EXPLAIN_SCHEMA_VERSION = 1


def render_explain_json(explanation: Explanation) -> str:
    """The stable machine-readable explanation: keys sorted, no ages."""
    report = explanation.report
    document = {
        "schema_version": EXPLAIN_SCHEMA_VERSION,
        "report": "explain",
        "head": {
            "commit": explanation.head.commit,
            "uncommitted_paths": explanation.head.uncommitted,
        },
        "history": {"shallow": explanation.shallow},
        "artefact": explanation.artefact.id,
        "location": explanation.artefact.location,
        "body": explanation.artefact.body,
        "state": explanation.state,
        "unanchored_because": explanation.artefact.unanchored_because,
        "excluded_by": _setting_json(explanation.artefact.excluded_by),
        "revalidation_point": (
            None
            if report is None or report.revalidation_point is None
            else report.revalidation_point.as_json()
        ),
        "revalidation_points": (
            [] if report is None else [point.as_json() for point in report.revalidation_points]
        ),
        "deferral_points": (
            []
            if report is None
            else [
                {
                    "anchor": _anchor_json(anchor),
                    "point": None if point is None else point.as_json(),
                }
                for anchor, point in report.deferral_points
            ]
        ),
        "anchors": [anchor.as_json() for anchor in explanation.anchors],
        "findings": [finding.as_json() for finding in explanation.findings],
    }
    return json.dumps(document, indent=2, sort_keys=True) + "\n"


_STATE_GLOSS = {
    "current": "no anchor changed since its points",
    "stale": "an anchor changed, or the artefact moved, with no answer since",
    "deferred": "friction deliberately postponed; nothing stale",
    "unreachable": "a point lies beyond this shallow clone — git fetch --unshallow",
    "unresolved": "not judged: an anchor cannot be resolved; its other anchors' findings stand",
    UNANCHORED: "no anchors and no deferrals: nothing to judge",
    EXCLUDED: "under an excluded path: left out of the measures and the debt",
}

# What the commits under a finding are, by its kind.
_COMMITS_LABEL = {
    _Kind.STALE: "changed in, oldest first",
    _Kind.DEFERRED: "postpones, oldest first",
    _Kind.LEFT_OUT: "left out in, oldest first",
    _Kind.DEAD_ANCHOR: "where its files went, oldest first",
}

_ANCHOR_GLOSS = {
    "current": "unchanged since the revalidation point",
    "deferred": "deferred; nothing after its deferral point",
    "unreachable": "not judged: a point lies beyond this shallow clone",
    EXCLUDED: "not judged: the artefact is under an excluded path",
}


def render_explain_human(explanation: Explanation, *, now: datetime | None = None) -> str:
    """The read view: the artefact's state, points and anchors, each finding and its answers."""
    now = datetime.now(UTC) if now is None else now
    artefact = explanation.artefact
    title = cli_render.style("title", "Friction explain") + f" — {artefact.location}"
    lines = [
        title + cli_render.style("muted", "   (every artefact: pkit friction check --all)"),
        "",
    ]
    if artefact.id != artefact.location:
        lines.append(f"  Artefact: {artefact.id}")
    state = explanation.state
    lines.append(f"  State: {state}" + cli_render.style("muted", f"   ({_STATE_GLOSS[state]})"))
    reason = artefact.unanchored_because
    if reason is not None:
        beside = cli_render.style("muted", "   (beside anchors: pkit validate refuses the pair)")
        lines.append(f"  Unanchored because: {reason}" + (beside if anchors_of(artefact) else ""))
    if artefact.excluded_by is not None:
        lines.append(f"  Excluded by: {_setting_cell(artefact.excluded_by)}")
    lines.extend(_header_lines(explanation.head, explanation.shallow))

    report = explanation.report
    if report is not None:
        lines.extend(["", *_point_lines(report)])
    if explanation.anchors:
        lines.extend(["", *_anchor_lines(explanation)])
    if report is not None or explanation.findings:
        lines.extend(["", *_finding_lines(explanation, now)])

    commands = [
        (
            command_line("pkit", "friction", "explain", artefact.location, "--json"),
            "the same, machine-readable",
        ),
        ("pkit friction debt", "every artefact's debt, oldest first"),
    ]
    width = max(len(command) for command, _gloss in commands)
    lines.extend(["", cli_render.style("heading", "Commands")])
    lines.extend(f"  {command:{width}}   {gloss}" for command, gloss in commands)
    return "\n".join(lines) + "\n"


def _point_lines(report: fr.ArtefactReport) -> list[str]:
    lines = [
        cli_render.style("heading", "POINTS")
        + cli_render.style("muted", " — from git: where each answer stands")
    ]
    # Every revalidation point, newest first: several where lines of work that do not
    # descend from one another each first carried the value (COR-050 point 3).
    revalidations: Sequence[fr.Commit | None] = report.revalidation_points or (
        report.revalidation_point,
    )
    rows: list[tuple[str, fr.Commit | None, str]] = [
        ("revalidation", point, "") for point in revalidations
    ]
    rows.extend(("deferral", point, _cell(anchor)) for anchor, point in report.deferral_points)
    width = max(len(name) for name, _point, _anchor in rows)
    for name, point, anchor in rows:
        where = (
            "beyond this clone's history"
            if point is None
            else f'{point.short}  {point.day}  "{point.subject}" ({point.author})'
        )
        lines.append(f"  {name:{width}}  {where}" + (f"   {anchor}" if anchor else ""))
    return lines


def _anchor_lines(explanation: Explanation) -> list[str]:
    lines = [
        cli_render.style("heading", "ANCHORS")
        + cli_render.style("muted", " — what makes it true, as HEAD declares it")
    ]
    anchors = explanation.anchors
    # A dead anchor, an unresolved kind or a missing answer is glossed with the check's
    # own reason.
    reasons = {
        (f.finding.kind.value, f.finding.anchor): f.finding.message for f in explanation.findings
    }
    kind_width = max(len(a.anchor.kind) for a in anchors)
    value_width = max(len(a.anchor.value) for a in anchors)
    state_width = max(len(a.state) for a in anchors)
    for explained in anchors:
        if explained.state == "stale":
            gloss = f"changed in {counted(explained.changes, 'commit', 'commits')} since its point"
        else:
            gloss = _ANCHOR_GLOSS.get(explained.state) or reasons.get(
                (explained.state, explained.anchor), ""
            )
        if explained.over_broad:
            gloss += " · over-broad"
        lines.append(
            f"  {explained.anchor.kind:{kind_width}}  {explained.anchor.value:{value_width}}  "
            f"{explained.state:{state_width}}  {gloss}"
        )
    return lines


def _finding_lines(explanation: Explanation, now: datetime) -> list[str]:
    lines = [
        cli_render.style("heading", "FINDINGS")
        + cli_render.style(
            "muted", " — as pkit friction check --all reports them: what changed, what clears it"
        )
    ]
    if not explanation.findings:
        lines.append("  nothing to answer")
        return lines
    kind_width = max(len(f.finding.kind.value) for f in explanation.findings)
    for explained in explanation.findings:
        finding = explained.finding
        message = finding.message
        if finding.kind is _Kind.DEFERRED and finding.origin is not None:
            message += f", {_age(now, finding.origin.date)}"
        lines.append(f"  {finding.kind.value:{kind_width}}  {_cell(finding.anchor)}  {message}")
        if explained.commits:
            label = _COMMITS_LABEL.get(finding.kind, "behind it")
            if finding.kind is _Kind.STALE and finding.anchor is None:
                label = "let back in" if finding.message.startswith(fr.LET_BACK_IN) else "moved in"
            author_width = max(len(c.commit.author) for c in explained.commits)
            lines.append(f"    {label}:")
            lines.extend(f"      {_commit_row(c.commit, author_width)}" for c in explained.commits)
        if explained.answers:
            lines.append(f"    clears it — {explained.clears}:")
            width = max(len(a.answer) for a in explained.answers)
            lines.extend(f"      {a.answer:{width}}  {a.command}" for a in explained.answers)
        else:
            lines.append(f"    clears it — {explained.clears}")
    kept = explanation.deferred
    if any(f.finding.kind is _Kind.STALE for f in explanation.findings) and kept:
        listed = ", ".join(_label(anchor) for anchor in kept)
        lines.extend(
            [
                "",
                f"  A revalidation answers every stale anchor at once and re-states the "
                f"deferrals: name each one kept with --keep ({listed}); the rest are removed.",
            ]
        )
    return lines


__all__ = [
    "BECAUSE",
    "DEBT_KINDS",
    "DEBT_SCHEMA_VERSION",
    "EXCLUDED",
    "EXPLAIN_SCHEMA_VERSION",
    "REASON",
    "UNANCHORED",
    "Answer",
    "DebtEntry",
    "DebtListing",
    "ExplainedAnchor",
    "ExplainedFinding",
    "Explanation",
    "FrictionReportError",
    "render_debt_human",
    "render_debt_json",
    "render_explain_human",
    "render_explain_json",
    "run_debt",
    "run_explain",
]
