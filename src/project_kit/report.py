"""`pkit report` — built-in adopter→project-kit feedback channel (PRJ-008 / ADR-047).

Composes a bug/feedback report with a **redacted** environment block and files it
to the distribution's fixed report target. Two sides:

- **Reporter** (any adopter): `compose_report` + `file_report_via_gh` (the
  confirm-gated API post — the primary path when `gh` is authenticated, #662 —
  with `ensure_kind_label`'s create-if-missing kind label, #663),
  `build_new_issue_url` (the URL survivor path: no `gh` auth or an explicit
  `--url`, within `URL_BUDGET` only), `stage_report` / `list_staged` /
  `load_staged` (the `--yes` stage + human `report submit` split), and the
  tracking reads (`list_my_reports`, `show_report`).
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
import webbrowser
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

from project_kit.environment import collect_environment, render_environment_block

#: The distribution's fixed report target (`owner/repo`). Set by whoever ships this
#: pkit — for project-kit it is project-kit's own repo. Same shape as
#: `router.DISTRIBUTION_GIT_URL` (PRJ-004): a distribution constant a fork retargets
#: by editing here, **never** an adopter-facing `--repo` flag (ADR-047). Empty ⇒
#: unconfigured ⇒ `report` degrades rather than filing.
REPORT_TARGET = "aleskalfas/project-kit"

#: The report kinds. Each carries a title prefix + a namespaced GitHub label
#: (below); the body kind-marker stays the machine-authoritative signal.
KINDS = ("bug", "feedback", "change-request")

#: Title prefix per kind, stamped on EVERY composed title (#663 — before it,
#: only change-requests were prefixed, so a report whose label was dropped had
#: no visible kind at all). The prefilled-URL path can lose the GitHub label
#: (labels in a new-issue URL are dropped for non-collaborators), so the
#: prefix + the body kind-marker are the reliable classification signals.
KIND_TITLE_PREFIXES = {
    "bug": "[Bug]",
    "feedback": "[Feedback]",
    "change-request": "[CR]",
}

#: GitHub label per kind, namespaced `report:<kind>` (#663) so the channel's
#: vocabulary never collides with the target repo's own labels (project-kit
#: already carries a bare `bug` label, and the namespacing matches its
#: `type:`/`state:`/`workstream:` label convention). API posts ensure the
#: label exists first (`ensure_kind_label`, create-if-missing); the read side
#: keeps recognizing the legacy bare-kind names on old reports.
KIND_LABELS = {kind: f"report:{kind}" for kind in KINDS}

#: Fixed color per kind for `ensure_kind_label`'s create-if-missing (bug red
#: matches GitHub's default `bug`; the others pick distinct calm hues).
_KIND_LABEL_COLORS = {
    "bug": "d73a4a",
    "feedback": "0e8a16",
    "change-request": "1d76db",
}

#: Description stamped on every label `ensure_kind_label` creates — marks the
#: label as channel-owned, distinguishing it from the target's own vocabulary.
KIND_LABEL_DESCRIPTION = "pkit report kind"

#: Machine-readable marker embedded in every composed report body
#: (`<!-- pkit-report: key=value -->`, invisible when rendered). Carries
#: `kind` plus, when resolved, the `project` / `workstream` context pair
#: (ADR-050; `parse_report_marker` reads any key, so unknown future keys —
#: e.g. EPIC #411's version provenance — degrade gracefully).
_MARKER_RE = re.compile(r"<!--\s*pkit-report:\s*([^>]*?)\s*-->")

#: Headings of the change-request compose template (structured-ish, per PRJ-008's
#: structured-vs-freeform split): motivation / desired behaviour / current workaround.
_CR_HEADING_RE = re.compile(
    r"(?mi)^#{2,4}\s+(motivation|desired behaviour|current workaround)\b"
)


def kind_marker(
    kind: str, *, project: str | None = None, workstream: str | None = None
) -> str:
    """The body marker line for `kind` plus any resolved context keys
    (see `_MARKER_RE`). Values are tokenised (whitespace → `-`) because the
    marker format is space-separated `key=value` pairs; the human context
    line keeps the verbatim name."""
    tokens = [f"kind={kind}"]
    if project:
        tokens.append(f"project={_marker_token(project)}")
    if workstream:
        tokens.append(f"workstream={_marker_token(workstream)}")
    return f"<!-- pkit-report: {' '.join(tokens)} -->"


def _marker_token(value: str) -> str:
    """A marker-safe token: internal whitespace collapsed to `-`."""
    return re.sub(r"\s+", "-", value.strip())


def render_context_line(project: str | None, workstream: str | None) -> str:
    """The human context line for the composed body (ADR-050): present halves
    joined with ` · `; an unresolvable project is stated as omitted rather
    than silently dropped. Pure over its inputs."""
    parts: list[str] = []
    if project:
        parts.append(f"Project: {project}")
    if workstream:
        parts.append(f"Workstream: {workstream}")
    if not project:
        parts.append("(project: not declared)")
    return " · ".join(parts)


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


#: The on-behalf-of attribution line's stable prefix (`compose_report_body`
#: writes `_Reported for @<handle> (filed on their behalf)._`). One of the
#: three positive-provenance signals `is_report` accepts (#681).
_ATTRIBUTION_MARKER = "Reported for @"


def is_report(labels: list[str], body: str) -> bool:
    """Positive report provenance (#681): a namespaced `report:*` label, the
    body's `pkit-report` marker, or the on-behalf-of attribution line. Title
    prefixes and legacy bare-kind labels are **display-only** kind fallbacks
    (`classify_kind`) — they never create membership, because an ordinary
    tracker issue can carry both (the pm capability title-prefixes its own
    issues, and the target repo owns a bare `bug` label). Pure over its
    inputs."""
    if any(label.startswith("report:") for label in labels):
        return True
    if _MARKER_RE.search(body):
        return True
    return _ATTRIBUTION_MARKER in body


def classify_kind(labels: list[str], title: str = "", body: str = "") -> str:
    """Classify an issue's report kind: label wins (the namespaced
    `report:<kind>` names, then the legacy bare-kind names old reports carry),
    then the body kind-marker, then the kind's title prefix (#663 — all three
    prefixes, so a label-less URL filing like #660's still classifies); ''
    when it is not a report. The fallbacks exist because URL-filed issues from
    non-collaborators lose their labels. Classification is display-only: it
    never establishes *membership* — that is `is_report`'s job (#681)."""
    for k in KINDS:
        if KIND_LABELS[k] in labels:
            return k
    for k in KINDS:
        if k in labels:
            return k
    marker_kind = parse_report_marker(body).get("kind", "")
    if marker_kind in KINDS:
        return marker_kind
    for k, prefix in KIND_TITLE_PREFIXES.items():
        if title.startswith(prefix):
            return k
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
    prose: str,
    env_block: str,
    *,
    on_behalf_of: str | None = None,
    project: str | None = None,
    workstream: str | None = None,
) -> str:
    """Assemble the issue body: the context line (ADR-050 — first, right
    under the issue title) + (optional attribution) + the reporter's prose +
    the redacted `## Environment` block. Pure over its inputs."""
    parts: list[str] = []
    parts.append(render_context_line(project, workstream))
    parts.append("")
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
    project: str | None = None,
    workstream: str | None = None,
) -> tuple[str, str, str]:
    """Compose a report → (issue title, full issue body, prefilled new-issue URL).

    Ties the redacted environment block (`collect_environment`) into the body,
    stamps the body kind-marker, and builds the URL against `REPORT_TARGET`.
    Every kind gets its title prefix (`[Bug]`/`[Feedback]`/`[CR]`, #663 — the
    human-visible kind, reliable even where the label is dropped), prepended
    before the project parenthetical; a change-request additionally gets the
    motivation/desired-behaviour/workaround template. The resolved context
    (ADR-050) renders three ways: the human context line atop the body, the
    `project=`/`workstream=` marker keys, and a ` (<project>)` title
    parenthetical when the project is known. Raises `ValueError` on an
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
    prefix = KIND_TITLE_PREFIXES[kind]
    if not title.startswith(prefix):
        title = f"{prefix} {title}"
    if project:
        title = f"{title} ({project})"
    env = collect_environment(target_root, include_private=include_private)
    body = compose_report_body(
        prose,
        render_environment_block(env),
        on_behalf_of=on_behalf_of,
        project=project,
        workstream=workstream,
    )
    body = f"{body}\n{kind_marker(kind, project=project, workstream=workstream)}\n"
    url = build_new_issue_url(
        REPORT_TARGET, title=title, body=body, label=KIND_LABELS[kind]
    )
    return title, body, url


# --- scratchpad attachment (COR-043 / ADR-047 refinement) ------------

#: Issue-body budget for the composed send payload. GitHub caps bodies at
#: 65536 chars; 60000 leaves headroom for maintainer edits.
REPORT_BODY_BUDGET = 60000

#: Compose-time redaction patterns for *attached* content. The environment
#: block is redacted by construction (`environment.py` — no paths collected);
#: attached scratchpad notes are free prose, so the same exposure ($HOME,
#: home-dir paths) is caught by lint instead. Runs on EVERY path, drafts and
#: URL-first included: redaction is a property of the composed payload, not
#: of the channel that carries it (ADR-047 refinement).
_REDACTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("$HOME reference", re.compile(r"\$HOME\b")),
    ("macOS home path (/Users/...)", re.compile(r"/Users/[A-Za-z0-9._-]+")),
    ("Linux home path (/home/...)", re.compile(r"/home/[A-Za-z0-9._-]+")),
    ("home-relative path (~/...)", re.compile(r"(?<![\w.])~/")),
)


@dataclass(frozen=True)
class RedactionFinding:
    """One possibly-unredacted spot in attached content."""

    line: int
    pattern: str
    excerpt: str


def lint_redaction(text: str) -> list[RedactionFinding]:
    """Scan `text` for content the environment block redacts by construction
    ($HOME, home-dir paths). Findings are surfaced, never auto-stripped — the
    author decides (edit-or-send-anyway interactively; warnings on drafts).
    Pure over its input."""
    findings: list[RedactionFinding] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for name, pattern in _REDACTION_PATTERNS:
            if pattern.search(line):
                findings.append(RedactionFinding(line_no, name, line.strip()[:80]))
    return findings


@dataclass(frozen=True)
class SendPayload:
    """The confirmed unit of a send (ADR-047 refinement): the issue body plus,
    when the attachment exceeds the budget, ONE overflow comment carrying the
    full as-sent note text. Confirmed as a single gesture before any post."""

    body: str
    overflow_comment: str | None = None
    truncated: bool = False


def render_note_details(filename: str, note_text: str, *, truncated: bool = False) -> str:
    """The collapsed `<details>` section carrying an attached scratchpad note.
    Pure over its inputs."""
    summary = f"{filename} (as sent)"
    if truncated:
        summary = f"{filename} (as sent — excerpt; full text in the first comment)"
    return (
        f"<details>\n<summary>{summary}</summary>\n\n"
        f"{note_text.rstrip()}\n\n</details>"
    )


def attach_note(
    body: str, filename: str, note_text: str, *, budget: int = REPORT_BODY_BUDGET
) -> SendPayload:
    """Inline a scratchpad note into a composed report body (collapsed, before
    the environment block). Oversize rule (ADR-047 refinement): when the
    composed body would exceed `budget`, the body carries an excerpt and the
    FULL note text rides as one overflow comment — one logical send. Pure
    over its inputs."""
    full = _insert_before_environment(body, render_note_details(filename, note_text))
    if len(full) <= budget:
        return SendPayload(full)
    frame = _insert_before_environment(
        body, render_note_details(filename, "", truncated=True)
    )
    marker = "\n\n_(…truncated — the full note text is carried in the first comment below.)_"
    allowed = max(budget - len(frame) - len(marker), 0)
    excerpt = note_text[:allowed].rstrip() + marker
    excerpted_body = _insert_before_environment(
        body, render_note_details(filename, excerpt, truncated=True)
    )
    overflow = (
        f"Full text of `{filename}` (as sent) — the issue body carries only "
        f"an excerpt:\n\n{note_text}"
    )
    return SendPayload(excerpted_body, overflow, truncated=True)


def _insert_before_environment(body: str, block: str) -> str:
    """Insert `block` just before the `## Environment` section (or append when
    the section is absent). Pure over its inputs."""
    idx = body.find("## Environment")
    if idx == -1:
        return body.rstrip() + "\n\n" + block + "\n"
    return body[:idx] + block + "\n\n" + body[idx:]


def post_issue_comment(target: str, issue: str, body: str) -> tuple[bool, str]:
    """Post the overflow comment of an already-confirmed send (`issue` is the
    posted issue's URL or number). Returns (ok, verbatim error text).

    This is NOT an independent second write: it is the second API call of the
    ONE logical send the operator confirmed (ADR-047 refinement — reviewers
    should continue to reject any independent foreign write)."""
    cmd = ["gh", "issue", "comment", str(issue), "--repo", target, "--body", body]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except OSError as exc:
        return False, str(exc)
    if proc.returncode != 0:
        return False, (proc.stderr or proc.stdout).strip()
    return True, ""


# --- send path: URL budget, browser open, stage + submit (#662) ------

#: Budget (in characters) for a prefilled new-issue URL, measured on the FULL
#: encoded URL. The binding constraint is not the browser (Chrome/Firefox
#: accept URLs far beyond this) but the server edge: GitHub rejects request
#: lines beyond the common ~8 KB reverse-proxy cap with HTTP 414 (nginx's
#: `large_client_header_buffers` default is 8k; Apache's `LimitRequestLine`
#: is 8190 — the same order), so an oversized prefill HARD-FAILS on open
#: rather than degrading (#662). 6000 leaves ~2 KB of headroom under that
#: request-line cap for the method/path and intermediary inflation. Over
#: budget, the flow refuses the URL form and routes to the API post (or the
#: stage + submit split).
URL_BUDGET = 6000


def open_in_browser(url: str) -> bool:
    """Open `url` in the default browser; False on any failure. The caller
    prints the URL before attempting this, so a failure degrades to
    copy-paste rather than losing the draft."""
    try:
        return bool(webbrowser.open(url))
    except Exception:  # any browser failure degrades the same way
        return False


#: Where `--yes`/non-interactive composes stage their payload for the human
#: `pkit report submit` gesture. Project-local, and ignored by git via the
#: `.gitignore` the stager drops inside the directory itself — self-contained,
#: so no repo-root `.gitignore` edit (and no merge-primitive involvement) is
#: needed in any adopter.
DRAFTS_RELPATH = Path(".pkit/scratchpad/.report-drafts")

#: Separates the staged issue body from the staged overflow comment inside a
#: stage file. A body containing this exact line would confuse the parse —
#: accepted: stage files are short-lived, tool-written intermediates.
_DRAFT_OVERFLOW_MARKER = "<!-- pkit-report-draft: overflow-comment -->"

#: Stage-file format marker (header key `pkit-report-draft`), bumped on an
#: incompatible stage-file change so a stale draft is skipped, not misparsed.
_DRAFT_FORMAT = "1"


@dataclass(frozen=True)
class StagedDraft:
    """One staged send payload under `DRAFTS_RELPATH` — the `--yes` product,
    consumed by the interactive-only `report submit` (ADR-047: autonomy
    stages, a human posts)."""

    draft_id: str
    path: Path
    kind: str
    title: str
    target: str
    staged: str  # ISO timestamp of the compose
    payload: SendPayload
    note: str | None = None  # target_root-relative path of the attached note
    project: str | None = None
    workstream: str | None = None
    warnings: tuple[str, ...] = ()  # compose-time redaction findings, rendered


def render_finding(finding: RedactionFinding) -> str:
    """One redaction finding as the single line it rides everywhere: draft
    warnings, stage-file headers, interactive prompts. Pure over its input."""
    return f"line {finding.line}: {finding.pattern}: {finding.excerpt}"


def stage_report(
    target_root: Path,
    *,
    kind: str,
    title: str,
    payload: SendPayload,
    findings: list[RedactionFinding] | None = None,
    note_path: Path | None = None,
    project: str | None = None,
    workstream: str | None = None,
) -> StagedDraft:
    """Write the composed send payload to a stage file and return the draft.

    The stage file is markdown with a simple `key: value` header (own
    format, not YAML — titles and warning excerpts need no escaping because
    values are single-line and parsed by first-`': '` partition): kind,
    title, target, timestamp, the attached note's relative path, the
    resolved project/workstream pair, and one `warning:` line per
    compose-time redaction finding (the findings ride the stage so `submit`
    can re-surface them). The body follows the header; an overflow comment
    follows `_DRAFT_OVERFLOW_MARKER`. Edge whitespace is normalized on the
    round-trip; content is otherwise verbatim."""
    drafts_dir = target_root / DRAFTS_RELPATH
    drafts_dir.mkdir(parents=True, exist_ok=True)
    gitignore = drafts_dir / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("*\n", encoding="utf-8")

    draft_id = _new_draft_id(drafts_dir, kind)
    warnings = tuple(render_finding(f) for f in findings or [])
    note_rel: str | None = None
    if note_path is not None:
        try:
            note_rel = str(note_path.relative_to(target_root))
        except ValueError:
            note_rel = str(note_path)
    staged = datetime.now(UTC).isoformat(timespec="seconds")

    header = [
        "---",
        f"pkit-report-draft: {_DRAFT_FORMAT}",
        f"kind: {kind}",
        f"title: {title}",
        f"target: {REPORT_TARGET}",
        f"staged: {staged}",
    ]
    if note_rel:
        header.append(f"note: {note_rel}")
    if project:
        header.append(f"project: {project}")
    if workstream:
        header.append(f"workstream: {workstream}")
    header.extend(f"warning: {w}" for w in warnings)
    header.append("---")

    content = "\n".join(header) + "\n" + payload.body.rstrip("\n") + "\n"
    if payload.overflow_comment is not None:
        content += (
            f"\n{_DRAFT_OVERFLOW_MARKER}\n\n"
            + payload.overflow_comment.rstrip("\n")
            + "\n"
        )
    path = drafts_dir / f"{draft_id}.md"
    path.write_text(content, encoding="utf-8")
    return StagedDraft(
        draft_id, path, kind, title, REPORT_TARGET, staged, payload,
        note=note_rel, project=project, workstream=workstream, warnings=warnings,
    )


def _new_draft_id(drafts_dir: Path, kind: str) -> str:
    """A timestamped, collision-free draft id (`YYYYMMDD-HHMMSS-<kind>`)."""
    base = datetime.now(UTC).strftime("%Y%m%d-%H%M%S") + f"-{kind}"
    candidate, n = base, 2
    while (drafts_dir / f"{candidate}.md").exists():
        candidate = f"{base}-{n}"
        n += 1
    return candidate


def list_staged(target_root: Path) -> list[StagedDraft]:
    """The parseable staged drafts, oldest first (draft ids are timestamped,
    so name order is stage order). Unparseable files are skipped."""
    drafts_dir = target_root / DRAFTS_RELPATH
    if not drafts_dir.is_dir():
        return []
    drafts: list[StagedDraft] = []
    for path in sorted(drafts_dir.glob("*.md")):
        draft = _parse_stage_file(path)
        if draft is not None:
            drafts.append(draft)
    return drafts


def load_staged(target_root: Path, draft_id: str) -> StagedDraft | None:
    """One staged draft by id; None when absent or unparseable."""
    path = target_root / DRAFTS_RELPATH / f"{draft_id}.md"
    if not path.is_file():
        return None
    return _parse_stage_file(path)


def _parse_stage_file(path: Path) -> StagedDraft | None:
    """Parse one stage file (see `stage_report` for the format); None when it
    is not a current-format stage file."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        return None
    try:
        close = lines.index("---", 1)
    except ValueError:
        return None
    fields: dict[str, str] = {}
    warnings: list[str] = []
    for line in lines[1:close]:
        key, sep, value = line.partition(": ")
        if not sep:
            continue
        if key == "warning":
            warnings.append(value)
        else:
            fields[key] = value
    if fields.get("pkit-report-draft") != _DRAFT_FORMAT:
        return None
    rest = "\n".join(lines[close + 1 :])
    body, sep2, overflow = rest.partition(f"\n{_DRAFT_OVERFLOW_MARKER}\n")
    payload = SendPayload(
        body.rstrip("\n") + "\n",
        overflow.strip("\n") or None if sep2 else None,
        truncated=bool(sep2),
    )
    return StagedDraft(
        draft_id=path.stem,
        path=path,
        kind=fields.get("kind", ""),
        title=fields.get("title", ""),
        target=fields.get("target", REPORT_TARGET),
        staged=fields.get("staged", ""),
        payload=payload,
        note=fields.get("note"),
        project=fields.get("project"),
        workstream=fields.get("workstream"),
        warnings=tuple(warnings),
    )


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


def ensure_kind_label(target: str, kind: str) -> bool:
    """Make sure `kind`'s namespaced label exists on `target` before an API
    post applies it (#663 create-if-missing — the target repo typically does
    not define the channel's labels, and GitHub silently drops an unknown
    one). True when the label can be applied; False on any failure — the
    caller then posts WITHOUT the label and warns, because label plumbing must
    never block the send (the title prefix + body marker still carry the
    kind). Creating the label is part of the one confirmed send, not an
    independent foreign write (ADR-047's overflow-comment precedent)."""
    label = KIND_LABELS[kind]
    existing = _gh_json(
        ["gh", "label", "list", "--repo", target, "--search", label,
         "--json", "name"]
    )
    if isinstance(existing, list) and any(
        isinstance(item, dict) and item.get("name") == label for item in existing
    ):
        return True
    # Absent — or the list read failed, in which case creating is still the
    # best recovery: an "already exists" refusal just means the label is
    # there, which is the desired end state.
    cmd = [
        "gh", "label", "create", label, "--repo", target,
        "--color", _KIND_LABEL_COLORS[kind],
        "--description", KIND_LABEL_DESCRIPTION,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except OSError:
        return False
    if proc.returncode == 0:
        return True
    return "already exists" in (proc.stderr or proc.stdout).lower()


def file_report_via_gh(
    target: str, *, title: str, body: str, label: str | None
) -> str | None:
    """Create the report issue on `target` via `gh issue create`. Returns the new
    issue's URL on success, or None on any failure (caller degrades to the URL).
    `label=None` posts unlabelled — the `ensure_kind_label`-failure degrade
    (#663); the title prefix + body marker still carry the kind.

    This is a **categorically-foreign** write (ADR-047): it targets the
    distribution's repo (`--repo <target>`), never the session's own, so it is
    scoped *outside* the self-guard interlock by category — no
    `--allow-foreign-repo` override is used. The interactive target-and-identity
    confirm is the caller's (CLI) responsibility; under `--yes`/autonomy the
    caller does not reach here (it stages the payload for `report submit` —
    the deliberate `--yes` asymmetry: stage, never post).
    """
    cmd = [
        "gh", "issue", "create", "--repo", target,
        "--title", title, "--body", body,
    ]
    if label:
        cmd += ["--label", label]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or "(created)"


# --- tracking reads --------------------------------------------------

_TRACKED_HEADING = "## Tracked by"

#: Fields every summary-producing `gh issue list` query fetches — bodies for
#: marker classification, `url` so list rows can render the report's own link
#: (#678; before it only tracked-fix rollup rows carried one).
_SUMMARY_FIELDS = "number,title,state,labels,updatedAt,body,url"


@dataclass(frozen=True)
class ReportSummary:
    number: int
    title: str
    kind: str  # "bug" | "feedback" | "change-request" | "" (not a report)
    state: str  # display state: "open" | "in progress" | "closed"
    updated_at: str
    attributed: bool = False  # filed *for* the invoker by someone else (on-behalf-of)
    project: str = ""  # body marker's `project=` value; "" when absent
    workstream: str = ""  # body marker's `workstream=` value; "" when absent
    url: str = ""  # the report's own issue URL (#678); "" when not fetched


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


def _is_report_issue(issue: dict) -> bool:
    """`is_report` over a raw `gh` issue dict (#681) — the membership filter
    every summary-producing sweep applies client-side."""
    return is_report(_label_names(issue.get("labels")), str(issue.get("body", "")))


def _fetch_issue(target: str, number: int) -> dict | None:
    """One issue fetched by number with the summary fields — the read behind
    the locally-reported union leg (#681; bounded by the `reported/` note
    count). None on gh failure — the caller skips that row (best-effort,
    like the attributed query)."""
    data = _gh_json([
        "gh", "issue", "view", str(number), "--repo", target,
        "--json", _SUMMARY_FIELDS,
    ])
    return data if isinstance(data, dict) else None


def _summarize(issue: dict) -> ReportSummary:
    labels = _label_names(issue.get("labels"))
    title = str(issue.get("title", ""))
    body = str(issue.get("body", ""))  # "" when the query didn't fetch bodies
    marker = parse_report_marker(body)
    return ReportSummary(
        number=int(issue.get("number", 0)),
        title=title,
        kind=classify_kind(labels, title, body),
        state=display_state(str(issue.get("state", "")), labels),
        updated_at=str(issue.get("updatedAt", "")),
        project=marker.get("project", ""),
        workstream=marker.get("workstream", ""),
        url=str(issue.get("url", "")),
    )


def current_login() -> str | None:
    """The authenticated `gh` user's login, or None if it can't be determined.
    Public because the send path names it as the posting identity before every
    confirm (#662 — the browser-identity misattribution guard)."""
    data = _gh_json(["gh", "api", "user"])
    if isinstance(data, dict) and isinstance(data.get("login"), str):
        return data["login"]
    return None


def list_my_reports(
    target: str, target_root: Path | None = None
) -> list[ReportSummary] | None:
    """The invoker's reports on `target`, newest first — both those they
    **authored** and those **attributed** to them (filed on their behalf via
    `--on-behalf-of`, carrying a `Reported for @login` marker). Membership
    requires positive provenance (`is_report`, #681) — the classifier's
    prefix/legacy fallbacks no longer sweep in every ordinary prefix-titled
    issue the invoker authored — **unioned** with any issue a local
    `reported/` note references (`local_reported_notes`; how a raw-`gh`-filed
    report without a marker, like #660, stays listed), fetched by number.
    None on gh failure of the authored query (caller degrades); the
    attributed query and the per-note fetches are best-effort."""
    data = _gh_json([
        "gh", "issue", "list", "--repo", target, "--author", "@me",
        "--state", "all", "--limit", "100", "--json", _SUMMARY_FIELDS,
    ])
    if not isinstance(data, list):
        return None
    by_number: dict[int, ReportSummary] = {}
    for issue in data:
        if isinstance(issue, dict) and _is_report_issue(issue):
            s = _summarize(issue)
            by_number[s.number] = s

    login = current_login()
    if login:
        attr = _gh_json([
            "gh", "issue", "list", "--repo", target,
            "--search", f'in:body "Reported for @{login}"',
            "--state", "all", "--limit", "100", "--json", _SUMMARY_FIELDS,
        ])
        if isinstance(attr, list):
            for issue in attr:
                if not isinstance(issue, dict) or not _is_report_issue(issue):
                    continue
                s = _summarize(issue)
                if s.number not in by_number:  # authored wins
                    by_number[s.number] = replace(s, attributed=True)

    if target_root is not None:
        for number in local_reported_notes(target_root, target):
            if number in by_number:
                continue
            issue = _fetch_issue(target, number)
            if issue is not None:
                # membership is established by the local note; kind still
                # classifies via the full fallback chain (prefix included)
                by_number[number] = _summarize(issue)

    return sorted(by_number.values(), key=lambda r: r.updated_at, reverse=True)


def list_my_reports_tree(
    target: str, target_root: Path | None = None
) -> list[tuple[ReportSummary, dict[int, TrackedFix]]] | None:
    """Like `list_my_reports` (same membership rule + locally-reported union,
    #681), but each report is paired with its `## Tracked by` fixes resolved
    to `TrackedFix` (state + title + url, #664) — for the `--tree` view. One
    extra read per tracked issue; bounded by a personal report list. None on
    the initial gh failure."""
    data = _gh_json([
        "gh", "issue", "list", "--repo", target, "--author", "@me",
        "--state", "all", "--limit", "100", "--json", _SUMMARY_FIELDS,
    ])
    if not isinstance(data, list):
        return None
    rows: list[tuple[ReportSummary, dict[int, TrackedFix]]] = []
    seen: set[int] = set()
    for issue in data:
        if not isinstance(issue, dict) or not _is_report_issue(issue):
            continue
        summary = _summarize(issue)
        seen.add(summary.number)
        tracked = resolve_tracked(target, parse_tracked_by(str(issue.get("body", ""))))
        rows.append((summary, tracked))
    if target_root is not None:
        for number in local_reported_notes(target_root, target):
            if number in seen:
                continue
            issue = _fetch_issue(target, number)
            if issue is None:
                continue
            body = str(issue.get("body", ""))
            tracked = resolve_tracked(target, parse_tracked_by(body))
            rows.append((_summarize(issue), tracked))
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


@dataclass(frozen=True)
class TrackedFix:
    """One resolved `## Tracked by` fix (#664): its display state plus — when
    the read succeeded — the title and URL, so a rollup can say WHAT is fixing
    a report, not just its number. Offline/unresolved: state 'unknown',
    title/url empty (the render degrades to number + state)."""

    state: str
    title: str = ""
    url: str = ""


def resolve_tracked(target: str, numbers: list[int]) -> dict[int, TrackedFix]:
    """Resolve each tracked issue number on `target` to a `TrackedFix` — one
    `gh` read per number, the same per-ref seam `resolve_states` always used,
    now also carrying title + url for the rollup render (#664). A failed read
    degrades that entry to state 'unknown' with empty title/url."""
    fixes: dict[int, TrackedFix] = {}
    for n in numbers:
        data = _gh_json([
            "gh", "issue", "view", str(n), "--repo", target,
            "--json", "state,labels,title,url",
        ])
        if isinstance(data, dict):
            fixes[n] = TrackedFix(
                state=display_state(
                    str(data.get("state", "")), _label_names(data.get("labels"))
                ),
                title=str(data.get("title", "")),
                url=str(data.get("url", "")),
            )
        else:
            fixes[n] = TrackedFix(state="unknown")
    return fixes


def resolve_states(target: str, numbers: list[int]) -> dict[int, str]:
    """Display state for each issue number on `target` (missing/failed →
    'unknown'). The state-only view of `resolve_tracked` — kept for callers
    (`list_resolved`) that decide on states alone."""
    return {n: fix.state for n, fix in resolve_tracked(target, numbers).items()}


def local_reported_notes(target_root: Path, target: str) -> dict[int, str]:
    """Map issue number → note slug for every local `reported/` scratchpad
    note whose `reported_to` refs point at `target` (#664 — the one-tracking-
    truth reconciliation, read side only). `report list` uses this to tag a
    row `[note: <slug>]` when a locally-reported note references that issue:
    the ISSUE stays the truth for state, the NOTE's frontmatter the truth for
    what was sent — nothing is synced or stored (derive-don't-store). When
    several notes reference the same issue, the first (name-sorted) wins.
    Empty when `reported/` is absent (its lazy normal state)."""
    from project_kit import scratchpads

    reported_dir = target_root / ".pkit" / "scratchpad" / "reported"
    if not reported_dir.is_dir():
        return {}
    out: dict[int, str] = {}
    for path in sorted(reported_dir.glob("*.md")):
        try:
            refs = scratchpads.read_reported_refs(
                path.read_text(encoding="utf-8")
            )
        except OSError:
            continue
        for ref in refs:
            owner_repo, _, number = ref.partition("#")
            if owner_repo == target and number.isdigit():
                out.setdefault(int(number), scratchpads.note_slug(path.name))
    return out


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


def _inbox_queries(target: str, kinds: tuple[str, ...]) -> list[list[str]]:
    """The gh list queries covering `kinds`: per kind, the namespaced label
    (`report:<kind>`), the legacy bare-kind label (reports filed before the
    #663 namespacing — they still carry the body marker that admits them),
    and a body search for the kind's marker (a URL-filed report from a
    non-collaborator loses its label, so the marker is its discoverable
    signal). The former title-prefix search leg was the over-sweep vector
    (#681 — every ordinary pm-filed `[Bug]`-titled issue matched) and is
    gone: a raw-filed report with neither label nor marker is not inbox-
    discoverable (acceptable — the channel API-posts with markers; the
    reporter side still lists such issues via local `reported/` notes).
    Sweep noise is dropped by `is_report` client-side; bodies are fetched
    for marker classification and project grouping."""
    queries: list[list[str]] = []
    for kind in kinds:
        for label in (KIND_LABELS[kind], kind):
            queries.append([
                "gh", "issue", "list", "--repo", target, "--label", label,
                "--state", "all", "--limit", "100", "--json", _SUMMARY_FIELDS,
            ])
        queries.append([
            "gh", "issue", "list", "--repo", target,
            "--search", f'"pkit-report: kind={kind}" in:body',
            "--state", "all", "--limit", "100", "--json", _SUMMARY_FIELDS,
        ])
    return queries


def list_inbox(target: str, *, kind: str | None = None) -> list[ReportSummary] | None:
    """All reports on `target` (any author), newest first — the maintainer's
    triage queue. `kind` narrows to one report kind. Membership is the same
    `is_report` provenance rule as the reporter list (#681) — sweep noise
    (an ordinary issue matching a query) is dropped by it client-side. None
    on gh failure."""
    kinds = (kind,) if kind else KINDS
    reports: list[ReportSummary] = []
    for query in _inbox_queries(target, kinds):
        data = _gh_json(query)
        if not isinstance(data, list):
            return None
        reports.extend(
            _summarize(i) for i in data
            if isinstance(i, dict) and _is_report_issue(i)
        )
    # de-dup (an issue can match several queries) and sort newest-first
    seen: dict[int, ReportSummary] = {}
    for r in reports:
        if kind is None or r.kind == kind:
            seen.setdefault(r.number, r)
    return sorted(seen.values(), key=lambda r: r.updated_at, reverse=True)


def list_resolved(target: str) -> list[tuple[ReportSummary, list[int]]] | None:
    """Open feedbacks/change-requests on `target` whose `## Tracked by` issues are
    **all closed** — the close-prompt candidates — each paired with its tracked
    issue numbers. A report with no tracked issues is not resolved (nothing
    vouches for it); bugs are excluded (they close with their own fix);
    membership is `is_report`'s provenance rule, consistently with the inbox
    (#681). None on gh failure."""
    resolved: list[tuple[ReportSummary, list[int]]] = []
    seen: set[int] = set()
    for kind in ("feedback", "change-request"):
        for query in _inbox_queries(target, (kind,)):
            data = _gh_json(query)
            if not isinstance(data, list):
                return None
            for issue in data:
                if not isinstance(issue, dict) or not _is_report_issue(issue):
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
    `## Tracked by` linked issues to `TrackedFix` (state + title + url,
    #664). None on gh failure."""
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
        "tracked_by": resolve_tracked(target, parse_tracked_by(body)),
    }
