"""The generated `depends-on` list (#995, COR-053 point 4): what a capability's
process definitions generate, when the package's copy is stale, the validation
error that names the fix, and `pkit capabilities refresh` — which rewrites only
that list, marks it generated, and refuses a kit-shipped package in an adopter."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner
from ruamel.yaml import YAML

from project_kit import cli as cli_mod
from project_kit import process_dependencies as deps
from project_kit.cli import main
from project_kit.manifest import (
    ComponentRegistryEntry,
    read_backbone_manifest,
    write_backbone_manifest,
)
from project_kit.process_dependencies import Entry
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo

ISSUES = "tracker:issue-lifecycle"
REVIEW = "pkit::documentation:review"
PACKAGE = """\
# The flow capability's package metadata — a comment refresh must keep.
schema_version: 1
component:
  kind: capability
  name: flow
  version: 0.1.0
description: A capability whose process depends on others.
requires_backbone: '>=0.0.0'
footprint:
  - flow/notes.md
"""


def _definition(process_id: str, *states: list[dict[str, Any]]) -> str:
    """A process definition whose states carry the given `depends_on` lists."""
    document = {
        "process": {
            "id": process_id,
            "version": 1,
            "subject": {"cardinality": "singleton"},
            "states": [
                {
                    "id": f"s{index}",
                    "meaning": "A state.",
                    "detection": {"mode": "inferred", "predicate": {"run": "detect"}},
                    **({"depends_on": entries} if entries else {}),
                }
                for index, entries in enumerate(states)
            ],
            "transitions": [],
        }
    }
    return _dump(document)


def _coupling(upstream: str, **extra: Any) -> dict[str, Any]:
    return {
        "upstream": upstream,
        "relation": "gates-on-readiness",
        "mode": "pull",
        "why": "It waits on the upstream.",
        **extra,
    }


def _dump(document: Any) -> str:
    buffer = io.StringIO()
    YAML().dump(document, buffer)
    return buffer.getvalue()


def _capability(root: Path, package: str = PACKAGE, **definitions: str) -> Path:
    cap_dir = root / ".pkit" / "capabilities" / "flow"
    (cap_dir / "schemas").mkdir(parents=True, exist_ok=True)
    (cap_dir / "package.yaml").write_text(package, encoding="utf-8")
    (cap_dir / "README.md").write_text("# flow\n", encoding="utf-8")
    for process_id, text in definitions.items():
        (cap_dir / "schemas" / f"{process_id}.yaml").write_text(text, encoding="utf-8")
    return cap_dir


def _register(repo: AdopterRepo, name: str, *, origin: str | None) -> None:
    """Register `name` in the backbone manifest; no origin reads as kit-shipped."""
    backbone = read_backbone_manifest(repo.root)
    assert backbone is not None
    backbone.components.append(
        ComponentRegistryEntry(
            kind="capability",
            name=name,
            manifest=f".pkit/capabilities/{name}/project/manifest.yaml",
            **({"origin": origin} if origin is not None else {}),
        )
    )
    write_backbone_manifest(repo.root, backbone)


def _package(cap_dir: Path) -> Any:
    return YAML(typ="safe").load((cap_dir / "package.yaml").read_text(encoding="utf-8"))


@pytest.fixture
def kit_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A scratch kit source, so the project under test is never the self-host: the
    self-host is the kit source's parent (`install.is_self_host`), so it sits one
    level below the project root."""
    source = tmp_path / "elsewhere" / ".kit-source"
    (source / "capabilities").mkdir(parents=True)
    monkeypatch.setattr(cli_mod, "find_source_kit", lambda: source)
    return source


# --- what the definitions generate --------------------------------------------


