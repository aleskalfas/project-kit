"""The check: what the project's visual work breaks, within the project's validation
(visual-communication DEC-002 points 3, 4, 6 and 7, DEC-003 point 9, DEC-004 points 8, 9
and 11, DEC-005 points 7, 9, 13 and 14, DEC-006 point 8, DEC-008 points 1 and 9, DEC-010
points 1, 2 and 9, DEC-013 points 5 and 6, DEC-017 points 4 to 7).

**File-level findings, every run:**

- the binding of each file of the capability's format in the location, read from its
  name, and of the configuration: a file that names no schema, or another one, fails (a
  file at another format number the core's data validation reports, so this check does
  not repeat it);
- the library folder and its list (`libraries.Held.findings`), and each copy of a library
  the capability ships against what the installed capability ships under its number
  (`copies.compare`, DEC-013 point 6);
- each piece's lock: a version the project does not hold or the capability cannot read,
  a library the piece uses that the lock does not name, libraries that build on another
  major than the one locked; a piece with no lock yet; a version not yet released under a
  final or a published piece's lock; and, read with the content, a key that both an item's
  component and its list declare, which fails where an item carries it and is stated as a
  fact where none does (DEC-010 points 2 and 9);
- each library version checked alone, once: the newest version the project holds of
  each major of each library, resolved with the newest version the project holds of each
  major it names. A brand is read over its base, a component library's own roles are
  judged, and so is each arrangement field of its patterns that its list's default
  component also declares, the components read through an environment of the engine
  that no piece or brand stands behind (`pipeline.LibraryEnv`, DEC-010 point 9); the
  foundations' declarations are read. What it shows lies in the version; a
  version that names majors no versions fit, or one the project holds no version of,
  cannot be checked alone, which is a finding. A check of one piece runs no such pass;
- the libraries each piece locks, read under its lock: the own roles of each component
  library, and the brand, with its open roles, fonts and declared pairs. A fault the
  version shows alone too lies in the version, reported once; one only the lock's
  combination of versions shows lies at the piece's lock, and its level stands;
- the name of each library a piece locks, against the top groups of the shared roles of
  the foundations it locks (DEC-004 points 7 and 11);
- each notation a piece names, against the colour families of the foundations it locks:
  a library that is no notation, a file that cannot be read, a concept that maps to no
  colour family the foundations declare (DEC-004 points 10 and 11);
- the ids in each content file, a list of runs skipped, and each content file against the
  fields and options of the components it fills, each list of runs against the words of
  its field's run styles, the nearest known key or word named (DEC-012 points 1, 2 and 8).

**Scene findings** (`scene_findings`): what computing a piece's scenes finds, in every
language and at every key over the size axes, a finding that differs by key naming the key
it holds at: the engine's own (overflow, a component that gets less than it asks for, two
owners of a value, a loop, a missing exposed part or point, a page inside a page, a
concept the piece's notations do not hold), a produced picture that is missing, contrast
as drawn, a colour role the brand lacks, each loss of the renderers that draw the piece
that nobody accepted, and the components it uses that are experimental or deprecated. A
render keeps them in the piece's `findings.yaml`, keyed by a fingerprint of every file
they were computed from. The check reads that record while its key verifies, and computes
the scenes now otherwise. It computes no more once the validator's bound
(`PKIT_COMMAND_DEADLINE`) is near: each piece left fails as not checked, naming
`pkit visual render <piece>`.

**A final piece** is read by its own file, its lock and the version handed out, and no more
(DEC-002 point 7, DEC-017 point 4): each other pass reads a piece through today's capability,
so a stricter release could fail what was handed out, and its mend would change nothing handed
out. The binding of each of its files is read with every other file's. Its lock is held to what
it names, a version that no longer matches what was released included, and not to its content,
which goes unread. A finding at its lock fails only where something other than a move of the
lock mends it (`lock_findings`), since its state forbids the move.

**What a final piece owes of the version handed out** (`handed_out_findings`, DEC-006 point 8,
DEC-017 point 6) is read from its record of exports and its files, whatever its lock shows. A
piece is final by its state or by that record, so each is held to the other: each of these
fails, in a file the project can correct:

- a file of the version that is missing, or holds another hash than the record's;
- `state: final` with no version handed out;
- a version handed out with another state, or another lock than the one read from it;
- a version whose lock or files cannot be read from the record;
- a record that cannot be read, which reads the piece as final and is held to no version.

**What a state owes of a current copy** (`_copy`, DEC-006 point 8, DEC-017 points 5 to 7) is
read from the record of exports, whichever way the piece came to its state, and the record's
word on whose copy it is settles each rule (`current_copy.own`). It runs after the piece's
reads and before a lock finding stops the piece, so each of these stands beside that finding:

- a published piece fails where it declares no format, where it has no current copy of its
  own, where a file of that copy is missing or holds another hash, or where something the
  version that wrote the copy read has changed (`published_findings`). So it is held to that
  version, and not to the last. A copy made over a stale output asks for attention;
- a draft with a file of its own current copy standing asks for attention, whatever the file
  holds (`standing_findings`);
- a final piece raises none of these, since no export can mend its copy (`_final`).

**An error the check does not expect** on one piece, such as one the engine raises on data
it does not guard against, stops that piece alone: it fails as `unexpected-error`, naming
the error, and the check goes on to the next piece.

**Severity** is computed when a finding is read: a failing finding in a released library
version asks for attention instead, naming the library's owner; in a copy of a library the
capability ships, released or not, it names whoever maintains the capability
(`findings.as_read`). Whether a version is released, and a library's source, are read from
the list. A released version whose folder no longer matches what was released is the
project's to restore, so a finding in it fails (DEC-002 point 7, DEC-003 point 9, DEC-013
point 6).

In the findings record, a finding's file is relative to the piece's folder, or, where it
lies in a library version, to that version's folder, so the record stays true when the
location moves or the piece is copied. The check gives every file relative to the project
root.
"""

from __future__ import annotations

import dataclasses
import math
import re
import time
from collections.abc import Collection, Iterator, Mapping, Sequence
from functools import cached_property
from pathlib import Path, PurePosixPath
from typing import Any, Protocol

from _lib import (
    code,
    copies,
    current_copy,
    exports,
    fingerprint,
    framing,
    layout,
    location,
    names,
    records,
    tokens,
)
from _lib import pipeline as pl
from _lib.env import MissingFont
from _lib.files import FileError, binding_problem, nearest, read_bound, schema_of
from _lib.findings import (
    ATTENTION,
    AUTHOR,
    FACT,
    FAILS,
    SEVERITY,
    Finding,
    accepted,
    as_read,
)
from _lib.findings import loss_finding as _loss_finding
from _lib.layout import (
    LAYOUT,
    RUN_KEYS,
    RUNS,
    PageForms,
    key_path,
    page_forms,
    run_problem,
    through,
)
from _lib.libraries import (
    FOLDER,
    FOUNDATIONS,
    SHIPPED_SOURCE,
    Held,
    Library,
    LibraryError,
    LockRefused,
    MajorsConflict,
    Version,
    kind_within,
    newest_of_majors,
    readable,
)
from _lib.plugins import seam
from _lib.reading import ReadError, read_yaml, sha256
from _lib.root import CONFIG, SHIPPED
from _lib.scene import SceneResult
from _lib.shipped import read as read_shipped

#: The renderer that draws every piece's previews.
PREVIEWS = "svg"

#: The environment variable that carries the validator's deadline, in seconds since the
#: epoch.
DEADLINE = "PKIT_COMMAND_DEADLINE"

#: What the check keeps of its bound to answer, in seconds.
MARGIN = 1.0

#: WCAG's large text: at least 24 px, or 18.66 px and bold (DEC-004 point 8).
LARGE = 24.0
LARGE_BOLD = 18.66
BOLD = 700

#: The colour a text with no fill is drawn in.
BLACK = {"colorSpace": "srgb", "components": [0, 0, 0], "alpha": 1}

#: The finding on a version not yet released under a final or a published piece's lock. It
#: stops no drawing (`viewing.opened`).
LOCK_NOT_RELEASED = "lock-not-released"

#: The findings on what a piece's state owes of its current copy (DEC-017 point 6).
PUBLISHED_NO_FORMAT = "published-no-format"
COPY_NONE = "current-copy-none"
COPY_FILE_MISSING = "current-copy-file-missing"
COPY_FILE_CHANGED = "current-copy-file-changed"
COPY_STALE = "current-copy-stale"
COPY_UNREADABLE = "current-copy-unreadable"
COPY_OVER_STALE = "current-copy-over-stale"
COPY_STANDING = "current-copy-standing"

#: The findings on what a final piece owes of the version handed out (DEC-017 point 6), and on
#: a record of exports that cannot be read, which makes a piece final (DEC-017 point 3).
HANDED_OUT_NONE = "handed-out-none"
HANDED_OUT_STATE = "handed-out-state"
HANDED_OUT_LOCK = "handed-out-lock"
HANDED_OUT_UNREADABLE = "handed-out-unreadable"
HANDED_OUT_FILE_MISSING = "handed-out-file-missing"
HANDED_OUT_FILE_CHANGED = "handed-out-file-changed"
EXPORTS_UNREADABLE = "exports-unreadable"

#: The properties of a scene element that are no property it draws.
_STRUCTURE = ("type", "id", "sources", "children")

_CONTENT_FILE = re.compile(r"^content\.(?P<language>[^.]+)\.yaml$")


@dataclasses.dataclass(frozen=True)
class Report:
    """What the check found: its summary, and each finding with the level it takes where
    it lies, its file relative to the project root."""

    summary: list[str]
    judged: list[tuple[Finding, str]]

    def failed(self) -> bool:
        return any(level == FAILS for _, level in self.judged)


def deadline_from(environ: Mapping[str, str]) -> float | None:
    """The validator's deadline the environment gives, or None."""
    try:
        value = float(environ.get(DEADLINE, ""))
    except ValueError:
        return None
    return value if math.isfinite(value) else None


# --- the check ----------------------------------------------------------------------------------


def check(root: Path, *, only: str | None = None, deadline: float | None = None) -> Report:
    """The check of the project at `root`: every piece, or the piece `only`."""
    found: list[Finding] = []
    config = _config_findings(root)
    try:
        where = location.for_reading(root)
    except location.LocationRefused as exc:
        found.append(Finding("location", FAILS, str(exc), file=CONFIG))
        return Report(
            ["The location cannot be read, so nothing is checked."], _plain(config + found)
        )
    if where is None:
        summary = [
            f"No visual work: {CONFIG} records no location, and `{location.DEFAULT}/` holds none."
        ]
        return Report(summary, _plain(config))
    run = _Run(root, where.path, deadline)
    try:
        run.all(only)
    except location.GitFailed as exc:
        run.add(Finding("files-unlisted", FAILS, f"the location's files cannot be listed: {exc}"))
    judged = [run.judged(finding) for finding in [*config, *run.found]]
    return Report(run.summary(only), judged)


def _plain(found: list[Finding]) -> list[tuple[Finding, str]]:
    return [(finding, finding.level) for finding in found]


def _config_findings(root: Path) -> list[Finding]:
    path = root / CONFIG
    if not path.is_file():
        return []
    try:
        data = read_yaml(path)
    except ReadError as exc:
        return [Finding("file-unreadable", FAILS, str(exc), file=CONFIG)]
    problem = _binding(data, "config")
    return (
        [Finding("binding", FAILS, f"the configuration {problem}", file=CONFIG)] if problem else []
    )


def _binding(data: Any, kind: str) -> str | None:
    """Why a file of `kind` is not bound to its schema, or None. A file bound to it at
    another format number is the core's data validation's to report."""
    if isinstance(data, Mapping) and data.get("pkit_schema") == schema_of(kind):
        return None
    return binding_problem(data, kind)


