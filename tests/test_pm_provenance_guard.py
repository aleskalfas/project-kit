"""Guard: no pm script writes an issue/PR body outside the provenance seam.

ADR-037 item 4. The provenance footer is maintained by exactly one seam
(`_lib/provenance.stamp`). This is a *scan-all* over every pm script —
not an allow-list of known sites — asserting that any script which
constructs an issue/PR body write also routes through the seam. A new
body-writing script that skips `provenance.stamp()` fails this test.

Body writes use a `"--body-file"` argv by convention across the
capability (issue/PR `edit`/`create`), which is the write-construction
marker scanned here. Comments (`--body`) and the pure criterion engine
(which returns a plan and performs no I/O) are not body writes.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = (
    REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
)

# The seam module itself constructs the footer; it is the exempt origin.
_EXEMPT = {"_lib/provenance.py"}

# Marker of an actual body-write argv construction (quoted argv element),
# as opposed to a bare docstring mention of the flag.
_BODY_WRITE_MARKER = '"--body-file"'
_SEAM_CALL = "provenance.stamp("


def _py_files() -> list[Path]:
    return sorted(
        [*SCRIPTS.glob("*.py"), *SCRIPTS.glob("_lib/*.py")]
    )


def _rel(p: Path) -> str:
    return str(p.relative_to(SCRIPTS))


def test_every_body_write_routes_through_the_seam() -> None:
    offenders = []
    for f in _py_files():
        rel = _rel(f)
        if rel in _EXEMPT:
            continue
        text = f.read_text(encoding="utf-8")
        if _BODY_WRITE_MARKER in text and _SEAM_CALL not in text:
            offenders.append(rel)
    assert not offenders, (
        "these scripts construct an issue/PR body write "
        f'({_BODY_WRITE_MARKER}) without routing through {_SEAM_CALL} '
        "(ADR-037 item 4): " + ", ".join(offenders)
    )


def test_guard_has_body_writers_to_check() -> None:
    """The guard is only meaningful if body-writing sites actually exist."""
    writers = [
        _rel(f)
        for f in _py_files()
        if _BODY_WRITE_MARKER in f.read_text(encoding="utf-8")
        and _rel(f) not in _EXEMPT
    ]
    assert writers, "expected at least one body-writing script to guard"
