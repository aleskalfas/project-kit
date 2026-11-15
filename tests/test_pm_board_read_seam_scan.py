"""No script outside the board read seam builds a read of the board ([pkit:ADR-096] point 6).

The seam, `_lib/board_fields` and `_lib/board_answer`, owns every read of a
Projects v2 board ([pkit:ADR-053] point 1): it decides what counts as the board's
answer, so a read built elsewhere would decide that for itself, which is how a
stored id comes to stand in for an answer. This scan is the guard the write
constructor has (ADR-031 point 4, `test_pm_substrate_write_seam`), on the read
side.

It reads each script of the capability as Python, and flags a string a script
builds that reads the board:

  * a GraphQL selection on the board, its cards or its fields: text with a
    selection's braces naming a `ProjectV2` type, `projectV2(` or `projectsV2`,
    a write (`mutation`) excepted, since the write seam builds those;
  * an issue's own list of cards, `projectItems`, in a GraphQL selection or a
    `gh issue view --json` field list alike, since that list names no board;
  * a `gh project` read verb in a command list: `view`, `field-list`,
    `item-list` or `list`.

A docstring is prose, not a read, and is not scanned. The adds (`item-add`) and
the field writes stay outside, each in its own place (ADR-031 point 3).
"""

from __future__ import annotations

import ast
import re
from itertools import pairwise
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"
SEAM = (SCRIPTS / "_lib" / "board_fields.py", SCRIPTS / "_lib" / "board_answer.py")

#: A selection on the board, its cards or its fields, by the names GraphQL gives them.
_BOARD_SELECTION = re.compile(r"ProjectV2|projectV2\s*\(|projectsV2")
#: An issue's own list of cards.
_ISSUE_CARDS = re.compile(r"\bprojectItems\b")
#: The `gh project` verbs that read the board.
_READ_VERBS = frozenset({"view", "field-list", "item-list", "list"})


def _not_scanned(tree: ast.AST) -> set[int]:
    """The ids of the string nodes not scanned on their own: docstrings and bare
    string statements, which are prose, and each piece of an f-string, which is
    scanned whole with the string it builds."""
    found: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant | ast.JoinedStr):
            found.add(id(node.value))
        if isinstance(node, ast.JoinedStr):
            found.update(id(value) for value in node.values)
    return found


def _text(node: ast.AST) -> str | None:
    """The literal text a string node builds, each placeholder an empty `{}`."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            else:
                parts.append("{}")
        return "".join(parts)
    return None


def _reads_the_board(text: str) -> bool:
    """Whether ``text`` is a GraphQL read of the board or an issue's cards."""
    if _ISSUE_CARDS.search(text):
        return True
    if text.lstrip().startswith("mutation"):
        return False
    return "{" in text and bool(_BOARD_SELECTION.search(text))


def _project_read(node: ast.List | ast.Tuple) -> bool:
    """Whether a command list runs a `gh project` read verb."""
    words = [
        element.value
        for element in node.elts
        if isinstance(element, ast.Constant) and isinstance(element.value, str)
    ]
    return any(
        word == "project" and following in _READ_VERBS for word, following in pairwise(words)
    )


def violations(path: Path) -> list[str]:
    """Each place ``path`` builds a read of the board, as `file:line: what`."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    skipped = _not_scanned(tree)
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.List | ast.Tuple) and _project_read(node):
            found.append(f"{path.name}:{node.lineno}: a `gh project` read")
            continue
        if id(node) in skipped:
            continue
        text = _text(node)
        if text is not None and _reads_the_board(text):
            line = getattr(node, "lineno", 0)
            found.append(f"{path.name}:{line}: a read of the board: {text[:80]!r}")
    return found


def _scripts() -> list[Path]:
    return sorted(path for path in SCRIPTS.rglob("*.py") if path not in SEAM)


def test_no_script_outside_the_seam_builds_a_read_of_the_board() -> None:
    found = [line for path in _scripts() for line in violations(path)]
    assert not found, (
        "a read of the board built outside the board read seam ([pkit:ADR-096] "
        "point 6); read the board through `_lib/board_fields` instead:\n  " + "\n  ".join(found)
    )


def test_the_seam_itself_builds_the_reads() -> None:
    """The seam is excluded by name; this pins that the reads live there, so an
    empty scan means none left it, not that the scan sees nothing."""
    assert all(violations(path) for path in SEAM)


@pytest.mark.parametrize(
    ("source", "flagged"),
    [
        pytest.param(
            'Q = "query($p: ID!) { node(id: $p) { ... on ProjectV2 { items { nodes { id } } } } }"\n',  # noqa: E501
            True,
            id="a-graphql-walk",
        ),
        pytest.param(
            'Q = f"query {{ user(login: {who}) {{ projectV2(number: 1) {{ id }} }} }}"\n',
            True,
            id="an-f-string-read",
        ),
        pytest.param('FIELDS = "title,body,projectItems"\n', True, id="an-issues-own-cards"),
        pytest.param(
            'cmd = ["gh", "project", "view", "7", "--format", "json"]\n', True, id="a-cli-read"
        ),
        pytest.param('cmd = ("gh", "project", "field-list", "7")\n', True, id="a-cli-field-list"),
        pytest.param(
            'M = "mutation { updateProjectV2Field(input: {}) { projectV2Field { id } } }"\n',
            False,
            id="a-write",
        ),
        pytest.param(
            'cmd = ["gh", "project", "item-add", "7", "--url", url]\n', False, id="an-add"
        ),
        pytest.param('KIND = "ProjectV2SingleSelectField"\n', False, id="a-type-name"),
        pytest.param(
            'def f():\n    """Reads `projectItems` and ProjectV2 { items }."""\n',
            False,
            id="a-docstring",
        ),
    ],
)
def test_the_scan_tells_a_read_of_the_board(tmp_path: Path, source: str, flagged: bool) -> None:
    path = tmp_path / "script.py"
    path.write_text(source, encoding="utf-8")
    assert bool(violations(path)) is flagged
