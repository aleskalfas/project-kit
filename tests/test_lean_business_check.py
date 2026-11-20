"""`pkit lean check` (lean-business DEC-002 point 14): the capability's validator, under the
query contract, and each finding it reports, with its severity. Each test starts from the
fixture idea, which breaks nothing, and changes one thing; a change to what a fingerprint
covers takes the fingerprints again, as a command would (`model.retaken`), unless the test
is of the fingerprint itself."""

from __future__ import annotations

import ast
import json
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner
from ruamel.yaml import YAML

from project_kit import data_validate as dv
from project_kit.cli import main
from tests.adopter_repo import MakeAdopterRepo
from tests.in_process import CAPABILITIES, load, run_main

(check_script, checks, fingerprint, layout, model) = load(
    "lean-business", "check.py", "checks", "fingerprint", "layout", "model"
)

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE = Path(__file__).resolve().parent / "fixtures/lean-business/repo"

IDEA = "lean-business/meal-plan"
GOAL = f"{IDEA}/goal.yaml"
DIRECT = f"{IDEA}/variants/direct/canvas.yaml"
ASSUMPTIONS = f"{IDEA}/variants/direct/assumptions.yaml"
SIDED = f"{IDEA}/variants/two-sided/canvas.yaml"
INTERVIEWS = f"{IDEA}/experiments/first-interviews.yaml"
LANDING = f"{IDEA}/experiments/landing-page.yaml"
CYCLE = f"{IDEA}/cycles/first.yaml"
CONFIG = ".pkit/capabilities/lean-business/project/config.yaml"

Change = Callable[[Any], None]


# --- the fixture, and changing it ---------------------------------------------------------------


