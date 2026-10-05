"""link-parent — link existing issues natively from their first-line parent-ref (#1033).

Drives the real `main()` against a staged capability tree carrying the REAL
shipped issue-types and classification schemas. The live tracker is never
touched: every `gh` call the verb makes goes through the containment seam's
`_gh_call` (the corpus read, the native sub-issue reads, the link, the
children-view comment), and that one function is replaced by `FakeGitHub`, a
small in-memory tracker that also records every write.
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
from ruamel.yaml import YAML

REPO_ROOT = Path(__file__).resolve().parent.parent
CAPABILITY = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
SCRIPT_PATH = CAPABILITY / "scripts" / "link-parent.py"

# A fake issue's database id is its number plus this, so a test can tell the
# id the sub-issue endpoint takes from the number a human reads.
DB_OFFSET = 10_000

_STAMP = (
    "schema_version: 1\n"
    "bootstrap:\n"
    "  completed_at: '2026-01-01T00:00:00+00:00'\n"
    "  capability_version: 0.0.0-test\n"
    "  by: bootstrap\n"
    "  repo:\n"
)


@pytest.fixture(scope="module")
def lp():
    """Load link-parent.py as a module via importlib."""
    module_name = "pm_link_parent_under_test"
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _stage(tmp_path: Path, *, containment: str | None = None) -> Path:
    """A bootstrapped capability tree in open membership mode."""
    root = tmp_path / ".pkit" / "capabilities" / "project-management"
    (root / "schemas").mkdir(parents=True)
    (root / "project").mkdir(parents=True)
    for name in ("issue-types.yaml", "classification.yaml"):
        (root / "schemas" / name).write_text(
            (CAPABILITY / "schemas" / name).read_text(encoding="utf-8"), encoding="utf-8"
        )
    (root / "project" / "config.yaml").write_text(
        "schema_version: 1\ndefault_branch: main\nworkstreams: []\n", encoding="utf-8"
    )
    (root / "project" / "members.yaml").write_text("members: []\n", encoding="utf-8")
    (root / "project" / "bootstrap-stamp.yaml").write_text(_STAMP, encoding="utf-8")
    if containment is not None:
        (root / "project" / "substrate-map.yaml").write_text(
            f"schema_version: 1\naxes: {{}}\ncontainment: {containment}\n",
            encoding="utf-8",
        )
    return root


def _issue(number: int, title: str, body: str, state: str = "OPEN", labels=()) -> dict:
    labelled = [{"name": name} for name in labels]
    return {"number": number, "title": title, "body": body, "state": state, "labels": labelled}


def _tracker() -> list[dict]:
    """One issue per outcome, plus the parents they name."""
    return [
        _issue(80, "[EPIC] the thesis", "Milestone: [#5](../milestone/5)\n"),
        _issue(90, "[Feature] a capability", "EPIC: #80\n\n## What\n"),
        _issue(91, "[Umbrella] an old bucket", "EPIC: #80\n", state="CLOSED"),
        _issue(101, "[Task] link me", "Feature: #90\n\n## What\n"),
        _issue(102, "[Task] linked already", "Feature: #90\n"),
        _issue(103, "[Task] under the milestone", "Milestone: [#5](../milestone/5)\n"),
        _issue(104, "[Task] no ref", "## What\n\nthe work\n"),
        _issue(105, "[Task] names a ghost", "Feature: #999\n"),
        _issue(106, "[Task] open under a closed bucket", "Umbrella: #91\n"),
        _issue(107, "[Task] closed under a closed bucket", "Umbrella: #91\n", state="CLOSED"),
        _issue(108, "[Bug] a kind-prefixed task", "Feature: #90\n"),
    ]


EXPLICIT = ["101", "102", "103", "104", "105", "106", "107", "108"]


def _ok(args, stdout: str) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args, 0, stdout=stdout, stderr="")


def _fail(args, stderr: str) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args, 1, stdout="", stderr=stderr)


# How `gh api` reports GitHub refusing an add on the one-parent rule: the JSON
# error body on stdout, a summary line on stderr that does not carry the rule.
_API = "https://api.github.com"
_ONE_PARENT_BODY = json.dumps(
    {
        "message": "Validation Failed",
        "errors": [
            {
                "resource": "Issue",
                "code": "custom",
                "field": "sub_issue_id",
                "message": "Sub issue may only have one parent",
            }
        ],
        "documentation_url": "https://docs.github.com/rest/issues/sub-issues#add-sub-issue",
        "status": "422",
    }
)


class FakeGitHub:
    """An in-memory tracker answering the containment seam's `gh` calls.

    ``native`` maps a parent to its native sub-issue numbers. ``list_error``
    fails every sub-issue list read with that stderr; ``post_error`` fails every
    link POST with it; ``fail_posts`` fails the POST for those children only.
    Like GitHub, an add is refused on the one-parent rule when the child is
    already under another parent. ``records_parent=False`` stands in for an
    instance whose issue record does not carry ``parent_issue_url``; with
    ``unanchored=True`` the sub-issues list names each entry's repository and
    carries no ``parent_issue_url`` either. ``elsewhere`` maps a parent to the
    numbers of its native sub-issues in another repository, ``acme/other``.
    """

    def __init__(
        self,
        issues: list[dict],
        *,
        native: dict[int, set[int]] | None = None,
        list_error: str | None = None,
        post_error: str | None = None,
        fail_posts: tuple[int, ...] = (),
        records_parent: bool = True,
        unanchored: bool = False,
        elsewhere: dict[int, list[int]] | None = None,
    ) -> None:
        self.issues = issues
        self.native = {parent: set(children) for parent, children in (native or {}).items()}
        self.list_error = list_error
        self.post_error = post_error
        self.fail_posts = set(fail_posts)
        self.records_parent = records_parent
        self.unanchored = unanchored
        self.elsewhere = elsewhere or {}
        self.posts: list[tuple[int, int]] = []
        self.comments: dict[int, list[dict]] = {}
        self.calls: list[list[str]] = []

    @property
    def writes(self) -> list[list[str]]:
        return [c for c in self.calls if "POST" in c or "PATCH" in c]

    def list_reads(self, parent: int) -> int:
        """How many times this parent's sub-issue list was read."""
        path = f"repos/{{owner}}/{{repo}}/issues/{parent}/sub_issues"
        return sum(1 for c in self.calls if path in c and "POST" not in c)

    def native_parent(self, child: int) -> int | None:
        return next((p for p, children in self.native.items() if child in children), None)

    def __call__(self, args, config):
        args = [str(a) for a in args]
        self.calls.append(args)
        path = next((a for a in args if a.startswith("repos/")), "")
        if args[:3] == ["gh", "issue", "list"]:
            return _ok(args, json.dumps(self.issues))
        m = re.fullmatch(r"repos/\{owner\}/\{repo\}/issues/(\d+)/sub_issues", path)
        if m:
            parent = int(m.group(1))
            if "POST" in args:
                return self._link(args, parent)
            if self.list_error:
                return _fail(args, self.list_error)
            children = sorted(self.native.get(parent, set()))
            here = f"{_API}/repos/o/r"
            entries = [
                {
                    "id": DB_OFFSET + n,
                    "number": n,
                    **({"repository_url": here} if self.unanchored else {}),
                }
                for n in children
            ] + [
                {
                    "id": 90_000 + n,
                    "number": n,
                    "repository_url": f"{_API}/repos/acme/other",
                    "parent_issue_url": f"{here}/issues/{parent}",
                }
                for n in self.elsewhere.get(parent, [])
            ]
            return _ok(args, json.dumps(entries))
        m = re.fullmatch(r"repos/\{owner\}/\{repo\}/issues/(\d+)/comments", path)
        if m:
            parent = int(m.group(1))
            if "POST" in args:
                body = args[args.index("-f") + 1].split("=", 1)[1]
                self.comments.setdefault(parent, []).append({"id": 7000 + parent, "body": body})
                return _ok(args, "{}")
            return _ok(args, json.dumps(self.comments.get(parent, [])))
        m = re.fullmatch(r"repos/\{owner\}/\{repo\}/issues/(\d+)", path)
        if m:
            number = int(m.group(1))
            jq = args[args.index("--jq") + 1] if "--jq" in args else ""
            if jq == ".number":  # the failure probe
                return _ok(args, str(number))
            if jq == ".repository_url":  # this repository's name, from a parent's record
                return _ok(args, f"{_API}/repos/o/r\n")
            # The child-record read: database id, native parent URL, repository URL.
            parent = self.native_parent(number) if self.records_parent else None
            parent_url = f"{_API}/repos/o/r/issues/{parent}" if parent else ""
            return _ok(args, f"{DB_OFFSET + number}\n{parent_url}\n{_API}/repos/o/r\n")
        raise AssertionError(f"unexpected gh call: {args}")

    def _link(self, args: list[str], parent: int) -> subprocess.CompletedProcess:
        child = int(args[args.index("-F") + 1].split("=", 1)[1]) - DB_OFFSET
        if self.post_error:
            return _fail(args, self.post_error)
        if child in self.fail_posts:
            return _fail(args, "gh: HTTP 500: server error")
        holder = self.native_parent(child)
        if holder is not None and holder != parent:
            return subprocess.CompletedProcess(
                args, 1, stdout=_ONE_PARENT_BODY, stderr="gh: Validation Failed (HTTP 422)"
            )
        self.posts.append((parent, child))
        self.native.setdefault(parent, set()).add(child)
        return _ok(args, "{}")


