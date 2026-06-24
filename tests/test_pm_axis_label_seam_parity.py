"""Greenfield byte-identity for the axis-label seam — ADR-026 part (a) parity.

Task A is a pure, behaviour-preserving refactor: with no ``substrate-map.yaml``
present (always, in this Task), every label the routed scripts emit must be
**byte-identical** to the inline ``f"<axis>:<value>"`` construction it replaced.
This is the resolution-test half of ADR-026's two-part invariant (the
sole-constructor *guard* is its structural companion in
`test_pm_axis_label_seam_guard`).

Modelled on `test_cli_render_wrap`'s byte-identity approach (a frozen oracle of
the pre-refactor behaviour, asserted equal across an input grid): here the oracle
is the trivial ``f"{axis}:{value}"`` the sites used to inline, and the grid
covers every axis with representative values.

Consumer parity is proven by loading the REAL modules and asserting on the labels
they actually construct (G-1) — not by re-implementing the label logic in the
test body, which would prove nothing beyond the seam-equals-inline unit test
above. ``bootstrap._compute_plan`` is exercised end-to-end (its ``_fetch`` /
``_starter_epic`` side-effecting helpers stubbed) and its real ``label_creates``
names are asserted against the frozen oracle across every axis. ``_lib.labels``
is likewise the real module (its terminal/non-terminal ``state:*`` sets compared
to the frozen literals). ``create-issue`` builds its label list inline in
``main()`` with no callable seam to exercise without invoking ``gh``; its
seam-routing is covered by the guard (`test_pm_axis_label_seam_guard`) and the
``label``-level identity grid above, so it gets no circular re-implementation here.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
LIB = SCRIPTS / "_lib"

# Put the scripts dir on sys.path so `import _lib.axis_labels` resolves exactly
# as it does for the PEP 723 scripts at runtime.
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from _lib import axis_labels  # noqa: E402


# A representative grid per axis. The values mirror what the scripts pass:
# classification.yaml type/priority values, lifecycle states, workstream slugs.
GREENFIELD_GRID: dict[str, list[str]] = {
    "type": ["feature", "bug", "docs", "refactor", "test", "maintenance", "chore"],
    "priority": ["High", "Medium", "Low"],
    "workstream": ["cli", "schemas", "agents", "a-slug-with-dashes"],
    "state": ["todo", "backlog", "in-progress", "review", "done"],
}


def _oracle_label(axis: str, value: str) -> str:
    """The frozen pre-refactor encoding: a literal ``f"{axis}:{value}"``."""
    return f"{axis}:{value}"


# --- the seam itself: identity across the whole grid ----------------------


@pytest.mark.parametrize(
    "axis,value",
    [(axis, v) for axis, vals in GREENFIELD_GRID.items() for v in vals],
)
def test_label_is_byte_identical_to_inline_construction(axis: str, value: str) -> None:
    assert axis_labels.label(axis, value) == _oracle_label(axis, value)


@pytest.mark.parametrize("axis", list(GREENFIELD_GRID))
def test_prefix_is_byte_identical(axis: str) -> None:
    assert axis_labels.prefix(axis) == f"{axis}:"


@pytest.mark.parametrize(
    "axis,value",
    [(axis, v) for axis, vals in GREENFIELD_GRID.items() for v in vals],
)
def test_read_round_trips_the_value(axis: str, value: str) -> None:
    label = axis_labels.label(axis, value)
    assert axis_labels.read(axis, [label]) == value
    assert axis_labels.is_axis_label(label, axis)


def test_read_first_match_wins_like_infer_current_state() -> None:
    # The "first `state:*` label wins" contract (lifecycle_inference precedence).
    labels = ["other:x", "state:review", "state:done"]
    assert axis_labels.read("state", labels) == "review"


def test_read_returns_none_when_axis_absent() -> None:
    assert axis_labels.read("workstream", ["type:bug", "priority:High"]) is None


def test_read_all_collects_every_value_in_order() -> None:
    labels = ["type:bug", "workstream:cli", "type:docs", "noise"]
    assert axis_labels.read_all("type", labels) == ["bug", "docs"]


# --- read() → str|None boundary (G-3) -------------------------------------
# Pin the divergence point of the seam's read against the old inline
# `removeprefix` behaviour: a bare prefix yields the empty string (a present
# axis at empty value), while a label that is *not* on the axis yields None.


def test_read_bare_prefix_yields_empty_string() -> None:
    # `"type:"` is a present `type` label at the empty value — matches the old
    # `name.removeprefix("type:")` returning "". NOT None.
    assert axis_labels.read("type", ["type:"]) == ""


def test_read_non_axis_label_yields_none() -> None:
    # `"type"` (no colon) is not a `type:` label at all — `startswith("type:")`
    # is False, so the axis is absent. Distinct from the empty-value case above.
    assert axis_labels.read("type", ["type"]) is None


# --- consumer parity: bootstrap, the REAL module (G-1) --------------------
# Load and exercise the actual `bootstrap._compute_plan`, asserting on the label
# names it really constructs — not a re-implementation in the test body.


def _load_script(name: str):
    mod_name = f"pm_parity_{name.replace('-', '_').replace('.py', '')}"
    spec = importlib.util.spec_from_file_location(mod_name, SCRIPTS / name)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module


def _write_yaml(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_bootstrap_compute_plan_constructs_byte_identical_labels(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The REAL `bootstrap._compute_plan` constructs its label names through the
    seam; in greenfield those names must be byte-identical to the frozen
    `f"{axis}:{v}"` oracle for every axis × value in the grid.

    We stub the two side-effecting helpers (`_fetch_existing_labels` → empty so
    every planned label lands in `label_creates`; `_starter_epic_already_filed`),
    drive the per-axis values from a synthetic classification + a tmp
    capability_root carrying workstreams.yaml and workflow.yaml, and compare the
    plan's actual `(axis, name)` creates against the oracle. This exercises the
    real `_plan_axis` → `axis_labels.label` path, not a copy of it."""
    bootstrap = _load_script("bootstrap.py")

    monkeypatch.setattr(bootstrap, "_fetch_existing_labels", lambda: set())
    monkeypatch.setattr(bootstrap, "_starter_epic_already_filed", lambda: False)

    cap_root = tmp_path / "cap"
    # workstreams.yaml — canonical source for the workstream axis.
    _write_yaml(
        cap_root / "project" / "workstreams.yaml",
        "workstreams:\n"
        + "".join(f"  - {s}\n" for s in GREENFIELD_GRID["workstream"]),
    )
    # workflow.yaml — drives the state axis (label-fallback mode). The resolver
    # reorders to canonical lifecycle order, which matches the grid's order.
    _write_yaml(
        cap_root / "schemas" / "workflow.yaml",
        "process:\n  states:\n"
        + "".join(f"    - id: {s}\n" for s in GREENFIELD_GRID["state"]),
    )

    classification = {
        "axes": {
            "type": {"values": GREENFIELD_GRID["type"]},
            "priority": {"values": GREENFIELD_GRID["priority"]},
        }
    }

    plan = bootstrap._compute_plan(
        config={},
        classification=classification,
        has_board=False,
        with_starter_epic=False,
        capability_root=cap_root,
    )

    # Guard against a vacuous pass: the plan must have actually built labels.
    assert plan.label_creates, "bootstrap produced no label creates to compare"

    # Every planned create, grouped by axis, must equal the frozen oracle names.
    constructed: dict[str, list[str]] = {axis: [] for axis in GREENFIELD_GRID}
    for axis, name in plan.label_creates:
        constructed[axis].append(name)

    for axis, values in GREENFIELD_GRID.items():
        assert constructed[axis] == [_oracle_label(axis, v) for v in values], (
            f"bootstrap constructed {axis} labels diverge from the inline oracle"
        )


# --- consumer parity: _lib.labels terminal-close label set ----------------


def test_lib_labels_terminal_and_non_terminal_sets_byte_identical() -> None:
    """`_lib.labels` builds the close-reconcile label set through the seam; the
    set must match the frozen literals close-issue relied on."""
    from _lib import labels as labels_mod

    assert labels_mod.TERMINAL_STATE_LABEL == "state:done"
    assert labels_mod.NON_TERMINAL_STATE_LABELS == (
        "state:todo",
        "state:backlog",
        "state:in-progress",
        "state:review",
    )
