"""A release candidate, cut from a commit that has taken in the default branch's head.

`pkit release plan --pre` and `apply --pre` plan a candidate from the commit they run
at: the versions it records and the changesets pending in its tree (ADR-092 point 2).
The plan is the one a final release would make there, at release versions, so every
check reads it as it reads a final release's, and the suffix `rcN` is added only where
the cut writes (ADR-089 point 1). `plan_candidate` refuses a cut before anything is
written:

- outside the methodology's source repository, the one the marker test finds, and
  where the release would move no backbone version, since a candidate is a backbone
  tag (ADR-089 point 2)
- where the working tree differs from the commit, since the plan would then not be
  the commit's
- where the default branch's head, read from the remote, is not in the commit's
  history (ADR-092 point 2)
- where a migration script would ship stranded (ADR-092 point 8)
- where the remote's tags cannot be read, since the cut's number counts them: one
  past the highest number any candidate tag on the remote carries, whatever its
  version, and 1 where there is none (ADR-092 point 3)

`cut_candidate` writes the candidate through `release.apply_candidate`, which raises
no floor and consumes no changeset (PRJ-002 D4 and D5). It records the cut's base in
the candidate's tree, at `BASE_PATH`: the commit the cut is made from, and the
version the backbone and each component record there (ADR-092 point 9). It commits
the writes on no branch, and with `tag` tags that commit, which the tag alone then
holds (ADR-089 points 1 and 9). It pushes nothing: the tag is pushed once the wheel
built from the commit is checked.

Each check is an interlock against a mistake, not a defence against a branch that
edits this code, since a run on that branch runs it (ADR-092 point 10).
"""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path, PurePosixPath
from typing import cast

import click

from project_kit import default_branch, remote_refs
from project_kit.changesets import BACKBONE, discover_components
from project_kit.release import ReleasePlan, apply_candidate, compute_release
from project_kit.router import is_source_checkout
from project_kit.stranded_migrations import refuse_stranded_scripts

#: The suffix every version a candidate moves takes, before its number (ADR-089
#: point 1).
SUFFIX = "rc"

#: Where a candidate's tree records its cut's base, from the repository root: in the
#: package, so the wheel built from the candidate's commit carries it (ADR-092 point 9).
BASE_PATH = PurePosixPath("src/project_kit/candidate_base.json")

#: A candidate tag's full reference on the remote, `refs/tags/v<X.Y.Z>rc<N>`: group 1
#: is its number. A `withdrawn/` tag's reference never matches it.
_CANDIDATE_TAG_RE = re.compile(r"refs/tags/v\d+\.\d+\.\d+rc(\d+)")

#: How many of the paths that differ a refusal names.
_SHOWN = 10

_SHORT = 12


@dataclass(frozen=True)
class Base:
    """A cut's base: the commit it is made from, and the version the backbone and each
    component, by name, record there (ADR-092 point 9)."""

    commit: str
    backbone: str
    components: Mapping[str, str]

    def text(self) -> str:
        """The base as its file holds it: JSON, the components in name order."""
        document = {
            "commit": self.commit,
            "backbone": self.backbone,
            "components": dict(sorted(self.components.items())),
        }
        return json.dumps(document, indent=2) + "\n"


def parse_base(text: str) -> Base:
    """The base a candidate's base file records. Raises `ValueError` where `text` is
    not one."""
    try:
        document = cast(object, json.loads(text))
    except json.JSONDecodeError as exc:
        raise ValueError(f"the base is no JSON ({exc})") from exc
    if not isinstance(document, dict):
        raise ValueError("the base is no JSON object")
    fields = cast(dict[str, object], document)
    commit, backbone, listed = (
        fields.get("commit"),
        fields.get("backbone"),
        fields.get("components"),
    )
    if not (isinstance(commit, str) and isinstance(backbone, str) and isinstance(listed, dict)):
        raise ValueError("the base lacks its commit, its backbone's version or its components")
    components: dict[str, str] = {}
    for name, version in cast(dict[object, object], listed).items():
        if not (isinstance(name, str) and isinstance(version, str)):
            raise ValueError(f"the base records no version for the component {name!r}")
        components[name] = version
    return Base(commit, backbone, components)


