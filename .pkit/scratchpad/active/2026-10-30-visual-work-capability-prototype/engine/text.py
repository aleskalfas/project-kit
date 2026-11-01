"""Text: fonts measured from committed files, lines broken by the engine.

A face is measured with HarfBuzz (through uharfbuzz) from a font file a library commits, never from
a font found on the machine. A profile without a file for its font measures by estimate, as the
Friday talk's generator did, and says so. Lines are broken with Unicode's rules (uniseg) plus the
language's own: in Czech a one-letter word never ends a line (as the Czech TeX tool `vlna` does).
"""

from __future__ import annotations

import hashlib
import re
from functools import lru_cache
from pathlib import Path

import uharfbuzz as hb
from fontTools.ttLib import TTFont
from uniseg.linebreak import line_break_units

NBSP = " "
BREAK_MARGIN = 12  # lines are broken against the planned width minus this, and drawn in the planned width

# Per language: a pattern whose match gets a non-breaking space after it.
LANGUAGE_RULES = {
    "cs": re.compile(r"(?<![\wÀ-ɏ])([KkSsVvZzOoUuAaIi]) "),
}


def prepare(text: str, lang: str) -> str:
    rule = LANGUAGE_RULES.get(lang)
    return rule.sub(lambda m: m.group(1) + NBSP, text) if rule else text


class Face:
    """A font file: measured exactly."""

    measure = "file"

    def __init__(self, path: Path, family: str, weight: int):
        self.path = Path(path)
        self.family, self.weight = family, weight
        data = self.path.read_bytes()
        self.sha256 = hashlib.sha256(data).hexdigest()
        tt = TTFont(str(self.path), lazy=True)
        self.cmap = set(tt.getBestCmap().keys())
        self.upem = tt["head"].unitsPerEm
        self.ascender = tt["hhea"].ascent / self.upem
        self.descender = -tt["hhea"].descent / self.upem
        self.postscript = tt["name"].getDebugName(6)
        tt.close()
        self._font = hb.Font(hb.Face(hb.Blob(data)))
        self._cache: dict[str, float] = {}

    def advance(self, text: str) -> float:
        """The width of a text in ems, shaped with kerning."""
        if text in self._cache:
            return self._cache[text]
        if not text:
            return 0.0
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self._font, buf, {"kern": True, "liga": True})
        width = sum(p.x_advance for p in buf.glyph_positions) / self.upem
        self._cache[text] = width
        return width

    def missing(self, text: str) -> set[str]:
        return {c for c in text if c not in "\n\t" and ord(c) not in self.cmap}

    def record(self, root: Path) -> dict:
        try:
            shown = self.path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            shown = self.path.as_posix()
        return {"by": "file", "file": shown, "sha256": self.sha256}


class Estimate:
    """A font nobody has as a file (Mural's proxima-nova): widths per kind of character."""

    measure = "estimate"
    ascender, descender = 0.8, 0.2
    postscript = None

    def __init__(self, family: str, weight: int = 400):
        self.family, self.weight = family, weight
        self.path = None

    @staticmethod
    @lru_cache(maxsize=None)
    def advance(text: str) -> float:
        em = 0.0
        for ch in text:
            em += 0.68 if ch.isupper() else 0.56 if ch.isdigit() else 0.3 if ch in "/.:, '-" + NBSP else 0.75 if ch == "…" else 0.52
        return em

    def missing(self, text: str) -> set[str]:
        return set()

    def record(self, root: Path) -> dict:
        return {"by": "estimate", "rule": "per kind of character: capitals 0.68, digits 0.56, narrow punctuation 0.30, others 0.52 em"}


class Style:
    """A text style resolved for one font profile: a face, a size and an explicit line height."""

    def __init__(self, name: str, face, size: float, line_height: float, weight: int, render: str = "text"):
        self.name, self.face, self.size, self.line_height, self.weight, self.render = name, face, size, line_height, weight, render

    def advance(self, text: str) -> float:
        """How far a text moves the pen, trailing spaces included."""
        return self.face.advance(text) * self.size

    def width(self, text: str) -> float:
        """How wide a text is drawn: trailing spaces do not count."""
        return self.face.advance(text.rstrip()) * self.size

    @property
    def baseline(self) -> float:
        """The first baseline below the top of a line box, with the leading split evenly."""
        content = (self.face.ascender + self.face.descender) * self.size
        return (self.line_height - content) / 2 + self.face.ascender * self.size


def break_paragraph(text: str, width: float, style: Style) -> tuple[list[str], bool]:
    """Greedy breaking at Unicode's break opportunities. Returns the lines and whether one overflows."""
    if not text:
        return [""], False
    limit = max(width - BREAK_MARGIN, 1)
    lines, current = [], ""
    for unit in line_break_units(text):
        candidate = current + unit
        if current and style.width(candidate) > limit:
            lines.append(current.rstrip(" "))
            current = unit
        else:
            current = candidate
    lines.append(current.rstrip(" "))
    return lines, any(style.width(line) > width for line in lines)


def break_text(text: str, width: float | None, style: Style, lang: str) -> tuple[list[str], bool]:
    """Every paragraph broken into lines; with no width, each paragraph is one line."""
    text = prepare(text, lang)
    lines, overflow = [], False
    for paragraph in text.split("\n"):
        if width is None:
            lines.append(paragraph)
            continue
        got, over = break_paragraph(paragraph, width, style)
        lines.extend(got)
        overflow |= over
    return lines, overflow


def shell_runs(text: str) -> list[list[list[str]]]:
    """A shell session coloured as a terminal shows it: comments, the prompt, the command, its
    arguments (continued after a backslash), and output."""
    out, continued = [], False
    for line in text.rstrip("\n").split("\n"):
        if continued:
            out.append([[line, "args"]])
        elif not line.strip():
            out.append([])
        elif line.lstrip().startswith("#"):
            out.append([[line, "comment"]])
        elif line.startswith("$ "):
            cmd, _, rest = line[2:].partition(" ")
            out.append([["$ ", "prompt"], [cmd, "command"]] + ([[" " + rest, "args"]] if rest else []))
        else:
            out.append([[line, "output"]])
        continued = line.rstrip().endswith("\\")
    return out