class _Run:
    """One run of the check over a location."""

    def __init__(self, root: Path, location_path: str, deadline: float | None) -> None:
        self.root = root
        self.location = location_path
        self.deadline = deadline
        self.found: list[Finding] = []
        self.held = Held(root, location_path)
        self.pieces: list[str] = []
        self.unbound: set[str] = set()
        self.alone: dict[str, list[Finding]] = {}
        self.reported: set[tuple[str, str, str, str, str]] = set()
        self.named: set[str] = set()
        self.notations: set[str] = set()
        self.held_as: dict[tuple[str, Version], tuple[bool, bool]] = {}
        self.counts = {"pieces": 0, "read": 0, "computed": 0, "unchecked": 0, "final": 0}

    def add(self, finding: Finding) -> None:
        self.found.append(finding)

    def judged(self, finding: Finding) -> tuple[Finding, str]:
        """A finding as it reads where it lies, with its level there."""
        name, _, text = finding.library.partition("@")
        try:
            version = Version.parse(text)
        except ValueError:
            return as_read(finding, False)
        released, shipped = self._as_released(name, version)
        return as_read(finding, released, shipped=shipped)

    def _as_released(self, name: str, version: Version) -> tuple[bool, bool]:
        """Whether the list marks a version released and its folder is still as it was
        released; and whether it is a copy of a library the list names from the source
        `shipped`, other than a released copy whose folder no longer matches. A copy that no
        longer matches is the project's to restore (DEC-002 point 7, DEC-003 point 9). Any
        other copy of a library the capability ships only whoever maintains the capability
        corrects (DEC-013 point 6)."""
        key = (name, version)
        if key not in self.held_as:
            released = self.held.released(name, version)
            changed = released and bool(self.held.hash_changes(name, version))
            shipped = self.held.source(name) == SHIPPED_SOURCE and not changed
            self.held_as[key] = (released and not changed, shipped)
        return self.held_as[key]

    @cached_property
    def compared(self) -> copies.Compared:
        """Each copy of a library the capability ships, against what it ships."""
        return copies.compare(self.held)

    def summary(self, only: str | None) -> list[str]:
        c = self.counts
        what = f"the piece `{only}`" if only else f"{c['pieces']} piece(s)"
        final = f", of {c['final']} left out as final" if c["final"] else ""
        return [
            f"{what} in `{self.location}`: the scenes of {c['read']} read from their findings "
            f"record, of {c['computed']} computed now, of {c['unchecked']} not checked{final}."
        ]

    def all(self, only: str | None) -> None:
        files = location.files(self.root, self.location)
        if only is None:
            self._bindings(files)
            for finding in self.held.findings(self.compared.restored):
                self._once(finding)
            self.found.extend(self.compared.findings)
            self._alone_pass()
        self.pieces = names_ = pl.piece_names(self.root, self.location)
        if only is not None:
            if only not in names_:
                self.add(
                    Finding(
                        "piece-missing",
                        FAILS,
                        f"the location holds no piece `{only}`",
                        file=f"{self.location}/{pl.PIECES}",
                    )
                )
                return
            self._bindings(
                [rel for rel in files if rel.startswith(f"{self.location}/{pl.PIECES}/{only}/")]
            )
            names_ = [only]
        for name in names_:
            self.counts["pieces"] += 1
            counted = dict(self.counts)
            try:
                self._piece(name)
            except location.GitFailed:
                raise  # the location's files cannot be listed: `files-unlisted`, in `check`
            except Exception as exc:
                # The last resort: an error no finding reports stops this piece alone.
                self.counts = {**counted, "unchecked": counted["unchecked"] + 1}
                self.add(self._unexpected(name, exc))
        if only is None:
            self.found.extend(_code_findings(self.root, self.location))

    def _unexpected(self, name: str, error: Exception) -> Finding:
        """The finding of a piece whose check stopped on an error it does not expect, such as
        one the engine raises on data it does not guard against. The check owed an answer
        and gave none, so it fails (DEC-002 point 7)."""
        said = f"{type(error).__name__}: {error}" if str(error) else type(error).__name__
        return Finding(
            "unexpected-error",
            FAILS,
            f"the check of `{name}` stopped on an error it does not expect: {said}",
            file=f"{self.location}/{pl.PIECES}/{name}/{pl.PIECE_FILE}",
            fix="mend what the error names in the piece's files or the components they use; "
            "where none is at fault, report the error as a fault of the capability",
        )

    # -- bindings

    def _bindings(self, files: Sequence[str]) -> None:
        prefix = f"{self.location}/"
        for rel in files:
            inside = rel[len(prefix) :]
            kind = kind_of(inside)
            if kind is None:
                continue
            library = _library_of(inside)
            try:
                data = read_yaml(self.root / rel)
            except ReadError as exc:
                self.unbound.add(rel)
                self.add(Finding("file-unreadable", FAILS, str(exc), file=rel, library=library))
                continue
            problem = _binding(data, kind)
            if problem is not None:
                self.unbound.add(rel)
                self.add(
                    Finding(
                        "binding",
                        FAILS,
                        f"a file of the capability's format {problem}",
                        file=rel,
                        library=library,
                    )
                )

    # -- a piece

    def _piece(self, name: str) -> None:
        rel = f"{self.location}/{pl.PIECES}/{name}"
        try:
            piece = pl.read_piece_file(self.root, self.location, name)
            if piece.final:
                self._final(piece)
                return
            piece = pl.read_piece(self.root, self.location, name)
        except pl.Refused as exc:
            if not any(path.startswith(f"{rel}/") for path in self.unbound):
                self.add(
                    Finding("piece-unreadable", FAILS, str(exc), file=f"{rel}/{pl.PIECE_FILE}")
                )
            self.counts["unchecked"] += 1
            return
        self.found.extend(id_findings(piece))
        lock = lock_findings(self.held, piece)
        self.found.extend(lock)
        self._copy(piece)
        if lock:
            self.counts["unchecked"] += 1
            return
        try:
            project = pl.Project(piece, piece.lock, self.held)
        except pl.Refused as exc:
            self.add(Finding("piece-unreadable", FAILS, str(exc), file=piece.file(pl.PIECE_FILE)))
            self.counts["unchecked"] += 1
            return
        except tokens.TokenError as exc:
            self._lock_found(piece, exc.findings)
            self.counts["unchecked"] += 1
            return
        self._lock_found(piece, [*project.scope.findings, *project.brand.findings])
        self._library_names(project)
        self._notation_findings(project)
        self.found.extend(content_findings(project))
        produced = _produced_findings(self.root, self.location, piece)
        self.found.extend(produced)
        self._scenes(project, _unmade(produced))

    def _copy(self, piece: pl.Piece) -> None:
        """What the piece's state owes of its current copy (DEC-006 point 8, DEC-017 point 6).
        `_piece` runs this after its reads and before a lock finding stops the piece, so a
        fault at the lock hides no stale copy, and a lock that differs reads as a change to
        what the copy was made from. A record that keeps no list of its versions, or a copy of
        no shape, leaves the copy unjudged, which fails. A record that cannot be read at all
        never comes here: it makes the piece final (`handed_out_findings`)."""
        published = current_copy.keeps(piece)
        if published and not piece.exports:
            self.add(_no_format(piece))
        try:
            record = exports.recorded(piece)
            versions = exports.recorded_versions(piece, record)
            entry = current_copy.own(piece, record, self.pieces)
        except pl.Refused as exc:
            self.add(Finding(COPY_UNREADABLE, FAILS, str(exc), file=piece.file(pl.EXPORTS_FILE)))
            return
        if published:
            self.found.extend(published_findings(self.held, piece, entry, versions))
        elif entry is not None and piece.state == copies.DRAFT:
            self.found.extend(standing_findings(piece, entry))

    def _final(self, piece: pl.Piece) -> None:
        """A final piece, read from its own file alone: its lock as it stands, and what it owes
        of the version handed out, whatever that lock shows, and no more (DEC-002 point 7,
        DEC-017 point 4). `piece` holds no contents, so no lock is held to them. Only a run over
        the location reads `Held.findings`, so this reads each version the lock names against
        what was released, and `_once` keeps the finding to one."""
        self.counts["final"] += 1
        self.found.extend(lock_findings(self.held, piece))
        for finding in changed_versions(self.held, piece.lock, self.compared.restored):
            self._once(finding)
        self.found.extend(handed_out_findings(piece))

    def _lock_found(self, piece: pl.Piece, found: Sequence[Finding]) -> None:
        """What the libraries a piece locks show under its lock: the own roles of each
        component library, and the brand, over its base (DEC-008 point 9). A fault the
        version shows alone too lies in the version, reported once; one only the lock's
        combination of versions shows lies at the piece's lock, which the project chose. A
        fault of the lock itself, which names no version, is reported once."""
        for finding in found:
            name, _, text = finding.library.partition("@")
            if finding.library:
                try:
                    alone = self._alone(name, Version.parse(text))
                except ValueError:
                    alone = []
                if _mark(finding) not in {_mark(seen) for seen in alone}:
                    self.add(_at_lock(finding, piece))
                    continue
            self._once(finding)

    def _once(self, finding: Finding) -> None:
        """Adds a finding the run has not reported yet."""
        if _mark(finding) not in self.reported:
            self.reported.add(_mark(finding))
            self.add(finding)

    # -- versions checked alone

    def _alone_pass(self) -> None:
        """The newest version the project holds of each major of each library, checked
        alone, once (`_alone`), what it shows reported in the version. A version a lock
        names is judged at that lock too (`_lock_found`)."""
        for name in self.held.names():
            for major in sorted({version.major for version in self.held.versions(name)}):
                newest, _ = readable(self.held, name, major)
                if not newest:
                    continue  # a version the capability cannot read: `Held.findings`
                version = newest[0].version
                try:
                    shown = self._alone(name, version)
                except Exception as exc:
                    # The last resort, as for a piece: an error no finding reports stops
                    # this version's check alone, and the run goes on.
                    said = f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__
                    shown = [
                        Finding(
                            "unexpected-error",
                            FAILS,
                            f"the check of {name}@{version} alone stopped on an error it does "
                            f"not expect: {said}",
                            file=f"{self.location}/{FOLDER}/{name}/{version}/library.yaml",
                            library=f"{name}@{version}",
                        )
                    ]
                for finding in shown:
                    self._once(finding)

    def _alone(self, name: str, version: Version) -> list[Finding]:
        """What the library version shows checked alone, worked out once: resolved with the
        newest version the project holds of each major it names (DEC-005 point 7, DEC-008
        point 1). A brand is read over its base, a component library's own roles are
        judged, and its patterns too, against their lists' default components, read
        through an environment of the engine that no piece or brand stands behind
        (`default_clashes`, DEC-010 point 9); the foundations' declarations are read; a
        notation is checked under each lock alone. Each finding lies in the version. A
        version that names majors no versions fit, or one of which the project holds no
        version, cannot be checked alone, which is the finding it shows.

        The pass is one each kind of library version joins: what a later record judges of
        a version alone joins its kind's branch here."""
        label = f"{name}@{version}"
        if label in self.alone:
            return self.alone[label]
        self.alone[label] = []
        try:
            library = self.held.library(name, version)
        except LibraryError:
            return []
        if self.held.unreadable(name, version) is not None:
            return []
        file = f"{self.location}/{FOLDER}/{name}/{version}/library.yaml"
        try:
            chosen = newest_of_majors(self.held, library)
        except MajorsConflict as exc:
            self.alone[label] = [
                Finding(
                    "alone-majors",
                    FAILS,
                    f"{label} cannot be checked alone: {exc}",
                    file=file,
                    where="builds-on",
                    fix="name in `builds-on`, in a version of its own, majors that fit together",
                    library=label,
                )
            ]
            return self.alone[label]
        except LockRefused as exc:
            self.alone[label] = [
                Finding(
                    "alone-missing",
                    FAILS,
                    f"{label} cannot be checked alone: {exc}",
                    file=self.held.list_path,
                    where=f"libraries.{name}",
                    fix=f"bring in a version of each major {label} names, or take {label} out",
                )
            ]
            return self.alone[label]
        folders = {other.name: other.folder for other in chosen.values()}
        try:
            if name == FOUNDATIONS:
                tokens.read_scope(folders, root=self.root)
                found: Sequence[Finding] = []
            elif library.kind == "components":
                scope = tokens.read_scope(folders, root=self.root)
                env = pl.LibraryEnv(chosen, scope)
                found = [*scope.findings_of(name), *default_clashes(self.held, library, env)]
            elif library.kind == "brand" and FOUNDATIONS in folders:
                found = tokens.read_brand(
                    library.folder,
                    tokens.read_scope(folders, root=self.root),
                    fonts=self.root / self.location / pl.FONTS,
                    root=self.root,
                    locked=folders,
                ).findings
            else:
                found = []
        except tokens.TokenError as exc:
            found = exc.findings
        self.alone[label] = [finding for finding in found if finding.library == label]
        return self.alone[label]

    def _library_names(self, project: pl.Project) -> None:
        """Each library the piece locks, once for each version and foundations, against the
        top groups of the shared roles of the foundations it locks (DEC-004 points 7 and
        11). The finding lies in the version's `library.yaml`, at its `name`."""
        groups = project.foundations.top_groups
        against = project.label(pl.FOUNDATIONS)
        for name, version in sorted(project.lock.items()):
            label = f"{name}@{version}"
            if f"{label} {against}" in self.named:
                continue
            self.named.add(f"{label} {against}")
            problem = names.library_name_problem(name, groups)
            if problem is not None:
                self.add(
                    Finding(
                        "library-name",
                        FAILS,
                        problem,
                        file=f"{self.location}/{FOLDER}/{name}/{version}/library.yaml",
                        where="name",
                        fix="rename the library, in a version of its own, and lock that version",
                        library=label,
                    )
                )

    def _notation_findings(self, project: pl.Project) -> None:
        """The findings of each notation the piece names, once for each version and
        foundations: a notation is read against the colour families of the foundations the
        piece locks (DEC-004 points 10 and 11). A file the binding pass already reports is
        not reported again (one owner per finding, DEC-002 point 6)."""
        against = project.label(pl.FOUNDATIONS)
        for notation in project.notations.values():
            if f"{notation.label} {against}" not in self.notations:
                self.notations.add(f"{notation.label} {against}")
                self.found.extend(f for f in notation.findings if f.file not in self.unbound)

    def _scenes(self, project: pl.Project, unmade: set[str]) -> None:
        piece = project.piece
        stored = read_findings_record(self.root, self.held, piece)
        if stored is not None:
            self.counts["read"] += 1
            self._scene_findings(piece, stored, unmade)
            return
        if self.deadline is not None and time.time() > self.deadline - MARGIN:
            self.counts["unchecked"] += 1
            self.add(
                Finding(
                    "not-checked",
                    FAILS,
                    f"the scenes of `{piece.name}` were not checked within the validation's "
                    f"bound, and its findings record is missing or out of date",
                    file=piece.file(pl.FINDINGS_FILE),
                    fix=f"run {pl.render_command(piece.name)} and commit its findings record",
                )
            )
            return
        self.counts["computed"] += 1
        self._scene_findings(piece, computed(project), unmade)

    def _scene_findings(self, piece: pl.Piece, found: Sequence[Finding], unmade: set[str]) -> None:
        """A piece's scene findings, each file relative to the project root, and each that
        only repeats another finding of the run left out (`_said`)."""
        for finding in found:
            placed = rooted(finding, piece)
            if not _said(placed, unmade, self.unbound):
                self.add(placed)


