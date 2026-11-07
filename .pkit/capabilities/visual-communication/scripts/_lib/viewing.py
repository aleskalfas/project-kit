"""The viewing step: a piece's drawn pages as images a person or an agent reads
(visual-communication DEC-015, DEC-020 point 5).

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
- **The HTML renderer's pages.** `viewing_browser` draws each page file as the renderer wrote
  it, in one browser start, its pages at one device scale, the largest any of them asks. A
  file holds every key its group gives it, whichever keys the caller picks, and the start
  draws each key picked out of it, with no reload: the step takes each key's signals from the
  renderer's declaration (`signals_of`) and the browser's module sets them (DEC-023 point 6).
  The browser is the one the configuration names (`browser_named`), or else the first found
  where Chrome and Chromium install themselves. Its profile lies in the clone's local folder,
  and the module removes it.
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
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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

#: How many decimals a browser's device scale keeps, rounded up, so its flag names it whole.
SCALE_PLACES = 3

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
    page where none is named, and the renderer it reads them through."""

    languages: tuple[str, ...]
    keys: tuple[str, ...]
    pages: tuple[str, ...] = ()
    renderer: str = SVG


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
) -> Asked:
    """What a caller's choices ask of `project`. Raises Refused for a language or a key the
    piece does not name, naming those it does, and for a renderer the step does not read."""
    piece = project.piece
    if renderer is not None and renderer not in RENDERERS:
        raise pl.Refused(
            f"the viewing step reads no renderer `{renderer}`: it reads "
            f"{' and '.join(f'`{each}`' for each in RENDERERS)}"
        )
    held = piece.languages
    chosen = _chosen(languages, held, "language", piece.name, every_language) or held[:1]
    named = _chosen(named_keys, project.keys, "key", piece.name, every_key)
    return Asked(
        tuple(chosen),
        tuple(named or [first_key(project)]),
        tuple(pages),
        renderer or renderer_of(piece),
    )


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
    whether the configuration names it, and where the step looked where it found none.
    Starts nothing. Raises Refused where the configuration cannot be read."""
    named = browser_named(root)
    try:
        program = viewing_browser.find(named)
    except viewing_browser.Stopped as stop:
        return {"program": None, "named": named is not None, "looked": list(stop.looked)}
    return {"program": str(program), "named": named is not None, "looked": []}


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
    scale they share, and each key drawn out of it with its signals, in the order of its keys."""

    name: str
    language: str
    keys: tuple[str, ...]
    document: bytes
    scene: Mapping[str, Any]
    numbers: list[int]
    scale: float
    modes: Mapping[str, Mapping[str, str]]


def _through_a_browser(
    project: pl.Project, results: Results, wanted: Asked, shown: _Shown, local: Path
) -> Viewed:
    """The HTML renderer's page files, each drawn as it was written, in one browser start
    (DEC-020 points 5 and 8). Every refusal comes before a file is written. A stop gives the
    page files and a report that says what stopped it, and no image."""
    made = _Made(project, HTML)
    declared = seam.declaration(HTML, seam.RENDERER)
    combinations = dict(zip(project.keys, project.combinations, strict=True))
    planned = []
    for language, held, drawn in pl.drawn(project, results, HTML, wanted.keys):
        scene, numbers = shown[language, project.size_key(held[0])]
        every = pages_of(scene)
        scale = device_scale([every[number - 1] for number in numbers])
        for number in numbers:
            _refuse_a_size(project, every[number - 1], scale)
        name = f"{project.piece.name}.{language}.{held[0]}.html"
        modes = {
            key: signals_of(declared, HTML, combinations[key]) for key in held if key in wanted.keys
        }
        planned.append(
            _PageFile(name, language, held, drawn.document, scene, numbers, scale, modes)
        )
        made.page_file(language, held, name, drawn.document)
        for key in modes:
            lost = [loss for loss in drawn.losses if loss.key in (None, key)]
            made.lost(scene, language, key, numbers, lost)
    named = browser_named(project.root)
    local.mkdir(parents=True, exist_ok=True)
    try:
        program = viewing_browser.find(named)
        with tempfile.TemporaryDirectory(prefix="page-files-", dir=local) as held:
            drawings = [(each, _drawn(each, Path(held), program, local)) for each in planned]
    except viewing_browser.Stopped as stop:
        return made.stopped(stop)
    for each, drawing in drawings:
        made.through(each, drawing, program)
    return made.viewed()


