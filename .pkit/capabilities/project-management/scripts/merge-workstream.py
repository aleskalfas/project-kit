#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — merge-workstream (verb-subject per DEC-020 + DEC-018).

Merges one or more "loser" workstreams into a "survivor". Per
DEC-018's lifecycle table:

  * Survivor must exist as an active workstream.
  * Losers' issue counts are surfaced before proceeding.
  * Issues using each loser's `workstream:<loser>` label are re-tagged
    to `workstream:<survivor>` (label-substrate adopters), and the loser
    label is deleted from the repo.
  * Where a board carries the axis, each card whose `Workstream` value is
    a loser is set to the survivor (the survivor's option is added when
    the field lacks it), and the loser's option is dropped from the field.
  * Each loser is removed from workstreams.yaml.
  * References are rewritten by default: each typed `workstream:<loser>`
    and `[workstream:<loser>]` becomes the survivor's, in the tracked
    files and in issue, pull-request and comment bodies. A comment by
    someone else is skipped, with a warning, without admin rights on the
    repository. The `.pkit/` tree, the changelog and the pending
    changesets are left. `--skip-references` leaves them all. Each file
    and body is confirmed in turn, so a run with no interactive shell
    refuses up front unless `--yes` batches the confirmations.

The substrate is changed before the file. A loser whose issues did not
all move stays in the file, with its label or option, so a re-run
finishes it.

