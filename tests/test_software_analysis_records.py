"""software-analysis: revalidation records, and actors and terms kept unanchored (#888).

Held to software-analysis DEC-001 points 5, 6 and 9:

- the **record stamp**, `pkit analysis new revalidation` — a record names the
  change that carried it, its trigger, the day in UTC, who performed it — an
  agent only beside the person who confirmed it — each artefact covered with
  its outcome and why, and each gap paired with what resolved it; it is
  `revalidations/<date>-<slug>.md` under the analysis location and passes the
  check;
- **only when there is something to say** — a planned revalidation, one that
  found a regression or a gap, or one where a person decided an artefact was
  stale. One whose artefacts all hold, or were updated because the change was
  plainly meant, is refused: each artefact's own revalidation block is its
  record. A regression or a gap names what it found;
- **its body rendered with no hints** (#1366) — each gap labelled with the ids
  of the artefacts it affects, refused where the form `gaps-match-outcomes`
  refuses it, and `None.` where there is none;
- **a planned record's sources** (#1366) — `--reviewed-against`, once for each,
  only on a planned record and required there, each held to the record's
  schema; a commit the default branch does not hold is written with a warning,
  and one the stamp cannot place says nothing;
- **every word is the person's** — an outcome with no justification, and a text
  still holding a placeholder, are refused rather than written;
- an **actor or term nothing embodies** is stamped with its reason,
  `unanchored-because`, instead of anchors, and never with both — written in
  its friction block, the core's key, which the core reads (COR-050 point 1);
  an artefact carrying both, written by hand, is the core's validation finding,
  and the reason among the artefact's own fields is refused;
- **an open regression is visible**: the check reports a record's
  `code-regressed` artefact until it is revalidated on a later day than the
  record, and never fails on it.
"""

from __future__ import annotations

import datetime
import re
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from project_kit import friction_write as fw
from project_kit.friction_validate import FrictionFindingKind, validate_friction
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo, sign_nothing
from tests.analysis_repo import (
    ACTORS,
    CONSTRAINTS,
    GLOSSARY,
    NEW,
    RECORDS,
    USE_CASES,
    actor_at,
    fill,
    front,
    installed,
    new,
    prepare_seeded,
    run_script,
    stamped,
)
from tests.test_software_analysis_check import check, errors


