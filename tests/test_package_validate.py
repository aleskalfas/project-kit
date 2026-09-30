"""Tests for the package-metadata schema and validator (#982, strict since #999):
every shipped `package.yaml` validates clean, an unknown key at any level is an
error with a suggestion (a warning only under a tree's older, open schema), the
fields COR-017 lists are required of every component, addresses are words,
known keys are type-checked, the repository checks refuse what the Task lists,
the install-time self-consistency check still refuses what it refused before,
and `pkit validate` runs the "packages" pass."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from project_kit import backbone_schemas as bs
from project_kit import capabilities as caps
from project_kit import package_validate as pv
from project_kit import lifecycle_ownership, process_journal, refs, scaffolds
from project_kit.cli import main
from project_kit.manifest import (
    ORIGIN_EXTERNALLY_SOURCED,
    ORIGIN_INCUBATED_IN_REPO,
    ORIGIN_KIT_SHIPPED,
    set_capability_origin,
)
from tests.adopter_repo import MakeAdopterRepo
from tests.process_journal_support import set_journal_logging

REPO = Path(__file__).resolve().parents[1]

# Every kit-shipped capability, dependencies before dependents.
SHIPPED_CAPABILITIES = (
    "evidence",
    "demo-recording",
    "living-docs",
    "software-analysis",
    "project-management",
    "software-engineering",
)


@pytest.fixture(scope="module")
def schema() -> dict[str, Any]:
    return bs.load_backbone_schema(REPO, pv.SCHEMA_KIND)


@pytest.fixture
def component_dir(tmp_path: Path) -> Path:
    """A component root with one script and one companion schema in place."""
    root = tmp_path / "demo"
    (root / "scripts").mkdir(parents=True)
    (root / "scripts" / "publish.py").write_text("", encoding="utf-8")
    (root / "scripts" / "create-page.py").write_text("", encoding="utf-8")
    (root / "schemas").mkdir()
    (root / "schemas" / "reading-evidence.schema.json").write_text("{}", encoding="utf-8")
    return root


def _package(**overrides: Any) -> dict[str, Any]:
    """A minimal valid capability package, with top-level keys overridden."""
    raw: dict[str, Any] = {
        "schema_version": 1,
        "component": {"kind": "capability", "name": "demo", "version": "0.1.0"},
        "description": "A demo.",
        "requires_backbone": ">=1.0.0,<2.0.0",
        "commands": {
            "publish": {"script": "scripts/publish.py", "help": "Publish."},
            "create": {"page": {"script": "scripts/create-page.py", "help": "Create a page."}},
        },
    }
    raw.update(overrides)
    return raw


def _connections(**overrides: Any) -> dict[str, Any]:
    block: dict[str, Any] = {
        "roles": ["pkit::documentation"],
        "extension-points": {
            "accepts": {
                "pkit::documentation:reading-evidence": {
                    "schema_version": 1,
                    "schema": "reading-evidence.schema.json",
                    "description": "What readers found.",
                }
            }
        },
    }
    block.update(overrides)
    return block


def _messages(findings: list[pv.PackageFinding], severity: pv.Severity) -> dict[str, str]:
    return {f.path: f.message for f in findings if f.severity is severity}


def _validate(
    raw: dict[str, Any], schema: dict[str, Any] | None, component_dir: Path
) -> list[pv.PackageFinding]:
    return pv.validate_package(raw, schema, component_dir=component_dir, expected_name="demo")


# --- the regression guard: everything shipped is clean ---------------------


@pytest.mark.parametrize(
    "package",
    sorted(REPO.glob(".pkit/capabilities/*/package.yaml"))
    + sorted(REPO.glob(".pkit/adapters/*/package.yaml")),
    ids=lambda p: p.parent.name,
)
def test_every_shipped_package_file_validates_with_no_findings(
    schema: dict[str, Any], package: Path
) -> None:
    report = pv.validate_package_file(package, schema, expected_name=package.parent.name)
    assert report.findings == (), [f"{f.severity.value} {f.path}: {f.message}" for f in report.findings]


def test_scaffold_templates_validate_with_no_findings(
    schema: dict[str, Any], tmp_path: Path
) -> None:
    """What `pkit new capability` / `pkit new adapter` stamp is clean from the start."""
    from ruamel.yaml import YAML

    for template, kind in (
        (scaffolds._CAPABILITY_PACKAGE_YAML_TEMPLATE, "capability"),  # pyright: ignore[reportPrivateUsage]
        (scaffolds._PACKAGE_YAML_TEMPLATE, "adapter"),  # pyright: ignore[reportPrivateUsage]
    ):
        text = template.format(kind=kind, name="demo", requires_backbone=">=1.0.0,<2.0.0")
        raw = YAML(typ="safe").load(text)
        assert _validate(raw, schema, tmp_path) == []


def test_installed_packages_validate_clean_in_an_adopter_repo(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    adopter = make_adopter_repo(capabilities=SHIPPED_CAPABILITIES)
    result = pv.validate_installed_packages(adopter.root)
    assert result.schema_note is None
    checked = {report.file.parent.name for report in result.reports}
    assert set(SHIPPED_CAPABILITIES) <= checked
    assert "claude-code" in checked
    assert result.errors == 0 and result.warnings == 0, [
        (str(r.file), f.path, f.message) for r in result.reports for f in r.findings
    ]


# --- unknown keys are errors; known keys are typed ---------------------------


def _opened(schema: Any) -> Any:
    """The schema as a tree synced before the strict flip carries it: every closed
    object left open, so unknown keys are the walker's warnings."""
    if isinstance(schema, dict):
        return {
            key: True if key == "additionalProperties" and value is False else _opened(value)
            for key, value in schema.items()
        }
    if isinstance(schema, list):
        return [_opened(item) for item in schema]
    return schema


