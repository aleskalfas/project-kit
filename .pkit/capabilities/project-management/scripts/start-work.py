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
    branch or assignee behind (#942). From Todo, move to Backlog first.
  - If a branch exists, matches `<type>/<N>-<slug>` (idempotent).

Side-effects:
  - Creates branch `<type>/<N>-<kebab-slug>` (type from issue's type:*
    label; slug from the issue title).
  - Sets assignee to the current invoker.
  - Composes over `move-issue.py --to in-progress`. If that move still fails
    after the branch / assignee were written (e.g. a network error), the run
    ends on a failure naming what it left behind.

Exit codes:
  0  in-progress
  1  membership refusal
  2  usage error / gate failure / illegal transition / gh failure
  *  a failed composed move-issue passes its exit code through
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from ruamel.yaml import YAML

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import (  # noqa: E402
    axis_labels,
    bootstrap_gate,
    classification_rules,
    lifecycle_inference as infer,
    session_guard,
)
from _lib.gh import gh_get_issue, gh_run, load_adopter_config  # noqa: E402
from _lib.membership import (  # noqa: E402
    CAPABILITY_NAME,
    check_membership,
    resolve_capability_root,
    resolve_invoker_identity,
)
from _lib.structural_type import infer_structural_type  # noqa: E402

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
        "--capability-root", type=Path, default=None,
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
        a.get("login") for a in assignees
        if isinstance(a, dict)
        and a.get("login")
        and a.get("login") != invoker.github_login
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
    # nothing. Same position read and transition table move-issue consults.
    refusal = _transition_refusal(
        args.issue_number,
        issue,
        labels,
        workflow=workflow,
        issue_types=issue_types,
        classification=classification,
        substrate_map=substrate_map,
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
    base = infer.resolve_base_branch(config, str(issue.get("body") or ""))

    print(f"start-work: #{args.issue_number}")
    print(f"  branch:    {branch_name}")
    print(f"  base:      {base}")
    print(f"  assignee:  {invoker.github_login or '(unknown invoker)'}")

    if args.dry_run:
        print(f"(dry-run: would create branch off {base}, set assignee, and call move-issue --to in-progress.)")
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
        isinstance(a, dict) and a.get("login") == invoker.github_login
        for a in assignees
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
    rc = _invoke_move_issue(
        args.issue_number, TARGET_STATE, args.capability_root, args.allow_foreign_repo
    )
    if rc != 0:
        print(
            _late_failure_message(
                args.issue_number,
                rc,
                branch_name=branch_name if branch_created else None,
                base=base,
                assignee=invoker.github_login if assignee_written else None,
            ),
            file=sys.stderr,
        )
        return rc

    print(f"\n[ok] started work on #{args.issue_number} (branch: {branch_name})")
    return 0


# ---- helpers -----------------------------------------------------------


def _gh_get_issue(issue_number: int, config: dict) -> dict | None:
    return gh_get_issue(
        issue_number, config, fields="title,labels,assignees,state,body,milestone"
    )


def _transition_refusal(
    issue_number: int,
    issue: dict,
    labels: list[str],
    *,
    workflow: dict,
    issue_types: dict,
    classification: dict,
    substrate_map: axis_labels.SubstrateMap | None,
) -> str | None:
    """Why the composed `move-issue --to in-progress` would refuse, or None.

    Reads the issue's position through `lifecycle_inference.infer_current_state`
    and its structural type through `infer_structural_type` (the readers
    move-issue uses), and the legal moves through
    `lifecycle_inference.legal_targets` (the table move-issue refuses on). An
    issue already In Progress passes: move-issue treats that as an idempotent
    no-op, so re-running start-work still works. When one intermediate move
    leads on to In Progress (Todo → Backlog), the refusal names it."""
    title = str(issue.get("title", ""))
    structural_type = infer_structural_type(
        title, issue_types, classification=classification, labels=labels
    )
    if structural_type is None:
        return (
            f"error: cannot determine structural type for issue #{issue_number}: "
            f"title {title!r} matches no known [Type] prefix and no `type:*` "
            "kind label is present. Nothing was changed.\n"
            "  → Restore the issue's title prefix (e.g. [Task]) and re-run."
        )
    current = infer.infer_current_state(
        state=str(issue.get("state", "")).lower(),
        milestone=issue.get("milestone") or {},
        labels=labels,
        substrate_map=substrate_map,
    )
    if current == TARGET_STATE:
        return None
    targets = infer.legal_targets(workflow, current, structural_type)
    if TARGET_STATE in targets:
        return None
    lines = [
        f"[refused] start-work #{issue_number}: the issue is in {current!r}, and "
        f"workflow.yaml declares no move {current!r} → {TARGET_STATE!r} for "
        f"{structural_type!r}. Nothing was changed (no branch, no assignee).",
    ]
    stepping_stones = [
        s for s in targets
        if TARGET_STATE in infer.legal_targets(workflow, s, structural_type)
    ]
    if stepping_stones:
        lines.append(
            f"  → move it first: `move-issue {issue_number} --to {stepping_stones[0]}`, "
            f"then re-run `start-work {issue_number}`."
        )
    else:
        lines.append(
            f"  legal targets from {current!r}: "
            f"{', '.join(targets) if targets else '<none>'}"
        )
    return "\n".join(lines)


def _late_failure_message(
    issue_number: int,
    rc: int,
    *,
    branch_name: str | None,
    base: str,
    assignee: str | None,
) -> str:
    """The closing failure when the composed move-issue fails after mutating.

    Names each thing this run left behind (the branch it created, the assignee
    it wrote) so the caller can retry or undo. The output must not end on the
    branch-creation line as if the run had succeeded (#942)."""
    lines = [
        f"\n[failed] start-work #{issue_number}: move-issue --to {TARGET_STATE} "
        f"failed (exit {rc}); the issue did not move.",
    ]
    left = []
    if branch_name is not None:
        left.append(
            f"  - branch {branch_name!r} (created and checked out). Undo: "
            f"`git checkout {base} && git branch -D {branch_name}`"
        )
    if assignee is not None:
        left.append(
            f"  - assignee @{assignee}. Undo: "
            f"`gh issue edit {issue_number} --remove-assignee {assignee}`"
        )
    if left:
        lines.append("  Left behind by this run:")
        lines.extend(left)
    else:
        lines.append("  This run created no branch and wrote no assignee.")
    lines.append(
        f"  Fix the cause above and re-run `start-work {issue_number}` "
        "(it reuses the branch)."
    )
    return "\n".join(lines)


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
            capture_output=True, text=True, check=False,
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
    branch (#835) — NOT off the incidental `HEAD`. The base is fetched first so the
    branch is cut from an up-to-date ref; fetch failure (e.g. offline) degrades to
    the local `base` ref."""
    fetched = subprocess.run(
        ["git", "fetch", "origin", base],
        capture_output=True, text=True, check=False,
    ).returncode == 0
    start_point = f"origin/{base}" if fetched else base
    proc = subprocess.run(
        ["git", "checkout", "-b", name, start_point],
        capture_output=True, text=True, check=False,
    )
    if proc.returncode != 0 and start_point != base:
        # origin/<base> unresolvable (e.g. base not on origin) — fall back to the
        # local base ref before giving up.
        start_point = base
        proc = subprocess.run(
            ["git", "checkout", "-b", name, base],
            capture_output=True, text=True, check=False,
        )
    if proc.returncode != 0:
        print(
            f"error: git checkout -b {name!r} off {base!r} failed: "
            f"{proc.stderr.strip()}",
            file=sys.stderr,
        )
        return False
    print(f"  created branch: {name} (off {start_point})")
    return True


def _set_assignee(issue_number: int, login: str, config: dict) -> bool:
    proc = gh_run(
        ["gh", "issue", "edit", str(issue_number), "--add-assignee", login],
        config, check=False,
    )
    if proc.returncode != 0:
        print(
            f"error: gh issue edit --add-assignee failed: {proc.stderr.strip()}",
            file=sys.stderr,
        )
        return False
    return True


def _invoke_move_issue(
    issue_number: int,
    target: str,
    capability_root_arg: Path | None,
    allow_foreign_repo: bool,
) -> int:
    cmd = [
        sys.executable,
        str(_HERE / "move-issue.py"),
        str(issue_number),
        "--to", target,
        "--yes",
    ]
    if allow_foreign_repo:
        cmd.append("--allow-foreign-repo")
    if capability_root_arg is not None:
        cmd += ["--capability-root", str(capability_root_arg)]
    proc = subprocess.run(cmd, check=False)
    return proc.returncode


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
