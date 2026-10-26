"""software-analysis: renumbering a new artefact with every reference to it (#1913).

`pkit analysis renumber` held to software-analysis DEC-001 point 3: when two lines
of work number a new artefact the same, the first to reach the default branch
keeps the number, and the other renumbers before merging. It gives this branch's
use case, journey or requirement a free number, renames its file, and rewrites
its id, its heading and every mention of it in the repository's analyses: front
matter and anchors, prose, revalidation records, and another analysis's mention
written with its qualifier. It refuses an artefact the default branch holds, a
number the working tree holds or one not past the default branch's, and shows its
plan before it writes (COR-004).
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from project_kit.cli import main
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.analysis_repo import (
    ANALYSIS,
    CAPABILITY,
    FUNCTIONAL,
    JOURNEYS,
    MAIN,
    NEW,
    NO_OVERVIEW,
    NUMBERS,
    OVERVIEW_FILE,
    QUALITY,
    RECORDS,
    SA,
    SETTINGS,
    SETTINGS_TEXT,
    USE_CASES,
    VALIDATE,
    fill,
    front,
    installed,
    link,
    load,
    load_lib,
    prepare,
    requirement,
    run_script,
    stamped,
)

RENUMBER = SA / "scripts" / "renumber.py"


def renumber(repo: AdopterRepo, *args: str) -> subprocess.CompletedProcess[str]:
    """`pkit analysis renumber …`, run as the dispatcher runs it, off a terminal."""
    return subprocess.run(
        [sys.executable, str(repo.root / RENUMBER), *args],
        cwd=repo.root,
        capture_output=True,
        text=True,
        check=False,
        stdin=subprocess.DEVNULL,
    )


def refused(completed: subprocess.CompletedProcess[str]) -> str:
    """The refusal's line, past any warning the backbone passes on (COR-054 point 2)."""
    assert completed.returncode == 1, completed.stdout + completed.stderr
    lines = [line for line in completed.stderr.splitlines() if line.startswith("refused: ")]
    assert len(lines) == 1, completed.stderr
    return lines[0]


def errors(repo: AdopterRepo) -> list[str]:
    """The check's errors on the working tree."""
    checked = json.loads(run_script(repo, VALIDATE, "--json").stdout)
    return [
        f"{f['location']}: {f['message']}" for f in checked["findings"] if f["severity"] == "error"
    ]


def text(repo: AdopterRepo, rel: str) -> str:
    return (repo.root / rel).read_text(encoding="utf-8")


def _today() -> str:
    return datetime.now(UTC).date().isoformat()


# Slow: two stamps, built once per session; the first test to ask pays it in its setup.
def _leave_main(repo: AdopterRepo) -> None:
    """`prepare`, then an actor and UC-001 on main, and the branch `topic` leaving main
    there."""
    prepare(repo)
    stamped(repo, "actor", "tester", "--path", "src/**")
    stamped(repo, "use-case", "one", "--actor", "ACT-tester", "--path", "src/run.py")
    fill(repo)
    repo.commit("UC-001")
    repo.checkout("topic", create=True)


