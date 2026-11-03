"""Notations: the concepts of one subject, each mapped to a colour family
(visual-communication DEC-004 points 10 and 11).

A *notation* is a library version of kind `notation`. Beside its `library.yaml`, its
`notation.yaml` (format `notation`) maps each concept of its subject, by its name, to
`{colour: <family>}`: a colour family the foundations declare, never a value, so each brand
colours a concept its own way. A piece names the notations it uses under `notations`, and
its content names a concept read with its notation's name, `concept: <notation>/<concept>`,
as `use` names a component read with its library's.

`read_notation` reads one notation version against the foundations' colour families. What
is wrong is a finding in that version, so its level is read where it lies (DEC-002 point
7): a library that is no notation, a file that cannot be read, and a concept that does not
map to a colour family the foundations declare, such as one that maps to a value. A
notation whose files cannot be read holds no concept, and a concept that cannot be read is
kept apart (`unread`): content that names either takes its colour family as if it named
none, and no finding of its own, since the fault lies in the notation.

Knows nothing of the working folder, pieces, the list or the configuration.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass
from pathlib import Path

from _lib.files import FileError, read_bound
from _lib.findings import FAILS, Finding
from _lib.names import is_name
from _lib.reading import ReadError

#: The kind of library a notation is.
KIND = "notation"

#: A notation's file, within its version folder.
FILE = "notation.yaml"

#: What a concept maps to in format 1: its colour family alone.
CONCEPT_KEYS = frozenset({"colour"})


@dataclass(frozen=True)
class Notation:
    """One notation version, read.

    - `name` and `label` (`<name>@<version>`): the library's, as its folder names them.
    - `concepts`: each concept it holds that can be read, mapped to its colour family.
    - `unread`: each concept it holds that cannot be read.
    - `readable`: false where its files cannot be read, so it holds no concept.
    - `findings`: what is wrong, each naming the version it lies in.
    """

    name: str
    label: str
    concepts: Mapping[str, str]
    unread: frozenset[str] = frozenset()
    readable: bool = True
    findings: tuple[Finding, ...] = ()

    def family(self, concept: str) -> str | None:
        """The colour family `concept` maps to; None where the notation, or the concept in
        it, cannot be read. Raises KeyError where it holds no such concept."""
        if not self.readable or concept in self.unread:
            return None
        return self.concepts[concept]


def read_notation(folder: Path, families: Collection[str], *, root: Path | None = None) -> Notation:
    """The notation whose version folder is `folder`, `<name>/<version>/`, read against the
    colour families the foundations declare. Findings name its files relative to `root`
    when given, else to the version folder. Never raises: what cannot be read is a
    finding."""
    name, label = folder.parent.name, f"{folder.parent.name}@{folder.name}"
    shown = folder.relative_to(root).as_posix() + "/" if root is not None else ""

    def finding(code: str, message: str, file: str, where: str = "") -> Finding:
        return Finding(code, FAILS, message, file=f"{shown}{file}", where=where, library=label)

    def unreadable(code: str, message: str, file: str, where: str = "") -> Notation:
        found = finding(code, message, file, where)
        return Notation(name, label, {}, readable=False, findings=(found,))

    try:
        library = read_bound(folder / "library.yaml", "library")
    except (ReadError, FileError) as exc:
        return unreadable("notation-unreadable", _said(exc, folder, "library.yaml"), "library.yaml")
    if library.get("kind") != KIND:
        message = (
            f"{label} is not a notation (`kind: {library.get('kind')}`), yet a piece names it "
            f"under `notations`"
        )
        return unreadable("notation-kind", message, "library.yaml", "kind")
    if not (folder / FILE).is_file():
        return unreadable("notation-unreadable", f"{label} holds no `{FILE}`", FILE)
    try:
        data = read_bound(folder / FILE, KIND)
    except (ReadError, FileError) as exc:
        return unreadable("notation-unreadable", _said(exc, folder, FILE), FILE)
    raw = data.get("concepts")
    if not isinstance(raw, Mapping):
        message = f"`concepts` of {label} is not a mapping of concepts"
        return unreadable("notation-unreadable", message, FILE, "concepts")
    concepts: dict[str, str] = {}
    unread: set[str] = set()
    found: list[Finding] = []
    for concept, spec in raw.items():
        problem = _concept_problem(concept, spec, families)
        if problem is None:
            concepts[concept] = spec["colour"]
        else:
            unread.add(str(concept))
            found.append(finding("concept-shape", problem, FILE, f"concepts.{concept}"))
    return Notation(name, label, concepts, frozenset(unread), findings=tuple(found))


def _said(error: Exception, folder: Path, file: str) -> str:
    """What the reader says of a file of the version, naming the file within the version
    rather than by its path on this machine; the finding names the file in full."""
    return f"`{file}` {str(error).removeprefix(f'{folder / file}: ')}"


def _concept_problem(concept: object, spec: object, families: Collection[str]) -> str | None:
    """Why a concept of a notation cannot be read, or None: its name is a name, and it maps
    to `{colour: <family>}`, a colour family the foundations declare."""
    if not is_name(concept):
        return f"`{concept}` is not a concept's name of lower-case words joined by hyphens"
    if (
        not isinstance(spec, Mapping)
        or set(spec) != CONCEPT_KEYS
        or not isinstance(spec["colour"], str)
    ):
        return (
            f"the concept `{concept}` is not `{{colour: <family>}}`: a concept maps to a colour "
            f"family the foundations declare, never to a value"
        )
    family = spec["colour"]
    if not is_name(family):
        return (
            f"the concept `{concept}` maps to `{family}`, which is no colour family's name: a "
            f"concept maps to a colour family the foundations declare, never to a value"
        )
    if family not in families:
        declared = ", ".join(f"`{name}`" for name in families)
        return (
            f"the concept `{concept}` maps to `{family}`, which is no colour family the "
            f"foundations declare: {declared}"
        )
    return None
