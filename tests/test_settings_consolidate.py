"""Tests for `pkit settings consolidate` and its subsumption logic."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from project_kit.cli import main
from project_kit.settings_consolidate import (
    apply_consolidation,
    detect_consolidation_opportunities,
    is_subsumed_by,
    plan_consolidation,
)


# --- subsumption rules ----------------------------------------------


def test_subsumes_when_broader_covers_subcommand() -> None:
    """`Bash(pkit:*)` subsumes `Bash(pkit new *)`."""
    assert is_subsumed_by("Bash(pkit new *)", "Bash(pkit:*)")


def test_subsumes_when_broader_covers_exact_command() -> None:
    """`Bash(pkit:*)` subsumes `Bash(pkit --help)`."""
    assert is_subsumed_by("Bash(pkit --help)", "Bash(pkit:*)")


def test_subsumes_when_broader_covers_colon_separated() -> None:
    """`Bash(git:*)` subsumes `Bash(git push --force-with-lease:*)`."""
    assert is_subsumed_by("Bash(git push --force-with-lease:*)", "Bash(git:*)")


def test_does_not_subsume_unrelated_command() -> None:
    """`Bash(git:*)` must NOT subsume `Bash(github-cli foo)`."""
    assert not is_subsumed_by("Bash(github-cli foo)", "Bash(git:*)")


def test_does_not_subsume_when_same_entry() -> None:
    """Self-subsumption is never True (would lose the only entry)."""
    assert not is_subsumed_by("Bash(pkit:*)", "Bash(pkit:*)")


def test_does_not_subsume_when_broader_is_not_wildcard() -> None:
    """`Bash(pwd)` is not a wildcard — can't subsume anything."""
    assert not is_subsumed_by("Bash(pwd /tmp)", "Bash(pwd)")


def test_does_not_subsume_skill_or_other_kinds() -> None:
    """v1 subsumption is Bash-only; Skill / Edit / etc. don't participate."""
    assert not is_subsumed_by("Skill(evidence-add)", "Skill(*)")
    assert not is_subsumed_by("Edit", "Edit:*")


# --- planning -------------------------------------------------------


def test_plan_with_no_redundancies_yields_empty_pairs() -> None:
    plan = plan_consolidation(["Bash(git:*)", "Bash(jq:*)", "Edit"])
    assert plan.pairs == ()
    assert plan.consolidated == ("Bash(git:*)", "Bash(jq:*)", "Edit")
    assert not plan.has_redundancies


def test_plan_removes_subsumed_entries() -> None:
    plan = plan_consolidation(
        [
            "Bash(pkit:*)",
            "Bash(pkit new *)",
            "Bash(pkit refs *)",
            "Bash(pkit --help)",
            "Bash(git:*)",  # unrelated, kept
        ]
    )
    assert plan.consolidated == ("Bash(pkit:*)", "Bash(git:*)")
    redundants = sorted(p.redundant for p in plan.pairs)
    assert redundants == [
        "Bash(pkit --help)",
        "Bash(pkit new *)",
        "Bash(pkit refs *)",
    ]
    assert all(p.subsumed_by == "Bash(pkit:*)" for p in plan.pairs)


def test_plan_preserves_order_of_kept_entries() -> None:
    plan = plan_consolidation(
        ["Bash(a:*)", "Bash(a foo)", "Bash(b:*)", "Bash(b bar)"]
    )
    assert plan.consolidated == ("Bash(a:*)", "Bash(b:*)")


def test_plan_handles_overlapping_broader_rules() -> None:
    """If two broader rules both subsume an entry, the first one wins (deterministic)."""
    plan = plan_consolidation(
        ["Bash(git:*)", "Bash(git push:*)", "Bash(git push --force *)"]
    )
    # Bash(git push --force *) is subsumed by Bash(git:*) AND Bash(git push:*).
    # Bash(git push:*) is also subsumed by Bash(git:*).
    # Both narrower entries get removed; only Bash(git:*) survives.
    assert plan.consolidated == ("Bash(git:*)",)
    assert len(plan.pairs) == 2


# --- file-level operations ------------------------------------------


def _write_settings(target_root: Path, allow: list[str], deny: list[str] | None = None) -> Path:
    """Write a `.claude/settings.json` with the given allow/deny lists."""
    claude_dir = target_root / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    data = {"permissions": {"allow": allow, "deny": deny or []}}
    settings_file = claude_dir / "settings.json"
    settings_file.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return settings_file


def test_detect_returns_none_when_no_settings_file(tmp_path: Path) -> None:
    assert detect_consolidation_opportunities(tmp_path) is None


