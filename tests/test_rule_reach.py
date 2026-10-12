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
    assert cmn["checks"][0] == {"check": "backbone:validate", "part": "The field resolves."}


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


def test_the_schema_refuses_a_check_part_without_its_part(repo: AdopterRepo) -> None:
    lay_out(
        repo,
        {"cmn": rule_set("CMN", checks={"RS-CMN-001": [{"check": "lint"}]})},
        a=page(),
    )
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
    assert {k: entry[k] for k in ("location", "kind", "span", "conflicts")} == {
        "location": A,
        "kind": "document",
        "span": None,
        "conflicts": [],
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
    assert human.exit_code == 0 and f"changed  {GUIDES}/c.md" in human.output


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
