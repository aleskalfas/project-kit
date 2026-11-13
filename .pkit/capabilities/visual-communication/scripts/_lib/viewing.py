"""The viewing step: a piece's drawn pages as images a person or an agent reads
(visual-communication DEC-015, DEC-020 point 5, DEC-027).

It is no plugin, no render and no export. It uses the seam from the engine's side, as
render and export do, and adds nothing to it. Only a person or an agent reads what it
writes, never a check, an export or a producer. So nothing here moves a lock, keeps a
finding or takes a number, no helper or producer runs, and a produced picture is drawn as it
stands, stale or not. Its scenes fill an export's facts as a preview's do: the next number
is read, and none is used up (DEC-016 point 5).

- **Under the lock.** It reads the piece's own file with its lock and computes the scenes
  under it. A piece with no lock, or a lock that does not hold, is refused (`opened`). A
  version not yet released stops no drawing.
- **What it draws.** The caller picks pages, languages, keys and the renderer (`Asked`). By
  default it draws every page in the source language, in the first key in the order a
  picture's variant uses (`keys.variant_key`), through the renderer `renderer_of` gives.
- **The SVG renderer's pages.** `viewing_tool` draws each page, at `LONG_EDGE` pixels on its
  long edge, or more where the page's smallest text would land under `SMALLEST_TEXT`. The
  tool may draw a picture without the colour profile it carries, so the report names each
  picture a page shows with one (`with_profiles`, DEC-025 point 5).
- **Bands** (DEC-022 point 7). A page too tall for one such image is drawn in bands, strips
  of its height each as wide as the page, at one scale (`bands`). The step computes them
  once, from the scene's frames, and each tool's module draws the regions it is handed, so
  both routes cut a page alike. Beside each band lie the frames of the elements it shows, in
  its own pixels. A page too wide for one image whose smallest text reads is drawn as wide as
  `LONG_EDGE` allows, and the report says its smallest text may not read (`page_scale`,
  `too_wide`). Text drawn to nothing is still read on the whole page, once.
- **The HTML renderer's pages.** `viewing_browser` draws each page file as the renderer wrote
  it, in one browser start, its pages at one device scale, the largest any of them asks, as
  far as the widest fits `LONG_EDGE` (`device_scale`). A file holds every key its group gives
  it, whichever keys the caller picks, and the start draws each key picked out of it, with no
  reload: the step takes each key's signals from the renderer's declaration (`signals_of`)
  and the browser's module sets them (DEC-023 point 6).
  The browser is the one the configuration names (`browser_named`), or else the first found
  where Chrome and Chromium install themselves. Its profile lies in the clone's local folder,
  and the module removes it.
- **Under forced colours,** where the caller asks (DEC-027). After a file's start, a second
  start draws it in each of the browser's forced palettes, at the same device scale. The step
  reads from the declaration's signal pairs which key the file holds for each palette's
  signals (`key_shown`), and that key names the image. Each palette's images lie in a folder
  of their own in the renderer's folder (`FORCED_FOLDER`), under the names any image takes,
  and the report names the palette in a field of its own (`FORCED`), in each image and each
  entry that lies on one. resvg knows no forced colours, so a run through the SVG renderer
  that asks for them is refused.
- **Beside them,** in the renderer's own folder of `FOLDER` (`folder_of`): each image's
  frames, one report of what the images cannot show as the renderer set it (DEC-015 point
  3), and for the HTML renderer each page file, for a person to open in their own browser.
- **A stop.** Where no browser runs, or one stops part way, or its first read fails, the
  run gives the page files and a report that says what stopped it, and no image (DEC-020
  point 8). Every refusal comes before that. The report names the ways on, in the order of
  DEC-024 point 4 (`ways_on`), and what an agent does where it stops (DEC-024 point 6).
- **A run replaces** what an earlier run left in its renderer's folder, as one change
  (`write`), and leaves the other renderer's folder where it lies.
"""

from __future__ import annotations

import json
import math
import tempfile
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, NamedTuple

from _lib import (
    checks,
    files,
    keys,
    layout,
    libraries,
    location,
    pictures,
    tokens,
    viewing_browser,
    viewing_tool,
)
from _lib import pipeline as pl
from _lib.checks import draws_ground
from _lib.env import MissingFont
from _lib.plugins import seam
from _lib.reading import ReadError, read_yaml
from _lib.root import CONFIG, LOCAL
from _lib.scene import SceneResult

#: Where the images of each piece lie, relative to the project root.
FOLDER = f"{LOCAL}/look"

#: The file beside the images that says what they cannot show.
REPORT = "report.json"

#: How long an image's long edge is, in pixels: a page's smallest text reads at it.
LONG_EDGE = 1568

#: The size a page's smallest text keeps in its image, in pixels, on a page so large that
#: `LONG_EDGE` would set it smaller.
SMALLEST_TEXT = 10.0

#: The renderers a run reads a piece through: the SVG renderer's pages through resvg, and the
#: HTML renderer's page files through a browser (DEC-020 point 5).
SVG = "svg"
HTML = "html"
RENDERERS = (SVG, HTML)

#: The configuration's key that names the browser the HTML renderer's pages are drawn
#: through, in place of the first one found (DEC-020 point 7).
BROWSER_KEY = "browser"

#: What the report says of an image whose page draws no ground: through the SVG renderer it
#: lies on white, and through the HTML renderer on the browser's own ground in the mode drawn
#: (DEC-015 point 5, DEC-023 point 7).
ON_WHITE = "on-white"
ON_BROWSER_GROUND = "on-browser-ground"

#: What the report says of an image of a page too wide for its smallest text to read at
#: `LONG_EDGE` pixels wide (DEC-022 point 7).
TOO_WIDE = "too-wide"

#: The flag of the command that asks for the forced palettes, and the field of the report
#: that names the one an image, or an entry that lies on it, was drawn in, empty for none
#: (DEC-027 points 1 and 5).
ASK_FORCED = "--forced-colours"
FORCED = "forced"

#: The folder of each forced palette's images inside the renderer's folder: a name with no
#: `.`, which no image, frames, page file or report takes, since each of theirs holds one.
FORCED_FOLDER = "forced-{}"

