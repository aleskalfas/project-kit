"""Tests for adopter-data validation (per COR-023).

Covers:
- Binding resolution via the `pkit_schema:` field (field-first).
- Binding resolution via per-schema `binds_to:` (fallback).
- "No binding" structured error when neither matches.
- Schema-version mismatch refuses with a migration hint.
- Successful shape validation against a sample data file + schema.
- Real shipped `evidence:evidence-record` schema binds + validates
  adopter `evidence.yaml` files.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from project_kit import data_validate as dv
from project_kit.cli import main
from project_kit.manifest import (
    BackboneManifest,
    ComponentRegistryEntry,
    read_backbone_manifest,
    write_backbone_manifest,
)

REPO_ROOT = Path(__file__).resolve().parent.parent

# --- fixtures --------------------------------------------------------


@pytest.fixture
def kit_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A bare adopter project with `.pkit/` + a backbone manifest."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".pkit").mkdir()
    write_backbone_manifest(
        tmp_path, BackboneManifest(backbone_version="1.28.0", components=[])
    )
    return tmp_path


def _stage_capability_schema(
    target_root: Path,
    capability: str,
    schema_name: str,
    *,
    schema_version: int = 1,
    properties: dict[str, dict] | None = None,
    required: list[str] | None = None,
    binds_to: list[str] | None = None,
) -> tuple[Path, Path]:
    """Stage a capability + a schema pair inside the adopter project.

    Registers the capability in the backbone manifest so the resolver
    sees it as installed. The schema YAML carries the optional
    `binds_to:` field when patterns are supplied (per COR-023).
    """
    cap_dir = target_root / ".pkit" / "capabilities" / capability
    schemas_dir = cap_dir / "schemas"
    schemas_dir.mkdir(parents=True, exist_ok=True)

    (cap_dir / "package.yaml").write_text(
        f"""schema_version: 1
component:
  kind: capability
  name: {capability}
  version: 0.1.0
