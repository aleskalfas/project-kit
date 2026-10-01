"""Role and point addresses as typed tokens (#996; COR-019 refined per COR-053):
the grammar, resolution against what installed capabilities declare, the
`pkit refs validate` findings, `pkit refs lookup`, and the schema fragment —
with the existing token kinds left as they were."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner
from jsonschema import Draft202012Validator
from ruamel.yaml import YAML

from project_kit import connections, refs, validators
from project_kit.cli import main
from project_kit.manifest import (
    ComponentRegistryEntry,
    read_backbone_manifest,
    write_backbone_manifest,
)
from project_kit.report_context import project_config_path
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo

REPO = Path(__file__).resolve().parents[1]
DOCS = "pkit::documentation"
READERS = f"{DOCS}:readers"
PAGE_CREATED = f"{DOCS}:page-created"

MALFORMED = (
    "pkit:documentation:readers",  # a single colon: never the address form
    "::documentation:readers",  # no publisher
    "pkit::",  # no role
    "pkit::documentation:",  # an empty point
    "pkit::documentation:readers:extra",  # a part too many
    "pkit::::documentation",  # the qualifier twice
    "Pkit::documentation",  # not a lowercase word
    "pkit::work_tracking",  # an underscore
)


# --- staging -------------------------------------------------------------------


def _stage(repo: AdopterRepo, name: str, connections_block: dict[str, Any]) -> Path:
    """Write `.pkit/capabilities/<name>/package.yaml` declaring `connections_block`
    and register it as incubated, as the wiring tests do."""
    cap_dir = repo.pkit / "capabilities" / name
    cap_dir.mkdir(parents=True, exist_ok=True)
    package = {
        "schema_version": 1,
        "component": {"kind": "capability", "name": name, "version": "0.1.0"},
        "description": f"Synthetic {name}.",
        "requires_backbone": ">=0.0.0",
        "connections": connections_block,
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
    return cap_dir / "package.yaml"


def _docs_provider(repo: AdopterRepo, name: str = "docs-a") -> Path:
    """A provider of the documentation role accepting `readers` and offering `page-created`."""
    return _stage(
        repo,
        name,
        {
            "roles": [DOCS],
            "extension-points": {
                "accepts": {
                    READERS: {
                        "schema_version": 1,
                        "schema": "readers.schema.json",
                        "description": "Who reads.",
                    }
                },
                "offers": {
                    PAGE_CREATED: {
                        "kind": "event",
                        "schema_version": 1,
                        "schema": "page-created.schema.json",
                        "command": "publish",
                        "description": "A page was created.",
                    }
                },
            },
        },
    )


def _citing_skill(repo: AdopterRepo, body: str, name: str = "citing") -> Path:
    path = repo.pkit / "skills" / "project" / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\nname: {name}\ndescription: t\n---\n# Skill\n{body}\n", encoding="utf-8")
    return path


def _address_issues(repo: AdopterRepo, skill: Path) -> list[refs.Issue]:
    location = str(skill.relative_to(repo.root))
    return [i for i in refs.validate_corpus(repo.root) if i.location == location]


# --- the grammar -----------------------------------------------------------------


def test_both_shapes_parse_bracketed_or_not() -> None:
    role = refs.parse_address(f"[{DOCS}]")
    assert role == refs.Address("pkit", "documentation") and role.role == DOCS
    assert str(role) == DOCS
    point = refs.parse_address(READERS)
    assert point == refs.Address("pkit", "documentation", "readers") and point.role == DOCS
    assert str(point) == READERS


@pytest.mark.parametrize("text", MALFORMED)
def test_a_malformed_address_does_not_parse(text: str) -> None:
    assert refs.parse_address(text) is None
    assert refs.parse_address(f"[{text}]") is None


def test_the_body_parser_reads_address_tokens_and_nothing_else() -> None:
    body = (
        f"Readers come from [{READERS}], under [{DOCS}]; a typo [::documentation:readers].\n"
        "Other families stay theirs: [issue-types:task], [issue-types:scope:task],\n"
        "[evidence:DEC-001-citation-discipline], [living-docs:RS-LDOC-001], COR-019.\n"
        f"Unbracketed {PAGE_CREATED} is prose, not a token.\n"
        f"```\n[{PAGE_CREATED}]\n```\n"
    )
    found = refs.extract_body_refs(body)
    assert found.addresses == frozenset({READERS, DOCS, "::documentation:readers"})
    assert found.capability_citations == frozenset({("evidence", "DEC-001-citation-discipline")})
    assert found.rule_citations == frozenset({"living-docs:RS-LDOC-001"})
    assert found.records == frozenset({"COR-019"})


def test_the_schema_fragment_is_the_parser_grammar_and_the_schema_token_is_unchanged() -> None:
    shared = json.loads((REPO / ".pkit/schemas/_defs/refs.schema.json").read_text())
    fragments = shared["$defs"]
    assert fragments["address_token"]["pattern"] == rf"^\[{refs.ADDRESS_PATTERN}\]$"
    address = Draft202012Validator(fragments["address_token"])
    schema_token = Draft202012Validator(fragments["reference_token"])
    for good in (f"[{DOCS}]", f"[{READERS}]"):
        assert address.is_valid(good)
        assert not schema_token.is_valid(good)  # the schema token did not widen
    for bad in MALFORMED:
        assert not address.is_valid(f"[{bad}]")
    for schema_reference in ("[issue-types:task]", "[issue-types:scope:task]"):
        assert schema_token.is_valid(schema_reference)
        assert not address.is_valid(schema_reference)
    assert re.fullmatch(refs.ADDRESS_PATTERN, READERS)


# --- resolution ----------------------------------------------------------------


def test_a_role_token_resolves_to_its_provider(make_adopter_repo: MakeAdopterRepo) -> None:
    repo = make_adopter_repo()
    _docs_provider(repo)
    resolution = refs.resolve_address(repo.root, f"[{DOCS}]")
    assert resolution.resolved and not resolution.malformed
    assert resolution.providers == ("docs-a",)
    assert resolution.locations == (".pkit/capabilities/docs-a/package.yaml:/connections/roles/0",)


def test_a_point_token_resolves_to_its_declaration(make_adopter_repo: MakeAdopterRepo) -> None:
    repo = make_adopter_repo()
    _docs_provider(repo)
    readers = refs.resolve_address(repo.root, f"[{READERS}]")
    assert readers.resolved
    assert [(p.address, p.provider, p.kind) for p in readers.points] == [
        (READERS, "docs-a", connections.PointKind.DATA)
    ]
    assert readers.locations == (
        f".pkit/capabilities/docs-a/package.yaml:/connections/extension-points/accepts/{READERS}",
    )
    event = refs.resolve_address(repo.root, PAGE_CREATED)
    assert event.resolved and event.points[0].kind is connections.PointKind.EVENT


def test_a_role_in_conflict_resolves_to_every_provider(make_adopter_repo: MakeAdopterRepo) -> None:
    """Two providers and no selection: the citation is well aimed; the conflict is
    the `connections` pass's finding, not the citation's."""
    repo = make_adopter_repo()
    _docs_provider(repo, "docs-a")
    _docs_provider(repo, "docs-b")
    role = refs.resolve_address(repo.root, DOCS)
    assert role.resolved and role.providers == ("docs-a", "docs-b")
    point = refs.resolve_address(repo.root, READERS)
    assert point.resolved and [p.provider for p in point.points] == ["docs-a", "docs-b"]


def test_a_selected_provider_is_the_one_a_token_resolves_to(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    _docs_provider(repo, "docs-a")
    _docs_provider(repo, "docs-b")
    config = project_config_path(repo.root)
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(f"connections:\n  providers:\n    {DOCS}: docs-b\n", encoding="utf-8")
    assert refs.resolve_address(repo.root, DOCS).providers == ("docs-b",)
    assert [p.provider for p in refs.resolve_address(repo.root, READERS).points] == ["docs-b"]


def test_a_malformed_address_is_a_grammar_error_not_a_resolution_one(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    _docs_provider(repo)
    for text in ("pkit:documentation:readers", "::documentation:readers"):
        resolution = refs.resolve_address(repo.root, text)
        assert resolution.malformed and not resolution.resolved
        assert resolution.problem == refs.NOT_AN_ADDRESS
    undeclared = refs.resolve_address(repo.root, f"{DOCS}:nope")
    assert not undeclared.malformed and not undeclared.resolved


# --- `pkit refs validate` ---------------------------------------------------------


def test_resolving_tokens_raise_no_finding(make_adopter_repo: MakeAdopterRepo) -> None:
    repo = make_adopter_repo()
    _docs_provider(repo)
    skill = _citing_skill(repo, f"Readers come from [{READERS}], under [{DOCS}].")
    assert _address_issues(repo, skill) == []


def test_an_undeclared_point_is_reported_like_an_unresolved_record_token(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    _docs_provider(repo)
    skill = _citing_skill(repo, f"See [{DOCS}:nope] and [missing:DEC-001-gone] for the rule.")
    issues = _address_issues(repo, skill)
    [point] = [i for i in issues if f"[{DOCS}:nope]" in i.diagnosis]
    [record] = [i for i in issues if "[missing:DEC-001-gone]" in i.diagnosis]
    # One shape: the citing artifact, a `cites …` diagnosis, the citation kind.
    assert (
        (point.location, point.kind)
        == (record.location, record.kind)
        == (
            str(skill.relative_to(repo.root)),
            refs.CITATION,
        )
    )
    assert point.diagnosis == (
        f"cites point '[{DOCS}:nope]', which does not resolve: no installed provider of role "
        f"'{DOCS}' declares point 'nope' (declared: '{PAGE_CREATED}', '{READERS}')."
    )


def test_an_undeclared_role_is_reported(make_adopter_repo: MakeAdopterRepo) -> None:
    repo = make_adopter_repo()
    _docs_provider(repo)
    skill = _citing_skill(repo, "Tracked through [acme::tracking] and [acme::tracking:board].")
    assert sorted(i.diagnosis for i in _address_issues(repo, skill)) == [
        "cites point '[acme::tracking:board]', which does not resolve: no installed capability "
        "provides role 'acme::tracking'.",
        "cites role '[acme::tracking]', which does not resolve: no installed capability "
        "provides role 'acme::tracking'.",
    ]


def test_a_malformed_token_is_reported_as_a_grammar_finding(
    make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Judged on its text alone: the wiring is never read for it."""
    repo = make_adopter_repo()
    skill = _citing_skill(repo, "Readers come from [::documentation:readers].")

    def _no_wiring(_root: Path) -> connections.Wiring:
        raise AssertionError("a grammar finding must not read the wiring")

    monkeypatch.setattr(connections, "shared_wiring", _no_wiring)
    [issue] = _address_issues(repo, skill)
    assert issue.kind == refs.CITATION
    assert issue.diagnosis == (
        f"cites '[::documentation:readers]', which is {refs.NOT_AN_ADDRESS}."
    )
    assert "does not resolve" not in issue.diagnosis


