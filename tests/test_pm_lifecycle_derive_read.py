"""Derive-state READ detector — the map-aware lifecycle position read (#269,
Feature #268; ADR-026 §5, DEC-033 detector swap).

This is the PARITY-CRITICAL detection path. The acceptance bars:

  1. **Derive-map read.** Under a present substrate-map binding `state` to a
     `derive` predicate, position resolves from the open/closed substrate
     (+ a blocked label): open ⇒ the collapsed open-ish `open`; closed ⇒ the
     terminal `done`; open + a `Blocked` label ⇒ `blocked`. A stray leftover
     kit `state:*` label is IGNORED — the wedge #265's docstring named (a
     `state:todo` must NOT shadow the open/closed read), closed by #269.

  2. **Greenfield position parity (the load-bearing bar).** For greenfield
     (no map), a `label`-bound `state`, and a non-derive present map, position
     is byte-identical to the pre-#269 precedence across the full
     (open/closed × labels × state set) grid. The oracle (`_pre_269_infer`) is
     an INDEPENDENT transcription of that precedence, not a call back into the
     code under test — so the grid cannot pass circularly.

  3. **Read/write agreement.** Under a derive map, the position this detector
     reads agrees with how `move-issue` / `close-issue` (#265) treat state: the
     write side writes/strips NO kit `state:*` label (the open/closed substrate
     carries state), and this read resolves from that same open/closed substrate.

  4. **DEC-034 closure fold.** The fold's done-detection (`detect_state(n,
     "done")` over the derived terminal) resolves a closed child to `done` under
     a derive binding, so the `all`-over-`done` reducer folds correctly.

The gh layer is stubbed; these tests exercise the pure inference + the predicate
contract, not the network.

SCOPE NOTE: `detect_state(n, "blocked")` here proves the *predicate* resolves a
blocked position from an open + `Blocked`-labelled issue. It does NOT prove the
*engine* surfaces `blocked` end-to-end — whether the engine iterates a `blocked`
state depends on the adopter shipping a `workflow.yaml` whose state set includes
it. That engine-side registration is the adopter-workflow / Feature concern
(#268 wave), not this READ task (#269). #269 owns only the derive predicate.
"""

from __future__ import annotations

import itertools
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CAP_SCRIPTS = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
if str(CAP_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(CAP_SCRIPTS))

from _lib import axis_labels  # noqa: E402
from _lib import lifecycle_inference as infer  # noqa: E402
from _lib import lifecycle_predicates as predicates  # noqa: E402


# --- fixtures: the four substrate-map shapes ------------------------------
# The AUJ-shaped derive map (#258 / ADR-026 §5): state derived from open/closed
# + a Blocked label. `from`/`states` carry prose conditions (the schema defers
# the grammar to this engine), so the test asserts the engine's convention, not
# a parse of that prose.
DERIVE_MAP = axis_labels.SubstrateMap(
    axes={
        "state": {
            "derive": {
                "from": "open-closed",
                "states": {
                    "open": "issue is open and not labelled Blocked",
                    "blocked": "issue is open and labelled Blocked",
                    "done": "issue is closed",
                },
            }
        },
    }
)

# A present map that binds `state` to a LABEL set (reverse remap), NOT derive —
# the adopter encodes lifecycle as their own labels `Status:*`.
LABEL_STATE_MAP = axis_labels.SubstrateMap(
    axes={
        "state": {
            "label": {
                "remap": {
                    "todo": "Status:Todo",
                    "backlog": "Status:Backlog",
                    "in-progress": "Status:Doing",
                    "review": "Status:Review",
                    "done": "Status:Done",
                }
            }
        },
    }
)

# A present map whose `state` is NON-DERIVE and NON-LABEL (unsupported) — the
# read must fall through exactly as greenfield's label-absent arm does, EXCEPT
# it finds no kit label (the map present means the kit `state:*` set is not read).
UNSUPPORTED_STATE_MAP = axis_labels.SubstrateMap(
    axes={"state": {"unsupported": True}},
)


# ==========================================================================
# 1. Derive-map read
# ==========================================================================


def test_derive_open_issue_no_label_is_open() -> None:
    """An open issue with NO kit state:* label resolves to the collapsed
    open-ish `open` — NOT 'no position' / todo."""
    assert (
        infer.infer_current_state(
            state="open", milestone={}, labels=[], substrate_map=DERIVE_MAP
        )
        == axis_labels.DERIVE_STATE_OPEN
    )


