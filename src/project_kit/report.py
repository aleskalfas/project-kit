"""`pkit report` — built-in adopter→project-kit feedback channel (PRJ-008 / ADR-047).

Composes a bug/feedback report with a **redacted** environment block and files it
to the distribution's fixed report target. Two sides:

- **Reporter** (any adopter): `compose_report` / `build_new_issue_url` (URL-first,
  no `gh` auth needed — the browser is the review gate), `file_report_via_gh` (opt-in
  `--file` via `gh`), and the tracking reads (`list_my_reports`, `show_report`).
- **Maintainer** (only inside the report target — `in_report_target` gates it):
  `list_inbox` (triage queue, kind-filterable), `list_resolved` /
  `close_report_as_resolved` (the `--resolved` close-prompt), `link_fix` /
  `unlink_fix` (wire a fix issue into a feedback's `## Tracked by` section via the
  pure `add_tracked_ref` / `remove_tracked_ref`).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import urllib.parse
from dataclasses import dataclass, replace
from pathlib import Path

from project_kit.environment import collect_environment, render_environment_block

#: The distribution's fixed report target (`owner/repo`). Set by whoever ships this
#: pkit — for project-kit it is project-kit's own repo. Same shape as
#: `router.DISTRIBUTION_GIT_URL` (PRJ-004): a distribution constant a fork retargets
#: by editing here, **never** an adopter-facing `--repo` flag (ADR-047). Empty ⇒
#: unconfigured ⇒ `report` degrades rather than filing.
REPORT_TARGET = "aleskalfas/project-kit"

#: The report kinds, each a GitHub label on the filed issue.
KINDS = ("bug", "feedback", "change-request")

#: Title prefix stamped on change-request reports. The prefilled-URL path can lose
#: the GitHub label (labels in a new-issue URL are dropped for non-collaborators),
#: so the prefix + the body kind-marker are the reliable classification signals.
CHANGE_REQUEST_TITLE_PREFIX = "[CR]"

#: Machine-readable marker embedded in every composed report body
#: (`<!-- pkit-report: key=value -->`, invisible when rendered). Carries `kind`
#: today; a future `project` key rides the same format (`parse_report_marker`
#: already reads any key, so grouping degrades gracefully until it ships).
_MARKER_RE = re.compile(r"<!--\s*pkit-report:\s*([^>]*?)\s*-->")

#: Headings of the change-request compose template (structured-ish, per PRJ-008's
#: structured-vs-freeform split): motivation / desired behaviour / current workaround.
_CR_HEADING_RE = re.compile(
    r"(?mi)^#{2,4}\s+(motivation|desired behaviour|current workaround)\b"
)


def kind_marker(kind: str) -> str:
    """The body marker line for `kind` (see `_MARKER_RE`)."""
    return f"<!-- pkit-report: kind={kind} -->"


def parse_report_marker(body: str) -> dict[str, str]:
    """Parse all `<!-- pkit-report: key=value ... -->` markers in `body` into one
    dict (later markers win on a duplicate key). Unknown keys pass through — the
    forward seam for the project marker. Pure over its input."""
    out: dict[str, str] = {}
    for match in _MARKER_RE.finditer(body):
        for token in match.group(1).split():
            key, sep, value = token.partition("=")
            if sep and key:
                out[key] = value
    return out


def classify_kind(labels: list[str], title: str = "", body: str = "") -> str:
    """Classify an issue's report kind: label wins, then the body kind-marker,
    then the `[CR]` title prefix; '' when it is not a report. The fallbacks exist
    because URL-filed issues from non-collaborators lose their labels."""
    for k in KINDS:
        if k in labels:
            return k
    marker_kind = parse_report_marker(body).get("kind", "")
    if marker_kind in KINDS:
        return marker_kind
    if title.startswith(CHANGE_REQUEST_TITLE_PREFIX):
        return "change-request"
    return ""


def apply_change_request_template(prose: str) -> str:
    """Scaffold `prose` into the change-request template (motivation / desired
    behaviour / current workaround) unless it already carries those headings.
    The placeholders are filled (or pruned) in the browser / by the author before
    filing — URL-first keeps the form editable. Pure over its input."""
    if _CR_HEADING_RE.search(prose):
        return prose
    return (
        "### Motivation\n\n"
        f"{prose.strip()}\n\n"
        "### Desired behaviour\n\n"
        "_(what should happen instead — edit before filing)_\n\n"
        "### Current workaround\n\n"
        "_(how you cope today, if at all — edit before filing)_"
    )


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
) -> tuple[str, str, str]:
    """Compose a report → (issue title, full issue body, prefilled new-issue URL).

    Ties the redacted environment block (`collect_environment`) into the body,
    stamps the body kind-marker, and builds the URL against `REPORT_TARGET`. A
    change-request additionally gets the `[CR]` title prefix and the
    motivation/desired-behaviour/workaround template. Raises `ValueError` on an
    unknown kind or an unconfigured target.
    """
    if kind not in KINDS:
        raise ValueError(f"unknown report kind {kind!r}; expected one of {KINDS}")
    if not REPORT_TARGET:
        raise ValueError(
            "no report target is configured for this distribution — `report` is "
            "inert (see PRJ-008)."
        )
    if kind == "change-request":
        prose = apply_change_request_template(prose)
        if not title.startswith(CHANGE_REQUEST_TITLE_PREFIX):
            title = f"{CHANGE_REQUEST_TITLE_PREFIX} {title}"
    env = collect_environment(target_root, include_private=include_private)
    body = compose_report_body(
        prose, render_environment_block(env), on_behalf_of=on_behalf_of
    )
    body = f"{body}\n{kind_marker(kind)}\n"
    url = build_new_issue_url(REPORT_TARGET, title=title, body=body, label=kind)
    return title, body, url


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
    kind: str  # "bug" | "feedback" | "change-request" | "" (not a report)
    state: str  # display state: "open" | "in progress" | "closed"
    updated_at: str
    attributed: bool = False  # filed *for* the invoker by someone else (on-behalf-of)
    project: str = ""  # body marker's `project=` value; "" until that marker ships


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


def _summarize(issue: dict) -> ReportSummary:
    labels = _label_names(issue.get("labels"))
    title = str(issue.get("title", ""))
    body = str(issue.get("body", ""))  # "" when the query didn't fetch bodies
    return ReportSummary(
        number=int(issue.get("number", 0)),
        title=title,
        kind=classify_kind(labels, title, body),
        state=display_state(str(issue.get("state", "")), labels),
        updated_at=str(issue.get("updatedAt", "")),
        project=parse_report_marker(body).get("project", ""),
    )


def _current_login() -> str | None:
    """The authenticated `gh` user's login, or None if it can't be determined."""
    data = _gh_json(["gh", "api", "user"])
    if isinstance(data, dict) and isinstance(data.get("login"), str):
        return data["login"]
    return None


def list_my_reports(target: str) -> list[ReportSummary] | None:
    """The invoker's reports on `target`, bug/feedback only, newest first — both
    those they **authored** and those **attributed** to them (filed on their behalf
    via `--on-behalf-of`, carrying a `Reported for @login` marker). None on gh
    failure of the authored query (caller degrades); the attributed query is
    best-effort and skipped when the login can't be resolved."""
    data = _gh_json([
        "gh", "issue", "list", "--repo", target, "--author", "@me",
        "--state", "all", "--limit", "100",
        "--json", "number,title,state,labels,updatedAt",
    ])
    if not isinstance(data, list):
        return None
    by_number: dict[int, ReportSummary] = {}
    for issue in data:
        if isinstance(issue, dict):
            s = _summarize(issue)
            if s.kind:
                by_number[s.number] = s

    login = _current_login()
    if login:
        attr = _gh_json([
            "gh", "issue", "list", "--repo", target,
            "--search", f'in:body "Reported for @{login}"',
            "--state", "all", "--limit", "100",
            "--json", "number,title,state,labels,updatedAt",
        ])
        if isinstance(attr, list):
            for issue in attr:
                if not isinstance(issue, dict):
                    continue
                s = _summarize(issue)
                if s.kind and s.number not in by_number:  # authored wins
                    by_number[s.number] = replace(s, attributed=True)

    return sorted(by_number.values(), key=lambda r: r.updated_at, reverse=True)


