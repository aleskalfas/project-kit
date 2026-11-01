"""software-analysis: a requirement carries a fingerprint of its texts, `obligation` (#2068).

Held to software-analysis DEC-006 points 6, 7 and 9:

- **the form, version 1** — each text read as its characters, its comments, the marks of
  emphasis CommonMark finds, wrapping and each derived link its place declares set
  aside, every other mark counted; a text absent, `None.` and empty told apart; the three
  in one order, each under its part's permanent id; the value pinned for example texts;
- **one fingerprint in either home** — the texts in front matter, and the same texts in
  the body's parts, wrapped, emphasised and with derived links written, give one value;
- **the check** — whatever any rule's status, a requirement without the field, with one
  that is no fingerprint, one of a version this release does not read, or one that no
  longer matches its texts, fails, naming the command, a withdrawn one included;
- **the command** — `pkit analysis obligation` writes the field where it is missing or no
  longer matches, leaves one that matches as it is, writes nothing under `--dry-run`, and
  keeps a file's line ends.
"""

from __future__ import annotations

import dataclasses
import functools
import json
from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML

from project_kit import document_parts
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.analysis_repo import (
    CAPABILITY,
    CONSTRAINTS,
    OBLIGATION,
    QUALITY,
    fingerprint,
    installed,
    load_lib,
    requirement,
    run_in_process,
)
from tests.test_software_analysis_check import check, errors

#: A requirement's file, and the location of its field in a finding.
QUICK = f"{QUALITY}/REQ-004-quick-result.md"
AT = f"{QUICK}:/obligation"

#: The texts `requirement` writes, as its front matter gives them.
TEXTS = {
    "statement": "The system shows a suite's result within two seconds of the run's end.",
    "measure": "None.",
    "applies-to": "Every run of a suite.",
}


@functools.cache
def _libs() -> tuple[Any, Any, Any, Any, Any]:
    """The capability's fingerprint and the modules it reads by, loaded once."""
    obligation, structure, links, citations, id_links = load_lib(
        "obligation", "structure", "links", "citations", "id_links"
    )
    return obligation, structure, links, citations, id_links


def _read(text: str) -> str:
    """One front-matter text as version 1 of the form reads it."""
    obligation, structure, *_rest = _libs()
    return obligation.canonical(structure.as_part(text), obligation.LINK_FORMS)


def _value(texts: dict[str, str], kind: str = "quality-requirement") -> str:
    """The fingerprint of `texts`, each in front matter, one left out read as absent."""
    return fingerprint(texts, kind)


# --- the form, version 1 ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "read"),
    [
        # Emphasis and strong emphasis set aside, and wrapping read as one space.
        (
            "The system **must** show a *report* within two\n  seconds.",
            "The system must show a report within two seconds.",
        ),
        ("***strong emph***", "strong emph"),
        ("**foo*", "*foo"),
        ("*foo**", "foo*"),
        ("foo*bar*", "foobar"),
        ("snake_case_name and _emph_", "snake_case_name and emph"),
        # A mark CommonMark reads as no emphasis counts.
        ("2 * 3 * 4", "2 * 3 * 4"),
        ("foo_bar_", "foo_bar_"),
        ("*foo bar *", "*foo bar *"),
        # Each item of a list is a paragraph of its own, so no mark pairs across two.
        ("- *a\n- b*", "- *a - b*"),
        # A comment is set aside, such as the escape that marks no mention.
        ("Show <!-- pkit:not-the-term --> it.", "Show it."),
        # A derived link of a form the place declares reads as its words; another counts.
        ("A [payment](../../glossary.md#term-payment--payment) is taken.", "A payment is taken."),
        ("[*x*](../../glossary.md#term-x--x)*", "x*"),
        (
            "See [the site](https://example.com/a_b_c).",
            "See [the site](https://example.com/a_b_c).",
        ),
        # A code span, an escape, strikethrough, an entity, inline HTML and an autolink
        # count as written, and hold no mark of emphasis.
        ("Run `pkit *x*` now", "Run `pkit *x*` now"),
        (r"2 \* 3", r"2 \* 3"),
        ("~~not~~ now", "~~not~~ now"),
        ("&amp; *y*", "&amp; y"),
        ("<kbd>*x*</kbd> and <https://x.y/*a*>", "<kbd>x</kbd> and <https://x.y/*a*>"),
        # Each space separator is white space; fenced code counts, but for its wrapping.
        ("a\u00a0 b\tc", "a b c"),
        ("First\n\n```\n*kept*  as   written\n```\nlast", "First ``` *kept* as written ``` last"),
    ],
)
def test_version_1_reads_a_text_as_its_rules_say(text: str, read: str) -> None:
    assert _read(text) == read


