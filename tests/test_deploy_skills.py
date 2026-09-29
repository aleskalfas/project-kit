"""Integration tests for `.pkit/adapters/claude-code/deploy-skills.sh`.

The script is exercised against synthesised kit layouts in tmp directories.
No mocking — the script symlinks canonical skill files from `.pkit/skills/`
(and the capabilities the backbone manifest registers) into
`.claude/skills/<name>/SKILL.md`.

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


# --- capability skills: registered capabilities only ----------------------------


def _register(root: Path, *capabilities: str) -> None:
    """Write the backbone manifest registering exactly `capabilities`, as the
    lifecycle writes it — an adapter entry first, so the parser meets other kinds."""
    lines = [
        "schema_version: 1",
        "backbone_version: 0.0.0",
        "components:",
        "  - kind: adapter",
        "    name: claude-code",
        "    manifest: .pkit/adapters/claude-code/project/manifest.yaml",
    ]
    for cap in capabilities:
        lines += [
            "  - kind: capability",
            f"    name: {cap}",
            f"    manifest: .pkit/capabilities/{cap}/manifest.yaml",
        ]
    (root / ".pkit" / "manifest.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_capability_skill(root: Path, capability: str, name: str, *, composite: bool) -> Path:
    """A skill shipped by `capability`; a composite one carries a sub-procedure."""
    skills = root / ".pkit" / "capabilities" / capability / "skills"
    if composite:
        (skills / name).mkdir(parents=True, exist_ok=True)
        (skills / name / "sub-procedure.md").write_text("# a sub-procedure\n", encoding="utf-8")
        source = skills / name / f"{name}.md"
    else:
        skills.mkdir(parents=True, exist_ok=True)
        source = skills / f"{name}.md"
    source.write_text(f"# {name}\n", encoding="utf-8")
    return source


def _deployed(root: Path, name: str) -> Path:
    return root / ".claude" / "skills" / name


def test_a_registered_capability_s_skills_deploy(mock_kit: Path) -> None:
    source = _write_capability_skill(mock_kit, "my-cap", "cap-skill", composite=True)
    _register(mock_kit, "my-cap")

    result = _run_deploy(mock_kit)

    assert result.returncode == 0, result.stderr
    assert (_deployed(mock_kit, "cap-skill") / "SKILL.md").resolve() == source.resolve()
    assert (_deployed(mock_kit, "cap-skill") / "sub-procedure.md").is_symlink()


def test_an_unregistered_capability_s_skills_do_not_deploy(mock_kit: Path) -> None:
    """A capability directory on disk that the manifest does not register ships no skill."""
    _write_capability_skill(mock_kit, "registered", "kept", composite=False)
    _write_capability_skill(mock_kit, "on-disk-only", "ignored", composite=True)
    _register(mock_kit, "registered")

    result = _run_deploy(mock_kit)

    assert result.returncode == 0, result.stderr
    assert (_deployed(mock_kit, "kept") / "SKILL.md").is_symlink()
    assert not _deployed(mock_kit, "ignored").exists()
    assert "ignored" not in result.stdout


def test_without_a_manifest_no_capability_skill_deploys(mock_kit: Path) -> None:
    _write_capability_skill(mock_kit, "my-cap", "cap-skill", composite=False)
    _write_flat_skill(mock_kit, "core", "atomic", "# atomic\n")

    result = _run_deploy(mock_kit)

    assert result.returncode == 0, result.stderr
    assert (_deployed(mock_kit, "atomic") / "SKILL.md").is_symlink()
    assert not _deployed(mock_kit, "cap-skill").exists()


def test_unregistering_in_place_removes_the_skills_on_the_next_deploy(mock_kit: Path) -> None:
    """The subtree stays on disk (an incubated capability, or the source repository);
    unregistering it is what makes its deployed skills stale."""
    _write_capability_skill(mock_kit, "my-cap", "composite-skill", composite=True)
    _write_capability_skill(mock_kit, "my-cap", "flat-skill", composite=False)
    _register(mock_kit, "my-cap")
    assert _run_deploy(mock_kit).returncode == 0
    assert (_deployed(mock_kit, "composite-skill") / "sub-procedure.md").is_symlink()

    _register(mock_kit)
    result = _run_deploy(mock_kit)

    assert result.returncode == 0, result.stderr
    assert not _deployed(mock_kit, "composite-skill").exists()
    assert not _deployed(mock_kit, "flat-skill").exists()
    assert "removed" in result.stdout and "composite-skill" in result.stdout
    # The capability's source is untouched.
    skills = mock_kit / ".pkit" / "capabilities" / "my-cap" / "skills"
    assert (skills / "composite-skill" / "sub-procedure.md").is_file()
    assert (skills / "flat-skill.md").is_file()


def test_the_stale_removal_never_touches_adopter_content(mock_kit: Path) -> None:
    """Only a symlink into `.pkit/skills/` or `.pkit/capabilities/` is the deploy's:
    a real file, or a symlink elsewhere, under a name no source ships survives."""
    _write_capability_skill(mock_kit, "my-cap", "authored", composite=False)
    _register(mock_kit)
    own = _deployed(mock_kit, "authored")
    own.mkdir(parents=True)
    (own / "SKILL.md").write_text("# the adopter's own skill\n", encoding="utf-8")
    elsewhere = mock_kit / "elsewhere.md"
    elsewhere.write_text("# elsewhere\n", encoding="utf-8")
    linked = _deployed(mock_kit, "linked")
    linked.mkdir(parents=True)
    (linked / "SKILL.md").symlink_to(elsewhere)

    result = _run_deploy(mock_kit)

    assert result.returncode == 0, result.stderr
    assert (own / "SKILL.md").read_text(encoding="utf-8") == "# the adopter's own skill\n"
    assert (linked / "SKILL.md").resolve() == elsewhere.resolve()


def test_a_name_that_now_resolves_flat_drops_the_old_siblings(mock_kit: Path) -> None:
    """A capability's composite skill shadowed by a same-named flat core skill: the
    capability's sub-procedure links go with it, not just its SKILL.md."""
    _write_capability_skill(mock_kit, "my-cap", "shared", composite=True)
    _register(mock_kit, "my-cap")
    assert _run_deploy(mock_kit).returncode == 0
    assert (_deployed(mock_kit, "shared") / "sub-procedure.md").is_symlink()

    core = mock_kit / ".pkit" / "skills" / "core" / "shared.md"
    core.write_text("# shared, from core\n", encoding="utf-8")
    result = _run_deploy(mock_kit)

    assert result.returncode == 0, result.stderr
    assert (_deployed(mock_kit, "shared") / "SKILL.md").resolve() == core.resolve()
    assert not (_deployed(mock_kit, "shared") / "sub-procedure.md").exists()


def test_siblings_deploy_from_the_source_that_wins_only(mock_kit: Path) -> None:
    """A flat skill that wins by precedence deploys alone: a lower location's
    composite folder of the same name contributes no sibling beside it."""
    _write_capability_skill(mock_kit, "my-cap", "shared", composite=True)
    _register(mock_kit, "my-cap")
    _write_flat_skill(mock_kit, "core", "shared", "# shared, from core\n")

    result = _run_deploy(mock_kit)

    assert result.returncode == 0, result.stderr
    assert sorted(p.name for p in _deployed(mock_kit, "shared").iterdir()) == ["SKILL.md"]
