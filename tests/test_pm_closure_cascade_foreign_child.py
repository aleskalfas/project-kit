"""A native child in another repository is identified; a held container says what holds it.

Issue #1308.

GitHub's native sub-issues may live in another repository. The containment
seam's native read kept only each sub-issue's number, so a child elsewhere was
taken for this repository's issue of the same number, and the close gate folded
that issue's state. The read now places each sub-issue in its repository, and a
child in another repository holds its container like any other child: the fold
names it `owner/repo#<n>` and reads its state there — one read, by the tracker's
own open/closed alone — closed is done, open holds, and one that cannot be read
leaves the fold indeterminate. Nothing is written in another repository.

`close-issue --mode=cascade-eligibility-close` on a held container now says what
holds it: an open child, named (with its repository, for one elsewhere) with
what releases the container; or a read that failed, with the re-run advice — and
only then.

Pinned through the real engine and the shipped predicate scripts against a fake
`gh` on PATH, which logs every call it is given (the pattern of
`tests/test_pm_closure_cascade_native_child.py`), and `close-issue` run as a
script with the real `pkit` on PATH.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CAP_SRC = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
CAP_SCRIPTS = CAP_SRC / "scripts"
if str(CAP_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(CAP_SCRIPTS))

from _lib import containment  # noqa: E402
from _lib import lifecycle_predicates as predicates  # noqa: E402

from project_kit.process import CascadeResolution, ProcessEngine, load_definition  # noqa: E402

ADDRESS = "project-management:issue-lifecycle"
CONTAINER = 5
ELSEWHERE = "acme/other"
FOREIGN = f"{ELSEWHERE}#42"
HERE_API = "https://api.github.com/repos/acme/widget"

_VALID_CONFIG = "schema_version: 1\ndefault_branch: main\nworkstreams: []\n"

# A fake `gh` answering from `_tracker.json`: `issues` maps each of this
# repository's issues to its record, `foreign` maps `owner/repo#<n>` to an issue
# in another repository, `native` maps a parent to its native sub-issues (a
# number here, or `owner/repo#<n>`), `unreadable` lists what cannot be read, and
# `unviewable` the issues only `gh issue view` cannot read (their REST record
# and the issue list still can). Every call is appended to `_calls.jsonl`; a call
# it does not expect fails.
_FAKE_GH = """\
import json, pathlib, sys
root = pathlib.Path(ROOT)
tracker = json.loads((root / "_tracker.json").read_text())
issues, foreign, unreadable = tracker["issues"], tracker["foreign"], tracker["unreadable"]
args = sys.argv[1:]
with (root / "_calls.jsonl").open("a") as log:
    log.write(json.dumps(args) + "\\n")
HERE = "https://api.github.com/repos/acme/widget"

def fail(message):
    sys.stderr.write(message + "\\n")
    sys.exit(1)

def pick(record, fields):
    return {field: record.get(field) for field in fields}

def native_parent(ref):
    for parent, children in tracker["native"].items():
        if ref in children:
            return parent
    return None

def rest(repo, number, record, ref):
    out = dict(record, number=int(number), state=record["state"].lower())
    out["repository_url"] = "https://api.github.com/repos/" + repo
    parent = native_parent(ref)
    if parent is not None:
        out["parent_issue_url"] = HERE + "/issues/" + parent
    return out

path = args[-1] if args[:1] == ["api"] else ""
if args[:2] == ["issue", "view"]:
    number = args[2]
    if number in unreadable or number in tracker["unviewable"] or number not in issues:
        fail("GraphQL: Could not resolve to an issue with the number of " + number + ".")
    fields = args[args.index("--json") + 1].split(",")
    print(json.dumps(pick(dict(issues[number], number=int(number)), fields)))
elif args[:2] == ["issue", "list"]:
    fields = args[args.index("--json") + 1].split(",")
    print(json.dumps([pick(dict(r, number=int(n)), fields) for n, r in issues.items()]))
elif args[:1] == ["issue"] and args[1] in ("comment", "close", "edit"):
    if args[2] not in issues:
        fail("no such issue: " + args[2])
    if args[1] == "close":
        issues[args[2]]["state"] = "CLOSED"
        (root / "_tracker.json").write_text(json.dumps(tracker))
elif path.endswith("/sub_issues"):
    parent = path.split("/")[-2]
    entries = []
    for ref in tracker["native"].get(parent, []):
        repo, _, number = ref.rpartition("#") if "#" in ref else ("acme/widget", "", ref)
        entries.append({
            "id": 90000 + int(number),
            "number": int(number),
            "repository_url": "https://api.github.com/repos/" + repo,
            "parent_issue_url": HERE + "/issues/" + parent,
        })
    print(json.dumps(entries))
elif path.startswith("repos/{owner}/{repo}/issues/"):
    number = path.rsplit("/", 1)[-1]
    if number in unreadable or number not in issues:
        fail("gh: Not Found (HTTP 404)")
    print(json.dumps(rest("acme/widget", number, issues[number], number)))
elif path.startswith("repos/") and path.count("/") == 4:
    _, owner, repo, _, number = path.split("/")
    ref = owner + "/" + repo + "#" + number
    if ref in unreadable or ref not in foreign:
        fail("gh: Not Found (HTTP 404)")
    print(json.dumps(rest(owner + "/" + repo, number, foreign[ref], ref)))
