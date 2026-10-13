"""software-analysis: a companion schema and a template per artefact kind (#887).

Held to software-analysis DEC-001 points 1 to 6:

- one **companion schema** per kind — actor, term, use case, journey,
  revalidation record — and the evidence point's (#1001), each valid Draft
  2020-12, sharing one home for the id shapes (`analysis.schema.json`);
- each anchored kind's **template** carrying the friction block inside the
  methodology's container — in the front matter of a document, in each entry
  of a collection — valid against the core's container schema and against the
  kind's own; the journey's anchors written from its steps; the revalidation
  record's no anchored artefact.
"""

from __future__ import annotations

import ast
import json
import re
from typing import Any, cast

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from scripts import prose_lint as pl

from project_kit import backbone_schemas as bs
from project_kit import document_parts
from tests.analysis_repo import CAPABILITY, REPO, below_floor, load

SCHEMAS = CAPABILITY / "schemas"

#: A commit's full name under SHA-1, and under SHA-256.
SHA1 = "78981922613b2afb6025042ff6bd878ac1994e85"
SHA256 = "4f9be057f0ea5d2ba72fd2c810e8d7b9aa98b469f9a6c4d6d0e2a2d3e1c4b5a6"

#: An executed check's name, as a filler gives it.
CHECK = "pytest-bridge.test-run.test-sandbox"


def _stems() -> list[str]:
    return sorted(
        p.name.removesuffix(".schema.json")
        for p in SCHEMAS.iterdir()
        if p.name.endswith(".schema.json")
    )


def _schema(stem: str) -> dict[str, Any]:
    return json.loads((SCHEMAS / f"{stem}.schema.json").read_text(encoding="utf-8"))


def _schema_errors(stem: str, instance: Any) -> list[str]:
    """The companion schema's messages for `instance`, its cross-file `$ref`s
    resolved over the capability's schemas, as the check resolves them."""
    resources: list[tuple[str, Resource[Any]]] = [
        (_schema(s)["$id"], Resource[Any].from_contents(_schema(s))) for s in _stems()
    ]
    registry = Registry[Any]().with_resources(resources)
    validator: Any = Draft202012Validator(_schema(stem), registry=registry)
    return [error.message for error in validator.iter_errors(instance)]


def _container_findings(carrier: Any) -> tuple[Any, ...]:
    """The core container schema's findings on a front matter or an entry."""
    backbone: Any = bs  # its schema loader returns an untyped mapping
    schema = backbone.load_backbone_schema(REPO, "container")
    return backbone.validate_container(carrier, schema, wiring=bs.ContainerWiring()).findings


def _template(name: str) -> dict[str, Any]:
    text = (CAPABILITY / "templates" / f"{name}.md").read_text(encoding="utf-8")
    front_matter, _body = document_parts.split_front_matter(text)
    assert front_matter is not None
    return load(front_matter)


def test_the_schemas_are_one_per_kind_and_valid() -> None:
    """One per kind, the shared definitions, the evidence point's companion (#1001), and
    the project configuration's (#1342)."""
    stems = _stems()
    assert stems == [
        "actor",
        "analysis",
        "config",
        "journey",
        "revalidation-evidence",
        "revalidation-record",
        "term",
        "use-case",
    ]
    for stem in stems:
        Draft202012Validator.check_schema(_schema(stem))


@pytest.mark.parametrize(
    "artefact",
    [
        "ACT-tester",
        "TERM-sandbox",
        "UC-007",
        "UC-1000",
        "JRN-001",
        "ACT-Tester",
        "UC-0007",
        "JRN-1",
        "USER-x",
        f"UC-007@{SHA1}",
        "",
    ],
)
def test_an_evidence_id_is_an_artefact_id_a_commit_and_a_check(artefact: str) -> None:
    """A pattern cannot refer to another, so the evidence id spells the four id
    shapes again beside them: held in step, it admits `<artefact>@<commit>#<check>`
    exactly when the artefact id does — and never without its check."""
    definitions = _schema("analysis")["$defs"]
    evidence_id = re.compile(definitions["evidence-id"]["pattern"])
    is_artefact = any(
        re.match(definitions[f"{kind}-id"]["pattern"], artefact)
        for kind in ("actor", "term", "use-case", "journey")
    )
    assert bool(evidence_id.match(f"{artefact}@{SHA1}#{CHECK}")) is is_artefact
    assert not evidence_id.match(f"{artefact}@{SHA1}")
    assert not evidence_id.match(f"{artefact}@{SHA1}#")
    assert not evidence_id.match(f"{artefact}@HEAD#{CHECK}")


