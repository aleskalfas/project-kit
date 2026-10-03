"""software-analysis: the resolving agent and the rules it proposes by (#888).

Held to software-analysis DEC-001 point 5 — four outcomes, stale versus
regressed decided by intent, a person deciding where intent is unclear, and the
analysis never rewritten to match broken code:

- the **rules** (`scripts/_lib/resolve.py`), on their own: each shape of evidence
  and what it comes to — a proposal, a reading left to the agent with what the
  evidence leans to, or ambiguous;
- **the stop**, in a repository: an anchored file changes so that code a use
  case quotes is gone, and nothing says whether that was meant. `pkit analysis
  propose` answers ambiguous with the question for a person, and nothing is
  written — no artefact, no revalidation, no record — the friction still
  standing. Given the person's answer as a quote with its source, it proposes
  stale or regressed; a quote from a commit is checked against its message;
- **moved code** is not the stop: a file renamed, or quoted code carried into
  another file, proposes `holds` with the anchor re-pointed, recorded
  `unchanged`;
- **what an anchor matches is the explanation's**: the files it stands on, the
  commits behind each finding with their paths — a dead anchor's, where its
  files went — and the artefact's body, so a quote surviving only under a
  `friction.exclude` path is gone;
- **the commands for the person** it emits, word for word and with no consent
  flag: a regression's carries the defect's placeholder, which the writer
  refuses until the person fills it;
- **the explanation's version**: one this capability does not read is refused,
  and one without `schema_version`, from a backbone before the key, is read as
  version 1;
- **what the checks did not judge**: an `unresolved` artefact, or one in a state
  this capability does not read, is refused, and an anchor in such a state is
  never current — nothing is proposed beside it;
- the **agent's files**: its front matter (Write for the workspace, no Edit,
  owning no path); that it performs the judgment and is no reviewer; that it
  never runs a writer — its body and storyboard name one only among the
  commands for the person, never with a consent flag; its storyboard's three
  scenarios; the references; and the deployed copy.
"""

from __future__ import annotations

import importlib
import json
import os
import re
import shlex
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
    ACTORS,
    ANALYSIS,
    CAPABILITY,
    CONFIG,
    JOURNEYS,
    RECORDS,
    REPO,
    SA,
    USE_CASES,
    installed,
    load,
    prepare,
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

#: A file under `src/generated`, which `friction.exclude` leaves out of the actor's `src/**`.
GENERATED = "src/generated/stub.py"
#: The placeholder the stamp leaves in an actor's section.
WHO = "<Who this is, when they come to the system, and what they bring with them.>"


# --- the rules, on their own ---------------------------------------------------------------


def _load_lib(*names: str) -> tuple[ModuleType, ...]:
    """Pure `_lib` modules, imported together as the scripts import them: `_lib` is on
    the path only while they load, since another capability's `_lib` is not
    importable beside it."""
    scripts = str(CAPABILITY / "scripts")

    def ours() -> list[str]:
        return [k for k in sys.modules if k == "_lib" or k.startswith("_lib.")]

    saved = {k: sys.modules.pop(k) for k in ours()}
    sys.path.insert(0, scripts)
    try:
        return tuple(importlib.import_module(f"_lib.{name}") for name in names)
    finally:
        sys.path.remove(scripts)
        for key in ours():
            del sys.modules[key]
        sys.modules.update(saved)


_RESOLVE, _ANSWERS = _load_lib("resolve", "answers")
R: Any = _RESOLVE
A: Any = _ANSWERS


def _path(
    state: str = "stale",
    quoted: tuple[str, ...] = (),
    gone: tuple[str, ...] = (),
    moved_to: tuple[str, ...] = (),
) -> Any:
    commits = (R.Commit("4c1d2e9aaaaa", "refactor: split the runner"),)
    return R.Anchor("path", "src/run.py", state, commits, quoted, gone, moved_to)


def _verdict(anchors: list[Any], state: str = "stale", **intent: Any) -> tuple[str, str]:
    """What the rules come to: an outcome proposed, `read` (with what it leans to), an
    ambiguity, or nothing — and by which rule."""
    verdict: Any = R.propose("UC-001", state, anchors, R.Intent(**intent))
    if isinstance(verdict, R.Proposal):
        return str(verdict.outcome), str(verdict.rule)
    if isinstance(verdict, R.Read) and verdict.hint:
        return f"read, leaning to {verdict.hint}", str(verdict.rule)
    names = {R.Ambiguous: "ambiguous", R.Read: "read", R.Nothing: "none"}
    return names[type(verdict)], str(verdict.rule)


