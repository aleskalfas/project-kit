"""The reviewer's report: the document it opens its grades with (visual-communication
DEC-042 points 1 and 4, #3152).

Held here:

- **its schema**: a grade in one of four words for each rule, on a page or for the piece,
  with its evidence; the marks the review alone sets, a need or the asker's; what it read
  before grading and after; the full name of the model it ran on; strict in every mapping,
  the methodology's container kept free in each; and no bar, no value and no number but the
  format's and the round's;
- **the reviewer's body** lists a place for each rule the capability ships, and the places
  match what the rule-set files say they judge;
- **where the reports are kept**: the agent's body, the pages of the capability and the
  schema name one folder, in the clone's local folder.

The schema is read through the capability's own `files.shape_problems`, in the test's own
process (`tests/in_process.py`).
"""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Iterator
from typing import Any

import pytest

from tests.in_process import load
from tests.visual_communication_project import CAPABILITY, SCHEMAS, bound

(files, reading) = load("visual-communication", "files", "reading")

REVIEWER = CAPABILITY / "agents" / "graphic-design-reviewer.md"
RULE_SETS = CAPABILITY / "rule-sets"

#: Where a round's report is kept, relative to the capability's folder.
KEPT = "project/local/reviews/<piece>/round-<n>.yaml"


def instance() -> dict[str, Any]:
    return reading.read_yaml(SCHEMAS / "review.yaml")


def refused(data: Any) -> list[str]:
    return files.shape_problems(data, "review")


def minimal(**fields: Any) -> dict[str, Any]:
    """The least a report holds, then `fields`."""
    return bound(
        "review",
        piece="deck",
        round=1,
        model={"name": "a-model-1.0"},
        **{
            "read-before-grading": [{"kind": "images", "what": "Every image."}],
            "grades": [
                {
                    "rule": "RS-COMM-001",
                    "on": {"page": "cover"},
                    "grade": "professional",
                    "evidence": "The lead answers the title.",
                }
            ],
            **fields,
        },
    )


# --- its schema ---------------------------------------------------------------------------------


def test_the_reference_instance_holds_and_shows_each_part_of_a_report() -> None:
    data = instance()
    assert refused(data) == []
    assert data["model"].keys() == {"name", "effort"}
    assert {read["kind"] for read in data["read-after-grading"]} == {
        "brief-file",
        "earlier-reports",
    }
    grades = data["grades"]
    assert {grade["grade"] for grade in grades} >= {"competent", "professional"}
    assert any("page" in grade["on"] for grade in grades)
    assert any("piece" in grade["on"] for grade in grades)
    assert any("mark" in grade for grade in grades)
    assert any("since-last-round" in grade for grade in grades)
    assert data["not-graded"]


def test_a_report_of_what_it_must_hold_alone_holds() -> None:
    assert refused(minimal()) == []


@pytest.mark.parametrize("field", ["piece", "round", "model", "read-before-grading", "grades"])
def test_a_report_without_one_of_its_required_parts_is_refused(field: str) -> None:
    data = minimal()
    del data[field]
    assert refused(data)


@pytest.mark.parametrize("word", ["below competent", "competent", "professional", "excellent"])
def test_each_of_the_four_grades_holds(word: str) -> None:
    data = minimal()
    data["grades"][0]["grade"] = word
    assert refused(data) == []


@pytest.mark.parametrize("word", ["fail", "pass", "good", "Professional", "below-competent", 3])
def test_no_other_grade_holds(word: Any) -> None:
    data = minimal()
    data["grades"][0]["grade"] = word
    assert refused(data)


def test_a_grade_is_of_a_page_or_of_the_piece_and_never_of_both_or_neither() -> None:
    for place in ({"piece": True}, {"page": "layers"}):
        data = minimal()
        data["grades"][0]["on"] = place
        assert refused(data) == []
    for place in ({}, {"page": "layers", "piece": True}, {"piece": False}, {"slide": "a"}):
        data = minimal()
        data["grades"][0]["on"] = place
        assert refused(data), place


