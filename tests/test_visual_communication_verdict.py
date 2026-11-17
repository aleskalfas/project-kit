"""The verdict against a project's bar, from a round's review report, and whether it ends the
designer's loop (visual-communication DEC-042 points 1, 9 and 10, #3227).

Held here:

- **the verdict**: given from a planted report and the configuration's bar, page by page
  and for the piece; each unmarked grade below the bar's grade fails it, a marked grade is
  left out, a grade of a rule the bar does not cover counts for nothing, and the same report
  gives the same verdict again;
- **no verdict, or a refusal**: no bar gives no verdict, and nor does a report that grades
  a covered rule nowhere; what the verdict would rest on and cannot be read refuses, and a
  report whose document does not parse is named so, with the line the reading stopped at
  where the reader names it and with none where it names none, while the same words as a
  block scalar give the verdict (#3391);
- **the hold**: ends no loop where no calibration's report is accepted, where the bar reaches
  past the accepted rules, and where anything point 9 names has lapsed, a change to the
  capability's code or to the body of its list of checks among it (DEC-065); ends it where
  the accepted data is the reading of the state it was given at, and where only a file
  beside the code or the list's front matter changed since;
- **the code's digest**: it leaves out no file the capability ships in its scripts folder
  but a folder's marker (DEC-065 point 2);
- **the accepted calibration's data**: the shape the capability ships, which the command
  reads.

Each test runs the command's script from a copy of the capability's folder, in the test's
own process (`tests/in_process.py`), so the data a test plants is the capability's own, as
a refinement's change would write it.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from tests.in_process import load, run_main
from tests.visual_communication_project import CAPABILITY, CONFIG, REPO, bound, project, write

#: The parts of the capability's folder the command reads, copied for each test.
COPIED = ("scripts", "schemas", "rule-sets", "agents", "design-knowledge", "checks.md")

#: The one kind of file the capability ships in its scripts folder that is not code: a
#: folder's marker.
MARKER = ".gitkeep"

#: Where the copy keeps the accepted calibration's data, and a round's report.
DATA = ".pkit/capabilities/visual-communication/calibration.yaml"
REVIEWS = ".pkit/capabilities/visual-communication/project/local/reviews"

#: The bar most tests set: one rule judged on each page, and one judged on the pieces as a
#: whole.
COVERS = ("RS-GRAPHIC-001@2", "RS-COMM-003@1")


class Copy:
    """A project whose capability's folder is a copy of this checkout's, with the command's
    script and the modules it reads loaded from the copy."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.folder = root / ".pkit" / "capabilities" / "visual-communication"
        for part in COPIED:
            if (CAPABILITY / part).is_file():
                shutil.copyfile(CAPABILITY / part, self.folder / part)
                continue
            shutil.copytree(
                CAPABILITY / part,
                self.folder / part,
                ignore=shutil.ignore_patterns("__pycache__"),
            )
        loaded = load(self.folder / "scripts", "verdict.py", "bar", "files", "calibration")
        self.script: ModuleType = loaded[0]
        self.bar: ModuleType = loaded[1]
        self.files: ModuleType = loaded[2]
        self.calibration: ModuleType = loaded[3]

    def run(self, *args: str) -> tuple[int, str, str]:
        done = run_main(self.script, *args, cwd=self.root)
        return done.returncode, done.stdout, done.stderr

    def answered(self, *args: str) -> dict[str, Any]:
        code, out, err = self.run(*args, "--json")
        assert code == 0, err
        return json.loads(out)

    def accept(self, reading: dict[str, Any]) -> None:
        """The accepted calibration's data, written as a refinement's change would."""
        write(self.root / DATA, json.dumps(bound("calibration", **reading)))


@pytest.fixture
def copy(tmp_path: Path) -> Copy:
    return Copy(project(tmp_path))


def configured(copy: Copy, *covers: str, at_least: str = "professional") -> None:
    data = bound("config", bar={"covers": list(covers), "at-least": at_least})
    write(copy.root / CONFIG, json.dumps(data))


def grade(rule: str, mark: str | None = None, *, page: str | None = None, **fields: Any) -> Any:
    """One grade of a report, on `page`, or for the piece as a whole where `page` is None."""
    entry: dict[str, Any] = {
        "rule": rule,
        "on": {"page": page} if page is not None else {"piece": True},
        "grade": fields.pop("grade", "professional"),
        "evidence": fields.pop("evidence", "What the drawn page shows."),
        **fields,
    }
    if mark is not None:
        entry["mark"] = {"kind": mark, "names": "What only it would raise."}
    return entry