def test_derive_closed_issue_is_done() -> None:
    """A closed issue resolves to the terminal `done` (the derived terminal)."""
    assert (
        infer.infer_current_state(
            state="closed", milestone={}, labels=[], substrate_map=DERIVE_MAP
        )
        == axis_labels.DERIVE_STATE_DONE
    )


def test_derive_open_blocked_label_is_blocked() -> None:
    """An open issue with a `Blocked` label resolves to `blocked`."""
    assert (
        infer.infer_current_state(
            state="open", milestone={}, labels=["Blocked"], substrate_map=DERIVE_MAP
        )
        == axis_labels.DERIVE_STATE_BLOCKED
    )


def test_derive_blocked_label_is_case_insensitive() -> None:
    """The blocked-label match is case-insensitive (the convention, not an exact
    string the adopter must capitalise identically)."""
    for variant in ("Blocked", "blocked", "BLOCKED"):
        assert (
            infer.infer_current_state(
                state="open", milestone={}, labels=[variant], substrate_map=DERIVE_MAP
            )
            == axis_labels.DERIVE_STATE_BLOCKED
        )


def test_derive_milestone_does_not_shift_open_to_backlog() -> None:
    """An open issue WITH a milestone still reads `open` under a derive map — the
    open-ish states collapse, so the milestone→backlog greenfield arm does NOT
    apply (the reduced state set, ADR-026 §5)."""
    assert (
        infer.infer_current_state(
            state="open",
            milestone={"title": "M1"},
            labels=[],
            substrate_map=DERIVE_MAP,
        )
        == axis_labels.DERIVE_STATE_OPEN
    )


# --- the wedge: a stray leftover kit state:* label is IGNORED --------------


def test_derive_stray_state_todo_label_is_ignored_when_open() -> None:
    """THE WEDGE (#265 → #269): a leftover `state:todo` on an OPEN issue under a
    derive map must NOT shadow the open/closed read — position is `open`, read
    from open/closed, with the stray label ignored."""
    # The mutation this guards against: the pre-#269 reader returned the first
    # `state:*` label (here `todo`), wedging the issue. Post-#269 it reads
    # open/closed and ignores the label.
    resolved = infer.infer_current_state(
        state="open",
        milestone={},
        labels=["state:todo"],
        substrate_map=DERIVE_MAP,
    )
    assert resolved == axis_labels.DERIVE_STATE_OPEN
    assert resolved != "todo", (
        "wedge NOT closed: a stray kit state:todo shadowed the open/closed read"
    )


def test_derive_stray_state_review_label_is_ignored_when_open() -> None:
    """A different stray label (`state:review`) is likewise ignored — the read
    is open/closed, not the kit label set, regardless of which stale value."""
    assert (
        infer.infer_current_state(
            state="open",
            milestone={},
            labels=["state:review", "priority:High"],
            substrate_map=DERIVE_MAP,
        )
        == axis_labels.DERIVE_STATE_OPEN
    )


def test_derive_closed_wins_over_stray_label_and_blocked() -> None:
    """A CLOSED issue reads `done` even with a stray `state:in-progress` label
    AND a `Blocked` label — closed is terminal and authoritative; neither the
    stale kit label nor the blocked label holds it open."""
    assert (
        infer.infer_current_state(
            state="closed",
            milestone={},
            labels=["state:in-progress", "Blocked"],
            substrate_map=DERIVE_MAP,
        )
        == axis_labels.DERIVE_STATE_DONE
    )


# --- the seam primitive in isolation --------------------------------------


def test_derive_state_primitive_truth_table() -> None:
    """`axis_labels.derive_state` is the predicate; pin its three outcomes
    directly (closed > blocked-label > open), independent of the inference
    wrapper."""
    assert axis_labels.derive_state(is_closed=True, labels=[]) == "done"
    assert axis_labels.derive_state(is_closed=True, labels=["Blocked"]) == "done"
    assert axis_labels.derive_state(is_closed=False, labels=["Blocked"]) == "blocked"
    assert axis_labels.derive_state(is_closed=False, labels=[]) == "open"
    # stray kit label is invisible to the primitive.
    assert axis_labels.derive_state(is_closed=False, labels=["state:done"]) == "open"


def test_state_derive_binding_recognises_only_derive() -> None:
    """`state_derive_binding` returns the derive mapping ONLY for a derive-bound
    state; None for no-map, label-bound, unsupported, absent."""
    assert axis_labels.state_derive_binding(DERIVE_MAP) is not None
    assert axis_labels.state_derive_binding(None) is None
    assert axis_labels.state_derive_binding(LABEL_STATE_MAP) is None
    assert axis_labels.state_derive_binding(UNSUPPORTED_STATE_MAP) is None