class _Stdin:
    def __init__(self, tty: bool) -> None:
        self._tty = tty

    def isatty(self) -> bool:
        return self._tty


def _run(lp, monkeypatch, capsys, root, fake, *argv, tty=False, reply=None, guard=True):
    """Run main(); return (rc, captured, guard calls)."""
    monkeypatch.setattr(lp.containment, "_gh_call", fake)
    guard_calls: list[dict] = []

    def fake_guard(**kwargs):
        guard_calls.append(kwargs)
        return guard

    monkeypatch.setattr(lp.session_guard, "enforce", fake_guard)
    monkeypatch.setenv("PM_INVOKER_LOGIN", "tester")
    monkeypatch.setattr(lp.sys, "stdin", _Stdin(tty))
    if reply is not None:
        monkeypatch.setattr("builtins.input", lambda prompt="": reply)
    monkeypatch.setattr(lp.sys, "argv", ["link-parent.py", *argv, "--capability-root", str(root)])
    rc = lp.main()
    return rc, capsys.readouterr(), guard_calls


# --- the plan: one outcome per issue, and a dry run writes nothing -----------


def test_dry_run_reports_every_outcome_and_changes_nothing(lp, tmp_path, monkeypatch, capsys):
    fake = FakeGitHub(_tracker(), native={90: {102}})
    rc, out, guard_calls = _run(
        lp, monkeypatch, capsys, _stage(tmp_path), fake, *EXPLICIT, "--dry-run"
    )

    assert rc == 0
    lines = out.out
    assert "#101  would link under #90" in lines
    assert "#102  already linked under #90" in lines
    assert "#103  milestone parent (milestone #5) — no issue link" in lines
    assert "#104  no parent line" in lines
    assert "#105  parent #999 not found — not linked" in lines
    assert "#106  parent #91 is closed while #106 is open — not linked" in lines
    # A closed child under a closed parent is history, and links normally.
    assert "#107  would link under #91" in lines
    # A kind-prefixed title is still recognised as a Task.
    assert "#108  would link under #90" in lines
    assert (
        "plan: 3 would link, 1 already linked, 1 milestone parent, 1 no parent line, "
        "2 parent not found or closed"
    ) in lines
    assert "[dry-run] nothing written." in lines
    # Read-only: no write of any kind, and the foreign-repo guard (a write gate)
    # is not even consulted.
    assert fake.writes == []
    assert guard_calls == []


