"""software-analysis: the analysis-author skill (#888).

The skill walks an author through `pkit analysis new` for each kind — actor,
term, use case, journey, revalidation record. Held here:

- **its shape** — a composite skill (COR-020) whose `composes` is exactly its
  sub-procedures, clean under `pkit refs validate`, deployed beside them;
- **it matches the command it pairs with** — every `pkit analysis new` form its
  walkthroughs give names a kind the stamp has, with flags that kind takes, so
  the skill cannot drift from the CLI unnoticed;
- **what it produces passes the check gate and carries the friction block** —
  the artefacts its walkthroughs stamp, an unanchored actor and a planned
  revalidation record included, pass `pkit analysis validate` and the core's
  friction pass, and each carries its `friction` block.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from project_kit import refs
from project_kit.friction_validate import validate_friction
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.analysis_repo import (
    CAPABILITY,
    NEW,
    REPO,
    installed,
    load,
    run_script,
    stamped,
)
from tests.test_software_analysis_check import check, errors

SKILL = CAPABILITY / "skills" / "analysis-author"
DISPATCHER = SKILL / "analysis-author.md"
DEPLOYED = REPO / ".claude" / "skills" / "analysis-author"

#: Each sub-procedure, and the kind of `pkit analysis new` it walks.
SUB_PROCEDURES = {
    "actor.md": "actor",
    "term.md": "term",
    "use-case.md": "use-case",
    "journey.md": "journey",
    "revalidation-record.md": "revalidation",
}

_FENCE = re.compile(r"^```\n(?P<block>.*?)^```", re.MULTILINE | re.DOTALL)


def _front(path: Path) -> dict[str, Any]:
    _, front, _body = path.read_text(encoding="utf-8").split("---\n", 2)
    return load(front) or {}


# --- its shape ---------------------------------------------------------------------------------


def test_the_skill_composes_one_sub_procedure_per_kind() -> None:
    front = _front(DISPATCHER)
    assert front["name"] == "analysis-author"
    assert sorted(front["composes"]) == sorted(SUB_PROCEDURES)
    assert sorted(p.name for p in SKILL.iterdir()) == sorted([*SUB_PROCEDURES, DISPATCHER.name])
    assert "pkit analysis new" in front["metadata"]["wraps_commands"]


def test_refs_find_nothing_in_the_skill() -> None:
    folder = str(SKILL.relative_to(REPO))
    assert [i for i in refs.validate_corpus(REPO) if i.location.startswith(folder)] == []
    (skill,) = [a for a in refs.load_artifacts(REPO) if a.name == "analysis-author"]
    assert (skill.kind, skill.capability) == ("skill", "software-analysis")


def test_the_skill_is_deployed_beside_its_sub_procedures() -> None:
    assert (DEPLOYED / "SKILL.md").resolve() == DISPATCHER.resolve()
    for name in SUB_PROCEDURES:
        assert (DEPLOYED / name).resolve() == (SKILL / name).resolve()


# --- it matches the command it pairs with ------------------------------------------------------


def _help(kind: str) -> str:
    completed = subprocess.run(
        [sys.executable, str(REPO / NEW), kind, "--help"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return completed.stdout


@pytest.mark.parametrize(("name", "kind"), sorted(SUB_PROCEDURES.items()))
def test_every_command_the_walkthrough_gives_is_one_the_stamp_takes(name: str, kind: str) -> None:
    blocks = [
        m["block"]
        for m in _FENCE.finditer((SKILL / name).read_text(encoding="utf-8"))
        if m["block"].startswith("pkit analysis new ")
    ]
    assert blocks, f"{name} gives no `pkit analysis new` command"
    options = _help(kind)
    for block in blocks:
        for command in re.split(r"\n(?=pkit )", block.strip()):
            assert command.split()[3] == kind, command
            for flag in set(re.findall(r"(--[a-z][a-z-]*)", command)):
                assert re.search(rf"(?<![\w-]){re.escape(flag)}\b", options), (name, flag)


# --- what it produces --------------------------------------------------------------------------


@pytest.fixture
def project(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    return installed(make_adopter_repo, monkeypatch)


def test_what_the_walkthroughs_stamp_passes_the_gate_and_carries_the_friction_block(
    project: AdopterRepo,
) -> None:
    stamped(project, "actor", "tester", "--name", "Test author", "--path", "src/run.py")
    reason = "No code or decision embodies it: it funds the project."
    stamped(project, "actor", "sponsor", "--name", "Sponsor", "--unanchored-because", reason)
    stamped(project, "term", "suite", "--name", "Suite", "--path", "src/run.py")
    stamped(project, "use-case", "run-suite", "--actor", "ACT-tester", "--path", "src/run.py")
    stamped(project, "use-case", "read-report", "--actor", "ACT-tester", "--area", "reports")
    steps = ("--step", "UC-001", "--step", "UC-002")
    stamped(project, "journey", "first-run", "--actor", "ACT-tester", *steps)
    planned = (
        "revalidation",
        "report-redesign",
        "--change",
        "#50",
        "--trigger",
        "planned",
        "--outcome",
        "UC-002=holds",
        "--because",
        "UC-002=The redesign keeps the report's content; only its layout changes.",
    )
    completed = run_script(project, NEW, *planned)
    assert completed.returncode == 0, completed.stderr

    assert errors(check(project)) == []
    assert validate_friction(project.root).errors == ()
    listing = subprocess.run(
        ["pkit", "friction", "artefacts", "--json"],
        cwd=project.root,
        capture_output=True,
        text=True,
        check=True,
    )
    artefacts = json.loads(listing.stdout)["artefacts"]
    ids = sorted(a["id"] for a in artefacts)
    assert ids == ["ACT-sponsor", "ACT-tester", "JRN-001", "TERM-suite", "UC-001", "UC-002"]
    assert all(a["container"] and a["friction"] for a in artefacts), artefacts
