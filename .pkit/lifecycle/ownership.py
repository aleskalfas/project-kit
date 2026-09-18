"""Tier-ownership predicates the lifecycle layer owns (per COR-031 / ADR-051).

**Stdlib only at module level.** The packaging build hook loads this file by
path in an isolated build environment where third-party packages are not
importable, so every non-stdlib import must stay inside the function that
needs it (see :func:`_load_yaml`). `test_ownership_has_no_third_party_module_level_import`
enforces it.

**Propagated neutral code, not an area's content.** This module owns the
project's ownership questions — *is this path the kit's to manage, so an agent
may not claim write authority over it?* (:func:`is_sync_managed`) and *is this
path adopter-owned by tier alone?* (:func:`is_adopter_owned_by_tier`) — for
every consumer that needs one of them. Note the first despite its name: `pkit
sync` does not call it, and never has. Sync decides what it writes through the
copy path's own ownership handling; this predicate's one production consumer is
the ADR-051 write-authority guard. The name invited the other reading and cost
a misfiled report (#823), so read the question, not the identifier. The two are
deliberately distinct: the first additionally depends on capability
*registration* and treats everything outside `.pkit/` as not-its, so a caller
asking about tier must not read it off it. Each
answer has exactly one definition here; what matters is that no consumer
re-derives either, not that there is only one question. It lives here (in-tree,
propagated) rather than in `src/project_kit/`
for the reason ADR-003 records: an adapter's deploy resolver runs *in the
adopter's tree*, where the global `pkit` runtime is not importable. Code both
the backbone CLI and a propagated adapter script can import is the only home
that keeps **one** definition of each. ADR-051 requires exactly that: a
per-adapter re-derivation would fork the ownership predicate and silently skip
the check on any future harness. The packaging build hook is the same lesson at
a different altitude — the wheel manifest carried its own idea of which paths
were adopter-owned, disagreed with this module, and nothing could notice
(#813).

Dependency direction is inward, as in ADR-003: the backbone CLI imports this,
each adapter's resolver imports this, and this module imports neither.

:func:`is_sync_managed` is *conservative under `.pkit/`*: everything the kit tree
holds reads as the kit's unless it falls in an enumerated adopter-owned
carve-out. A false "not the kit's" is the costlier error — it hands an agent
write authority over content the next refresh overwrites — which is why the
bias points this way. But the other direction was understated here as costing
only "a rejected overlay entry the adopter can re-point": when the misjudged
path is the adopter's *own* file, there is nowhere else to point and they are
locked out of it (#823). The bias stays; it is only safe while the map is right
about the adopter's tier.

Not to be confused with `capabilities._is_kit_propagated_path`, which answers a
different question (*is this text kit's own example prose?*, for citation
scanning) and deliberately ignores capability origin.
"""

from __future__ import annotations

from pathlib import Path

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

def _load_yaml(text: str):
    """Parse YAML, importing the parser lazily.

    Deliberately not a module-level import. The tier predicate
    (:func:`is_adopter_owned_by_tier`) is pure string logic, and the packaging
    build hook loads this module in an isolated build environment where no
    third-party runtime dependency is installed. Only the manifest read below
    needs a parser, so only that path pays for one — a pure predicate should not
    require a YAML library to import.
    """
    from ruamel.yaml import YAML  # lazy by design — see the docstring above

    return YAML(typ="safe").load(text)


# --- the predicates ----------------------------------------------------------

