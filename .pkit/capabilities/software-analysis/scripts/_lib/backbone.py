"""What the capability asks of the backbone and of git.

A capability script runs in its own environment and never imports the backbone
(the lifecycle README, "How a registered command is run"), so it reaches the
backbone through its commands:

- **where the analysis is** — `pkit friction artefacts --json`, the one
  discovery (ADR-057 point 2), at the working tree or, with `--at <commit>`, at
  another state: what the default branch holds, and what it held where this
  branch left it. The script never walks a place or lists a commit itself;
- **recording the analysis location** on first use — `pkit docs
  record-location`, the backbone's one writer of a capability's recorded
  locations (COR-049 point 5), with `--yes`: the stamp runs it when it places
  an artefact, so invoking the stamp is the consent;
- **one artefact's friction** — `pkit friction explain <artefact> --json`
  (COR-050 point 13): its state, anchors and the commits behind each changed
  one, which the proposal reads rather than recomputing.

Git answers which commit a name resolves to, the merge-base of two, who is
working here — the default author of a revalidation record — and, for the
proposal, a file's text at a commit, whether a path anchor's files held a piece
of code at a commit, and which commits touched them: each asked of git with the
anchor as a glob pathspec, so no file list is computed here.

`default_base` is the branch that numbers are compared with: `$PKIT_CHECK_BASE`,
the variable the project's diff-scoped checks already read, else `origin/main`.
"""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Callable, Mapping
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
    """Whether a file a path anchor names held `text` at `commit` — git's own search,
    the anchor read as a glob pathspec (`**` across folders, `*` within one, a
    folder naming everything beneath it), so no file list is computed here."""
    try:
        proc = subprocess.run(
            ["git", "grep", "-q", "-I", "-F", "-e", text, commit, "--", f":(glob){anchor}"],
            cwd=root,
            capture_output=True,
            check=False,
        )
    except OSError:
        return False
    return proc.returncode == 0


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


def commit_of(root: Path, name: str) -> str | None:
    """The commit `name` resolves to, or `None`."""
    if not name or name.startswith("-"):
        return None
    return _git(root, "rev-parse", "--verify", "--quiet", f"{name}^{{commit}}")


def merge_base(root: Path, one: str, other: str) -> str | None:
    """The merge-base of two commits, or `None` when they share no history."""
    return _git(root, "merge-base", one, other)


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
