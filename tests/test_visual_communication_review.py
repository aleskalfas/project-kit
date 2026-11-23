"""The reviewer's report: the document it opens its report with (visual-communication
DEC-070 point 5, #3152).

Held here:

- **its schema**: each finding, a fault, a rule finding, a brief finding or a note, on a
  page or for the piece, with its evidence; a rule finding cites one rule at least and is
  labelled settled or for a person, and no other kind carries a label; a brief finding and
  a note cite no rule; each finding says whether it is a thing a reader cannot make out;
  the marks the review alone sets, a need or the asker's; what it read before writing its
  findings and after; the full name of the model it ran on; strict in every mapping, the
  methodology's container kept free in each; and no grade, no bar, no verdict and no
  number but the format's and the round's;
- **its words**: the reference instance writes each value the schema gives as words as a
  folded block scalar, which parses words that hold `: ` or open with a quoted phrase, as
  the reviewer's body asks (#3391);
- **the reviewer's body** lists a place for each rule the capability ships, and the places
  match what the rule-set files say they judge; its report opens with the document, then
  says what it looked at, then gives its findings;
- **where the reports are kept**: the agent's body, the pages of the capability and the
  schema name one folder, in the clone's local folder, which keeps each round's report
  whole, as the reviewer wrote it, and beside it its document alone.

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
from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import FoldedScalarString

from tests.in_process import load
from tests.visual_communication_project import CAPABILITY, SCHEMAS, bound

(files, reading) = load("visual-communication", "files", "reading")

REVIEWER = CAPABILITY / "agents" / "graphic-design-reviewer.md"
RULE_SETS = CAPABILITY / "rule-sets"

#: Where a round's report is kept, relative to the capability's folder: the whole report as the
#: reviewer wrote it, and beside it its document alone.
KEPT_FOLDER = "project/local/reviews/<piece>/"
KEPT_REPORT = f"{KEPT_FOLDER}round-<n>.md"
KEPT_DOCUMENT = f"{KEPT_FOLDER}round-<n>.yaml"

#: The four kinds of finding (DEC-030 point 6), and the two labels of a rule finding.
KINDS = ("fault", "rule", "brief", "note")
LABELS = ("settled", "for-a-person")


def instance() -> dict[str, Any]:
    return reading.read_yaml(SCHEMAS / "review.yaml")


def refused(data: Any) -> list[str]:
    return files.shape_problems(data, "review")


def finding(kind: str = "rule", **fields: Any) -> dict[str, Any]:
    """The least a finding of `kind` holds, then `fields`."""
    least: dict[str, Any] = {
        "kind": kind,
        "on": {"page": "cover"},
        "reader-cannot-make-out": False,
        "evidence": "The lead does not answer the title.",
    }
    if kind == "rule":
        least |= {"rules": ["RS-COMM-001"], "label": "for-a-person"}
    return {**least, **fields}


def minimal(**fields: Any) -> dict[str, Any]:
    """The least a report holds, then `fields`."""
    return bound(
        "review",
        piece="deck",
        round=1,
        model={"name": "a-model-1.0"},
        **{
            "read-before-findings": [{"kind": "images", "what": "Every image."}],
            "findings": [finding()],
            **fields,
        },
    )


# --- its schema ---------------------------------------------------------------------------------


def test_the_reference_instance_holds_and_shows_each_part_of_a_report() -> None:
    data = instance()
    assert refused(data) == []
    assert data["model"].keys() == {"name", "effort"}
    assert {read["kind"] for read in data["read-after-findings"]} == {
        "brief-file",
        "earlier-reports",
    }
    found = data["findings"]
    assert {each["kind"] for each in found} == set(KINDS)
    assert {each["label"] for each in found if each["kind"] == "rule"} == set(LABELS)
    assert {each["reader-cannot-make-out"] for each in found} == {True, False}
    assert any(len(each.get("rules", ())) > 1 for each in found)
    assert any(each["kind"] == "fault" and each.get("rules") for each in found)
    assert any("page" in each["on"] for each in found)
    assert any("piece" in each["on"] for each in found)
    assert any("mark" in each for each in found)


def test_a_report_of_what_it_must_hold_alone_holds() -> None:
    assert refused(minimal()) == []


def test_a_report_that_found_nothing_holds() -> None:
    assert refused(minimal(findings=[])) == []


@pytest.mark.parametrize("field", ["piece", "round", "model", "read-before-findings", "findings"])
def test_a_report_without_one_of_its_required_parts_is_refused(field: str) -> None:
    data = minimal()
    del data[field]
    assert refused(data)


@pytest.mark.parametrize("kind", KINDS)
def test_each_of_the_four_kinds_of_finding_holds(kind: str) -> None:
    assert refused(minimal(findings=[finding(kind)])) == []


@pytest.mark.parametrize("kind", ["grade", "verdict", "Fault", "rule-finding", 3])
def test_no_other_kind_of_finding_holds(kind: Any) -> None:
    data = minimal()
    data["findings"][0]["kind"] = kind
    assert refused(data)


@pytest.mark.parametrize("label", LABELS)
def test_a_rule_finding_is_settled_or_for_a_person(label: str) -> None:
    assert refused(minimal(findings=[finding(label=label)])) == []


@pytest.mark.parametrize("label", ["informs", "binds", "for a person", "professional", True])
def test_no_other_label_holds(label: Any) -> None:
    assert refused(minimal(findings=[finding(label=label)]))


@pytest.mark.parametrize("field", ["rules", "label"])
def test_a_rule_finding_cites_a_rule_and_carries_its_label(field: str) -> None:
    data = minimal()
    del data["findings"][0][field]
    assert refused(data)
    assert refused(minimal(findings=[finding(rules=[])]))


@pytest.mark.parametrize("kind", ["fault", "brief", "note"])
def test_only_a_rule_finding_carries_a_label(kind: str) -> None:
    assert refused(minimal(findings=[finding(kind, label="settled")]))


def test_a_fault_cites_the_rule_that_names_its_defect_or_none() -> None:
    assert refused(minimal(findings=[finding("fault", rules=["RS-GRAPHIC-002"])])) == []
    assert refused(minimal(findings=[finding("fault")])) == []


@pytest.mark.parametrize("kind", ["brief", "note"])
def test_a_brief_finding_and_a_note_cite_no_rule(kind: str) -> None:
    assert refused(minimal(findings=[finding(kind, rules=["RS-COMM-001"])]))


def test_one_observation_that_fails_several_rules_is_one_finding_that_cites_each() -> None:
    cites = finding(rules=["RS-GRAPHIC-001", "RS-GRAPHIC-007"])
    assert refused(minimal(findings=[cites])) == []
    twice = finding(rules=["RS-GRAPHIC-001", "RS-GRAPHIC-001"])
    assert refused(minimal(findings=[twice]))


def test_each_finding_says_whether_a_reader_cannot_make_it_out() -> None:
    for kind in KINDS:
        for value in (True, False):
            data = minimal(findings=[finding(kind, **{"reader-cannot-make-out": value})])
            assert refused(data) == [], (kind, value)
        data = minimal(findings=[finding(kind)])
        del data["findings"][0]["reader-cannot-make-out"]
        assert refused(data), kind
    for value in ("yes", 1, None):
        data = minimal()
        data["findings"][0]["reader-cannot-make-out"] = value
        assert refused(data), value


def test_a_finding_is_of_a_page_or_of_the_piece_and_never_of_both_or_neither() -> None:
    for place in ({"piece": True}, {"page": "layers"}):
        assert refused(minimal(findings=[finding(on=place)])) == []
    for place in ({}, {"page": "layers", "piece": True}, {"piece": False}, {"slide": "a"}):
        assert refused(minimal(findings=[finding(on=place)])), place


@pytest.mark.parametrize("rule", ["comm-001", "RS-COMM-1", "RS-COMM-0001", "COMM@1", ""])
def test_a_rule_is_named_by_its_id(rule: str) -> None:
    assert refused(minimal(findings=[finding(rules=[rule])]))


@pytest.mark.parametrize("rule", ["RS-COMM-001", "RS-A11Y-001", "RS-X-1000"])
def test_any_id_the_rule_set_grammar_gives_holds(rule: str) -> None:
    """A project's own set may carry a digit in its name, and a set may pass its thousandth rule:
    the review cites any rule it reads, so the report takes any id the core's grammar gives."""
    assert refused(minimal(findings=[finding(rules=[rule])])) == []


