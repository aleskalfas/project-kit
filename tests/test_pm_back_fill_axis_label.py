"""Corpus back-fill — the `set-axis-label` change kind (the repair path, #818).

The back-fill ceremony was named as the repair for the corpus damaged by the
carriage bug ([project-management:DEC-051-axis-carriage-activation]), and it could
not perform it: its two change kinds write a Projects-v2 field value and a
milestone, and nothing in it could write a classification LABEL. The affected
shape is an adopter with a configured board whose map binds `priority` (or
`workstream`) to their own labels — during the broken window the writer honoured
the board flag and wrote no label, nothing wrote the board field, and the value
landed on NEITHER substrate. Once the presence gates resolve through the seam,
every such issue is refused for a missing label, so the repair has to exist before
the strict reader lands.

These tests pin the properties that make the repair safe rather than a second
mass-mutation hazard:

  * **the label comes from the write seam** — `axis_labels.resolve_write` under the
    adopter's map (`P0`), never the kit's own `priority:High` constructor;
  * **a value with no `remap` entry is UNRESOLVABLE and skipped** — reported, and
    emphatically not written as the raw kit value, which would create a label the
    adopter does not manage;
  * **candidacy is by CARRIAGE**, asked of `_lib/axis_carriage` — a board-carried
    axis belongs to the existing `set-board-field` kind, and a `title` / `derive` /
    `degrade` axis has no label to write at all;
  * **it fills gaps, never overwrites** — an issue already carrying a value on the
    axis is not proposed, whether that value is the target or one a human chose;
  * **idempotent** — a re-run over a repaired corpus plans nothing;
  * **the plan names the resolved label per issue**, so propose-and-cite is
    reviewable before anything is written;
  * **the residual pre-check gate applies** exactly as it does to the other kinds;
  * **the emitted script's guard fails CLOSED** — deliberately NOT the fail-open
    shape the two older fragments carry (#816).

The gh reads are stubbed; the gate's residual probes are stubbed at the pre-check
module functions the gate reuses.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
LIB_DIR = SCRIPTS_DIR / "_lib"
SCRIPT = SCRIPTS_DIR / "back-fill.py"

KIND = "set-axis-label"
TARGET_REPO = "ai-platform-incubation/spyre"

# The reported adopter's configuration (#708): a board IS configured, and the map
# binds `priority` to the repo's own labels. Carriage must answer "the adopter's
# labels" for that axis — which is what makes it a candidate here at all.
BOARD_CONFIG = {
    "has_projects_v2_board": True,
    "projects_v2_board_id": 7,
    "gh": {"default_owner": "ai-platform-incubation"},
}
NO_BOARD_CONFIG: dict = {}

NO_HOOKS = "schema_version: 1\nhooks: {}\n"

# `priority` bound to the adopter's own labels, with a declared default — the
# declaration point DEC-037 §3 names for a label-carried axis.
LABEL_BOUND_MAP = """\
schema_version: 1
axes:
  priority:
    label:
      remap:
        High: P0
        Medium: P1
    default: High
"""

# Same binding, but the declared default has no entry in the remap: the fourth
# ADR-026 arm (value-unresolvable within a bound axis).
UNRESOLVABLE_DEFAULT_MAP = """\
schema_version: 1
axes:
  priority:
    label:
      remap:
        Medium: P1
    default: High
"""

# The axis lives on the board — the existing `set-board-field` kind's job.
BOARD_BOUND_MAP = """\
schema_version: 1
axes:
  priority:
    board: true
    default: High
"""

# The axis is carried in the TITLE. `resolve_write` would return the PREFIX string
# (`[Task]`), which a naive label writer applies as a `gh --label` the tracker does
# not have (#454) — so this axis must never reach resolution here.
TITLE_BOUND_MAP = """\
schema_version: 1
axes:
  type:
    title-prefix:
      remap:
        task: "[Task]"
    default: task
"""

# A present map that says nothing about `priority`, with no board: the axis
# degrades (ADR-026's absent-≡-unsupported rule). `type` IS bound and defaulted, so
# the same map exercises both arms — one axis skipped, one resolved.
DEGRADED_MAP = """\
schema_version: 1
axes:
  type:
    label:
      remap:
        task: Chore
    default: task
