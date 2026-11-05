"""edit-pr --closes (#1049): a PR gains closing references through the verb.

The flag repeats; each named issue the body does not already close gets a
`Closes #N` line beside the existing ones, so the PR closes every Task it lands
on merge. Every `gh` call is faked.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CAP_ROOT = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
SCRIPT_PATH = CAP_ROOT / "scripts" / "edit-pr.py"

PR_BODY = "Closes #42\n\n## Summary\nwork\n\n## Test plan\n- [x] ran\n\n## Doc impact\n- [x] none\n"


@pytest.fixture(scope="module")
def ep():
    module_name = "pm_edit_pr_under_test"
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _run(
    ep, monkeypatch, argv: list[str], *, body: str = PR_BODY, known_issues=(42, 43, 44)
) -> SimpleNamespace:
    monkeypatch.setattr(sys, "argv", ["edit-pr", *argv])
    monkeypatch.setattr(ep, "resolve_capability_root", lambda _explicit: CAP_ROOT)
    monkeypatch.setattr(ep.bootstrap_gate, "enforce", lambda *a, **k: True)
    monkeypatch.setattr(ep.session_guard, "enforce", lambda **k: True)
    monkeypatch.setattr(ep, "load_adopter_config", lambda _root: {})
    monkeypatch.setattr(ep, "_read_members", lambda *a: [])
    monkeypatch.setattr(
        ep, "resolve_invoker_identity", lambda **k: SimpleNamespace(github_login="me")
    )
    monkeypatch.setattr(ep, "check_membership", lambda *a: SimpleNamespace(allowed=True))
    monkeypatch.setattr(
        ep,
        "_gh_get_issue",
        lambda n, _config: {"number": n, "state": "OPEN"} if n in known_issues else None,
    )

    def fake_gh_run(cmd, config, **kwargs):
        payload = {"title": "feat(pm): land it", "body": body, "state": "OPEN"}
        return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(payload), stderr="")

    monkeypatch.setattr(ep, "gh_run", fake_gh_run)
    edits: list[dict] = []

    def fake_apply(pr_number, *, title, body, current_title, config):
        edits.append({"title": title, "body": body})
        return True

    monkeypatch.setattr(ep, "_gh_apply_edit", fake_apply)
    return SimpleNamespace(rc=ep.main(), edits=edits)


def test_closes_adds_the_reference_beside_the_first(ep, monkeypatch) -> None:
    rec = _run(ep, monkeypatch, ["7", "--closes", "43", "--yes"])
    assert rec.rc == 0
    assert rec.edits[0]["body"].startswith("Closes #42\nCloses #43\n\n## Summary")


def test_closes_repeats(ep, monkeypatch) -> None:
    rec = _run(ep, monkeypatch, ["7", "--closes", "43", "--closes", "44", "--yes"])
    assert rec.rc == 0
    assert rec.edits[0]["body"].startswith("Closes #42\nCloses #43\nCloses #44\n")


def test_a_reference_already_there_is_a_noop(ep, monkeypatch, capsys) -> None:
    rec = _run(ep, monkeypatch, ["7", "--closes", "42", "--yes"])
    assert rec.rc == 0
    assert rec.edits == []
    assert "[noop]" in capsys.readouterr().out


def test_an_unknown_issue_is_refused_before_any_write(ep, monkeypatch) -> None:
    rec = _run(ep, monkeypatch, ["7", "--closes", "9999", "--yes"])
    assert rec.rc == 2
    assert rec.edits == []


def test_force_posts_its_audit_comment(ep, monkeypatch) -> None:
    """Regression: the `--force` audit comment was called without `config`,
    so `edit-pr --force` died with a TypeError before writing — the edit-issue
    bug #567 fixed, still present here."""
    posted: list = []
    monkeypatch.setattr(
        ep, "_gh_pr_comment", lambda n, body, config: posted.append((n, body)) or True
    )
    rec = _run(
        ep, monkeypatch, ["7", "--body", "no closing line, no doc impact", "--force", "--yes"]
    )
    assert rec.rc == 0
    assert posted and posted[0][0] == 7
    assert "--force" in posted[0][1]


def test_closes_applies_to_a_replaced_body(ep, monkeypatch, tmp_path) -> None:
    new = tmp_path / "body.md"
    new.write_text(
        "Closes #42\n\n## Summary\nrewritten\n\n## Doc impact\n- [x] none\n", encoding="utf-8"
    )
    rec = _run(ep, monkeypatch, ["7", "--body-file", str(new), "--closes", "43", "--yes"])
    assert rec.rc == 0
    assert rec.edits[0]["body"].startswith("Closes #42\nCloses #43\n\n## Summary\nrewritten")


