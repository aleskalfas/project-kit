"""Tests for the per-contribution opt-out (_lib/review_opt_outs.py, #148).

DEC-032 D5 activates a capability's reviewer contribution on install; the
opt-out lets an adopter withdraw one contribution — a `(capability, reviewer)`
pair — from `review.agents.contributed_opt_out` in their own pm config. This
covers the module on its own: the shape check (`parse_opt_outs` /
`read_opt_outs`), withdrawing the contribution from a collection (`apply`),
and the check that every entry names an installed contribution
(`problems_against`). The resolver and the consumers are covered in their own
test files.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import MappingProxyType

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = (
    REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
)
OO_PATH = SCRIPTS_DIR / "_lib" / "review_opt_outs.py"
RC_PATH = SCRIPTS_DIR / "_lib" / "review_contributions.py"


def _load(module_name: str, path: Path):
    inserted = str(SCRIPTS_DIR) not in sys.path
    if inserted:
        sys.path.insert(0, str(SCRIPTS_DIR))
    try:
        spec = importlib.util.spec_from_file_location(module_name, path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        if inserted and str(SCRIPTS_DIR) in sys.path:
            sys.path.remove(str(SCRIPTS_DIR))


@pytest.fixture(scope="module")
def oo():
    return _load("pm_review_opt_outs_under_test", OO_PATH)


@pytest.fixture(scope="module")
def rc():
    return _load("pm_rc_for_review_opt_outs", RC_PATH)


SE = "software-engineering"
REASON = "Docs are reviewed by the tech-writing team."


def _entry(capability=SE, reviewer="docs-reviewer", reason=REASON):
    return {"capability": capability, "reviewer": reviewer, "reason": reason}


def _rule(rc, capability, reviewer, *, floor=None, match=None, deployed=True):
    error = None if deployed else rc.ContributionError(
        rc.ERROR_UNDEPLOYED_AGENT, capability,
        f"capability `{capability}` contributes reviewer `{reviewer}` but no "
        "deployed agent file exists",
    )
    return rc.ContributionRule(
        capability=capability,
        predicate=MappingProxyType(match or {}),
        reviewer=reviewer,
        floor=floor,
        deployed=deployed,
        resolution_error=error,
    )


def _se_collection(rc, *, docs_deployed=True):
    """software-engineering's shipped contribution: three floor rules and a
    `type: *` match for docs-reviewer."""
    rules = (
        _rule(rc, SE, "code-reviewer", floor="touches-code"),
        _rule(rc, SE, "security-reviewer", floor="touches-code"),
        _rule(rc, SE, "docs-reviewer", floor="touches-code", deployed=docs_deployed),
        _rule(
            rc, SE, "docs-reviewer", match={"type": rc.MATCH_ANY},
            deployed=docs_deployed,
        ),
    )
    errors = tuple(r.resolution_error for r in rules if r.resolution_error)
    return rc.ContributionCollection(
        rules=rules,
        errors=errors,
        capabilities_walked=("project-management", SE),
    )


# ---- shape -------------------------------------------------------------


def test_absent_list_is_no_opt_outs(oo) -> None:
    parsed = oo.parse_opt_outs(None)
    assert parsed.ok
    assert parsed.entries == ()


def test_valid_list_parses_each_entry_with_its_position(oo) -> None:
    parsed = oo.parse_opt_outs([
        _entry(),
        _entry(capability="ux-ui-design", reviewer="design-reviewer", reason="No UI."),
    ])
    assert parsed.ok
    assert [(e.capability, e.reviewer, e.reason, e.index) for e in parsed.entries] == [
        (SE, "docs-reviewer", REASON, 0),
        ("ux-ui-design", "design-reviewer", "No UI.", 1),
    ]


def test_read_opt_outs_reads_the_review_agents_key(oo) -> None:
    config = {"review": {"agents": {
        "local_registered": [{"name": "pm-reviewer"}],
        "contributed_opt_out": [_entry()],
    }}}
    parsed = oo.read_opt_outs(config)
    assert parsed.ok
    assert [e.reviewer for e in parsed.entries] == ["docs-reviewer"]


@pytest.mark.parametrize("config", [
    {},
    {"review": None},
    {"review": {"mode": "agent"}},
    {"review": {"agents": {"local_registered": []}}},
    "not a mapping",
])
def test_read_opt_outs_absent_anywhere_is_none(oo, config) -> None:
    parsed = oo.read_opt_outs(config)
    assert parsed.ok and parsed.entries == ()


def test_not_a_list_is_an_error(oo) -> None:
    parsed = oo.parse_opt_outs({"capability": SE})
    assert not parsed.ok
    assert "must be a list" in parsed.errors[0]


@pytest.mark.parametrize("reason", [None, "", "   ", 3])
def test_reason_is_required(oo, reason) -> None:
    entry = _entry()
    if reason is None:
        del entry["reason"]
    else:
        entry["reason"] = reason
    parsed = oo.parse_opt_outs([entry])
    assert not parsed.ok
    assert parsed.entries == ()
    assert any("contributed_opt_out[0].reason" in e for e in parsed.errors)


@pytest.mark.parametrize("field", ["capability", "reviewer"])
def test_capability_and_reviewer_are_required(oo, field) -> None:
    entry = _entry()
    del entry[field]
    parsed = oo.parse_opt_outs([entry])
    assert not parsed.ok
    assert any(f"[0].{field}" in e for e in parsed.errors)


def test_unknown_key_is_an_error(oo) -> None:
    """An extra key (a scope the mechanism does not have) is refused, not
    ignored — ignoring it would withdraw more than the adopter wrote."""
    entry = {**_entry(), "workstream": "design"}
    parsed = oo.parse_opt_outs([entry])
    assert not parsed.ok
    assert any("unknown key `workstream`" in e for e in parsed.errors)


def test_entry_not_a_mapping_is_an_error(oo) -> None:
    parsed = oo.parse_opt_outs(["docs-reviewer"])
    assert not parsed.ok
    assert "must be a mapping" in parsed.errors[0]


def test_duplicate_pair_is_an_error(oo) -> None:
    parsed = oo.parse_opt_outs([_entry(), _entry(reason="Another reason.")])
    assert not parsed.ok
    assert any("repeats" in e and "[0]" in e for e in parsed.errors)


def test_one_bad_entry_voids_the_whole_list(oo) -> None:
    """A half-applied list is not what the adopter wrote: nothing applies."""
    parsed = oo.parse_opt_outs([_entry(), {"capability": SE}])
    assert not parsed.ok
    assert parsed.entries == ()


# ---- apply -------------------------------------------------------------


def test_apply_withdraws_every_rule_for_the_pair(oo, rc) -> None:
    """Both of docs-reviewer's rules (floor and match) leave; code-reviewer
    and security-reviewer stay."""
    applied = oo.parse_opt_outs([_entry()]).apply(_se_collection(rc))
    assert [r.reviewer for r in applied.rules] == ["code-reviewer", "security-reviewer"]
    assert applied.capabilities_walked == ("project-management", SE)


def test_apply_without_entries_is_identity(oo, rc) -> None:
    collection = _se_collection(rc)
    assert oo.NO_OPT_OUTS.apply(collection) is collection


def test_apply_keeps_the_same_reviewer_from_another_capability(oo, rc) -> None:
    """Withdrawing a pair never withdraws another capability's requirement
    for the same reviewer name."""
    collection = rc.ContributionCollection(rules=(
        _rule(rc, SE, "docs-reviewer", floor="touches-code"),
        _rule(rc, "tech-writing", "docs-reviewer", floor="touches-code"),
    ))
    applied = oo.parse_opt_outs([_entry()]).apply(collection)
    assert [(r.capability, r.reviewer) for r in applied.rules] == [
        ("tech-writing", "docs-reviewer"),
    ]


def test_apply_drops_the_undeployed_error_of_a_withdrawn_rule(oo, rc) -> None:
    """A requirement that no longer applies cannot make the gate unsatisfiable."""
    collection = _se_collection(rc, docs_deployed=False)
    assert not collection.ok
    applied = oo.parse_opt_outs([_entry()]).apply(collection)
    assert applied.ok


def test_apply_keeps_errors_of_rules_it_does_not_withdraw(oo, rc) -> None:
    collection = _se_collection(rc, docs_deployed=False)
    applied = oo.parse_opt_outs(
        [_entry(reviewer="code-reviewer")]
    ).apply(collection)
    assert not applied.ok
    assert all("docs-reviewer" in e.message for e in applied.errors)


# ---- problems against the installed contributions ---------------------


def test_every_entry_naming_a_contribution_has_no_problem(oo, rc) -> None:
    parsed = oo.parse_opt_outs([_entry(), _entry(reviewer="code-reviewer")])
    assert parsed.problems_against(_se_collection(rc)) == ()


def test_unknown_capability_is_a_problem(oo, rc) -> None:
    parsed = oo.parse_opt_outs([_entry(capability="ux-ui-design")])
    problems = parsed.problems_against(_se_collection(rc))
    assert len(problems) == 1
    entry, message = problems[0]
    assert entry.capability == "ux-ui-design"
    assert "contributed_opt_out[0]" in message
    assert "not an installed capability" in message


def test_installed_capability_without_contributions_is_a_problem(oo, rc) -> None:
    parsed = oo.parse_opt_outs([_entry(capability="project-management")])
    (_entry_, message), = parsed.problems_against(_se_collection(rc))
    assert "installed but contributes no reviewer requirement" in message


def test_unknown_reviewer_is_a_problem_naming_what_is_contributed(oo, rc) -> None:
    parsed = oo.parse_opt_outs([_entry(reviewer="docs-reviwer")])
    (_entry_, message), = parsed.problems_against(_se_collection(rc))
    assert "no reviewer `docs-reviwer`" in message
    assert "code-reviewer, docs-reviewer, security-reviewer" in message
