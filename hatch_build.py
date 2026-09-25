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

One carve-out, and the title line above is the rule it bends: the bundle does
carry an empty `.gitkeep` at each declared adopter-tier directory
(`ADOPTER_TIER_MARKERS`). `install.py` reads the bundle's *shape* — not merely
its contents — to decide whether to stub an adopter's `project/` tier, and a
per-file force-include ships no directory whose every file was withheld, so
withholding the contents alone silently killed that scaffolding. The markers
restore the shape while keeping the contents out: kit-owned layout rather than
adopter data, asserted byte-empty by the same test module, and never copied to
an adopter. ADR-033 D1 records the exception.

**Tracked state, not the filesystem (#909).** Filtering by tier was not enough
for the reproducibility claim: the walk still took every file it FOUND, so an
untracked, non-ignored file in a local checkout — an editor backup, a stray
`.DS_Store` — shipped. In a git work tree the hook therefore enumerates what git
TRACKS (`git ls-files`, i.e. the index), and it does so for the sdist too, which
until then walked the tree the same way. A wheel built FROM an sdist has no
`.git` and walks the unpacked tree — correct only because the sdist it walks was
itself assembled from tracked files. That is why the sdist is covered here
rather than left to its `exclude` glob: the default `uv build` / `python -m
build` path builds the wheel from the sdist, so an sdist that carried a stray
would hand it to the wheel. A `.git` without a working `git` fails the build
rather than falling back to the walk; see `_tracked_paths`. A tree with neither
a `.git` nor an sdist's `PKG-INFO` builds, with a warning; see
`_untracked_source_warning`.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

ROOT = Path(__file__).parent
KIT = ROOT / ".pkit"
DEST_ROOT = "project_kit/_kit"

# The `.pkit/` subtrees this hook force-includes, replacing the static entries in
# `pyproject.toml`. Membership is about HOW a tree is bundled, not about what it
# holds: a tree belongs here when the bundle takes it WHOLESALE, so something has
# to filter it file by file. `decisions` and `scratchpad` also hold adopter-owned
# content and are deliberately absent — `pyproject.toml` enumerates their
# kit-owned paths individually (`decisions/core`, `decisions/README.md`,
# `scratchpad/README.md`), which excludes the adopter's paths by construction.
# Adding one here would include it twice, by two mechanisms writing the same
# destinations — the duplication this hook exists to remove.
# A WHOLESALE tree left in the static list ships unfiltered — that is the bug.
# Note the criterion is not "has a `project/` subdirectory": `rules` has none
# and is a member because of `rules/project.md`.
#
# `decisions/core` is the one member below the top level. It is bundled
# wholesale, so it is the same case: as a static directory force-include it
# shipped whatever file sat in it, tracked or not (#909). The static list now
# names single tracked files only.
FILTERED_TREES: tuple[str, ...] = (
    "decisions/core",
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

# Build caches must never ride along. `pyproject.toml`'s `exclude` cannot help:
# it filters only the standard package walk, not force-included paths — which is
# the whole reason this hook exists — so a per-file force-include has to apply
# the same patterns itself. Missing this shipped 87 `.pyc` files on the first
# attempt, trading 41 unwanted files for 87 different ones.
EXCLUDED_PARTS: frozenset[str] = frozenset({"__pycache__", ".pytest_cache"})
EXCLUDED_SUFFIXES: tuple[str, ...] = (".pyc", ".pyo")

# The sdist's `.pkit/` entries, like the wheel's kit trees, are force-included
# by this hook — `pyproject.toml` excludes `/.pkit` from the sdist's own walk
# and declares what to withhold under this hook-config key.
SDIST_WITHHOLD_KEY = "withhold"

# Written at the root of every sdist by the build backend, so its presence is
# how a `.git`-less tree is recognised as an unpacked sdist.
SDIST_METADATA_FILE = "PKG-INFO"

# git's refusal when the repository's owner uid differs from the caller's
# (CVE-2022-24765). Matched on stderr because the exit code, 128, is git's
# generic fatal status.
GIT_DUBIOUS_OWNERSHIP = "dubious ownership"


def _tracked_paths(root: Path) -> frozenset[str] | None:
    """Root-relative POSIX paths git tracks under `.pkit/`, or `None` outside a work tree.

    `None` means "no tracked state to consult": `root` has no `.git` of its own,
    which is the case when building a wheel from an unpacked sdist. The caller
    then walks the tree as found — sound because the sdist was assembled from
    tracked files by this same hook. Only `root/.git` counts, never an
    ancestor's: an sdist unpacked somewhere inside another repository must not
    be filtered against that repository's index. `.git` may be a file (a linked
    worktree or a submodule); `exists()` covers both.

    A `.git` whose `git` cannot answer FAILS the build. Falling back to the walk
    would silently restore the defect this function exists to close, in exactly
    the situation — a local checkout — where untracked files are likely. That
    holds for git's "dubious ownership" refusal too, which gets its own message
    because its cause (a checkout owned by another uid: a CI container, a Docker
    volume mount, `sudo pip install`) and its remedy are not guessable from
    git's text alone. There is deliberately no environment variable to skip the
    check; the remedy is git's own `safe.directory`.
    """
    if not (root / ".git").exists():
        return None
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z", "--", ".pkit"],
            capture_output=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"hatch_build: {root} is a git work tree but `git` is not on PATH. The "
            "bundle is built from tracked files only, and walking the tree instead "
            "would ship untracked ones; install git or build from an sdist."
        ) from exc
    if proc.returncode != 0:
        stderr = proc.stderr.decode(errors="replace").strip()
        if GIT_DUBIOUS_OWNERSHIP in stderr:
            raise RuntimeError(
                f"hatch_build: git refuses to read {root}: the checkout is owned by "
                "a different user than the one building (common in CI containers, "
                "Docker volume mounts and `sudo pip install`). The bundle is built "
                "from tracked files only, so the build cannot proceed without git. "
                "Mark the checkout safe and rebuild: "
                f"git config --global --add safe.directory {root}\n"
                f"git said: {stderr}"
            )
        raise RuntimeError(
            f"hatch_build: `git ls-files` failed in {root} (exit {proc.returncode}): "
            f"{stderr}"
        )
    return frozenset(p for p in proc.stdout.decode("utf-8").split("\0") if p)


def _untracked_source_warning(root: Path) -> str | None:
    """The warning for a build whose tree is neither a work tree nor an sdist.

    With no `root/.git`, `_tracked_paths` has no index to consult and the tree
    is walked as found. That is sound only for a tree assembled from tracked
    files: an unpacked sdist, or a `git archive` / "Download ZIP" tarball. It
    is silently unsound for a Docker context whose `.dockerignore` drops
    `.git`, a vendored copy, or a `cp -r` that left `.git` behind — each can
    carry untracked files into the bundle.

    Every sdist carries a `PKG-INFO` at its root, so that case stays quiet. The
    rest cannot be told apart (a `git archive` tarball has neither marker), so
    this warns rather than fails: git-archive builds are legitimate.
    """
    if (root / ".git").exists() or (root / SDIST_METADATA_FILE).is_file():
        return None
    return (
        f"pkit packaging boundary: {root} has no `.git` and no `{SDIST_METADATA_FILE}`, "
        "so `.pkit/` is bundled from the tree as found rather than from tracked "
        "files. Untracked files present in it may ship. Build from a git work "
        "tree or an sdist to rule that out."
    )


def _shippable_files(
    base: Path, *, root: Path, tracked: frozenset[str] | None
) -> Iterator[Path]:
    """Every file under `base` a build may carry, in sorted order.

    Tracked files only when `tracked` is given, else the tree as found; build
    caches never. Membership is tested on the walked path rather than by
    iterating `tracked`, so a file deleted from the work tree but still in the
    index is skipped instead of failing the build.
    """
    for path in sorted(base.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        # Scoped to the project root: matching `path.parts` would also test
        # directories ABOVE it, so a checkout under a directory named
        # `__pycache__` would silently bundle nothing.
        if EXCLUDED_PARTS & set(rel.parts):
            continue
        if path.suffix in EXCLUDED_SUFFIXES:
            continue
        if tracked is not None and rel.as_posix() not in tracked:
            continue
        yield path


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

    Wheel scope is `FILTERED_TREES` above, not capabilities alone. The sole
    thing shipped at an adopter-owned path is an empty structural marker per
    `ADOPTER_TIER_MARKERS` entry, so the installer can still read the bundle's
    shape. Registered on the sdist target too, where it force-includes the
    `.pkit/` tree from tracked files (#909); see `_initialize_sdist`.
    """

    PLUGIN_NAME = "pkit-capability-boundary"

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        tracked = _tracked_paths(ROOT)
        warning = _untracked_source_warning(ROOT)
        if warning is not None:
            self.app.display_warning(warning)
        if self.target_name == "sdist":
            self._initialize_sdist(tracked, build_data)
        else:
            self._initialize_wheel(tracked, build_data)

    def _initialize_sdist(
        self, tracked: frozenset[str] | None, build_data: dict[str, Any]
    ) -> None:
        """Force-include `.pkit/` into the sdist from tracked files, minus `withhold`.

        The sdist's own walk cannot do this: hatchling takes every file it finds
        that the root `.gitignore` does not match, so an untracked file shipped,
        and a wheel built from that sdist then shipped it too. So
        `pyproject.toml` excludes `/.pkit` from the walk and this re-adds the
        tree. The withhold globs stay in `pyproject.toml`, applied here with the
        same `pathspec` engine hatchling uses for `exclude`.

        Globs by CHOICE, not necessity: this hook could call
        `is_adopter_owned_by_tier` here exactly as the wheel does. It does not,
        so that the sdist keeps a filter of its own — the independent oracle
        `tests/test_packaging_boundary.py` compares the wheel against. Do not
        "simplify" this into the predicate; that would delete the check which
        caught a hole in the predicate. What the two targets now SHARE is the
        enumeration (`_tracked_paths` / `_shippable_files`), so the comparison
        cannot see an enumeration defect —
        `test_untracked_file_ships_in_no_artifact` is the external check there.
        """
        import pathspec  # declared in `[build-system] requires`

        globs = self.config.get(SDIST_WITHHOLD_KEY, [])
        if not isinstance(globs, list) or not all(isinstance(g, str) for g in globs):
            raise TypeError(
                f"hatch_build: sdist hook option `{SDIST_WITHHOLD_KEY}` must be a "
                "list of strings"
            )
        withhold = pathspec.GitIgnoreSpec.from_lines(globs)

        include: dict[str, str] = {}
        withheld = 0
        for path in _shippable_files(KIT, root=ROOT, tracked=tracked):
            rel = path.relative_to(ROOT).as_posix()
            if withhold.match_file(rel):
                withheld += 1
                continue
            include[str(path)] = rel

        build_data.setdefault("force_include", {}).update(include)
        source = "tracked files" if tracked is not None else "the unpacked tree"
        self.app.display_info(
            f"pkit packaging boundary (sdist): {len(include)} .pkit file(s) from "
            f"{source}, {withheld} withheld"
        )

    def _initialize_wheel(
        self, tracked: frozenset[str] | None, build_data: dict[str, Any]
    ) -> None:
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
            for path in _shippable_files(base, root=ROOT, tracked=tracked):
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
            rel_dir
            for rel_dir in ADOPTER_TIER_MARKERS
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
