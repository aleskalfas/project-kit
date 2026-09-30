"""Tests for artefact discovery in the declared places and the validation
findings COR-050 point 12 assigns to validation (Task #988).

Built on the shared adopter-repository fixture: a real install, so the
container schema is read from the adopter's own `.pkit/schemas/backbone/`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from project_kit import connections, docs_roots
from project_kit import friction_discovery as fd
from project_kit import friction_validate as fv
from project_kit.cli import main
from project_kit.friction_check import CommitTree
from project_kit.manifest import (
    ComponentRegistryEntry,
    read_backbone_manifest,
    write_backbone_manifest,
)
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo

CONFIG = ".pkit/project/config.yaml"

VALID_DOCUMENT = """---
id: guide
title: A guide
pkit:
  friction:
    anchors:
      path: [src/cli/**]
      record: [COR-050]
    revalidated:
      at: 2026-10-02T09:40:12Z
      outcome: unchanged
      unchanged-because: the CLI surface did not move
      deferred:
        - anchor: {kind: path, value: src/cli/**}
          reason: waiting on the rename
---

The body.
"""

COLLECTION = """---
name: cmn
version: 1
RS-CMN-001:
  status: accepted
  pkit:
    friction:
      anchors: {path: [src/**]}
RS-CMN-002:
  status: draft
  pkit:
    friction:
      anchor: {path: [src/**]}
---
# Common rules

## RS-CMN-001 — Name things

Statement one.

### A sub-heading inside one

Still one.

## RS-CMN-002 — Keep it small

Statement two.
"""


def _config(places: list[str] | None = None, **friction: object) -> str:
    lines = ["name: adopter", "friction:"]
    if places is not None:
        lines.append(f"  places: {places!r}")
    for key, value in friction.items():
        lines.append(f"  {key}: {value!r}")
    return "\n".join(lines) + "\n"


def _document(artefact_id: str, **friction: object) -> str:
    block = "\n".join(f"    {k}: {v!r}" for k, v in friction.items())
    return f"---\nid: {artefact_id}\npkit:\n  friction:\n{block}\n---\n\nBody of {artefact_id}.\n"


@pytest.fixture
def adopter(make_adopter_repo: MakeAdopterRepo) -> AdopterRepo:
    return make_adopter_repo()


def _kinds(result: fv.FrictionValidation) -> list[fv.FrictionFindingKind]:
    return [f.kind for f in result.errors]


# --- discovery -------------------------------------------------------------


def test_document_with_valid_block_is_discovered_and_clean(adopter: AdopterRepo) -> None:
    adopter.write({CONFIG: _config(["docs"]), "docs/guide.md": VALID_DOCUMENT})
    result = fv.validate_friction(adopter.root)

    assert result.errors == (), [f.message for f in result.errors]
    assert not result.is_dormant
    (artefact,) = result.discovery.artefacts
    assert artefact.kind is fd.ArtefactKind.DOCUMENT
    assert artefact.id == "guide"
    assert artefact.path == "docs/guide.md"
    assert artefact.location == "docs/guide.md"
    assert artefact.anchors == {"path": ("src/cli/**",), "record": ("COR-050",)}
    assert artefact.revalidated is not None
    assert artefact.revalidated["at"] == "2026-10-02T09:40:12Z"  # as written, not a datetime
    assert artefact.deferrals == (
        fd.Deferral(index=0, anchor=fd.Anchor(kind="path", value="src/cli/**")),
    )
    assert artefact.body == "The body.\n"
    assert artefact.place.source == "project"


def test_collection_entries_are_artefacts_and_the_malformed_one_is_reported(
    adopter: AdopterRepo,
) -> None:
    adopter.write({CONFIG: _config(["docs"]), "docs/rules.md": COLLECTION})
    result = fv.validate_friction(adopter.root)

    first, second = result.discovery.artefacts
    assert (first.kind, first.id, first.location) == (
        fd.ArtefactKind.ENTRY,
        "RS-CMN-001",
        "docs/rules.md#RS-CMN-001",
    )
    assert first.anchors == {"path": ("src/**",)}
    assert first.body.startswith("## RS-CMN-001 — Name things")
    assert "Still one." in first.body and "Statement two." not in first.body
    assert second.body.startswith("## RS-CMN-002 — Keep it small")
    # The artefact's own fields stay outside the container (COR-050 point 1).
    assert first.carrier["status"] == "accepted"

    (finding,) = result.errors
    assert finding.kind is fv.FrictionFindingKind.MALFORMED_BLOCK
    assert finding.location == "docs/rules.md#RS-CMN-002"
    assert finding.pointer == "/pkit/friction"
    assert "'anchor' was unexpected" in finding.message


def test_front_matter_outside_declared_places_is_never_read(adopter: AdopterRepo) -> None:
    adopter.write(
        {
            CONFIG: _config(["docs"]),
            "docs/guide.md": VALID_DOCUMENT,
            "notes/stray.md": "---\npkit:\n  frictoin: {anchors: {path: [a]}}\n---\n",
            "README.md": "---\npkit: 3\n---\n",
        }
    )
    result = fv.validate_friction(adopter.root)
    assert [a.path for a in result.discovery.artefacts] == ["docs/guide.md"]
    assert result.errors == ()


def test_plain_yaml_in_a_place_is_not_a_document(adopter: AdopterRepo) -> None:
    adopter.write(
        {
            CONFIG: _config(["docs"]),
            "docs/guide.md": VALID_DOCUMENT,
            "docs/data.yaml": "pkit:\n  friction:\n    anchor: {path: [a]}\n",
            "docs/plain.md": "# No front matter\n\nJust prose.\n",
        }
    )
    result = fv.validate_friction(adopter.root)
    assert [a.path for a in result.discovery.artefacts] == ["docs/guide.md"]
    assert result.errors == ()


def test_glob_places_and_duplicate_matches_read_each_file_once(adopter: AdopterRepo) -> None:
    adopter.write(
        {
            CONFIG: _config(["docs/**/*.md", "docs"]),
            "docs/guide.md": VALID_DOCUMENT,
            "docs/deep/other.md": _document("other", anchors={"path": ["src/**"]}),
        }
    )
    result = fv.validate_friction(adopter.root)
    assert [a.path for a in result.discovery.artefacts] == ["docs/deep/other.md", "docs/guide.md"]
    assert all(a.place.pattern == "docs/**/*.md" for a in result.discovery.artefacts)


