"""Integration tests for `.pkit/adapters/claude-code/undeploy-capability.sh`.

The primitive removes one capability's deployed skills and agents from
`.claude/` — what the deploy primitives created for it, recognised by the mark
each leaves — and nothing else. Skills are deployed by the real
`deploy-skills.sh`; agents are staged as the resolved copies `deploy-agents.sh`
writes, carrying its marker (read from that script, so the two cannot drift
apart unnoticed).
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

SOURCE_REPO = Path(__file__).resolve().parents[1]
ADAPTER = SOURCE_REPO / ".pkit" / "adapters" / "claude-code"
UNDEPLOY_SCRIPT = ADAPTER / "undeploy-capability.sh"
DEPLOY_SKILLS_SCRIPT = ADAPTER / "deploy-skills.sh"
DEPLOY_AGENTS_SCRIPT = ADAPTER / "deploy-agents.sh"

_MARKER_LINE = re.compile(r'^MARKER="(?P<marker>[^"]+)"$', re.MULTILINE)


def _marker_of(script: Path) -> str:
    match = _MARKER_LINE.search(script.read_text(encoding="utf-8"))
    assert match, f"no MARKER= line in {script.name}"
    return match["marker"]


MARKER = _marker_of(DEPLOY_AGENTS_SCRIPT)


@pytest.fixture
def mock_kit(tmp_path: Path) -> Path:
    """A minimal kit layout with the claude-code deploy and undeploy scripts copied in."""
    adapter_dir = tmp_path / ".pkit" / "adapters" / "claude-code"
    adapter_dir.mkdir(parents=True)
    for script in (UNDEPLOY_SCRIPT, DEPLOY_SKILLS_SCRIPT):
        shutil.copy2(script, adapter_dir / script.name)
        (adapter_dir / script.name).chmod(0o755)
    for ns in ("core", "project"):
        (tmp_path / ".pkit" / "skills" / ns).mkdir(parents=True)
        (tmp_path / ".pkit" / "agents" / ns).mkdir(parents=True)
    return tmp_path


def _cap(root: Path, name: str) -> Path:
    return root / ".pkit" / "capabilities" / name


def _flat_skill(cap_dir: Path, skill: str) -> None:
    (cap_dir / "skills").mkdir(parents=True, exist_ok=True)
    (cap_dir / "skills" / f"{skill}.md").write_text(f"# {skill}\n", encoding="utf-8")


def _composite_skill(cap_dir: Path, skill: str) -> None:
    folder = cap_dir / "skills" / skill
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{skill}.md").write_text(f"# {skill}\n", encoding="utf-8")
    (folder / "sub-procedure.md").write_text("# a sub-procedure\n", encoding="utf-8")


def _cap_agent(cap_dir: Path, agent: str, *, folder: bool = False) -> None:
    agents = cap_dir / "agents"
    if folder:
        (agents / agent).mkdir(parents=True, exist_ok=True)
        (agents / agent / f"{agent}.md").write_text(f"# {agent}\n", encoding="utf-8")
    else:
        agents.mkdir(parents=True, exist_ok=True)
        (agents / f"{agent}.md").write_text(f"# {agent}\n", encoding="utf-8")


def _deployed_agent(root: Path, agent: str, *, marked: bool = True) -> Path:
    """A resolved agent copy as `deploy-agents.sh` writes it (marker on line 2)."""
    dest = root / ".claude" / "agents" / f"{agent}.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    marker = f"{MARKER}\n" if marked else ""
    dest.write_text(f"---\n{marker}name: {agent}\n---\n\n# {agent}\n", encoding="utf-8")
    return dest


def _run(root: Path, script: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(root / ".pkit" / "adapters" / "claude-code" / script), *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


def _undeploy(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return _run(root, "undeploy-capability.sh", *args)


def _deploy_skills(root: Path) -> None:
    result = _run(root, "deploy-skills.sh")
    assert result.returncode == 0, result.stdout + result.stderr


def _skill(root: Path, name: str) -> Path:
    return root / ".claude" / "skills" / name


def test_the_marker_is_deploy_agents_own() -> None:
    """The primitive recognises deploy-agents.sh's copies by the very marker it writes."""
    assert _marker_of(UNDEPLOY_SCRIPT) == MARKER


def test_removes_exactly_the_capabilitys_deployed_skills(mock_kit: Path) -> None:
    """Flat and composite skills of the capability go; another capability's, a core
    skill and a capability whose name only shares a prefix stay."""
    _flat_skill(_cap(mock_kit, "homegrown"), "home-flat")
    _composite_skill(_cap(mock_kit, "homegrown"), "home-folder")
    _flat_skill(_cap(mock_kit, "homegrown-extra"), "extra-skill")
    _flat_skill(_cap(mock_kit, "other"), "other-skill")
    (mock_kit / ".pkit" / "skills" / "core" / "core-skill.md").write_text("# c\n", encoding="utf-8")
    _deploy_skills(mock_kit)
    assert (_skill(mock_kit, "home-folder") / "sub-procedure.md").is_symlink()

    result = _undeploy(mock_kit, "homegrown")

    assert result.returncode == 0, result.stderr
    assert not _skill(mock_kit, "home-flat").exists()
    assert not _skill(mock_kit, "home-folder").exists()
    assert "removed    .claude/skills/home-flat (capability homegrown)" in result.stdout
    for kept in ("extra-skill", "other-skill", "core-skill"):
        assert (_skill(mock_kit, kept) / "SKILL.md").is_symlink(), kept
    # The capability's own subtree is untouched.
    assert (_cap(mock_kit, "homegrown") / "skills" / "home-flat.md").is_file()
    assert (_cap(mock_kit, "homegrown") / "skills" / "home-folder" / "sub-procedure.md").is_file()


