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


def test_the_user_s_account_github_answers_is_the_identity_and_the_variable_is_ignored(
    mship, monkeypatch
) -> None:
    """Where GitHub answers that the credential acts as a user's account, that
    login alone is the identity, whatever `PM_INVOKER_LOGIN` names (DEC-021)."""
    monkeypatch.setenv("PM_INVOKER_LOGIN", "ci-bot")
    ident = mship.resolve_invoker_identity(
        gh_login_provider=lambda: ("octocat", None),
        email_provider=lambda: "ci@example.com",
    )
    assert ident.github_login == "octocat"
    assert ident.login_source == mship.FROM_SERVICE
    assert ident.email == "ci@example.com"
    assert ident.unresolved_cause is None


def test_where_github_names_no_user_s_account_the_variable_is_the_identity(
    mship, monkeypatch
) -> None:
    monkeypatch.setenv("PM_INVOKER_LOGIN", "ci-bot")
    ident = mship.resolve_invoker_identity(
        gh_login_provider=lambda: (None, FORBIDDEN),
        email_provider=lambda: "ci@example.com",
    )
    assert ident.github_login == "ci-bot"
    assert ident.login_source == mship.FROM_VARIABLE
    assert ident.service_cause == FORBIDDEN
    assert ident.unresolved_cause is None


def test_github_is_asked_with_the_variable_set(mship, monkeypatch) -> None:
    monkeypatch.setenv("PM_INVOKER_LOGIN", "ci-bot")
    asked: list[str] = []

    def provider() -> tuple[str | None, str | None]:
        asked.append("gh api user")
        return None, FORBIDDEN

    mship.resolve_invoker_identity(gh_login_provider=provider, email_provider=lambda: None)
    assert asked == ["gh api user"]


def test_resolve_identity_falls_back_to_gh_login_provider(mship, monkeypatch) -> None:
    monkeypatch.delenv("PM_INVOKER_LOGIN", raising=False)
    ident = mship.resolve_invoker_identity(
        gh_login_provider=lambda: ("octocat", None),
        email_provider=lambda: None,
    )
    assert ident.github_login == "octocat"
    assert ident.login_source == mship.FROM_SERVICE
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


def test_a_blank_variable_where_github_names_no_user_s_account_names_both_causes(
    mship, monkeypatch
) -> None:
    monkeypatch.setenv("PM_INVOKER_LOGIN", "  ")
    ident = mship.resolve_invoker_identity(
        gh_login_provider=lambda: (None, FORBIDDEN), email_provider=lambda: None
    )
    assert ident.github_login is None
    assert ident.unresolved_cause == f"{FORBIDDEN}, and PM_INVOKER_LOGIN holds only blanks"


def test_a_blank_variable_beside_a_login_github_answers_is_ignored(
    mship, monkeypatch, capsys
) -> None:
    monkeypatch.setenv("PM_INVOKER_LOGIN", "  ")
    ident = mship.resolve_invoker_identity(
        gh_login_provider=lambda: ("octocat", None), email_provider=lambda: None
    )
    assert (ident.github_login, ident.unresolved_cause) == ("octocat", None)
    assert capsys.readouterr().err == ""


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
            assert args == ["gh", "api", "user", "--jq", "[.login, .type] | @tsv"]
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
    assert gh_user(_answered(0, stdout="octocat\tUser\n")) == ("octocat", None)


def test_an_account_of_another_type_than_a_user_s_is_no_answer(gh_user) -> None:
    assert gh_user(_answered(0, stdout="octo-app[bot]\tBot\n")) == (
        None,
        "`gh api user` answered octo-app[bot], an account of type Bot, not a user's",
    )


def test_a_one_field_answer_is_no_answer(gh_user) -> None:
    assert gh_user(_answered(0, stdout="octocat\n")) == (
        None,
        "`gh api user` answered 'octocat', not a login and an account type",
    )


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


# --- A login GitHub answers stands alone at the gate (DEC-021, #3175) --------

ALICE = {"github_login": "alice", "email": "alice@example.com"}


def _answered_as(mship, login: str, email: str | None = None):
    """The identity where GitHub answers that the credential acts as `login`."""
    return mship.Identity(github_login=login, email=email, login_source=mship.FROM_SERVICE)


def test_a_member_s_email_beside_a_non_member_login_github_answers_is_refused(mship) -> None:
    result = mship.check_membership([ALICE], _answered_as(mship, "bob", "alice@example.com"))
    assert result.allowed is False


