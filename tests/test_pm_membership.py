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
    """Load the capability-internal membership library by file path, with the
    capability's scripts on the path for the `_lib` modules it imports."""
    sys.path.insert(0, str(SCRIPTS_DIR))
    module_name = "pm_membership_under_test"
    spec = importlib.util.spec_from_file_location(module_name, MEMBERSHIP_PY)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Register in sys.modules so @dataclass can resolve cls.__module__ on Identity /
    # MembershipResult.
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    yield module
    sys.path.remove(str(SCRIPTS_DIR))


def _user(mship, login: str = "octocat"):
    """The backbone's reading where GitHub answers a user's account."""
    return mship.accounts.Reading(account=login, kind=mship.KIND_USER)


def _bot(mship, account: str = "robot[bot]"):
    """The backbone's reading where GitHub answers a bot's account."""
    return mship.accounts.Reading(account=account, kind=mship.KIND_BOT)


def _refused(mship, cause: str = "integration-refused", reason: str = FORBIDDEN):
    """The backbone's reading where it names no account, with `cause`."""
    return mship.accounts.Reading(cause=cause, reason=reason)


def _resolve(mship, reading, email: str | None = None):
    return mship.resolve_invoker_identity(
        reading_provider=lambda: reading, email_provider=lambda: email
    )


# --- Identity resolution (DEC-076 point 1) ------------------------------------


def test_identity_label_prefers_github_login(mship) -> None:
    ident = mship.Identity(github_login="alice", email="alice@example.com")
    assert ident.label() == "alice"


def test_identity_label_unresolved_when_no_account_is_named(mship) -> None:
    ident = mship.Identity(github_login=None, email="bob@example.com")
    assert ident.label() == "<unresolved>"


def test_the_user_s_account_github_answers_is_the_identity_and_the_variable_is_ignored(
    mship, monkeypatch, capsys
) -> None:
    """Where GitHub answers that the credential acts as a user's account, that
    login alone is the identity and the person, whatever `PM_INVOKER_LOGIN`
    names (DEC-021, DEC-076 point 3)."""
    monkeypatch.setenv("PM_INVOKER_LOGIN", "someone-else")
    ident = _resolve(mship, _user(mship), email="ci@example.com")
    assert (ident.github_login, ident.kind, ident.email) == ("octocat", "user", "ci@example.com")
    assert ident.names_user and ident.person == "octocat"
    assert ident.works_for is None
    assert "PM_INVOKER_LOGIN names someone-else" in capsys.readouterr().err


def test_a_bot_s_account_is_the_acting_account_and_the_variable_names_the_person(
    mship, monkeypatch
) -> None:
    """Under an App installation's token, the acting account is the bot's, and
    the variable names only the person the agent works for (DEC-076 points 1, 3)."""
    monkeypatch.setenv("PM_INVOKER_LOGIN", "alice")
    ident = _resolve(mship, _bot(mship))
    assert (ident.github_login, ident.kind) == ("robot[bot]", "bot")
    assert not ident.names_user
    assert (ident.works_for, ident.person) == ("alice", "alice")


@pytest.mark.parametrize("cause", ["integration-refused", "kind-unknown"])
def test_an_unnamed_account_names_no_account_and_no_person_without_the_variable(
    mship, cause
) -> None:
    ident = _resolve(mship, _refused(mship, cause=cause))
    assert ident.github_login is None
    assert ident.unnamed and not ident.unresolved
    assert ident.person is None
    assert ident.unresolved_cause == FORBIDDEN


@pytest.mark.parametrize("cause", ["refused", "no-answer", "gh-missing", "offline", "timeout"])
def test_a_reading_with_no_answer_is_an_unresolved_identity(mship, monkeypatch, cause) -> None:
    monkeypatch.setenv("PM_INVOKER_LOGIN", "alice")
    ident = _resolve(mship, _refused(mship, cause=cause, reason="no answer"))
    assert ident.github_login is None
    assert ident.unresolved and not ident.unnamed
    assert ident.person == "alice"


def test_the_variable_never_stands_for_the_acting_account(mship, monkeypatch) -> None:
    """No fallback to the variable or git's email for the account (DEC-076 point 1)."""
    monkeypatch.setenv("PM_INVOKER_LOGIN", "alice")
    ident = _resolve(mship, _refused(mship), email="alice@example.com")
    assert ident.github_login is None
    assert ident.label() == "<unresolved>"


def test_a_blank_variable_names_no_person(mship, monkeypatch) -> None:
    monkeypatch.setenv("PM_INVOKER_LOGIN", "   ")
    assert _resolve(mship, _bot(mship)).person is None


