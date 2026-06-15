"""Smoke guard: every pm script entry point can start.

Background
----------
done-work.py shipped with a call to `_gh_get_issue` on its main path but no
definition of that name — Python raises a NameError only when the line is
*executed*, not at import time, so the module imported cleanly and all
existing unit tests passed. The script was 100% dead on every real invocation.

This module guards against the whole class of dead-main-path bugs by running
each entry point under `sys.executable --help` as a subprocess. Reaching
`--help` means:

  - Python loaded the file (no SyntaxError, no bad shebang)
  - All module-scope imports resolved (no ImportError / NameError at
    import time)
  - argparse built the parser (no NameError / AttributeError in the
    parser-construction code, which is unconditional in every script)
  - argparse printed help and exited 0 — no traceback on stderr

Enumeration is dynamic: the test globs `scripts/*.py` so a newly-added
script is automatically covered without touching this file.

`_lib/*.py` internals are smoke-imported separately to catch broken library
modules before any entry point even loads them.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import types
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = (
    REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
)
LIB_DIR = SCRIPTS_DIR / "_lib"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _script_id(script_path: Path) -> str:
    """Short test-id used in pytest parametrisation output."""
    return script_path.name


def _lib_id(lib_path: Path) -> str:
    return f"_lib/{lib_path.name}"


def _load_as_module(path: Path, module_name: str) -> types.ModuleType:
    """Import *path* via importlib, inserting its parent on sys.path.

    Used for _lib modules that don't have a CLI and can't be subprocess-tested
    via --help.  The scripts dir is inserted so relative `_lib.*` sub-imports
    inside the library module resolve correctly.
    """
    scripts_dir_str = str(SCRIPTS_DIR)
    inserted = scripts_dir_str not in sys.path
    if inserted:
        sys.path.insert(0, scripts_dir_str)
    try:
        spec = importlib.util.spec_from_file_location(module_name, path)
        assert spec is not None and spec.loader is not None, (
            f"Could not create module spec for {path}"
        )
        mod = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = mod
        spec.loader.exec_module(mod)
        return mod
    finally:
        if inserted and scripts_dir_str in sys.path:
            sys.path.remove(scripts_dir_str)


# ---------------------------------------------------------------------------
# Dynamic entry-point collection
# ---------------------------------------------------------------------------

# All *.py in scripts/ (not inside _lib/).
_ALL_ENTRY_POINTS: list[Path] = sorted(SCRIPTS_DIR.glob("*.py"))

# _lib internals — smoke-imported rather than subprocess-tested because they
# expose no CLI surface of their own.
_ALL_LIB_MODULES: list[Path] = sorted(LIB_DIR.glob("*.py"))


# ---------------------------------------------------------------------------
# 1. Entry-point smoke test: --help exits 0, no traceback on stderr
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("script", _ALL_ENTRY_POINTS, ids=_script_id)
def test_entry_point_help_exits_zero(script: Path) -> None:
    """Every script entry point must start cleanly when passed --help.

    The check proves the module imported (no ImportError / NameError at
    module scope), the parser built (no AttributeError in parser construction),
    and argparse exited 0.  A traceback on stderr or a non-zero exit code
    fails the test.

    Uses `sys.executable` (the uv virtualenv interpreter) directly so the
    test runs offline/sandboxed without `uv run --script` re-fetching deps.
    All scripts add their own directory to sys.path at runtime and depend
    only on packages already present in the test environment.
    """
    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        capture_output=True,
        text=True,
        timeout=30,
    )

    # Collect both streams for a useful failure message.
    detail = (
        f"\n--- stdout ---\n{result.stdout}"
        f"\n--- stderr ---\n{result.stderr}"
    )

    assert result.returncode == 0, (
        f"{script.name}: --help exited {result.returncode} (expected 0){detail}"
    )

    # Argparse --help must produce some output.
    assert result.stdout.strip(), (
        f"{script.name}: --help produced no stdout output{detail}"
    )

    # No traceback or NameError should appear in stderr.
    lowered_stderr = result.stderr.lower()
    assert "traceback" not in lowered_stderr, (
        f"{script.name}: traceback detected in stderr{detail}"
    )
    assert "nameerror" not in lowered_stderr, (
        f"{script.name}: NameError detected in stderr{detail}"
    )
    assert "importerror" not in lowered_stderr, (
        f"{script.name}: ImportError detected in stderr{detail}"
    )
    assert "modulenotfounderror" not in lowered_stderr, (
        f"{script.name}: ModuleNotFoundError detected in stderr{detail}"
    )


# ---------------------------------------------------------------------------
# 2. _lib internals: import succeeds without error
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("lib_module", _ALL_LIB_MODULES, ids=_lib_id)
def test_lib_module_imports_cleanly(lib_module: Path) -> None:
    """Every _lib module must import without raising any exception.

    These are internal helpers without a CLI.  A clean import proves that
    all their own imports resolve and that no module-scope code raises.
    """
    module_name = f"pm_lib_smoke_{lib_module.stem.replace('-', '_')}"
    # Evict any prior load so each parametrised run is independent.
    sys.modules.pop(module_name, None)
    # This will raise (and fail the test) on any ImportError / NameError.
    _load_as_module(lib_module, module_name)
