"""Shared CLI driver for check-criterion / uncheck-criterion.

The two verbs are identical apart from the target checkbox state, so the whole
operational shell — argument parsing (the index + optional-guard positional
grammar), the startup context header, the DEC-021 membership gate, the body
fetch, the DEC-038 batch engine call, and edit-issue's `gh issue edit
--body-file` write-back — lives here once and each script calls
`run_criterion_verb(...)` with its state. This keeps each script a thin PEP 723
entry point (a single function call) while the behaviour and its tests live in
one place.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from _lib import provenance
from _lib import session_guard
from _lib.criterion_ops import Target, plan_batch
from _lib.gh import gh_get_issue, gh_run, load_adopter_config
from _lib.membership import (
    CAPABILITY_NAME,
    check_membership,
    resolve_capability_root,
    resolve_invoker_identity,
)


def run_criterion_verb(*, verb: str, target_checked: bool) -> int:
    """Drive one check/uncheck invocation end-to-end; return the exit code.

    `verb` is the command name (for help + output). `target_checked` is the
    state the named boxes should end in (True = ticked, for check-criterion).
    """
    parser = _build_parser(verb, target_checked)
    args = parser.parse_args()

    try:
        targets = _parse_targets(args.targets)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if not targets:
        print(
            f"error: no criteria named. Pass at least one <index>.\n"
            f"  {verb} <issue> <index> [expected-text] ...",
            file=sys.stderr,
        )
        return 2

    capability_root = resolve_capability_root(args.capability_root)
    if capability_root is None:
        print(f"error: {CAPABILITY_NAME} capability not found.", file=sys.stderr)
        return 2

    yaml_loader = YAML(typ="safe")
    config = load_adopter_config(capability_root)
    members = _read_members(capability_root, yaml_loader)
    invoker = resolve_invoker_identity(config=config)
    membership = check_membership(members, invoker)
    if not membership.allowed:
        print(membership.refusal_message, file=sys.stderr)
        return 1

    # Foreign-repo mutation guard (COR-039 / ADR-034) — gate before the
    # `gh issue edit` write-back: target repo (cwd) vs session anchor.
    if not session_guard.enforce(override=args.allow_foreign_repo):
        return 1

    issue = gh_get_issue(args.issue_number, config, fields="title,body")
    if issue is None:
        return 2
    # Work footer-free: strip on read so criterion indices are unaffected;
    # the seam re-stamps exactly one footer on write (ADR-037).
    body = provenance.strip_footer(str(issue.get("body") or ""))

    # Context header (standard pm-script scaffolding).
    action = "tick" if target_checked else "untick"
    print(f"{verb}: #{args.issue_number}")
    print(f"  action:  {action} {len(targets)} "
          f"{'criterion' if len(targets) == 1 else 'criteria'}")

    plan = plan_batch(body, targets, target_checked=target_checked)

    for result in plan.results:
        marker = "ok" if result.ok else "refused"
        print(f"  [{marker}] {result.message}")

    if not plan.accepted:
        # DEC-038 D4 hard-reject: the whole batch is refused before any
        # mutation. Nothing is written.
        print(
            "\n[refused] batch rejected before any mutation; nothing written.",
            file=sys.stderr,
        )
        return 1

    if not plan.changed:
        # Every target was already in the requested state — idempotent no-op.
        print(f"\n[ok] #{args.issue_number}: no change (all targets already {action}ed).")
        return 0

    if args.dry_run:
        print("\n[dry-run] gh would be invoked; nothing written.")
        return 0
    if not args.yes and sys.stdin.isatty():
        reply = input("Write the change? [y/N] ").strip().lower()
        if reply not in ("y", "yes"):
            print("aborted.", file=sys.stderr)
            return 0

    stamped = provenance.stamp(
        plan.new_body or "", provenance.read_versions(capability_root)
    )
    if not _gh_write_body(args.issue_number, stamped, config):
        return 3

    print(f"\n[ok] #{args.issue_number}: updated.")
    return 0


# ---- argument parsing -----------------------------------------------------


def _build_parser(verb: str, target_checked: bool) -> argparse.ArgumentParser:
    action = "Tick" if target_checked else "Untick"
    parser = argparse.ArgumentParser(
        prog=verb,
        description=(
            f"{action} one or more acceptance-criterion checkboxes on a GitHub "
            "issue, addressed by 1-based index with an optional expected-text "
            "guard (per DEC-038). Validates the whole batch up front and refuses "
            "before any mutation on a hard inconsistency; idempotent on re-run."
        ),
    )
    parser.add_argument("issue_number", type=int, help="GitHub issue number.")
    parser.add_argument(
        "targets",
        nargs="+",
        metavar="INDEX [TEXT]",
        help=(
            "One or more targets. Each is a 1-based criterion INDEX optionally "
            "followed by the expected TEXT at that index (a guard — the verb "
            "refuses unless the line still matches). An integer argument starts "
            "a new target; a non-integer argument is the preceding index's "
            "guard. Example: `1 \"docs updated\" 3 5`."
        ),
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
        help="Validate + show the plan; do not invoke gh.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the confirmation prompt.",
    )
    session_guard.add_override_argument(parser)
    return parser


def _parse_targets(tokens: list[str]) -> list[Target]:
    """Parse the `<index> [text] <index> [text] ...` positional grammar.

    An integer token opens a new target (its index); a following non-integer
    token is that index's expected-text guard. Two guards in a row, or a guard
    with no preceding index, is a usage error. Returns the parsed targets in
    order. A non-positive index is rejected here so the engine only ever sees
    well-formed targets (the out-of-*range* check — index exceeding the criteria
    count — stays in the engine, which knows the count).
    """
    targets: list[Target] = []
    pending_index: int | None = None
    for token in tokens:
        as_int = _as_int(token)
        if as_int is not None:
            if pending_index is not None:
                targets.append(Target(index=pending_index))
            if as_int < 1:
                raise ValueError(
                    f"criterion index must be 1-based (>= 1); got {as_int}"
                )
            pending_index = as_int
        else:
            if pending_index is None:
                raise ValueError(
                    f"expected-text {token!r} has no preceding index "
                    "(each guard follows the index it guards)"
                )
            targets.append(Target(index=pending_index, expected_text=token))
            pending_index = None
    if pending_index is not None:
        targets.append(Target(index=pending_index))
    return targets


def _as_int(token: str) -> int | None:
    """Parse a token as an int, or None when it is not an integer literal."""
    try:
        return int(token)
    except ValueError:
        return None


# ---- gh write-back (edit-issue's round-trip) ------------------------------


def _gh_write_body(issue_number: int, body: str, config: dict) -> bool:
    """Write the rewritten body via `gh issue edit --body-file` (edit-issue's pattern).

    The body always goes through a temp file (avoids shell length limits), exactly
    as edit-issue._gh_apply_edit does.
    """
    with tempfile.NamedTemporaryFile(
        "w", suffix=".md", encoding="utf-8", delete=False
    ) as f:
        f.write(body)
        body_path = f.name
    try:
        cmd = ["gh", "issue", "edit", str(issue_number), "--body-file", body_path]
        try:
            proc = gh_run(cmd, config, check=False)
        except FileNotFoundError:
            print("error: `gh` not on PATH. Install GitHub CLI.", file=sys.stderr)
            return False
        if proc.returncode != 0:
            print(
                f"error: gh issue edit failed (exit {proc.returncode}).\n"
                f"stderr: {proc.stderr.strip()}",
                file=sys.stderr,
            )
            return False
    finally:
        try:
            Path(body_path).unlink(missing_ok=True)
        except OSError:
            pass
    return True


def _read_members(capability_root: Path, yaml_loader: YAML) -> list[dict]:
    path = capability_root / "project" / "members.yaml"
    if not path.is_file():
        return []
    try:
        data = yaml_loader.load(path.read_text(encoding="utf-8")) or {}
    except (OSError, YAMLError):
        return []
    members = data.get("members") if isinstance(data, dict) else None
    return members if isinstance(members, list) else []
