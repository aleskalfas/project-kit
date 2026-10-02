"""One reader of a first line, one comparison of a native parent (#1281).

An issue's parent is read one way: `_lib/body_parent_ref` reads the first line
(`read_first_line` for one issue's parent, `named_issue` for a corpus scan), and
the containment seam holds the native parent to it (`containment.resolve_parent`,
or `compare_parents` for a native parent a caller derived itself). Two copies of
the reading drifted before — the cascades read a line one way, the close gate
and show-tree another — so this guard makes the single reading structural:

- no script outside `body_parent_ref` carries a regex that matches a parent-ref
  line (`<Label>: #<N>`, `Milestone: [#<N>](…)`). `validate-issue` and
  `edit-issue` are allow-listed: they check a body's shape (label-agnostic,
  tail-strict) before it is written, a form check rather than a reading of the
  parent — on the first line `body_parent_ref.first_line` gives them, so which
  line is checked is the reader's. So is `_lib/milestone`, which counts a
  body's milestone refs toward a Milestone's children: the Milestone axis, not
  an issue's parent.
- no script outside the containment seam compares a native parent itself
  (`NativeParent.is_issue`, or a raw `parent_issue_url`). `link-parent` and
  `set-field` are allow-listed: they write the native link, and check where the
  child sits natively before they do (DEC-026's value-equality) — a write's
  idempotency, not a reading of the parent.

Each failure says what to call instead. An allow-listed script is held to the
number of hits it carries today, so a second reading or comparison added to it
fails the guard too, rather than riding in under the first one's exemption.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterator
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / ".pkit" / "capabilities" / "project-management" / "scripts"

READER = "_lib/body_parent_ref.py"
SEAM = "_lib/containment.py"

# Scripts that check a body's first-line shape before it is written, and the
# Milestone axis's reader, which counts a body's `Milestone: [#<N>](…)` refs on
# any line toward a Milestone's children — a milestone's membership, not an
# issue's parent. Each with the number of parent-ref patterns it carries: the
# two form checks' three forms (milestone link, old milestone, `<Label>: #<N>`),
# and the Milestone axis's one link form.
PATTERN_ALLOWED = {"validate-issue.py": 3, "edit-issue.py": 3, "_lib/milestone.py": 1}
# Scripts that write the native link and check where the child sits first, each
# with the one comparison it makes.
NATIVE_COMPARE_ALLOWED = {"link-parent.py": 1, "set-field.py": 1}

# A regex source that matches a parent-ref line: a colon, optional or required
# whitespace, `#` (or a milestone link's `[#`) and a captured or matched number.
# A placeholder check (`EPIC: #` with no number) does not match.
_PARENT_REF_REGEX = re.compile(r":\\s[*+](\\\[)?#\(?(\?P<\w+>)?\\d")

_READ_INSTEAD = (
    "read the first line through `_lib.body_parent_ref` instead — `read_first_line` for "
    "one issue's parent, `named_issue` for a corpus scan — so every reader names the same "
    "issue"
)
_COMPARE_INSTEAD = (
    "resolve the parent through `containment.resolve_parent` instead (or "
    "`containment.compare_parents` with a native parent derived from child sets already "
    "read), which holds the native parent to the first line once for every consumer"
)


def _scripts() -> list[Path]:
    return sorted(SCRIPTS.rglob("*.py"))


def _name(path: Path) -> str:
    return path.relative_to(SCRIPTS).as_posix()


def _string_constants(tree: ast.AST) -> Iterator[tuple[ast.Constant, str]]:
    """Each string literal in ``tree``, with its text."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            yield node, node.value


def _parent_ref_patterns(path: Path) -> list[str]:
    """`file:line: pattern` for each regex source in ``path`` that matches a
    parent-ref line. Docstrings and comments name the forms in prose
    (`` `EPIC: #<N>` ``), which this does not match."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return [
        f"{_name(path)}:{node.lineno}: {text!r}"
        for node, text in _string_constants(tree)
        if _PARENT_REF_REGEX.search(text)
    ]


def _native_comparisons(path: Path) -> list[str]:
    """`file:line` for each comparison of a native parent in ``path``: a call
    of `.is_issue(...)`, or a read of `parent_issue_url`."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: list[str] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "is_issue"
        ):
            found.append(f"{_name(path)}:{node.lineno}: .is_issue(...)")
    for node, text in _string_constants(tree):
        if "parent_issue_url" in text and not _is_docstring(tree, node):
            found.append(f"{_name(path)}:{node.lineno}: parent_issue_url")
    return found


