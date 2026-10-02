"""Every reader of an issue's parent reads it one way (#1281).

The containment seam resolves an issue's parent (`containment.resolve_parent`):
the native parent wins wherever one was read, and how the native link and the
first line stand — agreed, native only, first line only, disagreeing, none,
unread — comes with it. A consumer that writes on the parent (the forward
cascade) acts only where the two agree or a conforming first line is the only
record; one that only reads (the closure cascade's report, the close gate's
fold, show-tree) follows the native parent, counts a first-line parent as well,
and labels the disagreement.

One stubbed world — an EPIC, two Features and an Umbrella under it, natively
and textually linked, and a child whose two records each scenario sets — and
every reader driven over it through its real code path:

- the resolver;
- the forward cascade's plan (`move-issue`'s preview of a promotion);
- close-issue's closure-cascade report;
- the fold — `resolve_children` for each candidate parent, and
  `cascade_membership` for the child;
- show-tree's `_link_parents`.

Each row of the table says the parent the seam resolves, the parents the close
gate counts the child under (which close-issue reports on), the ancestors the
forward cascade brings level (none on every row but the two walking ones), and
where show-tree lists it. The `gh` the readers call answers from the world;
any call it does not expect fails the test.
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest
from ruamel.yaml import YAML

REPO_ROOT = Path(__file__).resolve().parent.parent
CAPABILITY = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
SCRIPTS = CAPABILITY / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from _lib import containment  # noqa: E402
from _lib import lifecycle_predicates as predicates  # noqa: E402

_YAML = YAML(typ="safe")
ISSUE_TYPES = _YAML.load((CAPABILITY / "schemas" / "issue-types.yaml").read_text(encoding="utf-8"))
CLASSIFICATION = _YAML.load(
    (CAPABILITY / "schemas" / "classification.yaml").read_text(encoding="utf-8")
)
WORKFLOW = _YAML.load((CAPABILITY / "schemas" / "workflow.yaml").read_text(encoding="utf-8"))
REPOSITORY_URL = "https://api.github.com/repos/acme/widget"

EPIC, FEATURE, OTHER_FEATURE, UMBRELLA, CHILD = 1, 2, 3, 4, 10
CONTAINERS = (EPIC, FEATURE, OTHER_FEATURE, UMBRELLA)
NON_CONFORMING = "first line not an allowed form"


def _load(script: str, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def mi() -> ModuleType:
    return _load("move-issue.py", "pm_move_issue_parent_resolution_parity")


@pytest.fixture(scope="module")
def cl() -> ModuleType:
    return _load("close-issue.py", "pm_close_issue_parent_resolution_parity")


@pytest.fixture(scope="module")
def st() -> ModuleType:
    return _load("show-tree.py", "pm_show_tree_parent_resolution_parity")


# --- the world --------------------------------------------------------------


def _issue(title: str, body: str, labels: tuple[str, ...] = ()) -> dict[str, Any]:
    return {
        "title": title,
        "body": body,
        "state": "OPEN",
        "labels": [{"name": name} for name in labels],
        "milestone": None,
    }


@dataclass
class World:
    """The tracker the readers' `gh` calls reach. `natives` maps an issue to
    its native parent — a number here, or `owner/repo#<n>` in another
    repository; `unread` holds the issues whose REST record cannot be read."""

    issues: dict[int, dict[str, Any]]
    natives: dict[int, int | str]
    unread: set[int] = field(default_factory=set)
    calls: list[list[str]] = field(default_factory=list)

    def run(self, argv: Any, *_args: Any, **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        args = [str(arg) for arg in argv]
        self.calls.append(args)
        if args[:3] == ["gh", "issue", "list"]:
            fields = args[args.index("--json") + 1].split(",")
            rows = [
                {f: dict(issue, number=n).get(f) for f in fields}
                for n, issue in self.issues.items()
            ]
            return self._answer(args, rows)
        if args[:3] == ["gh", "issue", "view"]:
            fields = args[args.index("--json") + 1].split(",")
            return self._answer(args, {f: self.issues[int(args[3])].get(f) for f in fields})
        path = args[-1] if args[:2] == ["gh", "api"] else ""
        children = re.fullmatch(r"repos/\{owner\}/\{repo\}/issues/(\d+)/sub_issues", path)
        if children:
            parent = int(children.group(1))
            native = sorted(child for child, p in self.natives.items() if p == parent)
            return self._answer(args, [{"number": n} for n in native])
        record = re.fullmatch(r"repos/\{owner\}/\{repo\}/issues/(\d+)", path)
        if record:
            return self._record(args, int(record.group(1)))
        raise AssertionError(f"unexpected call: {args}")

    def _record(self, args: list[str], number: int) -> subprocess.CompletedProcess[str]:
        if number in self.unread:
            return subprocess.CompletedProcess(args, 1, "", "HTTP 502: Bad Gateway")
        issue = self.issues[number]
        record = dict(issue, number=number, repository_url=REPOSITORY_URL)
        native = self.natives.get(number)
        if isinstance(native, str):
            repository, parent = native.split("#")
            record["parent_issue_url"] = (
                f"https://api.github.com/repos/{repository}/issues/{parent}"
            )
        elif native is not None:
            record["parent_issue_url"] = f"{REPOSITORY_URL}/issues/{native}"
        return self._answer(args, record)

    @staticmethod
    def _answer(args: list[str], payload: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 0, json.dumps(payload), "")

    def record_reads(self, number: int) -> int:
        return self.calls.count(["gh", "api", f"repos/{{owner}}/{{repo}}/issues/{number}"])


# --- the table --------------------------------------------------------------


@dataclass(frozen=True)
class Row:
    """One scenario: the child's first line and native parent, and what every
    reader makes of them.

    ``named`` is the issue the first line names, in any form; ``parent`` the
    parent the seam resolves (`owner/repo#<n>` for one in another repository);
    ``fold`` the parents the close gate counts the child under, which
    close-issue reports on; ``walk`` the ancestors the forward cascade brings
    level, empty where it walks nothing; ``tree`` show-tree's ``parent_number``;
    ``listed`` the marks show-tree gives the child under each parent it lists it
    under."""

    first_line: str
    native: int | str | None
    named: int | None
    kind: str
    parent: int | str
    fold: tuple[int, ...]
    walk: tuple[int, ...]
    tree: int
    listed: dict[int, tuple[str, ...]]
    child_type: str = "task"
    unread: bool = False


# The body `create-issue --parent 2 --milestone 7` files: the milestone on the
# first line, the issue parent on the native link alone.
_MILESTONE_LINE = "Milestone: [#7](../milestone/7)"

ROWS: dict[str, Row] = {
    "conforming line": Row(
        "Feature: #2", None, 2, "textual-only", 2, (2,), (2, 1), 2, {2: ("textual",)}
    ),
    "loose line, agreeing native parent": Row(
        "Feature: #2 — auth", 2, 2, "agreed", 2, (2,), (2, 1), 2, {2: (NON_CONFORMING,)}
    ),
    "loose line alone": Row(
        "Feature: #2 — auth", None, 2, "textual-only", 2, (2,), (), 2,
        {2: ("textual", NON_CONFORMING)},
    ),
    "native only": Row("## What", 2, None, "native-only", 2, (2,), (), 2, {2: ()}),
    "native only, --parent with --milestone": Row(
        _MILESTONE_LINE, 2, None, "native-only", 2, (2,), (), 2, {2: ()}
    ),
    "disagreement": Row(
        "Feature: #2", 3, 2, "disagree", 3, (3, 2), (), 3,
        {3: (), 2: ("textual", "native parent #3")},
    ),
    "native parent in another repository": Row(
        "Feature: #2", "other/repo#9", 2, "disagree", "other/repo#9", (2,), (), 2,
        {2: ("textual",)},
    ),
    "integration marker first": Row(
        "Integration: integration/widgets\nFeature: #2", 2, 2, "agreed", 2, (2,), (2, 1), 2,
        {2: ()},
    ),
    "unread record": Row(
        "Feature: #2", 2, 2, "unread", 2, (2,), (), 2, {2: ()}, unread=True
    ),
    "Feature under an Umbrella": Row(
        "Umbrella: #4", 4, 4, "agreed", 4, (4,), (4, 1), 4, {4: ()}, child_type="feature"
    ),
}  # fmt: skip

# The rows the forward cascade walks on: the records agree, or a conforming
# first line is the only record.
WALKING = {"conforming line", "loose line, agreeing native parent", "integration marker first",
           "Feature under an Umbrella"}  # fmt: skip


def _world(row: Row) -> World:
    child = (
        _issue("[Feature] The child", f"{row.first_line}\n\n## What\n")
        if row.child_type == "feature"
        else _issue("[Task] The child", f"{row.first_line}\n\n## What\n", ("type:task",))
    )
    issues = {
        EPIC: _issue("[EPIC] The epic", "## What\n"),
        FEATURE: _issue("[Feature] A feature", "EPIC: #1\n\n## What\n"),
        OTHER_FEATURE: _issue("[Feature] Another feature", "EPIC: #1\n\n## What\n"),
        UMBRELLA: _issue("[Umbrella] A bucket", "EPIC: #1\n\n## What\n"),
        CHILD: child,
    }
    natives: dict[int, int | str] = {FEATURE: EPIC, OTHER_FEATURE: EPIC, UMBRELLA: EPIC}
    if row.native is not None:
        natives[CHILD] = row.native
    return World(issues, natives, unread={CHILD} if row.unread else set())


@pytest.fixture(params=sorted(ROWS))
def scenario(request, monkeypatch: pytest.MonkeyPatch) -> tuple[str, Row, World]:
    row = ROWS[request.param]
    world = _world(row)
    monkeypatch.setattr(subprocess, "run", world.run)
    monkeypatch.setattr(predicates, "_capability_root", lambda: CAPABILITY)
    monkeypatch.setattr(predicates, "_config", lambda _root: {})
    return request.param, row, world


def _ref(parent: containment.NativeParent | None) -> int | str | None:
    if parent is None:
        return None
    return parent.ref if parent.repository else parent.number


# --- the drivers ------------------------------------------------------------


def _forward_cascade(mi: ModuleType, row: Row, capsys) -> tuple[int, ...]:
    """The ancestors a promotion of the child plans to bring level."""
    mover = mi._MovedIssue(
        number=CHILD,
        body=f"{row.first_line}\n\n## What\n",
        structural_type=row.child_type,
        origin="todo",
        target="backlog",
        closed=False,
        closed_as=None,
    )
    context = mi._CascadeContext(
        workflow=WORKFLOW,
        issue_types=ISSUE_TYPES,
        classification=CLASSIFICATION,
        config={},
        substrate_map=None,
        invoker=SimpleNamespace(github_login="octocat"),
        projection="audit",
        levels=mi._cascade_levels(WORKFLOW),
    )
    plan = mi._preview_forward_cascade(mover, context)
    capsys.readouterr()
    return tuple(ancestor.number for ancestor in plan.ancestors) if plan else ()


def _closure_report(cl: ModuleType, row: Row, capsys) -> tuple[tuple[int, ...], str, str]:
    """The parents close-issue's closure cascade checks, and what it printed."""
    body = f"{row.first_line}\n\n## What\n"
    cl._report_parents(CHILD, body, row.child_type, ISSUE_TYPES, {})
    out, err = capsys.readouterr()
    m = re.search(r"parents to check for eligibility: (.*)\n", out)
    checked = tuple(int(n) for n in re.findall(r"#(\d+)", m.group(1))) if m else ()
    return checked, out, err


