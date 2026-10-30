"""Generate the Friday talk's slide instances into the board map.

Reads the slides' content (…friday-talk.slides.yaml) and writes instances of the
board library's templates into the board map (…friday-talk.board.yaml), replacing
every instance and layout it generated before (ids starting with "T-"). Library
masters and LIB objects are left untouched.

Usage: python gen_slides.py <slides.yaml> <board.yaml>
"""

import re
import sys

import yaml

GRID_W = 3200
MARGIN = 128
SPAN16 = 2944
GUT = 64
CONTENT_Y = 576
GAP = 48
STEP_H = 3 * 32 + 64 + 3 * 40 * 1.25  # 310
CARD_H = 3 * 32 + 64 + 2 * 48 * 1.25 + 16 + 5 * 36 * 1.25 + 32  # 553
CALLOUT_H = 176
NOTICE_H = 112
STAGE_H = 272
LINK_W = 96
ACTOR_W, ACTOR_H = 436, 248
SPAN8 = 1440
SPAN5 = 876


def md(s: str) -> str:
    """Slides show plain text: drop Markdown backticks."""
    return (s or "").replace("`", "")


def stage(pid, i, x, y, w, role, head, text, h=STAGE_H):
    return f"{pid}-s{i}", {
        "template": "stage", "parent": pid, "role": role, "head": md(head), "text": md(text),
        "x": x, "y": y,
        "override": {
            "root": {"width": w, "height": h},
            "box": {"width": w, "height": h},
            "head": {"width": w - 104, "height": 64},
            "text": {"y": 100, "width": w - 64, "height": h - 137},
        },
    }


def link(pid, i, x, y, h=STAGE_H):
    return f"{pid}-l{i}", {
        "template": "link", "parent": pid, "x": x, "y": y,
        "x1": 16, "y1": h / 2, "x2": LINK_W - 16, "y2": h / 2, "tone": "text_secondary",
        "override": {"root": {"width": LINK_W, "height": h}},
    }


ART_H = 96
FAN_GAP = 80


def artefact(pid, i, x, y, w, icon, text):
    return f"{pid}-f{i}", {
        "template": "artefact", "parent": pid, "icon": icon, "text": md(text), "x": x, "y": y,
        "override": {"root": {"width": w}, "box": {"width": w}, "text": {"width": w - 112}},
    }


def fanout(pid, y, v):
    """You -> the planning agent -> several builders in parallel -> the checks: stages left and right,
    the parallel items as one tile each, and one link per tile on either side."""
    out = {}
    items = v["middle"]
    n = len(items)
    h = n * ART_H + (n - 1) * FAN_GAP
    cols = len(v["left"]) + 2
    w = (SPAN16 - (cols - 1) * LINK_W) / cols
    x = MARGIN
    si = li = 0
    for s in v["left"]:
        si += 1
        k, val = stage(pid, si, round(x), y, round(w), s.get("role", "neutral"), s["head"], s.get("text", ""), h)
        out[k] = val
        x += w
        if s is not v["left"][-1]:
            li += 1
            k, val = link(pid, li, round(x), y, h)
            out[k] = val
            x += LINK_W
    for j in range(n):
        li += 1
        k, val = link(pid, li, round(x), round(y + j * (ART_H + FAN_GAP)), ART_H)
        out[k] = val
    x += LINK_W
    for j, it in enumerate(items, 1):
        k, val = artefact(pid, j, round(x), round(y + (j - 1) * (ART_H + FAN_GAP)), round(w), it.get("icon", "agents"), it["head"])
        out[k] = val
    x += w
    for j in range(n):
        li += 1
        k, val = link(pid, li, round(x), round(y + j * (ART_H + FAN_GAP)), ART_H)
        out[k] = val
    x += LINK_W
    r = v["right"]
    si += 1
    k, val = stage(pid, si, round(x), y, round(w), r.get("role", "neutral"), r["head"], r.get("text", ""), h)
    out[k] = val
    return out, h


PAIR_H = 200
PAIR_GAP = 40


CLEAR = "#FFFFFF00"
# Styles of a pairs diagram: per side, overrides of the stage's parts; and the arrows' tone and width.
PAIR_STYLES = {
    "plain": {"left": {}, "right": {}, "tone": "text_secondary", "arrow": 4},
    "tinted": {
        "left": {"box": {"color": "@role_neutral_bg", "border_color": "@role_neutral", "border_width": 2}},
        "right": {"box": {"color": "@role_code_bg", "border_color": "@role_code", "border_width": 4}},
        "tone": "role_code", "arrow": 6,
    },
    "solid": {
        "left": {
            "box": {"color": "@role_neutral_bg", "border_color": "@role_neutral_bg"},
            "dot": {"color": "@role_neutral_bg", "border_color": "@role_neutral_bg"},
            "text": {"ink": "@text_secondary"},
        },
        "right": {
            "box": {"color": "@role_code", "border_color": "@role_code"},
            "dot": {"color": "@text_on_color", "border_color": "@text_on_color"},
            "head": {"ink": "@text_on_color"},
            "text": {"ink": "@text_on_color"},
        },
        "tone": "role_code", "arrow": 6,
    },
    "dark": {
        "left": {"box": {"color": "@role_neutral_bg", "border_color": "@role_neutral_bg"}},
        "right": {
            "box": {"color": "@background_inverse", "border_color": "@background_inverse"},
            "dot": {"color": "@accent_inverse", "border_color": "@accent_inverse"},
            "head": {"ink": "@text_inverse"},
            "text": {"ink": "@text_inverse"},
        },
        "tone": "background_inverse", "arrow": 6,
    },
}


def styled(kv, parts):
    k, v = kv
    for part, fields in parts.items():
        v["override"].setdefault(part, {}).update(fields)
    return k, v


ICON = 64


def pstage_template(stage_tpl):
    """The stage with a pictogram in place of its role dot: `icon` names a PNG in the icons folder."""
    import copy

    t = copy.deepcopy(stage_tpl)
    t.pop("master", None)
    t["note"] = "Diagram stage with a pictogram (2026-10-29-friday-talk-icons/<icon>.png) in place of the role dot; made by the slide generator from the stage template."
    parts = t["parts"]
    parts.pop("dot", None)
    parts["icon"] = {"type": "image", "file": "2026-10-29-friday-talk-icons/{icon}.png", "x": 32, "y": 28, "width": ICON, "height": ICON}
    t["parts"] = {"box": parts["box"], "icon": parts["icon"], "head": parts["head"], "text": parts["text"]}
    return t


def with_icon(kv, icon, w, h):
    k, v = kv
    v["template"] = "pstage"
    v["icon"] = icon
    v["override"]["head"] = {"x": 32 + ICON + 24, "width": w - (32 + ICON + 24) - 32, "height": 64}
    v["override"]["text"] = {"x": 32 + ICON + 24, "y": 100, "width": w - (32 + ICON + 24) - 32, "height": h - 137}
    return k, v


def pairs(pid, y, items, style="plain", icons=False):
    """One row per pair: a left stage, a link, a right stage (e.g. a problem and what answers it)."""
    st = PAIR_STYLES[style]
    out = {}
    w = (SPAN16 - LINK_W) / 2
    for i, p in enumerate(items):
        yy = y + i * (PAIR_H + PAIR_GAP)
        a, b = p["left"], p["right"]
        kv = stage(pid, 2 * i + 1, MARGIN, yy, round(w), a.get("role", "neutral"), a["head"], a.get("text", ""), PAIR_H)
        if icons:
            kv = with_icon(kv, a["icon"], round(w), PAIR_H)
        k, v = styled(kv, {p_: f for p_, f in st["left"].items() if not (icons and p_ == "dot")})
        out[k] = v
        k, v = link(pid, i + 1, round(MARGIN + w), yy, PAIR_H)
        v["tone"] = st["tone"]
        v["override"]["arrow"] = {"border_width": st["arrow"]}
        out[k] = v
        kv = stage(pid, 2 * i + 2, round(MARGIN + w + LINK_W), yy, round(w), b.get("role", "neutral"), b["head"], b.get("text", ""), PAIR_H)
        if icons:
            kv = with_icon(kv, b["icon"], round(w), PAIR_H)
        k, v = styled(kv, {p_: f for p_, f in st["right"].items() if not (icons and p_ == "dot")})
        out[k] = v
    n = len(items)
    return out, n * PAIR_H + (n - 1) * PAIR_GAP


CLEAR_AREA = {"type": "area", "title": "{id}", "show_title": False, "color": "#FFFFFF00", "border_color": "#FFFFFF00", "border_width": 1}

TREE_TEMPLATES = {
    "tree_bar": {
        "note": "A connector line of a tree, drawn as a thin bar so every line has one thickness; made by the slide generator.",
        "root": {**CLEAR_AREA, "width": 4, "height": 64},
        "parts": {"bar": {"type": "shape", "shape": "rectangle", "text": "", "x": 0, "y": 0, "width": 4, "height": 64,
                          "color": "@{tone}", "border_color": "@{tone}", "border_width": 1, "ink": "@text_primary"}},
        "defaults": {"tone": "border_strong"},
    },
    "tree_tag": {
        "note": "A tag in a tree: a filled box with one line of text in a role's colour; made by the slide generator.",
        "root": {**CLEAR_AREA, "width": 200, "height": 64},
        "parts": {
            "bg": {"type": "shape", "shape": "rectangle", "text": "", "x": 0, "y": 0, "width": 200, "height": 64,
                   "color": "@{bg}", "border_color": "@{bg}", "border_width": 1, "ink": "@text_primary"},
            "text": {"type": "text", "text": "{text}", "style": "@style.key", "ink": "@{ink}", "x": 20, "y": 2, "width": 160, "height": 60},
        },
    },
    "tree_note": {
        "note": "A note beside a tree's tag, in the secondary text colour; made by the slide generator.",
        "root": {**CLEAR_AREA, "width": 600, "height": 64},
        "parts": {"text": {"type": "text", "text": "{text}", "style": "@style.body", "ink": "@text_secondary", "x": 0, "y": 6, "width": 600, "height": 58}},
    },
}

TAG_COLOURS = {"pkit": ("role_code_bg", "role_code"), "yours": ("role_people_bg", "role_people"), "plain": ("layer", "text_primary")}
TREE_PITCH, TREE_INDENT, TAG_H, CHAR_KEY, CHAR_BODY = 76, 56, 64, 23, 19


def text_w(s, size=40):
    """An estimate of a proportional font's width: capitals wide, punctuation narrow."""
    em = 0.0
    for ch in s:
        em += 0.68 if ch.isupper() else 0.56 if ch.isdigit() else 0.3 if ch in "/.:, '-" else 0.75 if ch == "…" else 0.52
    return em * size


def tag_w(s):
    return text_w(s) * 1.1 + 56


