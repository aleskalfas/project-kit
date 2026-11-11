"""The pipeline: a piece's files joined to the engine (visual-communication DEC-002 point 5,
DEC-003 point 8, DEC-005 points 5 to 7, DEC-006 point 5).

The engine knows nothing of the working folder, pieces, the list or the configuration; it
reads through an `Env` (`env.py`). This module builds the real one from a project's files:

- **A piece** is a folder of the location's `pieces/`: its `piece.yaml`, a content file
  `content.<language>.yaml` for each language it lists, its local components, and what
  a producer made for it under `produced/<output>/`. `read_piece` reads it, and
  `read_piece_file` its `piece.yaml` alone, which is what the check reads of a final piece.
- **Its lock** names the version of each library it uses. `needed` gives the libraries
  the piece names itself: its top's library, its brand, its notations and every library
  its content uses; `libraries.move_lock` adds what they build on, judging each whole
  combination it reaches with `Fit`. `locked` gives the bytes of `piece.yaml` with a
  lock written in as text, every other byte kept.
- **A project** (`Project`) is a piece under one lock: the scope of the locked versions,
  the foundations' declarations and the own roles of each component library the lock
  names (DEC-008 point 1), and the brand read against it, over its base at the version
  the lock names when it builds on one (DEC-004 point 6), the notations the piece names
  (DEC-004 point 10), the combinations the piece names, the `Env` over them, and the
  drawings that draw under the brand along its chain (`brand_drawings`, DEC-009 point 4). It
  computes one scene for each language and each key over the size axes the piece names
  (DEC-005 point 6), each reading the brand's roles at its key (`ProjectEnv.at`), and draws
  each combination from the scene of its key (`drawn`). A format that holds modes takes the
  combinations of one file in one call, grouped by the signal pairs its renderer declares
  (`files_of`, DEC-023 points 1 and 2).
- **A library version checked alone** is read through `LibraryEnv`, an `Env` that no
  piece or brand stands behind: components from a combination of library versions, and
  roles from their declarations alone (DEC-008 point 1, DEC-010 point 9).
- **Whether versions fit the piece** as its lock does is `Fit`, the judgement a draft's
  render gives the search for its lock: the piece placed under a combination, no scene
  computed, against the piece placed under its lock (DEC-003 point 8, DEC-010 point 2,
  DEC-011 point 4).
- **A produced picture** is read from `produced/<output>/record.yaml`. A missing record,
  or a variant file it names that is missing, makes the picture missing for the engine,
  with the reason kept so the finding names `pkit visual produce <piece> <output>`; it
  never crashes the computation.
- **A picture file** lies in the piece's `pictures/`, or in that of a locked library's
  version, found by its bare name and read as `pictures.Folder` reads one, each file once
  (DEC-025 points 2, 5 and 9). One that cannot be read is kept with why, so an export
  refuses the piece.
- **What a renderer is handed** for each image, in each language and combination it draws
  (`ProjectEnv.handed`): the file it shows there and its kind, by the image's trace id
  (`seam.Shown`, DEC-025 point 7). A content's picture differs by language, so what a
  renderer is handed is worked out from each language's scene.
- **The findings record's key** (`findings_key_sources`) is worked out here from the
  current files, under form 1.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field, replace
from functools import cached_property
from pathlib import Path
from typing import Any

from _lib import copies, keys, layout, notations, pictures, records, tokens, values
from _lib.copies import DRAFT
from _lib.env import MissingFont, PictureInfo, UnknownConcept, UnreadableComponent
from _lib.files import FileError, read_bound, refuse_links, without_binding
from _lib.findings import Finding
from _lib.fingerprint import COPY_PLACE
from _lib.libraries import FOLDER, FOUNDATIONS, Held, Library, LibraryError, Misfit, Version
from _lib.location import files as listed_files
from _lib.names import PIECE, is_language, is_name, split_use
from _lib.plugins import seam
from _lib.reading import ReadError, read_yaml, sha256
from _lib.scene import SceneResult, compute_scene

#: The folder of the location that holds the pieces, one folder each.
PIECES = "pieces"

#: The folder of the location that holds fonts a brand names by their hash.
FONTS = "fonts"

#: The files and folders of a piece's folder.
PIECE_FILE = "piece.yaml"
COMPONENTS = "components"
PRODUCED = "produced"
RECORD = "record.yaml"
FINDINGS_FILE = "findings.yaml"
EXPORTS_FILE = "exports.yaml"


#: The byte-order mark a file may open with, which a rewrite of the lock keeps.
BOM = records.BOM


class Refused(Exception):
    """What stops a command, or the check of a piece: the message names the file and the
    fix."""


def content_file(language: str) -> str:
    """The name of a piece's content file in `language`."""
    return f"content.{language}.yaml"


def new_piece_folder(root: Path, location: str, name: str) -> Path:
    """The folder of a new piece `name` in `location`. Raises Refused where `name` is not a
    piece's name, or anything lies there already, so a new piece never writes over a file."""
    if not is_name(name):
        raise Refused(f"`{name}` is not a piece's name: lower-case words joined by hyphens")
    rel = f"{location}/{PIECES}/{name}"
    target = root / rel
    if target.exists() or target.is_symlink():
        raise Refused(
            f"{rel} lies in the location already, so the name `{name}` is taken: name the new "
            f"piece another"
        )
    return target


def produce_command(piece: str, output: str) -> str:
    return f"`pkit visual produce {piece} {output}`"


def render_command(piece: str) -> str:
    return f"`pkit visual render {piece}`"


# --- a piece ------------------------------------------------------------------------------------


class Piece:
    """A piece's own files, read: its `piece.yaml`, and its content in each language, the
    binding fields removed."""

    def __init__(
        self,
        root: Path,
        location: str,
        name: str,
        data: Mapping[str, Any],
        contents: Mapping[str, Mapping[str, Any]],
    ) -> None:
        self.root = root
        self.location = location
        self.name = name
        self.data = data
        self.contents = contents

    @property
    def rel(self) -> str:
        """The piece's folder, relative to the project root."""
        return f"{self.location}/{PIECES}/{self.name}"

    @property
    def folder(self) -> Path:
        return self.root / self.rel

    def file(self, name: str) -> str:
        """A file of the piece, relative to the project root."""
        return f"{self.rel}/{name}" if name else self.rel

    @property
    def top(self) -> str:
        return str(self.data["top"])

    @property
    def brand(self) -> str:
        return str(self.data["brand"])

    @property
    def notations(self) -> list[str]:
        """The notations its content names concepts from, by their libraries' names."""
        return list(dict.fromkeys(self.data.get("notations") or []))

    @property
    def languages(self) -> list[str]:
        return list(self.data["languages"])

    @property
    def state(self) -> str:
        return str(self.data.get("state", ""))

    @property
    def stand_ins(self) -> layout.Facts:
        """What fills the facts of every scene a shared answer rests on, such as the check's:
        its state, and the stand-in for a version's number and its date (DEC-016 point 5)."""
        return layout.stand_ins(self.state)

    @property
    def pinned(self) -> bool:
        """Whether its lock is pinned, which is read of a draft alone (DEC-003 point 8)."""
        return self.state == DRAFT and self.data.get("pinned") is True

    @cached_property
    def why_final(self) -> str:
        """Why it is final to every command, in words; empty where it is not (`copies.why_final`,
        DEC-017 point 3). Its record of exports is read once."""
        return copies.why_final(self.data, self.folder)

    @property
    def final(self) -> bool:
        """Whether it is final to every command, by its state or by its record of exports."""
        return bool(self.why_final)

    @property
    def lock_stays(self) -> bool:
        """Whether no render moves its lock, whatever its `pinned` says (`copies.lock_stays`)."""
        return copies.lock_stays(self.data, self.final)

    @property
    def lock(self) -> dict[str, str]:
        return dict(self.data.get("lock") or {})

    @property
    def modes(self) -> dict[str, list[str]]:
        return {axis: list(named) for axis, named in (self.data.get("modes") or {}).items()}

    @property
    def produced(self) -> Mapping[str, Any]:
        return self.data.get("produced") or {}

    @property
    def exports(self) -> list[str]:
        return list(self.data.get("exports") or [])

    @property
    def copy_place(self) -> str | None:
        """The folder it names for its current copy, a path from the repository's root, or
        None, so the copy lies in the piece's folder (DEC-017 point 8)."""
        return self.data.get(COPY_PLACE)

    @property
    def accepted_losses(self) -> list[Mapping[str, Any]]:
        return [
            entry for entry in self.data.get("accept-losses") or [] if isinstance(entry, Mapping)
        ]