def kept(
    copy: Copy,
    grades: list[Any],
    *,
    piece: str = "deck",
    number: int = 1,
    not_graded: list[Any] | None = None,
    model: dict[str, Any] | None = None,
) -> None:
    """A round's report, kept alone as its dispatcher keeps it."""
    report = bound(
        "review",
        piece=piece,
        round=number,
        model=model if model is not None else {"name": "a-model-1.0", "effort": "high"},
        **{
            "read-before-grading": [{"kind": "images", "what": "Every image of the run."}],
            "grades": grades,
        },
    )
    if not_graded is not None:
        report["not-graded"] = not_graded
    write(copy.root / REVIEWS / piece / f"round-{number}.yaml", json.dumps(report))


def planted(copy: Copy, **fields: Any) -> None:
    """The bar most tests set, and a report that grades both its rules: the cover page
    leaves out the rule on the pages' order, and the piece takes it once."""
    configured(copy, *COVERS)
    kept(
        copy,
        [
            grade("RS-GRAPHIC-001", page="cover", grade="excellent"),
            grade("RS-GRAPHIC-001", page="layers", grade="competent", evidence="Two compete."),
            grade("RS-COMM-001", page="layers", grade="below competent"),
            grade("RS-COMM-003", grade="professional"),
        ],
        **fields,
    )


# --- the verdict --------------------------------------------------------------------------------


def test_the_verdict_from_a_planted_report_names_each_page_the_piece_and_what_fails(
    copy: Copy,
) -> None:
    planted(copy)
    answered = copy.answered("deck")
    assert answered["rules"] == ["RS-GRAPHIC-001", "RS-COMM-003"]
    assert answered["bar"] == {"covers": list(COVERS), "at-least": "professional"}
    verdict = answered["verdict"]
    assert verdict["meets"] is False
    assert [(page["page"], page["meets"]) for page in verdict["pages"]] == [
        ("cover", True),
        ("layers", False),
    ]
    (failing,) = verdict["pages"][1]["failing"]
    assert (failing["rule"], failing["grade"], failing["evidence"]) == (
        "RS-GRAPHIC-001",
        "competent",
        "Two compete.",
    )
    assert verdict["piece"] == {"meets": True, "failing": []}
    assert verdict["marked"] == []


def test_a_grade_of_a_rule_the_bar_does_not_cover_counts_for_nothing(copy: Copy) -> None:
    planted(copy)
    failing = copy.answered("deck")["verdict"]["pages"][1]["failing"]
    assert [each["rule"] for each in failing] == ["RS-GRAPHIC-001"]


def test_a_marked_grade_is_left_out_of_the_verdict_and_named_apart(copy: Copy) -> None:
    configured(copy, *COVERS)
    kept(
        copy,
        [
            grade("RS-GRAPHIC-001", "need", page="layers", grade="competent"),
            grade("RS-COMM-003", "asker", grade="below competent"),
        ],
    )
    verdict = copy.answered("deck")["verdict"]
    assert verdict["meets"] is True
    assert [(each["rule"], each["mark"]) for each in verdict["marked"]] == [
        ("RS-GRAPHIC-001", "need"),
        ("RS-COMM-003", "asker"),
    ]


def test_a_grade_for_the_piece_as_a_whole_fails_the_piece_though_every_page_meets(
    copy: Copy,
) -> None:
    configured(copy, *COVERS)
    kept(
        copy,
        [
            grade("RS-GRAPHIC-001", page="cover"),
            grade("RS-COMM-003", grade="competent", evidence="The third lead does not follow."),
        ],
    )
    verdict = copy.answered("deck")["verdict"]
    assert [page["meets"] for page in verdict["pages"]] == [True]
    assert verdict["piece"]["meets"] is False
    assert verdict["piece"]["failing"][0]["rule"] == "RS-COMM-003"
    assert verdict["meets"] is False


