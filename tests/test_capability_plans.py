"""Tests for discovery (#998, COR-053 point 8): `pkit capabilities show` for
installed and uninstalled capabilities, the install and uninstall plans — each
checked against what the operation then does — and the suggestions the status
report makes from local catalogues only."""

from __future__ import annotations

import dataclasses
import json
import socket
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner
from ruamel.yaml import YAML

from project_kit import capabilities as caps
from project_kit import capability_plans as plans
from project_kit import cli as cli_mod
from project_kit import connections as cx
from project_kit import status as status_mod
from project_kit.cli import main
from project_kit.manifest import (
    ComponentRegistryEntry,
    read_backbone_manifest,
    write_backbone_manifest,
)
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo

DOCS = "pkit::documentation"
READERS = f"{DOCS}:readers"
REVIEW = f"{DOCS}:review"
PAGE_CREATED = f"{DOCS}:page-created"
ANALYSIS = "pkit::analysis"
GLOSSARY = f"{ANALYSIS}:glossary"
CONFIG = ".pkit/project/config.yaml"
READERS_FILLER = "docs/pkit/fillers/pkit/documentation/readers.yaml"
READERS_SCHEMA = {"type": "array", "items": {"type": "string"}}


# --- staging ----------------------------------------------------------------------


@pytest.fixture
def repo(make_adopter_repo: MakeAdopterRepo) -> AdopterRepo:
    return make_adopter_repo()


