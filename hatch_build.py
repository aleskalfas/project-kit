"""Build hook: the distribution carries no adopter-owned path (#813).

The methodology tree is bundled into the wheel by `force-include` (ADR-033), and
hatchling's `exclude` **cannot filter force-included paths** — force-include is
the higher-priority mechanism. So `.pkit/capabilities` was included wholesale,
which carried each capability's adopter-owned `project/` subtree: in this repo
that meant project-kit's own config, its default-agent activation switch, its
bootstrap stamp and its per-issue audit journals (#811).

Two consequences, both real:

* Those files were then *seeded* into every adopter, which #812 fixed on the
  copy side. This hook fixes the packaging side, so the content is not merely
  un-copied but absent from the artifact.
* The journals are **git-ignored**, so what shipped depended on whatever
  untracked state sat on the build machine. Two builds of one commit differed:
  the released 1.149.0 wheel carries 14 journals; a wheel built from a working
  tree carried 36. **The distribution was not reproducible.**

Rather than enumerate what to keep — a hand-maintained list that has already
drifted once from the rule it was meant to mirror — this hook asks the project's
own ownership predicate. `.pkit/capabilities` is dropped from the static
`force-include` in `pyproject.toml` and rebuilt here, file by file, skipping
anything `ownership.is_adopter_owned_by_tier` calls adopter-owned. One rule, and
`tests/test_packaging_boundary.py` asserts the built artifact against the same
function, so the manifest cannot drift from the predicate again.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

ROOT = Path(__file__).parent
KIT = ROOT / ".pkit"
DEST_ROOT = "project_kit/_kit"

# The `.pkit/` subtrees this hook force-includes, replacing the static entries in
# `pyproject.toml`. Every tree that can contain an adopter-owned `project/`
# subdirectory belongs here; a tree left in the static list ships unfiltered.
FILTERED_TREES: tuple[str, ...] = (
    "capabilities",
    "agents",
    "permissions",
    "adapters",
    "skills",
    "rules",
    "schemas",
    "cli",
    "process",
    "lifecycle",
    "migrations",
)

# Build caches must never ride along. `pyproject.toml`'s `exclude` cannot help:
# it filters only the standard package walk, not force-included paths — which is
# the whole reason this hook exists — so a per-file force-include has to apply
# the same patterns itself. Missing this shipped 87 `.pyc` files on the first
# attempt, trading 41 unwanted files for 87 different ones.
EXCLUDED_PARTS: frozenset[str] = frozenset({"__pycache__", ".pytest_cache"})
EXCLUDED_SUFFIXES: tuple[str, ...] = (".pyc", ".pyo")


def _load_ownership():
    """Import `.pkit/lifecycle/ownership.py` by path.

    It is methodology content rather than an installed module, so it is not on
    `sys.path` at build time. Loading it by path is deliberate: the alternative
    is copying the tier rule into this file, which is the duplication the hook
    exists to avoid.
    """
    spec = importlib.util.spec_from_file_location(
        "_pkit_ownership_buildtime", KIT / "lifecycle" / "ownership.py"
    )
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise RuntimeError("cannot load .pkit/lifecycle/ownership.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class CapabilityBoundaryHook(BuildHookInterface):
    """Force-include capability source, minus every adopter-owned path."""

    PLUGIN_NAME = "pkit-capability-boundary"

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        ownership = _load_ownership()
        is_adopter_owned = ownership.is_adopter_owned_by_tier

        include: dict[str, str] = {}
        withheld = 0
        for tree in FILTERED_TREES:
            base = KIT / tree
            if not base.is_dir():
                continue
            for path in sorted(base.rglob("*")):
                if not path.is_file():
                    continue
                if EXCLUDED_PARTS & set(path.parts):
                    continue
                if path.suffix in EXCLUDED_SUFFIXES:
                    continue
                rel_to_kit = path.relative_to(KIT).as_posix()
                if is_adopter_owned(rel_to_kit):
                    withheld += 1
                    continue
                include[str(path)] = f"{DEST_ROOT}/{rel_to_kit}"

        build_data.setdefault("force_include", {}).update(include)
        self.app.display_info(
            f"pkit packaging boundary: {len(include)} file(s) bundled from "
            f"{len(FILTERED_TREES)} tree(s), {withheld} adopter-owned path(s) withheld"
        )
