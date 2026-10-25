#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — remove-workstream (verb-subject per DEC-020 + DEC-018).

Removes a workstream. Per DEC-018:

  * Zero-issues precondition: refuses if any issue (open or closed)
    still carries the workstream, whatever substrate carries the axis:
    the `workstream:<slug>` label, the adopter's own label or title
    prefix, or the board's `Workstream` field. The count is taken with
    `--skip-label` too, and a count that cannot be read refuses as well.
    `--force` (DEC-046) passes the precondition.
  * Type-the-slug confirmation prompt to prevent accidents. `--yes` skips
    it; off a terminal, without `--yes`, nobody is there to type it, so
    the removal is refused before anything changes (#2015).
  * Removes the entry from workstreams.yaml; deletes the GitHub label.

Membership gate per DEC-021 runs at startup.

Self-contained via PEP 723; runs via
  uv run --script .pkit/capabilities/project-management/scripts/remove-workstream.py <slug>

Or via the dispatcher (per COR-021):
  pkit project-management remove-workstream <slug>

Exit codes:
  0  removed
  1  membership refusal / validation refusal / non-zero issue count / off a
     terminal without --yes
  2  usage error (slug not found)
  3  gh failure (the issue count unreadable; the label not deleted)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
# Constraint-1 gate (RF-2, #265): the workstream-label MUTATORS mutate kit
# `workstream:*` labels via `gh label`. Under a PRESENT substrate-map whose
# `workstream` axis is `unsupported` (or absent), this would violate "never write
# an unmanaged label" — so the mutator calls
# `axis_labels.workstream_mutator_refusal(...)` after the membership check and
# REFUSES before any `gh label` op when it trips. Greenfield is unchanged; the
# richer present-map behaviour stays the adopt-existing Feature #264.
from _lib import (
    axis_carriage,
    axis_labels,
    bootstrap_gate,
    consent,
    session_guard,
    workstream_sync,
)
from _lib.gh import gh_run, load_adopter_config
from _lib.membership import (
    CAPABILITY_NAME,
    check_membership,
    resolve_capability_root,
    resolve_invoker_identity,
)
from _lib.workstreams import (
    parse_workstreams,
    workstreams_path,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Remove a workstream (refuses if any issue still uses it).",
    )
    parser.add_argument("slug", help="Slug to remove.")
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Force past the zero-issues precondition (the `--force` layer "
            "per DEC-046 — a label has no comment thread, so the override is "
            "surfaced in output but not audited to a comment). Discouraged — "
            "leaves orphaned `workstream:<slug>` labels on issues."
        ),
    )
    parser.add_argument(
        "--skip-label",
        action="store_true",
        help="Skip the gh label delete step.",
    )
    parser.add_argument("--capability-root", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the type-the-slug confirmation (use with extreme care).",
    )
    session_guard.add_override_argument(parser)
    args = parser.parse_args()

    capability_root = resolve_capability_root(args.capability_root)
    if capability_root is None:
        print(f"error: {CAPABILITY_NAME} capability not found.", file=sys.stderr)
        return 2

    # Prerequisite gate (#747): refuse on an un-bootstrapped project rather
    # than operating on assumed defaults. See _lib/bootstrap_gate.py.
    if not bootstrap_gate.enforce("remove-workstream", capability_root=capability_root):
        return 2

    yaml_loader = YAML(typ="safe")
    config = load_adopter_config(capability_root)
    members = _read_members(capability_root, yaml_loader)
    invoker = resolve_invoker_identity(config=config)
    membership = check_membership(members, invoker)
    if not membership.allowed:
        print(membership.refusal_message, file=sys.stderr)
        return 1

    # Foreign-repo mutation guard (COR-039 / ADR-034). workstreams.yaml (and the
    # `gh label delete` below) are resolved from the cwd-walk in
    # resolve_capability_root, so a `cd /B` redirects this mutation into a
    # DIFFERENT repo than the session anchor (CLAUDE_PROJECT_DIR); gate that
    # unless the operator confirms the override. Runs before any write/gh op.
    if not session_guard.enforce(override=args.allow_foreign_repo):
        return 1

    # Constraint-1 gate (RF-2, #265): refuse before any `gh label` op when the
    # workstream axis is unsupported/absent under a present substrate-map.
    refusal = axis_labels.workstream_mutator_refusal(capability_root)
    if refusal is not None:
        print(f"[refused] {refusal}", file=sys.stderr)
        return 1

    path = workstreams_path(capability_root)
    if not path.is_file():
        print(
            f"error: {path} does not exist. Nothing to remove.",
            file=sys.stderr,
        )
        return 2

    yaml = YAML(typ="rt")
    yaml.preserve_quotes = True
    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.load(f) or {}
    except (OSError, YAMLError) as exc:
        print(f"error: failed to parse {path}: {exc}", file=sys.stderr)
        return 2

    parsed = parse_workstreams(data)
    existing = {w.slug for w in parsed.entries}
    if args.slug not in existing:
        print(f"error: workstream {args.slug!r} not found.", file=sys.stderr)
        return 2

    config = _read_yaml(capability_root / "project" / "config.yaml", yaml_loader)

    # Whether the kit's own `workstream:*` labels may be DELETED here — asked of
    # the carriage accessor, never of the board flag alone
    # ([project-management:DEC-051-axis-carriage-activation] decision point 4).
    # Deleting is the sharper edge of the same hazard `add` carries: a flag-only
    # test would let a board adopter whose map binds `workstream` to their own
    # labels reach `gh label delete`, and no guard covers a label the kit never
    # owned. Only the greenfield (`kit-label`) arm touches labels.
    substrate_map = axis_labels.load_substrate_map(capability_root)
    kit_label_note = axis_carriage.kit_label_mutation_note("workstream", config, substrate_map)
    kit_labels = kit_label_note is None

    # Issue-count precondition (DEC-018): taken from whatever substrate carries
    # the axis, and taken with --skip-label too, which skips the label delete
    # alone.
    carriage = axis_carriage.carriage("workstream", config, substrate_map)
    read = workstream_sync.carriers(
        args.slug,
        carriage=carriage,
        config=config,
        substrate_map=substrate_map,
        gh_call=gh_run,
    )
    where = axis_carriage.describe("workstream", config, substrate_map)
    n = len(read.carriers) if read.ok else None
    if not read.ok:
        if not args.force:
            print(
                f"[error] could not tell whether any issue carries {args.slug!r} "
                f"(workstream is carried {where}), so nothing was removed: {read.error}\n"
                "  → Pass --force to remove anyway.",
                file=sys.stderr,
            )
            return 3
        print(f"[warn] --force: the issue count could not be read: {read.error}", file=sys.stderr)
    elif n and not args.force:
        numbers = ", ".join(f"#{c.number}" for c in read.carriers[:20] if c.number is not None)
        print(
            f"[refused] {n} issue(s) still carry {args.slug!r} (workstream is carried "
            f"{where}): {numbers}. Re-tag them (or use `merge-workstream` to "
            "consolidate into another slug) first.\n"
            "  → Pass --force to remove anyway (will leave orphan values).",
            file=sys.stderr,
        )
        return 1
    elif n:
        print(f"[warn] --force: {n} issue(s) still carry {args.slug!r}.", file=sys.stderr)

    print(f"remove-workstream: {args.slug}")
    print(f"  file:           {path}")
    if n is not None:
        print(f"  affected issues: {n}")
    if kit_labels and not args.skip_label:
        print(f"  label:          delete `{axis_labels.label('workstream', args.slug)}`")
    elif kit_label_note is not None:
        print(f"  label:          none — {kit_label_note}")

    if args.dry_run:
        print("\n[dry-run] nothing written; no gh invocation.")
        return 0

    if not args.yes:
        if not consent.at_a_terminal():
            return consent.refuse(f"Removing workstream {args.slug!r}", "remove-workstream")
        typed = input(f"Type the slug {args.slug!r} to confirm: ").strip()
        if typed != args.slug:
            print("[refused] slug did not match; aborted.", file=sys.stderr)
            return 0

    # Label deletion first: a label already gone counts as deleted, so a re-run
    # after a failed file write only writes the file.
    if kit_labels and not args.skip_label and not _gh_label_delete(args.slug, config):
        print(
            f"[error] `{axis_labels.label('workstream', args.slug)}` was not deleted, and "
            "workstreams.yaml was not changed.",
            file=sys.stderr,
        )
        return 3

    # File mutation.
    ws = data.get("workstreams")
    if isinstance(ws, list):
        data["workstreams"] = [item for item in ws if item != args.slug]
    elif isinstance(ws, dict):
        ws.pop(args.slug, None)
    try:
        with path.open("w", encoding="utf-8") as f:
            yaml.dump(data, f)
    except OSError as exc:
        print(f"error: failed to write {path}: {exc}", file=sys.stderr)
        return 2

    print(f"\n[ok] removed workstream {args.slug!r}.")
    return 0


def _gh_label_delete(slug: str, config: dict) -> bool:
    try:
        proc = gh_run(
            ["gh", "label", "delete", axis_labels.label("workstream", slug), "--yes"],
            config,
            check=False,
        )
    except FileNotFoundError:
        return False
    if proc.returncode == 0:
        return True
    if "not found" in (proc.stderr or ""):
        return True
    return False


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