"""


# ----- module fixtures ------------------------------------------------


@pytest.fixture(scope="module")
def bf():
    sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location("pm_bf_axis_label_under_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_bf_axis_label_under_test"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def apply_mod(bf):
    """The apply engine, reached through the driver so both halves share one
    module instance (a second file-path load would give the tests a different
    `PlannedChange` class than `main()` builds)."""
    return bf.back_fill_apply


@pytest.fixture(scope="module")
def axis_labels(bf):
    return bf.axis_labels


# ----- staging helpers ------------------------------------------------


@dataclass
class _Check:
    label: str
    status: str
    detail: str
    remediation: str | None = None


def _mark_bootstrapped(cap_root: Path) -> None:
    project = cap_root / "project"
    project.mkdir(parents=True, exist_ok=True)
    config = project / "config.yaml"
    if not config.is_file():
        config.write_text(
            "schema_version: 1\ndefault_branch: main\nworkstreams: []\n",
            encoding="utf-8",
        )
    (project / "bootstrap-stamp.yaml").write_text(
        "schema_version: 1\n"
        "bootstrap:\n"
        "  completed_at: '2026-01-01T00:00:00+00:00'\n"
        "  capability_version: 0.0.0-test\n"
        "  by: bootstrap\n"
        "  repo:\n",
        encoding="utf-8",
    )


def _cap_root(tmp_path: Path, *, map_yaml: str, hooks_yaml: str = NO_HOOKS) -> Path:
    cap = tmp_path / ".pkit" / "capabilities" / "project-management"
    (cap / "project").mkdir(parents=True, exist_ok=True)
    (cap / "project" / "hooks.yaml").write_text(hooks_yaml, encoding="utf-8")
    (cap / "project" / "substrate-map.yaml").write_text(map_yaml, encoding="utf-8")
    _mark_bootstrapped(cap)
    return cap


def _load_map(bf, cap: Path):
    return bf.axis_labels.load_substrate_map(cap)


def _issue(number: int, *label_names: str) -> dict:
    return {
        "number": number,
        "title": f"issue {number}",
        "milestone": None,
        "labels": [{"name": name} for name in label_names],
    }


def _patch_gate_checks(bf, monkeypatch, *, auth_ok=True, repo_ok=True, map_ok=True):
    """Stub the residual gate's three probes at the pre-check module it reuses."""
    class _FakePreCheck:
        @staticmethod
        def _check_gh_auth():
            return _Check("gh auth", "ok" if auth_ok else "fail", "auth")

        @staticmethod
        def _check_repo_accessible():
            return _Check("repo accessible", "ok" if repo_ok else "fail", "repo")

        @staticmethod
        def _check_substrate_map_parse(_root):
            return _Check("substrate-map parse", "ok" if map_ok else "fail", "map")

    monkeypatch.setattr(bf, "_load_pre_check_module", lambda _root: _FakePreCheck)


# ============================================================================
# Intent resolution — carriage scoping, the seam, and the unresolvable value
# ============================================================================


def test_label_bound_axis_under_a_board_is_a_candidate(bf, tmp_path) -> None:
    """The reported configuration: board flag ON, map binds `priority` to the
    adopter's own labels. Carriage answers "their labels", so the axis IS a
    candidate — the whole point of the repair."""
    cap = _cap_root(tmp_path, map_yaml=LABEL_BOUND_MAP)
    intents, errors = bf._resolve_label_intents(_load_map(bf, cap), BOARD_CONFIG)
    assert errors == []
    assert [i.kind for i in intents] == [KIND]
    assert intents[0].axis == "priority"


def test_the_written_label_comes_from_the_write_seam_not_the_kit_constructor(
    bf, tmp_path, axis_labels
) -> None:
    """The load-bearing property: the label is the adopter's `P0`, resolved by
    `resolve_write` — never the kit's own `priority:High`. A board adopter's
    remapped label is theirs, and the kit must not invent one."""
    cap = _cap_root(tmp_path, map_yaml=LABEL_BOUND_MAP)
    smap = _load_map(bf, cap)
    [intent] = bf._resolve_label_intents(smap, BOARD_CONFIG)[0]
    assert intent.label_value == axis_labels.resolve_write("priority", "High", smap)
    assert intent.label_value == "P0"
    # The kit's own constructor is NOT what was used, and its output never appears.
    assert intent.label_value != axis_labels.label("priority", "High")
    # Both values are carried so the report can show what was asked for AND what
    # will land on the tracker.
    assert intent.axis_value == "High"


def test_value_with_no_remap_entry_is_unresolvable_and_skipped(bf, tmp_path) -> None:
    """The fourth ADR-026 arm: the axis is bound but the declared default has no
    `remap` entry. NO intent is produced, an error is reported, and — the part
    that matters — the raw kit value is never substituted in."""
    cap = _cap_root(tmp_path, map_yaml=UNRESOLVABLE_DEFAULT_MAP)
    intents, errors = bf._resolve_label_intents(_load_map(bf, cap), BOARD_CONFIG)
    assert intents == []
    assert len(errors) == 1
    assert "remap" in errors[0] and "High" in errors[0]
    # The refusal explains itself in the adopter's terms and never leaks the kit
    # label as something that WOULD be written.
    assert "priority:High" not in errors[0].replace("`priority:High` label", "")


