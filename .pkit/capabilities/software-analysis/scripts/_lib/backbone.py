"""What the capability asks of the backbone and of git.

A capability script runs in its own environment and never imports the backbone
(the lifecycle README, "How a registered command is run"), so it reaches the
backbone through its commands:

- **where the analysis is** — `pkit friction artefacts --json`, the one
  discovery (ADR-057 point 2), at the working tree or, with `--at <commit>`, at
  another state: what the default branch holds, and what it held where this
  branch left it. The script never walks a place, in any state, itself;
- **recording the analysis location** on first use — `pkit docs
  record-location`, the backbone's one writer of a capability's recorded
  locations (COR-049 point 5), with `--yes`: the stamp runs it when it places
  an artefact, so invoking the stamp is the consent;
- **one artefact's friction** — `pkit friction explain <artefact> --json`
  (COR-050 point 13): its state, anchors and the commits behind each changed
  one, which the proposal reads;
- **one data point as it resolves** — `pkit connections resolve <address>
  --json`: the check reads the evidence point the capability defines
  (DEC-001 point 7) through it. The command exits 1 on a point that does not
  resolve and still prints its document, so the document decides, never the
  exit code. A filler never asks for a point: the readers filler reads only
  the analysis.

Git answers which commit a name resolves to, the merge-base of two, who is
working here — the default author of a revalidation record — for the stamp,
every path a history ever added under the places the backbone names, so a
number whose file is gone from the default branch is still counted held
(`added_paths`: one `git log`, since the backbone's reading is of one state,
not of a history); for the number comparison, which versions of those files a
branch's own history wrote, and which the default branch holds, so a number
the default branch took by landing this branch's own work is told from one it
took for another (`blobs_written`, `blob_of`); and, for the
proposal, a file's text at a commit, whether a path anchor's files held a piece
of code at a commit, which commits touched them, which files anywhere in the
tree held a piece of code, which of an anchor's files were renamed and where
to, and a commit's message: each asked of git, with an anchor as a glob
pathspec. Git's pathspec, not the backbone's matcher, decides which files an
anchor names here, and it knows nothing of the project's `friction.exclude`,
which the backbone does not expose to a capability yet.

`default_base` is the branch that numbers are compared with: `$PKIT_CHECK_BASE`,
the variable the project's diff-scoped checks already read, else `origin/main`.
"""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Any

from _lib.model import CAPABILITY, LOCATION, Analysis, Unreadable, analysis_of

Runner = Callable[..., subprocess.CompletedProcess[str]]

#: The base numbers are compared with when none is named, and the variable that names one.
BASE_ENV = "PKIT_CHECK_BASE"
DEFAULT_BASE = "origin/main"


def default_base() -> str:
    return os.environ.get(BASE_ENV) or DEFAULT_BASE


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


def explain(root: Path, artefact: str, run: Runner = subprocess.run) -> Mapping[str, Any]:
    """One artefact's friction, explained — `pkit friction explain <artefact> --json`
    (COR-050 point 13): its state, its anchors, the commits behind each changed one,
    its revalidation point. Raises Unreadable when it is refused or cannot be read."""
    if not artefact or artefact.startswith("-"):
        raise Unreadable(f"{artefact!r} names no artefact")
    return _document(root, ["pkit", "friction", "explain", artefact, "--json"], run)


def show(root: Path, commit: str, path: str) -> str | None:
    """The text of `path` at `commit`, or `None` when it has none there."""
    try:
        proc = subprocess.run(
            ["git", "show", f"{commit}:{path}"], cwd=root, capture_output=True, check=False
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.decode("utf-8", errors="replace")


def holds(root: Path, commit: str, anchor: str, text: str) -> bool:
    """Whether a file a path anchor names held `text` at `commit`, as a whole word —
    so a quoted `--out` is not held by `--output` — through git's own search, the
    anchor read as a glob pathspec (`**` across folders, `*` within one, a folder
    naming everything beneath it), so no file list is computed here. Whole words
    fail safe: a quote that never matches is never counted as quoted, and one that
    stops matching reads as gone, which asks rather than proposes `holds`."""
    try:
        proc = subprocess.run(
            ["git", "grep", "-q", "-I", "-F", "-w", "-e", text, commit, "--", f":(glob){anchor}"],
            cwd=root,
            capture_output=True,
            check=False,
        )
    except OSError:
        return False
    return proc.returncode == 0


def files_holding(root: Path, commit: str, text: str, anchor: str | None = None) -> set[str]:
    """The files that held `text` at `commit`, as a whole word, as `holds` reads it —
    in the whole tree, or among a path anchor's files."""
    argv = ["git", "grep", "-l", "-I", "-F", "-w", "-e", text, commit]
    if anchor is not None:
        argv += ["--", f":(glob){anchor}"]
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


def renamed(root: Path, since: str, anchor: str) -> list[str]:
    """Where the path anchor's files that are gone since `since` were renamed to, by
    git's rename detection between `since` and HEAD — the whole tree compared, so a
    file renamed out of the anchor is found."""
    gone = _git(
        root,
        "diff",
        "--name-only",
        "--no-renames",
        "--diff-filter=D",
        since,
        "HEAD",
        "--",
        f":(glob){anchor}",
    )
    if not gone:
        return []
    deleted = set(gone.splitlines())
    renames = _git(root, "diff", "-M", "--name-status", "--diff-filter=R", "-z", since, "HEAD")
    fields = (renames or "").split("\0")
    pairs = zip(fields[1::3], fields[2::3], strict=False)
    return sorted({new for old, new in pairs if old in deleted and new})


def message(root: Path, commit: str) -> str | None:
    """A commit's message, subject and body — `git log --format=%B` — or `None`."""
    return _git(root, "log", "-1", "--format=%B", commit)


def touched(root: Path, since: str, anchor: str) -> list[tuple[str, str]]:
    """The commits after `since` up to HEAD that touched a file a path anchor names,
    oldest first, each `(commit, subject)` — the anchor read as `holds` reads it. For
    an anchor whose files are gone, which the explanation names no commits for."""
    log = _git(
        root, "log", "--reverse", "--format=%H%x1f%s", f"{since}..HEAD", "--", f":(glob){anchor}"
    )
    pairs = (line.split("\x1f", 1) for line in (log or "").splitlines())
    return [(pair[0], pair[1]) for pair in pairs if len(pair) == 2]


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


def merge_base(root: Path, one: str, other: str) -> str | None:
    """The merge-base of two commits, or `None` when they share no history."""
    return _git(root, "merge-base", one, other)


def added_paths(root: Path, commit: str, folders: Iterable[str]) -> set[str]:
    """Every path under `folders` that a commit reachable from `commit` added — a
    rename read as a removal and an addition, so each name a file ever had is
    there — through one `git log`; empty when there are no folders, or git cannot
    answer. The folders are the places the backbone's reading names, taken as
    written."""
    pathspecs = [f":(literal){folder}" for folder in sorted(set(folders))]
    if not pathspecs or not commit or commit.startswith("-"):
        return set()
    listed = _git(
        root,
        "log",
        commit,
        "--no-renames",
        "--diff-filter=A",
        "--format=",
        "--name-only",
        "--",
        *pathspecs,
    )
    return {line for line in (listed or "").splitlines() if line}


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
