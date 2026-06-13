"""Tests for the `pkit` CLI entry point.

Phase 1's surface is `version` only; Phase 2 (PR-D / PR-E / PR-F) ports
the bash dispatcher's other commands and grows this test file alongside.
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from project_kit import __version__
from project_kit.cli import main


def test_version_subcommand_prints_pkit_then_version() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["version"])
    assert result.exit_code == 0
    assert result.output.strip() == f"pkit {__version__}"


def test_version_flag_uses_click_default_format() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    # Click's standard --version output uses the "<prog>, version <X>" form.
    assert result.output.strip() == f"pkit, version {__version__}"


def test_root_invocation_with_no_args_shows_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, [])
    assert result.exit_code == 0
    assert "Usage:" in result.output
    assert "version" in result.output  # the version subcommand is listed


def test_kit_version_is_semver_three_segment() -> None:
    parts = __version__.split(".")
    assert len(parts) == 3, f"expected major.minor.patch, got {__version__!r}"
    for part in parts:
        assert part.isdigit(), f"non-numeric segment in version {__version__!r}"


@pytest.mark.parametrize("subcommand", ["area", "adapter", "migration", "capability", "decision"])
def test_new_subcommand_surfaces_help(subcommand: str) -> None:
    """The core `new <subcommand>` commands all expose --help."""
    runner = CliRunner()
    result = runner.invoke(main, ["new", subcommand, "--help"])
    assert result.exit_code == 0
    assert "Usage:" in result.output
