"""Tests for `pkit schemas validate` and the underlying schemas_validate module."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from project_kit.cli import main
from project_kit.schemas_validate import (
    NamespaceDetail,
    SchemaPair,
    SchemaSummary,
    TokenResolution,
    detail_namespace,
    discover_schema_pairs,
    discover_schema_pairs_at,
    resolve_token_to_target,
    summarize_schemas,
    validate_all,
    validate_pair,
    validate_path,
)


# --- discovery ------------------------------------------------------


def _make_capability(target_root: Path, name: str) -> Path:
    """Set up a minimal capability subtree at `<target_root>/.pkit/capabilities/<name>/schemas/`."""
    schemas = target_root / ".pkit" / "capabilities" / name / "schemas"
    schemas.mkdir(parents=True)
    return schemas


def _write_schema_pair(
    schemas_dir: Path,
    name: str,
    *,
    yaml_body: str,
    json_schema: dict | None = None,
) -> tuple[Path, Path]:
    """Write a YAML + (optional) JSON Schema companion. Returns (yaml_path, companion_path)."""
    yaml_path = schemas_dir / f"{name}.yaml"
    yaml_path.write_text(yaml_body, encoding="utf-8")
    companion = schemas_dir / f"{name}.schema.json"
    if json_schema is not None:
        companion.write_text(json.dumps(json_schema, indent=2), encoding="utf-8")
    return yaml_path, companion


# Minimal JSON Schema that accepts the minimal YAML below.
_MINIMAL_JSON_SCHEMA: dict = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["schema_version", "name"],
    "additionalProperties": False,
    "properties": {
        "schema_version": {"type": "integer", "const": 1},
        "name": {"type": "string"},
    },
}

_MINIMAL_YAML = "schema_version: 1\nname: example\n"


def test_discover_returns_empty_when_no_capabilities(tmp_path: Path) -> None:
    assert discover_schema_pairs(tmp_path) == []


def test_discover_finds_yaml_schemas_under_capabilities(tmp_path: Path) -> None:
    """Walks `.pkit/capabilities/*/schemas/*.yaml`; companion path derived."""
    schemas = _make_capability(tmp_path, "demo")
    _write_schema_pair(schemas, "alpha", yaml_body=_MINIMAL_YAML, json_schema=_MINIMAL_JSON_SCHEMA)
    _write_schema_pair(schemas, "beta", yaml_body=_MINIMAL_YAML)  # no companion

    pairs = discover_schema_pairs(tmp_path)
    assert len(pairs) == 2
    names = sorted(p.yaml_path.stem for p in pairs)
    assert names == ["alpha", "beta"]
    # Every pair derives the companion path even when the file doesn't exist.
    for pair in pairs:
        assert pair.companion_path.name == f"{pair.yaml_path.stem}.schema.json"


def test_discover_walks_multiple_capabilities(tmp_path: Path) -> None:
    s1 = _make_capability(tmp_path, "cap-one")
    s2 = _make_capability(tmp_path, "cap-two")
    _write_schema_pair(s1, "a", yaml_body=_MINIMAL_YAML)
    _write_schema_pair(s2, "b", yaml_body=_MINIMAL_YAML)
    pairs = discover_schema_pairs(tmp_path)
    assert {p.yaml_path.stem for p in pairs} == {"a", "b"}


def test_discover_at_path_single_file(tmp_path: Path) -> None:
    schemas = _make_capability(tmp_path, "demo")
    yaml_path, _ = _write_schema_pair(schemas, "alpha", yaml_body=_MINIMAL_YAML)
    pairs = discover_schema_pairs_at(yaml_path)
    assert len(pairs) == 1
    assert pairs[0].yaml_path == yaml_path


def test_discover_at_path_directory(tmp_path: Path) -> None:
    schemas = _make_capability(tmp_path, "demo")
    _write_schema_pair(schemas, "alpha", yaml_body=_MINIMAL_YAML)
    _write_schema_pair(schemas, "beta", yaml_body=_MINIMAL_YAML)
    pairs = discover_schema_pairs_at(schemas)
    assert len(pairs) == 2


# --- validation: shape pass cases -----------------------------------


def test_validate_pair_passes_on_satisfying_yaml(tmp_path: Path) -> None:
    schemas = _make_capability(tmp_path, "demo")
    yaml_path, companion = _write_schema_pair(
        schemas, "alpha", yaml_body=_MINIMAL_YAML, json_schema=_MINIMAL_JSON_SCHEMA
    )
    issues = validate_pair(SchemaPair(yaml_path=yaml_path, companion_path=companion))
    assert issues == []


def test_validate_all_clean_report(tmp_path: Path) -> None:
    schemas = _make_capability(tmp_path, "demo")
    _write_schema_pair(schemas, "alpha", yaml_body=_MINIMAL_YAML, json_schema=_MINIMAL_JSON_SCHEMA)
    report = validate_all(tmp_path)
    assert report.is_clean
    assert report.pairs_checked == 1


# --- validation: shape fail cases -----------------------------------


def test_validate_flags_missing_companion(tmp_path: Path) -> None:
    schemas = _make_capability(tmp_path, "demo")
    _write_schema_pair(schemas, "alpha", yaml_body=_MINIMAL_YAML)  # no companion
    report = validate_all(tmp_path)
    assert not report.is_clean
    assert len(report.issues) == 1
    assert "missing companion" in report.issues[0].message.lower()


def test_validate_flags_required_property_missing(tmp_path: Path) -> None:
    schemas = _make_capability(tmp_path, "demo")
    _write_schema_pair(
        schemas,
        "alpha",
        yaml_body="schema_version: 1\n",  # missing required `name`
        json_schema=_MINIMAL_JSON_SCHEMA,
    )
    report = validate_all(tmp_path)
    assert not report.is_clean
    assert any("'name'" in i.message and "required" in i.message for i in report.issues)


def test_validate_flags_wrong_schema_version(tmp_path: Path) -> None:
    schemas = _make_capability(tmp_path, "demo")
    _write_schema_pair(
        schemas,
        "alpha",
        yaml_body="schema_version: 2\nname: example\n",
        json_schema=_MINIMAL_JSON_SCHEMA,
    )
    report = validate_all(tmp_path)
    assert not report.is_clean
    # jsonschema reports `const` violation; either '2' or 'const' is in the message.
    assert any("const" in i.message.lower() or "expected" in i.message.lower() for i in report.issues)


def test_validate_flags_unknown_property(tmp_path: Path) -> None:
    schemas = _make_capability(tmp_path, "demo")
    _write_schema_pair(
        schemas,
        "alpha",
        yaml_body="schema_version: 1\nname: example\nstray: 42\n",
        json_schema=_MINIMAL_JSON_SCHEMA,
    )
    report = validate_all(tmp_path)
    assert not report.is_clean
    # additionalProperties: false → unknown property is rejected
    assert any("stray" in i.message for i in report.issues)


def test_validate_flags_malformed_yaml(tmp_path: Path) -> None:
    schemas = _make_capability(tmp_path, "demo")
    _write_schema_pair(
        schemas,
        "alpha",
        yaml_body="schema_version: 1\n  name: bad-indent\n",  # malformed
        json_schema=_MINIMAL_JSON_SCHEMA,
    )
    report = validate_all(tmp_path)
    assert not report.is_clean
    assert any("yaml parse error" in i.message.lower() for i in report.issues)


def test_validate_flags_malformed_companion_json(tmp_path: Path) -> None:
    schemas = _make_capability(tmp_path, "demo")
    yaml_path, companion = _write_schema_pair(schemas, "alpha", yaml_body=_MINIMAL_YAML)
    companion.write_text("{ this is not valid json", encoding="utf-8")
    report = validate_all(tmp_path)
    assert not report.is_clean
    assert any("not valid json" in i.message.lower() for i in report.issues)


def test_validate_flags_invalid_meta_schema(tmp_path: Path) -> None:
    """A companion that's valid JSON but not a valid JSON Schema gets flagged."""
    schemas = _make_capability(tmp_path, "demo")
    yaml_path, companion = _write_schema_pair(schemas, "alpha", yaml_body=_MINIMAL_YAML)
    # `type: "fake-type"` is not a valid JSON Schema type keyword
    companion.write_text(
        json.dumps({"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "fake-type"}),
        encoding="utf-8",
    )
    report = validate_all(tmp_path)
    assert not report.is_clean
    assert any("draft 2020-12" in i.message.lower() or "not a valid" in i.message.lower() for i in report.issues)


# --- validate_path -------------------------------------------------


def test_validate_path_single_file(tmp_path: Path) -> None:
    schemas = _make_capability(tmp_path, "demo")
    yaml_path, _ = _write_schema_pair(
        schemas, "alpha", yaml_body=_MINIMAL_YAML, json_schema=_MINIMAL_JSON_SCHEMA
    )
    report = validate_path(yaml_path)
    assert report.is_clean
    assert report.pairs_checked == 1


def test_validate_path_directory_scans_recursively(tmp_path: Path) -> None:
    """Useful for adopters running the validator on non-capability data trees."""
    nested = tmp_path / "data" / "sub"
    nested.mkdir(parents=True)
    (nested / "foo.yaml").write_text(_MINIMAL_YAML, encoding="utf-8")
    (nested / "foo.schema.json").write_text(json.dumps(_MINIMAL_JSON_SCHEMA), encoding="utf-8")

    report = validate_path(tmp_path / "data")
    assert report.is_clean
    assert report.pairs_checked == 1


# --- CLI -----------------------------------------------------------


@pytest.fixture
def cli_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Project tree with `.pkit/` initialised (no full kit install — just enough for find_target_root)."""
    import subprocess

    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / ".pkit").mkdir()
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_cli_validate_clean(cli_target: Path) -> None:
    schemas = _make_capability(cli_target, "demo")
    _write_schema_pair(schemas, "alpha", yaml_body=_MINIMAL_YAML, json_schema=_MINIMAL_JSON_SCHEMA)
    runner = CliRunner()
    result = runner.invoke(main, ["schemas", "validate"])
    assert result.exit_code == 0
    assert "All checks passed" in result.output


def test_cli_validate_reports_issues_and_exits_nonzero(cli_target: Path) -> None:
    schemas = _make_capability(cli_target, "demo")
    _write_schema_pair(schemas, "alpha", yaml_body=_MINIMAL_YAML)  # no companion
    runner = CliRunner()
    result = runner.invoke(main, ["schemas", "validate"])
    assert result.exit_code != 0
    assert "missing companion" in result.output.lower()


def test_cli_validate_no_schemas_is_clean(cli_target: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["schemas", "validate"])
    assert result.exit_code == 0
    assert "No schemas found" in result.output


def test_cli_validate_at_explicit_path(cli_target: Path) -> None:
    """`pkit schemas validate <path>` — works on a single YAML outside the standard layout."""
    nested = cli_target / "data"
    nested.mkdir()
    yaml_path = nested / "thing.yaml"
    yaml_path.write_text(_MINIMAL_YAML, encoding="utf-8")
    (nested / "thing.schema.json").write_text(json.dumps(_MINIMAL_JSON_SCHEMA), encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(main, ["schemas", "validate", str(yaml_path)])
    assert result.exit_code == 0
    assert "Validated 1 schema(s)" in result.output


# --- Date coercion -------------------------------------------------


def test_validate_handles_yaml_date_against_format_date(tmp_path: Path) -> None:
    """YAML's native date parse round-trips into ISO string for jsonschema's `format: date`."""
    schemas = _make_capability(tmp_path, "demo")
    _write_schema_pair(
        schemas,
        "alpha",
        yaml_body="schema_version: 1\ncaptured_at: 2026-05-21\n",
        json_schema={
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "required": ["schema_version", "captured_at"],
            "additionalProperties": False,
            "properties": {
                "schema_version": {"type": "integer", "const": 1},
                "captured_at": {"type": "string", "format": "date"},
            },
        },
    )
    report = validate_all(tmp_path)
    assert report.is_clean


# --- reference resolution (COR-019) ---------------------------------


# A target namespace schema: declares "types" as the id collection at /types.
# Its data has two ids: "task" and "feature".
_TARGET_JSON_SCHEMA: dict = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "x-pkit-id-collection": "/types",
    "required": ["schema_version", "types"],
    "additionalProperties": False,
    "properties": {
        "schema_version": {"type": "integer", "const": 1},
        "types": {
            "type": "object",
            "patternProperties": {
                "^[a-z][a-z0-9-]*$": {"type": "object"},
            },
            "additionalProperties": False,
        },
    },
}

_TARGET_YAML = "schema_version: 1\ntypes:\n  task: {}\n  feature: {}\n"

# A consumer schema: references the target via a value-position token.
_CONSUMER_JSON_SCHEMA: dict = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["schema_version", "applies_to"],
    "additionalProperties": False,
    "properties": {
        "schema_version": {"type": "integer", "const": 1},
        "applies_to": {
            "type": "array",
            "items": {
                "type": "string",
                "pattern": r"^\[target:[a-z][a-z0-9-]*\]$",
            },
        },
    },
}


def test_resolver_passes_when_token_resolves(tmp_path: Path) -> None:
    schemas = _make_capability(tmp_path, "demo")
    _write_schema_pair(schemas, "target", yaml_body=_TARGET_YAML, json_schema=_TARGET_JSON_SCHEMA)
    _write_schema_pair(
        schemas,
        "consumer",
        yaml_body='schema_version: 1\napplies_to: ["[target:task]"]\n',
        json_schema=_CONSUMER_JSON_SCHEMA,
    )
    report = validate_all(tmp_path)
    assert report.is_clean, report.issues


def test_resolver_flags_unknown_id_in_known_namespace(tmp_path: Path) -> None:
    schemas = _make_capability(tmp_path, "demo")
    _write_schema_pair(schemas, "target", yaml_body=_TARGET_YAML, json_schema=_TARGET_JSON_SCHEMA)
    _write_schema_pair(
        schemas,
        "consumer",
        yaml_body='schema_version: 1\napplies_to: ["[target:bogus]"]\n',
        json_schema=_CONSUMER_JSON_SCHEMA,
    )
    report = validate_all(tmp_path)
    assert not report.is_clean
    msgs = [i.message for i in report.issues]
    assert any("'bogus'" in m and "not found" in m for m in msgs), msgs


def test_resolver_flags_missing_namespace(tmp_path: Path) -> None:
    schemas = _make_capability(tmp_path, "demo")
    # No target schema in sight.
    _write_schema_pair(
        schemas,
        "consumer",
        yaml_body='schema_version: 1\napplies_to: ["[target:task]"]\n',
        json_schema=_CONSUMER_JSON_SCHEMA,
    )
    report = validate_all(tmp_path)
    assert not report.is_clean
    msgs = [i.message for i in report.issues]
    assert any("sibling companion" in m and "not found" in m for m in msgs), msgs


def test_resolver_flags_missing_annotation(tmp_path: Path) -> None:
    """Target schema exists but its companion lacks x-pkit-id-collection."""
    schemas = _make_capability(tmp_path, "demo")
    target_schema = dict(_TARGET_JSON_SCHEMA)
    del target_schema["x-pkit-id-collection"]
    _write_schema_pair(schemas, "target", yaml_body=_TARGET_YAML, json_schema=target_schema)
    _write_schema_pair(
        schemas,
        "consumer",
        yaml_body='schema_version: 1\napplies_to: ["[target:task]"]\n',
        json_schema=_CONSUMER_JSON_SCHEMA,
    )
    report = validate_all(tmp_path)
    assert not report.is_clean
    msgs = [i.message for i in report.issues]
    assert any("x-pkit-id-collection" in m and "missing" in m for m in msgs), msgs


def test_resolver_flags_broken_pointer(tmp_path: Path) -> None:
    """Target companion's pointer doesn't resolve in the data YAML."""
    schemas = _make_capability(tmp_path, "demo")
    target_schema = dict(_TARGET_JSON_SCHEMA)
    target_schema["x-pkit-id-collection"] = "/nonexistent"
    _write_schema_pair(schemas, "target", yaml_body=_TARGET_YAML, json_schema=target_schema)
    _write_schema_pair(
        schemas,
        "consumer",
        yaml_body='schema_version: 1\napplies_to: ["[target:task]"]\n',
        json_schema=_CONSUMER_JSON_SCHEMA,
    )
    report = validate_all(tmp_path)
    assert not report.is_clean
    msgs = [i.message for i in report.issues]
    assert any("did not resolve" in m for m in msgs), msgs


def test_resolver_handles_key_position_tokens(tmp_path: Path) -> None:
    """Tokens appearing as mapping keys (the reference-keys case from COR-019)."""
    schemas = _make_capability(tmp_path, "demo")
    _write_schema_pair(schemas, "target", yaml_body=_TARGET_YAML, json_schema=_TARGET_JSON_SCHEMA)
    # Consumer keyed by target ids — like body-format.yaml's issues block.
    consumer_schema: dict = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["schema_version", "by_type"],
        "additionalProperties": False,
        "properties": {
            "schema_version": {"type": "integer", "const": 1},
            "by_type": {
                "type": "object",
                "patternProperties": {
                    r"^\[target:[a-z][a-z0-9-]*\]$": {"type": "object"},
                },
                "additionalProperties": False,
            },
        },
    }
    _write_schema_pair(
        schemas,
        "consumer",
        yaml_body=(
            "schema_version: 1\n"
            "by_type:\n"
            '  "[target:task]": {}\n'  # resolves
            '  "[target:bogus]": {}\n'  # fails
        ),
        json_schema=consumer_schema,
    )
    report = validate_all(tmp_path)
    assert not report.is_clean
    msgs = [i.message for i in report.issues]
    assert any("'bogus'" in m and "not found" in m for m in msgs), msgs
    # The resolved key shouldn't fire an issue.
    assert not any("'task'" in m and "not found" in m for m in msgs), msgs


def test_resolver_flags_self_namespace_reference(tmp_path: Path) -> None:
    """A token whose namespace matches the schema's own stem is wrong per COR-019."""
    schemas = _make_capability(tmp_path, "demo")
    target_schema = dict(_TARGET_JSON_SCHEMA)
    target_schema["properties"] = dict(target_schema["properties"])
    target_schema["properties"]["self_ref"] = {"type": "string"}
    target_schema["required"] = list(target_schema["required"]) + ["self_ref"]
    _write_schema_pair(
        schemas,
        "target",
        yaml_body='schema_version: 1\ntypes:\n  task: {}\nself_ref: "[target:task]"\n',
        json_schema=target_schema,
    )
    report = validate_all(tmp_path)
    assert not report.is_clean
    msgs = [i.message for i in report.issues]
    assert any("intra-schema" in m and "bare" in m for m in msgs), msgs


# Permissive consumer: accepts any token shape (general reference_token).
_PERMISSIVE_CONSUMER_JSON_SCHEMA: dict = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["schema_version", "applies_to"],
    "additionalProperties": False,
    "properties": {
        "schema_version": {"type": "integer", "const": 1},
        "applies_to": {
            "type": "array",
            "items": {
                "type": "string",
                "pattern": r"^\[[a-z][a-z0-9-]*:[a-z][a-z0-9-]*\]$",
            },
        },
    },
}


def test_resolver_can_be_disabled(tmp_path: Path) -> None:
    """`--shape-only` skips the resolver pass."""
    schemas = _make_capability(tmp_path, "demo")
    # Reference a non-existent namespace — resolver would fail; shape accepts.
    _write_schema_pair(
        schemas,
        "consumer",
        yaml_body='schema_version: 1\napplies_to: ["[missing:foo]"]\n',
        json_schema=_PERMISSIVE_CONSUMER_JSON_SCHEMA,
    )
    runner = CliRunner()
    consumer_yaml = schemas / "consumer.yaml"
    result = runner.invoke(
        main,
        ["schemas", "validate", str(consumer_yaml), "--shape-only"],
    )
    assert result.exit_code == 0, result.output


def test_resolver_runs_by_default_from_cli(tmp_path: Path) -> None:
    """Default `pkit schemas validate` runs the resolver and exits non-zero on unresolved refs."""
    schemas = _make_capability(tmp_path, "demo")
    _write_schema_pair(
        schemas,
        "consumer",
        yaml_body='schema_version: 1\napplies_to: ["[missing:foo]"]\n',
        json_schema=_PERMISSIVE_CONSUMER_JSON_SCHEMA,
    )
    runner = CliRunner()
    consumer_yaml = schemas / "consumer.yaml"
    result = runner.invoke(main, ["schemas", "validate", str(consumer_yaml)])
    assert result.exit_code != 0, result.output
    assert "sibling companion" in result.output or "not found" in result.output


def test_resolver_supports_list_of_objects_with_id(tmp_path: Path) -> None:
    """Target collection may be a list of objects each carrying an `id` field."""
    schemas = _make_capability(tmp_path, "demo")
    list_target_schema: dict = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "x-pkit-id-collection": "/items",
        "required": ["schema_version", "items"],
        "additionalProperties": False,
        "properties": {
            "schema_version": {"type": "integer", "const": 1},
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id"],
                    "properties": {"id": {"type": "string"}},
                },
            },
        },
    }
    _write_schema_pair(
        schemas,
        "target",
        yaml_body=(
            "schema_version: 1\n"
            "items:\n"
            "  - id: alpha\n"
            "  - id: beta\n"
        ),
        json_schema=list_target_schema,
    )
    _write_schema_pair(
        schemas,
        "consumer",
        yaml_body='schema_version: 1\napplies_to: ["[target:alpha]"]\n',
        json_schema=_CONSUMER_JSON_SCHEMA,
    )
    report = validate_all(tmp_path)
    assert report.is_clean, report.issues


