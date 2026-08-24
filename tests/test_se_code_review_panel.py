"""The software-engineering code-review panel: declaration + resolver unit tests,
plus one end-to-end collector pass (per [software-engineering:DEC-002-code-review-panel]).

DEC-002 ships a three-agent code-review panel — `code-reviewer`,
`security-reviewer`, `docs-reviewer` — registered through the reviewer-contribution
socket ([project-management:DEC-032]) so it folds through the existing merge gate.
The panel's activation is declared in the capability's real
`review-contributions.yaml`.

This module is two layers:

  * **Declaration + resolver unit tests (the bulk below).** They parse the
    *actual shipped declaration* with pm's own `parse_contributions` validator
    and wrap the rules in a `ContributionCollection` *directly*, then drive the
    resolver (`resolve_required_local_reviewers`, #732) with that injected
    collection and stubbed `gh` fetchers — pure-logic, no live repo and no
    manifest walk. A malformed shipped file fails these loudly. They assert the
    panel activates as DEC-002 specifies:
      - a code-carrying PR pulls in `code-reviewer` + `security-reviewer` via the
        `touches-code` diff floor (independent of classification — the #715
        gate-escape backstop), plus `docs-reviewer` (the floor + the `type:*`
        wildcard);
      - a docs-only PR pulls in only `docs-reviewer` via the wildcard (the code +
        security floor reviewers stay out — a docs-only diff does not touch code).

  * **End-to-end collector test (`test_collect_contributions_end_to_end_*`).** It
    builds a temp repo tree — a manifest registering `software-engineering`, the
    *shipped* `review-contributions.yaml` copied into place, and the three panel
    agents deployed — and drives the REAL `collect_contributions` (no injected
    collection) plus `resolve_required_local_reviewers` on top of it. This
    exercises the manifest-walk + per-declaration read + deployed-agent
    resolution the unit tests bypass, catching an orphan-safety or manifest-shape
    regression the direct-parse layer cannot see.
"""

from __future__ import annotations

import importlib.util
import shutil
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
    """All three panel reviewers are registered on the touches-code floor.

    code-reviewer + security-reviewer ride it as the correctness + security lens;
    docs-reviewer rides it too (G2) so a code PR always gets doc review, closing
    the doc-lens escape a mislabeled/unclassified code PR would otherwise use.
    """
    floor_reviewers = {
        rule.reviewer
        for rule in panel_collection.rules
        if rule.floor == rc.FLOOR_TOUCHES_CODE
    }
    assert floor_reviewers == {"code-reviewer", "security-reviewer", "docs-reviewer"}


def test_docs_reviewer_rides_floor_and_type_wildcard(panel_collection, rc):
    """docs-reviewer is registered by TWO rules: the touches-code floor (G2) and
    the `type:*` wildcard (a docs-only classified PR the floor does not require)."""
    docs_rules = [r for r in panel_collection.rules if r.reviewer == "docs-reviewer"]
    assert len(docs_rules) == 2
    floors = {r.floor for r in docs_rules}
    assert rc.FLOOR_TOUCHES_CODE in floors  # the G2 floor rule
    assert None in floors  # the wildcard match rule (no floor)
    match_rule = next(r for r in docs_rules if r.floor is None)
    assert match_rule.predicate.get("type") is rc.MATCH_ANY


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


