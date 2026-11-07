"""The JSON code writer, spelling form 1 (visual-communication DEC-004 point 4, DEC-005 points 7
to 9): the document written unchanged in one fixed text, the reference output pinned to its
version, the schema it holds to, and what it refuses. What a run and the check make of its
code is in `test_visual_communication_code.py`, as for any code writer."""

from __future__ import annotations

import ast
import json
from collections.abc import Mapping
from typing import Any

import pytest

from tests.in_process import load
from tests.visual_communication_project import (
    CAPABILITY,
    FIXTURES,
    FOUNDATIONS,
    TEST_BRAND,
    TEST_PARTS,
)

writer, writer_declaration, seam, values, tokens, files, reading = load(
    "visual-communication",
    "plugins.json",
    "plugins.json_declaration",
    "plugins.seam",
    "values",
    "tokens",
    "files",
    "reading",
)

LOCK = {"foundations": "1.0.0", "test-brand": "1.0.0"}

#: The file the writer writes for the test brand, by the writer's version. A change of output
#: is a new version of the writer (DEC-005 point 9): add its reference here.
REFERENCE = {"1.0.0": FIXTURES / "reference" / "json-1.0.0.json"}


@pytest.fixture(scope="module")
def brand() -> Any:
    return tokens.read_brand(TEST_BRAND, tokens.read_declarations(FOUNDATIONS / "roles.yaml"))


@pytest.fixture(scope="module")
def document(brand: Any) -> dict[str, Any]:
    """The test brand's values document."""
    return values.document(brand, brand.combinations(), LOCK)


def written(document: Mapping[str, Any], **options: Any) -> str:
    return writer.write(document, {}, **options)


def small(type_: str = "number", value: Any = 1) -> dict[str, Any]:
    """A document of one token in one combination."""
    token = {"type": type_, "values": {"default": value}}
    return {
        "document": "visual-communication/values",
        "version": 1,
        "lock": {"lab": "1.0.0"},
        "keys": ["default"],
        "tokens": {"a.b": token},
    }


#: A value of each type a document can hold.
OF_EACH_TYPE = {
    "color": {"colorSpace": "srgb", "components": [0, 0.5, 1], "alpha": 0.5},
    "dimension": {"value": 1.5, "unit": "px"},
    "fontFamily": ["Source Sans Pro", "Arial"],
    "fontWeight": 700,
    "number": 1.4,
    "typography": {
        "fontFamily": ["Source Sans Pro"],
        "fontSize": {"value": 16, "unit": "px"},
        "fontWeight": 400,
        "letterSpacing": {"value": 0, "unit": "px"},
        "lineHeight": 1.4,
    },
}


def reversed_mappings(value: Any) -> Any:
    """`value` with every mapping in it, however deep, in the opposite order."""
    if isinstance(value, Mapping):
        return {key: reversed_mappings(value[key]) for key in reversed(list(value))}
    return value


# --- the file -----------------------------------------------------------------------------------


def test_the_test_brand_gives_the_reference_file_of_the_writers_version(
    document: dict[str, Any],
) -> None:
    assert writer.VERSION in REFERENCE, f"no reference output for the json writer {writer.VERSION}"
    assert written(document) == REFERENCE[writer.VERSION].read_text(encoding="utf-8")


def test_the_file_is_the_document_unchanged(document: dict[str, Any]) -> None:
    assert json.loads(written(document)) == document


def test_a_typography_is_written_with_its_five_members(document: dict[str, Any]) -> None:
    assert json.loads(written(document))["tokens"]["type.body"]["values"]["default"] == {
        "fontFamily": ["Source Sans Pro"],
        "fontSize": {"value": 16, "unit": "px"},
        "fontWeight": 400,
        "letterSpacing": {"value": 0, "unit": "px"},
        "lineHeight": 1.4,
    }


def test_every_value_type_the_document_can_hold_is_written() -> None:
    assert set(OF_EACH_TYPE) == set(tokens.TYPES)
    held = {
        f"of.{type_.lower()}": {"type": type_, "values": {"default": value}}
        for type_, value in OF_EACH_TYPE.items()
    }
    document = {**small(), "tokens": held}
    assert json.loads(written(document)) == document
    assert files.shape_problems(json.loads(written(document)), "values") == []


def test_each_set_of_values_is_named_by_the_key_of_its_combination(
    document: dict[str, Any],
) -> None:
    held = json.loads(written(document))
    assert held["keys"] == [
        "default",
        "colour-scheme.dark",
        "contrast.high",
        "colour-scheme.dark+contrast.high",
    ]
    assert all(list(token["values"]) == held["keys"] for token in held["tokens"].values())


def test_a_token_path_stays_as_the_brand_exports_it(document: dict[str, Any]) -> None:
    assert list(json.loads(written(document))["tokens"]) == sorted(document["tokens"])


def test_the_roles_of_a_library_locked_with_the_brand_are_written() -> None:
    scope = tokens.read_scope({"foundations": FOUNDATIONS, "test-parts": TEST_PARTS})
    brand = tokens.read_brand(TEST_BRAND, scope)
    document = values.document(brand, brand.combinations(), {**LOCK, "test-parts": "1.0.0"})
    held = json.loads(written(document))
    assert held["lock"]["test-parts"] == "1.0.0"
    assert held["tokens"]["test-parts.note"] == {
        **held["tokens"]["text-primary"],
        "type": "color",
    }


