"""Tests for `_lib.criterion_ops` — the DEC-038 D4 batch engine.

Mirrors every row of DEC-038's D4 table on the pure engine (no network):
out-of-range refuse, text-mismatch refuse, ambiguous-wording refuse + list,
already-set no-op, half-batch re-run safety, plus the batch path and the
uncheck symmetry.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"


@pytest.fixture(scope="module", autouse=True)
def _scripts_on_path():
    sys.path.insert(0, str(SCRIPTS))
    yield
    sys.path.remove(str(SCRIPTS))


@pytest.fixture(scope="module")
def ops(_scripts_on_path):
    from _lib import criterion_ops

    return criterion_ops


BODY = (
    "Feature: #1\n\n"
    "## What\nbuild it\n\n"
    "## Acceptance criteria\n"
    "- [ ] alpha\n"
    "- [ ] beta\n"
    "- [x] gamma\n\n"
    "## Doc impact\nnone.\n"
)


def _msgs(plan) -> list[str]:
    return [r.message for r in plan.results]


# --- tick by index: single + batch -----------------------------------------


def test_tick_single_by_index(ops) -> None:
    plan = ops.plan_batch(BODY, [ops.Target(1)], target_checked=True)
    assert plan.accepted and plan.changed
    assert "- [x] alpha" in plan.new_body
    assert "- [ ] beta" in plan.new_body  # untouched


def test_tick_batch_by_index(ops) -> None:
    plan = ops.plan_batch(
        BODY, [ops.Target(1), ops.Target(2)], target_checked=True
    )
    assert plan.accepted and plan.changed
    assert "- [x] alpha" in plan.new_body
    assert "- [x] beta" in plan.new_body


# --- expected-text guard: match success ------------------------------------


def test_text_guard_match_succeeds(ops) -> None:
    plan = ops.plan_batch(
        BODY, [ops.Target(1, "alpha")], target_checked=True
    )
    assert plan.accepted and plan.changed
    assert "- [x] alpha" in plan.new_body


def test_text_guard_strips_before_compare(ops) -> None:
    plan = ops.plan_batch(
        BODY, [ops.Target(1, "  alpha  ")], target_checked=True
    )
    assert plan.accepted and plan.changed


# --- text-mismatch refusal (no mutation) -----------------------------------


def test_text_guard_mismatch_refuses_whole_batch(ops) -> None:
    plan = ops.plan_batch(
        BODY,
        [ops.Target(1, "wrong text"), ops.Target(2)],
        target_checked=True,
    )
    assert plan.accepted is False
    assert plan.new_body is None  # nothing to write
    assert any("text-guard mismatch" in m for m in _msgs(plan))
    # The other (valid) target is reported as not-applied, not silently ticked.
    assert any("not applied" in m for m in _msgs(plan))


# --- index out-of-range refusal --------------------------------------------


def test_index_out_of_range_refuses(ops) -> None:
    plan = ops.plan_batch(BODY, [ops.Target(99)], target_checked=True)
    assert plan.accepted is False
    assert plan.new_body is None
    assert any("out of range" in m for m in _msgs(plan))
    assert any("3 acceptance criteria" in m for m in _msgs(plan))


def test_non_checkbox_target_refuses(ops) -> None:
    body = "## Acceptance criteria\n- [ ] real\n- a plain bullet\n"
    plan = ops.plan_batch(body, [ops.Target(2)], target_checked=True)
    assert plan.accepted is False
    assert any("not a checkbox" in m for m in _msgs(plan))


# --- ambiguous-wording refusal + list --------------------------------------


def test_ambiguous_guard_refuses_and_lists(ops) -> None:
    body = (
        "## Acceptance criteria\n"
        "- [ ] duplicate text\n"
        "- [ ] duplicate text\n"
    )
    plan = ops.plan_batch(
        body, [ops.Target(1, "duplicate text")], target_checked=True
    )
    assert plan.accepted is False
    assert plan.new_body is None
    msg = " ".join(_msgs(plan))
    assert "ambiguous" in msg
    assert "1" in msg and "2" in msg  # lists the matching indices


# --- already-set no-op (idempotent) ----------------------------------------


def test_already_ticked_is_noop_success(ops) -> None:
    plan = ops.plan_batch(BODY, [ops.Target(3)], target_checked=True)
    assert plan.accepted is True
    assert plan.changed is False
    assert plan.new_body == BODY  # unchanged
    assert any("already ticked (no-op)" in m for m in _msgs(plan))


# --- half-batch re-run safety ----------------------------------------------


def test_half_batch_rerun_is_idempotent(ops) -> None:
    # Simulate a half-applied batch: alpha already ticked, beta not.
    half = BODY.replace("- [ ] alpha", "- [x] alpha")
    plan = ops.plan_batch(
        half, [ops.Target(1), ops.Target(2)], target_checked=True
    )
    assert plan.accepted is True and plan.changed is True
    # alpha is a no-op, beta completes.
    msgs = _msgs(plan)
    assert any("criterion 1: already ticked" in m for m in msgs)
    assert any("criterion 2: ticked" in m for m in msgs)
    assert "- [x] alpha" in plan.new_body
    assert "- [x] beta" in plan.new_body


# --- uncheck symmetry ------------------------------------------------------


def test_uncheck_single(ops) -> None:
    plan = ops.plan_batch(BODY, [ops.Target(3)], target_checked=False)
    assert plan.accepted and plan.changed
    assert "- [ ] gamma" in plan.new_body


def test_uncheck_already_unticked_noop(ops) -> None:
    plan = ops.plan_batch(BODY, [ops.Target(1)], target_checked=False)
    assert plan.accepted is True and plan.changed is False
    assert any("already unticked (no-op)" in m for m in _msgs(plan))


# --- whole-batch atomicity: one bad target blocks every good one -----------


def test_one_bad_target_blocks_the_good_ones(ops) -> None:
    plan = ops.plan_batch(
        BODY,
        [ops.Target(1), ops.Target(99), ops.Target(2)],
        target_checked=True,
    )
    assert plan.accepted is False
    assert plan.new_body is None
    # Result order is by index, and every target gets a line.
    indices = [r.index for r in plan.results]
    assert indices == sorted(indices)
    assert {1, 2, 99} == set(indices)
