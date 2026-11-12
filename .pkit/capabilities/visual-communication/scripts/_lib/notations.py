"""Notations: the concepts of one subject, each mapped to a colour family and a sign
(visual-communication DEC-004 points 10 and 11, DEC-036 point 1).

A *notation* is a library version of kind `notation`. Beside its `library.yaml`, its
`notation.yaml` (format `notation`) maps each concept of its subject, by its name, to
`{colour: <family>}`: a colour family the foundations declare, never a value, so each brand
colours a concept its own way. A concept may also hold its `icon`, an outline
(`outlines`), or map to a `shape` the foundations declare, by its name. Its *sign*, which
shows it beside its colour, is its icon, or else its shape. A piece names the notations it
uses under `notations`, and its content names a concept read with its notation's name,
`concept: <notation>/<concept>`, as `use` names a component read with its library's.

`read_notation` reads one notation version against the foundations' colour families and
shapes. What is wrong is a finding in that version, so its level is read where it lies
(DEC-002 point 7): a library that is no notation, a file that cannot be read, a concept
that does not map to a colour family the foundations declare, such as one that maps to a
value, and a concept's icon that is no outline or shape the foundations do not declare. A
notation whose files cannot be read holds no concept, and a concept whose colour cannot be
read is kept apart (`unread`): content that names either takes its colour family as if it
named none, and no finding of its own, since the fault lies in the notation. A concept
whose sign cannot be read keeps its colour family, and has no sign.

The checks of signs read two more findings in it (DEC-036 point 8). An icon that is no
closed outline within its square fails, and the concept keeps it as its sign, since it
draws. A concept that maps no sign, neither an icon nor a shape, asks the notation's owner
for attention, and never fails: a piece then tells it apart by its colour alone. A shape is
judged where the foundations declare it.

Knows nothing of the working folder, pieces, the list or the configuration.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from _lib.files import FileError, read_bound
from _lib.findings import ATTENTION, FAILS, Finding
from _lib.names import is_name
from _lib.outlines import CLOSE_IT, SIGN_OUTLINE, Outline, read_outline
from _lib.reading import ReadError

#: The kind of library a notation is.
KIND = "notation"

#: A notation's file, within its version folder.
FILE = "notation.yaml"

#: What a concept maps to in format 1: its colour family, and its icon or a shape.
CONCEPT_KEYS = frozenset({"colour", "icon", "shape"})

#: The call for attention on a concept that maps no sign (DEC-036 point 8).
CONCEPT_UNSIGNED = "concept-unsigned"


@dataclass(frozen=True)
class Notation:
    """One notation version, read.

    - `name` and `label` (`<name>@<version>`): the library's, as its folder names them.
    - `concepts`: each concept it holds that can be read, mapped to its colour family.
    - `unread`: each concept it holds that cannot be read.
    - `readable`: false where its files cannot be read, so it holds no concept.
    - `findings`: what is wrong, each naming the version it lies in.
    - `signs`: the sign of each concept that can be read and has one.
    """

    name: str
    label: str
    concepts: Mapping[str, str]
    unread: frozenset[str] = frozenset()
    readable: bool = True
    findings: tuple[Finding, ...] = ()
    signs: Mapping[str, Outline] = field(default_factory=dict)

    def family(self, concept: str) -> str | None:
        """The colour family `concept` maps to; None where the notation, or the concept in
        it, cannot be read. Raises KeyError where it holds no such concept."""
        if not self.readable or concept in self.unread:
            return None
        return self.concepts[concept]

    def sign(self, concept: str) -> Outline | None:
        """The sign of `concept`, its icon or else its shape; None where it has neither, or
        the notation, or the concept in it, cannot be read. Raises KeyError where it holds
        no such concept."""
        if self.family(concept) is None:
            return None
        return self.signs.get(concept)


def read_notation(
    folder: Path,
    families: Collection[str],
    *,
    shapes: Mapping[str, Outline],
    root: Path | None = None,
) -> Notation:
    """The notation whose version folder is `folder`, `<name>/<version>/`, read against the
    colour families and the shapes the foundations declare. Findings name its files
    relative to `root` when given, else to the version folder. Never raises: what cannot be
    read is a finding."""
    name, label = folder.parent.name, f"{folder.parent.name}@{folder.name}"
    shown = folder.relative_to(root).as_posix() + "/" if root is not None else ""

    def finding(
        code: str, message: str, file: str, where: str = "", level: str = FAILS, **more: str
    ) -> Finding:
        file = f"{shown}{file}"
        return Finding(code, level, message, file=file, where=where, library=label, **more)

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
    signs: dict[str, Outline] = {}
    found: list[Finding] = []
    for concept, spec in raw.items():
        problem = _concept_problem(concept, spec, families)
        if problem is not None:
            unread.add(str(concept))
            found.append(finding("concept-shape", problem, FILE, f"concepts.{concept}"))
            continue
        concepts[concept] = spec["colour"]
        sign = _sign(concept, spec, shapes)
        key = "icon" if "icon" in spec else "shape"
        if isinstance(sign, Outline):
            signs[concept] = sign
            fault = sign.fault() if key == "icon" else None  # a shape, in the foundations
            if fault is not None:
                message = f"the icon of the concept `{concept}` {fault}"
                where = f"concepts.{concept}.icon"
                found.append(finding(SIGN_OUTLINE, message, FILE, where, fix=CLOSE_IT))
        elif sign is not None:
            found.append(finding("concept-shape", sign, FILE, f"concepts.{concept}.{key}"))
        else:
            message = (
                f"the concept `{concept}` maps no sign, neither an `icon` nor a `shape`, so a "
                "piece tells it apart by its colour alone"
            )
            fix = "give the concept an `icon`, or map it to a `shape` the foundations declare"
            who = f"the owner of `{name}`"
            where = f"concepts.{concept}"
            unsigned = finding(CONCEPT_UNSIGNED, message, FILE, where, ATTENTION, fix=fix, who=who)
            found.append(unsigned)
    return Notation(name, label, concepts, frozenset(unread), findings=tuple(found), signs=signs)


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
        or "colour" not in spec
        or not set(spec) <= CONCEPT_KEYS
        or not isinstance(spec["colour"], str)
    ):
        return (
            f"the concept `{concept}` is not `{{colour: <family>}}`, with its `icon` or a "
            f"`shape` beside: a concept maps to a colour family the foundations declare, "
            f"never to a value"
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


def _sign(
    concept: str, spec: Mapping[str, object], shapes: Mapping[str, Outline]
) -> Outline | str | None:
    """The sign of a concept read, its icon or else its shape (DEC-036 point 1); why it
    cannot be read; or None where the concept maps neither. An icon that cannot be read
    leaves the concept with no sign, its shape unread."""
    if "icon" in spec:
        icon = read_outline(spec["icon"])
        return icon if isinstance(icon, Outline) else f"the icon of the concept `{concept}` {icon}"
    if "shape" not in spec:
        return None
    shape = spec["shape"]
    if isinstance(shape, str) and shape in shapes:
        return shapes[shape]
    declared = ", ".join(f"`{name}`" for name in shapes) or "none"
    return (
        f"the concept `{concept}` maps to the shape `{shape}`, which the foundations do not "
        f"declare: {declared}"
    )