# ==========================================================================
# 2. Greenfield position parity (the load-bearing bar) — a byte-identity grid
# ==========================================================================


def _pre_269_infer(state: str, milestone, labels: list[str]) -> str:
    """The pre-#269 precedence, transcribed independently (the parity oracle).

    This is a SECOND, hand-written copy of the greenfield precedence — NOT a
    call into `infer_current_state` — so the grid below is a real oracle, not a
    tautology. Matches `test_pm_lifecycle_rebind_parity._pre_rebind_infer`.
    """
    if state == "closed":
        return "done"
    for lbl in labels:
        if lbl.startswith("state:"):
            return lbl.removeprefix("state:")
    if milestone:
        return "backlog"
    return "todo"


def _grid_inputs():
    """The full (gh state × milestone × labels) grid the greenfield precedence
    distinguishes — the same shape as the rebind-parity truth table."""
    gh_states = ["open", "closed"]
    milestones = [None, {}, {"title": "M1"}]
    label_sets = [
        [],
        ["type:feature"],
        ["state:todo"],
        ["state:backlog"],
        ["state:in-progress"],
        ["state:review"],
        ["state:done"],
        ["state:in-progress", "type:feature"],
        ["priority:High", "state:review"],
        ["state:review", "state:todo"],  # two state labels: pin first-match-wins on the axis
    ]
    return itertools.product(gh_states, milestones, label_sets)


def test_greenfield_no_map_is_byte_identical() -> None:
    """No map (the default arm): every grid input resolves byte-identically to
    the pre-#269 precedence. This is the parity bar — the derive swap must not
    perturb the greenfield read at all."""
    for gh_state, milestone, labels in _grid_inputs():
        expected = _pre_269_infer(gh_state, milestone, labels)
        # both the explicit-None and the default (no kwarg) must match.
        explicit = infer.infer_current_state(
            state=gh_state, milestone=milestone, labels=labels, substrate_map=None
        )
        defaulted = infer.infer_current_state(
            state=gh_state, milestone=milestone, labels=labels
        )
        assert explicit == defaulted == expected, (
            f"greenfield parity break: state={gh_state} milestone={milestone} "
            f"labels={labels} -> pre={expected} none={explicit} default={defaulted}"
        )


def test_unsupported_state_map_matches_greenfield_minus_kit_labels() -> None:
    """A present map whose `state` is `unsupported` (non-derive, non-label) reads
    NO kit `state:*` label — so it resolves closed→done, else milestone→backlog,
    else todo, IGNORING any kit state:* label. This is the present-map
    non-derive arm: it must NOT read the kit label set (the map present means the
    kit substrate is not authoritative), but the closed/milestone/todo arms are
    byte-identical to greenfield."""
    for gh_state, milestone, labels in _grid_inputs():
        resolved = infer.infer_current_state(
            state=gh_state,
            milestone=milestone,
            labels=labels,
            substrate_map=UNSUPPORTED_STATE_MAP,
        )
        if gh_state == "closed":
            assert resolved == "done"
        elif milestone:
            assert resolved == "backlog"
        else:
            assert resolved == "todo"


def test_label_bound_state_reads_adopter_label_set() -> None:
    """A `label`-bound `state` reads the adopter's mapped label set (reverse
    remap), NOT the kit `state:*` set. An adopter `Status:Doing` resolves to the
    kit value `in-progress`; a kit `state:done` label present is IGNORED."""
    # adopter label present -> reverse-remapped kit value.
    assert (
        infer.infer_current_state(
            state="open",
            milestone={},
            labels=["Status:Doing"],
            substrate_map=LABEL_STATE_MAP,
        )
        == "in-progress"
    )
    # a stray KIT state:* label is NOT read under a present label-bound map —
    # only the adopter's mapped set is. Falls through to milestone/todo.
    assert (
        infer.infer_current_state(
            state="open",
            milestone={},
            labels=["state:review"],
            substrate_map=LABEL_STATE_MAP,
        )
        == "todo"
    )
    # closed still wins.
    assert (
        infer.infer_current_state(
            state="closed",
            milestone={},
            labels=["Status:Doing"],
            substrate_map=LABEL_STATE_MAP,
        )
        == "done"
    )


