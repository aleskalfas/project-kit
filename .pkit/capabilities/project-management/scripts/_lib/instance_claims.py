"""Claim and release of instance ownership in the lifecycle, and the clash guard
(DEC-035 points 3, 4 and 6, DEC-059 points 5, 7 and 9).

A clone that set its instance id (``set-instance``) marks the issues it owns.
``create-issue`` claims each issue it files, so the clone owns the filed arc
from birth; ``start-work`` claims an issue no instance owns yet (the commons);
``close-issue`` releases the owner as the issue closes, in every mode, and
``done-work`` releases through the ``close-issue --mode pr-merge`` it runs for
each issue its merge closed (DEC-035 points 3 and 4).

**Activation.** Outside a topology of seats, :func:`this_clone` answers ``None``
when no instance id is set, and every caller then writes and prints exactly
what it did before: the id is the sole activation gate (DEC-035 point 1). The
substrate is read only once an id is set, from the adopter's
``project/instance-ownership.yaml``, through the seam's selector (default
``comment``, DEC-043 point 2).

**A project with a topology of seats** (DEC-059). There a clone takes part by
holding a seat, and its number is the seat's, never a typed one (point 6). The
run's reading of the topology, this clone's seat and each seat's holder, comes
from :func:`read_topology`, whose source lands with #2140 and #2141. The clone's
key is read from its runtime file (``_lib/instance_identity``). A clone that
holds no seat marks no issue and is guarded by nothing. A claim names the seat,
its number and the clone's key, in the audit-log facility's stamp (point 9). It
counts only while that clone holds that seat, judged when it is read, so a
seat's release frees its clone's claims with no write (point 5). A planner's
seat files with no owner, so its work enters the shared pool, and every other
seat claims at filing; a worker claims at ``start-work`` (point 7). Renewal,
lapse and parking are not built yet.

**Every write is the seam's.** The ownership-event comment, the ``instance:N``
label and its lazy creation, and the owner mirror in the issue description are
built by ``_lib/instance_ownership`` and nowhere else (ADR-041 point 3). Owners
are read only through the seam's fold, ``resolve_owner`` (ADR-041 point 1). This
module decides when each write fires and what a result means: the failure
posture ADR-041 point 5 leaves to the caller.

**The claim re-reads.** A claim writes its marker, reads the issue again and
folds it. Where another instance claimed in the same instant, both markers are
there, and the higher-numbered instance backs off with an ``abandon`` event, or
by removing its label: the lowest instance wins, a choice every clone computes
from the markers alone (DEC-035 point 6). It is not a lock. A clone whose re-read
came before the other's claim keeps its claim, and the fold shows both.

**The clash guard** (DEC-035 point 6). :func:`guard` refuses an ordinary command
(``start-work``, ``review-work``, ``done-work``, ``promote-issue``,
``edit-issue``, ``move-issue``) on an issue another instance owns, at
``bypassable-with-audit`` (DEC-014): a bypass carries a reason, posted on the
issue as an audit comment before the command writes. In a project with a
topology, a claim that does not count is no claim, and one the fold cannot
judge refuses as one that counts (ADR-041 point 5).

**The owner is the assignee paired with an instance** (DEC-035 point 2). A clone
claims only an issue assigned to its own account, so a marker the fold trusts
is authored by the assignee (DEC-043 point 3). An issue filed for another person
is not claimed (DEC-035 point 5).

**A release clears every owner** the issue carries, whichever clone closes it:
an event per owning instance in ``comment`` mode, and each ``instance:N`` label
removed. A comment marker is released only by its own account's clone, since
the fold trusts no other author. In ``comment`` mode an ``instance:N`` label
beside a comment marker is residual, left from a label-mode past, and a claim
removes it (ADR-041 point 2). With no marker beside it, the seam reads the label
as the owner, so it is no residue. Where the lowest such label is this clone's,
a claim writes the comment marker first, and only then are the labels residual.
Where a lower instance's label is there, this clone withdraws by removing its
own label alone.

**The mirror.** In ``comment`` mode each claim and release regenerates the owner
mirror from the fold, before the provenance footer, through
``provenance.stamp`` (ADR-037). The mirror is derived, so a failed write of it is
a warning and loses nothing (ADR-041 point 4).

Realm-blind: nothing here is read by a gate, a transition or the cascade fold
(DEC-035 point 8).
"""

