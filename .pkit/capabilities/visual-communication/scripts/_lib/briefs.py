"""A piece's brief, `brief.yaml` in its folder (visual-communication DEC-029): what the piece
must show and why it is designed so, for whoever makes or reviews it.

- **Its parts.** `piece` holds what concerns the whole piece, and `pages` a part for each page
  it speaks of, keyed by the id the page carries in the content (point 3). Each part names
  parts of the content by key paths: each relation in `relates`, and each reason in `about`.
  A page's part starts a path at its page, and the piece's part at the content's top.
- **Read by the check alone.** No renderer, export or producer reads it (point 4), so no
  scene and no fingerprint does either (`fingerprint.BRIEF`), and no command writes it.
- **Its shape** is the core's data validation's, against the schema it names (point 5). So
  this reads only what has the shape it needs, and leaves the rest to that validation. A
  brief that cannot be read, or whose binding is broken, is the binding's finding.
- **What it names must be there** (point 5), in the content of the source language, since
  ids are the same in every language (DEC-002 point 4). Each finding fails, in the brief,
  which the project mends:
  - `brief-page`: a page's part keyed by an id that no page of the content carries, or any
    page's part where the top is a page alone and holds no pages;
  - `brief-path`: a key path that is no key path, or names nothing in the content.
- **Where the pages are.** A top whose layouts are its pages' forms holds its pages in the
  list it marks; another top, in each slot its layout marks as holding pages, as items of a
  list or as the one component the slot places (DEC-010 point 5). The top's declaration says
  which, read as the check of ids reads a component, before the lock is checked. Where it
  cannot be read, the pages' parts are not judged: the lock's check and the scene say why.
- **A final piece** is read by its files and its lock alone, so its brief goes unread, as
  its content does (point 5, DEC-017 point 4).
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any

from _lib import layout, names
from _lib import pipeline as pl
from _lib.files import FileError, nearest, read_bound, without_binding
from _lib.findings import FAILS, Finding
from _lib.fingerprint import BRIEF
from _lib.reading import ReadError

#: The brief's kind of file, and the schema that binds it.
KIND = "brief"

#: The brief's part for the whole piece, and its mapping of pages' parts.
PIECE = "piece"
PAGES = "pages"

#: How to mend a key path that names nothing.
PATH_FIX = (
    "name the part by the keys and ids the content file writes, each item as `<list>[<id>]`: "
    "from the page in a page's part, and from the content's top in the piece's"
)

#: How to mend a page's part keyed by an id no page carries.
PAGE_FIX = (
    "key the part by the id of a page the content holds, or give the page that id in the "
    "content; before the page exists, write its intent under `piece`"
)


def read(piece: pl.Piece) -> dict[str, Any] | None:
    """The piece's brief, its binding removed; None where it keeps none, or where the brief
    cannot be read or its binding is broken, which the check of bindings reports."""
    path = piece.folder / BRIEF
    if not path.is_file():
        return None
    try:
        return without_binding(read_bound(path, KIND))
    except (ReadError, FileError):
        return None


def findings(piece: pl.Piece, top: Mapping[str, Any] | None) -> list[Finding]:
    """What the piece's brief names that its content lacks (DEC-029 point 5). `top` is the
    data of the piece's top component, or None where it cannot be read, which leaves the
    pages' parts unjudged. A piece with no brief raises none."""
    brief = read(piece)
    if brief is None:
        return []
    source = piece.languages[0]
    content = piece.contents.get(source)
    if not isinstance(content, Mapping):
        return []
    check = _Names(piece.file(BRIEF), pl.content_file(source))
    whole = brief.get(PIECE)
    if isinstance(whole, Mapping):
        check.part(whole, content, PIECE)
    parts = brief.get(PAGES)
    if not isinstance(parts, Mapping) or top is None:
        return check.found
    pages = pages_of(top, content)
    if pages is None:
        return check.found
    for page, part in parts.items():
        if page == names.CONTAINER or not isinstance(part, Mapping):
            continue
        where = f"{PAGES}.{page}"
        if page in pages:
            check.part(part, pages[page], where)
        else:
            check.unknown_page(str(page), where, sorted(pages))
    return check.found


def pages_of(top: Mapping[str, Any], content: Mapping[str, Any]) -> dict[str, Any] | None:
    """Each page of `content` that carries an id, by that id, with the mapping that holds it:
    the items of the list a top whose layouts are its pages' forms marks, or what each slot
    of pages of another top holds, an item of its list or the one component it places
    (DEC-010 point 5). Empty where the top is a page alone; None where its declaration does
    not say where its pages are, which its own check reports."""
    forms = layout.page_forms(top)
    if forms is not None:
        if len(forms.fields) != 1:
            return None
        return dict(_with_ids(content.get(forms.fields[0])))
    layouts = top.get("layouts")
    if not isinstance(layouts, Mapping):
        return None
    pages: dict[str, Any] = {}
    for decl in layouts.values():
        slots = decl.get("slots") if isinstance(decl, Mapping) else None
        if not isinstance(slots, Mapping):
            continue
        for slot, slot_decl in slots.items():
            if isinstance(slot_decl, Mapping) and slot_decl.get("pages") is True:
                pages.update(_with_ids(content.get(slot)))
    return pages


