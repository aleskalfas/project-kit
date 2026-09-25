"""Every branch- and PR-opening verb targets the DEC-013 base branch (#903).

start-work cuts the branch, and open-pr / create-draft / review-work open its
PR, all through the one shared `lifecycle_inference.resolve_base_branch`:

  * an explicit `--base` wins (on the verbs that take one);
  * else the closing issue's `Integration: integration/<slug>` marker;
  * else the adopter's `default_branch` — never a hardcoded `main`.

Each test drives the verb's real `main()` with its gates and gh/git seams
stubbed, and captures the base handed to the mutating call.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CAP_ROOT = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
SCRIPTS = CAP_ROOT / "scripts"

INTEGRATION = "integration/508-multi-instance-ownership"
MARKED_BODY = f"Integration: {INTEGRATION}\nFeature: #510\n\n## What\nx"
UNMARKED_BODY = "Feature: #510\n\n## What\nx"
DEFAULT_BRANCH = "trunk"  # a non-`main` default proves nothing is hardcoded
EXPLICIT = "release/2"
BRANCH = "fix/42-do-thing"

# (issue body, extra argv, expected base)
MARKER = (MARKED_BODY, [], INTEGRATION)
NO_MARKER = (UNMARKED_BODY, [], DEFAULT_BRANCH)
EXPLICIT_BASE = (MARKED_BODY, ["--base", EXPLICIT], EXPLICIT)

CASES = pytest.mark.parametrize(
    "body,extra_argv,expected",
    [MARKER, NO_MARKER, EXPLICIT_BASE],
    ids=["marker", "no-marker-non-main-default", "explicit-base"],
)


def _load(script: str):
    sys.path.insert(0, str(SCRIPTS))
    name = f"pm_base_branch_{script.replace('-', '_')}_under_test"
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{script}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def verbs():
    loaded = {
        s: _load(s) for s in ("start-work", "open-pr", "create-draft", "review-work")
    }
    yield loaded
    sys.path.remove(str(SCRIPTS))


def _stub_gates(monkeypatch, mod, issue: dict, argv: list[str]) -> None:
    """Pass every pre-mutation gate and serve `issue` as the closing issue."""
    monkeypatch.setattr(sys, "argv", argv)
    monkeypatch.setattr(mod, "resolve_capability_root", lambda _explicit: CAP_ROOT)
    monkeypatch.setattr(mod.bootstrap_gate, "enforce", lambda *a, **k: True)
    monkeypatch.setattr(mod.session_guard, "enforce", lambda **k: True)
    monkeypatch.setattr(
        mod, "load_adopter_config", lambda _root: {"default_branch": DEFAULT_BRANCH}
    )
    monkeypatch.setattr(mod, "_read_members", lambda *a: [])
    monkeypatch.setattr(
        mod, "resolve_invoker_identity", lambda **k: SimpleNamespace(github_login="me")
    )
    monkeypatch.setattr(
        mod, "check_membership", lambda *a: SimpleNamespace(allowed=True)
    )
    monkeypatch.setattr(mod, "_gh_get_issue", lambda _n, _config: issue)


def _issue(body: str) -> dict:
    return {"title": "do thing", "labels": [], "assignees": [], "state": "OPEN", "body": body}


@pytest.mark.parametrize(
    "body,expected",
    [(MARKED_BODY, INTEGRATION), (UNMARKED_BODY, DEFAULT_BRANCH)],
    ids=["marker", "no-marker-non-main-default"],
)
def test_start_work_cuts_the_branch_off_the_resolved_base(
    verbs, monkeypatch, body, expected
) -> None:
    mod = verbs["start-work"]
    _stub_gates(monkeypatch, mod, _issue(body), ["start-work", "42", "--yes"])
    monkeypatch.setattr(mod, "_derive_branch_prefix", lambda *a: "fix")
    monkeypatch.setattr(mod, "_existing_branch_for_issue", lambda _n: None)
    captured = {}

    def fake_create_branch(name, base):
        captured["base"] = base
        return False  # stop before the assignee write / move-issue

    monkeypatch.setattr(mod, "_create_branch", fake_create_branch)
    assert mod.main() == 2
    assert captured["base"] == expected


@CASES
def test_open_pr_targets_the_resolved_base(
    verbs, monkeypatch, body, extra_argv, expected
) -> None:
    mod = verbs["open-pr"]
    argv = ["open-pr", "--type", "fix", "--summary", "do thing", "--draft", "--yes"]
    _stub_gates(monkeypatch, mod, _issue(body), argv + extra_argv)
    monkeypatch.setattr(mod, "_current_branch", lambda: BRANCH)
    captured = {}

    def fake_pr_create(*, title, body, base, draft, config):
        captured["base"] = base
        return None  # stop before the post-create comments / hooks

    monkeypatch.setattr(mod, "_gh_pr_create", fake_pr_create)
    assert mod.main() == 3
    assert captured["base"] == expected


@CASES
def test_create_draft_targets_the_resolved_base(
    verbs, monkeypatch, body, extra_argv, expected
) -> None:
    mod = verbs["create-draft"]
    _stub_gates(monkeypatch, mod, _issue(body), ["create-draft", "42", "--yes", *extra_argv])
    monkeypatch.setattr(mod, "_find_issue_branch", lambda _n: BRANCH)
    monkeypatch.setattr(mod, "_find_pr_for_branch", lambda *a: None)
    captured = {}

    def fake_resolve_base_ref(base):
        captured["gate_base"] = base
        return base

    def fake_commits_beyond(branch, base_ref):
        return 1

    def fake_create_draft(branch, base, title, body, config):
        captured["base"] = base
        return None

    monkeypatch.setattr(mod, "_resolve_base_ref", fake_resolve_base_ref)
    monkeypatch.setattr(mod, "_commits_beyond", fake_commits_beyond)
    monkeypatch.setattr(mod, "_gh_pr_create_draft", fake_create_draft)
    assert mod.main() == 3
    # The commits-ahead gate measures against the same base the PR targets.
    assert captured == {"gate_base": expected, "base": expected}


@CASES
def test_review_work_opens_its_pr_against_the_resolved_base(
    verbs, monkeypatch, body, extra_argv, expected
) -> None:
    mod = verbs["review-work"]
    _stub_gates(monkeypatch, mod, _issue(body), ["review-work", "42", "--yes", *extra_argv])
    monkeypatch.setattr(mod, "_find_issue_branch", lambda _n: BRANCH)
    monkeypatch.setattr(mod, "_find_pr_for_branch", lambda *a: None)
    monkeypatch.setattr(mod, "_ready_body_ok", lambda *a: True)
    captured = {}

    def fake_create_ready(branch, base, title, body, config):
        captured["base"] = base
        return None  # stop before reviewer assignment / move-issue

    monkeypatch.setattr(mod, "_gh_pr_create_ready", fake_create_ready)
    assert mod.main() == 3
    assert captured["base"] == expected


# --- create-draft's commits-beyond-base gate against real git (#903 review) ---


def _git(cwd: Path, *args: str) -> str:
    import subprocess

    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True,
        env={"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
             "GIT_COMMITTER_EMAIL": "t@t", "HOME": str(cwd), "PATH": __import__("os").environ["PATH"]},
    ).stdout.strip()


@pytest.fixture
def integration_clone(tmp_path, monkeypatch):
    """A clone where the integration base exists only as origin/<base>, as
    start-work leaves it: no local integration branch, feature branch cut from
    the remote-tracking ref, one commit ahead."""
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "commit", "-q", "--allow-empty", "-m", "root")
    sha = _git(tmp_path, "rev-parse", "HEAD")
    _git(tmp_path, "update-ref", "refs/remotes/origin/integration/foo", sha)
    _git(tmp_path, "checkout", "-q", "-b", BRANCH, "origin/integration/foo")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_an_integration_base_present_only_on_origin_is_found(verbs, integration_clone) -> None:
    mod = verbs["create-draft"]
    assert mod._resolve_base_ref("integration/foo") == "origin/integration/foo"
    assert mod._commits_beyond(BRANCH, "origin/integration/foo") == 0
    _git(integration_clone, "commit", "-q", "--allow-empty", "-m", "work")
    assert mod._commits_beyond(BRANCH, "origin/integration/foo") == 1


def test_a_missing_base_is_not_reported_as_no_commits(verbs, integration_clone) -> None:
    mod = verbs["create-draft"]
    assert mod._resolve_base_ref("integration/absent") is None


def test_create_draft_names_a_missing_base_instead_of_claiming_no_commits(
    verbs, monkeypatch, capsys
) -> None:
    mod = verbs["create-draft"]
    body = MARKED_BODY
    _stub_gates(monkeypatch, mod, _issue(body), ["create-draft", "42", "--yes"])
    monkeypatch.setattr(mod, "_find_issue_branch", lambda _n: BRANCH)
    monkeypatch.setattr(mod, "_resolve_base_ref", lambda _b: None)
    assert mod.main() == 2
    err = capsys.readouterr().err
    assert "not in this clone" in err
    assert f"git fetch origin {INTEGRATION}" in err
    assert "no commits beyond" not in err
