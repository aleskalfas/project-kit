"""Tests for rule-set files (COR-051, Task #989): the location rule, the schema,
the join between data and prose, ids, origins, successors, inheritance, rules as
friction artefacts, citations and the rule id space.

Built on the shared adopter-repository fixture: a real install, so both the
rule-set and container schemas are read from the adopter's own tree. Project
rule sets live in `docs/rule-sets/` (the internal documentation root's default).
"""

from __future__ import annotations

import io
import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner
from jsonschema import Draft202012Validator
from ruamel.yaml import YAML

from project_kit import backbone_schemas as bs
from project_kit import connections as cx
from project_kit import decisions_validate, refs
from project_kit import friction_discovery as fd
from project_kit import friction_validate as fv
from project_kit import rule_sets as rs
from project_kit.cli import main
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo

REPO = Path(__file__).resolve().parents[1]
CONFIG = ".pkit/project/config.yaml"
PROJECT_SETS = "docs/rule-sets"

Kind = rs.RuleSetFindingKind

QUOTE = {"date": "2026-09-27", "by": "A. Person", "why": "Findings must name the rule they broke."}


def rule_set_text(front: Mapping[str, Any], sections: Iterable[str] | None = None) -> str:
    """A rule-set file: `front` as its front matter, one body section per rule id
    (or per id in `sections`)."""
    yaml = YAML()
    yaml.default_flow_style = False
    buffer = io.StringIO()
    yaml.dump(dict(front), buffer)
    ids = list(sections) if sections is not None else list(front.get("rules", {}))
    body = "\n".join(
        f"## {rule_id} — Rule {rule_id}\n\nThe statement of {rule_id}.\n" for rule_id in ids
    )
    return f"---\n{buffer.getvalue()}---\n\n# Rules\n\n{body}"


def cmn(**overrides: Any) -> dict[str, Any]:
    """A valid project rule set, CMN, exercising every status and both origin forms."""
    front: dict[str, Any] = {
        "rule-set": "CMN",
        "version": "1.2.0",
        "scope": ["docs/**"],
        "rules": {
            "RS-CMN-001": {
                "status": "accepted",
                "origin": dict(QUOTE),
                "offers": ["cause-location"],
                "pkit": {"friction": {"anchors": {"record": ["COR-051"]}}},
            },
            "RS-CMN-002": {},
            "RS-CMN-003": {"status": "accepted", "origin": {"decision": "COR-051"}},
            "RS-CMN-004": {
                "status": "superseded",
                "successor": "RS-CMN-005",
                "origin": dict(QUOTE),
            },
            "RS-CMN-005": {"status": "accepted", "origin": dict(QUOTE)},
            "RS-CMN-006": {"status": "withdrawn", "origin": dict(QUOTE)},
        },
    }
    front.update(overrides)
    return front


def rules(*ids: str, **entry: Any) -> dict[str, Any]:
    """Accepted rules with a complete origin, each with `entry` merged in."""
    return {rule_id: {"status": "accepted", "origin": dict(QUOTE), **entry} for rule_id in ids}


def anchored_to(*artefacts: str) -> dict[str, Any]:
    """A rule entry's container anchoring it to `artefacts` by id."""
    return {"pkit": {"friction": {"anchors": {"artefact": list(artefacts)}}}}


@pytest.fixture
def adopter(make_adopter_repo: MakeAdopterRepo) -> AdopterRepo:
    return make_adopter_repo()


def write_set(adopter: AdopterRepo, rel: str, front: Mapping[str, Any], **kwargs: Any) -> None:
    adopter.write({rel: rule_set_text(front, **kwargs)})


def validate(adopter: AdopterRepo) -> rs.RuleSetValidation:
    return rs.validate_rule_sets(adopter.root)


def kinds(result: rs.RuleSetValidation) -> list[Kind]:
    return [f.kind for f in result.errors]


def only(result: rs.RuleSetValidation, kind: Kind) -> rs.RuleSetFinding:
    (finding,) = [f for f in result.findings if f.kind is kind]
    return finding


# --- a valid rule set, the default status ----------------------------------------


def test_a_valid_rule_set_is_clean_and_parsed(adopter: AdopterRepo) -> None:
    write_set(adopter, f"{PROJECT_SETS}/cmn.md", cmn())
    result = validate(adopter)

    assert result.findings == (), [f"{f.where}: {f.message}" for f in result.findings]
    (rule_set,) = result.discovery.rule_sets
    assert (rule_set.path, rule_set.name, rule_set.major) == (f"{PROJECT_SETS}/cmn.md", "CMN", 1)
    assert rule_set.component is None and rule_set.citation == "CMN"
    first = rule_set.rule("RS-CMN-001")
    assert first is not None and first.section.startswith("## RS-CMN-001 — Rule RS-CMN-001")
    assert first.offers == ("cause-location",)
    assert rs.summary_lines(result) == [
        "1 rule set(s), 6 rule(s) (1 proposed, 3 accepted, 1 superseded, 1 withdrawn); "
        "0 error(s), 0 report(s)."
    ]


def test_a_rule_without_status_is_proposed_and_binds_nothing(adopter: AdopterRepo) -> None:
    write_set(adopter, f"{PROJECT_SETS}/cmn.md", cmn())
    rule = validate(adopter).discovery.rule_sets[0].rule("RS-CMN-002")
    assert rule is not None
    assert (rule.status, rule.binds) == ("proposed", False)
    # A proposed rule needs no origin; only an accepted one does.
    assert rule.origin is None


def test_nothing_to_check_without_rule_sets(adopter: AdopterRepo) -> None:
    result = validate(adopter)
    assert result.is_dormant and result.findings == ()
    assert rs.summary_lines(result) == ["no rule sets found."]


# --- the location rule -------------------------------------------------------------


