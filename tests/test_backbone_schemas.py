"""Tests for the backbone file schemas: the container schema, its discrimination
rule, the shared unknown-key renderer, and the load-check `pkit schemas validate`
runs over `.pkit/schemas/backbone/` (ADR-056, COR-053 point 10, COR-050).

Fixtures are built on `tmp_path` (the shared adopter-repo fixture of PR #1019 had
not landed on `main` when this was written). The shipped container schema is read
from the repository itself, so a change to the schema is exercised here directly.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from ruamel.yaml import YAML

from project_kit import backbone_schemas as bs
from project_kit import schemas_validate

REPO = Path(__file__).resolve().parents[1]

ACTIVE = ["pkit::documentation", "pkit::analysis"]

REVALIDATED_UNCHANGED = {
    "at": "2026-10-02T09:40:12Z",
    "outcome": "unchanged",
    "unchanged-because": "the CLI surface did not move",
}
DEFERRAL = {"anchor": {"kind": "path", "value": "src/cli/**"}, "reason": "waiting on #12"}


@pytest.fixture(scope="module")
def schema() -> dict:
    return bs.load_backbone_schema(REPO, "container")


def _carrier(container: dict[Any, Any]) -> dict[str, Any]:
    """A document's front matter: the artefact's own keys plus the container."""
    return {"title": "An artefact", "status": "active", bs.CONTAINER_KEY: container}


def _friction(**block: Any) -> dict[str, Any]:
    return {"friction": block}


def _validate(
    schema: dict, container: dict[Any, Any], active: list[str] = ACTIVE
) -> bs.ContainerReport:
    return bs.validate_container(_carrier(container), schema, active_roles=active)


def _messages(report: bs.ContainerReport) -> list[str]:
    return [f.message for f in report.findings]


# --- the shipped schema ---------------------------------------------------


def test_shipped_container_schema_is_draft_2020_12() -> None:
    path = bs.backbone_schema_path(REPO, "container")
    assert path.is_file()
    Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))


def test_readme_example_validates_clean(schema: dict) -> None:
    """The example in the schemas README's container section is a valid carrier."""
    text = """
pkit:
  friction:
    anchors: { path: [src/cli/**] }
    revalidated: { at: 2026-10-02T09:40:12Z, outcome: unchanged, unchanged-because: "…" }
  documentation:
    reading-evidence:
      schema_version: 1
      last-run: 2026-10-01
"""
    carrier = YAML(typ="safe").load(text)  # `at` parses to an aware datetime here
    report = bs.validate_container(carrier, schema, active_roles=ACTIVE)
    assert report.is_clean, _messages(report)
    assert report.functionality_blocks == ("friction",)
    assert report.role_blocks == ("documentation",)
    assert report.orphaned_roles == ()


def test_carrier_without_container_is_clean_and_recognises_nothing(schema: dict) -> None:
    report = bs.validate_container({"title": "plain"}, schema, active_roles=ACTIVE)
    assert report.is_clean
    assert report.findings == ()
    assert report.functionality_blocks == () and report.role_blocks == ()


# --- the friction block ---------------------------------------------------


@pytest.mark.parametrize(
    "revalidated",
    [
        {"at": "2026-10-02T09:40:12Z", "outcome": "updated"},
        REVALIDATED_UNCHANGED,
        {"deferred": [DEFERRAL]},  # never revalidated: `deferred` alone, no `at`
        {**REVALIDATED_UNCHANGED, "deferred": [DEFERRAL]},
    ],
    ids=["updated", "unchanged-with-because", "deferred-without-at", "unchanged-with-deferred"],
)
def test_friction_accepts_well_formed_revalidations(schema: dict, revalidated: dict) -> None:
    report = _validate(schema, _friction(anchors={"path": ["src/**"]}, revalidated=revalidated))
    assert report.is_clean, _messages(report)


def test_friction_accepts_all_three_anchor_kinds_and_last_check(schema: dict) -> None:
    block = _friction(
        anchors={"path": ["src/**"], "record": ["COR-050"], "artefact": ["other-artefact"]},
        **{"last-check": {"state": "stale", "as-of": "abc1234", "since": "def5678"}},
    )
    report = _validate(schema, block)
    assert report.is_clean, _messages(report)


