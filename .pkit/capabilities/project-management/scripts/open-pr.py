#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
# ]
# ///
"""Project-management capability — open-pr (verb-subject per DEC-020).

Opens a PR per the methodology's branch + PR conventions
(git-conventions.yaml + titles.yaml + classification.yaml).

Inputs:
  * Current branch must match `git-conventions.yaml`'s branch-name
    pattern (refused if not).
  * Closing issue number(s) — the positional `<N>`, as review-work and
    done-work take it (#1017), and/or `--closes`, its explicit form, which
    repeats: one PR that lands several Tasks closes each of them on merge
    (#1049). Without either, the branch name's `<N>` segment. The first
    is the primary issue — it supplies the title's `<type>`, the default
    summary and the base branch.
  * PR title — composed as `<type>(<scope>): <summary>`, never taken
    whole. `<type>` is derived from the primary closing issue's `type:*`
    label via classification.yaml's pr_type_mapping, overridden by
    `--type`; `(<scope>)` comes from `--scope` and is omitted without it;
    `<summary>` — the description part — is `--summary`, defaulting to
    the issue title without its `[Type]` prefix, lowercased.
  * PR body — `templates/PR.md` skeleton with a `Closes #N` line per
    closing issue; user-supplied `--body-file` overrides, and gains a
    `Closes #N` line for any closing issue it does not already name.
  * `## Friction answers` (DEC-055) — the change check's list of the
    answers the change wrote, and the friction settings it alters, derived
    at the pushed head (the commit the branch's remote-tracking reference
    names, not local HEAD) against the PR's base, named to the check, and
    placed last before the provenance footer. A section the supplied body
    carries — written by a command or typed by hand — is dropped, with a
    warning. open-pr never refuses to open over it: a list it cannot
    derive, a branch not pushed, a word that reads as a closing reference
    or holds an HTML comment's delimiter, or a body it would make too long
    leaves the section out with one warning line, and land-work writes it
    or says why it cannot.
  * `--doc-impact-from-friction` (opt-in) — fill an unwritten `## Doc
    impact` (the template's placeholder, empty, or absent) with one line
    counting the answers listed under `## Friction answers`. It names no
    path and no reason, so it meets no mapping obligation; an authored
    section is never touched. Rendering only (DEC-053 point 2): the
    section meets no documentation obligation; the pages do.

Membership gate per DEC-021 runs at startup.

Self-contained via PEP 723; runs via
  uv run --script .pkit/capabilities/project-management/scripts/open-pr.py --scope cli --summary "add new dispatcher"

Or via the dispatcher (per COR-021):
  pkit project-management open-pr 42 --scope cli --summary "add new dispatcher"

Exit codes:
  0  PR opened (or dry-run reported)
  1  membership refusal / validation refusal
  2  usage error (not on a feature branch; closing issue not found)
  3  gh failure
"""  # noqa: E501 — a usage line is a command, kept whole

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
import contextlib