def is_adopter_owned_by_tier(rel_posix: str) -> bool:
    """True when a `.pkit/`-relative path is adopter-owned *by tier alone*.

    The registration-independent half of :func:`is_sync_managed`: it answers
    "does this path sit on the project side of the no-shared-files split?"
    without consulting any manifest, any origin, or any adopter's tree.

    Two consumers need exactly this, and they must not disagree:

    * **Packaging.** A distribution may carry kit-owned capability *source* (a
      distribution medium, ADR-033) but must never carry the source project's
      own project-side state — that is how one project's config, activation
      switches and audit journals reached every adopter (#811 / #812).
    * **The test that keeps packaging honest**, which asserts the built
      distribution contains no such path.

    Why not `is_sync_managed` for those two: it also returns False for
    everything *outside* `.pkit/` (so `src/`, which legitimately ships, reads as
    "not managed"), and for capability content whose origin is unregistered —
    neither of which is a statement about tier. A packaging rule keyed on it
    would either reject legitimate content or depend on the build machine's
    manifest state.

    `rel_posix` is a FILE path relative to `.pkit/` (e.g.
    `capabilities/pm/project/x.yaml`). That precondition is load-bearing: the
    depth-free `project/` case reads every part *except the last*, so handing
    it a directory path that names the tier itself — `agents/project` —
    answers False, while the bare top-level `project` answers True through an
    earlier case. (Other cases do read the final part: `rules/project.md` and
    the top-level-file set are matched by name, and `scratchpad/active`
    answers True as a directory. The precondition is about the `project/`
    case, which is the one a packaging caller leans on.) A
    caller asking "is this directory the adopter's tier?" is asking a
    different question and must not use this predicate to answer it.
    """
    parts = [p for p in rel_posix.strip("/").split("/") if p]
    if not parts:
        return False
    # Adopter-owned top-level files (install state, version pin, .gitignore).
    if len(parts) == 1 and parts[0] in _ADOPTER_OWNED_KIT_FILES:
        return True
    # `.pkit/project/` and `.pkit/<area>/project/`.
    if parts[0] == "project":
        return True
    if parts[0] == "rules" and len(parts) > 1 and parts[1] == "project.md":
        return True
    if parts[0] == "scratchpad" and len(parts) > 1 and parts[1] in _SCRATCHPAD_STATE_DIRS:
        return True
    # A `project/` directory ANYWHERE under `.pkit/` is the adopter tier. Depth
    # is not part of the rule: today that covers `<area>/project/` (depth 1),
    # `capabilities/<name>/project/` (depth 2) and
    # `adapters/<harness>/settings/project/` (depth 3), and it will cover
    # whatever nesting an area adopts next without another edit here.
    #
    # This was originally written as two positional cases and MISSED the
    # depth-3 adapter settings — so the wheel kept shipping this project's own
    # permission allow-list (`Bash(uv:*)`, `Bash(ruff:*)`, …) into every
    # adopter, the exact defect #813 exists to close, while the sdist's
    # `**/project` glob excluded it. Two artifacts of one version disagreeing by
    # rule is how the miss surfaced. The Claude Code adapter's own README
    # (`.pkit/adapters/claude-code/README.md`, not the area-level one) is
    # explicit that this tier is "the adopter's project-specific additions".
    if "project" in parts[:-1]:
        return True
    return False


# The adopter's tier, declared by POSITION. Depth is not the rule (#823) — and
# neither is the bare presence of a `project` component. The boundary is a
# property of where the copy paths draw their ownership line, and they draw it
# at exactly these five places — keep this list and the tuple below in step:
#
#   `install.py` `_install_area`     -> `.pkit/project/`, `.pkit/<area>/project/`
#                                       (`project` is in its unconditional
#                                       `_handled` set, for EVERY area including
#                                       `adapters`)
#   `install.py` component registry  -> `.pkit/adapters/<harness>/project/`, the
#                                       per-component manifest it writes there
#                                       (the component registry writes it;
#                                       `upgrade.py` reads it)
#   `install.py` `_install_adapter`  -> the adapter settings pair (seeded on init,
#                                       never written on sync)
#   `capabilities.py` `_capability_owned` -> a capability's TOP-LEVEL `project/`,
#                                       pinned verbatim by ADR-012 Decision 2
#
# A `project/` component at no declared position sits inside a kit-owned refresh
# root — `<area>/core/`, `<area>/_defs/`, or below a capability's top level — and
# is overwritten and orphan-pruned like any other kit content. Calling such a
# path the adopter's would hand an agent write authority over content the next
# refresh deletes. Note this is about *position*, not nesting depth: the adapter
# entries above are deep and are still the adopter's.
#
# Each position is pinned by `test_the_two_predicates_agree_on_paths_this_repo_does
# _not_have`, which declares its paths rather than discovering them — so deleting
# an entry here fails a test rather than silently narrowing the adopter's tier.
# That test exists because the real-tree walk could not see the adapter positions:
# project-kit is the source repo and has no `.pkit/adapters/<name>/project/`.
#
# Why enumeration rather than a depth-free `"project" in parts` test: under that
# test `agents/core/project/notes.md` carries two tier markers claiming opposite
# owners, so COR-001's exactly-one-owner invariant needs a precedence rule — and
# no precedence rule reproduces the copy paths. First-marker-wins gets
# `agents/core/project/` right and `capabilities/pm/schemas/project/` wrong;
# last-marker-wins gets both wrong. An enumeration cannot contradict itself.
_ADOPTER_TIER_DIRS: tuple[tuple[str, ...], ...] = (
    ("project",),
    ("*", "project"),                          # `.pkit/<area>/project/`, adapters included
    ("capabilities", "*", "project"),
    ("adapters", "*", "project"),              # per-component manifest (install.py)
    ("adapters", "*", "settings", "project"),
)

