"""Numbered exports of a piece, and their record (visual-communication DEC-006 point 7).

- **What a run makes.** Each format the piece declares under `exports`, in each of its
  languages and each combination of modes it names, drawn from the scene of its key over
  the size axes by the renderer of that format (`RENDERERS`). `svg` makes one file for
  each page, language and combination; `pdf` one file for each language and combination,
  which holds every page in order (`DOCUMENTS`). A piece with no page in one of its
  languages is refused.
- **A number for each run.** Version `N` is one more than the highest the piece's
  `exports.yaml` records or a file in the piece's exports folder carries, shared by every
  file the run makes; each file is named `<piece>.v<N>.<language>.<key>.<format>`, and a
  file of one page of a piece of more than one page adds the page's number, from 1:
  `<piece>.v<N>.<language>.<key>.<n>.<format>`. The files lie in the clone's local exports
  folder, never committed; no export overwrites another, and a file a failed run left
  there refuses no later run.
- **What a preview fills** (`preview_filling`). The facts of the next export on this clone:
  its next number and the date of the run. A final piece, which takes no export, and a
  record of exports that cannot be read give none, so those take the stand-ins and say why
  (DEC-016 point 5).
- **No stale output.** A run stops on a produced picture whose record no longer verifies,
  naming what changed, unless the person names it to be used as it is; it stops on a
  picture that is missing whatever is named. Naming an output the piece does not declare
  is refused; one that is not stale is used as it is, and the command says so.
- **What an export fills** (`FILLED`). One number and one date, those its record keeps, in
  every file of the version: its number, and the date of the time it records. The scenes
  it draws are computed again with them, where a scene shows either (DEC-016 point 5). The
  scenes the findings rest on keep the stand-ins (`Planned.results`), and the fingerprint
  reads none of these facts, so a new number makes nothing stale.
- **No number or date that overflows** (`overflows`). The run measures, in the scenes it
  draws, each element that shows a fact it fills, and each component around it, as the
  check does, from a font file. It stops on a text that overflows its width, and on a
  component that gets less than it asks for, naming the fact, its text and the element,
  whether or not the stand-in overflowed too, and in any library (DEC-016 point 6). A
  person names the fact to use its text as it is; a fact nobody named still stops, and
  the record keeps each text let through. An overflow measured from a table or by an
  estimate stops nothing, and the run says it. The language and the state come from
  files, which the check measures as they stand, so naming either is refused.
- **The record.** `exports.yaml` keeps, for each version, the fingerprint of every file
  its scenes were computed from and of the formats it made (form 1), the hash of each file
  it made, and what is only recorded: when, the piece's state, the capability's release,
  the renderers' versions, each produced output the scenes used with the version used
  (the `value` of its record's fingerprint, by which the check knows it), those used
  while stale (DEC-006 point 7), and each number or date let through, where one was.
- **The current copy.** A published piece's run also makes a copy of each file of the
  version, in its folder or at the place it names, and the record names the version that
  wrote it (`current_copy`). The run names each file of the last copy it left behind. A
  piece in any other state writes none, and the record keeps what it named. `plan` refuses
  an entry the schema refuses, in every state, so no run writes it back. What stops an
  export a person runs on a lock that differs from the copy's lies in `export.py`, outside
  `plan` and `add`, since a run that proposes a move of the lock shares these.
- **Refused before any write.** Everything that can refuse a run, a file reached through
  a link included, is checked by `plan`, so a refused run writes nothing.
- **Written as one change.** The files, the current copy, then the record (`write`): where
  a write fails, every file is put back as it was before the run, the files the run wrote
  removed, or each it could not put back is named. A run that writes more in that change
  adds the export to it (`add`), and takes it itself.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Collection, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _lib import current_copy, fingerprint, framing, layout, records
from _lib import pipeline as pl
from _lib.env import MissingFont
from _lib.files import Change
from _lib.libraries import Held, installed_release
from _lib.plugins import seam
from _lib.reading import is_sha256, sha256
from _lib.root import LOCAL
from _lib.scene import Element, Scene, SceneResult
from _lib.text import MEASURED

#: The renderer that draws each format a piece may export in format 1.
RENDERERS = {"svg": "svg", "pdf": "pdf"}

#: The formats whose file holds every page of a scene, in order: one file for each
#: language and combination. Every other format makes one file for each page.
DOCUMENTS = frozenset({"pdf"})

#: Where each piece's exports lie, relative to the project root.
FOLDER = f"{LOCAL}/exports"

#: The facts an export fills that no file holds, so it measures their text where it fills
#: them: those a stand-in takes the place of in every other scene (DEC-016 points 5 and 6).
FILLED = tuple(layout.STAND_INS)

#: The scene's findings by which a fact's text does not fit: a text wider than its width,
#: and a component that gets less than it asks for (DEC-005 point 14).
OVERFLOWS = "text-overflow"
GETS_LESS = "gets-less"

#: The comment that opens the record, a line each.
HEADER = (
    "The record of the piece's exports (visual-communication DEC-006 point 7): each",
    "numbered export, the fingerprint of what it was made from, each file it made with its",
    "hash, and what is only recorded. `pkit visual export` rewrites it; commit it.",
)


@dataclass(frozen=True)
class Overflow:
    """A fact an export fills whose text does not fit (DEC-016 point 6): the fact, its text,
    and the element a scene finds it at, either the text, which overflows its width, or a
    component around it that gets less than it asks for, as `short` says. `component` is
    the component that element lies in, and `version` that component's library version,
    empty for the piece's own. `measured` says whether each run of the text is measured
    from a font file, and not from a table or by an estimate."""

    fact: str
    text: str
    element: str
    component: str
    version: str
    short: bool
    measured: bool

    @property
    def said(self) -> str:
        """The overflow in words: the fact, its text, the element, its component, and why."""
        why = "gets less than it asks for" if self.short else "overflows its width"
        return (
            f"`{self.fact}` as `{self.text}` at `{self.element}` in `{self.component}`, which {why}"
        )

    @property
    def entry(self) -> dict[str, Any]:
        """What the record of exports keeps of the text once a person lets it through: the
        fact, the text, the element and its component, with the component's library version
        where it lies in a library."""
        kept = {
            "fact": self.fact,
            "text": self.text,
            "element": self.element,
            "component": self.component,
        }
        if self.version:
            kept["version"] = self.version
        return kept


@dataclass(frozen=True)
class Planned:
    """An export computed and not yet written: its number, each file's name and bytes, the
    record's versions with the new one last, the produced outputs used while stale, those
    named to be used while stale that were not, the current copy it writes, if any, what
    the record held of one before the run, the piece's own among it, where it writes one,
    and the scenes with the stand-ins, which the findings rest on (DEC-016 point 5). Then
    what it filled its facts with, each text it let through, each overflow measured
    otherwise than from a font file, and each fact named to be let through that did not
    overflow."""

    piece: pl.Piece
    number: int
    files: dict[str, bytes]
    versions: list[dict[str, Any]]
    used_stale: list[str]
    not_stale: list[str]
    copy: current_copy.Copy | None
    kept_copy: Mapping[str, Any] | None
    own_copy: Mapping[str, Any] | None
    results: Sequence[tuple[str, SceneResult]]
    facts: layout.Facts
    let_through: tuple[Overflow, ...]
    estimated: tuple[Overflow, ...]
    not_overflowing: tuple[str, ...]

    @property
    def folder(self) -> Path:
        return self.piece.root / FOLDER / self.piece.name

    @property
    def named_copy(self) -> Mapping[str, Any] | None:
        """What the record names of a current copy once this export is written."""
        return self.kept_copy if self.copy is None else self.copy.entry

    @property
    def left_behind(self) -> list[str]:
        """Each file of the last current copy this export leaves where it lies."""
        return current_copy.left_behind(self.piece, self.own_copy, self.copy)


def file_name(
    piece: str, number: int, language: str, key: str, form: str, page: int | None = None
) -> str:
    """An exported file's name: the piece, the version, the language, the combination's
    key and the format, with the page's number before the format where `page` names one,
    as for the file of each page of a piece of more than one page. A file that holds every
    page, as a PDF does, names none."""
    numbered = "" if page is None else f".{page}"
    return f"{piece}.{version_text(number)}.{language}.{key}{numbered}.{form}"


def recorded(piece: pl.Piece) -> dict[str, Any]:
    """What the piece's `exports.yaml` holds; nothing where it is absent. Raises Refused
    when it cannot be read."""
    path = piece.folder / pl.EXPORTS_FILE
    if not path.is_file():
        return {}
    try:
        return records.read(path, "exports")
    except records.RecordError as exc:
        raise pl.Refused(f"{exc}: mend it before the next export") from exc


def recorded_versions(piece: pl.Piece, record: Mapping[str, Any]) -> list[dict[str, Any]]:
    """The versions `record`, what the piece's `exports.yaml` holds (`recorded`), keeps;
    none where it is absent. Raises Refused when it keeps no list of them."""
    if not record:
        return []
    versions = record.get("versions")
    if not isinstance(versions, list) or not all(
        isinstance(entry, Mapping) and isinstance(entry.get("version"), int) for entry in versions
    ):
        raise pl.Refused(f"{piece.file(pl.EXPORTS_FILE)} keeps no list of numbered versions")
    return [dict(entry) for entry in versions]


def stale_outputs(project: pl.Project, held: Held | None = None) -> dict[str, list[str]]:
    """Each produced picture the piece's scenes read whose record no longer verifies, with
    what changed (DEC-006 point 5): its fingerprint, worked out again from the current
    files under its form by the producer's framing, and every combination the piece names
    that the record maps to no variant. The framing reads under the project's lock, whatever
    the piece's file holds. `held`, where it is given, is what it reads the library versions
    from (`framing.plan`)."""
    piece = project.piece
    stale: dict[str, list[str]] = {}
    for output in sorted(project.env.records):
        record = project.env.records[output]
        try:
            sources = framing.plan(
                piece.root, piece.location, piece.name, output, held, project.lock
            ).sources
        except framing.Refused as exc:
            stale[output] = [str(exc)]
            continue
        kept = record.get("fingerprint")
        changes = (
            fingerprint.verify(kept, "produced-record", **sources)
            if isinstance(kept, Mapping)
            else ["the record keeps no fingerprint"]
        )
        mapped = record.get("combinations") or {}
        changes += [
            f"the combination `{key}` has no variant" for key in project.keys if key not in mapped
        ]
        if changes:
            stale[output] = changes
    return stale


def plan(
    project: pl.Project,
    *,
    use_stale: Sequence[str] = (),
    use_overflowing: Sequence[str] = (),
    now: datetime | None = None,
    written: Mapping[Path, bytes] | None = None,
    way_past_stale: Callable[[Collection[str]], str] | None = None,
    way_past_overflow: Callable[[Collection[str]], str] | None = None,
) -> Planned:
    """The next export of the project's piece, computed: every file drawn, the record's
    new version written out, and every file it writes checked. `use_overflowing` names each
    fact whose text the run uses as it is, though it overflows. `now` is the time the record
    keeps, whose date the files show, by default this run's. `written` gives the bytes of
    each file the same change writes before it, such as `piece.yaml` with its lock moved,
    which the fingerprint reads in place of the file. `way_past_stale` and
    `way_past_overflow` say, from every output stale or every fact that overflows, the way
    past it, where a run takes another than an export's. Raises Refused, naming what stops
    it, so `write` refuses nothing."""
    piece = project.piece
    if not piece.exports:
        raise pl.Refused(
            f"{piece.file(pl.PIECE_FILE)} declares no format under `exports`: name "
            f"{' or '.join(f'`{form}`' for form in RENDERERS)} there"
        )
    undeclared = sorted(set(use_stale) - set(piece.produced))
    if undeclared:
        named = ", ".join(f"`--use-stale {output}`" for output in undeclared)
        declared = ", ".join(f"`{output}`" for output in sorted(piece.produced)) or "none"
        raise pl.Refused(
            f"{named} {'names' if len(undeclared) == 1 else 'name'} no produced output of "
            f"`{piece.name}`, which declares {declared}"
        )
    unfilled = sorted(set(use_overflowing) - set(FILLED))
    if unfilled:
        named = ", ".join(f"`--use-overflowing {word}`" for word in unfilled)
        raise pl.Refused(
            f"{named} {'names' if len(unfilled) == 1 else 'name'} no fact an export fills, "
            f"which are {' and '.join(f'`{word}`' for word in FILLED)}: the check measures the "
            f"language and the state as they stand"
        )
    try:
        results = project.scenes(facts=piece.stand_ins)
    except MissingFont as exc:
        raise pl.Refused(f"the scenes of `{piece.name}` cannot be drawn: {exc}") from exc
    if project.env.missing:
        why = "; ".join(
            f"`{output}`: {reason} — run {pl.produce_command(piece.name, output)}"
            for output, reason in sorted(project.env.missing.items())
        )
        raise pl.Refused(f"a produced picture the piece shows is missing: {why}")
    stale = stale_outputs(project)
    stopping = {output: why for output, why in stale.items() if output not in use_stale}
    if stopping:
        why = "; ".join(
            f"`{output}` ({'; '.join(changes)})" for output, changes in sorted(stopping.items())
        )
        way = (
            f"Run `pkit visual produce {piece.name} <output>` for each, or name it with "
            f"`--use-stale <output>` to export it as it is"
            if way_past_stale is None
            else way_past_stale(stale)
        )
        raise pl.Refused(f"a produced picture is stale: {why}. {way}")
    record = recorded(piece)
    versions = recorded_versions(piece, record)
    kept_copy = current_copy.recorded(piece, record)
    number = next_number(piece, versions)
    when = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    facts = layout.Facts(version_text(number), date_text(when), piece.state)
    try:
        drawn = _filled(project, results, facts)
    except MissingFont as exc:
        raise pl.Refused(f"the scenes of `{piece.name}` cannot be drawn: {exc}") from exc
    found = overflows(drawn)
    measured = tuple(overflow for overflow in found if overflow.measured)
    stopping = [overflow for overflow in measured if overflow.fact not in use_overflowing]
    if stopping:
        way = (
            "Give each room in its component, or name its fact with `--use-overflowing <fact>` "
            "to export its text as it is"
            if way_past_overflow is None
            else way_past_overflow({overflow.fact for overflow in measured})
        )
        said = "; ".join(overflow.said for overflow in stopping)
        raise pl.Refused(f"a number or a date the export fills does not fit: {said}. {way}")
    files = _drawn(project, drawn, number)
    sources = pl.findings_key_sources(
        project.root, project.held, piece, project.lock, sorted(project.env.fonts_read)
    )
    try:
        taken = fingerprint.fingerprint(fingerprint.export_inputs(**sources, written=written))
    except fingerprint.FingerprintError as exc:
        raise pl.Refused(f"the export's fingerprint cannot be taken: {exc}") from exc
    used_stale = sorted(stale)
    entry = {
        "version": number,
        "fingerprint": taken,
        "files": {name: sha256(data) for name, data in files.items()},
        "recorded": {
            "time": when.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "state": piece.state,
            "capability": ".".join(map(str, installed_release())),
            "renderers": {
                RENDERERS[form]: seam.declaration(RENDERERS[form], seam.RENDERER)["version"]
                for form in sorted(set(piece.exports))
            },
            "used": used_versions(project),
            "used-stale": used_stale,
        },
    }
    if measured:
        entry["recorded"]["let-through"] = [overflow.entry for overflow in measured]
    not_stale = sorted(set(use_stale) - set(stale))
    copy = current_copy.made(piece, number, files)
    planned = Planned(
        piece,
        number,
        files,
        [*versions, entry],
        used_stale,
        not_stale,
        copy,
        kept_copy,
        None if copy is None else current_copy.own(piece, record),
        results,
        facts,
        measured,
        tuple(overflow for overflow in found if not overflow.measured),
        tuple(sorted(set(use_overflowing) - {overflow.fact for overflow in found})),
    )
    writable(planned)
    return planned


def _filled(
    project: pl.Project, results: Sequence[tuple[str, SceneResult]], facts: layout.Facts
) -> Sequence[tuple[str, SceneResult]]:
    """The scenes an export draws: `results`, computed with the stand-ins, where no scene
    shows a fact the export fills, else computed again with `facts` (DEC-016 point 5). So
    only a piece that shows a version's number or its date is computed twice. Raises
    MissingFont."""
    if not shown_stand_ins(results):
        return results
    return project.scenes(facts=facts)


def overflows(results: Sequence[tuple[str, SceneResult]]) -> list[Overflow]:
    """Each fact of `FILLED` whose text does not fit in the scenes `results`, once, in order
    (DEC-016 point 6): a text that shows it and overflows its width, and a component around
    such a text that gets less than it asks for, found as the check finds them. Each says
    whether the text was measured from a font file."""
    found: dict[Overflow, None] = {}
    for _, result in results:
        shown = {
            trace: word
            for word, traces in result.facts.items()
            if word in FILLED
            for trace in traces
        }
        for finding in result.findings:
            if finding.code == OVERFLOWS and finding.where in shown:
                texts = [finding.where]
            elif finding.code == GETS_LESS:
                texts = [trace for trace in shown if _within(trace, finding.where)]
            else:
                continue
            for trace in texts:
                overflow = _overflow(
                    result.scene, shown[trace], trace, finding.where, finding.code == GETS_LESS
                )
                found.setdefault(overflow, None)
    return sorted(found, key=lambda overflow: (overflow.element, overflow.fact, overflow.text))


def _within(trace: str, around: str) -> bool:
    """Whether the element `trace` is the element `around`, or lies within it: a part, an
    item or a page of it."""
    rest = trace[len(around) :]
    return trace.startswith(around) and (not rest or rest[0] in "/[#")


def _overflow(scene: Scene, fact: str, trace: str, where: str, short: bool) -> Overflow:
    """The overflow of the fact `fact` that the text `trace` of `scene` shows, found at the
    element `where`: the text itself, or, where `short`, a component around it."""
    text = scene.find(trace)
    assert text is not None
    runs = [run for paragraph in text.properties["paragraphs"] for run in paragraph]
    group = _component_of(scene.children, where, None)
    component = "" if group is None else str(group.properties["component"])
    version = "" if group is None else str(group.properties.get("version", ""))
    return Overflow(
        fact,
        str(text.properties["text"]),
        where,
        component,
        version,
        short,
        all(run["measured"] == MEASURED for run in runs),
    )


def _component_of(
    elements: Sequence[Element], trace: str, around: Element | None
) -> Element | None:
    """The group that draws the component the element `trace` lies in, among `elements` and
    below them: the element itself where it is one, else the nearest group around it that
    names its component, `around` above `elements`. None where no element has that trace."""
    for element in elements:
        drawn = element if "component" in element.properties else around
        if element.id == trace:
            return drawn
        found = _component_of(element.children, trace, drawn)
        if found is not None:
            return found
    return None


def shown_stand_ins(results: Sequence[tuple[str, SceneResult]]) -> list[str]:
    """Each element the scenes show a stand-in at, with the fact it shows, in order."""
    return sorted(
        {
            f"`{word}` at `{trace}`"
            for _, result in results
            for word, traces in result.facts.items()
            if word in layout.STAND_INS
            for trace in traces
        }
    )


#: Why a final piece's preview takes the stand-ins (DEC-017 point 3).
NO_NEXT_EXPORT = "a final piece has no next export"


@dataclass(frozen=True)
class Filling:
    """What fills the facts of the scenes a person looks at: `facts`, and, where they are the
    stand-ins, why, in words. `why` is empty where they are what the piece's next export
    would fill (DEC-016 point 5)."""

    facts: layout.Facts
    why: str = ""

    def said(self, shown: Collection[str]) -> str:
        """What a run says of the stand-ins its scenes show, `shown` each element that shows
        a fact a stand-in fills (`shown_stand_ins`): why they show, and each such element;
        empty where this filling takes none, or no element shows one."""
        if not self.why or not shown:
            return ""
        return f"{self.why}, so a stand-in shows: {'; '.join(sorted(shown))}"


def preview_filling(piece: pl.Piece, now: datetime | None = None) -> Filling:
    """What a preview of `piece` fills its facts with: what its next export on this clone
    would, its next number and the date of `now`, by default this run's (DEC-016 point 5).
    Where the record of exports cannot be read, as one that conflicts on a merge, there is no
    next number, and a final piece has no next export (DEC-017 point 3). Each takes the
    stand-ins, and says why. The record is read first, since one that cannot be read makes
    the piece final."""
    try:
        versions = recorded_versions(piece, recorded(piece))
    except pl.Refused as exc:
        said = str(exc).replace(f"{piece.root}/", "")
        return Filling(piece.stand_ins, f"no next number can be read ({said})")
    if piece.final:
        return Filling(piece.stand_ins, NO_NEXT_EXPORT)
    when = now or datetime.now(timezone.utc)
    shown = layout.Facts(version_text(next_number(piece, versions)), date_text(when), piece.state)
    return Filling(shown)


def version_text(number: int) -> str:
    """A version's number as a scene shows it, and an exported file's name writes it."""
    return f"v{number}"


def date_text(when: datetime) -> str:
    """A version's date as a scene shows it, in every language (DEC-016 point 5)."""
    return when.strftime("%Y-%m-%d")


