"""Tier-ownership predicates the lifecycle layer owns (per COR-031 / ADR-051).

**Propagated neutral code, not an area's content.** This module answers one
question — *does `pkit sync` manage this path?* — for every consumer that needs
it, and it lives here (in-tree, propagated) rather than in `src/project_kit/`
for the reason ADR-003 records: an adapter's deploy resolver runs *in the
adopter's tree*, where the global `pkit` runtime is not importable. Code both
the backbone CLI and a propagated adapter script can import is the only home
that keeps **one** definition of sync-managed-ness. ADR-051 requires exactly
that: a per-adapter re-derivation would fork the ownership predicate and
silently skip the check on any future harness.

Dependency direction is inward, as in ADR-003: the backbone CLI imports this,
each adapter's resolver imports this, and this module imports neither.

The predicate is *conservative under `.pkit/`*: everything the kit tree holds
reads as sync-managed unless it falls in an enumerated adopter-owned carve-out.
That direction is the safe one — a false "managed" costs a rejected overlay
entry the adopter can re-point, while a false "not managed" hands an agent write
authority over content the next `pkit sync` overwrites.

Not to be confused with `capabilities._is_kit_propagated_path`, which answers a
different question (*is this text kit's own example prose?*, for citation
scanning) and deliberately ignores capability origin.
"""

from __future__ import annotations

from pathlib import Path

from ruamel.yaml import YAML

# Capability origin (COR-031), duplicated from the lifecycle vocabulary as plain
# strings so this module stays import-free. These are wire values in
# `.pkit/manifest.yaml`, not internal constants — they cannot drift without a
# manifest schema change.
ORIGIN_KIT_SHIPPED = "kit-shipped"
ORIGIN_INCUBATED_IN_REPO = "incubated-in-repo"

# Overlay categories a **core** record introduces that carry *write* authority
# (they appear in a core agent's `owns:`) and name paths only the adopter can
# enumerate. Three properties follow from that, and every consumer reads them
# from here:
#
#   1. Entries are checked against `is_sync_managed` — the no-shared-files
#      invariant at the agent surface (ADR-051 Decision point 2).
#   2. The category has **no conventional default**: core cannot guess an
#      adopter's layout, so `pkit agents adopt` cannot serve it and the honest
#      remediation is `pkit agents reconcile --write` (ADR-051 Implications).
#   3. It ships as an explicit empty list, which resolves to an empty `owns:`
#      and deploys the agent **inert** (a bare or absent key does not resolve
#      and the agent is skipped instead).
#
# Single-consumer by convention (ADR-051 Decision point 7): each entry here is
# referenced by exactly the one agent whose record introduced it. A *core* agent
# citing a write-carrying category some other record introduced is a review-time
# red flag. Adopter-defined categories are not listed here and stay the
# adopter's to share across their own agents.
WRITE_CARRYING_CATEGORIES: frozenset[str] = frozenset({
    "process-authoring-targets",  # ADR-051 — the `process-author` agent's teeth
})

# Adopter-owned files that sit directly under `.pkit/` rather than inside an
# area's `project/` tree. Each is written by the lifecycle or by the adopter,
# never propagated from kit source, so the conservative default below must not
# claim them.
_ADOPTER_OWNED_KIT_FILES: frozenset[str] = frozenset({
    "manifest.yaml",   # install-state: recorded backbone version + registry.
    "version-pin",     # the adopter's per-project version pin (ADR-049).
    ".gitignore",      # regenerated per-adopter from runtime_ignore (ADR-009).
})

# Scratchpad state folders are adopter-owned per COR-012: init stubs them, sync
# never touches their contents.
_SCRATCHPAD_STATE_DIRS: frozenset[str] = frozenset({"active", "done", "dropped"})

_yaml = YAML(typ="safe")


# --- the predicate -----------------------------------------------------------

def is_sync_managed(target_root: Path | str, raw_path: str) -> bool:
    """True when `pkit sync` propagates over *raw_path* in *target_root*.

    *raw_path* is an overlay entry as written — target-root-relative (the normal
    form), absolute, with or without a trailing slash. An entry that resolves
    outside the tree is not sync-managed (it is simply not the kit's).

    The tier map, in the order it is applied:

    - Anything outside `.pkit/` — adopter territory, never propagated.
    - `.pkit/project/`, `.pkit/<area>/project/`, `.pkit/rules/project.md`,
      `.pkit/scratchpad/{active,done,dropped}/` and the adopter-owned top-level
      files above — the project side of the no-shared-files split (COR-001).
    - `.pkit/capabilities/<name>/project/` — adopter-owned **by tier**, so
      admissible even when the capability itself is kit-shipped (ADR-051).
    - `.pkit/capabilities/<name>/…` otherwise — sync-managed only when the
      capability is *registered* with origin `kit-shipped`. An
      `incubated-in-repo` capability is the adopter's own (COR-031 D1), and one
      that is **not registered at all** — a just-authored subtree in the
      bootstrap window — has nothing managing it either.
    - Everything else under `.pkit/` — sync-managed (core areas included).
    """
    root = Path(target_root)
    rel = _relative_posix(root, raw_path)
    if rel is None:
        return False

    parts = rel.split("/")
    if parts[0] != ".pkit":
        return False
    if len(parts) == 1:
        return False  # `.pkit` itself is a container, not content.

    if len(parts) == 2 and parts[1] in _ADOPTER_OWNED_KIT_FILES:
        return False
    if parts[1] == "project":
        return False  # `.pkit/project/` — the adopter's own config tree.
    if parts[1] == "capabilities":
        return _capability_path_is_sync_managed(root, parts)
    if len(parts) >= 3 and parts[2] == "project":
        return False  # `.pkit/<area>/project/` — the project side of every area.
    if rel == ".pkit/rules/project.md":
        return False  # adopter-authored sibling of the propagated core.md.
    if parts[1] == "scratchpad" and len(parts) >= 3 and parts[2] in _SCRATCHPAD_STATE_DIRS:
        return False
    return True


