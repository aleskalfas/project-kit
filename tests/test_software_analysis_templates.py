"""software-analysis: a companion schema and a template per artefact kind (#887).

Held to software-analysis DEC-001 points 1 to 6:

- one **companion schema** per kind — actor, term, use case, journey,
  revalidation record — each valid Draft 2020-12, sharing one home for the id
  shapes (`analysis.schema.json`);
- each anchored kind's **template** carrying the friction block inside the
  methodology's container — in the front matter of a document, in each entry
  of a collection — valid against the core's container schema and against the
  kind's own; the journey's anchors written from its steps; the revalidation
  record's no anchored artefact.
"""

from __future__ import annotations

import json
import re
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from project_kit import backbone_schemas as bs
from project_kit import friction_discovery as fd
from tests.analysis_repo import CAPABILITY, REPO, load

SCHEMAS = CAPABILITY / "schemas"


def _stems() -> list[str]:
    return sorted(
        p.name.removesuffix(".schema.json")
        for p in SCHEMAS.iterdir()
        if p.name.endswith(".schema.json")
    )


def _schema(stem: str) -> dict[str, Any]:
    return json.loads((SCHEMAS / f"{stem}.schema.json").read_text(encoding="utf-8"))


def _schema_errors(stem: str, instance: Any) -> list[str]:
    """The companion schema's messages for `instance`, its cross-file `$ref`s
    resolved over the capability's schemas, as the check resolves them."""
    resources: list[tuple[str, Resource[Any]]] = [
        (_schema(s)["$id"], Resource[Any].from_contents(_schema(s))) for s in _stems()
    ]
    registry = Registry[Any]().with_resources(resources)
    validator: Any = Draft202012Validator(_schema(stem), registry=registry)
    return [error.message for error in validator.iter_errors(instance)]


def _container_findings(carrier: Any) -> tuple[Any, ...]:
    """The core container schema's findings on a front matter or an entry."""
    backbone: Any = bs  # its schema loader returns an untyped mapping
    schema = backbone.load_backbone_schema(REPO, "container")
    return backbone.validate_container(carrier, schema, wiring=bs.ContainerWiring()).findings


def _template(name: str) -> dict[str, Any]:
    text = (CAPABILITY / "templates" / f"{name}.md").read_text(encoding="utf-8")
    front_matter, _body = fd.split_front_matter(text)
    assert front_matter is not None
    return load(front_matter)


def test_the_schemas_are_one_per_kind_and_valid() -> None:
    stems = _stems()
    assert stems == ["actor", "analysis", "journey", "revalidation-record", "term", "use-case"]
    for stem in stems:
        Draft202012Validator.check_schema(_schema(stem))


def test_every_id_shape_has_one_home() -> None:
    """The kinds' schemas refer to the shared id shapes; none writes its own."""
    for prefix in ("ACT", "TERM", "UC", "JRN"):
        holders = [s for s in _stems() if f'"^{prefix}-' in json.dumps(_schema(s))]
        assert holders == ["analysis"], prefix


@pytest.mark.parametrize(("template", "schema"), [("use-case", "use-case"), ("journey", "journey")])
def test_a_document_template_carries_the_friction_block_in_the_container(
    template: str, schema: str
) -> None:
    data = _template(template)
    assert _container_findings(data) == ()
    assert set(data["pkit"]) == {"friction"}
    assert _schema_errors(schema, {k: v for k, v in data.items() if k != "pkit"}) == []


@pytest.mark.parametrize(("template", "schema"), [("actors", "actor"), ("glossary", "term")])
def test_a_collection_template_carries_the_friction_block_in_each_entry(
    template: str, schema: str
) -> None:
    data = _template(template)
    assert "pkit" not in data  # a collection: the container is in each entry
    id_pattern = _schema("analysis")["$defs"][f"{schema}-id"]["pattern"]
    for entry_id, entry in data.items():
        assert re.match(id_pattern, entry_id)
        assert _container_findings(entry) == ()
        assert set(entry["pkit"]) == {"friction"}
        assert _schema_errors(schema, {k: v for k, v in entry.items() if k != "pkit"}) == []


def test_the_journey_template_anchors_its_steps() -> None:
    data = _template("journey")
    assert data["pkit"]["friction"]["anchors"]["artefact"] == data["steps"]


def test_the_revalidation_record_template_is_no_anchored_artefact() -> None:
    data = _template("revalidation-record")
    assert "pkit" not in data
    assert _schema_errors("revalidation-record", data) == []


@pytest.mark.parametrize(
    ("stem", "instance", "message"),
    [
        ("use-case", {"id": "UC-7", "status": "active", "actor": "ACT-a"}, "does not match"),
        (
            "journey",
            {"id": "JRN-001", "status": "active", "actor": "ACT-a", "steps": ["UC-001"]},
            "is too short",
        ),
        ("actor", {"name": "A", "status": "active", "needs": []}, "should be non-empty"),
        (
            "term",
            {"name": "T", "status": "active", "definition": "d", "replaces": ["x", "x"]},
            "non-unique",
        ),
    ],
)
def test_the_schemas_refuse_what_the_decision_rules_out(
    stem: str, instance: dict[str, Any], message: str
) -> None:
    (found,) = _schema_errors(stem, instance)
    assert message in found
