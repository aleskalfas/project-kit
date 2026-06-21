"""Tests for `pre-check`'s review-agents validation (DEC-028 + DEC-032 #146).

These cover the singleton-cap lift + resolvable-set validation wired into
`pre-check.py` per project-management:DEC-032's D3 + Implications:

  * **cap lift** — N≥2 `local_registered` entries are accepted (no longer the
    DEC-028 singleton refusal). Their names are validated against deployed
    agent files.
  * **resolvable set** — the set validated is baseline union every contributed
    reviewer name the DEC-032 collector surfaces; a missing deployed agent
    file for any member is a `fail` with redeploy/uninstall remediation.
  * **contribution declarations** — the collector's `ContributionError`s
    (malformed declaration, undeployed contributed agent) are surfaced
    through pre-check's `fail` channel.
  * **baseline-only** — no contributions resolves to baseline only, behaving
    as DEC-028 left it (an absent/empty agents block stays a clean skip / ok).

`collect_contributions` is stubbed (the test owns the contributed half), and
agent deployment is exercised against a real temp `.claude/agents/` tree so
the shared `_lib.agents` resolver runs unmocked.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = (
    REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
)
SCRIPT = SCRIPTS_DIR / "pre-check.py"
RC_PATH = SCRIPTS_DIR / "_lib" / "review_contributions.py"


@pytest.fixture(scope="module")
def pc():
    sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location("pm_pre_check_under_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_pre_check_under_test"] = module
    spec.loader.exec_module(module)
    yield module
    sys.path.remove(str(SCRIPTS_DIR))


@pytest.fixture(scope="module")
def rc():
    sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location("pm_rc_for_pre_check", RC_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_rc_for_pre_check"] = module
    spec.loader.exec_module(module)
    yield module
    sys.path.remove(str(SCRIPTS_DIR))


# ----- helpers -------------------------------------------------------


def _repo_with_agents(tmp_path: Path, *deployed: str) -> Path:
    """Make a repo_root with `.claude/agents/<name>.md` for each `deployed`."""
    agents_dir = tmp_path / ".claude" / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    for name in deployed:
        (agents_dir / f"{name}.md").write_text("# stub agent\n", encoding="utf-8")
    return tmp_path


def _config(*, local=None, remote=None):
    """Build a `review:` config with the given agent registrations."""
    agents: dict = {}
    if local is not None:
        agents["local_registered"] = [{"name": n} for n in local]
    if remote is not None:
        agents["remote_registered"] = [{"github_login": g} for g in remote]
    return {"review": {"mode": "agent", "agents": agents}}


def _stub_collection(pc, rc, monkeypatch, collection) -> None:
    monkeypatch.setattr(pc, "collect_contributions", lambda repo_root: collection)


def _empty_collection(rc):
    return rc.ContributionCollection(rules=())


def _contributed_collection(rc, capability, workstream, reviewer, *, deployed=True):
    """A collection with one contributed rule (matching `workstream`)."""
    from types import MappingProxyType

    err = None
    errors: tuple = ()
    if not deployed:
        err = rc.ContributionError(
            rc.ERROR_UNDEPLOYED_AGENT,
            capability,
            f"capability `{capability}` contributes reviewer `{reviewer}` "
            "but no deployed agent file exists.",
        )
        errors = (err,)
    rule = rc.ContributionRule(
        capability=capability,
        predicate=MappingProxyType({"workstream": (workstream,)}),
        reviewer=reviewer,
        deployed=deployed,
        resolution_error=err,
    )
    return rc.ContributionCollection(
        rules=(rule,), errors=errors, capabilities_walked=(capability,)
    )


def _fails(results):
    return [r for r in results if r.status == "fail"]


def _by_status(results, status):
    return [r for r in results if r.status == status]


# ----- cap lift: N>=2 local reviewers accepted -----------------------


def test_two_local_reviewers_accepted(pc, rc, monkeypatch, tmp_path) -> None:
    """N=2 local agents, both deployed, no contributions → no fail (cap lifted)."""
    repo_root = _repo_with_agents(tmp_path, "reviewer", "second-reviewer")
    _stub_collection(pc, rc, monkeypatch, _empty_collection(rc))

    results = pc._check_review_block(
        _config(local=["reviewer", "second-reviewer"]),
        repo_root / ".pkit" / "capabilities" / "project-management",
    )

    assert _fails(results) == []
    assert any(
        r.status == "ok" and "2 baseline local reviewer" in r.detail
        for r in results
    )
    assert any(
        r.status == "ok" and "all 2 reviewer(s) have deployed" in r.detail
        for r in results
    )


def test_two_local_reviewers_one_missing_agent_fails(
    pc, rc, monkeypatch, tmp_path
) -> None:
    """N=2 baseline, only one deployed → the missing one is a clear fail."""
    repo_root = _repo_with_agents(tmp_path, "reviewer")  # second-reviewer absent
    _stub_collection(pc, rc, monkeypatch, _empty_collection(rc))

    results = pc._check_review_block(
        _config(local=["reviewer", "second-reviewer"]),
        repo_root / ".pkit" / "capabilities" / "project-management",
    )

    fails = _fails(results)
    assert len(fails) == 1
    assert "second-reviewer" in fails[0].label
    assert fails[0].remediation is not None
    assert "second-reviewer.md" in fails[0].remediation


# ----- resolvable set: baseline union contributed -------------------


def test_contributed_reviewer_in_resolvable_set(
    pc, rc, monkeypatch, tmp_path
) -> None:
    """A deployed contributed reviewer joins the resolvable set and passes."""
    repo_root = _repo_with_agents(tmp_path, "reviewer", "design-reviewer")
    collection = _contributed_collection(
        rc, "ux-ui-design", "design", "design-reviewer", deployed=True
    )
    _stub_collection(pc, rc, monkeypatch, collection)

    results = pc._check_review_block(
        _config(local=["reviewer"]),
        repo_root / ".pkit" / "capabilities" / "project-management",
    )

    assert _fails(results) == []
    ok = [r for r in results if r.status == "ok" and "deployed agent files" in r.detail]
    assert ok and "design-reviewer" in ok[0].detail and "reviewer" in ok[0].detail


def test_contributed_reviewer_missing_agent_fails(
    pc, rc, monkeypatch, tmp_path
) -> None:
    """A contributed reviewer with no deployed agent surfaces a blocking fail.

    The collector flags it via its error channel (deployed=False); pre-check
    surfaces that as exactly one fail (no double-report from the resolvable
    set's own missing-file check).
    """
    repo_root = _repo_with_agents(tmp_path, "reviewer")  # design-reviewer absent
    collection = _contributed_collection(
        rc, "ux-ui-design", "design", "design-reviewer", deployed=False
    )
    _stub_collection(pc, rc, monkeypatch, collection)

    results = pc._check_review_block(
        _config(local=["reviewer"]),
        repo_root / ".pkit" / "capabilities" / "project-management",
    )

    fails = _fails(results)
    assert len(fails) == 1
    assert "ux-ui-design" in fails[0].label
    assert fails[0].remediation is not None


# ----- malformed contribution declaration ---------------------------


def test_malformed_contribution_declaration_rejected(
    pc, rc, monkeypatch, tmp_path
) -> None:
    """A collector malformed-declaration error surfaces as a pre-check fail."""
    repo_root = _repo_with_agents(tmp_path, "reviewer")
    err = rc.ContributionError(
        rc.ERROR_MALFORMED,
        "ux-ui-design",
        "capability `ux-ui-design`: contributions[0].match must be a "
        "non-empty mapping",
    )
    collection = rc.ContributionCollection(
        rules=(), errors=(err,), capabilities_walked=("ux-ui-design",)
    )
    _stub_collection(pc, rc, monkeypatch, collection)

    results = pc._check_review_block(
        _config(local=["reviewer"]),
        repo_root / ".pkit" / "capabilities" / "project-management",
    )

    fails = _fails(results)
    assert len(fails) == 1
    assert "ux-ui-design" in fails[0].label
    assert "non-empty mapping" in fails[0].detail


# ----- baseline-only / no-contributions = DEC-028 behaviour ----------


def test_baseline_only_single_reviewer_ok(pc, rc, monkeypatch, tmp_path) -> None:
    """Single baseline reviewer, deployed, no contributions → ok (unchanged)."""
    repo_root = _repo_with_agents(tmp_path, "reviewer")
    _stub_collection(pc, rc, monkeypatch, _empty_collection(rc))

    results = pc._check_review_block(
        _config(local=["reviewer"]),
        repo_root / ".pkit" / "capabilities" / "project-management",
    )

    assert _fails(results) == []
    assert any(
        r.status == "ok" and "all 1 reviewer(s) have deployed" in r.detail
        for r in results
    )


def test_baseline_missing_agent_still_fails(pc, rc, monkeypatch, tmp_path) -> None:
    """The DEC-028 missing-baseline-agent refusal is preserved post-rebind."""
    repo_root = _repo_with_agents(tmp_path)  # reviewer not deployed
    _stub_collection(pc, rc, monkeypatch, _empty_collection(rc))

    results = pc._check_review_block(
        _config(local=["reviewer"]),
        repo_root / ".pkit" / "capabilities" / "project-management",
    )

    fails = _fails(results)
    assert len(fails) == 1
    assert "reviewer" in fails[0].label


def test_no_review_block_skips(pc, rc, monkeypatch, tmp_path) -> None:
    """No `review:` block → single skip, collector never consulted (unchanged)."""
    results = pc._check_review_block(
        {}, tmp_path / ".pkit" / "capabilities" / "project-management"
    )
    assert len(results) == 1
    assert results[0].status == "skip"


def test_empty_agents_block_no_resolvable_set(
    pc, rc, monkeypatch, tmp_path
) -> None:
    """`review:` present but no agents and no contributions → no fail."""
    repo_root = _repo_with_agents(tmp_path)
    _stub_collection(pc, rc, monkeypatch, _empty_collection(rc))

    results = pc._check_review_block(
        {"review": {"mode": "agent"}},
        repo_root / ".pkit" / "capabilities" / "project-management",
    )
    # mode ok + (agents absent so no agents validation path) — no fails.
    assert _fails(results) == []


# ----- remote path: singleton retained ------------------------------


def test_remote_registered_still_singleton(pc, rc, monkeypatch, tmp_path) -> None:
    """DEC-032 lifts only the local cap; N>1 remote entries still refused."""
    repo_root = _repo_with_agents(tmp_path, "reviewer")
    _stub_collection(pc, rc, monkeypatch, _empty_collection(rc))

    results = pc._check_review_block(
        _config(local=["reviewer"], remote=["bot-a", "bot-b"]),
        repo_root / ".pkit" / "capabilities" / "project-management",
    )

    fails = _fails(results)
    assert any("remote_registered singleton" in r.label for r in fails)
