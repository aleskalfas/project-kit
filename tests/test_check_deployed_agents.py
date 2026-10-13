"""The deployed agents' check, `scripts/check_deployed_agents.py` (#1559).

- **A matching copy passes:** the tracked copy is what the deploy writes.
- **A drifted copy fails:** a source changed without the deploy, naming the
  agent and the command that fixes it.
- **The index is what counts:** a copy redeployed only in the working tree, as
  CI's `pkit sync` leaves it, still fails, and the check writes nothing.
- **The other drifts:** a copy the deploy would write that git does not track, a
  tracked copy the deploy would remove, and an agent the deploy skips.

Each test stages a small kit in a git repository of its own, with the real
deploy script and resolver, and stages what it writes. The check reads the
index, so no test commits.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from scripts import check_deployed_agents as cda

REPO = Path(__file__).resolve().parents[1]
ADAPTER = REPO / ".pkit" / "adapters" / "claude-code"
OWNERSHIP = REPO / ".pkit" / "lifecycle" / "ownership.py"

AGENT = "helper"
COPY = f".claude/agents/{AGENT}.md"


def _source(body: str, name: str = AGENT) -> str:
    return f"---\nname: {name}\ndescription: Test.\n---\n\n# {name}\n\n{body}\n"


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _write_source(root: Path, body: str, name: str = AGENT) -> Path:
    source = root / ".pkit" / "agents" / "core" / name / f"{name}.md"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(_source(body, name), encoding="utf-8")
    return source


def _deploy(root: Path) -> None:
    subprocess.run(
        ["bash", str(root / ".pkit" / "adapters" / "claude-code" / "deploy-agents.sh")],
        cwd=root,
        check=True,
        capture_output=True,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A git repository whose index holds one agent's source and its deployed copy."""
    adapter = tmp_path / ".pkit" / "adapters" / "claude-code"
    adapter.mkdir(parents=True)
    for script in ("deploy-agents.sh", "_resolve_agent.py"):
        shutil.copy2(ADAPTER / script, adapter / script)
    (tmp_path / ".pkit" / "lifecycle").mkdir()
    shutil.copy2(OWNERSHIP, tmp_path / ".pkit" / "lifecycle" / "ownership.py")
    _write_source(tmp_path, "Says one thing.")
    _deploy(tmp_path)
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", "-A")
    return tmp_path


def _run(root: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    code = cda.main([], root=root)
    return code, capsys.readouterr().out


def test_a_matching_copy_passes(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, out = _run(repo, capsys)
    assert code == 0, out
    assert out == "deployed agents: each of the 1 tracked copies is what the deploy writes\n"


def test_a_copy_left_behind_its_source_fails_naming_the_agent_and_the_fix(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_source(repo, "Says another thing.")
    _git(repo, "add", "-A")

    code, out = _run(repo, capsys)
    assert code == 1, out
    assert f"- {AGENT}: {COPY} is not what the deploy writes from its source" in out
    assert "-Says one thing." in out and "+Says another thing." in out
    assert f"To fix: run {cda.DEPLOY}, then commit what it changes in .claude/agents/." in out


def test_a_copy_redeployed_only_in_the_working_tree_still_fails(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """CI's sync redeploys the working tree before the check: the index still shows the drift."""
    _write_source(repo, "Says another thing.")
    _git(repo, "add", "-A")
    _deploy(repo)
    redeployed = (repo / COPY).read_bytes()

    code, out = _run(repo, capsys)
    assert code == 1, out
    assert f"- {AGENT}: {COPY} is not what the deploy writes" in out
    assert (repo / COPY).read_bytes() == redeployed  # the check wrote nothing


def test_the_check_passes_once_the_redeploy_is_staged(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_source(repo, "Says another thing.")
    _deploy(repo)
    _git(repo, "add", "-A")

    code, out = _run(repo, capsys)
    assert code == 0, out


def test_a_copy_the_deploy_writes_but_git_does_not_track_fails(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_source(repo, "New.", name="newcomer")
    _git(repo, "add", "-A")

    code, out = _run(repo, capsys)
    assert code == 1, out
    expected = "- newcomer: the deploy writes .claude/agents/newcomer.md, which git does not track"
    assert expected in out


def test_a_tracked_copy_whose_agent_no_longer_ships_fails(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    shutil.rmtree(repo / ".pkit" / "agents" / "core" / AGENT)
    _git(repo, "add", "-A")

    code, out = _run(repo, capsys)
    assert code == 1, out
    assert f"- {AGENT}: the deploy removes {COPY}, as its agent no longer ships" in out


def test_an_agent_the_deploy_skips_fails(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """An agent with an overlay category the project does not define deploys nothing."""
    source = repo / ".pkit" / "agents" / "core" / "gapped" / "gapped.md"
    source.parent.mkdir(parents=True)
    source.write_text(
        "---\nname: gapped\ndescription: Test.\nowns:\n  - <code-paths>\n---\n\n# gapped\n",
        encoding="utf-8",
    )
    _git(repo, "add", "-A")

    code, out = _run(repo, capsys)
    assert code == 1, out
    assert "- gapped: the deploy skips it: gapped — " in out


def test_a_repository_that_tracks_no_kit_cannot_be_checked(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _git(tmp_path, "init", "-q")

    code = cda.main([], root=tmp_path)
    captured = capsys.readouterr()
    assert code == 2
    assert captured.err == "deployed agents: git tracks nothing under .pkit or .claude/agents\n"