def _drawn(planned: _PageFile, folder: Path, program: Path, local: Path) -> viewing_browser.Drawing:
    """One page file through the browser `program`, written in `folder` under its own name
    with the renderer's bytes, so the browser reads it as the renderer wrote it, each key
    drawn in its signals. The browser's profile lies in `local`, which the module removes.
    Raises Stopped."""
    file = folder / planned.name
    file.write_bytes(planned.document)
    pages = [browser_page(pages_of(planned.scene)[number - 1]) for number in planned.numbers]
    signals = signals_read(seam.declaration(HTML, seam.RENDERER), HTML)
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


def browser_page(page: Mapping[str, Any]) -> viewing_browser.Page:
    """`page` as the browser's reads take it: its trace id and size, and each of its texts in
    the tree's order, with the spans of each line."""
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
    return viewing_browser.Page(page["id"], float(page["width"]), float(page["height"]), texts)


def _refuse_a_size(project: pl.Project, page: Mapping[str, Any], scale: float) -> None:
    """Refuse a page with no size, or one past `viewing_tool.MOST_PIXELS` at `scale` device
    pixels to a px, as the SVG renderer's pages are refused, before the browser is asked."""
    width, height = float(page["width"]), float(page["height"])
    if min(width, height) <= 0:
        said = f"the page measures {width:g} by {height:g} px"
    elif width * height * scale**2 > viewing_tool.MOST_PIXELS:
        said = (
            f"at {scale:g} device pixels to a px the page takes more than "
            f"{viewing_tool.MOST_PIXELS}"
        )
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
    """What a run has drawn so far, through `renderer`."""

    def __init__(self, project: pl.Project, renderer: str) -> None:
        self.project = project
        self.renderer = renderer
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
        """One page of the SVG renderer's, of one language and key: its image and its frames,
        and what the report says of it, each picture `handed` that carries a colour profile
        among it."""
        page = pages_of(scene)[number - 1]
        at = {"language": language, "key": key, "page": page["id"]}
        try:
            image = viewing_tool.draw(
                drawn.pages[number - 1].svg, long_edge(page), faces, line_widths(page)
            )
        except viewing_tool.ToolFailed as exc:
            raise _cannot_draw(self.project, page, "the tool", str(exc)) from exc
        self._image(scene, language, key, number, image.image, image.width, image.height)
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
        """The pages of one page file a browser drew, in each key drawn out of it: each image and
        its frames, and what the report says of them (DEC-020 point 6, DEC-023 point 6)."""
        name, _, version = drawing.browser.partition("/")
        self.tool = {"name": name, "version": version, "program": str(program)}
        for key, shown in zip(planned.modes, drawing.shown, strict=True):
            self._through_in(planned, key, shown)

    def _through_in(self, planned: _PageFile, key: str, shown: viewing_browser.Shown) -> None:
        """The pages of one page file a browser drew in the key `key`."""
        numbers = {pages_of(planned.scene)[number - 1]["id"]: number for number in planned.numbers}
        for image in shown.images:
            self._image(
                planned.scene,
                planned.language,
                key,
                numbers[image.page],
                image.image,
                image.width,
                image.height,
            )
        where = {"language": planned.language, "key": key}
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
    ) -> None:
        """One page's image, its frames, and its entry in the report."""
        piece = self.project.piece.name
        every = pages_of(scene)
        page = every[number - 1]
        at = {"language": language, "key": key, "page": page["id"]}
        stem = f"{piece}.{language}.{key}" + (f".{number}" if len(every) > 1 else "")
        self.files[f"{stem}.png"] = image
        self.files[f"{stem}.frames.json"] = _json(
            {
                **at,
                "number": number,
                "image": f"{stem}.png",
                "pixels": {"width": width, "height": height},
                "lock": self.project.lock,
                "elements": frames(page, width, height),
            }
        )
        ground = draws_ground(page, pl.colours_at(self.document, key))
        self.images.append(
            {
                **at,
                "number": number,
                "image": f"{stem}.png",
                "frames": f"{stem}.frames.json",
                "pixels": {"width": width, "height": height},
                ON_WHITE if self.renderer == SVG else ON_BROWSER_GROUND: not ground,
            }
        )

    def lost(
        self,
        scene: Mapping[str, Any],
        language: str,
        key: str,
        numbers: Sequence[int],
        losses: Sequence[seam.Loss],
    ) -> None:
        """Each loss of the pages drawn, known before the renderer ran or reported as it
        drew, whether or not the piece accepts it (DEC-015 point 3)."""
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
                        "plugin": loss.plugin,
                        "what": loss.what,
                        "did": loss.did,
                        "why": loss.why,
                        "accepted": checks.accepted(loss, self.project.piece.accepted_losses),
                    }
                )

    def stopped(self, stop: viewing_browser.Stopped) -> Viewed:
        """What a stop gives: the page files, and a report that says what stopped the browser,
        what is missing and how to go on, and no image (DEC-020 point 8, DEC-024 point 4)."""
        self.stop = {
            "what": stop.what,
            "looked": list(stop.looked),
            "program": stop.program,
            "said": stop.said,
            "sandbox": stop.sandbox,
            "as-root": stop.as_root,
            "go-on": ways_on(self.project.piece.name),
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
        report["stopped"] = self.stop
        report["page-files"] = self.page_files
        report.update(images=self.images, words=self.words, dropped=self.dropped)
        report["losses"] = self.losses
        report["drawn-otherwise"] = self.otherwise
        report["refused"] = self.refused
        return Viewed({**self.files, REPORT: _json(report)}, report, self.stop is not None)


#: What an agent does where a look stops: it opens no way out of the sandbox itself (DEC-024
#: point 6). It names no way out, as no stop does (DEC-024 point 4).
FOR_AN_AGENT = (
    "read a pipeline's drawings where you can reach them, or ask a person, naming these ways "
    "on. Never take this command out of the sandbox yourself, and never run a look over the "
    "folder a person's run left"
)


def ways_on(piece: str) -> list[str]:
    """The ways on from a stop of `piece`'s HTML renderer's pages, in the order of DEC-024
    point 4: a build pipeline's drawings, a way a project may take, which show a pushed commit;
    the same look run by a person outside the sandbox, a line addressed to that person; and
    the SVG renderer's pages, which show the layout."""
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
    ]


