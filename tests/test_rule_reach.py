"""Tests for where accepted rules bind (COR-051 point 7, Task #1408): the reach walk at
one state, `pkit rule-sets reach`, what a change altered with the rules at each
state, `pkit rule-sets altered`, the conflicts validation fails, the declared check
parts, and the rule-set reader at a commit.

Built on the shared adopter-repository fixture. Project rule sets live in
`docs/rule-sets/` (the internal documentation root's default); the artefacts they
scope live in `docs/guides/`, the one declared place, so the rules themselves stay
out of every scope.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import pytest
from click.testing import CliRunner

from project_kit import friction_check as fc
from project_kit import friction_discovery as fd
from project_kit import rule_set_reading as reading
from project_kit import rule_sets as rs
from project_kit.cli import main
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.friction_documents import CONFIG, SOURCE, T2, friction_config, guide
from tests.test_rule_sets import QUOTE, anchored_to, rule_set_text, rules

Kind = rs.RuleSetFindingKind

SETS = "docs/rule-sets"
GUIDES = "docs/guides"
A = f"{GUIDES}/a.md"


@pytest.fixture
def repo(make_adopter_repo: MakeAdopterRepo) -> AdopterRepo:
    return make_adopter_repo()


def page(title: str = "A guide", body: str = "Body.") -> str:
    return f"---\ntitle: {title}\n---\n\n{body}\n"


def scoped(*paths: str) -> dict[str, Any]:
    return {"paths": list(paths)}


def rule_set(
    name: str,
    version: str = "1.0.0",
    *,
    inherits: list[str] | None = None,
    scope: Any = None,
    entries: Mapping[str, Any] | None = None,
    **front: Any,
) -> dict[str, Any]:
    """A rule set's front matter: `entries` its rules, else one accepted rule `RS-<name>-001`."""
    data: dict[str, Any] = {"rule-set": name, "version": version}
    if inherits is not None:
        data["inherits"] = inherits
    if scope is not None:
        data["scope"] = scope
    data["rules"] = dict(entries) if entries is not None else rules(f"RS-{name}-001")
    data.update(front)
    return data


def lay_out(repo: AdopterRepo, sets: Mapping[str, Mapping[str, Any]], **pages: str) -> None:
    """The configuration declaring `docs/guides`, each set at `docs/rule-sets/<key>.md`, and
    each page (keyword `a` is `docs/guides/a.md`; a `__` in a key is a folder)."""
    files = {CONFIG: friction_config(places=(GUIDES,))}
    files.update({f"{SETS}/{key}.md": rule_set_text(front) for key, front in sets.items()})
    files.update({f"{GUIDES}/{key.replace('__', '/')}.md": text for key, text in pages.items()})
    repo.write(files)


def bound(repo: AdopterRepo, location: str = A) -> list[str]:
    """The rules that bind on the artefact at `location`, as cited, in the walk's order."""
    _discovery, _sets, answer = rs.reach_at(repo.root)
    return [b.rule_set.cite(b.rule.id) for b in answer.of(location).bindings]


def binding(repo: AdopterRepo, rule: str, location: str = A) -> rs.Binding:
    _discovery, _sets, answer = rs.reach_at(repo.root)
    (found,) = [b for b in answer.of(location).bindings if b.rule.id == rule]
    return found


def errors(repo: AdopterRepo, kind: Kind) -> list[rs.RuleSetFinding]:
    return [f for f in rs.validate_rule_sets(repo.root).findings if f.kind is kind]


# --- reach at one state (COR-051 point 7) -------------------------------------------------


def test_an_inherited_rule_binds_within_the_inheriting_set_s_scope(repo: AdopterRepo) -> None:
    """A shared set with no scope reaches wherever the sets inheriting it reach."""
    lay_out(
        repo,
        {
            "cmn": rule_set("CMN"),
            "doc": rule_set("DOC", inherits=["CMN@1"], scope=scoped(f"{GUIDES}/**")),
        },
        a=page(),
    )
    repo.write({"docs/elsewhere.md": page()})
    assert bound(repo) == ["RS-CMN-001", "RS-DOC-001"]
    assert [s.path for s in binding(repo, "RS-CMN-001").covering] == [f"{SETS}/doc.md"]
    assert bound(repo, "docs/elsewhere.md") == []
    assert not rs.validate_rule_sets(repo.root).errors


def test_a_set_with_no_scope_inherited_by_none_binds_nothing(repo: AdopterRepo) -> None:
    lay_out(repo, {"cmn": rule_set("CMN")}, a=page())
    assert bound(repo) == []


def test_a_parent_with_a_scope_of_its_own_keeps_it(repo: AdopterRepo) -> None:
    """A parent's rules bind only where its own scope also selects the artefact."""
    lay_out(
        repo,
        {
            "doc": rule_set("DOC", inherits=["SUB@1"], scope=scoped(f"{GUIDES}/**")),
            "sub": rule_set("SUB", scope=scoped(f"{GUIDES}/sub/**")),
        },
        a=page(),
        sub__c=page(),
    )
    assert bound(repo) == ["RS-DOC-001"]
    sub = f"{GUIDES}/sub/c.md"
    assert bound(repo, sub) == ["RS-DOC-001", "RS-SUB-001"]
    assert [s.path for s in binding(repo, "RS-SUB-001", sub).covering] == [
        f"{SETS}/doc.md",
        f"{SETS}/sub.md",
    ]


def _filling(**overrides: Any) -> dict[str, Any]:
    """A rule filling CMN's `RS-CMN-001#where`, anchored to the rule it fills."""
    return {"fills": ["RS-CMN-001#where"], **anchored_to("RS-CMN-001"), **overrides}


def _offering() -> dict[str, Any]:
    return rule_set("CMN", entries={**rules("RS-CMN-001", offers=["where"]), **rules("RS-CMN-002")})