def _closed_objects(node: Any, pointer: str = "") -> list[tuple[str, Any]]:
    """`(schema pointer, additionalProperties)` for every schema object that declares
    `properties` — each place a key could be unknown. An `if` is a condition that
    only reads a key, never the shape of the object, so it is not walked."""
    found: list[tuple[str, Any]] = []
    if isinstance(node, dict):
        if isinstance(node.get("properties"), dict):
            found.append((pointer, node.get("additionalProperties", True)))
        for key, value in node.items():
            if key != "if":
                found.extend(_closed_objects(value, f"{pointer}/{key}"))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            found.extend(_closed_objects(value, f"{pointer}/{index}"))
    return found


def test_the_schema_closes_every_object_it_declares(schema: dict[str, Any]) -> None:
    """Strict at every level: no declared object leaves room for an unknown key."""
    declared = _closed_objects(schema)
    assert len(declared) >= 20
    assert [pointer for pointer, additional in declared if additional is not False] == []


def test_an_unknown_key_is_an_error_with_the_nearest_known_key_at_every_level(
    schema: dict[str, Any], component_dir: Path
) -> None:
    commands = _package()["commands"]
    commands["publish"]["hlep"] = "typo"
    connections = _connections(
        extensions={
            "contributes": [
                {
                    "point": "pkit::analysis:glossary",
                    "schema_version": 1,
                    "value": [],
                    "mandatroy": {"reason": "r"},
                }
            ],
            "subscribes": [
                {"point": "pkit::analysis:created", "schema_version": 1, "command": "publish"}
            ],
            "depends-on": {"generated": True, "entries": [], "generatd": True},
        },
        rolse=["pkit::documentation"],
    )
    point = connections["extension-points"]["accepts"]["pkit::documentation:reading-evidence"]
    point["descripton"] = "x"
    point["default"] = {"value": [], "participation": "alone", "participaton": "always"}
    point["mandatory"] = {"reason": "r", "reasn": "r"}
    connections["extensions"]["subscribes"][0]["comand"] = "publish"
    raw = _package(
        foootprint=[".claude"],
        commands=commands,
        connections=connections,
        component={"kind": "capability", "name": "demo", "version": "0.1.0", "verison": "1"},
        requires_capabilities=[{"name": "evidence", "version": ">=0.1", "nmae": "evidence"}],
        validators={"cites": {"command": "publish", "ordr": 5}},
        docs={"locations": {"pages": {"path": "pages", "roots": "user"}}, "location": {}},
        friction={"places": [{"path": "**/*.md", "locaton": "pages"}], "surfaces": []},
    )
    findings = _validate(raw, schema, component_dir)
    unknown = {
        path: message
        for path, message in _messages(findings, pv.Severity.ERROR).items()
        if message.startswith("unknown key")
    }
    accepts = "/connections/extension-points/accepts/pkit::documentation:reading-evidence"
    assert unknown == {
        "/foootprint": "unknown key 'foootprint'; did you mean 'footprint'?",
        "/component/verison": "unknown key 'verison'; did you mean 'version'?",
        "/commands/publish/hlep": "unknown key 'hlep'; did you mean 'help'?",
        "/requires_capabilities/0/nmae": "unknown key 'nmae'; did you mean 'name'?",
        "/validators/cites/ordr": "unknown key 'ordr'; did you mean 'order'?",
        "/connections/rolse": "unknown key 'rolse'; did you mean 'roles'?",
        f"{accepts}/descripton": "unknown key 'descripton'; did you mean 'description'?",
        f"{accepts}/default/participaton": (
            "unknown key 'participaton'; did you mean 'participation'?"
        ),
        f"{accepts}/mandatory/reasn": "unknown key 'reasn'; did you mean 'reason'?",
        "/connections/extensions/contributes/0/mandatroy": (
            "unknown key 'mandatroy'; did you mean 'mandatory'?"
        ),
        "/connections/extensions/subscribes/0/comand": (
            "unknown key 'comand'; did you mean 'command'?"
        ),
        "/connections/extensions/depends-on/generatd": (
            "unknown key 'generatd'; did you mean 'generated'?"
        ),
        "/docs/location": "unknown key 'location'; did you mean 'locations'?",
        "/docs/locations/pages/roots": "unknown key 'roots'; did you mean 'root'?",
        "/friction/places/0/locaton": "unknown key 'locaton'; did you mean 'location'?",
        "/friction/surfaces": "unknown key 'surfaces'; did you mean 'surface'?",
    }
    assert _messages(findings, pv.Severity.WARNING) == {}


def test_an_unknown_key_makes_a_report_unclean(
    schema: dict[str, Any], component_dir: Path, tmp_path: Path
) -> None:
    package = tmp_path / "package.yaml"
    package.write_text(
        "schema_version: 1\ncomponent: {kind: capability, name: demo, version: 0.1.0}\n"
        "description: A demo.\nrequires_backbone: '>=1.0.0'\ndescriptoin: typo\n",
        encoding="utf-8",
    )
    report = pv.validate_package_file(package, schema, component_dir=component_dir)
    assert not report.is_clean
    assert [(f.path, f.severity, f.message) for f in report.findings] == [
        (
            "/descriptoin",
            pv.Severity.ERROR,
            "unknown key 'descriptoin'; did you mean 'description'?",
        )
    ]


def test_under_a_tree_s_open_schema_an_unknown_key_still_only_warns(
    schema: dict[str, Any], component_dir: Path
) -> None:
    """A tree synced before the flip carries its open schema, and that is the one
    applied (ADR-056 point 1): the same key, the same sentence, a warning."""
    raw = _package(foootprint=[".claude"])
    raw["commands"]["publish"]["hlep"] = "typo"
    findings = _validate(raw, _opened(schema), component_dir)
    assert _messages(findings, pv.Severity.ERROR) == {}
    assert _messages(findings, pv.Severity.WARNING) == {
        "/foootprint": "unknown key 'foootprint'; did you mean 'footprint'?",
        "/commands/publish/hlep": "unknown key 'hlep'; did you mean 'help'?",
    }


