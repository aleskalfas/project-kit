"""Tests for data-point resolution (#994; COR-052, COR-053 point 2): the project
filler file and its envelope, capability contributions, the definer's default
and how it takes part, the three policies with precedence, whole-entry and
removal overrides, the contributor selection, the inert policy — and the
`connections` member of `pkit validate` that reports it, over one wiring per run."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner
from ruamel.yaml import YAML

from project_kit import backbone_schemas as bs
from project_kit import command_runner
from project_kit import connections as cx
from project_kit import data_points as dp
from project_kit import package_validate as pv
from project_kit import validators
from project_kit.cli import main
from project_kit.manifest import (
    ComponentRegistryEntry,
    read_backbone_manifest,
    write_backbone_manifest,
)
from project_kit.report_context import project_config_path
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo

DOCS = "pkit::documentation"
READERS = f"{DOCS}:readers"
TOOL = f"{DOCS}:tool"
FILLERS = "docs/pkit/fillers"
READERS_FILE = f"{FILLERS}/pkit/documentation/readers.yaml"
TOOL_FILE = f"{FILLERS}/pkit/documentation/tool.yaml"

# A union / additive point: a list of entries, each a string or a mapping with an id.
ENTRIES_SCHEMA = {
    "type": "array",
    "items": {
        "anyOf": [
            {"type": "string"},
            {
                "type": "object",
                "required": ["id"],
                "properties": {"id": {"type": "string"}, "role": {"type": "string"}},
                "additionalProperties": False,
            },
        ]
    },
}
# A single point: one mapping.
TOOL_SCHEMA = {
    "type": "object",
    "required": ["name"],
    "properties": {"name": {"type": "string"}},
    "additionalProperties": False,
}
SCHEMAS = {"readers.schema.json": ENTRIES_SCHEMA, "tool.schema.json": TOOL_SCHEMA}

W = validators.Severity.WARNING
E = validators.Severity.ERROR


# --- staging ------------------------------------------------------------------


@pytest.fixture
def repo(make_adopter_repo: MakeAdopterRepo) -> AdopterRepo:
    return make_adopter_repo()


def _stage(repo: AdopterRepo, name: str, connections: dict[str, Any], **extra: Any) -> None:
    """A synthetic capability registered as incubated, with the two point schemas."""
    cap_dir = repo.pkit / "capabilities" / name
    (cap_dir / "schemas").mkdir(parents=True, exist_ok=True)
    (cap_dir / "scripts").mkdir(exist_ok=True)
    (cap_dir / "scripts" / "noop.py").write_text("", encoding="utf-8")
    for file, schema in SCHEMAS.items():
        (cap_dir / "schemas" / file).write_text(json.dumps(schema), encoding="utf-8")
    package: dict[str, Any] = {
        "schema_version": 2,
        "component": {"kind": "capability", "name": name, "version": "0.1.0"},
        "description": f"Synthetic {name}.",
        "requires_backbone": ">=0.0.0",
        "commands": {"noop": {"script": "scripts/noop.py", "help": "Nothing."}},
        "connections": connections,
        **extra,
    }
    with (cap_dir / "package.yaml").open("w", encoding="utf-8") as handle:
        YAML().dump(package, handle)
    backbone = read_backbone_manifest(repo.root)
    assert backbone is not None
    if not any(e.name == name for e in backbone.components):
        backbone.components.append(
            ComponentRegistryEntry(
                kind="capability",
                name=name,
                manifest=f".pkit/capabilities/{name}/project/manifest.yaml",
                origin="incubated-in-repo",
            )
        )
        write_backbone_manifest(repo.root, backbone)


def _provider(
    repo: AdopterRepo,
    address: str = READERS,
    *,
    combination: str | None = "union",
    default: dict[str, Any] | None = None,
    inert: str | None = None,
    version: int = 1,
    name: str = "docs-a",
) -> None:
    point: dict[str, Any] = {
        "schema_version": version,
        "schema": "readers.schema.json" if address == READERS else "tool.schema.json",
        "description": "Who reads the documentation.",
    }
    if combination is not None:
        point["combination"] = combination
    if default is not None:
        point["default"] = default
    if inert is not None:
        point["inert"] = inert
    _stage(repo, name, {"roles": [DOCS], "extension-points": {"accepts": {address: point}}})


def _contributor(
    repo: AdopterRepo, name: str, value: Any, *, address: str = READERS, version: int = 1
) -> None:
    entry = {"point": address, "schema_version": version, "value": value}
    _stage(repo, name, {"extensions": {"contributes": [entry]}})


def _filler(repo: AdopterRepo, document: Any, path: str = READERS_FILE) -> None:
    text = document if isinstance(document, str) else json.dumps(document)
    repo.write({path: text})


def _config(repo: AdopterRepo, text: str) -> None:
    path = project_config_path(repo.root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _resolve(repo: AdopterRepo) -> dp.DataResolution:
    return dp.resolve_data_points(repo.root)


def _point(repo: AdopterRepo, address: str = READERS) -> dp.ResolvedPoint:
    point = _resolve(repo).point(address)
    assert point is not None
    return point


def _states(point: dp.ResolvedPoint) -> dict[str, tuple[str, str]]:
    return {f.name: (f.state.value, f.reason) for f in point.fillers}


def _findings(resolution: dp.DataResolution) -> list[tuple[str, str]]:
    return [(f.location, f.severity.value) for f in resolution.findings]


# --- the filler path: the location rule (ADR-056 point 2) --------------------------


@pytest.mark.parametrize(
    ("address", "subpath"),
    [
        ("pkit::documentation:readers", "pkit/documentation/readers.yaml"),
        ("super-docs::documentation:readers", "super-docs/documentation/readers.yaml"),
        ("pkit::analysis:revalidation-evidence", "pkit/analysis/revalidation-evidence.yaml"),
    ],
)
def test_an_address_maps_to_its_filler_path_and_back(address: str, subpath: str) -> None:
    assert str(bs.filler_subpath(address)) == subpath
    assert bs.filler_address(subpath) == address


@pytest.mark.parametrize(
    "address", ["pkit::Documentation:readers", "pkit:documentation:readers", "pkit::docs", "a::b:c.d"]
)
def test_an_address_outside_the_word_grammar_has_no_filler_path(address: str) -> None:
    assert bs.filler_subpath(address) is None


@pytest.mark.parametrize(
    "subpath",
    ["pkit/documentation.yaml", "a/b/c/d.yaml", "pkit/documentation/readers.yml", "pkit/Doc/readers.yaml"],
)
def test_a_path_that_names_no_point_has_no_address(subpath: str) -> None:
    assert bs.filler_address(subpath) is None


# --- the envelope -------------------------------------------------------------------


def test_the_project_filler_is_read_at_the_path_its_address_maps_to(repo: AdopterRepo) -> None:
    _provider(repo)
    _filler(repo, {"schema_version": 1, "value": ["operator"]})
    assert cx.project_filler(repo.root, READERS) == cx.ProjectFiller(repo.root / READERS_FILE, 1)
    point = _point(repo)
    assert point.resolved and point.value == ["operator"]
    assert _states(point) == {READERS_FILE: ("taken", "")}
    assert _resolve(repo).findings == ()


def test_the_prefix_follows_the_internal_documentation_root(repo: AdopterRepo) -> None:
    _provider(repo)
    _config(repo, "docs:\n  internal: tech-docs\n")
    _filler(repo, {"schema_version": 1, "value": ["operator"]}, path=READERS_FILE)
    assert cx.project_filler(repo.root, READERS) is None  # under the old root: not a filler
    moved = READERS_FILE.replace("docs/", "tech-docs/", 1)
    _filler(repo, {"schema_version": 1, "value": ["operator"]}, path=moved)
    assert cx.project_filler(repo.root, READERS) == cx.ProjectFiller(repo.root / moved, 1)


def test_a_malformed_envelope_is_an_error_and_fills_nothing(repo: AdopterRepo) -> None:
    _provider(repo, default={"value": ["guest"], "participation": "alone"})
    _filler(repo, {"schema_versoin": 1, "value": ["operator"]})
    resolution = _resolve(repo)
    messages = {f.location: f.message for f in resolution.findings}
    assert sorted(_findings(resolution)) == [
        (READERS_FILE, "error"),
        (f"{READERS_FILE}:/schema_versoin", "error"),
    ]
    assert "'schema_version' is a required property" in messages[READERS_FILE]
    assert "unknown key 'schema_versoin'; did you mean 'schema_version'?" in (
        messages[f"{READERS_FILE}:/schema_versoin"]
    )
    point = resolution.point(READERS)
    assert point is not None and not point.resolved
    assert _states(point)[READERS_FILE] == ("inert", "its envelope is malformed")
    # A declared filler broke: the `alone` default is not promoted (COR-052 point 6).
    assert _states(point)["docs-a"] == ("passed over", "not promoted: a declared filler is inert")


def test_a_project_filler_at_the_wrong_version_is_an_error_and_is_not_read(
    repo: AdopterRepo,
) -> None:
    """The version relation fails validation; the resolution does not read the value,
    and the `alone` default is not promoted in its place."""
    _provider(repo, version=2, default={"value": ["guest"], "participation": "alone"})
    _filler(repo, {"schema_version": 1, "value": ["operator"]})
    wiring = cx.resolve_wiring(repo.root)
    (error,) = wiring.version_findings()
    assert (error.relation, error.severity) == (cx.Relation.FILLER_VERSION, pv.Severity.ERROR)
    assert "targets version 1, but 'docs-a' defines the point at version 2" in error.message
    point = _point(repo)
    assert not point.resolved and point.why == "no filler answered"
    assert _states(point) == {
        READERS_FILE: ("inert", "it targets version 1; the point is at version 2"),
        "docs-a": ("passed over", "not promoted: a declared filler is inert"),
    }
    assert _resolve(repo).findings == ()  # the version error is the one finding, not repeated


def test_an_incompatible_project_filler_leaves_what_remains_and_never_the_default(
    repo: AdopterRepo,
) -> None:
    _provider(repo, version=2, default={"value": ["guest"], "participation": "alone"})
    _contributor(repo, "evidence", ["developer"], version=2)
    _filler(repo, {"schema_version": 1, "value": ["operator"]})
    point = _point(repo)
    assert point.resolved and point.value == ["developer"]
    assert _states(point)[READERS_FILE][0] == "inert"
    assert _states(point)["docs-a"] == ("passed over", "not promoted: a declared filler is inert")


def test_a_filler_whose_point_no_active_provider_defines_is_inert_and_unread(
    repo: AdopterRepo,
) -> None:
    _filler(repo, {"schema_version": 1, "value": {"not": "checked"}})
    resolution = _resolve(repo)
    (report,) = resolution.findings
    assert (report.location, report.severity) == (READERS_FILE, validators.Severity.REPORT)
    assert "role 'pkit::documentation' has no active provider" in report.message
    assert "its value is not read" in report.message
    assert resolution.points == ()


def test_a_stray_file_under_the_prefix_is_warned(repo: AdopterRepo) -> None:
    repo.write({f"{FILLERS}/pkit/readers.yaml": "schema_version: 1\nvalue: []\n"})
    (warning,) = _resolve(repo).findings
    assert (warning.location, warning.severity) == (f"{FILLERS}/pkit/readers.yaml", W)
    assert "not a project filler" in warning.message


def test_a_project_value_the_point_schema_refuses_is_an_error(repo: AdopterRepo) -> None:
    _provider(repo)
    _filler(repo, {"schema_version": 1, "value": ["ok", {"id": 5}]})
    resolution = _resolve(repo)
    assert _findings(resolution) == [(f"{READERS_FILE}:/value/1", "error")]
    point = resolution.point(READERS)
    assert point is not None and not point.resolved


def test_removals_on_a_single_point_are_an_error(repo: AdopterRepo) -> None:
    _provider(repo, TOOL, combination="single")
    _filler(
        repo,
        {"schema_version": 1, "value": {"name": "a"}, "remove": [{"id": "x", "reason": "r"}]},
        path=TOOL_FILE,
    )
    resolution = _resolve(repo)
    assert _findings(resolution) == [(f"{TOOL_FILE}:/remove", "error")]
    assert "a `single` point takes no removal overrides" in resolution.findings[0].message


# --- `single` ---------------------------------------------------------------------


def test_single_precedence_project_then_contribution_then_default(repo: AdopterRepo) -> None:
    _provider(repo, TOOL, combination="single", default={"value": {"name": "d"}, "participation": "always"})
    point = _point(repo, TOOL)
    assert (point.value, point.origin) == ({"name": "d"}, dp.DEFAULT)

    _contributor(repo, "evidence", {"name": "e"}, address=TOOL)
    point = _point(repo, TOOL)
    assert (point.value, point.origin) == ({"name": "e"}, "evidence")
    assert _states(point)["docs-a"] == ("passed over", "'evidence' answers first")

    _filler(repo, {"schema_version": 1, "value": {"name": "p"}}, path=TOOL_FILE)
    point = _point(repo, TOOL)
    assert (point.value, point.origin) == ({"name": "p"}, dp.PROJECT)
    assert _states(point)["evidence"] == ("passed over", "the project filler answers first")


def test_an_alone_default_answers_only_when_nothing_is_declared(repo: AdopterRepo) -> None:
    _provider(repo, TOOL, combination="single", default={"value": {"name": "d"}, "participation": "alone"})
    assert _point(repo, TOOL).value == {"name": "d"}
    _contributor(repo, "evidence", {"name": "e"}, address=TOOL)
    point = _point(repo, TOOL)
    assert point.value == {"name": "e"}
    assert _states(point)["docs-a"] == ("passed over", "another filler is declared")


def test_single_without_a_declared_policy_is_single(repo: AdopterRepo) -> None:
    """No `combination`: `single`, so two contributors need a selection (COR-052 point 3)."""
    _provider(repo, TOOL, combination=None)
    _contributor(repo, "evidence", {"name": "e"}, address=TOOL)
    _contributor(repo, "notes", {"name": "n"}, address=TOOL)
    wiring = cx.resolve_wiring(repo.root)
    assert [f.path for f in wiring.errors()] == ["/connections/selections"]
    point = _point(repo, TOOL)
    assert (point.policy, point.resolved) == ("single", False)
    assert point.why == "several capabilities contribute and none is selected"


def test_single_with_a_selection_takes_the_selected_contributor(repo: AdopterRepo) -> None:
    _provider(repo, TOOL, combination="single", default={"value": {"name": "d"}, "participation": "always"})
    _contributor(repo, "evidence", {"name": "e"}, address=TOOL)
    _contributor(repo, "notes", {"name": "n"}, address=TOOL)
    _config(repo, f"connections:\n  selections:\n    {TOOL}: notes\n")
    point = _point(repo, TOOL)
    assert (point.value, point.origin) == ({"name": "n"}, "notes")
    assert _states(point)["evidence"] == (
        "passed over",
        "not selected: the contributor selection names 'notes'",
    )
    assert _resolve(repo).findings == ()


def test_single_ambiguous_is_unresolved_and_the_default_does_not_stand_in(
    repo: AdopterRepo,
) -> None:
    _provider(repo, TOOL, combination="single", default={"value": {"name": "d"}, "participation": "always"})
    _contributor(repo, "evidence", {"name": "e"}, address=TOOL)
    _contributor(repo, "notes", {"name": "n"}, address=TOOL)
    point = _point(repo, TOOL)
    assert not point.resolved
    assert {state for state, _reason in _states(point).values()} == {"passed over"}

    # The project filler precedes every contribution: it answers, ambiguity or not.
    _filler(repo, {"schema_version": 1, "value": {"name": "p"}}, path=TOOL_FILE)
    point = _point(repo, TOOL)
    assert (point.resolved, point.origin) == (True, dp.PROJECT)


def test_single_with_nothing_declared_and_no_default_is_unfilled(repo: AdopterRepo) -> None:
    _provider(repo, TOOL, combination="single")
    point = _point(repo, TOOL)
    assert not point.resolved and point.why.startswith("unfilled")
    assert _resolve(repo).findings == ()


# --- `union` ------------------------------------------------------------------------


def test_union_merges_by_id_the_project_overriding_whole_entries(repo: AdopterRepo) -> None:
    _provider(repo, default={"value": ["guest", {"id": "operator", "role": "d"}], "participation": "always"})
    _contributor(repo, "evidence", [{"id": "operator", "role": "e"}, "developer"])
    _filler(repo, {"schema_version": 1, "value": [{"id": "developer"}]})
    point = _point(repo)
    assert point.resolved
    assert point.value == [{"id": "developer"}, "guest", {"id": "operator", "role": "e"}]
    assert [(e.id, e.origin, e.replaces) for e in point.entries] == [
        ("developer", dp.PROJECT, ("evidence",)),
        ("guest", dp.DEFAULT, ()),
        ("operator", "evidence", (dp.DEFAULT,)),
    ]


def test_union_two_capabilities_with_one_id_is_an_error_the_project_settles(
    repo: AdopterRepo,
) -> None:
    _provider(repo)
    _contributor(repo, "evidence", [{"id": "operator", "role": "e"}])
    _contributor(repo, "notes", [{"id": "operator", "role": "n"}])
    resolution = _resolve(repo)
    assert _findings(resolution) == [(READERS_FILE, "error")]
    assert "'evidence' and 'notes' both supply entry 'operator'" in resolution.findings[0].message
    point = resolution.point(READERS)
    assert point is not None and not point.resolved and "entries collide" in point.why

    _filler(repo, {"schema_version": 1, "value": [{"id": "operator", "role": "p"}]})
    point = _point(repo)
    assert point.resolved and point.value == [{"id": "operator", "role": "p"}]
    assert point.entries[0].replaces == ("evidence", "notes")


def test_union_suppression_with_a_reason_drops_the_entry(repo: AdopterRepo) -> None:
    _provider(repo)
    _contributor(repo, "evidence", ["operator", "guest"])
    _filler(
        repo,
        {"schema_version": 1, "value": [], "remove": [{"id": "guest", "reason": "No anonymous readers."}]},
    )
    point = _point(repo)
    assert point.value == ["operator"]
    assert point.removals == (dp.Removal("guest", "No anonymous readers.", ("evidence",)),)


def test_a_removal_that_matches_nothing_is_information(repo: AdopterRepo) -> None:
    _provider(repo)
    _filler(repo, {"schema_version": 1, "value": [], "remove": [{"id": "ghost", "reason": "r"}]})
    (info,) = _resolve(repo).findings
    assert (info.location, info.severity) == (f"{READERS_FILE}:/remove/0", validators.Severity.INFO)


# --- `additive` -----------------------------------------------------------------------


def test_additive_keeps_every_entry_in_precedence_order(repo: AdopterRepo) -> None:
    _provider(repo, combination="additive", default={"value": ["d1"], "participation": "always"})
    _contributor(repo, "notes", ["n1"])
    _contributor(repo, "evidence", ["e1", "e2"])
    _filler(repo, {"schema_version": 1, "value": ["p1"]})
    point = _point(repo)
    assert point.value == ["p1", "e1", "e2", "n1", "d1"]
    assert [e.origin for e in point.entries] == [dp.PROJECT, "evidence", "evidence", "notes", dp.DEFAULT]


def test_additive_collision_with_the_project_is_an_error_until_a_removal_override(
    repo: AdopterRepo,
) -> None:
    _provider(repo, combination="additive")
    _contributor(repo, "evidence", ["security-review", "e2"])
    _filler(repo, {"schema_version": 1, "value": ["p1", "security-review"]})
    resolution = _resolve(repo)
    assert _findings(resolution) == [(f"{READERS_FILE}:/value/1", "error")]
    assert "collides with the one 'evidence' supplies" in resolution.findings[0].message
    point = resolution.point(READERS)
    assert point is not None and not point.resolved

    _filler(
        repo,
        {
            "schema_version": 1,
            "value": ["p1", "security-review"],
            "remove": [{"id": "security-review", "reason": "Ours replaces theirs."}],
        },
    )
    point = _point(repo)
    assert point.resolved and point.value == ["p1", "security-review", "e2"]
    assert point.removals[0].removed_from == ("evidence",)


def test_additive_collision_between_capabilities_is_an_error(repo: AdopterRepo) -> None:
    _provider(repo, combination="additive")
    _contributor(repo, "evidence", ["x"])
    _contributor(repo, "notes", ["x"])
    resolution = _resolve(repo)
    assert _findings(resolution) == [(READERS_FILE, "error")]
    assert "'evidence' and 'notes' both supply entry 'x' to additive point" in (
        resolution.findings[0].message
    )


# --- the inert policy -------------------------------------------------------------------


def test_fallback_resolves_from_what_remains_with_a_warning(repo: AdopterRepo) -> None:
    _provider(repo, inert="fallback")
    _contributor(repo, "evidence", ["operator"])
    _contributor(repo, "notes", [{"id": 7}])
    resolution = _resolve(repo)
    assert _findings(resolution) == [
        (".pkit/capabilities/notes/package.yaml:/connections/extensions/contributes/0", "warning")
    ]
    message = resolution.findings[0].message
    assert "the contribution of 'notes' to 'pkit::documentation:readers' is inert" in message
    assert "the point resolves from the remaining fillers" in message
    point = resolution.point(READERS)
    assert point is not None and point.value == ["operator"]


def test_fail_leaves_the_whole_point_unresolved_with_an_error(repo: AdopterRepo) -> None:
    _provider(repo, inert="fail")
    _contributor(repo, "evidence", ["operator"])
    _contributor(repo, "notes", [{"id": 7}])
    resolution = _resolve(repo)
    assert [f.severity for f in resolution.findings] == [E]
    assert "inert policy is `fail`, so it is unresolved" in resolution.findings[0].message
    point = resolution.point(READERS)
    assert point is not None and not point.resolved and point.value is None
    # Asked and answered, but no partial value is ever taken.
    assert _states(point)["evidence"] == ("passed over", "answered, but the point does not resolve")


def test_an_out_of_step_contribution_is_inert_and_under_fail_unresolves(
    repo: AdopterRepo,
) -> None:
    _provider(repo, inert="fail")
    _contributor(repo, "evidence", ["operator"])
    _contributor(repo, "notes", ["x"], version=2)
    point = _point(repo)
    assert not point.resolved
    assert _states(point)["notes"] == ("inert", "it targets version 2; the point is at version 1")


def test_a_contribution_naming_command_and_value_is_a_package_error(repo: AdopterRepo) -> None:
    _stage(
        repo,
        "evidence",
        {"extensions": {"contributes": [{"point": READERS, "schema_version": 1, "command": "noop", "value": []}]}},
    )
    report = pv.validate_installed_packages(repo.root)
    errors = {f.path: f.message for r in report.reports for f in r.errors}
    assert errors["/connections/extensions/contributes/0/value"] == (
        "a contribution supplies its data through `command` or `value`, not both (COR-052 point 2)."
    )


# --- `pkit validate` ----------------------------------------------------------------------


def test_the_connections_member_reports_the_data_points_and_fails_on_their_errors(
    repo: AdopterRepo,
) -> None:
    _provider(repo)
    _filler(repo, {"schema_version": 1, "value": [5]})
    result = CliRunner().invoke(main, ["validate", "--only", "connections"])
    assert result.exit_code == 1, result.output
    assert "1 data point(s): 0 resolved, 1 unresolved; 1 project filler file(s)." in result.output
    assert f"error    {READERS_FILE}:/value/0" in result.output


def test_validate_resolves_the_wiring_and_the_data_points_once(
    repo: AdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    _provider(repo)
    _contributor(repo, "evidence", ["operator"])
    calls: list[str] = []
    wiring, data = cx.resolve_wiring, dp.resolve_data_points

    def counting_wiring(root: Path) -> cx.Wiring:
        calls.append("wiring")
        return wiring(root)

    def counting_data(root: Path) -> dp.DataResolution:
        calls.append("data")
        return data(root)

    monkeypatch.setattr(cx, "resolve_wiring", counting_wiring)
    monkeypatch.setattr(dp, "resolve_data_points", counting_data)
    result = CliRunner().invoke(main, ["validate", "--no-refs"])
    assert sorted(calls) == ["data", "wiring"], result.output


# --- command fillers (COR-052 point 6; the query policy) ------------------------------

ANSWER = {"schema_version": 1, "value": ["developer"]}


def _log(repo: AdopterRepo) -> Path:
    """Where the synthetic filler commands record each run (git never lists `.git/`)."""
    return repo.root / ".git" / "filler-runs.log"


def _command_contributor(
    repo: AdopterRepo,
    name: str,
    body: str,
    *,
    contract: bool = True,
    address: str = READERS,
) -> None:
    """A capability contributing through the command `export`, whose script records
    its arguments and the offline marker in the run log, then runs `body`."""
    leaf: dict[str, Any] = {"script": "scripts/export.py", "help": "Export the readers."}
    if contract:
        leaf["query-contract"] = True
    entry = {"point": address, "schema_version": 1, "command": "export"}
    _stage(
        repo,
        name,
        {"extensions": {"contributes": [entry]}},
        commands={"noop": {"script": "scripts/noop.py", "help": "Nothing."}, "export": leaf},
    )
    script = repo.pkit / "capabilities" / name / "scripts" / "export.py"
    script.write_text(
        "#!/usr/bin/env python3\n"
        "import json, os, sys, time\n"
        f"with open({str(_log(repo))!r}, 'a') as log:\n"
        "    log.write(json.dumps([sys.argv[1:], os.environ.get('PKIT_OFFLINE'),"
        " os.environ.get('UV_OFFLINE')]) + '\\n')\n" + body,
        encoding="utf-8",
    )
    script.chmod(0o755)


def _runs(repo: AdopterRepo) -> list[Any]:
    log = _log(repo)
    return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []


def _printing(document: Any) -> str:
    return f"print(json.dumps({document!r}))\n"


def test_a_command_filler_answers_with_json_alone_offline_marked(repo: AdopterRepo) -> None:
    _provider(repo)
    _command_contributor(repo, "evidence", _printing(ANSWER))
    point = _point(repo)
    assert point.resolved and point.value == ["developer"]
    (filler,) = point.fillers
    assert (filler.supplies, filler.state, filler.query_contract) == (
        "command 'export'",
        dp.FillerState.TAKEN,
        True,
    )
    # No parameter: `--json` alone; the offline marker set (ADR-057 point 3).
    assert _runs(repo) == [[["--json"], "1", "1"]]


@pytest.mark.parametrize(
    ("body", "reason"),
    [
        ("time.sleep(60)\n", "command 'export' did not answer within 1 s"),
        (
            "print('not json')\n",
            "command 'export' did not print a JSON document on its standard output",
        ),
        ("sys.exit(3)\n", "command 'export' exited 3"),
        (
            _printing({"value": ["x"]}),
            "printed no filler envelope: 'schema_version' is a required property",
        ),
        (
            _printing({"schema_version": 2, "value": ["x"]}),
            "answered for version 2; the point is at version 1",
        ),
        (
            _printing({"schema_version": 1, "value": ["x"], "remove": [{"id": "a", "reason": "r"}]}),
            "answered with `remove`: removal overrides are the project's alone",
        ),
        (
            _printing({"schema_version": 1, "value": ["ok", {"id": 5}]}),
            "its value does not fit the point at /1",
        ),
    ],
    ids=["timeout", "no-document", "abnormal-exit", "no-envelope", "other-version", "removals", "partial"],
)
def test_a_command_filler_without_an_answer_is_inert_never_a_partial_value(
    repo: AdopterRepo, monkeypatch: pytest.MonkeyPatch, body: str, reason: str
) -> None:
    monkeypatch.setattr(command_runner, "COMMAND_TIMEOUT_SECONDS", 1)
    _provider(repo, inert="fallback", default={"value": ["guest"], "participation": "alone"})
    _command_contributor(repo, "evidence", body)
    resolution = _resolve(repo)
    point = resolution.point(READERS)
    assert point is not None and not point.resolved and point.value is None
    state, why = _states(point)["evidence"]
    assert state == "inert" and reason in why, why
    # The broken filler does not promote the `alone` default.
    assert _states(point)["docs-a"] == ("passed over", "not promoted: a declared filler is inert")
    (warning,) = resolution.findings
    assert warning.severity is W
    assert warning.location == (
        ".pkit/capabilities/evidence/package.yaml:/connections/extensions/contributes/0"
    )
    assert "no filler remains, so the point is unresolved" in warning.message


def test_a_failing_command_filler_under_fail_is_an_error(repo: AdopterRepo) -> None:
    _provider(repo, inert="fail")
    _contributor(repo, "notes", ["operator"])
    _command_contributor(repo, "evidence", "sys.exit(1)\n")
    resolution = _resolve(repo)
    (error,) = resolution.findings
    assert error.severity is E and "inert policy is `fail`, so it is unresolved" in error.message
    point = resolution.point(READERS)
    assert point is not None and not point.resolved and point.value is None


def test_a_command_without_the_declaration_is_never_run_and_is_reported(
    repo: AdopterRepo,
) -> None:
    _provider(repo)
    _command_contributor(repo, "evidence", _printing(ANSWER), contract=False)
    point = _point(repo)
    assert not point.resolved
    (filler,) = point.fillers
    assert filler.query_contract is False
    assert filler.reason.startswith("its command 'export' does not declare the query contract")
    assert _runs(repo) == []  # the runner's backstop: never started
    # The packages member reports it where the author can fix it (the reporting rule).
    report = pv.validate_installed_packages(repo.root)
    (error,) = [f for r in report.reports for f in r.errors]
    assert error.path == "/connections/extensions/contributes/0/command"
    assert "names command 'export' as its filler, which does not declare the query contract" in (
        error.message
    )


def test_a_single_point_runs_no_command_once_a_filler_before_it_answers(
    repo: AdopterRepo,
) -> None:
    _provider(repo, TOOL, combination="single")
    tool = {"schema_version": 1, "value": {"name": "e"}}
    _command_contributor(repo, "evidence", _printing(tool), address=TOOL)
    _filler(repo, {"schema_version": 1, "value": {"name": "p"}}, path=TOOL_FILE)
    assert _point(repo, TOOL).origin == dp.PROJECT
    assert _runs(repo) == []


def test_validate_runs_each_command_filler_once(repo: AdopterRepo) -> None:
    _provider(repo)
    _command_contributor(repo, "evidence", _printing(ANSWER))
    result = CliRunner().invoke(main, ["validate", "--no-refs"])
    assert result.exit_code == 0, result.output
    assert len(_runs(repo)) == 1


# --- the status report (COR-052 point 7) ------------------------------------------------


def _data_points_section(output: str) -> str:
    return output.split("\n  Data points\n")[1].split("\n\n")[0]


def test_status_shows_how_each_point_resolved_and_why(repo: AdopterRepo) -> None:
    _provider(repo, default={"value": ["visitor", "guest"], "participation": "always"})
    _contributor(repo, "evidence", ["operator", "guest"])
    _command_contributor(repo, "notes", _printing({"schema_version": 1, "value": ["maintainer"]}))
    _filler(
        repo,
        {
            "schema_version": 1,
            "value": ["developer"],
            "remove": [{"id": "guest", "reason": "No anonymous readers."}],
        },
    )
    result = CliRunner().invoke(main, ["status"])
    assert result.exit_code == 0, result.output
    indent = " " * 25
    assert _data_points_section(result.output).splitlines() == [
        f"    fillers            {FILLERS}/   (1 file(s))",
        "    points             1 defined: 1 resolved, 0 unresolved",
        f"    {READERS}",
        f"{indent}union · inert fallback · default always — resolved",
        f"{indent}entry    developer — project filler",
        f"{indent}entry    maintainer — notes",
        f"{indent}entry    operator — evidence",
        f"{indent}entry    visitor — the default",
        f"{indent}removed  guest — No anonymous readers. (from evidence, the default)",
        f"{indent}filler   project filler {READERS_FILE}: taken",
        f"{indent}filler   evidence (value): taken",
        f"{indent}filler   notes (command 'export'; query contract declared: no network, "
        "trusted, not enforced): taken",
        f"{indent}filler   default of docs-a (always): taken",
    ]


def test_status_shows_an_unresolved_point_and_a_command_that_is_not_run(
    repo: AdopterRepo,
) -> None:
    default = {"value": {"name": "d"}, "participation": "alone"}
    _provider(repo, TOOL, combination="single", inert="fail", default=default)
    answer = _printing({"schema_version": 1, "value": {"name": "e"}})
    _command_contributor(repo, "evidence", answer, contract=False, address=TOOL)
    result = CliRunner().invoke(main, ["status"])
    assert result.exit_code == 0, result.output
    indent = " " * 25
    lines = _data_points_section(result.output).splitlines()
    assert lines[2:] == [
        f"    {TOOL}",
        f"{indent}single · inert fail · default alone — unresolved: a filler meant to answer is "
        "inert, and the point's inert policy is `fail`",
        f"{indent}filler   evidence (command 'export'; no query-contract declaration): inert — "
        "its command 'export' does not declare the query contract (`query-contract: true`), "
        "so it is not run",
        f"{indent}filler   default of docs-a (alone): passed over — not promoted: a declared "
        "filler is inert",
    ]


def test_status_resolves_the_wiring_once_outside_a_validate_run(
    repo: AdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The resolution is one run of its own when `pkit validate` is not running:
    the wiring its point schemas are read from is the wiring it resolves over."""
    _provider(repo)
    _contributor(repo, "evidence", ["operator"])
    calls: list[Path] = []
    wiring = cx.resolve_wiring

    def counting(root: Path) -> cx.Wiring:
        calls.append(root)
        return wiring(root)

    monkeypatch.setattr(cx, "resolve_wiring", counting)
    result = CliRunner().invoke(main, ["status"])
    assert result.exit_code == 0, result.output
    assert len(calls) == 1