@pytest.fixture
def kit_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A scratch kit source, the one the CLI and the status report read."""
    source = tmp_path / ".kit-source"
    (source / "capabilities").mkdir(parents=True)
    monkeypatch.setattr(cli_mod, "find_source_kit", lambda: source)
    monkeypatch.setattr(status_mod, "find_source_kit", lambda: source)
    return source


def _package(name: str, connections: dict[str, Any] | None = None, **extra: Any) -> dict[str, Any]:
    package: dict[str, Any] = {
        "schema_version": 1,
        "component": {"kind": "capability", "name": name, "version": "0.2.0"},
        "description": f"Synthetic {name}.",
        "requires_backbone": ">=0.0.0",
        "commands": {"publish": {"script": "scripts/publish.py", "help": "Publish."}},
        **extra,
    }
    if connections is not None:
        package["connections"] = connections
    return package


def _write(cap_dir: Path, package: dict[str, Any]) -> Path:
    """A capability subtree: its package, README, script and point schema."""
    (cap_dir / "schemas").mkdir(parents=True, exist_ok=True)
    (cap_dir / "scripts").mkdir(exist_ok=True)
    (cap_dir / "scripts" / "publish.py").write_text("", encoding="utf-8")
    (cap_dir / "README.md").write_text(f"# {cap_dir.name}\n", encoding="utf-8")
    (cap_dir / "schemas" / "readers.schema.json").write_text(
        json.dumps(READERS_SCHEMA), encoding="utf-8"
    )
    with (cap_dir / "package.yaml").open("w", encoding="utf-8") as handle:
        YAML().dump(package, handle)
    return cap_dir


def _in_source(kit_source: Path, package: dict[str, Any]) -> Path:
    return _write(kit_source / "capabilities" / package["component"]["name"], package)


def _incubated(repo: AdopterRepo, package: dict[str, Any], *, register: bool = True) -> Path:
    """A capability authored in the repository, registered in place unless told not to."""
    name = package["component"]["name"]
    cap_dir = _write(repo.pkit / "capabilities" / name, package)
    if register:
        backbone = read_backbone_manifest(repo.root)
        assert backbone is not None
        backbone.components.append(
            ComponentRegistryEntry(
                kind="capability",
                name=name,
                manifest=f".pkit/capabilities/{name}/project/manifest.yaml",
                origin="incubated-in-repo",
            )
        )
        write_backbone_manifest(repo.root, backbone)
    return cap_dir


def _install(repo: AdopterRepo, kit_source: Path, name: str) -> None:
    source = caps.find_capability_in_source(kit_source, name)
    assert source is not None
    caps.install_capability(repo.root, source)


def _docs_provider(name: str = "docs-a", **extra: Any) -> dict[str, Any]:
    """Provides the documentation role: accepts `readers`, offers the `review`
    process and the `page-created` event."""
    return _package(
        name,
        {
            "roles": [DOCS],
            "extension-points": {
                "accepts": {
                    READERS: {
                        "schema_version": 1,
                        "schema": "readers.schema.json",
                        "description": "Who reads the documentation.",
                        "combination": "union",
                    }
                },
                "offers": {
                    REVIEW: {
                        "kind": "process",
                        "schema_version": 1,
                        "process": "review",
                        "description": "The page review.",
                    },
                    PAGE_CREATED: {
                        "kind": "event",
                        "schema_version": 1,
                        "command": "publish",
                        "description": "A page was written.",
                    },
                },
            },
        },
        **extra,
    )


def _consumer(name: str = "evidence", **extra: Any) -> dict[str, Any]:
    """Contributes to `readers`, subscribes to `page-created`, depends on `review`."""
    return _package(
        name,
        {
            "extensions": {
                "contributes": [
                    {
                        "point": READERS,
                        "schema_version": 1,
                        "value": ["auditor"],
                        "description": "Auditors read it.",
                    }
                ],
                "subscribes": [{"point": PAGE_CREATED, "schema_version": 1, "command": "publish"}],
                "depends-on": {"generated": True, "entries": [{"process": REVIEW}]},
            }
        },
        **extra,
    )


def _config(repo: AdopterRepo, **blocks: Any) -> None:
    repo.write({CONFIG: json.dumps({"name": "adopter", **blocks}, indent=2) + "\n"})


def _role_block_artefact(repo: AdopterRepo) -> None:
    """`notes` declared as a place, one note carrying a `documentation` role block."""
    _config(repo, friction={"places": ["notes"]})
    repo.write(
        {
            "notes/guide.md": "---\nid: guide\npkit:\n"
            "  documentation: {readers: {schema_version: 1}}\n---\n\nThe body.\n"
        }
    )


def _manifest_text(repo: AdopterRepo) -> str:
    return (repo.pkit / "manifest.yaml").read_text(encoding="utf-8")


def _candidate(repo: AdopterRepo, kit_source: Path, name: str) -> plans.Candidate:
    candidate = plans.find_candidate(repo.root, kit_source, name)
    assert candidate is not None
    return candidate


# --- show ---------------------------------------------------------------------------


def test_show_an_uninstalled_capability_from_its_package_metadata(
    repo: AdopterRepo, kit_source: Path
) -> None:
    _install(repo, kit_source, _in_source(kit_source, _docs_provider()).name)
    _in_source(kit_source, _consumer())
    view = plans.show(repo.root, _candidate(repo, kit_source, "evidence"))

    assert (view.installed, view.origin, view.version) == (False, "kit-shipped", "0.2.0")
    assert [(e.kind, e.target, e.schema_version) for e in view.extensions] == [
        ("contributes", READERS, 1),
        ("subscribes", PAGE_CREATED, 1),
        ("depends-on", REVIEW, None),
    ]
    assert view.extensions[0].description == "Auditors read it."
    # What would connect here: its three extensions reach docs-a, installed.
    assert [(c.direction, c.kind, c.status, c.provider) for c in view.connections] == [
        ("out", "subscribes", "bound", "docs-a"),
        ("out", "contributes", "bound", "docs-a"),
        ("out", "depends-on", "bound", "docs-a"),
    ]
    assert not caps.is_installed(repo.root, "evidence")


def test_show_an_installed_capability_reads_the_live_wiring(
    repo: AdopterRepo, kit_source: Path
) -> None:
    _in_source(kit_source, _docs_provider())
    _in_source(kit_source, _consumer())
    _install(repo, kit_source, "docs-a")
    _install(repo, kit_source, "evidence")
    view = plans.show(repo.root, _candidate(repo, kit_source, "docs-a"))

    assert view.installed and view.origin == "kit-shipped"
    assert [(r.role, r.state) for r in view.roles] == [(DOCS, "docs-a")]
    assert [(p.address, p.kind, p.policy) for p in view.accepts] == [(READERS, "data", "union")]
    assert sorted((p.address, p.kind) for p in view.offers) == [
        (PAGE_CREATED, "event"),
        (REVIEW, "process"),
    ]
    assert {(c.direction, c.capability, c.kind) for c in view.connections} == {
        ("in", "evidence", "contributes"),
        ("in", "evidence", "subscribes"),
        ("in", "evidence", "depends-on"),
    }


def test_show_an_unregistered_capability_authored_in_the_repository(
    repo: AdopterRepo, kit_source: Path
) -> None:
    _incubated(repo, _docs_provider("docs-local"), register=False)
    result = CliRunner().invoke(main, ["capabilities", "show", "docs-local", "--json"])

    assert result.exit_code == 0, result.output
    document = json.loads(result.output)
    assert (document["origin"], document["installed"]) == ("incubated-in-repo", False)
    assert document["roles"] == [
        {"role": DOCS, "state": "docs-local", "providers": ["docs-local"], "active": "docs-local"}
    ]


def test_show_renders_every_section_and_refuses_an_unknown_name(
    repo: AdopterRepo, kit_source: Path
) -> None:
    _in_source(kit_source, _docs_provider())
    runner = CliRunner()
    result = runner.invoke(main, ["capabilities", "show", "docs-a"])
    assert result.exit_code == 0, result.output
    assert "Capability 'docs-a' v0.2.0 (kit-shipped, not installed)" in result.output
    for heading in (
        "Roles it provides (1)",
        "Points it accepts (1)",
        "Points it offers (2)",
        "Extensions (0)",
        "What connects here (0)",
    ):
        assert heading in result.output
    assert f"{READERS} (data v1, union) — Who reads the documentation." in result.output

    missing = runner.invoke(main, ["capabilities", "show", "nothing-here"])
    assert missing.exit_code != 0
    assert "no capability named 'nothing-here'" in missing.output


# --- the install plan -----------------------------------------------------------------


def test_the_install_plan_is_what_the_install_then_does(
    repo: AdopterRepo, kit_source: Path
) -> None:
    _in_source(kit_source, _docs_provider())
    _install(repo, kit_source, "docs-a")
    consumer = _consumer()
    # A contribution to a point the role does not define: warned in its own package.
    consumer["connections"]["extensions"]["contributes"].append(
        {"point": f"{DOCS}:nowhere", "schema_version": 1, "value": []}
    )
    source = caps.find_capability_in_source(kit_source, _in_source(kit_source, consumer).name)
    assert source is not None

    before = cx.resolve_wiring(repo.root)
    candidate = plans.candidate_of(source, caps.KIT_SHIPPED, installed=False)
    assert candidate is not None
    plan = plans.plan_install(repo.root, candidate)
    caps.install_capability(repo.root, source)
    after = cx.resolve_wiring(repo.root)

    assert plan.diff == plans.diff_wiring(repo.root, before, after)
    assert [(c.capability, c.kind, c.provider_after) for c in plan.diff.made] == [
        ("evidence", "contributes", "docs-a"),
        ("evidence", "depends-on", "docs-a"),
        ("evidence", "subscribes", "docs-a"),
    ]
    # Located where the install puts the package, as the live wiring then locates it.
    assert [(f.where, f.severity) for f in plan.diff.findings_added] == [
        (
            ".pkit/capabilities/evidence/package.yaml:/connections/extensions/contributes/1",
            "warning",
        )
    ]
    assert plan.conflicts == () and plan.needs == ()


def test_the_install_plan_names_a_role_conflict_and_how_to_resolve_it(
    repo: AdopterRepo, kit_source: Path
) -> None:
    _in_source(kit_source, _docs_provider())
    _in_source(kit_source, _consumer())
    _in_source(kit_source, _docs_provider("docs-b"))
    _install(repo, kit_source, "docs-a")
    _install(repo, kit_source, "evidence")
    before = cx.resolve_wiring(repo.root)

    result = CliRunner().invoke(main, ["capabilities", "install", "docs-b", "--plan", "--json"])
    assert result.exit_code == 0, result.output
    document = json.loads(result.output)
    assert document["operation"] == "install"
    assert document["conflicts"] == [
        {
            "role": DOCS,
            "providers": ["docs-a", "docs-b"],
            "resolve": [
                f"pkit connections providers set {DOCS} docs-a",
                f"pkit connections providers set {DOCS} docs-b",
            ],
        }
    ]
    # The conflict breaks evidence's three connections until a provider is selected.
    lost = [c for c in document["diff"]["connections"] if c["before"] == "bound"]
    assert {(c["kind"], c["after"]) for c in lost} == {
        ("contributes", "no active provider"),
        ("subscribes", "no active provider"),
        ("depends-on", "no active provider"),
    }
    assert not caps.is_installed(repo.root, "docs-b")

    # Then the install does exactly that.
    assert CliRunner().invoke(main, ["capabilities", "install", "docs-b"]).exit_code == 0
    actual = plans.diff_wiring(repo.root, before, cx.resolve_wiring(repo.root))
    assert _as_document(actual) == document["diff"]


def _as_document(diff: plans.WiringDiff) -> Any:
    """A wiring difference in a plan's machine form."""
    return json.loads(json.dumps(dataclasses.asdict(diff)))


