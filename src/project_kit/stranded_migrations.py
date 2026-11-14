"""No release ships a stranded migration script (ADR-092 point 8).

A tier's *fixed version*, in a project, is the newest version of that tier whose
migration scripts are fixed: those who take that version have received them, so a
script added since to its folder, or to one below it, runs for none of them.
`pkit release plan` and `apply` call `refuse_stranded_scripts` before they write
anything, and it refuses where a tier holds such a script: one in a folder at or
below the tier's fixed version that the fixed version's commit did not hold, at
its path or under another name in its folder with the same content. That is the
judgement `pkit migrations check-diff` makes against a base's tip
(`migrations.released_targets`), made here against that commit, so the two tell a
script, its tier and a rename alike. A script the project receives from elsewhere,
by sync or by a capability's install or upgrade, is passed by: the ownership
predicate `is_synced_copy` says which.

Where a version's scripts are fixed follows from how those who take it receive it,
and the marker test tells the two kinds of project apart (`router.is_source_checkout`,
ADR-059 point 3):

- **The methodology's source repository** (`_fixed_by_tags`): projects take a
  version through the tag that carries it (PRJ-004). The fixed version is the one
  the tier records at the newest final release tag, `v<X.Y.Z>`, read from the
  remote's tags, and its commit is that of the first final release tag that carries
  it. A candidate's tag, a `withdrawn/` tag and `latest` count for none.
- **Every other project** (`_fixed_by_history`): those who use its components pin
  a ref on its default branch, so they take a version at the first commit that
  records it. The fixed version is the one the default branch's head records, as
  `check-diff` reads it, and its commit is the first of the default branch's
  first-parent history that records it.

Only the release step writes a tier's version, raising it (PRJ-002 D3), so each
walk goes back from the newest tag, or the newest commit, only while the version
stays the same.

No answer is never a pass. Where the guard cannot read the remote's tags, a tag's
commit, the default branch, or the whole of its history, as in a shallow clone
(ADR-081 point 6), it refuses. It reads none of them for a project whose tiers hold
no script of their own.

Each script it names is told a folder above the version the default branch records
for its tier, found as `check-diff` finds one (`migrations.migration_target`), so
the move passes both.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import click
from packaging.version import Version

from project_kit import default_branch, lifecycle_ownership, migrations, remote_refs, working_tree
from project_kit.friction_git import SHORT, BlobReader, CommitTree, commit_of, run_git
from project_kit.router import is_source_checkout
from project_kit.versioning import is_release_version

#: The remote whose tags are read: the one `pkit version tag --push` pushes a tag to.
REMOTE = remote_refs.REMOTE

#: How the remote lists a final release tag's reference: `refs/tags/v<X.Y.Z>`.
_FINAL_TAG_PREFIX = f"{remote_refs.TAG_PREFIX}v"

#: What a refusal says of the scripts it names.
_STRANDED = (
    "a migration script sits in a folder at or below its tier's fixed version, which no "
    "project that took that version runs"
)

#: A tier: the backbone, or an adapter or a capability by its name.
TierKey = tuple[migrations.Tier, str | None]


@dataclass(frozen=True)
class Fixed:
    """Where a tier's scripts are fixed: its fixed version, the commit that fixed it,
    and how a line names that commit."""

    version: str
    commit: str
    named: str


@dataclass(frozen=True)
class StrandedScript:
    """A migration script a release would ship stranded; `line` names the folder to
    move it to."""

    path: str
    tier: migrations.Tier
    component: str | None
    line: str


def refuse_stranded_scripts(target_root: Path) -> None:
    """Refuse, naming each, where the project holds a stranded migration script, and
    where it cannot tell whether it does (`stranded_scripts`)."""
    found = stranded_scripts(target_root)
    if not found:
        return
    lines = "\n".join(f"  {script.line}" for script in found)
    raise click.ClickException(
        f"refusing to release: {_STRANDED} (ADR-092 point 8). Nothing was written:\n{lines}"
    )


def stranded_scripts(target_root: Path) -> tuple[StrandedScript, ...]:
    """Each migration script the working tree holds that the project's release would
    ship stranded, by path. Raises a `click.ClickException` where whether one is
    stranded cannot be told."""
    held = _scripts_by_tier(target_root)
    if not held:
        return ()
    branch: default_branch.DefaultBranch | None = None
    if is_source_checkout(target_root):
        fixed = _fixed_by_tags(target_root, held)
    else:
        branch = _default_branch(target_root)
        fixed = _fixed_by_history(target_root, held, branch)
    judged: list[tuple[migrations.ReleasedTarget, Fixed]] = []
    for key, paths in held.items():
        where = fixed.get(key)
        if where is None:
            continue
        found = migrations.released_targets(target_root, paths, base=where.named, tip=where.commit)
        judged.extend((target, where) for target in found)
    if not judged:
        return ()
    return _with_moves(target_root, judged, branch or _default_branch(target_root))


def _scripts_by_tier(target_root: Path) -> dict[TierKey, list[str]]:
    """The migration scripts the working tree holds, by tier, each a path from the
    project root, less those the project receives from elsewhere."""
    ownership = lifecycle_ownership.load_ownership(target_root)
    held: dict[TierKey, list[str]] = {}
    for rel in working_tree.working_tree(target_root).files():
        key = migrations.script_tier(rel)
        if key is None:
            continue
        if ownership is not None and ownership.is_synced_copy(target_root, rel):
            continue
        held.setdefault(key, []).append(rel)
    return held


# --- the methodology's source repository: fixed by the final release tags -------------------


def _fixed_by_tags(target_root: Path, tiers: Iterable[TierKey]) -> dict[TierKey, Fixed]:
    """Each tier's fixed version, at the newest final release tag the remote holds, and
    the first final release tag that carries it. A tier the newest tag records no
    version for has none, and nor does any tier where the remote holds no final tag."""
    tags = _final_tags(target_root)
    if not tags:
        return {}
    newest_name, newest_commit = tags[0]
    held: set[str] = set()
    _refuse_unheld(target_root, newest_name, newest_commit, held)
    reader = BlobReader(target_root)
    try:
        fixed: dict[TierKey, Fixed] = {}
        for key in tiers:
            version = _version_at(reader, key, newest_commit, f"the tag {newest_name}")
            if version is None:
                continue
            first_name, first_commit = newest_name, newest_commit
            for name, commit in tags[1:]:
                _refuse_unheld(target_root, name, commit, held)
                if _earlier_version_at(reader, key, commit) != version:
                    break
                first_name, first_commit = name, commit
            fixed[key] = Fixed(
                version, first_commit, f"the tag {first_name} ({first_commit[:SHORT]})"
            )
        return fixed
    finally:
        reader.close()


def _final_tags(target_root: Path) -> list[tuple[str, str]]:
    """Each final release tag the remote holds, `v<X.Y.Z>`, with the commit it names,
    the newest first. Refuses where the remote's tags cannot be read."""
    try:
        tags = remote_refs.tags(target_root)
    except remote_refs.Unread as exc:
        raise _cannot_tell(str(exc)) from None
    finals = [
        (ref.removeprefix(remote_refs.TAG_PREFIX), commit)
        for ref, commit in tags.items()
        if ref.startswith(_FINAL_TAG_PREFIX)
        and is_release_version(ref.removeprefix(_FINAL_TAG_PREFIX))
    ]
    return sorted(finals, key=lambda tag: Version(tag[0][1:]), reverse=True)


