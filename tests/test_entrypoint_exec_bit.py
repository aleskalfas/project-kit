"""CI guard: every dispatcher entrypoint script is git-tracked executable.

Background
----------
#402: two pm entrypoints (`check-doc-mapping.py`, `adopt-existing.py`) were
tracked `100644`, so the dispatcher's `subprocess.run([script_path, ...])`
raised `PermissionError` and those verbs could not run — a latent break,
undetected until a merge happened to need one of them.

The dispatcher invokes an entrypoint *directly* (relying on the kernel honouring
the file's exec bit and shebang), not via `python <script>`. So the git-tracked
mode is load-bearing: a fresh clone gets exactly the mode git records, and a
non-executable entrypoint ships unrunnable. This guard turns that whole class of
defect (stamp gap, manual edit dropping `+x`, bad merge) into a fast, loud,
repo-wide failing check.

Entrypoint discrimination
-------------------------
An *entrypoint* is a `.pkit/**/scripts/*.py` whose first line is the uv-script
shebang::

    #!/usr/bin/env -S uv run --script

The dispatcher invokes exactly these directly, relying on the exec bit.
Importable library modules (e.g. files under `scripts/_lib/`) are NOT
entrypoints — many are intentionally tracked non-executable — and they do not
carry the uv-script shebang. Keying on the shebang therefore excludes libs
naturally, without hard-coding directory layout. This is verified against the
tree: as of writing, no `_lib` module carries the shebang.

Git mode, not filesystem stat
-----------------------------
The check reads the *git-tracked* mode via `git ls-files -s` (the leading
field: `100755` = executable, `100644` = not), not `os.stat`. The tracked mode
is what ships to a fresh clone; a locally-chmodded working tree can mask a bad
tracked mode, so we assert the thing that actually ships.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

# The uv-script shebang that marks a directly-invoked dispatcher entrypoint.
UV_SCRIPT_SHEBANG = "#!/usr/bin/env -S uv run --script"

# Git's mode field for a tracked-executable / tracked-non-executable blob.
EXECUTABLE_MODE = "100755"


def _repo_root() -> Path:
    """Resolve the repo root from git, independent of the test's cwd."""
    out = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True,
        cwd=Path(__file__).resolve().parent,
    )
    return Path(out.stdout.strip())


def _parse_ls_files_mode(line: str) -> tuple[str, str]:
    """Parse one `git ls-files -s` line into (mode, path).

    The format is ``<mode> <object> <stage>\\t<path>``, e.g.::

        100755 9c4e... 0\\tscripts/foo.py

    Returns the leading mode field and the path. Kept as a tiny pure helper so
    the mode-parsing / failure path can be unit-tested against synthetic input
    (including a non-executable `100644` line) without mutating any real file.
    """
    meta, path = line.split("\t", 1)
    mode = meta.split(" ", 1)[0]
    return mode, path


def _is_uv_script_entrypoint(path: Path) -> bool:
    """True iff *path*'s first line is the uv-script shebang."""
    with path.open(encoding="utf-8") as fh:
        first_line = fh.readline().rstrip("\n")
    return first_line == UV_SCRIPT_SHEBANG


def _tracked_entrypoints(repo_root: Path) -> list[tuple[str, str]]:
    """Enumerate (mode, repo-relative-path) for every tracked entrypoint.

    Scans git-tracked `.pkit/**/scripts/*.py` files and keeps those carrying the
    uv-script shebang. Mode is the git-tracked mode from `git ls-files -s`.
    """
    out = subprocess.run(
        ["git", "ls-files", "-s", "--", ".pkit/**/scripts/*.py"],
        capture_output=True,
        text=True,
        check=True,
        cwd=repo_root,
    )
    entrypoints: list[tuple[str, str]] = []
    for line in out.stdout.splitlines():
        if not line:
            continue
        mode, rel_path = _parse_ls_files_mode(line)
        abs_path = repo_root / rel_path
        if not abs_path.is_file():
            continue
        if _is_uv_script_entrypoint(abs_path):
            entrypoints.append((mode, rel_path))
    return entrypoints


