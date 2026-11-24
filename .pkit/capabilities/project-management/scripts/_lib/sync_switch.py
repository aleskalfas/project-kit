"""The project's switch that lets a run of `sync-board` with no terminal add cards
where the board holds the state, and the hold every merge makes on turning it on
([project-management:DEC-072-sync-gives-missing-cards] point 3).

Where the board holds the state, a card `sync-board` adds carries no Status, so
the issue's position stays undetermined until a person sets it. Yet a board's own
automation may set a Status when a card is added, and every command would read it
as the issue's position. So the sync adds cards there only in a run at a terminal,
or where this switch is on: the person's consent to that automation, for every
session that runs the sync in the project.

The switch is the setting :data:`NAME` in this capability's project configuration.
:func:`read` says whether it is on for one run of the sync. It is:

* off by default, and off where the configuration holds no such setting, or holds
  anything but `true` there;
* off at once, from the configuration of the working tree the run starts from;
* on only as the shared remote's copy of the default branch holds it: the
  remote-tracking reference the backbone resolves the default branch to (COR-054
  point 2), never a local branch. So it is off in a project with no remote, where
  the backbone resolves the default branch to the local branch, and off where it
  resolves to no commit, or does not answer.

Only a change the person authorises turns it on. Each command of this capability
that merges a change into the default branch, :data:`HOLDING`, holds a change that
turns it on until the person authorises that merge themselves, at a terminal: an
authorisation of merges given up front, a `--yes`, does not cover it. :class:`Hold`
is what one merge found, read from git objects at two commits
(:func:`between_commits`, the landing command's read, which holds both) or from the
host at two refs (:func:`on_host`, the merge commands' read, whose clone may not).
Whether the change turns the switch on that cannot be read is held as one that
does. The sync honours the switch only while every command in :data:`HOLDING` makes
that hold, which `tests/test_pm_sync_switch.py` holds of each.

What stays open, as DEC-072 point 3 states it: a merge outside these commands, or a
direct commit to the default branch, passes no hold; a terminal tells only that one
is attached, not that a person watches; and the remote-tracking reference is what
the clone last fetched, which a session can write by hand.
"""

from __future__ import annotations

import base64
import json
import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from _lib import backbone, default_branch
from _lib.gh import gh_run

#: The block of this capability's project configuration the switch is set in, and
#: the setting in it.
BLOCK = "sync_board"
SETTING = "adds_with_no_terminal"
#: The switch as a message names it.
NAME = f"{BLOCK}.{SETTING}"

#: The capability's project configuration, from the capability's own directory.
CONFIG_RELATIVE = Path("project") / "config.yaml"

#: The commands of this capability that merge a change into the default branch.
#: Each holds a change that turns the switch on: `done-work` and `merge-pr` before
#: their merge, and `land-work`, which merges through `done-work`, before its own
#: `ready:` line, the prompt or the merge.
HOLDING = ("done-work", "land-work", "merge-pr")

#: What turning the switch on means, in plain words, for the person who authorises
#: the merge that turns it on.
MEANS = (
    f"Turning on `{NAME}` lets `pkit pm sync-board` add the missing cards with nobody at "
    "a terminal, where the board holds the state. The sync writes no Status on a card it "
    "adds, but the board's own automation may set one when the card is added, and every "
    "command then reads that Status as the issue's position, though nobody chose it. Such "
    "a run names each such card only in its own output. It consents for every session "
    "that runs the sync in this project, a person's or an agent's "
    "(project-management DEC-072 point 3)."
)

#: How long a git read waits.
TIMEOUT = 60

#: A git call: its arguments after `git`, run in the repository.
Git = Callable[[list[str]], "subprocess.CompletedProcess[str]"]
#: A `gh` call, as `_lib.gh.gh_run` makes one.
GhCall = Callable[..., "subprocess.CompletedProcess[str]"]


def on_in(config: Mapping[str, Any] | None) -> bool:
    """Whether ``config``, a project configuration, turns the switch on: only where
    its setting is `true`. Anything else, or no setting, is off. No I/O."""
    block = config.get(BLOCK) if isinstance(config, Mapping) else None
    return isinstance(block, Mapping) and block.get(SETTING) is True


