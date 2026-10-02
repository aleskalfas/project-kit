"""The default branch: declared once, resolved one way (COR-054).

A project declares the branch its pull requests merge into once, in the
backbone configuration — `repository.default-branch`, `main` when absent
(point 1) — and every reader of settled state takes its answer here (point
5), directly or through `pkit repository base`:

- **The default branch** (`resolve`): the declared name, then the commit it
  resolves to (point 2) — the remote-tracking reference of the remote the
  shared work is pushed to: the local branch's upstream, else `origin/<name>`;
  else, only when there is no such remote, the local branch, which a reader
  says it used (`warnings`). When none names a commit the answer carries none
  and says why, with the fixes; nothing is guessed (point 4). The one case
  that is not a failure to read is a branch with no commit yet — no remote,
  and HEAD is that branch before its first commit — which the answer marks
  `unborn`: it holds nothing yet, so a reader of what it holds reads nothing
  (COR-052 point 6). A remote not named `origin` is found only as the
  branch's upstream. Asked for a standing value rather than a comparison —
  a data point's filler reads the default branch and never a base (COR-054
  point 3) — the problem names the fetch and the declaration as its fixes,
  never a base (`resolve`'s `standing`).
- **Any branch named as a base** resolves the same way (`resolve_branch`); a
  remote-tracking reference (`origin/main`) or any other revision (a commit, a
  tag, `refs/heads/<name>`) is read as named.
- **The base of a comparison** (`base`): the reference a run names — an
  explicit one, else `$PKIT_CHECK_BASE` — or else the default branch (point
  3); the commit it names, where HEAD left it (their merge-base, the *fork*)
  and whether it moved on since. The friction change check, the migration and
  changeset checks and `pkit repository base` read it here, so no other
  module resolves a base or computes where HEAD left it.
- **The reading** (`settled`): both at once, and what a reader says of them —
  the default branch resolved once, its resolution reused as the base when no
  base is named — and HEAD (`head`). The default branch is read there as a
  standing value reads it, so its problem never names a base, which only the
  base's does. One run of a command reads it once and passes it on.

Each branch name is read in one `git for-each-ref` — the local branch,
`origin/<name>` and the local branch's upstream — and where HEAD left a base in
one `git merge-base`, so a reading starts a handful of git processes, not one
per reference it considers.

The override is a base, never a declaration: `$PKIT_CHECK_BASE` changes what a
comparison compares with, and never what `resolve` answers — nor what a command
that allocates from settled state reads, since such a command reads `resolve`.
A query the backbone runs — a validator, a data point's filler — never sees
the override at all (`validators.QUERY_DROPPED_ENV`).

**The history at hand** (`head`, `is_shallow`): HEAD's commit, or why it names
none — none yet, HEAD being a branch before its first commit (`Head.unborn`),
or git cannot read it here (`Head.problem`): history that exists and was not
read is never history that does not exist (COR-052 point 6) — and whether this
clone's history is cut short. Only a reader knows how much history it needs,
so the backbone says the clone is shallow and the reader judges whether that
stops it.

Reading is forgiving (COR-048 point 4): a configuration that does not parse, or
a value that is not a branch name, reads as the default; the value is kept in
`DefaultBranch.warning` for a reading command to print, and `pkit validate`
reports the file. Git is asked, never written to, and a git that cannot run is
an answer without commits — for HEAD, one that says so — never an exception.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from project_kit.project_config import PROJECT_CONFIG_RELPATH, read_config

#: The configuration block and key the default branch is declared under (point 1).
BLOCK = "repository"
KEY = "default-branch"
DOTTED_KEY = f"{BLOCK}.{KEY}"

#: The name read when none is declared (point 1).
DEFAULT_NAME = "main"

#: Git's default name for the remote a clone was made from — where a branch
#: without an upstream is looked for (point 2).
REMOTE = "origin"

#: The environment variable a pipeline sets once to name every comparison's base (point 3).
CHECK_BASE_ENV = "PKIT_CHECK_BASE"

#: A branch name as git accepts one (`git check-ref-format --branch`) and as the
#: declaration takes it: not an option, not `HEAD` or `@`, no component opening
#: with `.` or closing with `.lock`, no `..`, `@{`, `//`, control character,
#: whitespace or any of `~^:?*[\`, not ending with `/` or `.` — and not a
#: remote-tracking or full reference (`origin/main`, `refs/heads/main`), which
#: name a reference rather than the branch. The configuration schema's pattern
#: for the key is the same.
BRANCH_NAME = re.compile(
    r"^(?![-/.])(?!origin/)(?!refs/)(?!HEAD$)(?!@$)(?!.*\.\.)(?!.*@\{)(?!.*//)"
    r"(?!.*/\.)(?!.*\.lock(?:/|$))(?!.*[/.]$)[^\x00-\x20\x7f~^:?*\[\\]+$"
)

#: Where a default branch's name came from.
DECLARED = "configuration"
DEFAULTED = "default"

#: Where a comparison's base came from.
OPTION = "option"
ENVIRONMENT = "environment"
DEFAULT_BRANCH = "default-branch"

#: Which reference a branch was read from (point 2).
RESOLVED_REMOTE = "remote"
RESOLVED_LOCAL = "local"


def is_branch_name(value: object) -> bool:
    """Whether `value` is a branch name the declaration takes (`BRANCH_NAME`)."""
    return isinstance(value, str) and BRANCH_NAME.fullmatch(value) is not None


@dataclass(frozen=True)
class Resolved:
    """A branch name resolved to a commit (point 2), or why it is not (point 4).

    `ref` is the reference read — `<remote>/<name>`, or `<name>` for the local
    branch — and `resolved` which of the two it is; both `None`, with the
    `problem`, when neither names a commit. `unborn` when the branch has no
    commit yet: no remote, and HEAD is that branch before its first commit."""

    name: str
    ref: str | None
    commit: str | None
    resolved: str | None
    problem: str | None
    unborn: bool = False


@dataclass(frozen=True)
class DefaultBranch:
    """The default branch as declared and resolved (points 1, 2 and 4)."""

    name: str
    source: str  # DECLARED or DEFAULTED
    ref: str | None
    commit: str | None
    resolved: str | None  # RESOLVED_REMOTE or RESOLVED_LOCAL; `None` when nothing resolves
    problem: str | None  # why it names no commit here, with the fixes
    warning: str | None = None  # a declared value read as the default, and why
    unborn: bool = False  # no commit yet: no remote, HEAD on it before its first commit

    def as_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "source": self.source,
            "ref": self.ref,
            "commit": self.commit,
            "resolved": self.resolved,
            "problem": self.problem,
            "unborn": self.unborn,
        }


@dataclass(frozen=True)
class Base:
    """What a comparison against settled state compares with (points 3 and 4).

    `ref` is the reference read — as named, or as the branch resolved — or the
    name when nothing resolves. `tip` is the commit `ref` names; `fork` the
    merge-base of the tip and HEAD, where HEAD left the base; `outdated`
    whether the tip moved on since (it is not an ancestor of HEAD);
    `resolved` which reference a branch was read from — `None` for a revision
    read as named. `problem` is the first reason no comparison can be made — the
    base names no commit, HEAD names none yet, or the two share no history — and
    `None` when one can; the fields after the first missing one are then `None`.
    """

    ref: str
    source: str  # OPTION, ENVIRONMENT or DEFAULT_BRANCH
    tip: str | None
    fork: str | None
    outdated: bool | None
    resolved: str | None
    problem: str | None

    def as_json(self) -> dict[str, Any]:
        return {
            "ref": self.ref,
            "source": self.source,
            "tip": self.tip,
            "fork": self.fork,
            "outdated": self.outdated,
            "resolved": self.resolved,
            "problem": self.problem,
        }


@dataclass(frozen=True)
class Head:
    """HEAD at hand (`head`): its commit, or why it names none — `unborn` when HEAD
    is a branch before its first commit, so there is no history yet; else `problem`,
    why git cannot read it here, so there is history this clone did not read
    (COR-052 point 6)."""

    commit: str | None
    unborn: bool
    problem: str | None

    def as_json(self) -> dict[str, Any]:
        return {"commit": self.commit, "unborn": self.unborn, "problem": self.problem}


@dataclass(frozen=True)
class Settled:
    """One reading of settled state (point 5): the default branch, and the base a
    comparison reads — read together (`settled`), so the default branch is resolved
    once for both, and for what a reader says of them — and HEAD, whose history a
    reader of the reading may need to know exists."""

    default_branch: DefaultBranch
    base: Base
    head: Head

    @property
    def warnings(self) -> list[str]:
        """What a reader of settled state prints on standard error: a declaration read as
        the default (COR-048 point 4), and — since a local branch can lag the shared one
        or carry work nobody pushed (point 2) — a base read from the local branch: the
        default branch when no base is named, else the named one."""
        branch, found = self.default_branch, self.base
        said: list[str] = [branch.warning] if branch.warning else []
        if found.source == DEFAULT_BRANCH:
            if branch.resolved == RESOLVED_LOCAL:
                said.append(_local(f"the default branch {branch.name!r}", branch.name))
        elif found.resolved == RESOLVED_LOCAL:
            said.append(_local(f"the base {found.ref!r}", found.ref))
        return said

    def as_json(self) -> dict[str, Any]:
        """`pkit repository base`'s document: `default_branch` as `resolve` answers it
        for a standing value, `base` as `base` answers it for HEAD, and `head` as
        `head` answers it."""
        return {
            "schema_version": SCHEMA_VERSION,
            "default_branch": self.default_branch.as_json(),
            "base": self.base.as_json(),
            "head": self.head.as_json(),
        }


# --- the declaration (point 1) ---------------------------------------------------------------


def declared(target_root: Path) -> tuple[str, str, str | None]:
    """The declared name, where it came from, and — for a value read as the
    default — why: `(name, source, warning)`, forgivingly (COR-048 point 4)."""
    block = read_config(target_root).get(BLOCK)
    value: Any = cast(Mapping[str, Any], block).get(KEY) if isinstance(block, Mapping) else None
    if value is None:
        return DEFAULT_NAME, DEFAULTED, None
    if is_branch_name(value):
        return value, DECLARED, None
    return (
        DEFAULT_NAME,
        DEFAULTED,
        f"{DOTTED_KEY} {value!r} is not a branch name; read as {DEFAULT_NAME!r} — "
        f"`pkit validate` fails on it",
    )


# --- the resolution (points 2 and 4) --------------------------------------------------------


def resolve(target_root: Path, *, standing: bool = False) -> DefaultBranch:
    """The default branch: declared, then resolved as point 2 orders it.

    `standing` asks for it as a standing value reads it — a data point's filler,
    which no base reaches (COR-054 point 3) — so a problem names the fetch and
    the declaration as its fixes, and never a base."""
    declaration = declared(target_root)
    refs = _branch_refs(target_root, declaration[0])
    return _default_branch(target_root, declaration, refs, standing=standing)


def _default_branch(
    target_root: Path,
    declaration: tuple[str, str, str | None],
    refs: _BranchRefs,
    *,
    standing: bool,
) -> DefaultBranch:
    """`resolve` from the declaration and one listing of the branch's references."""
    name, source, warning = declaration
    found = _resolve_listed(
        target_root, refs, f"the default branch {name!r}", comparison=not standing
    )
    return DefaultBranch(
        name,
        source,
        found.ref,
        found.commit,
        found.resolved,
        found.problem,
        warning,
        found.unborn,
    )


