"""The `pkit process graph` render (COR-038): a read-only view of the configured
cross-process topology, built from DECLARATIONS only.

These tests pin the load-bearing facts:

- the graph model is DERIVED edges (subprocess/cascade) ∪ ANNOTATED edges
  (depends_on), with no edge expressible both ways (single source of truth);
- the render reads DECLARATIONS only -- it never resolves a live position or
  runs a predicate (COR-038's safety point), asserted by spying that the
  engine's resolution methods are never invoked;
- every format renders, and `--json` is byte-stable across TTY / COLUMNS / piped
  (ADR-024's load-bearing invariant);
- every atomic filter and every preset expands to the right edge set;
- cross-capability `--seams`, `--upstream-of`/`--downstream-of` closures, and an
  empty/standalone process all degrade sanely.

Built on a tiny fixture project with two capabilities and four processes,
exercising every edge kind (composed-subprocess, aggregates, and all four
depends_on relations across pull and push).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from project_kit import cli_render
from project_kit import process_graph as pg
from project_kit.cli import main
from project_kit.process import ProcessEngine

# --- the fixture project --------------------------------------------------

# Capability `alpha` ships three processes:
#   - `ship`: a delivery process. Its `building` state EMBEDS `alpha:review`
#     (composed-subprocess, derived) and its `releasing` state declares an
#     informational depends_on on `beta:issue` (annotated) plus a push
#     triggered-by on the same.
#   - `review`: a standalone-ish process whose `open` state has a
#     gates-on-readiness depends_on toward `beta:issue` (annotated, pull).
#   - `roster`: a process that FOLDS `alpha:review` members (cascade,
#     aggregates, derived) and declares a constrained-with depends_on toward
#     `alpha:ship`.
# Capability `beta` ships `issue`: a process with NO connections (standalone).

_SHIP = """\
process:
  id: ship
  version: 1
  subject:
    cardinality: singleton
  states:
    - id: planning
      meaning: Planning.
      entry: true
      detection:
        mode: inferred
        predicate:
          run: noop
    - id: building
      meaning: Building, embeds a review.
      subprocess:
        runs: alpha:review
      detection:
        mode: inferred
        predicate:
          run: noop
    - id: releasing
      meaning: Releasing.
      detection:
        mode: inferred
        predicate:
          run: noop
      depends_on:
        - upstream: beta:issue
          relation: informational
          mode: pull
          why: We document that a release references its tracking issue.
        - upstream: beta:issue
          relation: triggered-by
          mode: push
          why: A connector kicks the release off from the issue closing.
    - id: shipped
      meaning: Done.
      terminal: true
      detection:
        mode: inferred
        predicate:
          run: noop
  transitions: []
"""

_REVIEW = """\
process:
  id: review
  version: 1
  subject:
    cardinality: keyed
    key: review-id
  states:
    - id: open
      meaning: Review open.
      entry: true
      detection:
        mode: inferred
        predicate:
          run: noop
      depends_on:
        - upstream: beta:issue
          relation: gates-on-readiness
          mode: pull
          why: A gate predicate enforces the issue is ready before review opens.
    - id: approved
      meaning: Approved.
      terminal: true
      detection:
        mode: inferred
        predicate:
          run: noop
  transitions: []
"""

_ROSTER = """\
process:
  id: roster
  version: 1
  subject:
    cardinality: singleton
  states:
    - id: collecting
      meaning: Collecting reviews.
      entry: true
      detection:
        mode: inferred
        predicate:
          run: noop
      depends_on:
        - upstream: alpha:ship
          relation: constrained-with
          mode: pull
          why: A roster and its ship must agree on the review set.
    - id: complete
      meaning: All reviews in.
      terminal: true
      detection:
        mode: inferred
        predicate:
          run: noop
  transitions: []
  cascade:
    runs: alpha:review
    members:
      run: noop
    membership:
      run: noop
    reducer:
      op: all
      outcome: approved
"""

_ISSUE = """\
process:
  id: issue
  version: 1
  subject:
    cardinality: keyed
    key: number
  states:
    - id: triage
      meaning: Triage.
      entry: true
      detection:
        mode: inferred
        predicate:
          run: noop
    - id: closed
      meaning: Closed.
      terminal: true
      detection:
        mode: inferred
        predicate:
          run: noop
  transitions: []