description: Test capability.
requires_backbone: ">=0.1.0,<99.0.0"
""",
        encoding="utf-8",
    )

    yaml_path = schemas_dir / f"{schema_name}.yaml"
    yaml_lines = [f"schema_version: {schema_version}"]
    if binds_to:
        yaml_lines.append("binds_to:")
        for glob in binds_to:
            yaml_lines.append(f'  - "{glob}"')
    yaml_lines.append("entries: {}")
    yaml_path.write_text("\n".join(yaml_lines) + "\n", encoding="utf-8")

    companion = schemas_dir / f"{schema_name}.schema.json"
    schema_doc: dict = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"{schema_name}.schema.json",
        "type": "object",
        "additionalProperties": True,
        "required": ["schema_version", *(required or [])],
        "properties": {
            "schema_version": {"type": "integer", "const": schema_version},
            "pkit_schema": {"type": "string"},
            **(properties or {}),
        },
    }
    companion.write_text(json.dumps(schema_doc, indent=2), encoding="utf-8")

    # Register the capability in the backbone manifest.
    from project_kit.manifest import read_backbone_manifest

    bb = read_backbone_manifest(target_root)
    assert bb is not None
    entry = ComponentRegistryEntry(
        kind="capability",
        name=capability,
        manifest=f".pkit/capabilities/{capability}/package.yaml",
    )
    if entry not in bb.components:
        bb.components.append(entry)
    write_backbone_manifest(target_root, bb)
    return yaml_path, companion


# --- binding resolution: field-first ----------------------------------


def test_resolve_binding_via_field(kit_target: Path) -> None:
    _stage_capability_schema(kit_target, "trip-planning", "trip")
    data_path = kit_target / "trips" / "japan-2026" / "trip.yaml"
    data_path.parent.mkdir(parents=True)
    data_path.write_text(
        "pkit_schema: trip-planning:trip\nschema_version: 1\ntitle: Japan\n",
        encoding="utf-8",
    )
    result = dv.resolve_binding(data_path, kit_target)
    assert isinstance(result, dv.ResolvedBinding)
    assert result.capability == "trip-planning"
    assert result.schema_name == "trip"
    assert result.source == "field"


def test_resolve_binding_field_wins_over_capability_binding(kit_target: Path) -> None:
    """When both field and capability binding could apply, field is authoritative."""
    _stage_capability_schema(kit_target, "trip-planning", "trip")
    _stage_capability_schema(
        kit_target, "trip-planning", "transport", binds_to=["trips/*/*.yaml"]
    )
    data_path = kit_target / "trips" / "japan-2026" / "trip.yaml"
    data_path.parent.mkdir(parents=True)
    data_path.write_text(
        "pkit_schema: trip-planning:trip\nschema_version: 1\n",
        encoding="utf-8",
    )
    result = dv.resolve_binding(data_path, kit_target)
    assert isinstance(result, dv.ResolvedBinding)
    assert result.schema_name == "trip"
    assert result.source == "field"


def test_resolve_binding_rejects_malformed_field(kit_target: Path) -> None:
    _stage_capability_schema(kit_target, "trip-planning", "trip")
    data_path = kit_target / "trip.yaml"
    data_path.write_text("pkit_schema: not-a-pair\nschema_version: 1\n", encoding="utf-8")
    result = dv.resolve_binding(data_path, kit_target)
    assert isinstance(result, dv.BindingError)
    assert "<capability>:<schema>" in result.message


def test_resolve_binding_rejects_non_string_field(kit_target: Path) -> None:
    _stage_capability_schema(kit_target, "trip-planning", "trip")
    data_path = kit_target / "trip.yaml"
    data_path.write_text("pkit_schema: 42\nschema_version: 1\n", encoding="utf-8")
    result = dv.resolve_binding(data_path, kit_target)
    assert isinstance(result, dv.BindingError)
    assert "must be a string" in result.message


def test_resolve_binding_field_with_unknown_capability(kit_target: Path) -> None:
    data_path = kit_target / "data.yaml"
    data_path.write_text(
        "pkit_schema: missing-cap:thing\nschema_version: 1\n", encoding="utf-8"
    )
    result = dv.resolve_binding(data_path, kit_target)
    assert isinstance(result, dv.BindingError)
    assert "missing-cap" in result.message
    assert "not installed" in result.message


def test_resolve_binding_field_with_unknown_schema_in_capability(kit_target: Path) -> None:
    _stage_capability_schema(kit_target, "trip-planning", "trip")
    data_path = kit_target / "data.yaml"
    data_path.write_text(
        "pkit_schema: trip-planning:nope\nschema_version: 1\n", encoding="utf-8"
    )
    result = dv.resolve_binding(data_path, kit_target)
    assert isinstance(result, dv.BindingError)
    assert "trip-planning" in result.message
    assert "nope" in result.message


# --- binding resolution: capability fallback --------------------------


def test_resolve_binding_via_capability_glob(kit_target: Path) -> None:
    _stage_capability_schema(
        kit_target, "trip-planning", "trip", binds_to=["trips/*/trip.yaml"]
    )
    data_path = kit_target / "trips" / "japan-2026" / "trip.yaml"
    data_path.parent.mkdir(parents=True)
    data_path.write_text("schema_version: 1\ntitle: Japan\n", encoding="utf-8")
    result = dv.resolve_binding(data_path, kit_target)
    assert isinstance(result, dv.ResolvedBinding)
    assert result.capability == "trip-planning"
    assert result.schema_name == "trip"
    assert result.source == "capability-binding"


def test_resolve_binding_capability_glob_does_not_match(kit_target: Path) -> None:
    _stage_capability_schema(
        kit_target, "trip-planning", "trip", binds_to=["trips/*/trip.yaml"]
    )
    data_path = kit_target / "elsewhere" / "thing.yaml"
    data_path.parent.mkdir(parents=True)
    data_path.write_text("schema_version: 1\n", encoding="utf-8")
    result = dv.resolve_binding(data_path, kit_target)
    assert isinstance(result, dv.BindingError)
    assert "no schema binding found" in result.message
    assert "pkit_schema" in result.message


def test_resolve_binding_ambiguous_across_capabilities(kit_target: Path) -> None:
    """Two capabilities with overlapping bindings → ambiguous; refuse and hint at the field."""
    _stage_capability_schema(
        kit_target, "cap-a", "shared", binds_to=["shared/*.yaml"]
    )
    _stage_capability_schema(
        kit_target, "cap-b", "shared", binds_to=["shared/*.yaml"]
    )
    data_path = kit_target / "shared" / "file.yaml"
    data_path.parent.mkdir(parents=True)
    data_path.write_text("schema_version: 1\n", encoding="utf-8")
    result = dv.resolve_binding(data_path, kit_target)
    assert isinstance(result, dv.BindingError)
    assert "ambiguous" in result.message
    assert "cap-a" in result.message and "cap-b" in result.message


def test_resolve_binding_schema_without_binds_to_does_not_match(kit_target: Path) -> None:
    """A capability schema with no `binds_to:` contributes no fallback patterns."""
    _stage_capability_schema(kit_target, "trip-planning", "trip")  # no binds_to
    data_path = kit_target / "trips" / "japan-2026" / "trip.yaml"
    data_path.parent.mkdir(parents=True)
    data_path.write_text("schema_version: 1\n", encoding="utf-8")
    result = dv.resolve_binding(data_path, kit_target)
    assert isinstance(result, dv.BindingError)
    assert "no schema binding found" in result.message


def test_resolve_binding_supports_multiple_globs_per_schema(kit_target: Path) -> None:
    """A schema can declare multiple `binds_to:` glob entries."""
    _stage_capability_schema(
        kit_target,
        "trip-planning",
        "trip",
        binds_to=["trips/*/trip.yaml", "drafts/trip-*.yaml"],
    )
    file_a = kit_target / "trips" / "japan-2026" / "trip.yaml"
    file_a.parent.mkdir(parents=True)
    file_a.write_text("schema_version: 1\n", encoding="utf-8")
    file_b = kit_target / "drafts" / "trip-iceland.yaml"
    file_b.parent.mkdir(parents=True)
    file_b.write_text("schema_version: 1\n", encoding="utf-8")
    res_a = dv.resolve_binding(file_a, kit_target)
    res_b = dv.resolve_binding(file_b, kit_target)
    assert isinstance(res_a, dv.ResolvedBinding) and res_a.source == "capability-binding"
    assert isinstance(res_b, dv.ResolvedBinding) and res_b.source == "capability-binding"


# --- schema-version mismatch ------------------------------------------


def test_schema_version_mismatch_refuses(kit_target: Path) -> None:
    """Data declares schema_version 1; capability schema is at 2 — refuse with hint."""
    _stage_capability_schema(kit_target, "trip-planning", "trip", schema_version=2)
    data_path = kit_target / "trip.yaml"
    data_path.write_text(
        "pkit_schema: trip-planning:trip\nschema_version: 1\n", encoding="utf-8"
    )
    issues = dv.validate_data_file(data_path, kit_target)
    assert len(issues) == 1
    msg = issues[0].message
    assert "schema_version mismatch" in msg
    assert "1" in msg and "2" in msg
    assert "Auto-migration is not supported" in msg
    assert "COR-023" in msg


# --- happy-path shape validation --------------------------------------


def test_successful_shape_validation(kit_target: Path) -> None:
    _stage_capability_schema(
        kit_target,
        "trip-planning",
        "trip",
        properties={"title": {"type": "string"}, "slug": {"type": "string"}},
        required=["title", "slug"],
    )
    data_path = kit_target / "trip.yaml"
    data_path.write_text(
        "pkit_schema: trip-planning:trip\nschema_version: 1\nslug: japan-2026\ntitle: Japan\n",
        encoding="utf-8",
    )
    issues = dv.validate_data_file(data_path, kit_target)
    assert issues == []


def test_shape_failure_surfaces_field_error(kit_target: Path) -> None:
    _stage_capability_schema(
        kit_target,
        "trip-planning",
        "trip",
        properties={"title": {"type": "string"}, "slug": {"type": "string"}},
        required=["title", "slug"],
    )
    data_path = kit_target / "trip.yaml"
    data_path.write_text(
        "pkit_schema: trip-planning:trip\nschema_version: 1\nslug: japan-2026\n",
        encoding="utf-8",
    )
    issues = dv.validate_data_file(data_path, kit_target)
    assert len(issues) >= 1
    # jsonschema reports a missing required field.
    assert any("'title'" in i.message for i in issues)


def test_validate_path_walks_directory(kit_target: Path) -> None:
    _stage_capability_schema(
        kit_target,
        "trip-planning",
        "trip",
        properties={"title": {"type": "string"}},
        required=["title"],
    )
    # Add the binds_to to the staged schema (re-write the schema YAML).
    schema_yaml = kit_target / ".pkit" / "capabilities" / "trip-planning" / "schemas" / "trip.yaml"
    schema_yaml.write_text(
        'schema_version: 1\nbinds_to:\n  - "trips/*/trip.yaml"\nentries: {}\n',
        encoding="utf-8",
    )
    (kit_target / "trips" / "japan-2026").mkdir(parents=True)
    (kit_target / "trips" / "japan-2026" / "trip.yaml").write_text(
        "schema_version: 1\ntitle: Japan\n", encoding="utf-8"
    )
    (kit_target / "trips" / "iceland-2027").mkdir(parents=True)
    (kit_target / "trips" / "iceland-2027" / "trip.yaml").write_text(
        "schema_version: 1\ntitle: Iceland\n", encoding="utf-8"
    )
    report = dv.validate_path(kit_target / "trips", kit_target)
    assert report.files_checked == 2
    assert report.is_clean


def test_validate_path_excludes_pkit_subtree(kit_target: Path) -> None:
    """Files under `.pkit/` are kit-managed, not adopter data — skip them."""
    _stage_capability_schema(
        kit_target,
        "trip-planning",
        "trip",
        properties={"title": {"type": "string"}},
        required=["title"],
    )
    report = dv.validate_path(kit_target, kit_target)
    # Should find zero files — everything under .pkit/ is excluded; no other
    # adopter YAMLs were created in this fixture.
    assert report.files_checked == 0


# --- CLI surface ------------------------------------------------------


def test_cli_data_validate_clean(kit_target: Path) -> None:
    _stage_capability_schema(
        kit_target,
        "trip-planning",
        "trip",
        properties={"title": {"type": "string"}},
        required=["title"],
    )
    data_path = kit_target / "trip.yaml"
    data_path.write_text(
        "pkit_schema: trip-planning:trip\nschema_version: 1\ntitle: Japan\n",
        encoding="utf-8",
    )
    result = CliRunner().invoke(main, ["data", "validate", str(data_path)])
    assert result.exit_code == 0, result.output
    assert "All checks passed" in result.output


def test_cli_data_validate_failure(kit_target: Path) -> None:
    _stage_capability_schema(
        kit_target,
        "trip-planning",
        "trip",
        properties={"title": {"type": "string"}},
        required=["title"],
    )
    data_path = kit_target / "trip.yaml"
    data_path.write_text(
        "pkit_schema: trip-planning:trip\nschema_version: 1\n", encoding="utf-8"
    )
    result = CliRunner().invoke(main, ["data", "validate", str(data_path)])
    assert result.exit_code != 0
    assert "error(s)" in result.output


# --- real shipped evidence:evidence-record schema ---------------------
#
# These tests exercise the actual shipped schema pair from
# `.pkit/capabilities/evidence/schemas/` rather than a synthetic
# fixture. They guard the contract adopters rely on.


def _install_evidence_capability(target_root: Path) -> None:
    """Copy the real shipped evidence capability into an adopter fixture.

    Mirrors what `pkit sync` would land. Brings the `package.yaml`,
    the `schemas/evidence-record.{yaml,schema.json}` pair, and
    registers the capability in the backbone manifest.
    """
    src = REPO_ROOT / ".pkit" / "capabilities" / "evidence"
    dst = target_root / ".pkit" / "capabilities" / "evidence"
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copy(src / "package.yaml", dst / "package.yaml")
    schemas_src = src / "schemas"
    schemas_dst = dst / "schemas"
    schemas_dst.mkdir(exist_ok=True)
    for schema_file in schemas_src.iterdir():
        if schema_file.is_file():
            shutil.copy(schema_file, schemas_dst / schema_file.name)
    bb = read_backbone_manifest(target_root)
    assert bb is not None
    entry = ComponentRegistryEntry(
        kind="capability",
        name="evidence",
        manifest=".pkit/capabilities/evidence/package.yaml",
    )
    if entry not in bb.components:
        bb.components.append(entry)
    write_backbone_manifest(target_root, bb)


_WELL_FORMED_EVIDENCE_YAML = """\
schema_version: 1
records:
  - id: cre26-title
    source_url: https://cre26.tokyo/
    fetched_at: 2026-05-18
    excerpt: |
      Current Research in Egyptology 26
    title: CRE 26 Tokyo — conference title
    note: Full name of the conference.
  - id: api-rate-limit
    source_url: https://docs.example.com/api/limits
    fetched_at: 2026-05-17T14:32:00
    excerpt: |
      Each authenticated client may issue up to 1,000 requests per hour.