from _lib import (
    axis_labels,
    bootstrap_gate,
    classification_rules,
    default_branch,
    doc_impact,
    friction_answers,
    pr_validation,
    provenance,
    session_guard,
)
from _lib import lifecycle_inference as infer
from _lib.gh import gh_get_issue, gh_run, load_adopter_config
from _lib.hooks import fire_hooks
from _lib.membership import (
    CAPABILITY_NAME,
    check_membership,
    resolve_capability_root,
    resolve_invoker_identity,
)
from _lib.placeholder_detection import PHASE_TRANSITION


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Open a GitHub PR per the methodology's branch + PR + title "
            "conventions. The closing issue is the positional <N> (as "
            "review-work and done-work take it), or --closes, or else the "
            "current branch's <N>. The PR title is composed, not taken whole: "
            "`<type>(<scope>): <summary>`, where <type> is --type or the "
            "primary closing issue's type:* label mapped through "
            "classification.yaml, `(<scope>)` is --scope and is left out "
            "without it, and <summary> — the title's description part — is "
            "--summary or the issue title without its [Type] prefix, "
            "lowercased."
        ),
    )
    parser.add_argument(
        "issue_number",
        nargs="?",
        type=int,
        default=None,
        metavar="N",
        help=(
            "The closing issue, as review-work and done-work take it: the same "
            "as `--closes N`, and the primary issue when --closes names more."
        ),
    )
    parser.add_argument(
        "--closes",
        type=int,
        action="append",
        default=None,
        metavar="N",
        help=(
            "Closing issue number — the explicit form of the positional <N>; "
            "repeat it to close several issues with one PR — the body carries "
            "a `Closes #N` line for each. The first closing issue is the "
            "primary one (title <type>, default summary, base branch). "
            "Default: derived from the current branch's "
            "`<conv-type>/<N>-<slug>` form."
        ),
    )
    parser.add_argument(
        "--type",
        default=None,
        help=(
            "The title's Conventional Commits <type> (overrides the value "
            "derived from the primary closing issue's type:* label)."
        ),
    )
    parser.add_argument(
        "--scope",
        default=None,
        help="The title's Conventional Commits <scope>; omitted from the title when not given.",
    )
    parser.add_argument(
        "--summary",
        default=None,
        help=(
            "The title's description part — the <summary> after "
            "`<type>(<scope>): ` — short, imperative, lowercase, no trailing "
            "period. The type and scope are not part of it. Default: the "
            "primary issue's title without its [Type] prefix, lowercased."
        ),
    )
    parser.add_argument(
        "--body-file",
        type=Path,
        default=None,
        help=(
            "Path to a file containing the PR body. Default: use the "
            "capability's templates/PR.md skeleton with `Closes #N` filled in."
        ),
    )
    parser.add_argument(
        "--doc-impact-from-friction",
        action="store_true",
        help=(
            "Fill an unwritten `## Doc impact` section (the template's placeholder, "
            "empty, or absent) with one line counting the friction answers listed "
            "under `## Friction answers`; it names no path and no reason. An authored "
            "section is left as it is. Rendering only: the section meets no "
            "documentation obligation (DEC-053)."
        ),
    )
    parser.add_argument(
        "--base",
        default=None,
        help=(
            "Base branch (default: the closing issue's DEC-013 integration "
            "branch when its body carries an `Integration:` marker, else the "
            "project's default branch — the backbone's `repository.default-branch`, "
            "COR-054)."
        ),
    )
    parser.add_argument(
        "--draft",
        action="store_true",
        help="Open the PR as a draft (passed through as gh pr create --draft).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Open a non-draft PR despite hard-reject body-validation findings "
            "(empty required section / checkbox / missing Doc impact), recording "
            "an audit note on the PR. Drafts skip validation, so --force is a "
            "no-op with --draft."
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
        help="Print the plan; do not invoke gh.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the confirmation prompt.",
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
    if not bootstrap_gate.enforce("open-pr", capability_root=capability_root):
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

    git_conventions = _read_yaml(capability_root / "schemas" / "git-conventions.yaml", yaml_loader)
    classification = _read_yaml(capability_root / "schemas" / "classification.yaml", yaml_loader)

    branch = _current_branch()
    if branch is None:
        return 2

    # Validate the branch name.
    branch_pattern = _branch_pattern(git_conventions)
    if branch_pattern and not re.match(branch_pattern, branch):
        print(
            f"[refused] current branch {branch!r} does not match "
            f"git-conventions.yaml's branch-name pattern "
            f"({branch_pattern!r}).\n"
            "  → rename the branch via `git branch -m <new-name>` and retry.",
            file=sys.stderr,
        )
        return 1

    # Derive the closing issue number(s); the first is the primary issue.
    closing_issues = _closing_issues(args.issue_number, args.closes, branch)
    if not closing_issues:
        print(
            f"error: could not derive closing issue from branch {branch!r}; "
            "pass it: `open-pr <N>` (or --closes <N>).",
            file=sys.stderr,
        )
        return 2
    issue_number = closing_issues[0]

    # Fetch the primary closing issue to derive title / type label.
    issue = _gh_get_issue(issue_number, config)
    if issue is None:
        return 2
    # Every other closing issue must exist too — a typo would otherwise ride
    # into the body as a `Closes #N` that closes the wrong issue on merge.
    for other in closing_issues[1:]:
        if _gh_get_issue(other, config) is None:
            return 2

    issue_title = str(issue.get("title", ""))
    issue_labels = [
        lbl.get("name", "") if isinstance(lbl, dict) else str(lbl)
        for lbl in (issue.get("labels") or [])
    ]

    # Determine the PR's Conventional Commits <type>.
    substrate_map = axis_labels.load_substrate_map(capability_root)
    conv_type = args.type or _conv_type_from_issue_labels(
        issue_labels, classification, substrate_map
    )
    if conv_type is None:
        print(
            f"error: could not determine Conventional Commits <type> for "
            f"PR. Issue #{issue_number} has no `type:*` label; pass --type.",
            file=sys.stderr,
        )
        return 2

    # Derive the PR title.
    summary = args.summary or _summary_from_issue_title(issue_title)
    pr_title = f"{conv_type}({args.scope}): {summary}" if args.scope else f"{conv_type}: {summary}"

    # Base branch (DEC-013, #903): --base, else the closing issue's integration
    # marker, else default_branch — the resolution start-work cut the branch by.
    try:
        base = infer.resolve_base_branch(config, str(issue.get("body") or ""), explicit=args.base)
    except default_branch.Unanswered as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    # Build the PR body.
    body = _build_pr_body(
        capability_root=capability_root,
        issue_numbers=closing_issues,
        body_file=args.body_file,
    )
    if body is None:
        return 2
    # The change check's list of the answers the change wrote (DEC-055), last
    # before the footer, and never one a supplied body carries — a section a
    # command wrote or one typed by hand; open-pr never refuses over it.
    if friction_answers.hand_written(body) or friction_answers.has_list(body):
        print(
            f"warn: the body's `{friction_answers.HEADING}` section is dropped — only open-pr "
            "and land-work write it, from the change check",
            file=sys.stderr,
        )
    body = friction_answers.strip(body)
    versions = provenance.read_versions(capability_root)
    answers = _fitting(body, _friction_answers(branch, base), versions)
    doc_impact_note = None
    if args.doc_impact_from_friction:
        body, doc_impact_note = _prefill_doc_impact(body, answers)
    if answers.section is not None:
        body = friction_answers.stamp(body, answers.section)
    # Seam: stamp exactly one provenance footer onto the PR body (ADR-037).
    body = provenance.stamp(body, versions)

    # Validate-at-ready (#569): a non-draft PR goes straight to ready-for-review,
    # so its body must pass the checks the merge gate enforces (DEC-031 empty
    # checkbox → hard-reject at the transition phase; DEC-015 Doc impact). Drafts
    # are exempt — a skeleton-of-TODOs is legitimate WIP. --force overrides with an
    # audit note. Title/closing-label checks are skipped (the title is composed here).
    forced_findings: list[pr_validation.Finding] = []
    if not args.draft:
        findings = pr_validation.validate_pr(
            pr_title=pr_title,
            pr_body=body,
            titles={},
            classification=classification,
            git_conv=git_conventions,
            closing_type_labels=[],
            capability_root=capability_root,
            phase=PHASE_TRANSITION,
        )
        blocking = [f for f in findings if f.severity in pr_validation.BLOCKING_SEVERITIES]
        if blocking:
            print(
                "[refused] PR body is not ready for review (validate-at-ready, #569):",
                file=sys.stderr,
            )
            for f in blocking:
                print(f"  - [{f.severity}] {f.label}: {f.detail}", file=sys.stderr)
            if not args.force:
                print(
                    "  → fill the body (--body-file), or open a draft (--draft) and "
                    "fill it before marking ready; --force overrides with an audit note.",
                    file=sys.stderr,
                )
                return 1
            forced_findings = blocking
            print(
                "  → proceeding under --force; an audit note will be posted on the PR.",
                file=sys.stderr,
            )

    print("open-pr: plan")
    print(f"  branch:  {branch}")
    print(f"  base:    {base}")
    print(f"  closes:  {', '.join(f'#{n}' for n in closing_issues)}")
    print(f"  type:    {conv_type}")
    if args.scope:
        print(f"  scope:   {args.scope}")
    print(f"  title:   {pr_title}")
    print(f"  body:    {len(body)} chars")
    print(f"  answers: {answers.note}")
    if doc_impact_note is not None:
        print(f"  doc impact: {doc_impact_note}")
    if args.draft:
        print("  draft:   yes")

    if args.dry_run:
        print("\n[dry-run] gh would be invoked; nothing written.")
        return 0
    if not args.yes and sys.stdin.isatty():
        reply = input("Open the PR? [y/N] ").strip().lower()
        if reply not in ("y", "yes"):
            print("aborted.", file=sys.stderr)
            return 0

    url = _gh_pr_create(
        title=pr_title,
        body=body,
        base=base,
        draft=args.draft,
        config=config,
    )
    if url is None:
        return 3
    print(f"\n[ok] opened: {url}")

    # Fire after_open_pr hooks per DEC-024.
    import re as _re

    pr_number_match = _re.search(r"/pull/(\d+)", url)
    pr_number = int(pr_number_match.group(1)) if pr_number_match else None
    if pr_number is not None:
        # One-time immutable filing-version comment on the PR (DEC-041).
        print(provenance.post_filing_comment(pr_number, capability_root, config, is_pr=True))
        if forced_findings:
            _post_force_audit(pr_number, forced_findings, config)
    fire_hooks(
        "after_open_pr",
        context={"pr": {"number": pr_number, "title": pr_title}},
        config=config,
        capability_root=capability_root,
    )

    return 0


# ---- conventions helpers -------------------------------------------


def _branch_pattern(git_conventions: dict) -> str | None:
    conv = (git_conventions.get("conventions") or {}).get("branch-name")
    if isinstance(conv, dict):
        p = conv.get("pattern")
        if isinstance(p, str):
            return p
    return None


def _extract_issue_number(branch: str) -> int | None:
    m = re.match(r"^[a-z]+/(\d+)-", branch)
    if not m:
        return None
    return int(m.group(1))


def _closing_issues(positional: int | None, closes: list[int] | None, branch: str) -> list[int]:
    """The issues the PR closes, primary first, without repeats.

    The positional `<N>` (as review-work and done-work take it) and
    `--closes` (repeatable, the explicit form) name them — the positional one
    first; without either, the branch's `<N>` segment is the one closing
    issue. Empty when none yields one.
    """
    named = ([positional] if positional is not None else []) + list(closes or [])
    if named:
        return list(dict.fromkeys(named))
    derived = _extract_issue_number(branch)
    return [derived] if derived is not None else []


def _conv_type_from_issue_labels(
    labels: list[str],
    classification: dict,
    substrate_map: axis_labels.SubstrateMap | None,
) -> str | None:
    """Map the issue's type label to the PR's Conventional Commits <type>.

    Reads the kit type value off the issue's labels THROUGH the substrate map
    (the ADR-026 seam): the kit's `type:*` label in greenfield, the adopter's
    remapped label where the map binds `type` to a label remap (#910). Then maps
    it via classification.yaml's `pr_type_mapping` through the shared
    `classification_rules` reader — the one place that table is parsed, shared
    with start-work / review-work's branch-prefix derivation (COR-007)."""
    issue_label_value = axis_labels.resolve_read("type", labels, substrate_map)
    if issue_label_value is None:
        return None
    return classification_rules.conv_type_for_kind(issue_label_value, classification)


def _summary_from_issue_title(title: str) -> str:
    """Drop the [Type] prefix and lowercase the remainder.

    Strips trailing period if any. Result still needs the user's
    judgment (~50 chars, imperative); we make a best-effort default.
    """
    m = re.match(r"^\[[A-Za-z]+\]\s+(.*?)\.?\s*$", title)
    rest = m.group(1) if m else title
    return rest.lower()


def _build_pr_body(
    *,
    capability_root: Path,
    issue_numbers: list[int],
    body_file: Path | None,
) -> str | None:
    """The PR body, carrying a `Closes #N` line for every closing issue."""
    if body_file is not None:
        try:
            authored = body_file.read_text(encoding="utf-8")
        except OSError as exc:
            print(
                f"error: failed to read {body_file}: {exc}",
                file=sys.stderr,
            )
            return None
        return pr_validation.with_closing_references(authored, issue_numbers)
    template_path = capability_root / "templates" / "PR.md"
    if not template_path.is_file():
        return pr_validation.with_closing_references("", issue_numbers)
    raw = template_path.read_text(encoding="utf-8")
    # Drop the HTML comment scaffolding lines so the PR body stays clean.
    stripped = _strip_html_comments(raw)
    # Replace the `Closes #` placeholder with one line per closing issue; a
    # template without the placeholder gets them prepended instead.
    closing_lines = "\n".join(f"Closes #{n}" for n in issue_numbers)
    # `[ \t]*`, not `\s*`: the latter also swallowed the newline after the
    # placeholder, gluing the next heading onto the last `Closes` line.
    out = re.sub(
        r"^Closes #[ \t]*$", lambda _m: closing_lines, stripped, count=1, flags=re.MULTILINE
    )
    return pr_validation.with_closing_references(out, issue_numbers)


def _strip_html_comments(text: str) -> str:
    """Remove <!-- ... --> blocks (including multi-line ones)."""
    return re.sub(r"<!--.*?-->\s*", "", text, flags=re.DOTALL)


@dataclass(frozen=True)
class _Answers:
    """The friction answers' section open-pr writes, and what the plan says of it."""

    #: The section, or None when there is none to write.
    section: str | None
    #: The plan's `answers:` line.
    note: str
    #: The change check's document, when it was read.
    document: Mapping[str, Any] | None = None
    #: How many answers the change wrote, when the document was read.
    count: int = 0


def _friction_answers(branch: str, base: str) -> _Answers:
    """The change check's list of the answers the change wrote, and the friction
    settings it alters, derived at the pushed head against the PR's base — named
    always, so `$PKIT_CHECK_BASE` never changes it. Never refuses: a list that
    cannot be written is left out with one warning line, and land-work writes it
    or says why it cannot (DEC-055)."""
    head, why = _pushed_head(branch)
    if head is None:
        return _left_out(why)
    derived = friction_answers.derive(head, base)
    if derived.document is None:
        return _left_out(derived.problem or "the change check gave no document")
    count = len(derived.answers)
    if not derived.listed:
        return _Answers(None, "none written by this change", derived.document)
    settings = derived.settings
    for found, why in (
        (
            friction_answers.closing_reference(derived.document, settings),
            "read as a closing reference ({words}), which would close an issue at merge",
        ),
        (
            friction_answers.comment_delimiter(derived.document, settings),
            "hold an HTML comment's delimiter ({words}), which could hide the list",
        ),
    ):
        if found is not None:
            location, words = found
            left = _left_out(
                f"the words on {location} {why.format(words=words)} — reword them there"
            )
            return _Answers(None, left.note, derived.document, count)
    section = friction_answers.render(derived.document, head, settings)
    listed = (
        f"{count} written by this change"
        if count
        else "none written by this change, which alters the project's friction settings"
    )
    if count and settings:
        listed += ", which also alters the project's friction settings"
    return _Answers(
        section,
        f"{listed}, listed under `{friction_answers.HEADING}` (at {head[:7]})",
        derived.document,
        count,
    )


def _left_out(why: str) -> _Answers:
    print(
        f"warn: friction answers not listed — {why}; `land-work` writes the list or says "
        "why it cannot",
        file=sys.stderr,
    )
    return _Answers(None, "not listed (the warning above says why)")


def _fitting(body: str, answers: _Answers, versions: provenance.Versions) -> _Answers:
    """`answers`, its section left out with one warning line when the body with
    it would not fit the host's limit."""
    if answers.section is None:
        return answers
    whole = provenance.stamp(friction_answers.stamp(body, answers.section), versions)
    if friction_answers.fits(whole):
        return answers
    left = _left_out(
        f"the body with the list is {len(whole)} characters, past the host's "
        f"{friction_answers.BODY_LIMIT} — split the change or narrow the anchor"
    )
    return _Answers(None, left.note, answers.document, answers.count)


def _pushed_head(branch: str) -> tuple[str | None, str]:
    """The commit `branch`'s remote-tracking reference names — what the pull
    request opens at, not local HEAD, which may be ahead of it — or why none."""
    remote = "origin"
    for atom in ("push:remotename", "upstream:remotename"):
        named = _git_out("for-each-ref", f"--format=%({atom})", f"refs/heads/{branch}")
        if named and named != ".":
            remote = named
            break
    oid = _git_out("rev-parse", "--verify", "--quiet", f"refs/remotes/{remote}/{branch}^{{commit}}")
    if not oid:
        return None, f"{remote}/{branch} names no commit — push the branch first"
    return oid, ""


def _git_out(*argv: str) -> str:
    try:
        proc = subprocess.run(["git", *argv], capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return ""
    return proc.stdout.strip() if proc.returncode == 0 else ""


def _prefill_doc_impact(body: str, answers: _Answers) -> tuple[str, str]:
    """`body` with its unwritten `## Doc impact` section holding one line that
    counts the answers listed under `## Friction answers`, and one line saying
    what happened. The line names no path and no reason, so it meets no mapping
    obligation. Never refuses: no list leaves the body as it was."""
    if answers.document is None:
        return body, "not pre-filled — `pkit friction check --json` gave no document"
    still = doc_impact.unanswered(answers.document)
    if still:
        print(
            f"warn: {len(still)} artefact(s) still carry friction with no answer on the "
            f"page: {', '.join(still)} — answer each there (`pkit friction check`).",
            file=sys.stderr,
        )
    if not answers.count:
        return body, "not pre-filled — the change check reports no answers"
    if answers.section is None:
        return body, "not pre-filled — the answers are not listed"
    noun = "friction answer" if answers.count == 1 else "friction answers"
    line = (
        f"{answers.count} {noun} on anchored artefacts — listed under `{friction_answers.HEADING}`."
    )
    body, filled = doc_impact.prefill(body, [line])
    if not filled:
        return body, "not pre-filled — the section is already written"
    return body, f"pre-filled: {line}"


# ---- gh + git wrappers ---------------------------------------------


def _current_branch() -> str | None:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        print("error: `git` not on PATH.", file=sys.stderr)
        return None
    if proc.returncode != 0:
        print(
            f"error: could not determine current branch.\nstderr: {proc.stderr.strip()}",
            file=sys.stderr,
        )
        return None
    return proc.stdout.strip() or None


def _gh_get_issue(issue_number: int, config: dict) -> dict | None:
    return gh_get_issue(issue_number, config, fields="title,labels,state,body")


def _post_force_audit(pr_number: int, findings: list, config: dict) -> None:
    """Best-effort audit note when a non-draft PR is opened under --force despite
    ready-validation findings (#569) — mirrors edit-issue's --force audit trail."""
    lines = ["[audit] non-draft PR opened despite validate-at-ready findings (--force):"]
    for f in findings:
        lines.append(f"  - [{f.severity}] {f.label}: {f.detail}")
    with contextlib.suppress(FileNotFoundError):
        gh_run(
            ["gh", "pr", "comment", str(pr_number), "--body", "\n".join(lines)],
            config,
            check=False,
        )


def _gh_pr_create(*, title: str, body: str, base: str, draft: bool, config: dict) -> str | None:
    with tempfile.NamedTemporaryFile("w", suffix=".md", encoding="utf-8", delete=False) as f:
        f.write(body)
        body_path = f.name
    cmd = [
        "gh",
        "pr",
        "create",
        "--title",
        title,
        "--body-file",
        body_path,
        "--base",
        base,
    ]
    if draft:
        cmd.append("--draft")
    try:
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        except FileNotFoundError:
            return None
        if proc.returncode != 0:
            print(
                f"error: gh pr create failed (exit {proc.returncode}).\n"
                f"stderr: {proc.stderr.strip()}",
                file=sys.stderr,
            )
            return None
        return proc.stdout.strip() or None
    finally:
        with contextlib.suppress(OSError):
            Path(body_path).unlink(missing_ok=True)


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
