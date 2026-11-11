"""Picture files (visual-communication DEC-025 points 2, 5 and 9), read and judged on files
directly, with no part that names them: the encodings read, with each file's kind, size and
colour profile; each encoding refused, with its fix; bytes that are not what an extension
says; a file truncated or damaged, refused and never a crash; a bare name found as version
control lists its folder; a link and a large-file store refused; and where each finding
lies, in a piece, in a library's version, or nowhere in a final piece. A brand's version
read in full reports its logo once, though its brand and the full read both read it.

The test pictures (`TEST_PICTURES`) are 4 × 3 pixels, each named for what it is. Two carry
an RGB profile the tests made, `profile.png` in its `iCCP` chunk and `profile.jpg` in one ICC
segment. The variants a test needs, such as a profile split over segments or a file cut
short, it builds from them.
"""

from __future__ import annotations

import json
import os
import random
import shutil
import struct
import subprocess
import zlib
from pathlib import Path
from typing import Any

import pytest

from tests.in_process import load
from tests.visual_communication_project import (
    RELEASED_FOUNDATIONS,
    TEST_BRAND,
    TEST_PICTURES,
    copy_library,
    project,
)

pictures, findings, full_read, libraries = load(
    "visual-communication", "pictures", "findings", "full_read", "libraries"
)

#: Each picture the capability reads: its kind, and whether it carries a colour profile.
READ = {
    "palette.png": ("png", False),
    "grey.png": ("png", False),
    "alpha.png": ("png", False),
    "profile.png": ("png", True),
    "grey.jpg": ("jpeg", False),
    "colour.jpg": ("jpeg", False),
    "progressive.jpg": ("jpeg", False),
    "profile.jpg": ("jpeg", True),
}

#: Each picture the capability refuses: its label, what the message says it is, and the fix
#: `files.md` names under "The encodings read", as DEC-025 point 5 asks.
REFUSED = {
    "deep.png": (
        "picture-encoding",
        "a PNG of 16 bits for each sample",
        "save it at 8 bits for each sample, not interlaced",
    ),
    "interlaced.png": (
        "picture-encoding",
        "an interlaced PNG",
        "save it at 8 bits for each sample, not interlaced",
    ),
    "animated.png": ("picture-encoding", "an animated PNG", "save its first frame as a still PNG"),
    "cmyk.jpg": ("picture-encoding", "a JPEG in CMYK", "save it in RGB"),
    "twelve-bit.jpg": (
        "picture-encoding",
        "a JPEG of 12 bits",
        "save it as a PNG or a JPEG of 8 bits",
    ),
    "turned.jpg": (
        "picture-encoding",
        "a JPEG whose orientation tag turns it",
        "save it upright, with no orientation tag that turns it",
    ),
    "misnamed.png": (
        "picture-extension",
        "a JPEG by its bytes, and its extension says a PNG",
        "rename it `misnamed.jpg`, and name it so, or save it as a PNG",
    ),
}


def data(name: str) -> bytes:
    return (TEST_PICTURES / name).read_bytes()


def refusal(given: bytes, name: str) -> Any:
    """The refusal reading `given` as the picture file `name` raises."""
    with pytest.raises(pictures.Refused) as raised:
        pictures.read(given, name)
    return raised.value


def png_chunks(given: bytes) -> list[tuple[bytes, bytes]]:
    """Each chunk of a PNG, its name and its body."""
    chunks, at = [], 8
    while at < len(given):
        (length,) = struct.unpack_from(">I", given, at)
        chunks.append((given[at + 4 : at + 8], given[at + 8 : at + 8 + length]))
        at += 12 + length
    return chunks


def png_of(chunks: list[tuple[bytes, bytes]]) -> bytes:
    """A PNG of `chunks`, each with its checksum."""
    return b"\x89PNG\r\n\x1a\n" + b"".join(
        struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))
        for kind, body in chunks
    )


def jpeg_segments(given: bytes) -> tuple[list[bytes], bytes]:
    """A JPEG's segments before its first scan, each whole with its marker, and the rest
    from that scan's marker on."""
    segments, at = [], 2
    while given[at + 1] != 0xDA:
        (length,) = struct.unpack_from(">H", given, at + 2)
        segments.append(given[at : at + 2 + length])
        at += 2 + length
    return segments, given[at:]