def test_friction_refuses_unchanged_without_justification(schema: dict) -> None:
    report = _validate(
        schema, _friction(revalidated={"at": "2026-10-02T09:40:12Z", "outcome": "unchanged"})
    )
    assert not report.is_clean
    (finding,) = report.errors
    assert finding.kind is bs.FindingKind.SHAPE
    assert finding.location == "/pkit/friction/revalidated"
    assert "unchanged-because" in finding.message


def test_friction_refuses_empty_revalidation(schema: dict) -> None:
    report = _validate(schema, _friction(revalidated={}))
    assert not report.is_clean
    assert any("non-empty" in m or "too short" in m for m in _messages(report))


def test_friction_refuses_unknown_field_in_revalidated(schema: dict) -> None:
    report = _validate(
        schema,
        _friction(revalidated={"at": "2026-10-02T09:40:12Z", "outcome": "updated", "extra": 1}),
    )
    (finding,) = report.errors
    assert finding.location == "/pkit/friction/revalidated"
    assert "'extra' was unexpected" in finding.message


def test_friction_refuses_unknown_field_in_block(schema: dict) -> None:
    report = _validate(schema, _friction(anchor={"path": ["a"]}))  # `anchor`, not `anchors`
    (finding,) = report.errors
    assert finding.location == "/pkit/friction"
    assert "'anchor' was unexpected" in finding.message


def test_friction_refuses_non_utc_timestamp(schema: dict) -> None:
    report = _validate(
        schema, _friction(revalidated={"at": "2026-10-02T09:40:12+02:00", "outcome": "updated"})
    )
    (finding,) = report.errors
    assert finding.location == "/pkit/friction/revalidated/at"


def test_friction_refuses_fractional_seconds_as_written(schema: dict) -> None:
    """The parser keeps the fraction; the rendered text must too, so the pattern sees it."""
    text = "pkit:\n  friction:\n    revalidated: {at: 2026-10-02T09:40:12.5Z, outcome: updated}\n"
    carrier = YAML(typ="safe").load(text)
    assert carrier["pkit"]["friction"]["revalidated"]["at"].microsecond == 500_000
    report = bs.validate_container(carrier, schema, active_roles=ACTIVE)
    (finding,) = report.errors
    assert finding.location == "/pkit/friction/revalidated/at"
    assert "2026-10-02T09:40:12.5Z" in finding.message


def test_misspelt_functionality_key_is_unknown_key_with_suggestion(schema: dict) -> None:
    report = _validate(schema, {"frictoin": {"anchors": {"path": ["a"]}}})
    (finding,) = report.errors
    assert finding.kind is bs.FindingKind.UNKNOWN_KEY
    assert finding.location == "/pkit/frictoin"
    assert "unknown key 'frictoin'" in finding.message
    assert "did you mean 'friction'?" in finding.message
    assert bs.ROLE_BLOCK_REMINDER in finding.message
    # The shape errors the schema raised trying to read it as a role block are dropped.
    assert all(f.kind is bs.FindingKind.UNKNOWN_KEY for f in report.findings)


# --- role blocks ----------------------------------------------------------


def test_role_block_with_versioned_point_blocks_is_recognised(schema: dict) -> None:
    report = _validate(
        schema,
        {
            "documentation": {
                "reading-evidence": {"schema_version": 1, "last-run": "2026-10-01"},
                "coverage": {"schema_version": 3, "anything": {"the": "provider validates"}},
            }
        },
    )
    assert report.is_clean, _messages(report)
    assert report.role_blocks == ("documentation",)
    assert report.orphaned_roles == ()


def test_role_block_child_without_version_is_unknown_key(schema: dict) -> None:
    report = _validate(schema, {"documentaton": {"reading-evidence": {"last-run": "2026-10-01"}}})
    (finding,) = report.errors
    assert finding.kind is bs.FindingKind.UNKNOWN_KEY
    assert finding.location == "/pkit/documentaton"
    assert "did you mean 'documentation'?" in finding.message
    assert bs.ROLE_BLOCK_REMINDER in finding.message
    assert report.role_blocks == ()


