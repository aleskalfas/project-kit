"""The branch and the description of the release pull request (#2862).

The release-pr workflow (`.github/workflows/release-pr.yml`) runs `pkit release
plan --json`, and then this script for the branch it pushes the release to. On
that branch it runs `pkit release apply --yes`, and this script again for the
pull request's description, before it pushes:

    uv run python scripts/release_pr.py branch --version <version> --run-id <run id>
    uv run python scripts/release_pr.py body --plan <plan> --branch <branch> --repository-url <url>

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

It needs nothing but the standard library and `git`. Exit 0 with the branch's
name or the description on standard output; 1, saying why, when `git` fails, the
plan cannot be read, or the description is too long without the section.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Collection, Mapping
from pathlib import Path
from typing import Any

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
    plan: Mapping[str, Any], changelog: str, *, branch: str, repository_url: str | None
) -> str:
    """The release pull request's description: the bumps, the warnings, and the
    changelog's new section where the whole fits `PULL_REQUEST_BODY_LIMIT`, or
    the pointer to it on `branch` where it does not. Raises Refused where even
    the description without the section does not fit."""
    head = _head(plan)
    section = changelog_section(changelog)
    whole = head + section
    if len(whole) <= PULL_REQUEST_BODY_LIMIT:
        return whole
    short = head + changelog_pointer(len(whole), branch=branch, repository_url=repository_url)
    if len(short) > PULL_REQUEST_BODY_LIMIT:
        raise Refused(
            f"the description is {len(short):,} characters without the changelog's section, "
            f"past the {PULL_REQUEST_BODY_LIMIT:,} GitHub keeps in a pull request's description"
        )
    return short


def _read_plan(path: Path) -> Mapping[str, Any]:
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Refused(f"the plan {path} cannot be read ({exc})") from exc
    if not isinstance(plan, dict):
        raise Refused(f"the plan {path} is no JSON object")
    return plan


def _read_changelog(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise Refused(f"the changelog {path} cannot be read ({exc})") from exc


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
    args = parser.parse_args(argv)
    try:
        if args.command == "branch":
            print(release_branch(args.version, args.run_id, remote_branches(Path.cwd())))
        else:
            text = pull_request_body(
                _read_plan(args.plan),
                _read_changelog(args.changelog),
                branch=args.branch,
                repository_url=args.repository_url,
            )
            sys.stdout.write(text)
    except Refused as exc:
        print(f"error: {exc}.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