Per-change confirmation; per-file and per-object confirmation for the
references; --yes opts into batch. Off a terminal, without `--yes`, nobody
is there to confirm the merge, so it is refused before anything changes, as
with `--skip-references` (#2015).

Membership gate per DEC-021 runs at startup.

Self-contained via PEP 723; runs via
  uv run --script .pkit/capabilities/project-management/scripts/merge-workstream.py --survivor cli loser-1 loser-2

Or via the dispatcher (per COR-021):
  pkit project-management merge-workstream --survivor cli loser

Exit codes:
  0  merged
  1  membership refusal / validation refusal / no usable board field / off a
     terminal without --yes
  2  usage error
  3  gh failure (an issue count unreadable; a move, a delete or a rewrite failed)
"""  # noqa: E501 — a usage line is a command, kept whole

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
    provenance,
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
        description="Merge one or more workstreams into a survivor.",
    )
    parser.add_argument(
        "--survivor",
        required=True,
        help="The slug that survives. Must exist as an active workstream.",
    )
    parser.add_argument(
        "losers",
        nargs="+",
        help="One or more loser slugs to merge into the survivor.",
    )
    parser.add_argument(
        "--skip-labels",
        action="store_true",
        help="Skip the gh label rename + delete operations.",
    )
    parser.add_argument(
        "--skip-references",
        action="store_true",
        help=(
            "Leave the typed references to the losers (`workstream:<loser>`) in "
            "the files and on GitHub. They are rewritten by default."
        ),
    )
    parser.add_argument("--capability-root", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", action="store_true")
    session_guard.add_override_argument(parser)
    args = parser.parse_args()

    capability_root = resolve_capability_root(args.capability_root)
    if capability_root is None:
        print(f"error: {CAPABILITY_NAME} capability not found.", file=sys.stderr)
        return 2

    # Prerequisite gate (#747): refuse on an un-bootstrapped project rather
    # than operating on assumed defaults. See _lib/bootstrap_gate.py.
    if not bootstrap_gate.enforce("merge-workstream", capability_root=capability_root):
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
    # `gh label`/issue retag ops below) are resolved from the cwd-walk in
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

    if args.survivor in args.losers:
        print(
            "[refused] survivor cannot also be a loser.",
            file=sys.stderr,
        )
        return 1

    if not args.skip_references and workstream_sync.references_need_yes(args.yes, args.dry_run):
        print(
            "[refused] a merge rewrites the references to each loser, asking before each "
            "file and body, and no interactive shell is here to ask. Pass --yes to confirm "
            "them all, or --skip-references to leave them. Nothing was changed.",
            file=sys.stderr,
        )
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
    if args.survivor not in existing:
        print(
            f"[refused] survivor {args.survivor!r} not found in workstreams.yaml.",
            file=sys.stderr,
        )
        return 1
    missing_losers = [loser for loser in args.losers if loser not in existing]
    if missing_losers:
        print(
            f"[refused] losers not in workstreams.yaml: {', '.join(missing_losers)}.",
            file=sys.stderr,
        )
        return 1

    config = _read_yaml(capability_root / "project" / "config.yaml", yaml_loader)

    # Whether the kit's own `workstream:*` labels may be RETAGGED and DELETED here
    # — asked of the carriage accessor, never of the board flag alone
    # ([project-management:DEC-051-axis-carriage-activation] decision point 4). A
    # flag-only test would let a board adopter whose map binds `workstream` to
    # their own labels reach `gh label delete` on a name the kit never owned.
    substrate_map = axis_labels.load_substrate_map(capability_root)
    kit_label_note = axis_carriage.kit_label_mutation_note("workstream", config, substrate_map)
    kit_labels = kit_label_note is None and not args.skip_labels
    on_board = axis_carriage.is_board_carried("workstream", config, substrate_map)
    survivor_label = axis_labels.label("workstream", args.survivor)

    # Read every loser's issues before anything changes: DEC-018 surfaces the
    # per-loser count, and the moves below need the issues themselves.
    labelled: dict[str, tuple[workstream_sync.Carrier, ...]] = {}
    if kit_labels:
        for loser in args.losers:
            read = workstream_sync.issues_with_label(
                axis_labels.label("workstream", loser), config, gh_call=gh_run
            )
            if not read.ok:
                print(
                    f"[error] could not list the issues of {loser!r}, so nothing was "
                    f"changed: {read.error}",
                    file=sys.stderr,
                )
                return 3
            labelled[loser] = read.carriers

    board = None
    carded: dict[str, tuple[workstream_sync.Carrier, ...]] = {}
    if on_board:
        field_read = workstream_sync.read_board_field(config)
        if field_read.error is not None:
            print(f"[error] could not read the board: {field_read.error}", file=sys.stderr)
            return 3
        if field_read.field is None:
            print(f"[refused] {field_read.problem}", file=sys.stderr)
            return 1
        board = field_read.field
        for loser in args.losers:
            read = workstream_sync.board_carriers(board, loser, config)
            if not read.ok:
                print(
                    f"[error] could not list the cards of {loser!r}, so nothing was "
                    f"changed: {read.error}",
                    file=sys.stderr,
                )
                return 3
            carded[loser] = read.carriers

    print(f"merge-workstream: survivor={args.survivor}")
    for loser in args.losers:
        if loser in labelled:
            print(
                f"  loser {loser!r}: {len(labelled[loser])} issue(s) tagged "
                f"{axis_labels.label('workstream', loser)}"
            )
        else:
            reason = "--skip-labels" if args.skip_labels else kit_label_note
            print(f"  loser {loser!r}: (gh label ops skipped — {reason})")
        if loser in carded:
            print(f"  loser {loser!r}: {len(carded[loser])} card(s) on the board")
    if board is not None and workstream_sync.find_option(board, args.survivor) is None:
        print(f"  board: add the option `{args.survivor}` to the `Workstream` field")
    if args.skip_references:
        print("  references: left as they are (--skip-references)")
    else:
        print(
            f"  references: rewrite each typed reference to a loser as `{survivor_label}`, "
            "in the tracked files and in issue, pull-request and comment bodies"
        )

    if args.dry_run:
        print("\n[dry-run] nothing written; no gh invocation.")
        return 0
    stop = consent.authorise(
        f"Merge {len(args.losers)} loser(s) into {args.survivor!r}? [y/N] ",
        yes=args.yes,
        step=f"Merging {', '.join(repr(loser) for loser in args.losers)} into {args.survivor!r}",
        verb="merge-workstream",
    )
    if stop is not None:
        return stop

    failures: list[str] = []
    merged = set(args.losers)

    # The board: give it the survivor's option, move each loser's cards to it,
    # and drop the options whose cards all moved.
    if board is not None:
        board, error = _ensure_option(config, board, args.survivor)
        if board is None:
            print(
                f"[error] the board's `Workstream` field was not changed, and nothing "
                f"was written: {error}",
                file=sys.stderr,
            )
            return 3
        survivor_option = workstream_sync.find_option(board, args.survivor) or {}
        for loser, cards in carded.items():
            for card in cards:
                if card.item_id is None:
                    continue
                result = workstream_sync.set_card_option(
                    config, board, card.item_id, survivor_option.get("id", "")
                )
                if not result.ok:
                    failures.append(f"card of #{card.number} ({loser}): {result.error}")
                    merged.discard(loser)
        emptied = [loser for loser in args.losers if loser in merged]
        if any(workstream_sync.find_option(board, loser) for loser in emptied):
            result = workstream_sync.write_options(
                config, board, workstream_sync.options_without(board, emptied)
            )
            if not result.ok:
                failures.append(f"the board's loser options: {result.error}")
                merged.clear()

    # The labels: move each loser's issues, then delete the loser's label.
    for loser, issues in labelled.items():
        loser_label = axis_labels.label("workstream", loser)
        moved = True
        for issue in issues:
            if issue.number is None:
                continue
            error = workstream_sync.retag_issue(
                issue.number, loser_label, survivor_label, config, gh_call=gh_run
            )
            if error is not None:
                failures.append(f"#{issue.number} ({loser}): {error}")
                moved = False
        if not moved:
            merged.discard(loser)
            continue
        error = _gh_label_delete(loser_label, config)
        if error is not None:
            failures.append(f"`{loser_label}`: {error}")
            # The label stays, so the file keeps the loser and a re-run deletes it.
            merged.discard(loser)

    # The file: drop each loser whose issues all moved. A loser left here keeps
    # its label or option, so a re-run finishes it.
    ws = data.get("workstreams")
    if isinstance(ws, list):
        data["workstreams"] = [item for item in ws if item not in merged]
    elif isinstance(ws, dict):
        for loser in merged:
            ws.pop(loser, None)
    try:
        with path.open("w", encoding="utf-8") as f:
            yaml.dump(data, f)
    except OSError as exc:
        print(f"error: failed to write {path}: {exc}", file=sys.stderr)
        return 2

    # The references (DEC-018: default-on for a merge).
    if not args.skip_references:
        versions = provenance.read_versions(capability_root)
        root = workstream_sync.repo_root(capability_root)
        confirm = workstream_sync.confirm_each(args.yes)
        for loser in sorted(merged):
            outcome = workstream_sync.rewrite_everywhere(
                axis_labels.label("workstream", loser),
                target=lambda _number, _where: survivor_label,
                confirm=confirm,
                root=root,
                config=config,
                gh_call=gh_run,
                stamp=lambda text: provenance.stamp(text, versions),
                cwd=root,
            )
            for line in outcome.rewritten:
                print(f"  rewrote {line}")
            for line in outcome.skipped:
                print(f"[warn] left {line}", file=sys.stderr)
            failures += outcome.failed

    if failures:
        for line in failures:
            print(f"[error] {line}", file=sys.stderr)
        left = [loser for loser in args.losers if loser not in merged]
        if left:
            print(
                f"[error] not merged, kept in workstreams.yaml: {', '.join(left)}. "
                "Re-run the merge to finish them.",
                file=sys.stderr,
            )
        return 3

    print(f"\n[ok] merged {len(args.losers)} loser(s) into {args.survivor!r}.")
    return 0


def _ensure_option(
    config: dict, board: workstream_sync.BoardField, slug: str
) -> tuple[workstream_sync.BoardField | None, str | None]:
    """The board's field, with an option `slug` added first where it lacks one.

    Reads the field again after adding, for the new option's id.
    """
    if workstream_sync.find_option(board, slug) is not None:
        return board, None
    result = workstream_sync.write_options(
        config, board, workstream_sync.options_adding(board, slug)
    )
    if not result.ok:
        return None, result.error
    read = workstream_sync.read_board_field(config)
    if read.field is None or workstream_sync.find_option(read.field, slug) is None:
        return None, read.error or read.problem or f"the option `{slug}` did not appear"
    return read.field, None


def _gh_label_delete(label: str, config: dict) -> str | None:
    """Delete `label`; the error, or None. A label already gone counts as deleted."""
    try:
        proc = gh_run(["gh", "label", "delete", label, "--yes"], config, check=False)
    except FileNotFoundError:
        return "`gh` not on PATH"
    if proc.returncode == 0 or "not found" in (proc.stderr or ""):
        return None
    return (proc.stderr or "").strip() or "gh label delete failed"


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