from __future__ import annotations

import contextlib
import json
import sys
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from _lib import audit, provenance
from _lib import instance_ownership as ownership
from _lib.comment import post_audit_once
from _lib.instance_identity import read_clone_key, read_instance_id

#: The adopter's substrate selector, in the marker's own schema home (DEC-043
#: point 2), relative to the capability root.
SETTINGS_RELATIVE = "project/instance-ownership.yaml"

#: The fields one read of an issue takes: who it is assigned to, its labels, its
#: comments (the event log) and its body (the mirror's home).
VIEW_FIELDS = "assignees,labels,comments,body"

# Outcomes. A claim ends CLAIMED, HELD, ELSEWHERE, NOT_CLAIMED, LOST or FAILED; a
# release ends RELEASED, NOTHING, NOT_RELEASED or FAILED.
CLAIMED = "claimed"
HELD = "held"
ELSEWHERE = "owned-elsewhere"
NOT_CLAIMED = "not-claimed"
LOST = "lost"
RELEASED = "released"
NOTHING = "nothing"
NOT_RELEASED = "not-released"
FAILED = "failed"

# The clash guard ends PASSED, BYPASSED, REFUSED or FAILED (its audit comment
# could not be posted, so the command does nothing).
PASSED = "passed"
BYPASSED = "bypassed"
REFUSED = "refused"

#: The outcomes said as a warning, on standard error.
WARNINGS = frozenset({LOST, FAILED})

#: The seats' roles (DEC-059 point 2).
PLANNER = "planner"
WORKER = "worker"
LEAD = "lead"

#: The writer named in the key of the clash guard's audit comment. The comment
#: names no command, so a command and the move it composes post it once.
GUARD_AUDIT_WRITER = "ownership-guard"

Run = Callable[[list[str]], Any]


@dataclass(frozen=True)
class Seat:
    """A seat of the topology, as this clone holds it: its name, its number,
    which is its place in the topology, and its role (DEC-059 points 2 and 6)."""

    name: str
    number: int
    role: str


@dataclass(frozen=True)
class Topology:
    """One run's reading of the project's topology, as instance ownership takes
    it from its caller (ADR-041 point 7, ADR-071 point 1): the seat this clone
    holds, or None, and each seat's holder."""

    seat: Seat | None
    holders: Mapping[str, ownership.Holder]


@dataclass(frozen=True)
class Clone:
    """This clone, as instance ownership sees it: its instance number, the
    substrate the adopter selected, its GitHub account and its capability root
    (where the provenance footer reads its versions). In a project with a
    topology it also holds a seat, has a key, and carries each seat's holder,
    read once for the run."""

    instance: int
    substrate: str
    login: str | None
    capability_root: Path
    seat: Seat | None = None
    key: str | None = None
    holders: Mapping[str, ownership.Holder] | None = None

    @property
    def files_unowned(self) -> bool:
        """A planner files with no owner, so its work enters the shared pool
        (DEC-059 point 7). Every other seat owns what it files."""
        return self.seat is not None and self.seat.role == PLANNER

    def named(self) -> str:
        """How a line names this clone: its instance, and its seat where it holds one."""
        if self.seat is None:
            return f"instance {self.instance}"
        return f"seat {self.seat.name}, instance {self.instance}"


@dataclass(frozen=True)
class Result:
    """What a claim or a release did, and the line its caller prints.

    ``winner`` is the instance that holds the issue once the step is over, where
    one does. ``notes`` are further lines, such as a mirror that could not be
    written."""

    outcome: str
    line: str
    winner: int | None = None
    notes: tuple[str, ...] = ()

    @property
    def warning(self) -> bool:
        return self.outcome in WARNINGS


@dataclass(frozen=True)
class Guard:
    """What the clash guard decided, and the line its caller prints, if any."""

    outcome: str
    line: str = ""

    @property
    def refused(self) -> bool:
        return self.outcome in (REFUSED, FAILED)

    @property
    def bypassed(self) -> bool:
        return self.outcome == BYPASSED


