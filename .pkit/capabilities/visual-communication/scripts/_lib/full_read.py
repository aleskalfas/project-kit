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
- **Read by the engine.** The foundations' declarations and the version's own roles, the
  scope of the versions it is read with (`tokens.read_scope`). Each of its components, the
  file of each under `components/`, through the environment of a library checked alone,
  which no piece or brand stands behind (`pipeline.LibraryEnv`), a switch or a `when` by a
  size against the size axes of the foundations it is read with. A brand over its base,
  its tokens and its fonts opened as the engine opens them, with the facts its version
  states (`tokens.Brand.facts`). A notation against the
  foundations' colour families. Each picture file the version holds in `pictures/`, read
  as the engine reads it (`pictures.Folder.read`, DEC-025 point 9), whether or not anything
  names it. It computes no scene.

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
    - `components`: each component of a component library, by its name, as the engine
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
    if library.kind == "components":
        env = pl.LibraryEnv(chosen, scope)
        # A switch or a `when` by a size reads the foundations' size axes; nothing is placed,
        # so no mode is read (DEC-021 point 7).
        ctx = layout.Context(env, "", sizes=layout.Sizes(pl.size_axes(scope.axes)))
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
        found.extend(ctx.findings)
    elif library.kind == "brand":
        fonts = held.root / held.location / pl.FONTS
        try:
            brand = tokens.read_brand(
                library.folder, scope, fonts=fonts, root=held.root, locked=folders
            )
            found.extend((*brand.findings, *brand.facts))
        except tokens.TokenError as exc:
            found.extend(exc.findings)
    elif library.kind == "notation":
        notation = notations.read_notation(library.folder, scope.families, root=held.root)
        found.extend(notation.findings)
    found.extend(_picture_findings(held, library, label))
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


def _picture_findings(
    held: libraries.Held, library: libraries.Library, label: str
) -> list[Finding]:
    """What reading each picture file the version holds finds: each file directly in its
    `pictures/` folder that git lists, under a bare name, as the engine reads it."""
    folder = library.folder / pictures.FOLDER
    shown = f"{library.folder.relative_to(held.root).as_posix()}/"
    reader = pictures.Folder(library.folder, shown, label, label)
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
