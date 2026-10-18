"""software-analysis: the requirements a use case and a journey list, and what meets each (#1694).

Held to software-analysis DEC-002 point 7:

- **the stamp** — `pkit analysis new use-case` and `new journey` take
  `--requirement <REQ-id>`, repeatable, write the list in `requirements` and
  anchor each requirement, and refuse one the analysis does not hold or has
  withdrawn, writing nothing;
- **the check** — `pkit analysis validate` refuses a listed requirement that
  resolves to no requirement of the analysis, or that is withdrawn while the use
  case or the journey is in force, and requirement anchors that do not match the
  list exactly, a part anchor on a requirement included;
- **"Met by"** — `pkit analysis met-by [<REQ-id>] [--json]` lists, for each
  requirement, the use cases and journeys in force that list it, computed from
  the working tree, and writes nothing. A file it cannot read is no answer.

The companion schemas' field is `test_software_analysis_templates.py`'s.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from project_kit.cli import main
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.analysis_repo import (
    ANALYSIS,
    CAPABILITY,
    CONSTRAINTS,
    JOURNEYS,
    QUALITY,
    SA,
    USE_CASES,
    fill,
    front,
    installed,
    load,
    new,
    prepare_seeded,
    requirement,
    run_script,
    stamped,
)
from tests.test_software_analysis_check import check, errors

MET_BY = SA / "scripts" / "met-by.py"

#: Two requirements beside the seed's use cases and journey: a constraint and a quality
#: requirement, written as their structures ask.
LOCAL = f"{CONSTRAINTS}/REQ-001-local-runs.md"
QUICK = f"{QUALITY}/REQ-004-quick-result.md"
LOCAL_TITLE = "Run suites on the client's machines"
QUICK_TITLE = "Show a run's result quickly"

RUN_SUITE = f"{USE_CASES}/UC-001-run-suite.md"
READ_REPORT = f"{USE_CASES}/UC-002-read-report.md"
FIRST_RUN = f"{JOURNEYS}/JRN-001-first-run.md"


def _with_requirements(repo: AdopterRepo) -> None:
    """`prepare_seeded`, then the two requirements, committed."""
    prepare_seeded(repo)
    repo.write(
        {
            LOCAL: requirement("constraint", req_id="REQ-001", title=LOCAL_TITLE),
            QUICK: requirement(title=QUICK_TITLE),
        }
    )
    repo.commit("two requirements")


@pytest.fixture
def listed(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    """The seed, and the requirements REQ-001, a constraint, and REQ-004, a quality one."""
    return installed(make_adopter_repo, monkeypatch, then=_with_requirements)


def _set(repo: AdopterRepo, rel: str, old: str, new_text: str) -> None:
    text = (repo.root / rel).read_text(encoding="utf-8")
    assert old in text, (rel, old)
    repo.write({rel: text.replace(old, new_text, 1)})


def _lists(repo: AdopterRepo, rel: str, listed: list[str], anchored: list[str]) -> None:
    """The artefact at `rel` lists `listed` in its `requirements`, and anchors each of
    `anchored` beside its own artefact anchors."""
    text = (repo.root / rel).read_text(encoding="utf-8")
    written = "".join(f"  - {value}\n" for value in listed)
    text = text.replace("requirements: []\n", f"requirements:\n{written}" if listed else "", 1)
    head, sep, rest = text.partition("      artefact:\n")
    assert sep, rel
    anchors = "".join(f"        - {value}\n" for value in anchored)
    repo.write({rel: head + sep + anchors + rest})


def _withdraw(repo: AdopterRepo, rel: str) -> None:
    """The artefact at `rel` withdrawn: a stamped one, or one `requirement` wrote."""
    text = (repo.root / rel).read_text(encoding="utf-8")
    for old, withdrawn in (
        ('status: "active"', 'status: "withdrawn"'),
        ("status: active", "status: withdrawn"),
    ):
        if old in text:
            repo.write({rel: text.replace(old, withdrawn, 1)})
            return
    raise AssertionError(f"{rel} holds no status to withdraw")


def _tree(repo: AdopterRepo) -> dict[str, bytes]:
    """Every file of the analysis, by path, as it is on disk."""
    return {
        p.relative_to(repo.root).as_posix(): p.read_bytes()
        for p in sorted((repo.root / ANALYSIS).rglob("*"))
        if p.is_file()
    }


def _met_by(repo: AdopterRepo, *args: str) -> subprocess.CompletedProcess[str]:
    """`pkit analysis met-by …`, run as the dispatcher runs it."""
    return run_script(repo, MET_BY, *args)


def _met(repo: AdopterRepo, *args: str) -> dict[str, list[str]]:
    """Each requirement's id, and the ids of what meets it, from `--json`."""
    completed = _met_by(repo, *args, "--json")
    assert completed.returncode == 0, completed.stderr
    document = json.loads(completed.stdout)
    assert document["schema_version"] == 1
    return {
        entry["id"]: [lister["id"] for lister in entry["met_by"]]
        for entry in document["requirements"]
    }