def test_resolver_validates_keys_via_x_pkit_keys_from_namespace(tmp_path: Path) -> None:
    """Bare mapping keys + x-pkit-keys-from-namespace annotation resolve against target."""
    schemas = _make_capability(tmp_path, "demo")
    _write_schema_pair(schemas, "target", yaml_body=_TARGET_YAML, json_schema=_TARGET_JSON_SCHEMA)
    consumer_schema: dict = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["schema_version", "by_type"],
        "additionalProperties": False,
        "properties": {
            "schema_version": {"type": "integer", "const": 1},
            "by_type": {
                "type": "object",
                "x-pkit-keys-from-namespace": "target",
                "patternProperties": {
                    "^[a-z][a-z0-9-]*$": {"type": "object"},
                },
                "additionalProperties": False,
            },
        },
    }
    _write_schema_pair(
        schemas,
        "consumer",
        yaml_body=(
            "schema_version: 1\n"
            "by_type:\n"
            "  task: {}\n"
            "  feature: {}\n"
        ),
        json_schema=consumer_schema,
    )
    report = validate_all(tmp_path)
    assert report.is_clean, report.issues


def test_resolver_flags_unknown_key_via_x_pkit_keys_from_namespace(tmp_path: Path) -> None:
    """Bare key not in target namespace surfaces as a resolver error."""
    schemas = _make_capability(tmp_path, "demo")
    _write_schema_pair(schemas, "target", yaml_body=_TARGET_YAML, json_schema=_TARGET_JSON_SCHEMA)
    consumer_schema: dict = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["schema_version", "by_type"],
        "additionalProperties": False,
        "properties": {
            "schema_version": {"type": "integer", "const": 1},
            "by_type": {
                "type": "object",
                "x-pkit-keys-from-namespace": "target",
                "patternProperties": {
                    "^[a-z][a-z0-9-]*$": {"type": "object"},
                },
                "additionalProperties": False,
            },
        },
    }
    _write_schema_pair(
        schemas,
        "consumer",
        yaml_body=(
            "schema_version: 1\n"
            "by_type:\n"
            "  task: {}\n"
            "  bogus: {}\n"
        ),
        json_schema=consumer_schema,
    )
    report = validate_all(tmp_path)
    assert not report.is_clean
    msgs = [i.message for i in report.issues]
    assert any("'bogus'" in m and "namespace 'target'" in m for m in msgs), msgs
    # Valid key should not fire.
    assert not any("'task'" in m for m in msgs), msgs


