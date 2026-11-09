"""A PNG's samples decoded (visual-communication DEC-025 point 5), for the PDF renderer. It
embeds a PNG's image data as the file holds it where it can, and decodes it only to draw the
picture's transparency apart from its colours, as a soft mask.

- **What it reads** (`read`): a PNG's header, its palette, its transparency and its image
  data, each chunk bound by the file's size. It reads the encodings the picture reader reads
  (`_lib.pictures`), which judges the file first: 8 bits or fewer for each sample, not
  interlaced. A chunk the picture is drawn without is skipped.
- **Its samples** (`samples`): the image data inflated no further than the picture's own
  rows, each row's filter undone, the rows joined with no filter byte between them. A picture
  that would take more than `DECODED_BOUND` decoded, in its rows or in a byte for each of its
  pixels, is refused before any of it is inflated. `check` refuses what `samples` refuses,
  inflating the rows and undoing no filter, for a picture embedded as the file holds it.
- **Its transparency, apart from its colours:** an alpha channel taken out of the colours
  (`alpha_apart`); the alpha its palette gives each pixel (`palette_alpha`); and the one
  colour a grey or an RGB picture names transparent (`colour_key`). A transparency that does
  not fit the picture is left out, as a browser's PNG library leaves it out.

Every byte is untrusted: each length read is bound by the data, and a file truncated or
damaged raises Undecodable, never a crash. Standard library only.
"""

from __future__ import annotations

import struct
import zlib
from collections.abc import Callable
from dataclasses import dataclass

#: The first bytes of a PNG.
SIGNATURE = b"\x89PNG\r\n\x1a\n"

#: The colour types (PNG, "11.2.2 IHDR"): grey, RGB, a palette's indices, grey with alpha,
#: and RGB with alpha.
GREY, RGB, PALETTE, GREY_ALPHA, RGB_ALPHA = 0, 2, 3, 4, 6

#: The samples each pixel of a colour type holds.
CHANNELS = {GREY: 1, RGB: 3, PALETTE: 1, GREY_ALPHA: 2, RGB_ALPHA: 4}

#: The colour types whose pixels carry an alpha sample.
WITH_ALPHA = (GREY_ALPHA, RGB_ALPHA)

#: The bit depths each colour type is decoded in: those the picture reader reads.
DEPTHS = {GREY: (1, 2, 4, 8), RGB: (8,), PALETTE: (1, 2, 4, 8), GREY_ALPHA: (8,), RGB_ALPHA: (8,)}

#: The most bytes a picture may take decoded: its rows inflated, each with its filter's byte,
#: and a byte for each of its pixels, as its mask takes. Far above what a picture for a screen
#: needs, as 4 000 by 8 000 pixels with alpha take 122 MiB.
DECODED_BOUND = 2**27


class Undecodable(Exception):
    """A PNG this module does not decode, with why in words."""


@dataclass(frozen=True)
class Png:
    """A PNG read: its size in pixels, its bit depth and colour type; its palette, its
    transparency and its image data, each as the file holds it, empty where it holds none.
    The image data is its `IDAT` chunks joined, one zlib stream of its filtered rows."""

    width: int
    height: int
    depth: int
    colour: int
    palette: bytes
    transparency: bytes
    data: bytes

    @property
    def channels(self) -> int:
        """The samples each pixel holds."""
        return CHANNELS[self.colour]

    @property
    def row(self) -> int:
        """The bytes one row's samples take, its filter's byte left out."""
        return (self.width * self.channels * self.depth + 7) // 8


