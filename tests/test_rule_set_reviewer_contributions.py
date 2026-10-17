"""living-docs and software-analysis contribute the rule-set reviewer to the gate (#1420).

Each capability ships a `review-contributions.yaml` with one rule: the core
`rule-set-reviewer` (COR-057), under project-management's floor on ruled
artefacts ([project-management:DEC-032-conditional-reviewer-requirements] D1).
Each declares project-management as an optional dependency, from the release
that has the floor, so neither stops standing alone
([living-docs:DEC-001-living-docs-discipline] point 9,
[software-analysis:DEC-001-software-analysis-discipline] point 10). A branch
writes no floor above the project-management the tree carries (PRJ-002 D1), so
each capability's changeset declares the floor as `release`, and the release
that ships the floor raises the range to it (PRJ-002 D4).

The tests parse the SHIPPED declarations with pm's own validator, and drive the
REAL collector over a temporary tree that registers the capabilities, so the
manifest walk, the declarations' location and the deployed-agent check are
exercised as `review-pr` and `done-work` run them. The ruled-artefact reader is
injected: which artefacts a change alters is the backbone's answer, tested
with the floor itself (`test_pm_required_reviewers_lib.py`).
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from project_kit import release, versioning
from project_kit.connections import range_admits

REPO_ROOT = Path(__file__).resolve().parent.parent
CAPABILITIES = REPO_ROOT / ".pkit" / "capabilities"
PM_SCRIPTS_DIR = CAPABILITIES / "project-management" / "scripts"

CONTRIBUTORS = ("living-docs", "software-analysis")
REVIEWER = "rule-set-reviewer"
BASELINE = "pm-reviewer"

# A page and an analysis artefact an accepted rule binds on, as the backbone
# would list them. Either contributor covers both (COR-057 point 6).
RULED_PAGE = "docs/guides/a.md"
RULED_ACTOR = "tech-docs/analysis/use-case-model/actors/ACT-tester.md"

# project-management's last release without the floor.
PM_WITHOUT_THE_FLOOR = "0.54.0"
PM = "project-management"


def _load(module_name: str, path: Path):
    """Spec-load a pm `_lib` module with the scripts dir on sys.path, as
    `test_se_code_review_panel.py` does, so its `from _lib.* import` resolves."""
    scripts_dir = str(PM_SCRIPTS_DIR)
    inserted = scripts_dir not in sys.path
    if inserted:
        sys.path.insert(0, scripts_dir)
    try:
        spec = importlib.util.spec_from_file_location(module_name, path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        if inserted and scripts_dir in sys.path:
            sys.path.remove(scripts_dir)


@pytest.fixture(scope="module")
def rr():
    return _load(
        "rsr_contrib_required_reviewers", PM_SCRIPTS_DIR / "_lib" / "required_reviewers.py"
    )


@pytest.fixture(scope="module")
def rc():
    return _load(
        "rsr_contrib_review_contributions", PM_SCRIPTS_DIR / "_lib" / "review_contributions.py"
    )


@pytest.fixture(scope="module")
def cc():
    return _load(
        "rsr_contrib_contribution_collector", PM_SCRIPTS_DIR / "_lib" / "contribution_collector.py"
    )


@pytest.fixture(scope="module")
def oo():
    return _load("rsr_contrib_review_opt_outs", PM_SCRIPTS_DIR / "_lib" / "review_opt_outs.py")


def _declaration(capability: str) -> Path:
    return CAPABILITIES / capability / "review-contributions.yaml"


def _package(capability: str) -> dict:
    loaded = YAML(typ="safe").load((CAPABILITIES / capability / "package.yaml").read_text("utf-8"))
    assert isinstance(loaded, dict)
    return loaded


# ---- the shipped declarations ----------------------------------------------


@pytest.mark.parametrize("capability", CONTRIBUTORS)
def test_each_contributor_ships_one_rule_for_the_core_reviewer(capability, rc, cc) -> None:
    """One rule: the rule-set reviewer under the ruled-artefact floor, with no
    classification match, so a label never narrows it."""
    data = cc.default_load_yaml(_declaration(capability))
    assert data is not None, f"{capability} ships no review-contributions.yaml"
    rules, errors = rc.parse_contributions(data, capability)
    assert errors == (), f"{capability}'s declaration is malformed: {errors}"
    assert len(rules) == 1
    (rule,) = rules
    assert rule.reviewer == REVIEWER
    assert rule.floor == rc.FLOOR_TOUCHES_RULED_ARTEFACT
    assert not rule.predicate


def test_the_reviewer_is_the_core_agent_and_no_capability_ships_one() -> None:
    """Core ships it (COR-057 point 4), so a sync deploys it. A capability's
    agent of the same name would take its place at deploy."""
    assert (REPO_ROOT / ".pkit" / "agents" / "core" / f"{REVIEWER}.md").is_file()
    shadowing = sorted(str(p) for p in CAPABILITIES.glob(f"*/agents/**/{REVIEWER}.md"))
    assert shadowing == []


# ---- the optional dependency on project-management -------------------------


def _pm_dependency(capability: str) -> dict:
    entries = [
        entry
        for entry in _package(capability).get("requires_capabilities") or []
        if entry.get("name") == "project-management"
    ]
    assert len(entries) == 1, f"{capability} declares project-management {len(entries)} times"
    return entries[0]


@pytest.mark.parametrize("capability", CONTRIBUTORS)
def test_each_contributor_depends_on_pm_optionally(capability) -> None:
    """Optional, so the capability still installs and works without pm (COR-030)."""
    assert _pm_dependency(capability).get("optional") is True


@pytest.fixture(scope="module")
def next_release():
    """The next release over the tree as it stands: its pending changesets."""
    return release.compute_release(REPO_ROOT / ".pkit")


def _pm_range_after(plan, capability: str) -> str:
    """The capability's range on pm as `plan` leaves it: the tree's, its floor
    raised as `release apply` writes it where a pending changeset of the
    capability declares it."""
    text = (CAPABILITIES / capability / "package.yaml").read_text("utf-8")
    for rel in plan.releases:
        if rel.component.name == capability:
            text = release._with_capability_floors(text, rel)
    entry = versioning.requires_capability_entry(text, PM)
    assert entry is not None and entry.range is not None, f"{capability}: no range on {PM}"
    return entry.range


@pytest.mark.parametrize("capability", CONTRIBUTORS)
def test_the_range_admits_the_pm_the_tree_carries(capability, next_release) -> None:
    """A branch writes no floor above it, or validation refuses the tree (PRJ-002 D1)."""
    carried = next_release.versions.carries[PM]
    assert range_admits(_pm_dependency(capability)["version"], carried) is True


@pytest.mark.parametrize("capability", CONTRIBUTORS)
def test_after_the_next_release_the_range_admits_no_pm_without_the_floor(
    capability, next_release
) -> None:
    """An older pm refuses the floor, so every pull request would fail closed
    until it is upgraded. The range keeps that pm out at install and upgrade,
    from the release that ships the floor: the tree's range already, or the
    floor a pending changeset declares, raised by the release (PRJ-002 D4)."""
    after = _pm_range_after(next_release, capability)
    assert range_admits(after, PM_WITHOUT_THE_FLOOR) is False
    assert range_admits(after, next_release.versions.after(PM)) is True


@pytest.mark.parametrize("capability", CONTRIBUTORS)
def test_no_contributor_requires_any_capability(capability) -> None:
    """Each records that it works on its own (living-docs DEC-001 point 9,
    software-analysis DEC-001 point 10)."""
    for entry in _package(capability).get("requires_capabilities") or []:
        assert entry.get("optional") is True, entry


# ---- the gate, through the real collector ------------------------------------


def _install(repo_root: Path, capabilities: tuple[str, ...]) -> None:
    """Register `capabilities`, copy each one's shipped declaration into place,
    and deploy the core reviewer, as `pkit sync` does."""
    lines = ["schema_version: 1", "backbone_version: 1.0.0", "components:"]
    for name in ("project-management", *capabilities):
        lines += [
            "  - kind: capability",
            f"    name: {name}",
            f"    manifest: .pkit/capabilities/{name}/manifest.yaml",
        ]
    (repo_root / ".pkit").mkdir(parents=True, exist_ok=True)
    (repo_root / ".pkit" / "manifest.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for name in capabilities:
        target = repo_root / ".pkit" / "capabilities" / name
        target.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(_declaration(name), target / "review-contributions.yaml")
    agents = repo_root / ".claude" / "agents"
    agents.mkdir(parents=True, exist_ok=True)
    (agents / f"{REVIEWER}.md").write_text("# agent\n", encoding="utf-8")


def _resolve(rr, oo, repo_root: Path, *, ruled: tuple[str, ...], opt_out: tuple[str, ...] = ()):
    """Resolve PR 99, which closes nothing, with `ruled` as the backbone's
    answer and an opt-out of the reviewer from each capability in `opt_out`."""
    config = {
        "review": {
            "agents": {
                "contributed_opt_out": [
                    {"capability": name, "reviewer": REVIEWER, "reason": "Reviewed elsewhere."}
                    for name in opt_out
                ]
            }
        }
    }
    return rr.resolve_required_local_reviewers(
        99,
        baseline_local=[BASELINE],
        repo_root=repo_root,
        closing_issue_numbers=lambda _pr: [],
        issue_labels=lambda _n: [],
        changed_files=lambda _pr: pytest.fail("the ruled-artefact floor reads no changed file"),
        opt_outs=oo.read_opt_outs(config),
        ruled_artefacts=lambda _pr: ruled,
    )


def test_both_installed_require_the_reviewer_once(rr, oo, tmp_path) -> None:
    _install(tmp_path, CONTRIBUTORS)
    res = _resolve(rr, oo, tmp_path, ruled=(RULED_PAGE,))
    assert res.ok, res.error
    assert res.required_local == (BASELINE, REVIEWER)
    assert res.floors_by_reviewer == {REVIEWER: frozenset({"touches-ruled-artefact"})}


@pytest.mark.parametrize(
    ("opted_out", "still_by"),
    [("living-docs", "software-analysis"), ("software-analysis", "living-docs")],
)
def test_opting_out_of_one_leaves_the_reviewer_required_through_the_other(
    rr, oo, tmp_path, opted_out, still_by
) -> None:
    _install(tmp_path, CONTRIBUTORS)
    res = _resolve(rr, oo, tmp_path, ruled=(RULED_PAGE,), opt_out=(opted_out,))
    assert res.ok, res.error
    assert res.required_local == (BASELINE, REVIEWER)
    assert res.contributed_by == {REVIEWER: still_by}
    assert [entry.capability for entry in res.opted_out] == [opted_out]


def test_opting_out_of_both_withdraws_the_reviewer(rr, oo, tmp_path) -> None:
    _install(tmp_path, CONTRIBUTORS)
    res = _resolve(rr, oo, tmp_path, ruled=(RULED_PAGE,), opt_out=CONTRIBUTORS)
    assert res.ok, res.error
    assert res.required_local == (BASELINE,)


@pytest.mark.parametrize("capability", CONTRIBUTORS)
@pytest.mark.parametrize("artefact", [RULED_PAGE, RULED_ACTOR])
def test_either_contributor_alone_covers_every_ruled_artefact(
    rr, oo, tmp_path, capability, artefact
) -> None:
    """A page or an analysis artefact, whichever capability is installed."""
    _install(tmp_path, (capability,))
    res = _resolve(rr, oo, tmp_path, ruled=(artefact,))
    assert res.ok, res.error
    assert res.required_local == (BASELINE, REVIEWER)
    assert res.contributed_by == {REVIEWER: capability}


def test_a_change_altering_no_ruled_artefact_requires_no_more(rr, oo, tmp_path) -> None:
    _install(tmp_path, CONTRIBUTORS)
    res = _resolve(rr, oo, tmp_path, ruled=())
    assert res.ok, res.error
    assert res.required_local == (BASELINE,)


def test_an_undeployed_core_reviewer_fails_the_resolution_closed(rr, oo, tmp_path) -> None:
    """Every pull request, ruled or not, as for any contributed reviewer (DEC-032 D5)."""
    _install(tmp_path, CONTRIBUTORS)
    (tmp_path / ".claude" / "agents" / f"{REVIEWER}.md").unlink()
    res = _resolve(rr, oo, tmp_path, ruled=())
    assert not res.ok
    assert res.error.kind == rr.ERROR_COLLECTION
