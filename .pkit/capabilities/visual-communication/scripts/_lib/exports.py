"""Numbered exports of a piece, and their record (visual-communication DEC-006 point 7).

- **What a run makes.** Each format the piece declares under `exports`, in each of its
  languages and each combination of modes it names, drawn from the scene by the renderer
  of that format (`RENDERERS`). `svg` makes one file for each page, language and
  combination; `pdf` one file for each language and combination, which holds every page
  in order (`DOCUMENTS`). A piece with no page in one of its languages is refused.
- **A number for each run.** Version `N` is one more than the highest the piece's
  `exports.yaml` records or a file in the piece's exports folder carries, shared by every
  file the run makes; each file is named `<piece>.v<N>.<language>.<key>.<format>`, and a
  file of one page of a piece of more than one page adds the page's number, from 1:
  `<piece>.v<N>.<language>.<key>.<n>.<format>`. The files lie in the clone's local exports
  folder, never committed; no export overwrites another, and a file a failed run left
  there refuses no later run.
- **No stale output.** A run stops on a produced picture whose record no longer verifies,
  naming what changed, unless the person names it to be used as it is; it stops on a
  picture that is missing whatever is named. Naming an output the piece does not declare
  is refused; one that is not stale is used as it is, and the command says so.
- **The record.** `exports.yaml` keeps, for each version, the fingerprint of every file
  its scenes were computed from and of the formats it made (form 1), the hash of each file
  it made, and what is only recorded: when, the piece's state, the capability's release,
  the renderers' versions, each produced output the scenes used with the version used
  (the `value` of its record's fingerprint, by which the check knows it), and those used
  while stale (DEC-006 point 7).
- **The current copy.** A published piece's run also makes a copy of each file of the
  version, and the record names the version that wrote it (`current_copy`). A piece in any
  other state writes none, and the record keeps what it named. `plan` refuses an entry the
  schema refuses, in every state, so no run writes it back. What stops an export a person
  runs on a lock that differs from the copy's lies in `export.py`, outside `plan` and
  `write`, since a run that proposes a move of the lock shares these.
- **Refused before any write.** Everything that can refuse a run, a file reached through
  a link included, is checked by `plan`, so a refused run writes nothing. A piece that
  shows a version's number or its date is one: an export does not fill them yet, so no
  file ever holds a stand-in (DEC-016 point 5).
- **Written as one change.** The files, the current copy, then the record (`write`): where
  a write fails, every file is put back as it was before the run, the files the run wrote
  removed, or each it could not put back is named.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _lib import current_copy, fingerprint, framing, layout, records
from _lib import pipeline as pl
from _lib.env import MissingFont
from _lib.files import Change
from _lib.libraries import installed_release
from _lib.plugins import seam
from _lib.reading import is_sha256, sha256
from _lib.root import LOCAL
from _lib.scene import SceneResult

#: The renderer that draws each format a piece may export in format 1.
RENDERERS = {"svg": "svg", "pdf": "pdf"}

#: The formats whose file holds every page of a scene, in order: one file for each
#: language and combination. Every other format makes one file for each page.
DOCUMENTS = frozenset({"pdf"})

#: Where each piece's exports lie, relative to the project root.
FOLDER = f"{LOCAL}/exports"

#: The comment that opens the record, a line each.
HEADER = (
    "The record of the piece's exports (visual-communication DEC-006 point 7): each",
    "numbered export, the fingerprint of what it was made from, each file it made with its",
    "hash, and what is only recorded. `pkit visual export` rewrites it; commit it.",
)


@dataclass(frozen=True)
class Planned:
    """An export computed and not yet written: its number, each file's name and bytes, the
    record's versions with the new one last, the produced outputs used while stale, those
    named to be used while stale that were not, the current copy it writes, if any, and
    what the record held of one before the run."""

    piece: pl.Piece
    number: int
    files: dict[str, bytes]
    versions: list[dict[str, Any]]
    used_stale: list[str]
    not_stale: list[str]
    copy: current_copy.Copy | None
    kept_copy: Mapping[str, Any] | None

    @property
    def folder(self) -> Path:
        return self.piece.root / FOLDER / self.piece.name

    @property
    def named_copy(self) -> Mapping[str, Any] | None:
        """What the record names of a current copy once this export is written."""
        return self.kept_copy if self.copy is None else self.copy.entry


def file_name(
    piece: str, number: int, language: str, key: str, form: str, page: int | None = None
) -> str:
    """An exported file's name: the piece, the version, the language, the combination's
    key and the format, with the page's number before the format where `page` names one,
    as for the file of each page of a piece of more than one page. A file that holds every
    page, as a PDF does, names none."""
    numbered = "" if page is None else f".{page}"
    return f"{piece}.v{number}.{language}.{key}{numbered}.{form}"


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


def stale_outputs(project: pl.Project) -> dict[str, list[str]]:
    """Each produced picture the piece's scenes read whose record no longer verifies, with
    what changed (DEC-006 point 5): its fingerprint, worked out again from the current
    files under its form by the producer's framing, and every combination the piece names
    that the record maps to no variant."""
    piece = project.piece
    stale: dict[str, list[str]] = {}
    for output in sorted(project.env.records):
        record = project.env.records[output]
        try:
            sources = framing.plan(piece.root, piece.location, piece.name, output).sources
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


def plan(project: pl.Project, *, use_stale: Sequence[str] = (), now: str | None = None) -> Planned:
    """The next export of the project's piece, computed: every file drawn, the record's
    new version written out, and every file it writes checked. Raises Refused, naming what
    stops it, so `write` refuses nothing."""
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
    try:
        results = project.scenes()
    except MissingFont as exc:
        raise pl.Refused(f"the scenes of `{piece.name}` cannot be drawn: {exc}") from exc
    shown = shown_stand_ins(results)
    if shown:
        raise pl.Refused(
            f"`{piece.name}` shows a fact no export fills yet, so a file would hold a stand-in: "
            f"{'; '.join(shown)}. Draw the piece without it to export it"
        )
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
        raise pl.Refused(
            f"a produced picture is stale: {why}. Run `pkit visual produce {piece.name} "
            f"<output>` for each, or name it with `--use-stale <output>` to export it as it is"
        )
    record = recorded(piece)
    versions = recorded_versions(piece, record)
    kept_copy = current_copy.recorded(piece, record)
    number = next_number(piece, versions)
    files = _drawn(project, results, number)
    sources = pl.findings_key_sources(
        project.root, project.held, piece, project.lock, sorted(project.env.fonts_read)
    )
    try:
        taken = fingerprint.fingerprint(fingerprint.export_inputs(**sources))
    except fingerprint.FingerprintError as exc:
        raise pl.Refused(f"the export's fingerprint cannot be taken: {exc}") from exc
    used_stale = sorted(stale)
    entry = {
        "version": number,
        "fingerprint": taken,
        "files": {name: sha256(data) for name, data in files.items()},
        "recorded": {
            "time": now or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
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
    not_stale = sorted(set(use_stale) - set(stale))
    planned = Planned(
        piece,
        number,
        files,
        [*versions, entry],
        used_stale,
        not_stale,
        current_copy.made(piece, number, files),
        kept_copy,
    )
    writable(planned)
    return planned


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
        for language, key, drawn in pl.drawn(project, results, RENDERERS[form]):
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
    reached through a link, or a file lies where its current copy's folder goes."""
    piece = planned.piece
    for path in (
        *(planned.folder / name for name in planned.files),
        piece.folder / pl.EXPORTS_FILE,
    ):
        pl.writable(piece.root, path)
    if planned.copy is not None:
        current_copy.writable(piece, planned.copy)


def write(planned: Planned, change: Change) -> None:
    """Write a planned export's files, its current copy where it makes one, then its
    record, as the next steps of `change`, and take it. Raises Refused, writing nothing,
    where it could not be written (`writable`), which `plan` already checked; WriteFailed
    where a write fails, every file then put back as it was before the run, or named."""
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
    change.commit()