def read(data: bytes) -> Png:
    """The PNG whose bytes are `data`: its header, then the chunks it is decoded by. A palette
    or a transparency counts only before the image data, and only the first of each; a
    palette's transparency only after the palette, as a browser's PNG library reads them.
    Raises Undecodable."""
    if not data.startswith(SIGNATURE):
        raise Undecodable("it is no PNG")
    size = len(data)
    view = memoryview(data)
    at = len(SIGNATURE)
    header: tuple[int, int, int, int] | None = None
    palette = transparency = b""
    image = bytearray()
    seen = ended = False
    while at < size:
        if size - at < 12:
            raise Undecodable("it ends inside a chunk")
        length, kind = struct.unpack_from(">I4s", data, at)
        if length > size - at - 12:
            raise Undecodable("a chunk runs past the end of the file")
        body = view[at + 8 : at + 8 + length]
        at += 12 + length
        if header is None:
            if kind != b"IHDR" or length != 13:
                raise Undecodable("it does not start with its header, `IHDR`")
            header = _header(bytes(body))
            continue
        if kind == b"IEND":
            ended = True
            break
        if kind == b"IDAT":
            image += body
            seen = True
        elif kind == b"PLTE" and not seen and not palette:
            palette = bytes(body)
        elif kind == b"tRNS" and not seen and not transparency:
            if header[3] != PALETTE or palette:
                transparency = bytes(body)
    if header is None or not ended:
        raise Undecodable("it ends before its last chunk, `IEND`")
    if not seen:
        raise Undecodable("it holds no image data, `IDAT`")
    width, height, depth, colour = header
    if colour == PALETTE and (not palette or len(palette) % 3 or len(palette) > 3 * 256):
        raise Undecodable("its palette, `PLTE`, is not of whole colours")
    return Png(
        width,
        height,
        depth,
        colour,
        palette if colour == PALETTE else b"",
        transparency if colour in (GREY, RGB, PALETTE) else b"",
        bytes(image),
    )


def _header(body: bytes) -> tuple[int, int, int, int]:
    """A PNG's width, height, bit depth and colour type, from its `IHDR`, of an encoding
    decoded here. Raises Undecodable."""
    width, height, depth, colour, compression, filtering, interlace = struct.unpack(
        ">IIBBBBB", body
    )
    if not 0 < width < 2**31 or not 0 < height < 2**31:
        raise Undecodable(f"its header gives a size of {width} × {height} pixels")
    if colour not in DEPTHS or depth not in DEPTHS[colour]:
        raise Undecodable(f"its header gives {depth} bits to the colour type {colour}")
    if compression or filtering or interlace:
        raise Undecodable("its header names a method not decoded here, or interlacing")
    return width, height, depth, colour