def test_yes_links_exactly_the_planned_issues(lp, tmp_path, monkeypatch, capsys):
    fake = FakeGitHub(_tracker(), native={90: {102}})
    rc, out, guard_calls = _run(lp, monkeypatch, capsys, _stage(tmp_path), fake, *EXPLICIT, "--yes")

    assert rc == 0
    assert fake.posts == [(90, 101), (91, 107), (90, 108)]
    assert "[ok] #101 linked under #90" in out.out
    assert (
        "done: 3 linked, 1 already linked, 1 milestone parent, 1 no parent line, "
        "2 parent not found or closed"
    ) in out.out
    assert guard_calls == [{"override": False}], "the foreign-repo guard gates the write"


def test_an_existing_link_is_never_posted_again(lp, tmp_path, monkeypatch, capsys):
    """Idempotent: #102 is already a native sub-issue, so it gets no POST; and a
    second run over the same issues finds everything linked and writes nothing."""
    fake = FakeGitHub(_tracker(), native={90: {102}})
    root = _stage(tmp_path)
    _run(lp, monkeypatch, capsys, root, fake, "101", "102", "--yes")
    assert fake.posts == [(90, 101)]

    rc, out, _ = _run(lp, monkeypatch, capsys, root, fake, "101", "102", "--yes")
    assert rc == 0
    assert fake.posts == [(90, 101)], "nothing re-posted"
    assert "#101  already linked under #90" in out.out
    assert "nothing to link." in out.out


def test_a_sub_issue_naming_this_repository_without_an_anchor_is_already_linked(
    lp, tmp_path, monkeypatch, capsys
):
    """A tracker whose sub-issues list names each entry's repository and omits
    `parent_issue_url` (and whose issue records omit it too): #102, listed under
    #90 as `o/r`, is this repository's #102, so it is already linked and never
    posted again (#1308). This repository's name is read once, from #90's record."""
    fake = FakeGitHub(_tracker(), native={90: {102}}, records_parent=False, unanchored=True)
    rc, out, _ = _run(lp, monkeypatch, capsys, _stage(tmp_path), fake, "102", "--yes")

    assert rc == 0, out.err
    assert "#102  already linked under #90" in out.out
    assert fake.posts == []
    name_reads = [c for c in fake.calls if c[-2:] == ["--jq", ".repository_url"]]
    assert name_reads == [
        ["gh", "api", "repos/{owner}/{repo}/issues/90", "--jq", ".repository_url"]
    ]


def test_a_sub_issue_elsewhere_does_not_make_this_repository_s_issue_linked(
    lp, tmp_path, monkeypatch, capsys
):
    """`acme/other#101` listed under #90 is not this repository's #101: #101 is
    planned and linked like any child #90 does not hold (#1308)."""
    fake = FakeGitHub(_tracker(), native={90: set()}, elsewhere={90: [101]})
    rc, out, _ = _run(lp, monkeypatch, capsys, _stage(tmp_path), fake, "101", "--yes")

    assert rc == 0, out.err
    assert "#101  already linked" not in out.out
    assert fake.posts == [(90, 101)]
    assert not [c for c in fake.writes if any("acme/other" in arg for arg in c)]


# A reference to an issue elsewhere GitHub would link: not inside a code span.
_LINKED_ELSEWHERE = re.compile(r"(?<!`)acme/other#[0-9]+")


