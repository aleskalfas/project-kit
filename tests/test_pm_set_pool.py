"""Putting a Milestone into a pool of workers: `set-pool` and `create-milestone
--pool` (DEC-061 points 2 and 6).

Each asks the person, at a terminal or by `--yes`, and refuses off a terminal
without it. Each writes one `Pool:` line, replacing the one it finds, and logs
the change and the consent in the description, never in the `Pool:` form.
`set-pool` reads the description again right before it writes. Every `gh` call
and the topology's pools are fakes; no test reaches GitHub.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CAP_ROOT = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
SCRIPTS = CAP_ROOT / "scripts"


def _load(name: str, script: str) -> Any:
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def sp():
    return _load("pm_set_pool_under_test", "set-pool.py")


@pytest.fixture(scope="module")
def cm():
    return _load("pm_create_milestone_pool_under_test", "create-milestone.py")


class Milestones:
    """Milestones as GitHub holds them: each read returns the description now,
    and `then` changes it after the first read, as a person's edit would."""

    def __init__(self, description: str, *, state: str = "open", then: str | None = None):
        self.description = description
        self.state = state
        self.then = then
        self.reads = 0
        self.patches: list[list[str]] = []

    def fetch(self, number: int, _config: dict) -> dict:
        self.reads += 1
        found = {
            "number": number,
            "title": "Sprint 3: auth",
            "state": self.state,
            "description": self.description,
        }
        if self.then is not None:
            self.description, self.then = self.then, None
        return found

    def gh(self, argv: list[str], _config: dict, **_kw: Any) -> subprocess.CompletedProcess[str]:
        assert argv[:4] == ["gh", "api", "-X", "PATCH"], argv
        self.patches.append(argv)
        self.description = argv[-1].removeprefix("description=")
        return subprocess.CompletedProcess(argv, 0, "{}", "")


def _declared(sp_or_cm: Any, monkeypatch: pytest.MonkeyPatch, pools: Any, note: Any = None):
    monkeypatch.setattr(sp_or_cm.pools, "declared_pools", lambda _root: (pools, note))


def _run(sp, monkeypatch, held: Milestones, name: str | None, *, yes: bool = True, tty=False):
    monkeypatch.setattr(sp.milestone, "fetch_milestone", held.fetch)
    monkeypatch.setattr(sp, "gh_run", held.gh)
    monkeypatch.setattr(sp.consent, "at_a_terminal", lambda: tty)
    return sp.set_pool(CAP_ROOT, "3", name, config={}, yes=yes)


def test_it_puts_a_milestone_into_a_pool_and_logs_the_consent(sp, monkeypatch, capsys) -> None:
    _declared(sp, monkeypatch, ("alpha", "bravo"))
    held = Milestones("Close trigger: either\n\nAuth work.")
    assert _run(sp, monkeypatch, held, "alpha") == 0
    lines = held.description.splitlines()
    assert lines[:2] == ["Close trigger: either", "Pool: alpha"]
    assert sum(line.startswith("Pool:") for line in lines) == 1
    assert "Pool change by `pkit pm set-pool`" in lines[-1] and "none → alpha" in lines[-1]
    assert "consent" in lines[-1]
    assert "[ok] milestone #3 is in the pool alpha." in capsys.readouterr().out


def test_a_change_replaces_the_line_and_never_adds_a_second(sp, monkeypatch) -> None:
    _declared(sp, monkeypatch, ("alpha", "bravo"))
    held = Milestones("Close trigger: either\nPool: alpha\n\nWork.")
    assert _run(sp, monkeypatch, held, "bravo") == 0
    pool_lines = [line for line in held.description.splitlines() if line.startswith("Pool:")]
    assert pool_lines == ["Pool: bravo"]
    assert "alpha → bravo" in held.description


def test_clearing_takes_the_milestone_out_and_still_asks(sp, monkeypatch, capsys) -> None:
    _declared(sp, monkeypatch, ("alpha",))
    held = Milestones("Close trigger: either\nPool: alpha")
    assert _run(sp, monkeypatch, held, None, yes=False) == 1
    assert held.patches == []
    assert "is the person's to authorise" in capsys.readouterr().err
    assert _run(sp, monkeypatch, held, None) == 0
    assert not any(line.startswith("Pool:") for line in held.description.splitlines())


def test_off_a_terminal_without_yes_nothing_is_written(sp, monkeypatch, capsys) -> None:
    _declared(sp, monkeypatch, ("alpha",))
    held = Milestones("Close trigger: either")
    assert _run(sp, monkeypatch, held, "alpha", yes=False) == 1
    assert held.patches == []
    assert "pkit pm set-pool" in capsys.readouterr().err


def test_a_person_at_a_terminal_is_asked(sp, monkeypatch) -> None:
    _declared(sp, monkeypatch, ("alpha",))
    held = Milestones("Close trigger: either")
    asked: list[str] = []
    monkeypatch.setattr("builtins.input", lambda prompt: asked.append(prompt) or "y")
    assert _run(sp, monkeypatch, held, "alpha", yes=False, tty=True) == 0
    assert asked == ["Put milestone #3 into the pool alpha? [y/N] "]
    assert held.patches


