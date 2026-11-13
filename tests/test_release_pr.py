"""`scripts/release_pr.py`: the release pull request's branch and description (#2862).

The release-pr workflow pushes the release to the branch the script names, and
opens the pull request with the description it writes. The description holds
the changelog's new section where the whole fits the 65 536 characters GitHub
keeps in a pull request's description; where it does not, a link to
`CHANGELOG.md` on the release branch takes the section's place, and the bumps and
warnings stay whole. A branch a failed run left on `origin` makes the next run
name its branch with the run's id.

The description is a function of the plan and the changelog, so most tests call
it directly. The branch is read from a real bare `origin` in one test, and the
command runs as a process, as the workflow runs it, in one test.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML
from scripts import release_pr

from project_kit import release
from tests.adopter_repo import GitRepo

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "release-pr.yml"
SCRIPT = ROOT / "scripts" / "release_pr.py"
LIMIT = release_pr.PULL_REQUEST_BODY_LIMIT
BRANCH = "release/v2.1.0"
REPOSITORY = "https://github.com/owner/repo"

FLOOR = "requires_backbone floor raised to >=2.1.0"
CAPABILITY_FLOOR = "requires_capabilities project-management floor raised to >=0.56.0"
BOUND = "requires_capabilities living-docs upper bound widened to <2.0.0 (runs on 1.0.0)"
WARNING = "backbone migration dir 2.2.0 does not match the computed backbone release 2.1.0"

#: The commit the release's plan read, and the trailer line naming it (ADR-092 point 6).
PLAN_COMMIT = "0123456789abcdef0123456789abcdef01234567"
TRAILER = release.plan_commit_line(PLAN_COMMIT)


def _plan(*, warnings: list[str] | None = None) -> dict[str, Any]:
    """A plan shaped as `pkit release plan --json` prints one: a backbone move, a
    capability with a floor on the backbone and one on a capability, another
    with a widened bound, and the warnings given."""

    def ranges(*lines: str) -> list[dict[str, Any]]:
        return [{"lines": [line]} for line in lines]

    return {
        "empty": False,
        "backbone_version": "2.1.0",
        "releases": [
            {
                "component": "backbone",
                "old_version": "2.0.0",
                "new_version": "2.1.0",
                "segment": "minor",
                "notes": ["A note."],
                "requires_backbone_floor": None,
                "requires_capabilities_floors": [],
                "requires_capabilities_bounds": [],
            },
            {
                "component": "software-engineering",
                "old_version": "0.3.0",
                "new_version": "0.3.1",
                "segment": "patch",
                "notes": ["A note."],
                "requires_backbone_floor": {"lines": [FLOOR]},
                "requires_capabilities_floors": ranges(CAPABILITY_FLOOR),
                "requires_capabilities_bounds": [],
            },
            {
                "component": "doc-examples",
                "old_version": "1.0.0",
                "new_version": "1.0.1",
                "segment": "patch",
                "notes": ["A note."],
                "requires_backbone_floor": None,
                "requires_capabilities_floors": [],
                "requires_capabilities_bounds": ranges(BOUND),
            },
        ],
        "changesets_consumed": 3,
        "migration_warnings": warnings or [],
    }


BUMPS = [
    "- backbone: 2.0.0 → 2.1.0 (minor)",
    "- software-engineering: 0.3.0 → 0.3.1 (patch)",
    f"  - {FLOOR}",
    f"  - {CAPABILITY_FLOOR}",
    "- doc-examples: 1.0.0 → 1.0.1 (patch)",
    f"  - {BOUND}",
]

OLDER = "## 2.0.0 — 2026-10-30\n\n### Added\n- An older entry.\n"


def _changelog(*entries: str) -> str:
    """A changelog whose new section holds `entries`, above an older section."""
    items = "".join(f"- {entry}\n" for entry in entries)
    return f"# Changelog\n\n## 2.1.0 — 2026-11-07\n\n### Added\n{items}\n{OLDER}"


def _body(plan: dict[str, Any], changelog: str, branch: str = BRANCH) -> str:
    return release_pr.pull_request_body(
        plan, changelog, branch=branch, repository_url=REPOSITORY, trailer=TRAILER
    )


# --- A description that fits ------------------------------------------------


def test_a_description_that_fits_holds_the_changelogs_new_section() -> None:
    """Line for line what the workflow's shell wrote before the script."""
    body = _body(_plan(warnings=[WARNING]), _changelog("A new entry (#1)."))

    assert body == "\n".join(
        [
            *release_pr.INTRO,
            "",
            "## Version bumps",
            *BUMPS,
            "",
            "## Migration-dir warnings (see #465)",
            f"- {WARNING}",
            "",
            "## Generated changelog",
            "## 2.1.0 — 2026-11-07",
            "",
            "### Added",
            "- A new entry (#1).",
            "",
            "",
            TRAILER,
            "",
        ]
    )