def test_resolver_flags_keys_annotation_for_missing_namespace(tmp_path: Path) -> None:
    """The annotation pointing at a non-existent namespace surfaces as a resolver error."""
    schemas = _make_capability(tmp_path, "demo")
    consumer_schema: dict = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["schema_version", "by_type"],
        "additionalProperties": False,
        "properties": {
            "schema_version": {"type": "integer", "const": 1},
            "by_type": {
                "type": "object",
                "x-pkit-keys-from-namespace": "missing",
                "patternProperties": {
                    "^[a-z][a-z0-9-]*$": {"type": "object"},
                },
                "additionalProperties": False,
            },
        },
    }
    _write_schema_pair(
        schemas,
        "consumer",
        yaml_body=(
            "schema_version: 1\n"
            "by_type:\n"
            "  whatever: {}\n"
        ),
        json_schema=consumer_schema,
    )
    report = validate_all(tmp_path)
    assert not report.is_clean
    msgs = [i.message for i in report.issues]
    assert any("x-pkit-keys-from-namespace" in m and "missing" in m for m in msgs), msgs


def test_shape_validator_resolves_cross_file_ref_to_sibling(tmp_path: Path) -> None:
    """A companion's `$ref` to a sibling companion's `$defs` resolves via the Registry."""
    schemas = _make_capability(tmp_path, "demo")
    # Target schema publishes a narrowed token pattern in its own $defs.
    target_schema: dict = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "target.schema.json",
        "x-pkit-id-collection": "/types",
        "type": "object",
        "required": ["schema_version", "types"],
        "additionalProperties": False,
        "properties": {
            "schema_version": {"type": "integer", "const": 1},
            "types": {
                "type": "object",
                "patternProperties": {"^[a-z][a-z0-9-]*$": {"type": "object"}},
                "additionalProperties": False,
            },
        },
        "$defs": {
            "target_ref": {
                "type": "string",
                "pattern": r"^\[target:[a-z][a-z0-9-]*\]$",
            },
        },
    }
    _write_schema_pair(schemas, "target", yaml_body=_TARGET_YAML, json_schema=target_schema)
    # Consumer cross-file `$ref`s the sibling's $defs.target_ref.
    consumer_schema: dict = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "consumer.schema.json",
        "type": "object",
        "required": ["schema_version", "applies_to"],
        "additionalProperties": False,
        "properties": {
            "schema_version": {"type": "integer", "const": 1},
            "applies_to": {
                "type": "array",
                "items": {"$ref": "target.schema.json#/$defs/target_ref"},
            },
        },
    }
    _write_schema_pair(
        schemas,
        "consumer",
        yaml_body='schema_version: 1\napplies_to: ["[target:task]"]\n',
        json_schema=consumer_schema,
    )
    report = validate_all(tmp_path)
    assert report.is_clean, report.issues


