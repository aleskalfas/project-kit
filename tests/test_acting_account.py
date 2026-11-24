"""The reading of the acting account, and the one spelling it compares accounts in
(ADR-094).

The reading asks a `gh` of the test's own, first on PATH, which answers `gh api user`
as the service would: a user's account, an App's, a refusal of an installation's
token, another refusal, or nothing. No test reaches GitHub.
"""

from __future__ import annotations

import os
import shlex
import stat
from pathlib import Path

import pytest

from project_kit import acting_account as aa
from project_kit.acting_account import (
    ANSWER_CANNOT_TELL,
    ANSWER_ONE,
    ANSWER_TWO,
    FormError,
    compare,
    fold,
    spell,
)

INTEGRATION_BODY = (
    '{"message":"Resource not accessible by integration",'
    '"documentation_url":"https://docs.github.com/rest/users/users","status":"403"}'
)


def _gh(folder: Path, monkeypatch: pytest.MonkeyPatch, script: str) -> Path:
    """Put first on PATH a `gh` that runs `script` for `gh api user`, and records each
    call in `calls`."""
    folder.mkdir(parents=True, exist_ok=True)
    calls = folder / "calls"
    gh = folder / "gh"
    gh.write_text(
        f'#!/bin/sh\necho "$@" >> {shlex.quote(str(calls))}\n'
        f'if [ "$1" = api ] && [ "$2" = user ]; then\n{script}\nfi\nexit 127\n',
        encoding="utf-8",
    )
    gh.chmod(gh.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", f"{folder}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.delenv(aa.OFFLINE_VARIABLE, raising=False)
    aa.forget_service_answers()
    return calls


def _answers(folder: Path, monkeypatch: pytest.MonkeyPatch, *fields: str) -> Path:
    line = "\\t".join(fields)
    return _gh(folder, monkeypatch, f"printf '{line}\\n'; exit 0")


def _refuses(folder: Path, monkeypatch: pytest.MonkeyPatch, body: str, said: str) -> Path:
    script = f"printf '%s' {shlex.quote(body)}; echo {shlex.quote(said)} >&2; exit 1"
    return _gh(folder, monkeypatch, script)


# --- the reading -----------------------------------------------------------------------


def test_a_users_account_resolves_with_its_kind_and_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _answers(tmp_path, monkeypatch, "Octocat", "User", "583231")
    reading = aa.read()
    assert reading.document() == {
        "schema_version": 1,
        "account": "Octocat",
        "kind": "user",
        "id": 583231,
        "login": "Octocat",
        "cause": None,
        "reason": None,
    }


def test_a_login_with_the_suffix_is_a_bots_whatever_type_it_is_given(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _answers(tmp_path, monkeypatch, "robot[bot]", "User", "7")
    reading = aa.read()
    assert (reading.account, reading.kind) == ("robot[bot]", "bot")


def test_the_integrations_refusal_is_an_unnamed_account(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _refuses(
        tmp_path,
        monkeypatch,
        INTEGRATION_BODY,
        "gh: Resource not accessible by integration (HTTP 403)",
    )
    reading = aa.read()
    assert reading.account is None
    assert reading.cause == aa.CAUSE_INTEGRATION_REFUSED
    assert reading.unnamed
    assert reading.reason is not None
    assert "Resource not accessible by integration" in reading.reason


def test_an_account_of_a_kind_unknown_is_an_unnamed_account(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _answers(tmp_path, monkeypatch, "acme", "Organization", "9")
    reading = aa.read()
    document = reading.document()
    assert (document["account"], document["kind"], document["id"], document["login"]) == (
        None,
        None,
        None,
        None,
    )
    assert reading.cause == aa.CAUSE_KIND_UNKNOWN
    assert reading.unnamed


@pytest.mark.parametrize(
    ("body", "said", "cause"),
    [
        (
            '{"message":"Bad credentials","status":"401"}',
            "gh: Bad credentials (HTTP 401)",
            "refused",
        ),
        (
            '{"message":"API rate limit exceeded","status":"403"}',
            "gh: API rate limit exceeded (HTTP 403)",
            "refused",
        ),
        ('{"message":"Server Error"}', "gh: Server Error (HTTP 502)", "no-answer"),
        ("", "error connecting to api.github.com", "no-answer"),
    ],
    ids=["bad-credentials", "rate-limit", "server-error", "no-network"],
)
def test_every_other_failure_is_an_unresolved_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, body: str, said: str, cause: str
) -> None:
    _refuses(tmp_path, monkeypatch, body, said)
    reading = aa.read()
    assert reading.account is None
    assert reading.cause == cause
    assert not reading.unnamed


def test_an_answer_that_names_no_account_is_unresolved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _gh(tmp_path, monkeypatch, "exit 0")
    assert aa.read().cause == aa.CAUSE_NO_ACCOUNT


def test_gh_missing_is_unresolved(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.delenv(aa.OFFLINE_VARIABLE, raising=False)
    aa.forget_service_answers()
    assert aa.read().cause == aa.CAUSE_GH_MISSING


def test_the_offline_marker_asks_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _answers(tmp_path, monkeypatch, "octocat", "User", "1")
    monkeypatch.setenv(aa.OFFLINE_VARIABLE, "1")
    assert aa.read().cause == aa.CAUSE_OFFLINE
    assert not calls.exists()


def test_a_read_that_runs_out_of_time_is_unresolved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _gh(tmp_path, monkeypatch, "sleep 5; exit 0")
    monkeypatch.setattr(aa, "READ_SECONDS", 0.2)
    assert aa.read().cause == aa.CAUSE_TIMEOUT


def test_an_answer_lasts_the_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _answers(tmp_path, monkeypatch, "octocat", "User", "1")
    assert aa.read() is aa.read()
    assert len(calls.read_text(encoding="utf-8").splitlines()) == 1
    aa.forget_service_answers()
    aa.read()
    assert len(calls.read_text(encoding="utf-8").splitlines()) == 2


# --- the spelling ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("login", "form", "extra", "spelled", "kind"),
    [
        ("alice", "entry", {}, "alice", "user"),
        ("claude[bot]", "entry", {}, "claude[bot]", "bot"),
        ("app/claude", "entry", {}, "claude[bot]", "bot"),
        ("  Alice ", "entry", {}, "Alice", "user"),
        ("alice", "typed", {"account_type": "User"}, "alice", "user"),
        ("robot[bot]", "typed", {"account_type": "Bot"}, "robot[bot]", "bot"),
        ("copilot", "typed", {"account_type": "Bot"}, None, None),
        ("acme", "typed", {"account_type": "Organization"}, None, None),
        ("alice", "gh", {"account_id": 1, "is_bot": False}, "alice", "user"),
        ("alice", "gh", {"account_id": "MDQ6VXNlcjE=", "is_bot": False}, "alice", "user"),
        ("alice", "gh", {"account_id": "", "is_bot": False}, None, None),
        ("app/claude", "gh", {"is_bot": True}, None, None),
        ("alice", "gh", {"is_bot": False}, None, None),
        ("alice", "users-field", {}, "alice", "user"),
        ("alice", "login", {}, None, None),
        ("claude[bot]", "login", {}, "claude[bot]", "bot"),
        ("app/claude", "login", {}, None, None),
    ],
)
def test_the_kind_comes_from_the_form(
    login: str, form: str, extra: dict, spelled: str | None, kind: str | None
) -> None:
    account = spell(login, form, **extra)
    assert (account.account, account.kind) == (spelled, kind)
    assert account.login == login


@pytest.mark.parametrize(
    "login", ["", "  ", "@alice", "al ice", "ålice", "app/x[bot]", "app/", "[bot]", "a.b"]
)
def test_a_string_no_login_can_be_has_no_spelling(login: str) -> None:
    account = spell(login, "entry")
    assert account.account is None
    assert account.kind is None
    assert account.reason is not None
    assert compare(account, spell(login, "entry")) == ANSWER_CANNOT_TELL


def test_an_unknown_form_is_refused() -> None:
    with pytest.raises(FormError):
        spell("alice", "nickname")


# --- the comparison --------------------------------------------------------------------


def _entry(login: str) -> aa.Account:
    return spell(login, "entry")


@pytest.mark.parametrize(
    ("left", "right", "answer"),
    [
        (_entry("alice"), _entry("ALICE "), ANSWER_ONE),
        (_entry("alice"), _entry("bob"), ANSWER_TWO),
        (_entry("claude"), _entry("claude[bot]"), ANSWER_TWO),
        (_entry("app/claude"), _entry("Claude[bot]"), ANSWER_ONE),
        (_entry("alice"), spell("bob", "login"), ANSWER_TWO),
        (_entry("alice"), spell("alice", "login"), ANSWER_CANNOT_TELL),
        (_entry("claude[bot]"), spell("app/claude", "gh", is_bot=True), ANSWER_CANNOT_TELL),
        (_entry("claude[bot]"), spell("other", "login"), ANSWER_CANNOT_TELL),
        (spell("x", "login"), spell("y", "login"), ANSWER_CANNOT_TELL),
        (_entry("@alice"), _entry("alice"), ANSWER_CANNOT_TELL),
    ],
)
def test_what_a_comparison_answers(left: aa.Account, right: aa.Account, answer: str) -> None:
    assert compare(left, right) == answer
    assert compare(right, left) == answer


def test_case_is_set_aside_only_for_ascii_letters() -> None:
    # The Kelvin sign folds to `k` in Unicode, and no login holds it.
    kelvin = chr(0x212A)
    assert compare(_entry("kelly"), _entry(f"{kelvin}elly")) == ANSWER_CANNOT_TELL


@pytest.mark.parametrize(
    ("answers", "folded"),
    [
        ([ANSWER_TWO, ANSWER_ONE], ANSWER_ONE),
        ([ANSWER_TWO, ANSWER_TWO], ANSWER_TWO),
        ([], ANSWER_TWO),
        ([ANSWER_TWO, ANSWER_CANNOT_TELL], ANSWER_CANNOT_TELL),
        ([ANSWER_CANNOT_TELL, ANSWER_ONE], ANSWER_ONE),
        ([ANSWER_TWO, "maybe"], ANSWER_CANNOT_TELL),
    ],
)
def test_one_against_many_folds_the_answers(answers: list[str], folded: str) -> None:
    assert fold(answers) == folded


def test_the_compare_document_answers_pairs_and_folds_in_order() -> None:
    document = aa.compare_document(
        {
            "pairs": [
                [{"form": "entry", "login": "claude"}, {"form": "entry", "login": "app/claude"}],
            ],
            "folds": [
                {
                    "account": {"form": "typed", "login": "Bob", "type": "User"},
                    "among": [
                        {"form": "entry", "login": "alice"},
                        {"form": "entry", "login": "bob"},
                    ],
                }
            ],
        }
    )
    assert [pair["answer"] for pair in document["pairs"]] == [ANSWER_TWO]
    [question] = document["folds"]
    assert question["answer"] == ANSWER_ONE
    assert [entry["answer"] for entry in question["among"]] == [ANSWER_TWO, ANSWER_ONE]


def test_a_request_gives_gh_s_author_as_gh_prints_it() -> None:
    # gh's JSON gives an author's id as its node id, a string, and an app's as
    # `app/<name>` with its bot flag.
    document = aa.spell_document(
        {
            "accounts": [
                {"form": "gh", "login": "alice", "id": "MDQ6VXNlcjE=", "is_bot": False},
                {"form": "gh", "login": "app/claude", "id": "BOT_kgDO", "is_bot": True},
                {"form": "gh", "login": "alice", "id": True, "is_bot": False},
            ]
        }
    )
    assert [(one["account"], one["kind"]) for one in document["accounts"]] == [
        ("alice", "user"),
        (None, None),
        (None, None),
    ]


@pytest.mark.parametrize(
    "request_",
    [
        [],
        {"accounts": "alice"},
        {"accounts": [{"login": "alice"}]},
        {"accounts": [{"form": "entry"}]},
        {"accounts": [{"form": "nickname", "login": "alice"}]},
        {"accounts": ["alice"]},
    ],
)
def test_a_malformed_request_to_spell_is_refused(request_: object) -> None:
    with pytest.raises(FormError):
        aa.spell_document(request_)


@pytest.mark.parametrize(
    "request_",
    [
        {"pairs": [[{"form": "entry", "login": "a"}]]},
        {"pairs": "a"},
        {"folds": [{"account": {"form": "entry", "login": "a"}}]},
        {"folds": ["a"]},
    ],
)
def test_a_malformed_request_to_compare_is_refused(request_: object) -> None:
    with pytest.raises(FormError):
        aa.compare_document(request_)


@pytest.mark.parametrize(
    ("account", "searched"),
    [("alice", "alice"), ("claude[bot]", "app/claude"), ("Claude[bot]", "app/Claude")],
)
def test_the_search_names_a_bot_as_gh_s_search_does(account: str, searched: str) -> None:
    assert aa.search_name(account) == searched
