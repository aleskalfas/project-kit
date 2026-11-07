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
"""visual-communication capability — export: a numbered export of a piece, and its record
(DEC-006 point 7).

Makes each format the piece declares under `exports`, in each of its languages and each
combination of modes it names, from the scene, under the lock its `piece.yaml` holds:
`svg`, one file for each page, and `pdf`, one file that holds every page in order. The run
takes the piece's next number, past every version its `exports.yaml` records and every
file of its exports folder, and every file it makes carries it:
`<piece>.v<N>.<language>.<key>.<format>`, and for an SVG file of a piece of more than one
page `<piece>.v<N>.<language>.<key>.<n>.svg`, its page's number from 1, in
`.pkit/capabilities/visual-communication/project/local/exports/<piece>/`, local to the
clone and never committed. It then records the version in `exports.yaml`: the fingerprint
of every file its scenes were computed from, each file's hash, and when, in which state,
by which release and renderers it was made.

Where a component shows a version's number or its date, every file of the version shows
the number and the date of the time its record keeps (DEC-016 point 5). The run measures
that text where it fills it, from a font file, and stops on a text that overflows its width,
or a component around it that gets less than it asks for, naming the fact, its text and the
element, in any library, unless `--use-overflowing version` or `--use-overflowing date`
names the fact (DEC-016 point 6). The record keeps each text let through. An overflow
measured from a table or by an estimate stops nothing, and the run says it. Naming the
language or the state is refused: the check measures them as they stand.

It stops on a produced picture that is stale, naming what changed, unless `--use-stale`
names it; the record keeps each picture used while stale, and the version of each picture
the export used. `--use-stale` naming an output the piece does not declare is refused; one
that is not stale is used as it is, and the command says so. It stops on a picture that is
missing, and on a piece with no lock yet, which `pkit visual render` writes of a draft. A
final piece takes no export, whatever else holds of it, final by its state or by a version
handed out, or where its record of exports cannot be read, and the refusal names
`pkit visual take-up`, which copies it for new work (DEC-017 point 3).

A published piece's run also writes its current copy, an unnumbered copy of each file of
the version, in the piece's `current-copy/`, replacing that folder whole, and `exports.yaml`
names the version that wrote it. A piece that names a place under `copy-place` takes the
copy there instead: the run refuses a place the rules refuse, and any file at a path it
writes but one of the piece's own copy, with the hash the record keeps (DEC-017 point 8). It
removes nothing there: it names each file of the last copy it did not write again, which
stays where it lies (DEC-017 point 7). A piece in any other state writes none. It refuses a
published piece whose lock differs from the lock of the version that wrote its current copy,
and names both ways past (DEC-017 point 5): the gate reads the record, not the files, and
holds only this command, so it lies here, outside what `exports.plan` and `exports.add`
share with the run that proposes a move of the lock.

It writes in the location, so where the configuration records none it takes `visual/` and
records it before its first write, or the path `--location` names. Every check that can
refuse runs before that first write, so a refused export writes nothing, the location
included. It writes the files, the current copy, then `exports.yaml`, as one change: a
write that fails removes the files the run wrote, and leaves the current copy, the record
and the configuration as they were.

Usage:
  pkit visual export <piece> [--use-stale <output>]... [--use-overflowing <fact>]...
                     [--location <path>]

Exit codes:
  0  exported and recorded
  1  refused: nothing is written. Or a write failed: it names the file, and every file is
     as it was before the run, or each it could not put back is named
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import copies, current_copy, exports, files, fingerprint, libraries, location, rendering
from _lib import pipeline as pl
from _lib.root import project_root


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="pkit visual export",
        description="Make a numbered export of a piece in each format it declares.",
    )
    parser.add_argument("piece", help="the piece's name: its folder under the location's pieces/")
    parser.add_argument(
        "--use-stale",
        action="append",
        default=[],
        metavar="OUTPUT",
        help="export with this produced picture as it is, though it is stale; may repeat",
    )
    parser.add_argument(
        "--use-overflowing",
        action="append",
        default=[],
        metavar="FACT",
        help="export with this fact's text as it is, `version` or `date`, though it overflows; "
        "may repeat",
    )
    parser.add_argument("--location", help="the location to take and record, where none is")
    args = parser.parse_args()
    root = project_root()
    try:
        return _export(root, args.piece, args.use_stale, args.use_overflowing, args.location)
    except (
        pl.Refused,
        location.LocationRefused,
        location.GitFailed,
        files.WriteFailed,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _export(
    root: Path, name: str, use_stale: list[str], use_overflowing: list[str], given: str | None
) -> int:
    where = location.for_writing(root, given)
    piece = pl.read_piece(root, where.path, name)
    if piece.final:
        raise pl.Refused(
            f"the piece `{name}` is final ({piece.why_final}), and a final piece takes no export: "
            f"run {copies.take_up_command(name)} to take it up again as a new draft"
        )
    _refuse_a_lock_that_differs(piece)
    project = rendering.exportable(piece, libraries.Held(root, where.path))
    planned = exports.plan(project, use_stale=use_stale, use_overflowing=use_overflowing)
    change = files.Change(root)
    said = location.record(change, where)
    exports.write(planned, change)
    if said is not None:
        print(said)
    for line in exports.report(planned):
        print(line)
    return 0


def _refuse_a_lock_that_differs(piece: pl.Piece) -> None:
    """Raise Refused where the piece is published and its lock differs from the lock of the
    version that wrote its current copy, or that lock cannot be read (DEC-017 point 5). It
    reads the record, not the files, and compares nothing where the record holds no current
    copy of the piece's own."""
    if not current_copy.keeps(piece):
        return
    record = exports.recorded(piece)
    entry = current_copy.own(piece, record)
    if entry is None:
        return
    versions = exports.recorded_versions(piece, record)
    wrote = f"version {entry['version']}, which wrote the piece's current copy"
    try:
        lock = current_copy.written_lock(entry, versions)
    except fingerprint.UnreadableFingerprint as exc:
        raise pl.Refused(
            f"{piece.file(pl.EXPORTS_FILE)} gives no lock of {wrote}: {exc}. Mend it before the "
            f"next export"
        ) from exc
    if lock != piece.lock:
        said = ", ".join(f"{library}@{version}" for library, version in sorted(lock.items()))
        raise pl.Refused(
            f"the lock of {piece.file(pl.PIECE_FILE)} differs from the lock of {wrote}: {said}. "
            f"Run `pkit visual upgrade {piece.name}` to propose a move of the lock, or write "
            f"that lock back, which is no move of it"
        )


if __name__ == "__main__":
    sys.exit(main())