# --- one fixed text -----------------------------------------------------------------------------


def test_one_document_gives_one_file_whatever_the_order_of_its_mappings(
    document: dict[str, Any],
) -> None:
    shuffled = reversed_mappings(document)
    assert list(shuffled["tokens"]) != list(document["tokens"])
    assert written(shuffled) == written(document)


def test_the_fields_come_in_the_order_the_document_gives_them(document: dict[str, Any]) -> None:
    assert list(json.loads(written(document))) == ["document", "version", "lock", "keys", "tokens"]


def test_a_changed_value_changes_one_line(document: dict[str, Any]) -> None:
    changed = json.loads(json.dumps(document))
    changed["tokens"]["accent"]["values"]["contrast.high"]["alpha"] = 0.5
    before, after = written(document).splitlines(), written(changed).splitlines()
    assert len(before) == len(after)
    differing = [(old, new) for old, new in zip(before, after, strict=True) if old != new]
    assert len(differing) == 1
    assert differing[0][1].startswith('        "contrast.high": {"alpha":0.5,')


@pytest.mark.parametrize(
    ("type_", "value", "line"),
    [
        ("number", 16.0, "16"),
        ("number", 1.4, "1.4"),
        ("number", 1e21, "1e+21"),
        ("fontWeight", 700, "700"),
        ("dimension", {"value": 1.50, "unit": "px"}, '{"unit":"px","value":1.5}'),
        ("fontFamily", ["Šumava Sans"], '["Šumava Sans"]'),
        ("fontFamily", ['Say "hi"', "back\\slash"], r'["Say \"hi\"","back\\slash"]'),
    ],
)
def test_a_value_keeps_to_one_line_in_the_canonical_text(type_: str, value: Any, line: str) -> None:
    assert f'        "default": {line}\n' in written(small(type_, value))


def test_the_text_is_exact_and_ends_in_one_line_feed() -> None:
    assert written(small()) == (
        "{\n"
        '  "document": "visual-communication/values",\n'
        '  "version": 1,\n'
        '  "lock": {\n'
        '    "lab": "1.0.0"\n'
        "  },\n"
        '  "keys": ["default"],\n'
        '  "tokens": {\n'
        '    "a.b": {\n'
        '      "type": "number",\n'
        '      "values": {\n'
        '        "default": 1\n'
        "      }\n"
        "    }\n"
        "  }\n"
        "}\n"
    )


def test_a_document_of_no_token_is_written() -> None:
    assert '  "tokens": {}\n}\n' in written({**small(), "tokens": {}})


# --- the schema ---------------------------------------------------------------------------------


def test_the_file_holds_the_schema_of_the_document(document: dict[str, Any]) -> None:
    assert files.shape_problems(json.loads(written(document)), "values") == []


def test_the_schema_names_the_version_of_the_document_the_writer_writes() -> None:
    schema = reading.read_json(CAPABILITY / "schemas" / "values.schema.json")
    assert schema["properties"]["document"]["const"] == values.DOCUMENT
    assert schema["properties"]["version"]["const"] == values.VERSION
    assert set(schema["$defs"]["token"]["properties"]["type"]["enum"]) == set(tokens.TYPES)
    assert set(schema["$defs"]["typography"]["required"]) == set(tokens.TYPOGRAPHY)


# --- what it refuses ----------------------------------------------------------------------------


def test_it_refuses_another_form_or_document_and_a_prefix(document: dict[str, Any]) -> None:
    with pytest.raises(writer.JsonError, match="form 2"):
        written(document, form=2)
    with pytest.raises(writer.JsonError, match="document"):
        written({**document, "version": 2})
    with pytest.raises(writer.JsonError, match="document"):
        written({**document, "document": "another"})
    with pytest.raises(writer.JsonError, match="a token path stays as the brand exports it"):
        written(document, prefix="brand")


@pytest.mark.parametrize(
    ("type_", "value"),
    [("number", float("inf")), ("fontFamily", ["lone \ud800"])],
    ids=["infinity", "lone-surrogate"],
)
def test_it_refuses_what_a_json_file_cannot_hold(type_: str, value: Any) -> None:
    with pytest.raises(writer.JsonError, match="cannot"):
        written(small(type_, value))


# --- its declaration ----------------------------------------------------------------------------


def test_its_declaration_is_plain_data_the_seam_ships_as_a_code_writer() -> None:
    source = (CAPABILITY / "scripts/_lib/plugins/json_declaration.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert not [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]
    found = seam.declaration("json", seam.CODE_WRITER)
    assert found is writer_declaration.DECLARATION
    assert found["module"] == "json"
    assert found["forms"] == [1]
    assert found["prefix"] is False
    assert found["programs"] == [] and found["services"] == []
    assert found["version"] == writer.VERSION


def test_it_declares_every_type_and_kind_the_document_can_hold() -> None:
    assert set(writer_declaration.DECLARATION["kinds"]) == set(tokens.TYPES)
    assert set(writer_declaration.DECLARATION["axis-kinds"]) == set(tokens.AXIS_KINDS)
