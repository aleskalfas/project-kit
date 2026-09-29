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
  asks (criterion 3), and the friction pass, which enforces it, walks them all;
- the analysis location derives under the internal root (criterion 4);
- living-docs' own checks pass over this tree end to end: its validator, the
  shared method `LDOC` and both spaces' definitions inheriting it, and the
  friction pass over the roots it declares as places (#1003);
- every declared place is a page — its reader, a kind with a template, a
  friction block anchoring what it describes and a revalidation — and the
  code-to-doc mapping keeps no rule a page's anchors now carry (#1010).
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path, PurePosixPath

import pytest
from click.testing import CliRunner
from jsonschema import Draft202012Validator
from ruamel.yaml import YAML

from project_kit import config_validate as cv
from project_kit import docs_roots as dr
from project_kit import rule_sets as rs
from project_kit.cli import main
from project_kit.friction_discovery import (
    pattern_matcher,
    read_friction_settings,
    split_front_matter,
)
from project_kit.friction_validate import FrictionFindingKind, validate_friction
from project_kit.working_tree import working_tree

REPO = Path(__file__).resolve().parent.parent
LIVING_DOCS = REPO / ".pkit" / "capabilities" / "living-docs"
LIVING_DOCS_CONFIG = LIVING_DOCS / "project" / "config.yaml"
PM_CONFIG = REPO / ".pkit" / "capabilities" / "project-management" / "project" / "config.yaml"

#: The reader each space's pages are written for — the readers point's
#: defaults, one per mandatory space (living-docs DEC-001 point 7).
SPACE_READER = {"user": "user", "technical": "maintainer"}

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
    inside = lines.index("inside root        2 recorded location(s) inside the internal root:")
    assert lines[inside + 1] == "adr-records -> tech-docs/architecture/decisions"
    # living-docs' definitions location, recorded when the first space
    # definition was placed there (COR-049 point 5; DEC-001 point 2).
    assert lines[inside + 2] == "definitions (living-docs) -> tech-docs/living-docs"
    assert f"places             {len(read_friction_settings(REPO).places)} declared:" in lines
    for place in _project_places():
        assert place in lines, place
    # living-docs' default places — the roots — and its definitions (DEC-001 points 1 and 2).
    for place in ("docs/**", "tech-docs/**", "tech-docs/living-docs/rule-sets"):
        assert f"{place} (living-docs)" in lines, place


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


def test_the_friction_pass_refuses_none_of_the_places() -> None:
    """The backbone's check of the rule (COR-050 point 14) agrees: every declared
    place is walked, since `.pkit/` is the source here."""
    result = validate_friction(REPO)
    assert result.discovery.synced == ()
    assert [f.where for f in result.findings if f.kind is FrictionFindingKind.SYNCED_PLACE] == []


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


# --- living-docs over this tree (#1003) ---------------------------------------


def test_living_docs_validator_passes_over_this_tree() -> None:
    """The `living-docs:spaces` member of `pkit validate`, run as the backbone runs
    it (under this interpreter rather than `uv run --script`)."""
    completed = subprocess.run(
        [sys.executable, str(LIVING_DOCS / "scripts" / "validate.py"), "--json"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    document = json.loads(completed.stdout)
    assert [f for f in document["findings"] if f["severity"] == "error"] == []
    summary = document["summary"]
    assert summary[1].endswith("definition tech-docs/living-docs/rule-sets/user.md.")
    assert summary[2].endswith("definition tech-docs/living-docs/rule-sets/technical.md.")
    assert summary[4].startswith("reader resolution: dormant until the readers point")


def test_the_definitions_location_is_recorded_and_each_space_names_its_definition() -> None:
    assert dr.recorded_capability_locations(REPO, "living-docs") == {
        "definitions": "tech-docs/living-docs"
    }
    spaces = _living_docs_config()["spaces"]
    assert {space: entry["definition"] for space, entry in spaces.items()} == {
        "user": "tech-docs/living-docs/rule-sets/user.md",
        "technical": "tech-docs/living-docs/rule-sets/technical.md",
    }


def test_ldoc_and_both_space_definitions_validate_and_pin_it() -> None:
    result = rs.validate_rule_sets(REPO)
    assert result.errors == ()
    names = {rule_set.name: rule_set for rule_set in result.discovery.rule_sets}
    assert names["LDOC"].component == "living-docs"
    for name in ("USER", "TECH"):
        assert names[name].component is None
        assert [str(pin) for _index, pin in names[name].pins] == ["living-docs:LDOC@1"]
    assert all(check.problem is None for check in rs.pin_checks(result.discovery))


def test_the_friction_pass_over_the_declared_roots_has_no_error() -> None:
    """Declaring the roots as places makes every document under them an
    artefact; nothing there may fail the pass."""
    result = validate_friction(REPO)
    assert result.errors == ()


# --- the pages: every place anchored and revalidated (#1010) -----------------


def _front_matter(place: str) -> dict:
    front, _body = split_front_matter((REPO / place).read_text(encoding="utf-8"))
    assert front is not None, f"{place}: no front matter"
    return YAML(typ="safe").load(front)


def _friction(front: dict) -> dict:
    return (front.get("pkit") or {}).get("friction") or {}


@pytest.mark.parametrize("place", _project_places())
def test_every_declared_place_is_a_page_anchored_and_revalidated(place: str) -> None:
    """A place's document is a page (living-docs DEC-001 point 4): its reader —
    the one its space serves — and a kind whose template the capability ships
    (RS-LDOC-004), then a friction block that anchors what the page describes
    and records its revalidation (COR-050 points 2 and 3)."""
    front = _front_matter(place)
    schema = json.loads((LIVING_DOCS / "schemas" / "page.schema.json").read_text(encoding="utf-8"))
    assert list(Draft202012Validator(schema).iter_errors(front)) == [], place
    space = _living_docs_config()["places"][place]
    assert front["reader"] == SPACE_READER[space], place
    assert (LIVING_DOCS / "templates" / f"{front['kind']}.md").is_file(), place
    friction = _friction(front)
    anchors = friction.get("anchors") or {}
    assert any(anchors.values()), f"{place}: no anchor"
    revalidated = friction.get("revalidated") or {}
    assert revalidated.get("at") and revalidated.get("outcome") in ("updated", "unchanged"), place


def test_no_page_path_anchors_another_page() -> None:
    """A page grounded by another page names it as an artefact, never by path:
    a path anchor wakes on the other page's revalidation marker, which is not
    content, and would make every revalidation cascade (COR-050 point 5)."""
    places = _project_places()
    crossed = sorted(
        (place, anchor, other)
        for place in places
        for anchor in (_friction(_front_matter(place)).get("anchors") or {}).get("path", [])
        for other in places
        if other != place and pattern_matcher(anchor)(other)
    )
    assert crossed == []


def test_the_mapping_keeps_no_rule_a_page_anchor_carries() -> None:
    """The code-to-doc mapping's rules became page anchors (#1010): a rule whose
    document is a page that anchors part of the rule's code is converted, and
    stays out of the mapping — the page's friction holds the obligation now
    (project-management DEC-053). A rule may remain only for a document that
    is not a page."""
    mapping = YAML(typ="safe").load(PM_CONFIG.read_text(encoding="utf-8"))
    rules = (mapping.get("code_path_to_doc_mapping") or {}).get("rules") or []
    files = working_tree(REPO).files()
    pages = {place: _friction(_front_matter(place)) for place in _project_places()}
    carried = []
    for rule in rules:
        code = [rel for rel in files if pattern_matcher(rule["code"])(rel)]
        for doc in rule.get("docs", []):
            anchors = ((pages.get(doc) or {}).get("anchors") or {}).get("path", [])
            if any(pattern_matcher(anchor)(rel) for anchor in anchors for rel in code):
                carried.append((rule["code"], doc))
    assert carried == []


def test_the_declared_surface_is_what_the_retired_mapping_obliged() -> None:
    """The retired rules' code stays declared as the surface that ought to be
    described (COR-050 point 8), so what no page anchors to is still counted."""
    surface = [entry.value for entry in read_friction_settings(REPO).surface]
    assert surface == [
        "src/**",
        ".pkit/cli/**",
        ".pkit/capabilities/project-management/**",
        ".pkit/capabilities/evidence/**",
        ".pkit/capabilities/software-engineering/**",
        ".pkit/adapters/**",
    ]