"""


def test_evidence_record_binds_root_evidence_yaml(kit_target: Path) -> None:
    """`binds_to: ["evidence.yaml", ...]` catches a root-level adopter file."""
    _install_evidence_capability(kit_target)
    data_path = kit_target / "evidence.yaml"
    data_path.write_text(_WELL_FORMED_EVIDENCE_YAML, encoding="utf-8")
    result = dv.resolve_binding(data_path, kit_target)
    assert isinstance(result, dv.ResolvedBinding), getattr(result, "message", "")
    assert result.capability == "evidence"
    assert result.schema_name == "evidence-record"
    assert result.source == "capability-binding"


def test_evidence_record_binds_one_deep_evidence_yaml(kit_target: Path) -> None:
    """`binds_to: [..., "*/evidence.yaml"]` catches a one-deep adopter file."""
    _install_evidence_capability(kit_target)
    data_path = kit_target / "trips" / "evidence.yaml"
    data_path.parent.mkdir(parents=True)
    data_path.write_text(_WELL_FORMED_EVIDENCE_YAML, encoding="utf-8")
    result = dv.resolve_binding(data_path, kit_target)
    assert isinstance(result, dv.ResolvedBinding), getattr(result, "message", "")
    assert result.schema_name == "evidence-record"
    assert result.source == "capability-binding"


def test_evidence_record_validates_well_formed_yaml(kit_target: Path) -> None:
    """A real-shape adopter `evidence.yaml` passes shape validation cleanly."""
    _install_evidence_capability(kit_target)
    data_path = kit_target / "evidence.yaml"
    data_path.write_text(_WELL_FORMED_EVIDENCE_YAML, encoding="utf-8")
    issues = dv.validate_data_file(data_path, kit_target)
    assert issues == [], [i.message for i in issues]


def test_evidence_record_missing_required_field(kit_target: Path) -> None:
    """A record missing `fetched_at` surfaces a clear shape finding."""
    _install_evidence_capability(kit_target)
    data_path = kit_target / "evidence.yaml"
    data_path.write_text(
        """\
