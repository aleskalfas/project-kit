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
  result line's three forms, which the storyboard's run follows.

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

#: The result line's three forms (DEC-056 point 3), as the agent's body gives its side of
#: them until project-management states them in full.
LINE = re.compile(
    r"^Fixer result \(analysis-resolver\): "
    r"(?:(?P<proposed>proposed) `(?P<artefact>[^`]+)` in `(?P<file>[^`]+/answer\.json)`"
    r"|(?P<state>held|none) `(?P<other>[^`]+)`: (?P<text>\S.*))$"
)


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
        f"{POINT}: 7 type(s) for 1 agent(s); 7 pass the checks, 0 granted"
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
        f"{POINT}: 7 type(s) for 1 agent(s); 0 pass the checks, 0 granted"
    ]
    messages = {(f["severity"], f["message"]) for f in document["findings"]}
    assert len(document["findings"]) == 7
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
    block = lines.split("```text\n", 1)[1].split("```", 1)[0]
    forms = [line for line in block.splitlines() if line]
    assert [f.split("): ", 1)[1].split(" ", 1)[0] for f in forms] == ["proposed", "held", "none"]
    for form in forms:  # each form, its placeholders filled, is a line the command reads
        filled = (
            form.replace("<artefact>", "tech-docs/analysis/glossary.md#TERM-run")
            .replace("<the question>", "Was it meant?")
            .replace("<the reason>", "It is not stale at the commit.")
        )
        assert LINE.match(filled), form


def _scenario(title: str) -> str:
    _front, body = _front_and_body(STORYBOARD)
    return body.split(f"## Scenario 4: {title}", 1)[1]


def test_the_storyboard_s_run_follows_the_body_s_forms() -> None:
    scenario = _scenario("Started by a command")
    walkthrough = scenario.split("### Walkthrough", 1)[1].split("### Behind the scenes", 1)[0]
    brief = walkthrough.split("**The command's brief:**", 1)[1].split("\n", 1)[0]
    named = re.findall(r"`([^`]+\.md)` \([a-z:-]+\)", brief)
    assert len(named) == 3

    lines = [
        line.removeprefix("> ").strip()
        for line in walkthrough.splitlines()
        if line.removeprefix("> ").startswith("Fixer result")
    ]
    matches = [LINE.match(line) for line in lines]
    assert all(matches), lines
    assert [m["artefact"] or m["other"] for m in matches if m] == named  # one each, in order
    assert [m["proposed"] or m["state"] for m in matches if m] == ["proposed", "held", "none"]

    (proposed,) = [m for m in matches if m and m["proposed"]]
    example = scenario.split("```json\n", 1)[1].split("```", 1)[0]
    answer = json.loads("\n".join(line.strip() for line in example.splitlines()))
    assert tuple(answer) == ANSWER_FIELDS
    assert answer["artefact"] == proposed["artefact"]
    assert proposed["file"] == f"{proposed['artefact']}/answer.json"  # its own folder
    # holds: recorded unchanged, with its justification, and no edit (DEC-001 point 5)
    assert answer["outcome"] == "unchanged" and answer["justification"]
    assert (answer["sentence"], answer["diff"], answer["keep"]) == (None, None, [])
