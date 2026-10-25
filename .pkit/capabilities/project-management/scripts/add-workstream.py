#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — add-workstream (verb-subject per DEC-020 + DEC-018).

Adds a workstream to `project/workstreams.yaml`. Checks the slug and
each attribute against DEC-018's rules (`_lib/workstreams`), and refuses
duplicates; defaults `name` to the slug; defaults `status` to active.

Keeps the substrate that carries the axis in step with the file: for
label-substrate adopters it creates the `workstream:<slug>` label
(idempotent — skips if it already exists), and where a board carries
the axis it adds the option `<slug>` to the board's `Workstream`
single-select field. Either happens before the file is written, so a
failure leaves the file as it was.

Membership gate per DEC-021 runs at startup. A workstream is the project's own
configuration, which DEC-018 makes the PM's: the command asks at a terminal,
`--yes` authorises it, and off a terminal without `--yes` it refuses (#2015).

Self-contained via PEP 723; runs via
  uv run --script .pkit/capabilities/project-management/scripts/add-workstream.py <slug> [--name "..."] [--description "..."]

Or via the dispatcher (per COR-021):
  pkit project-management add-workstream <slug>

Exit codes:
  0  added (or dry-run reported)
  1  membership refusal / validation refusal / duplicate slug / no usable board field
     / off a terminal without --yes
  2  usage error (capability not found; bad slug)
  3  gh failure (board read or write; label creation)
"""  # noqa: E501 — a usage line is a command, kept whole

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import (
    axis_carriage,
    axis_labels,
    bootstrap_gate,
    consent,
    session_guard,
    workstream_sync,
)
from _lib.gh import gh_run, load_adopter_config

# Constraint-1 gate (RF-2, #265): the workstream-label MUTATORS
# (add/remove/merge/rename/split) create/delete/rename kit `workstream:*` labels
# via `gh label`. Under a PRESENT substrate-map whose `workstream` axis is
# `unsupported` (or absent), creating a kit `workstream:*` label would violate
# "never write an unmanaged label" — so each mutator calls
# `axis_labels.workstream_mutator_refusal(...)` after the membership check and
# REFUSES before any `gh label` op when it trips. Greenfield is unchanged. The
# richer present-map behaviour (validate-against-the-bound-set, retag) stays the
# adopt-existing Feature #264; this is just the constraint-1 gate.
from _lib.membership import (
    CAPABILITY_NAME,
    check_membership,
    resolve_capability_root,
    resolve_invoker_identity,
)
from _lib.workstreams import (
    parse_workstreams,
    validate_attributes,
    validate_slug,
    workstreams_path,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=("Add a workstream to project/workstreams.yaml per DEC-018."),
    )
    parser.add_argument(
        "slug",
        help="Kebab-case slug. Must match `^[a-z][a-z0-9-]*[a-z0-9]$`, 2–40 chars.",
    )
    parser.add_argument(
        "--name",
        default=None,
        help="Human-readable name. Defaults to the slug.",
    )
    parser.add_argument(
        "--description",
        default=None,
        help="One-line description, ≤200 chars.",
    )
    parser.add_argument(
        "--status",
        choices=["active", "deprecated"],
        default="active",
        help="Lifecycle status. Default: active.",
    )
    parser.add_argument(
        "--deprecated-reason",
        default=None,
        help="Required when --status=deprecated.",
    )
    parser.add_argument(
        "--skip-label",
        action="store_true",
        help=("Skip the `gh label create workstream:<slug>` step (label-substrate adopters only)."),
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
        help="Print the plan; do not write.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the confirmation prompt.",
    )
    session_guard.add_override_argument(parser)
    args = parser.parse_args()

    capability_root = resolve_capability_root(args.capability_root)
    if capability_root is None:
        print(
            f"error: {CAPABILITY_NAME} capability not found.",
            file=sys.stderr,
        )
        return 2

    # Prerequisite gate (#747): refuse on an un-bootstrapped project rather
    # than operating on assumed defaults. See _lib/bootstrap_gate.py.
    if not bootstrap_gate.enforce("add-workstream", capability_root=capability_root):
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
    # `gh label create` below) are resolved from the cwd-walk in
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

    # Slug and attribute validation (DEC-018's rules, all of them).
    errors = []
    err = validate_slug(args.slug)
    if err:
        errors.append(err)
    errors += validate_attributes(
        name=args.name,
        description=args.description,
        status=args.status,
        deprecated_reason=args.deprecated_reason,
    )
    if errors:
        for err in errors:
            print(f"[refused] {err}", file=sys.stderr)
        return 1

    if args.status == "deprecated" and not args.deprecated_reason:
        print(
            "[refused] --deprecated-reason is required when --status=deprecated.",
            file=sys.stderr,
        )
        return 1

    # Read current state.
    config = _read_yaml(capability_root / "project" / "config.yaml", yaml_loader)

    # Whether the kit's own `workstream:*` labels may be CREATED here — asked of
    # the carriage accessor, never of the board flag alone
    # ([project-management:DEC-051-axis-carriage-activation] decision point 4).
    # The flag alone answers "is a board configured?", which is not the same
    # question: a board adopter whose map binds `workstream` to their own labels
    # would pass a flag test and get an unmanaged `workstream:<slug>` label
    # created. Only the greenfield (`kit-label`) arm mutates kit labels; every
    # other carriage suppresses the label half and says so.
    substrate_map = axis_labels.load_substrate_map(capability_root)
    kit_label_note = axis_carriage.kit_label_mutation_note("workstream", config, substrate_map)
    kit_labels = kit_label_note is None
    on_board = axis_carriage.is_board_carried("workstream", config, substrate_map)

    current = _read_workstreams_file_or_legacy(capability_root, yaml_loader)
    parsed = parse_workstreams(current if current else None)

    existing_slugs = {w.slug for w in parsed.entries}
    if args.slug in existing_slugs:
        print(
            f"[refused] workstream {args.slug!r} already exists.",
            file=sys.stderr,
        )
        return 1

    new_entry = {
        "name": args.name or args.slug,
    }
    if args.description:
        new_entry["description"] = args.description
    new_entry["status"] = args.status
    if args.deprecated_reason:
        new_entry["deprecated_reason"] = args.deprecated_reason

    # Where a board carries the axis, read its `Workstream` field before
    # anything is written: a board that cannot take the option refuses here.
    board = None
    board_option = None
    if on_board:
        read = workstream_sync.read_board_field(config)
        if read.error is not None:
            print(f"[error] could not read the board: {read.error}", file=sys.stderr)
            return 3
        if read.field is None:
            print(f"[refused] {read.problem}", file=sys.stderr)
            return 1
        board = read.field
        board_option = workstream_sync.find_option(board, args.slug)

    print(f"add-workstream: {args.slug}")
    print(f"  name:        {new_entry['name']}")
    if "description" in new_entry:
        print(f"  description: {new_entry['description']}")
    print(f"  status:      {new_entry['status']}")
    if "deprecated_reason" in new_entry:
        print(f"  reason:      {new_entry['deprecated_reason']}")
    print(f"  target file: {workstreams_path(capability_root)}")
    if kit_labels and not args.skip_label:
        print(
            f"  label:       create `{axis_labels.label('workstream', args.slug)}` "
            "(label-substrate)"
        )
    elif kit_label_note is not None:
        print(f"  label:       none — {kit_label_note}")
    if board is not None:
        if board_option is None:
            print(f"  board:       add the option `{args.slug}` to the `Workstream` field")
        else:
            print(f"  board:       the `Workstream` field already offers `{args.slug}`")

    if args.dry_run:
        print("\n[dry-run] nothing written; no gh invocation.")
        return 0
    stop = consent.authorise(
        "Proceed? [y/N] ",
        yes=args.yes,
        step=f"Adding workstream {args.slug!r}",
        verb="add-workstream",
    )
    if stop is not None:
        return stop

    # The substrate first: the label create and the option write are both
    # idempotent, so a re-run after a failed file write finds them there and
    # only writes the file.
    if kit_labels and not args.skip_label and not _gh_label_create(args.slug, config):
        print("[error] the label was not created, and nothing was written.", file=sys.stderr)
        return 3
    if board is not None and board_option is None:
        result = workstream_sync.write_options(
            config,
            board,
            workstream_sync.options_adding(board, args.slug, args.description or ""),
        )
        if not result.ok:
            print(
                f"[error] the board's `Workstream` field was not changed, and nothing "
                f"was written: {result.error}",
                file=sys.stderr,
            )
            return 3

    # Write the file.
    if not _add_to_file(capability_root, args.slug, new_entry):
        return 2

    print(f"\n[ok] added workstream {args.slug!r}.")
    return 0


# ---- file I/O -------------------------------------------------------


def _read_workstreams_file_or_legacy(
    capability_root: Path, yaml_loader: YAML
) -> dict | list | None:
    """Read workstreams from the dedicated file, falling back to config.yaml."""
    path = workstreams_path(capability_root)
    if path.is_file():
        return _read_yaml(path, yaml_loader)
    config = _read_yaml(capability_root / "project" / "config.yaml", yaml_loader)
    return config.get("workstreams")


def _add_to_file(capability_root: Path, slug: str, entry: dict) -> bool:
    """Append the entry to workstreams.yaml (round-trip preserving)."""
    path = workstreams_path(capability_root)
    yaml = YAML(typ="rt")
    yaml.preserve_quotes = True

    if not path.is_file():
        # Bootstrap the file with mapping form.
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {"schema_version": 1, "workstreams": {slug: entry}}
        try:
            with path.open("w", encoding="utf-8") as f:
                yaml.dump(data, f)
            return True
        except OSError as exc:
            print(f"error: failed to write {path}: {exc}", file=sys.stderr)
            return False

    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.load(f) or {}
    except (OSError, YAMLError) as exc:
        print(f"error: failed to parse {path}: {exc}", file=sys.stderr)
        return False
    if not isinstance(data, dict):
        print(f"error: {path} top-level is not a mapping", file=sys.stderr)
        return False

    ws = data.get("workstreams")
    if isinstance(ws, list):
        # Upgrade to mapping form before adding the attributed entry.
        upgraded: dict = {}
        for item in ws:
            if isinstance(item, str):
                upgraded[item] = {"name": item, "status": "active"}
        upgraded[slug] = entry
        data["workstreams"] = upgraded
    elif isinstance(ws, dict):
        ws[slug] = entry
    else:
        data["workstreams"] = {slug: entry}

    data.setdefault("schema_version", 1)

    try:
        with path.open("w", encoding="utf-8") as f:
            yaml.dump(data, f)
    except OSError as exc:
        print(f"error: failed to write {path}: {exc}", file=sys.stderr)
        return False
    return True


# ---- gh wrapper -----------------------------------------------------


def _gh_label_create(slug: str, config: dict) -> bool:
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
    if proc.returncode == 0:
        return True
    # `gh label create` exits non-zero on already-exists.
    if "already exists" in proc.stderr or "already exists" in proc.stdout:
        return True
    print(
        f"error: gh label create failed (exit {proc.returncode}).\nstderr: {proc.stderr.strip()}",
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