def _mark(finding: Finding) -> tuple[str, str, str, str, str]:
    """What tells one finding of a library version from another."""
    return (finding.code, finding.file, finding.where, finding.message, finding.library)


def _at_lock(finding: Finding, piece: pl.Piece) -> Finding:
    """A finding of a library version that only the piece's lock shows, as it combines the
    versions: it lies at the lock, which the project chose, so it names no version and its
    level stands (DEC-002 point 7, DEC-008 point 9). It says where the version shows it."""
    at = f"{finding.file}, `{finding.where}`" if finding.where else finding.file
    return dataclasses.replace(
        finding,
        message=f"under this lock, {finding.library} shows what it does not alone ({at}): "
        f"{finding.message}",
        file=piece.file(pl.PIECE_FILE),
        where="lock",
        fix=finding.fix
        or f"move the lock to versions that fit together, or mend {finding.library}",
        library="",
    )


def default_clashes(held: Held, library: Library, env: pl.LibraryEnv) -> list[Finding]:
    """What each pattern of the library version declares for a list against the list's
    default component, the `draw` of a part that repeats over the list, a drawing of a
    top's layout included. An arrangement field or an end field the default component also
    declares as a field or an option is read by neither (`arrangement-clash`, `end-clash`;
    DEC-010 points 2 and 9, DEC-011 point 8). A list of ties whose default component takes
    no ends draws no tie by default (`tie-default`, DEC-011 points 1 and 8). The pattern
    chose both, so each is the pattern's to mend, in its file. Each component of the version
    is read through `env`, which reads the default component from the versions the library
    is checked alone with. A component that cannot be read, and a default that names none,
    are the scene's to report."""
    ctx = layout.Context(env, "")
    found = []
    for path in held.files(library.name, library.version):
        if path.parent != library.folder / pl.COMPONENTS or path.suffix != ".yaml":
            continue
        component = ctx.component(f"{library.name}/{path.stem}")
        if component is None:
            continue
        file = path.relative_to(held.root).as_posix()

        def fails(code: str, where: str, message: str, fix: str, file: str = file) -> Finding:
            return Finding(
                code, FAILS, message, file=file, where=where, fix=fix, library=library.label
            )

        for at, part, listed, draw, drawn, declared in _list_defaults(ctx, component):
            for name in declared.arrangement:
                what = _declared_as(drawn, name)
                if what:
                    found.append(
                        fails(
                            "arrangement-clash",
                            f"{at}lists.{listed}.arrangement.{name}",
                            f"`{name}` is an arrangement field of `{listed}`, and `{draw}`, which "
                            f"draws its items by default, declares it as {what}: neither reads "
                            "it on an item",
                            "rename the arrangement field, or draw the list with another "
                            "component, in a version of its own",
                        )
                    )
            if declared.ends is None:
                continue
            if not drawn.takes_ends:
                found.append(
                    fails(
                        "tie-default",
                        f"{at}parts.{part}.draw",
                        f"`{draw}` draws the ties of `{listed}` by default, and takes no ends: "
                        "every item of a list of ties is a tie",
                        "draw the list with a component that takes ends, in a version of its own",
                    )
                )
            for name in declared.ends:
                what = _declared_as(drawn, name)
                if what:
                    found.append(
                        fails(
                            "end-clash",
                            f"{at}lists.{listed}.ends",
                            f"`{name}` is an end field of `{listed}`, and `{draw}`, which draws "
                            f"its ties by default, declares it as {what}: neither reads it, so "
                            "no tie it draws has that end",
                            "rename the end field, or draw the list with another component, "
                            "in a version of its own",
                        )
                    )
    return found


def _list_defaults(
    ctx: layout.Context, component: layout.Component
) -> Iterator[tuple[str, str, str, str, layout.Component, layout.ListFields]]:
    """Each list that `component`, or the drawing of one of its layouts, declares fields for
    and a part of it repeats over with a default component that can be read: the prefix of
    the key path where what it declares lies, the part, the list, the default's name, the
    default, and what the list declares."""
    drawings = [("", component)] + [
        (f"layouts.{name}.", drawing) for name, drawing in sorted(component.drawings.items())
    ]
    for at, drawing in drawings:
        for part in drawing.parts.values():
            listed, draw = part.spec.get("repeat"), part.spec.get("draw")
            if part.kind != "repeat" or not isinstance(listed, str):
                continue
            if listed not in drawing.list_fields:
                continue
            drawn = ctx.component(draw) if isinstance(draw, str) else None
            if drawn is not None:
                yield at, part.name, str(listed), str(draw), drawn, drawing.list_fields[listed]


def _declared_as(component: layout.Component, name: str) -> str:
    """What `component` declares `name` as: a field, an option, or nothing."""
    if name in component.fields:
        return "a field"
    return "an option" if name in component.options else ""


def kind_of(inside: str) -> str | None:
    """The kind of file of the capability's format a path within the location names, by
    its name and place; None for a file no name makes one."""
    parts = inside.split("/")
    if not inside.endswith(".yaml"):
        return None
    if parts == [FOLDER, "libraries.yaml"]:
        return "libraries"
    if parts[0] == FOLDER and len(parts) >= 4:
        return kind_within(parts[3:])
    if parts[0] == pl.PIECES and len(parts) >= 3:
        within = parts[2:]
        single = {
            (pl.PIECE_FILE,): "piece",
            (pl.FINDINGS_FILE,): "findings",
            (pl.EXPORTS_FILE,): "exports",
        }
        if tuple(within) in single:
            return single[tuple(within)]
        if len(within) == 1 and _CONTENT_FILE.match(within[0]):
            return "content"
        if len(within) == 2 and within[0] == pl.COMPONENTS:
            return "component"
        if len(within) == 3 and within[0] == pl.PRODUCED and within[2] == pl.RECORD:
            return "produced-record"
        return None
    if parts[0] == "code" and len(parts) == 2:
        return "code"
    return None


def _library_of(inside: str) -> str:
    parts = inside.split("/")
    if parts[0] == FOLDER and len(parts) >= 4:
        try:
            return f"{parts[1]}@{Version.parse(parts[2])}"
        except ValueError:
            return ""
    return ""


def _produced_findings(root: Path, location_path: str, piece: pl.Piece) -> list[Finding]:
    """The findings on a piece's produced pictures (DEC-006 point 8): an output with no
    record, a record that names a missing variant file, a stale picture. The producer's
    framing owns them (`framing.findings`)."""
    return framing.findings(root, location_path, piece.name)


# The producer's findings that say a produced output has no picture to draw.
_UNMADE = ("produced-record-missing", "produced-record-unreadable", "produced-variant-missing")


def _unmade(produced: Sequence[Finding]) -> set[str]:
    """The produced outputs the producer's findings already report as having no picture
    to draw, by name: the folder above each record they lie in."""
    return {
        PurePosixPath(finding.file).parent.name
        for finding in produced
        if finding.code in _UNMADE and finding.file.endswith("/record.yaml")
    }


def _said(finding: Finding, unmade: set[str], unbound: set[str]) -> bool:
    """Whether a scene finding, its file relative to the project root, only repeats what
    another finding of the run says (one owner per finding, DEC-002 point 6): a picture the
    scene could not draw, of an output a producer's finding already reports as having none;
    a component whose file the binding pass already reports (`file-unreadable`, `binding`),
    a file of `unbound`."""
    if finding.code == "component-unreadable":
        return finding.file in unbound
    return finding.code == "missing-picture" and any(
        f"`{output}`" in finding.message for output in unmade
    )


def _code_findings(root: Path, location_path: str) -> list[Finding]:
    """The findings on written code (DEC-006 points 4 and 8): a missing record, a record
    naming a missing file, stale code. The code writer's module owns them
    (`code.findings`)."""
    return code.findings(root, location_path)


# --- the lock -----------------------------------------------------------------------------------


def no_move(piece: str) -> str:
    """What a finding on the final piece `piece` says where only a move of its lock would mend
    it: no move reaches that lock, and the command that copies the piece takes it up again
    (DEC-017 points 5 and 8)."""
    return (
        f"no move reaches a final piece's lock: {copies.take_up_command(piece)} takes it up again "
        f"as a new draft"
    )


def _lock_fix(piece: pl.Piece, mend: str) -> str:
    """What mends a fault at a piece's lock, by who moves that lock (DEC-003 point 8): a
    draft's render, and nothing else. Nothing moves a final piece's, and no state leads out
    of final, so `mend` says what else mends the fault (DEC-017 point 5). No render moves a
    published piece's, so it says what `pkit visual render` says of such a piece, and only a
    draft reads its pin."""
    render = pl.render_command(piece.name)
    if piece.final:
        return mend
    if piece.lock_stays:
        return (
            f"the piece is {piece.state}, so no render moves its lock: set it back to a draft "
            f"and run {render}"
        )
    if piece.pinned:
        return f"change the lock by hand, or unpin the piece and run {render}"
    return f"run {render}, which moves a draft's lock"


def lock_findings(held: Held, piece: pl.Piece) -> list[Finding]:
    """What is wrong with a piece's lock as its file holds it (DEC-003 points 8 and 9), by the
    piece's state. A `piece` read whole holds the lock to the libraries its content uses
    (`pl.needed`), as whatever draws it must; one read from its own file alone does not.

    Each finding fails, but on a final piece, whose state forbids a move of its lock. There
    one fails only where something other than a move mends it (DEC-002 point 7):

    - `lock-missing`, `lock-version`: writing back the lock of the version handed out. There
      is no version to move from, and that lock is no move (`copies.WRITE_BACK`).
    - `lock-not-held`: restoring the version.
    - `lock-unreadable`: upgrading the capability, or restoring the version's `library.yaml`.
      A fault in a released version still as it was released is its owner's to correct, in
      a new release, which only a move would reach, so it states a fact.
    - `lock-incomplete`, `lock-majors`: only a move mends them, so each states a fact.
    - `lock-not-released` takes the level `_not_released` gives it."""
    file = piece.file(pl.PIECE_FILE)
    final = piece.final

    def fails(code: str, message: str, mend: str = "") -> Finding:
        return Finding(code, FAILS, message, file=file, where="lock", fix=_lock_fix(piece, mend))

    def moved(code: str, message: str) -> Finding:
        """A finding only a move of the lock would mend."""
        if final:
            return Finding(code, FACT, message, file=file, where="lock", fix=no_move(piece.name))
        return fails(code, message)

    lock = piece.lock
    if not lock:
        missing = "the piece has no lock yet, so its scenes cannot be drawn"
        return [fails("lock-missing", missing, copies.WRITE_BACK)]
    found = []
    read = {}
    for name, text in sorted(lock.items()):
        try:
            version = Version.parse(text)
        except ValueError:
            said = f"the lock names `{name}: {text}`, which is no version"
            found.append(fails("lock-version", said, copies.WRITE_BACK))
            continue
        label = f"{name}@{text}"
        if version not in held.folders.get(name, {}):
            said = f"the lock names {label}, which the project does not hold"
            found.append(fails("lock-not-held", said, f"restore {label} in the library folder"))
            continue
        why = held.unreadable(name, version)
        if why is not None:
            said = f"the lock names {label}: {why}"
            if held.file_fault(name, version) is None:
                upgrade = "an upgrade mends it, with no move of the lock"
                found.append(fails("lock-unreadable", said, upgrade))
            elif held.released(name, version) and not held.hash_changes(name, version):
                found.append(moved("lock-unreadable", said))
            else:
                mend = f"mend or restore the `library.yaml` of {label}"
                found.append(fails("lock-unreadable", said, mend))
            continue
        read[name] = held.library(name, version)
        if piece.lock_stays and not held.released(name, version):
            found.append(_not_released(held, piece, name, version))
    for name in pl.needed(piece):
        if name not in lock:
            found.append(
                moved("lock-incomplete", f"the lock does not name `{name}`, which the piece uses")
            )
    for library in read.values():
        for need in library.builds_on:
            if need.name not in lock:
                found.append(
                    moved(
                        "lock-incomplete",
                        f"{library.label} builds on `{need.name}`, which the lock does not name",
                    )
                )
                continue
            try:
                major = Version.parse(lock[need.name]).major
            except ValueError:
                continue
            if major != need.major:
                found.append(
                    moved(
                        "lock-majors",
                        f"{library.label} builds on `{need.name}` {need.major}, but the lock "
                        f"names {need.name}@{lock[need.name]}: a piece locks one version of each "
                        f"library",
                    )
                )
    return found