# ---- the switch, for one run of the sync -----------------------------------------


@dataclass(frozen=True)
class Switch:
    """Whether the switch is on for one run, and where it was read or why it is off,
    on one line."""

    on: bool
    said: str


def read(
    config: Mapping[str, Any],
    capability_root: Path,
    *,
    run: Callable[..., Any] = backbone.run,
    git: Git | None = None,
) -> Switch:
    """Whether the switch is on for a run that starts from the working tree whose
    configuration is ``config``: on only where that configuration and the shared
    remote's copy of the default branch both turn it on. Nothing is raised: a read
    that fails is the switch off, with why."""
    if not on_in(config):
        return Switch(False, f"`{NAME}` is not on in this working tree's project/config.yaml")
    try:
        branch = default_branch.read(cwd=repo_root(capability_root), run=run).default_branch
    except default_branch.Unanswered as exc:
        return Switch(False, f"which commit the default branch is could not be read: {exc}")
    if branch.commit is None or branch.resolved != "remote":
        where = branch.ref or branch.name
        return Switch(
            False,
            f"the default branch resolves to {where}, not to the shared remote's copy of it, "
            f"and `{NAME}` counts only as that copy holds it",
        )
    at = f"{branch.ref} at {branch.commit[:7]}"
    try:
        text = text_at(capability_root, branch.commit, git=git)
    except Unread as exc:
        return Switch(False, f"its setting could not be read at {at}: {exc}")
    try:
        held = config_of(text)
    except Unread as exc:
        return Switch(False, f"its setting could not be read at {at}: {exc}")
    if not on_in(held):
        return Switch(False, f"{at} does not turn on `{NAME}`")
    return Switch(True, f"`{NAME}` is on, as {at} holds it")


# ---- the hold at a merge --------------------------------------------------------


@dataclass(frozen=True)
class Hold:
    """What a merge found of the switch: whether the change turns it on, or why
    that could not be read, which is held as a change that does."""

    turns_on: bool = False
    unread: str = ""

    @property
    def held(self) -> bool:
        """Whether the merge waits for the person to authorise it themselves."""
        return self.turns_on or bool(self.unread)

    def said(self) -> str:
        """The hold as the line above the question, or the refusal, says it."""
        if self.turns_on:
            return f"This change turns on `{NAME}`. {MEANS}"
        return (
            f"Whether this change turns on `{NAME}` could not be read ({self.unread}), so "
            f"the merge is held as for a change that does. {MEANS}"
        )

    def refusal(self, named: str, command: str) -> str:
        """The refusal of a merge the hold stops: one authorised up front, or one
        with no terminal to ask at. ``named`` is what it merges, and ``command``
        the run the person makes at a terminal to authorise it themselves."""
        return (
            f"error: refusing to merge {named}. {self.said()} An authorisation of merges "
            "given up front, a `--yes`, does not cover such a change, and a run with no "
            "terminal has nobody to ask. Nothing was posted, moved or merged. The person "
            f"runs `{command}` at a terminal, and authorises the merge there themselves."
        )


#: A merge whose change does not turn the switch on.
NOT_HELD = Hold()


class Unread(Exception):
    """A configuration that could not be read, with why."""


def between_commits(
    before: str, after: str, capability_root: Path, *, git: Git | None = None
) -> Hold:
    """Whether the change from commit ``before`` to commit ``after`` turns the switch
    on, read from git objects: where the head left its base, and the head. A change
    that leaves the configuration as it was turns nothing on, and is not read."""
    if not before or not after:
        return Hold(unread="no commit was named that the head left its base at")
    runner = git or _git(repo_root(capability_root))
    path = config_path(capability_root)
    same = _call(runner, ["diff", "--quiet", before, after, "--", path])
    if same is not None and same.returncode == 0:
        return NOT_HELD
    try:
        was = config_of(text_at(capability_root, before, git=runner))
        now = config_of(text_at(capability_root, after, git=runner))
    except Unread as exc:
        return Hold(unread=str(exc))
    return Hold(turns_on=on_in(now) and not on_in(was))


