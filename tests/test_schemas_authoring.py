"""Tests for `pkit schemas add` and `project_kit.schemas_authoring`."""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path

import pytest
from click.testing import CliRunner

from project_kit.cli import main
from project_kit.schemas_authoring import (
    RenameResult,
    SchemaAuthoringError,
    SchemaStampResult,
    add_entry_to_namespace,
    load_entry_data,
    rename_entry,
    stamp_new_schema,
)


# Fixtures --------------------------------------------------------------


def _setup_namespace(tmp_path: Path) -> tuple[Path, Path]:
    """Stamp a capability with a namespace-owning schema. Returns (yaml, companion) paths."""
    schemas = tmp_path / ".pkit" / "capabilities" / "demo" / "schemas"
    schemas.mkdir(parents=True)
    yaml_body = (
        "# A taxonomy.\n"
        "schema_version: 1\n"
        "types:\n"
        "  task:\n"
        "    role: A unit of work.\n"
        "  feature:\n"
        "    role: A coherent capability.\n"
    )
    yaml_path = schemas / "issue-types.yaml"
    yaml_path.write_text(yaml_body, encoding="utf-8")
    companion: dict = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "issue-types.schema.json",
        "x-pkit-id-collection": "/types",
        "type": "object",
        "required": ["schema_version", "types"],
        "additionalProperties": False,
        "properties": {
            "schema_version": {"type": "integer", "const": 1},
            "types": {
                "type": "object",
                "patternProperties": {
                    "^[a-z][a-z0-9-]*$": {
                        "type": "object",
                        "required": ["role"],
                        "additionalProperties": False,
                        "properties": {"role": {"type": "string", "minLength": 1}},
                    },
                },
                "additionalProperties": False,
            },
        },
    }
    companion_path = schemas / "issue-types.schema.json"
    companion_path.write_text(json.dumps(companion), encoding="utf-8")
    return yaml_path, companion_path


def _setup_list_form_namespace(tmp_path: Path) -> Path:
    """Stamp a capability with a list-of-objects-with-id namespace."""
    schemas = tmp_path / ".pkit" / "capabilities" / "demo" / "schemas"
    schemas.mkdir(parents=True)
    yaml_body = (
        "schema_version: 1\n"
        "items:\n"
        "  - id: alpha\n"
        "    label: Alpha\n"
        "  - id: beta\n"
        "    label: Beta\n"
    )
    yaml_path = schemas / "list-ns.yaml"
    yaml_path.write_text(yaml_body, encoding="utf-8")
    companion: dict = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "x-pkit-id-collection": "/items",
        "type": "object",
        "required": ["schema_version", "items"],
        "additionalProperties": False,
        "properties": {
            "schema_version": {"type": "integer", "const": 1},
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["id", "label"],
                    "additionalProperties": False,
                    "properties": {
                        "id": {"type": "string"},
                        "label": {"type": "string", "minLength": 1},
                    },
                },
            },
        },
    }
    (schemas / "list-ns.schema.json").write_text(json.dumps(companion), encoding="utf-8")
    return yaml_path


# add_entry_to_namespace ------------------------------------------------


def test_add_appends_entry_to_mapping_collection(tmp_path: Path) -> None:
    yaml_path, _ = _setup_namespace(tmp_path)
    add_entry_to_namespace(
        tmp_path,
        "issue-types",
        "umbrella",
        {"role": "A bucket of related Tasks."},
    )
    content = yaml_path.read_text(encoding="utf-8")
    assert "umbrella:" in content
    assert "A bucket of related Tasks." in content


def test_add_preserves_existing_comments_and_order(tmp_path: Path) -> None:
    """Round-trip YAML write keeps the file's leading comment and existing key order."""
    yaml_path, _ = _setup_namespace(tmp_path)
    add_entry_to_namespace(
        tmp_path, "issue-types", "umbrella", {"role": "Bucket."}
    )
    content = yaml_path.read_text(encoding="utf-8")
    assert content.startswith("# A taxonomy.")
    # The pre-existing types appear before the new one.
    task_idx = content.index("task:")
    feature_idx = content.index("feature:")
    umbrella_idx = content.index("umbrella:")
    assert task_idx < feature_idx < umbrella_idx


