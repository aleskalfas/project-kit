"""Tests for project-management's lifecycle-hooks engine per DEC-024.

The library lives at `.pkit/capabilities/project-management/scripts/_lib/hooks.py`
— capability-internal. These tests load it via `importlib` so the kit's
pytest run catches regressions in the engine every lifecycle script
relies on.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOKS_PY = (
    REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts" / "_lib" / "hooks.py"
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
        "schema_version: 1\nhooks:\n  after_create_issue:\n    - 'string-instead-of-mapping'\n",
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


# --- set-board-field handler (the non-label per-create field default) ----
# DEC-037 §3: the `set-board-field` hook seeds a Projects-v2 field default
# (the AUJ `workstream=Spyre` case) on a new issue. It needs the new item's
# board node id + the project node id in context — exactly what create-issue
# now threads in. These tests pin that the create-context shape drives a write,
# and that the label-fallback shape (no item id) skips by design.

_SET_BOARD_FIELD_HOOK = (
    "schema_version: 1\n"
    "hooks:\n"
    "  after_create_issue:\n"
    "    - kind: set-board-field\n"
    "      field_id: PVTF_workstream\n"
    "      single_select_option_id: OPT_spyre\n"
)


def test_set_board_field_seeds_via_seam_with_create_context(
    hooks, capability_root, monkeypatch
) -> None:
    """With the create-context shape (board_item_id on the issue + a
    project_node_id), the `set-board-field` hook drives a field-value write
    through the seam — the non-label per-create default actually seeds."""
    (capability_root / "project" / "hooks.yaml").write_text(_SET_BOARD_FIELD_HOOK, encoding="utf-8")

    captured: dict = {}

    class _Result:
        ok = True
        detail = "set field"
        error = None

    def fake_write(config, **kwargs):
        captured.update(kwargs)
        return _Result()

    monkeypatch.setattr(hooks.substrate_writes, "write_field_value", fake_write)

    results = hooks.fire_hooks(
        "after_create_issue",
        context={
            "issue": {"number": 9, "title": "x", "board_item_id": "PVTI_new"},
            "repo": "acme/repo",
            "project_node_id": "PVT_project",
        },
        config={},
        capability_root=capability_root,
    )

    assert len(results) == 1
    assert results[0].status == "ok"
    # The write targeted THIS new item, on the configured field/option.
    assert captured["item_id"] == "PVTI_new"
    assert captured["project_id"] == "PVT_project"
    assert captured["field_id"] == "PVTF_workstream"
    assert captured["single_select_option_id"] == "OPT_spyre"


def test_set_board_field_skips_without_item_id(hooks, capability_root, monkeypatch) -> None:
    """Label-fallback shape (no board → no board_item_id in context): the hook
    skips by design rather than guessing an item. No write is attempted."""
    (capability_root / "project" / "hooks.yaml").write_text(_SET_BOARD_FIELD_HOOK, encoding="utf-8")

    def boom(*a, **k):  # pragma: no cover — must not be reached
        raise AssertionError("write_field_value must not run without an item id")

    monkeypatch.setattr(hooks.substrate_writes, "write_field_value", boom)

    results = hooks.fire_hooks(
        "after_create_issue",
        context={"issue": {"number": 9, "title": "x"}, "repo": "acme/repo"},
        config={},
        capability_root=capability_root,
    )
    assert len(results) == 1
    assert results[0].status == "skipped"
    assert "board-item id" in results[0].detail


def test_set_board_field_skips_without_project_node_id(hooks, capability_root, monkeypatch) -> None:
    """Item id present but the project node id did not resolve: skip, no write
    (never guess the project the item belongs to)."""
    (capability_root / "project" / "hooks.yaml").write_text(_SET_BOARD_FIELD_HOOK, encoding="utf-8")

    def boom(*a, **k):  # pragma: no cover — must not be reached
        raise AssertionError("write_field_value must not run without a project id")

    monkeypatch.setattr(hooks.substrate_writes, "write_field_value", boom)

    results = hooks.fire_hooks(
        "after_create_issue",
        context={
            "issue": {"number": 9, "title": "x", "board_item_id": "PVTI_new"},
            "repo": "acme/repo",
            "project_node_id": None,
        },
        config={},
        capability_root=capability_root,
    )
    assert len(results) == 1
    assert results[0].status == "skipped"
    assert "Projects v2 board" in results[0].detail


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


# --- post-comment: one comment per firing, suppressed only by its own (#950) --


class _FakeGh:
    """A fake `gh` for the post-comment hook. `view` answers with the subject's
    comments; `comment` records the post and adds it to them the way GitHub
    would show it to the poster — authored by the viewer, unedited."""

    def __init__(self, comments: list[dict] | None = None, *, view_fails: bool = False) -> None:
        self.comments = list(comments or [])
        self.posted: list[str] = []
        self.view_fails = view_fails

    def __call__(self, args: list[str], config: dict) -> subprocess.CompletedProcess:
        if args[2] == "view":
            if self.view_fails:
                return subprocess.CompletedProcess(args, 1, stdout="", stderr="boom")
            payload = json.dumps({"comments": self.comments})
            return subprocess.CompletedProcess(args, 0, stdout=payload, stderr="")
        assert args[2] == "comment", args
        body = args[args.index("--body") + 1]
        self.posted.append(body)
        self.comments.append({"body": body, "viewerDidAuthor": True, "includesCreatedEdit": False})
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")


_MOVED = {"from": "in-progress", "to": "in-review"}


@pytest.fixture
def moved_hook(capability_root: Path) -> Path:
    """A `post-comment` hook on `after_move_issue` and `after_close_issue`,
    both from one template (so both stamp as `moved`)."""
    tmpl_dir = capability_root / "project" / "hook-templates"
    tmpl_dir.mkdir()
    tmpl_dir.joinpath("moved.md").write_text(
        "#{{ issue.number }} is now {{ transition.to }}", encoding="utf-8"
    )
    (capability_root / "project" / "hooks.yaml").write_text(
        "schema_version: 1\n"
        "hooks:\n"
        "  after_move_issue:\n"
        "    - kind: post-comment\n"
        "      template_path: project/hook-templates/moved.md\n"
        "  after_close_issue:\n"
        "    - kind: post-comment\n"
        "      template_path: project/hook-templates/moved.md\n",
        encoding="utf-8",
    )
    return capability_root


def _fire(hooks, root: Path, event: str = "after_move_issue", transition: dict | None = None):
    context: dict = {"issue": {"number": 7, "title": "t"}}
    if event == "after_move_issue":
        context["transition"] = transition or _MOVED
    return hooks.fire_hooks(event, context=context, config={}, capability_root=root)


def _moved_stamp(hooks, transition: dict = _MOVED) -> str:
    return hooks.hook_stamp("moved", "after_move_issue", "issue", 7, transition)


def test_post_comment_identical_retry_posts_once(hooks, moved_hook, monkeypatch) -> None:
    gh = _FakeGh()
    monkeypatch.setattr(hooks, "_gh_call", gh)

    first = _fire(hooks, moved_hook)
    retry = _fire(hooks, moved_hook)

    assert [r.status for r in first + retry] == ["ok", "ok"]
    assert len(gh.posted) == 1
    assert gh.posted[0].splitlines()[0] == _moved_stamp(hooks)
    assert "idempotent skip" in retry[0].detail


def test_post_comment_distinct_transition_posts_again(hooks, moved_hook, monkeypatch) -> None:
    """The fixed stamp dropped every firing after the first on an issue."""
    gh = _FakeGh()
    monkeypatch.setattr(hooks, "_gh_call", gh)

    _fire(hooks, moved_hook)
    _fire(hooks, moved_hook, transition={"from": "in-review", "to": "done"})

    assert len(gh.posted) == 2
    assert gh.posted[1].splitlines()[0] != gh.posted[0].splitlines()[0]
    assert "is now done" in gh.posted[1]


def test_post_comment_same_hook_on_another_event_posts_again(
    hooks, moved_hook, monkeypatch
) -> None:
    gh = _FakeGh()
    monkeypatch.setattr(hooks, "_gh_call", gh)

    _fire(hooks, moved_hook)
    _fire(hooks, moved_hook, event="after_close_issue")

    assert len(gh.posted) == 2
    assert gh.posted[1].splitlines()[0] == hooks.hook_stamp(
        "moved", "after_close_issue", "issue", 7
    )


@pytest.mark.parametrize(
    "authorship",
    [
        pytest.param({"viewerDidAuthor": False, "includesCreatedEdit": False}, id="other-author"),
        pytest.param({"viewerDidAuthor": True, "includesCreatedEdit": True}, id="edited-own"),
        pytest.param({}, id="identity-unreadable"),
        pytest.param(
            {"viewerDidAuthor": "yes", "includesCreatedEdit": None}, id="identity-garbled"
        ),
    ],
)
def test_post_comment_stamp_not_suppressing_unless_own_and_unedited(
    hooks, moved_hook, monkeypatch, authorship
) -> None:
    """A comment carrying this firing's exact stamp stops the post only when the
    posting account wrote it and nobody edited it. When the authorship cannot
    be read, the hook posts, as the audit writers do."""
    planted = {"body": f"{_moved_stamp(hooks)}\n\nnothing to see", **authorship}
    gh = _FakeGh([planted])
    monkeypatch.setattr(hooks, "_gh_call", gh)

    results = _fire(hooks, moved_hook)

    assert results[0].status == "ok"
    assert len(gh.posted) == 1


def test_post_comment_own_comment_quoting_the_stamp_does_not_suppress(
    hooks, moved_hook, monkeypatch
) -> None:
    """Only the first line counts: an own note that quotes the stamp further
    down is not the hook's comment."""
    quoting = {
        "body": f"See the hook's comment:\n{_moved_stamp(hooks)}",
        "viewerDidAuthor": True,
        "includesCreatedEdit": False,
    }
    gh = _FakeGh([quoting])
    monkeypatch.setattr(hooks, "_gh_call", gh)

    _fire(hooks, moved_hook)

    assert len(gh.posted) == 1


