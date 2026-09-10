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
import re
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


def test_ownership_has_no_third_party_module_level_import() -> None:
    """The build hook loads this module in an isolated build environment with no
    third-party dependency installed, so a module-level third-party import fails
    the build outright — as `ruamel.yaml` did.

    Checked structurally rather than by grepping for `ruamel`: a textual search
    for one library name would pass while a future `import click` broke the
    build in precisely the way this test exists to prevent. Every module-level
    import must resolve to the standard library.
    """
    import ast
    import sys

    source = (KIT / "lifecycle" / "ownership.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    roots: list[str] = []
    for node in tree.body:  # module level only — nested imports are the point
        if isinstance(node, ast.Import):
            roots += [a.name.split(".")[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.append(node.module.split(".")[0])
    third_party = sorted(
        r for r in set(roots)
        if r not in sys.stdlib_module_names and r != "__future__"
    )
    assert not third_party, (
        f"module-level third-party import(s) would break the build hook: {third_party}"
    )


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
    # One representative per filtered tree, so a tree dropped from the hook's
    # list — or an over-broad predicate — fails loudly rather than shipping a
    # hollow wheel. Previously this covered 5 of the 11 trees.
    required = {
        "capabilities": "capabilities/project-management/schemas/issue-types.yaml",
        "agents": "agents/core/critic.md",
        "permissions": "permissions/decide.py",
        "adapters": "adapters/claude-code/deploy-skills.sh",
        "skills": "skills/core/decision-author.md",
        "rules": "rules/core.md",
        "schemas": "schemas/README.md",
        "cli": "cli/README.md",
        "process": "process/README.md",
        "lifecycle": "lifecycle/ownership.py",
        "migrations": "migrations/backbone/README.md",
        # Statically force-included, not hook-filtered — covered so a change to
        # the static list is caught here too.
        "decisions": "decisions/core/COR-001-content-mechanisms.md",
        "VERSION": "VERSION",
    }
    missing = {tree: rel for tree, rel in required.items() if rel not in entries}
    assert not missing, f"kit-owned content missing from the distribution: {missing}"


def test_every_kit_tree_is_accounted_for() -> None:
    """Closes the gap the split enumeration opens.

    The packaging surface now lives in two places — `pyproject.toml`'s static
    force-include list and `hatch_build.py`'s `FILTERED_TREES`. A newly added
    top-level `.pkit/` entry that lands in neither silently never ships. This
    asserts every one is deliberately handled: hook-filtered, statically
    included, or adopter-owned.
    """
    import tomllib

    hook_trees = set(
        re.findall(
            r'^\s*"(\w[\w-]*)",',
            (REPO_ROOT / "hatch_build.py").read_text(),
            re.MULTILINE,  # without this the pattern matches nothing at all
        )
    )
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    static = pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]
    static_tops = {Path(k).relative_to(".pkit").parts[0] for k in static if k.startswith(".pkit/")}

    # Deliberately not shipped, recorded here so they are decisions rather than
    # silent omissions — and so that anything NEW failing this test is a real
    # finding. Both predate this change (neither was in the old static list).
    #   release/   — maintainer release tooling; an adopter never runs it.
    #   README.md  — the tree's own index. Arguably SHOULD ship, since an
    #                adopter's `.pkit/` is otherwise unexplained; left as-is
    #                because adding it is a packaging change of its own.
    not_shipped = {"release", "README.md"}

    ownership = _ownership()
    unaccounted = []
    for entry in sorted(KIT.iterdir()):
        name = entry.name
        if name in {"__pycache__", ".gitignore"} or name in not_shipped:
            continue
        if name in hook_trees or name in static_tops:
            continue
        if ownership.is_adopter_owned_by_tier(name):
            continue
        unaccounted.append(name)
    assert not unaccounted, (
        "top-level .pkit/ entries in neither the hook's FILTERED_TREES nor "
        f"pyproject's force-include, and not adopter-owned: {unaccounted}"
    )
