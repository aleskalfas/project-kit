"""The documents the backbone prints of its components hold their contracts (ADR-097
point 7): a capability shown, its install and uninstall planned, the project rule set it
declares, the rules of an agent's run and how the run ended, how each adapter's harness
meets the core's requirements, and the release the pending changesets compute.

Each command runs once in a project of the test's own. What that run does not reach is
built by the function the command prints through, from a result holding it.
`tests/test_backbone_documents.py` gathers the contracts here into its ratchet.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping
from enum import Enum
from pathlib import Path
from typing import Any

import pytest

from project_kit import agent_confinement as confinement
from project_kit import agent_runs, run_rules
from project_kit import capability_plans as plans
from project_kit import connections as cx
from project_kit import declared_rule_sets as drs
from project_kit import harness_support as hs
from project_kit.default_branch import CHECK_BASE_ENV
from project_kit.manifest import (
    ORIGIN_EXTERNALLY_SOURCED,
    ORIGIN_INCUBATED_IN_REPO,
    ORIGIN_KIT_SHIPPED,
)
from tests.adopter_repo import GitRepo, MakeAdopterRepo
from tests.backbone_documents import JSON_OPTION, document_of, invoke
from tests.document_contracts import Contract, Form, check

PLAN_OPTION = "--plan"
_ORIGINS = (ORIGIN_KIT_SHIPPED, ORIGIN_INCUBATED_IN_REPO, ORIGIN_EXTERNALLY_SOURCED)


def _values(enumeration: type[Enum]) -> tuple[str, ...]:
    """The values of an `Enum` class, as a document prints them."""
    return tuple(str(member.value) for member in enumeration)


# --- `pkit capabilities show --json` ---------------------------------------------------------

#: A point a capability defines, as its view shows it.
POINT = Form(
    keys={
        "address": "str",
        "kind": "str",
        "schema_version": "int",
        "description": "str|null",
        "policy": "str|null",
        "mandatory": "str|null",
        "process": "str|null",
        "question": "str|null",
    }
)

CAPABILITIES_SHOW = Contract(
    name="pkit capabilities show --json",
    forms={
        "view": Form(
            keys={
                "name": "str",
                "version": "str|null",
                "description": "str",
                "origin": "str",
                "installed": "bool",
                "roles": "list",
                "roles[]": "object",
                "roles[].role": "str",
                "roles[].state": "str",
                "roles[].providers": "list",
                "roles[].providers[]": "str",
                "roles[].active": "str|null",
                "accepts": "list",
                "accepts[]": "object",
                "offers": "list",
                "offers[]": "object",
                "extensions": "list",
                "extensions[]": "object",
                "extensions[].kind": "str",
                "extensions[].target": "str",
                "extensions[].schema_version": "int|null",
                "extensions[].command": "str|null",
                "extensions[].mandatory": "str|null",
                "extensions[].description": "str|null",
                "connections": "list",
                "connections[]": "object",
                "connections[].direction": "str",
                "connections[].capability": "str",
                "connections[].kind": "str",
                "connections[].target": "str",
                "connections[].status": "str",
                "connections[].provider": "str|null",
                "loaded_rules": "object|null",
                "loaded_rules.citation": "str",
                "loaded_rules.version": "str|null",
                "loaded_rules.rules": "list",
                "loaded_rules.rules[]": "object",
                "loaded_rules.rules[].id": "str",
                "loaded_rules.rules[].title": "str",
            }
        )
    },
    shapes={"point": POINT},
    refs={"accepts[]": "point", "offers[]": "point"},
    sets={
        "origin": frozenset(_ORIGINS),
        "point:kind": frozenset({"data", "process", "event"}),
        "point:policy": frozenset({"single", "union", "additive"}),
        "extensions[].kind": frozenset({"contributes", "subscribes", "depends-on"}),
        "connections[].direction": frozenset({"in", "out"}),
        "connections[].kind": frozenset({"contributes", "subscribes", "depends-on"}),
        "connections[].status": frozenset(_values(cx.BindingStatus)),
    },
)

_SHOW_ENUMERATIONS = {
    "origin": _ORIGINS,
    "point:kind": _values(cx.PointKind),
    "point:policy": cx.COMBINATIONS,
    "extensions[].kind": _values(cx.CounterpartKind),
    "connections[].kind": _values(cx.CounterpartKind),
    "connections[].status": _values(cx.BindingStatus),
}


def _view(origin: str, *, rules: bool) -> plans.CapabilityView:
    """A view holding each part a capability may show, its loaded rules when `rules`."""
    point = plans.PointView("pkit::docs:readers", "data", 1, "Who reads.", "union", "a need", None)
    offered = plans.PointView("pkit::docs:review", "process", 2, None, None, None, "review")
    extension = plans.ExtensionView("contributes", "pkit::docs:readers", 1, "readers", "x", "Hi.")
    bare = plans.ExtensionView("depends-on", "other:process", None, None, None, None)
    loaded = plans.LoadedSetView("docs:DOCS", None, (plans.RuleView("RS-DOCS-001", "A rule."),))
    return plans.CapabilityView(
        name="docs",
        version=None,
        description="Documentation.",
        origin=origin,
        installed=origin != ORIGIN_KIT_SHIPPED,
        roles=(
            plans.RoleView("pkit::docs", "docs (selected)", ("docs", "other"), "docs"),
            plans.RoleView("pkit::other", "no provider", (), None),
        ),
        accepts=(point,),
        offers=(offered,),
        extensions=(extension, bare),
        connections=(
            plans.ConnectionView("out", "docs", "contributes", "pkit::x:y", "bound", "x"),
            plans.ConnectionView(
                "in", "other", "subscribes", "pkit::docs:e", "no such point", None
            ),
        ),
        loaded_rules=loaded if rules else None,
    )


def test_the_capability_view_holds_its_contract(make_adopter_repo: MakeAdopterRepo) -> None:
    make_adopter_repo(capabilities=("project-management",))
    shown = [
        document_of(invoke("capabilities", "show", name, JSON_OPTION))
        for name in ("project-management", "software-analysis")
    ]
    built = [
        json.loads(plans.to_json(_view(origin, rules=index % 2 == 0)))
        for index, origin in enumerate(_ORIGINS)
    ]
    check(CAPABILITIES_SHOW, {"view": [*shown, *built]}, enumerations=_SHOW_ENUMERATIONS)


# --- `pkit capabilities install --plan --json` and `uninstall --plan --json` ----------------

#: Who answers a role in one wiring.
ROLE_STATE = Form(
    keys={
        "providers": "list",
        "providers[]": "str",
        "selected": "str|null",
        "active": "str|null",
        "conflict": "bool",
    }
)

#: A point a plan defines or undefines.
POINT_REF = Form(keys={"address": "str", "kind": "str", "version": "int", "provider": "str"})

#: How one counterpart's binding changes.
CONNECTION_CHANGE = Form(
    keys={
        "capability": "str",
        "kind": "str",
        "target": "str",
        "pointer": "str",
        "before": "str|null",
        "after": "str|null",
        "provider_before": "str|null",
        "provider_after": "str|null",
    }
)

#: A wiring finding a plan names.
FINDING = Form(
    keys={
        "file": "str",
        "path": "str",
        "severity": "str",
        "message": "str",
        "relation": "str|null",
    }
)

#: A role block of an artefact whose standing a plan changes.
ROLE_BLOCK = Form(keys={"artefact": "str", "key": "str", "change": "str"})

#: How the wiring changes.
DIFF = Form(
    keys={
        "roles": "list",
        "roles[]": "object",
        "roles[].role": "str",
        "roles[].before": "object|null",
        "roles[].after": "object|null",
        "points_defined": "list",
        "points_defined[]": "object",
        "points_undefined": "list",
        "points_undefined[]": "object",
        "connections": "list",
        "connections[]": "object",
        "findings_added": "list",
        "findings_added[]": "object",
        "findings_resolved": "list",
        "findings_resolved[]": "object",
    }
)

_PLAN_SHAPES = {
    "diff": DIFF,
    "role state": ROLE_STATE,
    "point ref": POINT_REF,
    "connection change": CONNECTION_CHANGE,
    "finding": FINDING,
    "role block": ROLE_BLOCK,
}
_PLAN_REFS = {
    "diff": "diff",
    "diff:roles[].before": "role state",
    "diff:roles[].after": "role state",
    "diff:points_defined[]": "point ref",
    "diff:points_undefined[]": "point ref",
    "diff:connections[]": "connection change",
    "diff:findings_added[]": "finding",
    "diff:findings_resolved[]": "finding",
    "role_blocks[]": "role block",
}
#: Each version relation a plan's finding may name: the rule-set pin is never one.
_RELATIONS = tuple(
    relation.value for relation in cx.Relation if relation is not cx.Relation.RULE_SET_PIN
)
_PLAN_SETS = {
    "origin": frozenset(_ORIGINS),
    "point ref:kind": frozenset({"data", "process", "event"}),
    "connection change:kind": frozenset({"contributes", "subscribes", "depends-on"}),
    "connection change:before": frozenset(_values(cx.BindingStatus)),
    "connection change:after": frozenset(_values(cx.BindingStatus)),
    "finding:severity": frozenset({"error", "warning"}),
    "finding:relation": frozenset(_RELATIONS),
    "role block:change": frozenset({"orphaned", "adopted", "ambiguous"}),
}
_PLAN_KEYS = {
    "operation": "str",
    "capability": "str",
    "version": "str|null",
    "origin": "str",
    "diff": "object",
    "role_blocks": "list",
    "role_blocks[]": "object",
}

CAPABILITIES_INSTALL = Contract(
    name="pkit capabilities install --plan --json",
    forms={
        "plan": Form(
            keys={
                **_PLAN_KEYS,
                "conflicts": "list",
                "conflicts[]": "object",
                "conflicts[].role": "str",
                "conflicts[].providers": "list",
                "conflicts[].providers[]": "str",
                "conflicts[].resolve": "list",
                "conflicts[].resolve[]": "str",
                "needs": "list",
                "needs[]": "object",
                "type_names": "list",
                "type_names[]": "object",
                "type_names[].type": "str",
                "type_names[].places": "list",
                "type_names[].places[]": "str",
            }
        )
    },
    shapes=_PLAN_SHAPES,
    refs={**_PLAN_REFS, "needs[]": "finding"},
    sets={**_PLAN_SETS, "operation": frozenset({plans.INSTALL})},
)

CAPABILITIES_UNINSTALL = Contract(
    name="pkit capabilities uninstall --plan --json",
    forms={
        "plan": Form(
            keys={
                **_PLAN_KEYS,
                "fillers_lost": "list",
                "fillers_lost[]": "object",
                "fillers_lost[].point": "str",
                "fillers_lost[].filler": "str",
                "fillers_lost[].source": "str",
                "fillers_lost[].point_after": "str",
                "left_without_provider": "list",
                "left_without_provider[]": "object",
                "selections": "list",
                "selections[]": "str",
            }
        )
    },
    shapes=_PLAN_SHAPES,
    refs={**_PLAN_REFS, "left_without_provider[]": "connection change"},
    sets={
        **_PLAN_SETS,
        "operation": frozenset({plans.UNINSTALL}),
        "fillers_lost[].source": frozenset({"contribution", "project filler"}),
        "fillers_lost[].point_after": frozenset(
            {plans.STAYS_FILLED, plans.LEFT_UNFILLED, plans.NO_LONGER_DEFINED}
        ),
    },
)

_PLAN_ENUMERATIONS = {
    "origin": _ORIGINS,
    "point ref:kind": _values(cx.PointKind),
    "connection change:kind": _values(cx.CounterpartKind),
    "connection change:before": _values(cx.BindingStatus),
    "connection change:after": _values(cx.BindingStatus),
    "role block:change": (plans.ORPHANED, plans.ADOPTED, plans.AMBIGUOUS),
}


def _change(kind: str, before: str | None, after: str | None) -> plans.ConnectionChange:
    provider = "docs" if after == "bound" else None
    return plans.ConnectionChange(
        "other", kind, "pkit::docs:readers", "/c/0", before, after, None, provider
    )


def _diff() -> plans.WiringDiff:
    """A change of each part of the wiring: a role gained and one lost, a point of each
    kind defined and undefined, connections that come, change and go, and findings of
    each severity and each relation, added and resolved."""
    state = plans.RoleState(("docs",), None, "docs", False)
    torn = plans.RoleState(("docs", "other"), "nobody", None, True)
    points = tuple(
        plans.PointRef(f"pkit::docs:{kind}", kind, 1, "docs") for kind in _values(cx.PointKind)
    )
    findings = tuple(
        plans.FindingRef("a.yaml", "/a", "error", "A finding.", relation)
        for relation in (*_RELATIONS, None)
    )
    return plans.WiringDiff(
        roles=(
            plans.RoleChange("pkit::docs", None, state),
            plans.RoleChange("pkit::other", torn, None),
        ),
        points_defined=points,
        points_undefined=points[:1],
        connections=(
            _change("contributes", None, "bound"),
            _change("subscribes", "bound", None),
            _change("depends-on", "no active provider", "inert (version)"),
        ),
        findings_added=findings,
        findings_resolved=(plans.FindingRef("b.yaml", "", "warning", "Gone.", None),),
    )


def _install_plan(origin: str) -> plans.InstallPlan:
    return plans.InstallPlan(
        capability="docs",
        version=None,
        origin=origin,
        diff=_diff(),
        conflicts=(
            plans.Conflict(
                "pkit::docs",
                ("docs", "other"),
                ("pkit connections providers set pkit::docs docs",),
            ),
        ),
        needs=(plans.FindingRef("c.yaml", "/n", "error", "A need.", None),),
        role_blocks=(plans.RoleBlockChange("notes/a.md", "docs", plans.ORPHANED),),
        type_names=(plans.TypeNameTaken("docs:page", ("a.yaml:/types/0",)),),
    )


def _uninstall_plan(origin: str) -> plans.UninstallPlan:
    losses = tuple(
        plans.FillerLoss("pkit::docs:readers", "other", source, after)
        for source, after in (
            ("contribution", plans.STAYS_FILLED),
            ("project filler", plans.LEFT_UNFILLED),
            ("contribution", plans.NO_LONGER_DEFINED),
        )
    )
    return plans.UninstallPlan(
        capability="docs",
        version="0.2.0",
        origin=origin,
        diff=_diff(),
        fillers_lost=losses,
        left_without_provider=(_change("subscribes", "bound", "no active provider"),),
        role_blocks=(plans.RoleBlockChange("notes/a.md#7", "docs", plans.ADOPTED),),
        selections=("connections.providers.pkit::docs",),
    )


def test_the_install_and_uninstall_plans_hold_their_contracts(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    make_adopter_repo(capabilities=("project-management",))
    planned = document_of(
        invoke("capabilities", "install", "software-analysis", PLAN_OPTION, JSON_OPTION)
    )
    unplanned = document_of(
        invoke("capabilities", "uninstall", "project-management", PLAN_OPTION, JSON_OPTION)
    )
    check(
        CAPABILITIES_INSTALL,
        {"plan": [planned, *(json.loads(plans.to_json(_install_plan(o))) for o in _ORIGINS)]},
        enumerations=_PLAN_ENUMERATIONS,
    )
    check(
        CAPABILITIES_UNINSTALL,
        {"plan": [unplanned, *(json.loads(plans.to_json(_uninstall_plan(o))) for o in _ORIGINS)]},
        enumerations=_PLAN_ENUMERATIONS,
    )


# --- `pkit capabilities project-rule-set --json` ---------------------------------------------

PROJECT_RULE_SET = Contract(
    name="pkit capabilities project-rule-set --json",
    version=1,
    forms={
        "answer": Form(
            keys={
                "schema_version": "int",
                "capability": "str",
                "declared": "bool",
                "set": "object|null",
                "set.name": "str",
                "set.title": "str",
                "set.inherits": "str",
                "set.scope": "object",
                "set.scope.types": "list",
                "set.scope.types[]": "str",
                "path": "str|null",
                "pin": "str|null",
                "inherited_by": "list",
                "inherited_by[]": "str",
                "creates": "bool",
                "blocked": "str|null",
                "text": "str|null",
            }
        )
    },
)


def _inherited() -> drs.Plan:
    """A declared set the project's own sets already inherit, its major unread."""
    declaration = drs.Declaration("docs", "DOCS", "METHOD", ("docs:page",), "Docs rules")
    return drs.Plan(declaration, "rule-sets/docs.md", None, ("OWN",), "already chosen", None)


