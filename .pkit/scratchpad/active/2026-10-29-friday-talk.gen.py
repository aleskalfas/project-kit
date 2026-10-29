"""Generate the Friday talk's slide instances into the board map.

Reads the slides' content (…friday-talk.slides.yaml) and writes instances of the
board library's templates into the board map (…friday-talk.board.yaml), replacing
every instance and layout it generated before (ids starting with "T-"). Library
masters and LIB objects are left untouched.

Usage: python gen_slides.py <slides.yaml> <board.yaml>
"""

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
        "branch": "#A8A8A8", "pkit": "#6929C4", "yours": "#0043CE", "plain": "#161616"}
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
        elif line.lstrip().startswith("#"):
            out.append([(line, "comment")])
        elif line.startswith("$ "):
            cmd, _, rest = line[2:].partition(" ")
            out.append([("$ ", "prompt"), (cmd, "command")] + ([(" " + rest, "args")] if rest else []))
        else:
            out.append([(line, "output")])
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


KIND_H, KIND_GAP = 192, 24
KIND_TEMPLATE = {
    "note": "A kind of record: a tinted row in its owner's colour with a filled tag (its prefix), a head, a line of text and a path; made by the slide generator.",
    "root": {**CLEAR_AREA, "width": 1440, "height": KIND_H},
    "parts": {
        "bg": {"type": "shape", "shape": "rectangle", "text": "", "x": 0, "y": 0, "width": 1440, "height": KIND_H,
               "color": "@{bg}", "border_color": "@{tone}", "border_width": 2, "ink": "@text_primary"},
        "tag": {"type": "shape", "shape": "rectangle", "text": "", "x": 32, "y": 28, "width": 136, "height": 64,
                "color": "@{tone}", "border_color": "@{tone}", "border_width": 1, "ink": "@text_on_color"},
        "tagtext": {"type": "text", "text": "{tag}", "style": "@style.key", "ink": "@text_on_color", "x": 32, "y": 30, "width": 136, "height": 60, "align": "center"},
        "head": {"type": "text", "text": "{head}", "style": "@style.key", "ink": "@text_primary", "x": 200, "y": 24, "width": 1208, "height": 60},
        "text": {"type": "text", "text": "{text}", "style": "@style.body", "x": 200, "y": 86, "width": 1208, "height": 50},
        "path": {"type": "text", "text": "{path}", "style": "@style.caption", "ink": "@text_secondary", "x": 200, "y": 138, "width": 1208, "height": 40},
    },
}
KIND_TONES = {"pkit": ("role_code_bg", "role_code"), "yours": ("role_people_bg", "role_people")}


def kinds(pid, x, y, w, items):
    """The kinds of a thing as rows, each tinted in its owner's colour (pkit's purple, yours blue)."""
    out = {}
    for i, it in enumerate(items):
        bg, tone = KIND_TONES[it.get("owner", "pkit")]
        out[f"{pid}-k{i + 1}"] = {
            "template": "kind", "parent": pid, "x": x, "y": round(y + i * (KIND_H + KIND_GAP)),
            "tag": it["tag"], "head": md(it["head"]), "text": md(it["text"]), "path": md(it["path"]), "bg": bg, "tone": tone,
            "override": {"root": {"width": w}, "bg": {"width": w}, "head": {"width": w - 232}, "text": {"width": w - 232}, "path": {"width": w - 232}},
        }
    n = len(items)
    return out, n * KIND_H + (n - 1) * KIND_GAP


PYR_H, PYR_GAP = 172, 18


def pyramid(pid, y, v):
    """A stepped pyramid of layers, the top first, and a column of relations beside it."""
    out = {}
    levels = v["levels"]
    cx = v.get("center", 1180)
    top_w, step = v.get("top_w", 760), v.get("step", 300)
    for i, lv in enumerate(levels):
        w = top_w + i * step
        x = round(cx - w / 2)
        yy = y + i * (PYR_H + PYR_GAP)
        k, val = stage(pid, i + 1, x, yy, w, "neutral", lv["head"], lv.get("text", ""), PYR_H)
        val["override"]["box"] = {"width": w, "height": PYR_H, "color": lv["fill"], "border_color": lv["fill"]}
        val["override"]["dot"] = {"color": lv["fill"], "border_color": lv["fill"]}
        val["override"]["head"] = {"x": 32, "y": 22, "width": w - 64, "height": 64, "align": "center", "ink": lv["ink"]}
        val["override"]["text"] = {"x": 32, "y": 92, "width": w - 64, "height": PYR_H - 110, "align": "center", "ink": lv["ink"]}
        out[k] = val
    h = len(levels) * PYR_H + (len(levels) - 1) * PYR_GAP
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
    if v.get("kinds"):
        d, kh = kinds(pid, MARGIN, yy, w, v["kinds"])
        out.update(d)
        yy += kh
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


def build_slide(s, n, total):
    pid = f"T-{s['id']}"
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
            add(notice(pid, y, "Limit: " + s["limit"]))
        if s.get("footnote"):
            add(notice(pid, y, s["footnote"]))
    inst.update(parts)
    if y - GAP > 1640:
        print(f"warn: {pid} content reaches y={y - GAP:.0f}, past the footer", file=sys.stderr)
    return inst


def main(slides_path, board_path):
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
    board["layouts"] = [lay for lay in board.get("layouts") or [] if not any(str(x).startswith("T-") for x in (lay.get("row") or lay.get("stack") or lay.get("grid") or []))]
    talk = sl["talk"]
    content = [s for s in sl["slides"]]
    total = len(content)
    new = {}
    new["T-cover"] = {
        "template": "cover", "project": talk.get("project", "project-kit"), "title": talk["title"], "author": talk["author"],
        "date": talk["date"], "version": talk["version"],
        "override": {"logo": {"file": "2026-10-29-friday-talk-icons/agents.png"}},
    }
    rows = {"T-cover": ["T-cover"]}
    order = ["T-cover"]
    for i, p in enumerate(sl["parts"], 1):
        sid = f"T-part-{p['id']}"
        new[sid] = {"template": "section", "part": str(i), "title": p["title"], "summary": p["summary"]}
        rows[sid] = [sid]
        order.append(sid)
        for s in content:
            if s["part"] == p["id"]:
                n = content.index(s) + 1
                new.update(build_slide(s, n, total))
                rows[sid].append(f"T-{s['id']}")
        # Variants of a slide, to choose from: after the part's last slide, so nothing moves.
        for var in sl.get("variants") or []:
            of = next(s for s in content if s["id"] == var["of"])
            if of["part"] == p["id"]:
                new.update(build_slide({**var, "part": p["id"]}, content.index(of) + 1, total))
                rows[sid].append(f"T-{var['id']}")
    for k, v in new.items():
        if k in old_ids:
            v["mural_ids"] = old_ids[k]
    board["instances"].update(new)
    for sid in order:
        board["layouts"].append({"row": rows[sid], "origin": old_origin.get(sid, "auto"), "gap": 400})
    yaml.safe_dump(board, open(board_path, "w"), sort_keys=False, allow_unicode=True, width=200)
    print(f"generated {len(new)} instances in {len(order)} rows")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