def next_number(piece: pl.Piece, versions: Sequence[Mapping[str, Any]]) -> int:
    """The number of the piece's next export: one more than the highest that the record's
    `versions` name or a file of the piece's exports folder carries, so no export
    overwrites another, and a file a failed run could not remove refuses no later run."""
    numbered = re.compile(rf"^{re.escape(piece.name)}\.v([0-9]+)\.")
    taken = [int(entry["version"]) for entry in versions]
    folder = piece.root / FOLDER / piece.name
    if folder.is_dir():
        names = (numbered.match(path.name) for path in folder.iterdir())
        taken += [int(found.group(1)) for found in names if found is not None]
    return max(taken, default=0) + 1


def used_versions(project: pl.Project) -> dict[str, str]:
    """Each produced output the piece's scenes read, with the version used: the `value` of
    its record's fingerprint, by which the check knows that record (DEC-006 point 7). A
    record whose fingerprint has no value is stale, and named with the outputs used while
    stale alone."""
    used = {}
    for output, record in sorted(project.env.records.items()):
        kept = record.get("fingerprint")
        value = kept.get("value") if isinstance(kept, Mapping) else None
        if is_sha256(value):
            used[output] = value
    return used


def _drawn(
    project: pl.Project, results: Sequence[tuple[str, SceneResult]], number: int
) -> dict[str, bytes]:
    """Each file of the export and its bytes, by its name, format by format as the piece
    declares them: for a format of `DOCUMENTS`, one for each language and combination,
    which holds every page in order; for another, one for each page, language and
    combination, the pages of each in order. Raises Refused where a language has no page,
    since the version would hold no file in it."""
    piece = project.piece
    files: dict[str, bytes] = {}
    for form in piece.exports:
        for language, (key,), drawn in pl.drawn(project, results, RENDERERS[form]):
            if not drawn.pages:
                raise pl.Refused(
                    f"`{piece.name}` has no page in `{language}`, so the export would hold no "
                    f"file in that language"
                )
            if form in DOCUMENTS:
                files[file_name(piece.name, number, language, key, form)] = drawn.document
                continue
            several = len(drawn.pages) > 1
            for index, page in enumerate(drawn.pages, start=1):
                name = file_name(
                    piece.name, number, language, key, form, index if several else None
                )
                files[name] = page.svg.encode("utf-8")
    return files