@pytest.mark.parametrize(
    ("name", "admitted"),
    [
        ("project", True),
        ("pytest-bridge.test-run.test-sandbox", True),
        ("trace-runner.2024-walk", True),  # a later word may begin with a digit
        ("trace-runner.v2", True),
        ("pytest-bridge.test_run", False),  # an underscore: slug the test's name
        ("Pytest-bridge.run", False),
        ("pytest-bridge.Run", False),
        ("2-bridge.run", False),  # the first word begins with a letter
        ("pytest-bridge..run", False),  # an empty word
        ("pytest-bridge.", False),
        (".run", False),
        ("pytest-bridge/run", False),
        ("pytest-bridge:run", False),
        ("tests/test_run.py::test_sandbox", False),
        ("", False),
    ],
)
def test_a_check_name_is_dotted_lower_case_words(name: str, admitted: bool) -> None:
    """Lower-case words of letters, digits and hyphens joined by dots, the first
    beginning with a letter (DEC-001 point 7) — in the check name and in the evidence
    id's copy of it alike."""
    definitions = _schema("analysis")["$defs"]
    assert bool(re.match(definitions["check-name"]["pattern"], name)) is admitted
    assert bool(re.match(definitions["evidence-id"]["pattern"], f"UC-007@{SHA1}#{name}")) is (
        admitted
    )


@pytest.mark.parametrize(
    ("name", "full"),
    [
        (SHA1, True),
        (SHA256, True),
        (SHA1[:7], False),
        (SHA1[:-1], False),
        (f"{SHA1}0", False),
        (SHA1.upper(), False),
        ("HEAD", False),
        ("", False),
    ],
)
def test_a_commit_is_written_by_its_full_name(name: str, full: bool) -> None:
    """40 hexadecimal digits, or 64 under SHA-256, in lower case; a short name is
    refused, so a commit has one spelling and a citation matches an entry exactly —
    in the commit shape and in the evidence id's copy of it alike."""
    definitions = _schema("analysis")["$defs"]
    assert bool(re.match(definitions["commit"]["pattern"], name)) is full
    assert bool(re.match(definitions["evidence-id"]["pattern"], f"UC-007@{name}#{CHECK}")) is full


#: The definitions the evidence point's companion carries as copies of the shared ones.
COPIED = (
    "text",
    "actor-id",
    "term-id",
    "use-case-id",
    "journey-id",
    "artefact-id",
    "commit",
    "check-name",
    "evidence-id",
)


def _refs(value: Any) -> list[str]:
    """Every `$ref` in a schema, at any depth."""
    if isinstance(value, dict):
        mapping = cast("dict[str, Any]", value)
        ref = mapping.get("$ref")
        own = [ref] if isinstance(ref, str) else []
        return own + [found for item in mapping.values() for found in _refs(item)]
    if isinstance(value, list):
        return [found for item in cast("list[Any]", value) for found in _refs(item)]
    return []


def test_the_evidence_point_s_schema_reads_alone() -> None:
    """Two providers of one point are compared by its companion file alone (COR-053
    point 5), so the evidence point's refers to nothing outside it: it carries a copy
    of each shared definition it needs, equal to the one in `analysis.schema.json`,
    their one home."""
    point = _schema("revalidation-evidence")
    assert [ref for ref in _refs(point) if not ref.startswith("#/")] == []
    shared = _schema("analysis")["$defs"]
    copies = {name: body for name, body in point["$defs"].items() if name != "evidence"}
    assert sorted(copies) == sorted(COPIED)
    assert {name: shared[name] for name in COPIED} == copies