def resolve_branch(target_root: Path, name: str, *, subject: str | None = None) -> Resolved:
    """The branch `name` resolved (point 2): the remote-tracking reference of its
    upstream, else `origin/<name>`, when it names a commit; else, only when there is
    no such remote, the local branch. Each is looked up by its full reference, so a
    tag or another ref of the same short name never stands in for the branch."""
    return _resolve_listed(target_root, _branch_refs(target_root, name), subject)


def _resolve_listed(
    target_root: Path, refs: _BranchRefs, subject: str | None, *, comparison: bool = True
) -> Resolved:
    """`resolve_branch` from what one listing of the branch's references said. A
    problem names a base as a fix only for a `comparison`."""
    name = refs.name
    what = subject or f"the branch {name!r}"
    upstream = refs.upstream
    tried: list[str] = []
    candidates = ([upstream[0]] if upstream else []) + [refs.tracking]
    for full in dict.fromkeys(candidates):
        short = full.removeprefix("refs/remotes/")
        tried.append(short)
        commit = refs.commits.get(full)
        if commit is not None:
            return Resolved(name, short, commit, RESOLVED_REMOTE, None)
    remote = upstream[1] if upstream else (REMOTE if _has_remote(target_root, REMOTE) else None)
    fixes = _fixes(
        declarable=subject is None or subject.startswith("the default branch"),
        comparison=comparison,
    )
    local = refs.commits.get(refs.local)
    if remote is not None:
        anyway = (
            f"; to compare with it anyway, name `refs/heads/{name}` as the base"
            if comparison
            else ""
        )
        unread = (
            f" The local branch {name!r} is not read while a remote holds the shared one — "
            f"it can lag it or carry work nobody pushed{anyway}."
            if local is not None
            else ""
        )
        return Resolved(
            name,
            None,
            None,
            None,
            f"{what} resolves to no commit here: {_either(tried)} names none — "
            f"{_any_of([f'fetch it (`git fetch {remote} {name}`)', *fixes])}.{unread}",
        )
    if local is not None:
        return Resolved(name, name, local, RESOLVED_LOCAL, None)
    if _unborn(target_root, name):
        return Resolved(
            name, None, None, None, f"{what} has no commit yet: commit first.", unborn=True
        )
    return Resolved(
        name,
        None,
        None,
        None,
        f"{what} resolves to no commit here: there is no remote and no local branch "
        f"{name!r} — {_any_of(fixes)}.",
    )


