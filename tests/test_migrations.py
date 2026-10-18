"""Tests for the shared migration-runner helpers (per COR-010)."""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from project_kit import __version__
from project_kit import migrations as migrations_mod
from project_kit.cli import main as pkit_main
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
    with pytest.raises(click.ClickException, match=r"major\.minor\.patch"):
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
    script1.write_text(f'#!/usr/bin/env bash\necho "$ROOT" >> "{trace}"\n', encoding="utf-8")
    script1.chmod(0o755)
    script2 = tmp_path / "002.sh"
    script2.write_text(f'#!/usr/bin/env bash\necho "$ROOT" >> "{trace}"\n', encoding="utf-8")
    script2.chmod(0o755)

    execute_migration_scripts([script1, script2], tmp_path, label="test")
    lines = trace.read_text(encoding="utf-8").strip().splitlines()
    assert lines == [str(tmp_path), str(tmp_path)]


def test_execute_scripts_halts_on_first_failure(tmp_path: Path) -> None:
    """A non-zero exit raises; subsequent scripts do not run."""
    trace = tmp_path / "trace.txt"
    pass_script = tmp_path / "001.sh"
    pass_script.write_text(f'#!/usr/bin/env bash\necho "pass" >> "{trace}"\n', encoding="utf-8")
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
    / ".pkit"
    / "migrations"
    / "backbone"
    / "1.54.0"
    / "001-seed-architect-overlay-categories.sh"
)
_OLD_OVERLAY = (
    "# adopter overlay\n"
    "workflow-docs:\n  - README.md\n\n"
    "project-root-docs:\n  - docs/team.md\n"  # a customised value to prove preservation
)


def _run_migration(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(_MIGRATION_154)],
        env={"ROOT": str(root), "PATH": __import__("os").environ["PATH"]},
        capture_output=True,
        text=True,
        check=False,
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
    assert overlay.read_text() == after_first  # no duplicate appends


def test_migration_skips_when_no_overlay(tmp_path: Path) -> None:
    (tmp_path / ".pkit" / "agents" / "project").mkdir(parents=True)
    result = _run_migration(tmp_path)
    assert result.returncode == 0
    assert "no .pkit/agents/project/overlay.yaml" in result.stdout


# ---- the runner's `pkit` and the migration marker (ADR-065 point 14, #1652) ----

_DECOY = '#!/bin/sh\necho "$0 $*" >> "{log}"\nexit 1\n'


def _pinned_project(root: Path) -> Path:
    """A project that pins a release no pkit here is: `.pkit/manifest.yaml` and
    `.pkit/version-pin` = 0.0.1, so a routed `pkit` would run `uvx …@v0.0.1`."""
    (root / ".pkit").mkdir(parents=True)
    (root / ".pkit" / "manifest.yaml").write_text(
        f"schema_version: 1\nbackbone_version: {__version__}\n"
        f"completed_version: {__version__}\ncomponents: []\n",
        encoding="utf-8",
    )
    (root / ".pkit" / "version-pin").write_text("0.0.1\n", encoding="utf-8")
    return root


def _decoys(bin_dir: Path, log: Path) -> Path:
    """A `pkit` and a `uvx` that each log their run and exit 1."""
    bin_dir.mkdir(parents=True)
    for name in ("pkit", "uvx"):
        decoy = bin_dir / name
        decoy.write_text(_DECOY.format(log=log), encoding="utf-8")
        decoy.chmod(0o755)
    return bin_dir


def _script(parent: Path, body: str) -> Path:
    script = parent / "001-probe.sh"
    script.write_text(f"#!/usr/bin/env bash\nset -euo pipefail\n{body}", encoding="utf-8")
    script.chmod(0o755)
    return script


@pytest.fixture
def decoyed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path, Path]:
    """A pinned project, and a decoy `pkit` and `uvx` first on the inherited
    `PATH`. Returns the project, the decoys' log and the folder for scripts."""
    project = _pinned_project(tmp_path / "project")
    log = tmp_path / "decoys.log"
    bin_dir = _decoys(tmp_path / "decoys", log)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    return project, log, scripts


