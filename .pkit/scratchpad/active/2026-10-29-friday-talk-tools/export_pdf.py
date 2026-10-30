"""Write the talk as PDFs, one page per slide in the board's order, one file per language.

Mural's API exports only the whole board, as one PDF page. This script exports it, lists the board
through the mural-boards tool's own API client (its login stays its own), and cuts that page into one
page per slide: the slide rows of the map's layouts, top to bottom, each row left to right. A row
holding a divider instance starts the next language; the divider itself is left out.

The page draws the board's top-level extent at one scale with an equal margin on every side, so the
scale and margin follow from the page size and that extent. A slide title found by text checks the fit.
Each slide page is the board page with everything outside the slide taken out and cropped to it, so it
stays vector and holds only its own text and images.

Usage (--pdf reuses an export instead of making one):
uv run --no-project --with pyyaml --with jsonschema --with pymupdf python export_pdf.py <tool.py> <map.yaml> <out-dir> [--pdf <board.pdf>]
"""

import importlib.util
import re
import sys
import time
import urllib.request
from pathlib import Path

import pymupdf
import yaml


def load_tool(tool_path):
    spec = importlib.util.spec_from_file_location("mural_boards", tool_path)
    mb = importlib.util.module_from_spec(spec)
    sys.modules["mural_boards"] = mb
    spec.loader.exec_module(mb)
    return mb


def export_board(mb, api, mural, out):
    started = api.call("POST", f"/murals/{mural}/export", {"downloadFormat": "pdf"}, repeatable=False)
    export_id = (started.get("value") or started)["exportId"]
    for _ in range(72):
        time.sleep(5)
        try:
            got = api.call("GET", f"/murals/{mural}/exports/{export_id}")
        except mb.ApiError:
            continue  # 404 until the export is ready
        body = got.get("value") or got
        if body.get("url"):
            urllib.request.urlretrieve(body["url"], out)
            return out
    raise SystemExit("the board export did not finish in six minutes")


def parent(w):
    p = w.get("parentId")
    return p.get("id") if isinstance(p, dict) else p


def plain(w):
    return re.sub(r"<[^>]+>", "", w.get("text") or w.get("htmlText") or "").strip()


def main(tool_path, map_path, out_dir, pdf=None):
    mb = load_tool(tool_path)
    data = yaml.safe_load(open(map_path))
    api = mb.Mural()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(map_path).name.removesuffix(".board.yaml")
    if not pdf:
        pdf = export_board(mb, api, data["mural"], out_dir / f"{stem}.board.pdf")
    widgets = api.widgets(data["mural"])
    by_id = {w["id"]: w for w in widgets}

    top = [w for w in widgets if not parent(w)]
    x0 = min(w["x"] for w in top)
    y0 = min(w["y"] for w in top)
    bw = max(w["x"] + w["width"] for w in top) - x0
    bh = max(w["y"] + w["height"] for w in top) - y0
    src = pymupdf.open(pdf)
    page = src[0]
    pw, ph = page.rect.width, page.rect.height
    # pw = bw*s + 2m and ph = bh*s + 2m
    s = (ph - pw) / (bh - bw)
    m = (pw - bw * s) / 2

    def to_pdf(x, y):
        return (x - x0) * s + m, (y - y0) * s + m

    rows, langs = [r["row"] for r in data["layouts"]], [[]]
    for row in rows:
        if any(data["instances"][i]["template"] == "divider" for i in row):
            langs.append([])
            continue
        langs[-1].extend(row)

    # Check the fit on each set's last slide title: Mural draws text a few points inside its box.
    worst = 0.0
    for slides in langs:
        root = by_id[data["instances"][slides[-1]]["mural_ids"]["root"]]
        for w in widgets:
            if w["type"] == "text" and parent(w) == root["id"] and plain(w):
                ax, ay = to_pdf(root["x"] + w["x"], root["y"] + w["y"])
                hits = page.search_for(plain(w).splitlines()[0])
                if hits:
                    worst = max(worst, min(abs(h.x0 - ax) + abs(h.y0 - ay) for h in hits))
                break
    print(f"scale {s:.5f} pt per board unit, margin {m:.2f} pt, title offset {worst:.1f} pt")
    if worst > 12:
        raise SystemExit("the slides do not land where the fit puts them; the export's geometry changed")

    names = ["en", "cs"] if len(langs) == 2 else [str(i + 1) for i in range(len(langs))]
    for name, slides in zip(names, langs):
        out = pymupdf.open()
        for iid in slides:
            root = by_id[data["instances"][iid]["mural_ids"]["root"]]
            ax, ay = to_pdf(root["x"], root["y"])
            clip = pymupdf.Rect(ax, ay, ax + root["width"] * s, ay + root["height"] * s)
            out.insert_pdf(src)
            new = out[-1]
            # Take out what lies outside the slide, so a page holds only its own text and images.
            whole = new.rect
            for r in (
                pymupdf.Rect(whole.x0, whole.y0, whole.x1, clip.y0),
                pymupdf.Rect(whole.x0, clip.y1, whole.x1, whole.y1),
                pymupdf.Rect(whole.x0, clip.y0, clip.x0, clip.y1),
                pymupdf.Rect(clip.x1, clip.y0, whole.x1, clip.y1),
            ):
                new.add_redact_annot(r, fill=False)
            new.apply_redactions(
                images=pymupdf.PDF_REDACT_IMAGE_REMOVE,
                graphics=pymupdf.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED,
                text=pymupdf.PDF_REDACT_TEXT_REMOVE,
            )
            new.set_cropbox(clip)
        path = out_dir / f"{stem}.{name}.pdf"
        out.save(path, garbage=4, deflate=True)
        print(f"{path}: {len(slides)} pages, {path.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    args = sys.argv[1:]
    pdf = None
    if "--pdf" in args:
        i = args.index("--pdf")
        pdf = args[i + 1]
        del args[i : i + 2]
    main(*args, pdf=pdf)