def piece_names(root: Path, location: str) -> list[str]:
    """The pieces of the location: each folder of its `pieces/` that holds a file."""
    return pieces_in(location, listed_files(root, f"{location}/{PIECES}"))


def pieces_in(location: str, listed: Iterable[str]) -> list[str]:
    """The pieces of the location that `listed`, the files of its `pieces/`, hold."""
    prefix = f"{location}/{PIECES}/"
    return sorted({rel[len(prefix) :].split("/")[0] for rel in listed})


def read_piece_file(root: Path, location: str, name: str) -> Piece:
    """The piece `name` of the location as its `piece.yaml` alone gives it, with no contents:
    no content file is read, so a fault in one refuses nothing (DEC-017 point 4). Raises
    Refused, naming the file and what to change, when that file cannot be read as a piece's."""
    if not is_name(name):
        raise Refused(f"`{name}` is not a piece's name: lower-case words joined by hyphens")
    rel = f"{location}/{PIECES}/{name}"
    path = root / rel / PIECE_FILE
    if not path.is_file():
        raise Refused(f"{rel}/{PIECE_FILE} does not exist: the location holds no piece `{name}`")
    try:
        data = without_binding(read_bound(path, "piece"))
    except (ReadError, FileError) as exc:
        raise Refused(str(exc)) from exc
    shown = f"{rel}/{PIECE_FILE}"
    _require(isinstance(data.get("top"), str) and _is_use(data["top"]), shown, "top", "a use")
    _require(is_name(data.get("brand")), shown, "brand", "a library's name")
    named = data.get("notations", [])
    _require(
        isinstance(named, list) and all(map(is_name, named)),
        shown,
        "notations",
        "a list of libraries' names",
    )
    languages = data.get("languages")
    _require(
        isinstance(languages, list) and bool(languages) and all(map(is_language, languages)),
        shown,
        "languages",
        "a list of language tags",
    )
    _require(_is_lock(data.get("lock", {})), shown, "lock", "a mapping of libraries to versions")
    _require(_is_modes(data.get("modes", {})), shown, "modes", "a mapping of axes to modes")
    _require(isinstance(data.get(COPY_PLACE, ""), str), shown, COPY_PLACE, "a path")
    return Piece(root, location, name, data, {})


def read_piece(root: Path, location: str, name: str) -> Piece:
    """The piece `name` of the location, read: its `piece.yaml` and its content in each
    language. Raises Refused, naming the file and what to change, when it cannot be read as a
    piece."""
    piece = read_piece_file(root, location, name)
    contents = {}
    for language in piece.languages:
        content = piece.folder / content_file(language)
        if not content.is_file():
            raise Refused(
                f"{piece.file(content_file(language))} does not exist: the piece lists the "
                f"language `{language}`, so write its content there"
            )
        try:
            contents[language] = without_binding(read_bound(content, "content"))
        except (ReadError, FileError) as exc:
            raise Refused(str(exc)) from exc
    return Piece(root, location, name, piece.data, contents)


def _require(holds: bool, file: str, key: str, shape: str) -> None:
    if not holds:
        raise Refused(f"{file}: `{key}` is not {shape}")


def _is_use(value: Any) -> bool:
    try:
        split_use(value)
    except ValueError:
        return False
    return True


def _is_lock(value: Any) -> bool:
    return isinstance(value, Mapping) and all(
        isinstance(name, str) and isinstance(version, str) for name, version in value.items()
    )


def _is_version(text: Any) -> bool:
    try:
        Version.parse(text)
    except ValueError:
        return False
    return True


def _is_modes(value: Any) -> bool:
    return isinstance(value, Mapping) and all(
        isinstance(named, list) and all(isinstance(mode, str) for mode in named)
        for named in value.values()
    )


def uses(value: Any) -> Iterator[str]:
    """Every component a content value places by `use`, at any depth."""
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key == "use" and isinstance(item, str):
                yield item
            else:
                yield from uses(item)
    elif isinstance(value, list):
        for item in value:
            yield from uses(item)


def needed(piece: Piece) -> list[str]:
    """The libraries the piece names itself: the foundations, which hold the shared roles
    every piece reads, its top's, its brand, its notations, and every library its content
    uses, in name order. What they build on the lock adds."""
    found = {FOUNDATIONS, piece.brand, *piece.notations}
    for use in [piece.top, *(use for content in piece.contents.values() for use in uses(content))]:
        library = use.partition("/")[0]
        if _is_use(use) and library != PIECE:
            found.add(library)
    return sorted(found)


# --- writing a lock into piece.yaml -------------------------------------------------------------


def lock_text(piece_yaml: str, lock: Mapping[str, str]) -> str:
    """The text of a `piece.yaml` with its top-level `lock` replaced by `lock`, or added at
    its end, one library a line in name order, every other byte kept: its comments, its
    order, its line endings and a byte-order mark (`records.with_mapping`). Raises Refused
    when the text would not read back as it was with that lock."""
    ordered = {name: lock[name] for name in sorted(lock)}
    try:
        return records.with_mapping(piece_yaml, "lock", ordered, each="library")
    except records.RecordError as exc:
        raise Refused(f"{PIECE_FILE} cannot take the lock as text: {exc}") from exc


def locked(piece: Piece, lock: Mapping[str, str]) -> bytes | None:
    """The bytes of the piece's `piece.yaml` with `lock` written in (`lock_text`), or None
    when it holds that lock already. Writes nothing; raises Refused, so a command learns of
    a lock it cannot write before its first write."""
    if piece.lock == dict(lock) and "lock" in piece.data:
        return None
    path = piece.folder / PIECE_FILE
    writable(piece.root, path)
    return lock_text(path.read_bytes().decode("utf-8"), lock).encode("utf-8")


# --- a piece under one lock ---------------------------------------------------------------------