@dataclass(frozen=True)
class Candidate:
    """A planned cut: the release's plan at release versions, which every check reads,
    the cut's number, and its base."""

    plan: ReleasePlan
    number: int
    base: Base

    def suffixed(self, version: str) -> str:
        """`version`, a release version the plan moves to, as the candidate writes it."""
        return f"{version}{SUFFIX}{self.number}"

    @property
    def version(self) -> str:
        """The candidate's version: the backbone's, with the suffix."""
        backbone = self.plan.backbone
        assert backbone is not None  # `plan_candidate` refuses a plan that moves none
        return self.suffixed(backbone.new_version)

    @property
    def tag(self) -> str:
        return f"v{self.version}"

    def written(self) -> ReleasePlan:
        """The plan as the cut writes it: each version it moves with the suffix, no
        floor raised and no changeset consumed (PRJ-002 D4 and D5)."""
        releases = [
            replace(
                rel,
                new_version=self.suffixed(rel.new_version),
                floor_raise=None,
                capability_floors=(),
            )
            for rel in self.plan.releases
        ]
        return replace(self.plan, releases=releases, consumed=[])


def plan_candidate(source_kit: Path) -> Candidate:
    """The candidate a cut at HEAD would write. Refuses, before anything is written,
    each cut the module docstring names."""
    repo_root = source_kit.parent
    if not is_source_checkout(repo_root):
        raise _refused(
            "a candidate is cut only in the methodology's source repository (ADR-089 point "
            "2), and this project is not it."
        )
    head = _head(repo_root)
    _refuse_a_changed_tree(repo_root, head)
    _refuse_unless_taken_in(repo_root, head)
    refuse_stranded_scripts(repo_root)
    plan = compute_release(source_kit)
    if plan.backbone is None:
        raise _refused(
            "the release would move no backbone version, so a candidate would have no tag "
            "to install (ADR-089 point 2)."
        )
    return Candidate(plan, next_number(repo_root), base_at(source_kit, head))


def next_number(repo_root: Path) -> int:
    """One past the highest number any candidate tag on the remote carries, whatever its
    version, and 1 where there is none (ADR-092 point 3). Refuses where the remote's
    tags cannot be read."""
    try:
        tags = remote_refs.tags(repo_root)
    except remote_refs.Unread as exc:
        raise _refused(f"the cut cannot be numbered (ADR-092 point 3): {exc}") from None
    numbers = [int(match.group(1)) for ref in tags if (match := _CANDIDATE_TAG_RE.fullmatch(ref))]
    return max(numbers, default=0) + 1


def base_at(source_kit: Path, commit: str) -> Base:
    """The base of a cut made from `commit`, whose tree `source_kit` holds: the version
    the backbone and each component record there."""
    backbone = ""
    components: dict[str, str] = {}
    for component in discover_components(source_kit):
        if component.name == BACKBONE:
            backbone = component.version
        else:
            components[component.name] = component.version
    return Base(commit, backbone, components)


def cut_candidate(
    source_kit: Path,
    candidate: Candidate,
    *,
    tag: bool,
    broaden: bool = True,
    today: date | None = None,
) -> str:
    """Write `candidate`, record its base, and commit the writes on no branch, tagging
    that commit `v<candidate>` where `tag`. Returns the commit. Refuses, before
    anything is written, a `tag` this clone holds already."""
    repo_root = source_kit.parent
    if tag and _git(repo_root, "tag", "--list", candidate.tag).strip():
        raise _refused(
            f"this clone holds the tag {candidate.tag} already, though {remote_refs.REMOTE} "
            "does not: an earlier cut here left it unpushed. A candidate's tag is never "
            "moved or deleted once pushed (PRJ-016 point 5); decide what becomes of this "
            "one, and run again."
        )
    apply_candidate(source_kit, candidate.plan, candidate.written(), broaden=broaden, today=today)
    base = repo_root / BASE_PATH
    base.parent.mkdir(parents=True, exist_ok=True)
    base.write_text(candidate.base.text(), encoding="utf-8")
    click.echo(f"Recorded the cut's base in {BASE_PATH}: {candidate.base.commit[:_SHORT]}")

    # The tree held nothing but the commit before the writes (`plan_candidate`), so
    # every change it holds now is the cut's.
    _git(repo_root, "switch", "--quiet", "--detach")
    _git(repo_root, "add", "--all")
    subject = f"chore(release): {candidate.tag}"
    _git(
        repo_root,
        "commit",
        "--quiet",
        "-m",
        subject,
        "-m",
        f"A release candidate, cut from {candidate.base.commit} (ADR-092 point 2).",
    )
    commit = _git(repo_root, "rev-parse", "HEAD").strip()
    click.echo(f"Committed {candidate.tag} as {commit[:_SHORT]}, on no branch.")
    if tag:
        _git(repo_root, "tag", "-a", candidate.tag, "-m", f"{candidate.tag}\n\n{subject}", commit)
        click.echo(f"Tagged {commit[:_SHORT]} as {candidate.tag}.")
    return commit


