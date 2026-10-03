"""A writer command an agent hands over writes nothing without a person (#1148).

The living-docs agent and software-analysis' resolver answer friction by handing
the commands over and running none: neither has a tool for putting a question to
the person, so the second of the four conditions in the agents README's
"Friction writers" never holds for them. Every writer command their bodies and
storyboards hand over is run here as a session with no person in it would run
it — off a terminal, with nothing added — on an adopter repository whose analysis
is committed:

- **as handed over**, placeholders unfilled and the examples' own paths and ids
  naming nothing here: refused, and nothing written;
- **bound to this repository** — its use case and anchor in place of the ones the
  command names, every placeholder written over, so the placeholder check does
  not answer first: a friction writer refuses for want of consent, and `git
  status` shows nothing;
- **the record stamp**, its ids bound and the person's words left as handed over:
  refused for the person's placeholder, which no agent fills;
- **the refusal** offers no command that writes: it names the dry run and no
  runnable `--yes` line, since passing `--yes` is consent only a person, or an
  agent for what its own change owes, may give (COR-050 point 3).

What this proves: an agent that follows its body returns commands in every
session, and those commands write nothing without a person. What it does not
prove: that a dispatched agent never adds `--yes` on its own. No test can run an
agent; that stays discipline.
"""

from __future__ import annotations

import re
import shlex
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner, Result

from project_kit.cli import main
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.analysis_repo import JOURNEYS, REPO, SA, USE_CASES, installed, prepare_seeded, run_script
from tests.handed_over import CONSENT, commands

LIVING_DOCS = REPO / ".pkit" / "capabilities" / "living-docs" / "agents" / "living-docs"
RESOLVER = REPO / ".pkit" / "capabilities" / "software-analysis" / "agents" / "analysis-resolver"

#: The files that hand writer commands over: each agent's body and storyboard.
SOURCES = (
    LIVING_DOCS / "living-docs.md",
    LIVING_DOCS / "storyboard.md",
    RESOLVER / "analysis-resolver.md",
    RESOLVER / "storyboard.md",
)

NEW = SA / "scripts" / "new.py"

#: The seeded analysis's use case, anchored to `src/run.py`: what a friction writer
#: is bound to here.
ARTEFACT = f"{USE_CASES}/UC-001-run-suite.md"
ANCHOR = "path:src/run.py"

#: The ids a handed-over record cites that the seeded analysis does not hold, bound
#: to its own.
IDS = {"UC-007": "UC-001", "JRN-003": "JRN-001"}

#: The words that are the person's alone, which the agent leaves for them to write.
PERSONS = ("<the defect reference>", "<your name>")

#: Words in angle brackets, as a command handed over writes a placeholder.
PLACEHOLDER = re.compile(r"<([^<>\n]+)>")


def _handed_over(stem: str) -> dict[str, str]:
    """Each command of the writers `stem` names, by the file that hands it over and its
    place there."""
    return {
        f"{path.parent.name}/{path.name}:{number}": command
        for path in SOURCES
        for number, command in enumerate(commands(path.read_text(encoding="utf-8")), 1)
        if command.startswith(stem)
    }


def _drafted(command: str) -> bool:
    """Whether every placeholder left in the command is the person's: the agent drafted
    its own words, as it does before handing a command over. The body's record is a
    template, its placeholders all still the agent's."""
    return {f"<{p}>" for p in PLACEHOLDER.findall(command)} <= set(PERSONS)


FRICTION_WRITERS = _handed_over("pkit friction ")
RECORD_STAMPS = _handed_over("pkit analysis new revalidation ")
DRAFTED_RECORDS = {where: c for where, c in RECORD_STAMPS.items() if _drafted(c)}


def _each(handed: dict[str, str]) -> Any:
    """The commands as test parameters, each named by where it is handed over."""
    return pytest.mark.parametrize("command", list(handed.values()), ids=list(handed))


def _commit_the_analysis(repo: AdopterRepo) -> None:
    """`prepare_seeded`, then all of it committed: a clean tree to write into."""
    prepare_seeded(repo)
    repo.commit("docs(analysis): the tester, the suite and the first run")


