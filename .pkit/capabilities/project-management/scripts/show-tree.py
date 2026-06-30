#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — show-tree (verb-subject per DEC-020).

PM-operational diagnostic. Walks the hierarchy:

  Milestones → EPICs → Features / Umbrellas → Tasks → sub-tasks + PRs

Surfaces orphans:
  * Open issues without a parent that aren't EPICs.
  * Tasks not under Feature / Umbrella / EPIC.
  * Open PRs not linked to any Task via Closes #N.
  * For board-substrate adopters: open issues not on the configured
    Projects v2 board (best-effort; checked when --board-check is on).

Output formats: text tree (default), JSON, markdown.

Read-only. Membership gate per DEC-021 runs at startup (read mode).

Self-contained via PEP 723; runs via
  uv run --script .pkit/capabilities/project-management/scripts/show-tree.py

Or via the dispatcher (per COR-021):
  pkit project-management show-tree --json

Exit codes:
  0  rendered cleanly
  1  membership refusal
  2  usage error / gh failure
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import axis_labels  # noqa: E402
from _lib import containment  # noqa: E402
from _lib import session_guard  # noqa: E402
from _lib.gh import gh_run, load_adopter_config  # noqa: E402
from _lib.membership import (  # noqa: E402
    CAPABILITY_NAME,
    check_membership,
    resolve_capability_root,
    resolve_invoker_identity,
)


CLOSING_KEYWORD_RE = re.compile(
    r"\b(?:closes|fixes|resolves)\s+#(\d+)", re.IGNORECASE
)


@dataclass
class Issue:
    number: int
    title: str
    state: str
    body: str
    labels: list[str]
    milestone: str | None
    structural_type: str | None  # epic / feature / umbrella / task / None
    parent_number: int | None = None
    children: list[int] = field(default_factory=list)
    # Per-child substrate provenance from the containment read-seam: maps a
    # child number to "native" / "textual" (native-wins on conflict, DEC-005).
    child_substrate: dict[int, str] = field(default_factory=dict)


