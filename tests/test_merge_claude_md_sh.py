"""Tests for the claude-code adapter's `merge-claude-md.sh` primitive.

The script keeps the rules every session loads included in the adopter's root
CLAUDE.md (issue #96; ADR-076 points 2 and 3): core's `@.pkit/rules/core.md`, the
capabilities' rules index `@.pkit/rules/capabilities.md` directly after it, and the
project's `@.pkit/rules/project.md`. The scenarios:

1. CLAUDE.md absent → created with the three @-includes, in their layers' order.
2. CLAUDE.md exists, no core include → the three inserted after the first H1.
3. CLAUDE.md exists, no H1 → the three prepended with a minimal header.
4. CLAUDE.md holds both core's include and the index's line → no-op (idempotent).
5. CLAUDE.md holds core's include only → the index's line inserted after it, and
   the project's line never put back on its own.
6. Each existing state: a linked CLAUDE.md, core's include only in a fence, a
   CRLF file, a file's mode, a project that keeps its include in `AGENTS.md`.
7. "Holds the line": the shell's test against the table both tests share
   (`tests/host_line_cases.py`), and its copy of the line against the adapter's key.
"""

from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

import pytest
from ruamel.yaml import YAML

from project_kit import loaded_rules
from tests.host_line_cases import CASES

REPO_ROOT = Path(__file__).resolve().parent.parent
ADAPTER_DIR = REPO_ROOT / ".pkit" / "adapters" / "claude-code"
ADAPTER_SCRIPT = ADAPTER_DIR / "merge-claude-md.sh"

CORE = "@.pkit/rules/core.md"
INDEX = "@.pkit/rules/capabilities.md"
PROJECT = "@.pkit/rules/project.md"


@pytest.fixture
def adapter_tree(tmp_path: Path) -> Path:
    """A tmp tree mirroring the kit-installed claude-code adapter layout.

    The script resolves ROOT from its own location (three dirs up from the
    script), so placing it under `tmp_path/.pkit/adapters/claude-code/`
    gives ROOT == tmp_path — exactly what a real adopter tree looks like.
    """
    adapter_dir = tmp_path / ".pkit" / "adapters" / "claude-code"
    adapter_dir.mkdir(parents=True)
    shutil.copy(ADAPTER_SCRIPT, adapter_dir / "merge-claude-md.sh")
    return tmp_path


def _run_script(adapter_tree: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(adapter_tree / ".pkit" / "adapters" / "claude-code" / "merge-claude-md.sh")],
        capture_output=True,
        text=True,
        check=False,
    )


def _claude_md(adapter_tree: Path) -> Path:
    return adapter_tree / "CLAUDE.md"


def _lines(adapter_tree: Path) -> list[str]:
    return _claude_md(adapter_tree).read_text(encoding="utf-8").splitlines()


# ── Scenario 1: CLAUDE.md absent → created ────────────────────────────────


def test_creates_claude_md_with_the_three_includes_in_their_layers_order(
    adapter_tree: Path,
) -> None:
    """The minimal host holds core's include, the index's line and the project's, in
    that order (ADR-076 point 3)."""
    assert not _claude_md(adapter_tree).exists()

    result = _run_script(adapter_tree)

    assert result.returncode == 0, result.stderr
    includes = [line for line in _lines(adapter_tree) if line.startswith("@")]
    assert includes == [CORE, INDEX, PROJECT]


def test_created_claude_md_has_h1(adapter_tree: Path) -> None:
    """The created CLAUDE.md must have an H1 (per core.md rule 13)."""
    _run_script(adapter_tree)
    assert any(line.startswith("# ") for line in _lines(adapter_tree)), (
        "created CLAUDE.md has no H1; violates the @-include authoring convention (rule 13)"
    )


def test_created_claude_md_include_after_h1(adapter_tree: Path) -> None:
    """The @-include must not be on line 1; it must come after the H1 (rule 13)."""
    _run_script(adapter_tree)
    lines = _lines(adapter_tree)
    include_idx = lines.index(CORE)
    h1_idx = next(i for i, line in enumerate(lines) if line.startswith("# "))
    assert include_idx > h1_idx


# ── Scenario 2: CLAUDE.md exists with H1, no core include → inserted ──────