def test_the_install_plan_lists_what_the_capability_needs(
    repo: AdopterRepo, kit_source: Path
) -> None:
    needy = _package(
        "needy",
        {
            "extensions": {
                "contributes": [
                    {
                        "point": GLOSSARY,
                        "schema_version": 1,
                        "value": [],
                        "mandatory": {"reason": "the glossary feeds our pages"},
                    }
                ]
            }
        },
        requires_capabilities=[{"name": "absent", "version": ">=1.0.0"}],
    )
    _in_source(kit_source, needy)
    result = CliRunner().invoke(main, ["capabilities", "install", "needy", "--plan"])

    assert result.exit_code == 0, result.output
    assert "What it needs (2)" in result.output
    assert "mandatory contributes entry for 'pkit::analysis:glossary' has no provider" in (
        result.output
    )
    assert "[capability dependency range]" in result.output
    assert "requires capability 'absent' >=1.0.0, which is not installed" in result.output


def test_a_plan_writes_nothing_and_json_needs_the_plan(repo: AdopterRepo, kit_source: Path) -> None:
    _in_source(kit_source, _docs_provider())
    manifest = _manifest_text(repo)
    runner = CliRunner()
    assert runner.invoke(main, ["capabilities", "install", "docs-a", "--plan"]).exit_code == 0
    assert _manifest_text(repo) == manifest
    assert not (repo.pkit / "capabilities" / "docs-a").exists()

    alone = runner.invoke(main, ["capabilities", "install", "docs-a", "--json"])
    assert alone.exit_code != 0
    assert "--json prints the plan: pass it with --plan" in alone.output