#: What the report says the forced images do not show (DEC-027 point 6), after the browser
#: that drew them.
FORCED_UNSHOWN = (
    "forced palette, not a reader's own, which may hold other colours, such as a link's. Each "
    "palette is drawn with the scheme of its darkness and more contrast, so a reader whose "
    "browser reports another scheme or contrast beside its forced palette meets a pairing no "
    "image shows"
)

#: How many decimals a browser's device scale keeps, rounded up, so its flag names it whole.
SCALE_PLACES = 3

#: How many decimals of a px a band's edge keeps, as the scene's lengths do.
BAND_PLACES = 2

#: The share of a band the overlap with the next may take at most. Bands of about one height
#: then each start well below the one before, even on a page whose tallest line is as tall
#: as a band.
MOST_OVERLAP = 1 / 4

#: The name a build pipeline keeps a commit's drawings under, and the page that says how one
#: draws them and how they are fetched (DEC-024 point 5).
DRAWINGS = "visual-drawings-<commit>"
DRAWINGS_PAGE = ".pkit/capabilities/visual-communication/outputs.md"
DRAWINGS_SECTION = "A pipeline's drawings"

#: The scenes of a piece, by language.
Results = Sequence[tuple[str, SceneResult]]


@dataclass(frozen=True)
class Asked:
    """What a run draws: its languages and keys, each page by its number or trace id, every
    page where none is named, the renderer it reads them through, and whether it draws each
    page file in the browser's forced palettes too."""

    languages: tuple[str, ...]
    keys: tuple[str, ...]
    pages: tuple[str, ...] = ()
    renderer: str = SVG
    forced: bool = False


@dataclass(frozen=True)
class Viewed:
    """What a run gives: each file of the renderer's folder, by name, and its report.
    `stopped` is whether a browser drew nothing, so the files hold no image."""

    files: dict[str, bytes]
    report: dict[str, Any]
    stopped: bool = False


def opened(root: Path, name: str) -> pl.Project:
    """The piece `name` under the lock its `piece.yaml` holds. Raises Refused where it has
    no lock, its lock does not hold, or its brand cannot be read. A version not yet released
    under a final or a published piece's lock holds, and draws."""
    found = location.for_reading(root)
    if found is None:
        raise pl.Refused(f"the project holds no visual work, so no piece `{name}`")
    piece = pl.read_piece(root, found.path, name)
    held = libraries.Held(root, found.path)
    faults = [
        finding
        for finding in checks.lock_findings(held, piece)
        if finding.code != checks.LOCK_NOT_RELEASED
    ]
    if faults:
        said = "; ".join(checks.said(finding) for finding in faults)
        raise pl.Refused(f"the lock of {piece.file(pl.PIECE_FILE)} cannot be drawn: {said}")
    try:
        return pl.Project(piece, piece.lock, held)
    except tokens.TokenError as exc:
        said = "; ".join(finding.message for finding in exc.findings)
        raise pl.Refused(f"the brand of `{name}` cannot be read: {said}") from exc


def scenes(
    project: pl.Project,
    languages: Sequence[str],
    keys: Sequence[str] | None = None,
    *,
    facts: layout.Facts,
) -> list[tuple[str, SceneResult]]:
    """The scenes of `languages`, computed under the lock: one for each key over the size
    axes, or each that serves one of the combinations `keys`. `facts` fills the facts of
    its export, as a preview's do (`exports.preview_filling`, DEC-016 point 5). Raises
    Refused where a font cannot measure the text."""
    try:
        return project.scenes(languages, keys, facts=facts)
    except MissingFont as exc:
        raise pl.Refused(f"`{project.piece.name}` cannot be drawn: {exc}") from exc


def first_key(project: pl.Project) -> str:
    """The key drawn by default: the first in the order a picture's variant uses, so the
    combination of defaults wherever the piece names it (DEC-015 point 5)."""
    return keys.variant_key(project.keys)


def asked(
    project: pl.Project,
    *,
    languages: Sequence[str] = (),
    every_language: bool = False,
    named_keys: Sequence[str] = (),
    every_key: bool = False,
    pages: Sequence[str] = (),
    renderer: str | None = None,
    forced: bool = False,
) -> Asked:
    """What a caller's choices ask of `project`. Raises Refused for a language or a key the
    piece does not name, naming those it does, for a renderer the step does not read, and for
    forced colours through the SVG renderer, naming the HTML renderer's where the piece goes
    through the SVG renderer by default (DEC-027 point 1)."""
    piece = project.piece
    if renderer is not None and renderer not in RENDERERS:
        raise pl.Refused(
            f"the viewing step reads no renderer `{renderer}`: it reads "
            f"{' and '.join(f'`{each}`' for each in RENDERERS)}"
        )
    through = renderer or renderer_of(piece)
    if forced and through == SVG:
        said = (
            f"resvg draws the SVG renderer's pages and knows no forced colours, so `{ASK_FORCED}` "
            f"draws only the HTML renderer's"
        )
        if renderer is None:
            said += (
                f". `{piece.name}` goes through the SVG renderer by default: `pkit visual look "
                f"{piece.name} --renderer {HTML} {ASK_FORCED}` draws its HTML renderer's pages"
            )
        raise pl.Refused(said)
    held = piece.languages
    chosen = _chosen(languages, held, "language", piece.name, every_language) or held[:1]
    named = _chosen(named_keys, project.keys, "key", piece.name, every_key)
    return Asked(tuple(chosen), tuple(named or [first_key(project)]), tuple(pages), through, forced)


def renderer_of(piece: pl.Piece) -> str:
    """The renderer a run reads `piece` through by default: the HTML renderer where it declares
    `html`, since a reviewer of a web page should see that page, and the SVG renderer
    otherwise (DEC-020 point 5)."""
    return HTML if HTML in piece.exports else SVG


def folder_of(name: str, renderer: str) -> str:
    """The folder of the piece `name`'s images through `renderer`, relative to the project
    root: `<piece>/` for the SVG renderer's, and `<piece>.<renderer>/` beside it for another's,
    a name no piece can take, since a piece's name holds no `.` (DEC-020 point 5)."""
    return f"{FOLDER}/{name}" if renderer == SVG else f"{FOLDER}/{name}.{renderer}"