def project(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    shutil.copytree(FIXTURE, root)
    return root


def _yaml() -> YAML:
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096
    return yaml


def load_file(root: Path, rel: str) -> Any:
    return _yaml().load((root / rel).read_text(encoding="utf-8"))


def write(root: Path, rel: str, data: Any) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as out:
        _yaml().dump(data, out)


def edit(root: Path, rel: str, change: Change, *, retake: bool = True) -> None:
    data = load_file(root, rel)
    change(data)
    write(root, rel, data)
    if retake:
        take_again(root)


def take_again(root: Path, *, only: tuple[str, str] | None = None) -> None:
    """Take every fingerprint of the location's ideas again, as the commands would, and keep
    each where `model.retaken` says it is kept; where `only` is given, only the one the file
    `only[0]` keeps at the keys `only[1]`, joined by slashes."""
    contents = layout.read(root, "lean-business")
    pools = model.Pools.of(contents)
    for idea in contents.ideas.values():
        for taken in model.retaken(model.IdeaModel(idea, pools)):
            if only is not None and (taken.rel, "/".join(taken.path)) != only:
                continue
            data = load_file(root, taken.rel)
            node = data
            for key in taken.path[:-1]:
                node = node[key]
            node[taken.path[-1]] = dict(taken.value)
            write(root, taken.rel, data)


def put(*path_and_value: Any) -> Change:
    """A change that sets the last of `path_and_value` at the path the others give."""
    *path, value = path_and_value

    def change(data: Any) -> None:
        node = data
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = value

    return change


def drop(*path: Any) -> Change:
    """A change that removes what lies at `path`."""

    def change(data: Any) -> None:
        node = data
        for key in path[:-1]:
            node = node[key]
        del node[path[-1]]

    return change


def recorded_on(day: str) -> Change:
    """A change that records an experiment's result and its decision on `day`."""

    def change(data: Any) -> None:
        data["result"]["when"] = data["decision"]["when"] = day

    return change


def found(root: Path) -> list[tuple[str, str, str]]:
    return [(f.severity, f.label, f.location) for f in checks.check(root).findings]


def kinds(root: Path) -> set[tuple[str, str]]:
    return {(severity, label) for severity, label, _ in found(root)}


def at(root: Path, label: str) -> list[str]:
    return [location for _, kind, location in found(root) if kind == label]


def messages(root: Path, label: str) -> list[str]:
    return [f.message for f in checks.check(root).findings if f.label == label]


def data_found(root: Path) -> list[tuple[str, str]]:
    """What the backbone's data validation finds in the location, which the check leaves to
    it: each issue's severity and place, a file's place relative to `root`."""
    report = dv.validate_path(root / "lean-business", REPO_ROOT)
    return [(i.severity, i.location.removeprefix(f"{root}/")) for i in report.issues]


# --- the fixture breaks nothing -----------------------------------------------------------------


def test_the_fixture_idea_breaks_nothing(tmp_path: Path) -> None:
    root = project(tmp_path)
    report = checks.check(root)
    assert report.findings == []
    assert report.summary == [
        "1 idea, 2 variants, 2 experiments, 1 cycle in `lean-business` (the default, not "
        "recorded yet)",
        "the shape of each file, and each reference that names nothing, is checked by "
        "`pkit validate`'s `data` member, or by `pkit data validate lean-business`; this "
        "check judges what they leave open",
    ]
    assert data_found(root) == []


# --- the query contract -------------------------------------------------------------------------


def test_json_prints_the_document_and_exits_0_though_a_finding_is_an_error(tmp_path: Path) -> None:
    root = project(tmp_path)
    edit(root, INTERVIEWS, put("learn", "Something else"), retake=False)
    shown = run_main(check_script, "--json", cwd=root)
    assert shown.returncode == 0, shown.stderr
    document = json.loads(shown.stdout)
    assert set(document) == {"summary", "findings"}
    assert document["findings"] == [
        {
            "severity": "error",
            "location": f"{INTERVIEWS}#/declared/fingerprint",
            "message": messages(root, "declaration-changed")[0],
            "label": "declaration-changed",
        }
    ]


def test_without_json_it_exits_1_on_an_error_and_0_on_a_warning(tmp_path: Path) -> None:
    root = project(tmp_path)
    assert run_main(check_script, cwd=root).returncode == 0
    edit(root, DIRECT, put("boxes", "problem", 0, "text", "Planning takes too long"), retake=False)
    shown = run_main(check_script, cwd=root)
    assert (shown.returncode, "[stale]" in shown.stdout) == (0, True)
    edit(root, INTERVIEWS, put("learn", "Something else"), retake=False)
    shown = run_main(check_script, cwd=root)
    assert (shown.returncode, "[declaration-changed]" in shown.stdout) == (1, True)
    assert shown.stdout.index("[declaration-changed]") < shown.stdout.index("[stale]")


# --- the location -------------------------------------------------------------------------------


def test_with_nothing_recorded_and_no_folder_there_are_no_ideas(tmp_path: Path) -> None:
    report = checks.check(tmp_path)
    assert (report.summary, report.findings) == (
        ["no ideas in `lean-business` (the default, not recorded yet)"],
        [],
    )


def test_a_file_named_as_the_default_is_no_location(tmp_path: Path) -> None:
    (tmp_path / "lean-business").write_text("notes\n", encoding="utf-8")
    report = checks.check(tmp_path)
    assert report.findings == []
    assert report.summary == ["no ideas: nothing is recorded, and `lean-business` is no folder"]


def test_the_recorded_location_is_read(tmp_path: Path) -> None:
    root = project(tmp_path)
    (root / "work").mkdir()
    (root / "lean-business").rename(root / "work/ideas")
    (root / CONFIG).parent.mkdir(parents=True)
    (root / CONFIG).write_text("location: work/ideas\n", encoding="utf-8")
    report = checks.check(root)
    assert report.findings == []
    assert report.summary[0].endswith("in `work/ideas` (recorded)")


def test_a_recorded_location_whose_folder_does_not_exist_holds_no_idea(tmp_path: Path) -> None:
    (tmp_path / CONFIG).parent.mkdir(parents=True)
    (tmp_path / CONFIG).write_text("location: ideas\n", encoding="utf-8")
    report = checks.check(tmp_path)
    assert (report.summary, report.findings) == (["no ideas in `ideas` (recorded)"], [])


@pytest.mark.parametrize(
    "config",
    [
        "location: .pkit/ideas\n",
        "location: ../ideas\n",
        "location: /ideas\n",
        "location: work/.hidden\n",
        "location: ideas/\n",
        "location: '.'\n",
        "location: 'a\\b'\n",
        "location:\n",
        "location: 3\n",
        "location: [\n",
        "- a list\n",
    ],
    ids=[
        "methodology",
        "outside",
        "absolute",
        "hidden",
        "trailing-slash",
        "the-top",
        "backslash",
        "empty",
        "no-path",
        "unreadable",
        "no-mapping",
    ],
)
def test_a_location_the_rules_refuse_is_an_error(tmp_path: Path, config: str) -> None:
    (tmp_path / CONFIG).parent.mkdir(parents=True)
    (tmp_path / CONFIG).write_text(config, encoding="utf-8")
    assert found(tmp_path) == [("error", "location", CONFIG)]


def test_a_location_reached_through_a_link_is_an_error(tmp_path: Path) -> None:
    root = project(tmp_path)
    (root / "linked").symlink_to(root / "lean-business", target_is_directory=True)
    (root / CONFIG).parent.mkdir(parents=True)
    (root / CONFIG).write_text("location: linked\n", encoding="utf-8")
    assert found(root) == [("error", "location", CONFIG)]


# --- the layout ---------------------------------------------------------------------------------


def test_a_file_of_the_capabilitys_where_the_layout_has_no_place_for_it(tmp_path: Path) -> None:
    root = project(tmp_path)
    (root / IDEA / "notes").mkdir()
    shutil.copy(root / GOAL, root / IDEA / "notes/goal.yaml")
    assert found(root) == [("error", "layout", f"{IDEA}/notes/goal.yaml")]


def test_files_of_no_schema_of_the_capabilitys_hidden_files_and_links_are_passed_over(
    tmp_path: Path,
) -> None:
    root = project(tmp_path)
    (root / IDEA / "notes.md").write_text("# Notes\n", encoding="utf-8")
    (root / IDEA / "other.yaml").write_text("pkit_schema: other:thing\n", encoding="utf-8")
    shutil.copy(root / GOAL, root / IDEA / ".draft.yaml")
    (root / IDEA / "linked").symlink_to(root / IDEA / "variants", target_is_directory=True)
    assert found(root) == []


def test_a_file_at_a_place_that_names_another_schema_or_none(tmp_path: Path) -> None:
    root = project(tmp_path)
    write(root, f"{IDEA}/experiments/later.yaml", {"pkit_schema": "lean-business:cycle"})
    write(root, f"{IDEA}/cycles/second.yaml", {"schema_version": 1})
    write(root, f"{IDEA}/cycles/third.yaml", ["a list"])
    assert found(root) == [
        ("error", "binding", f"{IDEA}/cycles/second.yaml"),
        ("error", "binding", f"{IDEA}/cycles/third.yaml"),
        ("error", "binding", f"{IDEA}/experiments/later.yaml"),
    ]
    [message] = [m for m in messages(root, "binding") if "later" not in m and "names no" in m]
    assert "where the layout puts a cycle" in message


def test_a_file_that_does_not_parse_is_an_error(tmp_path: Path) -> None:
    root = project(tmp_path)
    (root / GOAL).write_text("revenue: [\n", encoding="utf-8")
    assert ("error", "unreadable", GOAL) in found(root)


def test_a_folder_or_a_file_named_by_no_id(tmp_path: Path) -> None:
    root = project(tmp_path)
    shutil.copytree(root / IDEA, root / "lean-business/Meal_Plan")
    (root / LANDING).rename(root / IDEA / "experiments/Landing.yaml")
    assert found(root) == [
        ("error", "layout", "lean-business/Meal_Plan"),
        ("error", "layout", f"{IDEA}/experiments/Landing.yaml"),
    ]


def test_a_variants_assumptions_without_its_canvas(tmp_path: Path) -> None:
    root = project(tmp_path)
    ghost = f"{IDEA}/variants/ghost/assumptions.yaml"
    write(root, ghost, {"pkit_schema": "lean-business:assumptions", "assumptions": []})
    assert found(root) == [("error", "layout", ghost)]


def test_a_file_of_the_layout_that_ends_in_yml(tmp_path: Path) -> None:
    root = project(tmp_path)
    shutil.copy(root / LANDING, root / IDEA / "experiments/later.yml")
    shutil.copy(root / GOAL, root / IDEA / "draft.yml")
    (root / IDEA / "notes.yml").write_text("kept: true\n", encoding="utf-8")
    assert found(root) == [
        ("error", "layout", f"{IDEA}/draft.yml"),
        ("error", "layout", f"{IDEA}/experiments/later.yml"),
    ]
    assert "rename it to `later.yaml`" in messages(root, "layout")[1]


def test_a_file_of_the_capabilitys_outside_the_location(tmp_path: Path) -> None:
    root = project(tmp_path)
    shutil.copy(root / GOAL, root / "goal.yaml")
    (root / "docs").mkdir()
    shutil.copy(root / LANDING, root / "docs/landing.yaml")
    project_own = ".pkit/capabilities/lean-business/project/goal.yaml"
    (root / project_own).parent.mkdir(parents=True)
    shutil.copy(root / GOAL, root / project_own)
    (root / "config.yaml").write_text("pkit_schema: lean-business:config\n", encoding="utf-8")
    assert found(root) == [
        ("error", "layout", project_own),
        ("error", "layout", "config.yaml"),
        ("error", "layout", "docs/landing.yaml"),
        ("error", "layout", "goal.yaml"),
    ]
    assert f"outside `{CONFIG}`" in messages(root, "layout")[1]


def test_what_the_backbones_data_validation_never_reads_is_passed_over(tmp_path: Path) -> None:
    root = project(tmp_path)
    (root / CONFIG).parent.mkdir(parents=True)
    (root / CONFIG).write_text(
        "pkit_schema: lean-business:config\nlocation: lean-business\n", encoding="utf-8"
    )
    shipped = ".pkit/capabilities/lean-business/schemas/goal.yaml"
    (root / shipped).parent.mkdir(parents=True)
    shutil.copy(root / GOAL, root / shipped)
    (root / ".notes").mkdir()
    shutil.copy(root / GOAL, root / ".notes/goal.yaml")
    assert found(root) == []


def test_a_file_git_ignores_is_read_by_neither_validation(tmp_path: Path) -> None:
    root = project(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    ignored = f"{IDEA}/experiments/ignored.yaml"
    (root / ".gitignore").write_text(f"{ignored}\nstray.yaml\n", encoding="utf-8")
    shutil.copy(root / LANDING, root / ignored)
    shutil.copy(root / GOAL, root / "stray.yaml")
    assert found(root) == []
    # A file git does not track, and does not ignore, is one validation reads.
    shutil.copy(root / LANDING, root / IDEA / "experiments/seen.yaml")
    assert kinds(root) == {("error", "id")}


# --- days ---------------------------------------------------------------------------------------


def test_a_day_the_calendar_does_not_hold(tmp_path: Path) -> None:
    root = project(tmp_path)
    text = (root / GOAL).read_text(encoding="utf-8")
    # Written plain or quoted, a day reads alike.
    for value, written in (("2026-02-30", "2026-02-30"), ("2026-13-01", '"2026-13-01"')):
        (root / GOAL).write_text(text.replace("2026-10-01", written), encoding="utf-8")
        assert found(root) == [("error", "day", f"{GOAL}#/when")]
        assert f"`{value}` is written as a day" in messages(root, "day")[0]


def test_a_day_held_in_a_list_or_a_record_kept_beside_it(tmp_path: Path) -> None:
    root = project(tmp_path)
    edit(root, CYCLE, put("suspensions", 0, "resumed", "when", "2027-01-32"))
    edit(root, INTERVIEWS, put("declared", "rested-on", "when", "2026-10-00"), retake=False)
    assert at(root, "day") == [
        f"{CYCLE}#/suspensions/0/resumed/when",
        f"{INTERVIEWS}#/declared/rested-on/when",
    ]


# --- ids and references -------------------------------------------------------------------------


def test_an_id_that_does_not_match_its_place(tmp_path: Path) -> None:
    root = project(tmp_path)
    edit(root, LANDING, put("id", "meal-plan--landing"))
    assert found(root) == [("error", "id", f"{LANDING}#/id")]


def test_an_entry_not_qualified_by_its_variant(tmp_path: Path) -> None:
    root = project(tmp_path)
    edit(root, DIRECT, put("boxes", "cost-structure", 0, "id", "meal-plan--other--hosting"))
    assert found(root) == [("error", "id", f"{DIRECT}#/boxes/cost-structure/0/id")]


def test_an_entry_id_given_twice_in_a_canvas(tmp_path: Path) -> None:
    root = project(tmp_path)
    edit(root, DIRECT, put("boxes", "unfair-advantage", 0, "id", "meal-plan--direct--hosting"))
    assert found(root) == [("error", "duplicate-id", f"{DIRECT}#/boxes/unfair-advantage/0/id")]


def test_an_id_given_twice_across_the_location_is_the_data_members(tmp_path: Path) -> None:
    root = project(tmp_path)
    shutil.copy(root / LANDING, root / IDEA / "experiments/landing-page-again.yaml")
    assert found(root) == [("error", "id", f"{IDEA}/experiments/landing-page-again.yaml#/id")]
    assert data_found(root) == [("error", "lean-business:experiment")]


def test_an_assumption_not_qualified_by_its_variant(tmp_path: Path) -> None:
    root = project(tmp_path)
    edit(root, ASSUMPTIONS, put("assumptions", 1, "id", "meal-plan--other--pays-monthly"))
    assert found(root) == [("error", "id", f"{ASSUMPTIONS}#/assumptions/1/id")]
    # The landing page names the id it had, which the data member finds names nothing.
    assert data_found(root) == [("error", f"{LANDING}/assumption")]


@pytest.mark.parametrize(
    ("rel", "change", "where"),
    [
        (
            INTERVIEWS,
            put("assumption", "[assumptions:meal-plan--direct--nothing]"),
            f"{INTERVIEWS}/assumption",
        ),
        (
            CYCLE,
            put("review", "evidence", ["[experiment:meal-plan--nothing]"]),
            f"{CYCLE}/review/evidence/0",
        ),
    ],
    ids=["an-experiments-assumption", "a-reviews-evidence"],
)
def test_a_reference_that_names_nothing_is_the_data_members(
    tmp_path: Path, rel: str, change: Change, where: str
) -> None:
    root = project(tmp_path)
    edit(root, rel, change)
    assert found(root) == []
    assert data_found(root) == [("error", where)]


def test_a_reference_into_a_kind_the_location_holds_no_file_of(tmp_path: Path) -> None:
    root = project(tmp_path)
    (root / CYCLE).unlink()
    # The data member only warns: a reference to an instance not yet made is normal to it.
    assert data_found(root) == [("warning", f"{INTERVIEWS}/cycle"), ("warning", f"{LANDING}/cycle")]
    assert at(root, "reference") == [f"{INTERVIEWS}#/cycle", f"{LANDING}#/cycle"]
    assert "the location holds no cycle file" in messages(root, "reference")[0]


@pytest.mark.parametrize(
    ("rel", "change", "where"),
    [
        (INTERVIEWS, put("cycle", "[cycle:other-idea--first]"), f"{INTERVIEWS}#/cycle"),
        (SIDED, put("comes-from", "[canvas:other-idea--direct]"), f"{SIDED}#/comes-from"),
    ],
    ids=["an-experiments-cycle", "a-variants-origin"],
)
def test_a_reference_to_another_ideas_subject(
    tmp_path: Path, rel: str, change: Change, where: str
) -> None:
    root = project(tmp_path)
    edit(root, rel, change)
    assert found(root) == [("error", "reference", where)]
    assert "an idea stands alone" in messages(root, "reference")[0]


# --- a canvas -----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("rel", "change", "expected"),
    [
        (DIRECT, put("sides", ["cooks", "shops"]), {("error", "sides")}),
        (DIRECT, lambda d: d["viability"].append(dict(d["viability"][0])), {("error", "sides")}),
        (SIDED, put("boxes", "customer-segments", 0, "side", "eaters"), {("error", "sides")}),
        (SIDED, put("viability", 1, "side", "cooks"), {("error", "sides")}),
        (SIDED, put("sides", ["cooks"]), {("error", "sides"), ("warning", "sides-incomplete")}),
        (SIDED, drop("boxes", "customer-segments", 1, "side"), {("warning", "sides-incomplete")}),
        (SIDED, drop("viability", 1, "side"), {("warning", "sides-incomplete")}),
    ],
    ids=[
        "a-direct-model-naming-sides",
        "a-direct-model-with-two-sets-of-inputs",
        "an-entry-naming-an-unknown-side",
        "inputs-given-twice-for-a-side",
        "a-sided-model-naming-one-side",
        "an-entry-naming-no-side",
        "inputs-naming-no-side",
    ],
)
def test_the_sides_of_a_model(
    tmp_path: Path, rel: str, change: Change, expected: set[tuple[str, str]]
) -> None:
    root = project(tmp_path)
    edit(root, rel, change)
    assert kinds(root) == expected


def test_a_verdict_without_a_yes_on_each_step_before_it(tmp_path: Path) -> None:
    root = project(tmp_path)
    verdict = {
        "answer": "yes",
        "fingerprint": {"form": 1, "sha256": "0" * 64},
        "by": "A",
        "when": "2026-10-06",
    }
    edit(root, SIDED, put("verdicts", "viability", verdict), retake=False)
    assert found(root) == [("error", "verdicts", f"{SIDED}#/verdicts/viability")]
    assert "without a yes on desirability" in messages(root, "verdicts")[0]


def test_a_verdict_judged_against_the_goal_in_an_idea_with_none(tmp_path: Path) -> None:
    root = project(tmp_path)
    (root / GOAL).unlink()
    take_again(root)
    assert found(root) == [
        ("error", "plan-refused", f"{CYCLE}#/planned"),
        ("error", "verdicts", f"{DIRECT}#/verdicts/feasibility"),
        ("error", "verdicts", f"{DIRECT}#/verdicts/viability"),
    ]


def test_a_goal_whose_file_does_not_read_tells_nothing_the_goal_bears_on(tmp_path: Path) -> None:
    root = project(tmp_path)
    (root / GOAL).write_text("revenue: [\n", encoding="utf-8")
    assert found(root) == [("error", "unreadable", GOAL)]


@pytest.mark.parametrize(
    ("change", "step", "said"),
    [
        (drop("boxes", "early-adopters"), "desirability", "needs `early-adopters`"),
        (drop("boxes", "revenue-streams"), "viability", "needs `revenue-streams`"),
        (drop("viability"), "viability", "needs the estimate's inputs"),
        (drop("traction", "first-stage", "target"), "feasibility", "the first stage's target"),
    ],
    ids=["no-early-adopter", "no-revenue-stream", "no-inputs", "no-traction-target"],
)
def test_a_yes_that_still_matches_a_canvas_missing_what_it_needs(
    tmp_path: Path, change: Change, step: str, said: str
) -> None:
    root = project(tmp_path)
    edit(root, DIRECT, change, retake=False)
    assert at(root, "verdicts") == []
    take_again(root)
    assert at(root, "verdicts") == [f"{DIRECT}#/verdicts/{step}"]
    assert said in messages(root, "verdicts")[0]


def test_a_shortlisting_that_still_matches_over_a_stale_verdict(tmp_path: Path) -> None:
    root = project(tmp_path)

    def changed(data: Any) -> None:
        data["boxes"]["problem"][0]["text"] = "Planning takes long"
        data["outcome"]["when"] = "2027-02-20"

    edit(root, DIRECT, changed, retake=False)
    take_again(root, only=(DIRECT, "outcome/fingerprint"))
    assert found(root) == [("error", "verdicts", f"{DIRECT}#/verdicts/desirability/fingerprint")]


def test_a_shortlisting_without_a_yes_on_all_three_steps(tmp_path: Path) -> None:
    root = project(tmp_path)
    edit(root, DIRECT, put("verdicts", "feasibility", "answer", "no"))
    assert found(root) == [("error", "verdicts", f"{DIRECT}#/outcome")]


def test_a_split_into_a_variant_that_does_not_come_from_it(tmp_path: Path) -> None:
    root = project(tmp_path)
    split = {
        "kind": "split",
        "into": ["[canvas:meal-plan--direct]"],
        "by": "A",
        "when": "2026-10-05",
    }
    edit(root, SIDED, put("outcome", split))
    assert found(root) == [("error", "split", f"{SIDED}#/outcome/into/0")]
    edit(root, DIRECT, put("comes-from", "[canvas:meal-plan--two-sided]"))
    assert found(root) == []


SKETCH = f"{IDEA}/variants/sketch/canvas.yaml"


def test_a_variant_comes_from_one_shelved_or_one_split_into_it(tmp_path: Path) -> None:
    root = project(tmp_path)
    edit(root, DIRECT, put("comes-from", "[canvas:meal-plan--two-sided]"))
    assert found(root) == []
    sketch = {
        "pkit_schema": "lean-business:canvas",
        "schema_version": 1,
        "id": "meal-plan--sketch",
        "archetype": "direct",
        "authors": ["A. Founder"],
        "comes-from": "[canvas:meal-plan--two-sided]",
        "boxes": {"customer-segments": [{"id": "meal-plan--sketch--cooks", "text": "Cooks"}]},
    }
    write(root, SKETCH, sketch)
    split = {
        "kind": "split",
        "into": ["[canvas:meal-plan--sketch]"],
        "by": "A",
        "when": "2026-10-05",
    }
    edit(root, SIDED, put("outcome", split))
    assert found(root) == [("error", "comes-from", f"{DIRECT}#/comes-from")]
    assert "split into other variants, not this one" in messages(root, "comes-from")[0]


def test_a_variant_comes_from_one_neither_split_nor_shelved(tmp_path: Path) -> None:
    root = project(tmp_path)
    edit(root, SIDED, put("comes-from", "[canvas:meal-plan--direct]"))
    assert found(root) == [("error", "comes-from", f"{SIDED}#/comes-from")]
    assert "neither split nor shelved" in messages(root, "comes-from")[0]


def test_a_shortlisting_whose_canvas_changed_is_stale(tmp_path: Path) -> None:
    root = project(tmp_path)
    edit(root, DIRECT, put("boxes", "problem", 0, "text", "Planning takes long"), retake=False)
    assert found(root) == [("warning", "stale", f"{DIRECT}#/outcome/fingerprint")]


@pytest.mark.parametrize(
    "change", [put("years", 5), put("currency", "USD")], ids=["its-years", "its-currency"]
)
def test_a_goal_changed_makes_its_shortlisting_stale(tmp_path: Path, change: Change) -> None:
    root = project(tmp_path)
    edit(root, GOAL, change, retake=False)
    assert found(root) == [("warning", "stale", f"{DIRECT}#/outcome/fingerprint")]


@pytest.mark.parametrize(
    "change",
    [put("archetype", "marketplace"), put("sides", ["shops", "cooks"])],
    ids=["its-archetype", "its-sides"],
)
def test_a_verdict_whose_model_changed_is_stale(tmp_path: Path, change: Change) -> None:
    root = project(tmp_path)
    edit(root, SIDED, drop("outcome"), retake=False)
    # A change of model makes the verdict stale before any box changes.
    edit(root, SIDED, change, retake=False)
    assert found(root) == [("warning", "stale", f"{SIDED}#/verdicts/desirability/fingerprint")]
    assert "the model or the boxes it judged" in messages(root, "stale")[0]


def test_a_shortlisting_whose_model_changed_is_stale(tmp_path: Path) -> None:
    root = project(tmp_path)
    edit(root, DIRECT, put("archetype", "multisided"), retake=False)
    assert ("warning", "stale", f"{DIRECT}#/outcome/fingerprint") in found(root)


def test_a_verdict_of_a_variant_with_no_outcome_whose_boxes_changed_is_stale(
    tmp_path: Path,
) -> None:
    root = project(tmp_path)
    edit(root, SIDED, drop("outcome"), retake=False)
    assert found(root) == []
    edit(root, SIDED, put("boxes", "customer-segments", 1, "text", "Grocers"), retake=False)
    assert found(root) == [("warning", "stale", f"{SIDED}#/verdicts/desirability/fingerprint")]


def test_a_fingerprint_of_a_form_the_capability_does_not_know(tmp_path: Path) -> None:
    root = project(tmp_path)
    edit(root, DIRECT, put("outcome", "fingerprint", "form", 2), retake=False)
    assert found(root) == [("error", "fingerprint", f"{DIRECT}#/outcome/fingerprint")]


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d["boxes"]["problem"].extend(
            [
                {
                    "id": f"meal-plan--direct--p{n}",
                    "text": "More",
                    "alternatives": ["meal-plan--direct--paper-lists"],
                }
                for n in (3, 4)
            ]
        ),
        lambda d: d["boxes"]["key-metrics"].pop(),
        put("boxes", "unique-value-proposition", 0, "text", "x" * 121),
    ],
    ids=["four-problems", "two-key-metrics", "a-long-headline"],
)
def test_a_guideline_of_the_book_warns(tmp_path: Path, change: Change) -> None:
    root = project(tmp_path)
    edit(root, DIRECT, change)
    assert kinds(root) == {("warning", "guideline")}