def _either(refs: list[str]) -> str:
    quoted = [repr(ref) for ref in refs]
    return quoted[0] if len(quoted) == 1 else f"neither {quoted[0]} nor {quoted[1]}"


def _any_of(fixes: list[str]) -> str:
    return fixes[0] if len(fixes) == 1 else f"{', '.join(fixes[:-1])}, or {fixes[-1]}"


def _fixes(*, declarable: bool, comparison: bool = True) -> list[str]:
    """What else fixes a branch that resolves nowhere: the default branch can be
    declared, and a comparison — never a standing value — can name another base."""
    declare = f"declare the right one (`{DOTTED_KEY}` in {PROJECT_CONFIG_RELPATH.as_posix()})"
    name = f"name {'a' if declarable else 'another'} base with --base or {CHECK_BASE_ENV}"
    fixes = [declare] if declarable else []
    return [*fixes, name] if comparison else fixes


# --- the base of a comparison (point 3) ------------------------------------------------------


def base(target_root: Path, explicit: str | None = None) -> Base:
    """The base a comparison against settled state compares HEAD with (point 3):
    `explicit`, else `$PKIT_CHECK_BASE`, else the default branch — its commit, the
    fork and whether it moved on, or the problem that stops a comparison."""
    return _base(target_root, explicit, None)