def test_no_person_says_why_and_how_to_name_one(mship) -> None:
    said = _resolve(mship, _bot(mship)).no_person()
    assert said.startswith("GitHub answers that the credential acts as robot[bot], a bot's")
    assert "Set PM_INVOKER_LOGIN to the login of the person the agent works for" in said
    unresolved = _resolve(mship, _refused(mship, cause="refused", reason=FORBIDDEN)).no_person()
    assert unresolved.startswith(f"pkit cannot tell which account is acting, since {FORBIDDEN}")


def test_a_stand_in_with_no_kind_is_read_by_its_form(mship) -> None:
    assert mship.Identity(github_login="alice", email=None).names_user
    assert not mship.Identity(github_login="robot[bot]", email=None).names_user
    assert not mship.Identity(github_login=None, email=None).names_user


# --- The capability's reader of the backbone's reading (`_lib/accounts`) --------


def _document(**fields):
    import json

    keys = ("account", "kind", "id", "login", "cause", "reason")
    return json.dumps({"schema_version": 1, **{k: fields.get(k) for k in keys}})


def _ran(stdout: str = "", returncode: int = 0, stderr: str = ""):
    return subprocess.CompletedProcess([], returncode, stdout, stderr)


def test_the_reading_is_read_from_the_backbone_s_document(mship) -> None:
    accounts = mship.accounts
    accounts.forget_service_answers()
    asked: list[list[str]] = []

    def run(argv, **_options):
        asked.append(list(argv))
        return _ran(_document(account="robot[bot]", kind="bot", login="robot[bot]"))

    reading = accounts.read({}, run=run)
    assert (reading.account, reading.kind) == ("robot[bot]", "bot")
    assert asked == [list(accounts.READ_ARGV)]
    accounts.read({}, run=run)
    assert len(asked) == 1  # asked once in a run
    accounts.forget_service_answers()


@pytest.mark.parametrize(
    "ran",
    [_ran("", 1, "error: boom"), _ran("not json"), _ran('{"schema_version": 2}')],
    ids=["exit", "no-json", "version"],
)
def test_a_document_that_cannot_be_read_names_no_account(mship, ran) -> None:
    accounts = mship.accounts
    accounts.forget_service_answers()
    reading = accounts.read({}, run=lambda argv, **_o: ran)
    assert reading.account is None
    assert reading.cause == accounts.CAUSE_NO_DOCUMENT
    assert reading.unresolved
    accounts.forget_service_answers()


def test_the_host_the_configuration_pins_is_passed_on(mship) -> None:
    accounts = mship.accounts
    accounts.forget_service_answers()
    seen: list[object] = []

    def run(argv, **options):
        seen.append((options.get("env") or {}).get("GH_HOST"))
        return _ran(_document(account="alice", kind="user", login="alice"))

    accounts.read({"gh": {"host": "ghe.example.com"}}, run=run)
    assert seen == ["ghe.example.com"]
    accounts.forget_service_answers()


def test_a_comparison_the_backbone_cannot_be_asked_cannot_tell(mship) -> None:
    accounts = mship.accounts
    asked = accounts.ask(
        pairs=[(accounts.entry("a"), accounts.entry("a"))],
        run=lambda argv, **_o: _ran("", 1, "error: no"),
    )
    assert asked.pairs == (accounts.CANNOT_TELL,)
    assert asked.cause is not None


def test_the_backbone_s_function_compares(mship) -> None:
    """Answered by the backbone's own code in this process (tests/in_process.py)."""
    accounts = mship.accounts
    asked = accounts.ask(
        pairs=[
            (accounts.entry("Alice"), accounts.entry("alice")),
            (accounts.users_field("alice"), accounts.entry("bob")),
            (accounts.login("alice"), accounts.entry("alice")),
        ]
    )
    assert asked.pairs == (accounts.ONE, accounts.TWO, accounts.CANNOT_TELL)


# --- Membership predicate (DEC-076 point 2) -----------------------------------


def test_open_mode_allows_anyone(mship) -> None:
    invoker = mship.Identity(github_login="anyone", email=None)
    result = mship.check_membership([], invoker)
    assert result.allowed is True
    assert result.mode == "open"
    assert result.refusal_message is None


def test_closed_mode_allows_listed_github_login(mship) -> None:
    members = [{"github_login": "alice"}, {"github_login": "bob"}]
    invoker = mship.Identity(github_login="alice", email=None, kind="user")
    result = mship.check_membership(members, invoker)
    assert result.allowed is True
    assert result.mode == "closed"


def test_an_entry_that_differs_only_in_case_passes(mship) -> None:
    members = [{"github_login": "OctoCat"}]
    invoker = mship.Identity(github_login="octocat", email=None, kind="user")
    assert mship.check_membership(members, invoker).allowed


