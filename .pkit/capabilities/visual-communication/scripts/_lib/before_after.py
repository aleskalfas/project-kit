"""A before-and-after: what a piece draws, or a declaration's writer writes, on each side of a
change to the versions its lock names (visual-communication DEC-003 point 8, DEC-005 point 7,
DEC-013 point 5).

- **A side** (`Side`) is what one set of versions gives: each preview of a piece's scenes, or
  the code of a declaration; where they give none, why. A piece's side also says which
  produced pictures it drew stale or could not find (`drawing`), which it draws as they lie
  and never makes again (DEC-019 point 5).
- **Each side is read from a location of its own,** which it builds in the clone's local
  folder (`_built`): the piece or the declaration, the location's fonts, and each version the
  lock names, as the project holds it or, for a version `sources` gives, as the capability
  ships it. So the pipeline and the code writer read it as they read any location, and no
  file of the project is written to see what a change would do. It is removed once read.
- **Any change to a lock's versions** takes the same two calls. A copy that changes under one
  number gives the same lock on each side, with `sources` on one (`drawing`, `writing`). A
  lock that moves gives the two locks. `keep` lays a piece's two sides out under `FOLDER`,
  each file named as its preview.
- **The command that asks for it by name** takes a piece's two sides through the same calls
  (`looks`, DEC-019 point 5).
- **What a run of `pkit visual add` shows** (`shown`), of each lock that holds a copy it left:
  the piece's scenes drawn both ways, or the difference in the code its writer writes. A side
  that cannot be read stops nothing: the run says why, and goes on.
"""

from __future__ import annotations

import contextlib
import difflib
import shutil
import tempfile
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path

from _lib import code, copies, exports, tokens
from _lib import pipeline as pl
from _lib.env import MissingFont
from _lib.files import Change, FileError, refuse_links
from _lib.findings import FAILS
from _lib.libraries import FOLDER as LIBRARY_FOLDER
from _lib.libraries import Held, Version
from _lib.location import walked
from _lib.names import is_name
from _lib.root import LOCAL
from _lib.scene import SceneResult

#: Where each piece's before-and-after lies, relative to the project root, in a folder of
#: its own.
FOLDER = f"{LOCAL}/before-after"

#: The piece's folders under `FOLDER`: its scenes as its lock draws them now, and with the
#: change.
BEFORE = "before"
AFTER = "after"

#: What keeps a side from being read, each naming what to mend.
_FAULTS = (pl.Refused, tokens.TokenError, MissingFont, code.CodeRefused)


@dataclass(frozen=True)
class Side:
    """What one set of versions gives: each file's name and text; where it gives none, why;
    and each produced picture a piece's side read that is stale or missing, with what
    changed or why it is missing."""

    files: Mapping[str, str] = field(default_factory=dict)
    why: str = ""
    stale: Mapping[str, Sequence[str]] = field(default_factory=dict)


def drawing(
    root: Path,
    location: str,
    name: str,
    lock: Mapping[str, str],
    sources: Sequence[copies.Source] = (),
) -> Side:
    """The previews of the piece `name` under `lock`, each of `sources` in place of the
    project's copy of its version, and each picture they read that is stale or missing
    (`_stale`). A scene that holds no page is a side that cannot be drawn
    (`_refuse_no_page`)."""
    own = _files(root, f"{location}/{pl.PIECES}/{name}", f"{location}/{pl.FONTS}")

    def previews(built: Path) -> Side:
        piece = pl.read_piece(built, location, name)
        project = pl.Project(piece, lock, Held(built, location, walked=True))
        results = project.scenes()
        _refuse_no_page(results)
        found: dict[str, str] = {}
        for language, key, drawn in pl.drawn(project, results, "svg"):
            found.update(pl.preview_files(name, language, key, drawn.pages))
        return Side(found, stale=_stale(project, built))

    return _read(root, {**own, **_version_files(root, location, lock, sources)}, previews)