def samples(picture: Png) -> bytes:
    """The picture's samples, row after row, each row's filter undone and its filter's byte
    left out: its image data inflated to its rows, and no further. Raises Undecodable as
    `check` does."""
    filtered = _filtered(picture)
    row = picture.row
    stride = row + 1
    step = max(1, picture.channels * picture.depth // 8)
    out = bytearray(picture.height * row)
    above = bytes(row)
    for y in range(picture.height):
        at = y * stride
        above = _FILTERS[filtered[at]](filtered[at + 1 : at + stride], above, step)
        out[y * row : (y + 1) * row] = above
    return bytes(out)


def check(picture: Png) -> None:
    """That the picture decodes, for one embedded as the file holds it, so that no file holds
    a picture that `samples` refuses. Raises Undecodable for a picture that would take more
    than `DECODED_BOUND` decoded, image data that is damaged or ends before its last row, and
    a filter no PNG defines."""
    _filtered(picture)


def decoded_size(picture: Png) -> int:
    """The most bytes the picture takes decoded: its rows inflated, each with its filter's
    byte, or a byte for each of its pixels, as its mask takes, where that is more."""
    return max(picture.height * (picture.row + 1), picture.width * picture.height)


def _filtered(picture: Png) -> bytes:
    """The picture's rows inflated, each with its filter's byte before it, and no further,
    each filter one a PNG defines. Raises Undecodable as `check` does."""
    size = decoded_size(picture)
    if size > DECODED_BOUND:
        raise Undecodable(
            f"its {picture.width} × {picture.height} pixels would take {-(-size // 2**20)} MiB "
            f"decoded, more than the {DECODED_BOUND // 2**20} MiB decoded here"
        )
    stride = picture.row + 1
    expected = picture.height * stride
    inflater = zlib.decompressobj()
    try:
        filtered = inflater.decompress(picture.data, expected)
    except zlib.error:
        raise Undecodable("its image data, `IDAT`, is damaged") from None
    if len(filtered) < expected:
        raise Undecodable("its image data, `IDAT`, ends before its last row")
    unknown = filtered[::stride].translate(None, _KNOWN_FILTERS)
    if unknown:
        raise Undecodable(f"a row's filter, {unknown[0]}, is none a PNG defines")
    return filtered


def alpha_apart(picture: Png, decoded: bytes) -> tuple[bytes, bytes]:
    """The colours and the alpha of a picture of a colour type with alpha, `decoded` its
    samples: each pixel's grey or RGB samples, and its alpha, one byte each."""
    if picture.colour == GREY_ALPHA:
        return decoded[0::2], decoded[1::2]
    colours = bytearray(len(decoded) // 4 * 3)
    for channel in range(3):
        colours[channel::3] = decoded[channel::4]
    return bytes(colours), decoded[3::4]


def has_palette_alpha(picture: Png) -> bool:
    """Whether a palette's picture gives some index an alpha: a transparency of no more
    entries than its palette, as a browser's PNG library reads it."""
    return picture.colour == PALETTE and 0 < len(picture.transparency) <= len(picture.palette) // 3


def palette_alpha(picture: Png, decoded: bytes) -> bytes:
    """The alpha of each pixel of a palette's picture, `decoded` its samples, one byte each,
    row after row: the alpha its transparency gives the pixel's index, or opaque for an
    index past those it gives."""
    alphas = picture.transparency[:256].ljust(256, b"\xff")
    if picture.depth == 8:
        return decoded.translate(alphas)
    each = 8 // picture.depth
    mask = (1 << picture.depth) - 1
    # For each index a byte holds, from its high bits, the alpha that index takes.
    tables = [
        bytes(alphas[(byte >> (8 - picture.depth * (place + 1))) & mask] for byte in range(256))
        for place in range(each)
    ]
    out = bytearray()
    row = picture.row
    for y in range(picture.height):
        packed = decoded[y * row : (y + 1) * row]
        spread = bytearray(each * row)
        for place, table in enumerate(tables):
            spread[place::each] = packed.translate(table)
        out += spread[: picture.width]
    return bytes(out)


def colour_key(picture: Png) -> tuple[int, ...] | None:
    """The one colour a grey or an RGB picture names transparent, as a sample for each of its
    channels; None where it names none, or one its samples cannot hold, which no pixel
    takes."""
    given = picture.transparency
    if picture.colour == GREY and len(given) == 2:
        key = struct.unpack(">H", given)
    elif picture.colour == RGB and len(given) == 6:
        key = struct.unpack(">HHH", given)
    else:
        return None
    if any(sample >= 1 << picture.depth for sample in key):
        return None
    return key


# --- undoing a row's filter ---------------------------------------------------------------------
#
# Each takes a row's filtered bytes, the row above as decoded (zeros above the first), and how
# many bytes back the same sample of the pixel to the left lies, and gives the row decoded
# (PNG, "9.2 Filter types for filter method 0"). Every sum is modulo 256.


def _none(line: bytes, above: bytes, step: int) -> bytes:
    return line


def _sub(line: bytes, above: bytes, step: int) -> bytes:
    out = bytearray(line)
    for at in range(step, len(out)):
        out[at] = (out[at] + out[at - step]) & 0xFF
    return bytes(out)


def _up(line: bytes, above: bytes, step: int) -> bytes:
    # Each byte's sum at once: the low seven bits of each pair added, which never carries
    # into the next byte, and the top bit of each set by the two top bits it adds.
    length = len(line)
    low, top = int.from_bytes(b"\x7f" * length, "big"), int.from_bytes(b"\x80" * length, "big")
    x, y = int.from_bytes(line, "big"), int.from_bytes(above, "big")
    return (((x & low) + (y & low)) ^ ((x ^ y) & top)).to_bytes(length, "big")


def _average(line: bytes, above: bytes, step: int) -> bytes:
    out = bytearray(line)
    for at in range(min(step, len(out))):
        out[at] = (out[at] + (above[at] >> 1)) & 0xFF
    for at in range(step, len(out)):
        out[at] = (out[at] + ((out[at - step] + above[at]) >> 1)) & 0xFF
    return bytes(out)


def _paeth(line: bytes, above: bytes, step: int) -> bytes:
    out = bytearray(line)
    for at in range(min(step, len(out))):
        out[at] = (out[at] + above[at]) & 0xFF
    for at in range(step, len(out)):
        left, up, corner = out[at - step], above[at], above[at - step]
        to_left, to_up = abs(up - corner), abs(left - corner)
        to_corner = abs(left + up - 2 * corner)
        if to_left <= to_up and to_left <= to_corner:
            predicted = left
        elif to_up <= to_corner:
            predicted = up
        else:
            predicted = corner
        out[at] = (out[at] + predicted) & 0xFF
    return bytes(out)


_FILTERS: dict[int, Callable[[bytes, bytes, int], bytes]] = {
    0: _none,
    1: _sub,
    2: _up,
    3: _average,
    4: _paeth,
}

#: The byte of each filter a PNG defines.
_KNOWN_FILTERS = bytes(_FILTERS)
