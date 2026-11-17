"""A release lands only what its release step wrote, onto its plan's commit (#3101).

ADR-092 point 6. `pkit release apply` prints the trailer line naming the commit
its plan read; the release commit and the release PR's body carry it. One
predicate, in `project_kit.release` beside the recogniser `pkit release check`
reads a release diff by, judges a release: it lands on its plan's commit, and
its change from that commit holds only what `apply` writes and the answer files
it adds. `pkit release merge` applies it at its request, reading the base's head
from the remote (`release_pr_problem`), and the queue's check (`pkit release
check-queue`) applies it to each release commit of a squashing queue's merge.

Every test runs on real repositories: a source kit committed on `main`, a bare
`origin` where the merge reads the base's head and the PR's head
(`refs/pull/<n>/head`), and the release step's writes made by hand, as
`tests/test_release_check.py` makes them.
"""

from __future__ import annotations

import dataclasses
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from project_kit import answer_files, release
from project_kit.cli import main
from tests.adopter_repo import sign_nothing

#: The release PR's number, and its head branch.
NUMBER = 42
BRANCH = "release/v1.6.0"
TITLE = "chore(release): v1.6.0"


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def _commit(repo: Path, message: str, files: dict[str, str | None]) -> str:
    """Commit `files` — a path's text, or None to delete it — with `message`;
    the commit's id."""
    for relpath, content in files.items():
        target = repo / relpath
        if content is None:
            target.unlink()
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


_PACKAGE = (
    "schema_version: 1\ncomponent:\n  kind: adapter\n  name: claude-code\n"
    '  version: {version}\nrequires_backbone: ">=0.1.0,<2.0.0"\n'
)
_CHANGESET = ".changes/unreleased/backbone-minor.yaml"


def _kit(repo: Path, *, source: bool = False) -> Path:
    """A repository holding a source kit with one component and one pending
    changeset, committed as `main`; its `.pkit/`. With `source`, the package
    source sits beside it: the methodology's source repository, as the marker
    test finds it (ADR-059 point 3)."""
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "T")
    sign_nothing(repo)
    marker: dict[str, str | None] = {"src/project_kit/__init__.py": ""} if source else {}
    _commit(
        repo,
        "seed",
        {
            ".pkit/VERSION": "1.5.0\n",
            ".pkit/adapters/claude-code/package.yaml": _PACKAGE.format(version="0.5.0"),
            "src/seed.txt": "x\n",
            _CHANGESET: "component: backbone\nkind: minor\nbody: A note.\n",
            **marker,
        },
    )
    return repo / ".pkit"


def _release(repo: Path, plan: str | None, *, extra: dict[str, str | None] | None = None) -> str:
    """The release step's writes, committed under the release title with the
    trailer line naming `plan` (None: no trailer), and `extra` beside them; the
    release commit's id."""
    message = TITLE if plan is None else f"{TITLE}\n\n{release.plan_commit_line(plan)}"
    files: dict[str, str | None] = {
        ".pkit/VERSION": "1.6.0\n",
        ".pkit/adapters/claude-code/package.yaml": _PACKAGE.format(version="0.6.0"),
        "CHANGELOG.md": "# Changelog\n\n## 1.6.0 — 2026-11-13\n\n### Changed\n\n- A note.\n",
        _CHANGESET: None,
        **(extra or {}),
    }
    return _commit(repo, message, files)


def _answer_file() -> str:
    return f"{answer_files.FOLDER}/20261113T120000Z-abcdef12{answer_files.SUFFIX}"


# --- The trailer line ---------------------------------------------------------

PLAN = "0123456789abcdef0123456789abcdef01234567"
OTHER = "fedcba9876543210fedcba9876543210fedcba98"


def test_the_trailer_line_names_the_plans_commit_in_full() -> None:
    assert release.plan_commit_line(PLAN) == f"Release-plan-commit: {PLAN}"


def test_the_line_is_found_as_a_whole_line_anywhere_in_a_message_or_a_body() -> None:
    """Mid-text, as a squash message or a body holds it, where git reads no
    trailer, and with a body's carriage returns."""
    body = f"## Version bumps\r\nRelease-plan-commit: {PLAN}\r\n\r\n## Generated changelog\r\n"
    assert release.plan_commits_named(body) == [PLAN]
    assert release.plan_commits_named(f"subject\n\nRelease-plan-commit: {PLAN}") == [PLAN]