schema_version: 1
records:
  - id: api-rate-limit
    source_url: https://docs.example.com
    excerpt: |
      Some excerpt.
""",
        encoding="utf-8",
    )
    issues = dv.validate_data_file(data_path, kit_target)
    assert len(issues) >= 1
    assert any("fetched_at" in i.message for i in issues)


def test_evidence_record_bad_id_pattern(kit_target: Path) -> None:
    """An id violating the kebab-case pattern surfaces a finding."""
    _install_evidence_capability(kit_target)
    data_path = kit_target / "evidence.yaml"
    data_path.write_text(
        """\
schema_version: 1
records:
  - id: NotKebabCase
    source_url: https://example.com
    fetched_at: 2026-05-18
    excerpt: |
      Some excerpt.
""",
        encoding="utf-8",
    )
    issues = dv.validate_data_file(data_path, kit_target)
    assert len(issues) >= 1
    assert any(
        "NotKebabCase" in i.message or "pattern" in i.message for i in issues
    )


def test_evidence_record_rejects_additional_field(kit_target: Path) -> None:
    """An unexpected field on a record is rejected by additionalProperties: false."""
    _install_evidence_capability(kit_target)
    data_path = kit_target / "evidence.yaml"
    data_path.write_text(
        """\
schema_version: 1
records:
  - id: api-rate-limit
    source_url: https://example.com
    fetched_at: 2026-05-18
    excerpt: |
      Some excerpt.
    surprise: not-allowed