def test_known_role_word_with_unversioned_children_is_known_but_malformed(schema: dict) -> None:
    report = _validate(schema, {"documentation": {"reading-evidence": {"last-run": "2026-10-01"}}})
    (finding,) = report.errors
    assert finding.kind is bs.FindingKind.UNKNOWN_KEY
    assert "is known, but its value is not the shape its kind expects" in finding.message
    assert "did you mean" not in finding.message
    assert bs.ROLE_BLOCK_REMINDER in finding.message


@pytest.mark.parametrize(
    "value",
    [{}, {"p": {"schema_version": "1"}}, {"p": {"schema_version": True}}, {"p": 1}, "text"],
    ids=["empty", "string-version", "bool-version", "child-not-mapping", "not-mapping"],
)
def test_values_that_are_not_role_blocks(schema: dict, value: Any) -> None:
    assert not bs.is_role_block(value)
    report = _validate(schema, {"documentation": value})
    assert not report.is_clean
    assert all(f.kind is bs.FindingKind.UNKNOWN_KEY for f in report.errors)


def test_orphaned_role_is_reported_not_errored(schema: dict) -> None:
    report = _validate(schema, {"documentation": {"p": {"schema_version": 1}}}, active=[])
    assert report.is_clean
    assert report.role_blocks == ("documentation",)
    assert report.orphaned_roles == ("documentation",)
    (finding,) = report.reports
    assert finding.kind is bs.FindingKind.ORPHANED_ROLE
    assert finding.severity is bs.Severity.REPORT
    assert finding.location == "/pkit/documentation"
    assert "no active provider" in finding.message


def test_qualified_role_key_is_active(schema: dict) -> None:
    report = _validate(schema, {"pkit::documentation": {"p": {"schema_version": 1}}})
    assert report.is_clean and report.orphaned_roles == ()
    assert report.role_blocks == ("pkit::documentation",)


def test_bare_friction_is_always_the_functionality_block(schema: dict) -> None:
    """A role word equal to a functionality name must be written qualified."""
    active = ["other::friction"]
    roles = bs.KnownRoles.from_active(active)
    assert "friction" not in roles.words
    assert roles.known_keys() == {"friction", "other::friction"}

    # Looks like a role block, but the bare key is the functionality block — and fails its shape.
    report = _validate(schema, {"friction": {"p": {"schema_version": 1}}}, active=active)
    assert report.functionality_blocks == ("friction",)
    assert report.role_blocks == ()
    assert not report.is_clean
    assert all(f.kind is bs.FindingKind.SHAPE for f in report.errors)

    # The qualified form is the role block.
    report = _validate(schema, {"other::friction": {"p": {"schema_version": 1}}}, active=active)
    assert report.is_clean and report.role_blocks == ("other::friction",)


def test_container_not_a_mapping_is_a_shape_error(schema: dict) -> None:
    report = bs.validate_container({bs.CONTAINER_KEY: 3}, schema, active_roles=ACTIVE)
    (finding,) = report.errors
    assert finding.kind is bs.FindingKind.SHAPE
    assert finding.location == "/pkit"


def test_container_key_with_no_value_is_present_and_a_shape_error(schema: dict) -> None:
    """`pkit:` written with nothing under it parses to null — present, not absent."""
    carrier = YAML(typ="safe").load("title: plain\npkit:\n")
    assert bs.CONTAINER_KEY in carrier and carrier[bs.CONTAINER_KEY] is None
    report = bs.validate_container(carrier, schema, active_roles=ACTIVE)
    (finding,) = report.errors
    assert finding.kind is bs.FindingKind.SHAPE
    assert finding.location == "/pkit"
    assert "None is not of type 'object'" in finding.message


def test_point_compatibility_hook_is_unanswered_until_the_resolver_exists() -> None:
    assert bs.resolve_point_compatibility("documentation", "p", 1) is None


# --- keys the parser did not read as text -----------------------------------


