"""software-analysis: a companion schema and a template per artefact kind (#887).

Held to software-analysis DEC-001 points 1 to 6:

- one **companion schema** per kind — actor, term, use case, journey, the
  three kinds of requirement (#1691), revalidation record — and the evidence
  point's (#1001), each valid Draft 2020-12, sharing one home for the id shapes
  (`analysis.schema.json`), a requirement's `REQ-NNN` among them;
- each anchored kind's **template** carrying the friction block inside the
  methodology's container — in the front matter of a document, an actor's
  included (#1346), in each entry of the glossary, a collection — valid against
  the core's container schema and against the kind's own; the journey's
  anchors written from its steps; the revalidation record's no anchored
  artefact;
- each template's **body rendered from its kind's declaration** (#1366), held
  equal to the rendering: every part, in order, each a writer fills holding its
  hint, a one-line `pkit:hint` comment with its example, and the revalidation
  record's none.
"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, cast

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from scripts import prose_lint as pl

from project_kit import backbone_schemas as bs
from project_kit import document_parts
from tests.analysis_repo import CAPABILITY, REPO, below_floor, load, load_lib

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
    """One per kind, the shared definitions, the evidence point's companion (#1001), the
    project configuration's (#1342), the kinds' declared structure's (#1363), and a
    project's own structures' (#1367)."""
    stems = _stems()
    assert stems == [
        "actor",
        "analysis",
        "artefact-kinds",
        "config",
        "constraint",
        "functional-requirement",
        "journey",
        "quality-requirement",
        "revalidation-evidence",
        "revalidation-record",
        "structures",
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
        "REQ-004",
        "REQ-1000",
        "ACT-Tester",
        "UC-0007",
        "JRN-1",
        "REQ-04",
        "REQ-0004",
        "USER-x",
        f"UC-007@{SHA1}",
        "",
    ],
)
def test_an_evidence_id_is_an_artefact_id_a_commit_and_a_check(artefact: str) -> None:
    """A pattern cannot refer to another, so the evidence id spells the five id
    shapes again beside them, a requirement's among them (#1691): held in step, it
    admits `<artefact>@<commit>#<check>` exactly when the artefact id does — and never
    without its check."""
    definitions = _schema("analysis")["$defs"]
    evidence_id = re.compile(definitions["evidence-id"]["pattern"])
    is_artefact = any(
        re.match(definitions[f"{kind}-id"]["pattern"], artefact)
        for kind in ("actor", "term", "use-case", "journey", "requirement")
    )
    assert {ref["$ref"] for ref in definitions["artefact-id"]["anyOf"]} == {
        f"#/$defs/{kind}-id" for kind in ("actor", "term", "use-case", "journey", "requirement")
    }
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
    "requirement-id",
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
        (
            "requirement-id",
            ["REQ-000", "REQ-007", "REQ-999", "REQ-1000"],
            ["REQ-7", "REQ-07", "REQ-0007", "REQ-01000", "REQ-abc", "req-007", "QR-007"],
        ),
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
    for prefix in ("ACT", "TERM", "UC", "JRN", "REQ"):
        holders = [s for s in _stems() if f'"^{prefix}-' in json.dumps(_schema(s))]
        assert holders == ["analysis", "revalidation-evidence"], prefix


#: The three kinds of requirement, each a document kind whose template and schema are
#: named as its type (DEC-002 point 3, #1691).
REQUIREMENTS = ("quality-requirement", "functional-requirement", "constraint")

#: A requirement's own fields, filled: valid for each of the three kinds, which take the
#: same fields (DEC-002 point 4).
REQUIREMENT: dict[str, Any] = {
    "id": "REQ-004",
    "title": "Show a run's result quickly",
    "status": "active",
    "statement": "The system shows a suite's result within two seconds of the run's end.",
    "measure": "95 of every 100 runs show their result within two seconds.",
    "applies-to": "Every run of a suite.",
    "actors": ["ACT-tester"],
    "refines": ["REQ-001"],
}


