"""Tests for the manifest read/write layer (per COR-010 + PR-G of the build roadmap)."""

from __future__ import annotations

from pathlib import Path

import pytest

from project_kit.manifest import (
    ORIGIN_INCUBATED_IN_REPO,
    ORIGIN_KIT_SHIPPED,
    BackboneManifest,
    ComponentRegistryEntry,
    adapter_manifest_rel,
    capability_manifest_rel,
    read_backbone_manifest,
    read_capability_origin,
    read_component_manifest,
    record_adapter_version,
    record_backbone_target,
    record_completed_version,
    recorded_capability_manifest,
    set_capability_origin,
    set_component_manifest_path,
    set_state_line,
    write_backbone_manifest,
)


def test_read_returns_none_when_manifest_absent(tmp_path: Path) -> None:
    assert read_backbone_manifest(tmp_path) is None


def test_write_then_read_roundtrips_minimal_manifest(tmp_path: Path) -> None:
    (tmp_path / ".pkit").mkdir()
    write_backbone_manifest(tmp_path, BackboneManifest(backbone_version="0.9.0"))
    loaded = read_backbone_manifest(tmp_path)
    assert loaded is not None
    assert loaded.backbone_version == "0.9.0"
    assert loaded.schema_version == 1
    assert loaded.components == []


def test_write_then_read_roundtrips_with_components(tmp_path: Path) -> None:
    (tmp_path / ".pkit").mkdir()
    manifest = BackboneManifest(
        backbone_version="0.9.0",
        components=[
            ComponentRegistryEntry(
                kind="capability",
                name="evidence",
                manifest=".pkit/capabilities/evidence/manifest.yaml",
            ),
            ComponentRegistryEntry(
                kind="adapter",
                name="claude-code",
                manifest=".pkit/adapters/claude-code/project/manifest.yaml",
            ),
        ],
    )
    write_backbone_manifest(tmp_path, manifest)
    loaded = read_backbone_manifest(tmp_path)

    assert loaded is not None
    assert loaded.backbone_version == "0.9.0"
    assert len(loaded.components) == 2
    assert loaded.components[0].kind == "capability"
    assert loaded.components[0].name == "evidence"
    assert loaded.components[1].kind == "adapter"
    assert loaded.components[1].name == "claude-code"


def test_write_preserves_existing_comments(tmp_path: Path) -> None:
    """ruamel.yaml round-trip mode keeps comments through write+read."""
    (tmp_path / ".pkit").mkdir()
    path = tmp_path / ".pkit" / "manifest.yaml"
    path.write_text(
        "# Backbone manifest — adopter-managed.\n"
        "schema_version: 1\n"
        "backbone_version: 0.5.0\n"
        "components: []\n",
        encoding="utf-8",
    )

    write_backbone_manifest(tmp_path, BackboneManifest(backbone_version="0.6.0"))

    contents = path.read_text(encoding="utf-8")
    assert "# Backbone manifest — adopter-managed." in contents
    assert "backbone_version: 0.6.0" in contents


# --- capability origin (COR-031) ------------------------------------


def test_entry_origin_defaults_to_kit_shipped(tmp_path: Path) -> None:
    """A registry entry created without an origin defaults to kit-shipped."""
    entry = ComponentRegistryEntry(
        kind="capability",
        name="evidence",
        manifest=".pkit/capabilities/evidence/manifest.yaml",
    )
    assert entry.origin == ORIGIN_KIT_SHIPPED


def test_default_origin_is_omitted_from_serialization(tmp_path: Path) -> None:
    """Kit-shipped (default) origin is not written — keeps the change additive."""
    (tmp_path / ".pkit").mkdir()
    write_backbone_manifest(
        tmp_path,
        BackboneManifest(
            backbone_version="0.9.0",
            components=[
                ComponentRegistryEntry(
                    kind="capability",
                    name="evidence",
                    manifest=".pkit/capabilities/evidence/manifest.yaml",
                )
            ],
        ),
    )
    contents = (tmp_path / ".pkit" / "manifest.yaml").read_text(encoding="utf-8")
    assert "origin" not in contents


def test_incubated_origin_roundtrips(tmp_path: Path) -> None:
    """A non-default origin is written and read back."""
    (tmp_path / ".pkit").mkdir()
    write_backbone_manifest(
        tmp_path,
        BackboneManifest(
            backbone_version="0.9.0",
            components=[
                ComponentRegistryEntry(
                    kind="capability",
                    name="homegrown",
                    manifest=".pkit/capabilities/homegrown/manifest.yaml",
                    origin=ORIGIN_INCUBATED_IN_REPO,
                )
            ],
        ),
    )
    contents = (tmp_path / ".pkit" / "manifest.yaml").read_text(encoding="utf-8")
    assert f"origin: {ORIGIN_INCUBATED_IN_REPO}" in contents

    loaded = read_backbone_manifest(tmp_path)
    assert loaded is not None
    assert loaded.components[0].origin == ORIGIN_INCUBATED_IN_REPO


