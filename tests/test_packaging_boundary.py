"""The distribution carries no adopter-owned path (#813).

`pyproject.toml` bundles the methodology tree with `force-include`, and
hatchling's `exclude` cannot filter force-included paths. So the trees were
included wholesale, carrying each capability's adopter-owned `project/` subtree —
which seeded one project's state into every adopter (#811 / #812) and, because
some of that content is git-ignored, made the artifact depend on whatever
untracked state sat on the build machine.

`hatch_build.py` now rebuilds those force-includes file by file, asking
`.pkit/lifecycle/ownership.py`. These tests assert the *result* against the same
predicate, so the packaging manifest cannot drift from the rule again — which it
had already done once, since `ownership.py` knew a capability's `project/` tree
was adopter-owned while the packaging manifest did not.
"""

from __future__ import annotations

import importlib.util
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
KIT = REPO_ROOT / ".pkit"
BUILD_CACHE_PARTS = {"__pycache__", ".pytest_cache"}


def _ownership():
    """Load the ownership module by path — it is methodology content, not a
    package, and the build hook loads it the same way."""
    spec = importlib.util.spec_from_file_location(
        "_ownership_under_test", KIT / "lifecycle" / "ownership.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def ownership():
    return _ownership()


# --- the predicate the hook and these tests share ---------------------------


@pytest.mark.parametrize(
    "rel,expected",
    [
        ("capabilities/project-management/project/config.yaml", True),
        ("capabilities/project-management/project/process/1.journal.jsonl", True),
        ("capabilities/project-management/project/adapter-overlays/claude-code.json", True),
        # Kit-owned content inside the same capability still ships.
        ("capabilities/project-management/schemas/issue-types.yaml", False),
        ("capabilities/project-management/scripts/create-issue.py", False),
        # The template an adopter opts in with is kit-owned; the live copy is not.
        ("capabilities/project-management/adapters/claude-code/overlay.template.json", False),
        ("agents/project/overlay.yaml", True),
        ("agents/core/critic.md", False),
        ("rules/project.md", True),
        ("rules/core.md", False),
        ("decisions/project/PRJ-001-x.md", True),
        ("decisions/core/COR-001-x.md", False),
        ("scratchpad/active/note.md", True),
        ("scratchpad/README.md", False),
        ("manifest.yaml", True),
        ("VERSION", False),
    ],
)
def test_tier_predicate(ownership, rel: str, expected: bool) -> None:
    assert ownership.is_adopter_owned_by_tier(rel) is expected


def test_predicate_imports_without_a_yaml_parser() -> None:
    """The build hook loads this module in an isolated build environment where
    no third-party runtime dependency is installed, so the import must not
    require one. A module-level `ruamel.yaml` import failed the build."""
    source = (KIT / "lifecycle" / "ownership.py").read_text(encoding="utf-8")
    top_level = [
        line for line in source.splitlines()
        if line.startswith(("import ", "from ")) and "ruamel" in line
    ]
    assert not top_level, f"ruamel must be imported lazily, found: {top_level}"


# --- the built artifact ------------------------------------------------------


@pytest.fixture(scope="module")
def built_wheel(tmp_path_factory) -> Path:
    """Build a real wheel. Skipped when no builder is available, rather than
    silently asserting nothing."""
    import shutil
    import subprocess

    uv = shutil.which("uv")
    if uv is None:
        pytest.skip("uv not available to build a wheel")
    out = tmp_path_factory.mktemp("wheel")
    proc = subprocess.run(
        [uv, "build", "--wheel", "--out-dir", str(out)],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=600,
    )
    if proc.returncode != 0:
        pytest.fail(f"wheel build failed:\n{proc.stdout}\n{proc.stderr}")
    wheels = list(out.glob("*.whl"))
    assert len(wheels) == 1, wheels
    return wheels[0]


def _kit_entries(wheel: Path) -> list[str]:
    names = zipfile.ZipFile(wheel).namelist()
    return [n.split("/_kit/", 1)[1] for n in names if "/_kit/" in n and not n.endswith("/")]


def test_no_adopter_owned_path_ships(ownership, built_wheel: Path) -> None:
    """The load-bearing assertion: the manifest cannot drift from the rule."""
    offenders = sorted(
        rel for rel in _kit_entries(built_wheel)
        if ownership.is_adopter_owned_by_tier(rel)
    )
    assert not offenders, (
        f"{len(offenders)} adopter-owned path(s) in the distribution: {offenders[:10]}"
    )


def test_no_build_cache_ships(built_wheel: Path) -> None:
    """A per-file force-include bypasses `pyproject.toml`'s `exclude`, so the
    hook applies the patterns itself. Missing this shipped 87 `.pyc` files."""
    names = zipfile.ZipFile(built_wheel).namelist()
    cached = [n for n in names if BUILD_CACHE_PARTS & set(Path(n).parts) or n.endswith((".pyc", ".pyo"))]
    assert not cached, f"build cache in the distribution: {cached[:10]}"


def test_kit_owned_content_still_ships(built_wheel: Path) -> None:
    """Guards the inverse failure: filtering that removes too much.

    A representative path from each filtered tree, so an over-broad predicate or
    a tree dropped from the hook's list fails loudly instead of shipping a
    hollow wheel.
    """
    entries = set(_kit_entries(built_wheel))
    required = [
        "capabilities/project-management/schemas/issue-types.yaml",
        "capabilities/project-management/scripts/create-issue.py",
        "agents/core/critic.md",
        "rules/core.md",
        "skills/core/decision-author.md",
        "lifecycle/ownership.py",
        "decisions/core/COR-001-content-mechanisms.md",
        "VERSION",
    ]
    missing = [r for r in required if r not in entries]
    assert not missing, f"kit-owned content missing from the distribution: {missing}"