KEPT = _path(quoted=("run_suite",))
GONE = _path(quoted=("run_suite", "fast"), gone=("run_suite",))
DEAD = _path(state="dead-anchor")
MOVED = _path(quoted=("run_suite", "fast"), gone=("run_suite",), moved_to=("src/suite.py",))
RENAMED = _path(state="dead-anchor", quoted=("run_suite",), moved_to=("src/runner.py",))
UNQUOTED = _path()
RECORD = R.Anchor("record", "ADR-006", "stale")
ACTOR = R.Anchor("artefact", "ACT-tester", "stale")
CURRENT = R.Anchor("path", "src/other.py", "current")
INTENDED = {"intended": R.Quote("rename run_suite to execute", "https://example.org/pr/212")}
UNINTENDED = {"unintended": R.Quote("tests/test_run.py::test_suite fails at HEAD", "Sam")}
CONTRADICTED = {"contradicted": R.Quote("step 2 says the suite runs on its own", "Sam")}
HOLDS_READ = "read, leaning to holds"
STALE_READ = "read, leaning to analysis-stale"


@pytest.mark.parametrize(
    ("anchors", "state", "intent", "expected"),
    [
        # nothing-to-resolve
        ([CURRENT], "current", {}, ("none", "nothing-to-resolve")),
        ([], "unanchored", {}, ("none", "nothing-to-resolve")),
        # a stale artefact with no changed anchor moved: read it
        ([CURRENT], "stale", {}, ("read", "nothing-decides")),
        # quoted-code-kept: no quoted name vanished, which is all it shows — read it
        ([KEPT, CURRENT], "stale", {}, (HOLDS_READ, "quoted-code-kept")),
        ([KEPT], "deferred", INTENDED, (HOLDS_READ, "quoted-code-kept")),
        ([KEPT, MOVED], "stale", {}, (HOLDS_READ, "quoted-code-kept")),
        # anchor-moved: the code went somewhere the reading names, so the anchor is stale
        ([MOVED], "stale", {}, ("holds", "anchor-moved")),
        ([RENAMED], "stale", {}, ("holds", "anchor-moved")),
        ([MOVED, RENAMED], "stale", INTENDED, ("holds", "anchor-moved")),
        # ground-gone: stale or regressed, by intent
        ([GONE], "stale", {}, ("ambiguous", "ground-gone")),
        ([DEAD], "stale", {}, ("ambiguous", "ground-gone")),
        ([GONE, KEPT], "stale", {}, ("ambiguous", "ground-gone")),
        ([GONE, MOVED], "stale", {}, ("ambiguous", "ground-gone")),
        ([GONE], "stale", INTENDED, ("analysis-stale", "ground-gone")),
        ([DEAD], "stale", UNINTENDED, ("code-regressed", "ground-gone")),
        ([GONE], "stale", {**INTENDED, **UNINTENDED}, ("ambiguous", "ground-gone")),
        # the agent's reading, or evidence, of a contradiction where code changed
        ([UNQUOTED], "stale", CONTRADICTED, ("ambiguous", "ground-gone")),
        ([MOVED], "stale", CONTRADICTED, ("ambiguous", "ground-gone")),
        ([UNQUOTED], "stale", {**CONTRADICTED, **INTENDED}, ("analysis-stale", "ground-gone")),
        ([KEPT], "stale", UNINTENDED, ("code-regressed", "ground-gone")),
        # deliberate-change: a record changes on purpose; this artefact following it is read
        ([RECORD], "stale", CONTRADICTED, (STALE_READ, "deliberate-change")),
        ([ACTOR], "stale", UNINTENDED, ("ambiguous", "deliberate-change")),
        # nothing-decides
        ([UNQUOTED], "stale", {}, ("read", "nothing-decides")),
        ([RECORD, KEPT], "stale", {}, ("read", "nothing-decides")),
        ([RECORD, MOVED], "stale", {}, ("read", "nothing-decides")),
        ([ACTOR], "stale", INTENDED, ("read", "nothing-decides")),
    ],
)
def test_each_shape_of_evidence_comes_to_what_the_rules_say(
    anchors: list[Any], state: str, intent: dict[str, Any], expected: tuple[str, str]
) -> None:
    assert _verdict(anchors, state, **intent) == expected