"""


# --- disconfirming fixtures ----------------------------------------------

# A two-process MUTUAL dependency (a real cycle): `cycle-a` informationally
# depends on `gamma:cycle-b` and vice-versa. The cycle path must be surfaced
# EXACTLY (a false-negative direction in `_edges_on_cycle` would otherwise pass
# every acyclic test), and the closures / focus must TERMINATE on it.
_CYCLE_A = """\
process:
  id: cycle-a
  version: 1
  subject:
    cardinality: singleton
  states:
    - id: only
      meaning: Only state.
      entry: true
      terminal: true
      detection:
        mode: inferred
        predicate:
          run: noop
      depends_on:
        - upstream: gamma:cycle-b
          relation: informational
          mode: pull
          why: a depends on b.
  transitions: []
"""

_CYCLE_B = """\
process:
  id: cycle-b
  version: 1
  subject:
    cardinality: singleton
  states:
    - id: only
      meaning: Only state.
      entry: true
      terminal: true
      detection:
        mode: inferred
        predicate:
          run: noop
      depends_on:
        - upstream: gamma:cycle-a
          relation: informational
          mode: pull
          why: b depends on a.
  transitions: []
"""

# An OFF-cycle process: `tail` depends on `cycle-a` but nothing on the cycle
# depends back on `tail`. Its edge must NOT be reported as on-cycle -- this makes
# `--cycles` membership non-trivial (an over-inclusive predicate would wrongly
# pull it in, a direction-flipped predicate would report tail's edge instead of
# the real cycle edges).
_CYCLE_TAIL = """\
process:
  id: tail
  version: 1
  subject:
    cardinality: singleton
  states:
    - id: only
      meaning: Only state.
      entry: true
      terminal: true
      detection:
        mode: inferred
        predicate:
          run: noop
      depends_on:
        - upstream: gamma:cycle-a
          relation: informational
          mode: pull
          why: tail depends on a but is not part of the cycle.
  transitions: []
"""

# A DUPLICATE/ambiguous definition: two schema files in one capability both
# declare `process.id: dup`. `discover_process_addresses` collapses them to the
# single address `gamma:dup`, but `load_definition` finds two matching files and
# raises an "ambiguous process definition" ProcessError. The address must land in
# `skipped` (with the reason), NOT appear as a silent standalone node.
#
# Both files are deliberately named OFF the `<process-id>.yaml` convention
# (`dup_a.yaml` / `dup_b.yaml`), so the loader skips its fast-path convention
# lookup and takes the scan branch that detects the duplicate.
_DUP = """\
process:
  id: dup
  version: 1
  subject:
    cardinality: singleton
  states:
    - id: only
      meaning: Only.
      entry: true
      terminal: true
      detection:
        mode: inferred
        predicate:
          run: noop
  transitions: []
"""


def _write_capability(repo: Path, name: str, processes: dict[str, str]) -> None:
    cap = repo / ".pkit" / "capabilities" / name
    schemas = cap / "schemas"
    schemas.mkdir(parents=True, exist_ok=True)
    (cap / "package.yaml").write_text(
        f"""schema_version: 2
component:
  kind: capability
  name: {name}
  version: 0.1.0
description: Fixture capability for process-graph tests.
commands:
  noop:
    script: scripts/noop.py
    help: noop predicate
