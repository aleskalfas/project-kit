"""Picture files (visual-communication DEC-025 points 2, 5 and 9): a PNG or a JPEG file that
a person puts in the `pictures/` folder of a piece or of a library's version, a brand's
among them, found by its bare name, and read by its encoding.

- **A bare name** (`is_bare_name`): lower-case letters, digits and hyphens, from a letter,
  then `.png`, `.jpg` or `.jpeg`. It holds no `/`, so it cannot leave its folder.
- **Found as version control lists the folder** (`Folder.listing`): by its exact name among
  the files git lists there, tracked or untracked but not ignored, never by asking the file
  system. So `logo.png` never finds `Logo.png`, and a file git ignores is no picture. A link
  is no picture, and neither is a file git hands to a large-file store, nor a store's
  pointer in a picture's place: the engine reads no store.
- **Read by its encoding** (`read`): its first bytes say whether it is a PNG or a JPEG, and
  its extension must say the same. The encodings read are a PNG of 8 bits or fewer for each
  sample, of any colour type, and a JPEG of 8 bits, in grey or in colour, baseline or
  progressive. A PNG of 16 bits, an interlaced or an animated one, a JPEG in CMYK, one an
  orientation tag turns, and every other encoding, are refused, each with its fix. A
  picture gives its kind, its size in pixels, and the ICC profile it carries, whole, which
  each renderer passes on with it.
- **Judged where it lies** (`Folder.judge`, `Folder.read`): each finding fails, and lies in
  the piece for a piece's picture, or in the version for a library's or a brand's, so it
  asks for attention where that version is released (`findings.as_read`). A final piece's
  pictures take no finding (DEC-002 point 7).

Every byte is untrusted: each length read is bound by the file's size, a profile's by
`PROFILE_BOUND`, and a file truncated or malformed is refused, never a crash. Only what
says how to draw the picture is read; its pixels are a renderer's to decode.
"""

from __future__ import annotations

import os
import re
import stat
import struct
import zlib
from collections.abc import Sequence
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import TypeGuard

from _lib import location
from _lib.findings import FAILS, Finding

#: The folder of a piece or of a library's version that holds its picture files.
FOLDER = "pictures"

#: The kinds of picture file, each the word its finding and a renderer read.
PNG = "png"
JPEG = "jpeg"

#: What each extension says a file's bytes are.
EXTENSIONS = {"png": PNG, "jpg": JPEG, "jpeg": JPEG}

#: A picture file's bare name, in words, for a finding's message.
BARE_NAME = "lower-case letters, digits and hyphens, from a letter, then `.png`, `.jpg` or `.jpeg`"

#: The largest ICC profile read, in bytes: far above what a screen's profile needs, and a
#: bound on what a compressed one may grow to.
PROFILE_BOUND = 16 * 2**20

_PROFILE_TOO_LARGE = (
    f"its colour profile is larger than {PROFILE_BOUND // 2**20} MiB, which no picture's "
    f"profile needs"
)

#: The labels of a picture file's findings (DEC-025 point 9).
NAME = "picture-name"
MISSING = "picture-missing"
LINK = "picture-link"
UNREADABLE = "picture-unreadable"
STORED = "picture-stored"
ENCODING = "picture-encoding"
EXTENSION = "picture-extension"

#: The label of a folder git cannot list, the location's or a `pictures/` folder's.
UNLISTED = "files-unlisted"

_BARE_NAME = re.compile(r"^[a-z][a-z0-9-]*\.(png|jpg|jpeg)$")

#: What each refused encoding is fixed by (DEC-025 point 5).
_SAVE_AT_8_BITS = "save it at 8 bits for each sample, not interlaced"
_SAVE_FIRST_FRAME = "save its first frame as a still PNG"
_SAVE_IN_RGB = "save it in RGB"
_SAVE_UPRIGHT = "save it upright, with no orientation tag that turns it"
_SAVE_AS_READ = "save it as a PNG or a JPEG of 8 bits"
_SAVE_PROFILE = "save it with a colour profile for its own colours, or with none"
_SAVE_AGAIN = "save it again as a PNG or a JPEG of 8 bits"

