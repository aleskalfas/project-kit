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
import os
import sys
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


#: A `pkit` answering `friction artefacts` as a backbone from before the document
#: carried `anchors`: the real answer, with the key taken out of every artefact.
_OLDER_PKIT = """#!{python}
import json, subprocess, sys
done = subprocess.run([sys.executable, "-m", "project_kit", *sys.argv[1:]],
                      capture_output=True, text=True)
out = done.stdout
if sys.argv[1:3] == ["friction", "artefacts"] and done.returncode == 0:
    document = json.loads(out)
    for artefact in document["artefacts"]:
        del artefact["anchors"]
    out = json.dumps(document)
sys.stdout.write(out)
sys.stderr.write(done.stderr)
sys.exit(done.returncode)
"""


def test_a_backbone_without_anchors_in_its_document_is_unreadable(
    project: AdopterRepo, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Read as none, missing anchors would report every use case as not anchored to its
    actor and every journey as not anchored to its steps; the check says what is missing."""
    seed(project)
    older = tmp_path / "older-backbone"
    older.mkdir()
    (older / "pkit").write_text(_OLDER_PKIT.format(python=sys.executable), encoding="utf-8")
    (older / "pkit").chmod(0o755)
    monkeypatch.setenv("PATH", f"{older}{os.pathsep}{os.environ['PATH']}")
    document = check(project)
    assert document["summary"] == ["the analysis could not be read; nothing checked."]
    ((location, message),) = errors(document)
    assert location == "."
    assert message.startswith("the places could not be read: `pkit friction artefacts` gave ")
    assert message.endswith(
        "without the `anchors` key this capability reads each artefact's anchors from: the "
        "installed backbone predates it — upgrade it (`pkit upgrade`)"
    )
    refused = run_script(project, NEW, "use-case", "more", "--actor", "ACT-tester")
    assert refused.returncode == 1
    assert "without the `anchors` key" in refused.stderr


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


def test_a_number_spelt_with_other_zeros_is_refused_and_shares_the_id(
    project: AdopterRepo,
) -> None:
    """`UC-0002` is no second id for `UC-002`: the schema admits one spelling per number,
    and the duplicate check counts the two as one id, as the stamp does."""
    seed(project)
    text = (project.root / USE_CASES / "UC-002-read-report.md").read_text(encoding="utf-8")
    alias = f"{USE_CASES}/UC-0002-alias.md"
    project.write({alias: text.replace("UC-002", "UC-0002")})
    assert errors(check(project)) == [
        (f"{alias}:/id", "'UC-0002' does not match '^UC-(?:[0-9]{3}|[1-9][0-9]{3,})$'"),
        (
            alias,
            f"the id UC-0002, UC-002 spelt otherwise, is also held by "
            f"{USE_CASES}/UC-002-read-report.md: no two artefacts in the analysis share an id, "
            "and an id is never used again (DEC-001 point 3)",
        ),
    ]


def test_a_file_whose_id_cannot_be_read_is_reported(project: AdopterRepo) -> None:
    """Front matter that does not parse, or none, or one naming no id: the stamp counts
    the number the file's name carries, and the check reports the file, never skipping
    it — an id is never used again, so the one it holds must be readable."""
    seed(project)
    broken = f"{USE_CASES}/UC-005-broken.md"
    bare = f"{USE_CASES}/UC-006-bare.md"
    no_id = f"{USE_CASES}/UC-007-no-id.md"
    glossary = "---\nTERM-x: [unclosed\n---\n"
    project.write(
        {
            broken: "---\nid: [unclosed\n---\n",
            bare: "# No front matter\n",
            no_id: (
                "---\ntitle: No id\nstatus: active\nactor: ACT-tester\n"
                "pkit: {friction: {anchors: {artefact: [ACT-tester]}}}\n---\n\n# No id\n"
            ),
            GLOSSARY: glossary,
        }
    )
    found = errors(check(project))
    assert found[0] == (bare, "has no front matter: every file here is a use case")
    assert [location for location, _message in found[1:3]] == [GLOSSARY, broken]
    assert ": the terms it holds cannot be read, ids included, " in found[1][1]
    assert found[2][1].startswith("its front matter does not parse (")
    assert found[2][1].endswith(
        ": what it holds cannot be read, ids included, and an id is never used again "
        "(DEC-001 point 3); the stamp counts UC-005, the number its name carries, as held — "
        "fix the front matter"
    )
    assert found[3:] == [
        (no_id, "'id' is a required property"),
        (
            no_id,
            "its name carries UC-007, its front matter no id: the stamp counts UC-007 as held, "
            "and an id is never used again — write `id: UC-007` (DEC-001 point 3)",
        ),
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
                    "---\nid: UC-9\ntitle: X\nstatus: active\nactor: ACT-tester\n"
                    "pkit: {friction: {anchors: {artefact: [ACT-tester]}}}\n---\n"
                )
            },
            [
                (
                    f"{USE_CASES}/UC-009-x.md:/id",
                    "'UC-9' does not match '^UC-(?:[0-9]{3}|[1-9][0-9]{3,})$'",
                )
            ],
        ),
        (
            {
                f"{USE_CASES}/UC-009-x.md": (
                    "---\nid: UC-009\nstatus: done\nactor: ACT-tester\nowner: me\n"
                    "pkit: {friction: {anchors: {artefact: [ACT-tester]}}}\n---\n"
                )
            },
            [
                (f"{USE_CASES}/UC-009-x.md", "'title' is a required property"),
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


def test_a_heading_other_than_the_id_and_title_is_reported(project: AdopterRepo) -> None:
    """The front matter's `title` is what a reader of the front matter alone sees — a data
    point publishing `{id, title, status}` — so the page's heading must say the same."""
    seed(project)
    rel = f"{USE_CASES}/UC-002-read-report.md"
    text = (project.root / rel).read_text(encoding="utf-8")
    assert "\n# UC-002 — Read report\n" in text
    renamed = text.replace("title: Read report", "title: Read the report")
    project.write({rel: renamed})
    wanted = (
        "a use case opens with `# UC-002 — Read the report`, so what a reader of its front "
        "matter sees is what the page shows — write the heading, or change `title`"
    )
    assert errors(check(project)) == [
        (
            rel,
            "its heading, `# UC-002 — Read report`, is not its id and its front matter's "
            f"title: {wanted}",
        )
    ]
    # A heading inside fenced code is no heading.
    fenced = renamed.replace("# UC-002 — Read report", "```\n# UC-002 — Read the report\n```")
    project.write({rel: fenced})
    assert errors(check(project)) == [(rel, f"has no heading: {wanted}")]
    # Closing hashes are no part of the heading's text.
    project.write({rel: renamed.replace("# UC-002 — Read report", "# UC-002 — Read the report #")})
    assert errors(check(project)) == []


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


# --- what an artefact names (DEC-001 points 1, 3 and 6) ---------------------------------------


def _set(repo: AdopterRepo, rel: str, old: str, new: str) -> None:
    text = (repo.root / rel).read_text(encoding="utf-8")
    assert old in text, (rel, old)
    repo.write({rel: text.replace(old, new, 1)})


JOURNEY = f"{JOURNEYS}/JRN-001-first-run.md"
READ_REPORT = f"{USE_CASES}/UC-002-read-report.md"


def test_a_journey_s_actor_is_an_actor_of_the_analysis(project: AdopterRepo) -> None:
    """A journey's actor is no anchor, so nothing else resolves it."""
    seed(project)
    _set(project, JOURNEY, "actor: ACT-tester", "actor: ACT-nobody")
    assert errors(check(project)) == [
        (
            f"{JOURNEY}:/actor",
            "no actor ACT-nobody in the analysis: what a journey names is in the analysis "
            "(DEC-001 point 3)",
        )
    ]


def test_an_artefact_in_force_names_nothing_withdrawn_as_the_stamp_refuses(
    project: AdopterRepo,
) -> None:
    seed(project)
    stamped(project, "actor", "retired")
    _set(
        project, ACTORS, "  name: Retired\n  status: active", "  name: Retired\n  status: withdrawn"
    )
    _set(project, READ_REPORT, "actor: ACT-tester", "actor: ACT-retired")
    _set(project, READ_REPORT, "- ACT-tester", "- ACT-retired")
    _set(project, f"{USE_CASES}/UC-001-run-suite.md", "status: active", "status: withdrawn")
    rule = (
        "rests only on artefacts in force, as the stamp requires — withdraw it too, or name another"
    )
    assert errors(check(project)) == [
        (
            f"{READ_REPORT}:/actor",
            f"actor ACT-retired is withdrawn ({ACTORS}#ACT-retired): a use case in force {rule} "
            "(DEC-001 point 3)",
        ),
        (
            f"{JOURNEY}:/steps/0",
            f"use case UC-001 is withdrawn ({USE_CASES}/UC-001-run-suite.md): a journey in force "
            f"{rule} (DEC-001 point 3)",
        ),
    ]
    # The stamp refuses the same, and a withdrawn artefact may name withdrawn ones: it is history.
    refused = run_script(project, NEW, "use-case", "later", "--actor", "ACT-retired")
    assert "actor ACT-retired is withdrawn" in refused.stderr
    _set(project, READ_REPORT, "status: active", "status: withdrawn")
    _set(project, JOURNEY, "status: active", "status: withdrawn")
    assert errors(check(project)) == []


def test_a_record_cites_artefacts_of_the_analysis_withdrawn_ones_included(
    project: AdopterRepo,
) -> None:
    seed(project)
    _set(project, JOURNEY, "status: active", "status: withdrawn")
    record = (CAPABILITY / "templates" / "revalidation-record.md").read_text(encoding="utf-8")
    cited = record.replace(
        "  UC-000: holds", "  UC-001: holds\n  JRN-001: analysis-stale\n  UC-009: gap-found"
    )
    rel = f"{RECORDS}/2026-10-01-first-run.md"
    project.write({rel: cited})
    assert errors(check(project)) == [
        (
            f"{rel}:/outcomes/UC-009",
            "no artefact UC-009 in the analysis: a record's outcomes cite artefacts of the "
            "analysis by id, withdrawn ones included (DEC-001 point 6)",
        )
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
