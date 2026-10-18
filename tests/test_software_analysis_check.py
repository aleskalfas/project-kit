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
import re
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
    ANALYSIS_SET,
    ANALYSIS_SET_TEXT,
    CAPABILITY,
    CONFIG,
    CONSTRAINTS,
    FUNCTIONAL,
    GLOSSARY,
    JOURNEYS,
    MAIN,
    NEW,
    QUALITY,
    RECORDS,
    USE_CASES,
    VALIDATE,
    accepting_san,
    actor_at,
    field_hint,
    fill,
    front,
    installed,
    load_lib,
    new,
    prepare_seeded,
    requirement,
    run_script,
    stamped,
)


@pytest.fixture
def project(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    return installed(make_adopter_repo, monkeypatch)


@pytest.fixture
def seeded(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    """The project with the seed stamped and filled (`prepare_seeded`)."""
    return installed(make_adopter_repo, monkeypatch, then=prepare_seeded)


def check(repo: AdopterRepo) -> dict[str, Any]:
    """The validator's findings document, run as the backbone runs it: `--json` alone."""
    completed = run_script(repo, VALIDATE, "--json")
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def errors(document: Mapping[str, Any]) -> list[tuple[str, str]]:
    return [(f["location"], f["message"]) for f in document["findings"] if f["severity"] == "error"]


def beside_record_bodies(found: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """`found` without what a record's body breaks of the record's structure, which the
    capability holds always (DEC-001 point 1): a test of a record's front matter edits
    the front matter alone, so its body no longer matches. A structure's finding cites the
    record point and repeats the part's hint, so any other finding citing the point stays."""
    return [
        (location, message)
        for location, message in found
        if not (location.startswith(RECORDS) and "(DEC-001 point 1). What goes there: " in message)
    ]


#: What the check says while no rule of `SAN` is accepted, of an analysis of `n`
#: artefacts: a report, at the analysis, since no rule of the method set binds on any of
#: them (DEC-001 point 1).
def unbound(n: int) -> dict[str, str]:
    """The warning that no rule of `SAN` binds on any of the analysis's `n` artefacts: its
    rules are accepted, and no set of these repositories' own inherits it."""
    return {
        "severity": "warning",
        "location": "tech-docs/analysis",
        "message": (
            f"no rule of software-analysis:SAN binds on any of the analysis's {n} artefact(s), "
            f"as `pkit rule-sets reach` reads it, so none is held to its structure: no set of "
            f"the project's own whose scope selects them inherits software-analysis:SAN, or a "
            f"pin behind its set holds it back (COR-051 point 7). Write a set of your own "
            f"whose scope selects the analysis, such as by the capability's types, and that "
            f"inherits software-analysis:SAN at its current major, or review the new major "
            f"and update the pin (DEC-001 point 1)"
        ),
    }


# --- in the check gate ----------------------------------------------------------------------


def test_the_validator_is_a_member_of_pkit_validate(seeded: AdopterRepo) -> None:
    only = ["--color", "never", "validate", "--only", "software-analysis:artefacts"]
    result = CliRunner().invoke(main, only)
    assert result.exit_code == 0, result.output
    assert "software-analysis:artefacts" in result.output
    assert (
        "1 actor(s), 0 term(s), 2 use case(s), 1 journey(s), 0 quality requirement(s), "
        "0 functional requirement(s), 0 constraint(s)" in result.output
    )
    seeded.write({f"{USE_CASES}/UC-003-broken.md": "---\nid: UC-003\nstatus: active\n---\n"})
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


#: What an actor's `needs` and a term's `definition` hold as the stamp writes them: each
#: field's hint, as the declaration gives it, with its example (#1593).
NEEDS_HINT = (
    "What the actor needs from the system, each in one sentence in their own voice. Start "
    "with the verb, or with *Never* and the verb, with *I* and *my* where they refer to "
    "themselves. Example: Export my report as a file."
)
DEFINITION_HINT = (
    "What the term means, in a phrase of the same part of speech that could replace it. "
    "Start with its broader kind, with no article, then say what sets it apart. End with no "
    "full stop, and never repeat the term. Example: layout an administrator publishes, from "
    "which an analyst builds a report"
)


def _field_hint_left(said: str) -> str:
    return (
        "still holds its hint: write in its place what it asks for, and delete the hint "
        f"(DEC-001 point 1). The hint: {said}"
    )


def test_what_the_stamp_writes_passes_the_check_once_its_placeholders_are_filled(
    seeded: AdopterRepo,
) -> None:
    """What only a person can write the stamp leaves as its hint: each front-matter field
    it does not write itself (#1593), and each body part (#1366). The check fails each
    until it is written — in an own field, a body or a section — whatever the format rule's
    status, each hint found by its mark, the message repeating it."""
    stamped(seeded, "use-case", "export", "--actor", "ACT-tester", "--area", "reports")
    stamped(seeded, "term", "sandbox", "--record", "ADR-001")
    stamped(seeded, "actor", "admin", "--name", "Administrator")

    def hinted(rel: str, where: str, more: int) -> str:
        lines = (seeded.root / rel).read_text(encoding="utf-8").splitlines()
        body = lines.index("---", 1) + 1  # past the front matter, whose fields hold hints too
        line = next(n for n, text in enumerate(lines, 1) if n > body and "<!-- pkit:hint " in text)
        found = re.search(r"<!-- pkit:hint (.*) -->", lines[line - 1])
        assert found is not None
        return (
            f"{where} still holds a hint at line {line}, and {more} more below it: write in "
            f"its place what it asks for, and delete the hint (DEC-001 point 1). The hint: "
            f"{found[1]}"
        )

    export = f"{USE_CASES}/reports/UC-003-export.md"
    assert errors(check(seeded)) == [
        (f"{GLOSSARY}#TERM-sandbox:/definition", _field_hint_left(DEFINITION_HINT)),
        (f"{GLOSSARY}#TERM-sandbox", hinted(GLOSSARY, "its section", 1)),
        (f"{actor_at('ACT-admin')}:/needs/0", _field_hint_left(NEEDS_HINT)),
        (actor_at("ACT-admin"), hinted(actor_at("ACT-admin"), "its body", 2)),
        (export, hinted(export, "its body", 8)),
    ]
    # The first hint each message repeats is the first part's.
    assert dict(errors(check(seeded)))[export].endswith(
        "The hint: What the actor wants from this use case, in one sentence in their own "
        "voice. Start with the verb, or with *Never* and the verb, with *I* and *my* where "
        "they refer to themselves. Example: Export my report as a file."
    )
    # A placeholder quoted as code, not the template's, is no placeholder in a body.
    rel = f"{USE_CASES}/reports/UC-003-export.md"
    fill(seeded)
    body = (seeded.root / rel).read_text(encoding="utf-8")
    seeded.write({rel: body + '\nRun `pkit analysis new use-case <slug> --gap "<a gap>"`.\n'})
    document = check(seeded)
    assert document == {
        "summary": [
            "analysis at tech-docs/analysis: 2 actor(s), 1 term(s), 3 use case(s), "
            "1 journey(s), 0 quality requirement(s), 0 functional requirement(s), "
            "0 constraint(s); 0 revalidation record(s).",
            # The format rule is accepted, yet no set of this repository's own inherits
            # `SAN`, so no body is held to its kind's structure: the check says so, as a
            # warning.
            "structure (RS-SAN-001, accepted): 0 artefact(s) and file head(s) checked, where "
            "the rule binds, against the structure their kind declares in "
            ".pkit/capabilities/software-analysis/schemas/artefact-kinds.yaml; 0 of them "
            "departing from it. No rule of software-analysis:SAN binds on 7 of the 7 "
            "artefact(s).",
        ],
        "findings": [unbound(7)],
    }


def test_a_field_placeholder_a_template_once_shipped_is_still_caught(
    seeded: AdopterRepo,
) -> None:
    """An actor or a term stamped before each field held its hint holds the template's
    `<…>` text there: it stays caught while unfilled, since the list of placeholders is
    append-only (#1593)."""
    stamped(seeded, "term", "sandbox", "--record", "ADR-001")
    fill(seeded)
    tester = actor_at("ACT-tester")
    needs = "<what this actor needs from the system, in one sentence>"
    meaning = "<what the term means, in one sentence>"
    _set(seeded, tester, "  - 'Export my report as a file.'", f"  - {needs}")
    _set(
        seeded,
        GLOSSARY,
        "  definition: 'layout an administrator publishes, from which an analyst builds a report'",
        f"  definition: {meaning}",
    )
    rule = "write in its place what it asks for — until then it says nothing of the"
    assert errors(check(seeded)) == [
        (
            f"{GLOSSARY}#TERM-sandbox:/definition",
            f"still holds the placeholder {meaning!r}: {rule} term (DEC-001 point 1)",
        ),
        (
            f"{tester}:/needs/0",
            f"still holds the placeholder {needs!r}: {rule} actor (DEC-001 point 1)",
        ),
    ]


def test_a_field_s_hint_is_never_judged_against_its_form(seeded: AdopterRepo) -> None:
    """A field still holding its hint is the placeholder check's alone: previewed as
    accepted, the format rule reports no form of it (#1593)."""
    stamped(seeded, "actor", "admin", "--name", "Administrator")
    completed = run_script(seeded, VALIDATE, "--json", "--preview")
    document = json.loads(completed.stdout)
    at_needs = [
        f["message"]
        for f in document["findings"]
        if f["location"] == f"{actor_at('ACT-admin')}:/needs/0"
    ]
    assert at_needs == [_field_hint_left(NEEDS_HINT)]


def test_a_hint_left_in_is_refused_with_no_rule_needed(seeded: AdopterRepo) -> None:
    """A hint left in a body is an error where the format rule binds on nothing, as any
    placeholder is (DEC-001 point 1): here no set of the project's own inherits `SAN`.
    Its mark is matched outside code spans and fenced code, so a body may quote it
    (#1366)."""
    rel = f"{USE_CASES}/UC-001-run-suite.md"
    quoted = (seeded.root / rel).read_text(encoding="utf-8") + (
        "\nThe stamp writes `<!-- pkit:hint … -->` where a part goes.\n\n"
        "```markdown\n**Goal:** <!-- pkit:hint fenced -->\n```\n"
    )
    seeded.write({rel: quoted})
    document = check(seeded)
    assert errors(document) == []
    assert document["summary"][1].startswith(
        "structure (RS-SAN-001, accepted): 0 artefact(s) and file head(s) checked"
    )
    left = quoted.replace("**Trigger:** ", "**Trigger:** <!-- pkit:hint The event. --> ", 1)
    seeded.write({rel: left})
    line = left.splitlines().index(next(t for t in left.splitlines() if "The event." in t)) + 1
    assert errors(check(seeded)) == [
        (
            rel,
            f"its body still holds a hint at line {line}: write in its place what it asks for, "
            "and delete the hint (DEC-001 point 1). The hint: The event.",
        )
    ]


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
    seeded: AdopterRepo, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Read as none, missing anchors would report every use case as not anchored to its
    actor and every journey as not anchored to its steps; the check says what is missing."""
    older = tmp_path / "older-backbone"
    older.mkdir()
    (older / "pkit").write_text(_OLDER_PKIT.format(python=sys.executable), encoding="utf-8")
    (older / "pkit").chmod(0o755)
    monkeypatch.setenv("PATH", f"{older}{os.pathsep}{os.environ['PATH']}")
    document = check(seeded)
    assert document["summary"] == ["the analysis could not be read; nothing checked."]
    ((location, message),) = errors(document)
    assert location == "."
    assert message.startswith("the places could not be read: `pkit friction artefacts` gave ")
    assert message.endswith(
        "without the `anchors` key this capability reads each artefact's anchors from: the "
        "installed backbone predates it — upgrade it (`pkit upgrade`)"
    )
    refused = run_script(seeded, NEW, "use-case", "more", "--actor", "ACT-tester")
    assert refused.returncode == 1
    assert "without the `anchors` key" in refused.stderr


def test_a_placeholder_is_a_text_the_templates_shipped_never_a_shape(
    seeded: AdopterRepo,
) -> None:
    """The placeholders a shape would take for code — capitalised, with no space — are
    caught, since they are texts the templates shipped; words of the artefact's own in
    angle brackets are not, whatever their shape."""
    stamped(seeded, "term", "session", "--name", "Session")
    fill(seeded)
    _set(
        seeded,
        GLOSSARY,
        "  definition: 'layout an administrator publishes, from which an analyst builds a report'",
        "  definition: Maps <user id> to a session.",
    )
    tester = actor_at("ACT-tester")
    _set(seeded, tester, "name: Tester", "name: <Display name>")
    _set(seeded, tester, "# ACT-tester — Tester", "# ACT-tester — <Display name>")
    run_suite = f"{USE_CASES}/UC-001-run-suite.md"
    _set(seeded, run_suite, "title: Run suite", "title: <Title>")
    _set(seeded, run_suite, "# UC-001 — Run suite", "# UC-001 — <Title>")
    rule = "write in its place what it asks for — until then it says nothing of the"
    assert errors(check(seeded)) == [
        (
            f"{tester}:/name",
            f"still holds the placeholder '<Display name>': {rule} actor (DEC-001 point 1)",
        ),
        (
            tester,
            "its body still holds the template's placeholder '<Display name>': write in each "
            "one's place what it asks for, or remove it (DEC-001 point 1)",
        ),
        (
            f"{run_suite}:/title",
            f"still holds the placeholder '<Title>': {rule} use case (DEC-001 point 1)",
        ),
        (
            run_suite,
            "its body still holds the template's placeholder '<Title>': write in each one's "
            "place what it asks for, or remove it (DEC-001 point 1)",
        ),
    ]
    # The stamp reads what it is given the same way.
    reason = ("--unanchored-because", "The <user id> service stands for it; no code of ours.")
    assert stamped(seeded, "actor", "gateway", *reason) == "ACT-gateway"


def test_the_validator_reads_the_working_tree_alone(
    project: AdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A validator answers about the tree (ADR-058 point 7): no base, no variable naming
    one and no fetch state changes its answer — even where the default branch has since
    taken a number this branch took, which `pkit analysis check-numbers` reports."""
    stamped(project, "actor", "tester")
    project.commit("an actor")
    project.checkout("topic", create=True)
    # Numbered on each line of work before either landed: UC-001 twice, the number
    # main took after this branch left it.
    assert stamped(project, "use-case", "ours", "--actor", "ACT-tester") == "UC-001"
    project.commit("UC-001 on topic")
    project.checkout(MAIN)
    assert stamped(project, "use-case", "theirs", "--actor", "ACT-tester") == "UC-001"
    project.commit("UC-001 on main")
    project.checkout("topic")
    fill(project)
    answers = [check(project)]
    for base in (MAIN, "no-such-branch"):
        monkeypatch.setenv(BASE_ENV, base)
        answers.append(check(project))
    assert answers == [answers[0]] * 3
    assert answers[0]["findings"] == [unbound(2)]
    completed = run_script(project, VALIDATE, "--json", "--base", MAIN)
    assert completed.returncode == 2
    assert "unrecognized arguments: --base main" in completed.stderr


# --- ids (DEC-001 point 3) --------------------------------------------------------------------


def test_a_shared_id_is_reported_at_every_later_holder(seeded: AdopterRepo) -> None:
    text = (seeded.root / USE_CASES / "UC-002-read-report.md").read_text(encoding="utf-8")
    seeded.write({f"{USE_CASES}/area/UC-002-copy.md": text})
    assert errors(check(seeded)) == [
        (
            f"{USE_CASES}/area/UC-002-copy.md",
            f"the id UC-002 is also held by {USE_CASES}/UC-002-read-report.md: no two artefacts "
            "in the analysis share an id, and an id is never used again (DEC-001 point 3)",
        )
    ]


def test_a_number_spelt_with_other_zeros_is_refused_and_shares_the_id(
    seeded: AdopterRepo,
) -> None:
    """`UC-0002` is no second id for `UC-002`: the schema admits one spelling per number,
    and the duplicate check counts the two as one id, as the stamp does."""
    text = (seeded.root / USE_CASES / "UC-002-read-report.md").read_text(encoding="utf-8")
    alias = f"{USE_CASES}/UC-0002-alias.md"
    seeded.write({alias: text.replace("UC-002", "UC-0002")})
    assert errors(check(seeded)) == [
        (f"{alias}:/id", "'UC-0002' does not match '^UC-(?:[0-9]{3}|[1-9][0-9]{3,})$'"),
        (
            alias,
            f"the id UC-0002, UC-002 spelt otherwise, is also held by "
            f"{USE_CASES}/UC-002-read-report.md: no two artefacts in the analysis share an id, "
            "and an id is never used again (DEC-001 point 3)",
        ),
    ]


def test_a_name_carrying_another_number_than_the_id_is_reported(seeded: AdopterRepo) -> None:
    """`UC-009-<slug>.md` holding `id: UC-008` holds both numbers for the stamp, which
    counts the name's too: one artefact, one id, so the two must agree. The same number
    spelt with other zeros agrees; the id's own check reports the spelling."""
    text = (seeded.root / USE_CASES / "UC-002-read-report.md").read_text(encoding="utf-8")
    renamed = f"{USE_CASES}/UC-009-renamed.md"
    seeded.write({renamed: text.replace("UC-002", "UC-008")})
    assert errors(check(seeded)) == [
        (
            renamed,
            "its name carries UC-009, its front matter UC-008: the stamp counts both as held, "
            "and an artefact holds one id — name the file after its id, or correct `id` "
            "(DEC-001 point 3)",
        )
    ]


def test_a_file_whose_id_cannot_be_read_is_reported(seeded: AdopterRepo) -> None:
    """Front matter that does not parse, or none, or one naming no id: the stamp counts
    the number the file's name carries, and the check reports the file, never skipping
    it — an id is never used again, so the one it holds must be readable."""
    broken = f"{USE_CASES}/UC-005-broken.md"
    bare = f"{USE_CASES}/UC-006-bare.md"
    no_id = f"{USE_CASES}/UC-007-no-id.md"
    glossary = "---\nTERM-x: [unclosed\n---\n"
    seeded.write(
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
    found = errors(check(seeded))
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
        # An actor is a file of its own (#1346): a file of the actors' folder holding
        # keyed entries, as the actors' collection file once did, is no actor.
        (
            {
                f"{ACTORS}/all.md": (
                    "---\nACT-admin:\n  name: Admin\n  status: active\n  needs: [Run it]\n"
                    "  pkit: {friction: {}}\n---\n\n# Actors\n\n## ACT-admin — Admin\n"
                )
            },
            [(f"{ACTORS}/all.md", "holds keyed entries: each actor is a document of its own")],
        ),
        (
            {actor_at("ACT-bare"): "# ACT-bare — Bare\n"},
            [(actor_at("ACT-bare"), "has no front matter: every file here is an actor")],
        ),
    ],
)
def test_missing_or_misshapen_parts_are_reported(
    project: AdopterRepo, files: Mapping[str, str], expected: list[tuple[str, str]]
) -> None:
    stamped(project, "actor", "tester")
    fill(project)
    project.write(dict(files))
    assert errors(check(project)) == expected


def test_a_heading_other_than_the_id_and_title_is_reported(seeded: AdopterRepo) -> None:
    """The front matter's `title` is what a reader of the front matter alone sees — a data
    point publishing `{id, title, status}` — so the page's heading must say the same."""
    rel = f"{USE_CASES}/UC-002-read-report.md"
    text = (seeded.root / rel).read_text(encoding="utf-8")
    assert "\n# UC-002 — Read report\n" in text
    renamed = text.replace("title: Read report", "title: Read the report")
    seeded.write({rel: renamed})
    wanted = (
        "a use case opens with `# UC-002 — Read the report`, so what a reader of its front "
        "matter sees is what the page shows — write the heading, or change `title`"
    )
    assert errors(check(seeded)) == [
        (
            rel,
            "its heading, `# UC-002 — Read report`, is not its id and its front matter's "
            f"title: {wanted}",
        )
    ]
    # A heading inside fenced code is no heading.
    fenced = renamed.replace("# UC-002 — Read report", "```\n# UC-002 — Read the report\n```")
    seeded.write({rel: fenced})
    assert errors(check(seeded)) == [(rel, f"has no heading: {wanted}")]
    # Closing hashes are no part of the heading's text.
    seeded.write({rel: renamed.replace("# UC-002 — Read report", "# UC-002 — Read the report #")})
    assert errors(check(seeded)) == []


def test_an_actor_s_heading_is_its_id_and_name(seeded: AdopterRepo) -> None:
    """An actor is checked as a use case is (#1346): its heading is its id and the `name`
    its front matter gives, so what a reader of the front matter sees is what the page
    shows."""
    tester = actor_at("ACT-tester")
    text = (seeded.root / tester).read_text(encoding="utf-8")
    assert "\n# ACT-tester — Tester\n" in text
    seeded.write({tester: text.replace("name: Tester", "name: Test author")})
    wanted = (
        "an actor opens with `# ACT-tester — Test author`, so what a reader of its front "
        "matter sees is what the page shows — write the heading, or change `name`"
    )
    assert errors(check(seeded)) == [
        (
            tester,
            "its heading, `# ACT-tester — Tester`, is not its id and its front matter's name: "
            + wanted,
        )
    ]
    seeded.write({tester: text.replace("# ACT-tester — Tester\n", "")})
    assert errors(check(seeded)) == [
        (
            tester,
            "has no heading: an actor opens with `# ACT-tester — Tester`, so what a reader of "
            "its front matter sees is what the page shows — write the heading, or change `name`",
        )
    ]


def test_an_actor_without_its_id_or_with_a_foreign_one_is_reported(seeded: AdopterRepo) -> None:
    """The actor's schema has an `id` (#1346): an actor file with none is reported, and so
    is one whose id is no actor id. Neither is an actor the analysis holds, so a use case
    naming it names no actor."""
    tester = actor_at("ACT-tester")
    text = (seeded.root / tester).read_text(encoding="utf-8")
    seeded.write({tester: text.replace("id: ACT-tester\n", "")})
    found = errors(check(seeded))
    assert found[0] == (tester, "'id' is a required property")
    unnamed = (
        f"{USE_CASES}/UC-001-run-suite.md:/actor",
        "no actor ACT-tester in the analysis: what a use case names is in the analysis "
        "(DEC-001 point 3)",
    )
    assert unnamed in found
    seeded.write({tester: text.replace("id: ACT-tester", "id: tester")})
    found = errors(check(seeded))
    assert found[0] == (f"{tester}:/id", "'tester' does not match '^ACT-[a-z][a-z0-9-]*$'")


def test_an_actor_whose_file_s_name_is_not_its_id_is_reported(seeded: AdopterRepo) -> None:
    """An actor's id names its file (DEC-001 point 3), as the stamp names it: a file named
    otherwise is reported, a file in a folder of the actors' place included, and one named
    after its id passes wherever it lies."""
    tester = actor_at("ACT-tester")
    text = (seeded.root / tester).read_text(encoding="utf-8")
    other = text.replace("id: ACT-tester", "id: ACT-other").replace(
        "# ACT-tester — Tester", "# ACT-other — Tester"
    )
    seeded.write({tester: other, f"{ACTORS}/people/ACT-tester.md": text})
    assert errors(check(seeded)) == [
        (
            actor_at("ACT-tester"),
            "its name is ACT-tester.md, its front matter's id ACT-other: an actor's id names "
            "its file — name the file ACT-other.md, or correct `id` (DEC-001 point 3)",
        )
    ]


def test_an_entry_missing_its_parts_or_keyed_by_a_foreign_id_is_reported(
    project: AdopterRepo,
) -> None:
    stamped(project, "term", "suite")
    fill(project)
    text = (project.root / GLOSSARY).read_text(encoding="utf-8")
    text = text.replace("TERM-suite:", "suite:").replace("  definition:", "  meaning:")
    project.write({GLOSSARY: text})
    assert errors(check(project)) == [
        (
            f"{GLOSSARY}#suite",
            "the entry's key 'suite' is not a term id, `TERM-<slug>` (DEC-001 point 3)",
        ),
        (f"{GLOSSARY}#suite", "'definition' is a required property"),
        (f"{GLOSSARY}#suite", "Additional properties are not allowed ('meaning' was unexpected)"),
    ]


# --- what an artefact names (DEC-001 points 1, 3 and 6) ---------------------------------------


def _set(repo: AdopterRepo, rel: str, old: str, new: str) -> None:
    text = (repo.root / rel).read_text(encoding="utf-8")
    assert old in text, (rel, old)
    repo.write({rel: text.replace(old, new, 1)})


JOURNEY = f"{JOURNEYS}/JRN-001-first-run.md"
READ_REPORT = f"{USE_CASES}/UC-002-read-report.md"


def test_a_journey_s_actor_is_an_actor_of_the_analysis(seeded: AdopterRepo) -> None:
    """A journey's actor is in the analysis, as the stamp requires. Its anchor to the actor
    follows it, and a dead anchor is the core's to report, not this check's."""
    _set(seeded, JOURNEY, "actor: ACT-tester", "actor: ACT-nobody")
    _set(seeded, JOURNEY, "- ACT-tester", "- ACT-nobody")
    assert errors(check(seeded)) == [
        (
            f"{JOURNEY}:/actor",
            "no actor ACT-nobody in the analysis: what a journey names is in the analysis "
            "(DEC-001 point 3)",
        )
    ]


def test_an_artefact_in_force_names_nothing_withdrawn_as_the_stamp_refuses(
    seeded: AdopterRepo,
) -> None:
    stamped(seeded, "actor", "retired")
    fill(seeded)
    _set(seeded, actor_at("ACT-retired"), "status: active", "status: withdrawn")
    _set(seeded, READ_REPORT, "actor: ACT-tester", "actor: ACT-retired")
    _set(seeded, READ_REPORT, "- ACT-tester", "- ACT-retired")
    _set(seeded, f"{USE_CASES}/UC-001-run-suite.md", "status: active", "status: withdrawn")
    rule = (
        "rests only on artefacts in force, as the stamp requires — withdraw it too, or name another"
    )
    assert errors(check(seeded)) == [
        (
            f"{READ_REPORT}:/actor",
            f"actor ACT-retired is withdrawn ({actor_at('ACT-retired')}): a use case in force "
            f"{rule} (DEC-001 point 3)",
        ),
        (
            f"{JOURNEY}:/steps/0",
            f"use case UC-001 is withdrawn ({USE_CASES}/UC-001-run-suite.md): a journey in force "
            f"{rule} (DEC-001 point 3)",
        ),
        # UC-002 is ACT-retired's now, so the journey through it is no longer one actor's.
        (
            f"{JOURNEY}:/steps/1",
            "step 2, UC-002, is a use case of ACT-retired, and the journey is ACT-tester's: a "
            "journey is one actor's path across use cases, so each step is a use case of the "
            "journey's actor — name one of ACT-tester's in its place, or correct the use "
            "case's actor (DEC-001 point 1)",
        ),
    ]
    # The stamp refuses the same, and a withdrawn artefact may name withdrawn ones: it is history.
    refused = run_script(seeded, NEW, "use-case", "later", "--actor", "ACT-retired")
    assert "actor ACT-retired is withdrawn" in refused.stderr
    _set(seeded, READ_REPORT, "status: active", "status: withdrawn")
    _set(seeded, JOURNEY, "status: active", "status: withdrawn")
    assert errors(check(seeded)) == []


def test_each_step_of_a_journey_is_a_use_case_of_the_journey_s_actor(
    seeded: AdopterRepo,
) -> None:
    """A journey is one actor's path across use cases (DEC-001 point 1, #1584): the check
    fails a journey in force with a step of another actor, naming the step and both
    actors, and the stamp refuses the same journey, writing nothing."""
    stamped(seeded, "actor", "operator")
    assert stamped(seeded, "use-case", "restart", "--actor", "ACT-operator") == "UC-003"
    fill(seeded)
    # A journey of one actor passes.
    assert errors(check(seeded)) == []
    rule = (
        "is a use case of ACT-operator, and the journey is ACT-tester's: a journey is one "
        "actor's path across use cases, so each step is a use case of the journey's actor — "
        "name one of ACT-tester's in its place"
    )
    fixed = ", or correct the use case's actor (DEC-001 point 1)"
    before = sorted(p.relative_to(seeded.root) for p in (seeded.root / JOURNEYS).rglob("*"))
    steps = ("--step", "UC-001", "--step", "UC-003", "--step", "UC-002")
    refused = new(seeded, "journey", "mixed", "--actor", "ACT-tester", *steps)
    assert refused.returncode == 1
    assert f"step 2, UC-003, {rule}" in refused.stderr
    assert sorted(p.relative_to(seeded.root) for p in (seeded.root / JOURNEYS).rglob("*")) == before
    # The check fails the same journey written by hand, on the step.
    _set(seeded, JOURNEY, "  - UC-002\n", "  - UC-002\n  - UC-003\n")
    _set(seeded, JOURNEY, "        - UC-002\n", "        - UC-002\n        - UC-003\n")
    assert errors(check(seeded)) == [
        (f"{JOURNEY}:/steps/2", f"step 3, UC-003, {rule}{fixed}"),
    ]
    # A withdrawn journey is history: its steps' actors may have changed since.
    _set(seeded, JOURNEY, "status: active", "status: withdrawn")
    assert errors(check(seeded)) == []
    # A step naming no use case is the reference check's alone.
    _set(seeded, JOURNEY, "status: withdrawn", "status: active")
    _set(seeded, JOURNEY, "  - UC-003\n", "  - UC-009\n")
    _set(seeded, JOURNEY, "        - UC-003\n", "        - UC-009\n")
    assert errors(check(seeded)) == [
        (
            f"{JOURNEY}:/steps/2",
            "no use case UC-009 in the analysis: what a journey names is in the analysis "
            "(DEC-001 point 3)",
        ),
    ]


def test_a_record_cites_artefacts_of_the_analysis_withdrawn_ones_included(
    seeded: AdopterRepo,
) -> None:
    _set(seeded, JOURNEY, "status: active", "status: withdrawn")
    cited = _record_text().replace(
        "  UC-001: gap-found", "  UC-001: holds\n  JRN-001: analysis-stale\n  UC-009: gap-found"
    )
    rel = f"{RECORDS}/2026-10-01-first-run.md"
    seeded.write({rel: cited})
    assert beside_record_bodies(errors(check(seeded))) == [
        (
            f"{rel}:/outcomes/UC-009",
            "no artefact UC-009 in the analysis: a record's outcomes cite artefacts of the "
            "analysis by id, withdrawn ones included (DEC-001 point 6)",
        )
    ]


# --- the three kinds of requirement (software-analysis DEC-002, #1691) -------------------------

#: Each kind of requirement: its place, its name beside its id, and its last part,
#: *Rationale* or, on a constraint, *Imposed by* (DEC-002 points 2 to 4).
REQUIREMENT_KINDS = {
    "quality-requirement": (QUALITY, "Quality", "Rationale"),
    "functional-requirement": (FUNCTIONAL, "Functional", "Rationale"),
    "constraint": (CONSTRAINTS, "Constraint", "Imposed by"),
}

#: A set of the project's own created before the requirement kinds: its scope selects
#: the four kinds DEC-001 gives, and none of DEC-002's.
EARLIER_SET_TEXT = ANALYSIS_SET_TEXT.replace(
    ", software-analysis:quality-requirement, software-analysis:functional-requirement, "
    "software-analysis:constraint",
    "",
)


def _requirement(shown: str, last: str, **fields: str | None) -> str:
    """A requirement filled as its kind's structure asks, its front matter's `fields`
    changed, and one set to `None` left out."""
    front: dict[str, str | None] = {
        "id": "REQ-004",
        "title": "Show a run's result quickly",
        "status": "active",
        "statement": "The system shows a suite's result within two seconds of the run's end.",
        "measure": "None.",
        "applies-to": "Every run of a suite.",
        **fields,
    }
    written = "".join(f"{k}: {json.dumps(v)}\n" for k, v in front.items() if v is not None)
    return (
        f"---\n{written}pkit:\n  friction:\n    anchors:\n      path: [src/run.py]\n---\n\n"
        f"# REQ-004 · {shown} · Show a run's result quickly\n\n"
        f"**Verified by:** A timing test runs the suite and measures when its result shows.\n\n"
        f"**{last}:** None.\n"
    )


@pytest.mark.parametrize("kind", sorted(REQUIREMENT_KINDS))
def test_a_requirement_is_held_to_its_kind_s_schema_and_where_the_rule_binds_its_structure(
    project: AdopterRepo, pkit_on_path: Path, kind: str
) -> None:
    """A file in each new place is held by the check's existing passes (#1691): to its
    kind's companion schema always, and to its kind's structure where RS-SAN-001 binds,
    through a set of the project's own whose scope selects its type. A set created before
    the kinds selects none of them, so it holds no requirement to its structure."""
    place, shown, last = REQUIREMENT_KINDS[kind]
    rel = f"{place}/REQ-004-quick-result.md"
    project.write({**accepting_san(project), rel: _requirement(shown, last)})
    document = check(project)
    assert errors(document) == []
    noun = kind.replace("-", " ")
    assert f", 1 {noun}(s)" in document["summary"][0]
    assert document["summary"][1].startswith(
        "structure (RS-SAN-001, accepted): 1 artefact(s) and file head(s) checked"
    )
    # Its schema, whatever the rule binds: an id that is no `REQ-NNN`, and no measure.
    project.write({rel: _requirement(shown, last, id="REQ-4", measure=None)})
    assert sorted(errors(check(project))) == [
        (rel, "'measure' is a required property"),
        (f"{rel}:/id", "'REQ-4' does not match '^REQ-(?:[0-9]{3}|[1-9][0-9]{3,})$'"),
    ]
    # Its structure, where the rule binds: its last part missing, a statement of two
    # sentences, and where it holds reading `None.`.
    broken = _requirement(
        shown, last, statement="It shows the result. It does so fast.", **{"applies-to": "None."}
    ).replace(f"\n\n**{last}:** None.", "")
    project.write({rel: broken})
    found = errors(check(project))
    assert [location for location, _message in found] == [
        rel,
        f"{rel}:/statement",
        f"{rel}:/applies-to",
    ]
    missing = f"`**{last}:**` is missing, and it comes after `**Verified by:**`"
    assert found[0][1].startswith(missing)
    assert found[1][1].startswith("'It shows the result. It does so fast.' is more than one")
    assert found[2][1].startswith(
        f"a {noun}'s `applies-to` reads `None.`, which only a field that allows it may"
    )
    assert all("(RS-SAN-001)" in message for _location, message in found)
    # A set created before the kinds selects no requirement: the rule binds on none.
    project.write({ANALYSIS_SET: EARLIER_SET_TEXT})
    document = check(project)
    assert errors(document) == []
    assert document["summary"][1].endswith(
        "No rule of software-analysis:SAN binds on 1 of the 1 artefact(s)."
    )


def test_a_record_cites_a_requirement_and_copies_its_evidence(
    project: AdopterRepo, pkit_on_path: Path
) -> None:
    """A record's outcomes cite a requirement by its id, and an evidence entry copied for
    one names no steps (DEC-002, Implications). An id the analysis does not hold is
    refused, as any artefact's is."""
    place, shown, last = REQUIREMENT_KINDS["constraint"]
    record = (CAPABILITY / "templates" / "revalidation-record.md").read_text(encoding="utf-8")
    record = record.replace("UC-007: gap-found", "REQ-004: gap-found\n  REQ-009: holds")
    record = record.replace("UC-007", "REQ-004")
    entry = (
        "evidence:\n  - id: REQ-004@0000000000000000000000000000000000000000#project.check\n"
        "    artefact: REQ-004\n    commit: '0000000000000000000000000000000000000000'\n"
        "    check: project.check\n    result: passed\n    ran: a review of the stores\n---"
    )
    record = record.replace("\n---\n", f"\n{entry}\n", 1)  # the closing fence, after it
    rel = f"{RECORDS}/2026-10-18-country.md"
    project.write({f"{place}/REQ-004-country.md": _requirement(shown, last), rel: record})
    assert beside_record_bodies(errors(check(project))) == [
        (
            f"{rel}:/outcomes/REQ-009",
            "no artefact REQ-009 in the analysis: a record's outcomes cite artefacts of the "
            "analysis by id, withdrawn ones included (DEC-001 point 6)",
        )
    ]


#: Where a quality requirement lies when its file is named after its id, and a constraint
#: it refines (#1693).
QUICK = f"{QUALITY}/REQ-004-quick-result.md"
LOCAL = f"{CONSTRAINTS}/REQ-001-local-runs.md"
_LOCAL_TITLE = "Run suites on the client's machines"


def test_a_requirement_s_id_file_name_and_heading_agree(
    project: AdopterRepo, pkit_on_path: Path
) -> None:
    """A requirement's id is `REQ-NNN`, its file's name carries it, and its heading shows
    its id, its kind and its title (DEC-002 point 2, #1693). The heading is the heading
    check's whatever the format rule binds, so the structure never reports it twice."""
    project.write({**accepting_san(project), QUICK: requirement()})
    assert errors(check(project)) == []
    title = "Show a run's result quickly"
    wanted = f"`# REQ-004 · Quality · {title}`"
    why = (
        "so its heading shows its kind beside its id, as its place does (DEC-002 point 2) — "
        "write the heading, change `title`, or move the file to its kind's folder"
    )
    # A heading written as a use case's, with no kind.
    project.write({QUICK: requirement(heading=f"# REQ-004 — {title}")})
    assert errors(check(project)) == [
        (
            QUICK,
            f"its heading, `# REQ-004 — {title}`, is not its id, its kind and its front "
            f"matter's title: a quality requirement opens with {wanted}, {why}",
        )
    ]
    # No heading at all: one finding, the heading check's.
    project.write({QUICK: requirement(heading="")})
    assert errors(check(project)) == [
        (QUICK, f"has no heading: a quality requirement opens with {wanted}, {why}")
    ]
    # The file moved to another kind's place, its heading still naming the first kind.
    moved = f"{CONSTRAINTS}/REQ-004-quick-result.md"
    project.write(
        {QUICK: None, moved: requirement("constraint", heading=f"# REQ-004 · Quality · {title}")}
    )
    assert errors(check(project)) == [
        (
            moved,
            f"its heading, `# REQ-004 · Quality · {title}`, is not its id, its kind and its "
            f"front matter's title: a constraint opens with `# REQ-004 · Constraint · "
            f"{title}`, {why}",
        )
    ]
    # A file's name that carries no number, or another than its id.
    unnumbered = f"{QUALITY}/quick-result.md"
    project.write({moved: None, unnumbered: requirement()})
    assert errors(check(project)) == [
        (
            unnumbered,
            "its name is quick-result.md, which carries no number: a requirement's file is "
            "named after its id, `REQ-NNN-<slug>.md`, so its path shows its kind beside its "
            "id, and the stamp counts the number it carries — name the file REQ-004-<slug>.md "
            "(DEC-002 point 2)",
        )
    ]
    other = f"{QUALITY}/REQ-005-quick-result.md"
    project.write({unnumbered: None, other: requirement()})
    assert errors(check(project)) == [
        (
            other,
            "its name carries REQ-005, its front matter REQ-004: the stamp counts both as "
            "held, and an artefact holds one id — name the file after its id, or correct `id` "
            "(DEC-001 point 3)",
        )
    ]


def test_no_two_requirements_share_an_id_across_the_three_kinds(
    project: AdopterRepo, pkit_on_path: Path
) -> None:
    """One numbering across the three kinds (DEC-002 point 2): an id two requirements of
    different kinds hold is one id twice, and so is one spelt with other zeros, which
    the id check refuses too (#1691's advisory, #1693)."""
    second = f"{CONSTRAINTS}/REQ-004-local-runs.md"
    project.write({QUICK: requirement(), second: requirement("constraint", title=_LOCAL_TITLE)})
    assert errors(check(project)) == [
        (
            second,
            f"the id REQ-004 is also held by {QUICK}: no two artefacts in the analysis share "
            f"an id, and an id is never used again (DEC-001 point 3)",
        )
    ]
    spelt = f"{FUNCTIONAL}/REQ-0004-who-started.md"
    project.write({second: None, spelt: requirement("functional-requirement", req_id="REQ-0004")})
    assert errors(check(project)) == [
        (f"{spelt}:/id", "'REQ-0004' does not match '^REQ-(?:[0-9]{3}|[1-9][0-9]{3,})$'"),
        (
            spelt,
            f"the id REQ-0004, REQ-004 spelt otherwise, is also held by {QUICK}: no two "
            f"artefacts in the analysis share an id, and an id is never used again (DEC-001 "
            f"point 3)",
        ),
    ]


def test_what_a_requirement_names_is_in_the_analysis_and_in_force(seeded: AdopterRepo) -> None:
    """Each of a requirement's `actors` is an actor of the analysis, and each of its
    `refines` a requirement of any kind, never itself. One in force names none withdrawn,
    and a withdrawn one may: it is history (DEC-002 points 6 and 7, #1693)."""
    local = requirement("constraint", req_id="REQ-001", title=_LOCAL_TITLE)
    names: dict[str, Any] = {"actors": ["ACT-tester"], "refines": ["REQ-001"]}
    seeded.write({LOCAL: local, QUICK: requirement(anchored=["ACT-tester", "REQ-001"], **names)})
    assert errors(check(seeded)) == []
    # An actor and a requirement the analysis does not hold, and the requirement itself.
    unheld: dict[str, Any] = {"actors": ["ACT-nobody"], "refines": ["REQ-009", "REQ-004"]}
    seeded.write({QUICK: requirement(anchored=["ACT-nobody", "REQ-009"], **unheld)})
    named = "what a requirement names is in the analysis (DEC-002 point 6)"
    assert errors(check(seeded)) == [
        (f"{QUICK}:/actors/0", f"no actor ACT-nobody in the analysis: {named}"),
        (f"{QUICK}:/refines/0", f"no requirement REQ-009 in the analysis: {named}"),
        (
            f"{QUICK}:/refines/1",
            "`refines` names REQ-004, the requirement itself: a requirement refines others, "
            "never itself — remove it from `refines` (DEC-002 point 6)",
        ),
    ]
    # A use case is no requirement, though the analysis holds it: the schema refuses it,
    # and the anchor on it is none a requirement may hold.
    seeded.write({QUICK: requirement(anchored=["UC-001"], refines=["UC-001"])})
    assert [location for location, _message in errors(check(seeded))] == [
        f"{QUICK}:/refines/0",
        f"{QUICK}:/pkit/friction/anchors/artefact",
    ]
    # Withdrawn, an actor and the requirement it refines, while it is in force.
    stamped(seeded, "actor", "former", "--name", "Former", "--path", "src/**")
    fill(seeded)
    former = actor_at("ACT-former")
    _set(seeded, former, "status: active", "status: withdrawn")
    moved_on: dict[str, Any] = {"actors": ["ACT-former"], "refines": ["REQ-001"]}
    on: dict[str, Any] = {"anchored": ["ACT-former", "REQ-001"], **moved_on}
    seeded.write(
        {
            LOCAL: requirement(
                "constraint", req_id="REQ-001", title=_LOCAL_TITLE, status="withdrawn"
            ),
            QUICK: requirement(**on),
        }
    )
    rests = (
        "a requirement in force rests only on artefacts in force — withdraw it too, or name another"
    )
    assert errors(check(seeded)) == [
        (
            f"{QUICK}:/actors/0",
            f"actor ACT-former is withdrawn ({former}): {rests} (DEC-001 point 3)",
        ),
        (
            f"{QUICK}:/refines/0",
            f"requirement REQ-001 is withdrawn ({LOCAL}): {rests} (DEC-002 point 7)",
        ),
    ]
    seeded.write({QUICK: requirement(status="withdrawn", **on)})
    assert errors(check(seeded)) == []


def test_a_requirement_s_anchors_within_the_analysis_match_its_fields(
    seeded: AdopterRepo,
) -> None:
    """Within the analysis, a requirement anchors each of its `actors` and each of its
    `refines`, and nothing else (DEC-002 point 6, #1693). An artefact anchor outside the
    analysis, such as a rule, is not counted."""
    local = requirement("constraint", req_id="REQ-001", title=_LOCAL_TITLE)
    names: dict[str, Any] = {"actors": ["ACT-tester"], "refines": ["REQ-001"]}
    seeded.write({LOCAL: local, QUICK: requirement(anchored=["ACT-tester"], **names)})
    rule = (
        "within the analysis, a requirement anchors only each actor whose need it meets and "
        "each requirement it refines, written from the two fields, so a changed actor or "
        "requirement flags it"
    )
    where = f"{QUICK}:/pkit/friction/anchors/artefact"
    assert errors(check(seeded)) == [
        (
            where,
            f"its anchors within the analysis (ACT-tester) do not match its `actors` and "
            f"`refines` (ACT-tester, REQ-001): {rule} — anchor exactly [ACT-tester, REQ-001] "
            f"(DEC-002 point 6)",
        )
    ]
    # A use case anchored, which neither field names.
    seeded.write({QUICK: requirement(anchored=["UC-001", "RS-SAN-001"])})
    assert errors(check(seeded)) == [
        (
            where,
            f"its anchors within the analysis (UC-001) do not match its `actors` and "
            f"`refines` (none): {rule} — anchor none of them (DEC-002 point 6)",
        )
    ]
    # A part anchor names its artefact before its last `#` (COR-050 point 2): one on a use
    # case is within the analysis, and one on an actor is no anchor on the actor whole.
    seeded.write({QUICK: requirement(anchored=["UC-001#"])})
    assert errors(check(seeded)) == [
        (
            where,
            f"its anchors within the analysis (UC-001#) do not match its `actors` and "
            f"`refines` (none): {rule} — anchor none of them (DEC-002 point 6)",
        )
    ]
    seeded.write({QUICK: requirement(anchored=["ACT-tester#"], actors=["ACT-tester"])})
    assert errors(check(seeded)) == [
        (
            where,
            f"its anchors within the analysis (ACT-tester#) do not match its `actors` and "
            f"`refines` (ACT-tester): {rule} — anchor exactly [ACT-tester] (DEC-002 point 6)",
        )
    ]
    seeded.write({QUICK: requirement(anchored=["RS-SAN-001"])})
    assert errors(check(seeded)) == []


def test_a_hint_left_in_a_requirement_s_field_is_refused(project: AdopterRepo) -> None:
    """A requirement's statement, measure and where it holds still holding the hint its
    template writes are refused, as any hint left in is (DEC-001 point 1, #1693)."""
    hints: dict[str, Any] = {
        name: field_hint("quality-requirement", name)
        for name in ("statement", "measure", "applies-to")
    }
    project.write({QUICK: requirement(**hints)})
    said = {name: re.search(r"<!-- pkit:hint (.*) -->", hint) for name, hint in hints.items()}
    assert sorted(errors(check(project))) == [
        (f"{QUICK}:/{name}", _field_hint_left(found[1]))
        for name, found in sorted(said.items())
        if found is not None
    ]
    assert all(found is not None for found in said.values())


#: What the check says of a file under `requirements/` outside the three kinds' folders:
#: that folder is no place, so the file is in none (DEC-002 point 3, #1724).
OUTSIDE_KINDS = (
    "lies under `requirements/` outside the three kinds' folders, and `requirements/` is no "
    "place, so it is a requirement of no kind: the check holds it to none and the stamp counts "
    "no number it holds. A requirement lies in the folder of its kind, "
    "`requirements/quality/`, `requirements/functional/` or `requirements/constraints/` "
    "(DEC-002 point 3) — move it there, or leave it out with `friction.exclude`"
)


def test_a_file_under_requirements_outside_the_three_kinds_folders_is_refused(
    project: AdopterRepo, pkit_on_path: Path
) -> None:
    """`requirements/` holds the three kinds' folders and is no place itself, so a file in
    it outside them is no requirement of any kind (DEC-002 point 3, #1724). The check reads
    such files from the backbone's one listing (`unplaced` in `pkit friction artefacts`),
    and leaves out one `friction.exclude` leaves out. A file elsewhere in the analysis
    location is no concern of this report."""
    requirements = QUALITY.rsplit("/", 1)[0]
    loose = f"{requirements}/REQ-007-loose.md"
    draft = f"{requirements}/drafts/REQ-008-draft.md"
    project.write(
        {
            QUICK: requirement(),
            loose: requirement(req_id="REQ-007"),
            draft: "# A draft\n",
            f"{requirements}/README.md": "# Requirements\n",
            "tech-docs/analysis/notes.md": "# Notes\n",
            CONFIG: (
                f"docs:\n  internal: tech-docs\nfriction:\n  exclude: [{requirements}/README.md]\n"
            ),
        }
    )
    assert errors(check(project)) == [(loose, OUTSIDE_KINDS), (draft, OUTSIDE_KINDS)]
    # Moved into its kind's folder, it is a requirement like any other.
    moved = f"{FUNCTIONAL}/REQ-007-loose.md"
    project.write(
        {loose: None, draft: None, moved: requirement("functional-requirement", req_id="REQ-007")}
    )
    assert errors(check(project)) == []


@pytest.mark.parametrize(
    ("unplaced", "read"),
    [
        (None, None),  # a backbone that predates the key
        ({}, None),  # no entry for the analysis location
        ({"software-analysis": {"analysis": {"files": []}}}, None),  # no path given
        ({"software-analysis": {"analysis": {"path": "a"}}}, None),  # no list of files
        (
            {
                "software-analysis": {
                    "analysis": {
                        "path": "x/../a/",
                        "files": [{"path": "a/requirements/REQ-001-a.md", "excluded": False}],
                    }
                }
            },
            ("a/requirements/REQ-001-a.md",),
        ),
        (
            {
                "software-analysis": {
                    "analysis": {
                        "path": ".",
                        "files": [
                            {"path": "requirements/REQ-001-a.md", "excluded": False},
                            {"path": "requirements/old/REQ-002-b.md", "excluded": True},
                            {"path": "requirementsx/REQ-003-c.md", "excluded": False},
                            {"path": "notes.md", "excluded": False},
                        ],
                    }
                }
            },
            ("requirements/REQ-001-a.md",),
        ),
    ],
)
def test_the_files_outside_the_kinds_are_read_from_the_location_s_unplaced_files(
    unplaced: dict[str, Any] | None, read: tuple[str, ...] | None
) -> None:
    """The model keeps the location's files under `requirements/` that are not excluded,
    the location's path read in its normal form, and says it has no answer when the
    backbone's reading gives none for the location (#1724)."""
    (model,) = load_lib("model")
    document: dict[str, Any] = {"schema_version": 1}
    if unplaced is not None:
        document["unplaced"] = unplaced
    assert model.analysis_of(document).outside_kinds == read


#: A `pkit` answering `friction artefacts` as a backbone from before the document carried
#: `unplaced`: the real answer, with the key taken out.
_PKIT_WITHOUT_UNPLACED = """#!{python}
import json, subprocess, sys
done = subprocess.run([sys.executable, "-m", "project_kit", *sys.argv[1:]],
                      capture_output=True, text=True)
out = done.stdout
if sys.argv[1:3] == ["friction", "artefacts"] and done.returncode == 0:
    document = json.loads(out)
    del document["unplaced"]
    out = json.dumps(document)
sys.stdout.write(out)
sys.stderr.write(done.stderr)
sys.exit(done.returncode)
"""


def test_a_backbone_that_gives_no_unplaced_files_makes_the_check_say_it_did_not_look(
    project: AdopterRepo, pkit_on_path: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without the backbone's list, nothing says whether `requirements/` holds a file
    outside the three kinds' folders, so the check says it could not look, and never
    reads the silence as no such file (#1724)."""
    older = tmp_path / "older-backbone"
    older.mkdir()
    (older / "pkit").write_text(_PKIT_WITHOUT_UNPLACED.format(python=sys.executable))
    (older / "pkit").chmod(0o755)
    monkeypatch.setenv("PATH", f"{older}{os.pathsep}{os.environ['PATH']}")
    project.write({QUICK: requirement()})
    assert errors(check(project)) == [
        (
            "tech-docs/analysis",
            "no file under `requirements/` outside the three kinds' folders is looked for: "
            "`pkit friction artefacts --json` gives no `unplaced` list of the analysis "
            "location's files, which an installed backbone that predates it lacks — upgrade it "
            "(`pkit upgrade`)",
        )
    ]


# --- anchors (DEC-001 point 4) ----------------------------------------------------------------


def test_a_use_case_not_anchored_to_its_actor_is_reported(seeded: AdopterRepo) -> None:
    rel = f"{USE_CASES}/UC-002-read-report.md"
    text = (seeded.root / rel).read_text(encoding="utf-8")
    seeded.write({rel: text.replace("artefact:\n        - ACT-tester", "path:\n        - src/**")})
    assert front(seeded, rel)["pkit"]["friction"]["anchors"] == {"path": ["src/**"]}
    assert errors(check(seeded)) == [
        (
            f"{rel}:/pkit/friction/anchors/artefact",
            "a use case anchors to its actor, so a changed actor flags it: add ACT-tester to its "
            "artefact anchors (DEC-001 point 4)",
        )
    ]


def test_a_journey_whose_use_case_anchors_do_not_match_its_steps_is_reported(
    seeded: AdopterRepo,
) -> None:
    stamped(seeded, "use-case", "third", "--actor", "ACT-tester")
    fill(seeded)
    rel = f"{JOURNEYS}/JRN-001-first-run.md"
    text = (seeded.root / rel).read_text(encoding="utf-8")
    seeded.write({rel: text.replace("steps:\n  - UC-001\n", "steps:\n  - UC-003\n  - UC-001\n")})
    assert errors(check(seeded)) == [
        (
            f"{rel}:/pkit/friction/anchors/artefact",
            "its use-case anchors (UC-001, UC-002) do not match its steps and the use cases "
            "it relies on (UC-003, UC-001, UC-002): the anchors are written from `steps` and "
            "`relies-on`, so the friction check sees every use case it passes through or "
            "relies on — anchor exactly [UC-003, UC-001, UC-002] (DEC-001 point 4)",
        )
    ]
    # Order is the steps' business; a repeated step needs one anchor; other anchors are free.
    seeded.write(
        {
            rel: text.replace("steps:\n  - UC-001\n", "steps:\n  - UC-002\n  - UC-001\n").replace(
                "      artefact:\n", "      path:\n          - src/**\n      artefact:\n"
            )
        }
    )
    assert errors(check(seeded)) == []


def test_a_journey_s_part_anchor_on_a_use_case_is_an_anchor_on_that_use_case(
    seeded: AdopterRepo,
) -> None:
    """A part anchor names the artefact before its last `#` (COR-050 point 2), so one on a
    use case is among the journey's use-case anchors (#1725). It matches no entry of
    `steps` or `relies-on`, which name each use case whole: a part anchor flags the
    journey only when its part changes (COR-050 point 5). A part anchor on an artefact
    that is no use case is not among them."""
    stamped(seeded, "use-case", "third", "--actor", "ACT-tester")
    fill(seeded)
    where = f"{JOURNEY}:/pkit/friction/anchors/artefact"

    def mismatch(anchored: str) -> list[tuple[str, str]]:
        return [
            (
                where,
                f"its use-case anchors ({anchored}) do not match its steps and the use cases "
                f"it relies on (UC-001, UC-002): the anchors are written from `steps` and "
                f"`relies-on`, so the friction check sees every use case it passes through or "
                f"relies on — anchor exactly [UC-001, UC-002] (DEC-001 point 4)",
            )
        ]

    # A match: a part anchor on the journey's actor is no use-case anchor.
    _set(seeded, JOURNEY, "        - UC-002\n", "        - UC-002\n        - ACT-tester#\n")
    assert errors(check(seeded)) == []
    # A part anchor on a use case outside the lists, which slipped past before: a
    # section, then the lead.
    _set(seeded, JOURNEY, "        - ACT-tester#\n", "        - UC-003#main-flow\n")
    assert errors(check(seeded)) == mismatch("UC-001, UC-002, UC-003#main-flow")
    _set(seeded, JOURNEY, "        - UC-003#main-flow\n", "        - UC-003#\n")
    assert errors(check(seeded)) == mismatch("UC-001, UC-002, UC-003#")
    # A part anchor on a step's use case, in place of its whole anchor or beside it.
    _set(seeded, JOURNEY, "        - UC-003#\n", "")
    _set(seeded, JOURNEY, "        - UC-001\n", "        - UC-001#\n")
    assert errors(check(seeded)) == mismatch("UC-001#, UC-002")
    _set(seeded, JOURNEY, "        - UC-001#\n", "        - UC-001\n        - UC-001#\n")
    assert errors(check(seeded)) == mismatch("UC-001, UC-001#, UC-002")


def test_a_use_case_with_another_actor_names_it_and_anchors_to_it(seeded: AdopterRepo) -> None:
    """A use case lists each other actor it involves in `other-actors`, and anchors to each,
    so a changed actor flags every use case it takes part in (DEC-001 point 4). The stamp
    writes both. The check resolves each to an actor, refuses the use case's own actor,
    and requires each anchor."""
    stamped(seeded, "actor", "auditor")
    stamped(seeded, "use-case", "audit", "--actor", "ACT-tester", "--other-actor", "ACT-auditor")
    fill(seeded)
    rel = f"{USE_CASES}/UC-003-audit.md"
    written = front(seeded, rel)
    assert written["other-actors"] == ["ACT-auditor"]
    assert written["pkit"]["friction"]["anchors"]["artefact"] == ["ACT-tester", "ACT-auditor"]
    assert errors(check(seeded)) == []
    # The anchor dropped: a changed auditor would not flag the use case.
    _set(seeded, rel, "        - ACT-auditor\n", "")
    assert errors(check(seeded)) == [
        (
            f"{rel}:/pkit/friction/anchors/artefact",
            "a use case anchors to each other actor it involves, so a changed actor flags it: "
            "add ACT-auditor to its artefact anchors (DEC-001 point 4)",
        )
    ]
    # An actor that is not in the analysis, and the use case's own actor, are refused.
    _set(seeded, rel, "  - ACT-auditor\n", "  - ACT-nobody\n  - ACT-tester\n")
    _set(seeded, rel, "        - ACT-tester\n", "        - ACT-tester\n        - ACT-nobody\n")
    assert errors(check(seeded)) == [
        (
            f"{rel}:/other-actors/0",
            "no actor ACT-nobody in the analysis: what a use case names is in the analysis "
            "(DEC-001 point 3)",
        ),
        (
            f"{rel}:/other-actors/1",
            "`other-actors` names ACT-tester, the use case's own actor: the other actors are "
            "those who take part beside the actor whose goal it is — remove it from "
            "`other-actors` (DEC-001 point 4)",
        ),
    ]
    # The stamp refuses the same.
    own = new(seeded, "use-case", "own", "--actor", "ACT-tester", "--other-actor", "ACT-tester")
    assert own.returncode == 1 and "is the use case's own actor" in own.stderr
    nobody = new(seeded, "use-case", "x", "--actor", "ACT-tester", "--other-actor", "ACT-nobody")
    assert nobody.returncode == 1 and "no actor ACT-nobody in the analysis" in nobody.stderr


def test_a_journey_relying_on_a_use_case_outside_it_anchors_to_it(seeded: AdopterRepo) -> None:
    """A journey lists in `relies-on` each use case outside it that a step relies on, and its
    use-case anchors are written from `steps` and `relies-on` together, so a changed use
    case flags the journeys that rely on it (DEC-001 point 4). Each has a hand-over under
    the step that needs it, which the form of *Steps* holds once the format rule binds."""
    stamped(seeded, "actor", "admin")
    stamped(seeded, "use-case", "set-up", "--actor", "ACT-admin")
    stamped(
        seeded,
        "journey",
        "audited-run",
        "--actor",
        "ACT-tester",
        "--step",
        "UC-001",
        "--step",
        "UC-002",
        "--relies-on",
        "UC-003",
    )
    fill(seeded)
    rel = f"{JOURNEYS}/JRN-002-audited-run.md"
    written = front(seeded, rel)
    assert written["relies-on"] == ["UC-003"]
    assert written["pkit"]["friction"]["anchors"]["artefact"] == [
        "ACT-tester",
        "UC-001",
        "UC-002",
        "UC-003",
    ]
    assert errors(check(seeded)) == []
    # A drifted anchor: the use case relied on is missing from the anchors.
    _set(seeded, rel, "        - UC-003\n", "")
    assert errors(check(seeded)) == [
        (
            f"{rel}:/pkit/friction/anchors/artefact",
            "its use-case anchors (UC-001, UC-002) do not match its steps and the use cases it "
            "relies on (UC-001, UC-002, UC-003): the anchors are written from `steps` and "
            "`relies-on`, so the friction check sees every use case it passes through or "
            "relies on — anchor exactly [UC-001, UC-002, UC-003] (DEC-001 point 4)",
        )
    ]
    # A step is no use case outside the journey, and the journey anchors to its actor.
    _set(seeded, rel, "relies-on:\n  - UC-003\n", "relies-on:\n  - UC-001\n")
    _set(seeded, rel, "        - ACT-tester\n", "")
    assert errors(check(seeded)) == [
        (
            f"{rel}:/relies-on/0",
            "`relies-on` names UC-001, a step of the journey: it lists the use cases outside "
            "the journey that a step relies on — remove it from `relies-on` (DEC-001 point 4)",
        ),
        (
            f"{rel}:/pkit/friction/anchors/artefact",
            "a journey anchors to its actor, so a changed actor flags it: add ACT-tester to its "
            "artefact anchors (DEC-001 point 4)",
        ),
    ]
    # The stamp refuses a step relied on outside the journey, and a use case not there.
    steps = ("--actor", "ACT-tester", "--step", "UC-001", "--step", "UC-002")
    inside = new(seeded, "journey", "inside", *steps, "--relies-on", "UC-002")
    assert inside.returncode == 1 and "is a step of the journey" in inside.stderr
    missing = new(seeded, "journey", "missing", *steps, "--relies-on", "UC-009")
    assert missing.returncode == 1 and "no use case UC-009 in the analysis" in missing.stderr


def test_what_a_use_case_or_journey_names_beside_its_actor_is_in_force(
    seeded: AdopterRepo,
) -> None:
    """A use case's other actors, and the use cases a journey relies on outside it, are in
    force for one in force, as its actor and its steps are (DEC-001 points 3 and 4). The
    stamp refuses a withdrawn one, and a withdrawn artefact may name withdrawn ones."""
    stamped(seeded, "actor", "auditor")
    stamped(seeded, "use-case", "set-up", "--actor", "ACT-auditor")
    stamped(seeded, "use-case", "audit", "--actor", "ACT-tester", "--other-actor", "ACT-auditor")
    steps = ("--actor", "ACT-tester", "--step", "UC-001", "--step", "UC-002")
    stamped(seeded, "journey", "audited-run", *steps, "--relies-on", "UC-003")
    fill(seeded)
    assert errors(check(seeded)) == []
    set_up, audit = f"{USE_CASES}/UC-003-set-up.md", f"{USE_CASES}/UC-004-audit.md"
    audited_run = f"{JOURNEYS}/JRN-002-audited-run.md"
    _set(seeded, actor_at("ACT-auditor"), "status: active", "status: withdrawn")
    _set(seeded, set_up, "status: active", "status: withdrawn")
    rule = (
        "rests only on artefacts in force, as the stamp requires — withdraw it too, or name another"
    )
    assert errors(check(seeded)) == [
        (
            f"{audit}:/other-actors/0",
            f"actor ACT-auditor is withdrawn ({actor_at('ACT-auditor')}): a use case in force "
            f"{rule} (DEC-001 point 3)",
        ),
        (
            f"{audited_run}:/relies-on/0",
            f"use case UC-003 is withdrawn ({set_up}): a journey in force {rule} (DEC-001 point 3)",
        ),
    ]
    # The stamp refuses the same.
    other = new(
        seeded, "use-case", "later", "--actor", "ACT-tester", "--other-actor", "ACT-auditor"
    )
    assert other.returncode == 1 and "actor ACT-auditor is withdrawn" in other.stderr
    relied = new(seeded, "journey", "later", *steps, "--relies-on", "UC-003")
    assert relied.returncode == 1 and "use case UC-003 is withdrawn" in relied.stderr
    # A withdrawn artefact may name withdrawn ones: it is history.
    _set(seeded, audit, "status: active", "status: withdrawn")
    _set(seeded, audited_run, "status: active", "status: withdrawn")
    assert errors(check(seeded)) == []


def test_a_journey_stamped_without_its_actor_anchor_fails_until_it_is_added(
    seeded: AdopterRepo,
) -> None:
    """A journey stamped before its actor anchor was written (#1507) has no `relies-on` and
    no anchor to its actor. The check fails it, a withdrawn one too, as it fails a use case
    without its actor's anchor, and adding the actor to its artefact anchors clears it."""
    _set(seeded, JOURNEY, "relies-on: []\n", "")
    _set(seeded, JOURNEY, "        - ACT-tester\n", "")
    finding = (
        f"{JOURNEY}:/pkit/friction/anchors/artefact",
        "a journey anchors to its actor, so a changed actor flags it: add ACT-tester to its "
        "artefact anchors (DEC-001 point 4)",
    )
    assert errors(check(seeded)) == [finding]
    _set(seeded, JOURNEY, "status: active", "status: withdrawn")
    assert errors(check(seeded)) == [finding]
    _set(seeded, JOURNEY, "        - UC-001\n", "        - ACT-tester\n        - UC-001\n")
    assert errors(check(seeded)) == []


# --- revalidation records (DEC-001 points 5 and 6) --------------------------------------------

#: The template's `reviewed-against`, which a planned record carries, up to the next field.
_SOURCES = re.compile(r"^reviewed-against:.*?\n(?=date:)", re.MULTILINE | re.DOTALL)


def _record_text() -> str:
    """The record template, a planned record that shows each part's example (#1366), citing
    the seeded analysis's first use case in place of the example's."""
    record = (CAPABILITY / "templates" / "revalidation-record.md").read_text(encoding="utf-8")
    return record.replace("UC-007", "UC-001")


def test_revalidation_records_are_held_to_their_schema(seeded: AdopterRepo) -> None:
    # From the template; a date written unquoted reads as the text it was written as.
    good = _record_text().replace('date: "2026-01-05"', "date: 2026-10-01")
    bad = _SOURCES.sub("", good)  # only a planned record names its sources
    bad = bad.replace("trigger: planned", "trigger: whim").replace("UC-001: gap-found", "UC-1: ok")
    whim = f"{RECORDS}/2026-10-02-whim.md"
    seeded.write(
        {
            f"{RECORDS}/2026-10-01-first-run.md": good,
            whim: bad,
            f"{RECORDS}/2026-10-03-bare.md": "# No front matter\n",
            f"{RECORDS}/notes.txt": "not a record\n",
        }
    )
    document = check(seeded)
    assert "; 3 revalidation record(s)." in document["summary"][0]
    assert beside_record_bodies(errors(document)) == [
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


def test_a_planned_record_is_checked_for_the_sources_it_names(seeded: AdopterRepo) -> None:
    """Validation applies the record's schema whatever the format rule's status, so it
    checks `reviewed-against` (DEC-001 point 6, #1363): required on a planned record,
    left out of a record of another trigger, and each source's version of the form its
    place gives — here, an abbreviated commit is refused."""
    good = _record_text()
    short = 'reviewed-against:\n  - title: the redesign note\n    version: "4c1d2e9"\n'
    seeded.write(
        {
            f"{RECORDS}/2026-10-01-planned.md": good,
            f"{RECORDS}/2026-10-02-unnamed.md": _SOURCES.sub("", good),
            f"{RECORDS}/2026-10-03-drift.md": good.replace("trigger: planned", "trigger: drift"),
            f"{RECORDS}/2026-10-04-short.md": _SOURCES.sub(short, good),
        }
    )
    found = dict(errors(check(seeded)))
    assert sorted(found) == [
        f"{RECORDS}/2026-10-02-unnamed.md",
        f"{RECORDS}/2026-10-03-drift.md:/reviewed-against",
        f"{RECORDS}/2026-10-04-short.md:/reviewed-against/0/version",
    ]
    assert found[f"{RECORDS}/2026-10-02-unnamed.md"] == "'reviewed-against' is a required property"
    assert found[f"{RECORDS}/2026-10-03-drift.md:/reviewed-against"].endswith(
        "should not be valid under {}"
    )
    assert found[f"{RECORDS}/2026-10-04-short.md:/reviewed-against/0/version"] == (
        "'4c1d2e9' is not valid under any of the given schemas"
    )


def test_a_time_written_unquoted_is_told_to_be_quoted(seeded: AdopterRepo) -> None:
    """YAML reads an unquoted time as a time, not as the text written, and gives it back
    with `+00:00` for its `Z`, which the schema's form refuses: the message says why,
    and that quoting it fixes it, rather than repeating the value it no longer has."""
    good = _record_text()
    unquoted = good.replace('version: "2026-01-05T10:00:00Z"', "version: 2026-01-05T10:00:00Z")
    assert unquoted != good
    # A field that holds no time is told only to quote it, in the form the field takes.
    dated = good.replace('date: "2026-01-05"', "date: 2026-01-05T10:00:00Z")
    assert dated != good
    seeded.write(
        {f"{RECORDS}/2026-10-01-planned.md": unquoted, f"{RECORDS}/2026-10-02-dated.md": dated}
    )
    assert errors(check(seeded)) == [
        (
            f"{RECORDS}/2026-10-01-planned.md:/reviewed-against/0/version",
            "YAML reads this value as a time, since it is not quoted, and gives it back as "
            "'2026-01-05T10:00:00+00:00', not as written: quote it, a time in UTC such as "
            '"2026-01-05T10:00:00Z", as a revalidation\'s `at` is written '
            "(`schemas/revalidation-record.schema.json`)",
        ),
        (
            f"{RECORDS}/2026-10-02-dated.md:/date",
            "YAML reads this value as a time, since it is not quoted, and gives it back as "
            "'2026-01-05T10:00:00+00:00', not as written: quote it, in the form the field "
            "takes (`schemas/revalidation-record.schema.json`)",
        ),
    ]


def test_the_records_are_the_held_files_so_a_draft_git_ignores_is_not_checked(
    seeded: AdopterRepo,
) -> None:
    """The records are the files the held folder holds in `pkit friction artefacts`
    (COR-050 point 1), read from the working tree's one listing: a draft the project
    keeps git-ignored in the folder is not a record, whatever it holds."""
    good = _record_text()
    seeded.write(
        {
            ".gitignore": "draft-*.md\n",
            f"{RECORDS}/2026-10-01-first-run.md": good,
            f"{RECORDS}/draft-idea.md": "# Not yet a record\n",
        }
    )
    document = check(seeded)
    assert "; 1 revalidation record(s)." in document["summary"][0]
    assert errors(document) == []
    seeded.write({".gitignore": None})
    document = check(seeded)
    assert "; 2 revalidation record(s)." in document["summary"][0]
    assert [location for location, _message in errors(document)] == [f"{RECORDS}/draft-idea.md"]


def test_a_record_nested_under_the_folder_is_a_record(seeded: AdopterRepo) -> None:
    """The held folder holds every Markdown file beneath it, as a place matches: a
    record in a sub-folder is checked like one directly in it (the folder was
    once read by its direct children alone)."""
    good = _record_text()
    seeded.write(
        {
            f"{RECORDS}/2026-10-01-first-run.md": good,
            f"{RECORDS}/2026/2026-10-02-nested.md": good.replace("UC-001", "UC-404"),
        }
    )
    document = check(seeded)
    assert "; 2 revalidation record(s)." in document["summary"][0]
    assert [location for location, _message in errors(document)] == [
        f"{RECORDS}/2026/2026-10-02-nested.md:/outcomes/UC-404"
    ]


def test_a_record_friction_exclude_leaves_out_is_not_counted(seeded: AdopterRepo) -> None:
    """A record under an excluded path is still held, but the backbone's listing says it is
    excluded, and the check leaves it out as an excluded artefact is no part of the
    analysis (COR-050 point 7): neither counted nor checked."""
    good = _record_text()
    seeded.write(
        {
            CONFIG: f"docs:\n  internal: tech-docs\nfriction:\n  exclude: [{RECORDS}/archive]\n",
            f"{RECORDS}/2026-10-01-first-run.md": good,
            f"{RECORDS}/archive/2026-09-01-imported.md": "# No front matter\n",
        }
    )
    document = check(seeded)
    assert "; 1 revalidation record(s)." in document["summary"][0]
    assert errors(document) == []


def test_a_records_folder_the_backbone_skips_is_said_to_hold_nothing(
    seeded: AdopterRepo,
) -> None:
    """A project place equal to the records' folder oversteps the folder's bounds
    (COR-050 point 1), so the backbone skips it and `pkit validate` reports it at
    the declaration: the check reads no record, and says why rather than showing
    none as if there were none."""
    seeded.write(
        {
            CONFIG: f"docs:\n  internal: tech-docs\nfriction:\n  places: [{RECORDS}]\n",
            f"{RECORDS}/2026-10-01-first-run.md": _record_text(),
        }
    )
    document = check(seeded)
    assert document["summary"][0].endswith(
        "; 0 revalidation record(s). The records' folder holds nothing — the backbone skipped "
        "it (overlap); `pkit validate` says why."
    )
    assert errors(document) == []
