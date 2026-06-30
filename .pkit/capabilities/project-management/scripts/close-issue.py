#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — close-issue (verb-subject per DEC-020).

Closes a GitHub issue via either path declared in workflow.yaml's
`closure_triggers`:

  * `--mode=wont-do` (default when --reason supplied or when caller is
    explicit) — posts a closing comment with the reason, verifies the
    checkbox close-gate per DEC-007, then closes via `gh issue close`.
  * `--mode=pr-merge` — issue closure was triggered by GitHub's
    `Closes #N` keyword. The script runs the cascade pass on parents
    after the fact; it does not itself close the issue.
  * `--mode=cascade-eligibility-close` — closes a container (epic/feature/
    umbrella) once every child is closed AND its own checkboxes are ticked
    (the DEC-007 gate is non-skippable here). Implements the
    `cascade-eligibility-close` trigger this script previously only reported.
    Closes via `gh issue close --reason completed`.

All three paths reconcile the issue's ``state:*`` labels after closing: any
non-terminal label (``state:todo``, ``state:backlog``, ``state:in-progress``,
``state:review``) is removed and ``state:done`` is ensured.  The reconcile
logic is shared with ``move-issue`` via ``_lib.labels.reconcile_state_labels_to_done``
so there is no duplicated label-mutation code.

The ``state`` write is RESOLVED through the substrate-map seam (ADR-026
sole-constructor + fail-closed), the same as ``move-issue``: greenfield (no
``substrate-map.yaml``) writes the kit's own ``state:done``; a present map that
binds ``state`` to a ``derive`` predicate (or marks it ``unsupported`` / omits
it) writes NO kit ``state:*`` label — the open/closed substrate carries terminal
state, so closing the issue *is* the state write (ADR-026 §5). The map is loaded
once in :func:`main` and threaded into every reconcile call.

Membership gate per DEC-021 runs at startup.

Self-contained via PEP 723; runs via
  uv run --script .pkit/capabilities/project-management/scripts/close-issue.py 42 --reason "superseded by #99"

Or via the dispatcher (per COR-021):
  pkit project-management close-issue 42 --reason "..."

Exit codes:
  0  closed (or cascade reported)
  1  membership refusal / authorisation refusal / checkbox close-gate refusal
  2  usage error (issue not found; mode contradicts state)
  3  gh failure
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import axis_labels  # noqa: E402
from _lib import containment  # noqa: E402
from _lib.gh import gh_get_issue, gh_run, load_adopter_config  # noqa: E402
from _lib.hooks import fire_hooks  # noqa: E402
from _lib.labels import reconcile_state_labels_to_done  # noqa: E402
from _lib.membership import (  # noqa: E402
    CAPABILITY_NAME,
    check_membership,
    resolve_capability_root,
    resolve_invoker_identity,
)


