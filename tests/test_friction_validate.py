"""Tests for artefact discovery in the declared places and the validation
findings COR-050 point 12 assigns to validation (Task #988).

Built on the shared adopter-repository fixture: a real install, so the
container schema is read from the adopter's own `.pkit/schemas/backbone/`.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from project_kit import friction_discovery as fd
from project_kit import friction_validate as fv
from project_kit.cli import main
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
    assert artefact.deferrals == (fd.Anchor(kind="path", value="src/cli/**"),)
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


def test_capability_places_resolve_under_its_locations_and_the_internal_root(
    make_adopter_repo: MakeAdopterRepo,
) -> None:
    adopter = make_adopter_repo(capabilities=("evidence",))
    package = adopter.pkit / "capabilities" / "evidence" / "package.yaml"
    package.write_text(
        package.read_text(encoding="utf-8")
        + "docs:\n  locations: [evidence]\nfriction:\n  places: ['**/*.md']\n",
        encoding="utf-8",
    )
    adopter.write(
        {
            CONFIG: "name: adopter\ndocs:\n  internal: tech-docs\n",
            "tech-docs/evidence/run.md": _document("run", anchors={"path": ["src/**"]}),
            "docs/evidence/ignored.md": _document("ignored", anchors={"path": ["src/**"]}),
        }
    )
    result = fv.validate_friction(adopter.root)

    (place,) = result.discovery.places
    assert place.pattern == "tech-docs/evidence/**/*.md"
    assert place.source == "capability:evidence"
    assert place.declaration.file == ".pkit/capabilities/evidence/package.yaml"
    assert [a.path for a in result.discovery.artefacts] == ["tech-docs/evidence/run.md"]
    assert result.errors == ()


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
                        {"anchor": {"kind": "path", "value": "lib/**"}, "reason": "later"},
                        {"anchor": {"kind": "record", "value": "COR-050"}, "reason": "later"},
                        {"anchor": {"kind": "path", "value": "src/**"}, "reason": "kept"},
                    ]
                },
            ),
        }
    )
    result = fv.validate_friction(adopter.root)

    assert _kinds(result) == [fv.FrictionFindingKind.DANGLING_DEFERRAL] * 2
    first, second = result.errors
    assert first.pointer == "/pkit/friction/revalidated/deferred/0/anchor"
    assert "path anchor 'lib/**'" in first.message and "'src/**'" in first.message
    assert second.pointer == "/pkit/friction/revalidated/deferred/1/anchor"
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


def test_invalid_mode_is_an_error_even_when_dormant(adopter: AdopterRepo) -> None:
    adopter.write({CONFIG: _config(mode="enforce")})
    result = fv.validate_friction(adopter.root)

    assert result.is_dormant
    (finding,) = result.errors
    assert finding.kind is fv.FrictionFindingKind.INVALID_MODE
    assert (finding.location, finding.pointer) == (CONFIG, "/friction/mode")
    assert "'enforce'" in finding.message and "'enforcing'" in finding.message
    assert result.discovery.settings.mode_or_default == "warning"


@pytest.mark.parametrize("mode", ["warning", "enforcing"])
def test_valid_modes_pass(adopter: AdopterRepo, mode: str) -> None:
    adopter.write({CONFIG: _config(mode=mode)})
    result = fv.validate_friction(adopter.root)
    assert result.errors == ()
    assert result.discovery.settings.mode_or_default == mode


def test_settings_paths_outside_the_repository_are_errors(adopter: AdopterRepo) -> None:
    outside = adopter.root.parent / "elsewhere"
    outside.mkdir()
    (adopter.root / "docs").mkdir()
    (adopter.root / "docs" / "linked").symlink_to(outside, target_is_directory=True)
    adopter.write(
        {
            CONFIG: _config(
                ["docs", "../sibling", str(outside / "**"), "docs/linked/**"],
                surface=["src/**", "/abs/src"],
                exclude=["vendor/**", "docs/../../out"],
            ),
        }
    )
    result = fv.validate_friction(adopter.root)

    assert all(f.kind is fv.FrictionFindingKind.PATH_OUTSIDE_REPOSITORY for f in result.errors)
    assert [f.pointer for f in result.errors] == [
        "/friction/places/1",
        "/friction/places/2",
        "/friction/places/3",  # a link out of the repository, judged after resolving
        "/friction/surface/1",
        "/friction/exclude/1",
    ]
    assert all(f.location == CONFIG for f in result.errors)


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
    adopter.write(
        {
            CONFIG: _config(["docs"], mode="loud"),
            "docs/guide.md": VALID_DOCUMENT,
        }
    )
    result = CliRunner().invoke(main, ["validate", "--no-refs"])

    assert result.exit_code == 1, result.output
    assert "friction" in result.output
    assert "1 place(s), 1 artefact(s), 1 carrying the `pkit` container" in result.output
    assert f"{CONFIG} /friction/mode" in result.output
    assert "friction.mode 'loud'" in result.output


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


def test_is_inside_repository(tmp_path: Path) -> None:
    assert fd.is_inside_repository(tmp_path, "docs/**/*.md")
    assert fd.is_inside_repository(tmp_path, "docs/../src")
    assert not fd.is_inside_repository(tmp_path, "../docs")
    assert not fd.is_inside_repository(tmp_path, "docs/../../src")
    assert not fd.is_inside_repository(tmp_path, "/etc/**")
    assert not fd.is_inside_repository(tmp_path, "")