def test_add_to_list_collection_appends_with_id_first(tmp_path: Path) -> None:
    yaml_path = _setup_list_form_namespace(tmp_path)
    add_entry_to_namespace(tmp_path, "list-ns", "gamma", {"label": "Gamma"})
    content = yaml_path.read_text(encoding="utf-8")
    # The new item appears after the existing two.
    alpha_idx = content.index("- id: alpha")
    gamma_idx = content.index("- id: gamma")
    assert alpha_idx < gamma_idx
    assert "label: Gamma" in content


def test_add_rejects_duplicate_id(tmp_path: Path) -> None:
    _setup_namespace(tmp_path)
    with pytest.raises(SchemaAuthoringError, match="'task' already exists"):
        add_entry_to_namespace(tmp_path, "issue-types", "task", {"role": "dup"})


def test_add_rejects_unknown_namespace(tmp_path: Path) -> None:
    _setup_namespace(tmp_path)
    with pytest.raises(SchemaAuthoringError, match="namespace 'nope'"):
        add_entry_to_namespace(tmp_path, "nope", "foo", {"role": "x"})


def test_add_restores_original_on_validation_failure(tmp_path: Path) -> None:
    """An entry that doesn't satisfy the schema causes the file to be restored."""
    yaml_path, _ = _setup_namespace(tmp_path)
    original = yaml_path.read_text(encoding="utf-8")
    with pytest.raises(SchemaAuthoringError, match="would fail validation"):
        add_entry_to_namespace(
            tmp_path,
            "issue-types",
            "broken",
            # Missing required `role` field.
            {"description": "no role"},
        )
    assert yaml_path.read_text(encoding="utf-8") == original


# load_entry_data -------------------------------------------------------


def test_load_entry_data_from_yaml_file(tmp_path: Path) -> None:
    p = tmp_path / "entry.yaml"
    p.write_text("foo: bar\nbaz: 1\n", encoding="utf-8")
    data = load_entry_data(p)
    assert data == {"foo": "bar", "baz": 1}


def test_load_entry_data_from_json_file(tmp_path: Path) -> None:
    p = tmp_path / "entry.json"
    p.write_text('{"foo": "bar"}', encoding="utf-8")
    data = load_entry_data(p)
    assert data == {"foo": "bar"}


def test_load_entry_data_from_stdin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin", StringIO("foo: bar\n"))
    data = load_entry_data(None)
    assert data == {"foo": "bar"}


def test_load_entry_data_rejects_non_mapping(tmp_path: Path) -> None:
    p = tmp_path / "entry.yaml"
    p.write_text("- a\n- b\n", encoding="utf-8")  # a list
    with pytest.raises(SchemaAuthoringError, match="expected a mapping"):
        load_entry_data(p)


# CLI -------------------------------------------------------------------


def test_cli_schemas_add_via_file(tmp_path: Path) -> None:
    _setup_namespace(tmp_path)
    entry_file = tmp_path / "new.yaml"
    entry_file.write_text("role: A bucket of related Tasks.\n", encoding="utf-8")
    runner = CliRunner()
    # Run in the tmp_path subtree (cli's find_target_root walks up looking for .pkit).
    with runner.isolated_filesystem(temp_dir=tmp_path):
        import shutil

        shutil.copytree(tmp_path / ".pkit", Path.cwd() / ".pkit", dirs_exist_ok=True)
        shutil.copy(entry_file, Path.cwd() / "new.yaml")
        result = runner.invoke(
            main, ["schemas", "add", "issue-types", "umbrella", "--from", "new.yaml"]
        )
    assert result.exit_code == 0, result.output
    assert "Added entry 'umbrella'" in result.output