def jpeg_of(segments: list[bytes], rest: bytes) -> bytes:
    return b"\xff\xd8" + b"".join(segments) + rest


def segment(marker: int, body: bytes) -> bytes:
    return bytes((0xFF, marker)) + struct.pack(">H", len(body) + 2) + body


def profile_of(name: str) -> bytes:
    return pictures.read(data(name), name).profile


# --- the encodings read -------------------------------------------------------------------------


@pytest.mark.parametrize("name", READ)
def test_each_encoding_read_gives_its_kind_and_its_size_in_pixels(name: str) -> None:
    """A PNG of 8 bits or fewer for each sample, a palette with transparency among them,
    and a JPEG of 8 bits, in grey or in colour, baseline or progressive (DEC-025 point 5)."""
    kind, profiled = READ[name]
    picture = pictures.read(data(name), name)
    assert (picture.kind, picture.width, picture.height) == (kind, 4, 3)
    assert (picture.profile is not None) == profiled


def test_a_picture_named_jpeg_reads_as_a_jpeg() -> None:
    assert pictures.read(data("colour.jpg"), "colour.jpeg").kind == pictures.JPEG


def test_a_colour_profile_is_kept_whole_from_a_pngs_chunk_and_a_jpegs_segment() -> None:
    profile = profile_of("profile.png")
    assert profile == profile_of("profile.jpg")
    assert profile[36:40] == b"acsp"
    assert struct.unpack_from(">I", profile)[0] == len(profile)
    assert profile[16:20] == b"RGB "


def test_a_jpegs_profile_split_over_segments_is_joined_in_the_order_they_number() -> None:
    """ICC.1 Annex B: each segment names its place and the count of them."""
    profile = profile_of("profile.jpg")
    segments, rest = jpeg_segments(data("colour.jpg"))
    parts = [profile[:100], profile[100:300], profile[300:]]
    icc = [
        segment(0xE2, b"ICC_PROFILE\0" + bytes((place, 3)) + part)
        for place, part in zip((1, 2, 3), parts, strict=True)
    ]
    joined = jpeg_of([segments[0], icc[2], icc[0], *segments[1:], icc[1]], rest)
    assert pictures.read(joined, "split.jpg").profile == profile


@pytest.mark.parametrize(
    ("places", "said"),
    [
        (((1, 3), (2, 3)), "the segments of its colour profile do not fit together"),
        (((1, 2), (2, 3)), "the segments of its colour profile do not fit together"),
        (((1, 2), (1, 2)), "its colour profile gives one segment twice"),
        (((0, 1),), "the segments of its colour profile do not fit together"),
    ],
)
def test_a_jpegs_profile_whose_segments_do_not_fit_cannot_be_read(
    places: tuple[tuple[int, int], ...], said: str
) -> None:
    segments, rest = jpeg_segments(data("colour.jpg"))
    icc = [segment(0xE2, b"ICC_PROFILE\0" + bytes(place) + b"part") for place in places]
    found = refusal(jpeg_of([*segments, *icc], rest), "split.jpg")
    assert (found.code, found.message) == (
        "picture-unreadable",
        f"`split.jpg` cannot be read: {said}",
    )


def test_a_profile_for_other_colours_than_the_pictures_is_refused() -> None:
    """A grey picture with an RGB profile draws by it in one output and not in another."""
    iccp = next(body for kind, body in png_chunks(data("profile.png")) if kind == b"iCCP")
    grey = png_chunks(data("grey.png"))
    found = refusal(png_of([grey[0], (b"iCCP", iccp), *grey[1:]]), "grey.png")
    assert found.code == "picture-encoding"
    assert "a picture in grey with a colour profile for RGB colours" in found.message
    assert found.fix == "save it with a colour profile for its own colours, or with none"


def test_a_profile_that_is_no_icc_profile_cannot_be_read() -> None:
    body = b"tests\0\0" + zlib.compress(b"not a profile" * 20)
    chunks = png_chunks(data("alpha.png"))
    found = refusal(png_of([chunks[0], (b"iCCP", body), *chunks[1:]]), "alpha.png")
    assert found.message == "`alpha.png` cannot be read: its colour profile is no ICC profile"


