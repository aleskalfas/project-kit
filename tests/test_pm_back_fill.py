"""Corpus back-fill — the report half (T2a, DEC-037 §2 / ADR-031).

`back-fill.py` is the auditable propose-and-cite REPORT for the one-time
brownfield corpus back-fill: it enumerates the proposed per-issue non-label
substrate writes (Projects-v2 field value; milestone), cites why each is
proposed, and gates on the residual hard-fail subset of pre-check (auth /
repo-access / map-parse / declared-field-intent-but-board-unresolvable). It
MUTATES NOTHING — applying the plan is T2b.

These tests pin the contract this half owns:

  * enumeration correctness — one proposed change per (issue, intent);
  * the planned write argv is constructed through the substrate_writes `*_args`
    sole constructors (ADR-031), never string-built, and shows the exact write;
  * citation — each proposed change cites the hook entry (and any corroborating
    substrate-map default) that drives it (DEC-037 §2);
  * the residual-pre-check gate refuses on auth / repo / map-parse, and PROCEEDS
    under a merely-degraded axis (DEC-036 — the gate is not "any pre-check fail");
  * the FOURTH residual member — a declared field intent with the board globally
    unresolvable refuses ONCE at the top; the per-issue "not on the board" case
    stays a per-issue `blocked`;
  * the board node id is resolved from the REAL config shape (`projects_v2_board_id`
    board number + owner), not a fabricated `projects_v2_node_id` key;
  * board item-id resolution is repo-discriminated — a colliding number on another
    repo's board item does not resolve to the target issue;
  * value-equality idempotency annotation (already-satisfied) is surfaced;
  * `--limit` truncation is loudly signalled (warning line + `truncated` flag);
  * NO write executes (no `gh` mutating call is ever issued — caught at the seam
    both modules share, with a tightened mutation-vs-read graphql discrimination).

The gh reads are stubbed; the gate's residual probes are stubbed at the
pre-check module functions the gate reuses.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
LIB_DIR = SCRIPTS_DIR / "_lib"
SCRIPT = SCRIPTS_DIR / "back-fill.py"


@pytest.fixture(scope="module")
def bf():
    sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location("pm_back_fill_under_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_back_fill_under_test"] = module
    spec.loader.exec_module(module)
    yield module


@pytest.fixture(scope="module")
def axis_labels():
    sys.path.insert(0, str(SCRIPTS_DIR))
    from _lib import axis_labels as mod
    yield mod


# A pre-check-style CheckResult stand-in carrying the fields the gate reads.
@dataclass
class _Check:
    label: str
    status: str
    detail: str
    remediation: str | None = None


def _cap_root_with_hooks(tmp_path: Path, hooks_yaml: str, map_yaml: str | None = None) -> Path:
    """Build a temp capability root carrying a hooks.yaml (and optional map)."""
    cap = tmp_path / ".pkit" / "capabilities" / "project-management"
    (cap / "project").mkdir(parents=True, exist_ok=True)
    (cap / "project" / "hooks.yaml").write_text(hooks_yaml, encoding="utf-8")
    if map_yaml is not None:
        (cap / "project" / "substrate-map.yaml").write_text(map_yaml, encoding="utf-8")
    return cap


# The REAL adopter board-config shape (`has_projects_v2_board` + the board NUMBER
# `projects_v2_board_id`) — exactly what `create-issue.py` / `pre-check.py` /
# `config.yaml` use. NOT the fabricated `projects_v2_node_id` key no adopter sets.
AUJ_BOARD_CONFIG = {
    "has_projects_v2_board": True,
    "projects_v2_board_id": 7,
    "gh": {"default_owner": "ai-platform-incubation"},
}
TARGET_REPO = "ai-platform-incubation/spyre"


AUJ_HOOKS = """\
schema_version: 1
hooks:
  after_create_issue:
    - kind: set-board-field
      field_id: "FIELD_WS"
      single_select_option_id: "OPT_SPYRE"
    - kind: assign-milestone
      title: "Milestone 1"
    - kind: post-comment
      template_path: "project/welcome.md"
"""

AUJ_MAP_WS_DEFAULT = """\
schema_version: 1
axes:
  workstream:
    unsupported: true
    default: Spyre
"""

MILESTONE_ONLY_HOOKS = """\
schema_version: 1
hooks:
  after_create_issue:
    - kind: assign-milestone
      title: "Milestone 1"
