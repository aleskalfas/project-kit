"""`export`: a PDF per language, numbered in the piece's exports/, recorded in exports/versions.yaml.

The PDF is drawn by rsvg-convert from the SVG renderer's pages, pointed at the brand's font folder
only (fontconfig with no other folder), and the fonts in the result are checked against the faces
the scene was measured with, so a silent fallback to another font fails the export. A draft's
files are added to exports/.gitignore; a delivered piece's are committed (planning note, point 13).
"""

from __future__ import annotations

import datetime as dt
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import yaml

from .model import ENGINE_VERSION, EngineError, read_yaml
from .render_svg import render_page
from .scene import build, walk

RSVG = shutil.which("rsvg-convert") or "/opt/homebrew/bin/rsvg-convert"


def font_env(font_dirs: list[Path], workdir: Path) -> dict:
    """An environment in which rsvg-convert sees the given font folders and nothing else."""
    conf = workdir / "fonts.conf"
    dirs = "".join(f"<dir>{d}</dir>" for d in sorted({str(Path(d).resolve()) for d in font_dirs}))
    conf.write_text('<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "fonts.dtd">'
                    f"<fontconfig>{dirs}<cachedir>{workdir / 'fc-cache'}</cachedir></fontconfig>\n", encoding="utf-8")
    return {**os.environ, "FONTCONFIG_FILE": str(conf), "PANGOCAIRO_BACKEND": "fc"}


def scene_faces(piece, scene) -> dict[str, Path]:
    """The font files a scene's texts were measured with, by PostScript name."""
    from fontTools.ttLib import TTFont

    faces = {}
    for page in scene["pages"]:
        for node, _, _, _ in walk(page["root"]):
            if node["type"] == "text" and node["font"]["measured"].get("by") == "file":
                path = piece.root / node["font"]["measured"]["file"]
                if path not in faces.values():
                    tt = TTFont(str(path), lazy=True)
                    faces[tt["name"].getDebugName(6)] = path
                    tt.close()
    return faces


def pdf_fonts(path: Path) -> set[str]:
    from pypdf import PdfReader

    names, seen = set(), set()

    def visit(resources):
        resources = resources.get_object() if resources is not None else {}
        for ref in (resources.get("/Font") or {}).values():
            base = str(ref.get_object().get("/BaseFont", ""))
            names.add(base.lstrip("/").split("+", 1)[-1])
        for ref in (resources.get("/XObject") or {}).values():  # forms drawn inside the page
            obj = ref.get_object()
            if id(obj) not in seen and obj.get("/Resources") is not None:
                seen.add(id(obj))
                visit(obj["/Resources"])

    for page in PdfReader(str(path)).pages:
        visit(page.get("/Resources"))
    return names


def run(piece, profile_for) -> int:
    from .checks import run as check

    problems = check(piece)
    if problems:
        print(f"export: `check` reports {len(problems)} problems; fix them first")
        return 1
    brand, _ = piece.brand()
    mode = f"{brand.default_theme}/{next(iter(brand.themes[brand.default_theme]))}"
    profile = profile_for(brand, "pdf")
    out = piece.path / "exports"
    out.mkdir(exist_ok=True)
    versions_path = out / "versions.yaml"
    versions = (read_yaml(versions_path) or {}) if versions_path.exists() else {}
    entries = versions.get("versions") or []
    number = max((v["version"] for v in entries), default=0) + 1
    files = {}
    with tempfile.TemporaryDirectory(prefix="visual-export-") as tmp:
        tmp = Path(tmp)
        for lang in piece.languages:
            scene = build(piece, lang, piece.brand_entry, profile)
            tokens = brand.tokens(profile, mode)
            faces = scene_faces(piece, scene)
            env = font_env([p.parent for p in faces.values()], tmp)
            svgs = []
            for page in scene["pages"]:
                svg = tmp / f"{lang}-{page['number']:02d}.svg"
                svg.write_text(render_page(scene, page, tokens, piece.root, embed_fonts=False), encoding="utf-8")
                svgs.append(str(svg))
            name = f"{piece.name}.v{number}.{lang}.pdf"
            target = out / name
            done = subprocess.run([RSVG, "-f", "pdf", "-o", str(target), *svgs], env=env, capture_output=True, text=True)
            if done.returncode != 0:
                raise EngineError(f"rsvg-convert failed: {done.stderr.strip()}")
            used = pdf_fonts(target)
            strangers = used - set(faces)
            if strangers:
                target.unlink()
                raise EngineError(f"{name}: drawn with fonts the scene was not measured with: {sorted(strangers)}")
            files[lang] = name
    record = {
        "version": number,
        "made": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "state": piece.meta.get("state", "draft"),
        "brand": piece.brand_entry, "mode": mode, "font_profile": profile,
        "files": files,
        "libraries": dict(piece.lock),
        "engine": ENGINE_VERSION,
        "content_sha256": piece.content_hash(),
    }
    entries.append(record)
    versions_path.write_text("# Every export of this piece, numbered (planning note, point 13). Written by `visual.py export`.\n"
                             + yaml.safe_dump({"versions": entries}, sort_keys=False, allow_unicode=True), encoding="utf-8")
    if record["state"] == "draft":
        ignore = out / ".gitignore"
        lines = ignore.read_text(encoding="utf-8").splitlines() if ignore.exists() else []
        lines += [f for f in files.values() if f not in lines]
        ignore.write_text("\n".join(lines) + "\n", encoding="utf-8")
    for lang, name in files.items():
        print(f"export: {(out / name).relative_to(Path.cwd()) if (out / name).is_relative_to(Path.cwd()) else out / name}")
    print(f"export: version {number} recorded in {versions_path.name}" + (" (a draft: its files are gitignored)" if record["state"] == "draft" else ""))
    return 0
