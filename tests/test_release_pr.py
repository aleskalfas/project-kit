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
    return release_pr.pull_request_body(plan, changelog, branch=branch, repository_url=REPOSITORY)


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
        ]
    )


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
    body = release_pr.pull_request_body(_plan(), _too_long(), branch=BRANCH, repository_url=None)

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

    assert release_pr.main(["body", "--plan", str(plan), "--branch", BRANCH]) == 1

    assert "is no JSON object" in capsys.readouterr().err


# --- The workflow --------------------------------------------------------------


def _steps() -> list[dict[str, Any]]:
    workflow = YAML(typ="safe").load(WORKFLOW.read_text(encoding="utf-8"))
    return workflow["jobs"]["release-pr"]["steps"]


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
