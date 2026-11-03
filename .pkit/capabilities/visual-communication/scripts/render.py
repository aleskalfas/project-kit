#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "ruamel.yaml==0.19.1",
#   "uharfbuzz==0.57.0",
#   "fonttools==4.68.0",
#   "uniseg==0.10.1",
# ]
# ///
"""visual-communication capability — render: compute a piece's scenes, keep what they found,
and draw its previews (DEC-003 point 8, DEC-005 points 5, 9, 13 and 14).

- **Moves a draft's lock** to the newest versions the project holds that the installed
  capability reads and that fit together, within the lines the lock names, and writes it
  into `piece.yaml`, every other byte kept. A pinned draft's lock is checked, never moved.
- **Computes every scene:** one for each language the piece lists. A font with no file,
  or a character no family measures, refuses the render before anything is laid out.
- **Writes the piece's findings record,** `findings.yaml`, keyed by a fingerprint of every
  file the scenes were computed from: what the check reads while the key verifies.
- **Draws the previews** with the SVG renderer, one file for each page, language and
  combination of modes the piece names, under
  `.pkit/capabilities/visual-communication/project/local/previews/<piece>/`, local to the
  clone and never committed.
- **Prints** what the renderer loses that the piece does not accept, and the findings.

It writes in the location, so where the configuration records none it takes `visual/` and
records it before its first write, or the path `--location` names. Every check that can
refuse runs before that first write, the findings record's key taken over `piece.yaml` as
the render writes it, so a refused render writes nothing, the location included. It
writes the previews, then removes the old ones, then `piece.yaml` and the findings record,
as one change: a write that fails leaves the previews, the records and the configuration
as they were before the run.

Usage:
  pkit visual render <piece> [--location <path>]

Exit codes:
  0  rendered; findings, if any, are printed and kept in the findings record
  1  refused: the piece, its lock, its brand or its fonts cannot be drawn, the search for
     its lock stopped at its bound, or the location cannot be used; nothing is written.
     Or a write failed: it names the file, and every file is as it was before the run, or
     each it could not put back is named
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import checks, files, fingerprint, libraries, location, records, tokens
from _lib import pipeline as pl
from _lib.env import MissingFont
from _lib.findings import Finding
from _lib.plugins import seam
from _lib.root import LOCAL, project_root
from _lib.scene import SceneResult

#: The scenes of a piece, by language.
Results = Sequence[tuple[str, SceneResult]]

#: Where the previews of each piece lie, relative to the project root.
PREVIEWS = f"{LOCAL}/previews"

#: The comment that opens the findings record, a line each.
HEADER = (
    "The findings record of the piece (visual-communication DEC-005 point 13): what",
    "computing its scenes found, keyed by a fingerprint of every file they were computed",
    "from. `pkit visual render` rewrites it; commit it, so the check reads it.",
)


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pkit visual render",
        description="Compute a piece's scenes, keep their findings and draw its previews.",
    )
    parser.add_argument("piece", help="the piece's name: its folder under the location's pieces/")
    parser.add_argument("--location", help="the location to take and record, where none is")
    args = parser.parse_args()
    root = project_root()
    try:
        return _render(root, args.piece, args.location)
    except (
        pl.Refused,
        location.LocationRefused,
        location.GitFailed,
        files.WriteFailed,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _render(root: Path, name: str, given: str | None) -> int:
    where = location.for_writing(root, given)
    piece = pl.read_piece(root, where.path, name)
    held = libraries.Held(root, where.path)
    try:
        lock = libraries.move_lock(held, pl.needed(piece), piece.lock, pinned=piece.pinned)
    except libraries.LockRefused as exc:
        raise pl.Refused(f"{piece.file(pl.PIECE_FILE)}: {exc}") from exc
    try:
        project = pl.Project(piece, lock, held)
    except tokens.TokenError as exc:
        _print(exc.findings)
        raise pl.Refused(f"the brand of `{name}` cannot be read") from exc
    try:
        results = project.scenes()
    except MissingFont as exc:
        raise pl.Refused(
            f"the render of `{name}` is refused before anything is laid out: {exc}"
        ) from exc
    found = checks.scene_findings(project, results)
    lost = _known(results)
    previews = _draw(project, results, lost)
    # What can refuse is checked before the first write, so a refusal writes nothing: the
    # key is taken over `piece.yaml` as the render writes it.
    change = files.Change(root)
    said = location.record(change, where)
    locked = pl.locked(piece, lock)
    written = {piece.folder / pl.PIECE_FILE: locked} if locked is not None else {}
    sources = pl.findings_key_sources(root, held, piece, lock, sorted(project.env.fonts_read))
    record = {
        "pkit_schema": "visual-communication:findings",
        "schema_version": 1,
        "key": _key({**sources, "written": written}),
        "findings": [checks.record_entry(finding) for finding in found],
    }
    folder = root / PREVIEWS / name
    for path in (piece.folder / pl.FINDINGS_FILE, *(folder / file for file in previews)):
        pl.writable(root, path)
    # The previews first, the old ones removed once the new are in place; the records last.
    for file, text in previews.items():
        change.write(folder / file, text.encode("utf-8"))
    if folder.is_dir():
        for old in sorted(folder.glob("*.svg")):
            if old.name not in previews:
                change.remove(old)
    if locked is not None:
        change.write(piece.folder / pl.PIECE_FILE, locked)
    change.write(piece.folder / pl.FINDINGS_FILE, records.text(record, HEADER).encode("utf-8"))
    change.commit()
    if said is not None:
        print(said)
    if locked is not None:
        print(f"lock: {', '.join(f'{lib} {lock[lib]}' for lib in sorted(lock))}")
    print(f"previews: {len(previews)} file(s) in {PREVIEWS}/{name}/")
    for loss in lost:
        if not checks.accepted(loss, piece.accepted_losses):
            print(f"loss: {checks.loss_finding(loss).message}")
    _print(project.brand.findings)
    _print(checks.rooted(finding, piece) for finding in found if finding.code != "loss")
    print(f"findings: {len(found)} kept in {piece.file(pl.FINDINGS_FILE)}")
    return 0


def _key(sources: Mapping[str, Any]) -> dict[str, Any]:
    """The findings record's key over the files as the render leaves them: `sources` gives,
    under `written`, the bytes of each file the render writes. Raises Refused where one of
    them cannot be read under form 1."""
    try:
        return fingerprint.fingerprint(fingerprint.findings_key_inputs(**sources))
    except fingerprint.FingerprintError as exc:
        raise pl.Refused(f"the findings record's key cannot be taken: {exc}") from exc


def _draw(project: pl.Project, results: Results, lost: list[seam.Loss]) -> dict[str, str]:
    """Each preview's file name and text; what the renderer loses drawing them is added to
    `lost`."""
    name = project.piece.name
    previews: dict[str, str] = {}
    for language, key, drawn in pl.drawn(project, results, "svg"):
        for index, page in enumerate(drawn.pages, start=1):
            number = f".{index}" if len(drawn.pages) > 1 else ""
            previews[f"{name}.{language}.{key}{number}.svg"] = page.svg
        lost.extend(loss for loss in drawn.losses if loss not in lost)
    return previews


def _known(results: Results) -> list[seam.Loss]:
    """What the SVG renderer will lose of the scenes, known from its declaration before
    it runs (DEC-005 point 9)."""
    declared = seam.declaration("svg", seam.RENDERER)
    found: list[seam.Loss] = []
    for _, result in results:
        for loss in checks.losses(result.scene.to_dict(), declared):
            if loss not in found:
                found.append(loss)
    return found


def _print(found: Iterable[Finding]) -> None:
    for finding in found:
        print(f"{finding.level}: {checks.place(finding)}: {checks.said(finding)}")


if __name__ == "__main__":
    sys.exit(main())