@pytest.mark.parametrize("field", ["schema_version", "description", "requires_backbone"])
@pytest.mark.parametrize("kind", ["capability", "adapter"])
def test_every_component_requires_the_fields_cor_017_lists(
    schema: dict[str, Any], component_dir: Path, field: str, kind: str
) -> None:
    raw = _package(component={"kind": kind, "name": "demo", "version": "0.1.0"})
    del raw[field]
    assert _messages(_validate(raw, schema, component_dir), pv.Severity.ERROR) == {
        "": f"'{field}' is a required property"
    }


# The address grammar the package schema's patterns must spell: the one address
# word (`backbone_schemas.ADDRESS_WORD_PATTERN`), which the configuration
# schema's selection keys admit.
_ROLE_PATTERN = f"^{bs.ADDRESS_WORD_PATTERN}::{bs.ADDRESS_WORD_PATTERN}$"
_POINT_PATTERN = (
    f"^{bs.ADDRESS_WORD_PATTERN}::{bs.ADDRESS_WORD_PATTERN}:{bs.ADDRESS_WORD_PATTERN}$"
)


def test_the_citation_grammar_re_exports_the_one_address_word() -> None:
    """The word is defined once, in `backbone_schemas`; the citation grammar in
    `refs` reads that definition rather than repeating it."""
    assert refs.ADDRESS_WORD_PATTERN is bs.ADDRESS_WORD_PATTERN


def test_addresses_share_the_configuration_schema_s_word_pattern(schema: dict[str, Any]) -> None:
    config = bs.load_backbone_schema(REPO, "config")
    selections = config["$defs"]["connections"]["properties"]
    assert set(selections["providers"]["patternProperties"]) == {_ROLE_PATTERN}
    assert set(selections["selections"]["patternProperties"]) == {_POINT_PATTERN}
    assert schema["$defs"]["qualified-role"]["pattern"] == _ROLE_PATTERN
    assert schema["$defs"]["point-address"]["pattern"] == _POINT_PATTERN


@pytest.mark.parametrize("role", ["Pkit::documentation", "pkit::docs_v2", "pkit::2docs"])
def test_an_address_that_is_not_words_is_refused(
    schema: dict[str, Any], component_dir: Path, role: str
) -> None:
    """Every place an address is written in `connections`: the patterns the shipped
    loose form (`[^\\s:]+` per part) admitted are refused now."""
    address = f"{role}:readers"
    connections = _connections(
        roles=[role],
        **{
            "extension-points": {
                "accepts": {
                    address: {
                        "schema_version": 1,
                        "schema": "reading-evidence.schema.json",
                        "description": "d",
                    }
                }
            }
        },
        extensions={
            "contributes": [{"point": address, "schema_version": 1, "value": []}],
            "depends-on": {"generated": True, "entries": [{"process": address}]},
        },
    )
    errors = _messages(
        _validate(_package(connections=connections), schema, component_dir), pv.Severity.ERROR
    )
    # A key's pattern failure (`propertyNames`) is located at the mapping holding it.
    refused = {
        "/connections/roles/0",
        "/connections/extension-points/accepts",
        "/connections/extensions/contributes/0/point",
        "/connections/extensions/depends-on/entries/0/process",
    }
    assert refused <= set(errors), errors
    assert f"{role!r} does not match" in errors["/connections/roles/0"]
    for pointer in refused - {"/connections/roles/0"}:
        assert f"{address!r} does not match" in errors[pointer]


@pytest.mark.parametrize(
    ("overrides", "path", "fragment"),
    [
        ({"schema_version": 3}, "/schema_version", "is not one of [1, 2]"),
        ({"component": {"kind": "capability", "name": "demo", "version": 1}}, "/component/version", "not of type 'string'"),
        ({"component": {"kind": "bundle", "name": "demo", "version": "0.1.0"}}, "/component/kind", "is not one of"),
        ({"requires_capabilities": "project-management"}, "/requires_capabilities", "not of type 'array'"),
        ({"aliases": ["Bad Name"]}, "/aliases/0", "does not match"),
        ({"footprint": [".claude", ".claude"]}, "/footprint", "non-unique"),
        ({"commands": {"publish": {"script": "scripts/publish.py"}}}, "/commands/publish", "'help' is a required property"),
    ],
)
def test_wrong_type_is_an_error(
    schema: dict[str, Any],
    component_dir: Path,
    overrides: dict[str, Any],
    path: str,
    fragment: str,
) -> None:
    errors = _messages(_validate(_package(**overrides), schema, component_dir), pv.Severity.ERROR)
    assert path in errors, errors
    assert fragment in errors[path]


def test_a_file_that_is_not_a_mapping_is_one_root_error(
    schema: dict[str, Any], tmp_path: Path
) -> None:
    package = tmp_path / "package.yaml"
    package.write_text("- just\n- a list\n", encoding="utf-8")
    report = pv.validate_package_file(package, schema)
    assert [(f.path, f.severity) for f in report.findings] == [("", pv.Severity.ERROR)]
    assert "expected a mapping" in report.findings[0].message


# --- repository checks -------------------------------------------------------


def test_point_under_a_role_the_package_does_not_provide_is_an_error(
    schema: dict[str, Any], component_dir: Path
) -> None:
    connections = _connections()
    connections["extension-points"]["accepts"]["pkit::analysis:use-cases"] = {
        "schema_version": 1,
        "schema": "reading-evidence.schema.json",
        "description": "Use cases.",
    }
    errors = _messages(
        _validate(_package(connections=connections), schema, component_dir), pv.Severity.ERROR
    )
    assert errors == {
        "/connections/extension-points/accepts/pkit::analysis:use-cases": (
            "point 'pkit::analysis:use-cases' is declared under role 'pkit::analysis', which "
            "this package does not provide (connections.roles: ['pkit::documentation'])."
        )
    }


def test_missing_companion_schema_is_an_error(
    schema: dict[str, Any], component_dir: Path
) -> None:
    connections = _connections()
    point = connections["extension-points"]["accepts"]["pkit::documentation:reading-evidence"]
    point["schema"] = "nope.schema.json"
    errors = _messages(
        _validate(_package(connections=connections), schema, component_dir), pv.Severity.ERROR
    )
    assert list(errors) == [
        "/connections/extension-points/accepts/pkit::documentation:reading-evidence/schema"
    ]
    assert "companion schema 'nope.schema.json' does not exist under demo/schemas/" in next(
        iter(errors.values())
    )


