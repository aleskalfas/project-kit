"""Numbered exports of a piece, and their record (visual-communication DEC-006 point 7).

- **What a run makes.** Each format the piece declares under `exports`, in each of its
  languages and each combination of modes it names, drawn from the scene by the renderer
  of that format. Format 1 declares `svg`: one file for each language and combination, so
  a piece of one page alone exports as SVG.
- **A number for each run.** Version `N` is one more than the highest the piece's
  `exports.yaml` records, shared by every file the run makes; each file is named
  `<piece>.v<N>.<language>.<key>.<format>`. The files lie in the clone's local exports
  folder, never committed; no export overwrites another.
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
- **Refused before any write.** Everything that can refuse a run, a file of its number
  already in the exports folder and a file reached through a link included, is checked
  by `plan`, so a refused run writes nothing.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ruamel.yaml.scalarstring import SingleQuotedScalarString

from _lib import fingerprint, framing
from _lib import pipeline as pl
from _lib.env import MissingFont
from _lib.files import FileError, read_bound
from _lib.libraries import installed_release
from _lib.plugins import seam
from _lib.reading import ReadError, sha256
from _lib.root import LOCAL
from _lib.scene import SceneResult

#: The renderer that draws each format a piece may export in format 1.
RENDERERS = {"svg": "svg"}

#: Where each piece's exports lie, relative to the project root.
FOLDER = f"{LOCAL}/exports"

HEADER = (
    "The record of the piece's exports (visual-communication DEC-006 point 7): each\n"
    "numbered export, the fingerprint of what it was made from, each file it made with its\n"
    "hash, and what is only recorded. `pkit visual export` rewrites it; commit it."
)


#: The value of a fingerprint: a SHA-256 in lower-case hexadecimal.
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class Planned:
    """An export computed and not yet written: its number, each file's name and text, the
    record's versions with the new one last, the produced outputs used while stale, and
    those named to be used while stale that were not."""

    piece: pl.Piece
    number: int
    files: dict[str, str]
    versions: list[dict[str, Any]]
    used_stale: list[str]
    not_stale: list[str]

    @property
    def folder(self) -> Path:
        return self.piece.root / FOLDER / self.piece.name


def file_name(piece: str, number: int, language: str, key: str, form: str) -> str:
    return f"{piece}.v{number}.{language}.{key}.{form}"


def recorded_versions(piece: pl.Piece) -> list[dict[str, Any]]:
    """The versions the piece's `exports.yaml` records; none where it is absent. Raises
    Refused when it cannot be read."""
    path = piece.folder / pl.EXPORTS_FILE
    if not path.is_file():
        return []
    try:
        data = read_bound(path, "exports")
    except (ReadError, FileError) as exc:
        raise pl.Refused(f"{exc}: mend it before the next export") from exc
    versions = data.get("versions")
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
            f"{piece.file(pl.PIECE_FILE)} declares no format under `exports`: name `svg` there"
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
    versions = recorded_versions(piece)
    number = max((int(entry["version"]) for entry in versions), default=0) + 1
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
        "files": {name: sha256(text.encode("utf-8")) for name, text in files.items()},
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
    planned = Planned(piece, number, files, [*versions, entry], used_stale, not_stale)
    writable(planned)
    return planned


def used_versions(project: pl.Project) -> dict[str, str]:
    """Each produced output the piece's scenes read, with the version used: the `value` of
    its record's fingerprint, by which the check knows that record (DEC-006 point 7). A
    record whose fingerprint has no value is stale, and named with the outputs used while
    stale alone."""
    used = {}
    for output, record in sorted(project.env.records.items()):
        kept = record.get("fingerprint")
        value = kept.get("value") if isinstance(kept, Mapping) else None
        if isinstance(value, str) and _SHA256.match(value):
            used[output] = value
    return used


def _drawn(
    project: pl.Project, results: Sequence[tuple[str, SceneResult]], number: int
) -> dict[str, str]:
    piece = project.piece
    files: dict[str, str] = {}
    for form in piece.exports:
        for language, key, drawn in pl.drawn(project, results, RENDERERS[form]):
            if len(drawn.pages) != 1:
                raise pl.Refused(
                    f"`{piece.name}` has {len(drawn.pages)} pages; an export file of format 1 "
                    f"is named by piece, version, language and combination, so a piece of one "
                    f"page alone exports as `{form}`"
                )
            files[file_name(piece.name, number, language, key, form)] = drawn.pages[0].svg
    return files


def writable(planned: Planned) -> None:
    """Raise Refused where a planned export could not be written: a file of its number lies
    in the exports folder already, or a file it writes is reached through a link."""
    piece = planned.piece
    taken = sorted(name for name in planned.files if (planned.folder / name).exists())
    if taken:
        raise pl.Refused(
            f"{FOLDER}/{piece.name}/ holds {', '.join(taken)} already, from an export "
            f"{piece.file(pl.EXPORTS_FILE)} does not record: move it away, since no export "
            f"overwrites another"
        )
    for path in (
        *(planned.folder / name for name in planned.files),
        piece.folder / pl.EXPORTS_FILE,
    ):
        pl.writable(piece.root, path)


def write(planned: Planned) -> None:
    """Write a planned export's files, then its record. Raises Refused, writing nothing,
    where it could not be written (`writable`), which `plan` already checked."""
    piece = planned.piece
    writable(planned)
    for name, text in planned.files.items():
        pl.write_file(piece.root, planned.folder / name, text.encode("utf-8"))
    record = {
        "pkit_schema": "visual-communication:exports",
        "schema_version": 1,
        "versions": [_quoted_time(entry) for entry in planned.versions],
    }
    pl.write_file(
        piece.root, piece.folder / pl.EXPORTS_FILE, pl.yaml_text(record, HEADER).encode("utf-8")
    )


def _quoted_time(entry: Mapping[str, Any]) -> dict[str, Any]:
    """A version as the record writes it: its time quoted, as commands write times."""
    recorded = dict(entry.get("recorded") or {})
    if isinstance(recorded.get("time"), str):
        recorded["time"] = SingleQuotedScalarString(recorded["time"])
    return {**entry, "recorded": recorded}
