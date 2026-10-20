"""software-analysis: the analysis-author skill (#888).

The skill walks an author through `pkit analysis new` for each kind — actor,
term, domain-model view (#1817), use case, journey, the three kinds of
requirement (#1692), revalidation record. Held here:

- **its shape** — a composite skill (COR-020) whose `composes` is exactly its
  sub-procedures, clean under `pkit refs validate`, deployed beside them;
- **it builds an analysis from its concepts up** (#1784) — `build-analysis.md` walks
  the four steps of DEC-001 point 12 in order, each through the kinds'
  sub-procedures and each saying when it is done, and the dispatcher routes to it;
- **it matches the command it pairs with** — every `pkit analysis new` form its
  walkthroughs give names a kind the stamp has, with flags that kind takes, so
  the skill cannot drift from the CLI unnoticed;
- **what it produces passes the check gate and carries the friction block** —
  the artefacts its walkthroughs stamp, an unanchored actor, a requirement of
  each kind and a revalidation record included, pass `pkit analysis validate`
  and the core's friction pass, and each carries its `friction` block;
- **choosing each kind's templates works as it walks it** (#1371) — a candidate
  stamped and filled is checked with `pkit analysis validate --preview`, and a
  part of the project's own, under a proposed rule of its own, is previewed on
  the candidate and written by the stamp once it is stamped again.
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
    ANALYSIS,
    ANALYSIS_SET,
    ANALYSIS_SET_TEXT,
    CAPABILITY,
    NEW,
    REPO,
    STRUCTURES,
    VALIDATE,
    actor_at,
    fill,
    installed,
    load,
    run_script,
    stamped,
)
from tests.test_software_analysis_check import check, errors

SKILL = CAPABILITY / "skills" / "analysis-author"
DISPATCHER = SKILL / "analysis-author.md"
DEPLOYED = REPO / ".claude" / "skills" / "analysis-author"

#: Each sub-procedure, and the kinds of `pkit analysis new` it walks: one each, but the
#: requirements', which walks the three kinds of requirement (#1692).
SUB_PROCEDURES = {
    "actor.md": ("actor",),
    "term.md": ("term",),
    "view.md": ("view",),
    "use-case.md": ("use-case",),
    "journey.md": ("journey",),
    "requirement.md": ("quality-requirement", "functional-requirement", "constraint"),
    "revalidation-record.md": ("revalidation",),
}

#: The sub-procedure a project follows as it adopts the capability: it chooses each
#: kind's parts, and stamps through the sub-procedures above (DEC-001 point 1).
CHOOSING = "choose-templates.md"

#: The sub-procedure that builds an analysis from its concepts up, walking the kinds'
#: sub-procedures in the order DEC-001 point 12 gives (#1784).
BUILDING = "build-analysis.md"

#: The build's four steps, each with the words that tie it to its item of DEC-001 point
#: 12's list, and the kinds' sub-procedures it walks, in the order it first names them.
BUILD_STEPS = (
    ("## 1. The concepts, then the actors", "concepts", ("term.md", "view.md", "actor.md")),
    (
        "## 2. The requirements that bind the whole system",
        "requirements that bind the whole system",
        ("requirement.md",),
    ),
    (
        "## 3. The use cases, area by area",
        "use cases, area by area",
        ("requirement.md", "use-case.md"),
    ),
    ("## 4. The journeys, last", "journeys, last", ("journey.md",)),
)
DECISION = CAPABILITY / "decisions" / "DEC-001-software-analysis-discipline.md"


def _point_12_items() -> list[str]:
    """The four numbered items of DEC-001 point 12's order, read from the record."""
    text = DECISION.read_text(encoding="utf-8")
    point = text.split("### 12. ", 1)[1].split("What the order binds:", 1)[0]
    return [line for line in point.splitlines() if re.match(r"\d\. ", line)]


_FENCE = re.compile(r"^```\n(?P<block>.*?)^```", re.MULTILINE | re.DOTALL)


def _front(path: Path) -> dict[str, Any]:
    _, front, _body = path.read_text(encoding="utf-8").split("---\n", 2)
    return load(front) or {}


# --- its shape ---------------------------------------------------------------------------------


def test_the_skill_composes_one_sub_procedure_per_kind_the_build_and_the_choice() -> None:
    front = _front(DISPATCHER)
    assert front["name"] == "analysis-author"
    assert sorted(front["composes"]) == sorted([*SUB_PROCEDURES, CHOOSING, BUILDING])
    on_disk = sorted(p.name for p in SKILL.iterdir())
    assert on_disk == sorted([*SUB_PROCEDURES, CHOOSING, BUILDING, DISPATCHER.name])
    assert "pkit analysis new" in front["metadata"]["wraps_commands"]
    assert "pkit analysis validate" in front["metadata"]["wraps_commands"]


