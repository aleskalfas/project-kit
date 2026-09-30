"""Tests for project-management's open-pr script's pure logic.

Covers issue-number extraction, type derivation, summary derivation,
branch-pattern lookup, body template substitution.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from typing import Any
from types import ModuleType, SimpleNamespace

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = (
    REPO_ROOT
    / ".pkit"
    / "capabilities"
    / "project-management"
    / "scripts"
    / "open-pr.py"
)


@pytest.fixture(scope="module")
def op():
    module_name = "pm_open_pr_under_test"
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def classification() -> dict:
    return {
        "pr_type_mapping": [
            {"issue_label_value": "feature", "pr_conv_type": "feat"},
            {"issue_label_value": "bug", "pr_conv_type": "fix"},
            {"issue_label_value": "docs", "pr_conv_type": "docs"},
            {"issue_label_value": "test", "pr_conv_type": "test"},
            {"issue_label_value": "refactor", "pr_conv_type": "refactor"},
            {"issue_label_value": "maintenance", "pr_conv_type": "chore"},
        ],
    }


@pytest.fixture
def git_conventions() -> dict:
    return {
        "conventions": {
            "branch-name": {
                "pattern": r"^(feat|fix|docs|test|refactor|chore|ci)/[0-9]+-[a-z0-9][a-z0-9-]*$",
            },
        },
    }


# --- branch pattern extraction ---------------------------------------


def test_branch_pattern_returns_declared(op, git_conventions) -> None:
    p = op._branch_pattern(git_conventions)
    assert p == r"^(feat|fix|docs|test|refactor|chore|ci)/[0-9]+-[a-z0-9][a-z0-9-]*$"


def test_branch_pattern_returns_none_when_missing(op) -> None:
    assert op._branch_pattern({}) is None


# --- issue number extraction -----------------------------------------


def test_extract_issue_number_recognises_branch_form(op) -> None:
    assert op._extract_issue_number("feat/99-install-cli") == 99
    assert op._extract_issue_number("fix/77-render-tui") == 77
    assert op._extract_issue_number("chore/3-bump-deps") == 3


def test_extract_issue_number_returns_none_for_unconforming(op) -> None:
    assert op._extract_issue_number("main") is None
    assert op._extract_issue_number("install-cli") is None
    assert op._extract_issue_number("feat/install-cli") is None


# --- conv-type derivation --------------------------------------------


def test_conv_type_from_feature_label(op, classification) -> None:
    assert op._conv_type_from_issue_labels(["type:feature"], classification, None) == "feat"


def test_conv_type_from_bug_label(op, classification) -> None:
    assert op._conv_type_from_issue_labels(["type:bug"], classification, None) == "fix"


def test_conv_type_from_maintenance_label_picks_chore(op, classification) -> None:
    assert (
        op._conv_type_from_issue_labels(["type:maintenance"], classification, None)
        == "chore"
    )


def test_conv_type_returns_none_when_no_type_label(op, classification) -> None:
    assert op._conv_type_from_issue_labels(["priority:Medium"], classification, None) is None


def test_conv_type_uses_first_type_label_when_multiple(op, classification) -> None:
    # Multiple type labels is a validation error elsewhere; we don't
    # enforce here, but be deterministic.
    assert (
        op._conv_type_from_issue_labels(["type:bug", "type:feature"], classification, None)
        == "fix"
    )


def test_conv_type_from_a_remapped_type_label(op, classification) -> None:
    """An adopter whose substrate map binds `type` to their own `kind/*` labels
    gets the conv-type their label maps to, where the bare `type:` prefix scan
    found nothing and the verb refused with "pass --type" (#910)."""
    substrate_map = op.axis_labels.SubstrateMap(
        axes={"type": {"label": {"remap": {"bug": "kind/bug"}}}}
    )
    assert (
        op._conv_type_from_issue_labels(["kind/bug"], classification, substrate_map)
        == "fix"
    )
    # A leftover kit label is not the substrate under the remap.
    assert (
        op._conv_type_from_issue_labels(["type:docs"], classification, substrate_map)
        is None
    )


# --- summary derivation ----------------------------------------------


def test_summary_strips_type_prefix_and_lowercases(op) -> None:
    title = "[Task] Install the Claude Code CLI inside the sandbox"
    assert op._summary_from_issue_title(title) == (
        "install the claude code cli inside the sandbox"
    )


def test_summary_strips_trailing_period(op) -> None:
    title = "[Task] Render TUI cleanly."
    assert op._summary_from_issue_title(title) == "render tui cleanly"


def test_summary_handles_title_without_prefix(op) -> None:
    title = "no bracket prefix"
    # Should still lowercase, even without a prefix to strip.
    assert op._summary_from_issue_title(title) == "no bracket prefix"


# --- HTML comment stripping ------------------------------------------


def test_strip_html_comments_removes_single_line_comment(op) -> None:
    text = "before\n<!-- comment -->\nafter"
    assert "comment" not in op._strip_html_comments(text)


def test_strip_html_comments_removes_multi_line_comment(op) -> None:
    text = "before\n<!--\n  multi line\n  comment\n-->\nafter"
    result = op._strip_html_comments(text)
    assert "multi line" not in result
    assert "before" in result
    assert "after" in result


def test_strip_html_comments_preserves_uncommented_text(op) -> None:
    text = "plain text without comments"
    assert op._strip_html_comments(text) == text


# --- body template substitution --------------------------------------


def test_build_pr_body_fills_closes_placeholder(op, tmp_path) -> None:
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    (template_dir / "PR.md").write_text(
        "Closes #\n\n## Summary\n\n## Test plan\n", encoding="utf-8"
    )
    body = op._build_pr_body(
        capability_root=tmp_path, issue_numbers=[42], body_file=None
    )
    assert body is not None
    assert "Closes #42" in body


def test_build_pr_body_user_supplied_file(op, tmp_path) -> None:
    """The authored body is kept as written; a closing issue it does not name
    gets its `Closes #N` line on top, so the PR still closes it on merge."""
    f = tmp_path / "custom.md"
    f.write_text("user-supplied body\n", encoding="utf-8")
    body = op._build_pr_body(
        capability_root=tmp_path, issue_numbers=[42], body_file=f
    )
    assert body == "Closes #42\n\nuser-supplied body\n"


def test_build_pr_body_user_file_already_closing_is_verbatim(op, tmp_path) -> None:
    f = tmp_path / "custom.md"
    f.write_text("Fixes #42\n\n## Summary\n", encoding="utf-8")
    body = op._build_pr_body(
        capability_root=tmp_path, issue_numbers=[42], body_file=f
    )
    assert body == "Fixes #42\n\n## Summary\n"


def test_build_pr_body_user_file_gains_the_missing_references(op, tmp_path) -> None:
    """#1049: a PR that lands two Tasks closes both — the second reference goes
    right after the first, not somewhere down the body."""
    f = tmp_path / "custom.md"
    f.write_text("Closes #42\n\n## Summary\nwork\n", encoding="utf-8")
    body = op._build_pr_body(
        capability_root=tmp_path, issue_numbers=[42, 43, 44], body_file=f
    )
    assert body == "Closes #42\nCloses #43\nCloses #44\n\n## Summary\nwork\n"


def test_build_pr_body_template_carries_one_line_per_closing_issue(op, tmp_path) -> None:
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    (template_dir / "PR.md").write_text(
        "Closes #\n\n## Summary\n\n## Test plan\n", encoding="utf-8"
    )
    body = op._build_pr_body(
        capability_root=tmp_path, issue_numbers=[42, 43], body_file=None
    )
    assert body is not None
    assert body.startswith("Closes #42\nCloses #43\n\n## Summary")


def test_closing_issues_from_repeated_flag_then_branch(op) -> None:
    assert op._closing_issues(None, [7, 8, 7], "feat/7-thing") == [7, 8]
    assert op._closing_issues(None, None, "feat/7-thing") == [7]
    assert op._closing_issues(None, None, "main") == []


def test_closing_issues_positional_first(op) -> None:
    """#1017: the positional <N> is the closing issue, as review-work and
    done-work take it; with --closes as well, it stays the primary one."""
    assert op._closing_issues(9, None, "feat/7-thing") == [9]
    assert op._closing_issues(9, [10], "feat/7-thing") == [9, 10]
    assert op._closing_issues(9, [9], "main") == [9]


def test_build_pr_body_fallback_when_no_template(op, tmp_path) -> None:
    body = op._build_pr_body(
        capability_root=tmp_path, issue_numbers=[42], body_file=None
    )
    assert body == "Closes #42\n"


def test_build_pr_body_template_without_closes_placeholder(op, tmp_path) -> None:
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    (template_dir / "PR.md").write_text("## Summary\n\nfoo\n", encoding="utf-8")
    body = op._build_pr_body(
        capability_root=tmp_path, issue_numbers=[99], body_file=None
    )
    assert body is not None
    assert "Closes #99" in body


# --- main(): several closing references (#1049) ------------------------


CAP_ROOT = REPO_ROOT / ".pkit" / "capabilities" / "project-management"


def _no_config(_root: Path) -> dict[str, Any]:
    """An adopter config declaring nothing: the default branch is the backbone's."""
    return {}


def _backbone_says_main(op: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """The backbone's reading, stood in for: the default branch `main` (COR-054)."""
    lib = op.default_branch
    monkeypatch.setattr(lib, "_read", {})

    def ask(explicit: str | None, _run: Any) -> Any:
        branch = lib.Branch("main", False, "origin/main", "c0ffee", None)
        base = lib.Base(f"origin/{explicit or 'main'}", "c0ffee", "c0ffee", None)
        return lib.Reading(branch, base)

    monkeypatch.setattr(lib, "_ask", ask)


def _stub_main(op, monkeypatch, argv: list[str], issues: dict[int, dict]) -> dict:
    """Pass every gate, serve `issues` by number, capture the create call."""
    monkeypatch.setattr(sys, "argv", argv)
    monkeypatch.setattr(op, "resolve_capability_root", lambda _explicit: CAP_ROOT)
    monkeypatch.setattr(op.bootstrap_gate, "enforce", lambda *a, **k: True)
    monkeypatch.setattr(op.session_guard, "enforce", lambda **k: True)
    monkeypatch.setattr(op, "load_adopter_config", _no_config)
    _backbone_says_main(op, monkeypatch)
    monkeypatch.setattr(op, "_read_members", lambda *a: [])
    monkeypatch.setattr(
        op, "resolve_invoker_identity", lambda **k: SimpleNamespace(github_login="me")
    )
    monkeypatch.setattr(op, "check_membership", lambda *a: SimpleNamespace(allowed=True))
    monkeypatch.setattr(op, "_gh_get_issue", lambda n, _config: issues.get(n))
    monkeypatch.setattr(op, "_current_branch", lambda: "feat/42-thing")
    captured: dict = {}

    def fake_pr_create(*, title, body, base, draft, config):
        captured.update(title=title, body=body, base=base)
        return None  # stop before the post-create comments / hooks

    monkeypatch.setattr(op, "_gh_pr_create", fake_pr_create)
    return captured


def _open_issue() -> dict:
    return {
        "title": "[Task] do thing",
        "labels": [{"name": "type:feature"}],
        "state": "OPEN",
        "body": "",
    }


def test_main_repeated_closes_puts_every_reference_in_the_body(op, monkeypatch) -> None:
    captured = _stub_main(
        op,
        monkeypatch,
        [
            "open-pr", "--closes", "42", "--closes", "43",
            "--summary", "land both", "--draft", "--yes",
        ],
        {42: _open_issue(), 43: _open_issue()},
    )
    assert op.main() == 3  # the faked create returns no URL
    assert captured["title"] == "feat: land both"
    closing = [ln for ln in captured["body"].splitlines() if ln.startswith("Closes #")]
    assert closing == ["Closes #42", "Closes #43"]


def test_main_takes_the_issue_number_positionally(op, monkeypatch) -> None:
    """#1017: `open-pr 43` closes #43 — not the branch's #42 — exactly as
    `open-pr --closes 43` does."""
    captured = _stub_main(
        op,
        monkeypatch,
        ["open-pr", "43", "--scope", "pm", "--summary", "land it", "--draft", "--yes"],
        {43: _open_issue()},
    )
    assert op.main() == 3  # the faked create returns no URL
    assert captured["title"] == "feat(pm): land it"
    closing = [ln for ln in captured["body"].splitlines() if ln.startswith("Closes #")]
    assert closing == ["Closes #43"]


def test_positional_and_closes_close_both(op, monkeypatch) -> None:
    captured = _stub_main(
        op,
        monkeypatch,
        ["open-pr", "43", "--closes", "44", "--summary", "land both", "--draft", "--yes"],
        {43: _open_issue(), 44: _open_issue()},
    )
    assert op.main() == 3
    closing = [ln for ln in captured["body"].splitlines() if ln.startswith("Closes #")]
    assert closing == ["Closes #43", "Closes #44"]


def test_help_states_how_the_title_is_composed(op, monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["open-pr", "--help"])
    with pytest.raises(SystemExit):
        op.main()
    text = " ".join(capsys.readouterr().out.split())
    assert "<type>(<scope>): <summary>" in text
    assert "description part" in text


def test_main_refuses_an_unknown_second_closing_issue(op, monkeypatch) -> None:
    """A typo'd second issue would close the wrong issue on merge — refused
    before anything is opened."""
    captured = _stub_main(
        op,
        monkeypatch,
        ["open-pr", "--closes", "42", "--closes", "9999", "--draft", "--yes"],
        {42: _open_issue()},
    )
    assert op.main() == 2
    assert captured == {}


# --- main(): `## Doc impact` rendered from the change check (#1000, DEC-053) ----------

FRICTION = {
    "check": "change",
    "mode": "enforcing",
    "findings": [
        {
            "artefact": "guide",
            "location": "docs/guide.md",
            "kind": "answered",
            "anchor": {"kind": "code", "value": "src/cli.py"},
            "answer": "unchanged",
            "message": "changed in this diff; answered: unchanged — the flags did not move",
        },
        {
            "artefact": "intro",
            "location": "docs/intro.md",
            "kind": "revalidated",
            "anchor": None,
            "answer": "updated",
            "message": "revalidated with no changed anchor: updated",
        },
        {
            "artefact": "api",
            "location": "docs/api.md",
            "kind": "friction",
            "anchor": {"kind": "code", "value": "src/api.py"},
            "answer": None,
            "message": "changed in this diff; no answer",
        },
    ],
}
RENDERED = [
    "- `docs/guide.md` (anchor `code:src/cli.py`): changed in this diff; answered: "
    "unchanged — the flags did not move",
    "- `docs/intro.md`: revalidated with no changed anchor: updated",
]


def _doc_impact(body: str) -> list[str]:
    """The section's lines, without the provenance footer stamped after it."""
    section = body.split("## Doc impact", 1)[1].split("\n## ", 1)[0]
    section = section.split("<!-- pkit-provenance", 1)[0]
    return [ln for ln in section.splitlines() if ln.strip()]


def test_the_answers_render_as_the_doc_impact_bullets(op, monkeypatch, capsys) -> None:
    calls: list[str] = []
    monkeypatch.setattr(op, "_friction_check", lambda base: calls.append(base) or FRICTION)
    captured = _stub_main(
        op,
        monkeypatch,
        ["open-pr", "42", "--summary", "s", "--draft", "--yes", "--doc-impact-from-friction"],
        {42: _open_issue()},
    )
    assert op.main() == 3
    assert calls == [None]  # the default branch: the change check's own base (COR-054)
    assert _doc_impact(captured["body"]) == RENDERED
    out = capsys.readouterr()
    assert "doc impact: pre-filled from `pkit friction check` (2 answer(s))" in out.out
    # The page still carrying friction is named; its answer belongs on the page.
    assert "1 artefact(s) still carry friction with no answer on the page: docs/api.md" in out.err


def test_a_pr_against_another_base_is_checked_against_that_base(
    op: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An integration branch is named to the change check, which resolves it as every
    branch named as a base (COR-054 point 2); only the default branch goes unnamed."""
    calls: list[str | None] = []

    def check(base: str | None) -> dict[str, Any]:
        calls.append(base)
        return FRICTION

    monkeypatch.setattr(op, "_friction_check", check)
    _stub_main(
        op,
        monkeypatch,
        ["open-pr", "42", "--summary", "s", "--draft", "--yes", "--doc-impact-from-friction",
         "--base", "integration/7-x"],
        {42: _open_issue()},
    )
    assert op.main() == 3
    assert calls == ["integration/7-x"]


@pytest.mark.parametrize(
    ("base", "argv"),
    [
        (None, ["pkit", "friction", "check", "--json"]),
        ("integration/7-x", ["pkit", "friction", "check", "--json", "--base", "integration/7-x"]),
    ],
)
def test_the_change_check_is_named_a_base_only_when_it_is_not_its_own(
    op: Any, monkeypatch: pytest.MonkeyPatch, base: str | None, argv: list[str]
) -> None:
    seen: list[list[str]] = []

    def run(cmd: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        seen.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, "{}", "")

    monkeypatch.setattr(op.subprocess, "run", run)
    assert op._friction_check(base) == {}
    assert seen == [argv]


def test_an_authored_doc_impact_section_is_left_as_written(op, monkeypatch, tmp_path) -> None:
    body = tmp_path / "body.md"
    body.write_text("Closes #42\n\n## Summary\nx\n\n## Doc impact\nNo doc impact: tests only.\n")
    monkeypatch.setattr(op, "_friction_check", lambda base: FRICTION)
    captured = _stub_main(
        op,
        monkeypatch,
        ["open-pr", "42", "--body-file", str(body), "--draft", "--yes", "--doc-impact-from-friction"],
        {42: _open_issue()},
    )
    assert op.main() == 3
    assert _doc_impact(captured["body"])[0] == "No doc impact: tests only."


def test_without_the_flag_the_change_check_is_not_run(op, monkeypatch) -> None:
    def never(base):
        raise AssertionError("the change check ran without --doc-impact-from-friction")

    monkeypatch.setattr(op, "_friction_check", never)
    captured = _stub_main(
        op, monkeypatch, ["open-pr", "42", "--summary", "s", "--draft", "--yes"], {42: _open_issue()}
    )
    assert op.main() == 3
    assert _doc_impact(captured["body"]) == ["-"]


def test_no_document_leaves_the_body_as_it_was(op, monkeypatch) -> None:
    monkeypatch.setattr(op, "_friction_check", lambda base: None)
    body, note = op._prefill_doc_impact("## Doc impact\n\n-\n", "main")
    assert (body, note) == (
        "## Doc impact\n\n-\n",
        "not pre-filled — `pkit friction check --json` gave no document",
    )


@pytest.mark.parametrize("version", [2, None, "1"])
def test_a_check_of_another_version_leaves_the_body_as_it_was(
    op: ModuleType, monkeypatch: pytest.MonkeyPatch, version: object
) -> None:
    """A version this capability does not read is not rendered, never read as the one it knows."""

    def check(_base: str) -> dict[str, object]:
        return {**FRICTION, "schema_version": version}

    monkeypatch.setattr(op, "_friction_check", check)
    body, note = op._prefill_doc_impact("## Doc impact\n\n-\n", "main")
    assert (body, note) == (
        "## Doc impact\n\n-\n",
        f"not pre-filled — `pkit friction check --json` answered schema_version {version!r}; "
        "this capability reads 1",
    )


@pytest.mark.parametrize("versioned", [{}, {"schema_version": 1}])
def test_a_check_without_a_version_reads_as_the_first(
    op: ModuleType, monkeypatch: pytest.MonkeyPatch, versioned: dict[str, int]
) -> None:
    """A backbone from before the key answers version 1: the answers render."""

    def check(_base: str) -> dict[str, object]:
        return {**FRICTION, **versioned}

    monkeypatch.setattr(op, "_friction_check", check)
    body, note = op._prefill_doc_impact("## Doc impact\n\n-\n", "main")
    assert _doc_impact(body) == RENDERED
    assert note == "pre-filled from `pkit friction check` (2 answer(s))"


@pytest.fixture(scope="module")
def doc_impact():
    sys.path.insert(0, str(CAP_ROOT / "scripts"))
    from _lib import doc_impact as module

    return module


def test_prefill_fills_only_an_unwritten_section(doc_impact) -> None:
    lines = ["- `a.md`: updated"]
    placeholder = "Closes #1\n\n## Doc impact\n\n-\n\n## Test plan\n\n- [x] ok\n"
    assert doc_impact.prefill(placeholder, lines) == (
        "Closes #1\n\n## Doc impact\n\n- `a.md`: updated\n\n## Test plan\n\n- [x] ok\n",
        True,
    )
    commented = "## Doc impact\n<!-- say what changed -->\n"
    assert doc_impact.prefill(commented, lines) == ("## Doc impact\n\n- `a.md`: updated\n", True)
    absent = "Closes #1\n\n## Summary\nx"
    assert doc_impact.prefill(absent, lines) == (
        "Closes #1\n\n## Summary\nx\n\n## Doc impact\n\n- `a.md`: updated\n",
        True,
    )
    written = "## Doc impact\n- Updated README.md\n"
    assert doc_impact.prefill(written, lines) == (written, False)
    assert doc_impact.prefill(placeholder, []) == (placeholder, False)


def test_only_answers_are_rendered(doc_impact) -> None:
    assert doc_impact.answer_lines(FRICTION) == RENDERED
    assert doc_impact.unanswered(FRICTION) == ["docs/api.md"]
    assert doc_impact.answer_lines({"dormant": True, "findings": []}) == []
    assert doc_impact.answer_lines({"findings": "garbage"}) == []