def test_the_description_ends_with_the_trailer_line_whether_the_section_fits_or_not() -> None:
    """Last, so `pkit release merge` and the queue's check read the commit the
    plan read from the body, and the squash commit's message, whole (ADR-092
    point 6)."""
    for changelog in (_changelog("A new entry."), _too_long()):
        body = _body(_plan(), changelog)

        assert body.endswith(f"\n{TRAILER}\n")
        assert release.plan_commits_named(body) == [PLAN_COMMIT]


def test_without_warnings_the_description_has_no_warnings_section() -> None:
    body = _body(_plan(), _changelog("A new entry."))

    assert "Migration-dir warnings" not in body
    assert "\n".join(["", "## Version bumps", *BUMPS, "", "## Generated changelog", ""]) in body


def test_only_the_new_section_is_shown_and_never_an_older_one() -> None:
    body = _body(_plan(), _changelog("A new entry."))

    assert "- A new entry.\n" in body
    assert "older entry" not in body
    assert "# Changelog" not in body


def test_a_description_of_exactly_the_limit_keeps_the_section() -> None:
    plan = _plan()
    short = _body(plan, _changelog(""))
    filler = "x" * (LIMIT - len(short))

    body = _body(plan, _changelog(filler))

    assert len(body) == LIMIT
    assert filler in body


# --- A section too long for the description --------------------------------


def _too_long() -> str:
    """A changelog whose new section alone passes the limit, as 2.1.0's did, in
    entries of a thousand characters each."""
    return _changelog(*(f"Entry {n}: " + "y" * 1000 for n in range(80)))


def test_a_section_that_would_pass_the_limit_is_linked_on_the_release_branch() -> None:
    plan = _plan(warnings=[WARNING])

    body = _body(plan, _too_long())

    assert len(body) <= LIMIT
    assert "Entry 0" not in body
    assert f"[`CHANGELOG.md` on `{BRANCH}`]({REPOSITORY}/blob/{BRANCH}/CHANGELOG.md)" in body


def test_the_link_keeps_every_bump_line_and_warning_whole() -> None:
    body = _body(_plan(warnings=[WARNING, "another warning"]), _too_long())

    head, _, pointer = body.partition("## Generated changelog\n")
    assert head.splitlines()[3:] == [
        "## Version bumps",
        *BUMPS,
        "",
        "## Migration-dir warnings (see #465)",
        f"- {WARNING}",
        "- another warning",
        "",
    ]
    assert pointer.startswith("The changelog's new section is too long to show here.")


def test_the_pointer_says_how_long_the_description_would_be() -> None:
    plan = _plan()
    changelog = _too_long()
    # A changelog with no section gives the description without one.
    whole = len(_body(plan, "")) + len(release_pr.changelog_section(changelog))

    body = _body(plan, changelog)

    assert f"would hold {whole:,} characters, past the {LIMIT:,} GitHub keeps" in body


def test_one_character_past_the_limit_links_the_section() -> None:
    plan = _plan()
    short = _body(plan, _changelog(""))
    filler = "x" * (LIMIT - len(short) + 1)

    body = _body(plan, _changelog(filler))

    assert filler not in body
    assert f"{REPOSITORY}/blob/{BRANCH}/CHANGELOG.md" in body


