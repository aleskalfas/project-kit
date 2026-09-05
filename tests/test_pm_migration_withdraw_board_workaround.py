"""Warn-on-detect migration: retract the withdrawn `unsupported`-means-board advice.

Until the `board:` binding arm existed, `pre-check`'s remediation told adopters to
mark a board-backed axis `unsupported: true` — a declaration the schema defines as
the axis having NO encoding, with every rule needing it degrading. The guidance is
corrected at its source in the same change-set; this migration exists so the
retraction also reaches adopters who ALREADY acted on it and will never re-read
that remediation.

Pinned here:

  * the three-way signature (a configured board + a board-DECLARABLE axis marked
    `unsupported: true` + a `set-board-field` hook) — all three required, because
    each alone has an innocent reading;
  * NO auto-edit — `project/substrate-map.yaml` is adopter-owned hand-authored
    intent, and the detection is a heuristic (a hook names an opaque `field_id`,
    never an axis), the same posture as the 0.26.0 workflow.yaml override
    migration;
  * idempotency — a map already carrying `board: true` matches nothing, and every
    path exits 0 (this is a report, not a gate, and must not break an upgrade).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CAPABILITY = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
MIGRATION = (
    CAPABILITY / "migrations" / "0.55.0" / "002-withdraw-unsupported-board-workaround.sh"
)

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

NO_BOARD_HOOK = """\
schema_version: 1
hooks:
  after_create_issue:
    - kind: post-comment
      template_path: project/templates/welcome.md
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
    return (
        root
        / ".pkit"
        / "capabilities"
        / "project-management"
        / "project"
        / "substrate-map.yaml"
    )


# ----- the signature fires -------------------------------------------------


def test_workaround_shape_is_detected_and_reported(tmp_path: Path) -> None:
    root = _make_adopter(tmp_path)
    result = _run(root)
    assert result.returncode == 0, result.stderr
    assert "[warn]" in result.stdout
    assert "priority" in result.stdout and "workstream" in result.stdout


def test_report_shows_the_one_line_change(tmp_path: Path) -> None:
    """Actionable on its own: the exact edit, and why `unsupported` is not it."""
    out = _run(_make_adopter(tmp_path)).stdout
    assert "-     unsupported: true" in out
    assert "+     board: true" in out
    assert "NO encoding" in out


def test_report_says_why_it_did_not_apply_the_change(tmp_path: Path) -> None:
    """Two grounds, both load-bearing: adopter-owned intent, and a signature that
    is a heuristic (a hook names an opaque `field_id`, never an axis)."""
    out = _run(_make_adopter(tmp_path)).stdout
    assert "NOT APPLIED AUTOMATICALLY" in out
    assert "hand-authored" in out
    assert "field_id" in out


def test_the_map_is_never_edited(tmp_path: Path) -> None:
    """The load-bearing invariant. The file must come out byte-identical."""
    root = _make_adopter(tmp_path)
    before = _map_of(root).read_bytes()
    _run(root)
    assert _map_of(root).read_bytes() == before


def test_only_the_board_declarable_axis_is_reported(tmp_path: Path) -> None:
    """`type` and `state` refuse the arm in the schema, so neither can take this
    repair — reporting them would recommend a map `pkit schemas validate`
    rejects."""
    root = _make_adopter(
        tmp_path,
        substrate_map=(
            "schema_version: 1\n"
            "axes:\n"
            "  priority:\n"
            "    unsupported: true\n"
            "  type:\n"
            "    unsupported: true\n"
            "  state:\n"
            "    unsupported: true\n"
        ),
    )
    out = _run(root).stdout
    axes_line = next(line for line in out.splitlines() if line.strip().startswith("Axes:"))
    assert "priority" in axes_line
    assert "type" not in axes_line
    assert "state" not in axes_line


# ----- each missing signal makes it a no-op --------------------------------