def changed_versions(
    held: Held, lock: Mapping[str, str], restored: Collection[str] = ()
) -> list[Finding]:
    """The finding on each version `lock` names that no longer matches what was released
    (`Held.changed`, which takes `restored`). A version the project does not hold, or the
    list does not mark released, has nothing to compare."""
    found = []
    for name, text in sorted(lock.items()):
        try:
            version = Version.parse(text)
        except ValueError:
            continue  # `lock-version`
        if version in held.folders.get(name, {}) and held.released(name, version):
            changes = held.hash_changes(name, version)
            if changes:
                found.append(held.changed(name, version, changes, restored))
    return found


def _not_released(held: Held, piece: pl.Piece, name: str, version: Version) -> Finding:
    """The finding on a version not yet released that a final or a published piece's lock
    names, naming the piece, the library and the version (DEC-003 points 8 and 9). It fails,
    and names what mends it, but on a final piece, by whose release mends it:

    - a version of the project's own: its release (DEC-017 point 2);
    - a copy of a library the capability ships, of a number it released: `pkit visual add`,
      which names a published piece, since its lock moves only on purpose (DEC-013 point 5);
    - a copy of a number still being built: only the capability's release, so on a final
      piece it asks for attention;
    - a copy of a number the capability does not ship: no release, so on a final piece it
      states a fact, and `copy-not-shipped` keeps asking (DEC-013 point 5)."""
    label = f"{name}@{version}"
    final = piece.final
    finding = Finding(
        LOCK_NOT_RELEASED,
        FAILS,
        f"the {piece.state} piece `{piece.name}` locks {label}, which is not yet released",
        file=piece.file(pl.PIECE_FILE),
        where="lock",
    )
    if held.source(name) != SHIPPED_SOURCE:
        return dataclasses.replace(finding, fix=f"release it: `pkit visual release {name}`")
    source = _shipped_under(name, version)
    if source is not None and source.released is not None:
        add = (
            f"`pkit visual add {name}`"
            if final
            else f"`pkit visual add {name} --piece {piece.name}`"
        )
        return dataclasses.replace(finding, fix=f"run {add}, which replaces the copy as released")
    if not final:
        return dataclasses.replace(finding, fix=_lock_fix(piece, ""))
    if source is None:
        return dataclasses.replace(finding, level=FACT, fix=no_move(piece.name))
    return dataclasses.replace(
        finding,
        level=ATTENTION,
        fix=f"once the capability releases {label}, run `pkit visual add {name}`",
        who=f"whoever maintains the capability, who releases {label}",
    )


def _shipped_under(name: str, version: Version) -> copies.Source | None:
    """What the installed capability ships of the library `name` under `version`; None where
    it ships no such number, or cannot read its record or its version being built, which its
    own checks hold."""
    library = next((each for each in read_shipped(SHIPPED) if each.name == name), None)
    if library is None:
        return None
    try:
        return copies.under(library, version)
    except copies.CopyRefused:
        return None


# --- what a state owes of a current copy --------------------------------------------------------


def _no_format(piece: pl.Piece) -> Finding:
    """The finding on a published piece that declares no format (DEC-017 point 6)."""
    formats = " or ".join(f"`{form}`" for form in exports.RENDERERS)
    return Finding(
        PUBLISHED_NO_FORMAT,
        FAILS,
        f"the published piece `{piece.name}` declares no format under `exports`",
        file=piece.file(pl.PIECE_FILE),
        where="exports",
        fix=f"declare one there: {formats}",
    )


def published_findings(
    held: Held,
    piece: pl.Piece,
    entry: Mapping[str, Any] | None,
    versions: Sequence[Mapping[str, Any]],
) -> list[Finding]:
    """What a published piece owes of `entry`, the current copy the record names as its own,
    or None where it names none (`current_copy.own`), among the record's `versions` (DEC-006
    point 8, DEC-017 points 5 and 6): a copy that is whole, and that nothing it read has
    changed since. It reads the version that wrote the copy, not the last, so a piece set
    back to published is held to it. A copy made over a stale output asks for attention."""
    record = piece.file(pl.EXPORTS_FILE)
    if entry is None:
        said = f"the published piece `{piece.name}` has no current copy of its own"
        return [
            Finding(
                COPY_NONE, FAILS, said, file=record, where=current_copy.FIELD, fix=_export(piece)
            )
        ]
    number = entry["version"]
    found = []
    try:
        lock = current_copy.written_lock(entry, versions)
    except fingerprint.UnreadableFingerprint as exc:
        fix = f"mend {record}, then {_export(piece)}"
        said = f"{record} gives no lock of version {number}, which wrote the current copy: {exc}"
        found.append(
            Finding(COPY_UNREADABLE, FAILS, said, file=record, where=current_copy.FIELD, fix=fix)
        )
    else:
        fix = _made_again(piece, number, lock)
        kept = current_copy.written_fingerprint(entry, versions)
        fonts = pl.recorded_fonts(piece.root, piece.location, kept)
        sources = pl.findings_key_sources(piece.root, held, piece, piece.lock, fonts)
        changes = fingerprint.verify(kept, "export", **sources)
        if changes:
            said = (
                f"the current copy of `{piece.name}`, which version {number} wrote, is stale: "
                f"{'; '.join(changes)}"
            )
            found.append(
                Finding(COPY_STALE, FAILS, said, file=record, where=current_copy.FIELD, fix=fix)
            )
    found.extend(_file_findings(piece, entry, fix))
    for output in current_copy.written_over_stale(entry, versions):
        said = (
            f"the current copy of `{piece.name}`, which version {number} wrote, was made over "
            f"the stale produced picture `{output}`"
        )
        found.append(
            Finding(
                COPY_OVER_STALE,
                ATTENTION,
                said,
                file=record,
                where=current_copy.FIELD,
                fix=f"run {pl.produce_command(piece.name, output)}, then {fix}",
                who=AUTHOR,
            )
        )
    return found


def _export(piece: pl.Piece) -> str:
    """What writes a published piece's current copy."""
    return f"run `pkit visual export {piece.name}`, which makes the copy again"


def _made_again(piece: pl.Piece, number: int, lock: Mapping[str, str]) -> str:
    """What makes again the current copy the version `number` wrote under `lock`. Where the
    piece's lock differs from it, an export refuses, so this names both ways past that
    refusal (DEC-017 point 5)."""
    if piece.lock == lock:
        return _export(piece)
    return (
        f"{_write_back(number, lock)}, and {_export(piece)}; or run `pkit visual upgrade "
        f"{piece.name}` to propose a move of the lock"
    )


def _write_back(number: int, lock: Mapping[str, str]) -> str:
    """What puts back `lock`, the one the version `number` was made under."""
    named = ", ".join(f"{library}@{version}" for library, version in sorted(lock.items()))
    return f"write back the lock of version {number}, {named}, which is no move of it"


def _file_findings(piece: pl.Piece, entry: Mapping[str, Any], fix: str) -> list[Finding]:
    """Each file of the current copy `entry` that is missing, or holds another hash than the
    record's, at the path the record names (DEC-017 point 6). `fix` makes the copy again. An
    export writes over no other file at a place, so a person removes that first (DEC-017
    point 8); in the piece's folder it replaces the file."""
    found = []
    for path, kept in sorted(entry["files"].items()):
        file = current_copy.rooted(piece, path)
        data = _held(piece.root / file)
        if data is None:
            said = f"a file of the current copy of `{piece.name}` is missing"
            found.append(Finding(COPY_FILE_MISSING, FAILS, said, file=file, fix=fix))
        elif current_copy.hash_of(data) != kept:
            said = f"a file of the current copy of `{piece.name}` is not the one its export wrote"
            mend = fix if file == piece.file(path) else f"remove it, then {fix}"
            found.append(Finding(COPY_FILE_CHANGED, FAILS, said, file=file, fix=mend))
    return found


def _held(path: Path) -> bytes | None:
    """What the file at `path` holds, or None where no file can be read there."""
    try:
        return path.read_bytes()
    except OSError:
        return None


def standing_findings(piece: pl.Piece, entry: Mapping[str, Any]) -> list[Finding]:
    """A finding on each file of `entry`, the draft's own current copy, standing at the path
    the record names, whatever it holds: a page may rely on it, and no check holds it to its
    sources (DEC-017 points 5 and 6)."""
    found = []
    for path in sorted(entry["files"]):
        file = current_copy.rooted(piece, path)
        if (piece.root / file).is_file():
            found.append(
                Finding(
                    COPY_STANDING,
                    ATTENTION,
                    f"the draft `{piece.name}` keeps a file of its current copy, which no check "
                    f"holds to its sources",
                    file=file,
                    fix=f"remove it, or publish the piece again in {piece.file(pl.PIECE_FILE)}",
                    who=AUTHOR,
                )
            )
    return found


# --- what a final piece owes of the version handed out ------------------------------------------


def handed_out_findings(piece: pl.Piece) -> list[Finding]:
    """What a final piece owes of the version handed out, read from its record of exports and
    its files, whatever its lock shows (DEC-006 point 8, DEC-017 points 4 and 6). A record that
    cannot be read names no version to hold it to, and `state: final` with none has no version
    to read. Otherwise the piece's state and lock are held to the version, and each of the
    version's files to its hash. What cannot be read of the version leaves the rest read."""
    try:
        number = copies.handed_out(piece.folder)
    except records.RecordError:
        return [_exports_unreadable(piece)]
    if number is None:
        return [_none_handed_out(piece)]
    record = piece.file(pl.EXPORTS_FILE)

    def unreadable(said: str) -> Finding:
        return Finding(
            HANDED_OUT_UNREADABLE,
            FAILS,
            said,
            file=record,
            where=copies.HANDED_OUT_FIELD,
            fix=f"restore what {record} kept of version {number} from the repository's history",
        )

    found = [] if piece.state == copies.FINAL else [_other_state(piece, number)]
    try:
        versions = exports.recorded_versions(piece, exports.recorded(piece))
    except pl.Refused as exc:
        return [*found, unreadable(str(exc))]
    kept = next((each for each in versions if each["version"] == number), None)
    if kept is None:
        return [*found, unreadable(f"{record} hands out version {number}, and keeps no such one")]
    try:
        lock = current_copy.version_lock(kept)
    except fingerprint.UnreadableFingerprint as exc:
        found.append(unreadable(f"{record} gives no lock of version {number}, handed out: {exc}"))
    else:
        if piece.lock != lock:
            found.append(_other_lock(piece, number, lock))
    files = kept.get("files")
    if not isinstance(files, Mapping) or not files:
        return [*found, unreadable(f"{record} names no file of version {number}, handed out")]
    return [*found, *_handed_out_files(piece, number, files)]


def _exports_unreadable(piece: pl.Piece) -> Finding:
    """The finding that says why a piece whose record of exports cannot be read reads as final
    (DEC-017 point 3). It stands beside any finding of the binding pass, which says what is
    wrong with the file and not what follows for the piece. `why_final` is given no state, so
    the record alone answers, whatever the piece's own file says."""
    why = copies.why_final({}, piece.folder)
    return Finding(
        EXPORTS_UNREADABLE,
        FAILS,
        f"the piece `{piece.name}` reads as final, held to no version handed out: {why}",
        file=piece.file(pl.EXPORTS_FILE),
        fix="mend the record, and each command reads the piece by its state again",
    )


