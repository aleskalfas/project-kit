# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow==11.3.0"]
# ///
"""Lay out one run of the calibration (project-kit#3230): a review folder for each deck version.

Usage:

    uv run --script layout.py <ladder-judge> <ladder> <piece-dir> <intent-output> <out> <key> <run>

<ladder-judge>   the judges' folder: `blind/` and `key.json`
<ladder>         the ladder's source, for the order variant's pages alone
<piece-dir>      the scratch piece: `piece.yaml`, read for `audience`, `shown` and `explains`
<intent-output>  what the intent command printed for the scratch piece (`intent-output.txt`)
<out>            the folder the review folders go in; `<out>/run-<run>/` must not exist yet
<key>            where the run's key (code -> version) is written; it must lie outside <out>
<run>            the run's number

Each deck version gets a folder `<out>/run-<run>/<CODE>/` under a fresh neutral code: four
capital letters, drawn anew for each run, so no code repeats a judge's three-letter code or
another run's. A folder holds:

- `page-<n>.light.png` and `page-<n>.dark.png`, the 1600 x 900 copies the judges ranked
  (answer 16), byte for byte from `blind/`;
- `handed.md`, what the review is handed of the piece: its audience, where it is shown, that it
  explains, and the intent the command printed, its pages in this deck's order (answer 15).

Left out: the anchors (answer 18), the key, the rankings, the ladder's sources and any other
version. The order variant (`variants/RS-COMM-003`) has no page copies in `blind/`, since the
judges saw it as two strips. Its pages are made from its own images with the blinding tool's
resize (1600 x 900, Lanczos), and the script checks that this resize reproduces the judges' copy
of round 5's first page, which the variant shares, byte for byte or pixel for pixel.
"""

import hashlib
import json
import random
import re
import sys
from pathlib import Path

from PIL import Image, ImageChops

W, H = 1600, 900
ORDER_VARIANT = "variants/RS-COMM-003"
# The scratch piece's page ids, in round 5's order; the order variant shows round 5's pages
# 1, 4, 2, 3 (the ladder's manifest).
IDS = ["made-of", "kinds", "reaches", "read"]
VARIANT_PAGES = [1, 4, 2, 3]


def versions(key: dict) -> dict[str, dict[int, str]]:
    """Each deck version, with the blind code of each of its pages. Anchors are no version."""
    out: dict[str, dict[int, str]] = {}
    for page, codes in key["pages"].items():
        for code, sources in codes.items():
            for source in sources:
                if source.startswith("anchor"):
                    continue
                out.setdefault(source, {})[int(page)] = code
    for source, pages in out.items():
        if sorted(pages) != [1, 2, 3, 4]:
            sys.exit(f"error: {source} has pages {sorted(pages)} in the key")
    return out


def intent_of(path: Path) -> dict:
    text = path.read_text()
    return json.loads(text[text.index("{") : text.rindex("}") + 1])["intent"]


def piece_fields(path: Path) -> dict[str, str]:
    fields = {}
    for line in path.read_text().splitlines():
        m = re.match(r"^(audience|shown|explains):\s*(.*)$", line)
        if m:
            fields[m.group(1)] = m.group(2).strip().strip('"')
    return fields


def handed(fields: dict[str, str], intent: dict, ids: list[str]) -> str:
    lines = [
        "# What the review is handed",
        "",
        "## The piece",
        "",
        f"- audience: {fields['audience']}",
        f"- shown: {fields['shown']}",
        f"- explains: {fields['explains']}",
        "",
        "## The pages, in order",
        "",
    ]
    lines += [f"- page-{n}: `{pid}`" for n, pid in enumerate(ids, 1)]
    lines += ["", "## The intent, as the intent command hands it", "", "the piece:"]
    for goal in intent.get("piece", {}).get("goals", []):
        lines.append(f"  goal: {goal}")
    for rel in intent.get("piece", {}).get("relations", []):
        lines.append(f"  relation: {rel}")
    for pid in ids:
        part = intent.get("pages", {}).get(pid)
        if not part:
            continue
        lines.append(f"page {pid}:")
        for goal in part.get("goals", []):
            lines.append(f"  goal: {goal}")
        for rel in part.get("relations", []):
            lines.append(f"  relation: {rel}")
        if part.get("takeaway"):
            lines.append(f"  takeaway: {part['takeaway']}")
    return "\n".join(lines) + "\n"


