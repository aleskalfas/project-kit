"""The project's bar against what the review grades (visual-communication DEC-042 point 3):
the capability's check fails a bar that covers what the review does not grade, and one whose
major for a set differs from the major the project pins for it, or from the set's own where
it pins none. Run in this process; it starts no `pkit`."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.in_process import load
from tests.visual_communication_project import CONFIG, project, write

(checks,) = load("visual-communication", "checks")

BINDING = "pkit_schema: visual-communication:config\nschema_version: 1\n"
BACKBONE_CONFIG = ".pkit/project/config.yaml"


def configured(root: Path, *covers: str, at_least: str = "professional") -> None:
    """The capability's configuration holding a bar over `covers`."""
    listed = ", ".join(f'"{each}"' for each in covers)
    write(root / CONFIG, f"{BINDING}bar:\n  covers: [{listed}]\n  at-least: {at_least}\n")


def own_set(root: Path, name: str, *inherits: str, rules: tuple[str, ...] = ("001",)) -> None:
    """A rule set of the project's own, in `tech-docs/rule-sets/`, the internal root the
    project's backbone configuration names."""
    write(root / BACKBONE_CONFIG, "docs:\n  internal: tech-docs/\n")
    front = f"rule-set: {name}\nversion: 1.0.0\n"
    if inherits:
        front += f"inherits: [{', '.join(inherits)}]\n"
    front += "rules:\n"
    for number in rules:
        front += f"  RS-{name}-{number}:\n    status: accepted\n    origin: {{why: x}}\n"
    write(root / "tech-docs" / "rule-sets" / f"{name.lower()}.md", f"---\n{front}---\n\nText.\n")


def found(root: Path) -> list[tuple[str, str]]:
    """Each finding the check makes: its code, and what it says."""
    report = checks.check(root)
    return [(finding.code, finding.message) for finding, _ in report.judged]


def codes(root: Path) -> list[str]:
    return [code for code, _ in found(root)]


def test_a_bar_over_the_sets_the_review_grades_at_their_majors_fails_nothing(
    tmp_path: Path,
) -> None:
    root = project(tmp_path)
    configured(root, "COMM@2", "GRAPHIC@3", "RS-COMM-003@2")
    assert found(root) == []


def test_a_configuration_with_no_bar_fails_nothing(tmp_path: Path) -> None:
    root = project(tmp_path)
    write(root / CONFIG, BINDING)
    assert found(root) == []


@pytest.mark.parametrize("cover", ["NOPE@1", "VIS@1", "RS-VIS-001@1", "RS-COMM-999@1"])
def test_a_bar_that_covers_what_the_review_does_not_grade_fails(tmp_path: Path, cover: str) -> None:
    root = project(tmp_path)
    configured(root, "COMM@2", cover)
    ((code, message),) = found(root)
    assert code == "bar-ungraded"
    assert cover in message


def test_the_loaded_set_is_not_graded(tmp_path: Path) -> None:
    root = project(tmp_path)
    configured(root, "VIS@1")
    assert codes(root) == ["bar-ungraded"]


def test_a_set_of_the_projects_own_that_inherits_none_the_review_grades_is_not_graded(
    tmp_path: Path,
) -> None:
    root = project(tmp_path)
    own_set(root, "PLAIN")
    configured(root, "PLAIN@1")
    assert codes(root) == ["bar-ungraded"]


def test_a_set_of_the_projects_own_that_inherits_one_is_graded_for_its_own_rules(
    tmp_path: Path,
) -> None:
    root = project(tmp_path)
    own_set(root, "BRAND", "visual-communication:COMM@2", rules=("001", "002"))
    configured(root, "BRAND@1", "RS-BRAND-002@1")
    assert found(root) == []
    configured(root, "RS-BRAND-003@1")
    assert codes(root) == ["bar-ungraded"]


def test_a_set_that_inherits_one_through_another_of_the_projects_is_graded(
    tmp_path: Path,
) -> None:
    root = project(tmp_path)
    own_set(root, "BRAND", "visual-communication:COMM@2")
    own_set(root, "LEAF", "BRAND@1")
    configured(root, "LEAF@1")
    assert found(root) == []


@pytest.mark.parametrize("cover", ["COMM@3", "COMM@0", "RS-COMM-003@3", "GRAPHIC@2"])
def test_a_bar_whose_major_differs_from_the_sets_own_where_none_pins_it_fails(
    tmp_path: Path, cover: str
) -> None:
    root = project(tmp_path)
    configured(root, cover)
    ((code, message),) = found(root)
    assert code == "bar-major"
    assert cover in message
    assert "the set's own" in message


def test_a_bar_at_the_major_the_project_pins_stands_though_the_sets_own_differs(
    tmp_path: Path,
) -> None:
    root = project(tmp_path)
    own_set(root, "BRAND", "visual-communication:COMM@0")
    configured(root, "COMM@0")
    assert found(root) == []


def test_a_bar_at_the_sets_own_major_fails_where_the_project_pins_another(
    tmp_path: Path,
) -> None:
    root = project(tmp_path)
    own_set(root, "BRAND", "visual-communication:COMM@0")
    configured(root, "COMM@2")
    ((code, message),) = found(root)
    assert code == "bar-major"
    assert "pinned by a rule set of the project's" in message


def test_each_cover_is_judged_alone(tmp_path: Path) -> None:
    root = project(tmp_path)
    configured(root, "COMM@3", "NOPE@1", "GRAPHIC@3")
    assert codes(root) == ["bar-major", "bar-ungraded"]


def test_the_findings_lie_in_the_configuration_and_name_the_fix(tmp_path: Path) -> None:
    root = project(tmp_path)
    configured(root, "COMM@3")
    ((finding, level),) = checks.check(root).judged
    assert (finding.file, finding.where, level) == (CONFIG, "bar.covers", "fails")
    assert "COMM@2" in finding.fix


def test_a_bar_the_schema_refuses_is_left_to_the_cores_validation(tmp_path: Path) -> None:
    root = project(tmp_path)
    write(root / CONFIG, f"{BINDING}bar:\n  covers: COMM@2\n  at-least: competent\n")
    assert found(root) == []
