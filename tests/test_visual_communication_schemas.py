"""The capability's schemas, format 1 (DEC-002 point 3, DEC-003 point 1): one pair for each
kind of file, bound by `pkit_schema` alone, each reference instance and each shipped or
fixture file valid, and what format 1 refuses refused."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from tests.in_process import load
from tests.visual_communication_project import (
    FOUNDATIONS,
    SCHEMAS,
    TEST_BRAND,
    TEST_EDITION,
    TEST_NOTATION,
)

files, reading = load("visual-communication", "files", "reading")

COMPANIONS = sorted(SCHEMAS.glob("*.schema.json"))


def instance(kind: str) -> dict[str, Any]:
    """The reference instance of `kind`, to vary."""
    return reading.read_yaml(SCHEMAS / f"{kind}.yaml")


def refused(data: Any, kind: str) -> list[str]:
    return files.shape_problems(data, kind)


def test_each_kind_has_its_pair_and_the_shared_definitions_stand_alone() -> None:
    names = {path.name for path in SCHEMAS.iterdir()}
    wanted = {f"{kind}{suffix}" for kind in files.KINDS for suffix in (".yaml", ".schema.json")}
    assert names == wanted | {"defs.schema.json", ".gitkeep"}


@pytest.mark.parametrize("path", COMPANIONS, ids=lambda path: path.name)
def test_each_companion_is_a_draft_2020_12_schema_known_by_its_file_name(path: Path) -> None:
    schema = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"] == path.name


@pytest.mark.parametrize("kind", files.KINDS)
def test_each_kind_binds_by_pkit_schema_at_format_1_and_no_path(kind: str) -> None:
    schema = json.loads((SCHEMAS / f"{kind}.schema.json").read_text(encoding="utf-8"))
    assert schema["properties"]["pkit_schema"]["const"] == f"visual-communication:{kind}"
    assert schema["properties"]["schema_version"]["const"] == 1
    assert {"pkit_schema", "schema_version"} <= set(schema["required"])
    for path in (SCHEMAS / f"{kind}.yaml", SCHEMAS / f"{kind}.schema.json"):
        assert "binds_to" not in path.read_text(encoding="utf-8"), path.name


@pytest.mark.parametrize("kind", files.KINDS)
def test_each_reference_instance_holds_its_schema(kind: str) -> None:
    assert files.binding_problem(instance(kind), kind) is None
    assert refused(instance(kind), kind) == []


@pytest.mark.parametrize(
    ("path", "kind"),
    [
        (FOUNDATIONS / "library.yaml", "library"),
        (FOUNDATIONS / "roles.yaml", "roles"),
        (TEST_BRAND / "library.yaml", "library"),
        (TEST_EDITION / "library.yaml", "library"),
        (TEST_NOTATION / "library.yaml", "library"),
        (TEST_NOTATION / "notation.yaml", "notation"),
    ],
    ids=[
        "foundations-library",
        "foundations-roles",
        "test-brand-library",
        "test-edition-library",
        "test-notation-library",
        "test-notation-concepts",
    ],
)
def test_the_shipped_libraries_and_the_fixtures_hold_their_schemas(path: Path, kind: str) -> None:
    assert refused(reading.read_yaml(path), kind) == []


@pytest.mark.parametrize("kind", [kind for kind in files.KINDS if kind != "content"])
def test_each_kind_but_content_refuses_a_key_it_does_not_declare(kind: str) -> None:
    assert refused({**instance(kind), "binds_to": "x"}, kind) != []


def test_content_takes_names_at_its_top_and_the_reserved_keys_alone() -> None:
    assert (
        refused({**instance("content"), "legend": {}, "id": "intro", "pkit": {}}, "content") == []
    )
    assert refused({**instance("content"), "Legend": {}}, "content") != []
    assert refused({**instance("content"), "pkit": "x"}, "content") != []


# --- what format 1 refuses ----------------------------------------------------------------------


def test_a_piece_is_a_draft_in_format_1() -> None:
    assert refused({**instance("piece"), "state": "final"}, "piece") != []


def test_a_brand_names_its_dtcg_version_and_a_component_library_none() -> None:
    brand = {key: value for key, value in instance("library").items() if key != "dtcg"}
    assert refused(brand, "library") != []
    components = {**reading.read_yaml(FOUNDATIONS / "library.yaml"), "dtcg": "2025.10"}
    assert refused(components, "library") != []


@pytest.mark.parametrize(
    "concepts",
    [
        pytest.param({"person": {"colour": "#8250df"}}, id="value"),
        pytest.param({"person": "purple"}, id="family-alone"),
        pytest.param({"person": {"colour": "purple", "fill": "family.purple.fill"}}, id="role"),
        pytest.param({"Person": {"colour": "purple"}}, id="name"),
        pytest.param({}, id="none"),
    ],
)
def test_a_notation_maps_each_concept_to_a_colour_family_never_to_a_value(
    concepts: dict[str, Any],
) -> None:
    assert refused({**instance("notation"), "concepts": concepts}, "notation") != []


def test_a_piece_names_each_notation_once_by_its_library_s_name() -> None:
    assert instance("piece")["notations"] == ["test-notation"]
    assert refused({**instance("piece"), "notations": ["test-notation"] * 2}, "piece") != []
    assert refused({**instance("piece"), "notations": ["test-notation/person"]}, "piece") != []


def test_a_notation_names_no_dtcg_version_and_marks_no_base() -> None:
    notation = reading.read_yaml(TEST_NOTATION / "library.yaml")
    assert refused({**notation, "dtcg": "2025.10"}, "library") != []
    marked = [{**entry, "base": True} for entry in notation["builds-on"]]
    assert refused({**notation, "builds-on": marked}, "library") != []


def test_a_brand_marks_at_most_one_base_and_a_component_library_none() -> None:
    brand = instance("library")
    assert brand["builds-on"][1] == {"name": "test-brand", "major": 1, "base": True}
    two = [{**entry, "base": True} for entry in brand["builds-on"]]
    assert refused({**brand, "builds-on": two}, "library") != []
    unmarked = [{**entry, "base": False} for entry in brand["builds-on"]]
    assert refused({**brand, "builds-on": unmarked}, "library") != []
    components = reading.read_yaml(FOUNDATIONS / "library.yaml")
    marked = {**components, "builds-on": [{"name": "core", "major": 1, "base": True}]}
    assert refused(marked, "library") != []
    assert refused({**marked, "builds-on": [{"name": "core", "major": 1}]}, "library") == []


@pytest.mark.parametrize(
    "fields",
    [
        {"type": "object", "additionalProperties": True},
        {"type": "object", "properties": {"id": {"type": "string"}}},
        {"type": "object", "properties": {"pkit": {"type": "string"}}},
        {"type": "object", "required": ["use"]},
        {"type": "object", "properties": {"Label": {"type": "string"}}},
        {"type": "object", "patternProperties": {".*": {}}},
        {"type": "object", "properties": {"a": {"$ref": "https://example.org/x.json"}}},
    ],
)
def test_a_components_fields_take_the_format_1_subset_alone(fields: dict[str, Any]) -> None:
    assert refused({**instance("component"), "fields": fields}, "component") != []


def test_a_released_version_keeps_its_fingerprint_and_an_unreleased_one_none() -> None:
    listed = instance("libraries")
    entry = listed["libraries"]["brand"]["versions"]["1.0.0"]
    assert refused(_replaced(listed, {"released": True}), "libraries") != []
    assert refused(_replaced(listed, {**entry, "released": False}), "libraries") != []


def _replaced(listed: dict[str, Any], entry: dict[str, Any]) -> dict[str, Any]:
    copy = json.loads(json.dumps(listed))
    copy["libraries"]["brand"]["versions"]["1.0.0"] = entry
    return copy


@pytest.mark.parametrize("location", [".pkit/x", "", ".", "../out", "/abs", "a//b", "a/.git"])
def test_the_configuration_refuses_a_location_the_rules_refuse(location: str) -> None:
    assert refused({**instance("config"), "location": location}, "config") != []


@pytest.mark.parametrize(
    "value", ["no", "No", "YES", "y", "off", "true", "null", "Null", "NULL", "1a", "a.b", ""]
)
def test_an_id_is_never_a_yes_or_no_nor_nothing_nor_another_shape(value: str) -> None:
    defs = json.loads((SCHEMAS / "defs.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(defs["$defs"]["id"])
    assert not validator.is_valid(value)
    assert validator.is_valid("nope")


@pytest.mark.parametrize("value", ["y", "n", "yes", "no", "on", "off", "true", "false", "null"])
def test_a_name_is_never_a_yes_or_no_nor_nothing(value: str) -> None:
    defs = json.loads((SCHEMAS / "defs.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(defs["$defs"]["name"])
    assert not validator.is_valid(value)
    assert validator.is_valid(f"{value}-1")
