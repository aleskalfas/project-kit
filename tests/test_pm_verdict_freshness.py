"""Tests for the verdict freshness rule (#1179): the author's changes since a
reviewed head (`_lib.author_delta`), read from real git history, and the rule
that judges each verdict by them (`_lib.verdict_freshness`).

The reviewers have the shipped panel's shape: `pm-reviewer` is the baseline,
`docs-reviewer` rides the touches-code floor and a classification match (so it
is required for the whole change on any PR), and `code-reviewer` /
`security-reviewer` only the touches-code floor. The traces the issue names:

  * a clean merge of the base branch → every verdict fresh;
  * a Markdown-only fix → code and security fresh, pm and docs stale;
  * a fix outside a floor reviewer's floors → its approval stands, its
    rejection goes stale;
  * a stale latest verdict → no older fresh verdict stands in for it;
  * a code fix → every verdict stale;
  * a push during a review run → stale;
  * a rebase → stale;
  * a verdict naming no head → the commit-time rule.
"""

from __future__ import annotations

import importlib
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from tests.adopter_repo import sign_nothing

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"


@pytest.fixture(scope="module")
def lib():
    """The three modules, imported as the pm scripts import them."""
    inserted = str(SCRIPTS_DIR) not in sys.path
    if inserted:
        sys.path.insert(0, str(SCRIPTS_DIR))
    try:
        yield (
            importlib.import_module("_lib.agent_verdicts"),
            importlib.import_module("_lib.author_delta"),
            importlib.import_module("_lib.verdict_freshness"),
        )
    finally:
        if inserted:
            sys.path.remove(str(SCRIPTS_DIR))


@pytest.fixture
def av(lib):
    return lib[0]


@pytest.fixture
def ad(lib):
    return lib[1]


@pytest.fixture
def vf(lib):
    return lib[2]


# ---- a throwaway repository ---------------------------------------------


class _Repo:
    """A git repository in a temporary directory, its history built per test."""

    def __init__(self, root: Path) -> None:
        self.root = root
        root.mkdir()
        self.git("init", "-q", "-b", "main")
        sign_nothing(root)

    def git(self, *args: str) -> str:
        proc = subprocess.run(
            ["git", *args],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr
        return proc.stdout.strip()

    def commit(self, files: dict[str, str], message: str = "change") -> str:
        for path, text in files.items():
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)
        return self.head()

    def head(self, ref: str = "HEAD") -> str:
        return self.git("rev-parse", ref)


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> _Repo:
    """A repository with a base commit on `main` and a `feat` branch off it.

    Git reads no user or system configuration, so the history is the same on
    every machine.
    """
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "no-gitconfig"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for role in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{role}_NAME", "Test")
        monkeypatch.setenv(f"GIT_{role}_EMAIL", "test@example.test")
    built = _Repo(tmp_path / "repo")
    built.commit(
        {
            "README.md": "readme\n",
            "src/app.py": "x = 1\n",
            "docs/guide.md": "guide\n",
        },
        "base",
    )
    built.git("checkout", "-q", "-b", "feat")
    return built


# ---- the panel ------------------------------------------------------------

PM, DOCS, CODE, SECURITY = (
    "pm-reviewer",
    "docs-reviewer",
    "code-reviewer",
    "security-reviewer",
)
PANEL = (PM, DOCS, CODE, SECURITY)
TOUCHES_CODE = frozenset({"touches-code"})
FLOOR_ONLY = {CODE: TOUCHES_CODE, SECURITY: TOUCHES_CODE}


def _verdict(
    av,
    reviewer,
    sha,
    *,
    path=None,
    timestamp="2026-01-01T00:00:00Z",
    token=None,
    base="",
):
    return av.Verdict(
        reviewer=reviewer,
        token=token or av.APPROVED,
        path=path or av.PATH_LOCAL,
        body="",
        timestamp=timestamp,
        sha=sha,
        base=base,
    )


def _rule(vf, ad, repo, *, base_tip=None, floors=FLOOR_ONLY, head_timestamp=""):
    """The rule at the repository's current head, reading its real history."""
    head = repo.head()
    tip = repo.head("main") if base_tip is None else base_tip
    return vf.FreshnessRule(
        head_sha=head,
        head_timestamp=head_timestamp,
        base_tip=tip,
        floors_by_reviewer=floors,
        delta_since=lambda since: ad.author_delta(
            since,
            head,
            base_tip=tip,
            cwd=repo.root,
        ),
        base_kept=lambda reviewed_base: ad.base_kept(reviewed_base, tip, cwd=repo.root),
    )


def _stale(av, rule, sha, reviewers=PANEL):
    return {name for name in reviewers if not rule.is_fresh(_verdict(av, name, sha))}


# ---- the traces -------------------------------------------------------------


def test_a_clean_merge_of_the_base_leaves_every_verdict_fresh(av, ad, vf, repo) -> None:
    reviewed = repo.commit({"src/app.py": "x = 2\n"}, "feature")
    repo.git("checkout", "-q", "main")
    repo.commit({"src/lib.py": "y = 1\n", "docs/other.md": "other\n"}, "main moves")
    repo.git("checkout", "-q", "feat")
    repo.git("merge", "-q", "--no-edit", "main")

    rule = _rule(vf, ad, repo)
    assert _stale(av, rule, reviewed) == set()
    assert rule.assess(_verdict(av, PM, reviewed)).reason == (
        f"reviewed {reviewed[:7]}; only merges of the base branch since"
    )


def test_a_markdown_only_fix_keeps_code_and_security_fresh(av, ad, vf, repo) -> None:
    reviewed = repo.commit({"src/app.py": "x = 2\n"}, "feature")
    repo.commit({"README.md": "readme, fixed\n"}, "docs finding")

    rule = _rule(vf, ad, repo)
    assert _stale(av, rule, reviewed) == {PM, DOCS}
    assert rule.assess(_verdict(av, PM, reviewed)).reason == (
        f"reviewed {reviewed[:7]}; changed since: README.md"
    )
    assert rule.assess(_verdict(av, CODE, reviewed)).reason == (
        f"reviewed {reviewed[:7]}; changed since: README.md — reaches none of "
        "its floors (touches-code)"
    )


PANEL_DECLARATION = (
    REPO_ROOT / ".pkit" / "capabilities" / "software-engineering" / "review-contributions.yaml"
)


