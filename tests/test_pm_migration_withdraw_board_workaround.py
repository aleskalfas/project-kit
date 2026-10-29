"""Report-only migration: a label-bound axis under a board, whose corpus may need repair.

Until DEC-051 nothing decided which declaration won where a configured board and
a `label:` binding spoke to one axis, so issues filed then may carry a value on
neither substrate. This migration names `pkit pm back-fill` to the adopters
holding that shape.

Pinned here:

  * the condition: a configured board and a board-claimed axis bound with a
    `label:` arm, no hook required;
  * NO edit — `project/substrate-map.yaml` is the adopter's;
  * the withdrawn `unsupported: true` workaround is no longer reported here:
    DEC-062 ends the board flag's carriage, and the 005 migration of the same
    release writes `board: true` in its place;
  * idempotency — every path exits 0, and a re-run reports the same.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CAPABILITY = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
MIGRATION = CAPABILITY / "migrations" / "0.55.0" / "003-withdraw-unsupported-board-workaround.sh"

BOARD_CONFIG = """\
schema_version: 1
default_branch: main
has_projects_v2_board: true
projects_v2_board_id: 7
"""

NO_BOARD_CONFIG = """\
schema_version: 1
default_branch: main
has_projects_v2_board: false
"""

WORKAROUND_MAP = """\
schema_version: 1
axes:
  priority:
    unsupported: true  # the board's Priority field carries this
  workstream:
    unsupported: true
  type:
    title-prefix:
      remap:
        task: "[Task]"
"""

REPAIRED_MAP = """\
schema_version: 1
axes:
  priority:
    board: true
  workstream:
    board: true
  type:
    title-prefix:
      remap:
        task: "[Task]"
"""

CREATE_HOOK = """\
schema_version: 1
hooks:
  after_create_issue:
    - kind: set-board-field
      field_id: PVTSSF_x
      single_select_option_id: opt-1
"""


def _make_adopter(
    tmp_path: Path,
    *,
    config: str | None = BOARD_CONFIG,
    substrate_map: str | None = WORKAROUND_MAP,
    hooks: str | None = CREATE_HOOK,
    name: str = "adopter",
) -> Path:
    """A minimal adopter tree carrying whichever of the three signals are given."""
    root = tmp_path / name
    project = root / ".pkit" / "capabilities" / "project-management" / "project"
    project.mkdir(parents=True)
    for filename, body in (
        ("config.yaml", config),
        ("substrate-map.yaml", substrate_map),
        ("hooks.yaml", hooks),
    ):
        if body is not None:
            (project / filename).write_text(body, encoding="utf-8")
    return root


def _run(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(MIGRATION)],
        env={"ROOT": str(root), "PATH": "/usr/bin:/bin:/usr/local/bin"},
        capture_output=True,
        text=True,
        check=False,
    )


def _map_of(root: Path) -> Path:
    return root / ".pkit" / "capabilities" / "project-management" / "project" / "substrate-map.yaml"


# ----- the withdrawn workaround is left to the next migration ---------------


def test_the_workaround_shape_is_not_reported(tmp_path: Path) -> None:
    """DEC-062 point 6: the 005 migration writes `board: true` in place of
    `unsupported: true` under a set flag, so this one says nothing of it."""
    result = _run(_make_adopter(tmp_path))
    assert result.returncode == 0, result.stderr
    assert "[warn]" not in result.stdout
    assert "NOT APPLIED AUTOMATICALLY" not in result.stdout


def test_the_map_is_never_edited(tmp_path: Path) -> None:
    """The file must come out byte-identical."""
    root = _make_adopter(tmp_path)
    before = _map_of(root).read_bytes()
    _run(root)
    assert _map_of(root).read_bytes() == before


# ----- each missing signal makes it a no-op --------------------------------


def test_no_board_configured_is_clean(tmp_path: Path) -> None:
    """Without a board there is nothing for the board to carry, so
    `unsupported: true` is simply what it says."""
    result = _run(_make_adopter(tmp_path, config=NO_BOARD_CONFIG))
    assert result.returncode == 0
    assert "[warn]" not in result.stdout
    assert "no configured Projects-v2 board" in result.stdout


def test_no_config_is_clean(tmp_path: Path) -> None:
    result = _run(_make_adopter(tmp_path, config=None))
    assert result.returncode == 0
    assert "[warn]" not in result.stdout


def test_greenfield_no_map_is_clean(tmp_path: Path) -> None:
    """No substrate-map ⇒ greenfield: every axis reads the kit's own labels, and
    no axis is bound to the adopter's own."""
    result = _run(_make_adopter(tmp_path, substrate_map=None))
    assert result.returncode == 0
    assert "greenfield" in result.stdout


def test_capability_absent_skips(tmp_path: Path) -> None:
    root = tmp_path / "empty"
    root.mkdir()
    result = _run(root)
    assert result.returncode == 0
    assert "[skip]" in result.stdout


