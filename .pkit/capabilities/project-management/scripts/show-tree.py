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

Read-only EXCEPT `--refresh-children-views`, which rewrites each parent's
children comment (textual mode) and is gated by the foreign-repo session guard.
Membership gate per DEC-021 runs at startup (read mode).

Exit 1 covers a membership refusal and a refused write — the refresh declines
rather than rendering children comments from a corpus the seam could not vouch
for, since that write outlives the command.

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
import sys
from dataclasses import dataclass, field
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import axis_labels, body_parent_ref, bootstrap_gate, containment, session_guard
from _lib.gh import gh_run, load_adopter_config
from _lib.membership import (
    CAPABILITY_NAME,
    check_membership,
    resolve_capability_root,
    resolve_invoker_identity,
)
from _lib.structural_type import infer_structural_type

CLOSING_KEYWORD_RE = re.compile(r"\b(?:closes|fixes|resolves)\s+#(\d+)", re.IGNORECASE)


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
    # How this issue's native parent and its first line stand, as the
    # containment seam compares them (`containment.compare_parents`); None until
    # `_link_parents` has run.
    parent_resolution: containment.ParentResolution | None = None
    # Whether the native parent the resolution holds is the issue's native
    # parent as the tracker has it — one seen in a native child set, or none on
    # an instance without sub-issues — rather than "none seen" (`_link_parents`).
    native_parent_known: bool = False
    # What the render says of a child listed under this issue beyond its
    # substrate: a native parent elsewhere, a first line not in an allowed form.
    child_marks: dict[int, tuple[str, ...]] = field(default_factory=dict)


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
            "Max issues, and separately max PRs, to fetch from gh (default: "
            "500). A render where either fetch strikes this limit is marked "
            "partial; --refresh-children-views refuses rather than writing from "
            "a bounded issue view (it reads no PRs, so a bounded PR list does not "
            "stop it). Increase for large repos."
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

    # Prerequisite gate (#747): refuse on an un-bootstrapped project rather
    # than operating on assumed defaults. See _lib/bootstrap_gate.py.
    if not bootstrap_gate.enforce("show-tree", capability_root=capability_root):
        return 2

    yaml_loader = YAML(typ="safe")
    config = load_adopter_config(capability_root)
    members = _read_members(capability_root, yaml_loader)
    invoker = resolve_invoker_identity(config=config)
    membership = check_membership(members, invoker)
    if not membership.allowed:
        print(membership.refusal_message, file=sys.stderr)
        return 1

    issue_types = _read_yaml(capability_root / "schemas" / "issue-types.yaml", yaml_loader)
    # Kind-driven title prefixes ([Bug]/[Docs]/[Test]/[Refactor]/[Chore]) live in
    # classification.yaml; without it a kind-prefixed Task reads as unrecognised.
    classification = _read_yaml(capability_root / "schemas" / "classification.yaml", yaml_loader)

    # Acquisition belongs to the containment seam (ADR-035 §5); `--limit` and
    # `--state` stay view controls, and the seam's verdict is what lets a bounded
    # render admit it is bounded rather than pass a short tree off as the whole
    # one (#863).
    corpus = containment.fetch_issue_corpus(
        config,
        fields="number,title,body,state,labels,milestone",
        state=args.state,
        limit=args.limit,
    )
    if corpus is None:
        print("error: gh issue list failed.", file=sys.stderr)
        return 2
    issues_raw = list(corpus.rows)
    corpus_truncated = not corpus.complete
    prs_raw = _gh_list_prs(state=args.state, limit=args.limit, config=config)
    if prs_raw is None:
        return 2
    # Same rule as the issue corpus (`len >= limit` may be truncated), so the two
    # halves of the render are judged alike — including the false partial at
    # exactly `limit`, which is the price of not issuing a second query.
    prs_truncated = len(prs_raw) >= args.limit

    issues = _parse_issues(issues_raw, issue_types, classification)
    prs = _parse_prs(prs_raw)

    # Build parent relationships through the containment read-seam (native and
    # first-line children together, native-wins per DEC-005) — show-tree does NOT
    # parse body parent-refs directly (ADR-035, the one-read-seam discipline).
    incomplete_parents = _link_parents(
        issues, config, corpus_complete=corpus.complete, issue_types=issue_types
    )
    # Two independent reasons the view may be short, and both must label it: the
    # corpus was bounded, or the seam could not vouch for some parent's child set
    # (an unreadable native panel). Either one makes "no other children" and
    # "I could not see them" indistinguishable, which is what the label exists
    # to prevent.
    tree_partial = corpus_truncated or bool(incomplete_parents)
    # A third, independent reason: the PR list was bounded, so orphan-PR
    # detection and the issue-to-PR links may miss PRs. It labels the render but
    # does not touch the tree's child sets — which is why the children-view
    # refresh below gates on `tree_partial` alone.
    partial = tree_partial or prs_truncated
    partial_note = (
        _partial_note(
            limit=args.limit,
            truncated=corpus_truncated,
            incomplete_parents=incomplete_parents,
            prs_truncated=prs_truncated,
        )
        if partial
        else None
    )

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
        if args.state != "all":
            # A FILTER is not a truncation, and the completeness verdict cannot
            # see it: an open-only corpus is complete for what it asked, while
            # every closed child is missing from it. Writing a parent's children
            # comment from that view drops them silently — the same defect as a
            # bounded corpus, arriving with `complete=True`. The seam says why a
            # gate must not filter: a closed child still counts.
            print(
                f"[refused] children views not refreshed: --state {args.state} hides "
                "children from the write, and a closed child is still a child. "
                "Re-run with --state all.",
                file=sys.stderr,
            )
            return 1
        if tree_partial:
            # Refuse rather than overwrite. Each comment is replaced wholesale,
            # so rendering from a bounded corpus would drop real children from a
            # view that carries no hedge — and unlike a bounded tree render, the
            # damage persists after the command exits. The PR half is left out
            # deliberately: the refresh writes from issues alone, so a bounded
            # PR list cannot drop a child from any comment.
            note = _partial_note(
                limit=args.limit,
                truncated=corpus_truncated,
                incomplete_parents=incomplete_parents,
            )
            print(f"[refused] children views not refreshed: {note}", file=sys.stderr)
            return 1
        _refresh_children_views(issues, capability_root, config)

    if args.format == "json":
        out = {
            "issues": {str(num): _issue_to_dict(issues[num]) for num in issues},
            "prs": [
                {"number": p.number, "title": p.title, "state": p.state, "closes": p.closes}
                for p in prs.values()
            ],
            "orphans": orphans,
            "tree_roots": [n for n in tree if issues[n].parent_number is None],
            # Machine-readable consumers need the same caveat the humans get —
            # including WHY, since a bare False sends them back to inferring the
            # cause, which is the habit the seam pays an extra call to avoid.
            "complete": not partial,
            "incomplete_reason": partial_note,
        }
        print(json.dumps(out, indent=2))
    elif args.format == "markdown":
        _print_markdown(issues, prs, orphans, tree)
        if partial:
            print(f"\n> **Partial view** — {partial_note}")
    else:
        _print_text(issues, prs, orphans, tree)
        if partial:
            # stdout, so a redirected or piped render keeps the caveat — losing it
            # there is precisely the case this label exists for. Repeated on
            # stderr so it is also visible when stdout is being consumed.
            note = f"\n[partial] {partial_note}"
            print(note)
            print(note, file=sys.stderr)

    return 0