# --- the stamp --------------------------------------------------------------------------------


# Slow by design: two stamps, each a script that starts several `pkit` processes.
def test_the_stamp_writes_each_requirement_listed_and_anchors_it(listed: AdopterRepo) -> None:
    """`--requirement`, once for each, writes `requirements` and an artefact anchor on each
    requirement, after the actor and the other anchors the stamp writes. What it writes
    passes the check once filled (DEC-002 point 7)."""
    args = ("--actor", "ACT-tester", "--requirement", "REQ-004", "--requirement", "REQ-001")
    assert stamped(listed, "use-case", "export", *args, "--requirement", "REQ-004") == "UC-003"
    use_case = front(listed, f"{USE_CASES}/UC-003-export.md")
    assert use_case["requirements"] == ["REQ-004", "REQ-001"]
    assert use_case["pkit"]["friction"]["anchors"]["artefact"] == [
        "ACT-tester",
        "REQ-004",
        "REQ-001",
    ]
    steps = ("--actor", "ACT-tester", "--step", "UC-001", "--step", "UC-003")
    assert stamped(listed, "journey", "export-run", *steps, "--requirement", "REQ-001") == (
        "JRN-002"
    )
    journey = front(listed, f"{JOURNEYS}/JRN-002-export-run.md")
    assert journey["requirements"] == ["REQ-001"]
    assert journey["pkit"]["friction"]["anchors"]["artefact"] == [
        "ACT-tester",
        "UC-001",
        "UC-003",
        "REQ-001",
    ]
    fill(listed)
    assert errors(check(listed)) == []
    # Without the option, the list is written empty, and no requirement is anchored.
    assert front(listed, RUN_SUITE)["requirements"] == []


# Slow by design: six refused stamps, each a script that starts several `pkit` processes.
def test_the_stamp_refuses_a_requirement_not_held_or_withdrawn(listed: AdopterRepo) -> None:
    """A requirement the analysis does not hold, an artefact of another kind, and one
    withdrawn are each refused, for a use case and a journey, and nothing is written."""
    _withdraw(listed, LOCAL)
    before = sorted(p.relative_to(listed.root) for p in (listed.root / ANALYSIS).rglob("*"))
    steps = ("--step", "UC-001", "--step", "UC-002")
    for kind, extra in (("use-case", ()), ("journey", steps)):
        for listed_id, refusal in (
            ("REQ-009", "no requirement REQ-009 in the analysis: stamp it first"),
            ("UC-001", "no requirement UC-001 in the analysis"),
            (
                "REQ-001",
                f"requirement REQ-001 is withdrawn ({LOCAL}): a {kind.replace('-', ' ')} lists "
                f"only requirements in force",
            ),
        ):
            args = (kind, "later", "--actor", "ACT-tester", *extra, "--requirement", listed_id)
            completed = new(listed, *args)
            assert completed.returncode == 1, (args, completed.stdout)
            assert refusal in completed.stderr, (args, completed.stderr)
    after = sorted(p.relative_to(listed.root) for p in (listed.root / ANALYSIS).rglob("*"))
    assert after == before


# --- the check --------------------------------------------------------------------------------