def _shipped_panel_floors(*, closing_types: tuple[str, ...]) -> dict[str, frozenset[str]]:
    """`floors_by_reviewer` the resolver gives the shipped code-review panel
    on a code PR whose closing issues carry `closing_types`."""
    from ruamel.yaml import YAML

    rc = importlib.import_module("_lib.review_contributions")
    rr = importlib.import_module("_lib.required_reviewers")
    rules, errors = rc.parse_contributions(
        YAML(typ="safe").load(PANEL_DECLARATION.read_text(encoding="utf-8")),
        "software-engineering",
    )
    assert errors == ()
    collection = rc.ContributionCollection(
        rules=rules,
        capabilities_walked=("project-management", "software-engineering"),
    )
    issues = list(range(1, len(closing_types) + 1))
    resolution = rr.resolve_required_local_reviewers(
        99,
        baseline_local=[PM],
        repo_root=REPO_ROOT,
        closing_issue_numbers=lambda _pr: issues,
        issue_labels=lambda number: [{"name": f"type:{closing_types[number - 1]}"}],
        changed_files=lambda _pr: ["src/app.py"],
        collect_contributions=lambda _root: collection,
    )
    assert resolution.ok, resolution.error
    assert set(resolution.required_local) == set(PANEL)
    return resolution.floors_by_reviewer


@pytest.mark.parametrize("closing_types", [("feature",), ()], ids=["classified", "unclassified"])
def test_a_markdown_fix_stales_the_docs_reviewer_on_any_pr(
    av,
    ad,
    vf,
    repo,
    lib,
    closing_types,
) -> None:
    """docs-reviewer rides the touches-code floor and the `type: *` match; its
    job is the documentation, so a Markdown fix stales it even on an
    unclassified PR, where only the floor required it."""
    reviewed = repo.commit({"src/app.py": "x = 2\n"}, "feature")
    repo.commit({"README.md": "readme, fixed\n"}, "docs finding")

    floors = _shipped_panel_floors(closing_types=closing_types)
    assert floors == FLOOR_ONLY
    assert _stale(av, _rule(vf, ad, repo, floors=floors), reviewed) == {PM, DOCS}


def test_a_changeset_is_not_code_for_the_floor_reviewers(av, ad, vf, repo) -> None:
    """The not-code list the resolver applies is applied to the delta too."""
    reviewed = repo.commit({"src/app.py": "x = 2\n"}, "feature")
    repo.commit({".changes/unreleased/pm-minor.yaml": "component: pm\n"}, "changeset")

    assert _stale(av, _rule(vf, ad, repo), reviewed) == {PM, DOCS}


def test_any_change_stales_a_rejection(av, ad, vf, repo) -> None:
    """Floor scoping protects an approval only. The author is answering a
    CHANGES_REQUESTED, and a fix outside the reviewer's floors — a changeset,
    a README — still stales it, so the reviewer re-reads what it blocked."""
    reviewed = repo.commit({"src/app.py": "x = 2\n"}, "feature")
    repo.commit({".changes/unreleased/pm-minor.yaml": "component: pm\n"}, "changeset")

    rule = _rule(vf, ad, repo)
    rejection = _verdict(av, CODE, reviewed, token=av.CHANGES_REQUESTED)
    assert rule.assess(rejection) == vf.Freshness(
        False,
        f"reviewed {reviewed[:7]}; changed since: .changes/unreleased/pm-minor.yaml",
    )
    assert rule.is_fresh(_verdict(av, CODE, reviewed))


def test_a_rejection_survives_a_clean_merge_of_the_base(av, ad, vf, repo) -> None:
    """A clean merge of the base is no change by the author, so a rejection
    stands as an approval does."""
    reviewed = repo.commit({"src/app.py": "x = 2\n"}, "feature")
    repo.git("checkout", "-q", "main")
    repo.commit({"src/lib.py": "y = 1\n"}, "main moves")
    repo.git("checkout", "-q", "feat")
    repo.git("merge", "-q", "--no-edit", "main")

    rejection = _verdict(av, CODE, reviewed, token=av.CHANGES_REQUESTED)
    assert _rule(vf, ad, repo).is_fresh(rejection)


def test_a_code_fix_stales_every_verdict(av, ad, vf, repo) -> None:
    reviewed = repo.commit({"src/app.py": "x = 2\n"}, "feature")
    repo.commit({"src/app.py": "x = 3\n"}, "code finding")

    rule = _rule(vf, ad, repo)
    assert _stale(av, rule, reviewed) == set(PANEL)
    assert rule.assess(_verdict(av, CODE, reviewed)).reason == (
        f"reviewed {reviewed[:7]}; changed since: src/app.py — reaches its touches-code floor"
    )


def test_a_push_during_a_review_run_stales_the_verdict(av, ad, vf, repo) -> None:
    """review-pr records the head before invoking the reviewer and posts the
    verdict against it; a commit pushed while the reviewer ran is a change
    since that head, judged like any other."""
    reviewed = repo.commit({"src/app.py": "x = 2\n"}, "feature")
    # Pushed while the reviewer was running.
    repo.commit({"src/app.py": "x = 2\nz = 0\n"}, "late push")

    assert _stale(av, _rule(vf, ad, repo), reviewed) == set(PANEL)


def test_a_rebase_stales_every_verdict(av, ad, vf, repo) -> None:
    reviewed = repo.commit({"src/app.py": "x = 2\n"}, "feature")
    repo.git("checkout", "-q", "main")
    repo.commit({"docs/other.md": "other\n"}, "main moves")
    repo.git("checkout", "-q", "feat")
    repo.git("rebase", "-q", "main")

    rule = _rule(vf, ad, repo)
    assert _stale(av, rule, reviewed) == set(PANEL)
    assert "rebased or force-pushed" in rule.assess(_verdict(av, CODE, reviewed)).reason


# ---- the gate judges each reviewer's latest verdict ---------------------


def _comment(av, reviewer, token, *, ts, sha=""):
    """A verdict comment as review-pr posts it, naming `sha` when given."""
    return {
        "author": {"login": "dev"},
        "body": av.stamp_verdict(f"Reviewer agent (local, {reviewer}): {token}", sha),
        "createdAt": ts,
    }


def _gate(av, rule, comments):
    return av.gate_verdicts(
        comments,
        is_fresh=rule.is_fresh,
        local_reviewer_ok=lambda _name: True,
        remote_reviewer_ok=lambda _login: False,
    )


