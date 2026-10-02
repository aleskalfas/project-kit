"""Keep project-kit's one tracking issue for the whole-repository friction check.

The workflow `.github/workflows/friction-report.yml` runs the whole-repository
friction check (COR-050 point 6) with the full history, daily and after every
push to `main`, renders its findings with `scripts/friction_report_body.py
--json`, and hands that publication to this script, which keeps **one** GitHub
issue in step with it, through `gh`:

- **Found by its marker** — the body's first line is `MARKER`, a hidden comment
  — looked for only among the issues the automation opened (`AUTHOR`) that carry
  its label (`LABEL`), so an issue that quotes the marker is never taken for it.
- **Opened**, with its label, when a finding needs an answer and there is none.
- **Rewritten in place** when its body differs, and **reopened** when findings
  return: never a comment per run, never a second issue.
- **Closed** when nothing needs an answer, its body saying so; the deferrals and
  the measures stay in it. With nothing to answer and no issue, none is opened.
- **Left alone** when nothing changed: the same findings render the same body,
  so a run that finds what the last one found changes nothing.

It decides nothing about friction: what needs an answer is the renderer's. It
exits 0 whatever the check found, and 1, saying why, only when the publication
cannot be read or `gh` refuses — the check reports and never fails (COR-050
point 12), and the workflow is no required status.

The body reaches `gh` as a file (`--body-file`), and every call is an argument
list, never a shell line, so nothing the findings carry is run. It calls `gh`
directly rather than project-management's verbs: those file work items for
people — a type, a parent, an owner, a lifecycle — which this report is not, and
their gates ask for a member's identity a workflow's token does not have.

From the repository root, where `gh` reaches the repository's remote:

    uv run python scripts/friction_tracking_issue.py <publication.json>
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from typing import Any, cast

#: The tracking issue's marker: the first line of its body, invisible when rendered.
MARKER = "<!-- pkit-friction-report -->"

#: The label the issue carries, created when the first issue is opened, and the
#: author `gh` names for an issue opened with a workflow's token. Only an issue
#: with both is ever looked at for the marker.
LABEL = "friction-report"
LABEL_COLOR = "d4c5f9"
LABEL_DESCRIPTION = "The whole-repository friction check's tracking issue, kept by automation"
AUTHOR = "app/github-actions"

TITLE = "Friction: what the whole-repository check finds"

#: The version of `scripts/friction_report_body.py --json` this script reads.
PUBLICATION_VERSION = 1

#: How many of the automation's labelled issues are read when looking for the marker.
SEARCH_LIMIT = 100

Runner = Callable[..., subprocess.CompletedProcess[str]]


class Refused(Exception):
    """The publication cannot be read, or `gh` refused a call: nothing more is done."""


@dataclass(frozen=True)
class Issue:
    number: int
    open: bool
    body: str


@dataclass(frozen=True)
class Publication:
    needs_answer: int
    body: str


def read_publication(text: str, source: str) -> Publication:
    """The renderer's publication as `source` holds it. Raises Refused otherwise."""
    try:
        document = json.loads(text)
    except ValueError:
        document = None
    if not isinstance(document, Mapping):
        raise Refused(f"{source} holds no publication of `scripts/friction_report_body.py --json`")
    publication = cast("Mapping[str, Any]", document)
    version = publication.get("schema_version")
    if version != PUBLICATION_VERSION:
        raise Refused(
            f"{source} is a publication of schema_version {version!r}; "
            f"this script reads {PUBLICATION_VERSION}"
        )
    needs_answer = publication.get("needs_answer")
    body = publication.get("body")
    if not isinstance(needs_answer, int) or needs_answer < 0 or not isinstance(body, str):
        raise Refused(f"{source} gives no count of findings that need an answer and no body")
    return Publication(needs_answer, body)


class Gh:
    """`gh`, called with an argument list from the working directory."""

    def __init__(self, run: Runner = subprocess.run) -> None:
        self._run = run

    def __call__(self, *args: str) -> str:
        try:
            proc = self._run(["gh", *args], capture_output=True, text=True, check=False)
        except OSError as exc:
            raise Refused(f"`gh` could not be run ({exc})") from exc
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip()
            raise Refused(
                f"`gh {' '.join(args[:2])}` exited {proc.returncode}"
                + (f": {detail}" if detail else "")
            )
        return proc.stdout or ""