def test_one_entry_per_upstream_and_version_sorted_with_marks_merged(tmp_path: Path) -> None:
    cap_dir = _capability(
        tmp_path,
        intake=_definition(
            "intake",
            [_coupling(REVIEW, version=2), _coupling(ISSUES, mandatory={"reason": "issues first"})],
            [_coupling(ISSUES, relation="informational"), _coupling(REVIEW, version=3)],
        ),
        build=_definition(
            "build",
            [_coupling(ISSUES, mandatory={"reason": "builds track issues"})],
            [_coupling(ISSUES, mandatory={"reason": "issues first"})],
        ),
    )
    # Not a definition: a companion schema file and a YAML file that does not parse.
    (cap_dir / "schemas" / "notes.yaml").write_text("title: not a process\n", encoding="utf-8")
    (cap_dir / "schemas" / "broken.yaml").write_text("process: [unclosed\n", encoding="utf-8")

    assert deps.generated_entries(cap_dir) == (
        Entry(REVIEW, 2),
        Entry(REVIEW, 3),
        # `build.yaml` sorts before `intake.yaml`: its reason comes first.
        Entry(ISSUES, None, "builds track issues; issues first"),
    )


def test_a_capability_without_definitions_generates_nothing(tmp_path: Path) -> None:
    assert deps.generated_entries(_capability(tmp_path)) == ()


# --- staleness -------------------------------------------------------------------


def _with_list(entries: list[dict[str, Any]], *, generated: bool = True) -> str:
    block: dict[str, Any] = {"entries": entries}
    if generated:
        block = {"generated": True, **block}
    return PACKAGE + _dump({"connections": {"extensions": {"depends-on": block}}})


def test_a_fresh_list_is_not_stale_whatever_order_it_is_written_in(tmp_path: Path) -> None:
    cap_dir = _capability(
        tmp_path,
        _with_list([{"process": REVIEW}, {"process": ISSUES, "mandatory": {"reason": "r"}}]),
        flow=_definition("flow", [_coupling(ISSUES, mandatory={"reason": "r"}), _coupling(REVIEW)]),
    )
    assert deps.staleness(_package(cap_dir), cap_dir) is None


def test_no_definitions_and_no_list_is_fresh(tmp_path: Path) -> None:
    cap_dir = _capability(tmp_path)
    assert deps.staleness(_package(cap_dir), cap_dir) is None


def test_a_missing_list_is_stale_at_its_nearest_present_ancestor(tmp_path: Path) -> None:
    cap_dir = _capability(tmp_path, flow=_definition("flow", [_coupling(ISSUES)]))
    stale = deps.staleness(_package(cap_dir), cap_dir)
    assert stale is not None
    assert stale.pointer == ""  # no `connections` block at all
    assert stale.missing == (Entry(ISSUES),) and stale.extra == ()
    message = stale.message("flow")
    assert "missing 'tracker:issue-lifecycle'" in message
    assert "`pkit capabilities refresh flow`" in message


def test_a_changed_mark_or_version_and_an_undeclared_entry_are_stale(tmp_path: Path) -> None:
    cap_dir = _capability(
        tmp_path,
        _with_list([{"process": ISSUES}, {"process": REVIEW, "schema_version": 1}]),
        flow=_definition("flow", [_coupling(ISSUES, mandatory={"reason": "issues first"})]),
    )
    stale = deps.staleness(_package(cap_dir), cap_dir)
    assert stale is not None
    assert stale.pointer == "/connections/extensions/depends-on"
    assert stale.missing == (Entry(ISSUES, None, "issues first"),)
    assert stale.extra == (Entry(ISSUES), Entry(REVIEW, 1))
    assert "declared by no definition 'tracker:issue-lifecycle', " in stale.message("flow")


def test_a_list_without_the_generated_mark_is_stale(tmp_path: Path) -> None:
    cap_dir = _capability(
        tmp_path,
        _with_list([{"process": ISSUES}], generated=False),
        flow=_definition("flow", [_coupling(ISSUES)]),
    )
    stale = deps.staleness(_package(cap_dir), cap_dir)
    assert stale is not None and "not marked `generated: true`" in stale.message("flow")


# --- validation fails on a stale copy, naming the fix ---------------------------------