VALID_MODES = ("wont-do", "pr-merge", "cascade-eligibility-close")
DEFAULT_MODE = "wont-do"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Close a GitHub issue per the methodology's closure rules. "
            "Default mode is wont-do (explicit gesture with reason + close-"
            "gate check); pr-merge mode is the post-close cascade hook."
        ),
    )
    parser.add_argument(
        "issue_number",
        type=int,
        help="GitHub issue number to close.",
    )
    parser.add_argument(
        "--mode",
        choices=VALID_MODES,
        default=DEFAULT_MODE,
        help=(
            f"Closure mode. Default: {DEFAULT_MODE}. "
            "`wont-do` posts a closing comment + closes; "
            "`pr-merge` is the cascade-only hook after GitHub-native close; "
            "`cascade-eligibility-close` closes a container (epic/feature/"
            "umbrella) once all children are closed and its own checkboxes "
            "are ticked (non-skippable gate)."
        ),
    )
    parser.add_argument(
        "--reason",
        default=None,
        help=(
            "Closing reason recorded in the closing comment. Required in "
            "wont-do mode."
        ),
    )
    parser.add_argument(
        "--skip-checkbox-gate",
        action="store_true",
        help=(
            "Skip the DEC-007 checkbox close-gate. Discouraged; only use "
            "when you have just removed all open boxes by hand."
        ),
    )
    parser.add_argument(
        "--no-cascade",
        action="store_true",
        help="Skip the closure-cascade walk on parent issues.",
    )
    parser.add_argument(
        "--capability-root",
        type=Path,
        default=None,
        help=(
            "Path to the installed capability's directory "
            f"(default: <repo-root>/.pkit/capabilities/{CAPABILITY_NAME}/)."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the plan; do not invoke gh.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the confirmation prompt.",
    )
    args = parser.parse_args()

    capability_root = resolve_capability_root(args.capability_root)
    if capability_root is None:
        print(
            f"error: {CAPABILITY_NAME} capability not found.",
            file=sys.stderr,
        )
        return 2

    yaml_loader = YAML(typ="safe")
    config = load_adopter_config(capability_root)
    members = _read_members(capability_root, yaml_loader)
    invoker = resolve_invoker_identity(config=config)
    membership = check_membership(members, invoker)
    if not membership.allowed:
        print(membership.refusal_message, file=sys.stderr)
        return 1

    issue_types = _read_yaml(
        capability_root / "schemas" / "issue-types.yaml", yaml_loader
    )

    # The adopter's optional substrate-map (ADR-026): None ⇒ greenfield (state
    # is a `state:*` label); a present map may bind `state` to a `derive`
    # predicate (or mark it unsupported / omit it) ⇒ the kit writes NO `state:*`
    # label on close (the open/closed substrate carries terminal state). Loaded
    # once here and threaded into every reconcile call below (RF-1, #265).
    substrate_map = axis_labels.load_substrate_map(capability_root)

    issue = _gh_get_issue(args.issue_number, config)
    if issue is None:
        return 2

    title = str(issue.get("title", ""))
    body = str(issue.get("body") or "")
    state = str(issue.get("state", "")).lower()
    labels = [
        lbl.get("name", "") if isinstance(lbl, dict) else str(lbl)
        for lbl in (issue.get("labels") or [])
    ]
    structural_type = _infer_structural_type(title, issue_types)

    print(f"close-issue: #{args.issue_number}")
    print(f"  title:        {title}")
    print(f"  type:         {structural_type or '<unrecognised prefix>'}")
    print(f"  current state: {state}")
    print(f"  mode:         {args.mode}")

    if args.mode == "wont-do":
        if state == "closed":
            print("\n[noop] issue already closed.")
            return 0
        if not args.reason:
            print(
                "\nerror: --reason is required in wont-do mode.",
                file=sys.stderr,
            )
            return 2

        # Checkbox close-gate per DEC-007.
        unticked = [] if args.skip_checkbox_gate else _unticked_boxes(body)
        if unticked:
            print("\n[refused] DEC-007 checkbox close-gate:")
            for line in unticked:
                print(f"  - {line}")
            print(
                "\n  → tick or remove each unticked checkbox before closing, "
                "or pass --skip-checkbox-gate (discouraged).",
                file=sys.stderr,
            )
            return 1

        print(f"\nreason: {args.reason}")
        if args.dry_run:
            print("\n[dry-run] gh would be invoked; nothing written.")
            return 0
        if not args.yes and sys.stdin.isatty():
            reply = input("Proceed? [y/N] ").strip().lower()
            if reply not in ("y", "yes"):
                print("aborted.", file=sys.stderr)
                return 0

        comment_body = (
            f"[wont-do close] {args.reason}\n\n"
            f"Closed via `pkit project-management close-issue` "
            f"(per [project-management:DEC-006-state-machine-and-cascade])."
        )
        if not _gh_comment(args.issue_number, comment_body, config):
            return 3
        if not _gh_close_issue(args.issue_number, reason="not planned", config=config):
            return 3
        # Reconcile state:* labels — remove any non-terminal label and ensure
        # state:done.  Shared routine from _lib.labels (same logic as
        # move-issue's reconcile path) so there is no duplicated label logic.
        # Map-aware (RF-1): under a present derive/unsupported `state` map this
        # writes no kit `state:*` label (the open/closed substrate carries it).
        if not reconcile_state_labels_to_done(
            args.issue_number, labels, config, gh_run=gh_run,
            substrate_map=substrate_map,
        ):
            return 3
        print(f"\n[ok] closed #{args.issue_number} (wont-do).")

    elif args.mode == "pr-merge":
        # In pr-merge mode the issue is expected to be already-closed
        # via GitHub's Closes #N. The script's job is the cascade pass
        # plus label reconciliation (GitHub's auto-close does not touch
        # state:* labels).
        if state != "closed":
            print(
                "\n[warn] pr-merge mode but issue is still open. "
                "GitHub's Closes #N should have closed it on PR merge. "
                "Re-check the merged PR's body for `Closes #N`.",
                file=sys.stderr,
            )
        # Reconcile state:* labels regardless of open/closed state warning
        # above — the caller explicitly indicated a PR-merge close, so the
        # terminal label must be correct.
        if not args.dry_run:
            if not reconcile_state_labels_to_done(
                args.issue_number, labels, config, gh_run=gh_run,
                substrate_map=substrate_map,
            ):
                return 3
        print(f"\n[ok] noted pr-merge close for #{args.issue_number}.")

    elif args.mode == "cascade-eligibility-close":
        # Close a container (epic/feature/umbrella) that is cascade-eligible per
        # DEC-006 + workflow.yaml closure_triggers[cascade-eligibility-close]:
        # EVERY child is closed AND the container's own checkboxes are ticked.
        # The checkbox gate is a DEC-007 hard-reject here and is NOT skippable
        # (unlike wont-do) — a container is "done" only when its work is
        # genuinely complete. Closes with reason=completed.
        if structural_type not in ("epic", "feature", "umbrella"):
            print(
                "\nerror: cascade-eligibility-close applies to container issues "
                "(epic/feature/umbrella); "
                f"#{args.issue_number} is "
                f"{structural_type or 'an unrecognised type'}. "
                "Use --mode=wont-do, or close a leaf via its PR (Closes #N).",
                file=sys.stderr,
            )
            return 2
        if state == "closed":
            print("\n[noop] issue already closed.")
            return 0

        # Eligibility half 1 — own checkboxes ticked (DEC-007, NOT skippable here).
        unticked = _unticked_boxes(body)
        if unticked:
            print("\n[refused] DEC-007 checkbox close-gate (cascade-eligibility):")
            for line in unticked:
                print(f"  - {line}")
            print(
                "\n  → a container closes only when its own checkboxes are all "
                "ticked. This gate is not skippable in cascade-eligibility-close.",
                file=sys.stderr,
            )
            return 1

        # Eligibility half 2 — every child closed (the CHILDREN-HALF of the
        # conjunction). DEC-034 / DEC-033 D5: the wrapper no longer folds this
        # itself — it reads the process ENGINE's shared cascade resolution
        # (`pkit process cascade`), which folds the issue-lifecycle `all`-over-
        # `done` declaration in workflow.yaml. The close rule stays the
        # CONJUNCTION of (half 1) the checkbox gate above AND (half 2) this fold.
        #
        #   opened == True   -> every child reached `done` (or childless via
        #                       on_empty: satisfied) -> children-half satisfied.
        #   opened == False, indeterminate == False
        #                    -> a determinate "not yet": an open child holds the
        #                       fold (matches "open child blocks eligibility",
        #                       DEC-016 roll-forward included) -> refuse.
        #   indeterminate == True
        #                    -> the fold could not be resolved (a reachable engine
        #                       that could not fold: broken members/membership read
        #                       or an unresolved member); HOLD fail-closed -> refuse
        #                       (never fail-open), per COR-037 precedence.
        #   fold is None     -> `pkit` itself was unreachable (could not even invoke
        #                       the engine); also HOLD fail-closed -> refuse.
        # Both indeterminate and None are fail-closed holds; they differ only in
        # exit code (1 = engine reachable but refused/held; 3 = engine unreachable),
        # so callers/CI can tell a policy refusal from an environment failure. Keep
        # the 3-vs-1 split: it is a deliberate two-failure-surface contract, not noise.
        fold = _engine_cascade_fold(args.issue_number)
        if fold is None or fold.get("indeterminate"):
            reason = fold.get("reason") if isinstance(fold, dict) else None
            print(
                "\n[refused] could not resolve the children-half of cascade "
                "eligibility (held fail-closed):",
                file=sys.stderr,
            )
            print(f"  → {reason or 'the process engine could not fold the children.'}",
                  file=sys.stderr)
            print(
                "  → re-run once `gh` is reachable and every child's state is "
                "readable; the container holds until the fold resolves.",
                file=sys.stderr,
            )
            return 3 if fold is None else 1
        if not fold.get("opened"):
            print("\n[refused] not cascade-eligible — not every child has closed:")
            print(f"  · fold: {fold.get('reason', '')}")
            # Diagnostic colour only (the engine fold above is the DECISION): list
            # the still-open children so the user knows what to close.
            open_children = _find_open_children(args.issue_number, config)
            for n in open_children or []:
                print(f"  - #{n}")
            print(
                "\n  → close every child first; the container becomes eligible "
                "when the last child closes.",
                file=sys.stderr,
            )
            return 1

        if args.dry_run:
            print(
                "\n[dry-run] eligible (all children closed, checkboxes ticked); "
                "gh would close with --reason completed."
            )
            return 0
        if not args.yes and sys.stdin.isatty():
            reply = input("Close cascade-eligible container? [y/N] ").strip().lower()
            if reply not in ("y", "yes"):
                print("aborted.", file=sys.stderr)
                return 0

        comment_body = (
            "[cascade-eligibility close] all children closed and the container's "
            "checkboxes are complete.\n\n"
            "Closed via `pkit project-management close-issue "
            "--mode=cascade-eligibility-close` "
            "(per [project-management:DEC-006-state-machine-and-cascade])."
        )
        if not _gh_comment(args.issue_number, comment_body, config):
            return 3
        if not _gh_close_issue(args.issue_number, reason="completed", config=config):
            return 3
        if not reconcile_state_labels_to_done(
            args.issue_number, labels, config, gh_run=gh_run,
            substrate_map=substrate_map,
        ):
            return 3
        print(
            f"\n[ok] closed #{args.issue_number} (cascade-eligibility, completed)."
        )

    # Closure cascade — semi-automatic per DEC-006.
    if not args.no_cascade:
        parent_nums = _walk_parent_chain(body)
        if parent_nums:
            print(
                f"\n[cascade] parents to check for eligibility: "
                f"{', '.join(f'#{n}' for n in parent_nums)}"
            )
            for pnum in parent_nums:
                _check_parent_eligibility(pnum, config)
        else:
            print("\n[cascade] no parent ref found in body; cascade skipped.")

    # Fire after_close_issue hooks per DEC-024.
    fire_hooks(
        "after_close_issue",
        context={
            "issue": {
                "number": args.issue_number,
                "title": str(issue.get("title", "")) if issue else "",
            },
        },
        config=config,
        capability_root=capability_root,
    )

    return 0


# ---- DEC-007 checkbox gate ------------------------------------------


def _unticked_boxes(body: str) -> list[str]:
    """Return the raw lines for unticked `- [ ]` checkboxes in the body."""
    out: list[str] = []
    for line in body.splitlines():
        # Match either `- [ ]` (markdown) or `* [ ]` style.
        if re.match(r"^\s*[-*]\s+\[\s\]\s+\S", line):
            out.append(line.strip())
    return out


def _all_boxes_ticked(body: str) -> bool:
    return not _unticked_boxes(body)


# ---- parent eligibility ---------------------------------------------


def _check_parent_eligibility(parent_num: int, config: dict) -> None:
    """Report whether a parent is eligible to close.

    Eligibility per DEC-006: every open child has closed, AND parent's
    own checkboxes are ticked. We surface the report; we do not auto-
    close (DEC-006 explicit: closure is never auto).
    """
    parent = _gh_get_issue(parent_num, config)
    if parent is None:
        print(f"  [warn] could not fetch parent #{parent_num}", file=sys.stderr)
        return
    state = str(parent.get("state", "")).lower()
    if state == "closed":
        print(f"  · parent #{parent_num} already closed")
        return
    body = str(parent.get("body") or "")
    unticked = _unticked_boxes(body)
    if unticked:
        print(
            f"  · parent #{parent_num} open; not eligible "
            f"({len(unticked)} unticked box(es))"
        )
        return
    print(
        f"  · parent #{parent_num} open; checkboxes complete — "
        "eligible to close pending sibling check"
    )


# ---- process-engine cascade delegation (DEC-034 / DEC-033 D5) -------
#
# The CHILDREN-HALF of close-eligibility is the shared process engine's
# cascade fold (`pkit process cascade`, COR-037), invoked by subprocess
# (never imported, ADR-020). The fold reads workflow.yaml's
# `process.cascade` (all-over-`done` over the parent's child issues). The
# wrapper keeps the OTHER half — the DEC-007 checkbox gate — local, and
# ANDs the two. close-issue does not recompute the fold itself.

PROCESS_ADDRESS = "project-management:issue-lifecycle"


def _engine_cascade_fold(parent_num: int) -> dict | None:
    """Read the parent's children-half cascade fold from the engine.

    Returns the fold dict `{opened, indeterminate, reached, total, reason, ...}`
    (the `process cascade --json` payload's `cascade` object), or None when the
    engine cannot be reached at all (a missing `pkit`, a crash) — the caller maps
    None to a fail-closed HOLD (never an auto-open). A reachable engine that
    cannot resolve the fold reports `indeterminate: true` (also a HOLD); a
    determinate fold reports `opened` true/false.
    """
    argv = [
        "pkit", "process", "cascade", PROCESS_ADDRESS,
        "--subject", str(parent_num), "--json",
    ]
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, check=False)
    except (OSError, FileNotFoundError):
        return None
    # The command exits non-zero when the fold is NOT open (by design); the JSON
    # on stdout is authoritative regardless of exit code, so parse it either way.
    try:
        payload = json.loads(proc.stdout)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    cascade = payload.get("cascade")
    return cascade if isinstance(cascade, dict) else None


