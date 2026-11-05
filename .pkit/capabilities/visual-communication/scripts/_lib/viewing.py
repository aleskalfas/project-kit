"""The viewing step: a piece's drawn pages as images a person or an agent reads
(visual-communication DEC-015).

It is no plugin, no render and no export. It uses the seam from the engine's side, as
render and export do, and adds nothing to it. Only a person or an agent reads what it
writes, never a check, an export or a producer. So nothing here moves a lock, keeps a
finding or takes a number, no helper or producer runs, and a produced picture is drawn as it
stands, stale or not.

- **Under the lock.** It reads the piece's own file with its lock and computes the scenes
  under it. A piece with no lock, or a lock that does not hold, is refused (`opened`).
- **What it draws.** The caller picks pages, languages and keys (`Asked`). By default it
  draws every page in the source language, in the first key in the order a picture's
  variant uses (`keys.variant_key`).
- **The images.** `viewing_tool` draws each page, at `LONG_EDGE` pixels on its long edge,
  or more where the page's smallest text would land under `SMALLEST_TEXT`.
- **Beside them,** in `FOLDER/<piece>/` of the clone's local folder: each image's frames,
  and one report of what the images cannot show as the renderer set it (DEC-015 point 3).
- **A run replaces** what an earlier run left for the piece, as one change (`write`).
"""

from __future__ import annotations

import json
import math
import tempfile
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from _lib import checks, files, keys, libraries, location, tokens, viewing_tool
from _lib import pipeline as pl
from _lib.env import MissingFont
from _lib.plugins import seam
from _lib.root import LOCAL
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

#: The scenes of a piece, by language.
Results = Sequence[tuple[str, SceneResult]]


@dataclass(frozen=True)
class Asked:
    """What a run draws: its languages and keys, and each page by its number or trace id,
    every page where none is named."""

    languages: tuple[str, ...]
    keys: tuple[str, ...]
    pages: tuple[str, ...] = ()


@dataclass(frozen=True)
class Viewed:
    """What a run gives: each file of the piece's folder, by name, and its report."""

    files: dict[str, bytes]
    report: dict[str, Any]


def opened(root: Path, name: str) -> pl.Project:
    """The piece `name` under the lock its `piece.yaml` holds. Raises Refused where it has
    no lock, its lock does not hold, or its brand cannot be read."""
    found = location.for_reading(root)
    if found is None:
        raise pl.Refused(f"the project holds no visual work, so no piece `{name}`")
    piece = pl.read_piece(root, found.path, name)
    held = libraries.Held(root, found.path)
    faults = checks.lock_findings(held, piece)
    if faults:
        said = "; ".join(checks.said(finding) for finding in faults)
        raise pl.Refused(f"the lock of {piece.file(pl.PIECE_FILE)} cannot be drawn: {said}")
    try:
        return pl.Project(piece, piece.lock, held)
    except tokens.TokenError as exc:
        said = "; ".join(finding.message for finding in exc.findings)
        raise pl.Refused(f"the brand of `{name}` cannot be read: {said}") from exc


def scenes(project: pl.Project, languages: Sequence[str]) -> list[tuple[str, SceneResult]]:
    """The scenes of `languages`, computed under the lock. Raises Refused where a font
    cannot measure the text."""
    try:
        return project.scenes(languages)
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
) -> Asked:
    """What a caller's choices ask of `project`. Raises Refused for a language or a key the
    piece does not name, naming those it does."""
    piece = project.piece
    held = piece.languages
    chosen = _chosen(languages, held, "language", piece.name, every_language) or held[:1]
    named = _chosen(named_keys, project.keys, "key", piece.name, every_key)
    return Asked(tuple(chosen), tuple(named or [first_key(project)]), tuple(pages))


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
    """The images, the frames and the report of a run. Writes only the page's faces, in a
    temporary folder of the clone's local folder, which it removes (DEC-015 point 2). Raises
    Refused for a page the scene does not hold, or that the tool cannot draw."""
    shown = {
        language: (scene := result.scene.to_dict(), _numbers(scene, wanted.pages))
        for language, result in results
    }
    local = project.root / LOCAL
    local.mkdir(parents=True, exist_ok=True)
    made = _Made(project)
    with tempfile.TemporaryDirectory(prefix="faces-", dir=local) as faces:
        for language, key, drawn in pl.drawn(project, results, "svg", wanted.keys):
            scene, numbers = shown[language]
            for number in numbers:
                made.add(scene, language, key, number, drawn, Path(faces))
            made.lost(scene, language, key, numbers, drawn.losses)
    return made.viewed()


