"""pre-check degrades to a capability matrix under a substrate-map (DEC-036 / ADR-026, Task B).

Greenfield (no substrate-map.yaml) behaviour is unchanged: every axis is served
via the kit's own labels, so the per-axis kit-label checks run exactly as
before. With a map present, pre-check reports a per-axis capability matrix
(served via binding / degraded) and SKIPS the kit-label existence checks for
every axis — it never hard-refuses on labels a brownfield adopter cannot create.

These exercise the pure (non-gh) pieces pre-check uses for the matrix: the
substrate-map loader, `_check_substrate_capability_matrix`, and the per-axis
kit-label gating. The gh-dependent checks (`_check_labels`'s `gh label list`)
are not invoked here — the gating decision (`_axis_expects_kit_labels`) is what
Task B changed and is what we pin.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
SCRIPT = SCRIPTS_DIR / "pre-check.py"


@pytest.fixture(scope="module")
def pc():
    sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location("pm_pre_check_substrate", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_pre_check_substrate"] = module
    spec.loader.exec_module(module)
    yield module
    sys.path.remove(str(SCRIPTS_DIR))


@pytest.fixture(scope="module")
def axis_labels():
    sys.path.insert(0, str(SCRIPTS_DIR))
    from _lib import axis_labels as mod
    yield mod


def _write_map(cap_root: Path, body: str) -> None:
    (cap_root / "project").mkdir(parents=True, exist_ok=True)
    (cap_root / "project" / "substrate-map.yaml").write_text(body, encoding="utf-8")


AUJ_BODY = """\
schema_version: 1
axes:
  priority:
    label:
      remap:
        High: P0
        Medium: P1
        Low: P2
    default: P1
  type:
    title-prefix:
      remap:
        task: "[Task]"
        epic: "[Epic]"
  workstream:
    unsupported: true
  state:
    derive:
      from: open-closed
      states:
        open: open & not Blocked
        done: closed