def test_a_bare_pkit_in_a_migration_reaches_the_running_pkit(
    decoyed: tuple[Path, Path, Path],
) -> None:
    """Under a pin and behind a decoy `pkit` and `uvx`, a script's bare `pkit`,
    and one in a process it starts, answer with the running pkit's version, from
    the project folder of the runner; neither decoy runs, and the folder is gone."""
    project, log, scripts = decoyed
    script = _script(
        scripts,
        'pkit --version > "$ROOT/direct"\n'
        "sh -c 'pkit --version' > \"$ROOT/nested\"\n"
        'command -v pkit > "$ROOT/where"\n'
        'printf %s "$PKIT_MIGRATION" > "$ROOT/marker"\n',
    )

    execute_migration_scripts([script], project, label="test")

    expected = f"pkit, version {__version__}"
    assert (project / "direct").read_text(encoding="utf-8").strip() == expected
    assert (project / "nested").read_text(encoding="utf-8").strip() == expected
    where = Path((project / "where").read_text(encoding="utf-8").strip())
    assert where.parent.parent == project / migrations_mod.RUNNER_PARENT
    assert (project / "marker").read_text(encoding="utf-8") == "1"
    assert not log.exists(), log.read_text(encoding="utf-8")
    assert not where.parent.exists()
    assert not (project / migrations_mod.RUNNER_PARENT).exists()


def test_the_console_script_in_the_same_project_reaches_the_decoy(
    decoyed: tuple[Path, Path, Path],
) -> None:
    """The negative control: outside the runner, the installed `pkit` routes by
    the pin and runs the decoy `uvx`, so the test above proves the runner's `pkit`."""
    project, log, _ = decoyed
    console = shutil.which("pkit", path=str(Path(sys.executable).parent))
    if console is None:
        pytest.skip("no installed `pkit` console script beside this interpreter")

    subprocess.run([console, "--version"], cwd=project, capture_output=True, text=True, check=False)

    assert "uvx" in log.read_text(encoding="utf-8")


def test_a_failing_migration_leaves_no_folder(decoyed: tuple[Path, Path, Path]) -> None:
    project, _, scripts = decoyed
    script = _script(scripts, 'command -v pkit > "$ROOT/where"\nexit 3\n')

    with pytest.raises(click.ClickException, match="exited with status 3"):
        execute_migration_scripts([script], project, label="test")

    where = Path((project / "where").read_text(encoding="utf-8").strip())
    assert not where.parent.exists()
    assert not (project / migrations_mod.RUNNER_PARENT).exists()


def test_a_project_package_of_the_same_name_does_not_shadow_the_running_pkit(
    decoyed: tuple[Path, Path, Path],
) -> None:
    """`-P` keeps the project's root off the import path: a `project_kit/` there
    that raises on import is never imported."""
    project, _, scripts = decoyed
    shadow = project / "project_kit"
    shadow.mkdir()
    (shadow / "__init__.py").write_text("raise RuntimeError('shadowed')\n", encoding="utf-8")
    (shadow / "__main__.py").write_text("raise RuntimeError('shadowed')\n", encoding="utf-8")
    script = _script(scripts, 'pkit --version > "$ROOT/direct"\n')

    execute_migration_scripts([script], project, label="test")

    assert (project / "direct").read_text(encoding="utf-8").strip() == (
        f"pkit, version {__version__}"
    )