def _base(target_root: Path, explicit: str | None, branch: DefaultBranch | None) -> Base:
    """`base`, reading the default branch from `branch` when the caller resolved it
    already — so one run resolves it once — and resolving it only when it is the base."""
    if explicit is not None:
        return _named(target_root, explicit, OPTION)
    from_environment = os.environ.get(CHECK_BASE_ENV)
    if from_environment:
        return _named(target_root, from_environment, ENVIRONMENT)
    branch = resolve(target_root) if branch is None else branch
    if branch.ref is None or branch.commit is None:
        return Base(branch.name, DEFAULT_BRANCH, None, None, None, None, branch.problem)
    return _compared(target_root, branch.ref, DEFAULT_BRANCH, branch.commit, branch.resolved)


def _named(target_root: Path, ref: str, source: str) -> Base:
    """A base named for one run: a remote-tracking reference as named; a branch name
    resolved as the default branch is (point 2); any other revision as named."""
    if not ref or ref.startswith("-"):
        return _refused(ref, source, f"the base {ref!r} is not a revision name.")
    tracking = commit_of(target_root, f"refs/remotes/{ref}")
    if tracking is not None:
        return _compared(target_root, ref, source, tracking, RESOLVED_REMOTE)
    refs = _branch_refs(target_root, ref) if is_branch_name(ref) else None
    if refs is not None and refs.known:
        found = _resolve_listed(target_root, refs, f"the base {ref!r}")
        if found.ref is None or found.commit is None:
            return _refused(ref, source, found.problem or f"the base {ref!r} resolves nowhere.")
        return _compared(target_root, found.ref, source, found.commit, found.resolved)
    tip = commit_of(target_root, ref)
    if tip is None:
        return _refused(
            ref,
            source,
            f"the base {ref!r} does not resolve to a commit in this repository: fetch it "
            f"(e.g. `{_fetch_hint(target_root, ref)}`), or name another with --base or "
            f"{CHECK_BASE_ENV}.",
        )
    return _compared(target_root, ref, source, tip, None)


def _compared(target_root: Path, ref: str, source: str, tip: str, resolved: str | None) -> Base:
    """Where HEAD left `tip` and whether it moved on since, or why not. The merge-base
    is asked of HEAD by name; only when git finds none is HEAD looked at, to tell a
    branch with no commit yet from one that shares no history with the base."""
    found = _git(target_root, "merge-base", tip, "HEAD")
    fork = found.stdout.strip() if found is not None and found.returncode == 0 else ""
    if not fork and commit_of(target_root, "HEAD") is None:
        return Base(
            ref,
            source,
            tip,
            None,
            None,
            resolved,
            "HEAD names no commit yet; a branch is compared with its base, so commit first.",
        )
    if not fork:
        return Base(
            ref,
            source,
            tip,
            None,
            None,
            resolved,
            f"HEAD and the base {ref!r} share no history to compare; in a shallow clone, "
            f"fetch the history back to where the branch left the base (e.g. `git fetch "
            f"--unshallow`).",
        )
    return Base(ref, source, tip, fork, fork != tip, resolved, None)