# ---- a list of the answers in the description (DEC-065 point 1) ---------------------

FOOTER = (
    "<!-- pkit-provenance:start -->\n\n---\n<sub>🧰 pkit · tree `1` · pm `2`</sub>\n"
    "<!-- pkit-provenance:end -->\n"
)


def _section(ep, reason: str, head: str = "a" * 40, heading: str | None = None) -> str:
    """The section an earlier run of land-work or open-pr wrote, for one answer with
    `reason` (DEC-055 point 1)."""
    fa = ep.friction_answers
    return "\n".join(
        [
            heading or fa.HEADING,
            "",
            f"{fa.MARKER_START} head={head} base={'b' * 40} -->",
            f'1. `docs/guide.md` — **still accurate**: "``{reason}``"',
            fa.MARKER_END,
        ]
    )


def _carrying(ep, reason: str = "The guide holds; fixes #99 is elsewhere.") -> str:
    return f"{PR_BODY}\n{_section(ep, reason)}\n\n{FOOTER}"


#: The section's heading, and the one an earlier run wrote it under.
HEADING = "## Documentation this change affects"
FORMER_HEADING = "## Friction answers"
#: What edit-pr says when it drops a section.
DROPPED = f"warn: the `{HEADING}` section is dropped"


def _sections(body: str) -> int:
    return body.count(HEADING) + body.count(FORMER_HEADING)


@pytest.mark.parametrize("how", ["--body", "--body-file"])
def test_a_replaced_body_drops_the_section_the_description_and_the_body_carried(
    ep, monkeypatch, tmp_path, capsys, how
) -> None:
    """No command carries a list across an edit (DEC-065 point 1): the one the
    description carried and the one the supplied body carries are both dropped."""
    body = _carrying(ep)
    supplied = "Closes #42\n\n## Summary\nrewritten\n\n## Doc impact\n- [x] none\n\n" + _section(
        ep, "A list an agent wrote.", head="c" * 40
    )
    if how == "--body-file":
        path = tmp_path / "body.md"
        path.write_text(supplied, encoding="utf-8")
        supplied = str(path)
    rec = _run(ep, monkeypatch, ["7", how, supplied, "--yes"], body=body)
    assert rec.rc == 0
    written = rec.edits[0]["body"]
    assert "rewritten" in written and "A list an agent wrote." not in written
    assert _sections(written) == 0 and "The guide holds" not in written
    assert "- [x] none\n\n<!-- pkit-provenance:start -->" in written
    assert DROPPED in capsys.readouterr().err


def test_appended_text_drops_the_section(ep, monkeypatch, capsys) -> None:
    rec = _run(
        ep, monkeypatch, ["7", "--append", "## Notes\n\nA later note.", "--yes"], body=_carrying(ep)
    )
    assert rec.rc == 0
    written = rec.edits[0]["body"]
    assert "A later note.\n\n<!-- pkit-provenance:start -->" in written
    assert _sections(written) == 0
    assert DROPPED in capsys.readouterr().err


def test_a_description_with_no_section_draws_no_warning(ep, monkeypatch, capsys) -> None:
    rec = _run(ep, monkeypatch, ["7", "--append", "A note.", "--yes"], body=f"{PR_BODY}\n{FOOTER}")
    assert rec.rc == 0
    assert "A note." in rec.edits[0]["body"]
    assert DROPPED not in capsys.readouterr().err


def test_closes_reads_no_reference_in_the_section_and_drops_it(ep, monkeypatch) -> None:
    body = _carrying(ep)
    rec = _run(ep, monkeypatch, ["7", "--closes", "99", "--yes"], body=body, known_issues=(42, 99))
    assert rec.rc == 0
    written = rec.edits[0]["body"]
    assert written.startswith("Closes #42\nCloses #99\n\n## Summary")
    assert _sections(written) == 0


def test_a_closing_reference_only_in_the_section_meets_no_requirement(ep) -> None:
    section = _section(ep, "fixes #42 — see ## Doc impact")
    body = f"## Summary\nwork\n\n{section}\n"
    labels = [f.label for f in ep._validate(title="feat(pm): x", body=body, titles={})]
    assert labels == ["body.closes", "body.doc-impact"]


def test_of_two_lists_both_are_dropped(ep, monkeypatch) -> None:
    stale = _section(ep, "An earlier head's words.", head="e" * 40)
    latest = _section(ep, "The latest words.")
    body = f"{PR_BODY}\n{stale}\n\n{latest}\n\n{FOOTER}"
    rec = _run(ep, monkeypatch, ["7", "--append", "A note.", "--yes"], body=body)
    assert rec.rc == 0
    written = rec.edits[0]["body"]
    assert "words." not in written and _sections(written) == 0


