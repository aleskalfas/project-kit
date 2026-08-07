"""`pkit report` — built-in adopter→project-kit feedback channel (PRJ-008 / ADR-047).

Composes a bug/feedback report with a **redacted** environment block and files it
to the distribution's fixed report target. This increment ships the **URL-first**
path (works with no `gh` auth — the browser is the review gate); the `gh`-auto-file
path, the target-naming confirm, tracking reads, and the maintainer side land in
later increments of #613.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import urllib.parse
from dataclasses import dataclass
from pathlib import Path

from project_kit.environment import collect_environment, render_environment_block

#: The distribution's fixed report target (`owner/repo`). Set by whoever ships this
#: pkit — for project-kit it is project-kit's own repo. Same shape as
#: `router.DISTRIBUTION_GIT_URL` (PRJ-004): a distribution constant a fork retargets
#: by editing here, **never** an adopter-facing `--repo` flag (ADR-047). Empty ⇒
#: unconfigured ⇒ `report` degrades rather than filing.
REPORT_TARGET = "aleskalfas/project-kit"

#: The two report kinds, each a GitHub label on the filed issue.
KINDS = ("bug", "feedback")


def compose_report_body(
    prose: str, env_block: str, *, on_behalf_of: str | None = None
) -> str:
    """Assemble the issue body: (optional attribution) + the reporter's prose +
    the redacted `## Environment` block. Pure over its inputs."""
    parts: list[str] = []
    if on_behalf_of:
        handle = on_behalf_of.lstrip("@")
        parts.append(f"_Reported for @{handle} (filed on their behalf)._")
        parts.append("")
    parts.append(prose.strip())
    parts.append("")
    parts.append(env_block.rstrip())
    return "\n".join(parts).strip() + "\n"


def build_new_issue_url(target: str, *, title: str, body: str, label: str) -> str:
    """A GitHub *prefilled* new-issue URL (title + body + label as query params).
    Opening it lands the user on the issue form with everything filled — the
    browser submit is the review gate, and it needs no `gh` auth."""
    query = urllib.parse.urlencode(
        {"title": title, "body": body, "labels": label}
    )
    return f"https://github.com/{target}/issues/new?{query}"


def compose_report(
    kind: str,
    *,
    title: str,
    prose: str,
    target_root: Path,
    on_behalf_of: str | None = None,
    include_private: bool = False,
) -> tuple[str, str]:
    """Compose a report → (full issue body, prefilled new-issue URL).

    Ties the redacted environment block (`collect_environment`) into the body and
    builds the URL against `REPORT_TARGET`. Raises `ValueError` on an unknown kind
    or an unconfigured target.
    """
    if kind not in KINDS:
        raise ValueError(f"unknown report kind {kind!r}; expected one of {KINDS}")
    if not REPORT_TARGET:
        raise ValueError(
            "no report target is configured for this distribution — `report` is "
            "inert (see PRJ-008)."
        )
    env = collect_environment(target_root, include_private=include_private)
    body = compose_report_body(
        prose, render_environment_block(env), on_behalf_of=on_behalf_of
    )
    url = build_new_issue_url(REPORT_TARGET, title=title, body=body, label=kind)
    return body, url


def gh_authenticated() -> bool:
    """True iff `gh` is installed and authenticated (so the auto-file path can run).
    Best-effort; any failure ⇒ False ⇒ the caller degrades to the URL."""
    if shutil.which("gh") is None:
        return False
    try:
        proc = subprocess.run(
            ["gh", "auth", "status"], capture_output=True, text=True, check=False
        )
    except OSError:
        return False
    return proc.returncode == 0


def file_report_via_gh(
    target: str, *, title: str, body: str, label: str
) -> str | None:
    """Create the report issue on `target` via `gh issue create`. Returns the new
    issue's URL on success, or None on any failure (caller degrades to the URL).

    This is a **categorically-foreign** write (ADR-047): it targets the
    distribution's repo (`--repo <target>`), never the session's own, so it is
    scoped *outside* the self-guard interlock by category — no
    `--allow-foreign-repo` override is used. The interactive target-naming confirm
    is the caller's (CLI) responsibility; under `--yes`/autonomy the caller does
    not reach here (it degrades to the draft URL — the deliberate `--yes`
    asymmetry).
    """
    cmd = [
        "gh", "issue", "create", "--repo", target,
        "--title", title, "--body", body, "--label", label,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or "(created)"


# --- tracking reads --------------------------------------------------

_TRACKED_HEADING = "## Tracked by"


@dataclass(frozen=True)
class ReportSummary:
    number: int
    title: str
    kind: str  # "bug" | "feedback" | "" (unlabelled)
    state: str  # display state: "open" | "in progress" | "closed"
    updated_at: str


def _gh_json(args: list[str]) -> object | None:
    """Run a `gh … --json …` read and parse its JSON; None on any failure."""
    try:
        proc = subprocess.run(args, capture_output=True, text=True, check=False)
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout or "null")
    except json.JSONDecodeError:
        return None


def _label_names(labels: object) -> list[str]:
    out: list[str] = []
    if isinstance(labels, list):
        for lab in labels:
            if isinstance(lab, dict) and isinstance(lab.get("name"), str):
                out.append(lab["name"])
            elif isinstance(lab, str):
                out.append(lab)
    return out


def display_state(gh_state: str, labels: list[str]) -> str:
    """Collapse a GitHub open/closed state + `state:*` labels to a display state."""
    if gh_state.lower() == "closed":
        return "closed"
    if "state:in-progress" in labels or "state:review" in labels:
        return "in progress"
    return "open"


def _kind_of(labels: list[str]) -> str:
    for k in KINDS:
        if k in labels:
            return k
    return ""


def _summarize(issue: dict) -> ReportSummary:
    labels = _label_names(issue.get("labels"))
    return ReportSummary(
        number=int(issue.get("number", 0)),
        title=str(issue.get("title", "")),
        kind=_kind_of(labels),
        state=display_state(str(issue.get("state", "")), labels),
        updated_at=str(issue.get("updatedAt", "")),
    )


def list_my_reports(target: str) -> list[ReportSummary] | None:
    """The invoker's reports on `target` (authored by them), bug/feedback only,
    newest first. None on gh failure (caller degrades)."""
    data = _gh_json([
        "gh", "issue", "list", "--repo", target, "--author", "@me",
        "--state", "all", "--limit", "100",
        "--json", "number,title,state,labels,updatedAt",
    ])
    if not isinstance(data, list):
        return None
    reports = [_summarize(i) for i in data if isinstance(i, dict)]
    reports = [r for r in reports if r.kind]  # bug/feedback only
    return sorted(reports, key=lambda r: r.updated_at, reverse=True)


def parse_tracked_by(body: str) -> list[int]:
    """Extract the `#N` issue references from a feedback body's `## Tracked by`
    section (a GitHub task-list), de-duped, in order."""
    if _TRACKED_HEADING not in body:
        return []
    section = body.split(_TRACKED_HEADING, 1)[1]
    section = re.split(r"\n#{1,6} ", section, maxsplit=1)[0]  # stop at next heading
    out: list[int] = []
    for m in re.findall(r"#(\d+)", section):
        n = int(m)
        if n not in out:
            out.append(n)
    return out


def resolve_states(target: str, numbers: list[int]) -> dict[int, str]:
    """Display state for each issue number on `target` (missing/failed → 'unknown')."""
    states: dict[int, str] = {}
    for n in numbers:
        data = _gh_json([
            "gh", "issue", "view", str(n), "--repo", target,
            "--json", "state,labels",
        ])
        if isinstance(data, dict):
            states[n] = display_state(
                str(data.get("state", "")), _label_names(data.get("labels"))
            )
        else:
            states[n] = "unknown"
    return states


def show_report(target: str, number: int) -> dict | None:
    """Fetch one report's detail (state, body, comments) + resolve its
    `## Tracked by` linked issues' states. None on gh failure."""
    data = _gh_json([
        "gh", "issue", "view", str(number), "--repo", target,
        "--json", "number,title,state,body,labels,comments",
    ])
    if not isinstance(data, dict):
        return None
    labels = _label_names(data.get("labels"))
    tracked = parse_tracked_by(str(data.get("body", "")))
    return {
        "number": int(data.get("number", number)),
        "title": str(data.get("title", "")),
        "state": display_state(str(data.get("state", "")), labels),
        "kind": _kind_of(labels),
        "comments": data.get("comments") or [],
        "tracked_by": resolve_states(target, tracked),
    }
