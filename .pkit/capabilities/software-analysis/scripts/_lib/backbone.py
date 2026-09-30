"""What the capability asks of the backbone and of git.

A capability script runs in its own environment and never imports the backbone
(the lifecycle README, "How a registered command is run"), so it reaches the
backbone through its commands:

- **where the analysis is** — `pkit friction artefacts --json`, the one
  discovery (ADR-057 point 2), at the working tree or, with `--at <commit>`, at
  another state: what the default branch holds, and what it held where this
  branch left it. The script never walks a place, in any state, itself;
- **what is settled** — `pkit repository base --json` (COR-054 point 5): the
  default branch as declared and resolved, and the base a comparison reads —
  `--base <ref>` when a command is given one, else `$PKIT_CHECK_BASE`, else
  the default branch — with its commit and where this branch left it. The
  backbone resolves both; the script never reads the variable, the
  declaration or a remote's reference, and never computes a merge-base
  itself. What the backbone says of them on standard error — a branch read
  from the local branch — is passed on;
- **recording the analysis location** on first use — `pkit docs
  record-location`, the backbone's one writer of a capability's recorded
  locations (COR-049 point 5): with `--dry-run` to ask whether it is recorded
  already, and with `--yes` when it is not — the stamp runs it when it places
  an artefact, so invoking the stamp is the consent;
- **one artefact's friction** — `pkit friction explain <artefact> --json`
  (COR-050 point 13): its state and body, its anchors with the files each path
  anchor stands on, and the commits behind each finding with the paths behind
  it, which the proposal reads;
- **one data point as it resolves** — `pkit connections resolve <address>
  --json`: the check reads the evidence point the capability defines
  (DEC-001 point 7) through it. The command exits 1 on a point that does not
  resolve and still prints its document, so the document decides, never the
  exit code. A filler never asks for a point: the readers filler reads only
  the analysis.

Git answers which commit a name resolves to, who is working here — the
default author of a revalidation record — whether the clone
is shallow; for the stamp and the number comparison, each path a history
added under the folders of the places the backbone names, with the commit that
added it (`added`: one `git log`, since the backbone's reading is of one state,
not of a history) — git lists the paths, and which of them were files of a
place, not left out by `friction.exclude`, the backbone's reading at that
commit says (`_lib/history.py`); for the number comparison, which versions of those files a
branch's own history wrote, and which the default branch holds, so a number
the default branch took by landing this branch's own work is told from one it
took for another (`blobs_written`, `blob_of`); and, for the
proposal, which files held a piece of code at a commit — anywhere in the tree,
or among files the caller names — where files were renamed to between two
commits, and a commit's message. Which files an anchor stands on is never
asked of git: the explanation names them, and every path given to git here is
taken literally, never as a pattern.
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from _lib.model import CAPABILITY, LOCATION, Analysis, Unreadable, analysis_of

Runner = Callable[..., subprocess.CompletedProcess[str]]

#: How many characters of a commit a message shows.
SHORT = 12

#: What opens a commit's line in `added`'s listing, where no path can start.
_COMMIT_MARK = "\x01"


def project_root() -> Path:
    """The repository a command runs in: git's top level, else the working directory."""
    top = _git(Path.cwd(), "rev-parse", "--show-toplevel")
    return Path(top) if top else Path.cwd()


def read_analysis(root: Path, at: str | None = None, run: Runner = subprocess.run) -> Analysis:
    """The analysis in the working tree at `root` — or, with `at`, in that commit —
    through `pkit friction artefacts --json`. Raises Unreadable when there is no
    document to read."""
    argv = ["pkit", "friction", "artefacts", "--json"]
    if at is not None:
        argv[3:3] = ["--at", at]
    return analysis_of(_document(root, argv, run))


@dataclass(frozen=True)
class Branch:
    """The default branch as the backbone resolves it (COR-054 points 1 and 2): its
    name, the reference read and its commit — or, with neither, why, and the fix."""

    name: str
    ref: str | None
    commit: str | None
    problem: str | None


