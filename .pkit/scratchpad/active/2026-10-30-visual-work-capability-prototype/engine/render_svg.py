"""The SVG renderer: one page of a scene, in one mode, as a standalone SVG.

Colours are resolved here, from the mode's tokens. Fonts are embedded, subset to the page's
characters, under their real family names; a renderer that cannot read embedded fonts (rsvg-convert)
finds the same names in the library's font folder. Every element carries its trace id (`data-id`),
and a component its name and the content it draws (`data-component`, `data-content`).
"""

from __future__ import annotations

import base64
import io
import logging
import math
from html import escape
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

from .scene import walk

logging.getLogger("fontTools.subset").setLevel(logging.ERROR)


def num(v) -> str:
    v = round(float(v), 2)
    return str(int(v)) if v == int(v) else f"{v:.2f}".rstrip("0")


def attr(**kv) -> str:
    out = []
    for k, v in kv.items():
        if v is None:
            continue
        out.append(f'{k.replace("_", "-")}="{escape(str(v), quote=True)}"')
    return " ".join(out)


_SUBSETS: dict = {}


def font_face_css(path: Path, family: str, weight: int, chars: set[str]) -> str:
    key = (str(path), "".join(sorted(chars)))
    if key not in _SUBSETS:
        font = TTFont(str(path), recalcTimestamp=False)
        options = subset.Options()
        options.layout_features = ["*"]
        options.name_IDs = ["*"]
        options.notdef_outline = True
        subsetter = subset.Subsetter(options)
        subsetter.populate(text="".join(sorted(chars)) + " ")
        subsetter.subset(font)
        buf = io.BytesIO()
        font.save(buf)
        fmt, mime = ("opentype", "font/otf") if font.sfntVersion == "OTTO" else ("truetype", "font/ttf")
        _SUBSETS[key] = (base64.b64encode(buf.getvalue()).decode("ascii"), fmt, mime)
    data, fmt, mime = _SUBSETS[key]
    return (f"@font-face{{font-family:'{family}';font-weight:{weight};"
            f"src:url(data:{mime};base64,{data}) format('{fmt}');}}")


