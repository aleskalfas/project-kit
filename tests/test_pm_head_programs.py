"""Tests for `_lib/head_programs.py` and `_lib/escaped_output.py` (project-management
DEC-067): which pull request heads may start programs, and what a command prints.

What `land-work` makes of the test is tested with the command, through a real change
check (`tests/test_pm_land_work.py`). The move to review and the review command are held
here, on a head that replaced its resolver, through a real backbone.
"""

from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest

from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.anchor_kind_capabilities import RESOLVER, RESOLVING, register_kinds
from tests.friction_documents import CONFIG, SOURCE, document, friction_config, guide

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))
from _lib import audit_log, escaped_output, head_programs  # noqa: E402
from _lib.comment_log import LogComment, LogRead  # noqa: E402

HEAD = "a" * 40
BUILT = "b" * 40
OTHER = "c" * 40
ROOT = Path("/capability")
ISSUE = 42
PR = 99


def _script(name: str, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, SCRIPTS_DIR / name)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def rw() -> ModuleType:
    return _script("review-work.py", "pm_head_programs_review_work")


@pytest.fixture(scope="module")
def rpr() -> ModuleType:
    return _script("review-pr.py", "pm_head_programs_review_pr")


# ---- the test ---------------------------------------------------------------


def _take(placed: object, **overrides: Any) -> head_programs.Standing:
    arguments: dict[str, Any] = {
        "issue": ISSUE,
        "base": "main",
        "source": None,
        "capability_root": ROOT,
        "config": {},
    }
    return head_programs.take_test(HEAD, placed, **{**arguments, **overrides})


@pytest.mark.parametrize(
    ("placed", "why"),
    [
        pytest.param(True, "another repository", id="a-fork"),
        pytest.param(None, "the host did not say", id="not-said"),
        pytest.param("false", "the host did not say", id="a-word-for-false"),
        pytest.param(0, "the host did not say", id="falsy"),
    ],
)
def test_only_the_host_s_own_false_places_a_head(placed, why, monkeypatch) -> None:
    """A reading that does not say is never a pass (DEC-067 point 1), and the records are
    not read for a head already from elsewhere."""

    def unread(*_args: Any) -> frozenset[str]:
        raise AssertionError("the build records were read")

    monkeypatch.setattr(head_programs, "build_commits", unread)
    found = _take(placed)
    assert why in found.elsewhere and not found.passes and not found.may_start


def test_a_head_the_host_places_with_no_build_passes(monkeypatch) -> None:
    monkeypatch.setattr(head_programs, "build_commits", lambda *a: frozenset())
    found = _take(False)
    assert found.passes and found.may_start and found.head == HEAD


def test_records_that_cannot_be_read_fail_the_test(monkeypatch) -> None:
    monkeypatch.setattr(head_programs, "build_commits", lambda *a: "gh exited 1")
    assert "could not be read (gh exited 1)" in _take(False).elsewhere


def test_a_head_holding_a_build_s_commit_fails_and_one_without_passes(monkeypatch) -> None:
    monkeypatch.setattr(head_programs, "build_commits", lambda *a: frozenset({BUILT}))
    monkeypatch.setattr(head_programs, "_held", lambda *a: (BUILT,))
    assert f"sandboxed build ({BUILT[:7]})" in _take(False).elsewhere
    monkeypatch.setattr(head_programs, "_held", lambda *a: ())
    assert _take(False).passes


def test_what_held_cannot_read_fails_the_test(monkeypatch) -> None:
    monkeypatch.setattr(head_programs, "build_commits", lambda *a: frozenset({BUILT}))
    monkeypatch.setattr(head_programs, "_held", lambda *a: "the base could not be fetched")
    assert "the base could not be fetched" in _take(False).elsewhere


def test_a_person_s_word_lets_a_head_start_and_leaves_the_test_as_it_was() -> None:
    """An earlier head reads what the test found, not the word (DEC-067 point 4)."""
    named = head_programs.Standing(HEAD, elsewhere="a fork's", named=True)
    assert named.may_start and not named.passes