def desirable_sketch(root: Path) -> str:
    """A variant whose desirability has a yes, and which holds no revenue stream."""
    direct = load_file(root, DIRECT)
    boxes = {
        box: [{**entry, "id": entry["id"].replace("--direct--", "--sketch--")} for entry in entries]
        for box, entries in direct["boxes"].items()
        if box in ("customer-segments", "early-adopters", "existing-alternatives")
    }
    boxes["problem"] = [{"id": "meal-plan--sketch--p", "text": "Too long"}]
    boxes["unique-value-proposition"] = [{"id": "meal-plan--sketch--u", "text": "Quick"}]
    rel = f"{IDEA}/variants/sketch/canvas.yaml"
    verdict = {"answer": "yes", "fingerprint": {"form": 1, "sha256": "0" * 64}}
    sketch = {
        "pkit_schema": "lean-business:canvas",
        "schema_version": 1,
        "id": "meal-plan--sketch",
        "archetype": "direct",
        "authors": ["A. Founder"],
        "boxes": boxes,
        "verdicts": {"desirability": {**verdict, "by": "A. Founder", "when": "2026-10-05"}},
    }
    write(root, rel, sketch)
    take_again(root)
    return rel


def test_no_pricing_once_desirability_has_a_yes_warns(tmp_path: Path) -> None:
    root = project(tmp_path)
    rel = desirable_sketch(root)
    assert found(root) == [
        ("warning", "link", f"{rel}#/boxes/problem/0"),
        ("warning", "guideline", f"{rel}#/boxes/revenue-streams"),
        ("warning", "link", f"{rel}#/boxes/unique-value-proposition/0"),
    ]