def test_a_force_push_back_to_the_approved_head_does_not_revive_the_approval(
    av,
    ad,
    vf,
    repo,
) -> None:
    """The reviewer approved A, then rejected B; the author force-pushed back
    to A and added a Markdown change. The APPROVED on A reaches none of the
    reviewer's floors, but the CHANGES_REQUESTED superseded it, and that one
    is stale — so nothing counts."""
    approved_head = repo.commit({"src/app.py": "x = 2\n"}, "feature")
    rejected_head = repo.commit({"src/app.py": "x = 3\n"}, "rework")
    repo.git("reset", "-q", "--hard", approved_head)
    repo.commit({"README.md": "readme, fixed\n"}, "docs")

    rule = _rule(vf, ad, repo)
    approval = _comment(av, CODE, "APPROVED", ts="2026-06-01T00:00:00Z", sha=approved_head)
    rejection = _comment(
        av, CODE, "CHANGES_REQUESTED", ts="2026-06-02T00:00:00Z", sha=rejected_head
    )
    assert rule.is_fresh(_verdict(av, CODE, approved_head))
    assert _gate(av, rule, [approval, rejection]) == []


def test_a_stale_rejection_naming_no_head_does_not_revive_the_approval(
    av,
    ad,
    vf,
    repo,
) -> None:
    """The head could not be read when the CHANGES_REQUESTED was posted, so it
    names none and is judged by commit time; a later Markdown commit makes it
    stale. The older APPROVED it superseded does not count again."""
    approved_head = repo.commit({"src/app.py": "x = 2\n"}, "feature")
    repo.commit({"README.md": "readme, fixed\n"}, "docs")

    rule = _rule(vf, ad, repo, head_timestamp="2026-06-03T00:00:00Z")
    approval = _comment(av, CODE, "APPROVED", ts="2026-06-01T00:00:00Z", sha=approved_head)
    rejection = _comment(av, CODE, "CHANGES_REQUESTED", ts="2026-06-02T00:00:00Z")
    assert rule.is_fresh(_verdict(av, CODE, approved_head))
    assert _gate(av, rule, [approval, rejection]) == []


def test_a_verdict_naming_no_head_follows_the_commit_time(av, vf) -> None:
    rule = vf.FreshnessRule(
        head_timestamp="2026-06-05T00:00:00Z",
        floors_by_reviewer=FLOOR_ONLY,
        delta_since=lambda since: pytest.fail("no head is named"),
    )
    after = _verdict(av, CODE, "", timestamp="2026-06-06T00:00:00Z")
    at = _verdict(av, CODE, "", timestamp="2026-06-05T00:00:00Z")
    assert rule.assess(after) == vf.Freshness(
        True,
        "no reviewed head recorded; posted after the latest commit",
    )
    assert rule.assess(at) == vf.Freshness(
        False,
        "no reviewed head recorded; posted before the latest commit",
    )
    assert vf.FreshnessRule().assess(after) == vf.Freshness(
        False,
        "no reviewed head recorded; the latest commit's time is unknown",
    )


# ---- the base a verdict was reviewed against ---------------------------------


def test_a_retargeted_stacked_pr_stales_every_verdict(av, ad, vf, repo) -> None:
    """A stacked PR reviewed over its parent branch, then retargeted onto
    main once that parent was abandoned: no new commit, yet the PR's diff
    over main now carries the parent's commits, which nobody reviewed."""
    repo.git("checkout", "-q", "-b", "parent", "main")
    parent_tip = repo.commit({"src/parent.py": "p = 1\n"}, "parent work")
    repo.git("checkout", "-q", "-B", "feat", "parent")
    reviewed = repo.commit({"src/app.py": "x = 2\n"}, "feature")

    retargeted = _rule(vf, ad, repo, base_tip=repo.head("main"))
    pinned = _verdict(av, CODE, reviewed, base=parent_tip)
    assessment = retargeted.assess(pinned)
    assert not assessment.fresh
    assert assessment.reason == (
        f"reviewed {reviewed[:7]} against base {parent_tip[:7]}, which the base "
        "branch no longer contains — the pull request was retargeted or its base "
        "rewritten"
    )
    # Over the base it was reviewed against, the same verdict stands.
    assert _rule(vf, ad, repo, base_tip=parent_tip).is_fresh(pinned)
    # A marker naming no base predates the pin and is not checked.
    assert retargeted.is_fresh(_verdict(av, CODE, reviewed))


def test_a_base_that_moved_forward_keeps_the_verdict(av, ad, vf, repo) -> None:
    reviewed = repo.commit({"src/app.py": "x = 2\n"}, "feature")
    reviewed_base = repo.head("main")
    repo.git("checkout", "-q", "main")
    repo.commit({"src/lib.py": "y = 1\n"}, "main moves")
    repo.git("checkout", "-q", "feat")

    rule = _rule(vf, ad, repo)
    assert rule.assess(_verdict(av, PM, reviewed, base=reviewed_base)) == vf.Freshness(
        True,
        f"reviewed the current head {reviewed[:7]}",
    )


def test_a_rewritten_base_stales_the_verdict(av, ad, vf, repo) -> None:
    reviewed = repo.commit({"src/app.py": "x = 2\n"}, "feature")
    repo.git("checkout", "-q", "main")
    discarded = repo.commit({"src/lib.py": "y = 1\n"}, "main moves")
    repo.git("reset", "-q", "--hard", "HEAD~1")
    repo.commit({"src/lib.py": "y = 2\n"}, "main rewritten")
    repo.git("checkout", "-q", "feat")

    assert not _rule(vf, ad, repo).is_fresh(_verdict(av, PM, reviewed, base=discarded))


def test_a_base_that_cannot_be_read_stales_the_verdict(av, vf) -> None:
    rule = vf.FreshnessRule(head_sha="a" * 40, base_tip="c" * 40)
    assessment = rule.assess(_verdict(av, PM, "a" * 40, base="d" * 40))
    assert assessment == vf.Freshness(
        False,
        "reviewed aaaaaaa against base ddddddd; whether the base branch still "
        "contains it cannot be read: the base branch's head is unknown",
    )


# ---- what a merge contributes ------------------------------------------------


def test_an_edit_made_inside_a_merge_is_the_authors_change(av, ad, vf, repo) -> None:
    reviewed = repo.commit({"src/app.py": "x = 2\n"}, "feature")
    repo.git("checkout", "-q", "main")
    repo.commit({"docs/other.md": "other\n"}, "main moves")
    repo.git("checkout", "-q", "feat")
    repo.git("merge", "-q", "--no-commit", "main")
    (repo.root / "src" / "app.py").write_text("x = 99\n", encoding="utf-8")
    repo.git("add", "-A")
    repo.git("commit", "-q", "--no-edit")

    delta = ad.author_delta(
        reviewed,
        repo.head(),
        base_tip=repo.head("main"),
        cwd=repo.root,
    )
    assert delta.paths == ("src/app.py",)
    assert _stale(av, _rule(vf, ad, repo), reviewed) == set(PANEL)


