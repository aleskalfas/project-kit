"""The process-graph render (COR-038): a read-only view of the configured
cross-process topology, built ENTIRELY from declarations.

COR-038 settles that a project's whole cross-process wiring is made visible by
deriving the enforced edges from the `subprocess`/`cascade` blocks the engine
already owns and UNIONING them with the inert, annotated `depends_on` edges --
each edge expressible exactly one way, no edge both (the derive-don't-annotate
discipline, single source of truth, COR-006). This module is that render.

THE SAFETY POINT (COR-038, load-bearing). The render reads DECLARATIONS only.
It walks each installed process DEFINITION and reads its structure -- it never
resolves a live subject position, never runs a detection / gate / membership
predicate, never instantiates a `ProcessEngine` and never calls
`resolve_position` / `can_move` / `move` / `resolve_subprocess_outcome` /
`resolve_cascade_outcome`. Visibility, not enforcement: drawing the wiring must
not re-open the very cross-process position read the substrate forbids (a peer's
flapping mid-flight position, COR-033 P3). The test suite pins this by asserting
the engine's resolution methods are never invoked while a graph is built.

The graph is built ONCE (`build_graph`) from the definitions, then rendered many
ways (`render_*`). Every render reads the same immutable `Graph`; the filters and
presets (`apply_filters`) transform the edge set, never re-read reality.

Direction is stored once, canonically: an edge points in the DEPENDENCY
direction (the subscriber / owner -> the upstream it depends on / embeds /
folds). Each format renders that one stored direction its own way -- the
adjacency view labels each line with a per-direction glyph; `--flow` reorients to
the downstream (work-flows-this-way) reading; mermaid draws an arrow; `--json`
emits `from`/`to`. The canonical direction is never recomputed per format.

The four `depends_on` relations are ONLY annotated; `composed-subprocess` /
`aggregates` are ONLY derived -- COR-038's no-edge-is-both rule, made structural
here (a derived edge never carries a depends_on relation, and the depends_on
relations are never derived). `--json` is byte-stable: deterministic node + edge
ordering, no TTY styling (ADR-024's load-bearing invariant).
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from project_kit import cli_render
from project_kit.manifest import read_backbone_manifest
from project_kit.process import ProcessDefinition, ProcessError, load_definition

# A safe YAML loader for the declaration scan (mirrors the engine's own loader).
# The scan only reads `process.id` to discover addresses; `load_definition` does
# the authoritative parse of each definition's body.
_yaml = YAML(typ="safe")

# --- the relation vocabulary (COR-038) ------------------------------------

# Derived relations -- read from the `subprocess`/`cascade` declarations the
# engine owns (COR-038 point 2: composition/aggregation are DERIVED, never
# annotated). These never appear as a `depends_on` relation.
RELATION_COMPOSED = "composed-subprocess"  # from a state's `subprocess` block
RELATION_AGGREGATES = "aggregates"  # from the process's `cascade` block
DERIVED_RELATIONS = (RELATION_COMPOSED, RELATION_AGGREGATES)

# Annotated relations -- the closed `depends_on.relation` set (COR-038 point 2):
# exactly the edges the engine cannot already see. These never appear as a
# derived edge.
ANNOTATED_RELATIONS = (
    "informational",
    "gates-on-readiness",
    "triggered-by",
    "constrained-with",
)

SOURCE_DERIVED = "derived"
SOURCE_ANNOTATED = "annotated"

# Direction glyphs for the adjacency view (a per-edge line is read out- or
# in-edge, with a glyph naming the relation kind in that direction).
GLYPH_DEPENDS = "→ depends on"  # -> (gates-on-readiness / informational / constrained-with, out)
GLYPH_GATED_BY = "← gated by"  # <- (the dependency seen from the upstream, in)
GLYPH_EMBEDS = "⊃ embeds"  # composed-subprocess, out
GLYPH_EMBEDDED_BY = "⊂ embedded by"  # composed-subprocess, in
GLYPH_FOLDS = "⇄ folds"  # aggregates (cascade), bidirectional reading


@dataclass(frozen=True)
class Edge:
    """One directed connection in the configured topology.

    The canonical stored direction is the DEPENDENCY direction: `frm` is the
    subscriber / owner / parent and `to` is the upstream it depends on, embeds,
    or folds. `relation` + `mode` + `source` label it; `from_state` is the state
    the edge originates at (the `depends_on`-carrying state for an annotated
    edge, the `subprocess` state for a composed edge, or None for a process-level
    `cascade` aggregate). `why` is the human-readable reason a `depends_on`
    declares (None for a derived edge -- the block IS its own explanation).
    """

    frm: str
    to: str
    relation: str
    mode: str
    source: str
    from_state: str | None = None
    why: str | None = None

    @property
    def capability_from(self) -> str:
        return self.frm.split(":", 1)[0]

    @property
    def capability_to(self) -> str:
        return self.to.split(":", 1)[0]

    @property
    def crosses_capability(self) -> bool:
        """Whether the edge spans two capabilities (a cross-capability SEAM)."""
        return self.capability_from != self.capability_to

    def sort_key(self) -> tuple[str, str, str, str, str, str, str]:
        """Total order for byte-stable rendering -- by endpoints, then origin
        state, then relation/source/mode, then `why`.

        `why` is the final tie-breaker because it is the ONLY remaining field
        that can legally differ between two otherwise-identical entries: a state
        may declare two `depends_on` rows toward the same upstream with the same
        relation and mode but a different `why` (a legitimate authoring choice).
        Without `why` in the key those two edges collide and their relative order
        is unpinned, which would break `--json` byte-stability for that case.
        Normalising None->"" keeps the order total over the whole edge set."""
        return (
            self.frm,
            self.to,
            self.from_state or "",
            self.relation,
            self.source,
            self.mode,
            self.why or "",
        )


@dataclass(frozen=True)
class Skipped:
    """A discovered process address whose definition could not be loaded -- a
    duplicate / ambiguous id, an unreadable file, or any other `ProcessError`.

    Surfaced (never silently swallowed): a skipped definition contributes no
    edges, so without naming it the "trusted whole-workflow view" would lie --
    drawing a bare standalone node with no hint that its wiring is simply
    *unknown*. `reason` is the loader's own message."""

    address: str
    reason: str

    def sort_key(self) -> tuple[str, str]:
        return (self.address, self.reason)