def say(result: Result) -> None:
    """Print a result: its line on standard output, or on standard error where
    it is a warning, and each note on standard error."""
    print(result.line, file=sys.stderr if result.warning else sys.stdout)
    for note in result.notes:
        print(note, file=sys.stderr)


def say_guard(decision: Guard) -> None:
    """Print the guard's line: a refusal on standard error, a bypass as a warning
    on standard error, a dry run's on standard output, and nothing on a pass."""
    if not decision.line:
        return
    stream = sys.stdout if decision.line.startswith("[dry-run]") else sys.stderr
    print(decision.line, file=stream)


def this_clone(
    capability_root: Path, login: str | None, config: dict | None = None
) -> Clone | None:
    """This clone, or ``None`` when it takes no part in instance ownership.

    ``None`` is the no-op: the caller does nothing more than it did before
    instance ownership existed. In a project with a topology, the clone takes
    part only while it holds a seat, and its number is the seat's (DEC-059
    point 6). Its key is the one its runtime file keeps, which a clone that holds
    a seat has. Otherwise an instance id must be set, and the substrate selector
    is read only then."""
    topology = read_topology(capability_root, config or {})
    if topology is not None:
        key = read_clone_key(capability_root) if topology.seat is not None else None
        if topology.seat is None or key is None:
            return None
        return Clone(
            topology.seat.number,
            "comment",
            login,
            capability_root,
            seat=topology.seat,
            key=key,
            holders=topology.holders,
        )
    instance = read_instance_id(capability_root)
    if instance is None:
        return None
    substrate = ownership.resolve_substrate(_read_settings(capability_root))
    return Clone(instance, substrate, login, capability_root)


def read_topology(capability_root: Path, config: dict) -> Topology | None:
    """This run's reading of the project's topology, or ``None`` where the
    project declares none.

    The module that reads the topology from the default branch, and each seat's
    holder from its state issue, builds this reading once for each run (ADR-071
    point 1). It lands with #2140 and #2141. Until then no project has a
    topology, and every command keeps DEC-035's behaviour."""
    return None


def _read_settings(capability_root: Path) -> dict[str, Any] | None:
    """The adopter's ``instance-ownership.yaml``, or ``None`` when it is absent
    or cannot be read, which the selector reads as the default."""
    path = capability_root / SETTINGS_RELATIVE
    if not path.is_file():
        return None
    try:
        data = YAML(typ="safe").load(path.read_text(encoding="utf-8"))
    except (OSError, YAMLError):
        return None
    return data if isinstance(data, dict) else None


# ---- the plan lines a dry run and a summary print ----------------------


def claim_plan(clone: Clone, assignee: str | None = None, *, filing: bool = False) -> str:
    """What a claim will do, for a pre-flight summary. ``assignee`` is the
    account an issue being filed is assigned to, where it is known, and
    ``filing`` says the claim is the one at filing."""
    if filing and clone.files_unowned:
        return (
            f"not claimed: {clone.named()} is a planner's seat, which files with no owner, "
            "so the issue enters the shared pool"
        )
    if assignee is not None and assignee != clone.login:
        return (
            f"not claimed: assigned to @{assignee}, not to this clone's account ({clone.named()})"
        )
    return f"claimed for {clone.named()} ({clone.substrate} substrate)"


def claims_at_filing(clone: Clone, assignee: str | None) -> bool:
    """Whether ``create-issue`` claims what it files: for this clone's own
    account, and not from a planner's seat (DEC-035 points 3 and 5, DEC-059
    point 7)."""
    return assignee == clone.login and not clone.files_unowned


def release_plan(clone: Clone) -> str:
    """What a release will do, for a pre-flight summary."""
    return f"released on close (this clone is {clone.named()}, {clone.substrate} substrate)"


# ---- claim ------------------------------------------------------------------


