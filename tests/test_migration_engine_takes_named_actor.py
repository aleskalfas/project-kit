"""The guidance migration for the engine's lost default actor (ADR-098).

The engine takes only the actor its caller names, so a call that leaves `--actor` out
gets none, and a cross-authority gate whose authorisation names its producer is not
judged. `3.0.0/001-engine-takes-named-actor` names each process definition whose callers
the release does not bring and that holds such a gate: one of a capability the manifest
records as incubated in the repository or sourced from another repository. It edits
nothing and exits clean, over any state.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATION = (
    REPO_ROOT / ".pkit" / "migrations" / "backbone" / "3.0.0" / "001-engine-takes-named-actor.sh"
)

#: Run by its full path, so a test can leave python3 off PATH: the system's, where a
#: version manager's shim stands first on PATH.
BASH = "/bin/bash" if Path("/bin/bash").is_file() else shutil.which("bash") or "bash"

_GATED = """\
process:
  id: review
  version: 1
  transitions:
    - from: open
      to: shut
      trigger: approve
      authorisation: user
      gate:
        kind: authorisation-artifact
        predicate:
          run: gate-review
    - from: open
      to: open
      trigger: note
      authorisation: agent-autonomous
      entry_guards:
        - from: elsewhere
          run: guard-note
    - authorisation: user
      trigger: reopen
      from: shut
      to: open
      gate:
        kind: authorisation-artifact
        predicate:
          run: gate-reopen
"""

_UNGATED = """\
process:
  id: plain
  version: 1
  transitions:
    - from: open
      to: shut
      trigger: close
      gate:
        kind: deterministic
        predicate:
          run: gate-ok
"""


def _run(
    root: Path, path: str = "/usr/bin:/bin:/usr/local/bin"
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [BASH, str(MIGRATION)],
        env={"ROOT": str(root), "PATH": path},
        capture_output=True,
        text=True,
        check=False,
    )


def _project(tmp_path: Path, capabilities: dict[str, tuple[str, dict[str, str]]]) -> Path:
    """A project whose manifest registers each capability with its origin ("" for none),
    and its `schemas/` files."""
    root = tmp_path / "project"
    lines = ["schema_version: 1", "backbone_version: 3.0.0", "components:"]
    for name, (origin, schemas) in capabilities.items():
        lines += ["  - kind: capability", f"    name: {name}", f"    manifest: {name}.yaml"]
        if origin:
            lines.append(f"    origin: {origin}")
        for file, text in schemas.items():
            path = root / ".pkit" / "capabilities" / name / "schemas" / file
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
    (root / ".pkit").mkdir(parents=True, exist_ok=True)
    (root / ".pkit" / "manifest.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return root


def _tree(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): path.read_text(encoding="utf-8")
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


@pytest.mark.parametrize("origin", ["incubated-in-repo", "externally-sourced"])
def test_names_each_gate_whose_callers_the_release_does_not_bring(
    tmp_path: Path, origin: str
) -> None:
    root = _project(
        tmp_path,
        {
            "mine": (origin, {"review.yaml": _GATED, "plain.yaml": _UNGATED}),
            "shipped": ("", {"review.yaml": _GATED}),
        },
    )
    before = _tree(root)

    result = _run(root)

    assert result.returncode == 0, result.stderr
    assert "[warn] these process definitions hold a cross-authority" in result.stderr
    assert "mine:review (.pkit/capabilities/mine/schemas/review.yaml)" in result.stderr
    assert "the move open -> shut [approve]" in result.stderr
    # A transition is told apart by its place in the list, whatever key opens it,
    # and a list nested in another transition names no move.
    assert "the move shut -> open [reopen]" in result.stderr
    assert "elsewhere" not in result.stderr
    assert "mine:plain" not in result.stderr
    assert "shipped:" not in result.stderr
    assert "--actor" in result.stderr
    assert _tree(root) == before
    assert _run(root).stderr == result.stderr


def test_a_project_with_no_such_gate_exits_clean(tmp_path: Path) -> None:
    root = _project(
        tmp_path,
        {
            "mine": ("incubated-in-repo", {"plain.yaml": _UNGATED}),
            "shipped": ("", {"x.yaml": _GATED}),
        },
    )

    result = _run(root)

    assert result.returncode == 0, result.stderr
    assert "[skip]" in result.stdout
    assert result.stderr == ""


def test_a_project_with_no_manifest_exits_clean(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()

    result = _run(root)

    assert result.returncode == 0, result.stderr
    assert "[skip]" in result.stdout


def test_without_python3_it_says_what_it_could_not_read(tmp_path: Path) -> None:
    root = _project(tmp_path, {"mine": ("incubated-in-repo", {"review.yaml": _GATED})})
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    result = _run(root, path=str(bin_dir))

    assert result.returncode == 0, result.stderr
    assert "no python3 on PATH" in result.stderr
