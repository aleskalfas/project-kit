#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — rename-workstream (verb-subject per DEC-020 + DEC-018).

Renames a workstream's slug. Per DEC-018, this is a label-rename
operation: the workstreams.yaml entry's mapping key changes, the
GitHub `workstream:<old>` label is renamed to `workstream:<new>`,
issues using the old label are re-tagged automatically by gh's
rename behaviour. Where a board carries the axis, the option `<old>`
of its `Workstream` field is renamed instead, keeping each card's value.

Before it changes anything it checks the new slug against DEC-018's
rules, and the old and the new label (or board option). It refuses
where both exist, since the issues would then sit under two values:
`merge-workstream` consolidates them. Where only the new one exists,
there is nothing to rename. Where neither does, the new one is created.
The label or the board is changed before the file, so a re-run after a
failure finds the substrate renamed and writes the file.

Per-change confirmation: the script narrates the plan and prompts
unless `--yes` is set. Off a terminal, without `--yes`, nobody is there to
confirm it, so the rename is refused before anything changes (#2015).

Membership gate per DEC-021 runs at startup.

Self-contained via PEP 723; runs via
  uv run --script .pkit/capabilities/project-management/scripts/rename-workstream.py <old> <new>

Or via the dispatcher (per COR-021):
  pkit project-management rename-workstream <old> <new>

Exit codes:
  0  renamed (or dry-run reported)
  1  membership refusal / validation refusal / both old and new exist / off a
     terminal without --yes
  2  usage error
  3  gh failure (labels or board unreadable; label or board not changed)
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
    validate_slug,
    workstreams_path,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Rename a workstream slug.")
    parser.add_argument("old", help="Current slug.")
    parser.add_argument("new", help="Target slug.")
    parser.add_argument(
        "--skip-label",
        action="store_true",
        help="Skip the `gh label edit workstream:<old> --name workstream:<new>` step.",
    )
    parser.add_argument("--capability-root", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", action="store_true")
    session_guard.add_override_argument(parser)
    args = parser.parse_args()

    err = validate_slug(args.new)
    if err:
        print(f"[refused] new {err}", file=sys.stderr)
        return 1
    if args.old == args.new:
        print("[noop] new slug equals old slug.")
        return 0

    capability_root = resolve_capability_root(args.capability_root)
    if capability_root is None:
        print(f"error: {CAPABILITY_NAME} capability not found.", file=sys.stderr)
        return 2

    # Prerequisite gate (#747): refuse on an un-bootstrapped project rather
    # than operating on assumed defaults. See _lib/bootstrap_gate.py.
    if not bootstrap_gate.enforce("rename-workstream", capability_root=capability_root):
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
    # `gh label edit` below) are resolved from the cwd-walk in
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
            f"error: {path} does not exist. Run `add-workstream` or the v0.5.0 migration first.",
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
    if args.old not in existing:
        print(f"error: workstream {args.old!r} not found.", file=sys.stderr)
        return 2
    if args.new in existing:
        print(
            f"[refused] workstream {args.new!r} already exists. Use "
            "merge-workstream if you want to consolidate.",
            file=sys.stderr,
        )
        return 1

    config = _read_yaml(capability_root / "project" / "config.yaml", yaml_loader)

    # Whether the kit's own `workstream:*` labels may be RENAMED here — asked of
    # the carriage accessor, never of the board flag alone
    # ([project-management:DEC-051-axis-carriage-activation] decision point 4). A
    # flag-only test would let a board adopter whose map binds `workstream` to
    # their own labels reach `gh label edit --name`, renaming a label the kit
    # never owned.
    substrate_map = axis_labels.load_substrate_map(capability_root)
    kit_label_note = axis_carriage.kit_label_mutation_note("workstream", config, substrate_map)
    kit_labels = kit_label_note is None
    on_board = axis_carriage.is_board_carried("workstream", config, substrate_map)
    old_label = axis_labels.label("workstream", args.old)
    new_label = axis_labels.label("workstream", args.new)

    # Check the old and the new label before anything changes (DEC-018).
    label_step = None
    if kit_labels and not args.skip_label:
        names, error = workstream_sync.label_names(config, gh_call=gh_run)
        if names is None:
            print(
                f"[error] could not read the repository's labels, so nothing was changed: {error}",
                file=sys.stderr,
            )
            return 3
        label_step = _step(old_label.lower() in names, new_label.lower() in names)
        if label_step == "refuse":
            print(
                f"[refused] both `{old_label}` and `{new_label}` exist, so the issues "
                "would sit under two labels. Use merge-workstream to consolidate "
                "them. Nothing was changed.",
                file=sys.stderr,
            )
            return 1

    # The same check on the board's `Workstream` field, where a board carries it.
    board = None
    board_step = None
    if on_board:
        read = workstream_sync.read_board_field(config)
        if read.error is not None:
            print(f"[error] could not read the board: {read.error}", file=sys.stderr)
            return 3
        if read.field is None:
            print(f"[refused] {read.problem}", file=sys.stderr)
            return 1
        board = read.field
        board_step = _step(
            workstream_sync.find_option(board, args.old) is not None,
            workstream_sync.find_option(board, args.new) is not None,
        )
        if board_step == "refuse":
            print(
                f"[refused] the board's `Workstream` field offers both `{args.old}` and "
                f"`{args.new}`. Use merge-workstream to consolidate them. Nothing was "
                "changed.",
                file=sys.stderr,
            )
            return 1

    print(f"rename-workstream: {args.old} → {args.new}")
    print(f"  file:        {path}")
    if label_step is not None:
        print(f"  label:       {_describe(label_step, f'`{old_label}`', f'`{new_label}`')}")
    elif kit_label_note is not None:
        print(f"  label:       none — {kit_label_note}")
    if board_step is not None:
        print(f"  board:       {_describe(board_step, f'option `{args.old}`', f'`{args.new}`')}")

    if args.dry_run:
        print("\n[dry-run] nothing written; no gh invocation.")
        return 0
    stop = consent.authorise(
        "Proceed? [y/N] ",
        yes=args.yes,
        step=f"Renaming workstream {args.old!r} to {args.new!r}",
        verb="rename-workstream",
    )
    if stop is not None:
        return stop

    # The substrate first, then the file: a failure here leaves the file as it
    # was, and a re-run finds the renamed substrate and only writes the file.
    if board is not None and board_step in ("rename", "create"):
        options = (
            workstream_sync.options_renaming(board, args.old, args.new)
            if board_step == "rename"
            else workstream_sync.options_adding(board, args.new)
        )
        result = workstream_sync.write_options(config, board, options)
        if not result.ok:
            print(
                f"[error] the board's `Workstream` field was not changed, and the file "
                f"was not written: {result.error}",
                file=sys.stderr,
            )
            return 3

    if label_step == "rename" and not _gh_label_rename(args.old, args.new, config):
        print("[error] the label was not renamed, and the file was not written.", file=sys.stderr)
        return 3
    if label_step == "create" and not _gh_label_create(args.new, config):
        print("[error] the label was not created, and the file was not written.", file=sys.stderr)
        return 3

    if not _rename_in_file(yaml, data, args.old, args.new, path):
        return 2

    print(f"\n[ok] renamed workstream {args.old!r} → {args.new!r}.")
    return 0


def _step(old_exists: bool, new_exists: bool) -> str:
    """What a rename does to a substrate that holds these values.

    Both held: refuse, since the issues would sit under two values. The old one
    only: rename it. The new one only: nothing to do. Neither: create the new one.
    """
    if old_exists and new_exists:
        return "refuse"
    if old_exists:
        return "rename"
    if new_exists:
        return "none"
    return "create"


def _describe(step: str, old: str, new: str) -> str:
    if step == "rename":
        return f"rename {old} → {new}"
    if step == "create":
        return f"create {new} ({old} does not exist)"
    return f"none — {new} exists already and {old} does not"


def _rename_in_file(yaml: YAML, data: dict, old: str, new: str, path: Path) -> bool:
    ws = data.get("workstreams")
    if isinstance(ws, list):
        new_list = [new if item == old else item for item in ws]
        data["workstreams"] = new_list
    elif isinstance(ws, dict):
        # Rebuild preserving insertion order.
        new_map = {}
        for k, v in ws.items():
            if k == old:
                new_map[new] = v
            else:
                new_map[k] = v
        data["workstreams"] = new_map
    else:
        print(f"error: {path} `workstreams:` is malformed.", file=sys.stderr)
        return False

    try:
        with path.open("w", encoding="utf-8") as f:
            yaml.dump(data, f)
    except OSError as exc:
        print(f"error: failed to write {path}: {exc}", file=sys.stderr)
        return False
    return True


def _gh_label_create(slug: str, config: dict) -> bool:
    """Create `workstream:<slug>`; an existing label counts as created."""
    try:
        proc = gh_run(
            [
                "gh",
                "label",
                "create",
                axis_labels.label("workstream", slug),
                "--color",
                "0e8a16",
                "--description",
                f"Workstream `{slug}` (per project-management:DEC-018).",
            ],
            config,
            check=False,
        )
    except FileNotFoundError:
        return False
    if proc.returncode == 0 or "already exists" in (proc.stderr or ""):
        return True
    print(f"error: gh label create failed: {(proc.stderr or '').strip()}", file=sys.stderr)
    return False


def _gh_label_rename(old: str, new: str, config: dict) -> bool:
    """Rename `workstream:<old>` to `workstream:<new>` via gh label edit."""
    try:
        proc = gh_run(
            [
                "gh",
                "label",
                "edit",
                axis_labels.label("workstream", old),
                "--name",
                axis_labels.label("workstream", new),
            ],
            config,
            check=False,
        )
    except FileNotFoundError:
        return False
    if proc.returncode == 0:
        return True
    if "not found" in proc.stderr:
        print(
            f"[info] label `{axis_labels.label('workstream', old)}` not present; nothing to "
            "rename.",
            file=sys.stderr,
        )
        return True
    print(
        f"error: gh label edit failed (exit {proc.returncode}).\nstderr: {proc.stderr.strip()}",
        file=sys.stderr,
    )
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
