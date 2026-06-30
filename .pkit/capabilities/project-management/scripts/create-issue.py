#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — create-issue (verb-subject per DEC-020).

Files a new issue against the methodology's body shape: validates the
type, stamps the title against `titles.yaml`'s per-type regex,
composes the body from the matching `templates/<Type>.md`, applies the
classification axes (type:*, priority:*, workstream:* per
`classification.yaml`), and posts the issue via `gh issue create`.

For board-substrate adopters (per DEC-019 +
`schemas/mandatory-issue-state.yaml`), the new issue is also added to
the configured Projects v2 board as the final step of filing. The
default assignee is the resolved invoker identity per DEC-019's
default_at_filing: filer.

Membership predicate per DEC-021 runs at startup; closed mode refuses
non-members with the standard structured refusal.

Self-contained via PEP 723; runs via
  uv run --script .pkit/capabilities/project-management/scripts/create-issue.py

Or, via the dispatcher (per COR-021):
  pkit project-management create-issue --type task --title "..."

Exit codes:
  0  issue created
  1  membership refusal
  2  usage error / validation refusal
  3  gh failure (auth, network, repo not found, ...)
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import axis_labels  # noqa: E402
from _lib.containment import link_sub_issue  # noqa: E402
from _lib.gh import gh_run, load_adopter_config  # noqa: E402
from _lib.hooks import fire_hooks  # noqa: E402
from _lib.membership import (  # noqa: E402
    CAPABILITY_NAME,
    check_membership,
    resolve_capability_root,
    resolve_invoker_identity,
)
from _lib.milestone import resolve_milestone  # noqa: E402
from _lib.substrate_writes import milestone_create_args  # noqa: E402
from _lib.placeholder_detection import (  # noqa: E402
    PHASE_CREATE,
    detect_placeholder_residuals,
)


