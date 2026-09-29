"""Tests for the objective changeset + changelog format lint (#478).

Covers each objective check (pass on valid, fail on the specific invalid
input) — the floor field's value and carrier among them — the escape hatch,
and a dogfood check that the live repo's pending changesets + CHANGELOG.md
pass. Deliberately does *not* test plain-language / jargon judgment — that is
out of the objective subset by design."""

from __future__ import annotations

from pathlib import Path

import pytest

from project_kit import release
from project_kit.changesets import Changeset, Component, discover_components

REPO_ROOT = Path(__file__).resolve().parent.parent


def _cs(
    body: str = "Add the release format lint.",
    *,
    segment: str = "minor",
    category: str | None = None,
    name: str = "backbone-minor-x.yaml",
) -> Changeset:
    return Changeset(
        component="backbone",
        segment=segment,
        note=body,
        path=Path(name),
        category=category,
    )


# --- Check 1: changeset category enum ------------------------------------


def test_known_category_passes() -> None:
    assert release.lint_changeset(_cs(category="Added")) == []


def test_unknown_category_fails() -> None:
    violations = release.lint_changeset(_cs(category="Enhancements"))
    assert any("unknown category" in v.message for v in violations)


def test_absent_category_is_fine() -> None:
    assert release.lint_changeset(_cs(category=None)) == []


# --- Check 2: changeset body ---------------------------------------------


def test_well_formed_body_passes() -> None:
    assert release.lint_changeset(_cs("Ship the format lint.")) == []


def test_empty_body_fails() -> None:
    violations = release.lint_changeset(_cs(""))
    assert any("body is empty" in v.message for v in violations)


def test_body_that_is_only_a_bare_pr_ref_fails() -> None:
    violations = release.lint_changeset(_cs("#478"))
    assert any("bare reference" in v.message for v in violations)


def test_body_that_is_only_a_bare_record_ref_fails() -> None:
    for ref in ("ADR-013", "DEC-001", "COR-010"):
        violations = release.lint_changeset(_cs(ref))
        assert any("bare reference" in v.message for v in violations), ref


def test_body_that_is_only_a_bare_url_fails() -> None:
    violations = release.lint_changeset(_cs("https://example.com/pull/478"))
    assert any("bare reference" in v.message for v in violations)


def test_body_mentioning_a_ref_in_a_sentence_passes() -> None:
    # A reference *inside* a real sentence is not a bare-reference-only body.
    assert release.lint_changeset(_cs("Fix the guard flagged on #478.")) == []


def test_uncapitalized_body_fails() -> None:
    violations = release.lint_changeset(_cs("add the format lint."))
    assert any("start capitalized" in v.message for v in violations)


def test_body_without_trailing_period_fails() -> None:
    violations = release.lint_changeset(_cs("Add the format lint"))
    assert any("end with a period" in v.message for v in violations)


def test_none_changeset_body_is_not_linted() -> None:
    # A `none` changeset never produces a changelog line, so its body carries
    # no changelog-format obligation — an empty, lowercase, period-less body ok.
    assert release.lint_changeset(_cs("", segment="none")) == []


def test_none_changeset_still_validates_category() -> None:
    violations = release.lint_changeset(_cs("", segment="none", category="Bogus"))
    assert any("unknown category" in v.message for v in violations)


# --- Check 3: the floor field --------------------------------------------


def _components(
    tmp_path: Path, *, requires_backbone: str = '">=1.0.0,<2.0.0"', kind: str = "capability"
) -> dict[str, Component]:
    """The components of a kit holding one component, `houseware`."""
    source_kit = tmp_path / ".pkit"
    source_kit.mkdir()
    (source_kit / "VERSION").write_text("1.5.0\n", encoding="utf-8")
    home = source_kit / "capabilities" / "houseware"
    home.mkdir(parents=True)
    (home / "package.yaml").write_text(
        "schema_version: 1\n"
        f"component:\n  kind: {kind}\n  name: houseware\n  version: 0.3.0\n"
        f"requires_backbone: {requires_backbone}\n",
        encoding="utf-8",
    )
    return {c.name: c for c in discover_components(source_kit)}