def list_my_reports_tree(
    target: str,
) -> list[tuple[ReportSummary, dict[int, str]]] | None:
    """Like `list_my_reports`, but each report is paired with its `## Tracked by`
    fixes resolved to states — for the `--tree` view. One extra read per tracked
    issue; bounded by a personal report list. None on the initial gh failure."""
    data = _gh_json([
        "gh", "issue", "list", "--repo", target, "--author", "@me",
        "--state", "all", "--limit", "100",
        "--json", "number,title,state,labels,updatedAt,body",
    ])
    if not isinstance(data, list):
        return None
    rows: list[tuple[ReportSummary, dict[int, str]]] = []
    for issue in data:
        if not isinstance(issue, dict):
            continue
        summary = _summarize(issue)
        if not summary.kind:  # bug/feedback only
            continue
        tracked = resolve_states(target, parse_tracked_by(str(issue.get("body", ""))))
        rows.append((summary, tracked))
    rows.sort(key=lambda row: row[0].updated_at, reverse=True)
    return rows


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


def add_tracked_ref(body: str, n: int) -> str:
    """Return `body` with `#n` present in its `## Tracked by` task-list. Creates the
    section if absent; no-op if `#n` is already tracked. Pure over its inputs."""
    if n in parse_tracked_by(body):
        return body
    line = f"- [ ] #{n}"
    trailing = "\n" if body.endswith("\n") or not body else ""
    if _TRACKED_HEADING not in body:
        return body.rstrip() + f"\n\n{_TRACKED_HEADING}\n\n{line}\n"
    lines = body.splitlines()
    head = next(i for i, ln in enumerate(lines) if ln.strip() == _TRACKED_HEADING)
    end = len(lines)
    for j in range(head + 1, len(lines)):
        if re.match(r"#{1,6} ", lines[j]):
            end = j
            break
    insert_at = head + 1
    for j in range(head + 1, end):
        if lines[j].strip():
            insert_at = j + 1
    lines.insert(insert_at, line)
    return "\n".join(lines) + trailing