""",
        encoding="utf-8",
    )
    scripts = cap / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    (scripts / "noop.py").write_text(
        "#!/usr/bin/env python3\n"
        "import json\n"
        "print(json.dumps({'result': False, 'reason': 'noop'}))\n",
        encoding="utf-8",
    )
    for stem, body in processes.items():
        (schemas / f"{stem}.yaml").write_text(body, encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    (root / ".pkit" / "schemas" / "_defs").mkdir(parents=True, exist_ok=True)
    _write_capability(
        root, "alpha", {"ship": _SHIP, "review": _REVIEW, "roster": _ROSTER}
    )
    _write_capability(root, "beta", {"issue": _ISSUE})
    return root


@pytest.fixture
def graph(repo: Path) -> pg.Graph:
    return pg.build_graph(repo)


# --- the graph model: derived ∪ annotated, no double-counting --------------


def _edge_tuples(graph: pg.Graph) -> set[tuple[str, str, str, str, str]]:
    return {(e.frm, e.to, e.relation, e.mode, e.source) for e in graph.edges}


def test_nodes_are_every_installed_process(graph: pg.Graph) -> None:
    assert graph.nodes == (
        "alpha:review",
        "alpha:roster",
        "alpha:ship",
        "beta:issue",
    )


def test_derived_and_annotated_edges_present(graph: pg.Graph) -> None:
    edges = _edge_tuples(graph)
    # Derived: composition (ship.building embeds review) + aggregation (roster
    # folds review).
    assert ("alpha:ship", "alpha:review", "composed-subprocess", "pull", "derived") in edges
    assert ("alpha:roster", "alpha:review", "aggregates", "pull", "derived") in edges
    # Annotated: all four depends_on relations.
    assert ("alpha:ship", "beta:issue", "informational", "pull", "annotated") in edges
    assert ("alpha:ship", "beta:issue", "triggered-by", "push", "annotated") in edges
    assert ("alpha:review", "beta:issue", "gates-on-readiness", "pull", "annotated") in edges
    assert ("alpha:roster", "alpha:ship", "constrained-with", "pull", "annotated") in edges
    assert len(graph.edges) == 6


def test_derived_relations_never_annotated_and_vice_versa(graph: pg.Graph) -> None:
    # COR-038's no-edge-is-both rule, made structural: a composed/aggregates edge
    # is always derived; the four depends_on relations are always annotated.
    for e in graph.edges:
        if e.relation in pg.DERIVED_RELATIONS:
            assert e.source == pg.SOURCE_DERIVED
        if e.relation in pg.ANNOTATED_RELATIONS:
            assert e.source == pg.SOURCE_ANNOTATED


def test_no_double_counting(graph: pg.Graph) -> None:
    # The composed edge ship->review and the aggregates edge roster->review are
    # each present exactly once and only as derived -- never duplicated as an
    # annotated copy.
    derived_pairs = [(e.frm, e.to) for e in graph.edges if e.source == "derived"]
    assert derived_pairs.count(("alpha:ship", "alpha:review")) == 1
    assert derived_pairs.count(("alpha:roster", "alpha:review")) == 1
    annotated_pairs = {(e.frm, e.to) for e in graph.edges if e.source == "annotated"}
    assert ("alpha:ship", "alpha:review") not in annotated_pairs
    assert ("alpha:roster", "alpha:review") not in annotated_pairs


def test_from_state_recorded(graph: pg.Graph) -> None:
    # Annotated edges carry the originating state; a process-level cascade does
    # not; a composed edge carries the subprocess state.
    by = {(e.frm, e.to, e.relation): e for e in graph.edges}
    assert by[("alpha:ship", "alpha:review", "composed-subprocess")].from_state == "building"
    assert by[("alpha:ship", "beta:issue", "informational")].from_state == "releasing"
    assert by[("alpha:roster", "alpha:review", "aggregates")].from_state is None


# --- the safety invariant: declarations only, no live position read --------


def test_build_graph_never_resolves_position(repo: Path, monkeypatch) -> None:
    """COR-038's load-bearing safety point: building the graph must NOT resolve a
    live position or run a predicate. We poison every engine resolution method so
    any call raises -- if the render touched the engine, the build would blow up."""

    def _boom(*_args, **_kwargs):
        raise AssertionError("the graph render must not resolve live position/state")

    monkeypatch.setattr(ProcessEngine, "resolve_position", _boom)
    monkeypatch.setattr(ProcessEngine, "can_move", _boom)
    monkeypatch.setattr(ProcessEngine, "move", _boom)
    monkeypatch.setattr(ProcessEngine, "resolve_subprocess_outcome", _boom)
    monkeypatch.setattr(ProcessEngine, "resolve_cascade_outcome", _boom)

    # A full build + every render must complete without invoking any of them.
    g = pg.build_graph(repo)
    pg.render_adjacency(g)
    pg.render_flow(g)
    pg.render_mermaid(g)
    pg.render_json(g)
    assert len(g.edges) == 6


# --- every format renders --------------------------------------------------


def test_adjacency_renders(graph: pg.Graph) -> None:
    out = pg.render_adjacency(graph)
    assert "alpha:ship" in out
    assert "⊃ embeds" in out  # composed out-edge glyph
    assert "⊂ embedded by" in out  # the same edge seen from review's side
    assert "→ depends on" in out
    assert "⇄ folds" in out


def test_flow_renders_downstream(graph: pg.Graph) -> None:
    out = pg.render_flow(graph)
    # Flow groups by upstream; review is embedded/folded, so it heads a block and
    # ship/roster appear downstream of it.
    assert "alpha:review" in out
    assert "⇒ alpha:ship" in out


def test_mermaid_shows_derive_vs_annotate_split(graph: pg.Graph) -> None:
    out = pg.render_mermaid(graph)
    assert out.startswith("flowchart LR\n")
    assert "==>|composed-subprocess" in out  # derived = thick
    assert "==>|aggregates" in out  # derived = thick
    assert "-->|informational" in out  # declared-pull = solid
    assert "-.->|triggered-by" in out  # push = dotted


def test_json_shape(graph: pg.Graph) -> None:
    payload = json.loads(pg.render_json(graph))
    assert set(payload) == {"nodes", "edges", "skipped"}
    assert payload["nodes"] == list(graph.nodes)
    assert payload["skipped"] == []  # the clean fixture has nothing unloadable
    assert len(payload["edges"]) == 6
    for edge in payload["edges"]:
        assert set(edge) == {"from", "from_state", "to", "relation", "mode", "source", "why"}


def test_verbose_shows_why(graph: pg.Graph) -> None:
    plain = pg.render_adjacency(graph, verbose=False)
    verbose = pg.render_adjacency(graph, verbose=True)
    assert "We document that a release references" not in plain
    assert "We document that a release references" in verbose


# --- --json byte-stability (ADR-024's load-bearing invariant) --------------


def test_json_byte_stable_across_environment(graph: pg.Graph, monkeypatch) -> None:
    # No TTY styling and identical bytes regardless of COLUMNS / color decision.
    cli_render.set_color(False)
    cli_render.set_wrap_width(cli_render.NO_WRAP)
    baseline = pg.render_json(graph)

    cli_render.set_color(True)  # styling on...
    cli_render.set_wrap_width(40)  # ...and a narrow width
    monkeypatch.setenv("COLUMNS", "40")
    styled = pg.render_json(graph)

    assert styled == baseline
    assert "\033[" not in baseline  # no SGR codes leaked in
    # And byte-identical run to run.
    assert pg.render_json(graph) == baseline


def test_json_deterministic_ordering(repo: Path) -> None:
    # Two independent builds of the same project produce byte-identical JSON.
    a = pg.render_json(pg.build_graph(repo))
    b = pg.render_json(pg.build_graph(repo))
    assert a == b


# --- atomic filters --------------------------------------------------------


def test_filter_source(graph: pg.Graph) -> None:
    derived = pg.apply_filters(graph, pg.FilterSpec(sources=frozenset(["derived"])))
    assert all(e.source == "derived" for e in derived.edges)
    assert len(derived.edges) == 2
    annotated = pg.apply_filters(graph, pg.FilterSpec(sources=frozenset(["annotated"])))
    assert all(e.source == "annotated" for e in annotated.edges)
    assert len(annotated.edges) == 4


def test_filter_relation_csv(graph: pg.Graph) -> None:
    out = pg.apply_filters(
        graph, pg.FilterSpec(relations=frozenset(["informational", "triggered-by"]))
    )
    assert {e.relation for e in out.edges} == {"informational", "triggered-by"}


def test_filter_mode(graph: pg.Graph) -> None:
    push = pg.apply_filters(graph, pg.FilterSpec(modes=frozenset(["push"])))
    assert all(e.mode == "push" for e in push.edges)
    assert {e.relation for e in push.edges} == {"triggered-by"}


def test_filter_capability(graph: pg.Graph) -> None:
    out = pg.apply_filters(graph, pg.FilterSpec(capability="beta"))
    # Every surviving edge touches beta (as from or to).
    assert all("beta" in (e.capability_from, e.capability_to) for e in out.edges)
    assert len(out.edges) == 3  # the three edges into beta:issue


def test_filter_and_combine(graph: pg.Graph) -> None:
    # source:annotated AND mode:pull AND capability:beta.
    out = pg.apply_filters(
        graph,
        pg.FilterSpec(
            sources=frozenset(["annotated"]),
            modes=frozenset(["pull"]),
            capability="beta",
        ),
    )
    assert {(e.frm, e.to, e.relation) for e in out.edges} == {
        ("alpha:ship", "beta:issue", "informational"),
        ("alpha:review", "beta:issue", "gates-on-readiness"),
    }


def test_filter_direction_and_depth(graph: pg.Graph) -> None:
    # Focus ship, out-edges only, depth 1: ship's own out-edges (embeds review,
    # informational + triggered-by toward issue) -- not roster->ship (an in-edge).
    out = pg.apply_filters(
        graph, pg.FilterSpec(process="alpha:ship", direction="out", depth=1)
    )
    assert all(e.frm == "alpha:ship" for e in out.edges)
    assert len(out.edges) == 3
    # In-direction depth 1: only roster->ship.
    incoming = pg.apply_filters(
        graph, pg.FilterSpec(process="alpha:ship", direction="in", depth=1)
    )
    assert {(e.frm, e.to) for e in incoming.edges} == {("alpha:roster", "alpha:ship")}


def test_focus_keeps_process_node_even_with_no_edges(repo: Path) -> None:
    g = pg.build_graph(repo)
    # beta:issue has only in-edges; an out-focus at depth 1 yields no edges but
    # the node is still present (never silently dropped).
    out = pg.apply_filters(
        g, pg.FilterSpec(process="beta:issue", direction="out", depth=1)
    )
    assert out.edges == ()
    assert "beta:issue" in out.nodes


# --- presets (documented expansions of the atomics) ------------------------


def test_preset_enforced_is_union(graph: pg.Graph) -> None:
    # source:derived ∪ relation:gates-on-readiness -- the union, not an
    # intersection. Derived edges (2) + the gates-on-readiness annotated edge (1).
    spec = pg.expand_presets(pg.FilterSpec(), enforced=True)
    out = pg.apply_filters(graph, spec)
    got = {(e.frm, e.to, e.relation) for e in out.edges}
    assert got == {
        ("alpha:ship", "alpha:review", "composed-subprocess"),
        ("alpha:roster", "alpha:review", "aggregates"),
        ("alpha:review", "beta:issue", "gates-on-readiness"),
    }


def test_preset_advisory(graph: pg.Graph) -> None:
    spec = pg.expand_presets(pg.FilterSpec(), advisory=True)
    out = pg.apply_filters(graph, spec)
    assert {e.relation for e in out.edges} == {"informational", "triggered-by"}


def test_preset_seams(graph: pg.Graph) -> None:
    spec = pg.expand_presets(pg.FilterSpec(), seams=True)
    out = pg.apply_filters(graph, spec)
    # Only cross-capability edges: the three alpha->beta edges.
    assert all(e.crosses_capability for e in out.edges)
    assert all(e.capability_to == "beta" for e in out.edges)
    assert len(out.edges) == 3


def test_preset_connectors(graph: pg.Graph) -> None:
    spec = pg.expand_presets(pg.FilterSpec(), connectors=True)
    out = pg.apply_filters(graph, spec)
    assert all(e.mode == "push" for e in out.edges)


def test_preset_declared_and_derived(graph: pg.Graph) -> None:
    declared = pg.apply_filters(graph, pg.expand_presets(pg.FilterSpec(), declared=True))
    assert all(e.source == "annotated" for e in declared.edges)
    derived = pg.apply_filters(graph, pg.expand_presets(pg.FilterSpec(), derived=True))
    assert all(e.source == "derived" for e in derived.edges)


def test_preset_upstream_of(graph: pg.Graph) -> None:
    # What does alpha:ship (transitively) depend on? It embeds review and
    # depends on issue; review depends on issue. So the closure from ship reaches
    # {ship, review, issue}; edges among them survive.
    spec = pg.expand_presets(pg.FilterSpec(), upstream_of="alpha:ship")
    out = pg.apply_filters(graph, spec)
    nodes = set(out.nodes)
    assert "beta:issue" in nodes
    assert "alpha:review" in nodes
    # roster is NOT upstream of ship (it depends ON ship), so its edges drop.
    assert not any(e.frm == "alpha:roster" for e in out.edges)


def test_preset_downstream_of(graph: pg.Graph) -> None:
    # What (transitively) depends on beta:issue? ship, review (directly), and
    # roster via ship/review. The closure following edges backwards.
    spec = pg.expand_presets(pg.FilterSpec(), downstream_of="beta:issue")
    out = pg.apply_filters(graph, spec)
    froms = {e.frm for e in out.edges}
    assert "alpha:ship" in froms
    assert "alpha:review" in froms


def test_preset_cycles(graph: pg.Graph) -> None:
    # The fixture is acyclic, so --cycles yields nothing.
    spec = pg.expand_presets(pg.FilterSpec(), cycles=True)
    out = pg.apply_filters(graph, spec)
    assert out.edges == ()


def test_presets_and_combine_with_atomics(graph: pg.Graph) -> None:
    # --advisory plus --mode push narrows to just the push advisory edge.
    base = pg.FilterSpec(modes=frozenset(["push"]))
    spec = pg.expand_presets(base, advisory=True)
    out = pg.apply_filters(graph, spec)
    assert {e.relation for e in out.edges} == {"triggered-by"}


# --- degradation cases -----------------------------------------------------


def test_standalone_process_degrades(repo: Path) -> None:
    # beta:issue has no out-edges of its own (only in-edges). Filter to its
    # capability + out-direction: a sane, empty-but-node-present view.
    g = pg.build_graph(repo)
    assert g.out_edges("beta:issue") == []


def test_empty_project(tmp_path: Path) -> None:
    root = tmp_path / "empty"
    (root / ".pkit" / "capabilities").mkdir(parents=True, exist_ok=True)
    g = pg.build_graph(root)
    assert g.nodes == ()
    assert g.edges == ()
    # Every render degrades to a sane no-content view rather than erroring.
    assert "no installed processes" in pg.render_adjacency(g)
    assert "no configured connections" in pg.render_flow(g)
    assert pg.render_mermaid(g) == "flowchart LR\n"
    assert json.loads(pg.render_json(g)) == {"nodes": [], "edges": [], "skipped": []}


# --- W1: `why` ties pinned so --json stays byte-stable ---------------------


def test_why_breaks_sort_ties_for_byte_stability() -> None:
    # Two edges identical on every other sort-key field (same endpoints, state,
    # relation, source, mode) but DIFFERENT `why`. Without `why` in the key their
    # order is unpinned; with it the order is total and --json is byte-stable.
    a = pg.Edge(
        frm="x:a", to="y:b", relation="informational", mode="pull",
        source="annotated", from_state="s", why="zeta reason",
    )
    b = pg.Edge(
        frm="x:a", to="y:b", relation="informational", mode="pull",
        source="annotated", from_state="s", why="alpha reason",
    )
    g1 = pg.Graph(nodes=("x:a", "y:b"), edges=(a, b))
    g2 = pg.Graph(nodes=("x:a", "y:b"), edges=(b, a))  # built in the other order
    # Sorting is by `why` last, so both inputs serialise identically...
    assert pg.render_json(g1) == pg.render_json(g2)
    # ...and the `why` tie-break orders alpha before zeta, deterministically.
    payload = json.loads(pg.render_json(g1))
    whys = [e["why"] for e in payload["edges"]]
    assert whys == ["alpha reason", "zeta reason"]


# --- the cycle path: a REAL cycle (not just the empty acyclic case) --------


@pytest.fixture
def cyclic_repo(tmp_path: Path) -> Path:
    root = tmp_path / "cyclic"
    (root / ".pkit" / "capabilities").mkdir(parents=True, exist_ok=True)
    _write_capability(
        root,
        "gamma",
        {"cycle_a": _CYCLE_A, "cycle_b": _CYCLE_B, "tail": _CYCLE_TAIL},
    )
    return root


def test_cycles_surfaces_exactly_the_cycle_edges(cyclic_repo: Path) -> None:
    g = pg.build_graph(cyclic_repo)
    spec = pg.expand_presets(pg.FilterSpec(), cycles=True)
    out = pg.apply_filters(g, spec)
    # The mutual dependency is a 2-cycle; BOTH edges lie on it. A direction
    # false-negative in `_edges_on_cycle` would yield an empty set here (which is
    # exactly what every acyclic test would still pass), so this is the
    # disconfirming assertion: exactly the two cycle edges, not empty.
    got = {(e.frm, e.to) for e in out.edges}
    assert got == {
        ("gamma:cycle-a", "gamma:cycle-b"),
        ("gamma:cycle-b", "gamma:cycle-a"),
    }
    # tail->cycle-a is NOT on the cycle (nothing on the cycle depends on tail),
    # so an over-inclusive or direction-flipped predicate is caught here.
    assert ("gamma:tail", "gamma:cycle-a") not in got


def test_closures_and_focus_terminate_on_a_cycle(cyclic_repo: Path) -> None:
    # The walks must not loop forever on a cyclic graph (the `seen`/`reachable`
    # guards). If any of these did not terminate the test would hang, not fail --
    # so this is a liveness pin as much as a correctness one.
    g = pg.build_graph(cyclic_repo)
    up = pg.apply_filters(
        g, pg.expand_presets(pg.FilterSpec(), upstream_of="gamma:cycle-a")
    )
    down = pg.apply_filters(
        g, pg.expand_presets(pg.FilterSpec(), downstream_of="gamma:cycle-a")
    )
    focus = pg.apply_filters(
        g, pg.FilterSpec(process="gamma:cycle-a", direction="out", depth=None)
    )
    # upstream-of cycle-a follows what it depends on: into the 2-cycle (both
    # nodes), but NOT the off-cycle `tail` (tail depends on cycle-a, the other
    # way). The walk terminates despite the cycle.
    assert set(up.nodes) == {"gamma:cycle-a", "gamma:cycle-b"}
    # downstream-of cycle-a follows what depends on it: cycle-b (mutual) AND tail.
    assert set(down.nodes) == {"gamma:cycle-a", "gamma:cycle-b", "gamma:tail"}
    # out-focus walks out-edges from cycle-a: only cycle-b is reachable that way
    # (tail is an in-edge of cycle-a, not an out-edge). Terminates on the cycle.
    assert set(focus.nodes) == {"gamma:cycle-a", "gamma:cycle-b"}


# --- G1: a leaf queried in its own direction still renders the focus node ---


def test_upstream_of_leaf_renders_focus_node(repo: Path) -> None:
    # beta:issue depends on nothing, so its upstream-closure has no edges. The
    # focus node must still render (G1) rather than vanishing into a blank graph.
    g = pg.build_graph(repo)
    out = pg.apply_filters(
        g, pg.expand_presets(pg.FilterSpec(), upstream_of="beta:issue")
    )
    assert out.edges == ()
    assert "beta:issue" in out.nodes
    # And the adjacency render shows it as a standalone node, not "no processes".
    text = pg.render_adjacency(out)
    assert "beta:issue" in text
    assert "no installed processes" not in text


def test_downstream_of_leaf_renders_focus_node(repo: Path) -> None:
    # alpha:roster: nothing depends on it (it only depends OUT on ship/review).
    # Its downstream-closure is empty of edges; the focus node still renders.
    g = pg.build_graph(repo)
    out = pg.apply_filters(
        g, pg.expand_presets(pg.FilterSpec(), downstream_of="alpha:roster")
    )
    assert out.edges == ()
    assert "alpha:roster" in out.nodes


# --- enforced composed with a closure: order is pinned ---------------------


def test_enforced_upstream_of_runs_closure_over_narrowed_edges(repo: Path) -> None:
    # --enforced --upstream-of alpha:ship: the enforced union is applied FIRST
    # (source:derived ∪ gates-on-readiness), THEN the upstream closure walks only
    # what survived. ship embeds review (derived, kept) and informationally/
    # triggered-by depends on issue (annotated, NON-enforced -> dropped before
    # the closure). review gates-on-readiness issue (kept). So the closure over
    # the enforced set reaches issue via review's gate, but ship's own advisory
    # edges to issue are gone.
    g = pg.build_graph(repo)
    spec = pg.expand_presets(
        pg.FilterSpec(), enforced=True, upstream_of="alpha:ship"
    )
    out = pg.apply_filters(g, spec)
    got = {(e.frm, e.to, e.relation) for e in out.edges}
    assert got == {
        ("alpha:ship", "alpha:review", "composed-subprocess"),
        ("alpha:review", "beta:issue", "gates-on-readiness"),
    }
    # ship's advisory (non-enforced) edges to issue were dropped before the walk.
    assert ("alpha:ship", "beta:issue", "informational") not in got
    assert ("alpha:ship", "beta:issue", "triggered-by") not in got


# --- a dangling upstream renders (both endpoints + the edge) ----------------


_DANGLER = """\
process:
  id: dangler
  version: 1
  subject:
    cardinality: singleton
  states:
    - id: only
      meaning: Only.
      entry: true
      terminal: true
      detection:
        mode: inferred
        predicate:
          run: noop
      depends_on:
        - upstream: foo:bar
          relation: informational
          mode: pull
          why: depends on an uninstalled process.
  transitions: []
