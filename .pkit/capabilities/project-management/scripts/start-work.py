#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — start-work (DEC-026 workflow wrapper).

Transitions an issue Backlog → In Progress by creating the feature
branch + setting the assignee. Per DEC-026:

    start-work <N>

Gates per DEC-026:
  - Current user is a team member (DEC-021); open-mode degrades to no-op.
  - Issue not assigned to someone else (hard refusal points at handoff-issue).
  - Issue's current state can move to In Progress per workflow.yaml (or is
    already there). Checked before any mutation, so a refused move leaves no
    branch or assignee behind (#942). From Todo, move to Backlog first. The
    state is read as move-issue reads it (`_lib/issue_position`, #1242), and
    move-issue reads it again when it moves; a state that cannot be read
    refuses here, saying what failed.
  - If a branch exists, matches `<type>/<N>-<slug>` (idempotent).

Side-effects:
  - Creates branch `<type>/<N>-<kebab-slug>` (type from issue's type:*
    label; slug from the issue title).
  - Sets assignee to the current invoker.
  - Composes over `move-issue.py --to in-progress`. If that move still fails
    after the branch / assignee were written (a network error, or a state
    that changed since the check so the move is no longer legal), the run
    ends on a failure naming what it left behind.

Exit codes:
  0  in-progress
  1  membership refusal
  2  usage error / gate failure / illegal transition / unreadable state /
     gh failure
  *  a failed composed move-issue passes its exit code through
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

from ruamel.yaml import YAML

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import (
    axis_labels,
    bootstrap_gate,
    classification_rules,
    composed_move,
    default_branch,
    issue_position,
    session_guard,
)
from _lib import lifecycle_inference as infer
from _lib.gh import gh_get_issue, gh_run, load_adopter_config
from _lib.membership import (
    CAPABILITY_NAME,
    check_membership,
    resolve_capability_root,
    resolve_invoker_identity,
)

TARGET_STATE = "in-progress"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Start work on an issue: create the feature branch, set "
            "assignee, transition Backlog → In Progress. Composes over "
            "move-issue (per DEC-026)."
        ),
    )
    parser.add_argument("issue_number", type=int)
    parser.add_argument(
        "--capability-root",
        type=Path,
        default=None,
        help=f"Default: <repo-root>/.pkit/capabilities/{CAPABILITY_NAME}/.",
    )
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
    if not bootstrap_gate.enforce("start-work", capability_root=capability_root):
        return 2

    yaml_loader = YAML(typ="safe")
    config = load_adopter_config(capability_root)
    classification = _read_classification(capability_root, yaml_loader)
    workflow = _read_schema(capability_root, "workflow.yaml", yaml_loader)
    issue_types = _read_schema(capability_root, "issue-types.yaml", yaml_loader)
    members = _read_members(capability_root, yaml_loader)
    invoker = resolve_invoker_identity(config=config)
    membership = check_membership(members, invoker)
    if not membership.allowed:
        print(membership.refusal_message, file=sys.stderr)
        return 1

    # Foreign-repo mutation guard (COR-039 / ADR-034) — gate before the branch
    # create / assignee write / composed move-issue. A confirmed override is
    # threaded into move-issue so the gate is confirmed once, not twice.
    if not session_guard.enforce(override=args.allow_foreign_repo):
        return 1

    # Fetch issue.
    issue = _gh_get_issue(args.issue_number, config)
    if issue is None:
        return 2

    # Gate: not assigned to someone else.
    assignees = issue.get("assignees") or []
    other_assignees = [
        a.get("login")
        for a in assignees
        if isinstance(a, dict) and a.get("login") and a.get("login") != invoker.github_login
    ]
    if other_assignees:
        print(
            f"error: issue #{args.issue_number} is assigned to "
            f"{', '.join('@' + a for a in other_assignees)}. "
            f"Use `handoff-issue {args.issue_number}` to take ownership.",
            file=sys.stderr,
        )
        return 2

    title = str(issue.get("title", ""))
    labels = [
        lbl.get("name", "") if isinstance(lbl, dict) else str(lbl)
        for lbl in (issue.get("labels") or [])
    ]
    substrate_map = axis_labels.load_substrate_map(capability_root)

    # Gate: the move to In Progress is legal from where the issue is (#942).
    # Asked before the branch create / assignee write, so a refusal changes
    # nothing. The state is read as move-issue reads it (#1242).
    position = issue_position.read(
        issue,
        issue_position.ask_engine(args.issue_number),
        labels=labels,
        config=config,
        substrate_map=substrate_map,
    )
    refusal = composed_move.transition_refusal(
        "start-work",
        args.issue_number,
        issue,
        labels,
        position,
        target=TARGET_STATE,
        untouched="no branch, no assignee",
        workflow=workflow,
        issue_types=issue_types,
        classification=classification,
    )
    if refusal is not None:
        print(refusal, file=sys.stderr)
        return 2

    # Derive branch name from issue title + type axis. The type value resolves
    # through the ADR-026 read seam — a greenfield `type:*` label OR a brownfield
    # `[Prefix]` title — so the branch prefix is correct on both substrates.
    prefix = _derive_branch_prefix(labels, title, classification, substrate_map)
    if prefix is None:
        print(
            f"error: could not derive a branch prefix for issue #{args.issue_number}: "
            "no recognised type:* label and no known [Prefix] title. Expected a "
            "type value classification.yaml maps to a conv-type (via pr_type_mapping).",
            file=sys.stderr,
        )
        return 2
    slug = _slug_from_title(title)
    branch_name = f"{prefix}/{args.issue_number}-{slug}"

    # Idempotence: if a matching branch already exists locally, no-op.
    existing = _existing_branch_for_issue(args.issue_number)
    if existing is not None:
        if existing == branch_name:
            print(f"  branch {branch_name!r} already exists; idempotent skip")
        elif _branch_matches_shape(existing, args.issue_number):
            print(f"  branch {existing!r} exists with valid shape; using it")
            branch_name = existing
        else:
            print(
                f"error: branch {existing!r} exists for #{args.issue_number} "
                f"but doesn't match the expected shape `<type>/{args.issue_number}-<slug>`. "
                "Rename or delete the branch and re-run.",
                file=sys.stderr,
            )
            return 2

    # Branch base (#835): the default branch, or a DEC-013 integration branch when
    # the issue is marked — never the incidental HEAD. Shared with the PR-opening
    # verbs so the PR targets the branch this one was cut from (#903).
    try:
        base = infer.resolve_base_branch(config, str(issue.get("body") or ""))
    except default_branch.Unanswered as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"start-work: #{args.issue_number}")
    print(f"  branch:    {branch_name}")
    print(f"  base:      {base}")
    print(f"  assignee:  {invoker.github_login or '(unknown invoker)'}")

    if args.dry_run:
        print(
            f"(dry-run: would create branch off {base}, set assignee, and call move-issue --to "
            "in-progress.)"
        )
        return 0

    if not args.yes and sys.stdin.isatty():
        reply = input("Proceed? [y/N] ").strip().lower()
        if reply not in ("y", "yes"):
            print("aborted.", file=sys.stderr)
            return 0

    # Create branch (idempotent — git checkout -b on existing branch fails;
    # we check existence first).
    branch_created = False
    if existing is None:
        if not _create_branch(branch_name, base):
            return 2
        branch_created = True
    else:
        print(f"  branch {branch_name!r} already in repo; skipping creation")

    # Set assignee. "Written" means this run added it: an invoker who was
    # already assigned is not something this run left behind.
    already_assigned = any(
        isinstance(a, dict) and a.get("login") == invoker.github_login for a in assignees
    )
    assignee_written = False
    if invoker.github_login and not already_assigned:
        if _set_assignee(args.issue_number, invoker.github_login, config):
            assignee_written = True
        else:
            print(
                "[warn] branch created but failed to set assignee. "
                "Run `gh issue edit --add-assignee` manually and re-run move-issue.",
                file=sys.stderr,
            )

    # Compose over move-issue.
    rc = composed_move.invoke_move_issue(
        args.issue_number,
        TARGET_STATE,
        capability_root_arg=args.capability_root,
        allow_foreign_repo=args.allow_foreign_repo,
    )
    if rc != 0:
        print(
            composed_move.late_failure_message(
                "start-work",
                args.issue_number,
                TARGET_STATE,
                rc,
                left=_left_behind(
                    args.issue_number,
                    branch_name=branch_name if branch_created else None,
                    base=base,
                    assignee=invoker.github_login if assignee_written else None,
                ),
                nothing_left="This run created no branch and wrote no assignee.",
                reuses="the branch",
            ),
            file=sys.stderr,
        )
        return rc

    print(f"\n[ok] started work on #{args.issue_number} (branch: {branch_name})")
    return 0


