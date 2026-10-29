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


def code(pid, y, text, x=MARGIN + SPAN8 + GUT, h=None):
    lines = text.rstrip("\n").count("\n") + 1
    hh = h or max(304, 64 + lines * 48)
    return {
        f"{pid}-code": {
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

    if s["id"] == "opening":
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
            if s.get("does"):
                add(steps(pid, y, s["does"]))
        elif kind == "compare":
            add(compare(pid, y, v["left"], v["right"]))
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
    inst.update(parts)
    if y - GAP > 1640:
        print(f"warn: {pid} content reaches y={y - GAP:.0f}, past the footer", file=sys.stderr)
    return inst


def main(slides_path, board_path):
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
