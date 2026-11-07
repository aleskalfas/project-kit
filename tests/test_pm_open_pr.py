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

from tests.adopter_repo import sign_nothing

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
    """The derivation `friction_answers.checked` returns for a change that wrote `answers`."""
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
    change check's answers are `derived` (none written, by default), at `PUSHED`;
    `captured["checked"]` holds each (head, base) they were derived for."""
    calls: list[tuple[str, str | None]] = []

    def checked(head: str, base: str | None, *, from_checkout: bool = True) -> Any:
        # No temporary checkout for any head: a refusal costs a warning line (DEC-067).
        assert from_checkout is False
        calls.append((head, base))
        return derived if derived is not None else _derived(op)

    monkeypatch.setattr(op, "_pushed_head", lambda _branch: (PUSHED, ""))
    monkeypatch.setattr(op.friction_answers, "checked", checked)
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
    captured: dict = {"checked": calls}

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
    assert "title" not in captured and captured["checked"] == []


# --- main(): no list of the answers (DEC-065 points 1 and 3) ----------------------


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
#: The heading a list of the answers was written under, and the one before it.
HEADING = "## Documentation this change affects"
FORMER_HEADING = "## Friction answers"
#: How the plan's line for the answers begins.
PLAN = "  documents this change affects:"


def _open(op, monkeypatch, *extra: str, derived: Any = None, body_file: Path | None = None):
    argv = ["open-pr", "42", "--summary", "s", "--draft", "--yes", *extra]
    if body_file is not None:
        argv += ["--body-file", str(body_file)]
    return _stub_main(op, monkeypatch, argv, {42: _open_issue()}, derived=derived)


def test_no_list_is_written_and_the_plan_counts_the_documents(op, monkeypatch, capsys) -> None:
    """The answers are derived at the pushed head against the PR's base, named even
    for the default branch, and the plan counts the documents they are on; the
    description gains no list of them."""
    captured = _open(op, monkeypatch, derived=_derived(op, *TWO))
    assert op.main() == 3  # the faked create returns no URL
    body = captured["body"]
    assert HEADING not in body and "The flags did not move." not in body
    assert captured["checked"] == [(PUSHED, "main")]
    assert f"{PLAN} 2 (at abcdef0)" in capsys.readouterr().out.splitlines()


def test_a_pr_against_another_base_is_derived_against_that_base(op, monkeypatch) -> None:
    """An integration branch is named to the change check, which resolves it as every
    branch named as a base (COR-054 point 2), as the default branch is."""
    captured = _open(op, monkeypatch, "--base", "integration/7-x")
    assert op.main() == 3
    assert captured["checked"] == [(PUSHED, "integration/7-x")]


def test_no_answers_the_plan_says_none(op, monkeypatch, capsys) -> None:
    captured = _open(op, monkeypatch)
    assert op.main() == 3
    assert HEADING not in captured["body"]
    assert f"{PLAN} none (at abcdef0)" in capsys.readouterr().out.splitlines()


def _listed(heading: str) -> str:
    """A list as an earlier run of these commands wrote it, under `heading`."""
    return "\n".join(
        [
            heading,
            "",
            f"<!-- pkit-friction-answers:start head={'f' * 40} base={'0' * 40} -->",
            '1. `docs/x.md` — **still accurate**: "``An agent\'s own list.``"',
            "<!-- pkit-friction-answers:end -->",
        ]
    )


@pytest.mark.parametrize(
    "heading", [HEADING, FORMER_HEADING], ids=["a command's", "an earlier run's"]
)
def test_a_region_in_a_supplied_body_is_dropped(op, monkeypatch, tmp_path, capsys, heading) -> None:
    body_file = tmp_path / "body.md"
    body_file.write_text(
        f"Closes #42\n\n## Summary\nx\n\n{_listed(heading)}\n\n## Doc impact\n- none\n"
    )
    captured = _open(op, monkeypatch, body_file=body_file)
    assert op.main() == 3
    assert "An agent's own list." not in captured["body"]
    assert heading not in captured["body"]
    assert "## Doc impact\n- none" in captured["body"]
    assert f"warn: the body's `{HEADING}` section is dropped" in capsys.readouterr().err


@pytest.mark.parametrize("heading", [HEADING, FORMER_HEADING], ids=["heading", "former heading"])
def test_a_section_typed_under_the_heading_stays(
    op, monkeypatch, tmp_path, capsys, heading
) -> None:
    """Only a region a command wrote is dropped (DEC-065 point 1)."""
    body_file = tmp_path / "body.md"
    body_file.write_text(f"Closes #42\n\n{heading}\n\nIn my words.\n\n## Doc impact\n- none\n")
    captured = _open(op, monkeypatch, body_file=body_file)
    assert op.main() == 3
    assert "In my words." in captured["body"]
    assert "is dropped" not in capsys.readouterr().err


def test_a_start_marker_with_no_end_warns_and_stays(op, monkeypatch, tmp_path, capsys) -> None:
    marker = op.friction_answers.MARKER_START
    body_file = tmp_path / "body.md"
    body_file.write_text(f"Closes #42\n\n{marker} head=x base=y -->\n\n## Doc impact\n- none\n")
    captured = _open(op, monkeypatch, body_file=body_file)
    assert op.main() == 3
    assert marker in captured["body"] and "## Doc impact\n- none" in captured["body"]
    assert f"warn: {op.friction_answers.ORPHAN_WARNING}" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("how", "why"),
    [
        ("unreadable", "the base origin/main could not be fetched: no route"),
        ("not pushed", "origin/feat/42-thing names no commit — push the branch first"),
    ],
)
def test_open_pr_never_refuses_over_the_answers(op, monkeypatch, capsys, how, why) -> None:
    """Answers that cannot be read draw one warning line; the pull request opens, and
    review-work reads them at its head (DEC-065 point 3)."""
    derived = {
        "unreadable": op.friction_answers.Derivation(PUSHED, problem=why),
        "not pushed": _derived(op, *TWO),
    }[how]
    captured = _open(op, monkeypatch, derived=derived)
    if how == "not pushed":
        monkeypatch.setattr(op, "_pushed_head", lambda _branch: (None, why))
    assert op.main() == 3  # opened: the faked create was asked, and returns no URL
    assert HEADING not in captured["body"]
    out = capsys.readouterr()
    (line,) = [ln for ln in out.err.splitlines() if ln.startswith("warn: the answers the change")]
    assert line == (
        f"warn: the answers the change wrote were not read — {why}; review-work reads them at "
        "the pull request's head"
    )
    assert f"{PLAN} not read (the warning above says why)" in out.out


#: The supplied body's own section where the author says what changed in each
#: document the change revalidated as `updated` (DEC-065 point 1).
SAID = (
    "Closes #42\n\n## Summary\nx\n\n## What changed in each updated document\n\n"
    "- `docs/guide.md`: The guide now names the renamed flag.\n\n## Doc impact\n- none\n"
)
UPDATED = (
    _answer("docs/guide.md", None, answer="updated"),
    _answer("docs/api.md", None, answer="updated"),
    _answer("docs/cli.md", "Holds."),
)
#: How open-pr's warning of updated documents with no sentence begins.
UNSAID = (
    "warn: {n} updated document(s) with no sentence on what changed under `## What changed "
    "in each updated document`: "
)


def test_an_updated_document_given_no_sentence_is_warned_of(
    op, monkeypatch, tmp_path, capsys
) -> None:
    """The sentences are read from the body's own section, which stays as the author
    wrote it; each updated document with none is named in a warning that says
    review-work refuses it."""
    body_file = tmp_path / "body.md"
    body_file.write_text(SAID, encoding="utf-8")
    captured = _open(op, monkeypatch, derived=_derived(op, *UPDATED), body_file=body_file)
    assert op.main() == 3
    body = captured["body"]
    assert body.startswith(SAID.rstrip("\n"))  # the author's section stays where it was
    assert HEADING not in body
    err = capsys.readouterr().err
    assert (
        f"{UNSAID.format(n=1)}docs/api.md — review-work refuses them; add a list item there for "
        "each, naming the document in a code span, then the sentence"
    ) in err.splitlines()


@pytest.mark.parametrize("answers", [UPDATED, ()], ids=["answers", "no answers"])
def test_a_sentence_on_a_document_the_check_does_not_mark_updated_is_warned_of(
    op, monkeypatch, tmp_path, capsys, answers
) -> None:
    """No reviewer checks a sentence on a document the change check does not mark
    updated, one left unchanged here, or any where the change wrote no answers: a
    warning names each, and the edit that removes it. The PR opens all the same
    (DEC-065 point 3)."""
    body_file = tmp_path / "body.md"
    body_file.write_text(
        SAID.replace(
            "\n\n## Doc impact", "\n- `docs/cli.md`: The page drops the old flag.\n\n## Doc impact"
        ),
        encoding="utf-8",
    )
    captured = _open(op, monkeypatch, derived=_derived(op, *answers), body_file=body_file)
    assert op.main() == 3  # opened: the faked create was asked, and returns no URL
    assert captured["body"]
    err = capsys.readouterr().err
    unlisted = ["docs/cli.md"] if answers else ["docs/guide.md", "docs/cli.md"]
    assert [line for line in err.splitlines() if "no reviewer checks the sentence" in line] == [
        f"warn: {location} has a sentence under `## What changed in each updated document`, "
        "and the change check at abcdef0 does not mark it updated, so no reviewer checks the "
        "sentence — remove it from the description with `edit-pr`"
        for location in unlisted
    ]


def test_a_ready_pr_opens_with_an_updated_document_given_no_sentence(
    op, monkeypatch, tmp_path, capsys
) -> None:
    """open-pr only warns of a missing sentence, a PR opened ready too: its
    validate-at-ready refuses nothing over it. The move to review refuses it
    (DEC-065 point 3, `test_pm_review_work`)."""
    body_file = tmp_path / "body.md"
    body_file.write_text(SAID, encoding="utf-8")
    argv = ["open-pr", "42", "--summary", "s", "--yes", "--body-file", str(body_file)]
    _stub_main(op, monkeypatch, argv, {42: _open_issue()}, derived=_derived(op, *UPDATED))
    assert op.main() == 3  # opened: the faked create was asked, and returns no URL
    err = capsys.readouterr().err
    assert "[refused]" not in err
    assert UNSAID.format(n=1) in err


@pytest.mark.parametrize(
    ("item", "unread"),
    [
        ("- **docs/guide.md:** The guide now names the renamed flag.", True),
        ("- docs/guide.md: The guide now names the renamed flag.", True),
        ("- `docs/guide.md`: The guide now names the renamed flag.", False),
    ],
    ids=["bold path", "no code span", "read form"],
)
def test_an_item_it_cannot_read_draws_a_warning_naming_its_line_and_the_form(
    op, monkeypatch, tmp_path, capsys, item, unread
) -> None:
    """An item the reading leaves out is named by its line in the description, with
    the form it needs, and its document counts as having no sentence. The read form
    draws no such warning."""
    body_file = tmp_path / "body.md"
    body_file.write_text(
        SAID.replace("- `docs/guide.md`: The guide now names the renamed flag.", item)
    )
    captured = _open(op, monkeypatch, derived=_derived(op, *UPDATED), body_file=body_file)
    assert op.main() == 3
    body = captured["body"]
    lines = capsys.readouterr().err.splitlines()
    err = [ln for ln in lines if "is not read as a sentence" in ln]
    if not unread:
        assert err == []
        return
    assert body.split("\n")[7] == item  # line 8 of the description
    assert err == [
        "warn: line 8 of the description, under `## What changed in each updated document`, is "
        f'not read as a sentence: "{item}" — write it as "- `path`: sentence", starting in the '
        "line's first column, the document in a code span as the change check names it"
    ]
    assert any(ln.startswith(f"{UNSAID.format(n=2)}docs/guide.md, docs/api.md") for ln in lines)


def test_the_line_named_is_the_line_in_the_description_opened(
    op, monkeypatch, tmp_path, capsys
) -> None:
    """`--doc-impact-from-friction` fills an empty `## Doc impact` above the sentences,
    which moves them down: the warning names the line the item is on in the
    description as it is opened, not in the body file."""
    item = "- **docs/guide.md:** The guide now names the renamed flag."
    body_file = tmp_path / "body.md"
    body_file.write_text(
        "Closes #42\n\n## Summary\nx\n\n## Doc impact\n\n"
        f"## What changed in each updated document\n\n{item}\n",
        encoding="utf-8",
    )
    captured = _open(
        op,
        monkeypatch,
        "--doc-impact-from-friction",
        derived=_derived(op, *UPDATED),
        body_file=body_file,
    )
    assert op.main() == 3
    opened = captured["body"].split("\n")
    assert opened.index(item) + 1 != 10  # its line in the body file
    (warning,) = [ln for ln in capsys.readouterr().err.splitlines() if item in ln]
    assert warning.startswith(f"warn: line {opened.index(item) + 1} of the description, ")


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
    sign_nothing(work)
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


# --- main(): `--doc-impact-from-friction` (DEC-053, DEC-065) ---------------------


def _doc_impact(body: str) -> list[str]:
    """The section's lines, up to the next section or the provenance footer."""
    section = body.split("## Doc impact", 1)[1].split("\n## ", 1)[0]
    section = section.split(FOOTER_START, 1)[0]
    return [ln for ln in section.splitlines() if ln.strip()]