# ---- helpers -----------------------------------------------------------


def _gh_get_issue(issue_number: int, config: dict) -> dict | None:
    return gh_get_issue(issue_number, config, fields="title,labels,assignees,state,body,milestone")


def _left_behind(
    issue_number: int,
    *,
    branch_name: str | None,
    base: str,
    assignee: str | None,
) -> list[tuple[str, str]]:
    """What this run changed before the composed move-issue failed, each with
    its undo: the branch it created and the assignee it wrote, where it did."""
    left: list[tuple[str, str]] = []
    if branch_name is not None:
        left.append(
            (
                f"branch {branch_name!r} (created and checked out)",
                f"git checkout {base} && git branch -D {branch_name}",
            )
        )
    if assignee is not None:
        left.append(
            (
                f"assignee @{assignee}",
                f"gh issue edit {issue_number} --remove-assignee {assignee}",
            )
        )
    return left


def _derive_branch_prefix(
    labels: list[str],
    title: str,
    classification: dict,
    substrate_map: axis_labels.SubstrateMap | None,
) -> str | None:
    """The conventional-commit branch prefix for an issue's type axis.

    Resolves the kit type *value* through the ADR-026 read seam, then maps it to
    the conv-type via classification.yaml's `pr_type_mapping` (the same table
    open-pr's PR-title derivation reads — one source, per COR-007):

    * label substrate ⇒ the value off the issue's labels, read THROUGH the map
      (`axis_labels.resolve_read("type", labels, substrate_map)`): the kit's own
      `type:*` label in greenfield, the adopter's remapped label where the map
      binds `type` to a label remap (#910);
    * brownfield `title-prefix` substrate ⇒ the value off the `[Prefix]` title
      (`classification_rules.kind_from_title`), where no `type:*` label exists.

    The label arm is tried first so greenfield stays byte-identical; the title
    arm is the fallback that fixes the brownfield break. `None` when neither arm
    resolves a value the mapping recognises (caller reports the error)."""
    kind = axis_labels.resolve_read("type", labels, substrate_map)
    if kind is None:
        kind = classification_rules.kind_from_title(title, classification)
    if kind is None:
        return None
    return classification_rules.conv_type_for_kind(kind, classification)


