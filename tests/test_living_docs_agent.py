"""The living-docs agent and its storyboard (#1005).

The capability's agent does the judgment work living-docs DEC-001 reserves for
it — friction-fix proposals, reader-review, onboarding — always as proposals a
person reviews. These tests hold the contract its files carry:

- the **front matter**: read-only on the repository (no `Edit`, nothing owned),
  `Write` only for the agent workspace, its storyboard declared by its bare
  sibling filename (the agents README's convention), no model or effort of its
  own;
- the **references**: `pkit refs validate`'s checks find nothing in the agent's
  folder (every record and path the body and storyboard cite is declared, and
  the storyboard and the agent name each other);
- the **storyboard**: it names the agent back by its capability and scripts the
  three scenarios, each with its four parts;
- the **deployed copy**: `.claude/agents/living-docs.md` is what the Claude Code
  deploy writes from the source today, so a source edit without a redeploy
  fails here rather than shipping a stale agent; it carries the storyboard's
  source path, which is where the runtime reads it from.

The deploy's resolver runs under this interpreter, not through its `uv`
shebang, so no test reaches `uv` or the network.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML

from project_kit import refs

REPO = Path(__file__).resolve().parent.parent
AGENT_DIR = REPO / ".pkit" / "capabilities" / "living-docs" / "agents" / "living-docs"
AGENT = AGENT_DIR / "living-docs.md"
STORYBOARD = AGENT_DIR / "storyboard.md"
DEPLOYED = REPO / ".claude" / "agents" / "living-docs.md"
ADAPTER = REPO / ".pkit" / "adapters" / "claude-code"
OVERLAY = REPO / ".pkit" / "agents" / "project" / "overlay.yaml"

#: The friction writers the agent never runs (COR-050 point 13).
WRITERS = ("pkit friction revalidate", "pkit friction defer", "pkit friction record-status")

#: The storyboard's scenarios (COR-016), each with its four parts.
SCENARIOS = (
    "Happy path",
    "Reader-review finds nothing",
    "Onboarding plan rejected",
)
SCENARIO_PARTS = ("**Trigger.**", "**Preconditions.**", "### Walkthrough", "### Behind the scenes")


def _split(path: Path) -> tuple[dict[str, Any], str]:
    """A Markdown file's front matter, parsed, and its body."""
    text = path.read_text(encoding="utf-8")
    _, front, body = text.split("---\n", 2)
    return YAML(typ="safe").load(front) or {}, body


@pytest.fixture(scope="module")
def agent() -> tuple[dict[str, Any], str]:
    return _split(AGENT)


@pytest.fixture(scope="module")
def storyboard() -> tuple[dict[str, Any], str]:
    return _split(STORYBOARD)


# --- front matter --------------------------------------------------------------


def test_front_matter_names_the_agent(agent):
    front, _ = agent
    assert front["name"] == "living-docs"
    assert front["description"].strip()


def test_agent_is_read_only_on_the_repository(agent):
    """Read, search and the read commands; Write for the workspace; no Edit, nothing owned."""
    front, _ = agent
    assert set(front["tools"]) == {"Read", "Glob", "Grep", "Bash", "Write"}
    assert front["owns"] == []
    assert not front.get("needs")


def test_body_says_it_never_applies_or_runs_a_writer(agent):
    _, body = agent
    assert "## Read-only on the repository" in body
    for writer in WRITERS:
        assert writer in body, writer
    assert "`.agent-workspace/living-docs/`" in body


def test_storyboard_is_declared_as_its_sibling(agent):
    """The source names the storyboard beside it; the deploy rebases it (see the deployed copy)."""
    front, body = agent
    assert front["storyboards"] == [STORYBOARD.name]
    assert f"`{STORYBOARD.name}`" in body


def test_agent_inherits_model_and_effort(agent):
    front, _ = agent
    assert "model" not in front
    assert "effort" not in front


def test_body_carries_the_three_intents(agent):
    _, body = agent
    for heading in ("### 2. Friction-fix", "### 3. Reader-review", "### 4. Onboarding"):
        assert heading in body, heading


# --- references ----------------------------------------------------------------


def test_refs_find_nothing_in_the_agent_folder():
    folder = str(AGENT_DIR.relative_to(REPO))
    issues = [i for i in refs.validate_corpus(REPO) if i.location.startswith(folder)]
    assert issues == []


def test_agent_loads_as_the_capability_agent():
    loaded = [a for a in refs.load_artifacts(REPO) if a.kind == "agent" and a.name == "living-docs"]
    assert len(loaded) == 1
    assert loaded[0].capability == "living-docs"


# --- storyboard ----------------------------------------------------------------


def test_storyboard_names_the_agent_back(storyboard):
    front, _ = storyboard
    assert front["consumers"] == [{"kind": "agent", "name": "living-docs", "namespace": "living-docs"}]


def test_storyboard_scripts_the_three_scenarios(storyboard):
    _, body = storyboard
    sections = re.split(r"^## Scenario \d+: ", body, flags=re.MULTILINE)[1:]
    titles = [section.splitlines()[0] for section in sections]
    assert len(titles) == len(SCENARIOS)
    for title, expected in zip(titles, SCENARIOS, strict=True):
        assert title.startswith(expected), title
    for section in sections:
        for part in SCENARIO_PARTS:
            assert part in section, (section.splitlines()[0], part)


def test_storyboard_frames_and_sets_the_tone(storyboard):
    _, body = storyboard
    assert "## Framing" in body
    assert "## Tone" in body


# --- the deployed copy ---------------------------------------------------------


def _deploy_marker() -> str:
    """The marker the deploy stamps as line 2, read from the script rather than restated."""
    script = (ADAPTER / "deploy-agents.sh").read_text(encoding="utf-8")
    match = re.search(r'^MARKER="(.+)"$', script, flags=re.MULTILINE)
    assert match, "deploy-agents.sh no longer declares MARKER"
    return match.group(1)


def test_deployed_copy_matches_the_source():
    """What the deploy would write from the source today is what is committed."""
    completed = subprocess.run(
        [sys.executable, str(ADAPTER / "_resolve_agent.py"), str(AGENT), "living-docs", str(OVERLAY)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    first, rest = completed.stdout.split("\n", 1)
    expected = f"{first}\n{_deploy_marker()}\n{rest}"
    assert DEPLOYED.read_text(encoding="utf-8") == expected, (
        "stale deployed copy: run `bash .pkit/adapters/claude-code/deploy-agents.sh`"
    )


def test_deployed_copy_reads_the_storyboard_from_its_source_path():
    """The deployed copy lives in .claude/agents/, so it names the storyboard by its source path."""
    front, body = _split(DEPLOYED)
    source_path = str(STORYBOARD.relative_to(REPO))
    assert front["storyboards"] == [source_path]
    assert f"`{source_path}`" in body
    assert (REPO / source_path).is_file()