else:
    fail("unexpected gh call: " + " ".join(args))
"""


def _executable(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A bootstrapped adopter project with the shipped capability, its scripts
    run by this interpreter, and a fake `gh` first on PATH."""
    root = tmp_path / "repo"
    root.mkdir()
    for args in (["init", "-q"], ["remote", "add", "origin", "git@github.com:acme/widget.git"]):
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)
    cap = root / ".pkit" / "capabilities" / "project-management"
    shutil.copytree(CAP_SRC / "schemas", cap / "schemas")
    shutil.copytree(CAP_SCRIPTS, cap / "scripts")
    shutil.copy(CAP_SRC / "package.yaml", cap / "package.yaml")
    (cap / "project").mkdir()
    (cap / "project" / "config.yaml").write_text(_VALID_CONFIG, encoding="utf-8")
    (cap / "project" / "bootstrap-stamp.yaml").write_text(
        "schema_version: 1\nbootstrap:\n  completed_at: '2026-01-01T00:00:00+00:00'\n"
        "  capability_version: 0.53.0\n  by: bootstrap\n  repo: github.com/acme/widget\n",
        encoding="utf-8",
    )
    for script in (cap / "scripts").glob("*.py"):
        body = script.read_text(encoding="utf-8").split("\n", 1)[1]
        script.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
    defs = root / ".pkit" / "schemas" / "_defs"
    defs.mkdir(parents=True)
    shutil.copy(REPO_ROOT / ".pkit" / "schemas" / "_defs" / "process.schema.json", defs)

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _executable(bin_dir / "gh", f"#!{sys.executable}\nROOT = {str(root)!r}\n" + _FAKE_GH)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))
    monkeypatch.setenv("PM_INVOKER_LOGIN", "operator")
    return root


def _issue(state: str, body: str = "## What\n", labels: list[str] | None = None) -> dict[str, Any]:
    return {
        "title": "[Task] A task",
        "state": state,
        "body": body,
        "labels": [{"name": n} for n in (labels or ["type:task", "state:in-progress"])],
        "milestone": None,
    }


def _container() -> dict[str, Any]:
    return dict(
        _issue(
            "OPEN", "EPIC: #1\n\n## What\n\n- [x] done\n", ["type:feature", "state:in-progress"]
        ),
        title="[Feature] A feature",
    )


def _epic() -> dict[str, Any]:
    return dict(_issue("OPEN", "## What\n", ["type:epic", "state:in-progress"]), title="[EPIC] E")


def _tracker(
    root: Path,
    issues: dict[int, dict[str, Any]],
    *,
    native: dict[int, list[int | str]] | None = None,
    foreign: dict[str, dict[str, Any]] | None = None,
    unreadable: tuple[int | str, ...] = (),
    unviewable: tuple[int, ...] = (),
) -> None:
    tracker = {
        "issues": {str(n): record for n, record in {1: _epic(), **issues}.items()},
        "native": {str(p): [str(c) for c in cs] for p, cs in (native or {}).items()},
        "foreign": foreign or {},
        "unreadable": [str(u) for u in unreadable],
        "unviewable": [str(u) for u in unviewable],
    }
    (root / "_tracker.json").write_text(json.dumps(tracker), encoding="utf-8")
    (root / "_calls.jsonl").write_text("", encoding="utf-8")