def test_the_install_plan_lists_role_blocks_it_adopts(repo: AdopterRepo, kit_source: Path) -> None:
    _role_block_artefact(repo)
    _in_source(kit_source, _docs_provider())
    plan = plans.plan_install(repo.root, _candidate(repo, kit_source, "docs-a"))
    assert plan.role_blocks == (
        plans.RoleBlockChange("notes/guide.md", "documentation", plans.ADOPTED),
    )


def test_the_install_plan_lists_bare_role_keys_it_makes_ambiguous(
    repo: AdopterRepo, kit_source: Path
) -> None:
    _role_block_artefact(repo)
    _in_source(kit_source, _docs_provider())
    _install(repo, kit_source, "docs-a")
    other = _docs_provider("super-docs")
    other["connections"]["roles"] = ["super-docs::documentation"]
    other["connections"]["extension-points"] = {}
    _in_source(kit_source, other)
    plan = plans.plan_install(repo.root, _candidate(repo, kit_source, "super-docs"))
    assert plan.role_blocks == (
        plans.RoleBlockChange("notes/guide.md", "documentation", plans.AMBIGUOUS),
    )


# --- the uninstall plan -------------------------------------------------------------


def test_the_uninstall_plan_is_what_the_uninstall_then_does(
    repo: AdopterRepo, kit_source: Path
) -> None:
    _in_source(kit_source, _docs_provider())
    _in_source(kit_source, _consumer())
    _install(repo, kit_source, "docs-a")
    _install(repo, kit_source, "evidence")
    _role_block_artefact(repo)
    _config(repo, friction={"places": ["notes"]}, connections={"providers": {DOCS: "docs-a"}})
    repo.write({READERS_FILLER: "schema_version: 1\nvalue: [operator]\n"})

    before = cx.resolve_wiring(repo.root)
    plan = plans.plan_uninstall(repo.root, "docs-a", caps.KIT_SHIPPED)
    caps.uninstall_capability(repo.root, "docs-a")
    after = cx.resolve_wiring(repo.root)

    assert plan.diff == plans.diff_wiring(repo.root, before, after)
    assert plan.fillers_lost == (
        plans.FillerLoss(READERS, READERS_FILLER, "project filler", plans.NO_LONGER_DEFINED),
    )
    assert [(c.capability, c.kind, c.after) for c in plan.left_without_provider] == [
        ("evidence", "contributes", "no active provider"),
        ("evidence", "depends-on", "no active provider"),
        ("evidence", "subscribes", "no active provider"),
    ]
    assert plan.role_blocks == (
        plans.RoleBlockChange("notes/guide.md", "documentation", plans.ORPHANED),
    )
    assert plan.selections == (f"connections.providers.{DOCS}",)
    assert [p.address for p in plan.diff.points_undefined] == [PAGE_CREATED, READERS, REVIEW]