def test_the_project_rule_set_document_holds_its_contract(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    make_adopter_repo(capabilities=("project-management", "software-analysis"))
    answered = [
        document_of(invoke("capabilities", "project-rule-set", name, JSON_OPTION))
        for name in ("software-analysis", "project-management")
    ]
    built = json.loads(drs.to_json("docs", _inherited()))
    check(PROJECT_RULE_SET, {"answer": [*answered, built]})


# --- `pkit agents rules --json` ----------------------------------------------------------------


def _rule_keys(prefix: str) -> dict[str, str]:
    """A rule as the allow and deny lists give it: a tool, a tool on a folder, or a
    command's first words."""
    return {
        f"{prefix}": "list",
        f"{prefix}[]": "object",
        f"{prefix}[].tool": "str",
        f"{prefix}[].folder": "str",
        f"{prefix}[].command": "list",
        f"{prefix}[].command[]": "str",
    }


_HOW_HELD = ("allow list", "native deny", "allow list and native deny")

AGENTS_RULES = Contract(
    name="pkit agents rules --json",
    version=1,
    forms={
        "answer": Form(
            keys={
                "schema_version": "int",
                "rules_of": "str",
                "refused": "str|null",
                **_rule_keys("allow"),
                **_rule_keys("deny"),
                "held": "list",
                "held[]": "object",
                "held[].privilege": "str",
                "held[].how": "str",
                "forms": "list",
                "forms[]": "str",
                "excluded_candidates": "list",
                "excluded_candidates[]": "list",
                "excluded_candidates[][]": "str",
            }
        )
    },
    sets={"held[].how": frozenset(_HOW_HELD)},
)

_FIX_DRIFT = "project-management:fix-drift"


def _every_rule() -> run_rules.RunProjection:
    """A projection holding each form of rule, in both lists, and each way a deny is held."""
    rules = (
        {"tool": "Read"},
        {"tool": "Write", "folder": "{{pkit:workspace}}"},
        {"command": ["pkit", "status"]},
    )
    return run_rules.RunProjection(
        allow=rules,
        deny=rules,
        excluded_candidates=(("pkit", "status"),),
        forms=("Read", "pkit status"),
        held=tuple({"privilege": f"core:p{i}", "how": how} for i, how in enumerate(_HOW_HELD)),
    )


def test_the_run_rules_document_holds_its_contract(
    make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    make_adopter_repo(capabilities=("project-management",))
    projected = document_of(invoke("agents", "rules", _FIX_DRIFT, JSON_OPTION))
    refused = document_of(invoke("agents", "rules", "project-management:nothing", JSON_OPTION))
    assert projected["refused"] is None and refused["refused"], (projected, refused)
    monkeypatch.setattr(run_rules, "view", lambda *args: _every_rule())
    every = document_of(invoke("agents", "rules", _FIX_DRIFT, JSON_OPTION))
    check(AGENTS_RULES, {"answer": [projected, refused, every]})


# --- `pkit agents run --json` ------------------------------------------------------------------

AGENTS_RUN = Contract(
    name="pkit agents run --json",
    version=1,
    forms={
        "run": Form(
            keys={
                "schema_version": "int",
                "agent": "str",
                "runner": "str|null",
                "ending": "str",
                "exit_code": "int|null",
                "output": "str",
                "diagnostics": "str",
                "reason": "str",
                "refused_calls": "list",
                "refused_calls[]": "object",
                "refused_calls[].tool": "str",
                "refused_calls[].input": "str",
                "confined": "bool",
                "commit": "str|null",
                "check": "object|null",
                "check.verdict": "str",
                "check.changes": "list",
                "check.changes[]": "str",
                "files": "str|null",
                "excluded": "list",
                "excluded[]": "list",
                "excluded[][]": "str",
                "refusal_cause": "str|null",
            }
        )
    },
    sets={
        "ending": frozenset({"finished", "not-started", "timed-out", "refused", "no-answer"}),
        "check.verdict": frozenset({"clean", "breach", "not-run"}),
        "refusal_cause": frozenset({"run-folder"}),
    },
)


def _ended(ending: str, check: confinement.Check | None) -> agent_runs.AgentRun:
    """A confined run of `ending`, with all its parts."""
    return agent_runs.AgentRun(
        "critic",
        ending,
        runner="claude-code",
        exit_code=0 if ending == agent_runs.FINISHED else None,
        output="Done.",
        diagnostics="warned",
        reason="",
        refused_calls=({"tool": "Bash", "input": "rm -rf /"},),
        confined=True,
        commit="a" * 40,
        check=check,
        files=Path("out"),
        excluded=(("pkit", "status"),),
    )


def test_the_agent_run_document_holds_its_contract(
    make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = make_adopter_repo()
    monkeypatch.setenv(agent_runs.MARKER_ENV, "1")
    run = ("agents", "run", "critic", "--limit", "10", JSON_OPTION)
    unconfined = document_of(invoke(*run, "--folder", str(repo.root)))
    confined = document_of(
        invoke(*run, "--commit", "a" * 40, "--rules-of", _FIX_DRIFT, "--files-to", str(repo.root))
    )
    checks = (
        confinement.Check(confinement.CLEAN),
        confinement.Check(confinement.BREACH, ("a file changed",)),
        confinement.CHECK_NOT_RUN,
    )
    built = [
        json.loads(agent_runs.render_json(_ended(ending, checks[index % len(checks)])))
        for index, ending in enumerate(agent_runs.ENDINGS)
    ]
    check(
        AGENTS_RUN,
        {"run": [unconfined, confined, *built]},
        enumerations={
            "ending": agent_runs.ENDINGS,
            "check.verdict": (confinement.CLEAN, confinement.BREACH, confinement.NOT_RUN),
            "refusal_cause": (confinement.RUN_FOLDER,),
        },
    )


# --- `pkit harness report --json` --------------------------------------------------------------

_OBSERVATION_POINTS = ("out-of-session", "interposed-runtime", "in-session")

HARNESS_REPORT = Contract(
    name="pkit harness report --json",
    version=1,
    forms={
        "report": Form(
            keys={
                "schema_version": "int",
                "requirements": "list",
                "requirements[]": "str",
                "adapters": "list",
                "adapters[]": "object",
                "adapters[].adapter": "str",
                "adapters[].declaration": "str|null",
                "adapters[].requirements": "list",
                "adapters[].requirements[]": "object",
                "adapters[].requirements[].id": "str",
                "adapters[].requirements[].title": "str",
                "adapters[].requirements[].observation_point": "str",
                "adapters[].requirements[].result": "str",
                "adapters[].requirements[].grade": "str|null",
                "adapters[].requirements[].provenance": "str|null",
                "adapters[].requirements[].cost": "str|null",
                "adapters[].requirements[].harness_versions": "list|str|null",
                "adapters[].requirements[].harness_versions[]": "str",
                "adapters[].requirements[].reason": "str",
                "adapters[].unmet": "int",
                "unmet": "int",
            }
        )
    },
    sets={
        "adapters[].requirements[].observation_point": frozenset(_OBSERVATION_POINTS),
        "adapters[].requirements[].result": frozenset(
            {"satisfied", "unsatisfied", "indeterminate"}
        ),
        "adapters[].requirements[].grade": frozenset({"supported", "at-cost", "not-achievable"}),
        "adapters[].requirements[].provenance": frozenset({"computed"}),
    },
)

#: An adapter's answers to a requirement, each resolved another way.
_ANSWERS: tuple[Mapping[str, Any] | None, ...] = (
    None,
    {"grade": hs.SUPPORTED, "harness_versions": []},
    {"grade": hs.AT_COST, "cost": "a hook", "harness_versions": ["1.0", "2.0"]},
    {"grade": hs.NOT_ACHIEVABLE, "harness_versions": hs.UNBOUNDED},
    {"grade": hs.SUPPORTED, "harness_versions": hs.UNBOUNDED},
)


def _resolved() -> str:
    """Each answer resolved for a requirement of each observation point, for one adapter
    with a declaration and one without."""
    known = [
        hs.Requirement(f"r{i}", "A need.", point) for i, point in enumerate(_OBSERVATION_POINTS)
    ]
    results = tuple(
        hs.resolve(known[index % len(known)], answer) for index, answer in enumerate(_ANSWERS)
    )
    reports = [
        hs.AdapterReport("claude-code", "harness-support.yaml", results),
        hs.AdapterReport("other", None, (hs.resolve(known[0], None),)),
    ]
    return hs.render_json(reports, known)


def test_the_harness_report_holds_its_contract(make_adopter_repo: MakeAdopterRepo) -> None:
    make_adopter_repo()
    reported = document_of(invoke("harness", "report", JSON_OPTION))
    check(
        HARNESS_REPORT,
        {"report": [reported, json.loads(_resolved())]},
        enumerations={
            "adapters[].requirements[].result": (hs.SATISFIED, hs.UNSATISFIED, hs.INDETERMINATE),
            "adapters[].requirements[].grade": (hs.SUPPORTED, hs.AT_COST, hs.NOT_ACHIEVABLE),
        },
    )


# --- `pkit release plan --json` ----------------------------------------------------------------

_DECLARED_RANGE = {
    "from": "str",
    "to": "str",
    "raised": "bool",
    "declared": "str",
    "names_release": "bool",
    "lines": "list",
    "lines[]": "str",
    "changelog": "str|null",
}


def _under(prefix: str, keys: Mapping[str, str]) -> dict[str, str]:
    return {f"{prefix}.{key}": kind for key, kind in keys.items()}


#: What a release and its candidate both give.
_RELEASE_KEYS = {
    "empty": "bool",
    "backbone_version": "str|null",
    "changesets_consumed": "int",
    "migration_warnings": "list",
    "migration_warnings[]": "str",
    "releases": "list",
    "releases[]": "object",
    "releases[].component": "str",
    "releases[].old_version": "str",
    "releases[].new_version": "str",
    "releases[].segment": "str",
    "releases[].notes": "list",
    "releases[].notes[]": "str",
    "releases[].requires_capabilities_floors": "list",
    "releases[].requires_capabilities_bounds": "list",
    "releases[].requires_capabilities_bounds[]": "object",
    **_under(
        "releases[].requires_capabilities_bounds[]",
        {
            "capability": "str",
            "from": "str|null",
            "to": "str|null",
            "widened": "bool",
            "version": "str",
            "lines": "list",
            "lines[]": "str",
            "changelog": "str|null",
        },
    ),
}

#: The floors a release raises, which a candidate never does (PRJ-002 D4 and D5).
_FLOOR_KEYS = {
    "releases[].requires_backbone_floor": "object|null",
    **_under(
        "releases[].requires_backbone_floor",
        {**_DECLARED_RANGE, "backbone": "str", "backbone_moves": "bool"},
    ),
    "releases[].requires_capabilities_floors[]": "object",
    **_under(
        "releases[].requires_capabilities_floors[]",
        {**_DECLARED_RANGE, "capability": "str", "version": "str", "moves": "bool"},
    ),
}

RELEASE_PLAN = Contract(
    name="pkit release plan --json",
    forms={
        "plan": Form(keys={**_RELEASE_KEYS, **_FLOOR_KEYS}),
        "candidate": Form(
            keys={
                **_RELEASE_KEYS,
                "releases[].requires_backbone_floor": "null",
                "candidate": "object",
                "candidate.version": "str",
                "candidate.number": "int",
                "candidate.tag": "str",
                "base": "object",
            }
        ),
    },
    sets={"releases[].segment": frozenset({"major", "minor", "patch"})},
    # The base the cut records in the candidate's tree, as that file holds it: a file a
    # command writes, whose format is decided apart (ADR-097 point 1; ADR-092 point 9).
    payloads=frozenset({"base"}),
)

_NEEDS_PM = (
    '\nrequires_capabilities:\n  - name: project-management\n    version: ">=0.54.0,<1.0.0"\n'
)


def _package(name: str, version: str, extra: str = "") -> str:
    return (
        f"schema_version: 1\ncomponent:\n  kind: capability\n  name: {name}\n"
        f'  version: {version}\nrequires_backbone: ">=1.0.0,<2.0.0"\n{extra}'
    )


def _changeset(component: str, kind: str, *declared: str) -> str:
    return "\n".join([f"component: {component}", f"kind: {kind}", "body: A change.", *declared, ""])


@pytest.fixture
def source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> GitRepo:
    """The methodology's source repository, its `main` pushed to `origin`, run from its
    root: a backbone minor, a capability that needs the backbone the release ships, one
    that needs the project-management it writes, one that runs on it, and a migration
    folder at a version no tier is cut at."""
    monkeypatch.delenv(CHECK_BASE_ENV, raising=False)
    repo = GitRepo.init(tmp_path / "work")
    capabilities = ".pkit/capabilities"
    unreleased = ".changes/unreleased"
    repo.commit(
        "the source",
        {
            ".pkit/VERSION": "1.5.0\n",
            ".pkit/manifest.yaml": (
                "schema_version: 1\nbackbone_version: 1.5.0\ncompleted_version: 1.5.0\n"
            ),
            "src/project_kit/__init__.py": "",
            "CHANGELOG.md": "# Changelog\n\n## 1.5.0 — 2026-01-01\n\n### Added\n- A release.\n",
            f"{capabilities}/houseware/package.yaml": _package("houseware", "0.3.0"),
            f"{capabilities}/project-management/package.yaml": _package(
                "project-management", "0.54.0"
            ),
            f"{capabilities}/living-docs/package.yaml": _package("living-docs", "0.1.0", _NEEDS_PM),
            f"{capabilities}/software-engineering/package.yaml": _package(
                "software-engineering", "0.2.0", _NEEDS_PM
            ),
            f"{unreleased}/a.yaml": _changeset("backbone", "minor"),
            f"{unreleased}/b.yaml": _changeset("houseware", "major", "requires_backbone: release"),
            f"{unreleased}/c.yaml": _changeset("project-management", "minor"),
            f"{unreleased}/d.yaml": _changeset(
                "living-docs",
                "minor",
                "requires_capabilities:\n  project-management: release",
            ),
            f"{unreleased}/e.yaml": _changeset(
                "software-engineering",
                "patch",
                "runs_on_capabilities:\n  project-management: release",
            ),
        },
    )
    (repo.root / ".pkit" / "migrations" / "backbone" / "1.9.0").mkdir(parents=True)
    remote = tmp_path / "origin.git"
    subprocess.run(
        ["git", "init", "-q", "--bare", "--initial-branch=main", str(remote)],
        check=True,
        capture_output=True,
    )
    repo.git("remote", "add", "origin", str(remote))
    repo.git("push", "-q", "origin", "main")
    monkeypatch.chdir(repo.root)
    return repo


def test_the_release_plan_holds_its_contract(source: GitRepo) -> None:
    planned = document_of(invoke("release", "plan", JSON_OPTION))
    candidate = document_of(invoke("release", "plan", "--pre", JSON_OPTION))
    nothing = source.root / ".changes" / "unreleased"
    for changeset in sorted(nothing.iterdir()):
        changeset.unlink()
    empty = document_of(invoke("release", "plan", JSON_OPTION))
    check(RELEASE_PLAN, {"plan": [planned, empty], "candidate": [candidate]})


#: The contracts of each component command, by the command's words.
CONTRACTS: Mapping[str, tuple[Contract, ...]] = {
    "capabilities show": (CAPABILITIES_SHOW,),
    "capabilities install": (CAPABILITIES_INSTALL,),
    "capabilities uninstall": (CAPABILITIES_UNINSTALL,),
    "capabilities project-rule-set": (PROJECT_RULE_SET,),
    "agents rules": (AGENTS_RULES,),
    "agents run": (AGENTS_RUN,),
    "harness report": (HARNESS_REPORT,),
    "release plan": (RELEASE_PLAN,),
}