def test_no_board_configured_is_clean(tmp_path: Path) -> None:
    """Without a board there is nothing for the board to carry, so
    `unsupported: true` is simply what it says."""
    result = _run(_make_adopter(tmp_path, config=NO_BOARD_CONFIG))
    assert result.returncode == 0
    assert "[warn]" not in result.stdout
    assert "no configured Projects-v2 board" in result.stdout


def test_no_set_board_field_hook_is_clean(tmp_path: Path) -> None:
    """The corroborating signal. Without a hook, nothing suggests a board field is
    actually being written, and the `unsupported` reading stands."""
    result = _run(_make_adopter(tmp_path, hooks=NO_BOARD_HOOK))
    assert result.returncode == 0
    assert "[warn]" not in result.stdout
    assert "set-board-field" in result.stdout


def test_no_hooks_file_at_all_is_clean(tmp_path: Path) -> None:
    result = _run(_make_adopter(tmp_path, hooks=None))
    assert result.returncode == 0
    assert "[warn]" not in result.stdout


def test_no_config_is_clean(tmp_path: Path) -> None:
    result = _run(_make_adopter(tmp_path, config=None))
    assert result.returncode == 0
    assert "[warn]" not in result.stdout


def test_greenfield_no_map_is_clean(tmp_path: Path) -> None:
    """No substrate-map ⇒ greenfield: every axis reads the kit's own labels and
    the workaround cannot exist."""
    result = _run(_make_adopter(tmp_path, substrate_map=None))
    assert result.returncode == 0
    assert "greenfield" in result.stdout


def test_capability_absent_skips(tmp_path: Path) -> None:
    root = tmp_path / "empty"
    root.mkdir()
    result = _run(root)
    assert result.returncode == 0
    assert "[skip]" in result.stdout


def test_bound_axes_are_not_the_workaround(tmp_path: Path) -> None:
    """An axis bound to the adopter's own labels is a legitimate brownfield
    binding, not the withdrawn shape. (It IS the #708 conflict under a board —
    `pre-check` owns that finding; this migration must not duplicate it.)"""
    root = _make_adopter(
        tmp_path,
        substrate_map=(
            "schema_version: 1\n"
            "axes:\n"
            "  priority:\n"
            "    label:\n"
            "      remap:\n"
            "        High: P0\n"
        ),
    )
    result = _run(root)
    assert result.returncode == 0
    assert "[warn]" not in result.stdout


# ----- idempotency ---------------------------------------------------------


def test_repaired_map_matches_nothing(tmp_path: Path) -> None:
    """The destination state. An axis carrying `board: true` is no longer
    `unsupported`, so the signature cannot match."""
    result = _run(_make_adopter(tmp_path, substrate_map=REPAIRED_MAP))
    assert result.returncode == 0
    assert "[warn]" not in result.stdout
    assert "no board-declarable axis marked" in result.stdout


def test_rerun_on_a_repaired_map_is_a_byte_identical_noop(tmp_path: Path) -> None:
    root = _make_adopter(tmp_path, substrate_map=REPAIRED_MAP)
    first = _run(root)
    second = _run(root)
    assert first.returncode == second.returncode == 0
    assert first.stdout == second.stdout


def test_rerun_on_the_workaround_shape_is_stable(tmp_path: Path) -> None:
    """Re-running before the adopter has edited anything repeats the same report
    and still changes nothing — the migration is a report, and a report is safe to
    repeat."""
    root = _make_adopter(tmp_path)
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
    """`pkit migrations check-diff` reports no migration is REQUIRED for this
    change-set. The script says so, so a later reader does not mistake it for
    evidence that COR-010's trigger fired."""
    header = MIGRATION.read_text(encoding="utf-8")
    assert "DISCRETIONARY" in header
    assert "check-diff" in header


def test_script_is_executable_and_sets_strict_mode() -> None:
    assert MIGRATION.stat().st_mode & 0o111, "migration must be executable"
    assert "set -euo pipefail" in MIGRATION.read_text(encoding="utf-8")