def test_pkit_validate_fails_on_a_stale_list_and_names_the_refresh(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    _capability(repo.root, flow=_definition("flow", [_coupling(ISSUES)]))
    _register(repo, "flow", origin="incubated-in-repo")

    result = CliRunner().invoke(main, ["validate", "--no-refs"])
    assert result.exit_code == 1, result.output
    assert "the generated `depends-on` list is stale" in result.output
    assert "`pkit capabilities refresh flow`" in result.output

    refreshed = CliRunner().invoke(main, ["capabilities", "refresh", "flow"])
    assert refreshed.exit_code == 0, refreshed.output
    after = CliRunner().invoke(main, ["validate", "--no-refs"])
    assert "the generated `depends-on` list is stale" not in after.output


def test_register_refuses_a_capability_whose_list_is_stale(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """The register pre-flight runs the same package validation (COR-031 D1)."""
    repo = make_adopter_repo()
    _capability(repo.root, flow=_definition("flow", [_coupling(ISSUES)]))
    result = CliRunner().invoke(main, ["capabilities", "register", "flow"])
    assert result.exit_code != 0
    assert "the generated `depends-on` list is stale" in result.output


# --- `pkit capabilities refresh` --------------------------------------------------------


def test_refresh_writes_the_list_marked_generated_and_keeps_the_rest(
    make_adopter_repo: MakeAdopterRepo, kit_source: Path
) -> None:
    repo = make_adopter_repo()
    cap_dir = _capability(
        repo.root,
        flow=_definition(
            "flow",
            [_coupling(REVIEW, version=2), _coupling(ISSUES, mandatory={"reason": "issues first"})],
        ),
    )
    result = CliRunner().invoke(main, ["capabilities", "refresh", "flow"])
    assert result.exit_code == 0, result.output
    assert "Refreshed `connections.extensions.depends-on`" in result.output
    assert "2 entry(ies)" in result.output

    text = (cap_dir / "package.yaml").read_text(encoding="utf-8")
    assert text.startswith(PACKAGE)  # every byte before the list, the comment included
    assert _package(cap_dir)["connections"] == {
        "extensions": {
            "depends-on": {
                "generated": True,
                "entries": [
                    {"process": REVIEW, "schema_version": 2},
                    {"process": ISSUES, "mandatory": {"reason": "issues first"}},
                ],
            }
        }
    }

    again = CliRunner().invoke(main, ["capabilities", "refresh", "flow"])
    assert again.exit_code == 0 and "is fresh (2 entry(ies)); nothing to write" in again.output
    assert (cap_dir / "package.yaml").read_text(encoding="utf-8") == text


def test_refresh_drops_the_list_and_the_parents_it_empties(
    make_adopter_repo: MakeAdopterRepo, kit_source: Path
) -> None:
    repo = make_adopter_repo()
    cap_dir = _capability(repo.root, _with_list([{"process": ISSUES}]))
    result = CliRunner().invoke(main, ["capabilities", "refresh", "flow"])
    assert result.exit_code == 0, result.output
    assert "connections" not in _package(cap_dir)
    assert (cap_dir / "package.yaml").read_text(encoding="utf-8") == PACKAGE


def test_refresh_dry_run_writes_nothing(
    make_adopter_repo: MakeAdopterRepo, kit_source: Path
) -> None:
    repo = make_adopter_repo()
    cap_dir = _capability(repo.root, flow=_definition("flow", [_coupling(ISSUES)]))
    result = CliRunner().invoke(main, ["capabilities", "refresh", "flow", "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "Would refresh" in result.output and "'tracker:issue-lifecycle'" in result.output
    assert (cap_dir / "package.yaml").read_text(encoding="utf-8") == PACKAGE


def test_refresh_refuses_a_kit_shipped_package_in_an_adopter(
    make_adopter_repo: MakeAdopterRepo, kit_source: Path
) -> None:
    repo = make_adopter_repo()
    cap_dir = _capability(repo.root, flow=_definition("flow", [_coupling(ISSUES)]))
    _register(repo, "flow", origin=None)  # kit-shipped, the default origin
    result = CliRunner().invoke(main, ["capabilities", "refresh", "flow"])
    assert result.exit_code != 0
    assert "kit-shipped: its package.yaml is core-owned" in result.output
    assert (cap_dir / "package.yaml").read_text(encoding="utf-8") == PACKAGE


def test_refresh_needs_an_authored_capability(
    make_adopter_repo: MakeAdopterRepo, kit_source: Path
) -> None:
    make_adopter_repo()
    result = CliRunner().invoke(main, ["capabilities", "refresh", "nowhere"])
    assert result.exit_code != 0
    assert "no capability named 'nowhere' is authored in this repository" in result.output