def _none_handed_out(piece: pl.Piece) -> Finding:
    """The finding on `state: final` with no version handed out (DEC-017 point 6)."""
    return Finding(
        HANDED_OUT_NONE,
        FAILS,
        f"the piece `{piece.name}` is final, and {piece.file(pl.EXPORTS_FILE)} names no version "
        f"handed out",
        file=piece.file(pl.PIECE_FILE),
        where="state",
        fix=f"run `pkit visual mark-final {piece.name} <version>`, which takes such a piece, or "
        f"set its state back",
    )


def _other_state(piece: pl.Piece, number: int) -> Finding:
    """The finding on a version handed out with another state (DEC-017 point 6)."""
    return Finding(
        HANDED_OUT_STATE,
        FAILS,
        f"{piece.file(pl.EXPORTS_FILE)} hands out version {number}, and the state of "
        f"`{piece.name}` is {piece.state}",
        file=piece.file(pl.PIECE_FILE),
        where="state",
        fix=(
            f"set its state back to {copies.FINAL}, and for new work run "
            f"{copies.take_up_command(piece.name)}, which takes it up again as a new draft"
        ),
    )


def _other_lock(piece: pl.Piece, number: int, lock: Mapping[str, str]) -> Finding:
    """The finding on a version handed out with another lock than `lock`, the one it was made
    under (DEC-017 point 6)."""
    return Finding(
        HANDED_OUT_LOCK,
        FAILS,
        f"the lock of `{piece.name}` is not the one version {number}, handed out, was made under",
        file=piece.file(pl.PIECE_FILE),
        where="lock",
        fix=_write_back(number, lock),
    )


def _handed_out_files(piece: pl.Piece, number: int, files: Mapping[str, Any]) -> list[Finding]:
    """Each of `files`, the file of the version `number` by its name with its hash, that is
    missing from the folder of files handed out, or holds another hash (DEC-006 point 8)."""
    fix = "restore it from the repository's history, as it was handed out"
    found = []
    for name, kept in files.items():
        file = piece.file(f"{fingerprint.HANDED_OUT}/{name}")
        data = _held(piece.root / file)
        if data is None:
            said = f"a file of version {number} of `{piece.name}`, handed out, is missing"
            found.append(Finding(HANDED_OUT_FILE_MISSING, FAILS, said, file=file, fix=fix))
        elif sha256(data) != kept:
            said = f"a file of version {number} of `{piece.name}`, handed out, has changed"
            found.append(Finding(HANDED_OUT_FILE_CHANGED, FAILS, said, file=file, fix=fix))
    return found


# --- content ------------------------------------------------------------------------------------


def id_findings(piece: pl.Piece) -> list[Finding]:
    """The ids of a piece's content (DEC-002 point 4): each of the id shape, unique in its
    list, and the same in every language. A translation may order a list's items its own
    way, so each list's ids are compared as a set with those of the source language. A list
    of runs holds runs, not items, so it is skipped: the components the piece's lock names
    say which lists hold runs, read before the lock is checked (DEC-012 point 1)."""
    found: list[Finding] = []
    lists: dict[str, dict[str, list[Any]]] = {}
    locked = _Locked(piece)
    for language, content in piece.contents.items():
        file = piece.file(pl.content_file(language))
        reader = _Fields(locked, file, [])
        reader.placed(piece.top, content, "")
        for path, items in _lists(content, "", reader.runs):
            ids = [item.get("id") for item in items if isinstance(item, Mapping) and "id" in item]
            lists.setdefault(path, {})[language] = ids
            for item in ids:
                if not names.is_id(item):
                    found.append(
                        Finding(
                            "id-shape",
                            FAILS,
                            f"`{item}` is not an id: a letter, then letters, digits, `-` and "
                            f"`_`, and no word YAML reads as a yes-or-no",
                            file=file,
                            where=path,
                        )
                    )
            twice = sorted({str(item) for item in ids if ids.count(item) > 1})
            if twice:
                found.append(
                    Finding(
                        "id-twice",
                        FAILS,
                        f"the ids {', '.join(f'`{item}`' for item in twice)} appear twice in "
                        f"one list: an id is unique in its list",
                        file=file,
                        where=path,
                    )
                )
    source = piece.languages[0]
    for path, by_language in lists.items():
        expected = {str(item) for item in by_language.get(source, [])}
        for language, ids in by_language.items():
            held = {str(item) for item in ids}
            if held == expected:
                continue
            said = []
            if lacking := expected - held:
                said.append(f"lacks the ids {_shown(lacking)}, which it holds in `{source}`")
            if extra := held - expected:
                said.append(f"holds the ids {_shown(extra)}, which it lacks in `{source}`")
            found.append(
                Finding(
                    "id-languages",
                    FAILS,
                    f"`{path}` in `{language}` {', and '.join(said)}: an item keeps its id in "
                    f"every language",
                    file=piece.file(pl.content_file(language)),
                    where=path,
                )
            )
    return found


def _shown(ids: set[str]) -> str:
    return ", ".join(f"`{item}`" for item in sorted(ids))


def _lists(
    value: Any, path: str, runs: Collection[str] = (), at: str = ""
) -> Iterator[tuple[str, list[Any]]]:
    """Each list of a content value, by a path of keys and places that is the same in
    every language. A list of runs, which `runs` names by its key path as the check of the
    content writes it (`at`, an item by its id where it has one), is no list of items, and
    is skipped (DEC-012 point 1)."""
    if isinstance(value, Mapping):
        for key, item in value.items():
            yield from _lists(item, _join(path, str(key)), runs, _join(at, str(key)))
    elif isinstance(value, list) and at not in runs:
        yield path, value
        for index, item in enumerate(value, start=1):
            yield from _lists(item, f"{path}#{index}", runs, f"{at}{_item(item, index)}")


class _Components(Protocol):
    """What reads a component's data by its use; KeyError where there is none to read."""

    def component(self, use: str) -> Mapping[str, Any]: ...


class _Locked:
    """The components a piece's lock names, and its own, read before its lock is checked:
    what the check of ids needs to know which lists of the content hold runs. A component
    that a use, the lock or its file does not lead to, or that cannot be read as a
    mapping, is none, and the lock's check and the scene report why."""

    def __init__(self, piece: pl.Piece) -> None:
        self.piece = piece
        self.read: dict[str, Mapping[str, Any] | None] = {}

    def component(self, use: str) -> Mapping[str, Any]:
        if use not in self.read:
            self.read[use] = self._read(use)
        found = self.read[use]
        if found is None:
            raise KeyError(use)
        return found

    def _read(self, use: str) -> Mapping[str, Any] | None:
        try:
            library, name = names.split_use(use)
        except ValueError:
            return None
        piece = self.piece
        if library == names.PIECE:
            path = piece.folder / pl.COMPONENTS / f"{name}.yaml"
        else:
            try:
                version = Version.parse(piece.lock.get(library))
            except ValueError:
                return None
            folder = piece.root / piece.location / FOLDER / library / str(version)
            path = folder / pl.COMPONENTS / f"{name}.yaml"
        if not path.is_file():
            return None
        try:
            data = read_yaml(path)
        except ReadError:
            return None
        return data if isinstance(data, Mapping) else None


def content_findings(project: pl.Project) -> list[Finding]:
    """Each content file against the components it fills (DEC-001 point 3, DEC-002 point
    4): a key no component declares as a field or an option, a required field missing, a
    value of another type, a word an option does not take, a page that names no layout of
    its top or one its top does not declare (DEC-010 point 5), a run of a field of runs
    that is not of a run's shape or names a style its field does not declare, and a list
    in a field of text that takes no runs (DEC-012 point 8); the nearest known key, word
    or layout named."""
    found: list[Finding] = []
    piece = project.piece
    for language, content in piece.contents.items():
        reader = _Fields(project.env, piece.file(pl.content_file(language)), found)
        reader.placed(piece.top, content, "")
    return _clashes_once(found)


#: The findings on a key that both an item's component and its list declare, which lie at
#: the piece's lock (DEC-010 points 2 and 9): an item carries it, or no item does.
ITEM_CLASH = "item-clash"
LIST_CLASH = "list-clash"


def _clashes_once(found: list[Finding]) -> list[Finding]:
    """The content's findings, each clash at the lock reported once across the piece's
    languages: a key that both a component and a list declare is stated as a fact only
    where no item of the list that the component draws carries it, in any language."""
    carried = {f.extra.get("clash") for f in found if f.code == ITEM_CLASH}
    kept: list[Finding] = []
    seen: set[tuple[str, str, str, str, str]] = set()
    for finding in found:
        if finding.code == LIST_CLASH and finding.extra.get("clash") in carried:
            continue
        if finding.code in (ITEM_CLASH, LIST_CLASH):
            if _mark(finding) in seen:
                continue
            seen.add(_mark(finding))
        kept.append(finding)
    return kept


@dataclasses.dataclass(frozen=True)
class _Listed:
    """A list field a component draws, as the check of the content reads its items: the
    component that draws an item that names none (`draw`), what the component that
    repeats over it declares for it (DEC-010 points 1 to 4), and the field of this
    component in which content gives its component field, where content can give it."""

    draw: Any
    fields: layout.ListFields
    component: str | None


@dataclasses.dataclass(frozen=True)
class _Reader:
    """What reads a mapping of the content, as an end's key path walks it: the fields its
    component, or a top's layout, declares, and the lists it draws."""

    fields: frozenset[str]
    repeats: Mapping[str, _Listed]


