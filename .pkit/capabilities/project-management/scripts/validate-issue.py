#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — validate-issue (verb-subject per DEC-020).

Validates an existing GitHub issue against the methodology's body
shape: title regex per type, per-type required sections, classification
axes presence + uniqueness, parent-ref first line. Emits findings
tagged by the severity tokens from validation-severity.yaml (hard-
reject / bypassable-with-audit / warning).

Membership predicate per DEC-021 runs at startup; closed mode refuses
non-members (the gate applies to all mutating + read commands in the
v0.3.0 stub).

Self-contained via PEP 723; runs via
  uv run --script .pkit/capabilities/project-management/scripts/validate-issue.py 42

Or via the dispatcher:
  pkit project-management validate-issue 42

Exit codes:
  0  every check passed or only warning-level findings
  1  one or more hard-reject (or unbypassed bypassable-with-audit) findings
  2  usage error (issue not found; gh failure)
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import bootstrap_gate  # noqa: E402
from _lib import axis_labels  # noqa: E402
from _lib import classification_rules  # noqa: E402
from _lib.gh import gh_get_issue, gh_run, load_adopter_config  # noqa: E402
from _lib.membership import (  # noqa: E402
    CAPABILITY_NAME,
    check_membership,
    resolve_capability_root,
    resolve_invoker_identity,
)
from _lib.placeholder_detection import (  # noqa: E402
    PHASE_CREATE,
    PHASE_TRANSITION,
    detect_placeholder_residuals,
)


SEVERITY_HARD_REJECT = "hard-reject"
SEVERITY_BYPASSABLE = "bypassable-with-audit"
SEVERITY_WARNING = "warning"


