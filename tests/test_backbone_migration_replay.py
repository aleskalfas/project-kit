"""Every backbone migration replayed over the states a project may hold (#1459).

A project with no recorded completion has an unknown backbone migration history,
so its first upgrade runs every backbone migration up to its target once
(ADR-065 point 5). That leans on COR-010's contract for a backbone migration: it
acts only on a positive sign that its change is needed, and never deletes by a
path's name or position alone. Each fixture holds one failure a replay risks
("Projects already stranded", #1429's design), beside a fresh install:

- what a replay must leave alone: a hand-written `.claude/agents/orchestrator.md`,
  a `bindings.yaml` under a capability's `project/` and one in an incubated
  capability, a project's own file under `.pkit/workflow/project/`;
- what a replay may restore, the cost the release's notes state: an overlay
  category deleted after `1.54.0/001` ran, the `process` block removed while old
  journals stay on disk, a declared file forced back into git.

Every shipped script runs, the `1.150.0/` ones included, which the release that
ships them replays. Each runs as the upgrade runs it: bash, `ROOT` set, the
project root as the working directory, and here no terminal.
"""

from __future__ import annotations

import os
import pty
import subprocess
from pathlib import Path

import pytest

from project_kit.migrations import pending_migration_scripts
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo

REPO_ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS_ROOT = REPO_ROOT / ".pkit" / "migrations" / "backbone"
RETIRE_BUNDLES = MIGRATIONS_ROOT / "1.32.0" / "001-retire-bundle-pattern-and-workflow-area.sh"
RETIRE_AGENTS = MIGRATIONS_ROOT / "1.31.0" / "001-retire-pm-core-agents.sh"
BINDINGS = MIGRATIONS_ROOT / "1.0.0" / "001-remove-bindings-meta-schema.sh"


@pytest.fixture
def adopter(make_adopter_repo: MakeAdopterRepo) -> AdopterRepo:
    """A fresh install whose files are all in the index, as a committed project's are."""
    repo = make_adopter_repo()
    repo.git("add", "-A")
    return repo


def _every_script() -> list[Path]:
    """Every backbone migration the methodology ships, in the order a replay runs them."""
    scripts = pending_migration_scripts(MIGRATIONS_ROOT, None, "999.0.0")
    assert scripts, "the backbone ships migrations"
    return scripts


def _run(script: Path, root: Path, home: Path) -> subprocess.CompletedProcess[str]:
    """Run one script as the upgrade runner does, with no terminal to answer."""
    return subprocess.run(
        ["bash", str(script)],
        env={**os.environ, "ROOT": str(root), "HOME": str(home)},
        cwd=root,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )


def _replay(root: Path, home: Path) -> str:
    """Run every backbone migration once over *root*; each must succeed."""
    output: list[str] = []
    for script in _every_script():
        result = _run(script, root, home)
        assert result.returncode == 0, f"{script.name}: {result.stdout}{result.stderr}"
        output.append(result.stdout + result.stderr)
    return "".join(output)


def _tree(root: Path) -> dict[str, bytes | str | None]:
    """Every path under *root* outside `.git/`: a file's bytes, a link's target,
    None for a directory."""
    tree: dict[str, bytes | str | None] = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if rel.parts[0] == ".git":
            continue
        if path.is_symlink():
            tree[rel.as_posix()] = os.readlink(path)
        elif path.is_file():
            tree[rel.as_posix()] = path.read_bytes()
        else:
            tree[rel.as_posix()] = None
    return tree


def _index(repo: AdopterRepo) -> str:
    return repo.git("ls-files", "--stage").stdout


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# --- a fresh install ----------------------------------------------------------------


def test_a_replay_over_a_fresh_install_changes_nothing(
    adopter: AdopterRepo, tmp_path: Path
) -> None:
    before, index = _tree(adopter.root), _index(adopter)

    _replay(adopter.root, tmp_path)

    assert _tree(adopter.root) == before
    assert _index(adopter) == index


# --- what a replay leaves alone ------------------------------------------------------