class _Fields:
    """Reads content against the `fields` of the components it fills: the fixed subset of
    JSON Schema format 1 takes (`type`, `properties`, `required`, `items`, `minItems`,
    `maxItems`, `enum`, `const`, a local `$ref`), a key no property names refused. A field
    marked `x-pkit-runs` takes text, against its schema, or a list of runs, each against
    the words of its run styles (DEC-012 point 7). `runs` keeps the key path of each list
    of runs it read."""

    def __init__(self, env: _Components, file: str, found: list[Finding]) -> None:
        self.env = env
        self.file = file
        self.found = found
        self.runs: set[str] = set()

    def _fail(self, code: str, path: str, message: str) -> None:
        self.found.append(Finding(code, FAILS, message, file=self.file, where=path))

    def placed(
        self,
        use: str,
        value: Mapping[str, Any],
        path: str,
        listed: _Listed | None = None,
        list_at: str = "",
    ) -> None:
        """A mapping that places the component `use`; where it is an item of the list at
        `list_at`, `listed` says what that list declares. An item's keys are its
        component's fields and options, the reserved keys, its list's arrangement fields,
        each of which takes a word it declares, and, in a list of ties, its list's end
        fields (`_tie`). A key that both its component and its list declare is read by
        neither (DEC-010 point 2, DEC-011 point 1): it is no finding in the content, and lies
        at the lock (`_clash`)."""
        try:
            component = self.env.component(use)
        except KeyError:
            return  # the scene reports a component that does not exist, or cannot be read
        fields = component.get("fields") if isinstance(component.get("fields"), Mapping) else {}
        options = component.get("options") if isinstance(component.get("options"), Mapping) else {}
        repeats = self._repeats(component, (use,))
        own = {*(fields.get("properties") or {}), *options}
        arranged = listed.fields.arrangement if listed is not None else {}
        keys = set(listed.fields.keys) if listed is not None else set()
        claimed = own & keys
        if keys:
            lead = f"neither `{use}` nor the list `{list_at}` declares a key"
        else:
            lead = f"`{use}` takes no field or option"
        self._keys(value, {*own, *keys, *names.RESERVED_PLACING_KEYS}, path, lead)
        for name in sorted(claimed):
            outcome = (
                f"the arrangement field takes its default `{arranged[name].default}`"
                if name in arranged
                else "the tie lacks that end, and is left out"
            )
            self._clash(use, name, path if name in value else "", list_at, outcome)
        self._words(value, path, {n: o for n, o in options.items() if n not in claimed}, use)
        for name, each in arranged.items():
            if name in value and name not in claimed and value[name] not in each.words:
                self._word(
                    _join(path, name),
                    value[name],
                    each.words,
                    f"the arrangement field `{name}` of the list `{list_at}`",
                )
        forms = page_forms(component) if isinstance(component.get("layouts"), Mapping) else None
        unread = frozenset(name for name in claimed if name in value)
        self._object(
            fields, value, path, fields, repeats, keys_checked=True, forms=forms, unread=unread
        )
        if forms is None:
            return
        for name in forms.fields:
            if isinstance(value.get(name), list):
                self._pages(use, component, forms, value[name], _join(path, name))

    def _words(
        self, value: Mapping[str, Any], path: str, options: Mapping[str, Any], use: str
    ) -> None:
        """Each option of words `value` gives, against the words the option declares."""
        for name, option in options.items():
            if name in value and isinstance(option, list) and value[name] not in option:
                self._word(
                    _join(path, name), value[name], option, f"the option `{name}` of `{use}`"
                )

    def _word(self, path: str, given: Any, words: Sequence[Any], what: str) -> None:
        close = nearest(str(given), [str(word) for word in words])
        hint = f"; did you mean `{close}`?" if close else ""
        self._fail(
            "content-option",
            path,
            f"`{given}` is no word of {what} ({', '.join(map(str, words))}){hint}",
        )

    def _clash(self, use: str, key: str, carried: str, list_at: str, outcome: str) -> None:
        """A key that both the component `use` and the list at `list_at` declare (DEC-010
        points 2 and 9, DEC-011 point 1), with what follows on an item that carries it:
        `outcome`. It lies at the piece's lock, which combines the two: where the item at
        `carried` carries it, it fails; otherwise it states a fact, so the content's author
        learns of it before writing one, and `_clashes_once` keeps the fact only where no
        item carries the key."""
        lock = PurePosixPath(self.file).with_name(pl.PIECE_FILE).as_posix()
        both = f"under this lock, `{use}` and the list `{list_at}` both declare `{key}`"
        if carried:
            finding = Finding(
                ITEM_CLASH,
                FAILS,
                f"{both}, which the item `{carried}` carries in "
                f"{PurePosixPath(self.file).name}: neither reads it, so `{use}` leaves it "
                f"unfilled, and {outcome}",
                file=lock,
                where="lock",
                fix="take the key off the item, or move the lock to versions under which the "
                "item's component and its list do not both declare it",
            )
        else:
            finding = Finding(
                LIST_CLASH,
                FACT,
                f"{both}: neither would read it on an item of the list that `{use}` draws",
                file=lock,
                where="lock",
            )
        self.found.append(dataclasses.replace(finding, extra={"clash": (list_at, use, key)}))

    def _pages(
        self,
        use: str,
        component: Mapping[str, Any],
        forms: PageForms,
        pages: list[Any],
        path: str,
    ) -> None:
        """The pages of a top whose layouts are its pages' forms (DEC-010 point 5): each a
        mapping that names one of the top's layouts with `layout` and fills its slots, or
        places the component it names with `use`."""
        for place, page in enumerate(pages, start=1):
            at = f"{path}{_item(page, place)}"
            if not isinstance(page, Mapping):
                self._fail("content-type", at, f"the page holds {_type_name(page)}, not object")
            elif isinstance(page.get("use"), str):
                self.placed(page["use"], page, at)
            elif LAYOUT not in page:
                self._fail(
                    "content-layout",
                    at,
                    f"the page names neither a layout of `{use}` with `{LAYOUT}` "
                    f"({', '.join(forms.layouts)}) nor a component with `use`",
                )
            elif page[LAYOUT] not in forms.layouts:
                close = nearest(str(page[LAYOUT]), sorted(forms.layouts))
                hint = f"; did you mean `{close}`?" if close else ""
                self._fail(
                    "content-layout",
                    _join(at, LAYOUT),
                    f"`{use}` has no layout `{page[LAYOUT]}` ({', '.join(forms.layouts)}){hint}",
                )
            else:
                chosen = page[LAYOUT]
                slots, required = forms.layouts[chosen]
                known = {*slots, LAYOUT, *names.RESERVED_PLACING_KEYS}
                self._keys(page, known, at, f"the layout `{chosen}` of `{use}` takes no slot")
                schema = {"type": "object", "properties": slots, "required": list(required)}
                decl = (component.get("layouts") or {}).get(chosen)
                parts = decl.get("parts") if isinstance(decl, Mapping) else None
                lists = decl.get("lists") if isinstance(decl, Mapping) else None
                drawing = {"parts": parts, "lists": lists}
                repeats = self._repeats(drawing, (use,)) if isinstance(parts, Mapping) else {}
                self._object(schema, page, at, schema, repeats, keys_checked=True)

    def _component_field(self, value: Any, path: str, list_at: str) -> None:
        """A list's component field (DEC-010 point 1): a mapping that names a component by
        `use`, with words for its options, and `concept`, `state` and `override`, which the
        scene reads on each item that takes them. It places nothing, so none of the
        component's required fields is asked of it, and it gives no id and no field: an id
        names one thing, and a field holds what one item shows."""
        what = f"the component field of the list `{list_at}`"
        if not isinstance(value, Mapping) or not isinstance(value.get("use"), str):
            self._fail(
                "content-component",
                path,
                f"{what} names no component: it takes `{{use: <library>/<component>}}`, with "
                "words for that component's options",
            )
            return
        use = value["use"]
        try:
            component = self.env.component(use)
        except KeyError:
            return  # the scene reports a component that does not exist, or cannot be read
        fields = component.get("fields") if isinstance(component.get("fields"), Mapping) else {}
        options = component.get("options") if isinstance(component.get("options"), Mapping) else {}
        properties = fields.get("properties") or {}
        for key in value:
            if key == "id":
                self._fail(
                    "content-component",
                    _join(path, "id"),
                    f"{what} gives an id: it names the component of every item, and an id "
                    "names one thing",
                )
            elif key in properties:
                self._fail(
                    "content-component",
                    _join(path, str(key)),
                    f"{what} gives `{key}`, a field of `{use}`: a field holds what one item "
                    "shows, so each item gives its own",
                )
        known = {*properties, *options, *names.RESERVED_PLACING_KEYS}
        self._keys(value, known, path, f"`{use}` takes no option")
        self._words(value, path, options, use)

    def _repeats(self, component: Mapping[str, Any], chain: tuple[str, ...]) -> dict[str, _Listed]:
        """Each list field of `component` that a part draws, with the component its `draw`
        names and what the component that repeats over it declares for it under `lists`
        (DEC-010): a `repeat` part of its own, else, at any depth, one of a component a
        `use` part places, which the part passes the list on to under another name. The
        list's component field is the field of `component` that content gives it in: its
        own, or the one a `use` part passes on as it. `chain` holds the components on the
        way, so one that places itself ends the search."""
        parts = component.get("parts") or {}
        declared = layout.list_fields(component)
        repeats = {}
        for spec in parts.values():
            listed = spec.get("repeat") if isinstance(spec, Mapping) else None
            if isinstance(listed, str):
                fields = declared.get(listed, layout.ListFields(None, {}))
                repeats[listed] = _Listed(spec.get("draw"), fields, fields.component)
        for spec in parts.values():
            use = spec.get("use") if isinstance(spec, Mapping) else None
            bound = spec.get("fields") if isinstance(spec, Mapping) else None
            if not isinstance(use, str) or use in chain or not isinstance(bound, Mapping):
                continue
            try:
                placed = self._repeats(self.env.component(use), (*chain, use))
            except KeyError:
                continue  # the scene reports a component that does not exist, or cannot be read
            for theirs, ours in bound.items():
                # A list of ties is drawn only where its end fields are declared (DEC-011
                # point 1): the component reports a part that passes one on.
                if (
                    theirs in placed
                    and isinstance(ours, str)
                    and placed[theirs].fields.ends is None
                ):
                    inner = placed[theirs]
                    passed = bound.get(inner.component) if inner.component else None
                    given = passed if isinstance(passed, str) else None
                    repeats.setdefault(ours, dataclasses.replace(inner, component=given))
        return repeats

    def _keys(self, value: Mapping[str, Any], known: set[str], path: str, lead: str) -> None:
        for key in value:
            if key not in known:
                close = nearest(str(key), sorted(known - set(names.RESERVED_PLACING_KEYS)))
                hint = f"; did you mean `{close}`?" if close else ""
                self._fail("content-key", _join(path, str(key)), f"{lead} `{key}`{hint}")

    def _object(
        self,
        schema: Mapping[str, Any],
        value: Mapping[str, Any],
        path: str,
        root: Mapping[str, Any],
        repeats: Mapping[str, _Listed] | None = None,
        *,
        keys_checked: bool = False,
        forms: PageForms | None = None,
        unread: frozenset[str] = frozenset(),
    ) -> None:
        """`value` against the object `schema`. A field `forms` marks as holding pages is
        checked as a list here, and its pages by `_pages`. Each item of a list that
        `repeats` names is read against the component that draws it: the one it names, else
        the one its list's component field names, else the list's default (DEC-010 point
        1); a tie's ends also by `_tie`, from `value`, the mapping that holds its list. A
        list's component field is read by `_component_field`. A key of `unread` is read by
        neither the component nor the list, so it is judged at the lock alone."""
        properties = schema.get("properties") or {}
        repeats = repeats or {}
        component_fields = {
            listed.component: key for key, listed in repeats.items() if listed.component
        }
        if not keys_checked:
            self._keys(value, set(properties), path, "no field is named")
        for key in schema.get("required") or []:
            if key not in value:
                self._fail("content-required", _join(path, key), f"the field `{key}` is required")
        for key, item in value.items():
            if key not in properties or key in unread:
                continue
            at = _join(path, key)
            listed = repeats.get(key)
            if forms is not None and key in forms.fields:
                self._value(properties[key], item, at, root, items=False)
            elif listed is not None and isinstance(item, list):
                self._value(properties[key], item, at, root, items=False)
                field = value.get(listed.component) if listed.component else None
                named = field.get("use") if isinstance(field, Mapping) else None
                reader = _Reader(frozenset(properties), repeats)
                for place, entry in enumerate(item, start=1):
                    if isinstance(entry, Mapping):
                        use = entry.get("use", named if isinstance(named, str) else listed.draw)
                        entry_at = f"{at}{_item(entry, place)}"
                        if listed.fields.ends is not None:
                            by_content = "use" in entry or isinstance(named, str)
                            self._tie(entry, entry_at, use, by_content, listed, value, reader, path)
                        if isinstance(use, str):
                            self.placed(use, entry, entry_at, listed, at)
            elif key in component_fields:
                self._component_field(item, at, _join(path, component_fields[key]))
            elif isinstance(item, Mapping) and isinstance(item.get("use"), str):
                self.placed(item["use"], item, at)
            else:
                self._value(properties[key], item, at, root)

    def _tie(
        self,
        entry: Mapping[str, Any],
        at: str,
        use: Any,
        by_content: bool,
        listed: _Listed,
        holder: Mapping[str, Any],
        reader: _Reader,
        holder_at: str,
    ) -> None:
        """A tie of a list of ties (DEC-011 points 1 to 3 and 8): a component content names
        for it takes ends (`tie-component`); each end field gives `{item: <key path>}`, with
        a point's name where it names one (`tie-shape`); each key path leads, from `holder`,
        the mapping that holds the list, at `holder_at`, through what content holds and the
        components that draw it, to an item (`tie-path`); and an end names no tie, the two
        ends never one item, and neither leads through the other (`tie-ends`). A default
        component that takes no ends is the pattern's to mend, and is judged there. Where an
        end field is also a field or an option of the tie's component, the lock reports it
        (`_clash`), and no end of it is read here."""
        claimed: set[str] = set()
        if isinstance(use, str):
            try:
                component = self.env.component(use)
            except KeyError:
                component = None  # the scene reports a component there is none of
            if component is not None:
                fields = component.get("fields")
                properties = fields.get("properties") if isinstance(fields, Mapping) else None
                claimed = {*(properties or {}), *(component.get("options") or {})}
                if by_content and component.get("ends") is not True:
                    self._fail(
                        "tie-component",
                        at,
                        f"`{use}` takes no ends, and draws a tie of `{holder_at or 'the top'}`: "
                        "every item of a list of ties is a tie",
                    )
        paths: dict[str, str] = {}
        for field_name in listed.fields.ends or ():
            if field_name in claimed:
                continue
            end_at = _join(at, field_name)
            end = entry.get(field_name)
            if (
                not isinstance(end, Mapping)
                or not isinstance(end.get("item"), str)
                or set(end) - set(layout.END_KEYS)
                or ("point" in end and not names.is_name(end["point"]))
            ):
                given = "nothing" if end is None else f"`{end}`"
                self._fail(
                    "tie-shape",
                    end_at,
                    f"the end field `{field_name}` gives {given}: an end takes "
                    "`{item: <key path>}`, with `point: <name>` where it ends at a point",
                )
                continue
            reached = self._end_path(end["item"], holder, reader)
            if isinstance(reached, str):
                self._fail("tie-path", _join(end_at, "item"), f"`{end['item']}` {reached}")
            elif reached:
                self._fail(
                    "tie-ends",
                    _join(end_at, "item"),
                    f"`{end['item']}` names a tie: a tie joins two items, never a line",
                )
            else:
                paths[field_name] = end["item"]
        if len(paths) == 2:
            first, second = paths.values()
            if through(first, second):
                same = "names one item" if first == second else "leads through the other"
                self._fail(
                    "tie-ends",
                    at,
                    f"one of the tie's ends {same}: `{first}` and `{second}`; a tie joins two "
                    "items, neither inside the other",
                )

    def _end_path(self, text: str, holder: Mapping[str, Any], reader: _Reader) -> str | bool:
        """Where the key path `text` leads from `holder`, read by `reader` (DEC-011 point
        3): why it leads to no item, else whether that item is a tie. Each key is a field
        of the component that draws the mapping, where one does; each step into a list
        names an item by its id, and only there. A mapping no component draws is read by
        its keys alone."""
        steps = key_path(text)
        if steps is None:
            return (
                "is no key path: the content file's keys joined by `.`, each item by its id "
                "as `<list>[<id>]`"
            )
        mapping: Any = holder
        current: _Reader | None = reader
        tie = False
        for place, (key, item_id) in enumerate(steps):
            last = place == len(steps) - 1
            if not isinstance(mapping, Mapping):
                return f"steps into `{key}` below what is no mapping"
            if current is not None and key not in current.fields:
                close = nearest(key, sorted(current.fields))
                hint = f"; did you mean `{close}`?" if close else ""
                return f"names `{key}`, which no component on the way declares{hint}"
            if key not in mapping:
                return f"names `{key}`, which the content does not give"
            value = mapping[key]
            if item_id is None:
                if isinstance(value, list):
                    return f"steps into the list `{key}` with no id: name its item as `[<id>]`"
                if last:
                    return f"ends at `{key}`, which is no item of a list"
                mapping, tie = value, False
                current = self._reader_of(value.get("use") if isinstance(value, Mapping) else None)
                continue
            if not isinstance(value, list):
                return f"names the item `[{item_id}]` of `{key}`, which is no list"
            entry = next(
                (e for e in value if isinstance(e, Mapping) and e.get("id") == item_id), None
            )
            if entry is None:
                return f"names `[{item_id}]`, which the list `{key}` does not hold"
            drawn = current.repeats.get(key) if current is not None else None
            tie = drawn is not None and drawn.fields.ends is not None
            if drawn is None:
                use = None
            else:
                field = mapping.get(drawn.component) if drawn.component else None
                named = field.get("use") if isinstance(field, Mapping) else None
                use = entry.get("use", named if isinstance(named, str) else drawn.draw)
            mapping, current = entry, self._reader_of(use)
        return tie

    def _reader_of(self, use: Any) -> _Reader | None:
        """What reads a mapping that places the component `use`: its fields and the lists it
        draws; None where it names no component that can be read."""
        if not isinstance(use, str):
            return None
        try:
            component = self.env.component(use)
        except KeyError:
            return None
        fields = component.get("fields")
        properties = fields.get("properties") if isinstance(fields, Mapping) else None
        return _Reader(frozenset(properties or {}), self._repeats(component, (use,)))

    def _value(
        self, schema: Any, value: Any, path: str, root: Mapping[str, Any], *, items: bool = True
    ) -> None:
        if isinstance(value, list) and isinstance(schema, Mapping) and RUNS in schema:
            if run_problem(path, schema) is None:
                self.runs.add(path)
                self._runs(tuple(schema[RUNS]), value, path)
                return
        schema = _resolved(schema, root)
        if not isinstance(schema, Mapping):
            return
        wanted = schema.get("type")
        if wanted is not None and not any(_is_type(value, t) for t in _as_list(wanted)):
            kinds = _as_list(wanted)
            if isinstance(value, list) and "string" in kinds and "array" not in kinds:
                self._fail(
                    "runs-unmarked",
                    path,
                    "the field holds a list, and takes text: only a field its component "
                    f"marks `{RUNS}` takes a list of runs",
                )
                return
            self._fail(
                "content-type",
                path,
                f"the field holds {_type_name(value)}, not {' or '.join(_as_list(wanted))}",
            )
            return
        if "enum" in schema and value not in schema["enum"]:
            self._fail("content-value", path, f"`{value}` is not one of {schema['enum']}")
        if "const" in schema and value != schema["const"]:
            self._fail("content-value", path, f"`{value}` is not `{schema['const']}`")
        if isinstance(value, list):
            if len(value) < schema.get("minItems", 0):
                self._fail(
                    "content-count",
                    path,
                    f"the list holds {len(value)} item(s), fewer than {schema['minItems']}",
                )
            if "maxItems" in schema and len(value) > schema["maxItems"]:
                self._fail(
                    "content-count",
                    path,
                    f"the list holds {len(value)} item(s), more than {schema['maxItems']}",
                )
            if items and "items" in schema:
                for place, entry in enumerate(value, start=1):
                    self._value(schema["items"], entry, f"{path}{_item(entry, place)}", root)
        elif isinstance(value, Mapping) and (
            "properties" in schema or schema.get("type") == "object"
        ):
            self._object(schema, value, path, root)

    def _runs(self, words: tuple[str, ...], runs: list[Any], path: str) -> None:
        """A field's list of runs (DEC-012 points 1 and 2): each run text, or a mapping whose
        `text` holds text, which may hold `style`, a word of its field's run styles, and
        `concept`, and no other key. A run lies at its field's path and its place among the
        field's runs. The scene reads a run's concept, with the piece's notations, as it
        reads an item's."""
        for place, run in enumerate(runs, start=1):
            at = f"{path}#{place}"
            if isinstance(run, str):
                continue
            if not isinstance(run, Mapping):
                self._fail(
                    "run-shape",
                    at,
                    f"the run holds {_type_name(run)}, not text or a mapping of `text`, "
                    "`style` and `concept`",
                )
                continue
            for key in run:
                if key not in RUN_KEYS:
                    close = nearest(str(key), list(RUN_KEYS))
                    hint = f"; did you mean `{close}`?" if close else ""
                    self._fail(
                        "run-key",
                        _join(at, str(key)),
                        f"a run takes no key `{key}`, only `text`, `style` and `concept`{hint}",
                    )
            if "text" not in run:
                self._fail("run-shape", at, "the run holds no `text`")
            elif not isinstance(run["text"], str):
                self._fail(
                    "run-shape",
                    _join(at, "text"),
                    f"the run holds {_type_name(run['text'])} in `text`, not text",
                )
            if "style" in run and not any(run["style"] == word for word in words):
                close = nearest(str(run["style"]), list(words))
                hint = f"; did you mean `{close}`?" if close else ""
                self._fail(
                    "run-style",
                    _join(at, "style"),
                    f"`{run['style']}` is no run style of the field ({', '.join(words)}){hint}",
                )


