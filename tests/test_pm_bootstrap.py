"""Tests for project-management's bootstrap script.

Covers plan computation — what would be created vs already exists,
with a focus on the state-label additions in label-fallback mode — and
the refusal when no GitHub repository resolves (#2087), driven through
`main()` with `gh` stood in for, so no test reaches GitHub.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CAP_SRC = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
SCRIPT_PATH = CAP_SRC / "scripts" / "bootstrap.py"


@pytest.fixture(scope="module")
def bs():
    module_name = "pm_bootstrap_under_test"
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def classification() -> dict:
    """Minimal classification.yaml-shaped dict."""
    return {
        "axes": {
            "type": {
                "values": ["feature", "bug", "docs"],
            },
            "priority": {
                "values": ["High", "Medium", "Low"],
            },
        },
    }


@pytest.fixture
def workflow_data() -> dict:
    """Minimal workflow.yaml-shaped dict with five states."""
    return {
        "states": [
            {"id": "todo"},
            {"id": "backlog"},
            {"id": "in-progress"},
            {"id": "review"},
            {"id": "done"},
        ],
    }


# --- _resolve_state_ids -----------------------------------------------


def test_resolve_state_ids_reads_from_workflow(bs, tmp_path) -> None:
    """_resolve_state_ids returns state IDs from workflow.yaml in order."""
    schemas_dir = tmp_path / "schemas"
    schemas_dir.mkdir()
    workflow_path = schemas_dir / "workflow.yaml"
    workflow_path.write_text(
        "states:\n  - id: todo\n  - id: backlog\n  - id: in-progress\n  - id: review\n"
        "  - id: done\n",
        encoding="utf-8",
    )
    cap_root = tmp_path
    ids = bs._resolve_state_ids(cap_root)
    assert ids == ["todo", "backlog", "in-progress", "review", "done"]


def test_resolve_state_ids_returns_empty_when_missing(bs, tmp_path) -> None:
    """Missing workflow.yaml returns empty list — no crash."""
    ids = bs._resolve_state_ids(tmp_path)
    assert ids == []


def test_resolve_state_ids_skips_non_string_ids(bs, tmp_path) -> None:
    schemas_dir = tmp_path / "schemas"
    schemas_dir.mkdir()
    workflow_path = schemas_dir / "workflow.yaml"
    workflow_path.write_text(
        "states:\n  - id: todo\n  - id: 42\n  - id: done\n",
        encoding="utf-8",
    )
    ids = bs._resolve_state_ids(tmp_path)
    # 42 is an integer in YAML, not a string — should be filtered out
    assert "todo" in ids
    assert "done" in ids


# --- _compute_plan state-label behaviour ------------------------------


def test_compute_plan_includes_state_labels_in_label_fallback(
    bs, tmp_path, classification, workflow_data
) -> None:
    """In label-fallback mode, plan includes state:* label creates."""
    schemas_dir = tmp_path / "schemas"
    schemas_dir.mkdir()
    (schemas_dir / "workflow.yaml").write_text(
        "states:\n  - id: todo\n  - id: backlog\n  - id: in-progress\n  - id: review\n"
        "  - id: done\n",
        encoding="utf-8",
    )
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Patch _fetch_existing_labels to return an empty set (fresh repo).
    original = bs._fetch_existing_labels
    bs._fetch_existing_labels = lambda: set()
    try:
        plan = bs._compute_plan(
            config={},
            classification=classification,
            with_starter_epic=False,
            capability_root=tmp_path,
        )
    finally:
        bs._fetch_existing_labels = original

    label_names = [name for _, name in plan.label_creates]
    state_label_names = [n for n in label_names if n.startswith("state:")]
    assert "state:todo" in state_label_names
    assert "state:backlog" in state_label_names
    assert "state:in-progress" in state_label_names
    assert "state:review" in state_label_names
    assert "state:done" in state_label_names


def test_compute_plan_skips_existing_state_labels(
    bs, tmp_path, classification, workflow_data
) -> None:
    """State labels already in the repo are recorded as 'exists', not 'creates'."""
    schemas_dir = tmp_path / "schemas"
    schemas_dir.mkdir()
    (schemas_dir / "workflow.yaml").write_text(
        "states:\n  - id: todo\n  - id: backlog\n  - id: in-progress\n  - id: review\n"
        "  - id: done\n",
        encoding="utf-8",
    )

    existing = {"state:todo", "state:backlog", "state:in-progress", "state:review", "state:done"}
    original = bs._fetch_existing_labels
    bs._fetch_existing_labels = lambda: existing
    try:
        plan = bs._compute_plan(
            config={},
            classification=classification,
            with_starter_epic=False,
            capability_root=tmp_path,
        )
    finally:
        bs._fetch_existing_labels = original

    state_creates = [n for _, n in plan.label_creates if n.startswith("state:")]
    assert state_creates == [], "All state labels exist; none should be in creates"
    state_exists = [n for n in plan.label_exists if n.startswith("state:")]
    assert len(state_exists) == 5


def test_compute_plan_omits_state_labels_in_board_mode(
    bs, tmp_path, classification, workflow_data
) -> None:
    """In board mode, state:* labels are NOT created (skip message instead)."""
    schemas_dir = tmp_path / "schemas"
    schemas_dir.mkdir()
    (schemas_dir / "workflow.yaml").write_text(
        "states:\n  - id: todo\n  - id: backlog\n  - id: in-progress\n  - id: review\n"
        "  - id: done\n",
        encoding="utf-8",
    )

    original = bs._fetch_existing_labels
    bs._fetch_existing_labels = lambda: set()
    try:
        plan = bs._compute_plan(
            config={"has_projects_v2_board": True},
            classification=classification,
            with_starter_epic=False,
            capability_root=tmp_path,
        )
    finally:
        bs._fetch_existing_labels = original

    state_creates = [n for _, n in plan.label_creates if n.startswith("state:")]
    assert state_creates == [], "Board mode: state labels should not be in creates"
    state_skipped = any("state:*" in msg for msg in plan.skipped_messages)
    assert state_skipped, "Board mode: should have a skip message for state:* labels"


# --- the greenfield-only refusal (#712 / DEC-051) ---------------------------
#
# bootstrap provisions the KIT's own `<axis>:<value>` labels. Its comment used to
# ASSERT that this was safe by construction — "brownfield adoption enters via
# `adopt-existing`, so this map-blind construction is greenfield-by-construction" —
# with nothing enforcing it. Nothing stopped a run in a repo carrying a
# substrate-map, and it created the full kit palette for every axis: unmanaged
# labels no reader looks at, which is the constraint-1 violation this provisioner
# must never commit. The refusal is now explicit, asked per axis of the carriage
# accessor with the polarity that matters — "do the KIT's labels carry this axis?",
# never "is it on the board?".


def test_compute_plan_creates_no_kit_palette_under_a_present_map(
    bs, tmp_path, classification
) -> None:
    """A present substrate-map ⇒ NO kit axis labels are planned, for any axis, and
    each is skipped with the substrate named."""
    schemas_dir = tmp_path / "schemas"
    schemas_dir.mkdir()
    (schemas_dir / "workflow.yaml").write_text(
        "states:\n  - id: todo\n  - id: done\n", encoding="utf-8"
    )
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "substrate-map.yaml").write_text(
        "schema_version: 1\naxes:\n"
        "  type:\n    label:\n      remap:\n        feature: kind/feature\n",
        encoding="utf-8",
    )

    original = bs._fetch_existing_labels
    bs._fetch_existing_labels = lambda: set()
    try:
        plan = bs._compute_plan(
            config={},
            classification=classification,
            with_starter_epic=False,
            capability_root=tmp_path,
        )
    finally:
        bs._fetch_existing_labels = original

    assert plan.label_creates == []
    joined = " ".join(plan.skipped_messages)
    for axis in ("type", "priority", "workstream", "state"):
        assert f"{axis}:* labels" in joined, joined
    assert "adopt-existing" in joined


def test_compute_plan_board_adopter_with_a_label_binding_gets_no_kit_palette(
    bs, tmp_path, classification
) -> None:
    """The polarity guard. A board adopter whose map binds `priority` to their own
    labels is NOT-on-the-board for that axis — so a "skip when the board carries
    it" test would hand them the entire kit `priority:*` palette. The predicate is
    `expects_kit_labels`, which is False here, so nothing is created."""
    schemas_dir = tmp_path / "schemas"
    schemas_dir.mkdir()
    (schemas_dir / "workflow.yaml").write_text("states:\n  - id: todo\n", encoding="utf-8")
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "substrate-map.yaml").write_text(
        "schema_version: 1\naxes:\n  priority:\n    label:\n      remap:\n        High: P0\n",
        encoding="utf-8",
    )

    original = bs._fetch_existing_labels
    bs._fetch_existing_labels = lambda: set()
    try:
        plan = bs._compute_plan(
            config={"has_projects_v2_board": True},
            classification=classification,
            with_starter_epic=False,
            capability_root=tmp_path,
        )
    finally:
        bs._fetch_existing_labels = original

    assert not any(name.startswith("priority:") for _, name in plan.label_creates)
    assert plan.label_creates == []


# --- projects_v2_node_id cache population (#310) ----------------------------
# In board mode bootstrap resolves the invariant board→node-id mapping ONCE and
# caches it in config so create-issue skips the per-create `gh project view` read.


def test_compute_plan_plans_node_id_when_board_uncached(
    bs, tmp_path, classification, monkeypatch
) -> None:
    """Board configured + no cached node id ⇒ the plan resolves + will cache it."""
    monkeypatch.setattr(bs, "_fetch_existing_labels", lambda: set())
    monkeypatch.setattr(bs, "_resolve_project_node_id", lambda config, board_id: "PVT_resolved")
    config = {"has_projects_v2_board": True, "projects_v2_board_id": 7}
    plan = bs._compute_plan(
        config=config,
        classification=classification,
        with_starter_epic=False,
        capability_root=tmp_path,
    )
    assert plan.board_node_id == "PVT_resolved"
    assert plan.has_creates() is True


def test_compute_plan_skips_node_id_when_already_cached(
    bs, tmp_path, classification, monkeypatch
) -> None:
    """An already-cached projects_v2_node_id is left untouched — no re-resolution."""
    monkeypatch.setattr(bs, "_fetch_existing_labels", lambda: set())

    def boom(*a, **k):  # pragma: no cover — must not be reached when already cached
        raise AssertionError("must not resolve when the node id is already cached")

    monkeypatch.setattr(bs, "_resolve_project_node_id", boom)
    config = {
        "has_projects_v2_board": True,
        "projects_v2_board_id": 7,
        "projects_v2_node_id": "PVT_existing",
    }
    plan = bs._compute_plan(
        config=config,
        classification=classification,
        with_starter_epic=False,
        capability_root=tmp_path,
    )
    assert plan.board_node_id is None
    assert "already cached" in plan.board_node_id_note


def test_compute_plan_no_node_id_in_label_fallback(
    bs, tmp_path, classification, monkeypatch
) -> None:
    """Label-fallback mode (no board) ⇒ no node id resolved or cached (left absent)."""
    schemas_dir = tmp_path / "schemas"
    schemas_dir.mkdir()
    (schemas_dir / "workflow.yaml").write_text(
        "states:\n  - id: todo\n  - id: done\n", encoding="utf-8"
    )
    monkeypatch.setattr(bs, "_fetch_existing_labels", lambda: set())

    def boom(*a, **k):  # pragma: no cover — must not be reached in label-fallback mode
        raise AssertionError("no node id resolution in label-fallback mode")

    monkeypatch.setattr(bs, "_resolve_project_node_id", boom)
    plan = bs._compute_plan(
        config={},
        classification=classification,
        with_starter_epic=False,
        capability_root=tmp_path,
    )
    assert plan.board_node_id is None
    assert plan.board_node_id_note == ""


def test_persist_project_node_id_writes_config_preserving_comments(bs, tmp_path) -> None:
    """The cache write lands `projects_v2_node_id` in config and preserves comments
    (ruamel round-trip, not typ='safe')."""
    config_path = tmp_path / "project" / "config.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        "# adopter config comment\n"
        "schema_version: 1\n"
        "has_projects_v2_board: true\n"
        "projects_v2_board_id: 7\n",
        encoding="utf-8",
    )
    action = bs._persist_project_node_id(tmp_path, "PVT_xyz")
    assert action.status == "created"
    text = config_path.read_text(encoding="utf-8")
    assert "projects_v2_node_id: PVT_xyz" in text
    assert "# adopter config comment" in text  # comments survive the rewrite


def test_persist_project_node_id_is_idempotent(bs, tmp_path) -> None:
    """Re-running the cache write with the same id rewrites the same value once."""
    config_path = tmp_path / "project" / "config.yaml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text("schema_version: 1\n", encoding="utf-8")
    bs._persist_project_node_id(tmp_path, "PVT_xyz")
    bs._persist_project_node_id(tmp_path, "PVT_xyz")
    text = config_path.read_text(encoding="utf-8")
    assert text.count("projects_v2_node_id:") == 1


# --- no GitHub repository: bootstrap refuses before it plans (#2087) ----------
# project-management works on a GitHub repository. Where `gh` resolves none for
# the checkout, bootstrap says so in plain words at its first run, a dry run
# included, rather than printing `target repo: <unresolved>` and exiting 0.

NO_REMOTES = "no git remotes found\n"


class _FakeGh:
    """Stands in for `gh`, so no test reaches GitHub.

    Answers `gh repo view` as told, an empty label list, and refuses any other
    `gh` call. Any other program runs as it would. Every `gh` call is recorded.
    """

    def __init__(self, real_run, *, repo_view) -> None:
        self._real_run = real_run
        self._repo_view = repo_view
        self.calls: list[list[str]] = []

    def __call__(self, cmd, *args, **kwargs):
        if not cmd or cmd[0] != "gh":
            return self._real_run(cmd, *args, **kwargs)
        self.calls.append(list(cmd))
        if cmd[1:3] == ["repo", "view"]:
            return self._repo_view(cmd)
        if cmd[1:3] == ["label", "list"]:
            return subprocess.CompletedProcess(cmd, 0, stdout="[]", stderr="")
        raise AssertionError(f"unexpected gh call: {cmd}")


def _repo_view_fails(stderr: str):
    def answer(cmd):
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr=stderr)

    return answer


def _repo_view_resolves(name: str):
    def answer(cmd):
        return subprocess.CompletedProcess(
            cmd, 0, stdout=json.dumps({"nameWithOwner": name}), stderr=""
        )

    return answer


def _gh_not_on_path(cmd):
    raise FileNotFoundError(2, "No such file or directory", "gh")


@pytest.fixture
def installed(tmp_path, monkeypatch) -> Path:
    """An installed capability with its real schemas and a valid config.

    The cross-repo guard is given no session anchor, so it stays silent.
    """
    cap = tmp_path / ".pkit" / "capabilities" / "project-management"
    shutil.copytree(CAP_SRC / "schemas", cap / "schemas")
    shutil.copy(CAP_SRC / "package.yaml", cap / "package.yaml")
    (cap / "project").mkdir()
    (cap / "project" / "config.yaml").write_text(
        "schema_version: 1\nworkstreams: []\n", encoding="utf-8"
    )
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.chdir(tmp_path)
    return cap


def _fake_gh(bs, monkeypatch, repo_view) -> _FakeGh:
    fake = _FakeGh(subprocess.run, repo_view=repo_view)
    monkeypatch.setattr(bs.subprocess, "run", fake)
    return fake


def _main(bs, monkeypatch, cap: Path, *args: str) -> int:
    monkeypatch.setattr(sys, "argv", ["bootstrap.py", *args, "--capability-root", str(cap)])
    return bs.main()


def test_resolve_repo_names_the_repository(bs, monkeypatch) -> None:
    _fake_gh(bs, monkeypatch, _repo_view_resolves("acme/widget"))
    lookup = bs._resolve_repo()
    assert lookup.name == "acme/widget"
    assert lookup.why == ""


def test_resolve_repo_gives_gh_s_own_reason_when_none_resolves(bs, monkeypatch) -> None:
    _fake_gh(bs, monkeypatch, _repo_view_fails(NO_REMOTES))
    lookup = bs._resolve_repo()
    assert lookup.name is None
    assert "no git remotes found" in lookup.why
    assert "git remote add origin" in lookup.fix


def test_resolve_repo_quotes_gh_on_one_line_without_control_characters(bs, monkeypatch) -> None:
    _fake_gh(bs, monkeypatch, _repo_view_fails("no git\x1b[31m remotes\r\n found\x07\n"))
    lookup = bs._resolve_repo()
    assert lookup.why == "`gh repo view` says: no git[31m remotes found"


def test_resolve_repo_says_gh_is_missing(bs, monkeypatch) -> None:
    _fake_gh(bs, monkeypatch, _gh_not_on_path)
    lookup = bs._resolve_repo()
    assert lookup.name is None
    assert "`gh`" in lookup.why and "not on PATH" in lookup.why
    assert "cli.github.com" in lookup.fix


@pytest.mark.parametrize("mode", [["--dry-run"], ["--yes"], []])
def test_bootstrap_refuses_when_no_repository_resolves(
    bs, installed, monkeypatch, capsys, mode
) -> None:
    """A dry run, a confirmed run and a plain run all refuse, before any plan."""
    fake = _fake_gh(bs, monkeypatch, _repo_view_fails(NO_REMOTES))
    code = _main(bs, monkeypatch, installed, *mode)
    out, err = capsys.readouterr()
    assert code == 2
    assert "needs a GitHub repository" in err
    assert "no git remotes found" in err
    assert "git remote add origin" in err
    assert "gh auth login" in err
    assert "Plan:" not in out
    assert "<unresolved>" not in out + err
    assert [c[1:3] for c in fake.calls] == [["repo", "view"]]


def test_bootstrap_refuses_when_gh_is_missing(bs, installed, monkeypatch, capsys) -> None:
    _fake_gh(bs, monkeypatch, _gh_not_on_path)
    code = _main(bs, monkeypatch, installed, "--dry-run")
    out, err = capsys.readouterr()
    assert code == 2
    assert "needs a GitHub repository" in err
    assert "not on PATH" in err
    assert "Plan:" not in out


def test_dry_run_plans_when_the_repository_resolves(bs, installed, monkeypatch, capsys) -> None:
    """The refusal costs a resolving checkout nothing: its dry run plans as before."""
    fake = _fake_gh(bs, monkeypatch, _repo_view_resolves("acme/widget"))
    code = _main(bs, monkeypatch, installed, "--dry-run")
    out, err = capsys.readouterr()
    assert code == 0, err
    assert "target repo: acme/widget" in out
    assert "Plan:" in out
    assert "+ create label `type:bug`" in out
    assert "no GitHub mutations" in out
    assert all(c[1] in {"repo", "label"} for c in fake.calls)