#: The line the opt-in writes, for `n` documents: it points at the change check.
LINE = "{n} this change affects — their answers are the change check's (`pkit friction check`)."


def test_doc_impact_gets_one_line_pointing_at_the_change_check(op, monkeypatch, capsys) -> None:
    captured = _open(op, monkeypatch, "--doc-impact-from-friction", derived=_derived(op, *TWO))
    assert op.main() == 3
    line = LINE.format(n="2 documents")
    assert _doc_impact(captured["body"]) == [line]
    assert f"doc impact: pre-filled: {line}" in capsys.readouterr().out


def test_doc_impact_names_the_pages_still_carrying_friction(op, monkeypatch, capsys) -> None:
    unanswered = {"location": "docs/cli.md", "kind": "friction", "artefact": "cli"}
    derived = _derived(op, TWO[0], findings=[unanswered])
    captured = _open(op, monkeypatch, "--doc-impact-from-friction", derived=derived)
    assert op.main() == 3
    assert _doc_impact(captured["body"]) == [LINE.format(n="1 document")]
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
        ("unreadable", "not pre-filled — `pkit friction check --json` gave no document"),
    ],
)
def test_doc_impact_is_left_unwritten_without_answers(
    op, monkeypatch, capsys, derived, note
) -> None:
    found = {
        None: None,
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
