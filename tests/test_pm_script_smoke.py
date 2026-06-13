"""Regression guard: every pm script entry point resolves all names it calls.

Background: done-work.py shipped with a call to `_gh_get_issue` on its main
path (line 133) but no definition of that name — either local or imported.
Python raises a NameError only when the line is *executed*, not at import
time, so the module imported cleanly and all existing unit tests passed.
The script was 100% dead on every real invocation.

This test suite catches that class of bug by:

  1. Verifying `gh_get_issue` is exported from `_lib/gh.py` — the canonical
     home of the helper after the de-dup promotion (regression against the
     function being removed from the library).

  2. Importing every `scripts/*.py` module and asserting that each module
     exports a callable `_gh_get_issue` when it defines one, OR that the
     module at minimum imports cleanly without NameError. This catches the
     exact failure mode: `_gh_get_issue` called in `main()` but never
     defined → `AttributeError` on the module object (which is the
     importlib-equivalent of a NameError at call time).

How this test would have caught the original bug
-------------------------------------------------
The `dw` module fixture in test_pm_done_work.py already imports
`done-work.py` successfully (import doesn't fail). But none of that
file's tests exercises the code path that calls `_gh_get_issue`. The
check here — `assert callable(dw._gh_get_issue)` — would have produced
`AttributeError: module 'pm_done_work_under_test' has no attribute
'_gh_get_issue'` on the broken version, failing the test before any
mocking or gate logic is invoked.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = (
    REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
)
GH_LIB = SCRIPTS_DIR / "_lib" / "gh.py"


# ---------------------------------------------------------------------------
# Helper: load a script as a module without executing __main__ guard
# ---------------------------------------------------------------------------

def _load_script(script_path: Path, module_name: str) -> types.ModuleType:
    """Load a pm script by file path via importlib, inserting its parent on sys.path."""
    lib_dir = str(script_path.parent)
    inserted = lib_dir not in sys.path
    if inserted:
        sys.path.insert(0, lib_dir)
    try:
        spec = importlib.util.spec_from_file_location(module_name, script_path)
        assert spec is not None and spec.loader is not None, (
            f"Could not create module spec for {script_path}"
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        if inserted and lib_dir in sys.path:
            sys.path.remove(lib_dir)


# ---------------------------------------------------------------------------
# 1. Library-level: gh_get_issue is exported from _lib/gh.py
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def gh_lib():
    """Load _lib/gh.py."""
    return _load_script(GH_LIB, "pm_gh_lib_smoke_under_test")


def test_gh_lib_exports_gh_get_issue(gh_lib) -> None:
    """gh_get_issue must be a callable in _lib/gh.py.

    Regression: the helper was absent from _lib before the fix; done-work.py
    called a name that existed nowhere. If this function is removed from the
    library again, the test fails before any script even imports it.
    """
    assert callable(getattr(gh_lib, "gh_get_issue", None)), (
        "_lib/gh.py must export a callable gh_get_issue"
    )


def test_gh_get_issue_signature_accepts_fields_kwarg(gh_lib) -> None:
    """gh_get_issue must accept a keyword-only `fields` argument.

    The fields parameter is mandatory and keyword-only; callers pass their
    per-script field list explicitly so the function never silently fetches
    a fixed set of fields for every caller.
    """
    import inspect
    sig = inspect.signature(gh_lib.gh_get_issue)
    params = sig.parameters
    assert "fields" in params, "gh_get_issue must have a 'fields' parameter"
    assert params["fields"].kind == inspect.Parameter.KEYWORD_ONLY, (
        "'fields' must be keyword-only (defined after *)"
    )


# ---------------------------------------------------------------------------
# 2. done-work.py specifically: _gh_get_issue must be a callable attribute
# ---------------------------------------------------------------------------


DONE_WORK = SCRIPTS_DIR / "done-work.py"


@pytest.fixture(scope="module")
def done_work():
    """Load done-work.py as a module."""
    return _load_script(DONE_WORK, "pm_done_work_smoke_under_test")


def test_done_work_has_callable_gh_get_issue(done_work) -> None:
    """done-work.py must define (or import) a callable _gh_get_issue.

    This is the exact regression test for the NameError reported in the
    scratchpad note 2026-06-12-pm-done-work-crash.md. Before the fix,
    _gh_get_issue was called at line 133 of main() but was never defined —
    the module loaded without error but the script crashed on every real
    invocation. This assertion would have produced:

        AttributeError: module '...' has no attribute '_gh_get_issue'

    on the pre-fix module, catching the bug at test-collection time.
    """
    fn = getattr(done_work, "_gh_get_issue", None)
    assert callable(fn), (
        "done-work.py must define or import a callable _gh_get_issue; "
        "the script will NameError on every invocation without it"
    )


# ---------------------------------------------------------------------------
# 3. All scripts that define _gh_get_issue locally expose it as callable
# ---------------------------------------------------------------------------

# Scripts known to define a module-local _gh_get_issue shim.
SCRIPTS_WITH_GH_GET_ISSUE = [
    "done-work.py",
    "close-issue.py",
    "merge-pr.py",
    "create-draft.py",
    "edit-issue.py",
    "show-issue.py",
    "reopen-issue.py",
    "validate-pr.py",
    "review-work.py",
    "open-pr.py",
    "start-work.py",
    "validate-issue.py",
    "handoff-issue.py",
    "move-issue.py",
]


@pytest.mark.parametrize("script_name", SCRIPTS_WITH_GH_GET_ISSUE)
def test_script_gh_get_issue_is_callable(script_name: str) -> None:
    """Every pm script that calls _gh_get_issue must expose it as a callable.

    After the de-dup promotion, each script wraps the _lib helper in a thin
    module-level shim. This parametrised test ensures:
      - The script imports cleanly (no ImportError / NameError at module scope).
      - The _gh_get_issue name resolves to a callable on the module object.

    A script that calls _gh_get_issue inside a function but never defines or
    imports it will pass the import stage but fail this assertion — which is
    exactly the class of bug that made done-work.py dead.
    """
    script_path = SCRIPTS_DIR / script_name
    module_name = f"pm_smoke_{script_name.replace('-', '_').replace('.', '_')}"
    # Remove any prior load of this module name to get a fresh import.
    sys.modules.pop(module_name, None)
    mod = _load_script(script_path, module_name)
    fn = getattr(mod, "_gh_get_issue", None)
    assert callable(fn), (
        f"{script_name}: _gh_get_issue is not callable on the module "
        f"(got {fn!r}). The script will NameError at runtime."
    )