def test_board_carried_axis_is_not_a_candidate(bf, tmp_path) -> None:
    """Scoping by carriage: a `board:`-bound axis belongs to the existing
    `set-board-field` kind. Proposing a label for it would write the value to a
    second substrate the adopter did not ask for."""
    cap = _cap_root(tmp_path, map_yaml=BOARD_BOUND_MAP)
    intents, errors = bf._resolve_label_intents(_load_map(bf, cap), BOARD_CONFIG)
    assert intents == []
    # Not an error either — the axis is SERVED, just not by this kind.
    assert errors == []


def test_title_carried_axis_is_not_a_candidate(bf, tmp_path) -> None:
    """A `title-prefix` axis has no label. Skipping BEFORE resolution is what makes
    it safe: `resolve_write` returns the PREFIX string (`[Task]`), which a label
    writer would apply as a `gh --label` the tracker does not have (#454)."""
    cap = _cap_root(tmp_path, map_yaml=TITLE_BOUND_MAP)
    intents, errors = bf._resolve_label_intents(_load_map(bf, cap), BOARD_CONFIG)
    assert intents == [] and errors == []


def test_degraded_axis_is_not_a_candidate(bf, tmp_path) -> None:
    """An axis absent from a present map with no board degrades — nothing carries
    it by the adopter's own declaration, so there is no label to write."""
    cap = _cap_root(tmp_path, map_yaml=DEGRADED_MAP)
    intents, _errors = bf._resolve_label_intents(_load_map(bf, cap), NO_BOARD_CONFIG)
    assert [i.axis for i in intents] == ["type"]  # `type` is bound; `priority` is not


def test_greenfield_declares_no_default_so_resolves_no_intent(bf) -> None:
    """With no map every axis is kit-label-carried — a candidate by the rule — but
    there is no `default:` to declare without a map, so nothing resolves. The kit
    does not invent a corpus-wide value it was never given."""
    intents, errors = bf._resolve_label_intents(None, NO_BOARD_CONFIG)
    assert intents == [] and errors == []


def test_state_is_not_back_fillable(bf) -> None:
    """`state` is derived from the tracker's own lifecycle, so seeding a uniform
    value across a historical corpus would contradict the substrate rather than
    repair a gap in it. It is excluded by construction."""
    assert "state" not in bf.LABEL_BACK_FILL_AXES
    assert set(bf.LABEL_BACK_FILL_AXES) == {"type", "priority", "workstream"}


def test_citation_names_the_declaration_the_substrate_and_the_rule(bf, tmp_path) -> None:
    """Propose-and-cite: the human must see WHY the change is proposed, WHERE the
    axis lives, and that only gaps are filled."""
    cap = _cap_root(tmp_path, map_yaml=LABEL_BOUND_MAP)
    [intent] = bf._resolve_label_intents(_load_map(bf, cap), BOARD_CONFIG)[0]
    cite = bf._full_citation(intent)
    assert "substrate-map" in cite and "default" in cite
    assert "P0" in cite and "High" in cite
    assert "carry no `priority` value" in cite


# ============================================================================
# Enumeration — fill the gap, never overwrite; idempotency
# ============================================================================


def _one_intent(bf, cap: Path, config=BOARD_CONFIG):
    smap = _load_map(bf, cap)
    intents, _ = bf._resolve_label_intents(smap, config)
    return intents, smap


def test_issue_with_no_value_on_the_axis_is_proposed(bf, tmp_path) -> None:
    cap = _cap_root(tmp_path, map_yaml=LABEL_BOUND_MAP)
    intents, smap = _one_intent(bf, cap)
    proposed = bf._build_proposed_changes(
        intents, [_issue(1, "bug")], {}, None, TARGET_REPO, substrate_map=smap
    )
    [change] = proposed
    assert change.kind == KIND
    assert change.axis == "priority"
    assert change.prediction == "would-write"
    # The plan NAMES the resolved label for this issue — the reviewable artifact.
    assert change.argv == ["gh", "issue", "edit", "1", "--add-label", "P0"]
    # It proposes into a CONFIRMED gap, which is what lets the apply-time predicate
    # treat any value appearing later as drift.
    assert change.observed is None


def test_issue_already_carrying_the_adopters_label_is_not_proposed(bf, tmp_path) -> None:
    """The already-has-a-value skip, in the shape that matters: the adopter's own
    label carries no `priority:` prefix, so a prefix-only search would read this
    issue as a gap and give a single-valued axis a second value."""
    cap = _cap_root(tmp_path, map_yaml=LABEL_BOUND_MAP)
    intents, smap = _one_intent(bf, cap)
    proposed = bf._build_proposed_changes(
        intents, [_issue(1, "P1"), _issue(2, "P0")], {}, None, TARGET_REPO,
        substrate_map=smap,
    )
    # #1 carries a DIFFERENT value (a human's choice — not ours to normalise) and
    # #2 already carries the target. Both are left alone.
    assert proposed == []