def test_a_finding_holds_its_evidence() -> None:
    data = minimal()
    del data["findings"][0]["evidence"]
    assert refused(data)
    data["findings"][0]["evidence"] = "  "
    assert refused(data)


def test_a_mark_is_a_need_or_the_askers_and_names_what_it_asks_for() -> None:
    for kind in KINDS:
        for mark in ("need", "asker"):
            data = minimal(findings=[finding(kind, mark={"kind": mark, "names": "What it needs."})])
            assert refused(data) == [], (kind, mark)
    data = minimal()
    data["findings"][0]["mark"] = {"kind": "waived", "names": "Why."}
    assert refused(data)
    data["findings"][0]["mark"] = {"kind": "need"}
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
    data["read-before-findings"] = [
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
    data["read-before-findings"] = [{"kind": "hunch", "what": "Something."}]
    assert refused(data)
    data["read-before-findings"] = []
    assert refused(data)


def test_the_binding_and_each_mapping_refuse_what_they_do_not_name_but_the_container() -> None:
    for key, value in (
        ("bar", {"at-least": "professional"}),
        ("verdict", "pass"),
        ("grades", [{"rule": "RS-COMM-001", "grade": "professional"}]),
        ("not-graded", []),
        ("read-before-grading", [{"kind": "images", "what": "Every image."}]),
    ):
        data = minimal()
        data[key] = value
        assert refused(data), key
    data = minimal()
    data["pkit"] = {"anything": 1}
    data["findings"][0]["pkit"] = {"anything": 1}
    data["model"]["pkit"] = {"anything": 1}
    assert refused(data) == []
    for key, value in (("grade", "professional"), ("score", 3), ("other-cause", "The frame.")):
        data = minimal()
        data["findings"][0][key] = value
        assert refused(data), key
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


def _names(schema: Any) -> Iterator[str]:
    """Each property and definition `schema` names, anywhere within it."""
    if isinstance(schema, dict):
        for key in ("properties", "$defs"):
            yield from schema.get(key, {})
        for value in schema.values():
            yield from _names(value)
    elif isinstance(schema, list):
        for value in schema:
            yield from _names(value)


def test_nothing_in_it_holds_a_grade_a_bar_or_a_number_but_the_formats_and_the_rounds() -> None:
    schema = json.loads((SCHEMAS / "review.schema.json").read_text(encoding="utf-8"))
    numbers = [leaf for leaf in _leaves(schema) if leaf.get("type") in ("number", "integer")]
    assert numbers == [schema["properties"]["schema_version"], schema["properties"]["round"]]
    named = set(_names(schema))
    assert not {name for name in named if re.search("grade|bar|verdict", name)}, named


# --- the reviewer's body ------------------------------------------------------------------------


def body() -> str:
    return REVIEWER.read_text(encoding="utf-8")


def section(heading: str) -> str:
    """The body's section under `## <heading>`, up to the next of its level."""
    text = body()
    start = text.index(f"## {heading}")
    return text[start : text.index("\n## ", start + 1)]


def grades_section() -> str:
    return section("Grades")


def rule_ids(path: str) -> list[str]:
    text = (RULE_SETS / path).read_text(encoding="utf-8")
    return sorted(set(re.findall(r"^## (RS-[A-Z]+-\d{3}) ", text, flags=re.MULTILINE)))


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

    def step(opening: str) -> int:
        return next(n for n, line in steps.items() if line.startswith(f"**{opening}"))

    deferring = step("Read the intent, the rules and the design knowledge, but not the brief's")
    grading = step("Write your grades")
    reading_last = step("Read the brief's file and your earlier reports last.**")
    assert deferring < grading < reading_last
    deferral = "Leave the brief's file and your earlier reports until you read them last"
    assert deferral in steps[deferring]
    assert not re.search(r"\bsteps? \d", steps[deferring])


def test_the_report_opens_with_its_document_then_what_was_looked_at_then_the_findings() -> None:
    report = section("Your report")
    document = report.index("bound to `visual-communication:review`")
    looked_at = report.index("Looked at: <piece>")
    findings = report.index("FAULT <number")
    assert document < looked_at < findings
    assert "Its report opens with a document of a fixed form" in body()


def test_the_body_keeps_the_reports_where_the_pages_of_the_capability_say() -> None:
    prefix = ".pkit/capabilities/visual-communication/"
    outputs = (CAPABILITY / "outputs.md").read_text(encoding="utf-8")
    files_page = (CAPABILITY / "files.md").read_text(encoding="utf-8")
    assert f"{prefix}{KEPT_FOLDER}" in body()
    for kept in (KEPT_REPORT, KEPT_DOCUMENT):
        assert kept.rsplit("/", 1)[1] in body(), kept
        assert f"{prefix}{kept}" in outputs, kept
        assert kept.rsplit("/", 1)[1] in files_page, kept
    assert KEPT_FOLDER.split("/local/")[1] in files_page
    assert "clone's local folder" in outputs


def test_the_body_reads_the_whole_reports_of_earlier_rounds_and_keeps_the_document_alone() -> None:
    reading_section = section("What you read")
    earlier = next(
        line for line in reading_section.splitlines() if "reports of earlier rounds" in line
    )
    assert "`round-<n>.md`, the whole report" in earlier
    assert "Read each round's whole report, `round-<n>.md`" in earlier
    report = section("Your report")
    assert "**`round-<n>.md`** holds the whole report" in report
    assert "**`round-<n>.yaml`** holds the grades' document alone" in report


def test_the_reference_instance_reads_the_whole_report_of_the_round_before() -> None:
    earlier = [
        read["what"]
        for read in instance()["read-after-findings"]
        if read["kind"] == "earlier-reports"
    ]
    assert earlier and all("round-1.md" in what for what in earlier)


def test_the_body_names_the_schema_it_reports_in_and_that_schema_ships() -> None:
    text = body()
    assert "schemas/review.schema.json" in text
    assert "visual-communication:review" in text
    assert (SCHEMAS / "review.schema.json").is_file()
    assert (SCHEMAS / "review.yaml").is_file()


#: The schema's own type for a value in words.
TEXT = "defs.schema.json#/$defs/text"


def words_keys(schema: Any) -> set[str]:
    """Each key whose value the schema gives as words, anywhere within `schema`."""
    found: set[str] = set()
    if isinstance(schema, dict):
        for key, value in schema.get("properties", {}).items():
            if isinstance(value, dict) and value.get("$ref") == TEXT:
                found.add(key)
        for value in schema.values():
            found |= words_keys(value)
    return found


def written_in_words(data: Any, keys: set[str]) -> Iterator[tuple[str, Any]]:
    """Each value of `data`, as the round-trip reader reads it, under one of `keys`."""
    if isinstance(data, dict):
        for key, value in data.items():
            if key in keys:
                yield key, value
            yield from written_in_words(value, keys)
    elif isinstance(data, list):
        for value in data:
            yield from written_in_words(value, keys)


def test_the_reference_instance_writes_each_value_in_words_as_a_block_scalar() -> None:
    """A value in words written plain does not parse where it holds `: ` or opens with a
    quoted phrase and goes on after it, so the body has each written as a folded block
    scalar, and the reference instance shows that form for every one (#3391)."""
    schema = json.loads((SCHEMAS / "review.schema.json").read_text(encoding="utf-8"))
    keys = words_keys(schema)
    assert keys == {"name", "effort", "what", "names", "evidence"}
    data = YAML().load((SCHEMAS / "review.yaml").read_text(encoding="utf-8"))
    written = list(written_in_words(data, keys))
    assert {key for key, _ in written} == keys
    plain = [(key, value) for key, value in written if not isinstance(value, FoldedScalarString)]
    assert plain == []
    assert any(": " in value and value.startswith('"') for _, value in written)
    rule = next(
        line
        for line in section("Your report").splitlines()
        if line.startswith("**Each value in words, as a block scalar.**")
    )
    assert "`>-`" in rule
    assert "`review.yaml`" in rule
    for key in keys:
        assert f"`{key}`" in rule, key


def test_the_reference_instance_is_not_changed_by_a_check_of_it() -> None:
    data = instance()
    before = copy.deepcopy(data)
    refused(data)
    assert data == before
