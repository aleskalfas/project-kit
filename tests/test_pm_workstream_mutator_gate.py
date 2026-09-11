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

from _lib import axis_carriage, axis_labels  # noqa: E402


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


@pytest.fixture(scope="module")
def rw():
    return _load("pm_remove_workstream_gate", "remove-workstream.py")


def _mark_bootstrapped(cap_root: Path) -> None:
    """Make a staged tree look like the bootstrapped project it stands in for.

    Every pm verb except the five setup/diagnosis ones refuses a project with no
    bootstrap stamp or no adopter config (the #747 prerequisite gate); a staged
    tree standing in for a live project is a bootstrapped one. The config is
    seeded only when absent, so a test that stages its own keeps it, and the
    stamp is left unbound (`repo:` null) so no git remote is needed in a tmp tree.
    """
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
    _mark_bootstrapped(tmp_path)
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
    _mark_bootstrapped(tmp_path)
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


# --- carriage gates the kit-LABEL half (#712 / DEC-051) ----------------------
#
# The refusal above covers the one arm where the mutator has nothing to do at all.
# The kit-label half needs a SECOND, different gate, and the difference is the
# hazard [project-management:DEC-051-axis-carriage-activation] names: the mutators
# gate kit-label creation on the board FLAG and build the label with the greenfield
# constructor, so swapping the flag for the accessor naively turns kit-label
# mutation ON for a board adopter with a label-bound workstream. `add` would create
# an unmanaged `workstream:<slug>`; `remove` / `merge` / `split` would issue
# `gh label delete` and `rename` a `gh label edit` — against a name the kit never
# owned, covered by no guard. The gate is therefore "the kit's labels ARE this
# axis's substrate" (`expects_kit_labels`), never "the axis is not on the board".


BOARD = {"has_projects_v2_board": True, "projects_v2_board_id": 7}
NO_BOARD = {"has_projects_v2_board": False}


def test_kit_label_mutation_note_is_silent_in_greenfield() -> None:
    """Greenfield: the kit's `workstream:*` labels ARE the adopter's substrate, so
    the mutators run unchanged and the note is None."""
    assert axis_carriage.kit_label_mutation_note("workstream", NO_BOARD, None) is None


def test_kit_label_mutation_note_fires_for_a_label_bound_axis_under_a_board() -> None:
    """The hazard case: a board configured AND a `label` binding. Carriage says the
    adopter's own labels, so the kit-label half is suppressed — and the note names
    the substrate, because "no label was created" is only actionable with a why."""
    sm = axis_labels.SubstrateMap(
        axes={"workstream": {"label": {"remap": {"cli": "area/cli"}}}}
    )
    note = axis_carriage.kit_label_mutation_note("workstream", BOARD, sm)
    assert note is not None
    assert "your OWN labels" in note
    assert "#264" in note


def test_kit_label_mutation_note_fires_for_a_board_carried_axis() -> None:
    """Today's behaviour, preserved: a board adopter with no binding still skips
    the label half — now with a reason attached instead of silently."""
    note = axis_carriage.kit_label_mutation_note("workstream", BOARD, None)
    assert note is not None
    assert "Projects-v2 board" in note


def _stage_label_bound_board_adopter(cap_root: Path) -> None:
    """A board adopter whose map binds `workstream` to their own labels — the
    reported #708 shape, applied to the workstream axis."""
    project = cap_root / "project"
    project.mkdir(parents=True, exist_ok=True)
    (project / "config.yaml").write_text(
        "schema_version: 1\ndefault_branch: main\nworkstreams: [cli]\n"
        "has_projects_v2_board: true\nprojects_v2_board_id: 7\n",
        encoding="utf-8",
    )
    _write_substrate_map(
        cap_root, {"workstream": {"label": {"remap": {"cli": "area/cli"}}}}
    )
    _mark_bootstrapped(cap_root)


def test_add_workstream_creates_no_kit_label_for_a_label_bound_board_adopter(
    aw, tmp_path, monkeypatch
) -> None:
    """The mutator still updates the declared vocabulary (so it is not refused),
    but issues NO `gh label` op: creating `workstream:<slug>` here would be an
    unmanaged label, and not even the one the adopter's remap names."""
    _stage_label_bound_board_adopter(tmp_path)

    def fail_on_gh_label(cmd, config, *, check=True, **kwargs):
        if "label" in cmd:
            raise AssertionError(f"gh label op on a label-bound axis: {cmd}")
        raise AssertionError(f"unexpected gh_run call: {cmd}")

    monkeypatch.setattr(aw, "gh_run", fail_on_gh_label)
    monkeypatch.setattr(sys, "argv", [
        "add-workstream.py", "docs",
        "--capability-root", str(tmp_path),
        "--yes",
    ])
    assert aw.main() == 0
    assert "docs" in (tmp_path / "project" / "workstreams.yaml").read_text(
        encoding="utf-8"
    )


def test_remove_workstream_deletes_no_kit_label_for_a_label_bound_board_adopter(
    rw, tmp_path, monkeypatch
) -> None:
    """The sharper edge of the same hazard: a `gh label delete` here would destroy
    a label the kit never created — worse than writing one, and covered by no
    guard."""
    _stage_label_bound_board_adopter(tmp_path)
    (tmp_path / "project" / "workstreams.yaml").write_text(
        "schema_version: 1\nworkstreams:\n  cli:\n    name: cli\n    status: active\n",
        encoding="utf-8",
    )

    def fail_on_gh_label(cmd, config, *, check=True, **kwargs):
        if "label" in cmd:
            raise AssertionError(f"gh label op on a label-bound axis: {cmd}")
        raise AssertionError(f"unexpected gh_run call: {cmd}")

    monkeypatch.setattr(rw, "gh_run", fail_on_gh_label)
    monkeypatch.setattr(sys, "argv", [
        "remove-workstream.py", "cli",
        "--capability-root", str(tmp_path),
        "--yes",
    ])
    assert rw.main() == 0
    # The vocabulary edit still happened — the mutator ran, it just did not touch
    # a label substrate it does not own.
    assert "cli" not in (tmp_path / "project" / "workstreams.yaml").read_text(
        encoding="utf-8"
    )
