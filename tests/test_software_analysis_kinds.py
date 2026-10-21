"""software-analysis: each kind's structure, declared as data (#1363).

Held to software-analysis DEC-001 points 1 and 6, and to the parts the template
round chose for each kind (#1362):

- **`schemas/artefact-kinds.yaml` fits its schema**, and the schema is a strict
  superset of living-docs' `page-kinds.schema.json`: every declaration living-docs
  writes is accepted with the same meaning, and the analysis's is not one of them;
- **the five kinds hold the round's parts**, keyed by the types the places give and
  by `revalidation-record`, each element with its id, its type, whether it may read
  `None.` and its form, every shipped element required;
- **the three kinds of requirement hold DEC-002's parts** (point 4, #1691): the
  same fields on each, `statement` of the form `sentence`, `measure` the one field
  that may read `None.` and `statement` and `applies-to` two that may not, and
  *Verified by* then *Rationale*, or *Imposed by* on a
  constraint, each of which may read `None.`. Each is shown beside its id by its
  name, `# REQ-007 · Quality · <title>` (point 2);
- **each part has a hint and an example**, one line each, with no semicolon and no
  sentence over 25 words. A heading the stamp writes has an example and no hint;
- **a planned record names its design's sources** in `reviewed-against`, which the
  record's schema requires of a planned record alone, each source's version of the
  form its place gives.

No other code reads the declaration yet, so this module is what holds it.
"""

from __future__ import annotations

import json
import re
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from tests.analysis_repo import CAPABILITY, REPO, below_floor, load

SCHEMAS = CAPABILITY / "schemas"
KINDS = SCHEMAS / "artefact-kinds.yaml"
PAGE_KINDS = REPO / ".pkit" / "capabilities" / "living-docs" / "schemas" / "page-kinds"

#: A commit's full name under SHA-1, and under SHA-256.
SHA1 = "78981922613b2afb6025042ff6bd878ac1994e85"
SHA256 = "4f9be057f0ea5d2ba72fd2c810e8d7b9aa98b469f9a6c4d6d0e2a2d3e1c4b5a6"

#: A time tracker text was read, as a UTC timestamp.
READ_AT = "2026-01-05T10:00:00Z"

#: A link to a text outside this repository.
LINK = "https://tracker.example/issues/42"


def _json(path: Any) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _kinds() -> dict[str, Any]:
    return load(KINDS.read_text(encoding="utf-8"))


def _kinds_schema() -> dict[str, Any]:
    return _json(SCHEMAS / "artefact-kinds.schema.json")


def _messages(schema: dict[str, Any], instance: Any) -> list[str]:
    return [error.message for error in Draft202012Validator(schema).iter_errors(instance)]


# --- the file and its schema ------------------------------------------------------------------


def test_the_declaration_fits_its_schema() -> None:
    schema = _kinds_schema()
    Draft202012Validator.check_schema(schema)
    assert _messages(schema, _kinds()) == []


#: Declarations living-docs' schema accepts: its own file, and the shapes its grammar allows.
LIVING_DOCS_SHAPED = [
    {"schema_version": 1, "kinds": {"reference": {"sections": [{"level": 1}]}}},
    {
        "schema_version": 1,
        "kinds": {
            "guide": {
                "sections": [{"level": 1}, {"level": 2, "text": "Install"}, {"level": 6}],
                "ordered": False,
            },
            "signpost": {"sections": [{"level": 1}], "ordered": True},
        },
    },
]