"""


@pytest.fixture
def dangling_repo(tmp_path: Path) -> Path:
    root = tmp_path / "dangling"
    (root / ".pkit" / "capabilities").mkdir(parents=True, exist_ok=True)
    _write_capability(root, "delta", {"dangler": _DANGLER})
    return root


def test_dangling_upstream_renders_both_endpoints_and_edge(dangling_repo: Path) -> None:
    g = pg.build_graph(dangling_repo)
    # The uninstalled `foo:bar` is surfaced as a node (so the edge has both ends
    # visible) -- the claimed behaviour, now pinned.
    assert "delta:dangler" in g.nodes
    assert "foo:bar" in g.nodes
    edge_pairs = {(e.frm, e.to, e.relation) for e in g.edges}
    assert ("delta:dangler", "foo:bar", "informational") in edge_pairs
    # It is NOT mistaken for a skipped/unloadable definition: dangler itself
    # loaded fine; foo:bar was never a discovered address to load.
    assert g.skipped == ()


# --- G5: an unloadable/duplicate definition surfaces in `skipped` -----------


@pytest.fixture
def duplicate_repo(tmp_path: Path) -> Path:
    root = tmp_path / "dup"
    (root / ".pkit" / "capabilities").mkdir(parents=True, exist_ok=True)
    # Two non-convention-named files both declaring process.id: dup -> the loader
    # reports an ambiguous definition for gamma:dup.
    _write_capability(root, "gamma", {"dup_a": _DUP, "dup_b": _DUP})
    return root


def test_unloadable_definition_is_skipped_not_silent(duplicate_repo: Path) -> None:
    g = pg.build_graph(duplicate_repo)
    # The duplicate id is discovered once (set-collapsed) as gamma:dup but fails
    # to load -> it lands in `skipped` WITH a reason, not as a silent standalone.
    assert [s.address for s in g.skipped] == ["gamma:dup"]
    assert "ambiguous" in g.skipped[0].reason
    # It contributes no edges (correct -- it could not be read).
    assert g.edges == ()


def test_skipped_surfaced_in_json_and_renders(duplicate_repo: Path) -> None:
    g = pg.build_graph(duplicate_repo)
    payload = json.loads(pg.render_json(g))
    assert payload["skipped"] == [
        {"address": "gamma:dup", "reason": g.skipped[0].reason}
    ]
    # The non-json renders carry the ⚠ warning line, styling off.
    cli_render.set_color(False)
    text = pg.render_adjacency(g)
    assert "⚠" in text
    assert "could not be loaded" in text
    assert "gamma:dup" in text
    flow = pg.render_flow(g)
    assert "⚠" in flow


def test_skipped_json_stays_byte_stable(duplicate_repo: Path, monkeypatch) -> None:
    # The skipped block must not break the byte-stability invariant.
    g = pg.build_graph(duplicate_repo)
    cli_render.set_color(False)
    cli_render.set_wrap_width(cli_render.NO_WRAP)
    baseline = pg.render_json(g)
    cli_render.set_color(True)
    cli_render.set_wrap_width(40)
    monkeypatch.setenv("COLUMNS", "40")
    assert pg.render_json(g) == baseline
    assert "\033[" not in baseline


def test_clean_graph_has_empty_skipped(graph: pg.Graph) -> None:
    # The well-formed fixture has nothing unloadable.
    assert graph.skipped == ()
    assert "skipped" in json.loads(pg.render_json(graph))


# --- G3: --depth / --direction without --process is a usage error -----------


def test_depth_without_process_is_usage_error() -> None:
    # The guard fires before any repo resolution, so it surfaces even outside a
    # project tree -- a clear error, not a silent no-op.
    result = CliRunner().invoke(main, ["process", "graph", "--depth", "2"])
    assert result.exit_code != 0
    assert "--depth / --direction require --process" in result.output


def test_direction_without_process_is_usage_error() -> None:
    result = CliRunner().invoke(main, ["process", "graph", "--direction", "out"])
    assert result.exit_code != 0
    assert "--depth / --direction require --process" in result.output
