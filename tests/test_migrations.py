"""Tests for the shared migration-runner helpers (per COR-010)."""

from __future__ import annotations

from pathlib import Path

import click
import pytest

from project_kit.migrations import (
    execute_migration_scripts,
    parse_version_tuple,
    pending_migration_scripts,
    report_pending_migrations,
)


def test_parse_version_tuple_happy_path() -> None:
    assert parse_version_tuple("1.2.3") == (1, 2, 3)
    assert parse_version_tuple("0.0.0") == (0, 0, 0)
    assert parse_version_tuple("10.20.30") == (10, 20, 30)


def test_parse_version_tuple_rejects_malformed() -> None:
    with pytest.raises(click.ClickException, match="major.minor.patch"):
        parse_version_tuple("1.2")
    with pytest.raises(click.ClickException, match="non-integer"):
        parse_version_tuple("a.b.c")


def _stage_script(parent: Path, version_dir: str, name: str, body: str) -> Path:
    """Drop an executable script under <parent>/<version_dir>/<name>."""
    target = parent / version_dir
    target.mkdir(parents=True, exist_ok=True)
    script = target / name
    script.write_text(body, encoding="utf-8")
    script.chmod(0o755)
    return script


def test_pending_scripts_returns_empty_when_root_missing(tmp_path: Path) -> None:
    assert pending_migration_scripts(tmp_path / "nope", "0.1.0", "0.2.0") == []


def test_pending_scripts_respects_window(tmp_path: Path) -> None:
    """(installed, target] — installed minor is exclusive; target is inclusive."""
    root = tmp_path / "migrations"
    for minor in ("0.1.0", "0.2.0", "0.3.0", "0.4.0", "0.5.0"):
        _stage_script(root, minor, "001-a.sh", "#!/usr/bin/env bash\nexit 0\n")

    scripts = pending_migration_scripts(root, "0.2.0", "0.4.0")
    versions = [s.parent.name for s in scripts]
    assert versions == ["0.3.0", "0.4.0"]


def test_pending_scripts_unknown_installed_includes_all(tmp_path: Path) -> None:
    root = tmp_path / "migrations"
    for minor in ("0.1.0", "0.2.0"):
        _stage_script(root, minor, "001-a.sh", "#!/usr/bin/env bash\nexit 0\n")
    scripts = pending_migration_scripts(root, None, "0.2.0")
    versions = [s.parent.name for s in scripts]
    assert versions == ["0.1.0", "0.2.0"]


def test_pending_scripts_orders_by_nnn_within_version(tmp_path: Path) -> None:
    root = tmp_path / "migrations"
    _stage_script(root, "0.2.0", "002-second.sh", "#!/usr/bin/env bash\nexit 0\n")
    _stage_script(root, "0.2.0", "001-first.sh", "#!/usr/bin/env bash\nexit 0\n")
    scripts = pending_migration_scripts(root, "0.1.0", "0.2.0")
    assert [s.name for s in scripts] == ["001-first.sh", "002-second.sh"]


def test_pending_scripts_ignores_non_versioned_dirs(tmp_path: Path) -> None:
    """Directories whose name isn't `X.Y.0` get skipped."""
    root = tmp_path / "migrations"
    (root / "README.md").parent.mkdir(parents=True)
    (root / "junk").mkdir()
    _stage_script(root, "0.1.0", "001-a.sh", "#!/usr/bin/env bash\nexit 0\n")
    scripts = pending_migration_scripts(root, None, "0.1.0")
    assert len(scripts) == 1
    assert scripts[0].parent.name == "0.1.0"


def test_execute_scripts_runs_each_with_root_env_var(tmp_path: Path) -> None:
    """Every script sees ROOT=<target_root> in its environment."""
    trace = tmp_path / "trace.txt"
    script1 = tmp_path / "001.sh"
    script1.write_text(
        f'#!/usr/bin/env bash\necho "$ROOT" >> "{trace}"\n', encoding="utf-8"
    )
    script1.chmod(0o755)
    script2 = tmp_path / "002.sh"
    script2.write_text(
        f'#!/usr/bin/env bash\necho "$ROOT" >> "{trace}"\n', encoding="utf-8"
    )
    script2.chmod(0o755)

    execute_migration_scripts([script1, script2], tmp_path, label="test")
    lines = trace.read_text(encoding="utf-8").strip().splitlines()
    assert lines == [str(tmp_path), str(tmp_path)]