def _is_docstring(tree: ast.AST, constant: ast.Constant) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = node.body
            if (
                body
                and isinstance(body[0], ast.Expr)
                and body[0].value is constant  # the node itself, not an equal string
            ):
                return True
    return False


def test_the_detector_knows_a_parent_ref_regex_from_a_placeholder_check() -> None:
    for source in (
        r"^([A-Za-z]+):\s+#(\d+)",
        r"^[A-Za-z]+:\s+#\d+\s*$",
        r"^(?P<label>[A-Za-z]+):\s*#(?P<number>\d+)",
        r"^Milestone:\s+\[#(\d+)\]\(\.\./milestone/\1\)\s*$",
    ):
        assert _PARENT_REF_REGEX.search(source), source
    for source in (r"^[A-Za-z]+:\s+#\s*$", "`EPIC: #<N>`", r"\b(?:closes|fixes)\s+#(\d+)"):
        assert not _PARENT_REF_REGEX.search(source), source


def test_no_script_but_the_reader_matches_a_parent_ref_line_itself() -> None:
    offenders = [
        hit
        for path in _scripts()
        if _name(path) != READER and _name(path) not in PATTERN_ALLOWED
        for hit in _parent_ref_patterns(path)
    ]
    assert not offenders, (
        "a script matches a first-line parent-ref itself:\n  "
        + "\n  ".join(offenders)
        + f"\n{_READ_INSTEAD}."
    )


def test_the_reader_and_the_allow_listed_form_checks_do_match_one() -> None:
    """The guard sees what it guards: the reader and each allow-listed file still
    carry a parent-ref regex, so an allow-list entry that no longer earns its
    place is noticed."""
    for name in (READER, *sorted(PATTERN_ALLOWED)):
        assert _parent_ref_patterns(SCRIPTS / name), name


@pytest.mark.parametrize("name", sorted(PATTERN_ALLOWED))
def test_an_allow_listed_form_check_carries_no_second_reading(name: str) -> None:
    """An allow-listed script is exempt for the form check it makes, not for any
    parent-ref pattern: one added beside it is a second reading, and fails."""
    hits = _parent_ref_patterns(SCRIPTS / name)
    assert len(hits) == PATTERN_ALLOWED[name], (
        f"{name} carries {len(hits)} parent-ref pattern(s), allow-listed for "
        f"{PATTERN_ALLOWED[name]}:\n  " + "\n  ".join(hits) + f"\n{_READ_INSTEAD}."
    )


def test_no_script_but_the_seam_compares_a_native_parent_itself() -> None:
    offenders = [
        hit
        for path in _scripts()
        if _name(path) != SEAM and _name(path) not in NATIVE_COMPARE_ALLOWED
        for hit in _native_comparisons(path)
    ]
    assert not offenders, (
        "a script compares a native parent itself:\n  "
        + "\n  ".join(offenders)
        + f"\n{_COMPARE_INSTEAD}."
    )


def test_the_seam_and_the_allow_listed_linkers_do_compare_one() -> None:
    for name in (SEAM, *sorted(NATIVE_COMPARE_ALLOWED)):
        assert _native_comparisons(SCRIPTS / name), name


@pytest.mark.parametrize("name", sorted(NATIVE_COMPARE_ALLOWED))
def test_an_allow_listed_linker_makes_no_second_comparison(name: str) -> None:
    """A linker is exempt for the one idempotency check it makes before it
    writes; a second comparison of a native parent beside it fails."""
    hits = _native_comparisons(SCRIPTS / name)
    assert len(hits) == NATIVE_COMPARE_ALLOWED[name], (
        f"{name} compares a native parent {len(hits)} time(s), allow-listed for "
        f"{NATIVE_COMPARE_ALLOWED[name]}:\n  " + "\n  ".join(hits) + f"\n{_COMPARE_INSTEAD}."
    )