def _with_ids(held: Any) -> Iterator[tuple[str, Mapping[str, Any]]]:
    """Each page `held` holds that carries an id: each item of a list, or the one mapping."""
    for page in held if isinstance(held, list) else [held]:
        if isinstance(page, Mapping) and names.is_id(page.get("id")):
            yield page["id"], page


class _Names:
    """Reads what the parts of a brief name against the content, keeping what it finds."""

    def __init__(self, file: str, content_file: str) -> None:
        self.file = file
        self.content_file = content_file
        self.found: list[Finding] = []

    def part(self, part: Mapping[str, Any], start: Any, where: str) -> None:
        """The key paths of one part, each read from `start`: the page, or the content's top."""
        for place, relation in _listed(part.get("relations")):
            if isinstance(relation, Mapping):
                for at, text in _listed(relation.get("relates")):
                    self.path(text, start, f"{where}.relations#{place}.relates#{at}")
        for place, reason in _listed(part.get("reasons")):
            if isinstance(reason, Mapping) and "about" in reason:
                self.path(reason["about"], start, f"{where}.reasons#{place}.about")

    def path(self, text: Any, start: Any, where: str) -> None:
        """The key path `text`, at `where` in the brief, read from `start`."""
        why = named(text, start)
        if why is not None:
            self.found.append(
                Finding(
                    "brief-path",
                    FAILS,
                    f"`{text}` names nothing in `{self.content_file}`: it {why}",
                    file=self.file,
                    where=where,
                    fix=PATH_FIX,
                )
            )

    def unknown_page(self, page: str, where: str, pages: list[str]) -> None:
        """A page's part keyed by `page`, which is none of `pages`, the ids the content's
        pages carry."""
        if pages:
            close = nearest(page, pages)
            hint = f"; did you mean `{close}`?" if close else ""
            message = (
                f"the brief speaks of the page `{page}`, which no page of "
                f"`{self.content_file}` carries as its id; its pages are "
                f"{', '.join(f'`{each}`' for each in pages)}{hint}"
            )
            fix = PAGE_FIX
        else:
            message = (
                f"the brief speaks of the page `{page}`, and `{self.content_file}` holds no "
                "page that carries an id"
            )
            fix = f"a piece of one page keeps all of its brief under `piece`; else, {PAGE_FIX}"
        self.found.append(
            Finding("brief-page", FAILS, message, file=self.file, where=where, fix=fix)
        )


def _listed(value: Any) -> Iterator[tuple[int, Any]]:
    """Each entry of a list of the brief, with its place from 1; none where it is no list,
    a shape the data validation reports."""
    if isinstance(value, list):
        yield from enumerate(value, start=1)


def named(text: Any, start: Any) -> str | None:
    """Why the key path `text` names nothing from `start`, the page or the content's top,
    in words; None where it names a part of the content (DEC-029 point 3). Each key is one
    the content writes, and each step into a list names an item by its id (DEC-011 point
    3). A path may end at a list, a field that holds one."""
    steps = layout.key_path(text)
    if steps is None:
        return (
            "is no key path: the content file's keys joined by `.`, each item by its id as "
            "`<list>[<id>]`"
        )
    value = start
    previous = ""
    for key, item in steps:
        if isinstance(value, list):
            return f"steps into the list `{previous}` with no id: name its item as `[<id>]`"
        if not isinstance(value, Mapping):
            return f"steps into `{key}` below what is no mapping"
        if key not in value:
            close = nearest(key, [k for k in value if isinstance(k, str)])
            hint = f"; did you mean `{close}`?" if close else ""
            return f"names `{key}`, which the content does not give there{hint}"
        value, previous = value[key], key
        if item is None:
            continue
        if not isinstance(value, list):
            return f"names the item `[{item}]` of `{key}`, which is no list"
        held = [e for e in value if isinstance(e, Mapping) and isinstance(e.get("id"), str)]
        entry = next((e for e in held if e["id"] == item), None)
        if entry is None:
            close = nearest(item, [e["id"] for e in held])
            hint = f"; did you mean `[{close}]`?" if close else ""
            return f"names `[{item}]`, which the list `{key}` does not hold{hint}"
        value = entry
    return None
