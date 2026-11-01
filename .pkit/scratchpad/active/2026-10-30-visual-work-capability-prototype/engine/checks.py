"""`check`: only problems, one per line, `KIND where: message`.

FIT       a text overflows its box, or a part reaches past the room its layout gives it
CONTRAST  a text and what lies under it reach less than 4.5 (WCAG), in some mode
FONT      a font file is missing, or a face has no glyph for a character
REF       a reference leads nowhere: an id, a concept, a layout, a slot, a role, a library
SCHEMA    a content field a component does not allow, an option word not in its list
TERM      a word the notation's glossary says is never used, in a prose field
"""

from __future__ import annotations

import jsonschema

from .model import EngineError, prose_strings, read_yaml
from .scene import build, page_ids, walk

# ---------------------------------------------------------------- contrast


def luminance(hex_colour: str) -> float:
    def channel(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast(a: str, b: str) -> float:
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def contrast_problems(scene, page, tokens, mode) -> list[tuple]:
    out = []
    painted = []  # filled shapes in painting order, absolute
    for node, x, y, parents in walk(page["root"]):
        if node["type"] in ("box", "ellipse") and node.get("fill"):
            painted.append((x + node["x"], y + node["y"], node["width"], node["height"], node["fill"]))
            continue
        if node["type"] != "text":
            continue
        where = (parents[-1].get("content") if parents else "") or ""
        part = node["id"].rsplit("/", 1)[-1]
        lh, size = node["font"]["line_height"], node["font"]["size"]
        for i, line in enumerate(node["lines"]):
            runs = line["runs"]
            for j, run in enumerate(runs):
                if run.get("decorative") or not run["text"].strip():
                    continue
                end = runs[j + 1]["x"] if j + 1 < len(runs) else line["width"]
                px = x + node["x"] + line["x"] + (run["x"] + end) / 2
                py = y + node["y"] + i * lh + lh / 2
                under = "color.background"
                for bx, by, bw, bh, fill in reversed(painted):
                    if bx <= px <= bx + bw and by <= py <= by + bh:
                        under = fill
                        break
                ratio = contrast(tokens.colour(run["fill"]), tokens.colour(under))
                if ratio < 4.5 - 1e-9:
                    out.append(("CONTRAST", f"{where}/{part}",
                                f"{run['fill'][6:]} on {under[6:]} is {ratio:.2f} in {scene['brand']} {mode} (needs 4.5; {size:.0f}px)"))
    return out


# ---------------------------------------------------------------- content


def same_structure(a, b, path="") -> list[str]:
    """Where two content trees differ in shape: keys, list lengths, ids, the words that pick a component."""
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            out.append(f"{path or '/'}: keys {sorted(set(a) ^ set(b))} are in one language only")
        for key in sorted(set(a) & set(b)):
            sub = f"{path}/{key}" if path else str(key)
            if key in ("id", "use", "concept", "state", "layout") and a[key] != b[key]:
                out.append(f"{sub}: {a[key]!r} in one language, {b[key]!r} in the other")
            else:
                out.extend(same_structure(a[key], b[key], sub))
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f"{path}: {len(a)} items in one language, {len(b)} in the other")
        for i, (x, y) in enumerate(zip(a, b)):
            key = x.get("id", i) if isinstance(x, dict) else i
            out.extend(same_structure(x, y, f"{path}/{key}"))
    elif type(a) is not type(b) and not (isinstance(a, (int, float)) and isinstance(b, (int, float))):
        out.append(f"{path}: a {type(a).__name__} in one language, a {type(b).__name__} in the other")
    return out


def content_problems(piece) -> list[tuple]:
    out = []
    source = piece.content(piece.source)
    for lang in piece.languages:
        content = piece.content(lang)
        file = f"content.{lang}.yaml"
        for err in jsonschema.Draft202012Validator(piece.top.fields).iter_errors(content):
            loc = "/".join(str(p) for p in err.path)
            out.append(("SCHEMA", f"{file} {loc}", err.message))
        if lang != piece.source:
            for diff in same_structure(source, content):
                out.append(("REF", f"{file} {diff.split(':', 1)[0]}", f"not as in content.{piece.source}.yaml:{diff.split(':', 1)[1]}"))
    return out


def glossary_problems(piece, lang, prose: dict[str, str]) -> list[tuple]:
    import re

    out = []
    for notation in piece.notations:
        for term, entry in ((notation.glossary or {}).get("terms") or {}).items():
            rule = (entry or {}).get(lang) or {}
            for word in rule.get("never") or []:
                pattern = re.compile(rf"(?<![\w-]){re.escape(word)}(?![\w-])", re.IGNORECASE)
                for path, text in sorted(prose.items()):
                    if pattern.search(text):
                        out.append(("TERM", f"content.{lang}.yaml {path}", f"{word!r}; the {notation.name} notation says {rule.get('use', term)!r}"))
    return out


# ---------------------------------------------------------------- brands


def role_paths(piece) -> list[str]:
    roles = read_yaml(piece.library("foundations").file("roles.yaml"))
    colour = roles["colour"]
    paths = [f"color.{f}.{m}" for f in colour["families"] for m in colour["members"]]
    paths += [f"color.{s}" for s in colour["singles"]] + [f"color.code.{c}" for c in colour["code"]]
    for group, names in roles["dimension"].items():
        paths += [f"{group}.{n}" for n in names]
    paths += [f"type.{n}" for n in roles["typography"]] + [f"font.{n}" for n in roles["fontFamily"]]
    return paths


def brand_problems(piece, brand, modes) -> list[tuple]:
    out = []
    paths = role_paths(piece)
    for profile in brand.profiles:
        for mode in modes:
            try:
                tokens = brand.tokens(profile, mode)
            except EngineError as e:
                out.append(("REF", f"brand {brand.name}", str(e)))
                continue
            for path in paths:
                try:
                    tokens.resolve(path)
                except Exception as e:  # a missing token or an alias leading nowhere
                    out.append(("REF", f"brand {brand.name} {profile} {mode}", f"role {path}: {e}"))
    return out


# ---------------------------------------------------------------- all


def run(piece) -> list[tuple]:
    problems: list[tuple] = []
    try:
        problems += content_problems(piece)
    except EngineError as e:
        return [("REF", piece.name, str(e))]
    targets = piece.preview_targets()
    entries = list(dict.fromkeys(e for e, _ in targets))
    for entry in entries:
        brand, _ = piece.brand(entry)
        modes = [m for e, m in targets if e == entry]
        problems += brand_problems(piece, brand, modes)
        for lang in piece.languages:
            for profile in brand.profiles:
                try:
                    scene = build(piece, lang, entry, profile, problems)
                except EngineError as e:
                    problems.append(("FONT" if "font" in str(e).lower() else "REF", f"content.{lang}.yaml", str(e)))
                    continue
                for page in scene["pages"]:
                    ids = page_ids(page)
                    for dup in sorted({i for i in ids if ids.count(i) > 1}):
                        problems.append(("REF", f"content.{lang}.yaml {page['id']}", f"the id {dup!r} is used twice on one page"))
                if "svg" not in brand.profiles[profile].get("renderers", []):
                    continue
                for mode in modes:
                    tokens = brand.tokens(profile, mode)
                    for page in scene["pages"]:
                        problems += [(k, f"content.{lang}.yaml {w}", m) for k, w, m in contrast_problems(scene, page, tokens, mode)]
                if entry == entries[0]:
                    top_prose = dict(prose_strings(piece.top.fields, piece.content(lang), ""))
                    problems += glossary_problems(piece, lang, {**top_prose, **scene["prose"]})
    seen, out = set(), []
    for p in problems:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out