def test_the_question_names_what_disagrees_the_commit_and_both_readings() -> None:
    verdict = R.propose("UC-001", "stale", [GONE], R.Intent())
    assert isinstance(verdict, R.Ambiguous)
    assert "path:src/run.py no longer holds `run_suite`, which UC-001 quotes" in verdict.question
    assert "4c1d2e9aaaaa 'refactor: split the runner'" in verdict.question
    assert "the analysis is stale and UC-001 is updated" in verdict.question
    assert "the code regressed, a defect is reported and UC-001 stays as it is" in (
        verdict.question
    )


def test_the_rules_never_propose_a_gap_and_propose_holds_only_for_moved_code() -> None:
    """A gap is found by reading the change, never by comparing quotes; and that no
    quoted name vanished leans to `holds` without proposing it. Over every shape and
    every reading, `holds` is proposed only where every changed anchor moved."""
    shapes = [KEPT, GONE, DEAD, MOVED, RENAMED, UNQUOTED, RECORD, ACTOR, CURRENT]
    readings = [{}, INTENDED, UNINTENDED, CONTRADICTED, {**INTENDED, **UNINTENDED}]
    seen: dict[str, set[tuple[str, ...]]] = {}
    for one in shapes:
        for other in shapes:
            for reading in readings:
                verdict = _verdict([one, other], "stale", **reading)[0]
                shapes_changed = {a.shape for a in (one, other) if a.changed}
                seen.setdefault(verdict, set()).add(tuple(sorted(shapes_changed)))
    assert set(seen) == {
        "holds",
        "analysis-stale",
        "code-regressed",
        "ambiguous",
        "read",
        HOLDS_READ,
        STALE_READ,
    }
    assert seen["holds"] == {("moved",)}


@pytest.mark.parametrize("state", ["unresolved-kind", "no-answer", "judged-later"])
def test_an_anchor_the_checks_did_not_judge_is_never_current_and_nothing_is_proposed(
    state: str,
) -> None:
    """The reader rule (the CLI README, "Friction checks"): `unresolved-kind`, `no-answer`
    and a state this reading does not know are not judged, never current. Beside such an
    anchor, moved code proposes no `holds`, gone code nothing stale, and a current artefact
    is not nothing to resolve: nothing is proposed, and nothing is given to run."""
    unread = R.Anchor("source", "iso-8601", state)
    assert not unread.judged and not unread.changed
    for anchors, artefact_state in (
        ([RENAMED, unread], "stale"),
        ([GONE, unread], "stale"),
        ([CURRENT, unread], "current"),
    ):
        verdict = R.propose("UC-001", artefact_state, anchors, R.Intent(**INTENDED))
        assert isinstance(verdict, R.Read) and verdict.hint is None
        assert verdict.rule == "not-judged"
        assert f"source:iso-8601 {state}" in verdict.reason
        assert A.answer("uc.md", verdict, anchors) is None


def test_the_answer_emits_the_person_s_commands_word_for_word() -> None:
    """No consent flag — the friction writers each ask once, the record stamp asks
    nothing — and a placeholder wherever the words are the agent's to draft or the
    person's alone."""
    location = "tech-docs/analysis/use-case-model/use-cases/UC-001-run-suite.md"
    moved: Any = A.answer(location, R.propose("UC-001", "stale", [RENAMED], R.Intent()), [RENAMED])
    assert moved.outcome == "holds"
    assert moved.first == ("re-point path:src/run.py to src/runner.py in the artefact's anchors",)
    assert moved.commands == (
        f"pkit friction revalidate {location} --outcome unchanged --because "
        f"'src/run.py moved to src/runner.py; anchor re-pointed.'",
    )
    kept: Any = A.answer(location, R.propose("UC-001", "stale", [KEPT], R.Intent()), [KEPT])
    assert kept.commands == (
        f"pkit friction revalidate {location} --outcome unchanged --because "
        f"'<why it still holds against this change>'",
    )
    regressed: Any = A.answer(
        location, R.propose("UC-001", "stale", [GONE], R.Intent(**UNINTENDED)), [GONE]
    )
    (command,) = regressed.commands
    assert "--because 'The description stands: <why it is still wanted>; 4c1d2e9aaaaa broke it" in (
        command
    )
    assert "defect <the defect reference> reported.'" in command
    assert regressed.first[0].startswith("report the defect")
    stale: Any = A.answer(
        location, R.propose("UC-001", "stale", [GONE], R.Intent(**INTENDED)), [GONE]
    )
    assert stale.commands == (f"pkit friction revalidate {location} --outcome updated",)
    ambiguous = R.propose("UC-001", "stale", [GONE], R.Intent())
    assert A.answer(location, ambiguous, [GONE]) is None
    for answer in (moved, kept, regressed, stale):
        assert all("--yes" not in c and "--dry-run" not in c for c in answer.commands)