def _calls(root: Path) -> list[list[str]]:
    lines = (root / "_calls.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line]


def _fold(root: Path) -> CascadeResolution:
    engine = ProcessEngine.for_subject(load_definition(root, ADDRESS), root, str(CONTAINER))
    resolution = engine.resolve_cascade_outcome()
    assert resolution is not None, "the issue lifecycle declares the closure fold"
    return resolution


def _reads_of_local(root: Path, number: int) -> list[list[str]]:
    """Every read of this repository's issue `number`, through either read."""
    return [
        call
        for call in _calls(root)
        if call[:3] == ["issue", "view", str(number)]
        or (call[:1] == ["api"] and call[-1] == f"repos/{{owner}}/{{repo}}/issues/{number}")
    ]


def _naming_elsewhere(root: Path) -> list[list[str]]:
    return [call for call in _calls(root) if any(ELSEWHERE in arg for arg in call)]


# --- the seam: each native sub-issue in its repository -------------------------


def _answer(payload: object):
    return lambda args, _config: subprocess.CompletedProcess(args, 0, json.dumps(payload), "")


def test_the_native_read_places_each_sub_issue_in_its_repository(monkeypatch) -> None:
    here_child = {
        "number": 10,
        "repository_url": HERE_API,
        "parent_issue_url": f"{HERE_API}/issues/5",
    }
    elsewhere = {
        "number": 42,
        "repository_url": f"https://api.github.com/repos/{ELSEWHERE}",
        "parent_issue_url": f"{HERE_API}/issues/5",
    }
    # Without a parent_issue_url of their own, placed by the name the others'
    # anchor gives this repository.
    unanchored_elsewhere = {
        "number": 43,
        "repository_url": f"https://api.github.com/repos/{ELSEWHERE}",
    }
    unanchored_here = {"number": 12, "repository_url": HERE_API}
    number_only = {"number": 11}
    payload = [here_child, elsewhere, unanchored_elsewhere, unanchored_here, number_only]
    monkeypatch.setattr(containment, "_gh_call", _answer(payload))

    read = containment.read_native_children({}, parent_number=5)

    assert read.outcome is containment.NativeReadOutcome.READ
    assert read.numbers == {10, 11, 12}
    assert read.foreign == {
        containment.ForeignIssue(ELSEWHERE, 42),
        containment.ForeignIssue(ELSEWHERE, 43),
    }


def test_a_child_elsewhere_keeps_the_id_its_link_is_removed_by(monkeypatch) -> None:
    listed = {
        "id": 4242,
        "number": 42,
        "repository_url": f"https://api.github.com/repos/{ELSEWHERE}",
        "parent_issue_url": f"{HERE_API}/issues/5",
    }
    monkeypatch.setattr(containment, "_gh_call", _answer([listed]))

    resolution = containment.resolve_children({}, parent_number=5, corpus={}, corpus_complete=True)

    (child,) = resolution.foreign
    assert child.database_id == 4242
    # The removal runs on the parent, in this repository, never in the other one.
    assert containment.remove_sub_issue_args(parent_number=5, child_database_id=4242) == [
        "gh",
        "api",
        "-X",
        "DELETE",
        "repos/{owner}/{repo}/issues/5/sub_issue",
        "-F",
        "sub_issue_id=4242",
    ]
    assert containment.remove_sub_issue_command(parent_number=5, child_database_id=None) == (
        "gh api -X DELETE repos/{owner}/{repo}/issues/5/sub_issue -F sub_issue_id=<id>"
    )


def _unanchored_tracker(sub_issues: list[dict], *, here: str | None = HERE_API):
    """A `_gh_call` for a tracker whose sub-issue entries may omit
    `parent_issue_url`: it answers the list with `sub_issues`, a parent's record
    with `here` as its `repository_url` (`None`: the record cannot be read), and
    a child's link state as having no native parent. Every call is logged."""
    calls: list[list[str]] = []

    def gh(args, _config):
        calls.append(list(args))
        if args[-1].endswith("/sub_issues"):
            return subprocess.CompletedProcess(args, 0, json.dumps(sub_issues), "")
        if args[-2:] == ["--jq", ".repository_url"]:
            if here is None:
                return subprocess.CompletedProcess(args, 1, "", "gh: Not Found (HTTP 404)")
            return subprocess.CompletedProcess(args, 0, f"{here}\n", "")
        if args[-1] == containment._LINK_STATE_JQ:
            number = int(args[-3].rsplit("/", 1)[-1])
            return subprocess.CompletedProcess(args, 0, f"{1000 + number}\n\n{HERE_API}\n", "")
        if "POST" in args:
            return subprocess.CompletedProcess(args, 0, "{}", "")
        raise AssertionError(f"unexpected gh call: {args}")

    return gh, calls


_LIST_CALL = ["gh", "api", "--paginate", "repos/{owner}/{repo}/issues/5/sub_issues"]
_NAME_CALL = ["gh", "api", "repos/{owner}/{repo}/issues/5", "--jq", ".repository_url"]


def test_an_unanchored_entry_naming_this_repository_is_this_repository_s(monkeypatch) -> None:
    # The entry names this repository (in another case) and carries no
    # parent_issue_url: it is this repository's #10, whatever else it lacks.
    entry = {"number": 10, "repository_url": "https://api.github.com/repos/Acme/Widget"}
    gh, calls = _unanchored_tracker([entry])
    monkeypatch.setattr(containment, "_gh_call", gh)

    read = containment.read_native_children({}, parent_number=5)
    resolution = containment.resolve_children(
        {}, parent_number=5, corpus={10: "Feature: #5\n"}, corpus_complete=True
    )
    linked = containment.link_sub_issue({}, parent_number=5, child_number=10)

    assert (read.numbers, read.foreign) == ({10}, frozenset())
    # Deduped with the first line naming #5: one child, native.
    assert [(c.ref, c.substrate.value) for c in resolution.children] == [("#10", "native")]
    # The linked check finds it, so nothing is posted.
    assert linked.outcome is containment.LinkOutcome.ALREADY
    assert not [call for call in calls if "POST" in call]
    # This repository's name was read from #5's record, once per list read.
    assert calls[:2] == [_LIST_CALL, _NAME_CALL]


def test_an_unanchored_entry_naming_another_repository_is_foreign(monkeypatch) -> None:
    entry = {"number": 42, "repository_url": f"https://api.github.com/repos/{ELSEWHERE}"}
    gh, _calls = _unanchored_tracker([entry])
    monkeypatch.setattr(containment, "_gh_call", gh)

    read = containment.read_native_children({}, parent_number=5)

    assert (read.numbers, read.foreign) == (set(), {containment.ForeignIssue(ELSEWHERE, 42)})


def test_one_anchored_entry_places_them_all_at_no_cost(monkeypatch) -> None:
    entries = [
        {"number": 10, "repository_url": HERE_API},
        {"number": 11, "repository_url": HERE_API, "parent_issue_url": f"{HERE_API}/issues/5"},
        {"number": 42, "repository_url": f"https://api.github.com/repos/{ELSEWHERE}"},
        {"number": 12},
    ]
    gh, calls = _unanchored_tracker(entries)
    monkeypatch.setattr(containment, "_gh_call", gh)

    read = containment.read_native_children({}, parent_number=5)

    assert read.numbers == {10, 11, 12}
    assert read.foreign == {containment.ForeignIssue(ELSEWHERE, 42)}
    assert calls == [_LIST_CALL]


def test_number_only_entries_cost_no_name_read(monkeypatch) -> None:
    gh, calls = _unanchored_tracker([{"number": 10}, {"number": 11}])
    monkeypatch.setattr(containment, "_gh_call", gh)

    assert containment.read_native_children({}, parent_number=5).numbers == {10, 11}
    assert calls == [_LIST_CALL]


def test_entries_this_repository_s_name_cannot_place_leave_the_read_unreadable(
    monkeypatch,
) -> None:
    gh, _calls = _unanchored_tracker([{"number": 10, "repository_url": HERE_API}], here=None)
    monkeypatch.setattr(containment, "_gh_call", gh)

    read = containment.read_native_children({}, parent_number=5)
    resolution = containment.resolve_children({}, parent_number=5, corpus={}, corpus_complete=True)

    assert read.outcome is containment.NativeReadOutcome.UNREADABLE
    assert not resolution.complete
    assert "could not be read from #5's record" in (resolution.incomplete_reason or "")


def test_a_child_elsewhere_is_not_this_repository_s_issue_of_its_number(monkeypatch) -> None:
    # #42 here names #5 on its first line; acme/other#42 is natively under #5.
    elsewhere = {
        "number": 42,
        "repository_url": f"https://api.github.com/repos/{ELSEWHERE}",
        "parent_issue_url": f"{HERE_API}/issues/5",
    }
    monkeypatch.setattr(containment, "_gh_call", _answer([elsewhere]))

    resolution = containment.resolve_children(
        {}, parent_number=5, corpus={42: "Feature: #5\n"}, corpus_complete=True
    )

    assert [(c.ref, c.substrate.value) for c in resolution.children] == [
        ("#42", "textual"),
        (FOREIGN, "native"),
    ]
    assert resolution.numbers == [42]
    assert resolution.native_numbers == []
    assert [c.ref for c in resolution.foreign] == [FOREIGN]


def test_the_children_view_names_a_child_elsewhere_with_its_repository() -> None:
    resolution = containment.ChildResolution(
        children=(
            containment.ResolvedChild(42, containment.ChildSubstrate.TEXTUAL),
            containment.ResolvedChild(42, containment.ChildSubstrate.NATIVE, ELSEWHERE),
        ),
        native_supported=True,
    )
    body = containment.render_children_comment_body(
        parent_number=5, resolution=resolution, titles={42: "This repository's #42"}
    )
    assert "- #42 — This repository's #42  _(textual)_\n" in body
    # In a code span, which GitHub does not link: writing the view adds no
    # cross-reference to the issue elsewhere.
    assert f"- `{FOREIGN}`\n" in body
    assert body.count(FOREIGN) == body.count(f"`{FOREIGN}`") == 1


def test_a_member_id_reads_back_as_the_issue_it_names() -> None:
    here = containment.ResolvedChild(11, containment.ChildSubstrate.NATIVE)
    there = containment.ResolvedChild(42, containment.ChildSubstrate.NATIVE, ELSEWHERE)
    assert predicates.member_id(here) == "11"
    assert predicates.member_id(there) == FOREIGN
    assert predicates.read_subject("11") == 11
    assert predicates.read_subject(FOREIGN) == containment.ForeignIssue(ELSEWHERE, 42)
    for nonsense in ("", "#42", "acme#42", "acme/other#", "acme/other#4x", "a/b/c#1"):
        assert predicates.read_subject(nonsense) is None, nonsense


# A name outside the hosting service's alphabet (letters, digits, `-`, `_`, `.`;
# a number of ASCII digits only): a space, a `#`, a `/`, `..`, a lone dot.
_NOT_A_NAME = ("acme/oth er", "acme/oth#er", "acme/other/x", "acme/..", "../other", "acme/a..b")


@pytest.mark.parametrize("repository", (*_NOT_A_NAME, "acme/."))
def test_a_subject_naming_no_repository_names_no_issue(repository: str) -> None:
    assert not containment.is_repository_name(repository)
    assert predicates.read_subject(f"{repository}#42") is None
    assert containment.ForeignIssue.parse(f"{repository}#42") is None


# Digits Python's `str.isdigit` accepts and no issue number is written in:
# Arabic-Indic four-two, full-width four-two, a superscript two.
_NOT_ASCII_DIGITS = [chr(0x664) + chr(0x662), chr(0xFF14) + chr(0xFF12), chr(0xB2)]


@pytest.mark.parametrize("number", _NOT_ASCII_DIGITS)
def test_a_subject_number_is_ascii_digits_only(number: str) -> None:
    assert predicates.read_subject(number) is None
    assert predicates.read_subject(f"{ELSEWHERE}#{number}") is None


def test_the_service_s_own_names_are_names() -> None:
    for name in ("acme/other", "Acme-Co/my_repo.v2", "a/.github", "o/r-1"):
        assert containment.is_repository_name(name), name
        assert predicates.read_subject(f"{name}#7") == containment.ForeignIssue(name, 7)


@pytest.mark.parametrize("repository", _NOT_A_NAME)
def test_a_sub_issue_naming_no_repository_leaves_the_read_unreadable(
    monkeypatch, repository: str
) -> None:
    entry = {
        "number": 42,
        "repository_url": f"https://api.github.com/repos/{repository}",
        "parent_issue_url": f"{HERE_API}/issues/5",
    }
    monkeypatch.setattr(containment, "_gh_call", _answer([{"number": 10}, entry]))

    read = containment.read_native_children({}, parent_number=5)
    resolution = containment.resolve_children({}, parent_number=5, corpus={}, corpus_complete=True)

    assert read.outcome is containment.NativeReadOutcome.UNREADABLE
    assert (read.numbers, read.foreign) == (set(), frozenset())
    assert not resolution.complete
    assert "names a repository the hosting service could not have spelled" in (
        resolution.incomplete_reason or ""
    )


@pytest.mark.parametrize("repository", _NOT_A_NAME)
def test_an_issue_in_no_repository_is_unread_without_a_request(
    monkeypatch, repository: str
) -> None:
    calls: list[list[str]] = []

    def gh(args, _config):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, "{}", "")

    monkeypatch.setattr(containment, "_gh_call", gh)
    record = containment.read_issue_record({}, issue_number=42, repository=repository)

    assert isinstance(record, containment.UnreadIssue)
    assert "is not a repository name" in record.detail
    assert calls == []


