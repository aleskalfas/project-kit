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

import json
import os
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
# number here, or `owner/repo#<n>`), and `unreadable` lists what cannot be read.
# Every call is appended to `_calls.jsonl`; a call it does not expect fails.
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
    if number in unreadable or number not in issues:
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
) -> None:
    tracker = {
        "issues": {str(n): record for n, record in {1: _epic(), **issues}.items()},
        "native": {str(p): [str(c) for c in cs] for p, cs in (native or {}).items()},
        "foreign": foreign or {},
        "unreadable": [str(u) for u in unreadable],
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
    assert f"- {FOREIGN}\n" in body


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
        f"→ {FOREIGN} holds #5 until it is closed in {ELSEWHERE}, or its sub-issue link "
        "under #5 is removed; nothing is written in another repository from here."
    ) in done.stderr
    assert _RERUN not in done.stderr
    assert _writes(project) == []


def test_a_child_elsewhere_that_cannot_be_read_is_named_with_the_re_run_advice(
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
    assert f"{FOREIGN} holds #5 until it is closed in {ELSEWHERE}" in done.stderr
    assert _RERUN in done.stderr
    assert "is held by its open child" not in done.stderr
    assert _writes(project) == []


def test_a_child_whose_issue_cannot_be_read_gets_the_re_run_advice(
    project: Path, pkit_on_path: Path
) -> None:
    # #13 is natively under #5, but its issue cannot be read: the fold stops at
    # its membership, a read that failed.
    issues = {CONTAINER: _container(), 13: _issue("OPEN")}
    _tracker(project, issues, native={CONTAINER: [13]}, unreadable=(13,))

    done = _close(project)

    assert done.returncode == 1, done.stderr
    assert "held fail-closed" in done.stderr
    assert "membership of candidate '13'" in done.stderr
    assert _RERUN in done.stderr
    assert "is held by its open child" not in done.stderr


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