"""


# --- loader ----------------------------------------------------------------


def test_no_map_loads_as_none(axis_labels, tmp_path: Path) -> None:
    """No file ⇒ greenfield (None), the seam stays inert."""
    cap_root = tmp_path / "cap"
    (cap_root / "project").mkdir(parents=True)
    assert axis_labels.load_substrate_map(cap_root) is None


def test_present_map_loads_axes(axis_labels, tmp_path: Path) -> None:
    cap_root = tmp_path / "cap"
    _write_map(cap_root, AUJ_BODY)
    sm = axis_labels.load_substrate_map(cap_root)
    assert sm is not None
    assert set(sm.axes) == {"priority", "type", "workstream", "state"}


def test_present_map_loads_containment_from_file(axis_labels, tmp_path: Path) -> None:
    """The top-level `containment:` key round-trips through the loader (DEC-039 D2
    / ADR-035): an explicit `textual` parses to the textual mode, and a body with
    no `containment:` key defaults to native."""
    cap_root = tmp_path / "cap"
    _write_map(cap_root, AUJ_BODY + "containment: textual\n")
    sm = axis_labels.load_substrate_map(cap_root)
    assert sm is not None
    assert sm.containment == "textual"
    assert axis_labels.containment_mode(sm) == "textual"

    cap_root2 = tmp_path / "cap2"
    _write_map(cap_root2, AUJ_BODY)
    sm2 = axis_labels.load_substrate_map(cap_root2)
    assert sm2 is not None
    assert sm2.containment == "native"  # absent key ⇒ native default


def test_unparseable_map_fails_closed_to_degrade_all(axis_labels, tmp_path: Path) -> None:
    """A present-but-broken map degrades every axis — it never re-enters
    greenfield (fail closed)."""
    cap_root = tmp_path / "cap"
    _write_map(cap_root, "axes: [this is not a mapping\n")
    sm = axis_labels.load_substrate_map(cap_root)
    assert sm is not None  # present, not None
    for axis in axis_labels.AXES:
        assert axis_labels.axis_disposition(axis, sm) == "unsupported"


# --- the capability matrix -------------------------------------------------


def test_matrix_reports_served_and_degraded(pc, axis_labels) -> None:
    sm = axis_labels.load_substrate_map  # sanity: callable present
    parsed = axis_labels.SubstrateMap(
        axes={
            "priority": {"label": {"remap": {"High": "P0"}}},
            "type": {"title-prefix": {"remap": {"task": "[Task]"}}},
            "workstream": {"unsupported": True},
            # state absent ⇒ treated as unsupported
        }
    )
    results = pc._check_substrate_capability_matrix(parsed)
    by_label = {r.label: r for r in results}

    # Header present.
    assert any(r.label == "substrate-map present" for r in results)
    # Bound axes report served (ok).
    assert by_label["axis `priority` served"].status == "ok"
    assert by_label["axis `type` served"].status == "ok"
    # Unsupported + absent axes report degraded (skip, NOT fail).
    assert by_label["axis `workstream` degraded"].status == "skip"
    assert by_label["axis `state` degraded"].status == "skip"
    # The matrix never fails.
    assert all(r.status != "fail" for r in results)


def test_absent_axis_matrix_line_says_not_greenfield(pc, axis_labels) -> None:
    parsed = axis_labels.SubstrateMap(axes={"priority": {"label": {"remap": {"High": "P0"}}}})
    results = pc._check_substrate_capability_matrix(parsed)
    state_line = next(r for r in results if r.label == "axis `state` degraded")
    assert "NOT greenfield" in state_line.detail


# --- per-axis kit-label gating --------------------------------------------


def test_kit_labels_expected_only_in_greenfield(pc, axis_labels) -> None:
    """No map ⇒ kit labels expected (the original hard-check runs). Map present
    ⇒ no axis expects kit labels (each is bound or degraded)."""
    for axis in axis_labels.AXES:
        assert pc._axis_expects_kit_labels(axis, None) is True

    parsed = axis_labels.SubstrateMap(
        axes={"priority": {"label": {"remap": {"High": "P0"}}}, "workstream": {"unsupported": True}}
    )
    for axis in axis_labels.AXES:
        assert pc._axis_expects_kit_labels(axis, parsed) is False


def test_skip_line_distinguishes_bound_from_degraded(pc, axis_labels) -> None:
    parsed = axis_labels.SubstrateMap(
        axes={"priority": {"label": {"remap": {"High": "P0"}}}, "workstream": {"unsupported": True}}
    )
    bound = pc._axis_label_check_skipped("priority", parsed)
    degraded = pc._axis_label_check_skipped("workstream", parsed)
    assert bound.status == "skip" and "bound" in bound.detail
    assert degraded.status == "skip" and "unsupported" in degraded.detail


def test_state_label_check_degrades_under_derive_binding(pc, axis_labels) -> None:
    """`_check_state_labels` returns a skip (not a gh-dependent fail) when the
    state axis is bound to a derive predicate — no `state:*` labels to demand."""
    parsed = axis_labels.SubstrateMap(
        axes={"state": {"derive": {"from": "open-closed", "states": {"done": "closed"}}}}
    )
    result = pc._check_state_labels(Path("/nonexistent"), parsed)
    assert result.status == "skip"
    assert "derive" in result.detail or "not required" in result.detail


# --- title-prefix alignment: the RF-1 hard-refuse hole (DEC-036 / ADR-026) -

# A capability_root with the kit schemas — the title-prefix check reads
# issue-types.yaml + classification.yaml from there. Point at the live install
# so the kit prefix vocabulary is the real one.
_LIVE_CAP_ROOT = (
    REPO_ROOT / ".pkit" / "capabilities" / "project-management"
)


class _FakeProc:
    def __init__(self, returncode: int, stdout: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = ""


def _stub_issue_list(pc, monkeypatch, issues: list[dict]) -> None:
    """Make `gh issue list` (the only subprocess this check runs) return `issues`."""
    def fake_run(cmd, *args, **kwargs):
        if cmd[:3] == ["gh", "issue", "list"]:
            return _FakeProc(0, json.dumps(issues))
        return _FakeProc(1, "")
    monkeypatch.setattr(pc.subprocess, "run", fake_run)


# A native-prefixed issue: `[Epic]` (title case) is the adopter's own declared
# prefix in the AUJ map, but the kit uses `EPIC` (upper) — so this prefix is in
# the adopter's vocabulary yet NOT the kit's. It proves the present-map path
# validates against the ADOPTER's prefixes, not the kit set. A no-prefix issue
# stresses the second hard-refuse arm.
_NATIVE_PREFIX_ISSUE = {"number": 1, "title": "[Epic] do the thing"}
_NO_PREFIX_ISSUE = {"number": 2, "title": "untitled work item"}


def _auj_map(axis_labels):
    """The AUJ fixture: `type` bound to a `[Task]`/`[Epic]` title-prefix remap."""
    return axis_labels.SubstrateMap(
        axes={
            "priority": {"label": {"remap": {"High": "P0"}}},
            "type": {"title-prefix": {"remap": {"task": "[Task]", "epic": "[Epic]"}}},
            "workstream": {"unsupported": True},
        }
    )


def test_title_prefix_present_map_never_fails_on_native_prefix(
    pc, axis_labels, monkeypatch
) -> None:
    """RF-1: under a present map with `type` title-prefix-bound, an adopter's
    NATIVE-prefixed issue does NOT make the check fail — it validates against the
    adopter's own declared prefixes (advisory)."""
    _stub_issue_list(pc, monkeypatch, [_NATIVE_PREFIX_ISSUE])
    results = pc._check_title_prefix_alignment(_LIVE_CAP_ROOT, _auj_map(axis_labels))
    assert all(r.status != "fail" for r in results)


