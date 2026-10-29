"""List, and with --yes delete, the board objects the map does not describe that duplicate one it does.

A stray is a duplicate when a described object has the same type, the same title, the same position
(within 1 unit) and the same parent, or a parent that is itself such a duplicate's twin. Only those are
deleted, contents before containers. Uses the mural-boards tool's own API client (its login stays its own).

Usage: uv run --no-project --with pyyaml --with jsonschema python stray_duplicates.py <tool.py> <map.yaml> [--yes]
"""

import importlib.util
import sys

import yaml


def described_ids(node, out):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "mural_id" and isinstance(v, str):
                out.add(v)
            elif k == "mural_ids" and isinstance(v, dict):
                out.update(x for x in v.values() if isinstance(x, str))
            else:
                described_ids(v, out)
    elif isinstance(node, list):
        for v in node:
            described_ids(v, out)
    return out


def main(tool_path, map_path, yes):
    spec = importlib.util.spec_from_file_location("mural_boards", tool_path)
    mb = importlib.util.module_from_spec(spec)
    sys.modules["mural_boards"] = mb
    spec.loader.exec_module(mb)
    data = yaml.safe_load(open(map_path))
    described = described_ids(data, set())
    api = mb.Mural()
    widgets = api.widgets(data["mural"])
    index = {w["id"]: w for w in widgets}

    def parent(w):
        p = w.get("parentId")
        return p.get("id") if isinstance(p, dict) else p

    def key(w):
        return (w.get("type"), (w.get("title") or "").strip(), round(w.get("x") or 0), round(w.get("y") or 0))

    by_key = {}
    for w in widgets:
        if w["id"] in described:
            by_key.setdefault(key(w), []).append(w)
    strays = [w for w in widgets if w["id"] not in described]
    twin = {}
    # Resolve parents first: a stray's parent may be a stray whose twin is described.
    pending = list(strays)
    for _ in range(6):
        left = []
        for w in pending:
            cands = by_key.get(key(w), [])
            p = parent(w)
            p_twin = twin.get(p, p)
            match = [d for d in cands if parent(d) == p_twin]
            if match:
                twin[w["id"]] = match[0]["id"]
            else:
                left.append(w)
        if len(left) == len(pending):
            break
        pending = left
    dupe_ids = {w["id"] for w in strays if w["id"] in twin}
    # Never delete a duplicate that holds anything but other duplicates.
    holds = {d: [w["id"] for w in widgets if parent(w) == d and w["id"] not in dupe_ids] for d in dupe_ids}
    for d, inside in holds.items():
        if inside:
            print(f"  hold  {d[:13]} contains {len(inside)} object(s) that are not duplicates: not deleting it")
    dupes = [w for w in strays if w["id"] in dupe_ids and not holds[w["id"]]]
    others = [w for w in strays if w["id"] not in twin]
    print(f"{len(widgets)} objects; {len(strays)} not described; {len(dupes)} duplicates of a described one; {len(others)} not")
    for w in dupes:
        pw = index.get(parent(w), {})
        print(f"  dup   {w['id'][:13]} {w.get('type'):10} '{(w.get('title') or '')[:40]}' in '{(pw.get('title') or '')[:30]}'")
    for w in others:
        pw = index.get(parent(w), {})
        print(f"  keep  {w['id'][:13]} {w.get('type'):10} '{(w.get('title') or w.get('text') or '')[:40]}' in '{(pw.get('title') or '')[:30]}'")
    if not yes:
        print("dry run: nothing deleted")
        return

    def depth(w):
        d, p = 0, parent(w)
        while p and d < 20:
            d, p = d + 1, parent(index.get(p, {}))
        return d

    order = sorted(dupes, key=lambda w: (w.get("type") == "area", -depth(w)))
    for w in order:
        api.call("DELETE", f"/murals/{data['mural']}/widgets/{w['id']}")
        print(f"  deleted {w['id'][:13]} {w.get('type')} '{(w.get('title') or '')[:40]}'")
    print(f"deleted {len(order)}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], "--yes" in sys.argv[3:])