def writable(planned: Planned) -> None:
    """Raise Refused where a planned export could not be written: a file it writes is
    reached through a link, or its current copy could not lie where it goes."""
    piece = planned.piece
    for path in (
        *(planned.folder / name for name in planned.files),
        piece.folder / pl.EXPORTS_FILE,
    ):
        pl.writable(piece.root, path)
    if planned.copy is not None:
        current_copy.writable(piece, planned.copy, planned.own_copy)


def write(planned: Planned, change: Change) -> None:
    """Write a planned export as the next steps of `change` (`add`), and take it. Raises
    Refused, writing nothing, where it could not be written (`writable`), which `plan`
    already checked; WriteFailed where a write fails, every file then put back as it was
    before the run, or named."""
    add(planned, change)
    change.commit()


def add(planned: Planned, change: Change) -> None:
    """Add to `change`, as its next steps, a planned export's files, its current copy where it
    makes one, then its record. Raises Refused, adding nothing, where it could not be written
    (`writable`), which `plan` already checked."""
    piece = planned.piece
    writable(planned)
    for name, data in planned.files.items():
        change.write(planned.folder / name, data)
    if planned.copy is not None:
        current_copy.write(piece, planned.copy, change)
    record: dict[str, Any] = {
        "pkit_schema": "visual-communication:exports",
        "schema_version": 1,
    }
    if planned.named_copy is not None:
        record[current_copy.FIELD] = planned.named_copy
    record["versions"] = [records.quoted_time(entry) for entry in planned.versions]
    change.write(piece.folder / pl.EXPORTS_FILE, records.text(record, HEADER).encode("utf-8"))


def report(planned: Planned) -> Iterator[str]:
    """What a run says of a planned export, a line each: each file, each file of the current
    copy, each it left behind, each picture used while stale or named and not stale, each
    text let through, each overflow measured otherwise than from a font file, each fact named
    that did not overflow, and the version recorded."""
    piece = planned.piece
    for file in planned.files:
        yield f"export: {FOLDER}/{piece.name}/{file}"
    if planned.copy is not None:
        for path in planned.copy.entry["files"]:
            yield f"current copy: {current_copy.rooted(piece, path)}"
    for path in planned.left_behind:
        yield f"left behind: {path}: the run did not write it again, and only a person removes it"
    for output in planned.used_stale:
        yield f"used while stale: {output}"
    for output in planned.not_stale:
        yield f"not stale, so used as it is: {output}"
    for overflow in planned.let_through:
        yield f"let through: {overflow.said}"
    for overflow in planned.estimated:
        yield (
            f"stops nothing, measured otherwise than from a font file, from a table or by an "
            f"estimate: {overflow.said}"
        )
    for fact in planned.not_overflowing:
        yield f"not overflowing, so used as it is: {fact}"
    yield f"export: version {planned.number} recorded in {piece.file(pl.EXPORTS_FILE)}"