def test_the_link_names_the_branch_a_run_pushed() -> None:
    branch = f"{BRANCH}-12345"

    body = _body(_plan(), _too_long(), branch=branch)

    assert f"({REPOSITORY}/blob/{branch}/CHANGELOG.md)" in body


def test_without_a_repository_address_the_pointer_names_the_file_and_branch() -> None:
    body = release_pr.pull_request_body(
        _plan(), _too_long(), branch=BRANCH, repository_url=None, trailer=TRAILER
    )

    assert f"Read it as the first section of `CHANGELOG.md` on `{BRANCH}`." in body
    assert "](" not in body


def test_a_description_too_long_even_without_the_section_is_refused() -> None:
    plan = _plan(warnings=["w" * LIMIT])

    with pytest.raises(release_pr.Refused, match="without the changelog's section"):
        _body(plan, _too_long())


# --- The branch --------------------------------------------------------------


def test_the_branch_is_named_after_the_backbone_version() -> None:
    assert release_pr.release_branch("2.1.0", "42", {"main"}) == "release/v2.1.0"


def test_a_branch_left_behind_makes_the_run_name_its_own_with_the_run_id() -> None:
    taken = {"main", "release/v2.1.0"}

    assert release_pr.release_branch("2.1.0", "42", taken) == "release/v2.1.0-42"


def test_a_release_that_moves_no_backbone_takes_the_run_id() -> None:
    assert release_pr.release_branch("", "42", {"main", "release/v2.1.0"}) == "release/42"


def test_every_branch_is_one_pkit_release_merge_takes() -> None:
    names = [
        release_pr.release_branch("2.1.0", "42", set()),
        release_pr.release_branch("2.1.0", "42", {"release/v2.1.0"}),
        release_pr.release_branch("", "42", set()),
    ]

    assert all(name.startswith(release.RELEASE_BRANCH_PREFIX) for name in names)


def test_the_listing_gives_each_branch_and_nothing_else() -> None:
    listing = "\n".join(
        [
            f"{'a' * 40}\trefs/heads/main",
            f"{'b' * 40}\trefs/heads/release/v2.1.0\r",
            f"{'c' * 40}\trefs/tags/v2.0.0",
            "no tab here",
            "",
        ]
    )

    assert release_pr.branches_listed(listing) == {"main", "release/v2.1.0"}