def test_execute_scripts_halts_on_first_failure(tmp_path: Path) -> None:
    """A non-zero exit raises; subsequent scripts do not run."""
    trace = tmp_path / "trace.txt"
    pass_script = tmp_path / "001.sh"
    pass_script.write_text(
        f'#!/usr/bin/env bash\necho "pass" >> "{trace}"\n', encoding="utf-8"
    )
    pass_script.chmod(0o755)
    fail_script = tmp_path / "002.sh"
    fail_script.write_text("#!/usr/bin/env bash\nexit 7\n", encoding="utf-8")
    fail_script.chmod(0o755)
    not_run_script = tmp_path / "003.sh"
    not_run_script.write_text(
        f'#!/usr/bin/env bash\necho "ran-third" >> "{trace}"\n', encoding="utf-8"
    )
    not_run_script.chmod(0o755)

    with pytest.raises(click.ClickException, match="exited with status 7"):
        execute_migration_scripts(
            [pass_script, fail_script, not_run_script], tmp_path, label="test"
        )

    # The first script ran, the third did not.
    content = trace.read_text(encoding="utf-8")
    assert "pass" in content
    assert "ran-third" not in content


def test_report_pending_migrations_dry_run_prints_plan(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    script = _stage_script(
        tmp_path / "migrations", "0.2.0", "001-a.sh", "#!/usr/bin/env bash\nexit 0\n"
    )
    report_pending_migrations(
        [script],
        label="backbone",
        installed_version="0.1.0",
        target_version="0.2.0",
        dry_run=True,
        label_rel_to=tmp_path / "migrations",
    )
    captured = capsys.readouterr()
    assert "would run 1 migration(s)" in captured.out
    assert "backbone" in captured.out
    assert "0.1.0 -> v0.2.0" in captured.out


# ---- migration 1.54.0/001 seed-architect-overlay-categories (#288) -----------

import subprocess  # noqa: E402

_MIGRATION_154 = (
    Path(__file__).resolve().parents[1]
    / ".pkit" / "migrations" / "backbone" / "1.54.0"
    / "001-seed-architect-overlay-categories.sh"
)
_OLD_OVERLAY = (
    "# adopter overlay\n"
    "workflow-docs:\n  - README.md\n\n"
    "project-root-docs:\n  - docs/team.md\n"   # a customised value to prove preservation
)


def _run_migration(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(_MIGRATION_154)],
        env={"ROOT": str(root), "PATH": __import__("os").environ["PATH"]},
        capture_output=True, text=True, check=False,
    )


def _load_overlay(root: Path) -> dict:
    from ruamel.yaml import YAML
    p = root / ".pkit" / "agents" / "project" / "overlay.yaml"
    return YAML(typ="safe").load(p.read_text())


def test_migration_seeds_missing_categories_preserving_existing(tmp_path: Path) -> None:
    overlay = tmp_path / ".pkit" / "agents" / "project" / "overlay.yaml"
    overlay.parent.mkdir(parents=True)
    overlay.write_text(_OLD_OVERLAY, encoding="utf-8")

    result = _run_migration(tmp_path)
    assert result.returncode == 0, result.stderr
    assert "[add] architecture-docs" in result.stdout
    assert "[add] adr-records" in result.stdout

    doc = _load_overlay(tmp_path)
    # New categories present with the install-seed defaults.
    assert doc["architecture-docs"] == ["README.md"]
    assert doc["adr-records"] == ["docs/architecture/decisions/"]
    # Existing entries (incl. the customised value) untouched.
    assert doc["workflow-docs"] == ["README.md"]
    assert doc["project-root-docs"] == ["docs/team.md"]


def test_migration_is_idempotent(tmp_path: Path) -> None:
    overlay = tmp_path / ".pkit" / "agents" / "project" / "overlay.yaml"
    overlay.parent.mkdir(parents=True)
    overlay.write_text(_OLD_OVERLAY, encoding="utf-8")

    _run_migration(tmp_path)
    after_first = overlay.read_text()
    second = _run_migration(tmp_path)
    assert second.returncode == 0
    assert "already migrated" in second.stdout
    assert overlay.read_text() == after_first   # no duplicate appends


def test_migration_skips_when_no_overlay(tmp_path: Path) -> None:
    (tmp_path / ".pkit" / "agents" / "project").mkdir(parents=True)
    result = _run_migration(tmp_path)
    assert result.returncode == 0
    assert "no .pkit/agents/project/overlay.yaml" in result.stdout
