"""The parent an issue body names on its first line — one reading for every caller.

Every issue body opens with a parent-ref naming its immediate parent, in one of
the forms its structural type allows ([project-management:DEC-005-linking-and-containment];
`schemas/issue-types.yaml`'s per-type `parent_ref_form`): `<Label>: #<N>` for an
issue parent (EPIC, Feature, Umbrella), or `Milestone: [#<N>](../milestone/<N>)`
for a milestone parent.

`create-issue` acts on that line twice: it checks that a prepared body's first
line is an allowed form, and, when no `--parent` is given, links the new issue
natively under the parent the line names. `link-parent` links issues that
already exist from the same line. All of them read it here, so the line that
passes the filing check is exactly the line that gets linked, at filing or in a
later repair — one reading, not several that could drift.

The *first line* is the first non-blank line after a leading DEC-013
`Integration:` marker (which sits above the parent-ref) — the reading
create-issue's first-line check has always used. Only the forms the issue's own
type permits are recognised, so a line naming a parent the type may not have
(an EPIC under a Feature) is not a parent-ref for that issue.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from _lib import lifecycle_inference as _infer

# The label every milestone parent-ref carries. A milestone is not an issue:
# it scopes issues through its own native Milestone field, so a milestone ref
# never becomes a sub-issue link.
MILESTONE_LABEL = "Milestone"

# How a `parent_ref_form` option spells a milestone parent (the link form), and
# the concrete first line that option accepts. The number is back-referenced so
# a link whose text and target disagree is not accepted.
_MILESTONE_OPTION_MARKER = "../milestone/"
_MILESTONE_LINE = re.compile(
    rf"^(?P<label>{MILESTONE_LABEL}):\s+\[#(?P<number>\d+)\]"
    r"\(\.\./milestone/(?P=number)\)\s*$"
)
# The deprecated plain form (`Milestone: #<N>`) validate-issue still accepts
# with a warning. Read so a milestone move can bring it along; never written.
_OLD_MILESTONE_LINE = re.compile(rf"^{MILESTONE_LABEL}:\s+#(?P<number>\d+)\s*$")

# How a `parent_ref_form` option spells an issue parent: `<Label>: #<N>`.
_ISSUE_OPTION = re.compile(r"^([A-Za-z]+):\s*#<N>\s*$")


@dataclass(frozen=True)
class ParentRef:
    """A parsed first-line parent-ref.

    ``label`` is the ref's label as written (``EPIC``, ``Feature``,
    ``Umbrella``, ``Milestone``); ``number`` is the issue number, or the
    milestone number for a milestone ref; ``milestone`` says which.
    """

    label: str
    number: int
    milestone: bool

    @property
    def issue_number(self) -> int | None:
        """The parent issue to link under, or ``None`` for a milestone parent."""
        return None if self.milestone else self.number


def _options(parent_ref_form: str) -> list[tuple[bool, re.Pattern[str]]]:
    """Each `` or ``-separated option of a form as ``(is_milestone, matcher)``."""
    options: list[tuple[bool, re.Pattern[str]]] = []
    for raw in str(parent_ref_form).split(" or "):
        option = raw.strip()
        if not option:
            continue
        if _MILESTONE_OPTION_MARKER in option:
            options.append((True, _MILESTONE_LINE))
            continue
        m = _ISSUE_OPTION.match(option)
        if m:
            label = re.escape(m.group(1))
            options.append(
                (False, re.compile(rf"^(?P<label>{label}):\s+#(?P<number>\d+)\s*$"))
            )
    return options


def form_matchers(parent_ref_form: str) -> list[re.Pattern[str]]:
    """Compile a type's ``parent_ref_form`` into per-option first-line matchers.

    Each option becomes a regex matching a concrete first line: ``<Label>: #<N>``
    matches ``^<Label>:\\s+#\\d+\\s*$``, and the milestone link form matches its
    back-referenced link. The option set is the same one validate-issue accepts.
    Every matcher carries ``label`` and ``number`` groups.
    """
    return [matcher for _, matcher in _options(parent_ref_form)]


def first_line(body: str) -> str:
    """The body's parent-ref line as written: its first non-blank line after a
    leading DEC-013 ``Integration:`` marker, stripped. Empty for an empty body."""
    return _infer.strip_integration_marker(body or "").lstrip().split("\n", 1)[0].strip()


def parse_first_line(body: str, parent_ref_form: str) -> ParentRef | None:
    """The parent-ref on the body's first line, read against the type's forms.

    ``None`` when the first line is not one of the forms ``parent_ref_form``
    allows — including a line naming a parent the type may not have.
    """
    line = first_line(body)
    for is_milestone, matcher in _options(parent_ref_form):
        m = matcher.match(line)
        if m:
            return ParentRef(
                label=m.group("label"),
                number=int(m.group("number")),
                milestone=is_milestone,
            )
    return None


def milestone_line(number: int) -> str:
    """The milestone parent-ref line for milestone ``number`` (the link form)."""
    return f"{MILESTONE_LABEL}: [#{number}](../milestone/{number})"


def first_line_milestone(body: str) -> int | None:
    """The milestone the body's first line names as its parent, or ``None``.

    Reads the link form and the deprecated plain ``Milestone: #<N>`` form alike,
    whatever the issue's type — the question is what the line says, not whether
    the type may say it.
    """
    line = first_line(body)
    m = _MILESTONE_LINE.match(line) or _OLD_MILESTONE_LINE.match(line)
    return int(m.group("number")) if m else None


def set_first_line_milestone(body: str, number: int | None) -> str:
    """Point a milestone first line at milestone ``number``, or remove it.

    Keeps the textual parent-ref in step with the native Milestone field when an
    issue moves between milestones (#1049): a line left naming the old milestone
    would still count the issue among that milestone's children. Only a first
    line that already names a milestone is touched; any other body is returned
    unchanged. ``None`` removes the line together with the blank line after it.
    """
    if first_line_milestone(body) is None:
        return body
    lines = body.split("\n")
    index = _first_line_index(lines)
    if index is None:  # pragma: no cover - first_line_milestone found one
        return body
    if number is not None:
        lines[index] = milestone_line(number)
        return "\n".join(lines)
    del lines[index]
    if index < len(lines) and not lines[index].strip():
        del lines[index]
    return "\n".join(lines)


def _first_line_index(lines: list[str]) -> int | None:
    """Where :func:`first_line` is in ``lines``: the first non-blank line, past
    a leading DEC-013 ``Integration:`` marker."""
    marker_skipped = False
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if not marker_skipped and _infer.INTEGRATION_MARKER_RE.match(stripped):
            marker_skipped = True
            continue
        return index
    return None