def _fold_parents() -> tuple[int, ...]:
    """The containers whose child set holds the child, as the close gate's
    members source resolves each."""
    return tuple(
        parent
        for parent in CONTAINERS
        if CHILD in containment.resolve_children({}, parent_number=parent).numbers
    )


def _tree(st: ModuleType, world: World) -> dict[int, Any]:
    rows = [dict(issue, number=n) for n, issue in world.issues.items()]
    issues = st._parse_issues(rows, ISSUE_TYPES, CLASSIFICATION)
    st._link_parents(issues, {}, corpus_complete=True, issue_types=ISSUE_TYPES)
    return issues


# --- the pins ---------------------------------------------------------------


def test_the_resolver_returns_the_rows_parent_and_kind(scenario) -> None:
    _, row, _ = scenario
    resolution = containment.resolve_parent(
        {}, issue_number=CHILD, structural_type=row.child_type, issue_types=ISSUE_TYPES,
        body=f"{row.first_line}\n\n## What\n",
    )  # fmt: skip
    assert resolution.kind.value == row.kind
    assert _ref(resolution.parent) == row.parent
    assert resolution.local_parents == row.fold


def test_the_forward_cascade_walks_only_on_the_two_walking_rows(scenario, mi, capsys) -> None:
    name, row, _ = scenario
    walked = _forward_cascade(mi, row, capsys)
    assert walked == row.walk
    assert bool(walked) is (name in WALKING)


