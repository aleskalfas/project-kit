"""The sole constructor of non-label substrate writes (ADR-031).

A *non-label substrate* is one of the two issue attributes the capability
writes that are **not** an axis-label: a Projects-v2 single-select/text **field
value** (written with ``gh project item-edit``) and a **milestone assignment**
(written with ``gh issue edit --milestone`` post-hoc, or ``gh issue create
--milestone`` at create time). Those writes used to be string-built inline at
four scattered sites — DEC-024's ``set-board-field`` and ``assign-milestone``
hook handlers, ``create-issue``'s own milestone write, and (named OUT) the
board-membership write. This module pulls every covered construction behind one
seam.

Why a seam, per
[ADR-031](../../../../docs/architecture/decisions/ADR-031-substrate-write-path-contract.md):
this is the non-label, write-side twin of ADR-026's label sole-constructor.
Each covered substrate has **exactly one construction point** — a mutating
script obtains the write *only by asking this module*, never by string-building
the ``gh project item-edit`` / ``gh issue …--milestone`` argv itself. That makes
"no script string-builds these substrate writes inline" a structural property
enforced by the grep/AST guard (`tests/test_pm_substrate_write_seam.py`,
ADR-031's part-(b) sole-constructor test), the direct analogue of ADR-026's
``_lib/axis_labels`` seam and its guard.

Board-membership is OUT (ADR-031 point 3)
-----------------------------------------
``_gh_add_to_board``'s ``gh project item-add`` (board *membership*, DEC-019) is a
distinct operation — it establishes that an item is *on* the board; it does NOT
write an attribute *value* onto an existing item. It is **named out** of this
contract: the two covered substrates are field-value and milestone (the
attribute writes). The guard keys on the *operation* (``item-edit`` field-value;
``issue …--milestone``), not the ``gh project`` prefix, so ``item-add`` is left
alone.

Failure-posture neutrality (ADR-031 point 6)
--------------------------------------------
This module is **failure-posture-neutral**. Each constructor builds the ``gh``
argv; the executing functions run it and return a :class:`SubstrateWriteResult`
carrying enough detail (success / failure reason / the constructed argv) for the
*caller* to apply its own posture. The primitive imposes **no** skip / rollback
/ exit-code policy:

  * the per-event DEC-024 hooks keep **report-and-continue** — they read the
    result and raise their own ``HookFailure`` (or return ``ok``) per DEC-024;
  * the one-time bulk back-fill (T2, not built here) will impose the stricter
    audited posture of DEC-037 (re-validate at apply, skip-and-report on drift,
    value-equality idempotency) by wrapping the same constructors.

Construct vs. execute, and the at-create split
----------------------------------------------
Construction (building the argv) is separated from execution (running it) so
that:

  * a caller that does its own dry-run / reporting can construct the argv
    without running it (the construction test asserts the argv shape directly);
  * the milestone-at-create site can splice the ``--milestone`` argv fragment
    into its *own* ``gh issue create`` call (which also carries title / body /
    labels / assignee — concerns this module has no business owning) rather than
    delegating the whole create. The fragment is still *constructed here*, so the
    ``--milestone`` argv originates in the sole constructor; ``create-issue`` only
    chooses *when* it fires and assembles it into its create argv. ADR-031 point
    1: milestone spans two ``gh`` verbs but is one substrate with one
    construction point.

This module is deliberately content-free about *whether* a field/milestone write
should happen (idempotency, drift, defaults) — that is the caller's call. It owns
the ``gh`` argv construction and execution; nothing more.

The field-value substrate spans BOTH the ``gh project item-edit`` form and the
``gh api graphql … updateProjectV2ItemFieldValue`` GraphQL mutation form — they
write the same Projects-v2 field-value substrate by two routes. Both route
through this seam (the guard flags either form constructed inline), so the
sole-constructor invariant covers a field-value write however it is spelled.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Any

# Sibling module — the gh shell-out helper that pins the adopter's host/owner
# (DEC-023). Imported the same way `_lib.hooks` does, with a defensive fallback
# for unusual import contexts (tests that load a module by file path may not have
# _lib on sys.path).
try:
    from gh import gh_run  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    try:
        from _lib.gh import gh_run  # type: ignore[no-redef]
    except ImportError:  # pragma: no cover
        gh_run = None  # type: ignore[assignment]


@dataclass(frozen=True)
class SubstrateWriteResult:
    """Outcome of one non-label substrate write — the neutral carrier.

    Failure-posture-neutral (ADR-031 point 6): this records *what happened*; it
    takes no view on what the caller should do about it. Each driver reads these
    fields and applies its own posture — the per-event hook raises / continues
    per DEC-024, the bulk back-fill (T2) skips-and-reports per DEC-037.

    Drift and value-equality idempotency are NOT carried here. Whether a write
    *should* happen at all (the issue already carries the target value; the
    board state has drifted from the intended value) is the **bulk driver's
    (T2)** responsibility, decided by a state-read before it asks this primitive
    to write (and, for the per-event hooks, by the caller's own pre-write
    idempotency check). This type is content-free about *whether* a write should
    happen — it records only the outcome of one write that was already decided
    upon. T2 must not expect a ``drifted`` / ``skipped_idempotent`` field here,
    and must not reach back to widen this type to add one; the read-side decision
    lives in the driver.

    Fields:

      ok       — True when the write executed and ``gh`` returned success.
                 False on a non-zero ``gh`` exit, a missing ``gh`` binary, or any
                 execution error. It is NEVER an exception — the primitive does
                 not raise on a failed write; it returns ``ok=False`` and the
                 caller decides.
      executed — True when the ``gh`` write actually ran. False when the caller
                 only constructed the argv (no execution) — present so a future
                 ``--emit-script`` / dry-run driver can distinguish "built but not
                 run" from "ran and succeeded".
      argv     — the exact ``gh`` argv the primitive constructed, as an immutable
                 tuple. Carried so the construction test can assert the shape, and
                 so a later ``--emit-script`` back-fill driver can render the
                 reviewed mutation as a script the adopter runs themselves
                 (DEC-037's draft-not-apply) without re-deriving it. A tuple (not
                 a list) so a caller / the ``--emit-script`` renderer cannot mutate
                 state the result shares with whatever ran the write.
      detail   — a one-line human-readable summary (for hook reporting).
      error    — populated only when ``ok`` is False: the ``gh`` stderr (or the
                 reason the write could not run). ``None`` on success.
    """

    ok: bool
    executed: bool
    argv: tuple[str, ...] = ()
    detail: str = ""
    error: str | None = None


# ----- field-value write (gh project item-edit) --------------------------


def field_value_args(
    *,
    item_id: str,
    field_id: str,
    project_id: str,
    single_select_option_id: str | None = None,
    text_value: str | None = None,
) -> list[str]:
    """Construct the ``gh project item-edit`` field-value write argv.

    The sole constructor of the Projects-v2 single-select/text field-value write
    (ADR-031 point 1). Callers obtain this argv only here; they never string-build
    ``gh project item-edit … --field-id`` themselves.

    Exactly one of ``single_select_option_id`` / ``text_value`` selects the
    field's value form (single-select option vs. free text). The caller validates
    which one applies for its field kind and that the required ids are present;
    this constructor maps the resolved inputs onto the argv. ``ValueError`` if
    neither value form is supplied — a field-value write with no value is
    incoherent, and failing here (rather than emitting a valueless ``item-edit``)
    keeps the constructor from building a write that cannot mean anything.

    Note this is the field-value (``item-edit``) write, distinct from
    board-*membership* (``item-add``, ``_gh_add_to_board``), which is named OUT of
    the contract (ADR-031 point 3) and constructed at its own site.
    """
    args = [
        "gh", "project", "item-edit",
        "--id", item_id,
        "--field-id", field_id,
        "--project-id", project_id,
    ]
    if single_select_option_id:
        args += ["--single-select-option-id", str(single_select_option_id)]
    elif text_value:
        args += ["--text", str(text_value)]
    else:
        raise ValueError(
            "field-value write requires single_select_option_id or text_value"
        )
    return args


def write_field_value(
    config: dict[str, Any],
    *,
    item_id: str,
    field_id: str,
    project_id: str,
    single_select_option_id: str | None = None,
    text_value: str | None = None,
) -> SubstrateWriteResult:
    """Construct AND execute the Projects-v2 field-value write; return the result.

    Builds the argv via :func:`field_value_args`, runs it through the gh helper
    (adopter host/owner pinned per DEC-023), and returns a neutral
    :class:`SubstrateWriteResult`. Never raises on a failed write — a non-zero
    ``gh`` exit (or missing binary) yields ``ok=False`` with the stderr in
    ``error``, for the caller to handle per its own posture.
    """
    args = field_value_args(
        item_id=item_id,
        field_id=field_id,
        project_id=project_id,
        single_select_option_id=single_select_option_id,
        text_value=text_value,
    )
    return _execute(
        args,
        config,
        ok_detail=f"set field_id={field_id} on item_id={item_id}",
        fail_prefix="gh project item-edit failed",
    )


# ----- milestone write (gh issue edit / gh issue create --milestone) ------


def milestone_edit_args(*, issue_number: int | str, title: str) -> list[str]:
    """Construct the post-hoc ``gh issue edit <n> --milestone <title>`` argv.

    The sole constructor of the milestone write in its **post-hoc** form (ADR-031
    point 1) — assigning a milestone to an issue that already exists (DEC-024's
    ``assign-milestone`` handler, and the bulk back-fill in T2). The at-create
    form is :func:`milestone_create_args`; both are the *same substrate*
    (milestone) and route through this one module.
    """
    return ["gh", "issue", "edit", str(issue_number), "--milestone", title]


def milestone_create_args(title: str) -> list[str]:
    """Construct the ``--milestone <title>`` argv fragment for ``gh issue create``.

    The sole constructor of the milestone write in its **at-create** form (ADR-031
    point 1, the fourth site). It returns only the ``["--milestone", title]``
    fragment — NOT a whole ``gh issue create`` argv — because the create call also
    carries title / body / labels / assignee, concerns this module does not own.
    ``create-issue`` splices this fragment into its own create argv, so the
    ``--milestone`` argv still *originates in the sole constructor* (the guard's
    requirement) while ``create-issue`` owns assembling and executing the create.

    There is no ``write_milestone_create`` executing counterpart: at create time
    the milestone is set by the create call itself, which ``create-issue`` runs.
    This module supplies the fragment; the caller runs the create.
    """
    return ["--milestone", title]


def write_milestone(
    config: dict[str, Any],
    *,
    issue_number: int | str,
    title: str,
) -> SubstrateWriteResult:
    """Construct AND execute the post-hoc milestone write; return the result.

    Builds the argv via :func:`milestone_edit_args`, runs it through the gh helper
    (DEC-023), and returns a neutral :class:`SubstrateWriteResult`. Never raises on
    a failed write — a non-zero ``gh`` exit yields ``ok=False`` with the stderr in
    ``error``, for the caller's posture to act on.
    """
    args = milestone_edit_args(issue_number=issue_number, title=title)
    return _execute(
        args,
        config,
        ok_detail=f"set milestone={title!r} on #{issue_number}",
        fail_prefix="gh issue edit --milestone failed",
    )


# ----- execution (shared) ------------------------------------------------


def _execute(
    args: list[str],
    config: dict[str, Any],
    *,
    ok_detail: str,
    fail_prefix: str,
) -> SubstrateWriteResult:
    """Run ``args`` through the gh helper and wrap the outcome in a neutral result.

    The one place a covered substrate write is executed. Failure-posture-neutral:
    it reports the outcome and never raises on a non-zero exit or a missing
    binary; the caller decides what a failure means.
    """
    argv = tuple(args)
    try:
        proc = _gh_call(args, config)
    except FileNotFoundError:
        return SubstrateWriteResult(
            ok=False,
            executed=False,
            argv=argv,
            detail=f"{fail_prefix}: `gh` not on PATH",
            error="`gh` not on PATH",
        )
    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip() or "no stderr"
        return SubstrateWriteResult(
            ok=False,
            executed=True,
            argv=argv,
            detail=f"{fail_prefix}: {stderr}",
            error=stderr,
        )
    return SubstrateWriteResult(
        ok=True,
        executed=True,
        argv=argv,
        detail=ok_detail,
    )


def _gh_call(args: list[str], config: dict[str, Any]) -> subprocess.CompletedProcess:
    """Call ``gh`` through the helper. Direct subprocess fallback if helper missing.

    Mirrors ``_lib.hooks._gh_call`` so the two converged hook handlers keep the
    exact execution path they had before routing through this primitive.
    """
    if gh_run is not None:
        return gh_run(args, config, check=False)
    return subprocess.run(args, capture_output=True, text=True, check=False)