def test_inserts_the_three_after_h1_when_core_s_include_is_absent(adapter_tree: Path) -> None:
    _claude_md(adapter_tree).write_text(
        "# My Project Instructions\n\nSome existing content.\n", encoding="utf-8"
    )

    result = _run_script(adapter_tree)

    assert result.returncode == 0, result.stderr
    assert _claude_md(adapter_tree).read_text(encoding="utf-8") == (
        f"# My Project Instructions\n\n{CORE}\n{INDEX}\n{PROJECT}\n\nSome existing content.\n"
    )


def test_an_h1_inside_fenced_code_is_not_the_host_s(adapter_tree: Path) -> None:
    """The block goes after the first H1 outside fenced code."""
    _claude_md(adapter_tree).write_text(
        "```\n# not a heading\n```\n\n# Real\n\nProse.\n", encoding="utf-8"
    )
    _run_script(adapter_tree)
    lines = _lines(adapter_tree)
    assert lines.index(CORE) == lines.index("# Real") + 2


def test_adopter_content_preserved_after_insert(adapter_tree: Path) -> None:
    """Inserting the @-includes must not destroy any adopter prose."""
    original = (
        "# Claude Code instructions — my-project\n\n"
        "Custom session instructions here.\n\n"
        "## Workflow\n\nDo things.\n"
    )
    _claude_md(adapter_tree).write_text(original, encoding="utf-8")

    _run_script(adapter_tree)

    content = _lines(adapter_tree)
    for line in original.splitlines():
        assert line in content, f"adopter line {line!r} was lost after @-include insertion"


# ── Scenario 3: CLAUDE.md exists, no H1 → prepend ────────────────────────


def test_prepends_when_no_h1_in_existing_file(adapter_tree: Path) -> None:
    existing = "Some instructions without a heading.\n\nMore content.\n"
    _claude_md(adapter_tree).write_text(existing, encoding="utf-8")

    result = _run_script(adapter_tree)

    assert result.returncode == 0, result.stderr
    content = _claude_md(adapter_tree).read_text(encoding="utf-8")
    assert content.startswith(f"# Claude Code instructions\n\n{CORE}\n{INDEX}\n{PROJECT}\n\n")
    assert content.endswith(existing)


# ── Scenario 4: both already present → no-op ─────────────────────────────


def test_idempotent_when_both_lines_are_present(adapter_tree: Path) -> None:
    original = (
        f"# Claude Code instructions\n\n{CORE}\n{INDEX}\n{PROJECT}\n\nProject-specific content.\n"
    )
    _claude_md(adapter_tree).write_text(original, encoding="utf-8")

    result = _run_script(adapter_tree)

    assert result.returncode == 0, result.stderr
    assert "exists" in result.stdout
    assert _claude_md(adapter_tree).read_text(encoding="utf-8") == original


def test_a_second_run_changes_nothing(adapter_tree: Path) -> None:
    _claude_md(adapter_tree).write_text("# Mine\n\nProse.\n", encoding="utf-8")
    _run_script(adapter_tree)
    once = _claude_md(adapter_tree).read_text(encoding="utf-8")
    _run_script(adapter_tree)
    assert _claude_md(adapter_tree).read_text(encoding="utf-8") == once
    assert once.count(CORE) == once.count(INDEX) == once.count(PROJECT) == 1


# ── Scenario 5: core's include alone → the index's line after it ─────────


def test_inserts_the_index_s_line_directly_after_core_s_include(adapter_tree: Path) -> None:
    _claude_md(adapter_tree).write_text(
        f"# Mine\n\nIntro.\n\n{CORE}\n{PROJECT}\n\nMore.\n", encoding="utf-8"
    )

    result = _run_script(adapter_tree)

    assert result.returncode == 0, result.stderr
    assert "insert" in result.stdout
    assert _claude_md(adapter_tree).read_text(encoding="utf-8") == (
        f"# Mine\n\nIntro.\n\n{CORE}\n{INDEX}\n{PROJECT}\n\nMore.\n"
    )