def test_a_head_no_test_was_taken_on_starts_nothing() -> None:
    assert not head_programs.UNTAKEN.may_start


# ---- the build records --------------------------------------------------------


def _seats(monkeypatch: pytest.MonkeyPatch, tree: Any) -> None:
    monkeypatch.setattr(head_programs.topology, "read", lambda _root: tree)


def _log(monkeypatch: pytest.MonkeyPatch, read: LogRead) -> None:
    monkeypatch.setattr(head_programs.comment_log, "read_log", lambda _n, _gh: read)


def _hand_back(commits: str) -> LogComment:
    event = audit_log.Event(head_programs.BUILD_EVENT, (("commits", commits),))
    return LogComment(1, "someone", "2026-11-06T00:00:00Z", audit_log.stamp(event))


def _no_log(_number: int, _gh: Any) -> LogRead:
    raise AssertionError("the Task's log was read")


def test_a_project_with_no_seats_has_no_builds(monkeypatch) -> None:
    monkeypatch.setattr(head_programs.comment_log, "read_log", _no_log)
    _seats(monkeypatch, None)
    assert head_programs.build_commits(ISSUE, ROOT, {}) == frozenset()
    _seats(monkeypatch, SimpleNamespace(not_understood=(), seats=()))
    assert head_programs.build_commits(ISSUE, ROOT, {}) == frozenset()


def test_a_topology_that_cannot_be_read_is_no_answer_of_none(monkeypatch) -> None:
    def unresolved(_root: Path) -> Any:
        raise head_programs.topology.Unresolved("no default branch")

    monkeypatch.setattr(head_programs.topology, "read", unresolved)
    assert head_programs.build_commits(ISSUE, ROOT, {}) == "no default branch"
    _seats(monkeypatch, SimpleNamespace(not_understood=("a seat",), seats=()))
    assert "in full" in str(head_programs.build_commits(ISSUE, ROOT, {}))


def test_the_task_s_log_names_the_build_s_commits(monkeypatch) -> None:
    """Whoever posted it: a stranger's stamp can only stop a run. Any other event, and a
    comment with no stamp, names nothing."""
    _seats(monkeypatch, SimpleNamespace(not_understood=(), seats=("a seat",)))
    other = audit_log.Event("claim", (("commits", OTHER),))
    comments = (
        _hand_back(f"{HEAD},{BUILT}"),
        LogComment(2, None, "2026-11-06T00:00:00Z", audit_log.stamp(other)),
        LogComment(3, None, "2026-11-06T00:00:00Z", f"commits={OTHER}"),
    )
    _log(monkeypatch, LogRead(True, comments))
    assert head_programs.build_commits(ISSUE, ROOT, {}) == frozenset({HEAD, BUILT})


def test_a_log_read_in_part_is_no_answer_of_none(monkeypatch) -> None:
    _seats(monkeypatch, SimpleNamespace(not_understood=(), seats=("a seat",)))
    _log(monkeypatch, LogRead(False, cause="`gh` is not on PATH"))
    assert head_programs.build_commits(ISSUE, ROOT, {}) == "`gh` is not on PATH"


# ---- which pull request -------------------------------------------------------


def test_one_open_reads_the_branch_s_open_pull_request() -> None:
    prs = [
        {"number": 1, "headRefName": "feat/1-x", "state": "CLOSED"},
        {"number": 2, "headRefName": "feat/1-x", "state": "OPEN"},
        {"number": 3, "headRefName": "feat/1-other", "state": "OPEN"},
    ]
    found = head_programs.one_open(prs, "feat/1-x")
    assert found is not None and found["number"] == 2
    assert head_programs.one_open(prs, "feat/9-none") is None