def writing(
    root: Path,
    location: str,
    name: str,
    lock: Mapping[str, str],
    sources: Sequence[copies.Source] = (),
) -> Side:
    """The code the declaration `name`'s writer writes under `lock`, each of `sources` in
    place of the project's copy of its version, by the path the code goes to."""
    file = code.file_of(location, name)
    own = {file: root / file, **_files(root, f"{location}/{pl.FONTS}")}

    def written(built: Path) -> Side:
        declaration = replace(code.read(built, location, name), lock=dict(lock))
        planned = code.plan(built, location, declaration, Held(built, location, walked=True))
        return Side({declaration.out: code.text_of(planned)})

    return _read(root, {**own, **_version_files(root, location, lock, sources)}, written)


def keep(change: Change, name: str, before: Side, after: Side) -> None:
    """Add to `change` the two sides of the piece `name`: each preview in the side's folder
    under `FOLDER`, a file left there from before removed. Raises Refused where a file could
    not be written whole, adding nothing."""
    folders = {side: change.root / FOLDER / name / side for side in (BEFORE, AFTER)}
    pairs = ((folders[BEFORE], before), (folders[AFTER], after))
    for folder, side in pairs:
        for file in side.files:
            pl.writable(change.root, folder / file)
    for folder, side in pairs:
        for file, text in side.files.items():
            change.write(folder / file, text.encode("utf-8"))
        if folder.is_dir():
            for old in sorted(folder.glob("*.svg")):
                if old.name not in side.files:
                    change.remove(old)


def differing(before: Side, after: Side) -> list[str]:
    """Each file the two sides do not hold alike, in name order."""
    every = sorted({*before.files, *after.files})
    return [file for file in every if before.files.get(file) != after.files.get(file)]


def both_ways(name: str, before: Side, after: Side) -> str:
    """The two sides of the piece `name`, as `keep` lays them out, in words."""
    count, total = len(differing(before, after)), len({*before.files, *after.files})
    verb = "differs" if count == 1 else "differ"
    return f"drawn both ways in {FOLDER}/{name}/: {count} of {total} files {verb}"


def shown(
    root: Path, location: str, planned: copies.Plan, change: Change
) -> dict[tuple[str, str], tuple[str, ...]]:
    """What a run shows of each lock that holds a copy it left and that it can read, in
    words, by the lock's key. A piece's two sides are added to `change`."""
    found: dict[tuple[str, str], tuple[str, ...]] = {}
    for each in planned.copies:
        if not isinstance(each, copies.Left) or each.source is None:
            continue
        for lock in each.locks:
            if lock.versions is not None:
                show = _piece if lock.kind == copies.PIECE else _declaration
                found[lock.key] = show(root, location, lock, each.source, change)
    return found


def _piece(
    root: Path, location: str, lock: copies.Lock, source: copies.Source, change: Change
) -> tuple[str, ...]:
    """A piece's scenes drawn both ways, kept in `change`, in words."""
    versions = lock.versions or {}
    before = drawing(root, location, lock.name, versions)
    after = drawing(root, location, lock.name, versions, [source])
    why = _why(before, after)
    if why:
        return (f"no before-and-after: {why}",)
    try:
        keep(change, lock.name, before, after)
    except pl.Refused as exc:
        return (f"no before-and-after: {exc}",)
    return (both_ways(lock.name, before, after),)


def _declaration(
    root: Path, location: str, lock: copies.Lock, source: copies.Source, _change: Change
) -> tuple[str, ...]:
    """The difference in the code a declaration's writer writes, in words."""
    versions = lock.versions or {}
    before = writing(root, location, lock.name, versions)
    after = writing(root, location, lock.name, versions, [source])
    why = _why(before, after)
    if why:
        return (f"no before-and-after: {why}",)
    if not differing(before, after):
        return ("its writer writes the same code with what the capability ships",)
    (out, was), now = next(iter(before.files.items())), next(iter(after.files.values()))
    return (
        "its writer writes other code with what the capability ships:",
        *difflib.unified_diff(
            was.splitlines(),
            now.splitlines(),
            f"{out}, with the copy as it is",
            f"{out}, with what the capability ships",
            lineterm="",
        ),
    )


