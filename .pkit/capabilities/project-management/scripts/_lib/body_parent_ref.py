"""The parent an issue body names on its first line — one reading for every caller.

Every issue body opens with a parent-ref naming its immediate parent, in one of
the forms its structural type allows ([project-management:DEC-005-linking-and-containment];
`schemas/issue-types.yaml`'s per-type `parent_ref_form`): `<Label>: #<N>` for an
issue parent (EPIC, Feature, Umbrella), or `Milestone: [#<N>](../milestone/<N>)`
for a milestone parent.

`create-issue` acts on that line twice: it checks that a prepared body's first
line is an allowed form, and, when no `--parent` is given, links the new issue
natively under the parent the line names. `link-parent` links issues that
already exist from the same line. Which parent an issue has is answered by the
containment seam (`containment.resolve_parent`), which holds the issue's native
parent to the line read here (:func:`read_first_line`) — and the textual side of
a parent's child set (`containment.resolve_children`) reads it here too
(:func:`named_issue`). All of them read it here, so the line that passes the
filing check is exactly the line that gets linked, at filing or in a later
repair, and the issue a line names is the same for every reader — one reading,
not several that could drift.

The *first line* is the first non-blank line after a leading DEC-013
`Integration:` marker (which sits above the parent-ref) — the reading
create-issue's first-line check has always used. A line names an issue parent
when it reads `<Label>: #<N>` loosely — any label but `Milestone`, any spacing
after the colon, anything after the number. Whether it does so in a form the
issue's own type allows is a second fact, told apart by :func:`read_first_line`:
a line naming a parent in a form the type does not offer (`Epic: #5`,
`Feature: #12 — auth`) still names that parent, and is reported as
non-conforming. A milestone ref, in either form, names no issue.

The line writer :func:`issue_parent_line` writes the line `create-issue` and
`set-field --parent` put on a body, labelled with the parent's own type.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

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

# Any `<Label>: #<N>` first line, whatever the label — the form an issue whose
# type, and so whose allowed forms, cannot be told is held to
# (:func:`read_first_line`).
_ANY_ISSUE_LINE = re.compile(r"^(?P<label>[A-Za-z]+):\s+#(?P<number>\d+)")

# A first line that names an issue, matched loosely — any word, any spacing after
# the colon, anything after the number — the reading every form is a narrowing
# of, so wherever a form names an issue this names the same one
# (:func:`named_issue`). The `Milestone` label is excluded by the reader: its
# number is a milestone's, never an issue's.
_NAMES_AN_ISSUE = re.compile(r"^(?P<label>[A-Za-z]+):\s*#(?P<number>\d+)")

# A line that is a parent-ref and nothing else: a label, a colon, `#<N>` and at
# most trailing whitespace (:func:`is_only_a_parent_ref`).
_ONLY_AN_ISSUE_REF = re.compile(r"^[A-Za-z]+:\s*#\d+\s*$")


class LineForm(Enum):
    """How a body's first line names a parent (:func:`read_first_line`).

    CONFORMING      — an issue parent, in a form the issue's type allows.
    NON_CONFORMING  — an issue parent, in a form the type does not allow
                      (`Epic: #5`, `Feature: #12 — auth`); it names the parent
                      all the same.
    MILESTONE       — a milestone parent, in either form; names no issue.
    NONE            — no parent at all.
    """

    CONFORMING = "conforming"
    NON_CONFORMING = "non-conforming"
    MILESTONE = "milestone"
    NONE = "none"


@dataclass(frozen=True)
class FirstLine:
    """A body's first line, classified (:func:`read_first_line`).

    ``line`` is the line as written; ``number`` the issue it names, or the
    milestone for a milestone line, ``None`` for no parent; ``note`` — for a
    non-conforming line only — says so, quoting the line and the forms the type
    allows, for the caller to put after the issue's number. ``issue_form`` says
    whether the issue's type has a form that names an issue at all: False for a
    type whose only parent-ref names a milestone (an EPIC, whose container is a
    milestone), True where the type cannot be told.
    """

    form: LineForm
    line: str
    number: int | None = None
    note: str | None = None
    issue_form: bool = True

    @property
    def issue(self) -> int | None:
        """The parent issue the line names, in any form; ``None`` for a
        milestone line or no parent."""
        named = self.form in (LineForm.CONFORMING, LineForm.NON_CONFORMING)
        return self.number if named else None


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
            options.append((False, re.compile(rf"^(?P<label>{label}):\s+#(?P<number>\d+)\s*$")))
    return options


def form_allows_milestone(parent_ref_form: str) -> bool:
    """Whether a type's ``parent_ref_form`` offers a milestone parent-ref."""
    return any(is_milestone for is_milestone, _ in _options(parent_ref_form))