def test_the_project_s_line_is_never_put_back_on_its_own(adapter_tree: Path) -> None:
    """A project that removed its `project.md` include does not find it back: it is
    inserted only together with core's (ADR-076 point 3)."""
    _claude_md(adapter_tree).write_text(f"# Mine\n\n{CORE}\n", encoding="utf-8")
    _run_script(adapter_tree)
    content = _claude_md(adapter_tree).read_text(encoding="utf-8")
    assert content == f"# Mine\n\n{CORE}\n{INDEX}\n"
    assert PROJECT not in content


def test_an_indented_core_include_still_holds(adapter_tree: Path) -> None:
    _claude_md(adapter_tree).write_text(f"# Mine\n\n  {CORE}  \n", encoding="utf-8")
    _run_script(adapter_tree)
    assert _lines(adapter_tree) == ["# Mine", "", f"  {CORE}  ", INDEX]


# ── Scenario 6: each existing state of the file ───────────────────────────


def test_a_linked_claude_md_keeps_its_link_and_the_line_reaches_its_target(
    adapter_tree: Path,
) -> None:
    target = adapter_tree / "docs" / "INSTRUCTIONS.md"
    target.parent.mkdir()
    target.write_text(f"# Shared\n\n{CORE}\n", encoding="utf-8")
    _claude_md(adapter_tree).symlink_to(Path("docs") / "INSTRUCTIONS.md")

    result = _run_script(adapter_tree)

    assert result.returncode == 0, result.stderr
    assert _claude_md(adapter_tree).is_symlink()
    assert os.readlink(_claude_md(adapter_tree)) == str(Path("docs") / "INSTRUCTIONS.md")
    assert target.read_text(encoding="utf-8") == f"# Shared\n\n{CORE}\n{INDEX}\n"


def test_a_linked_claude_md_without_core_s_include_keeps_its_link(adapter_tree: Path) -> None:
    target = adapter_tree / "AGENTS.md"
    target.write_text("# Agents\n\nProse.\n", encoding="utf-8")
    _claude_md(adapter_tree).symlink_to("AGENTS.md")

    _run_script(adapter_tree)

    assert _claude_md(adapter_tree).is_symlink()
    assert target.read_text(encoding="utf-8") == (
        f"# Agents\n\n{CORE}\n{INDEX}\n{PROJECT}\n\nProse.\n"
    )


def test_the_file_s_mode_stays(adapter_tree: Path) -> None:
    path = _claude_md(adapter_tree)
    path.write_text(f"# Mine\n\n{CORE}\n", encoding="utf-8")
    path.chmod(0o640)
    _run_script(adapter_tree)
    assert stat.S_IMODE(path.stat().st_mode) == 0o640
    path.write_text("# Mine\n\nNo include.\n", encoding="utf-8")
    _run_script(adapter_tree)
    assert stat.S_IMODE(path.stat().st_mode) == 0o640


@pytest.mark.parametrize(
    "written",
    [
        f"# Mine\n\n```\n{CORE}\n```\n",
        f"# Mine\n\n~~~\n{CORE}\n~~~\n",
        f"# Mine\n\nThe rules are `{CORE}`.\n",
    ],
    ids=["backtick fence", "tilde fence", "code span"],
)
def test_core_s_include_only_in_code_is_refused_and_reported(
    adapter_tree: Path, written: str
) -> None:
    """Claude Code imports nothing inside code, so the primitive inserts nothing and
    names the file: the project's own edit mends it (ADR-076 point 3)."""
    _claude_md(adapter_tree).write_text(written, encoding="utf-8")

    result = _run_script(adapter_tree)

    assert result.returncode == 0, result.stderr
    assert "refused" in result.stdout and "CLAUDE.md" in result.stdout
    assert _claude_md(adapter_tree).read_text(encoding="utf-8") == written


def test_core_s_include_in_code_and_in_prose_is_not_refused(adapter_tree: Path) -> None:
    """A mention outside code that holds no line is no refusal: the block is inserted."""
    _claude_md(adapter_tree).write_text(
        f"# Mine\n\nSee {CORE} and `{CORE}`.\n", encoding="utf-8"
    )
    result = _run_script(adapter_tree)
    assert "refused" not in result.stdout
    assert INDEX in _lines(adapter_tree)