def _join(path: str, key: str) -> str:
    return f"{path}.{key}" if path else key


def _item(entry: Any, place: int) -> str:
    """An item's step in a path, as a trace id writes it: by its id, else its place."""
    if isinstance(entry, Mapping) and names.is_id(entry.get("id")):
        return f"[{entry['id']}]"
    return f"#{place}"


def _as_list(value: Any) -> list[str]:
    return [str(v) for v in value] if isinstance(value, list) else [str(value)]


def _is_type(value: Any, wanted: str) -> bool:
    if wanted == "object":
        return isinstance(value, Mapping)
    if wanted == "array":
        return isinstance(value, list)
    if wanted == "string":
        return isinstance(value, str)
    if wanted == "boolean":
        return isinstance(value, bool)
    if wanted == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if wanted == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if wanted == "null":
        return value is None
    return True


def _type_name(value: Any) -> str:
    for wanted in ("object", "array", "string", "boolean", "integer", "number", "null"):
        if _is_type(value, wanted):
            return f"a{'n' if wanted[0] in 'aeiou' else ''} {wanted}"
    return type(value).__name__


def _resolved(schema: Any, root: Mapping[str, Any]) -> Any:
    """`schema`, its local `$ref` (`#/...`) followed within the component's fields."""
    seen = 0
    while isinstance(schema, Mapping) and isinstance(schema.get("$ref"), str) and seen < 16:
        ref: str = schema["$ref"]
        if not ref.startswith("#"):
            return None
        target: Any = root
        for part in [p for p in ref[1:].split("/") if p]:
            part = part.replace("~1", "/").replace("~0", "~")
            target = target.get(part) if isinstance(target, Mapping) else None
        schema, seen = target, seen + 1
    return schema


# --- the findings record ------------------------------------------------------------------------


def read_findings_record(root: Path, held: Held, piece: pl.Piece) -> list[Finding] | None:
    """The findings a piece's `findings.yaml` keeps, while its key verifies against the
    current files; None when it is missing, cannot be read, or does not verify."""
    path = piece.folder / pl.FINDINGS_FILE
    if not path.is_file():
        return None
    try:
        data = read_bound(path, "findings")
        key = data["key"]
        sources = pl.findings_key_sources(
            root, held, piece, piece.lock, pl.recorded_fonts(root, piece.location, key)
        )
        if fingerprint.verify(key, "findings-key", **sources):
            return None
        return [_stored(entry) for entry in data["findings"]]
    except (ReadError, FileError, KeyError, TypeError, ValueError, AttributeError):
        return None


def _stored(entry: Mapping[str, Any]) -> Finding:
    return Finding(
        str(entry["code"]),
        str(entry["level"]),
        str(entry["message"]),
        file=str(entry.get("file", "")),
        where=str(entry.get("where", "")),
        fix=str(entry.get("fix", "")),
        library=str(entry.get("library", "")),
        who=str(entry.get("who", "")),
    )


def record_entry(finding: Finding) -> dict[str, Any]:
    """A scene finding as the findings record keeps it."""
    entry: dict[str, Any] = {
        "code": finding.code,
        "level": finding.level,
        "message": finding.message,
    }
    if finding.file:
        entry["file"] = finding.file
    entry["where"] = finding.where
    for name in ("fix", "library", "who"):
        if getattr(finding, name):
            entry[name] = getattr(finding, name)
    return entry


def rooted(finding: Finding, piece: pl.Piece) -> Finding:
    """A scene finding with its file relative to the project root: from a library
    version's folder where it lies in one, else from the piece's folder."""
    name, _, version = finding.library.partition("@")
    if version:
        base = f"{piece.location}/{FOLDER}/{name}/{version}"
        file = f"{base}/{finding.file}" if finding.file else base
    else:
        file = piece.file(finding.file)
    return dataclasses.replace(finding, file=file)


# --- scene findings -----------------------------------------------------------------------------


def computed(project: pl.Project) -> list[Finding]:
    """The scene findings of a piece, its scenes computed now; a font that refuses the
    render is one."""
    try:
        results = project.scenes()
    except MissingFont as exc:
        return [
            Finding(
                "font-missing",
                FAILS,
                f"the render is refused before anything is laid out: {exc}",
                file=pl.PIECE_FILE,
                where="brand",
                fix="commit the font's file and name it in the brand, or name another family",
            )
        ]
    return scene_findings(project, results)


def scene_findings(
    project: pl.Project, results: Sequence[tuple[str, SceneResult]]
) -> list[Finding]:
    """What computing a piece's scenes found, each finding once, in a fixed order; files
    relative to the piece's folder, or to a library version's folder where the finding
    lies in one (the findings record keeps them so).

    Each scene is computed at one key over the size axes, and contrast is measured on it in
    each combination it serves. A finding the scenes of every key find alike is reported
    once, as it reads. Any other is reported for each key whose scenes find it, its message
    opening with that key, so a finding takes no field for its size."""
    piece = project.piece
    document = project.values()
    colours = {
        path: token["values"]
        for path, token in document["tokens"].items()
        if token["type"] == "color"
    }
    by_size: dict[str, dict[tuple[str, str, str, str, str], Finding]] = {
        size: {} for size in dict.fromkeys(result.scene.size_key for _, result in results)
    }
    for language, result in results:
        size = result.scene.size_key
        served = [key for key in project.keys if project.size_key(key) == size]
        content = pl.content_file(language)
        found = [_placed(finding, content, project) for finding in result.findings]
        scene = result.scene.to_dict()
        found.extend(drawn_contrast(scene, colours, served))
        found.extend(_unknown_colours(scene, colours))
        for renderer in renderers(piece):
            declared = seam.declaration(renderer, seam.RENDERER)
            for loss in losses(scene, declared):
                if not accepted(loss, piece.accepted_losses):
                    found.append(loss_finding(loss))
        found.extend(_statuses(scene, project.env))
        for finding in found:
            by_size[size].setdefault(_mark(finding), finding)
    unique: dict[tuple[str, str, str, str, str], Finding] = {}
    for size, found_at in by_size.items():
        for mark, finding in found_at.items():
            if all(mark in other for other in by_size.values()):
                unique.setdefault(mark, finding)
            else:
                sized = dataclasses.replace(finding, message=f"`{size}`: {finding.message}")
                unique.setdefault(_mark(sized), sized)
    return sorted(unique.values(), key=lambda f: (f.file, f.where, f.code, f.message))


