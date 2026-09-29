"""The one wiring graph (COR-053 point 7): every connection a project declares,
drawn once, in the process graph's format.

COR-053 point 7 asks for one graph that draws the process graph's derived and
annotated edges (COR-038) together with the data and event edges — the wiring
graph subsumes the process graph; it does not sit beside it. This module builds
it from the two computations that already exist, never a third (ADR-057 point
2), and says where each edge comes from:

- **From the process definitions** (`process_graph.build_graph`, unchanged): the
  derived edges read from each definition's `subprocess` / `cascade` blocks,
  and the annotated edges read from its `depends_on` — the upstream written in
  either address form, a role-addressed `<publisher>::<role>:<point>` included.
- **From the wiring** (`connections.shared_wiring`), source `resolved`, each
  edge running into the connection point (provider → point ← counterparts):
  for every point an installed provider declares, an edge from its definer —
  `accepts` from the provider of a data point, `emits` from the provider of an
  event, `offers` from the offered process definition `<provider>:<process-id>`
  of a process point, which is how a role-addressed `depends_on` reaches the
  process that answers it; for every contribution and subscription, an edge
  from the capability declaring it — `contributes`, `subscribes`; and for the
  project filler of a data point, an edge from the file — `fills`.

The generated `depends-on` list of package metadata is **not** drawn: it is a
machine-written copy of the definitions' `depends_on` (COR-053 point 4), whose
edges the process graph already draws, and drawing the copy too would draw one
fact twice (COR-038: every edge expressible one way). Whether such an entry
binds — at a compatible version, to an installed upstream — is the status
report's and `pkit validate`'s.

A resolved edge fills the process graph's fields: the relation above; as its
`mode`, how it stands in the wiring — a definer's `active`, `not selected` or
`conflict`, a counterpart's binding status (`bound`, `inert (version)`,
`inert (provider)`, `no active provider`, `no such point`), a project filler's
`bound` or `inert (version)`; and as its `why`, the declaration's description,
which people read in the graph (COR-053 point 3). `--json` is therefore the
process graph's own shape, byte-stable in the same way.

`process_view` is the graph narrowed to its process edges: exactly what `pkit
process graph` renders, so the two commands never disagree. The graph reads
declarations only — the resolver runs no filler command and the process graph
resolves no position (COR-038's safety point).
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from project_kit import connections as cx
from project_kit import process_graph as pg
from project_kit.package_validate import POINT_SEPARATOR

# The kinds of edge: the three kinds of connection point (COR-053 point 2). The
# process kind carries every edge of the process graph as well.
DATA = cx.PointKind.DATA.value
PROCESS = cx.PointKind.PROCESS.value
EVENT = cx.PointKind.EVENT.value
KINDS = (DATA, PROCESS, EVENT)

# How a definer's edge stands: its provider is the one answering the role, or it
# is not — another is selected, or several provide it and none is (COR-053 point 1).
ACTIVE = "active"
NOT_SELECTED = "not selected"
CONFLICT = "conflict"

# The adjacency and flow views' titles and empty state for this graph.
TITLE = "Wiring graph"
FLOW_TITLE = "Wiring flow"
EMPTY = "(no installed processes and no connection points)"

_DEFINER_RELATION = {
    cx.PointKind.DATA: pg.RELATION_ACCEPTS,
    cx.PointKind.EVENT: pg.RELATION_EMITS,
    cx.PointKind.PROCESS: pg.RELATION_OFFERS,
}

_COUNTERPART_RELATION = {
    cx.CounterpartKind.CONTRIBUTION: pg.RELATION_CONTRIBUTES,
    cx.CounterpartKind.SUBSCRIPTION: pg.RELATION_SUBSCRIBES,
}

_KIND_OF_RESOLVED = {
    pg.RELATION_ACCEPTS: DATA,
    pg.RELATION_CONTRIBUTES: DATA,
    pg.RELATION_FILLS: DATA,
    pg.RELATION_EMITS: EVENT,
    pg.RELATION_SUBSCRIBES: EVENT,
    pg.RELATION_OFFERS: PROCESS,
}


def edge_kind(edge: pg.Edge) -> str:
    """The kind of connection an edge belongs to: every edge read from a process
    definition is a process edge; a resolved edge's kind is its relation's."""
    if edge.source in (pg.SOURCE_DERIVED, pg.SOURCE_ANNOTATED):
        return PROCESS
    return _KIND_OF_RESOLVED[edge.relation]


# --- building ---------------------------------------------------------------


def build_wiring_graph(repo_root: Path) -> pg.Graph:
    """The one graph of the project at `repo_root`: the process graph's edges and
    the wiring resolver's, over every node either names, in the process graph's
    total order. The wiring is the run's one (`connections.shared_wiring`)."""
    process = pg.build_graph(repo_root)
    resolved = resolved_edges(cx.shared_wiring(repo_root), repo_root)
    edges = sorted(set(process.edges) | set(resolved), key=pg.Edge.sort_key)
    nodes = set(process.nodes) | {e.frm for e in edges} | {e.to for e in edges}
    return pg.Graph(nodes=tuple(sorted(nodes)), edges=tuple(edges), skipped=process.skipped)


