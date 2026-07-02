#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — set-field (verb-subject per DEC-020).

Declaratively set an issue's classification field(s) — priority, workstream,
parent — in one batch call, per [project-management:DEC-038-criterion-addressing]
(D2 names set-field as the looser GitHub-substrate-tier verb in the same batch /
validate-up-front / idempotent family). Replaces the whole-body or ad-hoc
`gh issue edit --add-label` surgery a field change otherwise needs.

Signature (batch-capable — set several fields in one call):
  set-field <issue> [--kind K] [--priority X] [--workstream Y] [--parent N]

  - --kind        one of the adopter's classification type values; swaps the
                  prior `type:*` label and realigns the title prefix.
  - --priority    one of the adopter's classification priority values.
  - --workstream  one of the adopter's declared workstream slugs.
  - --parent      a parent issue number; rewrites the body's first parent-ref
                  line to the issue type's `parent_ref_form`.

It does NOT reinvent classification rules — kind/priority/workstream resolve
through the SAME seam create-issue uses (`axis_labels.resolve_write`, honouring
substrate-map.yaml), the parent-ref line uses the same form create-issue
composes, and the kind→title-prefix realignment reads classification.yaml's
`title_prefix_by_value` (the same map create-issue's title composition uses), so
prefix and label stay coupled. The `type:*` axis is ALWAYS a label (per
classification.yaml), so --kind labels regardless of board substrate; under a
Projects-v2 board, priority/workstream instead live on board fields, so set-field
reports a degrade note and does not touch a label (mirroring move-issue's board
posture at v1).

Failure + recovery (DEC-038 D4 family): the whole request is validated up front
(value in the adopter's vocabulary; parent resolvable; and the requested kind is
permitted for the issue's structural type — a non-`feature` kind on an
epic/feature/umbrella is a hard-reject per DEC-011 / classification.yaml's
`structural_restriction`, since it would manufacture the kind/structural mismatch
that breaks the closing PR's conv-type derivation) and refused before any
mutation on a hard inconsistency. Application is idempotent — setting a field to
the value it already holds is a no-op success, so a partial fault recovers on
re-run.

Membership gate per DEC-021 runs at startup. Reuses edit-issue's
`gh issue edit` write-back for the parent-ref body rewrite.

Self-contained via PEP 723; runs via
  uv run --script .pkit/capabilities/project-management/scripts/set-field.py 239 --priority High
Or via the dispatcher (per COR-021):
  pkit project-management set-field 239 --priority High --workstream cli

Exit codes:
  0  applied (or no-op idempotent success; or dry-run reported)
  1  membership refusal / validation refusal (nothing mutated)
  2  usage error (issue not found; no field given; unknown value)
  3  gh write failure
"""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import axis_labels  # noqa: E402
from _lib import classification_rules  # noqa: E402
from _lib import provenance  # noqa: E402
from _lib import session_guard  # noqa: E402
from _lib.gh import gh_get_issue, gh_run, load_adopter_config  # noqa: E402
from _lib.membership import (  # noqa: E402
    CAPABILITY_NAME,
    check_membership,
    resolve_capability_root,
    resolve_invoker_identity,
)


@dataclass(frozen=True)
class FieldResult:
    field: str
    ok: bool
    changed: bool
    message: str


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if (
        args.kind is None
        and args.priority is None
        and args.workstream is None
        and args.parent is None
    ):
        print(
            "error: nothing to set. Pass at least one of --kind, --priority, "
            "--workstream, --parent.",
            file=sys.stderr,
        )
        return 2

    capability_root = resolve_capability_root(args.capability_root)
    if capability_root is None:
        print(f"error: {CAPABILITY_NAME} capability not found.", file=sys.stderr)
        return 2

    yaml_loader = YAML(typ="safe")
    config = load_adopter_config(capability_root)
    members = _read_members(capability_root, yaml_loader)
    invoker = resolve_invoker_identity(config=config)
    membership = check_membership(members, invoker)
    if not membership.allowed:
        print(membership.refusal_message, file=sys.stderr)
        return 1

    # Foreign-repo mutation guard (COR-039 / ADR-034) — gate before any gh
    # mutation: target repo (cwd) vs session anchor (CLAUDE_PROJECT_DIR).
    if not session_guard.enforce(override=args.allow_foreign_repo):
        return 1

    issue_types = _read_yaml(capability_root / "schemas" / "issue-types.yaml", yaml_loader)
    classification = _read_yaml(
        capability_root / "schemas" / "classification.yaml", yaml_loader
    )
    substrate_map = axis_labels.load_substrate_map(capability_root)
    has_board = bool(config.get("has_projects_v2_board", False))

    issue = gh_get_issue(
        args.issue_number, config, fields="title,body,labels"
    )
    if issue is None:
        return 2
    title = str(issue.get("title", ""))
    # Strip the footer on read; the seam re-stamps one on write (ADR-036).
    body = provenance.strip_footer(str(issue.get("body") or ""))
    current_labels = [
        lbl.get("name", "") if isinstance(lbl, dict) else str(lbl)
        for lbl in (issue.get("labels") or [])
    ]

    print(f"set-field: #{args.issue_number}")

    # ---- validate the whole request up front (DEC-038 hard-reject family) ----
    errors: list[str] = []

    valid_kinds = _axis_values(classification, "type")
    if args.kind is not None and valid_kinds and args.kind not in valid_kinds:
        errors.append(
            f"kind {args.kind!r} is not a declared type value "
            f"({', '.join(sorted(valid_kinds))})"
        )
    elif args.kind is not None:
        # Refuse the kind/structural mismatch DEC-011 declares a hard-reject:
        # epic/feature/umbrella carry kind `feature` by definition, so swapping
        # in a non-feature kind while leaving the structural prefix would
        # manufacture exactly the mismatch that breaks PR-conv-type derivation
        # (open-pr/validate-pr read the closing issue's type:* label). Check
        # against `allowed_structural_types_per_kind` (the shared predicate in
        # _lib/classification_rules — the SAME reader create-issue and
        # validate-issue use) before any mutation. `--kind feature` on those
        # types is the allowed kind, so it passes here and lands as a no-op
        # (label already type:feature, no prefix change).
        structural_type = _infer_structural_type(title, issue_types, classification)
        if (
            structural_type is not None
            and not classification_rules.kind_allowed_for_structural_type(
                args.kind, structural_type, classification
            )
        ):
            errors.append(
                f"kind {args.kind!r} is not valid for structural type "
                f"{structural_type.upper()} — epic/feature/umbrella carry kind "
                "'feature' by definition (classification.yaml "
                "structural_restriction / DEC-011). Re-file as a Task if this "
                "is genuinely bug work."
            )

    valid_priorities = _axis_values(classification, "priority")
    if args.priority is not None and valid_priorities and args.priority not in valid_priorities:
        errors.append(
            f"priority {args.priority!r} is not a declared value "
            f"({', '.join(sorted(valid_priorities))})"
        )

    adopter_workstreams = _adopter_workstreams(config)
    if (
        args.workstream is not None
        and adopter_workstreams
        and args.workstream not in adopter_workstreams
    ):
        errors.append(
            f"workstream {args.workstream!r} is not in the adopter's declared "
            f"workstreams ({', '.join(sorted(adopter_workstreams))})"
        )

    parent_ref_line: str | None = None
    if args.parent is not None:
        if args.parent < 1:
            errors.append(f"parent must be a positive issue number; got {args.parent}")
        else:
            structural_type = _infer_structural_type(title, issue_types, classification)
            if structural_type is None:
                errors.append(
                    f"cannot set --parent: issue title {title!r} has no recognised "
                    "[Type] prefix, so the parent-ref form is unknown"
                )
            else:
                type_entry = (issue_types.get("types") or {}).get(structural_type) or {}
                parent_ref_line = _parent_ref_line(type_entry, args.parent)
                if not parent_ref_line:
                    errors.append(
                        f"issue type {structural_type!r} declares no parent_ref_form; "
                        "cannot set a parent-ref"
                    )

    if errors:
        for e in errors:
            print(f"  [refused] {e}")
        print(
            "\n[refused] validation failed before any mutation; nothing written.",
            file=sys.stderr,
        )
        return 1

    # ---- build the plan (idempotent) ----
    results: list[FieldResult] = []
    label_add: list[str] = []
    label_remove: list[str] = []
    new_title: str | None = None

    if args.kind is not None:
        kind_results, kind_add, kind_remove, new_title = _plan_kind(
            kind=args.kind,
            title=title,
            current_labels=current_labels,
            issue_types=issue_types,
            classification=classification,
            substrate_map=substrate_map,
        )
        results.extend(kind_results)
        label_add.extend(kind_add)
        label_remove.extend(kind_remove)

    label_results, axis_add, axis_remove = _plan_labels(
        priority=args.priority,
        workstream=args.workstream,
        current_labels=current_labels,
        substrate_map=substrate_map,
        has_board=has_board,
    )
    results.extend(label_results)
    label_add.extend(axis_add)
    label_remove.extend(axis_remove)

    new_body: str | None = None
    if parent_ref_line is not None:
        new_body, parent_result = _plan_parent(body, parent_ref_line)
        results.append(parent_result)

    for r in results:
        marker = "ok" if r.ok else "refused"
        print(f"  [{marker}] {r.message}")

    body_changed = new_body is not None and new_body != body
    title_changed = new_title is not None and new_title != title
    any_change = bool(label_add or label_remove) or body_changed or title_changed

    if not any_change:
        print(f"\n[ok] #{args.issue_number}: no change (all fields already set).")
        return 0

    if args.dry_run:
        print("\n[dry-run] gh would be invoked; nothing written.")
        return 0
    if not args.yes and sys.stdin.isatty():
        reply = input("Write the change(s)? [y/N] ").strip().lower()
        if reply not in ("y", "yes"):
            print("aborted.", file=sys.stderr)
            return 0

    if label_add or label_remove:
        if not _gh_edit_labels(args.issue_number, label_add, label_remove, config):
            return 3
    if title_changed:
        if not _gh_write_title(args.issue_number, new_title or "", config):
            return 3
    if body_changed:
        stamped = provenance.stamp(
            new_body or "", provenance.read_versions(capability_root)
        )
        if not _gh_write_body(args.issue_number, stamped, config):
            return 3

    print(f"\n[ok] #{args.issue_number}: updated.")
    return 0


# ---- planning -------------------------------------------------------------


def _plan_labels(
    *,
    priority: str | None,
    workstream: str | None,
    current_labels: list[str],
    substrate_map: "axis_labels.SubstrateMap | None",
    has_board: bool,
) -> tuple[list[FieldResult], list[str], list[str]]:
    """Resolve priority/workstream to add/remove label sets (idempotent).

    Mirrors create-issue's `_build_labels` resolution through
    `axis_labels.resolve_write` (so a remapped or board substrate is honoured),
    then diffs against the issue's current labels: a value already present is a
    no-op; a changed value removes the stale `<axis>:*` label(s) and adds the new
    one. Under a board, the axis lives on a Projects-v2 field, not a label, so the
    write degrades with a note (mirroring move-issue's v1 board posture).
    """
    results: list[FieldResult] = []
    to_add: list[str] = []
    to_remove: list[str] = []

    for axis, value in (("priority", priority), ("workstream", workstream)):
        if value is None:
            continue
        if has_board:
            results.append(
                FieldResult(
                    field=axis,
                    ok=True,
                    changed=False,
                    message=(
                        f"{axis}: board substrate — lives on the Projects-v2 "
                        f"field, not a label; not set here (set on the board)"
                    ),
                )
            )
            continue
        resolved = axis_labels.resolve_write(axis, value, substrate_map)
        if not isinstance(resolved, str):
            results.append(
                FieldResult(
                    field=axis,
                    ok=True,
                    changed=False,
                    message=(
                        f"{axis}: unsupported under your substrate-map "
                        f"(value {value!r}); not labelled"
                    ),
                )
            )
            continue
        if resolved in current_labels:
            results.append(
                FieldResult(
                    field=axis,
                    ok=True,
                    changed=False,
                    message=f"{axis}: already {resolved!r} (no-op)",
                )
            )
            continue
        stale = [
            lbl for lbl in current_labels
            if axis_labels.is_axis_label(lbl, axis) and lbl != resolved
        ]
        to_remove.extend(stale)
        to_add.append(resolved)
        results.append(
            FieldResult(
                field=axis,
                ok=True,
                changed=True,
                message=f"{axis}: set {resolved!r}"
                + (f" (was {', '.join(stale)})" if stale else ""),
            )
        )

    return results, to_add, to_remove


def _plan_kind(
    *,
    kind: str,
    title: str,
    current_labels: list[str],
    issue_types: dict,
    classification: dict,
    substrate_map: "axis_labels.SubstrateMap | None",
) -> tuple[list[FieldResult], list[str], list[str], str | None]:
    """Resolve a kind change to a `type:*` label swap + title-prefix realignment.

    Reached only for a kind permitted on the issue's structural type — the
    up-front gate in `main` refuses the kind/structural mismatch DEC-011 declares
    a hard-reject before any planning runs. In practice that means: a kind-driven
    (task) issue with any kind, or epic/feature/umbrella with kind `feature` (the
    kind they carry by definition, which lands as a no-op here).

    The `type` axis is ALWAYS a label (per classification.yaml), so unlike
    priority/workstream there is no board-degrade path: the kind label resolves
    through the SAME `axis_labels.resolve_write` create-issue uses, then diffs
    against the issue's current `type:*` label(s) — already-correct is a no-op,
    a change removes the stale `type:*` label and adds the new one.

    Title-prefix realignment (the create-issue coupling, reused): the new prefix
    is read from classification.yaml's `title_prefix_by_value[<kind>]` — the same
    map create-issue's title composition uses, so prefix and label cannot diverge.
    The prefix is realigned only when the issue's structural type is kind-driven
    (the leaf `task`, per `structural_restriction`); for epic/feature/umbrella the
    only kind that reaches here is `feature`, whose structural prefix is already
    correct, so no realignment is planned. Returns
    ``(results, to_add, to_remove, new_title)`` where ``new_title`` is None when
    no title rewrite is planned.
    """
    results: list[FieldResult] = []
    to_add: list[str] = []
    to_remove: list[str] = []
    new_title: str | None = None

    resolved = axis_labels.resolve_write("type", kind, substrate_map)
    if not isinstance(resolved, str):
        results.append(
            FieldResult(
                field="kind",
                ok=True,
                changed=False,
                message=(
                    f"kind: unsupported under your substrate-map "
                    f"(value {kind!r}); not labelled"
                ),
            )
        )
        return results, to_add, to_remove, new_title

    if resolved in current_labels:
        results.append(
            FieldResult(
                field="kind",
                ok=True,
                changed=False,
                message=f"kind: already {resolved!r} (no-op)",
            )
        )
    else:
        stale = [
            lbl for lbl in current_labels
            if axis_labels.is_axis_label(lbl, "type") and lbl != resolved
        ]
        to_remove.extend(stale)
        to_add.append(resolved)
        results.append(
            FieldResult(
                field="kind",
                ok=True,
                changed=True,
                message=f"kind: set {resolved!r}"
                + (f" (was {', '.join(stale)})" if stale else ""),
            )
        )

    # Realign the title prefix only when the issue's structural type is
    # kind-driven (today: the leaf `task`). For epic/feature/umbrella the only
    # kind that reaches here is `feature` (the up-front gate refuses any other),
    # whose structural prefix already matches — so nothing to realign.
    structural_type = _infer_structural_type(title, issue_types, classification)
    if structural_type is not None and classification_rules.kind_drives_title(
        structural_type, classification
    ):
        target_prefix = classification_rules.title_prefix_by_value(classification).get(kind)
        if target_prefix:
            realigned = _retitle_prefix(title, target_prefix)
            if realigned is not None and realigned != title:
                new_title = realigned
                results.append(
                    FieldResult(
                        field="title",
                        ok=True,
                        changed=True,
                        message=f"title: realign prefix to [{target_prefix}]",
                    )
                )

    return results, to_add, to_remove, new_title


def _retitle_prefix(title: str, target_prefix: str) -> str | None:
    """Swap a leading `[...]` title prefix for `[<target_prefix>]`.

    Idempotent — an already-correct prefix returns the title unchanged. Returns
    None when the title has no recognisable `[...] ` prefix to swap (the caller
    only reaches here for a kind-driven structural type, which is inferred FROM a
    recognised prefix, so this is a defensive guard rather than an expected path).
    """
    m = re.match(r"^\[[^\]]+\]\s+(.*)$", title, flags=re.DOTALL)
    if not m:
        return None
    return f"[{target_prefix}] {m.group(1)}"


def _plan_parent(body: str, parent_ref_line: str) -> tuple[str, FieldResult]:
    """Rewrite the body's first parent-ref line to `parent_ref_line` (idempotent).

    A parent-ref is the first non-blank body line in one of the recognised forms
    (`<Label>: #<N>` or `Milestone: [#<N>](../milestone/<N>)`). When the first
    line already matches a parent-ref shape, it is replaced; otherwise the new
    parent-ref is prepended. Setting the parent to the value already present is a
    no-op.
    """
    lines = body.splitlines()
    # Find the first non-blank line index.
    first_idx = next((i for i, ln in enumerate(lines) if ln.strip()), None)

    if first_idx is not None and _is_parent_ref(lines[first_idx]):
        if lines[first_idx].strip() == parent_ref_line:
            return body, FieldResult(
                field="parent",
                ok=True,
                changed=False,
                message=f"parent: already {parent_ref_line!r} (no-op)",
            )
        old = lines[first_idx].strip()
        lines[first_idx] = parent_ref_line
        new_body = "\n".join(lines)
        if body.endswith("\n"):
            new_body += "\n"
        return new_body, FieldResult(
            field="parent",
            ok=True,
            changed=True,
            message=f"parent: set {parent_ref_line!r} (was {old!r})",
        )

    # No parent-ref present — prepend one with a blank-line separator.
    new_body = parent_ref_line + ("\n\n" + body if body.strip() else "\n")
    return new_body, FieldResult(
        field="parent",
        ok=True,
        changed=True,
        message=f"parent: set {parent_ref_line!r} (prepended)",
    )


_PARENT_REF_RES = (
    re.compile(r"^Milestone:\s+\[#(\d+)\]\(\.\./milestone/\1\)\s*$"),
    re.compile(r"^Milestone:\s+#\d+\s*$"),
    re.compile(r"^[A-Za-z]+:\s+#\d+\s*$"),
)


def _is_parent_ref(line: str) -> bool:
    """True when `line` is one of the recognised parent-ref forms (parity with edit-issue)."""
    s = line.strip()
    return any(rx.match(s) for rx in _PARENT_REF_RES)


# ---- schema / config readers (mirroring create-issue + edit-issue) --------


def _axis_values(classification: dict, axis: str) -> set[str]:
    """The declared values for a classification axis (e.g. priority levels)."""
    axes = classification.get("axes") if isinstance(classification, dict) else None
    if not isinstance(axes, dict):
        return set()
    entry = axes.get(axis)
    if not isinstance(entry, dict):
        return set()
    values = entry.get("values")
    out: set[str] = set()
    if isinstance(values, list):
        for v in values:
            if isinstance(v, str):
                out.add(v)
            elif isinstance(v, dict) and isinstance(v.get("value"), str):
                out.add(v["value"])
    return out


def _adopter_workstreams(config: dict) -> set[str]:
    """The adopter's declared workstream slugs (list or mapping form)."""
    ws = config.get("workstreams")
    if isinstance(ws, list):
        return {entry for entry in ws if isinstance(entry, str)}
    if isinstance(ws, dict):
        return set(ws.keys())
    return set()


def _infer_structural_type(
    title: str, issue_types: dict, classification: dict | None = None
) -> str | None:
    """Infer the structural type from the title prefix (parity with edit-issue)."""
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
    if classification:
        prefix_by_value = (
            classification.get("axes", {})
            .get("type", {})
            .get("title_prefix_by_value", {})
        )
        for _kind_value, kind_prefix in prefix_by_value.items():
            if isinstance(kind_prefix, str) and title.startswith(f"[{kind_prefix}] "):
                return "task"
    return None


def _parent_ref_line(type_entry: dict, parent_num: int) -> str:
    """Build the `<Label>: #<N>` parent-ref line (parity with create-issue)."""
    form = type_entry.get("parent_ref_form")
    if not form:
        return ""
    head = str(form).split(":", 1)[0].strip()
    if " or " in head:
        head = head.split(" or ", 1)[0].strip()
    return f"{head}: #{parent_num}"


# ---- gh write-back --------------------------------------------------------


def _gh_edit_labels(
    issue_number: int, add: list[str], remove: list[str], config: dict
) -> bool:
    cmd = ["gh", "issue", "edit", str(issue_number)]
    for lbl in add:
        cmd.extend(["--add-label", lbl])
    for lbl in remove:
        cmd.extend(["--remove-label", lbl])
    try:
        proc = gh_run(cmd, config, check=False)
    except FileNotFoundError:
        print("error: `gh` not on PATH. Install GitHub CLI.", file=sys.stderr)
        return False
    if proc.returncode != 0:
        print(
            f"error: gh issue edit (labels) failed (exit {proc.returncode}).\n"
            f"stderr: {proc.stderr.strip()}",
            file=sys.stderr,
        )
        return False
    return True


def _gh_write_title(issue_number: int, title: str, config: dict) -> bool:
    """Write the realigned title via `gh issue edit --title` (edit-issue's pattern)."""
    cmd = ["gh", "issue", "edit", str(issue_number), "--title", title]
    try:
        proc = gh_run(cmd, config, check=False)
    except FileNotFoundError:
        print("error: `gh` not on PATH. Install GitHub CLI.", file=sys.stderr)
        return False
    if proc.returncode != 0:
        print(
            f"error: gh issue edit (title) failed (exit {proc.returncode}).\n"
            f"stderr: {proc.stderr.strip()}",
            file=sys.stderr,
        )
        return False
    return True


def _gh_write_body(issue_number: int, body: str, config: dict) -> bool:
    """Write the rewritten body via `gh issue edit --body-file` (edit-issue's pattern)."""
    with tempfile.NamedTemporaryFile(
        "w", suffix=".md", encoding="utf-8", delete=False
    ) as f:
        f.write(body)
        body_path = f.name
    try:
        cmd = ["gh", "issue", "edit", str(issue_number), "--body-file", body_path]
        try:
            proc = gh_run(cmd, config, check=False)
        except FileNotFoundError:
            print("error: `gh` not on PATH. Install GitHub CLI.", file=sys.stderr)
            return False
        if proc.returncode != 0:
            print(
                f"error: gh issue edit failed (exit {proc.returncode}).\n"
                f"stderr: {proc.stderr.strip()}",
                file=sys.stderr,
            )
            return False
    finally:
        try:
            Path(body_path).unlink(missing_ok=True)
        except OSError:
            pass
    return True


# ---- argument parsing -----------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="set-field",
        description=(
            "Declaratively set an issue's kind / priority / workstream / parent "
            "classification field(s) in one batch call. Validates up front and "
            "refuses before any mutation on an unknown value; idempotent on "
            "re-run. Reuses create-issue's classification resolution (DEC-038); "
            "a kind change swaps the type:* label and realigns the title prefix."
        ),
    )
    parser.add_argument("issue_number", type=int, help="GitHub issue number.")
    parser.add_argument(
        "--kind",
        default=None,
        help=(
            "Classification `type:*` value (one of the adopter's classification "
            "type values, e.g. bug/feature/docs/test/refactor/maintenance). "
            "Swaps the prior type:* label and realigns the title prefix per "
            "classification.yaml's title_prefix_by_value when the title is "
            "kind-driven."
        ),
    )
    parser.add_argument(
        "--priority",
        default=None,
        help="Priority value (one of the adopter's classification priority values).",
    )
    parser.add_argument(
        "--workstream",
        default=None,
        help="Workstream slug (one of the adopter's declared workstreams).",
    )
    parser.add_argument(
        "--parent",
        type=int,
        default=None,
        help="Parent issue number; rewrites the body's first parent-ref line.",
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
        help="Validate + show the plan; do not invoke gh.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the confirmation prompt.",
    )
    session_guard.add_override_argument(parser)
    return parser


# ---- helpers --------------------------------------------------------------


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
    if not path.is_file():
        return []
    try:
        data = yaml_loader.load(path.read_text(encoding="utf-8")) or {}
    except (OSError, YAMLError):
        return []
    members = data.get("members") if isinstance(data, dict) else None
    return members if isinstance(members, list) else []


if __name__ == "__main__":
    sys.exit(main())
