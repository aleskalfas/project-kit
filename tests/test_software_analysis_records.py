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
- **every word is the person's** — an outcome with no justification, and a text
  still holding a placeholder, are refused rather than written;
- an **actor or term nothing embodies** is stamped with its reason,
  `unanchored-because`, instead of anchors, and never with both — and the
  check warns about an artefact carrying both, written by hand;
- **an open regression is visible**: the check reports a record's
  `code-regressed` artefact until it is revalidated on a later day than the
  record, and never fails on it.
"""

from __future__ import annotations

import datetime
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from project_kit import friction_write as fw
from project_kit.friction_validate import validate_friction
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.analysis_repo import (
    ACTORS,
    GLOSSARY,
    NEW,
    RECORDS,
    USE_CASES,
    fill,
    front,
    installed,
    new,
    run_script,
    seed,
    stamped,
)
from tests.test_software_analysis_check import check, errors


@pytest.fixture
def project(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    repo = installed(make_adopter_repo, monkeypatch)
    seed(repo)
    return repo


def _today() -> str:
    """The record's day: UTC, as a revalidation's `at` is."""
    return datetime.datetime.now(datetime.UTC).date().isoformat()


def _record(repo: AdopterRepo, *args: str) -> subprocess.CompletedProcess[str]:
    """`pkit analysis new revalidation …`: a record reads no default branch."""
    return run_script(repo, NEW, "revalidation", *args)


def _said(document: Mapping[str, Any], severity: str) -> list[tuple[str, str]]:
    """The check's findings of one severity that never fails: `warning` or `report`."""
    return [
        (f["location"], f["message"]) for f in document["findings"] if f["severity"] == severity
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
        "The suite no longer runs from the CLI => defect #46 reported",
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
    assert "- The suite no longer runs from the CLI — **resolved:** defect #46 reported\n" in body
    assert "<" not in body and "UC-000" not in body
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


def test_a_planned_revalidation_is_recorded_even_when_everything_holds(
    project: AdopterRepo,
) -> None:
    completed = _record(project, "report-redesign", *PLANNED)
    assert completed.returncode == 0, completed.stderr
    rel = f"{RECORDS}/{_today()}-report-redesign.md"
    assert front(project, rel)["by"] == "pkit-test"  # git's user.name, when --by is not given
    body = (project.root / rel).read_text(encoding="utf-8")
    assert body.endswith("## Gaps\n\nNone found.\n")
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
        "The suite no longer runs => defect #46 reported",
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
            'is not "<gap> => <resolution>"',
        ),
        (
            ("--trigger", "scheduled", "--outcome", "UC-001=gap-found", *WHY, "--gap", " => x"),
            'is not "<gap> => <resolution>"',
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
                "Nothing exports => defect #46 reported",
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
                "Nothing exports => defect <the defect reference> reported",
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
    args = PLANNED
    assert _record(project, "report-redesign", *args).returncode == 0
    completed = _record(project, "report-redesign", *args)
    assert completed.returncode == 1
    assert "exists already: name the subject with another slug" in completed.stderr
    assert _records(project) == [f"{_today()}-report-redesign.md"]


# --- unanchored with its reason (DEC-001 point 9) ------------------------------------------


@pytest.mark.parametrize(
    ("kind", "rel", "prefix"), [("actor", ACTORS, "ACT"), ("term", GLOSSARY, "TERM")]
)
def test_an_actor_or_term_nothing_embodies_carries_its_reason(
    project: AdopterRepo, kind: str, rel: str, prefix: str
) -> None:
    reason = "No code or decision embodies it: it is who funds the project."
    stamped(project, kind, "sponsor", "--unanchored-because", reason)
    fill(project)
    entry = front(project, rel)[f"{prefix}-sponsor"]
    assert entry["unanchored-because"] == reason
    assert list(entry)[-2:] == ["unanchored-because", "pkit"]
    assert entry["pkit"] == {"friction": {}}
    assert errors(check(project)) == []
    assert validate_friction(project.root).errors == ()


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
    before = {p: (project.root / p).read_text(encoding="utf-8") for p in (ACTORS,)}
    completed = new(project, *args)
    assert completed.returncode == 1
    assert refusal in completed.stderr
    assert {p: (project.root / p).read_text(encoding="utf-8") for p in before} == before
    assert not (project.root / GLOSSARY).exists()


def test_a_use_case_takes_no_unanchored_reason(project: AdopterRepo) -> None:
    completed = new(
        project, "use-case", "idle", "--actor", "ACT-tester", "--unanchored-because", "Nothing."
    )
    assert completed.returncode == 2  # not an option a use case has: it anchors to its actor
    assert not any((project.root / USE_CASES).glob("*-idle.md"))


def test_unanchored_because_beside_anchors_is_warned_and_never_failed(project: AdopterRepo) -> None:
    """The stamp refuses the pair; a hand edit that writes it is warned about."""
    text = (project.root / ACTORS).read_text(encoding="utf-8")
    reason = "ACT-tester:\n  unanchored-because: No code embodies it.\n"
    project.write({ACTORS: text.replace("ACT-tester:\n", reason, 1)})
    document = check(project)
    ((location, message),) = _said(document, "warning")
    assert location == f"{ACTORS}#ACT-tester:/unanchored-because"
    assert "carries `unanchored-because` beside anchors" in message
    assert errors(document) == []