def resized(src: Path) -> Image.Image:
    return Image.open(src).convert("RGB").resize((W, H), Image.LANCZOS)


def same_pixels(a: Image.Image, b: Path) -> bool:
    other = Image.open(b).convert("RGB")
    return a.size == other.size and ImageChops.difference(a, other).getbbox() is None


def main() -> None:
    if len(sys.argv) != 8:
        sys.exit(__doc__)
    judge, ladder, piece, intent_out, out, key_path, run = (
        Path(sys.argv[1]),
        Path(sys.argv[2]),
        Path(sys.argv[3]),
        Path(sys.argv[4]),
        Path(sys.argv[5]),
        Path(sys.argv[6]),
        int(sys.argv[7]),
    )
    key = json.loads((judge / "key.json").read_text())
    run_dir = out / f"run-{run}"
    if run_dir.exists():
        sys.exit(f"error: {run_dir} exists; a run's folders are laid out once")
    if key_path.resolve().is_relative_to(out.resolve()):
        sys.exit("error: the key must lie outside the review folders")
    if key_path.exists():
        sys.exit(f"error: {key_path} exists")

    decks = versions(key)
    decks[ORDER_VARIANT] = {}
    fields = piece_fields(piece / "piece.yaml")
    intent = intent_of(intent_out)

    # The order variant's resize must reproduce the judges' copy of the page it shares with round 5.
    shared = judge / "blind" / "page-1" / "light" / f"{decks['rounds/round-5'][1]}.png"
    probe = resized(ladder / ORDER_VARIANT / "page-1.light.png")
    if not same_pixels(probe, shared):
        sys.exit(
            "error: the resize does not reproduce the judges' copy; "
            "the order variant's pages would differ in scale"
        )

    rng = random.SystemRandom()
    used: set[str] = set()

    def fresh() -> str:
        while True:
            c = "".join(rng.choice("BCDFGHJKLMNPRSTVWXZ") for _ in range(4))
            if c not in used:
                used.add(c)
                return c

    sources = sorted(decks)
    rng.shuffle(sources)
    run_key: dict = {"run": run, "folders": {}}
    for source in sources:
        code = fresh()
        folder = run_dir / code
        folder.mkdir(parents=True)
        digests = {}
        for n in range(1, 5):
            for mode in ("light", "dark"):
                dst = folder / f"page-{n}.{mode}.png"
                if source == ORDER_VARIANT:
                    resized(ladder / source / f"page-{n}.{mode}.png").save(dst)
                else:
                    dst.write_bytes(
                        (
                            judge / "blind" / f"page-{n}" / mode / f"{decks[source][n]}.png"
                        ).read_bytes()
                    )
                if Image.open(dst).size != (W, H):
                    sys.exit(f"error: {dst} is not {W} x {H}")
                digests[dst.name] = hashlib.sha256(dst.read_bytes()).hexdigest()
        ids = [IDS[p - 1] for p in VARIANT_PAGES] if source == ORDER_VARIANT else IDS
        (folder / "handed.md").write_text(handed(fields, intent, ids))
        if source == ORDER_VARIANT:
            # Not the judges' image: round 5's page, with only its footer's number changed.
            r5 = decks["rounds/round-5"]
            pages = {
                str(n): {"id": ids[n - 1], "image": None, "as": r5[VARIANT_PAGES[n - 1]]}
                for n in range(1, 5)
            }
        else:
            pages = {str(n): {"id": ids[n - 1], "image": decks[source][n]} for n in range(1, 5)}
        run_key["folders"][code] = {"version": source, "pages": pages, "digests": digests}
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_text(json.dumps(run_key, indent=2) + "\n")
    print(f"run {run}: {len(sources)} review folders under {run_dir}, key at {key_path}")


if __name__ == "__main__":
    main()
