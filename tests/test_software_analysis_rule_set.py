"""software-analysis: the method rule set, `SAN`, and its format rule (#1360).

Held to software-analysis DEC-001 point 1 ("When it binds") and COR-051:

- the **set ships** under the name DEC-001 gives it, `SAN`, with no scope, as a
  method rule set takes none (COR-051 point 2);
- it holds the **format rule**, `RS-SAN-001`, proposed, its origin and its anchor
  DEC-001, and its *How* says where a sentence ends for the `sentence` form, and
  that a part of that form holds no list, in its own words, citing no project's
  rule;
- it holds the **append-only rule**, `RS-SAN-002`, proposed, its origin DEC-001 and
  its anchor DEC-001 point 3 (#1370);
- each rule **declares the part a check enforces** beside it, under `checks`: the
  format rule names the command behind the `software-analysis:artefacts` member of
  `pkit validate`, and the append-only rule `check-numbers`;
- **validation accepts the set**, and **it binds nothing while its rule is
  proposed**, even where a project set with a scope inherits it. Accepted, the
  same rule binds there, and its declared part is the check's.
"""

from __future__ import annotations

import json
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
STEPS_RULE = "RS-SAN-002"
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
    assert list(data["rules"]) == [RULE, STEPS_RULE]
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
    """At a mark followed by a space and a capital letter, or at the text's end, as the
    maintainer chose on 17 October (#1370): a mark before a lowercase letter ends none,
    a script without capital letters is never split, and no invisible character moves
    an end."""
    _data, body = _shipped()
    section = " ".join(_section(body, RULE).split())
    assert "- **How:**" in section
    assert "**The `sentence` form.**" in section
    assert "holds one sentence: no sentence ends before the text's last word." in section
    assert (
        "**Where a sentence ends.** At a full stop, a question mark or an exclamation mark "
        "followed by a space and a capital letter, and at the end of the text."
    ) in section
    assert (
        "Any white space counts as a space, such as a line end, several spaces or a no-break "
        "space. A character a reader cannot see, such as a zero-width space, counts as nothing."
    ) in section
    assert '"e.g. for" or "3. října", ends no sentence.' in section
    assert '"Dr. Smith" or "z. B. Rechnungen", so a writer rewords such a text.' in section
    assert (
        "**A script without capital letters,** such as Chinese or Arabic: a mark followed by "
        "one of its letters ends no sentence. So a text in such a script is never split."
    ) in section
    # Its own words: the only rule it names is itself, and no project's set.
    assert re.findall(r"RS-[A-Z][A-Z0-9]*-\d{3}", _section(body, RULE)) == [RULE]
    assert not re.search(r"\b(?:WRITE|ANA)\b", body)


def test_the_how_refuses_a_list_in_a_part_of_the_sentence_form() -> None:
    """A body part of the form is one text and holds no list, a quoted one included; a
    front-matter list stays one text per item, as the maintainer chose (#1370). The
    reading belongs to the `sentence` form alone, and the form's schema description
    points to the rule rather than restating it."""
    _data, body = _shipped()
    section = " ".join(_section(body, RULE).split())
    assert "Each text of this form, such as an actor's need, holds one sentence" in section
    assert (
        "**One text.** A body part of this form, such as a use case's *Goal*, is one text, "
        "and holds no Markdown list, not even inside a block quote. In a front-matter field that "
        "holds a list, such as an actor's `needs`, each item is one text."
    ) in section
    forms = section.split("**Forms.**", 1)[1].split("**Hints.**", 1)[0]
    assert "each item" not in forms
    schema = json.loads((CAPABILITY / "schemas" / "artefact-kinds.schema.json").read_text("utf-8"))
    (sentence,) = [f for f in schema["$defs"]["form"]["oneOf"] if f["const"] == "sentence"]
    assert (
        "RS-SAN-001, says what one text is, that a part of this form holds no list"
        in (sentence["description"])
    )
    assert "block quote" not in sentence["description"]


def test_the_append_only_rule_ships_proposed_from_dec_001_point_3() -> None:
    """A rule of its own, as the maintainer chose on 17 October (#1370): a use case's
    steps and variants keep their numbers and letters, which DEC-001 point 3 decides."""
    data, body = _shipped()
    entry = data["rules"][STEPS_RULE]
    assert entry["status"] == "proposed"
    assert entry["origin"] == {"decision": "software-analysis:DEC-001"}
    assert entry["pkit"]["friction"]["anchors"] == {"record": ["software-analysis:DEC-001#3"]}
    section = _section(body, STEPS_RULE)
    assert section.splitlines()[0] == (
        f"## {STEPS_RULE} — A use case's steps and variants keep their numbers and letters"
    )
    statement = section.split("\n\n")[1]
    assert statement == "A use case's steps and variants keep their numbers and letters."
    flat = " ".join(section.split())
    assert "A change renumbers no step its use case held before the change, and removes none." in (
        flat
    )
    assert "A new step takes a number past the last of its use case" in flat
    assert re.findall(r"RS-[A-Z][A-Z0-9]*-\d{3}", section) == [STEPS_RULE]


def test_the_append_only_rule_declares_check_numbers_as_its_check() -> None:
    """`check-numbers` binds under the append-only rule, never the format rule, so the
    rule declares it under `checks` (COR-051 point 2), and the command is registered."""
    data, _body = _shipped()
    assert "checks" not in data["rules"][STEPS_RULE]
    (declared,) = data["checks"][STEPS_RULE]
    assert declared["check"] == "software-analysis:check-numbers"
    part = " ".join(declared["part"].split())
    assert part.startswith(
        "Each step and each variant that a use case held where the change left its base, of a "
        "use case the working tree still holds, is neither renumbered nor removed."
    )
    assert "left to whoever judges the rest of the rule" in part
    assert [c["check"] for c in data["checks"][RULE]] == ["software-analysis:validate"]
    package = _yaml.load((CAPABILITY / "package.yaml").read_text(encoding="utf-8"))
    assert "check-numbers" in package["commands"]


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
        "A shipped part or front-matter field that the structure gives a form holds that "
        "form, save on a withdrawn artefact"
    ) in part
    # A missing title heading of a document kind is the heading check's, which holds it
    # whatever the rule's status, so the part leaves it out.
    assert "A missing title heading of an actor, a use case or a journey is left to" in part
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
    project.write({SAN_REL: text.replace("status: proposed", "status: accepted")})
    assert not rs.validate_rule_sets(project.root).errors
    assert _bound(project) == ["software-analysis:" + RULE, "software-analysis:" + STEPS_RULE]
    document = reading.reach_document(project.root)
    (entry,) = [a for a in document["artefacts"] if a["location"] == ACTOR]
    checks = {r["id"]: [(c["check"], c["there"]) for c in r["checks"]] for r in entry["rules"]}
    assert checks == {
        RULE: [("software-analysis:validate", True)],
        STEPS_RULE: [("software-analysis:check-numbers", True)],
    }