def test_status_on_a_fresh_install_defines_no_point(repo: AdopterRepo) -> None:
    result = CliRunner().invoke(main, ["status"])
    assert _data_points_section(result.output).splitlines() == [
        f"    fillers            {FILLERS}/   (0 file(s))",
        "    points             none defined",
    ]


# --- `pkit connections resolve`: the read a capability's script consumes ----------------


def _resolve_cli(*args: str) -> Any:
    return CliRunner().invoke(main, ["connections", "resolve", *args])


def test_resolve_prints_the_point_as_the_status_report_resolves_it(repo: AdopterRepo) -> None:
    _provider(repo, combination="additive", default={"value": ["d1"], "participation": "always"})
    _command_contributor(repo, "notes", _printing({"schema_version": 1, "value": ["n1"]}))
    _filler(
        repo,
        {
            "schema_version": 1,
            "value": [{"id": "p1", "role": "owner"}],
            "remove": [{"id": "d1", "reason": "Not ours."}],
        },
    )
    result = _resolve_cli(READERS, "--json")
    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == {
        "address": READERS,
        "defined": True,
        "provider": "docs-a",
        "policy": "additive",
        "inert_policy": "fallback",
        "participation": "always",
        "resolved": True,
        "why": "",
        "value": [{"id": "p1", "role": "owner"}, "n1"],
        "origin": "",
        "entries": [
            {"id": "p1", "origin": dp.PROJECT, "replaces": [], "value": {"id": "p1", "role": "owner"}},
            {"id": "n1", "origin": "notes", "replaces": [], "value": "n1"},
        ],
        "removals": [{"id": "d1", "reason": "Not ours.", "removed_from": [dp.DEFAULT]}],
        "fillers": [
            {
                "source": "project filler",
                "name": READERS_FILE,
                "supplies": "file",
                "state": "taken",
                "reason": "",
                "query_contract": None,
            },
            {
                "source": "contribution",
                "name": "notes",
                "supplies": "command 'export'",
                "state": "taken",
                "reason": "",
                "query_contract": True,
            },
            {
                "source": "default",
                "name": "docs-a",
                "supplies": "always",
                "state": "taken",
                "reason": "",
                "query_contract": None,
            },
        ],
    }
    # The filler command ran as it does under `pkit validate`: `--json` alone, offline.
    assert _runs(repo) == [[["--json"], "1", "1"]]
    # Without --json, exactly the status report's lines for the point.
    human = _resolve_cli(READERS)
    assert human.exit_code == 0
    status = CliRunner().invoke(main, ["status"]).output
    assert human.output.splitlines() == _data_points_section(status).splitlines()[2:]