def claim(issue_number: int, clone: Clone, config: dict, *, run: Run | None = None) -> Result:
    """Claim ``issue_number`` for this clone, unless an instance owns it.

    Reads the issue, writes the claim where no instance owns it, reads it again
    and backs off where a lower-numbered instance claimed in the same instant.
    In ``comment`` mode it also writes the claim where this clone owns the issue
    by its label alone, before the label is removed. It then regenerates the
    owner mirror. Never raises on a ``gh`` failure: the result says what
    happened."""
    gh = run or _runner(config)
    n = issue_number
    if not clone.login:
        return Result(
            NOT_CLAIMED,
            f"[note] ownership: #{n} is not claimed: this clone's GitHub account "
            "could not be resolved.",
        )
    issue = _read(gh, n)
    if issue is None:
        return Result(FAILED, f"[warn] ownership: #{n} could not be read, so it is not claimed.")
    assignees = _assignees(issue)
    if clone.login not in assignees:
        who = ", ".join(f"@{a}" for a in assignees) or "nobody"
        return Result(
            NOT_CLAIMED,
            f"[note] ownership: #{n} is not claimed: it is assigned to {who}, not to "
            f"@{clone.login}, this clone's account.",
        )
    before = _resolve(issue, clone.login, clone)
    if before.claimants and clone.instance not in before.owners:
        first = min(before.claimants)
        return Result(
            ELSEWHERE,
            f"[note] ownership: #{n} is owned by {_owner(before, first)}, so this clone, "
            f"{clone.named()}, did not claim it.",
            winner=first,
        )
    held = before.owners == frozenset({clone.instance})
    # In comment mode, an issue whose lowest owner is this clone's label alone
    # has no other marker, and the strip below removes that label: the claim is
    # written on the comment log first, and the issue is read again (ADR-041
    # point 2).
    by_label = (
        clone.substrate == "comment"
        and before.substrate == "label"
        and before.winner == clone.instance
    )
    if not before.claimants or by_label:
        failure = _write_claim(gh, n, clone)
        if failure is not None:
            return Result(FAILED, f"[warn] ownership: the claim on #{n} failed: {failure}")
        issue = _read(gh, n)
        if issue is None:
            return Result(
                FAILED,
                f"[warn] ownership: #{n} was claimed for {clone.named()}, but the "
                "re-read that checks for a same-instant claim failed. Run this again.",
            )
    notes = _strip_residual_labels(gh, n, issue, clone)
    after = _resolve(issue, clone.login, clone)
    if clone.instance not in after.owners:
        return Result(
            FAILED,
            f"[warn] ownership: the claim on #{n} for {clone.named()} did not show "
            "when the issue was read again.",
            winner=after.winner,
        )
    # An unjudged claim of a lower number may be the winner: the claim path
    # treats it as one that counts (ADR-041 point 5).
    winner = min(after.claimants)
    if winner != clone.instance:
        return _back_off(gh, n, clone, after, winner, notes)
    notes.extend(_mirror(gh, n, clone, issue, clone.login))
    if held:
        line = f"[ok] ownership: #{n} is already owned by this clone, {clone.named()}."
        return Result(HELD, line, winner=clone.instance, notes=tuple(notes))
    contested = len(after.claimants) > 1
    line = f"[ok] ownership: #{n} claimed for {clone.named()} ({clone.substrate} substrate)" + (
        ", ahead of a higher instance that claimed in the same instant." if contested else "."
    )
    return Result(CLAIMED, line, winner=clone.instance, notes=tuple(notes))


def _write_claim(gh: Run, n: int, clone: Clone) -> str | None:
    """Write this clone's claim on the selected substrate; the failure, or None.
    In a project with a topology the claim names the seat, its number and the
    clone's key (DEC-059 point 9)."""
    if clone.substrate == "label":
        proc = gh(ownership.instance_label_args(issue_number=n, instance=clone.instance))
        if _ok(proc):
            return None
        # DEC-035 point 2: the label is created on first use. One retry, after.
        create = gh(ownership.instance_label_create_args(instance=clone.instance))
        if not _ok(create):
            return f"{_said(proc)}, and creating the label failed: {_said(create)}"
        proc = gh(ownership.instance_label_args(issue_number=n, instance=clone.instance))
        return None if _ok(proc) else _said(proc)
    seat = clone.seat
    proc = gh(
        ownership.ownership_event_comment_args(
            issue_number=n,
            versions=_versions(clone),
            event="claim",
            instance=clone.instance,
            seat=seat.name if seat is not None else None,
            seat_number=seat.number if seat is not None else None,
            clone=clone.key if seat is not None else None,
        )
    )
    return None if _ok(proc) else _said(proc)


