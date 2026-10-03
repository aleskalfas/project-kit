"""living-docs' places, the LDOC rule set, and the space and page templates (#1003).

The capability's first artefacts, each held to living-docs DEC-001:

- the **validator**, `pkit living-docs validate` — the `living-docs:spaces`
  member of `pkit validate` — over an adopter repository with the capability
  installed: one test per rule it applies (an out-of-root place without an
  assignment, a place enclosing a root, a record declared as a page, another
  component's place or held document, an entry point outside its space, a page's fields, the
  most specific place, a definition that does not inherit LDOC), and the
  readers each page's reader resolves against, named in its summary (reader
  resolution itself is `test_living_docs_points.py`'s);
- the **LDOC rule set** validating as a method rule set with its origins, and
  a space definition instantiated from the template inheriting it;
- the **page templates** — the signpost and the reference page — each
  validating: its own fields by the capability's schema, its friction block
  by the core's;
- **page formats** (RS-LDOC-004; #1267): a page's body against the structure
  its kind declares in `schemas/page-kinds.yaml` — a title missing, or written
  as something that is not read as one; a kind declaring no structure,
  reported and never failed; the severity the rule's status gives; a
  declaration that gives no reading, which is one error. What no shipped kind
  declares — a section out of order, fixed text, sections in any order — is
  tested on a declaration of the test's own, read from a file outside the
  repository: no test rewrites the declaration the capability ships. Then
  what a heading is, and each template following its kind's structure;
- **one home for discovery**: the capability's scripts read the places and
  their documents through `pkit friction artefacts` and carry no matcher,
  listing or place reader of their own (#1099; ADR-057 point 2).

The validator runs as a subprocess under this interpreter, as the backbone
runs it (its `--json` findings document); where `pkit validate` runs it, the
script's `uv run --script` shebang is pointed at this interpreter, and the
`pkit` it reads the places and the readers point through is the real CLI under
this interpreter (`pkit_on_path`), so no test reaches `uv` or the network.
project-kit's own configuration passing is in `test_self_host_documentation.py`.
"""

from __future__ import annotations

import ast
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType
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


def _install_component_with_place(
    repo: AdopterRepo, friction: Mapping[str, Any] | None = None
) -> None:
    """Another capability, declaring a place under the internal root — or, with
    `friction`, what that block says."""
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
                "friction": dict(friction or {"places": [{"location": "analysis", "path": "."}]}),
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


def test_a_document_another_component_holds_is_never_a_page_nor_unclassified(
    project: AdopterRepo,
) -> None:
    """A folder of held documents (COR-050 point 1) under the internal root: no place
    walks its files, and each is its owner's — counted "of another component",
    never an unclassified document, and never a page (DEC-001 point 1)."""
    _install_component_with_place(project, {"held": [{"location": "analysis", "path": "records"}]})
    record = "tech-docs/analysis/records/2026-10-01-run.md"
    project.write({record: "---\ndate: '2026-10-01'\n---\n\n# A run\n"})
    document = run(project)
    assert errors(document) == []
    assert "1 of another component" in document["summary"][3]
    assert "0 unclassified document(s)" in document["summary"][3]
    project.write({record: "---\ndate: '2026-10-01'\nreader: user\n---\n"})
    location, message = only_error(run(project))
    assert location == f"{record}:/reader"
    assert "is a document analysis-test holds in a folder it declares (COR-050 point 1)" in (
        message
    )


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


