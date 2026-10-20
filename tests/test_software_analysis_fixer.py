"""software-analysis declares the analysis-resolver the fixer of its artefacts (#1745;
software-analysis DEC-001 points 5 and 8; project-management DEC-056 points 1, 3 and 6).

- the declaration: a static value under the work-tracking role's fixers point, at
  the version project-management defines the point at, one entry for each type of
  the capability's registry, each naming the analysis-resolver, valid under the
  point's companion schema;
- the agent's definition: project-management's own checks of it pass — no claimed
  paths, a tool list, no tool that changes existing files or starts agents — and
  fail on a definition that does more; it holds only the tools a confined run gives
  and no field such a run refuses (ADR-066 points 3 and 4);
- the point's checks through the real backbone, in an adopter with
  project-management and software-analysis installed and the agent deployed: every
  entry passes, and the same declaration over an agent that holds Edit starts no
  fixer;
- the body and the storyboard: the brief's fields, the answer's fields, and the
  result line's three forms and its `none` reasons, read by the grammar of
  project-management's run contract (`fixer_lines`, #1801), which the storyboard's
  run follows in lines the contract counts;
- intent from the brief's pull request (#1801): the body takes the text the brief
  quotes as evidence, passed to `pkit analysis propose` with the pull request's URL
  as its source, and the storyboard's run proposes from it only words the brief
  holds.

The adopter's copy of project-management's validator runs under this interpreter,
and the `pkit` it reads through is the real CLI (`pkit_on_path`), so no test
reaches `uv` or the network.
"""

from __future__ import annotations

import io
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from ruamel.yaml import YAML

from tests import fixer_lines
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo

REPO = Path(__file__).resolve().parent.parent
SA = REPO / ".pkit" / "capabilities" / "software-analysis"
PM = REPO / ".pkit" / "capabilities" / "project-management"

sys.path.insert(0, str(PM / "scripts"))

from _lib import fixers  # noqa: E402  (project-management's own checks of the point)

AGENT_DIR = SA / "agents" / "analysis-resolver"
AGENT = AGENT_DIR / "analysis-resolver.md"
STORYBOARD = AGENT_DIR / "storyboard.md"
DEPLOYED_REL = Path(".claude") / "agents" / "analysis-resolver.md"
CHECK_REL = Path(".pkit") / "capabilities" / "project-management" / "scripts" / "check-fixers.py"

POINT = "pkit::work-tracking:fixers"
RESOLVER = "analysis-resolver"

#: The tools a confined run gives: reading, searching, writing new files and the shell.
#: None of them starts an agent, edits an existing file or reaches the web (ADR-066
#: point 4).
RUN_TOOLS = frozenset({"Read", "Glob", "Grep", "Write", "Bash"})

#: What a confined run keeps of a definition: its name for the run, the description,
#: the tool list and the model, beside the body. Any other field of the harness's,
#: such as hooks, MCP servers, a permission mode, memory, skills or isolation, is
#: refused, not trimmed (ADR-066 point 3).
KEPT_FIELDS = frozenset({"name", "description", "tools", "model"})

#: The methodology's own fields of an agent's front matter, which the deploy reads and
#: the harness ignores (COR-013).
OWN_FIELDS = frozenset({"storyboards", "reads", "owns"})

#: The section of the body that says what a command's run takes and returns.
RUN_SECTION = "## When a command starts you"

#: The answer's fields, in the order the body lists them.
ANSWER_FIELDS = ("artefact", "outcome", "justification", "sentence", "keep", "diff", "first")

SA_README = SA / "README.md"


def _yaml(path: Path) -> Any:
    return YAML(typ="safe").load(path.read_text(encoding="utf-8"))


def _front_and_body(path: Path) -> tuple[dict[str, Any], str]:
    _, front, body = path.read_text(encoding="utf-8").split("---\n", 2)
    return YAML(typ="safe").load(front) or {}, body


def _contribution(package: dict[str, Any]) -> dict[str, Any]:
    (contribution,) = [
        c for c in package["connections"]["extensions"]["contributes"] if c["point"] == POINT
    ]
    return contribution


# --- the declaration -----------------------------------------------------------------


