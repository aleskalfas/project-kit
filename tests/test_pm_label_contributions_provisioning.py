"""Bootstrap + pre-check integration for contributed labels (DEC-042).

Exercises the two pm surfaces the label-contribution mechanism touches:

  * bootstrap `_plan_contributed_labels` / `_compute_plan` — a manifest-
    registered capability shipping a `label-contributions.yaml` gets its label
    planned for creation (through the per-label path, carrying its own
    color/description), and the plan is idempotent when the label already exists.
  * pre-check `_check_contributed_labels` — warns (never fails) on a missing
    contributed label, is silent for a pm-only adopter, and passes when present.

Both build a synthetic repo tree whose capability_root is
`<repo>/.pkit/capabilities/project-management` so the collector's manifest walk
(repo_root = capability_root.parent.parent.parent) resolves the synthetic
manifest.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = (
    REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
)
BOOTSTRAP_PATH = SCRIPTS_DIR / "bootstrap.py"
PRECHECK_PATH = SCRIPTS_DIR / "pre-check.py"


def _load_script(module_name: str, path: Path):
    scripts_dir_str = str(SCRIPTS_DIR)
    inserted = scripts_dir_str not in sys.path
    if inserted:
        sys.path.insert(0, scripts_dir_str)
    try:
        spec = importlib.util.spec_from_file_location(module_name, path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        if inserted and scripts_dir_str in sys.path:
            sys.path.remove(scripts_dir_str)


@pytest.fixture(scope="module")
def bs():
    return _load_script("pm_bootstrap_labelcontrib_under_test", BOOTSTRAP_PATH)


@pytest.fixture(scope="module")
def pc():
    return _load_script("pm_precheck_labelcontrib_under_test", PRECHECK_PATH)


# --- synthetic repo tree ---------------------------------------------


_NEEDS_DESIGN = (
    "schema_version: 1\n"
    "labels:\n"
    "  - id: needs-design\n"
    "    default_name: needs-design\n"
    "    color: d4c5f9\n"
    "    description: Requires design input.\n"
)


def _make_repo(tmp_path: Path, *, contributor: bool) -> Path:
    """Build a repo tree; return the pm capability_root.

    Registers project-management always, and (when `contributor`) a synthetic
    `ux-ui-design` capability shipping a needs-design label contribution.
    """
    caps = ["project-management"] + (["ux-ui-design"] if contributor else [])
    lines = ["schema_version: 1", "backbone_version: 1.0.0", "components:"]
    lines += [
        "  - kind: adapter",
        "    name: claude-code",
        "    manifest: .pkit/adapters/claude-code/project/manifest.yaml",
    ]
    for name in caps:
        lines += [
            "  - kind: capability",
            f"    name: {name}",
            f"    manifest: .pkit/capabilities/{name}/manifest.yaml",
        ]
    (tmp_path / ".pkit").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".pkit" / "manifest.yaml").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )

    cap_root = tmp_path / ".pkit" / "capabilities" / "project-management"
    cap_root.mkdir(parents=True, exist_ok=True)

    if contributor:
        design_dir = tmp_path / ".pkit" / "capabilities" / "ux-ui-design"
        design_dir.mkdir(parents=True, exist_ok=True)
        (design_dir / "label-contributions.yaml").write_text(
            _NEEDS_DESIGN, encoding="utf-8"
        )
    return cap_root


# --- bootstrap: per-label create path + idempotency -------------------


@pytest.fixture
def classification() -> dict:
    return {"axes": {"type": {"values": ["feature"]}, "priority": {"values": ["High"]}}}


def _compute_plan(bs, cap_root: Path, classification, existing: set[str]):
    original = bs._fetch_existing_labels
    bs._fetch_existing_labels = lambda: existing
    try:
        return bs._compute_plan(
            config={"has_projects_v2_board": True},  # board mode: quiet axis noise
            classification=classification,
            has_board=True,
            with_starter_epic=False,
            capability_root=cap_root,
        )
    finally:
        bs._fetch_existing_labels = original


def test_bootstrap_plans_contributed_label_create(bs, tmp_path, classification) -> None:
    cap_root = _make_repo(tmp_path, contributor=True)
    plan = _compute_plan(bs, cap_root, classification, existing=set())

    created = {c.default_name: c for c in plan.contributed_label_creates}
    assert "needs-design" in created
    # Carries its OWN color/description, not an axis palette value.
    label = created["needs-design"]
    assert label.color == "d4c5f9"
    assert label.description == "Requires design input."
    assert label.capability == "ux-ui-design"
    assert plan.has_creates() is True


def test_bootstrap_contributed_label_idempotent_when_present(
    bs, tmp_path, classification
) -> None:
    cap_root = _make_repo(tmp_path, contributor=True)
    plan = _compute_plan(bs, cap_root, classification, existing={"needs-design"})

    assert plan.contributed_label_creates == []
    assert "needs-design" in plan.contributed_label_exists


def test_bootstrap_no_contributed_labels_for_pm_only_adopter(
    bs, tmp_path, classification
) -> None:
    cap_root = _make_repo(tmp_path, contributor=False)
    plan = _compute_plan(bs, cap_root, classification, existing=set())
    assert plan.contributed_label_creates == []
    assert plan.contributed_label_exists == []


def test_bootstrap_contributed_create_does_not_route_through_axis_path(
    bs, tmp_path, classification
) -> None:
    # A contributed label is not an axis label: it must not appear in the
    # axis-keyed label_creates list (which _execute_plan groups by axis).
    cap_root = _make_repo(tmp_path, contributor=True)
    plan = _compute_plan(bs, cap_root, classification, existing=set())
    axis_names = [name for _, name in plan.label_creates]
    assert "needs-design" not in axis_names


# --- pre-check: warn on missing contributed label ---------------------


def _run_check(pc, cap_root: Path, existing_labels: set[str], monkeypatch):
    """Invoke _check_contributed_labels with gh label list mocked."""
    import subprocess as _sp
    import json as _json

    class _Proc:
        returncode = 0
        stdout = _json.dumps([{"name": n} for n in existing_labels])
        stderr = ""

    monkeypatch.setattr(_sp, "run", lambda *a, **k: _Proc())
    return pc._check_contributed_labels(cap_root)


def test_precheck_warns_on_missing_contributed_label(pc, tmp_path, monkeypatch) -> None:
    cap_root = _make_repo(tmp_path, contributor=True)
    results = _run_check(pc, cap_root, existing_labels=set(), monkeypatch=monkeypatch)
    missing = [r for r in results if r.status == "warn" and "needs-design" in r.label]
    assert missing, "a missing contributed label must WARN"
    # It is a warning, not a fail — never flips the exit code.
    assert all(r.status != "fail" for r in results)
    assert any("bootstrap" in (r.remediation or "") for r in missing)


def test_precheck_ok_when_contributed_label_present(pc, tmp_path, monkeypatch) -> None:
    cap_root = _make_repo(tmp_path, contributor=True)
    results = _run_check(
        pc, cap_root, existing_labels={"needs-design"}, monkeypatch=monkeypatch
    )
    assert any(r.status == "ok" for r in results)
    assert all(r.status != "warn" for r in results)


def test_precheck_silent_for_pm_only_adopter(pc, tmp_path, monkeypatch) -> None:
    cap_root = _make_repo(tmp_path, contributor=False)
    results = _run_check(pc, cap_root, existing_labels=set(), monkeypatch=monkeypatch)
    # No contributor → no results at all (no noise for a pm-only adopter).
    assert results == []


def test_precheck_warns_on_malformed_declaration(pc, tmp_path, monkeypatch) -> None:
    cap_root = _make_repo(tmp_path, contributor=True)
    # Corrupt the declaration to a malformed shape.
    (tmp_path / ".pkit" / "capabilities" / "ux-ui-design" / "label-contributions.yaml").write_text(
        "schema_version: 1\nlabels: not-a-list\n", encoding="utf-8"
    )
    results = _run_check(pc, cap_root, existing_labels=set(), monkeypatch=monkeypatch)
    assert any(r.status == "warn" for r in results)
    assert all(r.status != "fail" for r in results)