def sync_managed_offences(
    target_root: Path | str, category: str, values: list[str]
) -> list[str]:
    """The entries of *category* that resolve into sync-managed content.

    Empty for a category that is not write-carrying: the constraint exists to
    protect *write* authority, and an agent legitimately *reads* kit-shipped
    paths through a read-carrying category.
    """
    if category not in WRITE_CARRYING_CATEGORIES:
        return []
    return [v for v in values if is_sync_managed(target_root, v)]


# --- messages ----------------------------------------------------------------
#
# Message text lives beside the predicate so every harness's resolver reports
# the same rejection in the same words, for the same reason the predicate is
# shared: a per-adapter copy drifts.

def rejection_message(category: str, offences: list[str]) -> list[str]:
    """Lines explaining why *offences* cannot appear in *category*.

    First line is the one-line reason (a resolver may use it as a status);
    the rest is remediation.
    """
    listed = ", ".join(offences)
    return [
        f"category <{category}> names sync-managed path(s): {listed}",
        f"<{category}> grants write authority, so it may name only paths "
        f"`pkit sync` does not overwrite.",
        "Fix: point the category at your own definition files and predicate-script",
        "     locations — an incubated capability's subtree, or the `project/` tree",
        "     inside a kit-shipped one — in .pkit/agents/project/overlay.yaml,",
        "     then re-run `pkit sync`.",
    ]


def undefined_category_remediation(category: str) -> list[str] | None:
    """Remediation lines for an *undefined* write-carrying category, or None.

    None means "this category has a conventional default; the generic
    `pkit agents adopt` advice applies". For a write-carrying category it never
    does — core cannot enumerate the adopter's paths, so there is nothing for
    `adopt` to create (ADR-051 Implications).
    """
    if category not in WRITE_CARRYING_CATEGORIES:
        return None
    return [
        f"`pkit agents adopt` cannot serve <{category}> — it names paths only you",
        "can enumerate, so there is no conventional default to create.",
        "Fix: run `pkit agents reconcile --write` (it fills the category with an",
        "     empty list — the agent then deploys inert), then list your own paths",
        "     in .pkit/agents/project/overlay.yaml and re-run `pkit sync`.",
    ]


# --- internals ---------------------------------------------------------------

def _relative_posix(root: Path, raw_path: str) -> str | None:
    """Normalise an overlay entry to a root-relative POSIX path, or None.

    None when the entry is empty or resolves outside *root* — in either case
    there is nothing in the kit tree for sync to manage.
    """
    text = raw_path.strip()
    if not text:
        return None
    candidate = Path(text)
    if candidate.is_absolute():
        try:
            candidate = candidate.resolve().relative_to(root.resolve())
        except (ValueError, OSError):
            return None
    # Collapse `.` / `..` lexically rather than on disk: an overlay entry names
    # a location, which need not exist yet (a predicate directory the author is
    # about to create still has an owner).
    parts: list[str] = []
    for part in candidate.parts:
        if part in (".", ""):
            continue
        if part == "..":
            if not parts:
                return None  # escapes the tree
            parts.pop()
            continue
        parts.append(part)
    if not parts:
        return None
    return "/".join(parts)


def _capability_path_is_sync_managed(root: Path, parts: list[str]) -> bool:
    """Origin-aware verdict for a path under `.pkit/capabilities/`."""
    if len(parts) < 3:
        return True  # `.pkit/capabilities/` itself — the kit-owned container.
    if len(parts) >= 4 and parts[3] == "project":
        return False  # adopter tier inside any capability, whatever its origin.
    origin = _registered_capability_origin(root, parts[2])
    if origin is None:
        return False  # not registered — nothing reconciles it against source.
    return origin == ORIGIN_KIT_SHIPPED


def _registered_capability_origin(root: Path, name: str) -> str | None:
    """A capability's recorded origin, or None when it is not registered.

    Reads the backbone manifest's component registry — lifecycle-owned
    install-state, which is where origin lives (COR-031 D2), never inside the
    capability's own subtree. The absent-origin default is `kit-shipped` (D2),
    but an absent *registration* is distinct and returns None: ADR-051 needs the
    bootstrap window (subtree authored, not yet registered) to read as
    adopter-owned, which the CLI's own `read_capability_origin` cannot express
    because it collapses both cases to `kit-shipped`.

    An unreadable manifest yields `kit-shipped` for every capability — the
    conservative direction, matching this module's bias.
    """
    manifest = root / ".pkit" / "manifest.yaml"
    if not manifest.is_file():
        return None
    try:
        data = _yaml.load(manifest.read_text(encoding="utf-8")) or {}
    except Exception:
        return ORIGIN_KIT_SHIPPED
    if not isinstance(data, dict):
        return ORIGIN_KIT_SHIPPED
    components = data.get("components") or []
    if not isinstance(components, list):
        return ORIGIN_KIT_SHIPPED
    for entry in components:
        if not isinstance(entry, dict):
            continue
        if entry.get("kind") != "capability" or str(entry.get("name", "")) != name:
            continue
        return str(entry.get("origin", ORIGIN_KIT_SHIPPED))
    return None