def test_shape_validator_catches_shape_mismatch_via_cross_file_ref(tmp_path: Path) -> None:
    """A YAML value that doesn't match the cross-referenced pattern surfaces as a shape issue."""
    schemas = _make_capability(tmp_path, "demo")
    target_schema: dict = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "target.schema.json",
        "x-pkit-id-collection": "/types",
        "type": "object",
        "required": ["schema_version", "types"],
        "additionalProperties": False,
        "properties": {
            "schema_version": {"type": "integer", "const": 1},
            "types": {
                "type": "object",
                "patternProperties": {"^[a-z][a-z0-9-]*$": {"type": "object"}},
                "additionalProperties": False,
            },
        },
        "$defs": {
            "target_ref": {
                "type": "string",
                "pattern": r"^\[target:[a-z][a-z0-9-]*\]$",
            },
        },
    }
    _write_schema_pair(schemas, "target", yaml_body=_TARGET_YAML, json_schema=target_schema)
    consumer_schema: dict = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "consumer.schema.json",
        "type": "object",
        "required": ["schema_version", "applies_to"],
        "additionalProperties": False,
        "properties": {
            "schema_version": {"type": "integer", "const": 1},
            "applies_to": {
                "type": "array",
                "items": {"$ref": "target.schema.json#/$defs/target_ref"},
            },
        },
    }
    _write_schema_pair(
        schemas,
        "consumer",
        # Value shape (bare id) doesn't match the cross-file pattern (token form).
        yaml_body='schema_version: 1\napplies_to: ["task"]\n',
        json_schema=consumer_schema,
    )
    report = validate_all(tmp_path)
    assert not report.is_clean
    msgs = [i.message for i in report.issues]
    assert any("does not match" in m or "pattern" in m for m in msgs), msgs


def test_shape_validator_resolves_cross_file_ref_to_kit_defs(tmp_path: Path) -> None:
    """A companion's `$ref` to `.pkit/schemas/_defs/refs.schema.json` resolves via the Registry."""
    # Set up the kit-wide _defs.
    defs_dir = tmp_path / ".pkit" / "schemas" / "_defs"
    defs_dir.mkdir(parents=True)
    refs_schema: dict = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "refs.schema.json",
        "$defs": {
            "envelope_version": {"type": "integer", "minimum": 1},
        },
    }
    (defs_dir / "refs.schema.json").write_text(json.dumps(refs_schema), encoding="utf-8")
    # Consumer cross-file `$ref`s into the kit-wide _defs.
    schemas = _make_capability(tmp_path, "demo")
    consumer_schema: dict = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "consumer.schema.json",
        "type": "object",
        "required": ["schema_version"],
        "additionalProperties": False,
        "properties": {
            "schema_version": {"$ref": "refs.schema.json#/$defs/envelope_version"},
        },
    }
    _write_schema_pair(
        schemas,
        "consumer",
        yaml_body="schema_version: 1\n",
        json_schema=consumer_schema,
    )
    report = validate_all(tmp_path)
    assert report.is_clean, report.issues