class SvgPage:
    def __init__(self, scene: dict, page: dict, tokens, root: Path, scale: float = 0.5, embed_fonts: bool = True):
        self.scene, self.page, self.tokens, self.root = scene, page, tokens, Path(root)
        self.scale, self.embed_fonts = scale, embed_fonts
        self.defs: dict[str, str] = {}

    def colour(self, role):
        return self.tokens.colour(role) if role else None

    def render(self) -> str:
        body = self.node(self.page["root"])
        w, h = self.page["width"], self.page["height"]
        css = self.fonts_css()
        defs = "".join(self.defs[k] for k in sorted(self.defs))
        head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{num(w * self.scale)}" height="{num(h * self.scale)}" '
                f'viewBox="0 0 {num(w)} {num(h)}" {attr(data_piece=self.scene["piece"], data_page=self.page["id"], data_lang=self.scene["lang"], data_brand=self.scene["brand"], data_profile=self.scene["profile"])}>')
        style = f"<style>{css}text{{white-space:pre}}</style>" if css else "<style>text{white-space:pre}</style>"
        return head + "<defs>" + style + defs + "</defs>" + body + "</svg>\n"

    def fonts_css(self) -> str:
        if not self.embed_fonts:
            return ""
        faces: dict = {}
        for node, _, _, _ in walk(self.page["root"]):
            if node["type"] != "text":
                continue
            font = node["font"]
            measured = font["measured"]
            if measured.get("by") != "file":
                continue
            key = (measured["file"], font["family"], font["weight"])
            chars = faces.setdefault(key, set())
            for line in node["lines"]:
                for run in line["runs"]:
                    chars |= set(run["text"])
        return "".join(font_face_css(self.root / f, fam, wt, chars) for (f, fam, wt), chars in sorted(faces.items()))

    # ------------------------------------------------------------ nodes

    def node(self, n) -> str:
        kind = n["type"]
        if kind == "group":
            inner = "".join(self.node(c) for c in n["children"])
            transform = f"translate({num(n['x'])},{num(n['y'])})" if (n["x"] or n["y"]) else None
            return (f"<g {attr(data_id=n['id'], data_component=n.get('component'), data_content=n.get('content'), transform=transform)}>"
                    f"{inner}</g>")
        return getattr(self, kind)(n)

    def stroke_attrs(self, n):
        stroke = self.colour(n.get("stroke"))
        if not stroke:
            return {}
        out = {"stroke": stroke, "stroke_width": num(n["stroke_width"])}
        if n.get("dash"):
            out["stroke_dasharray"] = " ".join(num(d) for d in n["dash"])
        return out

    def box(self, n) -> str:
        sw = n.get("stroke_width", 0) if n.get("stroke") else 0
        x, y, w, h = n["x"] + sw / 2, n["y"] + sw / 2, max(n["width"] - sw, 0), max(n["height"] - sw, 0)
        fill = self.colour(n.get("fill")) or "none"
        r = n.get("radius")
        return (f"<rect {attr(data_id=n['id'], x=num(x), y=num(y), width=num(w), height=num(h), rx=num(r) if r else None, fill=fill, **self.stroke_attrs(n))}/>")

    def ellipse(self, n) -> str:
        fill = self.colour(n.get("fill")) or "none"
        return (f"<ellipse {attr(data_id=n['id'], cx=num(n['x'] + n['width'] / 2), cy=num(n['y'] + n['height'] / 2), rx=num(n['width'] / 2), ry=num(n['height'] / 2), fill=fill, **self.stroke_attrs(n))}/>")

    def line(self, n) -> str:
        pts = [list(p) for p in n["points"]]
        sw = n["stroke_width"]
        colour = self.colour(n["stroke"])
        length, half = sw * 4, sw * 2.4
        heads = []
        tips = n.get("tips", "none")
        for at_end in (True, False):
            if (at_end and tips in ("end", "both")) or (not at_end and tips in ("start", "both")):
                tip, prev = (pts[-1], pts[-2]) if at_end else (pts[0], pts[1])
                dx, dy = tip[0] - prev[0], tip[1] - prev[1]
                d = math.hypot(dx, dy) or 1.0
                ux, uy = dx / d, dy / d
                base = (tip[0] - ux * length, tip[1] - uy * length)
                left = (base[0] - uy * half, base[1] + ux * half)
                right = (base[0] + uy * half, base[1] - ux * half)
                heads.append(f"<polygon {attr(points=' '.join(f'{num(a)},{num(b)}' for a, b in (tip, left, right)), fill=colour)}/>")
                cut = (tip[0] - ux * length * 0.8, tip[1] - uy * length * 0.8)
                if at_end:
                    pts[-1] = list(cut)
                else:
                    pts[0] = list(cut)
        dash = {"stroke_dasharray": " ".join(num(d) for d in n["dash"])} if n.get("dash") else {}
        path = " ".join(f"{num(a)},{num(b)}" for a, b in pts)
        return (f"<g {attr(data_id=n['id'])}><polyline {attr(points=path, fill='none', stroke=colour, stroke_width=num(sw), **dash)}/>"
                + "".join(heads) + "</g>")

    def image(self, n) -> str:
        path = self.root / n["href"]
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        filt = None
        if n.get("tint"):
            colour = self.colour(n["tint"])
            fid = "tint-" + colour.lstrip("#")
            self.defs[fid] = (f'<filter id="{fid}" color-interpolation-filters="sRGB"><feFlood flood-color="{colour}"/>'
                              f'<feComposite in2="SourceAlpha" operator="in"/></filter>')
            filt = f"url(#{fid})"
        aspect = {"contain": "xMidYMid meet", "cover": "xMidYMid slice", "fill": "none"}.get(n.get("fit", "contain"), "xMidYMid meet")
        return (f"<image {attr(data_id=n['id'], x=num(n['x']), y=num(n['y']), width=num(n['width']), height=num(n['height']), preserveAspectRatio=aspect, filter=filt)} "
                f'href="data:image/png;base64,{data}"/>')

    def text(self, n) -> str:
        font = n["font"]
        out = []
        for i, line in enumerate(n["lines"]):
            y = n["y"] + i * font["line_height"] + font["baseline"]
            for run in line["runs"]:
                if not run["text"]:
                    continue
                x = n["x"] + line["x"] + run["x"]
                out.append(f"<tspan {attr(x=num(x), y=num(y), fill=self.colour(run['fill']))}>{escape(run['text'], quote=False)}</tspan>")
        family = font["family"]
        return (f"<text xml:space=\"preserve\" {attr(data_id=n['id'], data_field=n.get('field'), font_family=family, font_size=num(font['size']), font_weight=font['weight'] if font['weight'] != 400 else None)}>"
                + "".join(out) + "</text>")


def render_page(scene, page, tokens, root, scale=0.5, embed_fonts=True) -> str:
    return SvgPage(scene, page, tokens, root, scale, embed_fonts).render()