def test_the_children_view_names_a_sub_issue_elsewhere_without_linking_it(
    lp, tmp_path, monkeypatch, capsys
):
    """In textual mode the refreshed children view lists `acme/other#555`, #90's
    sub-issue in another repository, in a code span: no write is addressed
    there, and none names it in a form GitHub links (#1308)."""
    fake = FakeGitHub(_tracker(), native={90: set()}, elsewhere={90: [555]})
    rc, out, _ = _run(
        lp, monkeypatch, capsys, _stage(tmp_path, containment="textual"), fake, "101", "--yes"
    )

    assert rc == 0, out.err
    view = fake.comments[90][0]["body"]
    assert "- `acme/other#555`\n" in view
    for write in fake.writes:
        assert not any("repos/acme/other" in arg for arg in write), write
        assert not any(_LINKED_ELSEWHERE.search(arg) for arg in write), write


def test_milestone_parent_no_parent_line_and_missing_parent_link_nothing(
    lp, tmp_path, monkeypatch, capsys
):
    fake = FakeGitHub(_tracker())
    rc, out, _ = _run(
        lp, monkeypatch, capsys, _stage(tmp_path), fake, "103", "104", "105", "106", "--yes"
    )
    assert rc == 0
    assert fake.writes == []
    assert "nothing to link." in out.out


def test_all_open_examines_every_open_issue_and_only_those(lp, tmp_path, monkeypatch, capsys):
    fake = FakeGitHub(_tracker(), native={90: {102}})
    rc, out, _ = _run(lp, monkeypatch, capsys, _stage(tmp_path), fake, "--all-open", "--yes")

    assert rc == 0
    # #90 is itself a Feature naming EPIC #80; the closed #91 and #107 are not
    # examined at all.
    assert fake.posts == [(80, 90), (90, 101), (90, 108)]
    assert "#107" not in out.out
    assert "link-parent: 9 issue(s)" in out.out


# --- consent -----------------------------------------------------------------


def test_non_interactive_run_without_yes_refuses_naming_the_rerun(
    lp, tmp_path, monkeypatch, capsys
):
    fake = FakeGitHub(_tracker())
    root = _stage(tmp_path)
    rc, out, _ = _run(lp, monkeypatch, capsys, root, fake, "108", "101", tty=False)

    assert rc == 2
    assert fake.writes == []
    assert f"pkit pm link-parent 101 108 --capability-root {root} --yes" in out.err


def test_interactive_prompt_declined_writes_nothing(lp, tmp_path, monkeypatch, capsys):
    fake = FakeGitHub(_tracker())
    rc, out, _ = _run(lp, monkeypatch, capsys, _stage(tmp_path), fake, "101", tty=True, reply="n")
    assert rc == 0
    assert fake.writes == []
    assert "aborted." in out.err


def test_interactive_prompt_accepted_links(lp, tmp_path, monkeypatch, capsys):
    fake = FakeGitHub(_tracker())
    rc, _out, _ = _run(lp, monkeypatch, capsys, _stage(tmp_path), fake, "101", tty=True, reply="y")
    assert rc == 0
    assert fake.posts == [(90, 101)]


def test_foreign_repo_refusal_writes_nothing(lp, tmp_path, monkeypatch, capsys):
    fake = FakeGitHub(_tracker())
    rc, _out, _ = _run(lp, monkeypatch, capsys, _stage(tmp_path), fake, "101", "--yes", guard=False)
    assert rc == 1
    assert fake.writes == []


# --- containment mode: textual links nothing, refreshes the children views ----


def test_textual_mode_links_nothing_and_refreshes_children_views(lp, tmp_path, monkeypatch, capsys):
    fake = FakeGitHub(_tracker(), native={90: {102}})
    rc, out, _ = _run(
        lp,
        monkeypatch,
        capsys,
        _stage(tmp_path, containment="textual"),
        fake,
        *EXPLICIT,
        "--yes",
    )

    assert rc == 0
    assert fake.posts == [], "textual mode must not make a native link"
    assert "#101  under #90 — textual mode links nothing" in out.out
    assert "children views to refresh: #90, #91" in out.out
    # One generated children comment per named parent, rendered from the corpus.
    assert sorted(fake.comments) == [90, 91]
    view = fake.comments[90][0]["body"]
    assert "pkit:children-view do-not-edit" in view
    assert "#101" in view and "#108" in view


def test_textual_mode_dry_run_writes_no_comment(lp, tmp_path, monkeypatch, capsys):
    fake = FakeGitHub(_tracker())
    rc, out, _ = _run(
        lp,
        monkeypatch,
        capsys,
        _stage(tmp_path, containment="textual"),
        fake,
        "101",
        "--dry-run",
    )
    assert rc == 0
    assert fake.writes == []
    assert "children views to refresh: #90" in out.out