def test_a_first_sketch_with_blanks_draws_no_guideline(tmp_path: Path) -> None:
    root = project(tmp_path)
    sketch = {
        "pkit_schema": "lean-business:canvas",
        "schema_version": 1,
        "id": "meal-plan--sketch",
        "archetype": "direct",
        "authors": ["A. Founder"],
        "boxes": {"customer-segments": [{"id": "meal-plan--sketch--cooks", "text": "Cooks"}]},
    }
    write(root, f"{IDEA}/variants/sketch/canvas.yaml", sketch)
    assert found(root) == []


@pytest.mark.parametrize(
    ("change", "where"),
    [
        (drop("boxes", "problem", 1, "alternatives"), "/boxes/problem/1"),
        (
            put("boxes", "problem", 1, "alternatives", 0, "meal-plan--direct--x"),
            "/boxes/problem/1/alternatives/0",
        ),
        (drop("boxes", "solution", 0, "problem"), "/boxes/solution/0"),
        (
            put("boxes", "unique-value-proposition", 0, "problem", "meal-plan--direct--x"),
            "/boxes/unique-value-proposition/0/problem",
        ),
        (drop("boxes", "early-adopters", 0, "triggers"), "/boxes/early-adopters/0"),
        (drop("boxes", "key-metrics", 0, "step"), "/boxes/key-metrics/0"),
    ],
    ids=[
        "a-problem-with-no-alternative",
        "a-problem-naming-an-alternative-not-held",
        "a-solution-with-no-problem",
        "a-value-proposition-naming-a-problem-not-held",
        "an-early-adopter-with-no-trigger",
        "a-key-metric-with-no-step",
    ],
)
def test_a_link_between_entries_missing_or_dangling_warns(
    tmp_path: Path, change: Change, where: str
) -> None:
    root = project(tmp_path)
    edit(root, DIRECT, change)
    assert found(root) == [("warning", "link", f"{DIRECT}#{where}")]