@pytest.mark.parametrize(
    ("template", "schema"),
    [
        ("actor", "actor"),
        ("use-case", "use-case"),
        ("journey", "journey"),
        *((kind, kind) for kind in REQUIREMENTS),
    ],
)
def test_a_document_template_carries_the_friction_block_in_the_container(
    template: str, schema: str
) -> None:
    data = _template(template)
    assert _container_findings(data) == ()
    assert set(data["pkit"]) == {"friction"}
    assert _schema_errors(schema, {k: v for k, v in data.items() if k != "pkit"}) == []


@pytest.mark.parametrize(("template", "schema"), [("glossary", "term")])
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


@pytest.mark.parametrize(
    ("template", "field"), [("actor", "name"), ("use-case", "title"), ("journey", "title")]
)
def test_a_document_template_s_heading_is_its_id_and_title(template: str, field: str) -> None:
    """A use case's or journey's heading is its id and title, an actor's its id and name."""
    text = (CAPABILITY / "templates" / f"{template}.md").read_text(encoding="utf-8")
    data = _template(template)
    assert f"\n# {data['id']} — {data[field]}\n" in text


@pytest.mark.parametrize(
    ("template", "shown"),
    [
        ("quality-requirement", "Quality"),
        ("functional-requirement", "Functional"),
        ("constraint", "Constraint"),
    ],
)
def test_a_requirement_template_s_heading_is_its_id_its_kind_and_its_title(
    template: str, shown: str
) -> None:
    """The kind shows beside the id in the heading: `# REQ-NNN · Quality · <title>`, with
    the kind's name for each kind (DEC-002 point 2)."""
    text = (CAPABILITY / "templates" / f"{template}.md").read_text(encoding="utf-8")
    data = _template(template)
    assert f"\n# {data['id']} · {shown} · {data['title']}\n" in text


def test_a_requirement_template_anchors_its_actors_and_what_it_refines() -> None:
    """Within the analysis, a requirement anchors only each actor in `actors` and each
    requirement in `refines`, as artefact anchors (DEC-002 point 6)."""
    for template in REQUIREMENTS:
        data = _template(template)
        anchored = [*data["actors"], *data["refines"]]
        assert data["pkit"]["friction"]["anchors"]["artefact"] == anchored, template


#: The migration that retires the actors' collection template (#1346).
RETIRED = CAPABILITY / "migrations" / "0.2.0" / "001-retire-actors-collection-template.sh"


def test_the_actors_collection_template_is_retired_by_a_migration_that_changes_nothing(
    tmp_path: Path,
) -> None:
    """An actor is a file of its own (#1346): the capability ships `actor.md` and no
    longer `actors.md`. The migration that goes with it does nothing and says why — the
    copy of the capability's tree drops the template, and the actors are the project's
    to move, each with its revalidation. Run twice over a project holding the old
    collection file, it leaves every byte as it was."""
    templates = sorted(p.name for p in (CAPABILITY / "templates").glob("*.md"))
    assert "actor.md" in templates and "actors.md" not in templates
    held = tmp_path / "tech-docs" / "analysis" / "use-case-model" / "actors.md"
    held.parent.mkdir(parents=True)
    held.write_text("---\nACT-admin:\n  name: Admin\n---\n", encoding="utf-8")
    before = sorted((p.relative_to(tmp_path), p.read_bytes()) for p in tmp_path.rglob("*.md"))
    for _run in range(2):
        done = subprocess.run(
            ["bash", str(RETIRED)],
            env={**os.environ, "ROOT": str(tmp_path)},
            capture_output=True,
            text=True,
            check=False,
        )
        assert done.returncode == 0, done.stderr
        assert done.stdout.startswith("  note     actors.md template retired: ")
    after = sorted((p.relative_to(tmp_path), p.read_bytes()) for p in tmp_path.rglob("*.md"))
    assert after == before


