"""Whether an issue's type may sit under its parent's — the containment graph
``schemas/issue-types.yaml`` declares, checked wherever a parent is written.

[project-management:DEC-005-linking-and-containment] fixes which type may sit
under which: each type's ``parent_issue_types`` lists the types it may sit
under, ``can_contain`` names the same edges from the parent's end, and the
schema's ``containment_invariants`` say in prose what the edges leave out (no
EPIC in an EPIC, no Feature in a Feature, no Umbrella in a Feature, no issue in
a Task). A filing or re-parent that breaks the graph is refused before anything
is written, at ``[validation-severity:hard-reject]``: no ``--bypass``, and no
severity knob a ``hierarchy: advisory`` substrate-map could soften
([project-management:DEC-036-substrate-pluggable-adoption] D4).

Where it is checked:

- ``create-issue`` and ``set-field --parent`` refuse such a parent before they
  write a body, a native link or a label (:func:`check_parent`).
- ``link-parent`` reports an issue whose first line names such a parent and
  does not link it (:func:`check_parent` on :func:`typed_parent`, from the
  parent's title in the issue list it already holds).
- ``validate-issue`` reports an issue already filed under one — it is never
  rewritten — and ``edit-issue`` checks a body it writes the same way
  (:func:`first_line_findings`).

A parent's type is read from its title (:func:`read_parent`), with the
vocabulary the verb reads an issue's own type with. Two parents cannot be
checked, and are told apart:

- a parent that **cannot be read** — nothing can be checked, so a writer
  refuses, and ``validate-issue`` reports that it could not check;
- a parent whose title carries **no type** the vocabulary recognises — an
  untyped issue is outside the graph, so it is accepted with a warning that
  nothing was checked, and a legacy tree stays linkable.

A type whose first-line forms name no issue — an EPIC, whose container is a
milestone — takes no issue parent from a writer (:func:`takes_an_issue_parent`):
the number a writer is given for it is a milestone's, so nothing is read or
checked for it.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from _lib import body_parent_ref
from _lib.gh import gh_run
from _lib.structural_type import infer_structural_type

SEVERITY_HARD_REJECT = "hard-reject"
SEVERITY_WARNING = "warning"

# The findings `first_line_findings` reports, in the `body.parent-ref` family
# validate-issue and edit-issue report the first line's form under — so
# edit-issue's per-field scoping treats them as body findings.
LABEL_VIOLATION = "body.parent-ref.containment"
LABEL_UNCHECKED = "body.parent-ref.containment-unchecked"

# How long one read of a parent may take. A writer and a validator alike make at
# most one such read per call; past this the parent is reported unread.
READ_TIMEOUT_SECONDS = 30

# How a refusal names the record that fixes the graph.
_GRAPH = "the containment graph in issue-types.yaml (DEC-005)"


class Verdict(Enum):
    """What :func:`check_parent` says of one parent.

    ALLOWED  — the child's type may sit under the parent's.
    REFUSED  — it may not.
    UNTYPED  — the parent's type cannot be told, so nothing was checked.
    UNREAD   — the parent could not be read, so nothing could be checked.
    """

    ALLOWED = "allowed"
    REFUSED = "refused"
    UNTYPED = "untyped"
    UNREAD = "unread"


@dataclass(frozen=True)
class ParentRead:
    """What one read of a parent says of its type.

    ``structural_type`` is ``None`` for an untyped parent, and for one that
    could not be read, which ``unread`` then says why.
    """

    number: int
    structural_type: str | None = None
    unread: str | None = None


@dataclass(frozen=True)
class ParentCheck:
    """A parent held to the containment graph (:func:`check_parent`).

    ``message`` says why a parent is refused, unread or untyped, in a sentence a
    caller prints after its own prefix; ``None`` where it is allowed.
    """

    verdict: Verdict
    message: str | None = None

    @property
    def refuses(self) -> bool:
        """Whether a writer stops here: the parent is refused, or unread."""
        return self.verdict in (Verdict.REFUSED, Verdict.UNREAD)


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
    classification: dict | None = None,
    substrate_map: Any | None = None,
) -> ParentRead:
    """The parent ``number`` whose title is in hand, typed from it."""
    parent_type = infer_structural_type(
        title, issue_types, classification=classification, substrate_map=substrate_map
    )
    return ParentRead(number, parent_type)


def read_parent(
    number: int,
    config: dict[str, Any],
    issue_types: dict,
    *,
    classification: dict | None = None,
    substrate_map: Any | None = None,
    timeout: float = READ_TIMEOUT_SECONDS,
) -> ParentRead:
    """Read parent ``number``'s title — one ``gh issue view``, bounded by
    ``timeout`` — and type it (:func:`typed_parent`). Quiet: a read that fails
    is returned as unread, with why, for the caller to say."""
    try:
        proc = gh_run(
            ["gh", "issue", "view", str(number), "--json", "title"],
            config,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return ParentRead(number, unread=f"gh did not answer within {timeout:g}s")
    except OSError:
        return ParentRead(number, unread="`gh` is not on PATH")
    if proc.returncode != 0:
        said = (proc.stderr or "").strip().splitlines()
        tail = f": {said[0]}" if said else ""
        return ParentRead(number, unread=f"gh exited {proc.returncode}{tail}")
    try:
        payload = json.loads(proc.stdout or "")
    except (json.JSONDecodeError, ValueError):
        return ParentRead(number, unread="gh's answer was not JSON")
    title = payload.get("title") if isinstance(payload, dict) else None
    if not isinstance(title, str):
        return ParentRead(number, unread="gh's answer carried no title")
    return typed_parent(
        number, title, issue_types, classification=classification, substrate_map=substrate_map
    )


def check_parent(issue_types: dict, child_type: str, parent: ParentRead) -> ParentCheck:
    """Hold ``parent`` to the graph for a child of ``child_type``.

    Refused where the parent's type is not in the child type's
    ``parent_issue_types``, the message naming both types and the first-line
    forms the child's type allows.
    """
    n, child = parent.number, child_type
    if parent.unread is not None:
        return ParentCheck(
            Verdict.UNREAD,
            f"#{n} could not be read ({parent.unread}), so whether {_a(child)} may sit "
            "under it cannot be checked",
        )
    if parent.structural_type is None:
        return ParentCheck(
            Verdict.UNTYPED,
            f"#{n}'s type cannot be told from its title, so whether {_a(child)} may sit "
            "under it was not checked (an untyped issue is outside the containment graph)",
        )
    if parent.structural_type in _parent_types(issue_types, child):
        return ParentCheck(Verdict.ALLOWED)
    return ParentCheck(
        Verdict.REFUSED,
        f"{_a(child)} may not sit under #{n}, which is {_a(parent.structural_type)}: "
        f"{_a(child)}'s parent is one of `{_form(issue_types, child).strip()}` — "
        f"{_GRAPH}. Choose a parent of one of those types, or change the issue's type",
    )


def first_line_findings(
    body: str,
    child_type: str,
    issue_types: dict,
    *,
    issue_number: int | None,
    read: Callable[[int], ParentRead],
) -> list[tuple[str, str, str]]:
    """``(severity, label, detail)`` findings for the parent a body's first line
    names, held to the graph — for an issue already filed, which is reported,
    never rewritten.

    ``read`` is asked for the parent only where the first line names one, in any
    form (``body_parent_ref.read_first_line``) — a milestone names none, and
    neither does a line naming the issue itself. A refused parent is a
    hard-reject; a parent that could not be read is a warning saying the check
    was not made, never a violation; an untyped parent is outside the graph and
    reports nothing.
    """
    named = body_parent_ref.read_first_line(body, child_type, issue_types).issue
    if named is None or named == issue_number:
        return []
    check = check_parent(issue_types, child_type, read(named))
    said = f"the first line names #{named} as the parent"
    if check.verdict is Verdict.REFUSED:
        return [(SEVERITY_HARD_REJECT, LABEL_VIOLATION, f"{said}, and {check.message}.")]
    if check.verdict is Verdict.UNREAD:
        return [(SEVERITY_WARNING, LABEL_UNCHECKED, f"{said}, but {check.message}.")]
    return []


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
