"""Tests for project-management's shared membership predicate library.

The library lives at `.pkit/capabilities/project-management/scripts/_lib/membership.py`
— capability-internal. These tests load it via `importlib` so the
kit's pytest run catches regressions in the predicate (which every
mutating pm script will invoke at startup per DEC-021).
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
MEMBERSHIP_PY = (
    REPO_ROOT
    / ".pkit"
    / "capabilities"
    / "project-management"
    / "scripts"
    / "_lib"
    / "membership.py"
)
SCRIPTS_DIR = MEMBERSHIP_PY.parent.parent

#: What `gh api user` says under an account that cannot look itself up, such as
#: a GitHub App installation's token (#3004), and the cause pkit reports for it.
GH_FORBIDDEN = "gh: Resource not accessible by integration (HTTP 403)"
FORBIDDEN = f"`gh api user` failed: {GH_FORBIDDEN}"


@pytest.fixture(scope="module")
def mship():
    """Load the capability-internal membership library by file path."""
    module_name = "pm_membership_under_test"
    spec = importlib.util.spec_from_file_location(module_name, MEMBERSHIP_PY)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Register in sys.modules so @dataclass can resolve cls.__module__ on Identity /
    # MembershipResult.
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# --- Identity resolution ---------------------------------------------


def test_identity_label_prefers_github_login(mship) -> None:
    ident = mship.Identity(github_login="alice", email="alice@example.com")
    assert ident.label() == "alice"


def test_identity_label_falls_back_to_email(mship) -> None:
    ident = mship.Identity(github_login=None, email="bob@example.com")
    assert ident.label() == "bob@example.com"


def test_identity_label_unresolved_when_neither_surface_known(mship) -> None:
    ident = mship.Identity(github_login=None, email=None)
    assert ident.label() == "<unresolved>"


def test_resolve_identity_uses_env_override_when_set(mship, monkeypatch) -> None:
    monkeypatch.setenv("PM_INVOKER_LOGIN", "ci-bot")
    ident = mship.resolve_invoker_identity(
        gh_login_provider=lambda: ("fallback-login", None),
        email_provider=lambda: "ci@example.com",
    )
    assert ident.github_login == "ci-bot"
    assert ident.email == "ci@example.com"
    assert ident.unresolved_cause is None


def test_resolve_identity_falls_back_to_gh_login_provider(mship, monkeypatch) -> None:
    monkeypatch.delenv("PM_INVOKER_LOGIN", raising=False)
    ident = mship.resolve_invoker_identity(
        gh_login_provider=lambda: ("octocat", None),
        email_provider=lambda: None,
    )
    assert ident.github_login == "octocat"
    assert ident.email is None
    assert ident.unresolved_cause is None


def test_resolve_identity_returns_none_when_providers_yield_none(mship, monkeypatch) -> None:
    monkeypatch.delenv("PM_INVOKER_LOGIN", raising=False)
    ident = mship.resolve_invoker_identity(
        gh_login_provider=lambda: (None, FORBIDDEN),
        email_provider=lambda: None,
    )
    assert ident.github_login is None
    assert ident.email is None


# --- An identity pkit cannot resolve is reported with its cause (#3162) ----


def test_an_unresolved_login_carries_its_cause(mship, monkeypatch) -> None:
    monkeypatch.delenv("PM_INVOKER_LOGIN", raising=False)
    ident = mship.resolve_invoker_identity(
        gh_login_provider=lambda: (None, FORBIDDEN), email_provider=lambda: None
    )
    assert ident.unresolved_cause == FORBIDDEN


def test_a_blank_env_override_is_reported_and_asks_no_gh(mship, monkeypatch) -> None:
    """A set `PM_INVOKER_LOGIN` stands in for `gh` even when blank, as before;
    the identity now says why it holds no login."""
    monkeypatch.setenv("PM_INVOKER_LOGIN", "  ")
    ident = mship.resolve_invoker_identity(
        gh_login_provider=lambda: ("octocat", None), email_provider=lambda: None
    )
    assert ident.github_login is None
    assert ident.unresolved_cause == "PM_INVOKER_LOGIN holds only blanks"


def test_the_report_says_pkit_cannot_tell_and_why(mship) -> None:
    assert mship.format_unresolved(FORBIDDEN) == (
        f"pkit cannot tell which account is acting, since {FORBIDDEN}"
    )
    assert mship.format_unresolved(None) == "pkit cannot tell which account is acting"


@pytest.fixture
def gh_user(mship, monkeypatch):
    """Answers `gh api user` with `answer`, a `CompletedProcess` or an exception
    to raise, and returns what the subprocess lookup makes of it."""
    monkeypatch.syspath_prepend(str(SCRIPTS_DIR))
    gh = importlib.import_module("_lib.gh")

    def lookup(answer: object) -> tuple[str | None, str | None]:
        def gh_run(args: list[str], _config: dict, **_kw: object) -> object:
            assert args == ["gh", "api", "user", "--jq", ".login"]
            if isinstance(answer, BaseException):
                raise answer
            return answer

        monkeypatch.setattr(gh, "gh_run", gh_run)
        return mship._gh_login_via_subprocess({})

    return lookup


def _answered(returncode: int, stdout: str = "", stderr: str = "") -> object:
    return subprocess.CompletedProcess(["gh"], returncode, stdout, stderr)


def test_gh_s_refusal_is_the_cause(gh_user) -> None:
    assert gh_user(_answered(1, stderr=f"{GH_FORBIDDEN}\n")) == (None, FORBIDDEN)


def test_a_refusal_gh_gives_no_words_for_names_its_exit(gh_user) -> None:
    assert gh_user(_answered(4)) == (None, "`gh api user` failed: gh exited 4")


def test_a_missing_gh_is_the_cause(gh_user) -> None:
    assert gh_user(FileNotFoundError("gh")) == (None, "`gh` is not on PATH")


def test_a_gh_that_does_not_answer_is_the_cause(gh_user) -> None:
    timeout = subprocess.TimeoutExpired(["gh"], 10)
    assert gh_user(timeout) == (None, "`gh api user` did not answer within 10 seconds")


def test_an_empty_answer_is_the_cause(gh_user) -> None:
    assert gh_user(_answered(0, stdout="\n")) == (None, "`gh api user` answered no login")


def test_a_login_gh_names_has_no_cause(gh_user) -> None:
    assert gh_user(_answered(0, stdout="octocat\n")) == ("octocat", None)


# --- Membership predicate --------------------------------------------


def test_open_mode_allows_anyone(mship) -> None:
    invoker = mship.Identity(github_login="random", email="random@example.com")
    result = mship.check_membership([], invoker)
    assert result.allowed is True
    assert result.mode == "open"
    assert result.refusal_message is None


def test_closed_mode_allows_listed_github_login(mship) -> None:
    members = [{"github_login": "alice", "email": "alice@example.com"}]
    invoker = mship.Identity(github_login="alice", email=None)
    result = mship.check_membership(members, invoker)
    assert result.allowed is True
    assert result.mode == "closed"


def test_closed_mode_allows_when_email_matches_even_without_login(mship) -> None:
    members = [{"github_login": "alice", "email": "alice@example.com"}]
    invoker = mship.Identity(github_login=None, email="alice@example.com")
    result = mship.check_membership(members, invoker)
    assert result.allowed is True


def test_closed_mode_refuses_non_member(mship) -> None:
    members = [{"github_login": "alice"}]
    invoker = mship.Identity(github_login="bob", email="bob@example.com")
    result = mship.check_membership(members, invoker)
    assert result.allowed is False
    assert result.mode == "closed"
    assert result.refusal_message is not None
    assert "Membership required" in result.refusal_message
    assert "bob" in result.refusal_message
    assert "add-member" in result.refusal_message


def test_closed_mode_skips_malformed_entries(mship) -> None:
    """Non-dict entries in members list don't break the predicate."""
    members = ["bad-entry", None, {"github_login": "alice"}]
    invoker = mship.Identity(github_login="alice", email=None)
    result = mship.check_membership(members, invoker)
    assert result.allowed is True