def test_resolve_an_unresolved_point_exits_1_with_no_value(repo: AdopterRepo) -> None:
    _provider(repo, inert="fail")
    _contributor(repo, "evidence", ["operator"])
    _contributor(repo, "notes", [{"id": 7}])
    result = _resolve_cli(READERS, "--json")
    assert result.exit_code == 1
    document = json.loads(result.output)
    assert (document["resolved"], document["value"], document["entries"]) == (False, None, [])
    assert document["why"] == "a filler meant to answer is inert, and the point's inert policy is `fail`"
    states = {f["name"]: (f["state"], f["reason"]) for f in document["fillers"]}
    assert states["notes"][0] == "inert"
    assert states["evidence"] == ("passed over", "answered, but the point does not resolve")


def test_resolve_an_address_nothing_defines_exits_1_and_says_why(repo: AdopterRepo) -> None:
    result = _resolve_cli(READERS, "--json")
    assert result.exit_code == 1
    assert json.loads(result.output) == {
        "address": READERS,
        "defined": False,
        "resolved": False,
        "value": None,
        "why": "role 'pkit::documentation' has no active provider",
    }
    _provider(repo)
    human = _resolve_cli(TOOL)
    assert human.exit_code == 1
    assert human.output == (
        f"{TOOL}: not defined — 'docs-a', the active provider of role "
        f"'pkit::documentation', defines no data point '{TOOL}'\n"
    )