def current_branch(repo_root: Path) -> str | None:
    """The branch HEAD is on, or None where HEAD is detached."""
    completed = subprocess.run(
        ["git", "symbolic-ref", "--quiet", "--short", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    branch = completed.stdout.strip()
    return branch if completed.returncode == 0 and branch else None


def _head(repo_root: Path) -> str:
    head = default_branch.head(repo_root)
    if head.commit is None:
        raise _refused(f"{head.problem or 'HEAD names no commit yet'}, so there is no cut.")
    return head.commit


def _refuse_a_changed_tree(repo_root: Path, head: str) -> None:
    """Refuse where the working tree differs from `head`, by a change to a tracked file
    or a file git does not track or ignore."""
    listed = _git(repo_root, "status", "--porcelain", "--untracked-files=all").splitlines()
    if not listed:
        return
    lines = [f"  {line}" for line in listed[:_SHOWN]]
    if len(listed) > _SHOWN:
        lines.append(f"  and {len(listed) - _SHOWN} more")
    shown = "\n".join(lines)
    raise click.ClickException(
        f"refusing to cut a candidate: the working tree differs from {head[:_SHORT]}, the "
        "commit the cut is planned from, so the plan would not be that commit's (ADR-092 "
        f"point 2). Commit each change, or set it aside, and run again. Nothing was "
        f"written:\n{shown}"
    )


def _refuse_unless_taken_in(repo_root: Path, head: str) -> None:
    """Refuse where the default branch's head, read from the remote, is not in `head`'s
    history (ADR-092 point 2)."""
    name, _, warning = default_branch.declared(repo_root)
    if warning is not None:
        click.echo(f"warning: {warning}", err=True)
    try:
        tip = remote_refs.branch_head(repo_root, name)
    except remote_refs.Unread as exc:
        raise _refused(
            f"whether {head[:_SHORT]} has taken in the default branch's head cannot be told "
            f"(ADR-092 point 2): {exc}"
        ) from None
    if tip is None:
        raise _refused(
            f"{remote_refs.REMOTE} has no branch {name}, the default branch, so whether "
            f"{head[:_SHORT]} has taken in its head cannot be told (ADR-092 point 2)."
        )
    if _is_ancestor(repo_root, tip, head):
        return
    where = f"the head of {name} on {remote_refs.REMOTE}, {tip[:_SHORT]},"
    planned = f"{head[:_SHORT]}, the commit the cut is planned from (ADR-092 point 2)"
    if not _holds(repo_root, tip):
        raise _refused(
            f"{where} is a commit this clone does not hold, so it is not in the history of "
            f"{planned}. Fetch {name}, merge it into this branch, and run again."
        )
    if default_branch.is_shallow(repo_root):
        raise _refused(
            f"{where} is not in the history of {planned}, as far as this clone sees: the "
            "clone is shallow, so its history may stop before it. Fetch the whole history "
            "(`git fetch --unshallow`), and run again."
        )
    raise _refused(
        f"{where} is not in the history of {planned}. Merge {remote_refs.REMOTE}/{name} into "
        "this branch, and run again."
    )


def _is_ancestor(repo_root: Path, ancestor: str, commit: str) -> bool:
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, commit],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode == 0


def _holds(repo_root: Path, commit: str) -> bool:
    completed = subprocess.run(
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.returncode == 0


def _git(repo_root: Path, *args: str) -> str:
    """`git <args>`'s output; raises `click.ClickException` where it fails."""
    try:
        completed = subprocess.run(
            ["git", *args], cwd=repo_root, capture_output=True, text=True, check=False
        )
    except OSError as exc:
        raise click.ClickException(f"`git` could not be run ({exc}).") from exc
    if completed.returncode != 0:
        said = completed.stderr.strip() or f"exit status {completed.returncode}"
        raise click.ClickException(f"`git {' '.join(args)}` failed: {said}")
    return completed.stdout


def _refused(reason: str) -> click.ClickException:
    return click.ClickException(f"refusing to cut a candidate: {reason} Nothing was written.")