def test_resolve_read_reverse_remap_and_arms() -> None:
    """`resolve_read` is the label-arm reverse-remap: greenfield identity,
    label reverse-remap, and None for derive/unsupported/title-prefix."""
    # greenfield: kit read.
    assert axis_labels.resolve_read("state", ["state:review"], None) == "review"
    # label-bound: reverse remap.
    assert (
        axis_labels.resolve_read("state", ["Status:Done"], LABEL_STATE_MAP) == "done"
    )
    # label-bound, none of the adopter labels present -> None.
    assert axis_labels.resolve_read("state", ["state:todo"], LABEL_STATE_MAP) is None
    # derive-bound -> None (read goes through derive_state, not a label).
    assert axis_labels.resolve_read("state", ["state:todo"], DERIVE_MAP) is None
    # unsupported -> None.
    assert (
        axis_labels.resolve_read("state", ["state:todo"], UNSUPPORTED_STATE_MAP)
        is None
    )


# ==========================================================================
# 3. Read/write agreement (the derive map) — #265 write side
# ==========================================================================


def test_read_agrees_with_write_close_writes_no_kit_label() -> None:
    """Read/write agreement: under a derive map the WRITE side
    (`reconcile_state_labels_to_done`) writes/strips NO kit `state:*` label (the
    open/closed substrate carries state), and this READ resolves position from
    that same open/closed substrate — no read/write disagreement.

    Concretely: the write side's terminal-label resolution DEGRADEs (no kit
    label), and the read for a closed issue is `done` read from `closed` — the
    two agree that the kit `state:*` label is irrelevant under a derive map.
    """
    from _lib import labels as labels_lib

    # WRITE side: the terminal `state` write degrades — no kit label.
    terminal = axis_labels.resolve_write("state", "done", DERIVE_MAP)
    assert terminal is axis_labels.DEGRADE, (
        "write side must NOT resolve a kit state:done under a derive map"
    )

    # And the reconcile helper writes nothing (returns True without a gh call):
    # we assert it never calls gh_run by passing a stub that fails the test if
    # invoked.
    def _gh_must_not_run(*_a, **_k):  # pragma: no cover - asserted not-called
        raise AssertionError("reconcile wrote a label under a derive map")

    assert (
        labels_lib.reconcile_state_labels_to_done(
            1,
            ["state:in-progress"],  # a stale kit label present
            {},
            gh_run=_gh_must_not_run,
            substrate_map=DERIVE_MAP,
        )
        is True
    )

    # READ side: a closed issue (even carrying the same stale kit label) reads
    # `done` from open/closed — agreeing that the kit label is irrelevant.
    assert (
        infer.infer_current_state(
            state="closed",
            milestone={},
            labels=["state:in-progress"],
            substrate_map=DERIVE_MAP,
        )
        == "done"
    )


def test_read_open_agrees_with_write_open_no_kit_label() -> None:
    """The open-ish symmetric case: the write side resolves no kit label for any
    non-terminal state under a derive map, and the read for an open issue is the
    collapsed `open` from open/closed — both ignore the kit label set."""
    for value in ("todo", "backlog", "in-progress", "review"):
        assert (
            axis_labels.resolve_write("state", value, DERIVE_MAP)
            is axis_labels.DEGRADE
        )
    assert (
        infer.infer_current_state(
            state="open", milestone={}, labels=["state:backlog"], substrate_map=DERIVE_MAP
        )
        == "open"
    )


# ==========================================================================
# 4. Engine detectors + DEC-034 closure fold under a derive binding
# ==========================================================================


def _stub_detect(monkeypatch: pytest.MonkeyPatch, issue: dict, substrate_map) -> None:
    """Stub the engine detector's gh + map load to fixed values."""
    monkeypatch.setattr(predicates, "_capability_root", lambda: REPO_ROOT)
    monkeypatch.setattr(predicates, "_config", lambda _root: {})
    monkeypatch.setattr(predicates, "_fetch_issue", lambda _n, _c, _f: issue)
    monkeypatch.setattr(
        predicates.axis_labels, "load_substrate_map", lambda _root: substrate_map
    )


def test_detect_state_is_map_aware_open(monkeypatch: pytest.MonkeyPatch) -> None:
    """The engine detector resolves the derived `open` for an open, unlabelled
    issue under a derive map — and a stray kit `state:todo` does NOT make
    `detect-todo` fire (the wedge closed end-to-end through the engine)."""
    issue = {"state": "open", "milestone": {}, "labels": ["state:todo"]}
    _stub_detect(monkeypatch, issue, DERIVE_MAP)
    assert predicates.detect_state(1, "open")["result"] is True
    # the stray label must NOT make the kit `todo` detector match.
    assert predicates.detect_state(1, "todo")["result"] is False
    assert predicates.detect_state(1, "done")["result"] is False