def test_a_hand_written_agent_of_a_retired_name_survives(
    adopter: AdopterRepo, tmp_path: Path
) -> None:
    """`1.31.0/001` deleted anything at `.claude/agents/orchestrator.md`. It now acts
    only on a link to the retired core agent that no longer resolves."""
    own = _write(adopter.root, ".claude/agents/orchestrator.md", "---\nname: orchestrator\n---\n")
    _write(adopter.root, ".pkit/agents/project/product-manager.md", "---\nname: pm\n---\n")
    link = adopter.root / ".claude" / "agents" / "product-manager.md"
    link.symlink_to("../../.pkit/agents/project/product-manager.md")

    _replay(adopter.root, tmp_path)

    assert own.read_text(encoding="utf-8") == "---\nname: orchestrator\n---\n"
    assert link.is_symlink() and link.resolve().is_file()


def test_a_stale_link_to_the_retired_core_agent_is_removed(
    adopter: AdopterRepo, tmp_path: Path
) -> None:
    link = adopter.root / ".claude" / "agents" / "orchestrator.md"
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to("../../.pkit/agents/core/orchestrator.md")  # gone since COR-026

    result = _run(RETIRE_AGENTS, adopter.root, tmp_path)

    assert result.returncode == 0, result.stderr
    assert not link.is_symlink()
    assert "stale link to the retired core agent" in result.stdout


def test_a_projects_bindings_files_survive_and_are_named(
    adopter: AdopterRepo, tmp_path: Path
) -> None:
    """`1.0.0/001` deleted every `schemas/bindings.yaml` four levels below
    `.pkit/capabilities/`, which reached a capability's `project/` and an incubated
    capability. It now removes nothing, and names each such file."""
    under_project = _write(
        adopter.root,
        ".pkit/capabilities/project-management/project/schemas/bindings.yaml",
        "bindings: []\n",
    )
    incubated = _write(
        adopter.root, ".pkit/capabilities/homegrown/data/schemas/bindings.yaml", "bindings: []\n"
    )

    out = _replay(adopter.root, tmp_path)

    assert under_project.read_text(encoding="utf-8") == "bindings: []\n"
    assert incubated.read_text(encoding="utf-8") == "bindings: []\n"
    assert ".pkit/capabilities/homegrown/data/schemas/bindings.yaml is unused" in out
    assert "project-management/project/schemas/bindings.yaml is unused" in out


def test_a_projects_own_file_under_the_retired_workflow_area_survives(
    adopter: AdopterRepo, tmp_path: Path
) -> None:
    """`1.32.0/001` removed every folder under `.pkit/workflow/project/` by position.
    With no record of a bundle, nothing there is the retired bundle's."""
    notes = _write(adopter.root, ".pkit/workflow/project/notes.md", "ours\n")
    folder = _write(adopter.root, ".pkit/workflow/project/github-issues/config.yaml", "ours\n")
    before = _tree(adopter.root)

    _replay(adopter.root, tmp_path)

    assert notes.is_file() and folder.is_file()
    assert _tree(adopter.root) == before


# --- the retired bundle, recorded --------------------------------------------------


_BUNDLE_ENTRY = (
    "  - kind: bundle\n"
    "    name: github-issues\n"
    "    manifest: .pkit/manifests/components/github-issues.yaml\n"
)


def _record_the_bundle(root: Path) -> tuple[Path, str]:
    """What `pkit bundle install github-issues` left: its registry entry with another
    entry after it, its component manifest and its project-side folder. Returns the
    manifest and the text it should hold once the entry is dropped."""
    manifest = root / ".pkit" / "manifest.yaml"
    text = manifest.read_text(encoding="utf-8")
    without = text
    with_bundle = text.replace("components:\n", "components:\n" + _BUNDLE_ENTRY, 1)
    assert with_bundle != text, "the fresh manifest has a components registry"
    manifest.write_text(with_bundle, encoding="utf-8")
    _write(
        root,
        ".pkit/manifests/components/github-issues.yaml",
        "schema_version: 1\ncomponent:\n  kind: bundle\n  name: github-issues\n",
    )
    _write(root, ".pkit/manifests/components/kept.yaml", "component:\n  kind: other\n")
    _write(root, ".pkit/workflow/project/github-issues/config.yaml", "project: board\n")
    return manifest, without


def test_the_bundle_entry_is_dropped_whole_and_the_entry_after_it_stays(
    adopter: AdopterRepo, tmp_path: Path
) -> None:
    """The old filter dropped four lines for a three-line entry, so the entry after
    it lost its first line. The rewrite drops the entry's own lines only. With no
    terminal it asks nothing, and keeps the project's folder."""
    manifest, expected = _record_the_bundle(adopter.root)

    result = _run(RETIRE_BUNDLES, adopter.root, tmp_path)

    assert result.returncode == 0, result.stderr
    assert manifest.read_text(encoding="utf-8") == expected
    assert not (adopter.root / ".pkit/manifests/components/github-issues.yaml").exists()
    assert (adopter.root / ".pkit/manifests/components/kept.yaml").is_file()
    assert (adopter.root / ".pkit/workflow/project/github-issues/config.yaml").is_file()
    assert "nobody here to ask" in result.stdout
    assert "rm -rf .pkit/workflow/project/github-issues/" in result.stdout