def test_title_prefix_present_map_never_fails_on_no_prefix(
    pc, axis_labels, monkeypatch
) -> None:
    """RF-1: under a present map, an issue with NO bracket prefix degrades to a
    skip, never a fail — the second hard-refuse arm is closed too."""
    _stub_issue_list(pc, monkeypatch, [_NO_PREFIX_ISSUE])
    results = pc._check_title_prefix_alignment(_LIVE_CAP_ROOT, _auj_map(axis_labels))
    assert all(r.status != "fail" for r in results)
    # The no-prefix issue is reported (advisory), not silently dropped.
    assert any("without bracket prefix" in r.label for r in results)


def test_title_prefix_present_map_unrecognised_prefix_degrades(
    pc, axis_labels, monkeypatch
) -> None:
    """RF-1: even a prefix outside the adopter's OWN declared set degrades to a
    skip advisory under a present map — the check never returns fail with a map."""
    _stub_issue_list(pc, monkeypatch, [{"number": 9, "title": "[Wat] mystery"}])
    results = pc._check_title_prefix_alignment(_LIVE_CAP_ROOT, _auj_map(axis_labels))
    assert all(r.status != "fail" for r in results)


def test_title_prefix_type_unsupported_skips_entirely(
    pc, axis_labels, monkeypatch
) -> None:
    """When `type` is not title-prefix-bound under a present map (here absent ⇒
    unsupported), the kit prefix vocabulary does not apply — skip, never fail."""
    _stub_issue_list(pc, monkeypatch, [_NO_PREFIX_ISSUE, _NATIVE_PREFIX_ISSUE])
    parsed = axis_labels.SubstrateMap(axes={"priority": {"label": {"remap": {"High": "P0"}}}})
    results = pc._check_title_prefix_alignment(_LIVE_CAP_ROOT, parsed)
    assert len(results) == 1
    assert results[0].status == "skip"
    assert "not served via kit title-prefixes" in results[0].detail


def test_title_prefix_greenfield_still_fails_on_unknown_prefix(
    pc, axis_labels, monkeypatch
) -> None:
    """Greenfield parity: with NO map, an unrecognised prefix is still a hard
    fail (the original behaviour is unchanged)."""
    _stub_issue_list(pc, monkeypatch, [{"number": 9, "title": "[Wat] mystery"}])
    results = pc._check_title_prefix_alignment(_LIVE_CAP_ROOT, None)
    assert any(r.status == "fail" for r in results)


def test_title_prefix_greenfield_still_fails_on_no_prefix(
    pc, axis_labels, monkeypatch
) -> None:
    """Greenfield parity: with NO map, a no-prefix issue is still a hard fail."""
    _stub_issue_list(pc, monkeypatch, [_NO_PREFIX_ISSUE])
    results = pc._check_title_prefix_alignment(_LIVE_CAP_ROOT, None)
    assert any(r.status == "fail" for r in results)