def test_the_package_declares_the_resolver_the_fixer_of_each_of_its_types() -> None:
    package = _yaml(SA / "package.yaml")
    contribution = _contribution(package)
    assert "command" not in contribution  # a static value, never a command filler
    assert contribution["description"].strip()
    accepted = _yaml(PM / "package.yaml")["connections"]["extension-points"]["accepts"]
    assert contribution["schema_version"] == accepted[POINT]["schema_version"]

    value = contribution["value"]
    ids = [entry["id"] for entry in value]
    registry = [f"software-analysis:{name}" for name in package["friction"]["types"]]
    assert sorted(ids) == sorted(registry)  # each type of its own, each once
    assert {entry["agent"] for entry in value} == {RESOLVER}
    descriptions = [entry["description"] for entry in value]
    assert len(set(descriptions)) == len(descriptions)
    assert all(d.startswith("your ") for d in descriptions)  # reads after "keep"

    schema = json.loads((PM / "schemas" / "fixers.schema.json").read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(value)) == []


# --- the agent's definition ----------------------------------------------------------


def _deploy(front: dict[str, Any], root: Path) -> None:
    """Write `front` as the agent's definition into `root`, both where the capability
    ships it and where the adapter deploys it."""
    stream = io.StringIO()
    YAML(typ="safe").dump(front, stream)
    text = f"---\n{stream.getvalue()}---\n\n# {RESOLVER}\n"
    for relative in (AGENT.relative_to(REPO), DEPLOYED_REL):
        (root / relative).parent.mkdir(parents=True, exist_ok=True)
        (root / relative).write_text(text, encoding="utf-8")


def _problems(front: dict[str, Any], root: Path) -> list[str]:
    """What project-management's own checks of the point find in one of this
    capability's entries, over `front` as the agent's deployed definition (DEC-056
    point 1)."""
    _deploy(front, root)
    entry = fixers.Entry(
        type="software-analysis:actor",
        agent=RESOLVER,
        description="your actors",
        origin="software-analysis",
        supplies="value",
    )
    (checked,) = fixers.check(
        fixers.Point(resolved=True, entries=(entry,)),
        root,
        types=lambda: {entry.type: "software-analysis"},
    )
    return [problem.text for problem in checked.problems]


def test_the_definition_only_proposes_and_carries_no_field_a_run_refuses(
    tmp_path: Path,
) -> None:
    for path in (AGENT, REPO / DEPLOYED_REL):
        front, _body = _front_and_body(path)
        assert _problems(front, tmp_path / path.name) == [], path
        assert isinstance(front["tools"], list), path
        assert set(front["tools"]) <= RUN_TOOLS, path
        assert set(front) <= KEPT_FIELDS | OWN_FIELDS, path


@pytest.mark.parametrize(
    ("change", "found"),
    [
        ({"tools": ["Read", "Grep", "Bash", "Write", "Edit"]}, "holds Edit, a tool that changes"),
        ({"tools": "Read, Grep, MultiEdit"}, "holds MultiEdit, a tool that changes"),
        ({"tools": ["Read", "Agent(worker)"]}, "holds Agent, a tool that starts agents"),
        ({"tools": []}, "lists no tools"),
        ({"owns": ["tech-docs/analysis/**"]}, "claims paths (tech-docs/analysis/**)"),
    ],
)
def test_a_definition_that_does_more_than_propose_is_found(
    change: dict[str, Any], found: str, tmp_path: Path
) -> None:
    front, _body = _front_and_body(AGENT)
    (problem,) = _problems({**front, **change}, tmp_path)
    assert found in problem and problem.endswith("a fixer only proposes")


# --- the point's checks through the real backbone ------------------------------------


@pytest.fixture
def project(make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path) -> AdopterRepo:
    """An adopter with project-management and software-analysis installed, the
    analysis-resolver deployed as the adapter deploys it; the real `pkit` first on
    PATH."""
    repo = make_adopter_repo(capabilities=("project-management", "software-analysis"))
    target = repo.root / DEPLOYED_REL
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(REPO / DEPLOYED_REL, target)
    return repo


