"""Workstream-mutator constraint-1 gate (RF-2, ADR-026, Task #265).

The five workstream-label MUTATORS (add / remove / merge / rename /
split-workstream) create / delete / rename kit `workstream:*` labels via
`gh label`. Under a PRESENT substrate-map whose `workstream` axis is
`unsupported` (or absent — absent ≡ unsupported), creating a kit `workstream:*`
label would violate "never write an unmanaged label" (DEC-036 / EPIC #217
constraint 1).

Before this fix the mutators ran `gh label create/delete` with no map check —
a LIVE constraint-1 hole, only TODO-deferred. The minimal safe gate is
`axis_labels.workstream_mutator_refusal`: each mutator calls it after the
membership check and REFUSES (exit 1) before any `gh label` op when the axis is
unsupported. Greenfield (no map) is unchanged.

This file pins:
  * the shared gate helper's ternary (greenfield ⇒ proceed; served ⇒ proceed;
    unsupported / absent ⇒ refuse);
  * a `main()`-level proof that an unsupported-workstream `add-workstream`
    REFUSES with exit 1 and issues NO `gh label create` (the mutation-proof: a
    monkeypatched `gh_run` that fails the test if it ever sees `gh label`);
  * greenfield parity — no map ⇒ the gate is inert.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from ruamel.yaml import YAML

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from _lib import axis_labels  # noqa: E402


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def aw():
    return _load("pm_add_workstream_gate", "add-workstream.py")


def _write_substrate_map(capability_root: Path, axes: dict) -> None:
    """Write a `project/substrate-map.yaml` under a temp capability root."""
    project = capability_root / "project"
    project.mkdir(parents=True, exist_ok=True)
    yaml = YAML(typ="safe")
    with (project / "substrate-map.yaml").open("w", encoding="utf-8") as f:
        yaml.dump({"axes": axes}, f)


# --- the shared gate helper -----------------------------------------------


def test_gate_greenfield_no_map_proceeds(tmp_path) -> None:
    """No substrate-map ⇒ the gate is inert (returns None ⇒ mutator proceeds)."""
    # tmp_path has no substrate-map.yaml under it.
    assert axis_labels.workstream_mutator_refusal(tmp_path) is None


def test_gate_unsupported_workstream_refuses(tmp_path) -> None:
    """workstream `unsupported` ⇒ a refusal string (mutator must refuse)."""
    _write_substrate_map(tmp_path, {"workstream": {"unsupported": True}})
    refusal = axis_labels.workstream_mutator_refusal(tmp_path)
    assert refusal is not None
    assert "unsupported" in refusal
    assert "#264" in refusal  # points at the richer-behaviour Feature


def test_gate_absent_workstream_in_present_map_refuses(tmp_path) -> None:
    """workstream ABSENT from a present map ⇒ unsupported (load-bearing rule) ⇒
    refuse."""
    _write_substrate_map(tmp_path, {"priority": {"label": {"remap": {"High": "P0"}}}})
    assert axis_labels.workstream_mutator_refusal(tmp_path) is not None


def test_gate_served_workstream_label_bound_proceeds(tmp_path) -> None:
    """workstream bound (e.g. to a `label` remap) ⇒ SERVED ⇒ the minimal gate
    proceeds (richer validate-against-the-set behaviour is #264, not this gate)."""
    _write_substrate_map(
        tmp_path, {"workstream": {"label": {"remap": {"cli": "area/cli"}}}}
    )
    assert axis_labels.workstream_mutator_refusal(tmp_path) is None


# --- main()-level mutation-proof: refuse before any `gh label` op ----------


def test_add_workstream_main_refuses_before_gh_label_under_unsupported_map(
    aw, tmp_path, monkeypatch
) -> None:
    """An unsupported-workstream `add-workstream` REFUSES with exit 1 and issues
    NO `gh label create`. `gh_run` is monkeypatched to fail the test if it is
    ever asked to run a `gh label` command — the call-site mutation-proof that
    no unmanaged label is created."""
    _write_substrate_map(tmp_path, {"workstream": {"unsupported": True}})

    def fail_on_gh_label(cmd, config, *, check=True, **kwargs):
        # Any gh label op under an unsupported map is a constraint-1 violation.
        if "label" in cmd:
            raise AssertionError(f"gh label op attempted under unsupported map: {cmd}")
        raise AssertionError(f"unexpected gh_run call: {cmd}")

    monkeypatch.setattr(aw, "gh_run", fail_on_gh_label)
    # Open membership (no members.yaml) ⇒ the invoker passes the membership gate,
    # so the constraint-1 gate is what stops the mutator.
    monkeypatch.setattr(sys, "argv", [
        "add-workstream.py", "cli",
        "--capability-root", str(tmp_path),
        "--yes",
    ])
    rc = aw.main()
    assert rc == 1  # refusal exit code


def test_add_workstream_main_greenfield_reaches_label_step(
    aw, tmp_path, monkeypatch
) -> None:
    """Greenfield parity: with NO substrate-map the gate is inert, so a
    label-substrate `add-workstream` proceeds to the `gh label create` step
    (here recorded, not actually run) — demonstrating the gate does not change
    greenfield behaviour."""
    # No substrate-map under tmp_path ⇒ greenfield.
    seen: list[list[str]] = []

    def record_gh(cmd, config, *, check=True, **kwargs):
        seen.append(cmd)

        class _Proc:
            returncode = 0
            stderr = ""
            stdout = ""

        return _Proc()

    monkeypatch.setattr(aw, "gh_run", record_gh)
    monkeypatch.setattr(sys, "argv", [
        "add-workstream.py", "cli",
        "--capability-root", str(tmp_path),
        "--yes",
    ])
    rc = aw.main()
    assert rc == 0
    # Greenfield label-substrate adopter ⇒ the gh label create step ran.
    assert any("label" in cmd and "create" in cmd for cmd in seen), seen