def test_the_schema_is_a_strict_superset_of_living_docs_page_kinds() -> None:
    """A later move of the reader into the backbone is then a move, not a reconciliation
    (the design behind #1352, part 1): every declaration living-docs' schema accepts, this
    one accepts, and a section that names no type is a heading, as there. Each key that
    schema gives keeps its shape here. The analysis's declaration is beyond it."""
    page_schema = _json(PAGE_KINDS.with_suffix(".schema.json"))
    ours = _kinds_schema()
    living_docs_file = load(PAGE_KINDS.with_suffix(".yaml").read_text(encoding="utf-8"))
    for declaration in [living_docs_file, *LIVING_DOCS_SHAPED]:
        assert _messages(page_schema, declaration) == []
        assert _messages(ours, declaration) == []
    assert _messages(page_schema, _kinds()) != []

    assert ours["properties"]["schema_version"] == page_schema["properties"]["schema_version"]
    assert ours["required"] == page_schema["required"]
    assert ours["$defs"]["word"]["pattern"] == page_schema["$defs"]["word"]["pattern"]
    theirs_kind, our_kind = page_schema["$defs"]["kind"], ours["$defs"]["kind"]
    assert our_kind["required"] == theirs_kind["required"]
    for key in ("type", "default"):
        assert our_kind["properties"]["ordered"][key] == theirs_kind["properties"]["ordered"][key]
    sections = our_kind["properties"]["sections"]
    assert sections["minItems"] == theirs_kind["properties"]["sections"]["minItems"]
    theirs, our = page_schema["$defs"]["section"]["properties"], ours["$defs"]["section"]
    for key in ("minimum", "maximum", "type"):
        assert our["properties"]["level"][key] == theirs["level"][key]
    assert our["properties"]["text"]["pattern"] == theirs["text"]["pattern"]
    assert "required" not in our  # a section of living-docs' names no id and no type


@pytest.mark.parametrize(
    ("element", "fragment"),
    [
        ({"id": "goal", "type": "label", "hint": "H.", "example": "E."}, "'text' is a required"),
        (
            {
                "id": "goal",
                "type": "label",
                "text": "Goal",
                "level": 2,
                "hint": "H.",
                "example": "E.",
            },
            "False schema",
        ),
        ({"id": "opening", "type": "opening", "hint": "H."}, "'example' is a required"),
        (
            {"id": "opening", "type": "opening", "text": "Who", "hint": "H.", "example": "E."},
            "False schema",
        ),
        ({"type": "heading", "level": 1}, "'id' is a dependency of 'type'"),
        ({"id": "heading", "type": "heading"}, "'level' is a required"),
        ({"id": "goal", "type": "aside", "level": 1}, "is not one of"),
        (
            {"id": "goal", "type": "label", "text": "Goal", "hint": "One.\nTwo.", "example": "E."},
            "should not be valid under",
        ),
        (
            {
                "id": "goal",
                "type": "label",
                "text": "Goal",
                "hint": "H.",
                "example": "E.",
                "form": "prose",
            },
            "is not valid under any of the given schemas",
        ),
        (
            {
                "id": "goal",
                "type": "label",
                "text": "Goal",
                "hint": "H.",
                "example": "E.",
                "note": "x",
            },
            "Additional properties are not allowed ('note' was unexpected)",
        ),
        ({"id": "Goal", "type": "heading", "level": 1}, "does not match"),
    ],
    ids=[
        "label-without-text",
        "label-with-a-level",
        "opening-without-example",
        "opening-with-text",
        "typed-without-id",
        "heading-without-level",
        "unknown-type",
        "hint-over-two-lines",
        "unknown-form",
        "unknown-key",
        "id-not-a-word",
    ],
)
def test_the_schema_refuses_an_element_that_is_not_one(
    element: dict[str, Any], fragment: str
) -> None:
    declaration = {"schema_version": 1, "kinds": {"use-case": {"sections": [element]}}}
    messages = _messages(_kinds_schema(), declaration)
    assert any(fragment in message for message in messages), messages


@pytest.mark.parametrize(
    ("kind", "fragment"),
    [
        (
            {"sections": [{"level": 2}], "head": [{"id": "file-heading", "type": "heading"}]},
            "'stamp'",
        ),
        (
            {
                "sections": [{"level": 2}],
                "head": [{"id": "o", "type": "opening", "stamp": "S.", "level": 1}],
            },
            "False schema",
        ),
        ({"sections": [{"level": 2}], "front-matter": {"needs": {"hint": "H."}}}, "'example'"),
        (
            {
                "sections": [{"level": 2}],
                "front-matter": {"needs": {"hint": "H.", "example": "E.", "x": 1}},
            },
            "'x' was unexpected",
        ),
        (
            {
                "sections": [{"level": 2}],
                "front-matter": {"needs": {"hint": "H.", "example": "E.", "form": "free"}},
            },
            "any of the given",
        ),
        ({"sections": [{"level": 2}], "aside": True}, "'aside' was unexpected"),
        (
            {
                "sections": [{"level": 2}],
                "front-matter": {"measure": {"hint": "H.", "example": "E.", "allows-none": "yes"}},
            },
            "is not of type 'boolean'",
        ),
        ({"sections": [{"level": 2}], "shown-as": ""}, "does not match"),
        ({"sections": [{"level": 2}], "shown-as": "Quality\nRequirement"}, "should not be valid"),
    ],
    ids=[
        "head-without-stamp",
        "head-opening-with-level",
        "field-without-example",
        "field-unknown-key",
        "field-unknown-form",
        "kind-unknown-key",
        "field-allows-none-not-a-boolean",
        "shown-as-blank",
        "shown-as-over-two-lines",
    ],
)
def test_the_schema_refuses_a_head_a_field_or_a_kind_that_is_not_one(
    kind: dict[str, Any], fragment: str
) -> None:
    declaration = {"schema_version": 1, "kinds": {"term": kind}}
    messages = _messages(_kinds_schema(), declaration)
    assert any(fragment in message for message in messages), messages