def _floor(
    component: str = "houseware", *, segment: str = "minor", value: str = "release"
) -> Changeset:
    return Changeset(
        component=component,
        segment=segment,
        note="Needs the new backbone.",
        path=Path(f"{component}-{segment}-x.yaml"),
        requires_backbone=value,
    )


@pytest.mark.parametrize("requires_backbone", ['">=1.0.0,<2.0.0"', '">=1.0.0"'])
def test_floor_field_on_a_capability_with_a_floor_passes(
    tmp_path: Path, requires_backbone: str
) -> None:
    components = _components(tmp_path, requires_backbone=requires_backbone)
    assert release.lint_floor(_floor(), components) == []


def test_a_changeset_without_the_floor_field_is_not_checked() -> None:
    assert release.lint_floor(_cs(), {}) == []


def test_floor_field_on_a_backbone_changeset_fails(tmp_path: Path) -> None:
    violations = release.lint_floor(_floor("backbone"), _components(tmp_path))
    assert [v.message for v in violations] == [
        "`requires_backbone` is a component's field: the backbone has no "
        "`requires_backbone` to raise."
    ]


@pytest.mark.parametrize(
    ("requires_backbone", "kind", "component"),
    [
        ('"*"', "capability", "houseware"),  # no floor to raise
        ('"<2.0.0,>=1.0.0"', "capability", "houseware"),  # does not open with the floor
        ("'>=1.0.0,<2.0.0'", "capability", "houseware"),  # a shape the broaden cannot widen
        ('">=1.0.0, <2.0.0"', "capability", "houseware"),  # likewise
        ('">=1.0.0,<2.0.0"', "bundle", "houseware"),  # not a capability or adapter
        ('">=1.0.0,<2.0.0"', "capability", "nowhere"),  # no such component
    ],
)
def test_floor_field_on_a_component_without_a_floor_to_raise_fails(
    tmp_path: Path, requires_backbone: str, kind: str, component: str
) -> None:
    components = _components(tmp_path, requires_backbone=requires_backbone, kind=kind)
    violations = release.lint_floor(_floor(component), components)
    assert [v.message for v in violations] == [
        f"{component!r} is not a capability or adapter whose `requires_backbone` has a "
        'floor the release can raise (a range of the form ">=X.Y.Z,<A.B.C" or ">=X.Y.Z").'
    ]


def test_floor_field_with_another_value_fails(tmp_path: Path) -> None:
    violations = release.lint_floor(_floor(value="1.150.0"), _components(tmp_path))
    assert any("takes one value, `release`" in v.message for v in violations)


def test_floor_field_on_a_none_changeset_fails(tmp_path: Path) -> None:
    violations = release.lint_floor(_floor(segment="none"), _components(tmp_path))
    assert any("a `none` changeset moves no version" in v.message for v in violations)


def test_lint_release_format_flags_a_floor_field_on_a_backbone_changeset(tmp_path: Path) -> None:
    source_kit = tmp_path / ".pkit"
    _seed(
        source_kit,
        changeset=(
            "component: backbone\nkind: minor\nbody: Ship it.\n"
            "custom:\n  category: Added\n  requires_backbone: release\n"
        ),
        changelog=VALID_CHANGELOG,
    )
    result = release.lint_release_format(source_kit)
    assert not result.ok
    assert [v.source for v in result.violations] == ["changeset backbone-minor-x.yaml"]


# --- Check 4: CHANGELOG.md structure -------------------------------------


VALID_CHANGELOG = """# Changelog

## 1.140.0 — 2026-07-04

### Added
- Ship the format lint. ([#478])

### Changed
- pkit now runs the version each project pins. ([#465])

[#465]: https://github.com/x/pull/465
[#478]: https://github.com/x/pull/478
"""


