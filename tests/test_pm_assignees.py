"""An assignee is never a bot's account (DEC-079 point 1).

`_lib/assignees.py` confirms each account a command makes an assignee: a bot's
spelling, and a string with no spelling, refuse with no request; a bare login
is assigned only where GitHub answers that it names a user's account, which
the account GitHub answered the credential acts as already is; and every
lookup that confirms nothing refuses with the login and its cause.
"""

from __future__ import annotations

from typing import Any

import pytest

from tests import pm_assignee_lookup

# The modules the helper put on the path and fakes the lookup in.
assignees = pm_assignee_lookup.assignees
membership = pm_assignee_lookup.membership

# The backbone's reading named the user's account alice (ADR-094).
FROM_SERVICE = membership.Identity(github_login="alice", email=None, kind=membership.KIND_USER)
# GitHub answered a bot's account, and `PM_INVOKER_LOGIN` names alice, the
# person the agent works for (DEC-076 point 3).
FROM_VARIABLE = membership.Identity(
    github_login="robot[bot]", email=None, kind=membership.KIND_BOT, works_for="alice"
)


def _refusal(
    monkeypatch: pytest.MonkeyPatch,
    login: str,
    answers: dict[str, membership.LookedUp] | None = None,
    *,
    invoker: membership.Identity | None = FROM_SERVICE,
    config: dict[str, Any] | None = None,
) -> tuple[str | None, list[str]]:
    asked = pm_assignee_lookup.answer(monkeypatch, answers)
    return assignees.refusal(login, invoker, config), asked


@pytest.mark.parametrize("login", ["robot[bot]", "Robot[BOT]", "app/robot"])
def test_a_bots_spelling_is_refused_with_no_request(monkeypatch, login) -> None:
    refused, asked = _refusal(monkeypatch, login)
    assert refused is not None
    assert "names a bot's account, and an assignee names a person" in refused
    assert asked == []


@pytest.mark.parametrize("login", ["@alice", "alice smith", "-alice"])
def test_a_string_with_no_spelling_is_refused_with_no_request(monkeypatch, login) -> None:
    refused, asked = _refusal(monkeypatch, login)
    assert refused is not None and "names no account" in refused
    assert asked == []


def test_the_account_github_answered_the_credential_acts_as_needs_no_lookup(monkeypatch) -> None:
    refused, asked = _refusal(monkeypatch, "alice")
    assert refused is None
    assert asked == []


def test_a_login_the_variable_names_is_looked_up(monkeypatch) -> None:
    """`PM_INVOKER_LOGIN` names the person the agent works for, which is no
    answer of GitHub's about the credential, so its login is confirmed."""
    refused, asked = _refusal(monkeypatch, "alice", invoker=FROM_VARIABLE)
    assert refused is None
    assert asked == ["alice"]


def test_another_bare_login_is_assigned_where_github_answers_a_users_account(
    monkeypatch,
) -> None:
    refused, asked = _refusal(monkeypatch, "bob")
    assert refused is None
    assert asked == ["bob"]


@pytest.mark.parametrize("kind", ["Bot", "Organization", "Mannequin"])
def test_a_bare_login_github_answers_as_another_kind_is_refused(monkeypatch, kind) -> None:
    """The service's own coding agent is assigned by a login with no suffix."""
    answers = {"Copilot": membership.LookedUp(login="Copilot", account_type=kind)}
    refused, _asked = _refusal(monkeypatch, "Copilot", answers)
    assert refused == (
        f"`Copilot` names an account of type {kind}, not a user's, and an assignee "
        "names a person (DEC-079 point 1)."
    )


def test_a_lookup_that_gives_no_answer_refuses_with_its_cause(monkeypatch) -> None:
    cause = "`gh api users/bob` failed: HTTP 502"
    refused, _asked = _refusal(monkeypatch, "bob", {"bob": membership.LookedUp(cause=cause)})
    assert refused is not None
    assert refused.startswith(f"could not confirm that `bob` names a user's account: {cause}.")
    assert "Run the command again once GitHub answers." in refused


def test_no_account_on_the_public_host_says_to_check_the_login(monkeypatch) -> None:
    refused, _asked = _refusal(monkeypatch, "bbo", {"bbo": membership.LookedUp(missing=True)})
    assert refused == "no account on GitHub has the login `bbo`: check the login."


def test_no_account_on_another_host_reads_as_a_login_mistyped_or_hidden(monkeypatch) -> None:
    refused, _asked = _refusal(
        monkeypatch,
        "bob",
        {"bob": membership.LookedUp(missing=True)},
        config={"gh": {"host": "github.example.com"}},
    )
    assert refused is not None
    assert refused.startswith("github.example.com knows no account `bob` that this credential")
    assert "running the command again changes neither" in refused
    assert "run the command under a credential that sees the account" in refused


def test_each_assignee_is_confirmed_once_and_the_first_refusal_is_given(monkeypatch) -> None:
    asked = pm_assignee_lookup.answer(
        monkeypatch, {"carol": membership.LookedUp(login="carol", account_type="Bot")}
    )
    refused = assignees.first_refusal(["bob", "bob", "carol", "dave"], FROM_SERVICE, None)
    assert refused is not None and "`carol` names an account of type Bot" in refused
    assert asked == ["bob", "carol"]
