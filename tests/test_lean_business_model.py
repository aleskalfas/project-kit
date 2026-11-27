"""The model of a lean-business idea's files (DEC-002 points 2 and 7): what the layout finds
in a location, where it puts a subject's file, the files it reads, and the lookups between
the files, each with a typed result."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from tests.in_process import load

(layout, listing, model) = load("lean-business", "layout", "listing", "model")

FIXTURE = Path(__file__).resolve().parent / "fixtures/lean-business/.repo"
LOCATION = "lean-business"
IDEA = f"{LOCATION}/meal-plan"


def project(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    shutil.copytree(FIXTURE, root)
    return root


def idea_model(root: Path) -> Any:
    contents = layout.read(root, LOCATION)
    return model.IdeaModel(contents.ideas["meal-plan"], model.Pools.of(contents))


# --- where the layout puts a subject's file -------------------------------------------------------


@pytest.mark.parametrize(
    ("kind", "qualified", "rel"),
    [
        ("goal", "meal-plan", f"{IDEA}/goal.yaml"),
        ("canvas", "meal-plan--direct", f"{IDEA}/variants/direct/canvas.yaml"),
        ("assumptions", "meal-plan--direct", f"{IDEA}/variants/direct/assumptions.yaml"),
        ("experiment", "meal-plan--landing-page", f"{IDEA}/experiments/landing-page.yaml"),
        ("cycle", "meal-plan--first", f"{IDEA}/cycles/first.yaml"),
    ],
)
def test_the_layout_puts_each_subjects_file_where_it_reads_it(
    kind: str, qualified: str, rel: str
) -> None:
    assert layout.path_of(LOCATION, kind, qualified) == rel
    assert (FIXTURE / rel).is_file()


@pytest.mark.parametrize(
    ("kind", "qualified"),
    [
        ("goal", "meal-plan--direct"),
        ("canvas", "meal-plan"),
        ("experiment", "meal-plan--direct--x"),
        ("cycle", "Meal-plan--first"),
        ("cycle", "meal-plan/../x.first"),
        ("note", "meal-plan--x"),
    ],
    ids=["goal-of-a-variant", "canvas-of-an-idea", "too-deep", "upper-case", "a-path", "no-kind"],
)
def test_no_place_for_an_id_of_another_form_or_a_kind_it_does_not_hold(
    kind: str, qualified: str
) -> None:
    with pytest.raises(layout.IdRefused):
        layout.path_of(LOCATION, kind, qualified)


# --- what a location holds ----------------------------------------------------------------------


def test_one_ideas_folder_is_read_alone(tmp_path: Path) -> None:
    root = project(tmp_path)
    shutil.copytree(root / IDEA, root / LOCATION / "other")
    whole = layout.read(root, LOCATION)
    assert sorted(whole.ideas) == ["meal-plan", "other"]
    alone = layout.read(root, LOCATION, idea="meal-plan")
    assert sorted(alone.ideas) == ["meal-plan"]
    assert alone.ideas["meal-plan"] == whole.ideas["meal-plan"]
    assert layout.read(root, LOCATION, idea="nothing").ideas == {}
    with pytest.raises(layout.IdRefused):
        layout.read(root, LOCATION, idea="../meal-plan")


def test_outside_a_repository_the_files_are_walked_without_links(tmp_path: Path) -> None:
    root = project(tmp_path)
    (root / "linked").symlink_to(root / LOCATION, target_is_directory=True)
    (root / "goal-link.yaml").symlink_to(root / IDEA / "goal.yaml")
    listed = listing.files(root)
    assert f"{IDEA}/goal.yaml" in listed
    assert not [rel for rel in listed if rel.startswith("linked/") or rel == "goal-link.yaml"]
    assert listing.files(root, "nothing") == []


def test_in_a_repository_the_files_are_those_git_sees(tmp_path: Path) -> None:
    root = project(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    (root / ".gitignore").write_text("ignored/\n", encoding="utf-8")
    (root / "ignored").mkdir()
    (root / "ignored/goal.yaml").write_text("x: 1\n", encoding="utf-8")
    listed = listing.files(root)
    assert f"{IDEA}/goal.yaml" in listed and ".gitignore" in listed
    assert "ignored/goal.yaml" not in listed
    # A tracked file the working tree no longer holds is no file.
    subprocess.run(["git", "add", f"{IDEA}/goal.yaml"], cwd=root, check=True)
    (root / IDEA / "goal.yaml").unlink()
    assert f"{IDEA}/goal.yaml" not in listing.files(root, LOCATION)


def test_a_listing_git_refuses_fails(tmp_path: Path) -> None:
    root = project(tmp_path)
    (root / ".git").write_text("gitdir: nowhere\n", encoding="utf-8")
    with pytest.raises(listing.ListingFailed):
        listing.files(root)


# --- the lookups ----------------------------------------------------------------------------------


def test_a_lookup_finds_a_subject_of_the_idea(tmp_path: Path) -> None:
    idea = idea_model(project(tmp_path))
    found = idea.resolve("[canvas:meal-plan--direct]", "canvas")
    assert isinstance(found, model.Found)
    assert found.subject.rel == f"{IDEA}/variants/direct/canvas.yaml"
    assert model.found(found) == found.subject.data


@pytest.mark.parametrize(
    ("value", "namespace", "expected"),
    [
        ("[canvas:meal-plan--nothing]", "canvas", model.Dangling("meal-plan--nothing")),
        ("[canvas:other--direct]", "canvas", model.Foreign("other--direct")),
        ("[cycle:meal-plan--first]", "canvas", model.NoReference()),
        ("meal-plan--direct", "canvas", model.NoReference()),
        (None, "cycle", model.NoReference()),
    ],
    ids=["names-nothing", "another-ideas", "another-namespace", "bare", "none"],
)
def test_a_lookup_that_finds_no_subject_says_why(
    tmp_path: Path, value: object, namespace: str, expected: object
) -> None:
    idea = idea_model(project(tmp_path))
    lookup = idea.resolve(value, namespace)
    assert lookup == expected
    assert model.found(lookup) is None


def test_the_lookups_between_an_ideas_files(tmp_path: Path) -> None:
    idea = idea_model(project(tmp_path))
    [interviews, landing] = idea.experiments
    assert (interviews.own, landing.own) == ("first-interviews", "landing-page")
    assert model.found(idea.cycle_of(landing)) == idea.cycles[0].data
    assert idea.variant_tested(landing) == "meal-plan--direct"
    assert idea.experiments_of("meal-plan--first") == [interviews, landing]
    assert idea.experiments_on("meal-plan--direct--pays-monthly") == [landing]
    assert idea.declared_on("meal-plan--direct--pays-monthly")
    assert not idea.declared_on("meal-plan--direct--nothing")
    assert [name for name, _, _ in idea.canvases()] == ["direct", "two-sided"]


def test_a_lookup_into_a_kind_the_location_holds_no_file_of_is_told_apart(tmp_path: Path) -> None:
    root = project(tmp_path)
    (root / IDEA / "cycles/first.yaml").unlink()
    pools = model.Pools.of(layout.read(root, LOCATION))
    assert pools.held == {"canvas", "assumptions", "experiment"}
    idea = idea_model(root)
    assert idea.resolve("[cycle:meal-plan--first]", "cycle") == model.Unheld(
        "cycle", "meal-plan--first"
    )
    assert idea.resolve("[canvas:meal-plan--nothing]", "canvas") == model.Dangling(
        "meal-plan--nothing"
    )


def test_an_id_given_twice_finds_the_first_file_that_gives_it(tmp_path: Path) -> None:
    root = project(tmp_path)
    shutil.copy(root / IDEA / "experiments/landing-page.yaml", root / IDEA / "experiments/x.yaml")
    pools = model.Pools.of(layout.read(root, LOCATION))
    # The duplicate is the data member's to report; a lookup reads the first that claims it.
    claims = pools.by["experiment"]["meal-plan--landing-page"]
    assert [claim.rel for claim in claims] == [
        f"{IDEA}/experiments/landing-page.yaml",
        f"{IDEA}/experiments/x.yaml",
    ]
    assert pools.get("experiment", "meal-plan--landing-page") == claims[0]


def test_a_goal_that_does_not_read_is_told_from_none(tmp_path: Path) -> None:
    root = project(tmp_path)
    assert not idea_model(root).goal_unread
    (root / IDEA / "goal.yaml").write_text("revenue: [\n", encoding="utf-8")
    unread = idea_model(root)
    assert unread.goal is None and unread.goal_unread
    (root / IDEA / "goal.yaml").unlink()
    none = idea_model(root)
    assert none.goal is None and not none.goal_unread


def test_a_cycle_first_planned_is_read_beside_its_last_change() -> None:
    planned = {"planned": {"when": "2026-10-25", "first": {"when": "2026-10-20"}}}
    assert str(model.first_planned(planned)) == "2026-10-20"
    assert str(model.first_planned({"planned": {"when": "2026-10-25"}})) == "2026-10-25"
    assert model.first_planned({}) is None


# --- every fingerprint taken again --------------------------------------------------------------


def test_the_fixture_keeps_every_fingerprint_its_files_take_again(tmp_path: Path) -> None:
    root = project(tmp_path)
    idea = idea_model(root)
    taken = model.retaken(idea)
    assert {(each.rel, "/".join(each.path)) for each in taken} >= {
        (f"{IDEA}/variants/direct/canvas.yaml", "outcome/fingerprint"),
        (f"{IDEA}/experiments/landing-page.yaml", "declared/rested-on"),
        (f"{IDEA}/experiments/landing-page.yaml", "declared/fingerprint"),
        (f"{IDEA}/cycles/first.yaml", "planned/fingerprint"),
    }
    kept = {file.rel: data for _, file, data in idea.canvases()}
    kept |= {each.rel: each.data for each in (*idea.experiments, *idea.cycles)}
    for each in taken:
        node = kept[each.rel]
        for key in each.path:
            node = node[key]
        assert node == each.value