def test_the_uninstall_plan_lists_the_contributions_lost(
    repo: AdopterRepo, kit_source: Path
) -> None:
    _incubated(repo, _docs_provider())
    _incubated(repo, _consumer())
    before = cx.resolve_wiring(repo.root)

    runner = CliRunner()
    planned = runner.invoke(main, ["capabilities", "uninstall", "evidence", "--plan", "--json"])
    assert planned.exit_code == 0, planned.output
    document = json.loads(planned.output)
    assert document["operation"] == "uninstall"
    assert document["fillers_lost"] == [
        {
            "point": READERS,
            "filler": "evidence",
            "source": "contribution",
            "point_after": plans.LEFT_UNFILLED,
        }
    ]
    assert document["left_without_provider"] == []
    assert caps.is_installed(repo.root, "evidence")

    # Incubated: unregistered in place, and the wiring moves exactly as planned.
    assert runner.invoke(main, ["capabilities", "uninstall", "evidence"]).exit_code == 0
    actual = plans.diff_wiring(repo.root, before, cx.resolve_wiring(repo.root))
    assert _as_document(actual) == document["diff"]


def test_the_uninstall_plan_renders_its_sections(repo: AdopterRepo, kit_source: Path) -> None:
    _incubated(repo, _docs_provider())
    _incubated(repo, _consumer())
    result = CliRunner().invoke(main, ["capabilities", "uninstall", "docs-a", "--plan"])

    assert result.exit_code == 0, result.output
    assert "Uninstall plan — capability 'docs-a' v0.2.0 (incubated-in-repo)" in result.output
    assert "Processes left without a provider (1)" in result.output
    assert f"evidence depends-on {REVIEW} → docs-a: bound → no active provider" in result.output
    assert "Other counterparts left without a provider (2)" in result.output
    assert caps.is_installed(repo.root, "docs-a")