def test_cli_schemas_add_via_stdin(tmp_path: Path) -> None:
    _setup_namespace(tmp_path)
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        import shutil

        shutil.copytree(tmp_path / ".pkit", Path.cwd() / ".pkit", dirs_exist_ok=True)
        result = runner.invoke(
            main,
            ["schemas", "add", "issue-types", "umbrella", "--from", "-"],
            input="role: A bucket of related Tasks.\n",
        )
    assert result.exit_code == 0, result.output


def test_cli_schemas_add_reports_validation_failure(tmp_path: Path) -> None:
    _setup_namespace(tmp_path)
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        import shutil

        shutil.copytree(tmp_path / ".pkit", Path.cwd() / ".pkit", dirs_exist_ok=True)
        result = runner.invoke(
            main,
            ["schemas", "add", "issue-types", "bad", "--from", "-"],
            input="description: no role field\n",
        )
    assert result.exit_code != 0
    assert "would fail validation" in result.output


def test_cli_schemas_add_unknown_namespace_errors(tmp_path: Path) -> None:
    _setup_namespace(tmp_path)
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        import shutil

        shutil.copytree(tmp_path / ".pkit", Path.cwd() / ".pkit", dirs_exist_ok=True)
        result = runner.invoke(
            main,
            ["schemas", "add", "nope", "foo", "--from", "-"],
            input="x: 1\n",
        )
    assert result.exit_code != 0
    assert "not found" in result.output


# stamp_new_schema ------------------------------------------------------


def _stamp_empty_capability(tmp_path: Path) -> Path:
    """Create a capability directory with no schemas yet (so stamp can land cleanly)."""
    cap_dir = tmp_path / ".pkit" / "capabilities" / "demo"
    cap_dir.mkdir(parents=True)
    return cap_dir


def test_stamp_new_schema_mapping_form(tmp_path: Path) -> None:
    _stamp_empty_capability(tmp_path)
    result = stamp_new_schema(
        tmp_path, capability="demo", name="my-namespace", collection_name="kinds"
    )
    assert isinstance(result, SchemaStampResult)
    assert result.yaml_path.is_file()
    assert result.companion_path.is_file()
    yaml_text = result.yaml_path.read_text(encoding="utf-8")
    assert "schema_version: 1" in yaml_text
    assert "kinds: {}" in yaml_text
    companion = json.loads(result.companion_path.read_text(encoding="utf-8"))
    assert companion["x-pkit-id-collection"] == "/kinds"
    assert "patternProperties" in companion["properties"]["kinds"]


def test_stamp_new_schema_list_form(tmp_path: Path) -> None:
    _stamp_empty_capability(tmp_path)
    result = stamp_new_schema(
        tmp_path,
        capability="demo",
        name="my-list",
        collection_form="list",
        collection_name="items",
    )
    yaml_text = result.yaml_path.read_text(encoding="utf-8")
    assert "items: []" in yaml_text
    companion = json.loads(result.companion_path.read_text(encoding="utf-8"))
    assert companion["properties"]["items"]["type"] == "array"
    assert companion["$defs"]["entry"]["required"] == ["id"]


def test_stamp_refuses_when_files_exist(tmp_path: Path) -> None:
    _stamp_empty_capability(tmp_path)
    stamp_new_schema(tmp_path, capability="demo", name="dup")
    with pytest.raises(SchemaAuthoringError, match="already exists"):
        stamp_new_schema(tmp_path, capability="demo", name="dup")


def test_stamp_refuses_when_capability_missing(tmp_path: Path) -> None:
    with pytest.raises(SchemaAuthoringError, match="capability 'missing'"):
        stamp_new_schema(tmp_path, capability="missing", name="schema")


# stamp_new_schema — core area (.pkit/schemas/) ------------------------


def _core_schemas_area(tmp_path: Path) -> Path:
    """Create the core schemas area so a `core` stamp can land cleanly."""
    area = tmp_path / ".pkit" / "schemas"
    area.mkdir(parents=True)
    return area