"""


# ----- intent resolution + citation ----------------------------------


def test_resolves_intents_from_after_create_issue_hooks(bf, tmp_path, axis_labels) -> None:
    """Only the two covered kinds become intents; post-comment is not a substrate
    write and is ignored (DEC-037 §4)."""
    cap = _cap_root_with_hooks(tmp_path, AUJ_HOOKS)
    intents, errors = bf._resolve_intents(cap, None)
    assert errors == []
    kinds = [i.kind for i in intents]
    assert kinds == ["set-board-field", "assign-milestone"]


def test_intent_citation_names_the_hook_entry(bf, tmp_path) -> None:
    """The citation names the driving hook entry + event (DEC-037 §2 propose-and-
    cite — the human must see WHY each change is proposed)."""
    cap = _cap_root_with_hooks(tmp_path, AUJ_HOOKS)
    intents, _ = bf._resolve_intents(cap, None)
    field_intent = next(i for i in intents if i.kind == "set-board-field")
    assert "hook entry 0" in field_intent.citation
    assert "set-board-field" in field_intent.citation
    assert "after_create_issue" in field_intent.citation


def test_intent_citation_corroborates_with_substrate_map_default(bf, tmp_path, axis_labels) -> None:
    """When the substrate-map declares a `workstream` default, the field intent's
    citation corroborates with it (DEC-036 per-axis default:)."""
    cap = _cap_root_with_hooks(tmp_path, AUJ_HOOKS, map_yaml=AUJ_MAP_WS_DEFAULT)
    smap = axis_labels.load_substrate_map(cap)
    intents, _ = bf._resolve_intents(cap, smap)
    field_intent = next(i for i in intents if i.kind == "set-board-field")
    assert "Spyre" in bf._full_citation(field_intent)
    assert "default" in bf._full_citation(field_intent)


def test_malformed_hook_entry_is_reported_not_crashed(bf, tmp_path) -> None:
    """A set-board-field hook missing its field_id is skipped with a reported
    error, not a crash."""
    hooks = (
        "schema_version: 1\n"
        "hooks:\n"
        "  after_create_issue:\n"
        "    - kind: set-board-field\n"
        "      single_select_option_id: \"OPT\"\n"  # no field_id
    )
    cap = _cap_root_with_hooks(tmp_path, hooks)
    intents, errors = bf._resolve_intents(cap, None)
    assert intents == []
    assert any("field_id" in e for e in errors)


# ----- enumeration + planned-argv construction -----------------------


def test_one_proposed_change_per_issue_per_intent(bf) -> None:
    """Enumeration correctness: |proposed| == |issues| × |intents|."""
    intents = [
        bf.BackFillIntent(kind="assign-milestone", citation="c", milestone_title="M1"),
        bf.BackFillIntent(
            kind="set-board-field", citation="c",
            field_id="F", single_select_option_id="O",
        ),
    ]
    issues = [
        {"number": 1, "title": "one", "milestone": None},
        {"number": 2, "title": "two", "milestone": None},
        {"number": 3, "title": "three", "milestone": None},
    ]
    item_ids = {
        (TARGET_REPO, 1): "ITEM_1",
        (TARGET_REPO, 2): "ITEM_2",
        (TARGET_REPO, 3): "ITEM_3",
    }
    proposed = bf._build_proposed_changes(
        intents, issues, item_ids, project_id="PROJ", target_repo=TARGET_REPO
    )
    assert len(proposed) == 3 * 2


def test_field_value_argv_is_constructed_through_the_sole_constructor(bf) -> None:
    """The planned field-value write shows the exact `gh project item-edit` argv
    the substrate_writes constructor builds (ADR-031) — not a string-built guess."""
    from _lib import substrate_writes

    intent = bf.BackFillIntent(
        kind="set-board-field", citation="c",
        field_id="FIELD_WS", single_select_option_id="OPT_SPYRE",
    )
    issues = [{"number": 7, "title": "seven", "milestone": None}]
    item_ids = {(TARGET_REPO, 7): "ITEM_7"}
    proposed = bf._build_proposed_changes(
        [intent], issues, item_ids, project_id="PROJ_X", target_repo=TARGET_REPO
    )
    [change] = proposed
    expected = substrate_writes.field_value_args(
        item_id="ITEM_7", field_id="FIELD_WS",
        project_id="PROJ_X", single_select_option_id="OPT_SPYRE",
    )
    assert change.argv == expected
    assert change.argv[:3] == ["gh", "project", "item-edit"]
    assert change.prediction == "would-write"


def test_milestone_argv_is_constructed_through_the_sole_constructor(bf) -> None:
    from _lib import substrate_writes

    intent = bf.BackFillIntent(kind="assign-milestone", citation="c", milestone_title="M1")
    issues = [{"number": 9, "title": "nine", "milestone": None}]
    proposed = bf._build_proposed_changes(
        [intent], issues, {}, project_id=None, target_repo=TARGET_REPO
    )
    [change] = proposed
    assert change.argv == substrate_writes.milestone_edit_args(issue_number=9, title="M1")


# ----- value-equality idempotency annotation -------------------------


def test_milestone_already_satisfied_is_annotated(bf) -> None:
    """When the issue's milestone already equals the target, the change is
    annotated already-satisfied (the value-equality DEC-037 §2 idempotency,
    surfaced for the human — the binding skip is T2b's at apply time)."""
    intent = bf.BackFillIntent(kind="assign-milestone", citation="c", milestone_title="M1")
    issues = [{"number": 5, "title": "five", "milestone": {"title": "M1"}}]
    proposed = bf._build_proposed_changes(
        [intent], issues, {}, project_id=None, target_repo=TARGET_REPO
    )
    [change] = proposed
    assert change.prediction == "already-satisfied"
    assert change.observed == "M1"
    # The argv is STILL constructed (the plan is value-equality-annotated, not
    # pruned — T2b makes the binding skip against a fresh read).
    assert change.argv is not None


def test_milestone_drift_is_would_write(bf) -> None:
    intent = bf.BackFillIntent(kind="assign-milestone", citation="c", milestone_title="M2")
    issues = [{"number": 5, "title": "five", "milestone": {"title": "M1"}}]
    proposed = bf._build_proposed_changes(
        [intent], issues, {}, project_id=None, target_repo=TARGET_REPO
    )
    assert proposed[0].prediction == "would-write"
    assert proposed[0].observed == "M1"


# ----- blocked field write (no fabricated argv) ----------------------


def test_field_write_blocked_when_issue_not_on_board(bf) -> None:
    """A field-value write needs the issue's board item id. When the board resolves
    but THIS issue isn't on it, the change is per-issue BLOCKED with no fabricated
    argv (ADR-031: never invent ids). This is the PER-ISSUE case — distinct from
    the global board-unresolvable gate (DEC-037 §2)."""
    intent = bf.BackFillIntent(
        kind="set-board-field", citation="c",
        field_id="F", single_select_option_id="O",
    )
    issues = [{"number": 11, "title": "eleven", "milestone": None}]
    # board resolves (project_id present)… but #11 is not in item_ids.
    proposed = bf._build_proposed_changes(
        [intent], issues, {}, project_id="PROJ", target_repo=TARGET_REPO
    )
    [change] = proposed
    assert change.prediction == "blocked"
    assert change.argv is None
    assert "not on" in change.blocked_reason


# ----- R2: board item-id resolution is repo-discriminated ------------


def test_board_item_ids_keyed_on_repo_and_number(bf, monkeypatch) -> None:
    """A Projects-v2 board can carry colliding issue numbers from multiple repos.
    The item map is keyed on (repo, number) so #42 in the target repo and #42 in
    another repo resolve to DISTINCT item ids — no cross-repo collision."""
    def fake_gh_run(args, config, **kwargs):
        return subprocess.CompletedProcess(
            args, 0,
            stdout=json.dumps({"data": {"node": {"items": {
                "pageInfo": {"hasNextPage": False, "endCursor": None},
                "nodes": [
                    {"id": "ITEM_TARGET_42", "content": {
                        "number": 42, "repository": {"nameWithOwner": TARGET_REPO}}},
                    {"id": "ITEM_OTHER_42", "content": {
                        "number": 42, "repository": {"nameWithOwner": "other/repo"}}},
                ],
            }}}}),
            stderr="",
        )

    monkeypatch.setattr(bf, "gh_run", fake_gh_run)
    item_ids = bf._resolve_board_item_ids({}, "PROJ_NODE", [{"number": 42}])
    assert item_ids[(TARGET_REPO, 42)] == "ITEM_TARGET_42"
    assert item_ids[("other/repo", 42)] == "ITEM_OTHER_42"


def test_field_value_resolves_target_repo_item_not_a_colliding_one(bf) -> None:
    """End-to-end of the discriminator: with a colliding #42 on the board, the
    field write for the TARGET repo's #42 carries the target's item id — the other
    repo's #42 item id never leaks into the plan's argv."""
    intent = bf.BackFillIntent(
        kind="set-board-field", citation="c",
        field_id="FIELD_WS", single_select_option_id="OPT_SPYRE",
    )
    issues = [{"number": 42, "title": "forty-two", "milestone": None}]
    item_ids = {
        (TARGET_REPO, 42): "ITEM_TARGET_42",
        ("other/repo", 42): "ITEM_OTHER_42",
    }
    proposed = bf._build_proposed_changes(
        [intent], issues, item_ids, project_id="PROJ", target_repo=TARGET_REPO
    )
    [change] = proposed
    assert change.prediction == "would-write"
    assert "ITEM_TARGET_42" in change.argv
    assert "ITEM_OTHER_42" not in change.argv


# ----- R1: board node id resolves from the REAL config shape ---------


def test_project_node_id_resolves_from_board_number_and_owner(bf, monkeypatch) -> None:
    """The board node id is resolved from `projects_v2_board_id` (a board NUMBER) +
    owner via `gh project view --format json` — the way create-issue/pre-check read
    the board — NOT from a fabricated `projects_v2_node_id` config key."""
    seen: dict = {}

    def fake_gh_run(args, config, **kwargs):
        seen["args"] = list(args)
        return subprocess.CompletedProcess(
            args, 0, stdout=json.dumps({"id": "PROJ_NODE_FROM_NUMBER"}), stderr=""
        )

    monkeypatch.setattr(bf, "gh_run", fake_gh_run)
    node_id = bf._resolve_project_node_id(AUJ_BOARD_CONFIG)
    assert node_id == "PROJ_NODE_FROM_NUMBER"
    # It read the board NUMBER (7) and the configured owner — the real shape.
    assert seen["args"][:4] == ["gh", "project", "view", "7"]
    assert "--owner" in seen["args"]
    assert "ai-platform-incubation" in seen["args"]


def test_project_node_id_none_when_no_board_configured(bf, monkeypatch) -> None:
    """`has_projects_v2_board` falsey ⇒ no board node id (and no gh call)."""
    called = {"ran": False}

    def fake_gh_run(args, config, **kwargs):
        called["ran"] = True
        return subprocess.CompletedProcess(args, 0, stdout="{}", stderr="")

    monkeypatch.setattr(bf, "gh_run", fake_gh_run)
    assert bf._resolve_project_node_id({"has_projects_v2_board": False}) is None
    assert called["ran"] is False


def test_auj_field_value_case_produces_would_write_under_real_config(
    bf, tmp_path, monkeypatch, capsys
) -> None:
    """The grounding-case regression: under the REAL config shape (board NUMBER +
    owner, `workstream=Spyre`), the field-value path produces `would-write` — NOT
    all-blocked. This is exactly the R1 BLOCKER: gating on a fabricated
    `projects_v2_node_id` key made every field change report `blocked`."""
    cap = _cap_root_with_hooks(tmp_path, AUJ_HOOKS, map_yaml=AUJ_MAP_WS_DEFAULT)

    def fake_load_config(_root):
        return dict(AUJ_BOARD_CONFIG)

    def fake_gh_run(args, config, **kwargs):
        if args[:4] == ["gh", "project", "view", "7"]:
            return subprocess.CompletedProcess(
                args, 0, stdout=json.dumps({"id": "PROJ_NODE"}), stderr="")
        if args[:3] == ["gh", "repo", "view"]:
            return subprocess.CompletedProcess(
                args, 0, stdout=json.dumps({"nameWithOwner": TARGET_REPO}), stderr="")
        if args[:3] == ["gh", "issue", "list"]:
            return subprocess.CompletedProcess(
                args, 0,
                stdout=json.dumps([{"number": 1, "title": "one", "milestone": None}]),
                stderr="")
        if args[:3] == ["gh", "api", "graphql"]:
            return subprocess.CompletedProcess(
                args, 0,
                stdout=json.dumps({"data": {"node": {"items": {
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                    "nodes": [{"id": "ITEM_1", "content": {
                        "number": 1, "repository": {"nameWithOwner": TARGET_REPO}}}],
                }}}}),
                stderr="")
        return subprocess.CompletedProcess(args, 0, stdout="{}", stderr="")

    monkeypatch.setattr(bf, "load_adopter_config", fake_load_config)
    monkeypatch.setattr(bf, "gh_run", fake_gh_run)
    _patch_gate_checks(bf, monkeypatch, auth_ok=True, repo_ok=True, map_ok=True)
    monkeypatch.setattr(
        sys, "argv", ["back-fill.py", "--capability-root", str(cap), "--json"]
    )

    rc = bf.main()
    assert rc == 0
    plan = json.loads(capsys.readouterr().out)
    field_changes = [c for c in plan["proposed"] if c["kind"] == "set-board-field"]
    assert field_changes, "no field-value change was proposed at all"
    assert all(c["prediction"] == "would-write" for c in field_changes), (
        f"field-value path is not all would-write under the real config: "
        f"{[c['prediction'] for c in field_changes]}"
    )


# ----- residual pre-check gate (arms 1 + the fourth member) -----------


def _patch_gate_checks(
    bf, monkeypatch, *, auth_ok: bool, repo_ok: bool, map_ok: bool = True
) -> None:
    """Patch the pre-check module the gate loads so its three residual probes
    return the requested statuses — without touching real gh or a real map."""
    fake_module = type("FakePreCheck", (), {})()
    fake_module._check_gh_auth = lambda: _Check(
        "`gh` authenticated", "ok" if auth_ok else "fail",
        "auth ok" if auth_ok else "no active authentication",
    )
    fake_module._check_repo_accessible = lambda: _Check(
        "repo accessible", "ok" if repo_ok else "fail",
        "owner/repo" if repo_ok else "`gh repo view` failed",
    )
    fake_module._check_substrate_map_parse = lambda _root: _Check(
        "substrate-map.yaml parses", "ok" if map_ok else "fail",
        "parses" if map_ok else "present but unparseable",
    )
    monkeypatch.setattr(bf, "_load_pre_check_module", lambda _root: fake_module)


def test_gate_passes_when_residual_checks_ok(bf, tmp_path, monkeypatch) -> None:
    cap = _cap_root_with_hooks(tmp_path, AUJ_HOOKS)
    _patch_gate_checks(bf, monkeypatch, auth_ok=True, repo_ok=True)
    gate = bf._residual_pre_check(cap)
    assert gate.passed is True


def test_gate_refuses_on_auth_failure(bf, tmp_path, monkeypatch) -> None:
    cap = _cap_root_with_hooks(tmp_path, AUJ_HOOKS)
    _patch_gate_checks(bf, monkeypatch, auth_ok=False, repo_ok=True)
    gate = bf._residual_pre_check(cap)
    assert gate.passed is False
    assert any(s == "fail" and "auth" in l.lower() for l, s, _ in gate.checks)


def test_gate_refuses_on_repo_inaccessible(bf, tmp_path, monkeypatch) -> None:
    cap = _cap_root_with_hooks(tmp_path, AUJ_HOOKS)
    _patch_gate_checks(bf, monkeypatch, auth_ok=True, repo_ok=False)
    gate = bf._residual_pre_check(cap)
    assert gate.passed is False


def test_gate_refuses_on_map_parse_failure(bf, tmp_path, monkeypatch) -> None:
    """A present-but-unparseable substrate-map fails the gate (DEC-037 §2)."""
    cap = _cap_root_with_hooks(tmp_path, AUJ_HOOKS, map_yaml="{{ not yaml")
    _patch_gate_checks(bf, monkeypatch, auth_ok=True, repo_ok=True, map_ok=False)
    gate = bf._residual_pre_check(cap)
    assert gate.passed is False
    assert any(s == "fail" and "map" in l.lower() for l, s, _ in gate.checks)


def test_gate_skips_map_parse_when_no_map_present(bf, tmp_path, monkeypatch) -> None:
    """No substrate-map ⇒ greenfield ⇒ the map-parse probe is not even run (an
    absent map cannot fail to parse and is not a back-fill failure)."""
    cap = _cap_root_with_hooks(tmp_path, AUJ_HOOKS)  # no map written
    called = {"map_parse": False}

    fake = type("FakePreCheck", (), {})()
    fake._check_gh_auth = lambda: _Check("`gh` authenticated", "ok", "ok")
    fake._check_repo_accessible = lambda: _Check("repo accessible", "ok", "ok")

    def _map_probe(_root):
        called["map_parse"] = True
        return _Check("substrate-map.yaml parses", "ok", "ok")

    fake._check_substrate_map_parse = _map_probe
    monkeypatch.setattr(bf, "_load_pre_check_module", lambda _root: fake)

    gate = bf._residual_pre_check(cap)
    assert gate.passed is True
    assert called["map_parse"] is False


def test_gate_proceeds_under_a_degraded_axis(bf, tmp_path, monkeypatch) -> None:
    """The DISCRIMINATING property (DEC-036): a merely-degraded axis (here
    `workstream: unsupported`) does NOT refuse the back-fill. The gate runs ONLY
    the residual subset — the degraded-axis matrix is never consulted by the gate.
    With auth/repo/map all ok, the gate passes despite an unsupported axis."""
    degraded_map = (
        "schema_version: 1\n"
        "axes:\n"
        "  workstream:\n"
        "    unsupported: true\n"
    )
    cap = _cap_root_with_hooks(tmp_path, AUJ_HOOKS, map_yaml=degraded_map)
    _patch_gate_checks(bf, monkeypatch, auth_ok=True, repo_ok=True, map_ok=True)
    gate = bf._residual_pre_check(cap)
    assert gate.passed is True
    # The gate's checks are ONLY the residual subset — no per-axis disposition line.
    labels = " ".join(l for l, _, _ in gate.checks).lower()
    assert "axis" not in labels
    assert "workstream" not in labels


def test_gate_fails_closed_when_pre_check_unloadable(bf, tmp_path, monkeypatch) -> None:
    """If pre-check can't be loaded the gate fails closed — we must not propose
    writes against an unverified substrate."""
    cap = _cap_root_with_hooks(tmp_path, AUJ_HOOKS)
    monkeypatch.setattr(bf, "_load_pre_check_module", lambda _root: None)
    gate = bf._residual_pre_check(cap)
    assert gate.passed is False


# ----- the FOURTH residual member (global board-unresolvable) ---------


def test_fourth_member_refuses_field_intent_with_unresolvable_board(
    bf, tmp_path, monkeypatch, capsys
) -> None:
    """DEC-037 §2 fourth member: a covered set-board-field intent IS declared AND
    the board node id cannot be resolved at all ⇒ refuse ONCE at the top (exit 2),
    NO report produced. This is the GLOBAL case — distinct from a per-issue block."""
    cap = _cap_root_with_hooks(tmp_path, AUJ_HOOKS)

    def fake_load_config(_root):
        return {"has_projects_v2_board": False}  # no board → unresolvable

    monkeypatch.setattr(bf, "load_adopter_config", fake_load_config)
    monkeypatch.setattr(
        bf, "gh_run",
        lambda args, config, **kw: subprocess.CompletedProcess(args, 0, "{}", ""),
    )
    _patch_gate_checks(bf, monkeypatch, auth_ok=True, repo_ok=True, map_ok=True)
    monkeypatch.setattr(sys, "argv", ["back-fill.py", "--capability-root", str(cap)])

    rc = bf.main()
    assert rc == 2
    err = capsys.readouterr().err
    assert "REFUSED" in err
    assert "no Projects v2 board resolvable" in err


def test_fourth_member_does_not_gate_a_milestone_only_back_fill(
    bf, tmp_path, monkeypatch, capsys
) -> None:
    """A milestone-only back-fill (no field intent) must NOT gate on the board node
    id — the board is irrelevant to it. With no board configured, it still produces
    a report (exit 0)."""
    cap = _cap_root_with_hooks(tmp_path, MILESTONE_ONLY_HOOKS)

    def fake_load_config(_root):
        return {"has_projects_v2_board": False}  # no board — but milestone-only

    def fake_gh_run(args, config, **kwargs):
        if args[:3] == ["gh", "repo", "view"]:
            return subprocess.CompletedProcess(
                args, 0, stdout=json.dumps({"nameWithOwner": TARGET_REPO}), stderr="")
        if args[:3] == ["gh", "issue", "list"]:
            return subprocess.CompletedProcess(
                args, 0,
                stdout=json.dumps([{"number": 1, "title": "one", "milestone": None}]),
                stderr="")
        return subprocess.CompletedProcess(args, 0, stdout="{}", stderr="")

    monkeypatch.setattr(bf, "load_adopter_config", fake_load_config)
    monkeypatch.setattr(bf, "gh_run", fake_gh_run)
    _patch_gate_checks(bf, monkeypatch, auth_ok=True, repo_ok=True, map_ok=True)
    monkeypatch.setattr(
        sys, "argv", ["back-fill.py", "--capability-root", str(cap), "--json"]
    )

    rc = bf.main()
    assert rc == 0
    plan = json.loads(capsys.readouterr().out)
    assert [c["kind"] for c in plan["proposed"]] == ["assign-milestone"]


# ----- G3: --limit truncation is loudly signalled ---------------------


def test_truncation_warns_and_flags_when_corpus_hits_limit(
    bf, tmp_path, monkeypatch, capsys
) -> None:
    """`len(issues) == limit` ⇒ a loud truncation warning AND a `truncated: true`
    flag in the --json plan (DEC-037 non-silent posture; a truncated corpus
    reviewed as complete is an audit gap)."""
    cap = _cap_root_with_hooks(tmp_path, MILESTONE_ONLY_HOOKS)

    def fake_gh_run(args, config, **kwargs):
        if args[:3] == ["gh", "issue", "list"]:
            # Return EXACTLY --limit (2) issues → truncation suspected.
            return subprocess.CompletedProcess(
                args, 0,
                stdout=json.dumps([
                    {"number": 1, "title": "one", "milestone": None},
                    {"number": 2, "title": "two", "milestone": None},
                ]),
                stderr="")
        if args[:3] == ["gh", "repo", "view"]:
            return subprocess.CompletedProcess(
                args, 0, stdout=json.dumps({"nameWithOwner": TARGET_REPO}), stderr="")
        return subprocess.CompletedProcess(args, 0, stdout="{}", stderr="")

    monkeypatch.setattr(bf, "load_adopter_config", lambda _r: {})
    monkeypatch.setattr(bf, "gh_run", fake_gh_run)
    _patch_gate_checks(bf, monkeypatch, auth_ok=True, repo_ok=True, map_ok=True)

    # --json: the flag is carried.
    monkeypatch.setattr(
        sys, "argv",
        ["back-fill.py", "--capability-root", str(cap), "--limit", "2", "--json"],
    )
    assert bf.main() == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["truncated"] is True

    # human report: a loud warning line is emitted.
    monkeypatch.setattr(
        sys, "argv", ["back-fill.py", "--capability-root", str(cap), "--limit", "2"]
    )
    assert bf.main() == 0
    out = capsys.readouterr().out
    assert "TRUNCATED" in out
    assert "--limit" in out


def test_no_truncation_flag_when_below_limit(bf, tmp_path, monkeypatch, capsys) -> None:
    cap = _cap_root_with_hooks(tmp_path, MILESTONE_ONLY_HOOKS)

    def fake_gh_run(args, config, **kwargs):
        if args[:3] == ["gh", "issue", "list"]:
            return subprocess.CompletedProcess(
                args, 0,
                stdout=json.dumps([{"number": 1, "title": "one", "milestone": None}]),
                stderr="")
        if args[:3] == ["gh", "repo", "view"]:
            return subprocess.CompletedProcess(
                args, 0, stdout=json.dumps({"nameWithOwner": TARGET_REPO}), stderr="")
        return subprocess.CompletedProcess(args, 0, stdout="{}", stderr="")

    monkeypatch.setattr(bf, "load_adopter_config", lambda _r: {})
    monkeypatch.setattr(bf, "gh_run", fake_gh_run)
    _patch_gate_checks(bf, monkeypatch, auth_ok=True, repo_ok=True, map_ok=True)
    monkeypatch.setattr(
        sys, "argv",
        ["back-fill.py", "--capability-root", str(cap), "--limit", "500", "--json"],
    )
    assert bf.main() == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["truncated"] is False


# ----- G2: the hook→back-fill coupling is surfaced in the report ------


def test_report_header_surfaces_hook_coupling_scope_boundary(
    bf, tmp_path, monkeypatch, capsys
) -> None:
    """The report header states the undeclared semantic: each `after_create_issue`
    hook of a covered kind is treated as a corpus-wide back-fill intent, and
    separating go-forward-default from retroactive back-fill is not yet expressible
    (DEC-037 §2 — the report is the gate; make acceptance informed)."""
    cap = _cap_root_with_hooks(tmp_path, MILESTONE_ONLY_HOOKS)

    def fake_gh_run(args, config, **kwargs):
        if args[:3] == ["gh", "issue", "list"]:
            return subprocess.CompletedProcess(
                args, 0,
                stdout=json.dumps([{"number": 1, "title": "one", "milestone": None}]),
                stderr="")
        if args[:3] == ["gh", "repo", "view"]:
            return subprocess.CompletedProcess(
                args, 0, stdout=json.dumps({"nameWithOwner": TARGET_REPO}), stderr="")
        return subprocess.CompletedProcess(args, 0, stdout="{}", stderr="")

    monkeypatch.setattr(bf, "load_adopter_config", lambda _r: {})
    monkeypatch.setattr(bf, "gh_run", fake_gh_run)
    _patch_gate_checks(bf, monkeypatch, auth_ok=True, repo_ok=True, map_ok=True)
    monkeypatch.setattr(sys, "argv", ["back-fill.py", "--capability-root", str(cap)])

    assert bf.main() == 0
    out = capsys.readouterr().out
    assert "corpus-wide" in out.lower()
    assert "go-forward" in out.lower()


# ----- the plan document (T2b seam) ----------------------------------


def test_plan_document_carries_argv_citation_and_prediction(bf) -> None:
    """The machine-stable plan T2b consumes carries the exact argv, the citation,
    the observed value, the prediction, and the truncation flag per the plan."""
    intents = [bf.BackFillIntent(kind="assign-milestone", citation="cite-me", milestone_title="M1")]
    proposed = [
        bf.ProposedChange(
            issue_number=3, issue_title="t", kind="assign-milestone",
            citation="cite-me",
            argv=["gh", "issue", "edit", "3", "--milestone", "M1"],
            observed=None, prediction="would-write",
        )
    ]
    gate = bf.GateResult(passed=True, checks=[("`gh` authenticated", "ok", "ok")])
    doc = bf._plan_document(intents, proposed, gate, truncated=False)
    # Round-trips through JSON (machine-stable).
    doc = json.loads(json.dumps(doc))
    assert doc["schema_version"] == bf.PLAN_SCHEMA_VERSION
    assert doc["truncated"] is False
    assert doc["residual_pre_check"]["passed"] is True
    assert doc["intents"][0]["citation"] == "cite-me"
    entry = doc["proposed"][0]
    assert entry["argv"] == ["gh", "issue", "edit", "3", "--milestone", "M1"]
    assert entry["citation"] == "cite-me"
    assert entry["prediction"] == "would-write"


# ----- NO write executes (G4: tightened, seam-level patch) ------------


def _serve_reads(args):
    """Serve the READ gh calls the report makes; return None for anything else so
    the caller can decide. Repo view, board view, issue list, and the item-id
    graphql READ query are the only legitimate calls."""
    if args[:3] == ["gh", "repo", "view"]:
        return subprocess.CompletedProcess(
            args, 0, stdout=json.dumps({"nameWithOwner": TARGET_REPO}), stderr="")
    if args[:4] == ["gh", "project", "view", "7"]:
        return subprocess.CompletedProcess(
            args, 0, stdout=json.dumps({"id": "PROJ_NODE"}), stderr="")
    if args[:3] == ["gh", "issue", "list"]:
        return subprocess.CompletedProcess(
            args, 0,
            stdout=json.dumps([
                {"number": 1, "title": "one", "milestone": None},
                {"number": 2, "title": "two", "milestone": {"title": "Milestone 1"}},
            ]),
            stderr="")
    if args[:3] == ["gh", "api", "graphql"]:
        return subprocess.CompletedProcess(
            args, 0,
            stdout=json.dumps({"data": {"node": {"items": {
                "pageInfo": {"hasNextPage": False, "endCursor": None},
                "nodes": [{"id": "ITEM_1", "content": {
                    "number": 1, "repository": {"nameWithOwner": TARGET_REPO}}}],
            }}}}),
            stderr="")
    return None


def _is_mutating_call(call: list[str]) -> bool:
    """Recognise a MUTATING gh call among those the report could conceivably issue.

    Covers the `gh` subcommand mutations (item-edit / item-add / issue edit /
    create / comment / label) AND — crucially — a graphql MUTATION. The earlier
    test blanket-exempted ALL `gh api graphql` calls, which would let an
    `updateProjectV2ItemFieldValue` MUTATION (the exact GraphQL write ADR-031
    covers) escape. Here a graphql call is exempt only if its query body is a READ
    (no mutation keyword); any mutation keyword in the body makes it mutating."""
    joined = " ".join(call)
    subcommand_mutations = [
        "item-edit", "item-add",
        "issue edit", "issue create", "issue comment",
        "label create", "label edit", "label delete",
    ]
    if any(m in joined for m in subcommand_mutations):
        return True
    if call[:3] == ["gh", "api", "graphql"]:
        # Inspect the query body: a read `query(...)` is fine; a `mutation { ... }`
        # or any GraphQL mutation field (e.g. updateProjectV2ItemFieldValue) is a
        # write and is NOT exempt.
        body = joined.lower()
        mutation_markers = ("mutation", "updateprojectv2", "additem", "createissue")
        return any(marker in body for marker in mutation_markers)
    return False


def test_no_mutating_gh_call_is_ever_issued(bf, tmp_path, monkeypatch) -> None:
    """The hard boundary (DEC-037 §2 / task T2a): running the report end-to-end
    issues only READ gh calls — never a mutating one. The catch is at the seam BOTH
    modules share (`_lib.gh.gh_run`), not just `bf.gh_run`: a write driven through
    `substrate_writes.write_*` calls `gh_run` via that module's OWN import binding,
    so patching only `bf.gh_run` would let it escape the `issued` list."""
    cap = _cap_root_with_hooks(tmp_path, AUJ_HOOKS, map_yaml=AUJ_MAP_WS_DEFAULT)

    issued: list[list[str]] = []

    def fake_gh_run(args, config=None, **kwargs):
        issued.append(list(args))
        served = _serve_reads(args)
        if served is not None:
            return served
        return subprocess.CompletedProcess(args, 0, stdout="{}", stderr="")

    # Patch at the SOURCE module both back-fill and substrate_writes import from,
    # so ANY reachable write (including one through substrate_writes._execute) is
    # captured — not only calls through back-fill's own binding.
    sys.path.insert(0, str(LIB_DIR))
    import gh as gh_source  # the `_lib.gh` module, imported as top-level `gh`
    monkeypatch.setattr(gh_source, "gh_run", fake_gh_run)
    monkeypatch.setattr(bf, "gh_run", fake_gh_run)
    # substrate_writes binds `gh_run` at import time; rebind its name too.
    from _lib import substrate_writes
    monkeypatch.setattr(substrate_writes, "gh_run", fake_gh_run)

    monkeypatch.setattr(bf, "load_adopter_config", lambda _r: dict(AUJ_BOARD_CONFIG))
    _patch_gate_checks(bf, monkeypatch, auth_ok=True, repo_ok=True, map_ok=True)
    monkeypatch.setattr(
        sys, "argv", ["back-fill.py", "--capability-root", str(cap), "--json"]
    )

    rc = bf.main()
    assert rc == 0

    offenders = [call for call in issued if _is_mutating_call(call)]
    assert not offenders, f"the report half issued mutating gh call(s): {offenders}"


def test_no_write_detector_catches_a_graphql_mutation(bf) -> None:
    """Mutation-proof for G4's tightened assertion: the detector must FLAG a
    `gh api graphql` call whose body is an `updateProjectV2ItemFieldValue` mutation
    (the exact GraphQL write form ADR-031 covers) — the old blanket graphql
    exemption would have let it pass."""
    read_call = [
        "gh", "api", "graphql", "-f",
        "query=query($project: ID!) { node(id: $project) { id } }",
    ]
    mutation_call = [
        "gh", "api", "graphql", "-f",
        "query=mutation { updateProjectV2ItemFieldValue(input: {}) "
        "{ clientMutationId } }",
    ]
    assert _is_mutating_call(read_call) is False
    assert _is_mutating_call(mutation_call) is True


def test_main_refuses_with_exit_2_when_gate_fails(bf, tmp_path, monkeypatch, capsys) -> None:
    """When the residual gate fails, main returns 2 and produces NO report — the
    refusal is the whole output."""
    cap = _cap_root_with_hooks(tmp_path, AUJ_HOOKS)

    def fake_gh_run(args, config, **kwargs):
        return subprocess.CompletedProcess(args, 0, stdout="{}", stderr="")

    monkeypatch.setattr(bf, "gh_run", fake_gh_run)
    _patch_gate_checks(bf, monkeypatch, auth_ok=False, repo_ok=True)
    monkeypatch.setattr(sys, "argv", ["back-fill.py", "--capability-root", str(cap)])

    rc = bf.main()
    assert rc == 2
    err = capsys.readouterr().err
    assert "REFUSED" in err
