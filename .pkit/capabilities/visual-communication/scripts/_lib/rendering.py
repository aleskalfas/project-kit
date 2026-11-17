"""What the commands that take a piece under one lock share (visual-communication DEC-005 point
13, DEC-006 point 7, DEC-019 point 2).

- **The piece an export run takes** (`exportable`). The lock is held to what the check holds
  it to, and the brand must read. `pkit visual export` takes the piece's own lock, and the run
  that proposes a move takes the moved one, so a move follows the same rule.
- **The findings record** (`record`, `record_text`). What computing the scenes found, keyed
  over the files as the run leaves them, so a run takes the key before its first write.
  `pkit visual render` and the run that proposes a move write it. The record reads no preview,
  so a run that draws none keeps it as a render does.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from _lib import checks, fingerprint, records, tokens
from _lib import pipeline as pl
from _lib.findings import Finding
from _lib.libraries import Held

#: The comment that opens the findings record, a line each.
HEADER = (
    "The findings record of the piece (visual-communication DEC-005 point 13): what",
    "computing its scenes found, keyed by a fingerprint of every file they were computed",
    "from. `pkit visual render` rewrites it; commit it, so the check reads it.",
)


def exportable(piece: pl.Piece, held: Held) -> pl.Project:
    """The piece under its lock, as an export run takes it. Raises Refused where a finding
    stands at that lock, or the brand cannot be read."""
    faults = checks.lock_findings(held, piece)
    if faults:
        said = "; ".join(checks.said(finding) for finding in faults)
        raise pl.Refused(f"the lock of {piece.file(pl.PIECE_FILE)} cannot be exported: {said}")
    try:
        return pl.Project(piece, piece.lock, held)
    except tokens.TokenError as exc:
        said = "; ".join(finding.message for finding in exc.findings)
        raise pl.Refused(f"the brand of `{piece.name}` cannot be read: {said}") from exc


def record(project: pl.Project, found: Sequence[Finding], locked: bytes | None) -> dict[str, Any]:
    """The piece's findings record: what its scenes `found`, keyed over the files as the run
    leaves them, `locked` the bytes of `piece.yaml` where it writes them. Raises Refused where
    one of them cannot be read under form 1."""
    piece = project.piece
    written = {piece.folder / pl.PIECE_FILE: locked} if locked is not None else {}
    sources = pl.findings_key_sources(
        project.root, project.held, piece, project.lock, sorted(project.env.fonts_read)
    )
    return {
        "pkit_schema": "visual-communication:findings",
        "schema_version": 1,
        "key": _key({**sources, "written": written}),
        "findings": [checks.record_entry(finding) for finding in found],
    }


def record_text(kept: Mapping[str, Any]) -> bytes:
    """The bytes of the findings record `kept`, as a run writes it."""
    return records.text(kept, HEADER).encode("utf-8")


def _key(sources: Mapping[str, Any]) -> dict[str, Any]:
    """The findings record's key over the files as the run leaves them: `sources` gives, under
    `written`, the bytes of each file the run writes. Raises Refused where one of them cannot
    be read under form 1."""
    try:
        return fingerprint.fingerprint(fingerprint.findings_key_inputs(**sources))
    except fingerprint.FingerprintError as exc:
        raise pl.Refused(f"the findings record's key cannot be taken: {exc}") from exc