@pytest.mark.parametrize(
    ("definition", "admitted", "refused"),
    [
        (
            "use-case-id",
            ["UC-000", "UC-007", "UC-999", "UC-1000", "UC-12345"],
            ["UC-07", "UC-0007", "UC-01000"],
        ),
        ("journey-id", ["JRN-001", "JRN-1000"], ["JRN-1", "JRN-0001"]),
    ],
)
def test_a_number_has_one_spelling(
    definition: str, admitted: list[str], refused: list[str]
) -> None:
    """Three digits below 1000, no leading zero from 1000 on: `UC-0007` is never a
    second id for `UC-007`."""
    pattern = re.compile(_schema("analysis")["$defs"][definition]["pattern"])
    assert [i for i in admitted if not pattern.match(i)] == []
    assert [i for i in refused if pattern.match(i)] == []


def test_every_id_shape_has_one_home() -> None:
    """The kinds' schemas refer to the shared id shapes; none writes its own. The
    evidence point's companion carries a copy, held equal to its home
    (`test_the_evidence_point_s_schema_reads_alone`)."""
    for prefix in ("ACT", "TERM", "UC", "JRN"):
        holders = [s for s in _stems() if f'"^{prefix}-' in json.dumps(_schema(s))]
        assert holders == ["analysis", "revalidation-evidence"], prefix


@pytest.mark.parametrize(("template", "schema"), [("use-case", "use-case"), ("journey", "journey")])
def test_a_document_template_carries_the_friction_block_in_the_container(
    template: str, schema: str
) -> None:
    data = _template(template)
    assert _container_findings(data) == ()
    assert set(data["pkit"]) == {"friction"}
    assert _schema_errors(schema, {k: v for k, v in data.items() if k != "pkit"}) == []


@pytest.mark.parametrize(("template", "schema"), [("actors", "actor"), ("glossary", "term")])
def test_a_collection_template_carries_the_friction_block_in_each_entry(
    template: str, schema: str
) -> None:
    data = _template(template)
    assert "pkit" not in data  # a collection: the container is in each entry
    id_pattern = _schema("analysis")["$defs"][f"{schema}-id"]["pattern"]
    for entry_id, entry in data.items():
        assert re.match(id_pattern, entry_id)
        assert _container_findings(entry) == ()
        assert set(entry["pkit"]) == {"friction"}
        assert _schema_errors(schema, {k: v for k, v in entry.items() if k != "pkit"}) == []


@pytest.mark.parametrize("template", ["use-case", "journey"])
def test_a_document_template_s_heading_is_its_id_and_title(template: str) -> None:
    text = (CAPABILITY / "templates" / f"{template}.md").read_text(encoding="utf-8")
    data = _template(template)
    assert f"\n# {data['id']} — {data['title']}\n" in text


def test_the_journey_template_anchors_its_steps() -> None:
    data = _template("journey")
    assert data["pkit"]["friction"]["anchors"]["artefact"] == data["steps"]


def test_the_revalidation_record_template_is_no_anchored_artefact() -> None:
    data = _template("revalidation-record")
    assert "pkit" not in data
    assert _schema_errors("revalidation-record", data) == []


def test_the_revalidation_record_template_shows_an_evidence_copy() -> None:
    """The optional `evidence` the template shows, commented out, is an entry of the
    evidence point copied whole: uncommented, the record still fits its schema."""
    text = (CAPABILITY / "templates" / "revalidation-record.md").read_text(encoding="utf-8")
    front_matter, _body = document_parts.split_front_matter(text)
    assert front_matter is not None
    lines = front_matter.splitlines()
    start = lines.index(next(line for line in lines if line.startswith("# evidence:")))
    shown = load("\n".join(line.removeprefix("# ") for line in lines[start:]))
    (entry,) = shown["evidence"]
    assert entry["id"] == f"{entry['artefact']}@{entry['commit']}#{entry['check']}"
    record = {**_template("revalidation-record"), "evidence": shown["evidence"]}
    assert entry["artefact"] in record["outcomes"]
    assert _schema_errors("revalidation-record", record) == []