def test_a_page_left_unanchored_counts_unless_its_block_gives_an_accepted_reason(
    project: AdopterRepo,
) -> None:
    """DEC-001 point 8: onboarding leaves no page unanchored without an accepted reason —
    the reason the page's friction block gives for having no anchors, the core's
    `unanchored-because` (COR-050 point 1), read as the backbone reads it. Counted
    apart, never failed; an anchored page is in neither count."""
    reason = "A signpost: nothing it lists is its own."
    project.write(
        {
            "docs/sponsor.md": (
                "---\nreader: user\nkind: signpost\npkit:\n  friction:\n"
                f"    unanchored-because: '{reason}'\n---\n\n# Sponsor\n"
            ),
            "docs/anchored.md": (
                "---\nreader: user\nkind: signpost\npkit:\n  friction:\n"
                "    anchors: {path: [README.md]}\n---\n\n# Anchored\n"
            ),
        }
    )
    document = run(project)
    assert errors(document) == []
    (line,) = [line for line in document["summary"] if line.startswith("pages unanchored:")]
    assert line == (
        "pages unanchored: 3 without an accepted reason, 1 accepted with one "
        "(`unanchored-because`); onboarding leaves none without (DEC-001 point 8)."
    )

    human = subprocess.run(
        [sys.executable, str(project.root / SCRIPT)],
        cwd=project.root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert human.returncode == 0, human.stderr
    lines = human.stdout.splitlines()
    forgotten = lines.index(
        "page(s) unanchored without an accepted reason, for onboarding to anchor or accept (3):"
    )
    assert lines[forgotten + 1 : forgotten + 4] == [
        "  README.md",
        "  docs/guide.md",
        "  tech-docs/README.md",
    ]
    accepted = lines.index("page(s) accepted unanchored, each with its reason (1):")
    assert lines[accepted + 1] == f"  docs/sponsor.md — {reason}"


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


# --- the places, read through the backbone --------------------------------------------


def test_places_the_backbone_gives_no_reading_of_are_one_error_and_nothing_checked(
    project: AdopterRepo,
    pkit_on_path: Path,
    tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A backbone without the read command: the spaces cannot be told, which is
    one error — never a pass on no places."""
    old = tmp_path_factory.mktemp("old-pkit")
    (old / "pkit").write_text(
        '#!/bin/sh\nif [ "$1" = friction ]; then echo "Error: No such command." >&2; exit 2; fi\n'
        f'exec "{pkit_on_path}/pkit" "$@"\n',
        encoding="utf-8",
    )
    (old / "pkit").chmod(0o755)
    monkeypatch.setenv("PATH", f"{old}{os.pathsep}{os.environ['PATH']}")
    document = run(project)
    location, message = only_error(document)
    assert location == CONFIG
    assert message.startswith(
        "the documentation places cannot be read — `pkit friction artefacts --json` exited 2 "
        "without its document: Error: No such command. No space is checked until they can"
    )
    assert document["summary"][0] == "places unreadable: no space checked."


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


#: Every template but the space definition's is a page template, named for its kind:
#: a kind arrives with its template (RS-LDOC-004; the page schema's `kind`).
PAGE_TEMPLATES = sorted(
    path.stem for path in (CAPABILITY / "templates").glob("*.md") if path.stem != "space-definition"
)


def test_the_page_templates_are_the_signpost_and_the_reference_page() -> None:
    assert PAGE_TEMPLATES == ["reference", "signpost"]


@pytest.mark.parametrize("kind", PAGE_TEMPLATES)
def test_the_page_template_validates_its_fields_and_its_friction_block(kind: str) -> None:
    front = _template_front_matter(kind)
    assert (front["reader"], front["kind"]) == ("user", kind)
    assert list(_page_schema().iter_errors(front)) == []
    container = bs.load_backbone_schema(REPO, "container")
    result = bs.validate_container(front, container, wiring=bs.ContainerWiring())
    assert result.findings == ()
    # The page's reader is its own field, outside the container: no role block.
    assert set(front["pkit"]) == {"friction"}


@pytest.mark.parametrize("reader", ["User", "", 7, None, ["user"], "a reader"])
def test_the_page_schema_refuses_a_wrong_reader(reader: Any) -> None:
    assert not _page_schema().is_valid({"reader": reader, "kind": "signpost"})


# --- page formats: a page's body against its kind's structure (RS-LDOC-004; #1267) -------


def _library(name: str) -> ModuleType:
    """A module of the capability's script library, under a name of its own: the
    library is `_lib` in every capability, so it is never imported by that name."""
    spec = importlib.util.spec_from_file_location(
        f"living_docs_lib_{name}", CAPABILITY / "scripts" / "_lib" / f"{name}.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


formats = _library("formats")

PAGE_KINDS = CAPABILITY / "schemas" / "page-kinds.yaml"
PAGE_KINDS_PATH = f"{LD.as_posix()}/schemas/page-kinds.yaml"
LDOC = CAPABILITY / "rule-sets" / "ldoc.md"

#: What the validator says of a reference page, docs/ref.md, without its title.
LACKS_TITLE = (
    "docs/ref.md, a page of kind 'reference', lacks a title written as `# Title` at the start "
    "of a line: the structure its kind declares is a title written as `# Title` "
    f"({PAGE_KINDS_PATH}) — add it; a heading that is underlined, written in HTML, indented, "
    "empty or a template's unfilled `<placeholder>` is not read. A page may carry other "
    "sections besides (RS-LDOC-004)."
)

INSTALL, USE = {"level": 2, "text": "Install"}, {"level": 2, "text": "Use"}

#: Runs the validator's check with the kinds' declaration read from another file.
KINDS_DRIVER = """
import json, sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])
from _lib import spaces
from _lib.declarations import project_root