def test_the_journey_template_anchors_its_actor_its_steps_and_what_it_relies_on() -> None:
    data = _template("journey")
    anchored = [data["actor"], *data["steps"], *data["relies-on"]]
    assert data["pkit"]["friction"]["anchors"]["artefact"] == anchored


def test_the_use_case_template_anchors_each_actor() -> None:
    data = _template("use-case")
    anchored = [data["actor"], *data["other-actors"]]
    assert data["pkit"]["friction"]["anchors"]["artefact"] == anchored


def _record_hint(front_matter: str) -> str | None:
    """The line of a template's front matter that holds its record anchor, if one does."""
    return next(
        (line for line in front_matter.splitlines() if line.strip().startswith("record:")),
        None,
    )


def _names_the_records_it_rests_on(line: str) -> bool:
    """Whether a record anchor's line names the records the artefact rests on, and the
    ones that answer it, since the analysis always anchors the solution (DEC-001
    point 11)."""
    return (
        '"<record it rests on>"' in line
        and "each record it rests on, or that answers it" in line
        and "DEC-001 point 11" in line
    )


def test_the_use_case_template_hints_the_records_it_rests_on() -> None:
    """The use case's record anchor names the records it rests on, and the ones that
    answer it: the use case anchors both, and no record anchors it back (#1447). The
    placeholder it replaced stays in the append-only list, as every placeholder a
    template shipped does."""
    text = (CAPABILITY / "templates" / "use-case.md").read_text(encoding="utf-8")
    front_matter, _body = document_parts.split_front_matter(text)
    assert front_matter is not None
    line = _record_hint(front_matter)
    assert line is not None and _names_the_records_it_rests_on(line), line
    assert _template("use-case")["pkit"]["friction"]["anchors"]["record"] == [
        "<record it rests on>"
    ]
    assert "<decision it relies on>" in _shipped("IN_TEMPLATES")


@pytest.mark.parametrize(
    "hint",
    [
        # The hint the use case shipped before: a decision it relies on, and nothing of
        # one that answers it.
        'record: ["<decision it relies on>"]     # --record: a change to one asks the same',
        # The placeholder alone, with a note that leaves out the records that answer it.
        'record: ["<record it rests on>"]  # --record: a record it rests on (DEC-001 point 11)',
    ],
)
def test_a_record_hint_that_omits_the_direction_is_caught(hint: str) -> None:
    """A record anchor's hint that leaves out the records that answer the use case
    fails the test above."""
    line = _record_hint(f"pkit:\n  friction:\n    anchors:\n      {hint}\n")
    assert line is not None and not _names_the_records_it_rests_on(line)


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


#: A text in angle brackets, as a template or a command writes a placeholder. A part's
#: hint, a comment, is matched by its mark instead, never by a list of its texts (#1366).
_BRACKETED = re.compile(r"<(?!!--)[^<>\n]+>")

#: Every placeholder the four artefact templates' bodies held before each part held its
#: hint (#1366): an artefact stamped before is still caught while it holds one.
EARLIER_BODIES = (
    "<Who this is, when they come to the system, and what they bring with them.>",
    "<More on the term when one sentence is not enough: where it applies, what it is not, "
    "an example.>",
    "<what the actor wants to achieve, in one sentence>",
    "<what triggers it>",
    "<what the actor or the system does>",
    "<…>",
    "<the condition at step 1, what happens instead, and where the path rejoins or ends>",
    "<the state that shows the goal is met>",
    "<where the actor begins, and what they want by the end>",
    "<what the actor achieves in this use case>",
    "<what carries over, and how it could break>",
    "<the state that shows the whole path succeeded>",
)

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
    for name in ("actor", "glossary", "use-case", "journey", *REQUIREMENTS):
        text = (CAPABILITY / "templates" / f"{name}.md").read_text(encoding="utf-8")
        _front, body = document_parts.split_front_matter(text)
        for value in [*_texts(_template(name)), body]:
            shipped |= set(_BRACKETED.findall(value))
    assert "<Title>" in shipped and "<Display name>" in shipped and "<Term>" in shipped
    assert shipped <= set(in_templates), sorted(shipped - set(in_templates))
    assert set(EARLIER_BODIES) <= set(in_templates), sorted(set(EARLIER_BODIES) - set(in_templates))
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
    "glossary": "The words of the domain and what each means.",
}