# --- the fold: a child elsewhere holds its container like any other ------------


def test_an_open_child_elsewhere_holds_its_container(project: Path) -> None:
    issues = {CONTAINER: _container(), 10: _issue("CLOSED", "Feature: #5\n", ["type:task"])}
    _tracker(project, issues, native={CONTAINER: [10, FOREIGN]}, foreign={FOREIGN: _issue("OPEN")})

    held = _fold(project)

    assert held.opened is False
    assert f"member '{FOREIGN}'" in held.reason
    assert (held.reached, held.total) == (1, 2)


def test_a_closed_child_elsewhere_lets_its_container_close(project: Path) -> None:
    issues = {CONTAINER: _container(), 10: _issue("CLOSED", "Feature: #5\n", ["type:task"])}
    foreign = {FOREIGN: _issue("CLOSED", labels=[])}
    _tracker(project, issues, native={CONTAINER: [10, FOREIGN]}, foreign=foreign)

    opened = _fold(project)

    assert opened.opened is True
    assert opened.indeterminate is False
    assert (opened.reached, opened.total) == (2, 2)


def test_a_child_elsewhere_that_cannot_be_read_leaves_the_fold_indeterminate(
    project: Path,
) -> None:
    issues = {CONTAINER: _container()}
    foreign = {FOREIGN: _issue("CLOSED", labels=[])}
    _tracker(project, issues, native={CONTAINER: [FOREIGN]}, foreign=foreign, unreadable=(FOREIGN,))

    held = _fold(project)

    assert held.opened is False
    assert held.indeterminate is True
    assert f"member '{FOREIGN}'" in held.reason
    assert f"could not read {FOREIGN}" in held.stderr_tail


