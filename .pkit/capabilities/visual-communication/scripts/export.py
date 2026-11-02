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
combination of modes it names, from the scene, under the lock its `piece.yaml` holds. The
run takes the next number of the piece's `exports.yaml`, and every file it makes carries
it: `<piece>.v<N>.<language>.<key>.svg`, in
`.pkit/capabilities/visual-communication/project/local/exports/<piece>/`, local to the
clone and never committed. It then records the version in `exports.yaml`: the fingerprint
of every file its scenes were computed from, each file's hash, and when, in which state,
by which release and renderers it was made.

It stops on a produced picture that is stale, naming what changed, unless `--use-stale`
names it; the record keeps each picture used while stale. It stops on a picture that is
missing, and on a piece with no lock yet, which `pkit visual render` writes.

It writes in the location, so where the configuration records none it takes `visual/` and
records it before its first write, or the path `--location` names.

Usage:
  pkit visual export <piece> [--use-stale <output>]... [--location <path>]

Exit codes:
  0  exported and recorded
  1  refused: nothing is written
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from _lib import checks, exports, libraries, location, tokens
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
    parser.add_argument("--location", help="the location to take and record, where none is")
    args = parser.parse_args()
    root = project_root()
    try:
        return _export(root, args.piece, args.use_stale, args.location)
    except (pl.Refused, location.LocationRefused, location.GitFailed) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _export(root: Path, name: str, use_stale: list[str], given: str | None) -> int:
    where = location.for_writing(root, given)
    piece = pl.read_piece(root, where.path, name)
    held = libraries.Held(root, where.path)
    faults = checks.lock_findings(held, piece)
    if faults:
        said = "; ".join(checks.said(finding) for finding in faults)
        raise pl.Refused(f"the lock of {piece.file(pl.PIECE_FILE)} cannot be exported: {said}")
    try:
        project = pl.Project(piece, piece.lock, held)
    except tokens.TokenError as exc:
        said = "; ".join(finding.message for finding in exc.findings)
        raise pl.Refused(f"the brand of `{name}` cannot be read: {said}") from exc
    planned = exports.plan(project, use_stale=use_stale)
    if where.record:
        print(location.record(root, where.path))
    exports.write(planned)
    for file in planned.files:
        print(f"export: {exports.FOLDER}/{name}/{file}")
    for output in planned.used_stale:
        print(f"used while stale: {output}")
    print(f"export: version {planned.number} recorded in {piece.file(pl.EXPORTS_FILE)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
