"""The cross-repository guard: a change on the hosting service is made in the
session's own repository, or with the operator's confirmation.

A session is rooted in one repository and carries that repository's governance;
a change aimed at another repository from inside it is made under the wrong
project's rules (COR-039). ADR-034 realises the principle as a check in the
program that makes the change: it compares the **session's anchor** — the
directory the harness fixed when the session started, which does not move with
`cd` — with the **target**, the repository the change would land in, and on a
difference refuses, or asks at a terminal. ADR-061 point 6 has the backbone's
commands that change the hosting service run that check themselves.

Two parts:

- :func:`evaluate` — the comparison, and nothing else: the repository of the
  session's anchor against the repository of the target directory, answered
  from git alone, needing no network. Two directories are the same repository
  when git gives them one common directory (a linked worktree of the session's
  repository is its own), or when both have an `origin` remote and the two
  remotes name one repository once normalised (:func:`normalize_origin_url`:
  ssh or https, with or without `.git`, in any case). Its verdict is
  :data:`SAME_REPO`, :data:`DIVERGED` or :data:`UNDETERMINED`, the last with
  why: :data:`NONCOVERAGE` when there is nothing to compare — no anchor, or a
  side that is not in a git repository — and :data:`FAULT` when git could not
  be asked.
- :func:`clear` — the gate a change passes through. It answers a
  :class:`Clearance`, saying how the change passed (:data:`SAME_REPO`;
  :data:`UNDETERMINED`; :data:`FLAG`, confirmed with the call; :data:`TERMINAL`,
  confirmed at a terminal), or a :class:`Refusal`. With no anchor there is no
  session to compare with, so the guard does not fire, and the verdict says
  undetermined, never that the target is the session's own repository. A git
  fault warns and proceeds. The question goes to standard error, and is asked
  only when standard input and standard error are both terminals: otherwise,
  with no confirmation passed with the call, a target in another repository is
  refused. A dry run never asks, and ends as a run with nobody to ask would.

A function that makes a change requires a clearance and the directory it acts
in (:func:`require`), and acts there, so a caller that imports it cannot make
the change without the guard, nor clear one directory and act in another.

The anchor is read from the harness. Claude Code's is the one read today, under
a name that says so (:data:`CLAUDE_CODE_ANCHOR`); the documents and the messages
name only "the session's anchor" and "the target", so another harness changes
the lookup, not the contract.

**An interlock, not a boundary** (ADR-034 point 5). It catches a change made
through the methodology's own commands while the session points at the wrong
repository. It does not stop a change routed around them — a raw `gh -R`, a
raw `git -C`, the anchor unset — and it compares directories, not what `gh`
reaches: a set `GH_REPO` sends `gh` to another repository than the working
directory's remote, and the guard does not see it.

project-management's guard (`_lib/session_guard.py` in the capability) keeps a
copy of this comparison until it reads this one by command (#1220);
`tests/test_session_guard_parity.py` holds the two to one table of cases.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TextIO, cast

#: Claude Code's session anchor: the project directory the harness sets when a
#: session starts, which does not move with `cd` (ADR-034). Another harness
#: provides its own, read under its own name.
CLAUDE_CODE_ANCHOR = "CLAUDE_PROJECT_DIR"

#: The comparison's verdicts (:class:`Comparison`), which a document's
#: `verdict` states as they are, whether or not the change was confirmed.
SAME_REPO = "same-repo"
DIVERGED = "diverged"
UNDETERMINED = "undetermined"

#: Why a verdict is undetermined: nothing to compare — no anchor, or a side
#: that is not in a git repository — or git could not be asked.
NONCOVERAGE = "noncoverage"
FAULT = "fault"

#: How a clearance passed, besides :data:`SAME_REPO` and :data:`UNDETERMINED`:
#: confirmed with the call, or at a terminal.
FLAG = "flag"
TERMINAL = "terminal"

#: A command's document's `reason_kind` for a change the guard refused.
FOREIGN_REPOSITORY = "foreign-repository"

#: The option a command takes to confirm a change in another repository.
CONFIRM_OPTION = "--allow-foreign-repo"

# How long one git question may take before it counts as a fault.
_GIT_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True)
class Comparison:
    """The session's anchor against the target: the verdict, and the two
    repositories as git names their working trees (None where there is none)."""

    verdict: str
    #: :data:`NONCOVERAGE` or :data:`FAULT` for an undetermined verdict; None otherwise.
    undetermined_kind: str | None
    anchor: Path | None
    target: Path | None
    #: The verdict in words, for a message.
    reason: str


@dataclass(frozen=True)
class Clearance:
    """A change in `directory` may go ahead; `passed` says how the guard let it:
    :data:`SAME_REPO`, :data:`UNDETERMINED`, :data:`FLAG` or :data:`TERMINAL`."""

    directory: Path
    passed: str
    comparison: Comparison

    def as_json(self) -> dict[str, Any]:
        """The guard as a command's document states it, `cleared` how it passed."""
        return _document(self.comparison, self.passed)

    def describe(self) -> str:
        """How the change passed, as one phrase for a command's output."""
        if self.passed == SAME_REPO:
            return "the target is the session's own repository"
        if self.passed == FLAG:
            return f"another repository than the session's anchor, confirmed by {CONFIRM_OPTION}"
        if self.passed == TERMINAL:
            return "another repository than the session's anchor, confirmed at the terminal"
        return f"not compared: {self.comparison.reason}"


