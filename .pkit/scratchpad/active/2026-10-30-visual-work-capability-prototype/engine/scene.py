"""The scene: what a piece draws, page by page, for one language, brand entry point and font profile.

Geometry depends on the font profile (fonts measure differently), never on the mode: a scene holds
colours as roles (`color.text-primary`), and a renderer resolves them in the mode it draws.
"""

from __future__ import annotations

from .layout import Instance, PageContext
from .model import EngineError, Spec


def labels_for(piece, lang):
    labels = piece.top.data.get("labels") or {}
    return {key: (per.get(lang) or per.get(piece.source) or "") for key, per in labels.items()}


def layout_spec(layouts: Spec, name: str) -> Spec | None:
    layout = (layouts.data.get("layouts") or {}).get(name)
    if layout is None:
        return None
    data = {"parts": layout.get("parts") or {}, "bounds": layout.get("bounds") or {},
            "page": layouts.data.get("page"), "define": layouts.data.get("define") or {}}
    return Spec(data, f"{layouts.ref}/{name}", layouts.library, kind="layouts")


def build(piece, lang: str, entry: str, profile: str, problems: list | None = None) -> dict:
    """One scene: every page of the piece in one language, laid out by one brand's entry point
    with one font profile's fonts."""
    problems = [] if problems is None else problems
    brand, point = piece.brand(entry)
    if piece.top.ref != brand.entry_points[point]["supplies"]:
        raise EngineError(f"brand entry {entry} supplies {brand.entry_points[point]['supplies']}, not {piece.top.ref}")
    layouts = brand.layouts(point)
    tokens = brand.tokens(profile)
    declared = piece.top.data.get("layouts") or {}
    pages_field = piece.top.data.get("pages", "self")
    pages = piece.pages(lang)
    labels = labels_for(piece, lang)
    scene = {"piece": piece.name, "lang": lang, "entry": entry, "brand": brand.name, "brand_version": brand.library.version,
             "profile": profile, "pages": [], "prose": {}}
    for number, page in enumerate(pages, start=1):
        page_id = str(page.get("id", f"page-{number}"))
        content_path = f"{pages_field}/{page_id}" if pages_field != "self" else piece.top.name
        ctx = PageContext(piece, brand, tokens, profile, lang, labels, page_id, number, len(pages), problems)
        name = page.get("layout")
        if name not in declared:
            ctx.problem("REF", content_path, f"layout {name!r} is not one of {piece.top.ref}'s layouts {sorted(declared)}")
            continue
        spec = layout_spec(layouts, name)
        if spec is None:
            ctx.problem("REF", content_path, f"brand {brand.name} supplies no layout {name!r}")
            continue
        for part, part_spec in spec.parts:
            slot = part_spec.get("slot")
            if slot and slot not in declared[name].get("slots", []):
                ctx.problem("REF", content_path, f"brand {brand.name}'s layout {name} fills slot {slot!r}, which {piece.top.ref} does not declare")
        inst = Instance(ctx, spec, page, {}, [page_id], content_path)
        width, height = inst.get("page.width"), inst.get("page.height")
        inst.give("width", width)
        inst.give("height", height)
        root = inst.emit()
        scene["prose"].update(ctx.prose)
        scene["pages"].append({"id": page_id, "number": number, "layout": name, "width": round(width, 2),
                               "height": round(height, 2), "root": root})
    return scene


def walk(node, x=0.0, y=0.0, parents=()):
    """Every primitive of a scene node with its absolute position, in painting order."""
    if node["type"] == "group":
        gx, gy = x + node["x"], y + node["y"]
        for child in node["children"]:
            yield from walk(child, gx, gy, parents + (node,))
        return
    yield node, x, y, parents


def page_ids(page) -> list[str]:
    out = []

    def visit(node):
        out.append(node["id"])
        for child in node.get("children", []):
            visit(child)

    visit(page["root"])
    return out
