"""The 0.55.0 migration that retires state seeded from the source project (#814).

The digests embedded in this migration cannot be recomputed from a clean
checkout — the journals they identify are git-ignored, so CI has no copy to hash
against. What CAN be asserted is their *shape*, and that is precisely the
assertion that would have caught the real defect: an early draft carried one
fabricated digest, built by taking a truncated 16-character prefix from earlier
output and inventing the remaining 48. It would have matched nothing, so the
migration would have removed nothing, reported everything, and looked correct.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATION = (
    REPO_ROOT
    / ".pkit"
    / "capabilities"
    / "project-management"
    / "migrations"
    / "0.55.0"
    / "002-retire-seeded-project-state.sh"
)


@pytest.fixture(scope="module")
def source() -> str:
    return MIGRATION.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def digests(source: str) -> list[str]:
    block = re.search(r'SEEDED_JOURNAL_HASHES="\n(.*?)\n"', source, re.S)
    assert block, "the embedded digest block should be findable"
    return block.group(1).split()


def test_every_digest_is_a_well_formed_sha256(digests: list[str]) -> None:
    """The fabricated-value guard. A hand-built digest fails this."""
    assert digests, "expected embedded digests"
    malformed = [d for d in digests if not re.fullmatch(r"[0-9a-f]{64}", d)]
    assert not malformed, f"not well-formed sha256 digests: {malformed}"


def test_digests_are_unique(digests: list[str]) -> None:
    """A duplicate would mean a copy-paste slip, the same failure family."""
    assert len(digests) == len(set(digests))


def test_script_is_syntactically_valid(source: str) -> None:
    proc = subprocess.run(["bash", "-n", str(MIGRATION)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr


def test_script_is_executable() -> None:
    assert MIGRATION.stat().st_mode & 0o111, "migrations are invoked as scripts"


def test_no_hasher_degrades_instead_of_halting(tmp_path: Path) -> None:
    """Absence of a sha256 tool must not abort the upgrade.

    Under `set -euo pipefail` a failing hasher inside a command substitution
    exits at that line, and the runtime halts the WHOLE run on non-zero exit
    with "state may be inconsistent" — while `2>/dev/null` would swallow the
    diagnostic. `shasum` is perl-provided and absent on minimal Debian images;
    `sha256sum` is absent on macOS, so neither name alone is safe.
    """
    journals = (
        tmp_path
        / ".pkit"
        / "capabilities"
        / "project-management"
        / "project"
        / "process"
        / "issue-lifecycle"
    )
    journals.mkdir(parents=True)
    (journals / "1.journal.jsonl").write_text('{"subject":"1"}\n', encoding="utf-8")

    # A PATH carrying the shell tools the script needs, but no hasher.
    binvar = tmp_path / "bin"
    binvar.mkdir()
    for tool in ("bash", "grep", "sed", "find", "cut", "tr", "git", "basename"):
        path = subprocess.run(
            ["/bin/bash", "-c", f"command -v {tool}"], capture_output=True, text=True
        ).stdout.strip()
        if path:
            (binvar / tool).symlink_to(path)

    proc = subprocess.run(
        ["/bin/bash", str(MIGRATION)],
        capture_output=True,
        text=True,
        env={"ROOT": str(tmp_path), "PATH": str(binvar)},
    )
    assert proc.returncode == 0, f"must not halt the upgrade: {proc.stderr}"
    assert "no sha256 tool" in proc.stdout, proc.stdout
    assert (journals / "1.journal.jsonl").exists(), "must judge nothing without a signal"


def test_idempotent_on_a_tree_with_nothing_seeded(tmp_path: Path) -> None:
    project = (
        tmp_path / ".pkit" / "capabilities" / "project-management" / "project"
    )
    project.mkdir(parents=True)
    (project / ".gitkeep").touch()

    for _ in range(2):
        proc = subprocess.run(
            ["/bin/bash", str(MIGRATION)],
            capture_output=True,
            text=True,
            env={"ROOT": str(tmp_path), "PATH": "/usr/bin:/bin"},
        )
        assert proc.returncode == 0, proc.stderr
        assert "nothing to retire" in proc.stdout
