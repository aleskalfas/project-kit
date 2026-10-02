"""Whether an issue's type may sit under its parent's — the containment graph
``schemas/issue-types.yaml`` declares, checked wherever a parent is written.

[project-management:DEC-005-linking-and-containment] fixes which type may sit
under which: each type's ``parent_issue_types`` lists the types it may sit
under, ``can_contain`` names the same edges from the parent's end, and the
schema's ``containment_invariants`` say in prose what the edges leave out (no
EPIC in an EPIC, no Feature in a Feature, no Umbrella in a Feature, no issue in
a Task). A filing or re-parent that breaks the graph is refused before anything
is written, at ``[validation-severity:hard-reject]``: no ``--bypass``, neither
verb exposes ``--force``, and no severity knob a ``hierarchy: advisory``
substrate-map could soften
([project-management:DEC-036-substrate-pluggable-adoption] D4).

Where it is checked:

- ``create-issue`` and ``set-field --parent`` refuse such a parent before they
  write a body, a native link or a label (:func:`check_parent` on
  :func:`read_parent`). ``create-issue`` without ``--parent`` holds the parent
  its body's first line asserts the same way (:func:`asserted_parent`).
- ``link-parent`` reports an issue whose first line names such a parent and
  does not link it (:func:`check_parent` on :func:`typed_parent`, from the
  parent's title and labels in the issue list it already holds).
- ``validate-issue`` reports an issue already filed under one — it is never
  rewritten — judging the parent the containment seam resolves for it
  (:func:`parent_findings`), at :func:`existing_violation_severity`.

**One typing.** Every one of them tells an issue's type — the child's and the
parent's, a writer's and the validator's — through :func:`issue_type`, which
takes the substrate map as a required argument: under a map a type is told only
through the map's ``type`` title-prefix binding, and the kit's own prefixes are
never read on a mapped tracker (ADR-026 point 2), so a writer and the validator
cannot judge the same pair in two vocabularies. In greenfield the kit's
prefixes, the kind-driven Task prefixes (``[Bug]``, ``[Docs]``, …) and, for a
title carrying none, the ``type:*`` label tell it.

**Outside the graph.** An issue whose type cannot be told — child or parent —
is not refused: a writer warns once that nothing was checked, the validator
reports nothing, and a legacy tree stays linkable. Two other parents cannot be
checked, and are told apart from it:

- a parent that **cannot be read** — nothing can be checked, so a writer
  refuses, and ``validate-issue`` reports that it could not check;
- a number that **names no issue here** — a pull request, or an issue
  transferred elsewhere — is no parent, so a writer refuses it, and
  ``validate-issue`` reports that it could not check.

A type whose first-line forms name no issue — an EPIC, whose container is a
milestone — takes no issue parent (:func:`takes_an_issue_parent`), so
``create-issue`` refuses its ``--parent``.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from _lib import body_parent_ref, containment
from _lib.placeholder_detection import PHASE_TRANSITION
from _lib.structural_type import infer_structural_type

SEVERITY_HARD_REJECT = "hard-reject"
SEVERITY_WARNING = "warning"

# The findings `parent_findings` reports, in the `body.parent-ref` family
# validate-issue reports the first line's form under.
LABEL_VIOLATION = "body.parent-ref.containment"
LABEL_UNCHECKED = "body.parent-ref.containment-unchecked"

# How a refusal names the record that fixes the graph.
_GRAPH = "the containment graph in issue-types.yaml (DEC-005)"

# What an untyped issue is, said after a warning that nothing was checked.
_OUTSIDE = "an issue whose type cannot be told is outside the containment graph"


class Verdict(Enum):
    """What :func:`check_parent` says of one parent.

    ALLOWED       — the child's type may sit under the parent's.
    REFUSED       — it may not.
    UNTYPED       — the child's type or the parent's cannot be told, so nothing
                    was checked.
    UNREAD        — the parent could not be read, so nothing could be checked.
    NOT_AN_ISSUE  — the number names no issue here (a pull request, or an issue
                    transferred elsewhere), so it is no parent.
    """

    ALLOWED = "allowed"
    REFUSED = "refused"
    UNTYPED = "untyped"
    UNREAD = "unread"
    NOT_AN_ISSUE = "not-an-issue"


@dataclass(frozen=True)
class ParentRead:
    """What one read of a parent says of its type.

    ``structural_type`` is ``None`` for an untyped parent, and for one that
    could not be read, which ``unread`` then says why; ``not_an_issue`` says the
    read found no issue numbered so here (``containment.UnreadIssue``).
    """

    number: int
    structural_type: str | None = None
    unread: str | None = None
    not_an_issue: bool = False


@dataclass(frozen=True)
class ParentCheck:
    """A parent held to the containment graph (:func:`check_parent`).

    ``message`` says why a parent is refused, unread, no issue or not checked,
    in a sentence a caller prints after its own prefix; ``None`` where it is
    allowed.
    """

    verdict: Verdict
    message: str | None = None

    @property
    def refuses(self) -> bool:
        """Whether a writer stops here: the parent is refused, unread, or no
        issue."""
        return self.verdict in (Verdict.REFUSED, Verdict.UNREAD, Verdict.NOT_AN_ISSUE)


def issue_type(
    title: str,
    issue_types: dict,
    *,
    classification: dict | None,
    substrate_map: Any | None,
    labels: Iterable[Any] | None = None,
) -> str | None:
    """An issue's structural type, as the containment graph tells it — the one
    typing, for the child and the parent alike, in every verb that checks.

    ``substrate_map`` is required, ``None`` for greenfield: a caller that does
    not pass it is a ``TypeError``, never a silent greenfield read of a mapped
    tracker. Under a map the type is told only through the map's ``type``
    title-prefix binding (``structural_type.infer_structural_type``'s first
    arm): a map that binds ``type`` any other way, or not at all, tells no type,
    and neither the kit's prefixes nor ``labels`` are consulted (ADR-026 point
    2). In greenfield the kit's prefixes tell it, then the kind-driven Task
    prefixes ``classification`` declares, then — for a title carrying none —
    the ``type:*`` label among ``labels`` (names, or the ``{"name": …}`` objects
    the tracker returns), which only ever tells a Task.
    """
    names = _label_names(labels) if substrate_map is None else None
    return infer_structural_type(
        title,
        issue_types,
        classification=classification,
        labels=names,
        substrate_map=substrate_map,
    )


def takes_an_issue_parent(issue_types: dict, child_type: str) -> bool:
    """Whether a writer's parent number names an issue for a child of this type:
    its ``parent_ref_form`` offers a form naming one. False for an EPIC, whose
    container is a milestone."""
    return body_parent_ref.form_names_an_issue(_form(issue_types, child_type))


def typed_parent(
    number: int,
    title: str,
    issue_types: dict,
    *,
    classification: dict | None,
    substrate_map: Any | None,
    labels: Iterable[Any] | None = None,
) -> ParentRead:
    """The parent ``number`` whose title (and labels) are in hand, typed by
    :func:`issue_type`."""
    parent_type = issue_type(
        title,
        issue_types,
        classification=classification,
        substrate_map=substrate_map,
        labels=labels,
    )
    return ParentRead(number, parent_type)


def read_parent(
    number: int,
    config: dict[str, Any],
    issue_types: dict,
    *,
    classification: dict | None,
    substrate_map: Any | None,
) -> ParentRead:
    """Read parent ``number``'s record through the containment seam
    (``containment.read_issue_record``, one read) and type it
    (:func:`typed_parent`), its labels with it. Quiet: a read that fails is
    returned as unread, with why, and a number that names a pull request or a
    transferred issue as no issue, for the caller to say."""
    record = containment.read_issue_record(config, issue_number=number)
    if isinstance(record, containment.UnreadIssue):
        return ParentRead(number, unread=record.detail, not_an_issue=record.not_an_issue)
    return typed_parent(
        number,
        str(record.issue.get("title") or ""),
        issue_types,
        classification=classification,
        substrate_map=substrate_map,
        labels=record.issue.get("labels"),
    )


def check_parent(issue_types: dict, child_type: str | None, parent: ParentRead) -> ParentCheck:
    """Hold ``parent`` to the graph for a child of ``child_type`` (``None``: a
    child whose type cannot be told).

    A number that names no issue, and a parent that could not be read, are
    said first: neither is known to be an issue at all. Then a child or a parent
    whose type cannot be told is outside the graph. Otherwise the parent is
    refused where its type is not in the child type's ``parent_issue_types``,
    the message naming both types and the first-line forms the child's type
    allows.
    """
    n = parent.number
    child = _a(child_type) if child_type is not None else "this issue"
    if parent.not_an_issue:
        return ParentCheck(
            Verdict.NOT_AN_ISSUE,
            f"#{n} is not an issue in this repository — {parent.unread} — so {child} "
            "cannot sit under it",
        )
    if parent.unread is not None:
        return ParentCheck(
            Verdict.UNREAD,
            f"#{n} could not be read ({parent.unread}), so whether {child} may sit "
            "under it cannot be checked",
        )
    if child_type is None:
        return ParentCheck(
            Verdict.UNTYPED,
            f"this issue's type cannot be told, so whether it may sit under #{n} was not "
            f"checked ({_OUTSIDE})",
        )
    if parent.structural_type is None:
        return ParentCheck(
            Verdict.UNTYPED,
            f"#{n}'s type cannot be told, so whether {child} may sit under it was not "
            f"checked ({_OUTSIDE})",
        )
    if parent.structural_type in _parent_types(issue_types, child_type):
        return ParentCheck(Verdict.ALLOWED)
    return ParentCheck(
        Verdict.REFUSED,
        f"{child} may not sit under #{n}, which is {_a(parent.structural_type)}: "
        f"{child}'s parent is one of `{_form(issue_types, child_type).strip()}` — "
        f"{_GRAPH}. Choose a parent of one of those types, or change the issue's type",
    )


def asserted_parent(body: str, child_type: str | None, issue_types: dict) -> int | None:
    """The parent a body's first line asserts, for a check of the graph to hold
    — or ``None``.

    The check is a refusal, so a first line asserts a parent only under an
    issue type's own label (``body_parent_ref.type_labels``: ``EPIC``,
    ``Feature``, ``Umbrella``, ``Task``, matched exactly), in a form
    ``child_type`` allows or not — so ``Feature: #9`` on a Feature asserts #9,
    while ``Related: #45`` or ``Supersedes: #120`` asserts nothing, though every
    reader of the parent (the close gate among them) still takes the issue it
    names. A milestone line names no issue.
    """
    line = body_parent_ref.read_first_line(body, child_type, issue_types)
    if line.issue is None or line.label not in body_parent_ref.type_labels(issue_types):
        return None
    return line.issue


def existing_violation_severity(phase: str) -> str:
    """The severity ``validate-issue`` reports an issue already under a parent
    its type may not sit under at — the one place it is decided.

    No record states it: [project-management:DEC-005-linking-and-containment]
    refuses a filing or re-parent, and says nothing of one already made. Built
    as recommended for the maintainer to confirm: the same split as the two
    precedents in ``validate-issue`` (the kind/structural mismatch; the title
    wording rules) — a hard-reject at ``--phase create``, where the violation is
    being manufactured, and a warning at ``--phase transition``, so a move is
    not walled by a containment made before the refusal existed. Any phase but
    ``transition`` keeps the hard-reject, as those precedents do.
    """
    return SEVERITY_WARNING if phase == PHASE_TRANSITION else SEVERITY_HARD_REJECT


def parent_findings(
    resolution: containment.ParentResolution,
    child_type: str | None,
    issue_types: dict,
    *,
    phase: str,
    read: Callable[[int], ParentRead],
) -> list[tuple[str, str, str]]:
    """``(severity, label, detail)`` findings for an existing issue's parent,
    held to the graph — reported, never rewritten.

    The parent judged is the one the containment seam resolves
    (``containment.resolve_parent``): the native parent wherever one was read —
    alone, where the first line names another, since a stale line is the
    seam's to settle, not a containment violation — else the parent the first
    line asserts (:func:`asserted_parent`'s rule: an issue type's own label),
    which is also the one judged where the issue's record could not be read. A
    native parent in another repository cannot be typed from here, and is
    reported as not checked.

    ``read`` is asked for the parent's type once, only where there is a parent
    to judge and the child's type can be told — an issue whose type cannot be
    told is outside the graph and draws nothing. A refused parent is reported at
    :func:`existing_violation_severity`; one that could not be read, or that is
    no issue, at warning as not checked, never as a violation; an untyped one
    draws nothing.
    """
    if child_type is None:
        return []
    native = resolution.native
    issue = resolution.issue
    if native is not None and native.repository is not None:
        return [
            (
                SEVERITY_WARNING,
                LABEL_UNCHECKED,
                f"#{issue}'s native parent is {native.ref}, in another repository, so "
                f"whether {_a(child_type)} may sit under it was not checked.",
            )
        ]
    if native is not None:
        number = native.number
        said = f"#{issue}'s native parent is #{number}"
    else:
        named = resolution.line.issue
        if named is None or resolution.line.label not in body_parent_ref.type_labels(issue_types):
            return []
        number = named
        said = f"the first line names #{number} as the parent"
        if resolution.unread is not None:
            said += f" (#{issue}'s record could not be read, so its native parent is not known)"
    check = check_parent(issue_types, child_type, read(number))
    if check.verdict is Verdict.REFUSED:
        severity = existing_violation_severity(phase)
        return [(severity, LABEL_VIOLATION, f"{said}, and {check.message}.")]
    if check.verdict in (Verdict.UNREAD, Verdict.NOT_AN_ISSUE):
        return [(SEVERITY_WARNING, LABEL_UNCHECKED, f"{said}, but {check.message}.")]
    return []


def _label_names(labels: Iterable[Any] | None) -> list[str] | None:
    """Label names from names or ``{"name": …}`` objects, ``None`` for none."""
    if labels is None:
        return None
    names = [str(lbl.get("name", "")) if isinstance(lbl, dict) else str(lbl) for lbl in labels]
    return [name for name in names if name]


def _parent_types(issue_types: dict, child_type: str) -> list[str]:
    """The types ``issue_types`` lets ``child_type`` sit under."""
    entry = _entry(issue_types, child_type)
    parents = entry.get("parent_issue_types") if entry else None
    return [str(p) for p in parents] if isinstance(parents, list) else []


def _form(issue_types: dict, child_type: str) -> str:
    entry = _entry(issue_types, child_type)
    form = entry.get("parent_ref_form") if entry else None
    return str(form) if isinstance(form, str) else ""


def _entry(issue_types: dict, structural_type: str) -> dict | None:
    types = issue_types.get("types") if isinstance(issue_types, dict) else None
    entry = types.get(structural_type) if isinstance(types, dict) else None
    return entry if isinstance(entry, dict) else None


def _a(noun: str) -> str:
    """``noun`` with its indefinite article: a task, an epic, an umbrella."""
    return f"{'an' if noun[:1].lower() in 'aeiou' else 'a'} {noun}"
