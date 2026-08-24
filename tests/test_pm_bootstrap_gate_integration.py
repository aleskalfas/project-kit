"""End-to-end: the prerequisite gate fires inside the real pm scripts (#747).

The unit tests (`test_pm_bootstrap_gate.py`) prove the gate's verdicts and the
coverage guard (`test_pm_bootstrap_gate_coverage.py`) proves every registered
verb calls it. This file proves the **live wiring** — that a real script,
launched as a subprocess the way an agent or a CI job launches it, refuses
before it does any work, and that the five exempt verbs still run on the same
un-bootstrapped tree.

One representative per family is driven here, because the gate is the same
single extracted check wired identically into all sixty:

  * a **mutator** (`create-issue`) — the classic write path;
  * a **read verb** (`show-issue`) — gated because it would render an adopter's
    remapped classification as the kit's assumed values: confidently wrong
    rather than blank;
  * an **engine-called predicate** (`detect-todo`) — gated because answering
    "where is this issue in the lifecycle?" from assumed defaults is the same
    silent-wrong-answer shape. Its non-zero exit is what the process engine
    reads as indeterminate, and the engine fails closed on that.

Direct script invocation is deliberately the launch mechanism: the dispatcher
was rejected as the gate's home precisely because it does not see these calls.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CAP_SRC = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
SCRIPTS = CAP_SRC / "scripts"

REFUSAL_MARKER = "prerequisites are not met"

VALID_CONFIG = "schema_version: 1\ndefault_branch: main\nworkstreams: []\n"


def _git(args: list[str], cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def _project(tmp_path: Path, *, config: str = VALID_CONFIG) -> Path:
    """An adopter project with the capability installed but NOT bootstrapped.

    Carries the real `schemas/` and `templates/` (so a script gets far enough to
    do work if the gate lets it through) and open-mode membership, so the
    prerequisite gate is the only thing standing in the way.
    """
    root = tmp_path / "repo"
    root.mkdir(parents=True, exist_ok=True)
    _git(["init", "-q"], root)
    _git(["remote", "add", "origin", "git@github.com:acme/widget.git"], root)
    cap = root / ".pkit" / "capabilities" / "project-management"
    shutil.copytree(CAP_SRC / "schemas", cap / "schemas")
    shutil.copytree(CAP_SRC / "templates", cap / "templates")
    shutil.copy(CAP_SRC / "package.yaml", cap / "package.yaml")
    (cap / "project").mkdir(parents=True)
    (cap / "project" / "config.yaml").write_text(config, encoding="utf-8")
    return cap


def _bootstrap(cap: Path, *, repo: str | None = "github.com/acme/widget") -> Path:
    """Write the stamp `bootstrap` would write on a clean completion."""
    stamp = cap / "project" / "bootstrap-stamp.yaml"
    stamp.write_text(
        "schema_version: 1\n"
        "bootstrap:\n"
        "  completed_at: '2026-01-01T00:00:00+00:00'\n"
        "  capability_version: 0.53.0\n"
        "  by: bootstrap\n"
        f"  repo: {repo if repo else ''}\n",
        encoding="utf-8",
    )
    return stamp


def _run(
    script: str, args: list[str], *, cap: Path, pass_root: bool = True
) -> subprocess.CompletedProcess:
    """Launch a pm script directly, the way an agent or a CI job does.

    `pass_root=False` is for the engine-called predicates, which expose no
    `--capability-root` flag: the engine runs them with the repo root as cwd and
    they discover the capability by walking up from there — which is exactly the
    discovery path the gate uses when no root is handed to it.
    """
    repo_root = cap.parent.parent.parent
    env = dict(os.environ)
    # Mark autonomy so nothing waits on a prompt, and anchor the session to this
    # repo so the (unrelated) foreign-repo guard stays silent.
    env["PM_INVOKER_LOGIN"] = "ci-bot"
    env["CLAUDE_PROJECT_DIR"] = str(repo_root)
    root_args = ["--capability-root", str(cap)] if pass_root else []
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args, *root_args],
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


# --- the three families, refused on an un-bootstrapped project -----------


def test_mutator_refuses_before_doing_anything(tmp_path: Path) -> None:
    """`create-issue --dry-run` on an un-bootstrapped project refuses BEFORE it
    composes a plan — so nothing is written and nothing is reported."""
    cap = _project(tmp_path)
    proc = _run(
        "create-issue.py",
        ["--type", "task", "--title", "x", "--workstream", "ws", "--parent", "1",
         "--dry-run"],
        cap=cap,
    )
    assert proc.returncode == 2, proc.stderr
    assert REFUSAL_MARKER in proc.stderr
    assert "create-issue" in proc.stderr
    assert "[dry-run]" not in proc.stdout


def test_read_verb_refuses(tmp_path: Path) -> None:
    """A read is gated too: `show-issue` would render classification lines off
    the kit's assumed labels, misreporting an adopter who remapped them."""
    cap = _project(tmp_path)
    proc = _run("show-issue.py", ["1"], cap=cap)
    assert proc.returncode == 2, proc.stderr
    assert REFUSAL_MARKER in proc.stderr
    assert "show-issue" in proc.stderr