def test_a_fill_binds_where_the_rule_it_fills_binds_through_the_filling_set(
    repo: AdopterRepo,
) -> None:
    lay_out(
        repo,
        {
            "cmn": _offering(),
            "doc": rule_set(
                "DOC",
                inherits=["CMN@1"],
                scope=scoped(f"{GUIDES}/**"),
                entries=rules("RS-DOC-001", **_filling()),
            ),
        },
        a=page(),
    )
    assert bound(repo) == ["RS-CMN-001", "RS-CMN-002", "RS-DOC-001"]
    assert binding(repo, "RS-DOC-001").fills == ("RS-CMN-001#where",)
    assert binding(repo, "RS-CMN-002").fills == ()
    assert not rs.validate_rule_sets(repo.root).errors


def test_a_fill_binds_nothing_once_the_rule_it_fills_is_no_longer_accepted(
    repo: AdopterRepo,
) -> None:
    offering = _offering()
    offering["rules"]["RS-CMN-001"]["status"] = "withdrawn"
    lay_out(
        repo,
        {
            "cmn": offering,
            "doc": rule_set(
                "DOC",
                inherits=["CMN@1"],
                scope=scoped(f"{GUIDES}/**"),
                entries={**rules("RS-DOC-001", **_filling()), **rules("RS-DOC-002")},
            ),
        },
        a=page(),
    )
    assert bound(repo) == ["RS-CMN-002", "RS-DOC-002"]


def test_the_more_specific_set_s_fill_binds_and_is_no_conflict(repo: AdopterRepo) -> None:
    """P inherits Q, both select the artefact: P is the more specific, so its fill binds
    although Q's chain brings none (COR-051 point 7, "Fills through several sets")."""
    lay_out(
        repo,
        {
            "cmn": _offering(),
            "q": rule_set("Q", inherits=["CMN@1"], scope=scoped(f"{GUIDES}/**")),
            "p": rule_set(
                "P",
                inherits=["Q@1"],
                scope=scoped(f"{GUIDES}/**"),
                entries=rules("RS-P-001", **_filling()),
            ),
        },
        a=page(),
    )
    assert "RS-P-001" in bound(repo)
    assert binding(repo, "RS-P-001").fills == ("RS-CMN-001#where",)
    assert errors(repo, Kind.FILL_CONFLICT) == []


def test_a_successor_binds_where_its_own_set_is_reached(repo: AdopterRepo) -> None:
    """The superseded rule binds nothing; its successor, in a set inheriting the
    original's, binds only where that set is reached (COR-051 point 4)."""
    cmn = rule_set(
        "CMN",
        "2.0.0",
        entries={
            **rules("RS-CMN-001"),
            "RS-CMN-002": {"status": "superseded", "successor": "RS-NEW-001", "origin": QUOTE},
        },
    )
    lay_out(
        repo,
        {
            "cmn": cmn,
            "doc": rule_set("DOC", inherits=["CMN@2"], scope=scoped(f"{GUIDES}/**")),
            "new": rule_set("NEW", inherits=["CMN@2"], scope=scoped(f"{GUIDES}/new/**")),
        },
        a=page(),
        new__b=page(),
    )
    assert bound(repo) == ["RS-CMN-001", "RS-DOC-001"]
    assert bound(repo, f"{GUIDES}/new/b.md") == ["RS-CMN-001", "RS-DOC-001", "RS-NEW-001"]


def test_no_rule_binds_through_a_pin_behind_its_set(repo: AdopterRepo) -> None:
    lay_out(
        repo,
        {
            "cmn": rule_set("CMN", "2.0.0"),
            "doc": rule_set("DOC", inherits=["CMN@1"], scope=scoped(f"{GUIDES}/**")),
        },
        a=page(),
    )
    assert bound(repo) == ["RS-DOC-001"]


def held(repo: AdopterRepo, location: str = A) -> list[tuple[str, list[str]]]:
    """The rules pins behind their sets hold back from the artefact at `location`, as
    cited, each with those pins as `<set> pins <pin>`."""
    found = rs.reach_at(repo.root)[2].of(location).held
    return [
        (h.rule_set.cite(h.rule.id), [f"{by.citation} pins {pin}" for by, _i, pin in h.pins])
        for h in found
    ]


def test_the_answer_names_the_rules_a_pin_behind_its_set_holds_back(repo: AdopterRepo) -> None:
    """COR-057's Implications: the backbone gives the rules a pin behind its set holds back,
    beside the rules that bind. They bind nothing; a reviewer may only inform of them."""
    lay_out(
        repo,
        {
            "cmn": rule_set(
                "CMN", "2.0.0", entries={**rules("RS-CMN-001", "RS-CMN-002"), "RS-CMN-003": {}}
            ),
            "doc": rule_set("DOC", inherits=["CMN@1"], scope=scoped(f"{GUIDES}/**")),
        },
        a=page(),
    )
    assert bound(repo) == ["RS-DOC-001"]
    # The proposed RS-CMN-003 binds nothing whatever its pins, so nothing holds it back.
    assert held(repo) == [
        ("RS-CMN-001", ["DOC pins CMN@1"]),
        ("RS-CMN-002", ["DOC pins CMN@1"]),
    ]
    document = reading.reach_document(repo.root)
    (entry,) = document["artefacts"]
    assert [(h["rule"], h["status"], h["rule_set_path"], h["pins"]) for h in entry["held"]] == [
        (
            "RS-CMN-001",
            "accepted",
            f"{SETS}/cmn.md",
            [{"by": f"{SETS}/doc.md", "by_rule_set": "DOC", "pin": "CMN@1"}],
        ),
        (
            "RS-CMN-002",
            "accepted",
            f"{SETS}/cmn.md",
            [{"by": f"{SETS}/doc.md", "by_rule_set": "DOC", "pin": "CMN@1"}],
        ),
    ]
    assert entry["held"][0]["text"].startswith("## RS-CMN-001 — Rule RS-CMN-001")
    assert "RS-CMN-001  (CMN)  held back, binding nothing: DOC pins CMN@1" in (
        reading.render_reach_human(document)
    )


