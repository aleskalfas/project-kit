"""pre-check fails when an axis is claimed by BOTH substrates (#709, report #708).

The reported failure (mockingbird — a brownfield adopter with a Projects v2
board): `config.yaml` declares `has_projects_v2_board: true`, so every writer
treats a board-claimed axis as a board field and writes no label, while
`project/substrate-map.yaml` binds that same axis to the adopter's own labels,
which is where every reader looks. Each file is individually well-formed and each
side believes itself, so the axis ends up unset on BOTH substrates and the review
gate becomes unsatisfiable by the capability's own verbs.

These pin the new cross-substrate conflict check: the conflict shape FAILS and
names the axis plus both claimants; the `unsupported: true` workaround shape does
NOT; and neither does any clean single-substrate config (board-only, labels-only
brownfield, greenfield). Pure (no gh, no network) — the check reads only the
already-loaded config mapping and parsed substrate-map.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
SCRIPT = SCRIPTS_DIR / "pre-check.py"


@pytest.fixture(scope="module")
def pc():
    sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location("pm_pre_check_conflict", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_pre_check_conflict"] = module
    spec.loader.exec_module(module)
    yield module
    sys.path.remove(str(SCRIPTS_DIR))


@pytest.fixture(scope="module")
def axis_labels():
    sys.path.insert(0, str(SCRIPTS_DIR))
    from _lib import axis_labels as mod

    yield mod


BOARD_CONFIG = {
    "schema_version": 1,
    "default_branch": "main",
    "workstreams": ["cli"],
    "has_projects_v2_board": True,
    "projects_v2_board_id": 2,
}

LABEL_CONFIG = {
    "schema_version": 1,
    "default_branch": "main",
    "workstreams": ["cli"],
    "has_projects_v2_board": False,
}


def _mockingbird_map(axis_labels):
    """The reported conflict shape: `priority` bound to the repo's own P* labels
    (a legitimate brownfield binding) while the board flag claims the axis."""
    return axis_labels.SubstrateMap(
        axes={
            "priority": {
                "label": {"remap": {"High": "P0", "Medium": "P1", "Low": "P2"}},
                "default": "P1",
            },
            "type": {"title-prefix": {"remap": {"task": "[Task]"}}},
            "workstream": {"unsupported": True},
        }
    )


def _workaround_map(axis_labels):
    """The report's own (now-withdrawn) workaround: the board-backed axis is
    `unsupported: true`. It names no substrate, so it makes no competing claim —
    no conflict. It is NOT the way to declare board carriage; see
    `test_board_arm_is_not_a_conflict` for the shape that replaced it."""
    return axis_labels.SubstrateMap(
        axes={
            "priority": {"unsupported": True},
            "type": {"title-prefix": {"remap": {"task": "[Task]"}}},
            "workstream": {"unsupported": True},
        }
    )


# --- the conflict shape fails ----------------------------------------------


def test_mockingbird_conflict_fails_and_names_the_axis(pc, axis_labels) -> None:
    results = pc._check_substrate_board_conflict(
        BOARD_CONFIG, _mockingbird_map(axis_labels)
    )
    fails = [r for r in results if r.status == "fail"]
    assert len(fails) == 1
    assert "priority" in fails[0].label


def test_conflict_detail_names_both_claimants_and_consequence(pc, axis_labels) -> None:
    """The message has to be actionable on its own: both files named, and what
    the state costs the adopter (unset on both substrates ⇒ gate unsatisfiable)."""
    fail = next(
        r
        for r in pc._check_substrate_board_conflict(
            BOARD_CONFIG, _mockingbird_map(axis_labels)
        )
        if r.status == "fail"
    )
    # Claimant 1: the config flag (with the board id when known).
    assert "config.yaml" in fail.detail
    assert "has_projects_v2_board: true" in fail.detail
    assert "#2" in fail.detail
    # Claimant 2: the substrate-map's label binding.
    assert "substrate-map.yaml" in fail.detail
    assert "label" in fail.detail
    # Consequence.
    assert "BOTH substrates" in fail.detail
    assert "unsatisfiable" in fail.detail
    # Remediation offers both single-substrate exits. The board-backed one names
    # `board: true` — NOT `unsupported: true`, which the arm's arrival withdrew
    # (it declares the axis has no encoding, the opposite of board carriage;
    # project-management:DEC-051 decision point 1).
    assert fail.remediation is not None
    assert "board: true" in fail.remediation
    assert "unsupported: true" not in fail.remediation
    assert "has_projects_v2_board: false" in fail.remediation


def test_conflict_reported_per_axis(pc, axis_labels) -> None:
    """Two conflicting axes ⇒ two findings, each naming its own axis, so the
    remediation is specific rather than an aggregate."""
    both = axis_labels.SubstrateMap(
        axes={
            "priority": {"label": {"remap": {"High": "P0"}}},
            "workstream": {"label": {"remap": {"cli": "area/cli"}}},
        }
    )
    results = pc._check_substrate_board_conflict(BOARD_CONFIG, both)
    labels = [r.label for r in results if r.status == "fail"]
    assert len(labels) == 2
    assert any("priority" in lbl for lbl in labels)
    assert any("workstream" in lbl for lbl in labels)


def test_label_bound_state_axis_conflicts_too(pc, axis_labels) -> None:
    """`state` is board-claimed as well (move-issue writes no `state:*` label
    under a board), so a label-bound state axis is the same failure."""
    sm = axis_labels.SubstrateMap(
        axes={"state": {"label": {"remap": {"open": "Status: Open"}}}}
    )
    results = pc._check_substrate_board_conflict(BOARD_CONFIG, sm)
    assert any(r.status == "fail" and "state" in r.label for r in results)


def test_conflict_is_a_fail_not_a_warn(pc, axis_labels) -> None:
    """The severity choice is load-bearing: pre-check is the hard prerequisite
    gate and this state makes the review gate unsatisfiable, so it must flip the
    exit code, not whisper. (A `warn` would be lost in a passing run — exactly
    the invisibility report #708 is about.)"""
    results = pc._check_substrate_board_conflict(
        BOARD_CONFIG, _mockingbird_map(axis_labels)
    )
    assert any(r.status == "fail" for r in results)
    assert not any(r.status == "warn" for r in results)


# --- clean configurations do not trip it -----------------------------------


def test_unsupported_workaround_shape_does_not_fail(pc, axis_labels) -> None:
    """The report's workaround (mark the board-backed axis `unsupported: true`)
    agrees with the writer — one claimant, no conflict."""
    results = pc._check_substrate_board_conflict(
        BOARD_CONFIG, _workaround_map(axis_labels)
    )
    assert all(r.status != "fail" for r in results)
    assert any(r.status == "ok" for r in results)


def test_axis_absent_from_present_map_does_not_fail(pc, axis_labels) -> None:
    """Absent ≡ unsupported (ADR-026's load-bearing rule) — the map makes no
    competing claim, so no conflict."""
    sm = axis_labels.SubstrateMap(axes={"type": {"title-prefix": {"remap": {"task": "[Task]"}}}})
    results = pc._check_substrate_board_conflict(BOARD_CONFIG, sm)
    assert all(r.status != "fail" for r in results)


def test_board_only_config_does_not_fail(pc, axis_labels) -> None:
    """A board adopter whose map binds only non-board-claimed / non-label axes:
    single substrate per axis, clean."""
    sm = axis_labels.SubstrateMap(
        axes={
            "type": {"title-prefix": {"remap": {"task": "[Task]"}}},
            "priority": {"unsupported": True},
            "workstream": {"unsupported": True},
            "state": {"derive": {"from": "open-closed", "states": {"done": "closed"}}},
        }
    )
    results = pc._check_substrate_board_conflict(BOARD_CONFIG, sm)
    assert all(r.status != "fail" for r in results)


def test_labels_only_brownfield_config_does_not_fail(pc, axis_labels) -> None:
    """The labels-only brownfield adopter: label bindings everywhere, but NO board
    flag — the label binding is the sole claimant, which is the whole point of a
    substrate map. Must not be collateral damage of the new check."""
    results = pc._check_substrate_board_conflict(
        LABEL_CONFIG, _mockingbird_map(axis_labels)
    )
    assert all(r.status != "fail" for r in results)
    assert any(r.status == "skip" for r in results)


def test_derive_bound_state_under_board_does_not_fail(pc, axis_labels) -> None:
    """A `derive` binding reads open/closed, which a board does not suppress —
    not a label starved of a writer, so not a conflict."""
    sm = axis_labels.SubstrateMap(
        axes={"state": {"derive": {"from": "open-closed", "states": {"done": "closed"}}}}
    )
    results = pc._check_substrate_board_conflict(BOARD_CONFIG, sm)
    assert all(r.status != "fail" for r in results)


def test_title_prefix_bound_type_under_board_does_not_fail(pc, axis_labels) -> None:
    """`type` is always-a-label per classification.yaml, so a board never claims
    it; and a title-prefix binding is title-carried, not label-carried. Neither
    is a competing claim."""
    sm = axis_labels.SubstrateMap(
        axes={"type": {"label": {"remap": {"bug": "kind/bug"}}}}
    )
    results = pc._check_substrate_board_conflict(BOARD_CONFIG, sm)
    assert all(r.status != "fail" for r in results)


def test_missing_config_does_not_fail(pc, axis_labels) -> None:
    """A config that failed to load cannot claim anything — the config check
    already reported that failure; this one degrades to a skip."""
    results = pc._check_substrate_board_conflict(None, _mockingbird_map(axis_labels))
    assert all(r.status != "fail" for r in results)


# --- this repo's own (greenfield, no map) config ---------------------------


def test_this_repos_own_config_has_no_conflict(pc, axis_labels) -> None:
    """Self-hosting sanity: project-kit's own pm config is board-less with no
    substrate-map, so the check cannot fire (it runs only under a present map)."""
    import json

    from ruamel.yaml import YAML

    cap_root = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
    config = YAML(typ="safe").load(
        (cap_root / "project" / "config.yaml").read_text(encoding="utf-8")
    )
    assert config.get("has_projects_v2_board") is False
    assert axis_labels.load_substrate_map(cap_root) is None
    # Belt: even if a map appeared, a board-less config makes it a skip.
    results = pc._check_substrate_board_conflict(config, _mockingbird_map(axis_labels))
    assert all(r.status != "fail" for r in results)
    # The result is JSON-serialisable like every other CheckResult (--json path).
    json.dumps([r.__dict__ for r in results])