def test_non_text_key_that_is_not_a_role_block_is_an_unknown_key(schema: dict) -> None:
    """Regression: an int key reached the edit-distance suggestion and raised TypeError."""
    report = _validate(schema, {1: "x"})
    (finding,) = report.findings
    assert finding.kind is bs.FindingKind.UNKNOWN_KEY
    assert finding.location == "/pkit/1"
    assert "unknown key '1'" in finding.message
    assert "did you mean" in finding.message


def test_mixed_key_types_do_not_break_the_shape_pass(schema: dict) -> None:
    """Regression: sorting shape errors compared an int path segment with a str one."""
    report = _validate(schema, {"friction": {"bogus": 1}, 5: {"x": 1}})
    assert report.functionality_blocks == ("friction",)
    assert [(f.location, f.kind) for f in report.errors] == [
        ("/pkit/friction", bs.FindingKind.SHAPE),
        ("/pkit/5", bs.FindingKind.UNKNOWN_KEY),
    ]


def test_non_text_role_block_key_keeps_its_shape_findings(schema: dict) -> None:
    """Regression: shape findings were grouped under the text key but looked up by the raw one."""
    report = _validate(schema, {2026: {"p": {"schema_version": 0}}}, active=[])
    assert report.role_blocks == ("2026",) and report.orphaned_roles == ("2026",)
    (finding,) = report.errors
    assert finding.kind is bs.FindingKind.SHAPE
    assert finding.location == "/pkit/2026/p/schema_version"


def test_yaml_keys_are_judged_as_written(schema: dict) -> None:
    """YAML reads `2026:` as an int and `2026-10-02:` as a date; the rule sees the text."""
    text = """
pkit:
  2026:
    p: {schema_version: 1}
  2026-10-02:
    q: {schema_version: 1}
"""
    carrier = YAML(typ="safe").load(text)
    assert {type(k) for k in carrier["pkit"]} == {int, date}
    report = bs.validate_container(carrier, schema, active_roles=[])
    assert report.is_clean, _messages(report)
    assert report.role_blocks == ("2026", "2026-10-02")
    assert [f.location for f in report.reports] == ["/pkit/2026", "/pkit/2026-10-02"]


# --- the collection-entry form --------------------------------------------


def test_collection_entry_carries_the_same_container(schema: dict) -> None:
    """One entry of a collection file: its id is the key it sits under; the entry is the carrier."""
    collection = {
        "rules": {
            "no-shared-files": {
                "status": "active",
                bs.CONTAINER_KEY: {
                    "friction": {
                        "anchors": {"record": ["COR-001"]},
                        "revalidated": REVALIDATED_UNCHANGED,
                    },
                    "documentation": {"p": {"schema_version": 2}},
                },
            },
            "typo": {bs.CONTAINER_KEY: {"frictoin": {}}},
        }
    }
    entry = collection["rules"]["no-shared-files"]
    good = bs.validate_container(entry, schema, active_roles=ACTIVE)
    assert good.is_clean, _messages(good)
    assert good.functionality_blocks == ("friction",) and good.role_blocks == ("documentation",)
    bad = bs.validate_container(collection["rules"]["typo"], schema, active_roles=ACTIVE)
    assert [f.kind for f in bad.errors] == [bs.FindingKind.UNKNOWN_KEY]


def test_schema_names_both_forms_over_one_carrier_definition(schema: dict) -> None:
    defs = schema["$defs"]
    assert defs["document-front-matter"]["$ref"] == "#/$defs/carrier"
    assert defs["collection-entry"]["$ref"] == "#/$defs/carrier"
    assert schema["$ref"] == "#/$defs/carrier"
    entry_validator = Draft202012Validator(
        {"$ref": "#/$defs/collection-entry", "$defs": defs}
    )
    assert entry_validator.is_valid({"id": "x", bs.CONTAINER_KEY: {"friction": {}}})
    assert not entry_validator.is_valid({bs.CONTAINER_KEY: {"friction": {"bogus": 1}}})


# --- the shared renderer ----------------------------------------------------