def test_referenced_command_that_does_not_exist_is_an_error(
    schema: dict[str, Any], component_dir: Path
) -> None:
    connections = _connections(
        extensions={
            "subscribes": [
                {"point": "pkit::analysis:use-case-created", "schema_version": 1, "command": "refresh"}
            ],
            "contributes": [
                {"point": "pkit::analysis:glossary", "schema_version": 1, "command": "create page"}
            ],
        }
    )
    connections["extension-points"]["offers"] = {
        "pkit::documentation:page-created": {
            "kind": "event",
            "schema_version": 1,
            "description": "A page landed.",
            "command": "create pgae",
            "schema": "reading-evidence.schema.json",
            "subject": "page",
        }
    }
    # The contribution's command is a filler: a query, declaring the query contract.
    commands = _package()["commands"]
    commands["create"]["page"]["query-contract"] = True
    errors = _messages(
        _validate(_package(connections=connections, commands=commands), schema, component_dir),
        pv.Severity.ERROR,
    )
    assert set(errors) == {
        "/connections/extensions/subscribes/0/command",
        "/connections/extension-points/offers/pkit::documentation:page-created/command",
    }
    assert errors["/connections/extensions/subscribes/0/command"] == (
        "command 'refresh' is not declared in `commands:` (declared: ['create page', 'publish'])."
    )
    # `create page` — a nested leaf — resolved, so the contribution raised nothing.


def test_a_validator_names_a_declared_command_that_declares_the_query_contract(
    schema: dict[str, Any], component_dir: Path
) -> None:
    undeclared = _messages(
        _validate(_package(validators={"citations": {"command": "refresh"}}), schema, component_dir),
        pv.Severity.ERROR,
    )
    assert undeclared == {
        "/validators/citations/command": (
            "validator 'citations': command 'refresh' is not declared in `commands:` "
            "(declared: ['create page', 'publish'])."
        )
    }
    no_contract = _messages(
        _validate(_package(validators={"citations": {"command": "publish"}}), schema, component_dir),
        pv.Severity.ERROR,
    )
    assert no_contract == {
        "/validators/citations/command": (
            "validator 'citations' names command 'publish', which does not declare the query "
            "contract (`query-contract: true` on its `commands:` entry)."
        )
    }
    raw = _package(validators={"citations": {"command": "create page", "order": 5}})
    raw["commands"]["create"]["page"]["query-contract"] = True
    assert _validate(raw, schema, component_dir) == []
    # The declaration is one constant: anything but `true` is the shape pass's error
    # at the leaf, and the validator that names the leaf is undeclared all the same.
    raw["commands"]["create"]["page"]["query-contract"] = False
    assert set(_messages(_validate(raw, schema, component_dir), pv.Severity.ERROR)) == {
        "/commands/create/page/query-contract",
        "/validators/citations/command",
    }


def test_command_script_that_does_not_exist_is_an_error(
    schema: dict[str, Any], component_dir: Path
) -> None:
    raw = _package()
    raw["commands"]["publish"]["script"] = "scripts/missing.py"
    errors = _messages(_validate(raw, schema, component_dir), pv.Severity.ERROR)
    assert errors == {
        "/commands/publish/script": (
            "command 'publish' names script 'scripts/missing.py', which does not exist under demo/."
        )
    }


def test_mandatory_mark_without_a_reason_is_an_error(
    schema: dict[str, Any], component_dir: Path
) -> None:
    connections = _connections()
    point = connections["extension-points"]["accepts"]["pkit::documentation:reading-evidence"]
    point["mandatory"] = True
    errors = _messages(
        _validate(_package(connections=connections), schema, component_dir), pv.Severity.ERROR
    )
    assert list(errors) == [
        "/connections/extension-points/accepts/pkit::documentation:reading-evidence/mandatory"
    ]
    point["mandatory"] = {"reason": "readers must exist for the discipline to mean anything"}
    assert _validate(_package(connections=connections), schema, component_dir) == []


_REVIEW = "pkit::documentation:review"
_REVIEW_POINTER = f"/connections/extension-points/offers/{_REVIEW}"


def _offering_review(schema_version: int) -> dict[str, Any]:
    """The package offering the process `review` under its role, at `schema_version`."""
    connections = _connections()
    connections["extension-points"]["offers"] = {
        _REVIEW: {
            "kind": "process",
            "schema_version": schema_version,
            "description": "The review process.",
            "process": "review",
        }
    }
    return _package(connections=connections)


def _write_definition(component_dir: Path, file: str, interface: str = "") -> None:
    (component_dir / "schemas" / file).write_text(
        "process:\n  id: review\n  version: 3\n" + interface, encoding="utf-8"
    )


def test_an_offered_process_point_carries_its_definition_s_interface_version(
    schema: dict[str, Any], component_dir: Path
) -> None:
    # Another file than `review.yaml` declares the id: the message names that file.
    _write_definition(component_dir, "reviewing.yaml", "  interface:\n    version: 1\n")
    errors = _messages(
        _validate(_offering_review(2), schema, component_dir), pv.Severity.ERROR
    )
    assert errors == {
        f"{_REVIEW_POINTER}/schema_version": (
            f"offered process point {_REVIEW!r} is at schema_version 2 in demo/package.yaml, "
            "but its definition demo/schemas/reviewing.yaml declares interface.version 1: an "
            "offered process carries its definition's interface version, so the two must be "
            "equal (COR-053 point 5)."
        )
    }
    # Equal: clean. The definition's own `version` (3) is not the interface's.
    assert _validate(_offering_review(1), schema, component_dir) == []


def test_an_offered_process_point_whose_definition_declares_no_interface_version_is_clean(
    schema: dict[str, Any], component_dir: Path
) -> None:
    _write_definition(component_dir, "review.yaml")
    assert _validate(_offering_review(2), schema, component_dir) == []