def test_code_pr_unclassified_still_gets_all_floor_reviewers(rr, panel_collection):
    """A code diff on an unclassified PR (closes nothing) pulls in ALL THREE
    panel reviewers via the touches-code floor. docs-reviewer rides the floor too
    (G2), so the doc-lens does not escape on a mislabeled/unclassified code PR —
    the `type:*` wildcard finds no axis here, but the floor still requires it."""
    res = _resolve(
        rr, panel_collection,
        closing=[],
        changed=["lib/core.py"],
    )
    assert res.ok
    assert set(res.required_local) == {
        "reviewer", "code-reviewer", "security-reviewer", "docs-reviewer",
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


# ---- end-to-end: the REAL collector walks a temp manifest ------------------
#
# The tests above inject the ContributionCollection directly, bypassing the
# manifest walk + per-declaration read + deployed-agent resolution. The tests
# below build a temp repo tree and drive the REAL `collect_contributions`, so a
# regression in the manifest-shape reading, the orphan-safe walk, or the shipped
# declaration's file location is caught here (not just the direct-parse layer).


def _write_manifest(repo_root: Path, capability_names: list[str]) -> None:
    """Write a backbone manifest registering the given capabilities.

    Mirrors the builder in test_pm_review_contributions_lib.py — the same shape
    `list_registered_capabilities` reads. Includes a non-capability adapter
    component to prove kind-filtering ignores it.
    """
    lines = ["schema_version: 1", "backbone_version: 1.0.0", "components:"]
    lines += [
        "  - kind: adapter",
        "    name: claude-code",
        "    manifest: .pkit/adapters/claude-code/project/manifest.yaml",
    ]
    for name in capability_names:
        lines += [
            "  - kind: capability",
            f"    name: {name}",
            f"    manifest: .pkit/capabilities/{name}/manifest.yaml",
        ]
    (repo_root / ".pkit").mkdir(parents=True, exist_ok=True)
    (repo_root / ".pkit" / "manifest.yaml").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def _install_shipped_declaration(repo_root: Path) -> None:
    """Copy the SHIPPED review-contributions.yaml into the temp capability tree."""
    cap_dir = repo_root / ".pkit" / "capabilities" / "software-engineering"
    cap_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(DECLARATION_PATH, cap_dir / "review-contributions.yaml")


def _deploy_agent(repo_root: Path, name: str) -> None:
    agents_dir = repo_root / ".claude" / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    (agents_dir / f"{name}.md").write_text("# agent\n", encoding="utf-8")


def _install_panel(repo_root: Path) -> None:
    """Register software-engineering, install its shipped declaration, deploy agents."""
    _write_manifest(repo_root, ["software-engineering"])
    _install_shipped_declaration(repo_root)
    for name in ("code-reviewer", "security-reviewer", "docs-reviewer"):
        _deploy_agent(repo_root, name)


def test_collect_contributions_end_to_end_reads_shipped_panel(rr, tmp_path):
    """The REAL collector walks the manifest, reads the shipped declaration, and
    resolves the three deployed panel reviewers with no blocking errors."""
    _install_panel(tmp_path)

    # No injected collection here — the resolver's DEFAULT collector walks the
    # temp manifest and reads the copied-in declaration off disk.
    res = rr.resolve_required_local_reviewers(
        99,
        baseline_local=["reviewer"],
        repo_root=tmp_path,
        closing_issue_numbers=lambda _pr: [42],
        issue_labels=lambda _n: [{"name": "type:feature"}],
        changed_files=lambda _pr: ["src/app.py"],
    )
    assert res.ok, res.error
    assert set(res.required_local) == {
        "reviewer", "code-reviewer", "security-reviewer", "docs-reviewer",
    }
    assert res.contributed_by == {
        "code-reviewer": "software-engineering",
        "security-reviewer": "software-engineering",
        "docs-reviewer": "software-engineering",
    }


def test_collect_contributions_end_to_end_docs_only_pr(rr, tmp_path):
    """Through the real collector: a docs-only PR pulls in only docs-reviewer (the
    `type:*` wildcard) — the touches-code floor stays out (no code in the diff)."""
    _install_panel(tmp_path)

    res = rr.resolve_required_local_reviewers(
        99,
        baseline_local=["reviewer"],
        repo_root=tmp_path,
        closing_issue_numbers=lambda _pr: [13],
        issue_labels=lambda _n: [{"name": "type:docs"}],
        changed_files=lambda _pr: ["README.md", "docs/guide.rst"],
    )
    assert res.ok, res.error
    assert set(res.required_local) == {"reviewer", "docs-reviewer"}


def test_collect_contributions_end_to_end_undeployed_agent_fails_closed(rr, tmp_path):
    """If a panel agent is NOT deployed, the collector keeps the requirement
    VISIBLE and unsatisfiable — the resolver fails closed rather than dropping it.

    This exercises the deployed-agent resolution the direct-parse layer skips.
    """
    _write_manifest(tmp_path, ["software-engineering"])
    _install_shipped_declaration(tmp_path)
    # Deploy only two of the three — security-reviewer is missing.
    _deploy_agent(tmp_path, "code-reviewer")
    _deploy_agent(tmp_path, "docs-reviewer")

    res = rr.resolve_required_local_reviewers(
        99,
        baseline_local=["reviewer"],
        repo_root=tmp_path,
        closing_issue_numbers=lambda _pr: [42],
        issue_labels=lambda _n: [{"name": "type:feature"}],
        changed_files=lambda _pr: ["src/app.py"],
    )
    assert not res.ok
    assert res.error.kind == rr.ERROR_COLLECTION