def test_this_repository_s_issue_of_the_same_number_is_not_read_for_it(project: Path) -> None:
    # #42 here is closed and no child of #5; acme/other#42, natively under #5, is
    # open. Read as this repository's #42, the child would fold done and the
    # container would open over it.
    issues = {CONTAINER: _container(), 42: _issue("CLOSED", labels=["type:task"])}
    _tracker(project, issues, native={CONTAINER: [FOREIGN]}, foreign={FOREIGN: _issue("OPEN")})

    held = _fold(project)

    assert held.opened is False
    assert f"member '{FOREIGN}'" in held.reason
    assert _reads_of_local(project, 42) == []


def test_a_child_here_costs_what_it_did_and_one_elsewhere_one_read(project: Path) -> None:
    issues = {CONTAINER: _container(), 11: _issue("CLOSED", labels=["type:task"])}
    foreign = {FOREIGN: _issue("CLOSED", labels=[])}
    _tracker(project, issues, native={CONTAINER: [11, FOREIGN]}, foreign=foreign)

    assert _fold(project).opened is True

    # A child here: its record read for membership, its fields for its state.
    assert _reads_of_local(project, 11) == [
        ["api", "repos/{owner}/{repo}/issues/11"],
        ["issue", "view", "11", "--json", "state,milestone,labels"],
    ]
    # A child elsewhere: one read of its record, there.
    assert _naming_elsewhere(project) == [["api", f"repos/{ELSEWHERE}/issues/42"]]


# --- close-issue: what holds a container, and nothing written elsewhere --------


def _close(root: Path) -> subprocess.CompletedProcess[str]:
    script = root / ".pkit" / "capabilities" / "project-management" / "scripts" / "close-issue.py"
    return subprocess.run(
        [str(script), str(CONTAINER), "--mode=cascade-eligibility-close", "--yes"],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=300,
    )