class Project:
    """A piece under one lock: the scope of the locked versions (`tokens.Scope`), the
    brand and the notations the piece names, read from the locked versions, the
    combinations the piece names, and the `Env` the engine reads. A notation that cannot
    be read, wholly or in part, keeps its findings (`notations.Notation`), and stops
    nothing; so does a library's own roles, whose findings the scope keeps.

    Raises Refused when the lock lacks the foundations, the brand or a notation, or the
    piece names a mode its brand lacks; `tokens.TokenError`, carrying its findings, when
    the foundations' declarations or the brand cannot be read."""

    def __init__(self, piece: Piece, lock: Mapping[str, str], held: Held) -> None:
        # Each name and version of the lock becomes a segment of a path below the library
        # folder, so a lock that holds anything else is refused before any is read. The
        # check reports such a lock as a finding first (`lock-version`).
        for library, version in lock.items():
            if not is_name(library) or not _is_version(version):
                raise Refused(
                    f"the lock of {piece.file(PIECE_FILE)} names `{library}: {version}`, "
                    f"which is no library at a version `X.Y.Z`"
                )
        self.piece = piece
        self.lock = dict(lock)
        self.held = held
        self.root = piece.root
        self.location = piece.location
        locked = {
            library: self.root / self.location / FOLDER / library / version
            for library, version in self.lock.items()
        }
        self.scope = tokens.read_scope(
            {
                **{name: folder for name, folder in locked.items() if folder.is_dir()},
                FOUNDATIONS: self.version_folder(FOUNDATIONS),
            },
            root=self.root,
        )
        self.foundations = self.scope.foundations
        self.brand = tokens.read_brand(
            self.version_folder(piece.brand),
            self.scope,
            fonts=self.root / self.location / FONTS,
            root=self.root,
            locked=locked,
            walked=held.walked,
        )
        self.notations = {
            name: notations.read_notation(
                self.version_folder(name), self.foundations.families, root=self.root
            )
            for name in piece.notations
        }
        try:
            self.combinations = self.brand.combinations_of(piece.modes)
        except keys.BadKey as exc:
            raise Refused(f"{piece.file(PIECE_FILE)}: `modes`: {exc}") from exc
        axes = self.brand.axes
        self.keys = [keys.key_of(combination, axes) for combination in self.combinations]
        self._size_keys = {
            key: size_key_of(combination, axes)
            for key, combination in zip(self.keys, self.combinations, strict=True)
        }
        self.size_keys = sorted(set(self._size_keys.values()), key=keys.key_order)
        self._values: dict[str, Any] | None = None
        self.env = ProjectEnv(self)
        drawn = brand_drawings(self.brand)
        self.drawings = drawn.drawings
        self.kept = drawn.kept
        self._choice: layout.Choice | None = None

    def label(self, library: str) -> str:
        """`<library>@<version>` of a locked library."""
        return f"{library}@{self.lock[library]}"

    @property
    def chain(self) -> list[tokens.Brand]:
        """The piece's brand, then each brand it builds on as its base, the root last."""
        found: list[tokens.Brand] = []
        brand: tokens.Brand | None = self.brand
        while brand is not None:
            found.append(brand)
            brand = brand.base
        return found

    def kind(self, library: str) -> str | None:
        """The kind of the version of `library` the lock names; None where it names none, or
        the version's `library.yaml` cannot be read, which the lock's findings report."""
        try:
            return self.held.library(library, Version.parse(self.lock[library])).kind
        except (KeyError, LibraryError):
            return None

    def version_folder(self, library: str) -> Path:
        """The folder of the version of `library` the lock names. Raises Refused when the
        lock names none, or the project does not hold it."""
        version = self.lock.get(library)
        if version is None:
            raise Refused(
                f"the lock of {self.piece.file(PIECE_FILE)} names no `{library}`: run "
                f"{render_command(self.piece.name)}"
            )
        folder = self.root / self.location / FOLDER / library / version
        if not (folder / "library.yaml").is_file():
            raise Refused(
                f"the lock of {self.piece.file(PIECE_FILE)} names {library}@{version}, which "
                f"the project does not hold"
            )
        return folder

    def values(self) -> dict[str, Any]:
        """The document of the brand's resolved values in every combination the piece names
        (DEC-005 point 7), computed once."""
        if self._values is None:
            self._values = values.document(self.brand, self.combinations, self.lock)
        return self._values

    def size_key(self, key: str) -> str:
        """The key over the size axes of the combination `key` the piece names: the key of
        the scene that serves it. Raises KeyError for a key the piece does not name."""
        return self._size_keys[key]

    def choice(self) -> layout.Choice:
        """Which drawing draws each instance of a layout in every scene of the piece,
        worked out once (DEC-034 point 6). A brand's drawing draws an instance only where it
        fits it in each language the piece holds and at every key over the size axes it
        names, so the piece is placed in each, as the search for a lock places it. Each
        instance a drawing does not fit somewhere is left to its top's own drawing in all
        of them, naming the first language and key where it did not fit, and the piece is
        placed again until no other instance is left so. A brand that draws no layout
        leaves every top to its own drawing, and places nothing more. Raises `MissingFont`
        as a scene does."""
        if self._choice is not None:
            return self._choice
        refused: dict[str, str] = {}
        choice = layout.Choice()
        while self.drawings:
            choice = layout.Choice(self.drawings, dict(refused))
            for language in self.piece.languages:
                for size in self.size_keys:
                    sizes = sizes_at(self.scope.axes, size)
                    ctx = layout.Context(
                        self.env.at(size), language, self.piece.stand_ins, sizes, choice
                    )
                    layout.place_top(ctx, self.piece.top, self.piece.contents[language])
                    for trace, why in ctx.misfits.items():
                        refused.setdefault(trace, f"{why}, in `{language}` at `{size}`")
            if len(refused) == len(choice.refused):
                break
        self._choice = choice
        return choice

    def scenes(
        self,
        languages: Sequence[str] | None = None,
        keys: Sequence[str] | None = None,
        *,
        facts: layout.Facts,
    ) -> list[tuple[str, SceneResult]]:
        """One scene for each language, or each of `languages`, and each key over the size
        axes the piece names, or each that serves one of the combinations `keys`, in the
        piece's order of languages, then in key order. Each scene's root names its key, and
        it reads each role at that key (`ProjectEnv.at`), and each size axis of the
        foundations a component reads at its mode there (`sizes_at`). Each takes its
        language, and `facts` fills the rest of its export's facts: the caller says what,
        and none takes one by default (DEC-016 point 5). A shared answer takes the piece's
        `stand_ins`.
        Raises `env.MissingFont` (and so `text.MissingGlyph`) before anything is laid out."""
        served = None if keys is None else {self.size_key(key) for key in keys}
        sizes = [size for size in self.size_keys if served is None or size in served]
        choice = self.choice()
        return [
            (
                language,
                compute_scene(
                    piece=self.piece.name,
                    top=self.piece.top,
                    content=dict(self.piece.contents[language]),
                    language=language,
                    lock=self.lock,
                    size_key=size,
                    seam_version=seam.SEAM_VERSION,
                    env=self.env.at(size),
                    facts=facts,
                    sizes=sizes_at(self.scope.axes, size),
                    choice=choice,
                ),
            )
            for language in self.piece.languages
            if languages is None or language in languages
            for size in sizes
        ]


@dataclass(frozen=True)
class Kept:
    """A brand's drawing that draws nothing, since a brand nearer the root of its chain
    serves its top (DEC-009 point 4): the top, and the label of the brand that serves it."""

    top: str
    by: str


@dataclass(frozen=True)
class Drawings:
    """What draws along a brand's chain (DEC-009 points 2 to 4, DEC-034 point 4): each
    drawing that draws, by its use under the top and the layout its `draws` names, and each
    a brand nearer the root keeps from drawing, by its use (`Kept`)."""

    drawings: dict[tuple[str, str], str] = field(default_factory=dict)
    kept: dict[str, Kept] = field(default_factory=dict)