def tree(pid, x0, y0, rows, legend=None):
    """A file tree drawn from shapes: each row is (depth, [(text, owner), ...], note); lines are bars."""
    out = {}
    n = 0

    def put(template, x, y, w, h, **params):
        nonlocal n
        n += 1
        key = f"{pid}-tr{n}"
        ov = {"root": {"width": round(w), "height": round(h)}}
        if template == "tree_bar":
            ov["bar"] = {"width": round(w), "height": round(h)}
        elif template == "tree_tag":
            ov["bg"] = {"width": round(w), "height": round(h)}
            ov["text"] = {"width": round(w - 40)}
        else:
            ov["text"] = {"width": round(w)}
        out[key] = {"template": template, "parent": pid, "x": round(x), "y": round(y), **params, "override": ov}

    last_child_y = {}
    xs = {}
    for i, (depth, tags, note) in enumerate(rows):
        y = y0 + i * TREE_PITCH
        x = x0 + depth * TREE_INDENT
        xs[i] = x
        if depth > 0:
            # the parent is the nearest row above at depth - 1
            parent = max(j for j in range(i) if rows[j][0] == depth - 1)
            px = xs[parent] + 24
            put("tree_bar", px + 2, y + TAG_H / 2 - 2, x - px - 10, 4)
            last_child_y[parent] = y + TAG_H / 2
        for text, owner in tags:
            bg, ink = TAG_COLOURS[owner]
            w = tag_w(text)
            put("tree_tag", x, y, w, TAG_H, text=text, bg=bg, ink=ink)
            x += w + 16
        if note:
            put("tree_note", x + 8, y, len(note) * CHAR_BODY + 40, TAG_H, text=note)
    for parent, ly in last_child_y.items():
        py = y0 + parent * TREE_PITCH + TAG_H
        put("tree_bar", xs[parent] + 24 - 2, py, 4, ly - py + 2)  # ends where the last elbow starts, beside it
    h = len(rows) * TREE_PITCH
    if legend:
        x = x0
        y = y0 + h + 16
        for text, owner in legend:
            bg, ink = TAG_COLOURS[owner]
            w = tag_w(text)
            put("tree_tag", x, y, w, TAG_H, text=text, bg=bg, ink=ink)
            x += w + 24
        h += 16 + TAG_H
    return out, h


def vlink(pid, i, x, y, h):
    return f"{pid}-l{i}", {
        "template": "link", "parent": pid, "x": x, "y": y,
        "x1": LINK_W / 2, "y1": 8, "x2": LINK_W / 2, "y2": h - 8, "tone": "role_code",
        "override": {"root": {"width": LINK_W, "height": h}, "arrow": {"border_width": 6}},
    }


# The deck's one style for a terminal: a light panel in a monospace font, the prompt and comments
# grey, the command green, its arguments near black, output dark grey; in a listing, what is pkit's
# purple and what is yours blue. Colours travel as spans in Mural's html.
TERM = {"prompt": "#6F6F6F", "command": "#198038", "args": "#161616", "comment": "#6F6F6F", "output": "#393939",
        "branch": "#A8A8A8", "pkit": "#6929C4", "yours": "#0043CE", "plain": "#161616",
        "del": "#DA1E28", "add": "#198038"}
TERM_LINE = 46
TERM_FONT = "ibm-plex-mono"


def _span(colour, s):
    import html as htmllib

    s = htmllib.escape(s, quote=False).replace("  ", "&nbsp; ")
    return f'<span style="color:{colour}">{s}</span>'


def terminal_html(content):
    """Text (each line coloured by its kind) or a list of lines, each a list of [text, role]."""
    divs = []
    if isinstance(content, str):
        for line in content.split("\n"):
            if not line.strip():
                divs.append("<div><br></div>")
            elif line.lstrip().startswith("#"):
                divs.append("<div>" + _span(TERM["comment"], line) + "</div>")
            elif line.startswith("$ "):
                cmd, _, rest = line[2:].partition(" ")
                divs.append("<div>" + _span(TERM["prompt"], "$ ") + _span(TERM["command"], cmd) + (_span(TERM["args"], " " + rest) if rest else "") + "</div>")
            else:
                divs.append("<div>" + _span(TERM["output"], line) + "</div>")
    else:
        for segs in content:
            divs.append("<div>" + ("".join(_span(TERM[role], text) for text, role in segs) or "<br>") + "</div>")
    return '<html v="1">' + "".join(divs) + "</html>"


def term_lines(content):
    return content.rstrip("\n").count("\n") + 1 if isinstance(content, str) else len(content)


TERMINAL_TEMPLATE = {
    "note": "The deck's terminal: a dark panel holding commands and their output, syntax coloured; made by the slide generator.",
    "root": {**CLEAR_AREA, "width": 1440, "height": 400},
    "parts": {
        "bg": {"type": "shape", "shape": "rectangle", "text": "", "x": 0, "y": 0, "width": 1440, "height": 400,
               "color": "#F4F4F4FF", "border_color": "#E0E0E0FF", "border_width": 2, "ink": "@text_primary"},
        "text": {"type": "text", "html": "{html}", "style": "@style.body", "font": TERM_FONT, "x": 40, "y": 36, "width": 1360, "height": 328},
    },
}


ICONS_DIR = "2026-10-29-friday-talk-icons"
MAP_DIR = None  # set in main: the folder the map lives in


def term_segments(content):
    """Each line as [text, role] segments, coloured as the deck's terminal colours them."""
    if not isinstance(content, str):
        return [[(s[0], s[1]) for s in line] for line in content]
    out = []
    continued = False
    for line in content.split("\n"):
        if continued:
            out.append([(line, "args")])
        elif not line.strip():
            out.append([])
        elif line.lstrip().startswith("#") and not line.lstrip().startswith("##"):
            out.append([(line, "comment")])
        elif line.startswith("$ "):
            cmd, _, rest = line[2:].partition(" ")
            out.append([("$ ", "prompt"), (cmd, "command")] + ([(" " + rest, "args")] if rest else []))
        elif line.startswith("- "):
            out.append([(line, "del")])
        elif line.startswith("+ "):
            out.append([(line, "add")])
        else:
            # a body, then an inline comment after two spaces; a body is a heading, a key and its value, or output
            i = line.find("  #")
            body, note = (line, "") if i < 0 else (line[:i], line[i:])
            key = re.match(r"([A-Za-z][\w-]*: )(.*)$", body)
            segs = [(body, "args")] if body.startswith("##") else [(key[1], "output"), (key[2], "args")] if key else [(body, "output")]
            out.append(segs + ([(note, "comment")] if note else []))
        continued = line.rstrip().endswith("\\")
    return out


def terminal_png(name, content, w, font_size=30):
    """Render a terminal panel to a PNG beside the map: a light panel, IBM Plex Mono, the deck's
    syntax colours. Mural has no monospace font, so a terminal is an image. Returns the file and its height."""
    import html as htmllib
    import subprocess
    from pathlib import Path

    lines = term_segments(content)
    line_h = round(font_size * 1.53)
    h = 72 + len(lines) * line_h
    texts = []
    for i, segs in enumerate(lines):
        y = 36 + (i + 1) * line_h - round(line_h * 0.3)
        spans = "".join(f'<tspan fill="{TERM[role]}">{htmllib.escape(text, quote=False)}</tspan>' for text, role in segs)
        texts.append(f'<text x="40" y="{y}" xml:space="preserve">{spans}</text>')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
           f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" fill="#F4F4F4" stroke="#E0E0E0" stroke-width="2"/>'
           f'<g font-family="IBM Plex Mono" font-size="{font_size}">' + "".join(texts) + "</g></svg>")
    folder = Path(MAP_DIR) / ICONS_DIR
    svg_path = folder / f"term-{name}.svg"
    png_path = folder / f"term-{name}.png"
    svg_path.write_text(svg, encoding="utf-8")
    subprocess.run(["rsvg-convert", "-w", str(2 * w), "-h", str(2 * h), "-o", str(png_path), str(svg_path)], check=True)
    svg_path.unlink()
    return f"term-{name}", h


TERM_IMAGE_TEMPLATE = {
    "note": "The deck's terminal, rendered as an image (Mural has no monospace font): the file is term-<name>.png beside the map; made by the slide generator.",
    "root": {**CLEAR_AREA, "width": 1440, "height": 400},
    "parts": {"img": {"type": "image", "file": ICONS_DIR + "/{file}.png", "x": 0, "y": 0, "width": 1440, "height": 400}},
}


def terminal(pid, x, y, w, text, key="term", font_size=30):
    file, h = terminal_png(f"{pid}-{key}".removeprefix("T-"), text, w, font_size)
    return {
        f"{pid}-{key}": {
            "template": "term_image", "parent": pid, "x": x, "y": y, "file": file,
            "override": {"root": {"width": w, "height": h}, "img": {"width": w, "height": h}},
        }
    }, h


HIGHLIGHT_TEMPLATE = {
    "note": "An important note: a light yellow box with a yellow bar on its left, a pictogram, a question and a line of text; made by the slide generator.",
    "root": {**CLEAR_AREA, "width": 1440, "height": 380},
    "parts": {
        "bg": {"type": "shape", "shape": "rectangle", "text": "", "x": 0, "y": 0, "width": 1440, "height": 380,
               "color": "#FCF4D6FF", "border_color": "#FCF4D6FF", "border_width": 1, "ink": "@text_primary"},
        "bar": {"type": "shape", "shape": "rectangle", "text": "", "x": 0, "y": 0, "width": 12, "height": 380,
                "color": "#F1C21BFF", "border_color": "#F1C21BFF", "border_width": 1, "ink": "@text_primary"},
        "icon": {"type": "image", "file": "2026-10-29-friday-talk-icons/{icon}.png", "x": 44, "y": 28, "width": 72, "height": 72},
        "head": {"type": "text", "text": "{head}", "style": "@style.key", "ink": "@text_primary", "x": 140, "y": 36, "width": 1260, "height": 64},
        "body": {"type": "text", "text": "{body}", "style": "@style.body", "ink": "@text_primary", "x": 140, "y": 256, "width": 1260, "height": 100},
    },
}


def highlight(pid, x, y, w, v):
    """An important note with a small terminal inside it."""
    key = f"{pid}-hl"
    out = {key: {"template": "highlight", "parent": pid, "x": x, "y": y, "icon": v["icon"], "head": md(v["head"]), "body": md(v["body"]),
                 "override": {"root": {"width": w}, "bg": {"width": w}, "head": {"width": w - 180}, "body": {"width": w - 180}}}}
    d, th = terminal(key, 140, 116, w - 180, v["command"], key="cmd")
    out.update(d)
    return out, 380