# ---- parsing --------------------------------------------------------


def _parse_issues(
    raw: list, issue_types: dict, classification: dict | None = None
) -> dict[int, Issue]:
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
            structural_type=infer_structural_type(
                title, issue_types, classification=classification
            ),
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
        closes = sorted({int(m.group(1)) for m in CLOSING_KEYWORD_RE.finditer(body)})
        out[number] = PR(
            number=number,
            title=str(r.get("title", "")),
            state=str(r.get("state", "")).lower(),
            closes=closes,
        )
    return out


def _link_parents(
    issues: dict[int, Issue], config: dict, *, corpus_complete: bool, issue_types: dict
) -> list[int]:
    """Populate children + child_substrate via the containment read-seam
    (``_lib.containment.resolve_children``), then each issue's parent through
    the seam's comparison of its native parent with its first line
    (``_lib.containment.compare_parents``).

    Returns the parents whose child set the seam could not vouch for, so the
    caller can label the render. The corpus's own completeness is passed IN
    rather than assumed: a caller that supplies a corpus without claiming it is
    whole gets an incomplete verdict for every parent, which would make the
    label meaningless by always firing.

    For each candidate parent the seam resolves its children — its native
    sub-issues together with every issue whose first line names it, native-wins
    on a child present both ways (DEC-005); show-tree never parses body
    parent-refs itself (ADR-035's one-read-seam discipline). The corpus
    (``{number: body}``) is handed to the seam so the textual side costs no API
    calls — the seam's only per-call cost is one native ``…/sub_issues`` GET per
    candidate parent.

    No issue's parent is read upward: each issue's native parent is the
    candidate parent whose native child set holds it, and the seam compares that
    with the issue's first line. ``parent_number`` is the parent the seam
    resolves — the native one wherever one was seen, else the first line's — so
    it does not depend on the order parents are walked in. A child the native
    parent and the first line place under different parents is listed under
    both, and under the first line's parent with a mark naming its native
    parent; a first line in a form the issue's type does not allow is marked
    where the child is listed under the parent it names.

    An issue whose native parent no resolved child set holds has none *seen*,
    which is not the same as none: the parent may be in another repository,
    outside the fetched issues (a closed parent under ``--state open``, one past
    ``--limit``), behind a native panel that could not be read, or an issue whose
    sub-issues were not read (below). So each issue's ``native_parent_known``
    says whether its native parent is known — seen in a native child set, or
    none on an instance the seam found without sub-issues — and is False
    wherever a missing one only means none was seen.

    Cost bound: the native read is issued only for *candidate parents* — issues
    of a structural type (epic/feature/umbrella/task) OR named as a parent by
    some issue's first line — not for every corpus issue. An issue that is
    neither, an untyped one no first line names, has its native sub-issues
    unread, so a native child of it is not seen: one linked in the tracker's own
    UI, or one whose first line names a milestone (as `create-issue --parent N
    --milestone M` files it) or nothing. Accepted to keep the walk from issuing
    one native call per corpus issue; such a child's native parent is not known.
    """
    corpus = {num: issue.body for num, issue in issues.items()}
    incomplete_parents: list[int] = []
    textual_parents = {
        parent
        for body in corpus.values()
        for parent in (_first_parent_ref(body),)
        if parent is not None
    }
    container_types = {"epic", "feature", "umbrella", "task"}
    native_parents: dict[int, int] = {}
    native_supported: list[bool] = []
    for num, issue in issues.items():
        is_candidate = issue.structural_type in container_types or num in textual_parents
        if not is_candidate:
            continue
        resolution = containment.resolve_children(
            config, parent_number=num, corpus=corpus, corpus_complete=corpus_complete
        )
        native_supported.append(resolution.native_supported)
        # A per-parent verdict can be incomplete even when the corpus is whole:
        # an UNREADABLE native panel for THIS parent means children may exist
        # unseen. Uncollected, the render would look complete while one parent's
        # child list was silently short — the defect this command is being
        # taught to admit to.
        if not resolution.complete:
            incomplete_parents.append(num)
        for child in resolution.children:
            if child.number not in issues:
                continue  # a native child outside the fetched corpus — skip render
            issue.children.append(child.number)
            issue.child_substrate[child.number] = child.substrate.value
            if child.substrate is containment.ChildSubstrate.NATIVE:
                native_parents[child.number] = num
    # No native substrate at all: every native read found the endpoint absent,
    # so an issue with no native parent seen has none.
    no_native_substrate = bool(native_supported) and not any(native_supported)
    for number, issue in issues.items():
        native = native_parents.get(number)
        resolution = containment.compare_parents(
            number,
            body_parent_ref.read_first_line(issue.body, issue.structural_type, issue_types),
            containment.NativeParent(native) if native is not None else None,
        )
        issue.parent_resolution = resolution
        issue.native_parent_known = native is not None or no_native_substrate
        parent = resolution.parent
        if parent is not None and number in _children_of(issues, parent.number):
            issue.parent_number = parent.number
        _mark_listing(issues, resolution)
    return incomplete_parents


