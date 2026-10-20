"""A project's own structures: what a project changes of each kind's shipped structure.

The capability ships each kind's structure (`_lib/structure.py`), and a project
changes it in a file of its own in the capability's project tier,
`project/structures.yaml`, keyed by kind (DEC-001 point 1). Its shape is its
companion's, `schemas/structures.schema.json`. This module reads the file
against the shipped structure, and gives the structure a body is checked
against, and the stamp writes:

- **A relabel** gives a shipped part a new label, hint or example, by the
  part's id. The part keeps its id, its place, its form and whether it is
  required, and its shipped label stays one of its `aliases`, which a body
  written before the relabel may carry. A label is the text of a label, or of a
  heading the kind fixes. A hint and an example are a part's a writer fills.
- **A field's hint** replaces a shipped front-matter field's hint and example,
  by the field's name. The stamp writes the project's hint as the field's
  placeholder.
- Neither tightens anything, so neither names a rule (`relabelled`).
- **A tightening** is a group that names the project rule that asks for it,
  of an artefact kind. A revalidation record is a held document, which no rule
  binds on, so the record's kind takes none, and its schema refuses one.
  It adds parts, each placed `after` an element. It makes a shipped optional
  part required (`require`), or closes the kind's list of labels (`closed`).
  An addition is optional unless it sets `required: true`. Which groups apply
  to a body is the caller's (`tightened`): the check's, by where the group's
  rule binds, and the stamp's. The labels of the other groups whose rule
  stands still end the part before them (`Kind.delimiting`).
- **Where an addition goes.** Right after the element it names. The additions
  naming one element keep the order of the file, each followed by those that
  name it, so an addition comes before any shipped element that follows the
  element it names. Where a group does not apply, its additions are left out,
  and those naming them keep the place they would have had. An addition after a
  part of a repeated section, a domain-model view's section for each concept,
  goes in each of its sections (DEC-004 point 2).

What the file is refused for, each an error at its place in the file, the
project being the one to mend it (COR-055 point 1):

- a shape its companion refuses, which leaves no key to drop, loosen or
  reorder a shipped part or to invent a form, and no label holding `*`
- a tightening of the record's kind, which the companion refuses too, saying
  why (`RECORD_TIGHTENING`)
- a kind the capability does not ship, since a new kind needs a decision of
  its own (DEC-001 point 11)
- a part, a field or an element `after` names that the kind does not hold, or
  that it retired
- an id or a label two parts take, and a cycle of additions
- a part placed between an element and the opening that follows it, which
  would take the opening's lines
- a heading of any level but the one just below the kind's own first heading:
  a shallower one would end the artefact's or the entry's section, and a deeper
  one would read as the content of the part before it. A domain-model view
  takes no heading at all, which its companion refuses: its headings are its
  title and its concepts' sections (DEC-004 point 2)
- a label given to a part with no text, or a hint to a part no writer fills
- a hint or an example that would not stay one comment on one line

The file is read whole or not at all: while any of these stands, none of it is
applied, and the stamp refuses. Requiring a part the kind requires already
changes nothing, and is reported (`Own.notes`).
"""

from __future__ import annotations

import dataclasses
import itertools
from collections import defaultdict
from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ruamel.yaml.error import YAMLError

from _lib import markdown, render, schemas
from _lib.findings import ERROR, REPORT, Finding, at
from _lib.structure import (
    HEADING,
    LABEL,
    OPENING,
    RECORD,
    REPEATED,
    Element,
    Field,
    Kind,
    comparable,
    elements,
    section_elements,
)

#: The project's own structures, relative to the project root.
FILE = ".pkit/capabilities/software-analysis/project/structures.yaml"

#: Where a tightening of the record's kind would be, which the companion refuses.
RECORD_TIGHTENING = f"/kinds/{RECORD}/tighten"


@dataclass(frozen=True)
class Change:
    """What a relabel or a field's new hint gives: any of a label, a hint and an example."""

    label: str | None = None
    hint: str | None = None
    example: str | None = None


@dataclass(frozen=True)
class Addition:
    """A part a group adds, and the id of the element it comes right after."""

    element: Element
    after: str


