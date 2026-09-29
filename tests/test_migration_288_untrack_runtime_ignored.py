"""Backbone migration 1.150.0/001-untrack-runtime-ignored-files.sh (#288).

An adopter who committed a runtime-local file before its `runtime_ignore`
declaration shipped keeps it tracked: the rendered `.pkit/.gitignore` ignores it,
but an ignore rule does not untrack. On upgrade the migration removes exactly the
declared files from the index and leaves every working copy as it was.

Each test builds a real repository whose history committed the files, then
renders `.pkit/.gitignore` with the real renderer — what the upgrade's sync step
does before backbone migrations run — and runs the script as the runner does.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from project_kit import visibility
from project_kit.migrations import pending_migration_scripts
from tests.adopter_repo import GitRepo

REPO_ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS_ROOT = REPO_ROOT / ".pkit" / "migrations" / "backbone"
MIGRATION = MIGRATIONS_ROOT / "1.150.0" / "001-untrack-runtime-ignored-files.sh"

# Declared by the backbone's runtime-ignore seam.
LEDGER = ".pkit/permissions/project/sandbox-provenance.yaml"
DIAGNOSE = ".pkit/permissions/project/diagnose.yaml"
PYCACHE = ".pkit/lifecycle/__pycache__/ownership.cpython-313.pyc"
# Declared by no component: legitimately tracked, shared by the team.
SHARED_CONFIG = ".pkit/capabilities/project-management/project/config.yaml"

# Bytes a text round-trip would change: CRLF, a non-UTF-8 byte, no final newline.
LEDGER_BYTES = b"entries:\r\n  - host: build-01\r\n    note: \xff\xfe per-machine"
CONFIG_BYTES = b"default_branch: main\n"


def _adopter(tmp_path: Path, files: dict[str, bytes]) -> GitRepo:
    """A repository that committed `files` before any runtime-ignore declaration
    existed, then upgraded: `.pkit/.gitignore` rendered, not yet committed."""
    repo = GitRepo.init(tmp_path / "adopter")
    for rel, content in files.items():
        path = repo.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    # `-f`: a global excludes file commonly ignores `__pycache__/`.
    repo.git("add", "-f", "--", *files)
    repo.git("commit", "-q", "-m", "commit runtime files before their declaration shipped")
    visibility.render_runtime_ignore(repo.root)
    return repo


def _run(root: Path, **env: str) -> subprocess.CompletedProcess[str]:
    """Run the migration as the upgrade runner does: bash, `ROOT` set, cwd root."""
    return subprocess.run(
        ["bash", str(MIGRATION)],
        env={**os.environ, "ROOT": str(root), **env},
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


def _tracked(repo: GitRepo) -> set[str]:
    return set(repo.git("ls-files", "-z").stdout.split("\0")) - {""}


def _staged(repo: GitRepo) -> list[str]:
    return repo.git("diff", "--cached", "--name-status").stdout.splitlines()


def _index(repo: GitRepo) -> str:
    return repo.git("ls-files", "--stage").stdout


def test_migration_is_registered_for_the_next_backbone_minor() -> None:
    """`pkit upgrade` from 1.149.x runs every script in the 1.150.0 window."""
    assert MIGRATION in pending_migration_scripts(MIGRATIONS_ROOT, "1.149.0", "1.150.0")


def test_tracked_before_declaration_is_untracked_and_working_copy_kept(
    tmp_path: Path,
) -> None:
    repo = _adopter(tmp_path, {LEDGER: LEDGER_BYTES, SHARED_CONFIG: CONFIG_BYTES})

    result = _run(repo.root)

    assert result.returncode == 0, result.stderr
    assert LEDGER not in _tracked(repo)
    assert (repo.root / LEDGER).read_bytes() == LEDGER_BYTES
    # The index change is the ledger's removal and nothing else.
    assert _staged(repo) == [f"D\t{LEDGER}"]
    # The rendered rule now applies: the ledger is ignored, not left untracked.
    assert repo.git("check-ignore", "-q", LEDGER, check=False).returncode == 0
    assert f"untracked  {LEDGER}" in result.stdout


def test_locally_changed_working_copy_is_kept_not_reverted(tmp_path: Path) -> None:
    """The usual per-machine case: this machine's ledger has moved on since the
    commit. The live copy survives as it is, never reset to the committed one."""
    repo = _adopter(tmp_path, {LEDGER: LEDGER_BYTES})
    live = LEDGER_BYTES + b"\r\n  - host: this-machine\r\n"
    (repo.root / LEDGER).write_bytes(live)

    result = _run(repo.root)

    assert result.returncode == 0, result.stderr
    assert LEDGER not in _tracked(repo)
    assert (repo.root / LEDGER).read_bytes() == live


def test_rerun_is_a_noop_and_says_so(tmp_path: Path) -> None:
    repo = _adopter(tmp_path, {LEDGER: LEDGER_BYTES})
    assert _run(repo.root).returncode == 0
    index_after_first = _index(repo)

    result = _run(repo.root)

    assert result.returncode == 0, result.stderr
    assert "nothing to untrack" in result.stdout
    assert _index(repo) == index_after_first
    assert (repo.root / LEDGER).read_bytes() == LEDGER_BYTES


def test_files_no_component_declares_are_never_touched(tmp_path: Path) -> None:
    """Scope is the declaration alone: a shared `config.yaml`, and a file the
    adopter's own `.gitignore` ignores but the adopter chose to track, stay put."""
    adopter_ignored = ".pkit/capabilities/project-management/project/team-notes.yaml"
    repo = _adopter(
        tmp_path,
        {
            LEDGER: LEDGER_BYTES,
            SHARED_CONFIG: CONFIG_BYTES,
            adopter_ignored: b"notes\n",
            ".gitignore": f"{adopter_ignored}\n".encode(),
        },
    )
    before = _index(repo)

    result = _run(repo.root)

    assert result.returncode == 0, result.stderr
    assert _staged(repo) == [f"D\t{LEDGER}"]
    assert {SHARED_CONFIG, adopter_ignored} <= _tracked(repo)
    kept = [line for line in before.splitlines() if not line.endswith(f"\t{LEDGER}")]
    assert _index(repo).splitlines() == kept
    assert (repo.root / SHARED_CONFIG).read_bytes() == CONFIG_BYTES