#: A text in angle brackets, as a template or a command writes a placeholder.
_BRACKETED = re.compile(r"<[^<>\n]+>")

#: A placeholder a skill's command shows for a text the artefact stamp writes.
_SHOWN = re.compile(r'--(?:title|name|unanchored-because) "(<[^"]+>)"')


def _texts(value: Any) -> list[str]:
    """Each text in a parsed YAML value."""
    if isinstance(value, str):
        return [value]
    items: list[Any] = []
    if isinstance(value, dict):
        items = list(cast(dict[Any, Any], value).values())
    elif isinstance(value, list):
        items = cast(list[Any], value)
    return [text for item in items for text in _texts(item)]


def _shipped(name: str) -> tuple[str, ...]:
    """A tuple `_lib/placeholder.py` defines, read from its source: the scripts run in
    their own environment, and their `_lib` is not importable here."""
    source = (CAPABILITY / "scripts" / "_lib" / "placeholder.py").read_text(encoding="utf-8")
    for node in ast.parse(source).body:
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == name
        ):
            return tuple(ast.literal_eval(node.value))
    raise AssertionError(f"_lib/placeholder.py defines no {name}")


def test_every_placeholder_shipped_is_in_the_append_only_lists() -> None:
    """The check and the stamp match an artefact against the placeholders ever shipped,
    exactly: each one the artefact templates hold — in a front matter's value or a
    body — and each the skill's commands show for a title, a name or a reason is in
    the lists, so rewording a template adds its new placeholder beside the old, which
    stays detectable in what was stamped before."""
    in_templates, in_commands = _shipped("IN_TEMPLATES"), _shipped("IN_COMMANDS")
    assert len(set(in_templates)) == len(in_templates)
    shipped: set[str] = set()
    for name in ("actors", "glossary", "use-case", "journey"):
        text = (CAPABILITY / "templates" / f"{name}.md").read_text(encoding="utf-8")
        _front, body = document_parts.split_front_matter(text)
        for value in [*_texts(_template(name)), body]:
            shipped |= set(_BRACKETED.findall(value))
    assert "<Title>" in shipped and "<Display name>" in shipped and "<Term>" in shipped
    assert shipped <= set(in_templates), sorted(shipped - set(in_templates))
    skill = CAPABILITY / "skills" / "analysis-author"
    shown = {
        found
        for page in sorted(skill.glob("*.md"))
        if page.name != "revalidation-record.md"  # the record stamp reads a text by shape
        for found in _SHOWN.findall(page.read_text(encoding="utf-8"))
    }
    assert "<why>" in shown
    assert shown <= set(in_templates) | set(in_commands), sorted(shown - set(in_templates))


#: Every template the capability ships.
TEMPLATES = tuple(sorted(p.stem for p in (CAPABILITY / "templates").glob("*.md")))

#: A collection template's opening sentence, which the stamp writes once (#1351).
COLLECTION_OPENINGS = {
    "actors": "Who uses the system, and what each needs from it.",
    "glossary": "The words of the domain and what each means.",
}

#: What a document template opens with after its heading: its first part, whose sentence
#: its author writes, or a revalidation record's outcomes (#1351).
DOCUMENT_OPENINGS = {
    "use-case": "**Goal:** <",
    "journey": "**Starts:** <",
    "revalidation-record": "## Outcomes",
}


def _body(name: str) -> str:
    text = (CAPABILITY / "templates" / f"{name}.md").read_text(encoding="utf-8")
    _front, body = document_parts.split_front_matter(text)
    return body.lstrip("\n")


def test_every_template_has_its_opening_checked() -> None:
    """Each template the capability ships is linted below, and one of the two tests of
    openings checks it, so a new template is left out of neither."""
    assert set(TEMPLATES) == set(COLLECTION_OPENINGS) | set(DOCUMENT_OPENINGS)


