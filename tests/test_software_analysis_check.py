"""software-analysis: the check of the analysis, in the check gate (#887).

`pkit analysis validate` — the `software-analysis:artefacts` member of `pkit
validate` — held to software-analysis DEC-001 points 1 to 6: what the stamp
writes passes it; it reports duplicate ids, missing or misshapen required
parts, a use case not anchored to its actor, a journey whose use-case anchors
do not match its steps, and revalidation records against their schema. It
reads the working tree alone: a number the default branch took first is
`pkit analysis check-numbers`' (`test_software_analysis_numbers.py`).
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from project_kit.cli import main
from project_kit.friction_check import BASE_ENV
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.analysis_repo import (
    ACTORS,
    CAPABILITY,
    GLOSSARY,
    JOURNEYS,
    MAIN,
    NEW,
    RECORDS,
    USE_CASES,
    VALIDATE,
    front,
    installed,
    run_script,
    seed,
    stamped,
)


@pytest.fixture
def project(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    return installed(make_adopter_repo, monkeypatch)


def check(repo: AdopterRepo) -> dict[str, Any]:
    """The validator's findings document, run as the backbone runs it: `--json` alone."""
    completed = run_script(repo, VALIDATE, "--json")
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def errors(document: Mapping[str, Any]) -> list[tuple[str, str]]:
    return [(f["location"], f["message"]) for f in document["findings"] if f["severity"] == "error"]


# --- in the check gate ----------------------------------------------------------------------


def test_the_validator_is_a_member_of_pkit_validate(project: AdopterRepo) -> None:
    seed(project)
    only = ["--color", "never", "validate", "--only", "software-analysis:artefacts"]
    result = CliRunner().invoke(main, only)
    assert result.exit_code == 0, result.output
    assert "software-analysis:artefacts" in result.output
    assert "1 actor(s), 0 term(s), 2 use case(s), 1 journey(s)" in result.output
    project.write({f"{USE_CASES}/UC-003-broken.md": "---\nid: UC-003\nstatus: active\n---\n"})
    result = CliRunner().invoke(main, only)
    assert result.exit_code == 1
    assert "'actor' is a required property" in result.output


@pytest.mark.parametrize("namespace", ["analysis", "software-analysis"])
def test_the_check_is_reached_under_the_capability_and_its_alias(
    project: AdopterRepo, namespace: str
) -> None:
    result = CliRunner().invoke(main, [namespace, "--help"])
    assert result.exit_code == 0, result.output
    assert "validate " in result.output


def test_what_the_stamp_writes_passes_the_check(project: AdopterRepo) -> None:
    seed(project)
    stamped(project, "use-case", "export", "--actor", "ACT-tester", "--area", "reports")
    stamped(project, "term", "sandbox", "--record", "ADR-001")
    stamped(project, "actor", "admin", "--name", "Administrator")
    document = check(project)
    assert document == {
        "summary": [
            "analysis at tech-docs/analysis: 2 actor(s), 1 term(s), 3 use case(s), "
            "1 journey(s); 0 revalidation record(s)."
        ],
        "findings": [],
    }