def test_the_closure_report_checks_every_parent_the_gate_counts(scenario, cl, capsys) -> None:
    _, row, _ = scenario
    checked, _, _ = _closure_report(cl, row, capsys)
    assert checked == row.fold


def test_the_fold_counts_the_child_under_the_native_and_the_first_line_parent(
    scenario,
) -> None:
    _, row, _ = scenario
    assert sorted(_fold_parents()) == sorted(row.fold)


def test_the_membership_step_admits_the_child_and_accounts_for_its_parent(scenario) -> None:
    _, row, _ = scenario
    out = predicates.cascade_membership(CHILD)
    if row.unread:
        assert out.get(predicates.INDETERMINATE_KEY) is True
        return
    assert out["result"] is True
    assert out["detail"] == {"parent_ref": row.named, "parent_kind": row.kind}


def test_show_tree_lists_the_child_where_the_gate_counts_it(scenario, st) -> None:
    _, row, world = scenario
    issues = _tree(st, world)
    assert issues[CHILD].parent_number == row.tree
    listed = {
        parent: st._listing_marks(issues[parent], CHILD)
        for parent in CONTAINERS
        if CHILD in issues[parent].children
    }
    assert listed == row.listed
    assert sorted(listed) == sorted(row.fold)


def test_every_reader_resolves_the_same_parent(scenario, mi, cl, st, capsys) -> None:
    """The parent the seam resolves is the parent each reader acts on: the
    cascade's first ancestor where it walks, the close report's first parent,
    the fold's native set where the native parent is local, and show-tree's
    `parent_number` wherever it could see the native parent."""
    _, row, world = scenario
    walked = _forward_cascade(mi, row, capsys)
    checked, _, _ = _closure_report(cl, row, capsys)
    tree = _tree(st, world)[CHILD].parent_number
    local = row.parent if isinstance(row.parent, int) else None
    if walked:
        assert walked[0] == row.parent
    if local is not None:
        assert checked[0] == local
        assert tree == local
        assert local in _fold_parents()
    else:
        # Abroad: no reader here asserts anything of a native parent elsewhere;
        # each follows the first line.
        assert checked == (tree,) == _fold_parents()


