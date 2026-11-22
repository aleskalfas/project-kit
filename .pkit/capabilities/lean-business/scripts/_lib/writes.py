"""Every write of an idea's files, alike: built, held, then written, and undone where the
move after it is refused (lean-business DEC-001 point 3; DEC-002 points 1 and 14).

- **Where it goes** (`for_writing`). A command writes into the location the capability's
  configuration records. Until one is recorded, it writes into the default, `lean-business/`,
  and its write records it, with no question asked: the location is read as the default
  until then, so the value recorded is the one already in use, and running the command is
  the consent (DEC-002 point 1; COR-049 point 5). Where the default folder holds files of
  another kind, or the rules refuse it, the command records nothing and names
  `set-location`. Any first write may create the idea's folder.
- **Built** (`Files`). A command reads each file it changes round trip (`editing`), and
  holds the text of each file as it would stand, and the configuration's where the write
  records the location.
- **Held** (`hold`). Before anything is written, the location's files are copied twice
  into a folder of their own, once as they stand and once as the write would leave them.
  Where the write records the location, both copies take the configuration as the write
  leaves it, so the check reads the same files in each, and a write that records where
  files already lie adds none of their errors. Each copy is held to the capability's check
  (`checks`) and to the backbone's data validation, `pkit data validate`, which holds each
  file to its schema and resolves the references and the ids between them (COR-023,
  COR-029). The findings of the two are
  compared. A write that adds an error is refused, and nothing is written. An error already
  in the files is named and refuses nothing, so a file broken by hand never freezes the
  commands on it. A warning the write adds is named.
- **Written** (`commit`). Each file is written whole, beside its place first and then moved
  into it, the configuration last. Where a step fails, every step taken is taken back.
- **Undone** (`Undo`). The command keeps what it wrote, so where the engine refuses the move
  after the write, every file it wrote or created is put back or removed, the location's
  record included, and every folder it created that is empty again.

Only the files git sees are copied, as the check and the data validation read only those,
and only YAML, as no reader of the location reads anything else.
"""

from __future__ import annotations

import contextlib
import os
import shutil
import tempfile
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from _lib import backbone, checks, editing, layout, listing
from _lib import location as locations
from _lib.editing import Refused
from _lib.findings import ERROR, WARNING, Finding, ordered
from _lib.reading import ReadError
from _lib.root import CAPABILITY, CONFIG

#: The suffixes of the files a reader of the location reads.
READ = (layout.SUFFIX, layout.OTHER_SUFFIX)

#: The label the findings of the backbone's data validation carry here.
DATA = "data"


# --- where a write goes ----------------------------------------------------------------------


@dataclass(frozen=True)
class Target:
    """The location a write goes to, relative to the project root, and whether this write
    records it in the configuration."""

    path: str
    record: bool


def for_writing(root: Path) -> Target:
    """The location a command writes into: the one the configuration records, else the
    default, which the write records. Raises Refused where the configuration cannot be read
    or records a location the rules refuse, or where nothing is recorded and the default is
    refused or holds files of another kind."""
    try:
        recorded = locations.configured(root)
    except locations.LocationRefused as exc:
        raise Refused(str(exc)) from exc
    if recorded is not None:
        return Target(recorded, record=False)
    default = locations.DEFAULT
    found = locations.problem(root, default)
    if found is None:
        found = _other_kind(root, default)
    if found is not None:
        raise Refused(
            f"nothing records where the ideas live, and the default, `{default}/`, {found}: "
            f"record the folder the ideas go in first, `pkit lean set-location <path>`"
        )
    return Target(default, record=True)


def _other_kind(root: Path, folder: str) -> str | None:
    """Why the folder `folder` cannot take ideas unasked: it holds a file that is none of the
    capability's, one that names no schema of the capability's."""
    if not (root / folder).is_dir():
        return None
    try:
        held = listing.files(root, folder)
    except listing.ListingFailed as exc:
        return f"cannot be listed: {exc}"
    for rel in held:
        if listing.hidden(PurePosixPath(rel).relative_to(folder).as_posix()):
            continue
        if layout.schema_named(root, rel) is None:
            return f"holds `{rel}`, a file of another kind"
    return None


def config_text(existing: str | None, location: str) -> str:
    """The configuration's text with the location recorded, every other line kept: a new
    file, bound to the configuration's schema, where none is. Raises Refused where the file
    is not a mapping that can take the key."""
    if existing is None or not existing.strip():
        return editing.new(f"{CAPABILITY}:config", {locations.KEY: location}).text()
    try:
        doc = editing.load(existing, CONFIG)
    except ReadError as exc:
        raise Refused(f"the location cannot be recorded: {exc}") from exc
    doc.data[locations.KEY] = location
    return doc.text()


# --- built -----------------------------------------------------------------------------------