KIND_H = 600
KIND_TEMPLATE = {
    "note": "A kind of a thing as a column in its own tone: a filled tag (its prefix), a head, what it decides, a real file of it, and why it lives where it does; made by the slide generator.",
    "root": {**CLEAR_AREA, "width": 896, "height": KIND_H},
    "parts": {
        "bg": {"type": "shape", "shape": "rectangle", "text": "", "x": 0, "y": 0, "width": 896, "height": KIND_H,
               "color": "@{bg}", "border_color": "@{tone}", "border_width": 2, "ink": "@text_primary"},
        "tag": {"type": "shape", "shape": "rectangle", "text": "", "x": 40, "y": 40, "width": 180, "height": 88,
                "color": "@{tone}", "border_color": "@{tone}", "border_width": 1, "ink": "@text_on_color"},
        "tagtext": {"type": "text", "text": "{tag}", "style": "@style.heading", "ink": "@text_on_color", "x": 40, "y": 44, "width": 180, "height": 80, "align": "center"},
        "head": {"type": "text", "text": "{head}", "style": "@style.tile_heading", "ink": "@text_primary", "x": 40, "y": 164, "width": 816, "height": 64},
        "text": {"type": "text", "text": "{text}", "style": "@style.body", "x": 40, "y": 240, "width": 816, "height": 100},
        "path": {"type": "text", "text": "{path}", "style": "@style.body", "ink": "@{tone}", "x": 40, "y": 352, "width": 816, "height": 56},
        "why": {"type": "text", "text": "{why}", "style": "@style.body", "ink": "@text_primary", "x": 40, "y": 428, "width": 816, "height": 150},
    },
}
GROUP_HEAD_H, CHIP_FONT, CHIP_PAD = 56, 40, 24
CHIP_H = round(CHIP_FONT * 1.9)
GROUP_H = GROUP_HEAD_H + 12 + CHIP_H + 20 + 6  # the heading, the path, the bar
GROUP_TEMPLATE = {
    "note": "A group's heading over the columns it holds, saying what they share; its path and bar are separate instances; made by the slide generator.",
    "root": {**CLEAR_AREA, "width": 1856, "height": GROUP_HEAD_H},
    "parts": {
        "head": {"type": "text", "text": "{head}", "style": "@style.key", "ink": "@text_primary", "x": 0, "y": 0, "width": 1856, "height": GROUP_HEAD_H},
    },
}
KIND_TONES = {"core": ("role_neutral_bg", "role_neutral"), "yours": ("role_people_bg", "role_people"),
              "architecture": ("role_architecture_bg", "role_architecture"), "pkit": ("role_code_bg", "role_code")}
GROUP_GAP = 192


def chip_png(name, text, font_size=CHIP_FONT):
    """A path in the deck's terminal style, as a one-line chip: a light panel, IBM Plex Mono, near-black text.
    Mural has no monospace font, so the chip is an image beside the map. Returns the file and its size."""
    import html as htmllib
    import subprocess
    from pathlib import Path

    w = round(2 * CHIP_PAD + len(text) * 0.6 * font_size)
    h = CHIP_H
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
           f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" fill="#F4F4F4" stroke="#E0E0E0" stroke-width="2"/>'
           f'<text x="{CHIP_PAD}" y="{round(h / 2 + font_size * 0.36)}" font-family="IBM Plex Mono" font-size="{font_size}" '
           f'fill="{TERM["plain"]}" xml:space="preserve">{htmllib.escape(text, quote=False)}</text></svg>')
    folder = Path(MAP_DIR) / ICONS_DIR
    svg_path = folder / f"chip-{name}.svg"
    png_path = folder / f"chip-{name}.png"
    svg_path.write_text(svg, encoding="utf-8")
    subprocess.run(["rsvg-convert", "-w", str(2 * w), "-h", str(2 * h), "-o", str(png_path), str(svg_path)], check=True)
    svg_path.unlink()
    return f"chip-{name}", w, h


def kinds(pid, y, v):
    """Kinds of a thing as columns, each in its own tone (`tone`: core grey, yours blue, architecture green), in groups across
    the slide: each group under its heading (what its kinds share), its path as a chip in the terminal style,
    and a bar its width."""
    out = {}
    groups = v["groups"]
    n = sum(len(g["kinds"]) for g in groups)
    w = (SPAN16 - (n - len(groups)) * GUT - (len(groups) - 1) * GROUP_GAP) / n
    ww = round(w)
    x = MARGIN
    i = 0
    for gi, g in enumerate(groups, 1):
        gw = round(len(g["kinds"]) * w + (len(g["kinds"]) - 1) * GUT)
        out[f"{pid}-grp{gi}"] = {
            "template": "kind_group", "parent": pid, "x": round(x), "y": y, "head": md(g["head"]),
            "override": {"root": {"width": gw}, "head": {"width": gw}},
        }
        file, cw, ch = chip_png(f"{pid}-path{gi}".removeprefix("T-"), g["path"])
        out[f"{pid}-path{gi}"] = {
            "template": "term_image", "parent": pid, "x": round(x), "y": y + GROUP_HEAD_H + 12, "file": file,
            "override": {"root": {"width": cw, "height": ch}, "img": {"width": cw, "height": ch}},
        }
        out[f"{pid}-bar{gi}"] = {
            "template": "tree_bar", "parent": pid, "x": round(x), "y": y + GROUP_H - 6,
            "override": {"root": {"width": gw, "height": 6}, "bar": {"width": gw, "height": 6}},
        }
        for it in g["kinds"]:
            i += 1
            bg, tone = KIND_TONES[it.get("tone", "pkit")]
            out[f"{pid}-col{i}"] = {
                "template": "kind", "parent": pid, "x": round(x), "y": y + GROUP_H + 24,
                "tag": it["tag"], "head": md(it["head"]), "text": md(it["text"]), "path": md(it["path"]), "why": md(it["why"]),
                "bg": bg, "tone": tone,
                "override": {"root": {"width": ww}, "bg": {"width": ww}, **{p: {"width": ww - 80} for p in ("head", "text", "path", "why")}},
            }
            x += w + GUT
        x += GROUP_GAP - GUT
    return out, GROUP_H + 24 + KIND_H


def step_card_template(stage_tpl):
    """The stage with a picture inside it: the step's name, a line of what happens, and the moment it shows,
    rendered in the terminal style (`file` names a PNG in the icons folder); made from the stage template."""
    import copy

    t = copy.deepcopy(stage_tpl)
    t.pop("master", None)
    t["note"] = "A step of a story with its picture inside: the stage's box, dot, head and text, and a terminal image below them; made by the slide generator from the stage template."
    t["parts"]["img"] = {"type": "image", "file": ICONS_DIR + "/{file}.png", "x": 32, "y": 216, "width": 576, "height": 300}
    return t


CARD_TEXT_H, CARD_IMG_Y = 100, 216


def story(pid, y, v):
    """One thing through its steps, left to right: a card per step, its picture inside it, arrows between."""
    out = {}
    st = v["stages"]
    n = len(st)
    w = round((SPAN16 - (n - 1) * LINK_W) / n)
    fs = v.get("font_size", 26)
    pics = [terminal_png(f"{pid}-step{i}".removeprefix("T-"), s["terminal"], w - 64, fs) for i, s in enumerate(st, 1)]
    x = MARGIN
    for i, (s, (file, ph)) in enumerate(zip(st, pics), 1):
        h = CARD_IMG_Y + ph + 32  # each card as tall as its picture; the arrows join them at their heads
        out[f"{pid}-card{i}"] = {
            "template": "step_card", "parent": pid, "role": s.get("role", "neutral"), "head": md(s["head"]), "text": md(s["text"]),
            "file": file, "x": x, "y": y,
            "override": {
                "root": {"width": w, "height": h}, "box": {"width": w, "height": h},
                "head": {"width": w - 104, "height": 64}, "text": {"y": 100, "width": w - 64, "height": CARD_TEXT_H},
                "img": {"x": 32, "y": CARD_IMG_Y, "width": w - 64, "height": ph},
            },
        }
        x += w
        if i < n:
            k, val = link(pid, i, x, y, CARD_IMG_Y)
            out[k] = val
            x += LINK_W
    return out, CARD_IMG_Y + max(ph for _, ph in pics) + 32


EXTRA_TEMPLATES = {}  # templates made for one slide, added to the map beside the shared ones
TIES_ROW, TIES_NODE_H, TIES_HEAD_H, TIES_CENTER_H = 76, 60, 72, 176
TIES_TONES = {"code": ("role_neutral_bg", "role_neutral"), "pkit": ("role_code_bg", "role_code"),
              "yours": ("role_people_bg", "role_people"), "architecture": ("role_architecture_bg", "role_architecture")}


CHECK_ROW, CHECK_GAP, CHECK_HEAD = 68, 10, 72


def checklist(pid, y, v):
    """One procedure as a numbered checklist, one step marked as its command's, and beside it the command's
    real output in a terminal, an arrow from the marked step. The list is one instance of a template made
    for this slide."""
    steps, mark = v["steps"], v["mark"] - 1
    lw = 1300
    tx_rel = lw + 160
    fs = v.get("font_size", 28)
    file, th = terminal_png(f"{pid}-cmd".removeprefix("T-"), v["terminal"], SPAN16 - tx_rel, fs)
    line_h = round(fs * 1.53)
    first = 36 + line_h - round(line_h * 0.3) - fs * 0.35  # the middle of the terminal's first line
    mark_mid = CHECK_HEAD + mark * (CHECK_ROW + CHECK_GAP) + CHECK_ROW / 2
    t_top = round(mark_mid - first)
    list_h = CHECK_HEAD + len(steps) * CHECK_ROW + (len(steps) - 1) * CHECK_GAP
    H = max(list_h, t_top + th)
    parts = {
        "lhead": {"type": "text", "text": md(v["head"]), "style": "@style.key", "ink": "@text_primary", "x": 0, "y": 0, "width": lw, "height": 56},
        "rhead": {"type": "text", "text": md(v["terminal_head"]), "style": "@style.key", "ink": "@text_primary",
                  "x": tx_rel, "y": t_top - CHECK_HEAD, "width": SPAN16 - tx_rel, "height": 56},
        "cmd": {"type": "image", "file": f"{ICONS_DIR}/{file}.png", "x": tx_rel, "y": t_top, "width": SPAN16 - tx_rel, "height": th},
    }
    for i, s in enumerate(steps):
        top = CHECK_HEAD + i * (CHECK_ROW + CHECK_GAP)
        on = i == mark
        fill = "@role_code" if on else "@role_neutral_bg"
        ink = "@text_on_color" if on else "@text_primary"
        parts[f"r{i}box"] = {"type": "shape", "shape": "rectangle", "text": "", "x": 0, "y": top, "width": lw, "height": CHECK_ROW,
                             "color": fill, "border_color": fill, "border_width": 1, "ink": ink}
        parts[f"r{i}num"] = {"type": "text", "text": str(i + 1), "style": "@style.key", "ink": ink, "x": 24, "y": top + 6, "width": 56, "height": 56}
        parts[f"r{i}text"] = {"type": "text", "text": md(s), "style": "@style.body", "ink": ink, "x": 96, "y": top + 9, "width": lw - 120, "height": 50}
        if on and v.get("mark_note"):
            parts[f"r{i}note"] = {"type": "text", "text": md(v["mark_note"]), "style": "@style.key", "ink": ink, "align": "right",
                                  "x": lw - 520, "y": top + 6, "width": 496, "height": 56}
    parts["arrow"] = {"type": "arrow", "points": [[lw + 16, round(mark_mid)], [tx_rel - 16, round(mark_mid)]], "arrow_type": "straight",
                      "tip": "end", "color": "@role_code", "border_width": 6, "border_style": "solid"}
    name = f"checklist_{pid}"
    EXTRA_TEMPLATES[name] = {
        "note": "One procedure as a numbered checklist with its command's output beside it, drawn for one slide by the slide generator.",
        "root": {**CLEAR_AREA, "width": SPAN16, "height": H},
        "parts": parts,
    }
    return {f"{pid}-checklist": {"template": name, "parent": pid, "x": MARGIN, "y": y}}, H


MAP_HEAD_H, MAP_ROW, MAP_GAP, MAP_ARROW = 152, 128, 16, 96


