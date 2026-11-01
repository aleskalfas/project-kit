"""Recolour Carbon pictograms for the opening slide's rows and render them to 256 px PNGs.

Usage: python -I make_row_icons.py <svg folder> <icons folder>
"""

import subprocess
import sys
from pathlib import Path

NEUTRAL = "#525252"  # role_neutral: the problems
CODE = "#6929C4"  # role_code: pkit's answers

ICONS = {
    "conversation": ("row-chat.png", NEUTRAL),
    "pencil": ("row-write.png", CODE),
    "question": ("row-question.png", NEUTRAL),
    "documentation": ("row-conventions.png", CODE),
    "technical-document-generation": ("row-doc.png", NEUTRAL),
    "link": ("row-link.png", CODE),
    "unauthorized--user--access": ("row-unguarded.png", NEUTRAL),
    "security--shield": ("row-shield.png", CODE),
}


def main(src: Path, dst: Path) -> None:
    for name, (out, colour) in ICONS.items():
        svg = (src / f"{name}.svg").read_text(encoding="utf-8")
        svg = svg.replace("<svg ", f'<svg fill="{colour}" ', 1)
        tmp = src / f"{name}.coloured.svg"
        tmp.write_text(svg, encoding="utf-8")
        subprocess.run(["rsvg-convert", "-w", "256", "-h", "256", "-o", str(dst / out), str(tmp)], check=True)
        print(f"{name} -> {out} ({colour})")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
