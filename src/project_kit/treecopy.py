"""The ownership-aware tree-refresh primitive (COR-001).

A single, dependency-free place that implements the *destructive* half of
the no-shared-files invariant: refreshing a destination tree from a source
tree while **never overwriting or removing adopter-owned content**. Kit-owned
files are copied (overwriting) and kit-owned orphans pruned; adopter-owned
files are seeded only when absent and otherwise left untouched.

Why this exists: the seed-once / never-overwrite contract was previously
re-derived ad-hoc at each copy site, and one site (`_copy_capability_tree`)
reimplemented copy with a blanket `rmtree` + recopy and forgot the rule —
clobbering an adopter's customised `project/` files on every sync. Routing
the destructive copy paths through one primitive means a copy path can't
silently reimplement-and-forget the mechanic. (It does **not** centralise the
ownership *policy* — each caller still injects `is_owned` for its own root
and convention; this owns the mechanism, not the convention.)

Placement: this module depends only on the standard library so that both
`install` and `capabilities` import *down* into it, keeping the dependency
graph a clean DAG (no `capabilities -> install` edge).

Failure contract (intentional, recorded in the ADR): the refresh is **not
transactional** — a crash or permission error mid-refresh can leave kit-owned
content partially written, recoverable simply by re-running the refresh.
Adopter-owned content is *never* deleted before a copy and is never the
target of an overwrite, so a partial failure cannot destroy adopter data.
This is strictly safer than the prior `rmtree`-first posture, which could
leave the adopter with neither old nor new content.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path, PurePath

# A predicate over a path *relative to the copy root* — True iff that path is
# adopter-owned (the `project/` convention, positional per tier). The mechanic
# is convention-agnostic; the caller supplies the convention.
OwnershipPredicate = Callable[[PurePath], bool]


def refresh_owned_tree(
    source: Path,
    dest: Path,
    *,
    is_owned: OwnershipPredicate,
    exclude: frozenset[str] = frozenset(),
    dry_run: bool = False,
) -> None:
    """Refresh `dest` from `source`, preserving adopter-owned paths (COR-001).

    - **kit-owned source file** (`is_owned` False): copied with `shutil.copy2`
      (preserving mode/executable bit + mtime), overwriting any existing file.
    - **adopter-owned source file** (`is_owned` True): copied only when the
      destination is absent (seed-once); an existing adopter file is never
      overwritten.
    - **kit-owned dest file with no live source counterpart**: pruned (an
      orphan from a prior version, or an `exclude`d artifact).
    - **adopter-owned dest file**: never pruned, never overwritten.
    - emptied **kit-owned** directories are removed; adopter-owned directories
      are always kept.

    `exclude` is a set of copy-root-relative POSIX path strings to treat as
    *not shipped* — neither copied nor preserved as kit-owned (so a prior
    install's copy of an now-excluded artifact is pruned). This is the generic
    seam capability skip-state rides on; the primitive knows nothing of
    "skipped artifacts".

    `dry_run` short-circuits to a no-op (writes nothing), matching the
    behaviour of the callers' existing dry-run paths.
    """
    if dry_run:
        return

    source_dirs: set[PurePath] = set()
    source_files: dict[PurePath, Path] = {}
    for path in source.rglob("*"):
        rel = path.relative_to(source)
        if path.is_dir():
            source_dirs.add(rel)
        elif path.is_file():
            source_files[rel] = path

    # 1. Materialise the destination + every source directory (so empty
    #    source dirs are reproduced, matching shutil.copytree).
    dest.mkdir(parents=True, exist_ok=True)
    for rel in sorted(source_dirs):
        (dest / rel).mkdir(parents=True, exist_ok=True)

    # 2. Copy files. Adopter-owned files are seeded only when absent.
    for rel, src_path in source_files.items():
        if rel.as_posix() in exclude:
            continue
        target = dest / rel
        if is_owned(rel) and target.exists():
            continue  # seed-once: never overwrite adopter content
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, target)

    # 3. Prune kit-owned orphans: dest files with no live source counterpart
    #    (removed upstream, or excluded). Adopter-owned files are never pruned.
    for path in sorted(dest.rglob("*")):
        if not (path.is_file() or path.is_symlink()):
            continue
        rel = path.relative_to(dest)
        if is_owned(rel):
            continue
        shipped = rel in source_files and rel.as_posix() not in exclude
        if not shipped:
            path.unlink()

    # 4. Remove emptied kit-owned *orphan* directories, deepest first so a
    #    parent is seen as empty only after its pruned children are gone. A
    #    directory present in the source is kept even when empty (matching
    #    copytree); only dirs the source no longer ships are pruned.
    for path in sorted(dest.rglob("*"), reverse=True):
        if not path.is_dir():
            continue
        rel = path.relative_to(dest)
        if is_owned(rel) or rel in source_dirs:
            continue
        if not any(path.iterdir()):
            path.rmdir()


def nothing_owned(_rel: PurePath) -> bool:
    """Ownership predicate for a purely kit-owned tree — nothing is preserved.

    The refresh becomes a plain overwrite-and-prune (the equivalent of the
    prior `rmtree` + `copytree`, but never bulk-deleting before copying).
    """
    return False
