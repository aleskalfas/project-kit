#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — split-workstream (verb-subject per DEC-020 + DEC-018).

Splits one workstream into 2–5 new workstreams. Per DEC-018:

  * Source must exist.
  * 2–5 new slugs supplied via `--into <slug>` (repeatable), each
    checked against DEC-018's slug rules in full.
  * New slugs must not already exist.
  * Source workstream is removed; new slugs are added (default
    name = slug, active status).
  * Each issue of the source is triaged: the script asks, of each one,
    which new slug it moves to. `--assign <issue>=<slug>` answers for one
    issue up front, and `--default <slug>` answers for every issue not
    otherwise answered (and is the answer an empty reply takes). A shell
    that cannot answer, or `--yes`, takes `--assign` and `--default`
    alone, and refuses before any change if an issue is left unanswered.
  * The split itself is confirmed at a terminal, or by `--yes`. Off a
    terminal, without `--yes`, nobody is there to confirm it, so it is
    refused before any change, once the plan is shown (#2015).
  * The issues are read from the substrate that carries the axis: the
    `workstream:<source>` label, or the cards whose `Workstream` value is
    the source where a board carries it. Each moves to its answer, the
    new labels or options are created first, and the source's label or
    option is deleted once every issue has moved.
  * `--include-github-bodies` opts into rewriting references: each typed
    `workstream:<source>` and `[workstream:<source>]`, in the tracked
    files and in issue, pull-request and comment bodies, leaving what a
    merge leaves (the `.pkit/` tree, the changelog, the pending changesets
    and, without admin rights, someone else's comment). A body on a
    triaged issue takes that issue's answer; any other reference is
    asked about, or takes `--default`, or is left with a warning. A run
    with no interactive shell to confirm each one refuses up front unless
    `--yes` batches the confirmations.

The substrate is changed before the file, and the file only once every
issue has moved, so a re-run after a failure finishes the split.

Membership gate per DEC-021 runs at startup.

Self-contained via PEP 723; runs via
  uv run --script .pkit/capabilities/project-management/scripts/split-workstream.py --source cli --into cli-tools --into cli-rendering

Or via the dispatcher (per COR-021):
  pkit project-management split-workstream --source cli --into a --into b

Exit codes:
  0  split (or dry-run reported)
  1  membership refusal / validation refusal / an issue left untriaged / off
     a terminal without --yes
  2  usage error
  3  gh failure (issues unreadable; a move, a delete or a rewrite failed)
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
    validate_slug,
    workstreams_path,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Split a workstream into 2–5 new slugs.",
    )
    parser.add_argument("--source", required=True, help="Source slug to split.")
    parser.add_argument(
        "--into",
        action="append",
        required=True,
        metavar="SLUG",
        help="New slug to create. Repeat for each split target (2–5 total).",
    )
    parser.add_argument(
        "--default",
        default=None,
        help=(
            "New slug an issue moves to when nothing else answers for it, and the "
            "answer an empty reply takes in the triage."
        ),
    )
    parser.add_argument(
        "--assign",
        action="append",
        default=[],
        metavar="ISSUE=SLUG",
        help="Move one issue of the source to one new slug, without asking. Repeatable.",
    )
    parser.add_argument(
        "--skip-labels",
        action="store_true",
        help="Skip the gh label creation, retag and delete steps.",
    )
    parser.add_argument(
        "--include-github-bodies",
        action="store_true",
        help=(
            "Rewrite the typed references to the source, in the tracked files and in "
            "issue, pull-request and comment bodies."
        ),
    )
    parser.add_argument("--capability-root", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", action="store_true")
    session_guard.add_override_argument(parser)
    args = parser.parse_args()

    if not (2 <= len(args.into) <= 5):
        print(
            f"[refused] --into requires 2–5 values; got {len(args.into)}.",
            file=sys.stderr,
        )
        return 1

    for slug in args.into:
        err = validate_slug(slug)
        if err:
            print(f"[refused] new {err}", file=sys.stderr)
            return 1
    if len(set(args.into)) != len(args.into):
        print("[refused] --into names a slug more than once.", file=sys.stderr)
        return 1
    if args.source in args.into:
        print("[refused] --into names the source itself.", file=sys.stderr)
        return 1

    if args.default is not None and args.default not in args.into:
        print(
            f"[refused] --default={args.default!r} is not in the --into set.",
            file=sys.stderr,
        )
        return 1

    assigned, err = _parse_assignments(args.assign, args.into)
    if err:
        print(f"[refused] {err}", file=sys.stderr)
        return 1

    if args.include_github_bodies and workstream_sync.references_need_yes(args.yes, args.dry_run):
        print(
            "[refused] --include-github-bodies asks before each file and body it rewrites, "
            "and no interactive shell is here to ask. Pass --yes to confirm them all. "
            "Nothing was changed.",
            file=sys.stderr,
        )
        return 1

    capability_root = resolve_capability_root(args.capability_root)
    if capability_root is None:
        print(f"error: {CAPABILITY_NAME} capability not found.", file=sys.stderr)
        return 2

    # Prerequisite gate (#747): refuse on an un-bootstrapped project rather
    # than operating on assumed defaults. See _lib/bootstrap_gate.py.
    if not bootstrap_gate.enforce("split-workstream", capability_root=capability_root):
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
    if args.source not in existing:
        print(
            f"[refused] source {args.source!r} not found in workstreams.yaml.",
            file=sys.stderr,
        )
        return 1
    overlap = [s for s in args.into if s in existing]
    if overlap:
        print(
            f"[refused] new slugs already exist: {', '.join(overlap)}.",
            file=sys.stderr,
        )
        return 1

    config = _read_yaml(capability_root / "project" / "config.yaml", yaml_loader)

    # Whether the kit's own `workstream:*` labels may be CREATED, RETAGGED and
    # DELETED here — asked of the carriage accessor, never of the board flag alone
    # ([project-management:DEC-051-axis-carriage-activation] decision point 4). A
    # flag-only test would let a board adopter whose map binds `workstream` to
    # their own labels reach both `gh label create` (an unmanaged label) and
    # `gh label delete` (a name the kit never owned).
    substrate_map = axis_labels.load_substrate_map(capability_root)
    kit_label_note = axis_carriage.kit_label_mutation_note("workstream", config, substrate_map)
    kit_labels = kit_label_note is None and not args.skip_labels
    on_board = axis_carriage.is_board_carried("workstream", config, substrate_map)
    source_label = axis_labels.label("workstream", args.source)

    # The issues of the source, from the substrate that carries the axis.
    board = None
    issues: tuple[workstream_sync.Carrier, ...] = ()
    if kit_labels:
        read = workstream_sync.issues_with_label(source_label, config, gh_call=gh_run)
        if not read.ok:
            print(
                f"[error] could not list the issues of {args.source!r}, so nothing was "
                f"changed: {read.error}",
                file=sys.stderr,
            )
            return 3
        issues = read.carriers
    elif on_board:
        field_read = workstream_sync.read_board_field(config)
        if field_read.error is not None:
            print(f"[error] could not read the board: {field_read.error}", file=sys.stderr)
            return 3
        if field_read.field is None:
            print(f"[refused] {field_read.problem}", file=sys.stderr)
            return 1
        board = field_read.field
        read = workstream_sync.board_carriers(board, args.source, config)
        if not read.ok:
            print(
                f"[error] could not list the cards of {args.source!r}, so nothing was "
                f"changed: {read.error}",
                file=sys.stderr,
            )
            return 3
        issues = read.carriers

    stray = sorted(set(assigned) - {i.number for i in issues})
    if stray:
        print(
            f"[refused] --assign names issue(s) that do not carry {args.source!r}: "
            f"{', '.join(f'#{n}' for n in stray)}.",
            file=sys.stderr,
        )
        return 1

    # The triage: one answer per issue (DEC-018's per-issue triage loop).
    interactive = sys.stdin.isatty() and not args.yes and not args.dry_run
    answers: dict[int, str] = {}
    untriaged: list[workstream_sync.Carrier] = []
    for issue in issues:
        if issue.number is None:
            continue
        if issue.number in assigned:
            answers[issue.number] = assigned[issue.number]
        elif interactive:
            answer = _ask(f"#{issue.number} {issue.title}", args.into, args.default)
            if answer is None:
                print("aborted; nothing was changed.", file=sys.stderr)
                return 0
            answers[issue.number] = answer
        elif args.default is not None:
            answers[issue.number] = args.default
        else:
            untriaged.append(issue)
    if untriaged and not args.dry_run:
        print(
            f"[refused] {len(untriaged)} issue(s) of {args.source!r} have no workstream to "
            f"move to: {', '.join(f'#{i.number}' for i in untriaged)}. Answer each in an "
            "interactive shell, or pass --assign <issue>=<slug> or --default <slug>. "
            "Nothing was changed.",
            file=sys.stderr,
        )
        return 1

    print(f"split-workstream: {args.source} → {', '.join(args.into)}")
    if kit_labels:
        print(f"  source label uses: {len(issues)} issue(s)")
    elif board is not None:
        print(f"  source cards on the board: {len(issues)}")
    elif kit_label_note is not None:
        print(f"  source label uses: n/a — {kit_label_note}")
    for issue in issues:
        target = answers.get(issue.number) if issue.number is not None else None
        print(f"  #{issue.number} {issue.title} → {target or '<to triage>'}")
    if args.include_github_bodies:
        print(
            f"  references: rewrite each typed reference to `{source_label}`, in the tracked "
            "files and in issue, pull-request and comment bodies"
        )

    if args.dry_run:
        print("\n[dry-run] nothing written; no gh invocation.")
        return 0
    stop = consent.authorise(
        "Proceed with split? [y/N] ",
        yes=args.yes,
        step=f"Splitting workstream {args.source!r}",
        verb="split-workstream",
    )
    if stop is not None:
        return stop

    failures: list[str] = []

    if kit_labels:
        for slug in args.into:
            if not _gh_label_create(slug, config):
                failures.append(f"`{axis_labels.label('workstream', slug)}` was not created")
        if not failures:
            for issue in issues:
                if issue.number is None:
                    continue
                error = workstream_sync.retag_issue(
                    issue.number,
                    source_label,
                    axis_labels.label("workstream", answers[issue.number]),
                    config,
                    gh_call=gh_run,
                )
                if error is not None:
                    failures.append(f"#{issue.number}: {error}")
        if not failures:
            error = _gh_label_delete(source_label, config)
            if error is not None:
                failures.append(f"`{source_label}`: {error}")

    if board is not None:
        failures += _split_board(
            config, board, args.source, args.into, issues, answers, args.default
        )

    if failures:
        for line in failures:
            print(f"[error] {line}", file=sys.stderr)
        print(
            "[error] workstreams.yaml was not changed. Re-run the split to finish it.",
            file=sys.stderr,
        )
        return 3

    # File mutation, once every issue has moved.
    ws = data.get("workstreams")
    if isinstance(ws, list):
        new_list = [item for item in ws if item != args.source]
        new_list.extend(args.into)
        data["workstreams"] = new_list
    elif isinstance(ws, dict):
        ws.pop(args.source, None)
        for slug in args.into:
            ws[slug] = {"name": slug, "status": "active"}
    try:
        with path.open("w", encoding="utf-8") as f:
            yaml.dump(data, f)
    except OSError as exc:
        print(f"error: failed to write {path}: {exc}", file=sys.stderr)
        return 2

    if args.include_github_bodies:
        versions = provenance.read_versions(capability_root)
        root = workstream_sync.repo_root(capability_root)

        def target(number: int | None, where: str) -> str | None:
            slug = answers.get(number) if number is not None else None
            if slug is None and sys.stdin.isatty() and not args.yes:
                slug = _ask(f"a reference in {where}", args.into, args.default)
            if slug is None:
                slug = args.default
            return axis_labels.label("workstream", slug) if slug else None

        outcome = workstream_sync.rewrite_everywhere(
            source_label,
            target=target,
            confirm=workstream_sync.confirm_each(args.yes),
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
        if outcome.failed:
            for line in outcome.failed:
                print(f"[error] {line}", file=sys.stderr)
            return 3

    print(f"\n[ok] split workstream {args.source!r} into {', '.join(args.into)}.")
    return 0


def _parse_assignments(raw: list[str], into: list[str]) -> tuple[dict[int, str], str | None]:
    """`--assign` values as {issue number: slug}, or the reason one is malformed."""
    assigned: dict[int, str] = {}
    for item in raw:
        number, sep, slug = item.partition("=")
        number = number.strip().lstrip("#")
        if not sep or not number.isdigit():
            return {}, f"--assign {item!r} is not <issue>=<slug>."
        if slug not in into:
            return {}, f"--assign {item!r} names {slug!r}, which is not in the --into set."
        if int(number) in assigned and assigned[int(number)] != slug:
            return {}, f"--assign moves #{number} to two workstreams."
        assigned[int(number)] = slug
    return assigned, None


def _ask(subject: str, into: list[str], default: str | None) -> str | None:
    """Ask which new slug `subject` moves to; None when the shell gives no answer."""
    choices = "  ".join(f"[{i}] {slug}" for i, slug in enumerate(into, start=1))
    suffix = f" (Enter: {default})" if default else ""
    while True:
        try:
            reply = input(f"{subject}\n  {choices}{suffix}: ").strip()
        except EOFError:
            return None
        if not reply and default:
            return default
        if reply.isdigit() and 1 <= int(reply) <= len(into):
            return into[int(reply) - 1]
        if reply in into:
            return reply
        print(f"  answer with a number from 1 to {len(into)}, or a slug.", file=sys.stderr)


def _split_board(
    config: dict,
    board: workstream_sync.BoardField,
    source: str,
    into: list[str],
    cards: tuple[workstream_sync.Carrier, ...],
    answers: dict[int, str],
    default: str | None,
) -> list[str]:
    """Give the board the new options, move each card to its answer, drop the source's."""
    missing = [slug for slug in into if workstream_sync.find_option(board, slug) is None]
    if missing:
        options = list(board.options) + [{"name": slug, "description": ""} for slug in missing]
        result = workstream_sync.write_options(config, board, options)
        if not result.ok:
            return [f"the board's new options: {result.error}"]
        read = workstream_sync.read_board_field(config)
        if read.field is None:
            return [f"the board after adding its options: {read.error or read.problem}"]
        board = read.field
    failures: list[str] = []
    for card in cards:
        if card.item_id is None:
            continue
        # A draft card holds no issue to triage, so it takes --default.
        slug = answers.get(card.number) if card.number is not None else default
        if slug is None:
            failures.append(f"the draft card {card.title!r} has no workstream; pass --default")
            continue
        option = workstream_sync.find_option(board, slug)
        if option is None:
            failures.append(f"the board offers no option `{slug}`")
            continue
        result = workstream_sync.set_card_option(config, board, card.item_id, option["id"])
        if not result.ok:
            failures.append(f"card of #{card.number}: {result.error}")
    if not failures and workstream_sync.find_option(board, source) is not None:
        result = workstream_sync.write_options(
            config, board, workstream_sync.options_without(board, [source])
        )
        if not result.ok:
            failures.append(f"the board's option `{source}`: {result.error}")
    return failures


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
    return proc.returncode == 0 or "already exists" in (proc.stderr or "")


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