def test_issue_carrying_a_stale_kit_label_is_not_proposed(bf, tmp_path) -> None:
    """A repo mid-adoption can hold a kit `priority:High` beside the adopter's own
    vocabulary. `carried_labels` unions both, so that issue has a value too."""
    cap = _cap_root(tmp_path, map_yaml=LABEL_BOUND_MAP)
    intents, smap = _one_intent(bf, cap)
    proposed = bf._build_proposed_changes(
        intents, [_issue(1, "priority:High")], {}, None, TARGET_REPO, substrate_map=smap
    )
    assert proposed == []


def test_rerun_over_a_repaired_corpus_plans_nothing(bf, tmp_path) -> None:
    """Idempotency at ENUMERATION, not as a write predicted and then skipped: once
    the corpus carries the label, the re-run has no gap to propose into."""
    cap = _cap_root(tmp_path, map_yaml=LABEL_BOUND_MAP)
    intents, smap = _one_intent(bf, cap)
    corpus = [_issue(1), _issue(2)]

    first = bf._build_proposed_changes(
        intents, corpus, {}, None, TARGET_REPO, substrate_map=smap
    )
    assert len(first) == 2

    repaired = [_issue(1, "P0"), _issue(2, "P0")]
    second = bf._build_proposed_changes(
        intents, repaired, {}, None, TARGET_REPO, substrate_map=smap
    )
    assert second == []


def test_a_mis_shaped_labels_block_reads_as_no_labels(bf, tmp_path) -> None:
    """An enumeration that could not read the labels proposes a write it will then
    re-validate — the apply-time read fails closed, so the cost is a declined
    proposal rather than a write against an unread issue."""
    cap = _cap_root(tmp_path, map_yaml=LABEL_BOUND_MAP)
    intents, smap = _one_intent(bf, cap)
    issue = {"number": 9, "title": "nine", "milestone": None}  # no `labels` key
    proposed = bf._build_proposed_changes(
        intents, [issue], {}, None, TARGET_REPO, substrate_map=smap
    )
    assert [c.issue_number for c in proposed] == [9]


# ============================================================================
# The plan document + the human report
# ============================================================================


def test_plan_carries_the_axis_and_the_resolved_label(bf, tmp_path) -> None:
    cap = _cap_root(tmp_path, map_yaml=LABEL_BOUND_MAP)
    intents, smap = _one_intent(bf, cap)
    proposed = bf._build_proposed_changes(
        intents, [_issue(1)], {}, None, TARGET_REPO, substrate_map=smap
    )
    gate = bf.GateResult(passed=True, checks=[])
    plan = bf._plan_document(intents, proposed, gate, truncated=False)
    [intent_dict] = plan["intents"]
    assert intent_dict["axis"] == "priority"
    assert intent_dict["axis_value"] == "High"
    assert intent_dict["label_value"] == "P0"
    assert intent_dict["carrier_labels"] == ["P0", "P1"]
    assert plan["proposed"][0]["axis"] == "priority"


def test_plan_carries_unresolvable_intent_errors(bf, tmp_path) -> None:
    """A value the back-fill declined to write is exactly what a `--json` consumer
    needs to see; it had no way to learn of it before."""
    cap = _cap_root(tmp_path, map_yaml=UNRESOLVABLE_DEFAULT_MAP)
    _intents, errors = bf._resolve_label_intents(_load_map(bf, cap), BOARD_CONFIG)
    gate = bf.GateResult(passed=True, checks=[])
    plan = bf._plan_document([], [], gate, truncated=False, intent_errors=errors)
    assert len(plan["intent_errors"]) == 1
    assert "remap" in plan["intent_errors"][0]


def test_report_names_the_resolved_label_per_issue(bf, tmp_path, capsys) -> None:
    """Propose-and-cite is reviewable BEFORE anything is written: the per-issue line
    shows the exact write, including the label that will land."""
    cap = _cap_root(tmp_path, map_yaml=LABEL_BOUND_MAP)
    intents, smap = _one_intent(bf, cap)
    proposed = bf._build_proposed_changes(
        intents, [_issue(1), _issue(2)], {}, None, TARGET_REPO, substrate_map=smap
    )
    gate = bf.GateResult(passed=True, checks=[])
    bf._print_report_from_plan(bf._plan_document(intents, proposed, gate, truncated=False))
    out = capsys.readouterr().out
    assert "gh issue edit 1 --add-label P0" in out
    assert "gh issue edit 2 --add-label P0" in out
    assert f"{KIND} (priority)" in out
    # The intent line shows the methodology value AND the substrate value.
    assert "'High' → label 'P0'" in out


# ============================================================================
# The residual pre-check gate applies to this kind too
# ============================================================================


