"""Reviewers are read-only on what they judge, and keep their working files in the workspace (#855).

A reviewer's read-only is about the work under review — it never changes that
work or the repository it lives in — not a claim that it writes nothing. A
reviewer that can execute needs working files (a dumped diff, a reproduction
that executes a payload), and those go in the agent workspace, where an
author's `git add` cannot find them. The rule is the reviewer role's (the
agents README's "Reviewers" paragraph), so every such reviewer carries the same
`## What read-only covers` section. These tests hold that:

- **discovery**: a reviewer is a shipped agent — core, project or any
  capability's, resolved in the deploy's order — named `*-reviewer`, or one of
  COR-024's other two (`critic`, `architect`); it executes when `Bash` is among
  its tools. The executing reviewers shipped when this landed must be among
  those found, so the discovery cannot go quietly empty;
- **the section**: each executing reviewer carries it once, just before
  `## Intermediate files`, word for word the same as every other, stating the
  scoped claim and naming the workspace;
- **the description**: a read-only claim there is scoped too;
- **the deployed copy** carries the same section, so a source edit without a
  redeploy fails here;
- **the next reviewer's author** finds the rule: the README names the section
  and `pkit new agent`'s template points at it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML

from project_kit.agents import AGENT_TEMPLATE, agent_locations, find_agent_file

REPO = Path(__file__).resolve().parent.parent
DEPLOYED = REPO / ".claude" / "agents"
README = REPO / ".pkit" / "agents" / "README.md"

SECTION = "## What read-only covers"
FOLLOWING_SECTION = "## Intermediate files"

#: COR-024's reviewers whose names do not end in `-reviewer`.
OTHER_REVIEWERS = frozenset({"critic", "architect"})

#: The executing reviewers shipped when #855 landed.
KNOWN_EXECUTING_REVIEWERS = frozenset(
    {
        "code-reviewer",
        "docs-reviewer",
        "security-reviewer",
        "pm-reviewer",
        "methodology-reviewer",
        "convention-compliance-reviewer",
    }
)

#: What the section must say: the scoped claim, and where working files go.
REQUIRED_PHRASES = (
    "Read-only is about what you judge",
    "you never change the work under review or the repository it lives in",
    "It does not mean you write nothing.",
    "a dumped diff",
    "a reproduction (even one that executes a payload to prove a defect)",
    "`.agent-workspace/` at the root of your checkout",
    "never loose in the repository",
    "a review leaves no file of yours outside the workspace",
)


def _split(path: Path) -> tuple[dict[str, Any], str]:
    """A Markdown file's front matter, parsed, and its body; no front matter parses as empty."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}, text
    _, front, body = text.split("---\n", 2)
    return YAML(typ="safe").load(front) or {}, body


def _shipped_agents() -> dict[str, Path]:
    """Every agent the repository ships, by name; the first location in deploy order wins."""
    found: dict[str, Path] = {}
    for _, location in agent_locations(REPO):
        if not location.is_dir():
            continue
        for entry in sorted(location.iterdir()):
            name = entry.stem if entry.suffix == ".md" else entry.name
            path = find_agent_file(location, name)
            if path is None or name in found:
                continue
            front, _ = _split(path)
            if front.get("name") == name:
                found[name] = path
    return found


def _executing_reviewers() -> dict[str, Path]:
    return {
        name: path
        for name, path in _shipped_agents().items()
        if (name.endswith("-reviewer") or name in OTHER_REVIEWERS)
        and "Bash" in (_split(path)[0].get("tools") or [])
    }


EXECUTING_REVIEWERS = _executing_reviewers()


def _section(body: str) -> str:
    """The text of the body's `## What read-only covers` section, up to the next heading."""
    assert body.count(f"\n{SECTION}\n") == 1, f"expected exactly one {SECTION!r} section"
    after = body.split(f"\n{SECTION}\n", 1)[1]
    return after.split("\n## ", 1)[0].strip()


def test_discovery_finds_every_known_executing_reviewer():
    missing = KNOWN_EXECUTING_REVIEWERS - EXECUTING_REVIEWERS.keys()
    assert not missing, f"not discovered as executing reviewers: {sorted(missing)}"


@pytest.mark.parametrize("name", sorted(EXECUTING_REVIEWERS))
def test_section_sits_just_before_intermediate_files(name):
    _, body = _split(EXECUTING_REVIEWERS[name])
    section = _section(body)
    assert f"\n{SECTION}\n\n{section}\n\n{FOLLOWING_SECTION}\n" in body, (
        f"{name}: {SECTION!r} must come just before {FOLLOWING_SECTION!r}"
    )


def test_section_is_identical_across_executing_reviewers():
    sections = {name: _section(_split(path)[1]) for name, path in EXECUTING_REVIEWERS.items()}
    assert len(set(sections.values())) == 1, (
        f"{SECTION!r} differs between reviewers — copy it word for word: {sorted(sections)}"
    )


@pytest.mark.parametrize("phrase", REQUIRED_PHRASES)
def test_section_states_the_scoped_claim_and_the_workspace(phrase):
    any_reviewer = next(iter(EXECUTING_REVIEWERS.values()))
    assert phrase in _section(_split(any_reviewer)[1])


@pytest.mark.parametrize("name", sorted(EXECUTING_REVIEWERS))
def test_a_read_only_claim_in_the_description_is_scoped(name):
    description = str(_split(EXECUTING_REVIEWERS[name])[0].get("description", ""))
    if "read-only" in description.lower():
        assert "Read-only on what it reviews" in description, (
            f"{name}: the description's read-only claim must name its scope"
        )


@pytest.mark.parametrize("name", sorted(EXECUTING_REVIEWERS))
def test_deployed_copy_carries_the_same_section(name):
    deployed = DEPLOYED / f"{name}.md"
    assert deployed.is_file(), f"{name} is not deployed"
    source_section = _section(_split(EXECUTING_REVIEWERS[name])[1])
    assert _section(_split(deployed)[1]) == source_section, (
        "stale deployed copy: run `bash .pkit/adapters/claude-code/deploy-agents.sh`"
    )


def test_the_next_reviewers_author_is_pointed_at_the_section():
    assert f"`{SECTION}`" in README.read_text(encoding="utf-8")
    assert f"`{SECTION}`" in AGENT_TEMPLATE