# --- the kinds and their parts (#1362) --------------------------------------------------------


def test_each_kind_is_keyed_by_its_type_and_the_record_by_a_key_of_its_own() -> None:
    """The kinds' keys are the types the capability's places give (#1409), and the
    revalidation record, which has no type, keeps `revalidation-record`."""
    package = load((CAPABILITY / "package.yaml").read_text(encoding="utf-8"))
    types = sorted(package["friction"]["types"])
    assert types == sorted([*FOUR, *REQUIREMENTS, VIEW])
    assert sorted(_kinds()["kinds"]) == sorted([*types, "revalidation-record"])


#: DEC-001's four kinds of anchored artefact, and the three kinds of requirement DEC-002
#: adds, each by the type its place gives.
FOUR = ("actor", "use-case", "journey", "term")
REQUIREMENTS = ("quality-requirement", "functional-requirement", "constraint")

#: The domain-model view DEC-004 adds, by the type its place gives (#1817).
VIEW = "domain-model-view"


#: Each kind's body as the round chose it (#1362, each kind's "Decided" section): each
#: element's id, type, label or fixed heading text, whether it may read `None.`, and form.
PARTS: dict[str, list[tuple[str, str, str | None, bool, str | None]]] = {
    "actor": [
        ("heading", "heading", None, False, None),
        ("opening", "opening", None, False, None),
        ("occasions", "label", "Occasions", True, None),
        ("context", "label", "Context", True, None),
    ],
    "use-case": [
        ("heading", "heading", None, False, None),
        ("goal", "label", "Goal", False, "sentence"),
        ("other-actors", "label", "Other actors", True, None),
        ("preconditions", "label", "Preconditions", True, None),
        ("assumptions", "label", "Assumptions", True, None),
        ("trigger", "label", "Trigger", False, None),
        ("main-path", "label", "Main path", False, "numbered-steps"),
        ("variants", "label", "Variants", True, "variants"),
        ("postconditions", "label", "Postconditions", False, None),
        ("minimal-guarantees", "label", "Minimal guarantees", True, None),
    ],
    "journey": [
        ("heading", "heading", None, False, None),
        ("goal", "label", "Goal", False, "sentence"),
        ("steps", "label", "Steps", False, "steps-match-front-matter"),
        ("variants", "label", "Variants", True, "variants"),
        ("postconditions", "label", "Postconditions", False, None),
        ("minimal-guarantees", "label", "Minimal guarantees", True, None),
    ],
    "term": [
        ("heading", "heading", None, False, None),
        ("example", "label", "Example", True, None),
        ("distinctions", "label", "Distinctions", True, None),
    ],
    "revalidation-record": [
        ("heading", "heading", None, False, None),
        ("outcomes", "heading", "Outcomes", False, "outcomes-match-front-matter"),
        ("gaps", "heading", "Gaps", True, "gaps-match-outcomes"),
    ],
    # DEC-002 point 4: what verifies it, then why it is needed, or on a constraint who
    # imposes it. Each may read `None.`.
    "quality-requirement": [
        ("heading", "heading", None, False, None),
        ("verified-by", "label", "Verified by", True, None),
        ("rationale", "label", "Rationale", True, None),
    ],
    "functional-requirement": [
        ("heading", "heading", None, False, None),
        ("verified-by", "label", "Verified by", True, None),
        ("rationale", "label", "Rationale", True, None),
    ],
    "constraint": [
        ("heading", "heading", None, False, None),
        ("verified-by", "label", "Verified by", True, None),
        ("imposed-by", "label", "Imposed by", True, None),
    ],
    # Its heading, the problem its group's concepts solve with the class diagram, then one
    # section for each concept it explains, headed by its term's name (DEC-004 point 2).
    VIEW: [
        ("heading", "heading", None, False, None),
        ("opening", "opening", None, False, None),
        ("concept", "repeated", None, False, "headings-match-front-matter"),
    ],
}