def _why(before: Side, after: Side) -> str:
    """Why either side cannot be read, in words, said once where it is one fault; empty where
    both can."""
    if before.why == after.why:
        return before.why
    said = [
        f"{where}, {side.why}"
        for where, side in (
            ("with the copy as it is", before),
            ("with what the capability ships", after),
        )
        if side.why
    ]
    return "; ".join(said)


def _stale(project: pl.Project, built: Path) -> dict[str, list[str]]:
    """Each produced picture the project's scenes read that is stale under its lock, with
    what changed, and each that is missing, with why. A picture's inputs are read under the
    lock of the piece's own file, so that file takes the side's first, in the location
    `built`, which is the side's alone."""
    if project.env.records:
        pl.write_lock(project.piece, project.lock)
    stale = {
        output: [change.replace(f"{built}/", "") for change in changes]
        for output, changes in exports.stale_outputs(project).items()
    }
    return {**stale, **{output: [why] for output, why in project.env.missing.items()}}


def _refuse_no_page(results: Sequence[tuple[str, SceneResult]]) -> None:
    """Raises Refused where a scene holds no page, which the engine reports as findings and
    the renderer draws as no file: naming each such language, and what failed in it, each
    reason once."""
    blank = [(language, result) for language, result in results if not result.scene.pages]
    if not blank:
        return
    languages = ", ".join(f"`{language}`" for language, _ in blank)
    failed = [
        finding.message
        for _, result in blank
        for finding in result.findings
        if finding.level == FAILS
    ]
    why = "; ".join(dict.fromkeys(failed))
    raise pl.Refused(f"the piece draws no page in {languages}{f': {why}' if why else ''}")


def _files(root: Path, *folders: str) -> dict[str, Path]:
    """Each file of `folders` as it lies, by its path relative to `root`."""
    return {rel: root / rel for folder in folders for rel in walked(root, folder)}


def _version_files(
    root: Path, location: str, lock: Mapping[str, str], sources: Sequence[copies.Source]
) -> dict[str, Path]:
    """Each file of the versions `lock` names, by its path relative to `root`: those of a
    version `sources` gives from what the capability ships, each other as the project holds
    it. A lock entry that spells no version is left to `Project` to refuse."""
    given = {(source.name, str(source.version)): source for source in sources}
    found: dict[str, Path] = {}
    for library, version in lock.items():
        folder = f"{location}/{LIBRARY_FOLDER}/{library}/{version}"
        source = given.get((library, version))
        if source is not None:
            found.update({f"{folder}/{rel}": source.folder / rel for rel in source.files})
        elif _spells_version(library, version):
            found.update(_files(root, folder))
    return found


def _spells_version(library: str, version: str) -> bool:
    """Whether a lock entry spells a library at a version, and so a folder of the location."""
    try:
        Version.parse(version)
    except ValueError:
        return False
    return is_name(library)


def _read(root: Path, files: Mapping[str, Path], read: Callable[[Path], Side]) -> Side:
    """What `read` gives of a location holding `files`, or why it gives nothing, the location
    named as the project's. Nothing of the location is left."""
    try:
        with _built(root, files) as built:
            try:
                return read(built)
            except _FAULTS as exc:
                return Side(why=str(exc).replace(f"{built}/", ""))
    except (FileError, OSError) as exc:
        return Side(why=str(exc))


@contextlib.contextmanager
def _built(root: Path, files: Mapping[str, Path]) -> Iterator[Path]:
    """A project root of its own in the clone's local folder, holding each of `files` at its
    path, and removed on leaving. Git ignores that folder, so a reader lists its files as
    they lie (`Held`). Raises FileError where `FOLDER` is reached through a link, and
    OSError where a file cannot be copied."""
    top = root / FOLDER
    refuse_links(root, top)
    top.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=top, prefix=".location.") as made:
        for rel, source in files.items():
            target = Path(made) / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        yield Path(made)
