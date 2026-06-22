"""Regression guard: review-pr's invoke-set == done-work's gate-set (DEC-032 D4).

DEC-032's whole point is that the required-reviewer resolution is "owned once
so the consumers can't diverge". `review-pr` INVOKES the resolved set and
`done-work`'s gate GATES on the resolved set; if they ever acted on *different*
sets, a developer could run `review-pr`, watch every invoked agent approve,
and still hit a gate refusal (or the inverse — the gate could pass on a set
`review-pr` never invoked). Issue #147's acceptance criteria call for a
regression guard against exactly that divergence.

**This guard exercises each consumer's REAL post-resolution wiring, not just
the shared helper's output twice.** Both `_resolve_required_local` methods are
~5-line pass-throughs to the same `resolve_required_local_reviewers`, so
comparing their return values only proves "the same function returns the same
value when called twice" — a near-tautology that says nothing about what each
consumer *does* with the resolution. The real, load-bearing property is
post-resolution:

  * `review-pr` must INVOKE exactly the resolved local set — its invoke loop
    (`main()`'s `for name in required_local:` block) is what produces the
    verdicts. We drive `main()` and capture the names it actually invokes.
  * `done-work`'s gate must GATE on exactly that same local set — its gate
    loop (`for name in required_local:` in `_check_agent_gate`) is what demands
    a fresh APPROVED. We drive `_check_agent_gate` against the same stubbed
    world and probe the set of names it requires an approval for.

The probe is bidirectional, so it fails loudly if a FUTURE edit re-introduces
a post-resolution filter in *either* consumer (e.g. a `if name in ...: continue`
that skips a name on one side but not the other):

  1. Provide a fresh APPROVED for exactly the names `review-pr` invoked → the
     gate must PASS. (Catches the gate requiring MORE than was invoked — an
     extra required local name `review-pr` never invoked.)
  2. For each invoked name, withhold just that one approval → the gate must
     REFUSE. (Catches the gate requiring LESS than was invoked — a name
     `review-pr` invoked but a gate-side filter dropped, which would let the
     gate pass without it.)

Together these pin the gate's required-local set to exactly the invoked set,
across the DEC-032 D1 resolution domain (baseline-only, compose, multi-issue
union, dedup) and the fail-closed branch.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import MappingProxyType, SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = (
    REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
)
DW_PATH = SCRIPTS_DIR / "done-work.py"
RPR_PATH = SCRIPTS_DIR / "review-pr.py"
RC_PATH = SCRIPTS_DIR / "_lib" / "review_contributions.py"

# A commit timestamp every verdict comment post-dates (the gate's freshness
# anchor); a fresh timestamp strictly after it for the verdicts.
_COMMIT_TS = "2026-06-01T00:00:00Z"
_FRESH_TS = "2026-06-02T00:00:00Z"


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
def dw():
    return _load("pm_dw_for_parity", DW_PATH)


@pytest.fixture(scope="module")
def rpr():
    return _load("pm_rpr_for_parity", RPR_PATH)


@pytest.fixture(scope="module")
def rc():
    return _load("pm_rc_for_parity", RC_PATH)


# A capability_root whose .parent.parent.parent is a throwaway repo_root.
# collect_contributions is stubbed, so the path is never read by the resolver.
CAP_ROOT = Path("/tmp/x/.pkit/capabilities/project-management")

# The single baseline local reviewer both consumers start from.
BASELINE = ("reviewer",)


# ---- collections + scenarios spanning the DEC-032 D1 resolution domain ----


def _design_collection(rc):
    rule = rc.ContributionRule(
        capability="ux-ui-design",
        predicate=MappingProxyType({"workstream": ("design",)}),
        reviewer="design-reviewer",
    )
    return rc.ContributionCollection(rules=(rule,))


def _multi_collection(rc):
    design = rc.ContributionRule(
        capability="ux-ui-design",
        predicate=MappingProxyType({"workstream": ("design",)}),
        reviewer="design-reviewer",
    )
    backend = rc.ContributionRule(
        capability="backend-discipline",
        predicate=MappingProxyType({"workstream": ("backend",)}),
        reviewer="backend-reviewer",
    )
    return rc.ContributionCollection(rules=(design, backend))


def _dedup_collection(rc):
    rule = rc.ContributionRule(
        capability="ux-ui-design",
        predicate=MappingProxyType({"workstream": ("design",)}),
        reviewer="reviewer",  # same name as baseline → required once.
    )
    return rc.ContributionCollection(rules=(rule,))


# Each scenario is (label, factory) where factory(rc) returns
# (collection, closing_issue_labels) — the SAME stubbed world fed to both
# consumers. closing_issue_labels maps issue-number → label-name list.
def _scenarios(rc):
    return {
        "baseline-only-no-closing": lambda: (
            rc.ContributionCollection(rules=()), {},
        ),
        "baseline-only-no-workstream": lambda: (
            _design_collection(rc), {42: ["type:feature"]},
        ),
        "baseline-only-non-matching": lambda: (
            _design_collection(rc), {42: ["workstream:backend"]},
        ),
        "compose-design": lambda: (
            _design_collection(rc), {42: ["workstream:design"]},
        ),
        "multi-issue-union": lambda: (
            _multi_collection(rc),
            {42: ["workstream:design"], 43: ["workstream:backend"]},
        ),
        "dedup": lambda: (
            _dedup_collection(rc), {42: ["workstream:design"]},
        ),
    }


_SCENARIO_LABELS = [
    "baseline-only-no-closing",
    "baseline-only-no-workstream",
    "baseline-only-non-matching",
    "compose-design",
    "multi-issue-union",
    "dedup",
]


# ---- world stubs: identical inputs to both consumers ------------------


def _stub_closing_resolution(module, monkeypatch, *, collection, labels, refs_rc=0):
    """Stub a consumer's resolution seams (collection + the two gh fetchers).

    Both `done-work` and `review-pr` resolve via their own module-level
    `collect_contributions` + `gh_run` + `gh_get_issue` (the delegating fetcher
    lambdas look these up as module globals at call time). Wiring identical
    stubs into each makes the resolution inputs identical, so any difference in
    what the consumers DO post-resolution is a real divergence.

    `labels` maps closing-issue number → label-name list. `refs_rc` non-zero
    forces the closingIssuesReferences lookup to fail (the fail-closed branch).
    This stub only governs the *resolution* gh calls (closingIssuesReferences +
    per-issue labels); the gate's later `author,comments,commits` round-trip is
    stubbed separately by `_run_gate` so the comment payload can be varied.
    """
    monkeypatch.setattr(module, "collect_contributions", lambda repo_root: collection)

    def fake_gh_get_issue(issue_number, config, *, fields):
        return {"labels": [{"name": n} for n in labels.get(issue_number, [])]}

    monkeypatch.setattr(module, "gh_get_issue", fake_gh_get_issue)
    return refs_rc


def _closing_refs_response(args, labels, refs_rc):
    """The CompletedProcess for a `gh pr view --json closingIssuesReferences`."""
    if refs_rc != 0:
        return subprocess.CompletedProcess(
            args=args, returncode=refs_rc, stdout="", stderr="gh boom",
        )
    refs = [{"number": n} for n in labels]
    return subprocess.CompletedProcess(
        args=args, returncode=0,
        stdout=json.dumps({"closingIssuesReferences": refs}), stderr="",
    )


# ---- review-pr: capture the set it actually INVOKES -------------------


def _invoke_set(rpr, monkeypatch, tmp_path, *, collection, labels):
    """Drive `review-pr.main()` against the stubbed world; return invoked names.

    Exercises the REAL invoke loop (`main()`'s `for name in required_local:`),
    not `_resolve_required_local` in isolation. Returns the list of reviewer
    names `review-pr` actually invoked, in order.
    """
    refs_rc = _stub_closing_resolution(
        rpr, monkeypatch, collection=collection, labels=labels,
    )

    def fake_gh_run(args, config, **kwargs):
        if "closingIssuesReferences" in " ".join(args):
            return _closing_refs_response(args, labels, refs_rc)
        return subprocess.CompletedProcess(
            args=args, returncode=0, stdout="{}", stderr="",
        )

    monkeypatch.setattr(rpr, "gh_run", fake_gh_run)

    cap_root = tmp_path / ".pkit" / "capabilities" / "project-management"
    cap_root.mkdir(parents=True, exist_ok=True)
    agents_dir = tmp_path / ".claude" / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    # The invoke loop requires each agent's file to exist; deploy them all so
    # invocation proceeds for every resolved name (we are measuring the set, not
    # the deploy check). The resolved set is small and known per scenario.
    for name in ("reviewer", "design-reviewer", "backend-reviewer"):
        (agents_dir / f"{name}.md").write_text("agent", encoding="utf-8")

    monkeypatch.setattr(rpr, "resolve_capability_root", lambda arg: cap_root)
    monkeypatch.setattr(rpr, "load_adopter_config", lambda root: {
        "review": {"agents": {"local_registered": [{"name": "reviewer"}]}}
    })
    monkeypatch.setattr(rpr, "_read_members", lambda root, loader: [])
    monkeypatch.setattr(rpr, "resolve_invoker_identity", lambda config: "dev")
    monkeypatch.setattr(
        rpr, "check_membership",
        lambda members, invoker: SimpleNamespace(allowed=True, refusal_message=""),
    )
    monkeypatch.setattr(rpr, "_find_issue_branch", lambda n: f"feat/{n}-x")
    monkeypatch.setattr(rpr, "_find_pr_for_branch", lambda branch, config: {"number": 99})

    invoked: list[str] = []

    def fake_invoke(name, pr_number, config):
        invoked.append(name)
        return "APPROVED", "body"

    monkeypatch.setattr(rpr, "_invoke_agent", fake_invoke)
    monkeypatch.setattr(rpr, "_post_comment", lambda pr, body, config: True)
    monkeypatch.setattr(sys, "argv", ["review-pr", "99"])

    rc_code = rpr.main()
    assert rc_code == 0, "review-pr should invoke cleanly in the resolvable domain"
    return invoked


# ---- done-work: probe the set its gate actually GATES on --------------


def _run_gate(dw, monkeypatch, *, collection, labels, approved_names, refs_rc=0):
    """Run `_check_agent_gate` against the stubbed world with `approved_names`
    having a fresh APPROVED. Returns the `_GateResult`.

    Exercises the REAL gate loop (`_check_agent_gate`'s `for name in
    required_local:`), so the gate's pass/fail reflects exactly which local
    names it demands a fresh APPROVED for. With no remote agents configured,
    the required set is purely local — the gate passes iff every required
    local name is approved.
    """
    _stub_closing_resolution(
        dw, monkeypatch, collection=collection, labels=labels, refs_rc=refs_rc,
    )

    comments = [
        {
            "author": {"login": "reviewer"},
            "body": f"Reviewer agent (local, {name}): APPROVED\n\nbody.",
            "createdAt": _FRESH_TS,
        }
        for name in approved_names
    ]

    def fake_gh_run(args, config, **kwargs):
        if "closingIssuesReferences" in " ".join(args):
            return _closing_refs_response(args, labels, refs_rc)
        # gh pr view --json author,comments,commits
        return subprocess.CompletedProcess(
            args=args, returncode=0,
            stdout=json.dumps({
                "author": {"login": "author"},
                "comments": comments,
                "commits": [{"committedDate": _COMMIT_TS}],
            }),
            stderr="",
        )

    monkeypatch.setattr(dw, "gh_run", fake_gh_run)

    config = {"review": {"agents": {
        "local_registered": [{"name": "reviewer"}],
        "remote_registered": [],
    }}}
    return dw._check_agent_gate(99, {}, config, "resolved", CAP_ROOT)


# ---- the guard --------------------------------------------------------


@pytest.mark.parametrize("label", _SCENARIO_LABELS)
def test_invoke_set_equals_gate_set(dw, rpr, rc, monkeypatch, tmp_path, label) -> None:
    """review-pr's invoked set == the local set done-work's gate gates on.

    Bidirectional: the gate PASSES given exactly the invoked approvals (no
    extra required name), and REFUSES if any single invoked approval is
    withheld (no dropped/filtered name). Both consumers run their real
    post-resolution wiring against one stubbed world.
    """
    collection, labels = _scenarios(rc)[label]()

    invoked = _invoke_set(rpr, monkeypatch, tmp_path, collection=collection, labels=labels)
    assert invoked, "every scenario invokes at least the baseline reviewer"

    # Direction 1: approving exactly the invoked set satisfies the gate.
    passing = _run_gate(
        dw, monkeypatch, collection=collection, labels=labels, approved_names=invoked,
    )
    assert passing.passed, (
        f"[{label}] gate refused on exactly review-pr's invoked set "
        f"{invoked!r} — the gate requires a local name review-pr did not "
        f"invoke (invoke-set ⊊ gate-set divergence). Refusal:\n"
        f"{passing.refusal_message}"
    )

    # Direction 2: withholding any one invoked approval must refuse — proving
    # the gate genuinely requires every invoked name (none silently filtered).
    for withheld in invoked:
        remaining = [n for n in invoked if n != withheld]
        refusing = _run_gate(
            dw, monkeypatch, collection=collection, labels=labels,
            approved_names=remaining,
        )
        assert not refusing.passed, (
            f"[{label}] gate PASSED without {withheld!r} approved, yet "
            f"review-pr invoked it — the gate does not require a name "
            f"review-pr invokes (gate-set ⊊ invoke-set divergence). A "
            f"post-resolution filter on the gate side would slip through here."
        )


def test_invoke_set_equals_gate_set_on_fail_closed(dw, rpr, rc, monkeypatch, tmp_path) -> None:
    """A transient closing-issue resolution failure: review-pr aborts WITHOUT
    invoking (exit 2) and done-work's gate REFUSES — neither acts on a set, so
    invoke-set == gate-set == ∅ holds in the fail-closed branch too (D5)."""
    collection = _design_collection(rc)
    labels: dict[int, list[str]] = {}

    # review-pr side: force the closingIssuesReferences lookup to fail and
    # confirm main() aborts (exit 2) invoking nothing.
    _stub_closing_resolution(rpr, monkeypatch, collection=collection, labels=labels, refs_rc=1)

    def fake_gh_run_rpr(args, config, **kwargs):
        if "closingIssuesReferences" in " ".join(args):
            return _closing_refs_response(args, labels, 1)
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="{}", stderr="")

    monkeypatch.setattr(rpr, "gh_run", fake_gh_run_rpr)
    cap_root = tmp_path / ".pkit" / "capabilities" / "project-management"
    cap_root.mkdir(parents=True, exist_ok=True)
    (tmp_path / ".claude" / "agents").mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(rpr, "resolve_capability_root", lambda arg: cap_root)
    monkeypatch.setattr(rpr, "load_adopter_config", lambda root: {
        "review": {"agents": {"local_registered": [{"name": "reviewer"}]}}
    })
    monkeypatch.setattr(rpr, "_read_members", lambda root, loader: [])
    monkeypatch.setattr(rpr, "resolve_invoker_identity", lambda config: "dev")
    monkeypatch.setattr(
        rpr, "check_membership",
        lambda members, invoker: SimpleNamespace(allowed=True, refusal_message=""),
    )
    monkeypatch.setattr(rpr, "_find_issue_branch", lambda n: f"feat/{n}-x")
    monkeypatch.setattr(rpr, "_find_pr_for_branch", lambda branch, config: {"number": 99})
    invoked: list[str] = []
    monkeypatch.setattr(
        rpr, "_invoke_agent",
        lambda name, pr, config: (invoked.append(name), ("APPROVED", "body"))[1],
    )
    monkeypatch.setattr(rpr, "_post_comment", lambda pr, body, config: True)
    monkeypatch.setattr(sys, "argv", ["review-pr", "99"])
    assert rpr.main() == 2
    assert invoked == []

    # done-work side: the same failure makes the gate refuse (fail-closed).
    gate = _run_gate(
        dw, monkeypatch, collection=collection, labels=labels,
        approved_names=["reviewer"], refs_rc=1,
    )
    assert not gate.passed