@dataclass(frozen=True)
class Group:
    """One group of tightenings of a kind, the `index`th of its `tighten`, and the project
    rule that asks for it."""

    kind: str
    index: int
    rule: str
    additions: tuple[Addition, ...] = ()
    require: tuple[str, ...] = ()
    closed: bool = False

    @property
    def where(self) -> str:
        """The group's place in the file."""
        return at(FILE, f"/kinds/{self.kind}/tighten/{self.index}")


@dataclass(frozen=True)
class Own:
    """A project's own structures: each kind's relabels and fields' hints, and its groups
    of tightenings, in the file's order — or, with `problems`, none of them. `notes` are
    what the reading reports and never fails on, and `present` says whether the project
    has the file at all."""

    relabels: Mapping[str, Mapping[str, Change]] = dataclasses.field(default_factory=dict)
    fields: Mapping[str, Mapping[str, Change]] = dataclasses.field(default_factory=dict)
    groups: tuple[Group, ...] = ()
    problems: tuple[Finding, ...] = ()
    present: bool = False
    notes: tuple[Finding, ...] = ()

    def of(self, kind: str) -> tuple[Group, ...]:
        """The groups of tightenings of `kind`."""
        return tuple(group for group in self.groups if group.kind == kind)


def read(root: Path, kinds: Mapping[str, Kind]) -> Own:
    """The project's own structures at `root`, held to their companion and to the shipped
    `kinds`. No file changes nothing."""
    path = root / FILE
    if not path.is_file():
        return Own()
    try:
        data: Any = markdown.load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, YAMLError) as exc:
        return Own(problems=(Finding(ERROR, FILE, _unparsed(exc)),), present=True)
    errors = schemas.structures_errors(data)
    shaped = [
        Finding(
            ERROR,
            at(FILE, pointer),
            f"{message} — the file is held to "
            f"`schemas/structures.schema.json`, which has no key to drop, loosen or reorder "
            f"a shipped part, or to invent a form (DEC-001 point 1)",
        )
        for pointer, message in errors
        if not _under(pointer, RECORD_TIGHTENING)
    ]
    if any(_under(pointer, RECORD_TIGHTENING) for pointer, _message in errors):
        shaped.append(
            Finding(
                ERROR,
                at(FILE, RECORD_TIGHTENING),
                "a revalidation record's structure takes no tightening: a record is a held "
                "document, which no rule binds on, so the capability checks its structure "
                "itself, always, and a tightening of it could never bind. Relabel its parts "
                "if you need to, and remove `tighten` here; `schemas/structures.schema.json` "
                "refuses it until a rule set can reach a held document (DEC-001 point 1)",
            )
        )
    if shaped:
        return Own(problems=tuple(shaped), present=True)
    reading = _Reading(kinds)
    for name, entry in (data.get("kinds") or {}).items():
        reading.kind(str(name), entry)
    if reading.problems:
        return Own(problems=tuple(reading.problems), present=True)
    return Own(
        reading.relabels,
        reading.fields,
        tuple(reading.groups),
        present=True,
        notes=tuple(reading.notes),
    )


def _under(pointer: str, parent: str) -> bool:
    """Whether the JSON Pointer `pointer` is `parent`, or lies beneath it."""
    return pointer == parent or pointer.startswith(parent + "/")


def _unparsed(exc: BaseException) -> str:
    if isinstance(exc, YAMLError):
        return f"it is not YAML ({exc}) — fix it: none of it is applied until it reads"
    return f"it cannot be read ({exc}) — none of it is applied until it reads"