#: The parts each section of a repeated section holds, in order (DEC-004 point 2): what
#: the concept is for, the explanation of the concept for a newcomer, then its attributes,
#: its relations, its life cycle and what is always true of it. Each but the explanation
#: may read `None.`.
SECTION_PARTS: dict[str, list[tuple[str, str, str | None, bool, str | None]]] = {
    VIEW: [
        ("why", "label", "Why", True, None),
        ("explanation", "opening", None, False, None),
        ("attributes", "label", "Attributes", True, None),
        ("relations", "label", "Relations", True, None),
        ("states", "label", "States", True, None),
        ("always-true", "label", "Always true", True, None),
    ],
}

#: A requirement's front-matter fields, the same on each kind (DEC-002 point 4): its
#: statement in one sentence, its measure, where it holds, its actors and what it refines.
REQUIREMENT_FIELDS: dict[str, str | None] = {
    "statement": "sentence",
    "measure": None,
    "applies-to": None,
    "actors": None,
    "refines": None,
}

#: Each kind's front-matter fields a writer fills, with the form of each (#1362).
FIELDS: dict[str, dict[str, str | None]] = {
    "actor": {"needs": "sentence"},
    "use-case": {},
    "journey": {},
    "term": {
        "name": None,
        "definition": "definition",
        "replaces": None,
        "noun-forms": None,
        "other-senses": None,
    },
    "revalidation-record": {"reviewed-against": None},
    **dict.fromkeys(REQUIREMENTS, REQUIREMENT_FIELDS),
    VIEW: {},
}

#: The fields that say whether they may read `None.`: a requirement's measure may, which
#: a requirement found before its measure reads, and its statement and where it holds may
#: not (DEC-002 point 4). Every other field says neither, so its form alone judges it.
FIELDS_SAYING_NONE = {
    kind: {"statement": False, "measure": True, "applies-to": False} for kind in REQUIREMENTS
}

#: How each kind shows beside its id, where it does (DEC-002 point 2).
SHOWN_AS = {
    "quality-requirement": "Quality",
    "functional-requirement": "Functional",
    "constraint": "Constraint",
}


def _elements(kind: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        *kind.get("head", []),
        *(found for e in kind["sections"] for found in (e, *e.get("sections", []))),
    ]


@pytest.mark.parametrize("name", sorted(PARTS))
def test_each_kind_holds_the_parts_the_round_chose(name: str) -> None:
    """In order, every shipped element required: a part with nothing to say reads
    `None.`, where its element allows it (DEC-001 point 1). The actor is a document,
    headed by its id and name (#1346). Every element names its id and its type."""
    kind = _kinds()["kinds"][name]
    assert kind.get("ordered", True) is True
    declared = [
        (
            element["id"],
            element["type"],
            element.get("text"),
            element.get("allows-none", False),
            element.get("form"),
        )
        for element in kind["sections"]
    ]
    assert declared == PARTS[name]
    nested = {
        element["id"]: [
            (
                part["id"],
                part["type"],
                part.get("text"),
                part.get("allows-none", False),
                part.get("form"),
            )
            for part in element["sections"]
        ]
        for element in kind["sections"]
        if "sections" in element
    }
    assert list(nested.values()) == ([SECTION_PARTS[name]] if name in SECTION_PARTS else [])
    assert all(element.get("required", True) is True for element in _elements(kind))
    ids = [element["id"] for element in _elements(kind)]
    assert len(set(ids)) == len(ids)
    fields = kind.get("front-matter", {})
    assert {field: entry.get("form") for field, entry in fields.items()} == FIELDS[name]
    saying = {f: entry["allows-none"] for f, entry in fields.items() if "allows-none" in entry}
    assert saying == FIELDS_SAYING_NONE.get(name, {})
    assert kind.get("shown-as") == SHOWN_AS.get(name)