def test_wrong_namespace_token_reports_once_not_twice(tmp_path: Path) -> None:
    """A wrong-namespace token fires shape + resolver checks; only the resolver one surfaces."""
    schemas = _make_capability(tmp_path, "demo")
    _write_schema_pair(schemas, "target", yaml_body=_TARGET_YAML, json_schema=_TARGET_JSON_SCHEMA)
    # Consumer's pattern is narrowed to the `target` namespace.
    consumer_schema: dict = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["schema_version", "applies_to"],
        "additionalProperties": False,
        "properties": {
            "schema_version": {"type": "integer", "const": 1},
            "applies_to": {
                "type": "array",
                "items": {
                    "type": "string",
                    "pattern": r"^\[target:[a-z][a-z0-9-]*\]$",
                },
            },
        },
    }
    _write_schema_pair(
        schemas,
        "consumer",
        # Token uses a different namespace than the field's pattern.
        yaml_body='schema_version: 1\napplies_to: ["[unknownns:task]"]\n',
        json_schema=consumer_schema,
    )
    report = validate_all(tmp_path)
    assert not report.is_clean
    # Only ONE issue at the offending data position — the resolver's,
    # not the shape pass's redundant "does not match" message.
    issues_at_pos = [
        i for i in report.issues
        if "applies_to/0" in i.location
    ]
    assert len(issues_at_pos) == 1, [i.message for i in issues_at_pos]
    assert "unresolved reference" in issues_at_pos[0].message


def test_no_crash_when_referenced_sibling_companion_is_malformed_json(tmp_path: Path) -> None:
    """A consumer that $refs a malformed sibling gets a clean issue, not a crash."""
    schemas = _make_capability(tmp_path, "demo")
    # Sibling whose JSON is broken.
    sibling_path = schemas / "target.schema.json"
    sibling_path.write_text('{ "broken', encoding="utf-8")
    (schemas / "target.yaml").write_text("schema_version: 1\n", encoding="utf-8")
    # Consumer $refs into the broken sibling.
    consumer_schema: dict = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "consumer.schema.json",
        "type": "object",
        "required": ["schema_version", "applies_to"],
        "additionalProperties": False,
        "properties": {
            "schema_version": {"type": "integer", "const": 1},
            "applies_to": {
                "type": "array",
                "items": {"$ref": "target.schema.json#/$defs/target_ref"},
            },
        },
    }
    _write_schema_pair(
        schemas,
        "consumer",
        yaml_body='schema_version: 1\napplies_to: ["[target:task]"]\n',
        json_schema=consumer_schema,
    )
    # Should NOT raise; should produce clean issues.
    report = validate_all(tmp_path)
    assert not report.is_clean
    msgs = [i.message for i in report.issues]
    # One issue against the broken sibling itself.
    assert any("not valid JSON" in m for m in msgs), msgs
    # One issue against the consumer naming the unresolvable $ref.
    assert any("cross-file $ref could not resolve" in m for m in msgs), msgs


def test_no_crash_when_referenced_sibling_companion_is_missing(tmp_path: Path) -> None:
    """A consumer that $refs a missing sibling gets a clean issue, not a crash."""
    schemas = _make_capability(tmp_path, "demo")
    # Note: no target.schema.json on disk.
    consumer_schema: dict = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "consumer.schema.json",
        "type": "object",
        "required": ["schema_version", "applies_to"],
        "additionalProperties": False,
        "properties": {
            "schema_version": {"type": "integer", "const": 1},
            "applies_to": {
                "type": "array",
                "items": {"$ref": "target.schema.json#/$defs/target_ref"},
            },
        },
    }
    _write_schema_pair(
        schemas,
        "consumer",
        yaml_body='schema_version: 1\napplies_to: ["[target:task]"]\n',
        json_schema=consumer_schema,
    )
    report = validate_all(tmp_path)
    assert not report.is_clean
    msgs = [i.message for i in report.issues]
    # The consumer's $ref must surface as a clean message, not a crash.
    assert any("cross-file $ref could not resolve" in m for m in msgs), msgs


def test_no_crash_when_referenced_defs_entry_does_not_exist(tmp_path: Path) -> None:
    """Consumer $refs an entry name that doesn't exist in a valid sibling — clean issue."""
    schemas = _make_capability(tmp_path, "demo")
    target_schema: dict = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "target.schema.json",
        "x-pkit-id-collection": "/types",
        "type": "object",
        "required": ["schema_version", "types"],
        "additionalProperties": False,
        "properties": {
            "schema_version": {"type": "integer", "const": 1},
            "types": {"type": "object"},
        },
        "$defs": {
            # No `target_ref` here — consumer's $ref will fail to resolve.
            "something_else": {"type": "string"},
        },
    }
    _write_schema_pair(schemas, "target", yaml_body=_TARGET_YAML, json_schema=target_schema)
    consumer_schema: dict = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "consumer.schema.json",
        "type": "object",
        "required": ["schema_version", "applies_to"],
        "additionalProperties": False,
        "properties": {
            "schema_version": {"type": "integer", "const": 1},
            "applies_to": {
                "type": "array",
                "items": {"$ref": "target.schema.json#/$defs/target_ref"},
            },
        },
    }
    _write_schema_pair(
        schemas,
        "consumer",
        yaml_body='schema_version: 1\napplies_to: ["[target:task]"]\n',
        json_schema=consumer_schema,
    )
    report = validate_all(tmp_path)
    assert not report.is_clean
    msgs = [i.message for i in report.issues]
    assert any("cross-file $ref could not resolve" in m for m in msgs), msgs


def test_resolver_caches_namespace_across_pairs(tmp_path: Path) -> None:
    """Loading the same target namespace once should serve every consumer."""
    schemas = _make_capability(tmp_path, "demo")
    _write_schema_pair(schemas, "target", yaml_body=_TARGET_YAML, json_schema=_TARGET_JSON_SCHEMA)
    _write_schema_pair(
        schemas,
        "consumer_a",
        yaml_body='schema_version: 1\napplies_to: ["[target:task]"]\n',
        json_schema=_CONSUMER_JSON_SCHEMA,
    )
    _write_schema_pair(
        schemas,
        "consumer_b",
        yaml_body='schema_version: 1\napplies_to: ["[target:feature]"]\n',
        json_schema=_CONSUMER_JSON_SCHEMA,
    )
    report = validate_all(tmp_path)
    assert report.is_clean, report.issues
    assert report.pairs_checked == 3


# --- summarize_schemas / detail_namespace / resolve_token_to_target ---


def test_summarize_schemas_classifies_owners_vs_consumers(tmp_path: Path) -> None:
    """Schemas with `x-pkit-id-collection` are owners; others are consumers."""
    schemas = _make_capability(tmp_path, "demo")
    _write_schema_pair(schemas, "target", yaml_body=_TARGET_YAML, json_schema=_TARGET_JSON_SCHEMA)
    consumer_schema: dict = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["schema_version"],
        "additionalProperties": False,
        "properties": {"schema_version": {"type": "integer", "const": 1}},
    }
    _write_schema_pair(
        schemas, "consumer", yaml_body="schema_version: 1\n", json_schema=consumer_schema
    )
    summaries = summarize_schemas(tmp_path)
    by_name = {s.name: s for s in summaries}
    assert by_name["target"].is_namespace_owner is True
    assert by_name["target"].entry_ids == ("feature", "task")
    assert by_name["consumer"].is_namespace_owner is False
    assert by_name["consumer"].entry_ids == ()