@pytest.fixture
def project(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    return installed(make_adopter_repo, monkeypatch, then=prepare_seeded)


def _today() -> str:
    """The record's day: UTC, as a revalidation's `at` is."""
    return datetime.datetime.now(datetime.UTC).date().isoformat()


def _record(repo: AdopterRepo, *args: str) -> subprocess.CompletedProcess[str]:
    """`pkit analysis new revalidation …`: a record reads no default branch."""
    return run_script(repo, NEW, "revalidation", *args)


def _said(document: Mapping[str, Any], severity: str) -> list[tuple[str, str]]:
    """The check's findings of one severity that never fails: `warning` or `report`. The
    one that says no rule of `SAN` binds on the analysis is left out: it is said of every
    analysis no set of the project's own makes `SAN` bind on (DEC-001 point 1)."""
    return [
        (f["location"], f["message"])
        for f in document["findings"]
        if f["severity"] == severity
        and not f["message"].startswith("no rule of software-analysis:SAN binds")
    ]


def _records(repo: AdopterRepo) -> list[str]:
    folder = repo.root / RECORDS
    return sorted(p.name for p in folder.iterdir()) if folder.is_dir() else []


# --- a record with something to say (DEC-001 point 6) ------------------------------------


def test_a_regression_found_is_recorded_with_its_gap(project: AdopterRepo) -> None:
    completed = _record(
        project,
        "export-lost",
        "--change",
        "#45",
        "--trigger",
        "drift",
        "--outcome",
        "UC-001=code-regressed",
        "--outcome",
        "JRN-001=holds",
        "--because",
        "UC-001=The suite still runs from the CLI by design; the change dropped it.",
        "--because",
        "JRN-001=The first run still passes through both use cases.",
        "--gap",
        "UC-001: The suite no longer runs from the CLI => defect #46 reported",
        "--by-agent",
        "analysis-resolver",
        "--confirmed-by",
        "Sam",
    )
    assert completed.returncode == 0, completed.stderr
    rel = f"{RECORDS}/{_today()}-export-lost.md"
    assert completed.stdout.splitlines()[-1] == f"stamped {_today()}-export-lost at {rel}"
    assert front(project, rel) == {
        "change": "#45",
        "trigger": "drift",
        "date": _today(),
        "by": "analysis-resolver",
        "confirmed-by": "Sam",
        "outcomes": {"UC-001": "code-regressed", "JRN-001": "holds"},
    }
    body = (project.root / rel).read_text(encoding="utf-8").split("---\n", 2)[2]
    assert f"\n# {_today()} — Export lost\n" in body
    assert (
        "- **UC-001 — code-regressed.** The suite still runs from the CLI by design; the "
        "change dropped it.\n" in body
    )
    assert "- **JRN-001 — holds.** The first run still passes through both use cases.\n" in body
    # The gap's ids as its label, then the gap and its resolution, each ended (#1366).
    assert body.endswith(
        "## Gaps\n\n- **UC-001:** The suite no longer runs from the CLI. **Resolution:** "
        "defect #46 reported.\n"
    )
    assert "<" not in body and "UC-000" not in body
    assert errors(check(project)) == []


def test_a_gap_names_each_artefact_it_affects(project: AdopterRepo) -> None:
    """One gap may affect several artefacts: its ids, separated by commas, are its bold
    label, and each regression or gap found is named by one (DEC-001 point 6, #1366)."""
    completed = _record(
        project,
        "suite-lost",
        "--change",
        "#45",
        "--trigger",
        "scheduled",
        "--outcome",
        "UC-001=code-regressed",
        "--outcome",
        "JRN-001=code-regressed",
        "--because",
        "UC-001=Running the suite is still wanted.",
        "--because",
        "JRN-001=The first run still starts with the suite.",
        "--gap",
        "UC-001,JRN-001: The suite no longer runs? => defect #46 reported!",
    )
    assert completed.returncode == 0, completed.stderr
    body = (project.root / RECORDS / f"{_today()}-suite-lost.md").read_text(encoding="utf-8")
    assert body.endswith(
        "## Gaps\n\n- **UC-001, JRN-001:** The suite no longer runs? **Resolution:** defect "
        "#46 reported!\n"
    )
    assert errors(check(project)) == []


#: A constraint, written whole as a person fills it, as its structure asks.
CONSTRAINT = (
    "---\nid: REQ-004\ntitle: Run suites on the client's machines\nstatus: active\n"
    "statement: The system runs every suite on a machine the client owns.\n"
    "measure: None.\napplies-to: The whole system.\n"
    "pkit:\n  friction:\n    anchors:\n      path: [src/run.py]\n---\n\n"
    "# REQ-004 · Constraint · Run suites on the client's machines\n\n"
    "**Verified by:** None.\n\n**Imposed by:** None.\n"
)


def test_a_requirement_s_regression_or_gap_is_recorded_with_its_gap(project: AdopterRepo) -> None:
    """A record's outcomes may name a requirement (DEC-002, Implications, #1691), so the
    stamp takes its id in an outcome and in the gap that names it, as any artefact's."""
    project.write({f"{CONSTRAINTS}/REQ-004-client-machines.md": CONSTRAINT})
    completed = _record(
        project,
        "suite-abroad",
        "--change",
        "#45",
        "--trigger",
        "drift",
        "--outcome",
        "REQ-004=gap-found",
        "--because",
        "REQ-004=The design now runs suites on a hired host, which nothing describes.",
        "--gap",
        "REQ-004: suites run on a hired host => the host is withdrawn, #46",
    )
    assert completed.returncode == 0, completed.stderr
    rel = f"{RECORDS}/{_today()}-suite-abroad.md"
    assert front(project, rel)["outcomes"] == {"REQ-004": "gap-found"}
    body = (project.root / rel).read_text(encoding="utf-8")
    assert body.endswith(
        "## Gaps\n\n- **REQ-004:** suites run on a hired host. **Resolution:** the host is "
        "withdrawn, #46.\n"
    )
    assert errors(check(project)) == []


#: A planned revalidation of UC-002 that found it holds.
PLANNED = (
    "--change",
    "#50",
    "--trigger",
    "planned",
    "--outcome",
    "UC-002=holds",
    "--because",
    "UC-002=The redesign keeps the report's content; only its layout changes.",
)


#: A source in the tracker, as `--reviewed-against` takes it: its title, its version and
#: its link.
TRACKER = "#50's body @ 2026-01-05T10:00:00Z @ https://tracker.example/issues/50"


def _source_warnings(completed: subprocess.CompletedProcess[str]) -> list[str]:
    """The stamp's warnings on the sources a record names, each opening with the source's
    title: what the backbone warns of the default branch it reads stands apart."""
    return [line for line in completed.stderr.splitlines() if line.startswith('warning: "')]


def _off_the_default_branch(repo: AdopterRepo) -> str:
    """A commit the clone holds and the default branch's history never reaches, as a
    branch's commit is once a squash merge left it behind."""
    tree = repo.git("rev-parse", "HEAD^{tree}").stdout.strip()
    return repo.git("commit-tree", tree, "-p", "HEAD", "-m", "the design").stdout.strip()


def test_a_planned_revalidation_is_something_to_say_and_names_its_sources(
    project: AdopterRepo,
) -> None:
    """A planned revalidation leaves a record even when everything holds (DEC-001 point
    6), and the record names each source of the design it reviewed in
    `reviewed-against`, one `--reviewed-against` each (#1366): a title and a version, then
    a link outside this repository. A time is written quoted, as is any value YAML would
    read as something other than text, so each reads back as the text written. A commit
    the default branch holds draws no warning."""
    held = project.head()
    sources = (
        "--reviewed-against",
        TRACKER,
        "--reviewed-against",
        f"the redesign note @ {held}",
        "--reviewed-against",
        "the export's design, part 2 @ this change",
    )
    completed = _record(project, "report-redesign", *PLANNED, *sources)
    assert completed.returncode == 0, completed.stderr
    assert _source_warnings(completed) == []
    rel = f"{RECORDS}/{_today()}-report-redesign.md"
    record = front(project, rel)
    assert list(record) == ["change", "trigger", "reviewed-against", "date", "by", "outcomes"]
    assert record["reviewed-against"] == [
        {
            "title": "#50's body",
            "url": "https://tracker.example/issues/50",
            "version": "2026-01-05T10:00:00Z",
        },
        {"title": "the redesign note", "version": held},
        {"title": "the export's design, part 2", "version": "this change"},
    ]
    text = (project.root / rel).read_text(encoding="utf-8")
    assert "version: '2026-01-05T10:00:00Z'" in text or 'version: "2026-01-05T10:00:00Z"' in text
    assert text.endswith("## Gaps\n\nNone.\n")
    assert errors(check(project)) == []


def test_a_planned_record_names_its_sources_and_only_a_planned_record_does(
    project: AdopterRepo,
) -> None:
    """A planned record without its sources is refused, saying how to give them, never
    "nothing to record". A record of another trigger is refused one (DEC-001 point 6)."""
    completed = _record(project, "report-redesign", *PLANNED)
    assert completed.returncode == 1, completed.stdout
    assert "a planned record names each source of the design it reviewed" in completed.stderr
    assert '"<title> @ <version>" for a source in this repository' in completed.stderr
    assert "nothing to record" not in completed.stderr
    completed = _record(project, "report-redesign", *STALE, "--reviewed-against", TRACKER)
    assert completed.returncode == 1, completed.stdout
    assert "a record triggered by drift takes none (DEC-001 point 6)" in completed.stderr
    assert _records(project) == []


@pytest.mark.parametrize(
    ("value", "refusal"),
    [
        ("the redesign note", 'is not "<title> @ <version>"'),
        (" @ this change", 'is not "<title> @ <version>"'),
        (
            "the redesign note @ 4c1d2e9",
            "reads as title 'the redesign note', version '4c1d2e9', which the record's schema "
            "refuses",
        ),
        (
            "#50's body @ 2026-01-05 10:00 @ https://tracker.example/issues/50",
            "version '2026-01-05 10:00', which the record's schema refuses",
        ),
        (
            "#50's body @ this change @ https://tracker.example/issues/50",
            "url 'https://tracker.example/issues/50', version 'this change', which",
        ),
        ("#50's body @ 2026-01-05T10:00:00Z", "version '2026-01-05T10:00:00Z', which"),
        ("<what the source is> @ this change", "still holds the placeholder"),
    ],
    ids=[
        "no-version",
        "no-title",
        "short-commit",
        "time-not-utc",
        "this-change-outside",
        "time-without-a-link",
        "placeholder",
    ],
)
def test_a_source_the_record_s_schema_refuses_is_refused(
    project: AdopterRepo, value: str, refusal: str
) -> None:
    """Each source is held to the record's schema before anything is written: a commit's
    full id, or `this change`, in this repository, and outside it a time in UTC or a
    commit's full id, beside its link (DEC-001 point 6)."""
    completed = _record(project, "report-redesign", *PLANNED, "--reviewed-against", value)
    assert completed.returncode == 1, completed.stdout
    assert refusal in completed.stderr
    assert _records(project) == []


def test_a_commit_off_the_default_branch_is_written_with_a_warning(project: AdopterRepo) -> None:
    """A source naming a commit the default branch does not hold is written all the same,
    and the stamp warns that `pkit analysis check-pointers` fails the change until the
    source names a commit the default branch holds, or `this change`: refusing would leave
    no way to write the record while the design's pull request is open (#1366). The stamp
    places the commit as that command does (#1448)."""
    branch = _off_the_default_branch(project)
    completed = _record(
        project, "report-redesign", *PLANNED, "--reviewed-against", f"the redesign note @ {branch}"
    )
    assert completed.returncode == 0, completed.stderr
    (warning,) = _source_warnings(completed)
    assert warning.startswith(
        f'warning: "the redesign note" names {branch[:12]}, which the default branch, main, '
        f"does not hold: `pkit analysis check-pointers` fails the change that adds this record "
        f"until the source names a commit main holds, or `this change`"
    )
    assert completed.stdout.splitlines()[-1].startswith("stamped ")
    assert _records(project) == [f"{_today()}-report-redesign.md"]


def test_a_commit_the_stamp_cannot_place_says_nothing(project: AdopterRepo, tmp_path: Path) -> None:
    """A commit beyond a shallow clone's cut cannot be placed, and draws no warning: the
    pointers are provenance, and `pkit analysis check-pointers` reports it as unknown
    (#1448). A clone one commit deep holds the analysis, and not the commit before it. A
    clone holds no `user.name` of its own, so the record names who performed it with
    `--by`, and the test does not depend on the machine's git configuration."""
    project.commit("the analysis")
    before = project.git("rev-parse", "HEAD~1").stdout.strip()
    shallow = tmp_path / "shallow"
    project.git("clone", "-q", "--depth", "1", f"file://{project.root}", str(shallow))
    clone = AdopterRepo(shallow, source_kit=project.source_kit)
    sign_nothing(shallow)
    completed = _record(
        clone,
        "report-redesign",
        *PLANNED,
        "--reviewed-against",
        f"the redesign note @ {before}",
        "--by",
        "Sam",
    )
    assert completed.returncode == 0, completed.stderr
    assert _source_warnings(completed) == []
    assert _records(clone) == [f"{_today()}-report-redesign.md"]


#: A drift revalidation where a person decided UC-002 was stale: something to say.
STALE = (
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


def test_a_record_with_no_gap_says_none_found(project: AdopterRepo) -> None:
    completed = _record(project, "report-redesign", *STALE)
    assert completed.returncode == 0, completed.stderr
    rel = f"{RECORDS}/{_today()}-report-redesign.md"
    assert front(project, rel)["by"] == "pkit-test"  # git's user.name, when --by is not given
    body = (project.root / rel).read_text(encoding="utf-8")
    assert body.endswith("## Gaps\n\nNone.\n")  # `None.`, as every part reads it (#1366)
    assert "pkit:hint" not in body  # the stamp writes every part, so it writes no hint
    assert errors(check(project)) == []


def test_an_open_regression_is_reported_until_it_is_revalidated_on_a_later_day(
    project: AdopterRepo,
) -> None:
    regression = (
        "--change",
        "#45",
        "--trigger",
        "drift",
        "--outcome",
        "UC-001=code-regressed",
        "--because",
        "UC-001=Running the suite is still wanted; the change dropped it.",
        "--gap",
        "UC-001: The suite no longer runs => defect #46 reported",
    )
    assert _record(project, "suite-lost", *regression).returncode == 0
    where = f"{RECORDS}/{_today()}-suite-lost.md:/outcomes/UC-001"
    ((location, message),) = _said(check(project), "report")
    assert location == where
    assert message.startswith("UC-001's regression is open: never revalidated, not since")

    # The regression's own answer, the same day, leaves it open.
    now = datetime.datetime.now(datetime.UTC)
    because = "The description stands: running the suite is wanted; defect #46 reported."
    fw.write(
        fw.plan_revalidate(project.root, "UC-001", outcome="unchanged", because=because, now=now)
    )
    ((location, message),) = _said(check(project), "report")
    assert location == where
    assert f"is open: last revalidated {_today()}, not since" in message

    # Revalidated against the fix on a later day, it is closed; it never failed the check.
    later = now + datetime.timedelta(days=1)
    fixed = "The fix for #46 runs the suite again, as step 1 says."
    fw.write(
        fw.plan_revalidate(project.root, "UC-001", outcome="unchanged", because=fixed, now=later)
    )
    document = check(project)
    assert _said(document, "report") == []
    assert errors(document) == []


# --- nothing to say, or not enough (DEC-001 points 5 and 6) ------------------------------------


#: UC-001's justification, as a refusal test that is not about it gives it.
WHY = ("--because", "UC-001=The suite still runs as described.")


@pytest.mark.parametrize(
    ("args", "refusal"),
    [
        (("--trigger", "drift"), "--outcome <id>=<outcome>"),
        (("--trigger", "drift", "--outcome", "UC-001=holds"), "nothing to record"),
        (
            (
                "--trigger",
                "close",
                "--outcome",
                "UC-001=holds",
                "--outcome",
                "JRN-001=analysis-stale",
            ),
            "nothing to record",
        ),
        (
            ("--trigger", "drift", "--outcome", "UC-001=code-regressed"),
            "UC-001 found a regression or a gap: name each with --gap",
        ),
        (
            ("--trigger", "scheduled", "--outcome", "UC-001=gap-found", *WHY, "--gap", "An export"),
            'is not "<ids>: <gap> => <resolution>"',
        ),
        (
            ("--trigger", "scheduled", "--outcome", "UC-001=gap-found", *WHY, "--gap", " => x"),
            'is not "<ids>: <gap> => <resolution>"',
        ),
        (
            (
                "--trigger",
                "scheduled",
                "--outcome",
                "UC-001=gap-found",
                *WHY,
                "--gap",
                "An export goes nowhere => defect #46 reported",
            ),
            'is not "<ids>: <gap> => <resolution>": the ids of the artefacts it affects',
        ),
        (
            # Written without its ids, a gap whose own text holds a colon is refused for
            # its form, naming what is no id, rather than as a gap of no outcome.
            (
                "--trigger",
                "scheduled",
                "--outcome",
                "UC-001=gap-found",
                *WHY,
                "--gap",
                "Step 2: export fails => #9",
            ),
            "--gap 'Step 2: export fails => #9' is not \"<ids>: <gap> => <resolution>\" "
            "('Step 2' is no artefact's id): the ids of the artefacts it affects",
        ),
        (
            (
                "--trigger",
                "scheduled",
                "--outcome",
                "UC-001=gap-found",
                *WHY,
                "--gap",
                "Step 2, step 3: export fails => #9",
            ),
            "('Step 2', 'step 3' are no artefacts' ids)",
        ),
        (
            # The skill's command pasted as shown: its placeholders are what to fill first.
            (
                "--trigger",
                "scheduled",
                "--outcome",
                "UC-001=gap-found",
                *WHY,
                "--gap",
                "<ids>: <what was found> => <the defect reported, or the artefact written>",
            ),
            "--gap still holds the placeholder '<what was found>'",
        ),
        (
            (
                "--trigger",
                "scheduled",
                "--outcome",
                "UC-001=gap-found",
                *WHY,
                "--gap",
                "UC-001, : An export goes nowhere => defect #46 reported",
            ),
            'is not "<ids>: <gap> => <resolution>"',
        ),
        (
            (
                "--trigger",
                "scheduled",
                "--outcome",
                "UC-001=gap-found",
                *WHY,
                "--gap",
                "UC-002: An export goes nowhere => defect #46 reported",
            ),
            "--gap 'UC-002: An export goes nowhere => defect #46 reported': the gap names "
            "`UC-002`, which `outcomes` does not list",
        ),
        (
            (
                "--trigger",
                "scheduled",
                "--outcome",
                "UC-001=gap-found",
                "--outcome",
                "UC-002=code-regressed",
                *WHY,
                "--because",
                "UC-002=Reading the report is still wanted.",
                "--gap",
                "UC-001: An export goes nowhere => defect #46 reported",
            ),
            "the gaps break the form `gaps-match-outcomes`: UC-002's outcome is "
            "`code-regressed`, and no gap names it",
        ),
        (
            (
                "--trigger",
                "scheduled",
                "--outcome",
                "UC-001=gap-found",
                *WHY,
                "--gap",
                "UC-001: An export goes nowhere.\n\nNothing says so. => defect #46 reported",
            ),
            "holds a line break: the record writes it on one line",
        ),
        (
            (
                "--trigger",
                "planned",
                "--outcome",
                "UC-001=holds",
                "--because",
                "UC-001=The suite still runs.\nAs described.",
            ),
            "--because UC-001 'The suite still runs.\\nAs described.' holds a line break",
        ),
        (
            ("--trigger", "planned", "--outcome", "UC-001=holds", "--outcome", "JRN-001=holds"),
            "JRN-001 has no --because",
        ),
        (
            ("--trigger", "planned", "--outcome", "UC-001=holds", *WHY, *WHY),
            "UC-001 is given two --because",
        ),
        (
            ("--trigger", "planned", "--outcome", "UC-001=holds", *WHY, "--by-agent", "resolver"),
            "resolver is an agent: name the person who confirmed its outcomes",
        ),
        (
            (
                "--trigger",
                "drift",
                "--outcome",
                "UC-001=code-regressed",
                "--because",
                "UC-001=The export is wanted; defect <the defect reference> reported.",
                "--gap",
                "UC-001: Nothing exports => defect #46 reported",
            ),
            "--because UC-001 still holds the placeholder '<the defect reference>'",
        ),
        (
            (
                "--trigger",
                "drift",
                "--outcome",
                "UC-001=code-regressed",
                *WHY,
                "--gap",
                "UC-001: Nothing exports => defect <the defect reference> reported",
            ),
            "--gap still holds the placeholder '<the defect reference>'",
        ),
        (
            (
                "--trigger",
                "planned",
                "--outcome",
                "UC-001=holds",
                *WHY,
                "--confirmed-by",
                "<your name>",
            ),
            "--confirmed-by still holds the placeholder '<your name>'",
        ),
        (
            ("--trigger", "planned", "--outcome", "UC-009=holds"),
            "no artefact UC-009 in the analysis",
        ),
        (("--trigger", "planned", "--outcome", "UC-001=hold"), "'hold' is not one of holds"),
        (
            ("--trigger", "planned", "--outcome", "UC-001=holds", "--outcome", "UC-001=gap-found"),
            "UC-001 is given two outcomes",
        ),
        (
            ("--trigger", "planned", "--outcome", "UC-001=holds", "--because", "UC-002=It does."),
            "--because names UC-002, which has no --outcome",
        ),
    ],
)
def test_a_record_with_nothing_to_say_or_not_enough_is_refused(
    project: AdopterRepo, args: tuple[str, ...], refusal: str
) -> None:
    """Nothing is written, whichever refusal it is."""
    completed = _record(project, "subject", "--change", "#45", *args)
    assert completed.returncode == 1, completed.stdout
    assert refusal in completed.stderr
    assert _records(project) == []


def test_a_stale_artefact_a_person_decided_is_recorded(project: AdopterRepo) -> None:
    """Where stale against regressed was ambiguous, the person's "meant" is what a
    record keeps (DEC-001 point 5): with no one named, the artefact's own block is
    the record, and the stamp refuses."""
    args = (
        "--change",
        "4c1d2e9",
        "--trigger",
        "scheduled",
        "--outcome",
        "UC-001=analysis-stale",
        "--because",
        "UC-001=run_suite became execute on purpose; step 1 now names execute.",
    )
    refused = _record(project, "runner-renamed", *args)
    assert refused.returncode == 1 and "nothing to record" in refused.stderr
    completed = _record(project, "runner-renamed", *args, "--confirmed-by", "Sam")
    assert completed.returncode == 0, completed.stderr
    record = front(project, f"{RECORDS}/{_today()}-runner-renamed.md")
    assert (record["by"], record["confirmed-by"]) == ("pkit-test", "Sam")
    assert errors(check(project)) == []


def test_a_person_and_an_agent_are_not_both_who_performed_it(project: AdopterRepo) -> None:
    args = (*PLANNED, "--by", "Sam", "--by-agent", "analysis-resolver", "--confirmed-by", "Sam")
    completed = _record(project, "report-redesign", *args)
    assert completed.returncode == 2  # a usage error: one of the two
    assert _records(project) == []


def test_a_record_already_written_is_not_overwritten(project: AdopterRepo) -> None:
    args = STALE
    assert _record(project, "report-redesign", *args).returncode == 0
    completed = _record(project, "report-redesign", *args)
    assert completed.returncode == 1
    assert "exists already: name the subject with another slug" in completed.stderr
    assert _records(project) == [f"{_today()}-report-redesign.md"]


# --- unanchored with its reason (DEC-001 point 9) ------------------------------------------


@pytest.mark.parametrize(
    ("kind", "rel", "prefix"),
    [("actor", actor_at("ACT-sponsor"), "ACT"), ("term", GLOSSARY, "TERM")],
)
def test_an_actor_or_term_nothing_embodies_carries_its_reason(
    project: AdopterRepo, kind: str, rel: str, prefix: str
) -> None:
    reason = "No code or decision embodies it: it is who funds the project."
    stamped(project, kind, "sponsor", "--unanchored-because", reason)
    fill(project)
    written = front(project, rel)
    entry = written if kind == "actor" else written[f"{prefix}-sponsor"]
    # In the core friction block, never among the entry's own fields (COR-050 point 1).
    assert "unanchored-because" not in entry and list(entry)[-1] == "pkit"
    assert entry["pkit"] == {"friction": {"unanchored-because": reason}}
    assert errors(check(project)) == []
    validation = validate_friction(project.root)
    assert validation.errors == ()
    # The core reads it: the unanchored measure lists the artefact apart with it.
    (sponsor,) = [a for a in validation.discovery.artefacts if a.id == f"{prefix}-sponsor"]
    assert sponsor.unanchored_because == reason


@pytest.mark.parametrize(
    ("args", "refusal"),
    [
        (
            ("actor", "sponsor", "--unanchored-because", "Nothing.", "--path", "src/**"),
            "an actor with anchors is not unanchored",
        ),
        (("term", "sponsor", "--unanchored-because", " "), "gives the reason it has no anchors"),
        (
            ("actor", "sponsor", "--unanchored-because", "<why nothing embodies it>"),
            "--unanchored-because still holds the placeholder '<why nothing embodies it>'",
        ),
    ],
)
def test_unanchored_is_refused_with_anchors_or_without_a_reason(
    project: AdopterRepo, args: tuple[str, ...], refusal: str
) -> None:
    before = sorted(p.name for p in (project.root / ACTORS).iterdir())
    completed = new(project, *args)
    assert completed.returncode == 1
    assert refusal in completed.stderr
    assert sorted(p.name for p in (project.root / ACTORS).iterdir()) == before
    assert not (project.root / GLOSSARY).exists()


def test_a_use_case_takes_no_unanchored_reason(project: AdopterRepo) -> None:
    completed = new(
        project, "use-case", "idle", "--actor", "ACT-tester", "--unanchored-because", "Nothing."
    )
    assert completed.returncode == 2  # not an option a use case has: it anchors to its actor
    assert not any((project.root / USE_CASES).glob("*-idle.md"))


def test_unanchored_because_beside_anchors_is_the_core_s_finding(project: AdopterRepo) -> None:
    """The stamp refuses the pair; a hand edit that writes it into the friction block
    fails the core's validation (COR-050 point 12), and the capability's check says
    nothing of it — the key is the core's."""
    tester = actor_at("ACT-tester")
    text = (project.root / tester).read_text(encoding="utf-8")
    block = re.search(r"\n( +)friction:\n", text)
    assert block is not None
    indent = block.group(1) + "  "
    written = f"{block.group(0)}{indent}unanchored-because: No code embodies it.\n"
    project.write({tester: text.replace(block.group(0), written, 1)})
    assert front(project, tester)["pkit"]["friction"]["anchors"]

    document = check(project)
    assert errors(document) == [] and _said(document, "warning") == []
    (finding,) = validate_friction(project.root).errors
    assert finding.kind is FrictionFindingKind.UNANCHORED_BESIDE_ANCHORS
    assert (finding.location, finding.pointer) == (tester, "/pkit/friction/unanchored-because")


def test_a_placeholder_left_in_the_block_s_reason_fails_the_check(project: AdopterRepo) -> None:
    """The stamp refuses a placeholder in `--unanchored-because`; one written into the
    friction block by hand is caught as a placeholder left in an own field is."""
    stamped(project, "actor", "sponsor", "--unanchored-because", "Nothing embodies it.")
    fill(project)
    sponsor = actor_at("ACT-sponsor")
    text = (project.root / sponsor).read_text(encoding="utf-8")
    placeholder = "<why nothing embodies it>"
    project.write({sponsor: text.replace("Nothing embodies it.", placeholder, 1)})
    assert front(project, sponsor)["pkit"]["friction"] == {"unanchored-because": placeholder}
    ((location, message),) = errors(check(project))
    assert location == f"{sponsor}:/pkit/friction/unanchored-because"
    assert f"still holds the placeholder '{placeholder}'" in message


def test_the_reason_among_an_artefact_s_own_fields_is_refused(project: AdopterRepo) -> None:
    """The reason is the friction block's, not the artefact's: written among the actor's
    own fields, the companion schema refuses it as a field it does not know."""
    tester = actor_at("ACT-tester")
    text = (project.root / tester).read_text(encoding="utf-8")
    reason = "id: ACT-tester\nunanchored-because: No code embodies it.\n"
    project.write({tester: text.replace("id: ACT-tester\n", reason, 1)})
    ((location, message),) = errors(check(project))
    assert location == tester
    assert "'unanchored-because' was unexpected" in message
