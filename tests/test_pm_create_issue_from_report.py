"""Tests for create-issue's `--from-report <N>` auto-link (DEC-048, #645).

The contract under test: after a successful create, the script links the new
issue into feedback/CR #N's `## Tracked by` by invoking the backbone's
canonical editor — `pkit report link <N> <new>` as a subprocess (the
one-linker rule: pm never reimplements the Tracked-by edit). Failure posture:
a link failure after a successful create warns loudly with the exact
remediation command, surfaces the backbone verb's refusal verbatim, exits 4,
and never rolls the created issue back. Without the flag, behaviour is
byte-unchanged (no `pkit` subprocess at all).

Conventions follow tests/test_pm_create_issue.py: the script is loaded via
importlib; `main()` is driven against a staged minimal capability tree with
`subprocess.run` faked per-command.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = (
    REPO_ROOT
    / ".pkit"
    / "capabilities"
    / "project-management"
    / "scripts"
    / "create-issue.py"
)

# The backbone verb's maintainer-side refusal, as `pkit report link` emits it
# outside the report-target repo — must reach the user verbatim.
_TARGET_REFUSAL = (
    "Error: the maintainer side (inbox/link/unlink) runs only inside the "
    "report target repo (acme/target-repo). Cd into it and retry."
)


@pytest.fixture(scope="module")
def ci():
    """Load create-issue.py as a module via importlib."""
    module_name = "pm_create_issue_from_report_under_test"
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class _FakeLink:
    """Minimal stand-in for containment.LinkResult — carries `ok` + `detail`."""

    def __init__(self, detail: str, *, ok: bool) -> None:
        self.detail = detail
        self.ok = ok


def _mark_bootstrapped(cap_root: Path) -> None:
    """Make a staged tree look like the bootstrapped project it stands in for.

    Every pm verb except the five setup/diagnosis ones refuses a project with no
    bootstrap stamp or no adopter config (the #747 prerequisite gate); a staged
    tree standing in for a live project is a bootstrapped one. The config is
    seeded only when absent, so a test that stages its own keeps it, and the
    stamp is left unbound (`repo:` null) so no git remote is needed in a tmp tree.
    """
    project = cap_root / "project"
    project.mkdir(parents=True, exist_ok=True)
    config = project / "config.yaml"
    if not config.is_file():
        config.write_text(
            "schema_version: 1\ndefault_branch: main\nworkstreams: []\n",
            encoding="utf-8",
        )
    (project / "bootstrap-stamp.yaml").write_text(
        "schema_version: 1\n"
        "bootstrap:\n"
        "  completed_at: '2026-01-01T00:00:00+00:00'\n"
        "  capability_version: 0.0.0-test\n"
        "  by: bootstrap\n"
        "  repo:\n",
        encoding="utf-8",
    )


def _stage_capability_tree(tmp_path: Path) -> Path:
    """Stage a minimal pm capability tree main() can run against (no board)."""
    root = tmp_path / ".pkit" / "capabilities" / "project-management"
    (root / "schemas").mkdir(parents=True)
    (root / "templates").mkdir(parents=True)
    (root / "project").mkdir(parents=True)

    (root / "schemas" / "issue-types.yaml").write_text(
        "types:\n"
        "  task:\n"
        "    title_prefix: Task\n"
        "    title_case: title\n"
        "    parent_issue_types: [feature, umbrella, epic, milestone]\n"
        "    parent_ref_form: 'Feature: #<N>'\n"
        "    parent_ref_optional: false\n"
        "    parent_ref_required_severity: '[validation-severity:hard-reject]'\n",
        encoding="utf-8",
    )
    (root / "schemas" / "titles.yaml").write_text(
        "formats:\n"
        "  issue-task:\n"
        "    pattern: '^\\[(Task|Bug|Docs|Test|Refactor|Chore)\\] .+$'\n",
        encoding="utf-8",
    )
    (root / "schemas" / "body-format.yaml").write_text(
        "sections: {}\n", encoding="utf-8"
    )
    (root / "templates" / "Task.md").write_text(
        "---\nname: Task\n---\nFeature: #\n\n## What\nfoo\n", encoding="utf-8"
    )
    (root / "project" / "config.yaml").write_text(
        "workstreams: [spyre]\n", encoding="utf-8"
    )
    # Empty members → open mode (membership passes for any resolved identity).
    (root / "project" / "members.yaml").write_text("members: []\n", encoding="utf-8")
    _mark_bootstrapped(root)
    return root


def _dispatcher(create_url: str, *, pkit_rc: int = 0, pkit_stderr: str = ""):
    """A fake subprocess.run answering the gh calls main() makes AND recording
    every argv — including a `pkit report link` invocation, whose outcome is
    configurable. Returns (fake_run, calls) where `calls` is every argv seen.
    """
    calls: list[list[str]] = []

    def fake_run(cmd, *args, **kwargs):
        class _Proc:
            returncode = 0
            stdout = ""
            stderr = ""

        proc = _Proc()
        calls.append(list(cmd))
        joined = " ".join(str(c) for c in cmd)
        if cmd and cmd[0] == "pkit":
            proc.returncode = pkit_rc
            proc.stderr = pkit_stderr
            proc.stdout = "" if pkit_rc else "Linked."
            return proc
        if "issue" in cmd and "create" in cmd:
            proc.stdout = create_url + "\n"
        elif "repo" in cmd and "view" in cmd:
            proc.stdout = "acme/repo"
        elif "api" in cmd and "user" in joined:
            proc.stdout = "filer-login"
        return proc

    return fake_run, calls


def _run_main(ci, root: Path, monkeypatch, *, extra_argv: list[str]) -> int:
    monkeypatch.setenv("PM_INVOKER_LOGIN", "filer-login")
    monkeypatch.setattr(ci, "link_sub_issue", lambda *a, **k: _FakeLink("ok", ok=True))
    monkeypatch.setattr(
        ci.sys,
        "argv",
        [
            "create-issue.py",
            "--type", "task",
            "--title", "fix the reported thing",
            "--parent", "1",
            "--workstream", "spyre",
            "--capability-root", str(root),
            "--yes",
            *extra_argv,
        ],
    )
    return ci.main()


# --- the flag links after a successful create -------------------------------


def test_from_report_invokes_pkit_report_link_after_create(
    ci, tmp_path, monkeypatch
) -> None:
    """`--from-report 77` on a successful create invokes the backbone's
    canonical editor — argv `pkit report link 77 55` — and exits 0. The
    one-linker rule realized: a subprocess to the verb, no body edit here."""
    root = _stage_capability_tree(tmp_path)
    fake_run, calls = _dispatcher("https://github.com/acme/repo/issues/55")
    monkeypatch.setattr(ci.subprocess, "run", fake_run)

    rc = _run_main(ci, root, monkeypatch, extra_argv=["--from-report", "77"])

    assert rc == 0
    pkit_calls = [c for c in calls if c and c[0] == "pkit"]
    assert pkit_calls == [["pkit", "report", "link", "77", "55"]]


def test_from_report_link_runs_after_the_create_call(ci, tmp_path, monkeypatch) -> None:
    """The link fires only AFTER `gh issue create` succeeded (it needs the new
    number) — never before any gh mutation."""
    root = _stage_capability_tree(tmp_path)
    fake_run, calls = _dispatcher("https://github.com/acme/repo/issues/55")
    monkeypatch.setattr(ci.subprocess, "run", fake_run)

    _run_main(ci, root, monkeypatch, extra_argv=["--from-report", "77"])

    create_idx = next(
        i for i, c in enumerate(calls) if "issue" in c and "create" in c
    )
    pkit_idx = next(i for i, c in enumerate(calls) if c and c[0] == "pkit")
    assert create_idx < pkit_idx


# --- failure posture: warn + remediation + exit 4, never rollback -----------


def test_from_report_link_failure_warns_exits_4_and_never_rolls_back(
    ci, tmp_path, monkeypatch, capsys
) -> None:
    """A failed link after a successful create: loud warning carrying the exact
    remediation command, exit 4 — and NO rollback (no `gh issue delete`/`close`
    is ever issued for the created issue)."""
    root = _stage_capability_tree(tmp_path)
    fake_run, calls = _dispatcher(
        "https://github.com/acme/repo/issues/55", pkit_rc=1, pkit_stderr="gh error."
    )
    monkeypatch.setattr(ci.subprocess, "run", fake_run)

    rc = _run_main(ci, root, monkeypatch, extra_argv=["--from-report", "77"])

    assert rc == 4
    err = capsys.readouterr().err
    assert "issue created but NOT linked" in err
    assert "pkit report link 77 55" in err  # the exact remediation command
    # No rollback: the create happened, and no destructive gh call followed.
    assert any("create" in c for c in calls if c and c[0] == "gh")
    assert not any(
        c[0] == "gh" and ("delete" in c or "close" in c) for c in calls if c
    )


def test_from_report_surfaces_backbone_refusal_verbatim(
    ci, tmp_path, monkeypatch, capsys
) -> None:
    """The maintainer-side same-repo check belongs to the backbone verb; when it
    refuses (not in the report-target repo), its message reaches the user
    verbatim — pm neither duplicates nor paraphrases the gate."""
    root = _stage_capability_tree(tmp_path)
    fake_run, _calls = _dispatcher(
        "https://github.com/acme/repo/issues/55",
        pkit_rc=1,
        pkit_stderr=_TARGET_REFUSAL,
    )
    monkeypatch.setattr(ci.subprocess, "run", fake_run)

    rc = _run_main(ci, root, monkeypatch, extra_argv=["--from-report", "77"])

    assert rc == 4
    assert _TARGET_REFUSAL in capsys.readouterr().err


# --- flag absent ⇒ unchanged behaviour --------------------------------------


def test_without_flag_no_pkit_invocation_and_exit_0(ci, tmp_path, monkeypatch) -> None:
    """No `--from-report` ⇒ byte-unchanged create path: exit 0 and NO `pkit`
    subprocess of any kind."""
    root = _stage_capability_tree(tmp_path)
    fake_run, calls = _dispatcher("https://github.com/acme/repo/issues/56")
    monkeypatch.setattr(ci.subprocess, "run", fake_run)

    rc = _run_main(ci, root, monkeypatch, extra_argv=[])

    assert rc == 0
    assert not any(c and c[0] == "pkit" for c in calls)


# --- _link_from_report unit edges -------------------------------------------


def test_link_from_report_pkit_missing_warns_with_remediation(
    ci, monkeypatch, capsys
) -> None:
    """`pkit` not on PATH: warn (with the remediation command) and return 4 —
    the caller's created issue stays."""
    def raise_missing(*a, **k):
        raise FileNotFoundError("pkit")

    monkeypatch.setattr(ci.subprocess, "run", raise_missing)
    assert ci._link_from_report(77, 55) == 4
    err = capsys.readouterr().err
    assert "`pkit` not on PATH" in err
    assert "pkit report link 77 55" in err


def test_link_from_report_unparsable_new_number_warns_with_placeholder(
    ci, monkeypatch, capsys
) -> None:
    """When the new issue number could not be parsed from the gh output there is
    nothing to link — warn with a placeholder remediation and return 4."""
    def boom(*a, **k):  # pragma: no cover — no subprocess may run
        raise AssertionError("no pkit call may run without a new issue number")

    monkeypatch.setattr(ci.subprocess, "run", boom)
    assert ci._link_from_report(77, None) == 4
    err = capsys.readouterr().err
    assert "pkit report link 77 <new-issue-number>" in err


def test_link_from_report_success_returns_0(ci, monkeypatch, capsys) -> None:
    class _Proc:
        returncode = 0
        stdout = "Linked #55 into #77's Tracked by.\n"
        stderr = ""

    monkeypatch.setattr(ci.subprocess, "run", lambda *a, **k: _Proc())
    assert ci._link_from_report(77, 55) == 0
    out = capsys.readouterr().out
    assert "linked #55 into report #77" in out