def test_absent_origin_reads_as_kit_shipped(tmp_path: Path) -> None:
    """A pre-existing entry with no origin field reads as kit-shipped (additive, no migration)."""
    (tmp_path / ".pkit").mkdir()
    path = tmp_path / ".pkit" / "manifest.yaml"
    path.write_text(
        "schema_version: 1\n"
        "backbone_version: 0.9.0\n"
        "components:\n"
        "  - kind: capability\n"
        "    name: legacy\n"
        "    manifest: .pkit/capabilities/legacy/manifest.yaml\n",
        encoding="utf-8",
    )
    loaded = read_backbone_manifest(tmp_path)
    assert loaded is not None
    assert loaded.components[0].origin == ORIGIN_KIT_SHIPPED


def test_read_capability_origin_accessor(tmp_path: Path) -> None:
    """The accessor reads origin from install-state, defaulting absent to kit-shipped."""
    (tmp_path / ".pkit").mkdir()
    write_backbone_manifest(
        tmp_path,
        BackboneManifest(
            backbone_version="0.9.0",
            components=[
                ComponentRegistryEntry(
                    kind="capability",
                    name="homegrown",
                    manifest=".pkit/capabilities/homegrown/manifest.yaml",
                    origin=ORIGIN_INCUBATED_IN_REPO,
                ),
                ComponentRegistryEntry(
                    kind="capability",
                    name="shipped",
                    manifest=".pkit/capabilities/shipped/manifest.yaml",
                ),
            ],
        ),
    )
    assert read_capability_origin(tmp_path, "homegrown") == ORIGIN_INCUBATED_IN_REPO
    assert read_capability_origin(tmp_path, "shipped") == ORIGIN_KIT_SHIPPED
    # Unregistered name → safe default.
    assert read_capability_origin(tmp_path, "nope") == ORIGIN_KIT_SHIPPED


def test_set_capability_origin_upgrades_existing_entry(tmp_path: Path) -> None:
    """Setting origin on an origin-unset entry rewrites only that field (COR-031 D2)."""
    (tmp_path / ".pkit").mkdir()
    write_backbone_manifest(
        tmp_path,
        BackboneManifest(
            backbone_version="0.9.0",
            components=[
                ComponentRegistryEntry(
                    kind="capability",
                    name="homegrown",
                    manifest=".pkit/capabilities/homegrown/manifest.yaml",
                ),
                ComponentRegistryEntry(
                    kind="capability",
                    name="other",
                    manifest=".pkit/capabilities/other/manifest.yaml",
                ),
            ],
        ),
    )
    assert read_capability_origin(tmp_path, "homegrown") == ORIGIN_KIT_SHIPPED

    changed = set_capability_origin(tmp_path, "homegrown", ORIGIN_INCUBATED_IN_REPO)
    assert changed is True
    assert read_capability_origin(tmp_path, "homegrown") == ORIGIN_INCUBATED_IN_REPO
    # Sibling entry untouched.
    assert read_capability_origin(tmp_path, "other") == ORIGIN_KIT_SHIPPED


def test_set_capability_origin_noop_when_already_set(tmp_path: Path) -> None:
    """Setting the origin it already holds reports no change and writes nothing."""
    (tmp_path / ".pkit").mkdir()
    write_backbone_manifest(
        tmp_path,
        BackboneManifest(
            backbone_version="0.9.0",
            components=[
                ComponentRegistryEntry(
                    kind="capability",
                    name="homegrown",
                    manifest=".pkit/capabilities/homegrown/manifest.yaml",
                    origin=ORIGIN_INCUBATED_IN_REPO,
                ),
            ],
        ),
    )
    assert set_capability_origin(tmp_path, "homegrown", ORIGIN_INCUBATED_IN_REPO) is False
    assert read_capability_origin(tmp_path, "homegrown") == ORIGIN_INCUBATED_IN_REPO


def test_set_capability_origin_returns_false_when_absent(tmp_path: Path) -> None:
    """No matching registry entry → no change."""
    (tmp_path / ".pkit").mkdir()
    write_backbone_manifest(tmp_path, BackboneManifest(backbone_version="0.9.0"))
    assert set_capability_origin(tmp_path, "nope", ORIGIN_INCUBATED_IN_REPO) is False