@pytest.mark.parametrize(
    "line",
    [
        f"see Release-plan-commit: {PLAN}",
        f"Release-plan-commit: {PLAN} and more",
        f"Release-plan-commit: {PLAN[:12]}",
        f"Release-plan-commit:{PLAN}",
        f"release-plan-commit: {PLAN}",
        f"Release-plan-commit: {PLAN.upper()}",
    ],
)
def test_a_line_that_is_not_the_trailer_whole_names_nothing(line: str) -> None:
    assert release.plan_commits_named(line) == []


def test_each_commit_named_is_given_once_in_order() -> None:
    text = "\n".join(release.plan_commit_line(c) for c in (OTHER, PLAN, OTHER))
    assert release.plan_commits_named(text) == [OTHER, PLAN]


def test_the_trailer_names_one_commit_or_the_problem_says_why() -> None:
    assert release.trailer_problem([PLAN], "its body") is None
    assert "carries no `Release-plan-commit:` line" in str(release.trailer_problem([], "its body"))
    assert "names 2 commits" in str(release.trailer_problem([PLAN, OTHER], "its body"))


# --- The predicate -------------------------------------------------------------


def test_a_release_written_onto_its_plans_commit_lands_sound(tmp_path: Path) -> None:
    source_kit = _kit(tmp_path)
    plan = _git(tmp_path, "rev-parse", "HEAD")
    head = _release(tmp_path, plan)
    assert (
        release.release_landing_problem(source_kit, lands_on=plan, plan_commit=plan, head=head)
        is None
    )


def test_a_release_onto_another_commit_than_its_plan_read_does_not(tmp_path: Path) -> None:
    source_kit = _kit(tmp_path)
    plan = _git(tmp_path, "rev-parse", "HEAD")
    head = _release(tmp_path, plan)
    problem = release.release_landing_problem(
        source_kit, lands_on=OTHER, plan_commit=plan, head=head
    )
    assert problem is not None and "the default branch has moved" in problem


def test_a_change_beyond_what_apply_writes_does_not_land_sound(tmp_path: Path) -> None:
    source_kit = _kit(tmp_path)
    plan = _git(tmp_path, "rev-parse", "HEAD")
    _release(tmp_path, plan)
    head = _commit(tmp_path, "fix: rides along", {"src/seed.txt": "y\n"})
    problem = release.release_landing_problem(
        source_kit, lands_on=plan, plan_commit=plan, head=head
    )
    assert problem is not None and "src/seed.txt" in problem


def test_answer_files_the_release_adds_land_beside_its_writes(tmp_path: Path) -> None:
    source_kit = _kit(tmp_path)
    plan = _git(tmp_path, "rev-parse", "HEAD")
    _release(tmp_path, plan)
    head = _commit(tmp_path, "docs: answers", {_answer_file(): "answers: []\n"})
    assert (
        release.release_landing_problem(source_kit, lands_on=plan, plan_commit=plan, head=head)
        is None
    )


def test_the_recogniser_still_reads_a_release_diff_from_where_head_left_its_base(
    tmp_path: Path,
) -> None:
    source_kit = _kit(tmp_path)
    plan = _git(tmp_path, "rev-parse", "HEAD")
    _git(tmp_path, "checkout", "-q", "-b", BRANCH)
    _release(tmp_path, plan)
    assert release.is_release_diff(source_kit, "main")
    assert release.release_change_problem(source_kit, ("main...HEAD",)) is None


# --- The queue's check -----------------------------------------------------------


def _squash(repo: Path, onto: str, head: str, message: str) -> str:
    """The squash commit a squashing queue makes of `head` onto `onto`, with
    `message` — the PR's title and body."""
    merged = _git(repo, "merge-tree", "--write-tree", onto, head).split()[0]
    return _git(repo, "commit-tree", merged, "-p", onto, "-m", message)


