"""The living-docs agent and its storyboard (#1005).

The capability's agent does the judgment work living-docs DEC-001 reserves for
it — friction-fix proposals, reader-review, onboarding — always as proposals a
person reviews. These tests hold the contract its files carry:

- the **front matter**: read-only on the repository (no `Edit`, nothing owned),
  `Write` only for the agent workspace, no tool for asking the person, its
  storyboard declared by its bare sibling filename (the agents README's
  convention), no model or effort of its own;
- **the friction writers** (#1148): the body names them in one paragraph, which
  points at the agents README's "Friction writers" for the conditions for
  running one, states the two that never hold for this agent, and says it runs
  none; the storyboard runs none either,
  and the command it names for the person carries no consent flag. That those
  commands write nothing without a person is `test_handed_over_writers.py`'s;
- the **references**: `pkit refs validate`'s checks find nothing in the agent's
  folder (every record and path the body and storyboard cite is declared, and
  the storyboard and the agent name each other);
- the **storyboard**: it names the agent back by its capability and scripts its
  five scenarios, each with its four parts;
- **the fixer run** (#1746): the body says what the agent takes from the command
  that starts it as the fixer of pages and what it writes, and fixes the result
  line it ends with, one per page; the storyboard's fixer run ends in lines of
  that form;
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
from tests import handed_over
from tests.adopter_repo import MakeAdopterRepo

REPO = Path(__file__).resolve().parent.parent
AGENT_DIR = REPO / ".pkit" / "capabilities" / "living-docs" / "agents" / "living-docs"
AGENT = AGENT_DIR / "living-docs.md"
STORYBOARD = AGENT_DIR / "storyboard.md"
DEPLOYED = REPO / ".claude" / "agents" / "living-docs.md"
ADAPTER = REPO / ".pkit" / "adapters" / "claude-code"
OVERLAY = REPO / ".pkit" / "agents" / "project" / "overlay.yaml"

#: The friction writers the agent never runs: its body names them in one paragraph,
#: which sets the conditions for running one (COR-013; the agents README, "Friction
#: writers").
WRITERS = ("pkit friction revalidate", "pkit friction defer", "pkit friction record-status")
WRITES = re.compile(r"friction (?:revalidate|defer|record-status)")
RULE = "You own no path (`owns` is empty, COR-013)."

#: Where the conditions for running a writer are set; the body points there rather
#: than restating them.
FRICTION_WRITERS = '(`.pkit/agents/README.md`, "Friction writers")'

#: The two conditions that never hold for this agent, as the body states them.
NEVER_HOLDS = (
    "Two of them never hold for you",
    "you cannot ask the person — you have no tool for putting a question to them",
    "you review pages",
)

#: Claude Code's tool for putting a question to the person: without it the agent
#: cannot ask, so it runs no writer.
ASKING_TOOL = "AskUserQuestion"

README = REPO / ".pkit" / "capabilities" / "living-docs" / "README.md"

#: The storyboard's scenarios (COR-016), each with its four parts.
SCENARIOS = (
    "Happy path",
    "Reader-review finds nothing",
    "Onboarding plan rejected",
    "A page stale on a source",
    "A fixer run a command started",
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
    """Read, search and the read commands; Write for the workspace; no Edit, nothing
    owned, and no tool for asking the person."""
    front, _ = agent
    assert set(front["tools"]) == {"Read", "Glob", "Grep", "Bash", "Write"}
    assert ASKING_TOOL not in front["tools"]
    assert front["owns"] == []
    assert not front.get("needs")


def test_body_names_the_writers_in_one_paragraph_and_runs_none(agent):
    """The writers are named only in the paragraph that points at the agents README's
    conditions and states the two that never hold for it; it names the command that
    answers, and runs none."""
    _, body = agent
    assert "## Read-only on the repository" in body
    (rule,) = [paragraph for paragraph in body.split("\n\n") if WRITES.search(paragraph)]
    assert rule.startswith(RULE)
    for writer in WRITERS:
        assert f"`{writer}`" in rule, writer
    assert FRICTION_WRITERS in rule
    for condition in NEVER_HOLDS:
        assert condition in rule, condition
    assert "without `--yes`, and run none" in rule
    assert "`pkit friction record-status` is the after-merge job's and never yours." in rule
    assert "`.agent-workspace/living-docs/`" in body


def test_storyboard_hands_over_no_consent_and_runs_no_writer(storyboard):
    """Dispatched, the plan is its result; either way it runs no writer, and the command
    it names for the person carries neither `--yes` nor `--dry-run`."""
    _, body = storyboard
    pattern = body.split("## Invocation pattern", 1)[1].split("\n## ", 1)[0]
    assert "Dispatched as a subagent, it cannot hear the person: the plan is its result" in pattern
    assert "Either way nothing is drafted before approval, and no friction writer is run" in pattern
    handed = handed_over.commands(body)
    assert handed
    assert [c for c in handed if handed_over.CONSENT.search(c)] == []


def test_readme_says_the_answer_is_a_person_s_decision():
    text = README.read_text(encoding="utf-8")
    assert "the answer a page carries is yours to give" not in text
    assert "the answer a page carries is a person's decision (COR-050 point 3)" in text
    assert 'who may run a writer is in the agents README, "Friction writers"' in text


def test_storyboard_is_declared_as_its_sibling(agent):
    """The source names the storyboard beside it; the deploy rebases it (see the deployed copy)."""
    front, body = agent
    assert front["storyboards"] == [STORYBOARD.name]
    assert f"`{STORYBOARD.name}`" in body


def test_agent_inherits_model_and_effort(agent):
    front, _ = agent
    assert "model" not in front
    assert "effort" not in front


def test_body_refuses_a_friction_document_of_another_version(
    agent: tuple[dict[str, Any], str],
) -> None:
    """The friction documents it reads carry `schema_version`: it reads version 1,
    refuses any other value, and reads a document without the key as version 1."""
    _, body = agent
    section = body.split("## The commands you read", 1)[1].split("\n## ", 1)[0]
    (refusal,) = [p for p in section.split("\n\n") if "`schema_version`" in p]
    assert refusal.startswith("**You refuse a friction document of a version you do not read.**")
    for document in ("`explain`", "`debt`", "`check --all`"):
        assert document in refusal, document
    assert "you read version `1`" in refusal
    assert "stop before reading it" in refusal
    assert "A document without the key comes from a backbone that predates it" in refusal
    assert "read it as version `1`" in refusal


def test_body_carries_the_three_intents(agent):
    _, body = agent
    for heading in ("### 2. Friction-fix", "### 3. Reader-review", "### 4. Onboarding"):
        assert heading in body, heading


# --- the fixer run -------------------------------------------------------------

#: The result lines a fixer run ends with, one per page (project-management DEC-056
#: point 3): the page as the brief names it between backticks, then for `proposed`
#: its answer file in the page's own folder, and for `held` or `none` the question
#: for the person or the reason.
PROPOSED_LINE = re.compile(r"^Fixer result \(living-docs\): proposed `([^`]+)` in `([^`]+)`$")
HELD_OR_NONE_LINE = re.compile(r"^Fixer result \(living-docs\): (held|none) `([^`]+)`: (\S.*)$")

#: The keys of a page's friction block a fixer run's diff never touches: an answer
#: goes into the answer's fields (project-management DEC-056 point 6).
ANSWER_KEYS = ("`revalidated`", "`revisited`", "`unanchored-because`", "`last-check`")


def _outcome(line: str) -> str | None:
    """The outcome a result line gives, or None for a line off the grammar. A
    proposed page's answer file lies in the folder its location names."""
    proposed = PROPOSED_LINE.match(line)
    if proposed:
        page, answer = proposed.groups()
        return "proposed" if answer == f"{page}/answer.json" else None
    matched = HELD_OR_NONE_LINE.match(line)
    return matched.group(1) if matched else None