def test_the_three_kinds_of_requirement_share_their_fields_and_all_parts_but_one() -> None:
    """Every kind has the same fields and the same parts, save one part, which differs for
    a constraint (DEC-002 point 4): *Imposed by* in the place of *Rationale*. So a
    requirement keeps its fields when it changes kind. Each kind's companion schema
    takes the same fields and requires the same, `statement`, `measure` and `applies-to`
    among them, and its name is the type its place gives."""
    kinds = _kinds()["kinds"]
    fields = {tuple(kinds[name]["front-matter"]) for name in REQUIREMENTS}
    assert fields == {tuple(REQUIREMENT_FIELDS)}
    parts = {name: [e["id"] for e in kinds[name]["sections"]] for name in REQUIREMENTS}
    assert parts["quality-requirement"] == parts["functional-requirement"]
    assert parts["constraint"][:-1] == parts["quality-requirement"][:-1]
    assert (parts["quality-requirement"][-1], parts["constraint"][-1]) == (
        "rationale",
        "imposed-by",
    )
    schemas = [_json(SCHEMAS / f"{name}.schema.json") for name in REQUIREMENTS]
    assert {tuple(sorted(s["properties"])) for s in schemas} == {
        ("actors", "applies-to", "id", "measure", "refines", "statement", "status", "title")
    }
    assert {tuple(s["required"]) for s in schemas} == {
        ("id", "title", "status", "statement", "measure", "applies-to")
    }
    assert [s["$id"] for s in schemas] == [f"{name}.schema.json" for name in REQUIREMENTS]


def test_the_title_heading_and_each_label_sit_where_the_round_put_them() -> None:
    """Each document kind's body opens with its title, a level-1 heading the stamp
    words from the id and the title or name, and the glossary's entry with a level-2
    heading. The record's two parts are level-2 headings. A requirement's title heading
    shows its kind between its id and its title (DEC-002 point 2), and its example
    does."""
    kinds = _kinds()["kinds"]
    for name in ("actor", "use-case", "journey", "revalidation-record", *REQUIREMENTS):
        assert kinds[name]["sections"][0]["level"] == 1
        assert "head" not in kinds[name]
    for name in REQUIREMENTS:
        example = kinds[name]["sections"][0]["example"]
        assert re.fullmatch(rf"# REQ-[0-9]{{3}} · {SHOWN_AS[name]} · \S.*", example), example
    assert kinds["term"]["sections"][0]["level"] == 2
    assert [e["level"] for e in kinds["revalidation-record"]["sections"][1:]] == [2, 2]


def test_the_glossary_is_a_collection_whose_head_the_stamp_writes_once() -> None:
    """The term is the one collection kind: its sections are each entry's, and its head
    is the file's heading and opening, the words the template's body opens with today."""
    kinds = _kinds()["kinds"]
    assert [name for name, kind in kinds.items() if "head" in kind] == ["term"]
    head = kinds["term"]["head"]
    assert [(e["id"], e["type"], e.get("level")) for e in head] == [
        ("file-heading", "heading", 1),
        ("file-opening", "opening", None),
    ]
    template = (CAPABILITY / "templates" / "glossary.md").read_text(encoding="utf-8")
    body = template.split("\n---\n", 1)[1].lstrip("\n")
    assert body.startswith(f"# {head[0]['stamp']}\n\n{head[1]['stamp']}\n")


@pytest.mark.parametrize("name", sorted(PARTS))
def test_each_front_matter_field_is_one_the_kind_s_schema_gives(name: str) -> None:
    """A kind's companion schema shares its name, and checks each field's shape."""
    properties = _json(SCHEMAS / f"{name}.schema.json")["properties"]
    fields = _kinds()["kinds"][name].get("front-matter", {})
    assert sorted(set(fields) - set(properties)) == []


#: The closed list of forms, as the round decided them (#1362, "For the build").
FORMS = (
    "sentence",
    "numbered-steps",
    "variants",
    "steps-match-front-matter",
    "outcomes-match-front-matter",
    "gaps-match-outcomes",
    "builds-on-matches-front-matter",
    "headings-match-front-matter",
    "definition",
)