_RERUN = "re-run once `gh` is reachable"
# The removal of the child elsewhere's link under #5, run in this repository:
# its id is the one the sub-issue list gives it (the fake's 90000 + number).
_UNLINK = "gh api -X DELETE repos/{owner}/{repo}/issues/5/sub_issue -F sub_issue_id=90042"


def _writes(root: Path) -> list[list[str]]:
    """Every call that writes: an issue changed, or an API call that is not a read."""
    return [
        call
        for call in _calls(root)
        if call[:2] in (["issue", "comment"], ["issue", "close"], ["issue", "edit"])
        or (call[:1] == ["api"] and any(arg in ("-X", "--method", "-f", "-F") for arg in call))
    ]


def test_a_container_held_by_an_open_child_names_it_and_what_releases_it(
    project: Path, pkit_on_path: Path
) -> None:
    issues = {CONTAINER: _container(), 11: _issue("OPEN", "Feature: #5\n")}
    _tracker(project, issues)

    done = _close(project)

    assert done.returncode == 1, done.stderr
    assert "#5 is held by its open child(ren):\n  - #11\n" in done.stderr
    assert "→ close each open child; #5 becomes eligible when the last one closes." in done.stderr
    assert _RERUN not in done.stderr
    assert "held fail-closed" not in done.stderr
    assert _writes(project) == []


def test_a_container_held_by_an_open_child_elsewhere_names_its_repository(
    project: Path, pkit_on_path: Path
) -> None:
    issues = {CONTAINER: _container()}
    _tracker(project, issues, native={CONTAINER: [FOREIGN]}, foreign={FOREIGN: _issue("OPEN")})

    done = _close(project)

    assert done.returncode == 1, done.stderr
    assert f"  - {FOREIGN}, a sub-issue in another repository\n" in done.stderr
    assert (
        f"  → {FOREIGN} holds #5 until it is closed in {ELSEWHERE}, or its sub-issue link "
        f"under #5 is removed, in this repository, with:\n      {_UNLINK}\n"
    ) in done.stderr
    assert _RERUN not in done.stderr
    assert _writes(project) == []


def test_a_child_elsewhere_that_cannot_be_read_is_named_with_its_two_ways_out(
    project: Path, pkit_on_path: Path
) -> None:
    issues = {CONTAINER: _container()}
    foreign = {FOREIGN: _issue("OPEN")}
    _tracker(project, issues, native={CONTAINER: [FOREIGN]}, foreign=foreign, unreadable=(FOREIGN,))

    done = _close(project)

    assert done.returncode == 1, done.stderr
    assert "held fail-closed" in done.stderr
    assert (
        f"→ {FOREIGN}, a sub-issue in another repository, could not be read: gh exited 1"
    ) in done.stderr
    assert (
        f"    two ways out: make {FOREIGN} readable to the account `gh` uses here, then run "
        "this again; or remove its sub-issue link under #5, in this repository, with:\n"
        f"      {_UNLINK}\n"
    ) in done.stderr
    # A permission failure does not pass by running again: no re-run advice alone.
    assert _RERUN not in done.stderr
    assert "is held by its open child" not in done.stderr
    assert _writes(project) == []


def test_a_child_whose_issue_cannot_be_read_gets_the_re_run_advice(
    project: Path, pkit_on_path: Path
) -> None:
    # #14 is natively under #5, but no read finds it: not in the issue list, and
    # its record cannot be read — the fold stops at its membership.
    issues = {CONTAINER: _container()}
    _tracker(project, issues, native={CONTAINER: [14]})

    done = _close(project)

    assert done.returncode == 1, done.stderr
    assert "held fail-closed" in done.stderr
    assert "membership of candidate '14'" in done.stderr
    assert "→ #14 could not be read: it is not among the issues the issue list returned" in (
        done.stderr
    )
    assert _RERUN in done.stderr
    assert "is held by its open child" not in done.stderr


def test_an_open_child_whose_record_cannot_be_read_is_said_both_ways(
    project: Path, pkit_on_path: Path
) -> None:
    # #13 is open in the issue list, and its record cannot be read: the fold
    # stops at its membership — a read the engine could not make — and what the
    # refusal reads finds #13 open. Both are said, each with its remedy.
    issues = {CONTAINER: _container(), 13: _issue("OPEN")}
    _tracker(project, issues, native={CONTAINER: [13]}, unreadable=(13,))

    done = _close(project)

    assert done.returncode == 1, done.stderr
    held_open, _, failed = done.stderr.partition("held fail-closed")
    assert "#5 is held by its open child(ren):\n  - #13\n" in held_open
    assert "membership of candidate '13'" in failed
    assert _RERUN in failed


