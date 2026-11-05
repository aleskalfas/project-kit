"""Keep the tag `latest` on the highest release's commit (PRJ-004, #2052).

`uv tool install git+ssh://git@github.com/aleskalfas/project-kit.git@latest`
installs the highest release because this script keeps `latest` there. The
release-tag workflow (`.github/workflows/release-tag.yml`) runs it on every
push to `main`, after it cut any tag the push needed:

    python3 scripts/latest_tag.py --push

It reads `origin`'s tags and branches (`git ls-remote --tags --heads origin`),
takes the highest release tag, and makes `latest` point at that tag's commit:

- **Missing:** where `origin` has no `latest`, it creates it.
- **Lagging:** where `latest` points at another commit, it moves it.
- **Current:** where `latest` already points there, it pushes nothing. So a run
  that failed to move it is mended by the next push to `main`.
- **Shadowed:** where `origin` has a branch named `latest`, it refuses and
  pushes nothing. uv can take a branch before a tag of the same name, so every
  `@latest` install would get that branch's head.

A release tag is `v<major>.<minor>.<patch>` in ASCII digits, no part padded by a
leading zero, as `versioning.is_release_version` reads a release version.
Pre-releases, dev releases and every other tag, `latest` itself among them, are
skipped. This script reads a ref name as git prints it, untrimmed, so a name
that only looks like a release tag is no release tag.

`pkit upgrade`'s `_max_released_tag` finds the highest release too, and a test
holds the two equal on a corpus of tags. They judge alike every ref name free
of whitespace, which is every tag the release step cuts. They are not alike in
trimming: `_max_released_tag` trims a name and splits lines at Unicode line
breaks. So a name git accepts with Unicode whitespace in it, such as a trailing
no-break space, counts as a release there and not here. The script needs
nothing but the standard library and `git`, so the workflow runs it on the
runner's own `python3` without installing the project.

`latest` is a lightweight tag on the commit itself. Its push is forced, since
git moves no tag without force, and leased on the value this run read: it goes
through only while `origin`'s `latest` is still that value, or still missing.
So a run that read an older state never moves `latest` back over a newer run's
move. Where the push fails, the run reads `origin` again. Where `latest` already
points at the target, as another run or the failed push itself left it, the run
passes; otherwise it fails, and the next push mends it.

Only the workflow pushes: outside GitHub Actions (`GITHUB_ACTIONS` is not
`true`), `--push` refuses and pushes nothing. It guards against a run by hand;
it is not a boundary, and nothing on the host stops another writer of `latest`.
Without `--push` it says what it would do and changes nothing. Exit 0 when
`latest` points at the highest release, or no release tag exists; 1, saying
why, when `git` fails, a branch shadows the tag, or the push fails and `latest`
points elsewhere.
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

#: The tag this script keeps on the highest release's commit.
LATEST = "latest"

#: The remote whose tags are read and written.
REMOTE = "origin"

_TAG_REF = f"refs/tags/{LATEST}"
_BRANCH_REF = f"refs/heads/{LATEST}"

# A release tag: `v` and a release version, as `versioning.is_release_version`
# reads one — `major.minor.patch`, no pre-release, no part padded by a zero —
# in ASCII digits alone.
_RELEASE_TAG = re.compile(r"v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", re.ASCII)

# An object id as git prints it: SHA-1 or SHA-256, in lowercase hex.
_OBJECT_ID = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}", re.ASCII)


class Refused(Exception):
    """`git` failed, a branch shadows the tag, or the push was refused; nothing
    more is done."""


def release_key(tag: str) -> tuple[int, int, int] | None:
    """The version `tag` names, where it is a release tag; None otherwise."""
    match = _RELEASE_TAG.fullmatch(tag)
    if match is None:
        return None
    major, minor, patch = (int(part) for part in match.groups())
    return major, minor, patch


def highest_release(tags: Iterable[str]) -> str | None:
    """The release tag of the highest version among `tags`; None where none is."""
    keyed = [(key, tag) for tag in tags if (key := release_key(tag)) is not None]
    return max(keyed)[1] if keyed else None


@dataclass(frozen=True)
class Plan:
    """What a run read of `origin`, and what it does about it."""

    #: The highest release tag on `origin`, or None where it has none.
    release: str | None
    #: The commit that release tag points at.
    target: str | None
    #: The object `origin`'s `latest` names, as read: the push's lease.
    current: str | None
    #: The commit `origin`'s `latest` points at.
    current_commit: str | None
    #: Whether `origin` has a branch named `latest`, which uv can take first.
    shadowed: bool = False

    @property
    def needed(self) -> bool:
        """Whether `latest` must be created or moved."""
        return self.target is not None and self.current_commit != self.target


def plan_for(ls_remote_output: str) -> Plan:
    """The plan for the refs `git ls-remote --tags --heads` lists.

    Each line is `<object id>\\t<ref>`. An annotated tag adds a peel line,
    `refs/tags/<tag>^{}`, naming the commit it points at; a tag without one
    names the commit itself. Lines are split on a newline alone and a ref is
    never trimmed, and a line whose object id is no object id is skipped.
    """
    named: dict[str, str] = {}
    peeled: dict[str, str] = {}
    shadowed = False
    for line in ls_remote_output.split("\n"):
        oid, tab, ref = line.removesuffix("\r").partition("\t")
        if not tab or _OBJECT_ID.fullmatch(oid) is None:
            continue
        if ref == _BRANCH_REF:
            shadowed = True
        elif ref.startswith("refs/tags/"):
            tag = ref.removeprefix("refs/tags/")
            if tag.endswith("^{}"):
                peeled[tag.removesuffix("^{}")] = oid
            else:
                named[tag] = oid
    commits = {tag: peeled.get(tag, oid) for tag, oid in named.items()}
    release = highest_release(commits)
    return Plan(
        release=release,
        target=None if release is None else commits[release],
        current=named.get(LATEST),
        current_commit=commits.get(LATEST),
        shadowed=shadowed,
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
    """The plan for `origin`'s tags and branches, as the clone at `repo` reaches them."""
    return plan_for(_git(repo, "ls-remote", "--tags", "--heads", REMOTE))


