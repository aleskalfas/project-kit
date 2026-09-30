"""software-analysis: a number the default branch took first (#887).

`pkit analysis check-numbers` held to software-analysis DEC-001 point 3 — when
two lines of work number a new artefact the same, the first to reach the
default branch keeps the number and the other renumbers before merging — and
to ADR-058 point 7: it reads a base, so it answers about a change, not the
tree, and is a query command of its own rather than a member of `pkit
validate`. Like the friction change check, it fails when its base names no
commit or shares no history with HEAD, and reports an outdated base without
failing on it.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from project_kit.cli import main
from project_kit.friction_check import BASE_ENV
from tests.adopter_repo import AdopterRepo, MakeAdopterRepo
from tests.analysis_repo import (
    CAPABILITY,
    MAIN,
    NUMBERS,
    USE_CASES,
    VALIDATE,
    fill,
    installed,
    load,
    run_script,
    seed,
    stamped,
)


@pytest.fixture
def project(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    return installed(make_adopter_repo, monkeypatch)


def numbers(repo: AdopterRepo, *args: str) -> subprocess.CompletedProcess[str]:
    """`pkit analysis check-numbers …`, run as the dispatcher runs it."""
    return run_script(repo, NUMBERS, *args)


def document(completed: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    return json.loads(completed.stdout)


def _main_took_ours(repo: AdopterRepo) -> str:
    """main numbers UC-002 after `topic` left it, and `topic` numbers a use case UC-002
    too, before seeing main's; `topic` also moves the use case it inherited into an area.
    Returns this branch's UC-002."""
    stamped(repo, "actor", "tester")
    stamped(repo, "use-case", "one", "--actor", "ACT-tester")
    repo.commit("UC-001")
    repo.checkout("topic", create=True)
    repo.checkout(MAIN)
    stamped(repo, "use-case", "two", "--actor", "ACT-tester")
    repo.commit("UC-002 on main")
    repo.checkout("topic")
    template = (repo.root / USE_CASES / "UC-001-one.md").read_text(encoding="utf-8")
    ours = f"{USE_CASES}/UC-002-mine.md"
    repo.write({ours: template.replace("UC-001", "UC-002")})
    (repo.root / USE_CASES / "core").mkdir()
    repo.git("mv", f"{USE_CASES}/UC-001-one.md", f"{USE_CASES}/core/UC-001-one.md")
    return ours


# --- where it is registered -------------------------------------------------------------------


def test_it_is_a_query_command_and_not_a_validator(project: AdopterRepo) -> None:
    package = load((CAPABILITY / "package.yaml").read_text(encoding="utf-8"))
    leaf = package["commands"]["check-numbers"]
    assert (leaf["script"], leaf["query-contract"]) == ("scripts/check-numbers.py", True)
    assert package["validators"] == {"artefacts": {"command": "validate"}}
    result = CliRunner().invoke(main, ["analysis", "--help"])
    assert result.exit_code == 0, result.output
    assert "check-numbers " in result.output


# --- the comparison (DEC-001 point 3) ---------------------------------------------------------