def test_a_resolved_conflict_is_the_authors_change(av, ad, vf, repo) -> None:
    reviewed = repo.commit({"README.md": "readme, the feature's way\n"}, "feature")
    repo.git("checkout", "-q", "main")
    repo.commit({"README.md": "readme, the base's way\n"}, "main moves")
    repo.git("checkout", "-q", "feat")
    proc = subprocess.run(
        ["git", "merge", "-q", "main"],
        cwd=repo.root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0  # the conflict
    (repo.root / "README.md").write_text("readme, both ways\n", encoding="utf-8")
    repo.git("add", "-A")
    repo.git("commit", "-q", "--no-edit")

    delta = ad.author_delta(
        reviewed,
        repo.head(),
        base_tip=repo.head("main"),
        cwd=repo.root,
    )
    assert delta.paths == ("README.md",)
    assert _stale(av, _rule(vf, ad, repo), reviewed) == {PM, DOCS}


def test_a_merge_of_another_branch_is_the_authors_change(av, ad, vf, repo) -> None:
    """Only the base branch is reviewed elsewhere; what any other merge brings
    in counts as the author's own change."""
    reviewed = repo.commit({"src/app.py": "x = 2\n"}, "feature")
    repo.git("checkout", "-q", "-b", "side", "main")
    repo.commit({"src/side.py": "s = 1\n"}, "side work")
    repo.git("checkout", "-q", "feat")
    repo.git("merge", "-q", "--no-edit", "side")

    delta = ad.author_delta(
        reviewed,
        repo.head(),
        base_tip=repo.head("main"),
        cwd=repo.root,
    )
    assert delta.paths == ("src/side.py",)


def test_the_delta_names_each_stretch_of_the_authors_change(ad, repo) -> None:
    """Each run of the author's own commits between merges of the base is a
    stretch, and so is a merge of the base the author changed something
    inside. A clean merge is none, and it ends the run before it (#1386)."""
    reviewed = repo.commit({"src/app.py": "x = 2\n"}, "feature")
    zeroth = repo.commit({"src/app.py": "x = 4\n"}, "first fix")
    first = repo.commit({"src/app.py": "x = 3\n"}, "fix")
    repo.git("checkout", "-q", "main")
    repo.commit({"docs/other.md": "other\n"}, "main moves")
    repo.git("checkout", "-q", "feat")
    repo.git("merge", "-q", "--no-edit", "main")
    clean = repo.head()
    second = repo.commit({"README.md": "readme, fixed\n"}, "docs")
    repo.git("checkout", "-q", "main")
    repo.commit({"docs/more.md": "more\n"}, "main moves again")
    repo.git("checkout", "-q", "feat")
    repo.git("merge", "-q", "--no-commit", "main")
    (repo.root / "src" / "app.py").write_text("x = 99\n", encoding="utf-8")
    repo.git("add", "-A")
    repo.git("commit", "-q", "--no-edit")
    edited = repo.head()

    delta = ad.author_delta(reviewed, edited, base_tip=repo.head("main"), cwd=repo.root)
    assert delta.paths == ("README.md", "src/app.py")
    assert zeroth != first
    assert delta.stretches == (
        ad.Stretch(reviewed, first),
        ad.Stretch(clean, second),
        ad.Stretch(second, edited),
    )


# ---- when the delta cannot be computed: stale -------------------------------


def _clone(repo: _Repo, name: str, *args: str) -> _Repo:
    """A clone of `repo`, which is its `origin`."""
    clone = _Repo.__new__(_Repo)
    clone.root = repo.root.parent / name
    subprocess.run(
        ["git", "clone", "-q", *args, f"file://{repo.root}", str(clone.root)],
        check=True,
        capture_output=True,
    )
    return clone


def test_a_head_missing_here_is_fetched_from_origin_first(ad, repo) -> None:
    """The PR moved on origin since this checkout last fetched: the missing
    head is fetched by its object name and the changes read from it — never a
    stale verdict for want of a fetch."""
    reviewed = repo.commit({"src/app.py": "x = 2\n"}, "feature")
    clone = _clone(repo, "clone", "--branch", "feat")
    head = repo.commit({"README.md": "readme, fixed\n"}, "docs finding")
    assert not ad.author_delta(reviewed, head, base_tip=repo.head("main"), cwd=repo.root).error

    delta = ad.author_delta(reviewed, head, base_tip=clone.head("origin/main"), cwd=clone.root)
    assert delta == ad.AuthorDelta(paths=("README.md",), stretches=(ad.Stretch(reviewed, head),))


def test_a_reviewed_head_origin_cannot_provide_names_the_fetch(ad, repo) -> None:
    clone = _clone(repo, "clone", "--branch", "feat")
    delta = ad.author_delta("d" * 40, clone.head(), base_tip=clone.head(), cwd=clone.root)
    assert delta.error.startswith(
        "the reviewed head, ddddddd, is not in this checkout and could not be fetched from origin: "
    )


def test_a_shallow_checkout_is_named_rather_than_called_a_rebase(ad, repo) -> None:
    """In a shallow checkout the reviewed head can be fetched yet still not
    look like an ancestor of the PR's head — the history between is not here.
    That is unfetched history, not a rebase, and the reason says so."""
    reviewed = repo.commit({"src/app.py": "x = 2\n"}, "feature")
    head = repo.commit({"README.md": "readme, fixed\n"}, "docs finding")
    shallow = _clone(repo, "shallow", "--depth", "1", "--branch", "feat")

    delta = ad.author_delta(reviewed, head, base_tip=repo.head("main"), cwd=shallow.root)
    assert delta.error == (
        f"this checkout is shallow, so whether {reviewed[:7]} is still in the "
        "branch's history cannot be told — fetch the full history "
        "(`git fetch --unshallow origin`)"
    )


def test_a_fetch_never_prompts_for_credentials(ad) -> None:
    fetches: list[dict] = []

    def no_commits(argv, **kwargs):
        if argv[1] == "fetch":
            fetches.append(kwargs.get("env") or {})
            return subprocess.CompletedProcess(argv, 128, "", "fatal: could not read Username\n")
        return subprocess.CompletedProcess(argv, 1, "", "")

    delta = ad.author_delta("a" * 40, "b" * 40, base_tip="", run=no_commits)
    assert delta.error == (
        "the reviewed head, aaaaaaa, is not in this checkout and could not be "
        "fetched from origin: fatal: could not read Username"
    )
    assert [env.get("GIT_TERMINAL_PROMPT") for env in fetches] == ["0"]


def test_a_base_missing_here_is_fetched_from_origin_first(ad, repo) -> None:
    clone = _clone(repo, "clone", "--branch", "feat")
    reviewed_base = clone.head("origin/main")
    repo.git("checkout", "-q", "main")
    moved = repo.commit({"src/lib.py": "y = 1\n"}, "main moves")

    assert ad.base_kept(reviewed_base, moved, cwd=clone.root) == ad.BaseCheck(kept=True)


def test_a_reviewed_head_not_in_this_checkout_is_stale(ad, repo) -> None:
    delta = ad.author_delta(
        "d" * 40,
        repo.head(),
        base_tip=repo.head("main"),
        cwd=repo.root,
    )
    assert not delta.ok
    assert "is not in this checkout" in delta.error


def test_a_reviewed_head_that_reached_the_branch_through_a_merge_is_stale(
    ad,
    repo,
) -> None:
    repo.git("checkout", "-q", "-b", "side", "main")
    reviewed = repo.commit({"src/side.py": "s = 1\n"}, "reviewed elsewhere")
    repo.git("checkout", "-q", "feat")
    repo.commit({"src/app.py": "x = 2\n"}, "feature")
    repo.git("merge", "-q", "--no-edit", "side")

    delta = ad.author_delta(
        reviewed,
        repo.head(),
        base_tip=repo.head("main"),
        cwd=repo.root,
    )
    assert "not on the branch's own line of commits" in delta.error


def test_an_unknown_base_stales_only_when_a_merge_needs_it(ad, repo) -> None:
    reviewed = repo.commit({"src/app.py": "x = 2\n"}, "feature")
    repo.commit({"README.md": "readme, fixed\n"}, "fix")
    assert ad.author_delta(
        reviewed,
        repo.head(),
        base_tip="",
        cwd=repo.root,
    ).paths == ("README.md",)

    repo.git("checkout", "-q", "main")
    repo.commit({"docs/other.md": "other\n"}, "main moves")
    repo.git("checkout", "-q", "feat")
    repo.git("merge", "-q", "--no-edit", "main")
    unknown = ad.author_delta(reviewed, repo.head(), base_tip="", cwd=repo.root)
    assert "the base branch's head is unknown" in unknown.error
    missing = ad.author_delta(
        reviewed,
        repo.head(),
        base_tip="e" * 40,
        cwd=repo.root,
    )
    assert (
        "the base branch's head, eeeeeee, is not in this checkout and could not be "
        "fetched from origin: "
    ) in missing.error


def test_a_git_without_merge_tree_write_tree_is_stale(ad, repo) -> None:
    """git older than 2.38 refuses `merge-tree --write-tree`."""
    reviewed = repo.commit({"src/app.py": "x = 2\n"}, "feature")
    repo.git("checkout", "-q", "main")
    repo.commit({"docs/other.md": "other\n"}, "main moves")
    repo.git("checkout", "-q", "feat")
    repo.git("merge", "-q", "--no-edit", "main")

    def old_git(argv, **kwargs):
        if argv[1:3] == ["merge-tree", "--write-tree"]:
            return subprocess.CompletedProcess(
                argv,
                129,
                "",
                "error: unknown option `write-tree'",
            )
        return subprocess.run(argv, **kwargs)

    delta = ad.author_delta(
        reviewed,
        repo.head(),
        base_tip=repo.head("main"),
        cwd=repo.root,
        run=old_git,
    )
    assert "needs git 2.38 or later" in delta.error


def test_git_missing_is_stale(ad) -> None:
    def no_git(argv, **kwargs):
        raise FileNotFoundError("git")

    delta = ad.author_delta("a" * 40, "b" * 40, base_tip="", run=no_git)
    assert delta.error.startswith("git could not run")


def test_an_unknown_head_is_stale(ad) -> None:
    assert ad.author_delta("a" * 40, "", base_tip="").error == (
        "the pull request's head is unknown"
    )


# ---- the rule's own behaviour -----------------------------------------------


def test_the_reviewed_head_itself_is_fresh_without_reading_git(av, vf) -> None:
    sha = "a" * 40
    rule = vf.FreshnessRule(
        head_sha=sha,
        delta_since=lambda since: pytest.fail("not read"),
    )
    assert rule.assess(_verdict(av, PM, sha)) == vf.Freshness(
        True,
        "reviewed the current head aaaaaaa",
    )


def test_the_delta_is_read_once_per_reviewed_head(av, ad, vf) -> None:
    reads: list[str] = []

    def delta(since):
        reads.append(since)
        return ad.AuthorDelta(paths=("README.md",))

    rule = vf.FreshnessRule(
        head_sha="b" * 40,
        floors_by_reviewer=FLOOR_ONLY,
        delta_since=delta,
    )
    for name in PANEL:
        rule.is_fresh(_verdict(av, name, "a" * 40))
    assert reads == ["a" * 40]


def test_a_remote_verdict_is_held_to_any_change(av, ad, vf) -> None:
    """Contributed reviewers register on the local path only, so a remote
    verdict is a baseline one, whatever its login."""
    rule = vf.FreshnessRule(
        head_sha="b" * 40,
        floors_by_reviewer=FLOOR_ONLY,
        delta_since=lambda since: ad.AuthorDelta(paths=("README.md",)),
    )
    remote = _verdict(av, CODE, "a" * 40, path=av.PATH_REMOTE)
    assert not rule.is_fresh(remote)


def test_a_long_change_is_named_in_part(av, ad, vf) -> None:
    paths = tuple(f"docs/page_{i}.md" for i in range(8))
    rule = vf.FreshnessRule(
        head_sha="b" * 40,
        delta_since=lambda since: ad.AuthorDelta(paths=paths),
    )
    assert rule.assess(_verdict(av, PM, "a" * 40)).reason.endswith(
        "docs/page_3.md, docs/page_4.md (+3 more)"
    )


def test_the_defaults_are_fail_closed(av, vf) -> None:
    rule = vf.FreshnessRule()
    assert not rule.is_fresh(_verdict(av, CODE, "a" * 40))
    assert not rule.is_fresh(_verdict(av, CODE, ""))


def test_rule_for_pr_reads_the_pr_view_and_the_resolution(av, ad, vf) -> None:
    calls: list[tuple] = []

    def delta(since, head, *, base_tip):
        calls.append((since, head, base_tip))
        return ad.AuthorDelta(paths=(".changes/unreleased/x.yaml",))

    bases: list[tuple] = []

    def base_kept(reviewed_base, base_tip):
        bases.append((reviewed_base, base_tip))
        return ad.BaseCheck(kept=False)

    resolution_module = importlib.import_module("_lib.required_reviewers")
    resolution = resolution_module.Resolution(
        floors_by_reviewer=FLOOR_ONLY,
        not_code=resolution_module.NotCode(patterns=()),
    )
    rule = vf.rule_for_pr(
        {
            "headRefOid": "b" * 40,
            "baseRefOid": "c" * 40,
            "commits": [{"committedDate": "2026-06-05T00:00:00Z"}],
        },
        resolution,
        author_delta=delta,
        base_kept=base_kept,
    )
    # The resolution's not-code list excludes nothing here, so a changeset is
    # code and reaches the floor.
    assert not rule.is_fresh(_verdict(av, CODE, "a" * 40))
    assert calls == [("a" * 40, "b" * 40, "c" * 40)]
    # A recorded base is checked against the PR's base.
    assert not rule.is_fresh(_verdict(av, PM, "b" * 40, base="e" * 40))
    assert bases == [("e" * 40, "c" * 40)]
    # A verdict naming no head is judged by the PR's latest commit.
    assert rule.is_fresh(_verdict(av, PM, "", timestamp="2026-06-06T00:00:00Z"))


def test_head_sha_falls_back_to_the_last_commit(vf) -> None:
    assert vf.head_sha({"headRefOid": "b" * 40}) == "b" * 40
    assert vf.head_sha({"commits": [{"oid": "x"}, {"oid": "y"}]}) == "y"
    assert vf.head_sha({}) == ""


# ---- the touches-ruled-artefact floor (#1386) ---------------------------------
#
# A reviewer contributed by the floor alone keeps its approval while the
# author's own changes reach nothing the floor counts. The backbone is asked
# what the author's changes since the review altered, a run of the author's
# own commits between merges of the base at a time — a merge of the base only
# when the author changed something inside it, a clean merge never. An altered
# artefact counts when a rule binds on it at the start or the end of its run
# (DEC-028).

RULES = "rule-set-reviewer"
RULED_FLOOR = {RULES: frozenset({"touches-ruled-artefact"})}
GUIDE = "docs/guide.md"


def _altered(location, change="changed", *, paths=None, ruled=True):
    """One artefact the backbone lists as altered."""
    ruled_artefacts = importlib.import_module("_lib.ruled_artefacts")
    return ruled_artefacts.AlteredArtefact(
        location=location, change=change, paths=tuple(paths or (location,)), ruled=ruled
    )


# What the stand-in backbone answers: the altered artefacts, a reason it cannot
# answer, or a function of the stretch (start, end) giving either.
Answer = list | str | Callable[[str, str], "list | str"]


def _ruled_rule(vf, ad, repo, answer: Answer, asked, *, floors=None):
    """The rule at the repository's current head, its author's changes read from
    real git, the backbone stood in by `answer` (the artefacts it lists as
    altered, a reason it cannot answer, or a function of the stretch giving
    either); each question lands in `asked` as (start, end)."""
    ruled_artefacts = importlib.import_module("_lib.ruled_artefacts")
    head = repo.head()

    def ruled(start, end):
        asked.append((start, end))
        said = answer(start, end) if callable(answer) else answer
        if isinstance(said, str):
            return ruled_artefacts.RuledAlteration(error=said)
        return ruled_artefacts.RuledAlteration(artefacts=tuple(said))

    resolution_module = importlib.import_module("_lib.required_reviewers")
    return vf.rule_for_pr(
        {"headRefOid": head, "baseRefOid": repo.head("main"), "commits": []},
        resolution_module.Resolution(floors_by_reviewer=floors or RULED_FLOOR),
        author_delta=lambda since, at, *, base_tip: ad.author_delta(
            since, at, base_tip=base_tip, cwd=repo.root
        ),
        base_kept=lambda reviewed_base, tip: ad.base_kept(reviewed_base, tip, cwd=repo.root),
        ruled_altered=ruled,
    )


def test_a_code_only_push_keeps_the_ruled_floor_s_approval(av, ad, vf, repo) -> None:
    reviewed = repo.commit({GUIDE: "guide, reviewed\n"}, "page")
    head = repo.commit({"src/app.py": "x = 2\n"}, "code fix")
    asked: list[tuple] = []
    rule = _ruled_rule(vf, ad, repo, [], asked)
    assessed = rule.assess(_verdict(av, RULES, reviewed))
    assert assessed.fresh, assessed.reason
    assert assessed.reason.endswith("reaches none of its floors (touches-ruled-artefact)")
    # No path says the question may be skipped: the backbone is asked.
    assert asked == [(reviewed, head)]


def test_a_push_altering_a_ruled_artefact_stales_the_approval(av, ad, vf, repo) -> None:
    reviewed = repo.commit({"src/app.py": "x = 2\n"}, "code")
    head = repo.commit({GUIDE: "guide, rewritten\n"}, "page fix")
    asked: list[tuple] = []
    rule = _ruled_rule(vf, ad, repo, [_altered(GUIDE)], asked)
    assessed = rule.assess(_verdict(av, RULES, reviewed))
    assert not assessed.fresh
    assert assessed.reason.endswith("reaches its touches-ruled-artefact floor")
    # Asked from the reviewed head to the PR's head.
    assert asked == [(reviewed, head)]


def test_a_push_to_the_declared_places_alone_stales_the_approval(av, ad, vf, repo) -> None:
    """The author changes only the configuration, bringing a ruled page into the
    declared places. The backbone lists the page as added though no file of it
    changed, and the PR's own change alters it, so the approval goes stale."""
    reviewed = repo.commit({GUIDE: "guide, reviewed\n"}, "page")
    repo.commit({".pkit/project/config.yaml": "friction: {}\n"}, "a new place")
    added = _altered("docs/notes/n.md", "added")
    asked: list[tuple] = []
    rule = _ruled_rule(vf, ad, repo, [added], asked)
    assessed = rule.assess(_verdict(av, RULES, reviewed))
    assert not assessed.fresh
    assert assessed.reason.endswith("reaches its touches-ruled-artefact floor")


def test_an_edit_a_later_commit_brings_under_a_rule_stales_the_approval(av, ad, vf, repo) -> None:
    """After the review the author edits a page no rule binds on, then accepts a
    rule that binds on it. Both commits are one run, read together: the page
    is altered, and a rule binds on it at the run's end, so the approval goes
    stale, as the resolver counts the page for the PR (DEC-028)."""
    reviewed = repo.commit({GUIDE: "guide, reviewed\n"}, "page")
    repo.commit({"README.md": "readme, edited\n"}, "readme")
    accept = repo.commit({"docs/rules.md": "RS-DOC-001 accepted\n"}, "accept a rule")
    asked: list[tuple] = []
    rule = _ruled_rule(vf, ad, repo, [_altered("README.md")], asked)
    assessed = rule.assess(_verdict(av, RULES, reviewed))
    assert not assessed.fresh
    assert assessed.reason.endswith("reaches its touches-ruled-artefact floor")
    assert asked == [(reviewed, accept)]


def test_a_rule_only_commit_keeps_the_approval(av, ad, vf, repo) -> None:
    """After the review the author only accepts a rule over a page the review
    saw. A change to the rules alone alters no page they govern, so the
    backbone lists none and the approval stands (DEC-028)."""
    reviewed = repo.commit({GUIDE: "guide, reviewed\n"}, "page")
    accept = repo.commit({"docs/rules.md": "RS-DOC-001 accepted\n"}, "accept a rule")
    asked: list[tuple] = []
    rule = _ruled_rule(vf, ad, repo, [], asked)
    assert rule.assess(_verdict(av, RULES, reviewed)).fresh
    assert asked == [(reviewed, accept)]


def test_an_edit_undone_within_a_run_keeps_the_approval(av, ad, vf, repo) -> None:
    """The author edits a ruled page and then undoes the edit. The run is read
    whole, so the backbone sees no change to the page (COR-050 point 5)."""
    reviewed = repo.commit({GUIDE: "guide, reviewed\n"}, "page")
    repo.commit({GUIDE: "guide, rewritten\n"}, "page fix")
    undone = repo.commit({GUIDE: "guide, reviewed\n"}, "undo the page fix")

    def answer(start, end):
        return [] if (start, end) == (reviewed, undone) else [_altered(GUIDE)]

    asked: list[tuple] = []
    rule = _ruled_rule(vf, ad, repo, answer, asked)
    assessed = rule.assess(_verdict(av, RULES, reviewed))
    assert assessed.fresh, assessed.reason
    assert asked == [(reviewed, undone)]


def test_changed_paths_without_a_stretch_stale_the_approval(av, vf) -> None:
    """A reader of the author's changes that names paths but no stretch to ask
    the backbone about cannot say the change alters no ruled artefact."""
    ad_module = importlib.import_module("_lib.author_delta")
    asked: list[tuple] = []

    def ruled(start, end):
        asked.append((start, end))
        return importlib.import_module("_lib.ruled_artefacts").RuledAlteration()

    rule = vf.FreshnessRule(
        head_sha="h" * 40,
        base_tip="b" * 40,
        floors_by_reviewer=RULED_FLOOR,
        delta_since=lambda since: ad_module.AuthorDelta(paths=(GUIDE,)),
        ruled_since=ruled,
    )
    assessed = rule.assess(_verdict(av, RULES, "r" * 40))
    assert not assessed.fresh
    assert "name no stretch to ask the backbone about" in assessed.reason
    assert asked == []


def test_a_push_the_backbone_counts_nothing_for_keeps_the_approval(av, ad, vf, repo) -> None:
    """Only a revalidation written, a page outside every scope, or a page the
    PR's own change does not alter: nothing the floor counts."""
    reviewed = repo.commit({GUIDE: "guide, reviewed\n"}, "page")
    repo.commit({"README.md": "readme, rewritten\n"}, "readme")
    asked: list[tuple] = []
    outside = _altered("README.md", ruled=False)
    rule = _ruled_rule(vf, ad, repo, [outside], asked)
    assert rule.assess(_verdict(av, RULES, reviewed)).fresh
    assert len(asked) == 1


def test_a_clean_merge_of_the_base_keeps_the_ruled_floor_s_approval(av, ad, vf, repo) -> None:
    """The base changed a ruled page; merging it cleanly is no change of the
    author's, so the backbone is not even asked."""
    reviewed = repo.commit({"src/app.py": "x = 2\n"}, "feature")
    repo.git("checkout", "-q", "main")
    repo.commit({GUIDE: "guide, changed on main\n"}, "main moves")
    repo.git("checkout", "-q", "feat")
    repo.git("merge", "-q", "--no-edit", "main")
    asked: list[tuple] = []
    rule = _ruled_rule(vf, ad, repo, [_altered(GUIDE)], asked)
    assessed = rule.assess(_verdict(av, RULES, reviewed))
    assert assessed.fresh and assessed.reason.endswith("only merges of the base branch since")
    assert asked == []


def test_a_clean_merge_beside_a_push_is_never_asked_about(av, ad, vf, repo) -> None:
    """The author pushes a code fix and merges the base cleanly; the base added
    a page the PR's own change now counts. Only the author's own run is asked
    about, so what the base brought never counts, whether or not the author
    pushed beside it."""
    reviewed = repo.commit({GUIDE: "guide, the PR's\n"}, "the PR's edit")
    repo.git("checkout", "-q", "main")
    repo.commit({"docs/other.md": "other\n", "README.md": "readme, main's\n"}, "main moves")
    repo.git("checkout", "-q", "feat")
    fix = repo.commit({"src/app.py": "x = 2\n"}, "code fix")
    repo.git("merge", "-q", "--no-edit", "main")
    asked: list[tuple] = []

    def answer(start, end):
        return [] if (start, end) == (reviewed, fix) else [_altered("docs/other.md", "added")]

    rule = _ruled_rule(vf, ad, repo, answer, asked)
    assessed = rule.assess(_verdict(av, RULES, reviewed))
    assert assessed.fresh, assessed.reason
    assert assessed.reason.endswith("reaches none of its floors (touches-ruled-artefact)")
    assert asked == [(reviewed, fix)]


def test_a_merge_the_author_changed_something_inside_counts_whole(av, ad, vf, repo) -> None:
    """The author edits a file while merging the base. No path tells what that
    edit brought into the declared places, so all the merge altered is asked
    about and counts, a ruled page the base added included."""
    reviewed = repo.commit({"src/app.py": "x = 2\n"}, "feature")
    repo.git("checkout", "-q", "main")
    repo.commit({"docs/other.md": "other\n"}, "main moves")
    repo.git("checkout", "-q", "feat")
    repo.git("merge", "-q", "--no-commit", "main")
    (repo.root / "src" / "app.py").write_text("x = 99\n", encoding="utf-8")
    repo.git("add", "-A")
    repo.git("commit", "-q", "--no-edit")
    merge = repo.head()
    asked: list[tuple] = []
    answer = [_altered("docs/other.md", "added")]
    rule = _ruled_rule(vf, ad, repo, answer, asked)
    assessed = rule.assess(_verdict(av, RULES, reviewed))
    assert not assessed.fresh
    assert assessed.reason.endswith("reaches its touches-ruled-artefact floor")
    # The page that cost the approval is named, though the author changed only code.
    assert (
        "changed since: src/app.py; ruled artefacts altered or brought under a rule: docs/other.md"
    ) in assessed.reason
    assert asked == [(reviewed, merge)]


def test_a_backbone_that_cannot_answer_stales_the_approval_with_its_reason(
    av, ad, vf, repo
) -> None:
    reviewed = repo.commit({"src/app.py": "x = 2\n"}, "code")
    repo.commit({GUIDE: "guide, rewritten\n"}, "page fix")
    asked: list[tuple] = []
    rule = _ruled_rule(vf, ad, repo, "this checkout is shallow", asked)
    assessed = rule.assess(_verdict(av, RULES, reviewed))
    assert not assessed.fresh
    assert "whether it alters a ruled artefact cannot be read: this checkout is shallow" in (
        assessed.reason
    )


def test_a_rejection_on_the_ruled_floor_goes_stale_on_any_change(av, ad, vf, repo) -> None:
    reviewed = repo.commit({GUIDE: "guide\n\nmore\n"}, "page")
    repo.commit({"src/app.py": "x = 2\n"}, "code")
    asked: list[tuple] = []
    rule = _ruled_rule(vf, ad, repo, [], asked)
    assert not rule.is_fresh(_verdict(av, RULES, reviewed, token=av.CHANGES_REQUESTED))
    assert asked == []


def test_an_unknown_floor_is_reached_by_any_change(av, ad, vf, repo) -> None:
    reviewed = repo.commit({"src/app.py": "x = 2\n"}, "code")
    repo.commit({".changes/unreleased/x.yaml": "kind: none\n"}, "changeset")
    asked: list[tuple] = []
    rule = _ruled_rule(vf, ad, repo, [], asked, floors={RULES: frozenset({"touches-secrets"})})
    assessed = rule.assess(_verdict(av, RULES, reviewed))
    assert not assessed.fresh and assessed.reason.endswith("reaches its touches-secrets floor")


def test_without_a_reader_any_change_stales_the_ruled_floor(av, ad, vf, repo) -> None:
    """A rule given no reader of what a commit altered cannot tell, so it stales
    the approval on any change."""
    reviewed = repo.commit({"src/app.py": "x = 2\n"}, "code")
    head = repo.commit({"src/app.py": "x = 3\n"}, "code fix")
    tip = repo.head("main")
    rule = vf.FreshnessRule(
        head_sha=head,
        base_tip=tip,
        floors_by_reviewer=RULED_FLOOR,
        delta_since=lambda since: ad.author_delta(since, head, base_tip=tip, cwd=repo.root),
    )
    assert not rule.is_fresh(_verdict(av, RULES, reviewed))


def test_an_artefact_ruled_at_either_end_of_its_stretch_stales_the_approval(
    av, ad, vf, repo
) -> None:
    """The author removes a ruled page after the review. No rule binds on it
    after that commit, since it is gone, but one does before it, so it
    counts."""
    reviewed = repo.commit({"src/app.py": "x = 2\n"}, "code")
    repo.git("rm", "-q", GUIDE)
    repo.git("commit", "-q", "-m", "remove the moved page")
    asked: list[tuple] = []
    answer = [_altered(GUIDE, "removed")]
    rule = _ruled_rule(vf, ad, repo, answer, asked)
    assessed = rule.assess(_verdict(av, RULES, reviewed))
    assert not assessed.fresh
    assert assessed.reason.endswith("reaches its touches-ruled-artefact floor")


def test_rules_count_only_where_the_stretch_starts_or_ends(av, ad, vf, repo) -> None:
    """The author edits a page after the review. No rule binds on it before or
    after that commit, so it counts not. A rule a later clean merge brings
    does not change that, since that merge is never asked about."""
    reviewed = repo.commit({"src/app.py": "x = 2\n"}, "code")
    repo.commit({GUIDE: "guide, rewritten\n"}, "page fix")
    asked: list[tuple] = []
    answer = [_altered(GUIDE, ruled=False)]
    rule = _ruled_rule(vf, ad, repo, answer, asked)
    assessed = rule.assess(_verdict(av, RULES, reviewed))
    assert assessed.fresh, assessed.reason
    assert len(asked) == 1


def test_the_ruled_artefacts_are_read_once_per_reviewed_head(av, ad, vf, repo) -> None:
    reviewed = repo.commit({"src/app.py": "x = 2\n"}, "code")
    repo.commit({GUIDE: "guide, rewritten\n"}, "page fix")
    asked: list[tuple] = []
    rule = _ruled_rule(vf, ad, repo, [], asked)
    for _ in range(3):
        assert rule.is_fresh(_verdict(av, RULES, reviewed))
    assert len(asked) == 1


def test_the_first_stretch_that_reaches_the_floor_settles_it(av, ad, vf, repo) -> None:
    """Two runs since the review, apart by a clean merge of the base, each
    alter a ruled page. The first settles the verdict, so the second is not
    asked about."""
    reviewed = repo.commit({"src/app.py": "x = 2\n"}, "code")
    first = repo.commit({GUIDE: "guide, once\n"}, "page fix")
    repo.git("checkout", "-q", "main")
    repo.commit({"docs/other.md": "other\n"}, "main moves")
    repo.git("checkout", "-q", "feat")
    repo.git("merge", "-q", "--no-edit", "main")
    repo.commit({GUIDE: "guide, twice\n"}, "page fix again")
    asked: list[tuple] = []
    rule = _ruled_rule(vf, ad, repo, [_altered(GUIDE)], asked)
    assert not rule.is_fresh(_verdict(av, RULES, reviewed))
    assert asked == [(reviewed, first)]
