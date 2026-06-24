"""Shared label-reconciliation helper for project-management scripts.

Close-issue and move-issue both need to reconcile ``state:*`` labels after a
state change.  This module exports :func:`reconcile_state_labels_to_done` so
that ``close-issue`` can apply the same logic that ``move-issue`` uses without
duplicating the ``gh issue edit`` machinery.

The non-terminal state labels that a closing operation must remove are the
four states that precede ``done`` in the workflow state machine declared in
``workflow.yaml``: ``todo``, ``backlog``, ``in-progress``, ``review``.

``state:done`` is always added; the call is idempotent if the label is already
present (GitHub's ``gh issue edit --add-label`` is a no-op for a label the
issue already carries).

Map-awareness (ADR-026)
-----------------------
The ``state`` write resolves through the substrate-map seam (ADR-026
sole-constructor + fail-closed), exactly as ``move-issue._compute_plan`` does.
The state-label SET this helper acts on is therefore computed *per call from the
resolved write target*, never from import-time eager constants:

  * **No map (greenfield)** ⇒ ``state`` resolves to the kit's own
    ``state:done`` / ``state:<non-terminal>`` labels — byte-identical to the
    prior behaviour. The add-``state:done`` / remove-stale reconcile runs.
  * **Map present, ``state`` derive-bound / ``unsupported`` / absent** ⇒
    :func:`axis_labels.resolve_write` returns :data:`~_lib.axis_labels.DEGRADE`,
    so this helper writes (and removes) NO ``state:*`` label. The open/closed
    substrate carries terminal state under a derive binding; the kit manages no
    state label at all (ADR-026 §5). The issue close itself still happens — only
    the kit label write degrades, mirroring ``move-issue``'s empty-plan-on-DEGRADE.

Building the write target eagerly at import (the prior
``TERMINAL_STATE_LABEL = axis_labels.label("state","done")``) was map-blind: it
always produced the kit's own label, so a present-map adopter got ``state:done``
written on close. Resolving per call with the loaded map fixes that.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from _lib import axis_labels

if TYPE_CHECKING:
    from _lib.gh import gh_run as _gh_run_type  # pragma: no cover

# The four methodology state values a terminal close must clear, plus the
# terminal value itself.  These are the kit's own (greenfield) values on the
# `state` axis; they are resolved to concrete write/match targets PER CALL
# through the seam (see `_resolve_state_labels`), never string-formatted into
# labels at import — that would be the map-blind greenfield-identity constructor.
NON_TERMINAL_STATE_VALUES: tuple[str, ...] = ("todo", "backlog", "in-progress", "review")
TERMINAL_STATE_VALUE = "done"


def _resolve_state_labels(
    substrate_map: "axis_labels.SubstrateMap | None",
) -> tuple[str | None, tuple[str, ...]]:
    """Resolve the terminal + non-terminal ``state`` labels for this substrate.

    Returns ``(terminal_label, non_terminal_labels)``:

    * **Greenfield / a present map that resolves ``state`` to labels** ⇒
      ``terminal_label`` is the resolved ``done`` write target (the kit's own
      ``state:done`` in greenfield) and ``non_terminal_labels`` are the resolved
      non-terminal labels to strip.
    * **DEGRADE** (derive-bound / unsupported / absent ``state``) ⇒
      ``(None, ())`` — touch no ``state:*`` label at all.

    The non-terminal set is resolved through the same seam so a present-map
    adopter's removal targets match their own substrate, never the kit's. If the
    terminal value degrades, the axis is not label-carried, so the non-terminal
    set degrades with it (empty) — there are no kit ``state:*`` labels to clear.
    """
    terminal = axis_labels.resolve_write("state", TERMINAL_STATE_VALUE, substrate_map)
    if not isinstance(terminal, str):
        return None, ()
    non_terminal: list[str] = []
    for value in NON_TERMINAL_STATE_VALUES:
        resolved = axis_labels.resolve_write("state", value, substrate_map)
        if isinstance(resolved, str):
            non_terminal.append(resolved)
    return terminal, tuple(non_terminal)


def reconcile_state_labels_to_done(
    issue_number: int,
    current_labels: list[str],
    config: dict,
    *,
    gh_run,
    substrate_map: "axis_labels.SubstrateMap | None" = None,
) -> bool:
    """Remove all non-terminal ``state:*`` labels and ensure ``state:done``.

    This is the shared reconcile routine reused by ``close-issue`` on the
    wont-do, pr-merge, and cascade-eligibility-close paths.  ``move-issue`` uses
    :func:`_compute_plan` + ``_gh_apply_state_label`` for the general case; this
    helper is the specialised terminal variant that handles *all* stale labels in
    one call.

    Parameters
    ----------
    issue_number:
        GitHub issue number to edit.
    current_labels:
        The label names currently on the issue (as returned by ``gh issue view
        --json labels``).  The function derives which non-terminal labels are
        present from this list.
    config:
        Adopter config dict (threaded to :func:`gh_run` for host/owner
        routing per DEC-023).
    gh_run:
        The ``gh_run`` callable from ``_lib.gh``.  Passed explicitly so this
        module stays importable without a circular dependency (both
        ``close-issue`` and this helper import from ``_lib.gh``; passing the
        function avoids a module-level import of ``_lib.gh`` here which would
        create an implicit dependency cycle on the ``sys.path`` insertion order
        used by the PEP 723 scripts).
    substrate_map:
        The adopter's parsed ``substrate-map.yaml`` (or ``None`` for greenfield,
        the default — so existing call sites that do not pass it keep the kit's
        own ``state:*`` behaviour).  When the map binds ``state`` to a ``derive``
        predicate (or marks it ``unsupported`` / omits it), the ``state`` write
        degrades and this helper touches NO ``state:*`` label (ADR-026 §5): the
        open/closed substrate carries terminal state, so the kit writes none.

    Returns
    -------
    bool
        ``True`` on success (or when no gh call was needed), ``False`` on gh
        failure.
    """
    terminal_label, non_terminal_labels = _resolve_state_labels(substrate_map)
    if terminal_label is None:
        # DEGRADE: state lives on the open/closed substrate, not a kit label.
        # The issue close happened upstream; touch no `state:*` label here.
        return True

    stale = [lbl for lbl in current_labels if lbl in non_terminal_labels]
    has_done = terminal_label in current_labels

    if not stale and has_done:
        # Already correctly labelled — nothing to do.
        return True

    cmd = ["gh", "issue", "edit", str(issue_number), "--add-label", terminal_label]
    for stale_label in stale:
        cmd.extend(["--remove-label", stale_label])

    try:
        proc = gh_run(cmd, config, check=False)
    except FileNotFoundError:
        print("error: `gh` not on PATH.", file=sys.stderr)
        return False

    if proc.returncode != 0:
        print(
            f"error: gh issue edit (label reconcile) failed (exit {proc.returncode}).\n"
            f"stderr: {proc.stderr.strip()}",
            file=sys.stderr,
        )
        return False

    return True