@pytest.fixture
def branched(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    """The project with `topic` leaving main after an actor and UC-001 (`_leave_main`)."""
    return installed(make_adopter_repo, monkeypatch, then=_leave_main)


@pytest.fixture
def project(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    return installed(make_adopter_repo, monkeypatch)


# --- where it is registered -------------------------------------------------------------------


def test_it_is_a_command_that_writes_and_no_query() -> None:
    package = load((CAPABILITY / "package.yaml").read_text(encoding="utf-8"))
    leaf = package["commands"]["renumber"]
    assert leaf["script"] == "scripts/renumber.py" and "query-contract" not in leaf
    result = CliRunner().invoke(main, ["analysis", "--help"])
    assert result.exit_code == 0, result.output
    assert "renumber " in result.output


def test_a_mention_is_the_id_whole_in_any_spelling_of_its_number() -> None:
    """Every form of a mention is rewritten, and nothing that only holds the id inside a
    longer token: a link to the file and to its heading, a qualified mention, another
    spelling of the number."""
    (renumbering,) = load_lib("renumber")
    rewrite: Any = renumbering._rewriter("UC-021", "UC-031")
    written = (
        "steps: [UC-020, UC-021]\n"
        "See core:UC-021, UC-21 and [UC-021](../UC-021-export.md#uc-021--export).\n"
        "Not UC-0210, XUC-021, UC-0211 or uc-021 outside an anchor.\n"
    )
    changed, mentions = rewrite(written)
    assert changed == (
        "steps: [UC-020, UC-031]\n"
        "See core:UC-031, UC-031 and [UC-031](../UC-031-export.md#uc-031--export).\n"
        "Not UC-0210, XUC-021, UC-0211 or uc-021 outside an anchor.\n"
    )
    assert mentions == 6


# --- a use case, with every reference (DEC-001 point 3) ---------------------------------------


# Slow by design: a dozen `pkit` processes — stamps, the plan, the write and the checks.
def test_a_use_case_main_numbered_too_takes_the_next_free_number_with_every_reference(
    branched: AdopterRepo,
) -> None:
    """`topic` numbers UC-002, steps a journey through it, names it in a record and in
    main's UC-001; main numbers UC-002 meanwhile. Renumbered, `topic`'s takes UC-003, and
    every mention follows, the links of its id to its file included (DEC-001 point 14):
    the check and the number comparison pass, and so does the check once main is merged
    in."""
    assert stamped(branched, "use-case", "mine", "--actor", "ACT-tester") == "UC-002"
    steps = ("--step", "UC-001", "--step", "UC-002")
    assert stamped(branched, "journey", "both", "--actor", "ACT-tester", *steps) == "JRN-001"
    fill(branched)
    one = f"{USE_CASES}/UC-001-one.md"
    branched.write({one: text(branched, one) + "\nIt hands over to UC-002.\n"})
    link(branched)
    assert text(branched, one).endswith("\nIt hands over to [UC-002](UC-002-mine.md).\n")
    recorded = run_script(
        branched,
        NEW,
        "revalidation",
        "mine-found",
        "--change",
        "#7",
        "--trigger",
        "drift",
        "--outcome",
        "UC-002=gap-found",
        "--because",
        "UC-002=Nothing described the export.",
        "--gap",
        "UC-002: The export was undescribed => UC-002 written",
    )
    assert recorded.returncode == 0, recorded.stderr
    record = f"{RECORDS}/{_today()}-mine-found.md"
    branched.commit("UC-002 on topic")
    branched.checkout(MAIN)
    assert stamped(branched, "use-case", "theirs", "--actor", "ACT-tester") == "UC-002"
    fill(branched)
    branched.commit("UC-002 on main")
    branched.checkout("topic")
    assert run_script(branched, NUMBERS, "--base", MAIN).returncode == 1

    ours, renamed = f"{USE_CASES}/UC-002-mine.md", f"{USE_CASES}/UC-003-mine.md"
    journey = f"{JOURNEYS}/JRN-001-both.md"
    dry = renumber(branched, "UC-002", "--dry-run")
    assert dry.returncode == 0, dry.stderr
    assert dry.stdout.splitlines()[:5] == [
        "renumber UC-002 as UC-003 (DEC-001 point 3):",
        f"  rename    {ours} → {renamed}, 2 mentions",
        f"  rewrite   {record}, 4 mentions",
        f"  rewrite   {journey}, 4 mentions",
        f"  rewrite   {one}, 2 mentions",
    ]
    assert dry.stdout.endswith("dry run: nothing is written.\n")
    assert branched.git("status", "--porcelain").stdout == ""

    # Off a terminal, without --yes, nothing is written.
    asked = refused(renumber(branched, "UC-002"))
    assert "`pkit analysis renumber UC-002 --to UC-003 --yes`" in asked
    assert branched.git("status", "--porcelain").stdout == ""

    done = renumber(branched, "UC-002", "--yes")
    assert done.returncode == 0, done.stderr
    assert not (branched.root / ours).exists()
    assert front(branched, renamed)["id"] == "UC-003"
    assert "\n# UC-003 — Mine\n" in text(branched, renamed)
    walked = front(branched, journey)
    assert walked["steps"] == ["UC-001", "UC-003"]
    assert "UC-003" in walked["pkit"]["friction"]["anchors"]["artefact"]
    assert "2. [UC-003](../use-cases/UC-003-mine.md) — Mine" in text(branched, journey)
    assert front(branched, record)["outcomes"] == {"UC-003": "gap-found"}
    assert "- **UC-003:** The export was undescribed. **Resolution:** UC-003 written." in text(
        branched, record
    )
    assert text(branched, one).endswith("\nIt hands over to [UC-003](UC-003-mine.md).\n")
    assert "UC-002" not in "".join(text(branched, rel) for rel in (renamed, journey, record, one))
    assert errors(branched) == []
    assert run_script(branched, NUMBERS, "--base", MAIN).returncode == 0

    branched.commit("UC-002 renumbered as UC-003")
    branched.git("merge", "-q", "--no-edit", MAIN)
    assert errors(branched) == []


# --- a requirement ------------------------------------------------------------------------------


def test_a_requirement_takes_the_number_named_and_what_refines_it_follows(
    project: AdopterRepo,
) -> None:
    """A requirement's number is one across its three kinds (DEC-002 point 2). `topic`
    numbers a functional requirement REQ-001, refined by its REQ-002; main numbers a
    constraint REQ-001. `--to REQ-005` gives `topic`'s that number, its heading its
    kind, and REQ-002's `refines` and anchor follow."""
    project.checkout("topic", create=True)
    ours = f"{FUNCTIONAL}/REQ-001-who-started.md"
    refining = f"{QUALITY}/REQ-002-quickly.md"
    project.write(
        {
            ours: requirement("functional-requirement", req_id="REQ-001", title="Who started"),
            refining: requirement(
                req_id="REQ-002", title="Quickly", refines=["REQ-001"], anchored=["REQ-001"]
            ),
        }
    )
    project.commit("REQ-001 and REQ-002 on topic")
    project.checkout(MAIN)
    theirs = f"{ANALYSIS}/requirements/constraints/REQ-001-local-runs.md"
    project.commit("REQ-001 on main", {theirs: requirement("constraint", req_id="REQ-001")})
    project.checkout("topic")

    held = refused(renumber(project, "REQ-001", "--to", "REQ-002", "--yes"))
    assert "REQ-002 is held in the working tree already" in held
    assert "REQ-003 is the next free number" in held

    done = renumber(project, "REQ-001", "--to", "REQ-005", "--yes")
    assert done.returncode == 0, done.stderr
    moved = f"{FUNCTIONAL}/REQ-005-who-started.md"
    assert done.stdout.splitlines()[:3] == [
        "renumber REQ-001 as REQ-005 (DEC-001 point 3):",
        f"  rename    {ours} → {moved}, 2 mentions",
        f"  rewrite   {refining}, 2 mentions",
    ]
    assert "\n# REQ-005 · Functional · Who started\n" in text(project, moved)
    refines = front(project, refining)
    assert refines["refines"] == ["REQ-005"]
    assert refines["pkit"]["friction"]["anchors"]["artefact"] == ["REQ-005"]
    assert errors(project) == []
    assert run_script(project, NUMBERS, "--base", MAIN).returncode == 0


# --- across analyses ----------------------------------------------------------------------------


def test_another_analysis_s_qualified_mention_follows(project: AdopterRepo) -> None:
    """Ids are unique across a repository's analyses (DEC-001 point 3), so billing's
    mention of the core's use case, `core:UC-003`, names it, and follows it, its link to the
    core's file included (DEC-001 point 14)."""
    listed = (
        SETTINGS_TEXT + "analyses:\n  - {component: core, folder: core}\n"
        "  - component: billing\n    folder: billing\n    builds-on:\n      - {analysis: core}\n"
    )
    project.write({SETTINGS: listed})
    stamped(project, "actor", "tester", "--analysis", "core", "--path", "src/**")
    stamped(project, "use-case", "run-suite", "--actor", "ACT-tester", "--analysis", "core")
    stamped(project, "actor", "clerk", "--analysis", "billing", "--path", "src/**")
    stamped(project, "use-case", "invoice", "--actor", "ACT-clerk", "--analysis", "billing")
    fill(project)
    project.commit("two analyses")
    project.checkout("topic", create=True)
    assert stamped(
        project, "use-case", "export", "--actor", "ACT-tester", "--analysis", "core"
    ) == ("UC-003")
    fill(project)
    invoice = f"{ANALYSIS}/billing/use-case-model/use-cases/UC-002-invoice.md"
    project.write(
        {invoice: text(project, invoice) + "\nThe clerk exports it, as core:UC-003 does.\n"}
    )
    link(project)
    to_core = "../../../core/use-case-model/use-cases"
    assert text(project, invoice).endswith(f"as [core:UC-003]({to_core}/UC-003-export.md) does.\n")
    project.commit("UC-003 on topic")
    project.checkout(MAIN)
    stamped(project, "use-case", "theirs", "--actor", "ACT-tester", "--analysis", "core")
    fill(project)
    project.commit("UC-003 on main")
    project.checkout("topic")

    done = renumber(project, "UC-003", "--yes")
    assert done.returncode == 0, done.stderr
    core = f"{ANALYSIS}/core/use-case-model/use-cases"
    assert done.stdout.splitlines()[:3] == [
        "renumber UC-003 as UC-004 (DEC-001 point 3):",
        f"  rename    {core}/UC-003-export.md → {core}/UC-004-export.md, 2 mentions",
        f"  rewrite   {invoice}, 2 mentions",
    ]
    assert text(project, invoice).endswith(f"as [core:UC-004]({to_core}/UC-004-export.md) does.\n")
    assert errors(project) == []


# --- what it refuses ----------------------------------------------------------------------------


def test_a_number_the_default_branch_holds_is_never_renumbered(branched: AdopterRepo) -> None:
    """UC-001 is main's, settled: once settled, a number names one artefact for good —
    moved into an area here or not."""
    said = refused(renumber(branched, "UC-001", "--dry-run"))
    assert said.startswith(f"refused: UC-001 is main's, at {USE_CASES}/UC-001-one.md: once ")
    branched.rename(f"{USE_CASES}/UC-001-one.md", f"{USE_CASES}/core/UC-001-one.md")
    moved = refused(renumber(branched, "UC-001", "--dry-run"))
    assert f"it held UC-001 at {USE_CASES}/UC-001-one.md when this branch left it" in moved
    for named, why in (
        ("ACT-tester", "'ACT-tester' is no use case's, journey's or requirement's id"),
        ("UC-009", "no use case of the working tree holds UC-009"),
    ):
        assert why in refused(renumber(branched, named, "--dry-run"))


# Slow by design: four stamps on two branches, then the refusals.
def test_a_new_number_is_past_the_default_branch_s_and_spelt_one_way(
    branched: AdopterRepo,
) -> None:
    """`topic` holds UC-002 and UC-003, main UC-002 to UC-004: UC-004 is held nowhere here,
    yet not past main's, so refused, naming UC-005, the next free number. A number of
    another kind, or of another spelling, is refused too."""
    stamped(branched, "use-case", "two", "--actor", "ACT-tester")
    stamped(branched, "use-case", "three", "--actor", "ACT-tester")
    branched.commit("UC-002 and UC-003 on topic")
    branched.checkout(MAIN)
    for slug in ("a", "b", "c"):
        stamped(branched, "use-case", slug, "--actor", "ACT-tester")
    branched.commit("UC-002 to UC-004 on main")
    branched.checkout("topic")
    past = refused(renumber(branched, "UC-002", "--to", "UC-004", "--dry-run"))
    assert "UC-004 is not past what main holds or its history gave, UC-004 the highest" in past
    assert "UC-005 is the next free number" in past
    assert "is no use case's id" in refused(renumber(branched, "UC-002", "--to", "JRN-009"))
    assert "write UC-005" in refused(renumber(branched, "UC-002", "--to", "UC-0005"))
    planned = renumber(branched, "UC-002", "--dry-run")
    assert planned.stdout.startswith("renumber UC-002 as UC-005 (DEC-001 point 3):\n")


# Slow by design: a stacked branch and a squash merge.
def test_this_branch_s_own_work_landed_by_a_squash_is_settled(branched: AdopterRepo) -> None:
    """`parent` numbered UC-002, and `child` stacked on it; main squash-merged `parent`.
    main's UC-002 is the version `child`'s history wrote: its own work, landed, so the
    number is settled."""
    branched.checkout("parent", create=True)
    stamped(branched, "use-case", "two", "--actor", "ACT-tester")
    branched.commit("UC-002 on parent")
    branched.checkout("child", create=True)
    branched.checkout(MAIN)
    branched.squash_merge("parent")
    branched.checkout("child")
    said = refused(renumber(branched, "UC-002", "--dry-run"))
    assert f"main holds UC-002 at {USE_CASES}/UC-002-two.md in a version this branch wrote" in said


# --- main merged in -----------------------------------------------------------------------------


# Slow by design: stamps on two branches, a merge, the write and the check.
def test_main_s_own_mentions_merged_in_are_kept(branched: AdopterRepo) -> None:
    """main merged into `topic` brings its UC-002 and its journey through it, so the
    working tree holds UC-002 twice. Renumbering `topic`'s leaves main's file and its
    journey's mentions as they are."""
    stamped(branched, "use-case", "mine", "--actor", "ACT-tester")
    fill(branched)
    branched.commit("UC-002 on topic")
    branched.checkout(MAIN)
    stamped(branched, "use-case", "theirs", "--actor", "ACT-tester")
    stamped(
        branched, "journey", "both", "--actor", "ACT-tester", "--step", "UC-001", "--step", "UC-002"
    )
    fill(branched)
    branched.commit("UC-002 and JRN-001 on main")
    branched.checkout("topic")
    branched.git("merge", "-q", "--no-edit", MAIN)
    journey = f"{JOURNEYS}/JRN-001-both.md"
    before = text(branched, journey)

    done = renumber(branched, "UC-002", "--yes")
    assert done.returncode == 0, done.stderr
    assert done.stdout.splitlines()[:2] == [
        "renumber UC-002 as UC-003 (DEC-001 point 3):",
        f"  rename    {USE_CASES}/UC-002-mine.md → {USE_CASES}/UC-003-mine.md, 2 mentions",
    ]
    assert text(branched, journey) == before
    assert front(branched, f"{USE_CASES}/UC-002-theirs.md")["id"] == "UC-002"
    assert errors(branched) == []


def test_the_number_is_given_past_a_base_named_too(branched: AdopterRepo) -> None:
    """`--base` names a branch the new number lies past, beside the default branch, as
    the stamp's does: an integration branch that took UC-002 and UC-003 moves the next
    free number past them."""
    branched.checkout(MAIN)
    branched.checkout("integration", create=True)
    for slug in ("a", "b"):
        stamped(branched, "use-case", slug, "--actor", "ACT-tester")
    branched.commit("UC-002 and UC-003 on integration")
    branched.checkout("topic")
    stamped(branched, "use-case", "mine", "--actor", "ACT-tester")
    branched.commit("UC-002 on topic")
    alone = renumber(branched, "UC-002", "--dry-run")
    assert alone.stdout.startswith("renumber UC-002 as UC-003 "), alone.stderr
    past = renumber(branched, "UC-002", "--base", "integration", "--dry-run")
    assert past.stdout.startswith("renumber UC-002 as UC-004 "), past.stderr


# Slow by design: stamps on two branches, each drawing the overview, then the write.
def test_an_overview_that_names_it_is_drawn_anew(project: AdopterRepo) -> None:
    """An overview carries a fingerprint of what it draws (DEC-003 point 8), so it is
    drawn anew, never rewritten as text: the check finds it fresh after."""
    project.commit("keep an overview", {SETTINGS: SETTINGS_TEXT.replace(NO_OVERVIEW, "")})
    stamped(project, "actor", "tester", "--path", "src/**")
    stamped(project, "use-case", "one", "--actor", "ACT-tester")
    fill(project)
    project.commit("UC-001")
    project.checkout("topic", create=True)
    stamped(project, "use-case", "mine", "--actor", "ACT-tester")
    fill(project)
    project.commit("UC-002 on topic")
    project.checkout(MAIN)
    stamped(project, "use-case", "theirs", "--actor", "ACT-tester")
    fill(project)
    project.commit("UC-002 on main")
    project.checkout("topic")
    assert "UC-002 — Mine" in text(project, OVERVIEW_FILE)

    done = renumber(project, "UC-002", "--yes")
    assert done.returncode == 0, done.stderr
    assert f"  overview  {OVERVIEW_FILE}, drawn anew" in done.stdout.splitlines()
    drawn = text(project, OVERVIEW_FILE)
    assert "UC-003 — Mine" in drawn and "UC-002" not in drawn
    assert errors(project) == []