def test_residual_gate_refuses_a_label_only_back_fill(bf, tmp_path, monkeypatch) -> None:
    """The gate is global, so it covers the new kind unchanged: a failing residual
    probe refuses the whole operation before any enumeration."""
    cap = _cap_root(tmp_path, map_yaml=LABEL_BOUND_MAP)
    _patch_gate_checks(bf, monkeypatch, auth_ok=False)
    monkeypatch.setattr(bf, "load_adopter_config", lambda _r: dict(BOARD_CONFIG))
    monkeypatch.setattr(
        bf, "gh_run",
        lambda *a, **k: pytest.fail("the gate must refuse before any gh read"),
    )
    args = bf.argparse.Namespace(json=False, apply=False, emit_script=False,
                                 limit=500, state="all")
    plan, gate_failed = bf._derive_plan(cap, dict(BOARD_CONFIG), args)
    assert gate_failed is True and plan is None


def test_label_only_back_fill_does_not_gate_on_the_board(bf, tmp_path, monkeypatch) -> None:
    """The fourth residual member is a CONJUNCTION over a declared field intent. A
    label-only back-fill declares none, so an unresolvable board is irrelevant to
    it — the same way a milestone-only back-fill is unaffected."""
    cap = _cap_root(tmp_path, map_yaml=LABEL_BOUND_MAP)
    _patch_gate_checks(bf, monkeypatch)
    monkeypatch.setattr(
        bf, "_resolve_project_node_id",
        lambda _c: pytest.fail("a label-only back-fill must not resolve the board"),
    )
    monkeypatch.setattr(bf, "_enumerate_corpus", lambda *a, **k: [_issue(1)])
    monkeypatch.setattr(bf, "_resolve_repo_name_with_owner", lambda _c: TARGET_REPO)
    args = bf.argparse.Namespace(json=True, apply=False, emit_script=False,
                                 limit=500, state="all")
    plan, gate_failed = bf._derive_plan(cap, dict(BOARD_CONFIG), args)
    assert gate_failed is False
    assert [c["kind"] for c in plan["proposed"]] == [KIND]


# ============================================================================
# Apply half — the drift guard, the write, the fail-closed read
# ============================================================================


def _planned(apply_mod, *, target="P0", observed=None, argv=("gh",), axis="priority"):
    return apply_mod.PlannedChange(
        issue_number=1, kind=KIND, target=target, observed=observed,
        argv=list(argv) if argv is not None else None, axis=axis,
    )


def test_classify_writes_into_a_confirmed_gap(apply_mod) -> None:
    fresh = apply_mod.FreshState(current=None, read_ok=True)
    assert apply_mod.classify_change(_planned(apply_mod), fresh) is (
        apply_mod.Disposition.WOULD_WRITE
    )


def test_classify_skips_when_the_target_appeared_since_plan_time(apply_mod) -> None:
    """A human labelled it with exactly the target during the review window: already
    done, idempotent, nothing to fight over."""
    fresh = apply_mod.FreshState(current="P0", read_ok=True)
    assert apply_mod.classify_change(_planned(apply_mod), fresh) is (
        apply_mod.Disposition.ALREADY_SATISFIED
    )


def test_classify_skips_when_another_value_appeared_since_plan_time(apply_mod) -> None:
    """The no-overwrite rule surviving the report→apply window: the existing drift
    guard yields it with no second predicate, because the plan's `observed` is None
    for every proposed label change."""
    fresh = apply_mod.FreshState(current="P1", read_ok=True)
    assert apply_mod.classify_change(_planned(apply_mod), fresh) is (
        apply_mod.Disposition.DRIFTED
    )


def test_classify_fails_closed_on_an_indeterminate_read(apply_mod) -> None:
    fresh = apply_mod.FreshState(current=None, read_ok=False)
    assert apply_mod.classify_change(_planned(apply_mod), fresh) is (
        apply_mod.Disposition.DRIFTED
    )


def test_apply_writes_the_resolved_label_through_one_constructor(
    apply_mod, monkeypatch
) -> None:
    issued: list[list[str]] = []

    def fake_gh_run(args, config=None, **kwargs):
        issued.append(list(args))
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(apply_mod, "gh_run", fake_gh_run)
    records = apply_mod.apply_plan(
        [_planned(apply_mod, argv=["gh", "issue", "edit", "1", "--add-label", "P0"])],
        {},
        read_fresh=lambda _c: apply_mod.FreshState(current=None, read_ok=True),
    )
    assert [r.outcome for r in records] == [apply_mod.ApplyOutcome.APPLIED]
    assert issued == [["gh", "issue", "edit", "1", "--add-label", "P0"]]
    # The executed argv IS the one construction point's output — the plan and the
    # apply cannot desync.
    assert issued[0] == apply_mod.axis_label_args(issue_number=1, label="P0")