def test_an_untested_assumption_whose_entry_has_gone(tmp_path: Path) -> None:
    root = project(tmp_path)
    untested = {
        "id": "meal-plan--direct--wasted",
        "statement": "Households throw food away",
        "source": {"entry": "meal-plan--direct--gone"},
        "kind": "desirability",
        "rank": 3,
    }
    edit(root, ASSUMPTIONS, lambda d: d["assumptions"].append(untested))
    assert found(root) == [
        ("warning", "assumption-source", f"{ASSUMPTIONS}#/assumptions/2/source/entry")
    ]
    # A tested one keeps its link to an entry its experiment refuted, as the method removes it.
    edit(root, ASSUMPTIONS, put("assumptions", 0, "source", "entry", "meal-plan--direct--gone"))
    assert at(root, "assumption-source") == [f"{ASSUMPTIONS}#/assumptions/2/source/entry"]


# --- an experiment ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "change",
    [
        put("learn", "Something else"),
        put("declared", "by", "B. Partner"),
        put("declared", "when", "2026-11-01"),
        put("declared", "rested-on", "when", "2026-10-07"),
    ],
    ids=["a-field", "who-declared-it", "the-day-it-was-declared", "what-it-rested-on"],
)
def test_a_declared_field_changed_since(tmp_path: Path, change: Change) -> None:
    root = project(tmp_path)
    edit(root, INTERVIEWS, change, retake=False)
    assert at(root, "declaration-changed") == [f"{INTERVIEWS}#/declared/fingerprint"]


def declare_again(root: Path, rel: str) -> None:
    """Take the declaration's fingerprint again over the experiment as its file stands, as
    a command that declared it so would have."""
    data = load_file(root, rel)
    data["declared"]["fingerprint"] = fingerprint.of_declaration(data).as_data()
    write(root, rel, data)


def test_a_shortlisting_given_again_after_a_declaration_leaves_it_standing(
    tmp_path: Path,
) -> None:
    root = project(tmp_path)
    edit(root, DIRECT, put("outcome", "when", "2027-01-10"), retake=False)
    assert found(root) == []


def test_a_declaration_rests_on_the_shortlisting_that_stood_on_its_day(tmp_path: Path) -> None:
    root = project(tmp_path)
    # Shortlisted again between the two declarations, so the later rests on it.
    edit(root, DIRECT, put("outcome", "when", "2026-11-15"), retake=False)
    assert found(root) == [("error", "declaration-refused", f"{LANDING}#/declared")]
    said = messages(root, "declaration-refused")[0]
    assert "the canvas keeps one recorded on 2026-11-15" in said
    assert "the declaration names one recorded on 2026-10-08" in said
    edit(root, LANDING, put("declared", "rested-on", "when", "2026-11-15"), retake=False)
    declare_again(root, LANDING)
    assert found(root) == []


