#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml>=0.18",
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
import subprocess
import sys
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))
from _lib.agent_verdicts import (  # noqa: E402
    PATH_LOCAL,
    latest_verdicts_per_reviewer,
)
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Show the methodology-relevant view of a GitHub PR: title, "
            "Conventional Commits parse, state, branches, closing issues, "
            "reviewers, doc-impact presence."
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
            f"error: unknown field '{args.field}'.\n"
            f"valid fields: {', '.join(PR_FIELD_NAMES)}",
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

    summary = _summarise(pr)
    if args.field is not None:
        for line in _field_lines_for(summary)[args.field]:
            print(line)
    elif args.json:
        print(json.dumps(summary, indent=2))
    else:
        _print_summary(args.pr_number, summary)
    return 0


def _summarise(pr: dict) -> dict:
    title = str(pr.get("title", ""))
    body = str(pr.get("body") or "")
    state = str(pr.get("state", "")).lower()
    head = pr.get("headRefName") or ""
    base = pr.get("baseRefName") or ""
    merged_at = pr.get("mergedAt")
    is_draft = bool(pr.get("isDraft"))
    url = pr.get("url")
    reviewers = [
        r.get("login") if isinstance(r, dict) else str(r)
        for r in (pr.get("reviewRequests") or [])
    ]

    conv = _parse_conventional_commits(title)
    closing_issues = _extract_closing_issues(body)
    has_doc_impact = "## Doc impact" in body
    latest_commit_ts = _latest_commit_timestamp(pr.get("commits") or [])
    review = _summarise_review(pr.get("comments") or [], latest_commit_ts)

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
    }


def _summarise_review(
    comments: list, latest_commit_ts: str = ""
) -> list[dict]:
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
    a live PR even though it predates the latest commit — which `done-work`
    would refuse. To keep the read honest about gate-agreement (#544's point:
    the agent reads the verdict to act on it), each entry is annotated `stale`
    when its timestamp is at/​before `latest_commit_ts` (the freshness anchor
    the gate uses). When `latest_commit_ts` is empty (no resolvable commit
    timestamp), nothing is marked stale — we render without the marker rather
    than guess.

    Each entry carries the reviewer, the verdict token, the path
    (`local`/`remote`), the full comment body (the reasons), and `stale`.
    """
    verdicts = latest_verdicts_per_reviewer(comments)
    return [
        {
            "reviewer": v.reviewer,
            "verdict": v.token,
            "path": v.path,
            "body": v.body,
            "stale": bool(latest_commit_ts) and v.timestamp <= latest_commit_ts,
        }
        for v in verdicts
    ]


def _latest_commit_timestamp(commits: list) -> str:
    """The latest commit's timestamp, the gate's verdict-freshness anchor.

    Mirrors `done-work`'s anchor: `gh pr view --json commits` returns the
    commits in order, so the last entry's `committedDate` (falling back to
    `authoredDate`) is the freshness boundary against which a shown verdict is
    marked stale. Returns "" when no commit timestamp is resolvable — the
    caller then renders every verdict without a stale marker rather than
    erroring.
    """
    if not commits:
        return ""
    last = commits[-1]
    if not isinstance(last, dict):
        return ""
    return str(last.get("committedDate") or last.get("authoredDate") or "")


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
    "doc-impact",
    "body",
    "url",
)

# Shown by `--field review` when no reviewer has posted a DEC-028 verdict
# comment. A clear message, not an empty result / traceback (issue #544).
NO_VERDICT_MESSAGE = "no reviewer verdict posted"

# Appended to a shown verdict that predates the latest commit — the merge gate
# anchors freshness to that commit and will not count such a verdict, so the
# read surface flags it rather than let an operator mistake it for
# gate-agreement (issue #544).
STALE_MARKER = " (stale — predates the latest commit; the merge gate will not count it)"


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

    A stale verdict (one predating the latest commit — which `done-work`'s
    gate will not count) is marked in its header, so an operator does not read
    an APPROVED that the merge gate will refuse and mistake it for
    gate-agreement.
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
        stale = STALE_MARKER if entry.get("stale") else ""
        lines.append(f"{verdict} — {reviewer}{qualifier}{stale}")
        body = str(entry.get("body") or "").strip()
        for body_line in body.splitlines():
            lines.append(f"    {body_line}" if body_line else "")
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
        "doc-impact": _bool(s.get("has_doc_impact_section")),
        "body": _scalar(s.get("body")),
        "url": _scalar(s.get("url")),
    }


def _print_summary(pr_number: int, s: dict) -> None:
    print(f"PR #{pr_number}: {s.get('title') or ''}")
    print(f"  state:        {s.get('state') or '<unknown>'}"
          + ("  (draft)" if s.get("is_draft") else ""))
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
    print(
        f"  closes:       "
        f"{', '.join(f'#{n}' for n in closes) if closes else '<none>'}"
    )
    reviewers = s.get("reviewers") or []
    print(f"  reviewers:    {', '.join(reviewers) or '<none>'}")
    review = s.get("review") or []
    if review:
        summary = ", ".join(
            f"{e.get('reviewer')}: {e.get('verdict')}"
            + (" (stale)" if e.get("stale") else "")
            for e in review
        )
        print(f"  review:       {summary}")
        print("                (--field review for reasons)")
    else:
        print(f"  review:       <{NO_VERDICT_MESSAGE}>")
    print(
        f"  doc impact:   {'present' if s.get('has_doc_impact_section') else 'missing'}"
    )
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
                "title,body,state,headRefName,baseRefName,mergedAt,"
                "isDraft,url,reviewRequests,comments,commits",
            ],
            config,
            check=False,
        )
    except FileNotFoundError:
        print("error: `gh` not on PATH.", file=sys.stderr)
        return None
    if proc.returncode != 0:
        print(
            f"error: gh pr view {pr_number} failed.\n"
            f"stderr: {proc.stderr.strip()}",
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