def test_detect_returns_plan_with_redundancies(tmp_path: Path) -> None:
    _write_settings(
        tmp_path, ["Bash(pkit:*)", "Bash(pkit new *)", "Bash(git:*)"]
    )
    plan = detect_consolidation_opportunities(tmp_path)
    assert plan is not None
    assert plan.has_redundancies
    assert plan.consolidated == ("Bash(pkit:*)", "Bash(git:*)")


def test_apply_consolidation_preserves_deny(tmp_path: Path) -> None:
    _write_settings(
        tmp_path,
        allow=["Bash(pkit:*)", "Bash(pkit new *)"],
        deny=["Bash(sudo:*)", "Bash(rm -rf:*)"],
    )
    plan = detect_consolidation_opportunities(tmp_path)
    assert plan is not None
    apply_consolidation(tmp_path, plan)

    text = (tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8")
    data = json.loads(text)
    assert data["permissions"]["allow"] == ["Bash(pkit:*)"]
    # Deny list untouched.
    assert data["permissions"]["deny"] == ["Bash(sudo:*)", "Bash(rm -rf:*)"]


# --- multi-file behavior (settings.json + settings.local.json) ------


def _write_local_settings(target_root: Path, allow: list[str]) -> Path:
    """Write `.claude/settings.local.json`."""
    claude_dir = target_root / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    path = claude_dir / "settings.local.json"
    path.write_text(
        json.dumps({"permissions": {"allow": allow, "deny": []}}, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def test_detect_walks_both_settings_files(tmp_path: Path) -> None:
    """A redundancy where the broader rule is in settings.json and narrow in local."""
    _write_settings(tmp_path, allow=["Bash(pkit:*)"])
    _write_local_settings(tmp_path, allow=["Bash(pkit new *)", "Bash(pkit refs *)"])

    plan = detect_consolidation_opportunities(tmp_path)
    assert plan is not None
    assert plan.has_redundancies
    # Both narrow entries are flagged.
    redundants = sorted(p.redundant for p in plan.pairs)
    assert redundants == ["Bash(pkit new *)", "Bash(pkit refs *)"]
    # Both come from settings.local.json.
    assert all(p.source_file == tmp_path / ".claude" / "settings.local.json" for p in plan.pairs)


def test_detect_handles_broader_in_local_narrow_in_main(tmp_path: Path) -> None:
    """Subsumption works regardless of which file holds the broader rule."""
    _write_settings(tmp_path, allow=["Bash(pkit new *)", "Bash(git push --force *)"])
    _write_local_settings(tmp_path, allow=["Bash(pkit:*)", "Bash(git:*)"])

    plan = detect_consolidation_opportunities(tmp_path)
    assert plan is not None
    # Both narrow entries in settings.json are redundant.
    assert {p.redundant for p in plan.pairs} == {"Bash(pkit new *)", "Bash(git push --force *)"}
    assert all(p.source_file == tmp_path / ".claude" / "settings.json" for p in plan.pairs)


def test_detect_emits_pair_per_file_when_entry_in_both(tmp_path: Path) -> None:
    """The same redundant entry in both files → two pairs (one per occurrence)."""
    _write_settings(tmp_path, allow=["Bash(pkit:*)", "Bash(pkit new *)"])
    _write_local_settings(tmp_path, allow=["Bash(pkit new *)"])

    plan = detect_consolidation_opportunities(tmp_path)
    assert plan is not None
    assert len(plan.pairs) == 2
    sources = sorted(p.source_file.name for p in plan.pairs if p.source_file is not None)
    assert sources == ["settings.json", "settings.local.json"]


def test_apply_removes_from_each_affected_file(tmp_path: Path) -> None:
    """Apply rewrites every affected file; untouched files stay byte-identical."""
    _write_settings(tmp_path, allow=["Bash(pkit:*)", "Bash(pkit new *)"])
    _write_local_settings(tmp_path, allow=["Bash(pkit refs *)", "Bash(git:*)"])

    plan = detect_consolidation_opportunities(tmp_path)
    assert plan is not None
    modified = apply_consolidation(tmp_path, plan)
    assert len(modified) == 2

    main_data = json.loads(
        (tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8")
    )
    local_data = json.loads(
        (tmp_path / ".claude" / "settings.local.json").read_text(encoding="utf-8")
    )
    assert main_data["permissions"]["allow"] == ["Bash(pkit:*)"]
    assert local_data["permissions"]["allow"] == ["Bash(git:*)"]


def test_detect_returns_none_when_neither_file_exists(tmp_path: Path) -> None:
    assert detect_consolidation_opportunities(tmp_path) is None


def test_detect_works_when_only_local_exists(tmp_path: Path) -> None:
    """settings.local.json on its own is enough — no settings.json required."""
    _write_local_settings(tmp_path, allow=["Bash(pkit:*)", "Bash(pkit new *)"])
    plan = detect_consolidation_opportunities(tmp_path)
    assert plan is not None
    assert plan.has_redundancies
    assert plan.pairs[0].source_file == tmp_path / ".claude" / "settings.local.json"


# --- CLI command ----------------------------------------------------


@pytest.fixture
def adopter_with_redundancies(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A project tree with `.pkit/`, `.claude/settings.json` containing redundancies."""
    (tmp_path / ".pkit").mkdir()
    _write_settings(
        tmp_path,
        allow=["Bash(pkit:*)", "Bash(pkit new *)", "Bash(pkit refs *)", "Bash(git:*)"],
    )
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_cli_consolidate_dry_run_does_not_write(adopter_with_redundancies: Path) -> None:
    original = (adopter_with_redundancies / ".claude" / "settings.json").read_text(encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(main, ["settings", "consolidate", "--dry-run"])
    assert result.exit_code == 0
    assert "2 redundant entry(ies)" in result.output
    assert "dry-run" in result.output
    # File unchanged.
    assert (adopter_with_redundancies / ".claude" / "settings.json").read_text(encoding="utf-8") == original


def test_cli_consolidate_with_yes_writes_immediately(adopter_with_redundancies: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["settings", "consolidate", "--yes"])
    assert result.exit_code == 0
    assert "Removed 2 entry(ies)" in result.output

    data = json.loads(
        (adopter_with_redundancies / ".claude" / "settings.json").read_text(encoding="utf-8")
    )
    assert data["permissions"]["allow"] == ["Bash(pkit:*)", "Bash(git:*)"]


def test_cli_consolidate_prompt_no_cancels(adopter_with_redundancies: Path) -> None:
    original = (adopter_with_redundancies / ".claude" / "settings.json").read_text(encoding="utf-8")
    runner = CliRunner()
    # Type "n" at the confirm prompt.
    result = runner.invoke(main, ["settings", "consolidate"], input="n\n")
    assert result.exit_code == 0
    assert "cancelled" in result.output
    # File unchanged.
    assert (adopter_with_redundancies / ".claude" / "settings.json").read_text(encoding="utf-8") == original


def test_cli_consolidate_no_redundancies_is_noop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / ".pkit").mkdir()
    _write_settings(tmp_path, allow=["Bash(pkit:*)", "Bash(git:*)"])
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["settings", "consolidate"])
    assert result.exit_code == 0
    assert "no redundant entries" in result.output


def test_cli_consolidate_no_settings_file_is_noop(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / ".pkit").mkdir()
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["settings", "consolidate"])
    assert result.exit_code == 0
    assert "no .claude/settings.json or .claude/settings.local.json" in result.output


def test_cli_consolidate_dry_run_groups_pairs_by_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Dry-run output groups redundant entries by their source file."""
    (tmp_path / ".pkit").mkdir()
    _write_settings(tmp_path, allow=["Bash(pkit:*)", "Bash(pkit new *)"])
    _write_local_settings(tmp_path, allow=["Bash(pkit refs *)"])
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(main, ["settings", "consolidate", "--dry-run"])
    assert result.exit_code == 0
    assert "2 redundant entry(ies) across 2 file(s)" in result.output
    assert ".claude/settings.json" in result.output
    assert ".claude/settings.local.json" in result.output
    assert "Bash(pkit new *)" in result.output
    assert "Bash(pkit refs *)" in result.output


def test_cli_consolidate_writes_to_both_files_with_yes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--yes commits the cleanup to every affected file."""
    (tmp_path / ".pkit").mkdir()
    _write_settings(tmp_path, allow=["Bash(pkit:*)", "Bash(pkit new *)"])
    _write_local_settings(tmp_path, allow=["Bash(pkit refs *)", "Bash(git:*)"])
    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(main, ["settings", "consolidate", "--yes"])
    assert result.exit_code == 0

    main_data = json.loads((tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8"))
    local_data = json.loads(
        (tmp_path / ".claude" / "settings.local.json").read_text(encoding="utf-8")
    )
    assert main_data["permissions"]["allow"] == ["Bash(pkit:*)"]
    assert local_data["permissions"]["allow"] == ["Bash(git:*)"]