def _find_open_children(parent_num: int, config: dict) -> list[int] | None:
    """Return the OPEN children of a container — diagnostic colour for the
    refused-cascade message only (the ENGINE fold is the decision).

    Children are resolved through the SAME containment read-seam
    (``_lib.containment.resolve_children``) the engine's ``cascade_members``
    predicate and ``show-tree`` use — native sub-issues where present, textual
    child-side parent-refs otherwise, native-wins (DEC-005). Routing this through
    the one seam is the ADR-026 point: no consumer re-derives containment by
    re-parsing body parent-refs. The seam returns ALL children; this helper
    filters to the still-OPEN ones for the "what to close first" hint.

    Empty list = all children closed (or none); None on gh failure.
    """
    proc = gh_run(
        [
            "gh", "issue", "list", "--state", "all", "--limit", "500",
            "--json", "number,state,body",
        ],
        config,
        check=False,
    )
    if proc.returncode != 0:
        print(
            f"error: gh issue list failed (exit {proc.returncode}).\n"
            f"stderr: {proc.stderr.strip()}",
            file=sys.stderr,
        )
        return None
    try:
        rows = json.loads(proc.stdout)
    except (ValueError, json.JSONDecodeError):
        print("error: gh issue list returned malformed JSON.", file=sys.stderr)
        return None
    corpus: dict[int, str] = {}
    states: dict[int, str] = {}
    for r in rows:
        if not isinstance(r, dict):
            continue
        num = r.get("number")
        if not isinstance(num, int):
            continue
        corpus[num] = str(r.get("body") or "")
        states[num] = str(r.get("state", "")).lower()
    resolution = containment.resolve_children(
        config, parent_number=parent_num, corpus=corpus
    )
    open_children = [
        n for n in resolution.numbers if states.get(n) != "closed"
    ]
    return sorted(open_children)


