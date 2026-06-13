"""Tests for project-management's lifecycle-hooks engine per DEC-024.

The library lives at `.pkit/capabilities/project-management/scripts/_lib/hooks.py`
— capability-internal. These tests load it via `importlib` so the kit's
pytest run catches regressions in the engine every lifecycle script
relies on.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
HOOKS_PY = (
    REPO_ROOT
    / ".pkit"
    / "capabilities"
    / "project-management"
    / "scripts"
    / "_lib"
    / "hooks.py"
)
GH_PY = HOOKS_PY.parent / "gh.py"


@pytest.fixture(scope="module")
def hooks():
    """Load the hooks module via importlib (sibling _lib import resolved via sys.path)."""
    lib_dir = HOOKS_PY.parent
    sys.path.insert(0, str(lib_dir))
    spec = importlib.util.spec_from_file_location("pm_hooks_under_test", HOOKS_PY)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["pm_hooks_under_test"] = module
    spec.loader.exec_module(module)
    yield module
    sys.path.remove(str(lib_dir))


@pytest.fixture
def capability_root(tmp_path: Path) -> Path:
    """Stage a minimal capability tree."""
    root = tmp_path / ".pkit" / "capabilities" / "project-management"
    (root / "project").mkdir(parents=True)
    return root


# --- file loading --------------------------------------------------------


def test_load_hooks_file_missing_returns_empty(hooks, capability_root) -> None:
    assert hooks.load_hooks_file(capability_root) == {}


def test_load_hooks_file_empty_yaml_returns_empty(hooks, capability_root) -> None:
    (capability_root / "project" / "hooks.yaml").write_text("", encoding="utf-8")
    assert hooks.load_hooks_file(capability_root) == {}


def test_load_hooks_file_parses_hooks_block(hooks, capability_root) -> None:
    (capability_root / "project" / "hooks.yaml").write_text(
        "schema_version: 1\n"
        "hooks:\n"
        "  after_create_issue:\n"
        "    - kind: assign-milestone\n"
        "      title: Milestone 1\n",
        encoding="utf-8",
    )
    doc = hooks.load_hooks_file(capability_root)
    assert doc["schema_version"] == 1
    assert "after_create_issue" in doc["hooks"]
    assert doc["hooks"]["after_create_issue"][0]["kind"] == "assign-milestone"


# --- event validation ----------------------------------------------------


def test_fire_hooks_rejects_unknown_event(hooks, capability_root) -> None:
    with pytest.raises(ValueError, match="unknown lifecycle event"):
        hooks.fire_hooks(
            "after_lol",
            context={},
            config={},
            capability_root=capability_root,
        )


def test_fire_hooks_no_file_returns_empty(hooks, capability_root) -> None:
    """No hooks.yaml → no hooks fire."""
    results = hooks.fire_hooks(
        "after_create_issue",
        context={"issue": {"number": 1, "title": "x"}},
        config={},
        capability_root=capability_root,
    )
    assert results == []


def test_fire_hooks_no_entries_for_event(hooks, capability_root) -> None:
    """hooks.yaml exists but has no entries for this event."""
    (capability_root / "project" / "hooks.yaml").write_text(
        "schema_version: 1\nhooks:\n  after_close_issue: []\n",
        encoding="utf-8",
    )
    results = hooks.fire_hooks(
        "after_create_issue",
        context={"issue": {"number": 1}},
        config={},
        capability_root=capability_root,
    )
    assert results == []


# --- dispatch / per-kind handling ---------------------------------------


def test_fire_hooks_unknown_kind_yields_skipped(hooks, capability_root) -> None:
    (capability_root / "project" / "hooks.yaml").write_text(
        "schema_version: 1\n"
        "hooks:\n"
        "  after_create_issue:\n"
        "    - kind: future-kind\n"
        "      some_field: x\n",
        encoding="utf-8",
    )
    results = hooks.fire_hooks(
        "after_create_issue",
        context={"issue": {"number": 1}},
        config={},
        capability_root=capability_root,
    )
    assert len(results) == 1
    assert results[0].status == "skipped"
    assert "future-kind" in results[0].detail


def test_fire_hooks_malformed_entry_recorded_as_failure(hooks, capability_root) -> None:
    """A non-dict entry → failed result, not exception."""
    (capability_root / "project" / "hooks.yaml").write_text(
        "schema_version: 1\n"
        "hooks:\n"
        "  after_create_issue:\n"
        "    - 'string-instead-of-mapping'\n",
        encoding="utf-8",
    )
    results = hooks.fire_hooks(
        "after_create_issue",
        context={"issue": {"number": 1}},
        config={},
        capability_root=capability_root,
    )
    assert len(results) == 1
    assert results[0].status == "failed"


# --- assign-milestone handler (dry-run) ---------------------------------


def test_assign_milestone_dry_run_skips_without_gh(hooks, capability_root) -> None:
    (capability_root / "project" / "hooks.yaml").write_text(
        "schema_version: 1\n"
        "hooks:\n"
        "  after_create_issue:\n"
        "    - kind: assign-milestone\n"
        "      title: Milestone 1\n",
        encoding="utf-8",
    )
    results = hooks.fire_hooks(
        "after_create_issue",
        context={"issue": {"number": 42, "title": "demo"}, "repo": "o/r"},
        config={},
        capability_root=capability_root,
        dry_run=True,
    )
    assert len(results) == 1
    assert results[0].status == "skipped"
    assert "would set milestone" in results[0].detail


def test_assign_milestone_missing_title_yields_failure(hooks, capability_root) -> None:
    (capability_root / "project" / "hooks.yaml").write_text(
        "schema_version: 1\n"
        "hooks:\n"
        "  after_create_issue:\n"
        "    - kind: assign-milestone\n",  # title missing
        encoding="utf-8",
    )
    results = hooks.fire_hooks(
        "after_create_issue",
        context={"issue": {"number": 1}},
        config={},
        capability_root=capability_root,
    )
    assert results[0].status == "failed"
    assert "title" in results[0].error


# --- post-comment handler -----------------------------------------------


def test_post_comment_dry_run_lists_action(hooks, capability_root) -> None:
    tmpl_dir = capability_root / "project" / "hook-templates"
    tmpl_dir.mkdir()
    tmpl_dir.joinpath("close.md").write_text("Closing #{{ issue.number }}", encoding="utf-8")
    (capability_root / "project" / "hooks.yaml").write_text(
        "schema_version: 1\n"
        "hooks:\n"
        "  after_close_issue:\n"
        "    - kind: post-comment\n"
        "      template_path: project/hook-templates/close.md\n",
        encoding="utf-8",
    )
    results = hooks.fire_hooks(
        "after_close_issue",
        context={"issue": {"number": 7}},
        config={},
        capability_root=capability_root,
        dry_run=True,
    )
    assert results[0].status == "skipped"
    assert "would post comment to #7" in results[0].detail


def test_post_comment_missing_template_yields_failure(hooks, capability_root) -> None:
    (capability_root / "project" / "hooks.yaml").write_text(
        "schema_version: 1\n"
        "hooks:\n"
        "  after_close_issue:\n"
        "    - kind: post-comment\n"
        "      template_path: project/hook-templates/missing.md\n",
        encoding="utf-8",
    )
    results = hooks.fire_hooks(
        "after_close_issue",
        context={"issue": {"number": 7}},
        config={},
        capability_root=capability_root,
    )
    assert results[0].status == "failed"
    assert "template not found" in results[0].error


# --- custom-script handler ---------------------------------------------


def test_custom_script_dry_run(hooks, capability_root) -> None:
    scripts_dir = capability_root / "project" / "hook-scripts"
    scripts_dir.mkdir()
    script = scripts_dir / "noop.sh"
    script.write_text("#!/usr/bin/env bash\necho ok\n", encoding="utf-8")
    script.chmod(0o755)
    (capability_root / "project" / "hooks.yaml").write_text(
        "schema_version: 1\n"
        "hooks:\n"
        "  after_create_issue:\n"
        "    - kind: custom-script\n"
        "      script_path: project/hook-scripts/noop.sh\n",
        encoding="utf-8",
    )
    results = hooks.fire_hooks(
        "after_create_issue",
        context={"issue": {"number": 1}, "repo": "o/r"},
        config={},
        capability_root=capability_root,
        dry_run=True,
    )
    assert results[0].status == "skipped"
    assert "would run" in results[0].detail


def test_custom_script_executes_real_script(hooks, capability_root, tmp_path) -> None:
    """Run a real script in non-dry-run mode; assert env var envelope."""
    trace = tmp_path / "trace.txt"
    scripts_dir = capability_root / "project" / "hook-scripts"
    scripts_dir.mkdir()
    script = scripts_dir / "trace.sh"
    script.write_text(
        f'#!/usr/bin/env bash\n'
        f'echo "$PKIT_HOOK_EVENT|$PKIT_ISSUE_NUMBER|$PKIT_REPO|$PKIT_DRY_RUN" >> "{trace}"\n',
        encoding="utf-8",
    )
    script.chmod(0o755)
    (capability_root / "project" / "hooks.yaml").write_text(
        "schema_version: 1\n"
        "hooks:\n"
        "  after_create_issue:\n"
        "    - kind: custom-script\n"
        "      script_path: project/hook-scripts/trace.sh\n",
        encoding="utf-8",
    )
    results = hooks.fire_hooks(
        "after_create_issue",
        context={"issue": {"number": 99}, "repo": "myorg/myrepo"},
        config={},
        capability_root=capability_root,
    )
    assert results[0].status == "ok"
    assert trace.read_text(encoding="utf-8").strip() == "after_create_issue|99|myorg/myrepo|false"


def test_custom_script_non_zero_exit_yields_failure(hooks, capability_root) -> None:
    scripts_dir = capability_root / "project" / "hook-scripts"
    scripts_dir.mkdir()
    script = scripts_dir / "fail.sh"
    script.write_text("#!/usr/bin/env bash\necho boom >&2\nexit 7\n", encoding="utf-8")
    script.chmod(0o755)
    (capability_root / "project" / "hooks.yaml").write_text(
        "schema_version: 1\n"
        "hooks:\n"
        "  after_create_issue:\n"
        "    - kind: custom-script\n"
        "      script_path: project/hook-scripts/fail.sh\n",
        encoding="utf-8",
    )
    results = hooks.fire_hooks(
        "after_create_issue",
        context={"issue": {"number": 1}, "repo": "o/r"},
        config={},
        capability_root=capability_root,
    )
    assert results[0].status == "failed"
    assert "7" in results[0].error  # exit code in the message


def test_custom_script_not_executable_yields_failure(hooks, capability_root) -> None:
    scripts_dir = capability_root / "project" / "hook-scripts"
    scripts_dir.mkdir()
    script = scripts_dir / "noexec.sh"
    script.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    # No chmod +x
    (capability_root / "project" / "hooks.yaml").write_text(
        "schema_version: 1\n"
        "hooks:\n"
        "  after_create_issue:\n"
        "    - kind: custom-script\n"
        "      script_path: project/hook-scripts/noexec.sh\n",
        encoding="utf-8",
    )
    results = hooks.fire_hooks(
        "after_create_issue",
        context={"issue": {"number": 1}, "repo": "o/r"},
        config={},
        capability_root=capability_root,
    )
    assert results[0].status == "failed"
    assert "not executable" in results[0].error


# --- multiple hooks for one event --------------------------------------


def test_multiple_hooks_fire_in_declared_order(hooks, capability_root, tmp_path) -> None:
    trace = tmp_path / "trace.txt"
    scripts_dir = capability_root / "project" / "hook-scripts"
    scripts_dir.mkdir()
    for i in (1, 2, 3):
        s = scripts_dir / f"step{i}.sh"
        s.write_text(f'#!/usr/bin/env bash\necho "step{i}" >> "{trace}"\n', encoding="utf-8")
        s.chmod(0o755)
    (capability_root / "project" / "hooks.yaml").write_text(
        "schema_version: 1\n"
        "hooks:\n"
        "  after_create_issue:\n"
        "    - kind: custom-script\n"
        "      script_path: project/hook-scripts/step1.sh\n"
        "    - kind: custom-script\n"
        "      script_path: project/hook-scripts/step2.sh\n"
        "    - kind: custom-script\n"
        "      script_path: project/hook-scripts/step3.sh\n",
        encoding="utf-8",
    )
    results = hooks.fire_hooks(
        "after_create_issue",
        context={"issue": {"number": 1}, "repo": "o/r"},
        config={},
        capability_root=capability_root,
    )
    assert len(results) == 3
    assert all(r.status == "ok" for r in results)
    assert trace.read_text(encoding="utf-8").splitlines() == ["step1", "step2", "step3"]


def test_hook_failure_does_not_block_subsequent_hooks(hooks, capability_root, tmp_path) -> None:
    """Report-and-continue: a failing hook doesn't stop the next from firing."""
    trace = tmp_path / "trace.txt"
    scripts_dir = capability_root / "project" / "hook-scripts"
    scripts_dir.mkdir()
    fail = scripts_dir / "fail.sh"
    fail.write_text("#!/usr/bin/env bash\nexit 1\n", encoding="utf-8")
    fail.chmod(0o755)
    ok = scripts_dir / "ok.sh"
    ok.write_text(f'#!/usr/bin/env bash\necho ok >> "{trace}"\n', encoding="utf-8")
    ok.chmod(0o755)
    (capability_root / "project" / "hooks.yaml").write_text(
        "schema_version: 1\n"
        "hooks:\n"
        "  after_create_issue:\n"
        "    - kind: custom-script\n"
        "      script_path: project/hook-scripts/fail.sh\n"
        "    - kind: custom-script\n"
        "      script_path: project/hook-scripts/ok.sh\n",
        encoding="utf-8",
    )
    results = hooks.fire_hooks(
        "after_create_issue",
        context={"issue": {"number": 1}, "repo": "o/r"},
        config={},
        capability_root=capability_root,
    )
    assert len(results) == 2
    assert results[0].status == "failed"
    assert results[1].status == "ok"
    assert trace.read_text(encoding="utf-8").strip() == "ok"


# --- template rendering -------------------------------------------------


def test_render_template_resolves_dotted_paths(hooks) -> None:
    rendered = hooks._render_template(
        "Issue #{{ issue.number }}: {{ issue.title }} in {{ repo }}",
        {"issue": {"number": 42, "title": "demo"}, "repo": "owner/name"},
    )
    assert rendered == "Issue #42: demo in owner/name"


def test_render_template_marks_missing_paths(hooks) -> None:
    rendered = hooks._render_template("{{ a.b.c }} and {{ x }}", {"a": {"b": {}}})
    assert "<missing: a.b.c>" in rendered
    assert "<missing: x>" in rendered