def test_version_1_gives_the_value_pinned_for_example_texts() -> None:
    """A value never changes under its version, so this one is pinned (DEC-006 point 7)."""
    texts = {
        "statement": "The system shows a report within two seconds.",
        "measure": "None.",
        "applies-to": "Every report.",
    }
    assert _value(texts) == (
        "v1:sha256:fc394ec665815dc4a4e639afa5ac41c915e240018b2b9946785be5d14a73f1c0"
    )
    # Each kind reads its texts alike.
    assert {_value(texts, kind) for kind in ("functional-requirement", "constraint")} == {
        _value(texts)
    }


def test_what_changes_what_a_text_says_changes_the_value() -> None:
    """Every word with its case and its punctuation counts, a text moved to another part
    counts, and an absent text, `None.` and an empty one differ (DEC-006 point 7)."""
    base = _value(TEXTS)
    changed = [
        {**TEXTS, "statement": TEXTS["statement"].replace("shows", "must not show")},
        {**TEXTS, "statement": TEXTS["statement"].replace("The", "the")},
        {**TEXTS, "statement": TEXTS["statement"].rstrip(".")},
        {**TEXTS, "measure": TEXTS["applies-to"], "applies-to": TEXTS["measure"]},
        {**TEXTS, "measure": ""},
        {key: text for key, text in TEXTS.items() if key != "measure"},
    ]
    values = [_value(texts) for texts in changed]
    assert base not in values
    assert len(set(values)) == len(values)
    # What changes only how a text looks changes nothing.
    looks = {
        **TEXTS,
        "statement": "The system *shows* a suite's result within\ntwo seconds of "
        "the run's **end**.",
    }
    assert _value(looks) == base


def test_the_reading_of_links_and_code_spans_is_friction_s() -> None:
    """The fingerprint reads a derived link as friction does (COR-050 point 5), so its
    link and code span are the backbone's."""
    obligation, *_rest = _libs()
    parts: Any = document_parts
    assert obligation._INLINE_LINK.pattern == parts._INLINE_LINK.pattern
    assert obligation._CODE_SPAN.pattern == parts._CODE_SPAN.pattern


def test_the_forms_are_those_each_requirement_s_place_declares() -> None:
    """The forms are those `pkit analysis link` writes, a link to a glossary entry by a
    path, a citation's and an id's, which each requirement's place declares at the top and
    one folder down, never the version's (DEC-006 point 7)."""
    obligation, _structure, links, citations, id_links = _libs()
    assert obligation.LINK_FORMS == (links.ENTRY_BY_PATH, citations.TARGET, id_links.TARGET)
    package = YAML(typ="safe").load((CAPABILITY / "package.yaml").read_text(encoding="utf-8"))
    declared = {
        place["path"]: tuple(link["target"] for link in place["derived-links"])
        for place in package["friction"]["places"]
        if place["type"] in ("quality-requirement", "functional-requirement", "constraint")
    }
    assert len(declared) == 6
    assert set(declared.values()) == {obligation.LINK_FORMS}


# --- one fingerprint in either home ----------------------------------------------------------