def test_the_description_is_read_again_right_before_the_write(sp, monkeypatch) -> None:
    _declared(sp, monkeypatch, ("alpha",))
    held = Milestones("Close trigger: either", then="Close trigger: either\n\nA person's note.")
    assert _run(sp, monkeypatch, held, "alpha") == 0
    assert held.reads == 2
    assert "A person's note." in held.description


@pytest.mark.parametrize(
    ("declared", "note", "said"),
    [
        (("bravo",), None, "does not declare the pool alpha"),
        (None, None, "declares no pools"),
        (None, "the topology could not be read", "cannot be told"),
    ],
)
def test_a_pool_the_topology_does_not_declare_is_refused(
    sp, monkeypatch, capsys, declared, note, said
) -> None:
    _declared(sp, monkeypatch, declared, note)
    held = Milestones("Close trigger: either")
    assert _run(sp, monkeypatch, held, "alpha") == 2
    assert held.patches == []
    assert said in capsys.readouterr().err


def test_a_closed_milestone_and_a_noop_write_nothing(sp, monkeypatch, capsys) -> None:
    _declared(sp, monkeypatch, ("alpha",))
    closed = Milestones("Pool: alpha", state="closed")
    assert _run(sp, monkeypatch, closed, None) == 2
    already = Milestones("Close trigger: either\nPool: alpha")
    assert _run(sp, monkeypatch, already, "alpha") == 0
    none = Milestones("Close trigger: either")
    assert _run(sp, monkeypatch, none, None) == 0
    assert closed.patches == already.patches == none.patches == []
    assert "is in the pool alpha already" in capsys.readouterr().out


# ---- create-milestone --pool -------------------------------------------------------


def _create(cm, monkeypatch, argv: list[str], *, tty: bool = False):
    created: list[dict] = []
    monkeypatch.setattr(sys, "argv", ["create-milestone", "sprint", "--name", "auth", *argv])
    monkeypatch.setattr(cm, "resolve_capability_root", lambda _e: CAP_ROOT)
    monkeypatch.setattr(cm.bootstrap_gate, "enforce", lambda *a, **k: True)
    monkeypatch.setattr(cm.session_guard, "enforce", lambda **k: True)
    monkeypatch.setattr(cm, "load_adopter_config", lambda _r: {})
    monkeypatch.setattr(
        cm, "resolve_invoker_identity", lambda **k: SimpleNamespace(github_login="me")
    )
    monkeypatch.setattr(cm, "check_membership", lambda *a: SimpleNamespace(allowed=True))
    config = {
        "milestone_categories": {
            "sprint": {"title_format": "Sprint {n}: {name}", "close_trigger_default": "either"}
        }
    }

    def read_yaml(path: Path, _loader: Any) -> dict:
        return config if path.name == "config.yaml" else {}

    monkeypatch.setattr(cm, "_read_yaml", read_yaml)
    monkeypatch.setattr(cm, "_next_number_for_category", lambda *_a: 3)
    monkeypatch.setattr(cm, "_existing_milestone_with_title", lambda *_a: None)
    monkeypatch.setattr(
        cm,
        "_gh_create_milestone",
        lambda **kw: created.append(kw) or "https://github.com/o/r/milestone/3",
    )
    monkeypatch.setattr(cm.consent, "at_a_terminal", lambda: tty)
    return cm.main(), created


def test_create_milestone_puts_the_new_milestone_into_a_declared_pool(cm, monkeypatch) -> None:
    _declared(cm, monkeypatch, ("alpha",))
    rc, created = _create(cm, monkeypatch, ["--pool", "alpha", "--description", "Auth.", "--yes"])
    assert rc == 0
    body = created[0]["body"].splitlines()
    assert body[:2] == ["Close trigger: either", "Pool: alpha"]
    assert "Auth." in body
    assert body[-1].startswith("Pool change by `pkit pm create-milestone`")


def test_create_milestone_with_a_pool_off_a_terminal_without_yes_is_refused(
    cm, monkeypatch, capsys
) -> None:
    _declared(cm, monkeypatch, ("alpha",))
    rc, created = _create(cm, monkeypatch, ["--pool", "alpha"])
    assert (rc, created) == (1, [])
    assert "is the person's to authorise" in capsys.readouterr().err


def test_create_milestone_refuses_an_undeclared_pool(cm, monkeypatch, capsys) -> None:
    _declared(cm, monkeypatch, ("alpha",))
    rc, created = _create(cm, monkeypatch, ["--pool", "bravo", "--yes"])
    assert (rc, created) == (2, [])
    assert "does not declare the pool bravo" in capsys.readouterr().err


def test_create_milestone_without_a_pool_writes_no_pool_line(cm, monkeypatch) -> None:
    rc, created = _create(cm, monkeypatch, ["--yes"])
    assert rc == 0
    assert "Pool" not in created[0]["body"]
    assert json.dumps(created[0]["body"]) == json.dumps("Close trigger: either")