def test_a_bar_at_excellent_fails_a_professional_grade(copy: Copy) -> None:
    configured(copy, *COVERS, at_least="excellent")
    kept(copy, [grade("RS-GRAPHIC-001", page="cover"), grade("RS-COMM-003", grade="excellent")])
    verdict = copy.answered("deck")["verdict"]
    assert verdict["pages"] == [
        {
            "page": "cover",
            "meets": False,
            "failing": [
                {
                    "rule": "RS-GRAPHIC-001",
                    "on": {"page": "cover"},
                    "grade": "professional",
                    "evidence": "What the drawn page shows.",
                }
            ],
        }
    ]
    assert verdict["piece"]["meets"] is True


def test_a_set_covered_takes_each_of_its_rules(copy: Copy) -> None:
    configured(copy, "COMM@1")
    rules = [f"RS-COMM-00{n}" for n in range(1, 6)]
    kept(copy, [grade(rule, page="cover") for rule in rules])
    answered = copy.answered("deck")
    assert answered["rules"] == rules
    assert answered["verdict"]["meets"] is True


def test_anyone_gives_the_same_verdict_again_from_the_same_report(copy: Copy) -> None:
    planted(copy)
    assert copy.run("deck") == copy.run("deck")
    assert copy.answered("deck") == copy.answered("deck")


def test_it_reads_the_highest_round_kept_unless_one_is_named(copy: Copy) -> None:
    planted(copy)
    kept(copy, [grade("RS-GRAPHIC-001", page="cover"), grade("RS-COMM-003")], number=2)
    assert copy.answered("deck")["round"] == 2
    assert copy.answered("deck")["verdict"]["meets"] is True
    assert copy.answered("deck", "--round", "1")["verdict"]["meets"] is False


def test_it_prints_the_verdict_and_why_it_ends_no_loop(copy: Copy) -> None:
    planted(copy)
    code, out, _ = copy.run("deck")
    assert code == 0
    lines = out.splitlines()
    assert lines[0] == f"report: round 1 of `deck`, in {REVIEWS}/deck/round-1.yaml"
    assert lines[1] == "bar: at least professional on RS-GRAPHIC-001@2, RS-COMM-003@1"
    assert lines[2] == "rules covered: RS-GRAPHIC-001, RS-COMM-003"
    assert lines[3:8] == [
        "verdict: the piece fails the bar",
        "  page `cover`: meets the bar",
        "  page `layers`: fails the bar",
        "    RS-GRAPHIC-001, competent: Two compete.",
        "  the piece as a whole: meets the bar",
    ]
    assert lines[8] == "ends the loop: no, the verdict informs"
    assert "no calibration's report is accepted" in lines[9]


# --- no verdict, or a refusal -------------------------------------------------------------------


def test_no_bar_gives_no_verdict_and_says_why(copy: Copy) -> None:
    write(copy.root / CONFIG, json.dumps(bound("config")))
    kept(copy, [grade("RS-GRAPHIC-001", page="cover")])
    answered = copy.answered("deck")
    assert (answered["bar"], answered["verdict"], answered["ends-the-loop"]) == (None, None, False)
    (why,) = answered["why"]
    assert "holds no bar" in why
    assert "DEC-030 point 2" in why


def test_a_project_with_no_configuration_has_no_bar(copy: Copy) -> None:
    kept(copy, [grade("RS-GRAPHIC-001", page="cover")])
    assert copy.answered("deck")["verdict"] is None


def test_a_covered_rule_the_report_grades_nowhere_gives_no_verdict(copy: Copy) -> None:
    configured(copy, *COVERS, "RS-GRAPHIC-002@2")
    kept(
        copy,
        [grade("RS-GRAPHIC-001", page="cover")],
        not_graded=[{"rule": "RS-COMM-003", "on": {"piece": True}, "why": "One page."}],
    )
    answered = copy.answered("deck")
    assert answered["verdict"] is None
    (why,) = answered["why"]
    assert "`RS-GRAPHIC-002`" in why
    assert "RS-COMM-003" not in why


@pytest.mark.parametrize(
    ("setup", "said"),
    [
        (lambda copy: None, "no report of a round of `deck` is kept"),
        (
            lambda copy: write(
                copy.root / REVIEWS / "deck" / "round-1.yaml",
                json.dumps(bound("review", piece="deck", round=1)),
            ),
            "its schema refuses it",
        ),
    ],
    ids=["none-kept", "refused-by-its-schema"],
)
def test_a_report_it_cannot_read_refuses(copy: Copy, setup: Any, said: str) -> None:
    configured(copy, *COVERS)
    setup(copy)
    code, out, err = copy.run("deck")
    assert (code, out) == (1, "")
    assert said in err