def test_edit_distance() -> None:
    assert bs.edit_distance("", "") == 0
    assert bs.edit_distance("friction", "friction") == 0
    assert bs.edit_distance("frictoin", "friction") == 2
    assert bs.edit_distance("abc", "") == 3


def test_nearest_known_key_breaks_ties_alphabetically_and_handles_empty() -> None:
    assert bs.nearest_known_key("ab", ["ac", "aa"]) == "aa"
    assert bs.nearest_known_key("x", []) is None


def test_render_unknown_key_without_reminder_reads_as_a_config_file_would() -> None:
    message = bs.render_unknown_key("documentaion-roots", ["documentation-roots", "friction"])
    assert message == "unknown key 'documentaion-roots'; did you mean 'documentation-roots'?"
    assert bs.render_unknown_key("x", []) == "unknown key 'x'."


# --- loading and the load-check ---------------------------------------------


def test_load_backbone_schema_missing_kind_raises(tmp_path: Path) -> None:
    with pytest.raises(bs.BackboneSchemaMissing):
        bs.load_backbone_schema(tmp_path, "container")


def test_load_backbone_schema_invalid_raises(tmp_path: Path) -> None:
    schemas_dir = bs.backbone_schemas_dir(tmp_path)
    schemas_dir.mkdir(parents=True)
    (schemas_dir / "config.schema.json").write_text('{"type": "nonsense"}', encoding="utf-8")
    with pytest.raises(bs.BackboneSchemaInvalid, match="Draft 2020-12"):
        bs.load_backbone_schema(tmp_path, "config")


def test_load_check_reports_each_malformed_schema(tmp_path: Path) -> None:
    schemas_dir = bs.backbone_schemas_dir(tmp_path)
    schemas_dir.mkdir(parents=True)
    (schemas_dir / "container.schema.json").write_text(
        json.dumps({"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object"}),
        encoding="utf-8",
    )
    (schemas_dir / "config.schema.json").write_text("{not json", encoding="utf-8")
    (schemas_dir / "rule-set.schema.json").write_text('{"type": "nonsense"}', encoding="utf-8")
    (schemas_dir / "notes.json").write_text("{}", encoding="utf-8")  # not a schema file; ignored

    result = bs.load_check(tmp_path)
    assert [p.name for p in result.checked] == [
        "config.schema.json",
        "container.schema.json",
        "rule-set.schema.json",
    ]
    assert [(p.name, reason.split(":")[0]) for p, reason in result.failures] == [
        ("config.schema.json", "not valid JSON"),
        ("rule-set.schema.json", "not a valid Draft 2020-12 JSON Schema"),
    ]


def test_load_check_absent_directory_checks_nothing(tmp_path: Path) -> None:
    result = bs.load_check(tmp_path)
    assert result.checked == () and result.failures == ()


def test_schemas_validate_all_runs_the_backbone_load_check(tmp_path: Path) -> None:
    """`pkit schemas validate` catches a malformed backbone schema (ADR-056 Implications)."""
    schemas_dir = bs.backbone_schemas_dir(tmp_path)
    schemas_dir.mkdir(parents=True)
    (schemas_dir / "container.schema.json").write_text('{"type": "object"}', encoding="utf-8")
    (schemas_dir / "config.schema.json").write_text('{"type": 12}', encoding="utf-8")

    report = schemas_validate.validate_all(tmp_path)
    assert report.backbone_schemas_checked == 2
    assert report.pairs_checked == 0
    (issue,) = report.issues
    assert issue.location == str(Path(".pkit/schemas/backbone/config.schema.json"))
    assert issue.message.startswith("backbone file schema is not a valid Draft 2020-12 JSON Schema")


def test_schemas_validate_all_is_clean_without_backbone_directory(tmp_path: Path) -> None:
    report = schemas_validate.validate_all(tmp_path)
    assert report.is_clean and report.backbone_schemas_checked == 0


def test_shipped_backbone_schemas_pass_the_load_check() -> None:
    result = bs.load_check(REPO)
    assert result.failures == ()
    assert "container.schema.json" in {p.name for p in result.checked}