def test_summarize_schemas_reports_load_errors_without_crashing(tmp_path: Path) -> None:
    """A malformed companion surfaces as load_error; the walk continues."""
    schemas = _make_capability(tmp_path, "demo")
    yaml_path = schemas / "broken.yaml"
    yaml_path.write_text(_MINIMAL_YAML, encoding="utf-8")
    (schemas / "broken.schema.json").write_text('{ "broken', encoding="utf-8")
    # And a good one alongside, to confirm the walk continues.
    _write_schema_pair(schemas, "ok", yaml_body=_MINIMAL_YAML, json_schema=_MINIMAL_JSON_SCHEMA)
    summaries = summarize_schemas(tmp_path)
    by_name = {s.name: s for s in summaries}
    assert by_name["broken"].load_error is not None
    assert "not valid JSON" in by_name["broken"].load_error
    assert by_name["ok"].load_error is None


def test_detail_namespace_finds_known_namespace(tmp_path: Path) -> None:
    schemas = _make_capability(tmp_path, "demo")
    _write_schema_pair(schemas, "target", yaml_body=_TARGET_YAML, json_schema=_TARGET_JSON_SCHEMA)
    detail = detail_namespace(tmp_path, "target")
    assert isinstance(detail, NamespaceDetail)
    assert detail.namespace == "target"
    assert [eid for eid, _ in detail.entries] == ["task", "feature"]


def test_detail_namespace_errors_on_unknown(tmp_path: Path) -> None:
    schemas = _make_capability(tmp_path, "demo")
    _write_schema_pair(schemas, "target", yaml_body=_TARGET_YAML, json_schema=_TARGET_JSON_SCHEMA)
    detail = detail_namespace(tmp_path, "nope")
    assert isinstance(detail, str)
    assert "not found" in detail and "Available namespaces" in detail


def test_resolve_token_resolves_known_token(tmp_path: Path) -> None:
    schemas = _make_capability(tmp_path, "demo")
    _write_schema_pair(schemas, "target", yaml_body=_TARGET_YAML, json_schema=_TARGET_JSON_SCHEMA)
    result = resolve_token_to_target(tmp_path, "[target:task]")
    assert isinstance(result, TokenResolution)
    assert result.namespace == "target"
    assert result.id == "task"


def test_resolve_token_errors_on_malformed(tmp_path: Path) -> None:
    result = resolve_token_to_target(tmp_path, "target:task")  # no brackets
    assert isinstance(result, str)
    assert "not a typed token" in result


def test_resolve_token_errors_on_unknown_id(tmp_path: Path) -> None:
    schemas = _make_capability(tmp_path, "demo")
    _write_schema_pair(schemas, "target", yaml_body=_TARGET_YAML, json_schema=_TARGET_JSON_SCHEMA)
    result = resolve_token_to_target(tmp_path, "[target:bogus]")
    assert isinstance(result, str)
    assert "'bogus'" in result and "namespace 'target'" in result
    assert "Known ids" in result


# --- CLI tests for list/show/resolve ----------------------------------


def test_cli_schemas_list(cli_target: Path) -> None:
    schemas = _make_capability(cli_target, "demo")
    _write_schema_pair(schemas, "target", yaml_body=_TARGET_YAML, json_schema=_TARGET_JSON_SCHEMA)
    runner = CliRunner()
    result = runner.invoke(main, ["schemas", "list"])
    assert result.exit_code == 0, result.output
    assert "capability: demo" in result.output
    assert "target" in result.output
    assert "task, feature" in result.output or "feature, task" in result.output


def test_cli_schemas_show(cli_target: Path) -> None:
    schemas = _make_capability(cli_target, "demo")
    _write_schema_pair(schemas, "target", yaml_body=_TARGET_YAML, json_schema=_TARGET_JSON_SCHEMA)
    runner = CliRunner()
    result = runner.invoke(main, ["schemas", "show", "target"])
    assert result.exit_code == 0, result.output
    assert "Namespace: target" in result.output
    assert "task" in result.output
    assert "feature" in result.output


def test_cli_schemas_show_unknown_errors(cli_target: Path) -> None:
    _make_capability(cli_target, "demo")  # empty
    runner = CliRunner()
    result = runner.invoke(main, ["schemas", "show", "nope"])
    assert result.exit_code != 0
    assert "not found" in result.output


def test_cli_schemas_resolve(cli_target: Path) -> None:
    schemas = _make_capability(cli_target, "demo")
    _write_schema_pair(schemas, "target", yaml_body=_TARGET_YAML, json_schema=_TARGET_JSON_SCHEMA)
    runner = CliRunner()
    result = runner.invoke(main, ["schemas", "resolve", "[target:task]"])
    assert result.exit_code == 0, result.output
    assert "Token: [target:task]" in result.output
    assert "Namespace: target" in result.output
    assert "Id:        task" in result.output


def test_cli_schemas_resolve_unknown_errors(cli_target: Path) -> None:
    _make_capability(cli_target, "demo")
    runner = CliRunner()
    result = runner.invoke(main, ["schemas", "resolve", "[target:task]"])
    assert result.exit_code != 0
    assert "not found" in result.output


# --- non-schema YAML exclusion from the companion requirement (issue #534) --
#
# `validate_path` (and its callers `pkit schemas validate` +
# `validate_capability_self_consistency`) must not demand a companion JSON
# Schema for YAML that isn't a schema definition: fixtures under `examples/`,
# `*-example.yaml` files, and instances validated against an *external*
# `$schema` (a shared/foreign schema, not their own companion). A genuine
# schema definition with no companion is still flagged (no COR-018 regression).


def test_example_dir_yaml_without_companion_not_flagged(tmp_path: Path) -> None:
    """A YAML under `examples/` is a fixture — never requires its own companion."""
    schemas = _make_capability(tmp_path, "demo")
    _write_schema_pair(schemas, "trip", yaml_body=_MINIMAL_YAML, json_schema=_MINIMAL_JSON_SCHEMA)
    examples = schemas / "examples"
    examples.mkdir()
    (examples / "japan.yaml").write_text(_MINIMAL_YAML, encoding="utf-8")  # no companion

    report = validate_path(schemas)
    assert report.is_clean
    # Only the real schema pair is enumerated; the fixture is excluded.
    assert report.pairs_checked == 1


def test_example_named_yaml_without_companion_not_flagged(tmp_path: Path) -> None:
    """A `*-example.yaml` file is a fixture by naming convention — no companion required."""
    schemas = _make_capability(tmp_path, "demo")
    _write_schema_pair(schemas, "trip", yaml_body=_MINIMAL_YAML, json_schema=_MINIMAL_JSON_SCHEMA)
    (schemas / "trip-example.yaml").write_text(_MINIMAL_YAML, encoding="utf-8")  # no companion

    report = validate_path(schemas)
    assert report.is_clean
    assert report.pairs_checked == 1


def _write_shared_defs_schema(
    schemas_dir: Path, name: str = "process", json_schema: dict | None = None
) -> Path:
    """Write a shared `_defs/<name>.schema.json` an instance's pointer can name."""
    defs = schemas_dir / "_defs"
    defs.mkdir(exist_ok=True)
    target = defs / f"{name}.schema.json"
    target.write_text(
        json.dumps(json_schema if json_schema is not None else _MINIMAL_JSON_SCHEMA),
        encoding="utf-8",
    )
    return target