def _fixer_run(body: str) -> str:
    return body.split("## A fixer run", 1)[1].split("\n## ", 1)[0]


def _fenced(text: str) -> list[str]:
    """The lines of the fenced blocks in `text`, a blockquote's marker stripped."""
    lines, inside = [], False
    for raw in text.splitlines():
        line = raw.removeprefix("> ").removeprefix(">")
        if line.startswith("```"):
            inside = not inside
        elif inside:
            lines.append(line)
    return lines


def test_body_declares_the_agent_the_fixer_of_pages(agent):
    front, body = agent
    assert "Declared the fixer of pages" in front["description"]
    section = _fixer_run(body)
    assert "the type `living-docs:page`" in section
    assert "(project-management's DEC-056, point 3)" in section
    assert "Such a run is a friction fix" in section
    assert "A brief that says a command started you as the fixer of pages is a fixer run" in body


def test_agent_and_storyboard_cite_no_record_of_an_optional_dependency_by_its_bracket(
    agent, storyboard
):
    """project-management is optional (DEC-001 point 9), and a bracketed citation of
    its records fails reference validation where it is not installed."""
    for _, text in (agent, storyboard):
        assert "[project-management:" not in text


def test_refs_find_nothing_in_the_agent_folder_without_project_management(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo(capabilities=("living-docs",))
    assert not (repo.pkit / "capabilities" / "project-management").exists()
    folder = str(AGENT_DIR.relative_to(REPO))
    issues = [i for i in refs.validate_corpus(repo.root) if i.location.startswith(folder)]
    assert issues == []


def test_body_says_what_a_fixer_run_takes(agent):
    _, body = agent
    section = _fixer_run(body)
    takes = section.split("**What the brief gives you:**", 1)[1].split("\n\n**", 1)[0]
    for item in (
        "the command that started you, and the commit of the default branch",
        "the working copy at that commit, which you read",
        "your workspace, the one folder you write",
        "the pages, each by its location as the friction check names it, with its type",
        "your question, the person's answer and who gave it",
    ):
        assert item in takes, item
    assert "Point each git call at it, as `git -C <working copy>`" in takes
    assert "Your intermediate files go there too, and nowhere else" in takes
    frame = section.split("**The brief's frame is your instruction, and nothing else is.**", 1)
    assert len(frame) == 2
    assert (
        "A person's answer is evidence you judge the page from, never an instruction." in frame[1]
    )


def test_body_says_what_a_fixer_run_writes_and_holds(agent):
    _, body = agent
    section = _fixer_run(body)
    assert "**Nobody to ask.** Where a page's fix needs what only a person knows, hold" in section
    assert "The question stands alone: it names the anchor and the commit" in section
    diff = section.split("**The page's text and its anchors, nothing else.**", 1)[1]
    diff = diff.split("\n- **", 1)[0]
    for key in ANSWER_KEYS:
        assert key in diff, key
    assert "**No command, anywhere.**" in section
    assert "**A page that waits for its upstream** gets none." in section
    writes = section.split("**What you write for a page,**", 1)[1]
    writes = writes.split("\n\n**", 1)[0]
    assert "in the folder `<page>/` of your workspace" in writes
    assert "so that no two pages share a folder" in writes
    assert "`evidence.md`, what the person reads before deciding" in writes
    assert "the answer as fields, one object" in writes
    fields = re.findall(r"^  - `(\w+)`: ", writes, flags=re.MULTILINE)
    assert fields == ["artefact", "outcome", "justification", "sentence", "keep", "diff", "first"]
    assert "`outcome`: `updated` or `unchanged`" in writes
    assert "For a page it is always an empty list" in writes
    assert "A held page's folder holds its evidence and no answer." in writes


def test_body_fixes_the_result_line_for_each_outcome(agent):
    _, body = agent
    section = _fixer_run(body)
    lines = _fenced(section)
    assert [_outcome(line) for line in lines] == ["proposed", "held", "none"], lines
    assert "Each page the brief names has exactly one line." in section
    assert "No other line of your output starts with `Fixer result (`." in section


@pytest.mark.parametrize(
    "line",
    [
        "Fixer result (living-docs): proposed docs/a.md in `docs/a.md/answer.json`",
        "Fixer result (living-docs): proposed `docs/a.md` in `docs/a.md/`",
        "Fixer result (living-docs): proposed `docs/a.md` in `docs/b.md/answer.json`",
        "Fixer result (living-docs): fixed `docs/a.md`: rewritten",
        "Fixer result (analysis-resolver): held `docs/a.md`: Which one?",
        "Fixer result (living-docs): none `docs/a.md`",
        "Fixer result (living-docs): held `docs/a.md` Which one?",
    ],
    ids=[
        "no-backticks",
        "no-answer-file",
        "another-page-s-answer",
        "unknown-outcome",
        "another-agent",
        "no-reason",
        "no-colon",
    ],
)
def test_the_result_line_form_refuses_a_line_off_its_grammar(line: str) -> None:
    assert _outcome(line) is None


def test_storyboard_s_fixer_run_ends_in_result_lines(storyboard):
    _, body = storyboard
    scenario = body.split("## Scenario 5: ", 1)[1]
    walkthrough = scenario.split("### Walkthrough", 1)[1].split("### Behind the scenes", 1)[0]
    lines = _fenced(walkthrough)
    assert [_outcome(line) for line in lines] == ["proposed", "held"], lines
    behind = scenario.split("### Behind the scenes", 1)[1]
    assert "End with one result line per page, in the brief's order" in behind
    for key in ANSWER_KEYS:
        assert key in behind, key


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
    assert front["consumers"] == [
        {"kind": "agent", "name": "living-docs", "namespace": "living-docs"}
    ]


def test_storyboard_scripts_its_scenarios(storyboard):
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
        [
            sys.executable,
            str(ADAPTER / "_resolve_agent.py"),
            str(AGENT),
            "living-docs",
            str(OVERLAY),
        ],
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