def _parted(kind: str = "quality-requirement") -> Any:
    """`kind` as a later structure gives it, its three texts its first three parts, each a
    label named after the field it replaces (DEC-006 point 1)."""
    _obligation, structure, *_rest = _libs()
    shipped = structure.read_kinds()[kind]
    texts = tuple(
        structure.Element(id_, structure.LABEL, text=label, hint="Write it.")
        for id_, label in (
            ("statement", "Statement"),
            ("measure", "Measure"),
            ("applies-to", "Applies to"),
        )
    )
    return dataclasses.replace(
        shipped, sections=(shipped.sections[0], *texts, *shipped.sections[1:])
    )


#: The texts in front matter, and the same texts in the body's parts: wrapped, emphasised,
#: and with each derived link written as `pkit analysis link` writes it, a term's, an id's
#: and a citation's.
IN_DATA = {
    "statement": "The system shows a report within two seconds of the analyst opening it.",
    "measure": "95 of every 100 reports show within two seconds, as PRJ-003 asks.",
    "applies-to": "Every report the analyst opens, as REQ-003 bounds it.",
}
IN_BODY = """# REQ-004 · Quality · Show a report fast

**Statement:** The system shows a [report](../../glossary.md#term-report--report) within
two seconds of the [analyst](../../use-case-model/actors/ACT-analyst.md) opening it.

**Measure:** 95 of every 100 reports show within *two seconds*, as
[PRJ-003](../../../../.pkit/decisions/project/PRJ-003-reports.md) asks.

**Applies to:** Every report the analyst opens, as [REQ-003](REQ-003-reports.md) bounds it.

**Verified by:** A timing test opens a report.

**Rationale:** None.
"""


def test_the_texts_in_data_and_in_the_body_give_one_fingerprint() -> None:
    """Moving the texts from front matter into the body, derived links written, changes no
    fingerprint, so the move asks no revisit (DEC-006 points 7 and 9)."""
    obligation, structure, *_rest = _libs()
    kind = _parted()
    forms = obligation.LINK_FORMS
    lines = structure.body_lines(IN_BODY)
    in_data = obligation.texts(IN_DATA, list, kind)
    in_body = obligation.texts({}, lambda: lines, kind)
    assert in_data.homes == dict.fromkeys(IN_DATA, obligation.FRONT_MATTER)
    assert in_body.homes == dict.fromkeys(IN_DATA, obligation.BODY)
    assert obligation.value(in_body, forms) == obligation.value(in_data, forms)
    # A word changed in the body changes it.
    reworded = structure.body_lines(IN_BODY.replace("95 of every", "90 of every"))
    changed = obligation.texts({}, lambda: reworded, kind)
    assert obligation.value(changed, forms) != obligation.value(in_data, forms)


def test_a_text_moved_word_for_word_gives_one_fingerprint() -> None:
    """A text moved after its label as its characters stand reads as it did in front
    matter: a comment, a code span, an escape, a list and fenced code included."""
    obligation, structure, *_rest = _libs()
    kind = _parted()
    forms = obligation.LINK_FORMS
    texts = {
        "statement": "The `check` *fails* a run <!-- pkit:not-the-term --> that \\* breaks.",
        "measure": "Two cases:\n\n- one run\n- **two** runs\n\n```\nkept  as written\n```",
        "applies-to": "Every run.",
    }
    body = "# REQ-004 · Quality · A run\n\n" + "".join(
        f"**{label}:** {texts[id_]}\n\n"
        for id_, label in (
            ("statement", "Statement"),
            ("measure", "Measure"),
            ("applies-to", "Applies to"),
        )
    )
    lines = structure.body_lines(body)
    moved = obligation.texts({}, lambda: lines, kind)
    assert obligation.value(moved, forms) == obligation.value(
        obligation.texts(texts, list, kind), forms
    )