def brand_drawings(brand: tokens.Brand) -> Drawings:
    """The drawings of the brand and of each brand it builds on as its base, as they draw
    under it (DEC-009 points 2 to 4, DEC-034 points 1 and 4).

    Along the chain, the brand nearest the root that serves a top keeps its form. A brand
    serves a top where it holds a drawing of one of its layouts, or holds the top itself,
    whose own drawing draws each of its layouts. So each brand's drawings draw only the tops
    no brand nearer the root serves, and a drawing of any other top draws nothing, which the
    piece states (`Drawings.kept`). A drawing draws only where its `draws` names a top whose
    library its own brand names (DEC-009 point 3). A brand names component libraries alone
    (`tokens.Brand.named`), so a top a brand holds is drawn by its own drawing alone, and a
    drawing of it is the check's to fail (DEC-034 point 4). Where a brand holds two drawings of
    one layout, neither draws, and the top's own drawing does. A file that cannot be read
    draws nothing, and the check of its brand reports it."""
    chain: list[tokens.Brand] = []
    link: tokens.Brand | None = brand
    while link is not None:
        chain.append(link)
        link = link.base
    drawn = Drawings()
    serving: dict[str, str] = {}
    for link in reversed(chain):
        own, held = _served(link)
        for (top, layout_name), uses in sorted(own.items()):
            if top in serving:
                drawn.kept.update({use: Kept(top, serving[top]) for use in uses})
            elif len(uses) == 1:
                drawn.drawings[top, layout_name] = uses[0]
        for top in [*(top for top, _ in own), *held]:
            serving.setdefault(top, link.label)
    return drawn


def _served(brand: tokens.Brand) -> tuple[dict[tuple[str, str], list[str]], list[str]]:
    """What the brand's own version holds of the tops it serves: each drawing, by its use
    under the top and the layout its `draws` names, of a top whose library the brand names
    (DEC-009 point 3); and each top it holds, by its use (DEC-034 point 4)."""
    drawings: dict[tuple[str, str], list[str]] = {}
    held: list[str] = []
    for path in sorted((brand.folder / COMPONENTS).glob("*.yaml")):
        data, _ = read_component(path)
        use = f"{brand.name}/{path.stem}"
        draws = data.get(layout.DRAWS) if data is not None else None
        top = draws.get("top") if isinstance(draws, Mapping) else None
        drawn = draws.get("layout") if isinstance(draws, Mapping) else None
        if isinstance(top, str) and isinstance(drawn, str) and top.split("/")[0] in brand.named:
            drawings.setdefault((top, drawn), []).append(use)
        elif data is not None and draws is None and layout.LAYOUTS in data:
            held.append(use)
    return drawings, held


def size_key_of(combination: Mapping[str, str], axes: Mapping[str, tokens.Axis]) -> str:
    """The key over the size axes of a combination: its modes on the axes of kind `size`,
    each other axis taken at its default (DEC-004 points 2 and 3)."""
    return keys.key_of(
        {axis: mode for axis, mode in combination.items() if axes[axis].kind == "size"}, axes
    )


def size_axes(axes: Mapping[str, tokens.Axis]) -> dict[str, tokens.Axis]:
    """The axes of kind `size` among `axes`: those a component reads by a marked name
    (DEC-021 point 3)."""
    return {name: axis for name, axis in axes.items() if axis.kind == "size"}


def sizes_at(axes: Mapping[str, tokens.Axis], size_key: str) -> layout.Sizes:
    """What a scene at the key over the size axes `size_key` reads of them (DEC-021 point
    3): each size axis of `axes`, the foundations', with its modes and its default, and the
    mode the key holds on each. Raises keys.BadKey for a key `axes` do not hold."""
    sized = size_axes(axes)
    return layout.Sizes(sized, keys.parse_key(size_key, sized))


@dataclass
class _Read:
    """What a project's `Env` has read, shared by its view at each key over the size axes:
    each component by its use, and why each whose file cannot be read as one cannot; why
    each produced picture that is missing is; the records read; the font files read from
    the location's `fonts/`; the `pictures/` folder of the piece and of each library
    version, by its holder (`piece` or the library's name); and why each picture file that
    cannot be read cannot, by its holder and its name."""

    components: dict[str, dict[str, Any] | None] = field(default_factory=dict)
    unreadable: dict[str, str] = field(default_factory=dict)
    missing: dict[str, str] = field(default_factory=dict)
    records: dict[str, Mapping[str, Any]] = field(default_factory=dict)
    fonts_read: set[Path] = field(default_factory=set)
    folders: dict[str, pictures.Folder] = field(default_factory=dict)
    refused: dict[tuple[str, str], str] = field(default_factory=dict)


