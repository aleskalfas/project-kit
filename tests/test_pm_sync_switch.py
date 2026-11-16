"""The sync's switch, and the hold each merging command makes on turning it on
([project-management:DEC-072-sync-gives-missing-cards] point 3).

`sync_board.adds_with_no_terminal` lets a run of `sync-board` with no terminal add
cards where the board holds the state. It is off by default, off at once from the
working tree's configuration, and on only as the shared remote's copy of the
default branch holds it. Each command of the capability that merges into the
default branch holds a change that turns it on until the person authorises the
merge themselves; the sync honours the switch only while each does, which the scan
at the end holds.
"""

from __future__ import annotations

import base64
import json
import re
import subprocess
from pathlib import Path
from typing import Any

import pytest

from tests.in_process import CAPABILITIES, load

(sync_switch, default_branch) = load("project-management", "sync_switch", "default_branch")

SCRIPTS = CAPABILITIES / "project-management" / "scripts"
ON = "sync_board:\n  adds_with_no_terminal: true\n"
OFF = "sync_board:\n  adds_with_no_terminal: false\n"
CONFIG = ".pkit/capabilities/project-management/project/config.yaml"


@pytest.fixture(autouse=True)
def _fresh_answers(monkeypatch: pytest.MonkeyPatch) -> None:
    """The backbone's answer is asked once a run; each test is a run of its own."""
    monkeypatch.setattr(default_branch, "_read", {})


# --- the setting -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("config", "on"),
    [
        pytest.param({}, False, id="no-setting"),
        pytest.param({"sync_board": {}}, False, id="no-key"),
        pytest.param({"sync_board": {"adds_with_no_terminal": False}}, False, id="false"),
        pytest.param({"sync_board": {"adds_with_no_terminal": "yes"}}, False, id="not-true"),
        pytest.param({"sync_board": True}, False, id="not-a-block"),
        pytest.param({"sync_board": {"adds_with_no_terminal": True}}, True, id="true"),
    ],
)
def test_only_true_turns_it_on(config: dict, on: bool) -> None:
    assert sync_switch.on_in(config) is on


# --- a repository to read it from -------------------------------------------------


def _git(root: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True)
    return proc.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / CONFIG).parent.mkdir(parents=True)
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    _git(root, "config", "commit.gpgsign", "false")
    return root


def _capability(root: Path) -> Path:
    return root / ".pkit" / "capabilities" / "project-management"


def _commit(root: Path, text: str | None, message: str) -> str:
    path = root / CONFIG
    if text is None:
        if path.exists():
            _git(root, "rm", "-q", CONFIG)
    else:
        path.write_text(text, encoding="utf-8")
        _git(root, "add", CONFIG)
    _git(root, "commit", "-q", "--allow-empty", "-m", message)
    return _git(root, "rev-parse", "HEAD")