@dataclass
class PR:
    number: int
    title: str
    state: str
    closes: list[int]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Walk the methodology hierarchy (Milestones → EPICs → Features/"
            "Umbrellas → Tasks → sub-tasks + PRs) and report orphans."
        ),
    )
    parser.add_argument(
        "--state",
        choices=["open", "closed", "all"],
        default="open",
        help="Issue/PR state filter (default: open).",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json", "markdown"],
        default="text",
        help="Output format (default: text tree).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=500,
        help=(
            "Max issues to fetch from gh (default: 500). Increase for "
            "large repos."
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
        "--refresh-children-views",
        action="store_true",
        help=(
            "TEXTUAL-mode only: refresh each parent's render-on-demand "
            "do-not-edit children comment (DEC-039 D4 / ADR-035) by full "
            "overwrite — the explicit refresh path for the parent-side children "
            "view where the tracker has no native sub-issues panel. Idempotent "
            "(unchanged child sets are skipped); a no-op in native mode. "
            "WRITES comments — refused under a foreign-repo session."
        ),
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

    issues_raw = _gh_list_issues(state=args.state, limit=args.limit, config=config)
    if issues_raw is None:
        return 2
    prs_raw = _gh_list_prs(state=args.state, limit=args.limit, config=config)
    if prs_raw is None:
        return 2

    issues = _parse_issues(issues_raw, issue_types)
    prs = _parse_prs(prs_raw)

    # Build parent relationships through the containment read-seam (native-where-
    # present / textual-otherwise / native-wins per DEC-005) — show-tree does NOT
    # parse body parent-refs directly (ADR-026 one-read-seam discipline).
    _link_parents(issues, config)

    orphans = _detect_orphans(issues, prs)
    tree = _build_tree(issues)

    # Explicit refresh path for the render-on-demand textual children view
    # (DEC-039 D4 / ADR-035 section 4). In `textual` mode each parent has no
    # native sub-issues panel, so its parent-side children view is a generated
    # do-not-edit comment refreshed by full overwrite. show-tree already resolved
    # every parent's children through the seam (above); --refresh-children-views
    # writes those resolutions back as comments. A WRITE — gated by the
    # foreign-repo session guard; a no-op in native mode (the writer's mode gate).
    if args.refresh_children_views:
        if not session_guard.enforce(override=args.allow_foreign_repo):
            return 1
        _refresh_children_views(issues, capability_root, config)

    if args.format == "json":
        out = {
            "issues": {
                str(num): _issue_to_dict(issues[num]) for num in issues
            },
            "prs": [
                {"number": p.number, "title": p.title, "state": p.state, "closes": p.closes}
                for p in prs.values()
            ],
            "orphans": orphans,
            "tree_roots": [n for n in tree if issues[n].parent_number is None],
        }
        print(json.dumps(out, indent=2))
    elif args.format == "markdown":
        _print_markdown(issues, prs, orphans, tree)
    else:
        _print_text(issues, prs, orphans, tree)

    return 0


# ---- parsing --------------------------------------------------------


def _parse_issues(raw: list, issue_types: dict) -> dict[int, Issue]:
    out: dict[int, Issue] = {}
    for r in raw:
        if not isinstance(r, dict):
            continue
        number = r.get("number")
        if not isinstance(number, int):
            continue
        title = str(r.get("title", ""))
        labels = [
            lbl.get("name", "") if isinstance(lbl, dict) else str(lbl)
            for lbl in (r.get("labels") or [])
        ]
        milestone = r.get("milestone") or {}
        ms_title = milestone.get("title") if isinstance(milestone, dict) else None
        out[number] = Issue(
            number=number,
            title=title,
            state=str(r.get("state", "")).lower(),
            body=str(r.get("body") or ""),
            labels=labels,
            milestone=ms_title,
            structural_type=_infer_structural_type(title, issue_types),
        )
    return out


def _parse_prs(raw: list) -> dict[int, PR]:
    out: dict[int, PR] = {}
    for r in raw:
        if not isinstance(r, dict):
            continue
        number = r.get("number")
        if not isinstance(number, int):
            continue
        body = str(r.get("body") or "")
        closes = sorted(
            {int(m.group(1)) for m in CLOSING_KEYWORD_RE.finditer(body)}
        )
        out[number] = PR(
            number=number,
            title=str(r.get("title", "")),
            state=str(r.get("state", "")).lower(),
            closes=closes,
        )
    return out


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


def _link_parents(issues: dict[int, Issue], config: dict) -> None:
    """Populate parent_number + children + child_substrate via the containment
    read-seam (``_lib.containment.resolve_children``).

    For each candidate parent the seam resolves its children native-where-present
    / textual-otherwise with native-wins (DEC-005); show-tree never parses body
    parent-refs itself (ADR-026 one-read-seam discipline). The corpus
    (``{number: body}``) is handed to the seam so the textual side costs no API
    calls — the seam's only per-call cost is one native ``…/sub_issues`` GET per
    candidate parent.

    Cost bound: the native read is issued only for *candidate parents* — issues
    that are structural containers (epic/feature/umbrella/task) OR are named as a
    parent by some issue's textual ref — not for every corpus issue. A leaf that
    is neither cannot hold children under the methodology, so skipping its native
    read cannot drop a child. (The write seam always writes BOTH substrates, so a
    native sub-issue also carries a textual ref and thus marks its parent a
    candidate; a hypothetical native-only child under an otherwise-leaf parent is
    the sole uncovered edge — accepted to keep the walk from issuing one native
    call per corpus issue.)
    """
    corpus = {num: issue.body for num, issue in issues.items()}
    textual_parents = {
        parent
        for body in corpus.values()
        for parent in (_first_parent_ref(body),)
        if parent is not None
    }
    container_types = {"epic", "feature", "umbrella", "task"}
    for num, issue in issues.items():
        is_candidate = (
            issue.structural_type in container_types or num in textual_parents
        )
        if not is_candidate:
            continue
        resolution = containment.resolve_children(
            config, parent_number=num, corpus=corpus
        )
        for child in resolution.children:
            if child.number not in issues:
                continue  # a native child outside the fetched corpus — skip render
            issues[child.number].parent_number = num
            issue.children.append(child.number)
            issue.child_substrate[child.number] = child.substrate.value


def _refresh_children_views(
    issues: dict[int, Issue], capability_root: Path, config: dict
) -> None:
    """Refresh every parent's render-on-demand children comment (textual mode).

    The explicit refresh path for the textual children view (DEC-039 D4 / ADR-035
    section 4). Routes each parent through the one writer
    (`containment.refresh_children_comment`), which mode-gates (no-op in native),
    renders from the seam, finds the existing marked comment, and overwrites it
    (or creates one) — never an append, idempotent on an unchanged child set.

    The mode gate lives inside the writer: it is consulted once here (so a native
    repo short-circuits to a single advisory line rather than one no-op call per
    parent), and the writer re-checks it defensively per call. Failure-posture-
    neutral — every outcome is a one-line note; none aborts the walk.
    """
    mode = axis_labels.containment_mode(capability_root)
    if mode != axis_labels.CONTAINMENT_TEXTUAL:
        print(
            f"[skip] containment is {mode!r}; children-view refresh is a no-op "
            "(the native sub-issues panel gives parent-side visibility).",
            file=sys.stderr,
        )
        return
    corpus = {num: issue.body for num, issue in issues.items()}
    titles = {num: issue.title for num, issue in issues.items() if issue.title}
    # Only parents that resolved at least one child get a view — a parent with no
    # children needs no children comment (and the seam would render an empty one).
    parents = sorted(num for num, issue in issues.items() if issue.children)
    if not parents:
        print("[ok] no parents with children to refresh.", file=sys.stderr)
        return
    for parent in parents:
        result = containment.refresh_children_comment(
            config,
            parent_number=parent,
            corpus=corpus,
            containment_mode=mode,
            titles=titles,
        )
        prefix = "[ok]" if result.ok else "[warn]"
        print(f"{prefix} {result.detail}", file=sys.stderr)


def _first_parent_ref(body: str) -> int | None:
    """The parent number on a body's first non-blank parent-ref line, for the
    candidate-parent pre-scan only — the seam still owns authoritative
    resolution. Kept minimal and local to bounding which parents get a native
    read; it never decides the rendered child set."""
    if not body:
        return None
    for line in body.splitlines():
        s = line.strip()
        if not s:
            continue
        m = re.match(r"^([A-Za-z]+):\s+#(\d+)", s)
        if not m:
            return None
        return int(m.group(2))
    return None


# ---- orphan detection -----------------------------------------------


def _detect_orphans(issues: dict[int, Issue], prs: dict[int, PR]) -> dict:
    """Return dict with several orphan categories."""
    orphan_open_no_parent: list[int] = []
    task_not_under_container: list[int] = []
    pr_no_closing_issue: list[int] = []

    for num, issue in issues.items():
        if issue.state != "open":
            continue
        if issue.structural_type == "epic":
            # EPICs are tops; no parent expected (parent_ref_optional: true).
            continue
        if issue.parent_number is None:
            orphan_open_no_parent.append(num)
        elif issue.structural_type == "task":
            parent = issues.get(issue.parent_number)
            if parent is not None and parent.structural_type not in (
                "feature",
                "umbrella",
                "epic",
            ):
                task_not_under_container.append(num)

    for pr_num, pr in prs.items():
        if pr.state != "open":
            continue
        # Any closes-target should be an issue we know about.
        if not pr.closes or not any(n in issues for n in pr.closes):
            pr_no_closing_issue.append(pr_num)

    return {
        "open_issues_with_no_parent_ref": sorted(orphan_open_no_parent),
        "tasks_not_under_container": sorted(task_not_under_container),
        "prs_without_closing_issue_in_repo": sorted(pr_no_closing_issue),
    }


# ---- tree construction ----------------------------------------------


def _build_tree(issues: dict[int, Issue]) -> dict[int, Issue]:
    """Identity passthrough for now; the dict order is the iteration order.

    The tree shape is encoded by `parent_number` + `children` on each
    Issue. The renderers walk roots (parent_number is None) and recurse.
    """
    return issues


def _issue_to_dict(issue: Issue) -> dict:
    return {
        "number": issue.number,
        "title": issue.title,
        "state": issue.state,
        "structural_type": issue.structural_type,
        "milestone": issue.milestone,
        "parent_number": issue.parent_number,
        "children": sorted(issue.children),
        # Provenance from the read-seam: child number -> "native" / "textual".
        "child_substrate": {
            str(n): issue.child_substrate.get(n, "textual")
            for n in sorted(issue.children)
        },
    }


# ---- text renderer --------------------------------------------------


def _print_text(
    issues: dict[int, Issue],
    prs: dict[int, PR],
    orphans: dict,
    _tree: dict[int, Issue],
) -> None:
    roots = sorted(n for n, i in issues.items() if i.parent_number is None)
    print("# Issue hierarchy")
    print()
    if not roots:
        print("  (no roots found)")
    else:
        for root in roots:
            _print_branch(issues, prs, root, depth=0)

    print()
    print("# Orphans / drift")
    print()
    if not any(orphans.values()):
        print("  (none)")
        return
    for category, nums in orphans.items():
        if not nums:
            continue
        print(f"  [{category}]")
        for n in nums:
            target = issues.get(n) or prs.get(n)
            label = (
                f"#{n} — {target.title}"
                if target is not None and getattr(target, "title", None)
                else f"#{n}"
            )
            print(f"    - {label}")
        print()


def _print_branch(
    issues: dict[int, Issue],
    prs: dict[int, PR],
    num: int,
    depth: int,
    substrate: str | None = None,
) -> None:
    issue = issues[num]
    prefix = "  " * depth + ("- " if depth else "")
    type_marker = f"[{issue.structural_type or '?'}]"
    state_marker = f"({issue.state})"
    ms = f" — milestone: {issue.milestone}" if issue.milestone else ""
    # Only annotate textual-only links — native is the canonical default, so the
    # marker calls out the projection-only children (DEC-005) without noise.
    sub_marker = "  [textual]" if substrate == "textual" else ""
    print(f"{prefix}{type_marker} #{num} {state_marker} {issue.title}{ms}{sub_marker}")
    # Linked PRs.
    linked = [p for p in prs.values() if num in p.closes]
    for p in linked:
        sub = "  " * (depth + 1) + "↪ "
        print(f"{sub}PR #{p.number} ({p.state}) — {p.title}")
    for child in sorted(issue.children):
        _print_branch(
            issues, prs, child, depth + 1, issue.child_substrate.get(child)
        )


# ---- markdown renderer ----------------------------------------------


def _print_markdown(
    issues: dict[int, Issue],
    prs: dict[int, PR],
    orphans: dict,
    _tree: dict[int, Issue],
) -> None:
    print("# Issue hierarchy")
    print()
    roots = sorted(n for n, i in issues.items() if i.parent_number is None)
    for root in roots:
        _md_branch(issues, prs, root, depth=0)
    print()
    print("# Orphans / drift")
    print()
    for category, nums in orphans.items():
        if not nums:
            continue
        print(f"## {category}")
        for n in nums:
            print(f"- #{n}")
        print()


def _md_branch(
    issues: dict[int, Issue],
    prs: dict[int, PR],
    num: int,
    depth: int,
    substrate: str | None = None,
) -> None:
    issue = issues[num]
    indent = "  " * depth
    state = f" *(closed)*" if issue.state == "closed" else ""
    sub_marker = " _(textual)_" if substrate == "textual" else ""
    print(
        f"{indent}- **[{issue.structural_type or '?'}] #{num}**{state} "
        f"{issue.title}{sub_marker}"
    )
    linked = [p for p in prs.values() if num in p.closes]
    for p in linked:
        print(f"{indent}  - PR #{p.number} ({p.state}) {p.title}")
    for child in sorted(issue.children):
        _md_branch(
            issues, prs, child, depth + 1, issue.child_substrate.get(child)
        )


# ---- gh wrappers ----------------------------------------------------


def _gh_list_issues(*, state: str, limit: int, config: dict) -> list | None:
    try:
        proc = gh_run(
            [
                "gh",
                "issue",
                "list",
                "--state",
                state,
                "--limit",
                str(limit),
                "--json",
                "number,title,body,state,labels,milestone",
            ],
            config,
            check=False,
        )
    except FileNotFoundError:
        print("error: `gh` not on PATH.", file=sys.stderr)
        return None
    if proc.returncode != 0:
        print(
            f"error: gh issue list failed.\nstderr: {proc.stderr.strip()}",
            file=sys.stderr,
        )
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def _gh_list_prs(*, state: str, limit: int, config: dict) -> list | None:
    try:
        proc = gh_run(
            [
                "gh",
                "pr",
                "list",
                "--state",
                state,
                "--limit",
                str(limit),
                "--json",
                "number,title,body,state",
            ],
            config,
            check=False,
        )
    except FileNotFoundError:
        return None
    if proc.returncode != 0:
        print(
            f"error: gh pr list failed.\nstderr: {proc.stderr.strip()}",
            file=sys.stderr,
        )
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


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