def _children_of(issues: dict[int, Issue], number: int) -> list[int]:
    """The children the render lists under issue ``number`` — none for an issue
    outside the fetched corpus."""
    parent = issues.get(number)
    return parent.children if parent is not None else []


def _mark_listing(issues: dict[int, Issue], resolution: containment.ParentResolution) -> None:
    """Mark the child ``resolution`` resolves where it is listed under the
    parent its first line names: with its native parent, where that is another
    issue, and with the line's form, where the issue's type does not allow it."""
    child, named = resolution.issue, resolution.named
    if named is None or child not in _children_of(issues, named):
        return
    marks: list[str] = []
    native = resolution.native
    if resolution.kind is containment.ParentKind.DISAGREE and native is not None:
        marks.append(f"native parent {native.ref}")
    if resolution.line.form is body_parent_ref.LineForm.NON_CONFORMING:
        marks.append("first line not an allowed form")
    if marks:
        issues[named].child_marks[child] = tuple(marks)


def _listing_marks(parent: Issue, child: int) -> tuple[str, ...]:
    """What the render says of ``child`` listed under ``parent``: ``textual``
    for a child held there by its first line alone, then the marks
    :func:`_mark_listing` set."""
    textual = ("textual",) if parent.child_substrate.get(child) == "textual" else ()
    return textual + parent.child_marks.get(child, ())


