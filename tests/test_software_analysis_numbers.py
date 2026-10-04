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
    CONFIG,
    MAIN,
    NUMBERS,
    USE_CASES,
    VALIDATE,
    fill,
    installed,
    load,
    prepare,
    prepare_seeded,
    run_script,
    stamped,
)


@pytest.fixture
def project(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    return installed(make_adopter_repo, monkeypatch)


@pytest.fixture
def seeded(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    """The project with the seed stamped and filled (`prepare_seeded`)."""
    return installed(make_adopter_repo, monkeypatch, then=prepare_seeded)


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


# Slow by design: three stamps, three number checks and the check, each starting `pkit` processes.
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


# Slow: two stamps, built once per session; the first test to ask pays it in its setup.
def _leave_main(repo: AdopterRepo) -> None:
    """`prepare`, then an actor and UC-001 on main, and the branch `topic` leaving main
    there."""
    prepare(repo)
    stamped(repo, "actor", "tester")
    stamped(repo, "use-case", "one", "--actor", "ACT-tester")
    repo.commit("UC-001")
    repo.checkout("topic", create=True)


@pytest.fixture
def branched(
    make_adopter_repo: MakeAdopterRepo, pkit_on_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AdopterRepo:
    """The project with `topic` leaving main after an actor and UC-001 (`_leave_main`)."""
    return installed(make_adopter_repo, monkeypatch, then=_leave_main)


def test_an_id_moved_within_the_branch_is_no_collision(branched: AdopterRepo) -> None:
    """UC-001 moved into an area here, and elsewhere on main, while main numbered on:
    the merge-base held UC-001, so neither side took it."""
    branched.rename(f"{USE_CASES}/UC-001-one.md", f"{USE_CASES}/core/UC-001-one.md")
    branched.checkout(MAIN)
    branched.rename(f"{USE_CASES}/UC-001-one.md", f"{USE_CASES}/other/UC-001-one.md")
    stamped(branched, "use-case", "two", "--actor", "ACT-tester")
    branched.commit("UC-002 on main")
    branched.checkout("topic")
    completed = numbers(branched, "--base", MAIN, "--json")
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert [f["severity"] for f in document(completed)["findings"]] == ["report"]


def _possibly_ours(number: str, path: str) -> str:
    """The warning for a number main took in a file of the name this branch gives it."""
    return (
        f"{number} is numbered on main too, for {path}, since this branch left it, in a file "
        "of the name this branch gives it: possibly your own work landed — merge main and keep "
        "one file; otherwise renumber this use case before merging — `pkit analysis new` gives "
        "the next free one (DEC-001 point 3)"
    )


def test_two_branches_stamping_the_same_slug_are_warned_not_failed(
    branched: AdopterRepo,
) -> None:
    """One path, two versions: each line of work took UC-002 for an export. That is one
    line of work's file landed and edited since as much as two artefacts, and only the
    person can tell which — warned, never failed; merging main brings the two to one
    path, where git asks which to keep."""
    stamped(branched, "use-case", "export", "--actor", "ACT-tester", "--path", "src/run.py")
    branched.commit("UC-002 on topic")
    branched.checkout(MAIN)
    stamped(branched, "use-case", "export", "--actor", "ACT-tester")
    branched.commit("UC-002 on main")
    branched.checkout("topic")
    ours = f"{USE_CASES}/UC-002-export.md"
    completed = numbers(branched, "--base", MAIN, "--json")
    assert completed.returncode == 0, completed.stderr
    _outdated, warning = document(completed)["findings"]
    assert warning == {
        "severity": "warning",
        "location": ours,
        "message": _possibly_ours("UC-002", ours),
    }


# Slow by design: three stamps, two number checks and the check, each starting `pkit` processes.
def test_a_stacked_branch_whose_parent_squash_merged_is_no_collision(
    branched: AdopterRepo,
) -> None:
    """`child` stacked on `parent`, which numbered UC-002; `child` moved it into an area
    and numbered UC-003. `parent` squash-merged: main took UC-002 under a commit of
    its own, but its file is, byte for byte, the version `parent` wrote — this
    branch's own work landed, not another line of work's number. Merging main then
    leaves two files for UC-002 — git pairs no rename where the merge-base holds
    neither — and the duplicate check catches it there."""
    branched.checkout("parent", create=True)
    stamped(branched, "use-case", "two", "--actor", "ACT-tester")
    branched.commit("UC-002 on parent")
    branched.checkout("child", create=True)
    branched.rename(f"{USE_CASES}/UC-002-two.md", f"{USE_CASES}/area/UC-002-two.md")
    stamped(branched, "use-case", "three", "--actor", "ACT-tester")
    branched.commit("UC-003 on child")
    branched.checkout(MAIN)
    branched.squash_merge("parent")
    branched.checkout("child")
    completed = numbers(branched, "--base", MAIN, "--json")
    assert completed.returncode == 0, completed.stdout + completed.stderr
    ((outdated,),) = [document(completed)["findings"]]
    assert outdated["severity"] == "report"
    # Another line of work taking UC-003 on main meanwhile still collides.
    branched.checkout(MAIN)
    stamped(branched, "use-case", "theirs", "--actor", "ACT-tester")
    branched.commit("UC-003 on main")
    branched.checkout("child")
    completed = numbers(branched, "--base", MAIN, "--json")
    assert completed.returncode == 1
    assert [f["location"] for f in document(completed)["findings"][1:]] == [
        f"{USE_CASES}/UC-003-three.md"
    ]
    branched.git("merge", "-q", "--no-edit", MAIN)
    fill(branched)
    validated = json.loads(run_script(branched, VALIDATE, "--json").stdout)
    duplicates = [f["message"].split(":")[0] for f in validated["findings"]]
    assert f"the id UC-002 is also held by {USE_CASES}/UC-002-two.md" in duplicates


def test_a_parent_edited_after_the_child_forked_is_a_warning_not_a_collision(
    branched: AdopterRepo,
) -> None:
    """`child` forked from `parent` while UC-002 was its first version; `parent` then took
    a review edit and squash-merged. main holds the edited version, which `child`'s
    history never wrote — yet it is `child`'s own work, landed: a file of the name
    `child` gives UC-002 is warned, never failed, and the advice is to merge main."""
    branched.checkout("parent", create=True)
    stamped(branched, "use-case", "two", "--actor", "ACT-tester")
    branched.commit("UC-002 on parent")
    branched.checkout("child", create=True)
    stamped(branched, "use-case", "three", "--actor", "ACT-tester")
    branched.commit("UC-003 on child")
    branched.checkout("parent")
    two = f"{USE_CASES}/UC-002-two.md"
    edited = (branched.root / two).read_text(encoding="utf-8").replace("Two", "Two, reviewed")
    branched.commit("review: UC-002's title", {two: edited})
    branched.checkout(MAIN)
    branched.squash_merge("parent")
    branched.checkout("child")
    completed = numbers(branched, "--base", MAIN, "--json")
    assert completed.returncode == 0, completed.stdout + completed.stderr
    outdated, warning = document(completed)["findings"]
    assert outdated["severity"] == "report"
    assert warning == {
        "severity": "warning",
        "location": two,
        "message": _possibly_ours("UC-002", two),
    }


def test_a_number_the_default_branch_took_and_removed_since_is_still_taken(
    branched: AdopterRepo,
) -> None:
    """main numbered UC-002 after `topic` left it, then removed it: the number is still
    taken — a number is never used again — so `topic`'s UC-002 collides, as the stamp,
    which counts it held on main, agrees."""
    stamped(branched, "use-case", "mine", "--actor", "ACT-tester")
    branched.commit("UC-002 on topic")
    branched.checkout(MAIN)
    stamped(branched, "use-case", "theirs", "--actor", "ACT-tester")
    branched.commit("UC-002 on main")
    theirs = f"{USE_CASES}/UC-002-theirs.md"
    branched.commit("UC-002 removed on main", {theirs: None})
    # The stamp counts UC-002 held on main, where no file holds it now.
    assert stamped(branched, "use-case", "next", "--actor", "ACT-tester") == "UC-003"
    branched.write({f"{USE_CASES}/UC-003-next.md": None})
    branched.checkout("topic")
    completed = numbers(branched, "--base", MAIN, "--json")
    assert completed.returncode == 1, completed.stderr
    _outdated, collision = document(completed)["findings"]
    assert collision == {
        "severity": "error",
        "location": f"{USE_CASES}/UC-002-mine.md",
        "message": (
            f"UC-002 was numbered on main since this branch left it, for {theirs}, which main no "
            "longer holds: a number is never used again, so renumber this use case before "
            "merging — `pkit analysis new` gives the next free one (DEC-001 point 3)"
        ),
    }


def test_this_branch_s_numbers_are_read_by_name_and_id_as_main_s_are(
    branched: AdopterRepo,
) -> None:
    """A file here whose number is in its name alone — no front matter — holds it, as a
    file on main does: main taking UC-002 since collides with it."""
    draft = f"{USE_CASES}/UC-002-draft.md"
    branched.commit("a draft on topic", {draft: "# A draft\n"})
    branched.checkout(MAIN)
    stamped(branched, "use-case", "two", "--actor", "ACT-tester")
    branched.commit("UC-002 on main")
    branched.checkout("topic")
    completed = numbers(branched, "--base", MAIN, "--json")
    assert completed.returncode == 1, completed.stderr
    _outdated, collision = document(completed)["findings"]
    assert (collision["severity"], collision["location"]) == ("error", draft)


def test_a_stale_base_is_reported_as_the_friction_change_check_reports_it(
    branched: AdopterRepo,
) -> None:
    """main moved on after this branch left it, taking no number: reported, never
    failed, with the same base as `pkit friction check` gives."""
    stamped(branched, "use-case", "two", "--actor", "ACT-tester")
    branched.commit("UC-002 on topic")
    branched.checkout(MAIN)
    stamped(branched, "term", "sandbox")
    branched.commit("a term on main")
    branched.checkout("topic")
    completed = numbers(branched, "--base", MAIN, "--json")
    assert completed.returncode == 0, completed.stderr
    answer = document(completed)
    ((finding,),) = [answer["findings"]]
    assert finding["severity"] == "report"
    assert finding["message"].startswith(
        f"outdated base: the base main is at {answer['base']['tip'][:12]}"
    )
    friction = subprocess.run(
        ["pkit", "friction", "check", "--base", MAIN, "--json"],
        cwd=branched.root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert json.loads(friction.stdout)["base"] == answer["base"]


def test_a_branch_containing_its_base_has_nothing_to_collide_with(seeded: AdopterRepo) -> None:
    seeded.commit("seeded")
    completed = numbers(seeded, "--base", MAIN, "--json")
    assert completed.returncode == 0, completed.stderr
    assert document(completed)["findings"] == []


def test_a_working_tree_numbering_nothing_needs_no_base(project: AdopterRepo) -> None:
    """Nothing numbered, nothing to compare: no base is read, not even one that names no
    commit here (COR-054 point 4)."""
    stamped(project, "actor", "tester")
    completed = numbers(project, "--base", "origin/main", "--json")
    assert completed.returncode == 0, completed.stderr
    assert document(completed) == {
        "schema_version": 1,
        "base": None,
        "freed": [],
        "summary": [
            "numbers: no use case or journey is numbered here; nothing to compare, no base read."
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
def test_a_base_that_names_no_commit_fails(seeded: AdopterRepo, base: str, refusal: str) -> None:
    for json_flag in ((), ("--json",)):
        completed = numbers(seeded, f"--base={base}", *json_flag)
        assert completed.returncode == 1
        assert completed.stdout == ""
        assert f"error: {refusal}" in completed.stderr


def test_a_base_sharing_no_history_with_head_fails(seeded: AdopterRepo) -> None:
    seeded.git("checkout", "-q", "--orphan", "unrelated")
    seeded.commit("a history of its own")
    completed = numbers(seeded, "--base", MAIN)
    assert completed.returncode == 1
    assert "HEAD and the base 'main' share no history to compare" in completed.stderr


def test_the_base_is_the_variable_else_the_default_branch(
    seeded: AdopterRepo, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without `--base`, the base the backbone names (COR-054): the default branch — here
    the local `main`, since there is no remote, which it says — or a declared one that
    resolves nowhere, which fails as the change check does; `$PKIT_CHECK_BASE` replaces
    either."""
    seeded.commit("seeded")
    unnamed = numbers(seeded, "--json")
    assert unnamed.returncode == 0, unnamed.stderr
    assert document(unnamed)["base"]["ref"] == MAIN
    assert "warning: the default branch 'main' is read from the local branch 'main'" in (
        unnamed.stderr
    )
    seeded.write({CONFIG: "docs:\n  internal: tech-docs\nrepository:\n  default-branch: trunk\n"})
    undeclared = numbers(seeded)
    assert undeclared.returncode == 1
    assert "error: the default branch 'trunk' resolves to no commit here" in undeclared.stderr
    monkeypatch.setenv(BASE_ENV, MAIN)
    named = numbers(seeded, "--json")
    assert named.returncode == 0, named.stderr
    assert document(named)["base"]["ref"] == MAIN