@dataclass(frozen=True)
class Graph:
    """The configured cross-process topology, built once from the definitions.

    `nodes` is the sorted list of installed process addresses; `edges` is the
    sorted derived-union-annotated edge set. `skipped` names every discovered
    address whose definition failed to load (so a missing-wiring node is honestly
    flagged, not silently drawn as standalone). Immutable -- filters return a NEW
    `Graph` over a subset of edges, never mutate this one (and carry `skipped`
    through unchanged: a filter narrows the edge view, it does not change which
    definitions failed to load).
    """

    nodes: tuple[str, ...]
    edges: tuple[Edge, ...]
    skipped: tuple[Skipped, ...] = ()

    def out_edges(self, address: str) -> list[Edge]:
        return [e for e in self.edges if e.frm == address]

    def in_edges(self, address: str) -> list[Edge]:
        return [e for e in self.edges if e.to == address]


# --- building the graph (declarations only) -------------------------------


def discover_process_addresses(repo_root: Path) -> list[str]:
    """Find every installed process DEFINITION's `<capability>:<process-id>`
    address by scanning declarations -- never resolving reality.

    Walks each installed capability's `schemas/*.yaml` for a top-level
    `process:` block and reads its declared `id`. Capability order follows the
    backbone manifest (falling back to a filesystem scan when no manifest is
    present); within a capability, schema files iterate in lexicographic order.
    The result is sorted, so the node list is deterministic.
    """
    addresses: set[str] = set()
    for capability in _installed_capabilities(repo_root):
        schemas_dir = repo_root / ".pkit" / "capabilities" / capability / "schemas"
        if not schemas_dir.is_dir():
            continue
        for schema_yaml in sorted(schemas_dir.glob("*.yaml")):
            process_id = _read_process_id(schema_yaml)
            if process_id is not None:
                addresses.add(f"{capability}:{process_id}")
    return sorted(addresses)