def test_an_open_child_and_a_failed_read_are_both_said_each_with_its_remedy(
    project: Path, pkit_on_path: Path
) -> None:
    # #11 here is open; acme/other#42 cannot be read. Each cause gets its block,
    # and the open child's account never sits under the failed-read header.
    issues = {CONTAINER: _container(), 11: _issue("OPEN", "Feature: #5\n")}
    foreign = {FOREIGN: _issue("OPEN")}
    _tracker(
        project,
        issues,
        native={CONTAINER: [11, FOREIGN]},
        foreign=foreign,
        unreadable=(FOREIGN,),
    )

    done = _close(project)

    assert done.returncode == 1, done.stderr
    held_open, _, failed = done.stderr.partition("held fail-closed")
    assert failed, "the failed-read block is said"
    assert "#5 is held by its open child(ren):\n  - #11\n" in held_open
    assert "→ close each open child; #5 becomes eligible when the last one closes." in held_open
    assert FOREIGN not in held_open
    assert "#11" not in failed and "'11'" not in failed
    assert f"→ {FOREIGN}, a sub-issue in another repository, could not be read" in failed
    assert f"two ways out: make {FOREIGN} readable" in failed
    assert _UNLINK in failed
    assert _writes(project) == []


def test_a_fold_stopped_on_a_read_is_said_as_a_failed_read(
    project: Path, pkit_on_path: Path
) -> None:
    # #13 is closed in the issue list, and its record cannot be read: the fold
    # stops at its membership before counting a member that holds it — a read
    # the engine could not make, which no read here sees.
    issues = {CONTAINER: _container(), 13: _issue("CLOSED", labels=["type:task"])}
    _tracker(project, issues, native={CONTAINER: [13]}, unreadable=(13,))

    done = _close(project)

    assert done.returncode == 1, done.stderr
    assert "held fail-closed" in done.stderr
    assert "membership of candidate '13'" in done.stderr
    assert _RERUN in done.stderr
    assert "is held by its open child" not in done.stderr


def test_a_hold_the_children_do_not_explain_claims_no_cause(
    project: Path, pkit_on_path: Path
) -> None:
    # #13 is closed in the issue list and its record reads; only its state read
    # (`gh issue view`) fails, so the fold counts it and stops there unresolved
    # — while every child the refusal reads is closed and readable.
    issues = {CONTAINER: _container(), 13: _issue("CLOSED", labels=["type:task"])}
    _tracker(project, issues, native={CONTAINER: [13]}, unviewable=(13,))

    done = _close(project)

    assert done.returncode == 1, done.stderr
    assert (
        "[refused] not cascade-eligible — the process engine's fold over #5's children "
        "did not open:\n  → member '13'"
    ) in done.stderr
    assert "held fail-closed" not in done.stderr
    assert "is held by its open child" not in done.stderr
    assert _RERUN not in done.stderr


def test_closing_over_a_closed_child_elsewhere_writes_nothing_there(
    project: Path, pkit_on_path: Path
) -> None:
    issues = {CONTAINER: _container()}
    foreign = {FOREIGN: _issue("CLOSED", labels=[])}
    _tracker(project, issues, native={CONTAINER: [FOREIGN]}, foreign=foreign)

    done = _close(project)

    assert done.returncode == 0, done.stderr
    assert "[ok] closed #5 (cascade-eligibility, completed)." in done.stdout
    writes = _writes(project)
    assert ["issue", "close", "5", "--reason", "completed"] in writes
    assert not [call for call in writes if any(ELSEWHERE in arg for arg in call)]
    # The child elsewhere is only ever read.
    assert _naming_elsewhere(project) == [["api", f"repos/{ELSEWHERE}/issues/42"]]


def test_the_refusal_reads_a_child_elsewhere_once_more_than_the_fold(
    project: Path, pkit_on_path: Path
) -> None:
    issues = {CONTAINER: _container()}
    _tracker(project, issues, native={CONTAINER: [FOREIGN]}, foreign={FOREIGN: _issue("OPEN")})

    done = _close(project)

    assert done.returncode == 1, done.stderr
    # Once by the fold's read of its state, once by the refusal saying what holds #5.
    assert _naming_elsewhere(project) == [["api", f"repos/{ELSEWHERE}/issues/42"]] * 2


# --- the real shape of a sub-issues answer ------------------------------------

# One entry of a real sub-issues answer — `gh api
# repos/aleskalfas/project-kit/issues/434/sub_issues --jq '.[0]'`, read on
# 2026-10-02 — reduced to the keys the seam reads. GitHub carries
# `parent_issue_url` on every entry (all 68 under #434 carried it).
REAL_ENTRY = json.loads(
    (REPO_ROOT / "tests" / "fixtures" / "github_sub_issue_entry.json").read_text(encoding="utf-8")
)
_SEAM_KEYS = {"id", "number", "repository_url", "parent_issue_url"}


def test_the_real_entry_carries_what_the_seam_reads(monkeypatch) -> None:
    assert set(REAL_ENTRY) == _SEAM_KEYS
    assert isinstance(REAL_ENTRY["id"], int) and isinstance(REAL_ENTRY["number"], int)
    gh, calls = _unanchored_tracker([REAL_ENTRY])
    monkeypatch.setattr(containment, "_gh_call", gh)

    read = containment.read_native_children({}, parent_number=434)

    # Placed by its own anchor: this repository's, at no cost beyond the list.
    assert (read.numbers, read.foreign) == ({435}, frozenset())
    assert calls == [["gh", "api", "--paginate", "repos/{owner}/{repo}/issues/434/sub_issues"]]

    elsewhere = dict(REAL_ENTRY, repository_url=f"https://api.github.com/repos/{ELSEWHERE}")
    gh, _calls = _unanchored_tracker([elsewhere])
    monkeypatch.setattr(containment, "_gh_call", gh)
    (child,) = containment.read_native_children({}, parent_number=434).foreign
    assert (child.ref, child.database_id) == (f"{ELSEWHERE}#435", REAL_ENTRY["id"])