def test_a_profile_that_inflates_past_its_bound_is_refused_without_inflating_it_whole() -> None:
    body = b"tests\0\0" + zlib.compress(bytes(pictures.PROFILE_BOUND + 1))
    chunks = png_chunks(data("alpha.png"))
    found = refusal(png_of([chunks[0], (b"iCCP", body), *chunks[1:]]), "alpha.png")
    assert found.code == "picture-unreadable"
    assert "larger than 16 MiB" in found.message


def tiff_of(order: str, orientation: int, kind: int = 3) -> bytes:
    """A TIFF header and a first directory of one entry, the orientation tag."""
    mark = b"II" if order == "<" else b"MM"
    return (
        mark
        + struct.pack(f"{order}HI", 42, 8)
        + struct.pack(f"{order}H", 1)
        + struct.pack(f"{order}HHIHH", 0x0112, kind, 1, orientation, 0)
        + bytes(4)
    )


def with_exif(tiff: bytes) -> bytes:
    segments, rest = jpeg_segments(data("colour.jpg"))
    return jpeg_of([segment(0xE1, b"Exif\0\0" + tiff), *segments], rest)


@pytest.mark.parametrize("order", ["<", ">"])
@pytest.mark.parametrize("orientation", [2, 3, 6, 8])
def test_an_orientation_tag_that_turns_or_mirrors_a_jpeg_is_refused(
    order: str, orientation: int
) -> None:
    assert refusal(with_exif(tiff_of(order, orientation)), "photo.jpg").code == "picture-encoding"


@pytest.mark.parametrize(
    "tiff",
    [
        tiff_of("<", 1),
        tiff_of(">", 0),
        tiff_of("<", 6, kind=4),
        tiff_of("<", 6)[:12],
        b"XX*\0" + bytes(20),
        tiff_of("<", 6).replace(struct.pack("<I", 8), struct.pack("<I", 9000), 1),
    ],
    ids=["upright", "unknown", "other-type", "cut-short", "no-order", "far-directory"],
)
def test_an_orientation_tag_that_turns_nothing_or_cannot_be_read_reads(tiff: bytes) -> None:
    """A browser reads such a tag as turning nothing, so the picture draws alike."""
    assert pictures.read(with_exif(tiff), "photo.jpg").kind == pictures.JPEG


# --- the encodings refused ----------------------------------------------------------------------


@pytest.mark.parametrize("name", REFUSED)
def test_each_encoding_refused_names_itself_and_its_fix(name: str) -> None:
    code, said, fix = REFUSED[name]
    found = refusal(data(name), name)
    assert (found.code, found.fix) == (code, fix)
    assert found.message.startswith(f"`{name}` is {said}")


def test_a_png_refused_for_two_reasons_names_both_in_one_finding() -> None:
    chunks = png_chunks(data("interlaced.png"))
    header = bytearray(chunks[0][1])
    header[8] = 16
    found = refusal(png_of([(b"IHDR", bytes(header)), *chunks[1:]]), "both.png")
    assert found.message == (
        "`both.png` is a PNG of 16 bits for each sample and an interlaced PNG, which the "
        "capability does not read"
    )
    assert found.fix == "save it at 8 bits for each sample, not interlaced"


def test_a_png_named_jpeg_is_refused_with_the_name_its_bytes_call_for() -> None:
    found = refusal(data("alpha.png"), "logo.jpeg")
    assert found.message == "`logo.jpeg` is a PNG by its bytes, and its extension says a JPEG"
    assert found.fix == "rename it `logo.png`, and name it so, or save it as a JPEG"


@pytest.mark.parametrize("given", [b"GIF89a" + bytes(20), b"", b"\x89PN"])
def test_bytes_neither_a_png_nor_a_jpeg_are_refused(given: bytes) -> None:
    found = refusal(given, "logo.png")
    assert (found.code, found.fix) == ("picture-extension", "save it as a PNG or a JPEG of 8 bits")