""",
        encoding="utf-8",
    )
    issues = dv.validate_data_file(data_path, kit_target)
    assert len(issues) >= 1
    assert any(
        "surprise" in i.message or "additional" in i.message.lower() for i in issues
    )


def test_evidence_record_accepts_iso_timestamp(kit_target: Path) -> None:
    """`fetched_at` accepts both date-only and ISO 8601 timestamp forms."""
    _install_evidence_capability(kit_target)
    data_path = kit_target / "evidence.yaml"
    data_path.write_text(
        """\
schema_version: 1
records:
  - id: with-date
    source_url: https://example.com
    fetched_at: 2026-05-18
    excerpt: |
      Date-only.
  - id: with-timestamp-minute
    source_url: https://example.com
    fetched_at: 2026-05-18T14:32
    excerpt: |
      Timestamp minute-precision.
  - id: with-timestamp-second
    source_url: https://example.com
    fetched_at: 2026-05-18T14:32:00
    excerpt: |
      Timestamp second-precision.
""",
        encoding="utf-8",
    )
    issues = dv.validate_data_file(data_path, kit_target)
    assert issues == [], [i.message for i in issues]


def test_evidence_record_rejects_malformed_fetched_at(kit_target: Path) -> None:
    """A non-ISO `fetched_at` string is rejected by the pattern."""
    _install_evidence_capability(kit_target)
    data_path = kit_target / "evidence.yaml"
    data_path.write_text(
        """\