def test_stamp_new_schema_core_area_namespace(tmp_path: Path) -> None:
    _core_schemas_area(tmp_path)
    result = stamp_new_schema(
        tmp_path, capability="core", name="perm-grants", collection_name="grants"
    )
    assert result.yaml_path == tmp_path / ".pkit" / "schemas" / "perm-grants.yaml"
    assert result.companion_path == tmp_path / ".pkit" / "schemas" / "perm-grants.schema.json"
    assert result.yaml_path.is_file()
    companion = json.loads(result.companion_path.read_text(encoding="utf-8"))
    assert companion["x-pkit-id-collection"] == "/grants"


def test_stamp_new_schema_core_area_document(tmp_path: Path) -> None:
    _core_schemas_area(tmp_path)
    result = stamp_new_schema(
        tmp_path, capability="core", name="perm-config", no_namespace=True
    )
    assert result.yaml_path == tmp_path / ".pkit" / "schemas" / "perm-config.yaml"
    companion = json.loads(result.companion_path.read_text(encoding="utf-8"))
    assert "x-pkit-id-collection" not in companion


def test_stamp_core_refuses_when_exists(tmp_path: Path) -> None:
    _core_schemas_area(tmp_path)
    stamp_new_schema(tmp_path, capability="core", name="dup")
    with pytest.raises(SchemaAuthoringError, match="already exists in the core schemas area"):
        stamp_new_schema(tmp_path, capability="core", name="dup")


def test_stamp_core_refuses_when_area_missing(tmp_path: Path) -> None:
    # No .pkit/schemas/ in this tree.
    with pytest.raises(SchemaAuthoringError, match="core schemas area not found"):
        stamp_new_schema(tmp_path, capability="core", name="orphan")


def test_stamp_refuses_non_kebab_name(tmp_path: Path) -> None:
    _stamp_empty_capability(tmp_path)
    with pytest.raises(SchemaAuthoringError, match="must be kebab-case"):
        stamp_new_schema(tmp_path, capability="demo", name="Bad_Name")


def test_stamp_refuses_non_kebab_collection_name(tmp_path: Path) -> None:
    _stamp_empty_capability(tmp_path)
    with pytest.raises(SchemaAuthoringError, match="must be kebab-case"):
        stamp_new_schema(
            tmp_path, capability="demo", name="good", collection_name="BadName"
        )


def test_stamp_validates_clean_via_pkit_schemas_validate(tmp_path: Path) -> None:
    """The stamped file passes the full validator end-to-end."""
    _stamp_empty_capability(tmp_path)
    stamp_new_schema(tmp_path, capability="demo", name="freshly-stamped")
    # Use the standard validator path.
    from project_kit.schemas_validate import validate_all

    report = validate_all(tmp_path)
    assert report.is_clean, report.issues


# stamp_new_schema --no-namespace --------------------------------------


def test_stamp_document_shape_yaml_has_no_collection(tmp_path: Path) -> None:
    """`--no-namespace` stamps a document YAML with no top-level collection key."""
    _stamp_empty_capability(tmp_path)
    result = stamp_new_schema(
        tmp_path, capability="demo", name="trip", no_namespace=True
    )
    assert isinstance(result, SchemaStampResult)
    yaml_text = result.yaml_path.read_text(encoding="utf-8")
    # Envelope present.
    assert "schema_version: 1" in yaml_text
    # No collection wrapper key.
    for forbidden in ("entries:", "types:", "items: []", "entries: []", "entries: {}"):
        assert forbidden not in yaml_text, (
            f"document YAML must not contain collection wrapper {forbidden!r}; "
            f"got:\n{yaml_text}"
        )


def test_stamp_document_shape_companion_has_no_collection_annotation(
    tmp_path: Path,
) -> None:
    """`--no-namespace` companion omits `x-pkit-id-collection`."""
    _stamp_empty_capability(tmp_path)
    result = stamp_new_schema(
        tmp_path, capability="demo", name="trip", no_namespace=True
    )
    companion = json.loads(result.companion_path.read_text(encoding="utf-8"))
    assert "x-pkit-id-collection" not in companion