def test_the_fake_tracker_answers_in_the_real_shape(project: Path) -> None:
    issues = {CONTAINER: _container()}
    _tracker(project, issues, native={CONTAINER: [10, FOREIGN]}, foreign={FOREIGN: _issue("OPEN")})

    listed = subprocess.run(
        ["gh", "api", "--paginate", "repos/{owner}/{repo}/issues/5/sub_issues"],
        capture_output=True,
        text=True,
        check=True,
    )

    assert [set(entry) for entry in json.loads(listed.stdout)] == [_SEAM_KEYS, _SEAM_KEYS]


# --- linking, and every write a verb makes, with a child elsewhere --------------


def test_a_child_elsewhere_does_not_make_this_repository_s_issue_linked(monkeypatch) -> None:
    # acme/other#42 is under #5; this repository's #42 has no native parent. The
    # linked check does not take one for the other: #42 is posted.
    listed = {
        "id": 4242,
        "number": 42,
        "repository_url": f"https://api.github.com/repos/{ELSEWHERE}",
        "parent_issue_url": f"{HERE_API}/issues/5",
    }
    gh, calls = _unanchored_tracker([listed])
    monkeypatch.setattr(containment, "_gh_call", gh)

    result = containment.link_sub_issue({}, parent_number=5, child_number=42)

    assert result.outcome is containment.LinkOutcome.LINKED
    post = ["gh", "api", "-X", "POST", "repos/{owner}/{repo}/issues/5/sub_issues"]
    assert [call for call in calls if "POST" in call] == [[*post, "-F", "sub_issue_id=1042"]]


# A reference to an issue elsewhere GitHub would link: not inside a code span.
_LINKED_ELSEWHERE = re.compile(rf"(?<!`){re.escape(ELSEWHERE)}#[0-9]+")


def _writes_stay_here(calls: list[list[str]]) -> list[list[str]]:
    """The writing calls among `calls`, each checked to be addressed to this
    repository and to name an issue elsewhere only in a code span."""
    writes = [call for call in calls if {"POST", "PATCH", "DELETE"} & set(call)]
    for call in writes:
        assert not any(f"repos/{ELSEWHERE}" in arg for arg in call), call
        assert not any(_LINKED_ELSEWHERE.search(arg) for arg in call), call
    return writes


def test_create_issue_s_children_view_leaves_nothing_elsewhere(monkeypatch) -> None:
    spec = importlib.util.spec_from_file_location(
        "pm_create_issue_foreign_child", CAP_SCRIPTS / "create-issue.py"
    )
    assert spec is not None and spec.loader is not None
    create_issue = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(create_issue)
    listed = {
        "id": 90042,
        "number": 42,
        "repository_url": f"https://api.github.com/repos/{ELSEWHERE}",
        "parent_issue_url": f"{HERE_API}/issues/5",
    }
    rows = [
        {"number": 5, "title": "[Feature] F", "body": "EPIC: #1\n"},
        {"number": 11, "title": "[Task] t", "body": "Feature: #5\n"},
    ]
    calls: list[list[str]] = []

    def gh(args, _config):
        calls.append(list(args))
        if args[:3] == ["gh", "issue", "list"]:
            return subprocess.CompletedProcess(args, 0, json.dumps(rows), "")
        if "POST" in args:
            return subprocess.CompletedProcess(args, 0, "{}", "")
        if args[-1] == "repos/{owner}/{repo}/issues/5/sub_issues":
            return subprocess.CompletedProcess(args, 0, json.dumps([listed]), "")
        if args[-1] == "repos/{owner}/{repo}/issues/5/comments":
            return subprocess.CompletedProcess(args, 0, "[]", "")
        raise AssertionError(f"unexpected gh call: {args}")

    monkeypatch.setattr(containment, "_gh_call", gh)
    create_issue._refresh_parent_children_view({}, parent_number=5, containment_mode="textual")

    (write,) = _writes_stay_here(calls)
    assert write[4] == "repos/{owner}/{repo}/issues/5/comments"
    assert f"- `{FOREIGN}`\n" in write[-1]


@pytest.mark.parametrize("subject", [FOREIGN, "not-an-issue"])
def test_the_lifecycle_world_refuses_a_subject_it_does_not_hold(subject: str) -> None:
    """The in-memory tracker other suites drive the engine against holds this
    repository's issues only: a member elsewhere, or an id naming no issue, is
    refused with why — never a crash on `int()`."""
    from types import SimpleNamespace

    from project_kit.process import PredicateFailure
    from tests.pm_lifecycle_world import answer_from_tracker

    answer = answer_from_tracker(SimpleNamespace(subject=subject), "detect-state", None)  # type: ignore[arg-type]

    assert isinstance(answer, PredicateFailure)
    assert answer.cause == "exited 2"
    assert repr(subject) in answer.stderr_tail
    assert "holds this repository's issues only" in answer.stderr_tail
