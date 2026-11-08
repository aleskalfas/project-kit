"""A brand of the capability's tests that gives its logo, the picture role `picture.logo`
(visual-communication DEC-025 point 4; #2858).

**The brand** `test-logo` is the test brand copied into a project's library folder under a
name of its own (`logo_brand`), so the tests that share the test brand never see a logo. It
gives `picture.logo` a light logo in every combination, and a dark one in the dark colour
scheme, which holds twice the pixels at the same proportion. A test may leave either out,
or give a phone its own logo on the size axis `device`, which the foundations being built
declare.

**The logos** are PNGs drawn here with the standard library alone (zlib and struct), so no
binary fixture is kept: a mark, a ring round a dot, beside two bars of a word mark, each
pixel's cover sampled four times so its edges are smooth. The light logo is ink on a clear
ground, for a light page; the dark logo is a light ink, for a dark page. The phone's logo is
the mark alone, square.
"""

from __future__ import annotations

import functools
import json
import shutil
import struct
import zlib
from collections.abc import Callable
from pathlib import Path
from typing import Any

from tests.visual_communication_project import TEST_BRAND, version_folder

#: The brand's name, and its version.
NAME = "test-logo"
VERSION = "1.0.0"

#: Each logo's bare name in the brand's `pictures/`.
LIGHT = "logo.png"
DARK = "logo-dark.png"
PHONE = "logo-phone.png"

#: The light logo's pixels; the dark one holds twice as many each way.
WIDTH, HEIGHT = 160, 48

#: The inks, 8-bit RGB: the word mark's and the mark's, on a light page and on a dark one.
LIGHT_INK = ((31, 35, 40), (9, 105, 218))
DARK_INK = ((240, 246, 252), (88, 166, 255))

#: The token file of the dark colour scheme, and the one a phone's logo lies in.
BASE_FILE = "tokens/base.tokens.json"
DARK_FILE = "tokens/dark.tokens.json"
PHONE_FILE = "tokens/phone.tokens.json"

_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def png(width: int, height: int, cover: Callable[[float, float], tuple[int, ...] | None]) -> bytes:
    """A PNG of 8-bit RGBA, `width` × `height` pixels: each pixel's colour the one `cover`
    gives at the most points of four within it, by `x` and `y` from 0 to 1 across the
    picture, its alpha the share of them it covers; clear where it covers none."""
    rows = bytearray()
    for row in range(height):
        rows.append(0)
        for column in range(width):
            found = [
                cover((column + dx) / width, (row + dy) / height)
                for dx in (0.25, 0.75)
                for dy in (0.25, 0.75)
            ]
            inked = [colour for colour in found if colour is not None]
            if not inked:
                rows.extend((0, 0, 0, 0))
                continue
            colour = max(set(inked), key=inked.count)
            rows.extend((*colour, round(255 * len(inked) / len(found))))
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        _SIGNATURE
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", zlib.compress(bytes(rows), 9))
        + _chunk(b"IEND", b"")
    )


def _mark(x: float, y: float, cx: float, cy: float, unit: float) -> bool:
    """Whether the point lies on the mark, a ring round a dot, centred at `cx cy`, its
    outer radius `unit`."""
    distance = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
    return distance <= 0.3 * unit or 0.62 * unit <= distance <= unit


def _bar(x: float, y: float, left: float, right: float, top: float, bottom: float) -> bool:
    """Whether the point lies on a bar with round ends, from `left` to `right`."""
    if not top <= y <= bottom:
        return False
    radius, middle = (bottom - top) / 2, (top + bottom) / 2
    for end in (left + radius, right - radius):
        if (x - end) ** 2 + (y - middle) ** 2 <= radius**2:
            return True
    return left + radius <= x <= right - radius


@functools.cache
def logo(scale: int = 1, dark: bool = False) -> bytes:
    """The brand's logo, `scale` times the light logo's pixels each way: the mark, and the
    word mark's two bars beside it, in the light inks or the dark ones."""
    word, accent = DARK_INK if dark else LIGHT_INK

    def cover(u: float, v: float) -> tuple[int, ...] | None:
        x, y = u * WIDTH, v * HEIGHT  # in the light logo's pixels
        if _mark(x, y, 24, 24, 18):
            return accent
        if _bar(x, y, 52, 148, 12, 22) or _bar(x, y, 52, 116, 28, 36):
            return word
        return None

    return png(WIDTH * scale, HEIGHT * scale, cover)


@functools.cache
def mark(size: int = HEIGHT, dark: bool = False) -> bytes:
    """The mark alone, `size` pixels square: the phone's logo."""
    accent = (DARK_INK if dark else LIGHT_INK)[1]

    def cover(u: float, v: float) -> tuple[int, ...] | None:
        return accent if _mark(u * 48, v * 48, 24, 24, 20) else None

    return png(size, size, cover)


def picture(name: str) -> dict[str, Any]:
    """A picture role's value: an empty group that names its file (DEC-025 point 4)."""
    return {"$extensions": {"pkit.visual-communication": {"file": name}}}


def giving(folder: Path, file: str, name: str | None) -> None:
    """The token file `file` of the brand at `folder` giving `picture.logo` the file `name`,
    or giving it none where `name` is None."""
    path = folder / file
    data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    group = data.setdefault("picture", {})
    if name is None:
        group.pop("logo", None)
        if not group:
            data.pop("picture")
    else:
        group["logo"] = picture(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def hold(folder: Path, name: str, data: bytes) -> Path:
    """`data` held as `name` in the `pictures/` of the version at `folder`."""
    path = folder / "pictures" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def logo_brand(
    root: Path,
    *,
    light: bool = True,
    dark: bool = True,
    version: str = VERSION,
    location: str = "visual",
) -> Path:
    """The brand `test-logo` at `version`, by default 1.0.0, in the location at `root`: the
    test brand under that name, giving `picture.logo` the light logo in every combination
    where `light`, and the dark logo, twice its pixels, in the dark colour scheme where
    `dark`."""
    folder = version_folder(root, NAME, version, location)
    shutil.copytree(TEST_BRAND, folder, ignore=shutil.ignore_patterns("__pycache__"))
    library = folder / "library.yaml"
    text = library.read_text(encoding="utf-8").replace("name: test-brand", f"name: {NAME}", 1)
    library.write_text(text.replace("version: 1.0.0", f"version: {version}", 1), encoding="utf-8")
    resolver = folder / "test-brand.resolver.json"
    data = json.loads(resolver.read_text(encoding="utf-8"))
    resolver.write_text(json.dumps({**data, "name": NAME}, indent=2), encoding="utf-8")
    if light:
        giving(folder, BASE_FILE, LIGHT)
        hold(folder, LIGHT, logo())
    if dark:
        giving(folder, DARK_FILE, DARK)
        hold(folder, DARK, logo(2, dark=True))
    return folder


def give_phone(folder: Path, name: str = PHONE) -> None:
    """The brand at `folder` giving a phone its own logo, the mark alone, from the token
    file of the size axis `device`'s mode `phone`, which its Resolver document already
    applies (`tests.test_visual_communication_logos.add_device`)."""
    giving(folder, PHONE_FILE, name)
    hold(folder, name, mark())