def test_stamp_document_shape_companion_has_flat_properties(tmp_path: Path) -> None:
    """`--no-namespace` companion has flat `properties` (not a `patternProperties` collection).

    Properties starts with the envelope fields (`schema_version`, `source`)
    plus no namespaced collection — author adds document fields here.
    """
    _stamp_empty_capability(tmp_path)
    result = stamp_new_schema(
        tmp_path, capability="demo", name="trip", no_namespace=True
    )
    companion = json.loads(result.companion_path.read_text(encoding="utf-8"))
    assert companion["type"] == "object"
    assert companion["additionalProperties"] is False
    # Top-level `properties` is a flat mapping with just the envelope fields,
    # not a collection wrapper with `patternProperties`/`items`.
    properties = companion["properties"]
    assert "schema_version" in properties
    assert "patternProperties" not in companion  # not at the root
    # The author fills properties beyond the envelope, so we should NOT see
    # a nested collection-shaped property.
    for prop_name, prop_schema in properties.items():
        if isinstance(prop_schema, dict):
            assert "patternProperties" not in prop_schema, (
                f"document property {prop_name!r} should not be a collection wrapper"
            )


def test_stamp_document_shape_has_no_defs_entry(tmp_path: Path) -> None:
    """`--no-namespace` companion does not carry a `$defs.entry` placeholder.

    Document schemas describe one resource per file; there's no per-entry
    shape to declare.
    """
    _stamp_empty_capability(tmp_path)
    result = stamp_new_schema(
        tmp_path, capability="demo", name="trip", no_namespace=True
    )
    companion = json.loads(result.companion_path.read_text(encoding="utf-8"))
    defs = companion.get("$defs", {})
    assert "entry" not in defs


def test_stamp_document_shape_has_no_narrowed_ref(tmp_path: Path) -> None:
    """`--no-namespace` companion does not stamp a `<name>_ref` $defs entry."""
    _stamp_empty_capability(tmp_path)
    result = stamp_new_schema(
        tmp_path, capability="demo", name="trip", no_namespace=True
    )
    companion = json.loads(result.companion_path.read_text(encoding="utf-8"))
    defs = companion.get("$defs", {})
    assert "trip_ref" not in defs


def test_stamp_document_shape_validates_clean(tmp_path: Path) -> None:
    """The stamped document pair validates clean via the full validator."""
    _stamp_empty_capability(tmp_path)
    stamp_new_schema(tmp_path, capability="demo", name="trip", no_namespace=True)
    from project_kit.schemas_validate import validate_all

    report = validate_all(tmp_path)
    assert report.is_clean, report.issues


def test_stamp_document_shape_refuses_when_exists(tmp_path: Path) -> None:
    """`--no-namespace` respects existence check just like the namespace path."""
    _stamp_empty_capability(tmp_path)
    stamp_new_schema(tmp_path, capability="demo", name="trip", no_namespace=True)
    with pytest.raises(SchemaAuthoringError, match="already exists"):
        stamp_new_schema(tmp_path, capability="demo", name="trip", no_namespace=True)


def test_stamp_document_shape_refuses_non_kebab_name(tmp_path: Path) -> None:
    """`--no-namespace` still validates kebab-case on the schema name."""
    _stamp_empty_capability(tmp_path)
    with pytest.raises(SchemaAuthoringError, match="must be kebab-case"):
        stamp_new_schema(
            tmp_path, capability="demo", name="Bad_Name", no_namespace=True
        )


