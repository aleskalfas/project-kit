"""Tests for the workstreams parsing library (_lib/workstreams.py).

Covers slug validation, mapping-form parsing, list-form parsing,
duplicate-name detection, and graceful handling of malformed input.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
LIB_PATH = (
    REPO_ROOT
    / ".pkit"
    / "capabilities"
    / "project-management"
    / "scripts"
    / "_lib"
    / "workstreams.py"
)


@pytest.fixture(scope="module")
def ws():
    module_name = "pm_workstreams_lib_under_test"
    spec = importlib.util.spec_from_file_location(module_name, LIB_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# --- slug pattern ----------------------------------------------------


def test_slug_pattern_matches_valid_slugs(ws) -> None:
    assert ws.SLUG_PATTERN.match("cli")
    assert ws.SLUG_PATTERN.match("agent-platform")
    assert ws.SLUG_PATTERN.match("a1-b2")
    assert ws.SLUG_PATTERN.match("ab")


def test_slug_pattern_rejects_invalid(ws) -> None:
    assert not ws.SLUG_PATTERN.match("A")
    assert not ws.SLUG_PATTERN.match("Cli")
    assert not ws.SLUG_PATTERN.match("-foo")
    assert not ws.SLUG_PATTERN.match("foo-")
    assert not ws.SLUG_PATTERN.match("foo_bar")
    assert not ws.SLUG_PATTERN.match("a")  # 1 char fails (needs 2+)


# --- empty input -----------------------------------------------------


def test_parse_none_returns_empty(ws) -> None:
    parse = ws.parse_workstreams(None)
    assert parse.form == "empty"
    assert parse.entries == ()
    assert parse.errors == ()


def test_parse_missing_workstreams_key(ws) -> None:
    parse = ws.parse_workstreams({"schema_version": 1})
    assert parse.form == "empty"
    assert any("missing" in e for e in parse.errors)


def test_parse_garbage_type_errors(ws) -> None:
    parse = ws.parse_workstreams({"workstreams": 42})
    assert parse.entries == ()
    assert any("list or mapping" in e for e in parse.errors)


# --- list form -------------------------------------------------------


def test_parse_list_form_simple(ws) -> None:
    parse = ws.parse_workstreams({"workstreams": ["cli", "schemas", "agent-platform"]})
    assert parse.form == "list"
    slugs = [w.slug for w in parse.entries]
    assert slugs == ["cli", "schemas", "agent-platform"]
    # Name defaults to slug.
    assert all(w.name == w.slug for w in parse.entries)
    assert all(w.status == "active" for w in parse.entries)


def test_parse_list_form_bare_list_accepted(ws) -> None:
    """The library also accepts a bare list (legacy config.yaml shape)."""
    parse = ws.parse_workstreams(["cli", "schemas"])
    assert parse.form == "list"
    assert len(parse.entries) == 2


def test_parse_list_rejects_invalid_slugs(ws) -> None:
    parse = ws.parse_workstreams({"workstreams": ["cli", "BadCase", "foo--bar"]})
    slugs = [w.slug for w in parse.entries]
    assert "cli" in slugs
    assert "BadCase" not in slugs
    assert "foo--bar" not in slugs
    assert len(parse.errors) >= 2


def test_parse_list_rejects_too_short(ws) -> None:
    parse = ws.parse_workstreams({"workstreams": ["a"]})
    assert parse.entries == ()
    assert len(parse.errors) >= 1


# --- mapping form ----------------------------------------------------


def test_parse_mapping_form_simple(ws) -> None:
    data = {
        "schema_version": 1,
        "workstreams": {
            "cli": {"name": "cli", "description": "CLI work", "status": "active"},
            "agent-platform": {
                "name": "Agent Platform",
                "description": "Kagenti platform",
                "status": "active",
            },
        },
    }
    parse = ws.parse_workstreams(data)
    assert parse.form == "mapping"
    assert len(parse.entries) == 2
    cli = next(w for w in parse.entries if w.slug == "cli")
    assert cli.name == "cli"
    assert cli.description == "CLI work"
    ap = next(w for w in parse.entries if w.slug == "agent-platform")
    assert ap.name == "Agent Platform"


def test_parse_mapping_with_null_attrs_defaults_name(ws) -> None:
    data = {"workstreams": {"cli": None}}
    parse = ws.parse_workstreams(data)
    assert len(parse.entries) == 1
    assert parse.entries[0].name == "cli"
    assert parse.entries[0].status == "active"


def test_parse_mapping_rejects_invalid_slug(ws) -> None:
    data = {"workstreams": {"BadCase": {"name": "x"}}}
    parse = ws.parse_workstreams(data)
    assert parse.entries == ()
    assert len(parse.errors) >= 1


def test_parse_mapping_rejects_invalid_status(ws) -> None:
    data = {"workstreams": {"cli": {"name": "cli", "status": "in-progress"}}}
    parse = ws.parse_workstreams(data)
    assert parse.entries == ()
    assert any("status" in e for e in parse.errors)


def test_parse_mapping_accepts_deprecated(ws) -> None:
    data = {
        "workstreams": {
            "cli": {
                "name": "cli",
                "status": "deprecated",
                "deprecated_reason": "merged into platform",
            }
        }
    }
    parse = ws.parse_workstreams(data)
    assert len(parse.entries) == 1
    assert parse.entries[0].status == "deprecated"
    assert parse.entries[0].deprecated_reason == "merged into platform"


def test_parse_mapping_rejects_oversized_name(ws) -> None:
    data = {"workstreams": {"cli": {"name": "x" * 65}}}
    parse = ws.parse_workstreams(data)
    assert parse.entries == ()


def test_parse_mapping_rejects_newline_in_description(ws) -> None:
    data = {"workstreams": {"cli": {"name": "cli", "description": "a\nb"}}}
    parse = ws.parse_workstreams(data)
    assert parse.entries == ()


# --- find_active + duplicate_names -----------------------------------


def test_find_active_filters_deprecated(ws) -> None:
    data = {
        "workstreams": {
            "cli": {"name": "cli", "status": "active"},
            "old-thing": {
                "name": "old",
                "status": "deprecated",
                "deprecated_reason": "merged",
            },
        }
    }
    parse = ws.parse_workstreams(data)
    active = ws.find_active(parse)
    assert {w.slug for w in active} == {"cli"}


def test_slug_set_returns_all_slugs(ws) -> None:
    data = {"workstreams": ["cli", "schemas", "agent-platform"]}
    parse = ws.parse_workstreams(data)
    assert ws.slug_set(parse) == {"cli", "schemas", "agent-platform"}


def test_duplicate_names_detects(ws) -> None:
    data = {
        "workstreams": {
            "cli-one": {"name": "Shared Name"},
            "cli-two": {"name": "Shared Name"},
            "unique": {"name": "Unique"},
        }
    }
    parse = ws.parse_workstreams(data)
    dupes = ws.duplicate_names(parse)
    assert dupes == ["Shared Name"]


def test_duplicate_names_ignores_deprecated(ws) -> None:
    data = {
        "workstreams": {
            "active-one": {"name": "Shared"},
            "deprecated-one": {
                "name": "Shared",
                "status": "deprecated",
                "deprecated_reason": "x",
            },
        }
    }
    parse = ws.parse_workstreams(data)
    assert ws.duplicate_names(parse) == []


# --- DEC-018's rules, checked by every mutator (#1940) ----------------


def test_validate_slug_keeps_the_rule_in_full(ws) -> None:
    assert ws.validate_slug("cli") is None
    assert ws.validate_slug("a" * 40) is None
    # The pattern alone accepts each of these; DEC-018's other rules do not.
    assert "consecutive hyphens" in ws.validate_slug("a--b")
    assert "2–40" in ws.validate_slug("a" * 41)
    assert ws.validate_slug("A-b") is not None
    assert ws.validate_slug("") is not None
    assert ws.validate_slug(None) is not None


def test_validate_attributes_accepts_values_within_the_rules(ws) -> None:
    assert (
        ws.validate_attributes(
            name="Agent Platform",
            description="d" * 200,
            status="deprecated",
            deprecated_reason="r" * 200,
        )
        == []
    )
    # An attribute not being set is not checked.
    assert ws.validate_attributes() == []


def test_validate_attributes_names_each_broken_rule(ws) -> None:
    errors = ws.validate_attributes(
        name="n" * 65,
        description="d" * 250,
        status="retired",
        deprecated_reason="line one\nline two",
    )
    joined = "\n".join(errors)
    assert "`name` is 65 chars" in joined
    assert "`description` is 250 chars" in joined
    assert "`status` must be" in joined
    assert "`deprecated_reason` must be one line" in joined
    assert len(errors) == 4


def test_validate_attributes_refuses_an_empty_name_and_a_multiline_description(ws) -> None:
    assert ws.validate_attributes(name="  ") == ["`name` must not be empty."]
    assert ws.validate_attributes(description="a\r\nb") == ["`description` must be one line."]


def test_rewrite_references_rewrites_both_typed_forms(ws) -> None:
    text = "Filed under workstream:cli, see [workstream:cli] and `workstream:cli`."
    new, count = ws.rewrite_references(text, "workstream:cli", "workstream:tools")
    assert count == 3
    assert new == "Filed under workstream:tools, see [workstream:tools] and `workstream:tools`."


def test_rewrite_references_leaves_longer_slugs_and_bare_slugs(ws) -> None:
    text = (
        "workstream:cli-tools, myworkstream:cli, the cli workstream, workstream:clix, "
        "workstream:cliX, workstream:cli_x"
    )
    new, count = ws.rewrite_references(text, "workstream:cli", "workstream:tools")
    assert count == 0
    assert new == text


# --- what an issue may take: the file's active workstreams (#1933) -----------

_FILE = (
    "schema_version: 1\n"
    "workstreams:\n"
    "  cli:\n"
    "    name: cli\n"
    "    status: active\n"
    "  docs:\n"
    "    name: docs\n"
    "    status: active\n"
    "  old:\n"
    "    name: old\n"
    "    status: deprecated\n"
    "    deprecated_reason: merged into cli\n"
)


def _stage(tmp_path: Path, *, file: str | None, legacy: str) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    (project / "config.yaml").write_text(f"schema_version: 1\n{legacy}", encoding="utf-8")
    if file is not None:
        (project / "workstreams.yaml").write_text(file, encoding="utf-8")
    return tmp_path


def test_read_declared_reads_the_file_where_it_exists(ws, tmp_path) -> None:
    """The file is authoritative, so an empty legacy key does not turn the check off."""
    declared = ws.read_declared(_stage(tmp_path, file=_FILE, legacy="workstreams: []\n"))
    assert declared is not None
    assert declared.source == "project/workstreams.yaml"
    assert [w.slug for w in ws.find_active(declared.parse)] == ["cli", "docs"]


def test_read_declared_prefers_the_file_to_a_stale_legacy_list(ws, tmp_path) -> None:
    """The 0.5.0 migration may leave a list in config.yaml: the file wins over it."""
    declared = ws.read_declared(_stage(tmp_path, file=_FILE, legacy="workstreams: [spyre]\n"))
    assert declared is not None
    assert ws.slug_set(declared.parse) == {"cli", "docs", "old"}


def test_read_declared_falls_back_to_the_legacy_list_without_a_file(ws, tmp_path) -> None:
    declared = ws.read_declared(_stage(tmp_path, file=None, legacy="workstreams: [spyre]\n"))
    assert declared is not None
    assert declared.source == "the `workstreams:` key of project/config.yaml"
    assert ws.slug_set(declared.parse) == {"spyre"}


@pytest.mark.parametrize("legacy", ["workstreams: []\n", ""])
def test_read_declared_is_none_where_the_project_declares_nothing(ws, tmp_path, legacy) -> None:
    assert ws.read_declared(_stage(tmp_path, file=None, legacy=legacy)) is None


def test_read_declared_keeps_why_an_unreadable_file_declares_nothing(ws, tmp_path) -> None:
    declared = ws.read_declared(_stage(tmp_path, file="workstreams: [\n", legacy=""))
    assert declared is not None
    assert declared.parse.entries == ()
    assert "cannot be read" in declared.parse.errors[0]


def test_filing_refusal_accepts_an_active_workstream(ws, tmp_path) -> None:
    declared = ws.read_declared(_stage(tmp_path, file=_FILE, legacy=""))
    assert ws.filing_refusal("cli", declared) is None


def test_filing_refusal_refuses_a_workstream_the_file_lacks(ws, tmp_path) -> None:
    declared = ws.read_declared(_stage(tmp_path, file=_FILE, legacy="workstreams: []\n"))
    refusal = ws.filing_refusal("no-such-workstream", declared)
    assert refusal is not None
    assert "'no-such-workstream' is not in project/workstreams.yaml" in refusal
    assert "Its active workstreams: cli, docs." in refusal
    assert "add-workstream" in refusal


def test_filing_refusal_refuses_a_deprecated_workstream_with_its_reason(ws, tmp_path) -> None:
    declared = ws.read_declared(_stage(tmp_path, file=_FILE, legacy=""))
    refusal = ws.filing_refusal("old", declared)
    assert refusal is not None
    assert "'old' is deprecated in project/workstreams.yaml: merged into cli." in refusal


def test_filing_refusal_refuses_every_value_of_a_file_with_none_active(ws, tmp_path) -> None:
    empty = "schema_version: 1\nworkstreams: {}\n"
    declared = ws.read_declared(_stage(tmp_path, file=empty, legacy=""))
    refusal = ws.filing_refusal("cli", declared)
    assert refusal is not None
    assert "which holds no active workstream" in refusal


def test_filing_refusal_names_why_the_file_could_not_be_read(ws, tmp_path) -> None:
    declared = ws.read_declared(_stage(tmp_path, file="workstreams: [\n", legacy=""))
    refusal = ws.filing_refusal("cli", declared)
    assert refusal is not None
    assert "Problems in the file: it cannot be read:" in refusal


def test_filing_refusal_checks_nothing_where_the_project_declares_nothing(ws) -> None:
    assert ws.filing_refusal("anything", None) is None