class ProjectEnv:
    """The `Env` the engine reads a project through: components from the locked versions
    and the piece's own folder, roles and fonts from the brand, colour families from the
    foundations' declarations, concepts from the notations the piece names, produced
    pictures from their records, picture files from the `pictures/` folder of the piece and
    of each locked version, the file the brand gives each picture role, and the lock.

    It reads each role at one key over the size axes, `size_key`, which is `default` for
    the project's own (`Project.env`). `at` gives the view that reads roles at another key,
    and shares every other read with this one.

    It keeps what the engine asked for that a check needs, across every key: why a produced
    picture is missing (`missing`), the records read (`records`), the font files read from
    the location's `fonts/` (`fonts_read`), and why a picture file a drawn image names or
    the brand gives a picture role it shows cannot be read (`refused`)."""

    def __init__(
        self, project: Project, size_key: str = keys.DEFAULT_KEY, read: _Read | None = None
    ) -> None:
        self._project = project
        self.size_key = size_key
        self._combination = keys.parse_key(size_key, project.brand.axes)
        self._read = _Read() if read is None else read

    def at(self, size_key: str) -> ProjectEnv:
        """The view that reads each role at the key over the size axes `size_key`, sharing
        every other read with this one, so a file is read once whatever the key."""
        return ProjectEnv(self._project, size_key, self._read)

    @property
    def missing(self) -> dict[str, str]:
        return self._read.missing

    @property
    def records(self) -> dict[str, Mapping[str, Any]]:
        return self._read.records

    @property
    def fonts_read(self) -> set[Path]:
        return self._read.fonts_read

    @property
    def refused(self) -> dict[tuple[str, str], str]:
        return self._read.refused

    def component(self, use: str) -> dict:
        read = self._read
        if use not in read.components:
            read.components[use] = self._read_component(use)
        if use in read.unreadable:
            raise UnreadableComponent(use, read.unreadable[use])
        found = read.components[use]
        if found is None:
            raise KeyError(use)
        return found

    def _read_component(self, use: str) -> dict[str, Any] | None:
        """A component's data; None where there is none, and where its file is present and
        cannot be read as one, why kept in `unreadable`."""
        data, why = read_component(self.component_path(use))
        if why is not None:
            self._read.unreadable[use] = why
        return data

    def component_path(self, use: str) -> Path | None:
        """The file of a component, by its use; None where the lock names no version of its
        library."""
        try:
            library, name = split_use(use)
        except ValueError:
            return None
        project = self._project
        if library == PIECE:
            return project.piece.folder / COMPONENTS / f"{name}.yaml"
        version = project.lock.get(library)
        if version is None:
            return None
        folder = project.root / project.location / FOLDER / library / version
        return folder / COMPONENTS / f"{name}.yaml"

    def role(self, token_path: str) -> dict:
        """The role's value under the brand, at the view's key over the size axes, every
        value axis at its default. Raises tokens.RoleWithoutValue for a role of the scope the
        brand leaves with none, and tokens.UnknownRole for a path no role holds; both are
        KeyErrors, as the engine reads them."""
        return self._project.brand.resolve(token_path, self._combination)

    def picture_role(self, token_path: str) -> pictures.Picture | None:
        """The picture the brand gives the picture role at `token_path` at the view's key
        over the size axes, every value axis at its default, as read; None where it gives
        none, or its file cannot be read, which is the brand's own finding. Within that key,
        each file the role takes in a combination the piece names that cannot be read is
        kept in `refused`, so an export refuses it. Raises KeyError for a path no role
        holds, and ValueError for a role of another type (DEC-025 point 4)."""
        brand = self._project.brand
        kind = brand.type_of(token_path)
        if kind != tokens.PICTURE:
            raise ValueError(f"the role @{token_path} is a {kind}, not a picture")
        named = f"the picture role `{token_path}`"
        project = self._project
        for key, combination in zip(project.keys, project.combinations, strict=True):
            given = brand.given(token_path, combination)
            if given is None or project.size_key(key) != self.size_key:
                continue
            judged = brand.picture_of(given, named)
            if judged.picture is None:
                said = [f"{f.message} — {f.fix}" if f.fix else f.message for f in judged.findings]
                self.refused[given.brand, given.name] = "; ".join(said) or "it cannot be read"
        given = brand.given(token_path, self._combination)
        return None if given is None else brand.picture_of(given, named).picture

    def font_file(self, family: str) -> Path:
        path = self._project.brand.font_file(family)
        fonts = self._project.root / self._project.location / FONTS
        if path.parent == fonts:
            self.fonts_read.add(path)
        return path

    def picture(self, output: str) -> PictureInfo:
        if output in self.missing:
            raise KeyError(output)
        if output not in self.records:
            try:
                self.records[output] = _read_record(self._project.piece, output)
            except _Missing as exc:
                self.missing[output] = str(exc)
                raise KeyError(output) from exc
        return _picture_info(self.records[output])

    def picture_file(self, holder: str, name: object, *, named: str, where: str) -> pictures.Judged:
        judged = self._folder(holder).judge(name, named=named, file="", where=where)
        if judged.picture is None:
            said = [f"{f.message} — {f.fix}" if f.fix else f.message for f in judged.findings]
            self.refused[holder, str(name)] = "; ".join(said) or "it cannot be read"
        return judged

    def _folder(self, holder: str) -> pictures.Folder:
        """The `pictures/` folder of the piece, where `holder` is `piece`, else of the version
        of the library `holder` the lock names: its findings lie in the piece, or in that
        version (DEC-025 point 9)."""
        folders = self._read.folders
        if holder not in folders:
            piece = self._project.piece
            walked = self._project.held.walked
            if holder == PIECE:
                folders[holder] = pictures.Folder(
                    piece.folder, "", "the piece", final=piece.final, walked=walked
                )
            else:
                label = self._project.label(holder)
                folder = self._project.root / self._project.location / FOLDER / holder
                folders[holder] = pictures.Folder(
                    folder / self._project.lock[holder],
                    "",
                    f"the version {label}",
                    label,
                    walked=walked,
                )
        return folders[holder]

    def handed(self, scene: Mapping[str, Any], key: str) -> dict[str, seam.Shown]:
        """What a renderer is handed to draw `scene` (`Scene.to_dict()`) in the combination
        `key`: the picture each of its images shows there, by the image's trace id (DEC-025
        point 7). A produced output shows the variant its record maps `key` to, a PNG; a
        picture file shows itself, of the kind its bytes are; a picture role shows the file
        the document of values gives it in `key`, in the version of the brand that holds it.
        An image of an output whose record maps `key` to no variant, of a picture file that
        cannot be read, or of a picture role given no readable file in `key`, is left out,
        and its renderer reports the loss."""
        found = {}
        for element in _images(scene.get("children", [])):
            trace = str(element.get("id"))
            if "output" in element:
                variant = self._variant(str(element["output"]), key)
                if variant is not None:
                    found[trace] = seam.Shown(variant, seam.PNG)
            elif "file" in element:
                holder = str(element.get("library", PIECE)).partition("@")[0]
                name = str(element["file"])
                read = self._folder(holder).judge(name, named="", file="", where="").picture
                if read is not None:
                    file = self._folder(holder).holder / pictures.FOLDER / name
                    found[trace] = seam.Shown(file, read.kind)
            elif "role" in element:
                shown = self._role_file(str(element["role"]), key)
                if shown is not None:
                    found[trace] = shown
        return found

    def _role_file(self, token_path: str, key: str) -> seam.Shown | None:
        """The file the document of values gives the picture role at `token_path` in the
        combination `key`, and its kind; None where it gives none, or the file cannot be
        read (DEC-025 point 7)."""
        token = self._project.values()["tokens"].get(token_path)
        value = token["values"].get(key) if token is not None else None
        if not isinstance(value, Mapping) or value.get("library") not in self._project.lock:
            return None
        folder = self._folder(str(value["library"]))
        name = str(value["file"])
        read = folder.judge(name, named="", file="", where="").picture
        if read is None:
            return None
        return seam.Shown(folder.holder / pictures.FOLDER / name, read.kind)

    def _variant(self, output: str, key: str) -> Path | None:
        """The file of the variant of the produced output `output` that serves the
        combination `key`; None where the engine read no record of it, or its record maps
        `key` to no variant."""
        record = self.records.get(output)
        if record is None:
            return None
        combinations = record.get("combinations")
        variant = combinations.get(key) if isinstance(combinations, Mapping) else None
        entry = record["variants"].get(variant)
        if not isinstance(entry, Mapping):
            return None
        return self._project.piece.folder / PRODUCED / output / entry["file"]

    def family(self, name: str) -> dict[str, str]:
        return dict(self._project.foundations.families[name])

    def concept(self, name: str) -> str | None:
        named, _, concept = name.partition("/")
        notation = self._project.notations.get(named)
        if notation is None:
            raise UnknownConcept(
                name,
                f"the concept `{name}` comes from `{named}`, a notation the piece does not name "
                f"under `notations`",
            )
        try:
            return notation.family(concept)
        except KeyError:
            raise UnknownConcept(
                name, f"the notation {notation.label} holds no concept `{concept}`"
            ) from None

    def library_version(self, library: str) -> str:
        return self._project.lock[library]


def read_component(path: Path | None) -> tuple[dict[str, Any] | None, str | None]:
    """A component's data from its file at `path`; None where there is no such file. Where
    the file is present and cannot be read as a component, None and why. The reader names
    the file by its path on this machine, and why names it by nothing: the finding names
    it from the piece or the version, so a findings record holds where the work moves."""
    if path is None or not path.is_file():
        return None, None
    try:
        data = read_yaml(path)
    except ReadError as exc:
        return None, str(exc).removeprefix(f"{path}: ")
    if not isinstance(data, Mapping):
        return None, "it is not a mapping"
    return dict(data), None