def browser_named(root: Path) -> Path | None:
    """The browser the configuration names under `BROWSER_KEY`, or None, where the step takes
    the first it finds (DEC-020 point 7). No flag and no environment variable names one, so
    the choice lies in a file the project reviews. A path that starts `~/` lies in the home
    folder, and a relative one below the project root. Raises Refused where the configuration
    cannot be read, or names no path there."""
    target = root / CONFIG
    if not target.is_file():
        return None
    try:
        data = read_yaml(target)
    except ReadError as exc:
        raise pl.Refused(f"{CONFIG} cannot be read: {exc}") from exc
    if data is None:
        return None
    if not isinstance(data, dict):
        raise pl.Refused(f"{CONFIG} is not a mapping; fix it first")
    if BROWSER_KEY not in data:
        return None
    value = data[BROWSER_KEY]
    if not isinstance(value, str) or not value:
        raise pl.Refused(
            f"{CONFIG} records `{BROWSER_KEY}: {value!r}`, which names no program: write the "
            f"path of the browser there, or remove the line"
        )
    path = Path(value).expanduser()
    return path if path.is_absolute() else root / path


def browser_found(root: Path) -> dict[str, Any]:
    """The browser a run would draw the HTML renderer's pages through: its program, or None,
    whether the configuration names it, where the step looked where it found none, and the
    forced palettes it can draw where asked (DEC-027 point 2). Starts nothing. Raises Refused
    where the configuration cannot be read."""
    named = browser_named(root)
    palettes = [palette.name for palette in viewing_browser.PALETTES]
    found: dict[str, Any] = {"program": None, "named": named is not None, "looked": []}
    try:
        found["program"] = str(viewing_browser.find(named))
    except viewing_browser.Stopped as stop:
        found["looked"] = list(stop.looked)
    return {**found, "forced-palettes": palettes}


def _chosen(
    given: Sequence[str], held: Sequence[str], what: str, piece: str, every: bool
) -> list[str]:
    """The ones of `held` a caller named, each once, in `held`'s order, or all of them."""
    unknown = [each for each in given if each not in held]
    if unknown:
        raise pl.Refused(
            f"`{piece}` has no {what} `{unknown[0]}`: it has {', '.join(f'`{h}`' for h in held)}"
        )
    return list(held) if every else [each for each in held if each in given]


