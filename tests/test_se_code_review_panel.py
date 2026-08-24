"""Integration test — the software-engineering code-review panel resolves through
the pm required-reviewer resolver (per [software-engineering:DEC-002-code-review-panel]).

DEC-002 ships a three-agent code-review panel — `code-reviewer`,
`security-reviewer`, `docs-reviewer` — registered through the reviewer-contribution
socket ([project-management:DEC-032]) so it folds through the existing merge gate.
The panel's activation is declared in the capability's real
`review-contributions.yaml`. This test wires that *actual shipped declaration*
through the pm resolver (`resolve_required_local_reviewers`, #732) and asserts the
panel activates as DEC-002 specifies:

  * a code-carrying PR pulls in `code-reviewer` + `security-reviewer` via the
    `touches-code` diff floor (independent of classification — the #715
    gate-escape backstop), plus `docs-reviewer` via the `type:*` wildcard when
    the PR closes a classified issue;
  * a docs-only PR pulls in only `docs-reviewer` (the floor reviewers stay out —
    a docs-only diff does not touch code).

The declaration is parsed with pm's own `parse_contributions` validator (the
same code the collector runs), so a malformed shipped file fails this test
loudly. The `gh`-backed fetchers are injected — pure-logic, no live repo.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PM_SCRIPTS_DIR = (
    REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
)
RR_PATH = PM_SCRIPTS_DIR / "_lib" / "required_reviewers.py"
RC_PATH = PM_SCRIPTS_DIR / "_lib" / "review_contributions.py"
CC_PATH = PM_SCRIPTS_DIR / "_lib" / "contribution_collector.py"

DECLARATION_PATH = (
    REPO_ROOT
    / ".pkit"
    / "capabilities"
    / "software-engineering"
    / "review-contributions.yaml"
)


def _load(module_name: str, path: Path):
    """Spec-load a pm `_lib` module with the scripts dir on sys.path.

    Mirrors the loader in test_pm_required_reviewers_lib.py so the module's own
    `from _lib.* import ...` resolves as it does at runtime.
    """
    scripts_dir_str = str(PM_SCRIPTS_DIR)
    inserted = scripts_dir_str not in sys.path
    if inserted:
        sys.path.insert(0, scripts_dir_str)
    try:
        spec = importlib.util.spec_from_file_location(module_name, path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        if inserted and scripts_dir_str in sys.path:
            sys.path.remove(scripts_dir_str)


@pytest.fixture(scope="module")
def rr():
    return _load("se_panel_required_reviewers", RR_PATH)


@pytest.fixture(scope="module")
def rc():
    return _load("se_panel_review_contributions", RC_PATH)


@pytest.fixture(scope="module")
def cc():
    return _load("se_panel_contribution_collector", CC_PATH)


@pytest.fixture(scope="module")
def panel_collection(rc, cc):
    """The panel's ContributionCollection, built from the SHIPPED declaration.

    Loads the real `software-engineering/review-contributions.yaml`, validates
    it with pm's own `parse_contributions` (asserting no malformed-shape
    errors), and wraps the rules in a `ContributionCollection` — the structure
    the resolver consumes. Every reviewer is treated as deployed here (agent
    deployment is exercised by the deploy path, not this resolver test).
    """
    data = cc.default_load_yaml(DECLARATION_PATH)
    assert data is not None, f"missing declaration at {DECLARATION_PATH}"
    rules, errors = rc.parse_contributions(data, "software-engineering")
    assert errors == (), f"shipped declaration is malformed: {errors}"
    return rc.ContributionCollection(rules=rules)


def _resolve(rr, panel_collection, *, closing, labels=None, changed=None):
    """Drive resolve_required_local_reviewers against the panel collection.

    `closing` is the closing-issue-number list; `labels` maps issue number →
    label-name list; `changed` is the PR's changed-file path list the floor
    sees. The collection is injected (the shipped panel), and the `gh` fetchers
    are stubbed — pure-logic, no live repo.
    """
    labels = labels or {}
    changed = changed or []

    return rr.resolve_required_local_reviewers(
        99,
        baseline_local=["reviewer"],
        repo_root=REPO_ROOT,
        closing_issue_numbers=lambda _pr: list(closing),
        issue_labels=lambda n: [{"name": x} for x in labels.get(n, [])],
        changed_files=lambda _pr: list(changed),
        collect_contributions=lambda _root: panel_collection,
    )


# ---- the shipped declaration's shape ---------------------------------------


def test_declaration_registers_the_three_panel_reviewers(panel_collection):
    """The shipped declaration parses to exactly the three panel reviewers."""
    reviewers = {rule.reviewer for rule in panel_collection.rules}
    assert reviewers == {"code-reviewer", "security-reviewer", "docs-reviewer"}


def test_floor_reviewers_ride_touches_code(panel_collection, rc):
    """code-reviewer + security-reviewer are registered on the touches-code floor."""
    floor_reviewers = {
        rule.reviewer
        for rule in panel_collection.rules
        if rule.floor == rc.FLOOR_TOUCHES_CODE
    }
    assert floor_reviewers == {"code-reviewer", "security-reviewer"}


def test_docs_reviewer_rides_the_type_wildcard(panel_collection, rc):
    """docs-reviewer matches every `type` value via the wildcard (no floor)."""
    docs_rules = [r for r in panel_collection.rules if r.reviewer == "docs-reviewer"]
    assert len(docs_rules) == 1
    docs_rule = docs_rules[0]
    assert docs_rule.floor is None
    assert docs_rule.predicate.get("type") is rc.MATCH_ANY


# ---- code-carrying PR: the floor activates the panel ------------------------


def test_code_pr_pulls_in_code_and_security_via_floor(rr, panel_collection):
    """A code-carrying PR resolves the floor reviewers into the required set.

    The closing issue is `type:feature`, so `docs-reviewer` also joins via the
    `type:*` wildcard — a feature PR gets the full panel.
    """
    res = _resolve(
        rr, panel_collection,
        closing=[42],
        labels={42: ["type:feature", "priority:High"]},
        changed=["src/app.py", "README.md"],
    )
    assert res.ok
    assert set(res.required_local) == {
        "reviewer", "code-reviewer", "security-reviewer", "docs-reviewer",
    }
    assert res.contributed_by == {
        "code-reviewer": "software-engineering",
        "security-reviewer": "software-engineering",
        "docs-reviewer": "software-engineering",
    }


def test_code_pr_floor_fires_for_docs_typed_issue(rr, panel_collection):
    """The #715 gate-escape backstop: a code diff on a `type:docs` issue still
    pulls in the floor reviewers (code + security), plus docs via the wildcard."""
    res = _resolve(
        rr, panel_collection,
        closing=[7],
        labels={7: ["type:docs"]},
        changed=["scripts/deploy.sh"],
    )
    assert res.ok
    assert "code-reviewer" in res.required_local
    assert "security-reviewer" in res.required_local
    # docs-reviewer via the type:* wildcard (the issue carries a type axis).
    assert "docs-reviewer" in res.required_local


def test_code_pr_unclassified_still_gets_floor_reviewers(rr, panel_collection):
    """A code diff on an unclassified PR (closes nothing) still gets the floor
    reviewers; docs-reviewer stays out (no type axis to match the wildcard)."""
    res = _resolve(
        rr, panel_collection,
        closing=[],
        changed=["lib/core.py"],
    )
    assert res.ok
    assert set(res.required_local) == {
        "reviewer", "code-reviewer", "security-reviewer",
    }


# ---- docs-only PR: only docs-reviewer activates ----------------------------


def test_docs_only_pr_resolves_docs_reviewer_only(rr, panel_collection):
    """A docs-only PR pulls in docs-reviewer (type:* wildcard) but NOT the floor
    reviewers — a docs-only diff does not touch code."""
    res = _resolve(
        rr, panel_collection,
        closing=[13],
        labels={13: ["type:docs"]},
        changed=["README.md", "docs/guide.rst", "docs/img/diagram.png"],
    )
    assert res.ok
    assert set(res.required_local) == {"reviewer", "docs-reviewer"}
    assert "code-reviewer" not in res.required_local
    assert "security-reviewer" not in res.required_local