def test_a_number_the_default_branch_took_first_fails(project: AdopterRepo) -> None:
    ours = _main_took_ours(project)
    completed = numbers(project, "--base", MAIN, "--json")
    assert completed.returncode == 1, completed.stderr
    answer = document(completed)
    assert answer["base"]["ref"] == MAIN and answer["base"]["outdated"] is True
    assert answer["summary"][0].startswith("numbers: compared with main (")
    outdated, collision = answer["findings"]
    assert outdated["severity"] == "report"
    assert outdated["message"].startswith("outdated base: the base main is at ")
    assert "which is not an ancestor of HEAD" in outdated["message"]
    # The use case moved into an area is no collision; the one numbered in parallel is.
    assert collision == {
        "severity": "error",
        "location": ours,
        "message": (
            f"UC-002 is numbered on main too, for {USE_CASES}/UC-002-two.md, since this branch "
            "left it: the first to reach the default branch keeps the number, so renumber this "
            "use case before merging — `pkit analysis new` gives the next free one (DEC-001 "
            "point 3)"
        ),
    }
    read_view = numbers(project, "--base", MAIN)
    assert read_view.returncode == 1
    assert f"  error  {ours}\n" in read_view.stdout

    # Once main is merged in, it is contained: nothing to collide with here, and the two
    # files holding one id are the validator's duplicate.
    project.commit("topic's use case")
    project.git("merge", "-q", "--no-edit", MAIN)
    merged = numbers(project, "--base", MAIN, "--json")
    assert merged.returncode == 0, merged.stderr
    assert document(merged)["base"]["outdated"] is False
    assert document(merged)["summary"][0].startswith("numbers: this branch contains main (")
    fill(project)
    validated = json.loads(run_script(project, VALIDATE, "--json").stdout)
    assert [f["message"].split(":")[0] for f in validated["findings"]] == [
        f"the id UC-002 is also held by {USE_CASES}/UC-002-mine.md"
    ]


# --- an artefact is known by its id, not its path ---------------------------------------------


def _left_main(repo: AdopterRepo) -> None:
    """An actor and UC-001 on main, and the branch `topic` leaving main there."""
    stamped(repo, "actor", "tester")
    stamped(repo, "use-case", "one", "--actor", "ACT-tester")
    repo.commit("UC-001")
    repo.checkout("topic", create=True)


def test_an_id_moved_within_the_branch_is_no_collision(project: AdopterRepo) -> None:
    """UC-001 moved into an area here, and elsewhere on main, while main numbered on:
    the merge-base held UC-001, so neither side took it."""
    _left_main(project)
    project.rename(f"{USE_CASES}/UC-001-one.md", f"{USE_CASES}/core/UC-001-one.md")
    project.checkout(MAIN)
    project.rename(f"{USE_CASES}/UC-001-one.md", f"{USE_CASES}/other/UC-001-one.md")
    stamped(project, "use-case", "two", "--actor", "ACT-tester")
    project.commit("UC-002 on main")
    project.checkout("topic")
    completed = numbers(project, "--base", MAIN, "--json")
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert [f["severity"] for f in document(completed)["findings"]] == ["report"]


def test_two_branches_stamping_the_same_slug_at_the_same_path_collide(
    project: AdopterRepo,
) -> None:
    """One path, two artefacts: each line of work took UC-002 for its own export."""
    _left_main(project)
    stamped(project, "use-case", "export", "--actor", "ACT-tester", "--path", "src/run.py")
    project.commit("UC-002 on topic")
    project.checkout(MAIN)
    stamped(project, "use-case", "export", "--actor", "ACT-tester")
    project.commit("UC-002 on main")
    project.checkout("topic")
    ours = f"{USE_CASES}/UC-002-export.md"
    completed = numbers(project, "--base", MAIN, "--json")
    assert completed.returncode == 1, completed.stderr
    _outdated, collision = document(completed)["findings"]
    assert (collision["severity"], collision["location"]) == ("error", ours)
    assert collision["message"].startswith(f"UC-002 is numbered on main too, for {ours}, since ")


def test_a_stacked_branch_whose_parent_squash_merged_is_no_collision(
    project: AdopterRepo,
) -> None:
    """`child` stacked on `parent`, which numbered UC-002; `child` moved it into an area
    and numbered UC-003. `parent` squash-merged: main took UC-002 under a commit of
    its own, but its file is, byte for byte, the version `parent` wrote — this
    branch's own work landed, not another line of work's number."""
    _left_main(project)
    project.checkout("parent", create=True)
    stamped(project, "use-case", "two", "--actor", "ACT-tester")
    project.commit("UC-002 on parent")
    project.checkout("child", create=True)
    project.rename(f"{USE_CASES}/UC-002-two.md", f"{USE_CASES}/area/UC-002-two.md")
    stamped(project, "use-case", "three", "--actor", "ACT-tester")
    project.commit("UC-003 on child")
    project.checkout(MAIN)
    project.squash_merge("parent")
    project.checkout("child")
    completed = numbers(project, "--base", MAIN, "--json")
    assert completed.returncode == 0, completed.stdout + completed.stderr
    ((outdated,),) = [document(completed)["findings"]]
    assert outdated["severity"] == "report"
    # Another line of work taking UC-003 on main meanwhile still collides.
    project.checkout(MAIN)
    stamped(project, "use-case", "theirs", "--actor", "ACT-tester")
    project.commit("UC-003 on main")
    project.checkout("child")
    completed = numbers(project, "--base", MAIN, "--json")
    assert completed.returncode == 1
    assert [f["location"] for f in document(completed)["findings"][1:]] == [
        f"{USE_CASES}/UC-003-three.md"
    ]


