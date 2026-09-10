"""Build hook: the distribution carries no adopter-owned path (#813).

The methodology tree is bundled into the wheel by `force-include` (ADR-033), and
hatchling's `exclude` **cannot filter force-included paths** — force-include is
the higher-priority mechanism. So eleven `.pkit/` trees were included wholesale
(see `FILTERED_TREES`), carrying every adopter-owned `project/` subtree they
held. In this repo that meant project-kit's own config, its default-agent
activation switch, its bootstrap stamp, its per-issue audit journals (#811) —
and, at a depth the first version of the tier predicate did not reach, its own
harness permission allow-list at `adapters/<harness>/settings/project/`
(`Bash(uv:*)`, `Bash(ruff:*)`, …), which is why the rule is now depth-free.

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
own ownership predicate. Those eleven trees are dropped from the static
`force-include` in `pyproject.toml` and rebuilt here, file by file, skipping
anything `ownership.is_adopter_owned_by_tier` calls adopter-owned. One rule, and
`tests/test_packaging_boundary.py` asserts the built artifacts against that same
function **and against each other** — the cross-artifact check being the one
that can catch a hole in the predicate itself, which a per-artifact check
structurally cannot.
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
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
# Adopter-tier directories whose EXISTENCE the installer reads. `install.py`
# stubs an adopter's `project/` tier only when the source bundle has that
# directory — `if (src / "project").is_dir()` for an area, and
# `if project_src.is_dir()` for an adapter's settings pair — so the bundle must
# carry each one even though every file inside is withheld.
#
# DECLARED, not discovered. Deriving this from the filesystem breaks the build
# path that matters most: the sdist prunes `**/project`, so a wheel built FROM
# an sdist (what `pip install` does with a source distribution) finds no such
# directory and emits no markers — and the scaffolding regression returns
# silently. A declared tuple lives in the code, which is in both artifacts, so
# both build paths emit the same set. `tests/test_packaging_boundary.py` asserts
# the tuple against the source tree so it cannot drift into fiction.
ADOPTER_TIER_MARKERS: tuple[str, ...] = (
    "agents/project",
    "permissions/project",
    "skills/project",
    "adapters/claude-code/settings/project",
)

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
    """Force-include every wholesale-bundled `.pkit/` tree, minus adopter-owned paths.

    Scope is `FILTERED_TREES` below — eleven trees, not capabilities alone.
    """

    PLUGIN_NAME = "pkit-capability-boundary"

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        ownership = _load_ownership()
        is_adopter_owned = ownership.is_adopter_owned_by_tier

        include: dict[str, str] = {}
        withheld = 0
        for tree in FILTERED_TREES:
            base = KIT / tree
            if not base.is_dir():
                # Fail loudly. Skipping silently would drop an entire tree from
                # the distribution while the hook still reported success — the
                # exact failure mode this change was made to end, and one this
                # hook hit twice during development.
                raise RuntimeError(
                    f"hatch_build: .pkit/{tree} is listed in FILTERED_TREES but "
                    "is not a directory. Either the tree was renamed (update the "
                    "tuple) or the checkout is incomplete; shipping a wheel "
                    "missing that tree silently is not an option."
                )
            for path in sorted(base.rglob("*")):
                if not path.is_file():
                    continue
                rel_parts = path.relative_to(KIT).parts
                # Scoped to the kit tree: matching `path.parts` would also test
                # directories ABOVE the repo root, so a checkout under a
                # directory named `__pycache__` would silently bundle nothing.
                if EXCLUDED_PARTS & set(rel_parts):
                    continue
                if path.suffix in EXCLUDED_SUFFIXES:
                    continue
                rel_to_kit = path.relative_to(KIT).as_posix()
                if is_adopter_owned(rel_to_kit):
                    withheld += 1
                    continue
                include[str(path)] = f"{DEST_ROOT}/{rel_to_kit}"

        # A per-file force-include can only ship FILES, so a directory whose
        # every file was withheld disappears from the bundle entirely. That is
        # not cosmetic: `install.py` gates the adopter-side `project/`
        # scaffolding on `(src / "project").is_dir()`, reading the bundle's
        # shape as a proxy for "does this area have a project tier?". Losing the
        # directory silently stopped the official install from stubbing
        # `.pkit/<area>/project/` at all — a regression the file-level tests
        # could not see, since they assert file presence.
        #
        # So ship the directory's *existence* while still withholding its
        # contents: an empty marker per fully-withheld directory. The marker is
        # kit-owned layout, not adopter data, and it never reaches an adopter —
        # the area install path skips `project` when copying and only stubs it.
        # Derived from `ADOPTER_TIER_MARKERS` — the directories `install.py`
        # gates on — never from where withheld files happened to sit.
        #
        # The first version collected the parent of every withheld file, and
        # withheld files include git-IGNORED ones, so a marker materialised
        # purely from build-machine state: this tree produced 419 `_kit`
        # entries against 418 from a clean clone of the same commit, the delta
        # being a marker for `project/process/issue-lifecycle/` — a directory
        # that exists locally only because of untracked journals. That broke the
        # reproducibility obligation THIS CHANGE-SET records in ADR-033, and it
        # materialised the source's nested adopter-tier layout, which #812
        # explicitly rejects ("nested structure is the adopter's to create").
        #
        # Depth is NOT the rule: the tuple deliberately includes
        # `adapters/claude-code/settings/project` at depth 3, because
        # `install.py` gates that adapter's settings scaffolding on it. An
        # earlier revision of this comment claimed depth-1 was "the whole
        # requirement" — a reader trusting that would delete the depth-3 entry
        # as spurious and silently restore the scaffolding regression. Every
        # declared directory carries tracked content, so the marker set is a
        # function of tracked state alone.
        represented = {str(Path(dest).parent) for dest in include.values()}
        pending = [
            rel_dir for rel_dir in ADOPTER_TIER_MARKERS
            if f"{DEST_ROOT}/{rel_dir}" not in represented
        ]
        if pending:
            # One distinct source file per destination: hatchling keys
            # force_include by source path, so a shared marker would collide.
            marker_dir = Path(tempfile.mkdtemp(prefix="pkit-boundary-"))
            for rel_dir in pending:
                marker = marker_dir / (rel_dir.replace("/", "_") + ".gitkeep")
                marker.write_text("", encoding="utf-8")
                include[str(marker)] = f"{DEST_ROOT}/{rel_dir}/.gitkeep"

        build_data.setdefault("force_include", {}).update(include)
        self.app.display_info(
            f"pkit packaging boundary: {len(include)} file(s) bundled from "
            f"{len(FILTERED_TREES)} tree(s), {withheld} adopter-owned path(s) withheld"
        )