def written(copy: Copy, *evidence: str) -> int:
    """A round's document as a reviewer writes it, in YAML, kept alone: its first grade fails
    the bar most tests set, and `evidence` gives the lines of its evidence, each indented
    under the grade's other keys. Returns the line of the document the evidence opens on."""
    head = [
        "pkit_schema: visual-communication:review",
        "schema_version: 1",
        "piece: deck",
        "round: 1",
        "model:",
        "  name: a-model-1.0",
        "read-before-grading:",
        "  - kind: images",
        "    what: Every image of the run.",
        "grades:",
        "  - rule: RS-GRAPHIC-001",
        "    on:",
        "      page: layers",
        "    grade: competent",
    ]
    tail = [
        "  - rule: RS-COMM-003",
        "    on:",
        "      piece: true",
        "    grade: professional",
        "    evidence: Each lead follows from the one before it.",
    ]
    lines = [*head, *(f"    {line}" for line in evidence), *tail]
    write(copy.root / REVIEWS / "deck" / "round-1.yaml", "\n".join(lines) + "\n")
    return len(head) + 1


#: Words a value in words may hold that a plain value does not parse with (#3391): a `: `,
#: and a quoted phrase the value opens with and goes on after.
UNPARSED = pytest.mark.parametrize(
    "words",
    ["The lead: it answers no question.", '"Two compete" for the eye, and the figure loses.'],
    ids=["holding-a-colon", "opening-with-a-quoted-phrase"],
)


@UNPARSED
def test_a_report_whose_document_does_not_parse_is_named_with_the_line_it_stopped_at(
    copy: Copy, words: str
) -> None:
    configured(copy, *COVERS)
    line = written(copy, f"evidence: {words}")
    for args in (("deck",), ("deck", "--json")):
        code, out, err = copy.run(*args)
        assert (code, out) == (1, "")
        assert (
            f"{REVIEWS}/deck/round-1.yaml: the report's document does not parse as YAML, so no "
            f"verdict is read from it: the reading stopped at line {line}, column "
        ) in err


def test_a_report_whose_document_does_not_parse_where_the_reader_names_no_place_gives_none(
    copy: Copy,
) -> None:
    """A character YAML does not allow stops the reader before it names a line (#3391)."""
    configured(copy, *COVERS)
    written(copy, "evidence: >-", "  The lead\x07 answers no question.")
    code, out, err = copy.run("deck")
    assert (code, out) == (1, "")
    assert (
        f"{REVIEWS}/deck/round-1.yaml: the report's document does not parse as YAML, so no "
        "verdict is read from it: "
    ) in err
    assert "the reading stopped at" not in err


@UNPARSED
def test_the_same_words_as_a_block_scalar_give_the_verdict(copy: Copy, words: str) -> None:
    configured(copy, *COVERS)
    written(copy, "evidence: >-", f"  {words}")
    (failing,) = copy.answered("deck")["verdict"]["pages"][0]["failing"]
    assert failing["evidence"] == words


@pytest.mark.parametrize(
    ("piece", "number", "said"),
    [
        ("other", 3, "is of round 3 of `other`, yet is kept as round 3 of `deck`"),
        ("deck", 2, "is of round 2 of `deck`, yet is kept as round 3 of `deck`"),
    ],
)
def test_a_report_of_another_piece_or_round_than_it_is_kept_as_refuses(
    copy: Copy, piece: str, number: int, said: str
) -> None:
    configured(copy, *COVERS)
    kept(copy, [grade("RS-GRAPHIC-001", page="cover")], piece=piece, number=number)
    folder = copy.root / REVIEWS / "deck"
    folder.mkdir(parents=True, exist_ok=True)
    (copy.root / REVIEWS / piece / f"round-{number}.yaml").rename(folder / "round-3.yaml")
    code, _, err = copy.run("deck")
    assert code == 1
    assert said in err


@pytest.mark.parametrize(
    ("covers", "said"),
    [
        (("RS-GRAPHIC-001@1",), "bar-major"),
        (("NOPE@1",), "bar-ungraded"),
    ],
)
def test_a_bar_the_check_fails_refuses(copy: Copy, covers: tuple[str, ...], said: str) -> None:
    configured(copy, *covers)
    kept(copy, [grade("RS-GRAPHIC-001", page="cover")])
    code, _, err = copy.run("deck")
    assert code == 1
    assert said in err