def remove_tracked_ref(body: str, n: int) -> str:
    """Return `body` with any `#n` task-list entry dropped from its `## Tracked by`
    section (the heading is kept even if it empties). Pure over its inputs."""
    if _TRACKED_HEADING not in body:
        return body
    trailing = "\n" if body.endswith("\n") else ""
    result: list[str] = []
    in_section = False
    for line in body.splitlines():
        if line.strip() == _TRACKED_HEADING:
            in_section = True
            result.append(line)
            continue
        if in_section and re.match(r"#{1,6} ", line):
            in_section = False
        if in_section and re.match(rf"\s*- \[[ xX]\] #{n}\b", line):
            continue  # drop this tracked-ref line
        result.append(line)
    return "\n".join(result) + trailing


def current_repo_slug() -> str | None:
    """The `owner/repo` the current directory's default repo resolves to (via `gh`),
    or None if it can't be determined. Used to gate the maintainer side to the
    report-target repo (PRJ-008: `inbox`/`link` run only inside the target)."""
    data = _gh_json(["gh", "repo", "view", "--json", "nameWithOwner"])
    if isinstance(data, dict) and isinstance(data.get("nameWithOwner"), str):
        return data["nameWithOwner"]
    return None


def in_report_target() -> bool:
    """True iff the current repo is the configured report target."""
    return bool(REPORT_TARGET) and current_repo_slug() == REPORT_TARGET


_INBOX_FIELDS = "number,title,state,labels,updatedAt,body"


def _inbox_queries(target: str, kinds: tuple[str, ...]) -> list[list[str]]:
    """The gh list queries covering `kinds`: one per kind label, plus a title
    search for change-requests (a URL-filed CR from a non-collaborator loses its
    label, so the `[CR]` prefix is its discoverable signal; false positives are
    dropped by `classify_kind` client-side). Bodies are fetched for marker
    classification and project grouping."""
    queries: list[list[str]] = []
    for kind in kinds:
        queries.append([
            "gh", "issue", "list", "--repo", target, "--label", kind,
            "--state", "all", "--limit", "100", "--json", _INBOX_FIELDS,
        ])
        if kind == "change-request":
            queries.append([
                "gh", "issue", "list", "--repo", target,
                "--search", f'"{CHANGE_REQUEST_TITLE_PREFIX}" in:title',
                "--state", "all", "--limit", "100", "--json", _INBOX_FIELDS,
            ])
    return queries