def test_a_listed_requirement_is_one_of_the_analysis_and_in_force(listed: AdopterRepo) -> None:
    """Each listed requirement resolves to a requirement of the analysis, of any of the
    three kinds. A use case or a journey in force lists none withdrawn, and a withdrawn
    one may: it is history (DEC-002 point 7)."""
    _lists(listed, RUN_SUITE, ["REQ-004", "REQ-001"], ["REQ-004", "REQ-001"])
    _lists(listed, FIRST_RUN, ["REQ-001"], ["REQ-001"])
    assert errors(check(listed)) == []
    # Not in the analysis: a number nothing holds, and an id of the right shape.
    _lists(listed, READ_REPORT, ["REQ-009"], ["REQ-009"])
    assert errors(check(listed)) == [
        (
            f"{READ_REPORT}:/requirements/0",
            "no requirement REQ-009 in the analysis: what a use case lists is in the analysis "
            "(DEC-002 point 7)",
        )
    ]
    _set(listed, READ_REPORT, "  - REQ-009\n", "  - UC-001\n")
    found = errors(check(listed))
    # The schema refuses an id of another kind, and the anchors no longer match the list.
    assert [location for location, _message in found] == [
        f"{READ_REPORT}:/requirements/0",
        f"{READ_REPORT}:/pkit/friction/anchors/artefact",
    ]
    _set(listed, READ_REPORT, "  - UC-001\n", "  - REQ-004\n")
    _set(listed, READ_REPORT, "        - REQ-009\n", "        - REQ-004\n")
    assert errors(check(listed)) == []
    # Withdrawn while the use case and the journey are in force.
    _withdraw(listed, LOCAL)
    rule = "in force lists only requirements in force — take it off `requirements` and its anchors"
    assert sorted(errors(check(listed))) == [
        (
            f"{FIRST_RUN}:/requirements/0",
            f"requirement REQ-001 is withdrawn ({LOCAL}): a journey {rule}, or withdraw this "
            f"one too (DEC-002 point 7)",
        ),
        (
            f"{RUN_SUITE}:/requirements/1",
            f"requirement REQ-001 is withdrawn ({LOCAL}): a use case {rule}, or withdraw this "
            f"one too (DEC-002 point 7)",
        ),
    ]
    # A withdrawn use case and a withdrawn journey are history, and may list it.
    _withdraw(listed, RUN_SUITE)
    _withdraw(listed, FIRST_RUN)
    assert errors(check(listed)) == []


def test_the_requirement_anchors_match_the_list_exactly(listed: AdopterRepo) -> None:
    """A use case's and a journey's requirement anchors are exactly its `requirements`, as
    a journey's use-case anchors match its steps: a listed requirement not anchored, a
    requirement anchored and not listed, and a part anchor on a requirement each break it.
    An artefact anchor outside the analysis is not counted (DEC-002 point 7)."""
    rule = (
        "the anchors are written from `requirements`, so a changed requirement flags every "
        "use case and journey that lists it"
    )
    where = f"{RUN_SUITE}:/pkit/friction/anchors/artefact"
    _lists(listed, RUN_SUITE, ["REQ-004", "REQ-001"], ["REQ-004"])
    assert errors(check(listed)) == [
        (
            where,
            f"its requirement anchors (REQ-004) do not match its `requirements` (REQ-004, "
            f"REQ-001): {rule} — anchor exactly [REQ-004, REQ-001] (DEC-002 point 7)",
        )
    ]
    _set(listed, RUN_SUITE, "requirements:\n  - REQ-004\n  - REQ-001\n", "")
    assert errors(check(listed)) == [
        (
            where,
            f"its requirement anchors (REQ-004) do not match its `requirements` (none): {rule} "
            f"— anchor none (DEC-002 point 7)",
        )
    ]
    # A part anchor names its requirement before its last `#` (COR-050 point 2).
    _set(listed, RUN_SUITE, "        - REQ-004\n", "        - REQ-004#\n")
    _set(listed, RUN_SUITE, "other-actors: []\n", "other-actors: []\nrequirements: [REQ-004]\n")
    assert errors(check(listed)) == [
        (
            where,
            f"its requirement anchors (REQ-004#) do not match its `requirements` (REQ-004): "
            f"{rule} — anchor exactly [REQ-004] (DEC-002 point 7)",
        )
    ]
    _set(listed, RUN_SUITE, "        - REQ-004#\n", "        - REQ-004\n        - RS-SAN-001\n")
    assert errors(check(listed)) == []
    # A journey the same way.
    _lists(listed, FIRST_RUN, ["REQ-001"], [])
    assert errors(check(listed)) == [
        (
            f"{FIRST_RUN}:/pkit/friction/anchors/artefact",
            f"its requirement anchors (none) do not match its `requirements` (REQ-001): {rule} "
            f"— anchor exactly [REQ-001] (DEC-002 point 7)",
        )
    ]


# --- "Met by" ---------------------------------------------------------------------------------