def test_post_comment_unreadable_comment_list_posts(hooks, moved_hook, monkeypatch) -> None:
    gh = _FakeGh(view_fails=True)
    monkeypatch.setattr(hooks, "_gh_call", gh)

    _fire(hooks, moved_hook)

    assert len(gh.posted) == 1


def test_post_comment_old_form_stamp_does_not_suppress(hooks, moved_hook, monkeypatch) -> None:
    """A comment from a version that wrote the bare `<!-- pkit-hook: <id> -->`
    names no firing: the hook posts once under the new stamp, then a retry
    finds that one."""
    old = {
        "body": "<!-- pkit-hook: moved -->\n\n#7 is now in-review",
        "viewerDidAuthor": True,
        "includesCreatedEdit": False,
    }
    gh = _FakeGh([old])
    monkeypatch.setattr(hooks, "_gh_call", gh)

    _fire(hooks, moved_hook)
    _fire(hooks, moved_hook)

    assert len(gh.posted) == 1
    assert gh.posted[0].splitlines()[0] == _moved_stamp(hooks)


def test_post_comment_crlf_own_comment_still_found(hooks, moved_hook, monkeypatch) -> None:
    """GitHub may hand a body back with CRLF line endings; the first-line match
    is made on the normalised body."""
    own = {
        "body": f"{_moved_stamp(hooks)}  \r\n\r\n#7 is now in-review",
        "viewerDidAuthor": True,
        "includesCreatedEdit": False,
    }
    gh = _FakeGh([own])
    monkeypatch.setattr(hooks, "_gh_call", gh)

    _fire(hooks, moved_hook)

    assert gh.posted == []


