"""A library version read in full (visual-communication DEC-014 point 1): the one routine
that reads a version as a whole, for the capability's own checks of the versions it ships
(DEC-013 point 6) and for the release's comparison of two versions (`comparison`). The
release of a project's own library and the fetch of a version from another repository read
a version through it too, once they are built.

`read` takes a version a location holds (`libraries.Held`), and reads it with the versions
it is checked with: the newest version held of each major it builds on, and of each major
those build on (`libraries.newest_of_majors`).

- **Its files.** Each file of the capability's format in the version, against its binding
  and its schema (`file_findings`). The core's data validation reads no file under
  `.pkit/`, so a version the capability ships meets its schemas here alone.
- **Read by the engine.** The foundations' declarations and the version's own roles and
  its components' tokens, the scope of the versions it is read with (`tokens.read_scope`).
  Each of its components, the file of each under `components/`, through the environment
  of a library checked alone, which no piece or brand stands behind
  (`pipeline.LibraryEnv`), a switch or a `when` by a size against the size axes of the
  foundations it is read with, and each token it declares that its file reads nowhere
  (`layout.unread_token_findings`, DEC-035 point 9). A component of a library that is no
  brand that declares `draws` (`layout.held_drawing_finding`), a brand's drawing read as
  one, a drawing of a top a brand holds (`pipeline.held_top_findings`), and a top's own
  drawing of a layout that shows a field by no part named after it
  (`layout.own_drawing_findings`, DEC-034 points 1, 4, 5 and 10). A brand's components are
  read as a component library's are, and the brand over its base,
  its tokens and its fonts opened as the engine opens them, with the facts its version
  states (`tokens.Brand.facts`) and what it shows of the forms it draws
  (`pipeline.brand_findings`, DEC-009 point 9). A notation against the
  foundations' colour families. Each picture file the version holds in `pictures/`, read
  as the engine reads it (`pictures.Folder.read`, DEC-025 point 9), whether or not anything
  names it, and each name an image of its components gives by `file`, found there as the
  engine finds it (`pictures.Folder.judge`). It computes no scene.

What it reads is kept, beside what it finds (`FullRead`): the comparison reads the model of
each component, the scope and the brand from it. Each finding lies in the version. A version
the installed capability cannot read, or that cannot be read with its bases, is one finding
(`library-unreadable`, `alone-majors`, `alone-missing`), and leaves the rest unread.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from _lib import files, layout, libraries, notations, pictures, reading, tokens
from _lib import pipeline as pl
from _lib.findings import FAILS, Finding

#: The label of a file of the capability's format that its schema refuses.
SCHEMA_REFUSED = "schema-refused"


@dataclass(frozen=True)
class FullRead:
    """A library version read in full.

    - `name`, `version`: the version read; `label`, `<name>@<version>`.
    - `library`: its `library.yaml`, read; None where the engine could not read it with
      its bases, which `findings` says.
    - `versions`: the versions it was read with, by name, itself included.
    - `scope`: the roles of those versions (`tokens.Scope`); None where it could not be
      read.
    - `components`: each component of a component library or a brand, by its name, as the engine
      reads it (`layout.Component`); `data`, the mapping its file holds; `unread`, each
      component whose file the engine cannot read.
    - `brand`: a brand, read over its base; None for another kind, or where it could not
      be read.
    - `findings`: what the read found in the version, its files' first.
    """

    name: str
    version: libraries.Version
    library: libraries.Library | None = None
    versions: Mapping[str, libraries.Library] = field(default_factory=dict)
    scope: tokens.Scope | None = None
    components: Mapping[str, layout.Component] = field(default_factory=dict)
    data: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    unread: tuple[str, ...] = ()
    brand: tokens.Brand | None = None
    findings: tuple[Finding, ...] = ()

    @property
    def label(self) -> str:
        return f"{self.name}@{self.version}"


def read(held: libraries.Held, name: str, version: libraries.Version) -> FullRead:
    """The version `name@version` the location `held` holds, read in full: each of its files
    against its schema, then read by the engine with the versions it is checked with."""
    folder = held.root / held.location / libraries.FOLDER / name / str(version)
    found = file_findings(folder, held.files(name, version), f"{name}@{version}", held.root)
    engine = _engine(held, name, version)
    return replace(engine, findings=(*found, *engine.findings))


def file_findings(folder: Path, files_: Sequence[Path], label: str, root: Path) -> list[Finding]:
    """Each file of the capability's format among `files_`, the files of the version folder
    `folder`, against its binding and its schema."""
    found = []
    for path in files_:
        kind = libraries.kind_within(path.relative_to(folder).parts)
        if kind is not None:
            found.extend(shape_findings(path, kind, label, root))
    return found


def shape_findings(path: Path, kind: str, label: str, root: Path) -> list[Finding]:
    """A file of `kind` against its binding and its schema, the findings naming it relative
    to `root`, and lying in the version `label`, or in none where it is ""."""
    shown = path.relative_to(root).as_posix()
    try:
        data = reading.read_yaml(path)
    except reading.ReadError as exc:
        return [Finding("file-unreadable", FAILS, str(exc), file=shown, library=label)]
    problem = files.binding_problem(data, kind)
    if problem is not None:
        message = f"a file of the capability's format {problem}"
        return [Finding("binding", FAILS, message, file=shown, library=label)]
    return [
        Finding(
            SCHEMA_REFUSED,
            FAILS,
            f"the schema `{kind}` refuses it at {refused}",
            file=shown,
            library=label,
        )
        for refused in files.shape_problems(data, kind)
    ]


def _engine(held: libraries.Held, name: str, version: libraries.Version) -> FullRead:
    """What the engine reads of the version, and finds in it."""
    label = f"{name}@{version}"
    file = f"{held.location}/{libraries.FOLDER}/{name}/{version}/library.yaml"
    unreadable = FullRead(name, version)
    why = held.unreadable(name, version)
    if why is not None:
        message = f"the engine cannot read {label}: {why}"
        finding = Finding("library-unreadable", FAILS, message, file=file, library=label)
        return replace(unreadable, findings=(finding,))
    library = held.library(name, version)
    try:
        chosen = libraries.newest_of_majors(held, library)
    except libraries.LockRefused as exc:
        code = "alone-majors" if isinstance(exc, libraries.MajorsConflict) else "alone-missing"
        message = f"{label} cannot be read with its bases: {exc}"
        finding = Finding(code, FAILS, message, file=file, library=label)
        return replace(unreadable, findings=(finding,))
    folders = {other.name: other.folder for other in chosen.values()}
    try:
        scope = tokens.read_scope(folders, root=held.root)
    except tokens.TokenError as exc:
        own = tuple(finding for finding in exc.findings if finding.library == label)
        return replace(unreadable, findings=own)
    found: list[Finding] = list(scope.findings_of(name))
    components: dict[str, layout.Component] = {}
    data: dict[str, Mapping[str, Any]] = {}
    unread: list[str] = []
    brand = None
    shown = f"{library.folder.relative_to(held.root).as_posix()}/"
    reader = pictures.Folder(library.folder, shown, label, label)
    env = pl.LibraryEnv(chosen, scope)
    # A switch or a `when` by a size reads the foundations' size axes; nothing is placed, so
    # no mode is read (DEC-021 point 7).
    ctx = layout.Context(env, "", sizes=layout.Sizes(pl.size_axes(scope.axes)))
    if library.kind in ("components", "brand"):
        for path in held.files(name, version):
            if path.parent != library.folder / pl.COMPONENTS or path.suffix != ".yaml":
                continue
            use = f"{name}/{path.stem}"
            component = ctx.component(use)
            if component is None:
                unread.append(path.stem)
                continue
            components[path.stem] = component
            data[path.stem] = env.component(use)
            file = path.relative_to(held.root).as_posix()
            found.extend(layout.unread_token_findings(component, file=file, library=label))
            # Only a brand's component draws a layout, and none a top a brand holds (DEC-034
            # points 1 and 4).
            if component.draws is not None and library.kind != "brand":
                found.append(layout.held_drawing_finding(use, file=file, library=label))
            else:
                found.extend(pl.held_top_findings(component, env, file=file, library=label))
            if component.top:
                found.extend(layout.own_drawing_findings(component, file=file, library=label))
        found.extend(_named_findings(reader, components, shown))
    if library.kind == "brand":
        fonts = held.root / held.location / pl.FONTS
        try:
            brand = tokens.read_brand(
                library.folder, scope, fonts=fonts, root=held.root, locked=folders
            )
            found.extend((*brand.findings, *brand.facts))
            # The forms it draws, over its base, as its check alone judges them (DEC-009
            # point 9), before the engine's findings, of which they may take one back.
            found.extend(pl.brand_findings(brand, ctx, env, shown=shown))
        except tokens.TokenError as exc:
            found.extend(exc.findings)
    found.extend(ctx.findings)
    if library.kind == "notation":
        notation = notations.read_notation(library.folder, scope.families, root=held.root)
        found.extend(notation.findings)
    found.extend(_picture_findings(held, library, reader))
    return FullRead(
        name,
        version,
        library=library,
        versions=chosen,
        scope=scope,
        components=components,
        data=data,
        unread=tuple(unread),
        brand=brand,
        findings=tuple(_once(finding for finding in found if finding.library == label)),
    )


def _named_findings(
    reader: pictures.Folder, components: Mapping[str, layout.Component], shown: str
) -> list[Finding]:
    """What each name an image of the version's components gives by `file` finds in the
    version's `pictures/`, as the engine finds it where the image is drawn (DEC-025 points 3
    and 9): a finding on the name at the part, in the component's file, and one on the file
    at the file. A component that names no picture file finds nothing."""
    found = []
    for stem, component in sorted(components.items()):
        for part in component.parts.values():
            if part.kind != "image" or "file" not in part.props:
                continue
            judged = reader.judge(
                part.props["file"],
                named=f"{component.use}: the image `{part.name}`",
                file=f"{shown}{pl.COMPONENTS}/{stem}.yaml",
                where=f"parts.{part.name}.image.file",
            )
            found.extend(judged.findings)
    return found


def _picture_findings(
    held: libraries.Held, library: libraries.Library, reader: pictures.Folder
) -> list[Finding]:
    """What reading each picture file the version holds finds: each file directly in its
    `pictures/` folder that git lists, under a bare name, as the engine reads it."""
    folder = library.folder / pictures.FOLDER
    names = [
        path.name
        for path in held.files(library.name, library.version)
        if path.parent == folder and pictures.is_bare_name(path.name)
    ]
    return [finding for name in names for finding in reader.read(name).findings]


def _once(found: Iterable[Finding]) -> list[Finding]:
    """Each finding once: a picture file a brand's role names is judged by the brand too."""
    out: list[Finding] = []
    for finding in found:
        if finding not in out:
            out.append(finding)
    return out