def test_apply_does_not_write_when_a_value_appeared(apply_mod, monkeypatch) -> None:
    monkeypatch.setattr(
        apply_mod, "gh_run",
        lambda *a, **k: pytest.fail("a drifted change must not be written"),
    )
    records = apply_mod.apply_plan(
        [_planned(apply_mod)],
        {},
        read_fresh=lambda _c: apply_mod.FreshState(current="P1", read_ok=True),
    )
    assert [r.outcome for r in records] == [apply_mod.ApplyOutcome.SKIPPED_DRIFT]


def test_a_failed_write_is_audited_and_exits_nonzero(apply_mod, monkeypatch) -> None:
    monkeypatch.setattr(
        apply_mod, "gh_run",
        lambda *a, **k: subprocess.CompletedProcess(a[0], 1, stdout="", stderr="nope"),
    )
    records = apply_mod.apply_plan(
        [_planned(apply_mod)],
        {},
        read_fresh=lambda _c: apply_mod.FreshState(current=None, read_ok=True),
    )
    assert [r.outcome for r in records] == [apply_mod.ApplyOutcome.FAILED]
    assert "nope" in records[0].detail
    assert apply_mod.exit_code_for(apply_mod.summarise(records)) == 1


# ----- the apply-time fresh read --------------------------------------


def _fresh_read(bf, monkeypatch, smap, *, returncode=0, stdout="{}"):
    monkeypatch.setattr(
        bf, "gh_run",
        lambda *a, **k: subprocess.CompletedProcess(a[0], returncode, stdout, ""),
    )
    change = bf.back_fill_apply.PlannedChange(
        issue_number=1, kind=KIND, target="P0", observed=None,
        argv=["gh"], axis="priority",
    )
    return bf._read_current_axis_label(change, {}, smap)


def test_fresh_read_recognises_the_adopters_own_label(bf, tmp_path, monkeypatch) -> None:
    cap = _cap_root(tmp_path, map_yaml=LABEL_BOUND_MAP)
    state = _fresh_read(
        bf, monkeypatch, _load_map(bf, cap),
        stdout=json.dumps({"labels": [{"name": "bug"}, {"name": "P1"}]}),
    )
    assert state.read_ok is True and state.current == "P1"


def test_fresh_read_reports_a_confirmed_gap(bf, tmp_path, monkeypatch) -> None:
    """An EMPTY label list is a genuine "no value" and must read as a confirmed gap
    — otherwise the repair could never write anything."""
    cap = _cap_root(tmp_path, map_yaml=LABEL_BOUND_MAP)
    state = _fresh_read(bf, monkeypatch, _load_map(bf, cap),
                        stdout=json.dumps({"labels": []}))
    assert state.read_ok is True and state.current is None


def test_fresh_read_fails_closed_on_gh_failure(bf, tmp_path, monkeypatch) -> None:
    cap = _cap_root(tmp_path, map_yaml=LABEL_BOUND_MAP)
    state = _fresh_read(bf, monkeypatch, _load_map(bf, cap), returncode=1)
    assert state.read_ok is False


def test_fresh_read_fails_closed_on_an_absent_labels_block(
    bf, tmp_path, monkeypatch
) -> None:
    """An ABSENT `labels` key is a read that did not answer. Treating it as a gap is
    the fail-open mistake — it would write into an issue we never saw."""
    cap = _cap_root(tmp_path, map_yaml=LABEL_BOUND_MAP)
    state = _fresh_read(bf, monkeypatch, _load_map(bf, cap), stdout=json.dumps({}))
    assert state.read_ok is False


def test_fresh_read_fails_closed_on_unparseable_output(bf, tmp_path, monkeypatch) -> None:
    cap = _cap_root(tmp_path, map_yaml=LABEL_BOUND_MAP)
    state = _fresh_read(bf, monkeypatch, _load_map(bf, cap), stdout="not json")
    assert state.read_ok is False


# ============================================================================
# Saved-plan reconstruction
# ============================================================================


def _label_intent_dict(axis: str, value: str, label: str, carriers: list[str]) -> dict:
    return {
        "kind": KIND, "citation": f"{axis} cite",
        "field_id": None, "single_select_option_id": None, "text_value": None,
        "milestone_title": None,
        "axis": axis, "axis_value": value, "label_value": label,
        "carrier_labels": carriers,
    }


def _label_entry(number: int, axis: str, label: str) -> dict:
    return {
        "issue_number": number, "issue_title": f"issue {number}", "kind": KIND,
        "citation": f"{axis} cite",
        "argv": ["gh", "issue", "edit", str(number), "--add-label", label],
        "observed": None, "prediction": "would-write", "blocked_reason": "",
        "axis": axis,
    }


