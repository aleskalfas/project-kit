"""`pkit visual intent <piece>` (visual-communication DEC-070 point 5, #3223).

Held here:

- **what it hands the review**: the goals, relations and takeaways of the piece and of each
  page the brief speaks of, a relation with the parts it relates;
- **no reason**: a brief that holds reasons yields none of their words, aspects or
  principles, in the words printed or in the document;
- **a piece without intent**: a part that states nothing is named so, and a piece with no
  brief is said to keep none;
- **only a read**: nothing is written.

The commands run in the test's own process (`tests/in_process.py`).
"""

from __future__ import annotations

import json
from pathlib import Path

from tests.in_process import load, run_main
from tests.test_visual_communication_checks import deck_project
from tests.test_visual_communication_pipeline import PIECE_FOLDER
from tests.visual_communication_project import bound, write, yaml_text

(intent,) = load("visual-communication", "intent.py")

BRIEF = f"{PIECE_FOLDER}/brief.yaml"
PIECE = Path(PIECE_FOLDER).name

#: The words each reason holds, none of which the command may print.
REASONS = [
    {
        "aspect": "form",
        "about": "visual.steps",
        "text": "A stepped pyramid carries the order by width.",
        "principle": {"name": "Ordered visual variables", "source": "A book by Bertin."},
    },
    {
        "aspect": "colour",
        "text": "One accent marks the source.",
        "principle": {"name": "Selective emphasis", "source": "A paper by Ware."},
    },
]
LEAKS = [
    "stepped pyramid",
    "One accent",
    "Ordered visual variables",
    "Bertin",
    "Selective emphasis",
    "Ware",
    "aspect",
    "reason",
]


def write_brief(root: Path, **parts: object) -> None:
    write(root / BRIEF, yaml_text(bound("brief", **parts)))


def handed(root: Path, *flags: str) -> str:
    done = run_main(intent, *flags, PIECE, cwd=root)
    assert done.returncode == 0, done.stderr
    return done.stdout


def test_it_prints_the_goals_relations_and_takeaways_of_the_piece_and_of_each_page(
    tmp_path: Path,
) -> None:
    root = deck_project(tmp_path)
    write_brief(
        root,
        piece={
            "goals": ["A newcomer can say where a decision lives."],
            "relations": [{"text": "A cover, then rules.", "relates": ["slides[cover].title"]}],
        },
        pages={
            "cover": {"takeaway": "What the talk is about."},
            "rules": {
                "goals": ["The reader can name a step."],
                "relations": [{"text": "One step after another."}],
            },
        },
    )
    assert handed(root).splitlines() == [
        "the piece:",
        "  goal: A newcomer can say where a decision lives.",
        "  relation: A cover, then rules. (relates: slides[cover].title)",
        "page cover:",
        "  takeaway: What the talk is about.",
        "page rules:",
        "  goal: The reader can name a step.",
        "  relation: One step after another.",
    ]


def test_a_brief_with_reasons_yields_none_of_them(tmp_path: Path) -> None:
    root = deck_project(tmp_path)
    write_brief(
        root,
        piece={
            "goals": ["A goal."],
            "relations": [{"text": "A relation."}],
            "takeaway": "A point.",
            "reasons": REASONS,
        },
        pages={"rules": {"takeaway": "A page point.", "reasons": REASONS}},
    )
    for printed in (handed(root), handed(root, "--json")):
        assert "A goal." in printed and "A page point." in printed
        for leaked in LEAKS:
            assert leaked not in printed
    document = json.loads(handed(root, "--json"))["intent"]
    for part in [document["piece"], *document["pages"].values()]:
        assert set(part) <= {"goals", "relations", "takeaway"}


def test_a_part_that_states_nothing_is_named_so(tmp_path: Path) -> None:
    root = deck_project(tmp_path)
    write_brief(root, piece={"reasons": REASONS}, pages={"cover": {"reasons": REASONS}})
    assert handed(root).splitlines() == [
        "the piece:",
        "  (states no goal, relation or takeaway)",
        "page cover:",
        "  (states no goal, relation or takeaway)",
    ]


def test_a_piece_with_no_brief_is_said_to_keep_none(tmp_path: Path) -> None:
    root = deck_project(tmp_path)
    assert "keeps no brief" in handed(root)
    assert json.loads(handed(root, "--json"))["intent"] is None


def test_it_writes_nothing(tmp_path: Path) -> None:
    root = deck_project(tmp_path)
    write_brief(root, piece={"goals": ["A goal."]})
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    handed(root)
    assert {p: p.read_bytes() for p in root.rglob("*") if p.is_file()} == before


def test_a_piece_the_location_lacks_is_refused(tmp_path: Path) -> None:
    root = deck_project(tmp_path)
    done = run_main(intent, "no-such-piece", cwd=root)
    assert done.returncode == 1
    assert "no-such-piece" in done.stderr