def test_a_rule_reached_cleanly_too_is_not_held_back(repo: AdopterRepo) -> None:
    """A rule binds through any route whose pins are not behind, so a second route behind
    its set holds nothing back; a set beyond the held one is held back by the same pin."""
    lay_out(
        repo,
        {
            "base": rule_set("BASE"),
            "cmn": rule_set("CMN", "2.0.0", inherits=["BASE@1"]),
            "doc": rule_set("DOC", inherits=["CMN@1"], scope=scoped(f"{GUIDES}/**")),
            "own": rule_set("OWN", inherits=["CMN@2"], scope=scoped(f"{GUIDES}/b.md")),
        },
        a=page(),
        b=page(),
    )
    assert held(repo) == [
        ("RS-BASE-001", ["DOC pins CMN@1"]),
        ("RS-CMN-001", ["DOC pins CMN@1"]),
    ]
    b = f"{GUIDES}/b.md"
    assert bound(repo, b) == ["RS-BASE-001", "RS-CMN-001", "RS-DOC-001", "RS-OWN-001"]
    assert held(repo, b) == []


def test_a_rule_that_fills_is_never_held_back_as_a_rule(repo: AdopterRepo) -> None:
    """A fill binds only as a fill, so a pin behind its set holds back the rules of the
    sets beyond it, and never a filling rule as a rule of its own."""
    lay_out(
        repo,
        {
            "cmn": _offering(),
            "fill": rule_set(
                "FILL", "2.0.0", inherits=["CMN@1"], entries=rules("RS-FILL-001", **_filling())
            ),
            "doc": rule_set("DOC", inherits=["FILL@1"], scope=scoped(f"{GUIDES}/**")),
        },
        a=page(),
    )
    assert bound(repo) == ["RS-DOC-001"]
    assert held(repo) == [
        ("RS-CMN-001", ["DOC pins FILL@1"]),
        ("RS-CMN-002", ["DOC pins FILL@1"]),
    ]


def test_a_held_rule_names_only_the_pins_on_the_artefact_s_routes(repo: AdopterRepo) -> None:
    """A pin leads towards a held rule only along routes that pass each set's own scope:
    TTT is reached through WWW alone, since the route through YYY stops at ZZZ, whose
    scope does not select the artefact."""
    lay_out(
        repo,
        {
            "doc": rule_set("DOC", inherits=["YYY@1", "WWW@1"], scope=scoped(f"{GUIDES}/**")),
            "yyy": rule_set("YYY", "2.0.0", inherits=["ZZZ@1"]),
            "zzz": rule_set("ZZZ", inherits=["TTT@1"], scope=scoped("docs/other/**")),
            "www": rule_set("WWW", "2.0.0", inherits=["TTT@1"]),
            "ttt": rule_set("TTT"),
        },
        a=page(),
    )
    assert held(repo) == [
        ("RS-TTT-001", ["DOC pins WWW@1"]),
        ("RS-WWW-001", ["DOC pins WWW@1"]),
        ("RS-YYY-001", ["DOC pins YYY@1"]),
    ]


def test_an_artefact_whose_rules_are_all_held_back_is_listed(repo: AdopterRepo) -> None:
    lay_out(
        repo,
        {
            "cmn": rule_set("CMN", "2.0.0"),
            "doc": rule_set(
                "DOC", inherits=["CMN@1"], scope=scoped(f"{GUIDES}/**"), entries={"RS-DOC-001": {}}
            ),
        },
        a=page(),
    )
    (entry,) = reading.reach_document(repo.root)["artefacts"]
    assert entry["location"] == A and entry["rules"] == [] and entry["conflicts"] == []
    assert [h["rule"] for h in entry["held"]] == ["RS-CMN-001"]


def test_a_pin_ahead_of_its_set_is_not_behind_it(repo: AdopterRepo) -> None:
    """COR-051 point 7 holds rules back only through a pin behind its set; a pin ahead
    does not hold, and the version relations report it (`PinCheck.problem`)."""
    lay_out(
        repo,
        {
            "cmn": rule_set("CMN", "2.0.0"),
            "doc": rule_set("DOC", inherits=["CMN@3"], scope=scoped(f"{GUIDES}/**")),
        },
        a=page(),
    )
    assert bound(repo) == ["RS-CMN-001", "RS-DOC-001"]
    (check,) = rs.pin_checks(rs.discover_rule_sets(repo.root))
    assert not check.behind and check.problem is not None


def test_a_method_rule_set_s_scope_starts_no_route_and_narrows_none(repo: AdopterRepo) -> None:
    """Every route starts at a set of the project's own (COR-051 point 7); the scope on a
    method rule set is refused, and read as none."""
    lay_out(
        repo,
        {"doc": rule_set("DOC", inherits=["backbone:BB@1"], scope=scoped(f"{GUIDES}/**"))},
        a=page(),
        b=page(),
    )
    repo.write({".pkit/rule-sets/bb.md": rule_set_text(rule_set("BB", scope=[f"{GUIDES}/b.md"]))})
    assert bound(repo) == ["backbone:RS-BB-001", "RS-DOC-001"]
    assert bound(repo, f"{GUIDES}/b.md") == ["backbone:RS-BB-001", "RS-DOC-001"]
    lay_out(repo, {"doc": rule_set("DOC", scope=scoped(f"{GUIDES}/a.md"))}, a=page(), b=page())
    assert bound(repo, f"{GUIDES}/b.md") == []


def test_an_inheritance_cycle_ends_the_walk(repo: AdopterRepo) -> None:
    lay_out(
        repo,
        {
            "one": rule_set("ONE", inherits=["TWO@1"], scope=scoped(f"{GUIDES}/**")),
            "two": rule_set("TWO", inherits=["ONE@1"]),
        },
        a=page(),
    )
    assert bound(repo) == ["RS-ONE-001", "RS-TWO-001"]
    assert errors(repo, Kind.INHERITANCE_CYCLE)