@pytest.mark.parametrize(
    ("marker", "said"),
    [(0xC1, "extended sequential"), (0xC3, "lossless"), (0xC9, "extended sequential, arithmetic")],
)
def test_every_other_jpeg_coding_is_refused_with_the_rests_fix(marker: int, said: str) -> None:
    segments, rest = jpeg_segments(data("colour.jpg"))
    frame = next(i for i, each in enumerate(segments) if each[1] == 0xC0)
    segments[frame] = bytes((0xFF, marker)) + segments[frame][2:]
    found = refusal(jpeg_of(segments, rest), "photo.jpg")
    assert (
        found.message
        == f"`photo.jpg` is a JPEG in {said} coding, which the capability does not read"
    )
    assert found.fix == "save it as a PNG or a JPEG of 8 bits"


def test_a_png_with_a_chunk_no_reader_may_skip_is_refused() -> None:
    chunks = png_chunks(data("alpha.png"))
    found = refusal(png_of([chunks[0], (b"CgBI", b"\0" * 4), *chunks[1:]]), "alpha.png")
    assert found.code == "picture-encoding"
    assert "the chunk `CgBI`" in found.message


# --- a file truncated or damaged ----------------------------------------------------------------


@pytest.mark.parametrize("name", [*READ, *REFUSED])
def test_every_file_cut_short_is_refused(name: str) -> None:
    whole = data(name)
    for end in range(len(whole)):
        with pytest.raises(pictures.Refused):
            pictures.read(whole[:end], name)


@pytest.mark.parametrize("name", [*READ, *REFUSED])
def test_damaged_bytes_are_read_or_refused_and_never_crash(name: str) -> None:
    """Bytes changed at random, with a seed of their own, so a failure repeats."""
    whole = data(name)
    chance = random.Random(f"{name}-2855")
    for _ in range(400):
        changed = bytearray(whole)
        for _ in range(chance.randint(1, 4)):
            changed[chance.randrange(len(changed))] = chance.randrange(256)
        try:
            pictures.read(bytes(changed), name)
        except pictures.Refused as refused:
            assert refused.code in ("picture-unreadable", "picture-encoding", "picture-extension")


def test_a_damaged_png_chunk_fails_its_checksum() -> None:
    damaged = bytearray(data("alpha.png"))
    damaged[-20] ^= 0xFF  # within the image data, before `IEND`
    found = refusal(bytes(damaged), "alpha.png")
    assert found.message == "`alpha.png` cannot be read: its chunk `IDAT` is damaged"
    assert found.fix == "save it again as a PNG or a JPEG of 8 bits"


@pytest.mark.parametrize(
    ("change", "said"),
    [
        (lambda c: [c[0], (b"IEND", b"")], "it holds no image data, `IDAT`"),
        (lambda c: c[1:], "it does not start with its header, `IHDR`"),
        (lambda c: [c[0], c[0], *c[1:]], "it holds a second header, `IHDR`"),
        (lambda c: [(b"IHDR", bytes(13)), *c[1:]], "its header gives a size of 0 × 0 pixels"),
        (lambda c: [c[0], (b"PLTE", bytes(3)), *c[1:]], "its palette, `PLTE`, is out of place"),
    ],
    ids=["no-data", "no-header", "two-headers", "no-size", "grey-palette"],
)
def test_a_png_out_of_its_shape_cannot_be_read(change: Any, said: str) -> None:
    found = refusal(png_of(change(png_chunks(data("grey.png")))), "grey.png")
    assert found.message == f"`grey.png` cannot be read: {said}"


def test_a_palette_png_without_its_palette_cannot_be_read() -> None:
    chunks = [each for each in png_chunks(data("palette.png")) if each[0] != b"PLTE"]
    found = refusal(png_of(chunks), "palette.png")
    assert "it names colours from a palette, and holds none" in found.message


def test_a_chunk_that_claims_more_than_the_file_holds_is_refused() -> None:
    whole = bytearray(data("grey.png"))
    whole[33:37] = struct.pack(">I", 2**31 - 1)  # the first chunk after the header
    found = refusal(bytes(whole), "grey.png")
    assert found.message == "`grey.png` cannot be read: a chunk runs past the end of the file"