def test_textual_mode_refuses_to_refresh_from_a_short_issue_list(lp, tmp_path, monkeypatch, capsys):
    """The children comment is the parent's only parent-side view and carries no
    hedge, so a partial list published there would read as the complete one."""
    fake = FakeGitHub(_tracker())
    monkeypatch.setattr(
        lp.containment,
        "fetch_issue_corpus",
        lambda config, **kw: lp.containment.IssueCorpus(rows=tuple(_tracker()), complete=False),
    )
    rc, out, _ = _run(
        lp,
        monkeypatch,
        capsys,
        _stage(tmp_path, containment="textual"),
        fake,
        "101",
        "--yes",
    )
    assert rc == 1
    assert "[refused]" in out.err
    assert fake.writes == []


def test_textual_mode_withholds_a_view_the_seam_cannot_vouch_for(lp, tmp_path, monkeypatch, capsys):
    """A whole issue list is not enough: when a parent's native sub-issues read
    fails, a native child may exist unseen, so that parent's view is not
    overwritten — and the reason given is the one the seam established."""
    fake = FakeGitHub(_tracker(), list_error="gh: HTTP 500: server error")
    rc, out, _ = _run(
        lp,
        monkeypatch,
        capsys,
        _stage(tmp_path, containment="textual"),
        fake,
        "101",
        "--yes",
    )
    assert rc == 3
    assert fake.writes == []
    assert "[refused] children view of #90 not refreshed" in out.out
    assert "native sub-issues read failed" in out.out


# --- instances and failures ---------------------------------------------------


def test_an_instance_without_sub_issues_links_nothing(lp, tmp_path, monkeypatch, capsys):
    fake = FakeGitHub(_tracker(), list_error="gh: HTTP 410: Gone")
    rc, out, _ = _run(lp, monkeypatch, capsys, _stage(tmp_path), fake, "101", "--yes")
    assert rc == 0
    assert fake.writes == []
    assert "native sub-issues are unsupported on this instance" in out.out


def test_a_422_reading_sub_issues_does_not_plan_the_instance_as_unsupported(
    lp, tmp_path, monkeypatch, capsys
):
    """#808, on the read side: a 422 on the parent's list says nothing about
    the instance, so the plan keeps the link (to be checked again at the add)
    instead of writing the whole parent off as "unsupported"."""
    fake = FakeGitHub(_tracker(), list_error="gh: HTTP 422: Unprocessable Entity")
    rc, out, _ = _run(lp, monkeypatch, capsys, _stage(tmp_path), fake, "101", "--yes")

    assert rc == 0
    assert fake.posts == [(90, 101)]
    assert "#90's sub-issues could not be read" in out.out
    assert "unsupported" not in out.out


def test_a_link_failure_exits_non_zero_and_the_others_still_link(lp, tmp_path, monkeypatch, capsys):
    fake = FakeGitHub(_tracker(), fail_posts=(101,))
    rc, out, _ = _run(lp, monkeypatch, capsys, _stage(tmp_path), fake, "101", "107", "108", "--yes")
    assert rc == 3
    assert fake.posts == [(91, 107), (90, 108)]
    assert "[fail] #101 not linked under #90" in out.out
    assert "1 failed" in out.out
    # A server error is not GitHub refusing the link: no textual-mode way out.
    assert "containment: textual" not in out.out


def test_a_refusal_where_sub_issues_demonstrably_work_is_a_failure(
    lp, tmp_path, monkeypatch, capsys
):
    """The seam reads a 410 on the add as "unsupported" — a no-op on an instance
    without sub-issues. Here the same parent's sub-issues were just read, so the
    instance has them: the refusal is this link's, reported as a failure, and
    without asserting a cause nobody established."""
    fake = FakeGitHub(_tracker(), post_error="gh: HTTP 410: Gone")
    rc, out, _ = _run(lp, monkeypatch, capsys, _stage(tmp_path), fake, "101", "--yes")
    assert rc == 3
    assert fake.posts == []
    assert "GitHub refused the link as unsupported, although #90's sub-issues read" in out.out


def test_an_unrecognised_422_on_the_add_fails_with_githubs_message(
    lp, tmp_path, monkeypatch, capsys
):
    """#808: a 422 is a failure for this link, carrying what was said — not
    "unsupported", and not a quiet no-op. The run still exits 3 so the operator
    sees it. With no error body the words are gh's own line, and are attributed
    to gh rather than passed off as GitHub's."""
    fake = FakeGitHub(_tracker(), post_error="gh: Parent issue is locked (HTTP 422)")
    rc, out, _ = _run(lp, monkeypatch, capsys, _stage(tmp_path), fake, "101", "--yes")

    assert rc == 3
    assert fake.posts == []
    assert "[fail] #101 not linked under #90" in out.out
    assert 'gh said: "gh: Parent issue is locked (HTTP 422)"' in out.out
    assert "GitHub said" not in out.out
    assert "textual ref recorded" not in out.out, "link-parent recorded no textual ref"
    assert "unsupported" not in out.out