@dataclass(frozen=True)
class Refusal:
    """The guard refused a change in `directory`; `reason` says why, and how to go on."""

    directory: Path
    comparison: Comparison
    reason: str

    def as_json(self) -> dict[str, Any]:
        """The guard as a command's document states it, `cleared` null."""
        return _document(self.comparison, None)


def session_anchor() -> str | None:
    """The session's anchor the harness provides, or None outside any session."""
    return os.environ.get(CLAUDE_CODE_ANCHOR) or None


def evaluate(target_dir: Path | str, anchor: Path | str | None) -> Comparison:
    """Compare the repository of `target_dir` with the repository of the
    session's `anchor`, from git's answers alone; no network, no question.

    See the module docstring for when two directories are one repository.
    """
    if anchor is None or not str(anchor):
        return Comparison(
            UNDETERMINED,
            NONCOVERAGE,
            None,
            None,
            "there is no session's anchor, so there is no session to compare the target with",
        )
    try:
        anchor_root, anchor_identity = _repository(anchor)
        target_root, target_identity = _repository(target_dir)
    except _GitFault as fault:
        return Comparison(
            UNDETERMINED,
            FAULT,
            None,
            None,
            f"git could not be asked which repositories the session's anchor and the target "
            f"are in ({fault})",
        )
    if anchor_identity is None or target_identity is None:
        return Comparison(
            UNDETERMINED,
            NONCOVERAGE,
            anchor_root,
            target_root,
            "the session's anchor or the target is not in a git repository, so there is no "
            "repository to compare",
        )
    if _same(anchor_identity, target_identity):
        return Comparison(
            SAME_REPO,
            None,
            anchor_root,
            target_root,
            "the target is the session's own repository",
        )
    return Comparison(
        DIVERGED,
        None,
        anchor_root,
        target_root,
        f"the target, {target_root}, is another repository than the session's anchor, "
        f"{anchor_root}",
    )


