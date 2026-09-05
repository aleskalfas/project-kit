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
classification.yaml), so --kind labels regardless of board substrate.

Board-carried axes (#724, from #723 / report #708)
-------------------------------------------------
Where `_lib/axis_carriage` resolves priority/workstream to the BOARD — a map that
binds the axis `board: true`, or a configured board on an axis the map is silent
about ([project-management:DEC-051-axis-carriage-activation]) — the value lives on
a Projects-v2 single-select field rather than a label, and set-field WRITES it. A
map that binds the axis to a label wins over the board flag, and the value is
written as that label instead: the flag is not consulted for an axis the adopter
has explicitly bound.

Everything about the board write is resolved from names the adopter already
speaks, at runtime, through the board READ seam (`_lib/board_fields`): the board
NUMBER in config → the project node id; the field whose NAME matches the axis
(`priority` → `Priority`, the Title-case convention Projects-v2 boards use); the
option whose NAME matches the requested value; and the issue's own card (item) id.

No hand-configured ids — before this, the ONLY writer of a board field was an
`after_create_issue` `set-board-field` hook whose entries carry field/option ids
the adopter had to dig out of the API by hand, which is the pain report #708
describes.

The write itself is constructed and executed only by `_lib/substrate_writes`
(ADR-031's sole constructor for a non-label substrate write) — the same primitive
the hook uses, so there is exactly one field-value write path in the capability.

Four board cases are REFUSED rather than guessed at, each naming what was looked
for and what the board actually offers (the diagnosis an adopter could not get
before):

  * **no card** — board membership is a post-creation step (DEC-019), so a
    just-filed issue may have no card yet. set-field refuses with the exact
    `gh project item-add` remediation instead of adding the card itself: adding an
    issue to a board is a membership decision, explicitly NOT part of the
    field-value substrate (ADR-031 point 3), and a verb asked to set a field must
    not silently enlarge the board's contents. Never a silent no-op either way.
  * **no such field / no such option** — the board has no `Priority` field, or no
    `High` option on it; the refusal lists the board's field names / the field's
    option names, both of which come back on the same read.
  * **not a single-select** — a text / number / date / iteration field has no
    option vocabulary to match a classification value against; out of scope
    (#724) and refused by type name rather than mangled into a text value.
  * **read failure** — a missing `read:project` scope or any other `gh` failure
    surfaces gh's stderr VERBATIM (the remedy, `gh auth refresh -s project`, is
    in that text).

When `config.yaml` claims the board for an axis while `substrate-map.yaml` binds
that same axis to a label, the two declarations disagree (the #708 root cause) and
set-field refuses the axis rather than picking a winner — pre-check fails on that
conflict and names both remediations.

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
  1  refusal — membership; up-front validation (nothing mutated); or a requested
     axis could not be set on its substrate: the board case cannot be resolved
     (no card, no such field, no such option, unsupported field type, or the board
     read failed), or the board and substrate-map disagree about who owns the axis
     (#709 / #724). Every such refusal happens BEFORE any write for that axis, so
     nothing is half-written. In the mixed case (some axes applied, some refused)
     the applicable writes ARE applied and the exit is still non-zero, with the
     summary naming what was and was not done — a partial application must never
     read as a clean success. `--dry-run` reports the same refusals with the same
     non-zero exit, since all of them are knowable without writing.
  2  usage error (issue not found; no field given; unknown value)
  3  gh write failure (a label/title/body edit, or a board field-value write,
     failed at the point of writing). Re-running is safe: application is
     idempotent.
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
from _lib import bootstrap_gate  # noqa: E402
from _lib import axis_carriage  # noqa: E402
from _lib import axis_labels  # noqa: E402
from _lib import board_fields  # noqa: E402
from _lib import classification_rules  # noqa: E402
from _lib import provenance  # noqa: E402
from _lib import session_guard  # noqa: E402
from _lib import substrate_writes  # noqa: E402
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


@dataclass(frozen=True)
class BoardState:
    """What one board READ round-trip knows, for planning a board field write.

    Gathered once per call (not per axis) by :func:`_read_board_state`; every
    board-carried axis in the same call plans against this one snapshot.
    `error` is the verbatim reason a read failed (gh's stderr where there is one);
    when it is set the other fields are unknown and every board axis refuses.
    `item_id` None with no `error` is the membership case — the issue has no card.
    """

    project_id: str | None = None
    item_id: str | None = None
    fields: tuple[dict, ...] = ()
    error: str | None = None
    board_ref: str = "the Projects-v2 board"
    membership_remediation: str = ""


@dataclass(frozen=True)
class BoardWrite:
    """One resolved, ready-to-execute board single-select write.

    Every id here came from a name the adopter speaks (see the module docstring);
    the write is handed to `substrate_writes.write_field_value` unchanged.
    """

    axis: str
    field_name: str
    field_id: str
    option_name: str
    option_id: str
    item_id: str
    project_id: str


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

    # Prerequisite gate (#747): refuse on an un-bootstrapped project rather
    # than operating on assumed defaults. See _lib/bootstrap_gate.py.
    if not bootstrap_gate.enforce("set-field", capability_root=capability_root):
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

    # `id` + `url` are for the board path: `id` is the issue's GraphQL node id (the
    # key the card lookup asks `projectItems` on) and `url` renders the exact
    # `gh project item-add` remediation when the card is missing. Both ride the one
    # `gh issue view` round-trip this call already makes.
    issue = gh_get_issue(
        args.issue_number, config, fields="title,body,labels,id,url"
    )
    if issue is None:
        return 2
    title = str(issue.get("title", ""))
    # Strip the footer on read; the seam re-stamps one on write (ADR-037).
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

    # Route each requested axis to the substrate that owns it, THEN plan on that
    # substrate. Routing is separate from planning so the board path (which needs
    # live reads to turn names into ids) never runs for a label-carried axis, and
    # the label planner stays pure.
    label_axes, board_axes, routing_results = _route_axes(
        priority=args.priority,
        workstream=args.workstream,
        config=config,
        substrate_map=substrate_map,
        board_id=config.get("projects_v2_board_id"),
    )
    results.extend(routing_results)

    board_writes: list[BoardWrite] = []
    if board_axes:
        board_state = _read_board_state(
            config, issue=issue, issue_number=args.issue_number
        )
        board_results, board_writes = _plan_board_fields(
            board_axes=board_axes,
            state=board_state,
            issue_number=args.issue_number,
        )
        results.extend(board_results)

    label_results, axis_add, axis_remove = _plan_labels(
        priority=label_axes.get("priority"),
        workstream=label_axes.get("workstream"),
        current_labels=current_labels,
        substrate_map=substrate_map,
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
    any_change = (
        bool(label_add or label_remove)
        or body_changed
        or title_changed
        or bool(board_writes)
    )

    # A refused field — an axis whose board write could not be resolved, or one the
    # board and the substrate-map both claim — must never be summarised as success:
    # neither as "all fields already set" nor as a bare "updated" (#709). It drives
    # a non-zero exit even when the other fields in the same call apply cleanly; the
    # summary says which is which so a partial application is legible.
    refused = [r for r in results if not r.ok]

    if not any_change:
        if refused:
            print(
                f"\n[refused] #{args.issue_number}: nothing written — "
                f"{_field_list(refused)} could not be set here (see above). "
                "This is NOT 'already set': the field(s) remain unset."
            )
            return 1
        print(f"\n[ok] #{args.issue_number}: no change (all fields already set).")
        return 0

    if args.dry_run:
        # The board plan is fully resolved by now (names → ids), so a dry-run can
        # report the concrete write it would make. The resolution itself is a READ:
        # nothing on the board was touched to learn this.
        for w in board_writes:
            print(
                f"  [dry-run] would set board field `{w.field_name}` = "
                f"{w.option_name!r} (field {w.field_id}, option {w.option_id}, "
                f"item {w.item_id})"
            )
        print("\n[dry-run] gh would be invoked; nothing written.")
        if refused:
            print(
                f"[refused] {_field_list(refused)} could not be set here even "
                "outside dry-run (see above)."
            )
            return 1
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
    for write in board_writes:
        if not _write_board_field(write, config):
            # The plan line above read `[ok] priority: set board field …`. That
            # write did not happen, so say so on the same stream the plan was
            # printed on before exiting non-zero — a failed write must never be
            # left looking like the reported plan (#709).
            print(
                f"\n[failed] #{args.issue_number}: board field "
                f"`{write.field_name}` = {write.option_name!r} was NOT written "
                f"(see stderr); {write.axis} remains unset."
            )
            return 3

    if refused:
        applied = [r for r in results if r.ok and r.changed]
        print(
            f"\n[partial] #{args.issue_number}: applied "
            f"{_field_list(applied) or 'nothing'}; REFUSED "
            f"{_field_list(refused)} (see above — not written on any substrate)."
        )
        return 1

    print(f"\n[ok] #{args.issue_number}: updated.")
    return 0


def _field_list(results: list[FieldResult]) -> str:
    """`priority, workstream` — the field names of `results`, for a summary line.

    Deduplicated, order-preserving: the summary names each field once even if a
    field contributed more than one result (a kind change contributes both `kind`
    and `title`).
    """
    seen: list[str] = []
    for r in results:
        if r.field not in seen:
            seen.append(r.field)
    return ", ".join(seen)


# ---- planning -------------------------------------------------------------


def _route_axes(
    *,
    priority: str | None,
    workstream: str | None,
    config: dict,
    substrate_map: "axis_labels.SubstrateMap | None",
    board_id: int | str | None = None,
) -> tuple[dict[str, str], dict[str, str], list[FieldResult]]:
    """Split the requested priority/workstream axes by the substrate that owns them.

    Returns ``(label_axes, board_axes, results)`` — the axes to plan as labels, the
    axes to plan as board single-selects, and any result the routing itself
    produced (today: the degrade refusal).

    **Which substrate owns the axis is asked of `_lib/axis_carriage`, and of
    nothing else** ([project-management:DEC-051-axis-carriage-activation] decision
    points 1 and 4). Where the map binds the axis, the binding is the answer and
    `has_projects_v2_board` is not consulted for it; where the map is silent, the
    flag governs exactly as before. This replaces the previous predicate — the flag
    crossed with `axis_is_label_bound` — which was the same pair pre-check's
    cross-substrate conflict check keyed on. That statement of the invariant is
    updated rather than preserved: the two claimants no longer *conflict*, so what
    the two sides must share is the ANSWER, not a duplicated cross, and one
    composition is the stronger guarantee of that.

    **Honest as-built note.** pre-check's refusal has NOT softened yet. [DEC-051]
    decision point 5 rules that it becomes a warning, and its own implications
    order that softening LAST — after the consumers are rewired — because relaxing
    it first would make the reported state less detectable than it is today. So
    between this change and that one, an adopter in the reported configuration gets
    a working write here and a hard failure from `pre-check`. That is the ordering
    the record asks for, not a disagreement about where the axis lives.

    The arms:

      * ``board`` ⇒ the board plan (the field write, resolved by name at write
        time);
      * ``kit-label`` / ``adopter-label`` ⇒ the label plan — the kit's own label in
        greenfield, the adopter's remapped label under a `label:` binding;
      * ``title`` / ``derived`` ⇒ **refused**, non-zero exit. These are substrates
        set-field does not write for these axes — it realigns a title prefix only
        for `--kind`, and a derived axis is computed from tracker state rather than
        set — so the axis is SERVED but this verb cannot serve it, and a value it
        declined to record must never read as success (#709). Routing them away
        from the label planner also stops a live mis-write: for a title-bound axis
        `resolve_write` returns the PREFIX string, which the label planner would
        apply as a `gh --label` the tracker does not have;
      * ``degrade`` ⇒ a NOTE (`ok=True`), not a refusal. Here the adopter has
        declared the axis `unsupported` (or omitted it from a present map, which
        the schema defines as equivalent): the value has nowhere to go BY THEIR
        OWN DECLARATION, which is degradation working as designed rather than a
        write the verb declined. That scoping is deliberate and predates this
        change (#709 draws the refusal line at the board/label disagreement), and
        it is what the rest of the capability does with a declared-unsupported axis
        — `create-issue` files the issue and emits an advisory. The value-level
        degrade is a different matter and IS a refusal; see `_plan_labels`.
    """
    label_axes: dict[str, str] = {}
    board_axes: dict[str, str] = {}
    results: list[FieldResult] = []
    board_ref = f" #{board_id}" if board_id is not None else ""

    for axis, value in (("priority", priority), ("workstream", workstream)):
        if value is None:
            continue
        carried = axis_carriage.carriage(axis, config, substrate_map)
        if carried == "board":
            board_axes[axis] = value
            continue
        if carried in ("kit-label", "adopter-label"):
            label_axes[axis] = value
            continue
        if carried == "degrade":
            # Declared unsupported (or omitted, which the schema defines as the
            # same): nothing carries the axis by the adopter's own declaration.
            results.append(
                FieldResult(
                    field=axis,
                    ok=True,
                    changed=False,
                    message=(
                        f"{axis}: unsupported under your substrate-map "
                        f"(value {value!r}); not set here"
                    ),
                )
            )
            continue
        # SERVED, but on a substrate this verb does not write. Refuse rather than
        # write nowhere and report success.
        where = axis_carriage.describe(axis, config, substrate_map)
        results.append(
            FieldResult(
                field=axis,
                ok=False,
                changed=False,
                message=(
                    f"{axis}: set-field does not write the substrate that carries "
                    f"`{axis}` — it is carried {where}. NOT SET: {value!r} was not "
                    f"recorded on any substrate. Bind `{axis}` to a label (or "
                    f"`board: true`, with a board configured{board_ref}) in "
                    f"project/substrate-map.yaml, or set the value on its own "
                    f"substrate directly."
                ),
            )
        )

    return label_axes, board_axes, results


def _plan_labels(
    *,
    priority: str | None,
    workstream: str | None,
    current_labels: list[str],
    substrate_map: "axis_labels.SubstrateMap | None",
) -> tuple[list[FieldResult], list[str], list[str]]:
    """Resolve priority/workstream to add/remove label sets (idempotent).

    Mirrors create-issue's `_build_labels` resolution through
    `axis_labels.resolve_write` (so a remapped substrate is honoured), then diffs
    against the issue's current labels: a value already present is a no-op; a
    changed value removes the stale `<axis>:*` label(s) and adds the new one.

    Pure — no gh reads. Only axes `_route_axes` assigned to the LABEL substrate
    reach here; a board-carried axis is planned by `_plan_board_fields` instead, so
    this function no longer needs to know whether a board exists.

    A DEGRADE reaching this function therefore means exactly ONE thing, and it is
    not "the axis is unsupported": routing has already established that a label
    carries this axis, so the only way `resolve_write` can decline is the
    value-unresolvable fourth arm (ADR-026) — the adopter's `remap` has no entry
    for this methodology value. That is a REFUSAL, not a no-op. Reporting it as
    `ok=True, changed=False` (which this did) let a value land on no substrate and
    still exit zero — the never-report-success-on-a-declined-write posture
    [project-management:DEC-051-axis-carriage-activation] decision point 5 requires
    be preserved on whichever path the inversion now enters.
    """
    results: list[FieldResult] = []
    to_add: list[str] = []
    to_remove: list[str] = []

    for axis, value in (("priority", priority), ("workstream", workstream)):
        if value is None:
            continue
        resolved = axis_labels.resolve_write(axis, value, substrate_map)
        if not isinstance(resolved, str):
            results.append(
                FieldResult(
                    field=axis,
                    ok=False,
                    changed=False,
                    message=(
                        f"{axis}: your substrate-map binds `{axis}` to your own "
                        f"labels but its `remap` has no entry for {value!r}, so "
                        f"there is no label to write. NOT SET: {value!r} was not "
                        f"recorded on any substrate. Add a `remap` entry for "
                        f"{value!r} in project/substrate-map.yaml (or pass a value "
                        f"your map remaps)."
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
        # Map-aware stale search: under a `label` binding the substrate is the
        # adopter's OWN label name, which carries no `<axis>:` prefix — a
        # prefix-only search would add the new label and leave the old one on the
        # issue, accumulating two values on a single-valued axis.
        stale = [
            lbl
            for lbl in axis_labels.carried_labels(axis, current_labels, substrate_map)
            if lbl != resolved
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


def _board_field_name(axis: str) -> str:
    """The Projects-v2 field name to look for, for a methodology `axis`.

    The Title-cased axis name (`priority` → `Priority`, `workstream` →
    `Workstream`) — the convention Projects-v2 boards use, and the name the write
    path now RESOLVES against the board's live field list (case-insensitively, per
    `board_fields.find_field`). Deliberately still not a config lookup: a per-axis
    field-name key would be a new adopter surface, and a board that does not carry
    the conventional name gets a refusal that lists the names it does carry — the
    adopter renames the field (or binds the axis to a label) rather than teaching
    the kit a mapping.
    """
    return axis.capitalize()


def _read_board_state(
    config: dict,
    *,
    issue: dict,
    issue_number: int,
) -> BoardState:
    """One board READ round-trip: project node id, the live field list, the card id.

    Everything a board write needs that config does not declare. All three reads go
    through the board READ seam (`_lib/board_fields`) and mutate nothing — so this
    runs unchanged under `--dry-run`, which is what lets a dry-run report the
    concrete write (and refuse a knowably-impossible one) without touching the
    board.

    Any failure is captured in `BoardState.error` with gh's stderr VERBATIM: the
    likely cause is a token without the `project` scope, and the remedy is in that
    text. A successful read with no card yields `item_id=None` — the membership
    case, which the planner refuses with the `gh project item-add` remediation
    composed here (it has the owner and the issue URL).
    """
    number = board_fields.board_number(config)
    board_ref = f"Projects-v2 board #{number}" if number else "the Projects-v2 board"
    owner = board_fields.default_owner(config)
    issue_url = issue.get("url") if isinstance(issue.get("url"), str) else None
    remediation = (
        f"gh project item-add {number or '<board-number>'} "
        f"--owner {owner or '<board-owner>'} "
        f"--url {issue_url or f'<url of issue #{issue_number}>'}"
    )

    project = board_fields.read_project_node_id(config, owner=owner)
    if not project.ok or not project.node_id:
        return BoardState(
            error=project.error or f"{board_ref} did not resolve to a project id.",
            board_ref=board_ref,
            membership_remediation=remediation,
        )

    fields_read = board_fields.read_fields(config, owner=owner)
    if not fields_read.ok:
        return BoardState(
            project_id=project.node_id,
            error=fields_read.error,
            board_ref=board_ref,
            membership_remediation=remediation,
        )

    issue_node_id = issue.get("id") if isinstance(issue.get("id"), str) else None
    if not issue_node_id:
        return BoardState(
            project_id=project.node_id,
            fields=fields_read.fields,
            error=(
                f"`gh issue view {issue_number}` returned no node id, so the "
                f"issue's card on {board_ref} cannot be looked up."
            ),
            board_ref=board_ref,
            membership_remediation=remediation,
        )

    item = board_fields.resolve_item_id(
        config, issue_node_id=issue_node_id, project_node_id=project.node_id
    )
    if not item.ok:
        return BoardState(
            project_id=project.node_id,
            fields=fields_read.fields,
            error=item.error,
            board_ref=board_ref,
            membership_remediation=remediation,
        )

    return BoardState(
        project_id=project.node_id,
        item_id=item.item_id,
        fields=fields_read.fields,
        board_ref=board_ref,
        membership_remediation=remediation,
    )


def _plan_board_fields(
    *,
    board_axes: dict[str, str],
    state: BoardState,
    issue_number: int,
) -> tuple[list[FieldResult], list[BoardWrite]]:
    """Resolve each board-carried axis to a single-select write, or refuse it.

    Pure — it plans against the `state` snapshot `_read_board_state` gathered, so
    every diagnosis below is reachable in a test without a network and is identical
    under `--dry-run`.

    The refusals, in the order they become knowable. Each names what was looked for
    AND what the board actually offers, because "no `Priority` field" without the
    field list leaves the adopter exactly where report #708 left them — guessing:

      1. **read failed** — nothing is known; surface gh's stderr verbatim.
      2. **no card** — the read succeeded and the issue has no item on the board.
         Refused with the exact `gh project item-add` command rather than adding
         the card: membership is a distinct operation (DEC-019; named out of the
         field-value substrate by ADR-031 point 3) and a decision about what
         belongs on the board, which a field write must not make silently.
      3. **no such field** — lists the board's field names.
      4. **not a single-select** — names the type found; #724 keeps text / number /
         date / iteration out of scope rather than inventing a serialisation.
      5. **no such option** — lists the field's option names. This is the
         classification-vocabulary-vs-board-vocabulary mismatch: the value already
         passed the up-front check against classification.yaml, so the board is
         what disagrees.

    A resolved axis returns `ok=True, changed=True` and a :class:`BoardWrite`.
    There is no pre-write value-equality read (unlike the label path's no-op
    detection): learning the card's CURRENT option costs another round-trip, and
    the write is convergent — re-running sets the same value. The reported line
    describes the write that will be made, which is honest either way.
    """
    results: list[FieldResult] = []
    writes: list[BoardWrite] = []

    for axis, value in board_axes.items():
        field_name = _board_field_name(axis)
        unset = f"NOT SET: {value!r} was not recorded anywhere."

        if state.error is not None:
            results.append(
                FieldResult(
                    field=axis,
                    ok=False,
                    changed=False,
                    message=(
                        f"{axis}: could not read {state.board_ref} to resolve "
                        f"`{field_name}` = {value!r} to ids. {unset}\n"
                        f"      reason: {state.error}"
                    ),
                )
            )
            continue

        if state.item_id is None:
            results.append(
                FieldResult(
                    field=axis,
                    ok=False,
                    changed=False,
                    message=(
                        f"{axis}: issue #{issue_number} has NO CARD on "
                        f"{state.board_ref}, so there is no item whose "
                        f"`{field_name}` field could be set. {unset} Add the card, "
                        f"then re-run:\n"
                        f"      {state.membership_remediation}\n"
                        f"      (set-field writes field VALUES; putting an issue on "
                        f"a board is a separate membership operation — DEC-019 — "
                        f"and not a side effect this verb takes on your behalf.)"
                    ),
                )
            )
            continue

        field = board_fields.find_field(state.fields, field_name)
        if field is None:
            offered = board_fields.field_names(state.fields)
            results.append(
                FieldResult(
                    field=axis,
                    ok=False,
                    changed=False,
                    message=(
                        f"{axis}: {state.board_ref} has NO FIELD named "
                        f"`{field_name}`. It offers: "
                        f"{', '.join(offered) or '(no fields)'}. {unset} Rename or "
                        f"add a `{field_name}` single-select on the board, or bind "
                        f"`{axis}` to a label in project/substrate-map.yaml — a "
                        f"binding wins over the board flag for the axis it names, "
                        f"so the board keeps working for everything else."
                    ),
                )
            )
            continue

        if not board_fields.is_single_select(field):
            results.append(
                FieldResult(
                    field=axis,
                    ok=False,
                    changed=False,
                    message=(
                        f"{axis}: board field `{field_name}` is a "
                        f"{board_fields.field_type(field)}, not a single-select — "
                        f"UNSUPPORTED FIELD TYPE. set-field writes single-select "
                        f"options only (text / number / date / iteration fields are "
                        f"out of scope), so it will not guess a serialisation for "
                        f"{value!r}. {unset}"
                    ),
                )
            )
            continue

        option_id = board_fields.option_id(field, value)
        if option_id is None:
            offered = board_fields.option_names(field)
            results.append(
                FieldResult(
                    field=axis,
                    ok=False,
                    changed=False,
                    message=(
                        f"{axis}: board field `{field_name}` has NO OPTION named "
                        f"{value!r}. It offers: "
                        f"{', '.join(offered) or '(no options)'}. {unset} The value "
                        f"is declared in classification.yaml, so it is the board's "
                        f"option list that disagrees — add the option on the board, "
                        f"or use one of the names it offers."
                    ),
                )
            )
            continue

        field_id = field.get("id")
        if not isinstance(field_id, str) or not field_id:
            results.append(
                FieldResult(
                    field=axis,
                    ok=False,
                    changed=False,
                    message=(
                        f"{axis}: board field `{field_name}` came back without an "
                        f"id, so it cannot be written. {unset}"
                    ),
                )
            )
            continue

        resolved_name = field.get("name")
        writes.append(
            BoardWrite(
                axis=axis,
                field_name=resolved_name if isinstance(resolved_name, str) else field_name,
                field_id=field_id,
                option_name=value,
                option_id=option_id,
                item_id=state.item_id,
                project_id=state.project_id or "",
            )
        )
        results.append(
            FieldResult(
                field=axis,
                ok=True,
                changed=True,
                message=(
                    f"{axis}: set board field `{field_name}` = {value!r} on "
                    f"{state.board_ref}"
                ),
            )
        )

    return results, writes


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

    The `type` axis is ALWAYS a label (per classification.yaml, and the map's
    `board:` arm is inadmissible on it), so unlike priority/workstream there is no
    board path here and no carriage question to ask: the kind label resolves
    through the SAME `axis_labels.resolve_write` create-issue uses, then diffs
    against the issue's current type label(s) — already-correct is a no-op, a
    change removes the stale one and adds the new one.

    **Known gap, unfixed here and NOT touched by the carriage rewiring
    (#712).** A `title-prefix`-bound `type` axis is not detected before resolving:
    `resolve_write` returns the PREFIX string (`[Task]`), which this plans as a
    `gh --label` the tracker does not have — the #454 failure, in set-field rather
    than create-issue, where `_build_labels` guards it by consulting the binding
    kind first. It is left alone deliberately rather than patched in passing: the
    right behaviour for such an adopter is a design question (realigning the title
    prefix may BE the correct write for them, in which case this should not refuse
    but retitle), and it is unrelated to which substrate the board flag claims.

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
        # Map-aware stale search, as in `_plan_labels`: under a `label` binding the
        # substrate is the adopter's own label name, which carries no `type:`
        # prefix, so a prefix-only search would leave the old kind label in place
        # beside the new one.
        stale = [
            lbl
            for lbl in axis_labels.carried_labels("type", current_labels, substrate_map)
            if lbl != resolved
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


def _write_board_field(write: BoardWrite, config: dict) -> bool:
    """Execute one resolved board single-select write; True on success.

    The write is obtained from `substrate_writes.write_field_value` — ADR-031's
    sole constructor for a non-label substrate write, the same primitive the
    `set-board-field` hook uses. set-field never string-builds a `gh project
    item-edit` argv itself; the difference between this call site and the hook's is
    only WHERE the ids came from (resolved here from names, hand-authored there).

    On failure the primitive's `error` — gh's stderr verbatim — is printed and the
    caller exits 3. Nothing is retried and nothing else is rolled back: application
    is idempotent, so a re-run converges.
    """
    result = substrate_writes.write_field_value(
        config,
        item_id=write.item_id,
        field_id=write.field_id,
        project_id=write.project_id,
        single_select_option_id=write.option_id,
    )
    if not result.ok:
        print(
            f"error: writing board field `{write.field_name}` = "
            f"{write.option_name!r} for {write.axis} failed.\n"
            f"stderr: {result.error or 'no stderr'}",
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
            "a kind change swaps the type:* label and realigns the title prefix. "
            "Under a Projects-v2 board, priority/workstream are written as board "
            "single-select values — field and option resolved by NAME at runtime — "
            "and refused with a diagnosis (naming what the board offers) when the "
            "issue has no card, or the field / option / field type cannot serve it."
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
        help=(
            "Priority value (one of the adopter's classification priority values). "
            "Written as a label, or — under a Projects-v2 board — as the board's "
            "`Priority` single-select option."
        ),
    )
    parser.add_argument(
        "--workstream",
        default=None,
        help=(
            "Workstream slug (one of the adopter's declared workstreams). Written "
            "as a label, or — under a Projects-v2 board — as the board's "
            "`Workstream` single-select option."
        ),
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