def on_host(
    head: str,
    base: str,
    capability_root: Path,
    config: dict[str, Any],
    *,
    gh_call: GhCall | None = None,
) -> Hold:
    """Whether merging the commit ``head`` into the branch ``base`` turns the switch
    on, read from the host: on at the head, and not on at the base's tip. A change
    the base made since the head left it can make that hold a merge that turns
    nothing on, never let through one that does."""
    if not head or not base:
        return Hold(unread="the pull request's head or its base could not be read")
    try:
        now = config_of(_hosted(head, capability_root, config, gh_call))
        if not on_in(now):
            return NOT_HELD
        was = config_of(_hosted(base, capability_root, config, gh_call))
    except Unread as exc:
        return Hold(unread=str(exc))
    return Hold(turns_on=not on_in(was))


# ---- reading a configuration ---------------------------------------------------


def repo_root(capability_root: Path) -> Path:
    """The repository the capability is installed in."""
    return capability_root.parents[2]


def config_path(capability_root: Path) -> str:
    """The capability's project configuration, as a path from the repository's root."""
    root = repo_root(capability_root)
    return (capability_root / CONFIG_RELATIVE).relative_to(root).as_posix()


def config_of(text: str | None) -> Mapping[str, Any]:
    """The configuration ``text`` holds; empty for no file. Raises Unread for text
    that is no mapping."""
    if text is None:
        return {}
    try:
        data = YAML(typ="safe").load(text)
    except YAMLError as exc:
        raise Unread(f"project/config.yaml does not parse: {' '.join(str(exc).split())}") from exc
    if data is None:
        return {}
    if not isinstance(data, Mapping):
        raise Unread("project/config.yaml is not a mapping")
    return data


def text_at(capability_root: Path, commit: str, *, git: Git | None = None) -> str | None:
    """The text of the capability's project configuration at ``commit``, or None
    where the commit holds no such file. Raises Unread where git cannot say."""
    runner = git or _git(repo_root(capability_root))
    path = config_path(capability_root)
    listed = _call(runner, ["ls-tree", "-z", "--full-tree", "--name-only", commit, "--", path])
    if listed is None or listed.returncode != 0:
        raise Unread(f"git could not list {path} at {commit[:7]}")
    if path not in (listed.stdout or "").split("\0"):
        return None
    shown = _call(runner, ["cat-file", "blob", f"{commit}:{path}"])
    if shown is None or shown.returncode != 0:
        raise Unread(f"git could not read {path} at {commit[:7]}")
    return shown.stdout or ""


def _hosted(
    ref: str, capability_root: Path, config: dict[str, Any], gh_call: GhCall | None
) -> str | None:
    """The text of the capability's project configuration at ``ref`` on the host,
    or None where the host answers that the file is not there. Raises Unread for
    any other answer."""
    path = config_path(capability_root)
    argv = ["gh", "api", f"repos/{{owner}}/{{repo}}/contents/{path}?ref={ref}"]
    try:
        proc = (gh_call or gh_run)(argv, config, check=False)
    except FileNotFoundError as exc:
        raise Unread("`gh` is not on PATH") from exc
    payload = _json(proc.stdout or "")
    message = payload.get("message") if isinstance(payload, dict) else None
    if proc.returncode != 0:
        if message == "Not Found":
            return None
        said = message or " ".join((proc.stderr or "").split()) or f"exit {proc.returncode}"
        raise Unread(f"{path} at {ref[:12]} could not be read from the host: {said}")
    content = payload.get("content") if isinstance(payload, dict) else None
    if not isinstance(content, str) or payload.get("encoding") != "base64":
        raise Unread(f"the host's answer for {path} at {ref[:12]} carries no file")
    try:
        return base64.b64decode(content).decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exc:
        raise Unread(f"{path} at {ref[:12]} is not UTF-8 text") from exc


def _git(root: Path) -> Git:
    def run(args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=TIMEOUT,
        )

    return run


def _call(runner: Git, args: list[str]) -> subprocess.CompletedProcess[str] | None:
    """One git call, or None where it could not be run."""
    try:
        return runner(args)
    except (OSError, subprocess.TimeoutExpired):
        return None


def _json(text: str) -> Any:
    try:
        return json.loads(text)
    except ValueError:
        return None