schema_version: 1
records:
  - id: bad-date
    source_url: https://example.com
    fetched_at: yesterday
    excerpt: |
      Bad date format.
""",
        encoding="utf-8",
    )
    issues = dv.validate_data_file(data_path, kit_target)
    assert len(issues) >= 1
    assert any(
        "yesterday" in i.message or "pattern" in i.message for i in issues
    )


def test_evidence_record_schema_self_validates(kit_target: Path) -> None:
    """The schema's own YAML (with `binds_to:`) parses clean against its companion."""
    _install_evidence_capability(kit_target)
    # The capability-side YAML carries `pkit_schema:` of its own type? No —
    # it carries `binds_to:` but is itself a schema-side file, not adopter
    # data. We verify the JSON Schema accepts the shape `{schema_version,
    # binds_to, records: []}` so the capability schema YAML is self-
    # consistent with its companion.
    src_yaml = kit_target / ".pkit" / "capabilities" / "evidence" / "schemas" / "evidence-record.yaml"
    companion = kit_target / ".pkit" / "capabilities" / "evidence" / "schemas" / "evidence-record.schema.json"
    raw = dv._yaml.load(src_yaml.read_text(encoding="utf-8"))
    schema_doc = json.loads(companion.read_text(encoding="utf-8"))
    from jsonschema import Draft202012Validator

    errors = list(Draft202012Validator(schema_doc).iter_errors(raw))
    assert errors == [], [e.message for e in errors]


def test_cli_data_validate_evidence_yaml_clean(kit_target: Path) -> None:
    """The CLI walks an adopter dir containing `evidence.yaml` and exits 0."""
    _install_evidence_capability(kit_target)
    scope = kit_target / "trips" / "japan-2026"
    scope.mkdir(parents=True)
    (scope / "evidence.yaml").write_text(_WELL_FORMED_EVIDENCE_YAML, encoding="utf-8")
    result = CliRunner().invoke(main, ["data", "validate", str(scope)])
    assert result.exit_code == 0, result.output
    assert "All checks passed" in result.output


# --- cross-file reference resolution (per COR-029) --------------------
#
# Scope-subtree resolution: a `[<namespace>:<id>]` token at a field marked
# `x-pkit-reference-namespace` resolves against the union of in-scope files
# bound to that namespace. These tests walk the disconfirming-instance
# space: clean resolve, dangling id, duplicate id, out-of-scope (soft),
# scope isolation vs union, the position-gate, cross-file `$ref` into a
# `$defs`, wrong-namespace token, and `--shape-only`.

_DRAFT = "https://json-schema.org/draft/2020-12/schema"


