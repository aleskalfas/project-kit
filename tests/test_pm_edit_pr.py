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


# ---- the friction answers' section (DEC-055) ---------------------------------------

FOOTER = (
    "<!-- pkit-provenance:start -->\n\n---\n<sub>🧰 pkit · tree `1` · pm `2`</sub>\n"
    "<!-- pkit-provenance:end -->\n"
)


def _section(ep, reason: str, head: str = "a" * 40) -> str:
    """The section land-work or open-pr writes, for one answer with `reason`."""
    entry = {
        "artefact": "guide",
        "location": "docs/guide.md",
        "answer": "unchanged",
        "anchor": None,
        "reason": reason,
        "kept": [],
        "asked": True,
        "status": "stands",
        "new": False,
    }
    document = {"base": {"commit": "b" * 40}, "answers": [entry], "unreadable": []}
    section = ep.friction_answers.render(document, head)
    assert section is not None
    return section


def _carrying(ep, reason: str = "The guide holds; fixes #99 is elsewhere.") -> tuple[str, str]:
    section = _section(ep, reason)
    return section, f"{PR_BODY}\n{section}\n\n{FOOTER}"


def _sections(body: str) -> int:
    return body.count("## Friction answers")


@pytest.mark.parametrize("how", ["--body", "--body-file"])
def test_a_replaced_body_keeps_the_section_the_description_carried(
    ep, monkeypatch, tmp_path, how
) -> None:
    section, body = _carrying(ep)
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
    assert _sections(written) == 1
    assert f"- [x] none\n\n{section}\n\n<!-- pkit-provenance:start -->" in written


def test_appended_text_lands_outside_the_section(ep, monkeypatch) -> None:
    section, body = _carrying(ep)
    rec = _run(ep, monkeypatch, ["7", "--append", "## Notes\n\nA later note.", "--yes"], body=body)
    assert rec.rc == 0
    written = rec.edits[0]["body"]
    assert f"A later note.\n\n{section}\n\n<!-- pkit-provenance:start -->" in written
    assert _sections(written) == 1


def test_closes_reads_no_reference_in_the_section_and_keeps_it(ep, monkeypatch) -> None:
    section, body = _carrying(ep)
    rec = _run(ep, monkeypatch, ["7", "--closes", "99", "--yes"], body=body, known_issues=(42, 99))
    assert rec.rc == 0
    written = rec.edits[0]["body"]
    assert written.startswith("Closes #42\nCloses #99\n\n## Summary")
    assert section in written and _sections(written) == 1


def test_a_closing_reference_only_in_the_section_meets_no_requirement(ep) -> None:
    section = _section(ep, "fixes #42 — see ## Doc impact")
    body = f"## Summary\nwork\n\n{section}\n"
    labels = [f.label for f in ep._validate(title="feat(pm): x", body=body, titles={})]
    assert labels == ["body.closes", "body.doc-impact"]


def test_of_two_lists_the_latest_is_kept_and_the_other_dropped(ep, monkeypatch, capsys) -> None:
    """Every write places its list last, so of two the last is the latest: edit-pr
    carries it, drops the other, and says so."""
    stale = _section(ep, "An earlier head's words.", head="e" * 40)
    latest = _section(ep, "The latest words.")
    body = f"{PR_BODY}\n{stale}\n\n{latest}\n\n{FOOTER}"
    rec = _run(ep, monkeypatch, ["7", "--append", "A note.", "--yes"], body=body)
    assert rec.rc == 0
    written = rec.edits[0]["body"]
    assert "The latest words." in written and "An earlier head's words." not in written
    assert _sections(written) == 1
    assert "edit-pr keeps only the latest list the description carried" in capsys.readouterr().err


def test_a_section_typed_by_hand_is_dropped(ep, monkeypatch, capsys) -> None:
    section, body = _carrying(ep)
    hand = "## Friction answers\n\n1. docs/guide.md — unchanged: as I recall it\n"
    rec = _run(ep, monkeypatch, ["7", "--append", hand, "--yes"], body=body)
    assert rec.rc == 0
    written = rec.edits[0]["body"]
    assert "as I recall it" not in written and section in written and _sections(written) == 1
    assert "drops every other `## Friction answers` section" in capsys.readouterr().err