def test_two_open_pull_requests_on_a_branch_s_name_are_named() -> None:
    prs = [{"number": 1, "headRefName": "feat/1-x"}, {"number": 2, "headRefName": "feat/1-x"}]
    with pytest.raises(head_programs.TwoOpen, match="#1 and #2 share the branch name feat/1-x"):
        head_programs.one_open(prs, "feat/1-x")


def test_repository_names_where_the_head_comes_from() -> None:
    pr = {"headRepository": {"name": "kit"}, "headRepositoryOwner": {"login": "someone"}}
    assert head_programs.repository(pr) == "someone/kit"
    assert head_programs.repository({"headRepository": None}) == ""


# ---- the question -------------------------------------------------------------


@pytest.fixture
def word(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Each comment a word leaves, posted through a host that takes it."""
    posted: list[str] = []

    def post(_subject: str, _number: int, key: str, body: str, _config: Any, **_: Any) -> bool:
        assert key in body.splitlines()
        posted.append(body)
        return True

    monkeypatch.setattr(head_programs, "post_audit_once", post)
    monkeypatch.setattr(
        head_programs,
        "resolve_invoker_identity",
        lambda **_k: SimpleNamespace(github_login="octocat", email=None),
    )
    monkeypatch.setattr(
        head_programs,
        "render_audit_comment",
        lambda _root, invoker, reason: f"{invoker.github_login}: {reason}",
    )
    return posted


def _ask(monkeypatch: pytest.MonkeyPatch, reply: str | None) -> head_programs.Standing:
    def typed(_prompt: str = "") -> str:
        if reply is None:
            raise EOFError
        return reply

    monkeypatch.setattr("builtins.input", typed)
    return head_programs.ask(
        head_programs.Standing(HEAD, elsewhere="a fork's"),
        command="land-work",
        number=PR,
        source_repository="someone/kit",
        capability_root=ROOT,
        config={},
    )


def test_the_question_says_what_naming_the_head_starts(word, monkeypatch, capsys) -> None:
    """The commit, where it comes from, that its programs would start under the person's
    account, that reading its diff needs no checkout (DEC-067 point 4)."""
    found = _ask(monkeypatch, HEAD[:7])
    out = capsys.readouterr().out
    assert found.named and found.may_start
    assert HEAD in out and "someone/kit" in out
    assert "under your account" in out and f"`gh pr diff {PR}`" in out
    (body,) = word
    assert HEAD in body and "`land-work`" in body and "octocat" in body


@pytest.mark.parametrize(
    "reply",
    [
        pytest.param("yes", id="a-yes"),
        pytest.param("", id="nothing"),
        pytest.param(HEAD, id="the-full-id"),
        pytest.param(None, id="end-of-input"),
    ],
)
def test_only_the_short_id_names_the_head(reply, word, monkeypatch) -> None:
    found = _ask(monkeypatch, reply)
    assert not found.named and not found.may_start and word == []


def test_each_word_is_a_comment_of_its_own(word, monkeypatch) -> None:
    """A second run names the head again, and leaves a second comment."""
    _ask(monkeypatch, HEAD[:7])
    _ask(monkeypatch, HEAD[:7])
    assert len(word) == 2 and word[0] != word[1]


def test_no_comment_posted_starts_nothing(word, monkeypatch, capsys) -> None:
    monkeypatch.setattr(head_programs, "post_audit_once", lambda *a, **k: False)
    found = _ask(monkeypatch, HEAD[:7])
    assert not found.may_start
    assert "could not be posted" in capsys.readouterr().out


def test_the_comment_is_posted_whatever_the_audit_projection_says(
    word, monkeypatch, capsys
) -> None:
    """With no comment nothing starts, so `audit.projection: off` does not silence it."""
    monkeypatch.setattr("builtins.input", lambda _prompt="": HEAD[:7])
    found = head_programs.ask(
        head_programs.Standing(HEAD, elsewhere="a fork's"),
        command="review-pr",
        number=PR,
        source_repository="",
        capability_root=ROOT,
        config={"audit": {"projection": "off"}},
    )
    assert found.named and len(word) == 1
    assert "one the host does not name" in capsys.readouterr().out


# ---- what a command prints ----------------------------------------------------


@pytest.mark.parametrize(
    ("text", "escaped"),
    [
        pytest.param("plain — words\n", "plain — words\n", id="plain"),
        pytest.param("a\x1b[2Kb\n", "a\\x1b[2Kb\n", id="a-control-sequence"),
        pytest.param("a‮b​c", "a\\u202eb\\u200bc", id="bidi-and-zero-width"),
        pytest.param("one\ntwo\n\nthree", "one\ntwo\n\nthree", id="lines-kept"),
        pytest.param("one\r\ntwo\r\n", "one\r\ntwo\r\n", id="a-host-s-line-ends-kept"),
        pytest.param("over\rwrite\n", "over\\rwrite\n", id="a-carriage-return-alone"),
        pytest.param("a\tb\n", "a\\tb\n", id="a-tab"),
    ],
)
def test_lines_keep_their_ends_and_escape_the_rest(text, escaped) -> None:
    assert escaped_output.lines(text) == escaped


def test_escaping_covers_both_streams_and_restores_them(capsys) -> None:
    before = sys.stdout, sys.stderr

    @escaped_output.escaping
    def main() -> int:
        print("out\x1b[A")
        print("err\x1b[A", file=sys.stderr)
        sys.stdout.writelines(["a\x07", "b\n"])
        return 3

    assert main() == 3
    assert (sys.stdout, sys.stderr) == before
    captured = capsys.readouterr()
    assert captured.out == "out\\x1b[A\na\\x07b\n"
    assert captured.err == "err\\x1b[A\n"


def test_a_command_that_exits_leaves_the_streams_restored() -> None:
    before = sys.stdout, sys.stderr

    @escaped_output.escaping
    def main() -> int:
        raise SystemExit(2)

    with pytest.raises(SystemExit):
        main()
    assert (sys.stdout, sys.stderr) == before


def test_an_exception_no_command_caught_is_reported_escaped() -> None:
    """Python reports it once the streams are restored, so a real run shows what it
    prints, and it can quote outside text as any line can."""
    program = (
        f"import sys; sys.path.insert(0, {str(SCRIPTS_DIR)!r})\n"
        "from _lib.escaped_output import escaping\n"
        "@escaping\n"
        "def main():\n"
        "    raise ValueError('a' + chr(27) + '[2Kb')\n"
        "main()\n"
    )
    run = subprocess.run(
        [sys.executable, "-c", program], capture_output=True, text=True, check=False
    )
    assert run.returncode == 1
    assert "ValueError: a\\x1b[2Kb\n" in run.stderr
    assert "\x1b" not in run.stderr


def test_machine_readable_output_keeps_its_bytes(capsys) -> None:
    told = {"title": "a\x1b[2Kb\nc\ttabbed‮", "n": 1}
    text = json.dumps(told, indent=2)

    @escaped_output.escaping
    def main() -> None:
        print(text)

    main()
    out = capsys.readouterr().out
    assert out == text + "\n"
    assert json.loads(out) == told


def test_a_prompt_is_escaped_with_the_rest(monkeypatch, capsys) -> None:
    """`input` writes its prompt to a stream that names no descriptor, as a terminal's
    prompt must not pass around the escaping."""
    stream = escaped_output._Escaping(io.StringIO())
    with pytest.raises(io.UnsupportedOperation):
        stream.fileno()
    monkeypatch.setattr(sys, "stdin", io.StringIO("typed\n"))

    @escaped_output.escaping
    def main() -> str:
        return input("name\x1b[2K: ")

    assert main() == "typed"
    assert capsys.readouterr().out == "name\\x1b[2K: "


@pytest.mark.parametrize(
    "name",
    [
        "land-work.py",
        "review-work.py",
        "review-pr.py",
        "show-pr.py",
        "open-pr.py",
        "done-work.py",
        "merge-pr.py",
        "check-doc-mapping.py",
        "move-issue.py",
        "close-issue.py",
    ],
)
def test_each_command_the_record_names_prints_through_the_escaping(name) -> None:
    """DEC-067 point 7's list: a command left out would print a head's words as they came.
    The last two are `review-work`'s and `done-work`'s children, which write to the
    terminal past their parent's streams, so each escapes what it prints itself."""
    source = (SCRIPTS_DIR / name).read_text(encoding="utf-8")
    assert "@escaping\ndef main(" in source


# ---- the move to review and the review command, through a real backbone ---------


def _head_replacing_its_resolver(
    make_adopter_repo: MakeAdopterRepo, ran: Path
) -> tuple[AdopterRepo, str, Path]:
    """A change whose head replaces the resolver its anchors need with one that leaves
    `ran` behind. The clone is on `main`, a tree of the person's."""
    repo = make_adopter_repo()
    repo.write({CONFIG: friction_config(mode="enforcing"), **SOURCE, "docs/guide.md": guide()})
    capability = register_kinds(
        repo.root, "kinds", kinds={"source": "resolve"}, script_body=RESOLVING
    )
    repo.write({"sources/alpha.md": "alpha\n"})
    repo.write({"docs/sourced.md": document("sourced", anchors={"source": ["alpha"]})})
    repo.commit("base", files=None)
    repo.checkout("feature", create=True)
    resolver = capability / RESOLVER
    planted = resolver.read_text(encoding="utf-8") + f"open({str(ran)!r}, 'w').close()\n"
    resolver.write_text(planted, encoding="utf-8")
    repo.commit("a resolver of its own", files=None)
    head = repo.head()
    repo.checkout("main")
    return repo, head, repo.root / ".pkit" / "capabilities" / "project-management"


@pytest.fixture
def replaced(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path, tmp_path_factory, answers_in_files
) -> tuple[AdopterRepo, str, Path, Path]:
    ran = tmp_path_factory.mktemp("outside-the-repository") / "the-head-s-resolver-ran"
    repo, head, capability_root = _head_replacing_its_resolver(make_adopter_repo, ran)
    return repo, head, capability_root, ran


def _description(rw: ModuleType, head: str, placed: object) -> Any:
    return rw._Description(
        "## Doc impact\n\nNone.\n",
        number=PR,
        head=head,
        base="main",
        branch="feature",
        cross_repository=placed is True,
        placed=placed,
        repository="someone/kit",
    )


_MOVE = "the move to review end to end: only a real change check refuses, and only a real "
_MOVE += "resolver started from a checkout shows the mark this test reads means a start"


@pytest.mark.process(_MOVE)
@pytest.mark.parametrize("placed", [True, None], ids=["a-fork", "not-placed"])
def test_the_move_to_review_stops_and_starts_nothing(replaced, rw, placed, capsys) -> None:
    """Off a terminal nothing starts, and the stop says a second run changes nothing
    (DEC-067 point 3). Its words send nobody to a checkout of the head."""
    _repo, head, capability_root, ran = replaced
    move = rw._Move(ISSUE, capability_root, {})
    assert rw._sentence_findings(_description(rw, head, placed), move) is None
    err = capsys.readouterr().err
    assert not ran.exists()
    assert "A second run changes nothing" in err
    assert f"`review-work {ISSUE}`" in err and "--force" in err
    assert "Run from a checkout" not in err


@pytest.mark.process(_MOVE)
def test_force_moves_on_with_its_warning_and_starts_nothing(replaced, rw, capsys) -> None:
    """`--force` goes without the check and never takes a checkout (DEC-067 point 3)."""
    _repo, head, capability_root, ran = replaced
    move = rw._Move(ISSUE, capability_root, {})
    found = rw._sentence_findings(_description(rw, head, True), move, force=True)
    assert found is not None and [f.severity for f in found] == [rw.PRECONDITION]
    assert not ran.exists()
    assert "under --force, no sentence on what changed is checked" in capsys.readouterr().err


@pytest.mark.process(_MOVE)
def test_a_head_that_passes_keeps_its_checkout_at_the_move(replaced, rw) -> None:
    """A writer's head moves as it did: the test passes, and the resolver runs."""
    _repo, head, capability_root, ran = replaced
    move = rw._Move(ISSUE, capability_root, {})
    assert rw._sentence_findings(_description(rw, head, False), move) == []
    assert ran.exists()


@pytest.mark.process(_MOVE)
def test_a_person_at_a_terminal_can_name_the_head_at_the_move(
    replaced, rw, word, monkeypatch
) -> None:
    """The word starts the head's programs for this run, once its comment is posted."""
    _repo, head, capability_root, ran = replaced
    move = rw._Move(ISSUE, capability_root, {}, may_ask=True)
    monkeypatch.setattr("builtins.input", lambda _prompt="": head[:7])
    assert rw._sentence_findings(_description(rw, head, True), move) == []
    assert ran.exists() and len(word) == 1
    assert "`review-work`" in word[0]


@pytest.mark.process(_MOVE)
def test_a_person_who_declines_at_the_move_starts_nothing(replaced, rw, word, monkeypatch) -> None:
    _repo, head, capability_root, ran = replaced
    move = rw._Move(ISSUE, capability_root, {}, may_ask=True)
    monkeypatch.setattr("builtins.input", lambda _prompt="": "no")
    assert rw._sentence_findings(_description(rw, head, True), move) is None
    assert not ran.exists() and word == []


def _pr(head: str, placed: object) -> dict[str, Any]:
    return {
        "number": PR,
        "baseRefName": "main",
        "headRefName": "feature",
        "headRefOid": head,
        "isCrossRepository": placed,
    }


_REVIEW = "the review command's check end to end: only a real change check refuses"


@pytest.mark.process(_REVIEW)
def test_the_review_command_reads_a_head_from_elsewhere_from_git_objects(
    replaced, rpr, monkeypatch, capsys
) -> None:
    """Off a terminal nothing is asked and nothing starts: the reviewers run under the
    brief that says so (DEC-067 point 3)."""
    _repo, head, capability_root, ran = replaced
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False, raising=False)
    found = rpr._head_standing(ISSUE, _pr(head, True), head, capability_root, {})
    assert not found.may_start and not ran.exists()
    assert "from elsewhere" in capsys.readouterr().out