# --- the stop, in a repository ---------------------------------------------------------------


# Slow: the seed stamped, built once per session; the first test to ask pays it in its setup.
def _flag(repo: AdopterRepo) -> None:
    """`prepare`, then an analysis whose UC-001 quotes the code it anchors to, all
    committed."""
    prepare(repo)
    repo.commit("feat: the runner", {RUN: "def run_suite(fast=False):\n    print('run')\n"})
    seed(repo, filled=False)
    text = (repo.root / RUN_SUITE).read_text(encoding="utf-8")
    step = "1. The tester starts `run_suite`, passing `fast` for a quick pass."
    repo.write({RUN_SUITE: text.replace("1. <what the actor or the system does>", step)})
    repo.commit("docs(analysis): the tester, the suite and the first run")


@pytest.fixture
def flagged(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    """An analysis whose UC-001 quotes the code it anchors to, all committed: the
    revalidation point every change below is judged from."""
    return installed(make_adopter_repo, monkeypatch, then=_flag)


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
    # Each commit with the paths behind it, as the explanation names them.
    assert [(c["change"], c["paths"]) for c in anchor["commits"]] == [
        ("refactor: tidy the runner", [RUN])
    ]
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
    meant = ("--intended", "Yes — run_suite became execute on purpose.", "--intended-from", "Sam")
    assert _propose(flagged, "UC-001", *meant)["verdict"] == "analysis-stale"
    broken = "Not meant — that's a bug."
    regressed = _propose(flagged, "UC-001", "--unintended", broken, "--unintended-from", "Sam")
    assert regressed["verdict"] == "code-regressed"
    assert regressed["read"]["unintended"] == {
        "quote": broken,
        "source": "Sam",
        "source_kind": "other",
        "verified": None,
    }
    both = _propose(flagged, "UC-001", *meant, "--unintended", broken, "--unintended-from", "Sam")
    assert both["verdict"] == "ambiguous"
    assert both["answer"] is None
    assert flagged.git("status", "--porcelain").stdout == ""


def test_a_quote_is_given_with_its_source_and_a_commit_s_is_checked(flagged: AdopterRepo) -> None:
    said = "run_suite becomes execute, as every other entry point is named."
    sha = flagged.commit(
        f"refactor: tidy the runner\n\n{said}",
        {RUN: "def execute(fast=False):\n    print('run')\n"},
    )
    lone = run_script(flagged, PROPOSE, "UC-001", "--intended", said, "--json")
    assert lone.returncode == 2 and "--intended and --intended-from go together" in lone.stderr

    def checked(quote: str, source: str) -> Any:
        return _propose(flagged, "UC-001", "--intended", quote, "--intended-from", source)

    found = checked(said.replace(" as", "\n as"), sha[:7])  # whitespace runs read as one
    assert (found["verdict"], found["read"]["intended"]["verified"]) == ("analysis-stale", True)
    assert found["read"]["intended"]["source_kind"] == "commit"
    assert checked("run_suite is dropped on purpose.", sha)["read"]["intended"]["verified"] is False
    install = flagged.git("rev-list", "--max-parents=0", "HEAD").stdout.split()[0]
    assert checked(said, install)["read"]["intended"]["verified"] is False  # not behind it
    assert checked(said, "https://example.org/pr/212")["read"]["intended"]["verified"] is None
    # Shown, never enforced: an unchecked or failed quote decides as any quote does.
    assert checked("run_suite is dropped on purpose.", sha)["verdict"] == "analysis-stale"
    human = run_script(
        flagged, PROPOSE, "UC-001", "--intended", "Dropped.", "--intended-from", sha[:12]
    )
    assert f"intended: 'Dropped.' — {sha[:12]}, NOT found in its message" in human.stdout


def test_a_regression_s_command_waits_for_the_person_s_defect(flagged: AdopterRepo) -> None:
    """The proposal never names the defect: its command carries the placeholder, the
    writer refuses it as shown, and records it once the person has filled it."""
    flagged.commit(
        "refactor: tidy the runner", {RUN: "def execute(fast=False):\n    print('run')\n"}
    )
    document = _propose(flagged, "UC-001", "--unintended", "A bug.", "--unintended-from", "Sam")
    answer = document["answer"]
    assert answer["outcome"] == "code-regressed"
    (command,) = answer["commands"]
    assert "<the defect reference>" in command and "--yes" not in command
    drafted = command.replace("<why it is still wanted>", "running the suite is still wanted")

    def run(line: str) -> Any:
        return CliRunner().invoke(main, [*shlex.split(line)[1:], "--yes"])

    refused = run(drafted)
    assert refused.exit_code != 0
    assert "still holds the placeholder '<the defect reference>'" in refused.output
    assert flagged.git("status", "--porcelain").stdout == ""
    recorded = run(drafted.replace("<the defect reference>", "#231"))
    assert recorded.exit_code == 0, recorded.output
    flagged.commit("docs(analysis): UC-001 stands; the defect is #231")
    assert _explained_state(flagged, "UC-001") == "current"


def test_quoted_code_is_matched_as_a_whole_word(flagged: AdopterRepo) -> None:
    """`fast` renamed to `fastest` is gone, though `fastest` holds it as a substring: a
    substring match would read code that changed under the quote as kept."""
    flagged.commit("feat: a faster pass", {RUN: "def run_suite(fastest=False):\n    pass\n"})
    document = _propose(flagged, "UC-001")
    assert document["verdict"] == "ambiguous"
    assert document["anchors"][0]["gone"] == ["fast"]


def test_a_deleted_anchor_is_ambiguous_until_intent_is_quoted(flagged: AdopterRepo) -> None:
    flagged.commit("chore: drop the runner", {RUN: None})
    document = _propose(flagged, "UC-001")
    assert document["verdict"] == "ambiguous"
    (anchor,) = document["anchors"]
    assert (anchor["state"], anchor["shape"], anchor["moved_to"]) == ("dead-anchor", "gone", [])
    # A dead anchor's finding says where its files went: the commit that removed them.
    assert [(c["change"], c["paths"]) for c in anchor["commits"]] == [
        ("chore: drop the runner", [RUN])
    ]
    assert "path:src/run.py resolves to nothing any more" in document["question"]
    assert "'chore: drop the runner'" in document["question"]
    intended = _propose(
        flagged, "UC-001", "--intended", "The runner is gone on purpose.", "--intended-from", "Sam"
    )
    assert intended["verdict"] == "analysis-stale"
    assert any("resolves to nothing" in step for step in intended["answer"]["first"])


def test_a_renamed_file_is_moved_code_not_the_stop(flagged: AdopterRepo) -> None:
    """The anchor is what went stale: re-pointed and recorded `unchanged`, since an
    anchor-only edit changes no content — `updated` would be a bump."""
    flagged.rename(RUN, "src/runner.py", "refactor: name the runner module for what it does")
    document = _propose(flagged, "UC-001")
    assert (document["verdict"], document["rule"]) == ("holds", "anchor-moved")
    (anchor,) = document["anchors"]
    assert (anchor["shape"], anchor["moved_to"]) == ("moved", ["src/runner.py"])
    answer = document["answer"]
    assert answer["first"] == [
        "re-point path:src/run.py to src/runner.py in the artefact's anchors"
    ]
    (command,) = answer["commands"]
    assert command.endswith(
        "--outcome unchanged --because 'src/run.py moved to src/runner.py; anchor re-pointed.'"
    )

    # The person re-points the anchor and runs the command: the friction is answered.
    text = (flagged.root / RUN_SUITE).read_text(encoding="utf-8")
    flagged.write({RUN_SUITE: text.replace(f"- {RUN}\n", "- src/runner.py\n")})
    result = CliRunner().invoke(main, [*shlex.split(command)[1:], "--yes"])
    assert result.exit_code == 0, result.output
    flagged.commit("docs(analysis): UC-001 follows the runner to its new module")
    assert _explained_state(flagged, "UC-001") == "current"


def test_quoted_code_carried_into_another_file_is_moved_code(flagged: AdopterRepo) -> None:
    flagged.commit(
        "refactor: the suite runs from its own module",
        {
            RUN: "fast = False\nprint('run')\n",
            "src/suite.py": "def run_suite(fast=False):\n    print('run')\n",
        },
    )
    document = _propose(flagged, "UC-001")
    assert (document["verdict"], document["rule"]) == ("holds", "anchor-moved")
    (anchor,) = document["anchors"]
    assert (anchor["gone"], anchor["moved_to"]) == (["run_suite"], ["src/suite.py"])
    # `fast` stayed in src/run.py: the new file joins the anchor rather than replacing it.
    assert document["answer"]["first"] == [
        "add src/suite.py to the artefact's path anchors, beside src/run.py"
    ]
    assert document["answer"]["commands"][0].endswith(
        "'`run_suite` moved from src/run.py to src/suite.py; anchored there too.'"
    )


def test_a_quote_found_only_in_a_file_of_another_kind_did_not_move(flagged: AdopterRepo) -> None:
    """A note mentioning the old name is no new home for the code."""
    flagged.commit(
        "refactor: tidy the runner",
        {
            RUN: "def execute(fast=False):\n    print('run')\n",
            "docs/notes.md": "We used to call `run_suite` here.\n",
        },
    )
    document = _propose(flagged, "UC-001")
    assert (document["verdict"], document["anchors"][0]["shape"]) == ("ambiguous", "gone")


# Slow by design: the seed stamped over a commit each case makes first, so no template has it.
@pytest.mark.parametrize("carried", [False, True], ids=["held-at-the-point", "carried-in"])
def test_a_quote_surviving_only_under_an_excluded_path_is_gone(
    make_adopter_repo: MakeAdopterRepo,
    pkit_on_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    carried: bool,
) -> None:
    """An anchor stands on no file `friction.exclude` leaves out, so a quote only such a
    file still holds is gone — whether it held the quote at the revalidation point or
    the code was carried into it — never kept, and never moved there: the anchor
    re-pointed would stand on nothing. The actor is an entry of a collection file,
    read by the section the explanation gives as its body."""
    repo = installed(make_adopter_repo, monkeypatch)
    config = "docs:\n  internal: tech-docs\nfriction:\n  exclude:\n    - src/generated\n"
    stub = {GENERATED: "from run import run_suite\n"}
    runner = {CONFIG: config, RUN: "def run_suite(fast=False):\n    print('run')\n"}
    repo.commit("feat: the runner", runner if carried else {**runner, **stub})
    seed(repo, filled=False)
    text = (repo.root / ACTORS).read_text(encoding="utf-8")
    assert WHO in text
    repo.write({ACTORS: text.replace(WHO, "The tester starts `run_suite` to check a change.")})
    repo.commit("docs(analysis): the tester and the suite")
    change = {RUN: "def execute(fast=False):\n    print('run')\n"}
    carried_in = {GENERATED: "def run_suite(fast=False):\n    print('run')\n"}
    repo.commit("refactor: tidy the runner", {**change, **carried_in} if carried else change)

    document = _propose(repo, "ACT-tester")
    (anchor,) = document["anchors"]
    assert (anchor["value"], anchor["quoted"], anchor["gone"], anchor["moved_to"]) == (
        "src/**",
        ["run_suite"],
        ["run_suite"],
        [],
    )
    assert (anchor["shape"], document["verdict"], document["rule"]) == (
        "gone",
        "ambiguous",
        "ground-gone",
    )


def test_kept_code_leans_to_holds_and_leaves_the_diff_to_be_read(flagged: AdopterRepo) -> None:
    flagged.commit("fix: say what runs", {RUN: "def run_suite(fast=False):\n    print('suite')\n"})
    document = _propose(flagged, "UC-001")
    assert (document["verdict"], document["rule"], document["hint"]) == (
        "read",
        "quoted-code-kept",
        "holds",
    )
    assert document["anchors"][0]["gone"] == []
    assert "<why it still holds against this change>" in document["answer"]["commands"][0]
    # The actor quotes nothing from `src/**`: the same change is the agent's to read.
    actor = _propose(flagged, "ACT-tester")
    assert (actor["verdict"], actor["hint"], actor["answer"]) == ("read", None, None)


def test_an_upstream_artefact_changed_is_read_never_regressed(flagged: AdopterRepo) -> None:
    text = (flagged.root / RUN_SUITE).read_text(encoding="utf-8")
    flagged.commit(
        "docs(analysis): the suite reports its time",
        {RUN_SUITE: text.replace("**Done when:** <", "**Done when:** the time is shown; <")},
    )
    document = _propose(flagged, "JRN-001")
    assert (document["verdict"], document["rule"]) == ("read", "nothing-decides")
    assert document["anchors"][0]["shape"] == "deliberate"
    read = ("--contradicted", "Step 1 says nothing of the time.", "--contradicted-from", "Sam")
    contradicted = _propose(flagged, "JRN-001", *read)
    assert (contradicted["verdict"], contradicted["hint"]) == ("read", "analysis-stale")
    assert (flagged.root / FIRST_RUN).read_text(encoding="utf-8") == (
        flagged.git("show", f"HEAD:{FIRST_RUN}").stdout
    )


def test_an_artefact_that_cannot_be_explained_is_refused(flagged: AdopterRepo) -> None:
    completed = run_script(flagged, PROPOSE, "UC-404", "--json")
    assert completed.returncode == 1
    assert completed.stdout == ""
    assert completed.stderr.startswith("cannot propose: ")


#: A `pkit` answering `friction explain` as another backbone would: the real answer
#: with its `schema_version` set to `$EXPLAIN_VERSION` (JSON), or taken out when that
#: is empty — a backbone from before the key — and its `state` set to `$EXPLAIN_STATE`
#: when that is given.
_ANOTHER_PKIT = """#!{python}
import json, os, subprocess, sys
done = subprocess.run([sys.executable, "-m", "project_kit", *sys.argv[1:]],
                      capture_output=True, text=True)
out = done.stdout
if sys.argv[1:3] == ["friction", "explain"] and done.returncode == 0:
    document = json.loads(out)
    version = os.environ["EXPLAIN_VERSION"]
    if version:
        document["schema_version"] = json.loads(version)
    else:
        del document["schema_version"]
    if os.environ.get("EXPLAIN_STATE"):
        document["state"] = os.environ["EXPLAIN_STATE"]
    out = json.dumps(document)
sys.stdout.write(out)
sys.stderr.write(done.stderr)
sys.exit(done.returncode)
"""


def _another_backbone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, version: str, state: str = ""
) -> None:
    """Put `_ANOTHER_PKIT` first on PATH, answering `explain` at `version`, in `state`
    when one is given."""
    other = tmp_path / "another-backbone"
    other.mkdir()
    (other / "pkit").write_text(_ANOTHER_PKIT.format(python=sys.executable), encoding="utf-8")
    (other / "pkit").chmod(0o755)
    monkeypatch.setenv("PATH", f"{other}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("EXPLAIN_VERSION", version)
    monkeypatch.setenv("EXPLAIN_STATE", state)


@pytest.mark.parametrize(
    ("state", "said"),
    [
        ("unresolved", "UC-001 is not judged: an anchor of it cannot be resolved"),
        ("judged-later", "the state 'judged-later', which this capability does not read"),
    ],
)
def test_an_artefact_the_checks_did_not_judge_is_refused(
    flagged: AdopterRepo, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, state: str, said: str
) -> None:
    """As an `unreachable` one is: an `unresolved` artefact, or one in a state this
    capability does not read, is never proposed for — not even `holds` for code its
    other anchors show moved, which would answer for the anchor nobody read."""
    flagged.rename(RUN, "src/runner.py", "refactor: name the runner module for what it does")
    assert _propose(flagged, "UC-001")["verdict"] == "holds"
    _another_backbone(tmp_path, monkeypatch, "1", state)
    completed = run_script(flagged, PROPOSE, "UC-001", "--json")
    assert completed.returncode == 1
    assert completed.stdout == ""
    assert completed.stderr.startswith("cannot propose: ")
    assert said in completed.stderr
    assert "`pkit friction explain UC-001`" in completed.stderr


@pytest.mark.parametrize("version", ["2", "null", '"1"'])
def test_an_explanation_of_another_version_is_refused(
    flagged: AdopterRepo, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, version: str
) -> None:
    """A version this capability does not read is refused, never read as the one it knows."""
    _another_backbone(tmp_path, monkeypatch, version)
    completed = run_script(flagged, PROPOSE, "UC-001", "--json")
    assert completed.returncode == 1
    assert completed.stdout == ""
    shown = repr(json.loads(version))
    assert completed.stderr == (
        f"cannot propose: `pkit friction explain` answered schema_version {shown}; "
        f"this capability reads 1\n"
    )


def test_an_explanation_without_a_version_reads_as_the_first(
    flagged: AdopterRepo, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A backbone from before the key answers version 1: the same proposal."""
    expected = _propose(flagged, "UC-001")
    _another_backbone(tmp_path, monkeypatch, "")
    assert _propose(flagged, "UC-001") == expected


@pytest.mark.parametrize("namespace", ["analysis", "software-analysis"])
def test_propose_is_reached_under_the_capability_and_its_alias(
    flagged: AdopterRepo, namespace: str
) -> None:
    result = CliRunner().invoke(main, [namespace, "--help"])
    assert result.exit_code == 0, result.output
    assert "propose " in result.output


# --- the agent's files -------------------------------------------------------------------------

#: A writer invoked: the friction writers, and the record stamp.
WRITES = re.compile(r"friction (?:revalidate|defer|record-status)|analysis new revalidation")
CONSENT = re.compile(r"--yes\b|--dry-run\b")

#: The one section of the body, and the head of each block in the storyboard, that
#: list the commands for the person.
COMMANDS_SECTION = "## Commands for the person"
COMMANDS_BLOCK = "# Commands for the person"

SCENARIOS = ("Happy path", "The stop", "A regression, recorded")
SCENARIO_PARTS = ("**Trigger.**", "**Preconditions.**", "### Walkthrough", "### Behind the scenes")

_FENCE = re.compile(r"^[ ]*(?:>[ ]?)?[ ]*```")
_QUOTED = re.compile(r"^[ ]*(?:>[ ]?)?[ ]*")


def _split(path: Path) -> tuple[dict[str, Any], str]:
    _, front, body = path.read_text(encoding="utf-8").split("---\n", 2)
    return load(front) or {}, body


def _commands_for_the_person(text: str) -> tuple[str, str]:
    """(the commands for the person, everything else): the body's section of that
    name, and each fenced block — in a quote or a list or not — headed by it."""
    inside: list[str] = []
    outside: list[str] = []
    if COMMANDS_SECTION in text:
        before, after = text.split(COMMANDS_SECTION, 1)
        section, sep, rest = after.partition("\n## ")
        inside.append(section)
        text = before + sep + rest
    block: list[str] | None = None
    for line in text.splitlines():
        if block is None:
            if _FENCE.match(line):
                block = []
            else:
                outside.append(line)
            continue
        if _FENCE.match(line):
            content = [_QUOTED.sub("", ln) for ln in block]
            heads = [ln for ln in content if ln.strip()]
            (inside if heads and heads[0] == COMMANDS_BLOCK else outside).extend(content)
            block = None
            continue
        block.append(line)
    return "\n".join(inside), "\n".join(outside)


def _command_lines(commands: str) -> list[str]:
    return [line.strip() for line in commands.splitlines() if line.strip().startswith("pkit ")]


def test_the_agent_performs_the_judgment_and_never_runs_a_writer() -> None:
    front, body = _split(AGENT)
    assert front["name"] == "analysis-resolver"
    assert set(front["tools"]) == {"Read", "Glob", "Grep", "Bash", "Write"}  # no Edit
    assert front["owns"] == []
    assert "model" not in front and "effort" not in front
    assert front["storyboards"] == [STORYBOARD.name]
    assert f"`{STORYBOARD.name}`" in body
    assert "**perform the judgment of the revalidation**" in body
    assert "You are **not a reviewer**" in body
    assert "**You never run a writer.**" in body
    assert "`.agent-workspace/analysis-resolver/<change>/`" in body
    assert "#revalidation" not in body  # links the README's table by name, restating none
    assert WRITES.search(front["description"]) is None

    commands, rest = _commands_for_the_person(body)
    assert WRITES.findall(rest) == []
    for writer in ("friction revalidate", "friction defer", "analysis new revalidation"):
        assert writer in commands, writer
    assert "record-status" not in commands
    assert [c for c in _command_lines(commands) if CONSENT.search(c)] == []
    assert "<the defect reference>" in commands and '--confirmed-by "<your name>"' in commands


def test_the_storyboard_scripts_the_three_scenarios_and_hands_over_commands() -> None:
    front, body = _split(STORYBOARD)
    assert front["consumers"] == [
        {"kind": "agent", "name": "analysis-resolver", "namespace": "software-analysis"}
    ]
    assert "## Framing" in body and "## Tone" in body
    assert "**Hold only what depends on the ambiguity.**" in body
    pattern = body.split("## Invocation pattern", 1)[1].split("\n## ", 1)[0]
    assert "it returns the proposal" in pattern and "and nothing else" in pattern
    sections = re.split(r"^## Scenario \d+: ", body, flags=re.MULTILINE)[1:]
    titles = [section.splitlines()[0] for section in sections]
    assert len(titles) == len(SCENARIOS)
    for title, expected in zip(titles, SCENARIOS, strict=True):
        assert title.startswith(expected), title
    for section in sections:
        for part in SCENARIO_PARTS:
            assert part in section, (section.splitlines()[0], part)
    stop = sections[1]
    assert "**Hold only what depends on the ambiguity.**" in stop

    commands, rest = _commands_for_the_person(body)
    assert WRITES.findall(rest) == []
    for writer in ("friction revalidate", "friction defer", "analysis new revalidation"):
        assert writer in commands, writer
    assert [c for c in _command_lines(commands) if CONSENT.search(c)] == []
    # The stop hands over no command for what it asks about.
    assert WRITES.findall(_commands_for_the_person(stop)[0]) == []


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
