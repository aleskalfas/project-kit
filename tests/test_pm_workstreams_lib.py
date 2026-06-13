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