@pytest.mark.parametrize("name", TEMPLATES)
def test_a_template_s_text_holds_no_semicolon_and_no_long_sentence(name: str) -> None:
    """A template's text, its front matter's values and its body, is plain enough for any
    project's writing rules (#1351). It holds no semicolon and no sentence over 25 words,
    read as the prose lint reads them (`below_floor`). The front matter's comments are
    notes on the template, which the stamp never writes."""
    text = (CAPABILITY / "templates" / f"{name}.md").read_text(encoding="utf-8")
    assert below_floor(text) == []


@pytest.mark.parametrize(
    ("text", "rule"),
    [
        (
            "Who uses the system, and what each needs from it. Each actor's id is stable; its "
            "name may change.",
            "RS-WRITE-008",
        ),
        (
            "**Variants:** each lettered after the step it branches from; steps and variants "
            "are only ever added, never renumbered.",
            "RS-WRITE-008",
        ),
        (
            "**Variants:** each variant is lettered after the step it branches from, and steps "
            "and variants are only ever added and never renumbered, since journeys and evidence "
            "cite them.",
            "RS-WRITE-005",
        ),
        ("<Who this is; when they come to the system.>", "RS-WRITE-008"),
    ],
    ids=[
        "semicolon-in-an-opening",
        "semicolon-in-a-part",
        "sentence-over-25-words",
        "semicolon-in-a-placeholder-line",
    ],
)
def test_a_template_s_text_with_a_semicolon_or_a_long_sentence_is_caught(
    text: str, rule: str
) -> None:
    """Two texts the templates shipped before #1351, a sentence of 27 words, and a
    placeholder on a line of its own each fail the test above."""
    (finding,) = below_floor(f"# Heading\n\n{text}\n")
    assert finding.startswith(f"3 {rule}: ")


@pytest.mark.parametrize(("name", "opening"), sorted(COLLECTION_OPENINGS.items()))
def test_a_collection_template_opens_with_one_sentence_on_what_it_holds(
    name: str, opening: str
) -> None:
    """A collection file opens with one sentence that says what it holds (#1351). The stamp
    writes it once, when it creates the file, and the project may reword it after."""
    heading, first, *_rest = _body(name).split("\n\n")
    assert heading.startswith("# ")
    (block,) = pl.markdown_blocks(first)
    sentence = pl.sentences(block, block.text)[0]
    assert block.text[sentence.start : sentence.end].strip() == opening


@pytest.mark.parametrize(("name", "opening"), sorted(DOCUMENT_OPENINGS.items()))
def test_a_document_template_opens_with_its_first_part(name: str, opening: str) -> None:
    """A use case or a journey opens with its first part, the goal or where the actor
    starts, whose sentence its author writes in place of the placeholder. A revalidation
    record opens with its outcomes, a section that is only a list, which its heading
    names (#1351)."""
    heading, first, *_rest = _body(name).split("\n\n")
    assert heading.startswith("# ")
    assert first.startswith(opening)


@pytest.mark.parametrize(
    ("stem", "instance", "message"),
    [
        (
            "use-case",
            {"id": "UC-7", "title": "T", "status": "active", "actor": "ACT-a"},
            "does not match",
        ),
        ("use-case", {"id": "UC-007", "status": "active", "actor": "ACT-a"}, "'title' is a"),
        (
            "journey",
            {
                "id": "JRN-001",
                "title": "T",
                "status": "active",
                "actor": "ACT-a",
                "steps": ["UC-001"],
            },
            "is too short",
        ),
        (
            "journey",
            {
                "id": "JRN-001",
                "title": "",
                "status": "active",
                "actor": "ACT-a",
                "steps": ["UC-001", "UC-002"],
            },
            "should be non-empty",
        ),
        ("actor", {"name": "A", "status": "active", "needs": []}, "should be non-empty"),
        (
            "term",
            {"name": "T", "status": "active", "definition": "d", "replaces": ["x", "x"]},
            "non-unique",
        ),
    ],
)
def test_the_schemas_refuse_what_the_decision_rules_out(
    stem: str, instance: dict[str, Any], message: str
) -> None:
    (found,) = _schema_errors(stem, instance)
    assert message in found
