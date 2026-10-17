"""software-analysis: the method rule set, `SAN`, and its format rule (#1360).

Held to software-analysis DEC-001 point 1 ("When it binds") and COR-051:

- the **set ships** under the name DEC-001 gives it, `SAN`, with no scope, as a
  method rule set takes none (COR-051 point 2);
- it holds the **format rule**, `RS-SAN-001`, proposed, its origin and its anchor
  DEC-001, and its *How* says where a sentence ends for the `sentence` form, in
  its own words, citing no project's rule;
- the rule **declares the part a check enforces** beside it, under `checks`, naming
  the command behind the `software-analysis:artefacts` member of `pkit validate`;
- **validation accepts the set**, and **it binds nothing while its rule is
  proposed**, even where a project set with a scope inherits it. Accepted, the
  same rule binds there, and its declared part is the check's.
"""

from __future__ import annotations

import re
from typing import Any

import pytest
from ruamel.yaml import YAML

from project_kit import document_parts
from project_kit import rule_set_reading as reading
from project_kit import rule_sets as rs
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.analysis_repo import CAPABILITY, SA, actor_at, installed
from tests.test_rule_sets import rule_set_text

Kind = rs.RuleSetFindingKind

SAN = CAPABILITY / "rule-sets" / "san.md"
SAN_REL = f"{SA.as_posix()}/rule-sets/san.md"
RULE = "RS-SAN-001"
ACTOR = actor_at("ACT-tester")

#: A set of the project's own whose scope selects the analysis's actors, inheriting
#: `SAN` at the major it ships: the route COR-051 point 7 asks for.
ANALYSIS_SET = "tech-docs/rule-sets/analysis.md"

_yaml: Any = YAML(typ="safe")


def _shipped() -> tuple[dict[str, Any], str]:
    front_matter, body = document_parts.split_front_matter(SAN.read_text(encoding="utf-8"))
    assert front_matter is not None
    return _yaml.load(front_matter), body


def _forms_by_owner() -> tuple[set[str], set[str]]:
    """The forms the artefact kinds' structure gives, and those the revalidation
    record's gives, as `schemas/artefact-kinds.yaml` declares them."""
    kinds = _yaml.load((CAPABILITY / "schemas" / "artefact-kinds.yaml").read_text("utf-8"))
    artefacts: set[str] = set()
    records: set[str] = set()
    for name, kind in kinds["kinds"].items():
        elements = [*kind.get("sections", []), *kind.get("front-matter", {}).values()]
        forms = {element["form"] for element in elements if "form" in element}
        (records if name == "revalidation-record" else artefacts).update(forms)
    return artefacts, records


def _section(body: str, rule_id: str) -> str:
    """The body section headed by `rule_id`, read as the rule-set reader reads it."""
    section = document_parts.entry_section(body, rule_id)
    assert section, f"no section headed by {rule_id}"
    return section


@pytest.fixture
def project(make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch) -> AdopterRepo:
    return installed(make_adopter_repo, monkeypatch)


# --- what ships (DEC-001 point 1) ----------------------------------------------------------


def test_the_set_ships_under_dec_001_s_name_with_no_scope() -> None:
    data, _body = _shipped()
    assert data["rule-set"] == "SAN"
    assert "scope" not in data  # a method rule set takes none (COR-051 point 2)
    assert "inherits" not in data
    # No accepted rule yet, so no major: accepting its first rule is a new major
    # (COR-051 point 7), and the set reaches 1.0.0 with it.
    assert data["version"].split(".")[0] == "0"


def test_the_set_holds_the_format_rule_proposed_its_origin_dec_001() -> None:
    data, body = _shipped()
    assert list(data["rules"]) == [RULE]
    entry = data["rules"][RULE]
    assert entry["status"] == "proposed"
    assert entry["origin"] == {"decision": "software-analysis:DEC-001"}
    assert entry["pkit"]["friction"]["anchors"] == {"record": ["software-analysis:DEC-001"]}
    statement = _section(body, RULE).split("\n\n")[1]
    # An analysis artefact alone: no rule binds on a record, a held document, so the
    # capability checks a record's structure itself (DEC-001 point 1, #1475). No clause
    # an artefact cannot break, such as a template per kind (COR-051 point 1, #1370).
    assert " ".join(statement.split()) == (
        "An analysis artefact carries its kind's declared structure."
    )


def test_the_how_says_where_a_sentence_ends_citing_no_project_s_rule() -> None:
    _data, body = _shipped()
    section = _section(body, RULE)
    assert "- **How:**" in section
    assert "**The `sentence` form.**" in section
    assert "holds one sentence: no sentence ends before the text's last word." in section
    assert (
        "A sentence ends at a full stop, a question mark or an exclamation mark. It ends "
        "there only where a space, a line end or the end of the text follows the mark."
    ) in section
    # Its own words: the only rule it names is itself, and no project's set.
    assert re.findall(r"RS-[A-Z][A-Z0-9]*-\d{3}", section) == [RULE]
    assert not re.search(r"\b(?:WRITE|ANA)\b", body)


def test_the_how_reads_a_list_of_the_sentence_form_item_by_item() -> None:
    """Each item of a list holds one sentence, a nested item apart, and so does the rest
    of the part, as the check reads it (#1365). The reading belongs to the `sentence`
    form alone: a form that reads a list is no item's (#1370)."""
    _data, body = _shipped()
    section = " ".join(_section(body, RULE).split())
    assert (
        "In a list, each item holds one sentence of its own, and a nested item holds one "
        "apart from the item it sits in."
    ) in section
    # The rest of the part is one text, and a list in a block quote is part of it, as
    # the check's list reader leaves a quoted line outside every list (`_lib/forms.py`).
    assert (
        "Any text the part holds outside its lists is taken as one text, and holds one "
        "sentence too. A list inside a block quote is such text, not a list."
    ) in section
    assert "In a front-matter field that holds a list" in section
    forms = section.split("**Forms.**", 1)[1].split("**Hints.**", 1)[0]
    assert "each item" not in forms