# --- the conflicts validation fails (COR-051 point 7) ---------------------------------


def test_routes_pinning_one_set_at_different_majors_fail_validation(repo: AdopterRepo) -> None:
    lay_out(
        repo,
        {
            "cmn": rule_set("CMN", "2.0.0"),
            "tech": rule_set("TECH", inherits=["CMN@1"], scope=scoped(f"{GUIDES}/**")),
            "user": rule_set("USER", inherits=["CMN@2"], scope=scoped(f"{GUIDES}/a.md")),
        },
        a=page(),
        b=page(),
    )
    (finding,) = errors(repo, Kind.PIN_CONFLICT)
    assert finding.location == A
    assert "TECH pins CMN@1" in finding.message and "USER pins CMN@2" in finding.message
    _discovery, _sets, answer = rs.reach_at(repo.root)
    (conflict,) = answer.of(A).conflicts
    assert isinstance(conflict, rs.PinConflict) and conflict.rule_set.name == "CMN"
    assert answer.of(f"{GUIDES}/b.md").conflicts == ()  # one route only


def test_routes_filling_one_point_differently_fail_validation_and_bind_no_fill(
    repo: AdopterRepo,
) -> None:
    """Two sets, neither inheriting the other, select one artefact: one fills, the other
    brings none — a fill against none — so no fill binds, and the answer names it."""
    lay_out(
        repo,
        {
            "cmn": _offering(),
            "tech": rule_set(
                "TECH",
                inherits=["CMN@1"],
                scope=scoped(f"{GUIDES}/**"),
                entries=rules("RS-TECH-001", **_filling()),
            ),
            "user": rule_set("USER", inherits=["CMN@1"], scope=scoped(f"{GUIDES}/a.md")),
        },
        a=page(),
        b=page(),
    )
    (finding,) = errors(repo, Kind.FILL_CONFLICT)
    assert finding.location == A
    assert "TECH brings RS-TECH-001" in finding.message and "USER brings none" in finding.message
    assert "RS-TECH-001" not in bound(repo)
    assert "RS-CMN-001" in bound(repo)  # the offering rule still binds
    assert "RS-TECH-001" in bound(repo, f"{GUIDES}/b.md")  # one route: the fill binds


def test_two_different_fills_of_one_point_fail_validation(repo: AdopterRepo) -> None:
    lay_out(
        repo,
        {
            "cmn": _offering(),
            "tech": rule_set(
                "TECH",
                inherits=["CMN@1"],
                scope=scoped(f"{GUIDES}/**"),
                entries=rules("RS-TECH-001", **_filling()),
            ),
            "user": rule_set(
                "USER",
                inherits=["CMN@1"],
                scope=scoped(f"{GUIDES}/**"),
                entries=rules("RS-USER-001", **_filling()),
            ),
        },
        a=page(),
    )
    assert [f.location for f in errors(repo, Kind.FILL_CONFLICT)] == [A]
    assert not {"RS-TECH-001", "RS-USER-001"} & set(bound(repo))


def test_a_most_specific_set_brings_the_fill_its_chain_holds_whatever_its_pins(
    repo: AdopterRepo,
) -> None:
    """T inherits S through a pin behind S, so no rule binds through that pin. T is still
    the more specific set, and its chain holds S's fill, which binds through S's own
    route (COR-051 point 7, "Fills through several sets")."""
    lay_out(
        repo,
        {
            "cmn": _offering(),
            "s": rule_set(
                "S",
                "2.0.0",
                inherits=["CMN@1"],
                scope=scoped(f"{GUIDES}/**"),
                entries=rules("RS-S-001", **_filling()),
            ),
            "t": rule_set("T", inherits=["S@1", "CMN@1"], scope=scoped(f"{GUIDES}/**")),
        },
        a=page(),
    )
    assert binding(repo, "RS-S-001").fills == ("RS-CMN-001#where",)
    assert errors(repo, Kind.FILL_CONFLICT) == []


def test_a_rule_whose_fill_names_no_offered_point_binds_nowhere(repo: AdopterRepo) -> None:
    """A rule that fills binds only as a fill; validation fails the undeclared fill."""
    lay_out(
        repo,
        {
            "cmn": _offering(),
            "doc": rule_set(
                "DOC",
                inherits=["CMN@1"],
                scope=scoped(f"{GUIDES}/**"),
                entries=rules(
                    "RS-DOC-001",
                    fills=["RS-CMN-002#nowhere"],
                    **anchored_to("RS-CMN-002"),
                ),
            ),
        },
        a=page(),
    )
    assert "RS-DOC-001" not in bound(repo)
    assert errors(repo, Kind.UNDECLARED_FILL)


# --- the declared check parts (COR-051 point 2) ------------------------------------------