# ---- gh wrappers ----------------------------------------------------


def _gh_get_issue(issue_number: int, config: dict) -> dict | None:
    return gh_get_issue(issue_number, config, fields="title,body,state,labels,milestone")


def _gh_comment(issue_number: int, body: str, config: dict) -> bool:
    try:
        proc = gh_run(
            ["gh", "issue", "comment", str(issue_number), "--body", body],
            config,
            check=False,
        )
    except FileNotFoundError:
        return False
    if proc.returncode != 0:
        print(
            f"error: gh issue comment failed (exit {proc.returncode}).\n"
            f"stderr: {proc.stderr.strip()}",
            file=sys.stderr,
        )
        return False
    return True


def _gh_close_issue(issue_number: int, *, reason: str = "completed", config: dict) -> bool:
    cmd = ["gh", "issue", "close", str(issue_number)]
    if reason:
        cmd.extend(["--reason", reason])
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return False
    if proc.returncode != 0:
        print(
            f"error: gh issue close failed (exit {proc.returncode}).\n"
            f"stderr: {proc.stderr.strip()}",
            file=sys.stderr,
        )
        return False
    return True


def _infer_structural_type(title: str, issue_types: dict) -> str | None:
    types = issue_types.get("types") or {}
    for type_name, entry in types.items():
        if not isinstance(entry, dict):
            continue
        prefix = entry.get("title_prefix", "")
        case = entry.get("title_case", "title")
        rendered = str(prefix)
        if case == "upper":
            rendered = rendered.upper()
        if title.startswith(f"[{rendered}] "):
            return str(type_name)
    return None


def _walk_parent_chain(body: str) -> list[int]:
    """Extract parent issue numbers from the body's parent-ref first line."""
    if not body:
        return []
    out: list[int] = []
    for line in body.splitlines():
        s = line.strip()
        if not s:
            if out:
                break
            continue
        m = re.match(r"^([A-Za-z]+):\s+#(\d+)", s)
        if not m:
            break
        out.append(int(m.group(2)))
        break
    return out


def _read_yaml(path: Path, yaml_loader: YAML) -> dict:
    if not path.is_file():
        return {}
    try:
        data = yaml_loader.load(path.read_text(encoding="utf-8"))
    except (OSError, YAMLError):
        return {}
    return data if isinstance(data, dict) else {}


def _read_members(capability_root: Path, yaml_loader: YAML) -> list[dict]:
    data = _read_yaml(capability_root / "project" / "members.yaml", yaml_loader)
    members = data.get("members") or []
    return members if isinstance(members, list) else []


if __name__ == "__main__":
    sys.exit(main())