def test_external_schema_directive_yaml_not_flagged(tmp_path: Path) -> None:
    """A YAML with a `# yaml-language-server: $schema=<external>` directive is an instance."""
    schemas = _make_capability(tmp_path, "demo")
    _write_schema_pair(
        schemas, "process", yaml_body=_MINIMAL_YAML, json_schema=_MINIMAL_JSON_SCHEMA
    )
    _write_shared_defs_schema(schemas)
    # A process-definition instance validated against a shared _defs schema.
    (schemas / "software-development.yaml").write_text(
        "# yaml-language-server: $schema=_defs/process.schema.json\n"
        "schema_version: 1\nname: sw-dev\n",
        encoding="utf-8",
    )  # no own companion

    report = validate_path(schemas)
    assert report.is_clean, [f"{i.location}: {i.message}" for i in report.issues]
    # No companion demanded of the instance — and it IS checked, against the
    # schema its pointer names.
    assert report.pairs_checked == 1
    assert report.instances_checked == 1


def test_external_schema_top_level_key_yaml_not_flagged(tmp_path: Path) -> None:
    """A YAML with a top-level `$schema:` key pointing at an external schema is an instance."""
    schemas = _make_capability(tmp_path, "demo")
    _write_schema_pair(
        schemas, "process", yaml_body=_MINIMAL_YAML, json_schema=_MINIMAL_JSON_SCHEMA
    )
    # The key form puts the pointer in the DATA, so the target must permit it —
    # the same rule the kit's own companions apply to `pkit_schema:` (COR-023).
    target = dict(_MINIMAL_JSON_SCHEMA)
    target["properties"] = dict(target["properties"]) | {"$schema": {"type": "string"}}
    _write_shared_defs_schema(schemas, json_schema=target)
    (schemas / "onboarding.yaml").write_text(
        "$schema: _defs/process.schema.json\nschema_version: 1\nname: onboarding\n",
        encoding="utf-8",
    )  # no own companion

    report = validate_path(schemas)
    assert report.is_clean, [f"{i.location}: {i.message}" for i in report.issues]
    assert report.pairs_checked == 1
    assert report.instances_checked == 1


def test_self_pointing_schema_directive_still_requires_companion(tmp_path: Path) -> None:
    """A `$schema` pointer at the YAML's *own* companion is an ordinary pair — still required."""
    schemas = _make_capability(tmp_path, "demo")
    (schemas / "alpha.yaml").write_text(
        "# yaml-language-server: $schema=alpha.schema.json\nschema_version: 1\nname: a\n",
        encoding="utf-8",
    )  # no companion on disk

    report = validate_path(schemas)
    assert not report.is_clean
    assert any("missing companion" in issue.message.lower() for issue in report.issues)


def test_genuine_schema_without_companion_still_flagged(tmp_path: Path) -> None:
    """The COR-018 true positive: a direct schema YAML with no companion is still flagged."""
    schemas = _make_capability(tmp_path, "demo")
    (schemas / "real.yaml").write_text(_MINIMAL_YAML, encoding="utf-8")  # no companion, no signals

    report = validate_path(schemas)
    assert not report.is_clean
    assert any("missing companion" in issue.message.lower() for issue in report.issues)


def _build_trip_planner_shaped_schemas(schemas: Path) -> None:
    """Populate a `schemas/` tree mirroring trip-planner's shape (issue #534).

    A genuine schema definition + side-by-side companion, an `examples/` fixture
    with no companion, and a process-definition YAML validated against a shared
    `_defs/` schema via a `$schema` directive.
    """
    _write_schema_pair(schemas, "trip", yaml_body=_MINIMAL_YAML, json_schema=_MINIMAL_JSON_SCHEMA)

    examples = schemas / "examples"
    examples.mkdir()
    (examples / "japan-example.yaml").write_text(_MINIMAL_YAML, encoding="utf-8")

    _write_shared_defs_schema(schemas)
    (schemas / "software-development.yaml").write_text(
        "# yaml-language-server: $schema=_defs/process.schema.json\n"
        "schema_version: 1\nname: sw-dev\n",
        encoding="utf-8",
    )


def test_trip_planner_shaped_capability_passes(tmp_path: Path) -> None:
    """The full trip-planner-shaped `schemas/` tree passes the companion check."""
    schemas = _make_capability(tmp_path, "trip-planning")
    _build_trip_planner_shaped_schemas(schemas)

    report = validate_path(schemas)
    assert report.is_clean, [f"{i.location}: {i.message}" for i in report.issues]
    # Only the genuine `trip` schema is enumerated; the example + process-def
    # are excluded as non-schema material.
    assert report.pairs_checked == 1


def test_trip_planner_shaped_capability_self_consistency_clean(tmp_path: Path) -> None:
    """`validate_capability_self_consistency` (register's check) accepts the trip-planner shape."""
    from project_kit.capabilities import (
        CapabilityPackage,
        CapabilitySource,
        validate_capability_self_consistency,
    )

    cap_dir = tmp_path / "trip-planning"
    (cap_dir / "schemas").mkdir(parents=True)
    (cap_dir / "README.md").write_text("# trip-planning\n", encoding="utf-8")
    _build_trip_planner_shaped_schemas(cap_dir / "schemas")

    package = CapabilityPackage(
        name="trip-planning",
        version="0.1.0",
        description="trip planning",
        requires_backbone=">=0.1.0",
    )
    source = CapabilitySource(name="trip-planning", path=cap_dir, package=package)

    problems = validate_capability_self_consistency(source)
    schema_problems = [p for p in problems if p.startswith("schema ")]
    assert schema_problems == [], schema_problems


# --- pointered instances ARE validated against their target (issue #710) -----
#
# The `$schema` pointer a definition carries used to buy nothing but the
# companion exemption above — nothing validated the file against the schema it
# named. These tests pin the pointer meaning what it says: the instance is
# checked against its declared target, findings land on the instance's own
# path, and a broken pointer is reported rather than silently skipped. The
# companion exemption is unchanged.

_SHIPPED_PROCESS_CONTRACT = (
    Path(__file__).resolve().parents[1]
    / ".pkit"
    / "schemas"
    / "_defs"
    / "process.schema.json"
)

# How `pkit process new` writes the pointer: the definition lands at
# `.pkit/capabilities/<cap>/schemas/<id>.yaml`, three levels below `.pkit/`.
_STAMPED_POINTER = "../../../schemas/_defs/process.schema.json"


def test_shipped_process_contract_declares_root_constraints() -> None:
    """The regression pin: a `$defs`-only contract accepts every document.

    Without these root keywords the stamped `$schema` pointer validates
    nothing — the exact defect issue #710 exists to close. Any future edit
    that drops the root fails here.
    """
    contract = json.loads(_SHIPPED_PROCESS_CONTRACT.read_text(encoding="utf-8"))
    assert contract["type"] == "object"
    assert contract["required"] == ["process"]
    assert contract["properties"]["process"] == {"$ref": "#/$defs/process"}


def _minimal_process_block() -> dict:
    """A minimal valid singleton process, in the shape the stamp emits."""
    return {
        "id": "demo",
        "version": 1,
        "subject": {"cardinality": "singleton"},
        "states": [
            {
                "id": "open",
                "meaning": "Open.",
                "detection": {
                    "mode": "inferred",
                    "predicate": {"run": "demo-detect-open"},
                },
            }
        ],
        "transitions": [],
    }