def test_the_forms_are_a_closed_list_and_each_is_used() -> None:
    """The schema gives the closed list, each form with what it holds. `seams-match-steps`
    went with the journey's seams (#1362). No form in the list is unused: a glossary's
    head takes `builds-on-matches-front-matter` (DEC-001 point 2)."""
    listed = [entry["const"] for entry in _kinds_schema()["$defs"]["form"]["oneOf"]]
    assert listed == list(FORMS)
    assert all(entry["description"] for entry in _kinds_schema()["$defs"]["form"]["oneOf"])
    used = {
        element["form"]
        for kind in _kinds()["kinds"].values()
        for element in [
            *kind["sections"],
            *kind.get("head", []),
            *kind.get("front-matter", {}).values(),
        ]
        if "form" in element
    }
    assert used == set(FORMS)


# --- hints and examples ---------------------------------------------------------------------


def _written() -> list[tuple[str, str, dict[str, Any]]]:
    """Each element and front-matter field of each kind: its kind, its id, and itself."""
    found: list[tuple[str, str, dict[str, Any]]] = []
    for name, kind in _kinds()["kinds"].items():
        found += [(name, element["id"], element) for element in kind["sections"]]
        found += [(name, field, entry) for field, entry in kind.get("front-matter", {}).items()]
    return found


def test_each_part_has_a_hint_and_an_example_and_a_stamped_heading_no_hint() -> None:
    """Each part a writer fills has a hint and an example. A heading the stamp words
    from the artefact's id and title or name has an example and no hint: the round gave
    none (#1362). The record's two parts are headings with fixed text, and have both."""
    for name, element_id, element in _written():
        assert element.get("example"), (name, element_id)
        stamped = element.get("type") == "heading" and "text" not in element
        assert ("hint" in element) is not stamped, (name, element_id)


@pytest.mark.parametrize(
    ("name", "element_id", "key"),
    [
        (name, element_id, key)
        for name, element_id, element in _written()
        for key in ("hint", "example")
        if key in element
    ],
)
def test_each_hint_and_example_is_one_plain_line(name: str, element_id: str, key: str) -> None:
    """One line, with no semicolon and no sentence over 25 words, read as the prose lint
    reads them (`below_floor`): a floor any project's writing rules accept (#1351)."""
    text = next(e for n, i, e in _written() if (n, i) == (name, element_id))[key]
    assert "\n" not in text and text.strip() == text
    assert below_floor(f"# Heading\n\n{text}\n") == []


def test_the_reviewed_against_example_names_each_kind_of_source_with_full_commits() -> None:
    """The record's hint and example for `reviewed-against` come from the round's table for
    the field (#1362). The example is the field's value, so it reads as YAML and fits the
    record's schema, a source in the tracker and one in this repository. Its commit is
    written in full, since an abbreviation can come to name two commits."""
    field = _kinds()["kinds"]["revalidation-record"]["front-matter"]["reviewed-against"]
    sources = load(field["example"])
    assert _record_messages(_planned(sources)) == []
    assert ["url" in source for source in sources] == [True, False]
    assert re.fullmatch(r"[0-9a-f]{40}", sources[1]["version"])


# --- reviewed-against: a planned record's sources (DEC-001 point 6) ------------------------------


def _record_messages(record: dict[str, Any]) -> list[str]:
    """The record's schema's messages, its references resolved over the capability's
    schemas, as the check resolves them."""
    schemas = [_json(path) for path in sorted(SCHEMAS.glob("*.schema.json"))]
    registry = Registry[Any]().with_resources(
        (schema["$id"], Resource[Any].from_contents(schema)) for schema in schemas
    )
    validator: Any = Draft202012Validator(
        _json(SCHEMAS / "revalidation-record.schema.json"), registry=registry
    )
    return [error.message for error in validator.iter_errors(record)]


def _planned(sources: Any = None, trigger: str = "planned") -> dict[str, Any]:
    record: dict[str, Any] = {
        "change": "#42",
        "trigger": trigger,
        "date": "2026-01-05",
        "by": "Sam",
        "outcomes": {"UC-007": "gap-found"},
    }
    if sources is not None:
        record["reviewed-against"] = sources
    return record