class _Made:
    """What a run has drawn so far."""

    def __init__(self, project: pl.Project) -> None:
        self.project = project
        self.document = project.values()
        self.files: dict[str, bytes] = {}
        self.images: list[dict[str, Any]] = []
        self.dropped: list[dict[str, Any]] = []
        self.otherwise: list[dict[str, Any]] = []
        self.losses: list[dict[str, Any]] = []

    def add(
        self,
        scene: Mapping[str, Any],
        language: str,
        key: str,
        number: int,
        drawn: Any,
        faces: Path,
    ) -> None:
        """One page of one language and key: its image and its frames, and what the report
        says of it."""
        piece = self.project.piece.name
        page = pages_of(scene)[number - 1]
        at = {"language": language, "key": key, "page": page["id"]}
        try:
            image = viewing_tool.draw(drawn.pages[number - 1].svg, long_edge(page), faces)
        except viewing_tool.ToolFailed as exc:
            raise pl.Refused(
                f"the tool cannot draw page {page['id']} of `{piece}`: {exc}. "
                f"`pkit visual check {piece}` names what the piece still owes"
            ) from exc
        total = len(drawn.pages)
        stem = f"{piece}.{language}.{key}" + (f".{number}" if total > 1 else "")
        self.files[f"{stem}.png"] = image.image
        self.files[f"{stem}.frames.json"] = _json(
            {
                **at,
                "number": number,
                "image": f"{stem}.png",
                "pixels": {"width": image.width, "height": image.height},
                "lock": self.project.lock,
                "elements": frames(page, image.width, image.height),
            }
        )
        self.images.append(
            {
                **at,
                "number": number,
                "image": f"{stem}.png",
                "frames": f"{stem}.frames.json",
                "pixels": {"width": image.width, "height": image.height},
                "on-white": not draws_ground(page, pl.colours_at(self.document, key)),
            }
        )
        self.dropped.extend(
            {**at, "element": each.element, "text": each.text, "whole": each.whole}
            for each in image.dropped
        )
        self.otherwise.extend({**at, **each} for each in drawn_otherwise(page))

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
        declared = seam.declaration("svg", seam.RENDERER)
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

    def viewed(self) -> Viewed:
        report = {
            "piece": self.project.piece.name,
            "lock": self.project.lock,
            "tool": viewing_tool.TOOL,
            "images": self.images,
            "dropped": self.dropped,
            "losses": self.losses,
            "drawn-otherwise": self.otherwise,
        }
        return Viewed({**self.files, REPORT: _json(report)}, report)


def long_edge(page: Mapping[str, Any]) -> int:
    """How many pixels the long edge of `page`'s image takes (DEC-015 point 5)."""
    edge = max(float(page["width"]), float(page["height"]))
    sizes = [
        float(run["font-size"])
        for element in _elements(page)
        for paragraph in element.get("paragraphs") or ()
        for run in paragraph
        if run.get("font-size")
    ]
    scale = max(LONG_EDGE / edge, SMALLEST_TEXT / min(sizes, default=SMALLEST_TEXT))
    return math.ceil(edge * scale)


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
    frame. Where it draws none, its image lies on white, which the piece never set (DEC-015
    point 5)."""
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
    draw otherwise than a browser does (DEC-015 point 2): it may set the whole line in the
    family that holds the character the first one lacks."""
    for element in _elements(page):
        for paragraph in element.get("paragraphs") or ():
            for run in paragraph:
                families = [face.get("family") for face in run.get("fonts", [])]
                if len(set(families)) > 1:
                    yield {"element": element["id"], "text": run.get("text"), "families": families}


def write(root: Path, name: str, viewed: Viewed) -> str:
    """Replace the piece's folder by what `viewed` holds, as one change, and give the folder,
    relative to `root`. Raises Refused where it is reached through a link, and WriteFailed."""
    folder = root / FOLDER / name
    pl.writable(root, folder / REPORT)
    change = files.Change(root)
    if folder.is_dir():
        change.replace_folder(folder, viewed.files)
    else:
        change.add_folder(folder, viewed.files)
    change.commit()
    return f"{FOLDER}/{name}/"


def _json(data: Mapping[str, Any]) -> bytes:
    return (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
