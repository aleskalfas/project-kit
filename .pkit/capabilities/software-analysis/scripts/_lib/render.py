"""A kind's body, rendered from its declared structure (DEC-001 point 1).

Each kind's structure is declared once, as data, in `schemas/artefact-kinds.yaml`
(`_lib/structure.py` reads it). The stamp writes each body from it, and never
copies a template's lines. A committed template's body is the same rendering,
made from the template's own front matter, and a test holds the two equal. So a
template shows exactly its kind's structure.

- **Every part, in its order.** A heading, a label or an opening, each as its
  element declares it, one blank line between two parts. The body ends with a
  line end.
- **The title heading** reads the id and the title or name the stamp gives,
  such as `# UC-007 — Export the report as a file`. A heading with fixed text,
  such as a record's `## Outcomes`, reads that text.
- **A part a writer fills** holds its hint as the placeholder: one line, a
  marked comment, `<!-- pkit:hint <hint> Example: <example> -->`. It follows a
  label on the label's line. Below a heading, and as an opening, it is a line of
  its own.
- **What the stamp writes besides** follows the part's first line, after a
  blank line, such as a journey's step lines under *Steps*.
- **A front-matter field a writer fills** holds its hint the same way, as the
  field's text: the same marked comment, one line, which a YAML parse reads as
  a text like any other. A field that takes a list holds one item, its hint.
  The fields are those the kind declares and its template's front matter
  gives, less those the stamp writes itself (`STAMPED`): an actor's `needs`
  and a term's `definition`. The template's front matter, written by hand,
  shows the same hints, and a test holds the two equal.
- **A revalidation record** carries no hints, since its stamp writes every part
  from its command line. Its template shows each part's declared example as one
  item of the part's list, which is how its stamp writes every item.
- **A collection's file head**, the glossary's heading and opening, holds the
  words the declaration gives the stamp. It is written once, when the file is
  created.

A hint is matched by its marker, `<!-- pkit:hint`, wherever a hint is left in
(`_lib/structure.py`'s `hints`), in a body or a field, so it never needs a
list of its own texts.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from _lib.structure import HEADING, LABEL, OPENING, RECORD, Element, Field, Kind

#: The mark that makes an HTML comment a hint, after `<!--` and a space.
HINT = "pkit:hint"

#: What closes a comment, which no hint or example may hold.
_CLOSE = "-->"

#: The front-matter fields the stamp writes itself, from its command line or its
#: template, so never a writer's to fill: an artefact's id, its title or name, its
#: status, its actor and its steps.
STAMPED = frozenset({"id", "title", "name", "status", "actor", "steps"})


def hint(element: Element) -> str:
    """The part's hint as its placeholder: one marked comment, its example after it."""
    return _marked(element.id, element.hint or "", element.example)


def field_hint(field: Field) -> str:
    """A front-matter field's hint as its placeholder: the same marked comment a part
    holds, its example after it."""
    return _marked(field.name, field.hint, field.example)


def fields_left(kind: Kind, front: Mapping[str, Any]) -> dict[str, Any]:
    """Each front-matter field `kind` declares, that the template's front matter `front`
    gives and the stamp does not write itself (`STAMPED`), holding its hint as its
    placeholder: a field that takes a list, one item (DEC-001 point 1)."""
    return {
        field.name: [field_hint(field)]
        if isinstance(front[field.name], list)
        else field_hint(field)
        for field in kind.fields
        if field.name in front and field.name not in STAMPED
    }


def _marked(name: str, said: str, example: str | None) -> str:
    if example:
        said = f"{said} Example: {example}"
    if _CLOSE in said or "\n" in said:
        raise ValueError(f"the hint of {name!r} would not stay one comment on one line")
    return f"<!-- {HINT} {said} -->"


def body(
    kind: Kind, title: str, written: Mapping[str, str] | None = None, *, hints: bool = True
) -> str:
    """The body of an artefact or a record of `kind`, its title heading reading `title`:
    each part a writer fills holds its hint, unless `hints` is false, and then what
    `written` gives it by the element's id."""
    given = written or {}
    blocks = [_block(element, title, given.get(element.id), hints) for element in kind.sections]
    return "\n\n".join(block for block in blocks if block) + "\n"


def head(kind: Kind) -> str:
    """A collection file's head: the heading and the opening the declaration gives the
    stamp, which it writes once, when it creates the file."""
    blocks: list[str] = []
    for element in kind.head:
        words = element.example or ""
        if element.type == HEADING:
            blocks.append(f"{'#' * (element.level or 1)} {words}")
        elif words:
            blocks.append(words)
    return "\n\n".join(blocks) + "\n"


def examples(kind: Kind) -> dict[str, str]:
    """Each part's declared example as one item of its list, by the element's id: what a
    revalidation record's template shows, since its stamp writes each part's items."""
    return {e.id: f"- {e.example}" for e in kind.sections if e.filled and e.example}


def template(kind: Kind, front: Mapping[str, Any]) -> str:
    """The body of `kind`'s committed template, whose front matter is `front`. A
    document's title heading reads the id and the title or name its front matter gives,
    and each part holds its hint. A collection's file head comes first, then its one
    entry's section. A revalidation record shows the example of each part, its heading
    included, and no hint."""
    if kind.name == RECORD:
        heading = next(e for e in kind.sections if e.type == HEADING and e.text is None)
        title = (heading.example or "").lstrip("#").strip()
        return body(kind, title, examples(kind), hints=False)
    if kind.head:
        ((entry_id, entry),) = front.items()
        name = entry["name"]
        return f"{head(kind)}\n{body(kind, f'{entry_id} — {name}')}"
    named = front.get("title", front.get("name"))
    return body(kind, f"{front['id']} — {named}")


def _block(element: Element, title: str, written: str | None, hints: bool) -> str:
    lead = hint(element) if hints and element.filled else None
    below = written.strip("\n") if written else None
    if element.type == HEADING:
        heading = f"{'#' * (element.level or 1)} {element.text if element.text else title}"
        return "\n\n".join(text for text in (heading, lead, below) if text)
    if element.type == LABEL:
        label = f"**{element.text}:**"
        if lead is not None:
            label = f"{label} {lead}"
        elif below is not None and "\n" not in below:
            return f"{label} {below}"
        return "\n\n".join(text for text in (label, below) if text)
    assert element.type == OPENING, element.type
    return "\n\n".join(text for text in (lead, below) if text)