def test_private_visibility_does_not_hide_declared_files(tmp_path: Path) -> None:
    """Private mode puts all of `.pkit/` in `.git/info/exclude`; the declared
    files are still found, glob declarations (`**/__pycache__/`) included."""
    repo = _adopter(
        tmp_path, {LEDGER: LEDGER_BYTES, PYCACHE: b"\x00bytecode", SHARED_CONFIG: CONFIG_BYTES}
    )
    exclude = repo.root / ".git" / "info" / "exclude"
    exclude.write_text(exclude.read_text(encoding="utf-8") + ".pkit/\n", encoding="utf-8")

    result = _run(repo.root)

    assert result.returncode == 0, result.stderr
    assert sorted(_staged(repo)) == sorted([f"D\t{LEDGER}", f"D\t{PYCACHE}"])
    assert SHARED_CONFIG in _tracked(repo)
    assert (repo.root / PYCACHE).read_bytes() == b"\x00bytecode"


def test_many_files_are_all_untracked_and_the_listing_is_capped(tmp_path: Path) -> None:
    caches = {f".pkit/lifecycle/__pycache__/m{i:02}.pyc": b"\x00" for i in range(25)}
    repo = _adopter(tmp_path, caches)

    result = _run(repo.root)

    assert result.returncode == 0, result.stderr
    assert not set(caches) & _tracked(repo)
    assert result.stdout.count("(index only; working copy untouched)") == 20
    assert "… and 5 more" in result.stdout
    assert "25 untracked, 0 left tracked" in result.stdout


def test_mid_operation_leaves_everything_tracked(tmp_path: Path) -> None:
    repo = _adopter(tmp_path, {LEDGER: LEDGER_BYTES})
    (repo.root / ".git" / "MERGE_HEAD").write_text(repo.head() + "\n", encoding="utf-8")
    before = _index(repo)

    result = _run(repo.root)

    assert result.returncode == 0, result.stderr
    assert _index(repo) == before
    assert "mid-operation" in result.stderr
    assert LEDGER in result.stderr  # the command to finish by hand names it


def test_path_git_refuses_keeps_its_staged_content_and_the_rest_move(
    tmp_path: Path,
) -> None:
    """Staged content matching neither HEAD nor the working copy would be lost
    to a forced removal, so that path stays tracked; the others are untracked."""
    repo = _adopter(tmp_path, {LEDGER: LEDGER_BYTES, DIAGNOSE: b"armed: false\n"})
    (repo.root / DIAGNOSE).write_bytes(b"armed: true\n")
    repo.git("add", "-f", "--", DIAGNOSE)
    (repo.root / DIAGNOSE).write_bytes(b"armed: true\nttl: 60\n")

    result = _run(repo.root)

    assert result.returncode == 0, result.stderr
    assert LEDGER not in _tracked(repo)
    assert DIAGNOSE in _tracked(repo)
    assert repo.git("show", f":{DIAGNOSE}").stdout == "armed: true\n"
    assert (repo.root / DIAGNOSE).read_bytes() == b"armed: true\nttl: 60\n"
    assert "left tracked" in result.stderr and DIAGNOSE in result.stderr


def test_skips_when_no_runtime_ignore_is_rendered(tmp_path: Path) -> None:
    repo = _adopter(tmp_path, {LEDGER: LEDGER_BYTES})
    (repo.root / ".pkit" / ".gitignore").unlink()

    result = _run(repo.root)

    assert result.returncode == 0, result.stderr
    assert "[skip]" in result.stdout
    assert LEDGER in _tracked(repo)


def test_skips_outside_a_git_work_tree(tmp_path: Path) -> None:
    root = tmp_path / "not-a-repo"
    visibility.render_runtime_ignore(root)

    # The ceiling keeps git from discovering a repository above tmp_path.
    result = _run(root, GIT_CEILING_DIRECTORIES=str(tmp_path))

    assert result.returncode == 0, result.stderr
    assert "[skip]" in result.stdout