def test_the_branch_is_read_from_origin(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    origin = tmp_path / "origin.git"
    GitRepo(tmp_path).git("init", "--bare", "-q", str(origin))
    clone = GitRepo.init(tmp_path / "clone")
    clone.git("remote", "add", "origin", str(origin))
    clone.commit("Start", {"README.md": "start\n"})
    clone.git("push", "-q", "origin", "main")
    args = ["branch", "--version", "2.1.0", "--run-id", "42"]

    with pytest.MonkeyPatch.context() as patch:
        patch.chdir(clone.root)
        assert release_pr.main(args) == 0
        assert capsys.readouterr().out == "release/v2.1.0\n"

        clone.git("push", "-q", "origin", "main:refs/heads/release/v2.1.0")
        assert release_pr.main(args) == 0
        assert capsys.readouterr().out == "release/v2.1.0-42\n"


def test_a_clone_with_no_origin_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    clone = GitRepo.init(tmp_path / "clone")

    with pytest.MonkeyPatch.context() as patch:
        patch.chdir(clone.root)
        assert release_pr.main(["branch", "--version", "2.1.0", "--run-id", "42"]) == 1

    assert "error: `git ls-remote --heads origin` failed" in capsys.readouterr().err


# --- The command, as the workflow runs it -------------------------------------


def test_the_command_writes_the_description_as_the_workflow_runs_it(tmp_path: Path) -> None:
    plan = tmp_path / "release-plan.json"
    plan.write_text(json.dumps(_plan(warnings=[WARNING])), encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text(_too_long(), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "body",
            "--plan",
            str(plan),
            "--branch",
            BRANCH,
            "--repository-url",
            REPOSITORY,
            "--trailer",
            TRAILER,
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout == _body(_plan(warnings=[WARNING]), _too_long())


def test_a_plan_that_cannot_be_read_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    plan = tmp_path / "plan.json"
    plan.write_text("[]", encoding="utf-8")

    assert (
        release_pr.main(["body", "--plan", str(plan), "--branch", BRANCH, "--trailer", TRAILER])
        == 1
    )

    assert "is no JSON object" in capsys.readouterr().err


def test_a_trailer_that_is_not_the_line_alone_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps(_plan()), encoding="utf-8")
    args = ["body", "--plan", str(plan), "--branch", BRANCH, "--trailer", f"{TRAILER} and more"]

    assert release_pr.main(args) == 1

    assert "is not the trailer line alone" in capsys.readouterr().err


# --- The trailer line `pkit release apply` printed ------------------------------


def test_the_trailer_is_the_one_line_apply_printed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    printed = tmp_path / "apply.txt"
    printed.write_text(f"Backbone: 2.0.0 -> 2.1.0\n{TRAILER}\n", encoding="utf-8")

    assert release_pr.main(["trailer", "--apply-output", str(printed)]) == 0

    assert capsys.readouterr().out == f"{TRAILER}\n"


@pytest.mark.parametrize(
    "printed",
    [
        "No pending changesets move a version — nothing to release.\n",
        f"{TRAILER}\n{release.plan_commit_line('f' * 40)}\n",
    ],
    ids=["none", "two"],
)
def test_apply_output_without_one_trailer_line_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], printed: str
) -> None:
    output = tmp_path / "apply.txt"
    output.write_text(printed, encoding="utf-8")

    assert release_pr.main(["trailer", "--apply-output", str(output)]) == 1

    assert "trailer lines naming the commit its plan read, not one" in capsys.readouterr().err


# --- The open release pull requests: the way on --------------------------------


def _listed(number: int, branch: str, body: str) -> dict[str, Any]:
    return {"number": number, "headRefName": branch, "body": body}


def test_a_release_pr_planned_from_the_head_is_current_and_every_other_stale() -> None:
    """A release PR planned from an older head, or naming none, is stale, and
    a PR on any other branch is no release PR at all."""
    older = release.plan_commit_line("f" * 40)
    listed = [
        _listed(7, "release/v2.1.0", f"Bumps.\n\n{TRAILER}\n"),
        _listed(8, "release/v2.0.9", f"Bumps.\n\n{older}\n"),
        _listed(9, "release/41", "Opened before the trailer existed.\n"),
        _listed(10, "feat/1-thing", f"{older}\n"),
    ]

    assert release_pr.open_release_pull_requests(listed, PLAN_COMMIT) == ([7], [8, 9])


def test_a_body_naming_the_head_beside_another_commit_is_stale() -> None:
    body = f"{TRAILER}\n{release.plan_commit_line('f' * 40)}\n"

    assert release_pr.open_release_pull_requests([_listed(7, BRANCH, body)], PLAN_COMMIT) == (
        [],
        [7],
    )