def _run_at_a_terminal(script: Path, root: Path, answer: str) -> tuple[int, str]:
    """Run *script* with a terminal on its standard input and output, answering its
    question with *answer*."""
    pid, fd = pty.fork()
    if pid == 0:  # the child: become the migration
        os.chdir(root)
        os.execvpe("bash", ["bash", str(script)], {**os.environ, "ROOT": str(root)})
    os.write(fd, f"{answer}\n".encode())
    chunks: list[bytes] = []
    while True:
        try:
            data = os.read(fd, 4096)
        except OSError:  # the child closed the terminal
            break
        if not data:
            break
        chunks.append(data)
    _, status = os.waitpid(pid, 0)
    os.close(fd)
    return os.waitstatus_to_exitcode(status), b"".join(chunks).decode("utf-8", "replace")


@pytest.mark.parametrize(("answer", "removed"), [("y", True), ("n", False)])
def test_the_bundles_folder_goes_only_on_a_yes_at_a_terminal(
    adopter: AdopterRepo, answer: str, removed: bool
) -> None:
    """COR-027's Migration: the project-side folder is removed, and the migration
    asks first."""
    _record_the_bundle(adopter.root)
    _write(adopter.root, ".pkit/workflow/project/notes.md", "ours\n")

    code, output = _run_at_a_terminal(RETIRE_BUNDLES, adopter.root, answer)

    assert code == 0, output
    assert "Remove .pkit/workflow/project/github-issues/" in output
    folder = adopter.root / ".pkit/workflow/project/github-issues"
    assert folder.exists() is not removed
    assert (adopter.root / ".pkit/workflow/project/notes.md").is_file()


# --- what a replay may restore, as the release's notes say --------------------------


def test_an_overlay_category_deleted_after_1_54_0_comes_back(
    adopter: AdopterRepo, tmp_path: Path
) -> None:
    overlay = adopter.root / ".pkit" / "agents" / "project" / "overlay.yaml"
    lines = overlay.read_text(encoding="utf-8").splitlines(keepends=True)
    start = next(i for i, line in enumerate(lines) if line.startswith("architecture-docs:"))
    end = start + 1
    while end < len(lines) and lines[end].startswith(("  ", "-")):
        end += 1
    overlay.write_text("".join(lines[:start] + lines[end:]), encoding="utf-8")

    _replay(adopter.root, tmp_path)

    assert "\narchitecture-docs:\n" in overlay.read_text(encoding="utf-8")


def test_journal_logging_comes_back_where_the_process_block_was_removed(
    adopter: AdopterRepo, tmp_path: Path
) -> None:
    _write(adopter.root, ".pkit/capabilities/kept/project/process/subject.journal.jsonl", "{}\n")
    config = adopter.root / ".pkit" / "project" / "config.yaml"
    if config.is_file():
        assert "process:" not in config.read_text(encoding="utf-8")

    _replay(adopter.root, tmp_path)

    assert "    enabled: true" in config.read_text(encoding="utf-8")


def test_a_declared_file_forced_back_into_git_is_untracked_again(
    adopter: AdopterRepo, tmp_path: Path
) -> None:
    ledger = _write(
        adopter.root, ".pkit/permissions/project/sandbox-provenance.yaml", "entries: []\n"
    )
    adopter.git("add", "-f", "--", ".pkit/permissions/project/sandbox-provenance.yaml")

    _replay(adopter.root, tmp_path)

    tracked = adopter.git("ls-files", "--", ".pkit/permissions/project/").stdout
    assert "sandbox-provenance.yaml" not in tracked
    assert ledger.read_text(encoding="utf-8") == "entries: []\n"


def test_the_bindings_migration_names_no_file_where_there_is_none(
    adopter: AdopterRepo, tmp_path: Path
) -> None:
    result = _run(BINDINGS, adopter.root, tmp_path)
    assert result.returncode == 0
    assert "nothing to report" in result.stdout