def test_a_run_github_refused_ends_with_the_textual_way_out_once(lp, tmp_path, monkeypatch, capsys):
    """pm never reads a refusal as an instance without sub-issues (ADR-035), so
    an operator whose GitHub has none needs the way out: it follows the run's
    links once, however many GitHub refused."""
    fake = FakeGitHub(_tracker(), post_error="gh: Validation Failed (HTTP 422)")
    rc, out, _ = _run(lp, monkeypatch, capsys, _stage(tmp_path), fake, "101", "107", "--yes")

    assert rc == 3
    assert out.out.count("[fail]") == 2
    way_out = (
        "  → If this GitHub does not offer sub-issues, set `containment: textual` in "
        "project/substrate-map.yaml and pm stops attempting the native link."
    )
    assert out.out.count(way_out) == 1


# --- one native parent (#1040) ----------------------------------------------


def _tracker_with_second_feature() -> list[dict]:
    return [*_tracker(), _issue(95, "[Feature] another capability", "EPIC: #80\n")]


def test_dry_run_reports_a_child_under_another_native_parent_as_a_conflict(
    lp, tmp_path, monkeypatch, capsys
):
    """#101's first line names #90, but it is natively a sub-issue of #95. The
    plan says so by name — child, the parent it has, the parent the line names —
    before anything is posted, and does not call it unsupported."""
    fake = FakeGitHub(_tracker_with_second_feature(), native={95: {101}})
    rc, out, _ = _run(lp, monkeypatch, capsys, _stage(tmp_path), fake, "101", "108", "--dry-run")

    assert rc == 0
    assert (
        "#101  conflict — natively a sub-issue of #95, but the first line names "
        "#90; not linked (an issue has one native parent)"
    ) in out.out
    assert "#108  would link under #90" in out.out
    # The native parent wins (DEC-005), in the containment seam's words.
    assert (
        "    → the native parent wins (DEC-005): `set-field 101 --parent 95` rewrites #101's "
        "first line to name it.\n"
    ) in out.out
    assert "your call" not in out.out
    assert "plan: 1 would link, 1 conflict (another native parent)" in out.out
    assert "unsupported" not in out.out
    assert fake.writes == []


def test_a_conflict_is_reported_not_linked_and_the_others_still_link(
    lp, tmp_path, monkeypatch, capsys
):
    fake = FakeGitHub(_tracker_with_second_feature(), native={95: {101}})
    rc, out, _ = _run(lp, monkeypatch, capsys, _stage(tmp_path), fake, "101", "108", "--yes")

    assert rc == 0, "a conflict is reported for the operator, not a gh failure"
    assert fake.posts == [(90, 108)]
    assert fake.native[95] == {101}, "the child keeps the parent it has"
    assert "done: 1 linked, 1 conflict (another native parent)" in out.out


def test_the_one_parent_422_is_read_from_its_body_not_taken_as_unsupported(
    lp, tmp_path, monkeypatch, capsys
):
    """An instance whose issue record does not carry the parent: the plan sees
    no conflict, GitHub refuses the add with a 422, and the rule its error body
    states is what the report says — a conflict, not "unsupported" and not a
    failure — even though the parent cannot be named."""
    fake = FakeGitHub(_tracker_with_second_feature(), native={95: {101}}, records_parent=False)
    rc, out, _ = _run(lp, monkeypatch, capsys, _stage(tmp_path), fake, "101", "--yes")

    assert rc == 0
    assert fake.posts == []
    assert (
        "[warn] #101 conflict — natively a sub-issue of another parent, but the "
        "first line names #90"
    ) in out.out
    # GitHub's own words follow pm's line (#808).
    assert 'GitHub said: "Validation Failed; Sub issue may only have one parent"' in out.out
    assert "unsupported" not in out.out
    assert "containment: textual" not in out.out, "a conflict is not a refusal to work around"


# --- one read per parent -------------------------------------------------------


def test_all_open_reads_each_parents_sub_issues_once_over_64_links(
    lp, tmp_path, monkeypatch, capsys
):
    """#1040: link-parent read a parent's sub-issue list once per child. Over 64
    links under four Features (and the Features under their EPIC) each parent's
    list is read exactly once — the plan's read, reused by every link."""
    features = [90, 91, 92, 93]
    tracker = [_issue(80, "[EPIC] the thesis", "Milestone: [#5](../milestone/5)\n")]
    tracker += [_issue(f, f"[Feature] f{f}", "EPIC: #80\n") for f in features]
    tracker += [
        _issue(200 + i, f"[Task] t{i}", f"Feature: #{features[i % 4]}\n") for i in range(64)
    ]
    fake = FakeGitHub(tracker)
    rc, _out, _ = _run(lp, monkeypatch, capsys, _stage(tmp_path), fake, "--all-open", "--yes")

    assert rc == 0
    assert len(fake.posts) == 64 + len(features)
    for parent in [80, *features]:
        assert fake.list_reads(parent) == 1, f"#{parent}'s sub-issues read more than once"


def test_an_issue_number_that_is_not_an_issue_refuses_the_whole_run(
    lp, tmp_path, monkeypatch, capsys
):
    fake = FakeGitHub(_tracker())
    rc, out, _ = _run(lp, monkeypatch, capsys, _stage(tmp_path), fake, "101", "9999", "--yes")
    assert rc == 2
    assert fake.writes == []
    assert "#9999" in out.err