def test_a_jpeg_whose_image_never_ends_cannot_be_read() -> None:
    whole = data("colour.jpg")
    found = refusal(whole[: whole.rindex(b"\xff\xd9")] + b"\0\0", "colour.jpg")
    assert found.message == "`colour.jpg` cannot be read: it ends before the end of its image"


def test_a_jpeg_scan_before_its_frame_cannot_be_read() -> None:
    segments, rest = jpeg_segments(data("colour.jpg"))
    kept = [each for each in segments if each[1] != 0xC0]
    found = refusal(jpeg_of(kept, rest), "colour.jpg")
    assert found.message == "`colour.jpg` cannot be read: its first scan comes before its frame"


# --- a folder of picture files ------------------------------------------------------------------


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def held(folder: Path, *names: str, source: str = "alpha.png") -> Path:
    """`folder`, the folder of a piece or of a version, holding each of `names` in its
    `pictures/`, a copy of the test picture `source`."""
    for name in names:
        target = folder / "pictures" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(TEST_PICTURES / source, target)
    return folder


def piece_folder(tmp_path: Path, **given: Any) -> Any:
    """A piece's `pictures/` folder, its findings lying at the piece."""
    folder = tmp_path / "visual" / "pieces" / "flow"
    folder.mkdir(parents=True, exist_ok=True)
    return pictures.Folder(folder, "visual/pieces/flow/", "the piece", **given)


def version_folder(tmp_path: Path) -> Any:
    """A library version's `pictures/` folder, its findings lying in the version."""
    folder = tmp_path / "visual" / "libraries" / "parts" / "1.0.0"
    folder.mkdir(parents=True, exist_ok=True)
    return pictures.Folder(
        folder, "visual/libraries/parts/1.0.0/", "parts@1.0.0", library="parts@1.0.0"
    )


def judged(folder: Any, name: Any) -> Any:
    return folder.judge(
        name, named="the field `photo`", file="visual/pieces/flow/content.en.yaml", where="photo"
    )


@pytest.mark.parametrize("name", ["logo.png", "a.jpg", "brand-mark-2.jpeg"])
def test_a_bare_name_is_lower_case_words_and_a_picture_extension(name: str) -> None:
    assert pictures.is_bare_name(name)


@pytest.mark.parametrize(
    "name",
    [
        "Logo.png",
        "logo.PNG",
        "logo.gif",
        "2-logo.png",
        "-logo.png",
        "sub/logo.png",
        "../logo.png",
        "logo_mark.png",
        "logo",
        ".png",
        "",
        None,
        ["logo.png"],
    ],
)
def test_a_name_not_of_a_bare_names_shape_fails_where_it_is_given(
    tmp_path: Path, name: Any
) -> None:
    folder = piece_folder(tmp_path)
    found = judged(folder, name)
    assert found.picture is None
    [finding] = found.findings
    assert (finding.code, finding.level, finding.file, finding.where) == (
        "picture-name",
        findings.FAILS,
        "visual/pieces/flow/content.en.yaml",
        "photo",
    )
    assert (
        f"the field `photo` names `{name}`, which is no picture file's bare name" in finding.message
    )


def test_a_name_finds_its_file_and_reads_it(tmp_path: Path) -> None:
    folder = piece_folder(tmp_path)
    held(folder.holder, "photo.jpg", source="profile.jpg")
    found = judged(folder, "photo.jpg")
    assert found.findings == ()
    assert (found.picture.kind, found.picture.width, found.picture.height) == ("jpeg", 4, 3)
    assert found.picture.profile == profile_of("profile.jpg")


def test_a_name_the_folder_does_not_hold_fails_where_it_is_given(tmp_path: Path) -> None:
    folder = piece_folder(tmp_path)
    [finding] = judged(folder, "photo.png").findings
    assert (finding.code, finding.file, finding.where, finding.library) == (
        "picture-missing",
        "visual/pieces/flow/content.en.yaml",
        "photo",
        "",
    )
    assert finding.message == (
        "the field `photo` names `photo.png`, which the piece does not hold in `pictures/`"
    )
    assert finding.fix == "add `pictures/photo.png` to the piece, or name a file it holds there"


