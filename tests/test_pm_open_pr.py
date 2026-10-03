"""Tests for project-management's open-pr script's pure logic.

Covers issue-number extraction, type derivation, summary derivation,
branch-pattern lookup, body template substitution.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts" / "open-pr.py"


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
    assert op._conv_type_from_issue_labels(["type:maintenance"], classification, None) == "chore"


def test_conv_type_returns_none_when_no_type_label(op, classification) -> None:
    assert op._conv_type_from_issue_labels(["priority:Medium"], classification, None) is None


def test_conv_type_uses_first_type_label_when_multiple(op, classification) -> None:
    # Multiple type labels is a validation error elsewhere; we don't
    # enforce here, but be deterministic.
    assert (
        op._conv_type_from_issue_labels(["type:bug", "type:feature"], classification, None) == "fix"
    )


def test_conv_type_from_a_remapped_type_label(op, classification) -> None:
    """An adopter whose substrate map binds `type` to their own `kind/*` labels
    gets the conv-type their label maps to, where the bare `type:` prefix scan
    found nothing and the verb refused with "pass --type" (#910)."""
    substrate_map = op.axis_labels.SubstrateMap(
        axes={"type": {"label": {"remap": {"bug": "kind/bug"}}}}
    )
    assert op._conv_type_from_issue_labels(["kind/bug"], classification, substrate_map) == "fix"
    # A leftover kit label is not the substrate under the remap.
    assert op._conv_type_from_issue_labels(["type:docs"], classification, substrate_map) is None


# --- summary derivation ----------------------------------------------


def test_summary_strips_type_prefix_and_lowercases(op) -> None:
    title = "[Task] Install the Claude Code CLI inside the sandbox"
    assert op._summary_from_issue_title(title) == ("install the claude code cli inside the sandbox")


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
    body = op._build_pr_body(capability_root=tmp_path, issue_numbers=[42], body_file=None)
    assert body is not None
    assert "Closes #42" in body


def test_build_pr_body_user_supplied_file(op, tmp_path) -> None:
    """The authored body is kept as written; a closing issue it does not name
    gets its `Closes #N` line on top, so the PR still closes it on merge."""
    f = tmp_path / "custom.md"
    f.write_text("user-supplied body\n", encoding="utf-8")
    body = op._build_pr_body(capability_root=tmp_path, issue_numbers=[42], body_file=f)
    assert body == "Closes #42\n\nuser-supplied body\n"


def test_build_pr_body_user_file_already_closing_is_verbatim(op, tmp_path) -> None:
    f = tmp_path / "custom.md"
    f.write_text("Fixes #42\n\n## Summary\n", encoding="utf-8")
    body = op._build_pr_body(capability_root=tmp_path, issue_numbers=[42], body_file=f)
    assert body == "Fixes #42\n\n## Summary\n"


def test_build_pr_body_user_file_gains_the_missing_references(op, tmp_path) -> None:
    """#1049: a PR that lands two Tasks closes both — the second reference goes
    right after the first, not somewhere down the body."""
    f = tmp_path / "custom.md"
    f.write_text("Closes #42\n\n## Summary\nwork\n", encoding="utf-8")
    body = op._build_pr_body(capability_root=tmp_path, issue_numbers=[42, 43, 44], body_file=f)
    assert body == "Closes #42\nCloses #43\nCloses #44\n\n## Summary\nwork\n"


def test_build_pr_body_template_carries_one_line_per_closing_issue(op, tmp_path) -> None:
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    (template_dir / "PR.md").write_text(
        "Closes #\n\n## Summary\n\n## Test plan\n", encoding="utf-8"
    )
    body = op._build_pr_body(capability_root=tmp_path, issue_numbers=[42, 43], body_file=None)
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
    body = op._build_pr_body(capability_root=tmp_path, issue_numbers=[42], body_file=None)
    assert body == "Closes #42\n"


def test_build_pr_body_template_without_closes_placeholder(op, tmp_path) -> None:
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    (template_dir / "PR.md").write_text("## Summary\n\nfoo\n", encoding="utf-8")
    body = op._build_pr_body(capability_root=tmp_path, issue_numbers=[99], body_file=None)
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


#: The commit the branch's remote-tracking reference names, as `_pushed_head` reads it.
PUSHED = "abcdef0123456789abcdef0123456789abcdef01"


def _derived(op: Any, *answers: dict[str, Any], **document: Any) -> Any:
    """The derivation `friction_answers.derive` returns for a change that wrote `answers`."""
    found = {
        "schema_version": 1,
        "base": {"commit": "0" * 40, "outdated": False},
        "findings": [],
        "answers": list(answers),
        "unreadable": [],
        **document,
    }
    return op.friction_answers.Derivation(PUSHED, document=found, answers=tuple(answers))


def _stub_main(
    op, monkeypatch, argv: list[str], issues: dict[int, dict], *, derived: Any = None
) -> dict:
    """Pass every gate, serve `issues` by number, capture the create call. The
    change check's list is `derived` (none written, by default), at `PUSHED`;
    `captured["derive"]` holds each (head, base) it was derived for."""
    calls: list[tuple[str, str | None]] = []

    def derive(head: str, base: str | None) -> Any:
        calls.append((head, base))
        return derived if derived is not None else _derived(op)

    monkeypatch.setattr(op, "_pushed_head", lambda _branch: (PUSHED, ""))
    monkeypatch.setattr(op.friction_answers, "derive", derive)
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
    captured: dict = {"derive": calls}

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
            "open-pr",
            "--closes",
            "42",
            "--closes",
            "43",
            "--summary",
            "land both",
            "--draft",
            "--yes",
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
    assert "title" not in captured and captured["derive"] == []


# --- main(): the friction answers' section (DEC-055) ------------------------------


def _answer(location: str, reason: str | None, **fields: Any) -> dict[str, Any]:
    """One entry of the change check's `answers`."""
    return {
        "artefact": location.split("/")[-1].removesuffix(".md"),
        "location": location,
        "answer": "unchanged",
        "anchor": None,
        "reason": reason,
        "kept": [],
        "asked": True,
        "status": "stands",
        "new": False,
        **fields,
    }


TWO = (_answer("docs/guide.md", "The flags did not move."), _answer("docs/api.md", "Holds."))
FOOTER_START = "<!-- pkit-provenance:start -->"


def _open(op, monkeypatch, *extra: str, derived: Any = None, body_file: Path | None = None):
    argv = ["open-pr", "42", "--summary", "s", "--draft", "--yes", *extra]
    if body_file is not None:
        argv += ["--body-file", str(body_file)]
    return _stub_main(op, monkeypatch, argv, {42: _open_issue()}, derived=derived)


def test_the_list_is_written_last_before_the_footer(op, monkeypatch, capsys) -> None:
    captured = _open(op, monkeypatch, derived=_derived(op, *TWO))
    assert op.main() == 3  # the faked create returns no URL
    body = captured["body"]
    section = op.friction_answers.render(_derived(op, *TWO).document, PUSHED)
    assert f"\n\n{section}\n\n{FOOTER_START}" in body
    assert body.count("## Friction answers") == 1
    # The PR's base, named even for the default branch; the pushed head.
    assert captured["derive"] == [(PUSHED, "main")]
    out = capsys.readouterr().out
    assert (
        "  answers: 2 written by this change, listed under `## Friction answers` (at abcdef0)"
        in (out)
    )


def test_a_pr_against_another_base_is_derived_against_that_base(op, monkeypatch) -> None:
    """An integration branch is named to the change check, which resolves it as every
    branch named as a base (COR-054 point 2), as the default branch is."""
    captured = _open(op, monkeypatch, "--base", "integration/7-x")
    assert op.main() == 3
    assert captured["derive"] == [(PUSHED, "integration/7-x")]


def test_no_answers_no_section(op, monkeypatch, capsys) -> None:
    captured = _open(op, monkeypatch)
    assert op.main() == 3
    assert "## Friction answers" not in captured["body"]
    assert "  answers: none written by this change" in capsys.readouterr().out


@pytest.mark.parametrize("marked", [True, False], ids=["a command's", "typed by hand"])
def test_a_section_in_a_supplied_body_is_dropped(op, monkeypatch, tmp_path, capsys, marked) -> None:
    supplied = (
        op.friction_answers.render(
            _derived(op, _answer("docs/x.md", "An agent's own list.")).document, "f" * 40
        )
        if marked
        else "## Friction answers\n\n```\n1. docs/x.md — unchanged: An agent's own list.\n```"
    )
    body_file = tmp_path / "body.md"
    body_file.write_text(f"Closes #42\n\n## Summary\nx\n\n{supplied}\n\n## Doc impact\n- none\n")
    captured = _open(op, monkeypatch, body_file=body_file)
    assert op.main() == 3
    assert "An agent's own list." not in captured["body"]
    assert "## Friction answers" not in captured["body"]
    assert "## Doc impact\n- none" in captured["body"]
    assert "warn: the body's `## Friction answers` section is dropped" in capsys.readouterr().err


def test_the_friction_settings_a_change_alters_are_listed(op, monkeypatch, capsys) -> None:
    derived = _derived(op)
    derived = op.friction_answers.Derivation(
        PUSHED,
        document=derived.document,
        settings=(op.friction_answers.Setting("friction.mode", "enforcing", "warning"),),
    )
    captured = _open(op, monkeypatch, derived=derived)
    assert op.main() == 3
    assert '- `friction.mode`: `"enforcing"` → `"warning"`' in captured["body"]
    assert (
        "  answers: none written by this change, which alters the project's friction "
        "settings, listed under `## Friction answers` (at abcdef0)"
    ) in capsys.readouterr().out


@pytest.mark.parametrize(
    ("how", "warning"),
    [
        ("unreadable", "the base origin/main could not be fetched"),
        ("not pushed", "origin/feat/42-thing names no commit — push the branch first"),
        ("closing reference", "the words on docs/api.md read as a closing reference (fixes #7)"),
        ("comment delimiter", "the words on docs/api.md hold an HTML comment's delimiter (-->)"),
        ("too long", "past the host's 65536 — split the change or narrow the anchor"),
    ],
)
def test_open_pr_never_refuses_over_the_list(op, monkeypatch, capsys, how, warning) -> None:
    """The section is left out with one warning line; the pull request opens, and
    land-work writes the list or says why it cannot."""
    derived = {
        "unreadable": op.friction_answers.Derivation(
            PUSHED, problem="the base origin/main could not be fetched: no route"
        ),
        "not pushed": _derived(op, *TWO),
        "closing reference": _derived(op, TWO[0], _answer("docs/api.md", "This fixes #7.")),
        "comment delimiter": _derived(op, TWO[0], _answer("docs/api.md", "ends -->")),
        "too long": _derived(op, _answer("docs/guide.md", "x" * 70000)),
    }[how]
    captured = _open(op, monkeypatch, derived=derived)
    if how == "not pushed":
        monkeypatch.setattr(op, "_pushed_head", lambda _branch: (None, warning))
    assert op.main() == 3  # opened: the faked create was asked, and returns no URL
    assert "## Friction answers" not in captured["body"]
    out = capsys.readouterr()
    (line,) = [ln for ln in out.err.splitlines() if ln.startswith("warn: friction answers")]
    assert warning in line and "`land-work` writes the list or says why it cannot" in line
    assert "  answers: not listed (the warning above says why)" in out.out


def test_the_pushed_head_is_the_remote_tracking_reference_not_local_head(
    op, monkeypatch, tmp_path
) -> None:
    def git(*argv: str, cwd: Path) -> str:
        done = subprocess.run(["git", *argv], cwd=cwd, capture_output=True, text=True, check=True)
        return done.stdout.strip()

    git("init", "-q", "--bare", "-b", "main", "origin.git", cwd=tmp_path)
    work = tmp_path / "work"
    work.mkdir()
    git("init", "-q", "-b", "feat/42-thing", cwd=work)
    git("config", "user.email", "o@example.com", cwd=work)
    git("config", "user.name", "O", cwd=work)
    git("remote", "add", "origin", "../origin.git", cwd=work)
    git("commit", "-q", "--allow-empty", "-m", "pushed", cwd=work)
    git("push", "-q", "-u", "origin", "feat/42-thing", cwd=work)
    pushed = git("rev-parse", "HEAD", cwd=work)
    git("commit", "-q", "--allow-empty", "-m", "not pushed", cwd=work)
    monkeypatch.chdir(work)
    assert op._pushed_head("feat/42-thing") == (pushed, "")
    assert op._pushed_head("feat/43-other") == (
        None,
        "origin/feat/43-other names no commit — push the branch first",
    )


# --- main(): `--doc-impact-from-friction` (DEC-053, DEC-055) ---------------------


def _doc_impact(body: str) -> list[str]:
    """The section's lines, up to the next section or the provenance footer."""
    section = body.split("## Doc impact", 1)[1].split("\n## ", 1)[0]
    section = section.split(FOOTER_START, 1)[0]
    return [ln for ln in section.splitlines() if ln.strip()]


def test_doc_impact_gets_one_line_pointing_at_the_list(op, monkeypatch, capsys) -> None:
    captured = _open(op, monkeypatch, "--doc-impact-from-friction", derived=_derived(op, *TWO))
    assert op.main() == 3
    line = "2 friction answers on anchored artefacts — listed under `## Friction answers`."
    assert _doc_impact(captured["body"]) == [line]
    assert f"doc impact: pre-filled: {line}" in capsys.readouterr().out


def test_doc_impact_names_the_pages_still_carrying_friction(op, monkeypatch, capsys) -> None:
    unanswered = {"location": "docs/cli.md", "kind": "friction", "artefact": "cli"}
    derived = _derived(op, TWO[0], findings=[unanswered])
    captured = _open(op, monkeypatch, "--doc-impact-from-friction", derived=derived)
    assert op.main() == 3
    assert _doc_impact(captured["body"]) == [
        "1 friction answer on anchored artefacts — listed under `## Friction answers`."
    ]
    err = capsys.readouterr().err
    assert "1 artefact(s) still carry friction with no answer on the page: docs/cli.md" in err


def test_an_authored_doc_impact_section_is_left_as_written(op, monkeypatch, tmp_path) -> None:
    body = tmp_path / "body.md"
    body.write_text("Closes #42\n\n## Summary\nx\n\n## Doc impact\nNo doc impact: tests only.\n")
    captured = _open(
        op, monkeypatch, "--doc-impact-from-friction", derived=_derived(op, *TWO), body_file=body
    )
    assert op.main() == 3
    assert _doc_impact(captured["body"])[0] == "No doc impact: tests only."


@pytest.mark.parametrize(
    ("derived", "note"),
    [
        (None, "not pre-filled — the change check reports no answers"),
        ("unlisted", "not pre-filled — the answers are not listed"),
        ("unreadable", "not pre-filled — `pkit friction check --json` gave no document"),
    ],
)
def test_doc_impact_is_left_unwritten_without_a_list(
    op, monkeypatch, capsys, derived, note
) -> None:
    found = {
        None: None,
        "unlisted": _derived(op, _answer("docs/api.md", "This fixes #7.")),
        "unreadable": op.friction_answers.Derivation(PUSHED, problem="no document"),
    }[derived]
    captured = _open(op, monkeypatch, "--doc-impact-from-friction", derived=found)
    assert op.main() == 3
    assert _doc_impact(captured["body"]) == ["-"]
    assert f"doc impact: {note}" in capsys.readouterr().out


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


def test_the_pages_still_carrying_friction_are_named(doc_impact) -> None:
    document = {
        "findings": [
            {"location": "docs/api.md", "kind": "friction"},
            {"location": "docs/guide.md", "kind": "answered"},
        ]
    }
    assert doc_impact.unanswered(document) == ["docs/api.md"]
    assert doc_impact.unanswered({"findings": "garbage"}) == []
