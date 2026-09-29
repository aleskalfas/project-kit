"""Tests for the one wiring graph (#997, COR-053 point 7): every kind of edge
from its one source — the process definitions' derived and annotated edges, the
wiring resolver's data, event and offered-process edges — in the process graph's
format; `pkit process graph` as the same graph filtered to process edges, so the
two never disagree; and the graph's determinism."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from project_kit import cli_render, command_runner
from project_kit import process_graph as pg
from project_kit import wiring_graph as wg
from project_kit.cli import main
from project_kit.process import ProcessEngine
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.connection_capabilities import (
    DOCS,
    GLOSSARY,
    PAGE_CREATED,
    READERS,
    READERS_FILLER,
    REVIEW,
    contributes,
    data_point,
    definition,
    event_point,
    process_point,
    provider,
    stage,
    state,
    write_config,
)

RESOLVED = pg.SOURCE_RESOLVED

_WAITS_ON_REVIEW = (
    "      depends_on:\n"
    f"        - upstream: {REVIEW}\n"
    "          relation: gates-on-readiness\n"
    "          mode: pull\n"
    "          why: Shipping waits on the review, whoever offers it.\n"
)
_EMBEDS_CHECK = "      subprocess:\n        runs: flow:check\n"


def _stage_flow(repo: AdopterRepo, *, generated: bool = True) -> None:
    """`flow`: `ship` embeds `flow:check` and waits on the role-addressed review;
    `idle` is standalone. Its package carries the generated copy of the one
    `depends_on` entry, as the refresh command writes it."""
    connections = (
        {
            "extensions": {
                "depends-on": {
                    "generated": True,
                    "entries": [{"process": REVIEW, "schema_version": 1}],
                }
            }
        }
        if generated
        else None
    )
    stage(
        repo,
        "flow",
        connections,
        definitions={
            "ship": definition(
                "ship", state("building", _EMBEDS_CHECK) + state("waiting", _WAITS_ON_REVIEW)
            ),
            "check": definition("check", state("only")),
            "idle": definition("idle", state("only")),
        },
    )


@pytest.fixture
def repo(make_adopter_repo: MakeAdopterRepo) -> AdopterRepo:
    """Every kind of edge: a provider defining a data point, an event and a
    process point (offering its `page-review` definition); a process waiting on
    that point by role; a bound and an out-of-step contribution, a project
    filler, a subscriber, and a contribution to a role nobody provides."""
    repo = make_adopter_repo()
    stage(
        repo,
        "docs-a",
        provider(
            accepts={READERS: data_point()},
            offers={PAGE_CREATED: event_point(), REVIEW: process_point("page-review")},
        ),
        definitions={"page-review": definition("page-review", state("open"))},
    )
    _stage_flow(repo)
    stage(repo, "evidence", contributes(description="The readers evidence has met."))
    stage(repo, "old", contributes(version=2))
    stage(
        repo,
        "notifier",
        {
            "extensions": {
                "subscribes": [{"point": PAGE_CREATED, "schema_version": 1, "command": "publish"}]
            }
        },
    )
    stage(repo, "glossary-user", contributes(GLOSSARY))
    repo.write({READERS_FILLER: json.dumps({"schema_version": 1, "value": ["developer"]})})
    return repo


@pytest.fixture(autouse=True)
def _plain_rendering():
    """Each test owns the process-wide render decisions; restore plain, unwrapped
    output afterwards so no styled state leaks between tests."""
    cli_render.set_color(False)
    cli_render.set_wrap_width(cli_render.NO_WRAP)
    yield
    cli_render.set_color(False)
    cli_render.set_wrap_width(cli_render.NO_WRAP)


def _edges(graph: pg.Graph) -> set[tuple[str, str, str, str, str]]:
    return {(e.frm, e.to, e.relation, e.mode, e.source) for e in graph.edges}


# --- every kind of edge, from its one source ------------------------------------


def test_the_graph_draws_every_kind_of_edge(repo: AdopterRepo) -> None:
    graph = wg.build_wiring_graph(repo.root)
    assert _edges(graph) == {
        # From the process definitions: derived and annotated (a role-addressed upstream).
        ("flow:ship", "flow:check", "composed-subprocess", "pull", "derived"),
        ("flow:ship", REVIEW, "gates-on-readiness", "pull", "annotated"),
        # From the wiring: provider → point ← counterparts.
        ("docs-a", READERS, "accepts", "active", RESOLVED),
        ("docs-a", PAGE_CREATED, "emits", "active", RESOLVED),
        ("docs-a:page-review", REVIEW, "offers", "active", RESOLVED),
        (READERS_FILLER, READERS, "fills", "bound", RESOLVED),
        ("evidence", READERS, "contributes", "bound", RESOLVED),
        ("old", READERS, "contributes", "inert (version)", RESOLVED),
        ("notifier", PAGE_CREATED, "subscribes", "bound", RESOLVED),
        ("glossary-user", GLOSSARY, "contributes", "no active provider", RESOLVED),
    }
    assert "flow:idle" in graph.nodes  # a standalone process stays a node
    assert graph.skipped == ()


def test_the_generated_depends_on_copy_is_not_drawn_twice(repo: AdopterRepo) -> None:
    """The package's generated `depends-on` copies the definitions' `depends_on`,
    whose edge the graph already draws; the copy adds no edge of its own."""
    graph = wg.build_wiring_graph(repo.root)
    assert "flow" not in graph.nodes
    assert [e for e in graph.edges if e.to == REVIEW and e.frm.startswith("flow")] == [
        next(e for e in graph.edges if e.relation == "gates-on-readiness")
    ]


def test_a_resolved_edge_carries_its_declarations_description(repo: AdopterRepo) -> None:
    graph = wg.build_wiring_graph(repo.root)
    why = {(e.frm, e.relation): e.why for e in graph.edges}
    assert why[("docs-a", "accepts")] == "Who reads the documentation."
    assert why[("evidence", "contributes")] == "The readers evidence has met."
    assert why[("old", "contributes")] is None  # an extension's description is optional


def test_every_edge_has_a_kind(repo: AdopterRepo) -> None:
    graph = wg.build_wiring_graph(repo.root)
    kinds = {(e.frm, e.relation): wg.edge_kind(e) for e in graph.edges}
    assert kinds[("flow:ship", "composed-subprocess")] == wg.PROCESS
    assert kinds[("flow:ship", "gates-on-readiness")] == wg.PROCESS
    assert kinds[("docs-a:page-review", "offers")] == wg.PROCESS
    assert kinds[("docs-a", "accepts")] == wg.DATA
    assert kinds[(READERS_FILLER, "fills")] == wg.DATA
    assert kinds[("docs-a", "emits")] == wg.EVENT
    assert kinds[("notifier", "subscribes")] == wg.EVENT


def test_a_kind_view_keeps_its_edges_and_their_nodes(repo: AdopterRepo) -> None:
    graph = wg.build_wiring_graph(repo.root)
    events = wg.with_kinds(graph, [wg.EVENT])
    assert _edges(events) == {
        ("docs-a", PAGE_CREATED, "emits", "active", RESOLVED),
        ("notifier", PAGE_CREATED, "subscribes", "bound", RESOLVED),
    }
    assert events.nodes == ("docs-a", "notifier", PAGE_CREATED)  # no standalone process
    data = wg.with_kinds(graph, [wg.DATA])
    assert {e.relation for e in data.edges} == {"accepts", "fills", "contributes"}
    assert wg.with_kinds(graph, wg.KINDS) == graph


def test_the_provider_selection_decides_how_each_definer_stands(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    stage(repo, "docs-a", provider(accepts={READERS: data_point()}))
    stage(repo, "docs-b", provider(accepts={READERS: data_point()}))

    def definers() -> dict[str, str]:
        graph = wg.build_wiring_graph(repo.root)
        return {e.frm: e.mode for e in graph.edges if e.relation == pg.RELATION_ACCEPTS}

    assert definers() == {"docs-a": wg.CONFLICT, "docs-b": wg.CONFLICT}
    write_config(repo, f"connections:\n  providers:\n    {DOCS}: docs-b\n")
    assert definers() == {"docs-a": wg.NOT_SELECTED, "docs-b": wg.ACTIVE}


# --- the process graph is the wiring graph filtered to process edges ------------


def test_the_process_view_is_the_process_graph_plus_the_offered_processes(
    repo: AdopterRepo,
) -> None:
    process = pg.build_graph(repo.root)
    view = wg.process_view(wg.build_wiring_graph(repo.root))
    # Nothing the process graph draws is removed...
    assert set(process.edges) <= set(view.edges)
    assert set(process.nodes) <= set(view.nodes)
    assert view.skipped == process.skipped
    # ...and the one process edge the resolver adds is the offered process.
    assert _edges(view) - _edges(process) == {
        ("docs-a:page-review", REVIEW, "offers", "active", RESOLVED)
    }


def test_without_connections_the_process_view_equals_the_process_graph(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    _stage_flow(repo, generated=False)
    assert wg.process_view(wg.build_wiring_graph(repo.root)) == pg.build_graph(repo.root)


def test_process_graph_renders_the_filtered_wiring_graph(repo: AdopterRepo) -> None:
    """One graph computation: the process graph command, the connections graph
    narrowed to process edges and the wiring graph's process view — through the
    one filter pass both commands render with — are the same bytes."""
    rendered = pg.apply_filters(wg.process_view(wg.build_wiring_graph(repo.root)), pg.FilterSpec())
    runner = CliRunner()
    process_json = runner.invoke(main, ["process", "graph", "--json"])
    connections_json = runner.invoke(main, ["connections", "graph", "--kind", "process", "--json"])
    assert process_json.exit_code == 0, process_json.output
    assert process_json.output == pg.render_json(rendered) == connections_json.output
    adjacency = runner.invoke(main, ["--color", "never", "process", "graph"])
    cli_render.set_color(False)
    cli_render.set_wrap_width(cli_render.NO_WRAP)
    assert adjacency.output == pg.render_adjacency(rendered)


def test_process_graph_filters_apply_to_the_view(repo: AdopterRepo) -> None:
    result = CliRunner().invoke(main, ["process", "graph", "--source", "resolved", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert [(e["from"], e["relation"], e["to"]) for e in payload["edges"]] == [
        ("docs-a:page-review", "offers", REVIEW)
    ]
    focused = CliRunner().invoke(main, ["process", "graph", "--upstream-of", "flow:ship", "--json"])
    assert {e["to"] for e in json.loads(focused.output)["edges"]} == {"flow:check", REVIEW}


# --- determinism and the safety point --------------------------------------------


def test_the_graph_is_deterministic(repo: AdopterRepo, monkeypatch: pytest.MonkeyPatch) -> None:
    first = wg.build_wiring_graph(repo.root)
    second = wg.build_wiring_graph(repo.root)
    assert first == second
    assert list(first.edges) == sorted(first.edges, key=pg.Edge.sort_key)
    assert list(first.nodes) == sorted(first.nodes)
    cli_render.set_color(False)
    cli_render.set_wrap_width(cli_render.NO_WRAP)
    baseline = pg.render_json(first)
    cli_render.set_color(True)
    cli_render.set_wrap_width(40)
    monkeypatch.setenv("COLUMNS", "40")
    assert pg.render_json(second) == baseline
    assert "\033[" not in baseline
    runs = [CliRunner().invoke(main, ["connections", "graph", "--json"]).output for _ in range(2)]
    assert runs[0] == runs[1] == pg.render_json(pg.apply_filters(first, pg.FilterSpec()))


def test_the_graph_reads_declarations_only(
    repo: AdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """COR-038's safety point, and COR-053 point 7's: no position is resolved, no
    predicate and no filler command is run to draw the wiring."""

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("drawing the wiring must not resolve or run anything")

    for method in ("resolve_position", "can_move", "move"):
        monkeypatch.setattr(ProcessEngine, method, _boom)
    monkeypatch.setattr(command_runner, "run_command", _boom)
    graph = wg.build_wiring_graph(repo.root)
    for render in (pg.render_adjacency, pg.render_flow, pg.render_mermaid, pg.render_json):
        render(graph)
    assert len(graph.edges) == 10


# --- the renders ---------------------------------------------------------------------


def test_the_adjacency_view_reads_each_relation_both_ways(repo: AdopterRepo) -> None:
    cli_render.set_color(False)
    text = pg.render_adjacency(wg.build_wiring_graph(repo.root), title=wg.TITLE)
    assert text.startswith("Wiring graph  (configured topology)\n")
    for line in (
        f"◇ accepts {READERS}  [accepts · active]",
        "◇ accepted by docs-a  [accepts · active]",
        "◇ offered by docs-a:page-review  [offers · active]",
        "← gated by flow:ship  [gates-on-readiness · pull] @waiting",
        f"← filled by {READERS_FILLER}  [fills · bound]",
        "← contributed by old  [contributes · inert (version)]",
        f"→ contributes to {GLOSSARY}  [contributes · no active provider]",
        "◇ emitted by docs-a  [emits · active]",
        f"→ subscribes to {PAGE_CREATED}  [subscribes · bound]",
    ):
        assert line in text, line


def test_mermaid_draws_resolved_edges_and_file_nodes(repo: AdopterRepo) -> None:
    text = pg.render_mermaid(wg.build_wiring_graph(repo.root))
    assert "--o|contributes · bound|" in text
    assert "==>|composed-subprocess · pull|" in text
    ids = [line.split("[", 1)[0].strip() for line in text.splitlines()[1:] if "[" in line]
    assert all(i.replace("_", "").isalnum() for i in ids), ids
    assert len(set(ids)) == len(ids)


def test_connections_graph_command(repo: AdopterRepo) -> None:
    runner = CliRunner()
    plain = runner.invoke(main, ["--color", "never", "connections", "graph"])
    assert plain.exit_code == 0, plain.output
    assert plain.output.startswith("Wiring graph  (configured topology)\n")
    assert "The readers evidence has met." not in plain.output
    verbose = runner.invoke(main, ["--color", "never", "connections", "graph", "--verbose"])
    assert "The readers evidence has met." in verbose.output
    flow = runner.invoke(main, ["--color", "never", "connections", "graph", "--flow"])
    assert flow.output.startswith("Wiring flow  (downstream pipeline)\n")
    data = runner.invoke(main, ["connections", "graph", "--kind", "data", "--json"])
    nodes = json.loads(data.output)["nodes"]
    assert "flow:idle" not in nodes and "flow:ship" not in nodes and READERS in nodes
    both = runner.invoke(main, ["connections", "graph", "--json", "--flow"])
    assert both.exit_code != 0 and "choose at most one" in both.output


def test_connections_graph_of_an_empty_project(make_adopter_repo: MakeAdopterRepo) -> None:
    make_adopter_repo()
    runner = CliRunner()
    text = runner.invoke(main, ["--color", "never", "connections", "graph"]).output
    assert "(no installed processes and no connection points)" in text
    payload = json.loads(runner.invoke(main, ["connections", "graph", "--json"]).output)
    assert payload == {"nodes": [], "edges": [], "skipped": []}


def test_a_node_id_keeps_its_process_address_mapping() -> None:
    """Widening the mermaid id to file paths leaves a process address's id as it was."""
    assert pg._mermaid_node_id("alpha:ship-it") == "n_alpha__ship_it"  # pyright: ignore[reportPrivateUsage]
    assert pg._mermaid_node_id("a/b.yaml") != pg._mermaid_node_id("a.b/yaml")  # pyright: ignore[reportPrivateUsage]


def test_wiring_graph_nodes_are_every_endpoint(repo: AdopterRepo) -> None:
    graph = wg.build_wiring_graph(repo.root)
    endpoints = {e.frm for e in graph.edges} | {e.to for e in graph.edges}
    assert set(graph.nodes) == endpoints | {"flow:idle"}
    assert Path(READERS_FILLER).as_posix() in graph.nodes