def _placed(finding: Finding, content: str, project: pl.Project) -> Finding:
    """An engine finding placed in the file a person edits to mend it: the piece's own file
    where it lies in what the piece names (`piece`), its top or its lock (DEC-008 point 9);
    the file of the component it names (`component`), the piece's own in its `components/`
    and a library's in the locked version's; with neither, the content file. A missing
    picture gets why, and the command that makes it."""
    library, _, name = str(finding.extra.get("component") or "").partition("/")
    versioned, _, version = finding.library.partition("@")
    if finding.extra.get("piece"):
        finding = dataclasses.replace(finding, library="", file=pl.PIECE_FILE)
    elif library == names.PIECE and name:
        finding = dataclasses.replace(finding, library="", file=f"{pl.COMPONENTS}/{name}.yaml")
    elif library == versioned and name and version:
        finding = dataclasses.replace(finding, file=f"{pl.COMPONENTS}/{name}.yaml")
    elif version:
        finding = dataclasses.replace(finding, file="")  # the version's folder
    else:
        finding = dataclasses.replace(finding, library="", file=content)
    if finding.code == "missing-picture":
        for output, why in project.env.missing.items():
            if f"`{output}`" in finding.message:
                return dataclasses.replace(
                    finding,
                    message=f"{finding.message}: {why}",
                    fix=f"run {pl.produce_command(project.piece.name, output)}",
                )
    return finding


def _walk(
    elements: Sequence[Mapping[str, Any]], x: float = 0.0, y: float = 0.0
) -> Iterator[tuple[Mapping[str, Any], float, float]]:
    """Each element in draw order, with the place of its parent's origin."""
    for element in elements:
        yield element, x, y
        if element.get("type") == "group":
            yield from _walk(
                element.get("children", []),
                x + float(element.get("x", 0)),
                y + float(element.get("y", 0)),
            )


def _pages(scene: Mapping[str, Any]) -> Iterator[Mapping[str, Any]]:
    wanted = set(scene.get("pages", []))
    for element, _, _ in _walk(scene.get("children", [])):
        if element.get("id") in wanted:
            yield element


def drawn_contrast(
    scene: Mapping[str, Any], colours: Mapping[str, Mapping[str, Any]], keys: Sequence[str]
) -> list[Finding]:
    """Each run of each text of a scene measured against the fill under it, in each
    combination `keys` names, at WCAG's level for the run's size and weight, in the run's
    own paint (DEC-004 point 8, DEC-012 point 3). The fill under a run's span of a line is
    that of the last box or ellipse drawn before the text that holds the span's middle; a
    translucent one is laid over the one under it. A text over a picture is not measured,
    nor one with nothing under it."""
    found = []
    for page in _pages(scene):
        painted: list[tuple[Mapping[str, Any], float, float]] = []
        for element, x, y in _walk(page.get("children", [])):
            kind = element.get("type")
            if kind in ("box", "ellipse", "image"):
                painted.append((element, x, y))
            elif kind == "text" and element.get("lines"):
                found.extend(_text_contrast(element, x, y, painted, colours, keys))
    return found


def _text_contrast(
    text: Mapping[str, Any],
    x: float,
    y: float,
    painted: Sequence[tuple[Mapping[str, Any], float, float]],
    colours: Mapping[str, Mapping[str, Any]],
    keys: Sequence[str],
) -> list[Finding]:
    left, width = x + float(text["x"]), float(text["width"])
    step = float(text["line-height"])
    paragraphs = text.get("paragraphs") or [[{}]]
    # Each look of a run and the fills under its spans, in the order first met.
    measured: list[tuple[Mapping[str, Any], list[str]]] = []
    looks: list[tuple[Any, ...]] = []
    for index, line in enumerate(text["lines"]):
        runs = paragraphs[line.get("paragraph", 0)] or [{}]
        drawn = float(line.get("width", 0))
        at = {"middle": left + (width - drawn) / 2, "end": left + width - drawn}.get(
            str(text.get("text-anchor")), left
        )
        middle = y + float(text["y"]) + index * step + step / 2
        # A line with no span is measured at its start, in its paragraph's first run.
        spans = line.get("spans") or [{"run": 0, "width": 0}]
        for span in spans:
            run = runs[int(span.get("run", 0))]
            span_width = float(span.get("width", 0))
            stack = _under((at + span_width / 2, middle), painted)
            if stack is None:
                return []  # over a picture: a reviewer judges it
            at += span_width
            look = (run.get("fill"), run.get("font-size"), run.get("font-weight"), stack)
            if stack and look not in looks:
                looks.append(look)
                measured.append((run, stack))
    found = []
    for run, stack in measured:
        found.extend(_run_contrast(text, run, stack, colours, keys))
    return found


def _run_contrast(
    text: Mapping[str, Any],
    run: Mapping[str, Any],
    stack: Sequence[str],
    colours: Mapping[str, Mapping[str, Any]],
    keys: Sequence[str],
) -> list[Finding]:
    """A run of a text measured against one stack of fills under it, in its own paint, at
    WCAG's level for its size and weight."""
    role = run.get("fill")
    if role is not None and role not in colours:
        return []  # a colour role the brand lacks is a finding of its own
    if any(fill not in colours for fill in stack):
        return []
    size, weight = float(run.get("font-size", 0)), run.get("font-weight")
    bold = isinstance(weight, (int, float)) and weight >= BOLD
    level = "large-text" if size >= LARGE or (size >= LARGE_BOLD and bold) else "text"
    minimum = tokens.LEVELS[level]
    found = []
    for key in keys:
        ground = _ground([colours[fill][key] for fill in stack])
        if ground is None:
            continue
        ink = colours[role][key] if role is not None else BLACK
        ratio = tokens.contrast_ratio(ink, ground)
        if ratio < minimum:
            found.append(
                Finding(
                    "contrast-drawn",
                    FAILS,
                    f"`{role or 'black'}` on `{stack[-1]}` has the contrast {ratio:.2f} in "
                    f"the combination `{key}`, below the {minimum} a text of {size:g} px "
                    f"needs (`{level}`)",
                    file=pl.PIECE_FILE,
                    where=str(text["id"]),
                    fix="change the colour roles of the text or of what lies under it, in "
                    "the component, its content's `override`, or the brand",
                )
            )
    return found


def _under(
    point: tuple[float, float], painted: Sequence[tuple[Mapping[str, Any], float, float]]
) -> list[str] | None:
    """The fills under a point, bottom first, down to the first opaque one; None when a
    picture lies over it. Translucent fills are judged in `_ground`."""
    stack: list[str] = []
    for element, x, y in reversed(painted):
        if not _holds(element, x, y, point):
            continue
        if element.get("type") == "image":
            return stack or None
        fill = element.get("fill")
        if fill is None:
            continue
        stack.insert(0, str(fill))
        if len(stack) > 8:
            break
    return stack


def _ground(stack: Sequence[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    """The colour a stack of fills shows, bottom first; None when nothing opaque lies under
    a translucent one."""
    ground: Mapping[str, Any] | None = None
    for fill in stack:
        alpha = float(fill.get("alpha", 1))
        if alpha >= 1:
            ground = fill
        elif ground is not None:
            ground = {
                "colorSpace": "srgb",
                "components": [
                    f * alpha + g * (1 - alpha)
                    for f, g in zip(fill["components"], ground["components"], strict=True)
                ],
                "alpha": 1,
            }
    return ground


def _holds(element: Mapping[str, Any], x: float, y: float, point: tuple[float, float]) -> bool:
    left, top = x + float(element.get("x", 0)), y + float(element.get("y", 0))
    width, height = float(element.get("width", 0)), float(element.get("height", 0))
    px, py = point
    if element.get("type") == "ellipse":
        if width <= 0 or height <= 0:
            return False
        dx = (px - left - width / 2) / (width / 2)
        dy = (py - top - height / 2) / (height / 2)
        return dx * dx + dy * dy <= 1
    return left <= px <= left + width and top <= py <= top + height


def _unknown_colours(
    scene: Mapping[str, Any], colours: Mapping[str, Mapping[str, Any]]
) -> list[Finding]:
    found = []
    for element, _, _ in _walk(scene.get("children", [])):
        painted = [element]
        for runs in element.get("paragraphs", []) if element.get("type") == "text" else []:
            painted.extend(runs)  # each run of a text holds its own paint (DEC-012)
        for prop, role in [(p, each.get(p)) for each in painted for p in ("fill", "stroke")]:
            if role is not None and role not in colours:
                found.append(
                    Finding(
                        "unknown-colour",
                        FAILS,
                        f"paints its {prop} with `{role}`, which is no colour role of the brand",
                        file=pl.PIECE_FILE,
                        where=str(element.get("id")),
                        fix="name a colour role the brand gives a value, in the component or "
                        "its content's `override`",
                    )
                )
    return found


def _statuses(scene: Mapping[str, Any], env: pl.ProjectEnv) -> list[Finding]:
    """A fact for each experimental component the piece uses, and a call for attention for
    each deprecated one (DEC-003 point 9)."""
    found = []
    seen: set[str] = set()
    for element, _, _ in _walk(scene.get("children", [])):
        use = element.get("component")
        if not isinstance(use, str) or use in seen:
            continue
        seen.add(use)
        try:
            status = env.component(use).get("status")
        except KeyError:
            continue
        if status == "experimental":
            found.append(
                Finding(
                    "component-experimental",
                    FACT,
                    f"the piece uses `{use}`, which is experimental: its library may still "
                    f"change it in any release",
                    file=pl.PIECE_FILE,
                    where=str(element["id"]),
                )
            )
        elif status == "deprecated":
            found.append(
                Finding(
                    "component-deprecated",
                    ATTENTION,
                    f"the piece uses `{use}`, which is deprecated",
                    file=pl.PIECE_FILE,
                    where=str(element["id"]),
                    fix="replace it with the component its library names in its place",
                    who="the piece's author",
                )
            )
    return found


# --- losses -------------------------------------------------------------------------------------


def renderers(piece: pl.Piece) -> list[str]:
    """The renderers that draw a piece, each once, in name order: the one that draws its
    previews, and the one that draws each format it exports in (`exports.RENDERERS`)."""
    found = (exports.RENDERERS.get(form) for form in piece.exports)
    return sorted({PREVIEWS, *(renderer for renderer in found if renderer is not None)})


def losses(scene: Mapping[str, Any], declaration: Mapping[str, Any]) -> list[seam.Loss]:
    """What a renderer will lose of a scene, known from its declaration before it runs
    (DEC-005 point 9): a primitive it does not draw it refuses, and a property it does not
    draw it leaves out."""
    plugin = str(declaration["name"])
    draws: Mapping[str, Mapping[str, Any]] = declaration.get("draws", {})
    found: list[seam.Loss] = []
    for element, _, _ in _walk(scene.get("children", [])):
        kind, what = str(element.get("type")), str(element.get("id"))
        if kind not in draws:
            found.append(
                seam.Loss(plugin, what, seam.REFUSED, f"the {plugin} renderer draws no `{kind}`")
            )
            continue
        for prop in element:
            if prop not in _STRUCTURE and prop not in draws[kind]:
                found.append(
                    seam.Loss(
                        plugin,
                        what,
                        seam.LEFT_OUT,
                        f"the {plugin} renderer draws no `{prop}` of a {kind}",
                    )
                )
    return found


def loss_finding(loss: seam.Loss) -> Finding:
    """A renderer's loss nobody accepted, which asks the piece's author for attention
    (DEC-005 point 14), at the trace of what it loses. Whether the piece accepts a loss,
    `accepted` says (`findings.accepted`)."""
    return _loss_finding(loss, "renderer", file=pl.PIECE_FILE, where=loss.what)


# --- the validator's document -------------------------------------------------------------------


def document(report: Report) -> dict[str, Any]:
    """The findings document `pkit validate` reads (COR-055 point 3)."""
    return {
        "summary": list(report.summary),
        "findings": [
            {
                "severity": SEVERITY[level],
                "location": place(finding),
                "message": said(finding),
                "label": finding.code,
            }
            for finding, level in report.judged
        ],
    }


def place(finding: Finding) -> str:
    """Where a finding lies: its file, and what within it after `#`."""
    return f"{finding.file}#{finding.where}" if finding.where else finding.file or "."


def said(finding: Finding) -> str:
    """A finding's message, with who is to act and what mends it."""
    parts = [finding.message]
    if finding.who:
        parts.append(f"for {finding.who}")
    if finding.fix:
        parts.append(finding.fix)
    return " — ".join(parts)
