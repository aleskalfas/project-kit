"""The architect's pass test: is drawing `fits` and `connect` from data smaller than the Friday
talk's code for them? Compared in lines: the component files the page's scene uses plus the page's
content, against gen.py's `pyramid` and `sockets` with every gen.py function they call. Lines are
non-blank and not comments; docstrings (Python) and `about:` texts (YAML) are left out on both
sides. Constants (gen.py's sizes and colours, our brand tokens) and the board's templates (gen.py's
stage, link, notice...) and our layouts are left out too. The numbers are printed after the run.

Run alone for the table: `uv run --no-project --with pytest ... python tests/test_pass.py`.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TALK = ROOT.parent / "2026-10-29-friday-talk.gen.py"
TALK_SLIDES = ROOT.parent / "2026-10-29-friday-talk.slides.yaml"
RESULTS: list[str] = []


def python_lines(path: Path, roots: list[str]) -> tuple[int, int, list[str]]:
    """Lines of the named functions alone, and with every module function they call, transitively."""
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    lines = source.splitlines()
    funcs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}

    def count(fn):
        doc = set()
        body0 = fn.body[0] if fn.body else None
        if isinstance(body0, ast.Expr) and isinstance(getattr(body0, "value", None), ast.Constant) and isinstance(body0.value.value, str):
            doc = set(range(body0.lineno, body0.end_lineno + 1))
        return sum(1 for i in range(fn.lineno, fn.end_lineno + 1)
                   if i not in doc and lines[i - 1].strip() and not lines[i - 1].strip().startswith("#"))

    def calls(fn):
        return {n.func.id for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in funcs}

    alone = sum(count(funcs[r]) for r in roots)
    seen, todo = set(), list(roots)
    while todo:
        name = todo.pop()
        if name in seen:
            continue
        seen.add(name)
        todo.extend(calls(funcs[name]) - seen)
    return alone, sum(count(funcs[n]) for n in seen), sorted(seen - set(roots))


def yaml_lines(text: str) -> int:
    count, about_indent = 0, None
    for line in text.splitlines():
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())
        if about_indent is not None:
            if stripped and indent > about_indent:
                continue
            about_indent = None
        if not stripped or stripped.startswith("#"):
            continue
        if re.match(r"^about:", stripped):
            about_indent = indent
            continue
        count += 1
    return count


def slide_block(path: Path, slide_id: str, key: str | None = None) -> str:
    """The lines of one slide's entry in a slides list (`- id: <slide_id>` to the next entry)."""
    lines = path.read_text(encoding="utf-8").splitlines()
    start = next(i for i, l in enumerate(lines) if re.match(rf"^\s*- id: {slide_id}\s*$", l))
    indent = len(lines[start]) - len(lines[start].lstrip())
    end = next((i for i in range(start + 1, len(lines))
                if re.match(r"^\s*- id: ", lines[i]) and len(lines[i]) - len(lines[i].lstrip()) == indent), len(lines))
    block = lines[start:end]
    if key:  # only one key of the entry, e.g. the talk's `visual:`
        at = next(i for i, l in enumerate(block) if l.strip().startswith(f"{key}:"))
        k_indent = len(block[at]) - len(block[at].lstrip())
        stop = next((i for i in range(at + 1, len(block)) if block[i].strip() and len(block[i]) - len(block[i].lstrip()) <= k_indent), len(block))
        block = block[at:stop]
    return "\n".join(block)


def used_component_files(piece, slide_id: str) -> list[Path]:
    from engine.scene import build

    scene = build(piece, piece.source, piece.brand_entry, "standard")
    page = next(p for p in scene["pages"] if p["id"] == slide_id)
    refs = set()

    def visit(node):
        label = node.get("component", "")
        if label and "#" not in label:
            refs.add(label.split("@")[0])
        for child in node.get("children", []):
            visit(child)

    visit(page["root"])
    files = []
    for ref in sorted(refs):
        lib, _, name = ref.partition("/")
        if lib not in piece.libraries or piece.libraries[lib].kind != "component library":
            continue  # the brand's layouts are left out, as the board's templates are on gen.py's side
        spec = piece.libraries[lib].components().get(name)
        if spec and spec.kind != "top":
            files.append(next(p for p in piece.libraries[lib].path.rglob(f"{name}.yaml")))
    return files


def measure(piece, slide_id, roots):
    files = used_component_files(piece, slide_id)
    components = sum(yaml_lines(f.read_text(encoding="utf-8")) for f in files)
    content = yaml_lines(slide_block(piece.content_file(piece.source), slide_id))
    alone, with_helpers, helpers = python_lines(TALK, roots)
    talk_data = yaml_lines(slide_block(TALK_SLIDES, slide_id, "visual"))
    row = (f"pass test {slide_id}: data {components + content} lines (components {components} in "
           f"{', '.join(f.stem for f in files)}; content {content}) | gen.py {with_helpers} lines "
           f"({'+'.join(roots)} {alone}, helpers {with_helpers - alone}: {', '.join(helpers) or 'none'}); "
           f"the talk's own data for it {talk_data}")
    RESULTS.append(row)
    return components, content, with_helpers


def test_fits_pass_lines(friday):
    components, content, code = measure(friday, "fits", ["pyramid"])
    assert components > 0 and content > 0 and code > 0


def test_connect_pass_lines(friday):
    components, content, code = measure(friday, "connect", ["sockets"])
    assert components > 0 and content > 0 and code > 0


def test_both_pages_together(friday):
    """Components shared by both pages are counted once, as the code's shared helpers are."""
    files = sorted(set(used_component_files(friday, "fits")) | set(used_component_files(friday, "connect")))
    components = sum(yaml_lines(f.read_text(encoding="utf-8")) for f in files)
    content = sum(yaml_lines(slide_block(friday.content_file(friday.source), s)) for s in ("fits", "connect"))
    _, code, helpers = python_lines(TALK, ["pyramid", "sockets"])
    talk_data = sum(yaml_lines(slide_block(TALK_SLIDES, s, "visual")) for s in ("fits", "connect"))
    RESULTS.append(f"pass test both: data {components + content} lines (components {components} in {len(files)} files; "
                   f"content {content}) | gen.py {code} lines (pyramid+sockets with {len(helpers)} helpers); the talk's own data {talk_data}")
    assert components > 0


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(ROOT))
    from engine.model import Piece

    piece = Piece(ROOT / "pieces" / "friday-slice")
    measure(piece, "fits", ["pyramid"])
    measure(piece, "connect", ["sockets"])
    test_both_pages_together(piece)
    print("\n".join(RESULTS))