@pytest.mark.parametrize(
    ("stamp_id", "transition"),
    [
        ("close-thanks", None),
        ("a--b>c", {"from": "x-->y", "to": "<!--z>"}),
        ("Ünïcode name.md", {"from": "-", "to": ">"}),
        ("x" * 500, {"from": "s" * 500, "to": "t"}),
        ("---", None),
    ],
)
def test_hook_stamp_is_safe_inside_an_html_comment(hooks, stamp_id, transition) -> None:
    stamp = hooks.hook_stamp(stamp_id, "after_move_issue", "issue", 7, transition)

    assert stamp.startswith(hooks.HOOK_STAMP_OPEN)
    assert stamp.endswith(hooks.HOOK_STAMP_CLOSE)
    inner = stamp[len("<!--") : -len("-->")]
    assert "--" not in inner
    assert ">" not in inner
    assert "<" not in inner
    assert "\n" not in stamp
    limit = len(hooks.HOOK_STAMP_OPEN) + hooks.HOOK_STAMP_NAME_MAX + 1
    assert len(stamp) <= limit + hooks.FIRING_DIGEST_LENGTH + len(hooks.HOOK_STAMP_CLOSE)


def test_hook_stamp_keeps_hooks_with_alike_names_apart(hooks) -> None:
    """`close_thanks` and `close.thanks` both show as `close-thanks`; the digest
    hashes the id as given, so they still stamp differently."""
    a = hooks.hook_stamp("close_thanks", "after_close_issue", "issue", 7)
    b = hooks.hook_stamp("close.thanks", "after_close_issue", "issue", 7)

    assert a != b
    assert a.startswith(f"{hooks.HOOK_STAMP_OPEN}close-thanks:")


def test_hook_stamp_tells_subjects_apart(hooks) -> None:
    on_issue = hooks.hook_stamp("note", "after_close_issue", "issue", 7)

    assert on_issue == hooks.hook_stamp("note", "after_close_issue", "issue", 7)
    assert on_issue != hooks.hook_stamp("note", "after_close_issue", "issue", 8)
    assert on_issue != hooks.hook_stamp("note", "after_close_issue", "pr", 7)


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
        f"#!/usr/bin/env bash\n"
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