def test_leaves_adopter_content_among_the_skills(mock_kit: Path) -> None:
    """Adopter content is never removed: a skill directory of its own, a symlink
    deploy-skills.sh did not write (absolute, though into the capability), and a
    file an adopter put in the capability's deployed folder."""
    _composite_skill(_cap(mock_kit, "homegrown"), "home-folder")
    _deploy_skills(mock_kit)
    own = _skill(mock_kit, "mine")
    own.mkdir(parents=True)
    (own / "SKILL.md").write_text("# mine\n", encoding="utf-8")
    elsewhere = _skill(mock_kit, "linked")
    elsewhere.mkdir()
    (elsewhere / "SKILL.md").symlink_to(mock_kit / ".pkit" / "capabilities" / "homegrown")
    note = _skill(mock_kit, "home-folder") / "NOTES.md"
    note.write_text("adopter notes\n", encoding="utf-8")

    result = _undeploy(mock_kit, "homegrown")

    assert result.returncode == 0, result.stderr
    assert (own / "SKILL.md").read_text(encoding="utf-8") == "# mine\n"
    assert (elsewhere / "SKILL.md").is_symlink()
    # The capability's links are gone; the adopter's file and its folder stay.
    assert note.read_text(encoding="utf-8") == "adopter notes\n"
    assert sorted(p.name for p in note.parent.iterdir()) == ["NOTES.md"]
    assert "kept       .claude/skills/home-folder/" in result.stdout


def test_removes_exactly_the_capabilitys_deployed_agents(mock_kit: Path) -> None:
    """Marked copies of the capability's flat and folder agents go; another
    capability's, an unmarked adopter file of the same name, and the copy of a
    project agent of the same name — project outranks every source — all stay."""
    home = _cap(mock_kit, "homegrown")
    _cap_agent(home, "home-flat")
    _cap_agent(home, "home-folder", folder=True)
    _cap_agent(home, "adopters-own")
    _cap_agent(home, "shadowed")
    _cap_agent(_cap(mock_kit, "other"), "other-agent")
    project_agent = mock_kit / ".pkit" / "agents" / "project" / "shadowed"
    project_agent.mkdir()
    (project_agent / "shadowed.md").write_text("# s\n", encoding="utf-8")
    flat = _deployed_agent(mock_kit, "home-flat")
    folder = _deployed_agent(mock_kit, "home-folder")
    adopters_own = _deployed_agent(mock_kit, "adopters-own", marked=False)
    shadowed = _deployed_agent(mock_kit, "shadowed")
    other = _deployed_agent(mock_kit, "other-agent")

    result = _undeploy(mock_kit, "homegrown")

    assert result.returncode == 0, result.stderr
    assert not flat.exists()
    assert not folder.exists()
    assert "removed    .claude/agents/home-flat.md (capability homegrown)" in result.stdout
    assert adopters_own.is_file()
    assert shadowed.is_file()
    assert "kept       .claude/agents/shadowed.md" in result.stdout
    assert other.is_file()
    assert (home / "agents" / "home-flat.md").is_file()


def test_is_idempotent(mock_kit: Path) -> None:
    _flat_skill(_cap(mock_kit, "homegrown"), "home-flat")
    _cap_agent(_cap(mock_kit, "homegrown"), "home-agent")
    _deploy_skills(mock_kit)
    _deployed_agent(mock_kit, "home-agent")
    assert _undeploy(mock_kit, "homegrown").returncode == 0

    again = _undeploy(mock_kit, "homegrown")

    assert again.returncode == 0, again.stderr
    assert "removed" not in again.stdout
    assert "Nothing deployed for capability homegrown." in again.stdout


def test_runs_with_no_harness_directories(mock_kit: Path) -> None:
    """A tree the deploy primitives never ran in has nothing to undeploy."""
    result = _undeploy(mock_kit, "homegrown")

    assert result.returncode == 0, result.stderr
    assert "Nothing deployed for capability homegrown." in result.stdout
    assert not (mock_kit / ".claude").exists()


@pytest.mark.parametrize("args", [[], ["../skills"], ["Homegrown"], ["a", "b"]])
def test_refuses_anything_but_one_capability_name(mock_kit: Path, args: list[str]) -> None:
    result = _undeploy(mock_kit, *args)

    assert result.returncode == 2
    assert result.stderr.strip()
