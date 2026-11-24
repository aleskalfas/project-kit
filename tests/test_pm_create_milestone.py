"""Tests for project-management's create-milestone script — pure logic.

Covers title-format → regex conversion and max-number-from-milestone-list
computation. The gh subprocess invocations are thin wrappers and not
unit-tested.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = (
    REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts" / "create-milestone.py"
)


@pytest.fixture(scope="module")
def cm():
    """Load create-milestone.py as a module via importlib."""
    module_name = "pm_create_milestone_under_test"
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# --- title format → regex --------------------------------------------


def test_regex_matches_canonical_milestone_format(cm) -> None:
    regex = cm.title_format_regex("Milestone {n}: {name}")
    m = regex.match("Milestone 1: Self-host cleanly")
    assert m is not None
    assert m.group("n") == "1"
    assert m.group("name") == "Self-host cleanly"


def test_regex_matches_phase_format(cm) -> None:
    regex = cm.title_format_regex("Phase {n}: {name}")
    m = regex.match("Phase 5: Sprint Q3")
    assert m is not None
    assert m.group("n") == "5"
    assert m.group("name") == "Sprint Q3"


def test_regex_matches_release_format(cm) -> None:
    """Release format has only {n}, no {name} — but the format still requires {name}
    per the script's validation. This test confirms the regex compiles for a
    purely numeric tail format."""
    regex = cm.title_format_regex("v{n} GA: {name}")
    m = regex.match("v3 GA: stable release")
    assert m is not None
    assert m.group("n") == "3"


def test_regex_rejects_non_matching_title(cm) -> None:
    regex = cm.title_format_regex("Milestone {n}: {name}")
    assert regex.match("Phase 1: thing") is None
    assert regex.match("Just a regular title") is None
    assert regex.match("Milestone: missing number") is None


def test_regex_escapes_special_format_characters(cm) -> None:
    """A title_format with regex-special characters (e.g., periods) is escaped."""
    regex = cm.title_format_regex("v{n}.0 — {name}")
    m = regex.match("v2.0 — initial release")
    assert m is not None
    assert m.group("n") == "2"
    # Confirm the . in v{n}.0 is literal, not a wildcard.
    assert regex.match("v2X0 — initial release") is None


# --- next-number-from-list ------------------------------------------


def _patch_gh_list(monkeypatch, cm, milestones):
    """Stub `_gh_list_milestones` to return a fixed list."""
    monkeypatch.setattr(cm, "_gh_list_milestones", lambda config=None: milestones)


def test_next_number_returns_one_when_no_milestones_exist(cm, monkeypatch) -> None:
    _patch_gh_list(monkeypatch, cm, [])
    assert cm._next_number_for_category("Milestone {n}: {name}") == 1


def test_next_number_returns_max_plus_one(cm, monkeypatch) -> None:
    _patch_gh_list(
        monkeypatch,
        cm,
        [
            {"title": "Milestone 1: First"},
            {"title": "Milestone 2: Second"},
            {"title": "Milestone 3: Third"},
        ],
    )
    assert cm._next_number_for_category("Milestone {n}: {name}") == 4


def test_next_number_skips_milestones_in_other_categories(cm, monkeypatch) -> None:
    """A repo with Phase + Milestone milestones — `Milestone {n}:` only counts Milestones."""
    _patch_gh_list(
        monkeypatch,
        cm,
        [
            {"title": "Phase 1: Sprint A"},
            {"title": "Phase 2: Sprint B"},
            {"title": "Milestone 1: Bundle A"},
            {"title": "v3 GA: release"},
        ],
    )
    assert cm._next_number_for_category("Milestone {n}: {name}") == 2


def test_next_number_handles_gaps(cm, monkeypatch) -> None:
    """Gaps don't matter — script picks max+1, not first-available."""
    _patch_gh_list(
        monkeypatch,
        cm,
        [
            {"title": "Milestone 1: First"},
            {"title": "Milestone 4: Fourth"},  # gap: 2, 3 missing
        ],
    )
    assert cm._next_number_for_category("Milestone {n}: {name}") == 5


def test_next_number_ignores_unparseable_numbers(cm, monkeypatch) -> None:
    """A milestone whose `n` group matches but doesn't parse as int is silently skipped."""
    _patch_gh_list(
        monkeypatch,
        cm,
        [
            {"title": "Milestone 1: First"},
            # The regex requires \d+ for n, so this won't even match — but
            # the defensive try/except in _next_number_for_category handles
            # edge cases like format changes.
        ],
    )
    assert cm._next_number_for_category("Milestone {n}: {name}") == 2


def test_next_number_returns_none_when_gh_fails(cm, monkeypatch) -> None:
    monkeypatch.setattr(cm, "_gh_list_milestones", lambda config=None: None)
    assert cm._next_number_for_category("Milestone {n}: {name}") is None


# --- existing-title check -------------------------------------------


def test_existing_with_title_finds_exact_match(cm, monkeypatch) -> None:
    _patch_gh_list(
        monkeypatch,
        cm,
        [
            {"title": "Milestone 1: A", "number": 1},
            {"title": "Milestone 2: B", "number": 2},
        ],
    )
    found = cm._existing_milestone_with_title("Milestone 2: B")
    assert found is not None
    assert found["number"] == 2