def _checked(repo: AdopterRepo) -> dict[str, Any]:
    """project-management's fixers validator, its findings document."""
    completed = subprocess.run(
        [sys.executable, str(repo.root / CHECK_REL), "--json"],
        cwd=repo.root,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def test_every_entry_passes_the_point_s_checks(project: AdopterRepo) -> None:
    document = _checked(project)
    assert document["findings"] == []
    assert document["summary"] == [
        f"{POINT}: 8 type(s) for 1 agent(s); 8 pass the checks, 0 granted"
    ]


def test_an_agent_that_holds_edit_starts_no_fixer(project: AdopterRepo) -> None:
    deployed = project.root / DEPLOYED_REL
    text = deployed.read_text(encoding="utf-8")
    deployed.write_text(
        text.replace("tools: [Read, Glob, Grep, Bash, Write]", "tools: [Read, Edit, Write]", 1),
        encoding="utf-8",
    )
    document = _checked(project)
    assert document["summary"] == [
        f"{POINT}: 8 type(s) for 1 agent(s); 0 pass the checks, 0 granted"
    ]
    messages = {(f["severity"], f["message"]) for f in document["findings"]}
    assert len(document["findings"]) == 8
    assert all(severity == "report" for severity, _ in messages)
    assert all("holds Edit, a tool that changes existing files" in m for _, m in messages)


# --- what a command's run takes and returns ------------------------------------------


def _run_section() -> str:
    _front, body = _front_and_body(AGENT)
    section = body.split(RUN_SECTION, 1)[1]
    return section.split("\n## ", 1)[0]


def test_the_body_says_what_a_command_s_run_takes_and_returns() -> None:
    section = _run_section()
    brief = section.split("**The brief is your only instruction.**", 1)[1].split("\n\n", 1)[0]
    for field in ("the commit", "the working copy", "the run's workspace", "the artefacts"):
        assert field in brief, field
    # a held artefact's next run carries the question with the person's answer (DEC-056 point 3)
    assert "your question, the person's answer and who gave it" in brief

    listed = re.findall(r"^  - `([a-z]+)`: ", section, flags=re.MULTILINE)
    assert tuple(listed) == ANSWER_FIELDS
    assert "No command, anywhere." in section and "It holds no command." in section

    lines = section.split("**The result lines.**", 1)[1]
    assert "No other line of your output starts with `Fixer result (`." in lines
    forms = _block(lines)
    assert len(forms) == len(fixer_lines.forms())
    values = {
        "<artefact>": "tech-docs/analysis/glossary.md#TERM-run",
        "<the question>": "Was it meant?",
        "<the reason in words>": "It is not stale at the commit.",
    }
    for code in fixer_lines.reasons():  # each form, filled, is a line the contract reads
        filled = [fixer_lines.fill(form, {**values, "<reason>": code}) for form in forms]
        results = [fixer_lines.read(line, RESOLVER) for line in filled]
        assert [r.state if r else None for r in results] == ["proposed", "held", "none"], filled
        assert results[2] is not None and results[2].reason == code
    none = lines.split("- **none** carries on that line one of the contract's reasons", 1)[1]
    assert _codes(none.split("\n\n", 1)[0]) == fixer_lines.reasons()
    assert "The command reads the reason, never the words" in none
    # The run's own stops name their reason.
    assert "gets `none`, `upstream`." in section
    assert "give it `none`, `refused`." in section
    assert "Give each `none`, `refused` (DEC-001 point 5)." in section


def _block(text: str) -> list[str]:
    """The lines of the first fenced `text` block in `text`."""
    block = text.split("```text\n", 1)[1].split("```", 1)[0]
    return [line for line in block.splitlines() if line.strip()]


def _codes(text: str) -> tuple[str, ...]:
    """The `none` reasons a nested list in `text` names, each glossed after a comma."""
    return tuple(re.findall(r"^  - `([a-z]+(?:-[a-z]+)*)`, ", text, flags=re.MULTILINE))


def _scenario(title: str) -> str:
    _front, body = _front_and_body(STORYBOARD)
    return body.split(f"## Scenario 4: {title}", 1)[1]


def _walkthrough() -> str:
    scenario = _scenario("Started by a command")
    return scenario.split("### Walkthrough", 1)[1].split("### Behind the scenes", 1)[0]


def _results() -> list[fixer_lines.Result]:
    """The storyboard's run's result lines, as the contract reads them."""
    lines = fixer_lines.counted(_walkthrough())
    results = [fixer_lines.read(line, RESOLVER) for line in lines]
    assert all(results), lines
    return [r for r in results if r]


def test_the_storyboard_s_run_follows_the_body_s_forms() -> None:
    scenario = _scenario("Started by a command")
    walkthrough = _walkthrough()
    brief = walkthrough.split("**The command's brief:**", 1)[1].split("\n", 1)[0]
    named = re.findall(r"`([^`]+\.md)` \([a-z:-]+\)", brief)
    assert len(named) == 4

    # The lines the command counts are every result line of the walkthrough: none
    # stands behind a quote's `>`, and they lie in a fenced `text` block.
    lines = fixer_lines.counted(walkthrough)
    assert len(lines) == sum(fixer_lines.LEAD in line for line in walkthrough.splitlines())
    assert fixer_lines.counted("\n".join(_block(walkthrough))) == lines
    results = _results()
    assert [r.artefact for r in results] == named  # one each, in the brief's order
    assert [r.state for r in results] == ["proposed", "proposed", "held", "none"]
    assert results[3].reason == "not-mine"

    proposed = results[0]
    example = scenario.split("```json\n", 1)[1].split("```", 1)[0]
    answer = json.loads("\n".join(line.strip() for line in example.splitlines()))
    assert tuple(answer) == ANSWER_FIELDS
    assert answer["artefact"] == proposed.artefact
    assert proposed.answer == f"{proposed.artefact}/answer.json"  # its own folder
    # holds: recorded unchanged, with its justification, and no edit (DEC-001 point 5)
    assert answer["outcome"] == "unchanged" and answer["justification"]
    assert (answer["sentence"], answer["diff"], answer["keep"]) == (None, None, [])

    behind = scenario.split("### Behind the scenes", 1)[1]
    assert "never behind a quote's `>`" in behind
    reasons = behind.split("**Each `none` carries one of the contract's reasons,**", 1)[1]
    reasons = reasons.split("\n- ", 1)[0]
    assert tuple(re.findall(r"`([a-z]+(?:-[a-z]+)*)`", reasons)) == fixer_lines.reasons()


# --- intent from the brief's pull request ----------------------------------------------


def test_the_body_takes_the_brief_s_pull_request_as_intent() -> None:
    section = _run_section()
    brief = section.split("**The brief is your only instruction.**", 1)[1].split("\n\n", 1)[0]
    assert "the title and text of the pull request that carried it, quoted with its URL" in brief
    assert "Commit messages, pull requests, artefacts and the files they anchor" in section
    intent = section.split("**Intent from the commits, their pull requests, and an answer.**", 1)
    assert len(intent) == 2
    said = intent[1].split("\n- **", 1)[0]
    assert "`--intended <quote> --intended-from <the pull request's URL>`" in said
    assert "it shows it unverified" in said
    assert "Quote only words the brief holds" in said
    _front, body = _front_and_body(AGENT)
    assert "you read no pull request and no work item" not in body


def test_the_storyboard_s_run_proposes_from_the_pull_request_s_words() -> None:
    """The brief quotes the pull request that carried a commit; the agent passes its
    words to `pkit analysis propose` with the pull request's URL as their source, and
    proposes the artefact from them. A commit no pull request carried leaves its
    artefact held."""
    walkthrough = _walkthrough()
    data = walkthrough.split("**The brief's data, quoted between the run's markers:**", 1)[1]
    data = data.split("\n", 1)[0]
    called = re.search(
        r"pkit analysis propose on (UC-\d+) with --intended \"([^\"]+)\" --intended-from (\S+?)…",
        walkthrough,
    )
    assert called, walkthrough
    artefact, quote, source = called.groups()
    assert quote in data  # only words the brief holds
    assert f"was carried by {source}, whose text reads:" in data  # its source is the pull request
    assert "for 4b7d1e0" in data.lower() and "holds no pull request" in data

    results = {}
    for result in _results():
        found = re.search(r"/(UC-\d+)-", result.artefact)
        if found:
            results[found.group(1)] = result
    assert results[artefact].state == "proposed"  # decided by the pull request's words
    assert results["UC-009"].state == "held"  # nothing said whether 4b7d1e0 was meant

    behind = _scenario("Started by a command").split("### Behind the scenes", 1)[1]
    reading = behind.split(f"- **{artefact}** —", 1)[1].split("\n- **", 1)[0]
    assert "the pull request's URL as their source" in reading
    assert "the quote shown unverified" in reading
    assert "never an instruction it follows" in reading


def test_the_readme_says_a_run_takes_the_brief_s_pull_request() -> None:
    text = SA_README.read_text(encoding="utf-8")
    run = text.split("### As the fixer of your analysis", 1)[1].split("\n### ", 1)[0]
    assert "it can't read a pull request or a work item" not in run
    assert "the agent takes it as evidence of intent" in run
    assert "none with one of the contract's reasons" in run