@pytest.mark.parametrize("rule", ["comm-001", "RS-COMM-1", "RS-COMM-0001", "COMM@1", ""])
def test_a_rule_is_named_by_its_id(rule: str) -> None:
    data = minimal()
    data["grades"][0]["rule"] = rule
    assert refused(data)


def test_a_grade_holds_its_evidence() -> None:
    data = minimal()
    del data["grades"][0]["evidence"]
    assert refused(data)
    data["grades"][0]["evidence"] = "  "
    assert refused(data)


def test_a_mark_is_a_need_or_the_askers_and_names_what_it_asks_for() -> None:
    for kind in ("need", "asker"):
        data = minimal()
        data["grades"][0]["mark"] = {"kind": kind, "names": "What it needs."}
        assert refused(data) == []
    data = minimal()
    data["grades"][0]["mark"] = {"kind": "waived", "names": "Why."}
    assert refused(data)
    data["grades"][0]["mark"] = {"kind": "need"}
    assert refused(data)


def test_a_grade_that_differs_from_the_round_before_says_what_it_was_and_why() -> None:
    data = minimal()
    data["grades"][0]["since-last-round"] = {"was": "competent", "why": "The figure now shows it."}
    assert refused(data) == []
    del data["grades"][0]["since-last-round"]["why"]
    assert refused(data)
    data["grades"][0]["since-last-round"] = {"was": "fine", "why": "Why."}
    assert refused(data)


def test_a_round_numbers_from_1() -> None:
    for number in (0, -1, 1.5, "1"):
        data = minimal()
        data["round"] = number
        assert refused(data), number


def test_the_model_holds_its_full_name_and_its_effort_only_where_the_harness_has_one() -> None:
    data = minimal()
    data["model"] = {"name": "a-model-1.0", "effort": "high"}
    assert refused(data) == []
    data["model"] = {"effort": "high"}
    assert refused(data)
    data["model"] = {"name": "a-model-1.0", "version": "1"}
    assert refused(data)


def test_what_was_read_is_named_by_a_kind_the_schema_lists() -> None:
    data = minimal()
    data["read-before-grading"] = [
        {"kind": kind, "what": "Something."}
        for kind in (
            "images",
            "frames",
            "report",
            "piece",
            "brand",
            "intent",
            "rule-sets",
            "design-knowledge",
            "sources",
            "brief-file",
            "earlier-reports",
        )
    ]
    assert refused(data) == []
    data["read-before-grading"] = [{"kind": "hunch", "what": "Something."}]
    assert refused(data)
    data["read-before-grading"] = []
    assert refused(data)


def test_a_rule_not_graded_names_the_place_and_why() -> None:
    data = minimal(
        **{"not-graded": [{"rule": "RS-COMM-003", "on": {"piece": True}, "why": "One page."}]}
    )
    assert refused(data) == []
    data = minimal(**{"not-graded": [{"rule": "RS-COMM-003", "on": {"piece": True}}]})
    assert refused(data)


def test_the_binding_and_each_mapping_refuse_what_they_do_not_name_but_the_container() -> None:
    data = minimal()
    data["bar"] = {"at-least": "professional"}
    assert refused(data)
    data = minimal()
    data["verdict"] = "pass"
    assert refused(data)
    data = minimal()
    data["pkit"] = {"anything": 1}
    data["grades"][0]["pkit"] = {"anything": 1}
    data["model"]["pkit"] = {"anything": 1}
    assert refused(data) == []
    data = minimal()
    data["grades"][0]["score"] = 3
    assert refused(data)
    assert refused({**minimal(), "pkit_schema": "visual-communication:brief"})


def _leaves(schema: Any) -> Iterator[Any]:
    """Each schema within `schema` that declares a value's type, or refers to another."""
    if isinstance(schema, dict):
        if "type" in schema or "$ref" in schema or "enum" in schema or "const" in schema:
            yield schema
        for value in schema.values():
            yield from _leaves(value)
    elif isinstance(schema, list):
        for value in schema:
            yield from _leaves(value)