def _slug_from_title(title: str) -> str:
    """Derive a kebab-case slug from an issue title.

    Strips the `[Type]` prefix, removes punctuation, lowercases, joins
    words with hyphens. Trims to 5 words for branch-name readability.
    """
    # Strip [Type] prefix
    title = re.sub(r"^\[[^\]]+\]\s*", "", title)
    # Lowercase + replace non-alphanumeric with spaces, then collapse
    cleaned = re.sub(r"[^a-zA-Z0-9]+", " ", title).strip().lower()
    words = cleaned.split()[:5]  # cap at 5 words
    return "-".join(words) if words else "untitled"


def _existing_branch_for_issue(issue_number: int) -> str | None:
    """Find a local branch matching `*/<N>-*` for the issue. Returns first match or None."""
    try:
        proc = subprocess.run(
            ["git", "branch", "--list", "--format=%(refname:short)"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None
    if proc.returncode != 0:
        return None
    pattern = re.compile(rf"^[a-z]+/{issue_number}(-|$)")
    for line in proc.stdout.splitlines():
        line = line.strip()
        if pattern.match(line):
            return line
    return None


def _branch_matches_shape(name: str, issue_number: int) -> bool:
    return bool(re.match(rf"^[a-z]+/{issue_number}-[a-z0-9-]+$", name))


def _create_branch(name: str, base: str) -> bool:
    """Create `name` off `base` — the default branch or a DEC-013 integration
    branch (#835) — NOT off the incidental `HEAD`. It is cut from the commit the
    backbone resolves `base` to, as it resolves every branch named as a base
    (COR-054 point 2): the remote-tracking reference of its upstream, else
    `origin/<base>`, and the local branch only when there is no remote. The
    remote's copy is fetched first, best-effort, so the cut is up to date; a base
    that resolves nowhere refuses with the backbone's reason and fix — the branch
    is never cut from a guess."""
    _fetch("origin", base)
    try:
        found = default_branch.branch(base)
        remote, slash, _rest = found.ref.partition("/")
        if found.tip is not None and slash and remote != "origin" and _fetch(remote, base):
            found = default_branch.branch(base)  # the upstream is another remote's: fetched too
    except default_branch.Unanswered as exc:
        print(f"error: {exc}", file=sys.stderr)
        return False
    if found.tip is None:
        print(f"error: cannot cut {name!r} from {base!r}: {found.problem}", file=sys.stderr)
        return False
    proc = subprocess.run(
        ["git", "checkout", "-b", name, found.tip],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        print(
            f"error: git checkout -b {name!r} off {found.ref!r} failed: {proc.stderr.strip()}",
            file=sys.stderr,
        )
        return False
    print(f"  created branch: {name} (off {found.ref} at {found.tip[:12]})")
    return True


def _fetch(remote: str, branch: str) -> bool:
    """Fetch `branch` from `remote`, best-effort: whether it was fetched."""
    return (
        subprocess.run(
            ["git", "fetch", remote, branch],
            capture_output=True,
            text=True,
            check=False,
        ).returncode
        == 0
    )


def _set_assignee(issue_number: int, login: str, config: dict) -> bool:
    proc = gh_run(
        ["gh", "issue", "edit", str(issue_number), "--add-assignee", login],
        config,
        check=False,
    )
    if proc.returncode != 0:
        print(
            f"error: gh issue edit --add-assignee failed: {proc.stderr.strip()}",
            file=sys.stderr,
        )
        return False
    return True


def _read_members(capability_root: Path, yaml_loader: YAML) -> list[dict]:
    path = capability_root / "project" / "members.yaml"
    if not path.is_file():
        return []
    try:
        data = yaml_loader.load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return []
    members = data.get("members") if isinstance(data, dict) else None
    return members if isinstance(members, list) else []


def _read_classification(capability_root: Path, yaml_loader: YAML) -> dict:
    """The parsed classification.yaml, or {} when absent/unparseable.

    Feeds the type-value → conv-type lookup (`pr_type_mapping`) and the
    title-prefix reverse read the branch-prefix derivation goes through. A thin
    or missing schema degrades to {} — `_derive_branch_prefix` then resolves no
    prefix and the caller reports the derivation failure."""
    return _read_schema(capability_root, "classification.yaml", yaml_loader)


def _read_schema(capability_root: Path, name: str, yaml_loader: YAML) -> dict:
    """A parsed capability schema (`schemas/<name>`), or {} when absent or
    unparseable. A missing workflow.yaml therefore declares no legal moves and
    the transition gate refuses, as move-issue would."""
    path = capability_root / "schemas" / name
    if not path.is_file():
        return {}
    try:
        data = yaml_loader.load(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


if __name__ == "__main__":
    sys.exit(main())