def clear(
    target_dir: Path | str,
    *,
    confirmed: bool,
    interactive: bool | None = None,
    dry_run: bool = False,
    stream: TextIO | None = None,
) -> Clearance | Refusal:
    """Let a change in `target_dir` go ahead, or refuse it.

    The session's anchor is read from the harness (:func:`session_anchor`).
    `confirmed` is the confirmation passed with the call (:data:`CONFIRM_OPTION`).
    `interactive` says whether a person can be asked; None asks only when
    standard input and `stream` are both terminals. A `dry_run` never asks: it
    ends as a run with nobody to ask would, and its refusal says so. What the
    guard says — a warning on a git fault, an advisory on a confirmed change,
    the question — goes to `stream`, standard error by default; a refusal's
    words are the caller's to say (:attr:`Refusal.reason`).
    """
    out = stream if stream is not None else sys.stderr
    directory = Path(target_dir).resolve()
    comparison = evaluate(directory, session_anchor())
    if comparison.verdict == SAME_REPO:
        return Clearance(directory, SAME_REPO, comparison)
    if comparison.verdict == UNDETERMINED:
        if comparison.undetermined_kind == FAULT:
            print(
                f"[warn] the cross-repository guard could not compare: {comparison.reason}; "
                "going on without it.",
                file=out,
            )
        return Clearance(directory, UNDETERMINED, comparison)
    if confirmed:
        print(
            f"[advisory] the cross-repository guard: {comparison.reason}; the change goes "
            f"ahead, confirmed by {CONFIRM_OPTION}.",
            file=out,
        )
        return Clearance(directory, FLAG, comparison)
    if dry_run:
        return Refusal(
            directory,
            comparison,
            f"the cross-repository guard refused: {comparison.reason}. A dry run does not ask; "
            "a run at a terminal would ask, and a run without one refuses (COR-039) — pass "
            f"{CONFIRM_OPTION} to preview the confirmed run.",
        )
    if not _at_a_terminal(interactive, out):
        return Refusal(
            directory,
            comparison,
            f"the cross-repository guard refused: {comparison.reason}, and there is no terminal "
            f"to ask (COR-039). Run it from a session rooted in {comparison.target}, or pass "
            f"{CONFIRM_OPTION} to confirm the change there.",
        )
    print(
        f"The cross-repository guard (COR-039): {comparison.reason}. That repository's own "
        "rules are not the ones this session carries.",
        file=out,
    )
    print("Make the change there anyway? [y/N] ", end="", file=out, flush=True)
    if _answer().strip().lower() in ("y", "yes"):
        return Clearance(directory, TERMINAL, comparison)
    return Refusal(
        directory,
        comparison,
        f"the cross-repository guard refused: {comparison.reason}, and the change was not "
        "confirmed at the terminal.",
    )


def require(clearance: Clearance | None, directory: Path | str) -> Path:
    """`directory`, resolved, once `clearance` is a clearance for it.

    Raises `TypeError` for anything but a clearance — none, or a refusal — and
    `ValueError` for a clearance of another directory: a change is made only
    where the guard looked.
    """
    given = cast(object, clearance)
    if not isinstance(given, Clearance):
        raise TypeError(f"a change needs a clearance from session_guard.clear, not {given!r}")
    where = Path(directory).resolve()
    if where != given.directory:
        raise ValueError(f"the clearance is for {given.directory}, not for {where}")
    return where


# ---- the comparison ------------------------------------------------------------


@dataclass(frozen=True)
class _Identity:
    """Which repository git acts on in a directory: its common directory,
    shared by the linked worktrees of one repository, and its normalised
    `origin`, shared by the clones of one remote (None without an `origin`)."""

    common_dir: Path
    origin: str | None


class _GitFault(Exception):
    """git could not be run, or did not answer in time."""


def _same(anchor: _Identity, target: _Identity) -> bool:
    if anchor.common_dir == target.common_dir:
        return True
    return anchor.origin is not None and anchor.origin == target.origin


def _repository(start: Path | str) -> tuple[Path | None, _Identity | None]:
    """The working tree `start` is in and its identity; (None, None) when it is
    in no git repository. Raises :class:`_GitFault` when git cannot be asked."""
    root = _toplevel(start)
    if root is None:
        return None, None
    answer = _git(root, "rev-parse", "--git-common-dir")
    common_text = answer.stdout.strip() if answer.returncode == 0 else ""
    if not common_text:
        return root, None
    common = Path(common_text)
    if not common.is_absolute():
        common = root / common
    try:
        common = common.resolve()
    except OSError:
        return root, None
    return root, _Identity(common, _origin(root))


