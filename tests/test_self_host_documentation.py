"""project-kit's own documentation declaration (ADR-055, Task #1007).

project-kit is the first adopter of living-docs, and its declaration is data
in two files: the backbone configuration (`docs` roots, `friction` places and
exclusions) and living-docs' project configuration (entry points, the space
each place belongs to). These tests hold that data to the records it
realises, over the real repository:

- the configuration validates with both roots and every declared place, and
  the status report shows them (acceptance criterion 1);
- the `.pkit/` READMEs declared are exactly the adopter-facing ones — every
  README under `.pkit/` is either a place or named here with the reason it is
  not, so a new one cannot land unclassified (criterion 2);
- no declared place is a synced copy, which is what living-docs' place rule
  asks (criterion 3);
- the analysis location derives under the internal root (criterion 4).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path, PurePosixPath

import pytest
from click.testing import CliRunner
from ruamel.yaml import YAML

from project_kit import config_validate as cv
from project_kit import docs_roots as dr
from project_kit.cli import main
from project_kit.friction_discovery import read_friction_settings

REPO = Path(__file__).resolve().parent.parent
LIVING_DOCS_CONFIG = REPO / ".pkit" / "capabilities" / "living-docs" / "project" / "config.yaml"

# Every README under `.pkit/` that is *not* a place, with the reason ADR-055
# point 3's principle gives: a README an adopter reads in order to use an area,
# capability or adapter is a page; a maintainer-facing one is not.
NOT_PLACES: dict[str, str] = {
    ".pkit/lifecycle/templates/README.md": "maintainer-facing: the stamp templates",
    ".pkit/migrations/backbone/README.md": "maintainer-facing: the migration scripts",
    ".pkit/capabilities/project-management/migrations/README.md": (
        "maintainer-facing: the capability's migration scripts"
    ),
}


def _ownership():
    path = REPO / ".pkit" / "lifecycle" / "ownership.py"
    spec = importlib.util.spec_from_file_location("pkit_ownership_self_host", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _project_places() -> list[str]:
    return [p.value for p in read_friction_settings(REPO).places if p.source == "project"]


def _living_docs_config() -> dict:
    return YAML(typ="safe").load(LIVING_DOCS_CONFIG.read_text(encoding="utf-8"))


# --- criterion 1: the configuration and the status report --------------------


def test_the_configuration_declares_both_roots_and_validates() -> None:
    roots = dr.resolve_roots(REPO)
    assert (roots.user, roots.user_source) == (Path("docs"), dr.Source.EXPLICIT)
    assert (roots.internal, roots.internal_source) == (Path("tech-docs"), dr.Source.EXPLICIT)
    report = cv.run_configuration_pass(REPO)
    assert report.errors == ()
    # `docs/` holds no user page yet: COR-049 point 7 makes that a warning only.
    assert [f.path for f in report.findings] in ([], ["/docs/user"])


def test_every_declared_place_is_a_file_outside_both_roots() -> None:
    roots = dr.resolve_roots(REPO)
    places = _project_places()
    assert places
    for place in places:
        assert (REPO / place).is_file(), place
        # The roots are living-docs' default places, never declared as project
        # places (living-docs DEC-001 point 1: a place enclosing a root is refused).
        assert not dr.is_within(place, roots.user), place
        assert not dr.is_within(place, roots.internal), place


def test_the_status_report_shows_roots_places_and_the_records_inside_the_internal_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(REPO)
    monkeypatch.setenv("PKIT_SOURCE_BIN", "/fake/pkit")
    result = CliRunner().invoke(main, ["--color", "never", "status"])
    assert result.exit_code == 0, result.output
    lines = [line.strip() for line in result.output.splitlines()]
    assert "user root          docs/   (explicit)" in lines
    assert "internal root      tech-docs/   (explicit)" in lines
    inside = lines.index("inside root        1 recorded location(s) inside the internal root:")
    assert lines[inside + 1] == "adr-records -> tech-docs/architecture/decisions"
    assert f"places             {len(_project_places())} declared:" in lines
    for place in _project_places():
        assert place in lines, place


# --- criterion 2: exactly the adopter-facing `.pkit/` READMEs ----------------


def test_every_pkit_readme_is_a_place_or_named_as_not_one() -> None:
    declared = {p for p in _project_places() if p.startswith(".pkit/")}
    on_disk = {
        path.relative_to(REPO).as_posix()
        for path in (REPO / ".pkit").rglob("README.md")
        # A `project/` tier is the project's own content, not a shipped README.
        if "project" not in PurePosixPath(path.relative_to(REPO / ".pkit").as_posix()).parts
    }
    unclassified = sorted(on_disk - declared - NOT_PLACES.keys())
    assert unclassified == [], (
        f"{unclassified}: a README under .pkit/ is either a place of the user space — "
        "an adopter reads it to use an area, capability or adapter (ADR-055 point 3) — "
        "and listed in `friction.places` of .pkit/project/config.yaml and assigned in "
        ".pkit/capabilities/living-docs/project/config.yaml, or maintainer-facing and "
        "named in NOT_PLACES here with the reason."
    )
    assert declared & NOT_PLACES.keys() == set()
    assert (declared | NOT_PLACES.keys()) <= on_disk


# --- criterion 3: the synced-copy rule ---------------------------------------


def test_no_declared_place_is_a_synced_copy() -> None:
    """living-docs refuses a synced copy as a place, keyed on origin (DEC-001 point 1).

    project-kit is the methodology's source, so its `.pkit/` READMEs are the
    originals a sync copies from — places here, refused in an adopter.
    """
    own = _ownership()
    assert own.is_methodology_source(REPO) is True
    assert [p for p in _project_places() if own.is_synced_copy(REPO, p)] == []


def test_every_place_is_assigned_to_one_declared_space_with_its_entry_point() -> None:
    """Every place here lies outside both roots, so each is assigned (DEC-001 point 1)."""
    config = _living_docs_config()
    spaces = config["spaces"]
    assert set(spaces) == {"user", "technical"}
    assignments = config["places"]
    assert set(assignments) == set(_project_places())
    assert set(assignments.values()) <= set(spaces)
    for space, entry in spaces.items():
        entry_point = entry["entry-point"]
        assert assignments.get(entry_point) == space, (space, entry_point)
    # the technical space outside its root: the contributor guide (its entry
    # point until tech-docs/README.md exists) and the release guide, both
    # maintainer documentation per COR-049
    assert {p for p, s in assignments.items() if s == "technical"} == {
        "CONTRIBUTING.md",
        ".pkit/release/README.md",
    }


# --- criterion 4: the analysis location --------------------------------------


def test_the_analysis_location_derives_to_tech_docs_analysis() -> None:
    """software-analysis keeps its artefacts at the `analysis` sub-path of the
    internal root (its DEC-001, "Location"; ADR-055 point 4)."""
    internal = dr.resolve_roots(REPO).internal
    location = dr.derive_location(internal, "analysis", subpaths={"analysis": "analysis"})
    assert location == dr.Location(Path("tech-docs/analysis"), dr.Source.DERIVED)