def test_a_corpus_citing_no_address_never_reads_the_wiring(
    make_adopter_repo: MakeAdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = make_adopter_repo()
    _citing_skill(repo, "See [issue-types:task] and COR-019.")

    def _no_wiring(_root: Path) -> connections.Wiring:
        raise AssertionError("nothing cites an address")

    monkeypatch.setattr(connections, "shared_wiring", _no_wiring)
    refs.validate_corpus(repo.root)


def test_pkit_validate_counts_an_unresolved_address_as_an_error(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    skill = _citing_skill(repo, "Tracked through [acme::tracking].")
    location = str(skill.relative_to(repo.root))
    [finding] = [f for f in refs.outcome(repo.root).findings if f.location == location]
    assert finding.severity is validators.Severity.ERROR


def test_cli_refs_validate_fails_on_an_unresolved_address(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    _citing_skill(repo, "Tracked through [acme::tracking].")
    result = CliRunner().invoke(main, ["refs", "validate"])
    assert result.exit_code == 1
    assert "cites role '[acme::tracking]', which does not resolve" in result.output


# --- `pkit refs lookup` -----------------------------------------------------------


def test_cli_refs_lookup_prints_where_an_address_is_declared(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    _docs_provider(repo)
    result = CliRunner().invoke(main, ["refs", "lookup", f"[{READERS}]"])
    assert result.exit_code == 0, result.output
    assert result.output.strip() == (
        f".pkit/capabilities/docs-a/package.yaml:/connections/extension-points/accepts/{READERS}"
    )
    role = CliRunner().invoke(main, ["refs", "lookup", DOCS])
    assert role.output.strip() == ".pkit/capabilities/docs-a/package.yaml:/connections/roles/0"


def test_cli_refs_lookup_tells_a_malformed_address_from_an_undeclared_one(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    repo = make_adopter_repo()
    _docs_provider(repo)
    malformed = CliRunner().invoke(main, ["refs", "lookup", "[::documentation:readers]"])
    assert malformed.exit_code != 0
    assert "is not a role or point address" in malformed.output
    undeclared = CliRunner().invoke(main, ["refs", "lookup", f"{DOCS}:nope"])
    assert undeclared.exit_code != 0
    assert "does not resolve: no installed provider of role" in undeclared.output


def test_cli_refs_lookup_still_resolves_records(make_adopter_repo: MakeAdopterRepo) -> None:
    make_adopter_repo()
    result = CliRunner().invoke(main, ["refs", "lookup", "COR-019"])
    assert result.exit_code == 0, result.output
    assert result.output.strip() == ".pkit/decisions/core/COR-019-schema-reference-form.md"