def test_a_declaration_resting_on_another_shortlisting_than_the_one_kept(tmp_path: Path) -> None:
    root = project(tmp_path)
    other = {"form": 1, "sha256": "1" * 64}
    edit(root, INTERVIEWS, put("declared", "rested-on", "fingerprint", other), retake=False)
    declare_again(root, INTERVIEWS)
    assert found(root) == [("error", "declaration-refused", f"{INTERVIEWS}#/declared")]


@pytest.mark.parametrize(
    ("change", "said"),
    [
        (put("end", "2026-12-26"), "holds 15 days, more than 14"),
        (put("end", "2026-12-11"), "ends on 2026-12-11, before it starts"),
        (
            put("declared", "when", "2026-12-13"),
            "starts on 2026-12-12, before the day it was declared",
        ),
        (drop("estimates"), "without an estimate"),
        (drop("control"), "without `control`"),
        (put("expected", "range", "low", 0.09), "runs from 0.09 to 0.08, its low above its high"),
    ],
    ids=[
        "a-box-over-14-days",
        "a-box-ending-before-it-starts",
        "a-start-before-declaring",
        "no-estimate",
        "no-control",
        "a-range-low-above-high",
    ],
)
def test_a_declaration_its_gate_refuses(tmp_path: Path, change: Change, said: str) -> None:
    root = project(tmp_path)
    edit(root, LANDING, change)
    assert found(root) == [("error", "declaration-refused", f"{LANDING}#/declared")]
    assert said in messages(root, "declaration-refused")[0]


def test_a_declaration_after_its_cycles_window_ended(tmp_path: Path) -> None:
    root = project(tmp_path)

    def late(data: Any) -> None:
        data["declared"]["when"] = "2027-02-13"
        data["start"], data["end"] = "2027-02-14", "2027-02-20"
        data["result"]["when"], data["decision"]["when"] = "2027-02-21", "2027-02-22"

    edit(root, LANDING, late)
    assert kinds(root) == {("error", "declaration-refused"), ("warning", "time-box")}
    assert (
        "after its cycle's window ended on 2027-02-12" in messages(root, "declaration-refused")[0]
    )


def test_a_declaration_on_a_variant_shelved_before_it(tmp_path: Path) -> None:
    root = project(tmp_path)
    shelved = {"kind": "shelved", "reason": "No", "by": "A", "when": "2026-12-01"}
    edit(root, DIRECT, put("outcome", shelved))
    assert at(root, "declaration-refused") == [f"{LANDING}#/declared"]
    assert kinds(root) == {("error", "declaration-refused"), ("error", "review-refused")}


def test_a_declaration_resting_on_a_shortlisting_recorded_after_it(tmp_path: Path) -> None:
    root = project(tmp_path)
    edit(root, DIRECT, put("outcome", "when", "2026-11-05"))
    assert found(root) == [("error", "declaration-refused", f"{INTERVIEWS}#/declared")]


def test_what_is_recorded_on_an_experiment_never_declared(tmp_path: Path) -> None:
    root = project(tmp_path)
    edit(root, INTERVIEWS, drop("declared"))
    assert found(root) == [
        ("error", "undeclared", f"{INTERVIEWS}#/decision"),
        ("error", "undeclared", f"{INTERVIEWS}#/result"),
    ]


@pytest.mark.parametrize(
    "change",
    [
        drop("result"),
        put("result", "when", "2027-01-06"),
        recorded_on("2026-12-19"),
    ],
    ids=["no-result", "a-result-after-the-decision", "decided-before-the-box-ended"],
)
def test_a_decision_its_gate_refuses(tmp_path: Path, change: Change) -> None:
    root = project(tmp_path)
    edit(root, LANDING, change)
    assert kinds(root) == {("error", "decision-refused")}


def test_a_generative_experiment_is_decided_early_once_its_stopping_rule_is_reached(
    tmp_path: Path,
) -> None:
    root = project(tmp_path)

    edit(root, INTERVIEWS, recorded_on("2026-11-10"))
    assert found(root) == [("error", "decision-refused", f"{INTERVIEWS}#/decision")]
    edit(root, INTERVIEWS, put("stopped", {"by": "A. Founder", "when": "2026-11-09"}))
    assert found(root) == []


@pytest.mark.parametrize(
    ("when", "said"),
    [
        ("2026-11-02", "reached on 2026-11-02, before its time box started"),
        ("2026-11-17", "reached on 2026-11-17, after its time box ended on 2026-11-16"),
    ],
    ids=["before-the-box", "after-the-box"],
)
def test_a_stopping_rule_reached_outside_its_time_box(tmp_path: Path, when: str, said: str) -> None:
    root = project(tmp_path)
    edit(root, INTERVIEWS, put("stopped", {"by": "A. Founder", "when": when}))
    assert found(root) == [("error", "stop-refused", f"{INTERVIEWS}#/stopped")]
    assert said in messages(root, "stop-refused")[0]


def test_an_early_decision_rests_on_a_stopping_rule_reached_within_the_box(
    tmp_path: Path,
) -> None:
    root = project(tmp_path)
    edit(root, INTERVIEWS, recorded_on("2026-11-10"))
    edit(root, INTERVIEWS, put("stopped", {"by": "A. Founder", "when": "2026-11-02"}))
    assert kinds(root) == {("error", "stop-refused"), ("error", "decision-refused")}


def test_a_result_spoiled_only_by_a_suspension_its_time_box_ran_through(tmp_path: Path) -> None:
    root = project(tmp_path)
    edit(root, INTERVIEWS, put("result", "spoiled", True))
    assert found(root) == [("error", "result-refused", f"{INTERVIEWS}#/result/spoiled")]
    edit(root, INTERVIEWS, put("result", "spoiled", False))
    edit(root, LANDING, put("result", "spoiled", True))
    assert found(root) == []


def test_a_time_box_a_suspension_moved_is_decided_after_its_moved_end(tmp_path: Path) -> None:
    root = project(tmp_path)

    def moved(data: Any) -> None:
        data["declared"]["when"] = "2026-12-15"
        data["start"], data["end"] = "2026-12-22", "2027-01-04"

    edit(root, LANDING, moved)
    assert found(root) == [("error", "decision-refused", f"{LANDING}#/decision")]
    assert "ends on 2027-01-16" in messages(root, "decision-refused")[0]
    edit(root, LANDING, recorded_on("2027-01-17"))
    assert found(root) == []


def test_a_time_box_outside_its_cycles_window(tmp_path: Path) -> None:
    root = project(tmp_path)

    def early(data: Any) -> None:
        data["declared"]["when"] = "2026-10-24"
        data["start"], data["end"] = "2026-10-25", "2026-11-07"

    edit(root, LANDING, early)
    assert found(root) == [("warning", "time-box", f"{LANDING}#/start")]


# --- a cycle ------------------------------------------------------------------------------------


