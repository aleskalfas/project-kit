"""The living-docs project configuration: its schema and its COR-023 binding.

What the capability needs that the backbone does not (living-docs DEC-001
point 1): each space's entry point, and the space each place belongs to. The
places themselves are the backbone configuration's `friction.places`; this
file assigns them, joined by path, and `places` is a mapping so each place
names exactly one space.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from ruamel.yaml import YAML

from project_kit import data_validate as dv
from tests.adopter_repo import MakeAdopterRepo

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS = REPO_ROOT / ".pkit" / "capabilities" / "living-docs" / "schemas"
COMPANION = SCHEMAS / "config.schema.json"
CARRIER = SCHEMAS / "config.yaml"
PROJECT_CONFIG = Path(".pkit") / "capabilities" / "living-docs" / "project" / "config.yaml"


@pytest.fixture(scope="module")
def validator() -> Draft202012Validator:
    schema = json.loads(COMPANION.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _errors(validator: Draft202012Validator, doc: Any) -> list[str]:
    return [e.message for e in validator.iter_errors(doc)]


def _config(**fields: Any) -> dict[str, Any]:
    return {"schema_version": 1, **fields}


# --- shape ------------------------------------------------------------------


def test_reference_instance_validates(validator: Draft202012Validator) -> None:
    data = YAML(typ="safe").load(CARRIER.read_text(encoding="utf-8"))
    assert _errors(validator, data) == []


def test_a_project_adds_a_space_and_assigns_places_to_it(
    validator: Draft202012Validator,
) -> None:
    doc = _config(
        spaces={
            "user": {"entry-point": "README.md"},
            "technical": {"entry-point": "CONTRIBUTING.md"},
            "interface-reference": {"entry-point": "api/index.md"},
        },
        places={"README.md": "user", "api/": "interface-reference"},
    )
    assert _errors(validator, doc) == []


def test_only_the_version_is_required(validator: Draft202012Validator) -> None:
    assert _errors(validator, _config()) == []


@pytest.mark.parametrize(
    "doc",
    [
        _config(places={"README.md": ["user", "technical"]}),  # one place, one space
        _config(places={"README.md": "User Space"}),  # not a space id
        _config(places={"/abs/README.md": "user"}),  # a place is repository-relative
        _config(spaces={"user": {"entry-point": "/README.md"}}),
        _config(spaces={"user": {"entry": "README.md"}}),  # unknown key in a space
        _config(spaces={"User": {}}),  # not a space id
        _config(assignments={"README.md": "user"}),  # unknown top-level key
    ],
)
def test_malformed_shapes_are_refused(validator: Draft202012Validator, doc: Any) -> None:
    assert _errors(validator, doc)


# --- the COR-023 binding ----------------------------------------------------


def test_the_project_file_binds_to_the_schema(make_adopter_repo: MakeAdopterRepo) -> None:
    repo = make_adopter_repo(capabilities=("living-docs",))
    path = repo.root / PROJECT_CONFIG
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "schema_version: 1\nplaces:\n  README.md: user\n", encoding="utf-8"
    )
    result = dv.resolve_binding(path, repo.root)
    assert isinstance(result, dv.ResolvedBinding), getattr(result, "message", "")
    assert (result.capability, result.schema_name) == ("living-docs", "config")
    assert dv.validate_data_file(path, repo.root) == []

    path.write_text("schema_version: 1\nplaces:\n  README.md: [user]\n", encoding="utf-8")
    assert dv.validate_data_file(path, repo.root)


def test_the_glob_does_not_claim_the_backbone_configuration(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo(capabilities=("living-docs",))
    path = repo.root / ".pkit" / "project" / "config.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("name: x\n", encoding="utf-8")
    assert isinstance(dv.resolve_binding(path, repo.root), dv.BindingError)