def test_the_email_still_matches_where_github_names_no_user_s_account(mship) -> None:
    """A login from the variable and git's email each count, as before."""
    invoker = mship.Identity(
        github_login="ci-bot", email="alice@example.com", login_source=mship.FROM_VARIABLE
    )
    assert mship.check_membership([ALICE], invoker).allowed is True


def test_an_entry_that_differs_only_in_case_from_a_login_github_answers_passes(mship) -> None:
    assert mship.check_membership([ALICE], _answered_as(mship, "Alice")).allowed is True


def test_a_stand_in_without_login_source_keeps_the_match_on_any_surface(mship) -> None:
    invoker = SimpleNamespace(github_login="bob", email="alice@example.com", label=lambda: "bob")
    assert mship.check_membership([ALICE], invoker).allowed is True


def test_the_refusal_names_what_it_did_not_count_beside_a_login_github_answers(
    mship, monkeypatch
) -> None:
    monkeypatch.setenv("PM_INVOKER_LOGIN", "alice")
    result = mship.check_membership([ALICE], _answered_as(mship, "bob", "alice@example.com"))
    assert result.refusal_message is not None
    lines = result.refusal_message.splitlines()
    assert lines[2].endswith("Your identity (bob) is not in the member list.")
    assert lines[3] == (
        "          → PM_INVOKER_LOGIN names the member alice, and is no identity where "
        "GitHub answers that the credential acts as a user's account (bob)."
    )
    assert lines[4] == (
        "          → git's email (alice@example.com) matches the entry of alice, and counts "
        "only where GitHub answers with no user's account."
    )
    assert "add-member" in lines[5]


def test_the_refusal_names_no_variable_that_names_no_member(mship, monkeypatch) -> None:
    monkeypatch.setenv("PM_INVOKER_LOGIN", "carol")
    result = mship.check_membership([ALICE], _answered_as(mship, "bob"))
    assert result.refusal_message is not None
    assert "PM_INVOKER_LOGIN" not in result.refusal_message


# --- The warning on an ignored variable -----------------------------------


def _resolved(mship, answered: str) -> object:
    return mship.resolve_invoker_identity(
        gh_login_provider=lambda: (answered, None), email_provider=lambda: None
    )


def test_a_variable_that_names_another_account_is_warned_of_once(
    mship, monkeypatch, capsys
) -> None:
    monkeypatch.setenv("PM_INVOKER_LOGIN", "ci-bot")
    _resolved(mship, "octocat")
    _resolved(mship, "octocat")
    assert capsys.readouterr().err == (
        "[warn] PM_INVOKER_LOGIN names ci-bot, but GitHub answers that the credential acts "
        "as the user's account octocat. pkit takes octocat as the account acting and "
        "ignores the variable (DEC-021).\n"
    )


def test_a_variable_that_names_the_same_account_in_another_case_is_not_warned_of(
    mship, monkeypatch, capsys
) -> None:
    monkeypatch.setenv("PM_INVOKER_LOGIN", "OctoCat")
    _resolved(mship, "octocat")
    assert capsys.readouterr().err == ""


# --- GitHub is asked once per process and host -------------------------------


@pytest.fixture
def requests(mship, monkeypatch) -> list[list[str]]:
    """The `gh` calls the membership library makes, each answered with a user's
    account, `octocat`."""
    monkeypatch.syspath_prepend(str(SCRIPTS_DIR))
    gh = importlib.import_module("_lib.gh")
    made: list[list[str]] = []

    def gh_run(args: list[str], _config: dict, **_kw: object) -> object:
        made.append(args)
        return _answered(0, stdout="octocat\tUser\n")

    monkeypatch.setattr(gh, "gh_run", gh_run)
    monkeypatch.setattr(mship, "_email_via_subprocess", lambda: None)
    return made


def test_github_is_asked_once_per_process_and_host(mship, requests) -> None:
    other_host = {"gh": {"host": "github.example.com"}}
    for config in ({}, {}, other_host, other_host):
        assert mship.resolve_invoker_identity(config=config).github_login == "octocat"
    assert len(requests) == 2


def test_a_provider_passed_is_asked_and_github_is_not(mship, requests) -> None:
    _resolved(mship, "octocat")
    assert requests == []


# --- The `gh` on PATH the suite puts there (tests/conftest.py) ----------------


def test_github_names_no_account_in_a_test_and_the_variable_counts(mship, monkeypatch) -> None:
    monkeypatch.syspath_prepend(str(SCRIPTS_DIR))
    monkeypatch.setenv("PM_INVOKER_LOGIN", "ci-bot")
    ident = mship.resolve_invoker_identity(config={}, email_provider=lambda: None)
    assert (ident.github_login, ident.login_source) == ("ci-bot", mship.FROM_VARIABLE)