def _stage_reference_capability(target_root: Path) -> None:
    """Stage a `trip-planning` capability: `transport` (namespace owner) + `trip` (citing).

    `transport` declares `x-pkit-id-collection: /transport` and a
    `$defs/transport_ref` carrying `x-pkit-reference-namespace: transport`;
    `trip`'s `transport[]` items `$ref` that definition cross-file.
    """
    cap = "trip-planning"
    schemas_dir = target_root / ".pkit" / "capabilities" / cap / "schemas"
    schemas_dir.mkdir(parents=True, exist_ok=True)
    (target_root / ".pkit" / "capabilities" / cap / "package.yaml").write_text(
        "schema_version: 1\n"
        "component:\n  kind: capability\n  name: trip-planning\n  version: 0.1.0\n"
        'description: Test capability.\nrequires_backbone: ">=0.1.0,<99.0.0"\n',
        encoding="utf-8",
    )

    (schemas_dir / "transport.yaml").write_text(
        'schema_version: 1\nbinds_to:\n  - "**/transport.yaml"\ntransport: {}\n',
        encoding="utf-8",
    )
    (schemas_dir / "transport.schema.json").write_text(
        json.dumps(
            {
                "$schema": _DRAFT,
                "$id": "transport.schema.json",
                "x-pkit-id-collection": "/transport",
                "type": "object",
                "additionalProperties": True,
                "required": ["schema_version"],
                "properties": {
                    "schema_version": {"type": "integer", "const": 1},
                    "pkit_schema": {"type": "string"},
                    "transport": {"type": "object"},
                },
                "$defs": {
                    "transport_ref": {
                        "type": "string",
                        "x-pkit-reference-namespace": "transport",
                    }
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    (schemas_dir / "trip.yaml").write_text(
        'schema_version: 1\nbinds_to:\n  - "**/trip.yaml"\nentries: {}\n',
        encoding="utf-8",
    )
    (schemas_dir / "trip.schema.json").write_text(
        json.dumps(
            {
                "$schema": _DRAFT,
                "$id": "trip.schema.json",
                "type": "object",
                "additionalProperties": True,
                "required": ["schema_version"],
                "properties": {
                    "schema_version": {"type": "integer", "const": 1},
                    "pkit_schema": {"type": "string"},
                    "title": {"type": "string"},
                    "note": {"type": "string"},
                    "transport": {
                        "type": "array",
                        "items": {"$ref": "transport.schema.json#/$defs/transport_ref"},
                    },
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    bb = read_backbone_manifest(target_root)
    assert bb is not None
    entry = ComponentRegistryEntry(
        kind="capability",
        name=cap,
        manifest=f".pkit/capabilities/{cap}/package.yaml",
    )
    if entry not in bb.components:
        bb.components.append(entry)
    write_backbone_manifest(target_root, bb)


def _transport_file(*ids: str) -> str:
    lines = ["pkit_schema: trip-planning:transport", "schema_version: 1", "transport:"]
    for i in ids:
        lines.append(f"  {i}:")
        lines.append(f"    carrier: {i}")
    return "\n".join(lines) + "\n"


def _trip_file(*tokens: str, note: str | None = None) -> str:
    lines = ["pkit_schema: trip-planning:trip", "schema_version: 1", "title: A trip"]
    if note is not None:
        lines.append(f"note: {note!r}")
    lines.append("transport:")
    for t in tokens:
        lines.append(f'  - "{t}"')
    return "\n".join(lines) + "\n"


def test_reference_resolves_clean(kit_target: Path) -> None:
    _stage_reference_capability(kit_target)
    scope = kit_target / "trips" / "japan"
    scope.mkdir(parents=True)
    (scope / "transport.yaml").write_text(_transport_file("asiana-fux5mv"), encoding="utf-8")
    (scope / "trip.yaml").write_text(_trip_file("[transport:asiana-fux5mv]"), encoding="utf-8")
    report = dv.validate_path(scope, kit_target)
    assert report.is_clean, report.issues


def test_reference_dangling_id_is_error(kit_target: Path) -> None:
    _stage_reference_capability(kit_target)
    scope = kit_target / "trips" / "japan"
    scope.mkdir(parents=True)
    (scope / "transport.yaml").write_text(_transport_file("asiana-fux5mv"), encoding="utf-8")
    (scope / "trip.yaml").write_text(_trip_file("[transport:does-not-exist]"), encoding="utf-8")
    report = dv.validate_path(scope, kit_target)
    assert report.has_errors
    assert any("does-not-exist" in i.message for i in report.errors)


def test_reference_duplicate_id_is_error(kit_target: Path) -> None:
    _stage_reference_capability(kit_target)
    scope = kit_target / "trips"
    (scope / "japan").mkdir(parents=True)
    (scope / "korea").mkdir(parents=True)
    # Same id defined in two in-scope transport files -> ambiguous pool.
    (scope / "japan" / "transport.yaml").write_text(_transport_file("dupe-id"), encoding="utf-8")
    (scope / "korea" / "transport.yaml").write_text(_transport_file("dupe-id"), encoding="utf-8")
    report = dv.validate_path(scope, kit_target)
    assert report.has_errors
    assert any("duplicate id" in i.message and "dupe-id" in i.message for i in report.errors)


def test_reference_out_of_scope_is_warning(kit_target: Path) -> None:
    _stage_reference_capability(kit_target)
    # transport.yaml lives OUTSIDE the validated subtree -> no bound file in
    # scope -> soft warning, not a failure.
    trips = kit_target / "trips"
    japan = trips / "japan"
    japan.mkdir(parents=True)
    (trips / "transport.yaml").write_text(_transport_file("asiana-fux5mv"), encoding="utf-8")
    (japan / "trip.yaml").write_text(_trip_file("[transport:asiana-fux5mv]"), encoding="utf-8")
    report = dv.validate_path(japan, kit_target)
    assert not report.has_errors
    assert report.warnings
    assert any("no file bound to namespace" in i.message for i in report.warnings)


def test_reference_scope_subtree_isolates_then_unions(kit_target: Path) -> None:
    _stage_reference_capability(kit_target)
    trips = kit_target / "trips"
    (trips / "japan").mkdir(parents=True)
    (trips / "korea").mkdir(parents=True)
    (trips / "japan" / "transport.yaml").write_text(_transport_file("jp-air"), encoding="utf-8")
    (trips / "korea" / "transport.yaml").write_text(_transport_file("kr-air"), encoding="utf-8")
    # Japan's trip references Korea's id.
    (trips / "japan" / "trip.yaml").write_text(_trip_file("[transport:kr-air]"), encoding="utf-8")

    # Validating only japan/: kr-air is out of scope -> dangling error.
    narrow = dv.validate_path(trips / "japan", kit_target)
    assert narrow.has_errors
    assert any("kr-air" in i.message for i in narrow.errors)

    # Validating trips/: both transport files union -> kr-air resolves.
    wide = dv.validate_path(trips, kit_target)
    assert not wide.has_errors, wide.issues


def test_reference_position_gate_ignores_nonreference_field(kit_target: Path) -> None:
    _stage_reference_capability(kit_target)
    scope = kit_target / "trips" / "japan"
    scope.mkdir(parents=True)
    (scope / "transport.yaml").write_text(_transport_file("asiana-fux5mv"), encoding="utf-8")
    # A token-shaped string in `note` (NOT reference-annotated) must be
    # ignored, even though its id would dangle.
    (scope / "trip.yaml").write_text(
        _trip_file("[transport:asiana-fux5mv]", note="[transport:not-a-real-ref]"),
        encoding="utf-8",
    )
    report = dv.validate_path(scope, kit_target)
    assert report.is_clean, report.issues


def test_reference_wrong_namespace_is_error(kit_target: Path) -> None:
    _stage_reference_capability(kit_target)
    scope = kit_target / "trips" / "japan"
    scope.mkdir(parents=True)
    (scope / "transport.yaml").write_text(_transport_file("asiana-fux5mv"), encoding="utf-8")
    (scope / "trip.yaml").write_text(_trip_file("[lodging:some-hotel]"), encoding="utf-8")
    report = dv.validate_path(scope, kit_target)
    assert report.has_errors
    assert any("namespace" in i.message and "lodging" in i.message for i in report.errors)


def test_reference_shape_only_skips_resolution(kit_target: Path) -> None:
    _stage_reference_capability(kit_target)
    scope = kit_target / "trips" / "japan"
    scope.mkdir(parents=True)
    (scope / "transport.yaml").write_text(_transport_file("asiana-fux5mv"), encoding="utf-8")
    (scope / "trip.yaml").write_text(_trip_file("[transport:does-not-exist]"), encoding="utf-8")
    report = dv.validate_path(scope, kit_target, resolve_references=False)
    assert report.is_clean, report.issues


def test_reference_cli_shape_only_flag(kit_target: Path) -> None:
    _stage_reference_capability(kit_target)
    scope = kit_target / "trips" / "japan"
    scope.mkdir(parents=True)
    (scope / "transport.yaml").write_text(_transport_file("asiana-fux5mv"), encoding="utf-8")
    (scope / "trip.yaml").write_text(_trip_file("[transport:does-not-exist]"), encoding="utf-8")
    # Default run fails on the dangling reference.
    fail = CliRunner().invoke(main, ["data", "validate", str(scope)])
    assert fail.exit_code != 0
    # --shape-only passes.
    ok = CliRunner().invoke(main, ["data", "validate", str(scope), "--shape-only"])
    assert ok.exit_code == 0, ok.output