def test_the_validator_reads_the_working_tree_alone(
    project: AdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A validator answers about the tree (ADR-058 point 7): no base, no variable naming
    one and no fetch state changes its answer — even where the default branch has since
    taken a number this branch took, which `pkit analysis check-numbers` reports."""
    stamped(project, "actor", "tester")
    project.commit("an actor")
    project.checkout("topic", create=True)
    project.checkout(MAIN)
    stamped(project, "use-case", "theirs", "--actor", "ACT-tester")
    project.commit("UC-001 on main")
    project.checkout("topic")
    # Numbered against this branch alone: UC-001, the number main took since.
    ours = run_script(project, NEW, "use-case", "ours", "--actor", "ACT-tester", "--base", "topic")
    assert ours.stdout.splitlines()[-1] == f"stamped UC-001 at {USE_CASES}/UC-001-ours.md"
    answers = [check(project)]
    for base in (MAIN, "no-such-branch"):
        monkeypatch.setenv(BASE_ENV, base)
        answers.append(check(project))
    assert answers == [answers[0]] * 3
    assert answers[0]["findings"] == []
    completed = run_script(project, VALIDATE, "--json", "--base", MAIN)
    assert completed.returncode == 2
    assert "unrecognized arguments: --base main" in completed.stderr


# --- ids (DEC-001 point 3) --------------------------------------------------------------------


def test_a_shared_id_is_reported_at_every_later_holder(project: AdopterRepo) -> None:
    seed(project)
    text = (project.root / USE_CASES / "UC-002-read-report.md").read_text(encoding="utf-8")
    project.write({f"{USE_CASES}/area/UC-002-copy.md": text})
    assert errors(check(project)) == [
        (
            f"{USE_CASES}/area/UC-002-copy.md",
            f"the id UC-002 is also held by {USE_CASES}/UC-002-read-report.md: no two artefacts "
            "in the analysis share an id, and an id is never used again (DEC-001 point 3)",
        )
    ]


# --- required parts (DEC-001 points 1 and 3) --------------------------------------------------


@pytest.mark.parametrize(
    ("files", "expected"),
    [
        (
            {f"{USE_CASES}/UC-009-bare.md": "# No front matter\n"},
            [(f"{USE_CASES}/UC-009-bare.md", "has no front matter: every file here is a use case")],
        ),
        (
            {
                f"{USE_CASES}/UC-009-x.md": (
                    "---\nid: UC-9\nstatus: active\nactor: ACT-tester\n"
                    "pkit: {friction: {anchors: {artefact: [ACT-tester]}}}\n---\n"
                )
            },
            [(f"{USE_CASES}/UC-009-x.md:/id", "'UC-9' does not match '^UC-[0-9]{3,}$'")],
        ),
        (
            {
                f"{USE_CASES}/UC-009-x.md": (
                    "---\nid: UC-009\nstatus: done\nactor: ACT-tester\nowner: me\n"
                    "pkit: {friction: {anchors: {artefact: [ACT-tester]}}}\n---\n"
                )
            },
            [
                (
                    f"{USE_CASES}/UC-009-x.md",
                    "Additional properties are not allowed ('owner' was unexpected)",
                ),
                (
                    f"{USE_CASES}/UC-009-x.md:/status",
                    "'done' is not one of ['active', 'withdrawn']",
                ),
            ],
        ),
        (
            {GLOSSARY: "---\ntitle: Glossary\npkit: {friction: {}}\n---\n# Glossary\n"},
            [
                (
                    GLOSSARY,
                    "is not a collection of terms: each term is an entry of its front matter "
                    "keyed by its id, carrying the `pkit:` container",
                )
            ],
        ),
    ],
)
def test_missing_or_misshapen_parts_are_reported(
    project: AdopterRepo, files: Mapping[str, str], expected: list[tuple[str, str]]
) -> None:
    stamped(project, "actor", "tester")
    project.write(dict(files))
    assert errors(check(project)) == expected


def test_an_entry_missing_its_parts_or_keyed_by_a_foreign_id_is_reported(
    project: AdopterRepo,
) -> None:
    stamped(project, "actor", "tester")
    text = (project.root / ACTORS).read_text(encoding="utf-8")
    text = text.replace("ACT-tester:", "tester:").replace("  needs:\n", "  wants:\n")
    project.write({ACTORS: text})
    assert errors(check(project)) == [
        (
            f"{ACTORS}#tester",
            "the entry's key 'tester' is not an actor id, `ACT-<slug>` (DEC-001 point 3)",
        ),
        (f"{ACTORS}#tester", "'needs' is a required property"),
        (f"{ACTORS}#tester", "Additional properties are not allowed ('wants' was unexpected)"),
    ]


# --- anchors (DEC-001 point 4) ----------------------------------------------------------------


def test_a_use_case_not_anchored_to_its_actor_is_reported(project: AdopterRepo) -> None:
    seed(project)
    rel = f"{USE_CASES}/UC-002-read-report.md"
    text = (project.root / rel).read_text(encoding="utf-8")
    project.write({rel: text.replace("artefact:\n        - ACT-tester", "path:\n        - src/**")})
    assert front(project, rel)["pkit"]["friction"]["anchors"] == {"path": ["src/**"]}
    assert errors(check(project)) == [
        (
            f"{rel}:/pkit/friction/anchors/artefact",
            "a use case anchors to its actor, so a changed actor flags it: add ACT-tester to its "
            "artefact anchors (DEC-001 point 4)",
        )
    ]


def test_a_journey_whose_use_case_anchors_do_not_match_its_steps_is_reported(
    project: AdopterRepo,
) -> None:
    seed(project)
    stamped(project, "use-case", "third", "--actor", "ACT-tester")
    rel = f"{JOURNEYS}/JRN-001-first-run.md"
    text = (project.root / rel).read_text(encoding="utf-8")
    project.write({rel: text.replace("steps:\n  - UC-001\n", "steps:\n  - UC-003\n  - UC-001\n")})
    assert errors(check(project)) == [
        (
            f"{rel}:/pkit/friction/anchors/artefact",
            "its use-case anchors (UC-001, UC-002) do not match its steps (UC-003, UC-001, "
            "UC-002): the anchors are written from `steps`, so the friction check sees every "
            "use case it passes through — anchor exactly [UC-003, UC-001, UC-002] (DEC-001 "
            "point 4)",
        )
    ]
    # Order is the steps' business; a repeated step needs one anchor; other anchors are free.
    project.write(
        {
            rel: text.replace("steps:\n  - UC-001\n", "steps:\n  - UC-002\n  - UC-001\n").replace(
                "      artefact:\n", "      path:\n          - src/**\n      artefact:\n"
            )
        }
    )
    assert errors(check(project)) == []


# --- revalidation records (DEC-001 points 5 and 6) --------------------------------------------


def test_revalidation_records_are_held_to_their_schema(project: AdopterRepo) -> None:
    seed(project)
    record = (CAPABILITY / "templates" / "revalidation-record.md").read_text(encoding="utf-8")
    # From the template; a date written unquoted reads as the text it was written as.
    good = record.replace('"#000"', '"#887"').replace("UC-000", "UC-001")
    good = good.replace('date: "2026-01-01"', "date: 2026-10-01")
    bad = good.replace("trigger: planned", "trigger: whim").replace("UC-001: holds", "UC-1: ok")
    whim = f"{RECORDS}/2026-10-02-whim.md"
    project.write(
        {
            f"{RECORDS}/2026-10-01-first-run.md": good,
            whim: bad,
            f"{RECORDS}/2026-10-03-bare.md": "# No front matter\n",
            f"{RECORDS}/notes.txt": "not a record\n",
        }
    )
    document = check(project)
    assert "; 3 revalidation record(s)." in document["summary"][0]
    assert errors(document) == [
        (f"{whim}:/outcomes", "'UC-1' is not valid under any of the given schemas"),
        (
            f"{whim}:/outcomes/UC-1",
            "'ok' is not one of ['holds', 'analysis-stale', 'code-regressed', 'gap-found']",
        ),
        (
            f"{whim}:/trigger",
            "'whim' is not one of ['planned', 'drift', 'scheduled', 'close', 'onboarding']",
        ),
        (
            f"{RECORDS}/2026-10-03-bare.md",
            "has no front matter mapping: a revalidation record names the change, the trigger, "
            "the date, who performed it and each artefact's outcome (DEC-001 point 6)",
        ),
    ]