def _backbone(commit: str | None, resolved: str | None, *, ref: str = "origin/main"):
    """The backbone's answer to `pkit repository base --json`, its default branch
    resolved to ``commit`` by ``resolved``."""

    def run(argv: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        branch = {
            "name": "main",
            "source": "default",
            "ref": ref if commit else None,
            "commit": commit,
            "resolved": resolved if commit else None,
            "problem": None if commit else "no commit",
            "unborn": False,
        }
        base = {"ref": ref, "tip": commit, "fork": commit, "resolved": resolved, "problem": None}
        document = {"schema_version": 1, "default_branch": branch, "base": base}
        return subprocess.CompletedProcess(argv, 0, json.dumps(document), "")

    return run


def _unanswered(argv: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(argv, 1, "", "Error: the backbone broke\n")


# --- the switch, for one run --------------------------------------------------------


def test_it_is_on_where_the_remotes_copy_of_the_default_branch_holds_it(repo: Path) -> None:
    pushed = _commit(repo, ON, "on")

    switch = sync_switch.read(
        {"sync_board": {"adds_with_no_terminal": True}},
        _capability(repo),
        run=_backbone(pushed, "remote"),
    )

    assert switch.on is True
    assert f"origin/main at {pushed[:7]}" in switch.said


def test_it_is_off_at_once_from_the_working_trees_configuration(repo: Path) -> None:
    _commit(repo, ON, "on")

    def not_asked(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("the working tree turns it off before the backbone is asked")

    switch = sync_switch.read({}, _capability(repo), run=not_asked)

    assert switch.on is False
    assert "this working tree" in switch.said


def test_a_local_commit_nobody_pushed_does_not_turn_it_on(repo: Path) -> None:
    """The remote's copy is read, never the local branch's commit: a commit made in
    the clone and not pushed counts for nothing."""
    pushed = _commit(repo, OFF, "off")
    _commit(repo, ON, "on, not pushed")

    switch = sync_switch.read(
        {"sync_board": {"adds_with_no_terminal": True}},
        _capability(repo),
        run=_backbone(pushed, "remote"),
    )

    assert switch.on is False
    assert "does not turn on" in switch.said


@pytest.mark.parametrize(
    ("resolved", "has_commit"),
    [
        pytest.param("local", True, id="the-local-branch"),
        pytest.param("remote", False, id="no-commit"),
    ],
)
def test_it_is_off_where_the_default_branch_is_not_the_remotes_commit(
    repo: Path, resolved: str, has_commit: bool
) -> None:
    head = _commit(repo, ON, "on")

    switch = sync_switch.read(
        {"sync_board": {"adds_with_no_terminal": True}},
        _capability(repo),
        run=_backbone(head if has_commit else None, resolved, ref="main"),
    )

    assert switch.on is False
    assert "not to the shared remote's copy" in switch.said


def test_it_is_off_where_the_backbone_does_not_answer(repo: Path) -> None:
    _commit(repo, ON, "on")

    switch = sync_switch.read(
        {"sync_board": {"adds_with_no_terminal": True}}, _capability(repo), run=_unanswered
    )

    assert switch.on is False
    assert "could not be read" in switch.said


def test_it_is_off_where_the_remotes_copy_holds_no_configuration(repo: Path) -> None:
    pushed = _commit(repo, None, "no configuration")

    switch = sync_switch.read(
        {"sync_board": {"adds_with_no_terminal": True}},
        _capability(repo),
        run=_backbone(pushed, "remote"),
    )

    assert switch.on is False


# --- the hold, from git objects -----------------------------------------------------


@pytest.mark.parametrize(
    ("before", "after", "turns_on"),
    [
        pytest.param(OFF, ON, True, id="off-to-on"),
        pytest.param(None, ON, True, id="absent-to-on"),
        pytest.param(ON, ON + "# a comment\n", False, id="on-already"),
        pytest.param(ON, OFF, False, id="on-to-off"),
        pytest.param(OFF, OFF + "other: 1\n", False, id="another-setting"),
    ],
)
def test_between_commits_holds_only_a_change_that_turns_it_on(
    repo: Path, before: str | None, after: str, turns_on: bool
) -> None:
    fork = _commit(repo, before, "base")
    head = _commit(repo, after, "change")

    hold = sync_switch.between_commits(fork, head, _capability(repo))

    assert (hold.turns_on, hold.held) == (turns_on, turns_on)


def test_a_change_that_leaves_the_configuration_as_it_was_is_not_read(repo: Path) -> None:
    fork = _commit(repo, ON, "base")
    head = _commit(repo, ON, "unrelated")
    calls: list[list[str]] = []

    def git(args: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)

    assert sync_switch.between_commits(fork, head, _capability(repo), git=git).held is False
    assert [args[0] for args in calls] == ["diff"]


@pytest.mark.parametrize(
    ("before", "after"),
    [pytest.param("", "abc", id="no-fork"), pytest.param("0" * 40, "1" * 40, id="no-objects")],
)
def test_a_change_git_cannot_read_is_held(repo: Path, before: str, after: str) -> None:
    hold = sync_switch.between_commits(before, after, _capability(repo))
    assert hold.held is True and hold.turns_on is False and hold.unread


def test_a_configuration_that_does_not_parse_is_held(repo: Path) -> None:
    fork = _commit(repo, OFF, "base")
    head = _commit(repo, "sync_board: [unclosed\n", "broken")

    hold = sync_switch.between_commits(fork, head, _capability(repo))

    assert hold.held is True and "does not parse" in hold.unread


# --- the hold, from the host --------------------------------------------------------


def _host(files: dict[str, str | None], *, fails: str | None = None):
    """The host's contents endpoint: `files` maps a ref to the configuration's text
    there, None for no such file."""
    asked: list[str] = []

    def gh(argv: list[str], config: dict, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        path = argv[2]
        match = re.fullmatch(r"repos/\{owner\}/\{repo\}/contents/(.+)\?ref=(.+)", path)
        assert match and match.group(1) == CONFIG, argv
        ref = match.group(2)
        asked.append(ref)
        if fails is not None:
            return subprocess.CompletedProcess(argv, 1, "", fails)
        text = files.get(ref)
        if text is None:
            body = json.dumps({"message": "Not Found", "status": "404"})
            return subprocess.CompletedProcess(argv, 1, body, "gh: Not Found (HTTP 404)")
        content = base64.b64encode(text.encode()).decode()
        return subprocess.CompletedProcess(
            argv, 0, json.dumps({"content": content, "encoding": "base64"}), ""
        )

    return gh, asked


@pytest.mark.parametrize(
    ("files", "held", "reads"),
    [
        pytest.param({"head": ON, "main": OFF}, True, ["head", "main"], id="turns-it-on"),
        pytest.param({"head": ON, "main": None}, True, ["head", "main"], id="base-has-none"),
        pytest.param({"head": ON, "main": ON}, False, ["head", "main"], id="on-already"),
        pytest.param({"head": OFF, "main": ON}, False, ["head"], id="off-at-the-head"),
        pytest.param({"head": None, "main": None}, False, ["head"], id="no-file-at-the-head"),
    ],
)
def test_on_host_holds_a_head_that_turns_it_on_against_the_base_tip(
    repo: Path, files: dict, held: bool, reads: list[str]
) -> None:
    gh, asked = _host(files)

    hold = sync_switch.on_host("head", "main", _capability(repo), {}, gh_call=gh)

    assert hold.held is held and hold.turns_on is held
    assert asked == reads


def test_a_host_that_does_not_answer_is_held(repo: Path) -> None:
    gh, _ = _host({}, fails="HTTP 502: Bad Gateway")

    hold = sync_switch.on_host("head", "main", _capability(repo), {}, gh_call=gh)

    assert hold.held is True and "HTTP 502" in hold.unread


def test_a_head_or_base_not_read_is_held(repo: Path) -> None:
    def not_asked(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("nothing to ask the host for")

    assert sync_switch.on_host("", "main", _capability(repo), {}, gh_call=not_asked).held
    assert sync_switch.on_host("head", "", _capability(repo), {}, gh_call=not_asked).held


# --- what the hold says ---------------------------------------------------------


def test_the_hold_says_in_plain_words_what_turning_it_on_means() -> None:
    said = sync_switch.Hold(turns_on=True).said()
    assert said.startswith("This change turns on `sync_board.adds_with_no_terminal`.")
    assert "with nobody at a terminal" in said
    assert "every command then reads that Status as the issue's position" in said
    assert "for every session that runs the sync in this project" in said
    refusal = sync_switch.Hold(unread="git broke").refusal("PR #7 at abc1234", "pkit pm x 7")
    assert "could not be read (git broke)" in refusal
    assert "a `--yes`, does not cover such a change" in refusal
    assert "runs `pkit pm x 7` at a terminal" in refusal


# --- every merging command holds (DEC-072 point 3) --------------------------------


def _merging_scripts() -> set[str]:
    """Each script of the capability that merges a pull request: one that lands
    through `pr_merge.land`, the one landing, or composes a script that does."""
    merging = {
        path.stem
        for path in SCRIPTS.glob("*.py")
        if "pr_merge.land(" in path.read_text(encoding="utf-8")
    }
    composing = {
        path.stem
        for path in SCRIPTS.glob("*.py")
        if any(
            f"{name.replace('-', '_')}.run(" in path.read_text(encoding="utf-8") for name in merging
        )
    }
    return merging | composing


def test_the_commands_that_hold_are_every_command_that_merges() -> None:
    """The sync honours the switch only while every merging command holds; a new
    one that lands a merge fails here until it holds too."""
    assert _merging_scripts() == set(sync_switch.HOLDING)


@pytest.mark.parametrize("name", sync_switch.HOLDING)
def test_each_merging_command_reads_the_hold(name: str) -> None:
    text = (SCRIPTS / f"{name}.py").read_text(encoding="utf-8")
    assert "sync_switch" in text
    assert re.search(r"sync_switch\.(on_host|between_commits)\(", text)