def _queue(tmp_path: Path, *, trailer: bool = True, ahead: bool = False) -> tuple[Path, str, str]:
    """A merge group on `main`: a release PR squashed onto `main`'s head —
    behind another PR's squash commit where `ahead` — its message the PR's
    title and body, the body ending with the trailer line where `trailer`.
    The source kit, the group's base and its head."""
    source_kit = _kit(tmp_path)
    base = _git(tmp_path, "rev-parse", "HEAD")
    _git(tmp_path, "checkout", "-q", "-b", BRANCH)
    release_commit = _release(tmp_path, base)
    onto = base
    if ahead:
        _git(tmp_path, "checkout", "-q", "-b", "feature", base)
        other = _commit(tmp_path, "feat: another change", {"src/other.txt": "z\n"})
        onto = _git(tmp_path, "commit-tree", f"{other}^{{tree}}", "-p", base, "-m", "feat: other")
    body = (
        f"Automated release PR.\n\n{release.plan_commit_line(base)}\n" if trailer else "No line.\n"
    )
    squash = _squash(tmp_path, onto, release_commit, f"{TITLE}\n\n{body}")
    _git(tmp_path, "checkout", "-q", "--detach", squash)
    return source_kit, base, squash


def test_a_release_squashed_onto_its_plans_commit_passes_the_queues_check(tmp_path: Path) -> None:
    source_kit, base, head = _queue(tmp_path)
    (judged,) = release.check_queue(source_kit, base, head)
    assert judged.commit == head and judged.subject == TITLE and judged.problem is None


def test_a_release_queued_behind_another_pull_request_fails_it(tmp_path: Path) -> None:
    """The other PR's squash commit lands between the plan's commit and the
    release's, so the release's parent is not the commit its plan read."""
    source_kit, base, head = _queue(tmp_path, ahead=True)
    (judged,) = release.check_queue(source_kit, base, head)
    assert judged.problem is not None and "the default branch has moved" in judged.problem


def test_a_release_commit_without_the_trailer_fails_it(tmp_path: Path) -> None:
    source_kit, base, head = _queue(tmp_path, trailer=False)
    (judged,) = release.check_queue(source_kit, base, head)
    assert judged.problem is not None and "carries no `Release-plan-commit:` line" in judged.problem


def test_a_merge_with_no_release_commit_has_nothing_to_judge(tmp_path: Path) -> None:
    source_kit = _kit(tmp_path)
    base = _git(tmp_path, "rev-parse", "HEAD")
    head = _commit(tmp_path, "feat: a change", {"src/seed.txt": "y\n"})
    assert release.check_queue(source_kit, base, head) == []


def _check_queue(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, base: str) -> tuple[int, str]:
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(main, ["release", "check-queue", "--base", base])
    return result.exit_code, result.output


def test_the_command_passes_a_sound_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, base, _ = _queue(tmp_path)
    code, output = _check_queue(tmp_path, monkeypatch, base)
    assert code == 0, output
    assert "lands sound" in output and "every release commit in this merge lands sound" in output


