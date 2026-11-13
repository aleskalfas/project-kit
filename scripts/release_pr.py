"""The branch and the description of the release pull request (#2862).

The release-pr workflow (`.github/workflows/release-pr.yml`) first runs this
script for the tags whose notes an earlier run left unpublished. It runs `pkit
release plan --json`, then this script for the open release pull requests it
replaces, and for the branch it pushes the release to. On that branch it runs
`pkit release apply --yes`, and this script again for the trailer line `apply`
printed and for the pull request's description, before it pushes:

    uv run python scripts/release_pr.py unpublished --tags <ls-remote> --releases <tags>
    uv run python scripts/release_pr.py open --prs <open pull requests> --head <commit>
    uv run python scripts/release_pr.py branch --version <version> --run-id <run id>
    uv run python scripts/release_pr.py trailer --apply-output <what apply printed>
    uv run python scripts/release_pr.py body --plan <plan> --branch <branch> \\
        --repository-url <url> --trailer <line>

- **The notes left unpublished** (ADR-092 point 5). A release's or a candidate's
  tag on `origin` with no GitHub Release lacks its notes: the run that pushed it
  stopped before it published them. The script names the version of each such
  tag, oldest first, and the workflow publishes their notes before anything
  else.
- **The open release pull requests** (ADR-092 point 6, the way on). A release
  pull request whose body's trailer line names the default branch's head, the
  commit this run plans from, is the one a person reviews, so the run opens no
  second. Every other one, planned from an older head or naming none, is
  stale: `pkit release merge` refuses it, so the workflow closes it, and
  opens one planned from the new head.
- **The trailer line** names the commit the release's plan read,
  `Release-plan-commit: <commit>`, as `pkit release apply` printed it. The
  workflow commits the release with it, and the description ends with it.

- **The branch** is `release/v<version>`, after the backbone version the
  release computes. Where `origin` already has that branch, as a run that failed
  after its push leaves it, the branch is `release/v<version>-<run id>`, so the
  push does not fail on it. The workflow opens no pull request while one is open
  from any `release/` branch, so a branch left behind has none open from it. A
  release that moves no backbone takes `release/<run id>`. `pkit release merge`
  takes a pull request from any branch under `release/`, so it merges each.
- **The description** holds the version bumps, each with the floor and bound
  lines the plan gives it, the migration-dir warnings (#465), and the
  changelog's new section, the top one, which `pkit release apply` wrote. GitHub
  keeps at most `PULL_REQUEST_BODY_LIMIT` characters in a pull request's
  description, and refuses to open one with more. Where the section would take
  the description past that, a line takes its place that says so and links
  `CHANGELOG.md` on the release branch, where the section is the first. So does
  `pkit release publish-notes` for a section longer than a Release keeps
  (#2384). The bumps and the warnings are kept whole. A description too long
  even without the section is refused, before anything is pushed.

It needs the standard library, `git`, and the trailer's one reading, in
`project_kit.release`. Exit 0 with what it names on standard output; 1, saying
why, when `git` fails, a file cannot be read, `apply` printed no one trailer
line, or the description is too long without the section.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Collection, Mapping
from pathlib import Path
from typing import Any

from project_kit.release import plan_commit_line, plan_commits_named

#: The most characters GitHub keeps in a pull request's description: it refuses a
#: longer one with "Body is too long (maximum is 65536 characters)".
PULL_REQUEST_BODY_LIMIT = 65_536

#: The prefix of every release branch, the one `pkit release merge` takes.
BRANCH_PREFIX = "release/"

#: The remote the release branch is pushed to.
REMOTE = "origin"

#: The changelog `pkit release apply` writes its new section at the top of.
CHANGELOG = "CHANGELOG.md"

_HEADS = "refs/heads/"

INTRO = (
    "Automated release PR — review the version bumps and changelog, then merge.",
    "Merging tags the backbone version post-merge (release-tag.yml). "
    "Do not squash away the version bump.",
)

CHANGELOG_HEADING = "## Generated changelog"


class Refused(Exception):
    """`git` failed, the plan cannot be read, or the description does not fit."""


# --- The branch --------------------------------------------------------------


def release_branch(version: str, run_id: str, taken: Collection[str]) -> str:
    """The branch a run pushes the release to: `release/v<version>`, or
    `release/v<version>-<run id>` where `taken`, the branches `origin` has,
    holds that one already. `release/<run id>` where the release moves no
    backbone, so `version` is empty."""
    if not version:
        return f"{BRANCH_PREFIX}{run_id}"
    branch = f"{BRANCH_PREFIX}v{version}"
    return f"{branch}-{run_id}" if branch in taken else branch


def branches_listed(ls_remote_output: str) -> set[str]:
    """The branches `git ls-remote --heads` lists, one `<object id>\\t<ref>` a line."""
    branches: set[str] = set()
    for line in ls_remote_output.split("\n"):
        _, tab, ref = line.removesuffix("\r").partition("\t")
        if tab and ref.startswith(_HEADS):
            branches.add(ref.removeprefix(_HEADS))
    return branches


def remote_branches(repo: Path) -> set[str]:
    """The branches `origin` has, as the clone at `repo` reaches it."""
    args = ["ls-remote", "--heads", REMOTE]
    try:
        completed = subprocess.run(
            ["git", *args], cwd=repo, capture_output=True, text=True, check=False
        )
    except OSError as exc:
        raise Refused(f"`git` cannot be run ({exc})") from exc
    if completed.returncode != 0:
        said = completed.stderr.strip() or completed.stdout.strip()
        raise Refused(f"`git {' '.join(args)}` failed: {said}")
    return branches_listed(completed.stdout)


# --- The description ---------------------------------------------------------


def changelog_section(changelog: str) -> str:
    """The changelog's top section: from its first `## ` heading up to the next
    one, or the end. Empty where it has no such heading."""
    lines = changelog.split("\n")
    if lines[-1] == "":
        lines.pop()
    start = next((i for i, line in enumerate(lines) if line.startswith("## ")), None)
    if start is None:
        return ""
    end = next(
        (j for j in range(start + 1, len(lines)) if lines[j].startswith("## ")),
        len(lines),
    )
    return "".join(f"{line}\n" for line in lines[start:end])


def bump_lines(plan: Mapping[str, Any]) -> list[str]:
    """Each release's bump, then the floor and bound lines the plan gives it, as
    `pkit release plan` prints them."""
    out: list[str] = []
    for release in plan.get("releases") or []:
        out.append(
            f"- {release['component']}: {release['old_version']} → "
            f"{release['new_version']} ({release['segment']})"
        )
        floor = release.get("requires_backbone_floor") or {}
        ranges = [
            floor,
            *(release.get("requires_capabilities_floors") or []),
            *(release.get("requires_capabilities_bounds") or []),
        ]
        out.extend(f"  - {line}" for each in ranges for line in each.get("lines") or [])
    return out


def _head(plan: Mapping[str, Any]) -> str:
    """The description down to the changelog's heading: the bumps, and the
    warnings where there are any."""
    lines = [*INTRO, "", "## Version bumps", *bump_lines(plan)]
    warnings = plan.get("migration_warnings") or []
    if warnings:
        lines += ["", "## Migration-dir warnings (see #465)", *(f"- {w}" for w in warnings)]
    lines += ["", CHANGELOG_HEADING]
    return "".join(f"{line}\n" for line in lines)


def changelog_pointer(whole: int, *, branch: str, repository_url: str | None) -> str:
    """The lines that take the section's place, where with it the description
    would hold `whole` characters: they say why, and link `CHANGELOG.md` on
    `branch`, or name it where there is no `repository_url`."""
    where = f"`{CHANGELOG}` on `{branch}`"
    if repository_url:
        where = f"[{where}]({repository_url.rstrip('/')}/blob/{branch}/{CHANGELOG})"
    return (
        "The changelog's new section is too long to show here. With it this description "
        f"would hold {whole:,} characters, past the {PULL_REQUEST_BODY_LIMIT:,} GitHub keeps "
        f"in a pull request's description.\n\nRead it as the first section of {where}.\n"
    )


def pull_request_body(
    plan: Mapping[str, Any],
    changelog: str,
    *,
    branch: str,
    repository_url: str | None,
    trailer: str,
) -> str:
    """The release pull request's description: the bumps, the warnings, and the
    changelog's new section where the whole fits `PULL_REQUEST_BODY_LIMIT`, or
    the pointer to it on `branch` where it does not; then the `trailer` line,
    last. Raises Refused where even the description without the section does
    not fit."""
    head = _head(plan)
    tail = f"\n{trailer}\n"
    section = changelog_section(changelog)
    whole = head + section + tail
    if len(whole) <= PULL_REQUEST_BODY_LIMIT:
        return whole
    pointer = changelog_pointer(len(whole), branch=branch, repository_url=repository_url)
    short = head + pointer + tail
    if len(short) > PULL_REQUEST_BODY_LIMIT:
        raise Refused(
            f"the description is {len(short):,} characters without the changelog's section, "
            f"past the {PULL_REQUEST_BODY_LIMIT:,} GitHub keeps in a pull request's description"
        )
    return short


# --- The notes an earlier run left unpublished --------------------------------

#: A release's or a candidate's tag, by its full reference on `origin`:
#: `refs/tags/v<X.Y.Z>`, or `refs/tags/v<X.Y.Z>rc<N>` (ADR-089 point 9).
_RELEASE_TAG_RE = re.compile(r"refs/tags/v((\d+)\.(\d+)\.(\d+)(?:rc(\d+))?)")


def unpublished(ls_remote_output: str, released: Collection[str]) -> list[str]:
    """The version of each release or candidate tag `git ls-remote --tags` lists, one
    `<object id>\\t<ref>` a line, with no Release: its tag is none of `released`,
    the tags the Releases are on. Oldest first in PEP 440's order, so each
    candidate comes before the release of its version."""
    versions: dict[str, tuple[int, ...]] = {}
    for line in ls_remote_output.split("\n"):
        _, tab, ref = line.removesuffix("\r").partition("\t")
        match = _RELEASE_TAG_RE.fullmatch(ref) if tab else None
        if match is None or f"v{match.group(1)}" in released:
            continue
        major, minor, patch, number = match.group(2, 3, 4, 5)
        final = (1, 0) if number is None else (0, int(number))
        versions[match.group(1)] = (int(major), int(minor), int(patch), *final)
    return sorted(versions, key=versions.__getitem__)


# --- The trailer line, and the open release pull requests -------------------


def trailer_printed(apply_output: str) -> str:
    """The one trailer line `pkit release apply` printed in `apply_output`,
    naming the commit the release's plan read. Raises Refused where it printed
    none, or named more than one commit."""
    named = plan_commits_named(apply_output)
    if len(named) != 1:
        raise Refused(
            f"`pkit release apply` printed {len(named)} trailer lines naming the commit its "
            "plan read, not one"
        )
    return plan_commit_line(named[0])


def open_release_pull_requests(listed: object, head: str) -> tuple[list[int], list[int]]:
    """The open release pull requests `gh pr list --json number,headRefName,body`
    lists, split in two: those whose body names `head`, and only it, as the
    commit their plan read — current — and every other one, stale, since its
    plan read another commit of the default branch, or its body names none.
    Raises Refused where the listing is not such a list."""
    if not isinstance(listed, list):
        raise Refused("the open pull requests are no JSON list")
    current: list[int] = []
    stale: list[int] = []
    for each in listed:
        if not isinstance(each, dict):
            raise Refused("an open pull request is no JSON object")
        number, branch, body = each.get("number"), each.get("headRefName"), each.get("body")
        if not (isinstance(number, int) and isinstance(branch, str) and isinstance(body, str)):
            raise Refused(f"an open pull request lacks its number, branch or body: {each!r}")
        if branch.startswith(BRANCH_PREFIX):
            (current if plan_commits_named(body) == [head] else stale).append(number)
    return current, stale


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Refused(f"{path} cannot be read ({exc})") from exc


def _read_plan(path: Path) -> Mapping[str, Any]:
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Refused(f"the plan {path} cannot be read ({exc})") from exc
    if not isinstance(plan, dict):
        raise Refused(f"the plan {path} is no JSON object")
    return plan


def _read_text(path: Path, what: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise Refused(f"{what} {path} cannot be read ({exc})") from exc


# --- The command -------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "The branch and the description of the release pull request that "
            "`.github/workflows/release-pr.yml` opens."
        ),
    )
    commands = parser.add_subparsers(dest="command", required=True)
    branch = commands.add_parser(
        "branch", help=f"Print the branch to push the release to, reading {REMOTE}'s branches."
    )
    branch.add_argument("--version", required=True, help="The backbone version, or ''.")
    branch.add_argument("--run-id", required=True, help="The workflow run's id.")
    body = commands.add_parser("body", help="Print the pull request's description.")
    body.add_argument("--plan", required=True, type=Path, help="`pkit release plan --json`.")
    body.add_argument("--branch", required=True, help="The release branch.")
    body.add_argument(
        "--changelog", type=Path, default=Path(CHANGELOG), help=f"Default: {CHANGELOG}."
    )
    body.add_argument("--repository-url", help="The repository's web address, for the link.")
    body.add_argument("--trailer", required=True, help="The trailer line, last in the body.")
    trailer = commands.add_parser(
        "trailer", help="Print the trailer line `pkit release apply` printed."
    )
    trailer.add_argument(
        "--apply-output", required=True, type=Path, help="What `pkit release apply` printed."
    )
    opened = commands.add_parser(
        "open",
        help="Print the open release pull requests, as `current=` and `stale=` lines.",
    )
    opened.add_argument(
        "--prs", required=True, type=Path, help="`gh pr list --json number,headRefName,body`."
    )
    opened.add_argument("--head", required=True, help="The commit this run plans from.")
    left = commands.add_parser(
        "unpublished",
        help="Print the version of each release or candidate tag with no Release, a line each.",
    )
    left.add_argument("--tags", required=True, type=Path, help=f"`git ls-remote --tags {REMOTE}`.")
    left.add_argument(
        "--releases", required=True, type=Path, help="The tag of each Release, a line each."
    )
    args = parser.parse_args(argv)
    try:
        if args.command == "unpublished":
            released = set(_read_text(args.releases, "the Releases' tags").split())
            for version in unpublished(_read_text(args.tags, "the tags"), released):
                print(version)
        elif args.command == "branch":
            print(release_branch(args.version, args.run_id, remote_branches(Path.cwd())))
        elif args.command == "trailer":
            print(
                trailer_printed(
                    _read_text(args.apply_output, "the output of `pkit release apply`,")
                )
            )
        elif args.command == "open":
            current, stale = open_release_pull_requests(_read_json(args.prs), args.head)
            print(f"current={' '.join(str(n) for n in current)}")
            print(f"stale={' '.join(str(n) for n in stale)}")
        else:
            if [plan_commit_line(c) for c in plan_commits_named(args.trailer)] != [args.trailer]:
                raise Refused(f"{args.trailer!r} is not the trailer line alone")
            text = pull_request_body(
                _read_plan(args.plan),
                _read_text(args.changelog, "the changelog"),
                branch=args.branch,
                repository_url=args.repository_url,
                trailer=args.trailer,
            )
            sys.stdout.write(text)
    except Refused as exc:
        print(f"error: {exc}.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