def _write_process_definition(target_root: Path, document: dict) -> Path:
    """Stamp a pointered process definition into a tmp tree beside the real contract.

    Copies the shipped `_defs/` library so the pointer resolves exactly as it
    does in an installed tree, then writes the definition with the same header
    directive `pkit process new` writes. The body is serialised as JSON, which
    the YAML loader reads natively — it keeps the nested definition readable
    here without a YAML dumper.
    """
    import shutil

    defs_dir = target_root / ".pkit" / "schemas" / "_defs"
    defs_dir.mkdir(parents=True, exist_ok=True)
    for schema_file in _SHIPPED_PROCESS_CONTRACT.parent.glob("*.schema.json"):
        shutil.copy(schema_file, defs_dir / schema_file.name)
    schemas = _make_capability(target_root, "demo")
    definition = schemas / "demo.yaml"
    definition.write_text(
        f"# yaml-language-server: $schema={_STAMPED_POINTER}\n"
        + json.dumps(document, indent=2)
        + "\n",
        encoding="utf-8",
    )
    return definition


def test_stamped_shape_definition_validates_clean(tmp_path: Path) -> None:
    """A valid definition carrying the stamped pointer passes — and IS checked."""
    _write_process_definition(tmp_path, {"process": _minimal_process_block()})
    report = validate_all(tmp_path)
    assert report.is_clean, [f"{i.location}: {i.message}" for i in report.issues]
    # No companion demanded (pairs_checked == 0), yet the file was validated.
    assert report.pairs_checked == 0
    assert report.instances_checked == 1


def test_definition_missing_process_envelope_is_reported(tmp_path: Path) -> None:
    """The root's `required: [process]` — the check a `$defs`-only contract lost."""
    _write_process_definition(tmp_path, _minimal_process_block())  # no envelope
    report = validate_all(tmp_path)
    assert not report.is_clean
    msgs = [i.message for i in report.issues]
    assert any("'process'" in m and "required" in m for m in msgs), msgs


def test_definition_missing_version_is_reported_at_its_position(tmp_path: Path) -> None:
    """A `process` block violating the shape is reported, located at the block."""
    block = _minimal_process_block()
    del block["version"]
    definition = _write_process_definition(tmp_path, {"process": block})
    report = validate_all(tmp_path)
    assert not report.is_clean
    findings = [
        i for i in report.issues if "'version'" in i.message and "required" in i.message
    ]
    assert findings, [f"{i.location}: {i.message}" for i in report.issues]
    # Reported against the instance's own path + a JSON pointer into the block.
    assert findings[0].location.endswith(f"{definition.name}/process")


def test_definition_with_bad_cardinality_is_reported_at_its_position(
    tmp_path: Path,
) -> None:
    """An enum violation deep in the block carries a pointer to the offending value."""
    block = _minimal_process_block()
    block["subject"]["cardinality"] = "swarm"  # not in the shipped enum
    _write_process_definition(tmp_path, {"process": block})
    report = validate_all(tmp_path)
    assert not report.is_clean
    locations = [i.location for i in report.issues]
    assert any(
        loc.endswith("/process/subject/cardinality") for loc in locations
    ), [f"{i.location}: {i.message}" for i in report.issues]


def test_pointered_instance_needs_no_companion_when_named_explicitly(
    tmp_path: Path,
) -> None:
    """`pkit schemas validate <instance.yaml>` must not demand a companion.

    Naming an instance directly is the natural way to check one file; the
    companion it categorically cannot have must not be required (COR-018's
    requirement scopes to schema definitions).
    """
    definition = _write_process_definition(
        tmp_path, {"process": _minimal_process_block()}
    )
    report = validate_path(definition, tmp_path)
    assert report.is_clean, [f"{i.location}: {i.message}" for i in report.issues]
    assert report.pairs_checked == 0
    assert report.instances_checked == 1


def test_pointered_instance_missing_target_is_reported(tmp_path: Path) -> None:
    """A pointer at a nonexistent file is a finding, never a silent skip."""
    schemas = _make_capability(tmp_path, "demo")
    (schemas / "typo.yaml").write_text(
        "# yaml-language-server: $schema=_defs/porcess.schema.json\n"
        "schema_version: 1\n",
        encoding="utf-8",
    )
    report = validate_all(tmp_path)
    assert not report.is_clean
    msgs = [i.message for i in report.issues]
    assert any("does not resolve to a file" in m for m in msgs), msgs
    assert any("porcess.schema.json" in m for m in msgs), msgs


def test_pointered_instance_unparseable_target_is_reported(tmp_path: Path) -> None:
    schemas = _make_capability(tmp_path, "demo")
    defs = schemas / "_defs"
    defs.mkdir()
    (defs / "process.schema.json").write_text('{ "broken', encoding="utf-8")
    (schemas / "instance.yaml").write_text(
        "# yaml-language-server: $schema=_defs/process.schema.json\n"
        "schema_version: 1\n",
        encoding="utf-8",
    )
    report = validate_all(tmp_path)
    assert not report.is_clean
    msgs = [i.message for i in report.issues]
    assert any("not valid JSON" in m for m in msgs), msgs


def test_pointered_instance_target_not_a_schema_is_reported(tmp_path: Path) -> None:
    """Valid JSON that isn't a valid Draft 2020-12 schema is reported, not applied."""
    schemas = _make_capability(tmp_path, "demo")
    _write_shared_defs_schema(
        schemas,
        json_schema={
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "fake-type",
        },
    )
    (schemas / "instance.yaml").write_text(
        "# yaml-language-server: $schema=_defs/process.schema.json\n"
        "schema_version: 1\n",
        encoding="utf-8",
    )
    report = validate_all(tmp_path)
    assert not report.is_clean
    msgs = [i.message for i in report.issues]
    assert any("not a valid Draft 2020-12" in m for m in msgs), msgs


def test_pointered_instance_malformed_yaml_is_reported(tmp_path: Path) -> None:
    schemas = _make_capability(tmp_path, "demo")
    _write_shared_defs_schema(schemas)
    (schemas / "instance.yaml").write_text(
        "# yaml-language-server: $schema=_defs/process.schema.json\n"
        "schema_version: 1\n  name: bad-indent\n",
        encoding="utf-8",
    )
    report = validate_all(tmp_path)
    assert not report.is_clean
    msgs = [i.message for i in report.issues]
    assert any("yaml parse error" in m.lower() for m in msgs), msgs


def test_remote_pointer_is_exempt_but_not_validated(tmp_path: Path) -> None:
    """A `https://` target can't be read offline: still exempt, not a finding."""
    schemas = _make_capability(tmp_path, "demo")
    (schemas / "instance.yaml").write_text(
        "# yaml-language-server: $schema=https://example.invalid/process.schema.json\n"
        "schema_version: 1\n",
        encoding="utf-8",
    )
    report = validate_all(tmp_path)
    assert report.is_clean, [f"{i.location}: {i.message}" for i in report.issues]
    assert report.pairs_checked == 0
    assert report.instances_checked == 0


def test_cli_reports_instance_shape_failure_and_exits_nonzero(cli_target: Path) -> None:
    """The gate `scripts/check.sh` runs surfaces a malformed definition."""
    block = _minimal_process_block()
    del block["states"]
    definition = _write_process_definition(cli_target, {"process": block})
    result = CliRunner().invoke(main, ["schemas", "validate"])
    assert result.exit_code != 0, result.output
    assert definition.name in result.output
    assert "'states'" in result.output


def test_cli_clean_run_counts_instances(cli_target: Path) -> None:
    _write_process_definition(cli_target, {"process": _minimal_process_block()})
    result = CliRunner().invoke(main, ["schemas", "validate"])
    assert result.exit_code == 0, result.output
    assert "1 instance(s)" in result.output