def pages_of(scene: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """The scene's pages, as groups, in order."""
    found = {element["id"]: element for element in _elements(scene)}
    return [found[trace] for trace in scene.get("pages", []) if trace in found]


def _elements(parent: Mapping[str, Any]) -> Iterator[Mapping[str, Any]]:
    """Every element under `parent`, in drawing order."""
    for child in parent.get("children", []):
        yield child
        yield from _elements(child)


def _numbers(scene: Mapping[str, Any], named: Sequence[str]) -> list[int]:
    """The page numbers, from 1, of the pages `named` by a number or a trace id, in order;
    every page where none is named. Raises Refused for one the scene does not hold."""
    traces = list(scene.get("pages", []))
    if not named:
        return list(range(1, len(traces) + 1))
    chosen = set()
    for page in named:
        if page in traces:
            chosen.add(traces.index(page) + 1)
        elif page.isdecimal() and 1 <= int(page) <= len(traces):
            chosen.add(int(page))
        else:
            raise pl.Refused(
                f"`{scene.get('piece')}` has no page `{page}` in `{scene.get('language')}`: it "
                f"has {len(traces)}, from 1, which `pkit visual pages {scene.get('piece')}` lists"
            )
    return sorted(chosen)


def view(project: pl.Project, results: Results, wanted: Asked) -> Viewed:
    """The images, the frames and the report of a run, through the renderer `wanted` names.
    Writes only transient files, in a temporary folder of the clone's local folder, which it
    removes: the SVG renderer's faces (DEC-015 point 2), or the HTML renderer's page files and
    the browser's profile (DEC-020 point 5). Raises Refused for a page the scene does not
    hold, or that cannot be drawn."""
    shown = {
        (language, result.scene.size_key): (
            scene := result.scene.to_dict(),
            _numbers(scene, wanted.pages),
        )
        for language, result in results
    }
    local = project.root / LOCAL
    if wanted.renderer == HTML:
        return _through_a_browser(project, results, wanted, shown, local)
    local.mkdir(parents=True, exist_ok=True)
    made = _Made(project, SVG)
    with tempfile.TemporaryDirectory(prefix="faces-", dir=local) as faces:
        for language, (key,), drawn in pl.drawn(project, results, SVG, wanted.keys):
            scene, numbers = shown[language, project.size_key(key)]
            handed = project.env.handed(scene, key)
            for number in numbers:
                made.add(scene, language, key, number, drawn, Path(faces), handed)
            made.lost(scene, language, key, numbers, drawn.losses)
    return made.viewed()


#: Each scene, by its language and its key over the size axes, and the numbers of the pages
#: a run draws of it.
_Shown = Mapping[tuple[str, str], tuple[Mapping[str, Any], list[int]]]


@dataclass(frozen=True)
class _PageFile:
    """A page file a run draws: its name, its language, the keys it holds, the first naming
    it, the renderer's bytes, its scene with the numbers of the pages drawn of it, the device
    scale they share, the regions of each page drawn, by its number, each key drawn out of
    it with its signals, in the order of its keys, and the key each forced palette shows, by
    the palette's name, none where the run asks for none."""

    name: str
    language: str
    keys: tuple[str, ...]
    document: bytes
    scene: Mapping[str, Any]
    numbers: list[int]
    scale: float
    bands: Mapping[int, tuple[Region, ...]]
    modes: Mapping[str, Mapping[str, str]]
    forced: Mapping[str, str] = field(default_factory=dict[str, str])


def _through_a_browser(
    project: pl.Project, results: Results, wanted: Asked, shown: _Shown, local: Path
) -> Viewed:
    """The HTML renderer's page files, each drawn as it was written, in one browser start, and
    where the caller asks, in a second start in the browser's forced palettes (DEC-020 points 5
    and 8, DEC-027 point 3). Every refusal comes before a file is written. A stop of either
    start gives the page files and a report that says what stopped it, and no image."""
    made = _Made(project, HTML, wanted.forced)
    declared = seam.declaration(HTML, seam.RENDERER)
    combinations = dict(zip(project.keys, project.combinations, strict=True))
    planned = []
    for language, held, drawn in pl.drawn(project, results, HTML, wanted.keys):
        scene, numbers = shown[language, project.size_key(held[0])]
        every = pages_of(scene)
        scale = device_scale([every[number - 1] for number in numbers])
        regions = {number: bands(every[number - 1], scale) for number in numbers}
        for number in numbers:
            _refuse_a_size(project, every[number - 1], scale, regions[number])
        name = f"{project.piece.name}.{language}.{held[0]}.html"
        modes = {
            key: signals_of(declared, HTML, combinations[key]) for key in held if key in wanted.keys
        }
        forced = {
            palette.name: key_shown(
                declared, HTML, {key: combinations[key] for key in held}, palette.signals
            )
            for palette in (viewing_browser.PALETTES if wanted.forced else ())
        }
        planned.append(
            _PageFile(
                name, language, held, drawn.document, scene, numbers, scale, regions, modes, forced
            )
        )
        made.page_file(language, held, name, drawn.document)
        drawn_in = [*((key, "") for key in modes), *((key, p) for p, key in forced.items())]
        for key, palette in drawn_in:
            lost = [loss for loss in drawn.losses if loss.key in (None, key)]
            made.lost(scene, language, key, numbers, lost, palette)
    named = browser_named(project.root)
    local.mkdir(parents=True, exist_ok=True)
    forcing = False
    try:
        program = viewing_browser.find(named)
        drawings = []
        with tempfile.TemporaryDirectory(prefix="page-files-", dir=local) as held:
            for each in planned:
                forcing = False
                drawing = _drawn(each, Path(held), program, local)
                forcing = bool(each.forced)
                forced_drawing = _drawn(each, Path(held), program, local, True) if forcing else None
                drawings.append((each, drawing, forced_drawing))
    except viewing_browser.Stopped as stop:
        return made.stopped(stop, forcing)
    for each, drawing, forced_drawing in drawings:
        made.through(each, drawing, program)
        if forced_drawing is not None:
            made.through(each, forced_drawing, program)
    return made.viewed()


def _drawn(
    planned: _PageFile, folder: Path, program: Path, local: Path, forced: bool = False
) -> viewing_browser.Drawing:
    """One page file through the browser `program`, written in `folder` under its own name
    with the renderer's bytes, so the browser reads it as the renderer wrote it: each key
    drawn in its signals, or where `forced`, in a start of its own, each forced palette. The
    browser's profile lies in `local`, which the module removes. Raises Stopped."""
    file = folder / planned.name
    file.write_bytes(planned.document)
    every = pages_of(planned.scene)
    pages = [browser_page(every[number - 1], planned.bands[number]) for number in planned.numbers]
    signals = signals_read(seam.declaration(HTML, seam.RENDERER), HTML)
    if forced:
        return viewing_browser.draw_forced(
            file, pages, planned.scale, program, local, signals=signals
        )
    modes = list(planned.modes.values())
    return viewing_browser.draw(
        file, pages, planned.scale, program, local, signals=signals, modes=modes
    )


def signals_read(declared: Mapping[str, Any], form: str) -> dict[str, tuple[str, ...]]:
    """Each reader's signal a file of the format `form` reads, as the renderer's declaration
    pairs its modes, with each value it pairs a mode with, the value of a reader with no
    preference first (DEC-023 point 5)."""
    pairs = declared.get("holds-modes", {}).get(form, {})
    return {pair["signal"]: tuple(pair["pairs"].values()) for pair in pairs.values()}


def signals_of(
    declared: Mapping[str, Any], form: str, combination: Mapping[str, str]
) -> dict[str, str]:
    """The signals a reader of the combination `combination` gives a file of the format `form`:
    every signal it reads (`signals_read`), each at the value its axis's mode there pairs with
    in the renderer's declaration (DEC-023 point 6). A mode that pairs with none lies in a
    file of its own, which no rule on that signal parts, so its signal takes the value of a
    reader with no preference."""
    pairs = declared.get("holds-modes", {}).get(form, {})
    found = {}
    for axis, pair in pairs.items():
        values = pair["pairs"]
        found[pair["signal"]] = values.get(combination.get(axis), next(iter(values.values())))
    return found


def key_shown(
    declared: Mapping[str, Any],
    form: str,
    held: Mapping[str, Mapping[str, str]],
    signals: Mapping[str, str],
) -> str:
    """The key of a file of the format `form` that a reader whose browser sets `signals` gets,
    of the keys `held`, each with its combination, the first naming the file (DEC-027 point 2).
    As the renderer writes the file, the first key's values hold under any signals, and each
    other key's hold where each signal that parts it from the first takes its value in
    `signals`, the rule of more such signals after the rule of fewer, so a later rule wins
    (DEC-023 point 4)."""
    given = {key: signals_of(declared, form, combination) for key, combination in held.items()}
    first = next(iter(given.values()))
    found, most = next(iter(given)), 0
    for key, each in given.items():
        parted = {signal: value for signal, value in each.items() if value != first[signal]}
        if len(parted) >= most and all(signals.get(s) == v for s, v in parted.items()):
            found, most = key, len(parted)
    return found


def browser_page(page: Mapping[str, Any], regions: Sequence[Region] = ()) -> viewing_browser.Page:
    """`page` as the browser's reads take it: its trace id and size, each of its texts in the
    tree's order, with the spans of each line, and the bands among `regions` it is drawn in,
    none where one image shows it whole."""
    texts = tuple(
        viewing_browser.Text(
            element["id"],
            tuple(
                tuple(str(span["text"]) for span in line.get("spans", []))
                for line in element.get("lines", [])
            ),
        )
        for element in _elements(page)
        if element.get("type") == "text"
    )
    width, height = float(page["width"]), float(page["height"])
    return viewing_browser.Page(page["id"], width, height, texts, _handed(regions))


def _refuse_a_size(
    project: pl.Project, page: Mapping[str, Any], scale: float, regions: Sequence[Region]
) -> None:
    """Refuse a page with no size, or one whose image, or the image of one of its bands
    `regions` holds, takes more than `viewing_tool.MOST_PIXELS` at `scale` device pixels to a
    px, as the SVG renderer's pages are refused, before the browser is asked."""
    width, height = float(page["width"]), float(page["height"])
    most = viewing_tool.MOST_PIXELS
    tallest = max((region.height for region in regions), default=height)
    what = "the page" if len(regions) < 2 else "a band of the page"
    if min(width, height) <= 0:
        said = f"the page measures {width:g} by {height:g} px"
    elif width * tallest * scale**2 > most:
        said = f"at {scale:g} device pixels to a px {what} takes more than {most}"
    else:
        return
    raise _cannot_draw(project, page, "the browser", said)


def _cannot_draw(project: pl.Project, page: Mapping[str, Any], tool: str, said: str) -> pl.Refused:
    """The refusal of a page `tool` cannot draw, for the reason `said`."""
    piece = project.piece.name
    said = f"{tool} cannot draw page {page['id']} of `{piece}`: {said}"
    # The check reads no picture of a final piece (DEC-017 point 4).
    if not project.piece.final:
        said += f". `pkit visual check {piece}` names what the piece still owes"
    return pl.Refused(said)


class _Made:
    """What a run has drawn so far, through `renderer`, and whether it asks for the browser's
    forced palettes too."""

    def __init__(self, project: pl.Project, renderer: str, forced: bool = False) -> None:
        self.project = project
        self.renderer = renderer
        self.forced = forced
        self.document = project.values()
        self.files: dict[str, bytes] = {}
        self.tool: dict[str, Any] | None = viewing_tool.TOOL if renderer == SVG else None
        self.stop: dict[str, Any] | None = None
        self.page_files: list[dict[str, Any]] = []
        self.images: list[dict[str, Any]] = []
        self.words: list[dict[str, Any]] = []
        self.dropped: list[dict[str, Any]] = []
        self.otherwise: list[dict[str, Any]] = []
        self.profiles: list[dict[str, Any]] = []
        self.refused: list[dict[str, Any]] = []
        self.losses: list[dict[str, Any]] = []

    def add(
        self,
        scene: Mapping[str, Any],
        language: str,
        key: str,
        number: int,
        drawn: Any,
        faces: Path,
        handed: Mapping[str, seam.Shown],
    ) -> None:
        """One page of the SVG renderer's, of one language and key: its image, or an image of
        each of its bands, with their frames, and what the report says of it, each picture
        `handed` that carries a colour profile among it."""
        page = pages_of(scene)[number - 1]
        at = {"language": language, "key": key, "page": page["id"]}
        drawn_at = page_scale(page)
        regions = bands(page, drawn_at)
        try:
            image = viewing_tool.draw(
                drawn.pages[number - 1].svg,
                drawn_at,
                faces,
                line_widths(page),
                regions=_handed(regions),
            )
        except viewing_tool.ToolFailed as exc:
            raise _cannot_draw(self.project, page, "the tool", str(exc)) from exc
        narrow = too_wide(page, drawn_at)
        for band, each in zip(_numbered(regions), image.images, strict=True):
            self._image(
                scene, language, key, number, each.image, each.width, each.height, band, narrow
            )
        self.dropped.extend(
            {**at, "element": each.element, "text": each.text, "whole": each.whole}
            for each in image.dropped
        )
        self.otherwise.extend({**at, **each} for each in drawn_otherwise(page))
        self.profiles.extend({**at, **each} for each in with_profiles(page, handed))

    def page_file(self, language: str, keys: Sequence[str], name: str, document: bytes) -> None:
        """A page file the HTML renderer wrote, left beside the images as it was written: the
        keys it holds, the first naming it."""
        self.files[name] = document
        self.page_files.append(
            {"language": language, "key": keys[0], "keys": list(keys), "file": name}
        )

    def through(self, planned: _PageFile, drawing: viewing_browser.Drawing, program: Path) -> None:
        """The pages of one page file a browser drew, in each key drawn out of it, or in each
        forced palette, by the key it shows: each image and its frames, and what the report
        says of them (DEC-020 point 6, DEC-023 point 6, DEC-027 point 5)."""
        name, _, version = drawing.browser.partition("/")
        self.tool = {"name": name, "version": version, "program": str(program)}
        keys = iter(planned.modes)
        for shown in drawing.shown:
            key = planned.forced[shown.palette] if shown.palette else next(keys)
            self._through_in(planned, key, shown)

    def _through_in(self, planned: _PageFile, key: str, shown: viewing_browser.Shown) -> None:
        """The pages of one page file a browser drew in the key `key`, under the forced palette
        `shown` names, if any."""
        every = pages_of(planned.scene)
        numbers = {every[number - 1]["id"]: number for number in planned.numbers}
        for image in shown.images:
            number = numbers[image.page]
            regions = _numbered(planned.bands[number])
            self._image(
                planned.scene,
                planned.language,
                key,
                number,
                image.image,
                image.width,
                image.height,
                regions[image.band - 1] if image.band else None,
                too_wide(every[number - 1], planned.scale),
                shown.palette,
            )
        where = {"language": planned.language, "key": key, **self._forced_in(shown.palette)}
        read = shown.read
        self.words.extend(
            {
                **where,
                "page": each.page,
                "element": each.element,
                "scene": [list(line) for line in each.scene],
                "document": [[list(line) for line in held] for held in each.document],
            }
            for each in read.words
        )
        self.dropped.extend(
            {
                **where,
                "page": each.page,
                "element": each.element,
                "text": each.text,
                "why": each.why,
            }
            for each in read.dropped
        )
        self.otherwise.extend(
            {
                **where,
                "page": each.page,
                "element": each.element,
                "text": each.text,
                "why": viewing_browser.NO_FACE,
                "family": each.family,
                "weight": each.weight,
            }
            for each in read.no_face
        )
        self.otherwise.extend(
            {
                **where,
                "page": each.page,
                "element": each.element,
                "text": each.text,
                "why": viewing_browser.MACHINE_FONT,
                "fonts": list(each.fonts),
            }
            for each in read.machine_fonts
        )
        self.refused.extend({**where, "url": url} for url in read.refused)

    def _image(
        self,
        scene: Mapping[str, Any],
        language: str,
        key: str,
        number: int,
        image: bytes,
        width: int,
        height: int,
        band: _Band | None = None,
        narrow: bool = False,
        palette: str = "",
    ) -> None:
        """One page's image, or one band's, its frames, and its entry in the report. `narrow`
        says the page is too wide for its smallest text to read (DEC-022 point 7). An image
        under the forced palette `palette` lies in that palette's folder (DEC-027 point 5)."""
        piece = self.project.piece.name
        every = pages_of(scene)
        page = every[number - 1]
        at = {"language": language, "key": key, "page": page["id"], **self._forced_in(palette)}
        stem = f"{piece}.{language}.{key}" + (f".{number}" if len(every) > 1 else "")
        stem += f".band-{band.number}" if band else ""
        stem = f"{FORCED_FOLDER.format(palette)}/{stem}" if palette else stem
        held = {"band": band.said()} if band else {}
        self.files[f"{stem}.png"] = image
        self.files[f"{stem}.frames.json"] = _json(
            {
                **at,
                "number": number,
                **held,
                "image": f"{stem}.png",
                "pixels": {"width": width, "height": height},
                "lock": self.project.lock,
                "elements": frames(page, width, height, band.region if band else None),
            }
        )
        ground = draws_ground(page, pl.colours_at(self.document, key, scene))
        self.images.append(
            {
                **at,
                "number": number,
                **held,
                "image": f"{stem}.png",
                "frames": f"{stem}.frames.json",
                "pixels": {"width": width, "height": height},
                ON_WHITE if self.renderer == SVG else ON_BROWSER_GROUND: not ground,
                **({TOO_WIDE: True} if narrow else {}),
            }
        )

    def lost(
        self,
        scene: Mapping[str, Any],
        language: str,
        key: str,
        numbers: Sequence[int],
        losses: Sequence[seam.Loss],
        palette: str = "",
    ) -> None:
        """Each loss of the pages drawn, known before the renderer ran or reported as it
        drew, whether or not the piece accepts it (DEC-015 point 3), under the forced palette
        `palette`, if any."""
        declared = seam.declaration(self.renderer, seam.RENDERER)
        pages = pages_of(scene)
        owners = {
            element["id"]: pages[number - 1]["id"]
            for number in numbers
            for element in _elements(pages[number - 1])
        }
        known = checks.losses(scene, declared)
        for loss in (*known, *(each for each in losses if each not in known)):
            if loss.what in owners:
                self.losses.append(
                    {
                        "language": language,
                        "key": key,
                        "page": owners[loss.what],
                        **self._forced_in(palette),
                        "plugin": loss.plugin,
                        "what": loss.what,
                        "did": loss.did,
                        "why": loss.why,
                        "accepted": checks.accepted(loss, self.project.piece.accepted_losses),
                    }
                )

    def _forced_in(self, palette: str) -> dict[str, Any]:
        """The field that names the forced palette an image, or an entry that lies on one, was
        drawn in: none for the SVG renderer's, and empty for an image under none."""
        return {FORCED: palette or None} if self.renderer == HTML else {}

    def stopped(self, stop: viewing_browser.Stopped, forcing: bool = False) -> Viewed:
        """What a stop gives: the page files, and a report that says what stopped the browser,
        what is missing and how to go on, and no image (DEC-020 point 8, DEC-024 point 4).
        `forcing` says it stopped a start that forced its colours, whose ways on name a run
        without forced colours too (DEC-027 point 4)."""
        self.stop = {
            "what": stop.what,
            "looked": list(stop.looked),
            "program": stop.program,
            "said": stop.said,
            "sandbox": stop.sandbox,
            "as-root": stop.as_root,
            "forcing": forcing,
            "go-on": ways_on(self.project.piece.name, forcing),
            "for-an-agent": FOR_AN_AGENT,
        }
        return self.viewed()

    def viewed(self) -> Viewed:
        declared = seam.declaration(self.renderer, seam.RENDERER)
        report: dict[str, Any] = {
            "piece": self.project.piece.name,
            "lock": self.project.lock,
            "renderer": {"name": self.renderer, "version": declared["version"]},
            "tool": self.tool,
        }
        if self.renderer == SVG:
            report.update(
                images=self.images,
                dropped=self.dropped,
                losses=self.losses,
            )
            report["drawn-otherwise"] = self.otherwise
            report["profiles"] = self.profiles
            return Viewed({**self.files, REPORT: _json(report)}, report)
        if self.stop is None and self.tool is not None:
            report["stands-for"] = (
                f"each image shows how {self.tool['name']} {self.tool['version']} drew the page, "
                f"and stands for no other browser"
            )
        report[FORCED] = self._forced_said()
        report["stopped"] = self.stop
        report["page-files"] = self.page_files
        report.update(images=self.images, words=self.words, dropped=self.dropped)
        report["losses"] = self.losses
        report["drawn-otherwise"] = self.otherwise
        report["refused"] = self.refused
        return Viewed({**self.files, REPORT: _json(report)}, report, self.stop is not None)

    def _forced_said(self) -> dict[str, Any] | None:
        """What the report says of the forced palettes a run asks for: each one, the browser's
        flag that forced them, the folder of each, and what their images do not show (DEC-027
        points 5 and 6). None where it asks for none."""
        if not self.forced:
            return None
        names = [palette.name for palette in viewing_browser.PALETTES]
        tool = f"{self.tool['name']} {self.tool['version']}" if self.tool else "the browser"
        return {
            "palettes": names,
            "flag": viewing_browser.FORCING,
            "folders": {name: f"{FORCED_FOLDER.format(name)}/" for name in names},
            "does-not-show": f"each forced image shows {tool}'s own {FORCED_UNSHOWN}",
        }


#: What an agent does where a look stops: it opens no way out of the sandbox itself (DEC-024
#: point 6). It names no way out, as no stop does (DEC-024 point 4).
FOR_AN_AGENT = (
    "read a pipeline's drawings where you can reach them, or ask a person, naming these ways "
    "on. Never take this command out of the sandbox yourself, and never run a look over the "
    "folder a person's run left"
)


def ways_on(piece: str, forcing: bool = False) -> list[str]:
    """The ways on from a stop of `piece`'s HTML renderer's pages, in the order of DEC-024
    point 4: a build pipeline's drawings, a way a project may take, which show a pushed commit;
    the same look run by a person outside the sandbox, a line addressed to that person; and
    the SVG renderer's pages, which show the layout. Where the start that stopped forced its
    colours, a run without forced colours too (DEC-027 point 4)."""
    unforced = [
        f"`pkit visual look {piece} --renderer {HTML}`, without `{ASK_FORCED}`, draws the same "
        f"page files in their own colours, in a start that forces none"
    ]
    return [
        (
            f"a build pipeline's drawings, where the project has its pipeline draw each piece's "
            f"pages: read those of `{piece}`, kept as `{DRAWINGS}`. They show a pushed commit, "
            f'not the working tree ({DRAWINGS_PAGE}, "{DRAWINGS_SECTION}")'
        ),
        (
            f"for a person: run `pkit visual look {piece} --renderer {HTML}` once on a machine "
            f"with a browser, outside any sandbox, such as in your own terminal. It runs the "
            f"clone's scripts as they stand, with your rights"
        ),
        (
            f"`pkit visual look {piece} --renderer {SVG}` draws the same scenes through the SVG "
            f"renderer and resvg, whose images show the layout, never this page"
        ),
        *(unforced if forcing else []),
    ]


class Region(NamedTuple):
    """A strip of a page's height one image shows: its top and its height, in the page's px."""

    top: float
    height: float


@dataclass(frozen=True)
class _Band:
    """One band of a page drawn: its number, from 1, how many the page has, and its region."""

    number: int
    of: int
    region: Region

    def said(self) -> dict[str, Any]:
        """The band as the report and its frames name it."""
        top, height = self.region
        return {"number": self.number, "of": self.of, "top": top, "height": height}


def _numbered(regions: Sequence[Region]) -> list[_Band | None]:
    """Each of `regions` as an image of it is named: None for one that shows a page whole,
    and each band with its number otherwise."""
    if len(regions) < 2:
        return [None]
    return [_Band(number, len(regions), each) for number, each in enumerate(regions, 1)]


def _handed(regions: Sequence[Region]) -> tuple[tuple[float, float], ...]:
    """The regions a tool's module is handed: none for a page one image shows whole, so it
    draws that image as it always has, and each band otherwise."""
    return tuple((top, height) for top, height in regions) if len(regions) > 1 else ()


def pixels(length: float, scale: float) -> int:
    """How many pixels of an image `length` px take at `scale` pixels to a px, whole."""
    return math.ceil(round(length * scale, 6))


def _smallest_text(page: Mapping[str, Any]) -> float | None:
    """The size of `page`'s smallest text in px, or None where it holds none."""
    sizes = [
        float(run["font-size"])
        for element in _elements(page)
        for paragraph in element.get("paragraphs") or ()
        for run in paragraph
        if run.get("font-size")
    ]
    return min(sizes) if sizes else None


def scale(page: Mapping[str, Any]) -> float:
    """How many pixels of its image a px of `page` asks: `LONG_EDGE` on its long edge, or more
    where its smallest text would land under `SMALLEST_TEXT` (DEC-015 point 5). 1 for a page
    with no size, which is refused, naming its measure."""
    edge = max(float(page["width"]), float(page["height"]))
    if edge <= 0:
        return 1.0
    found = LONG_EDGE / edge
    smallest = _smallest_text(page)
    if smallest is not None:
        found = max(found, SMALLEST_TEXT / smallest)
    return found


def page_scale(page: Mapping[str, Any]) -> float:
    """How many pixels of its images a px of `page` takes through the SVG renderer: what it
    asks (`scale`), or, where its width would then pass `LONG_EDGE`, as many as let its width
    fill it, so its smallest text may not read (DEC-022 point 7)."""
    found = scale(page)
    width = float(page["width"])
    if width > 0 and pixels(width, found) > LONG_EDGE:
        return LONG_EDGE / width
    return found


def device_scale(pages: Sequence[Mapping[str, Any]]) -> float:
    """The device scale one browser start draws `pages` at: the largest `scale` any of them
    asks, since a browser's flag binds a whole start (DEC-020 point 5), rounded up to
    `SCALE_PLACES` decimals. Where the widest page would then pass `LONG_EDGE`, as many as let
    its width fit it, rounded down (DEC-022 point 7)."""
    places = 10**SCALE_PLACES
    found = math.ceil(round(max(scale(page) for page in pages) * places, 6)) / places
    widest = max(float(page["width"]) for page in pages)
    if widest > 0:
        fits = math.floor(round(LONG_EDGE / widest * places, 6)) / places
        found = min(found, max(fits, 1 / places))
    return found


def too_wide(page: Mapping[str, Any], scale: float) -> bool:
    """Whether `page` drawn at `scale` pixels to a px sets its smallest text under
    `SMALLEST_TEXT`: only a page too wide for one image whose smallest text reads is drawn so
    small (DEC-022 point 7)."""
    smallest = _smallest_text(page)
    return smallest is not None and round(smallest * scale, 6) < SMALLEST_TEXT


def bands(page: Mapping[str, Any], scale: float) -> tuple[Region, ...]:
    """The regions of `page` an image each shows at `scale` pixels to a px, top to bottom: the
    whole page, where its height fits `LONG_EDGE`, or else its bands (DEC-022 point 7).

    Each band is as wide as the page, and as tall as `LONG_EDGE` allows at most. The bands are
    of about one height, so none is a sliver. Each overlaps the next by the page's tallest
    line, and at most by `MOST_OVERLAP` of a band, so a line lies whole in one band. A band
    ends where the overlap holds a gap between elements, in the middle of the lowest gap
    there, and at the overlap's bottom otherwise. A gap is a strip no element's frame covers,
    but a page's ground."""
    height = float(page["height"])
    if height <= 0 or pixels(height, scale) <= LONG_EDGE:
        return (Region(0.0, height),)
    most = _floored(LONG_EDGE / scale)
    overlap = min(_tallest_line(page), most * MOST_OVERLAP)
    covered = _covered(page)
    found = []
    top = 0.0
    while height - top > most:
        left = height - top
        count = math.ceil((left - overlap) / (most - overlap))
        bottom = top + min(most, (left + (count - 1) * overlap) / count)
        cut = _cut(covered, bottom - overlap, bottom)
        found.append(Region(top, round(cut - top, BAND_PLACES)))
        top = max(_floored(cut - overlap), top + 10**-BAND_PLACES)
    found.append(Region(top, round(height - top, BAND_PLACES)))
    return tuple(found)


def _floored(length: float) -> float:
    """`length` rounded down to `BAND_PLACES` decimals."""
    places = 10**BAND_PLACES
    return math.floor(round(length * places, 6)) / places


def _tallest_line(page: Mapping[str, Any]) -> float:
    """The line height of `page`'s tallest line, in px, 0 where it holds no text."""
    return max(
        (
            float(element.get("line-height") or 0)
            for element in _elements(page)
            if element.get("type") == "text"
        ),
        default=0.0,
    )


def _covered(page: Mapping[str, Any]) -> list[tuple[float, float]]:
    """The strips of `page`'s height the frames of its drawn elements cover, top to bottom, each
    from its top to its bottom, those that touch joined. A group draws nothing, and a box over
    the whole page is its ground, which covers no gap."""
    width, height = float(page["width"]), float(page["height"])
    spans = []
    for element, x, y in _placed(page):
        wide, tall = float(element.get("width", 0)), float(element.get("height", 0))
        ground = x <= 0 and y <= 0 and x + wide >= width and y + tall >= height
        if element.get("type") == "group" or (element.get("type") == "box" and ground):
            continue
        spans.append((y, y + tall))
    joined: list[tuple[float, float]] = []
    for top, bottom in sorted(spans):
        if joined and top <= joined[-1][1]:
            joined[-1] = (joined[-1][0], max(joined[-1][1], bottom))
        else:
            joined.append((top, bottom))
    return joined


def _cut(covered: Sequence[tuple[float, float]], low: float, high: float) -> float:
    """Where a band ends whose overlap with the next runs from `low` to `high`: in the middle
    of the lowest gap between `covered` strips there, or at `high` where it holds none."""
    gaps = []
    start = low
    for top, bottom in covered:
        if bottom < start:
            continue
        if top > high:
            break
        if top > start:
            gaps.append((start, top))
        start = max(start, bottom)
    if start < high:
        gaps.append((start, high))
    for begin, end in reversed(gaps):
        middle = _floored((begin + end) / 2)
        if begin < middle < end:
            return middle
    return _floored(high)


def line_widths(page: Mapping[str, Any]) -> dict[str, list[float]]:
    """The width the engine measured of each line of each text of `page`, by its trace id."""
    return {
        element["id"]: [float(line["width"]) for line in element["lines"]]
        for element in _elements(page)
        if element.get("lines")
    }


def _placed(page: Mapping[str, Any]) -> Iterator[tuple[Mapping[str, Any], float, float]]:
    """Each element of `page`, with where its frame's corner lies in the page: a scene
    holds a frame relative to its parent (`components.md`, What a scene holds)."""

    def walk(
        parent: Mapping[str, Any], x: float, y: float
    ) -> Iterator[tuple[Mapping[str, Any], float, float]]:
        for child in parent.get("children", []):
            left, top = x + float(child.get("x", 0)), y + float(child.get("y", 0))
            yield child, left, top
            yield from walk(child, left, top)

    return walk(page, 0.0, 0.0)


def frames(
    page: Mapping[str, Any], width: int, height: int, region: Region | None = None
) -> list[dict[str, Any]]:
    """Each element's frame in the pixels of an image of `width` by `height`, with its trace
    id, the page's own first, in drawing order (DEC-015 point 5). Of a band, `region`, each
    element the band shows, a part of it or the whole, in the band's own pixels, so a frame a
    cut crosses reaches past the image (DEC-022 point 7)."""
    top, tall = (0.0, float(page["height"])) if region is None else region
    across, down = width / float(page["width"]), height / tall

    def frame(element: Mapping[str, Any], x: float, y: float) -> dict[str, Any]:
        return {
            "id": element["id"],
            "type": element.get("type"),
            "x": round(x * across, 2),
            "y": round((y - top) * down, 2),
            "width": round(float(element.get("width", 0)) * across, 2),
            "height": round(float(element.get("height", 0)) * down, 2),
        }

    def shows(element: Mapping[str, Any], y: float) -> bool:
        bottom, reach = top + tall, float(element.get("height", 0))
        return region is None or (y < bottom and y + reach > top if reach else top <= y <= bottom)

    placed = (frame(each, x, y) for each, x, y in _placed(page) if shows(each, y))
    return [frame(page, 0.0, 0.0), *placed]


def drawn_otherwise(page: Mapping[str, Any]) -> Iterator[dict[str, Any]]:
    """Each run of `page` the engine measured in more than one family, which the tool may
    draw otherwise than a browser does (DEC-015 point 2): it may set the whole run on a line
    in the family that holds the character the first one lacks."""
    for element in _elements(page):
        for paragraph in element.get("paragraphs") or ():
            for run in paragraph:
                families = [face.get("family") for face in run.get("fonts", [])]
                if len(set(families)) > 1:
                    yield {"element": element["id"], "text": run.get("text"), "families": families}


#: What the report says of a picture the SVG renderer's page shows with a colour profile.
WITHOUT_PROFILE = (
    "the tool may draw the picture without the colour profile it carries, so its colours "
    "may differ from those a browser draws by it"
)


def with_profiles(
    page: Mapping[str, Any], handed: Mapping[str, seam.Shown]
) -> Iterator[dict[str, Any]]:
    """Each picture `page` shows that carries a colour profile, as it is `handed` to the
    renderer, which the tool may draw without it (DEC-025 point 5, DEC-015 point 3): its
    image's trace id and the name of the file it shows. A file the reader cannot read names
    no profile here: the check names why."""
    for element in _elements(page):
        shown = handed.get(str(element.get("id"))) if element.get("type") == "image" else None
        if shown is None:
            continue
        try:
            read = pictures.read(shown.file.read_bytes(), shown.file.name)
        except (OSError, ValueError, pictures.Refused):
            continue
        if read.profile is not None:
            yield {"element": element["id"], "picture": shown.file.name, "why": WITHOUT_PROFILE}


def write(root: Path, folder: str, viewed: Viewed) -> str:
    """Replace `folder`, a renderer's folder relative to `root` (`folder_of`), by what `viewed`
    holds, as one change, and give it. No other folder is touched. Raises Refused where it is
    reached through a link, and WriteFailed."""
    path = root / folder
    pl.writable(root, path / REPORT)
    change = files.Change(root)
    if path.is_dir():
        change.replace_folder(path, viewed.files)
    else:
        change.add_folder(path, viewed.files)
    change.commit()
    return f"{folder}/"


def _json(data: Mapping[str, Any]) -> bytes:
    return (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