@dataclass(frozen=True)
class Base:
    """The base a comparison reads (COR-054 point 3): the reference read, the commit it
    names (`tip`), where HEAD left it (`fork`) and whether it moved on since — or why
    no comparison can be made (`problem`); `tip` may name a commit even then."""

    ref: str
    tip: str | None
    fork: str | None
    outdated: bool
    problem: str | None


@dataclass(frozen=True)
class Settled:
    """What `pkit repository base --json` answers: the default branch, and the base."""

    default_branch: Branch
    base: Base


#: The version of `pkit repository base --json` this reading understands.
SETTLED_VERSION = 1


def settled(root: Path, base: str | None = None, run: Runner = subprocess.run) -> Settled:
    """What is settled, as the backbone resolves it — `pkit repository base --json`
    (COR-054 point 5): the default branch, and the base a comparison reads — `base`
    when given, else the backbone's own. Its warnings are passed on to standard error.
    Raises Unreadable when there is no document to read — from a backbone that
    predates the command, too, saying so — or one of a version this reading does not
    understand."""
    argv = ["pkit", "repository", "base", "--json"]
    if base is not None:
        argv.append(f"--base={base}")
    proc = _run(root, argv, run)
    for line in (proc.stderr or "").splitlines():
        if line.startswith("warning:"):
            print(line, file=sys.stderr)
    if proc.returncode != 0 and "No such command" in (proc.stderr or ""):
        raise Unreadable(
            f"`{' '.join(argv)}` is not a command of the installed backbone, which predates "
            f"it — upgrade it (`pkit upgrade`)"
        )
    try:
        document = json.loads(proc.stdout or "") if proc.returncode == 0 else None
    except ValueError:
        document = None
    if not isinstance(document, Mapping):
        raise Unreadable(_failed(argv, proc))
    version = document.get("schema_version")
    if version != SETTLED_VERSION:
        raise Unreadable(
            f"`pkit repository base` answered schema_version {version!r}; this capability "
            f"reads {SETTLED_VERSION}"
        )
    branch = document.get("default_branch")
    named = document.get("base")
    if not isinstance(branch, Mapping) or not isinstance(named, Mapping):
        raise Unreadable(_failed(argv, proc))
    return Settled(
        Branch(
            name=str(branch.get("name")),
            ref=_text(branch.get("ref")),
            commit=_text(branch.get("commit")),
            problem=_text(branch.get("problem")),
        ),
        Base(
            ref=str(named.get("ref")),
            tip=_text(named.get("tip")),
            fork=_text(named.get("fork")),
            outdated=named.get("outdated") is True,
            problem=_text(named.get("problem")),
        ),
    )


