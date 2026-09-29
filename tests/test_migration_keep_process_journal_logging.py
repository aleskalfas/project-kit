"""Backbone migration 1.150.0/001-keep-process-journal-logging.sh (COR-033 point 7).

Journal logging became opt-in and off by default. The migration keeps it on for
a project that already kept journals, so an upgrade does not silently change its
behaviour:

- no journals → nothing written (the new default, off, applies);
- journals, none tracked → `enabled: true`, `committed: false`;
- journals, some tracked → `enabled: true`, `committed: true`, and the journal
  line the pre-migration render left in `.pkit/.gitignore` is removed;
- a `process:` block already declared → left alone;
- a second run changes nothing.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from ruamel.yaml import YAML

from project_kit import process_journal, project_config

REPO_ROOT = Path(__file__).resolve().parent.parent
MIGRATION = (
    REPO_ROOT
    / ".pkit"
    / "migrations"
    / "backbone"
    / "1.150.0"
    / "001-keep-process-journal-logging.sh"
)
CONFIG_SCHEMA = REPO_ROOT / ".pkit" / "schemas" / "backbone" / "config.schema.json"
JOURNAL = Path(".pkit/capabilities/project-management/project/process/issue-lifecycle/42.journal.jsonl")
RENDERED_LINE = "capabilities/*/project/process/**/*.journal.jsonl"
GITIGNORE_BEFORE = (
    "# pkit-owned — rendered\n\n**/__pycache__/\n"
    f"{RENDERED_LINE}\n"
    "capabilities/project-management/project/instance/*.json\n"
)


def _run(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(MIGRATION)],
        capture_output=True,
        text=True,
        check=False,
        env={"ROOT": str(root), "PATH": "/usr/bin:/bin:/usr/local/bin"},
    )


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _project(root: Path, *, journal: bool, tracked: bool = False) -> Path:
    """A git repository with the rendered `.pkit/.gitignore`, and optionally one
    process journal — tracked or not."""
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@t")
    _git(root, "config", "user.name", "t")
    (root / ".pkit").mkdir()
    (root / ".pkit" / ".gitignore").write_text(GITIGNORE_BEFORE, encoding="utf-8")
    if journal:
        path = root / JOURNAL
        path.parent.mkdir(parents=True)
        path.write_text('{"to": "done"}\n', encoding="utf-8")
        if tracked:
            _git(root, "add", "-f", str(JOURNAL))
            _git(root, "commit", "-qm", "journal")
    return root


def _config_path(root: Path) -> Path:
    return root / ".pkit" / "project" / "config.yaml"


def _config(root: Path) -> dict:
    return YAML(typ="safe").load(_config_path(root).read_text(encoding="utf-8")) or {}


def _assert_valid(root: Path) -> None:
    schema = json.loads(CONFIG_SCHEMA.read_text(encoding="utf-8"))
    errors = list(project_config.schema_validator(schema).iter_errors(_config(root)))
    assert errors == []


def test_no_journals_writes_nothing(tmp_path: Path) -> None:
    root = _project(tmp_path, journal=False)

    result = _run(root)

    assert result.returncode == 0, result.stderr
    assert "[skip]" in result.stdout
    assert not _config_path(root).exists()


def test_clone_local_journals_keep_logging_on_uncommitted(tmp_path: Path) -> None:
    root = _project(tmp_path, journal=True)

    result = _run(root)

    assert result.returncode == 0, result.stderr
    assert _config(root)["process"] == {"journal": {"enabled": True, "committed": False}}
    assert process_journal.read_settings(root) == process_journal.JournalSettings(True, False)
    assert _config_path(root).read_text(encoding="utf-8").startswith(
        project_config.EDITOR_DIRECTIVE
    )
    assert (root / ".pkit" / ".gitignore").read_text(encoding="utf-8") == GITIGNORE_BEFORE
    _assert_valid(root)


def test_tracked_journals_keep_logging_on_committed(tmp_path: Path) -> None:
    root = _project(tmp_path, journal=True, tracked=True)

    result = _run(root)

    assert result.returncode == 0, result.stderr
    assert _config(root)["process"] == {"journal": {"enabled": True, "committed": True}}
    gitignore = (root / ".pkit" / ".gitignore").read_text(encoding="utf-8")
    assert RENDERED_LINE not in gitignore
    assert "capabilities/project-management/project/instance/*.json" in gitignore
    _assert_valid(root)


def test_an_existing_configuration_keeps_its_content(tmp_path: Path) -> None:
    root = _project(tmp_path, journal=True)
    _config_path(root).parent.mkdir(parents=True)
    # No trailing newline: the appended block must still start on its own line.
    _config_path(root).write_text("# ours\nname: example\nfriction:\n  mode: warning", encoding="utf-8")

    assert _run(root).returncode == 0

    config = _config(root)
    assert config["name"] == "example"
    assert config["friction"] == {"mode": "warning"}
    assert config["process"] == {"journal": {"enabled": True, "committed": False}}
    assert _config_path(root).read_text(encoding="utf-8").startswith("# ours\n")
    _assert_valid(root)


def test_a_declared_process_block_is_left_alone(tmp_path: Path) -> None:
    root = _project(tmp_path, journal=True)
    _config_path(root).parent.mkdir(parents=True)
    declared = "process:\n  journal:\n    enabled: false\n"
    _config_path(root).write_text(declared, encoding="utf-8")

    result = _run(root)

    assert result.returncode == 0, result.stderr
    assert "[skip]" in result.stdout
    assert _config_path(root).read_text(encoding="utf-8") == declared


def test_second_run_changes_nothing(tmp_path: Path) -> None:
    root = _project(tmp_path, journal=True, tracked=True)
    assert _run(root).returncode == 0
    config_after_first = _config_path(root).read_text(encoding="utf-8")
    gitignore_after_first = (root / ".pkit" / ".gitignore").read_text(encoding="utf-8")

    second = _run(root)

    assert second.returncode == 0, second.stderr
    assert "[skip]" in second.stdout
    assert _config_path(root).read_text(encoding="utf-8") == config_after_first
    assert (root / ".pkit" / ".gitignore").read_text(encoding="utf-8") == gitignore_after_first


def test_outside_a_git_repository_journals_count_as_uncommitted(tmp_path: Path) -> None:
    path = tmp_path / JOURNAL
    path.parent.mkdir(parents=True)
    path.write_text("{}\n", encoding="utf-8")

    result = _run(tmp_path)

    assert result.returncode == 0, result.stderr
    assert _config(tmp_path)["process"] == {"journal": {"enabled": True, "committed": False}}