def test_stamp_namespace_owner_path_unchanged(tmp_path: Path) -> None:
    """Regression: the default (namespace-owner) stamp still produces the same shape."""
    _stamp_empty_capability(tmp_path)
    result = stamp_new_schema(
        tmp_path, capability="demo", name="kinds", collection_name="types"
    )
    yaml_text = result.yaml_path.read_text(encoding="utf-8")
    # Namespace-owner YAML still carries the collection.
    assert "types: {}" in yaml_text
    companion = json.loads(result.companion_path.read_text(encoding="utf-8"))
    # Namespace-owner companion still carries the annotation + entry shape.
    assert companion["x-pkit-id-collection"] == "/types"
    assert "patternProperties" in companion["properties"]["types"]
    assert "entry" in companion["$defs"]


# CLI: pkit new schema --------------------------------------------------


def test_cli_new_schema_default(tmp_path: Path) -> None:
    _stamp_empty_capability(tmp_path)
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        import shutil

        shutil.copytree(tmp_path / ".pkit", Path.cwd() / ".pkit", dirs_exist_ok=True)
        result = runner.invoke(main, ["new", "schema", "demo", "fresh-schema"])
    assert result.exit_code == 0, result.output
    assert "Stamped:" in result.output
    assert "fresh-schema.yaml" in result.output
    assert "fresh-schema.schema.json" in result.output


def test_cli_new_schema_list_form(tmp_path: Path) -> None:
    _stamp_empty_capability(tmp_path)
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        import shutil

        shutil.copytree(tmp_path / ".pkit", Path.cwd() / ".pkit", dirs_exist_ok=True)
        result = runner.invoke(
            main,
            [
                "new",
                "schema",
                "demo",
                "fresh-list",
                "--collection-form",
                "list",
                "--collection-name",
                "items",
            ],
        )
    assert result.exit_code == 0, result.output


def test_cli_new_schema_refuses_existing(tmp_path: Path) -> None:
    _stamp_empty_capability(tmp_path)
    stamp_new_schema(tmp_path, capability="demo", name="taken")
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        import shutil

        shutil.copytree(tmp_path / ".pkit", Path.cwd() / ".pkit", dirs_exist_ok=True)
        result = runner.invoke(main, ["new", "schema", "demo", "taken"])
    assert result.exit_code != 0
    assert "already exists" in result.output


def test_cli_new_schema_no_namespace(tmp_path: Path) -> None:
    """`pkit new schema ... --no-namespace` stamps the document shape."""
    _stamp_empty_capability(tmp_path)
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        import shutil

        shutil.copytree(tmp_path / ".pkit", Path.cwd() / ".pkit", dirs_exist_ok=True)
        result = runner.invoke(
            main, ["new", "schema", "demo", "trip", "--no-namespace"]
        )
        assert result.exit_code == 0, result.output
        assert "Stamped:" in result.output
        # Confirm the stamped companion is document-shaped.
        companion = json.loads(
            (Path.cwd() / ".pkit/capabilities/demo/schemas/trip.schema.json").read_text(
                encoding="utf-8"
            )
        )
        assert "x-pkit-id-collection" not in companion


# rename_entry ----------------------------------------------------------