def _back_off(
    gh: Run,
    n: int,
    clone: Clone,
    after: ownership.OwnershipResolution,
    winner: int,
    notes: list[str],
) -> Result:
    """Abandon this clone's claim: a lower instance claimed in the same instant
    and wins (DEC-035 point 6). A claim the seam read from a label, in either
    mode, is withdrawn by removing that label."""
    if clone.substrate == "label" or after.substrate == "label":
        proc = gh(
            ownership.instance_label_args(issue_number=n, instance=clone.instance, remove=True)
        )
    else:
        proc = gh(
            ownership.ownership_event_comment_args(
                issue_number=n, versions=_versions(clone), event="abandon", instance=clone.instance
            )
        )
    rival = _owner(after, winner)
    if not _ok(proc):
        return Result(
            FAILED,
            f"[warn] ownership: {rival} claimed #{n} in the same instant and wins, "
            f"but this clone, {clone.named()}, could not withdraw its own claim: "
            f"{_said(proc)}",
            winner=winner,
            notes=tuple(notes),
        )
    issue = _read(gh, n)
    if issue is not None:
        notes.extend(_mirror(gh, n, clone, issue, clone.login))
    return Result(
        LOST,
        f"[warn] ownership: {rival} claimed #{n} in the same instant, and the "
        f"lowest instance wins: this clone, {clone.named()}, withdrew its claim.",
        winner=winner,
        notes=tuple(notes),
    )


# ---- the clash guard (DEC-035 point 6) ------------------------------------------


def guard(
    issue_number: int,
    clone: Clone,
    config: dict,
    *,
    verb: str,
    flag: str,
    bypass: str | None,
    invoker: Any,
    dry_run: bool = False,
    run: Run | None = None,
) -> Guard:
    """Refuse ``verb`` on an issue another instance owns, unless ``bypass``
    gives a reason (DEC-035 point 6, DEC-014's ``bypassable-with-audit``).

    The owner is read through the seam's fold. An issue no claim holds, or one
    this clone holds, passes. In a project with a topology a claim that does not
    count is no claim, and a claim the fold cannot judge refuses as one that
    counts (ADR-041 point 5). An issue that cannot be read refuses too, since
    whose it is cannot be told. A bypass posts its audit comment before the
    command writes, once however many commands of one act post it, and a dry run
    posts none. ``flag`` is the command's spelling of the bypass (DEC-046)."""
    gh = run or _runner(config)
    n = issue_number
    issue = _read(gh, n)
    if issue is None:
        why = f"#{n} could not be read, so whose it is cannot be told"
    else:
        assignees = _assignees(issue)
        account = clone.login if clone.login in assignees else (assignees[0] if assignees else None)
        resolution = _resolve(issue, account, clone)
        if not resolution.claimants:
            return Guard(PASSED)
        first = min(resolution.claimants)
        if account == clone.login and first == clone.instance and first in resolution.owners:
            return Guard(PASSED)
        whose = f" of @{account}" if account and account != clone.login else ""
        why = f"#{n} is owned by {_owner(resolution, first)}{whose}"
    me = clone.named()
    reason = (bypass or "").strip()
    if not reason:
        return Guard(
            REFUSED,
            f"[refused] {verb} #{n}: {why}, and this clone is {me}. The clash guard refuses "
            "an ordinary command on another instance's issue (DEC-035 point 6). Leave it to "
            f'its owner, or pass {flag} "<reason>" to act anyway: the reason is posted on '
            "the issue as an audit comment.",
        )
    if dry_run:
        return Guard(
            BYPASSED, f"[dry-run] ownership: {why}; {flag} would post an audit comment first."
        )
    key = audit.audit_key(GUARD_AUDIT_WRITER, str(n), why, me, reason)
    body = (
        f"{audit.render_audit_comment(clone.capability_root, invoker, reason)}\n\n"
        f"The clash guard was bypassed: {why}, and this clone, {me}, acted on it "
        f"(DEC-035 point 6).\n\n{key}"
    )
    if not post_audit_once("issue", n, key, body, config, run=lambda args, _c, **_k: gh(args)):
        return Guard(
            FAILED,
            f"[refused] {verb} #{n}: {why}, and the audit comment {flag} posts could not "
            "be written, so nothing was done.",
        )
    return Guard(
        BYPASSED,
        f"[warn] ownership: {why}, and {flag} let this clone, {me}, act on it. "
        "The reason is on the issue.",
    )