def _refuse_unheld(target_root: Path, name: str, commit: str, held: set[str]) -> None:
    """Refuse where this clone does not hold the commit the remote's tag `name` names;
    `held` keeps the commits found here already."""
    if commit in held:
        return
    if commit_of(target_root, commit) is None:
        raise _cannot_tell(
            f"the remote's tag {name} names {commit[:SHORT]}, a commit this clone does not "
            f"hold. Fetch the tags (`git fetch --tags {REMOTE}`), and run again."
        )
    held.add(commit)


# --- every other project: fixed by the default branch's history ----------------------------


def _default_branch(target_root: Path) -> default_branch.DefaultBranch:
    """The default branch, read as a standing value: no base reaches the release, so
    `$PKIT_CHECK_BASE` does not either (COR-054 point 3). Refuses where it names no
    commit and has history to read."""
    branch = default_branch.resolve(target_root, standing=True)
    for said in branch.warnings:
        click.echo(f"warning: {said}", err=True)
    if branch.commit is None and not branch.unborn:
        raise _cannot_tell(
            branch.problem or f"the default branch {branch.name!r} resolves to no commit here."
        )
    return branch


def _fixed_by_history(
    target_root: Path, tiers: Iterable[TierKey], branch: default_branch.DefaultBranch
) -> dict[TierKey, Fixed]:
    """Each tier's fixed version, at the default branch's head, and the first commit of
    the branch's first-parent history that records it. A branch with no commit yet,
    and a tier its head records no version for, have none. Refuses in a shallow clone,
    whose history may stop before that commit."""
    if branch.commit is None or branch.ref is None:
        return {}
    if default_branch.is_shallow(target_root):
        raise _cannot_tell(
            "this clone is shallow, so the first commit of the default branch's history that "
            "records a tier's version may not be here. Fetch the whole history (`git fetch "
            "--unshallow`), and run again."
        )
    head, ref = branch.commit, branch.ref
    reader = BlobReader(target_root)
    try:
        fixed: dict[TierKey, Fixed] = {}
        for key in tiers:
            version = _version_at(reader, key, head, ref)
            if version is None:
                continue
            cell = migrations.version_cell(*key)
            changed = (
                run_git(target_root, "log", "--first-parent", "--format=%H", head, "--", cell)
                .stdout.decode()
                .split()
            )
            first = changed[0] if changed else head
            for commit in changed[1:]:
                if _earlier_version_at(reader, key, commit) != version:
                    break
                first = commit
            fixed[key] = Fixed(
                version,
                first,
                f"{first[:SHORT]}, the first commit of {ref}'s first-parent history that "
                f"records {version}",
            )
        return fixed
    finally:
        reader.close()