def scale(page: Mapping[str, Any]) -> float:
    """How many pixels of its image a px of `page` takes: `LONG_EDGE` on its long edge, or more
    where its smallest text would land under `SMALLEST_TEXT` (DEC-015 point 5). 1 for a page
    with no size, which is refused, naming its measure."""
    edge = max(float(page["width"]), float(page["height"]))
    if edge <= 0:
        return 1.0
    sizes = [
        float(run["font-size"])
        for element in _elements(page)
        for paragraph in element.get("paragraphs") or ()
        for run in paragraph
        if run.get("font-size")
    ]
    found = LONG_EDGE / edge
    if sizes:
        found = max(found, SMALLEST_TEXT / min(sizes))
    return found


def device_scale(pages: Sequence[Mapping[str, Any]]) -> float:
    """The device scale one browser start draws `pages` at: the largest `scale` any of them
    asks, since a browser's flag binds a whole start (DEC-020 point 5), rounded up to
    `SCALE_PLACES` decimals."""
    largest = max(scale(page) for page in pages)
    places = 10**SCALE_PLACES
    return math.ceil(round(largest * places, 6)) / places


def long_edge(page: Mapping[str, Any]) -> int:
    """How many pixels the long edge of `page`'s image takes through the SVG renderer (DEC-015
    point 5)."""
    edge = max(float(page["width"]), float(page["height"]))
    if edge <= 0:
        return LONG_EDGE  # the tool refuses a page with no size, naming its measure
    return math.ceil(edge * scale(page))


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


def frames(page: Mapping[str, Any], width: int, height: int) -> list[dict[str, Any]]:
    """Each element's frame in the pixels of an image of `width` by `height`, with its trace
    id, the page's own first, in drawing order (DEC-015 point 5)."""
    across, down = width / float(page["width"]), height / float(page["height"])

    def frame(element: Mapping[str, Any], x: float, y: float) -> dict[str, Any]:
        return {
            "id": element["id"],
            "type": element.get("type"),
            "x": round(x * across, 2),
            "y": round(y * down, 2),
            "width": round(float(element.get("width", 0)) * across, 2),
            "height": round(float(element.get("height", 0)) * down, 2),
        }

    return [frame(page, 0.0, 0.0), *(frame(each, x, y) for each, x, y in _placed(page))]


def draws_ground(page: Mapping[str, Any], colours: Mapping[str, Mapping[str, Any]]) -> bool:
    """Whether `page` draws a ground of its own: a box of an opaque colour over its whole
    frame. Where it draws none, its image lies on white through the SVG renderer, and on the
    browser's own ground in the mode drawn through the HTML renderer, neither of which the
    piece set (DEC-015 point 5, DEC-023 point 7)."""
    width, height = float(page["width"]), float(page["height"])
    for element, x, y in _placed(page):
        colour = colours.get(element.get("fill") or "")
        if element.get("type") == "box" and colour and float(colour.get("alpha", 1)) >= 1:
            right, bottom = x + float(element["width"]), y + float(element["height"])
            if x <= 0 and y <= 0 and right >= width and bottom >= height:
                return True
    return False


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