spaces.PAGE_KINDS = Path(sys.argv[2])
print(json.dumps(spaces.check(project_root()).document()))
"""


def _page(kind: str, body: str) -> str:
    return f"---\nreader: user\nkind: {kind}\n---\n\n{body}"


def _format_line(document: Mapping[str, Any]) -> str:
    (line,) = [line for line in document["summary"] if line.startswith("page formats")]
    return line


def _declaration(folder: Path, kinds: Mapping[str, Any]) -> Path:
    """A declaration of `kinds` in a file of its own, outside any repository."""
    path = folder / "page-kinds.yaml"
    path.write_text(_yaml({"schema_version": 1, "kinds": kinds}), encoding="utf-8")
    return path


def run_declaring(repo: AdopterRepo, declaration: Path) -> dict[str, Any]:
    """The validator's findings document with the kinds' structures read from
    `declaration`: what the adopter's copy of the capability ships stays as synced."""
    completed = subprocess.run(
        [sys.executable, "-c", KINDS_DRIVER, str(repo.root / LD / "scripts"), str(declaration)],
        cwd=repo.root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def test_a_page_that_follows_its_kind_s_structure_passes(project: AdopterRepo) -> None:
    """The fixture's signposts and a reference page each carry their title: no
    finding, and the summary counts each checked."""
    project.write({"docs/ref.md": _page("reference", "# Ref\n\nWhat it is.\n")})
    document = run(project)
    assert document["findings"] == []
    assert _format_line(document) == (
        "page formats (RS-LDOC-004, accepted): 4 page(s) checked against the structure their "
        f"kind declares in {PAGE_KINDS_PATH}, 0 departing from it; 0 page(s) not checked, of "
        "0 kind(s) that declare no structure."
    )


def test_a_page_lacking_a_section_fails_naming_the_page_its_kind_the_section_and_the_structure(
    project: AdopterRepo,
) -> None:
    project.write({"docs/ref.md": _page("reference", "What it is, and nothing more.\n")})
    document = run(project)
    assert [f["severity"] for f in document["findings"]] == ["error"]
    assert only_error(document) == ("docs/ref.md", LACKS_TITLE)
    assert ", 1 departing from it; " in _format_line(document)


@pytest.mark.parametrize(
    "body",
    [
        "- ```sh\n# install\n```\n",  # the only `#` line is code, fenced on a list item's line
        "- A step:\n\n  # Under a list item\n",  # indented
        "<!--\n# Commented out\n-->\n\nProse.\n",
        "#\n\nProse.\n",  # an empty heading
        "# <Surface>\n\nProse.\n",  # the template's placeholder, unfilled
        "Ref\n===\n\nProse.\n",  # an underlined (setext) title
        '<h1 align="center">Ref</h1>\n\nProse.\n',
    ],
)
def test_what_is_not_read_as_a_title_leaves_the_page_without_one(
    project: AdopterRepo, body: str
) -> None:
    project.write({"docs/ref.md": _page("reference", body)})
    assert only_error(run(project)) == ("docs/ref.md", LACKS_TITLE)


def test_a_title_after_code_fenced_under_a_list_item_is_read(project: AdopterRepo) -> None:
    """The fence a list item's line opens is closed by the indented fence under it,
    which opens nothing: the title below is read."""
    body = "- ```sh\n  # install\n  ```\n\n# Ref\n"
    project.write({"docs/ref.md": _page("reference", body)})
    assert run(project)["findings"] == []


def test_pkit_validate_fails_on_a_page_departing_from_its_kind_s_structure(
    project: AdopterRepo,
) -> None:
    project.write({"docs/ref.md": _page("reference", "What it is, and nothing more.\n")})
    result = CliRunner().invoke(
        main, ["--color", "never", "validate", "--only", "living-docs:spaces"]
    )
    assert result.exit_code == 1
    assert "docs/ref.md, a page of kind 'reference', lacks a title" in result.output


def test_a_kind_that_declares_no_structure_is_reported_with_its_pages_and_never_failed(
    project: AdopterRepo,
) -> None:
    """A kind the project adds, and a kind mistyped: each is one report naming the
    kind, the pages that name it and the kinds that are declared."""
    project.write(
        {
            "docs/notes.md": _page("tutorial", "Only prose, no heading at all.\n"),
            "docs/steps.md": _page("tutorial", "# Steps\n"),
            "docs/ref.md": _page("refrence", "# Ref\n"),
        }
    )
    document = run(project)
    assert errors(document) == []
    declared = f"{PAGE_KINDS_PATH} declares ['reference', 'signpost'] — name one of them where"
    closing = "a page is of that kind; a kind the project adds is reported, never failed"
    assert [(f["severity"], f["location"], f["message"]) for f in document["findings"]] == [
        (
            "report",
            "docs/ref.md:/kind",
            "kind 'refrence' declares no structure, so the body of the 1 page(s) that name it "
            f"is not checked: docs/ref.md. {declared} {closing} (DEC-001 point 3).",
        ),
        (
            "report",
            "docs/notes.md:/kind",
            "kind 'tutorial' declares no structure, so the body of the 2 page(s) that name it "
            f"is not checked: docs/notes.md, docs/steps.md. {declared} {closing} "
            "(DEC-001 point 3).",
        ),
    ]
    assert _format_line(document).endswith(
        "3 page(s) checked against the structure their kind declares in "
        f"{PAGE_KINDS_PATH}, 0 departing from it; 3 page(s) not checked, of 2 kind(s) that "
        "declare no structure."
    )
    result = CliRunner().invoke(
        main, ["--color", "never", "validate", "--only", "living-docs:spaces"]
    )
    assert result.exit_code == 0, result.output
    assert "kind 'tutorial' declares no structure" in result.output


def test_the_rule_the_check_names_is_an_accepted_rule_of_the_shipped_method() -> None:
    """The check applies one rule by its id (`FORMAT_RULE`): were the shipped LDOC to
    supersede or withdraw it, the check would stop while its successor binds."""
    front, _body = fd.split_front_matter(LDOC.read_text(encoding="utf-8"))
    assert front is not None
    rules = YAML(typ="safe").load(front)["rules"]
    assert rules[formats.FORMAT_RULE]["status"] == "accepted"


@pytest.mark.parametrize(
    ("status", "line"),
    [
        ("    status: proposed\n", "RS-LDOC-004 is proposed"),
        ("    status: superseded\n", "RS-LDOC-004 is superseded"),
        ("    status: withdrawn\n", "RS-LDOC-004 is withdrawn"),
        ("", "RS-LDOC-004 is proposed"),  # a rule without a status is proposed
    ],
)
def test_the_severity_is_the_one_the_rule_s_status_gives(
    project: AdopterRepo, status: str, line: str
) -> None:
    """An accepted RS-LDOC-004 binds, so a departure is an error (above); a rule of any
    other status binds nothing (COR-051 point 4), so no page's body is checked."""
    project.write({"docs/ref.md": _page("reference", "No title.\n")})
    assert errors(run(project)) != []
    ldoc = project.root / LD / "rule-sets" / "ldoc.md"
    accepted = "  RS-LDOC-004:\n    status: accepted\n"
    text = ldoc.read_text(encoding="utf-8")
    assert accepted in text
    ldoc.write_text(text.replace(accepted, f"  RS-LDOC-004:\n{status}"), encoding="utf-8")
    document = run(project)
    assert document["findings"] == []
    assert _format_line(document) == (
        f"page formats: not checked — {line}, so it binds nothing (COR-051 point 4)."
    )


def test_a_shared_method_without_the_rule_checks_no_body_and_says_so(
    project: AdopterRepo,
) -> None:
    """The rule set's own defects are the backbone's `rule-sets` findings; here the
    summary says the check did not run, and why."""
    project.write({"docs/ref.md": _page("reference", "No title.\n")})
    ldoc = project.root / LD / "rule-sets" / "ldoc.md"
    text = ldoc.read_text(encoding="utf-8")
    assert "  RS-LDOC-004:\n" in text
    ldoc.write_text(text.replace("  RS-LDOC-004:\n", "  RS-LDOC-014:\n"), encoding="utf-8")
    document = run(project)
    assert document["findings"] == []
    assert _format_line(document) == (
        f"page formats: not checked — {LD.as_posix()}/rule-sets/ldoc.md holds no RS-LDOC-004."
    )


@pytest.mark.parametrize(
    ("content", "why"),
    [
        (None, "the file cannot be read"),
        ("kinds: [unclosed\n", "the file is not YAML"),
        (
            "schema_version: 1\nkinds:\n  reference:\n    sections: []\n",
            "the file does not fit schemas/page-kinds.schema.json: at `/kinds/reference/sections`",
        ),
    ],
)
def test_a_declaration_that_gives_no_reading_is_one_error_and_no_body_is_checked(
    project: AdopterRepo,
    tmp_path_factory: pytest.TempPathFactory,
    content: str | None,
    why: str,
) -> None:
    declaration = tmp_path_factory.mktemp("kinds") / "page-kinds.yaml"
    if content is not None:
        declaration.write_text(content, encoding="utf-8")
    project.write({"docs/ref.md": _page("reference", "No title.\n")})
    document = run_declaring(project, declaration)
    assert [f["severity"] for f in document["findings"]] == ["error"]
    location, message = only_error(document)
    assert location == PAGE_KINDS_PATH
    assert message.startswith(f"structures unreadable — {why}")
    assert message.endswith(
        ". No page's body is checked until the page kinds' structures can be read: the file "
        "is living-docs's own, never the project's to edit — restore it as the capability "
        "ships it (DEC-001 point 3)."
    )
    assert _format_line(document) == (
        "page formats: structures unreadable, so no page's body is checked."
    )


def test_a_section_out_of_order_fails_naming_its_line_and_the_declared_order(
    project: AdopterRepo, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """No shipped kind declares two sections, so the declaration is one of the test's
    own, read in place of the shipped one — which reads as the validator reads it."""
    assert run_declaring(project, project.root / PAGE_KINDS_PATH) == run(project)
    declaration = _declaration(
        tmp_path_factory.mktemp("kinds"),
        {
            "guide": {"sections": [{"level": 1}, INSTALL, USE]},
            "faq": {"ordered": False, "sections": [INSTALL, USE]},
        },
    )
    project.write(
        {
            "docs/guide.md": _page("guide", "# Guide\n\n## Use\n\n## Install\n"),
            "docs/faq.md": _page("faq", "## Use\n\n## Install\n"),
        }
    )
    document = run_declaring(project, declaration)
    assert only_error(document) == (
        "docs/guide.md",
        "docs/guide.md, a page of kind 'guide', carries the section `## Use` out of order, at "
        "line 8: the structure its kind declares is a title written as `# Title`, then the "
        f"section `## Install`, then the section `## Use` ({PAGE_KINDS_PATH}) — move the "
        "section into that order. A page may carry other sections besides (RS-LDOC-004).",
    )
    # The guide and the list of questions are checked; the two signposts left are of a
    # kind this declaration does not list.
    assert "2 page(s) checked" in _format_line(document)
    assert "1 departing from it; 2 page(s) not checked, of 1 kind(s)" in _format_line(document)


# The declaration, read whole or not at all.


def test_a_declaration_reads_as_each_kind_s_sections_and_their_order(tmp_path: Path) -> None:
    structures = formats.read_structures(
        _declaration(
            tmp_path,
            {
                "guide": {"sections": [{"level": 1}, INSTALL, USE]},
                "faq": {"ordered": False, "sections": [INSTALL, USE]},
                "note": {"ordered": True, "sections": [{"level": 1}, {"level": 2}]},
            },
        )
    )
    install, use = formats.Section(2, "Install"), formats.Section(2, "Use")
    assert structures == {
        "guide": formats.Structure((formats.Section(1), install, use)),
        "faq": formats.Structure((install, use), ordered=False),
        "note": formats.Structure((formats.Section(1), formats.Section(2))),
    }
    assert structures["guide"].described() == (
        "a title written as `# Title`, then the section `## Install`, then the section `## Use`"
    )
    assert structures["faq"].described() == (
        "the section `## Install` and the section `## Use`, in any order"
    )
    assert structures["note"].described() == (
        "a title written as `# Title`, then a section written as `## Heading`"
    )


@pytest.mark.parametrize(
    ("content", "why"),
    [
        (None, "the file cannot be read"),
        ("kinds: [unclosed\n", "the file is not YAML ("),
        ("", "does not fit schemas/page-kinds.schema.json: at `/`"),
        ("kinds: {}\n", "'schema_version' is a required property"),
        ("schema_version: 2\nkinds: {}\n", "at `/schema_version`"),
        ("schema_version: 1\nkinds: []\n", "at `/kinds`"),
        ("schema_version: 1\nkinds:\n  Bad Kind:\n    sections: [{level: 1}]\n", "at `/kinds`"),
        ("schema_version: 1\nkinds:\n  guide: {}\n", "at `/kinds/guide`"),
        ("schema_version: 1\nkinds:\n  guide:\n    sections: []\n", "at `/kinds/guide/sections`"),
        (
            "schema_version: 1\nkinds:\n  guide:\n    sections: [{level: 7}]\n",
            "at `/kinds/guide/sections/0/level`",
        ),
        (
            "schema_version: 1\nkinds:\n  guide:\n    sections: [{level: true}]\n",
            "at `/kinds/guide/sections/0/level`",
        ),
        (
            "schema_version: 1\nkinds:\n  guide:\n    sections: [{level: 1, text: '  '}]\n",
            "at `/kinds/guide/sections/0/text`",
        ),
        (
            "schema_version: 1\nkinds:\n  guide:\n    sections: [{level: 1}]\n    order: yes\n",
            "at `/kinds/guide`",
        ),
    ],
)
def test_a_declaration_absent_unparsable_or_unfit_gives_no_reading(
    tmp_path: Path, content: str | None, why: str
) -> None:
    path = tmp_path / "page-kinds.yaml"
    if content is not None:
        path.write_text(content, encoding="utf-8")
    with pytest.raises(formats.Unreadable) as refused:
        formats.read_structures(path)
    assert why in str(refused.value)


# A body against a structure.


def test_a_section_the_body_lacks_is_missing(tmp_path: Path) -> None:
    structures = formats.read_structures(
        _declaration(
            tmp_path,
            {
                "note": {"sections": [{"level": 1}, {"level": 2}]},
                "guide": {"sections": [{"level": 1}, INSTALL, USE]},
            },
        )
    )
    assert formats.departures(formats.headings("# Note\n\nProse.\n"), structures["note"]) == [
        formats.Departure(formats.Section(2), formats.MISSING)
    ]
    assert formats.departures(formats.headings("# Guide\n\n## Use\n"), structures["guide"]) == [
        formats.Departure(formats.Section(2, "Install"), formats.MISSING)
    ]
    assert formats.departures(formats.headings("# Note\n\n## Part\n"), structures["note"]) == []


def test_sections_out_of_order_depart_only_where_the_kind_says_order_matters(
    tmp_path: Path,
) -> None:
    structures = formats.read_structures(
        _declaration(
            tmp_path,
            {
                "guide": {"sections": [{"level": 1}, INSTALL, USE]},
                "faq": {"ordered": False, "sections": [INSTALL, USE]},
            },
        )
    )
    swapped = formats.headings("# Guide\n\n## Use\n\n## Install\n")
    assert formats.departures(swapped, structures["guide"]) == [
        formats.Departure(formats.Section(2, "Use"), formats.OUT_OF_ORDER, 3)
    ]
    assert formats.departures(swapped, structures["faq"]) == []
    # In any order, each section is still owed.
    assert formats.departures(formats.headings("# Guide\n\n## Use\n"), structures["faq"]) == [
        formats.Departure(formats.Section(2, "Install"), formats.MISSING)
    ]


def test_a_section_s_text_compares_ignoring_case_space_and_trailing_punctuation() -> None:
    section = formats.Section(2, "Getting started")
    assert section.matches(formats.Heading(2, "getting   STARTED:", 1))
    assert section.matches(formats.Heading(2, "Getting started?", 1))
    assert not section.matches(formats.Heading(3, "Getting started", 1))
    assert not section.matches(formats.Heading(2, "Getting started fast", 1))


def test_a_section_the_writer_words_takes_a_heading_with_words_of_its_own() -> None:
    title = formats.Section(1)
    assert title.matches(formats.Heading(1, "Anything the writer says", 1))
    assert title.matches(formats.Heading(1, "The <kbd> element", 1))
    assert not title.matches(formats.Heading(1, "", 1))  # `#` alone
    assert not title.matches(formats.Heading(1, "<Surface>", 1))  # a placeholder, unfilled


def test_each_declared_section_takes_a_heading_of_its_own() -> None:
    two = formats.Structure((formats.Section(2), formats.Section(2)))
    one_h2 = [formats.Heading(2, "Only", 3)]
    assert formats.departures(one_h2, two) == [
        formats.Departure(formats.Section(2), formats.MISSING)
    ]
    # Text fixed first: the one `## Install` serves the section that names it.
    either = formats.Structure((formats.Section(2), formats.Section(2, "Install")), ordered=False)
    assert formats.departures([formats.Heading(2, "Install", 3)], either) == [
        formats.Departure(formats.Section(2), formats.MISSING)
    ]


# What a section is: a `#` heading at the start of a line, below the front matter,
# outside fenced code and outside an HTML comment.


def _headings(text: str) -> list[tuple[int, str, int]]:
    return [(h.level, h.text, h.line) for h in formats.headings(text)]


def test_a_heading_is_a_line_of_hashes_at_the_start_of_a_line_below_the_front_matter() -> None:
    text = (
        "---\n# a YAML comment, not a heading\nkind: reference\n---\n"  # lines 1-4
        "# Title ##\n"  # 5: the closing run of `#` is not text
        "#Not a heading\n"  # 6: no space after the `#`
        " ## One space in\n"  # 7: indented, as under a list item
        "    # four spaces: indented code\n"  # 8
        "####### seven\n"  # 9: more than six
        "## Closing# kept\n"  # 10
        "#\n"  # 11: an empty heading
        "Underlined\n==========\n"  # 12-13: a setext heading
        "<h2>In HTML</h2>\n"  # 14
        "> ## In a block quote\n"  # 15
        "- ## On a list item's line\n"  # 16
    )
    assert _headings(text) == [(1, "Title", 5), (2, "Closing# kept", 10), (1, "", 11)]
    assert _headings("# One\r\n\r\n## Two\r\n") == [(1, "One", 1), (2, "Two", 3)]


def test_a_line_inside_fenced_code_is_no_heading() -> None:
    text = (
        "```python\n# in code\n```\n"  # lines 1-3
        "~~~~\n# in code\n~~~\n# still in: a closing fence is as long as the opening\n~~~~\n"
        "``` `not` a fence\n"  # 9: a backtick fence's info has no backtick
        "## Read\n"  # 10
    )
    assert _headings(text) == [(2, "Read", 10)]
    assert _headings("```\n# never closed\n") == []


@pytest.mark.parametrize(
    ("opening", "inside", "closing"),
    [
        ("- ```sh", "  # install", "  ```"),  # under a list item, as a renderer indents it
        ("- ```sh", "# install", "```"),
        ("1. ~~~", "# install", "   ~~~"),
        ("> ```", "> # install", "> ```"),
        ("- > ```", "# install", "  > ```"),
        ("      ```", "# install", "```"),  # under a nested list item
    ],
)
def test_a_fence_opens_after_list_and_quote_markers_and_closes_at_any_indentation(
    opening: str, inside: str, closing: str
) -> None:
    """The closing fence closes the one that is open and opens none: what follows is read."""
    text = f"# Tool\n\n{opening}\n{inside}\n{closing}\n\n## Usage\n"
    assert _headings(text) == [(1, "Tool", 1), (2, "Usage", 7)]


def test_a_line_inside_an_html_comment_is_no_heading() -> None:
    text = (
        "<!--\n# Hidden\n-->\n"  # lines 1-3
        "# Shown\n"  # 4
        "<!-- closed on its own line -->\n"  # 5
        "## Also shown\n"  # 6
        "  <!-- opens\n## Hidden too\nand closes --> here\n"  # 7-9
        "### Last\n"  # 10
    )
    assert _headings(text) == [(1, "Shown", 4), (2, "Also shown", 6), (3, "Last", 10)]
    # Fenced code holds no comment: the `<!--` in it opens none.
    assert _headings("```html\n<!--\n```\n# Read\n") == [(1, "Read", 4)]


@pytest.mark.parametrize(
    "text",
    [
        "# No front matter\n\n## Part\n",
        "---\r\nkind: reference\r\n---\r\n\r\n# Title\r\n",
        "---\nkind: reference\n---\n\n# Title\n\n---\n\n## After a rule in the body\n",
        "---\n# never closed, so no front matter\nkind: reference\n",
        "--- \n# a YAML comment\n---\t\n# Title\n",
        "Prose first.\n\n---\n# Between two rules\n---\n",
    ],
)
def test_the_body_starts_where_the_backbone_s_front_matter_split_puts_it(text: str) -> None:
    """The capability's scripts import nothing of the backbone, so the reader finds
    the body itself; it finds the one the backbone's split gives."""
    _front, body = fd.split_front_matter(text)
    assert [(h.level, h.text) for h in formats.headings(text)] == [
        (h.level, h.text) for h in formats.headings(body)
    ]


# The one declaration: the templates follow it, and it is what the schema says.


def test_the_declared_kinds_are_the_page_templates_and_validate() -> None:
    data = YAML(typ="safe").load(PAGE_KINDS.read_text(encoding="utf-8"))
    schema = json.loads((CAPABILITY / "schemas" / "page-kinds.schema.json").read_text("utf-8"))
    Draft202012Validator.check_schema(schema)
    assert list(Draft202012Validator(schema).iter_errors(data)) == []
    assert sorted(formats.read_structures(PAGE_KINDS)) == sorted(data["kinds"]) == PAGE_TEMPLATES


@pytest.mark.parametrize("kind", PAGE_TEMPLATES)
def test_each_page_template_filled_in_follows_the_structure_its_kind_declares(kind: str) -> None:
    """A template is the starting shape a writer fills in: with its placeholders
    worded it satisfies its kind's structure, and left as shipped it lacks every
    section the writer words."""
    structure = formats.read_structures(PAGE_KINDS)[kind]
    template = (CAPABILITY / "templates" / f"{kind}.md").read_text(encoding="utf-8")
    filled = re.sub(r"<[^<>\n]+>", "words", template)
    assert formats.departures(formats.headings(filled), structure) == []
    assert formats.departures(formats.headings(template), structure) == [
        formats.Departure(section, formats.MISSING)
        for section in structure.sections
        if section.text is None
    ]


# --- one home for discovery (#1099; ADR-057 point 2) -------------------------------------

#: What re-reading the declarations, walking the places or matching an anchor would
#: take — each a pattern over a script's code (comments and docstrings left out)
#: and what it would mean. Where artefacts are is the backbone's discovery, read
#: through `pkit friction artefacts --json`, and what an anchor matches its
#: explanation's, `pkit friction explain --json`; a second computation drifts.
DISCOVERY_TOKENS = {
    r"\bfnmatch\b": "a glob matcher (fnmatch)",
    r"\b(?:import|from)\s+glob\b": "a glob matcher (glob)",
    r"\.r?glob\(": "a walk by glob",
    r"compile_glob|_segment_regex|pattern_matcher": "a ported glob matcher",
    r"['\"]\*\*['\"]": "`**`-matching code",
    r"\bos\.walk\b": "a walk of the working tree",
    r"ls-files": "a listing of the working tree",
    r"\.get\(\s*['\"]friction['\"]|\[\s*['\"]friction['\"]\s*\]": (
        "`friction.places` parsing (the friction settings)"
    ),
    r"\.get\(\s*['\"]locations['\"]|docs-locations": "a capability's locations resolved",
    r"manifest\.yaml": "the installed capabilities read",
    r":\([^)]*\bglob\b[^)]*\)|GIT_GLOB_PATHSPECS": "a pattern matched as git's glob pathspec",
}


def _code(text: str) -> str:
    """A script's code without its comments and docstrings."""
    tree = ast.parse(text)
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if (
            isinstance(body, list)
            and body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            body[0] = ast.Pass()
    return ast.unparse(tree)


def _discovery_tokens(text: str) -> list[str]:
    code = _code(text)
    return [meaning for token, meaning in DISCOVERY_TOKENS.items() if re.search(token, code)]


def test_the_guard_recognises_a_ported_discovery() -> None:
    """The guard is not vacuous: the reading this capability carried before #1099
    trips it, while prose about the same things does not."""
    ported = (
        '"""Places are read from `friction.places`, matched with fnmatch and `**`."""\n'
        "import fnmatch\n"
        "def _compile_glob(p):\n    return p.replace('**', '.*')\n"
        "places = config.get('friction', {}).get('places')\n"
        "listed = run(['git', 'ls-files'])\n"
    )
    assert _discovery_tokens(ported) == [
        "a glob matcher (fnmatch)",
        "a ported glob matcher",
        "`**`-matching code",
        "a listing of the working tree",
        "`friction.places` parsing (the friction settings)",
    ]
    assert _discovery_tokens('"""fnmatch, `**`, ls-files and manifest.yaml, in prose."""\n') == []


def test_the_capability_s_scripts_carry_no_discovery_of_their_own() -> None:
    """living-docs reads the places, the files each matches and their front matter
    through `pkit friction artefacts`; no script of it matches, lists or reads a
    place declaration itself."""
    scripts = sorted((CAPABILITY / "scripts").rglob("*.py"))
    assert scripts
    found = {
        path.relative_to(CAPABILITY).as_posix(): tokens
        for path in scripts
        if (tokens := _discovery_tokens(path.read_text(encoding="utf-8")))
    }
    assert found == {}