def test_a_crlf_file_gets_crlf_lines(adapter_tree: Path) -> None:
    path = _claude_md(adapter_tree)
    path.write_bytes(f"# Mine\r\n\r\n{CORE}\r\nProse.\r\n".encode())
    _run_script(adapter_tree)
    assert path.read_bytes() == f"# Mine\r\n\r\n{CORE}\r\n{INDEX}\r\nProse.\r\n".encode()
    path.write_bytes(b"# Mine\r\n\r\nProse.\r\n")
    _run_script(adapter_tree)
    assert path.read_bytes() == (
        f"# Mine\r\n\r\n{CORE}\r\n{INDEX}\r\n{PROJECT}\r\n\r\nProse.\r\n".encode()
    )


def test_a_project_with_agents_md_alone_gets_a_claude_md(adapter_tree: Path) -> None:
    """The primitive reads CLAUDE.md alone (ADR-076 point 3): a repository holding only
    `AGENTS.md` gets a CLAUDE.md created, and `AGENTS.md` is left as it is."""
    agents = adapter_tree / "AGENTS.md"
    agents.write_text(f"# Agents\n\n{CORE}\n", encoding="utf-8")

    _run_script(adapter_tree)

    assert agents.read_text(encoding="utf-8") == f"# Agents\n\n{CORE}\n"
    assert [line for line in _lines(adapter_tree) if line.startswith("@")] == [
        CORE,
        INDEX,
        PROJECT,
    ]


def test_an_include_moved_into_an_imported_file_is_added_to_claude_md_too(
    adapter_tree: Path,
) -> None:
    (adapter_tree / "AGENTS.md").write_text(f"# Agents\n\n{CORE}\n", encoding="utf-8")
    _claude_md(adapter_tree).write_text("# Mine\n\n@AGENTS.md\n", encoding="utf-8")
    _run_script(adapter_tree)
    assert _lines(adapter_tree) == ["# Mine", "", CORE, INDEX, PROJECT, "", "@AGENTS.md"]


# ── Scenario 7: "holds the line", the table both tests share ──────────────


@pytest.mark.parametrize(("name", "text", "held"), CASES, ids=[case[0] for case in CASES])
def test_the_shell_s_test_of_the_line_follows_the_shared_cases(
    adapter_tree: Path, name: str, text: str, held: bool
) -> None:
    """After a held core include, the primitive inserts the index's line exactly where
    the shared table says the text does not hold it."""
    head = f"# Host\n\n{CORE}\n"
    _claude_md(adapter_tree).write_bytes((head + text).encode("utf-8"))

    result = _run_script(adapter_tree)

    assert result.returncode == 0, result.stderr
    written = _claude_md(adapter_tree).read_bytes().decode("utf-8")
    if held:
        assert written == head + text, name
    else:
        assert written == f"{head}{INDEX}\n{text}", name


@pytest.mark.parametrize(("name", "text", "held"), CASES, ids=[case[0] for case in CASES])
def test_the_backbone_s_test_of_the_line_follows_the_shared_cases(
    name: str, text: str, held: bool
) -> None:
    assert loaded_rules.holds_line(f"# Host\n\n{CORE}\n{text}", INDEX) is held, name


def test_the_shell_s_copy_of_the_line_is_the_key_s_rendered_line() -> None:
    """The primitive is given no `pkit` to ask (ADR-065 point 14), so it keeps the line
    itself; it must be the line the adapter's `loaded_rules:` renders (ADR-076 point 3)."""
    script = ADAPTER_SCRIPT.read_text(encoding="utf-8")
    (copied,) = re.findall(r'^INDEX_INCLUDE="([^"]+)"$', script, re.MULTILINE)
    (core,) = re.findall(r'^CORE_INCLUDE="([^"]+)"$', script, re.MULTILINE)
    package = YAML(typ="safe").load((ADAPTER_DIR / "package.yaml").read_text(encoding="utf-8"))
    form = loaded_rules.read_delivery_form("claude-code", package)
    assert form is not None
    assert copied == form.rendered_line
    assert core == form.core_line
    heredoc = script.split("<<'HEREDOC'", 1)[1].split("HEREDOC", 1)[0]
    assert [line for line in heredoc.splitlines() if line.startswith("@")] == [
        core,
        copied,
        PROJECT,
    ]
