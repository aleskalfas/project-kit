"""The check that holds a document to its contract fails on each break ADR-097 rules out
(`tests/document_contracts.py`, points 4, 5 and 7).

Each test pins a small contract, prints a document that keeps it or breaks it in one
way, and reads what the check says.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from tests.document_contracts import ANY, Contract, Document, Form, check, judge, shape

KEYS = {
    "schema_version": "int",
    "outcome": "str",
    "why": "str|null",
    "findings": "list",
    "findings[]": "object",
    "findings[].kind": "str",
}

CONTRACT = Contract(
    name="a document",
    version=1,
    forms={"answer": Form(keys=KEYS)},
    sets={"outcome": frozenset({"passed", "failed"}), "findings[].kind": frozenset({"stale"})},
)


#: What `_document` leaves out of the document for a key given it.
_LEFT_OUT = object()


def _document(**changes: Any) -> dict[str, Any]:
    document: dict[str, Any] = {
        "schema_version": 1,
        "outcome": "passed",
        "why": None,
        "findings": [{"kind": "stale"}],
    }
    document.update(changes)
    return {key: value for key, value in document.items() if value is not _LEFT_OUT}


def _problems(
    contract: Contract,
    *documents: Document,
    enumerations: Mapping[str, Any] | None = None,
) -> list[str]:
    return judge(contract, {"answer": documents}, enumerations=enumerations or {})


def _said(problems: list[str], *words: str) -> bool:
    return any(all(word in problem for word in words) for problem in problems)


def test_a_document_that_keeps_its_contract_passes() -> None:
    check(CONTRACT, {"answer": [_document(), _document(outcome="failed", why="a reason")]})


def test_a_key_added_and_not_pinned_fails_until_it_is_pinned() -> None:
    problems = _problems(CONTRACT, _document(new=True), _document(outcome="failed"))
    assert _said(problems, "`new`", "not pinned")
    pinned = Contract(
        name="a document",
        version=1,
        forms={"answer": Form(keys={**KEYS, "new": "bool"})},
        sets=CONTRACT.sets,
    )
    assert _problems(pinned, _document(new=True), _document(outcome="failed")) == []


def test_a_key_that_goes_fails() -> None:
    problems = _problems(
        CONTRACT, _document(why=_LEFT_OUT), _document(outcome="failed", why=_LEFT_OUT)
    )
    assert _said(problems, "`why`", "no document printed it", "major")


def test_a_key_that_went_and_comes_back_fails() -> None:
    gone = Contract(
        name="a document",
        version=2,
        forms={"answer": Form(keys={k: v for k, v in KEYS.items() if k != "why"}, gone={"why": 2})},
        sets=CONTRACT.sets,
    )
    assert (
        _problems(
            gone,
            _document(schema_version=2, why=_LEFT_OUT),
            _document(schema_version=2, outcome="failed", why=_LEFT_OUT),
        )
        == []
    )
    problems = _problems(
        gone, _document(schema_version=2), _document(schema_version=2, outcome="failed")
    )
    assert _said(problems, "`why`", "went", "never comes back")


def test_a_key_gone_without_its_version_rising_fails() -> None:
    unraised = Contract(
        name="a document",
        version=1,
        forms={"answer": Form(keys={k: v for k, v in KEYS.items() if k != "why"}, gone={"why": 2})},
        sets=CONTRACT.sets,
    )
    problems = _problems(
        unraised, _document(why=_LEFT_OUT), _document(outcome="failed", why=_LEFT_OUT)
    )
    assert _said(problems, "version 2 dropped", "at version 1")


def test_a_version_raised_with_nothing_gone_fails_unless_it_came_before_the_rule() -> None:
    raised = Contract(name="a document", version=2, forms=CONTRACT.forms, sets=CONTRACT.sets)
    documents = (_document(schema_version=2), _document(schema_version=2, outcome="failed"))
    assert _said(_problems(raised, *documents), "version 2 was raised with no key or value gone")
    before = Contract(
        name="a document",
        version=2,
        forms=CONTRACT.forms,
        sets=CONTRACT.sets,
        raised_before={2: "a meaning changed before ADR-097"},
    )
    assert _problems(before, *documents) == []


def test_a_version_other_than_the_contract_s_fails() -> None:
    problems = _problems(CONTRACT, _document(schema_version=2), _document(outcome="failed"))
    assert _said(problems, "carries schema_version 2")


def test_a_value_of_another_type_fails() -> None:
    problems = _problems(CONTRACT, _document(why=3), _document(outcome="failed"))
    assert _said(problems, "`why` printed a int", "never changes")


def test_a_value_not_listed_fails_until_it_is_listed() -> None:
    problems = _problems(CONTRACT, _document(outcome="skipped"), _document(outcome="failed"))
    assert _said(problems, "`outcome` printed 'skipped'", "does not list")


def test_a_value_that_goes_fails() -> None:
    assert _said(_problems(CONTRACT, _document()), "`outcome` lists 'failed', which nothing gives")


def test_a_value_that_went_and_comes_back_fails() -> None:
    gone = Contract(
        name="a document",
        version=2,
        forms=CONTRACT.forms,
        sets={**CONTRACT.sets, "outcome": frozenset({"passed"})},
        gone_values={"outcome": {"failed": 2}},
    )
    documents = (_document(schema_version=2), _document(schema_version=2, outcome="failed"))
    assert _said(_problems(gone, *documents), "`outcome` printed 'failed', which went at version 2")


def test_an_enumeration_holds_a_set_the_documents_print_only_part_of() -> None:
    enumerated = {"outcome": ("passed", "failed")}
    assert _problems(CONTRACT, _document(), enumerations=enumerated) == []
    problems = _problems(
        CONTRACT, _document(), enumerations={"outcome": ("passed", "failed", "new")}
    )
    assert _said(problems, "`outcome` may take 'new'", "does not list")
    problems = _problems(CONTRACT, _document(), enumerations={"outcome": ("passed",)})
    assert _said(problems, "`outcome` lists 'failed', which nothing gives")


def test_a_key_that_leaves_one_form_goes_from_it() -> None:
    forms = Contract(
        name="a document",
        version=1,
        forms={
            "answer": Form(keys={"schema_version": "int", "why": "null"}),
            "no answer": Form(keys={"schema_version": "int", "why": "str"}),
        },
    )
    printed = {"answer": [{"schema_version": 1}], "no answer": [{"schema_version": 1, "why": "x"}]}
    problems = judge(forms, printed, enumerations={})
    assert _said(problems, "`why` is pinned in the form 'answer'", "no document printed it")


def test_a_shape_is_pinned_once_and_a_key_none_of_its_places_print_goes() -> None:
    shaped = Contract(
        name="a document",
        forms={"answer": Form(keys={"base": "object|null", "head": "object|null"})},
        shapes={"side": Form(keys={"commit": "str", "rules": "list", "rules[]": "str"})},
        refs={"base": "side", "head": "side"},
    )
    printed = [
        {"base": {"commit": "a", "rules": ["r"]}, "head": None},
        {"base": None, "head": {"commit": "b", "rules": []}},
    ]
    assert _problems(shaped, *printed) == []
    problems = _problems(shaped, {"base": {"commit": "a"}, "head": {"commit": "b", "extra": 1}})
    assert _said(problems, "`side:rules` is pinned in the shape 'side'", "no document printed it")
    assert _said(problems, "`side:extra` is printed in the shape 'side' and not pinned")


def test_a_mapping_keyed_by_data_names_its_entries_and_a_payload_is_not_walked() -> None:
    keyed = Contract(
        name="a document",
        forms={
            "answer": Form(
                keys={"types": "object", "types{}": "object", "types{}.owner": "str", "value": ANY}
            )
        },
        data=frozenset({"types"}),
        payloads=frozenset({"value"}),
    )
    document = {
        "types": {"a": {"owner": "x"}, "b": {"owner": "y"}},
        "value": {"any": [1, {"k": 2}]},
    }
    assert _problems(keyed, document) == []


def test_a_document_that_is_a_list_names_its_items_from_the_root() -> None:
    listed = Contract(
        name="a list",
        forms={"answer": Form(keys={"[]": "object", "[].label": "str", "[].why": "str|null"})},
        sets={"[].label": frozenset({"a", "b"})},
    )
    assert _problems(listed, [{"label": "a", "why": None}, {"label": "b", "why": "w"}]) == []
    problems = _problems(listed, [{"label": "c"}])
    assert _said(problems, "`[].label` printed 'c', which its contract does not list")
    assert _said(problems, "`[].why` is pinned in the form 'answer' and no document printed it")


def test_a_contract_that_contradicts_itself_fails() -> None:
    broken = Contract(
        name="a document",
        version=1,
        forms={"answer": Form(keys={"schema_version": "int", "x": "string"}, gone={"x": 2})},
        sets={"y": frozenset({"a"})},
        refs={"x": "nowhere"},
    )
    problems = _problems(broken, {"schema_version": 1, "x": "v"})
    assert _said(problems, "`x` is pinned and gone at once")
    assert _said(problems, "`x` is typed 'string'")
    assert _said(problems, "`y` is named in `sets` and pinned nowhere")
    assert _said(problems, "`x` holds the shape 'nowhere'")


def test_a_form_no_document_was_printed_in_fails() -> None:
    problems = judge(CONTRACT, {}, enumerations={})
    assert _said(problems, "no document of the form 'answer' was printed")


def test_the_shape_of_documents_is_read_to_pin_them() -> None:
    assert shape(CONTRACT, [_document(), _document(why="w")]) == {
        "findings": "list",
        "findings[]": "object",
        "findings[].kind": "str",
        "outcome": "str",
        "schema_version": "int",
        "why": "null|str",
    }


def test_check_names_the_document_and_each_problem() -> None:
    with pytest.raises(AssertionError, match=r"a document:\n  - `new` is printed"):
        check(CONTRACT, {"answer": [_document(new=1), _document(outcome="failed")]})