def resolved_edges(wiring: cx.Wiring, repo_root: Path) -> list[pg.Edge]:
    """The wiring's edges (the module docstring): each installed provider's
    points from their definer, each active data point's project filler, and
    each contribution and subscription — in the wiring's own order."""
    edges = [_definer_edge(wiring, point) for point in wiring.declarations.points]
    edges.extend(_filler_edge(p, repo_root) for p in wiring.points if p.filler is not None)
    edges.extend(
        _counterpart_edge(b)
        for b in wiring.bindings
        if b.counterpart.kind in _COUNTERPART_RELATION
    )
    return edges


def _definer_edge(wiring: cx.Wiring, point: cx.Point) -> pg.Edge:
    definer = point.provider
    if point.kind is cx.PointKind.PROCESS and point.process_id is not None:
        definer = f"{point.provider}{POINT_SEPARATOR}{point.process_id}"
    return pg.Edge(
        frm=definer,
        to=point.address,
        relation=_DEFINER_RELATION[point.kind],
        mode=_definer_mode(wiring, point),
        source=pg.SOURCE_RESOLVED,
        why=point.description,
    )


def _definer_mode(wiring: cx.Wiring, point: cx.Point) -> str:
    role = wiring.role(point.role)
    if role is not None and role.active == point.provider:
        return ACTIVE
    if role is not None and role.conflict:
        return CONFLICT
    return NOT_SELECTED


def _filler_edge(point: cx.PointBinding, repo_root: Path) -> pg.Edge:
    filler = point.filler
    assert filler is not None  # the caller draws only points with a filler
    status = cx.BindingStatus.BOUND if point.filler_compatible else cx.BindingStatus.INERT_VERSION
    file = filler.file
    if file.is_absolute() and file.is_relative_to(repo_root):
        file = file.relative_to(repo_root)
    return pg.Edge(
        frm=file.as_posix(),
        to=point.point.address,
        relation=pg.RELATION_FILLS,
        mode=status.value,
        source=pg.SOURCE_RESOLVED,
    )


def _counterpart_edge(binding: cx.Binding) -> pg.Edge:
    c = binding.counterpart
    return pg.Edge(
        frm=c.capability,
        to=c.target,
        relation=_COUNTERPART_RELATION[c.kind],
        mode=binding.status.value,
        source=pg.SOURCE_RESOLVED,
        why=c.description,
    )


# --- views ------------------------------------------------------------------


def with_kinds(graph: pg.Graph, kinds: Iterable[str]) -> pg.Graph:
    """The graph narrowed to the edges of `kinds`.

    A node stays when a kept edge touches it. A node no edge of the whole graph
    touches — a standalone process definition — stays when the process kind is
    kept, as do the definitions that could not be loaded, since both are the
    process graph's; nothing else is dropped or added.
    """
    wanted = frozenset(kinds)
    edges = tuple(e for e in graph.edges if edge_kind(e) in wanted)
    nodes = {e.frm for e in edges} | {e.to for e in edges}
    with_process = PROCESS in wanted
    if with_process:
        touched = {e.frm for e in graph.edges} | {e.to for e in graph.edges}
        nodes |= {n for n in graph.nodes if n not in touched}
    return pg.Graph(
        nodes=tuple(sorted(nodes)),
        edges=edges,
        skipped=graph.skipped if with_process else (),
    )


def process_view(graph: pg.Graph) -> pg.Graph:
    """The wiring graph filtered to its process edges — the process graph's
    derived and annotated edges and the resolver's offered processes. What
    `pkit process graph` renders, before its own filters."""
    return with_kinds(graph, (PROCESS,))