# --- what each reader says --------------------------------------------------


def test_the_closure_report_words_a_disagreement_with_its_remedy(cl, monkeypatch, capsys) -> None:
    row = ROWS["disagreement"]
    monkeypatch.setattr(subprocess, "run", _world(row).run)
    _, out, err = _closure_report(cl, row, capsys)
    assert "[cascade] parents to check for eligibility: #3, #2\n" in out
    assert (
        "[warn] #10's first line names #2, its native parent is #3.\n"
        "  → the native parent wins (DEC-005): `set-field 10 --parent 3` rewrites #10's first "
        "line to name it.\n"
    ) in err


def test_the_closure_report_notes_a_native_parent_no_line_names(cl, monkeypatch, capsys) -> None:
    row = ROWS["native only, --parent with --milestone"]
    monkeypatch.setattr(subprocess, "run", _world(row).run)
    _, out, err = _closure_report(cl, row, capsys)
    assert "[cascade] parents to check for eligibility: #2\n" in out
    assert "[note] #10's first line names no parent issue, its native parent is #2.\n" in out
    assert "[warn]" not in err


def test_the_closure_report_checks_no_parent_in_another_repository(cl, monkeypatch, capsys) -> None:
    row = ROWS["native parent in another repository"]
    monkeypatch.setattr(subprocess, "run", _world(row).run)
    _, out, err = _closure_report(cl, row, capsys)
    assert "[cascade] parents to check for eligibility: #2\n" in out
    assert (
        "[warn] #10's first line names #2, its native parent is other/repo#9.\n"
        "  → other/repo#9 is in another repository, which no first-line form can name and the "
        "closure cascade does not check; if #2 is its parent, `set-field 10 --parent 2` moves "
        "the native link under it.\n"
    ) in err