def test_an_offered_process_point_names_an_existing_definition(
    schema: dict[str, Any], component_dir: Path
) -> None:
    errors = _messages(
        _validate(_offering_review(1), schema, component_dir), pv.Severity.ERROR
    )
    assert errors == {
        f"{_REVIEW_POINTER}/process": (
            f"offered process point {_REVIEW!r} names process 'review', which no definition "
            "under demo/schemas/ declares."
        )
    }


def test_depends_on_must_carry_the_generated_mark(
    schema: dict[str, Any], component_dir: Path
) -> None:
    # The definition the list is generated from, so only the mark is at issue.
    (component_dir / "schemas" / "flow.yaml").write_text(
        "process:\n  id: flow\n  states:\n    - id: open\n      depends_on:\n"
        "        - upstream: project-management:issue-lifecycle\n",
        encoding="utf-8",
    )
    connections = _connections(
        extensions={"depends-on": {"entries": [{"process": "project-management:issue-lifecycle"}]}}
    )
    errors = _messages(
        _validate(_package(connections=connections), schema, component_dir), pv.Severity.ERROR
    )
    assert errors == {
        "/connections/extensions/depends-on": "'generated' is a required property"
    }
    connections["extensions"]["depends-on"]["generated"] = True
    assert _validate(_package(connections=connections), schema, component_dir) == []


# What the project-management package declared before the backbone took the
# process-journal ignore line over (#1120).
STALE_JOURNAL_LINE = ".pkit/capabilities/project-management/project/process/**/*.journal.jsonl"

# The journal settings under which the render drops a component's claim.
JOURNALS_COMMITTED = process_journal.JournalSettings(enabled=True, committed=True)


@pytest.mark.parametrize("pattern", [STALE_JOURNAL_LINE, process_journal.JOURNAL_GLOB])
def test_a_runtime_ignore_entry_declaring_committed_process_journals_is_warned(
    schema: dict[str, Any], component_dir: Path, pattern: str
) -> None:
    """Journals' ignore line is the backbone's; while the project commits them the
    render drops a component's claim on them — a warning, never an error."""
    raw = _package(runtime_ignore=[".pkit/capabilities/demo/project/instance/*.json", pattern])
    findings = pv.validate_package(
        raw, schema, component_dir=component_dir, expected_name="demo", journal=JOURNALS_COMMITTED
    )
    assert _messages(findings, pv.Severity.ERROR) == {}
    assert _messages(findings, pv.Severity.WARNING) == {
        "/runtime_ignore/1": pv.journal_claim_message(pattern)
    }


@pytest.mark.parametrize(
    "journal",
    [
        process_journal.JournalSettings(),
        process_journal.JournalSettings(enabled=True, committed=False),
        process_journal.JournalSettings(enabled=False, committed=True),
    ],
)
def test_a_claim_on_journals_kept_out_of_version_control_is_not_warned(
    schema: dict[str, Any], component_dir: Path, journal: process_journal.JournalSettings
) -> None:
    """While the journals stay ignored the claim is redundant: nothing to warn about."""
    raw = _package(runtime_ignore=[STALE_JOURNAL_LINE])
    findings = pv.validate_package(
        raw, schema, component_dir=component_dir, expected_name="demo", journal=journal
    )
    assert findings == []


@pytest.mark.parametrize(
    "pattern",
    [
        ".pkit/capabilities/demo/project/instance/*.json",
        ".pkit/capabilities/demo/project/process/notes.md",
        ".pkit/capabilities/demo/project/journal.jsonl",
    ],
)
def test_a_runtime_ignore_entry_that_is_not_a_journal_is_not_warned(
    schema: dict[str, Any], component_dir: Path, pattern: str
) -> None:
    raw = _package(runtime_ignore=[pattern])
    findings = pv.validate_package(
        raw, schema, component_dir=component_dir, expected_name="demo", journal=JOURNALS_COMMITTED
    )
    assert findings == []


@pytest.mark.parametrize(
    ("provenance", "fix"),
    [
        (pv.Provenance.OWN, "Drop the entry"),
        (pv.Provenance.SYNCED, "a synced copy the next sync overwrites, so do not edit it"),
        (pv.Provenance.PINNED, "move the pin to an author release that drops the entry"),
    ],
)
def test_the_journal_warning_names_the_backbone_pattern_and_the_way_out(
    provenance: pv.Provenance, fix: str
) -> None:
    message = pv.journal_claim_message(STALE_JOURNAL_LINE, provenance)
    assert repr(process_journal.JOURNAL_GLOB) in message
    assert "`process.journal.committed: true`" in message
    assert "the `.pkit/.gitignore` render drops the entry" in message
    assert fix in message


@pytest.mark.parametrize(
    ("path_value", "problem"),
    [("../pages", "contains a `..` segment"), ("/srv/docs", "is absolute"), ("a/../b", "contains a `..` segment")],
)
def test_docs_location_must_be_a_relative_sub_path(
    schema: dict[str, Any], component_dir: Path, path_value: str, problem: str
) -> None:
    raw = _package(docs={"locations": {"pages": {"path": path_value}}})
    errors = _messages(_validate(raw, schema, component_dir), pv.Severity.ERROR)
    assert errors == {
        "/docs/locations/pages/path": (
            f"{path_value!r} is not a sub-path relative to a documentation root: it {problem}."
        )
    }


def test_friction_places_lie_inside_a_declared_location_or_the_project(
    schema: dict[str, Any], component_dir: Path
) -> None:
    raw = _package(
        docs={"locations": {"pages": {"path": "pages", "root": "user"}}},
        friction={
            "places": [
                {"location": "pages", "path": "**/*.md"},
                {"path": "notes/**/*.md"},
                {"location": "spaces", "path": "**/*.md"},
                {"location": "pages", "path": "/etc/**"},
            ],
            "surface": ["src/**", "../elsewhere/**"],
        },
    )
    errors = _messages(_validate(raw, schema, component_dir), pv.Severity.ERROR)
    assert errors == {
        "/friction/places/2/location": (
            "place names location 'spaces', which `docs.locations` does not declare "
            "(declared: ['pages'])."
        ),
        "/friction/places/3/path": (
            "'/etc/**' is not a path relative to its location or the project: it is absolute."
        ),
        "/friction/surface/1": (
            "'../elsewhere/**' is not a repository-relative path: it contains a `..` segment."
        ),
    }