def form_names_an_issue(parent_ref_form: str) -> bool:
    """Whether a type's ``parent_ref_form`` offers a parent-ref naming an issue —
    False for a type whose container is a milestone alone (an EPIC)."""
    return bool(_issue_option_labels(parent_ref_form))


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


def named_issue(body: str) -> int | None:
    """The issue a body's first line names as its parent, whatever the issue's
    type and whatever the line's form — ``None`` for a milestone ref, in either
    form, and for a line that names no issue.

    The reading for a corpus scan, where each body's type is not to hand: the
    textual side of a parent's child set (`containment.resolve_children`) and a
    tree's candidate parents. Wherever :func:`read_first_line` finds an issue,
    conforming or not, this finds the same one, so a child set and a parent
    resolution never disagree on which issue a line names.
    """
    m = _NAMES_AN_ISSUE.match(first_line(body))
    if m is None or m.group("label") == MILESTONE_LABEL:
        return None
    return int(m.group("number"))


def read_first_line(body: str, structural_type: str | None, issue_types: dict) -> FirstLine:
    """The body's first line, classified — the one reading of what it says
    about the issue's parent.

    A milestone ref, in either form, is ``MILESTONE``: a milestone is not an
    issue, so an EPIC under one has no parent issue. A line that names no issue
    (:func:`named_issue`) is ``NONE``. A line that does is ``CONFORMING`` where
    it is a form the issue's type allows (:func:`parse_first_line`) and
    ``NON_CONFORMING`` otherwise — ``Related: #45``, ``Epic: #5``, an EPIC's
    ``Feature: #12`` — carrying a note that quotes the line and the forms. Where
    the type cannot be told — a brownfield issue with no ``[Type]`` prefix and no
    ``type:*`` label, or a type ``issue_types`` declares no ``parent_ref_form``
    for — any ``<Label>: #<N>`` line conforms, so an untyped tree is walked as it
    always was, and only a line outside that shape (``Epic:#5``) is noted. Each
    reading says, too, whether the type has a form naming an issue at all
    (``FirstLine.issue_form``): an EPIC's has none.
    """
    line = first_line(body)
    form = _parent_ref_form(structural_type, issue_types)
    issue_form = form is None or bool(_issue_option_labels(form))
    milestone = first_line_milestone(body)
    if milestone is not None:
        return FirstLine(LineForm.MILESTONE, line, milestone, issue_form=issue_form)
    number = named_issue(body)
    if number is None:
        return FirstLine(LineForm.NONE, line, issue_form=issue_form)
    if form is not None:
        ref = parse_first_line(body, form)
        if ref is not None and not ref.milestone:
            return FirstLine(LineForm.CONFORMING, line, number, issue_form=issue_form)
        note = (
            f"first line `{line}` is not a parent-ref a {structural_type} may have: {form.strip()}"
        )
        return FirstLine(LineForm.NON_CONFORMING, line, number, note, issue_form)
    if _ANY_ISSUE_LINE.match(line):
        return FirstLine(LineForm.CONFORMING, line, number)
    note = f"first line `{line}` is not in the parent-ref form `<Label>: #<N>`"
    return FirstLine(LineForm.NON_CONFORMING, line, number, note)


def is_only_a_parent_ref(line: str) -> bool:
    """Whether ``line`` is a parent-ref and nothing else: ``<Label>: #<N>`` (any
    spacing after the colon) or a milestone ref in either form, with nothing
    after it but whitespace.

    A line that names a parent and says more — ``Feature: #12 — auth``, or a
    sentence that happens to open ``Note: #45 was closed…`` — is not: every reader
    takes the issue it names (:func:`named_issue`), but the line carries words a
    writer of the parent-ref has no business removing.
    """
    stripped = line.strip()
    return bool(
        _ONLY_AN_ISSUE_REF.match(stripped)
        or _MILESTONE_LINE.match(stripped)
        or _OLD_MILESTONE_LINE.match(stripped)
    )


def parent_issue(body: str, structural_type: str | None, issue_types: dict) -> int | None:
    """The parent issue a body's first line names in a form the issue's type
    allows, or ``None`` — :func:`read_first_line` narrowed to a conforming line.

    So ``Related: #45`` names no parent for a typed issue, and neither does a
    milestone ref, while an untyped issue's ``<Label>: #<N>`` line does.
    """
    read = read_first_line(body, structural_type, issue_types)
    return read.number if read.form is LineForm.CONFORMING else None