# ---- release ----------------------------------------------------------------


def release(issue_number: int, clone: Clone, config: dict, *, run: Run | None = None) -> Result:
    """Release every owner of ``issue_number`` as it closes (DEC-035 point 4).

    Posts a ``release`` event for each instance the comment log holds, where the
    log is this clone's account's, and removes each ``instance:N`` label. In a
    project with a topology the log's claims are judged against the seats'
    holders, as the claim and the guard judge them: a claim that counts, or one
    that cannot be judged, is released, and a void claim is no owner to release.
    In ``comment`` mode it then regenerates the owner mirror."""
    gh = run or _runner(config)
    n = issue_number
    issue = _read(gh, n)
    if issue is None:
        return Result(FAILED, f"[warn] ownership: #{n} could not be read, so it is not released.")
    assignees = _assignees(issue)
    account = clone.login if clone.login in assignees else (assignees[0] if assignees else None)
    logged = ownership.resolve_owner(
        comments=_comments(issue),
        labels=[],
        assignee_login=account,
        selector="comment",
        holders=clone.holders,
    ).claimants
    labelled = ownership.resolve_owner(
        comments=[], labels=_labels(issue), assignee_login=account, selector="label"
    ).owners
    if not logged and not labelled:
        line = f"[ok] ownership: no instance owned #{n}, so there was nothing to release."
        return Result(NOTHING, line)
    # A comment marker counts only from its account (DEC-043 point 3), so a
    # release from another account would be ignored: it is not posted.
    kept = sorted(logged) if logged and account != clone.login else []
    versions = _versions(clone)
    writes = [
        ownership.ownership_event_comment_args(
            issue_number=n, versions=versions, event="release", instance=i
        )
        for i in ([] if kept else sorted(logged))
    ] + [
        ownership.instance_label_args(issue_number=n, instance=i, remove=True)
        for i in sorted(labelled)
    ]
    failures = [_said(proc) for proc in map(gh, writes) if not _ok(proc)]
    released = sorted((set() if kept else set(logged)) | set(labelled))
    notes: list[str] = []
    if clone.substrate == "comment":
        reread = _read(gh, n)
        if reread is not None:
            notes.extend(_mirror(gh, n, clone, reread, account))
    if failures:
        return Result(
            FAILED,
            f"[warn] ownership: #{n} closed, but its owner could not all be released: "
            + "; ".join(failures),
            notes=tuple(notes),
        )
    if kept:
        return Result(
            NOT_RELEASED,
            f"[note] ownership: #{n} is owned by @{account}'s "
            + ", ".join(f"instance {i}" for i in kept)
            + ", and only that account's clone can release it.",
            notes=tuple(notes),
        )
    instances = ", ".join(f"instance {i}" for i in sorted(set(released)))
    return Result(RELEASED, f"[ok] ownership: #{n} released ({instances}).", notes=tuple(notes))


# ---- shared steps -------------------------------------------------------------


def _owner(resolution: ownership.OwnershipResolution, instance: int) -> str:
    """How a line names the owner ``instance``: its seat, where its claim names
    one, and why its claim could not be judged, where it could not."""
    judgement = resolution.judgement(instance)
    if judgement is None or not judgement.seat:
        name = f"instance {instance}"
    else:
        name = f"seat {judgement.seat}, instance {instance}"
    if judgement is not None and judgement.verdict == ownership.UNJUDGED:
        return f"{name}, whose claim could not be judged since {judgement.reason}"
    return name


def _strip_residual_labels(gh: Run, n: int, issue: dict, clone: Clone) -> list[str]:
    """In ``comment`` mode, remove any ``instance:N`` label the issue still
    carries from a label-mode past: it is residual, and the next ownership
    mutation removes it (ADR-041 point 2). A label is residual only beside a
    comment marker: with none, the label is the owner and stays. The warnings,
    if a removal failed."""
    if clone.substrate != "comment":
        return []
    if _resolve(issue, clone.login, clone).substrate != "comment":
        return []
    residual = ownership.resolve_owner(
        comments=[], labels=_labels(issue), assignee_login=None, selector="label"
    ).owners
    out = []
    for instance in sorted(residual):
        proc = gh(ownership.instance_label_args(issue_number=n, instance=instance, remove=True))
        if not _ok(proc):
            out.append(
                f"[warn] ownership: the residual label instance:{instance} on #{n} could not "
                f"be removed: {_said(proc)}"
            )
    return out


