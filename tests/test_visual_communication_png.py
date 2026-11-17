"""The PNG decoder the PDF renderer decodes a picture's transparency with (visual-communication
DEC-025 point 5, `_lib/png.py`): the chunks it reads, each row's filter undone, an alpha
channel apart from the colours, a palette's alpha and a colour key, the transparency a
browser's PNG library leaves out, and a file damaged, cut short or too large decoded, refused
with why, and never a crash.

The pictures are built here, of random samples filtered by each of the five filters, so each
decodes back to the samples it was built of. The test pictures (`TEST_PICTURES`) the renderers'
tests draw decode too.
"""

from __future__ import annotations

import random
import struct
import zlib
from collections.abc import Callable, Sequence
from typing import Any

import pytest

from tests.in_process import load
from tests.visual_communication_project import TEST_PICTURES

(png,) = load("visual-communication", "png")

#: Each colour type with each bit depth decoded.
ENCODINGS = [(colour, depth) for colour, depths in sorted(png.DEPTHS.items()) for depth in depths]


def chunk(kind: bytes, body: bytes) -> bytes:
    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))


def paeth(left: int, up: int, corner: int) -> int:
    guess = left + up - corner
    to_left, to_up, to_corner = abs(guess - left), abs(guess - up), abs(guess - corner)
    if to_left <= to_up and to_left <= to_corner:
        return left
    return up if to_up <= to_corner else corner


def filtered(rows: Sequence[bytes], step: int, methods: Sequence[int]) -> bytes:
    """`rows` filtered, the row `y` by `methods[y % len(methods)]`, each after its filter's
    byte (PNG, "9.2 Filter types for filter method 0")."""
    out = bytearray()
    above = bytes(len(rows[0]))
    for y, row in enumerate(rows):
        method = methods[y % len(methods)]
        line = bytearray()
        for at, sample in enumerate(row):
            left = row[at - step] if at >= step else 0
            corner = above[at - step] if at >= step else 0
            predicted = (
                0,
                left,
                above[at],
                (left + above[at]) // 2,
                paeth(left, above[at], corner),
            )
            line.append((sample - predicted[method]) & 0xFF)
        out += bytes([method]) + line
        above = row
    return bytes(out)