class LibraryEnv:
    """The `Env` a library version checked alone is read through, which no piece or brand
    stands behind (DEC-008 point 1, DEC-010 point 9): components from a combination of
    library versions, such as the one `libraries.newest_of_majors` chooses, and roles from
    the declarations alone, the scope of those versions (`tokens.Scope`).

    A role's value is a stand-in of the type its declaration gives, of no magnitude: a
    length of 0 px, the number 0, or, for any other type, a mapping that holds the type
    alone. So the engine reads a component's formulas, their dimensions included, as under
    any brand that gives each role a value of its type. It computes no scene: no font,
    produced picture or concept lies behind it."""

    def __init__(self, versions: Mapping[str, Library], scope: tokens.Scope) -> None:
        self._versions = dict(versions)
        self._scope = scope
        self._components: dict[str, dict[str, Any] | None] = {}
        self._unreadable: dict[str, str] = {}
        self._folders: dict[str, pictures.Folder] = {}

    def brand_of(self, use: str) -> str | None:
        """The label of the brand, among the versions the library is checked with, that
        holds the component `use`; None where its library is none of them, or no brand."""
        version = self._versions.get(use.partition("/")[0])
        return version.label if version is not None and version.kind == "brand" else None

    def component(self, use: str) -> dict:
        if use not in self._components:
            data, why = read_component(self.component_path(use))
            self._components[use] = data
            if why is not None:
                self._unreadable[use] = why
        if use in self._unreadable:
            raise UnreadableComponent(use, self._unreadable[use])
        found = self._components[use]
        if found is None:
            raise KeyError(use)
        return found

    def component_path(self, use: str) -> Path | None:
        """The file of a component, by its use; None where the combination holds no version
        of its library, and for a piece's own component, since no piece stands behind it."""
        try:
            library, name = split_use(use)
        except ValueError:
            return None
        version = self._versions.get(library)
        if library == PIECE or version is None:
            return None
        return version.folder / COMPONENTS / f"{name}.yaml"

    def role(self, token_path: str) -> Any:
        """A stand-in of the role's declared type. Raises tokens.UnknownRole, a KeyError,
        for a path no declaration of the scope holds."""
        kind = self._scope.type_of(token_path)
        if kind == "dimension":
            return {"value": 0.0, "unit": "px"}
        if kind == "number":
            return 0.0
        return {"$type": kind}

    def picture_role(self, token_path: str) -> pictures.Picture | None:
        """None: no brand stands behind a library checked alone, so it gives no picture role
        a file. Raises tokens.UnknownRole, a KeyError, for a path no declaration of the scope
        holds, and ValueError for a role of another type."""
        kind = self._scope.type_of(token_path)
        if kind != tokens.PICTURE:
            raise ValueError(f"the role @{token_path} is a {kind}, not a picture")
        return None

    def font_file(self, family: str) -> Path:
        raise MissingFont(
            f"no brand stands behind a library checked alone, so no file measures {family!r}"
        )

    def picture(self, output: str) -> PictureInfo:
        raise KeyError(output)

    def picture_file(self, holder: str, name: object, *, named: str, where: str) -> pictures.Judged:
        """A picture file of a version among those the library is checked with, its findings
        lying in it; none of a piece, since no piece stands behind it."""
        version = self._versions.get(holder)
        if holder == PIECE or version is None:
            return pictures.Judged(None)
        if holder not in self._folders:
            label = f"{holder}@{version.version}"
            self._folders[holder] = pictures.Folder(
                version.folder, "", f"the version {label}", label
            )
        return self._folders[holder].judge(name, named=named, file="", where=where)

    def family(self, name: str) -> dict[str, str]:
        return dict(self._scope.families[name])

    def concept(self, name: str) -> str | None:
        raise UnknownConcept(name, "no piece names a notation where a library is checked alone")

    def library_version(self, library: str) -> str:
        return str(self._versions[library].version)


def held_top_findings(
    component: layout.Component | None, env: LibraryEnv, *, file: str, library: str
) -> list[Finding]:
    """The finding on `component`, a drawing in its file `file` of the version `library`,
    whose top a brand among the versions `env` reads holds (DEC-034 points 4 and 10,
    `layout.held_top_drawing_finding`); none on any other component."""
    if component is None or component.draws is None:
        return []
    holder = env.brand_of(component.draws[0])
    if holder is None:
        return []
    return [
        layout.held_top_drawing_finding(
            component.use, component.draws, holder, file=file, library=library
        )
    ]


class _Missing(Exception):
    """Why a produced picture is missing."""


def _read_record(piece: Piece, output: str) -> Mapping[str, Any]:
    """The record of the piece's produced output `output`. Raises _Missing, saying why the
    picture is missing."""
    if not is_name(output):
        raise _Missing(f"`{output}` is not the name of a produced output")
    folder = piece.folder / PRODUCED / output
    rel = piece.file(f"{PRODUCED}/{output}/{RECORD}")
    if not (folder / RECORD).is_file():
        raise _Missing(f"{rel} does not exist: the picture was never produced")
    try:
        record = read_bound(folder / RECORD, "produced-record")
        variants, points = record["variants"], record["points"]
        for key, variant in variants.items():
            file, pixels = variant["file"], variant["pixels"]
            if not isinstance(file, str) or "/" in file or not (folder / file).is_file():
                raise _Missing(f"{rel} names the variant `{key}` file `{file}`, which is missing")
            int(pixels["width"]), int(pixels["height"])
        for places in points.values():
            for place in places.values():
                float(place["x"]), float(place["y"])
    except (ReadError, FileError) as exc:
        raise _Missing(f"{rel} cannot be read: {exc}") from exc
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise _Missing(f"{rel} is not of the shape of a produced output's record") from exc
    return record


def _picture_info(record: Mapping[str, Any]) -> PictureInfo:
    """A produced output as the engine reads it, from its record."""
    return PictureInfo(
        variants={
            key: {"file": variant["file"], "pixels": dict(variant["pixels"])}
            for key, variant in record["variants"].items()
        },
        points={point: dict(places) for point, places in record["points"].items()},
    )


# --- whether versions fit the piece as its lock does --------------------------------------------


def fit(piece: Piece, held: Held) -> Fit | None:
    """The judgement of the versions a draft's lock may move to (`Fit`). None where the
    piece has no lock yet: its first lock takes the newest versions, and nothing holds them
    back (DEC-003 point 8, DEC-011 point 4)."""
    return Fit(piece, held) if piece.lock else None