def test_service_answers_makes_github_answer_with_a_user_s_account(
    mship, monkeypatch, service_answers
) -> None:
    monkeypatch.syspath_prepend(str(SCRIPTS_DIR))
    monkeypatch.setenv("PM_INVOKER_LOGIN", "OctoCat")
    service_answers("octocat")
    ident = mship.resolve_invoker_identity(config={}, email_provider=lambda: None)
    assert (ident.github_login, ident.login_source) == ("octocat", mship.FROM_SERVICE)


def test_service_answers_an_app_s_account_as_no_user_s(mship, monkeypatch, service_answers) -> None:
    monkeypatch.syspath_prepend(str(SCRIPTS_DIR))
    service_answers("octo-app[bot]", "Bot")
    ident = mship.resolve_invoker_identity(config={}, email_provider=lambda: None)
    assert ident.github_login is None
    assert ident.unresolved_cause == (
        "`gh api user` answered octo-app[bot], an account of type Bot, not a user's"
    )


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
    `invoker` is the identity resolved, by default `me`'s. Where the module
    looks a login up on GitHub, GitHub names a user's account by it, spelled
    as given."""
    cap = tmp_path / ".pkit" / "capabilities" / "project-management"
    (cap / "project").mkdir(parents=True)
    monkeypatch.setattr(module, "resolve_capability_root", lambda explicit: cap)
    monkeypatch.setattr(module.bootstrap_gate, "enforce", lambda *a, **k: True)
    monkeypatch.setattr(module, "load_adopter_config", lambda root: {})
    if invoker is None:
        invoker = SimpleNamespace(github_login="me", email=None, label=lambda: "me")
    monkeypatch.setattr(module, "resolve_invoker_identity", lambda config=None: invoker)
    if hasattr(module, "look_up_account"):
        monkeypatch.setattr(module, "look_up_account", _github_names_as_given)
    return cap


def _github_names_as_given(login: str, config: object = None) -> object:
    return SimpleNamespace(login=login, account_type="User", missing=False, cause=None)


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


# --- add-member writes a user's login as GitHub spells it (DEC-021, #3175) ----


def _add(add_member, monkeypatch, *argv: str, terminal: bool = False, reply: str = "") -> int:
    monkeypatch.setattr(sys, "argv", ["add-member.py", *argv, "--yes"])
    monkeypatch.setattr(sys, "stdin", _Stdin(terminal=terminal))
    monkeypatch.setattr("builtins.input", (lambda q: reply) if terminal else _never_asked)
    return add_member.main()


def _looked_up(monkeypatch, add_member, mship, answer: object) -> list[str]:
    """GitHub answers each lookup with `answer`; returns the logins looked up."""
    asked: list[str] = []

    def look_up(login: str, config: object = None) -> object:
        asked.append(login)
        return answer

    monkeypatch.setattr(add_member, "look_up_account", look_up)
    return asked


def _written(members: Path) -> list[dict]:
    from ruamel.yaml import YAML

    return YAML(typ="safe").load(members.read_text(encoding="utf-8"))["members"]


def test_add_member_writes_the_login_as_github_spells_it(
    add_member, mship, tmp_path, monkeypatch, capsys
) -> None:
    members = _roster(add_member, tmp_path, monkeypatch, None)
    asked = _looked_up(
        monkeypatch, add_member, mship, mship.LookedUp(login="OctoCat", account_type="User")
    )
    assert _add(add_member, monkeypatch, "--github-login", "octocat") == 0
    assert asked == ["octocat"]
    assert _written(members)[0]["github_login"] == "OctoCat"
    assert (
        "[note] GitHub spells the login 'OctoCat', and the entry takes that spelling, "
        "not 'octocat'." in capsys.readouterr().out
    )


def test_add_member_refuses_a_login_github_knows_no_account_by(
    add_member, mship, tmp_path, monkeypatch, capsys
) -> None:
    members = _roster(add_member, tmp_path, monkeypatch, None)
    _looked_up(monkeypatch, add_member, mship, mship.LookedUp(missing=True))
    assert _add(add_member, monkeypatch, "--github-login", "nobody-here") == 2
    assert not members.exists()
    assert capsys.readouterr().err == (
        "error: GitHub knows no account by the login 'nobody-here'.\n"
    )


def test_add_member_writes_a_login_as_typed_where_github_gives_no_answer(
    add_member, mship, tmp_path, monkeypatch, capsys
) -> None:
    members = _roster(add_member, tmp_path, monkeypatch, None)
    _looked_up(monkeypatch, add_member, mship, mship.LookedUp(cause=FORBIDDEN))
    assert _add(add_member, monkeypatch, "--github-login", "octocat") == 0
    assert _written(members)[0]["github_login"] == "octocat"
    assert capsys.readouterr().err == (
        f"[warn] GitHub gave no answer for the login 'octocat', since {FORBIDDEN}. Its "
        "spelling is unchecked, and the entry takes it as typed.\n"
    )


def test_add_member_writes_an_app_s_login_as_typed(
    add_member, mship, tmp_path, monkeypatch
) -> None:
    members = _roster(add_member, tmp_path, monkeypatch, None)
    _looked_up(
        monkeypatch, add_member, mship, mship.LookedUp(login="Octo-App[bot]", account_type="Bot")
    )
    assert _add(add_member, monkeypatch, "--github-login", "octo-app[bot]") == 0
    assert _written(members)[0]["github_login"] == "octo-app[bot]"


def test_add_member_looks_up_the_login_typed_at_the_prompt(
    add_member, mship, unresolved, tmp_path, monkeypatch
) -> None:
    members = _roster(add_member, tmp_path, monkeypatch, None, invoker=unresolved)
    asked = _looked_up(
        monkeypatch, add_member, mship, mship.LookedUp(login="OctoCat", account_type="User")
    )
    assert _add(add_member, monkeypatch, "--me", terminal=True, reply="octocat") == 0
    assert asked == ["octocat"]
    assert _written(members)[0]["github_login"] == "OctoCat"


def test_add_member_me_looks_up_the_variable_s_login(
    add_member, mship, tmp_path, monkeypatch
) -> None:
    invoker = mship.Identity(github_login="ci-bot", email=None, login_source=mship.FROM_VARIABLE)
    members = _roster(add_member, tmp_path, monkeypatch, None, invoker=invoker)
    asked = _looked_up(
        monkeypatch, add_member, mship, mship.LookedUp(login="CI-Bot", account_type="User")
    )
    assert _add(add_member, monkeypatch, "--me") == 0
    assert asked == ["ci-bot"]
    assert _written(members)[0]["github_login"] == "CI-Bot"


def test_add_member_me_takes_the_login_github_answers_unlooked_and_git_s_email(
    add_member, mship, tmp_path, monkeypatch, capsys
) -> None:
    invoker = mship.Identity(
        github_login="octocat", email="octo@example.com", login_source=mship.FROM_SERVICE
    )
    members = _roster(add_member, tmp_path, monkeypatch, None, invoker=invoker)
    asked = _looked_up(monkeypatch, add_member, mship, mship.LookedUp(missing=True))
    assert _add(add_member, monkeypatch, "--me") == 0
    assert asked == []
    entry = _written(members)[0]
    assert (entry["github_login"], entry["email"]) == ("octocat", "octo@example.com")
    out = capsys.readouterr().out
    assert "  email: octo@example.com\n  (the email is git's user.email)\n" in out


def test_add_member_refuses_a_login_already_listed_in_another_case(
    add_member, tmp_path, monkeypatch, capsys
) -> None:
    members = _roster(add_member, tmp_path, monkeypatch, ROSTER)
    assert _add(add_member, monkeypatch, "--github-login", "SomeOne") == 3
    assert members.read_text(encoding="utf-8") == ROSTER
    assert "an entry for github_login='someone' already exists" in capsys.readouterr().err


# --- show-members says where the login came from ----------------------------


@pytest.mark.parametrize(
    ("source", "cause", "shown"),
    [
        ("service", None, "octocat (GitHub's answer for the credential)"),
        ("variable", FORBIDDEN, f"octocat (from PM_INVOKER_LOGIN, since {FORBIDDEN})"),
    ],
)
def test_show_members_says_where_the_login_came_from(
    mship, tmp_path, monkeypatch, capsys, source, cause, shown
) -> None:
    show_members = _load_script("show-members")
    invoker = mship.Identity(
        github_login="octocat", email=None, login_source=source, service_cause=cause
    )
    _gated(show_members, tmp_path, monkeypatch, invoker)
    monkeypatch.setattr(sys, "argv", ["show-members.py"])
    assert show_members.main() == 0
    assert f"  github_login: {shown}\n" in capsys.readouterr().out
