"""pre-check's board health check resolves an org-owned board (#444).

The prior `_check_board` ran a bare `gh project view <n>` with no `--owner` and
ignored the cached `projects_v2_node_id`, so it false-negatived on an org-owned
board (an ownerless `gh project view 2` fails; `--owner <org>` or the cached
node id resolves). The runtime create path already gets this right —
`create-issue._resolve_project_node_id` is cache-first on `projects_v2_node_id`
and `_gh_add_to_board` threads `--owner`. This mirrors that ordering.

These exercise `_check_board` directly with `subprocess.run` monkeypatched, so
no network is touched. They pin: the cache short-circuits (no gh call); a cache
miss threads `--owner` and passes for an org-owned board; the repo-owned board
path (owner threaded, view succeeds) is unchanged; and a genuine failure still
reports `fail`.
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
    spec = importlib.util.spec_from_file_location("pm_pre_check_board", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_pre_check_board"] = module
    spec.loader.exec_module(module)
    yield module


class _Proc:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_check_board_none_id_fails(pc) -> None:
    """No `projects_v2_board_id` while a board is declared ⇒ fail (unchanged)."""
    result = pc._check_board(None)
    assert result.status == "fail"
    assert "no projects_v2_board_id" in result.detail


def test_check_board_cached_node_id_short_circuits_no_gh_call(pc, monkeypatch) -> None:
    """A cached `projects_v2_node_id` is sufficient evidence — no `gh project
    view` is issued at all (the cache-first arm mirroring the create path)."""
    def boom(*a, **k):  # pragma: no cover — must not be reached on a cache hit
        raise AssertionError("no gh call may run when projects_v2_node_id is cached")

    monkeypatch.setattr(pc.subprocess, "run", boom)
    result = pc._check_board(2, config={"projects_v2_node_id": "PVT_cached"})
    assert result.status == "ok"
    assert "cached node id" in result.detail


def test_check_board_empty_cache_falls_through_to_live_view(pc, monkeypatch) -> None:
    """An empty-string cache value is treated as absent → live-resolve (not a
    spurious pass on a blank node id)."""
    captured: dict = {}

    def fake_run(cmd, *a, **k):
        captured["cmd"] = cmd
        return _Proc(0, stdout='{"id": "PVT_live", "number": 2}')

    monkeypatch.setattr(pc.subprocess, "run", fake_run)
    result = pc._check_board(2, config={"projects_v2_node_id": ""}, owner="an-org")
    assert result.status == "ok"
    assert captured["cmd"][:3] == ["gh", "project", "view"]


def test_check_board_org_owned_threads_owner_and_passes(pc, monkeypatch) -> None:
    """#444 core: on a cache miss the check threads `--owner`, which resolves an
    org-owned board that a bare `gh project view` would false-negative on."""
    captured: dict = {}

    def fake_run(cmd, *a, **k):
        captured["cmd"] = cmd
        # Model the org-owned board: only the owner-threaded view succeeds.
        if "--owner" in cmd:
            return _Proc(0, stdout='{"id": "PVT_org", "number": 2}')
        return _Proc(1, stderr="owner-less lookup failed")

    monkeypatch.setattr(pc.subprocess, "run", fake_run)
    result = pc._check_board(2, config={}, owner="ai-platform-incubation")
    assert result.status == "ok"
    assert "--owner" in captured["cmd"]
    assert captured["cmd"][captured["cmd"].index("--owner") + 1] == "ai-platform-incubation"


def test_check_board_repo_owned_owner_threaded_passes(pc, monkeypatch) -> None:
    """The repo-owned board path is unchanged: the owner-threaded view succeeds
    and the check passes (the owner is harmless when the board is repo-owned)."""
    def fake_run(cmd, *a, **k):
        return _Proc(0, stdout='{"id": "PVT_repo", "number": 5}')

    monkeypatch.setattr(pc.subprocess, "run", fake_run)
    result = pc._check_board(5, config={}, owner="a-user")
    assert result.status == "ok"
    assert "board #5 resolves" in result.detail


def test_check_board_genuine_failure_still_fails(pc, monkeypatch) -> None:
    """A board that resolves under NEITHER the cache NOR an owner-threaded view
    still reports `fail` — the fix widens what passes, it does not mask failures.
    The failure detail names the owner-threaded command so the remediation is
    actionable."""
    def fake_run(cmd, *a, **k):
        return _Proc(1, stderr="no such project")

    monkeypatch.setattr(pc.subprocess, "run", fake_run)
    result = pc._check_board(9, config={}, owner="an-org")
    assert result.status == "fail"
    assert "--owner an-org" in result.detail


def test_check_board_no_owner_no_cache_uses_ownerless_view(pc, monkeypatch) -> None:
    """With neither a cache nor a resolvable owner, the check falls back to the
    bare (ownerless) `gh project view` — preserving the prior behaviour for the
    case where the owner could not be resolved (`<unresolved>`)."""
    captured: dict = {}

    def fake_run(cmd, *a, **k):
        captured["cmd"] = cmd
        return _Proc(0, stdout='{"id": "PVT_x", "number": 3}')

    monkeypatch.setattr(pc.subprocess, "run", fake_run)
    result = pc._check_board(3, config={}, owner=None)
    assert result.status == "ok"
    assert "--owner" not in captured["cmd"]