def list_inbox(target: str, *, kind: str | None = None) -> list[ReportSummary] | None:
    """All reports on `target` (any author), newest first — the maintainer's
    triage queue. `kind` narrows to one report kind. Non-report issues swept in
    by the CR title search are dropped by classification. None on gh failure."""
    kinds = (kind,) if kind else KINDS
    reports: list[ReportSummary] = []
    for query in _inbox_queries(target, kinds):
        data = _gh_json(query)
        if not isinstance(data, list):
            return None
        reports.extend(_summarize(i) for i in data if isinstance(i, dict))
    # de-dup (an issue can match several queries) and sort newest-first
    seen: dict[int, ReportSummary] = {}
    for r in reports:
        if r.kind and (kind is None or r.kind == kind):
            seen.setdefault(r.number, r)
    return sorted(seen.values(), key=lambda r: r.updated_at, reverse=True)


def list_resolved(target: str) -> list[tuple[ReportSummary, list[int]]] | None:
    """Open feedbacks/change-requests on `target` whose `## Tracked by` issues are
    **all closed** — the close-prompt candidates — each paired with its tracked
    issue numbers. A report with no tracked issues is not resolved (nothing
    vouches for it); bugs are excluded (they close with their own fix). None on
    gh failure."""
    resolved: list[tuple[ReportSummary, list[int]]] = []
    seen: set[int] = set()
    for kind in ("feedback", "change-request"):
        for query in _inbox_queries(target, (kind,)):
            data = _gh_json(query)
            if not isinstance(data, list):
                return None
            for issue in data:
                if not isinstance(issue, dict):
                    continue
                summary = _summarize(issue)
                if (
                    summary.kind != kind
                    or summary.state == "closed"
                    or summary.number in seen
                ):
                    continue
                seen.add(summary.number)
                tracked = parse_tracked_by(str(issue.get("body", "")))
                if not tracked:
                    continue
                states = resolve_states(target, tracked)
                if all(state == "closed" for state in states.values()):
                    resolved.append((summary, tracked))
    resolved.sort(key=lambda row: row[0].updated_at, reverse=True)
    return resolved


def close_report_as_resolved(target: str, number: int, tracked: list[int]) -> bool:
    """Post a closing comment on report `#number` (naming its closed fixes) and
    close it. Same-repo maintainer edit (the caller's gate ensures cwd == target).
    Only ever invoked after an explicit interactive confirm — never autonomously
    (the report family's close-prompt discipline). True iff both steps succeed."""
    refs = ", ".join(f"#{n}" for n in tracked)
    comment = (
        f"All tracked fixes ({refs}) are closed — closing this report as "
        "resolved. If something is still missing, reply here or file a new "
        "report with `pkit report`."
    )
    for cmd in (
        ["gh", "issue", "comment", str(number), "--repo", target, "--body", comment],
        ["gh", "issue", "close", str(number), "--repo", target],
    ):
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        except OSError:
            return False
        if proc.returncode != 0:
            return False
    return True


def _edit_body(target: str, number: int, body: str) -> bool:
    """`gh issue edit <n> --repo <target> --body <body>`. This is a *local* mutation
    when run inside the target repo (the maintainer-side gate ensures cwd == target,
    so it is not a foreign write). True on success."""
    cmd = ["gh", "issue", "edit", str(number), "--repo", target, "--body", body]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except OSError:
        return False
    return proc.returncode == 0


def link_fix(target: str, feedback_n: int, fix_n: int) -> bool:
    """Add `#fix_n` to feedback `#feedback_n`'s `## Tracked by` section. Idempotent
    (a duplicate link is a no-op that still succeeds). True on success."""
    data = _gh_json([
        "gh", "issue", "view", str(feedback_n), "--repo", target, "--json", "body",
    ])
    if not isinstance(data, dict):
        return False
    new_body = add_tracked_ref(str(data.get("body", "")), fix_n)
    return _edit_body(target, feedback_n, new_body)


def unlink_fix(target: str, feedback_n: int, fix_n: int) -> bool:
    """Remove `#fix_n` from feedback `#feedback_n`'s `## Tracked by` section.
    Idempotent. True on success."""
    data = _gh_json([
        "gh", "issue", "view", str(feedback_n), "--repo", target, "--json", "body",
    ])
    if not isinstance(data, dict):
        return False
    new_body = remove_tracked_ref(str(data.get("body", "")), fix_n)
    return _edit_body(target, feedback_n, new_body)


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
    title = str(data.get("title", ""))
    body = str(data.get("body", ""))
    return {
        "number": int(data.get("number", number)),
        "title": title,
        "state": display_state(str(data.get("state", "")), labels),
        "kind": classify_kind(labels, title, body),
        "comments": data.get("comments") or [],
        "tracked_by": resolve_states(target, parse_tracked_by(body)),
    }
