"""A test's copy of a folder of Python code leaves out `__pycache__` (#2745).

The suite runs in parallel workers, and a compiled file's temporary name lives for a moment.
A `shutil.copytree` that meets one stops the test with a `shutil.Error`, on a change that has
nothing to do with it. So every copy leaves `__pycache__` out, or its module lists the source
it names in `HOLDS_NO_PYTHON`. The guard reads each module's syntax tree, which cannot show
what a folder holds, so that list is a judgement. `DATA_FOLDERS` holds the part of it the
repository can answer for.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
TESTS = REPO / "tests"

_INSTEAD = (
    'pass `ignore=shutil.ignore_patterns("__pycache__")`, or list the source in '
    "`HOLDS_NO_PYTHON` if the folder it names holds no Python"
)

#: The repository's folders of data, where the sources in `HOLDS_NO_PYTHON` that a test does
#: not build itself come from.
DATA_FOLDERS = (
    ".pkit/capabilities/project-management/schemas",
    ".pkit/capabilities/project-management/templates",
    ".pkit/capabilities/visual-communication/libraries",
    ".pkit/permissions/profiles",
    "tests/fixtures/visual-communication",
)

#: The sources each module copies whole, as its calls write them: folders that hold no Python.
HOLDS_NO_PYTHON = {
    "test_data_points.py": {"os.environ[run_cache.CACHE_ENV]"},
    "test_migrations_check.py": {"tmp_path / '.pkit'"},
    "test_permission_hook.py": {"REPO / '.pkit' / 'permissions' / 'profiles'"},
    "test_permissions_cli.py": {"REPO / '.pkit' / 'permissions' / 'profiles'"},
    "test_pm_bootstrap.py": {"CAP_SRC / 'schemas'"},
    "test_pm_bootstrap_gate_integration.py": {"CAP_SRC / 'schemas'", "CAP_SRC / 'templates'"},
    "test_pm_closure_cascade_foreign_child.py": {"CAP_SRC / 'schemas'"},
    "test_pm_closure_cascade_native_child.py": {"CAP_SRC / 'schemas'"},
    "test_pm_decision_ids.py": {"CAPABILITY_ROOT / folder"},
    "test_pm_done_work.py": {"CAPABILITY_ROOT_DW / 'schemas'"},
    "test_pm_land_work.py": {"CAPABILITY / 'schemas'", "CAPABILITY / 'templates'", "clone.root"},
    "test_pm_lifecycle_classifier.py": {"CAP_SRC / 'schemas'"},
    "test_pm_seats.py": {"CAPABILITY / 'schemas'"},
    "test_pm_session_guard_integration.py": {"CAP_SRC / 'schemas'", "CAP_SRC / 'templates'"},
    "test_pm_use_case_citations.py": {"CAPABILITY_ROOT / folder"},
    "test_release.py": {"pending"},
    "test_schemas_authoring.py": {"tmp_path / '.pkit'"},
    "test_visual_communication_add.py": {"FOUNDATIONS", "TEST_PARTS", "built"},
    "test_visual_communication_checks.py": {
        "FOUNDATIONS",
        "root / PIECE_FOLDER",
        "root / 'visual/pieces/tags'",
    },
    "test_visual_communication_current_copy.py": {"root / PIECE_FOLDER"},
    "test_visual_communication_export.py": {"root / PIECE_FOLDER"},
    "test_visual_communication_code.py": {"TEST_PARTS"},
    "test_visual_communication_fingerprint.py": {"tmp_path / 'visual'"},
    "test_visual_communication_libraries.py": {"FOUNDATIONS", "built"},
    "test_visual_communication_look.py": {"PIECES"},
    "test_visual_communication_neutral.py": {"PIECES"},
    "test_visual_communication_pipeline.py": {"TESTS"},
    "test_visual_communication_release.py": {"FOUNDATIONS"},
    "test_visual_communication_render.py": {"TESTS"},
    "test_visual_communication_shipped_libraries.py": {
        "FOUNDATIONS",
        "built(folder, name)",
        "place(folder)",
    },
    "test_visual_communication_starter.py": {"PIECES", "location"},
    "test_visual_communication_tokens.py": {"TEST_BRAND", "TEST_EDITION", "edition", "naming"},
    "visual_communication_project.py": {"source"},
}


def _is_copytree(function: ast.expr) -> bool:
    return (isinstance(function, ast.Attribute) and function.attr == "copytree") or (
        isinstance(function, ast.Name) and function.id == "copytree"
    )


def _leaves_out_pycache(call: ast.Call) -> bool:
    return any(
        keyword.arg == "ignore" and "__pycache__" in ast.unparse(keyword.value)
        for keyword in call.keywords
    )


def _whole_copies(code: str) -> list[tuple[int, str]]:
    """The line and the source, as written, of each copy in `code` that keeps `__pycache__`."""
    return [
        (node.lineno, ast.unparse(node.args[0]) if node.args else "")
        for node in ast.walk(ast.parse(code))
        if isinstance(node, ast.Call) and _is_copytree(node.func) and not _leaves_out_pycache(node)
    ]


def _copies_by_module() -> dict[str, list[tuple[int, str]]]:
    """Each module's whole copies, under its name in `tests/`."""
    texts = {
        path.relative_to(TESTS).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(TESTS.rglob("*.py"))
    }
    return {name: _whole_copies(text) for name, text in texts.items() if "copytree" in text}