def test_valid_changelog_passes() -> None:
    assert release.lint_changelog(VALID_CHANGELOG) == []


def test_date_only_release_heading_passes() -> None:
    text = "# Changelog\n\n## 2026-07-04\n\n### Fixed\n- A component-only fix.\n"
    assert release.lint_changelog(text) == []


def test_bracketed_kac_heading_passes() -> None:
    text = "# Changelog\n\n## [1.2.0] - 2026-07-04\n\n### Added\n- A thing.\n"
    assert release.lint_changelog(text) == []


def test_malformed_release_heading_fails() -> None:
    text = "# Changelog\n\n## release 1.2.0 on tuesday\n\n### Added\n- A thing.\n"
    violations = release.lint_changelog(text)
    assert any("malformed release heading" in v.message for v in violations)


def test_unknown_category_heading_fails() -> None:
    text = "# Changelog\n\n## 1.2.0 — 2026-07-04\n\n### Enhancements\n- A thing.\n"
    violations = release.lint_changelog(text)
    assert any("unknown category heading" in v.message for v in violations)


def test_changelog_violation_reports_line_number() -> None:
    text = "# Changelog\n\n## bogus heading\n"
    violations = release.lint_changelog(text)
    assert violations and violations[0].source == "CHANGELOG.md:3"


# --- lint_release_format + the escape hatch ------------------------------


def _seed(source_kit: Path, *, changeset: str | None, changelog: str | None) -> None:
    source_kit.mkdir(parents=True, exist_ok=True)
    if changeset is not None:
        unreleased = source_kit.parent / ".changes" / "unreleased"
        unreleased.mkdir(parents=True, exist_ok=True)
        (unreleased / "backbone-minor-x.yaml").write_text(changeset, encoding="utf-8")
    if changelog is not None:
        (source_kit.parent / "CHANGELOG.md").write_text(changelog, encoding="utf-8")


def test_lint_release_format_ok_on_valid_inputs(tmp_path: Path) -> None:
    source_kit = tmp_path / ".pkit"
    _seed(
        source_kit,
        changeset="component: backbone\nkind: minor\nbody: Ship it.\ncategory: Added\n",
        changelog=VALID_CHANGELOG,
    )
    result = release.lint_release_format(source_kit)
    assert result.ok
    assert result.violations == []


def test_lint_release_format_flags_bad_changeset(tmp_path: Path) -> None:
    source_kit = tmp_path / ".pkit"
    _seed(
        source_kit,
        changeset="component: backbone\nkind: minor\nbody: ship it\ncategory: Bogus\n",
        changelog=VALID_CHANGELOG,
    )
    result = release.lint_release_format(source_kit)
    assert not result.ok
    # Bad category + lowercase start + missing period = three violations.
    assert len(result.violations) == 3


def test_lint_release_format_flags_bad_changelog(tmp_path: Path) -> None:
    source_kit = tmp_path / ".pkit"
    _seed(
        source_kit,
        changeset=None,
        changelog="# Changelog\n\n## nope\n",
    )
    result = release.lint_release_format(source_kit)
    assert not result.ok


def test_escape_hatch_passes_unconditionally(tmp_path: Path) -> None:
    source_kit = tmp_path / ".pkit"
    _seed(source_kit, changeset=None, changelog="# Changelog\n\n## nope\n")
    result = release.lint_release_format(source_kit, skip=True)
    assert result.skipped
    assert result.ok


def test_no_changelog_and_no_changesets_is_ok(tmp_path: Path) -> None:
    source_kit = tmp_path / ".pkit"
    source_kit.mkdir()
    result = release.lint_release_format(source_kit)
    assert result.ok


# --- Dogfood: the live repo's own state must pass ------------------------


def test_live_repo_changesets_and_changelog_pass() -> None:
    result = release.lint_release_format(REPO_ROOT / ".pkit")
    assert result.ok, [f"{v.source}: {v.message}" for v in result.violations]