def test_the_build_walks_dec_001_point_12_s_order_and_says_when_each_step_is_done() -> None:
    """`build-analysis.md` (#1784): its four steps in point 12's order, each walking the
    kinds' sub-procedures in that order, each with what makes it done. A step that needs
    more goes back, and no step waits on another being closed."""
    text = (SKILL / BUILDING).read_text(encoding="utf-8")
    assert "[software-analysis:DEC-001-software-analysis-discipline] point 12" in text
    steps = [line for line in text.splitlines() if re.match(r"## \d\. ", line)]
    assert steps == [heading for heading, _ties, _walks in BUILD_STEPS]
    # Each step is the record's item at the same place, so the two cannot drift apart.
    items = _point_12_items()
    assert len(items) == len(BUILD_STEPS)
    for item, (heading, ties, _walks) in zip(items, BUILD_STEPS, strict=True):
        assert ties in item, (heading, item)
    sections = {s.splitlines()[0]: s for s in re.split(r"(?m)^(?=## )", text) if s[:3] == "## "}
    for heading, _ties, walks in BUILD_STEPS:
        section = sections[heading]
        assert re.search(r"\*\*(?:An area is )?[Dd]one when:\*\*", section), heading
        named = [n for n in re.findall(r"`([a-z-]+\.md)`", section) if n in SUB_PROCEDURES]
        assert list(dict.fromkeys(named)) == list(walks), heading
    flat = " ".join(text.split())
    assert "go back and write it there first" in flat
    # A person confirms a brownfield project's candidates, with no step gate (point 9).
    assert "but the order does not ask it." in flat


def test_the_dispatcher_routes_to_the_build_and_keeps_no_list_of_its_steps() -> None:
    """The dispatcher routes, and the steps have their one home in the sub-procedure
    (COR-020, COR-006): the actors no longer come before the glossary, and the dispatcher
    holds no numbered list of the steps."""
    text = DISPATCHER.read_text(encoding="utf-8")
    assert f"| `{BUILDING}` |" in text
    assert "actors first (a use case names one)" not in text
    assert "Write terms whenever a word needs pinning down" not in text
    flat = " ".join(text.split())
    assert (
        f"For a part of the product not yet described, follow `{BUILDING}`, which builds it "
        "from its concepts up (DEC-001 point 12)"
    ) in flat
    numbered = [line for line in text.splitlines() if re.match(r"\d\. ", line)]
    for _heading, ties, _walks in BUILD_STEPS[1:]:
        assert not [line for line in numbered if ties in line], ties
    # Every kind's walkthrough points at the shared framing on the glossary's terms.
    assert "### Use the glossary's terms" in text
    for name in ("actor.md", "use-case.md", "journey.md", "requirement.md"):
        assert "(the shared framing's \"Use the glossary's terms\")" in (SKILL / name).read_text(
            encoding="utf-8"
        ), name


def test_refs_find_nothing_in_the_skill() -> None:
    folder = str(SKILL.relative_to(REPO))
    assert [i for i in refs.validate_corpus(REPO) if i.location.startswith(folder)] == []
    (skill,) = [a for a in refs.load_artifacts(REPO) if a.name == "analysis-author"]
    assert (skill.kind, skill.capability) == ("skill", "software-analysis")


def test_the_skill_is_deployed_beside_its_sub_procedures() -> None:
    assert (DEPLOYED / "SKILL.md").resolve() == DISPATCHER.resolve()
    for name in [*SUB_PROCEDURES, CHOOSING, BUILDING]:
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


@pytest.mark.parametrize(("name", "kinds"), sorted(SUB_PROCEDURES.items()))
def test_every_command_the_walkthrough_gives_is_one_the_stamp_takes(
    name: str, kinds: tuple[str, ...]
) -> None:
    blocks = [
        m["block"]
        for m in _FENCE.finditer((SKILL / name).read_text(encoding="utf-8"))
        if m["block"].startswith("pkit analysis new ")
    ]
    assert blocks, f"{name} gives no `pkit analysis new` command"
    options = {kind: _help(kind) for kind in kinds}
    walked: set[str] = set()
    for block in blocks:
        for command in re.split(r"\n(?=pkit )", block.strip()):
            kind = command.split()[3]
            assert kind in kinds, command
            walked.add(kind)
            for flag in set(re.findall(r"(--[a-z][a-z-]*)", command)):
                assert re.search(rf"(?<![\w-]){re.escape(flag)}\b", options[kind]), (name, flag)
    # Each kind the sub-procedure walks has a command of its own.
    assert walked == set(kinds), name


# --- what it produces --------------------------------------------------------------------------