def test_dispatcher_entrypoints_are_tracked_executable() -> None:
    """Every uv-script dispatcher entrypoint must be git-tracked `100755`.

    A non-executable entrypoint ships unrunnable through the dispatcher (see
    #402). The git-tracked mode is what reaches a fresh clone, so that — not the
    local filesystem stat — is what we assert.
    """
    repo_root = _repo_root()
    entrypoints = _tracked_entrypoints(repo_root)

    # Sanity: the scan must actually find entrypoints, else a silent enumeration
    # bug would let the guard pass vacuously.
    assert entrypoints, (
        "No uv-script entrypoints found under .pkit/**/scripts/*.py — the "
        "enumeration is broken (it should find dozens)."
    )

    offenders = sorted(rel_path for mode, rel_path in entrypoints if mode != EXECUTABLE_MODE)
    assert not offenders, (
        "These dispatcher entrypoints are tracked non-executable and will "
        "raise PermissionError when the dispatcher invokes them directly "
        f"(expected git mode {EXECUTABLE_MODE}):\n"
        + "\n".join(f"  - {p}" for p in offenders)
        + "\n\nFix each with:\n"
        + "\n".join(f"  chmod +x {p} && git add {p}" for p in offenders)
    )


def test_enumeration_covers_known_entrypoints() -> None:
    """Guard the discriminator itself: known entrypoints must be enumerated.

    If the shebang string or the path glob ever drifts, the scan could silently
    return an empty / partial set and the exec-bit guard would pass vacuously.
    Anchor it to entrypoints we know exist across capabilities.
    """
    repo_root = _repo_root()
    found = {Path(rel_path).name for _, rel_path in _tracked_entrypoints(repo_root)}
    expected = {
        "check-doc-mapping.py",  # was 100644 pre-#402
        "adopt-existing.py",  # was 100644 pre-#402
        "set-field.py",
        "create-issue.py",
    }
    missing = expected - found
    assert not missing, (
        f"Entrypoint enumeration missed known entrypoints {sorted(missing)} — "
        "the shebang discriminator or path glob has drifted."
    )


# ---------------------------------------------------------------------------
# Unit coverage of the failure path, without mutating any real file.
# ---------------------------------------------------------------------------


def test_parse_ls_files_mode_executable() -> None:
    """A `100755` line parses to (mode, path) with the executable mode."""
    line = "100755 9c4e0d8b2f1a3c4d5e6f7a8b9c0d1e2f3a4b5c6d 0\tscripts/foo.py"
    assert _parse_ls_files_mode(line) == ("100755", "scripts/foo.py")


def test_parse_ls_files_mode_non_executable_is_flagged() -> None:
    """A synthetic `100644` line is parsed as non-executable.

    Exercises the failure path of the guard (a tracked non-executable
    entrypoint) without ever leaving a real file at the wrong mode.
    """
    line = "100644 9c4e0d8b2f1a3c4d5e6f7a8b9c0d1e2f3a4b5c6d 0\tscripts/foo.py"
    mode, path = _parse_ls_files_mode(line)
    assert path == "scripts/foo.py"
    assert mode != EXECUTABLE_MODE


@pytest.mark.parametrize(
    ("first_line", "expected"),
    [
        (UV_SCRIPT_SHEBANG, True),
        ("#!/usr/bin/env python3", False),
        ("\"\"\"A library module with no shebang.\"\"\"", False),
    ],
)
def test_is_uv_script_entrypoint_discriminates(
    tmp_path: Path, first_line: str, expected: bool
) -> None:
    """The shebang discriminant accepts only the uv-script first line."""
    script = tmp_path / "candidate.py"
    script.write_text(first_line + "\nprint('hello')\n", encoding="utf-8")
    assert _is_uv_script_entrypoint(script) is expected