def test_friction_held_folders_are_written_and_checked_as_places_are(
    schema: dict[str, Any], component_dir: Path
) -> None:
    """The schema accepts the held list in the place shape and refuses another key
    in an entry; the repository checks hold its paths and locations as a place's."""
    raw = _package(
        docs={"locations": {"records": {"path": "records"}}},
        friction={
            "held": [
                {"location": "records", "path": "revalidations", "description": "The records."},
                {"path": "notes/acts"},
                {"location": "logs", "path": "runs"},
                {"location": "records", "path": "../outside"},
            ]
        },
    )
    errors = _messages(_validate(raw, schema, component_dir), pv.Severity.ERROR)
    assert errors == {
        "/friction/held/2/location": (
            "held folder names location 'logs', which `docs.locations` does not declare "
            "(declared: ['records'])."
        ),
        "/friction/held/3/path": (
            "'../outside' is not a path relative to its location or the project: it contains "
            "a `..` segment."
        ),
    }
    raw = _package(friction={"held": [{"path": "revalidations", "kind": "records"}]})
    errors = _messages(_validate(raw, schema, component_dir), pv.Severity.ERROR)
    assert list(errors) == ["/friction/held/0/kind"]


def test_legacy_messages_are_kept_and_run_without_a_schema(component_dir: Path) -> None:
    """The install-time check's messages are a subset of the validator's, schema or not."""
    raw = _package(
        component={"kind": "capability", "name": "other", "version": "not-a-version"},
        requires_backbone="banana",
        requires_capabilities=[{"name": "project-management", "version": "~~1"}],
    )
    errors = _messages(_validate(raw, None, component_dir), pv.Severity.ERROR)
    assert errors == {
        "/component/name": (
            "package.yaml component.name 'other' does not match the capability directory "
            "name 'demo'."
        ),
        "/component/version": (
            "package.yaml component.version 'not-a-version' is not a valid version "
            "(it gates dependency edges)."
        ),
        "/requires_backbone": "requires_backbone 'banana' is not a valid version specifier.",
        "/requires_capabilities/0/version": (
            "requires_capabilities entry for 'project-management' has an invalid version "
            "range '~~1'."
        ),
    }


@pytest.mark.parametrize(
    ("component", "path"),
    [
        ({"kind": "capability", "name": "demo"}, "/component"),
        ({"kind": "capability", "name": "demo", "version": ""}, "/component/version"),
    ],
    ids=["missing", "empty"],
)
def test_missing_or_empty_version_is_refused_without_a_schema(
    component_dir: Path, component: dict[str, Any], path: str
) -> None:
    """The old install-time refusal survives on the no-schema path, with its message."""
    findings = _validate(_package(component=component), None, component_dir)
    assert _messages(findings, pv.Severity.ERROR) == {
        path: "package.yaml is missing component.version."
    }


@pytest.mark.parametrize(
    ("component", "path", "fragment"),
    [
        ({"kind": "capability", "name": "demo"}, "/component", "'version' is a required property"),
        ({"kind": "capability", "name": "demo", "version": ""}, "/component/version", "non-empty"),
    ],
    ids=["missing", "empty"],
)
def test_a_location_the_shape_pass_rejected_is_reported_once(
    schema: dict[str, Any],
    component_dir: Path,
    component: dict[str, Any],
    path: str,
    fragment: str,
) -> None:
    """With a schema the shape pass owns the location; the repository pass adds nothing there."""
    findings = _validate(_package(component=component), schema, component_dir)
    assert [f.path for f in findings] == [path]
    assert fragment in findings[0].message


def test_if_condition_resolves_a_ref_against_the_schema_root() -> None:
    """A `$ref` inside an `if` is looked up from the schema root, not from the condition."""
    schema = {
        "$id": "conditional.schema.json",
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$defs": {"is-event": {"properties": {"kind": {"const": "event"}}}},
        "type": "object",
        "if": {"$ref": "#/$defs/is-event"},
        "then": {"properties": {"kind": {}, "command": {}}},
        "else": {"properties": {"kind": {}, "process": {}}},
    }
    walker = pv._UnknownKeyWalker(Draft202012Validator(schema))  # pyright: ignore[reportPrivateUsage]
    resource = Resource.from_contents(schema, default_specification=DRAFT202012)
    resolver = Registry().with_resource(schema["$id"], resource).resolver(base_uri=schema["$id"])
    assert walker.walk({"kind": "event", "command": "x"}, schema, resolver, "") == []
    warned = walker.walk({"kind": "event", "process": "x"}, schema, resolver, "")
    assert [(f.path, f.severity) for f in warned] == [("/process", pv.Severity.WARNING)]
    assert walker.walk({"kind": "process", "process": "x"}, schema, resolver, "") == []


def test_the_wiring_hooks_answer_from_the_resolver(tmp_path: Path) -> None:
    """Outside a project tree there is nothing to wire: no roles, no findings."""
    assert pv.resolve_active_roles(tmp_path) == frozenset()
    wiring = pv.check_wiring(tmp_path)
    assert wiring.roles == () and wiring.findings == ()


# --- the install-time path is a caller of the same validator ----------------


def _stage_incubated(root: Path, name: str, package_yaml: str) -> caps.CapabilitySource:
    cap_dir = root / ".pkit" / "capabilities" / name
    (cap_dir / "scripts").mkdir(parents=True)
    (cap_dir / "scripts" / "publish.py").write_text("", encoding="utf-8")
    (cap_dir / "package.yaml").write_text(package_yaml, encoding="utf-8")
    (cap_dir / "README.md").write_text(f"# {name}\n", encoding="utf-8")
    source = caps.find_capability_in_repo(root, name)
    assert source is not None
    return source


