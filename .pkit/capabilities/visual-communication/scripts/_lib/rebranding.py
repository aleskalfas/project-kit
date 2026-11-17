"""What a move of a piece's lock onto another brand says does not follow it (visual-communication
DEC-025 point 8).

- **The brand a lock names** (`brand_of`): the brand among its versions that no other brand of
  it builds on, as the versions the project holds read. A brand built on a base locks its base
  too, so the base is the lock's brand only where no brand built on it is locked.
- **A move onto another brand** (`moved`): two locks that name different brands. A first lock,
  a lock whose brand cannot be read, and a move within one brand say nothing.
- **What does not follow the new brand** (`unfollowed`), read from the scenes under the new
  lock, in each language and at each key over the size axes:
  - each picture file of the piece an image shows, whoever names it, the content or a local
    component's `file` (DEC-025 points 1 and 3);
  - each picture role a part shows that the new brand gives no file, which the scene does not
    draw (`SceneResult.unvalued`, DEC-025 point 4).

  A library's own file is part of the form its owner chose for every brand, and a produced
  picture is no picture file, so neither is named. Each is named with its image's trace id,
  and with the keys over the size axes it lies at where those are not every key.
- **Said, never kept** (`said`): a line each, which the command prints. No record keeps it, and
  the check reads none of it, since validation answers about the files as they are (DEC-002
  point 7).
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass

from _lib.libraries import Held, Library, LibraryError, Version
from _lib.names import PIECE
from _lib.scene import Element, SceneResult

#: The kind of library a brand is (`libraries.KINDS`).
BRAND = "brand"

#: What each kind of thing that does not follow a brand is, in the order it is said.
FILE = "file"
ROLE = "role"


@dataclass(frozen=True)
class Unfollowed:
    """What does not follow a new brand, in one language: the trace id of the image, and the
    picture file of the piece it shows, `file`, or the picture role the brand gives no file,
    `role`. `keys` names the keys over the size axes it lies at, where those are not every key
    the language's scenes hold."""

    language: str
    trace: str
    file: str = ""
    role: str = ""
    keys: tuple[str, ...] = ()


def brand_of(held: Held, lock: Mapping[str, str]) -> str | None:
    """The brand `lock` names: the one among its versions of kind `brand` that no other of them
    builds on, read as the project holds it. None where it names none, or more than one such.
    A version the project does not hold, or cannot read, is passed over."""
    brands: dict[str, Library] = {}
    for name, number in lock.items():
        try:
            library = held.library(name, Version.parse(number))
        except (ValueError, LibraryError):
            continue
        if library.kind == BRAND:
            brands[name] = library
    built_on = {need.name for library in brands.values() for need in library.builds_on}
    named = sorted(set(brands) - built_on)
    return named[0] if len(named) == 1 else None


def moved(
    held: Held, before: Mapping[str, str] | None, after: Mapping[str, str]
) -> tuple[str, str] | None:
    """The brand `before` names and the brand `after` names, where they differ (`brand_of`).
    None where they name one brand, or either names none, as a piece's first lock does."""
    if not before:
        return None
    was, now = brand_of(held, before), brand_of(held, after)
    if was is None or now is None or was == now:
        return None
    return was, now


def unfollowed(results: Sequence[tuple[str, SceneResult]]) -> tuple[Unfollowed, ...]:
    """What the scenes `results` show that does not follow their brand: in the order of their
    languages, each picture file of the piece an image shows, in drawing order, then each
    picture role left out, each once. One that lies at some keys over the size axes alone names
    them."""
    found: dict[tuple[str, str, str, str], list[str]] = {}
    keys: dict[str, list[str]] = {}
    for language, result in results:
        key = result.scene.size_key
        keys.setdefault(language, []).append(key)
        for element in _images(result.scene.children):
            if element.properties.get("library") == PIECE and "file" in element.properties:
                named = str(element.properties["file"])
                found.setdefault((language, FILE, element.id, named), []).append(key)
        for trace, role in result.unvalued.items():
            found.setdefault((language, ROLE, trace, role), []).append(key)
    languages = list(keys)
    seen = {each: place for place, each in enumerate(found)}
    ordered = sorted(
        found, key=lambda each: (languages.index(each[0]), (FILE, ROLE).index(each[1]), seen[each])
    )
    listed = []
    for each in ordered:
        language, kind, trace, name = each
        at = () if set(found[each]) == set(keys[language]) else tuple(found[each])
        if kind == FILE:
            listed.append(Unfollowed(language, trace, file=name, keys=at))
        else:
            listed.append(Unfollowed(language, trace, role=name, keys=at))
    return tuple(listed)


def said(was: str, now: str, found: Sequence[Unfollowed], why: str = "") -> list[str]:
    """What a move from the brand `was` onto `now` says, a line each: the move, then each of
    `found`. Where the scenes under the new lock cannot be computed, it says `why` instead."""
    head = f"another brand: `{was}` to `{now}`"
    if why:
        return [f"{head}, and what does not follow it cannot be told: {why}"]
    if not found:
        return [
            f"{head}: no picture file of the piece shows, and `{now}` gives each picture role a "
            f"part shows"
        ]
    lines = [head]
    for each in found:
        at = f", at {', '.join(f'`{key}`' for key in each.keys)}" if each.keys else ""
        if each.file:
            what = f"the picture file `{each.file}` of the piece, which stays as it was"
        else:
            what = (
                f"the picture role `{each.role}`, which `{now}` gives no file, so it is not drawn"
            )
        lines.append(f"not following `{now}`: `{each.language}`: `{each.trace}`: {what}{at}")
    return lines


def _images(elements: Sequence[Element]) -> Iterator[Element]:
    """Each image among `elements` and the groups under them, in drawing order."""
    for element in elements:
        if element.type == "image":
            yield element
        yield from _images(element.children)