def test_a_name_never_finds_a_file_whose_name_differs_in_case(tmp_path: Path) -> None:
    folder = piece_folder(tmp_path)
    held(folder.holder, "Photo.png")
    [finding] = judged(folder, "photo.png").findings
    assert finding.code == "picture-missing"
    assert finding.message.endswith(
        "it holds `Photo.png`, and a name finds a file by its exact case"
    )


def test_a_name_never_finds_a_file_in_a_folder_within(tmp_path: Path) -> None:
    folder = piece_folder(tmp_path)
    held(folder.holder / "pictures", "photo.png")
    assert [f.code for f in judged(folder, "photo.png").findings] == ["picture-missing"]


def test_a_name_that_finds_a_symbolic_link_fails_at_the_link(tmp_path: Path) -> None:
    folder = piece_folder(tmp_path)
    held(folder.holder, "elsewhere.png")
    (folder.holder / "pictures" / "photo.png").symlink_to("elsewhere.png")
    found = judged(folder, "photo.png")
    assert found.picture is None
    [finding] = found.findings
    assert (finding.code, finding.file, finding.where) == (
        "picture-link",
        "visual/pieces/flow/pictures/photo.png",
        "",
    )
    assert "is a symbolic link" in finding.message
    assert finding.fix == "put the picture file itself at `pictures/photo.png`, in the link's place"


def test_a_name_finds_a_file_as_git_lists_the_folder(tmp_path: Path) -> None:
    """Tracked or untracked, but not ignored: a file only an ignored name holds finds none,
    and the message says git ignores it (DEC-025 point 2)."""
    git(tmp_path, "init", "-q")
    folder = piece_folder(tmp_path)
    held(folder.holder, "tracked.png", "untracked.png", "ignored.png")
    git(tmp_path, "add", "visual/pieces/flow/pictures/tracked.png")
    (tmp_path / ".gitignore").write_text("ignored.png\n", encoding="utf-8")
    assert judged(folder, "tracked.png").findings == ()
    assert judged(folder, "untracked.png").findings == ()
    [finding] = judged(folder, "ignored.png").findings
    assert finding.code == "picture-missing"
    assert finding.message.endswith("the file lies there, and git ignores it, so no clone holds it")


def test_a_pointer_a_large_file_store_keeps_in_a_pictures_place_says_its_bytes_are_not_committed(
    tmp_path: Path,
) -> None:
    folder = piece_folder(tmp_path)
    target = folder.holder / "pictures" / "photo.png"
    target.parent.mkdir(parents=True)
    target.write_bytes(
        b"version https://git-lfs.github.com/spec/v1\noid sha256:" + b"0" * 64 + b"\nsize 1234\n"
    )
    found = judged(folder, "photo.png")
    assert found.picture is None
    [finding] = found.findings
    assert (finding.code, finding.file) == (
        "picture-stored",
        "visual/pieces/flow/pictures/photo.png",
    )
    assert "its bytes are not committed" in finding.message
    assert (
        finding.fix == "commit the picture's own bytes: take `pictures/photo.png` out of the store"
    )


def test_a_file_git_hands_to_a_large_file_store_is_refused_whatever_its_bytes(
    tmp_path: Path,
) -> None:
    """A clone without the store would hold the pointer in its place."""
    git(tmp_path, "init", "-q")
    folder = piece_folder(tmp_path)
    held(folder.holder, "photo.png", "other.png")
    (tmp_path / ".gitattributes").write_text("photo.png filter=lfs diff=lfs merge=lfs -text\n")
    [finding] = judged(folder, "photo.png").findings
    assert finding.code == "picture-stored"
    assert "its bytes are not committed" in finding.message
    assert judged(folder, "other.png").findings == ()


@pytest.mark.skipif(os.name != "posix" or os.geteuid() == 0, reason="reads any file as root")
def test_a_file_that_cannot_be_read_fails_at_the_file(tmp_path: Path) -> None:
    folder = piece_folder(tmp_path)
    held(folder.holder, "photo.png")
    target = folder.holder / "pictures" / "photo.png"
    target.chmod(0)
    try:
        [finding] = judged(folder, "photo.png").findings
    finally:
        target.chmod(0o644)
    assert (finding.code, finding.file) == (
        "picture-unreadable",
        "visual/pieces/flow/pictures/photo.png",
    )
    assert finding.message == "`photo.png` cannot be read: Permission denied"