def _parent_ref_form(structural_type: str | None, issue_types: dict) -> str | None:
    """The `parent_ref_form` ``issue_types`` declares for the type, or ``None``."""
    types = issue_types.get("types") if isinstance(issue_types, dict) else None
    entry = types.get(structural_type) if isinstance(types, dict) and structural_type else None
    form = entry.get("parent_ref_form") if isinstance(entry, dict) else None
    return form if isinstance(form, str) and form.strip() else None


def milestone_line(number: int) -> str:
    """The milestone parent-ref line for milestone ``number`` (the link form)."""
    return f"{MILESTONE_LABEL}: [#{number}](../milestone/{number})"


@dataclass(frozen=True)
class ParentLine:
    """The first line :func:`issue_parent_line` writes for a parent, and what to
    warn of: ``line`` is empty when the type has no form to write; ``warning``
    says why the line does not carry the parent's own label — or, where the
    line names a milestone, that it names no issue — for the caller to print
    after ``[warn]``."""

    line: str
    warning: str | None = None


def type_label(issue_types: dict, structural_type: str) -> str | None:
    """How a parent-ref labels a parent of ``structural_type``: the type's own
    rendered ``title_prefix`` (epic → ``EPIC``, feature → ``Feature``, umbrella →
    ``Umbrella``) — the token the forms in ``issue-types.yaml`` use. ``None``
    when ``issue_types`` does not declare the type."""
    types = issue_types.get("types") if isinstance(issue_types, dict) else None
    entry = types.get(structural_type) if isinstance(types, dict) else None
    if not isinstance(entry, dict):
        return None
    rendered = str(entry.get("title_prefix", ""))
    if entry.get("title_case", "title") == "upper":
        rendered = rendered.upper()
    return rendered or None


def issue_parent_line(
    parent_ref_form: str, parent_number: int, parent_label: str | None = None
) -> ParentLine:
    """The first line a writer puts on a body given parent ``parent_number`` —
    the one writer `create-issue` and `set-field --parent` share.

    The label is ``parent_label`` — the parent's own label (:func:`type_label`)
    — when it is one of the forms ``parent_ref_form`` allows, so a Task filed
    under an Umbrella opens `Umbrella: #<N>`. Where the parent's type is not
    known (``parent_label`` is ``None``) the line takes the form's first option.
    It takes the first option, too, where the parent's label is not among the
    forms, and says so in ``warning``: DEC-005 requires a parent the type may
    not sit under to be refused, and until that refusal is built a writer
    names the parent this way and warns.

    Where the first option names a milestone the number is a milestone's: a
    type whose only parent-ref names a milestone (an EPIC) sits under a
    milestone, never under an issue, so its line `Milestone: #<N>` names
    milestone N and no issue, and ``warning`` says so whatever the parent's
    label. A form with no option to write from gives an empty line.
    """
    form = str(parent_ref_form or "").strip()
    first = form.split(" or ", 1)[0].split(":", 1)[0].strip()
    if not first:
        return ParentLine("")
    issue_labels = _issue_option_labels(form)
    if parent_label is not None and parent_label in issue_labels:
        return ParentLine(f"{parent_label}: #{parent_number}")
    line = f"{first}: #{parent_number}"
    if first == MILESTONE_LABEL:
        if not issue_labels:
            why = f"this type's container is a milestone, never an issue ({form})"
        elif parent_label is not None:
            why = f"`{parent_label}: #<N>` is not a parent-ref this type may have ({form})"
        else:
            why = f"the parent's type is not known, and the first form names a milestone ({form})"
        return ParentLine(
            line,
            f"{why}, so the first line `{line}` names milestone {parent_number}, "
            f"not issue #{parent_number}",
        )
    if parent_label is None:
        return ParentLine(line)
    return ParentLine(
        line,
        f"`{parent_label}: #<N>` is not a parent-ref this type may have "
        f"({form}), so the first line names #{parent_number} as `{line}`",
    )


def _issue_option_labels(parent_ref_form: str) -> list[str]:
    """The labels of the issue-parent options of a form (`EPIC`, `Umbrella`, …)."""
    labels: list[str] = []
    for raw in str(parent_ref_form).split(" or "):
        m = _ISSUE_OPTION.match(raw.strip())
        if m and _MILESTONE_OPTION_MARKER not in raw:
            labels.append(m.group(1))
    return labels


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