def built(
    width: int,
    height: int,
    depth: int,
    colour: int,
    rows: Sequence[bytes],
    *,
    methods: Sequence[int] = (0,),
    before: Sequence[bytes] = (),
    after: Sequence[bytes] = (),
    data: bytes | None = None,
    interlace: int = 0,
) -> bytes:
    """A PNG of `rows`, filtered by `methods`, with the chunks `before` its image data and
    `after` it; or with `data` as its image data."""
    header = struct.pack(">IIBBBBB", width, height, depth, colour, 0, 0, interlace)
    if data is None:
        step = max(1, png.CHANNELS[colour] * depth // 8)
        data = zlib.compress(filtered(rows, step, methods))
    return (
        png.SIGNATURE
        + chunk(b"IHDR", header)
        + b"".join(before)
        + chunk(b"IDAT", data)
        + b"".join(after)
        + chunk(b"IEND", b"")
    )


def random_rows(width: int, height: int, depth: int, colour: int, seed: int = 1) -> list[bytes]:
    row = (width * png.CHANNELS[colour] * depth + 7) // 8
    rnd = random.Random(seed)
    return [rnd.randbytes(row) for _ in range(height)]


# --- its samples --------------------------------------------------------------------------------


@pytest.mark.parametrize("method", [0, 1, 2, 3, 4])
@pytest.mark.parametrize(("colour", "depth"), ENCODINGS)
def test_each_filter_of_each_encoding_decodes_back_to_its_samples(
    colour: int, depth: int, method: int
) -> None:
    rows = random_rows(7, 5, depth, colour)
    picture = png.read(built(7, 5, depth, colour, rows, methods=[method], before=_palette(colour)))
    assert (picture.width, picture.height, picture.depth, picture.colour) == (7, 5, depth, colour)
    assert png.samples(picture) == b"".join(rows)


@pytest.mark.parametrize(("colour", "depth"), ENCODINGS)
def test_rows_of_each_filter_in_turn_decode_back_to_their_samples(colour: int, depth: int) -> None:
    rows = random_rows(13, 11, depth, colour, seed=2)
    data = built(13, 11, depth, colour, rows, methods=[4, 3, 2, 1, 0], before=_palette(colour))
    assert png.samples(png.read(data)) == b"".join(rows)


def test_image_data_in_several_chunks_is_read_as_one_stream() -> None:
    rows = random_rows(5, 4, 8, png.RGB_ALPHA)
    stream = zlib.compress(filtered(rows, 4, [4]))
    whole = built(5, 4, 8, png.RGB_ALPHA, rows)
    split = whole.replace(
        chunk(b"IDAT", stream), chunk(b"IDAT", stream[:7]) + chunk(b"IDAT", stream[7:])
    )
    assert png.samples(png.read(split)) == b"".join(rows)


def test_a_chunk_the_picture_is_drawn_without_is_skipped() -> None:
    rows = random_rows(3, 2, 8, png.GREY)
    data = built(3, 2, 8, png.GREY, rows, before=[chunk(b"tEXt", b"Title\0A")])
    assert png.samples(png.read(data)) == b"".join(rows)


def _palette(colour: int) -> list[bytes]:
    """A palette of 256 colours, for a picture of a palette's indices."""
    return [chunk(b"PLTE", bytes(range(256)) * 3)] if colour == png.PALETTE else []


# --- its transparency ---------------------------------------------------------------------------


def test_an_alpha_channel_is_taken_apart_from_the_rgb_colours() -> None:
    pixels = [bytes([10, 20, 30, 40, 50, 60, 70, 80]), bytes([1, 2, 3, 4, 5, 6, 7, 8])]
    picture = png.read(built(2, 2, 8, png.RGB_ALPHA, pixels, methods=[1, 4]))
    colours, alpha = png.alpha_apart(picture, png.samples(picture))
    assert colours == bytes([10, 20, 30, 50, 60, 70, 1, 2, 3, 5, 6, 7])
    assert alpha == bytes([40, 80, 4, 8])


def test_an_alpha_channel_is_taken_apart_from_the_grey() -> None:
    pixels = [bytes([10, 200, 30, 0, 50, 255])]
    picture = png.read(built(3, 1, 8, png.GREY_ALPHA, pixels, methods=[3]))
    assert png.alpha_apart(picture, png.samples(picture)) == (
        bytes([10, 30, 50]),
        bytes([200, 0, 255]),
    )


@pytest.mark.parametrize("depth", [1, 2, 4, 8])
def test_a_palettes_alpha_is_given_each_pixel_by_its_index(depth: int) -> None:
    """Each index the transparency gives takes its alpha, and each past it is opaque; a row's
    padding bits are no pixel."""
    width, height = 5, 3
    entries = 1 << depth
    rnd = random.Random(depth)
    indices = [[rnd.randrange(entries) for _ in range(width)] for _ in range(height)]
    rows = [_packed(row, depth) for row in indices]
    given = bytes([0, 128, 255, 64, 32][: min(entries, 5) - 1])
    data = built(
        width, height, depth, png.PALETTE, rows, methods=[2],
        before=[chunk(b"PLTE", bytes(3 * entries)), chunk(b"tRNS", given)],
    )  # fmt: skip
    picture = png.read(data)
    assert png.has_palette_alpha(picture)
    alphas = given + b"\xff" * (256 - len(given))
    expected = bytes(alphas[index] for row in indices for index in row)
    assert png.palette_alpha(picture, png.samples(picture)) == expected


def _packed(indices: Sequence[int], depth: int) -> bytes:
    """Indices of `depth` bits packed into bytes, from each byte's high bits, the last byte
    padded with zeros."""
    bits = "".join(format(index, f"0{depth}b") for index in indices)
    bits += "0" * (-len(bits) % 8)
    return bytes(int(bits[at : at + 8], 2) for at in range(0, len(bits), 8))


@pytest.mark.parametrize(
    ("chunks", "said"),
    [
        ([chunk(b"PLTE", bytes(6)), chunk(b"tRNS", bytes(3))], "more entries than the palette"),
        ([chunk(b"tRNS", bytes(1)), chunk(b"PLTE", bytes(6))], "before the palette"),
        ([chunk(b"PLTE", bytes(6)), chunk(b"tRNS", b"")], "of no entry"),
    ],
)
def test_a_palettes_transparency_that_does_not_fit_is_left_out(
    chunks: list[bytes], said: str
) -> None:
    picture = png.read(built(2, 1, 8, png.PALETTE, [bytes(2)], before=chunks))
    assert not png.has_palette_alpha(picture), said


def test_a_transparency_after_the_image_data_is_left_out() -> None:
    late = chunk(b"tRNS", bytes(1))
    data = built(2, 1, 8, png.PALETTE, [bytes(2)], before=_palette(png.PALETTE), after=[late])
    assert not png.has_palette_alpha(png.read(data))


@pytest.mark.parametrize(
    ("colour", "depth", "given", "key"),
    [
        (png.GREY, 8, struct.pack(">H", 200), (200,)),
        (png.GREY, 2, struct.pack(">H", 3), (3,)),
        (png.RGB, 8, struct.pack(">HHH", 1, 2, 255), (1, 2, 255)),
        (png.GREY, 2, struct.pack(">H", 4), None),
        (png.RGB, 8, struct.pack(">HHH", 1, 256, 3), None),
        (png.GREY, 8, struct.pack(">HHH", 1, 2, 3), None),
        (png.RGB, 8, struct.pack(">H", 1), None),
    ],
    ids=["grey", "grey-of-2-bits", "rgb", "past-2-bits", "past-8-bits", "grey-of-6", "rgb-of-2"],
)
def test_a_colour_named_transparent_is_a_key_where_the_samples_can_hold_it(
    colour: int, depth: int, given: bytes, key: tuple[int, ...] | None
) -> None:
    rows = random_rows(3, 2, depth, colour)
    picture = png.read(built(3, 2, depth, colour, rows, before=[chunk(b"tRNS", given)]))
    assert png.colour_key(picture) == key


def test_a_colour_type_with_alpha_takes_no_other_transparency() -> None:
    rows = random_rows(2, 2, 8, png.RGB_ALPHA)
    picture = png.read(built(2, 2, 8, png.RGB_ALPHA, rows, before=[chunk(b"tRNS", bytes(6))]))
    assert picture.transparency == b""
    assert png.colour_key(picture) is None


# --- the test pictures --------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["palette.png", "grey.png", "alpha.png", "profile.png"])
def test_each_test_picture_the_renderers_draw_decodes(name: str) -> None:
    picture = png.read((TEST_PICTURES / name).read_bytes())
    decoded = png.samples(picture)
    assert (picture.width, picture.height) == (4, 3)
    assert len(decoded) == picture.row * picture.height


# --- what is refused ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("depth", "colour", "interlace", "said"),
    [
        (16, png.RGB, 0, "16 bits to the colour type 2"),
        (8, png.RGB, 1, "interlacing"),
        (8, 1, 0, "8 bits to the colour type 1"),
        (3, png.GREY, 0, "3 bits to the colour type 0"),
    ],
)
def test_an_encoding_the_picture_reader_refuses_is_not_decoded(
    depth: int, colour: int, interlace: int, said: str
) -> None:
    data = built(1, 1, depth, colour, [], data=zlib.compress(b"\0\0"), interlace=interlace)
    with pytest.raises(png.Undecodable, match=said):
        png.read(data)