class _Reading:
    """The file's entries, held to the shipped kinds, as they are read."""

    def __init__(self, kinds: Mapping[str, Kind]) -> None:
        self.kinds = kinds
        self.relabels: dict[str, dict[str, Change]] = {}
        self.fields: dict[str, dict[str, Change]] = {}
        self.groups: list[Group] = []
        self.problems: list[Finding] = []
        self.notes: list[Finding] = []

    def problem(self, pointer: str, message: str) -> None:
        self.problems.append(Finding(ERROR, at(FILE, pointer), message))

    def kind(self, name: str, entry: Mapping[str, Any]) -> None:
        here = f"/kinds/{name}"
        kind = self.kinds.get(name)
        if kind is None:
            shipped = ", ".join(f"`{k}`" for k in self.kinds)
            self.problem(
                here,
                f"`{name}` is no kind the capability ships ({shipped}): a project changes a "
                f"shipped kind's structure, and a new kind needs a decision of its own "
                f"(DEC-001 points 1 and 11)",
            )
            return
        relabels = {
            str(i): Change(c.get("label"), c.get("hint"), c.get("example"))
            for i, c in (entry.get("relabel") or {}).items()
        }
        for element_id, change in relabels.items():
            self.relabel(kind, element_id, change)
        fields = {
            str(n): Change(None, c.get("hint"), c.get("example"))
            for n, c in (entry.get("front-matter") or {}).items()
        }
        for field_name, change in fields.items():
            self.field(kind, field_name, change)
        self.relabels[name] = relabels
        self.fields[name] = fields
        groups = [
            Group(
                kind=name,
                index=index,
                rule=str(group["rule"]),
                additions=tuple(
                    Addition(_added(item, str(group["rule"])), str(item["after"]))
                    for item in group.get("add") or ()
                ),
                require=tuple(str(i) for i in group.get("require") or ()),
                closed=group.get("closed") is True,
            )
            for index, group in enumerate(entry.get("tighten") or ())
        ]
        self.tightenings(kind, groups, relabels)
        self.groups += groups

    def relabel(self, kind: Kind, element_id: str, change: Change) -> None:
        here = f"/kinds/{kind.name}/relabel/{element_id}"
        element = next((e for e in elements(kind) if e.id == element_id), None)
        if element is None:
            self.problem(here, _unknown(kind, element_id, "relabels"))
            return
        if change.label is not None and element.text is None:
            self.problem(
                f"{here}/label",
                f"`{element_id}` has no text to relabel: a label, and a heading the kind fixes, "
                f"have one. Give it a hint or an example instead",
            )
        if (change.hint is not None or change.example is not None) and not element.filled:
            self.problem(
                here,
                f"`{element_id}` is a heading the stamp writes, which no writer fills, so it has "
                f"no hint or example to replace",
            )
        self.one_line(here, element_id, change)

    def field(self, kind: Kind, name: str, change: Change) -> None:
        here = f"/kinds/{kind.name}/front-matter/{name}"
        if not any(f.name == name for f in kind.fields):
            declared = ", ".join(f"`{f.name}`" for f in kind.fields) or "none"
            self.problem(
                here,
                f"`{name}` is no front-matter field the {kind.name} kind gives a hint (it gives "
                f"{declared}): a project replaces the hint of a shipped field, and adds none",
            )
            return
        self.one_line(here, name, change)

    def tightenings(
        self, kind: Kind, groups: Sequence[Group], relabels: Mapping[str, Change]
    ) -> None:
        shipped = {e.id: e for e in elements(kind)}
        runs = [
            kind.sections,
            *(section_elements(e) for e in kind.sections if e.type == REPEATED),
        ]
        opened = {
            before.id: after.id
            for run in runs
            for before, after in itertools.pairwise(run)
            if after.type == OPENING
        }
        top = min((e.level or 1 for e in kind.sections if e.type == HEADING), default=0)
        added: dict[str, tuple[Group, int]] = {}
        texts: dict[str, str] = {}
        for element in elements(kind):
            if element.text is None:
                continue
            relabel = relabels.get(element.id)
            text = relabel.label if relabel is not None and relabel.label else element.text
            other = texts.get(comparable(text))
            if other is not None:
                relabelled = element.id if relabel is not None and relabel.label else other
                kept = other if relabelled == element.id else element.id
                self.problem(
                    f"/kinds/{kind.name}/relabel/{relabelled}/label",
                    f"`{text}` is the text of `{kept}` already: two parts of one kind are told "
                    f"apart by their text",
                )
            texts.setdefault(comparable(text), element.id)
        for group in groups:
            for index, addition in enumerate(group.additions):
                here = f"/kinds/{kind.name}/tighten/{group.index}/add/{index}"
                element = addition.element
                if element.id in shipped or element.id in kind.retired or element.id in added:
                    taken = "retired" if element.id in kind.retired else "taken"
                    self.problem(
                        f"{here}/id",
                        f"`{element.id}` is an id the {kind.name} kind has {taken}: each part "
                        f"of a kind has an id of its own, and a shipped one is permanent "
                        f"(DEC-001 point 1)",
                    )
                    continue
                added[element.id] = (group, index)
                if element.type == HEADING and (element.level or 1) != top + 1:
                    self.problem(
                        f"{here}/level",
                        _level(kind.name, element.level or 1, top),
                    )
                text = comparable(element.text or "")
                if text in texts:
                    self.problem(
                        f"{here}/label",
                        f"`{element.text}` is the text of `{texts[text]}` already: two parts "
                        f"of one kind are told apart by their text",
                    )
                else:
                    texts[text] = element.id
                self.one_line(here, element.id, Change(None, element.hint, element.example))
            for index, element_id in enumerate(group.require):
                here = f"/kinds/{kind.name}/tighten/{group.index}/require/{index}"
                if element_id not in shipped:
                    also = (
                        " An addition is made required by its own `required: true`."
                        if any(a.element.id == element_id for g in groups for a in g.additions)
                        else ""
                    )
                    self.problem(here, _unknown(kind, element_id, "requires") + also)
                elif shipped[element_id].required:
                    self.notes.append(
                        Finding(
                            REPORT,
                            at(FILE, here),
                            f"`{element_id}` is required already, as the {kind.name} kind "
                            f"ships it, so requiring it changes nothing",
                        )
                    )
        for element_id, (group, index) in added.items():
            here = f"/kinds/{kind.name}/tighten/{group.index}/add/{index}/after"
            after = group.additions[index].after
            if after in kind.retired:
                self.problem(
                    here,
                    f"`{after}` is an element the {kind.name} kind retired: name an element it "
                    f"holds, so the addition keeps a place (DEC-001 point 1)",
                )
            elif after not in shipped and after not in added:
                self.problem(here, _unknown(kind, after, "names after"))
            elif after in opened:
                self.problem(
                    here,
                    f"the {kind.name}'s opening text follows `{after}`, and a part placed "
                    f"between them would take the opening's lines: name `{opened[after]}`, so "
                    f"the part comes after the opening",
                )
            elif _in_cycle(element_id, {i: g.additions[n].after for i, (g, n) in added.items()}):
                self.problem(
                    here,
                    f"`{element_id}` comes after `{after}`, which comes after it in turn: a "
                    f"cycle of additions has no place, so name an element the kind ships "
                    f"somewhere in it",
                )

    def one_line(self, here: str, name: str, change: Change) -> None:
        """A hint and its example stay one comment on one line, as the stamp writes them."""
        try:
            render.field_hint(Field(name, change.hint or "", change.example or ""))
        except ValueError as exc:
            self.problem(here, f"{exc}: a hint or an example holds no `-->` and no line break")


