"""`pkit report` — built-in adopter→project-kit feedback channel (PRJ-008 / ADR-047).

Composes a bug/feedback report with a **redacted** environment block and files it
to the distribution's fixed report target. This increment ships the **URL-first**
path (works with no `gh` auth — the browser is the review gate); the `gh`-auto-file
path, the target-naming confirm, tracking reads, and the maintainer side land in
later increments of #613.
"""

from __future__ import annotations

import urllib.parse
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