def test_install_time_check_still_refuses_what_it_refused_before(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    adopter = make_adopter_repo()
    source = _stage_incubated(
        adopter.root,
        "homegrown",
        "schema_version: 1\ncomponent:\n  kind: capability\n  name: homegrown\n"
        "  version: not-a-version\nrequires_backbone: banana\n",
    )
    problems = caps.validate_capability_self_consistency(source)
    assert any("not a valid version" in p for p in problems)
    assert any("not a valid version specifier" in p for p in problems)


def test_install_time_check_refuses_an_empty_version_without_a_schema(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    adopter = make_adopter_repo()
    bs.backbone_schema_path(adopter.root, pv.SCHEMA_KIND).unlink()
    source = _stage_incubated(
        adopter.root,
        "homegrown",
        "schema_version: 1\ncomponent:\n  kind: capability\n  name: homegrown\n"
        "  version: ''\nrequires_backbone: '>=1.0.0'\n",
    )
    problems = caps.validate_capability_self_consistency(source)
    assert any("package.yaml is missing component.version." in p for p in problems), problems


def test_install_time_check_refuses_the_new_repository_checks_too(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    adopter = make_adopter_repo()
    source = _stage_incubated(
        adopter.root,
        "homegrown",
        "schema_version: 1\ncomponent:\n  kind: capability\n  name: homegrown\n  version: 0.1.0\n"
        "requires_backbone: '>=1.0.0'\n"
        "connections:\n  roles: [pkit::documentation]\n  extension-points:\n    accepts:\n"
        "      pkit::analysis:use-cases: {schema_version: 1, schema: x.schema.json, description: d}\n",
    )
    problems = caps.validate_capability_self_consistency(source)
    assert any("does not provide" in p for p in problems)
    assert any("companion schema 'x.schema.json' does not exist" in p for p in problems)


_HOMEGROWN_WITH_A_TYPO = (
    "schema_version: 1\ncomponent:\n  kind: capability\n  name: homegrown\n  version: 0.1.0\n"
    "description: Grown at home.\nrequires_backbone: '>=1.0.0'\ndescriptoin: a typo\n"
)


def test_install_time_check_refuses_an_unknown_key(make_adopter_repo: MakeAdopterRepo) -> None:
    adopter = make_adopter_repo()
    source = _stage_incubated(adopter.root, "homegrown", _HOMEGROWN_WITH_A_TYPO)
    assert caps.validate_capability_self_consistency(source) == [
        "package.yaml/descriptoin: unknown key 'descriptoin'; did you mean 'description'?"
    ]


def test_install_time_check_does_not_refuse_on_a_warning(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """Under a tree's open schema the same key is a warning, and warnings never refuse."""
    adopter = make_adopter_repo()
    schema_path = bs.backbone_schema_path(adopter.root, pv.SCHEMA_KIND)
    schema_path.write_text(
        json.dumps(_opened(json.loads(schema_path.read_text(encoding="utf-8")))),
        encoding="utf-8",
    )
    source = _stage_incubated(adopter.root, "homegrown", _HOMEGROWN_WITH_A_TYPO)
    assert caps.validate_capability_self_consistency(source) == []


# --- `pkit validate`: the "packages" pass ------------------------------------


def _installed_package(adopter_root: Path, name: str) -> Path:
    return adopter_root / ".pkit" / "capabilities" / name / "package.yaml"


def test_pkit_validate_fails_on_an_unknown_key_naming_the_nearest_known_one(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    adopter = make_adopter_repo(capabilities=("evidence",))
    package = _installed_package(adopter.root, "evidence")
    package.write_text(package.read_text(encoding="utf-8") + "foootprint: [x]\n", encoding="utf-8")

    result = CliRunner().invoke(main, ["validate", "--no-refs"])
    assert result.exit_code == 1, result.output
    assert "packages" in result.output
    assert "1 error(s), 0 warning(s)" in result.output
    assert ".pkit/capabilities/evidence/package.yaml:/foootprint" in result.output
    assert "→ unknown key 'foootprint'; did you mean 'footprint'?" in result.output


def test_pkit_validate_under_a_tree_s_open_schema_warns_and_passes(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """A tree synced before the flip: its own open schema applies, so the key only warns."""
    adopter = make_adopter_repo(capabilities=("evidence",))
    schema_path = bs.backbone_schema_path(adopter.root, pv.SCHEMA_KIND)
    schema_path.write_text(
        json.dumps(_opened(json.loads(schema_path.read_text(encoding="utf-8")))),
        encoding="utf-8",
    )
    package = _installed_package(adopter.root, "evidence")
    package.write_text(package.read_text(encoding="utf-8") + "foootprint: [x]\n", encoding="utf-8")

    result = CliRunner().invoke(main, ["validate", "--no-refs"])
    assert result.exit_code == 0, result.output
    assert "0 error(s), 1 warning(s)" in result.output
    assert "warning  .pkit/capabilities/evidence/package.yaml:/foootprint" in result.output
    assert "→ unknown key 'foootprint'; did you mean 'footprint'?" in result.output


def test_pkit_validate_fails_on_a_package_error(make_adopter_repo: MakeAdopterRepo) -> None:
    adopter = make_adopter_repo(capabilities=("evidence",))
    package = _installed_package(adopter.root, "evidence")
    package.write_text(
        package.read_text(encoding="utf-8").replace("version: 0.5.1", "version: 5"),
        encoding="utf-8",
    )

    result = CliRunner().invoke(main, ["validate", "--no-refs"])
    assert result.exit_code == 1
    assert ".pkit/capabilities/evidence/package.yaml:/component/version" in result.output
    assert "5 is not of type 'string'" in result.output


@pytest.mark.parametrize(
    ("origin", "fix"),
    [
        # A synced copy: the next sync overwrites an edit.
        (ORIGIN_KIT_SHIPPED, "upgrade this component together with the backbone"),
        # Restored to its pin on every sync (COR-041).
        (ORIGIN_EXTERNALLY_SOURCED, "move the pin to an author release that drops the entry"),
        # The project's own file.
        (ORIGIN_INCUBATED_IN_REPO, "Drop the entry"),
    ],
)
def test_pkit_validate_warns_on_an_installed_package_declaring_process_journals(
    make_adopter_repo: MakeAdopterRepo, origin: str, fix: str
) -> None:
    """The reverse skew: an older package on a backbone that owns the journal line,
    in a project that commits its journals. The warning's fix is the one that
    lasts for where the package comes from."""
    adopter = make_adopter_repo(capabilities=("evidence",))
    set_capability_origin(adopter.root, "evidence", origin)
    set_journal_logging(adopter.root, enabled=True, committed=True)
    package = _installed_package(adopter.root, "evidence")
    stale = ".pkit/capabilities/evidence/project/process/**/*.journal.jsonl"
    package.write_text(
        package.read_text(encoding="utf-8") + f"runtime_ignore:\n  - {stale}\n", encoding="utf-8"
    )

    result = CliRunner().invoke(main, ["validate", "--no-refs"])
    assert result.exit_code == 0, result.output
    assert "0 error(s), 1 warning(s)" in result.output
    assert "warning  .pkit/capabilities/evidence/package.yaml:/runtime_ignore/0" in result.output
    assert f"→ {stale!r} declares process journals" in result.output
    assert fix in " ".join(result.output.split())


def test_pkit_validate_is_silent_on_a_claim_while_journals_are_kept_out(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """Journals the project does not commit stay ignored by the backbone's own
    line, so the same stale claim is redundant and not warned about."""
    adopter = make_adopter_repo(capabilities=("evidence",))
    set_journal_logging(adopter.root, enabled=True, committed=False)
    package = _installed_package(adopter.root, "evidence")
    stale = ".pkit/capabilities/evidence/project/process/**/*.journal.jsonl"
    package.write_text(
        package.read_text(encoding="utf-8") + f"runtime_ignore:\n  - {stale}\n", encoding="utf-8"
    )

    result = CliRunner().invoke(main, ["validate", "--no-refs"])
    assert result.exit_code == 0, result.output
    assert "0 error(s), 0 warning(s)" in result.output


def _declare_aliases(package: Path, *aliases: str) -> None:
    listed = "".join(f"  - {alias}\n" for alias in aliases)
    package.write_text(
        package.read_text(encoding="utf-8") + f"aliases:\n{listed}", encoding="utf-8"
    )


@pytest.mark.parametrize(
    ("alias", "shadowed_by"),
    [
        # A backbone command: every capability name and alias yields to it.
        ("status", "the backbone command `pkit status`, which every capability name and alias"),
        # Another capability's own name.
        ("software-analysis", "the name of capability 'software-analysis', which every alias"),
        # The same alias, declared by a capability earlier in the manifest.
        ("analysis", "the same alias of capability 'software-analysis', registered first"),
    ],
)
def test_an_alias_another_name_shadows_is_warned_naming_what_holds_it(
    make_adopter_repo: MakeAdopterRepo, alias: str, shadowed_by: str
) -> None:
    """`software-analysis` comes first in the manifest and declares `analysis`, so
    the later `evidence` cannot take its name or its alias, nor a backbone command."""
    adopter = make_adopter_repo(capabilities=("software-analysis", "evidence"))
    _declare_aliases(_installed_package(adopter.root, "evidence"), "ev", alias)

    result = pv.validate_installed_packages(adopter.root)
    findings = {
        (report.file.parent.name, f.path): f for report in result.reports for f in report.findings
    }
    assert result.errors == 0 and result.warnings == 1, list(findings)
    finding = findings[("evidence", "/aliases/1")]
    assert finding.severity is pv.Severity.WARNING
    message = " ".join(finding.message.split())
    assert message.startswith(
        f"alias {alias!r} of capability 'evidence' is shadowed by {shadowed_by}"
    )
    assert f"`pkit {alias}`" in message and "never evidence" in message
    assert "`pkit evidence …` still reaches it" in message


def test_pkit_validate_warns_on_an_alias_another_name_shadows_and_passes(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    adopter = make_adopter_repo(capabilities=("software-analysis", "evidence"))
    _declare_aliases(_installed_package(adopter.root, "evidence"), "analysis")

    result = CliRunner().invoke(main, ["validate", "--no-refs"])
    assert result.exit_code == 0, result.output
    assert "0 error(s), 1 warning(s)" in result.output
    assert "warning  .pkit/capabilities/evidence/package.yaml:/aliases/0" in result.output
    output = " ".join(result.output.split())
    assert (
        "→ alias 'analysis' of capability 'evidence' is shadowed by the same alias of "
        "capability 'software-analysis'"
    ) in output


def test_in_the_methodology_source_a_kit_shipped_package_is_its_own() -> None:
    """The source is where a kit-shipped package is authored, so the fix is to edit it."""
    package = REPO / ".pkit" / "capabilities" / "project-management" / "package.yaml"
    ownership = lifecycle_ownership.load_ownership(REPO)
    assert ownership is not None
    provenance = pv.package_provenance(REPO, package, ORIGIN_KIT_SHIPPED, ownership)
    assert provenance is pv.Provenance.OWN


def test_packages_pass_without_a_schema_in_the_tree_runs_repository_checks_only(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """A tree recorded before the schema landed: skipped shape, still the tree checks (ADR-056)."""
    adopter = make_adopter_repo(capabilities=("evidence",))
    bs.backbone_schema_path(adopter.root, pv.SCHEMA_KIND).unlink()
    package = _installed_package(adopter.root, "evidence")
    package.write_text(
        package.read_text(encoding="utf-8").replace("version: 0.5.1", "version: nope")
        + "foootprint: [x]\n",
        encoding="utf-8",
    )
    result = pv.validate_installed_packages(adopter.root)
    assert result.schema_note is not None and "skipped" in result.schema_note
    assert result.warnings == 0  # no schema, no unknown-key pass
    assert [f.path for r in result.reports for f in r.errors] == ["/component/version"]