def test_resolve_refuses_what_is_not_a_point_address(repo: AdopterRepo) -> None:
    result = _resolve_cli("pkit::documentation")
    assert result.exit_code == 2
    assert "is not a point address" in result.output


# --- resolving one point asks only its fillers (#1103) ----------------------------------


def _two_points_each_filled_by_a_command(repo: AdopterRepo) -> None:
    """READERS and TOOL, defined by one provider; `notes` fills READERS and
    `evidence` fills TOOL, each through its command `export`."""
    accepts = {
        READERS: {
            "schema_version": 1,
            "schema": "readers.schema.json",
            "description": "Who reads the documentation.",
            "combination": "union",
        },
        TOOL: {
            "schema_version": 1,
            "schema": "tool.schema.json",
            "description": "The tool that renders it.",
            "combination": "single",
        },
    }
    _stage(repo, "docs-a", {"roles": [DOCS], "extension-points": {"accepts": accepts}})
    _command_contributor(repo, "notes", _printing(ANSWER))
    tool = {"schema_version": 1, "value": {"name": "e"}}
    _command_contributor(repo, "evidence", _printing(tool), address=TOOL)


@pytest.fixture
def started(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """The capabilities whose command filler the data points start, in order."""
    names: list[str] = []
    real = dp.run_command

    def counting(script: Path, *args: Any, **kwargs: Any) -> Any:
        names.append(Path(script).parts[-3])  # .pkit/capabilities/<name>/scripts/<script>
        return real(script, *args, **kwargs)

    monkeypatch.setattr(dp, "run_command", counting)
    return names


def test_resolve_starts_only_the_command_fillers_of_the_point_asked_for(
    repo: AdopterRepo, started: list[str]
) -> None:
    _two_points_each_filled_by_a_command(repo)
    readers = _resolve_cli(READERS, "--json")
    assert readers.exit_code == 0, readers.output
    assert json.loads(readers.output)["value"] == ["developer"]
    assert started == ["notes"]
    started.clear()
    tool = _resolve_cli(TOOL, "--json")
    assert tool.exit_code == 0, tool.output
    assert json.loads(tool.output)["value"] == {"name": "e"}
    assert started == ["evidence"]


def test_validate_and_status_still_resolve_every_point_once(
    repo: AdopterRepo, started: list[str]
) -> None:
    _two_points_each_filled_by_a_command(repo)
    result = CliRunner().invoke(main, ["validate", "--no-refs"])
    assert result.exit_code == 0, result.output
    assert sorted(started) == ["evidence", "notes"]
    started.clear()
    status = CliRunner().invoke(main, ["--color", "never", "status"])
    assert status.exit_code == 0, status.output
    assert sorted(started) == ["evidence", "notes"]


def test_a_point_resolved_first_is_shared_by_the_whole_resolution_of_the_run(
    repo: AdopterRepo, started: list[str]
) -> None:
    """Within one run, the point asked for first is not resolved again, and the
    whole resolution is the one a fresh run gives — findings in the same order."""
    _two_points_each_filled_by_a_command(repo)
    _filler(repo, "value: [not an envelope\n")  # a filler-file finding, before any point's

    def one_then_all() -> tuple[dp.ResolvedPoint | None, dp.DataResolution]:
        point, _why = dp.resolve_point(repo.root, TOOL)
        return point, dp.shared_resolution(repo.root)

    point, whole = validators.as_one_run(one_then_all)
    assert started == ["evidence", "notes"]
    assert whole.point(TOOL) == point
    started.clear()
    assert whole == dp.resolve_data_points(repo.root)
    assert sorted(started) == ["evidence", "notes"]
