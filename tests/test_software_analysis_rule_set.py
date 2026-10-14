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


def _section(body: str, rule_id: str) -> str:
    """The body section headed by `rule_id`, up to the next heading of its level."""
    match = re.search(rf"^## {rule_id} — .*?(?=^## |\Z)", body, re.MULTILINE | re.DOTALL)
    assert match is not None, f"no section headed by {rule_id}"
    return match.group(0)


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
    assert statement == (
        "An analysis artefact or a revalidation record carries its kind's declared "
        "structure, and each kind has a template."
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


def test_the_format_rule_declares_the_part_the_capability_s_check_enforces() -> None:
    """Beside the rule, never in its entry (COR-051 point 2), naming the command the
    `software-analysis:artefacts` member of `pkit validate` runs."""
    data, _body = _shipped()
    assert "checks" not in data["rules"][RULE]
    (declared,) = data["checks"][RULE]
    assert declared["check"] == "software-analysis:validate"
    # The parts a kind ships, the forms its structure gives, and the structure a
    # record or a withdrawn artefact is held to (DEC-001 point 1).
    assert declared["part"].startswith("Every part its kind ships is present,")
    assert "front-matter field that the structure gives a form" in declared["part"]
    assert "structure in force when it was written" in declared["part"]
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