def test_the_how_holds_the_glossary_s_head_where_the_rule_binds_on_a_term() -> None:
    """The head belongs to no term, but it is part of the term kind's structure, so it
    is held wherever the rule binds on a term of its file (DEC-001 point 1)."""
    _data, body = _shipped()
    section = " ".join(_section(body, RULE).split())
    assert "**The glossary's head.**" in section
    assert "Where this rule binds on a term, the glossary that holds it carries its head." in (
        section
    )


def test_the_format_rule_declares_the_part_the_capability_s_check_enforces() -> None:
    """Beside the rule, never in its entry (COR-051 point 2), naming the command the
    `software-analysis:artefacts` member of `pkit validate` runs."""
    data, _body = _shipped()
    assert "checks" not in data["rules"][RULE]
    (declared,) = data["checks"][RULE]
    assert declared["check"] == "software-analysis:validate"
    # The parts a kind ships, the glossary's head and the forms its structure gives, as
    # far as the check holds them: a withdrawn artefact to neither a part it lacks nor a
    # form (DEC-001 point 1). A record is no part of the rule, which binds on artefacts
    # alone (#1475), so neither are a record's two forms (#1370).
    part = " ".join(declared["part"].split())
    assert part.startswith("Every part its kind ships is present,")
    assert "The glossary carries its head wherever the rule binds on one of its terms." in part
    assert (
        "front-matter field that the structure gives a form holds that form, "
        "save on a withdrawn artefact"
    ) in part
    assert (
        "one sentence in each item of a list, a nested item apart, and in any text of its "
        "part outside its lists, a list in a block quote included."
    ) in part
    # A document's title heading is left out: the heading check holds it always.
    assert "A document's title heading is left out" in part
    assert "record" not in part
    # It names each form an artefact kind's structure gives, and none that only a
    # record's gives: the check enforces those always, outside the rule.
    forms = part.split("The forms are", 1)[1].split(", each as", 1)[0]
    named = set(re.findall(r"`([a-z-]+)`", forms))
    artefact_forms, record_forms = _forms_by_owner()
    assert named == artefact_forms
    assert not named & (record_forms - artefact_forms)
    package = _yaml.load((CAPABILITY / "package.yaml").read_text(encoding="utf-8"))
    assert package["validators"]["artefacts"]["command"] == "validate"
    assert "validate" in package["commands"]


# --- validation and reach in an adopter (COR-051 points 4 and 7) ---------------------------


def _with_an_actor_and_a_set_inheriting_san(project: AdopterRepo) -> None:
    project.write(
        {
            ACTOR: "---\nid: ACT-tester\nname: Tester\nneeds: [Run a suite.]\n---\n\n"
            "# ACT-tester — Tester\n",
            ANALYSIS_SET: rule_set_text(
                {
                    "rule-set": "ANALYSIS",
                    "version": "1.0.0",
                    "inherits": ["software-analysis:SAN@0"],
                    "scope": {"types": ["software-analysis:actor"]},
                    "rules": {},
                }
            ),
        }
    )


def _bound(project: AdopterRepo) -> list[str]:
    _discovery, _sets, answer = rs.reach_at(project.root)
    return [b.rule_set.cite(b.rule.id) for b in answer.of(ACTOR).bindings]


def test_validation_accepts_the_set_as_the_capability_s_method_set(project: AdopterRepo) -> None:
    result = rs.validate_rule_sets(project.root)
    # The schema was there to judge the set, so no finding means it passed.
    assert Kind.SCHEMA_UNAVAILABLE not in [f.kind for f in result.findings]
    (san,) = result.discovery.sets_named("SAN")
    assert (san.path, san.citation) == (SAN_REL, "software-analysis:SAN")
    assert [f.where for f in result.findings if f.location.startswith(SAN_REL)] == []


def test_the_set_binds_nothing_while_its_rule_is_proposed(project: AdopterRepo) -> None:
    """A project set whose scope selects an actor inherits `SAN`: the route is there,
    yet a proposed rule binds nothing (COR-051 point 4)."""
    _with_an_actor_and_a_set_inheriting_san(project)
    assert not rs.validate_rule_sets(project.root).errors
    assert "software-analysis:" + RULE not in _bound(project)
    document = reading.reach_document(project.root)
    assert not any(rule["id"] == RULE for entry in document["artefacts"] for rule in entry["rules"])


def test_accepted_the_same_rule_binds_and_its_part_is_the_check_s(project: AdopterRepo) -> None:
    """The control: the route above carries the rule once it is accepted, and the part
    it declares names a check that is there, so a reviewer leaves it to the check."""
    _with_an_actor_and_a_set_inheriting_san(project)
    # A fixture, not the acceptance procedure: accepting the rule also takes the set
    # to a new major (COR-051 point 7), which validation does not hold it to.
    text = (project.root / SAN_REL).read_text(encoding="utf-8")
    project.write({SAN_REL: text.replace("status: proposed", "status: accepted", 1)})
    assert not rs.validate_rule_sets(project.root).errors
    assert _bound(project) == ["software-analysis:" + RULE]
    document = reading.reach_document(project.root)
    (entry,) = [a for a in document["artefacts"] if a["location"] == ACTOR]
    (rule,) = [r for r in entry["rules"] if r["id"] == RULE]
    assert [(c["check"], c["there"]) for c in rule["checks"]] == [
        ("software-analysis:validate", True)
    ]
