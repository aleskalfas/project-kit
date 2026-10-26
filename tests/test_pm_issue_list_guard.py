"""Every listing of issues in project-management runs through one read (#2139).

DEC-058 point 3 puts the exclusion of state issues in the capability's one read
of its issues, never in each consumer. `_lib/issue_list.list_issues` is that
read, so no other script may build the `gh issue list` command itself: a listing
built beside it would hand state issues to a check of work. The guard reads each
script's syntax tree for a command list that holds `"issue"` and then `"list"`.
The failure names what to call instead.
"""

from __future__ import annotations

import ast
import itertools
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"

READ = "_lib/issue_list.py"

_INSTEAD = (
    "list issues through `_lib.issue_list.list_issues` instead, the one read that leaves "
    "state issues out (DEC-058 point 3)"
)


def _name(path: Path) -> str:
    return path.relative_to(SCRIPTS).as_posix()


def _issue_listings(source: str) -> list[int]:
    """The line of each list or tuple in `source` that holds `"issue"` then `"list"`."""
    lines: list[int] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, (ast.List, ast.Tuple)):
            continue
        words = [elt.value if isinstance(elt, ast.Constant) else None for elt in node.elts]
        if ("issue", "list") in itertools.pairwise(words):
            lines.append(node.lineno)
    return lines


def test_the_detector_finds_a_listing_and_nothing_else() -> None:
    assert _issue_listings('args = ["gh", "issue", "list", "--json", "number"]') == [1]
    assert _issue_listings('run(("gh", "issue", "list"))') == [1]
    for source in (
        'args = ["gh", "issue", "view", "7"]',
        'args = ["gh", "pr", "list"]',
        'args = ["gh", "label", "list"]',
        'note = "gh issue list failed"',
    ):
        assert _issue_listings(source) == [], source


def test_no_script_but_the_one_read_lists_issues_itself() -> None:
    offenders = [
        f"{_name(path)}:{line}"
        for path in sorted(SCRIPTS.rglob("*.py"))
        if _name(path) != READ
        for line in _issue_listings(path.read_text(encoding="utf-8"))
    ]
    assert not offenders, (
        "a script builds `gh issue list` itself:\n  " + "\n  ".join(offenders) + f"\n{_INSTEAD}."
    )


def test_the_one_read_does_build_the_listing() -> None:
    """The guard sees what it guards: the read itself still builds the command."""
    assert _issue_listings((SCRIPTS / READ).read_text(encoding="utf-8"))