def _installed_capabilities(repo_root: Path) -> list[str]:
    """The installed capability names, from the backbone manifest when present,
    else a filesystem scan of `.pkit/capabilities/`. Sorted for determinism."""
    backbone = read_backbone_manifest(repo_root)
    if backbone is not None:
        names = [c.name for c in backbone.components if c.kind == "capability"]
        if names:
            return sorted(names)
    caps_dir = repo_root / ".pkit" / "capabilities"
    if not caps_dir.is_dir():
        return []
    return sorted(p.name for p in caps_dir.iterdir() if p.is_dir())


def _read_process_id(schema_yaml: Path) -> str | None:
    """Read a schema file's top-level `process.id`, or None when the file holds
    no process block / is unreadable. A parse failure degrades to None rather
    than raising -- the scan is best-effort discovery."""
    try:
        raw = _yaml.load(schema_yaml.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(raw, dict):
        return None
    block = raw.get("process")
    if not isinstance(block, dict):
        return None
    process_id = block.get("id")
    return process_id if isinstance(process_id, str) and process_id else None


def build_graph(repo_root: Path, addresses: list[str] | None = None) -> Graph:
    """Build the configured topology from the installed process DEFINITIONS.

    Reads declarations only (COR-038's safety point): it loads each definition
    and reads its `subprocess` / `cascade` / `depends_on` structure -- it never
    instantiates a `ProcessEngine`, resolves a position, or runs a predicate.

    `addresses` defaults to every discovered process; pass a subset to scope the
    build (the node set is exactly the addresses built, plus any upstream an edge
    points at that is itself a known process address -- an edge to an
    uninstalled process is still drawn, so a dangling reference is visible).
    """
    if addresses is None:
        addresses = discover_process_addresses(repo_root)
    node_set = set(addresses)
    edges: list[Edge] = []
    skipped: list[Skipped] = []
    for address in addresses:
        try:
            definition = load_definition(repo_root, address)
        except ProcessError as exc:
            # A discovered address that fails to load (duplicate/ambiguous id,
            # unreadable file) is skipped rather than aborting the whole render
            # -- it still appears as a node, BUT we record WHY so the render can
            # flag it. A skip without a surfaced reason would let a missing-wiring
            # node masquerade as a genuinely standalone one (G5): the whole-
            # workflow view must not lie about a definition it simply could not
            # read.
            skipped.append(Skipped(address=address, reason=str(exc)))
            continue
        edges.extend(_edges_for(address, definition))
    # An edge may point at an upstream that was not in the built set (a
    # cross-capability dependency on a process outside the scope, or a dangling
    # reference). Surface those endpoints as nodes too, so the edge has both
    # ends visible.
    for edge in edges:
        node_set.add(edge.frm)
        node_set.add(edge.to)
    # De-dup defensively (a malformed definition could declare the same edge
    # twice); keep the first occurrence's order via the sort.
    unique = sorted(set(edges), key=Edge.sort_key)
    return Graph(
        nodes=tuple(sorted(node_set)),
        edges=tuple(unique),
        skipped=tuple(sorted(skipped, key=Skipped.sort_key)),
    )


def _edges_for(address: str, definition: ProcessDefinition) -> list[Edge]:
    """Compute one process's outgoing edges from its declarations.

    DERIVED edges (COR-038 point 2):
      - each `subprocess` state -> a `composed-subprocess` edge (the parent
        embeds the inner; canonical dependency direction parent -> inner).
      - the process's `cascade` block -> an `aggregates` edge (the parent folds
        the child's members; parent -> child).
    ANNOTATED edges:
      - each state's `depends_on` entry -> an edge with the declared
        relation / mode / why (subscriber -> upstream).

    Derived edges never carry a `depends_on` relation and annotated edges never
    carry a derived relation -- the no-edge-is-both rule, structural here.
    """
    edges: list[Edge] = []
    for state in definition.states:
        state_id = state.get("id")
        state_id = state_id if isinstance(state_id, str) else None

        # Derived: composition (COR-036). A `subprocess` state embeds an inner.
        subprocess = state.get("subprocess")
        if isinstance(subprocess, dict):
            runs = subprocess.get("runs")
            if isinstance(runs, str) and runs:
                edges.append(
                    Edge(
                        frm=address,
                        to=runs,
                        relation=RELATION_COMPOSED,
                        # Composition is an engine-resolved (pull) coupling.
                        mode="pull",
                        source=SOURCE_DERIVED,
                        from_state=state_id,
                    )
                )

        # Annotated: the inert `depends_on` list (COR-038). Read only the
        # well-formed entries; a malformed entry is a lint concern, not the
        # render's to enforce -- it is simply skipped so the render stays robust.
        depends_on = state.get("depends_on")
        if isinstance(depends_on, list):
            for entry in depends_on:
                edge = _annotated_edge(address, state_id, entry)
                if edge is not None:
                    edges.append(edge)

    # Derived: aggregation (COR-037). The process declares at most one cascade.
    cascade = definition.cascade
    if isinstance(cascade, dict):
        runs = cascade.get("runs")
        if isinstance(runs, str) and runs:
            edges.append(
                Edge(
                    frm=address,
                    to=runs,
                    relation=RELATION_AGGREGATES,
                    mode="pull",
                    source=SOURCE_DERIVED,
                    from_state=None,  # process-level, not a single state
                )
            )
    return edges


def _annotated_edge(
    address: str, state_id: str | None, entry: Any
) -> Edge | None:
    """Build one annotated edge from a `depends_on` entry, or None when the entry
    is malformed (missing upstream / relation / mode). A render is robust to a
    lint-failing definition: it skips the bad entry rather than raising."""
    if not isinstance(entry, dict):
        return None
    upstream = entry.get("upstream")
    relation = entry.get("relation")
    mode = entry.get("mode")
    if not isinstance(upstream, str) or not upstream:
        return None
    if relation not in ANNOTATED_RELATIONS:
        # Defensive: a relation outside the closed set (or a derived relation
        # wrongly annotated) is dropped -- the derive-don't-annotate rule means
        # composed/aggregates must never arrive here.
        return None
    if mode not in ("pull", "push"):
        return None
    why = entry.get("why")
    return Edge(
        frm=address,
        to=upstream,
        relation=str(relation),
        mode=str(mode),
        source=SOURCE_ANNOTATED,
        from_state=state_id,
        why=why if isinstance(why, str) and why else None,
    )


# --- filters + presets (COR-038's atomic filters, AND-combined) -----------


@dataclass(frozen=True)
class FilterSpec:
    """The resolved filter request -- atomic filters AND-combined, with presets
    pre-expanded into the same atomic fields (a preset is a documented named
    combination of atomics, never separate machinery).

    Each field is None / empty when unconstrained. `relations` / `modes` /
    `sources` are membership sets; `capability` / `process` scope to one
    endpoint; `direction` restricts to a focused process's out- or in-edges;
    `depth` bounds hops from the focused `process`. `seams_only` keeps only
    cross-capability edges; `upstream_of` / `downstream_of` take the transitive
    closure following dependency direction; `cycles_only` keeps edges that lie on
    a dependency cycle.

    `enforced` is the one constraint that is a UNION rather than an intersection
    (source:derived ∪ relation:gates-on-readiness -- the `--enforced` preset), so
    it is its own boolean applied as a union pre-filter, NOT a widening of the
    AND-combined `sources`/`relations` sets (which would intersect to empty).
    """

    capability: str | None = None
    process: str | None = None
    relations: frozenset[str] = frozenset()
    modes: frozenset[str] = frozenset()
    sources: frozenset[str] = frozenset()
    depth: int | None = None
    direction: str | None = None  # "in" | "out"
    seams_only: bool = False
    upstream_of: str | None = None
    downstream_of: str | None = None
    cycles_only: bool = False
    enforced: bool = False


def apply_filters(graph: Graph, spec: FilterSpec) -> Graph:
    """Return a new `Graph` whose edges satisfy EVERY constraint in `spec`
    (atomic filters AND-combine). The node list is recomputed to the endpoints
    the surviving edges touch (so a filtered view shows only the relevant nodes),
    plus a focused `--process` itself even when it has no surviving edge (so it
    is never silently dropped).
    """
    edges = list(graph.edges)

    # `enforced` is the OR-preset, applied FIRST as a union (source:derived ∪
    # relation:gates-on-readiness). It cannot ride the AND-combined membership
    # sets, so it is its own union pre-filter; the atomic filters below then
    # narrow whatever it kept.
    if spec.enforced:
        edges = [
            e
            for e in edges
            if e.source == SOURCE_DERIVED or e.relation == "gates-on-readiness"
        ]

    if spec.sources:
        edges = [e for e in edges if e.source in spec.sources]
    if spec.relations:
        edges = [e for e in edges if e.relation in spec.relations]
    if spec.modes:
        edges = [e for e in edges if e.mode in spec.modes]
    if spec.capability:
        edges = [
            e
            for e in edges
            if spec.capability in (e.capability_from, e.capability_to)
        ]
    if spec.seams_only:
        edges = [e for e in edges if e.crosses_capability]

    # Transitive closures (follow dependency direction). Computed against the
    # already-narrowed edge set so they compose with the atomic filters.
    if spec.upstream_of is not None:
        reachable = _closure(edges, spec.upstream_of, downstream=False)
        edges = [e for e in edges if e.frm in reachable and e.to in reachable]
    if spec.downstream_of is not None:
        reachable = _closure(edges, spec.downstream_of, downstream=True)
        edges = [e for e in edges if e.frm in reachable and e.to in reachable]

    # Focus on one process: direction + depth (hops from the focused process).
    if spec.process is not None:
        edges = _focus(edges, spec.process, spec.direction, spec.depth)

    if spec.cycles_only:
        on_cycle = _edges_on_cycle(edges)
        edges = [e for e in edges if e in on_cycle]

    node_set = {e.frm for e in edges} | {e.to for e in edges}
    if spec.process is not None and spec.process in graph.nodes:
        node_set.add(spec.process)
    # A directional/cycle closure can legally produce an empty edge set for a
    # leaf queried in its own direction (a node that depends on nothing for
    # --upstream-of, or that nothing depends on for --downstream-of). Re-add the
    # queried focus so it always renders as a standalone node rather than
    # vanishing into a blank graph (G1) -- mirroring the --process focus guard
    # above. _closure already seeds itself with `start`, so the address is known
    # to be reachable; we only need it to survive into the node set.
    for focus in (spec.upstream_of, spec.downstream_of):
        if focus is not None and focus in graph.nodes:
            node_set.add(focus)
    return Graph(
        nodes=tuple(sorted(node_set)),
        edges=tuple(sorted(edges, key=Edge.sort_key)),
        skipped=graph.skipped,
    )


def _focus(
    edges: list[Edge], process: str, direction: str | None, depth: int | None
) -> list[Edge]:
    """Keep edges within `depth` hops of `process`, optionally only out- or
    in-edges. `depth` counts hops along the dependency direction for an out
    focus and against it for an in focus; `None` depth means the full reachable
    set (BFS over every connected edge)."""
    out_adj: dict[str, list[Edge]] = defaultdict(list)
    in_adj: dict[str, list[Edge]] = defaultdict(list)
    for e in edges:
        out_adj[e.frm].append(e)
        in_adj[e.to].append(e)

    kept: set[Edge] = set()
    # BFS frontier of (node, hops). Direction "out" walks out_adj (this process
    # depends on ...), "in" walks in_adj (... depends on this process), and the
    # default (None) walks both.
    seen: set[str] = {process}
    frontier: list[tuple[str, int]] = [(process, 0)]
    while frontier:
        node, hops = frontier.pop()
        if depth is not None and hops >= depth:
            continue
        steps: list[Edge] = []
        if direction in (None, "out"):
            steps.extend(out_adj.get(node, []))
        if direction in (None, "in"):
            steps.extend(in_adj.get(node, []))
        for edge in steps:
            kept.add(edge)
            nxt = edge.to if edge.frm == node else edge.frm
            if nxt not in seen:
                seen.add(nxt)
                frontier.append((nxt, hops + 1))
    return [e for e in edges if e in kept]


def _closure(edges: list[Edge], start: str, *, downstream: bool) -> set[str]:
    """The transitive closure of nodes reachable from `start` following
    dependency direction. `downstream=False` (upstream-of): follow edges FROM
    each node to what it depends on -- the things `start` (transitively) depends
    upon. `downstream=True`: follow edges backwards -- the things that
    (transitively) depend on `start`."""
    adj: dict[str, list[str]] = defaultdict(list)
    for e in edges:
        if downstream:
            adj[e.to].append(e.frm)  # who depends on this node
        else:
            adj[e.frm].append(e.to)  # what this node depends on
    reachable: set[str] = {start}
    stack = [start]
    while stack:
        node = stack.pop()
        for nxt in adj.get(node, []):
            if nxt not in reachable:
                reachable.add(nxt)
                stack.append(nxt)
    return reachable


def _edges_on_cycle(edges: list[Edge]) -> set[Edge]:
    """The subset of edges lying on a dependency cycle (an edge whose `to` can
    reach its `frm` following dependency direction).

    Small-graph assumption (mirrors the cascade's own note): this runs one
    reachability search per edge, so O(E·(V+E)). The configured topology is a
    handful of processes, so a per-edge walk is the simplest correct thing. If
    the graph ever grows large, replace this with a single strongly-connected-
    components pass (Tarjan) -- every edge inside a non-trivial SCC, plus every
    self-loop, is on a cycle -- which collapses it to O(V+E)."""
    adj: dict[str, list[str]] = defaultdict(list)
    for e in edges:
        adj[e.frm].append(e.to)

    def reaches(src: str, dst: str) -> bool:
        seen = {src}
        stack = [src]
        while stack:
            node = stack.pop()
            for nxt in adj.get(node, []):
                if nxt == dst:
                    return True
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        return False

    return {e for e in edges if reaches(e.to, e.frm)}


# --- preset expansions (each is a documented named combo of atomics) ------

# COR-038 presets, expressed as the atomic filters they expand to. The help
# text surfaces each expansion so a preset is explainable, never magic. A preset
# layers ONTO any atomic filters the caller also passed (they AND-combine).
PRESET_HELP: dict[str, str] = {
    "enforced": "source:derived ∪ relation:gates-on-readiness (the edges that actually block)",
    "advisory": "relation:informational,triggered-by (no runtime block)",
    "seams": "cross-capability edges only (drop edges whose ends share a capability)",
    "connectors": "mode:push (externally/connector-mediated couplings)",
    "declared": "source:annotated (the inert depends_on layer)",
    "derived": "source:derived (the composition/aggregation layer)",
    "cycles": "edges lying on a dependency cycle",
}


def expand_presets(
    base: FilterSpec,
    *,
    enforced: bool = False,
    advisory: bool = False,
    seams: bool = False,
    connectors: bool = False,
    declared: bool = False,
    derived: bool = False,
    cycles: bool = False,
    upstream_of: str | None = None,
    downstream_of: str | None = None,
) -> FilterSpec:
    """Fold the requested presets into `base`, expanding each into its atomic
    fields (COR-038: a preset is a named combination, not separate machinery).

    `enforced` is the one preset that is a UNION of two atomic conditions
    (source:derived ∪ relation:gates-on-readiness) -- not expressible as a single
    intersection of the atomic membership sets, so it carries a dedicated OR
    predicate rather than widening `sources`/`relations` (which AND-combine).
    Every other preset is a pure widening of an atomic membership set or a
    boolean, so it folds straight in.
    """
    relations = set(base.relations)
    modes = set(base.modes)
    sources = set(base.sources)
    seams_only = base.seams_only
    cycles_only = base.cycles_only

    if advisory:
        relations |= {"informational", "triggered-by"}
    if connectors:
        modes |= {"push"}
    if declared:
        sources |= {SOURCE_ANNOTATED}
    if derived:
        sources |= {SOURCE_DERIVED}
    if seams:
        seams_only = True
    if cycles:
        cycles_only = True

    return FilterSpec(
        capability=base.capability,
        process=base.process,
        relations=frozenset(relations),
        modes=frozenset(modes),
        sources=frozenset(sources),
        depth=base.depth,
        direction=base.direction,
        seams_only=seams_only,
        upstream_of=upstream_of if upstream_of is not None else base.upstream_of,
        downstream_of=downstream_of
        if downstream_of is not None
        else base.downstream_of,
        cycles_only=cycles_only,
        # The OR-preset rides its own boolean (applied as a union pre-filter in
        # apply_filters), never the AND-combined `sources`/`relations` sets.
        enforced=enforced or base.enforced,
    )


# --- rendering ------------------------------------------------------------


def _relation_label(edge: Edge) -> str:
    """The `relation · mode` label a line / row carries."""
    return f"{edge.relation} · {edge.mode}"


def _skipped_lines(graph: Graph) -> list[str]:
    """A short warning block naming the definitions that could not be loaded
    (G5), or [] when none. `⚠` is the load-bearing signal (mirrors cli_render's
    own status-warn convention); the `warn` role is plain in v1, so the glyph
    carries the meaning even with styling off."""
    if not graph.skipped:
        return []
    count = len(graph.skipped)
    noun = "definition" if count == 1 else "definitions"
    head = cli_render.style(
        "warn", f"⚠ {count} {noun} could not be loaded:"
    )
    lines = ["", "  " + head]
    for s in sorted(graph.skipped, key=Skipped.sort_key):
        lines.extend(cli_render.wrap(f"{s.address} — {s.reason}", indent="    "))
    return lines


def _out_glyph(edge: Edge) -> str:
    """The direction glyph for an OUT-edge (this process -> the upstream) in the
    adjacency view."""
    if edge.relation == RELATION_COMPOSED:
        return GLYPH_EMBEDS
    if edge.relation == RELATION_AGGREGATES:
        return GLYPH_FOLDS
    return GLYPH_DEPENDS


def _in_glyph(edge: Edge) -> str:
    """The direction glyph for an IN-edge (some process -> this process), read
    from this process's side."""
    if edge.relation == RELATION_COMPOSED:
        return GLYPH_EMBEDDED_BY
    if edge.relation == RELATION_AGGREGATES:
        return GLYPH_FOLDS
    return GLYPH_GATED_BY


def render_adjacency(graph: Graph, *, verbose: bool = False) -> str:
    """ASCII ADJACENCY view: per process, its out- and in-edges with a direction
    glyph and a `relation · mode` label. Cycle-safe (no layout engine -- it just
    lists each node's incident edges). TTY-aware styling (ADR-011); prose wraps
    through `cli_render.wrap` (ADR-024)."""
    lines: list[str] = []
    lines.append(cli_render.style("title", "Process graph") + "  (configured topology)")
    if not graph.nodes:
        lines.append("")
        lines.append("  (no installed processes)")
        lines.extend(_skipped_lines(graph))
        return "\n".join(lines) + "\n"

    for node in graph.nodes:
        out = sorted(graph.out_edges(node), key=Edge.sort_key)
        incoming = sorted(graph.in_edges(node), key=Edge.sort_key)
        lines.append("")
        lines.append("  " + cli_render.style("strong", node))
        if not out and not incoming:
            lines.append("    (standalone -- no configured connections)")
            continue
        for edge in out:
            lines.extend(_adjacency_edge_lines(_out_glyph(edge), edge.to, edge, verbose))
        for edge in incoming:
            lines.extend(_adjacency_edge_lines(_in_glyph(edge), edge.frm, edge, verbose))
    lines.extend(_skipped_lines(graph))
    return "\n".join(lines) + "\n"


def _adjacency_edge_lines(
    glyph: str, other: str, edge: Edge, verbose: bool
) -> list[str]:
    """One edge as a glyph line plus, in verbose mode, its `why` wrapped beneath
    (ADR-024: hanging-indent always, width-wrap TTY-only)."""
    label = _relation_label(edge)
    at = f" @{edge.from_state}" if edge.from_state else ""
    line = f"    {glyph} {other}  [{label}]{at}"
    out = [line]
    if verbose and edge.why:
        # `why` is an own-line author-supplied prose field (ADR-024): wrap it
        # under the edge line at the sub-detail indent rhythm.
        out.extend(cli_render.wrap(edge.why, indent="        "))
    return out


def render_flow(graph: Graph, *, verbose: bool = False) -> str:
    """ASCII PIPELINE view: edges drawn DOWNSTREAM (the work-flows-this-way
    reading). The stored edge is the dependency direction (subscriber ->
    upstream); flow reorients it to upstream ==> subscriber, so a reader follows
    work from the thing-depended-on toward the thing-that-depends. Grouped by
    upstream, cycle-safe."""
    lines: list[str] = []
    lines.append(cli_render.style("title", "Process flow") + "  (downstream pipeline)")
    if not graph.edges:
        lines.append("")
        lines.append("  (no configured connections)")
        lines.extend(_skipped_lines(graph))
        return "\n".join(lines) + "\n"

    # Group by the UPSTREAM end (edge.to), so each block reads "from this
    # upstream, work flows down into ...".
    upstreams = sorted({e.to for e in graph.edges})
    for upstream in upstreams:
        downstream = sorted(
            (e for e in graph.edges if e.to == upstream), key=Edge.sort_key
        )
        lines.append("")
        lines.append("  " + cli_render.style("strong", upstream))
        for edge in downstream:
            label = _relation_label(edge)
            at = f" @{edge.from_state}" if edge.from_state else ""
            lines.append(f"    ⇒ {edge.frm}  [{label}]{at}")  # ==>
            if verbose and edge.why:
                lines.extend(cli_render.wrap(edge.why, indent="        "))
    lines.extend(_skipped_lines(graph))
    return "\n".join(lines) + "\n"


def _mermaid_node_id(address: str) -> str:
    """A mermaid-safe node id for an address (`:` and `-` are not valid in a
    bare flowchart id). Deterministic 1:1 mapping."""
    return "n_" + address.replace(":", "__").replace("-", "_")


def render_mermaid(graph: Graph) -> str:
    """A mermaid `flowchart` of the topology. The derive-vs-annotate split is
    VISIBLE in the link style: derived edges are thick (`==>`), declared-pull
    edges solid (`-->`), push edges dotted (`-.->`). Arrow direction is the
    canonical dependency direction (subscriber -> upstream).

    Byte-stable in its own right: nodes and edges emit in sorted order, no TTY
    styling. (It is human-targeted markup, not the `--json` machine surface, but
    determinism keeps it diff-friendly.)"""
    lines: list[str] = ["flowchart LR"]
    for node in graph.nodes:
        lines.append(f"  {_mermaid_node_id(node)}[\"{node}\"]")
    for edge in sorted(graph.edges, key=Edge.sort_key):
        src = _mermaid_node_id(edge.frm)
        dst = _mermaid_node_id(edge.to)
        label = _relation_label(edge)
        if edge.source == SOURCE_DERIVED:
            arrow = f"  {src} ==>|{label}| {dst}"  # thick: derived
        elif edge.mode == "push":
            arrow = f"  {src} -.->|{label}| {dst}"  # dotted: push
        else:
            arrow = f"  {src} -->|{label}| {dst}"  # solid: declared-pull
        lines.append(arrow)
    return "\n".join(lines) + "\n"


def render_json(graph: Graph) -> str:
    """The byte-stable machine form `{nodes:[...], edges:[...]}` (ADR-024's
    load-bearing invariant). Deterministic node + edge ordering, no TTY styling,
    identical bytes across runs. This is the surface a script keys on."""
    payload = {
        "nodes": list(graph.nodes),
        "edges": [
            {
                "from": e.frm,
                "from_state": e.from_state,
                "to": e.to,
                "relation": e.relation,
                "mode": e.mode,
                "source": e.source,
                "why": e.why,
            }
            for e in sorted(graph.edges, key=Edge.sort_key)
        ],
        # Definitions discovered but unloadable (G5). Always present (possibly
        # empty) so a script can key on it; sorted for byte-stability.
        "skipped": [
            {"address": s.address, "reason": s.reason}
            for s in sorted(graph.skipped, key=Skipped.sort_key)
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"
