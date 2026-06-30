"""End-to-end: the foreign-repo guard fires inside a real mutating pm script.

Drives the real `create-issue.py` as a subprocess in the incident shape — the
session anchored to repo A (`CLAUDE_PROJECT_DIR=A`) while the cwd is a DIFFERENT
repo B — and proves the guard refuses BEFORE the script reaches its gh
mutation. Complements the in-process `test_pm_session_guard.py` unit tests by
proving the live wiring at the script seam.

`create-issue` is the representative leaf mutator; the guard is the same single
extracted check (`_lib.session_guard.enforce`) wired identically into every
mutating script, so proving it here proves the wiring shape for all of them.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CAP_SRC = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
CREATE_ISSUE = CAP_SRC / "scripts" / "create-issue.py"
PROMOTE_ISSUE = CAP_SRC / "scripts" / "promote-issue.py"
ADD_MEMBER = CAP_SRC / "scripts" / "add-member.py"


def _git_init(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "init", "-q"], cwd=path, check=True, capture_output=True, text=True
    )


def _minimal_capability_tree(anchor: Path) -> Path:
    """A capability tree complete enough for create-issue to run a full --dry-run.

    Copies the real `schemas/` and `templates/` (so the dry-run composes a body
    and validates the title) and uses open-mode membership (no members.yaml) so
    the gate passes and the foreign-repo guard is the next thing the script
    reaches before its (skipped, dry-run) gh mutation."""
    cap = anchor / ".pkit" / "capabilities" / "project-management"
    shutil.copytree(CAP_SRC / "schemas", cap / "schemas")
    shutil.copytree(CAP_SRC / "templates", cap / "templates")
    (cap / "project").mkdir(parents=True)
    (cap / "project" / "config.yaml").write_text("schema_version: 1\n")
    return cap


def _run_create_issue(
    *, cwd: Path, anchor: Path, cap_root: Path, extra: list[str]
) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(anchor)
    # Mark autonomy so the guard refuses (rather than waiting on a prompt) and
    # the subprocess never blocks on stdin.
    env["PM_INVOKER_LOGIN"] = "ci-bot"
    env.pop("PKIT_ALLOW_FOREIGN_REPO", None)
    return subprocess.run(
        [
            sys.executable,
            str(CREATE_ISSUE),
            "--type", "task",
            "--title", "x",
            "--workstream", "ws",
            "--parent", "1",  # task requires a parent-ref; the guard runs before this.
            "--capability-root", str(cap_root),
            "--dry-run",
            *extra,
        ],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_cross_repo_create_issue_refuses_before_mutation(tmp_path):
    """Incident reproduction: anchored to A, cwd in B → create-issue refuses
    with the interlock BEFORE the dry-run plan (no gh, no mutation)."""
    repo_a = tmp_path / "A"
    repo_b = tmp_path / "B"
    _git_init(repo_a)
    _git_init(repo_b)
    cap = _minimal_capability_tree(repo_a)

    proc = _run_create_issue(cwd=repo_b, anchor=repo_a, cap_root=cap, extra=[])

    assert proc.returncode == 1, f"expected guard refusal (1); got {proc.returncode}\n{proc.stderr}"
    assert "cross-repo mutation interlock" in proc.stderr
    # It refused BEFORE reaching the dry-run plan output.
    assert "[dry-run]" not in proc.stdout


def test_same_repo_create_issue_passes_guard(tmp_path):
    """cwd inside the anchor → the guard is silent; the script proceeds to its
    dry-run plan (proving no friction on the ordinary in-tree path)."""
    repo_a = tmp_path / "A"
    _git_init(repo_a)
    cap = _minimal_capability_tree(repo_a)

    proc = _run_create_issue(cwd=repo_a, anchor=repo_a, cap_root=cap, extra=[])

    assert "cross-repo mutation interlock" not in proc.stderr
    # The dry-run reached its plan output → the guard let it through.
    assert proc.returncode == 0, proc.stderr
    assert "[dry-run]" in proc.stdout


def test_cross_repo_override_proceeds(tmp_path):
    """--allow-foreign-repo confirms the cross-repo mutation: the script
    proceeds past the guard to its dry-run plan (operator-gated, not a wall)."""
    repo_a = tmp_path / "A"
    repo_b = tmp_path / "B"
    _git_init(repo_a)
    _git_init(repo_b)
    cap = _minimal_capability_tree(repo_a)

    proc = _run_create_issue(
        cwd=repo_b, anchor=repo_a, cap_root=cap, extra=["--allow-foreign-repo"]
    )

    assert proc.returncode == 0, proc.stderr
    assert "[dry-run]" in proc.stdout
    assert "operator override" in proc.stderr


def test_unset_anchor_does_not_falsely_block(tmp_path):
    """Residual gap honesty: with CLAUDE_PROJECT_DIR UNSET, the guard cannot
    determine the anchor and must NOT block — the script proceeds (the guard
    does not pretend coverage). Reproduces the `unset CLAUDE_PROJECT_DIR`
    declared-out-of-scope case."""
    repo_b = tmp_path / "B"
    _git_init(repo_b)
    cap = _minimal_capability_tree(repo_b)  # cap lives in B; cwd is B.

    env = dict(os.environ)
    env.pop("CLAUDE_PROJECT_DIR", None)  # the unset case.
    env["PM_INVOKER_LOGIN"] = "ci-bot"
    env.pop("PKIT_ALLOW_FOREIGN_REPO", None)
    proc = subprocess.run(
        [
            sys.executable,
            str(CREATE_ISSUE),
            "--type", "task",
            "--title", "x",
            "--workstream", "ws",
            "--parent", "1",
            "--capability-root", str(cap),
            "--dry-run",
        ],
        cwd=str(repo_b),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert "cross-repo mutation interlock" not in proc.stderr
    assert proc.returncode == 0, proc.stderr
    assert "[dry-run]" in proc.stdout


def _minimal_member_capability_tree(anchor: Path) -> Path:
    """A capability tree complete enough for add-member to reach its write.

    Open-mode membership (no members.yaml) so the gate passes and the
    foreign-repo guard is the next thing add-member reaches before it writes
    members.yaml."""
    cap = anchor / ".pkit" / "capabilities" / "project-management"
    (cap / "project").mkdir(parents=True)
    (cap / "project" / "config.yaml").write_text("schema_version: 1\n")
    return cap


def _run_add_member(
    *, cwd: Path, anchor: Path | None, cap_root: Path, extra: list[str]
) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    if anchor is not None:
        env["CLAUDE_PROJECT_DIR"] = str(anchor)
    else:
        env.pop("CLAUDE_PROJECT_DIR", None)
    env["PM_INVOKER_LOGIN"] = "ci-bot"  # autonomy → refuse, never prompt.
    env.pop("PKIT_ALLOW_FOREIGN_REPO", None)
    return subprocess.run(
        [
            sys.executable,
            str(ADD_MEMBER),
            "--github-login", "someone",
            "--capability-root", str(cap_root),
            "--yes",
            *extra,
        ],
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_cross_repo_local_file_mutator_refuses_before_writing(tmp_path):
    """A LOCAL-FILE mutator in the incident shape (anchor A, cwd B, no override)
    refuses BEFORE writing members.yaml.

    This is the local-file analogue of the create-issue gh case: add-member
    resolves members.yaml from the cwd-walk, so `cd /B && add-member` would land
    the write in B. The guard fires first — and members.yaml is never written."""
    repo_a = tmp_path / "A"
    repo_b = tmp_path / "B"
    _git_init(repo_a)
    _git_init(repo_b)
    cap = _minimal_member_capability_tree(repo_a)
    members_file = cap / "project" / "members.yaml"

    proc = _run_add_member(cwd=repo_b, anchor=repo_a, cap_root=cap, extra=[])

    assert proc.returncode == 1, (
        f"expected guard refusal (1); got {proc.returncode}\n{proc.stderr}"
    )
    assert "cross-repo mutation interlock" in proc.stderr
    assert not members_file.exists(), "members.yaml was written despite a DIVERGED refusal"


def test_same_repo_local_file_mutator_writes(tmp_path):
    """cwd inside the anchor → the guard is silent and add-member proceeds to
    write members.yaml (no friction on the ordinary in-tree path)."""
    repo_a = tmp_path / "A"
    _git_init(repo_a)
    cap = _minimal_member_capability_tree(repo_a)
    members_file = cap / "project" / "members.yaml"

    proc = _run_add_member(cwd=repo_a, anchor=repo_a, cap_root=cap, extra=[])

    assert "cross-repo mutation interlock" not in proc.stderr
    assert proc.returncode == 0, proc.stderr
    assert members_file.exists(), "members.yaml was not written on the same-repo path"
    assert "someone" in members_file.read_text()


def test_cross_repo_local_file_mutator_override_writes(tmp_path):
    """--allow-foreign-repo confirms the cross-repo write: add-member proceeds
    and writes members.yaml into the (foreign) cwd-resolved tree."""
    repo_a = tmp_path / "A"
    repo_b = tmp_path / "B"
    _git_init(repo_a)
    _git_init(repo_b)
    cap = _minimal_member_capability_tree(repo_a)
    members_file = cap / "project" / "members.yaml"

    proc = _run_add_member(
        cwd=repo_b, anchor=repo_a, cap_root=cap, extra=["--allow-foreign-repo"]
    )

    assert proc.returncode == 0, proc.stderr
    assert "operator override" in proc.stderr
    assert members_file.exists()


def test_wrapper_diverged_refuses_without_threading_override_to_leaf(tmp_path):
    """Override-not-leaked: a composing wrapper (promote-issue) that is NOT
    overridden + DIVERGED refuses at the guard and never reaches its composed
    `move-issue` leaf — so `--allow-foreign-repo` is never threaded onward.

    promote-issue runs the guard (with override=args.allow_foreign_repo, here
    False) BEFORE `_invoke_move_issue`. We prove the leaf is unreached by a
    spy `move-issue.py`: the wrapper resolves the composed script as a sibling
    of itself (`_HERE / move-issue.py`), so we run a COPY of the scripts tree
    whose move-issue is a sentinel that records its argv. The sentinel never
    fires → the guard refused before composing → no flag leak."""
    repo_a = tmp_path / "A"
    repo_b = tmp_path / "B"
    _git_init(repo_a)
    _git_init(repo_b)
    cap = _minimal_capability_tree(repo_a)

    # A copy of the scripts tree with move-issue replaced by an argv-recording
    # spy. The wrapper composes its sibling move-issue.py, so the copy's spy is
    # what would run if the guard let it through.
    scripts_copy = tmp_path / "scripts"
    shutil.copytree(CAP_SRC / "scripts", scripts_copy)
    marker = tmp_path / "move-issue-was-invoked.txt"
    (scripts_copy / "move-issue.py").write_text(
        "import sys, pathlib\n"
        f"pathlib.Path({str(marker)!r}).write_text(' '.join(sys.argv[1:]))\n"
        "print('SPY-MOVE-ISSUE-RAN')\n"
    )

    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(repo_a)
    env["PM_INVOKER_LOGIN"] = "ci-bot"
    env.pop("PKIT_ALLOW_FOREIGN_REPO", None)
    proc = subprocess.run(
        [
            sys.executable,
            str(scripts_copy / "promote-issue.py"),
            "1",
            "--reason", "test",
            "--capability-root", str(cap),
            "--yes",
        ],
        cwd=str(repo_b),  # cwd is B; anchor is A → DIVERGED.
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert proc.returncode == 1, f"expected guard refusal (1); got {proc.returncode}\n{proc.stderr}"
    assert "cross-repo mutation interlock" in proc.stderr
    # The leaf was never reached: the spy did not run, so no --allow-foreign-repo
    # (nor anything else) was threaded into the composed move-issue.
    assert not marker.exists(), "move-issue leaf was reached despite a DIVERGED refusal"
    assert "SPY-MOVE-ISSUE-RAN" not in proc.stdout