def table_map(pid, y, v):
    """Columns as the pyramid's layers, side by side in their colours, read left to right: a head per column
    (its name and what it does), then a row per example, a command cell holding its command as a chip in the
    terminal style. Arrows join the heads. Under the rows, a caption, or a row of reasons (`why`): a heading,
    then a box under each column, the column's colour as a bar on top. One instance of a template made for
    this slide."""
    cols, rows = v["columns"], v["rows"]
    n = len(cols)
    cw = round((SPAN16 - (n - 1) * MAP_ARROW) / n)
    xs = [i * (cw + MAP_ARROW) for i in range(n)]
    HEAD_H, ROW = v.get("head_h", MAP_HEAD_H), v.get("row_h", MAP_ROW)
    rows_top = HEAD_H + 24
    cap_top = rows_top + len(rows) * ROW + (len(rows) - 1) * MAP_GAP + 24
    H = cap_top + (56 if v.get("caption") else 0)
    why = v.get("why")
    if why:
        why_top = cap_top + 16
        lines = max(-(-text_w(t) // (cw - 64)) for t in why["items"])
        why_h = 32 + lines * 50 + 24
        H = why_top + 68 + why_h
    parts = {}

    def shape(key, x, top, w, h, fill):
        parts[key] = {"type": "shape", "shape": "rectangle", "text": "", "x": x, "y": round(top), "width": w, "height": h,
                      "color": fill, "border_color": fill, "border_width": 1, "ink": "@text_primary"}

    def text(key, s, style, x, top, w, h, ink):
        parts[key] = {"type": "text", "text": md(s), "style": style, "ink": ink, "x": x, "y": round(top), "width": w, "height": h}

    for i, c in enumerate(cols):
        ink = c.get("ink", "@text_primary")
        shape(f"h{i}box", xs[i], 0, cw, HEAD_H, c["fill"])
        text(f"h{i}head", c["head"], "@style.tile_heading", xs[i] + 32, HEAD_H / 2 - 52, cw - 64, 64, ink)
        text(f"h{i}text", c["text"], "@style.body", xs[i] + 32, HEAD_H / 2 + 16, cw - 64, 50, ink)
        if i:
            parts[f"h{i}arrow"] = {"type": "arrow", "points": [[xs[i] - MAP_ARROW + 16, HEAD_H // 2], [xs[i] - 16, HEAD_H // 2]],
                                   "arrow_type": "straight", "tip": "end", "color": "@role_code", "border_width": 6, "border_style": "solid"}
    for r, row in enumerate(rows):
        top = rows_top + r * (ROW + MAP_GAP)
        for i, (c, cell) in enumerate(zip(cols, row)):
            ink = c.get("ink", "@text_primary")
            key = f"r{r}c{i}"
            shape(f"{key}box", xs[i], top, cw, ROW, c["fill"])
            if c.get("cell") == "chip":
                file, w, h = chip_png(f"{pid}-r{r}".removeprefix("T-"), cell, v.get("chip_font", 32))
                parts[f"{key}chip"] = {"type": "image", "file": f"{ICONS_DIR}/{file}.png", "x": xs[i] + 32, "y": round(top + (ROW - h) / 2),
                                       "width": w, "height": h}
            elif isinstance(cell, dict):
                text(f"{key}head", cell["head"], "@style.key", xs[i] + 32, top + ROW / 2 - 54, cw - 64, 56, ink)
                text(f"{key}text", cell["text"], "@style.body", xs[i] + 32, top + ROW / 2 + 2, cw - 64, 50, ink)
            else:
                lines = 1 if text_w(cell) <= cw - 64 else 2
                style = "@style.key" if c.get("cell") == "name" else "@style.body"
                text(f"{key}text", cell, style, xs[i] + 32, top + (ROW - lines * 50) / 2 - 4, cw - 64, lines * 50, ink)
    if v.get("caption"):
        text("caption", v["caption"], "@style.body", 0, cap_top, SPAN16, 50, "@text_secondary")
    if why:
        text("whyhead", why["head"], "@style.key", 0, why_top, SPAN16, 56, "@text_primary")
        for i, (c, t) in enumerate(zip(cols, why["items"])):
            top = why_top + 68
            shape(f"w{i}box", xs[i], top, cw, why_h, "@role_neutral_bg")
            shape(f"w{i}bar", xs[i], top, cw, 8, c["fill"])
            text(f"w{i}text", t, "@style.body", xs[i] + 32, top + 32, cw - 64, why_h - 56, "@text_primary")
    name = f"map_{pid}"
    EXTRA_TEMPLATES[name] = {
        "note": "Columns as the pyramid's layers, side by side, a row per example; drawn for one slide by the slide generator.",
        "root": {**CLEAR_AREA, "width": SPAN16, "height": H},
        "parts": parts,
    }
    return {f"{pid}-map": {"template": name, "parent": pid, "x": MARGIN, "y": y}}, H


def wired(pid, y, v):
    """What comes wired: terminals side by side, joined by a sign between them (pkit's file + your file = what
    your tool gets); under them a card per tie, and the yellow note last in that row. The terminals and cards are
    one instance of a template made for this slide; the note is the deck's highlight."""
    panels, signs = v["panels"], v.get("signs", [])
    n = len(panels)
    aw = 120
    pw = round((SPAN16 - (n - 1) * aw) / n)
    fs = v.get("font_size", 26)
    imgs = [terminal_png(f"{pid}-p{i}".removeprefix("T-"), p["terminal"], pw, fs) for i, p in enumerate(panels)]
    th = max(h for _, h in imgs)
    HEAD = 68
    parts = {}
    for i, (p, (file, h)) in enumerate(zip(panels, imgs)):
        x = i * (pw + aw)
        parts[f"p{i}head"] = {"type": "text", "text": md(p["head"]), "style": "@style.key", "ink": "@text_primary", "x": x, "y": 0, "width": pw, "height": 56}
        parts[f"p{i}img"] = {"type": "image", "file": f"{ICONS_DIR}/{file}.png", "x": x, "y": HEAD, "width": pw, "height": h}
        if i and i - 1 < len(signs):
            parts[f"p{i}sign"] = {"type": "text", "text": signs[i - 1], "style": "@style.heading", "ink": "@role_code", "align": "center",
                                  "x": x - aw, "y": round(HEAD + th / 2 - 44), "width": aw, "height": 88}
    row2 = HEAD + th + 48
    ties, note = v["ties"], v.get("note")
    nw = v.get("note_w", 0) if note else 0
    cw = round((SPAN16 - (nw + GUT if note else 0) - (len(ties) - 1) * GUT) / len(ties))
    CH = 380
    for i, t in enumerate(ties):
        x = i * (cw + GUT)
        parts[f"t{i}box"] = {"type": "shape", "shape": "rectangle", "text": "", "x": x, "y": row2, "width": cw, "height": CH,
                             "color": "@role_code_bg", "border_color": "@role_code", "border_width": 2, "ink": "@text_primary"}
        parts[f"t{i}head"] = {"type": "text", "text": md(t["head"]), "style": "@style.tile_heading", "ink": "@text_primary",
                              "x": x + 40, "y": row2 + 36, "width": cw - 80, "height": 64}
        parts[f"t{i}text"] = {"type": "text", "text": md(t["text"]), "style": "@style.body", "ink": "@text_primary",
                              "x": x + 40, "y": row2 + 120, "width": cw - 80, "height": CH - 150}
    H = row2 + CH
    name = f"wired_{pid}"
    EXTRA_TEMPLATES[name] = {
        "note": "What comes wired, drawn for one slide by the slide generator: files side by side, and a card per tie.",
        "root": {**CLEAR_AREA, "width": SPAN16, "height": H},
        "parts": parts,
    }
    out = {f"{pid}-wired": {"template": name, "parent": pid, "x": MARGIN, "y": y}}
    if note:
        d, _ = highlight(pid, MARGIN + len(ties) * (cw + GUT), y + row2, nw, note)
        out.update(d)
    return out, H


ROLE_TONES = {"pkit": ("@role_code_bg", "@role_code"), "yours": ("@role_people_bg", "@role_people")}


def roles(pid, y, v):
    """One piece of work from left to right, a card per stop: who (name), what it does (job) and its limit as a
    filled tag, arrows between the cards; under each card the reason for it, in a box with the card's colour as a
    bar on top. Heights are the tallest stop's, so the rows line up. One instance of a template made for this slide."""
    stops = v["stops"]
    n = len(stops)
    gap = 80
    cw = round((SPAN16 - (n - 1) * gap) / n)
    iw = cw - 64
    xs = [i * (cw + gap) for i in range(n)]

    def lines(s, size, w=iw):
        return max(1, -(-text_w(s or "", size) // w))

    HEAD = 72 if v.get("head") else 0
    name_h = max(lines(s["name"], 48) for s in stops) * 60
    job_h = max(lines(s["job"], 36) for s in stops) * 46
    tag_h = max(lines(s.get("limit", ""), 36, iw - 40) for s in stops) * 46 + 20
    card_h = 28 + name_h + 12 + job_h + 20 + tag_h + 28
    why_lines = max(lines(s.get("why", ""), 36, iw - 60) for s in stops)  # a margin: wrapping breaks at words
    why_top = HEAD + card_h + 24
    why_h = 32 + why_lines * 46 + 24
    H = why_top + why_h if any(s.get("why") for s in stops) else HEAD + card_h
    parts = {}

    def shape(key, x, top, w, h, fill, line, bw=2):
        parts[key] = {"type": "shape", "shape": "rectangle", "text": "", "x": round(x), "y": round(top), "width": round(w), "height": round(h),
                      "color": fill, "border_color": line, "border_width": bw, "ink": "@text_primary"}

    def text(key, s, style, x, top, w, h, ink="@text_primary"):
        parts[key] = {"type": "text", "text": md(s), "style": style, "ink": ink, "x": round(x), "y": round(top), "width": round(w), "height": round(h)}

    if v.get("head"):
        text("head", v["head"], "@style.key", 0, 0, SPAN16, 56)
    for i, s in enumerate(stops):
        bg, tone = ROLE_TONES[s.get("tone", "pkit")]
        x = xs[i]
        shape(f"s{i}box", x, HEAD, cw, card_h, bg, tone)
        text(f"s{i}name", s["name"], "@style.tile_heading", x + 32, HEAD + 28, iw, name_h)
        text(f"s{i}job", s["job"], "@style.body", x + 32, HEAD + 28 + name_h + 12, iw, job_h)
        if s.get("limit"):
            th = lines(s["limit"], 36, iw - 40) * 46 + 20
            top = HEAD + card_h - 28 - tag_h
            shape(f"s{i}tag", x + 32, top, iw, th, tone, tone, 1)
            text(f"s{i}tagtext", s["limit"], "@style.body", x + 52, top + 10, iw - 40, th - 20, "@text_on_color")
        if i:
            mid = HEAD + 28 + name_h / 2
            parts[f"s{i}arrow"] = {"type": "arrow", "points": [[xs[i] - gap + 12, round(mid)], [xs[i] - 12, round(mid)]], "arrow_type": "straight",
                                   "tip": "end", "color": "@role_code", "border_width": 6, "border_style": "solid"}
        if s.get("why"):
            shape(f"w{i}box", x, why_top, cw, why_h, "@role_neutral_bg", "@role_neutral_bg", 1)
            shape(f"w{i}bar", x, why_top, cw, 8, tone, tone, 1)
            text(f"w{i}text", s["why"], "@style.body", x + 32, why_top + 32, iw, why_h - 56)
    name = f"roles_{pid}"
    EXTRA_TEMPLATES[name] = {
        "note": "One piece of work and who sees it, drawn for one slide by the slide generator: a card per stop, its limit, and the reason under it.",
        "root": {**CLEAR_AREA, "width": SPAN16, "height": H},
        "parts": parts,
    }
    return {f"{pid}-roles": {"template": name, "parent": pid, "x": MARGIN, "y": y}}, H


ANSWER_TONES = {"updated": ("#DEFBE6FF", "#24A148FF"), "unchanged": ("@role_people_bg", "@role_people"),
                "deferred": ("#FCF4D6FF", "#F1C21BFF")}


def answers(pid, y, v):
    """A change answering for a document: on the left, a heading and a terminal (the check naming the document);
    on the right, a heading, a row per kind of answer (a filled tag in the answer's tone, and what it means), then a
    terminal (the answer as written). Under both, a heading and a box per reason, a bar on top. The headings, tags
    and boxes are one instance of a template made for this slide; the terminals are images."""
    fs = v.get("font_size", 24)
    LW = v.get("left_w", 1200)
    RX = LW + GUT
    RW = SPAN16 - RX
    HEAD = 68
    ROW, RGAP, TAGW = 88, 16, 300
    parts = {}

    def text(key, s, style, x, top, w, h, ink="@text_primary"):
        parts[key] = {"type": "text", "text": md(s), "style": style, "ink": ink, "x": round(x), "y": round(top), "width": round(w), "height": round(h)}

    def shape(key, x, top, w, h, fill, line, bw=1):
        parts[key] = {"type": "shape", "shape": "rectangle", "text": "", "x": round(x), "y": round(top), "width": round(w), "height": round(h),
                      "color": fill, "border_color": line, "border_width": bw, "ink": "@text_primary"}

    left, right = v["left"], v["right"]
    text("lhead", left["head"], "@style.key", 0, 0, LW, 56)
    lfile, lh = terminal_png(f"{pid}-left".removeprefix("T-"), left["terminal"], LW, fs)
    parts["limg"] = {"type": "image", "file": f"{ICONS_DIR}/{lfile}.png", "x": 0, "y": HEAD, "width": LW, "height": lh}
    text("rhead", right["head"], "@style.key", RX, 0, RW, 56)
    top = HEAD
    for i, a in enumerate(right["answers"]):
        bg, tone = ANSWER_TONES[a["tone"]]
        shape(f"a{i}tag", RX, top, TAGW, ROW, tone, tone)
        text(f"a{i}tagtext", a["tag"], "@style.key", RX + 24, top + (ROW - 56) / 2, TAGW - 48, 56, "@text_on_color" if a["tone"] != "deferred" else "@text_primary")
        shape(f"a{i}box", RX + TAGW, top, RW - TAGW, ROW, bg, bg)
        text(f"a{i}text", a["text"], "@style.body", RX + TAGW + 32, top + (ROW - 50) / 2, RW - TAGW - 64, 50)
        top += ROW + RGAP
    rfile, rh = terminal_png(f"{pid}-right".removeprefix("T-"), right["terminal"], RW, fs)
    parts["rimg"] = {"type": "image", "file": f"{ICONS_DIR}/{rfile}.png", "x": RX, "y": top + 8, "width": RW, "height": rh}
    H = max(HEAD + lh, top + 8 + rh)
    why = v.get("why")
    if why:
        wt = H + 40
        n = len(why["items"])
        bw = round((SPAN16 - (n - 1) * GUT) / n)
        lines = max(-(-text_w(t, 36) // (bw - 124)) for t in why["items"])
        bh = 32 + lines * 46 + 24
        text("whyhead", why["head"], "@style.key", 0, wt, SPAN16, 56)
        for i, t in enumerate(why["items"]):
            x = i * (bw + GUT)
            shape(f"w{i}box", x, wt + 68, bw, bh, "@role_neutral_bg", "@role_neutral_bg")
            shape(f"w{i}bar", x, wt + 68, bw, 8, "@role_code", "@role_code")
            text(f"w{i}text", t, "@style.body", x + 32, wt + 68 + 32, bw - 64, lines * 46)
        H = wt + 68 + bh
    name = f"answers_{pid}"
    EXTRA_TEMPLATES[name] = {
        "note": "A change answering for a document, drawn for one slide by the slide generator.",
        "root": {**CLEAR_AREA, "width": SPAN16, "height": H},
        "parts": parts,
    }
    return {f"{pid}-answers": {"template": name, "parent": pid, "x": MARGIN, "y": y}}, H


TAG_TONES = {"core": ("@role_code_bg", "@role_code"), "example": ("#FCF4D6FF", "#F1C21BFF")}


def files(pid, y, v):
    """Real files side by side, in groups: each group a heading over its panels and a tag under it (purple: in core;
    yellow: an example from an add-on), each panel a heading and a terminal. Under them, a heading and a row of
    terminals (the commands that come with it). The headings and tags are one instance of a template made for this
    slide; the terminals are images."""
    groups, below = v["groups"], v.get("below")
    count = sum(len(g["panels"]) for g in groups)
    pw = round((SPAN16 - (count - 1) * GUT) / count)
    fs = v.get("font_size", 22)
    GH, TAG_TOP, TAG_H, PH_TOP = 64, 72, 52, 140
    TERM_TOP = PH_TOP + 60
    parts = {}

    def text(key, s, style, x, top, w, h, ink="@text_primary"):
        parts[key] = {"type": "text", "text": md(s), "style": style, "ink": ink, "x": round(x), "y": round(top), "width": round(w), "height": round(h)}

    def shape(key, x, top, w, h, fill):
        parts[key] = {"type": "shape", "shape": "rectangle", "text": "", "x": round(x), "y": round(top), "width": round(w), "height": round(h),
                      "color": fill, "border_color": fill, "border_width": 1, "ink": "@text_primary"}

    k = 0
    row_h = 0
    for gi, g in enumerate(groups):
        gx = k * (pw + GUT)
        gw = len(g["panels"]) * pw + (len(g["panels"]) - 1) * GUT
        text(f"g{gi}head", g["head"], "@style.tile_heading", gx, 0, gw, GH)
        bg, bar = TAG_TONES[g.get("tone", "core")]
        tw = min(gw, round(text_w(g["tag"], 36)) + 120)
        shape(f"g{gi}tag", gx, TAG_TOP, tw, TAG_H, bg)
        shape(f"g{gi}tagbar", gx, TAG_TOP, 10, TAG_H, bar)
        text(f"g{gi}tagtext", g["tag"], "@style.body", gx + 32, TAG_TOP + 1, tw - 48, 50)
        for p in g["panels"]:
            x = k * (pw + GUT)
            text(f"p{k}head", p["head"], "@style.key", x, PH_TOP, pw, 56)
            file, h = terminal_png(f"{pid}-p{k}".removeprefix("T-"), p["terminal"], pw, fs)
            parts[f"p{k}img"] = {"type": "image", "file": f"{ICONS_DIR}/{file}.png", "x": x, "y": TERM_TOP, "width": pw, "height": h}
            row_h = max(row_h, h)
            k += 1
    H = TERM_TOP + row_h
    if below:
        top = H + 32
        text("bhead", below["head"], "@style.key", 0, top, SPAN16, 56)
        n = len(below["terminals"])
        bw = round((SPAN16 - (n - 1) * GUT) / n)
        bh = 0
        for i, t in enumerate(below["terminals"]):
            file, h = terminal_png(f"{pid}-b{i}".removeprefix("T-"), t, bw, fs)
            parts[f"b{i}img"] = {"type": "image", "file": f"{ICONS_DIR}/{file}.png", "x": i * (bw + GUT), "y": top + 64, "width": bw, "height": h}
            bh = max(bh, h)
        H = top + 64 + bh
    name = f"files_{pid}"
    EXTRA_TEMPLATES[name] = {
        "note": "Real files side by side in groups, and the commands that come with them, drawn for one slide by the slide generator.",
        "root": {**CLEAR_AREA, "width": SPAN16, "height": H},
        "parts": parts,
    }
    return {f"{pid}-files": {"template": name, "parent": pid, "x": MARGIN, "y": y}}, H


WHO_TONES = {"you": "@role_people", "agent": "@role_code"}


def board(pid, y, v):
    """A process as the task board everyone knows: a column per state, an arrow between the column heads, and above
    each arrow who makes that move, in its tone (you blue, the agent purple). One card sits in its column; a dashed red
    arrow from it to the state it may not reach yet, and the reason in red there. Under the board, panels side by side,
    each with a heading: a terminal (the rule as data; what the agent asks), with an optional caption, or a box of
    reasons with a bar on top. The board and the boxes are one instance of a template made for this slide; the
    terminals are images."""
    states, moves, card = v["states"], v["moves"], v["card"]
    n = len(states)
    ag = 96
    sw = round((SPAN16 - (n - 1) * ag) / n)
    xs = [i * (sw + ag) for i in range(n)]
    WHO_H, HEAD_H, LANE_H = 52, 72, 210
    head_top = WHO_H + 8
    lane_top = head_top + HEAD_H + 12
    parts = {}

    def shape(key, x, top, w, h, fill, line, bw=2):
        parts[key] = {"type": "shape", "shape": "rectangle", "text": "", "x": round(x), "y": round(top), "width": round(w), "height": round(h),
                      "color": fill, "border_color": line, "border_width": bw, "ink": "@text_primary"}

    def text(key, s, style, x, top, w, h, ink="@text_primary", align=None):
        parts[key] = {"type": "text", "text": md(s), "style": style, "ink": ink, "x": round(x), "y": round(top), "width": round(w), "height": round(h)}
        if align:
            parts[key]["align"] = align

    for i, s in enumerate(states):
        shape(f"s{i}head", xs[i], head_top, sw, HEAD_H, "#E8DAFFFF", "#E8DAFFFF", 1)
        text(f"s{i}name", s, "@style.key", xs[i] + 24, head_top + 8, sw - 48, 56)
        shape(f"s{i}lane", xs[i], lane_top, sw, LANE_H, "@role_neutral_bg", "@role_neutral_bg", 1)
        if i:
            m = moves[i - 1]
            parts[f"m{i}arrow"] = {"type": "arrow", "points": [[xs[i] - ag + 14, head_top + HEAD_H // 2], [xs[i] - 14, head_top + HEAD_H // 2]],
                                   "arrow_type": "straight", "tip": "end", "color": "@role_code", "border_width": 6, "border_style": "solid"}
            mid = xs[i] - ag / 2
            text(f"m{i}who", m["text"], "@style.body", mid - (sw + ag) / 2, 0, sw + ag, 48, WHO_TONES[m["who"]], "center")
    at, to = card["at"], card["to"]
    cx, cw = xs[at] + 24, sw - 48
    ch = LANE_H - 32
    shape("card", cx, lane_top + 16, cw, ch, "@background", "@role_code", 4)
    text("cardhead", card["head"], "@style.key", cx + 24, lane_top + 32, cw - 48, 56)
    text("cardtext", card["text"], "@style.body", cx + 24, lane_top + 92, cw - 48, 92)
    mid_y = lane_top + 16 + ch / 2
    parts["cardarrow"] = {"type": "arrow", "points": [[cx + cw + 8, round(mid_y)], [xs[to] + 16, round(mid_y)]], "arrow_type": "straight",
                          "tip": "end", "color": "@text_error", "border_width": 6, "border_style": "dashed"}
    text("refusedhead", card["refused"], "@style.key", xs[to] + 40, lane_top + 32, sw - 64, 56, "@text_error")
    text("refusedtext", card["reason"], "@style.body", xs[to] + 40, lane_top + 92, sw - 64, 92, "@text_error")
    board_h = lane_top + LANE_H

    panels = v["panels"]
    pn = len(panels)
    pw = round((SPAN16 - (pn - 1) * GUT) / pn)
    ptop = board_h + 40
    PHEAD = 68
    fs = v.get("font_size", 22)
    images = {}
    heights = []
    for i, p in enumerate(panels):
        if p.get("terminal"):
            file, h = terminal_png(f"{pid}-p{i}".removeprefix("T-"), p["terminal"], pw, fs)
            images[i] = (file, h)
            heights.append(h + (52 if p.get("caption") else 0))
        else:
            iw = pw - 64
            lines = sum(max(1, -(-text_w(t, 36) // (iw - 60))) for t in p["items"])
            heights.append(8 + 28 + lines * 46 + (len(p["items"]) - 1) * 20 + 28)
    body_h = max(heights)
    for i, p in enumerate(panels):
        x = i * (pw + GUT)
        text(f"p{i}head", p["head"], "@style.key", x, ptop, pw, 56)
        top = ptop + PHEAD
        if i in images:
            file, h = images[i]
            parts[f"p{i}img"] = {"type": "image", "file": f"{ICONS_DIR}/{file}.png", "x": x, "y": top, "width": pw, "height": h}
            if p.get("caption"):
                text(f"p{i}caption", p["caption"], "@style.caption", x, top + h + 8, pw, 40, "@text_secondary")
        else:
            shape(f"p{i}box", x, top, pw, body_h, "@role_neutral_bg", "@role_neutral_bg", 1)
            shape(f"p{i}bar", x, top, pw, 8, "@role_code", "@role_code", 1)
            ty = top + 36
            for j, t in enumerate(p["items"]):
                lines = max(1, -(-text_w(t, 36) // (pw - 124)))
                text(f"p{i}item{j}", t, "@style.body", x + 32, ty, pw - 64, lines * 46)
                ty += lines * 46 + 20
    H = ptop + PHEAD + body_h
    name = f"board_{pid}"
    EXTRA_TEMPLATES[name] = {
        "note": "A process as a task board whose moves are checked, drawn for one slide by the slide generator.",
        "root": {**CLEAR_AREA, "width": SPAN16, "height": H},
        "parts": parts,
    }
    return {f"{pid}-board": {"template": name, "parent": pid, "x": MARGIN, "y": y}}, H


def ideas(pid, y, v):
    """Where ideas start: a conversation, the scratchpad note that keeps it, and what the note becomes, the
    products large on the right, the first (records) dark like the pyramid's apex, dropped small below. A box
    per step; the note's picture is a terminal image inside it. One instance of a template made for this slide."""
    W = SPAN16
    fs = v.get("font_size", 26)
    conv, note, prods, dropped = v["conversation"], v["note"], v["becomes"], v["dropped"]
    cw, nw = 600, 960
    nx = cw + 120
    ex = nx + nw + 160
    ew = W - ex
    file, ph = terminal_png(f"{pid}-note".removeprefix("T-"), note["terminal"], nw - 80, fs)
    PROD_H, PROD_GAP, HEAD_H, DROP_H = 172, 24, 72, 96
    prods_top = HEAD_H
    drop_top = prods_top + len(prods) * PROD_H + (len(prods) - 1) * PROD_GAP + 32
    H = drop_top + DROP_H
    conv_h = 136 + 72 + conv.get("text_h", 100) + 40
    note_h = 136 + 72 + note.get("text_h", 100) + 24 + ph + 40
    parts = {}

    def shape(key, x, top, w, h, fill, line):
        parts[key] = {"type": "shape", "shape": "rectangle", "text": "", "x": x, "y": round(top), "width": w, "height": h,
                      "color": fill, "border_color": line, "border_width": 2, "ink": "@text_primary"}

    def text(key, s, style, x, top, w, h, ink="@text_primary"):
        parts[key] = {"type": "text", "text": md(s), "style": style, "ink": ink, "x": x, "y": round(top), "width": w, "height": h}

    for k, s, x, w, top, h in (("conversation", conv, 0, cw, (H - conv_h) / 2, conv_h), ("note", note, nx, nw, (H - note_h) / 2, note_h)):
        shape(f"{k}box", x, top, w, h, "@role_code_bg", "@role_code")
        parts[f"{k}icon"] = {"type": "image", "file": f"{ICONS_DIR}/{s['icon']}.png", "x": x + 40, "y": round(top + 40), "width": 72, "height": 72}
        text(f"{k}head", s["head"], "@style.tile_heading", x + 40, top + 136, w - 80, 64)
        text(f"{k}text", s["text"], "@style.body", x + 40, top + 208, w - 80, s.get("text_h", 100))
    ntop = (H - note_h) / 2
    parts["notepic"] = {"type": "image", "file": f"{ICONS_DIR}/{file}.png", "x": nx + 40, "y": round(ntop + 208 + note.get("text_h", 100) + 24),
                        "width": nw - 80, "height": ph}
    text("rhead", v["becomes_head"], "@style.key", ex, 0, ew, 56)
    for i, p in enumerate(prods):
        top = prods_top + i * (PROD_H + PROD_GAP)
        dark = i == 0
        ink = "@text_on_color" if dark else "@text_primary"
        shape(f"p{i}box", ex, top, ew, PROD_H, "@role_code" if dark else "@role_code_bg", "@role_code")
        text(f"p{i}head", p["head"], "@style.tile_heading", ex + 40, top + 24, ew - 80, 64, ink)
        text(f"p{i}text", p["text"], "@style.body", ex + 40, top + 100, ew - 80, 50, ink)
    shape("dropbox", ex, drop_top, ew, DROP_H, "@role_neutral_bg", "@role_neutral")
    text("droptext", dropped["text"], "@style.body", ex + 40, drop_top + 23, ew - 80, 50)

    def arrow(key, p1, p2, dashed=False):
        parts[key] = {"type": "arrow", "points": [[round(p1[0]), round(p1[1])], [round(p2[0]), round(p2[1])]], "arrow_type": "straight",
                      "tip": "end", "color": "@text_secondary", "border_width": 4, "border_style": "dashed" if dashed else "solid"}

    arrow("a1", (cw + 16, H / 2), (nx - 16, H / 2))
    ends = [prods_top + i * (PROD_H + PROD_GAP) + PROD_H / 2 for i in range(len(prods))] + [drop_top + DROP_H / 2]
    for i, ey in enumerate(ends):
        sy = ntop + note_h * (0.2 + 0.6 * i / (len(ends) - 1))
        arrow(f"b{i}", (nx + nw + 16, sy), (ex - 16, ey), dashed=i == len(prods))
    name = f"ideas_{pid}"
    EXTRA_TEMPLATES[name] = {
        "note": "Where ideas start, drawn for one slide by the slide generator: a conversation, the note that keeps it, and what the note becomes.",
        "root": {**CLEAR_AREA, "width": W, "height": H},
        "parts": parts,
    }
    return {f"{pid}-ideas": {"template": name, "parent": pid, "x": MARGIN, "y": y}}, H


def ties(pid, y, v):
    """Documents' ties: the files they describe on the left, the documents in the middle, the records the
    first carries out on the right, a line for each tie, a broken one red and dashed. A left item ties to
    the documents its `to` lists (the first by default); a `note` stands under it. The diagram is one
    instance of a template made for this slide; the check's output stands beside it."""
    left, right, docs = v["left"], v["right"], v["center"]
    W, lw, cw, rw = 1960, 380, 600, 560
    lx, cx, rx = 0, 600, 1960 - 560
    n = max(len(left), len(right))
    body = n * TIES_ROW - (TIES_ROW - TIES_NODE_H)
    H = TIES_HEAD_H + body + (52 if any(it.get("note") for it in left) else 0)
    # the documents: one in the middle; two, the first at the top and the last at the foot
    heights = [d.get("height", TIES_CENTER_H) for d in docs]
    if len(docs) == 1:
        tops = [TIES_HEAD_H + body / 2 - heights[0] / 2]
    else:
        tops = [TIES_HEAD_H + 16, TIES_HEAD_H + body - heights[1]]
    parts = {
        "lhead": {"type": "text", "text": md(v["left_head"]), "style": "@style.key", "ink": "@text_primary", "x": lx, "y": 0, "width": lw + 200, "height": 56},
        "rhead": {"type": "text", "text": md(v["right_head"]), "style": "@style.key", "ink": "@text_primary", "x": rx, "y": 0, "width": rw, "height": 56},
    }
    for k, (d, top, h) in enumerate(zip(docs, tops, heights)):
        p = "c" if k == 0 else f"c{k}"
        parts[f"{p}box"] = {"type": "shape", "shape": "rectangle", "text": "", "x": cx, "y": round(top), "width": cw, "height": h,
                            "color": "@background", "border_color": "@text_primary", "border_width": 4, "ink": "@text_primary"}
        parts[f"{p}head"] = {"type": "text", "text": md(d["head"]), "style": "@style.key", "ink": "@text_primary", "x": cx + 32, "y": round(top + h / 2 - 56), "width": cw - 64, "height": 56}
        parts[f"{p}path"] = {"type": "text", "text": md(d["path"]), "style": "@style.body", "x": cx + 32, "y": round(top + h / 2 + 4), "width": cw - 64, "height": 50}

    def end(k, i, count):
        # where a tie meets document k's edge: spread along it, the i-th of count
        top, h = tops[k], heights[k]
        return top + h / 2 if count == 1 else top + 20 + i * (h - 40) / (count - 1)

    def column(items, side, x, w):
        off = (n - len(items)) * TIES_ROW / 2
        for i, it in enumerate(items):
            ny = TIES_HEAD_H + off + i * TIES_ROW
            broken = it.get("broken", False)
            bg, tone = TIES_TONES[it.get("tone", "code")]
            parts[f"{side}{i}box"] = {"type": "shape", "shape": "rectangle", "text": "", "x": x, "y": round(ny), "width": w, "height": TIES_NODE_H,
                                     "color": "@background" if broken else f"@{bg}", "border_color": "@text_error" if broken else f"@{tone}",
                                     "border_width": 4 if broken else 2, "ink": "@text_primary"}
            parts[f"{side}{i}text"] = {"type": "text", "text": md(it["label"]), "style": "@style.body", "ink": "@text_error" if broken else "@text_primary",
                                      "x": x + 20, "y": round(ny + 6), "width": w - 40, "height": 50}
            if it.get("note"):
                parts[f"{side}{i}note"] = {"type": "text", "text": md(it["note"]), "style": "@style.caption", "ink": "@text_error",
                                          "x": x, "y": round(ny + TIES_NODE_H + 8), "width": w + 160, "height": 40}
            for k in it.get("to", [0]):
                ey = end(k, i, len(items)) if k == 0 else end(k, 0, 1)
                x1, x2 = (x + w, cx) if side == "l" else (x, cx + cw)
                parts[f"{side}{i}tie" + (str(k) if k else "")] = {
                    "type": "arrow", "points": [[x1, round(ny + TIES_NODE_H / 2)], [x2, round(ey)]], "arrow_type": "straight", "tip": "none",
                    "color": "@text_error" if broken else "@border_strong", "border_width": 4, "border_style": "dashed" if broken else "solid"}

    column(left, "l", lx, lw)
    column(right, "r", rx, rw)
    name = f"ties_{pid}"
    EXTRA_TEMPLATES[name] = {
        "note": "Documents' ties, drawn for one slide by the slide generator: the files they describe, the records they carry out, a line per tie.",
        "root": {**CLEAR_AREA, "width": W, "height": H},
        "parts": parts,
    }
    out = {f"{pid}-ties": {"template": name, "parent": pid, "x": MARGIN, "y": y}}
    tx = MARGIN + W + 64
    d, th = terminal(pid, tx, y, MARGIN + SPAN16 - tx, v["terminal"], key="check", font_size=v.get("font_size", 24))
    d[f"{pid}-check"]["y"] = y + H - th  # level with the broken tie, at the diagram's foot
    out.update(d)
    return out, H


PYR_H, PYR_GAP = 172, 18


def pyramid(pid, y, v):
    """A stepped pyramid of layers, the top first, and a column of relations beside it."""
    out = {}
    levels = v["levels"]
    cx = v.get("center", 1180)
    top_w, step = v.get("top_w", 760), v.get("step", 300)
    lh = v.get("level_h", PYR_H)
    for i, lv in enumerate(levels):
        w = top_w + i * step
        x = round(cx - w / 2)
        yy = y + i * (lh + PYR_GAP)
        k, val = stage(pid, i + 1, x, yy, w, "neutral", lv["head"], lv.get("text", ""), lh)
        val["override"]["box"] = {"width": w, "height": lh, "color": lv["fill"], "border_color": lv["fill"]}
        val["override"]["dot"] = {"color": lv["fill"], "border_color": lv["fill"]}
        val["override"]["head"] = {"x": 32, "y": 22, "width": w - 64, "height": 64, "align": "center", "ink": lv["ink"]}
        val["override"]["text"] = {"x": 32, "y": 92, "width": w - 64, "height": lh - 110, "align": "center", "ink": lv["ink"]}
        out[k] = val
    h = len(levels) * lh + (len(levels) - 1) * PYR_GAP
    # the relations: a box per relation, on the right with an arrow beside it (down, up) or into the
    # apex (left), or on the left with an arrow into the apex (right); a box of role code is tinted purple
    sx = v.get("side_x", 2240)
    sw = MARGIN + SPAN16 - sx
    li = 100
    for j, sd in enumerate(v["side"]):
        sy = y + sd["at"]
        sh = sd.get("h", 240)
        arrow = sd.get("arrow", "down")
        role = sd.get("role", "neutral")
        if arrow == "right":
            tx, tw = MARGIN, sd.get("w", 600)
        else:
            tx, tw = sx + LINK_W + 16, sw - LINK_W - 16
        k, val = stage(pid, 50 + j, tx, sy, tw, role, sd["head"], sd.get("text", ""), sh)
        k, val = styled((k, val), PAIR_STYLES["tinted"]["right" if role == "code" else "left"])
        out[k] = val
        li += 1
        if arrow == "right":
            ax = round(tx + tw + 8)
            aw = round(cx - top_w / 2 - 16 - ax)
            ah = min(sh, PYR_H)
            out[f"{pid}-l{li}"] = {"template": "link", "parent": pid, "x": ax, "y": sy, "x1": 8, "y1": ah / 2, "x2": aw - 8, "y2": ah / 2,
                                   "tone": "role_code", "override": {"root": {"width": aw, "height": ah}, "arrow": {"border_width": 6}}}
        elif arrow == "left":
            apex_right = cx + top_w / 2
            ax = round(apex_right + 16)
            aw = round(tx - ax - 8)
            # no taller than the apex, so the arrow's frame stays clear of the layer below it
            ah = min(sh, PYR_H)
            out[f"{pid}-l{li}"] = {"template": "link", "parent": pid, "x": ax, "y": sy, "x1": aw - 8, "y1": ah / 2, "x2": 8, "y2": ah / 2,
                                   "tone": "role_code", "override": {"root": {"width": aw, "height": ah}, "arrow": {"border_width": 6}}}
        else:
            y1, y2 = (8, sh - 8) if arrow == "down" else (sh - 8, 8)
            out[f"{pid}-l{li}"] = {"template": "link", "parent": pid, "x": sx, "y": sy, "x1": LINK_W / 2, "y1": y1, "x2": LINK_W / 2, "y2": y2,
                                   "tone": "role_code", "override": {"root": {"width": LINK_W, "height": sh}, "arrow": {"border_width": 6}}}
    return out, h


def rules(pid, y, v):
    """One rule's way as a slice of the pyramid, its layers stacked as the pyramid's are, and beside it a
    terminal of what a session loads at its start and what it looks up when needed."""
    out, h = pyramid(pid, y, {**v, "side": []})
    widest = v["top_w"] + (len(v["levels"]) - 1) * v["step"]
    tx = round(v["center"] + widest / 2 + 80)
    d, th = terminal(pid, tx, y, MARGIN + SPAN16 - tx, v["terminal"], key="loads", font_size=v.get("font_size", 30))
    d[f"{pid}-loads"]["y"] = round(y + (h - th) / 2) if th < h else y
    out.update(d)
    return out, max(h, th)


def install(pid, y, v):
    """The commands as two tinted steps with pictograms on the left, the project's tree on the right."""
    out = {}
    w = SPAN8
    hs = []
    yy = y
    if v.get("terminal"):
        d, th = terminal(pid, MARGIN, y, w, v["terminal"], font_size=v.get("font_size", 30))
        out.update(d)
        yy = y + th
    if v.get("highlight"):
        yy += GAP
        d, hh = highlight(pid, MARGIN, yy, w, v["highlight"])
        out.update(d)
        yy += hh
    for i, st in enumerate(v.get("steps") or []):
        h = st.get("h", 260)
        k, val = with_icon(stage(pid, i + 1, MARGIN, yy, w, "code", st["head"], st["text"], h), st["icon"], w, h)
        k, val = styled((k, val), PAIR_STYLES["tinted"]["right"])
        out[k] = val
        yy += h
        if i < len(v.get("steps") or []) - 1:
            if v["steps"][i + 1].get("arrow", True):
                k, val = vlink(pid, i + 1, round(MARGIN + w / 2 - LINK_W / 2), yy, 96)
                out[k] = val
                yy += 96
            else:
                yy += GAP
    left_h = yy - y
    if v.get("listing"):
        d, right_h = terminal(pid, MARGIN + SPAN8 + GUT, y, SPAN8, v["listing"], key="listing", font_size=v.get("font_size", 30))
    else:
        d, right_h = tree(pid, MARGIN + SPAN8 + GUT, y, [(r[0], [tuple(t) for t in r[1]], r[2]) for r in v["tree"]], [tuple(t) for t in v.get("legend") or []])
    out.update(d)
    return out, max(left_h, right_h)


def flow(pid, y, stages):
    out = {}
    n = len(stages)
    w = (SPAN16 - (n - 1) * LINK_W) / n
    x = MARGIN
    for i, s in enumerate(stages, 1):
        k, v = stage(pid, i, round(x), y, round(w), s.get("role", "neutral"), s["head"], s.get("text", ""))
        out[k] = v
        x += w
        if i < n:
            k, v = link(pid, i, round(x), y)
            out[k] = v
            x += LINK_W
    return out, STAGE_H


def steps(pid, y, items, x0=MARGIN, width=SPAN16, per_row=None):
    out = {}
    n = len(items)
    per_row = per_row or n
    w = (width - (per_row - 1) * GUT) / per_row
    rows = (n + per_row - 1) // per_row
    for i, text in enumerate(items):
        r, c = divmod(i, per_row)
        x = x0 + c * (w + GUT)
        yy = y + r * (STEP_H + GAP)
        out[f"{pid}-d{i + 1}"] = {
            "template": "step", "parent": pid, "ident": str(i + 1), "text": md(text), "x": round(x), "y": round(yy),
            "override": {
                "root": {"width": round(w)},
                "bg": {"width": round(w)},
                "text": {"width": round(w - 64)},
            },
        }
    return out, rows * STEP_H + (rows - 1) * GAP


def cards(pid, y, items):
    out = {}
    n = len(items)
    w = (SPAN16 - (n - 1) * GUT) / n
    for i, c in enumerate(items):
        x = MARGIN + i * (w + GUT)
        out[f"{pid}-c{i + 1}"] = {
            "template": "card", "parent": pid, "ident": c["ident"], "space": c.get("space", "tech"),
            "space_label": c.get("space_label", ""), "heading": md(c["heading"]), "body": md(c["body"]),
            "x": round(x), "y": y,
            "override": {
                "root": {"width": round(w)},
                "bg": {"width": round(w)},
                "heading": {"width": round(w - 64)},
                "body": {"width": round(w - 64)},
            },
        }
    return out, CARD_H


def compare(pid, y, left, right):
    out = {}
    for i, (side, x) in enumerate(((left, MARGIN), (right, MARGIN + SPAN8 + GUT)), 1):
        out[f"{pid}-cmp{i}"] = {"template": "compare", "parent": pid, **{k: md(v) for k, v in side.items()}, "x": x, "y": y}
    return out, 576


def actors(pid, y, items):
    out = {}
    n = len(items)
    gap = (SPAN16 - n * ACTOR_W) / (n - 1) if n > 1 else 0
    for i, a in enumerate(items):
        out[f"{pid}-a{i + 1}"] = {
            "template": "actor", "parent": pid, "icon": a["icon"], "name": md(a["name"]), "role": a.get("role", "neutral"),
            "x": round(MARGIN + i * (ACTOR_W + gap)), "y": y,
        }
    return out, ACTOR_H


def code(pid, y, text, x=MARGIN + SPAN8 + GUT, h=None, key="code"):
    lines = text.rstrip("\n").count("\n") + 1
    hh = h or max(304, 64 + lines * 48)
    return {
        f"{pid}-{key}": {
            "template": "code", "parent": pid, "code": text.rstrip("\n"), "x": x, "y": y,
            "override": {"root": {"height": hh}, "bg": {"height": hh}, "text": {"height": hh - 64}},
        }
    }, hh


def callout(pid, y, title, body):
    return {f"{pid}-problem": {"template": "callout", "parent": pid, "title": title, "body": md(body), "x": MARGIN, "y": y}}, CALLOUT_H


def notice(pid, y, text):
    return {f"{pid}-limit": {"template": "notice", "parent": pid, "text": md(text), "x": MARGIN, "y": y}}, NOTICE_H


LABELS = {
    "en": {"limit": "Limit: ", "part": "Part {part}", "version": "Version {version} · {date}"},
    "cs": {"limit": "Omezení: ", "part": "Část {part}", "version": "Verze {version} · {date}"},
}


def build_slide(s, n, total, prefix="T-", labels=LABELS["en"]):
    pid = f"{prefix}{s['id']}"
    inst = {
        pid: {
            "template": "slide", "title": md(s["title"]), "lead": md(s["message"]), "rests": md(s.get("show") or " "),
            "n": n, "total": total,
            "override": {"rests": {"text": md(s.get("show") or "")}},
        }
    }
    v = s.get("visual") or {}
    kind = v.get("kind", "none")
    y = CONTENT_Y
    parts = {}

    def add(d_h):
        nonlocal y
        d, h = d_h
        parts.update(d)
        y += h + GAP

    if s["id"] == "opening" and kind == "cards":
        add(steps(pid, y, s["does"]))
        add(cards(pid, y, v["cards"]))
    elif kind == "cards":
        add(cards(pid, y, v["cards"]))
    elif kind == "none":
        pass
    else:
        if s.get("problem"):
            add(callout(pid, y, "The problem", s["problem"]))
        if kind in ("flow", "lifecycle"):
            st = v.get("stages") or [{"role": "neutral", "head": h, "text": ""} for h in v["states"]]
            add(flow(pid, y, st))
            if v.get("terminal"):
                add(terminal(pid, MARGIN, y, SPAN16, v["terminal"], font_size=v.get("font_size", 30)))
            if v.get("panel_left"):
                fs = v.get("font_size", 30)
                d1, h1 = terminal(pid, MARGIN, y, SPAN8, v["panel_left"], key="left", font_size=fs)
                d2, h2 = terminal(pid, MARGIN + SPAN8 + GUT, y, SPAN8, v["panel_right"], key="right", font_size=fs)
                parts.update(d1)
                parts.update(d2)
                y += max(h1, h2) + GAP
            if v.get("code"):
                d1, h1 = steps(pid, y, s["does"], x0=MARGIN, width=SPAN8, per_row=2) if s.get("does") else ({}, 0)
                d2, h2 = code(pid, y, v["code"])
                parts.update(d1)
                parts.update(d2)
                y += max(h1, h2) + GAP
            elif s.get("does"):
                add(steps(pid, y, s["does"]))
            if v.get("cards"):
                add(cards(pid, y, v["cards"]))
        elif kind == "compare":
            add(compare(pid, y, v["left"], v["right"]))
        elif kind == "kinds":
            add(kinds(pid, y, v))
        elif kind == "ideas":
            add(ideas(pid, y, v))
        elif kind == "rules":
            add(rules(pid, y, v))
        elif kind == "checklist":
            add(checklist(pid, y, v))
        elif kind == "map":
            add(table_map(pid, y, v))
        elif kind == "roles":
            add(roles(pid, y, v))
        elif kind == "board":
            add(board(pid, y, v))
        elif kind == "files":
            add(files(pid, y, v))
        elif kind == "answers":
            add(answers(pid, y, v))
        elif kind == "wired":
            add(wired(pid, y, v))
        elif kind == "ties":
            add(ties(pid, y, v))
        elif kind == "story":
            add(story(pid, y, v))
        elif kind == "pyramid":
            add(pyramid(pid, y, v))
        elif kind == "install":
            add(install(pid, y, v))
            if v.get("stages"):
                add(flow(pid, y, v["stages"]))
        elif kind == "code2":
            lines = max(v["left"].rstrip("\n").count("\n"), v["right"].rstrip("\n").count("\n")) + 1
            hh = max(304, 64 + lines * 48)
            d1, _ = code(pid, y, v["left"], x=MARGIN, h=hh, key="code-left")
            d2, _ = code(pid, y, v["right"], h=hh, key="code-right")
            parts.update(d1)
            parts.update(d2)
            y += hh + GAP
        elif kind == "pairs":
            add(pairs(pid, y, v["pairs"], v.get("style", "plain"), bool(v.get("icons"))))
        elif kind == "fanout":
            add(fanout(pid, y, v))
            if s.get("does"):
                add(steps(pid, y, s["does"]))
        elif kind == "actors":
            add(actors(pid, y, v["actors"]))
            if s.get("does"):
                add(steps(pid, y, s["does"]))
        elif kind == "code":
            d1, h1 = steps(pid, y, s["does"], x0=MARGIN, width=SPAN8, per_row=2) if s.get("does") else ({}, 0)
            d2, h2 = code(pid, y, v["code"])
            parts.update(d1)
            parts.update(d2)
            y += max(h1, h2) + GAP
        if s.get("limit"):
            add(notice(pid, y, labels["limit"] + s["limit"]))
        if s.get("footnote"):
            add(notice(pid, y, s["footnote"]))
    inst.update(parts)
    if y - GAP > 1640:
        print(f"warn: {pid} content reaches y={y - GAP:.0f}, past the footer", file=sys.stderr)
    return inst


DIVIDER_TEMPLATE = {
    "note": "A divider between two versions of the talk: an empty slide-sized area with one large line; made by the slide generator.",
    "root": {**CLEAR_AREA, "width": GRID_W, "height": 1800},
    "parts": {"text": {"type": "text", "text": "{text}", "style": "@style.title", "ink": "@text_secondary", "align": "center",
                       "x": MARGIN, "y": 820, "width": GRID_W - 2 * MARGIN, "height": 160}},
}


TALK_COVER_TEMPLATE = {
    "note": "The talk's cover, made by the slide generator: no logo; an accent bar, the title, the project as a subtitle in pkit's purple, the author, the project's address, and the version with its date.",
    "root": {**CLEAR_AREA, "width": GRID_W, "height": 1800},
    "parts": {
        "bg": {"type": "shape", "shape": "rectangle", "text": "", "x": 0, "y": 0, "width": GRID_W, "height": 1800,
               "color": "@background", "border_color": "@border_subtle", "border_width": 2, "ink": "@text_primary"},
        "bar": {"type": "shape", "shape": "rectangle", "text": "", "x": MARGIN, "y": 600, "width": 160, "height": 8,
                "color": "@interactive", "border_color": "@interactive", "border_width": 1, "ink": "@text_primary"},
        "title": {"type": "text", "text": "{title}", "style": "@style.title", "ink": "@text_primary", "x": MARGIN, "y": 640, "width": SPAN16, "height": 160},
        "subtitle": {"type": "text", "text": "{subtitle}", "style": "@style.lead", "ink": "@role_code", "x": MARGIN, "y": 816, "width": SPAN16, "height": 96},
        "author": {"type": "text", "text": "{author}", "style": "@style.key", "ink": "@text_secondary", "x": MARGIN, "y": 1000, "width": SPAN8, "height": 64},
        "link": {"type": "text", "text": "{link}", "style": "@style.body", "ink": "@interactive", "x": MARGIN, "y": 1072, "width": SPAN8, "height": 56},
        "version": {"type": "text", "text": "{version}", "style": "@style.caption", "ink": "@text_helper", "x": MARGIN, "y": 1640, "width": SPAN8, "height": 48},
    },
}


def build_set(sl, prefix, labels, new, rows, order):
    """One version of the talk: its cover, then per part its section and its slides, each part a row."""
    talk = sl["talk"]
    content = [s for s in sl["slides"]]
    total = len(content)
    cover = f"{prefix}cover"
    new[cover] = {
        "template": "talk_cover", "title": talk["title"], "subtitle": talk.get("project", "project-kit (pkit)"),
        "author": talk["author"], "link": talk["link"], "version": labels["version"].format(version=talk["version"], date=talk["date"]),
    }
    rows[cover] = [cover]
    order.append(cover)
    for i, p in enumerate(sl["parts"], 1):
        sid = f"{prefix}part-{p['id']}"
        if p.get("section", True):
            new[sid] = {"template": "section", "part": str(i), "title": p["title"], "summary": p["summary"],
                        "override": {"eyebrow": {"text": labels["part"].format(part=i)}}}
            rows[sid] = [sid]
        else:  # slides on a row of their own, with no section before them (the closing questions)
            rows[sid] = []
        order.append(sid)
        for s in content:
            if s["part"] == p["id"]:
                n = content.index(s) + 1
                new.update(build_slide(s, n, total, prefix, labels))
                rows[sid].append(f"{prefix}{s['id']}")
        # Variants of a slide, to choose from: after the part's last slide, so nothing moves.
        for var in sl.get("variants") or []:
            of = next(s for s in content if s["id"] == var["of"])
            if of["part"] == p["id"]:
                new.update(build_slide({**var, "part": p["id"]}, content.index(of) + 1, total, prefix, labels))
                rows[sid].append(f"{prefix}{var['id']}")


def main(slides_path, board_path, cs_path=None):
    global MAP_DIR
    from pathlib import Path

    MAP_DIR = str(Path(board_path).resolve().parent)
    sl = yaml.safe_load(open(slides_path))
    board = yaml.safe_load(open(board_path))
    # Keep what a push recorded: each instance's board ids and each row's frozen origin, so a
    # regeneration updates the board in place instead of creating every slide again.
    old_ids = {k: v["mural_ids"] for k, v in board["instances"].items() if k.startswith("T-") and v.get("mural_ids")}
    old_origin = {}
    for lay in board.get("layouts") or []:
        members = lay.get("row") or lay.get("stack") or lay.get("grid") or []
        if members and str(members[0]).startswith("T-"):
            old_origin[members[0]] = lay.get("origin", "auto")
    board["instances"] = {k: v for k, v in board["instances"].items() if not k.startswith("T-")}
    board["templates"]["pstage"] = pstage_template(board["templates"]["stage"])
    board["templates"].update(TREE_TEMPLATES)
    board["templates"]["terminal"] = TERMINAL_TEMPLATE
    board["templates"]["term_image"] = TERM_IMAGE_TEMPLATE
    board["templates"]["highlight"] = HIGHLIGHT_TEMPLATE
    board["templates"]["kind"] = KIND_TEMPLATE
    board["templates"]["kind_group"] = GROUP_TEMPLATE
    board["templates"]["step_card"] = step_card_template(board["templates"]["stage"])
    board["templates"]["talk_cover"] = TALK_COVER_TEMPLATE
    board["layouts"] = [lay for lay in board.get("layouts") or [] if not any(str(x).startswith("T-") for x in (lay.get("row") or lay.get("stack") or lay.get("grid") or []))]
    new, rows, order = {}, {}, []
    build_set(sl, "T-", LABELS["en"], new, rows, order)
    if cs_path:
        # The Czech version, under the English one: a divider slide first, then the same talk in Czech.
        board["templates"]["divider"] = DIVIDER_TEMPLATE
        new["T-cs-divider"] = {"template": "divider", "text": "Česká verze"}
        rows["T-cs-divider"] = ["T-cs-divider"]
        order.append("T-cs-divider")
        build_set(yaml.safe_load(open(cs_path)), "T-cs-", LABELS["cs"], new, rows, order)
    board["templates"].update(EXTRA_TEMPLATES)
    for k, v in new.items():
        if k in old_ids:
            v["mural_ids"] = old_ids[k]
    board["instances"].update(new)
    for sid in order:
        if rows[sid]:
            board["layouts"].append({"row": rows[sid], "origin": old_origin.get(rows[sid][0], "auto"), "gap": 400})
    yaml.safe_dump(board, open(board_path, "w"), sort_keys=False, allow_unicode=True, width=200)
    print(f"generated {len(new)} instances in {len(order)} rows")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
