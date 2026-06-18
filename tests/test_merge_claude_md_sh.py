"""Tests for the claude-code adapter's `merge-claude-md.sh` primitive.

The script wires `@.pkit/rules/core.md` (and `@.pkit/rules/project.md`)
into the adopter's root CLAUDE.md (issue #96). Four scenarios:

1. CLAUDE.md absent → created with both @-includes.
2. CLAUDE.md exists, no @-include → @-includes inserted after the first H1.
3. CLAUDE.md exists, no H1 → @-includes prepended with a minimal header.
4. CLAUDE.md exists, already has the @-include → no-op (idempotent).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
ADAPTER_SCRIPT = REPO_ROOT / ".pkit" / "adapters" / "claude-code" / "merge-claude-md.sh"


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


def _run_script(adapter_tree: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(adapter_tree / ".pkit" / "adapters" / "claude-code" / "merge-claude-md.sh")],
        capture_output=True,
        text=True,
        check=False,
    )


def _claude_md(adapter_tree: Path) -> Path:
    return adapter_tree / "CLAUDE.md"


# ── Scenario 1: CLAUDE.md absent → created ────────────────────────────────


def test_creates_claude_md_when_absent(adapter_tree: Path) -> None:
    """When no CLAUDE.md exists, the script creates a minimal one with both @-includes."""
    assert not _claude_md(adapter_tree).exists()

    result = _run_script(adapter_tree)

    assert result.returncode == 0, result.stderr
    content = _claude_md(adapter_tree).read_text(encoding="utf-8")
    assert "@.pkit/rules/core.md" in content
    assert "@.pkit/rules/project.md" in content


def test_created_claude_md_has_h1(adapter_tree: Path) -> None:
    """The created CLAUDE.md must have an H1 (per core.md rule 13)."""
    _run_script(adapter_tree)
    content = _claude_md(adapter_tree).read_text(encoding="utf-8")
    lines = content.splitlines()
    assert any(line.startswith("# ") for line in lines), (
        "created CLAUDE.md has no H1; violates the @-include authoring convention (rule 13)"
    )


def test_created_claude_md_include_after_h1(adapter_tree: Path) -> None:
    """The @-include must not be on line 1; it must come after the H1 (rule 13)."""
    _run_script(adapter_tree)
    lines = _claude_md(adapter_tree).read_text(encoding="utf-8").splitlines()
    include_idx = next(
        (i for i, l in enumerate(lines) if "@.pkit/rules/core.md" in l), None
    )
    h1_idx = next((i for i, l in enumerate(lines) if l.startswith("# ")), None)
    assert include_idx is not None, "@.pkit/rules/core.md not found in created file"
    assert h1_idx is not None, "no H1 in created file"
    assert include_idx > h1_idx, (
        "@.pkit/rules/core.md appears before (or at) the H1; violates rule 13"
    )


# ── Scenario 2: CLAUDE.md exists with H1, no @-include → inserted ─────────


def test_inserts_include_after_h1_when_absent(adapter_tree: Path) -> None:
    """When CLAUDE.md has an H1 but no @-include, the @-include is inserted after the H1."""
    _claude_md(adapter_tree).write_text(
        "# My Project Instructions\n\nSome existing content.\n",
        encoding="utf-8",
    )

    result = _run_script(adapter_tree)

    assert result.returncode == 0, result.stderr
    content = _claude_md(adapter_tree).read_text(encoding="utf-8")
    assert "@.pkit/rules/core.md" in content
    assert "@.pkit/rules/project.md" in content
    # The H1 must still be present.
    assert "# My Project Instructions" in content
    # The existing prose must be preserved.
    assert "Some existing content." in content


def test_include_positioned_after_h1_in_existing_file(adapter_tree: Path) -> None:
    """The inserted @-include must come after the H1, not before."""
    _claude_md(adapter_tree).write_text(
        "# My Project\n\nPre-existing prose.\n",
        encoding="utf-8",
    )
    _run_script(adapter_tree)
    lines = _claude_md(adapter_tree).read_text(encoding="utf-8").splitlines()
    include_idx = next(
        (i for i, l in enumerate(lines) if "@.pkit/rules/core.md" in l), None
    )
    h1_idx = next((i for i, l in enumerate(lines) if l.startswith("# ")), None)
    assert include_idx is not None
    assert h1_idx is not None
    assert include_idx > h1_idx, "@-include appears before the H1"


def test_adopter_content_preserved_after_insert(adapter_tree: Path) -> None:
    """Inserting the @-include must not destroy any adopter prose."""
    original = (
        "# Claude Code instructions — my-project\n\n"
        "Custom session instructions here.\n\n"
        "## Workflow\n\nDo things.\n"
    )
    _claude_md(adapter_tree).write_text(original, encoding="utf-8")

    _run_script(adapter_tree)

    content = _claude_md(adapter_tree).read_text(encoding="utf-8")
    # Every line from the original must survive in the output.
    for line in original.splitlines():
        assert line in content.splitlines(), (
            f"adopter line {line!r} was lost after @-include insertion"
        )


# ── Scenario 3: CLAUDE.md exists, no H1 → prepend ────────────────────────


def test_prepends_when_no_h1_in_existing_file(adapter_tree: Path) -> None:
    """When the existing CLAUDE.md has no H1, a minimal header + @-includes are prepended."""
    existing = "Some instructions without a heading.\n\nMore content.\n"
    _claude_md(adapter_tree).write_text(existing, encoding="utf-8")

    result = _run_script(adapter_tree)

    assert result.returncode == 0, result.stderr
    content = _claude_md(adapter_tree).read_text(encoding="utf-8")
    assert "@.pkit/rules/core.md" in content
    # Original content must still be present.
    assert "Some instructions without a heading." in content
    assert "More content." in content


def test_prepend_produces_h1_for_no_h1_case(adapter_tree: Path) -> None:
    """The prepend case must produce an H1 so the @-include can nest under it (rule 13)."""
    _claude_md(adapter_tree).write_text("No heading here.\n", encoding="utf-8")
    _run_script(adapter_tree)
    lines = _claude_md(adapter_tree).read_text(encoding="utf-8").splitlines()
    assert any(l.startswith("# ") for l in lines), "prepend case produced no H1"


# ── Scenario 4: @-include already present → no-op ─────────────────────────


def test_idempotent_when_include_already_present(adapter_tree: Path) -> None:
    """Re-running on a CLAUDE.md that already has the @-include is a no-op."""
    original = (
        "# Claude Code instructions\n\n"
        "@.pkit/rules/core.md\n"
        "@.pkit/rules/project.md\n\n"
        "Project-specific content.\n"
    )
    _claude_md(adapter_tree).write_text(original, encoding="utf-8")

    result = _run_script(adapter_tree)

    assert result.returncode == 0, result.stderr
    # File must be byte-for-byte identical.
    assert _claude_md(adapter_tree).read_text(encoding="utf-8") == original


def test_no_duplicate_include_on_second_run(adapter_tree: Path) -> None:
    """Running the script twice must not produce a second @-include line."""
    _run_script(adapter_tree)  # first run: creates CLAUDE.md
    _run_script(adapter_tree)  # second run: must be a no-op

    content = _claude_md(adapter_tree).read_text(encoding="utf-8")
    count = content.count("@.pkit/rules/core.md")
    assert count == 1, f"@.pkit/rules/core.md appears {count} times (expected 1)"