class Fit:
    """The judgement a draft's render gives the search for its lock (`libraries.Judge`):
    whether a whole combination of versions fits the piece as its lock does (DEC-003 point
    8). It places the piece under the combination, in every language and at each key over
    the size axes the piece names that the combination's foundations declare, as the
    engine finds a tie's ends (`layout.place_top`), and computes no scene. Versions do not
    fit where, under them, at a key (DEC-021 point 7):

    - an item the lock places carries a key that both its component and its list declare,
      where it does not under the lock (DEC-010 point 2). The libraries of the item's
      component, and of each component above it, are implicated.
    - an end of a tie the lock draws is not found: its item is drawn other than once below
      the tie's pattern or off the tie's page, or the tie is not drawn (DEC-011 point 4).
      Every library whose component the placing read or looked for is implicated.

    So what the lock already shows holds nothing back: a clash under the lock, an end it
    does not find, and what a library it does not name yet brings. A misfit at every key
    the lock places the piece at reads as it is; one at some keys is said at each, ending
    with the key it holds at. Each component file, each produced picture's record and each
    version of the foundations' declarations is read once, across every combination judged.
    The placing under the lock, which each combination is compared with, is made at the
    first judgement."""

    def __init__(self, piece: Piece, held: Held) -> None:
        self.piece = piece
        self.held = held
        self.components: dict[Path | None, tuple[dict[str, Any] | None, str | None]] = {}
        self.pictures: dict[str, PictureInfo | str] = {}
        self.folders: dict[Path, pictures.Folder] = {}
        self.declared: dict[Path, dict[str, tokens.Axis]] = {}
        self._placed: dict[frozenset[str], _Placed] = {}
        self._lock: _Placed | None = None

    def __call__(self, versions: Mapping[str, Library]) -> list[Misfit]:
        under_lock = self._under_lock()
        if not under_lock.items and not under_lock.drawn:
            return []
        now = self._place(versions)
        by_size: dict[str, dict[str, Misfit]] = {size: {} for size in under_lock.sizes}
        for at, (said, implicates) in now.clashes.items():
            language, size, item, _ = at
            if (language, size, item) in under_lock.items and at not in under_lock.clashes:
                by_size[size].setdefault(said, Misfit("clash", said, implicates))
        for _, size, tie, end in sorted(under_lock.drawn - now.found):
            said = f"the end `{end}` of the tie `{tie}` would not be found"
            by_size[size].setdefault(said, Misfit("end", said, now.asked))
        misfits: dict[str, Misfit] = {}
        for size, found in by_size.items():
            for said, misfit in found.items():
                if all(said in other for other in by_size.values()):
                    misfits.setdefault(said, misfit)
                else:
                    named = f"{said} at `{size}`"
                    misfits.setdefault(named, replace(misfit, said=named))
        return list(misfits.values())

    def _under_lock(self) -> _Placed:
        """The piece placed under the versions its lock names that the project holds and the
        installed capability reads."""
        if self._lock is None:
            versions = {}
            for name, text in self.piece.lock.items():
                try:
                    version = Version.parse(text)
                except ValueError:
                    continue
                if self.held.unreadable(name, version) is None:
                    versions[name] = self.held.library(name, version)
            self._lock = self._place(versions)
        return self._lock

    def _place(self, versions: Mapping[str, Library]) -> _Placed:
        key = frozenset(library.label for library in versions.values())
        if key not in self._placed:
            env = _FitEnv(self, versions)
            placed = _Placed()
            asked: set[str] = set()
            sized = self._size_axes(versions)
            for combination in self._size_combinations(sized):
                size = keys.key_of(combination, sized)
                placed.sizes.append(size)
                sizes = layout.Sizes(sized, combination)
                for language in self.piece.languages:
                    ctx = layout.Context(env, language, sizes=sizes)
                    content = dict(self.piece.contents[language])
                    top = layout.place_top(ctx, self.piece.top, content)
                    asked |= ctx.asked()
                    if top is not None:
                        placed.add(language, size, top)
            placed.asked = frozenset(asked)
            self._placed[key] = placed
        return self._placed[key]

    def _size_axes(self, versions: Mapping[str, Library]) -> dict[str, tokens.Axis]:
        """The size axes the foundations among `versions` declare, read once for each
        version; none where they hold no foundations, or their declarations cannot be read,
        which their own check reports."""
        foundations = versions.get(FOUNDATIONS)
        if foundations is None:
            return {}
        path = foundations.folder / "roles.yaml"
        if path not in self.declared:
            try:
                self.declared[path] = size_axes(tokens.read_declarations(path).axes)
            except tokens.TokenError:
                self.declared[path] = {}
        return self.declared[path]

    def _size_combinations(self, sized: Mapping[str, tokens.Axis]) -> list[dict[str, str]]:
        """Each combination of the modes the piece names on the size axes `sized`, in key
        order; the one of their defaults alone where it names a mode they lack, which the
        piece's own read refuses."""
        named = {axis: modes for axis, modes in self.piece.modes.items() if axis in sized}
        try:
            return keys.combinations(named, sized)
        except keys.BadKey:
            return [{}]


@dataclass
class _Placed:
    """What placing the piece under one combination of versions shows, in every language
    and at each key over the size axes, `sizes`, in key order: each item placed, by its
    language, its key and its key path; each key an item carries that both its component
    and its list declare, in words, with the libraries it implicates; the ends of each tie
    drawn; every end found, a left-out tie's included where its item lies on the tie's
    page; and the library of each component read or looked for, at any key."""

    sizes: list[str] = field(default_factory=list)
    items: set[tuple[str, str, str]] = field(default_factory=set)
    clashes: dict[tuple[str, str, str, str], tuple[str, frozenset[str]]] = field(
        default_factory=dict
    )
    drawn: set[tuple[str, str, str, str]] = field(default_factory=set)
    found: set[tuple[str, str, str, str]] = field(default_factory=set)
    asked: frozenset[str] = frozenset()

    def add(self, language: str, size: str, top: layout.Instance) -> None:
        for each in [top, *top.below()]:
            path = _path_of(each)
            if each.is_item:
                self.items.add((language, size, path))
            if each.clashed:
                above, at = set(), each
                while at is not None:
                    above.add(at.library.partition("@")[0])
                    at = at.parent
                above.discard("")
                for key in each.clashed:
                    said = (
                        f"the item `{path}` carries `{key}`, which both its component "
                        f"`{each.component.use}` and its list declare"
                    )
                    at = (language, size, path, key)
                    self.clashes.setdefault(at, (said, frozenset(above)))
            if each.tie is not None and each.tie.ends is not None:
                for name in each.tie.ends:
                    self.drawn.add((language, size, path, name))
                    self.found.add((language, size, path, name))
            for tie in each.left_out:
                page = tie.page()
                for which, name in zip(layout.ENDS, tie.tie.ends if tie.tie else (), strict=False):
                    end = tie.ends.get(which)
                    if end is not None and page is not None and end.item.page() is page:
                        self.found.add((language, size, _path_of(tie), name))


def _path_of(instance: layout.Instance) -> str:
    """An instance by the key path in the content file of what content gave it, else by
    its trace id."""
    return instance.content_path if instance.content_path is not None else instance.trace


class _FitEnv:
    """The `Env` a combination of versions is placed through, for its fit (`Fit`):
    components from those versions and from the piece's own folder, and the piece's
    produced pictures, each read once across the combinations. No brand stands behind it,
    so a role has no value, and no concept a colour family: neither changes where an item
    is placed, or how often."""

    def __init__(self, fit: Fit, versions: Mapping[str, Library]) -> None:
        self._fit = fit
        self._versions = dict(versions)

    def component(self, use: str) -> dict:
        path = self.component_path(use)
        read = self._fit.components
        if path not in read:
            read[path] = read_component(path)
        data, why = read[path]
        if why is not None:
            raise UnreadableComponent(use, why)
        if data is None:
            raise KeyError(use)
        return data

    def component_path(self, use: str) -> Path | None:
        """The file of a component, by its use; None where the combination holds no version
        of its library."""
        try:
            library, name = split_use(use)
        except ValueError:
            return None
        if library == PIECE:
            return self._fit.piece.folder / COMPONENTS / f"{name}.yaml"
        version = self._versions.get(library)
        return None if version is None else version.folder / COMPONENTS / f"{name}.yaml"

    def role(self, token_path: str) -> dict:
        raise KeyError(token_path)

    def picture_role(self, token_path: str) -> pictures.Picture | None:
        """None: no brand stands behind the fit, so no picture role has a file."""
        return None

    def font_file(self, family: str) -> Path:
        raise MissingFont(
            f"no brand stands behind the fit of versions, so no file measures {family!r}"
        )

    def picture(self, output: str) -> PictureInfo:
        pictures = self._fit.pictures
        if output not in pictures:
            try:
                pictures[output] = _picture_info(_read_record(self._fit.piece, output))
            except _Missing as exc:
                pictures[output] = str(exc)
        found = pictures[output]
        if isinstance(found, str):
            raise KeyError(output)
        return found

    def picture_file(self, holder: str, name: object, *, named: str, where: str) -> pictures.Judged:
        """A picture file of the piece or of a version of the combination, each folder read
        once across the combinations; none of a library the combination holds no version of.
        Whether it is drawn changes no item's place, so its findings are left to the scenes."""
        if holder == PIECE:
            folder = self._fit.piece.folder
        elif holder in self._versions:
            folder = self._versions[holder].folder
        else:
            return pictures.Judged(None)
        folders = self._fit.folders
        if folder not in folders:
            folders[folder] = pictures.Folder(folder, "", "the folder")
        return folders[folder].judge(name, named=named, file="", where=where)

    def family(self, name: str) -> dict[str, str]:
        raise KeyError(name)

    def concept(self, name: str) -> str | None:
        raise UnknownConcept(name, "no notation stands behind the fit of versions")

    def library_version(self, library: str) -> str:
        return str(self._versions[library].version)