@dataclass
class Files:
    """What a command writes: each file's text as it would stand, by its path relative to
    the project root, None for one it removes; and the location it writes into."""

    root: Path
    target: Target
    texts: dict[str, str | None] = field(default_factory=dict)

    @property
    def location(self) -> str:
        return self.target.path

    def path(self, kind: str, qualified: str) -> str:
        """Where the layout puts the file of `kind` whose subject is `qualified`."""
        try:
            return layout.path_of(self.location, kind, qualified)
        except layout.IdRefused as exc:
            raise Refused(str(exc)) from exc

    def exists(self, rel: str) -> bool:
        """Whether the file `rel` stands, as this write leaves it so far."""
        if rel in self.texts:
            return self.texts[rel] is not None
        return (self.root / rel).is_file()

    def read(self, rel: str) -> editing.Doc | None:
        """The file `rel` as this write leaves it so far, round trip, or None where none
        stands. Raises Refused where it cannot be read."""
        if rel in self.texts:
            text = self.texts[rel]
        else:
            path = self.root / rel
            if not path.is_file():
                return None
            try:
                text = path.read_bytes().decode("utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                raise Refused(f"`{rel}` cannot be read: {exc}") from exc
        if text is None:
            return None
        try:
            return editing.load(text, rel)
        except ReadError as exc:
            raise Refused(f"`{rel}` cannot be changed: {exc}") from exc

    def put(self, rel: str, doc: editing.Doc) -> None:
        """Write the file `rel` as `doc` stands."""
        self.texts[rel] = doc.text()

    def remove(self, rel: str) -> None:
        """Remove the file `rel`."""
        self.texts[rel] = None

    def written(self) -> dict[str, str | None]:
        """Every file the write changes, the configuration last where it records the
        location."""
        out = dict(self.texts)
        if self.target.record:
            config = self.root / CONFIG
            existing = config.read_text(encoding="utf-8") if config.is_file() else None
            out[CONFIG] = config_text(existing, self.location)
        return out


# --- held ------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Held:
    """What holding a write found: the errors it adds, which refuse it; the errors already in
    the files, which it leaves; and the warnings it adds."""

    added: tuple[Finding, ...]
    standing: tuple[Finding, ...]
    warnings: tuple[Finding, ...]


def hold(files: Files) -> Held:
    """Hold the write `files` to the check and to the backbone's data validation, as the
    files stand and as the write would leave them. Raises Refused where either cannot be
    run."""
    written = files.written()
    # The configuration the write leaves lies under both copies, so the check reads the same
    # location in each, and the two differ only by the content the write changes.
    configured = {CONFIG: written[CONFIG]} if CONFIG in written else {}
    staging = Path(tempfile.mkdtemp(prefix="lean-business-"))
    try:
        before = _stage(files.root, files.location, staging / "before", configured)
        after = _stage(files.root, files.location, staging / "after", written)
        found_before = _found(files.root, before, files.location)
        found_after = _found(files.root, after, files.location)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    errors = [f for f in found_after if f.severity == ERROR]
    added = _beyond(errors, [f for f in found_before if f.severity == ERROR])
    kept = [f for f in errors if not any(f is a for a in added)]
    warned = _beyond(
        [f for f in found_after if f.severity == WARNING],
        [f for f in found_before if f.severity == WARNING],
    )
    return Held(tuple(ordered(added)), tuple(ordered(kept)), tuple(ordered(warned)))


def _stage(root: Path, location: str, into: Path, written: Mapping[str, str | None]) -> Path:
    """A copy of the project's location and configuration, as the files git sees stand, at
    `into`, with `written` laid over it. Raises Refused where git cannot list the files."""
    into.mkdir(parents=True)
    try:
        held = listing.files(root, location) if (root / location).is_dir() else []
    except listing.ListingFailed as exc:
        raise Refused(f"the files of `{location}` cannot be listed: {exc}") from exc
    copied = [rel for rel in held if rel.endswith(READ)]
    if (root / CONFIG).is_file():
        copied.append(CONFIG)
    for rel in copied:
        (into / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / rel, into / rel)
    for rel, text in written.items():
        target = into / rel
        if text is None:
            target.unlink(missing_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    return into


def _found(root: Path, staged: Path, location: str) -> list[Finding]:
    """What the check and the backbone's data validation find in the copy `staged`."""
    found = list(checks.check(staged).findings)
    found.extend(data_validation(root, staged, location))
    return found


def data_validation(root: Path, staged: Path, location: str) -> list[Finding]:
    """What `pkit data validate` finds in the location of the copy `staged`, run from the
    project `root`, whose installed capability gives the schemas: each file's shape, and each
    reference and id between the files. Its places and messages name the files as the
    project does. Raises Refused where it cannot be run or does not answer."""
    folder = staged / location
    if not folder.is_dir() or not any(folder.rglob(f"*{layout.SUFFIX}")):
        return []
    argv = ["pkit", "data", "validate", str(folder)]
    try:
        done = backbone.run(argv, cwd=root, capture_output=True, text=True, check=False)
    except OSError as exc:
        raise Refused(f"the files cannot be held to `pkit data validate`: {exc}") from exc
    found = _read_data_report(str(done.stdout or ""), f"{staged}/")
    if done.returncode not in (0, 1) or (
        done.returncode == 1 and not any(f.severity == ERROR for f in found)
    ):
        said = (str(done.stderr or "") or str(done.stdout or "")).strip()
        raise Refused(f"`pkit data validate` could not hold the files: {said}")
    return found


def _read_data_report(text: str, prefix: str) -> list[Finding]:
    """The findings `pkit data validate` prints, each `[<severity>] <place>` with its message
    on the line after, the copy's folder `prefix` taken out of each."""
    found: list[Finding] = []
    lines = text.splitlines()
    for index, line in enumerate(lines):
        head = line.strip()
        if not head.startswith("[") or "] " not in head:
            continue
        severity, _, place = head[1:].partition("] ")
        if severity not in (ERROR, WARNING):
            continue
        message = ""
        if index + 1 < len(lines):
            message = lines[index + 1].strip().removeprefix("→").strip()
        found.append(
            Finding(severity, _place(place.replace(prefix, "")), message.replace(prefix, ""), DATA)
        )
    return found


def _place(place: str) -> str:
    """A place the data validation names, a file with a JSON Pointer run on after it, as the
    check writes one, `<file>#<pointer>`."""
    end = place.find(layout.SUFFIX)
    if end < 0:
        return place
    end += len(layout.SUFFIX)
    return f"{place[:end]}#{place[end:]}" if place[end:] else place[:end]


def _key(finding: Finding) -> tuple[str, str, str, str]:
    """What tells one finding from another across a write: its severity, its file, its label
    and its message, never the place within the file, which an entry added or removed before
    it shifts."""
    return finding.severity, finding.location.split("#", 1)[0], finding.label, finding.message


def _beyond(after: Sequence[Finding], before: Sequence[Finding]) -> list[Finding]:
    """The findings of `after` that `before` does not hold, counted, so a finding found once
    more than before is one the write adds."""
    left = Counter(_key(f) for f in before)
    out: list[Finding] = []
    for finding in after:
        key = _key(finding)
        if left[key] > 0:
            left[key] -= 1
        else:
            out.append(finding)
    return out


# --- written, and undone ---------------------------------------------------------------------


class Undo:
    """What a write changed, so it can be taken back: each file's bytes from before, None
    where the write created it, and each folder it created."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.saved: list[tuple[Path, bytes | None]] = []
        self.made: list[Path] = []

    def __call__(self) -> list[str]:
        """Take every step back, the last first. Returns each file it could not put back."""
        left: list[str] = []
        for path, before in reversed(self.saved):
            try:
                if before is None:
                    path.unlink(missing_ok=True)
                else:
                    _write(path, before)
            except OSError:
                left.append(path.relative_to(self.root).as_posix())
        for folder in reversed(self.made):
            # A folder something else wrote into since stays, with what it holds.
            with contextlib.suppress(OSError):
                folder.rmdir()
        self.saved.clear()
        self.made.clear()
        return left


def commit(root: Path, written: Mapping[str, str | None]) -> Undo:
    """Write each file of `written`, in its order, whole, or remove it where its text is
    None. Returns how to take the write back. Raises Refused, with every step taken back,
    where a step fails."""
    undo = Undo(root)
    try:
        for rel, text in written.items():
            path = root / rel
            if path.is_symlink():
                raise Refused(f"`{rel}` is a link, and a command writes no file through a link")
            before = path.read_bytes() if path.is_file() else None
            if text is None:
                if before is None:
                    continue
                undo.saved.append((path, before))
                path.unlink()
                continue
            _make_folders(root, path.parent, undo)
            undo.saved.append((path, before))
            _write(path, text.encode("utf-8"))
    except OSError as exc:
        left = undo()
        unrestored = f"; these could not be put back: {', '.join(left)}" if left else ""
        raise Refused(f"the write failed and was taken back: {exc}{unrestored}") from exc
    except Refused:
        undo()
        raise
    return undo


def _make_folders(root: Path, folder: Path, undo: Undo) -> None:
    missing: list[Path] = []
    while not folder.exists() and folder != root:
        missing.append(folder)
        folder = folder.parent
    for each in reversed(missing):
        each.mkdir()
        undo.made.append(each)


def _write(path: Path, data: bytes) -> None:
    """Write `data` to `path` whole: to a file beside it first, then moved into place."""
    handle, staged = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as out:
            out.write(data)
        os.replace(staged, path)
    except BaseException:
        Path(staged).unlink(missing_ok=True)
        raise