def test_existing_with_title_returns_none_when_absent(cm, monkeypatch) -> None:
    _patch_gh_list(
        monkeypatch,
        cm,
        [
            {"title": "Milestone 1: A"},
        ],
    )
    assert cm._existing_milestone_with_title("Milestone 2: B") is None


def test_existing_with_title_is_case_sensitive(cm, monkeypatch) -> None:
    """Title matching is exact — case differences are not collapsed."""
    _patch_gh_list(
        monkeypatch,
        cm,
        [
            {"title": "Milestone 1: lowercase"},
        ],
    )
    assert cm._existing_milestone_with_title("Milestone 1: LOWERCASE") is None


# --- titles.yaml's `milestone` check at filing (#803) -----------------


def _run_dry(
    cm,
    tmp_path,
    monkeypatch,
    *,
    title_format: str = "R{n} {name}",
    name: str = "first",
    config: str | None = None,
) -> int:
    """Run main() --dry-run for the category `release` against a staged tree
    carrying the shipped titles.yaml. The configuration declares `release` with
    `title_format`, unless `config` gives its text."""
    from types import SimpleNamespace

    root = tmp_path / "project-management"
    (root / "schemas").mkdir(parents=True)
    (root / "project").mkdir(parents=True)
    shipped = SCRIPT_PATH.parent.parent / "schemas" / "titles.yaml"
    (root / "schemas" / "titles.yaml").write_text(shipped.read_text("utf-8"), "utf-8")
    if config is None:
        config = (
            "milestone_categories:\n"
            "  release:\n"
            f"    title_format: '{title_format}'\n"
            "    close_trigger_default: content-based\n"
        )
    (root / "project" / "config.yaml").write_text(config, "utf-8")
    monkeypatch.setattr(cm, "resolve_capability_root", lambda _explicit: root)
    monkeypatch.setattr(cm.bootstrap_gate, "enforce", lambda *a, **k: True)
    monkeypatch.setattr(cm.session_guard, "enforce", lambda **k: True)
    monkeypatch.setattr(cm, "load_adopter_config", lambda _root: {})
    monkeypatch.setattr(cm, "check_membership", lambda *a: SimpleNamespace(allowed=True))
    monkeypatch.setattr(
        cm, "resolve_invoker_identity", lambda **k: SimpleNamespace(github_login="me")
    )
    monkeypatch.setattr(
        cm.sys,
        "argv",
        ["create-milestone.py", "release", "--name", name, "--number", "3", "--dry-run"],
    )
    return cm.main()


def test_a_numeric_only_milestone_title_warns(cm, tmp_path, monkeypatch, capsys) -> None:
    rc = _run_dry(cm, tmp_path, monkeypatch, title_format="M{n} {name}", name="1")

    assert rc == 0
    assert "[warning] title.numeric-only" in capsys.readouterr().err


def test_a_named_milestone_title_draws_no_warning(cm, tmp_path, monkeypatch, capsys) -> None:
    rc = _run_dry(cm, tmp_path, monkeypatch, title_format="M{n} {name}", name="CLI walkthrough")

    assert rc == 0
    assert "title." not in capsys.readouterr().err


# --- a category not declared: the refusal names the command (#3160) -----------


def test_with_no_category_declared_the_refusal_names_the_command(
    cm, tmp_path, monkeypatch, capsys
) -> None:
    rc = _run_dry(cm, tmp_path, monkeypatch, config="schema_version: 1\n")

    assert rc == 2
    err = capsys.readouterr().err
    assert "no milestone categories declared" in err
    assert (
        "pkit pm add-milestone-category release --title-format "
        "'<a format with {n} and {name}>' --close-trigger <date-based|content-based|either>"
    ) in err


def test_a_category_not_declared_is_refused_with_the_command(
    cm, tmp_path, monkeypatch, capsys
) -> None:
    config = (
        "milestone_categories:\n"
        "  phase:\n"
        "    title_format: 'Phase {n}: {name}'\n"
        "    close_trigger_default: date-based\n"
    )
    rc = _run_dry(cm, tmp_path, monkeypatch, config=config)

    assert rc == 2
    err = capsys.readouterr().err
    assert "Declared categories: phase." in err
    assert "pkit pm add-milestone-category release --title-format" in err


@pytest.mark.parametrize(
    "title_format", ["R{n} {name} {owner}", "R{n} {name} {0}", "R{n} {name} }"]
)
def test_a_format_with_a_placeholder_it_cannot_fill_is_refused(
    cm, tmp_path, monkeypatch, capsys, title_format
) -> None:
    rc = _run_dry(cm, tmp_path, monkeypatch, title_format=title_format)

    assert rc == 2
    assert "other than {n} and {name}" in capsys.readouterr().err


def test_a_category_add_milestone_category_declares_is_filed_in(
    cm, tmp_path, monkeypatch, capsys
) -> None:
    from _lib import milestone_categories

    config = tmp_path / "declared.yaml"
    config.write_text("schema_version: 1\n", "utf-8")
    milestone_categories.declare(
        config, "release", milestone_categories.entry("R{n}: {name}", "either", "Releases.")
    )

    rc = _run_dry(cm, tmp_path, monkeypatch, config=config.read_text("utf-8"), name="Polish")

    assert rc == 0
    out = capsys.readouterr().out
    assert "title:         R3: Polish" in out
    assert "close_trigger: either" in out