def _refused(ref: str, source: str, problem: str) -> Base:
    return Base(ref, source, None, None, None, None, problem)


# --- what a reader says ----------------------------------------------------------------------


def warnings(target_root: Path, explicit: str | None = None) -> list[str]:
    """What a reader of settled state prints on standard error (`Settled.warnings`)."""
    return settled(target_root, explicit).warnings


def _local(what: str, name: str) -> str:
    return (
        f"{what} is read from the local branch {name!r}: this repository has no remote to "
        f"read the shared one from, and a local branch can lag it or carry work nobody "
        f"pushed (COR-054 point 2)"
    )


# --- the reading command (point 5) -----------------------------------------------------------

#: The version of the reading's document (`Settled.as_json`); raised when a key a
#: reader relies on changes its meaning or goes, never for a key added.
SCHEMA_VERSION = 1


def settled(target_root: Path, explicit: str | None = None) -> Settled:
    """The reading (point 5): the default branch, resolved once, and the base a
    comparison reads — `explicit`, else `$PKIT_CHECK_BASE`, else that same
    resolution of the default branch — and HEAD.

    The default branch is read as a standing value reads it: a data point's filler
    reads it here, and no base reaches a filler (COR-054 point 3), so its problem
    names the fetch and the declaration. As the base it keeps a comparison's fixes,
    which name a base too."""
    declaration = declared(target_root)
    refs = _branch_refs(target_root, declaration[0])
    branch = _default_branch(target_root, declaration, refs, standing=True)
    compared = (
        branch
        if branch.commit is not None
        else _default_branch(target_root, declaration, refs, standing=False)
    )
    return Settled(branch, _base(target_root, explicit, compared), head(target_root))


def render_json(document: Mapping[str, Any]) -> str:
    """The reading's document as stable JSON: keys sorted, the same bytes for the same state."""
    return json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


#: How many characters of a commit the human view shows.
_SHORT = 12

#: Where a base came from, in the human view.
_BASE_SOURCES = {
    OPTION: "--base",
    ENVIRONMENT: f"${CHECK_BASE_ENV}",
    DEFAULT_BRANCH: "the default branch",
}


def render_human(document: Mapping[str, Any]) -> str:
    """Two lines for the reading's document: the default branch, and the base."""
    branch = document["default_branch"]
    if branch["commit"]:
        resolved = f"{branch['ref']} at {branch['commit'][:_SHORT]} ({branch['resolved']})"
    else:
        resolved = f"no commit — {branch['problem']}"
    lines = [f"Default branch: {branch['name']} ({branch['source']}) → {resolved}"]
    found = document["base"]
    line = f"Base: {found['ref']} ({_BASE_SOURCES.get(found['source'], found['source'])})"
    if found["problem"] is not None:
        line += f" — {found['problem']}"
    else:
        line += f" at {found['tip'][:_SHORT]}; HEAD left it at {found['fork'][:_SHORT]}"
        if found["outdated"]:
            line += " (it moved on since)"
    lines.append(line)
    return "\n".join(lines) + "\n"


# --- git ------------------------------------------------------------------------------------


def commit_of(target_root: Path, name: str) -> str | None:
    """The commit `name` resolves to, or `None` — for a name that is none, or a git
    that cannot answer."""
    if not name or name.startswith("-"):
        return None
    completed = _git(target_root, "rev-parse", "--verify", "--quiet", f"{name}^{{commit}}")
    if completed is None or completed.returncode != 0:
        return None
    return completed.stdout.strip() or None


@dataclass(frozen=True)
class _BranchRefs:
    """What this repository holds of the branch `name`: the commit each of its
    references names — the local branch, `origin/<name>` and the local branch's
    upstream, those that name one — and that upstream, in full, with its remote
    (`None` when it tracks none, or tracks a local branch)."""

    name: str
    commits: Mapping[str, str]
    upstream: tuple[str, str] | None

    @property
    def local(self) -> str:
        return f"refs/heads/{self.name}"

    @property
    def tracking(self) -> str:
        return f"refs/remotes/{REMOTE}/{self.name}"

    @property
    def known(self) -> bool:
        """Whether this repository knows a branch `name`: locally, or on `origin`."""
        return self.local in self.commits or self.tracking in self.commits


