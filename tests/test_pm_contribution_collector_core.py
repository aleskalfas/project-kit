"""Tests for the shared contribution-collector core (_lib/contribution_collector.py).

Per ADR-038 the orphan-safe manifest walk, per-declaration read, `schema_version`
validation, error taxonomy, and fail-disposition policy are extracted into one
core that each contribution kind instantiates. This covers the core directly
(independent of any one kind):

  * `list_registered_capabilities` — manifest `components:` reading, orphan-safe.
  * `validate_schema_version` — absent / non-int / mismatched / matching.
  * `collect` — the manifest walk against a temp tree, exercising:
      - no declarations present (empty, ok),
      - one registered capability with a declaration (collected),
      - an UNregistered (orphan) directory present but ignored,
      - a schema_version mismatch skipped-and-recorded,
      - a malformed declaration surfaced through the kind's parser,
      - the FAIL_CLOSED vs SKIP_AND_WARN disposition on `ok` / blocking.
      - an optional resolver replacing an item + adding an error.
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
CORE_PATH = SCRIPTS_DIR / "_lib" / "contribution_collector.py"


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
def cc():
    return _load_lib("pm_contribution_collector_under_test", CORE_PATH)


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


def _write_decl(repo_root: Path, capability: str, filename: str, body: str) -> None:
    cap_dir = repo_root / ".pkit" / "capabilities" / capability
    cap_dir.mkdir(parents=True, exist_ok=True)
    (cap_dir / filename).write_text(body, encoding="utf-8")


# A trivial per-entry parser: a declaration is `{items: [str, ...]}`; each
# non-empty string becomes an item, anything else a malformed error. Enough to
# exercise the core without depending on a real kind.
def _make_parse(cc):
    def parse(data, capability):
        if data is None:
            return (), ()
        if not isinstance(data, dict):
            return (), (
                cc.ContributionError(cc.ERROR_MALFORMED, capability, "not a mapping"),
            )
        entries = data.get("items")
        if not isinstance(entries, list):
            return (), (
                cc.ContributionError(
                    cc.ERROR_MALFORMED, capability, "`items` must be a list"
                ),
            )
        items = []
        errors = []
        for e in entries:
            if isinstance(e, str) and e:
                items.append((capability, e))
            else:
                errors.append(
                    cc.ContributionError(
                        cc.ERROR_MALFORMED, capability, f"bad item {e!r}"
                    )
                )
        return tuple(items), tuple(errors)

    return parse


# --- list_registered_capabilities ------------------------------------


def test_list_registered_capabilities_filters_kind(cc) -> None:
    manifest = {
        "components": [
            {"kind": "adapter", "name": "claude-code"},
            {"kind": "capability", "name": "project-management"},
            {"kind": "capability", "name": "ux-ui-design"},
        ]
    }
    assert cc.list_registered_capabilities(manifest) == (
        "project-management",
        "ux-ui-design",
    )


def test_list_registered_capabilities_tolerates_garbage(cc) -> None:
    assert cc.list_registered_capabilities(None) == ()
    assert cc.list_registered_capabilities({}) == ()
    assert cc.list_registered_capabilities({"components": "nope"}) == ()


# --- validate_schema_version -----------------------------------------


def test_validate_schema_version_matching_is_none(cc) -> None:
    assert cc.validate_schema_version({"schema_version": 1}, "cap", 1, "k") is None


def test_validate_schema_version_absent_is_malformed(cc) -> None:
    err = cc.validate_schema_version({}, "cap", 1, "k")
    assert err is not None and err.kind == cc.ERROR_MALFORMED
    assert "schema_version" in err.message


def test_validate_schema_version_non_int_is_malformed(cc) -> None:
    err = cc.validate_schema_version({"schema_version": "1"}, "cap", 1, "k")
    assert err is not None and err.kind == cc.ERROR_MALFORMED


def test_validate_schema_version_bool_is_not_an_int(cc) -> None:
    # `True` is an int subclass in Python; guard it explicitly.
    err = cc.validate_schema_version({"schema_version": True}, "cap", 1, "k")
    assert err is not None and err.kind == cc.ERROR_MALFORMED


def test_validate_schema_version_mismatch_is_malformed(cc) -> None:
    err = cc.validate_schema_version({"schema_version": 2}, "cap", 1, "k")
    assert err is not None and err.kind == cc.ERROR_MALFORMED
    assert "version 1" in err.message


def test_validate_schema_version_non_mapping_defers(cc) -> None:
    # Non-mapping data is left to the kind's parser (clearer message there).
    assert cc.validate_schema_version("nope", "cap", 1, "k") is None


# --- collect (end-to-end against a temp tree) ------------------------


def test_collect_no_declarations_present(cc, tmp_path) -> None:
    _write_manifest(tmp_path, ["project-management"])
    result = cc.collect(
        tmp_path,
        filename="x.yaml",
        parse_entries=_make_parse(cc),
        disposition=cc.Disposition.SKIP_AND_WARN,
    )
    assert result.items == ()
    assert result.errors == ()
    assert result.ok is True
    assert result.capabilities_walked == ("project-management",)


def test_collect_one_registered_capability_with_item(cc, tmp_path) -> None:
    _write_manifest(tmp_path, ["project-management", "ux-ui-design"])
    _write_decl(tmp_path, "ux-ui-design", "x.yaml", "items:\n  - alpha\n")
    result = cc.collect(
        tmp_path,
        filename="x.yaml",
        parse_entries=_make_parse(cc),
        disposition=cc.Disposition.SKIP_AND_WARN,
    )
    assert result.items == (("ux-ui-design", "alpha"),)
    assert result.ok is True


def test_collect_ignores_orphan_unregistered_capability(cc, tmp_path) -> None:
    # Only project-management is registered; the orphan dir must not contribute.
    _write_manifest(tmp_path, ["project-management"])
    _write_decl(tmp_path, "ux-ui-design", "x.yaml", "items:\n  - alpha\n")
    result = cc.collect(
        tmp_path,
        filename="x.yaml",
        parse_entries=_make_parse(cc),
        disposition=cc.Disposition.SKIP_AND_WARN,
    )
    assert result.items == ()
    assert "ux-ui-design" not in result.capabilities_walked


def test_collect_missing_manifest_returns_empty(cc, tmp_path) -> None:
    result = cc.collect(
        tmp_path,
        filename="x.yaml",
        parse_entries=_make_parse(cc),
        disposition=cc.Disposition.SKIP_AND_WARN,
    )
    assert result.items == ()
    assert result.ok is True
    assert result.capabilities_walked == ()


def test_collect_schema_version_mismatch_skips_declaration(cc, tmp_path) -> None:
    _write_manifest(tmp_path, ["ux-ui-design"])
    _write_decl(
        tmp_path, "ux-ui-design", "x.yaml", "schema_version: 2\nitems:\n  - alpha\n"
    )
    result = cc.collect(
        tmp_path,
        filename="x.yaml",
        parse_entries=_make_parse(cc),
        disposition=cc.Disposition.SKIP_AND_WARN,
        expected_schema_version=1,
        schema_version_prefix="x",
    )
    # The whole declaration drops (incompatible), a warning is recorded.
    assert result.items == ()
    assert any(e.kind == cc.ERROR_MALFORMED for e in result.errors)


def test_collect_schema_version_match_collects(cc, tmp_path) -> None:
    _write_manifest(tmp_path, ["ux-ui-design"])
    _write_decl(
        tmp_path, "ux-ui-design", "x.yaml", "schema_version: 1\nitems:\n  - alpha\n"
    )
    result = cc.collect(
        tmp_path,
        filename="x.yaml",
        parse_entries=_make_parse(cc),
        disposition=cc.Disposition.SKIP_AND_WARN,
        expected_schema_version=1,
        schema_version_prefix="x",
    )
    assert result.items == (("ux-ui-design", "alpha"),)
    assert result.errors == ()


def test_collect_malformed_declaration_surfaced(cc, tmp_path) -> None:
    _write_manifest(tmp_path, ["ux-ui-design"])
    _write_decl(tmp_path, "ux-ui-design", "x.yaml", "items: not-a-list\n")
    result = cc.collect(
        tmp_path,
        filename="x.yaml",
        parse_entries=_make_parse(cc),
        disposition=cc.Disposition.SKIP_AND_WARN,
    )
    assert result.items == ()
    err = next(e for e in result.errors if "must be a list" in e.message)
    assert err.kind == cc.ERROR_MALFORMED
    assert err.capability == "ux-ui-design"


def test_collect_parse_error_is_error_parse(cc, tmp_path) -> None:
    _write_manifest(tmp_path, ["ux-ui-design"])
    # Invalid YAML → the core's load raises RuntimeError → ERROR_PARSE.
    _write_decl(tmp_path, "ux-ui-design", "x.yaml", "items: [unterminated\n")
    result = cc.collect(
        tmp_path,
        filename="x.yaml",
        parse_entries=_make_parse(cc),
        disposition=cc.Disposition.SKIP_AND_WARN,
    )
    assert any(e.kind == cc.ERROR_PARSE for e in result.errors)


# --- disposition: block vs warn --------------------------------------


def test_fail_closed_error_blocks(cc, tmp_path) -> None:
    _write_manifest(tmp_path, ["ux-ui-design"])
    _write_decl(tmp_path, "ux-ui-design", "x.yaml", "items: not-a-list\n")
    result = cc.collect(
        tmp_path,
        filename="x.yaml",
        parse_entries=_make_parse(cc),
        disposition=cc.Disposition.FAIL_CLOSED,
    )
    assert result.has_blocking_errors is True
    assert result.ok is False


def test_skip_and_warn_error_does_not_block(cc, tmp_path) -> None:
    _write_manifest(tmp_path, ["ux-ui-design"])
    _write_decl(tmp_path, "ux-ui-design", "x.yaml", "items: not-a-list\n")
    result = cc.collect(
        tmp_path,
        filename="x.yaml",
        parse_entries=_make_parse(cc),
        disposition=cc.Disposition.SKIP_AND_WARN,
    )
    # Same error, opposite disposition: it is a warning, not a blocker.
    assert result.errors  # surfaced...
    assert result.warnings == result.errors  # ...via the warn channel too
    assert result.has_blocking_errors is False
    assert result.ok is True


# --- optional resolver -----------------------------------------------


def test_collect_resolver_replaces_item_and_adds_error(cc, tmp_path) -> None:
    _write_manifest(tmp_path, ["ux-ui-design"])
    _write_decl(tmp_path, "ux-ui-design", "x.yaml", "items:\n  - alpha\n")

    def resolve(repo_root, capability, item):
        replaced = (item[0], item[1].upper())
        err = cc.ContributionError(cc.ERROR_MALFORMED, capability, "resolved-with-note")
        return replaced, (err,)

    result = cc.collect(
        tmp_path,
        filename="x.yaml",
        parse_entries=_make_parse(cc),
        disposition=cc.Disposition.FAIL_CLOSED,
        resolve=resolve,
    )
    assert result.items == (("ux-ui-design", "ALPHA"),)
    assert any(e.message == "resolved-with-note" for e in result.errors)