def test_a_bot_s_account_passes_only_as_its_own_entry(mship) -> None:
    """The closed gate matches a bot's own login, never a bare entry of its name."""
    invoker = mship.Identity(github_login="robot[bot]", email=None, kind="bot")
    assert mship.check_membership([{"github_login": "robot[bot]"}], invoker).allowed
    refused = mship.check_membership([{"github_login": "robot"}], invoker)
    assert not refused.allowed
    assert "robot" in refused.refusal_message


def test_closed_mode_refuses_where_no_account_is_named(mship, monkeypatch) -> None:
    """Neither the variable nor git's email passes a closed gate (DEC-076 point 2)."""
    monkeypatch.setenv("PM_INVOKER_LOGIN", "alice")
    members = [{"github_login": "alice", "email": "alice@example.com"}]
    invoker = _resolve(mship, _refused(mship), email="alice@example.com")
    result = mship.check_membership(members, invoker)
    assert not result.allowed
    message = result.refusal_message
    assert FORBIDDEN in message
    assert "git's email (alice@example.com) matches an entry, and passes no gate" in message


def test_closed_mode_refuses_non_member(mship) -> None:
    members = [{"github_login": "alice"}]
    invoker = mship.Identity(github_login="mallory", email=None, kind="user")
    result = mship.check_membership(members, invoker)
    assert result.allowed is False
    assert result.mode == "closed"
    assert "mallory" in result.refusal_message
    assert "pkit project-management add-member" in result.refusal_message


def test_closed_mode_skips_malformed_entries(mship) -> None:
    members = ["just-a-string", {"no_login_field": True}, {"github_login": "alice"}]
    invoker = mship.Identity(github_login="alice", email=None, kind="user")
    assert mship.check_membership(members, invoker).allowed is True


def test_an_entry_with_no_spelling_is_named_in_the_refusal(mship) -> None:
    members = [{"github_login": "@alice"}]
    invoker = mship.Identity(github_login="alice", email=None, kind="user")
    result = mship.check_membership(members, invoker)
    assert not result.allowed
    assert "@alice" in result.refusal_message


def test_the_member_list_changes_only_under_a_user_s_account(mship) -> None:
    user = mship.Identity(github_login="alice", email=None, kind="user")
    assert mship.member_list_refusal(user, "add-member") is None
    bot = mship.Identity(github_login="robot[bot]", email=None, kind="bot")
    refused = mship.member_list_refusal(bot, "add-member")
    assert refused.startswith("[refused] add-member: GitHub answers that the credential acts")
    assert "DEC-076 point 2" in refused
    unresolved = _resolve(mship, _refused(mship, cause="refused"))
    assert "pkit cannot tell which account is acting" in mship.member_list_refusal(
        unresolved, "remove-member"
    )


# --- The `gh` on PATH the suite puts there (tests/conftest.py) ----------------


def test_github_names_no_account_in_a_test(mship, monkeypatch) -> None:
    monkeypatch.setenv("PM_INVOKER_LOGIN", "ci-bot")
    ident = mship.resolve_invoker_identity(email_provider=lambda: None)
    assert ident.github_login is None
    assert ident.person == "ci-bot"


def test_service_answers_makes_github_answer_with_a_user_s_account(
    mship, monkeypatch, service_answers
) -> None:
    monkeypatch.setenv("PM_INVOKER_LOGIN", "ci-bot")
    service_answers("octocat", "User")
    ident = mship.resolve_invoker_identity(email_provider=lambda: None)
    assert (ident.github_login, ident.kind, ident.person) == ("octocat", "user", "octocat")


def test_service_answers_an_app_s_account_as_a_bot_s(mship, monkeypatch, service_answers) -> None:
    monkeypatch.setenv("PM_INVOKER_LOGIN", "ci-bot")
    service_answers("octo-app[bot]", "Bot")
    ident = mship.resolve_invoker_identity(email_provider=lambda: None)
    assert (ident.github_login, ident.kind, ident.person) == ("octo-app[bot]", "bot", "ci-bot")


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
        invoker = SimpleNamespace(
            github_login="me",
            email=None,
            kind="user",
            names_user=True,
            person="me",
            label=lambda: "me",
        )
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


# --- Commands that read the identity under a credential that names no user's account --
#
# The member list changes only under a credential that names a user's account
# (DEC-076 point 2), and `--me` on an assignment names the person the agent
# works for, or refuses where none is named (point 3).

#: The report, as each command words it.
CANNOT_TELL = f"pkit cannot tell which account is acting, since {FORBIDDEN}"


@pytest.fixture
def unresolved(mship):
    """The identity resolved where `gh api user` refuses."""
    return mship.Identity(
        github_login=None, email=None, unresolved_cause=FORBIDDEN, cause="refused"
    )