def test_a_bar_its_schema_refuses_refuses(copy: Copy) -> None:
    configured(copy, *COVERS, at_least="competent")
    kept(copy, [grade("RS-GRAPHIC-001", page="cover")])
    code, _, err = copy.run("deck")
    assert code == 1
    assert "the schema refuses its bar" in err


@pytest.mark.parametrize("args", [("Deck",), ("deck", "--round", "0"), ("deck", "--round", "x")])
def test_a_name_or_a_round_that_is_none_is_refused(copy: Copy, args: tuple[str, ...]) -> None:
    planted(copy)
    code, _, _ = copy.run(*args)
    assert code in (1, 2)


# --- the hold -----------------------------------------------------------------------------------


def test_no_report_accepted_ends_no_loop(copy: Copy) -> None:
    planted(copy)
    answered = copy.answered("deck")
    assert answered["ends-the-loop"] is False
    (why,) = answered["why"]
    assert "no calibration's report is accepted" in why
    assert "DEC-042 point 9" in why


def test_the_reading_accepted_as_the_data_ends_the_loop(copy: Copy) -> None:
    planted(copy)
    copy.accept(copy.answered("deck")["reading"])
    answered = copy.answered("deck")
    assert (answered["ends-the-loop"], answered["why"]) == (True, [])
    _, out, _ = copy.run("deck")
    assert "ends the loop: yes" in out


def test_a_failing_verdict_under_the_hold_still_ends_the_loop_at_the_bar(copy: Copy) -> None:
    planted(copy)
    copy.accept(copy.answered("deck")["reading"])
    answered = copy.answered("deck")
    assert answered["verdict"]["meets"] is False
    assert answered["ends-the-loop"] is True


def test_a_bar_that_reaches_past_the_accepted_rules_ends_no_loop(copy: Copy) -> None:
    planted(copy)
    reading = copy.answered("deck")["reading"]
    del reading["rules"]["RS-COMM-003"]
    copy.accept(reading)
    (why,) = copy.answered("deck")["why"]
    assert "reaches past the accepted calibration" in why
    assert "`RS-COMM-003`" in why
    assert "DEC-042 point 10" in why


def test_a_bar_over_some_of_the_accepted_rules_gets_the_hold(copy: Copy) -> None:
    planted(copy)
    copy.accept(copy.answered("deck")["reading"])
    configured(copy, "RS-GRAPHIC-001@2")
    assert copy.answered("deck")["ends-the-loop"] is True


def _new_major(copy: Copy) -> None:
    path = copy.folder / "rule-sets" / "graphic.md"
    path.write_text(path.read_text().replace("version: 2.0.0", "version: 3.0.0", 1))
    configured(copy, "RS-GRAPHIC-001@3", "RS-COMM-003@1")


def _reworded(copy: Copy, rule: str = "RS-GRAPHIC-001") -> None:
    path = copy.folder / "rule-sets" / "graphic.md"
    text = path.read_text()
    assert f"## {rule} — " in text
    path.write_text(text.replace(f"## {rule} — ", f"## {rule} — Reworded: ", 1))


def _appended(path: Path) -> None:
    path.write_text(path.read_text() + "\nOne more line.\n")


def _commented(copy: Copy, code: str) -> None:
    """A comment added to the program file `code` of the copy's scripts folder."""
    path = copy.folder / "scripts" / code
    path.write_text(path.read_text() + "# One more line.\n")


