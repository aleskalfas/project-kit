"""The documents `pkit account` prints hold their contracts (ADR-097 point 7; ADR-094
point 1).

`account read` runs against a `gh` of the test's own for each outcome it names: a
user's account, a bot's, and the reading naming none. `account spell` and `account
compare` read their requests on standard input and ask GitHub nothing.
`tests/test_backbone_documents.py` gathers the contracts here into its ratchet.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from project_kit import acting_account as aa
from tests.backbone_documents import JSON_OPTION, document_of, invoke
from tests.document_contracts import Contract, Form, check
from tests.test_acting_account import INTEGRATION_BODY, _answers, _refuses

#: An account as `spell` and `compare` give it, wherever their documents hold one.
ACCOUNT = Form(
    keys={
        "account": "str|null",
        "kind": "str|null",
        "id": "null",
        "login": "str",
        "reason": "str|null",
    }
)

_KINDS = frozenset({aa.KIND_USER, aa.KIND_BOT})
_ANSWERS = frozenset({aa.ANSWER_ONE, aa.ANSWER_TWO, aa.ANSWER_CANNOT_TELL})

READ = Contract(
    name="pkit account read --json",
    version=1,
    forms={
        "answer": Form(
            keys={
                "schema_version": "int",
                "account": "str|null",
                "kind": "str|null",
                "id": "int|null",
                "login": "str|null",
                "cause": "str|null",
                "reason": "str|null",
            }
        )
    },
    sets={"kind": _KINDS, "cause": frozenset(aa.CAUSES)},
)

SPELL = Contract(
    name="pkit account spell --json",
    version=1,
    forms={
        "answer": Form(keys={"schema_version": "int", "accounts": "list", "accounts[]": "object"})
    },
    shapes={"account": ACCOUNT},
    refs={"accounts[]": "account"},
    sets={"account:kind": _KINDS},
)

COMPARE = Contract(
    name="pkit account compare --json",
    version=1,
    forms={
        "answer": Form(
            keys={
                "schema_version": "int",
                "pairs": "list",
                "pairs[]": "object",
                "pairs[].answer": "str",
                "pairs[].accounts": "list",
                "pairs[].accounts[]": "object",
                "folds": "list",
                "folds[]": "object",
                "folds[].answer": "str",
                "folds[].account": "object",
                "folds[].among": "list",
                "folds[].among[]": "object",
                "folds[].among[].answer": "str",
                "folds[].among[].account": "object",
            }
        )
    },
    shapes={"account": ACCOUNT},
    refs={
        "pairs[].accounts[]": "account",
        "folds[].account": "account",
        "folds[].among[].account": "account",
    },
    sets={
        "pairs[].answer": _ANSWERS,
        "folds[].answer": _ANSWERS,
        "folds[].among[].answer": _ANSWERS,
        "account:kind": _KINDS,
    },
)


def _read(folder: Path) -> dict[str, Any]:
    return document_of(invoke("account", "read", JSON_OPTION))


def test_the_account_read_document_holds_its_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    documents = []
    _answers(tmp_path / "user", monkeypatch, "octocat", "User", "583231")
    documents.append(_read(tmp_path))
    _answers(tmp_path / "bot", monkeypatch, "robot[bot]", "Bot", "7")
    documents.append(_read(tmp_path))
    _refuses(
        tmp_path / "app",
        monkeypatch,
        INTEGRATION_BODY,
        "gh: Resource not accessible by integration (HTTP 403)",
    )
    documents.append(_read(tmp_path))
    check(READ, {"answer": documents}, enumerations={"cause": aa.CAUSES})


def _spelled(*accounts: Mapping[str, Any]) -> dict[str, Any]:
    request = json.dumps({"accounts": list(accounts)})
    return document_of(invoke("account", "spell", JSON_OPTION, stdin=request))


def test_the_account_spell_document_holds_its_contract() -> None:
    document = _spelled(
        {"form": "entry", "login": "alice"},
        {"form": "entry", "login": "app/claude"},
        {"form": "login", "login": "alice"},
        {"form": "entry", "login": "@alice"},
    )
    check(SPELL, {"answer": [document]})


def test_the_account_compare_document_holds_its_contract() -> None:
    alice = {"form": "entry", "login": "alice"}
    request = {
        "pairs": [
            [alice, {"form": "users-field", "login": "Alice"}],
            [alice, {"form": "entry", "login": "claude[bot]"}],
            [alice, {"form": "login", "login": "alice"}],
        ],
        "folds": [{"account": alice, "among": [{"form": "entry", "login": "bob"}, alice]}],
    }
    document = document_of(invoke("account", "compare", JSON_OPTION, stdin=json.dumps(request)))
    answers = {name: aa.ANSWERS for name in COMPARE.sets if name.endswith("answer")}
    check(COMPARE, {"answer": [document]}, enumerations=answers)


@pytest.mark.parametrize(
    ("command", "request_"),
    [
        ("spell", '{"accounts": [{"form": "x", "login": "a"}]}'),
        ("compare", '{"pairs": [[{"form": "x", "login": "a"}, {"form": "entry", "login": "a"}]]}'),
        ("compare", "not json"),
    ],
)
def test_a_refused_request_prints_no_document(command: str, request_: str) -> None:
    result = invoke("account", command, JSON_OPTION, stdin=request_)
    assert result.exit_code == 1
    assert result.stdout == ""


CONTRACTS: Mapping[str, tuple[Contract, ...]] = {
    "account read": (READ,),
    "account spell": (SPELL,),
    "account compare": (COMPARE,),
}
