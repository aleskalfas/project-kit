"""A natively linked child holds its container open, whatever its first line says (#1304).

The close gate's children-half is the process engine's fold over the issue
lifecycle (DEC-034, COR-037). Its candidates are the container's children as the
containment seam resolves them — native sub-issues as well as issues whose first
line names the container (ADR-035) — and the engine then asks `cascade-membership`
of each. That second question used to answer "member" only for a candidate whose
first line names an issue, and the engine drops a candidate it determinately
rejects: a child linked natively whose first line names none was listed, dropped,
and its container could close while it was open. Two ordinary routes file such a
child — a sub-issue linked in GitHub's UI, and `create-issue --parent N
--milestone M`, whose first line is the `Milestone:` ref — and each is pinned here.

Pinned, through the real engine and the shipped predicate scripts against a fake
`gh` on PATH (each script given this test's interpreter rather than its `uv run
--script` shebang):

- an open native child whose first line names no issue holds the container, and
  closing it opens the fold — for each route;
- an ordinary textual child (first line names the container, no native link)
  still holds and still counts;
- a candidate whose issue cannot be read leaves the fold indeterminate, so the
  container is not eligible.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML

REPO_ROOT = Path(__file__).resolve().parents[1]
CAP_SRC = REPO_ROOT / ".pkit" / "capabilities" / "project-management"
CAP_SCRIPTS = CAP_SRC / "scripts"
if str(CAP_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(CAP_SCRIPTS))

from _lib import body_parent_ref  # noqa: E402

from project_kit.process import CascadeResolution, ProcessEngine, load_definition  # noqa: E402

ADDRESS = "project-management:issue-lifecycle"
CONTAINER = 5
MILESTONE = 7

_VALID_CONFIG = "schema_version: 1\ndefault_branch: main\nworkstreams: []\n"

# A fake `gh` answering from `_tracker.json`: `issues` maps each issue number to
# its record, `native` maps a parent to its native sub-issues, and `unreadable`
# lists the issues `gh` cannot read. It answers the reads the fold makes — the
# issue list, a parent's sub-issues, one issue's fields, one issue's REST record
# with its native parent — and fails anything else, so a read the fold is not
# expected to make shows as an error.
_FAKE_GH = """\
import json, pathlib, sys
root = pathlib.Path({root!r})
tracker = json.loads((root / "_tracker.json").read_text())
issues = tracker["issues"]
args = sys.argv[1:]

def pick(record, fields):
    return {{field: record.get(field) for field in fields}}

if args[:2] == ["issue", "view"]:
    number = args[2]
    if number in tracker["unreadable"] or number not in issues:
        sys.stderr.write(
            "GraphQL: Could not resolve to an issue with the number of " + number + ".\\n"
        )
        sys.exit(1)
    fields = args[args.index("--json") + 1].split(",")
    print(json.dumps(pick(dict(issues[number], number=int(number)), fields)))
elif args[:2] == ["issue", "list"]:
    fields = args[args.index("--json") + 1].split(",")
    rows = [pick(dict(record, number=int(n)), fields) for n, record in issues.items()]
    print(json.dumps(rows))
elif args[:1] == ["api"] and args[-1].endswith("/sub_issues"):
    parent = args[-1].split("/")[-2]
    print(json.dumps([{{"number": n}} for n in tracker["native"].get(parent, [])]))
elif args[:1] == ["api"] and args[-1].rsplit("/", 1)[-1].isdigit():
    number = args[-1].rsplit("/", 1)[-1]
    if number in tracker["unreadable"] or number not in issues:
        sys.stderr.write("gh: Not Found (HTTP 404)\\n")
        sys.exit(1)
    here = "https://api.github.com/repos/acme/widget"
    record = dict(issues[number], number=int(number), repository_url=here)
    for parent, children in tracker["native"].items():
        if int(number) in children:
            record["parent_issue_url"] = here + "/issues/" + parent
    print(json.dumps(record))
else:
    sys.stderr.write("unexpected gh call: " + " ".join(args) + "\\n")
    sys.exit(1)
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
    _executable(bin_dir / "gh", f"#!{sys.executable}\n" + _FAKE_GH.format(root=str(root)))
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))
    return root


def _issue(state: str, body: str, labels: list[str] | None = None) -> dict[str, Any]:
    return {
        "state": state,
        "body": body,
        "labels": [{"name": n} for n in (labels or ["type:task", "state:in-progress"])],
        "milestone": None,
    }


def _tracker(
    root: Path,
    issues: dict[int, dict[str, Any]],
    *,
    native: dict[int, list[int]] | None = None,
    unreadable: tuple[int, ...] = (),
) -> None:
    tracker = {
        "issues": {str(n): record for n, record in issues.items()},
        "native": {str(p): children for p, children in (native or {}).items()},
        "unreadable": [str(n) for n in unreadable],
    }
    (root / "_tracker.json").write_text(json.dumps(tracker), encoding="utf-8")