def apply(repo: Path, plan: Plan) -> str:
    """Push `latest` to the plan's target, leased on what the plan read. Returns
    what was done. Where the push fails, reads `origin` again, and returns where
    `latest` already points at the target: another run put it there, or the
    failed push reached `origin`. Raises Refused otherwise."""
    if plan.target is None or not plan.needed:
        raise ValueError("the plan moves nothing")
    lease = f"--force-with-lease={_TAG_REF}:{plan.current or ''}"
    try:
        _git(repo, "push", lease, REMOTE, f"{plan.target}:{_TAG_REF}")
    except Refused:
        if not _points_at(repo, plan.target):
            raise
        return (
            f"`{LATEST}` on {REMOTE} already points at {plan.release} ({plan.target[:12]}), "
            "though this run's push failed."
        )
    verb = "Created" if plan.current is None else "Moved"
    return f"{verb} `{LATEST}` on {REMOTE}: it points at {plan.release} ({plan.target[:12]})."


def _points_at(repo: Path, target: str) -> bool:
    """Whether `origin`'s `latest` points at `target` now, with no branch shadowing
    it. False where `origin` cannot be read."""
    try:
        again = read(repo)
    except Refused:
        return False
    return again.current_commit == target and not again.shadowed


def run(repo: Path, *, push: bool) -> int:
    """Read `origin`'s refs and, with `push`, point `latest` at the highest release."""
    try:
        found = read(repo)
        if found.shadowed:
            raise Refused(
                f"{REMOTE} has a branch named `{LATEST}`, which uv can take before the tag, so "
                f"every `@{LATEST}` install would get that branch's head. Delete the branch"
            )
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