@pytest.mark.parametrize("heading", [HEADING, FORMER_HEADING], ids=["heading", "former heading"])
def test_a_section_typed_under_the_heading_stays(ep, monkeypatch, capsys, heading) -> None:
    """Only a region a command wrote is dropped: no list remains for a person's section
    to be mistaken for (DEC-065 point 1)."""
    hand = f"{heading}\n\nIn the author's words.\n"
    rec = _run(ep, monkeypatch, ["7", "--append", hand, "--yes"], body=f"{PR_BODY}\n{FOOTER}")
    assert rec.rc == 0
    assert "In the author's words." in rec.edits[0]["body"]
    assert DROPPED not in capsys.readouterr().err


def test_a_start_marker_with_no_end_warns_and_stays(ep, monkeypatch, capsys) -> None:
    marker = ep.friction_answers.MARKER_START
    quoted = f"```\n{marker} head=x base=y -->\n```\n\nAfter the quote.\n"
    rec = _run(ep, monkeypatch, ["7", "--append", quoted, "--yes"], body=f"{PR_BODY}\n{FOOTER}")
    assert rec.rc == 0
    written = rec.edits[0]["body"]
    assert marker in written and "After the quote." in written
    assert f"warn: {ep.friction_answers.ORPHAN_WARNING}" in capsys.readouterr().err


def test_a_list_an_earlier_run_left_under_the_former_heading_is_dropped(ep, monkeypatch) -> None:
    """The markers identify the list, and the former heading directly above it goes
    with it: no stray former heading is left."""
    earlier = _section(ep, "Words of an earlier run.", heading=FORMER_HEADING)
    body = f"{PR_BODY}\n{earlier}\n\n{FOOTER}"
    rec = _run(ep, monkeypatch, ["7", "--append", "A note.", "--yes"], body=body)
    assert rec.rc == 0
    written = rec.edits[0]["body"]
    assert _sections(written) == 0 and "Words of an earlier run." not in written
    assert "A note.\n\n<!-- pkit-provenance:start -->" in written


# ---- the author's sentences (DEC-065 points 1 and 3) ---------------------------------

SENTENCES = "## What changed in each updated document"


def test_an_edit_keeps_the_author_s_sentences_as_written(ep, monkeypatch, capsys) -> None:
    """The sentences stay in the author's own section. edit-pr derives nothing, so it
    warns of no updated document given no sentence: review-work refuses one."""
    said = f"{SENTENCES}\n\n- `docs/guide.md`: The guide names the new flag.\n"
    body = f"{PR_BODY}\n{_section(ep, 'Holds.')}\n\n{FOOTER}"
    rec = _run(ep, monkeypatch, ["7", "--append", said, "--yes"], body=body)
    assert rec.rc == 0
    written = rec.edits[0]["body"]
    assert f"{said}\n<!-- pkit-provenance:start -->" in written
    out = capsys.readouterr().out
    assert "validation: clean (no findings)." in out


@pytest.mark.parametrize(
    ("item", "unread"),
    [
        ("- **docs/guide.md:** The guide names the new flag.", True),
        ("- docs/guide.md: The guide names the new flag.", True),
        ("- `docs/guide.md`: The guide names the new flag.", False),
    ],
    ids=["bold path", "no code span", "read form"],
)
def test_an_item_it_cannot_read_is_a_warning_naming_its_line_and_the_form(
    ep, monkeypatch, capsys, item, unread
) -> None:
    """On PR #1519 four sentences in bold read as none, while edit-pr said
    "validation: clean". The edit is still written; the validation names the line
    and the form a sentence takes."""
    body = f"{PR_BODY}\n{_section(ep, 'Holds.')}\n\n{FOOTER}"
    said = f"{SENTENCES}\n\n{item}\n"
    rec = _run(ep, monkeypatch, ["7", "--append", said, "--yes"], body=body)
    assert rec.rc == 0
    written = rec.edits[0]["body"]
    out = capsys.readouterr().out
    if not unread:
        assert "validation: clean (no findings)." in out
        return
    line = written.split("\n").index(item) + 1  # its line in the description written
    assert "validation: clean" not in out
    assert (
        f"  [warning] body.sentences: line {line} of the description, under `## What changed in "
        f'each updated document`, is not read as a sentence: "{item}" — write it as "- `path`: '
        "sentence\", starting in the line's first column, the document in a code span as the "
        "change check names it"
    ) in out.splitlines()