def test_saved_plan_matches_each_axis_to_its_own_intent(apply_mod) -> None:
    """Two label intents on ONE kind: keying intents by kind alone would collapse
    them and write `priority`'s label for `workstream`'s change."""
    plan = {
        "schema_version": 1,
        "truncated": False,
        "residual_pre_check": {"passed": True, "checks": []},
        "intents": [
            _label_intent_dict("priority", "High", "P0", ["P0", "P1"]),
            _label_intent_dict("workstream", "Spyre", "team/spyre", ["team/spyre"]),
        ],
        "proposed": [
            _label_entry(1, "priority", "P0"),
            _label_entry(1, "workstream", "team/spyre"),
        ],
    }
    changes = apply_mod.planned_changes_from_plan(plan)
    assert [(c.axis, c.target) for c in changes] == [
        ("priority", "P0"), ("workstream", "team/spyre")
    ]
    assert changes[0].carrier_labels == ("P0", "P1")


def test_a_plan_saved_before_this_kind_still_reconstructs(apply_mod) -> None:
    """Backward compatibility, which is why the schema_version is not bumped: a
    two-kind plan carries no `axis` key and reconstructs exactly as before."""
    plan = {
        "schema_version": 1,
        "truncated": False,
        "residual_pre_check": {"passed": True, "checks": []},
        "intents": [{"kind": "assign-milestone", "citation": "c",
                     "milestone_title": "M1"}],
        "proposed": [{
            "issue_number": 1, "issue_title": "one", "kind": "assign-milestone",
            "citation": "c",
            "argv": ["gh", "issue", "edit", "1", "--milestone", "M1"],
            "observed": None, "prediction": "would-write", "blocked_reason": "",
        }],
    }
    [change] = apply_mod.planned_changes_from_plan(plan)
    assert change.target == "M1" and change.axis is None


# ============================================================================
# --emit-script — the guard FAILS CLOSED (deliberately not #816's shape)
# ============================================================================


def _emit(apply_mod, **kwargs) -> str:
    change = apply_mod.PlannedChange(
        issue_number=7, kind=KIND, target="P0", observed=None,
        argv=["gh", "issue", "edit", "7", "--add-label", "P0"],
        axis="priority", carrier_labels=("P0", "P1"),
        **kwargs,
    )
    return apply_mod.render_emit_script([change])


def test_emitted_guard_fails_closed_on_a_failed_reread(apply_mod) -> None:
    """The sibling defect (#816) is that the two older fragments treat an
    unreadable substrate as an unset one and write anyway. This one must not copy
    that shape: `if ! current=$(...)` separates a non-zero `gh` exit from a
    successful read that returned empty, which a bare `|| echo ""` collapses."""
    script = _emit(apply_mod)
    assert "if ! current=$(gh issue view 7 --json labels" in script
    assert "failing closed" in script
    assert "guard fails CLOSED" in script
    # And emphatically NOT the fail-open idiom.
    assert '--jq "..." 2>/dev/null || echo ""' not in script


def test_emitted_guard_skips_when_a_value_is_already_present(apply_mod) -> None:
    script = _emit(apply_mod)
    assert 'elif [ -n "$current" ]; then' in script
    assert "not overwriting" in script


def test_emitted_guard_recognises_the_adopters_vocabulary(apply_mod) -> None:
    """A static script cannot load the map, so the vocabulary travels in the plan.
    Without it the guard would be blind to exactly the adopter this repair is for —
    their labels carry no `priority:` prefix."""
    script = _emit(apply_mod)
    assert '. == "P0"' in script and '. == "P1"' in script
    assert 'startswith("priority:")' in script


def test_emitted_jq_matches_the_seams_own_vocabulary(apply_mod, bf, tmp_path) -> None:
    """The emitted vocabulary is the seam's, not a re-derivation: what the script
    treats as "a value for this axis" is what `carried_labels` treats as one."""
    cap = _cap_root(tmp_path, map_yaml=LABEL_BOUND_MAP)
    smap = _load_map(bf, cap)
    vocabulary = bf.axis_labels.axis_label_vocabulary("priority", smap)
    jq = apply_mod._axis_label_carrier_jq("priority:", vocabulary)
    for name in bf.axis_labels.carried_labels("priority", ["P0", "P1"], smap):
        assert f'. == "{name}"' in jq


def test_emit_script_executes_no_write(apply_mod, monkeypatch) -> None:
    monkeypatch.setattr(
        apply_mod, "gh_run",
        lambda *a, **k: pytest.fail("emit-script must execute no write"),
    )
    assert "gh issue edit 7 --add-label P0" in _emit(apply_mod)


