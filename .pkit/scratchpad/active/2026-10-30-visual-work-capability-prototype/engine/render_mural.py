"""`mural`: a mural-boards map file (plain `objects:`, every geometry computed) for one language.

The scene is laid out with the brand's `mural` font profile: proxima-nova measured by estimate (no
file of it exists to measure), Mural wrapping each text itself within the measured width. A
component whose texts are all in a font Mural lacks (`render: image`, the monospace font) is drawn
as one PNG through the SVG renderer and rsvg-convert, as point 5 decided; inline code stays text in
proxima-nova, a declared loss. A tinted picture is drawn to a PNG in its colour. Images go to a
folder beside the map. Nothing is pushed: the mural-boards tool does that.
"""

from __future__ import annotations

import re
import subprocess
import tempfile
from html import escape
from pathlib import Path

import yaml

from .export import RSVG, font_env
from .model import EngineError
from .render_svg import SvgPage
from .scene import build

AREA_GAP = 400
ALIGN = {"start": "left", "center": "center", "end": "right"}


def colour8(hex_colour: str) -> str:
    return hex_colour.upper() + "FF"


def safe(part: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", part).strip("-.") or "x"


class MuralPage:
    def __init__(self, piece, scene, page, tokens, area_id, images_dir: Path, map_dir: Path, workdir: Path, env):
        self.piece, self.scene, self.page, self.tokens = piece, scene, page, tokens
        self.area_id, self.images_dir, self.map_dir, self.workdir, self.env = area_id, images_dir, map_dir, workdir, env
        self.objects: dict[str, dict] = {}
        self.stack = 0

    def colour(self, role):
        return colour8(self.tokens.colour(role)) if role else None

    def key(self, node_id: str) -> str:
        return f"{self.area_id}.{safe(node_id.split('/', 1)[1] if '/' in node_id else node_id)}"

    def add(self, key, obj):
        self.stack += 1
        obj = {**obj, "parent": self.area_id, "stack": self.stack}
        self.objects[key] = obj

    def visit(self, node, x=0.0, y=0.0):
        if node["type"] == "group":
            if node.get("component") and self.all_image_text(node):
                self.picture(node, x + node["x"], y + node["y"])
                return
            for child in node["children"]:
                self.visit(child, x + node["x"], y + node["y"])
            return
        getattr(self, node["type"])(node, x, y)

    @staticmethod
    def texts(node):
        if node["type"] == "text":
            yield node
        for child in node.get("children", []):
            yield from MuralPage.texts(child)

    def all_image_text(self, node) -> bool:
        texts = list(self.texts(node))
        return bool(texts) and all(t["font"]["render"] == "image" for t in texts)

    def frame(self, node, x, y):
        return {"x": round(x + node["x"]), "y": round(y + node["y"]),
                "width": max(round(node["width"]), 1), "height": max(round(node["height"]), 1)}

    def box(self, node, x, y, shape="rectangle"):
        if not node.get("fill") and not node.get("stroke"):
            return
        fill = self.colour(node.get("fill")) or "#FFFFFF00"
        obj = {"type": "shape", "shape": shape, "text": "", **self.frame(node, x, y), "color": fill}
        if node.get("stroke"):
            obj["border_color"] = self.colour(node["stroke"])
            obj["border_width"] = min(max(round(node["stroke_width"]), 1), 7)
            obj["border_style"] = "dashed" if node.get("dash") else "solid"
        else:
            obj["border_color"] = fill
            obj["border_width"] = 1
        self.add(self.key(node["id"]), obj)

    def ellipse(self, node, x, y):
        self.box(node, x, y, shape="ellipse")

    def line(self, node, x, y):
        pts = [[round(x + a), round(y + b)] for a, b in node["points"]]
        tips = node.get("tips", "none")
        if tips == "start":
            pts, tips = pts[::-1], "end"
        self.add(self.key(node["id"]), {"type": "arrow", "points": pts, "arrow_type": "straight", "tip": tips,
                                        "color": self.colour(node["stroke"]), "border_width": min(max(round(node["stroke_width"]), 1), 7),
                                        "border_style": "dashed" if node.get("dash") else "solid"})

    def text(self, node, x, y):
        font = node["font"]
        runs = [run for line in node["lines"] for run in line["runs"]]
        fills = {run["fill"] for run in runs}
        obj = {"type": "text", **self.frame(node, x, y), "font": font["family"], "font_size": round(font["size"]),
               "align": ALIGN.get(node.get("align", "start"), "left")}
        if len(fills) <= 1:
            obj["text"] = node.get("source") or "\n".join("".join(r["text"] for r in line["runs"]) for line in node["lines"])
            if fills:
                obj["ink"] = self.colour(next(iter(fills)))
        else:  # runs in several colours travel as spans, as the Friday talk's map did
            divs = []
            for line in node["lines"]:
                spans = "".join(f'<span style="color:{self.colour(r["fill"])[:7]}">{escape(r["text"], quote=False).replace("  ", "&nbsp; ")}</span>'
                                for r in line["runs"] if r["text"])
                divs.append(f"<div>{spans or '<br>'}</div>")
            obj["html"] = '<html v="1">' + "".join(divs) + "</html>"
            obj["text"] = "\n".join("".join(r["text"] for r in line["runs"]) for line in node["lines"])
        self.add(self.key(node["id"]), obj)

    def image(self, node, x, y):
        self.picture(node, x, y)

    def picture(self, node, x, y):
        """Draw a node (a component group or a picture) to a PNG beside the map."""
        w, h = node["width"], node["height"]
        local = {**node, "x": 0, "y": 0}
        page = {"id": self.page["id"], "width": w, "height": h, "root": {"type": "group", "id": node["id"], "x": 0, "y": 0, "width": w, "height": h, "children": [local]}}
        svg = SvgPage(self.scene, page, self.tokens, self.piece.root, scale=1.0, embed_fonts=False).render()
        name = safe(self.key(node["id"])) + ".png"
        src = self.workdir / (name + ".svg")
        src.write_text(svg, encoding="utf-8")
        target = self.images_dir / name
        done = subprocess.run([RSVG, "-w", str(round(2 * w)), "-h", str(round(2 * h)), "-o", str(target), str(src)],
                              env=self.env, capture_output=True, text=True)
        if done.returncode != 0:
            raise EngineError(f"rsvg-convert failed: {done.stderr.strip()}")
        self.add(self.key(node["id"]), {"type": "image", "file": target.relative_to(self.map_dir).as_posix(), **self.frame(node, x, y)})


def run(piece, lang, out: Path, board: str, mode: str | None, profile_for) -> int:
    if lang not in piece.languages:
        raise EngineError(f"piece {piece.name} has no language {lang!r}; it has {piece.languages}")
    if not re.match(r"^[A-Za-z0-9_-]+\.[0-9]+$", board):
        raise EngineError(f"--board must be <workspace>.<number>, not {board!r}")
    brand, _ = piece.brand()
    mode = mode or f"{brand.default_theme}/{next(iter(brand.themes[brand.default_theme]))}"
    profile = profile_for(brand, "mural")
    problems = []
    scene = build(piece, lang, piece.brand_entry, profile, problems)
    tokens = brand.tokens(profile, mode)
    out = out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    images_dir = out.parent / f"{out.stem}-images"
    images_dir.mkdir(exist_ok=True)
    fonts = {Path(piece.root / n["font"]["measured"]["file"]).parent
             for p in scene["pages"] for n in MuralPage.texts(p["root"]) if n["font"]["measured"].get("by") == "file"}
    objects: dict[str, dict] = {}
    with tempfile.TemporaryDirectory(prefix="visual-mural-") as tmp:
        env = font_env(sorted(fonts), Path(tmp))
        for i, page in enumerate(scene["pages"]):
            area = safe(f"{piece.name}.{page['id']}")
            title = next((n for n in MuralPage.texts(page["root"]) if n["id"].endswith("/title")), None)
            label = "".join(r["text"] for r in title["lines"][0]["runs"]) if title and title["lines"] else page["id"]
            objects[area] = {"type": "area", "title": f"{page['number']} · {label}", "show_title": False,
                             "x": i * (round(page["width"]) + AREA_GAP), "y": 0,
                             "width": round(page["width"]), "height": round(page["height"]),
                             "color": "#FFFFFF00", "border_color": "#FFFFFF00", "border_width": 1, "outline": i + 1}
            mp = MuralPage(piece, scene, page, tokens, area, images_dir, out.parent, Path(tmp), env)
            mp.visit(page["root"])
            objects.update(mp.objects)
    data = {"schema": "mural-boards/1", "mural": board, "objects": objects}
    header = (f"# {piece.name} in {lang}, drawn by visual.py from its content ({brand.name} {mode}, font profile {profile}).\n"
              f"# Generated: edit the piece, not this file. Pictures are in {images_dir.name}/.\n")
    out.write_text(header + yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=1000), encoding="utf-8")
    print(f"mural: {len(objects)} objects ({sum(1 for o in objects.values() if o['type'] == 'image')} images) in {out}")
    for kind, where, message in problems:
        print(f"{kind} {where}: {message}")
    return 1 if problems else 0
