"""Process journal logging in test repositories (COR-033 point 7).

Journal logging is off unless a project turns it on, so a test that exercises
what the journal records says so explicitly — through the same consent-gated
writer every configuration write uses.
"""

from __future__ import annotations

from pathlib import Path

from project_kit import project_config


def set_journal_logging(repo: Path, *, enabled: bool, committed: bool = False) -> None:
    """Write `process.journal` into the repository's backbone configuration."""
    project_config.write_config(
        repo,
        lambda data: project_config.set_path(
            data, ("process", "journal"), {"enabled": enabled, "committed": committed}
        ),
        consent=project_config.Consent(yes=True),
    )


def enable_journal_logging(repo: Path, *, committed: bool = False) -> None:
    """Turn journal logging on for a test repository."""
    set_journal_logging(repo, enabled=True, committed=committed)