@pytest.fixture
def project(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    return installed(make_adopter_repo, monkeypatch)


# Slow by design: ten stamps and the check, each a script that starts `pkit` processes.
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
    quick = ("--actor", "ACT-tester", "--path", "src/run.py")
    stamped(project, "quality-requirement", "quick-result", *quick)
    stamped(project, "functional-requirement", "who-ran", "--refines", "REQ-001")
    stated = ("--unanchored-because", "A stakeholder states it, and nothing embodies it yet.")
    stamped(project, "constraint", "on-site", *stated)
    stale = (
        "revalidation",
        "report-redesign",
        "--change",
        "#50",
        "--trigger",
        "drift",
        "--outcome",
        "UC-002=analysis-stale",
        "--because",
        "UC-002=The redesign moved the report's layout on purpose, and step 2 now says so.",
        "--confirmed-by",
        "Sam",
    )
    completed = run_script(project, NEW, *stale)
    assert completed.returncode == 0, completed.stderr

    fill(project)  # the walkthroughs' "Fill it": the check fails a placeholder left
    assert errors(check(project)) == []
    assert validate_friction(project.root).errors == ()
    listing = subprocess.run(
        ["pkit", "friction", "artefacts", "--json"],
        cwd=project.root,
        capture_output=True,
        text=True,
        check=True,
    )
    # The analysis's own artefacts: the capability's method rule set ships rules,
    # which are artefacts too (RS-SAN-001, COR-051 point 2), outside the analysis.
    artefacts = [
        a for a in json.loads(listing.stdout)["artefacts"] if a["path"].startswith(f"{ANALYSIS}/")
    ]
    ids = sorted(a["id"] for a in artefacts)
    assert ids == [
        "ACT-sponsor",
        "ACT-tester",
        "JRN-001",
        "REQ-001",
        "REQ-002",
        "REQ-003",
        "TERM-suite",
        "UC-001",
        "UC-002",
    ]
    assert all(a["container"] and a["friction"] for a in artefacts), artefacts


# --- choosing each kind's templates ------------------------------------------------------------

#: A rule of the project's own, in its set that inherits `SAN`, asking for a part the
#: shipped actor lacks. It is proposed, as a rule is when first written.
OWN_RULE = "RS-ANALYSIS-001"
OWN_SET_TEXT = (
    ANALYSIS_SET_TEXT.replace(
        "rules: {}\n",
        f"rules:\n  {OWN_RULE}:\n    status: proposed\n"
        '    origin: {why: "A reader needs to know where the role works."}\n',
    )
    + f"\n## {OWN_RULE} — An actor says where the role works\n\nAn actor says where it works.\n"
)
STRUCTURES_TEXT = (
    "pkit_schema: software-analysis:structures\nschema_version: 1\nkinds:\n  actor:\n"
    f"    tighten:\n      - rule: {OWN_RULE}\n        add:\n          - id: setup\n"
    "            label: Setup\n            after: opening\n"
    "            hint: Where the role works.\n            example: A lab.\n"
    "            required: true\n"
)


def _previewed(repo: AdopterRepo, rel: str) -> tuple[str, list[tuple[str, str]]]:
    """What `pkit analysis validate --preview` says: its summary of the structure, and
    each finding on one artefact, with its severity."""
    completed = run_script(repo, VALIDATE, "--json", "--preview")
    assert completed.returncode == 0, completed.stderr
    document = json.loads(completed.stdout)
    found = [(f["severity"], f["message"]) for f in document["findings"] if f["location"] == rel]
    return document["summary"][1], found


# Slow by design: two stamps and three checks, each a script that starts `pkit` processes.
def test_a_candidate_is_previewed_and_stamped_again_with_the_project_s_own_part(
    project: AdopterRepo,
) -> None:
    """`choose-templates.md`: with a set of the project's own that inherits `SAN`, a
    candidate stamped and filled is checked with the preview while the format rule is
    proposed. A part the project adds under a proposed rule of its own is previewed on
    the candidate, which lacks it. Set aside and stamped again, the candidate keeps its id
    and holds the part, its hint naming the rule, and once filled the preview finds
    nothing."""
    project.write({ANALYSIS_SET: ANALYSIS_SET_TEXT})
    candidate = ("actor", "tester", "--name", "Test author", "--path", "src/run.py")
    stamped(project, *candidate)
    rel = actor_at("ACT-tester")
    fill(project)
    summary, found = _previewed(project, rel)
    assert "1 artefact(s) and file head(s) checked" in summary, summary
    assert found == []

    project.write({ANALYSIS_SET: OWN_SET_TEXT, STRUCTURES: STRUCTURES_TEXT})
    [(severity, missing)] = _previewed(project, rel)[1]
    assert severity == "report"  # a preview's finding never fails
    assert missing.startswith("preview: `**Setup:**` is missing"), missing
    assert f"({OWN_RULE}, RS-SAN-001)" in missing, missing

    # Set aside out of the analysis, for the comparison: never committed, it holds no id.
    aside = project.root.parent / "first-candidate.md"
    (project.root / rel).rename(aside)
    assert stamped(project, *candidate) == "ACT-tester"
    assert "**Setup:**" not in aside.read_text(encoding="utf-8")
    text = (project.root / rel).read_text(encoding="utf-8")
    [setup] = [line for line in text.splitlines() if line.startswith("**Setup:**")]
    assert (
        setup == f"**Setup:** <!-- pkit:hint Where the role works. ({OWN_RULE}) Example: A lab. -->"
    )
    fill(project)
    assert _previewed(project, rel)[1] == []
