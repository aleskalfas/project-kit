"""software-analysis: the resolving agent and the rules it proposes by (#888).

Held to software-analysis DEC-001 point 5 — four outcomes, stale versus
regressed decided by intent, a person deciding where intent is unclear, and the
analysis never rewritten to match broken code:

- the **rules** (`scripts/_lib/resolve.py`), on their own: each shape of evidence
  and what it decides — a proposal, a reading left to the agent, or ambiguous;
- **the stop**, in a repository: an anchored file changes so that code a use
  case quotes is gone, and nothing says whether that was meant. `pkit analysis
  propose` answers ambiguous with the question for a person, and nothing is
  written — no artefact, no revalidation, no record — the friction still
  standing. Given the person's answer as a quote, it proposes stale or
  regressed; other shapes propose holds, or leave the change to be read;
- the **agent's files**: its front matter (Write for the workspace, no Edit,
  owning no path), the writers it runs and the one it never does, its
  storyboard's three scenarios, the references, and the deployed copy.
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from click.testing import CliRunner

from project_kit import refs
from project_kit.cli import main
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.analysis_repo import (
    ANALYSIS,
    CAPABILITY,
    JOURNEYS,
    RECORDS,
    REPO,
    SA,
    USE_CASES,
    installed,
    load,
    run_script,
    seed,
)

PROPOSE = SA / "scripts" / "propose.py"
AGENT_DIR = CAPABILITY / "agents" / "analysis-resolver"
AGENT = AGENT_DIR / "analysis-resolver.md"
STORYBOARD = AGENT_DIR / "storyboard.md"
DEPLOYED = REPO / ".claude" / "agents" / "analysis-resolver.md"
ADAPTER = REPO / ".pkit" / "adapters" / "claude-code"
OVERLAY = REPO / ".pkit" / "agents" / "project" / "overlay.yaml"

RUN = "src/run.py"
RUN_SUITE = f"{USE_CASES}/UC-001-run-suite.md"
FIRST_RUN = f"{JOURNEYS}/JRN-001-first-run.md"


# --- the rules, on their own ---------------------------------------------------------------


def _load_resolve() -> ModuleType:
    """`_lib/resolve.py` by its path: it imports nothing of `_lib`, and the capability's
    `_lib` is not importable beside another capability's."""
    path = CAPABILITY / "scripts" / "_lib" / "resolve.py"
    spec = importlib.util.spec_from_file_location("software_analysis_resolve", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


R: Any = _load_resolve()


def _path(state: str = "stale", quoted: tuple[str, ...] = (), gone: tuple[str, ...] = ()) -> Any:
    commits = (R.Commit("4c1d2e9aaaaa", "refactor: split the runner"),)
    return R.Anchor("path", "src/run.py", state, commits, quoted, gone)


def _verdict(anchors: list[Any], state: str = "stale", **intent: str) -> tuple[str, str]:
    verdict: Any = R.propose("UC-001", state, anchors, R.Intent(**intent))
    if isinstance(verdict, R.Proposal):
        return str(verdict.outcome), str(verdict.rule)
    names = {R.Ambiguous: "ambiguous", R.Read: "read", R.Nothing: "none"}
    return names[type(verdict)], str(verdict.rule)


KEPT = _path(quoted=("run_suite",))
GONE = _path(quoted=("run_suite", "fast"), gone=("run_suite",))
DEAD = _path(state="dead-anchor")
UNQUOTED = _path()
RECORD = R.Anchor("record", "ADR-006", "stale")
ACTOR = R.Anchor("artefact", "ACT-tester", "stale")
CURRENT = R.Anchor("path", "src/other.py", "current")
INTENDED = {"intended": "PR #212: 'rename run_suite to execute'"}
UNINTENDED = {"unintended": "tests/test_run.py::test_suite fails at HEAD"}
CONTRADICTED = {"contradicted": "step 2 still says the suite runs on its own"}


@pytest.mark.parametrize(
    ("anchors", "state", "intent", "expected"),
    [
        # nothing-to-resolve
        ([CURRENT], "current", {}, ("none", "nothing-to-resolve")),
        ([], "unanchored", {}, ("none", "nothing-to-resolve")),
        # a stale artefact with no changed anchor moved: read it
        ([CURRENT], "stale", {}, ("read", "nothing-decides")),
        # quoted-code-kept
        ([KEPT, CURRENT], "stale", {}, ("holds", "quoted-code-kept")),
        ([KEPT], "deferred", INTENDED, ("holds", "quoted-code-kept")),
        # ground-gone: stale or regressed, by intent
        ([GONE], "stale", {}, ("ambiguous", "ground-gone")),
        ([DEAD], "stale", {}, ("ambiguous", "ground-gone")),
        ([GONE, KEPT], "stale", {}, ("ambiguous", "ground-gone")),
        ([GONE], "stale", INTENDED, ("analysis-stale", "ground-gone")),
        ([DEAD], "stale", UNINTENDED, ("code-regressed", "ground-gone")),
        ([GONE], "stale", {**INTENDED, **UNINTENDED}, ("ambiguous", "ground-gone")),
        # the agent's reading, or evidence, of a contradiction where code changed
        ([UNQUOTED], "stale", CONTRADICTED, ("ambiguous", "ground-gone")),
        ([UNQUOTED], "stale", {**CONTRADICTED, **INTENDED}, ("analysis-stale", "ground-gone")),
        ([KEPT], "stale", UNINTENDED, ("code-regressed", "ground-gone")),
        # deliberate-change: records and artefacts change only on purpose
        ([RECORD], "stale", CONTRADICTED, ("analysis-stale", "deliberate-change")),
        ([ACTOR], "stale", UNINTENDED, ("ambiguous", "deliberate-change")),
        # nothing-decides
        ([UNQUOTED], "stale", {}, ("read", "nothing-decides")),
        ([RECORD, KEPT], "stale", {}, ("read", "nothing-decides")),
        ([ACTOR], "stale", INTENDED, ("read", "nothing-decides")),
    ],
)
def test_each_shape_of_evidence_decides_what_the_rules_say(
    anchors: list[Any], state: str, intent: dict[str, str], expected: tuple[str, str]
) -> None:
    assert _verdict(anchors, state, **intent) == expected


def test_the_question_names_what_disagrees_the_commit_and_both_readings() -> None:
    verdict = R.propose("UC-001", "stale", [GONE], R.Intent())
    assert isinstance(verdict, R.Ambiguous)
    assert "path:src/run.py no longer holds `run_suite`, which it quotes" in verdict.question
    assert "4c1d2e9aaaaa 'refactor: split the runner'" in verdict.question
    assert "the analysis is stale and UC-001 is updated" in verdict.question
    assert "the code regressed, a defect is reported and UC-001 stays as it is" in (
        verdict.question
    )


def test_the_rules_never_propose_a_gap() -> None:
    """A gap is found by reading the change, never by comparing quotes: over every
    shape and every reading, the rules propose one of the other three or none."""
    shapes = [KEPT, GONE, DEAD, UNQUOTED, RECORD, ACTOR, CURRENT]
    readings = [{}, INTENDED, UNINTENDED, CONTRADICTED, {**INTENDED, **UNINTENDED}]
    proposed = {
        _verdict([one, other], "stale", **reading)[0]
        for one in shapes
        for other in shapes
        for reading in readings
    }
    assert proposed == {"holds", "analysis-stale", "code-regressed", "ambiguous", "read"}


# --- the stop, in a repository ---------------------------------------------------------------


@pytest.fixture
def flagged(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    """An analysis whose UC-001 quotes the code it anchors to, all committed: the
    revalidation point every change below is judged from."""
    repo = installed(make_adopter_repo, monkeypatch)
    repo.commit("feat: the runner", {RUN: "def run_suite(fast=False):\n    print('run')\n"})
    seed(repo)
    text = (repo.root / RUN_SUITE).read_text(encoding="utf-8")
    step = "1. The tester starts `run_suite`, passing `fast` for a quick pass."
    repo.write({RUN_SUITE: text.replace("1. <what the actor or the system does>", step)})
    repo.commit("docs(analysis): the tester, the suite and the first run")
    return repo


def _propose(repo: AdopterRepo, artefact: str, *args: str) -> dict[str, Any]:
    completed = run_script(repo, PROPOSE, artefact, *args, "--json")
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def _analysis(repo: AdopterRepo) -> dict[str, bytes]:
    """Every file of the analysis, byte for byte."""
    root = repo.root / ANALYSIS
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def _explained_state(repo: AdopterRepo, artefact: str) -> str:
    result = CliRunner().invoke(main, ["friction", "explain", artefact, "--json"])
    assert result.exit_code == 0, result.output
    return json.loads(result.output)["state"]


def test_the_stop_ambiguous_writes_nothing_and_asks_a_person(flagged: AdopterRepo) -> None:
    """Code the use case quotes is gone, and nothing says whether that was meant: the
    agent's helper answers ambiguous with the question, and nothing is written."""
    flagged.commit(
        "refactor: tidy the runner", {RUN: "def execute(fast=False):\n    print('run')\n"}
    )
    before = _analysis(flagged)
    assert _explained_state(flagged, "UC-001") == "stale"

    document = _propose(flagged, "UC-001")
    assert document["verdict"] == "ambiguous"
    assert document["rule"] == "ground-gone"
    (anchor,) = document["anchors"]
    assert (anchor["kind"], anchor["value"], anchor["shape"]) == ("path", RUN, "gone")
    assert anchor["quoted"] == ["run_suite", "fast"]
    assert anchor["gone"] == ["run_suite"]
    assert [c["change"] for c in anchor["commits"]] == ["refactor: tidy the runner"]
    assert "Was that meant" in document["question"]
    assert "refactor: tidy the runner" in document["question"]

    # No writer ran: not a byte of the analysis changed, nothing is staged or new, no
    # record exists, and the friction still stands.
    assert _analysis(flagged) == before
    assert flagged.git("status", "--porcelain").stdout == ""
    assert not (flagged.root / RECORDS).exists()
    assert _explained_state(flagged, "UC-001") == "stale"

    human = run_script(flagged, PROPOSE, "UC-001")
    assert human.returncode == 0, human.stderr
    assert "ambiguous (ground-gone)" in human.stdout
    assert "ask a person: " in human.stdout
    assert human.stdout.rstrip().endswith("Read-only: nothing was written.")


def test_the_person_s_answer_decides_stale_or_regressed(flagged: AdopterRepo) -> None:
    flagged.commit(
        "refactor: tidy the runner", {RUN: "def execute(fast=False):\n    print('run')\n"}
    )
    meant = "Yes — run_suite became execute on purpose (#212)."
    assert _propose(flagged, "UC-001", "--intended", meant)["verdict"] == "analysis-stale"
    broken = "Not meant — that's a bug, #231."
    regressed = _propose(flagged, "UC-001", "--unintended", broken)
    assert (regressed["verdict"], regressed["read"]["unintended"]) == ("code-regressed", broken)
    both = _propose(flagged, "UC-001", "--intended", meant, "--unintended", broken)
    assert both["verdict"] == "ambiguous"
    assert flagged.git("status", "--porcelain").stdout == ""


def test_a_deleted_anchor_is_ambiguous_until_intent_is_quoted(flagged: AdopterRepo) -> None:
    flagged.commit("chore: drop the runner", {RUN: None})
    document = _propose(flagged, "UC-001")
    assert document["verdict"] == "ambiguous"
    (anchor,) = document["anchors"]
    assert (anchor["state"], anchor["shape"]) == ("dead-anchor", "gone")
    # The checks name no commit for a dead anchor; the proposal names the one that did it.
    assert [c["change"] for c in anchor["commits"]] == ["chore: drop the runner"]
    assert "path:src/run.py resolves to nothing any more" in document["question"]
    assert "'chore: drop the runner'" in document["question"]
    intended = _propose(flagged, "UC-001", "--intended", "The runner is gone on purpose (#300).")
    assert intended["verdict"] == "analysis-stale"


def test_a_change_that_keeps_the_quoted_code_is_proposed_as_holding(flagged: AdopterRepo) -> None:
    flagged.commit("fix: say what runs", {RUN: "def run_suite(fast=False):\n    print('suite')\n"})
    document = _propose(flagged, "UC-001")
    assert (document["verdict"], document["rule"]) == ("holds", "quoted-code-kept")
    assert document["anchors"][0]["gone"] == []
    # The actor quotes nothing from `src/**`: the same change is the agent's to read.
    assert _propose(flagged, "ACT-tester")["verdict"] == "read"


def test_an_upstream_artefact_changed_is_read_or_stale_never_regressed(
    flagged: AdopterRepo,
) -> None:
    text = (flagged.root / RUN_SUITE).read_text(encoding="utf-8")
    flagged.commit(
        "docs(analysis): the suite reports its time",
        {RUN_SUITE: text.replace("**Done when:** <", "**Done when:** the time is shown; <")},
    )
    document = _propose(flagged, "JRN-001")
    assert (document["verdict"], document["rule"]) == ("read", "nothing-decides")
    assert document["anchors"][0]["shape"] == "deliberate"
    read = "Step 1 of JRN-001 says nothing of the time UC-001 now shows."
    assert _propose(flagged, "JRN-001", "--contradicted", read)["verdict"] == "analysis-stale"
    assert (flagged.root / FIRST_RUN).read_text(encoding="utf-8") == (
        flagged.git("show", f"HEAD:{FIRST_RUN}").stdout
    )


def test_an_artefact_that_cannot_be_explained_is_refused(flagged: AdopterRepo) -> None:
    completed = run_script(flagged, PROPOSE, "UC-404", "--json")
    assert completed.returncode == 1
    assert completed.stdout == ""
    assert completed.stderr.startswith("cannot propose: ")


@pytest.mark.parametrize("namespace", ["analysis", "software-analysis"])
def test_propose_is_reached_under_the_capability_and_its_alias(
    flagged: AdopterRepo, namespace: str
) -> None:
    result = CliRunner().invoke(main, [namespace, "--help"])
    assert result.exit_code == 0, result.output
    assert "propose " in result.output


# --- the agent's files -------------------------------------------------------------------------

#: The writers the agent runs, after a person's confirmation, and the one it never runs.
WRITERS = ("pkit friction revalidate", "pkit friction defer", "pkit analysis new revalidation")
NEVER = "pkit friction record-status"

SCENARIOS = ("Happy path", "The stop", "A regression, recorded")
SCENARIO_PARTS = ("**Trigger.**", "**Preconditions.**", "### Walkthrough", "### Behind the scenes")


def _split(path: Path) -> tuple[dict[str, Any], str]:
    _, front, body = path.read_text(encoding="utf-8").split("---\n", 2)
    return load(front) or {}, body


def test_the_agent_writes_only_through_the_writers_and_the_workspace() -> None:
    front, body = _split(AGENT)
    assert front["name"] == "analysis-resolver"
    assert set(front["tools"]) == {"Read", "Glob", "Grep", "Bash", "Write"}  # no Edit
    assert front["owns"] == []
    assert "model" not in front and "effort" not in front
    assert front["storyboards"] == [STORYBOARD.name]
    assert f"`{STORYBOARD.name}`" in body
    for writer in WRITERS:
        assert writer in body, writer
    assert f"never run `{NEVER}`" in body
    assert "`.agent-workspace/analysis-resolver/<change>/`" in body
    assert "**On `ambiguous` you stop.**" in body


def test_the_storyboard_scripts_the_three_scenarios() -> None:
    front, body = _split(STORYBOARD)
    assert front["consumers"] == [
        {"kind": "agent", "name": "analysis-resolver", "namespace": "software-analysis"}
    ]
    assert "## Framing" in body and "## Tone" in body
    sections = re.split(r"^## Scenario \d+: ", body, flags=re.MULTILINE)[1:]
    titles = [section.splitlines()[0] for section in sections]
    assert len(titles) == len(SCENARIOS)
    for title, expected in zip(titles, SCENARIOS, strict=True):
        assert title.startswith(expected), title
    for section in sections:
        for part in SCENARIO_PARTS:
            assert part in section, (section.splitlines()[0], part)
    stop = sections[1]
    assert "**Write nothing in the repository**" in stop


def test_refs_find_nothing_in_the_agent_folder() -> None:
    folder = str(AGENT_DIR.relative_to(REPO))
    assert [i for i in refs.validate_corpus(REPO) if i.location.startswith(folder)] == []
    (agent,) = [a for a in refs.load_artifacts(REPO) if a.name == "analysis-resolver"]
    assert (agent.kind, agent.capability) == ("agent", "software-analysis")


def _deploy_marker() -> str:
    script = (ADAPTER / "deploy-agents.sh").read_text(encoding="utf-8")
    match = re.search(r'^MARKER="(.+)"$', script, flags=re.MULTILINE)
    assert match, "deploy-agents.sh no longer declares MARKER"
    return match.group(1)


def test_the_deployed_copy_matches_the_source() -> None:
    completed = subprocess.run(
        [sys.executable, str(ADAPTER / "_resolve_agent.py"), str(AGENT), AGENT.stem, str(OVERLAY)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    first, rest = completed.stdout.split("\n", 1)
    assert DEPLOYED.read_text(encoding="utf-8") == f"{first}\n{_deploy_marker()}\n{rest}", (
        "stale deployed copy: run `bash .pkit/adapters/claude-code/deploy-agents.sh`"
    )
    front, _body = _split(DEPLOYED)
    assert front["storyboards"] == [str(STORYBOARD.relative_to(REPO))]