def test_a_part_the_body_lacks_reads_as_absent() -> None:
    """A part the body lacks reads as absent, never as another part's text, and differs
    from `None.` (DEC-006 points 3 and 7)."""
    obligation, structure, *_rest = _libs()
    kind = _parted()
    forms = obligation.LINK_FORMS
    lines = structure.body_lines(IN_BODY.replace("**Measure:**", "**Measured:**"))
    read = obligation.texts({}, lambda: lines, kind)
    assert read.absent == ("measure",)
    assert obligation.value(read, forms) != obligation.value(
        obligation.texts({**IN_DATA, "measure": "None."}, list, kind), forms
    )
    # The shipped kind declares no such part, so a body holds none of the three yet.
    shipped = structure.read_kinds()["quality-requirement"]
    assert obligation.texts({}, lambda: lines, shipped).absent == tuple(IN_DATA)


# --- writing the field in front matter ----------------------------------------------------------


def test_the_field_is_written_after_the_texts_and_every_other_line_kept() -> None:
    obligation, *_rest = _libs()
    text = (
        "---\nid: REQ-004\ntitle: Fast\nstatus: active\nstatement: It is fast.\n"
        "measure: None.\napplies-to: |\n  Every run.\n# the actors\nactors: [ACT-tester]\n"
        "pkit:\n  friction: {}\n---\n\n# REQ-004 · Quality · Fast\n"
    )
    written = obligation.with_value(text, "v1:sha256:00")
    assert written == text.replace("# the actors\n", "obligation: v1:sha256:00\n# the actors\n")
    # Written again, its line is replaced, and nothing else moves.
    assert obligation.with_value(written, "v1:sha256:11") == written.replace(
        "v1:sha256:00", "v1:sha256:11"
    )
    with pytest.raises(obligation.Unwritable):
        obligation.with_value("---\n- a list\n---\n", "v1:sha256:00")


# --- the check --------------------------------------------------------------------------------