def _refresh_children_views(issues: dict[int, Issue], capability_root: Path, config: dict) -> None:
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
    """The issue a body's first line names as its parent, for the
    candidate-parent pre-scan only — read as the seam's textual side reads it
    (`body_parent_ref.named_issue`), so every parent a child set can hold is a
    candidate. It bounds which parents get a native read; it never decides the
    rendered child set."""
    return body_parent_ref.named_issue(body)


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
            str(n): issue.child_substrate.get(n, "textual") for n in sorted(issue.children)
        },
        # How the issue's native parent and its first line stand: `disagree`
        # marks two parents, `non-conforming` a first line in a form the issue's
        # type does not allow.
        "parent_resolution": _resolution_to_dict(
            issue.parent_resolution, native_known=issue.native_parent_known
        ),
    }


def _resolution_to_dict(
    resolution: containment.ParentResolution | None, *, native_known: bool
) -> dict | None:
    """How an issue's two records of its parent stand, for the JSON render.

    ``native_parent_known`` tells a ``native_parent`` of ``null`` that means
    none from one that means none was seen (`_link_parents`): where it is false,
    the native parent is not known, and ``kind`` — read from what was seen —
    says nothing of it. ``first_line_names_itself`` marks a first line naming
    the issue itself, which names no parent."""
    if resolution is None:
        return None
    native = resolution.native
    return {
        "kind": resolution.kind.value,
        "native_parent": native.number if native is not None else None,
        "native_parent_known": native_known,
        "first_line_parent": resolution.named,
        "first_line_form": resolution.line.form.value,
        "first_line_names_itself": resolution.names_itself,
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
    marks: tuple[str, ...] = (),
) -> None:
    issue = issues[num]
    prefix = "  " * depth + ("- " if depth else "")
    type_marker = f"[{issue.structural_type or '?'}]"
    state_marker = f"({issue.state})"
    ms = f" — milestone: {issue.milestone}" if issue.milestone else ""
    # Only annotate what departs from the canonical default — a native child
    # whose first line agrees — so the marks call out projection-only children
    # (DEC-005), a native parent elsewhere and a malformed first line, without
    # noise (`_listing_marks`).
    sub_marker = "  " + " ".join(f"[{mark}]" for mark in marks) if marks else ""
    print(f"{prefix}{type_marker} #{num} {state_marker} {issue.title}{ms}{sub_marker}")
    # Linked PRs.
    linked = [p for p in prs.values() if num in p.closes]
    for p in linked:
        sub = "  " * (depth + 1) + "↪ "
        print(f"{sub}PR #{p.number} ({p.state}) — {p.title}")
    for child in sorted(issue.children):
        _print_branch(issues, prs, child, depth + 1, _listing_marks(issue, child))


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
    marks: tuple[str, ...] = (),
) -> None:
    issue = issues[num]
    indent = "  " * depth
    state = " *(closed)*" if issue.state == "closed" else ""
    sub_marker = "".join(f" _({mark})_" for mark in marks)
    print(f"{indent}- **[{issue.structural_type or '?'}] #{num}**{state} {issue.title}{sub_marker}")
    linked = [p for p in prs.values() if num in p.closes]
    for p in linked:
        print(f"{indent}  - PR #{p.number} ({p.state}) {p.title}")
    for child in sorted(issue.children):
        _md_branch(issues, prs, child, depth + 1, _listing_marks(issue, child))


