#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — edit-issue (verb-subject per DEC-020).

Methodology-aware body edit. Fetches the current issue body via
`gh issue view --json body`, applies the requested change (--body /
--body-file / --append / --title), validates the new state against
`body-format.yaml` + `titles.yaml` + `issue-types.yaml`, and writes
back via `gh issue edit --body-file`.

Validation is scoped to the field(s) being edited (#583): a title-only
edit validates the new title but not the untouched body (which may
predate the current body schema), and a body-only edit validates the new
body but not the untouched title. This lets a legacy issue take a clean
title edit without a full body rewrite.

`--milestone <number|title>` moves the issue to an OPEN milestone, resolved
exactly as `create-issue --milestone` resolves it; `--clear-milestone`
detaches it (#1049). The native Milestone field is written through the
substrate-write seam, and a first body line naming the old milestone as the
parent is rewritten to the new one (or removed, where the type's parent-ref
is optional), so the textual record and the native field keep agreeing. A
milestone edit never moves the issue in the lifecycle: where the issue's
state is read from its milestone alone (it carries no state label), a change
that would move it — scheduling a Todo issue, unscheduling a Backlog one — is
refused and the verb that owns that transition is named. A milestone change
takes `--reason` and posts an audit comment (from, to, why) before it writes,
and the issue's type must be one `issue-types.yaml` lets sit under a
milestone (#1016).

Refuses on hard-reject validation findings; warns on warning-level
findings. The `--force` flag is the operator override of a hard-reject
finding (the `--force` layer per DEC-046 — distinct from the reason-based
`--bypass` mechanism), recording an audit comment.

Membership gate per DEC-021 runs at startup.

Self-contained via PEP 723; runs via
  uv run --script .pkit/capabilities/project-management/scripts/edit-issue.py 42 --body-file new-body.md

Or via the dispatcher (per COR-021):
  pkit project-management edit-issue 42 --append "Additional context..."

Exit codes:
  0  edited (or dry-run reported, or nothing to change)
  1  membership refusal / validation refusal / a milestone edit that would
     move the issue in the lifecycle or orphan its parent-ref
  2  usage error (issue not found; no mode specified; milestone matches no
     open milestone)
  3  gh failure
"""  # noqa: E501 — a usage line is a command, kept whole

from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
import contextlib

from _lib import (
    axis_labels,
    body_parent_ref,
    bootstrap_gate,
    provenance,
    session_guard,
    title_rules,
)
from _lib import lifecycle_inference as infer
from _lib.audit import audit_key
from _lib.comment import post_audit_once
from _lib.gh import gh_get_issue, gh_run, load_adopter_config
from _lib.membership import (
    CAPABILITY_NAME,
    check_membership,
    resolve_capability_root,
    resolve_invoker_identity,
)
from _lib.milestone import Milestone, resolve_milestone
from _lib.structural_type import infer_structural_type
from _lib.substrate_writes import clear_milestone, write_milestone
from _lib import use_case_citations

SEVERITY_HARD_REJECT = "hard-reject"
SEVERITY_BYPASSABLE = "bypassable-with-audit"
SEVERITY_WARNING = "warning"

# The milestone-change audit comment (#1016): its kind marker (the shape
# handoff-issue's audit uses) and the writer name in its idempotency key.
MILESTONE_AUDIT_MARKER = "<!-- pkit-hook: edit-issue-milestone -->"
MILESTONE_AUDIT_WRITER = "edit-issue-milestone"


@dataclass(frozen=True)
class Finding:
    severity: str
    label: str
    detail: str


@dataclass(frozen=True)
class MilestoneEdit:
    """A requested milestone change: the issue's milestone now, and after.

    ``None`` on either side means no milestone — so a ``target`` of ``None``
    is a `--clear-milestone`.
    """

    current: Milestone | None
    target: Milestone | None

    @property
    def changed(self) -> bool:
        return _milestone_number(self.current) != _milestone_number(self.target)

    def describe(self) -> str:
        return f"{_milestone_label(self.current)} → {_milestone_label(self.target)}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Edit a GitHub issue's body or title. Validates the new state "
            "against the methodology's body + title rules before writing."
        ),
    )
    parser.add_argument(
        "issue_number",
        type=int,
        help="GitHub issue number.",
    )
    g = parser.add_mutually_exclusive_group()
    g.add_argument(
        "--body",
        default=None,
        help=("Replace the body with the supplied text. Pass `-` to read from stdin."),
    )
    g.add_argument(
        "--body-file",
        type=Path,
        default=None,
        help="Replace the body with the contents of this file.",
    )
    g.add_argument(
        "--append",
        default=None,
        help="Append the supplied text to the existing body (with a blank line separator).",
    )
    parser.add_argument(
        "--title",
        default=None,
        help="Replace the title (passed to `gh issue edit --title`).",
    )
    milestone_group = parser.add_mutually_exclusive_group()
    milestone_group.add_argument(
        "--milestone",
        default=None,
        metavar="M",
        help=(
            "Move the issue to this OPEN milestone — its number (e.g. `6`) or "
            "exact title, validated as `create-issue --milestone` validates it. "
            "A first body line naming the old milestone is rewritten to the "
            "new one. Refused when it would move the issue in the lifecycle "
            "(scheduling a Todo issue is `promote-issue --milestone`)."
        ),
    )
    milestone_group.add_argument(
        "--clear-milestone",
        action="store_true",
        help=(
            "Detach the issue from its milestone. Refused when the body's "
            "first line names that milestone as the issue's required parent, "
            "or when it would move the issue in the lifecycle."
        ),
    )
    parser.add_argument(
        "--reason",
        default=None,
        help=(
            "Why the milestone changes — required with --milestone / "
            "--clear-milestone and recorded in the audit comment the change "
            "posts (who scheduled what, and why, as promote-issue records it)."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Operator override of hard-reject validation findings, with an "
            "audit comment (the `--force` layer per DEC-046 — a hard-reject "
            "is force-overridable out of band, distinct from the "
            "`--bypass` mechanism). Default: refuse on hard-reject."
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
        help="Print the plan + findings; do not invoke gh.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the confirmation prompt.",
    )
    session_guard.add_override_argument(parser)
    args = parser.parse_args()

    milestone_requested = args.milestone is not None or args.clear_milestone
    if (
        args.body is None
        and args.body_file is None
        and args.append is None
        and args.title is None
        and not milestone_requested
    ):
        print(
            "error: nothing to edit. Pass --body, --body-file, --append, "
            "--title, --milestone or --clear-milestone.",
            file=sys.stderr,
        )
        return 2
    reason = (args.reason or "").strip()
    if milestone_requested and not reason:
        print(
            "error: a milestone change records why it was made: pass --reason "
            '"<why>" (the audit comment carries it).',
            file=sys.stderr,
        )
        return 2
    if reason and not milestone_requested:
        print(
            "error: --reason goes with --milestone / --clear-milestone; a title "
            "or body edit carries none.",
            file=sys.stderr,
        )
        return 2

    capability_root = resolve_capability_root(args.capability_root)
    if capability_root is None:
        print(
            f"error: {CAPABILITY_NAME} capability not found.",
            file=sys.stderr,
        )
        return 2

    # Prerequisite gate (#747): refuse on an un-bootstrapped project rather
    # than operating on assumed defaults. See _lib/bootstrap_gate.py.
    if not bootstrap_gate.enforce("edit-issue", capability_root=capability_root):
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
    titles = _read_yaml(capability_root / "schemas" / "titles.yaml", yaml_loader)
    body_format = _read_yaml(capability_root / "schemas" / "body-format.yaml", yaml_loader)
    classification = _read_yaml(capability_root / "schemas" / "classification.yaml", yaml_loader)

    issue = _gh_get_issue(args.issue_number, config)
    if issue is None:
        return 2

    current_title = str(issue.get("title", ""))
    # Work footer-free internally: strip any provenance region on read so
    # the edit, validation, and --append all operate on real body content;
    # the seam re-stamps exactly one footer on write (ADR-037).
    current_body = provenance.strip_footer(str(issue.get("body") or ""))

    # Compute the new title + body.
    new_title = args.title if args.title is not None else current_title
    new_body = _compute_new_body(current_body, args)
    if new_body is None:
        return 2  # error already printed

    # Scope validation to the field(s) actually being edited (#583). A
    # title-only edit validates the new title but not the untouched body (which
    # may predate the current body schema); a body-only edit validates the new
    # body but not the untouched title.
    title_changed = args.title is not None
    body_changed = args.body is not None or args.body_file is not None or args.append is not None

    # A milestone move (#1049): resolved and checked before anything is shown
    # as a plan, and the first line follows it. Rewriting that line is not a
    # body edit for validation's purposes — the form is preserved — so it does
    # not pull an untouched legacy body into validation.
    milestone_edit: MilestoneEdit | None = None
    first_line_moved = False
    if milestone_requested:
        planned = _plan_milestone(
            args,
            issue,
            config=config,
            substrate_map=axis_labels.load_substrate_map(capability_root),
            structural_type=infer_structural_type(
                new_title, issue_types, classification=classification
            ),
            issue_types=issue_types,
        )
        if isinstance(planned, int):
            return planned
        milestone_edit = planned
        followed = _follow_milestone_in_first_line(
            new_body,
            milestone_edit,
            issue_number=args.issue_number,
            parent_ref_optional=_parent_ref_optional(new_title, issue_types, classification),
        )
        if followed is None:
            return 1
        first_line_moved = followed != new_body
        new_body = followed

    writes_issue = title_changed or body_changed or first_line_moved
    writes_milestone = milestone_edit is not None and milestone_edit.changed

    print(f"edit-issue: #{args.issue_number}")
    print(f"  current title: {current_title}")
    if args.title is not None:
        print(f"  new title:     {new_title}")
    if writes_issue:
        print(f"  body change:   {len(current_body)} → {len(new_body)} chars")
    if milestone_edit is not None:
        print(f"  milestone:     {milestone_edit.describe()}")
    if first_line_moved:
        target_number = _milestone_number(milestone_edit.target) if milestone_edit else None
        print(
            "  first line:    "
            + (
                body_parent_ref.milestone_line(target_number)
                if target_number is not None
                else "(milestone parent-ref removed)"
            )
        )

    if not writes_issue and not writes_milestone:
        # Only a milestone flag can get here: every other flag writes the issue.
        print(
            f"\n[noop] #{args.issue_number}'s milestone is already "
            f"{_milestone_label(milestone_edit.target if milestone_edit else None)}; "
            "nothing to change."
        )
        return 0

    # Validate the new state, scoped to the edited axes.
    findings: list[Finding] = []
    if title_changed or body_changed:
        findings = _validate(
            title=new_title,
            body=new_body,
            issue_types=issue_types,
            titles=titles,
            body_format=body_format,
            classification=classification,
            check_title=title_changed,
            check_body=body_changed,
            # Read only for a body edit that cites a use case (DEC-054).
            use_cases=(
                use_case_citations.read_for(
                    new_body, capability_root.parent.parent.parent, config
                )
                if body_changed
                else None
            ),
        )
        _print_findings(findings)

    has_hard_reject = any(f.severity == SEVERITY_HARD_REJECT for f in findings)
    has_bypassable = any(f.severity == SEVERITY_BYPASSABLE for f in findings)

    if (has_hard_reject or has_bypassable) and not args.force:
        sev = "hard-reject" if has_hard_reject else "bypassable-with-audit"
        print(
            f"\n[refused] validation surfaced {sev} findings. "
            "Pass --force to write anyway (records an audit comment).",
            file=sys.stderr,
        )
        return 1

    if args.dry_run:
        print("\n[dry-run] gh would be invoked; nothing written.")
        return 0
    if not args.yes and sys.stdin.isatty():
        reply = input("Write the edit? [y/N] ").strip().lower()
        if reply not in ("y", "yes"):
            print("aborted.", file=sys.stderr)
            return 0

    # Audit comment on --force.
    if (has_hard_reject or has_bypassable) and args.force:
        audit_lines = [
            "[audit] edit applied despite validation findings (--force):",
        ]
        for f in findings:
            if f.severity in (SEVERITY_HARD_REJECT, SEVERITY_BYPASSABLE):
                audit_lines.append(f"  - [{f.severity}] {f.label}: {f.detail}")
        if not _gh_comment(args.issue_number, "\n".join(audit_lines), config):
            return 3

    # The audit comment first, so the record of who moved it and why survives
    # a failed write (#1016); then the native milestone, then the first line
    # that follows it (the order set-field keeps for a parent): a failure in
    # between leaves a state a re-run completes, since an already-set milestone
    # is not written again and the posted comment is not posted twice.
    if writes_milestone:
        if not _post_milestone_audit(args.issue_number, milestone_edit, reason, config):
            return 3
        if not _write_milestone(args.issue_number, milestone_edit, config):
            return 3

    if writes_issue:
        # Seam: write exactly one current footer (strip-then-append-one).
        stamped_body = provenance.stamp(new_body, provenance.read_versions(capability_root))
        if not _gh_apply_edit(
            args.issue_number,
            title=new_title,
            body=stamped_body,
            current_title=current_title,
            config=config,
        ):
            return 3

    print(f"\n[ok] edited #{args.issue_number}.")
    return 0


# ---- milestone move (#1049) -----------------------------------------


def _plan_milestone(
    args: argparse.Namespace,
    issue: dict,
    *,
    config: dict,
    substrate_map: axis_labels.SubstrateMap | None,
    structural_type: str | None,
    issue_types: dict,
) -> MilestoneEdit | int:
    """Resolve the requested milestone and check the move is an edit, not a
    lifecycle transition. Returns the edit, or the exit code to stop with.

    The target resolves exactly as `create-issue --milestone` resolves it: an
    OPEN milestone, by number or exact title (`_lib.milestone`). A closed or
    unknown milestone is a usage error. The issue's type must be one that may
    carry a milestone (#1016) — read from `issue-types.yaml`, not assumed.
    """
    current = _issue_milestone(issue)
    target: Milestone | None = None
    if args.milestone is not None:
        target = resolve_milestone(str(args.milestone), config)
        if target is None:
            print(
                f"error: --milestone {args.milestone!r} did not match any "
                "OPEN milestone (tried as number, then as title). "
                "List with `gh api repos/<owner>/<repo>/milestones?state=open`.",
                file=sys.stderr,
            )
            return 2
        if not _type_may_carry_milestone(structural_type, issue_types):
            kind = structural_type or "of an unrecognised type"
            print(
                f"\n[refused] #{args.issue_number} is {kind}, which "
                "issue-types.yaml does not let sit under a milestone.",
                file=sys.stderr,
            )
            return 1
    edit = MilestoneEdit(current=current, target=target)
    if not edit.changed:
        return edit

    # An issue carrying no state label has its position read from the
    # milestone (milestone → backlog, else todo — the detectors' precedence,
    # `lifecycle_inference`). Changing the milestone of such an issue would
    # move it without a transition, so it is refused.
    labels = _label_names(issue)
    state = str(issue.get("state", "")).lower()
    before = infer.infer_current_state(
        state=state,
        milestone=_milestone_payload(current),
        labels=labels,
        substrate_map=substrate_map,
    )
    after = infer.infer_current_state(
        state=state,
        milestone=_milestone_payload(target),
        labels=labels,
        substrate_map=substrate_map,
    )
    if before == after:
        return edit
    if (before, after) == ("todo", "backlog"):
        remedy = (
            "scheduling a Todo issue into a milestone is the Todo → Backlog "
            f"transition: `promote-issue {args.issue_number} --milestone "
            f'{args.milestone!r} --reason "<why>"`.'
        )
    else:
        remedy = (
            f"the workflow has no {before} → {after} transition; move it to "
            "another milestone with --milestone instead."
        )
    print(
        f"\n[refused] this milestone change would move #{args.issue_number} from "
        f"{before} to {after}: it carries no state label, so its state is read "
        "from its milestone, and edit-issue never changes an issue's state.\n"
        f"  → {remedy}",
        file=sys.stderr,
    )
    return 1


def _follow_milestone_in_first_line(
    body: str,
    edit: MilestoneEdit,
    *,
    issue_number: int,
    parent_ref_optional: bool,
) -> str | None:
    """The body with a milestone first line following the milestone edit.

    A first line naming a milestone other than the target is rewritten to the
    target; on a clear it is removed where the type's parent-ref is optional
    (an EPIC). Clearing the milestone an issue names as its required parent
    would leave that line naming a milestone the issue is no longer in, so it
    is refused (None) with the way out. A body whose first line names no
    milestone — an issue parent, or none — is returned unchanged.
    """
    named = body_parent_ref.first_line_milestone(body)
    target = _milestone_number(edit.target)
    if named is None or named == target:
        return body
    if target is not None or parent_ref_optional:
        return body_parent_ref.set_first_line_milestone(body, target)
    print(
        f"\n[refused] #{issue_number}'s first line names Milestone #{named} as "
        "its parent, which its type requires; clearing the milestone would "
        "leave that line naming a milestone the issue is no longer in.\n"
        f"  → re-parent it first (`set-field {issue_number} --parent <N>`), or "
        "move it with --milestone.",
        file=sys.stderr,
    )
    return None


def _parent_ref_optional(title: str, issue_types: dict, classification: dict) -> bool:
    """Whether the issue's type may go without a parent-ref (an EPIC). An
    unrecognised type is treated as requiring one — the cautious reading."""
    structural_type = infer_structural_type(title, issue_types, classification=classification)
    type_entry = (issue_types.get("types") or {}).get(structural_type)
    return isinstance(type_entry, dict) and bool(type_entry.get("parent_ref_optional"))


def _type_may_carry_milestone(structural_type: str | None, issue_types: dict) -> bool:
    """Whether issue-types.yaml lets this type sit under a milestone: its
    parents include `milestone`, or its parent-ref form has a milestone option
    (an EPIC's optional `Milestone:` line). An unrecognised type may not — the
    cautious reading, since nothing says it may."""
    entry = (issue_types.get("types") or {}).get(structural_type)
    if not isinstance(entry, dict):
        return False
    return "milestone" in (entry.get("parent_issue_types") or []) or (
        body_parent_ref.form_allows_milestone(str(entry.get("parent_ref_form") or ""))
    )


def _post_milestone_audit(
    issue_number: int, edit: MilestoneEdit, reason: str, config: dict
) -> bool:
    """Post the milestone-change audit comment unless it is already there.

    The record of who moved the issue and why (#1016): a milestone change is a
    scheduling decision, which the workflow gives to the user, so it carries its
    reason the way `promote-issue`'s milestone attach does. Posted through the
    shared `post_audit_once`: a retry of a failed attempt finds its own comment
    and does not post it again.
    """
    key = _milestone_audit_key(edit, reason)
    body = _milestone_audit_body(edit, reason, dt.date.today().isoformat(), key)
    return post_audit_once(
        "issue",
        issue_number,
        key,
        body,
        config,
        run=gh_run,
        present_note="milestone audit comment already present; idempotent skip",
    )


def _milestone_audit_key(edit: MilestoneEdit, reason: str) -> str:
    """The idempotency key for one milestone change: where from, where to, why.
    The date is in the prose, so the same change for the same reason on a later
    day posts its own comment; on the same day it reads as the retry it most
    likely is."""
    return audit_key(
        MILESTONE_AUDIT_WRITER,
        str(_milestone_number(edit.current) or ""),
        str(_milestone_number(edit.target) or ""),
        reason.strip(),
    )


def _milestone_audit_body(edit: MilestoneEdit, reason: str, today: str, key: str) -> str:
    """The milestone audit comment: kind marker, the change line, idempotency key."""
    return (
        f"{MILESTONE_AUDIT_MARKER}\n\n"
        f"Milestone: {edit.describe()} ({today}, reason: {reason.strip()})\n\n"
        f"{key}"
    )


def _write_milestone(issue_number: int, edit: MilestoneEdit, config: dict) -> bool:
    """Write the native milestone through the substrate-write seam (ADR-031)."""
    if edit.target is not None:
        result = write_milestone(config, issue_number=issue_number, title=edit.target.title)
    else:
        result = clear_milestone(config, issue_number=issue_number)
    if not result.ok:
        print(f"error: {result.detail}", file=sys.stderr)
        return False
    return True


def _issue_milestone(issue: dict) -> Milestone | None:
    """The milestone `gh issue view --json milestone` reports, or None."""
    raw = issue.get("milestone")
    if not isinstance(raw, dict) or not isinstance(raw.get("number"), int):
        return None
    return Milestone(number=raw["number"], title=str(raw.get("title", "")))


def _milestone_number(milestone: Milestone | None) -> int | None:
    return milestone.number if milestone is not None else None


def _milestone_label(milestone: Milestone | None) -> str:
    if milestone is None:
        return "(none)"
    return f"#{milestone.number} {milestone.title}".rstrip()


def _milestone_payload(milestone: Milestone | None) -> dict | None:
    """The milestone in the shape the position reader takes."""
    if milestone is None:
        return None
    return {"number": milestone.number, "title": milestone.title}


def _label_names(issue: dict) -> list[str]:
    return [
        lbl.get("name", "") if isinstance(lbl, dict) else str(lbl)
        for lbl in (issue.get("labels") or [])
    ]


# ---- body computation -----------------------------------------------


def _compute_new_body(current_body: str, args: argparse.Namespace) -> str | None:
    """Resolve the new-body content from the mutually-exclusive flags."""
    if args.body is not None:
        if args.body == "-":
            try:
                return sys.stdin.read()
            except OSError as exc:
                print(f"error: failed to read stdin: {exc}", file=sys.stderr)
                return None
        return args.body
    if args.body_file is not None:
        try:
            return args.body_file.read_text(encoding="utf-8")
        except OSError as exc:
            print(
                f"error: failed to read {args.body_file}: {exc}",
                file=sys.stderr,
            )
            return None
    if args.append is not None:
        sep = "\n\n" if current_body and not current_body.endswith("\n\n") else ""
        return current_body + sep + args.append
    return current_body


# ---- validation -----------------------------------------------------


def _validate(
    *,
    title: str,
    body: str,
    issue_types: dict,
    titles: dict,
    body_format: dict,
    classification: dict | None = None,
    check_title: bool = True,
    check_body: bool = True,
    use_cases: use_case_citations.UseCases | use_case_citations.Unreadable | None = None,
) -> list[Finding]:
    """Apply the body + title validators used by validate-issue.py.

    ``check_title`` / ``check_body`` scope the findings to the field(s) being
    changed (#583). Both default True (full validation, unchanged for callers
    that revalidate the whole issue); edit-issue passes only the axes it is
    actually editing so a title-only edit does not re-reject an untouched
    (possibly legacy-schema) body, and a body-only edit does not re-reject an
    untouched title. Findings are labelled ``title.*`` / ``body.*``; the scope
    is applied by dropping findings for the unchanged axis.
    """
    findings: list[Finding] = []

    structural_type = infer_structural_type(title, issue_types, classification=classification or {})
    if structural_type is None:
        findings.append(
            Finding(
                SEVERITY_HARD_REJECT,
                "title.format",
                f"title {title!r} does not match any known [Type] prefix.",
            )
        )
    else:
        # The type's titles.yaml checks — the pattern and every declared wording
        # rule (#803) — at their declared severity: an edit writes the title.
        for severity, label, detail in title_rules.check_title(
            titles, title_rules.issue_key(structural_type), title
        ):
            findings.append(Finding(severity, label, detail))

    # Per-type required body sections.
    if structural_type is not None:
        bodies = body_format.get("bodies") or {}
        type_body = bodies.get(structural_type) or {}
        for section in type_body.get("required_sections") or []:
            if not isinstance(section, dict):
                continue
            heading = str(section.get("heading", ""))
            if heading and heading not in body:
                severity = _severity_from_token(section.get("severity"))
                findings.append(
                    Finding(
                        severity,
                        "body.required-section",
                        f"missing required section {heading!r}.",
                    )
                )

        # DEC-013 marker form (#763 AC3), parity with validate-issue. A first line
        # that attempts an integration marker but is malformed hard-rejects here
        # with a precise message, instead of the misleading `body.parent-ref` a
        # malformed marker would otherwise trigger by falling through.
        malformed_marker = infer.malformed_integration_marker(body)
        if malformed_marker is not None:
            marker_pattern = str((body_format.get("integration_marker") or {}).get("pattern") or "")
            findings.append(
                Finding(
                    SEVERITY_HARD_REJECT,
                    "body.integration-marker",
                    f"first body line looks like a DEC-013 integration marker but "
                    f"does not match the required form "
                    f"`Integration: integration/<slug>` (pattern {marker_pattern!r}); "
                    f"got {malformed_marker!r}.",
                )
            )

        # Parent-ref first line. Accepts three forms (parity with
        # validate-issue per #210):
        #   1. New canonical milestone link: `Milestone: [#<N>](../milestone/<N>)`
        #   2. Old plain milestone form: `Milestone: #<N>` (accepted with
        #      a deprecation warning during the grace period).
        #   3. Issue-parent form: `<Label>: #<N>` (EPIC, Feature, Umbrella,
        #      Task — anything that resolves through issue-types.yaml's
        #      `parent_ref_form`).
        type_entry = (issue_types.get("types") or {}).get(structural_type)
        if isinstance(type_entry, dict):
            parent_ref_optional = bool(type_entry.get("parent_ref_optional", False))
            parent_ref_form = str(type_entry.get("parent_ref_form", ""))
            if parent_ref_form and not parent_ref_optional and malformed_marker is None:
                # The first line as every reader of an issue's parent takes it
                # (`body_parent_ref.first_line`): past the DEC-013 (#763)
                # `Integration: integration/<slug>` marker a marked descendant
                # carries above the parent-ref. The form check below is this
                # script's own.
                first_line = body_parent_ref.first_line(body)
                _NEW_MILESTONE_RE = re.compile(r"^Milestone:\s+\[#(\d+)\]\(\.\./milestone/\1\)\s*$")
                _OLD_MILESTONE_RE = re.compile(r"^Milestone:\s+#\d+\s*$")
                _ISSUE_PARENT_RE = re.compile(r"^[A-Za-z]+:\s+#\d+\s*$")

                if _NEW_MILESTONE_RE.match(first_line):
                    # New form — clean pass.
                    pass
                elif _OLD_MILESTONE_RE.match(first_line):
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
                    findings.append(
                        Finding(
                            SEVERITY_HARD_REJECT,
                            "body.parent-ref",
                            f"first body line does not match the parent-ref "
                            f"form {parent_ref_form!r}; got {first_line!r}.",
                        )
                    )

    # Universal body rules.
    if re.search(r"^# [^#]", body, flags=re.MULTILINE):
        findings.append(
            Finding(
                SEVERITY_HARD_REJECT,
                "body.h1",
                "body contains an h1 (`# ...`) heading; use `## Title`.",
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
    # Use-case citations (DEC-054), parity with validate-issue: inert where
    # `use_cases` is None (software-analysis not installed, nothing cited).
    for sev, label, detail in use_case_citations.check(body, use_cases):
        findings.append(Finding(sev, label, detail))

    # Scope to the fields being changed (#583). Findings are labelled
    # `title.*` / `body.*`; drop the ones for an axis the caller is not editing
    # so an untouched (possibly legacy-schema) title/body is not re-rejected.
    if not check_title:
        findings = [f for f in findings if not f.label.startswith("title.")]
    if not check_body:
        findings = [f for f in findings if not f.label.startswith("body.")]
    return findings


def _severity_from_token(token) -> str:
    if not isinstance(token, str):
        return SEVERITY_WARNING
    m = re.match(r"\[validation-severity:([a-z-]+)\]", token)
    if not m:
        return SEVERITY_WARNING
    return m.group(1)


def _print_findings(findings: list[Finding]) -> None:
    if not findings:
        print("\nvalidation: clean (no findings).")
        return
    print("\nvalidation findings:")
    for f in findings:
        print(f"  [{f.severity}] {f.label}: {f.detail}")


# ---- gh wrappers ----------------------------------------------------


def _gh_get_issue(issue_number: int, config: dict) -> dict | None:
    return gh_get_issue(issue_number, config, fields="title,body,state,labels,milestone")


def _gh_apply_edit(
    issue_number: int,
    *,
    title: str,
    body: str,
    current_title: str,
    config: dict,
) -> bool:
    """Apply the edit via `gh issue edit --body-file`."""
    cmd = ["gh", "issue", "edit", str(issue_number)]
    if title != current_title:
        cmd.extend(["--title", title])
    # Always write body via a temp file — avoids shell length limits.
    with tempfile.NamedTemporaryFile("w", suffix=".md", encoding="utf-8", delete=False) as f:
        f.write(body)
        body_path = f.name
    try:
        cmd.extend(["--body-file", body_path])
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        except FileNotFoundError:
            return False
        if proc.returncode != 0:
            print(
                f"error: gh issue edit failed (exit {proc.returncode}).\n"
                f"stderr: {proc.stderr.strip()}",
                file=sys.stderr,
            )
            return False
    finally:
        with contextlib.suppress(OSError):
            Path(body_path).unlink(missing_ok=True)
    return True


def _gh_comment(issue_number: int, body: str, config: dict) -> bool:
    try:
        proc = gh_run(
            ["gh", "issue", "comment", str(issue_number), "--body", body],
            config,
            check=False,
        )
    except FileNotFoundError:
        return False
    return proc.returncode == 0


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