def test_a_planned_record_requires_its_sources_and_another_leaves_them_out() -> None:
    source = {"title": "the redesign note", "version": SHA1}
    assert _record_messages(_planned([source])) == []
    assert _record_messages(_planned()) == ["'reviewed-against' is a required property"]
    assert _record_messages(_planned(trigger="drift")) == []
    (refused,) = _record_messages(_planned([source], trigger="drift"))
    assert refused.endswith("should not be valid under {}")
    assert _record_messages(_planned([])) == ["[] should be non-empty"]


@pytest.mark.parametrize(
    ("source", "admitted"),
    [
        # In this repository: no link, and a commit's full id or `this change`.
        ({"title": "the note", "version": SHA1}, True),
        ({"title": "the note", "version": SHA256}, True),
        ({"title": "the note", "version": "this change"}, True),
        ({"title": "the note", "version": SHA1[:7]}, False),
        ({"title": "the note", "version": SHA1.upper()}, False),
        ({"title": "the note", "version": READ_AT}, False),
        ({"title": "the note", "version": "This change"}, False),
        # Outside it: an absolute link, and the time it was read or another repository's
        # commit, in full.
        ({"title": "#42's body", "url": LINK, "version": READ_AT}, True),
        ({"title": "a design", "url": "https://git.example/other/repo", "version": SHA1}, True),
        (
            {
                "title": "a comment",
                "url": "https://github.com/o/r/pull/1374#issuecomment-6046070594",
                "version": READ_AT,
            },
            True,
        ),
        ({"title": "#42's body", "url": LINK, "version": "this change"}, False),
        ({"title": "#42's body", "url": LINK, "version": SHA1[:7]}, False),
        ({"title": "#42's body", "url": LINK, "version": "2026-01-05"}, False),
        ({"title": "#42's body", "url": LINK, "version": "2026-01-05T10:00:00+01:00"}, False),
        ({"title": "#42's body", "url": LINK, "version": "2026-01-05 10:00:00Z"}, False),
        # A link that is not absolute.
        ({"title": "#42's body", "url": "issues/42", "version": READ_AT}, False),
        ({"title": "#42's body", "url": "/issues/42", "version": READ_AT}, False),
        ({"title": "#42's body", "url": "//tracker.example/issues/42", "version": READ_AT}, False),
        ({"title": "#42's body", "url": "https:///issues/42", "version": READ_AT}, False),
        ({"title": "#42's body", "url": "https://tracker.example/a b", "version": READ_AT}, False),
        # The mapping's own keys.
        ({"title": "the note", "version": SHA1, "author": "Sam"}, False),
        ({"version": SHA1}, False),
        ({"title": "the note"}, False),
        ({"title": "", "version": SHA1}, False),
    ],
    ids=[
        "commit",
        "commit-sha256",
        "this-change",
        "abbreviated-commit",
        "commit-in-capitals",
        "time-without-link",
        "this-change-in-capitals",
        "link-and-time",
        "link-and-another-repository-s-commit",
        "link-to-a-comment",
        "link-and-this-change",
        "link-and-abbreviated-commit",
        "link-and-a-date",
        "link-and-a-time-not-in-utc",
        "link-and-a-time-with-a-space",
        "relative-link",
        "root-relative-link",
        "scheme-relative-link",
        "link-without-host",
        "link-with-white-space",
        "unknown-key",
        "no-title",
        "no-version",
        "empty-title",
    ],
)
def test_each_source_s_version_has_the_form_its_place_gives(
    source: dict[str, Any], admitted: bool
) -> None:
    assert (_record_messages(_planned([source])) == []) is admitted


def test_a_time_is_spelt_as_a_revalidation_s_at() -> None:
    """A UTC timestamp, the core container schema's spelling of `at` (COR-050 point 3):
    the copy here is held equal to it, since the capability's schemas read alone."""
    container = _json(REPO / ".pkit" / "schemas" / "backbone" / "container.schema.json")
    record = _json(SCHEMAS / "revalidation-record.schema.json")
    assert record["$defs"]["time"]["pattern"] == container["$defs"]["utc-timestamp"]["pattern"]


def test_the_record_s_change_names_a_range_of_commits_on_the_default_branch() -> None:
    record = _json(SCHEMAS / "revalidation-record.schema.json")
    assert (
        "a range of commits on the default branch" in record["properties"]["change"]["description"]
    )