# ---- gh wrappers ----------------------------------------------------


# Said the same way in every format, because the distinction it draws is the
# whole point: a bounded render cannot tell "this parent has no other children"
# from "I stopped looking", and this command is how people check whether a
# container is ready to close.
_PARTIAL_TRUNCATED = (
    "the tree was built from the first {limit} issues, so a parent may have "
    "children not shown here — re-run with a higher --limit for a complete view"
)

_PARTIAL_UNVOUCHED = (
    "the child set could not be vouched for on {count} parent(s) ({parents}), so "
    "children may exist that are not shown — the corpus was read in full, so a "
    "higher --limit will not help; retry, and check access to the sub-issues API"
)


_PARTIAL_PRS_TRUNCATED = (
    "only the first {limit} pull requests were read, so PRs closing an issue and "
    "PRs with no closing issue may be missing — re-run with a higher --limit for "
    "a complete view"
)


def _partial_note(
    *,
    limit: int,
    truncated: bool,
    incomplete_parents: list[int],
    prs_truncated: bool = False,
) -> str:
    """Name the fact that made the view partial, not merely that it is partial.

    Two causes, two remedies. A single note told every operator to raise
    `--limit`, which is the wrong advice when the corpus was already complete and
    the seam simply could not vouch for a parent — they would raise the limit,
    see the same warning, and have no way to tell why.

    Truncation is reported FIRST because it is the root cause when both hold: a
    bounded corpus is passed to the seam as an unvouched one, so every parent
    then reports incomplete as a consequence. Naming the consequence would tell
    the operator the corpus was read in full when it plainly was not.

    A bounded PR list is a separate fact, not a consequence of either issue-side
    cause, so it is appended rather than ranked: suppressing it would hide a
    short PR list behind an issue note, and vice versa.
    """
    reasons: list[str] = []
    if truncated:
        reasons.append(_PARTIAL_TRUNCATED.format(limit=limit))
    elif incomplete_parents:
        shown = ", ".join(f"#{n}" for n in incomplete_parents[:5])
        if len(incomplete_parents) > 5:
            shown += ", …"
        reasons.append(_PARTIAL_UNVOUCHED.format(count=len(incomplete_parents), parents=shown))
    if prs_truncated:
        reasons.append(_PARTIAL_PRS_TRUNCATED.format(limit=limit))
    if reasons:
        return "; ".join(reasons)
    # Unreachable while the caller only asks when something is partial — but a
    # fallback that invents a cause is exactly what this function exists to
    # prevent, so it says only what is known.
    return "the view may be short; the reason was not established"


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