@pytest.mark.parametrize(
    ("lapse", "said"),
    [
        (_new_major, "is at major 3, and the calibration read major 2"),
        (_reworded, "the text of `RS-GRAPHIC-001` differs"),
        (
            lambda copy: _appended(copy.folder / "agents" / "graphic-design-reviewer.md"),
            "the reviewer's definition differs",
        ),
        (
            lambda copy: _appended(copy.folder / "design-knowledge" / "colour.md"),
            "the design knowledge differs",
        ),
        (
            lambda copy: write(copy.folder / "design-knowledge" / "new-topic.md", "A topic.\n"),
            "the design knowledge differs",
        ),
        (
            lambda copy: _commented(copy, "_lib/scene_checks.py"),
            "the capability's code, in `scripts/`, differs from the code the calibration ran on",
        ),
        (
            lambda copy: _commented(copy, "_lib/plugins/svg.py"),
            "the capability's code, in `scripts/`, differs",
        ),
        (
            lambda copy: write(copy.folder / "scripts" / "_lib" / "left.py", "LEFT = 1\n"),
            "the capability's code, in `scripts/`, differs",
        ),
        (
            lambda copy: (copy.folder / "scripts" / "_lib" / "boxes.py").unlink(),
            "the capability's code, in `scripts/`, differs",
        ),
        (
            lambda copy: _appended(copy.folder / "checks.md"),
            "the list of checks, `checks.md`, differs from the one the calibration read",
        ),
        (
            lambda copy: planted(copy, model={"name": "another-model-2.0", "effort": "high"}),
            "the review ran on the model `another-model-2.0`, and the calibration on `a-model-1.0`",
        ),
        (
            lambda copy: planted(copy, model={"name": "a-model-1.0", "effort": "low"}),
            "the review ran at the effort `low`, and the calibration at the effort `high`",
        ),
        (
            lambda copy: planted(copy, model={"name": "a-model-1.0"}),
            "the review ran with no effort named",
        ),
        (
            lambda copy: write(
                copy.root / ".pkit" / "agents" / "project" / "graphic-design-reviewer.md", "x\n"
            ),
            "another definition of `graphic-design-reviewer` stands in the project, in "
            "`.pkit/agents/project/graphic-design-reviewer.md`",
        ),
        (
            lambda copy: write(
                copy.root / ".pkit/capabilities/other/agents/graphic-design-reviewer.md", "x\n"
            ),
            "`.pkit/capabilities/other/agents/graphic-design-reviewer.md`",
        ),
    ],
    ids=[
        "a-new-major",
        "a-rule-reworded",
        "the-reviewers-definition",
        "the-design-knowledge-changed",
        "the-design-knowledge-added-to",
        "a-checks-code",
        "a-renderer",
        "a-program-file-added",
        "a-program-file-removed",
        "the-list-of-checks",
        "another-model",
        "another-effort",
        "no-effort",
        "the-projects-own-reviewer",
        "another-capabilitys-reviewer",
    ],
)
def test_each_lapse_ends_no_loop_and_says_why(copy: Copy, lapse: Any, said: str) -> None:
    planted(copy)
    copy.accept(copy.answered("deck")["reading"])
    lapse(copy)
    answered = copy.answered("deck")
    assert answered["verdict"] is not None
    assert answered["ends-the-loop"] is False
    (why,) = answered["why"]
    assert said in why
    assert "DEC-042 point 9" in why


def test_a_rule_the_bar_does_not_cover_lapses_nothing(copy: Copy) -> None:
    planted(copy)
    copy.accept(copy.answered("deck")["reading"])
    _reworded(copy, "RS-GRAPHIC-002")
    assert copy.answered("deck")["ends-the-loop"] is True


def _beside(copy: Copy, name: str, data: bytes = b"\x00") -> None:
    path = copy.folder / "scripts" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _front_matter_changed(copy: Copy) -> None:
    path = copy.folder / "checks.md"
    text = path.read_text()
    assert text.startswith("---\nreader: user\n")
    path.write_text(text.replace("reader: user\n", "reader: user\n# A note.\n", 1))


@pytest.mark.parametrize(
    "change",
    [
        lambda copy: _beside(copy, "_lib/__pycache__/calibration.cpython-312.pyc"),
        lambda copy: _beside(copy, ".gitkeep", b"marked\n"),
        lambda copy: _beside(copy, "_lib/plugins/.gitkeep"),
        lambda copy: _beside(copy, "_lib/calibration.py~", b"An editor's copy.\n"),
        lambda copy: _beside(copy, ".DS_Store"),
        _front_matter_changed,
    ],
    ids=[
        "a-compiled-cache",
        "a-folders-marker-changed",
        "a-folders-marker-added",
        "an-editors-file",
        "a-systems-file",
        "the-lists-front-matter",
    ],
)
def test_a_file_beside_the_code_or_the_lists_front_matter_lapses_nothing(
    copy: Copy, change: Any
) -> None:
    planted(copy)
    copy.accept(copy.answered("deck")["reading"])
    change(copy)
    answered = copy.answered("deck")
    assert (answered["ends-the-loop"], answered["why"]) == (True, [])