# --- reading a tier's version -------------------------------------------------------------


def _version_at(reader: BlobReader, key: TierKey, commit: str, where: str) -> str | None:
    """The version `commit` records for the tier, or `None` where it records none.
    Refuses where it records none in `major.minor.patch` form, saying `where`."""
    try:
        return _recorded(reader, key, commit)
    except click.ClickException as exc:
        raise _cannot_tell(f"at {where}, {exc.message}") from None


def _earlier_version_at(reader: BlobReader, key: TierKey, commit: str) -> str | None:
    """The version an earlier `commit` records for the tier, or `None` where it records
    none it can be read as: either way, not the version a later commit records."""
    try:
        return _recorded(reader, key, commit)
    except click.ClickException:
        return None


def _recorded(reader: BlobReader, key: TierKey, commit: str) -> str | None:
    tier, component = key
    return migrations.recorded_version(tier, component, lambda rel: reader.read(commit, rel))


# --- the refusal -----------------------------------------------------------------------------


def _with_moves(
    target_root: Path,
    judged: Sequence[tuple[migrations.ReleasedTarget, Fixed]],
    branch: default_branch.DefaultBranch,
) -> tuple[StrandedScript, ...]:
    """Each stranded script with its line: the folder to move it to, past the version the
    default branch records for its tier, as `check-diff` names one."""
    if branch.commit is None or branch.ref is None:
        raise _unnamed(f"the default branch {branch.name!r} has no commit yet.")
    tree = CommitTree(target_root, branch.commit)
    files = tree.files()

    def read(rel: str) -> bytes | None:
        return tree.read_bytes([rel])[rel]

    recorded: dict[TierKey, str | None] = {}
    keys: set[TierKey] = {(target.tier, target.component) for target, _ in judged}
    for key in keys:
        try:
            recorded[key] = migrations.recorded_version(key[0], key[1], read)
        except click.ClickException as exc:
            raise _unnamed(f"at {branch.ref}, {exc.message}") from None
    found: list[StrandedScript] = []
    for target, fixed in judged:
        tier, component = target.tier, target.component
        subject = migrations.tier_subject(tier, component)
        script = PurePosixPath(target.path)
        upcoming = migrations.migration_target(
            subject,
            recorded[(tier, component)] or fixed.version,
            branch.ref,
            folders=migrations.version_folders(files, script.parent.parent.as_posix()),
        )
        label = tier + (f":{component}" if component else "")
        line = (
            f"[{label}] {target.path}: targets {script.parent.name}, at or below {subject} "
            f"{fixed.version}, whose scripts are fixed at {fixed.named}. That commit does not "
            f"hold the script, so no project that took {fixed.version} runs it. Move it to "
            f"{upcoming.version}/ or a later folder."
        )
        found.append(StrandedScript(target.path, tier, component, line))
    return tuple(sorted(found, key=lambda script: script.path))


def _cannot_tell(reason: str) -> click.ClickException:
    """The refusal where whether a script is stranded cannot be told, with why."""
    return click.ClickException(
        "refusing to release: whether a migration script sits in a folder at or below its "
        f"tier's fixed version cannot be told (ADR-092 point 8): {reason} Nothing was written."
    )


def _unnamed(reason: str) -> click.ClickException:
    """The refusal where a script is stranded and the folder to move it to cannot be named."""
    return click.ClickException(
        f"refusing to release: {_STRANDED} (ADR-092 point 8), and the folder to move it to "
        f"cannot be named: {reason} Nothing was written."
    )
