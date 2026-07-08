"""Integration tests for `.pkit/adapters/claude-code/deploy-skills.sh`.

The script is exercised against synthesised kit layouts in tmp directories.
No mocking — the script symlinks canonical skill files from `.pkit/skills/`
(and installed capabilities) into `.claude/skills/<name>/SKILL.md`.

The load-bearing case here is #537: a composite skill folder mid-build (per
COR-020) with sub-procedures but no `<name>/<name>.md` dispatcher must NOT
abort the whole run under `set -euo pipefail`. It must skip that one skill
loudly, deploy valid siblings, and exit 0.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


SOURCE_REPO = Path(__file__).resolve().parents[1]
DEPLOY_SCRIPT = SOURCE_REPO / ".pkit" / "adapters" / "claude-code" / "deploy-skills.sh"


@pytest.fixture
def mock_kit(tmp_path: Path) -> Path:
    """Stage a minimal kit layout under tmp_path with the deploy script copied in.

    Returns the project root (the directory containing `.pkit/`).
    """
    adapter_dir = tmp_path / ".pkit" / "adapters" / "claude-code"
    adapter_dir.mkdir(parents=True)
    shutil.copy2(DEPLOY_SCRIPT, adapter_dir / "deploy-skills.sh")
    (adapter_dir / "deploy-skills.sh").chmod(0o755)

    (tmp_path / ".pkit" / "skills" / "core").mkdir(parents=True)
    (tmp_path / ".pkit" / "skills" / "project").mkdir(parents=True)

    return tmp_path


def _write_flat_skill(root: Path, namespace: str, name: str, content: str) -> None:
    (root / ".pkit" / "skills" / namespace / f"{name}.md").write_text(content, encoding="utf-8")


def _write_composite_skill(
    root: Path, namespace: str, name: str, *, dispatcher: bool
) -> None:
    """Create a composite skill folder. With `dispatcher=False`, sub-procedures
    are present but the canonical `<name>/<name>.md` dispatcher is missing —
    the COR-020 mid-build state that used to brick the whole run (#537)."""
    skill_dir = root / ".pkit" / "skills" / namespace / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "sub-procedure.md").write_text("# a sub-procedure\n", encoding="utf-8")
    if dispatcher:
        (skill_dir / f"{name}.md").write_text(f"# {name} dispatcher\n", encoding="utf-8")


def _run_deploy(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(root / ".pkit" / "adapters" / "claude-code" / "deploy-skills.sh")],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


def test_deploy_no_skills_succeeds(mock_kit: Path) -> None:
    """With zero kit skills, deploy reports 'Done.' and exits 0."""
    result = _run_deploy(mock_kit)
    assert result.returncode == 0, result.stderr
    assert "Done." in result.stdout
    assert (mock_kit / ".claude" / "skills").is_dir()


def test_deploy_flat_skill_creates_symlink(mock_kit: Path) -> None:
    """A flat (atomic) skill deploys to .claude/skills/<name>/SKILL.md."""
    _write_flat_skill(mock_kit, "core", "atomic", "# atomic\n")
    result = _run_deploy(mock_kit)
    assert result.returncode == 0, result.stderr
    assert "created" in result.stdout
    link = mock_kit / ".claude" / "skills" / "atomic" / "SKILL.md"
    assert link.is_symlink()
    assert link.resolve() == (mock_kit / ".pkit" / "skills" / "core" / "atomic.md").resolve()


def test_deploy_composite_skill_with_dispatcher(mock_kit: Path) -> None:
    """A well-formed composite skill deploys the dispatcher as SKILL.md plus each sibling."""
    _write_composite_skill(mock_kit, "core", "whole", dispatcher=True)
    result = _run_deploy(mock_kit)
    assert result.returncode == 0, result.stderr
    assert (mock_kit / ".claude" / "skills" / "whole" / "SKILL.md").is_symlink()
    assert (mock_kit / ".claude" / "skills" / "whole" / "sub-procedure.md").is_symlink()


def test_deploy_dispatcherless_composite_degrades_not_aborts(mock_kit: Path) -> None:
    """A composite skill folder with sub-procedures but NO <name>/<name>.md
    dispatcher (a COR-020 mid-build state) must be skipped loudly — naming the
    offending skill — while a valid sibling still deploys and the run exits 0.

    Regression for #537: the unguarded `expected="$(expected_for ...)"` tripped
    `set -e` on the resolver's benign `return 1`, aborting the whole run with no
    diagnostic and no `Done.` — bricking `pkit sync`/`upgrade` for the adopter."""
    _write_composite_skill(mock_kit, "core", "trip", dispatcher=False)
    # A valid sibling that must still deploy despite the broken one.
    _write_flat_skill(mock_kit, "core", "fine", "# fine\n")

    result = _run_deploy(mock_kit)

    # Degrade, not abort.
    assert result.returncode == 0, result.stderr
    assert "Done." in result.stdout
    # The offending skill is named in a skipped line.
    assert "skipped" in result.stdout and "trip" in result.stdout
    # The precise defect is named.
    assert "skills/trip/trip.md" in result.stdout
    assert "COR-020" in result.stdout
    # End-of-run summary reports the skip count.
    assert "1 skill(s) skipped" in result.stdout
    # The valid sibling still deployed.
    assert (mock_kit / ".claude" / "skills" / "fine" / "SKILL.md").is_symlink()
    # The broken one was not deployed.
    assert not (mock_kit / ".claude" / "skills" / "trip" / "SKILL.md").exists()


def test_deploy_never_exits_nonzero_with_empty_output(mock_kit: Path) -> None:
    """The core #537 invariant: an unresolvable item never produces the silent
    abort (non-zero exit with nothing on stdout). Even with ONLY a broken skill
    present, the run exits 0 and emits a diagnostic naming it."""
    _write_composite_skill(mock_kit, "core", "trip", dispatcher=False)

    result = _run_deploy(mock_kit)

    assert result.returncode == 0, result.stderr
    # Never the opaque failure: nonzero exit AND empty stdout.
    assert not (result.returncode != 0 and result.stdout.strip() == "")
    assert "trip" in result.stdout
    assert "Done." in result.stdout