#: What a document template opens with after its heading: its first part, whose sentence
#: its author writes in place of the part's hint, or a revalidation record's outcomes
#: (#1351, #1366).
DOCUMENT_OPENINGS = {
    "actor": "<!-- pkit:hint What this role is",
    "use-case": "**Goal:** <!-- pkit:hint ",
    "journey": "**Goal:** <!-- pkit:hint ",
    "revalidation-record": "## Outcomes",
    # A requirement's obligation is in its front matter, so its body opens with what
    # verifies it (DEC-002 point 4).
    **dict.fromkeys(REQUIREMENTS, "**Verified by:** <!-- pkit:hint "),
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
    """An actor, a use case or a journey opens with its first part — who the actor is,
    the goal, or where the actor starts — whose sentence its author writes in place of
    the placeholder. A revalidation
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
        (
            "actor",
            {"id": "ACT-a", "name": "A", "status": "active", "needs": []},
            "should be non-empty",
        ),
        ("actor", {"name": "A", "status": "active", "needs": ["N"]}, "'id' is a required"),
        ("actor", {"id": "a", "name": "A", "status": "active", "needs": ["N"]}, "does not match"),
        (
            "term",
            {"name": "T", "status": "active", "definition": "d", "replaces": ["x", "x"]},
            "non-unique",
        ),
        # A requirement (DEC-002 points 2 to 4, #1691): its id is `REQ-NNN`, and it
        # requires its statement, its measure and where it holds. No field names its kind.
        *(
            (kind, {**REQUIREMENT, "id": bad}, "does not match")
            for kind in REQUIREMENTS
            for bad in ("REQ-7", "REQ-0007", "UC-007", "QR-007")
        ),
        *(
            (kind, {k: v for k, v in REQUIREMENT.items() if k != field}, f"'{field}' is a required")
            for kind in REQUIREMENTS
            for field in ("statement", "measure", "applies-to")
        ),
        *(
            (kind, {**REQUIREMENT, "kind": "quality"}, "'kind' was unexpected")
            for kind in REQUIREMENTS
        ),
        *(
            (kind, {**REQUIREMENT, field: value}, message)
            for kind in REQUIREMENTS
            for field, value, message in (
                ("refines", ["UC-001"], "does not match"),
                ("actors", ["ACT-a", "ACT-a"], "non-unique"),
                ("applies-to", "", "should be non-empty"),
            )
        ),
    ],
)
def test_the_schemas_refuse_what_the_decision_rules_out(
    stem: str, instance: dict[str, Any], message: str
) -> None:
    (found,) = _schema_errors(stem, instance)
    assert message in found


@pytest.mark.parametrize("kind", REQUIREMENTS)
def test_a_requirement_s_schema_takes_what_the_decision_gives(kind: str) -> None:
    """Its fields, a `measure` of `None.` included, and `actors` and `refines` absent,
    empty or listing ids. Where it holds may read anything here: the declared structure
    refuses `None.` there, where the format rule binds (DEC-002 point 4)."""
    assert _schema_errors(kind, REQUIREMENT) == []
    assert _schema_errors(kind, {**REQUIREMENT, "measure": "None."}) == []
    assert _schema_errors(kind, {**REQUIREMENT, "actors": [], "refines": []}) == []
    bare = {k: v for k, v in REQUIREMENT.items() if k not in ("actors", "refines")}
    assert _schema_errors(kind, bare) == []
    assert _schema_errors(kind, {**REQUIREMENT, "status": "withdrawn"}) == []


def _evidence(artefact: str, **more: Any) -> dict[str, Any]:
    return {
        "id": f"{artefact}@{SHA1}#{CHECK}",
        "artefact": artefact,
        "commit": SHA1,
        "check": CHECK,
        "result": "passed",
        "ran": "tests/test_run.py::test_sandbox",
        **more,
    }


def test_a_record_and_the_evidence_point_take_a_requirement_s_id() -> None:
    """A revalidation record's outcomes and the evidence point's entries may name a
    requirement by its id. A requirement has no steps, as an actor has none (DEC-002,
    Implications; #1691)."""
    record = {
        "change": "#42",
        "trigger": "drift",
        "date": "2026-10-18",
        "by": "Sam",
        "outcomes": {"REQ-004": "holds", "UC-003": "holds"},
        "evidence": [_evidence("REQ-004")],
    }
    assert _schema_errors("revalidation-record", record) == []
    assert _schema_errors("revalidation-evidence", [_evidence("REQ-004")]) == []
    (stepped,) = _schema_errors("revalidation-evidence", [_evidence("REQ-004", steps=["1"])])
    assert "False schema does not allow" in stepped
    (misspelt,) = _schema_errors("revalidation-record", {**record, "outcomes": {"REQ-4": "holds"}})
    assert "REQ-4" in misspelt


def test_the_evidence_point_s_version_stays() -> None:
    """Taking a requirement's id is an addition to the point's schema, so its version stays
    (COR-052 point 5)."""
    package = load((CAPABILITY / "package.yaml").read_text(encoding="utf-8"))
    accepts = package["connections"]["extension-points"]["accepts"]
    assert accepts["pkit::analysis:revalidation-evidence"]["schema_version"] == 1


# --- each body rendered from its kind's declaration (#1366) --------------------------------

_RENDER, _STRUCTURE = load_lib("render", "structure")
RENDER: Any = _RENDER
STRUCTURE: Any = _STRUCTURE

#: Each template, and the kind whose declared structure renders its body.
KIND_OF = {
    "actor": "actor",
    "glossary": "term",
    "journey": "journey",
    "revalidation-record": "revalidation-record",
    "use-case": "use-case",
    **{kind: kind for kind in REQUIREMENTS},
}

#: The mark that opens a hint, and what closes it (#1366).
MARK, CLOSE = "<!-- pkit:hint ", " -->"


def _kind(name: str) -> Any:
    return STRUCTURE.read_kinds()[KIND_OF[name]]


@pytest.mark.parametrize("name", TEMPLATES)
def test_a_template_s_body_is_rendered_from_its_kind_s_declaration(name: str) -> None:
    """The template's front matter is written by hand and held to its kind's schema
    (above). Its body is its kind's structure rendered, and is held equal to it here, so
    it shows exactly the structure: every part, in order (DEC-001 point 1)."""
    assert set(KIND_OF) == set(TEMPLATES)
    assert _body(name) == RENDER.template(_kind(name), _template(name))


@pytest.mark.parametrize("name", TEMPLATES)
def test_each_part_a_writer_fills_holds_its_hint_and_a_record_none(name: str) -> None:
    """Each part a writer fills holds its hint as its placeholder, one marked line with
    its example, as the check's reader finds it. A revalidation record holds none, since
    its stamp writes every part (#1366)."""
    found = [said for _line, said in STRUCTURE.hints(STRUCTURE.body_lines(_body(name)))]
    if name == "revalidation-record":
        assert found == []
        assert "pkit:hint" not in _body(name)
        return
    filled = [e for e in _kind(name).sections if e.filled]
    hints = [RENDER.hint(e) for e in filled]
    assert [f"{MARK}{said}{CLOSE}" for said in found] == hints
    assert all(f"Example: {e.example}" in h for e, h in zip(filled, hints, strict=True))
    assert all(_body(name).count(h) == 1 for h in hints)


@pytest.mark.parametrize("name", TEMPLATES)
def test_a_template_misses_no_part_and_breaks_no_order(name: str) -> None:
    """Read against its kind's structure, a template carries every part in order: each
    part a writer fills is only empty, its hint being no content, and an opening holding
    only its hint reads as missing. The record's template, filled with each part's
    example, departs from nothing."""
    kind = _kind(name)
    lines = STRUCTURE.body_lines(_body(name))
    if kind.head:
        first = next(n for n, text in lines if text.startswith("## "))
        lines = [(n, text) for n, text in lines if n >= first]
    departing = STRUCTURE.departures(lines, kind, fields=_template(name))
    if name == "revalidation-record":
        assert departing == []
        return
    for departure in departing:
        element = departure.element
        assert element.filled, element.id
        assert departure.how == ("missing" if element.type == "opening" else "empty"), element.id


def test_a_hint_is_one_marked_comment_with_its_example() -> None:
    """The issue's own example of a part as stamped (#1366), with the goal's hint as the
    declaration words it."""
    goal = next(e for e in STRUCTURE.read_kinds()["use-case"].sections if e.id == "goal")
    assert RENDER.hint(goal) == (
        "<!-- pkit:hint What the actor wants from this use case, in one sentence in their own "
        "voice. Start with the verb, or with *Never* and the verb, with *I* and *my* where they "
        "refer to themselves. Example: Export my report as a file. -->"
    )
    assert f"**Goal:** {RENDER.hint(goal)}\n" in _body("use-case")


#: The front-matter fields the stamp leaves a writer to fill, by artefact template: each
#: holds its declared hint (#1593). A revalidation record's stamp writes every field. A
#: requirement's statement, measure and where it holds are a writer's, and its actors and
#: what it refines are written from what the stamp is given (#1691).
FIELDS_LEFT = {
    "actor": {"needs"},
    "glossary": {"definition"},
    "use-case": set(),
    "journey": set(),
    **{kind: {"statement", "measure", "applies-to"} for kind in REQUIREMENTS},
}


@pytest.mark.parametrize("name", sorted(FIELDS_LEFT))
def test_a_template_s_front_matter_shows_each_field_s_hint(name: str) -> None:
    """Each front-matter field the stamp leaves a writer to fill holds the field's declared
    hint, its placeholder, in the template's front matter, written by hand: the same text
    the stamp writes (`render.fields_left`), held equal here (#1593)."""
    front = _template(name)
    entry = next(iter(front.values())) if name == "glossary" else front
    left = RENDER.fields_left(_kind(name), entry)
    assert set(left) == FIELDS_LEFT[name]
    assert {field: entry[field] for field in left} == left
    for field, value in left.items():
        text = value[0] if isinstance(value, list) else value
        example = next(f.example for f in _kind(name).fields if f.name == field)
        assert STRUCTURE.hint_in(text).endswith(f"Example: {example}")


def test_a_field_s_hint_is_one_marked_line_found_by_its_mark() -> None:
    """A field's hint is one marked line, the comment a part's hint is, which a YAML parse
    reads as text. The check finds it by its mark, and not inside a code span (#1593)."""
    (needs,) = [f for f in STRUCTURE.read_kinds()["actor"].fields if f.name == "needs"]
    hint = RENDER.field_hint(needs)
    assert hint.startswith(MARK) and hint.endswith(CLOSE) and "\n" not in hint
    assert load(f"needs:\n  - '{hint}'\n") == {"needs": [hint]}
    assert STRUCTURE.hint_in(hint) == hint[len(MARK) : -len(CLOSE)]
    assert STRUCTURE.hint_in(f"Quote `{hint}` as code.") is None
    assert STRUCTURE.hint_in("Export my report as a file.") is None