def find(gh: Gh) -> Issue | None:
    """The tracking issue: the oldest the automation opened with its label whose body
    opens with the marker; `None` when there is none."""
    listed = gh(
        "issue",
        "list",
        "--state",
        "all",
        "--label",
        LABEL,
        "--author",
        AUTHOR,
        "--limit",
        str(SEARCH_LIMIT),
        "--json",
        "number,state,body,author",
    )
    try:
        entries = json.loads(listed)
    except ValueError as exc:
        raise Refused("`gh issue list` answered no list of issues") from exc
    if not isinstance(entries, list):
        raise Refused("`gh issue list` answered no list of issues")
    found: list[Issue] = []
    for raw in cast("list[Any]", entries):
        if not isinstance(raw, Mapping):
            continue
        entry = cast("Mapping[str, Any]", raw)
        author = entry.get("author")
        login = (
            cast("Mapping[str, Any]", author).get("login") if isinstance(author, Mapping) else None
        )
        body = entry.get("body")
        number = entry.get("number")
        if login != AUTHOR or not isinstance(body, str) or not isinstance(number, int):
            continue
        if _normalised(body).split("\n", 1)[0].strip() != MARKER:
            continue
        found.append(Issue(number, entry.get("state") == "OPEN", body))
    return min(found, key=lambda issue: issue.number, default=None)


def publish(publication: Publication, gh: Gh) -> str:
    """Bring the tracking issue in step with `publication`; say what was done."""
    body = f"{MARKER}\n{publication.body}"
    issue = find(gh)
    if issue is None:
        if not publication.needs_answer:
            return "nothing needs an answer and there is no tracking issue: nothing to do"
        _ensure_label(gh)
        with _body_file(body) as path:
            url = gh("issue", "create", "--title", TITLE, "--body-file", path, "--label", LABEL)
        return f"opened the tracking issue: {url.strip()}"
    done: list[str] = []
    if _normalised(issue.body) != _normalised(body):
        with _body_file(body) as path:
            gh("issue", "edit", str(issue.number), "--body-file", path)
        done.append("rewrote its body")
    if publication.needs_answer and not issue.open:
        gh("issue", "reopen", str(issue.number))
        done.append("reopened it: a finding needs an answer")
    elif not publication.needs_answer and issue.open:
        gh("issue", "close", str(issue.number), "--reason", "completed")
        done.append("closed it: nothing needs an answer")
    return f"tracking issue #{issue.number}: " + ("; ".join(done) or "unchanged")


def _ensure_label(gh: Gh) -> None:
    """The label exists before the issue is opened with it. One that exists already
    is left as it is; any other refusal stops the run, since an issue opened
    without its label would never be found again."""
    try:
        gh(
            "label",
            "create",
            LABEL,
            "--color",
            LABEL_COLOR,
            "--description",
            LABEL_DESCRIPTION,
        )
    except Refused as exc:
        if "already exists" not in str(exc).lower():
            raise


@contextlib.contextmanager
def _body_file(body: str) -> Iterator[str]:
    """A temporary file holding `body`, for `--body-file`; removed on leaving."""
    handle, path = tempfile.mkstemp(prefix="friction-report-", suffix=".md")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as out:
            out.write(body)
        yield path
    finally:
        os.unlink(path)


def _normalised(text: str) -> str:
    """A body as compared: line endings unified, surrounding whitespace dropped — what
    the tracker may change in a body without changing what it says."""
    return text.replace("\r\n", "\n").strip()


def main(argv: list[str] | None = None, run: Runner = subprocess.run) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Keep the one tracking issue of the whole-repository friction check in step with "
            "a publication of `scripts/friction_report_body.py --json`."
        ),
    )
    parser.add_argument("publication", help="The file the renderer's --json output was written to.")
    args = parser.parse_args(argv)
    try:
        with open(args.publication, encoding="utf-8") as handle:
            text = handle.read()
    except OSError as exc:
        print(
            f"error: {args.publication} cannot be read ({exc}); nothing published.", file=sys.stderr
        )
        return 1
    try:
        print(publish(read_publication(text, args.publication), Gh(run)))
    except Refused as exc:
        print(f"error: {exc}; nothing more was published.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