# `("*", "project")` must not swallow `capabilities`, whose second component is a
# capability NAME rather than an area subdir; `("capabilities", "*", "project")`
# above states that position properly. Adapters are deliberately NOT excluded:
# an earlier revision skipped them too and thereby *narrowed* the tier, flipping
# `.pkit/adapters/project/` from the adopter's to the kit's — the #823 defect one
# directory over. `_install_area` puts `project` in its unconditional `_handled`
# set for every area including `adapters`, so the kit never writes or prunes
# there, and COR-003 gives every area a `project/` sibling. A hypothetical
# adapter *named* `project` would collide with the area tier; the methodology's
# own convention is what forbids that name, not this rule.
_AREAS_EXCLUDED_FROM_WILDCARD: frozenset[str] = frozenset({"capabilities"})


def _on_adopter_tier(parts: list[str]) -> bool:
    """True when *parts* names an adopter tier directory, or anything inside it.

    *parts* is a `.pkit/`-relative component list. Matching is by **prefix**, so
    the tier directory itself answers True as well as its contents — which the
    write-authority consumer needs, since overlay entries are usually
    directories rather than files.
    """
    for pattern in _ADOPTER_TIER_DIRS:
        if len(parts) < len(pattern):
            continue
        if pattern == ("*", "project") and parts[0] in _AREAS_EXCLUDED_FROM_WILDCARD:
            continue
        if all(want in ("*", have) for want, have in zip(pattern, parts)):
            return True
    return False


def is_sync_managed(target_root: Path | str, raw_path: str) -> bool:
    """True when *raw_path* is kit-owned content the adopter must not claim.

    **Despite the name, `pkit sync` does not call this.** Sync decides what it
    writes through the copy path's own ownership handling — adopter-owned files
    are seeded only when absent and never overwritten — so a wrong answer here
    does not put an adopter's file at risk. The one production consumer is the
    agent-overlay write-authority check (ADR-051): a write-carrying category may
    not name content the kit owns.

    That matters because the name misleads in a specific, costly way. #823 was
    filed as "sync will overwrite the adopter's settings", reasoning from this
    name and this docstring; the measured consequence was the opposite — an
    adopter locked out of granting write authority over their own file. Read
    this as *is this the kit's to manage?*, and when reporting a defect in it,
    measure the consumer rather than the name.

    *raw_path* is an overlay entry as written — target-root-relative (the normal
    form), absolute, with or without a trailing slash. An entry that resolves
    outside the tree is not sync-managed (it is simply not the kit's).

    The tier map, in the order it is applied:

    - Anything outside `.pkit/` — adopter territory, never propagated.
    - The adopter tier at any of its **declared positions** (`_ADOPTER_TIER_DIRS`,
      checked before the capabilities branch below, which is why that branch's
      own `project/` case is now an unreachable restatement) — `.pkit/project/`,
      `.pkit/<area>/project/` (adapters included),
      `.pkit/capabilities/<name>/project/`,
      `.pkit/adapters/<harness>/project/` (the per-component manifest) and
      `.pkit/adapters/<harness>/settings/project/` — plus
      `.pkit/rules/project.md`, `.pkit/scratchpad/{active,done,dropped}/` and
      the adopter-owned top-level files above: the project side of the
      no-shared-files split (COR-001). A `project/` component elsewhere is
      *inside* a kit-owned refresh root and is not the adopter's.
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
    # The adopter tier, by POSITION. Checked before the capabilities dispatch, so
    # `capabilities/<name>/project/` is answered here rather than there. What keeps
    # a capability literally *named* `project` from being misread is not the
    # ordering — that is what exposes it — but `_AREAS_EXCLUDED_FROM_WILDCARD`
    # holding `capabilities` out of the `("*", "project")` pattern.
    if _on_adopter_tier(parts[1:]):
        return False
    if parts[1] == "capabilities":
        return _capability_path_is_sync_managed(root, parts)
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
    # Unreachable today: `_on_adopter_tier` answers `capabilities/<name>/project/`
    # before `is_sync_managed` dispatches here. Kept as a local restatement of the
    # invariant, so a future reordering cannot silently drop it — and deliberately
    # NOT widened past the top level, which ADR-012 D2 pins as the capability rule.
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
        data = _load_yaml(manifest.read_text(encoding="utf-8")) or {}
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