def test_a_declared_check_part_is_listed_on_its_rule_and_one_not_there_is_reported(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo(capabilities=("living-docs",))
    parts = {
        "RS-CMN-001": [
            {"check": "backbone:validate", "part": "The field resolves."},
            {"check": "backbone:friction check", "part": "Its anchors are answered."},
            {"check": "living-docs:validate", "part": "The sections, in order."},
            {"check": "lint-writing", "part": "Sentence length."},
            {"check": "backbone:no-such-check", "part": "Nothing."},
            {"check": "living-docs:no-such-command", "part": "Nothing."},
            {"check": "nocapability:validate", "part": "Nothing."},
        ],
        "RS-CMN-009": [{"check": "lint-writing", "part": "Nothing."}],
    }
    lay_out(
        repo,
        {
            "cmn": rule_set("CMN", checks=parts),
            "doc": rule_set("DOC", inherits=["CMN@1"], scope=scoped(f"{GUIDES}/**")),
        },
        a=page(),
    )
    result = rs.validate_rule_sets(repo.root)
    rule = result.discovery.sets_named("CMN")[0].rule("RS-CMN-001")
    assert rule is not None
    assert [(p.check, p.owner, p.name) for p in rule.checks][:4] == [
        ("backbone:validate", "backbone", "validate"),
        ("backbone:friction check", "backbone", "friction check"),
        ("living-docs:validate", "living-docs", "validate"),
        ("lint-writing", None, "lint-writing"),
    ]
    unknown = [f for f in result.findings if f.kind is Kind.UNKNOWN_CHECK]
    assert [(f.severity, f.pointer) for f in unknown] == [
        (rs.Severity.REPORT, "/checks/RS-CMN-001/4/check"),
        (rs.Severity.REPORT, "/checks/RS-CMN-001/5/check"),
        (rs.Severity.REPORT, "/checks/RS-CMN-001/6/check"),
    ]
    assert "no installed component is named nocapability" in unknown[2].message
    (missing,) = [f for f in result.findings if f.kind is Kind.CHECK_FOR_NO_RULE]
    assert missing.severity is rs.Severity.ERROR and missing.pointer == "/checks/RS-CMN-009"
    document = reading.reach_document(repo.root)
    (entry,) = [a for a in document["artefacts"] if a["location"] == A]
    (cmn,) = [r for r in entry["rules"] if r["id"] == "RS-CMN-001"]
    # Each declared part says whether its check is there, as validation judges it
    # (COR-057's Implications): a part whose check is not there is the reviewer's.
    assert [(c["check"], c["there"], c["problem"]) for c in cmn["checks"]] == [
        ("backbone:validate", True, None),
        ("backbone:friction check", True, None),
        ("living-docs:validate", True, None),
        ("lint-writing", True, None),
        ("backbone:no-such-check", False, "the backbone has no check `pkit no-such-check`"),
        (
            "living-docs:no-such-command",
            False,
            "living-docs registers no command `no-such-command` in its package metadata",
        ),
        ("nocapability:validate", False, "no installed component is named nocapability"),
    ]
    assert cmn["checks"][0]["part"] == "The field resolves."
    human = reading.render_reach_human(document)
    assert "checked by backbone:validate: The field resolves.\n" in human
    assert (
        "checked by backbone:no-such-check: Nothing.  "
        "(not there: the backbone has no check `pkit no-such-check`)"
    ) in human


def test_a_component_s_check_is_judged_at_the_state_read_a_backbone_check_by_the_tool(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """A component's check is there by the registrations of the state read: the working
    tree's, or the commit's with `--at`, and the base's and the head's for `altered`. A
    backbone check is there by the `pkit` that runs, whatever the state, since no commit
    holds the tool (ADR-057 point 2)."""
    repo = make_adopter_repo(capabilities=("living-docs",))
    parts = {
        "RS-CMN-001": [
            {"check": "living-docs:validate", "part": "The sections."},
            {"check": "backbone:validate", "part": "The field resolves."},
        ]
    }
    lay_out(
        repo,
        {
            "cmn": rule_set("CMN", checks=parts),
            "doc": rule_set("DOC", inherits=["CMN@1"], scope=scoped(f"{GUIDES}/**")),
        },
        a=page(),
    )
    commit = repo.commit("living-docs installed")  # on main, the base below

    def presence(entry: Mapping[str, Any]) -> list[tuple[bool, str | None]]:
        (cmn,) = [r for r in entry["rules"] if r["id"] == "RS-CMN-001"]
        return [(c["there"], c["problem"]) for c in cmn["checks"]]

    def reach(at: str | None) -> list[tuple[bool, str | None]]:
        (entry,) = reading.reach_document(repo.root, at)["artefacts"]
        return presence(entry)

    there = [(True, None), (True, None)]
    gone = [(False, "no installed component is named living-docs"), (True, None)]
    assert reach(None) == reach(commit) == there
    repo.write({".pkit/capabilities/living-docs/package.yaml": None, A: page(body="Edited.")})
    assert reach(None) == gone
    assert reach(commit) == there  # the commit holds the package, whatever this checkout does
    (altered,) = reading.altered_document(repo.root, "main")["artefacts"]
    assert altered["change"] == "changed"
    assert presence(altered["base"]) == there and presence(altered["head"]) == gone


def test_a_commit_s_installed_packages_are_read_from_that_commit(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """The packages a commit installs are its manifest's components whose package file it
    holds: an empty one is installed and registers nothing, an absent one is left out, as
    the working tree's reader keeps and leaves them."""
    repo = make_adopter_repo(capabilities=("living-docs",))
    package = ".pkit/capabilities/living-docs/package.yaml"

    def at(commit: str) -> dict[str, dict[str, Any]]:
        tree = fc.CommitTree(repo.root, commit)
        return {name: found for name, _dir, found in fd.installed_packages_at(repo.root, tree)}

    installed = at(repo.commit("installed"))
    assert "commands" in installed["living-docs"]
    repo.write({package: ""})
    assert at(repo.commit("an empty package file"))["living-docs"] == {}
    repo.write({package: None})
    assert "living-docs" not in at(repo.commit("no package file"))


def test_a_check_part_is_no_part_of_the_rule_s_content(repo: AdopterRepo) -> None:
    """Declared beside the rule, outside its entry: declaring one leaves its content alone."""
    lay_out(repo, {"cmn": rule_set("CMN")}, a=page())
    before = fd.discover_artefacts(repo.root)
    lay_out(
        repo,
        {"cmn": rule_set("CMN", checks={"RS-CMN-001": [{"check": "lint", "part": "All."}]})},
        a=page(),
    )
    after = fd.discover_artefacts(repo.root)
    location = f"{SETS}/cmn.md#RS-CMN-001"
    (old,) = [x for x in before.artefacts if x.location == location]
    (new,) = [x for x in after.artefacts if x.location == location]
    assert not fc.content_differs(new, old)


@pytest.mark.parametrize(
    "declared",
    [{"check": "lint"}, {"check": "living-docs: validate", "part": "An owner, then a space."}],
)
def test_the_schema_refuses_a_malformed_check_part(
    repo: AdopterRepo, declared: dict[str, str]
) -> None:
    """A part is required, and an owner's name followed by a colon and a space would read
    as a bare name, the project's own tool, so it is refused."""
    lay_out(repo, {"cmn": rule_set("CMN", checks={"RS-CMN-001": [declared]})}, a=page())
    assert any(f.kind is Kind.SHAPE for f in rs.validate_rule_sets(repo.root).errors)


# --- the rule-set reader at a commit -------------------------------------------------------


def test_the_rule_set_reader_reads_a_commit_through_discovery_s_tree(repo: AdopterRepo) -> None:
    lay_out(
        repo,
        {
            "cmn": rule_set("CMN"),
            "gone": rule_set("GONE"),
            "doc": rule_set("DOC", inherits=["CMN@1"], scope=scoped(f"{GUIDES}/**")),
        },
        a=page(),
    )
    commit = repo.commit("rule sets")
    repo.write(
        {
            f"{SETS}/cmn.md": rule_set_text(
                rule_set("CMN", "2.0.0", entries=rules("RS-CMN-001", "RS-CMN-002"))
            ),
            f"{SETS}/gone.md": None,
        }
    )
    tree = fc.CommitTree(repo.root, commit)
    at_commit = rs.discover_rule_sets(repo.root, tree=tree)
    now = rs.discover_rule_sets(repo.root)
    assert [s.name for s in at_commit.rule_sets] == ["CMN", "DOC", "GONE"]
    assert [s.name for s in now.rule_sets] == ["CMN", "DOC"]
    assert [r.id for r in at_commit.sets_named("CMN")[0].rules] == ["RS-CMN-001"]
    # the reader and discovery claim the same rule-set files at one state
    walked = fd.discover_artefacts(repo.root, tree=tree)
    assert [s.path for s in at_commit.rule_sets] == [
        f.path for f in walked.files if f.rule_set is not None
    ]
    # the walk at the commit reads that state's rules: CMN@1 held there
    _discovery, _sets, answer = rs.reach_at(repo.root, tree)
    assert [b.rule.id for b in answer.of(A).bindings] == ["RS-CMN-001", "RS-DOC-001"]
    assert bound(repo) == ["RS-DOC-001"]  # the working tree's pin is behind CMN 2.0.0


# --- the reading command at one state ------------------------------------------------------


def _cli(*args: str) -> Any:
    return CliRunner().invoke(main, ["rule-sets", *args])


def test_reach_gives_each_ruled_artefact_with_its_rules(repo: AdopterRepo) -> None:
    lay_out(
        repo,
        {
            "cmn": rule_set("CMN"),
            "doc": rule_set("DOC", inherits=["CMN@1"], scope=scoped(f"{GUIDES}/**")),
        },
        a=page(),
    )
    repo.write({"docs/unruled.md": page()})
    result = _cli("reach", "--json")
    assert result.exit_code == 0, result.output
    document = json.loads(result.output)
    assert document["schema_version"] == 1 and document["commit"] is None
    (entry,) = document["artefacts"]
    assert {k: entry[k] for k in ("location", "kind", "span", "conflicts", "held")} == {
        "location": A,
        "kind": "document",
        "span": None,
        "conflicts": [],
        "held": [],
    }
    assert [r["rule"] for r in entry["rules"]] == ["RS-CMN-001", "RS-DOC-001"]
    cmn = entry["rules"][0]
    assert {k: cmn[k] for k in ("status", "rule_set", "rule_set_path", "covering", "fills")} == {
        "status": "accepted",
        "rule_set": "CMN",
        "rule_set_path": f"{SETS}/cmn.md",
        "covering": [f"{SETS}/doc.md"],
        "fills": [],
    }
    assert cmn["text"].startswith("## RS-CMN-001 — Rule RS-CMN-001")
    human = _cli("reach")
    assert human.exit_code == 0 and "RS-CMN-001  (CMN)  through docs/rule-sets/doc.md" in (
        human.output
    )


def test_reach_at_a_commit_reads_that_state(repo: AdopterRepo) -> None:
    lay_out(repo, {"doc": rule_set("DOC", scope=scoped(f"{GUIDES}/**"))}, a=page())
    commit = repo.commit("ruled")
    repo.write({f"{SETS}/doc.md": None})
    assert json.loads(_cli("reach", "--json").output)["artefacts"] == []
    at = json.loads(_cli("reach", "--at", "HEAD", "--json").output)
    assert at["commit"] == commit and [a["location"] for a in at["artefacts"]] == [A]
    refused = _cli("reach", "--at", "no-such-rev")
    assert refused.exit_code == 1 and "names no commit" in refused.output


# --- what a change altered, with the rules at each state ----------------------------------


def _start(repo: AdopterRepo) -> None:
    """The base on `main`: a ruled guide per letter, and one with an identity of its own;
    then branch `feature`."""
    lay_out(
        repo,
        {
            "cmn": rule_set("CMN"),
            "doc": rule_set("DOC", inherits=["CMN@1"], scope=scoped(f"{GUIDES}/**")),
        },
        a=guide(),
        b=page("B"),
        c=page("C"),
        old=page(
            "Old",
            body="An old guide, about something else entirely, and long enough to stand apart.",
        ),
    )
    repo.write(SOURCE)
    repo.commit("base", files=None)
    repo.checkout("feature", create=True)


def _altered(repo: AdopterRepo, **kwargs: Any) -> list[tuple[str, str | None, str | None]]:
    document = reading.altered_document(repo.root, "main", **kwargs)
    return [
        (
            entry["change"],
            None if entry["base"] is None else entry["base"]["location"],
            None if entry["head"] is None else entry["head"]["location"],
        )
        for entry in document["artefacts"]
    ]


def test_a_move_keeping_content_and_a_revalidation_alone_alter_nothing(repo: AdopterRepo) -> None:
    _start(repo)
    repo.rename(f"{GUIDES}/b.md", f"{GUIDES}/moved/b.md")
    repo.commit("revalidate a", {A: guide(at=T2, because="nothing it rests on changed")})
    assert _altered(repo) == []


def test_altered_lists_added_removed_and_changed_with_the_rules_at_each_state(
    repo: AdopterRepo,
) -> None:
    _start(repo)
    repo.commit(
        "change",
        {
            f"{GUIDES}/c.md": page("C", body="A new body."),
            f"{GUIDES}/old.md": None,
            f"{GUIDES}/new.md": page(
                "New", body="A new guide on another subject: nothing in it is the old one."
            ),
        },
    )
    repo.write({f"{SETS}/doc.md": rule_set_text(rule_set("DOC", scope=scoped(f"{GUIDES}/**")))})
    assert _altered(repo) == [
        ("changed", f"{GUIDES}/c.md", f"{GUIDES}/c.md"),
        ("added", None, f"{GUIDES}/new.md"),
        ("removed", f"{GUIDES}/old.md", None),
    ]
    document = reading.altered_document(repo.root, "main")
    changed, added, removed = document["artefacts"]
    assert [r["rule"] for r in changed["base"]["rules"]] == ["RS-CMN-001", "RS-DOC-001"]
    assert [r["rule"] for r in changed["head"]["rules"]] == ["RS-DOC-001"]  # head: no CMN
    assert [r["rule"] for r in added["head"]["rules"]] == ["RS-DOC-001"]
    # ruled only at the base, and removed at the head
    assert [r["rule"] for r in removed["base"]["rules"]] == ["RS-CMN-001", "RS-DOC-001"]
    assert removed["head"] is None
    assert document["head"]["working_tree"] is True and document["base"]["ref"] == "main"


def test_altered_reads_a_named_head_and_the_cli_gives_the_document(repo: AdopterRepo) -> None:
    _start(repo)
    repo.commit("change c", {f"{GUIDES}/c.md": page("C", body="Another body.")})
    repo.write({f"{GUIDES}/b.md": page("B", body="Uncommitted.")})
    assert _altered(repo, named=fc.named_head(repo.root, "feature")) == [
        ("changed", f"{GUIDES}/c.md", f"{GUIDES}/c.md")
    ]
    result = _cli("altered", "--base", "main", "--json")
    assert result.exit_code == 0, result.output
    document = json.loads(result.stdout)
    assert document["schema_version"] == 1
    assert [e["head"]["location"] for e in document["artefacts"]] == [
        f"{GUIDES}/b.md",
        f"{GUIDES}/c.md",
    ]
    named = json.loads(_cli("altered", "--base", "main", "--head", "feature", "--json").stdout)
    assert named["head"]["working_tree"] is False and len(named["artefacts"]) == 1
    human = _cli("altered", "--base", "main")
    assert human.exit_code == 0 and f"changed   {GUIDES}/c.md" in human.output


def test_the_change_check_and_the_command_share_one_pairing(
    repo: AdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One function pairs and compares for both (ADR-057 point 2), and the change check's
    answer on a move is what it was: the move needs a revalidation."""
    _start(repo)
    repo.rename(A, f"{GUIDES}/moved/a.md")
    calls: list[str] = []
    pair = fc.pair_artefacts

    def spy(base: fd.Discovery, head: fd.Discovery, diff: fc.Diff) -> fc.Pairing:
        calls.append("pair")
        return pair(base, head, diff)

    monkeypatch.setattr(fc, "pair_artefacts", spy)
    check = fc.run_change_check(repo.root, "main")
    assert [(f.kind.value, f.location) for f in check.findings] == [
        ("friction", f"{GUIDES}/moved/a.md")
    ]
    assert _altered(repo) == []
    assert calls == ["pair", "pair"]


# --- what a change brings under a rule (COR-057 point 2, #1560) ----------------------------


def _brought(repo: AdopterRepo, **kwargs: Any) -> list[tuple[str, list[str]]]:
    """Each artefact the change brought under a rule without altering it, with the rules
    it brought it under."""
    document = reading.altered_document(repo.root, "main", **kwargs)
    assert all(e["change"] == "unaltered" for e in document["brought_unaltered"])
    return [(e["head"]["location"], e["brought_under"]) for e in document["brought_unaltered"]]


def _narrow_start(repo: AdopterRepo, **sets: Mapping[str, Any]) -> None:
    """The base on `main`: guides `a` and `new/b` and the sets given; then branch
    `feature`."""
    lay_out(repo, sets, a=page(), new__b=page("B"))
    repo.commit("base", files=None)
    repo.checkout("feature", create=True)


def _set(repo: AdopterRepo, key: str, front: Mapping[str, Any]) -> None:
    repo.write({f"{SETS}/{key}.md": rule_set_text(front)})


def test_widening_a_scope_brings_unaltered_artefacts_under_its_rules(repo: AdopterRepo) -> None:
    """The first of the four (#1560): a set's scope widens over a page the change does not
    edit. The `artefacts` list does not take it in, so its meaning holds."""
    _narrow_start(repo, doc=rule_set("DOC", scope=scoped(f"{GUIDES}/new/**")))
    _set(repo, "doc", rule_set("DOC", scope=scoped(f"{GUIDES}/**")))
    assert _brought(repo) == [(A, ["RS-DOC-001"])]
    assert _altered(repo) == []  # the rules are out of every scope, so nothing is altered


def test_accepting_a_rule_brings_the_artefacts_it_binds_on_under_it(repo: AdopterRepo) -> None:
    """The second: a proposed rule binds nothing, so accepting it brings each artefact in
    its set's scope under it, and under it alone."""
    proposed = {**rules("RS-DOC-001"), "RS-DOC-002": {}}
    _narrow_start(repo, doc=rule_set("DOC", scope=scoped(f"{GUIDES}/**"), entries=proposed))
    accepted = rules("RS-DOC-001", "RS-DOC-002")
    _set(repo, "doc", rule_set("DOC", scope=scoped(f"{GUIDES}/**"), entries=accepted))
    assert _brought(repo) == [(A, ["RS-DOC-002"]), (f"{GUIDES}/new/b.md", ["RS-DOC-002"])]


def test_updating_a_pin_brings_the_rules_it_held_back_under_it(repo: AdopterRepo) -> None:
    """The third: a rule a pin behind its set held back bound nothing at the base, so the
    pin raised to reach it brings the artefacts under it."""
    _narrow_start(
        repo,
        cmn=rule_set("CMN", "2.0.0"),
        doc=rule_set("DOC", inherits=["CMN@1"], scope=scoped(f"{GUIDES}/new/**")),
    )
    _set(repo, "doc", rule_set("DOC", inherits=["CMN@2"], scope=scoped(f"{GUIDES}/new/**")))
    assert _brought(repo) == [(f"{GUIDES}/new/b.md", ["RS-CMN-001"])]


def test_typing_a_place_brings_its_artefacts_under_a_set_that_selects_the_type(
    repo: AdopterRepo,
) -> None:
    """The fourth: a type is no part of content, so typing a place alters nothing, yet a
    set whose scope selects the type reaches the place's artefacts (COR-056 point 5)."""
    _narrow_start(repo, doc=rule_set("DOC", scope={"types": ["guide"]}))
    typed: Any = {"path": GUIDES, "type": "guide"}
    repo.write({CONFIG: friction_config(places=(typed,))})
    assert _altered(repo) == []
    assert _brought(repo) == [(A, ["RS-DOC-001"]), (f"{GUIDES}/new/b.md", ["RS-DOC-001"])]


def test_a_move_into_a_set_s_paths_brings_the_artefact_under_its_rules(
    repo: AdopterRepo,
) -> None:
    """A move the pairing follows, keeping the content, alters nothing, yet the scope that
    selects its new path brings it under that set's rules."""
    _narrow_start(repo, new=rule_set("NEW", scope=scoped(f"{GUIDES}/new/**")))
    repo.rename(A, f"{GUIDES}/new/a.md")
    assert _altered(repo) == []
    assert _brought(repo) == [(f"{GUIDES}/new/a.md", ["RS-NEW-001"])]


def test_each_altered_artefact_carries_the_rules_the_change_brings_it_under(
    repo: AdopterRepo,
) -> None:
    """A changed artefact is brought under a rule that binds on it at the head only, an
    added one under every rule that binds on it, a removed one under none. An artefact the
    change alters is never listed apart as well."""
    _narrow_start(
        repo,
        doc=rule_set("DOC", scope=scoped(f"{GUIDES}/**")),
        new=rule_set("NEW", scope=scoped(f"{GUIDES}/new/**")),
    )
    _set(repo, "new", rule_set("NEW", scope=scoped(f"{GUIDES}/**")))
    repo.write(
        {
            A: page(body="A changed body."),
            f"{GUIDES}/new/b.md": None,
            f"{GUIDES}/c.md": page("C", body="A guide the change adds, on its own subject."),
        }
    )
    document = reading.altered_document(repo.root, "main")
    assert [(e["change"], e["brought_under"]) for e in document["artefacts"]] == [
        ("changed", ["RS-NEW-001"]),
        ("added", ["RS-DOC-001", "RS-NEW-001"]),
        ("removed", []),
    ]
    assert document["brought_unaltered"] == []


def test_narrowing_a_scope_or_leaving_a_file_out_brings_nothing_under_a_rule(
    repo: AdopterRepo,
) -> None:
    """Taking artefacts out from under a rule lists nothing, and a file the widened scope
    leaves out with `exclude` is not brought under it (COR-051 point 2)."""
    _narrow_start(repo, doc=rule_set("DOC", scope=scoped(f"{GUIDES}/new/**")))
    _set(repo, "doc", rule_set("DOC", scope=scoped(f"{GUIDES}/none/**")))
    assert _brought(repo) == [] and _altered(repo) == []
    _set(
        repo,
        "doc",
        rule_set("DOC", scope={"paths": [f"{GUIDES}/**"], "exclude": [f"{GUIDES}/a.md"]}),
    )
    assert _brought(repo) == []  # new/b is in scope at both states, a at neither


def test_a_rule_that_binds_at_both_states_brings_nothing_under_it(repo: AdopterRepo) -> None:
    """A set's change that leaves where its rule binds as it was brings nothing under it."""
    _narrow_start(repo, doc=rule_set("DOC", scope=scoped(f"{GUIDES}/**")))
    _set(repo, "doc", rule_set("DOC", "1.1.0", scope=scoped(f"{GUIDES}/**")))
    assert _brought(repo) == []


def test_the_cli_gives_what_a_change_brings_under_a_rule(repo: AdopterRepo) -> None:
    _narrow_start(repo, doc=rule_set("DOC", scope=scoped(f"{GUIDES}/new/**")))
    _set(repo, "doc", rule_set("DOC", scope=scoped(f"{GUIDES}/**")))
    result = _cli("altered", "--base", "main", "--json")
    assert result.exit_code == 0, result.output
    document = json.loads(result.stdout)
    assert document["schema_version"] == 1 and document["artefacts"] == []
    (entry,) = document["brought_unaltered"]
    assert entry["change"] == "unaltered" and entry["brought_under"] == ["RS-DOC-001"]
    assert entry["base"]["location"] == entry["head"]["location"] == A
    assert entry["base"]["rules"] == []
    assert [r["rule"] for r in entry["head"]["rules"]] == ["RS-DOC-001"]
    human = _cli("altered", "--base", "main")
    assert human.exit_code == 0, human.output
    assert "Brought under a rule, unaltered:" in human.output
    assert f"unaltered {A}" in human.output and "brought under: RS-DOC-001" in human.output
    assert "0 artefact(s) altered, 0 with a binding rule; 1 brought under a rule unaltered." in (
        human.output
    )