@pytest.fixture
def analysed(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    repo = installed(make_adopter_repo, monkeypatch, then=_commit_the_analysis)
    assert repo.git("status", "--porcelain").stdout == ""
    assert (repo.root / ARTEFACT).is_file() and (repo.root / JOURNEYS).is_dir()
    return repo


def _off_a_terminal(argv: list[str]) -> Result:
    """`pkit <argv>` run as the CLI runs it, with no terminal to ask at."""
    assert argv[0] == "pkit"
    return CliRunner().invoke(main, argv[1:])


def _bound(argv: list[str]) -> list[str]:
    """A friction writer's arguments bound to this repository: its use case in place
    of the artefact named, its anchor in place of the one named, and every
    placeholder written over with its own words."""
    assert argv[:2] == ["pkit", "friction"] and argv[2] in ("revalidate", "defer")
    bound = [*argv[:3], ARTEFACT]
    rest = iter(argv[4:])
    for token in rest:
        bound.append(token)
        if token == "--anchor":
            next(rest)
            bound.append(ANCHOR)
    return [PLACEHOLDER.sub(r"\1", token) for token in bound]


def test_both_agents_hand_writers_over() -> None:
    """The parameters below are what the files hand over: each agent hands over a
    friction writer, and the resolver a drafted record besides."""
    handed = {where.split(":")[0] for where in [*FRICTION_WRITERS, *RECORD_STAMPS]}
    assert handed == {
        "living-docs/storyboard.md",
        "analysis-resolver/analysis-resolver.md",
        "analysis-resolver/storyboard.md",
    }
    assert DRAFTED_RECORDS


@_each(FRICTION_WRITERS)
def test_a_friction_writer_as_handed_over_writes_nothing(
    analysed: AdopterRepo, command: str
) -> None:
    assert CONSENT.search(command) is None
    result = _off_a_terminal(shlex.split(command))
    assert result.exit_code != 0, result.output
    assert isinstance(result.exception, SystemExit), result.exception  # refused, not crashed
    assert "Wrote " not in result.output
    assert analysed.git("status", "--porcelain").stdout == ""


@_each(FRICTION_WRITERS)
def test_a_friction_writer_bound_here_refuses_without_consent(
    analysed: AdopterRepo, command: str
) -> None:
    argv = _bound(shlex.split(command))
    result = _off_a_terminal(argv)
    assert result.exit_code != 0, result.output
    assert f"refusing to write {ARTEFACT} without consent" in result.output
    assert "Nothing was written." in result.output
    assert analysed.git("status", "--porcelain").stdout == ""


def test_no_refusal_offers_a_command_that_writes(analysed: AdopterRepo) -> None:
    """Each refusal names the dry run and no line a session could run to write."""
    offered: dict[str, list[str]] = {}
    for where, command in FRICTION_WRITERS.items():
        result = _off_a_terminal(_bound(shlex.split(command)))
        assert result.exit_code != 0, result.output
        lines = [line.strip() for line in result.output.splitlines()]
        assert any(line.startswith("pkit ") and line.endswith("--dry-run") for line in lines)
        writes = [line for line in lines if line.startswith("pkit ") and "--yes" in line]
        if writes:
            offered[where] = writes
    assert offered == {}
    assert analysed.git("status", "--porcelain").stdout == ""


@_each(RECORD_STAMPS)
def test_a_record_stamp_as_handed_over_writes_nothing(analysed: AdopterRepo, command: str) -> None:
    argv = shlex.split(command)
    assert argv[:3] == ["pkit", "analysis", "new"] and CONSENT.search(command) is None
    completed = run_script(analysed, NEW, *argv[3:])
    assert completed.returncode != 0, completed.stdout
    assert completed.stderr.startswith(("refused: ", "usage: ")), completed.stderr
    assert analysed.git("status", "--porcelain").stdout == ""


@_each(DRAFTED_RECORDS)
def test_a_record_stamp_waits_for_the_person_s_words(analysed: AdopterRepo, command: str) -> None:
    """Its ids bound here, a record holding only the person's placeholders is refused
    for one of them."""
    argv = [
        "=".join([IDS.get(head, head), *tail])
        for head, *tail in (token.split("=", 1) for token in shlex.split(command))
    ]
    completed = run_script(analysed, NEW, *argv[3:])
    assert completed.returncode == 1, completed.stderr
    assert "still holds the placeholder" in completed.stderr
    assert any(repr(person) in completed.stderr for person in PERSONS), completed.stderr
    assert analysed.git("status", "--porcelain").stdout == ""