@pytest.fixture
def app(mship):
    """The identity resolved under an App installation's token."""
    return mship.Identity(github_login="robot[bot]", email=None, kind="bot")


@pytest.mark.parametrize("who", ["unresolved", "app"])
@pytest.mark.parametrize(("fixture", "argv", "roster"), _MEMBER_CHANGES)
def test_the_member_list_changes_under_no_credential_that_names_no_user_s_account(
    request, tmp_path, monkeypatch, capsys, fixture, argv, roster, who
) -> None:
    """In open mode, and behind a closed gate whose entry names the bot's own account."""
    module = request.getfixturevalue(fixture)
    invoker = request.getfixturevalue(who)
    if roster is not None:
        roster = f"{roster}  - github_login: robot[bot]\n"
        if who == "unresolved":
            roster = None if fixture == "add_member" else roster
    members = _roster(module, tmp_path, monkeypatch, roster, invoker=invoker)
    monkeypatch.setattr(sys, "argv", [*argv, "--yes"])
    monkeypatch.setattr(sys, "stdin", _Stdin(terminal=False))
    monkeypatch.setattr("builtins.input", _never_asked)
    assert module.main() == 1
    assert (members.read_text(encoding="utf-8") if members.exists() else None) == roster
    err = capsys.readouterr().err
    verb = argv[0].removesuffix(".py")
    if roster is not None and who == "unresolved":
        # Behind a closed gate, a credential that names no account is no member.
        assert err.startswith("[refused] Membership required for this operation")
        assert CANNOT_TELL in err
        return
    assert err.startswith(f"[refused] {verb}: ")
    assert "DEC-076 point 2" in err
    assert (CANNOT_TELL if who == "unresolved" else "acts as robot[bot], a bot's account") in err


def test_assign_issue_me_says_why_it_names_no_person(
    unresolved, tmp_path, monkeypatch, capsys
) -> None:
    assign_issue = _load_script("assign-issue")
    _gated(assign_issue, tmp_path, monkeypatch, unresolved)
    monkeypatch.setattr(assign_issue.session_guard, "enforce", lambda override=False: True)
    monkeypatch.setattr(sys, "argv", ["assign-issue.py", "42", "--me", "--yes"])
    assert assign_issue.main() == 2
    err = capsys.readouterr().err
    assert err.startswith(f"error: --me names no person: {CANNOT_TELL}, and PM_INVOKER_LOGIN")


def test_show_members_says_why_it_shows_no_login(unresolved, tmp_path, monkeypatch, capsys) -> None:
    show_members = _load_script("show-members")
    _gated(show_members, tmp_path, monkeypatch, unresolved)
    monkeypatch.setattr(sys, "argv", ["show-members.py"])
    assert show_members.main() == 0
    out = capsys.readouterr().out
    assert "invoker:      <unresolved>\n" in out
    assert f"  github_login: none: {CANNOT_TELL}\n" in out
    assert "  works for:    none: PM_INVOKER_LOGIN is not set" in out


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
    add_member, mship, tmp_path, monkeypatch
) -> None:
    members = _roster(add_member, tmp_path, monkeypatch, None)
    asked = _looked_up(
        monkeypatch, add_member, mship, mship.LookedUp(login="OctoCat", account_type="User")
    )
    assert _add(add_member, monkeypatch, terminal=True, reply="octocat") == 0
    assert asked == ["octocat"]
    assert _written(members)[0]["github_login"] == "OctoCat"


def test_add_member_me_takes_the_login_github_answers_unlooked_and_git_s_email(
    add_member, mship, tmp_path, monkeypatch, capsys
) -> None:
    invoker = mship.Identity(github_login="octocat", email="octo@example.com", kind="user")
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


# --- show-members says what kind of account GitHub answered -----------------------


@pytest.mark.parametrize(
    ("kind", "shown"),
    [
        ("user", "octocat (GitHub's answer for the credential: a user's account)"),
        ("bot", "octocat[bot] (GitHub's answer for the credential: a bot's account)"),
    ],
)
def test_show_members_says_what_kind_of_account_github_answered(
    mship, tmp_path, monkeypatch, capsys, kind, shown
) -> None:
    show_members = _load_script("show-members")
    login = "octocat" if kind == "user" else "octocat[bot]"
    invoker = mship.Identity(github_login=login, email=None, kind=kind, works_for="alice")
    _gated(show_members, tmp_path, monkeypatch, invoker)
    monkeypatch.setattr(sys, "argv", ["show-members.py"])
    assert show_members.main() == 0
    out = capsys.readouterr().out
    assert f"  github_login: {shown}\n" in out
    assert ("works for:    alice" in out) is (kind == "bot")
