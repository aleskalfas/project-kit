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


def _run(ep, monkeypatch, argv: list[str], *, body: str = PR_BODY,
         known_issues=(42, 43, 44)) -> SimpleNamespace:
    monkeypatch.setattr(sys, "argv", ["edit-pr", *argv])
    monkeypatch.setattr(ep, "resolve_capability_root", lambda _explicit: CAP_ROOT)
    monkeypatch.setattr(ep.bootstrap_gate, "enforce", lambda *a, **k: True)
    monkeypatch.setattr(ep.session_guard, "enforce", lambda **k: True)
    monkeypatch.setattr(ep, "load_adopter_config", lambda _root: {})
    monkeypatch.setattr(ep, "_read_members", lambda *a: [])
    monkeypatch.setattr(ep, "resolve_invoker_identity", lambda **k: SimpleNamespace(github_login="me"))
    monkeypatch.setattr(ep, "check_membership", lambda *a: SimpleNamespace(allowed=True))
    monkeypatch.setattr(
        ep, "_gh_get_issue",
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


def test_closes_applies_to_a_replaced_body(ep, monkeypatch, tmp_path) -> None:
    new = tmp_path / "body.md"
    new.write_text("Closes #42\n\n## Summary\nrewritten\n\n## Doc impact\n- [x] none\n", encoding="utf-8")
    rec = _run(ep, monkeypatch, ["7", "--body-file", str(new), "--closes", "43", "--yes"])
    assert rec.rc == 0
    assert rec.edits[0]["body"].startswith("Closes #42\nCloses #43\n\n## Summary\nrewritten")