def test_the_detector_finds_a_copy_that_keeps_pycache_and_nothing_else() -> None:
    assert _whole_copies("shutil.copytree(CODE, target)") == [(1, "CODE")]
    assert _whole_copies("shutil.copytree(CODE / 'x', target, symlinks=True)") == [
        (1, "CODE / 'x'")
    ]
    assert _whole_copies("from shutil import copytree\ncopytree(CODE, target)") == [(2, "CODE")]
    assert _whole_copies("shutil.copytree(src=CODE, dst=target)") == [(1, "")]
    assert _whole_copies(
        'shutil.copytree(CODE, target, ignore=shutil.ignore_patterns("*.log"))'
    ) == [(1, "CODE")]
    for code in (
        'shutil.copytree(CODE, target, ignore=shutil.ignore_patterns("__pycache__"))',
        'shutil.copytree(CODE, target, ignore=shutil.ignore_patterns("*.log", "__pycache__"))',
        "shutil.copy(CODE, target)",
        "note = 'shutil.copytree(CODE, target)'",
    ):
        assert _whole_copies(code) == [], code


def test_no_copy_in_the_tests_keeps_pycache_in_a_folder_of_python() -> None:
    offenders = [
        f"{name}:{line}: {source}"
        for name, copies in _copies_by_module().items()
        for line, source in copies
        if source not in HOLDS_NO_PYTHON.get(name, ())
    ]
    assert not offenders, (
        "a copy may meet a compiled file another worker is writing:\n  "
        + "\n  ".join(offenders)
        + f"\n{_INSTEAD}."
    )


def test_every_source_listed_is_still_copied_whole() -> None:
    copies = _copies_by_module()
    stale = [
        f"{name}: {source}"
        for name, sources in sorted(HOLDS_NO_PYTHON.items())
        for source in sorted(sources)
        if source not in {copied for _, copied in copies.get(name, ())}
    ]
    assert not stale, "`HOLDS_NO_PYTHON` lists what no copy names:\n  " + "\n  ".join(stale)


@pytest.mark.parametrize("folder", DATA_FOLDERS)
def test_a_folder_of_data_holds_no_python(folder: str) -> None:
    root = REPO / folder
    assert root.is_dir()
    python = [path.relative_to(REPO).as_posix() for path in sorted(root.rglob("*.py"))]
    assert not python, f"each copy of {folder} must leave `__pycache__` out now: {python}"
