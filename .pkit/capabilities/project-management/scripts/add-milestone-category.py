#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — add-milestone-category (verb-subject per DEC-020).

Declares a Milestone category in `project/config.yaml`'s `milestone_categories:`
block, as [project-management:DEC-016-time-bound-containers] has a project do
before it files the first Milestone of it: the category's title format, with the
`{n}` and `{name}` placeholders `create-milestone` fills, the close trigger its
Milestones take unless they name their own, and an optional line saying what it
means. No category is declared by default.

Refuses a category already declared, and a value outside the rules, among them a
title format `create-milestone` could not file under, before it writes anything.
The block is written as text, every other byte of the file kept, and the file must
read back as it was with only the category added, or nothing is written
(`_lib/milestone_categories`).

Membership gate per DEC-021 runs at startup. A category is the project's own
configuration: the command asks at a terminal, `--yes` authorises it, and off a
terminal without `--yes` it refuses (#2015).

Self-contained via PEP 723; runs via
  uv run --script .pkit/capabilities/project-management/scripts/add-milestone-category.py <category> --title-format "..." --close-trigger <trigger>

Or via the dispatcher (per COR-021):
  pkit project-management add-milestone-category <category> --title-format "..." --close-trigger <trigger>

Exit codes:
  0  declared (or dry-run reported), or the person declined at the prompt
  1  membership refusal / a value outside the rules / a category already declared
     / off a terminal without --yes
  2  usage error (capability not found; not bootstrapped) / a configuration the
     command cannot write the category into
"""  # noqa: E501 — a usage line is a command, kept whole

from __future__ import annotations

import argparse
import shlex
import sys
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import bootstrap_gate, consent, session_guard
from _lib import milestone_categories as categories
from _lib.gh import load_adopter_config
from _lib.membership import (
    CAPABILITY_NAME,
    check_membership,
    resolve_capability_root,
    resolve_invoker_identity,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Declare a Milestone category in project/config.yaml's "
            "milestone_categories: block per DEC-016, so create-milestone can "
            "file Milestones in it."
        ),
    )
    parser.add_argument(
        "category",
        help="The category's name, which `create-milestone <category>` takes.",
    )
    parser.add_argument(
        "--title-format",
        required=True,
        help=(
            "The title its Milestones take, with the {n} (number) and {name} "
            'placeholders create-milestone fills, e.g. "Sprint {n}: {name}".'
        ),
    )
    parser.add_argument(
        "--close-trigger",
        required=True,
        choices=categories.CLOSE_TRIGGERS,
        help=(
            "The close trigger its Milestones take unless one names its own "
            "(create-milestone --close-trigger)."
        ),
    )
    parser.add_argument(
        "--description",
        default=None,
        help="One line, at most 200 chars, saying what the category means here.",
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
    parser.add_argument("--dry-run", action="store_true", help="Print the plan; do not write.")
    parser.add_argument("--yes", action="store_true", help="Skip the confirmation prompt.")
    session_guard.add_override_argument(parser)
    args = parser.parse_args()

    capability_root = resolve_capability_root(args.capability_root)
    if capability_root is None:
        print(f"error: {CAPABILITY_NAME} capability not found.", file=sys.stderr)
        return 2

    # Prerequisite gate (#747): refuse on an un-bootstrapped project rather
    # than operating on assumed defaults. See _lib/bootstrap_gate.py.
    if not bootstrap_gate.enforce("add-milestone-category", capability_root=capability_root):
        return 2

    yaml_loader = YAML(typ="safe")
    config = load_adopter_config(capability_root)
    members = _read_members(capability_root, yaml_loader)
    invoker = resolve_invoker_identity(config=config)
    membership = check_membership(members, invoker)
    if not membership.allowed:
        print(membership.refusal_message, file=sys.stderr)
        return 1

    # Foreign-repo mutation guard (COR-039 / ADR-034). The configuration is
    # resolved from the cwd-walk in resolve_capability_root, so a `cd /B` would
    # write into another repository than the session's; gate that before writing.
    if not session_guard.enforce(override=args.allow_foreign_repo):
        return 1

    problems = categories.entry_problems(
        args.category,
        title_format=args.title_format,
        close_trigger=args.close_trigger,
        description=args.description,
    )
    if problems:
        for problem in problems:
            print(f"[refused] {problem}", file=sys.stderr)
        return 1

    path = capability_root / categories.CONFIG_RELATIVE
    declared = categories.declared(_read_yaml(path, yaml_loader))
    if args.category in declared:
        print(
            f"[refused] milestone category {args.category!r} is already declared in {path}.",
            file=sys.stderr,
        )
        return 1

    value = categories.entry(args.title_format, args.close_trigger, args.description)
    print(f"add-milestone-category: {args.category}")
    print(f"  title format:  {value['title_format']}")
    print(
        f"  close trigger: {value['close_trigger_default']}  (a Milestone's own line overrides it)"
    )
    if "description" in value:
        print(f"  description:   {value['description']}")
    print(f"  target file:   {path}")

    if args.dry_run:
        print("\n[dry-run] nothing written.")
        return 0
    stop = consent.authorise(
        "Proceed? [y/N] ",
        yes=args.yes,
        step=f"Declaring milestone category {args.category!r}",
        verb="add-milestone-category",
    )
    if stop is not None:
        return stop

    try:
        categories.declare(path, args.category, value)
    except categories.Refused as exc:
        print(f"[refused] {exc}", file=sys.stderr)
        return 2

    print(f"\n[ok] declared milestone category {args.category!r}.")
    print(
        "  → file its first Milestone: "
        f"pkit pm create-milestone {shlex.quote(args.category)} --name '<name>'"
    )
    return 0


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