@dataclass(frozen=True)
class Finding:
    """One validation finding."""

    severity: str
    label: str
    detail: str


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate an existing GitHub issue against the project-management "
            "methodology's body + classification rules. Reports findings by "
            "severity; exit code is the contract for CI gating."
        ),
    )
    parser.add_argument(
        "issue_number",
        type=int,
        help="GitHub issue number to validate.",
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
        "--phase",
        choices=(PHASE_CREATE, PHASE_TRANSITION),
        default=PHASE_TRANSITION,
        help=(
            "Validation phase. 'create' — body was just stamped from the "
            "template (empty-checkbox-section is a warning, not a hard-reject). "
            "'transition' (default) — body is being validated at a lifecycle "
            "transition; empty-checkbox-section is a hard-reject per DEC-031."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of human-readable text.",
    )
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
    if not bootstrap_gate.enforce("validate-issue", capability_root=capability_root):
        return 2

    yaml_loader = YAML(typ="safe")

    config = load_adopter_config(capability_root)

    members = _read_members(capability_root, yaml_loader)
    invoker = resolve_invoker_identity(config=config)
    membership = check_membership(members, invoker)
    if not membership.allowed:
        print(membership.refusal_message, file=sys.stderr)
        return 1

    # Read schemas + adopter config.
    issue_types = _read_yaml(capability_root / "schemas" / "issue-types.yaml", yaml_loader)
    titles = _read_yaml(capability_root / "schemas" / "titles.yaml", yaml_loader)
    body_format = _read_yaml(capability_root / "schemas" / "body-format.yaml", yaml_loader)
    classification = _read_yaml(
        capability_root / "schemas" / "classification.yaml", yaml_loader
    )
    config = _read_yaml(capability_root / "project" / "config.yaml", yaml_loader)
    mandatory_state = _read_yaml(
        capability_root / "schemas" / "mandatory-issue-state.yaml", yaml_loader
    )

    issue = _gh_get_issue(args.issue_number, config)
    if issue is None:
        return 2

    # The adopter's substrate-map (DEC-036 / ADR-026), loaded once and threaded
    # into the validation. None ⇒ greenfield (no map). The type-presence gate
    # and the hierarchy mode below both read it, so load it here rather than
    # re-walking the tree per consumer.
    substrate_map = axis_labels.load_substrate_map(capability_root)

    # The adopter's hierarchy MODE (DEC-036 D4). Governs whether a missing /
    # malformed parent-ref first line hard-rejects (gated / greenfield) or
    # degrades to a warning (advisory) — the body-format.yaml parent-ref rule
    # is one of the two parent-requiredness rules advisory relaxes. None map ⇒
    # gated (greenfield, byte-unchanged); a present map carries its own mode.
    hierarchy = (
        axis_labels.hierarchy_disposition(substrate_map)
        if substrate_map is not None
        else axis_labels.HIERARCHY_GATED
    )

    findings = _validate_issue(
        issue=issue,
        issue_types=issue_types,
        titles=titles,
        body_format=body_format,
        classification=classification,
        config=config,
        mandatory_state=mandatory_state,
        capability_root=capability_root,
        phase=args.phase,
        hierarchy=hierarchy,
        substrate_map=substrate_map,
    )

    if args.json:
        out = {
            "issue_number": args.issue_number,
            "issue_title": issue.get("title", ""),
            "findings": [
                {"severity": f.severity, "label": f.label, "detail": f.detail}
                for f in findings
            ],
        }
        print(json.dumps(out, indent=2))
    else:
        _print_findings(args.issue_number, issue, findings)

    # Exit code: non-zero on any hard-reject or bypassable.
    has_blocking = any(
        f.severity in (SEVERITY_HARD_REJECT, SEVERITY_BYPASSABLE)
        for f in findings
    )
    return 1 if has_blocking else 0


# ---- validation -----------------------------------------------------


def _validate_issue(
    *,
    issue: dict,
    issue_types: dict,
    titles: dict,
    body_format: dict,
    classification: dict | None = None,
    config: dict,
    mandatory_state: dict | None = None,
    capability_root: Path | None = None,
    phase: str = PHASE_TRANSITION,
    hierarchy: str = axis_labels.HIERARCHY_GATED,
    substrate_map: "axis_labels.SubstrateMap | None" = None,
) -> list[Finding]:
    findings: list[Finding] = []
    title = str(issue.get("title", ""))
    body = str(issue.get("body") or "")
    labels = [
        lbl.get("name", "") if isinstance(lbl, dict) else str(lbl)
        for lbl in (issue.get("labels") or [])
    ]
    assignees = issue.get("assignees") or []

    # Infer structural type from the title prefix, substrate-aware (#553): the
    # kit's own prefix vocabulary in greenfield, the ADOPTER's declared prefixes
    # when the substrate-map binds `type` via title-prefix.
    structural_type = _infer_structural_type(title, issue_types, substrate_map)

    # Title format / pattern.
    #
    # The kit's title vocabulary (issue-types prefixes + the titles.yaml regex)
    # is the authority ONLY in greenfield. Under a substrate-map:
    #   * `type` bound to title-prefix ⇒ the type IS title-carried, and the
    #     yardstick is the ADOPTER's prefixes (resolved above). A title matching
    #     none of them resolves to NO structural type — an undeterminable
    #     close-gate failure, so it hard-rejects `title.format` exactly as
    #     greenfield hard-rejects an unknown prefix (only the message vocabulary
    #     differs, naming the adopter's declared prefixes rather than the kit's;
    #     architect ruling (b), #553); the kit's titles.yaml regex (which
    #     hardcodes `[EPIC]` etc.) does NOT additionally apply (the adopter owns
    #     the title format).
    #   * `type` bound to label/derive/unsupported/absent ⇒ the type is NOT
    #     title-carried; no title-format demand is made (its presence gate / the
    #     capability matrix covers the axis via its own substrate).
    type_title_carried = substrate_map is None or axis_labels.axis_is_title_carried(
        "type", substrate_map
    )
    if type_title_carried and structural_type is None:
        expected = _expected_type_prefixes(issue_types, substrate_map)
        if substrate_map is None:
            findings.append(
                Finding(
                    SEVERITY_HARD_REJECT,
                    "title.format",
                    f"title {title!r} does not match any known type prefix "
                    f"(expected one of {', '.join(expected)}).",
                )
            )
        else:
            findings.append(
                Finding(
                    SEVERITY_HARD_REJECT,
                    "title.format",
                    f"title {title!r} matches none of the adopter's declared "
                    f"substrate-map type prefixes "
                    f"(expected one of {', '.join(expected)}).",
                )
            )
    elif structural_type is not None and substrate_map is None:
        # Greenfield: also enforce the titles.yaml regex pattern. Under a present
        # map the kit's regex does not apply (the adopter owns the title format).
        pattern = _title_pattern_for(titles, structural_type)
        if pattern and not re.match(pattern, title):
            findings.append(
                Finding(
                    SEVERITY_HARD_REJECT,
                    "title.pattern",
                    f"title does not match titles.yaml pattern for "
                    f"{structural_type!r}: {pattern!r}",
                )
            )

    # Type axis presence (per DEC-012), fully substrate-aware per-binding (#553).
    #
    # The kit's `type:*` labels are the type substrate ONLY in greenfield. Under a
    # substrate-map the type axis resolves through the adopter's OWN substrate, so
    # the presence demand is per-binding — and it mirrors pre-check's disposition
    # on the same repo, so the two gates agree across every binding:
    #   * kit labels (greenfield)  — require exactly one `type:*` label, and
    #                                cross-check its kind vs the structural type
    #                                (DEC-011). Byte-unchanged.
    #   * title-prefix             — the type IS the title prefix; a missing /
    #                                unrecognised one is the `title.format` finding
    #                                above. No label is written or demanded.
    #   * label remap              — require one of the adopter's remapped type
    #                                labels (resolve_read). A missing one is a
    #                                genuine missing-value, gated as greenfield
    #                                gates a missing `type:*`.
    #   * derive / unsupported     — nothing to carry; no presence demand.
    # Every arm routes through the seam (axis_expects_kit_labels / axis_is_label_
    # bound / resolve_read) — no second source of truth for "which substrate?".
    if axis_labels.axis_expects_kit_labels("type", substrate_map):
        # --- Greenfield: the kit's `type:*` labels are the substrate. ---
        type_labels = [lbl for lbl in labels if axis_labels.is_axis_label(lbl, "type")]
        if len(type_labels) == 0:
            findings.append(
                Finding(
                    SEVERITY_HARD_REJECT,
                    "classification.type.missing",
                    "no `type:*` label present (required by classification.yaml).",
                )
            )
        elif len(type_labels) > 1:
            findings.append(
                Finding(
                    SEVERITY_HARD_REJECT,
                    "classification.type.multiple",
                    f"multiple `type:*` labels — must be mutually exclusive: "
                    f"{', '.join(type_labels)}",
                )
            )
        else:
            # Exactly one `type:*` label — cross-check the kind against the issue's
            # structural type (DEC-011's kind/structural restriction). A
            # non-`feature` kind on an epic/feature/umbrella manufactures the
            # kind/structural mismatch that breaks the closing PR's Conventional-
            # Commits `<type>` derivation. This is the validate-issue enforcement
            # point DEC-011 names ("refused at create-issue and at validate-issue").
            # Reads `allowed_structural_types_per_kind` via the SAME shared
            # predicate create-issue / set-field call — single source of truth.
            # Fires only when the structural type is known (the title.format
            # finding above already covers an unrecognised prefix).
            #
            # DEC-011 cross-check stays inert in brownfield BY CONSTRUCTION: it
            # lives inside this greenfield-only branch, and in brownfield the kit
            # writes no `type:*` label to cross-check (kind and structural type are
            # the same title-derived signal there — nothing to cross-check).
            #
            # Severity is phase-split (architect review, #410), mirroring the
            # placeholder-residual phase pattern (detect_placeholder_residuals):
            #   - `--phase create` — hard-reject: refuse the mismatch at the point
            #     of manufacture, using the schema's authored `mismatch_severity`
            #     token (hard-reject in the shipped classification).
            #   - `--phase transition` (validate-issue's default) — the SAME
            #     finding at warning: a pre-existing container-kind mismatch
            #     corrupts the closing-PR conv-type derivation (a create-PR-time
            #     concern), NOT the transition in flight. Reporting rather than
            #     blocking keeps a lifecycle transition from being walled on
            #     traversal of a mismatched live ancestor (e.g. EPIC #128).
            # Any phase other than `transition` (only `create` today) keeps the
            # schema-authored severity — the hard-reject is the default posture,
            # and only the transition gate relaxes it.
            kind = axis_labels.read("type", labels)
            if (
                kind is not None
                and structural_type is not None
                and not classification_rules.kind_allowed_for_structural_type(
                    kind, structural_type, classification or {}
                )
            ):
                if phase == PHASE_TRANSITION:
                    severity = SEVERITY_WARNING
                else:
                    severity = _severity_from_token(
                        classification_rules.mismatch_severity_token(
                            classification or {}
                        )
                    )
                findings.append(
                    Finding(
                        severity,
                        "classification.type.structural-mismatch",
                        f"kind {kind!r} (its type:* label) is not valid for "
                        f"structural type {structural_type!r} — epic/feature/"
                        "umbrella carry kind 'feature' by definition "
                        "(classification.yaml structural_restriction / DEC-011). "
                        "Re-file the non-feature kind as a Task, or set the kind "
                        "to 'feature'.",
                    )
                )
    elif axis_labels.axis_is_label_bound("type", substrate_map):
        # --- Present map, `type` bound to an adopter LABEL remap. ---
        # The adopter's own type labels are the substrate; require one present
        # (resolve_read reverse-maps it to the kit value, or None if absent). A
        # missing one is a genuine missing-value — hard-reject, exactly as
        # greenfield gates a missing `type:*` (G1). No DEC-011 cross-check: the
        # kind/structural cross-check is greenfield-only (above).
        if axis_labels.resolve_read("type", labels, substrate_map) is None:
            findings.append(
                Finding(
                    SEVERITY_HARD_REJECT,
                    "classification.type.missing",
                    "no type label present — substrate-map.yaml binds `type` to a "
                    "label remap; one of the adopter's remapped type labels is "
                    "required (see the `type` binding in project/substrate-map.yaml).",
                )
            )
    # else: `type` bound to title-prefix (handled by title.format above), derive,
    # unsupported, or absent — nothing to carry, so no presence demand (mirrors
    # pre-check reporting the axis served/degraded via its own substrate).

    has_board = bool(config.get("has_projects_v2_board", False))
    if not has_board:
        # Resolve each axis THROUGH THE SEAM, exactly as `type` does above
        # (#742). Reading the kit prefix unconditionally was wrong twice over
        # for a no-board adopter carrying a substrate map:
        #
        #   * LABEL-BOUND axis — `create-issue` writes the adopter's REMAPPED
        #     label (e.g. `P1`) through the write seam, while this gate demanded
        #     the kit `priority:High`. Writer and reader disagreed and NOTHING
        #     detected it: pre-check's substrate-conflict check (#709) keys on a
        #     configured board crossed with a label binding, so with no board it
        #     skips. Same unsatisfiable-gate class as the reported board case,
        #     through a path with no alarm on it.
        #   * OMITTED axis in a PRESENT map — demanding the kit label is the
        #     exact hazard DEC-036 D2 exists to prevent ("a brownfield adopter
        #     who simply omits an axis they can't serve must get degradation,
        #     not a silent fall-back to greenfield refusal on labels they cannot
        #     create"). An omitted axis degrades; it does not fall back.
        #
        # Greenfield (no map at all) is byte-unchanged: kit labels, same
        # findings, same severities.
        for axis, kit_label_glob in (("priority", "`priority:*`"), ("workstream", "`workstream:*`")):
            if axis_labels.axis_is_label_bound(axis, substrate_map):
                # The adopter's own labels are the substrate; require one.
                # Presence-only, mirroring the `type` bound arm (no multiplicity
                # check there either — the remap's own shape governs).
                if axis_labels.resolve_read(axis, labels, substrate_map) is None:
                    findings.append(
                        Finding(
                            SEVERITY_HARD_REJECT,
                            f"classification.{axis}.missing",
                            f"no {axis} label present — substrate-map.yaml binds "
                            f"`{axis}` to a label remap; one of the adopter's "
                            f"remapped {axis} labels is required (see the "
                            f"`{axis}` binding in project/substrate-map.yaml).",
                        )
                    )
            elif axis_labels.axis_expects_kit_labels(axis, substrate_map):
                # Greenfield: the kit's own `<axis>:*` label. Unchanged.
                present = [lbl for lbl in labels if axis_labels.is_axis_label(lbl, axis)]
                if len(present) == 0:
                    findings.append(
                        Finding(
                            SEVERITY_HARD_REJECT,
                            f"classification.{axis}.missing",
                            f"no {kit_label_glob} label present (required in "
                            "label-fallback mode per classification.yaml).",
                        )
                    )
                elif len(present) > 1:
                    findings.append(
                        Finding(
                            SEVERITY_HARD_REJECT,
                            f"classification.{axis}.multiple",
                            f"multiple {kit_label_glob} labels: {', '.join(present)}",
                        )
                    )
            # else: present map, axis bound to title-prefix / derive /
            # unsupported / absent — nothing kit-side to carry, so no presence
            # demand (mirrors the `type` arm's else, and DEC-036 D2's degrade).

    # Mandatory assignment (per DEC-019 / mandatory-issue-state.yaml).
    state_fields = (mandatory_state or {}).get("required_fields") or {}
    if not assignees:
        assignee_field = state_fields.get("assignee") or {}
        sev = _severity_from_token(assignee_field.get("drift_severity")) if assignee_field else SEVERITY_WARNING
        findings.append(
            Finding(
                sev,
                "assignment.missing",
                "no assignee. Mandatory per DEC-019 (mandatory-issue-state.yaml).",
            )
        )

    # Board membership drift (per DEC-019 / mandatory-issue-state.yaml).
    # Only fires for board-substrate adopters. We surface a finding when
    # the issue is open + board configured + the issue's `projectItems`
    # is empty (best-effort; the gh JSON surface for project membership
    # is limited at v1 so this is gated to data we have).
    if has_board and state_fields.get("board_membership"):
        project_items = issue.get("projectItems")
        board_field = state_fields["board_membership"]
        sev = _severity_from_token(board_field.get("drift_severity"))
        if isinstance(project_items, list) and len(project_items) == 0:
            findings.append(
                Finding(
                    sev,
                    "board_membership.missing",
                    "issue is not on the configured Projects v2 board. "
                    "Mandatory per DEC-019.",
                )
            )
        elif not isinstance(project_items, list):
            # UNVERIFIED is not MISSING, and it is not satisfied either (#740).
            # `projectItems` absent / null / non-list means membership could not
            # be DETERMINED — an unreadable board, a token without the project
            # scope, or a partial-success GraphQL reply carrying an errors array.
            # The prior condition (`is not None and isinstance(list) and len==0`)
            # skipped this branch entirely, so an undeterminable membership was
            # silently indistinguishable from a satisfied one: a check that
            # passes on a value it could not read is indistinguishable, in the
            # adopter's repo, from a check that does not exist.
            #
            # Reported at DEC-019's OWN `drift_severity` (warning) — this adds no
            # severity, verdict token, exit code, or network call; the payload is
            # already fetched. The message is deliberately distinct from
            # `.missing`: sending an adopter to "add this issue to the board"
            # when the issue may already be on it is the wrong diagnosis, and a
            # wrong diagnosis teaches distrust of the gate.
            findings.append(
                Finding(
                    sev,
                    "board_membership.unverified",
                    "could not determine Projects v2 board membership "
                    "(no projectItems in the issue payload — board unreadable, "
                    "token missing the project scope, or a partial API reply). "
                    "Membership is mandatory per DEC-019; this is NOT a report "
                    "that the issue is off the board.",
                )
            )

    # Per-type required body sections.
    if structural_type is not None:
        bodies = body_format.get("bodies") or {}
        type_body = bodies.get(structural_type)
        if isinstance(type_body, dict):
            required = type_body.get("required_sections") or []
            for section in required:
                if not isinstance(section, dict):
                    continue
                heading = str(section.get("heading", ""))
                if heading and heading not in body:
                    severity = _severity_from_token(section.get("severity"))
                    findings.append(
                        Finding(
                            severity,
                            "body.required-section",
                            f"missing required section {heading!r} "
                            f"({structural_type} body).",
                        )
                    )

        # Parent-ref first line.
        type_entry = (issue_types.get("types") or {}).get(structural_type)
        if isinstance(type_entry, dict):
            parent_ref_optional = bool(type_entry.get("parent_ref_optional", False))
            parent_ref_form = str(type_entry.get("parent_ref_form", ""))
            if parent_ref_form and not parent_ref_optional:
                first_line = body.lstrip().split("\n", 1)[0]
                # New canonical form: `Milestone: [#<N>](../milestone/<N>)`
                _NEW_MILESTONE_RE = re.compile(
                    r"^Milestone:\s+\[#(\d+)\]\(\.\./milestone/\1\)\s*$"
                )
                # Old (deprecated) form: `Milestone: #<N>` — accepted with
                # a warning during the grace period; suggests upgrading.
                _OLD_MILESTONE_RE = re.compile(r"^Milestone:\s+#\d+\s*$")
                # Plain issue-parent form: `<Label>: #<N>` (EPIC, Feature, etc.)
                _ISSUE_PARENT_RE = re.compile(r"^[A-Za-z]+:\s+#\d+\s*$")

                if _NEW_MILESTONE_RE.match(first_line):
                    # New form — clean pass.
                    pass
                elif _OLD_MILESTONE_RE.match(first_line):
                    # Old plain form — accepted with a deprecation warning.
                    findings.append(
                        Finding(
                            SEVERITY_WARNING,
                            "body.parent-ref.milestone-old-form",
                            "milestone parent-ref uses the old `Milestone: #<N>` "
                            "form; update to "
                            "`Milestone: [#<N>](../milestone/<N>)` so the link "
                            "points to the milestone rather than an issue.",
                        )
                    )
                elif not _ISSUE_PARENT_RE.match(first_line):
                    # Neither milestone form nor a valid issue-parent ref.
                    #
                    # Hierarchy-aware per DEC-036 D4: the body-format.yaml
                    # parent-ref rule is one of the two parent-requiredness rules
                    # advisory relaxes. Under `hierarchy: advisory` (a flat
                    # brownfield tracker that records the parent-ref as plain
                    # body-text, or has none) this degrades to a warning so the
                    # flat adopter is NOT walled at the first transition after
                    # create-issue already let them file parentless. Under
                    # `gated` / greenfield it stays a hard-reject, byte-unchanged.
                    # (Containment is untouched — advisory relaxes requiredness,
                    # never nesting.)
                    if hierarchy == axis_labels.HIERARCHY_ADVISORY:
                        findings.append(
                            Finding(
                                SEVERITY_WARNING,
                                "body.parent-ref",
                                f"first body line does not match the parent-ref "
                                f"form {parent_ref_form!r}; got {first_line!r}. "
                                f"Advisory under hierarchy: advisory — a flat "
                                f"tracker is not required to carry a "
                                f"machine-checkable parent-ref.",
                            )
                        )
                    else:
                        findings.append(
                            Finding(
                                SEVERITY_HARD_REJECT,
                                "body.parent-ref",
                                f"first body line does not match the parent-ref "
                                f"form {parent_ref_form!r}; got {first_line!r}. "
                                f"If your tracker is flat / brownfield, set "
                                f"`hierarchy: advisory` in substrate-map.yaml so "
                                f"parent-refs are recorded but not required.",
                            )
                        )

        # Residual-placeholder detection per DEC-031.
        if capability_root is not None:
            for sev, label, detail in detect_placeholder_residuals(
                body=body,
                structural_type=structural_type,
                body_format=body_format,
                capability_root=capability_root,
                phase=phase,
            ):
                findings.append(Finding(sev, label, detail))

    # Universal body rules — minimal subset.
    if re.search(r"^# [^#]", body, flags=re.MULTILINE):
        findings.append(
            Finding(
                SEVERITY_HARD_REJECT,
                "body.h1",
                "body contains an h1 (`# ...`) heading; the issue title "
                "is the h1. Use `## Title` for sections.",
            )
        )
    if re.search(r"[A-Za-z0-9_/\.\-]+\.[a-z]+:\d+\b", body):
        findings.append(
            Finding(
                SEVERITY_WARNING,
                "body.file-line-refs",
                "body contains file:line references; line numbers go stale.",
            )
        )

    return findings


def _infer_structural_type(
    title: str,
    issue_types: dict,
    substrate_map: "axis_labels.SubstrateMap | None" = None,
) -> str | None:
    """Map the title prefix to the structural type name, substrate-aware (#553).

    The prefix vocabulary the title is read against depends on the substrate:

    * **Greenfield** (``substrate_map is None``) ⇒ the kit's own rendered
      prefixes from ``issue-types.yaml`` (``[EPIC]`` / ``[Feature]`` /
      ``[Umbrella]`` / ``[Task]``), byte-unchanged.
    * **Map binds ``type`` via ``title-prefix``** ⇒ the ADOPTER's own declared
      prefixes, via the seam's :func:`axis_labels.resolve_title_prefix_read` (which
      reads the same binding shape ``pre-check`` validates against). This is the
      R1 fix: an AUJ ``[Epic]`` title (adopter prefix, ≠ the kit's ``[EPIC]``)
      resolves here instead of failing ``title.format`` against the kit vocabulary.
    * **Map binds ``type`` otherwise** (``label`` / ``derive`` / ``unsupported`` /
      absent) ⇒ ``None`` — the type is not carried in the title under such a
      binding, so the kit prefix vocabulary does not apply (mirrors ``pre-check``
      skipping title-prefix alignment for non-title-prefix bindings). The caller
      keys the ``title.format`` demand on whether the type is title-carried, so a
      ``None`` here does NOT spuriously fail a label-bound brownfield issue.
    """
    if substrate_map is not None:
        if axis_labels.axis_title_prefix_remap("type", substrate_map) is None:
            # `type` not title-carried under the map — the kit prefix vocabulary
            # does not apply; the structural type is not read from the title.
            return None
        return axis_labels.resolve_title_prefix_read("type", title, substrate_map)

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


def _expected_type_prefixes(
    issue_types: dict,
    substrate_map: "axis_labels.SubstrateMap | None" = None,
) -> list[str]:
    """The bracketed type prefixes a title is expected to carry, for the error text.

    Greenfield ⇒ the kit's own rendered prefixes; a ``title-prefix``-bound ``type``
    ⇒ the adopter's declared prefixes (already bracketed, e.g. ``[Task]``). Kept
    in step with :func:`_infer_structural_type` so the ``title.format`` message
    names the SAME vocabulary the inference actually validated against.
    """
    if substrate_map is not None:
        remap = axis_labels.axis_title_prefix_remap("type", substrate_map)
        if remap is not None:
            return sorted(remap.values())
    prefixes: list[str] = []
    for entry in (issue_types.get("types") or {}).values():
        if not isinstance(entry, dict):
            continue
        prefix = entry.get("title_prefix", "")
        case = entry.get("title_case", "title")
        rendered = str(prefix).upper() if case == "upper" else str(prefix)
        if rendered:
            prefixes.append(f"[{rendered}]")
    return prefixes


def _title_pattern_for(titles: dict, structural_type: str) -> str | None:
    formats = titles.get("formats") or {}
    key = f"issue-{structural_type}"
    entry = formats.get(key)
    if isinstance(entry, dict):
        pattern = entry.get("pattern")
        if isinstance(pattern, str):
            return pattern
    return None


def _severity_from_token(token: Any) -> str:
    """Parse a `[validation-severity:<sev>]` token to a string severity."""
    if not isinstance(token, str):
        return SEVERITY_WARNING
    m = re.match(r"\[validation-severity:([a-z-]+)\]", token)
    if not m:
        return SEVERITY_WARNING
    return m.group(1)


# ---- I/O helpers ----------------------------------------------------


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


def _gh_get_issue(issue_number: int, config: dict) -> dict | None:
    """Fetch issue title/body/labels/assignees via `gh issue view`."""
    return gh_get_issue(
        issue_number, config,
        fields="title,body,labels,assignees,projectItems",
    )


def _print_findings(issue_number: int, issue: dict, findings: list[Finding]) -> None:
    title = issue.get("title", "")
    print(f"validating issue #{issue_number}: {title}")
    print()
    if not findings:
        print("[ok] no findings.")
        return
    by_severity: dict[str, list[Finding]] = {}
    for f in findings:
        by_severity.setdefault(f.severity, []).append(f)
    for sev in (SEVERITY_HARD_REJECT, SEVERITY_BYPASSABLE, SEVERITY_WARNING):
        group = by_severity.get(sev, [])
        if not group:
            continue
        print(f"[{sev}]")
        for f in group:
            print(f"  - {f.label}: {f.detail}")
        print()
    n_blocking = len(by_severity.get(SEVERITY_HARD_REJECT, [])) + len(
        by_severity.get(SEVERITY_BYPASSABLE, [])
    )
    n_warn = len(by_severity.get(SEVERITY_WARNING, []))
    print(f"summary: {n_blocking} blocking, {n_warn} warning(s).")


if __name__ == "__main__":
    sys.exit(main())
