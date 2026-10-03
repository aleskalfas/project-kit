"""Keep project-kit's one tracking issue for the whole-repository friction check.

The workflow `.github/workflows/friction-report.yml` runs the whole-repository
friction check (COR-050 point 6) on `main` with the full history, renders its
findings with `scripts/friction_report_body.py --json`, and hands that
publication to this script, which keeps **one** GitHub issue in step with it
(ADR-055 point 5). It is the only code of the pipeline that talks to `gh`.

- **Which issue it is.** An issue the pipeline's token opened (`AUTHOR`) that
  carries either sign: the marker (`MARKER`, a hidden comment) on any line of
  its body, or the label (`LABEL`). A person's issue that quotes the marker or
  wears the label is never taken for it. Whichever sign a hand removed is put
  back: the body is rewritten with the marker, the label is added again.
- **Found in a listing that is complete.** The token's issues, open and closed,
  are listed by author alone — a label filter would send `gh` through the search
  index, which lags a write, and a run right after another could miss the issue
  that one opened. The signs are read here. A listing that fills `LISTING_LIMIT`
  may have left the issue out: the run fails and opens nothing.
- **Open exactly while a finding needs an answer.** Opened, with its label, when
  one does and the listing shows no tracking issue; reopened when one does
  again; closed when none does, its body saying so and still listing the
  deferrals and the measures. With nothing to answer and no issue, none is
  opened.
- **Rewritten in place** when its body differs — never a comment per run — and
  left alone when nothing changed: the same findings render the same body. The
  body opens with `NOTICE`, which tells a reader that edits to it are lost.
- **One tracking issue; a second is a failed run that names both.** When the
  listing shows more than one, the oldest is kept in step, nothing is changed
  on the others, and the run fails saying which to close and strip of their
  signs. Nothing is closed for anyone.

It decides nothing about friction: what needs an answer is the renderer's. It
exits 0 whatever the check found, and 1, saying why, only when the publication
cannot be read, `gh` refuses, the listing may be incomplete, or there is more
than one tracking issue — the check reports and never fails (COR-050 point 12),
and the workflow is no required status. What it says of a failure goes to the
log and, in a workflow, to the run's step summary; never into the issue.

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

#: The tracking issue's marker: a line of its body, invisible when rendered.
MARKER = "<!-- pkit-friction-report -->"

#: The line every body opens with, under the marker.
NOTICE = (
    "_Automation keeps this issue: each run of the whole-repository friction check rewrites "
    "this body, and edits to it are lost._"
)

#: The label the issue carries, created when it is first needed.
LABEL = "friction-report"
LABEL_COLOR = "d4c5f9"
LABEL_DESCRIPTION = "The whole-repository friction check's tracking issue, kept by automation"

#: The identity a workflow's token writes as, spelled two ways that are not
#: interchangeable. The listing must ask for `github-actions[bot]`:
#: `gh issue list --author app/github-actions` matches nothing, so a listing by
#: that spelling finds no tracking issue and every run opens another. The
#: issues it lists then give their author as `app/github-actions`, the spelling
#: each listed issue's author is checked against.
AUTHOR_LISTED_AS = "github-actions[bot]"
AUTHOR = "app/github-actions"

TITLE = "Friction: what the whole-repository check finds"

#: The version of `scripts/friction_report_body.py --json` this script reads.
PUBLICATION_VERSION = 1

#: How many of the token's issues the listing asks for. One that returns as many
#: may be incomplete.
LISTING_LIMIT = 1000

Runner = Callable[..., subprocess.CompletedProcess[str]]


class Refused(Exception):
    """The run fails: the publication cannot be read, `gh` refused a call, or the
    tracking issue cannot be told. Nothing more is done."""


@dataclass(frozen=True)
class Issue:
    number: int
    open: bool
    body: str
    labelled: bool


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
                + "; nothing more was done"
            )
        return proc.stdout or ""


def tracking_issues(gh: Gh) -> list[Issue]:
    """Every tracking issue, oldest first: the issues the token opened that carry
    the marker or the label. Raises Refused when the listing may be incomplete."""
    listed = gh(
        "issue",
        "list",
        "--author",
        AUTHOR_LISTED_AS,
        "--state",
        "all",
        "--limit",
        str(LISTING_LIMIT),
        "--json",
        "number,state,body,labels,author",
    )
    try:
        entries = json.loads(listed)
    except ValueError as exc:
        raise Refused("`gh issue list` answered no list of issues") from exc
    if not isinstance(entries, list):
        raise Refused("`gh issue list` answered no list of issues")
    entries = cast("list[Any]", entries)
    if len(entries) >= LISTING_LIMIT:
        raise Refused(
            f"`gh issue list` answered {len(entries)} issues, as many as it was asked for, so "
            f"the listing may be incomplete and a tracking issue may be missing from it; "
            f"nothing was opened or changed"
        )
    found = [issue for issue in map(_tracking_issue, entries) if issue is not None]
    return sorted(found, key=lambda issue: issue.number)


def _tracking_issue(raw: Any) -> Issue | None:
    """The tracking issue a listed entry is, or `None`: another author's, or one
    of the token's with neither sign."""
    if not isinstance(raw, Mapping):
        raise Refused("`gh issue list` answered an entry that is no issue")
    entry = cast("Mapping[str, Any]", raw)
    number, state, body = entry.get("number"), entry.get("state"), entry.get("body")
    author, labels = entry.get("author"), entry.get("labels")
    if (
        not isinstance(number, int)
        or not isinstance(state, str)
        or not isinstance(body, str)
        or not isinstance(author, Mapping)
        or not isinstance(labels, list)
    ):
        raise Refused("`gh issue list` answered an entry that is no issue")
    if cast("Mapping[str, Any]", author).get("login") != AUTHOR:
        return None
    labelled = any(
        isinstance(label, Mapping) and cast("Mapping[str, Any]", label).get("name") == LABEL
        for label in cast("list[Any]", labels)
    )
    if not labelled and MARKER not in body:
        return None
    return Issue(number, state == "OPEN", body, labelled)