@pytest.mark.process(_REVIEW)
def test_a_word_at_the_review_command_reaches_the_reviewers(
    replaced, rpr, word, monkeypatch
) -> None:
    _repo, head, capability_root, ran = replaced
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True, raising=False)
    monkeypatch.setattr("builtins.input", lambda _prompt="": head[:7])
    found = rpr._head_standing(ISSUE, _pr(head, True), head, capability_root, {})
    assert found.may_start and not ran.exists() and len(word) == 1
    assert "`review-pr`" in word[0]


def test_the_host_s_word_counts_only_for_the_head_it_named(rpr, monkeypatch, capsys) -> None:
    """A reading of another head says nothing of this one (DEC-067 point 1)."""
    monkeypatch.setattr(head_programs, "build_commits", lambda *a: frozenset())
    monkeypatch.setattr(rpr.pr_head, "base_remote", lambda _base: "origin")
    monkeypatch.setattr(
        rpr.friction_answers,
        "checked",
        lambda head, base, *, source=None, from_checkout=True: rpr.friction_answers.Derivation(
            head, document={}, answers=()
        ),
    )
    found = rpr._head_standing(ISSUE, _pr(OTHER, False), HEAD, ROOT, {})
    assert "the host did not say" in found.elsewhere
    assert rpr._head_standing(ISSUE, _pr(HEAD, False), HEAD, ROOT, {}).passes
