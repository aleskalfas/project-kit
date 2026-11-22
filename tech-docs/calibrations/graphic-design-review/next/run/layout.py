# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow==11.3.0", "ruamel.yaml==0.19.1"]
# ///
"""Lay out the next calibration's folders (project-kit#3397): one folder for each deck version,
for every run of the review and for every outside judge, each handed the same files.

Usage, from the repository's root:

    uv run --script layout.py --reference R --judged DIR --ladder DIR --piece FILE
        --content FILE [--own-content DIR] --intent FILE --runs N --judges N --out DIR
        --keys DIR [--dry-run]

- `--reference`: what plan.md section 1 fixes, for the page ids, the orders and the piece.
- `--judged`: the judges' folder: their blind copies, `blind/page-<n>/<mode>/<CODE>.png`, and
  the blind key, `key.json`.
- `--ladder`: the ladder's source, `<version>/page-<n>.<mode>.png`, for a version the blind key
  does not place, such as an order variant.
- `--piece`: the piece's `piece.yaml`, read for `audience`, `shown` and `explains`.
- `--content`: the piece's content file, such as `content.en.yaml`.
- `--own-content`: for each version whose words differ from the piece's, its own content file,
  `<version>/<the content file's name>`.
- `--intent`: what the intent command printed for the piece.
- `--runs`, `--judges`: how many runs of the review, and how many judges.
- `--out`: where the folders go, `run-<n>/<CODE>/` and `judge-<n>/<CODE>/`; none may exist yet.
- `--keys`: where each key goes, `run-<n>.json` and `judge-<n>.json`, outside `--out`.
- `--dry-run`: lay out from a plan folder that holds uncommitted changes, and say so in each
  key. Without it, the script refuses to.

What each folder holds, the same for the review and for the judges (plan.md section 2):

- `page-<n>.light.png` and `page-<n>.dark.png`, the judges' blind copies of the version's pages,
  byte for byte. A version the blind key does not place takes its own images, resized as the
  blinding tool resized, once the script has checked that the resize reproduces a blind copy.
- `handed.md`: the piece's audience, where it is shown, that it explains, its pages in this
  deck's order and the intent the command printed.
- the content file, under the piece's content file's name: the version's own where
  `--own-content` holds one, the piece's otherwise, its slides in this deck's order, with no
  comment.

Every file is made once, for the version, and copied to each folder byte for byte. Each key
records the version of each folder, its pages' ids and images, the digest of every file the
folder holds, and the commit of the plan the folders were laid out from.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import random
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image, ImageChops
from ruamel.yaml import YAML

MODES = ("light", "dark")
LETTERS = "BCDFGHJKLMNPRSTVWXZ"
PLAN = Path(__file__).resolve().parents[1] / "plan.md"


def versions(key: dict, pages: int) -> dict[str, dict[int, str]]:
    """Each deck version the blind key places, with the blind code of each of its pages. An
    anchor is no version."""
    out: dict[str, dict[int, str]] = {}
    for page, codes in key["pages"].items():
        for code, sources in codes.items():
            for source in sources:
                if not source.startswith("anchor"):
                    out.setdefault(source, {})[int(page)] = code
    for source, placed in out.items():
        if sorted(placed) != list(range(1, pages + 1)):
            sys.exit(f"error: the blind key places {source} on pages {sorted(placed)}")
    return out


def intent_of(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    return json.loads(text[text.index("{") : text.rindex("}") + 1])["intent"]


def piece_fields(path: Path) -> dict[str, str]:
    data = YAML(typ="safe").load(path.read_text(encoding="utf-8"))
    missing = [name for name in ("audience", "shown", "explains") if name not in data]
    if missing:
        sys.exit(f"error: {path} gives no {', '.join(missing)}")
    return {
        name: str(data[name]).lower() if name == "explains" else data[name]
        for name in ("audience", "shown", "explains")
    }


def handed(fields: dict[str, str], intent: dict, ids: list[str], content: str) -> str:
    lines = [
        "# What the review is handed",
        "",
        "## The piece",
        "",
        f"- audience: {fields['audience']}",
        f"- shown: {fields['shown']}",
        f"- explains: {fields['explains']}",
        f"- its content: `{content}`, beside this file",
        "",
        "## The pages, in order",
        "",
    ]
    lines += [f"- page-{n}: `{page}`" for n, page in enumerate(ids, 1)]
    lines += ["", "## The intent, as the intent command hands it", "", "the piece:"]
    for goal in intent.get("piece", {}).get("goals", []):
        lines.append(f"  goal: {goal}")
    for relation in intent.get("piece", {}).get("relations", []):
        lines.append(f"  relation: {relation}")
    for page in ids:
        part = intent.get("pages", {}).get(page)
        if not part:
            continue
        lines.append(f"page {page}:")
        lines += [f"  goal: {goal}" for goal in part.get("goals", [])]
        lines += [f"  relation: {relation}" for relation in part.get("relations", [])]
        if part.get("takeaway"):
            lines.append(f"  takeaway: {part['takeaway']}")
    return "\n".join(lines) + "\n"


def content_for(content: Path, own: Path | None, version: str, ids: list[str]) -> bytes:
    """The version's content, its slides in the deck's order: its own file where `own` holds
    one, the piece's otherwise. Comments are dropped, since they may say how the ladder was
    made."""
    mine = own / version / content.name if own is not None else None
    path = mine if mine is not None and mine.is_file() else content
    yaml = YAML(typ="safe")
    data = yaml.load(path.read_text(encoding="utf-8"))
    by_id = {slide["id"]: slide for slide in data.get("slides", [])}
    if sorted(by_id) != sorted(ids):
        sys.exit(f"error: {path} holds slides {sorted(by_id)}, the deck {version} {sorted(ids)}")
    data["slides"] = [by_id[page] for page in ids]
    yaml.default_flow_style = False
    yaml.sort_base_mapping_type_on_output = False  # keep each slide's fields in their order
    yaml.width = 4096
    out = io.StringIO()
    yaml.dump(data, out)
    return out.getvalue().encode("utf-8")


def resized(src: Path, size: tuple[int, int]) -> bytes:
    image = Image.open(src).convert("RGB").resize(size, Image.LANCZOS)
    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def same_pixels(a: bytes, b: Path) -> bool:
    one = Image.open(io.BytesIO(a)).convert("RGB")
    other = Image.open(b).convert("RGB")
    return one.size == other.size and ImageChops.difference(one, other).getbbox() is None


def git(*args: str) -> str:
    done = subprocess.run(["git", *args], capture_output=True, text=True, cwd=PLAN.parent)
    if done.returncode:
        sys.exit(f"error: git {' '.join(args)}: {done.stderr.strip()}")
    return done.stdout.strip()


def stamp(dry_run: bool) -> dict:
    """The plan's commit, and whether its folder holds uncommitted changes."""
    root = Path(git("rev-parse", "--show-toplevel"))
    dirty = git("status", "--porcelain", "--", str(PLAN.parent))
    if dirty and not dry_run:
        sys.exit(f"error: {PLAN.parent} holds uncommitted changes; commit the plan first")
    return {
        "commit": git("rev-parse", "HEAD"),
        "at": datetime.now(UTC).isoformat(timespec="seconds"),
        "plan": PLAN.relative_to(root).as_posix(),
        "clean": not dirty,
        **({"dry-run": True} if dry_run else {}),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    for name in ("reference", "judged", "ladder", "piece", "content", "intent", "out", "keys"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--own-content", type=Path)
    parser.add_argument("--runs", type=int, required=True)
    parser.add_argument("--judges", type=int, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    ref = json.loads(args.reference.read_text())
    ids, orders = ref["page-ids"], ref.get("orders", {})
    names = [f"run-{n}" for n in range(1, args.runs + 1)]
    names += [f"judge-{n}" for n in range(1, args.judges + 1)]
    if names[args.runs :] != ref["judges"]:
        sys.exit(f"error: the reference names the judges {ref['judges']}")
    for name in names:
        if (args.out / name).exists() or (args.keys / f"{name}.json").exists():
            sys.exit(f"error: {name}'s folders or key exist; each is laid out once")
    if args.keys.resolve().is_relative_to(args.out.resolve()):
        sys.exit("error: the keys must lie outside the folders")
    laid = stamp(args.dry_run)

    key = json.loads((args.judged / "key.json").read_text())
    blind = args.judged / "blind"
    decks = versions(key, len(ids))
    first = sorted(decks)[0]
    probe_copy = blind / "page-1" / "light" / f"{decks[first][1]}.png"
    size = Image.open(probe_copy).size
    if any(version not in decks for version in orders):
        probe = resized(args.ladder / first / "page-1.light.png", size)
        if not same_pixels(probe, probe_copy):
            sys.exit("error: the resize does not reproduce the blind copy of " + first)
    fields = piece_fields(args.piece)
    intent = intent_of(args.intent)

    store: dict[str, dict] = {}
    for version in sorted({*decks, *orders}):
        order = orders.get(version, list(range(1, len(ids) + 1)))
        shown = [ids[n - 1] for n in order]
        files: dict[str, bytes] = {}
        pages = {}
        for n in range(1, len(ids) + 1):
            for mode in MODES:
                name = f"page-{n}.{mode}.png"
                if version in decks:
                    copy = blind / f"page-{n}" / mode / f"{decks[version][n]}.png"
                    files[name] = copy.read_bytes()
                else:
                    files[name] = resized(args.ladder / version / name, size)
                if Image.open(io.BytesIO(files[name])).size != size:
                    sys.exit(f"error: {version}'s {name} is not {size[0]} x {size[1]}")
            pages[str(n)] = {"id": shown[n - 1], "image": decks.get(version, {}).get(n)}
        files["handed.md"] = handed(fields, intent, shown, args.content.name).encode("utf-8")
        files[args.content.name] = content_for(args.content, args.own_content, version, shown)
        digests = {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())}
        store[version] = {"files": files, "pages": pages, "digests": digests}

    rng = random.SystemRandom()
    used: set[str] = set()
    for name in names:
        source_key: dict = {"run": name, "laid-out": laid, "folders": {}}
        order = sorted(store)
        rng.shuffle(order)
        for version in order:
            while (code := "".join(rng.choice(LETTERS) for _ in range(4))) in used:
                pass
            used.add(code)
            folder = args.out / name / code
            folder.mkdir(parents=True)
            for file_name, data in store[version]["files"].items():
                (folder / file_name).write_bytes(data)
            source_key["folders"][code] = {
                "version": version,
                "pages": store[version]["pages"],
                "digests": store[version]["digests"],
            }
        args.keys.mkdir(parents=True, exist_ok=True)
        (args.keys / f"{name}.json").write_text(json.dumps(source_key, indent=2) + "\n")
        print(f"{name}: {len(order)} folders under {args.out / name}")
    if not laid["clean"]:
        print("dry run: the plan's folder held uncommitted changes, and each key says so")


if __name__ == "__main__":
    main()