def test_an_experiment_on_a_variant_its_cycle_does_not_explore(tmp_path: Path) -> None:
    root = project(tmp_path)
    sided = {
        "pkit_schema": "lean-business:assumptions",
        "schema_version": 1,
        "assumptions": [
            {
                "id": "meal-plan--two-sided--grocers-pay",
                "statement": "Grocers pay",
                "source": {"input": "price", "side": "shops"},
                "kind": "viability",
                "rank": 1,
            }
        ],
    }
    write(root, f"{IDEA}/variants/two-sided/assumptions.yaml", sided)
    edit(root, LANDING, put("assumption", "[assumptions:meal-plan--two-sided--grocers-pay]"))
    assert at(root, "cycle-variants") == [f"{LANDING}#/assumption"]
    assert kinds(root) == {("error", "cycle-variants"), ("error", "declaration-refused")}


def test_a_key_result_for_a_variant_the_cycle_does_not_explore(tmp_path: Path) -> None:
    root = project(tmp_path)
    result = {"variant": "[canvas:meal-plan--two-sided]", "metric": "acquisition", "target": 5}

    def more(data: Any) -> None:
        data["objective"]["key-results"].append(result)
        data["review"]["reached"].append(0)

    edit(root, CYCLE, more)
    assert found(root) == [("error", "cycle-variants", f"{CYCLE}#/objective/key-results/1/variant")]


def test_a_variant_explored_without_a_key_result(tmp_path: Path) -> None:
    root = project(tmp_path)
    edit(root, CYCLE, lambda d: d["variants"].append("[canvas:meal-plan--two-sided]"))
    assert found(root) == [("error", "cycle-variants", f"{CYCLE}#/objective/key-results")]


@pytest.mark.parametrize(
    "change",
    [put("window", "days", 80), put("planned", "by", "B. Partner")],
    ids=["its-window", "who-planned-it"],
)
def test_a_plan_changed_since_its_fingerprint(tmp_path: Path, change: Change) -> None:
    root = project(tmp_path)
    edit(root, CYCLE, change, retake=False)
    assert found(root) == [("error", "plan-changed", f"{CYCLE}#/planned/fingerprint")]


def test_a_plan_last_changed_after_its_window_started(tmp_path: Path) -> None:
    root = project(tmp_path)
    edit(root, CYCLE, put("planned", "when", "2026-11-02"))
    assert found(root) == [("error", "plan-refused", f"{CYCLE}#/planned")]
    assert "after its window started on 2026-11-01" in messages(root, "plan-refused")[0]
    # Changed on the window's first day, it may have come before the window started.
    edit(root, CYCLE, put("planned", "when", "2026-11-01"))
    assert found(root) == []


SECOND = f"{IDEA}/cycles/second.yaml"


def second_cycle(root: Path, start: str, *, review: str | None, planned: str | None = None) -> None:
    """A second cycle of the idea, its window from `start`, planned on `planned` or on its
    start, and decided on `review` where it is given."""
    second = load_file(root, CYCLE)
    second["id"] = "meal-plan--second"
    second["window"]["start"] = start
    second["planned"]["when"] = second["planned"]["first"]["when"] = planned or start
    del second["suspensions"]
    if review is None:
        second.pop("review", None)
    else:
        second["review"]["when"] = review
    write(root, SECOND, second)
    take_again(root)


def test_two_undecided_cycles_of_one_idea(tmp_path: Path) -> None:
    root = project(tmp_path)
    edit(root, CYCLE, drop("review"))
    second_cycle(root, "2027-03-01", review=None)
    assert found(root) == [
        ("error", "one-cycle", CYCLE),
        ("error", "one-cycle", SECOND),
        ("error", "plan-refused", f"{SECOND}#/planned/first"),
    ]


def test_two_cycles_whose_windows_overlap(tmp_path: Path) -> None:
    root = project(tmp_path)
    second_cycle(root, "2027-02-10", planned="2027-02-15", review="2027-05-20")
    assert found(root) == [("error", "one-cycle", SECOND)]
    edit(root, SECOND, put("window", "start", "2027-02-16"))
    assert found(root) == []


def test_the_next_cycle_planned_before_the_last_was_decided(tmp_path: Path) -> None:
    root = project(tmp_path)
    second_cycle(root, "2027-02-20", planned="2027-02-14", review="2027-05-25")
    assert found(root) == [("error", "plan-refused", f"{SECOND}#/planned/first")]
    assert "decided only on 2027-02-15" in messages(root, "plan-refused")[0]
    # Planned at the last cycle's review, the same day, it may have come after it.
    edit(root, SECOND, put("planned", "first", "when", "2027-02-15"))
    edit(root, SECOND, put("planned", "when", "2027-02-15"))
    assert found(root) == []


@pytest.mark.parametrize(
    "change",
    [
        put("suspensions", 0, "when", "2026-12-19"),
        lambda d: d["suspensions"].append(
            {
                "reason": "Ill",
                "first-day": "2026-11-17",
                "by": "A. Founder",
                "when": "2026-11-17",
                "resumed": {"day": "2026-11-18", "by": "A. Founder", "when": "2026-11-18"},
            }
        ),
    ],
    ids=["first-day-after-recording", "over-recorded-work"],
)
def test_a_suspension_that_breaks_its_rules(tmp_path: Path, change: Change) -> None:
    root = project(tmp_path)
    edit(root, CYCLE, change)
    assert kinds(root) == {("error", "suspension")}


def test_a_suspension_recorded_after_the_cycle_was_decided(tmp_path: Path) -> None:
    root = project(tmp_path)
    edit(root, CYCLE, put("suspensions", 0, "when", "2027-02-16"))
    assert found(root) == [("error", "suspension", f"{CYCLE}#/suspensions/0")]
    assert "after the cycle was decided on 2027-02-15" in messages(root, "suspension")[0]


def landing_page_boxed_after_the_suspension(root: Path) -> None:
    """Moves the landing page's time box to start after the suspension's first day, so the
    suspension moves it to end on 2027-01-18, after its decision on 2027-01-05."""

    def moved(data: Any) -> None:
        data["declared"]["when"] = "2026-12-15"
        data["start"], data["end"] = "2026-12-22", "2027-01-04"

    edit(root, LANDING, moved)


def test_an_act_is_held_to_its_gate_as_the_suspensions_stood_on_its_day(tmp_path: Path) -> None:
    root = project(tmp_path)
    landing_page_boxed_after_the_suspension(root)
    # Recorded on 2026-12-21, the suspension had moved the time box by the decision's day.
    assert found(root) == [("error", "decision-refused", f"{LANDING}#/decision")]
    # The review comes after it, so reads the window it moved, to 2027-02-12.
    edit(root, LANDING, put("decision", "when", "2027-01-19"))
    edit(root, CYCLE, put("review", "when", "2027-02-11"))
    assert found(root) == [("error", "review-refused", f"{CYCLE}#/review")]


@pytest.mark.parametrize("recorded", ["2027-01-06", "2027-01-05"], ids=["later", "the-same-day"])
def test_a_suspension_recorded_late_contradicts_no_act_already_recorded(
    tmp_path: Path, recorded: str
) -> None:
    root = project(tmp_path)
    landing_page_boxed_after_the_suspension(root)
    # Recorded once the landing page was decided, the suspension would say its time box had
    # not ended when it was decided. On the decision's own day, which came first cannot be
    # told, so the break is the suspension's too (DEC-002 point 12).
    edit(root, CYCLE, put("suspensions", 0, "when", recorded))
    edit(root, CYCLE, put("suspensions", 0, "resumed", "when", recorded))
    assert found(root) == [("error", "suspension", f"{CYCLE}#/suspensions/0")]
    assert (
        "the decision of `meal-plan--landing-page`, recorded on 2027-01-05"
        in (messages(root, "suspension")[0])
    )