def test_refusal_message_includes_canonical_remediation_path(mship) -> None:
    invoker = mship.Identity(github_login="bob", email=None)
    msg = mship.format_refusal(invoker)
    assert "project-management" in msg
    assert "members.yaml" in msg
    assert "add-member" in msg
    assert "cannot tell" not in msg


def test_a_refusal_of_an_unresolved_login_says_why(mship) -> None:
    """Closed mode refuses an identity whose login pkit cannot resolve, and says
    so with its cause, not only that the identity is no member (#3162)."""
    members = [{"github_login": "alice"}]
    invoker = mship.Identity(github_login=None, email=None, unresolved_cause=FORBIDDEN)
    result = mship.check_membership(members, invoker)
    assert result.allowed is False
    assert result.refusal_message is not None
    lines = result.refusal_message.splitlines()
    assert lines[2].endswith("Your identity (<unresolved>) is not in the member list.")
    assert lines[3] == (f"          → pkit cannot tell which account is acting, since {FORBIDDEN}.")
    assert "add-member" in lines[4]


# --- Capability root resolution --------------------------------------


def test_resolve_capability_root_honours_explicit_path(mship, tmp_path) -> None:
    """An explicit path that exists is returned as-is; nonexistent → None."""
    existing = tmp_path / "cap"
    existing.mkdir()
    assert mship.resolve_capability_root(existing) == existing
    nonexistent = tmp_path / "nope"
    assert mship.resolve_capability_root(nonexistent) is None