def _text(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


#: The version of `pkit friction explain --json` this reading understands. A document
#: without `schema_version` comes from a backbone that predates the key: version 1.
EXPLAIN_VERSION = 1


def explain(root: Path, artefact: str, run: Runner = subprocess.run) -> Mapping[str, Any]:
    """One artefact's friction, explained — `pkit friction explain <artefact> --json`
    (COR-050 point 13): its state, body and revalidation point, its anchors with the
    files each path anchor stands on, and the commits behind each finding with the
    paths behind it. Raises Unreadable when it is refused, cannot be read, or
    answers a version this reading does not understand."""
    if not artefact or artefact.startswith("-"):
        raise Unreadable(f"{artefact!r} names no artefact")
    document = _document(root, ["pkit", "friction", "explain", artefact, "--json"], run)
    version = document.get("schema_version", EXPLAIN_VERSION)
    if version != EXPLAIN_VERSION:
        raise Unreadable(
            f"`pkit friction explain` answered schema_version {version!r}; "
            f"this capability reads {EXPLAIN_VERSION}"
        )
    return document


def files_holding(
    root: Path, commit: str, text: str, among: Iterable[str] | None = None
) -> set[str]:
    """The files that held `text` at `commit`, as a whole word — so a quoted `--out`
    is not held by `--output` — through git's own search, binary files left out: in
    the whole tree, or among the files `among` names, each taken literally, never as
    a pattern (none named, none searched). Whole words fail safe: a quote that never
    matches is never counted as quoted, and one that stops matching reads as gone,
    which asks rather than proposes `holds`."""
    argv = ["git", "grep", "-l", "-I", "-F", "-w", "-e", text, commit]
    if among is not None:
        pathspecs = [f":(literal){path}" for path in sorted(set(among))]
        if not pathspecs:
            return set()
        argv += ["--", *pathspecs]
    try:
        proc = subprocess.run(argv, cwd=root, capture_output=True, text=True, check=False)
    except OSError:
        return set()
    prefix = f"{commit}:"
    return {
        line[len(prefix) :]
        for line in proc.stdout.splitlines()
        if proc.returncode == 0 and line.startswith(prefix)
    }


def renamed(root: Path, since: str, until: str, paths: Iterable[str]) -> list[str]:
    """Where those of `paths` that `since` held were renamed to by `until`, by git's
    rename detection between the two — the whole tree compared, so a file renamed
    anywhere is found; sorted."""
    names = set(paths)
    if not names:
        return []
    renames = _git(root, "diff", "-M", "--name-status", "--diff-filter=R", "-z", since, until)
    fields = (renames or "").split("\0")
    pairs = zip(fields[1::3], fields[2::3], strict=False)
    return sorted({new for old, new in pairs if old in names and new})


def message(root: Path, commit: str) -> str | None:
    """A commit's message, subject and body — `git log --format=%B` — or `None`."""
    return _git(root, "log", "-1", "--format=%B", commit)


def record_location(root: Path, run: Runner = subprocess.run) -> str | None:
    """Record the analysis location where it now lies (COR-049 point 5), through
    `pkit docs record-location`. Returns the line it printed when it recorded,
    `None` when the location was recorded already. Raises Unreadable when it fails."""
    argv = ["pkit", "docs", "record-location", CAPABILITY, LOCATION, "--yes"]
    proc = _run(root, argv, run)
    if proc.returncode != 0:
        raise Unreadable(_failed(argv, proc))
    line = (proc.stdout or "").strip()
    return line if line.startswith("recorded ") else None


def location_recorded(root: Path, run: Runner = subprocess.run) -> bool:
    """Whether the analysis location is recorded already (COR-049 point 5), as `pkit
    docs record-location --dry-run` says, writing nothing; `False` when it cannot
    tell, so the stamp records, and a recording that fails refuses the stamp."""
    argv = ["pkit", "docs", "record-location", CAPABILITY, LOCATION, "--dry-run"]
    try:
        proc = _run(root, argv, run)
    except Unreadable:
        return False
    return proc.returncode == 0 and (proc.stdout or "").strip().endswith("(recorded already)")


def read_point(root: Path, address: str, run: Runner = subprocess.run) -> Mapping[str, Any]:
    """The data point `address` as `pkit connections resolve --json` prints it,
    resolved or not. Raises Unreadable when there is no document to read."""
    argv = ["pkit", "connections", "resolve", address, "--json"]
    proc = _run(root, argv, run)
    try:
        document = json.loads(proc.stdout or "")
    except ValueError:
        document = None
    if not isinstance(document, Mapping) or "resolved" not in document:
        raise Unreadable(_failed(argv, proc))
    return document


def commit_of(root: Path, name: str) -> str | None:
    """The commit `name` resolves to, or `None`."""
    if not name or name.startswith("-"):
        return None
    return _git(root, "rev-parse", "--verify", "--quiet", f"{name}^{{commit}}")


def added(root: Path, revisions: str, folders: Iterable[str]) -> list[tuple[str, str]]:
    """Each path under `folders` a commit of `revisions` added — a commit and its
    history, or a range `<from>..<to>` — with that commit, newest first; a rename is
    read as a removal and an addition, so each name a file ever had is there. One
    `git log`; empty when there are no folders, or git cannot answer. The folders
    are the places the backbone's reading names, taken as written: every path
    beneath them, whatever it is — which were files of a place is the backbone's
    reading at the commit to say."""
    pathspecs = [f":(literal){folder}" for folder in sorted(set(folders))]
    if not pathspecs or not revisions or revisions.startswith("-"):
        return []
    listed = _git(
        root,
        "log",
        revisions,
        "-z",  # every path as written, never quoted
        "--no-renames",
        "--diff-filter=A",
        "--format=%x01%H",  # the commit, after `_COMMIT_MARK`
        "--name-only",
        "--",
        *pathspecs,
    )
    found: list[tuple[str, str]] = []
    commit = ""
    for field in (listed or "").split("\0"):
        field = field.lstrip("\n")  # the line ending a commit's line
        if field.startswith(_COMMIT_MARK):
            commit = field[len(_COMMIT_MARK) :]
        elif field and commit:
            found.append((commit, field))
    return found


def is_shallow(root: Path) -> bool:
    """Whether this clone is shallow: its history stops before the first commit."""
    return _git(root, "rev-parse", "--is-shallow-repository") == "true"


def blobs_written(root: Path, since: str, folders: Iterable[str]) -> set[str]:
    """Every version of a file under `folders` a commit after `since` up to HEAD wrote,
    by its blob — through one `git log`; empty when there are no folders, or git
    cannot answer. A file's content, not its path, is what two histories share when
    one landed the other's work under another commit, as a squash does."""
    pathspecs = [f":(literal){folder}" for folder in sorted(set(folders))]
    if not pathspecs or not since or since.startswith("-"):
        return set()
    listed = _git(
        root,
        "log",
        f"{since}..HEAD",
        "--no-renames",
        "--format=",
        "--raw",
        "--no-abbrev",
        "--",
        *pathspecs,
    )
    written: set[str] = set()
    for line in (listed or "").splitlines():
        fields = line.split("\t", 1)[0].split()
        if line.startswith(":") and len(fields) >= 4 and fields[3].strip("0"):
            written.add(fields[3])
    return written


def blob_of(root: Path, commit: str, path: str) -> str | None:
    """The blob `path` holds at `commit`, or `None` when it holds none there."""
    if not commit or commit.startswith("-"):
        return None
    return _git(root, "rev-parse", "--verify", "--quiet", f"{commit}:{path}")


def user_name(root: Path) -> str | None:
    """Who git says is working here, its `user.name`, or `None`."""
    return _git(root, "config", "user.name")


def _document(root: Path, argv: list[str], run: Runner) -> Mapping[str, Any]:
    proc = _run(root, argv, run)
    try:
        document = json.loads(proc.stdout or "") if proc.returncode == 0 else None
    except ValueError:
        document = None
    if not isinstance(document, Mapping):
        raise Unreadable(_failed(argv, proc))
    return document


def _run(root: Path, argv: list[str], run: Runner) -> subprocess.CompletedProcess[str]:
    try:
        return run(argv, cwd=root, capture_output=True, text=True, check=False)
    except OSError as exc:
        raise Unreadable(f"`pkit` could not be run ({exc})") from exc


def _failed(argv: list[str], proc: subprocess.CompletedProcess[str]) -> str:
    detail = [line for line in (proc.stderr or proc.stdout or "").strip().splitlines() if line]
    return f"`{' '.join(argv)}` exited {proc.returncode}" + (f": {detail[-1]}" if detail else "")


def _git(root: Path, *args: str) -> str | None:
    try:
        proc = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)
    except OSError:
        return None
    out = proc.stdout.strip()
    return out if proc.returncode == 0 and out else None