def _mirror(gh: Run, n: int, clone: Clone, issue: dict, account: str | None) -> list[str]:
    """In ``comment`` mode, regenerate the owner mirror in the issue body from
    the fold of ``account``'s markers, before the provenance footer, by full
    overwrite. Writes only when the body changes. The warnings, if the write
    failed: the mirror is derived, so a failed write loses nothing (ADR-041
    points 4 and 5)."""
    if clone.substrate != "comment":
        return []
    resolution = _resolve(issue, account, clone)
    seats = {j.instance: j.seat for j in resolution.judgements if j.seat}
    region = ownership.render_mirror_region(resolution, names=seats)
    current = str(issue.get("body") or "")
    # Above the footer, the region is overwritten where it stands and placed
    # once at the end where it is absent. The footer is stamped again after it.
    head = ownership.render_mirror_body(provenance.strip_footer(current), region)
    body = provenance.stamp(head, _versions(clone))
    if body == current:
        return []
    failure = _write_body(gh, n, body)
    if failure is None:
        return []
    return [
        f"[warn] ownership: the owner shown in #{n}'s description could not be updated: "
        f"{failure}. The comment log holds the owner."
    ]


def _versions(clone: Clone) -> provenance.Versions:
    """The versions in force, which an event comment's footer and the
    description's footer name (DEC-052, ADR-037)."""
    return provenance.read_versions(clone.capability_root)


def _write_body(gh: Run, n: int, body: str) -> str | None:
    """Write ``body`` back through a temporary file, as every body write does
    (``--body-file``); the failure, or None."""
    with tempfile.NamedTemporaryFile("w", suffix=".md", encoding="utf-8", delete=False) as f:
        f.write(body)
        path = f.name
    try:
        proc = gh(["gh", "issue", "edit", str(n), "--body-file", path])
    finally:
        with contextlib.suppress(OSError):
            Path(path).unlink()
    return None if _ok(proc) else _said(proc)


def _resolve(issue: dict, account: str | None, clone: Clone) -> ownership.OwnershipResolution:
    """The issue's owners, folded by the seam: the markers ``account`` wrote,
    or the labels, as the clone's substrate selects. In a project with a
    topology, each claim is judged against the seats' holders."""
    return ownership.resolve_owner(
        comments=_comments(issue),
        labels=_labels(issue),
        assignee_login=account,
        selector=clone.substrate,
        holders=clone.holders,
    )


def _read(gh: Run, n: int) -> dict | None:
    """One read of the issue, or None when it failed."""
    proc = gh(["gh", "issue", "view", str(n), "--json", VIEW_FIELDS])
    if not _ok(proc):
        return None
    try:
        data = json.loads(getattr(proc, "stdout", "") or "")
    except (TypeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _assignees(issue: dict) -> list[str]:
    return [
        str(a.get("login"))
        for a in issue.get("assignees") or []
        if isinstance(a, dict) and a.get("login")
    ]


def _labels(issue: dict) -> list[Any]:
    return list(issue.get("labels") or [])


def _comments(issue: dict) -> list[dict]:
    return [c for c in issue.get("comments") or [] if isinstance(c, dict)]


def _ok(proc: Any) -> bool:
    return getattr(proc, "returncode", 1) == 0


def _said(proc: Any) -> str:
    """What a failed ``gh`` call said, in one line."""
    said = str(getattr(proc, "stderr", "") or "").strip().splitlines()
    return said[-1] if said else f"gh exited {getattr(proc, 'returncode', '?')}"


def _runner(config: dict) -> Run:
    """Every ``gh`` call of a claim, a release or the guard, through the gh
    helper (DEC-023)."""
    return lambda args: _gh(args, config)


def _gh(args: list[str], config: dict) -> Any:
    try:
        return ownership.gh_call(args, config)
    except FileNotFoundError:
        return _NoGh()


class _NoGh:
    """The result of a ``gh`` that is not on the PATH."""

    returncode = 127
    stdout = ""
    stderr = "`gh` is not on PATH"