def test_accepted_data_it_cannot_read_ends_no_loop(copy: Copy) -> None:
    planted(copy)
    write(copy.root / DATA, json.dumps(bound("calibration", rules={})))
    (why,) = copy.answered("deck")["why"]
    assert "the accepted calibration's data cannot be read" in why


# --- a rule's text ------------------------------------------------------------------------------


def test_a_rules_text_runs_from_its_heading_to_the_next_of_its_level_outside_fenced_code(
    copy: Copy, tmp_path: Path
) -> None:
    path = write(
        tmp_path / "set.md",
        "---\nrule-set: X\n---\n\n# X\n\n## RS-X-0010 — Not this one\n\nNo.\n\n"
        "## RS-X-001 — This one\n\nIt says.\n\n```\n## RS-X-002 in a fence\n```\n\n"
        "### A part of it\n\nMore.\n\n\n## RS-X-002 — The next\n\nNo.\n",
    )
    assert copy.bar.rule_text(path, "RS-X-001") == (
        "## RS-X-001 — This one\n\nIt says.\n\n```\n## RS-X-002 in a fence\n```\n\n"
        "### A part of it\n\nMore.\n"
    )
    assert copy.bar.rule_text(path, "RS-X-003") == ""


# --- the code's digest --------------------------------------------------------------------------


def test_the_codes_digest_leaves_out_no_file_shipped_in_the_scripts_folder_but_a_marker(
    copy: Copy,
) -> None:
    """Each file the capability ships in its scripts folder is a program file the code's
    digest takes, or a folder's marker. A program file of another kind fails here, in the
    change that brings it, so that change decides how the digest sees it (DEC-065 point 2)."""
    scripts = CAPABILITY / "scripts"
    listed = subprocess.run(
        ["git", "ls-files", "-z", "--", str(scripts.relative_to(REPO))],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    shipped = [REPO / each for each in listed.split("\0") if each]
    taken = [path for path in shipped if copy.calibration.is_code(path)]
    assert taken, "the digest takes no file the capability ships in its scripts folder"
    left_out = [
        path.relative_to(scripts).as_posix()
        for path in shipped
        if not copy.calibration.is_code(path) and path.name != MARKER
    ]
    assert left_out == [], (
        f"the code's digest leaves out {left_out}: say how it sees a program file of their "
        f"kind (DEC-065 point 2)"
    )


# --- the accepted calibration's data ------------------------------------------------------------


def _data(**fields: Any) -> dict[str, Any]:
    reading = {
        "rules": {"RS-GRAPHIC-001": {"major": 1, "text": f"sha256:{'a' * 64}"}},
        "reviewer": f"sha256:{'b' * 64}",
        "design-knowledge": f"sha256:{'c' * 64}",
        "code": f"sha256:{'d' * 64}",
        "checks": f"sha256:{'e' * 64}",
        "model": {"name": "a-model-1.0"},
    }
    return bound("calibration", **{**reading, **fields})


def test_the_data_takes_its_shape(copy: Copy) -> None:
    assert copy.files.shape_problems(_data(), "calibration") == []


@pytest.mark.parametrize("key", ["code", "checks"])
def test_the_data_without_a_digest_of_the_code_or_the_list_is_refused(copy: Copy, key: str) -> None:
    data = _data()
    del data[key]
    assert copy.files.shape_problems(data, "calibration") != []


@pytest.mark.parametrize(
    "fields",
    [
        {"rules": {}},
        {"rules": {"COMM": {"major": 1, "text": f"sha256:{'a' * 64}"}}},
        {"rules": {"RS-GRAPHIC-001": {"major": 1}}},
        {"rules": {"RS-GRAPHIC-001": {"major": -1, "text": f"sha256:{'a' * 64}"}}},
        {"rules": {"RS-GRAPHIC-001": {"major": 1, "text": "a" * 64}}},
        {"reviewer": f"sha256:{'B' * 64}"},
        {"design-knowledge": "sha256:abc"},
        {"code": f"sha256:{'D' * 64}"},
        {"checks": None},
        {"model": {"effort": "high"}},
        {"grades": []},
    ],
)
def test_the_data_refuses_another_shape(copy: Copy, fields: dict[str, Any]) -> None:
    assert copy.files.shape_problems(_data(**fields), "calibration") != []