VALID_STRUCTURAL_TYPES = ("epic", "feature", "umbrella", "task")
VALID_KINDS = ("feature", "bug", "docs", "test", "refactor", "maintenance")
VALID_PRIORITIES = ("High", "Medium", "Low")
DEFAULT_KIND = "feature"
DEFAULT_PRIORITY = "Medium"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "File a new issue against the project-management methodology's "
            "body shape. Composes title + body from the type's template + "
            "titles regex, applies classification labels, optionally adds "
            "to the configured Projects v2 board (per DEC-019)."
        ),
    )
    parser.add_argument(
        "--type",
        required=True,
        choices=VALID_STRUCTURAL_TYPES,
        help="Structural issue type per issue-types.yaml.",
    )
    parser.add_argument(
        "--title",
        required=True,
        help="Title text (without the [Type] prefix — that's prepended automatically).",
    )
    parser.add_argument(
        "--kind",
        choices=VALID_KINDS,
        default=DEFAULT_KIND,
        help=(
            "Classification axis `type:*` value per classification.yaml. "
            f"Default: {DEFAULT_KIND}. Drives PR-title alignment when the "
            "issue closes."
        ),
    )
    parser.add_argument(
        "--priority",
        choices=VALID_PRIORITIES,
        default=DEFAULT_PRIORITY,
        help=f"Priority axis per classification.yaml. Default: {DEFAULT_PRIORITY}.",
    )
    parser.add_argument(
        "--workstream",
        default=None,
        help=(
            "Workstream slug per the adopter's workstreams list. Required "
            "in label-fallback mode (no Projects v2 board)."
        ),
    )
    parser.add_argument(
        "--parent",
        type=int,
        default=None,
        help=(
            "Parent issue number. Substituted into the body template's "
            "first parent-ref line. create-issue enforces parent-*requiredness* "
            "only (whether a parent-ref is required for this type, degradable "
            "via the hierarchy mode); it does NOT gate issue-types.yaml's "
            "containment graph at filing — the containment_invariants are a "
            "prose invariant, not a create-time gate."
        ),
    )
    parser.add_argument(
        "--assignee",
        default=None,
        help="Assignee GitHub login. Defaults to the resolved invoker identity.",
    )
    parser.add_argument(
        "--milestone",
        default=None,
        help=(
            "Milestone to attach. Accepts the milestone number "
            "(e.g. `6`) or its exact title (e.g. "
            "`Milestone 1: Self-host project-kit pm capability cleanly`). "
            "Matches `gh issue create --milestone`'s permissive behaviour."
        ),
    )
    parser.add_argument(
        "--body-file",
        type=Path,
        default=None,
        help=(
            "Path to a file whose content becomes the issue body, "
            "bypassing the template-based composition. The file's "
            "first line must be the parent-ref per the issue type's "
            "`parent_ref_form` (the same first-line check the "
            "template-composition path enforces). Useful when the "
            "caller has the full body already prepared (e.g. agent "
            "filing). See #218."
        ),
    )
    parser.add_argument(
        "--board",
        type=int,
        default=None,
        help=(
            "Projects v2 board ID. Overrides the adopter's "
            "`projects_v2_board_id` config for this invocation."
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
        "--dry-run",
        action="store_true",
        help="Print what would be done; do not invoke gh.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the confirmation prompt before invoking gh.",
    )
    args = parser.parse_args()

    capability_root = resolve_capability_root(args.capability_root)
    if capability_root is None:
        print(
            f"error: {CAPABILITY_NAME} capability not found.",
            file=sys.stderr,
        )
        return 2

    yaml_loader = YAML(typ="safe")

    # Membership gate first.
    config = load_adopter_config(capability_root)
    members = _read_members(capability_root, yaml_loader)
    invoker = resolve_invoker_identity(config=config)
    membership = check_membership(members, invoker)
    if not membership.allowed:
        print(membership.refusal_message, file=sys.stderr)
        return 1

    # Read schemas + adopter config.
    issue_types = _read_yaml(
        capability_root / "schemas" / "issue-types.yaml", yaml_loader
    )
    titles = _read_yaml(
        capability_root / "schemas" / "titles.yaml", yaml_loader
    )
    body_format = _read_yaml(
        capability_root / "schemas" / "body-format.yaml", yaml_loader
    )
    config = _read_yaml(
        capability_root / "project" / "config.yaml", yaml_loader
    )

    type_entry = (issue_types.get("types") or {}).get(args.type)
    if not isinstance(type_entry, dict):
        print(
            f"error: issue-types.yaml has no entry for type {args.type!r}.",
            file=sys.stderr,
        )
        return 2

    # Compose the full title with the type's title_prefix.
    title_prefix = type_entry.get("title_prefix", args.type.capitalize())
    title_case = type_entry.get("title_case", "title")
    if title_case == "upper":
        title_prefix = str(title_prefix).upper()
    full_title = f"[{title_prefix}] {args.title.strip()}"

    # Validate against titles.yaml's pattern for this surface.
    title_pattern = _title_pattern_for(titles, args.type)
    if title_pattern and not re.match(title_pattern, full_title):
        print(
            f"error: composed title {full_title!r} does not match "
            f"titles.yaml pattern for {args.type!r}: {title_pattern!r}",
            file=sys.stderr,
        )
        return 2

    # The adopter's optional substrate-map (ADR-026 / DEC-036). None ⇒
    # greenfield. Loaded here (not just for label resolution below) because the
    # hierarchy MODE it declares governs whether the parent-requiredness check
    # just below gates or merely advises.
    substrate_map = axis_labels.load_substrate_map(capability_root)
    hierarchy = axis_labels.hierarchy_disposition(substrate_map)

    # Validate parent type (if --parent given) / parent-REQUIREDNESS.
    #
    # Parent-requiredness softens per the hierarchy MODE (DEC-036 D4). The
    # mechanism is a short-circuit, not a token re-resolution: under
    # `hierarchy: advisory` (a flat brownfield tracker with no machine-checkable
    # parent-refs) `_parent_requiredness_is_gated` returns False BEFORE consulting
    # the authored severity, so create-issue NEVER demands a parent the repo
    # cannot express — a parent-ref is still recorded as body-text when --parent
    # is given. The per-type `parent_ref_required_severity` field is the authored
    # default consulted only on the gated arm (greenfield / `hierarchy: gated`),
    # where it keeps the hard-reject exactly as before. (Resolving the authored
    # severity THROUGH the DEC-014 token path under advisory is deferred —
    # ADR-026; today advisory simply short-circuits the gate.) This softens ONLY
    # requiredness; the containment invariants stay hard (they carry no knob —
    # the no-knob-stays-hard fail-safe).
    parent_issue_types = type_entry.get("parent_issue_types") or []
    parent_ref_optional = bool(type_entry.get("parent_ref_optional", False))
    milestone_is_valid_parent = "milestone" in parent_issue_types
    parent_ref_missing = (
        args.parent is None
        and not parent_ref_optional
        and not (args.milestone is not None and milestone_is_valid_parent)
    )
    if parent_ref_missing:
        gated = _parent_requiredness_is_gated(type_entry, hierarchy)
        message = (
            f"--parent is required for issue type {args.type!r}. "
            f"Permitted parent types: {', '.join(parent_issue_types) or '<none>'}. "
            f"You may pass --milestone instead when milestone is a permitted parent."
        )
        if gated:
            print(
                f"error: {message} "
                "If your tracker is flat / brownfield, set `hierarchy: advisory` "
                "in substrate-map.yaml so parent-refs are recorded but not "
                "required.",
                file=sys.stderr,
            )
            return 2
        # advisory hierarchy: degrade to a warning, proceed parentless.
        print(
            f"[advisory] {message} (not gated under hierarchy: advisory — "
            "filing without a parent-ref)",
            file=sys.stderr,
        )

    # Resolve --milestone (accepts number OR title; per #217).
    # Normalises `args.milestone` to the int form so downstream code
    # (parent-ref URL composition, display) sees a single shape. The
    # TITLE is kept separately because `gh issue create --milestone`
    # matches by NAME only (`gh issue create --help`: "Add the issue to
    # a milestone by name") — passing the number fails with
    # "could not add to milestone '<N>': '<N>' not found" (#223).
    milestone_title: str | None = None
    if args.milestone is not None:
        resolved = resolve_milestone(str(args.milestone), config)
        if resolved is None:
            print(
                f"error: --milestone {args.milestone!r} did not match any "
                "OPEN milestone (tried as number, then as title). "
                "List with `gh api repos/<owner>/<repo>/milestones?state=open`.",
                file=sys.stderr,
            )
            return 2
        args.milestone = resolved.number
        milestone_title = resolved.title

    # Workstream requirement when in label-fallback mode.
    has_board = bool(config.get("has_projects_v2_board", False))
    if not has_board and args.workstream is None:
        print(
            "error: --workstream is required in label-fallback mode "
            "(no Projects v2 board configured in project/config.yaml).",
            file=sys.stderr,
        )
        return 2

    # Workstream value validation against adopter config.
    if args.workstream is not None:
        adopter_workstreams = _adopter_workstreams(config)
        if adopter_workstreams and args.workstream not in adopter_workstreams:
            print(
                f"error: workstream {args.workstream!r} is not in the "
                "adopter's declared workstreams list "
                f"({', '.join(sorted(adopter_workstreams))}).",
                file=sys.stderr,
            )
            return 2

    # Compose the body. Two paths per #218:
    #   1. --body-file: read the file's content verbatim. The first
    #      line must match the parent-ref form (same check the
    #      validator + edit-issue apply); errors out otherwise.
    #   2. Default: stamp from the type's template + parent-ref line.
    expected_parent_ref = _parent_ref_line(
        type_entry,
        parent_num=args.parent,
        milestone_num=args.milestone,
    )
    if args.body_file is not None:
        if not args.body_file.is_file():
            print(
                f"error: --body-file path {str(args.body_file)!r} is not a file.",
                file=sys.stderr,
            )
            return 2
        try:
            body = args.body_file.read_text(encoding="utf-8")
        except OSError as exc:
            print(
                f"error: failed to read --body-file {str(args.body_file)!r}: {exc}",
                file=sys.stderr,
            )
            return 2
        first_line = body.lstrip().split("\n", 1)[0]
        if expected_parent_ref and first_line.strip() != expected_parent_ref.strip():
            print(
                f"error: --body-file's first line must be the parent-ref "
                f"line for this issue type. Expected:\n  {expected_parent_ref}\n"
                f"Got:\n  {first_line}",
                file=sys.stderr,
            )
            return 2
    else:
        template_path = capability_root / "templates" / f"{title_prefix}.md"
        if not template_path.is_file():
            # Fall back to title-case for the file (e.g., Feature.md).
            template_path = (
                capability_root / "templates" / f"{type_entry.get('title_prefix', '')}.md"
            )
        body = _compose_body(template_path, parent_ref=expected_parent_ref)

    # Residual-placeholder check at create-phase (DEC-031).
    # Emits warnings when the composed body is still the raw skeleton so
    # the author sees the unfinished state from the first moment.  Does
    # NOT block filing — the hard-reject gate fires at the first
    # lifecycle transition via validate-issue --phase transition.
    _warn_placeholder_residuals(body, args.type, body_format, capability_root)

    # Resolve assignee.
    assignee = args.assignee or invoker.github_login
    if not assignee:
        print(
            "error: could not resolve assignee. Pass --assignee explicitly "
            "or ensure `gh api user` works (sets the default).",
            file=sys.stderr,
        )
        return 2

    # Labels. Axis-labels are RESOLVED through the seam's write-path resolver
    # (ADR-026 sole-constructor + fail-closed): greenfield (no substrate-map)
    # resolves to the kit's own `<axis>:<value>`; a present map resolves to the
    # adopter's substrate value, or omits the label entirely (DEGRADE) on an
    # unsupported/absent/value-unresolvable axis — never coerced to a kit write.
    # `substrate_map` was loaded above (it also governs hierarchy mode).
    labels, label_advisories, resolved_by_axis = _build_labels(
        kind=args.kind,
        priority=args.priority,
        workstream=args.workstream,
        has_board=has_board,
        substrate_map=substrate_map,
    )
    for advisory in label_advisories:
        print(f"[advisory] {advisory}", file=sys.stderr)

    # Pre-flight summary.
    print("about to create issue:")
    print(f"  title:      {full_title}")
    print(f"  type:       {args.type}  (structural)")
    # The classification label as resolved — read from the `_build_labels`
    # result (G-2, #265) so the displayed value and the APPLIED label cannot
    # diverge (one resolution, not two). Absent ⇒ DEGRADE (unsupported / absent /
    # value-unresolvable `type` axis) ⇒ not labelled.
    kind_label = resolved_by_axis.get("type")
    kind_display = kind_label if kind_label else "(not labelled — axis unsupported)"
    print(f"  kind:       {kind_display}  (classification label)")
    print(f"  priority:   {args.priority}")
    if args.workstream:
        print(f"  workstream: {args.workstream}")
    if args.parent:
        print(f"  parent:     #{args.parent}")
    if args.milestone:
        print(f"  milestone:  #{args.milestone}")
    print(f"  assignee:   {assignee}")
    print(f"  labels:     {', '.join(labels)}")
    board_id = args.board if args.board is not None else config.get("projects_v2_board_id")
    if has_board:
        print(f"  board:      v2/{board_id}  (auto-add per DEC-019)")

    if args.dry_run:
        print("\n[dry-run] gh would be invoked; nothing written.")
        return 0

    if not args.yes and sys.stdin.isatty():
        reply = input("Proceed? [y/N] ").strip().lower()
        if reply not in ("y", "yes"):
            print("aborted.", file=sys.stderr)
            return 0

    # Invoke gh issue create.
    issue_url = _gh_create_issue(
        title=full_title,
        body=body,
        labels=labels,
        assignee=assignee,
        milestone_title=milestone_title,
        config=config,
    )
    if issue_url is None:
        return 3

    print(f"\n[ok] created: {issue_url}")

    # Set GitHub's native sub-issue link under the parent, IN ADDITION to the
    # textual first-line parent-ref already written into the body above (DEC-005:
    # native sub-issues are the canonical containment mechanism; the textual ref
    # is the universal spine). Only an ISSUE parent is linked natively — a
    # milestone parent (--milestone) is not a sub-issue relationship and carries
    # its own native Milestone field, so it is not linked here. The link is
    # idempotent (value-equality re-link is a no-op, DEC-026) and degrades to a
    # no-op where the instance lacks sub-issue support — the textual ref carries
    # the relationship in that case, and a native failure never fails the create.
    new_issue_number = _extract_issue_number_from_url(issue_url)
    if args.parent is not None and new_issue_number is not None:
        link = link_sub_issue(
            config,
            parent_number=args.parent,
            child_number=new_issue_number,
        )
        prefix = "[ok]" if link.ok else "[warn]"
        print(f"{prefix} {link.detail}", file=sys.stderr)

    # Auto-add to board for board-substrate adopters (per DEC-019).
    #
    # Capture the created board-item node id (and resolve the project node id)
    # so the `after_create_issue` `set-board-field` hook can seed the non-label
    # field default onto THIS new item (DEC-037 §3 — the non-label per-create
    # default; the same field write the one-time back-fill drives over the
    # corpus). Without these two ids the hook skips ("no board-item id in
    # context"), so the Projects-v2 field default would never seed on create.
    # The milestone default (`assign-milestone`) needs only the issue number
    # and seeds regardless.
    board_item_id: str | None = None
    project_node_id: str | None = None
    if has_board and board_id:
        board_item_id = _gh_add_to_board(board_id, issue_url, config)
        if board_item_id is None:
            print(
                f"[warn] issue created but failed to add to board v2/{board_id}.",
                file=sys.stderr,
            )
        else:
            owner = _owner_from_issue_url(issue_url)
            project_node_id = _resolve_project_node_id(board_id, owner, config)

    # Fire lifecycle hooks per DEC-024. Report-and-continue contract:
    # hook failures don't propagate to this script's exit code. The board-item
    # / project node ids let the `set-board-field` hook target the new item;
    # both stay absent in label-fallback mode (no board), where that hook is a
    # no-op skip by design.
    issue_context: dict[str, Any] = {"number": new_issue_number, "title": full_title}
    if board_item_id is not None:
        issue_context["board_item_id"] = board_item_id
    fire_hooks(
        "after_create_issue",
        context={
            "issue": issue_context,
            "repo": _resolve_repo_name_with_owner_safe(),
            "project_node_id": project_node_id,
        },
        config=config,
        capability_root=capability_root,
    )

    return 0


def _warn_placeholder_residuals(
    body: str,
    structural_type: str,
    body_format: dict,
    capability_root: Path,
) -> None:
    """Emit stderr warnings when *body* still contains template-skeleton content.

    Runs at create-phase (DEC-031): the hard-reject gate lives in
    validate-issue --phase transition.  Filing is not blocked; the warnings
    make the unfinished body visible from the first moment.
    """
    findings = detect_placeholder_residuals(
        body=body,
        structural_type=structural_type,
        body_format=body_format,
        capability_root=capability_root,
        phase=PHASE_CREATE,
    )
    for _sev, label, detail in findings:
        print(f"[warning] {label}: {detail}", file=sys.stderr)


def _build_labels(
    *,
    kind: str,
    priority: str,
    workstream: str | None,
    has_board: bool,
    substrate_map: "axis_labels.SubstrateMap | None",
) -> tuple[list[str], list[str], dict[str, str]]:
    """Resolve the applied-label list for a new issue through the seam (ADR-026).

    Returns ``(labels, advisories, resolved_by_axis)`` where ``resolved_by_axis``
    maps each axis that RESOLVED to its applied label string (a DEGRADE'd axis is
    absent from the dict). Callers that need to DISPLAY a resolved label read it
    from this dict rather than re-resolving — so the displayed value and the
    applied label share one resolution and cannot diverge (G-2, #265).

    Each axis (``type`` via ``kind``, ``priority``, ``workstream``) is resolved
    with :func:`axis_labels.resolve_write`:

      * greenfield (``substrate_map is None``) ⇒ the kit's own
        ``<axis>:<value>`` label, byte-identical to the pre-rewire output;
      * a present map, axis bound ⇒ the adopter's own substrate value;
      * a present map, axis unsupported / absent / value-unresolvable ⇒
        :data:`axis_labels.DEGRADE`, which is **omitted from the label list**
        (fail-closed — never coerced to a kit write) and recorded as an
        advisory line.

    Where the adopter declared a per-axis ``default:`` and the resolved value
    is missing, the seam's :func:`axis_labels.axis_default` supplies it before
    resolution. ``priority`` / ``workstream`` are only carried in label-fallback
    mode (no board), exactly as before — under a board those axes live on the
    Projects v2 fields, not on labels.

    DEGRADE is filtered structurally: it is a non-str singleton, so the
    ``isinstance(resolved, str)`` gate skips it. This is the call-site half of
    ADR-026 part (ii) — a degrade has no write.
    """
    labels: list[str] = []
    advisories: list[str] = []
    resolved_by_axis: dict[str, str] = {}

    # type axis (carried as the classification `type:<kind>` label / its remap).
    # priority + workstream are only label-carried in label-fallback mode — under
    # a board they live on the Projects v2 fields, not on labels. The value may
    # be blank (workstream is nullable); the adopter's per-axis `default:` seeds
    # it before resolution.
    axes_to_apply: list[tuple[str, str | None]] = [("type", kind)]
    if not has_board:
        axes_to_apply.append(("priority", priority))
        axes_to_apply.append(("workstream", workstream))

    for axis, value in axes_to_apply:
        # Apply the adopter's declared per-axis default only when the caller
        # gave no explicit value (workstream is the only nullable axis here;
        # type/priority always carry an argparse default).
        resolved_value = value or axis_labels.axis_default(axis, substrate_map)
        if not resolved_value:
            # No value and no default — nothing to label on this axis. This is
            # the greenfield workstream-omitted case (a board adopter never
            # reaches here for workstream; a label-fallback adopter is required
            # to pass --workstream upstream), so it is not an advisory.
            continue
        resolved = axis_labels.resolve_write(axis, resolved_value, substrate_map)
        if isinstance(resolved, str):
            labels.append(resolved)
            resolved_by_axis[axis] = resolved
        else:
            advisories.append(
                f"axis {axis!r} unsupported under your substrate-map — not labelled "
                f"(value {resolved_value!r})"
            )

    return labels, advisories, resolved_by_axis


def _extract_issue_number_from_url(url: str) -> int | None:
    """Parse the trailing issue number from `gh issue create`'s URL output."""
    m = re.search(r"/issues/(\d+)(?:[/?#].*)?$", url.strip())
    return int(m.group(1)) if m else None


def _resolve_repo_name_with_owner_safe() -> str:
    """Best-effort `owner/name` resolution for hook context. Empty on failure."""
    try:
        proc = subprocess.run(
            ["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"],
            capture_output=True, text=True, check=False, timeout=5,
        )
        return proc.stdout.strip() if proc.returncode == 0 else ""
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""


# ---- schema helpers --------------------------------------------------


# The validation-severity token a hard (gating) parent-requiredness rule carries,
# and the warning token it degrades to under advisory hierarchy. Centralised so
# the create-issue gate and any future validator agree on the spelling.
_SEVERITY_HARD_REJECT = "[validation-severity:hard-reject]"
_SEVERITY_WARNING = "[validation-severity:warning]"


def _parent_requiredness_is_gated(
    type_entry: dict,
    hierarchy: str,
) -> bool:
    """Whether a MISSING required parent-ref hard-rejects (gates) or just warns.

    The hierarchy MODE governs this via a short-circuit, NOT a token
    re-resolution (DEC-036 D4):

    * ``hierarchy == "advisory"`` ⇒ return ``False`` (not gated) immediately,
      BEFORE the authored severity is consulted. create-issue files parentless
      and advises. The ``parent_ref_required_severity`` field is deliberately not
      read on this arm — advisory short-circuits the gate regardless of the
      authored default. (Resolving that authored token through the DEC-014 path
      under advisory is deferred per ADR-026; the short-circuit is what ships.)
    * otherwise (``gated`` / greenfield) ⇒ the per-type
      ``parent_ref_required_severity`` field is the authored default (hard-reject
      when the schema omits it); return ``True`` when it is ``hard-reject`` — the
      byte-unchanged greenfield gate.

    This governs ONLY parent-requiredness. The containment invariants carry no
    such knob and are never reached here — they stay hard by construction.
    """
    if hierarchy == axis_labels.HIERARCHY_ADVISORY:
        return False
    authored = type_entry.get("parent_ref_required_severity", _SEVERITY_HARD_REJECT)
    return authored == _SEVERITY_HARD_REJECT


def _read_yaml(path: Path, yaml_loader: YAML) -> dict:
    if not path.is_file():
        return {}
    try:
        data = yaml_loader.load(path.read_text(encoding="utf-8"))
    except (OSError, YAMLError):
        return {}
    return data if isinstance(data, dict) else {}


def _read_members(capability_root: Path, yaml_loader: YAML) -> list[dict]:
    path = capability_root / "project" / "members.yaml"
    data = _read_yaml(path, yaml_loader)
    members = data.get("members") or []
    return members if isinstance(members, list) else []


def _title_pattern_for(titles: dict, structural_type: str) -> str | None:
    """Look up the titles.yaml regex for the given structural type."""
    formats = titles.get("formats") or {}
    key = f"issue-{structural_type}"
    entry = formats.get(key)
    if isinstance(entry, dict):
        pattern = entry.get("pattern")
        if isinstance(pattern, str):
            return pattern
    return None


def _adopter_workstreams(config: dict) -> set[str]:
    """Extract the adopter's declared workstream slugs.

    Supports both the v0.2.0 shape (`workstreams:` as a bare list in
    config.yaml) and the v0.5.0 shape (mapping form per DEC-018) as a
    forward-compatible read.
    """
    ws = config.get("workstreams")
    if isinstance(ws, list):
        out: set[str] = set()
        for entry in ws:
            if isinstance(entry, str):
                out.add(entry)
        return out
    if isinstance(ws, dict):
        return set(ws.keys())
    return set()


def _parent_ref_line(
    type_entry: dict,
    parent_num: int | None,
    milestone_num: int | None = None,
) -> str:
    """Build the parent-ref line that goes at the top of the body.

    When ``milestone_num`` is given (and the type permits milestone as a
    parent), emits the markdown-link form so the rendered link points to
    the actual milestone rather than auto-linking to an issue:
        ``Milestone: [#<N>](../milestone/<N>)``

    When ``parent_num`` is given, emits the plain ``<Label>: #<N>`` form
    (issue auto-links are correct for issue parents).
    """
    if milestone_num is not None and "milestone" in (
        type_entry.get("parent_issue_types") or []
    ):
        return f"Milestone: [#{milestone_num}](../milestone/{milestone_num})"
    if parent_num is None:
        return ""
    form = type_entry.get("parent_ref_form", "Parent: #<N>")
    # form is like "Feature: #<N>" or "EPIC: #<N> or Umbrella: #<N>" — pick
    # the first label fragment before the `:` and use it.
    head = str(form).split(":", 1)[0].strip()
    if " or " in head:
        head = head.split(" or ", 1)[0].strip()
    return f"{head}: #{parent_num}"


def _compose_body(template_path: Path, parent_ref: str) -> str:
    """Read the template, strip GitHub-issue-template frontmatter, substitute parent ref."""
    if not template_path.is_file():
        # Minimal fallback body.
        return parent_ref + ("\n\n" if parent_ref else "")
    raw = template_path.read_text(encoding="utf-8")
    body = _strip_issue_template_frontmatter(raw)
    if parent_ref:
        # Replace the first `<Label>: #` placeholder line (e.g., `Feature: #`)
        # with the actual parent ref.
        body = re.sub(
            r"^([A-Za-z]+)(:\s*)#\s*$",
            parent_ref,
            body,
            count=1,
            flags=re.MULTILINE,
        )
    return body


def _strip_issue_template_frontmatter(raw: str) -> str:
    """Remove a leading `---\\n...---\\n` block if present."""
    if not raw.startswith("---\n"):
        return raw
    end = raw.find("\n---\n", 4)
    if end < 0:
        return raw
    return raw[end + len("\n---\n"):]


# ---- gh helpers ------------------------------------------------------


def _gh_create_issue(
    *,
    title: str,
    body: str,
    labels: list[str],
    assignee: str,
    milestone_title: str | None,
    config: dict,
) -> str | None:
    """Invoke `gh issue create` and return the issue URL on success.

    ``milestone_title`` is the milestone's NAME, not its number:
    `gh issue create --milestone` matches by name only (#223).
    """
    cmd = [
        "gh",
        "issue",
        "create",
        "--title",
        title,
        "--body",
        body,
        "--assignee",
        assignee,
    ]
    for label in labels:
        cmd.extend(["--label", label])
    if milestone_title is not None:
        # The `--milestone` argv fragment is constructed by the sole constructor
        # (ADR-031); create-issue only chooses when it fires and splices it into
        # its own create call (which also carries title / body / labels /
        # assignee). The create itself executes below.
        cmd.extend(milestone_create_args(milestone_title))
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        print("error: `gh` not on PATH. Install GitHub CLI.", file=sys.stderr)
        return None
    if proc.returncode != 0:
        print(
            f"error: gh issue create failed (exit {proc.returncode}).\n"
            f"stderr: {proc.stderr.strip()}",
            file=sys.stderr,
        )
        return None
    # gh prints the URL on stdout.
    return proc.stdout.strip() or None


def _owner_from_issue_url(issue_url: str) -> str | None:
    """Extract the `<owner>` segment from a github issue URL, or ``None``.

    Both the board membership write (inside ``_gh_add_to_board``) and the
    project-node-id resolution (``main`` → ``_resolve_project_node_id``) scope to
    the issue's owner. They parse it independently at each site from the same
    source URL, so the two agree by construction (pure regex over one input).
    """
    m = re.match(r"https?://[^/]+/([^/]+)/", issue_url)
    return m.group(1) if m else None


def _gh_add_to_board(board_id: int, issue_url: str, config: dict) -> str | None:
    """Add an issue to a Projects v2 board via gh project item-add.

    The owner is derived from the issue URL (github.com/<owner>/<repo>/...).

    Returns the created board *item* node id on success (so the
    `after_create_issue` `set-board-field` hook can target the new item per
    DEC-037 §3 — the non-label field default), or ``None`` on any failure.
    The item id is captured here, at the one moment it is freshly known,
    rather than re-resolved with a board-wide GraphQL scan (the way the
    one-time back-fill must, since it has no fresh item to read).

    `gh project item-add --format json` returns the created item as
    ``{"id": "<item-node-id>", ...}``; we read `.id` off that.
    """
    owner = _owner_from_issue_url(issue_url)
    if owner is None:
        return None
    cmd = [
        "gh",
        "project",
        "item-add",
        str(board_id),
        "--owner",
        owner,
        "--url",
        issue_url,
        "--format",
        "json",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return None
    if proc.returncode != 0:
        return None
    try:
        payload = json.loads(proc.stdout)
    except (json.JSONDecodeError, ValueError):
        return None
    item_id = payload.get("id") if isinstance(payload, dict) else None
    return item_id if isinstance(item_id, str) and item_id else None


def _resolve_project_node_id(board_id: int, owner: str | None, config: dict) -> str | None:
    """Resolve the Projects-v2 *project* node id from the board NUMBER.

    The `set-board-field` hook's field-value write needs the project's GraphQL
    node id, but the adopter only declares the board *number*
    (`projects_v2_board_id`). This resolves number → node id via `gh project
    view --format json` (`.id`), the same read `back-fill.py`'s
    `_resolve_project_node_id` and `pre-check` use — kept here as the per-create
    half of that one resolution shape. A READ only; returns ``None`` when the
    board does not resolve (the hook then skips with "no board configured"
    rather than guessing).
    """
    view_args = ["gh", "project", "view", str(board_id), "--format", "json"]
    if owner:
        view_args += ["--owner", owner]
    try:
        proc = subprocess.run(view_args, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return None
    if proc.returncode != 0:
        return None
    try:
        payload = json.loads(proc.stdout)
    except (json.JSONDecodeError, ValueError):
        return None
    node_id = payload.get("id") if isinstance(payload, dict) else None
    return node_id if isinstance(node_id, str) and node_id else None


if __name__ == "__main__":
    sys.exit(main())
