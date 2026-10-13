"""The rule-set reviewer's instructions hold no rule and no gate's form (COR-057, #1385).

The core agent judges a change against the accepted rules that bind on what it
alters. It takes those rules only from the rule sets, through the backbone's
answer, so its instructions say how to judge and never what to require: they
name no rule (COR-057 point 1). Whoever invokes it names the form of its verdict
and the marks of its findings, so they name no gate's form either, and, as a
core agent, no capability (COR-057 points 3 and 4). These tests hold that:

- **no rule id**: neither the source nor its deployed copy names a rule, by any
  form a rule is cited in. The detector is shown to find each form, so the
  guard cannot pass by finding nothing;
- **no gate's form**: no verdict word, finding mark or verdict marker a gate
  reads, those of the one gate the repository ships read from its brief, so a
  change to that brief moves the guard with it;
- **no capability**: no name of a capability the repository ships;
- **its rules come from the backbone**: the body names the command that gives
  each altered artefact's rules at the base and at the head;
- **deployed and tracked**: the deployed copy carries the source's body, and is
  tracked, as every deployed agent is.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from project_kit import rule_sets

REPO = Path(__file__).resolve().parent.parent
SOURCE = REPO / ".pkit" / "agents" / "core" / "rule-set-reviewer.md"
DEPLOYED = REPO / ".claude" / "agents" / "rule-set-reviewer.md"
CAPABILITIES = REPO / ".pkit" / "capabilities"
REVIEW_PR = CAPABILITIES / "project-management" / "scripts" / "review-pr.py"

#: A rule cited in any form: bare, with its component, or as an extension point.
RULE_ID_RE = re.compile(rf"(?<![A-Za-z0-9-]){rule_sets.RULE_ID_PATTERN}(?![0-9])")

#: What a gate reads in a verdict: its words, the marks of findings, its marker.
GATE_TERMS = (
    "APPROVED",
    "CHANGES_REQUESTED",
    "Reviewer agent (local",
    "[block]",
    "[advisory]",
    "[person]",
    "pkit-verdict",
)


def _brief_terms() -> set[str]:
    """The verdict words and finding marks the shipped gate's brief gives every reviewer."""
    source = REVIEW_PR.read_text(encoding="utf-8")
    tags = source[source.index("FINDING_TAGS = (") :]
    marks = set(re.findall(r"`(\[[a-z]+\])`", tags[: tags.index("\n)\n")]))
    words = set(re.findall(r"Reviewer agent \(local, \{name\}\): ([A-Z_]+)", source))
    return marks | words


def test_the_gate_s_terms_are_read_from_its_brief() -> None:
    assert _brief_terms() >= {"[block]", "[advisory]", "[person]", "APPROVED", "CHANGES_REQUESTED"}


def _body(path: Path) -> str:
    """The file after its front matter."""
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path} has no front matter"
    return text.split("---\n", 2)[2]


def _capabilities() -> list[str]:
    return sorted(p.name for p in CAPABILITIES.iterdir() if (p / "package.yaml").is_file())


@pytest.fixture(params=[SOURCE, DEPLOYED], ids=["source", "deployed"])
def agent_file(request: pytest.FixtureRequest) -> Path:
    path: Path = request.param
    assert path.is_file(), f"{path} is missing"
    return path


@pytest.mark.parametrize(
    "cited",
    ["RS-WRITE-005", "living-docs:RS-LDOC-003", "RS-CMN-003#cause-location", "(RS-A1-1000)"],
)
def test_the_detector_finds_a_rule_in_every_cited_form(cited: str) -> None:
    assert RULE_ID_RE.search(f"A finding under {cited} breaks it."), cited


@pytest.mark.parametrize("text", ["RS-<SET>-NNN", "COR-057", "the RS family", "RS-write-005"])
def test_the_detector_finds_no_rule_where_none_is_named(text: str) -> None:
    assert RULE_ID_RE.search(text) is None, text


def test_the_agent_names_no_rule(agent_file: Path) -> None:
    named = RULE_ID_RE.findall(agent_file.read_text(encoding="utf-8"))
    assert not named, f"{agent_file.name} names a rule: {named}"


@pytest.mark.parametrize("term", sorted(set(GATE_TERMS) | _brief_terms()))
def test_the_agent_names_no_term_of_a_gate(agent_file: Path, term: str) -> None:
    assert term not in agent_file.read_text(encoding="utf-8"), term


def test_the_agent_names_no_capability(agent_file: Path) -> None:
    capabilities = _capabilities()
    assert capabilities, "no capability found, so the guard would pass on nothing"
    text = agent_file.read_text(encoding="utf-8")
    named = [name for name in capabilities if re.search(rf"\b{re.escape(name)}\b", text)]
    assert not named, f"{agent_file.name} names a capability: {named}"


def test_the_agent_reads_its_rules_from_the_backbone_answer() -> None:
    """It runs the command that gives each altered artefact's rules at the base and at
    the head, naming both, and reads their JSON."""
    body = _body(SOURCE)
    assert "`pkit rule-sets altered --base <base> --head <head> --json`" in body


def test_the_deployed_copy_carries_the_source_body_and_is_tracked() -> None:
    assert _body(DEPLOYED) == _body(SOURCE), (
        "stale deployed copy: run `bash .pkit/adapters/claude-code/deploy-agents.sh`"
    )
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(DEPLOYED.relative_to(REPO))],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert tracked.returncode == 0, "the deployed copy is not tracked"