# ----- the emitted guard, actually RUN ---------------------------------
#
# Asserting on the emitted text proves the words are there; only running it proves
# the guard works. The fail-closed claim in particular rests on shell behaviour
# under `set -euo pipefail` — that a failing command substitution inside an `if`
# condition neither aborts the script nor reads as an empty success — which no
# string assertion can check. These run the emitted script against a stub `gh`.


def _run_emitted(tmp_path: Path, script: str, mode: str) -> subprocess.CompletedProcess:
    """Run the emitted script with a stub `gh` on PATH in one of three modes:
    `fail` (the re-read errors), `empty` (a confirmed gap), `has` (a value present).
    The stub echoes any other invocation, so a write is visible in stdout."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    stub = bin_dir / "gh"
    stub.write_text(
        "#!/usr/bin/env bash\n"
        'if [ "$1" = "issue" ] && [ "$2" = "view" ]; then\n'
        '  case "$GH_STUB_MODE" in\n'
        "    fail) exit 1 ;;\n"
        '    empty) echo "" ; exit 0 ;;\n'
        '    has) echo "P1" ; exit 0 ;;\n'
        "  esac\n"
        "fi\n"
        'echo "WROTE: $*"\n',
        encoding="utf-8",
    )
    stub.chmod(0o755)
    script_file = tmp_path / "emit.sh"
    script_file.write_text(script, encoding="utf-8")
    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    env["GH_STUB_MODE"] = mode
    return subprocess.run(
        ["bash", str(script_file)], capture_output=True, text=True, env=env, check=False
    )


def test_emitted_script_is_valid_bash(apply_mod, tmp_path) -> None:
    script_file = tmp_path / "emit.sh"
    script_file.write_text(_emit(apply_mod), encoding="utf-8")
    proc = subprocess.run(
        ["bash", "-n", str(script_file)], capture_output=True, text=True, check=False
    )
    assert proc.returncode == 0, proc.stderr


def test_running_the_emitted_script_writes_only_into_a_confirmed_gap(
    apply_mod, tmp_path
) -> None:
    proc = _run_emitted(tmp_path, _emit(apply_mod), "empty")
    assert "WROTE: issue edit 7 --add-label P0" in proc.stdout
    assert proc.returncode == 0


def test_running_the_emitted_script_skips_a_failed_reread(apply_mod, tmp_path) -> None:
    """The property the whole guard exists for, executed rather than asserted: a
    re-read that FAILS writes NOTHING — and does not abort the script, so the rest
    of the corpus still runs (the audited skip/report posture, in shell)."""
    proc = _run_emitted(tmp_path, _emit(apply_mod), "fail")
    assert "WROTE:" not in proc.stdout
    assert "failing closed" in proc.stderr
    assert "complete." in proc.stderr  # the loop continued past the skip
    assert proc.returncode == 0


def test_running_the_emitted_script_skips_an_existing_value(apply_mod, tmp_path) -> None:
    proc = _run_emitted(tmp_path, _emit(apply_mod), "has")
    assert "WROTE:" not in proc.stdout
    assert "not overwriting" in proc.stderr


# ============================================================================
# End-to-end: the report over a staged brownfield corpus
# ============================================================================


def test_report_end_to_end_over_the_reported_configuration(
    bf, tmp_path, monkeypatch, capsys
) -> None:
    """The whole path on the shape #818 describes: a board configured, `priority`
    bound to the adopter's own labels, and a corpus in which some issues carry a
    value and some do not. Only the gaps are proposed, each naming its label."""
    cap = _cap_root(tmp_path, map_yaml=LABEL_BOUND_MAP)
    issued: list[list[str]] = []

    def fake_gh_run(args, config=None, **kwargs):
        issued.append(list(args))
        if args[:3] == ["gh", "repo", "view"]:
            return subprocess.CompletedProcess(
                args, 0, json.dumps({"nameWithOwner": TARGET_REPO}), "")
        if args[:3] == ["gh", "issue", "list"]:
            return subprocess.CompletedProcess(
                args, 0,
                json.dumps([
                    _issue(1),               # gap → proposed
                    _issue(2, "P0"),         # already the target → skipped
                    _issue(3, "P1"),         # a human's value → skipped
                ]),
                "")
        return subprocess.CompletedProcess(args, 0, "{}", "")

    monkeypatch.setattr(bf, "gh_run", fake_gh_run)
    monkeypatch.setattr(bf, "load_adopter_config", lambda _r: dict(BOARD_CONFIG))
    _patch_gate_checks(bf, monkeypatch)
    monkeypatch.setattr(
        sys, "argv", ["back-fill.py", "--capability-root", str(cap), "--json"]
    )

    assert bf.main() == 0
    plan = json.loads(capsys.readouterr().out)
    assert [(c["issue_number"], c["argv"][-1]) for c in plan["proposed"]] == [(1, "P0")]
    # The report half mutates nothing.
    assert not [c for c in issued if "edit" in c or "item-edit" in c]