def test_the_closure_report_says_the_native_parent_was_not_compared(
    cl, monkeypatch, capsys
) -> None:
    row = ROWS["unread record"]
    monkeypatch.setattr(subprocess, "run", _world(row).run)
    checked, _, err = _closure_report(cl, row, capsys)
    assert checked == (2,)
    assert (
        "[warn] #10's record could not be read to hold its native parent to #2, the parent its "
        "first line names (gh exited 1"
    ) in err
    assert "#2 is checked, and the native parent was not compared.\n" in err


def test_show_tree_says_how_the_records_stand_in_json(st, monkeypatch) -> None:
    row = ROWS["disagreement"]
    world = _world(row)
    monkeypatch.setattr(subprocess, "run", world.run)
    issue = _tree(st, world)[CHILD]
    assert st._issue_to_dict(issue)["parent_resolution"] == {
        "kind": "disagree",
        "native_parent": 3,
        "first_line_parent": 2,
        "first_line_form": "conforming",
    }


# --- what each reader costs -------------------------------------------------


def test_a_close_reads_the_closed_issue_once_and_each_checked_parent_once(
    cl, monkeypatch, capsys
) -> None:
    row = ROWS["disagreement"]
    world = _world(row)
    monkeypatch.setattr(subprocess, "run", world.run)
    _closure_report(cl, row, capsys)
    assert world.record_reads(CHILD) == 1
    views = [argv[3] for argv in world.calls if argv[1:3] == ["issue", "view"]]
    assert views == ["3", "2"]
    assert len(world.calls) == 3


def test_the_members_half_of_the_fold_costs_what_it_did(monkeypatch) -> None:
    """One issue list and one sub-issues read for the container — no read of
    any member's own record."""
    world = _world(ROWS["disagreement"])
    monkeypatch.setattr(subprocess, "run", world.run)
    monkeypatch.setattr(predicates, "_capability_root", lambda: CAPABILITY)
    monkeypatch.setattr(predicates, "_config", lambda _root: {})
    out = predicates.cascade_members(FEATURE)
    assert out["members"] == [str(CHILD)]
    assert [argv[1:3] for argv in world.calls] == [["api", "--paginate"], ["issue", "list"]]


def test_the_membership_half_reads_each_candidate_once(monkeypatch) -> None:
    world = _world(ROWS["disagreement"])
    monkeypatch.setattr(subprocess, "run", world.run)
    monkeypatch.setattr(predicates, "_capability_root", lambda: CAPABILITY)
    monkeypatch.setattr(predicates, "_config", lambda _root: {})
    predicates.cascade_membership(CHILD)
    assert world.calls == [["gh", "api", f"repos/{{owner}}/{{repo}}/issues/{CHILD}"]]


def test_the_forward_cascade_reads_the_moved_issue_and_each_ancestor_once(
    mi, monkeypatch, capsys
) -> None:
    row = ROWS["Feature under an Umbrella"]
    world = _world(row)
    monkeypatch.setattr(subprocess, "run", world.run)
    assert _forward_cascade(mi, row, capsys) == (UMBRELLA, EPIC)
    assert [world.record_reads(n) for n in (CHILD, UMBRELLA, EPIC)] == [1, 1, 1]
    assert len(world.calls) == 3


def test_show_tree_reads_no_issue_upward(st, monkeypatch) -> None:
    world = _world(ROWS["disagreement"])
    monkeypatch.setattr(subprocess, "run", world.run)
    _tree(st, world)
    assert not any(world.record_reads(n) for n in world.issues)
    assert all(argv[-1].endswith("/sub_issues") for argv in world.calls)
