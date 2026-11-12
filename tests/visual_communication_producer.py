"""The producer kept for the visual-communication tests, and a piece that uses it (#2428;
DEC-006 Implications: the walking skeleton "proves the seam with a small producer kept for
its tests, which calls no outside program").

**The producer** `square` is never shipped: a test registers it in its own process with
`seam.register` (`register`), and takes it back after. Its input `fill` names a colour
role. For each variant it writes a solid PNG of that colour at the variant's pixels, with
the standard library alone (zlib and struct), and it exposes one point, `tip`, at the
middle of the top edge. Its other input, `edge`, may name a colour role too, which a
square of one colour cannot draw: it leaves the edge out and reports that loss, in the
seam's one form (DEC-005 point 9). It declares that it calls no outside program and
reaches no service, and calls none.

**The piece** (`producing_project`) is `flow`, in a project of its own: the shipped
foundations and the test brand copied into the location's library folder, and a draft
that declares the produced output `marker`, made by `square` from `accent`.
"""

from __future__ import annotations

import struct
import sys
import zlib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from tests.visual_communication_project import (
    RELEASED_FOUNDATIONS,
    TEST_BRAND,
    copy_library,
    project,
    write_piece,
)

NAME = "square"
VERSION = "1.0.0"

#: Its declaration, in the seam's form, which version 2 left as version 1 wrote it for a
#: producer: two inputs, each a colour role, the first required; and what it needs beyond
#: the project's files, which is nothing.
DECLARATION: dict[str, Any] = {
    "name": NAME,
    "kind": "producer",
    "version": VERSION,
    "seam": 8,
    "inputs": {
        "type": "object",
        "description": "What the square is painted with.",
        "properties": {
            "fill": {
                "description": "The colour the square is filled with.",
                "x-pkit-role": "color",
            },
            "edge": {
                "description": "The colour of the square's edge, which it leaves out.",
                "x-pkit-role": "color",
            },
        },
        "required": ["fill"],
        "additionalProperties": False,
    },
    "values": ["color"],
    "programs": [],
    "services": [],
}

#: Why the square leaves out the edge it is given.
NO_EDGE = "a square of one colour draws no edge"

#: The piece, its produced output, and the lock its first render would write.
PIECE = "flow"
OUTPUT = "marker"
LOCK = {"foundations": "1.0.0", "test-brand": "1.0.0"}

#: Both value axes of the test brand in every mode: four combinations.
EVERY_MODE = {"colour-scheme": ["light", "dark"], "contrast": ["standard", "high"]}

_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def produce(handover: Mapping[str, Any], out_dir: Path) -> dict[str, Any]:
    """Write each variant as a solid square of its `fill`, and expose `tip`; an `edge`
    given is left out, and reported as a loss."""
    fill = handover["tokens"][handover["inputs"]["fill"]]["values"]
    tip = {}
    for key, variant in handover["variants"].items():
        width, height = variant["pixels"]["width"], variant["pixels"]["height"]
        (out_dir / f"{key}.png").write_bytes(png(width, height, rgba(fill[key])))
        tip[key] = {"x": width / 2, "y": 0}
    result: dict[str, Any] = {"points": {"tip": tip}}
    edge = handover["inputs"].get("edge")
    if edge is not None:
        result["losses"] = [{"plugin": NAME, "what": edge, "did": "left-out", "why": NO_EDGE}]
    return result


def rgba(colour: Mapping[str, Any]) -> tuple[int, int, int, int]:
    """A colour of the values document, in its canonical form, as 8-bit RGBA."""
    red, green, blue = (round(component * 255) for component in colour["components"])
    return red, green, blue, round(colour["alpha"] * 255)


def png(width: int, height: int, colour: tuple[int, int, int, int]) -> bytes:
    """A PNG of `width` × `height` pixels, each of `colour` (8-bit RGBA)."""
    row = b"\x00" + bytes(colour) * width
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        _SIGNATURE
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", zlib.compress(row * height, 9))
        + _chunk(b"IEND", b"")
    )


def pixel(data: bytes) -> tuple[int, int, int, int]:
    """The first pixel of a PNG `png` wrote."""
    at, found = len(_SIGNATURE), b""
    while at < len(data):
        (length,) = struct.unpack(">I", data[at : at + 4])
        kind = data[at + 4 : at + 8]
        if kind == b"IDAT":
            found += data[at + 8 : at + 8 + length]
        at += 12 + length
    red, green, blue, alpha = zlib.decompress(found)[1:5]
    return red, green, blue, alpha


def register(
    seam: Any, declaration: Mapping[str, Any] | None = None, implementation: Any = None
) -> None:
    """Register the producer with `seam`, the seam module of the `_lib` a test loaded; or,
    given them, a producer of another declaration or implementation, such as one that
    misbehaves on purpose."""
    seam.register(dict(declaration or DECLARATION), implementation or sys.modules[__name__])


def producing_project(
    tmp_path: Path,
    *,
    modes: Mapping[str, list[str]] | None = None,
    produced: Mapping[str, Any] | None = None,
    lock: Mapping[str, str] | None = LOCK,
    accept_losses: Sequence[Mapping[str, str]] | None = None,
) -> Path:
    """A project whose piece `flow` declares `marker`, made by `square` from `accent` at
    64 × 64 pixels, drawn in every mode of both axes unless `modes` says otherwise; and
    accepting `accept_losses`, when given."""
    root = project(tmp_path)
    copy_library(root, RELEASED_FOUNDATIONS, "foundations", "1.0.0")
    copy_library(root, TEST_BRAND, "test-brand", "1.0.0")
    fields: dict[str, Any] = {
        "modes": dict(EVERY_MODE if modes is None else modes),
        "produced": dict(
            produced
            or {
                OUTPUT: {
                    "producer": NAME,
                    "inputs": {"fill": "accent"},
                    "pixels": {"width": 64, "height": 64},
                }
            }
        ),
    }
    if lock is not None:
        fields["lock"] = dict(lock)
    if accept_losses is not None:
        fields["accept-losses"] = [dict(entry) for entry in accept_losses]
    write_piece(root, PIECE, **fields)
    return root


def _chunk(kind: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(kind + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", crc)