def _level(kind: str, level: int, top: int) -> str:
    """Why an added heading of `level` has no place in a kind whose own heading is of
    level `top`: each part of the kind ends at a heading of level `top + 1` or above."""
    if level <= top:
        return (
            f"a heading of level {level} would end the {kind}'s own section, whose heading is "
            f"of level {top}: add a heading of level {top + 1}"
        )
    return (
        f"a heading of level {level} would read as the content of the part before it, which "
        f"ends only at a heading of level {top + 1} or above: add a heading of level {top + 1}"
    )


def _added(item: Mapping[str, Any], rule: str) -> Element:
    kind = item.get("type", LABEL)
    return Element(
        id=str(item["id"]),
        type=kind,
        level=item.get("level") if kind == HEADING else None,
        text=str(item["label"]).strip(),
        required=item.get("required", False) is True,
        allows_none=item.get("allows-none", False) is True,
        form=item.get("form"),
        hint=item.get("hint"),
        example=item.get("example"),
        rule=rule,
        added=True,
    )


def _unknown(kind: Kind, element_id: str, does: str) -> str:
    if element_id in kind.retired:
        return (
            f"`{element_id}` is an element the {kind.name} kind retired: a retired element "
            f"is never given back (DEC-001 point 1)"
        )
    ids = ", ".join(f"`{e.id}`" for e in elements(kind))
    return (
        f"`{element_id}` is no element of the {kind.name} kind, which the entry {does}: its "
        f"elements are {ids}, and the project's additions"
    )


