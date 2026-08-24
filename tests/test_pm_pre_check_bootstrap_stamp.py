"""pre-check reports what the prerequisite gate sees (#747).

The gate makes every non-exempt pm verb refuse on an un-bootstrapped project.
The operator who hits that refusal is told to run `pre-check` for the full
diagnosis — so the diagnosis has to *carry* the answer. This pins the three
outcomes of the check that does:

  * **fail** when the gate refuses — with the gate's own reason, so "why is
    everything refusing?" is answered in one line, and with the bootstrap
    command as remediation;
  * **warn** when the stamp is older than the installed capability version —
    the staleness signal the stamp records a version *for*. Non-blocking: most
    upgrades change nothing about what bootstrap provisions, and refusing on
    drift would break every command after every upgrade. Reporting it in the
    deliberate diagnosis (rather than as a banner on every command, which is
    ignored within a week) is the whole design;
  * **ok** when the stamp is present and current.

The check is also pinned to run OUTSIDE the `gh`-missing short-circuit: it is a
local file read, and it is the one prerequisite that must be reportable when the
environment is otherwise broken.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CAPABILITY = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
SCRIPTS_DIR = CAPABILITY / "scripts"
SCRIPT = SCRIPTS_DIR / "pre-check.py"


@pytest.fixture(scope="module")
def pc():
    sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location("pm_pre_check_bootstrap_stamp", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_pre_check_bootstrap_stamp"] = module
    spec.loader.exec_module(module)
    yield module
    sys.path.remove(str(SCRIPTS_DIR))


def _tree(tmp_path: Path, *, version: str = "9.9.9") -> Path:
    cap = tmp_path / ".pkit" / "capabilities" / "project-management"
    (cap / "project").mkdir(parents=True)
    (cap / "package.yaml").write_text(
        "schema_version: 2\ncomponent:\n  kind: capability\n"
        f"  name: project-management\n  version: {version}\n",
        encoding="utf-8",
    )
    (cap / "project" / "config.yaml").write_text(
        "schema_version: 1\ndefault_branch: main\nworkstreams: []\n", encoding="utf-8"
    )
    return cap


def _stamp(cap: Path, *, version: str) -> None:
    (cap / "project" / "bootstrap-stamp.yaml").write_text(
        "schema_version: 1\n"
        "bootstrap:\n"
        "  completed_at: '2026-01-01T00:00:00+00:00'\n"
        f"  capability_version: {version}\n"
        "  by: bootstrap\n"
        "  repo:\n",
        encoding="utf-8",
    )


def test_missing_stamp_fails_with_the_gates_reason_and_the_fix(pc, tmp_path) -> None:
    cap = _tree(tmp_path)
    result = pc._check_bootstrap_stamp(cap)
    assert result.status == "fail"
    assert "never completed `bootstrap`" in result.detail
    # It says what the consequence is, so the operator connects this line to the
    # refusals they are seeing.
    assert "refuses" in result.detail
    assert "bootstrap" in (result.remediation or "")


def test_a_current_stamp_is_ok(pc, tmp_path) -> None:
    cap = _tree(tmp_path, version="9.9.9")
    _stamp(cap, version="9.9.9")
    result = pc._check_bootstrap_stamp(cap)
    assert result.status == "ok"
    assert "9.9.9" in result.detail


def test_a_stale_stamp_warns_without_failing(pc, tmp_path) -> None:
    """The staleness signal: reported, never a refusal — `warn` does not flip
    pre-check's exit code."""
    cap = _tree(tmp_path, version="9.9.9")
    _stamp(cap, version="0.1.0")
    result = pc._check_bootstrap_stamp(cap)
    assert result.status == "warn"
    assert "0.1.0" in result.detail and "9.9.9" in result.detail


def test_a_broken_config_fails_even_with_a_stamp(pc, tmp_path) -> None:
    """A config can break after a successful bootstrap; the check reports that
    as the gate's reason rather than a generic failure."""
    cap = _tree(tmp_path)
    _stamp(cap, version="9.9.9")
    (cap / "project" / "config.yaml").unlink()
    result = pc._check_bootstrap_stamp(cap)
    assert result.status == "fail"
    assert "adopter config is missing" in result.detail


def test_the_stamp_check_runs_before_the_gh_short_circuit(pc, tmp_path, monkeypatch) -> None:
    """With `gh` absent, pre-check short-circuits the remaining checks — but the
    stamp check has already run, because it is local and it is the answer to
    "why is every command refusing?"."""
    cap = _tree(tmp_path)
    monkeypatch.setattr(
        pc, "_check_command_on_path",
        lambda name: pc.CheckResult(f"`{name}` on PATH", "fail", "absent"),
    )
    results = pc._run_all_checks(cap)
    labels = [r.label for r in results]
    assert "bootstrap completed (stamp)" in labels
    assert labels.index("bootstrap completed (stamp)") == 0
    # And the short-circuit still happened (nothing gh-dependent ran).
    assert any(r.label == "remaining checks" and r.status == "skip" for r in results)