# --- suggestions and the local catalogue ----------------------------------------------


def test_status_suggests_a_catalogue_capability_for_an_unfilled_point_without_the_network(
    repo: AdopterRepo, kit_source: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _incubated(repo, _docs_provider())
    _in_source(kit_source, _consumer())

    def no_network(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("a suggestion reached for the network")

    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setattr(socket, "create_connection", no_network)
    manifest = _manifest_text(repo)
    result = CliRunner().invoke(main, ["status"])

    assert result.exit_code == 0, result.output
    assert "suggested          1 from local catalogues (nothing is installed):" in result.output
    assert (
        f"{READERS} (unfilled point): evidence (kit-shipped) contributes to it at version 1 — "
        "see `pkit capabilities show evidence`"
    ) in result.output
    assert _manifest_text(repo) == manifest  # a suggestion is never an action


def test_suggestions_name_a_provider_for_a_role_and_an_upstream_not_installed(
    repo: AdopterRepo, kit_source: Path
) -> None:
    consumer = _consumer()
    consumer["connections"]["extensions"]["depends-on"]["entries"].append(
        {"process": "reviews:triage"}
    )
    _incubated(repo, consumer)
    _in_source(kit_source, _docs_provider())
    _in_source(kit_source, _package("reviews"))
    found = plans.suggest(repo.root, kit_source)

    assert [(s.need, s.reason, s.capability) for s in found] == [
        (DOCS, "role without a provider", "docs-a"),
        ("reviews", "upstream not installed", "reviews"),
    ]


def test_an_installed_capability_or_an_incompatible_one_is_not_suggested(
    repo: AdopterRepo, kit_source: Path
) -> None:
    _incubated(repo, _docs_provider())
    stale = _consumer("stale")
    stale["connections"]["extensions"]["contributes"][0]["schema_version"] = 2
    _in_source(kit_source, stale)
    _in_source(kit_source, _docs_provider())  # installed under the same name in the repo
    assert plans.suggest(repo.root, kit_source) == ()
    result = CliRunner().invoke(main, ["status"])
    assert "suggested" not in result.output


def test_the_local_catalogue_reads_installed_then_in_repo_then_kit_source(
    repo: AdopterRepo, kit_source: Path
) -> None:
    _incubated(repo, _docs_provider())
    _incubated(repo, _package("drafting"), register=False)
    _in_source(kit_source, _package("drafting"))
    _in_source(kit_source, _package("shipped"))
    catalogue = caps.local_catalogue(repo.root, kit_source)

    assert [(e.source.name, e.origin, e.installed) for e in catalogue] == [
        ("docs-a", "incubated-in-repo", True),
        ("drafting", "incubated-in-repo", False),
        ("shipped", "kit-shipped", False),
    ]


def test_an_unregistered_capability_in_the_kit_source_itself_is_kit_shipped(
    repo: AdopterRepo,
) -> None:
    """The methodology's own repository: its `.pkit/` is the kit source."""
    _incubated(repo, _package("shipped"), register=False)
    (entry,) = [e for e in caps.local_catalogue(repo.root, repo.pkit) if e.source.name == "shipped"]
    assert (entry.origin, entry.installed) == ("kit-shipped", False)


def test_status_still_resolves_the_wiring_once_with_suggestions(
    repo: AdopterRepo, kit_source: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _incubated(repo, _docs_provider())
    _in_source(kit_source, _consumer())
    calls: list[Path] = []
    wiring = cx.resolve_wiring

    def counting(root: Path) -> cx.Wiring:
        calls.append(root)
        return wiring(root)

    monkeypatch.setattr(cx, "resolve_wiring", counting)
    result = CliRunner().invoke(main, ["status"])
    assert result.exit_code == 0, result.output
    assert "suggested" in result.output
    assert len(calls) == 1