def test_write_uses_block_style_not_flow_style(tmp_path: Path) -> None:
    (tmp_path / ".pkit").mkdir()
    write_backbone_manifest(
        tmp_path,
        BackboneManifest(
            backbone_version="0.9.0",
            components=[
                ComponentRegistryEntry(
                    kind="capability",
                    name="evidence",
                    manifest=".pkit/capabilities/evidence/manifest.yaml",
                )
            ],
        ),
    )

    contents = (tmp_path / ".pkit" / "manifest.yaml").read_text(encoding="utf-8")
    # Block style: sequences use `- ` prefix on their own lines, not `[...]`.
    assert "  - kind: capability" in contents
    assert "[" not in contents.splitlines()[3]  # the components line itself isn't flow-style


# --- a capability's manifest, under its project/ (ADR-065 point 2) -------------


def test_a_capabilitys_manifest_is_registered_under_its_project() -> None:
    assert capability_manifest_rel("evidence") == (
        ".pkit/capabilities/evidence/project/manifest.yaml"
    )


def test_set_component_manifest_path_rewrites_only_that_entrys_path(tmp_path: Path) -> None:
    (tmp_path / ".pkit").mkdir()
    write_backbone_manifest(
        tmp_path,
        BackboneManifest(
            backbone_version="0.9.0",
            components=[
                ComponentRegistryEntry(
                    kind="capability",
                    name="evidence",
                    manifest=".pkit/capabilities/evidence/manifest.yaml",
                    origin=ORIGIN_INCUBATED_IN_REPO,
                ),
                ComponentRegistryEntry(
                    kind="capability",
                    name="other",
                    manifest=".pkit/capabilities/other/manifest.yaml",
                ),
            ],
        ),
    )
    moved = capability_manifest_rel("evidence")

    assert set_component_manifest_path(tmp_path, "capability", "evidence", moved) is True
    assert set_component_manifest_path(tmp_path, "capability", "evidence", moved) is False
    assert set_component_manifest_path(tmp_path, "capability", "nope", moved) is False

    loaded = read_backbone_manifest(tmp_path)
    assert loaded is not None
    assert [(c.name, c.manifest, c.origin) for c in loaded.components] == [
        ("evidence", moved, ORIGIN_INCUBATED_IN_REPO),
        ("other", ".pkit/capabilities/other/manifest.yaml", ORIGIN_KIT_SHIPPED),
    ]


def test_the_root_manifest_is_read_first_then_the_one_under_project(tmp_path: Path) -> None:
    cap = tmp_path / ".pkit" / "capabilities" / "evidence"
    (cap / "project").mkdir(parents=True)
    assert recorded_capability_manifest(tmp_path, "evidence") is None

    (cap / "project" / "manifest.yaml").write_text("schema_version: 1\n", encoding="utf-8")
    assert recorded_capability_manifest(tmp_path, "evidence") == cap / "project" / "manifest.yaml"

    (cap / "manifest.yaml").write_text("schema_version: 1\n", encoding="utf-8")
    assert recorded_capability_manifest(tmp_path, "evidence") == cap / "manifest.yaml"


# --- The backbone's two recorded states (ADR-065 point 3) --------------------------


_STATES = """\
schema_version: 1
# The install record.
backbone_version: 1.149.0
completed_version: 1.148.0
future_key: kept as written
components:
  - kind: adapter
    name: claude-code
    manifest: .pkit/adapters/claude-code/project/manifest.yaml
"""


def _write_raw(root: Path, text: str) -> Path:
    path = root / ".pkit" / "manifest.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_the_writer_keeps_a_key_it_does_not_know(tmp_path: Path) -> None:
    """A registry write keeps every key it does not set: the completion, and a key
    a later release may add. So an older pkit's writer leaves both in place, and
    the completion needs no schema bump (ADR-065 point 3)."""
    _write_raw(tmp_path, _STATES)
    loaded = read_backbone_manifest(tmp_path)
    assert loaded is not None
    loaded.components = []
    loaded.completed_version = "9.9.9"  # never written by the registry writer

    write_backbone_manifest(tmp_path, loaded)

    text = (tmp_path / ".pkit" / "manifest.yaml").read_text(encoding="utf-8")
    assert "future_key: kept as written" in text
    assert "completed_version: 1.148.0" in text
    reread = read_backbone_manifest(tmp_path)
    assert reread is not None
    assert reread.completed_version == "1.148.0"
    assert reread.components == []


def test_a_missing_or_empty_completion_reads_as_none(tmp_path: Path) -> None:
    _write_raw(tmp_path, "schema_version: 1\nbackbone_version: 1.0.0\ncomponents: []\n")
    loaded = read_backbone_manifest(tmp_path)
    assert loaded is not None and loaded.completed_version is None
    _write_raw(tmp_path, "schema_version: 1\nbackbone_version: 1.0.0\ncompleted_version:\n")
    loaded = read_backbone_manifest(tmp_path)
    assert loaded is not None and loaded.completed_version is None