# --- drawing ------------------------------------------------------------------------------------


def colours_at(document: Mapping[str, Any], key: str) -> dict[str, Any]:
    """The value of each colour role of a values document in the combination `key`."""
    return {
        path: token["values"][key]
        for path, token in document["tokens"].items()
        if token["type"] == "color"
    }


def drawn(
    project: Project,
    results: Sequence[tuple[str, SceneResult]],
    renderer: str,
    keys: Sequence[str] | None = None,
    *,
    form: str | None = None,
) -> Iterator[tuple[str, tuple[str, ...], Any]]:
    """Each file the renderer `renderer` draws in the format `form`, its own name by default, of
    the combinations the piece names, or of those that serve one of `keys`, from the scene of
    `results` in its language that serves it, the one of its key over the size axes, in the
    order of the piece's languages and of the keys: the language, the keys the file holds, the
    first naming it, and what the renderer gives (`render`, the renderers' entry of the seam).
    A combination whose scene `results` does not hold is not drawn. A renderer is handed, for
    each combination, the picture each image of that language's scene shows there
    (`ProjectEnv.handed`).

    A format the renderer's declaration names under `holds-modes` takes its keys in one call
    for each file, grouped by the signal pairs it names there (`files_of`, DEC-023 points 1
    and 2), each key with its combination, colours and pictures. A file holds every key its
    group gives it, whichever `keys` asks for. Any other format's renderer is handed one key at
    a time."""
    declared = seam.declaration(renderer, seam.RENDERER)
    implementation = seam.implementation(renderer)
    pairs = declared.get("holds-modes", {}).get(renderer if form is None else form)
    asked = project.keys if keys is None else list(keys)
    combinations = dict(zip(project.keys, project.combinations, strict=True))
    if pairs is None:
        groups = [(key,) for key in asked]
    else:
        held = files_of(project.combinations, project.brand.axes, pairs)
        groups = [group for group in held if any(key in asked for key in group)]
    document = project.values()
    scenes = {
        (language, result.scene.size_key): result.scene.to_dict() for language, result in results
    }
    for language in dict.fromkeys(language for language, _ in results):
        for group in groups:
            scene = scenes.get((language, project.size_key(group[0])))
            if scene is None:
                continue
            if pairs is None:
                made = implementation.render(
                    scene,
                    key=group[0],
                    colours=colours_at(document, group[0]),
                    font_file=project.brand.font_file,
                    pictures=project.env.handed(scene, group[0]),
                )
            else:
                made = implementation.render(
                    scene,
                    form=renderer if form is None else form,
                    keys={key: combinations[key] for key in group},
                    colours={key: colours_at(document, key) for key in group},
                    font_file=project.brand.font_file,
                    pictures={key: project.env.handed(scene, key) for key in group},
                )
            yield language, group, made


def _images(elements: Sequence[Mapping[str, Any]]) -> Iterator[Mapping[str, Any]]:
    """Each image among `elements` and the groups under them, in drawing order."""
    for element in elements:
        if element.get("type") == "image":
            yield element
        yield from _images(element.get("children", []))


def files_of(
    combinations: Sequence[Mapping[str, str]],
    axes: Mapping[str, tokens.Axis],
    pairs: Mapping[str, Mapping[str, Any]],
) -> list[tuple[str, ...]]:
    """The keys of `combinations`, grouped by the file of a format that holds modes and reads the
    signal pairs `pairs`, as a renderer's declaration names them (DEC-023 point 1). Combinations
    share a file where they differ only in modes that `pairs` pairs with a reader's signal, on
    axes of kind `value`. So a file serves one key over the size axes, and any other mode takes
    a file of its own. Each file's keys come in key order, the first naming it, and the files
    in the order of their first keys."""
    shared: dict[tuple[tuple[str, str | None], ...], list[str]] = {}
    for combination in combinations:
        mark = tuple(
            (axis, None if _paired(axis, mode, axes, pairs) else mode)
            for axis, mode in sorted(combination.items())
        )
        shared.setdefault(mark, []).append(keys.key_of(combination, axes))
    held = [tuple(sorted(group, key=keys.key_order)) for group in shared.values()]
    return sorted(held, key=lambda group: keys.key_order(group[0]))


def _paired(
    axis: str, mode: str, axes: Mapping[str, tokens.Axis], pairs: Mapping[str, Mapping[str, Any]]
) -> bool:
    """Whether `mode` of `axis` pairs with a reader's signal: the axis is a value axis, and the
    pairs name the mode. A size axis is the whole page's, so it never shares a file."""
    return axes[axis].kind != "size" and mode in pairs.get(axis, {}).get("pairs", {})


def preview_files(
    piece: str, language: str, key: str, pages: Sequence[Any]
) -> Iterator[tuple[str, str]]:
    """Each page a renderer drew of a scene, as the name of its preview and its text."""
    for index, page in enumerate(pages, start=1):
        number = f".{index}" if len(pages) > 1 else ""
        yield f"{piece}.{language}.{key}{number}.svg", page.svg


# --- the inputs of a fingerprint, worked out from the current files -----------------------------


def findings_key_sources(
    root: Path,
    held: Held,
    piece: Piece,
    lock: Mapping[str, str],
    fonts: Sequence[Path],
) -> dict[str, Any]:
    """What `fingerprint.findings_key_inputs` and `export_inputs` read, form 1: the piece's
    files as git sees them, every file of each locked version the project holds, and the
    fonts of the location's `fonts/` that were read."""
    files = [root / rel for rel in listed_files(root, piece.rel)]
    versions = {}
    for library, text in lock.items():
        try:
            version = Version.parse(text)
        except ValueError:
            continue
        folder = held.folders.get(library, {}).get(version)
        if folder is not None:
            versions[library] = (text, folder, held.files(library, version))
    return {"piece": piece.folder, "files": files, "versions": versions, "fonts": list(fonts)}


def recorded_fonts(root: Path, location: str, recorded: Mapping[str, Any]) -> list[Path]:
    """The fonts of the location's `fonts/` whose hashes a fingerprint names, as they lie
    now: a font named and no longer held is left out, so the fingerprint no longer
    verifies."""
    wanted = {
        entry["font"]
        for entry in recorded.get("inputs") or []
        if isinstance(entry, Mapping) and isinstance(entry.get("font"), str)
    }
    folder = root / location / FONTS
    if not wanted or not folder.is_dir():
        return []
    return sorted(
        path
        for path in folder.iterdir()
        if path.is_file() and not path.is_symlink() and sha256(path.read_bytes()) in wanted
    )


# --- writing a record ---------------------------------------------------------------------------


def yaml_text(data: Mapping[str, Any], header: str) -> str:
    """A file a command writes whole: `header`, a comment of `# ` lines, then `data` as
    block YAML, set apart by a blank line (`records.text`)."""
    return records.text(data, header.splitlines())


def writable(root: Path, path: Path) -> None:
    """Raise Refused where a command could not write `path` whole: it, or a folder between
    it and `root`, is a link. A command checks each file it writes before its first write."""
    try:
        refuse_links(root, path)
    except FileError as exc:
        raise Refused(str(exc)) from exc