def test_met_by_lists_the_use_cases_and_journeys_in_force_that_list_each_one(
    listed: AdopterRepo,
) -> None:
    """Each requirement, in the order of its number, with the use cases and then the
    journeys in force that list it. A withdrawn one meets nothing, and a requirement
    nothing lists says so. Nothing is written (DEC-002 point 7)."""
    assert _met(listed) == {"REQ-001": [], "REQ-004": []}
    _lists(listed, READ_REPORT, ["REQ-004"], ["REQ-004"])
    _lists(listed, RUN_SUITE, ["REQ-004", "REQ-001"], ["REQ-004", "REQ-001"])
    _lists(listed, FIRST_RUN, ["REQ-004"], ["REQ-004"])
    before = _tree(listed)
    assert _met(listed) == {"REQ-001": ["UC-001"], "REQ-004": ["UC-001", "UC-002", "JRN-001"]}
    assert _met(listed, "REQ-001") == {"REQ-001": ["UC-001"]}
    completed = _met_by(listed)
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.splitlines() == [
        f"REQ-001 · Constraint · {LOCAL_TITLE}",
        "  Met by:",
        "    UC-001 — Run suite",
        f"REQ-004 · Quality · {QUICK_TITLE}",
        "  Met by:",
        "    UC-001 — Run suite",
        "    UC-002 — Read report",
        "    JRN-001 — First run",
    ]
    document = json.loads(_met_by(listed, "REQ-001", "--json").stdout)
    assert document == {
        "schema_version": 1,
        "requirements": [
            {
                "id": "REQ-001",
                "kind": "constraint",
                "title": LOCAL_TITLE,
                "path": LOCAL,
                "shown_as": "Constraint",
                "status": "active",
                "met_by": [
                    {"id": "UC-001", "kind": "use-case", "title": "Run suite", "path": RUN_SUITE}
                ],
            }
        ],
    }
    # It wrote nothing: the analysis is as the edits left it.
    assert _tree(listed) == before
    # A use case in force that lists a withdrawn requirement is shown under it, and the
    # check refuses it.
    _withdraw(listed, LOCAL)
    assert _met(listed)["REQ-001"] == ["UC-001"]
    # A withdrawn use case meets nothing, and a withdrawn requirement keeps its status.
    _withdraw(listed, RUN_SUITE)
    assert _met(listed) == {"REQ-001": [], "REQ-004": ["UC-002", "JRN-001"]}
    assert _met_by(listed).stdout.splitlines()[:2] == [
        f"REQ-001 · Constraint · {LOCAL_TITLE} (withdrawn)",
        "  Met by: none",
    ]


def _no_answer(repo: AdopterRepo, said: str) -> None:
    """`met-by` gives no answer: exit 1, nothing on standard output, and `said` among the
    reason on standard error, with and without `--json`."""
    for args in ((), ("--json",)):
        completed = _met_by(repo, *args)
        assert (completed.returncode, completed.stdout) == (1, ""), args
        assert said in completed.stderr, (args, completed.stderr)


def test_met_by_gives_no_answer_it_cannot_give_in_full(listed: AdopterRepo) -> None:
    """A requirement the analysis does not hold is no answer, and so is a file whose list
    or whose requirement cannot be told: one whose front matter does not parse, one with
    none, a requirement with no id, and a use case whose `requirements` is no list. Each
    exits 1, with nothing on standard output and the reason on standard error."""
    completed = _met_by(listed, "REQ-009")
    assert (completed.returncode, completed.stdout) == (1, "")
    assert "no requirement REQ-009 in the analysis" in completed.stderr
    broken = f"{USE_CASES}/UC-009-broken.md"
    listed.write({broken: "---\nid: [UC-009\n---\n\n# UC-009 — Broken\n"})
    _no_answer(listed, f"{broken} cannot be read as an artefact of its place")
    (listed.root / broken).unlink()
    bare = f"{QUALITY}/REQ-005-bare.md"
    listed.write({bare: "# REQ-005 · Quality · No front matter\n"})
    _no_answer(listed, f"{bare} cannot be read as an artefact of its place")
    listed.write({bare: requirement(req_id="REQ-005", title="No id", id=None)})
    _no_answer(listed, f"{bare} gives no requirement id")
    (listed.root / bare).unlink()
    _set(listed, READ_REPORT, "requirements: []\n", "requirements: REQ-004\n")
    _no_answer(listed, f"{READ_REPORT} (UC-002) gives a `requirements` that is no list")
    # The check reports the field's shape once, as the schema's, and compares no anchors.
    assert [location for location, _message in errors(check(listed))] == [
        f"{READ_REPORT}:/requirements"
    ]


def test_with_no_requirement_met_by_says_so(listed: AdopterRepo) -> None:
    for rel in (LOCAL, QUICK):
        (listed.root / rel).unlink()
    completed = _met_by(listed)
    assert (completed.returncode, completed.stdout) == (0, "The analysis holds no requirement.\n")
    assert _met(listed) == {}


# --- where it is registered -------------------------------------------------------------------


def test_met_by_is_a_query_command_and_no_validator() -> None:
    package: dict[str, Any] = load((CAPABILITY / "package.yaml").read_text(encoding="utf-8"))
    leaf = package["commands"]["met-by"]
    assert (leaf["script"], leaf["query-contract"]) == ("scripts/met-by.py", True)
    assert package["validators"] == {"artefacts": {"command": "validate"}}
    result = CliRunner().invoke(main, ["analysis", "--help"])
    assert result.exit_code == 0, result.output
    assert "met-by " in result.output