def test_rows_larger_than_the_bound_are_refused_before_any_is_inflated() -> None:
    side = 2**31 - 1
    huge = built(side, side, 8, png.RGB_ALPHA, [], data=zlib.compress(bytes(2**20)))
    picture = png.read(huge)
    with pytest.raises(png.Undecodable, match="more than the 128 MiB decoded here"):
        png.samples(picture)
    # One row past the bound is refused, and the rows the bound holds are inflated.
    width = png.DECODED_BOUND // 4 - 1
    just = png.read(built(width, 1, 8, png.RGB_ALPHA, [], data=zlib.compress(bytes(9))))
    with pytest.raises(png.Undecodable, match="ends before its last row"):
        png.samples(just)
    past = png.read(built(width + 1, 1, 8, png.RGB_ALPHA, [], data=zlib.compress(bytes(9))))
    with pytest.raises(png.Undecodable, match="more than the 128 MiB decoded here"):
        png.samples(past)


@pytest.mark.parametrize("decode", [png.samples, png.check], ids=["samples", "check"])
def test_pixels_beyond_the_bound_are_refused_where_their_rows_are_not(
    decode: Callable[[Any], object],
) -> None:
    """A palette of 1 bit packs eight pixels in a byte, and its mask takes a byte for each:
    so 32 768 by 32 760 pixels take 128 MiB in their rows and 1 GiB in their mask."""
    rows = zlib.compress(bytes(32760 * 4097), 9)
    palette = [chunk(b"PLTE", bytes(6)), chunk(b"tRNS", b"\0")]
    bomb = png.read(built(32768, 32760, 1, png.PALETTE, [], before=palette, data=rows))
    assert png.decoded_size(bomb) == 32768 * 32760 > png.DECODED_BOUND >= 32760 * 4097
    with pytest.raises(
        png.Undecodable,
        match="its 32768 × 32760 pixels would take 1024 MiB decoded, more than the 128 MiB",
    ):
        decode(bomb)
    # One pixel past the bound is refused, and the pixels the bound holds are decoded.
    side = png.DECODED_BOUND
    just = png.read(built(side, 1, 1, png.GREY, [], data=zlib.compress(bytes(side // 8 + 1))))
    decoded = decode(just)
    assert decoded is None or decoded == bytes(side // 8)
    past = png.read(built(side + 1, 1, 1, png.GREY, [], data=zlib.compress(bytes(side // 8 + 2))))
    with pytest.raises(png.Undecodable, match="would take 129 MiB decoded"):
        decode(past)


def test_image_data_that_inflates_past_its_rows_is_inflated_no_further() -> None:
    rows = [bytes(4)] * 3
    bomb = zlib.compress(filtered(rows, 1, [0]) + bytes(64 * 2**20), 9)
    picture = png.read(built(4, 3, 8, png.GREY, rows, data=bomb))
    assert png.samples(picture) == bytes(12)


@pytest.mark.parametrize(
    ("data", "said"),
    [
        (zlib.compress(b"\0" * 5), "ends before its last row"),
        (b"\x78\x9c\xff\xff\xff", "is damaged"),
        (
            zlib.compress(b"\x05" + bytes(4) + b"\0" * 10),
            "a row's filter, 5, is none a PNG defines",
        ),
    ],
    ids=["cut-short", "damaged", "unknown-filter"],
)
@pytest.mark.parametrize("decode", [png.samples, png.check], ids=["samples", "check"])
def test_image_data_damaged_or_cut_short_is_refused_with_why(
    data: bytes, said: str, decode: Callable[[Any], object]
) -> None:
    picture = png.read(built(4, 3, 8, png.GREY, [bytes(4)] * 3, data=data))
    with pytest.raises(png.Undecodable, match=said):
        decode(picture)


def test_a_picture_that_decodes_passes_its_check() -> None:
    for name in ("grey.png", "profile.png", "palette.png", "alpha.png"):
        png.check(png.read((TEST_PICTURES / name).read_bytes()))


@pytest.mark.parametrize(
    ("data", "said"),
    [
        (b"GIF89a", "it is no PNG"),
        (png.SIGNATURE + b"\0\0", "ends inside a chunk"),
        (png.SIGNATURE + struct.pack(">I", 99) + b"IHDR" + bytes(20), "runs past the end"),
        (png.SIGNATURE + chunk(b"IEND", b""), "does not start with its header"),
    ],
)
def test_a_file_out_of_shape_is_refused_with_why(data: bytes, said: str) -> None:
    with pytest.raises(png.Undecodable, match=said):
        png.read(data)


def test_a_file_with_no_image_data_or_no_end_is_refused() -> None:
    whole = built(1, 1, 8, png.GREY, [b"\0"])
    no_data = whole.replace(chunk(b"IDAT", zlib.compress(b"\0\0")), b"")
    with pytest.raises(png.Undecodable, match="holds no image data"):
        png.read(no_data)
    with pytest.raises(png.Undecodable, match="ends before its last chunk"):
        png.read(whole[: -len(chunk(b"IEND", b""))])


def test_a_palettes_picture_with_no_palette_of_whole_colours_is_refused() -> None:
    for palette in ([], [chunk(b"PLTE", bytes(4))], [chunk(b"PLTE", bytes(3 * 257))]):
        with pytest.raises(png.Undecodable, match="not of whole colours"):
            png.read(built(1, 1, 8, png.PALETTE, [b"\0"], before=palette))


@pytest.mark.parametrize("name", ["palette.png", "alpha.png", "grey.png", "profile.png"])
def test_every_test_picture_cut_short_or_damaged_decodes_or_is_refused_and_never_crashes(
    name: str,
) -> None:
    whole = (TEST_PICTURES / name).read_bytes()
    rnd = random.Random(name)
    variants = [whole[:cut] for cut in range(len(whole))]
    for _ in range(300):
        damaged = bytearray(whole)
        for _ in range(rnd.randrange(1, 4)):
            damaged[rnd.randrange(len(damaged))] = rnd.randrange(256)
        variants.append(bytes(damaged))
    for data in variants:
        try:
            picture = png.read(data)
            decoded = png.samples(picture)
            if picture.colour in png.WITH_ALPHA:
                png.alpha_apart(picture, decoded)
            if png.has_palette_alpha(picture):
                png.palette_alpha(picture, decoded)
            png.colour_key(picture)
        except png.Undecodable:
            pass