def test_detect_done_is_map_aware_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    """DEC-034 closure fold: the fold's done-detection (`detect-done`) resolves a
    CLOSED child to `done` under a derive binding — so the `all`-over-`done`
    reducer reads a well-defined terminal."""
    issue = {"state": "closed", "milestone": {}, "labels": ["state:in-progress"]}
    _stub_detect(monkeypatch, issue, DERIVE_MAP)
    assert predicates.detect_state(1, "done")["result"] is True
    assert predicates.detect_state(1, "open")["result"] is False


def test_detect_blocked_is_map_aware(monkeypatch: pytest.MonkeyPatch) -> None:
    """An open, `Blocked`-labelled issue detects as `blocked` under a derive
    map — the third derived state."""
    issue = {"state": "open", "milestone": {}, "labels": ["Blocked"]}
    _stub_detect(monkeypatch, issue, DERIVE_MAP)
    assert predicates.detect_state(1, "blocked")["result"] is True
    assert predicates.detect_state(1, "open")["result"] is False


def test_detect_state_greenfield_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    """No map: the detector reads the kit `state:*` precedence exactly as before
    — a `state:review` label detects `review`."""
    issue = {"state": "open", "milestone": {}, "labels": ["state:review"]}
    _stub_detect(monkeypatch, issue, None)
    assert predicates.detect_state(1, "review")["result"] is True
    assert predicates.detect_state(1, "open")["result"] is False


def test_closure_fold_done_detection_over_derived_terminal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """End-to-end-ish DEC-034 fold shape: a parent's children, resolved through
    the now-map-aware detector, fold to done iff ALL are closed under a derive
    map — a closed child resolves `done` (counts), an open child resolves `open`
    (holds the fold). Verified via the per-child detector the fold runs."""
    children = [
        {"number": 11, "state": "closed", "milestone": {}, "labels": []},
        {"number": 12, "state": "closed", "milestone": {}, "labels": ["state:todo"]},
    ]
    # every child closed -> every detect-done True -> all-done satisfied.
    for child in children:
        _stub_detect(monkeypatch, child, DERIVE_MAP)
        assert predicates.detect_state(child["number"], "done")["result"] is True

    # an OPEN child holds the fold: detect-done is False, so all-over-done fails.
    open_child = {"number": 13, "state": "open", "milestone": {}, "labels": []}
    _stub_detect(monkeypatch, open_child, DERIVE_MAP)
    assert predicates.detect_state(13, "done")["result"] is False
    assert predicates.detect_state(13, "open")["result"] is True


def test_parent_active_descendant_map_aware(monkeypatch: pytest.MonkeyPatch) -> None:
    """The pm-local descendant walk resolves an OPEN child under a derive map to
    the collapsed `open`, which `state_is_active` treats as active (the open-ish
    collapse subsumes in-progress) — so a possibly-in-flight child is NOT
    silently dropped from the forward-cascade walk."""
    children = [
        {
            "number": 11,
            "body": "Feature: #10\n\n## What\nx",
            "state": "open",
            "milestone": {},
            "labels": [],  # no kit label; open-ish under derive
        },
    ]
    monkeypatch.setattr(predicates, "_capability_root", lambda: REPO_ROOT)
    monkeypatch.setattr(predicates, "_config", lambda _root: {})
    monkeypatch.setattr(predicates, "_list_issues", lambda _c: children)
    monkeypatch.setattr(
        predicates.axis_labels, "load_substrate_map", lambda _root: DERIVE_MAP
    )
    out = predicates.parent_has_active_descendant(10)
    assert out["result"] is True
    assert out["detail"]["active_descendants"] == [11]


def test_state_is_active_handles_derived_ids() -> None:
    """`state_is_active` recognises the derived `open`/`blocked` as active (the
    open-ish collapse subsumes in-progress, so they must not ValueError-fall to
    inactive). The derived `done` IS the kit `"done"` value, so it counts active
    exactly as greenfield `done` does (>= in-progress in the order) — no
    divergence. The greenfield five-state order is unperturbed."""
    assert infer.state_is_active(axis_labels.DERIVE_STATE_OPEN) is True
    assert infer.state_is_active(axis_labels.DERIVE_STATE_BLOCKED) is True
    # `done` is active in greenfield too (>= in-progress); the derived terminal
    # IS "done", so it inherits that — preserved, not changed.
    assert infer.state_is_active(axis_labels.DERIVE_STATE_DONE) is True
    assert infer.state_is_active("done") is True
    # greenfield order unperturbed.
    assert infer.state_is_active("in-progress") is True
    assert infer.state_is_active("review") is True
    assert infer.state_is_active("todo") is False
    assert infer.state_is_active("backlog") is False
