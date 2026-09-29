"""living-docs' places, the LDOC rule set, and the space and page templates (#1003).

The capability's first artefacts, each held to living-docs DEC-001:

- the **validator**, `pkit living-docs validate` — the `living-docs:spaces`
  member of `pkit validate` — over an adopter repository with the capability
  installed: one test per rule it applies (an out-of-root place without an
  assignment, a place enclosing a root, a record declared as a page, another
  component's place, an entry point outside its space, a page's fields, the
  most specific place, a definition that does not inherit LDOC), and the
  readers each page's reader resolves against, named in its summary (reader
  resolution itself is `test_living_docs_points.py`'s);
- the **LDOC rule set** validating as a method rule set with its origins, and
  a space definition instantiated from the template inheriting it;
- the **page template** validating — its own fields by the capability's
  schema, its friction block by the core's.

The validator runs as a subprocess under this interpreter, as the backbone
runs it (its `--json` findings document); where `pkit validate` runs it, the
script's `uv run --script` shebang is pointed at this interpreter, and the
`pkit` it reads the readers point through is the real CLI under this
interpreter (`pkit_on_path`), so no test reaches `uv` or the network.
project-kit's own configuration passing is in `test_self_host_documentation.py`.
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner
from jsonschema import Draft202012Validator
from ruamel.yaml import YAML

from project_kit import backbone_schemas as bs
from project_kit import friction_discovery as fd
from project_kit import rule_sets as rs
from project_kit.cli import main
from project_kit.manifest import (
    ComponentRegistryEntry,
    read_backbone_manifest,
    write_backbone_manifest,
)
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo

REPO = Path(__file__).resolve().parent.parent
CAPABILITY = REPO / ".pkit" / "capabilities" / "living-docs"
LD = Path(".pkit") / "capabilities" / "living-docs"
SCRIPT = LD / "scripts" / "validate.py"
CONFIG = ".pkit/project/config.yaml"
LD_CONFIG = f"{LD.as_posix()}/project/config.yaml"
DEFINITIONS = "tech-docs/living-docs/rule-sets"

PAGE = "---\nreader: user\nkind: signpost\n---\n\n# Guide\n"
RECORD = "---\nid: ADR-001\ntitle: A decision\nstatus: accepted\n---\n\n## Context\n"


def _yaml(data: Mapping[str, Any]) -> str:
    buffer = io.StringIO()
    YAML().dump(dict(data), buffer)
    return buffer.getvalue()


def _definition(set_name: str, inherits: list[str] | None = None) -> str:
    """A space definition instantiated from the capability's template."""
    template = (CAPABILITY / "templates" / "space-definition.md").read_text(encoding="utf-8")
    text = template.replace("rule-set: SPACE", f"rule-set: {set_name}").replace(
        "<space>", set_name.lower()
    )
    if inherits is not None:
        text = text.replace("inherits: [living-docs:LDOC@1]", f"inherits: {json.dumps(inherits)}")
    return text


def declare(
    repo: AdopterRepo,
    *,
    places: list[str] | None = None,
    assignments: Mapping[str, str] | None = None,
    spaces: Mapping[str, Mapping[str, str]] | None = None,
    roots: Mapping[str, str] | None = None,
) -> None:
    """The backbone configuration (roots, project places) and living-docs' own."""
    config = {
        "docs": dict(roots or {"user": "docs/", "internal": "tech-docs/"}),
        "friction": {"places": list(places if places is not None else ["README.md"])},
    }
    repo.write({CONFIG: _yaml(config)})
    own = {
        "pkit_schema": "living-docs:config",
        "schema_version": 1,
        "spaces": dict(
            spaces
            if spaces is not None
            else {
                "user": {"entry-point": "README.md", "definition": f"{DEFINITIONS}/user.md"},
                "technical": {
                    "entry-point": "tech-docs/README.md",
                    "definition": f"{DEFINITIONS}/technical.md",
                },
            }
        ),
        "places": dict(assignments if assignments is not None else {"README.md": "user"}),
    }
    repo.write({LD_CONFIG: _yaml(own)})