def test_resolve_capability_root_walks_up_to_find_pkit_tree(mship, tmp_path, monkeypatch) -> None:
    """CWD-walk fallback locates `.pkit/capabilities/project-management/`."""
    cap_dir = tmp_path / ".pkit" / "capabilities" / "project-management"
    cap_dir.mkdir(parents=True)
    nested = tmp_path / "src" / "deep" / "child"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)
    found = mship.resolve_capability_root(None)
    assert found == cap_dir


def test_resolve_capability_root_returns_none_outside_pkit_tree(
    mship, tmp_path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert mship.resolve_capability_root(None) is None


# --- add-member / remove-member: the change is the person's (#2015) ---------
#
# members.yaml is the project's own configuration. At a terminal the change is
# asked, `--yes` authorises it, and off a terminal without `--yes` it is
# refused before the file is written; an answer piped in is never read.

ROSTER = "members:\n  - github_login: me\n  - github_login: someone\n"


def _load_script(name: str):
    module_name = f"pm_{name.replace('-', '_')}_under_test"
    spec = importlib.util.spec_from_file_location(module_name, SCRIPTS_DIR / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def add_member():
    return _load_script("add-member")


@pytest.fixture(scope="module")
def remove_member():
    return _load_script("remove-member")


class _Stdin:
    """A standard input that is a terminal or, as `echo y | …` gives, a pipe."""

    def __init__(self, terminal: bool) -> None:
        self.terminal = terminal

    def isatty(self) -> bool:
        return self.terminal


def _never_asked(question: str) -> str:
    raise AssertionError(f"asked off a terminal: {question!r}")


def _gated(module, tmp_path: Path, monkeypatch, invoker: object = None) -> Path:
    """A capability root, returned, whose bootstrap gate passes and where
    `invoker` is the identity resolved, by default `me`'s."""
    cap = tmp_path / ".pkit" / "capabilities" / "project-management"
    (cap / "project").mkdir(parents=True)
    monkeypatch.setattr(module, "resolve_capability_root", lambda explicit: cap)
    monkeypatch.setattr(module.bootstrap_gate, "enforce", lambda *a, **k: True)
    monkeypatch.setattr(module, "load_adopter_config", lambda root: {})
    if invoker is None:
        invoker = SimpleNamespace(github_login="me", email=None, label=lambda: "me")
    monkeypatch.setattr(module, "resolve_invoker_identity", lambda config=None: invoker)
    return cap


def _roster(
    module, tmp_path: Path, monkeypatch, roster: str | None, invoker: object = None
) -> Path:
    """A capability root whose gates pass, holding `roster` as members.yaml.
    `invoker` is the identity resolved, by default `me`'s."""
    members = module.members_path(_gated(module, tmp_path, monkeypatch, invoker))
    if roster is not None:
        members.write_text(roster, encoding="utf-8")
    monkeypatch.setattr(module.session_guard, "enforce", lambda override=False: True)
    return members


# (fixture, argv, the roster it starts from)
_MEMBER_CHANGES = [
    pytest.param("add_member", ["add-member.py", "--github-login", "new"], None, id="add"),
    pytest.param("remove_member", ["remove-member.py", "someone"], ROSTER, id="remove"),
]


@pytest.mark.parametrize(("fixture", "argv", "roster"), _MEMBER_CHANGES)
def test_off_a_terminal_without_yes_the_roster_is_not_written(
    request, tmp_path, monkeypatch, capsys, fixture, argv, roster
) -> None:
    module = request.getfixturevalue(fixture)
    members = _roster(module, tmp_path, monkeypatch, roster)
    monkeypatch.setattr(sys, "argv", argv)
    monkeypatch.setattr(sys, "stdin", _Stdin(terminal=False))
    monkeypatch.setattr("builtins.input", _never_asked)
    assert module.main() == 1
    assert (members.read_text(encoding="utf-8") if members.exists() else None) == roster
    err = capsys.readouterr().err
    assert "is the person's to authorise" in err
    assert f"pkit pm {argv[0].removesuffix('.py')} {argv[1]}" in err
    assert err.rstrip().endswith("--yes")


@pytest.mark.parametrize(("fixture", "argv", "roster"), _MEMBER_CHANGES)
@pytest.mark.parametrize(("reply", "written"), [("y", True), ("n", False)])
def test_at_a_terminal_the_roster_change_is_asked(
    request, tmp_path, monkeypatch, fixture, argv, roster, reply, written
) -> None:
    module = request.getfixturevalue(fixture)
    members = _roster(module, tmp_path, monkeypatch, roster)
    monkeypatch.setattr(sys, "argv", argv)
    monkeypatch.setattr(sys, "stdin", _Stdin(terminal=True))
    monkeypatch.setattr("builtins.input", lambda q: reply)
    assert module.main() == 0
    after = members.read_text(encoding="utf-8") if members.exists() else None
    assert (after != roster) is written


@pytest.mark.parametrize(("fixture", "argv", "roster"), _MEMBER_CHANGES)
def test_yes_changes_the_roster_off_a_terminal_without_asking(
    request, tmp_path, monkeypatch, fixture, argv, roster
) -> None:
    module = request.getfixturevalue(fixture)
    members = _roster(module, tmp_path, monkeypatch, roster)
    monkeypatch.setattr(sys, "argv", [*argv, "--yes"])
    monkeypatch.setattr(sys, "stdin", _Stdin(terminal=False))
    monkeypatch.setattr("builtins.input", _never_asked)
    assert module.main() == 0
    assert members.read_text(encoding="utf-8") != roster


# --- Commands that read the identity, where pkit cannot tell the account (#3162) --
#
# Each words its message from the report the identity carries.

#: The report, as each command words it.
CANNOT_TELL = f"pkit cannot tell which account is acting, since {FORBIDDEN}"


@pytest.fixture
def unresolved(mship):
    """The identity resolved where `gh api user` refuses."""
    return mship.Identity(github_login=None, email=None, unresolved_cause=FORBIDDEN)


def test_add_member_me_says_why_it_names_no_login(
    unresolved, add_member, tmp_path, monkeypatch, capsys
) -> None:
    members = _roster(add_member, tmp_path, monkeypatch, None, invoker=unresolved)
    monkeypatch.setattr(sys, "argv", ["add-member.py", "--me", "--yes"])
    monkeypatch.setattr(sys, "stdin", _Stdin(terminal=False))
    monkeypatch.setattr("builtins.input", _never_asked)
    assert add_member.main() == 2
    assert not members.exists()
    assert capsys.readouterr().err == (
        f"[note] --me names the account acting, and {CANNOT_TELL}.\n"
        "error: --github-login is required.\n"
    )


def test_remove_member_me_says_why_it_names_no_login(
    unresolved, remove_member, tmp_path, monkeypatch, capsys
) -> None:
    _roster(remove_member, tmp_path, monkeypatch, None, invoker=unresolved)
    monkeypatch.setattr(sys, "argv", ["remove-member.py", "--me", "--yes"])
    assert remove_member.main() == 2
    assert capsys.readouterr().err == (
        f"error: --me names the account acting, and {CANNOT_TELL}. Pass the login to remove.\n"
    )


def test_assign_issue_me_says_why_it_names_no_login(
    unresolved, tmp_path, monkeypatch, capsys
) -> None:
    assign_issue = _load_script("assign-issue")
    _gated(assign_issue, tmp_path, monkeypatch, unresolved)
    monkeypatch.setattr(assign_issue.session_guard, "enforce", lambda override=False: True)
    monkeypatch.setattr(sys, "argv", ["assign-issue.py", "42", "--me", "--yes"])
    assert assign_issue.main() == 2
    assert capsys.readouterr().err == (
        f"error: --me names the account acting, and {CANNOT_TELL}.\n"
    )


def test_show_members_says_why_it_shows_no_login(unresolved, tmp_path, monkeypatch, capsys) -> None:
    show_members = _load_script("show-members")
    _gated(show_members, tmp_path, monkeypatch, unresolved)
    monkeypatch.setattr(sys, "argv", ["show-members.py"])
    assert show_members.main() == 0
    out = capsys.readouterr().out
    assert "invoker:      <unresolved>\n" in out
    assert f"  github_login: none: {CANNOT_TELL}\n" in out