#: The first bytes of each kind.
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_JPEG_SIGNATURE = b"\xff\xd8\xff"

#: The first bytes of a large-file store's pointer, in each form its specification took.
_POINTERS = (
    b"version https://git-lfs.github.com/spec/",
    b"version https://hawser.github.com/spec/",
)

#: The bit depths each colour type of a PNG may take (PNG, "11.2.2 IHDR").
_PNG_DEPTHS = {0: (1, 2, 4, 8, 16), 2: (8, 16), 3: (1, 2, 4, 8), 4: (8, 16), 6: (8, 16)}

#: The PNG colour types whose samples are grey.
_PNG_GREY = (0, 4)

#: The chunks a PNG of the encodings read must know, every other chunk whose name starts
#: with a capital letter being one no reader may skip.
_PNG_CRITICAL = (b"IHDR", b"PLTE", b"IDAT", b"IEND")

#: The largest length a PNG chunk may give (PNG, "5.3 Chunk layout").
_PNG_LENGTH_BOUND = 2**31 - 1

#: A JPEG's frame markers, each with the coding it names (ITU T.81, Table B.1).
_JPEG_FRAMES = {
    0xC0: "baseline",
    0xC1: "extended sequential",
    0xC2: "progressive",
    0xC3: "lossless",
    0xC5: "differential sequential",
    0xC6: "differential progressive",
    0xC7: "differential lossless",
    0xC9: "extended sequential, arithmetic",
    0xCA: "progressive, arithmetic",
    0xCB: "lossless, arithmetic",
    0xCD: "differential sequential, arithmetic",
    0xCE: "differential progressive, arithmetic",
    0xCF: "differential lossless, arithmetic",
}

#: The frame markers whose coding is read, and the extended one, which a JPEG of 12 bits
#: takes in place of the baseline.
_JPEG_READ = (0xC0, 0xC2)
_EXTENDED = 0xC1

#: The markers that stand alone, with no length: the start of the image, the end, the
#: temporary marker and the restart markers.
_JPEG_ALONE = (0xD8, 0xD9, 0x01, *range(0xD0, 0xD8))

#: The bytes that may come before a JPEG's marker, its own `0xFF` among them.
_FILL = re.compile(rb"\xff+")

#: The marker that starts a scan, after which the coded data runs to the end of the image.
_SOS = 0xDA
_EOI = b"\xff\xd9"

#: The Exif orientation tag, and the values that turn or mirror a picture.
_ORIENTATION = 0x0112
_TURNED = range(2, 9)

#: The header of each segment of a JPEG's ICC profile (ICC.1, Annex B.4).
_ICC_HEADER = b"ICC_PROFILE\0"


def is_bare_name(name: object) -> TypeGuard[str]:
    """Whether `name` is a picture file's bare name (DEC-025 point 2)."""
    return isinstance(name, str) and _BARE_NAME.match(name) is not None


# --- reading a picture's bytes ------------------------------------------------------------------


@dataclass(frozen=True)
class Picture:
    """A picture file read: its kind, `PNG` or `JPEG`; its size in pixels, as stored; and
    the ICC profile it carries, whole, or None where it carries none. Each renderer is
    handed these, and the file's bytes, to draw it."""

    kind: str
    width: int
    height: int
    profile: bytes | None = None