def test_a_runner_pkit_that_cannot_run_stops_before_any_script(
    decoyed: tuple[Path, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    project, _, scripts = decoyed
    script = _script(scripts, 'touch "$ROOT/ran"\n')
    monkeypatch.setattr(sys, "executable", str(project / "no-such-interpreter"))

    with pytest.raises(click.ClickException) as raised:
        execute_migration_scripts([script], project, label="test")

    message = raised.value.format_message()
    assert "no test migration ran" in message
    assert "ADR-065 point 14" in message
    assert migrations_mod.RUNNER_PARENT in message
    assert "TMPDIR" in message
    assert not (project / "ran").exists()
    assert not (project / migrations_mod.RUNNER_PARENT).exists()


@pytest.mark.parametrize("how", ["folder-blocked", "not-runnable", "others-can-write", "a-link"])
def test_the_runner_falls_back_to_the_temporary_folder(
    decoyed: tuple[Path, Path, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    how: str,
) -> None:
    """Where the project folder cannot be made, is not one only this user can
    write, or its `pkit` cannot run, the runner's `pkit` lies in the temporary
    folder, and is removed from there too. A `pkit` that cannot run is not
    excused by another `pkit` further on the `PATH` that gives the same version."""
    project, log, scripts = decoyed
    temporary = tmp_path / "temporary"
    temporary.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(temporary))
    parent = project / migrations_mod.RUNNER_PARENT
    if how == "folder-blocked":
        parent.write_text("a file where the folder would be\n", encoding="utf-8")
    elif how == "others-can-write":
        parent.mkdir()
        parent.chmod(0o777)
    elif how == "a-link":
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir(mode=0o700)
        parent.symlink_to(elsewhere, target_is_directory=True)
    else:
        # A folder that forbids running files, as a noexec mount does, behind a
        # `pkit` on the operator's `PATH` that answers with the same version.
        same = tmp_path / "same-version"
        same.mkdir()
        impostor = same / "pkit"
        impostor.write_text(
            f'#!/bin/sh\necho impostor >> "{log}"\necho "pkit, version {__version__}"\n',
            encoding="utf-8",
        )
        impostor.chmod(0o755)
        monkeypatch.setenv("PATH", f"{same}{os.pathsep}{os.environ['PATH']}")
        make = migrations_mod._make_runner_folder

        def _not_runnable_in_the_project(where: Path | None) -> Path:
            folder = make(where)
            if where is not None:
                (folder / "pkit").chmod(0o644)
            return folder

        monkeypatch.setattr(migrations_mod, "_make_runner_folder", _not_runnable_in_the_project)
    script = _script(scripts, 'command -v pkit > "$ROOT/where"\npkit --version > "$ROOT/direct"\n')

    execute_migration_scripts([script], project, label="test")

    where = Path((project / "where").read_text(encoding="utf-8").strip())
    assert where.parent.parent == temporary
    assert (project / "direct").read_text(encoding="utf-8").strip() == (
        f"pkit, version {__version__}"
    )
    assert not log.exists(), log.read_text(encoding="utf-8")
    assert list(temporary.iterdir()) == []
    if how == "not-runnable":
        assert not parent.exists()


def test_a_runner_pkit_of_another_version_stops_before_any_script(
    decoyed: tuple[Path, Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The probe compares the answer with the running pkit's version: an answer
    with another version, in both places, stops the run."""
    project, _, scripts = decoyed
    script = _script(scripts, 'touch "$ROOT/ran"\n')
    monkeypatch.setattr(migrations_mod, "__version__", "0.0.0")

    with pytest.raises(click.ClickException) as raised:
        execute_migration_scripts([script], project, label="test")

    message = raised.value.format_message()
    assert f"said 'pkit, version {__version__}', not 0.0.0" in message
    assert not (project / "ran").exists()
    assert not (project / migrations_mod.RUNNER_PARENT).exists()


_INSTALLATION_CHANGING = [
    ["init", "--here", "--yes"],
    ["sync"],
    ["sync", "--dry-run"],
    ["merge"],
    ["upgrade"],
    ["upgrade", "--dry-run"],
    ["pin"],
    ["pin", "9.9.9"],
    ["unpin"],
    ["agents", "adopt", "architect", "--yes"],
    ["agents", "reconcile", "--write"],
    ["capabilities", "install", "evidence"],
    ["capabilities", "install", "evidence", "--dry-run"],
    ["capabilities", "upgrade", "evidence"],
    ["capabilities", "register", "evidence"],
    ["capabilities", "uninstall", "evidence", "--yes"],
]


@pytest.mark.parametrize("argv", _INSTALLATION_CHANGING, ids=" ".join)
def test_a_command_that_changes_the_installation_refuses_under_the_marker(
    argv: list[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = _pinned_project(tmp_path / "project")
    before = sorted(p.relative_to(project) for p in project.rglob("*"))
    monkeypatch.chdir(project)

    result = CliRunner().invoke(pkit_main, argv, env={migrations_mod.MIGRATION_ENV: "1"})

    assert result.exit_code == 1, result.output
    assert f"refusing to run `pkit {argv[0]}" in result.output
    assert f"inside a migration ({migrations_mod.MIGRATION_ENV} is set)" in result.output
    assert "ADR-065 point 14" in result.output
    assert sorted(p.relative_to(project) for p in project.rglob("*")) == before


_READING = [
    ["--version"],
    ["version"],
    ["status"],
    ["agents", "reconcile"],
    ["capabilities", "list"],
    ["capabilities", "project-rule-set", "software-analysis", "--json"],
]


@pytest.mark.parametrize("argv", _READING, ids=" ".join)
def test_a_reading_command_runs_under_the_marker(
    argv: list[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = _pinned_project(tmp_path / "project")
    monkeypatch.chdir(project)

    result = CliRunner().invoke(pkit_main, argv, env={migrations_mod.MIGRATION_ENV: "1"})

    assert "inside a migration" not in result.output
    assert "ADR-065 point 14" not in result.output


def test_an_empty_marker_refuses_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = _pinned_project(tmp_path / "project")
    monkeypatch.chdir(project)

    result = CliRunner().invoke(pkit_main, ["unpin"], env={migrations_mod.MIGRATION_ENV: ""})

    assert result.exit_code == 0, result.output
    assert not (project / ".pkit" / "version-pin").exists()