def _setup_namespace_with_consumer(tmp_path: Path) -> dict[str, Path]:
    """Stamp a namespace owner + a consumer that references it via tokens and annotation keys."""
    schemas = tmp_path / ".pkit" / "capabilities" / "demo" / "schemas"
    schemas.mkdir(parents=True)
    # Owner: namespace `kinds`, mapping form with `types:` collection.
    (schemas / "kinds.yaml").write_text(
        "schema_version: 1\n"
        "types:\n"
        "  task:\n"
        "    role: Unit of work.\n"
        "  feature:\n"
        "    role: A capability.\n",
        encoding="utf-8",
    )
    (schemas / "kinds.schema.json").write_text(
        json.dumps(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "$id": "kinds.schema.json",
                "x-pkit-id-collection": "/types",
                "type": "object",
                "required": ["schema_version", "types"],
                "additionalProperties": False,
                "properties": {
                    "schema_version": {"type": "integer", "const": 1},
                    "types": {
                        "type": "object",
                        "patternProperties": {
                            "^[a-z][a-z0-9-]*$": {
                                "type": "object",
                                "required": ["role"],
                                "additionalProperties": False,
                                "properties": {"role": {"type": "string", "minLength": 1}},
                            },
                        },
                        "additionalProperties": False,
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    # Consumer 1: token reference in a value.
    (schemas / "rules.yaml").write_text(
        "schema_version: 1\n"
        "applies_to: [\"[kinds:feature]\", \"[kinds:task]\"]\n",
        encoding="utf-8",
    )
    (schemas / "rules.schema.json").write_text(
        json.dumps(
            {
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
                            "pattern": r"^\[kinds:[a-z][a-z0-9-]*\]$",
                        },
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    # Consumer 2: annotation-based mapping keys.
    (schemas / "per-kind.yaml").write_text(
        "schema_version: 1\n"
        "by_kind:\n"
        "  task:\n"
        "    note: t\n"
        "  feature:\n"
        "    note: f\n",
        encoding="utf-8",
    )
    (schemas / "per-kind.schema.json").write_text(
        json.dumps(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "required": ["schema_version", "by_kind"],
                "additionalProperties": False,
                "properties": {
                    "schema_version": {"type": "integer", "const": 1},
                    "by_kind": {
                        "type": "object",
                        "x-pkit-keys-from-namespace": "kinds",
                        "patternProperties": {
                            "^[a-z][a-z0-9-]*$": {
                                "type": "object",
                                "required": ["note"],
                                "additionalProperties": False,
                                "properties": {"note": {"type": "string"}},
                            },
                        },
                        "additionalProperties": False,
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    return {
        "owner": schemas / "kinds.yaml",
        "rules": schemas / "rules.yaml",
        "per_kind": schemas / "per-kind.yaml",
    }


def test_rename_updates_owner_token_and_annotation_key(tmp_path: Path) -> None:
    paths = _setup_namespace_with_consumer(tmp_path)
    result = rename_entry(tmp_path, "kinds", "feature", "capability")
    assert isinstance(result, RenameResult)

    kinds_text = paths["owner"].read_text(encoding="utf-8")
    assert "capability:" in kinds_text
    assert "feature:" not in kinds_text

    rules_text = paths["rules"].read_text(encoding="utf-8")
    assert "[kinds:capability]" in rules_text
    assert "[kinds:feature]" not in rules_text

    per_kind_text = paths["per_kind"].read_text(encoding="utf-8")
    assert "capability:" in per_kind_text
    assert "  feature:\n" not in per_kind_text


def test_rename_returns_change_breakdown(tmp_path: Path) -> None:
    _setup_namespace_with_consumer(tmp_path)
    result = rename_entry(tmp_path, "kinds", "feature", "capability")
    kinds = {c.kind for c in result.changes}
    assert kinds == {"owner-key", "token", "annotation-key"}


def test_rename_list_form_owner(tmp_path: Path) -> None:
    schemas = tmp_path / ".pkit" / "capabilities" / "demo" / "schemas"
    schemas.mkdir(parents=True)
    (schemas / "items.yaml").write_text(
        "schema_version: 1\nitems:\n  - id: alpha\n    label: A\n  - id: beta\n    label: B\n",
        encoding="utf-8",
    )
    (schemas / "items.schema.json").write_text(
        json.dumps(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "x-pkit-id-collection": "/items",
                "type": "object",
                "required": ["schema_version", "items"],
                "additionalProperties": False,
                "properties": {
                    "schema_version": {"type": "integer", "const": 1},
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["id", "label"],
                            "additionalProperties": False,
                            "properties": {
                                "id": {"type": "string", "pattern": "^[a-z][a-z0-9-]*$"},
                                "label": {"type": "string"},
                            },
                        },
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    rename_entry(tmp_path, "items", "beta", "gamma")
    text = (schemas / "items.yaml").read_text(encoding="utf-8")
    assert "id: gamma" in text
    assert "id: beta" not in text


def test_rename_refuses_non_kebab_new_id(tmp_path: Path) -> None:
    _setup_namespace_with_consumer(tmp_path)
    with pytest.raises(SchemaAuthoringError, match="must be kebab-case"):
        rename_entry(tmp_path, "kinds", "feature", "BadName")


def test_rename_refuses_same_id(tmp_path: Path) -> None:
    _setup_namespace_with_consumer(tmp_path)
    with pytest.raises(SchemaAuthoringError, match="nothing to rename"):
        rename_entry(tmp_path, "kinds", "feature", "feature")


def test_rename_refuses_unknown_namespace(tmp_path: Path) -> None:
    with pytest.raises(SchemaAuthoringError, match="namespace 'nope'"):
        rename_entry(tmp_path, "nope", "a", "b")


def test_rename_refuses_unknown_old_id(tmp_path: Path) -> None:
    _setup_namespace_with_consumer(tmp_path)
    with pytest.raises(SchemaAuthoringError, match="'bogus' not found"):
        rename_entry(tmp_path, "kinds", "bogus", "newid")


def test_rename_refuses_new_id_collision(tmp_path: Path) -> None:
    paths = _setup_namespace_with_consumer(tmp_path)
    original = paths["owner"].read_text(encoding="utf-8")
    with pytest.raises(SchemaAuthoringError, match="already exists in namespace"):
        rename_entry(tmp_path, "kinds", "feature", "task")
    # Rolled back.
    assert paths["owner"].read_text(encoding="utf-8") == original


def test_rename_rolls_back_on_collision_in_annotation_keys(tmp_path: Path) -> None:
    """Annotation-key collision in a consumer rolls back even the owner change."""
    paths = _setup_namespace_with_consumer(tmp_path)
    # Add a collision: per-kind already has both `task` and `feature`; if
    # we ask to rename feature → task, the collision lives in BOTH the
    # owner AND the per-kind annotation-key — the owner collision fires
    # first. Setup a case where ONLY per-kind has the collision: rename
    # `feature` in owner to a new id `x`; then make per-kind have a
    # pre-existing `x` key. Easier: rename to an id that exists ONLY in
    # per-kind, not in owner.
    # Add a "task2" entry only to per-kind, rename feature → task2.
    per_kind_text = paths["per_kind"].read_text(encoding="utf-8")
    paths["per_kind"].write_text(
        per_kind_text + "  task2:\n    note: t2\n", encoding="utf-8"
    )
    # Now per-kind has task, feature, task2. owner still has task, feature.
    # Try to rename feature → task2 in kinds: owner has no collision (task2
    # isn't in owner), but per-kind does (task2 is already present).
    owner_original = paths["owner"].read_text(encoding="utf-8")
    with pytest.raises(SchemaAuthoringError):
        rename_entry(tmp_path, "kinds", "feature", "task2")
    # Owner should be restored.
    assert paths["owner"].read_text(encoding="utf-8") == owner_original


# CLI -------------------------------------------------------------------


def test_cli_schemas_rename(tmp_path: Path) -> None:
    _setup_namespace_with_consumer(tmp_path)
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        import shutil

        shutil.copytree(tmp_path / ".pkit", Path.cwd() / ".pkit", dirs_exist_ok=True)
        result = runner.invoke(
            main, ["schemas", "rename", "kinds", "feature", "capability"]
        )
    assert result.exit_code == 0, result.output
    assert "Renamed 'feature'" in result.output
    assert "[owner-key]" in result.output
    assert "[token]" in result.output
    assert "[annotation-key]" in result.output


def test_cli_schemas_rename_unknown_namespace_errors(tmp_path: Path) -> None:
    _setup_namespace_with_consumer(tmp_path)
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path):
        import shutil

        shutil.copytree(tmp_path / ".pkit", Path.cwd() / ".pkit", dirs_exist_ok=True)
        result = runner.invoke(main, ["schemas", "rename", "nope", "a", "b"])
    assert result.exit_code != 0
    assert "not found" in result.output