def test_a_place_ending_in_double_star_means_every_markdown_file_beneath(
    adopter: AdopterRepo,
) -> None:
    adopter.write(
        {
            CONFIG: _config(["docs/**"]),
            "docs/guide.md": VALID_DOCUMENT,
            "docs/deep/other.md": _document("other", anchors={"path": ["src/**"]}),
            "docs/deep/data.yaml": "pkit: {}\n",
        }
    )
    result = fv.validate_friction(adopter.root)
    assert [a.path for a in result.discovery.artefacts] == ["docs/deep/other.md", "docs/guide.md"]
    assert result.errors == ()


# --- capability places (the package schema's `{path, location?}`) ------------

EVIDENCE_PACKAGE = ".pkit/capabilities/evidence/package.yaml"


def _evidence_declares(adopter: AdopterRepo, blocks: str) -> None:
    """Append `docs` / `friction` blocks to the installed evidence capability's package."""
    package = adopter.root / EVIDENCE_PACKAGE
    package.write_text(package.read_text(encoding="utf-8") + blocks, encoding="utf-8")


def test_capability_places_are_read_in_the_package_schema_shape(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """With `location`, a place lies inside that `docs.locations` entry under its
    root (internal by default, or the user root); without one, it is
    repository-relative — never under a documentation root."""
    adopter = make_adopter_repo(capabilities=("evidence",))
    _evidence_declares(
        adopter,
        "docs:\n"
        "  locations:\n"
        "    runs: {path: evidence}\n"
        "    guides: {path: guides, root: user}\n"
        "friction:\n"
        "  places:\n"
        "    - {location: runs, path: '**/*.md'}\n"
        "    - {location: guides, path: '*.md', description: The user guides.}\n"
        "    - {path: notes}\n",
    )
    anchored = _document("x", anchors={"path": ["src/**"]})
    adopter.write(
        {
            CONFIG: "name: adopter\ndocs:\n  internal: tech-docs\n  user: handbook\n",
            "tech-docs/evidence/run.md": anchored.replace("id: x", "id: run"),
            "handbook/guides/guide.md": anchored.replace("id: x", "id: guide"),
            "notes/note.md": anchored.replace("id: x", "id: note"),
            "docs/evidence/default-root.md": anchored.replace("id: x", "id: default-root"),
            "tech-docs/notes/under-a-root.md": anchored.replace("id: x", "id: under-a-root"),
        }
    )
    result = fv.validate_friction(adopter.root)

    places = result.discovery.places
    assert [(p.pattern, p.declaration.value, p.declaration.pointer) for p in places] == [
        ("tech-docs/evidence/**/*.md", "**/*.md", "/friction/places/0"),
        ("handbook/guides/*.md", "*.md", "/friction/places/1"),
        ("notes", "notes", "/friction/places/2"),
    ]
    assert {p.source for p in places} == {"capability:evidence"}
    assert {p.declaration.file for p in places} == {EVIDENCE_PACKAGE}
    assert [a.id for a in result.discovery.artefacts] == ["run", "guide", "note"]
    assert result.errors == ()


def test_a_capability_place_in_another_shape_is_a_finding_and_is_not_walked(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """Plain text is not the schema's shape: every place discovery cannot read is
    an error at its entry, and only the well-formed place is walked."""
    adopter = make_adopter_repo(capabilities=("evidence",))
    _evidence_declares(
        adopter,
        "docs:\n"
        "  locations:\n"
        "    runs: {path: evidence}\n"
        "    legacy: evidence\n"
        "    shared: {path: shared, root: team}\n"
        "friction:\n"
        "  places:\n"
        "    - '**/*.md'\n"
        "    - {location: runs}\n"
        "    - {path: [notes]}\n"
        "    - {location: [runs], path: '**/*.md'}\n"
        "    - {location: spaces, path: '**/*.md'}\n"
        "    - {location: legacy, path: '**/*.md'}\n"
        "    - {location: shared, path: '**/*.md'}\n"
        "    - {location: runs, path: '**/*.md'}\n",
    )
    adopter.write({"docs/evidence/run.md": _document("run", anchors={"path": ["src/**"]})})
    result = fv.validate_friction(adopter.root)

    (place,) = result.discovery.places
    assert place.pattern == "docs/evidence/**/*.md"
    assert [a.id for a in result.discovery.artefacts] == ["run"]
    assert {f.kind for f in result.errors} == {fv.FrictionFindingKind.MALFORMED_PLACE}
    assert {f.location for f in result.errors} == {EVIDENCE_PACKAGE}
    reasons = {f.pointer: f.message.split(", so friction discovery")[0] for f in result.errors}
    assert reasons == {
        "/friction/places/0": "the place is text ('**/*.md'), not an object `{path, location?}`",
        "/friction/places/1": "the place has no `path`",
        "/friction/places/2": "the place's `path` is a list, not a path or glob",
        "/friction/places/3": "the place's `location` is a list, not a name from `docs.locations`",
        "/friction/places/4": (
            "the place names location 'spaces', which `docs.locations` does not declare "
            "(declared: ['legacy', 'runs', 'shared'])"
        ),
        "/friction/places/5": (
            "the place names location 'legacy', whose `docs.locations` entry is not an "
            "object `{path, root?}`"
        ),
        "/friction/places/6": (
            "the place names location 'shared', whose `docs.locations` entry names `root` "
            "'team', not one of ['internal', 'user']"
        ),
    }
    assert result.errors[0].message.endswith(
        "so friction discovery walks nothing under it; a capability place is "
        "`{path, location?}`, its `location` naming a `docs.locations` entry written "
        "`{path, root?}` (COR-050 point 7)."
    )


def test_a_malformed_capability_place_fails_validate_even_while_dormant(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """Nothing is walked, so the pass is dormant — yet the declaration it could not
    read is an error, and the count line says a place was not walked."""
    adopter = make_adopter_repo(capabilities=("evidence",))
    _evidence_declares(adopter, "friction:\n  places: {path: notes}\n")
    result = fv.validate_friction(adopter.root)

    assert result.is_dormant
    (finding,) = result.errors
    assert finding.kind is fv.FrictionFindingKind.MALFORMED_PLACE
    assert (finding.location, finding.pointer) == (EVIDENCE_PACKAGE, "/friction/places")
    assert finding.message.startswith("`friction.places` is a mapping, not a list of places")
    assert fv.summary_lines(result) == [
        "0 place(s), 0 artefact(s), none carrying the `pkit` container; dormant; "
        "1 capability place(s) not walked."
    ]

    cli = CliRunner().invoke(main, ["validate", "--no-refs"])
    assert cli.exit_code == 1, cli.output
    friction = cli.output.split("\n  friction\n")[1].split("\n  rule-sets\n")[0]
    assert f"error    {EVIDENCE_PACKAGE}:/friction/places" in friction


def test_a_capability_place_leaving_the_repository_through_a_link_is_a_finding(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """A place whose location, or whose own path, is a link out of the repository
    is reported where it is declared — and nothing beyond the link is read."""
    adopter = make_adopter_repo(capabilities=("evidence",))
    outside = adopter.root.parent / f"{adopter.root.name}-outside"  # beside the repository
    outside.mkdir()
    (outside / "stray.md").write_text(_document("stray", anchors={"path": ["a"]}))
    (adopter.root / "docs").mkdir()
    (adopter.root / "docs" / "evidence").symlink_to(outside, target_is_directory=True)
    (adopter.root / "notes").symlink_to(outside, target_is_directory=True)
    _evidence_declares(
        adopter,
        "docs:\n"
        "  locations:\n"
        "    runs: {path: evidence}\n"
        "friction:\n"
        "  places:\n"
        "    - {location: runs, path: '**/*.md'}\n"
        "    - {path: notes}\n",
    )
    result = fv.validate_friction(adopter.root)

    assert result.discovery.artefacts == ()
    assert [(f.kind, f.location, f.pointer) for f in result.errors] == [
        (fv.FrictionFindingKind.PLACE_OUTSIDE_REPOSITORY, EVIDENCE_PACKAGE, "/friction/places/0"),
        (fv.FrictionFindingKind.PLACE_OUTSIDE_REPOSITORY, EVIDENCE_PACKAGE, "/friction/places/1"),
    ]
    assert result.errors[0].message.startswith(
        "capability place '**/*.md' resolves to 'docs/evidence/**/*.md', which leaves the "
        "repository (absolute, climbing above the root, or resolving outside it through a "
        "link), so friction discovery walks nothing under it"
    )
    assert fv.summary_lines(result)[0].endswith("; dormant; 2 capability place(s) not walked.")


def test_a_capability_place_lies_inside_the_recorded_location_when_one_is_recorded(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """A location recorded in `docs-locations.yaml` wins over the declared one
    (COR-049 point 5): discovery walks where the project chose, and a recorded
    location places even a declaration the reading could not."""
    adopter = make_adopter_repo(capabilities=("evidence",))
    _evidence_declares(
        adopter,
        "docs:\n"
        "  locations:\n"
        "    runs: {path: evidence}\n"
        "    legacy: notes\n"
        "friction:\n"
        "  places:\n"
        "    - {location: runs, path: '**/*.md'}\n"
        "    - {location: legacy, path: '*.md'}\n",
    )
    anchored = _document("x", anchors={"path": ["src/**"]})
    adopter.write(
        {
            "docs/evidence/declared.md": anchored.replace("id: x", "id: declared"),
            "records/runs/recorded.md": anchored.replace("id: x", "id: recorded"),
            "records/notes/note.md": anchored.replace("id: x", "id: note"),
        }
    )
    docs_roots.record_location(adopter.root, "evidence", "runs", "records/runs")
    docs_roots.record_location(adopter.root, "evidence", "legacy", "records/notes")
    result = fv.validate_friction(adopter.root)

    assert [p.pattern for p in result.discovery.places] == [
        "records/runs/**/*.md",
        "records/notes/*.md",
    ]
    assert [a.id for a in result.discovery.artefacts] == ["recorded", "note"]
    assert result.errors == ()


def test_discovery_reads_the_recorded_location_of_the_state_it_is_given(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """The change check reads its base commit through a tree: the location
    recorded in that commit places the base's places, not the working tree's."""
    adopter = make_adopter_repo(capabilities=("evidence",))
    _evidence_declares(
        adopter,
        "docs:\n"
        "  locations:\n"
        "    runs: {path: evidence}\n"
        "friction:\n"
        "  places:\n"
        "    - {location: runs, path: '**/*.md'}\n",
    )
    docs_roots.record_location(adopter.root, "evidence", "runs", "records/runs")
    base = adopter.commit("record the runs location", None)
    recorded = docs_roots.capability_locations_path(adopter.root, "evidence")
    recorded.write_text("locations:\n  runs: archive/runs\n", encoding="utf-8")

    def patterns(tree: CommitTree | None = None) -> list[str]:
        return [p.resolved for p in fd.read_friction_settings(adopter.root, tree).places]

    assert patterns() == ["archive/runs/**/*.md"]
    assert patterns(CommitTree(adopter.root, base)) == ["records/runs/**/*.md"]


# --- synced places (COR-050 point 14, living-docs DEC-001 point 1) ------------
#
# A place is never a synced tree. Whether a path is a synced copy is the tree's
# ownership predicate's question — keyed on the capability's recorded origin and
# on the repository being the methodology's source, never on the path.

EVIDENCE_README = ".pkit/capabilities/evidence/README.md"


def _anchored(artefact_id: str) -> str:
    return _document(artefact_id, anchors={"path": ["src/**"]})


def _as_methodology_source(adopter: AdopterRepo) -> None:
    """Make the adopter the methodology's source repository, as the ownership
    tests simulate it: the package source beside the in-tree dispatcher it
    already has (ADR-059)."""
    assert (adopter.pkit / "cli" / "pkit").is_file()
    adopter.write({"src/project_kit/__init__.py": ""})


@pytest.mark.parametrize("place", [EVIDENCE_README, ".pkit/cli/README.md"])
def test_a_synced_copy_declared_as_a_place_is_refused_even_while_dormant(
    make_adopter_repo: MakeAdopterRepo, place: str
) -> None:
    """A kit-shipped capability's README, or a backbone area's, arrives in an
    adopter by sync: declared as a place it is an error at its declaration, and
    it is not walked — so the pass is dormant, and the error stands."""
    adopter = make_adopter_repo(capabilities=("evidence",))
    (evidence,) = [
        c for c in read_backbone_manifest(adopter.root).components if c.name == "evidence"
    ]
    assert evidence.origin == "kit-shipped"
    adopter.write({CONFIG: _config([place]), place: _anchored("copied")})
    result = fv.validate_friction(adopter.root)

    assert result.discovery.artefacts == ()
    assert [m.path for m in result.discovery.synced] == [place]
    assert result.is_dormant
    (finding,) = result.errors
    assert (finding.kind, finding.location, finding.pointer) == (
        fv.FrictionFindingKind.SYNCED_PLACE,
        CONFIG,
        "/friction/places/0",
    )
    assert finding.message == (
        f"place {place!r} is a synced copy — the methodology's sync writes it into this "
        f"repository, so friction discovery does not walk it; a place is never a synced "
        f"tree: narrow it to the project's own files or remove it (COR-050 point 14)."
    )
    assert fv.summary_lines(result) == [
        "1 place(s), 0 artefact(s), none carrying the `pkit` container; dormant; "
        "1 place(s) matching a synced copy."
    ]

    cli = CliRunner().invoke(main, ["validate", "--no-refs"])
    assert cli.exit_code == 1, cli.output
    friction = cli.output.split("\n  friction\n")[1].split("\n  rule-sets\n")[0]
    assert f"error    {CONFIG}:/friction/places/0" in friction


def test_a_capability_place_matching_a_synced_copy_is_reported_in_its_package(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    adopter = make_adopter_repo(capabilities=("evidence",))
    _evidence_declares(adopter, f"friction:\n  places:\n    - {{path: {EVIDENCE_README}}}\n")
    result = fv.validate_friction(adopter.root)

    (finding,) = result.errors
    assert (finding.kind, finding.location, finding.pointer) == (
        fv.FrictionFindingKind.SYNCED_PLACE,
        EVIDENCE_PACKAGE,
        "/friction/places/0",
    )
    assert finding.message.startswith(f"capability place {EVIDENCE_README!r} is a synced copy")


def test_a_place_in_the_methodology_source_is_not_a_synced_copy(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """Where the methodology is authored, its trees are the source a sync copies
    from: the same READMEs are places there, walked like any other."""
    adopter = make_adopter_repo(capabilities=("evidence",))
    _as_methodology_source(adopter)
    adopter.write(
        {
            CONFIG: _config([".pkit/cli/README.md", EVIDENCE_README]),
            ".pkit/cli/README.md": _anchored("cli"),
            EVIDENCE_README: _anchored("evidence"),
        }
    )
    result = fv.validate_friction(adopter.root)

    assert result.discovery.synced == ()
    assert [a.id for a in result.discovery.artefacts] == ["cli", "evidence"]
    assert result.errors == (), [f.message for f in result.errors]


def test_a_glob_matching_a_synced_copy_and_the_project_s_own_file_refuses_only_the_copy(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """One glob over a kit-shipped capability's subtree: its README and every
    other shipped file are synced copies, reported at the declaration and not
    walked; the `project/` tier inside it is the adopter's, and is walked."""
    adopter = make_adopter_repo(capabilities=("evidence",))
    own = ".pkit/capabilities/evidence/project/notes.md"
    place = ".pkit/capabilities/evidence/**/*.md"
    adopter.write(
        {CONFIG: _config([place]), EVIDENCE_README: _anchored("copied"), own: _anchored("own")}
    )
    result = fv.validate_friction(adopter.root)

    assert [a.path for a in result.discovery.artefacts] == [own]
    synced = [m.path for m in result.discovery.synced]
    assert EVIDENCE_README in synced and own not in synced
    assert len(synced) > 3  # the message names three and counts the rest
    (finding,) = result.errors
    assert (finding.kind, finding.location, finding.pointer) == (
        fv.FrictionFindingKind.SYNCED_PLACE,
        CONFIG,
        "/friction/places/0",
    )
    shown = ", ".join(repr(p) for p in synced[:3])
    assert finding.message.startswith(
        f"place {place!r} matches {len(synced)} synced copies: {shown} and {len(synced) - 3} "
        f"more — the methodology's sync writes them into this repository, so friction "
        f"discovery does not walk them;"
    )
    assert fv.summary_lines(result)[0].endswith(
        "0 report(s); 1 place(s) matching a synced copy."
    )


def test_without_the_tree_s_ownership_module_the_synced_check_is_reported_skipped(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """A tree that has not synced since the lifecycle area carried the module
    cannot tell a synced copy: every match is walked, and a report says why."""
    adopter = make_adopter_repo()
    (adopter.pkit / "lifecycle" / "ownership.py").unlink()
    place = ".pkit/cli/README.md"
    adopter.write({CONFIG: _config([place]), place: _anchored("cli")})
    result = fv.validate_friction(adopter.root)

    assert [a.id for a in result.discovery.artefacts] == ["cli"]
    assert result.errors == (), [f.message for f in result.errors]
    unavailable = fv.FrictionFindingKind.OWNERSHIP_UNAVAILABLE
    (report,) = [f for f in result.reports if f.kind is unavailable]
    assert report.location == ".pkit/lifecycle/ownership.py"
    assert report.message.endswith("every match is walked (run `pkit sync`).")


# --- capability surface (the package schema's repository-relative globs) ------


def test_a_capability_surface_is_repository_relative(make_adopter_repo: MakeAdopterRepo) -> None:
    """The package schema's `friction.surface` holds repository-relative paths
    or globs: read as written, never under a documentation location or root."""
    adopter = make_adopter_repo(capabilities=("evidence",))
    _evidence_declares(
        adopter,
        "docs:\n"
        "  locations:\n"
        "    runs: {path: evidence}\n"
        "friction:\n"
        "  surface: ['src/**', lib/core.py]\n",
    )
    adopter.write({CONFIG: "name: adopter\ndocs:\n  internal: tech-docs\n"})
    surface = fd.read_friction_settings(adopter.root).surface

    assert {(s.file, s.source) for s in surface} == {(EVIDENCE_PACKAGE, "capability:evidence")}
    assert [(s.value, s.resolved, s.pointer) for s in surface] == [
        ("src/**", "src/**", "/friction/surface/0"),
        ("lib/core.py", "lib/core.py", "/friction/surface/1"),
    ]
    assert fv.validate_friction(adopter.root).errors == ()


def test_a_capability_surface_entry_in_another_shape_is_a_finding(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    """An entry that is not a path is an error at its entry, never dropped
    silently; the entries that are paths are still read."""
    adopter = make_adopter_repo(capabilities=("evidence",))
    _evidence_declares(adopter, "friction:\n  surface: ['src/**', {path: lib}, 42, '']\n")
    result = fv.validate_friction(adopter.root)

    assert [s.resolved for s in result.discovery.settings.surface] == ["src/**"]
    assert [(f.kind, f.location, f.pointer) for f in result.errors] == [
        (fv.FrictionFindingKind.MALFORMED_SURFACE, EVIDENCE_PACKAGE, f"/friction/surface/{i}")
        for i in (1, 2, 3)
    ]
    assert [f.message.split(", so the uncovered")[0] for f in result.errors] == [
        "the surface entry is a mapping, not a path or glob",
        "the surface entry is int (42), not a path or glob",
        "the surface entry is text (''), not a path or glob",
    ]
    assert result.errors[0].message.endswith(
        "so the uncovered-surface measure reads nothing from it; a capability's "
        "`friction.surface` is a list of repository-relative paths or globs "
        "(COR-050 points 7 and 8)."
    )
    assert fv.summary_lines(result) == [
        "0 place(s), 0 artefact(s), none carrying the `pkit` container; dormant; "
        "3 capability surface entries not read."
    ]


def test_a_capability_surface_that_is_not_a_list_fails_validate_even_while_dormant(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    adopter = make_adopter_repo(capabilities=("evidence",))
    _evidence_declares(adopter, "friction:\n  surface: src/**\n")
    result = fv.validate_friction(adopter.root)

    assert result.is_dormant
    assert result.discovery.settings.surface == ()
    (finding,) = result.errors
    assert finding.kind is fv.FrictionFindingKind.MALFORMED_SURFACE
    assert (finding.location, finding.pointer) == (EVIDENCE_PACKAGE, "/friction/surface")
    assert finding.message.startswith("`friction.surface` is text ('src/**'), not a list of paths")
    assert fv.summary_lines(result) == [
        "0 place(s), 0 artefact(s), none carrying the `pkit` container; dormant; "
        "1 capability surface entry not read."
    ]

    cli = CliRunner().invoke(main, ["validate", "--no-refs"])
    assert cli.exit_code == 1, cli.output
    friction = cli.output.split("\n  friction\n")[1].split("\n  rule-sets\n")[0]
    assert f"error    {EVIDENCE_PACKAGE}:/friction/surface" in friction


# --- the findings validation owns -------------------------------------------


def test_dangling_deferral_is_an_error_naming_the_anchor(adopter: AdopterRepo) -> None:
    adopter.write(
        {
            CONFIG: _config(["docs"]),
            "docs/guide.md": _document(
                "guide",
                anchors={"path": ["src/**"]},
                revalidated={
                    "deferred": [
                        {"reason": "no anchor at all"},  # malformed: the block check reports it
                        {"anchor": {"kind": "path", "value": "lib/**"}, "reason": "later"},
                        {"anchor": {"kind": "record", "value": "COR-050"}, "reason": "later"},
                        {"anchor": {"kind": "path", "value": "src/**"}, "reason": "kept"},
                    ]
                },
            ),
        }
    )
    result = fv.validate_friction(adopter.root)

    dangling = [f for f in result.errors if f.kind is fv.FrictionFindingKind.DANGLING_DEFERRAL]
    assert len(dangling) == 2
    first, second = dangling
    # The pointer keeps the index as written: the malformed entry at 0 still counts.
    assert first.pointer == "/pkit/friction/revalidated/deferred/1/anchor"
    assert "path anchor 'lib/**'" in first.message and "'src/**'" in first.message
    assert second.pointer == "/pkit/friction/revalidated/deferred/2/anchor"
    assert "record anchor 'COR-050'" in second.message


def test_two_artefact_cycle_and_self_cycle_are_each_reported_once(adopter: AdopterRepo) -> None:
    adopter.write(
        {
            CONFIG: _config(["docs"]),
            "docs/a.md": _document("A", anchors={"artefact": ["B"]}),
            "docs/b.md": _document("B", anchors={"artefact": ["A"]}),
            "docs/c.md": _document("C", anchors={"artefact": ["C", "A"]}),
            "docs/d.md": _document("D", anchors={"artefact": ["A"]}),  # into the cycle, not in it
        }
    )
    result = fv.validate_friction(adopter.root)

    cycles = [f for f in result.errors if f.kind is fv.FrictionFindingKind.CYCLE]
    assert [f.location for f in cycles] == ["docs/a.md", "docs/c.md"]
    assert "A -> B -> A" in cycles[0].message
    assert "anchors to itself: C -> C" in cycles[1].message
    assert all(f.pointer == "/pkit/friction/anchors/artefact" for f in cycles)
    assert len(result.errors) == 2


def test_artefact_anchor_may_name_a_document_by_path_or_an_entry_by_id(
    adopter: AdopterRepo,
) -> None:
    adopter.write(
        {
            CONFIG: _config(["docs"]),
            "docs/a.md": _document("A", anchors={"artefact": ["RS-CMN-001"]}),
            "docs/rules.md": COLLECTION.replace(
                "anchors: {path: [src/**]}", "anchors: {artefact: [docs/a.md]}"
            ),
        }
    )
    result = fv.validate_friction(adopter.root)
    cycles = [f for f in result.errors if f.kind is fv.FrictionFindingKind.CYCLE]
    assert len(cycles) == 1
    assert "A -> RS-CMN-001 -> A" in cycles[0].message


def test_invalid_mode_is_the_configuration_pass_s_finding_and_reads_as_the_default(
    adopter: AdopterRepo,
) -> None:
    adopter.write({CONFIG: _config(["docs"], mode="enforce"), "docs/guide.md": VALID_DOCUMENT})
    result = fv.validate_friction(adopter.root)

    assert result.errors == ()  # the configuration pass owns the file and reports the enum
    assert result.discovery.settings.mode == "enforce"
    assert result.discovery.settings.mode_or_default == "warning"
    assert "mode warning" in fv.summary_lines(result)[0]


@pytest.mark.parametrize("mode", ["warning", "enforcing"])
def test_valid_modes_pass(adopter: AdopterRepo, mode: str) -> None:
    adopter.write({CONFIG: _config(mode=mode)})
    result = fv.validate_friction(adopter.root)
    assert result.errors == ()
    assert result.discovery.settings.mode_or_default == mode


def test_nothing_outside_the_repository_is_walked_or_read(adopter: AdopterRepo) -> None:
    """Places leaving the repository, and matches that resolve outside it through a
    link, are never read; the configuration pass reports the pattern, not this one."""
    outside = adopter.root.parent / f"{adopter.root.name}-outside"  # beside the repository
    (outside / "sub").mkdir(parents=True)
    (outside / "stray.md").write_text(_document("stray", anchors={"path": ["a"]}))
    (outside / "sub" / "deep.md").write_text(_document("deep", anchors={"path": ["a"]}))
    (adopter.root / "docs").mkdir()
    (adopter.root / "docs" / "linked").symlink_to(outside, target_is_directory=True)
    (adopter.root / "docs" / "alias.md").symlink_to(outside / "stray.md")
    adopter.write(
        {
            CONFIG: _config(
                [
                    "docs/**/*.md",  # never walks through the link docs/linked
                    "../sibling",
                    str(outside / "**"),
                    "docs/linked/**",
                    "docs/linked/sub/**",  # the nearest existing ancestor is the link
                ],
                surface=["/abs/src"],
                exclude=["docs/../../out"],
            ),
            "docs/guide.md": VALID_DOCUMENT,
        }
    )
    result = fv.validate_friction(adopter.root)

    assert [a.path for a in result.discovery.artefacts] == ["docs/guide.md"]
    assert result.errors == ()


def test_unparsable_front_matter_in_a_place_is_an_error(adopter: AdopterRepo) -> None:
    adopter.write(
        {
            CONFIG: _config(["docs"]),
            "docs/guide.md": VALID_DOCUMENT,
            "docs/broken.md": "---\npkit: [unclosed\n---\n",
        }
    )
    result = fv.validate_friction(adopter.root)
    (finding,) = result.errors
    assert finding.kind is fv.FrictionFindingKind.UNPARSABLE_FRONT_MATTER
    assert finding.location == "docs/broken.md"
    assert "'docs'" in finding.message
    assert "1 with unparsable front matter" in fv.summary_lines(result)[0]


def test_unparsable_front_matter_as_the_only_file_in_a_place_keeps_the_pass_awake(
    adopter: AdopterRepo,
) -> None:
    """A YAML typo in the only container-carrying file must not switch the check off."""
    adopter.write(
        {
            CONFIG: _config(["docs"]),
            "docs/broken.md": VALID_DOCUMENT.replace("anchors:", "anchors: ["),
        }
    )
    result = fv.validate_friction(adopter.root)

    assert not result.is_dormant
    assert result.discovery.artefacts == ()
    (finding,) = result.errors
    assert finding.kind is fv.FrictionFindingKind.UNPARSABLE_FRONT_MATTER
    assert finding.location == "docs/broken.md"
    assert fv.summary_lines(result)[0].startswith(
        "1 place(s), 0 artefact(s), 0 carrying the `pkit` container, 1 with unparsable "
        "front matter; mode warning; 1 error(s)"
    )

    cli = CliRunner().invoke(main, ["validate", "--no-refs"])
    assert cli.exit_code == 1, cli.output
    assert "docs/broken.md" in cli.output and "dormant" not in cli.output


# --- role blocks against the resolved wiring (COR-053 point 10) --------------

# An incubated capability providing `pkit::documentation`, whose one data point
# takes a string `last-run` and nothing else.
DOCS_PROVIDER = """schema_version: 1
component: {kind: capability, name: docs-a, version: 0.1.0}
description: Synthetic documentation provider.
requires_backbone: ">=0.0.0"
commands:
  publish: {script: scripts/publish.py, help: Publish.}
connections:
  roles: [pkit::documentation]
  extension-points:
    accepts:
      pkit::documentation:reading-evidence:
        schema_version: 1
        schema: reading-evidence.schema.json
        description: What readers found.
"""
READING_SCHEMA = {
    "type": "object",
    "required": ["last-run"],
    "properties": {"last-run": {"type": "string"}},
    "additionalProperties": False,
}


def _stage_documentation_provider(adopter: AdopterRepo) -> None:
    name = "docs-a"
    adopter.write(
        {
            f".pkit/capabilities/{name}/package.yaml": DOCS_PROVIDER,
            f".pkit/capabilities/{name}/scripts/publish.py": "",
            f".pkit/capabilities/{name}/schemas/reading-evidence.schema.json": json.dumps(
                READING_SCHEMA
            ),
        }
    )
    backbone = read_backbone_manifest(adopter.root)
    assert backbone is not None
    backbone.components.append(
        ComponentRegistryEntry(
            kind="capability",
            name=name,
            manifest=f".pkit/capabilities/{name}/project/manifest.yaml",
            origin="incubated-in-repo",
        )
    )
    write_backbone_manifest(adopter.root, backbone)


def _with_roles(**roles: str) -> str:
    """A document whose container carries one role block per keyword (YAML flow text)."""
    blocks = "\n".join(f"  {key}: {block}" for key, block in roles.items())
    return f"---\nid: guide\npkit:\n{blocks}\n---\n\nThe body.\n"


@pytest.fixture
def documented(adopter: AdopterRepo) -> AdopterRepo:
    """The adopter with the documentation provider installed and `docs` declared."""
    _stage_documentation_provider(adopter)
    adopter.write({CONFIG: _config(["docs"])})
    return adopter


def test_only_a_role_without_an_active_provider_is_orphaned(documented: AdopterRepo) -> None:
    """`documentation` has its provider and a compatible, valid point block: nothing
    is said of it. `analysis` has no provider: it alone is the orphan."""
    documented.write(
        {
            "docs/guide.md": _with_roles(
                documentation="{reading-evidence: {schema_version: 1, last-run: 2026-10-01}}",
                analysis="{glossary: {schema_version: 1}}",
            )
        }
    )
    result = fv.validate_friction(documented.root)

    assert result.errors == ()
    (report,) = result.reports
    assert report.kind is fv.FrictionFindingKind.CONTAINER_REPORT
    assert (report.location, report.pointer) == ("docs/guide.md", "/pkit/analysis")
    assert "no active provider" in report.message


def test_point_block_at_another_version_is_inert_and_not_validated(
    documented: AdopterRepo,
) -> None:
    """The body breaks the point schema, but at version 2 it is never read."""
    documented.write(
        {"docs/guide.md": _with_roles(documentation="{reading-evidence: {schema_version: 2, x: 5}}")}
    )
    result = fv.validate_friction(documented.root)

    assert result.errors == ()
    (report,) = result.reports
    assert report.pointer == "/pkit/documentation/reading-evidence"
    assert "defines 'pkit::documentation:reading-evidence' at version 1" in report.message
    assert "inert, body unvalidated" in report.message


def test_compatible_point_block_is_validated_by_the_provider_point_schema(
    documented: AdopterRepo,
) -> None:
    documented.write(
        {"docs/guide.md": _with_roles(documentation="{reading-evidence: {schema_version: 1, last-run: 5}}")}
    )
    result = fv.validate_friction(documented.root)

    (error,) = result.errors
    assert error.kind is fv.FrictionFindingKind.MALFORMED_BLOCK
    assert error.pointer == "/pkit/documentation/reading-evidence/last-run"
    assert "5 is not of type 'string'" in error.message
    assert result.reports == ()


def test_validate_resolves_the_wiring_once_for_every_member_that_reads_it(
    documented: AdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`connections`, `versions`, `friction` and `rule-sets` all read the wiring;
    one run of `pkit validate` resolves it once (ADR-057 point 2)."""
    documented.write(
        {"docs/guide.md": _with_roles(documentation="{reading-evidence: {schema_version: 2}}")}
    )
    calls: list[Path] = []
    resolve = connections.resolve_wiring

    def counting(target_root: Path) -> connections.Wiring:
        calls.append(target_root)
        return resolve(target_root)

    monkeypatch.setattr(connections, "resolve_wiring", counting)
    result = CliRunner().invoke(main, ["validate", "--no-refs"])

    assert len(calls) == 1, result.output
    friction = result.output.split("\n  friction\n")[1].split("\n  rule-sets\n")[0]
    assert "report   docs/guide.md:/pkit/documentation/reading-evidence" in friction


# --- dormancy and determinism ------------------------------------------------


def test_dormant_when_no_places_are_declared(adopter: AdopterRepo) -> None:
    adopter.write({"docs/guide.md": "---\npkit:\n  frictoin: 1\n---\n"})
    result = fv.validate_friction(adopter.root)

    assert result.is_dormant
    assert result.findings == ()
    assert fv.summary_lines(result) == ["no places declared; dormant."]


def test_dormant_when_no_artefact_carries_the_container(adopter: AdopterRepo) -> None:
    adopter.write(
        {
            CONFIG: _config(["docs"]),
            "docs/one.md": "---\ntitle: One\n---\n",
            "docs/two.md": "---\ntitle: Two\n---\n",
        }
    )
    result = fv.validate_friction(adopter.root)

    assert result.is_dormant
    assert len(result.discovery.artefacts) == 2
    assert result.findings == ()
    assert fv.summary_lines(result) == [
        "1 place(s), 2 artefact(s), none carrying the `pkit` container; dormant."
    ]


def test_results_are_deterministic_across_runs(adopter: AdopterRepo) -> None:
    adopter.write(
        {
            CONFIG: _config(["docs", "notes/*.md"]),
            "docs/z.md": _document("Z", anchors={"artefact": ["Y"]}),
            "docs/y.md": _document("Y", anchors={"artefact": ["Z"]}),
            "docs/rules.md": COLLECTION,
            "notes/n.md": _document(
                "N",
                anchors={"path": ["src/**"]},
                revalidated={
                    "deferred": [{"anchor": {"kind": "path", "value": "x"}, "reason": "r"}]
                },
            ),
        }
    )
    first = fv.validate_friction(adopter.root)
    second = fv.validate_friction(adopter.root)

    assert first.findings == second.findings
    assert [a.location for a in first.discovery.artefacts] == [
        "docs/rules.md#RS-CMN-001",
        "docs/rules.md#RS-CMN-002",
        "docs/y.md",
        "docs/z.md",
        "notes/n.md",
    ]
    assert _kinds(first) == [
        fv.FrictionFindingKind.MALFORMED_BLOCK,
        fv.FrictionFindingKind.DANGLING_DEFERRAL,
        fv.FrictionFindingKind.CYCLE,
    ]


# --- `pkit validate` ---------------------------------------------------------


def test_validate_command_prints_the_friction_section_and_fails_on_errors(
    adopter: AdopterRepo,
) -> None:
    adopter.write({CONFIG: _config(["docs"]), "docs/rules.md": COLLECTION})
    result = CliRunner().invoke(main, ["validate", "--no-refs"])

    assert result.exit_code == 1, result.output
    assert "1 place(s), 2 artefact(s), 2 carrying the `pkit` container" in result.output
    # The finding sits under its own heading; the members print in registry order.
    out = result.output
    friction = out.split("\n  friction\n")[1].split("\n  rule-sets\n")[0]
    assert "error    docs/rules.md#RS-CMN-002:/pkit/friction" in friction
    assert out.index("\n  configuration\n") < out.index("\n  packages\n") < out.index("\n  friction\n")


def test_validate_command_reports_settings_findings_once_under_configuration(
    adopter: AdopterRepo,
) -> None:
    adopter.write(
        {
            CONFIG: _config(["docs", "../sibling"], mode="loud"),
            "docs/guide.md": VALID_DOCUMENT,
        }
    )
    result = CliRunner().invoke(main, ["validate", "--no-refs"])

    assert result.exit_code == 1, result.output
    configuration = result.output.split("\n  configuration\n")[1].split("\n  packages\n")[0]
    assert configuration.count("/friction/mode") == 1
    assert configuration.count("/friction/places/1") == 1
    assert result.output.count("/friction/mode") == 1  # nowhere else
    assert fv.validate_friction(adopter.root).errors == ()


def test_validate_command_is_dormant_and_passes_on_a_fresh_install(adopter: AdopterRepo) -> None:
    result = CliRunner().invoke(main, ["validate", "--no-refs"])
    assert result.exit_code == 0, result.output
    assert "friction" in result.output
    assert "no places declared; dormant." in result.output
    assert "All checks passed." in result.output


# --- Markdown helpers --------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("---\na: 1\n---\nbody\n", ("a: 1\n", "body\n")),
        ("---\na: 1\n---\n\n\nbody\n", ("a: 1\n", "body\n")),
        ("---\na: 1\n", (None, "---\na: 1\n")),  # never closed
        ("--- \na: 1\n---\n", ("a: 1\n", "")),  # trailing space on the opening fence
        ("----\na: 1\n---\n", (None, "----\na: 1\n---\n")),  # not a fence
        ("no front matter\n", (None, "no front matter\n")),
    ],
)
def test_split_front_matter(text: str, expected: tuple[str | None, str]) -> None:
    assert fd.split_front_matter(text) == expected


def test_entry_section_runs_to_the_next_heading_of_equal_or_higher_level() -> None:
    body = "# Set\n\n## RS-1: One\n\ntext\n\n### RS-1 detail\n\nmore\n\n## RS-10 — Ten\n\nten\n"
    assert fd.entry_section(body, "RS-1") == "## RS-1: One\n\ntext\n\n### RS-1 detail\n\nmore\n"
    assert fd.entry_section(body, "RS-10") == "## RS-10 — Ten\n\nten\n"
    assert fd.entry_section(body, "RS-2") == ""


def test_entry_section_takes_the_id_as_a_whole_token() -> None:
    """Two hyphenated ids sharing a prefix: the shorter one's section is never the longer's,
    whichever comes first."""
    body = (
        "## uc-login-sso — Sign in with SSO\n\nsso\n\n"
        "## uc-login.v2 — Sign in, again\n\nagain\n\n"
        "## uc-login — Sign in\n\nlogin\n\n"
        "## uc-login: the details\n\ndetails\n"
    )
    assert fd.entry_section(body, "uc-login") == "## uc-login — Sign in\n\nlogin\n"
    assert fd.entry_section(body, "uc-login-sso") == "## uc-login-sso — Sign in with SSO\n\nsso\n"
    assert fd.entry_section(body, "uc-login.v2") == "## uc-login.v2 — Sign in, again\n\nagain\n"
    assert fd.entry_section(body, "uc-log") == ""
    # Punctuation that continues no id ends it, as the end of the heading does.
    assert fd.entry_section("## uc-login: Sign in\n\ntext\n", "uc-login") == (
        "## uc-login: Sign in\n\ntext\n"
    )
    assert fd.entry_section("## uc-login.\n\ntext\n", "uc-login") == "## uc-login.\n\ntext\n"


def test_is_inside_repository(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "docs").mkdir()
    (root / "docs" / "linked").symlink_to(outside, target_is_directory=True)
    (root / "docs" / "inner").symlink_to(root / "docs", target_is_directory=True)

    assert fd.is_inside_repository(root, "docs/**/*.md")
    assert fd.is_inside_repository(root, "docs/../src")
    assert fd.is_inside_repository(root, "docs/inner/**")  # a link staying inside
    assert fd.is_inside_repository(root, "not/yet/created/**")
    assert not fd.is_inside_repository(root, "../docs")
    assert not fd.is_inside_repository(root, "docs/../../src")
    assert not fd.is_inside_repository(root, "/etc/**")
    assert not fd.is_inside_repository(root, "")
    assert not fd.is_inside_repository(root, "docs/linked/**")
    # `sub` does not exist: the nearest existing ancestor is the link out.
    assert not fd.is_inside_repository(root, "docs/linked/sub/**")


def test_a_glob_with_star_star_inside_a_segment_reads_as_on_python_3_13_and_never_raises(
    make_adopter_repo,
) -> None:
    """`docs/**.md` is rejected by `Path.glob` before Python 3.13; the walk matches
    it over the working tree's listing, as pathlib 3.13 reads it, on every
    interpreter — and never crashes `pkit validate`."""
    from project_kit import friction_discovery

    repo = make_adopter_repo()
    root = repo.root
    (root / "docs").mkdir(exist_ok=True)
    (root / "docs" / "page.md").write_text("---\npkit: {friction: {anchors: {path: [src]}}}\n---\n# p\n")
    place = friction_discovery.Place(
        pattern="docs/**.md",
        declaration=friction_discovery.SettingsPath(
            value="docs/**.md", resolved=root / "docs", file=root / ".pkit/project/config.yaml",
            pointer="/friction/places/0", source="project",
        ),
    )
    files = friction_discovery.files_in_place(root, place)
    assert files == [root / "docs" / "page.md"]