def test_a_stale_base_is_reported_as_the_friction_change_check_reports_it(
    project: AdopterRepo,
) -> None:
    """main moved on after this branch left it, taking no number: reported, never
    failed, with the same base as `pkit friction check` gives."""
    _left_main(project)
    stamped(project, "use-case", "two", "--actor", "ACT-tester")
    project.commit("UC-002 on topic")
    project.checkout(MAIN)
    stamped(project, "term", "sandbox")
    project.commit("a term on main")
    project.checkout("topic")
    completed = numbers(project, "--base", MAIN, "--json")
    assert completed.returncode == 0, completed.stderr
    answer = document(completed)
    ((finding,),) = [answer["findings"]]
    assert finding["severity"] == "report"
    assert finding["message"].startswith(
        f"outdated base: the base main is at {answer['base']['tip'][:12]}"
    )
    friction = subprocess.run(
        ["pkit", "friction", "check", "--base", MAIN, "--json"],
        cwd=project.root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert json.loads(friction.stdout)["base"] == answer["base"]


def test_a_branch_containing_its_base_has_nothing_to_collide_with(project: AdopterRepo) -> None:
    seed(project)
    project.commit("seeded")
    completed = numbers(project, "--base", MAIN, "--json")
    assert completed.returncode == 0, completed.stderr
    assert document(completed)["findings"] == []


def test_a_working_tree_numbering_nothing_needs_no_base(project: AdopterRepo) -> None:
    stamped(project, "actor", "tester")
    completed = numbers(project, "--base", "origin/main", "--json")
    assert completed.returncode == 0, completed.stderr
    assert document(completed) == {
        "schema_version": 1,
        "base": None,
        "summary": [
            "numbers: no use case or journey is numbered here; nothing to compare with origin/main."
        ],
        "findings": [],
    }


# --- the base: fails when it cannot compare, as the friction change check does -------------


@pytest.mark.parametrize(
    ("base", "refusal"),
    [
        ("origin/main", "the base 'origin/main' does not resolve to a commit in this repository"),
        ("-x", "the base '-x' is not a revision name."),
    ],
)
def test_a_base_that_names_no_commit_fails(project: AdopterRepo, base: str, refusal: str) -> None:
    seed(project)
    for json_flag in ((), ("--json",)):
        completed = numbers(project, f"--base={base}", *json_flag)
        assert completed.returncode == 1
        assert completed.stdout == ""
        assert completed.stderr.startswith(f"error: {refusal}")


def test_a_base_sharing_no_history_with_head_fails(project: AdopterRepo) -> None:
    seed(project)
    project.git("checkout", "-q", "--orphan", "unrelated")
    project.commit("a history of its own")
    completed = numbers(project, "--base", MAIN)
    assert completed.returncode == 1
    assert "HEAD and the base 'main' share no history to compare" in completed.stderr


def test_the_base_is_the_variable_else_origin_main(
    project: AdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed(project)
    project.commit("seeded")
    unnamed = numbers(project)
    assert unnamed.returncode == 1
    assert "the base 'origin/main' does not resolve" in unnamed.stderr
    monkeypatch.setenv(BASE_ENV, MAIN)
    named = numbers(project, "--json")
    assert named.returncode == 0, named.stderr
    assert document(named)["base"]["ref"] == MAIN