def _in_cycle(start: str, after: Mapping[str, str]) -> bool:
    """Whether following `after` from the addition `start`, through additions alone, comes
    back to it."""
    current = after[start]
    for _step in range(len(after)):
        if current == start:
            return True
        if current not in after:
            return False
        current = after[current]
    return current == start


# --- the structure a body is held to ----------------------------------------------------------


def relabelled(kind: Kind, own: Own) -> Kind:
    """`kind` with the project's relabels and fields' hints, which tighten nothing and so
    bind with the shipped structure, wherever it binds."""
    relabels = own.relabels.get(kind.name) or {}
    fields = own.fields.get(kind.name) or {}
    if not relabels and not fields:
        return kind

    def changed(element: Element) -> Element:
        parts = tuple(changed(part) for part in element.parts)
        if element.id not in relabels:
            return dataclasses.replace(element, parts=parts) if parts else element
        relabel = relabels[element.id]
        return dataclasses.replace(
            element,
            text=_or(relabel.label, element.text),
            hint=_or(relabel.hint, element.hint),
            example=_or(relabel.example, element.example),
            aliases=(element.text,)
            if relabel.label is not None and element.text is not None
            else (),
            parts=parts,
        )

    sections = tuple(changed(element) for element in kind.sections)
    hinted = tuple(
        dataclasses.replace(
            field,
            hint=_or(fields[field.name].hint, field.hint) or field.hint,
            example=_or(fields[field.name].example, field.example) or field.example,
        )
        if field.name in fields
        else field
        for field in kind.fields
    )
    return dataclasses.replace(kind, sections=sections, fields=hinted)


def _or(given: str | None, shipped: str | None) -> str | None:
    return given.strip() if given is not None else shipped


def tightened(
    kind: Kind,
    groups: Sequence[Group],
    applying: Collection[Group],
    standing: Collection[Group] = (),
) -> Kind:
    """`kind` — relabelled, as `relabelled` gives it — tightened by the groups of
    `groups` that are `applying`: each of their additions placed right after the element
    it names, each shipped part they require made required, and the rules that close the
    list of labels named. `groups` are all the kind's, so an addition keeps its place
    when one it names is left out. The labels the other `standing` groups add, those
    whose rule is the project's and not retired, still end the part before them
    (`Kind.delimiting`)."""
    applied = [group for group in groups if group in applying]
    delimiting = frozenset(
        comparable(addition.element.text or "")
        for group in groups
        if group in standing and group not in applying
        for addition in group.additions
        if addition.element.type == LABEL
    )
    if delimiting:
        kind = dataclasses.replace(kind, delimiting=kind.delimiting | delimiting)
    if not applied:
        return kind
    following: dict[str, list[tuple[Element, bool]]] = defaultdict(list)
    for group in groups:
        for addition in group.additions:
            following[addition.after].append((addition.element, group in applying))
    required = _required(kind, applied)

    def place(after: str, into: list[Element]) -> None:
        for element, applies in following.get(after, ()):
            if applies:
                into.append(element)
            place(element.id, into)

    def laid(run: Sequence[Element]) -> tuple[Element, ...]:
        into: list[Element] = []
        for element in run:
            element = required.get(element.id, element)
            if element.parts:
                element = dataclasses.replace(element, parts=laid(element.parts))
            into.append(element)
            place(element.id, into)
        return tuple(into)

    closed = tuple(dict.fromkeys(group.rule for group in applied if group.closed))
    return dataclasses.replace(kind, sections=laid(kind.sections), closed=closed)


def _required(kind: Kind, groups: Iterable[Group]) -> dict[str, Element]:
    """Each shipped optional part a group requires, required by the group's rule."""
    found: dict[str, Element] = {}
    by_id = {element.id: element for element in elements(kind)}
    for group in groups:
        for element_id in group.require:
            element = by_id.get(element_id)
            if element is not None and not element.required and element_id not in found:
                found[element_id] = dataclasses.replace(element, required=True, rule=group.rule)
    return found