def test_the_command_prints_current_and_stale_for_the_workflow(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    prs = tmp_path / "open.json"
    prs.write_text(
        json.dumps([_listed(7, BRANCH, TRAILER), _listed(8, "release/v2.0.9", "")]),
        encoding="utf-8",
    )

    assert release_pr.main(["open", "--prs", str(prs), "--head", PLAN_COMMIT]) == 0

    assert capsys.readouterr().out == "current=7\nstale=8\n"


def test_a_listing_that_is_not_the_one_asked_for_is_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    prs = tmp_path / "open.json"
    prs.write_text(json.dumps([{"number": 7}]), encoding="utf-8")

    assert release_pr.main(["open", "--prs", str(prs), "--head", PLAN_COMMIT]) == 1

    assert "lacks its number, branch or body" in capsys.readouterr().err


# --- The notes an earlier run left unpublished (ADR-092 point 5) ---------------


def _ls_remote(*refs: str) -> str:
    return "".join(f"{n:040x}\t{ref}\n" for n, ref in enumerate(refs, start=1))


def test_each_release_and_candidate_tag_without_a_release_is_named_oldest_first() -> None:
    listed = _ls_remote(
        "refs/tags/v2.2.0",
        "refs/tags/v2.2.0^{}",
        "refs/tags/v2.3.0rc2",
        "refs/tags/v2.3.0rc2^{}",
        "refs/tags/v2.1.0",
        "refs/tags/v2.3.0",
        "refs/tags/v2.3.0rc10",
        "refs/tags/withdrawn/v2.3.0rc2",
        "refs/tags/latest",
        "refs/tags/v2.4.0b1",
    )

    named = release_pr.unpublished(listed, {"v2.1.0", "v2.2.0"})

    assert named == ["2.3.0rc2", "2.3.0rc10", "2.3.0"]


def test_with_every_tag_released_nothing_is_named() -> None:
    assert release_pr.unpublished(_ls_remote("refs/tags/v2.2.0"), {"v2.2.0"}) == []
    assert release_pr.unpublished("", set()) == []


def test_the_command_prints_a_version_a_line_for_the_workflow(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    tags = tmp_path / "tags.txt"
    tags.write_text(_ls_remote("refs/tags/v2.3.0rc1", "refs/tags/v2.2.0"), encoding="utf-8")
    releases = tmp_path / "releases.txt"
    releases.write_text("v2.2.0\nv2.1.0\n", encoding="utf-8")

    code = release_pr.main(["unpublished", "--tags", str(tags), "--releases", str(releases)])

    assert code == 0
    assert capsys.readouterr().out == "2.3.0rc1\n"


def test_tags_that_cannot_be_read_are_refused(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    releases = tmp_path / "releases.txt"
    releases.write_text("", encoding="utf-8")
    missing = str(tmp_path / "missing.txt")

    code = release_pr.main(["unpublished", "--tags", missing, "--releases", str(releases)])

    assert code == 1
    assert "the tags" in capsys.readouterr().err


# --- The workflow --------------------------------------------------------------


def _workflow() -> dict[str, Any]:
    return YAML(typ="safe").load(WORKFLOW.read_text(encoding="utf-8"))


def _steps(job: str = "release-pr") -> list[dict[str, Any]]:
    return _workflow()["jobs"][job]["steps"]


def _index(steps: list[dict[str, Any]], runs: str) -> int:
    (index,) = [i for i, step in enumerate(steps) if runs in step.get("run", "")]
    return index


def test_the_branch_is_derived_after_no_open_release_pull_request_was_found() -> None:
    steps = _steps()
    branch = _index(steps, "scripts/release_pr.py branch")

    assert steps[branch]["id"] == "branch"
    assert branch > _index(steps, "gh pr list --state open")
    assert "steps.existing.outputs.count == '0'" in steps[branch]["if"]
    assert steps[branch]["env"]["RUN_ID"] == "${{ github.run_id }}"


def test_the_description_is_built_after_the_apply_and_before_the_push() -> None:
    steps = _steps()
    run = steps[_index(steps, "scripts/release_pr.py body")]["run"]

    apply = run.index("pkit release apply --yes")
    body = run.index("scripts/release_pr.py body")
    assert apply < body < run.index("git push") < run.index("gh pr create")
    assert '--branch "${branch}"' in run
    assert '--body-file "${body}"' in run


def test_a_release_pr_planned_from_an_older_head_is_closed_before_the_branch_is_derived() -> None:
    """The way on (ADR-092 point 6): the run reads the open PRs' bodies,
    closes each stale one with its branch, and skips only for a current one."""
    steps = _steps()
    existing = steps[_index(steps, "scripts/release_pr.py open")]
    run = existing["run"]

    assert existing["id"] == "existing"
    assert "gh pr list --state open --json number,headRefName,body" in run
    assert '--head "${head}"' in run and 'head="$(git rev-parse HEAD)"' in run
    assert run.index("scripts/release_pr.py open") < run.index(
        'gh pr close "${number}" --delete-branch'
    )
    assert 'echo "count=${count}" >> "$GITHUB_OUTPUT"' in run
    assert _index(steps, "scripts/release_pr.py open") < _index(
        steps, "scripts/release_pr.py branch"
    )


def test_the_release_commit_and_the_body_carry_the_line_apply_printed() -> None:
    steps = _steps()
    run = steps[_index(steps, "scripts/release_pr.py body")]["run"]

    apply = run.index('uv run pkit release apply --yes | tee "${applied}"')
    trailer = run.index('scripts/release_pr.py trailer --apply-output "${applied}"')
    assert apply < trailer < run.index("scripts/release_pr.py body")
    assert '--trailer "${trailer}"' in run
    assert 'git commit -m "${title}" -m "${trailer}"' in run


def test_the_input_pre_release_chooses_the_job_and_one_group_keeps_runs_apart() -> None:
    workflow = _workflow()
    jobs = workflow["jobs"]

    pre = workflow["on"]["workflow_dispatch"]["inputs"]["pre-release"]
    assert pre["type"] == "boolean" and pre["default"] is False
    assert workflow["concurrency"] == {"group": "release", "cancel-in-progress": False}
    assert jobs["release-pr"]["if"] == "${{ !inputs.pre-release }}"
    assert jobs["pre-release"]["if"] == "${{ inputs.pre-release }}"
    assert jobs["release-pr"]["needs"] == jobs["pre-release"]["needs"] == "start"


def test_without_the_input_the_run_refuses_off_the_default_branch_before_anything_else() -> None:
    """ADR-092 point 5: the refusal comes before the notes, and the plan after both."""
    steps = _steps("start")
    refusal = steps[_index(steps, "jq -r '.default_branch.name'")]

    assert refusal["if"] == "${{ !inputs.pre-release }}"
    assert '[ "${GITHUB_REF}" != "refs/heads/${default}" ]' in refusal["run"]
    assert "exit 1" in refusal["run"]
    assert _index(steps, "jq -r '.default_branch.name'") < _index(
        steps, "scripts/release_pr.py unpublished"
    )


def test_the_notes_left_unpublished_are_finished_and_a_failure_is_said_and_passed_by() -> None:
    steps = _steps("start")
    run = steps[_index(steps, "scripts/release_pr.py unpublished")]["run"]

    assert "set -uo pipefail" in run and "set -e" not in run
    assert "git ls-remote --tags origin" in run
    assert 'gh api --paginate "repos/${GITHUB_REPOSITORY}/releases"' in run
    publish = run.index('uv run pkit release publish-notes "${version}"')
    assert run.index("scripts/release_pr.py unpublished") < publish
    assert "::warning::The notes of v${version} could not be published" in run[publish:]


def test_a_candidate_is_cut_after_the_check_and_its_tag_pushed_after_the_wheel_check() -> None:
    """ADR-092 point 2 and ADR-089 point 9: the check, the cut, the wheel, the push of
    the tag alone, never forced, then its notes."""
    steps = _steps("pre-release")
    check = _index(steps, 'uv run pkit release check --base "${default}"')
    cut = _index(steps, "uv run pkit release apply --pre --tag --yes")
    wheel = _index(steps, "uv build --wheel")
    push = _index(steps, "git push")
    notes = _index(steps, "pkit release publish-notes")

    assert check < cut < wheel < push < notes
    assert "PKIT_CHANGESET_SKIP" not in str(steps)
    assert steps[push]["run"] == 'git push origin "refs/tags/v${VERSION}"'
    assert '"${venv}/bin/pkit" --version' in steps[wheel]["run"]
    assert '!= "pkit, version ${VERSION}"' in steps[wheel]["run"]
    # No job forces a push or deletes a tag (ADR-092 point 10).
    text = WORKFLOW.read_text(encoding="utf-8")
    for forbidden in ("--force", "push -f", "git tag -d", "tag --delete", ":refs/tags/"):
        assert forbidden not in text