def test_the_issue_list_unreadable_is_a_gh_failure(lp, tmp_path, monkeypatch, capsys):
    def broken(args, config):
        return _fail(list(args), "gh: could not connect")

    rc, out, _ = _run(lp, monkeypatch, capsys, _stage(tmp_path), broken, "101", "--dry-run")
    assert rc == 3
    assert "could not be read" in out.err


@pytest.mark.parametrize("argv", [[], ["101", "--all-open"]])
def test_selection_is_numbers_or_all_open(lp, tmp_path, monkeypatch, capsys, argv):
    with pytest.raises(SystemExit) as exc:
        _run(lp, monkeypatch, capsys, _stage(tmp_path), FakeGitHub([]), *argv)
    assert exc.value.code == 2


# --- the classification itself (pure: no gh) -----------------------------------


@pytest.fixture(scope="module")
def schemas() -> tuple[dict, dict]:
    load = YAML(typ="safe").load
    return (
        load((CAPABILITY / "schemas" / "issue-types.yaml").read_text(encoding="utf-8")),
        load((CAPABILITY / "schemas" / "classification.yaml").read_text(encoding="utf-8")),
    )


def _classify(lp, schemas, rows, number, *, complete=True, substrate_map=None):
    issue_types, classification = schemas
    by_number = {row["number"]: row for row in rows}
    return lp.classify(
        number,
        by_number,
        issue_types,
        classification,
        corpus_complete=complete,
        substrate_map=substrate_map,
    )


def test_an_unrecognised_title_has_no_parent_line(lp, schemas):
    entry = _classify(
        lp,
        schemas,
        [_issue(1, "no prefix at all", "Feature: #2\n"), _issue(2, "[Feature] f", "EPIC: #3\n")],
        1,
    )
    assert entry.outcome is lp.Outcome.NO_PARENT_LINE
    assert "type prefix is not recognised" in entry.detail


def test_a_parent_the_type_may_not_have_is_named_non_conforming_and_not_linked(lp, schemas):
    """An EPIC's only parent form is a milestone: `Feature: #2` on its first line
    names #2 for every reader, in a form an EPIC may not have, and must not become
    an EPIC-under-Feature link. It is reported as the seam reads it — naming its
    parent, non-conforming — not as no parent line (#1281)."""
    entry = _classify(
        lp, schemas, [_issue(1, "[EPIC] e", "Feature: #2\n"), _issue(2, "[Feature] f", "")], 1
    )
    assert entry.outcome is lp.Outcome.NON_CONFORMING
    assert entry.detail == (
        "names #2 as its parent, non-conforming — 'Feature: #2' is not a parent-ref form for "
        "type 'epic'; not linked"
    )
    assert entry.parent is None, "nothing is planned to link"


@pytest.mark.parametrize("line", ["Epic: #2", "Feature: #2 — auth", "Feature:#2"])
def test_a_task_line_in_a_form_it_may_not_have_names_its_parent_non_conforming(
    lp, schemas, line: str
) -> None:
    rows = [_issue(1, "[Task] t", f"{line}\n"), _issue(2, "[Feature] f", "")]
    entry = _classify(lp, schemas, rows, 1)
    assert entry.outcome is lp.Outcome.NON_CONFORMING
    assert entry.detail.startswith("names #2 as its parent, non-conforming — ")
    assert "no parent line" not in entry.detail


def test_an_empty_body_and_a_self_reference_have_no_parent_line(lp, schemas):
    rows = [_issue(1, "[Task] t", ""), _issue(2, "[Task] t", "Feature: #2\n")]
    assert "the body is empty" in _classify(lp, schemas, rows, 1).detail
    assert "names #2 itself" in _classify(lp, schemas, rows, 2).detail


def test_a_missing_parent_on_a_short_list_says_the_list_was_short(lp, schemas):
    entry = _classify(lp, schemas, [_issue(1, "[Task] t", "Feature: #2\n")], 1, complete=False)
    assert entry.outcome is lp.Outcome.PARENT_UNAVAILABLE
    assert "not read in full" in entry.detail


# --- a parent the type may not sit under is reported, never linked (#1313) ------
# A first line in an allowed form may still name a parent of a type the issue's
# type may not sit under — `Feature: #2` where #2 is a Task. The link would make
# that containment, so link-parent refuses it as create-issue and set-field do.


def _shipped_types() -> dict:
    return YAML(typ="safe").load((CAPABILITY / "schemas" / "issue-types.yaml").read_text())["types"]


_TYPES = _shipped_types()


def _title(structural_type: str) -> str:
    entry = _TYPES[structural_type]
    prefix = entry["title_prefix"]
    return f"[{prefix.upper() if entry.get('title_case') == 'upper' else prefix}] x"


def _first_form_label(child: str) -> str:
    """The label of the first issue-parent option of `child`'s form."""
    return str(_TYPES[child]["parent_ref_form"]).split(":", 1)[0].strip()