@pytest.fixture
def project(make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path) -> AdopterRepo:
    """An adopter with living-docs installed, two separate roots, one page per
    space's entry, a decision record, and both spaces' definitions — clean."""
    repo = make_adopter_repo(capabilities=("living-docs",))
    script = repo.root / SCRIPT
    body = script.read_text(encoding="utf-8").split("\n", 1)[1]
    script.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
    declare(repo)
    repo.write(
        {
            "README.md": PAGE,
            "docs/guide.md": PAGE,
            "tech-docs/README.md": "---\nreader: maintainer\nkind: signpost\n---\n\n# Tech\n",
            "tech-docs/architecture/decisions/ADR-001-a-decision.md": RECORD,
            f"{DEFINITIONS}/user.md": _definition("USER"),
            f"{DEFINITIONS}/technical.md": _definition("TECH"),
        }
    )
    return repo


def run(repo: AdopterRepo) -> dict[str, Any]:
    """The validator's findings document, run as the backbone runs it."""
    completed = subprocess.run(
        [sys.executable, str(repo.root / SCRIPT), "--json"],
        cwd=repo.root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def errors(document: Mapping[str, Any]) -> list[tuple[str, str]]:
    return [(f["location"], f["message"]) for f in document["findings"] if f["severity"] == "error"]


def only_error(document: Mapping[str, Any]) -> tuple[str, str]:
    (found,) = errors(document)
    return found


# --- a clean project, and what is dormant -----------------------------------------------


def test_a_clean_project_answers_with_no_finding_and_names_the_readers(
    project: AdopterRepo,
) -> None:
    document = run(project)
    assert document["findings"] == []
    summary = document["summary"]
    assert summary[1] == (
        "user: 2 page(s); entry point README.md, a page; definition "
        "tech-docs/living-docs/rule-sets/user.md."
    )
    assert summary[2] == (
        "technical: 1 page(s); entry point tech-docs/README.md, a page; definition "
        "tech-docs/living-docs/rule-sets/technical.md."
    )
    assert "1 decision record(s)" in summary[3] and "2 in the definitions location" in summary[3]
    assert summary[4] == (
        "readers (pkit::documentation:readers): maintainer, user; 3 page reader(s) checked."
    )


def test_the_validator_is_a_member_of_pkit_validate(project: AdopterRepo) -> None:
    result = CliRunner().invoke(
        main, ["--color", "never", "validate", "--only", "living-docs:spaces"]
    )
    assert result.exit_code == 0, result.output
    assert "living-docs:spaces" in result.output
    assert "readers (pkit::documentation:readers): maintainer, user" in result.output
    project.write({"docs/guide.md": "---\nreader: 42\nkind: signpost\n---\n"})
    result = CliRunner().invoke(
        main, ["--color", "never", "validate", "--only", "living-docs:spaces"]
    )
    assert result.exit_code == 1
    assert "docs/guide.md:/reader" in result.output
    # A well-formed reader the readers point does not hold fails the page too.
    project.write({"docs/guide.md": "---\nreader: guest\nkind: signpost\n---\n"})
    result = CliRunner().invoke(
        main, ["--color", "never", "validate", "--only", "living-docs:spaces"]
    )
    assert result.exit_code == 1
    assert "reader 'guest', which does not resolve" in result.output


# --- places and their assignment (DEC-001 point 1) ---------------------------------------


def test_an_out_of_root_place_holding_a_document_needs_an_assignment(project: AdopterRepo) -> None:
    declare(project, places=["README.md", "CONTRIBUTING.md"])
    project.write({"CONTRIBUTING.md": "# Contributing\n"})
    location, message = only_error(run(project))
    assert location == f"{CONFIG}:/friction/places/1"
    assert (
        "lies outside every documentation root and holds a document nothing else claims" in message
    )
    assert "add `CONTRIBUTING.md: <space>` under `places`" in message


def test_an_out_of_root_place_holding_only_what_something_else_claims_needs_none(
    project: AdopterRepo,
) -> None:
    declare(project, places=["README.md", "records/"])
    project.write({"records/ADR-002-other.md": RECORD.replace("ADR-001", "ADR-002")})
    assert errors(run(project)) == []


def test_an_assignment_names_a_declared_place_and_a_declared_space(project: AdopterRepo) -> None:
    declare(
        project,
        places=["README.md", "NOTES.md"],
        assignments={"README.md": "user", "./NOTES.md/": "readers", "GHOST.md": "user"},
    )
    found = errors(run(project))
    assert [location for location, _ in found] == [
        f"{LD_CONFIG}:/places/.~1NOTES.md~1",
        f"{LD_CONFIG}:/places/GHOST.md",
    ]
    # The join is a normalised path: `./NOTES.md/` is NOTES.md, so only its space is wrong.
    assert "to space 'readers', which is not a space of this project" in found[0][1]
    assert "which `friction.places` in .pkit/project/config.yaml does not declare" in found[1][1]


def test_a_place_is_assigned_to_exactly_one_space(project: AdopterRepo) -> None:
    declare(project, assignments={"README.md": "user", "./README.md": "technical"})
    location, message = only_error(run(project))
    assert location == f"{LD_CONFIG}:/places/.~1README.md"
    assert "the place already assigned as 'README.md'" in message


@pytest.mark.parametrize("place", ["docs/", "docs", "docs/**", "**/*.md", ".", "**"])
def test_a_place_equal_to_or_enclosing_a_root_is_refused(project: AdopterRepo, place: str) -> None:
    declare(project, places=["README.md", place])
    found = errors(run(project))
    assert found[0][0] == f"{CONFIG}:/friction/places/1"
    assert "is equal to or encloses the user root 'docs'" in found[0][1]


def test_a_place_inside_a_root_is_not_refused_and_takes_the_root_s_space(
    project: AdopterRepo,
) -> None:
    declare(project, places=["README.md", "docs/*.md"])
    document = run(project)
    assert errors(document) == []
    assert document["summary"][1].startswith("user: 2 page(s)")


def test_the_most_specific_place_wins(project: AdopterRepo) -> None:
    """A project place inside the user root, assigned to the technical space, takes
    its pages from the root: a project place beats a root."""
    declare(
        project,
        places=["README.md", "docs/internal/"],
        assignments={"README.md": "user", "docs/internal/": "technical"},
    )
    project.write({"docs/internal/notes.md": PAGE})
    summary = run(project)["summary"]
    assert summary[1].startswith("user: 2 page(s)")
    assert summary[2].startswith("technical: 2 page(s)")


def test_a_file_two_project_places_claim_with_equal_specificity_is_an_error(
    project: AdopterRepo,
) -> None:
    declare(
        project,
        places=["README.md", "extra/*.md", "extra/[ab].md"],
        assignments={"README.md": "user", "extra/*.md": "user", "extra/[ab].md": "technical"},
    )
    project.write({"extra/a.md": PAGE})
    location, message = only_error(run(project))
    assert location == f"{CONFIG}:/friction/places/2"
    assert (
        "'extra/*.md' and 'extra/[ab].md' both claim extra/a.md with equal specificity" in message
    )


# --- what is never a page (DEC-001 points 1 and 4) ---------------------------------------


def test_a_record_declared_as_a_page_is_an_error(project: AdopterRepo) -> None:
    adr = "tech-docs/architecture/decisions/ADR-001-a-decision.md"
    project.write(
        {adr: RECORD.replace("status: accepted\n", "status: accepted\nreader: maintainer\n")}
    )
    location, message = only_error(run(project))
    assert location == f"{adr}:/reader"
    assert "is a decision record (ADR-001), an anchor target" in message
    assert "remove `reader`" in message


def test_a_rule_set_file_declared_as_a_page_is_an_error(project: AdopterRepo) -> None:
    rule_set = "tech-docs/rule-sets/cmn.md"
    front = "rule-set: CMN\nversion: 1.0.0\nrules: {}\nreader: user\nkind: signpost\n"
    project.write({rule_set: f"---\n{front}---\n"})
    location, message = only_error(run(project))
    assert location == f"{rule_set}:/reader"
    assert "is a rule-set file, an anchor target (COR-051)" in message


def _install_component_with_place(repo: AdopterRepo) -> None:
    """Another capability, declaring a place under the internal root."""
    cap = repo.root / ".pkit" / "capabilities" / "analysis-test"
    cap.mkdir(parents=True)
    (cap / "package.yaml").write_text(
        _yaml(
            {
                "schema_version": 1,
                "component": {"kind": "capability", "name": "analysis-test", "version": "0.1.0"},
                "description": "An analysis capability, for the test.",
                "requires_backbone": ">=0.0.0",
                "docs": {"locations": {"analysis": {"path": "analysis"}}},
                "friction": {"places": [{"location": "analysis", "path": "."}]},
            }
        ),
        encoding="utf-8",
    )
    backbone = read_backbone_manifest(repo.root)
    assert backbone is not None
    backbone.components.append(
        ComponentRegistryEntry(
            kind="capability",
            name="analysis-test",
            manifest=".pkit/capabilities/analysis-test/project/manifest.yaml",
            origin="incubated-in-repo",
        )
    )
    write_backbone_manifest(repo.root, backbone)


def test_another_component_s_place_is_never_a_page(project: AdopterRepo) -> None:
    _install_component_with_place(project)
    project.write({"tech-docs/analysis/uc-001.md": "---\nid: UC-001\n---\n"})
    document = run(project)
    assert errors(document) == []
    assert "1 of another component" in document["summary"][3]
    project.write({"tech-docs/analysis/uc-001.md": "---\nid: UC-001\nkind: signpost\n---\n"})
    location, message = only_error(run(project))
    assert location == "tech-docs/analysis/uc-001.md:/kind"
    assert "is an artefact of analysis-test, which declares the place it is in" in message


# --- entry points (DEC-001 point 1) ------------------------------------------------------


@pytest.mark.parametrize(
    ("entry", "problem"),
    [
        ("README.md", "belongs to space 'user', by its root or its assignment"),
        ("docs/guide.md", "belongs to space 'user', by its root or its assignment"),
        ("tech-docs/missing.md", "is not a Markdown document of the working tree"),
        (
            "tech-docs/architecture/decisions/ADR-001-a-decision.md",
            "is a decision record (ADR-001), an anchor target (COR-050), never a page",
        ),
        ("notes/elsewhere.md", "lies in no place of any space"),
    ],
)
def test_an_entry_point_outside_its_space_is_an_error(
    project: AdopterRepo, entry: str, problem: str
) -> None:
    project.write({"notes/elsewhere.md": PAGE})
    declare(
        project,
        spaces={
            "user": {"entry-point": "README.md", "definition": f"{DEFINITIONS}/user.md"},
            "technical": {"entry-point": entry, "definition": f"{DEFINITIONS}/technical.md"},
        },
    )
    location, message = only_error(run(project))
    assert location == f"{LD_CONFIG}:/spaces/technical/entry-point"
    assert f"the entry point of space 'technical', {entry!r}, {problem}" in message


def test_an_entry_point_not_yet_a_page_is_shown_not_failed(project: AdopterRepo) -> None:
    project.write({"README.md": "# Project\n"})
    document = run(project)
    assert errors(document) == []
    assert "entry point README.md, not yet a page" in document["summary"][1]


# --- pages' own fields (DEC-001 point 4) -------------------------------------------------


@pytest.mark.parametrize(
    ("front", "location"),
    [
        ("reader: User Guide\nkind: signpost", "docs/guide.md:/reader"),
        ("reader: [user, maintainer]\nkind: signpost", "docs/guide.md:/reader"),
        ("reader: user\nkind: 3", "docs/guide.md:/kind"),
        ("reader: user", "docs/guide.md"),
        ("kind: signpost", "docs/guide.md"),
    ],
)
def test_a_page_with_a_wrong_reader_or_kind_field_fails(
    project: AdopterRepo, front: str, location: str
) -> None:
    project.write({"docs/guide.md": f"---\n{front}\n---\n\n# Guide\n"})
    found_location, message = only_error(run(project))
    assert found_location == location
    assert "schemas/page.schema.json; DEC-001 point 4" in message


def test_a_document_carrying_neither_field_is_unclassified_for_onboarding(
    project: AdopterRepo,
) -> None:
    project.write({"docs/old.md": "# An old page\n"})
    document = run(project)
    assert errors(document) == []
    assert "1 unclassified document(s) for onboarding" in document["summary"][3]


# --- definitions (DEC-001 point 2) -------------------------------------------------------


def test_a_definition_inherits_the_shared_method(project: AdopterRepo) -> None:
    project.write({f"{DEFINITIONS}/technical.md": _definition("TECH", inherits=["USER@1"])})
    location, message = only_error(run(project))
    assert location == f"{LD_CONFIG}:/spaces/technical/definition"
    assert (
        "does not inherit the shared method: add `living-docs:LDOC@1` to its `inherits`" in message
    )


def test_a_definition_lives_in_the_definitions_location_s_rule_sets(project: AdopterRepo) -> None:
    project.write({"tech-docs/rule-sets/technical.md": _definition("TECH")})
    declare(
        project,
        spaces={
            "user": {"entry-point": "README.md", "definition": f"{DEFINITIONS}/user.md"},
            "technical": {
                "entry-point": "tech-docs/README.md",
                "definition": "tech-docs/rule-sets/technical.md",
            },
        },
    )
    location, message = only_error(run(project))
    assert location == f"{LD_CONFIG}:/spaces/technical/definition"
    assert f"lies outside {DEFINITIONS}/" in message


def test_a_space_without_a_definition_yet_is_reported(project: AdopterRepo) -> None:
    declare(project, spaces={"user": {"entry-point": "README.md"}})
    document = run(project)
    assert errors(document) == []
    reports = [f["location"] for f in document["findings"] if f["severity"] == "report"]
    assert reports == [f"{LD_CONFIG}:/spaces/user", f"{LD_CONFIG}:/spaces/technical"]


# --- separation (DEC-001 point 1) --------------------------------------------------------


def test_roots_that_are_one_folder_are_reported_not_failed(project: AdopterRepo) -> None:
    declare(project, roots={"user": "docs/", "internal": "docs/"}, spaces={})
    document = run(project)
    assert errors(document) == []
    separation = [f for f in document["findings"] if f["location"] == f"{CONFIG}:/docs"]
    assert [f["severity"] for f in separation] == ["report"]
    assert "both documentation roots are 'docs'" in separation[0]["message"]


# --- the package metadata ----------------------------------------------------------------


def test_the_package_declares_the_roots_and_the_definitions_as_places(project: AdopterRepo) -> None:
    settings = fd.read_friction_settings(project.root)
    ours = [p.resolved for p in settings.places if p.source == "capability:living-docs"]
    assert ours == ["docs/**", "tech-docs/**", "tech-docs/living-docs/rule-sets"]
    # The definitions are project rule sets: the backbone reads them there.
    places = fd.rule_set_places(project.root, settings)
    definitions = [p for p in places if p.pattern == "tech-docs/living-docs/rule-sets"]
    assert [p.component for p in definitions] == [None]


# --- the LDOC rule set and the space definition template (DEC-001 points 2 and 3) --------


def test_ldoc_validates_as_a_method_rule_set_with_its_origins(project: AdopterRepo) -> None:
    result = rs.validate_rule_sets(project.root)
    assert result.errors == ()
    (ldoc,) = result.discovery.sets_named("LDOC")
    assert (ldoc.component, ldoc.version, ldoc.path) == (
        "living-docs",
        "1.0.0",
        ".pkit/capabilities/living-docs/rule-sets/ldoc.md",
    )
    assert [rule.id for rule in ldoc.rules] == [f"RS-LDOC-00{n}" for n in range(1, 7)]
    for rule in ldoc.rules:
        assert rule.status == "accepted"
        assert rule.origin == {"decision": "living-docs:DEC-001"}
        assert rule.anchors("record") == ("living-docs:DEC-001",)


def test_a_space_definition_from_the_template_inherits_ldoc(project: AdopterRepo) -> None:
    result = rs.validate_rule_sets(project.root)
    assert result.errors == ()
    for name in ("USER", "TECH"):
        (definition,) = result.discovery.sets_named(name)
        assert definition.component is None  # a project rule set, cited bare
        assert [str(pin) for _index, pin in definition.pins] == ["living-docs:LDOC@1"]
    checks = rs.pin_checks(result.discovery)
    assert {c.rule_set.name for c in checks} == {"USER", "TECH"}
    assert all(c.problem is None for c in checks)


# --- the page template (DEC-001 points 3 and 4) ------------------------------------------


def _page_schema() -> Draft202012Validator:
    schema = json.loads((CAPABILITY / "schemas" / "page.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _template_front_matter(name: str) -> dict[str, Any]:
    text = (CAPABILITY / "templates" / f"{name}.md").read_text(encoding="utf-8")
    front, _body = fd.split_front_matter(text)
    assert front is not None
    return YAML(typ="safe").load(front)


def test_the_page_template_validates_its_fields_and_its_friction_block() -> None:
    front = _template_front_matter("signpost")
    assert (front["reader"], front["kind"]) == ("user", "signpost")
    assert list(_page_schema().iter_errors(front)) == []
    container = bs.load_backbone_schema(REPO, "container")
    result = bs.validate_container(front, container, wiring=bs.ContainerWiring())
    assert result.findings == ()
    # The page's reader is its own field, outside the container: no role block.
    assert set(front["pkit"]) == {"friction"}


@pytest.mark.parametrize("reader", ["User", "", 7, None, ["user"], "a reader"])
def test_the_page_schema_refuses_a_wrong_reader(reader: Any) -> None:
    assert not _page_schema().is_valid({"reader": reader, "kind": "signpost"})