def test_a_label_bound_axis_under_a_board_points_at_the_repair(tmp_path: Path) -> None:
    """The reported failure's own shape, and the reason the detection widened.

    An axis bound to the adopter's own labels under a configured board is not the
    withdrawn `unsupported: true` workaround — it is a legitimate brownfield
    binding, and from this release it WORKS. But it is also the configuration
    whose already-filed issues carry a value on neither substrate, because until
    now nothing decided which declaration won.

    That adopter previously matched no signal and saw nothing on upgrade: the old
    signature required a `set-board-field` hook, which this shape does not have.
    So the one whose corpus is damaged was the one told nothing. The migration now
    names the repair verb — it cannot know whether the corpus is affected without
    reading issues, and a migration makes no network calls, so it points rather
    than claims.
    """
    root = _make_adopter(
        tmp_path,
        substrate_map=(
            "schema_version: 1\naxes:\n  priority:\n    label:\n      remap:\n        High: P0\n"
        ),
    )
    result = _run(root)
    assert result.returncode == 0
    assert "[warn]" in result.stdout
    assert "pkit pm back-fill" in result.stdout
    assert "priority" in result.stdout
    # It must NOT claim the corpus is damaged — it has not looked.
    assert "does NOT know whether your corpus is affected" in result.stdout
    assert "unsupported: true" not in result.stdout


def test_no_hook_does_not_suppress_the_label_finding(tmp_path: Path) -> None:
    """A `label:` binding needs no hook to be the damaged shape."""
    root = _make_adopter(
        tmp_path,
        substrate_map=(
            "schema_version: 1\n"
            "axes:\n"
            "  workstream:\n"
            "    label:\n"
            "      remap:\n"
            "        cli: area/cli\n"
        ),
        hooks="after_create_issue: []\n",
    )
    result = _run(root)
    assert result.returncode == 0
    assert "pkit pm back-fill" in result.stdout


# ----- idempotency ---------------------------------------------------------


def test_repaired_map_matches_nothing(tmp_path: Path) -> None:
    """An axis carrying `board: true` is bound to no label, so nothing matches."""
    result = _run(_make_adopter(tmp_path, substrate_map=REPAIRED_MAP))
    assert result.returncode == 0
    assert "[warn]" not in result.stdout
    assert "no board-claimed axis is bound to labels" in result.stdout


def test_rerun_on_a_repaired_map_is_a_byte_identical_noop(tmp_path: Path) -> None:
    root = _make_adopter(tmp_path, substrate_map=REPAIRED_MAP)
    first = _run(root)
    second = _run(root)
    assert first.returncode == second.returncode == 0
    assert first.stdout == second.stdout


def test_rerun_on_a_label_bound_map_is_stable(tmp_path: Path) -> None:
    """Re-running repeats the same report and still changes nothing — the
    migration is a report, and a report is safe to repeat."""
    root = _make_adopter(
        tmp_path,
        substrate_map=(
            "schema_version: 1\naxes:\n  priority:\n    label:\n      remap:\n        High: P0\n"
        ),
    )
    before = _map_of(root).read_bytes()
    first = _run(root)
    second = _run(root)
    assert first.stdout == second.stdout
    assert first.returncode == second.returncode == 0
    assert _map_of(root).read_bytes() == before


def test_every_path_exits_zero(tmp_path: Path) -> None:
    """It must never break an upgrade: this is advice, not a gate."""
    cases = [
        _make_adopter(tmp_path, name="a"),
        _make_adopter(tmp_path, name="b", config=NO_BOARD_CONFIG),
        _make_adopter(tmp_path, name="c", hooks=None),
        _make_adopter(tmp_path, name="d", substrate_map=None),
        _make_adopter(tmp_path, name="e", substrate_map=REPAIRED_MAP),
        _make_adopter(tmp_path, name="f", substrate_map="axes: [not a mapping\n"),
        _make_adopter(tmp_path, name="g", substrate_map="schema_version: 1\n"),
    ]
    for root in cases:
        assert _run(root).returncode == 0, root.name


# ----- provenance ----------------------------------------------------------


def test_header_declares_the_migration_discretionary(tmp_path: Path) -> None:
    """`pkit migrations check-diff` reports no migration was REQUIRED for the
    DEC-051 change-set. The script says so, so a later reader does not mistake
    it for evidence that COR-010's trigger fired."""
    header = MIGRATION.read_text(encoding="utf-8")
    assert "DISCRETIONARY" in header
    assert "check-diff" in header
    assert "005-board-flag-carries-no-axis.sh" in header


def test_script_is_executable_and_sets_strict_mode() -> None:
    assert MIGRATION.stat().st_mode & 0o111, "migration must be executable"
    assert "set -euo pipefail" in MIGRATION.read_text(encoding="utf-8")