def test_the_location_rule_binds_by_folder_never_by_a_field(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    adopter = make_adopter_repo(capabilities=("evidence",))
    adopter.write(
        {
            CONFIG: "name: adopter\nfriction:\n  places: [analysis/rule-sets]\n",
            f"{PROJECT_SETS}/README.md": "# Our rule sets\n\nA signpost, not a rule set.\n",
            "docs/elsewhere.md": rule_set_text(
                {"rule-set": "OUT", "version": "1.0.0", "rules": {}}
            ),
        }
    )
    write_set(adopter, f"{PROJECT_SETS}/cmn.md", cmn())
    write_set(
        adopter, "analysis/rule-sets/ana.md", {"rule-set": "ANA", "version": "1.0.0", "rules": {}}
    )
    write_set(
        adopter, ".pkit/rule-sets/base.md", {"rule-set": "BASE", "version": "1.0.0", "rules": {}}
    )
    write_set(
        adopter,
        ".pkit/capabilities/evidence/rule-sets/ev.md",
        {"rule-set": "EV", "version": "1.0.0", "rules": {}},
    )
    discovery = rs.discover_rule_sets(adopter.root)

    owners = {s.path: (s.component, s.citation) for s in discovery.rule_sets}
    assert owners == {
        ".pkit/capabilities/evidence/rule-sets/ev.md": ("evidence", "evidence:EV"),
        ".pkit/rule-sets/base.md": ("backbone", "backbone:BASE"),
        "analysis/rule-sets/ana.md": (None, "ANA"),
        f"{PROJECT_SETS}/cmn.md": (None, "CMN"),
    }
    assert [s.path for s in discovery.rule_sets] == sorted(owners)
    assert discovery.unreadable == ()  # the README is a signpost, never claimed


def test_the_project_folder_follows_the_internal_documentation_root(adopter: AdopterRepo) -> None:
    adopter.write({CONFIG: "name: adopter\ndocs:\n  internal: tech-docs\n"})
    write_set(adopter, "tech-docs/rule-sets/cmn.md", cmn())
    write_set(adopter, f"{PROJECT_SETS}/ignored.md", cmn(**{"rule-set": "IGN"}))
    assert [s.path for s in rs.discover_rule_sets(adopter.root).rule_sets] == [
        "tech-docs/rule-sets/cmn.md"
    ]


def test_a_file_in_a_rule_set_folder_without_front_matter_is_reported(
    adopter: AdopterRepo,
) -> None:
    adopter.write(
        {
            f"{PROJECT_SETS}/prose.md": "# Just prose\n",
            f"{PROJECT_SETS}/broken.md": "---\nrules: [unclosed\n---\n",
            f"{PROJECT_SETS}/list.md": "---\n- a\n- b\n---\n",
        }
    )
    result = validate(adopter)
    assert [(f.location, f.kind) for f in result.errors] == [
        (f"{PROJECT_SETS}/broken.md", Kind.UNREADABLE),
        (f"{PROJECT_SETS}/list.md", Kind.UNREADABLE),
        (f"{PROJECT_SETS}/prose.md", Kind.UNREADABLE),
    ]
    messages = [f.message for f in result.errors]
    assert "does not parse" in messages[0] and "at line 3" in messages[0]  # lines of the file
    assert "not a mapping" in messages[1]
    assert "has no front matter" in messages[2]


# --- the schema: strict, unknown keys with a suggestion ----------------------------


def test_unknown_keys_are_refused_with_the_nearest_known_key(adopter: AdopterRepo) -> None:
    front = cmn(rulez=1)
    front["rules"]["RS-CMN-002"] = {"statsu": "accepted"}
    front["rules"]["RS-CMN-003"]["origin"] = {"decision": "COR-051", "sorce": "x"}
    write_set(adopter, f"{PROJECT_SETS}/cmn.md", front)
    result = validate(adopter)

    unknown = [(f.where, f.message) for f in result.errors if f.kind is Kind.UNKNOWN_KEY]
    assert unknown == [
        (f"{PROJECT_SETS}/cmn.md /rulez", "unknown key 'rulez'; did you mean 'rules'?"),
        (
            f"{PROJECT_SETS}/cmn.md#RS-CMN-002 /statsu",
            "unknown key 'statsu'; did you mean 'status'?",
        ),
        (
            f"{PROJECT_SETS}/cmn.md#RS-CMN-003 /origin/sorce",
            "unknown key 'sorce'; did you mean 'source'?",
        ),
    ]


def test_the_schema_types_every_field(adopter: AdopterRepo) -> None:
    front = cmn(version="1.0", inherits=["cmn"], scope=[])
    front["rules"]["RS-CMN-002"] = {"status": "draft", "offers": ["Bad_Point"]}
    del front["rules"]["RS-CMN-004"]["successor"]  # superseded without a successor
    front["rules"]["RS-CMN-005"]["successor"] = "RS-CMN-001"  # a successor on an accepted rule
    write_set(adopter, f"{PROJECT_SETS}/cmn.md", front)
    result = validate(adopter)

    shape = {f.where: f.message for f in result.errors if f.kind is Kind.SHAPE}
    path = f"{PROJECT_SETS}/cmn.md"
    assert set(shape) == {
        f"{path} /version",
        f"{path} /inherits/0",
        f"{path} /scope",
        f"{path}#RS-CMN-002 /status",
        f"{path}#RS-CMN-002 /offers/0",
        f"{path}#RS-CMN-004",
        f"{path}#RS-CMN-005 /successor",
    }
    assert shape[f"{path}#RS-CMN-004"].startswith("a superseded rule names its successor")
    assert shape[f"{path}#RS-CMN-005 /successor"].startswith("only a superseded rule names")


def test_the_rule_set_name_version_and_rules_are_required(adopter: AdopterRepo) -> None:
    adopter.write({f"{PROJECT_SETS}/empty.md": "---\nscope: [docs/**]\n---\n"})
    messages = sorted(f.message for f in validate(adopter).errors)
    assert messages == [
        "'rule-set' is a required property",
        "'rules' is a required property",
        "'version' is a required property",
    ]


# --- the join between data and prose ------------------------------------------------


def test_the_join_is_checked_both_ways(adopter: AdopterRepo) -> None:
    front = cmn()
    sections = [*front["rules"], "RS-CMN-009", "RS-CMN-001"]
    sections.remove("RS-CMN-003")
    write_set(adopter, f"{PROJECT_SETS}/cmn.md", front, sections=sections)
    result = validate(adopter)
    path = f"{PROJECT_SETS}/cmn.md"

    assert [(f.location, f.kind) for f in result.errors] == [
        (f"{path}#RS-CMN-003", Kind.MISSING_SECTION),
        (f"{path}#RS-CMN-001", Kind.DUPLICATE_SECTION),
        (f"{path}#RS-CMN-009", Kind.MISSING_DATA),
    ]


def test_headings_in_fenced_code_are_not_sections(adopter: AdopterRepo) -> None:
    text = rule_set_text(cmn()) + "\n```markdown\n## RS-CMN-042 — an example, not a rule\n```\n"
    adopter.write({f"{PROJECT_SETS}/cmn.md": text})
    assert validate(adopter).findings == ()


# --- ids ----------------------------------------------------------------------------


def test_malformed_duplicate_and_foreign_set_ids(adopter: AdopterRepo) -> None:
    front = cmn()
    front["rules"]["RS-cmn-7"] = {}
    front["rules"]["RS-DOC-001"] = {}
    text = rule_set_text(front, sections=[*cmn()["rules"], "RS-DOC-001", "RS-cmn-7 is not an id"])
    # A copy-pasted rule under an id already in use: written twice in `rules`.
    text = text.replace(
        "  RS-CMN-002: {}\n", "  RS-CMN-002: {}\n  RS-CMN-002:\n    status: accepted\n"
    )
    adopter.write({f"{PROJECT_SETS}/cmn.md": text})
    result = validate(adopter)
    path = f"{PROJECT_SETS}/cmn.md"

    by_kind = {(f.kind, f.location) for f in result.errors}
    assert (Kind.DUPLICATE_ID, f"{path}#RS-CMN-002") in by_kind
    assert (Kind.MALFORMED_ID, f"{path}#RS-cmn-7") in by_kind  # the data key
    assert (Kind.MALFORMED_ID, path) in by_kind  # the heading
    assert (Kind.FOREIGN_SET_ID, f"{path}#RS-DOC-001") in by_kind
    duplicate = only(result, Kind.DUPLICATE_ID)
    assert "written 2 times" in duplicate.message and "never reused" in duplicate.message
    # The first value is the one read: RS-CMN-002 stays proposed.
    rule = result.discovery.rule_sets[0].rule("RS-CMN-002")
    assert rule is not None and rule.status == "proposed"


def test_rule_set_names_are_unique_among_rule_sets(adopter: AdopterRepo) -> None:
    write_set(adopter, f"{PROJECT_SETS}/a.md", cmn())
    write_set(adopter, f"{PROJECT_SETS}/b.md", cmn())
    finding = only(validate(adopter), Kind.DUPLICATE_SET_NAME)
    assert (finding.location, finding.pointer) == (f"{PROJECT_SETS}/b.md", "/rule-set")
    assert f"{PROJECT_SETS}/a.md" in finding.message


# --- origins ------------------------------------------------------------------------


def test_an_accepted_rule_carries_a_complete_origin(adopter: AdopterRepo) -> None:
    front = cmn()
    del front["rules"]["RS-CMN-001"]["origin"]
    front["rules"]["RS-CMN-005"]["origin"] = {"date": "2026-09-27", "by": "A. Person"}
    front["rules"]["RS-CMN-006"]["origin"] = {**QUOTE, "decision": "COR-051"}
    front["rules"]["RS-CMN-002"] = {"origin": {"by": "someone"}}  # proposed: partial is fine
    write_set(adopter, f"{PROJECT_SETS}/cmn.md", front)
    result = validate(adopter)
    path = f"{PROJECT_SETS}/cmn.md"

    assert [(f.location, f.kind) for f in result.errors] == [
        (f"{path}#RS-CMN-001", Kind.MISSING_ORIGIN),
        (f"{path}#RS-CMN-005", Kind.INCOMPLETE_ORIGIN),
        (f"{path}#RS-CMN-006", Kind.INCOMPLETE_ORIGIN),
    ]
    assert "lacks `why`" in result.errors[1].message
    assert "not both" in result.errors[2].message


def test_an_origin_citing_a_missing_or_unaccepted_decision(adopter: AdopterRepo) -> None:
    adopter.write(
        {
            ".pkit/decisions/project/PRJ-001-draft.md": (
                "---\nid: PRJ-001\ntitle: A draft\nstatus: proposed\ndate: 2026-09-01\n"
                "author: A. Person\n---\n\n## Context\n"
            )
        }
    )
    front = cmn()
    front["rules"]["RS-CMN-001"]["origin"] = {"decision": "PRJ-999"}
    front["rules"]["RS-CMN-003"]["origin"] = {"decision": "PRJ-001"}
    front["rules"]["RS-CMN-002"] = {"origin": {"decision": "PRJ-001"}}  # proposed: fine
    write_set(adopter, f"{PROJECT_SETS}/cmn.md", front)
    result = validate(adopter)
    path = f"{PROJECT_SETS}/cmn.md"

    assert [(f.where, f.kind) for f in result.errors] == [
        (f"{path}#RS-CMN-001 /origin/decision", Kind.MISSING_DECISION),
        (f"{path}#RS-CMN-003 /origin/decision", Kind.DECISION_NOT_ACCEPTED),
    ]
    assert "status is proposed" in result.errors[1].message


def test_a_capability_decision_resolves_through_its_capability(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    adopter = make_adopter_repo(capabilities=("evidence",))
    front = cmn()
    front["rules"]["RS-CMN-003"]["origin"] = {"decision": "evidence:DEC-001"}
    front["rules"]["RS-CMN-005"]["origin"] = {"decision": "evidence:DEC-099"}
    write_set(adopter, f"{PROJECT_SETS}/cmn.md", front)
    finding = only(validate(adopter), Kind.MISSING_DECISION)
    assert finding.location == f"{PROJECT_SETS}/cmn.md#RS-CMN-005"


def test_a_source_is_reported_as_an_unresolved_kind_never_passed(adopter: AdopterRepo) -> None:
    front = cmn()
    front["rules"]["RS-CMN-001"]["origin"]["source"] = {"kind": "transcript", "value": "t-12"}
    write_set(adopter, f"{PROJECT_SETS}/cmn.md", front)
    result = validate(adopter)

    assert result.errors == ()
    report = only(result, Kind.UNRESOLVED_SOURCE_KIND)
    assert report.severity is rs.Severity.REPORT
    assert report.where == f"{PROJECT_SETS}/cmn.md#RS-CMN-001 /origin/source"
    assert "'transcript' is unresolved" in report.message
    # The registry's own verdict, word for word the one an anchor of the kind gets.
    reason = fd.unresolved_kind_reason("transcript", {})
    assert reason is not None and reason in report.message
    assert rs.fd.registered_anchor_kinds(adopter.root) == {}


def test_a_source_of_a_core_anchor_kind_is_no_source_kind(adopter: AdopterRepo) -> None:
    front = cmn()
    front["rules"]["RS-CMN-001"]["origin"]["source"] = {"kind": "path", "value": "t-12"}
    write_set(adopter, f"{PROJECT_SETS}/cmn.md", front)
    result = validate(adopter)

    assert result.errors == ()
    report = only(result, Kind.UNRESOLVED_SOURCE_KIND)
    assert report.severity is rs.Severity.REPORT
    assert report.where == f"{PROJECT_SETS}/cmn.md#RS-CMN-001 /origin/source"
    assert "'path' is unresolved" in report.message
    assert "resolves it as an anchor, never as a source" in report.message
    assert rs.fd.registered_anchor_kinds(adopter.root) == {}


def test_a_source_is_judged_through_the_resolver_its_kind_registers(
    adopter: AdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The pass reads the one anchor-kind registry the friction checks read, takes its
    verdict on the kind, and resolves the source through the resolver the kind
    registers (COR-051 point 5; ADR-057 point 2). The synthetic resolver is
    registered at the registry itself — the function every engine calls — and its
    run stood in for (`run_resolver`); `test_friction_anchor_kinds` runs real ones."""
    front = cmn()
    front["rules"]["RS-CMN-001"]["origin"]["source"] = {"kind": "transcript", "value": "t-12"}
    front["rules"]["RS-CMN-005"]["origin"]["source"] = {"kind": "transcript", "value": "t-13"}
    write_set(adopter, f"{PROJECT_SETS}/cmn.md", front)
    declared = fd.ResolverCommand(
        "transcript", "sources", "resolve transcript", query_contract=True
    )
    reads: list[Path] = []

    def register(resolver: fd.ResolverCommand) -> None:
        def registry(root: Path) -> dict[str, fd.ResolverCommand]:
            reads.append(root)
            return {resolver.kind: resolver}

        monkeypatch.setattr(fd, "registered_anchor_kinds", registry)

    # Registered with the query contract but naming no command: its resolver gives no
    # answer, so the source is reported — never as a kind nothing registers.
    register(declared)
    result = validate(adopter)
    assert [f.kind for f in result.findings] == [Kind.UNRESOLVED_SOURCE_KIND] * 2
    assert reads == [adopter.root]  # the registry is read once per pass
    message = result.findings[0].message
    assert "source transcript:t-12 is unresolved: its resolver gave no answer" in message
    assert "command 'resolve transcript' is not declared in the `commands:` of sources" in message
    reason = fd.unresolved_kind_reason("transcript", {})
    assert reason is not None and reason not in message

    # Registered without it: refused, as the friction checks refuse it.
    register(fd.ResolverCommand("transcript", "sources", "resolve transcript"))
    refused = validate(adopter).findings[0].message
    assert "does not declare the query contract" in refused

    # The kind resolves: each source is what its resolver answers for its value.
    register(declared)
    asked: list[str] = []
    answers = {"t-12": ("transcripts/t-12.md",), "t-13": ()}

    def resolving(
        root: Path, resolver: fd.ResolverCommand, value: str, files: object
    ) -> fd.AnchorResolution:
        assert resolver == declared
        asked.append(value)
        return fd.AnchorResolution(paths=answers[value])

    monkeypatch.setattr(fd, "run_resolver", resolving)
    result = validate(adopter)
    assert sorted(asked) == ["t-12", "t-13"]
    # A source naming a file resolves; one its resolver names no file for fails validation.
    assert [f.kind for f in result.findings] == [Kind.MISSING_SOURCE]
    missing = only(result, Kind.MISSING_SOURCE)
    assert missing.severity is rs.Severity.ERROR
    assert missing.where == f"{PROJECT_SETS}/cmn.md#RS-CMN-005 /origin/source"
    assert missing.message == (
        "cites source transcript:t-13, which does not resolve: the resolver `resolve "
        "transcript` that sources registers for `transcript` names no file for it (COR-051 "
        "point 5)."
    )


# --- successors ---------------------------------------------------------------------


def test_a_successor_exists_in_the_set_or_one_inheriting_it(adopter: AdopterRepo) -> None:
    front = cmn()
    front["rules"]["RS-CMN-004"]["successor"] = "RS-CMN-099"
    front["rules"]["RS-CMN-007"] = {"status": "superseded", "successor": "RS-DOC-001"}
    front["rules"]["RS-CMN-008"] = {"status": "superseded", "successor": "RS-OTH-001"}
    front["rules"]["RS-CMN-009"] = {"status": "superseded", "successor": "RS-CMN-009"}
    write_set(adopter, f"{PROJECT_SETS}/cmn.md", front)
    doc = {
        "rule-set": "DOC",
        "version": "1.0.0",
        "inherits": ["CMN@1"],
        "rules": rules("RS-DOC-001"),
    }
    write_set(adopter, f"{PROJECT_SETS}/doc.md", doc)
    write_set(
        adopter,
        f"{PROJECT_SETS}/oth.md",
        {"rule-set": "OTH", "version": "1.0.0", "rules": rules("RS-OTH-001")},
    )
    result = validate(adopter)
    path = f"{PROJECT_SETS}/cmn.md"

    assert [(f.location, f.kind) for f in result.errors] == [
        (f"{path}#RS-CMN-004", Kind.SUCCESSOR_NOT_FOUND),
        (f"{path}#RS-CMN-008", Kind.SUCCESSOR_OUT_OF_LINE),
        (f"{path}#RS-CMN-009", Kind.SUCCESSOR_NOT_FOUND),
    ]
    assert "has no rule RS-CMN-099" in result.errors[0].message
    assert "does not inherit CMN" in result.errors[1].message
    assert "names itself" in result.errors[2].message


# --- inheritance --------------------------------------------------------------------


def doc(
    *pins: str, version: str = "1.0.0", rules: Mapping[str, dict[str, Any]] | None = None
) -> dict[str, Any]:
    entries = {"RS-DOC-001": {"status": "accepted", "origin": dict(QUOTE)}, **(rules or {})}
    return {"rule-set": "DOC", "version": version, "inherits": list(pins), "rules": entries}


def test_an_inherited_set_that_does_not_exist(adopter: AdopterRepo) -> None:
    write_set(adopter, f"{PROJECT_SETS}/doc.md", doc("LDOC@1"))
    finding = only(validate(adopter), Kind.INHERITED_SET_MISSING)
    assert finding.where == f"{PROJECT_SETS}/doc.md /inherits/0"
    assert "no rule set is named LDOC" in finding.message


def test_a_wrong_major_is_a_version_relation_naming_the_new_major(adopter: AdopterRepo) -> None:
    write_set(adopter, f"{PROJECT_SETS}/cmn.md", cmn(version="2.1.0"))
    write_set(adopter, f"{PROJECT_SETS}/doc.md", doc("CMN@1"))
    app = {"rule-set": "APP", "version": "1.0.0", "inherits": ["CMN@2"], "rules": {}}
    write_set(adopter, f"{PROJECT_SETS}/app.md", app)

    checks = rs.pin_checks(rs.discover_rule_sets(adopter.root))
    assert [(c.rule_set.name, str(c.pin), c.problem is None) for c in checks] == [
        ("APP", "CMN@2", True),
        ("DOC", "CMN@1", False),
    ]
    wiring = cx.resolve_wiring(adopter.root)
    assert wiring.checked[cx.Relation.RULE_SET_PIN] == 2
    (finding,) = [f for f in wiring.findings if f.relation is cx.Relation.RULE_SET_PIN]
    assert (finding.file.as_posix(), finding.path) == (f"{PROJECT_SETS}/doc.md", "/inherits/0")
    assert finding.severity is cx.Severity.ERROR
    assert "at version 2.1.0, major 2" in finding.message
    assert "update the pin to CMN@2" in finding.message
    assert validate(adopter).errors == ()  # reported once, under `versions`

    result = CliRunner().invoke(main, ["validate", "--no-refs"])
    assert result.exit_code == 1, result.output
    versions = result.output.split("\n  versions\n")[1].split("\n  rule-sets\n")[0]
    assert "2 rule-set pin(s)" in versions and "[rule-set pin]" in versions
    assert f"{PROJECT_SETS}/doc.md:/inherits/0" in versions


def test_an_inherited_id_is_never_redefined(adopter: AdopterRepo) -> None:
    write_set(adopter, f"{PROJECT_SETS}/cmn.md", cmn())
    write_set(adopter, f"{PROJECT_SETS}/doc.md", doc("CMN@1", rules={"RS-CMN-001": {}}))
    result = validate(adopter)
    finding = only(result, Kind.REDEFINED_ID)
    assert finding.location == f"{PROJECT_SETS}/doc.md#RS-CMN-001"
    assert "inherited set CMN" in finding.message
    assert Kind.FOREIGN_SET_ID not in kinds(result)


def test_a_fill_names_a_point_an_inherited_rule_offers(adopter: AdopterRepo) -> None:
    write_set(adopter, f"{PROJECT_SETS}/cmn.md", cmn())
    write_set(
        adopter,
        f"{PROJECT_SETS}/oth.md",
        {"rule-set": "OTH", "version": "1.0.0", "rules": {"RS-OTH-001": {"offers": ["p"]}}},
    )
    fills = {
        "fills": ["RS-CMN-001#cause-location", "RS-CMN-001#nowhere", "RS-OTH-001#p", "RS-CMN-777#x"]
    }
    write_set(adopter, f"{PROJECT_SETS}/doc.md", doc("CMN@1", rules={"RS-DOC-002": fills}))
    result = validate(adopter)

    undeclared = [(f.pointer, f.message) for f in result.errors if f.kind is Kind.UNDECLARED_FILL]
    assert [pointer for pointer, _ in undeclared] == ["/fills/1", "/fills/2", "/fills/3"]
    assert "offers no extension point #nowhere (it offers: #cause-location)" in undeclared[0][1]
    assert "OTH is not a set DOC inherits" in undeclared[1][1]
    assert "has no rule RS-CMN-777" in undeclared[2][1]


def test_each_point_is_filled_at_most_once_along_a_chain(adopter: AdopterRepo) -> None:
    write_set(adopter, f"{PROJECT_SETS}/cmn.md", cmn())
    fill = {"fills": ["RS-CMN-001#cause-location"]}
    # A chain: DOC fills the point, then APP, inheriting DOC, fills it again.
    write_set(adopter, f"{PROJECT_SETS}/doc.md", doc("CMN@1", rules={"RS-DOC-002": fill}))
    app = {
        "rule-set": "APP",
        "version": "1.0.0",
        "inherits": ["DOC@1"],
        "rules": {"RS-APP-001": fill},
    }
    write_set(adopter, f"{PROJECT_SETS}/app.md", app)
    # A diamond: B1 and B2 each fill it once; D inherits both.
    for name in ("B1", "B2"):
        branch = {
            "rule-set": name,
            "version": "1.0.0",
            "inherits": ["CMN@1"],
            "rules": {f"RS-{name}-001": fill},
        }
        write_set(adopter, f"{PROJECT_SETS}/{name.lower()}.md", branch)
    write_set(
        adopter,
        f"{PROJECT_SETS}/d.md",
        {"rule-set": "D", "version": "1.0.0", "inherits": ["B1@1", "B2@1"], "rules": {}},
    )
    result = validate(adopter)

    doubles = [(f.where, f.message) for f in result.errors if f.kind is Kind.DOUBLE_FILL]
    assert [where for where, _ in doubles] == [
        f"{PROJECT_SETS}/app.md#RS-APP-001 /fills/0",
        f"{PROJECT_SETS}/d.md /inherits",
    ]
    assert "filled 2 times" in doubles[0][1] and "RS-DOC-002 (DOC)" in doubles[0][1]
    assert "RS-B1-001 (B1), RS-B2-001 (B2)" in doubles[1][1]


def test_a_fill_of_a_retired_rule_is_orphaned_and_a_retired_fill_counts_for_nothing(
    adopter: AdopterRepo,
) -> None:
    front = cmn()
    front["rules"]["RS-CMN-006"]["offers"] = ["reader"]
    write_set(adopter, f"{PROJECT_SETS}/cmn.md", front)
    old = {"status": "withdrawn", "origin": dict(QUOTE), "fills": ["RS-CMN-001#cause-location"]}
    new = {
        "status": "accepted",
        "origin": dict(QUOTE),
        "fills": ["RS-CMN-001#cause-location"],
        **anchored_to("RS-CMN-001"),
    }
    orphan = {"fills": ["RS-CMN-006#reader"]}  # orphaned: no anchor is asked of it
    write_set(
        adopter,
        f"{PROJECT_SETS}/doc.md",
        doc("CMN@1", rules={"RS-DOC-002": old, "RS-DOC-003": new, "RS-DOC-004": orphan}),
    )
    result = validate(adopter)

    assert result.errors == ()  # the withdrawn RS-DOC-002's fill does not make a double fill
    report = only(result, Kind.ORPHANED_FILL)
    assert report.severity is rs.Severity.REPORT
    assert report.where == f"{PROJECT_SETS}/doc.md#RS-DOC-004 /fills/0"
    assert "RS-CMN-006 is withdrawn" in report.message


def test_a_fill_whose_rule_does_not_anchor_to_the_rule_it_fills(adopter: AdopterRepo) -> None:
    front = cmn()
    front["rules"]["RS-CMN-005"]["offers"] = ["reader", "writer"]
    write_set(adopter, f"{PROJECT_SETS}/cmn.md", front)
    fill = {"fills": ["RS-CMN-001#cause-location"]}
    entries = {
        "RS-DOC-002": {**fill, **anchored_to("RS-CMN-001")},  # anchored: clean
        "RS-DOC-003": {"fills": ["RS-CMN-005#reader"]},  # no anchor at all
        # Anchored elsewhere: to another rule, through a point, and to a path.
        "RS-DOC-004": {
            "fills": ["RS-CMN-005#writer"],
            "pkit": {
                "friction": {
                    "anchors": {
                        "artefact": ["RS-CMN-001", "RS-CMN-005#writer"],
                        "path": ["docs/**"],
                    }
                }
            },
        },
    }
    write_set(adopter, f"{PROJECT_SETS}/doc.md", doc("CMN@1", rules=entries))
    result = validate(adopter)

    unanchored = [f for f in result.errors if f.kind is Kind.UNANCHORED_FILL]
    assert [f.where for f in unanchored] == [
        f"{PROJECT_SETS}/doc.md#RS-DOC-003 /fills/0",
        f"{PROJECT_SETS}/doc.md#RS-DOC-004 /fills/0",
    ]
    assert kinds(result) == [Kind.UNANCHORED_FILL, Kind.UNANCHORED_FILL]
    assert (
        "fills RS-CMN-005#reader, but RS-DOC-003 does not anchor to RS-CMN-005"
        in unanchored[0].message
    )
    assert "add RS-CMN-005 to `pkit.friction.anchors.artefact`" in unanchored[0].message


def test_a_fill_of_a_method_rule_anchors_to_it_bare_or_as_cited(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    adopter = make_adopter_repo(capabilities=("evidence",))
    write_set(
        adopter,
        ".pkit/capabilities/evidence/rule-sets/ev.md",
        {"rule-set": "EV", "version": "1.0.0", "rules": {"RS-EV-001": {"offers": ["a", "b", "c"]}}},
    )
    entries = {
        "RS-DOC-002": {"fills": ["evidence:RS-EV-001#a"], **anchored_to("evidence:RS-EV-001")},
        "RS-DOC-003": {"fills": ["RS-EV-001#b"], **anchored_to("RS-EV-001")},
        # A component that does not own the set names no rule, so it anchors nothing.
        "RS-DOC-004": {"fills": ["evidence:RS-EV-001#c"], **anchored_to("living-docs:RS-EV-001")},
    }
    write_set(adopter, f"{PROJECT_SETS}/doc.md", doc("evidence:EV@1", rules=entries))
    result = validate(adopter)

    (finding,) = result.errors
    assert (finding.kind, finding.where) == (
        Kind.UNANCHORED_FILL,
        f"{PROJECT_SETS}/doc.md#RS-DOC-004 /fills/0",
    )
    assert "add evidence:RS-EV-001 to" in finding.message

    # The anchor the pass accepts is one the friction pass resolves to the same rule.
    discovery = fd.discover_artefacts(adopter.root)
    filling = next(a for a in discovery.artefacts if a.id == "RS-DOC-002")
    (anchor,) = filling.anchors_of_kind("artefact")
    found = discovery.find(anchor)
    assert found is not None and found.location.endswith("ev.md#RS-EV-001")


def test_a_bare_pin_of_a_method_set_names_the_qualified_form(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    adopter = make_adopter_repo(capabilities=("evidence",))
    write_set(
        adopter,
        ".pkit/capabilities/evidence/rule-sets/ev.md",
        {"rule-set": "EV", "version": "3.0.0", "rules": {}},
    )
    write_set(adopter, f"{PROJECT_SETS}/doc.md", doc("EV@3"))
    finding = only(validate(adopter), Kind.INHERITED_SET_MISSING)
    assert "belongs to capability evidence" in finding.message
    assert "write the pin as evidence:EV@3" in finding.message

    write_set(adopter, f"{PROJECT_SETS}/doc.md", doc("evidence:EV@3"))
    assert validate(adopter).errors == ()


def test_a_capability_inherits_another_only_with_the_dependency(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    adopter = make_adopter_repo(capabilities=("evidence", "demo-recording"))
    empty = {"version": "1.0.0", "rules": {}}
    write_set(adopter, ".pkit/rule-sets/base.md", {"rule-set": "BASE", **empty})
    write_set(
        adopter,
        ".pkit/capabilities/demo-recording/rule-sets/demo.md",
        {"rule-set": "DEMO", **empty},
    )
    write_set(adopter, f"{PROJECT_SETS}/prj.md", {"rule-set": "PRJ", **empty})
    inheriting = {
        "rule-set": "EV",
        **empty,
        "inherits": ["backbone:BASE@1", "demo-recording:DEMO@1", "PRJ@1"],
    }
    write_set(adopter, ".pkit/capabilities/evidence/rule-sets/ev.md", inheriting)
    result = validate(adopter)

    refused = [
        (f.pointer, f.message) for f in result.errors if f.kind is Kind.INHERITANCE_NOT_ALLOWED
    ]
    assert [pointer for pointer, _ in refused] == ["/inherits/1", "/inherits/2"]
    assert "does not declare a dependency on capability demo-recording" in refused[0][1]
    assert "cannot inherit the project rule set PRJ" in refused[1][1]

    package = adopter.pkit / "capabilities" / "evidence" / "package.yaml"
    package.write_text(
        package.read_text(encoding="utf-8")
        + 'requires_capabilities:\n  - name: demo-recording\n    version: ">=0.1.0"\n',
        encoding="utf-8",
    )
    remaining = [
        f.pointer for f in validate(adopter).errors if f.kind is Kind.INHERITANCE_NOT_ALLOWED
    ]
    assert remaining == ["/inherits/2"]


def test_an_inheritance_cycle_is_reported_once(adopter: AdopterRepo) -> None:
    empty = {"version": "1.0.0", "rules": {}}
    write_set(adopter, f"{PROJECT_SETS}/a.md", {"rule-set": "A", **empty, "inherits": ["B@1"]})
    write_set(adopter, f"{PROJECT_SETS}/b.md", {"rule-set": "B", **empty, "inherits": ["A@1"]})
    write_set(
        adopter, f"{PROJECT_SETS}/c.md", {"rule-set": "C", **empty, "inherits": ["C@1", "A@1"]}
    )
    cycles = [f for f in validate(adopter).errors if f.kind is Kind.INHERITANCE_CYCLE]
    assert [(f.location, f.message.split(";")[0]) for f in cycles] == [
        (f"{PROJECT_SETS}/a.md", "rule set A is part of an inheritance cycle: A -> B -> A"),
        (f"{PROJECT_SETS}/c.md", "rule set C inherits itself: C -> C"),
    ]


# --- rules are friction artefacts ---------------------------------------------------


def test_rule_entries_are_discovered_by_the_friction_pass_as_artefacts(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    adopter = make_adopter_repo(capabilities=("evidence",))
    write_set(adopter, f"{PROJECT_SETS}/cmn.md", cmn())
    write_set(
        adopter,
        ".pkit/capabilities/evidence/rule-sets/ev.md",
        {"rule-set": "EV", "version": "1.0.0", "rules": {"RS-EV-001": {}}},
    )
    discovery = fd.discover_artefacts(adopter.root)

    by_id = {a.id: a for a in discovery.artefacts}
    assert list(by_id) == ["RS-EV-001", *cmn()["rules"]]  # the set's own keys are not entries
    first = by_id["RS-CMN-001"]
    assert (first.kind, first.location) == (
        fd.ArtefactKind.ENTRY,
        f"{PROJECT_SETS}/cmn.md#RS-CMN-001",
    )
    assert first.carrier["status"] == "accepted"  # the rule's data is its content
    assert first.body.startswith("## RS-CMN-001 — Rule RS-CMN-001")
    assert first.anchors == {"record": ("COR-051",)}
    assert first.rule_set is not None and first.rule_set.component is None
    # A method rule is also reachable the way it is cited.
    assert by_id["RS-EV-001"].identifiers == frozenset({"RS-EV-001", "evidence:RS-EV-001"})
    assert {p.pattern for p in discovery.places} == {
        PROJECT_SETS,
        ".pkit/capabilities/evidence/rule-sets",
    }


def test_a_crlf_rule_set_is_discovered_and_validated_as_its_lf_twin(adopter: AdopterRepo) -> None:
    """A clone with `core.autocrlf=true` checks the file out with `\\r\\n`: both passes
    read it as they read the same text with `\\n`."""
    rel = f"{PROJECT_SETS}/cmn.md"
    text = rule_set_text(cmn())

    def reading() -> tuple[object, ...]:
        rule_result = validate(adopter)
        (rule_set,) = rule_result.discovery.rule_sets
        friction = fv.validate_friction(adopter.root)
        return (
            rule_result.findings,
            rule_set.front_matter,
            rule_set.body,
            [(r.id, r.data, r.section) for r in rule_set.rules],
            [(a.location, a.carrier, a.body, a.anchors) for a in friction.discovery.artefacts],
            [(f.kind, f.where) for f in friction.findings],
        )

    write_set(adopter, rel, cmn())
    lf = reading()
    adopter.write({rel: text.replace("\n", "\r\n")})
    crlf = reading()

    assert crlf == lf
    assert crlf[0] == ()  # clean, as its twin is
    assert crlf[4]  # the rules are artefacts


def test_a_rule_set_mixing_line_endings_is_the_friction_pass_s_finding(
    adopter: AdopterRepo,
) -> None:
    rel = f"{PROJECT_SETS}/cmn.md"
    adopter.write({rel: rule_set_text(cmn()).replace("\n", "\r\n", 1)})
    assert validate(adopter).errors == ()  # the set's shape reads as written
    (finding,) = fv.validate_friction(adopter.root).errors
    assert (finding.kind, finding.location) == (fv.FrictionFindingKind.MIXED_LINE_ENDINGS, rel)


def test_other_collection_files_are_read_as_before(adopter: AdopterRepo) -> None:
    collection = (
        "---\nname: x\nRS-CMN-001:\n  pkit:\n    friction:\n      anchors: {path: [src/**]}\n---\n"
    )
    adopter.write(
        {CONFIG: "name: adopter\nfriction:\n  places: [notes]\n", "notes/rules.md": collection}
    )
    (artefact,) = fd.discover_artefacts(adopter.root).artefacts
    assert (artefact.id, artefact.rule_set) == ("RS-CMN-001", None)


def test_a_rule_s_container_is_validated_once_by_the_rule_set_pass(adopter: AdopterRepo) -> None:
    front = cmn()
    front["rules"]["RS-CMN-002"] = {"pkit": {"frictoin": {"anchors": {"path": ["src/**"]}}}}
    front["rules"]["RS-CMN-005"]["pkit"] = {"friction": {"anchor": {"path": ["src/**"]}}}
    write_set(adopter, f"{PROJECT_SETS}/cmn.md", front)
    adopter.write({f"{PROJECT_SETS}/broken.md": "---\nrules: [unclosed\n---\n"})

    rule_result = validate(adopter)
    assert [(f.where, f.kind) for f in rule_result.errors] == [
        (f"{PROJECT_SETS}/broken.md", Kind.UNREADABLE),
        (f"{PROJECT_SETS}/cmn.md#RS-CMN-002 /pkit/frictoin", Kind.MALFORMED_CONTAINER),
        (f"{PROJECT_SETS}/cmn.md#RS-CMN-005 /pkit/friction", Kind.MALFORMED_CONTAINER),
    ]
    assert "unknown key 'frictoin'; did you mean 'friction'?" in rule_result.errors[1].message
    assert "'anchor' was unexpected" in rule_result.errors[2].message

    # The friction pass walks the rules, but leaves the claimed file's findings alone.
    friction_result = fv.validate_friction(adopter.root)
    assert friction_result.errors == ()
    assert not friction_result.is_dormant


def test_a_rule_s_role_blocks_are_read_against_the_active_wiring(
    adopter: AdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The rule-set pass hands the container validator the resolver's wiring, as the
    friction pass does: an active role's point block at another version is inert,
    and only the role nobody provides is orphaned."""
    front = cmn()
    front["rules"]["RS-CMN-003"]["pkit"] = {
        "documentation": {"reading-evidence": {"schema_version": 2}},
        "analysis": {"glossary": {"schema_version": 1}},
    }
    write_set(adopter, f"{PROJECT_SETS}/cmn.md", front)
    wiring = bs.ContainerWiring(
        providers={"pkit::documentation": "docs-a"},
        points={"pkit::documentation:reading-evidence": bs.ActivePoint(1)},
    )
    monkeypatch.setattr(cx, "container_wiring", lambda _root: wiring)

    result = validate(adopter)
    assert result.errors == ()
    entry = f"{PROJECT_SETS}/cmn.md#RS-CMN-003"
    assert [(f.where, f.kind) for f in result.reports] == [
        (f"{entry} /pkit/documentation/reading-evidence", Kind.CONTAINER_REPORT),
        (f"{entry} /pkit/analysis", Kind.CONTAINER_REPORT),
    ]
    assert "inert" in result.reports[0].message
    assert "no active provider" in result.reports[1].message


def test_rules_take_part_in_the_friction_cycle_check(adopter: AdopterRepo) -> None:
    front = cmn()
    front["rules"]["RS-CMN-002"] = {"pkit": {"friction": {"anchors": {"artefact": ["guide"]}}}}
    write_set(adopter, f"{PROJECT_SETS}/cmn.md", front)
    guide = (
        "---\nid: guide\npkit:\n  friction:\n    anchors: {artefact: [RS-CMN-002]}\n---\n\nBody.\n"
    )
    adopter.write(
        {CONFIG: "name: adopter\nfriction:\n  places: [guides]\n", "guides/guide.md": guide}
    )
    (cycle,) = fv.validate_friction(adopter.root).errors
    assert cycle.kind is fv.FrictionFindingKind.CYCLE
    assert "RS-CMN-002 -> guide -> RS-CMN-002" in cycle.message


# --- citations ----------------------------------------------------------------------


@pytest.fixture
def cited(make_adopter_repo: MakeAdopterRepo) -> AdopterRepo:
    """A project set CMN and a method set EV shipped by the evidence capability."""
    adopter = make_adopter_repo(capabilities=("evidence",))
    write_set(adopter, f"{PROJECT_SETS}/cmn.md", cmn())
    write_set(
        adopter,
        ".pkit/capabilities/evidence/rule-sets/ev.md",
        {"rule-set": "EV", "version": "1.0.0", "rules": {"RS-EV-001": {"offers": ["reader"]}}},
    )
    return adopter


@pytest.mark.parametrize(
    ("citation", "location"),
    [
        ("RS-CMN-001", f"{PROJECT_SETS}/cmn.md#RS-CMN-001"),
        ("RS-CMN-001#cause-location", f"{PROJECT_SETS}/cmn.md#RS-CMN-001"),
        ("[evidence:RS-EV-001]", ".pkit/capabilities/evidence/rule-sets/ev.md#RS-EV-001"),
        ("evidence:RS-EV-001#reader", ".pkit/capabilities/evidence/rule-sets/ev.md#RS-EV-001"),
        ("RS-EV-001", ".pkit/capabilities/evidence/rule-sets/ev.md#RS-EV-001"),
    ],
)
def test_every_citation_form_resolves_to_the_rule(
    cited: AdopterRepo, citation: str, location: str
) -> None:
    resolution = refs.resolve_rule_citation(cited.root, citation)
    assert resolution.resolved, resolution.problem
    assert resolution.location == location


@pytest.mark.parametrize(
    ("citation", "problem"),
    [
        ("RS-CMN-099", "rule set CMN has no rule RS-CMN-099"),
        ("RS-XYZ-001", "no rule set is named XYZ"),
        ("RS-CMN-001#nowhere", "offers no extension point #nowhere"),
        ("[living-docs:RS-EV-001]", "belongs to capability evidence, not to living-docs"),
        ("[evidence:RS-CMN-001]", "belongs to the project, not to evidence, and is cited CMN"),
        ("CMN-001", "not a rule citation"),
    ],
)
def test_a_citation_that_does_not_resolve_says_why(
    cited: AdopterRepo, citation: str, problem: str
) -> None:
    resolution = refs.resolve_rule_citation(cited.root, citation)
    assert not resolution.resolved
    assert problem in (resolution.problem or "")


def test_body_citations_are_extracted_in_every_form() -> None:
    body = (
        "Follow RS-CMN-001, fill `RS-CMN-001#cause-location`, and see [evidence:RS-EV-001] "
        "or [evidence:RS-EV-001#reader]. Not RS-CMN-0012, not xRS-CMN-001.\n"
        "```\nRS-CMN-777 inside a fence\n```\n"
    )
    assert refs.extract_body_refs(body).rule_citations == frozenset(
        {
            "RS-CMN-001",
            "RS-CMN-001#cause-location",
            "evidence:RS-EV-001",
            "evidence:RS-EV-001#reader",
        }
    )


def test_refs_validate_reports_only_the_citation_that_does_not_resolve(cited: AdopterRepo) -> None:
    cited.write(
        {
            ".pkit/agents/project/rule-reader.md": (
                "---\nname: rule-reader\ndescription: Reads rules.\ntools: [Read]\n---\n\n"
                "Apply RS-CMN-001 and [evidence:RS-EV-001]; never RS-CMN-999.\n"
            )
        }
    )
    issues = [i for i in refs.validate_corpus(cited.root) if "cites rule" in i.diagnosis]
    assert [(i.location, i.diagnosis.split(",")[0]) for i in issues] == [
        (".pkit/agents/project/rule-reader.md", "cites rule 'RS-CMN-999'")
    ]


def test_refs_lookup_resolves_a_rule(cited: AdopterRepo) -> None:
    runner = CliRunner()
    found = runner.invoke(main, ["refs", "lookup", "[evidence:RS-EV-001]"])
    assert found.exit_code == 0, found.output
    assert found.output.strip() == ".pkit/capabilities/evidence/rule-sets/ev.md#RS-EV-001"
    missing = runner.invoke(main, ["refs", "lookup", "RS-CMN-999"])
    assert missing.exit_code != 0
    assert "has no rule RS-CMN-999" in missing.output


# --- the rule id space in `pkit decisions validate` -------------------------------------


def test_decisions_validate_reports_a_rule_id_colliding_across_rule_sets(
    adopter: AdopterRepo,
) -> None:
    write_set(adopter, f"{PROJECT_SETS}/a.md", cmn())
    write_set(
        adopter,
        f"{PROJECT_SETS}/b.md",
        {"rule-set": "B", "version": "1.0.0", "rules": {"RS-CMN-002": {}}},
    )
    report = decisions_validate.validate_decision_ids(adopter.root)

    (issue,) = [i for i in report.issues if i.location.startswith("rules ::")]
    assert issue.location == "rules :: RS-CMN-002"
    assert f"{PROJECT_SETS}/a.md, {PROJECT_SETS}/b.md" in issue.message
    assert report.rules_checked == 7

    result = CliRunner().invoke(main, ["decisions", "validate"])
    assert result.exit_code != 0
    assert "rules :: RS-CMN-002" in result.output


def test_decisions_validate_counts_rules_when_the_space_is_clean(adopter: AdopterRepo) -> None:
    write_set(adopter, f"{PROJECT_SETS}/cmn.md", cmn())
    result = CliRunner().invoke(main, ["decisions", "validate"])
    assert result.exit_code == 0, result.output
    assert "and 6 rule(s). No id collisions found." in result.output


# --- `pkit validate`, determinism, the shipped schema --------------------------------


def test_validate_command_prints_the_rule_sets_section_and_fails_on_errors(
    adopter: AdopterRepo,
) -> None:
    front = cmn()
    del front["rules"]["RS-CMN-001"]["origin"]
    front["rules"]["RS-CMN-001"]["origin"] = {
        "decision": "COR-051",
        "source": {"kind": "k", "value": "v"},
    }
    del front["rules"]["RS-CMN-005"]["origin"]
    write_set(adopter, f"{PROJECT_SETS}/cmn.md", front)
    result = CliRunner().invoke(main, ["validate", "--no-refs"])

    assert result.exit_code == 1, result.output
    out = result.output
    section = out.split("\n  rule-sets\n")[1]
    assert section.lstrip().startswith("1 rule set(s), 6 rule(s)")
    assert "1 error(s), 1 report(s)." in section
    assert f"error    {PROJECT_SETS}/cmn.md#RS-CMN-005" in section
    assert f"report   {PROJECT_SETS}/cmn.md#RS-CMN-001:/origin/source" in section
    assert out.index("\n  friction\n") < out.index("\n  rule-sets\n")


def test_validate_command_is_quiet_on_a_fresh_install(adopter: AdopterRepo) -> None:
    result = CliRunner().invoke(main, ["validate", "--no-refs"])
    assert result.exit_code == 0, result.output
    assert "\n  rule-sets\n    no rule sets found." in result.output


def test_findings_are_deterministic(adopter: AdopterRepo) -> None:
    broken = cmn()
    del broken["rules"]["RS-CMN-001"]["origin"]
    broken["rules"]["RS-DOC-009"] = {}
    write_set(adopter, f"{PROJECT_SETS}/z.md", broken, sections=["RS-CMN-001", "RS-CMN-099"])
    write_set(adopter, f"{PROJECT_SETS}/y.md", doc("CMN@9", "A@1"))
    write_set(
        adopter,
        f"{PROJECT_SETS}/a.md",
        {"rule-set": "A", "version": "1.0.0", "rules": {}, "inherits": ["DOC@1"]},
    )
    first, second = validate(adopter), validate(adopter)

    assert first.findings == second.findings
    locations = [f.location.split("#")[0] for f in first.findings]
    assert locations == sorted(locations[:-1]) + locations[-1:]  # files by path, then cycles
    assert first.findings[-1].kind is Kind.INHERITANCE_CYCLE


def test_a_tree_without_the_schema_skips_the_kind(adopter: AdopterRepo) -> None:
    write_set(adopter, f"{PROJECT_SETS}/cmn.md", {"rule-set": "bad"})
    (adopter.pkit / "schemas" / "backbone" / "rule-set.schema.json").unlink()
    (finding,) = validate(adopter).findings
    assert (finding.kind, finding.severity) == (Kind.SCHEMA_UNAVAILABLE, rs.Severity.REPORT)
    assert "not validated" in finding.message


def test_the_reference_example_has_the_shipped_shape() -> None:
    """The front matter shown in the schemas README's "Rule-set files" section is valid."""
    readme = (REPO / ".pkit/schemas/README.md").read_text(encoding="utf-8")
    section = readme.split("### Rule-set files", 1)[1]
    example = section.split("```yaml\n", 1)[1].split("```", 1)[0]
    front_matter, body = fd.split_front_matter(example)
    assert front_matter is not None and body.startswith("## RS-DOC-001")
    data = bs.as_written(YAML(typ="safe").load(front_matter))
    schema = json.loads((REPO / ".pkit/schemas/backbone/rule-set.schema.json").read_text())
    errors = [e.message for e in Draft202012Validator(schema).iter_errors(data)]
    assert errors == []


def test_the_shipped_schema_is_draft_2020_12_and_matches_the_grammar() -> None:
    schema = json.loads((REPO / ".pkit/schemas/backbone/rule-set.schema.json").read_text())
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    defs = schema["$defs"]
    assert defs["set-name"]["pattern"] == f"^{rs.SET_NAME_PATTERN}$"
    assert defs["rule-id"]["pattern"] == f"^{rs.RULE_ID_PATTERN}$"
    assert defs["point-name"]["pattern"] == f"^{rs.POINT_NAME_PATTERN}$"
    component = f"(?:{rs.COMPONENT_PATTERN}:)?"
    assert defs["rule-reference"]["pattern"] == f"^{component}{rs.RULE_ID_PATTERN}$"
    point = f"#{rs.POINT_NAME_PATTERN}"
    assert defs["point-reference"]["pattern"] == f"^{component}{rs.RULE_ID_PATTERN}{point}$"
    assert defs["pin"]["pattern"] == f"^{component}{rs.SET_NAME_PATTERN}@{rs.MAJOR_PATTERN}$"
    shared = json.loads((REPO / ".pkit/schemas/_defs/refs.schema.json").read_text())
    assert shared["$defs"]["rule_citation"]["pattern"] == (
        f"^{component}{rs.RULE_ID_PATTERN}(?:{point})?$"
    )