#: One line of `_branch_refs`' listing: a reference, the object it names and that
#: object's type, and — for a local branch — its upstream and the upstream's remote.
_LISTING = "%(refname)%09%(objectname)%09%(objecttype)%09%(upstream)%09%(upstream:remotename)"


def _branch_refs(target_root: Path, name: str) -> _BranchRefs:
    """The branch `name`'s references, read in one `git for-each-ref`: the local branch
    and `origin/<name>`, each by its full name. An upstream that is neither — a remote
    not called `origin`, or a branch of another name — is looked up on its own, and so
    is a reference that names something other than a commit, which `commit_of` peels as
    it peels every name; neither is the common case."""
    local, tracking = f"refs/heads/{name}", f"refs/remotes/{REMOTE}/{name}"
    completed = _git(target_root, "for-each-ref", f"--format={_LISTING}", local, tracking)
    listed = completed.stdout if completed is not None and completed.returncode == 0 else ""
    commits: dict[str, str] = {}
    upstream: tuple[str, str] | None = None
    for line in listed.splitlines():
        refname, objectname, objecttype, full, remote = [*line.split("\t"), "", "", "", ""][:5]
        if refname not in (local, tracking):  # a pattern matches the references beneath it too
            continue
        commit = objectname if objecttype == "commit" else commit_of(target_root, refname)
        if commit:
            commits[refname] = commit
        if refname == local and full.startswith("refs/remotes/") and remote:
            upstream = (full, remote)
    if upstream is not None and upstream[0] not in (local, tracking):
        commit = commit_of(target_root, upstream[0])
        if commit is not None:
            commits[upstream[0]] = commit
    return _BranchRefs(name, commits, upstream)


def head(target_root: Path) -> Head:
    """HEAD at hand: its commit; else none yet, when HEAD names no object — a branch
    before its first commit; else why git cannot read it — HEAD names an object git
    cannot read as a commit, or git cannot answer at all (a repository it refuses or
    cannot open, none, no git)."""
    commit = commit_of(target_root, "HEAD")
    if commit is not None:
        return Head(commit, False, None)
    named = _git(target_root, "rev-parse", "--verify", "--quiet", "HEAD")
    if named is None:
        return Head(None, False, "git cannot read HEAD here: git could not be run")
    object_name = named.stdout.strip()
    if named.returncode == 1 and not object_name:
        return Head(None, True, None)
    if named.returncode == 0 and object_name:
        return Head(
            None,
            False,
            f"HEAD names {object_name[:_SHORT]}, which git cannot read as a commit here",
        )
    said = [line.strip() for line in named.stderr.splitlines() if line.strip()]
    detail = said[0] if said else f"exit status {named.returncode}"
    return Head(None, False, f"git cannot read HEAD here: {detail}")


def is_shallow(target_root: Path) -> bool:
    """Whether this clone's history is cut short — a shallow clone. A git that
    cannot answer reads as not shallow: nothing is said that git did not say."""
    completed = _git(target_root, "rev-parse", "--is-shallow-repository")
    if completed is None or completed.returncode != 0:
        return False
    return completed.stdout.strip() == "true"


def _has_remote(target_root: Path, remote: str) -> bool:
    completed = _git(target_root, "remote", "get-url", remote)
    return completed is not None and completed.returncode == 0


def _unborn(target_root: Path, name: str) -> bool:
    """Whether HEAD is the branch `name`, before its first commit — never a branch
    whose commit git cannot read (`head`)."""
    completed = _git(target_root, "symbolic-ref", "--quiet", "HEAD")
    on_it = completed is not None and completed.stdout.strip() == f"refs/heads/{name}"
    return on_it and head(target_root).unborn


def _fetch_hint(target_root: Path, ref: str) -> str:
    """The fetch that brings `ref` here: from the remote it names, or from `origin`."""
    remote, slash, branch = ref.partition("/")
    if slash and branch and _has_remote(target_root, remote):
        return f"git fetch {remote} {branch}"
    return f"git fetch {REMOTE} {ref}" if is_branch_name(ref) else f"git fetch {REMOTE}"


def _git(target_root: Path, *args: str) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            ["git", *args], cwd=target_root, capture_output=True, text=True, check=False
        )
    except OSError:
        return None