def publish(publication: Publication, gh: Gh) -> str:
    """Bring the tracking issue in step with `publication`; say what was done.
    Raises Refused, having kept the oldest in step, when there is more than one."""
    body = f"{MARKER}\n{NOTICE}\n\n{publication.body}"
    found = tracking_issues(gh)
    if not found:
        if not publication.needs_answer:
            return "nothing needs an answer and there is no tracking issue: nothing to do"
        _ensure_label(gh)
        with _body_file(body) as path:
            url = gh("issue", "create", "--title", TITLE, "--body-file", path, "--label", LABEL)
        return f"opened the tracking issue: {url.strip()}"
    issue, *others = found
    done: list[str] = []
    if _normalised(issue.body) != _normalised(body):
        with _body_file(body) as path:
            gh("issue", "edit", str(issue.number), "--body-file", path)
        done.append("rewrote its body")
    if not issue.labelled:
        _ensure_label(gh)
        gh("issue", "edit", str(issue.number), "--add-label", LABEL)
        done.append("put its label back")
    if publication.needs_answer and not issue.open:
        gh("issue", "reopen", str(issue.number))
        done.append("reopened it: a finding needs an answer")
    elif not publication.needs_answer and issue.open:
        gh("issue", "close", str(issue.number), "--reason", "completed")
        done.append("closed it: nothing needs an answer")
    said = f"tracking issue #{issue.number}: " + ("; ".join(done) or "unchanged")
    if others:
        extra = ", ".join(f"#{other.number}" for other in others)
        raise Refused(
            f"there is more than one tracking issue: #{issue.number}, {extra}. "
            f"#{issue.number}, the oldest, was kept in step ({said}); nothing was changed on "
            f"{extra}. Close {extra} and remove the marker line `{MARKER}` and the `{LABEL}` "
            f"label from each, so that one tracking issue is left"
        )
    return said


def _ensure_label(gh: Gh) -> None:
    """The label exists before an issue is given it. One that exists already is
    left as it is; any other refusal stops the run."""
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
    """A temporary file holding `body`, for `--body-file`; removed on leaving. What
    no UTF-8 can hold is written escaped, so no body stops the run."""
    handle, path = tempfile.mkstemp(prefix="friction-report-", suffix=".md")
    try:
        with os.fdopen(handle, "w", encoding="utf-8", errors="backslashreplace") as out:
            out.write(body)
        yield path
    finally:
        os.unlink(path)


def _normalised(text: str) -> str:
    """A body as compared: line endings unified, surrounding whitespace dropped — what
    the tracker may change in a body without changing what it says."""
    return text.replace("\r\n", "\n").strip()


def _fail(message: str) -> int:
    """Say why the run fails: in the log and, in a workflow, in the step summary."""
    print(f"error: {message}.", file=sys.stderr)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8", errors="backslashreplace") as out:
            out.write(f"\n**The friction report's run failed.** {message}.\n")
    return 1


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
    except (OSError, ValueError) as exc:
        return _fail(f"{args.publication} cannot be read ({exc}); nothing was published")
    try:
        print(publish(read_publication(text, args.publication), Gh(run)))
    except Refused as exc:
        return _fail(str(exc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
