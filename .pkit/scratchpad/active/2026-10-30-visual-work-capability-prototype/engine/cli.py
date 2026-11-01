"""The commands: render, export, mural, check."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import checks, export, render_mural
from .model import EngineError, Piece
from .render_html import index
from .render_svg import render_page
from .scene import build


def profile_for(brand, renderer: str) -> str:
    for name, profile in brand.profiles.items():
        if renderer in profile.get("renderers", []):
            return name
    raise EngineError(f"brand {brand.name} has no font profile for the {renderer} renderer")


def mode_folder(mode: str) -> str:
    return mode.replace("/", "-")


def cmd_render(piece: Piece, args) -> int:
    out = piece.path / "previews"
    out.mkdir(exist_ok=True)
    targets = piece.preview_targets()
    written, problems, page_ids = [], [], None
    for lang in piece.languages:
        for entry in dict.fromkeys(e for e, _ in targets):
            brand, _ = piece.brand(entry)
            scene = build(piece, lang, entry, profile_for(brand, "svg"), problems)
            if page_ids is None:
                page_ids = [p["id"] for p in scene["pages"]]
            for e, mode in targets:
                if e != entry:
                    continue
                tokens = brand.tokens(scene["profile"], mode)
                folder = out / brand.name / mode_folder(mode) / lang
                folder.mkdir(parents=True, exist_ok=True)
                for page in scene["pages"]:
                    name = f"{page['number']:02d}-{page['id']}.svg"
                    (folder / name).write_text(render_page(scene, page, tokens, piece.root), encoding="utf-8")
                    rel = (folder / name).relative_to(out).as_posix()
                    written.append({"lang": lang, "entry": entry, "mode": mode, "page": page["id"], "file": rel})
    (out / "index.html").write_text(index(piece.name, written, piece.languages, targets, page_ids or []), encoding="utf-8")
    print(f"render: {len(written)} SVG files and index.html in {out.relative_to(Path.cwd()) if out.is_relative_to(Path.cwd()) else out}")
    if problems:
        print(f"render: {len(problems)} problems; `check` lists them")
    return 0


def cmd_check(piece: Piece, args) -> int:
    problems = checks.run(piece)
    for kind, where, message in problems:
        print(f"{kind} {where}: {message}")
    return 1 if problems else 0


def cmd_export(piece: Piece, args) -> int:
    return export.run(piece, profile_for)


def cmd_mural(piece: Piece, args) -> int:
    return render_mural.run(piece, args.lang, Path(args.out), args.board, args.mode, profile_for)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="visual.py", description="Draw a piece of visual communication from its content.")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, about in [("render", "SVG previews of every page, language, brand and mode, and an index.html"),
                        ("export", "a numbered PDF per language in the piece's exports/"),
                        ("check", "only problems: overflow, contrast, fonts, references, fields")]:
        p = sub.add_parser(name, help=about)
        p.add_argument("piece", help="the piece's folder")
    p = sub.add_parser("mural", help="a mural-boards map file of one language")
    p.add_argument("piece")
    p.add_argument("--lang", required=True)
    p.add_argument("--out", required=True, help="the map file to write (YAML)")
    p.add_argument("--mode", help="theme/mode, by default the brand's first")
    p.add_argument("--board", default="new-board.0", help="the mural id, <workspace>.<number>; a placeholder by default")
    args = parser.parse_args(argv)
    try:
        piece = Piece(Path(args.piece))
        return {"render": cmd_render, "export": cmd_export, "check": cmd_check, "mural": cmd_mural}[args.command](piece, args)
    except EngineError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
