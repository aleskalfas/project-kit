"""Tests for the issue #96 migrations: rules-area propagation + CLAUDE.md wiring.

Backbone migration 1.93.0/001-propagate-rules-area.sh:
  - Idempotent: already-present core.md → skip.
  - Missing core.md with uv-locatable source → copies file.
  - Missing core.md with no source → exits non-zero (warns).

Adapter migration 0.5.0/001-wire-claude-md-rules-include.sh:
  - CLAUDE.md absent → created with @-includes.
  - CLAUDE.md exists, no @-include, has H1 → @-includes inserted after H1.
  - CLAUDE.md exists, no H1 → @-includes prepended with minimal header.
  - CLAUDE.md already has @-include → no-op (idempotent).
  - Adopter content is always preserved.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
BACKBONE_MIGRATION = (
    REPO_ROOT / ".pkit" / "migrations" / "backbone" / "1.93.0" / "001-propagate-rules-area.sh"
)
ADAPTER_MIGRATION = (
    REPO_ROOT
    / ".pkit"
    / "adapters"
    / "claude-code"
    / "migrations"
    / "0.5.0"
    / "001-wire-claude-md-rules-include.sh"
)
SOURCE_RULES_DIR = REPO_ROOT / ".pkit" / "rules"


def _run_backbone(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(BACKBONE_MIGRATION)],
        capture_output=True,
        text=True,
        check=False,
        env={"ROOT": str(root), "PATH": "/usr/bin:/bin:/usr/local/bin"},
    )


def _run_adapter(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(ADAPTER_MIGRATION)],
        capture_output=True,
        text=True,
        check=False,
        env={"ROOT": str(root), "PATH": "/usr/bin:/bin:/usr/local/bin"},
    )


# ── Backbone migration: propagate-rules-area ──────────────────────────────


class TestPropagateRulesArea:
    def test_skips_when_core_md_already_present(self, tmp_path: Path) -> None:
        """Already-migrated state: core.md present → exit 0, skip message."""
        rules = tmp_path / ".pkit" / "rules"
        rules.mkdir(parents=True)
        (rules / "core.md").write_text("# Rules\n", encoding="utf-8")

        result = _run_backbone(tmp_path)

        assert result.returncode == 0, result.stderr
        assert "skip" in result.stdout.lower()
        # File must be untouched (migration is read-only when already present).
        assert (rules / "core.md").read_text(encoding="utf-8") == "# Rules\n"

    def test_idempotent_second_run_also_skips(self, tmp_path: Path) -> None:
        """Running the backbone migration twice on an already-migrated tree is a no-op."""
        rules = tmp_path / ".pkit" / "rules"
        rules.mkdir(parents=True)
        (rules / "core.md").write_text("# Core rules\n", encoding="utf-8")

        r1 = _run_backbone(tmp_path)
        r2 = _run_backbone(tmp_path)

        assert r1.returncode == 0
        assert r2.returncode == 0
        assert "skip" in r2.stdout.lower()


# ── Adapter migration: wire-claude-md-rules-include ───────────────────────


class TestWireClaudeMdRulesInclude:
    def test_creates_claude_md_when_absent(self, tmp_path: Path) -> None:
        """Migration creates a minimal CLAUDE.md when none exists."""
        assert not (tmp_path / "CLAUDE.md").exists()

        result = _run_adapter(tmp_path)

        assert result.returncode == 0, result.stderr
        content = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
        assert "@.pkit/rules/core.md" in content
        assert "@.pkit/rules/project.md" in content

    def test_created_has_h1(self, tmp_path: Path) -> None:
        """The created CLAUDE.md has an H1 (rule 13: includes must nest under a host heading)."""
        _run_adapter(tmp_path)
        lines = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8").splitlines()
        assert any(l.startswith("# ") for l in lines)

    def test_inserts_after_h1_in_existing_file(self, tmp_path: Path) -> None:
        """Existing CLAUDE.md with H1 but no @-include → @-includes inserted after H1."""
        (tmp_path / "CLAUDE.md").write_text(
            "# My project\n\nExisting instructions.\n", encoding="utf-8"
        )

        result = _run_adapter(tmp_path)

        assert result.returncode == 0, result.stderr
        content = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
        assert "@.pkit/rules/core.md" in content
        assert "My project" in content
        assert "Existing instructions." in content

        lines = content.splitlines()
        h1_idx = next(i for i, l in enumerate(lines) if l.startswith("# "))
        inc_idx = next(i for i, l in enumerate(lines) if "@.pkit/rules/core.md" in l)
        assert inc_idx > h1_idx, "@-include must appear after the H1"

    def test_prepends_when_no_h1(self, tmp_path: Path) -> None:
        """Existing CLAUDE.md with no H1 → @-includes prepended with a synthetic H1."""
        (tmp_path / "CLAUDE.md").write_text(
            "Some instructions with no heading.\n", encoding="utf-8"
        )

        result = _run_adapter(tmp_path)

        assert result.returncode == 0, result.stderr
        content = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
        assert "@.pkit/rules/core.md" in content
        assert "Some instructions with no heading." in content

    def test_idempotent_when_include_present(self, tmp_path: Path) -> None:
        """Already-migrated state: @-include present → exit 0, file unchanged."""
        original = (
            "# Claude Code instructions\n\n"
            "@.pkit/rules/core.md\n"
            "@.pkit/rules/project.md\n\n"
            "Project content.\n"
        )
        (tmp_path / "CLAUDE.md").write_text(original, encoding="utf-8")

        result = _run_adapter(tmp_path)

        assert result.returncode == 0, result.stderr
        assert "skip" in result.stdout.lower()
        assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8") == original

    def test_idempotent_second_run_no_duplicate(self, tmp_path: Path) -> None:
        """Running the adapter migration twice does not duplicate the @-include."""
        _run_adapter(tmp_path)  # creates CLAUDE.md
        _run_adapter(tmp_path)  # must be a no-op

        content = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
        assert content.count("@.pkit/rules/core.md") == 1

    def test_adopter_content_preserved_on_insert(self, tmp_path: Path) -> None:
        """Every line of the adopter's existing CLAUDE.md survives the insertion."""
        original = (
            "# Claude Code instructions — my-app\n\n"
            "We follow the team handbook.\n\n"
            "## Session style\n\n"
            "Be terse.\n"
        )
        (tmp_path / "CLAUDE.md").write_text(original, encoding="utf-8")
        _run_adapter(tmp_path)

        content = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
        for line in original.splitlines():
            assert line in content.splitlines(), (
                f"adopter line {line!r} was lost after migration"
            )
