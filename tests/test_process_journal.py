"""The journal-logging setting reader (COR-033 point 7): forgiving reads (COR-048
point 4) and what the setting means for the ignore rules."""

from __future__ import annotations

from pathlib import Path

import pytest

from project_kit.process_journal import (
    JOURNAL_GLOB,
    JournalSettings,
    read_settings,
    runtime_ignore_patterns,
    settings_from,
)


def _write(root: Path, text: str) -> None:
    path = root / ".pkit" / "project" / "config.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_absent_file_reads_as_off(tmp_path: Path) -> None:
    assert read_settings(tmp_path) == JournalSettings(enabled=False, committed=False)


@pytest.mark.parametrize(
    "config",
    [
        {},
        {"process": None},
        {"process": "on"},
        {"process": {"journal": True}},
        {"process": {"journal": {"enabled": "true", "committed": "yes"}}},
        {"process": {"journal": {"enabled": 1}}},
    ],
)
def test_anything_but_booleans_reads_as_the_default(config: dict) -> None:
    assert settings_from(config) == JournalSettings()


def test_booleans_are_read(tmp_path: Path) -> None:
    _write(tmp_path, "process:\n  journal:\n    enabled: true\n    committed: true\n")
    assert read_settings(tmp_path) == JournalSettings(enabled=True, committed=True)


def test_an_unparsable_file_reads_as_off(tmp_path: Path) -> None:
    _write(tmp_path, "process: [unclosed\n")
    assert read_settings(tmp_path) == JournalSettings()


@pytest.mark.parametrize(
    ("settings", "ignored"),
    [
        (JournalSettings(enabled=False, committed=False), True),
        (JournalSettings(enabled=False, committed=True), True),
        (JournalSettings(enabled=True, committed=False), True),
        (JournalSettings(enabled=True, committed=True), False),
    ],
)
def test_journals_are_ignored_unless_logged_and_committed(
    settings: JournalSettings, ignored: bool
) -> None:
    assert settings.ignored is ignored


def test_the_ignore_pattern_follows_the_setting(tmp_path: Path) -> None:
    assert runtime_ignore_patterns(tmp_path) == [JOURNAL_GLOB]
    _write(tmp_path, "process:\n  journal:\n    enabled: true\n    committed: true\n")
    assert runtime_ignore_patterns(tmp_path) == []