def test_nothing_in_it_holds_a_bar_or_a_number_but_the_formats_and_the_rounds() -> None:
    schema = json.loads((SCHEMAS / "review.schema.json").read_text(encoding="utf-8"))
    numbers = [leaf for leaf in _leaves(schema) if leaf.get("type") in ("number", "integer")]
    assert numbers == [schema["properties"]["schema_version"], schema["properties"]["round"]]
    assert "bar" not in schema["properties"]


# --- the reviewer's body ------------------------------------------------------------------------


def body() -> str:
    return REVIEWER.read_text(encoding="utf-8")


def grades_section() -> str:
    text = body()
    start = text.index("## Grades")
    return text[start : text.index("\n## ", start + 1)]


def rule_ids(path: str) -> list[str]:
    text = (RULE_SETS / path).read_text(encoding="utf-8")
    return sorted(set(re.findall(r"^## (RS-[A-Z]+-\d{3}) ", text, flags=re.MULTILINE)))


def test_the_body_gives_each_grade_in_the_words_the_schema_holds() -> None:
    section = grades_section()
    schema = json.loads((SCHEMAS / "review.schema.json").read_text(encoding="utf-8"))
    for word in schema["$defs"]["grade-word"]["enum"]:
        assert f"*{word}*" in section, word


def test_the_body_places_each_rule_the_capability_ships_in_one_list() -> None:
    section = grades_section()
    for rule in (*rule_ids("comm.md"), *rule_ids("graphic.md")):
        assert section.count(rule) >= 1, rule
    lines = {
        line.split(":**")[0].strip("- *"): line
        for line in section.splitlines()
        if line.strip().startswith(
            ("- **For the piece", "- **On each page and", "- **On each page:")
        )
    }
    assert len(lines) == 3
    piece = lines["For the piece, once"]
    both = lines["On each page and for the piece"]
    page = lines["On each page"]
    assert re.findall(r"RS-[A-Z]+-\d{3}", piece) == ["RS-COMM-003"]
    assert re.findall(r"RS-[A-Z]+-\d{3}", both) == ["RS-COMM-002", "RS-GRAPHIC-004"]
    assert "RS-COMM-003" not in page


def test_the_body_reads_the_briefs_file_and_the_earlier_reports_only_after_the_grades() -> None:
    text = body()
    working = text[text.index("## How you work") : text.index("## The list of faults")]
    steps = {int(n): line for n, line in re.findall(r"^(\d+)\. (.+)$", working, flags=re.MULTILINE)}
    grading = next(n for n, line in steps.items() if line.startswith("**Write your grades"))
    reading_last = next(
        n for n, line in steps.items() if line.startswith("**Read the brief's file")
    )
    assert grading < reading_last
    assert f"step {reading_last}" in steps[4]


def test_the_body_keeps_the_reports_where_the_pages_of_the_capability_say() -> None:
    folder = f".pkit/capabilities/visual-communication/{KEPT}"
    assert folder in body()
    assert KEPT.split("/local/")[1].rsplit("/", 1)[0] + "/" in (CAPABILITY / "files.md").read_text(
        encoding="utf-8"
    )
    assert folder in (CAPABILITY / "outputs.md").read_text(encoding="utf-8")
    assert "clone's local folder" in (CAPABILITY / "outputs.md").read_text(encoding="utf-8")


def test_the_body_names_the_schema_it_reports_in_and_that_schema_ships() -> None:
    text = body()
    assert "schemas/review.schema.json" in text
    assert "visual-communication:review" in text
    assert (SCHEMAS / "review.schema.json").is_file()
    assert (SCHEMAS / "review.yaml").is_file()


def test_the_reference_instance_is_not_changed_by_a_check_of_it() -> None:
    data = instance()
    before = copy.deepcopy(data)
    refused(data)
    assert data == before
