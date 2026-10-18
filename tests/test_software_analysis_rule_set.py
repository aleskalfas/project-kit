"""software-analysis: the method rule set, `SAN`, and its format rule (#1360).

Held to software-analysis DEC-001 point 1 ("When it binds") and COR-051:

- the **set ships** under the name DEC-001 gives it, `SAN`, with no scope, as a
  method rule set takes none (COR-051 point 2);
- it holds the **format rule**, `RS-SAN-001`, accepted, its origin and its anchor
  DEC-001, and its *How* says where a sentence ends for the `sentence` form, and
  that a part of that form holds no list, in its own words, citing no project's
  rule;
- it holds the **append-only rule**, `RS-SAN-002`, accepted, its origin DEC-001 and
  its anchor DEC-001 point 3 (#1370);
- both rules were **accepted together**, on 17 October (#1370), so the set is at 1.0.0;
- it holds three **judgement rules**, `RS-SAN-003` to `RS-SAN-005` (#1577), each
  proposed, its origin DEC-001, declaring no check: a reviewer judges each. Each
  *How* leaves out what the stamp and the check hold always, and judges an artefact
  in force alone. Proposed rules move no version, so the set stays at 1.0.0;
- the **anchors rule**, `RS-SAN-005`, asks of a use case the anchors DEC-001 points
  4 and 11 give it, in their one direction: the decisions that answer it and the
  views that realise it, beside what it rests on (#1686). It asks of a requirement
  what DEC-002 point 6 gives it (#1695);
- the **record rule**, `RS-SAN-006`, compares a requirement's obligation with each
  accepted record it rests on, its origin DEC-002 and its anchor point 8 (#1695);
- the **source rule**, `RS-SAN-007`, asks each goal, minimal guarantee and
  requirement for its source, in the four forms the maintainer chose on 17 October
  (#1681). Both stay proposed with the others, so the set stays at 1.0.0;
- each rule **declares the part a check enforces** beside it, under `checks`: the
  format rule names the command behind the `software-analysis:artefacts` member of
  `pkit validate`, and the append-only rule `check-numbers`;
- **validation accepts the set**, and **it binds nothing while its rule is
  proposed**, even where a project set with a scope inherits it: a proposed copy
  shows it. Accepted, as shipped, the same rule binds there, and its declared part
  is the check's.
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
from tests.analysis_repo import CAPABILITY, SA, actor_at, installed, with_status
from tests.test_rule_sets import rule_set_text

Kind = rs.RuleSetFindingKind

SAN = CAPABILITY / "rule-sets" / "san.md"
SAN_REL = f"{SA.as_posix()}/rule-sets/san.md"
RULE = "RS-SAN-001"
STEPS_RULE = "RS-SAN-002"
#: The judgement rules (#1577, #1695, #1681): each statement, and the record points it
#: anchors to.
JUDGEMENT_RULES = {
    "RS-SAN-003": (
        "A use case's actor is the one whose goal it is, and each other actor that takes "
        "part in it is one of its `other-actors`.",
        [
            "software-analysis:DEC-001#1",
            "software-analysis:DEC-001#3",
            "software-analysis:DEC-001#4",
        ],
    ),
    "RS-SAN-004": (
        "A use case's goal is one of its actor's needs.",
        ["software-analysis:DEC-001#1"],
    ),
    "RS-SAN-005": (
        "An analysis artefact's anchors name what its statements rest on. A use case's or "
        "a requirement's anchors also name the decisions that answer it and the "
        "architecture views that realise it.",
        [
            "software-analysis:DEC-001#2",
            "software-analysis:DEC-001#4",
            "software-analysis:DEC-001#9",
            "software-analysis:DEC-001#11",
            "software-analysis:DEC-002#5",
            "software-analysis:DEC-002#6",
            "COR-050#1",
            "COR-050#2",
            "COR-050#5",
        ],
    ),
    "RS-SAN-006": (
        "A requirement never contradicts an accepted decision record it rests on.",
        [
            "software-analysis:DEC-002#4",
            "software-analysis:DEC-002#6",
            "software-analysis:DEC-002#8",
        ],
    ),
    "RS-SAN-007": (
        "Each goal, minimal guarantee and requirement names its source.",
        [
            "software-analysis:DEC-001#1",
            "software-analysis:DEC-001#4",
            "software-analysis:DEC-001#11",
            "software-analysis:DEC-002#4",
            "software-analysis:DEC-002#6",
            "software-analysis:DEC-002#8",
        ],
    ),
}
#: Each judgement rule's origin, where a decision record holds it. The source rule's is
#: the maintainer's decision of 17 October (#1648, choice 6), which no record holds.
ORIGINS = {
    "RS-SAN-003": "software-analysis:DEC-001",
    "RS-SAN-004": "software-analysis:DEC-001",
    "RS-SAN-005": "software-analysis:DEC-001",
    "RS-SAN-006": "software-analysis:DEC-002",
}
SOURCE_RULE = "RS-SAN-007"
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
    # Accepting its first rules was a new major (COR-051 point 7): the maintainer
    # accepted both on 17 October (#1370), and the set reached 1.0.0 with them.
    assert data["version"] == "1.0.0"


def test_the_set_holds_the_format_rule_accepted_its_origin_dec_001() -> None:
    data, body = _shipped()
    assert list(data["rules"]) == [RULE, STEPS_RULE, *JUDGEMENT_RULES]
    entry = data["rules"][RULE]
    assert entry["status"] == "accepted"
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
        "**Where a sentence ends.** At `.`, `?` or `!` followed by a space and a capital "
        "letter, and at the end of the text. No other mark ends a sentence"
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


def test_the_append_only_rule_ships_accepted_from_dec_001_point_3() -> None:
    """A rule of its own, as the maintainer chose and accepted on 17 October (#1370): a
    use case's steps and variants keep their numbers and letters, which DEC-001 point 3
    decides."""
    data, body = _shipped()
    entry = data["rules"][STEPS_RULE]
    assert entry["status"] == "accepted"
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
    assert "A new step takes a number higher than every number of its use case" in flat
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
    assert "Whoever judges the rest of the rule judges these" in part
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


def test_the_judgement_rules_ship_proposed_declaring_no_check() -> None:
    """The maintainer's three judgement rules (8 October, on #1360), proposed until he
    accepts them (#1577), each with DEC-001 as its origin. Beside them the record rule,
    from DEC-002 point 8 (#1695), and the source rule (#1681), proposed until all are
    accepted in one major. Each anchors to the points it rests on. None declares a
    check: a reviewer judges each (COR-057). A proposed rule moves no version (COR-051
    point 7), so `SAN` stays at 1.0.0."""
    data, body = _shipped()
    assert data["version"] == "1.0.0"
    assert set(ORIGINS) | {SOURCE_RULE} == set(JUDGEMENT_RULES)
    for rule_id, (statement, anchors) in JUDGEMENT_RULES.items():
        entry = data["rules"][rule_id]
        assert entry["status"] == "proposed", rule_id
        if rule_id in ORIGINS:
            assert entry["origin"] == {"decision": ORIGINS[rule_id]}, rule_id
        assert entry["pkit"]["friction"]["anchors"] == {"record": anchors}, rule_id
        # A change to a point it rests on asks for its revalidation, so it may carry
        # one. It carries no deferral and no reason for having no anchors.
        assert set(entry["pkit"]["friction"]) <= {"anchors", "revalidated"}, rule_id
        revalidated = entry["pkit"]["friction"].get("revalidated", {})
        assert isinstance(revalidated, dict), rule_id
        assert "deferred" not in revalidated, rule_id
        assert rule_id not in data["checks"], rule_id
        assert "checks" not in entry, rule_id
        section = _section(body, rule_id)
        assert section.split("\n\n")[1] == statement, rule_id
        assert "- **How:**" in section, rule_id


def test_each_judgement_rule_leaves_the_checks_their_part_by_its_own_words() -> None:
    """What the stamp and the check refuse whatever any rule's status is no part of a
    judgement rule: its *How* names it and leaves it out, rather than declaring a check
    under `checks`, which binds a check only where the rule binds (COR-051 point 2).
    The anchors rule's list of what its anchors name is whole, so it never asks for an
    anchor DEC-001 point 4 does not give."""
    _data, body = _shipped()
    for rule_id in ("RS-SAN-003", "RS-SAN-005"):
        section = " ".join(_section(body, rule_id).split())
        assert "**What the check holds.** The " in section, rule_id
        assert "whatever any rule's status, and this rule does not cover it." in section, rule_id
    goal = " ".join(_section(body, "RS-SAN-004").split())
    # Found by the part's permanent id, so a project's own label never hides it.
    assert "The goal is the use case's part whose id is `goal`, whatever label" in goal
    assert "a narrower want than one of them." in goal
    assert "**What the check holds.**" not in goal  # no check holds any of it
    anchors = " ".join(_section(body, "RS-SAN-005").split())
    assert "This list is whole:" in anchors
    assert "**What this rule judges.** The rest: - the code and the decisions" in anchors
    # Unanchored is a state the core reports, never a failure (DEC-001 point 4), and the
    # rule judges it all the same. A reason for having none is a person's answer, never
    # judged here (COR-050 point 1; COR-057 point 1).
    unanchored = "no check fails on it. This rule still judges what its statements rest on."
    assert unanchored in anchors
    assert "An actor or a term that gives a reason for having none is not judged" in anchors
    assert "The reason is a person's answer, and only a person decides it." in anchors


def _anchors_list(body: str) -> dict[str, str]:
    """The anchors rule's whole list of what an artefact's anchors name, one item per
    kind, keyed by the kind it opens with."""
    section = _section(body, "RS-SAN-005")
    _head, found, rest = section.partition("  - **What its anchors name.**")
    assert found, "RS-SAN-005 has no item labelled What its anchors name"
    block, found, _tail = rest.partition("\n  - **Nothing else.**")
    assert found, "RS-SAN-005 has no item labelled Nothing else"
    items = [" ".join(item.split()) for item in re.split(r"\n {4}- ", block)[1:]]
    listed = {item.split(" rests on ", 1)[0]: item for item in items}
    assert len(listed) == len(items), "two kinds open their items alike"
    return listed


def test_the_anchors_rule_asks_a_use_case_for_what_answers_or_realises_it() -> None:
    """DEC-001 points 4 and 11 (#1686): a use case anchors each decision it rests on or
    is answered by, and each architecture view that realises it. The rule's list, its
    finder, the anchor each takes, what it judges and its break all reach the two, so
    an anchor on either is never judged unasked once the rule is accepted."""
    _data, body = _shipped()
    listed = _anchors_list(body)
    assert list(listed) == ["An actor or a term", "A use case", "A journey", "A requirement"]
    use_case = listed["A use case"]
    # What a use case rests on is what its statements cite or apply, as point 11's
    # "rests on" reads. Point 4's "relies on" also takes in the decisions that answer
    # it, which the rule names apart.
    assert "the decisions it cites or applies." in use_case
    assert "relies on" not in use_case
    assert (
        "Its anchors also name each decision that answers it and each architecture view "
        "that realises it. Each is asked for even where none of the use case's statements "
        "names it, since a change to it can leave the use case untrue of the system."
    ) in use_case
    section = " ".join(_section(body, "RS-SAN-005").split())
    # The finder reaches each, narrowed by DEC-001's own words: a record made to meet
    # what the use case asks, and a view made to show how the system carries it out, so
    # a decision or a view of the whole system is not asked of every use case. It says
    # where the records lie.
    assert "**The decisions an artefact rests on** are the records its statements cite or" in (
        section
    )
    assert "An actor's or a term's are also the records that embody it." in section
    assert (
        "**The decisions that answer a use case or a requirement** are the records made to "
        "meet what it asks"
    ) in section
    # Where they lie, in point 11's own words: no kind of record is left out.
    assert "Each may be a core record, a capability's record or the project's own." in section
    assert (
        "**The views that realise a use case or a requirement** are the architecture views the "
        "project keeps to show how the system carries it out."
    ) in section
    assert (
        "A view a place holds takes an artefact anchor, and any other view takes a path "
        "anchor on its file."
    ) in section
    # Nothing that decides nothing, and nothing no anchor can name: a record not
    # accepted, and a view outside the repository.
    assert "a decision that is not accepted: one not yet recorded, a proposed one or a " in (
        section
    )
    assert "a view the project does not keep, or keeps outside its repository" in section
    assert (
        "**What this rule judges.** The rest: - the code and the decisions a statement rests "
        "on - the decisions that answer a use case or a requirement, and the views that "
        "realise one"
    ) in section
    assert (
        "A use case or a requirement also breaks it while no anchor names a decision that "
        "answers it, or a view that realises it."
    ) in section


@pytest.mark.parametrize("kind", ["An actor or a term", "A journey"])
def test_the_anchors_rule_asks_no_other_kind_for_what_answers_it(kind: str) -> None:
    """Only a use case and a requirement are answered by a decision or realised by a
    view (DEC-001 point 11, DEC-002 point 6): an actor, a term or a journey anchors what
    point 4 gives it, and nothing more."""
    _data, body = _shipped()
    item = _anchors_list(body)[kind]
    assert not re.search(r"\b(?:answers?|answered|realises?|realised|views?)\b", item)


def test_the_anchors_rule_keeps_its_anchors_against_a_cycle_back() -> None:
    """The analysis points at the solution, never the reverse (DEC-001 point 11). So no
    cycle excuses an anchor the rule asks for on a decision or a view: the rule holds no
    exemption that would let it give way to an anchor back. It sets nothing on the
    decision or the view, which it does not bind."""
    _data, body = _shipped()
    section = " ".join(_section(body, "RS-SAN-005").split())
    assert "Nor does this rule ask for an anchor" not in section
    assert (
        "**No cycle excuses it.** An anchor this list asks for on a decision or a view is "
        "asked for even where anchors that run back from that decision or view would close "
        "a cycle."
    ) in section
    assert "solution's side" not in section


def test_the_anchors_rule_asks_a_requirement_for_what_dec_002_point_6_gives() -> None:
    """A requirement anchors each record it rests on or is answered by, each view that
    realises it, the files that verify it, the narrow code that holds it, its actors and
    the requirements it refines (DEC-002 points 5 and 6, #1695). The check that holds
    its anchors on its actors and the requirements it refines is not built yet, so the
    rule judges them, and its `What the check holds` names no requirement."""
    _data, body = _shipped()
    item = _anchors_list(body)["A requirement"]
    for asked in (
        "each actor in its `actors`",
        "each requirement in its `refines`",
        "the decisions it cites or applies",
        "the narrow code that holds it and the files that verify it",
        "each decision that answers it and each architecture view that realises it",
        "Each is asked for even where none of its statements names it.",
    ):
        assert asked in item, asked
    section = " ".join(_section(body, "RS-SAN-005").split())
    assert (
        "**The files that verify a requirement** are the files of the tests and checks named "
        "in its part whose id is `verified-by`."
    ) in section
    # Narrow, in words every adopter's requirement fits: no word of one kind of system.
    assert (
        "**The code that holds a requirement** is the code that keeps it, never all the code "
        "its `applies-to` reaches."
    ) in section
    assert "command" not in section
    # Judged until a check holds them, and a missing one is a break.
    judged = section.split("**What this rule judges.**", 1)[1].split("**A break.**")[0]
    assert "- a requirement's anchors on its `actors` and its `refines`" in judged
    held = section.split("**What the check holds.**", 1)[1].split("**What this rule judges.**")[0]
    assert "requirement" not in held
    assert (
        "A requirement breaks it too while no anchor names an actor in its `actors`, or a "
        "requirement in its `refines`."
    ) in section
    # A reason for having none means no actor and no requirement it refines (DEC-002
    # point 6), so a requirement that lists either is still judged.
    assert ("Nor is a requirement that gives one, with no `actors` and no `refines`.") in section


def test_the_record_rule_compares_the_obligation_with_the_records_it_rests_on() -> None:
    """DEC-002 point 8 (#1695): a requirement that contradicts an accepted record it rests
    on breaks the rule, and the record wins until it is changed. The rule compares the
    three fields that state the obligation with the records the requirement anchors, and
    leaves a conflict between two requirements to a decision record."""
    _data, body = _shipped()
    section = " ".join(_section(body, "RS-SAN-006").split())
    assert (
        "**What it compares.** A requirement's `statement`, its `measure` and its `applies-to`, "
        "with each accepted decision record it rests on."
    ) in section
    assert "They are the records its record anchors name, each whole or the point its anchor" in (
        section
    )
    # What it rests on is told by what the anchor is for, never by agreement: all a
    # record decides, save a decision made to meet the requirement, which answers it.
    assert "The requirement rests on what they decide, save a decision made to meet what it" in (
        section
    )
    assert "That decision answers it, and this rule compares nothing with it." in section
    # Only what is in force: no proposed or superseded record, and no point another
    # record overturns (COR-058 point 5).
    assert "A proposed record decides nothing yet, and a superseded one no longer does." in (
        section
    )
    assert "Nor does a point another record overturns." in section
    # Both ways: a measure that accepts what the record rules out, or rules out what it
    # requires.
    assert (
        "it accepts what the record rules out, or rules out what the record requires."
    ) in section
    assert "So a measure looser than a limit the record sets contradicts the record." in section
    assert "a stricter one" not in section
    assert "**The record wins.**" in section
    assert "changes the requirement, or has the record changed first." in section
    assert (
        "**Two requirements.** A conflict between two requirements is no break of this rule. "
        "It is a choice, so a decision record holds it."
    ) in section


def test_the_source_rule_takes_any_of_the_four_forms_the_maintainer_chose() -> None:
    """The maintainer's decision of 17 October (#1648, choice 6; #1681): each goal,
    guarantee and requirement names its source, in any of four forms. No record holds
    the decision, so the rule's origin is his: its date and its decider. Its why, in his
    own words, is his to give when he accepts it (COR-051 point 5)."""
    data, body = _shipped()
    origin = data["rules"][SOURCE_RULE]["origin"]
    assert set(origin) == {"date", "by"}
    assert str(origin["date"]) == "2026-10-17"
    assert origin["by"] == "Aleš Kalfas"
    section = " ".join(_section(body, SOURCE_RULE).split())
    for form in (
        "**A record.** An accepted decision record the artefact anchors",
        "**A requirement's reason.** Its part whose id is `rationale`, or `imposed-by` on a "
        "constraint",
        "**Existing behaviour.** Code the artefact anchors, which already does what the item",
        "**A quoted decision.** The words of the person who decided, quoted in the artefact's "
        "body, with their name and the date. The quote names the item it sources, in its text "
        "or a label beside it, or it stands beside the item.",
    ):
        assert form in section, form
    # A source names only what it bears out, so a requirement's sources cover its
    # statement and any value its measure sets, and code shows what the system does,
    # never how well.
    assert "**What a source bears out.** A source names only what it bears out." in section
    assert "- A reason bears out what it says the system needs." in section
    assert "Its sources together cover both." in section
    assert "so this form sources no value a `measure` sets." in section
    assert "A point another record overturns decides nothing." in section
    assert "**Nothing else.** Anything else is no source" in section
    assert "the need a goal states is no source of the goal" in section


def test_the_new_rules_name_parts_each_kind_declares() -> None:
    """The source rule and the anchors rule find a part by its permanent id, so a
    project's own label never hides it. Each id they name is one the kinds' declared
    structure gives the kind the rule reads it on."""
    kinds = _yaml.load((CAPABILITY / "schemas" / "artefact-kinds.yaml").read_text("utf-8"))

    def ids(kind: str) -> set[str]:
        return {section["id"] for section in kinds["kinds"][kind]["sections"]}

    requirements = ("quality-requirement", "functional-requirement", "constraint")
    for kind in ("use-case", "journey"):
        assert {"goal", "minimal-guarantees"} <= ids(kind), kind
    for kind in requirements:
        assert "verified-by" in ids(kind), kind
        assert {"statement", "measure", "applies-to", "actors", "refines"} <= set(
            kinds["kinds"][kind]["front-matter"]
        ), kind
    assert "rationale" in ids("quality-requirement") & ids("functional-requirement")
    assert "imposed-by" in ids("constraint")
    assert "rationale" not in ids("constraint")


def test_each_judgement_rule_judges_an_artefact_in_force_alone() -> None:
    """A withdrawn artefact is history (DEC-001 point 1), so no judgement rule reaches
    back into it, and each rule names no other rule of a project's set."""
    _data, body = _shipped()
    for rule_id in JUDGEMENT_RULES:
        section = " ".join(_section(body, rule_id).split())
        assert "**History.** This rule judges " in section, rule_id
        assert "in force. A withdrawn " in section, rule_id
        assert set(re.findall(r"RS-[A-Z][A-Z0-9]*-\d{3}", section)) == {rule_id}, rule_id


# --- validation and reach in an adopter (COR-051 points 4 and 7) ---------------------------


def _with_an_actor_and_a_set_inheriting_san(project: AdopterRepo, *, major: int = 1) -> None:
    project.write(
        {
            ACTOR: "---\nid: ACT-tester\nname: Tester\nneeds: [Run a suite.]\n---\n\n"
            "# ACT-tester — Tester\n",
            ANALYSIS_SET: rule_set_text(
                {
                    "rule-set": "ANALYSIS",
                    "version": "1.0.0",
                    "inherits": [f"software-analysis:SAN@{major}"],
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
    yet a proposed rule binds nothing (COR-051 point 4). `SAN` ships its rules accepted,
    so a proposed copy is the fixture."""
    _with_an_actor_and_a_set_inheriting_san(project)
    text = (project.root / SAN_REL).read_text(encoding="utf-8")
    project.write({SAN_REL: text.replace("status: accepted", "status: proposed")})
    assert not rs.validate_rule_sets(project.root).errors
    assert "software-analysis:" + RULE not in _bound(project)
    document = reading.reach_document(project.root)
    assert not any(rule["id"] == RULE for entry in document["artefacts"] for rule in entry["rules"])


def test_accepted_the_same_rule_binds_and_its_part_is_the_check_s(project: AdopterRepo) -> None:
    """The control: the route above carries the rule as `SAN` ships it, accepted, and
    the part it declares names a check that is there, so a reviewer leaves it to the
    check."""
    _with_an_actor_and_a_set_inheriting_san(project)
    assert not rs.validate_rule_sets(project.root).errors
    assert _bound(project) == ["software-analysis:" + RULE, "software-analysis:" + STEPS_RULE]
    document = reading.reach_document(project.root)
    (entry,) = [a for a in document["artefacts"] if a["location"] == ACTOR]
    checks = {r["id"]: [(c["check"], c["there"]) for c in r["checks"]] for r in entry["rules"]}
    assert checks == {
        RULE: [("software-analysis:validate", True)],
        STEPS_RULE: [("software-analysis:check-numbers", True)],
    }


def test_the_judgement_rules_bind_nothing_while_proposed(project: AdopterRepo) -> None:
    """As `SAN` ships them, on the route above: validation accepts the set, and no
    judgement rule binds, since a proposed rule binds nothing (COR-051 point 4)."""
    _with_an_actor_and_a_set_inheriting_san(project)
    assert not rs.validate_rule_sets(project.root).errors
    # The route binds the two accepted rules, so it is there, and nothing more.
    assert _bound(project) == ["software-analysis:" + RULE, "software-analysis:" + STEPS_RULE]


#: The source rule's origin as it ships, with no why.
_SOURCE_ORIGIN = 'origin: {date: 2026-10-17, by: "Aleš Kalfas"}'


def _source_rule_with_its_why(text: str) -> str:
    """`SAN`'s text with the source rule's origin complete, as a fixture."""
    assert text.count(_SOURCE_ORIGIN) == 1
    return text.replace(
        _SOURCE_ORIGIN, _SOURCE_ORIGIN[:-1] + ', why: "The decider\'s reason, in his words."}'
    )


def test_the_source_rule_cannot_be_accepted_without_its_why(project: AdopterRepo) -> None:
    """Its origin ships with its date and its decider only. An accepted rule carries a
    complete origin (COR-051 point 5), so a copy that accepts it as shipped fails
    validation on its `why`, and passes once the why is given."""
    _with_an_actor_and_a_set_inheriting_san(project, major=2)
    text = with_status(
        (project.root / SAN_REL).read_text(encoding="utf-8"), SOURCE_RULE, "accepted"
    ).replace("version: 1.0.0", "version: 2.0.0", 1)
    project.write({SAN_REL: text})
    (error,) = rs.validate_rule_sets(project.root).errors
    assert error.location == f"{SAN_REL}#{SOURCE_RULE}"
    assert error.pointer == "/origin"
    assert "lacks `why`" in error.message
    project.write({SAN_REL: _source_rule_with_its_why(text)})
    assert not rs.validate_rule_sets(project.root).errors


def test_accepted_each_judgement_rule_binds_with_no_check_to_leave(
    project: AdopterRepo,
) -> None:
    """A copy with the judgement rules accepted, a fixture and not the acceptance: each
    binds on the route above, and the answer gives it no check's part, so a reviewer
    judges the whole of it (COR-057 point 1). Accepting a rule gives `SAN` a new major,
    and the set re-pins to it, as an acceptance would (COR-051 point 7). The source
    rule's origin gains its why, as its acceptance must give it."""
    _with_an_actor_and_a_set_inheriting_san(project, major=2)
    text = _source_rule_with_its_why((project.root / SAN_REL).read_text(encoding="utf-8"))
    for rule_id in JUDGEMENT_RULES:
        text = with_status(text, rule_id, "accepted")
    project.write({SAN_REL: text.replace("version: 1.0.0", "version: 2.0.0", 1)})
    assert not rs.validate_rule_sets(project.root).errors
    assert _bound(project) == [
        "software-analysis:" + r for r in (RULE, STEPS_RULE, *JUDGEMENT_RULES)
    ]
    document = reading.reach_document(project.root)
    (entry,) = [a for a in document["artefacts"] if a["location"] == ACTOR]
    checks = {r["id"]: r["checks"] for r in entry["rules"]}
    assert [checks[rule_id] for rule_id in JUDGEMENT_RULES] == [[]] * len(JUDGEMENT_RULES)
