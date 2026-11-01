"""The HTML renderer: every preview of a piece in one page, with buttons for language, brand and mode."""

from __future__ import annotations

import json
from html import escape


def index(piece_name: str, previews: list[dict], languages: list[str], targets: list[tuple[str, str]], page_ids: list[str]) -> str:
    """`previews`: one entry per SVG written, {lang, entry, mode, page, file} with the file relative to the index."""
    brands: dict[str, list[str]] = {}
    for entry, mode in targets:
        brands.setdefault(entry, []).append(mode)
    files = {f"{p['lang']}|{p['entry']}|{p['mode']}|{p['page']}": p["file"] for p in previews}
    data = json.dumps({"languages": languages, "brands": brands, "pages": page_ids, "files": files}, indent=1, sort_keys=True)
    title = escape(piece_name)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title} — previews</title>
<style>
  body {{ margin: 0; font: 15px/1.4 system-ui, sans-serif; background: #e8e8e8; color: #161616; }}
  header {{ position: sticky; top: 0; z-index: 1; display: flex; flex-wrap: wrap; gap: 18px; align-items: center;
           padding: 10px 20px; background: #fff; border-bottom: 1px solid #c6c6c6; }}
  header h1 {{ font-size: 16px; margin: 0 12px 0 0; }}
  .group {{ display: flex; gap: 4px; align-items: center; }}
  .group span {{ color: #6f6f6f; margin-right: 4px; }}
  button {{ font: inherit; padding: 4px 10px; border: 1px solid #8d8d8d; background: #fff; cursor: pointer; border-radius: 3px; }}
  button[aria-pressed="true"] {{ background: #161616; color: #fff; border-color: #161616; }}
  main {{ display: grid; gap: 24px; padding: 24px; justify-items: center; }}
  figure {{ margin: 0; }}
  figure img {{ display: block; max-width: min(1600px, 96vw); height: auto; box-shadow: 0 1px 6px rgba(0,0,0,.25); background: #fff; }}
  figcaption {{ color: #525252; font-size: 13px; margin-top: 6px; }}
</style>
</head>
<body>
<header>
  <h1>{title}</h1>
  <div class="group" id="lang"><span>Language</span></div>
  <div class="group" id="brand"><span>Brand</span></div>
  <div class="group" id="mode"><span>Mode</span></div>
</header>
<main id="pages"></main>
<script>
const DATA = {data};
const state = {{ lang: DATA.languages[0], brand: Object.keys(DATA.brands)[0], mode: null }};
state.mode = DATA.brands[state.brand][0];
function buttons(id, values, key) {{
  const box = document.getElementById(id);
  box.querySelectorAll('button').forEach(b => b.remove());
  values.forEach(v => {{
    const b = document.createElement('button');
    b.textContent = v; b.setAttribute('aria-pressed', String(state[key] === v));
    b.onclick = () => {{ state[key] = v; if (key === 'brand' && !DATA.brands[v].includes(state.mode)) {{
      const same = DATA.brands[v].find(m => m.split('/')[1] === state.mode.split('/')[1]); state.mode = same || DATA.brands[v][0]; }}
      draw(); }};
    box.appendChild(b);
  }});
}}
function draw() {{
  buttons('lang', DATA.languages, 'lang');
  buttons('brand', Object.keys(DATA.brands), 'brand');
  buttons('mode', DATA.brands[state.brand], 'mode');
  const main = document.getElementById('pages');
  main.innerHTML = '';
  DATA.pages.forEach((page, i) => {{
    const file = DATA.files[[state.lang, state.brand, state.mode, page].join('|')];
    const fig = document.createElement('figure');
    if (file) {{ const img = document.createElement('img'); img.src = file; img.alt = page; fig.appendChild(img); }}
    const cap = document.createElement('figcaption');
    cap.textContent = `${{i + 1}} · ${{page}} · ${{state.lang}} · ${{state.brand}} · ${{state.mode}}` + (file ? '' : ' (not drawn)');
    fig.appendChild(cap); main.appendChild(fig);
  }});
}}
draw();
</script>
</body>
</html>
"""