@pytest.fixture
def project(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    return installed(make_adopter_repo, monkeypatch)


def test_the_check_holds_the_fingerprint_whatever_any_rule_s_status(
    project: AdopterRepo,
) -> None:
    """No rule of `SAN` binds here, and the check still fails a requirement without its
    fingerprint, one that is no fingerprint, one of a version this release does not
    read, and one that no longer matches its texts, a withdrawn one too, each naming the
    command (DEC-006 point 6)."""
    project.write({QUICK: requirement()})
    assert errors(check(project)) == []

    project.write({QUICK: requirement(obligation=None)})
    ((where, said),) = errors(check(project))
    assert where == AT
    assert said == (
        "it carries no `obligation`, the fingerprint of its statement, its measure and where "
        "it holds, which the check holds equal to them: run `pkit analysis obligation` to "
        "write it, and commit it with the change (DEC-006 point 6)"
    )

    project.write({QUICK: requirement(obligation="sha256:00")})
    ((where, said),) = errors(check(project))
    assert said.startswith("it reads 'sha256:00', which is no fingerprint, `v<version>:sha256")

    project.write({QUICK: requirement(obligation="v9:sha256:00")})
    ((where, said),) = errors(check(project))
    assert said.startswith(
        "it names version 9 of the form, hashed with sha256, which this release does not read"
    )

    stale = requirement(obligation=fingerprint({**TEXTS, "measure": "Two seconds."}))
    project.write({QUICK: stale.replace('status: "active"', 'status: "withdrawn"')})
    ((where, said),) = errors(check(project))
    assert (where, said) == (
        AT,
        "it no longer matches its statement, its measure and where it holds: one of them "
        "changed since it was written. Run `pkit analysis obligation` to write it anew, and "
        "commit it with the change (DEC-006 point 6)",
    )


def test_a_change_that_only_changes_how_a_text_looks_keeps_the_fingerprint(
    project: AdopterRepo,
) -> None:
    project.write({QUICK: requirement()})
    looks = requirement(
        statement="The system *shows* a suite's result within  two seconds of the run's **end**.",
        obligation=fingerprint(TEXTS),
    )
    project.write({QUICK: looks})
    assert errors(check(project)) == []


# --- the command --------------------------------------------------------------------------------


def _obligation(project: AdopterRepo, *args: str) -> Any:
    return run_in_process(project, OBLIGATION, *args)


def test_the_command_writes_each_missing_or_stale_fingerprint_and_leaves_the_rest(
    project: AdopterRepo,
) -> None:
    """It writes the field where a requirement holds none or one that no longer matches,
    leaves one that matches byte for byte, and run again writes nothing."""
    local = f"{CONSTRAINTS}/REQ-001-local-runs.md"
    held = f"{QUALITY}/REQ-002-held.md"
    project.write(
        {
            QUICK: requirement(obligation=None),
            local: requirement(
                "constraint", req_id="REQ-001", obligation=fingerprint({**TEXTS, "measure": "x"})
            ),
            held: requirement(req_id="REQ-002"),
        }
    )
    before = (project.root / held).read_bytes()

    dry = _obligation(project, "--dry-run")
    assert dry.returncode == 0, dry.stderr
    assert dry.stdout.splitlines() == [
        f"would write the obligation of REQ-001 at {local} (it no longer matched its texts)",
        f"would write the obligation of REQ-004 at {QUICK} (it held none)",
    ]
    assert len(errors(check(project))) == 2

    done = _obligation(project)
    assert done.returncode == 0, done.stderr
    assert errors(check(project)) == []
    assert (project.root / held).read_bytes() == before
    text = (project.root / QUICK).read_text(encoding="utf-8")
    assert f'applies-to: "Every run of a suite."\nobligation: {fingerprint(TEXTS)}\npkit:' in text

    again = _obligation(project)
    assert again.returncode == 0, again.stderr
    assert again.stdout == "Each of 3 requirement(s) holds its obligation; nothing written.\n"


def test_the_command_writes_the_requirements_named_and_prints_its_document(
    project: AdopterRepo,
) -> None:
    other = f"{QUALITY}/REQ-002-other.md"
    project.write(
        {QUICK: requirement(obligation=None), other: requirement(req_id="REQ-002", obligation=None)}
    )
    shown = _obligation(project, "REQ-4", "--json")
    assert shown.returncode == 0, shown.stderr
    document = json.loads(shown.stdout)
    (entry,) = document["written"]
    assert (document["schema_version"], document["dry_run"], document["held"]) == (1, False, 0)
    assert (entry["id"], entry["path"], entry["was"]) == ("REQ-004", QUICK, None)
    assert entry["value"] == fingerprint(TEXTS)
    assert entry["text"] == (project.root / QUICK).read_text(encoding="utf-8")
    assert "obligation" not in (project.root / other).read_text(encoding="utf-8")
    # An id the analysis does not hold writes nothing.
    unknown = _obligation(project, "REQ-009")
    assert unknown.returncode == 1
    assert "no requirement REQ-009 in the analysis; nothing is written" in unknown.stderr


def test_the_command_keeps_a_file_s_line_ends_and_leaves_a_version_it_does_not_read(
    project: AdopterRepo,
) -> None:
    crlf = requirement(obligation=None).replace("\n", "\r\n")
    later = f"{QUALITY}/REQ-002-later.md"
    project.write({later: requirement(req_id="REQ-002", obligation="v9:sha256:00")})
    (project.root / QUICK).write_bytes(crlf.encode("utf-8"))

    done = _obligation(project)
    assert done.returncode == 1
    assert f"error: {later}: it names version 9 of the form" in done.stderr
    written = (project.root / QUICK).read_bytes().decode("utf-8")
    assert "\n" not in written.replace("\r\n", "")
    assert f"obligation: {fingerprint(TEXTS)}\r\n" in written
    assert "v9:sha256:00" in (project.root / later).read_text(encoding="utf-8")