def test_a_file_of_an_encoding_refused_fails_at_the_file_with_its_fix(tmp_path: Path) -> None:
    folder = piece_folder(tmp_path)
    held(folder.holder, "photo.jpg", source="cmyk.jpg")
    [finding] = judged(folder, "photo.jpg").findings
    assert (finding.code, finding.file, finding.fix) == (
        "picture-encoding",
        "visual/pieces/flow/pictures/photo.jpg",
        "save it in RGB",
    )


# --- where each finding lies --------------------------------------------------------------------


def test_a_finding_on_a_pieces_picture_lies_at_the_piece_and_fails(tmp_path: Path) -> None:
    folder = piece_folder(tmp_path)
    held(folder.holder, "photo.png", source="deep.png")
    [finding] = judged(folder, "photo.png").findings
    assert finding.library == ""
    assert findings.as_read(finding, released=True)[1] == findings.FAILS


def test_a_finding_on_a_versions_picture_lies_in_it_and_asks_for_attention_once_released(
    tmp_path: Path,
) -> None:
    folder = version_folder(tmp_path)
    held(folder.holder, "photo.png", source="animated.png")
    [file_finding] = judged(folder, "photo.png").findings
    [name_finding] = judged(folder, "missing.png").findings
    for finding in (file_finding, name_finding):
        assert finding.library == "parts@1.0.0"
        assert findings.as_read(finding, released=False)[1] == findings.FAILS
        read, level = findings.as_read(finding, released=True)
        assert level == findings.ATTENTION
        assert read.who == "the owner of `parts`, who corrects it in a new release"
    assert file_finding.file == "visual/libraries/parts/1.0.0/pictures/photo.png"


def test_a_final_pieces_pictures_take_no_finding(tmp_path: Path) -> None:
    """Its content is not judged, and neither are its pictures (DEC-002 point 7)."""
    folder = piece_folder(tmp_path, final=True)
    held(folder.holder, "deep.png", source="deep.png")
    held(folder.holder, "photo.png")
    assert judged(folder, "deep.png") == pictures.Judged(None)
    assert judged(folder, "missing.png") == pictures.Judged(None)
    assert judged(folder, "Bad name") == pictures.Judged(None)
    assert judged(folder, "photo.png").picture == pictures.read(data("alpha.png"), "photo.png")


def test_a_file_is_read_once_however_often_it_is_named(tmp_path: Path) -> None:
    folder = piece_folder(tmp_path)
    held(folder.holder, "photo.png")
    first = judged(folder, "photo.png")
    (folder.holder / "pictures" / "photo.png").write_bytes(b"")
    assert judged(folder, "photo.png") == first


def test_a_brands_logo_read_in_full_is_reported_once(tmp_path: Path) -> None:
    """The brand judges the file its role names, and the full read each file of the version;
    a file nothing names is read too (DEC-014 point 1)."""
    root = project(tmp_path)
    copy_library(root, RELEASED_FOUNDATIONS, "foundations", "1.0.0")
    folder = copy_library(root, TEST_BRAND, "test-brand", "1.0.0")
    tokens = folder / "tokens" / "base.tokens.json"
    data = json.loads(tokens.read_text(encoding="utf-8"))
    data["picture"] = {"logo": {"$extensions": {"pkit.visual-communication": {"file": "logo.png"}}}}
    tokens.write_text(json.dumps(data), encoding="utf-8")
    held(folder, "logo.png", source="deep.png")
    held(folder, "spare.jpg", source="cmyk.jpg")
    held(folder, "Not-bare.png", source="deep.png")

    read = full_read.read(libraries.Held(root, "visual"), "test-brand", libraries.Version(1, 0, 0))

    assert [(f.code, f.file) for f in read.findings if f.code.startswith("picture-")] == [
        ("picture-encoding", "visual/libraries/test-brand/1.0.0/pictures/logo.png"),
        ("picture-encoding", "visual/libraries/test-brand/1.0.0/pictures/spare.jpg"),
    ]