# Every type a first line can link from (an EPIC's form names a milestone only),
# against every type the parent can be, from the shipped schema.
_LINKABLE = [
    c for c in sorted(_TYPES) if any(p != "milestone" for p in _TYPES[c]["parent_issue_types"])
]
_PAIRS = [(c, p) for c in _LINKABLE for p in sorted(_TYPES)]


@pytest.mark.parametrize(("child", "parent"), _PAIRS)
def test_a_parent_is_linked_exactly_where_the_schema_lets_the_type_sit_under_it(
    lp, schemas, child: str, parent: str
) -> None:
    rows = [
        _issue(1, _title(child), f"{_first_form_label(child)}: #2\n"),
        _issue(2, _title(parent), ""),
    ]
    entry = _classify(lp, schemas, rows, 1)

    if parent in _TYPES[child]["parent_issue_types"]:
        assert entry.outcome is lp.Outcome.WOULD_LINK
    else:
        assert entry.outcome is lp.Outcome.PARENT_TYPE_REFUSED
        article = "an" if child[0] in "aeiou" else "a"
        parent_article = "an" if parent[0] in "aeiou" else "a"
        assert entry.detail.startswith(
            f"not linked — {article} {child} may not sit under #2, which is "
            f"{parent_article} {parent}: "
        )
        assert f"`{_TYPES[child]['parent_ref_form']}`" in entry.detail


def test_a_parent_whose_type_cannot_be_told_is_linked(lp, schemas):
    """An untyped parent is outside the containment graph, so a legacy tree links."""
    rows = [_issue(1, "[Task] t", "Feature: #2\n"), _issue(2, "an untyped issue", "")]
    assert _classify(lp, schemas, rows, 1).outcome is lp.Outcome.WOULD_LINK


def test_a_task_under_a_kind_prefixed_task_is_refused_and_nothing_is_posted(
    lp, tmp_path, monkeypatch, capsys
):
    """`[Bug] …` is a Task: a Task whose first line names it is reported, not
    linked, and the others in the run still link."""
    issues = [
        *_tracker(),
        _issue(200, "[Bug] a kind-prefixed task", "Feature: #90\n"),
        _issue(201, "[Task] under a task", "Feature: #200\n"),
    ]
    fake = FakeGitHub(issues)
    rc, out, _guard = _run(lp, monkeypatch, capsys, _stage(tmp_path), fake, "101", "201", "--yes")

    assert rc == 0
    assert fake.posts == [(90, 101)]
    assert "#201  not linked — a task may not sit under #200, which is a task" in out.out
    assert "done: 1 linked, 1 parent's type not allowed" in out.out


def test_an_untitled_kind_labelled_parent_is_a_task_from_the_list_read(lp, schemas):
    """The issue list carries labels: a parent with no type prefix and a `type:bug`
    label is a Task in greenfield, so a Task under it is refused."""
    rows = [
        _issue(1, "[Task] t", "Feature: #2\n"),
        _issue(2, "Login crashes", "", labels=("type:bug",)),
    ]
    assert _classify(lp, schemas, rows, 1).outcome is lp.Outcome.PARENT_TYPE_REFUSED


_STORY = {"type": {"title-prefix": {"remap": {"feature": "[Story]", "task": "[Task]"}}}}
_TYPE_BY_LABEL = {"type": {"label": {"remap": {"bug": "kind/bug"}}}}


@pytest.mark.parametrize(
    ("axes", "parent", "outcome"),
    [
        (_STORY, _issue(2, "[Task] a task", ""), "PARENT_TYPE_REFUSED"),
        (_STORY, _issue(2, "[Story] a story", ""), "WOULD_LINK"),
        (_TYPE_BY_LABEL, _issue(2, "[Bug] Login crashes", ""), "WOULD_LINK"),
        (_TYPE_BY_LABEL, _issue(2, "Login crashes", "", labels=("type:bug",)), "WOULD_LINK"),
    ],
    ids=["story-map-task", "story-map-story", "label-map-kind-prefix", "label-map-kind-label"],
)
def test_under_a_map_both_types_are_told_by_its_title_prefixes(lp, schemas, axes, parent, outcome):
    """Under a map a type is told only by the map's title-prefix binding: a Task
    under a `[Task]` is refused, under a `[Story]` (a Feature) linked; where the
    map does not carry `type` in titles no type is told, and the pair links."""
    rows = [_issue(1, "[Task] t", "Feature: #2\n"), parent]
    entry = _classify(lp, schemas, rows, 1, substrate_map=lp.axis_labels.SubstrateMap(axes=axes))
    assert entry.outcome is getattr(lp.Outcome, outcome)


def test_the_issue_list_is_read_with_labels(lp, tmp_path, monkeypatch, capsys):
    fake = FakeGitHub(_tracker())
    seen: list[str] = []
    real = lp.containment.fetch_issue_corpus

    def spy(config, **kwargs):
        seen.append(kwargs.get("fields", ""))
        return real(config, **kwargs)

    monkeypatch.setattr(lp.containment, "fetch_issue_corpus", spy)
    _run(lp, monkeypatch, capsys, _stage(tmp_path), fake, "101", "--dry-run")
    assert seen and "labels" in seen[0].split(",")