def test_the_command_fails_a_release_without_the_trailer_naming_the_way_on(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, base, _ = _queue(tmp_path, trailer=False)
    code, output = _check_queue(tmp_path, monkeypatch, base)
    assert code == 1
    assert "does not land sound" in output
    assert "Run the release again" in output and "never amend the release commit" in output


def test_the_command_passes_a_merge_with_no_release_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _kit(tmp_path)
    base = _git(tmp_path, "rev-parse", "HEAD")
    _commit(tmp_path, "feat: a change", {"src/seed.txt": "y\n"})
    code, output = _check_queue(tmp_path, monkeypatch, base)
    assert code == 0 and "no release commit in this merge" in output


# --- `pkit release merge` at its request -----------------------------------------


def _origin(tmp_path: Path, *, source: bool = False) -> tuple[Path, Path, str]:
    """A bare `origin`, and a clone of it holding the source kit on `main`;
    the clone's root, the origin, and `main`'s head. `source` as for `_kit`."""
    origin = tmp_path / "origin.git"
    _git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    clone = tmp_path / "clone"
    _kit(clone, source=source)
    _git(clone, "remote", "add", "origin", str(origin))
    _git(clone, "push", "-q", "origin", "main")
    return clone, origin, _git(clone, "rev-parse", "HEAD")


def _open(clone: Path, head: str) -> None:
    """The release PR opened from `head`: its branch and `refs/pull/<n>/head` on `origin`."""
    _git(clone, "push", "-q", "-f", "origin", f"{head}:refs/heads/{BRANCH}")
    _git(clone, "push", "-q", "-f", "origin", f"{head}:refs/pull/{NUMBER}/head")


def _pr(head: str, body: str) -> release.ReleasePrState:
    return release.ReleasePrState(
        number=NUMBER,
        title=TITLE,
        state="OPEN",
        head_ref=BRANCH,
        head_oid=head,
        base_ref="main",
        cross_repository=False,
        url=f"https://github.com/owner/repo/pull/{NUMBER}",
        mergeable="MERGEABLE",
        checks_passing=True,
        failing_checks=(),
        body=body,
    )


def _body(plan: str) -> str:
    return f"Automated release PR.\n\n{release.plan_commit_line(plan)}\n"


def _released(
    tmp_path: Path, *, source: bool = False, extra: dict[str, str | None] | None = None
) -> tuple[Path, Path, str, str]:
    """A release PR open on `origin`, planned from `main`'s head, its release
    commit holding `extra` beside the release step's writes; the clone, the
    origin, the plan's commit and the PR's head. `source` as for `_kit`."""
    clone, origin, plan = _origin(tmp_path, source=source)
    _git(clone, "checkout", "-q", "-b", BRANCH)
    head = _release(clone, plan, extra=extra)
    _git(clone, "checkout", "-q", "main")
    _open(clone, head)
    return clone, origin, plan, head


def test_a_release_pr_planned_from_the_bases_head_lands_sound(tmp_path: Path) -> None:
    clone, _, plan, head = _released(tmp_path)
    assert release.release_pr_problem(_pr(head, _body(plan)), clone) is None


def test_the_commits_are_fetched_where_the_clone_does_not_hold_them(tmp_path: Path) -> None:
    """Another clone made the release; this one has never seen it."""
    clone, origin, plan = _origin(tmp_path)
    maker = tmp_path / "maker"
    _git(tmp_path, "clone", "-q", str(origin), str(maker))
    sign_nothing(maker)
    _git(maker, "config", "user.email", "t@example.com")
    _git(maker, "config", "user.name", "T")
    head = _release(maker, plan)
    _open(maker, head)
    assert subprocess.run(["git", "cat-file", "-e", head], cwd=clone, check=False).returncode != 0
    assert release.release_pr_problem(_pr(head, _body(plan)), clone) is None


def test_a_body_without_the_trailer_is_refused(tmp_path: Path) -> None:
    clone, _, _, head = _released(tmp_path)
    problem = release.release_pr_problem(_pr(head, "No trailer here.\n"), clone)
    assert problem is not None and "its body carries no `Release-plan-commit:` line" in problem


def test_a_body_naming_another_commit_than_the_release_commit_is_refused(tmp_path: Path) -> None:
    clone, _, plan, head = _released(tmp_path)
    problem = release.release_pr_problem(_pr(head, _body(plan) + _body(OTHER)), clone)
    assert problem is not None
    assert f"its body names {plan[:12]}, {OTHER[:12]}" in problem


def test_a_release_branch_whose_commits_carry_no_trailer_is_refused(tmp_path: Path) -> None:
    clone, _, plan = _origin(tmp_path)
    _git(clone, "checkout", "-q", "-b", BRANCH)
    head = _release(clone, None)
    _open(clone, head)
    problem = release.release_pr_problem(_pr(head, _body(plan)), clone)
    assert problem is not None and "carries a `Release-plan-commit:` line" in problem


def test_two_commits_carrying_the_trailer_are_refused(tmp_path: Path) -> None:
    clone, _, plan = _origin(tmp_path)
    _git(clone, "checkout", "-q", "-b", BRANCH)
    _release(clone, plan)
    head = _commit(
        clone,
        f"docs: answers\n\n{release.plan_commit_line(plan)}",
        {_answer_file(): "answers: []\n"},
    )
    _open(clone, head)
    problem = release.release_pr_problem(_pr(head, _body(plan)), clone)
    assert problem is not None and "2 commits of release/v1.6.0 carry the trailer line" in problem


def test_a_release_planned_before_the_base_moved_is_refused(tmp_path: Path) -> None:
    """A pull request merged after the plan: the base's head, read from the
    remote, is no longer the plan's commit."""
    clone, _, plan, head = _released(tmp_path)
    _commit(clone, "feat: merged since", {"src/seed.txt": "y\n"})
    _git(clone, "push", "-q", "origin", "main")
    _git(clone, "reset", "-q", "--hard", plan)  # the clone has not pulled: the remote is read
    problem = release.release_pr_problem(_pr(head, _body(plan)), clone)
    assert problem is not None and "the default branch has moved" in problem


def test_a_commit_pushed_onto_the_release_branch_is_refused(tmp_path: Path) -> None:
    clone, _, plan = _origin(tmp_path)
    _git(clone, "checkout", "-q", "-b", BRANCH)
    _release(clone, plan)
    head = _commit(clone, "fix: pushed onto the release", {"src/seed.txt": "y\n"})
    _open(clone, head)
    problem = release.release_pr_problem(_pr(head, _body(plan)), clone)
    assert problem is not None and "holds more than `pkit release apply` writes" in problem


def test_a_base_the_remote_does_not_have_merges_nothing(tmp_path: Path) -> None:
    clone, _, plan, head = _released(tmp_path)
    pr = dataclasses.replace(_pr(head, _body(plan)), base_ref="trunk")
    with pytest.raises(release.click.ClickException) as exc:
        release.release_pr_problem(pr, clone)
    assert "refs/heads/trunk" in str(exc.value) and "Nothing was merged." in str(exc.value)


# --- A release PR records release versions alone (ADR-089 point 3) ----------------

_CANDIDATE_VERSION: dict[str, str | None] = {".pkit/VERSION": "1.6.0rc1\n"}


def test_a_release_pr_recording_a_pre_release_lands_sound_and_is_refused(tmp_path: Path) -> None:
    """In the methodology's source repository: the predicate passes it, since
    `apply` writes the backbone's `VERSION` whole, so only this refusal stops it."""
    clone, _, plan, head = _released(tmp_path, source=True, extra=_CANDIDATE_VERSION)
    pr = _pr(head, _body(plan))

    assert release.release_pr_problem(pr, clone) is None
    assert [each.named for each in release.release_pr_pre_releases(pr, clone)] == [
        ".pkit/VERSION: backbone at 1.6.0rc1"
    ]


def test_each_pre_release_a_release_pr_records_is_named(tmp_path: Path) -> None:
    package = _PACKAGE.format(version="0.6.0rc1")
    clone, _, plan, head = _released(
        tmp_path,
        source=True,
        extra={**_CANDIDATE_VERSION, ".pkit/adapters/claude-code/package.yaml": package},
    )

    recorded = release.release_pr_pre_releases(_pr(head, _body(plan)), clone)

    assert [(each.component, each.path, each.version) for each in recorded] == [
        ("backbone", ".pkit/VERSION", "1.6.0rc1"),
        ("claude-code", ".pkit/adapters/claude-code/package.yaml", "0.6.0rc1"),
    ]


def test_a_release_pr_recording_release_versions_passes(tmp_path: Path) -> None:
    clone, _, plan, head = _released(tmp_path, source=True)
    assert release.release_pr_pre_releases(_pr(head, _body(plan)), clone) == []


def test_the_head_is_fetched_where_the_clone_does_not_hold_it(tmp_path: Path) -> None:
    clone, origin, plan = _origin(tmp_path, source=True)
    maker = tmp_path / "maker"
    _git(tmp_path, "clone", "-q", str(origin), str(maker))
    sign_nothing(maker)
    _git(maker, "config", "user.email", "t@example.com")
    _git(maker, "config", "user.name", "T")
    head = _release(maker, plan, extra=_CANDIDATE_VERSION)
    _open(maker, head)

    recorded = release.release_pr_pre_releases(_pr(head, _body(plan)), clone)

    assert [each.version for each in recorded] == ["1.6.0rc1"]


def test_an_adopters_release_pr_recording_a_pre_release_passes(tmp_path: Path) -> None:
    """Outside the methodology's source repository the refusal binds nothing."""
    clone, _, plan, head = _released(tmp_path, extra=_CANDIDATE_VERSION)
    assert release.release_pr_pre_releases(_pr(head, _body(plan)), clone) == []


# --- `pkit release apply` prints the line ----------------------------------------


def test_apply_prints_the_trailer_line_naming_the_commit_its_plan_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _kit(tmp_path)
    plan = _git(tmp_path, "rev-parse", "HEAD")
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(main, ["release", "apply", "--yes"])
    assert result.exit_code == 0, result.output
    assert result.stdout.splitlines()[-1] == f"Release-plan-commit: {plan}"
    assert release.plan_commits_named(result.stdout) == [plan]


def test_apply_with_nothing_to_release_prints_no_trailer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _kit(tmp_path)
    _commit(tmp_path, "chore: nothing pending", {_CHANGESET: None})
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(main, ["release", "apply", "--yes"])
    assert result.exit_code == 0, result.output
    assert release.plan_commits_named(result.stdout) == []
