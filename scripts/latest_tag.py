"""Keep the tag `latest` on the newest release's commit (PRJ-004, #2052).

`uv tool install git+ssh://git@github.com/aleskalfas/project-kit.git@latest`
installs the newest release because this script keeps `latest` there. The
release-tag workflow (`.github/workflows/release-tag.yml`) runs it on every
push to `main`, after it cut any tag the push needed:

    python scripts/latest_tag.py --push

It reads `origin`'s tags (`git ls-remote --tags origin`), takes the highest
release tag, and makes `latest` point at that tag's commit:

- **Missing:** where `origin` has no `latest`, it creates it.
- **Lagging:** where `latest` points at another commit, it moves it.
- **Current:** where `latest` already points there, it pushes nothing. So a run
  that failed to move it is mended by the next push to `main`.

A release tag is `v<major>.<minor>.<patch>`, no part padded by a leading zero,
judged as `pkit upgrade` judges one (`upgrade._max_released_tag`); a test holds
the two equal. Pre-releases, dev releases and every other tag, `latest` itself
among them, are skipped. The script needs nothing but the standard library and
`git`, so the workflow runs it without installing the project.

`latest` is a lightweight tag on the commit itself. Its push is forced, since
git moves no tag without force, and leased on the value this run read: it goes
through only while `origin`'s `latest` is still that value, or still missing.
So a run that read an older state never moves `latest` back over a newer run's
move; it fails instead, and the next push mends it.

Only the workflow pushes: outside GitHub Actions (`GITHUB_ACTIONS` is not
`true`), `--push` refuses and pushes nothing. It guards against a run by hand;
it is not a boundary. Without `--push` it says what it would do and changes
nothing. Exit 0 when `latest` points at the newest release, or no release tag
exists; 1, saying why, when `git` fails or the push is refused.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

#: The tag this script keeps on the newest release's commit.
LATEST = "latest"

#: The remote whose tags are read and written.
REMOTE = "origin"

_REF = f"refs/tags/{LATEST}"

# A release tag: `v` and a release version, as `versioning.is_release_version`
# reads one — `major.minor.patch`, no pre-release, no part padded by a zero.
_RELEASE_TAG = re.compile(r"^v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


class Refused(Exception):
    """`git` failed, or the push was refused; nothing more is done."""


def release_key(tag: str) -> tuple[int, int, int] | None:
    """The version `tag` names, where it is a release tag; None otherwise."""
    match = _RELEASE_TAG.match(tag)
    if match is None:
        return None
    major, minor, patch = (int(part) for part in match.groups())
    return major, minor, patch


def newest_release(tags: Iterable[str]) -> str | None:
    """The release tag of the highest version among `tags`; None where none is."""
    keyed = [(key, tag) for tag in tags if (key := release_key(tag)) is not None]
    return max(keyed)[1] if keyed else None


@dataclass(frozen=True)
class Plan:
    """What a run read of `origin`, and what it does about it."""

    #: The newest release tag on `origin`, or None where it has none.
    release: str | None
    #: The commit that release tag points at.
    target: str | None
    #: The object `origin`'s `latest` names, as read: the push's lease.
    current: str | None
    #: The commit `origin`'s `latest` points at.
    current_commit: str | None

    @property
    def needed(self) -> bool:
        """Whether `latest` must be created or moved."""
        return self.target is not None and self.current_commit != self.target


def plan_for(ls_remote_output: str) -> Plan:
    """The plan for the tags `git ls-remote --tags` lists.

    Each line is `<sha>\\trefs/tags/<tag>`; an annotated tag adds a peel line,
    `<tag>^{}`, naming the commit it points at. A tag without one names the
    commit itself.
    """
    named: dict[str, str] = {}
    peeled: dict[str, str] = {}
    for line in ls_remote_output.splitlines():
        sha, _, ref = line.partition("\t")
        tag = ref.strip().removeprefix("refs/tags/")
        if tag == ref.strip():
            continue
        if tag.endswith("^{}"):
            peeled[tag.removesuffix("^{}")] = sha
        else:
            named[tag] = sha
    commits = {tag: peeled.get(tag, sha) for tag, sha in named.items()}
    release = newest_release(commits)
    return Plan(
        release=release,
        target=None if release is None else commits[release],
        current=named.get(LATEST),
        current_commit=commits.get(LATEST),
    )


def _git(repo: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args], cwd=repo, capture_output=True, text=True, check=False
        )
    except OSError as exc:
        raise Refused(f"`git` cannot be run ({exc})") from exc
    if completed.returncode != 0:
        said = completed.stderr.strip() or completed.stdout.strip()
        raise Refused(f"`git {' '.join(args)}` failed: {said}")
    return completed.stdout


def read(repo: Path) -> Plan:
    """The plan for `origin`'s tags, as the clone at `repo` reaches them."""
    return plan_for(_git(repo, "ls-remote", "--tags", REMOTE))


def apply(repo: Path, plan: Plan) -> str:
    """Push `latest` to the plan's target, leased on what the plan read. Returns
    what was done. Raises Refused where the push fails."""
    if plan.target is None or not plan.needed:
        raise ValueError("the plan moves nothing")
    lease = f"--force-with-lease={_REF}:{plan.current or ''}"
    _git(repo, "push", lease, REMOTE, f"{plan.target}:{_REF}")
    verb = "Created" if plan.current is None else "Moved"
    return f"{verb} `{LATEST}` on {REMOTE}: it points at {plan.release} ({plan.target[:12]})."


def run(repo: Path, *, push: bool) -> int:
    """Read `origin`'s tags and, with `push`, point `latest` at the newest release."""
    try:
        found = read(repo)
        if found.release is None or found.target is None:
            print(f"{REMOTE} has no release tag: nothing for `{LATEST}` to point at.")
            return 0
        if not found.needed:
            print(
                f"`{LATEST}` already points at {found.release} ({found.target[:12]}): "
                "nothing to do."
            )
            return 0
        if not push:
            verb = "create" if found.current is None else "move"
            print(
                f"Would {verb} `{LATEST}` on {REMOTE} to {found.release} ({found.target[:12]}). "
                "Only the release-tag workflow pushes it (`--push`)."
            )
            return 0
        print(apply(repo, found))
    except Refused as exc:
        print(f"error: {exc}. `{LATEST}` was left as it was.", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            f"Point the tag `{LATEST}` at the commit of {REMOTE}'s highest release tag. "
            "Only the workflow `.github/workflows/release-tag.yml` pushes it; outside "
            "GitHub Actions `--push` refuses."
        ),
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help=f"Create or move `{LATEST}` on {REMOTE}, force-pushed with a lease.",
    )
    args = parser.parse_args(argv)
    if args.push and os.environ.get("GITHUB_ACTIONS") != "true":
        print(
            f"error: only the workflow `.github/workflows/release-tag.yml` pushes `{LATEST}`, "
            "and this is no GitHub Actions run (`GITHUB_ACTIONS` is not `true`); nothing was "
            "pushed. Run it without `--push` to see what it would do.",
            file=sys.stderr,
        )
        return 1
    return run(Path.cwd(), push=args.push)


if __name__ == "__main__":
    sys.exit(main())