@pytest.mark.parametrize(
    ("completed", "incomplete"),
    [
        (None, True),  # no completion: the history is unknown
        ("1.148.0", True),  # behind its target: an interrupted transition
        ("1.150.0", True),  # ahead: an older pkit synced over a finished transition
        ("1.149.0", False),
    ],
)
def test_a_transition_is_complete_only_when_both_states_are_equal(
    completed: str | None, incomplete: bool
) -> None:
    state = BackboneManifest(backbone_version="1.149.0", completed_version=completed)
    assert state.transition_incomplete is incomplete


def test_the_target_is_written_by_an_in_place_edit_of_its_own_line(tmp_path: Path) -> None:
    """Every other byte stays: the comment, the completion, an unknown key."""
    path = _write_raw(tmp_path, _STATES)

    record_backbone_target(tmp_path, "1.150.0")

    assert path.read_text(encoding="utf-8") == _STATES.replace(
        "backbone_version: 1.149.0", "backbone_version: 1.150.0"
    )


def test_the_target_seeds_a_missing_manifest_with_no_completion(tmp_path: Path) -> None:
    (tmp_path / ".pkit").mkdir()

    record_backbone_target(tmp_path, "1.150.0")

    loaded = read_backbone_manifest(tmp_path)
    assert loaded is not None
    assert loaded.backbone_version == "1.150.0"
    assert loaded.completed_version is None
    assert loaded.components == []


def test_the_completion_rewrites_its_line_or_adds_it_after_the_target(tmp_path: Path) -> None:
    path = _write_raw(tmp_path, _STATES)
    record_completed_version(tmp_path, "1.149.0")
    assert path.read_text(encoding="utf-8") == _STATES.replace(
        "completed_version: 1.148.0", "completed_version: 1.149.0"
    )

    without = _STATES.replace("completed_version: 1.148.0\n", "")
    _write_raw(tmp_path, without)
    record_completed_version(tmp_path, "1.149.0")
    assert path.read_text(encoding="utf-8") == without.replace(
        "backbone_version: 1.149.0\n", "backbone_version: 1.149.0\ncompleted_version: 1.149.0\n"
    )


@pytest.mark.parametrize(
    ("line", "written"),
    [
        ("completed_version:\n", "completed_version: 2.0.0\n"),
        ("completed_version:   \n", "completed_version: 2.0.0\n"),
        ("completed_version: # note\n", "completed_version: 2.0.0 # note\n"),
        ("completed_version: 1.0.0 # note\n", "completed_version: 2.0.0 # note\n"),
        ('completed_version: "1.0.0"\n', "completed_version: 2.0.0\n"),
    ],
)
def test_a_state_line_is_rewritten_whole_whatever_value_it_held(
    tmp_path: Path, line: str, written: str
) -> None:
    """An empty value, or a comment where the value was, still yields `key: value`,
    so the manifest stays YAML and the value reads back as the version written."""
    text = f"schema_version: 1\nbackbone_version: 2.0.0\n{line}components: []\n"
    assert set_state_line(text, "completed_version", "2.0.0") == text.replace(line, written)
    _write_raw(tmp_path, text)
    record_completed_version(tmp_path, "2.0.0")
    loaded = read_backbone_manifest(tmp_path)
    assert loaded is not None and loaded.completed_version == "2.0.0"


def test_set_state_line_appends_where_no_anchor_line_exists() -> None:
    assert set_state_line("a: 1", "completed_version", "1.0.0", after="backbone_version") == (
        "a: 1\ncompleted_version: 1.0.0\n"
    )
    assert set_state_line("", "backbone_version", "1.0.0") == "backbone_version: 1.0.0\n"


def test_an_adapter_is_recorded_at_the_version_its_package_ships(tmp_path: Path) -> None:
    package = tmp_path / "package.yaml"
    package.write_text(
        "schema_version: 1\ncomponent:\n  kind: adapter\n  name: harness\n  version: 0.4.0\n"
        'requires_backbone: ">=1.0.0,<2.0.0"\n',
        encoding="utf-8",
    )

    assert record_adapter_version(tmp_path, "harness", package) == "0.4.0"

    recorded = read_component_manifest(tmp_path / adapter_manifest_rel("harness"))
    assert recorded is not None
    assert (recorded.kind, recorded.name, recorded.version) == ("adapter", "harness", "0.4.0")
    assert recorded.requires_backbone == ">=1.0.0,<2.0.0"
    assert record_adapter_version(tmp_path, "harness", tmp_path / "missing.yaml") is None