def test_a_late_suspension_never_reopens_a_window_past_the_goal_set(tmp_path: Path) -> None:
    root = project(tmp_path)
    # Set once the cycle's window, moved by its suspension to 2027-02-12, ended.
    edit(root, GOAL, put("when", "2027-02-13"))
    assert found(root) == []
    late = {
        "reason": "Ill",
        "first-day": "2027-01-20",
        "by": "A. Founder",
        "when": "2027-02-14",
        "resumed": {"day": "2027-01-22", "by": "A. Founder", "when": "2027-02-14"},
    }
    edit(root, CYCLE, lambda d: d["suspensions"].append(late))
    assert found(root) == [("error", "suspension", f"{CYCLE}#/suspensions/1")]
    assert "the goal set, recorded on 2027-02-13" in messages(root, "suspension")[0]


@pytest.mark.parametrize(
    "change",
    [
        put("review", "winning", "[canvas:meal-plan--two-sided]"),
        lambda d: d["review"]["reached"].append(1),
        put("review", "decision", "pivot"),
        put("review", "when", "2027-02-12"),
    ],
    ids=[
        "a-winner-not-explored",
        "a-reach-for-no-key-result",
        "a-pivot-on-no-experiment",
        "before-the-window-ended",
    ],
)
def test_a_review_its_gate_refuses(tmp_path: Path, change: Change) -> None:
    root = project(tmp_path)
    edit(root, CYCLE, change)
    assert kinds(root) == {("error", "review-refused")}


def test_a_pivot_rests_on_a_decided_experiment(tmp_path: Path) -> None:
    root = project(tmp_path)
    edit(root, CYCLE, put("review", "decision", "pivot"))
    edit(root, CYCLE, put("review", "evidence", ["[experiment:meal-plan--first-interviews]"]))
    assert found(root) == []
    edit(root, INTERVIEWS, drop("decision"))
    assert found(root) == [("error", "review-refused", f"{CYCLE}#/review/evidence")]


def test_a_review_under_an_ongoing_suspension(tmp_path: Path) -> None:
    root = project(tmp_path)
    edit(root, CYCLE, drop("suspensions", 0, "resumed"))
    assert kinds(root) == {("error", "review-refused"), ("error", "suspension")}
    assert "has no end yet" in messages(root, "review-refused")[0]


def test_a_perseverance_with_a_winner_that_missed_the_objective(tmp_path: Path) -> None:
    root = project(tmp_path)
    edit(root, CYCLE, put("review", "reached", 0, 30))
    assert found(root) == [("warning", "persevere-missed", f"{CYCLE}#/review/decision")]


# --- the goal -----------------------------------------------------------------------------------


def test_the_goal_set_while_a_cycle_was_planned_running_or_suspended(tmp_path: Path) -> None:
    root = project(tmp_path)
    edit(root, GOAL, put("when", "2026-11-15"))
    assert found(root) == [("error", "goal-changed", GOAL)]
    edit(root, GOAL, put("when", "2027-02-13"))
    assert found(root) == []


def test_the_goal_set_on_the_day_a_cycle_was_first_planned(tmp_path: Path) -> None:
    root = project(tmp_path)
    # Days have no order within them, so the goal may have been set before the planning.
    edit(root, GOAL, put("when", "2026-10-20"))
    assert found(root) == []
    edit(root, GOAL, put("when", "2026-10-21"))
    assert found(root) == [("error", "goal-changed", GOAL)]


def test_the_goal_held_still_from_the_first_planning_though_the_plan_changed(
    tmp_path: Path,
) -> None:
    root = project(tmp_path)
    edit(root, CYCLE, put("planned", "when", "2026-10-25"))
    edit(root, GOAL, put("when", "2026-10-22"))
    assert found(root) == [("error", "goal-changed", GOAL)]


def test_a_goal_names_its_currency(tmp_path: Path) -> None:
    root = project(tmp_path)
    edit(root, GOAL, drop("currency"))
    # The shape requires it; the check reads a goal without one as it reads any other.
    assert found(root) == []
    assert data_found(root) == [("error", GOAL)]


# --- the clock ----------------------------------------------------------------------------------

SCRIPTS = CAPABILITIES / "lean-business/scripts"

#: What reads the clock or the environment: the clock's module, and the names that reach
#: either, such as `date.today` or `os.environ`.
CLOCK_MODULE = "time"
CLOCK_NAMES = {"today", "now", "utcnow", "environ", "getenv", "localtime", "gmtime"}


def test_the_check_reads_no_clock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = project(tmp_path)

    def stopped() -> float:
        raise AssertionError("the check read the clock")

    monkeypatch.setattr(time, "time", stopped)
    assert checks.check(root).findings == []


def _clock_reads(path: Path) -> list[str]:
    """Each place in the module at `path` that names the clock or the environment."""
    found: list[str] = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        named: list[str] = []
        if isinstance(node, ast.Attribute):
            named = [node.attr]
        elif isinstance(node, ast.Name):
            named = [node.id]
        elif isinstance(node, ast.Import):
            named = [alias.name for alias in node.names if alias.name == CLOCK_MODULE]
        elif isinstance(node, ast.ImportFrom):
            named = [alias.name for alias in node.names]
            if node.module == CLOCK_MODULE:
                named.append(CLOCK_MODULE)
        line = getattr(node, "lineno", 0)
        found += [
            f"{path.name}:{line} {name}"
            for name in named
            if name in CLOCK_NAMES or name == CLOCK_MODULE
        ]
    return found


def test_no_module_of_the_check_names_the_clock_or_the_environment() -> None:
    """COR-055 point 2: a gate and a reading take the day from their caller, and nothing
    the check runs reads the clock or an environment variable."""
    modules = [SCRIPTS / "check.py", *sorted((SCRIPTS / "_lib").glob("*.py"))]
    assert len(modules) > 10
    assert [read for path in modules for read in _clock_reads(path)] == []


# --- through pkit validate ----------------------------------------------------------------------


@pytest.mark.process(
    "the validator's end-to-end test: `pkit validate` finds the `lean-business:check` member, "
    "starts its script as a process of its own and reads its document and its exit"
)
def test_it_is_the_check_member_of_pkit_validate(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path
) -> None:
    repo = make_adopter_repo(capabilities=("lean-business",))
    script = repo.root / ".pkit/capabilities/lean-business/scripts/check.py"
    body = script.read_text(encoding="utf-8").split("\n", 1)[1]
    script.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
    shutil.copytree(FIXTURE / "lean-business", repo.root / "lean-business")
    only = ["--color", "never", "validate", "--only", "lean-business:check"]
    result = CliRunner().invoke(main, only)
    assert result.exit_code == 0, result.output
    assert "lean-business:check" in result.output
    edit(repo.root, INTERVIEWS, put("learn", "Something else"), retake=False)
    result = CliRunner().invoke(main, only)
    assert result.exit_code == 1, result.output
    assert "declaration-changed" in result.output