def _fold(root: Path) -> CascadeResolution:
    engine = ProcessEngine.for_subject(load_definition(root, ADDRESS), root, str(CONTAINER))
    resolution = engine.resolve_cascade_outcome()
    assert resolution is not None, "the issue lifecycle declares the closure fold"
    return resolution


def _container() -> dict[str, Any]:
    return _issue(
        "OPEN", "EPIC: #1\n\n## What\n\n- [x] done\n", ["type:feature", "state:in-progress"]
    )


# A sub-issue linked in GitHub's UI: its body is whatever its author wrote, and
# here the first line names no issue.
_UI_LINKED_BODY = "## What\n\nFiled on its own and linked under the Feature in the UI.\n"


def _create_issue_body() -> str:
    """The body `create-issue --type task --parent 5 --milestone 7` files: the
    shipped Task template with the parent-ref line `create-issue` builds, which
    is the `Milestone:` ref whenever a milestone is given."""
    spec = importlib.util.spec_from_file_location(
        "pm_create_issue_native_child_under_test", CAP_SCRIPTS / "create-issue.py"
    )
    assert spec is not None and spec.loader is not None
    create_issue = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(create_issue)
    types = YAML(typ="safe").load((CAP_SRC / "schemas" / "issue-types.yaml").read_text())
    line = create_issue._parent_ref_line(
        types["types"]["task"],
        parent_num=CONTAINER,
        milestone_num=MILESTONE,
        parent_label="Feature",
    )
    return create_issue._compose_body(CAP_SRC / "templates" / "Task.md", parent_ref=line)


_ROUTES = {
    "linked-in-the-ui": lambda: _UI_LINKED_BODY,
    "create-issue-parent-and-milestone": _create_issue_body,
}


@pytest.mark.parametrize("route", sorted(_ROUTES))
def test_an_open_native_child_naming_no_issue_holds_its_container(
    project: Path, route: str
) -> None:
    child_body = _ROUTES[route]()
    # The route's own premise: the child's first line names no issue, so only
    # the native link makes it a child of #5.
    assert body_parent_ref.named_issue(child_body) is None
    issues = {
        CONTAINER: _container(),
        10: _issue("CLOSED", "Feature: #5\n\n## What\n", ["type:task"]),
        11: _issue("OPEN", child_body),
    }
    _tracker(project, issues, native={CONTAINER: [11]})

    held = _fold(project)
    assert held.opened is False
    assert "member '11'" in held.reason
    assert "'in-progress'" in held.reason
    # #10 was folded as done before #11 held the fold: both are members.
    assert (held.reached, held.total) == (1, 2)

    issues[11] = _issue("CLOSED", child_body, ["type:task"])
    _tracker(project, issues, native={CONTAINER: [11]})

    opened = _fold(project)
    assert opened.opened is True
    assert opened.indeterminate is False
    assert (opened.reached, opened.total) == (2, 2)


def test_the_create_issue_body_carries_the_milestone_line_and_no_issue_ref() -> None:
    # What makes the create-issue route a native-only child: the parent-ref slot
    # holds the `Milestone:` ref, which names no issue.
    body = _create_issue_body()
    assert f"Milestone: [#{MILESTONE}](../milestone/{MILESTONE})" in body.splitlines()
    assert f"Feature: #{CONTAINER}" not in body


def test_an_ordinary_textual_child_still_holds_and_still_counts(project: Path) -> None:
    issues = {
        CONTAINER: _container(),
        12: _issue("OPEN", "Feature: #5\n\n## What\n"),
    }
    _tracker(project, issues)

    held = _fold(project)
    assert held.opened is False
    assert "member '12'" in held.reason

    issues[12] = _issue("CLOSED", "Feature: #5\n\n## What\n", ["type:task"])
    _tracker(project, issues)

    opened = _fold(project)
    assert opened.opened is True
    assert (opened.reached, opened.total) == (1, 1)


def test_an_unreadable_candidate_leaves_the_container_not_eligible(project: Path) -> None:
    # #13 is listed — natively under #5 — but its issue cannot be read, so the
    # membership step cannot answer, and the fold holds rather than dropping it.
    issues = {
        CONTAINER: _container(),
        10: _issue("CLOSED", "Feature: #5\n\n## What\n", ["type:task"]),
        13: _issue("CLOSED", _UI_LINKED_BODY, ["type:task"]),
    }
    _tracker(project, issues, native={CONTAINER: [13]}, unreadable=(13,))

    held = _fold(project)
    assert held.opened is False
    assert held.indeterminate is True
    assert "membership of candidate '13'" in held.reason
    assert "could not read issue #13" in held.stderr_tail