class Refused(Exception):
    """A picture file the capability does not read: its finding's label, what is wrong in
    words, and the fix."""

    def __init__(self, code: str, message: str, fix: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.fix = fix


def kind_named(name: str) -> str:
    """The kind of picture file a bare name's extension says. Raises ValueError for a name
    whose extension is none of a picture file's."""
    extension = name.rpartition(".")[2]
    if extension not in EXTENSIONS:
        raise ValueError(f"`{name}` names no picture file's extension")
    return EXTENSIONS[extension]


def kind_of(data: bytes) -> str | None:
    """The kind of picture file the first bytes of `data` say it is, or None."""
    if data.startswith(_PNG_SIGNATURE):
        return PNG
    if data.startswith(_JPEG_SIGNATURE):
        return JPEG
    return None


def is_pointer(data: bytes) -> bool:
    """Whether `data` is a large-file store's pointer, which a store keeps in a file's place."""
    return data.startswith(_POINTERS)


def read(data: bytes, name: str) -> Picture:
    """The picture file `name` whose bytes are `data`, read by its encoding (DEC-025 point
    5). Raises Refused for bytes that are not what its extension says, an encoding the
    capability does not read, and a file that cannot be read."""
    said = kind_named(name)
    kind = kind_of(data)
    if kind is None:
        raise Refused(
            EXTENSION,
            f"`{name}` is neither a PNG nor a JPEG, by its first bytes",
            _SAVE_AS_READ,
        )
    if kind != said:
        stem = name.rpartition(".")[0]
        right = f"{stem}.png" if kind == PNG else f"{stem}.jpg"
        raise Refused(
            EXTENSION,
            f"`{name}` is a {_KIND_SAID[kind]} by its bytes, and its extension says a "
            f"{_KIND_SAID[said]}",
            f"rename it `{right}`, and name it so, or save it as a {_KIND_SAID[said]}",
        )
    return _png(data, name) if kind == PNG else _jpeg(data, name)


_KIND_SAID = {PNG: "PNG", JPEG: "JPEG"}


def _unreadable(name: str, why: str) -> Refused:
    return Refused(UNREADABLE, f"`{name}` cannot be read: {why}", _SAVE_AGAIN)


def _refused(name: str, faults: Sequence[tuple[str, str]]) -> Refused:
    """The encodings `name` is stored in that the capability does not read, each with its
    fix, as one finding."""
    what = " and ".join(fault for fault, _ in faults)
    fixes = list(dict.fromkeys(fix for _, fix in faults))
    return Refused(
        ENCODING,
        f"`{name}` is {what}, which the capability does not read",
        "; ".join(fixes),
    )


def _png(data: bytes, name: str) -> Picture:
    """A PNG's header and the chunks that say how to draw it, each chunk bound by the
    file's size and its checksum checked; its image data is not decoded."""
    size = len(data)
    view = memoryview(data)
    at = len(_PNG_SIGNATURE)
    header: tuple[int, int, int, int, int] | None = None
    colour = -1
    profile: bytes | None = None
    palette = animated = image = ended = False
    while at < size:
        if size - at < 12:
            raise _unreadable(name, "it ends inside a chunk")
        length, kind = struct.unpack_from(">I4s", data, at)
        if length > _PNG_LENGTH_BOUND or length > size - at - 12:
            raise _unreadable(name, "a chunk runs past the end of the file")
        if not kind.isalpha():
            raise _unreadable(name, "a chunk's name is not four letters")
        body = view[at + 8 : at + 8 + length]
        (checksum,) = struct.unpack_from(">I", data, at + 8 + length)
        if zlib.crc32(body, zlib.crc32(kind)) != checksum:
            raise _unreadable(name, f"its chunk `{kind.decode('ascii')}` is damaged")
        at += 12 + length
        if header is None:
            if kind != b"IHDR" or length != 13:
                raise _unreadable(name, "it does not start with its header, `IHDR`")
            header = _png_header(bytes(body), name)
            colour = header[3]
            continue
        if kind == b"IEND":
            ended = True
            break
        if kind == b"IHDR":
            raise _unreadable(name, "it holds a second header, `IHDR`")
        if kind == b"PLTE":
            if colour in _PNG_GREY or image or palette:
                raise _unreadable(name, "its palette, `PLTE`, is out of place")
            if length == 0 or length % 3 or length > 3 * 256:
                raise _unreadable(name, "its palette, `PLTE`, is not of whole colours")
            palette = True
        elif kind == b"IDAT":
            image = True
        elif kind == b"acTL" and not image:
            animated = True
        elif kind == b"iCCP" and not image and profile is None:
            profile = _png_profile(bytes(body), name)
        elif kind[0:1].isupper() and kind not in _PNG_CRITICAL:
            raise _refused(
                name, [(f"a PNG with the chunk `{kind.decode('ascii')}`", _SAVE_AS_READ)]
            )
    if header is None or not ended:
        raise _unreadable(name, "it ends before its last chunk, `IEND`")
    width, height, depth, _, interlace = header
    if not image:
        raise _unreadable(name, "it holds no image data, `IDAT`")
    if colour == 3 and not palette:
        raise _unreadable(name, "it names colours from a palette, and holds none")
    faults = []
    if depth == 16:
        faults.append(("a PNG of 16 bits for each sample", _SAVE_AT_8_BITS))
    if interlace:
        faults.append(("an interlaced PNG", _SAVE_AT_8_BITS))
    if animated:
        faults.append(("an animated PNG", _SAVE_FIRST_FRAME))
    if faults:
        raise _refused(name, faults)
    if profile is not None:
        _check_profile(profile, name, grey=colour in _PNG_GREY)
    return Picture(PNG, width, height, profile)


def _png_header(body: bytes, name: str) -> tuple[int, int, int, int, int]:
    """A PNG's width, height, bit depth, colour type and interlace method, from its `IHDR`."""
    width, height, depth, colour, compression, filtering, interlace = struct.unpack(
        ">IIBBBBB", body
    )
    if not 0 < width <= _PNG_LENGTH_BOUND or not 0 < height <= _PNG_LENGTH_BOUND:
        raise _unreadable(name, f"its header gives a size of {width} × {height} pixels")
    if colour not in _PNG_DEPTHS or depth not in _PNG_DEPTHS[colour]:
        raise _unreadable(name, f"its header gives {depth} bits to the colour type {colour}")
    if compression or filtering or interlace not in (0, 1):
        raise _unreadable(name, "its header names a method no PNG defines")
    return width, height, depth, colour, interlace


def _png_profile(body: bytes, name: str) -> bytes:
    """The ICC profile a PNG's `iCCP` chunk holds: a name of 1 to 79 bytes, its end, the
    method 0, then the profile, compressed, inflated no further than `PROFILE_BOUND`."""
    end = body.find(b"\0", 0, 80)
    if end < 1 or len(body) < end + 2 or body[end + 1] != 0:
        raise _unreadable(name, "its colour profile, `iCCP`, is not of its shape")
    inflater = zlib.decompressobj()
    try:
        profile = inflater.decompress(body[end + 2 :], PROFILE_BOUND + 1)
    except zlib.error:
        raise _unreadable(name, "its colour profile, `iCCP`, is damaged") from None
    if len(profile) > PROFILE_BOUND or inflater.unconsumed_tail:
        raise _unreadable(name, _PROFILE_TOO_LARGE)
    if not inflater.eof:
        raise _unreadable(name, "its colour profile, `iCCP`, ends too early")
    return profile


def _jpeg(data: bytes, name: str) -> Picture:
    """A JPEG's frame and the segments before its first scan that say how to draw it, each
    bound by the file's size; its coded data is not decoded, but must reach the end of the
    image."""
    size = len(data)
    at = 2
    frame: tuple[int, bytes] | None = None
    exif: bytes | None = None
    icc: list[bytes] = []
    while True:
        if at >= size or data[at] != 0xFF:
            raise _unreadable(name, "it ends, or holds bytes out of place, before its first scan")
        at = _FILL.match(data, at).end()  # a marker may follow fill bytes
        if at >= size:
            raise _unreadable(name, "it ends before its first scan")
        marker = data[at]
        at += 1
        if marker in _JPEG_ALONE or marker == 0x00:
            raise _unreadable(name, "a marker is out of place before its first scan")
        if size - at < 2:
            raise _unreadable(name, "it ends inside a segment")
        (length,) = struct.unpack_from(">H", data, at)
        if length < 2 or length > size - at:
            raise _unreadable(name, "a segment runs past the end of the file")
        body = data[at + 2 : at + length]
        at += length
        if marker == _SOS:
            break
        if marker in _JPEG_FRAMES:
            if frame is not None:
                raise _refused(name, [("a JPEG of more than one frame", _SAVE_AS_READ)])
            frame = (marker, body)
        elif marker == 0xE1 and exif is None and body.startswith(b"Exif\0\0"):
            exif = body[6:]
        elif marker == 0xE2 and body.startswith(_ICC_HEADER):
            icc.append(body[len(_ICC_HEADER) :])
    if frame is None:
        raise _unreadable(name, "its first scan comes before its frame")
    if data.find(_EOI, at) < 0:
        raise _unreadable(name, "it ends before the end of its image")
    coding, header = frame
    if len(header) < 6:
        raise _unreadable(name, "its frame is shorter than its header")
    precision, height, width, components = struct.unpack_from(">BHHB", header)
    if len(header) != 6 + 3 * components or components == 0:
        raise _unreadable(name, "its frame's length does not fit its colour components")
    if width == 0 or height == 0:
        raise _unreadable(name, f"its frame gives a size of {width} × {height} pixels")
    faults = []
    if precision != 8:
        faults.append((f"a JPEG of {precision} bits", _SAVE_AS_READ))
    # A JPEG of 12 bits is coded as extended sequential, or progressive, for its bits alone.
    if coding not in _JPEG_READ and not (precision != 8 and coding == _EXTENDED):
        faults.append((f"a JPEG in {_JPEG_FRAMES[coding]} coding", _SAVE_AS_READ))
    if components == 4:
        faults.append(("a JPEG in CMYK", _SAVE_IN_RGB))
    elif components not in (1, 3):
        faults.append((f"a JPEG of {components} colour components", _SAVE_AS_READ))
    if exif is not None and _orientation(exif) in _TURNED:
        faults.append(("a JPEG whose orientation tag turns it", _SAVE_UPRIGHT))
    if faults:
        raise _refused(name, faults)
    profile = _jpeg_profile(icc, name) if icc else None
    if profile is not None:
        _check_profile(profile, name, grey=components == 1)
    return Picture(JPEG, width, height, profile)


def _orientation(tiff: bytes) -> int | None:
    """The orientation an Exif segment's first directory gives, as a browser reads it: a
    tag of one short value; None where it gives none, or cannot be read. A tag that cannot
    be read turns the picture nowhere, so the picture draws alike in every output."""
    if len(tiff) < 8 or tiff[:2] not in (b"II", b"MM"):
        return None
    order = "<" if tiff[:2] == b"II" else ">"
    magic, first = struct.unpack_from(f"{order}HI", tiff, 2)
    if magic != 42 or first < 8 or first > len(tiff) - 2:
        return None
    (count,) = struct.unpack_from(f"{order}H", tiff, first)
    if count > (len(tiff) - first - 2) // 12:
        return None
    for entry in range(first + 2, first + 2 + 12 * count, 12):
        tag, kind, values = struct.unpack_from(f"{order}HHI", tiff, entry)
        if tag == _ORIENTATION:
            if kind != 3 or values != 1:
                return None
            return struct.unpack_from(f"{order}H", tiff, entry + 8)[0]
    return None


def _jpeg_profile(parts: Sequence[bytes], name: str) -> bytes:
    """The ICC profile a JPEG's segments hold, joined in the order each numbers itself: each
    names its place and their count, and every place from 1 to the count is given once."""
    numbered: dict[int, bytes] = {}
    counts: set[int] = set()
    for part in parts:
        if len(part) < 2:
            raise _unreadable(name, "a segment of its colour profile is not of its shape")
        place, count = part[0], part[1]
        if place in numbered:
            raise _unreadable(name, "its colour profile gives one segment twice")
        numbered[place] = part[2:]
        counts.add(count)
    if len(counts) != 1 or set(numbered) != set(range(1, min(counts) + 1)):
        raise _unreadable(name, "the segments of its colour profile do not fit together")
    profile = b"".join(numbered[place] for place in sorted(numbered))
    if len(profile) > PROFILE_BOUND:
        raise _unreadable(name, _PROFILE_TOO_LARGE)
    return profile


def _check_profile(profile: bytes, name: str, *, grey: bool) -> None:
    """A colour profile is an ICC profile, whole, for the picture's colours: grey for a grey
    picture, RGB for a colour one, as each output draws a picture by it (DEC-025 point 5)."""
    if len(profile) < 128 or profile[36:40] != b"acsp":
        raise _unreadable(name, "its colour profile is no ICC profile")
    (declared,) = struct.unpack_from(">I", profile)
    if declared != len(profile):
        raise _unreadable(name, "its colour profile is not whole")
    space = profile[16:20]
    if space != (b"GRAY" if grey else b"RGB "):
        said = space.decode("latin-1").strip() or "no"
        colours = "grey" if grey else "RGB"
        raise _refused(
            name,
            [(f"a picture in {colours} with a colour profile for {said} colours", _SAVE_PROFILE)],
        )


# --- a folder of picture files ------------------------------------------------------------------


@dataclass(frozen=True)
class Listing:
    """The files of a `pictures/` folder as version control lists them, by their bare
    names: each plain file, each link, and each file git hands to a large-file store."""

    files: frozenset[str] = frozenset()
    links: frozenset[str] = frozenset()
    stored: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Judged:
    """A picture file judged: the picture read, or None where it cannot be read; and the
    findings on it."""

    picture: Picture | None
    findings: tuple[Finding, ...] = ()


@dataclass
class Folder:
    """The `pictures/` folder of a piece or of a library's version, `holder`, and where its
    findings lie (DEC-025 point 9).

    - `shown`: how findings name the holder's folder, relative to the project root and
      ending in `/`, or "".
    - `said`: the holder in words, as a message names it: "the piece", "the brand's
      version".
    - `library`: `<name>@<version>` for a library's version, whose findings lie in it, so
      they ask for attention where it is released; "" for a piece.
    - `final`: a final piece, whose pictures are read but take no finding (DEC-002 point 7).
    - `walked`: its files listed as they lie, for a holder a command built in the clone's
      local folder, which git ignores (`before_after`), so there git would list none.

    Its files are listed once, the first time a name is judged, as version control lists
    them (`location.listed`), or as they lie where `walked`; each name is read once."""

    holder: Path
    shown: str
    said: str
    library: str = ""
    final: bool = False
    walked: bool = False
    _read: dict[str, Judged] = field(default_factory=dict, init=False, repr=False)

    @cached_property
    def listing(self) -> Listing:
        """The folder's files, by their bare names. Raises location.GitFailed."""
        prefix = f"{FOLDER}/"
        found = (
            location.walked(self.holder, FOLDER, links=True)
            if self.walked
            else location.listed(self.holder, FOLDER)
        )
        entries = [rel for rel in found if rel.startswith(prefix) and "/" not in rel[len(prefix) :]]
        links = {rel for rel in entries if (self.holder / rel).is_symlink()}
        stored = location.in_store(self.holder, [rel for rel in entries if rel not in links])
        return Listing(
            files=frozenset(rel[len(prefix) :] for rel in entries if rel not in links),
            links=frozenset(rel[len(prefix) :] for rel in links),
            stored=frozenset(rel[len(prefix) :] for rel in stored),
        )

    def judge(self, name: object, *, named: str, file: str, where: str) -> Judged:
        """The picture file `name` names, which `named` gives in words, as "the picture role
        `picture.logo`", at `where` in `file`: its name of a bare name's shape, found by its
        exact name among the folder's listed files, no link, then read (`read`). A finding
        on the name lies at `file#where`; one on the file, at the file."""
        if not is_bare_name(name):
            return self._judged(
                None,
                Finding(
                    NAME,
                    FAILS,
                    f"{named} names `{name}`, which is no picture file's bare name: {BARE_NAME}",
                    file=file,
                    where=where,
                    fix=f"name a file of `{FOLDER}/` by its bare name",
                    library=self.library,
                ),
            )
        try:
            listing = self.listing
        except location.GitFailed as exc:
            return self._judged(None, self._unlisted(exc))
        if name in listing.links:
            return self._judged(
                None,
                Finding(
                    LINK,
                    FAILS,
                    f"{named} names `{name}`, which is a symbolic link: one may lead out of "
                    f"the folder, or to a file another clone lacks",
                    file=self._path(name),
                    fix=f"put the picture file itself at `{FOLDER}/{name}`, in the link's place",
                    library=self.library,
                ),
            )
        if name not in listing.files:
            return self._judged(
                None,
                Finding(
                    MISSING,
                    FAILS,
                    f"{named} names `{name}`, which {self.said} does not hold in "
                    f"`{FOLDER}/`{self._why_missing(name, listing)}",
                    file=file,
                    where=where,
                    fix=f"add `{FOLDER}/{name}` to {self.said}, or name a file it holds there",
                    library=self.library,
                ),
            )
        return self.read(name)

    def read(self, name: str) -> Judged:
        """The file `name` the folder lists, read by its bytes: no file a large-file store
        keeps, nor its pointer, and of an encoding read (`read`)."""
        if name not in self._read:
            self._read[name] = self._read_file(name)
        found = self._read[name]
        return Judged(found.picture) if self.final else found

    def _read_file(self, name: str) -> Judged:
        try:
            stored = name in self.listing.stored
        except location.GitFailed as exc:
            return Judged(None, (self._unlisted(exc),))
        out_of_store = f"commit the picture's own bytes: take `{FOLDER}/{name}` out of the store"
        if stored:
            return self._on_file(
                name,
                STORED,
                f"git hands `{name}` to a large-file store, which commits a pointer in its "
                f"place, so its bytes are not committed, and the engine reads no store",
                fix=out_of_store,
            )
        try:
            data = _bytes(self.holder / FOLDER / name)
        except OSError as exc:
            return self._on_file(
                name,
                UNREADABLE,
                f"`{name}` cannot be read: {exc.strerror or exc}",
                fix="make it a file the check can read, or save it again",
            )
        if is_pointer(data):
            return self._on_file(
                name,
                STORED,
                f"`{name}` holds a large-file store's pointer in the picture's place, so its "
                f"bytes are not committed, and the engine reads no store",
                fix=out_of_store,
            )
        try:
            return Judged(read(data, name))
        except Refused as refused:
            return self._on_file(name, refused.code, refused.message, fix=refused.fix)

    def _on_file(self, name: str, code: str, message: str, *, fix: str = _SAVE_AGAIN) -> Judged:
        return Judged(
            None,
            (Finding(code, FAILS, message, file=self._path(name), fix=fix, library=self.library),),
        )

    def _unlisted(self, exc: location.GitFailed) -> Finding:
        return Finding(
            UNLISTED,
            FAILS,
            f"git cannot list the files of `{FOLDER}/`: {exc}",
            file=self._path(""),
            library=self.library,
        )

    def _judged(self, picture: Picture | None, finding: Finding) -> Judged:
        return Judged(picture) if self.final else Judged(picture, (finding,))

    def _path(self, name: str) -> str:
        return f"{self.shown}{FOLDER}/{name}"

    def _why_missing(self, name: str, listing: Listing) -> str:
        """Why a name the folder does not list finds nothing, where a file comes near: one
        whose name differs only in case, or one that lies there and git ignores."""
        alike = sorted(held for held in listing.files | listing.links if held.lower() == name)
        if alike:
            return f": it holds `{alike[0]}`, and a name finds a file by its exact case"
        folder = self.holder / FOLDER
        try:
            lies = folder.is_dir() and name in os.listdir(folder)
            ignored = lies and bool(location.ignored(self.holder, [f"{FOLDER}/{name}"]))
        except (OSError, location.GitFailed):
            return ""
        if ignored:
            return ": the file lies there, and git ignores it, so no clone holds it"
        return ""


def _bytes(path: Path) -> bytes:
    """The bytes of the plain file at `path`, never through a link: a link put in a listed
    file's place after it was listed is refused, as the listing refuses one."""
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    with os.fdopen(descriptor, "rb") as opened:
        if not stat.S_ISREG(os.fstat(opened.fileno()).st_mode):
            raise OSError(0, "it is no plain file")
        return opened.read()