def _toplevel(start: Path | str) -> Path | None:
    answer = _git(start, "rev-parse", "--show-toplevel")
    text = answer.stdout.strip() if answer.returncode == 0 else ""
    if not text:
        return None
    try:
        return Path(text).resolve()
    except OSError:
        return None


def _origin(root: Path) -> str | None:
    answer = _git(root, "remote", "get-url", "origin")
    text = answer.stdout.strip() if answer.returncode == 0 else ""
    return normalize_origin_url(text) if text else None


def _git(where: Path | str, *args: str) -> subprocess.CompletedProcess[str]:
    """`git -C <where> <args>`; a clean non-zero exit is an answer, a git that
    cannot run or does not answer in time a :class:`_GitFault`."""
    try:
        return subprocess.run(
            ["git", "-C", str(where), *args],
            capture_output=True,
            text=True,
            check=False,
            timeout=_GIT_TIMEOUT_SECONDS,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        raise _GitFault(f"git {' '.join(args)} could not run: {exc!r}") from exc


# The remote forms that name one repository three ways — scp-like ssh
# (`git@host:owner/repo.git`), an ssh URL (`ssh://git@host/owner/repo.git`) and
# https — collapse to `host/owner/repo`; anything else (a local path, another
# scheme) is only stripped of `.git` and case-folded.
_SCHEME_URL = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://(?P<rest>.*)$")
_SCP_LIKE = re.compile(r"^[^/]+:[^/].*$")


def normalize_origin_url(raw: str) -> str:
    """An `origin` remote as one form, so two clones of one repository compare
    equal: `host/owner/repo`, case-folded, for the ssh and https forms; any other
    remote stripped of a trailing `.git` and slashes and case-folded."""
    url = raw.strip()
    scheme = _SCHEME_URL.match(url)
    if scheme is not None:
        rest = scheme.group("rest").split("@", 1)[-1]
        host, slash, path = rest.partition("/")
        if slash and host and path:
            return f"{host.split(':', 1)[0]}/{_strip_git(path)}".casefold()
    elif _SCP_LIKE.match(url):
        user_host, _, path = url.partition(":")
        host = user_host.split("@", 1)[-1]
        if host and path:
            return f"{host}/{_strip_git(path)}".casefold()
    return _strip_git(url).casefold()


def _strip_git(path: str) -> str:
    path = path.rstrip("/")
    return path.removesuffix(".git")


# ---- the gate ----------------------------------------------------------------


def _at_a_terminal(interactive: bool | None, out: TextIO) -> bool:
    """A person can be asked: the question is written to `out` and the answer
    read from standard input, so both ends must be a terminal."""
    if interactive is not None:
        return interactive
    return _is_a_terminal(sys.stdin) and _is_a_terminal(out)


def _is_a_terminal(stream: object) -> bool:
    try:
        return bool(cast(TextIO, stream).isatty())
    except (AttributeError, ValueError, OSError):  # no stream, or a closed one
        return False


def _answer() -> str:
    """The operator's answer, one line from standard input; empty at its end."""
    try:
        return sys.stdin.readline()
    except (OSError, ValueError):
        return ""


def _document(comparison: Comparison, cleared: str | None) -> dict[str, Any]:
    """The guard as a document states it: `verdict`, the comparison alone;
    `cleared`, how the guard let the change through, or None when it refused."""
    return {
        "verdict": comparison.verdict,
        "undetermined_kind": comparison.undetermined_kind,
        "anchor": str(comparison.anchor) if comparison.anchor is not None else None,
        "target": str(comparison.target) if comparison.target is not None else None,
        "cleared": cleared,
    }
