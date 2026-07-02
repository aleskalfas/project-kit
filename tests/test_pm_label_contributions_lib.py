"""Tests for the label-contribution collector (_lib/label_contributions.py).

Per project-management:DEC-042 a capability declares the labels it needs and pm
collects them by walking the manifest-registered capabilities (the second
instantiation of the ADR-038 collector core). This covers:

  * `parse_label_contributions` — well-formed, empty, malformed-entry-skips,
    missing field, duplicate id, non-mapping.
  * `collect_label_contributions` end-to-end against a temp tree — collected,
    orphan-ignored, schema_version mismatch skipped-and-warned (NOT blocking),
    malformed skip-and-warn.
  * `resolve_contributed_label` — the inert v1 seam returns `default_name`, and
    None for an unknown id.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = (
    REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
)
LIB_PATH = SCRIPTS_DIR / "_lib" / "label_contributions.py"


def _load_lib(module_name: str, path: Path):
    scripts_dir_str = str(SCRIPTS_DIR)
    inserted = scripts_dir_str not in sys.path
    if inserted:
        sys.path.insert(0, scripts_dir_str)
    try:
        spec = importlib.util.spec_from_file_location(module_name, path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        if inserted and scripts_dir_str in sys.path:
            sys.path.remove(scripts_dir_str)


@pytest.fixture(scope="module")
def lc():
    return _load_lib("pm_label_contributions_lib_under_test", LIB_PATH)


# --- repo-tree builders ----------------------------------------------


def _write_manifest(repo_root: Path, capability_names: list[str]) -> None:
    lines = ["schema_version: 1", "backbone_version: 1.0.0", "components:"]
    lines += [
        "  - kind: adapter",
        "    name: claude-code",
        "    manifest: .pkit/adapters/claude-code/project/manifest.yaml",
    ]
    for name in capability_names:
        lines += [
            "  - kind: capability",
            f"    name: {name}",
            f"    manifest: .pkit/capabilities/{name}/manifest.yaml",
        ]
    (repo_root / ".pkit").mkdir(parents=True, exist_ok=True)
    (repo_root / ".pkit" / "manifest.yaml").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


_NEEDS_DESIGN = (
    "schema_version: 1\n"
    "labels:\n"
    "  - id: needs-design\n"
    "    default_name: needs-design\n"
    "    color: d4c5f9\n"
    "    description: Requires design input.\n"
)


def _write_labels(repo_root: Path, capability: str, body: str) -> None:
    cap_dir = repo_root / ".pkit" / "capabilities" / capability
    cap_dir.mkdir(parents=True, exist_ok=True)
    (cap_dir / "label-contributions.yaml").write_text(body, encoding="utf-8")


# --- parse_label_contributions (pure shape validation) ---------------


def test_parse_none_is_empty_no_error(lc) -> None:
    labels, errors = lc.parse_label_contributions(None, "ux-ui-design")
    assert labels == ()
    assert errors == ()


def test_parse_well_formed_label(lc) -> None:
    data = {
        "schema_version": 1,
        "labels": [
            {
                "id": "needs-design",
                "default_name": "needs-design",
                "color": "d4c5f9",
                "description": "Requires design input.",
            }
        ],
    }
    labels, errors = lc.parse_label_contributions(data, "ux-ui-design")
    assert errors == ()
    assert len(labels) == 1
    label = labels[0]
    assert label.id == "needs-design"
    assert label.default_name == "needs-design"
    assert label.color == "d4c5f9"
    assert label.description == "Requires design input."
    assert label.capability == "ux-ui-design"


def test_parse_missing_labels_key(lc) -> None:
    labels, errors = lc.parse_label_contributions({"schema_version": 1}, "cap")
    assert labels == ()
    assert any("missing the `labels:` key" in e.message for e in errors)


def test_parse_labels_not_a_list(lc) -> None:
    labels, errors = lc.parse_label_contributions({"labels": "nope"}, "cap")
    assert labels == ()
    assert any("`labels` must be a list" in e.message for e in errors)


def test_parse_non_mapping_data(lc) -> None:
    labels, errors = lc.parse_label_contributions(["x"], "cap")
    assert labels == ()
    assert any("must be a mapping" in e.message for e in errors)


def test_parse_missing_field_skips_entry(lc) -> None:
    data = {
        "labels": [
            {"id": "a", "default_name": "a", "color": "aaaaaa"},  # no description
        ]
    }
    labels, errors = lc.parse_label_contributions(data, "cap")
    assert labels == ()
    assert any("description must be a non-empty string" in e.message for e in errors)


def test_parse_mixed_good_and_bad_entries(lc) -> None:
    # Skip-and-warn at the entry level: a broken entry drops, a sibling
    # well-formed one still contributes.
    data = {
        "labels": [
            {
                "id": "good",
                "default_name": "good",
                "color": "aaaaaa",
                "description": "ok",
            },
            {"id": "bad"},  # missing fields
        ]
    }
    labels, errors = lc.parse_label_contributions(data, "cap")
    assert [l.id for l in labels] == ["good"]
    assert errors  # the bad entry warned


def test_parse_duplicate_id_within_declaration(lc) -> None:
    data = {
        "labels": [
            {"id": "dup", "default_name": "a", "color": "aaaaaa", "description": "x"},
            {"id": "dup", "default_name": "b", "color": "bbbbbb", "description": "y"},
        ]
    }
    labels, errors = lc.parse_label_contributions(data, "cap")
    assert [l.id for l in labels] == ["dup"]  # first wins
    assert any("duplicate label id" in e.message for e in errors)


# --- collect_label_contributions (end-to-end) ------------------------


def test_collect_no_contributions_present(lc, tmp_path) -> None:
    _write_manifest(tmp_path, ["project-management"])
    result = lc.collect_label_contributions(tmp_path)
    assert result.labels == ()
    assert result.warnings == ()
    assert result.capabilities_walked == ("project-management",)


def test_collect_one_registered_capability(lc, tmp_path) -> None:
    _write_manifest(tmp_path, ["project-management", "ux-ui-design"])
    _write_labels(tmp_path, "ux-ui-design", _NEEDS_DESIGN)
    result = lc.collect_label_contributions(tmp_path)
    assert len(result.labels) == 1
    assert result.labels[0].id == "needs-design"
    assert result.labels[0].capability == "ux-ui-design"


def test_collect_ignores_orphan_unregistered_capability(lc, tmp_path) -> None:
    _write_manifest(tmp_path, ["project-management"])
    _write_labels(tmp_path, "ux-ui-design", _NEEDS_DESIGN)  # not registered
    result = lc.collect_label_contributions(tmp_path)
    assert result.labels == ()
    assert "ux-ui-design" not in result.capabilities_walked


def test_collect_schema_version_mismatch_skips_and_warns(lc, tmp_path) -> None:
    _write_manifest(tmp_path, ["ux-ui-design"])
    _write_labels(
        tmp_path,
        "ux-ui-design",
        _NEEDS_DESIGN.replace("schema_version: 1", "schema_version: 2"),
    )
    result = lc.collect_label_contributions(tmp_path)
    # Skipped-and-warned: no label collected, a warning surfaced, NOT blocking.
    assert result.labels == ()
    assert result.warnings
    assert any("schema_version" in str(w) for w in result.warnings)


def test_collect_malformed_declaration_skips_and_warns(lc, tmp_path) -> None:
    _write_manifest(tmp_path, ["ux-ui-design"])
    _write_labels(tmp_path, "ux-ui-design", "schema_version: 1\nlabels: not-a-list\n")
    result = lc.collect_label_contributions(tmp_path)
    assert result.labels == ()
    assert any("`labels` must be a list" in str(w) for w in result.warnings)


# --- resolve_contributed_label (the inert v1 seam, DEC-042 D5) -------


def test_resolve_contributed_label_returns_default_name(lc, tmp_path) -> None:
    _write_manifest(tmp_path, ["ux-ui-design"])
    _write_labels(tmp_path, "ux-ui-design", _NEEDS_DESIGN)
    # v1 is the identity map: the seam returns the declared default_name.
    assert lc.resolve_contributed_label(tmp_path, "needs-design") == "needs-design"


def test_resolve_contributed_label_unknown_id_is_none(lc, tmp_path) -> None:
    _write_manifest(tmp_path, ["ux-ui-design"])
    _write_labels(tmp_path, "ux-ui-design", _NEEDS_DESIGN)
    assert lc.resolve_contributed_label(tmp_path, "no-such-id") is None


def test_resolve_contributed_label_no_contributor_is_none(lc, tmp_path) -> None:
    _write_manifest(tmp_path, ["project-management"])
    assert lc.resolve_contributed_label(tmp_path, "needs-design") is None