def test_engine_called_predicate_refuses_with_no_json_on_stdout(tmp_path: Path) -> None:
    """A predicate refuses with a non-zero exit and an EMPTY stdout.

    Both halves matter: the engine reads a non-zero exit as indeterminate and
    fails closed (the correct answer — an un-bootstrapped project genuinely
    cannot say where an issue stands), and an empty stdout means it cannot
    mistake a refusal for a `result: false` verdict.
    """
    cap = _project(tmp_path)
    proc = _run("detect-todo.py", ["42", "--json"], cap=cap, pass_root=False)
    assert proc.returncode != 0
    assert proc.stdout.strip() == ""
    assert REFUSAL_MARKER in proc.stderr


def test_the_refusal_names_the_command_that_fixes_it(tmp_path: Path) -> None:
    """The hint is the point: a self-remedying failure, not a puzzle."""
    cap = _project(tmp_path)
    err = _run("move-issue.py", ["1", "--to", "backlog", "--yes"], cap=cap).stderr
    assert "pkit project-management bootstrap" in err
    assert "scripts/bootstrap.py" in err
    assert "pkit project-management pre-check" in err


# --- the exempt verbs still work on the same tree ------------------------


@pytest.mark.parametrize(
    ("verb", "args"),
    [
        ("pre-check", []),
        ("bootstrap", ["--dry-run"]),
        ("migrate", ["--dry-run", "--skip-pre-check"]),
        ("adopt-existing", ["--json"]),
        ("self-test", ["--dry-run"]),
    ],
)
def test_exempt_verbs_are_usable_un_bootstrapped(
    tmp_path: Path, verb: str, args: list[str]
) -> None:
    """Each of the five runs its own logic on an un-bootstrapped project.

    They may well fail for their own reasons in a sandbox with no reachable
    tracker — what must never appear is the prerequisite refusal: these are the
    verbs you use TO become bootstrapped, or to find out why you are not.
    """
    cap = _project(tmp_path)
    proc = _run(f"{verb}.py", args, cap=cap)
    combined = proc.stdout + proc.stderr
    assert REFUSAL_MARKER not in combined, combined


# --- a bootstrapped project is unaffected --------------------------------


def test_bootstrapped_project_is_unaffected(tmp_path: Path) -> None:
    """The whole point of the stamp: with it present the gate is silent and the
    script proceeds exactly as before (here, to its dry-run plan)."""
    cap = _project(tmp_path)
    _bootstrap(cap)
    proc = _run(
        "create-issue.py",
        ["--type", "task", "--title", "x", "--workstream", "ws", "--parent", "1",
         "--dry-run"],
        cap=cap,
    )
    assert REFUSAL_MARKER not in proc.stderr, proc.stderr
    assert proc.returncode == 0, proc.stderr
    assert "[dry-run]" in proc.stdout


def test_a_stamped_but_shape_invalid_config_is_refused(tmp_path: Path) -> None:
    """A config can break AFTER a successful bootstrap, so the stamp alone is
    not enough. Here the misspelling the config schema was built for
    (`has_projects_v2_boards`, trailing `s`) — silently ignored by every reader,
    which used to leave the adopter in label-fallback mode with no signal."""
    cap = _project(
        tmp_path, config=VALID_CONFIG + "has_projects_v2_boards: true\n"
    )
    _bootstrap(cap)
    proc = _run("show-issue.py", ["1"], cap=cap)
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "has_projects_v2_boards" in proc.stderr


def test_a_stamp_carried_in_from_another_repo_is_refused(tmp_path: Path) -> None:
    """The seeded/copied-stamp case, end to end: the capability's `project/`
    subtree is seeded from source on a fresh install and can be copied between
    repos, so a stamp naming a different repository must not open the gate."""
    cap = _project(tmp_path)
    _bootstrap(cap, repo="github.com/someone-else/other")
    proc = _run("show-issue.py", ["1"], cap=cap)
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "written for a different repository" in proc.stderr


def test_help_still_answers_on_a_delegating_entry_point(tmp_path: Path) -> None:
    """`check-criterion` hands its whole argument parsing to a shared runner, so
    its gate call necessarily precedes argparse. `--help` must still answer
    there — printing usage performs no operation."""
    cap = _project(tmp_path)
    proc = _run("check-criterion.py", ["--help"], cap=cap)
    assert REFUSAL_MARKER not in proc.stderr, proc.stderr
    assert "usage" in proc.stdout.lower()
