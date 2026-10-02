#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
#   "pathspec>=0.12",
# ]
# ///
"""Project-management capability — show-pr (verb-subject per DEC-020).

Read-only diagnostic for a GitHub PR. Surfaces the methodology-relevant
view: title, Conventional Commits parse, state, base/head branches,
closing issues, reviewers, doc-impact section presence, and the latest
DEC-028 reviewer verdict(s) — `--field review` renders each reviewer's
verdict token AND the reasons, read via the same governed `gh` path the
rest of the view uses (issue #544; the operator's only allowed path to the
verdict body, since raw `gh pr view --comments` is denied).
`--field review-history` renders EVERY verdict each reviewer posted, in
posting order — earlier rounds a later verdict superseded included (#905).
A verdict the merge gate would not count is marked stale, with the reason,
by the gate's own freshness rule (`_lib.verdict_freshness`, #1179); to
judge it the view resolves the PR's required reviewers as the gate does.

Membership gate per DEC-021 runs at startup.

Self-contained via PEP 723; runs via
  uv run --script .pkit/capabilities/project-management/scripts/show-pr.py 99

Or via the dispatcher (per COR-021):
  pkit project-management show-pr 99

Exit codes:
  0  shown
  1  membership refusal
  2  usage error (PR not found)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib import bootstrap_gate
from _lib.agent_verdicts import (
    all_verdicts,
    latest_verdicts_per_reviewer,
    reduce_latest_per_reviewer,
)
from _lib.author_delta import author_delta, base_kept
from _lib.gh import gh_get_issue, gh_run, load_adopter_config
from _lib.membership import (
    CAPABILITY_NAME,
    check_membership,
    resolve_capability_root,
    resolve_invoker_identity,
)

# The one wiring of the required reviewers and the freshness rule (#1195),
# shared with done-work's gate and review-pr.
from _lib.pr_review import REVIEW_VIEW_FIELDS, PrReview, resolve_pr_review
from _lib.required_reviewers import Resolution
from _lib.review_contributions import collect_contributions
from _lib.verdict_freshness import FreshnessRule

CLOSING_KEYWORD_RE = re.compile(r"\b(?:closes|fixes|resolves)\s+#(\d+)", re.IGNORECASE)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Show the methodology-relevant view of a GitHub PR: title, "
            "Conventional Commits parse, state, branches, closing issues, "
            "reviewers, doc-impact presence, the latest reviewer verdicts "
            "(--field review) and every verdict posted, in posting order "
            "(--field review-history)."
        ),
    )
    parser.add_argument(
        "pr_number",
        type=int,
        help="GitHub PR number.",
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
    output = parser.add_mutually_exclusive_group()
    output.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of human-readable text.",
    )
    output.add_argument(
        "--field",
        metavar="NAME",
        default=None,
        help=(
            "Print only the value of a single field, with no surrounding "
            "chrome (scalars bare, lists one per line). Mutually exclusive "
            "with --json. Valid fields: " + ", ".join(PR_FIELD_NAMES) + "."
        ),
    )
    args = parser.parse_args()

    if args.field is not None and args.field not in PR_FIELD_NAMES:
        print(
            f"error: unknown field '{args.field}'.\nvalid fields: {', '.join(PR_FIELD_NAMES)}",
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
    if not bootstrap_gate.enforce("show-pr", capability_root=capability_root):
        return 2

    yaml_loader = YAML(typ="safe")
    config = load_adopter_config(capability_root)
    members = _read_members(capability_root, yaml_loader)
    invoker = resolve_invoker_identity(config=config)
    membership = check_membership(members, invoker)
    if not membership.allowed:
        print(membership.refusal_message, file=sys.stderr)
        return 1

    pr = _gh_get_pr(args.pr_number, config)
    if pr is None:
        return 2

    # Only a view that shows verdicts pays for resolving the required set.
    shows_verdicts = args.field in (None, "review", "review-history")
    freshness = (
        _resolve_review(args.pr_number, config, capability_root).freshness_rule(pr)
        if shows_verdicts
        else None
    )
    summary = _summarise(pr, freshness)
    if args.field is not None:
        for line in _field_lines_for(summary)[args.field]:
            print(line)
    elif args.json:
        print(json.dumps(summary, indent=2))
    else:
        _print_summary(args.pr_number, summary)
    return 0


def _summarise(pr: dict, freshness: FreshnessRule | None = None) -> dict:
    """The PR's methodology view. `freshness` judges each verdict; by default
    it is the rule for this PR with no floor-only reviewer, under which every
    verdict is held to any change since the head it reviewed."""
    if freshness is None:
        freshness = PrReview(
            Resolution(), author_delta=author_delta, base_kept=base_kept
        ).freshness_rule(pr)
    title = str(pr.get("title", ""))
    body = str(pr.get("body") or "")
    state = str(pr.get("state", "")).lower()
    head = pr.get("headRefName") or ""
    base = pr.get("baseRefName") or ""
    merged_at = pr.get("mergedAt")
    is_draft = bool(pr.get("isDraft"))
    url = pr.get("url")
    reviewers = [
        r.get("login") if isinstance(r, dict) else str(r) for r in (pr.get("reviewRequests") or [])
    ]

    conv = _parse_conventional_commits(title)
    closing_issues = _extract_closing_issues(body)
    has_doc_impact = "## Doc impact" in body
    comments = pr.get("comments") or []
    review = _summarise_review(comments, freshness)
    review_history = _summarise_review_history(comments, freshness)

    return {
        "title": title,
        "state": state,
        "is_draft": is_draft,
        "head": head,
        "base": base,
        "merged_at": merged_at,
        "url": url,
        "conventional_commits": conv,
        "closes": closing_issues,
        "reviewers": reviewers,
        "has_doc_impact_section": has_doc_impact,
        "review": review,
        "body": body,
        "review_history": review_history,
    }


def _summarise_review(comments: list, freshness: FreshnessRule) -> list[dict]:
    """Latest DEC-028 reviewer verdict per reviewer, token + reasons (#544).

    Delegates recognition and latest-per-reviewer selection to the SHARED
    selection (`_lib.agent_verdicts`) that `done-work`'s gate also consumes,
    so the two never diverge on *which* comment is a reviewer's current verdict
    (COR-007; one parser, not two). But the read surface is a SUPERSET of what
    the gate acts on, not the same set: it applies no freshness filter and no
    required-set membership filter, so it includes stale verdicts and verdicts
    from non-required reviewers that the gate excludes. It shows every posted
    verdict (latest per reviewer); the gate acts on a filtered subset.

    Because there is no freshness filter, a verdict can be shown as APPROVED on
    a live PR even though the gate would not count it. To keep the read honest
    about gate-agreement (#544's point: the agent reads the verdict to act on
    it), each entry is annotated by the gate's own freshness rule
    (`freshness`, #1179): `stale`, and `freshness` — the one-line reason, the
    head it reviewed and what changed since.

    Each entry carries the reviewer, the verdict token, the path
    (`local`/`remote`), the full comment body (the reasons), `stale` and
    `freshness`.
    """
    entries = []
    for v in latest_verdicts_per_reviewer(comments):
        assessment = freshness.assess(v)
        entries.append(
            {
                "reviewer": v.reviewer,
                "verdict": v.token,
                "path": v.path,
                "body": v.body,
                "stale": not assessment.fresh,
                "freshness": assessment.reason,
            }
        )
    return entries


def _summarise_review_history(comments: list, freshness: FreshnessRule) -> list[dict]:
    """Every DEC-028 verdict per reviewer, in posting order (#905).

    The full sequence behind `_summarise_review`'s latest-per-reviewer view,
    for reading earlier review rounds (an audit of a PR reviewed several
    times). Built on the same shared recogniser (`_lib.agent_verdicts`) with
    the same permissive read-surface scope as `review` — no freshness, marker
    or membership filter — so the verdicts shown here are exactly the ones
    `review` reduces, never a differently-parsed set.

    One entry per reviewer, ordered as `review` orders them, each carrying the
    reviewer, the path, and `verdicts`: every verdict that reviewer posted,
    oldest first. Each verdict carries the token, the comment's timestamp and
    url, the full body, `current` (it is the verdict `review` shows for this
    reviewer — every other one was superseded by a later round), and `stale`
    with its `freshness` reason (the same rule as `review`).
    """
    history = all_verdicts(comments)
    current = {id(v) for v in reduce_latest_per_reviewer(history)}
    by_reviewer: dict[tuple[str, str], list[dict]] = {}
    for v in history:
        assessment = freshness.assess(v)
        by_reviewer.setdefault((v.path, v.reviewer), []).append(
            {
                "verdict": v.token,
                "timestamp": v.timestamp,
                "url": v.url,
                "current": id(v) in current,
                "stale": not assessment.fresh,
                "freshness": assessment.reason,
                "body": v.body,
            }
        )
    return [
        {"reviewer": reviewer, "path": path, "verdicts": verdicts}
        for (path, reviewer), verdicts in sorted(by_reviewer.items())
    ]


# The addressable field vocabulary for `--field`. Order is the documented
# order (and is asserted to match `_field_lines_for`'s keys in the tests).
PR_FIELD_NAMES = (
    "title",
    "state",
    "draft",
    "base",
    "head",
    "merged-at",
    "cc-type",
    "cc-summary",
    "closes",
    "reviewers",
    "review",
    "review-history",
    "doc-impact",
    "body",
    "url",
)

# Shown by `--field review` when no reviewer has posted a DEC-028 verdict
# comment. A clear message, not an empty result / traceback (issue #544).
NO_VERDICT_MESSAGE = "no reviewer verdict posted"

# Appended to a shown verdict the freshness rule holds stale (#1179), naming
# why — the merge gate will not count such a verdict, so the read surface flags
# it rather than let an operator mistake it for gate-agreement (issue #544).
STALE_MARKER = " (stale — {reason}; the merge gate will not count it)"


def _scalar(value: object) -> list[str]:
    """Render a scalar field as zero or one output line.

    `None` and the empty string render as no output (a bare command for an
    absent field yields nothing, not a blank line).
    """
    if value is None:
        return []
    text = str(value)
    return [text] if text != "" else []


def _bool(value: object) -> list[str]:
    """Render a boolean field as a single `true`/`false` line."""
    return ["true" if value else "false"]


def _review_lines(review: list) -> list[str]:
    """Render the latest DEC-028 verdict(s) as readable lines (#544).

    Each reviewer's verdict is a header line (`<verdict> — <reviewer>`,
    qualified `local`/`remote`) followed by the verdict comment body indented
    beneath it, so an operator reads the token AND the reasons through the
    governed surface. Multiple reviewers are separated by a blank line. The
    absent case yields a single clear message rather than no output — a bare
    `--field review` on an unreviewed PR must not look like a silent empty
    field.

    A stale verdict (one `done-work`'s gate will not count) is marked in its
    header with the reason — the head it reviewed and what changed since — so
    an operator does not read an APPROVED that the merge gate will refuse and
    mistake it for gate-agreement.
    """
    if not review:
        return [NO_VERDICT_MESSAGE]
    lines: list[str] = []
    for i, entry in enumerate(review):
        if i > 0:
            lines.append("")
        reviewer = entry.get("reviewer") or "<unknown>"
        verdict = entry.get("verdict") or "<unknown>"
        path = entry.get("path")
        qualifier = f" ({path})" if path else ""
        stale = (
            STALE_MARKER.format(reason=entry.get("freshness") or "unknown")
            if entry.get("stale")
            else ""
        )
        lines.append(f"{verdict} — {reviewer}{qualifier}{stale}")
        body = str(entry.get("body") or "").strip()
        for body_line in body.splitlines():
            lines.append(f"    {body_line}" if body_line else "")
    return lines


# Qualifiers on a `--field review-history` verdict header.
CURRENT_MARKER = " (current)"
HISTORY_STALE_MARKER = " (stale)"


def _review_history_lines(history: list) -> list[str]:
    """Render every verdict per reviewer, in posting order (#905).

    Each reviewer is a header line (`<reviewer> (<path>) — <n> verdict(s)`)
    followed by its verdicts oldest first: a numbered line
    (`[<i>] <verdict> — <timestamp>`, qualified `(current)` for the one
    `--field review` shows and `(stale)` for one the gate would not count),
    then the comment body indented beneath it. Reviewers are separated by a
    blank line. No verdicts yields the same clear message as `--field review`.
    """
    if not history:
        return [NO_VERDICT_MESSAGE]
    lines: list[str] = []
    for i, entry in enumerate(history):
        if i > 0:
            lines.append("")
        reviewer = entry.get("reviewer") or "<unknown>"
        path = entry.get("path")
        qualifier = f" ({path})" if path else ""
        verdicts = entry.get("verdicts") or []
        noun = "verdict" if len(verdicts) == 1 else "verdicts"
        lines.append(f"{reviewer}{qualifier} — {len(verdicts)} {noun}")
        for n, v in enumerate(verdicts, start=1):
            flags = (CURRENT_MARKER if v.get("current") else "") + (
                HISTORY_STALE_MARKER if v.get("stale") else ""
            )
            verdict = v.get("verdict") or "<unknown>"
            timestamp = v.get("timestamp") or "<no timestamp>"
            lines.append(f"  [{n}] {verdict} — {timestamp}{flags}")
            body = str(v.get("body") or "").strip()
            for body_line in body.splitlines():
                lines.append(f"      {body_line}" if body_line else "")
    return lines


def _field_lines_for(s: dict) -> dict[str, list[str]]:
    """Project the summary into the addressable `--field` vocabulary.

    Each value is the list of output lines for that field: scalars are zero or
    one line, booleans a single true/false line, lists one item per line.
    Derived from the same summary the `--json` path serialises — no second
    fetch.
    """
    conv = s.get("conventional_commits") or {}
    cc_type = ""
    cc_summary = None
    if conv.get("matched"):
        cc_type = str(conv.get("type") or "")
        if conv.get("scope"):
            cc_type = f"{cc_type}({conv['scope']})"
        cc_summary = conv.get("summary")
    closes = [f"#{n}" for n in (s.get("closes") or [])]
    return {
        "title": _scalar(s.get("title")),
        "state": _scalar(s.get("state")),
        "draft": _bool(s.get("is_draft")),
        "base": _scalar(s.get("base")),
        "head": _scalar(s.get("head")),
        "merged-at": _scalar(s.get("merged_at")),
        "cc-type": _scalar(cc_type),
        "cc-summary": _scalar(cc_summary),
        "closes": closes,
        "reviewers": list(s.get("reviewers") or []),
        "review": _review_lines(s.get("review") or []),
        "review-history": _review_history_lines(s.get("review_history") or []),
        "doc-impact": _bool(s.get("has_doc_impact_section")),
        "body": _scalar(s.get("body")),
        "url": _scalar(s.get("url")),
    }


def _print_summary(pr_number: int, s: dict) -> None:
    print(f"PR #{pr_number}: {s.get('title') or ''}")
    print(
        f"  state:        {s.get('state') or '<unknown>'}"
        + ("  (draft)" if s.get("is_draft") else "")
    )
    print(f"  base:         {s.get('base') or '<unknown>'}")
    print(f"  head:         {s.get('head') or '<unknown>'}")
    conv = s.get("conventional_commits") or {}
    if conv.get("matched"):
        type_part = f"{conv.get('type', '')}"
        if conv.get("scope"):
            type_part += f"({conv['scope']})"
        print(f"  cc type:      {type_part}")
        print(f"  cc summary:   {conv.get('summary') or ''}")
    else:
        print("  cc type:      <does not match Conventional Commits pattern>")
    closes = s.get("closes") or []
    print(f"  closes:       {', '.join(f'#{n}' for n in closes) if closes else '<none>'}")
    reviewers = s.get("reviewers") or []
    print(f"  reviewers:    {', '.join(reviewers) or '<none>'}")
    review = s.get("review") or []
    if review:
        summary = ", ".join(
            f"{e.get('reviewer')}: {e.get('verdict')}" + (" (stale)" if e.get("stale") else "")
            for e in review
        )
        print(f"  review:       {summary}")
        print("                (--field review for reasons)")
    else:
        print(f"  review:       <{NO_VERDICT_MESSAGE}>")
    print(f"  doc impact:   {'present' if s.get('has_doc_impact_section') else 'missing'}")
    if s.get("merged_at"):
        print(f"  merged at:    {s['merged_at']}")
    if s.get("url"):
        print(f"  url:          {s['url']}")


def _parse_conventional_commits(title: str) -> dict:
    """Decompose `<type>(<scope>): <summary>` into parts.

    Returns a dict with `matched`, `type`, `scope`, `summary`.
    """
    m = re.match(
        r"^(?P<type>[a-z]+)(\((?P<scope>[^)]+)\))?:\s+(?P<summary>.+)$",
        title,
    )
    if not m:
        return {"matched": False}
    return {
        "matched": True,
        "type": m.group("type"),
        "scope": m.group("scope"),
        "summary": m.group("summary"),
    }


def _extract_closing_issues(pr_body: str) -> list[int]:
    out: list[int] = []
    for m in CLOSING_KEYWORD_RE.finditer(pr_body or ""):
        n = int(m.group(1))
        if n not in out:
            out.append(n)
    return out


def _gh_get_pr(pr_number: int, config: dict) -> dict | None:
    try:
        proc = gh_run(
            [
                "gh",
                "pr",
                "view",
                str(pr_number),
                "--json",
                ",".join(
                    (
                        "title",
                        "body",
                        "state",
                        "headRefName",
                        "baseRefName",
                        "mergedAt",
                        "isDraft",
                        "url",
                        "reviewRequests",
                        *REVIEW_VIEW_FIELDS,
                    )
                ),
            ],
            config,
            check=False,
        )
    except FileNotFoundError:
        print("error: `gh` not on PATH.", file=sys.stderr)
        return None
    if proc.returncode != 0:
        print(
            f"error: gh pr view {pr_number} failed.\nstderr: {proc.stderr.strip()}",
            file=sys.stderr,
        )
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def _resolve_review(
    pr_number: int,
    config: dict,
    capability_root: Path,
) -> PrReview:
    """The PR's required reviewers and freshness rule, resolved as
    `done-work`'s gate resolves them, for the freshness rule's floor-only
    reviewers (#1179).

    Through `_lib.pr_review.resolve_pr_review` — the ONE wiring the gate and
    `review-pr` call — handing it this script's `gh` helpers,
    `collect_contributions` and author-change readers. A resolution that
    fails names no floor-only reviewer, so a verdict is shown stale on any
    change; the gate, refusing on that failure, counts none.
    """
    return resolve_pr_review(
        pr_number,
        config,
        capability_root.parent.parent.parent,
        gh_run=gh_run,
        gh_get_issue=gh_get_issue,
        collect_contributions=collect_contributions,
        author_delta=author_delta,
        base_kept=base_kept,
    )


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
