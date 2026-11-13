"""An order's colour steps (visual-communication DEC-032 points 4 and 5): how the scene names
a step, how the engine spreads it between an order's two ends, and its value in each
combination, which comes with the scene.

- **A step's name.** A paint the scene holds names a colour role, or a step:
  `step(<first>,<last>,<share>)`, the two roles it is spread between and its place's share
  of the way from the first to the last, a fraction in lowest terms such as `1/3`, or `0` or
  `1` (DEC-005 point 5). It is the same in every mode, so one scene serves every mode. No
  token path takes its shape, so a step is never read as a role.
- **Its place.** Where a list draws n places, place k takes the share (k - 1) / (n - 1), and
  a list of one place the share 0 (`placed`). The engine spreads a step at no other share.
- **Its members.** A step paints as a colour family: its fill and its line are its colour,
  and its text is the order's text (`members`).
- **The spread** (`spread`). In Oklab, along the straight line between the ends, each
  component premultiplied by its alpha, as CSS Color 4 interpolates. A step that falls
  outside the wider of the ranges of colours its ends are given in comes back by CSS Color
  4's gamut mapping. Format 1 gives every colour in sRGB, so that range is sRGB's. The share
  0 is the first end as given, and 1 the last, so the first and last places draw the very
  colours a brand's check measured. Each step between is computed in a fixed order, and its
  components and alpha rounded to 1/10 000, half away from zero (`formula.rounded`), so the
  same ends give the same step on every machine.
- **Its value comes with the scene** (`values_at`): each step a scene paints, in one
  combination, spread from that combination's own ends, and None where one of them has no
  colour, as a role with none there. The document of a brand's resolved values holds no
  step.

Standard library and `_lib.formula` only.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from _lib import formula as fm

#: The decimal places a step's components and alpha are rounded to.
PLACES = 4

#: The members of a colour family a step paints with its own colour; its text member takes
#: the order's text (DEC-032 point 4).
COLOURED = ("fill", "line")
TEXT = "text"

#: CSS Color 4's gamut mapping: the colour difference no reader sees, in Oklab, and how close
#: the search for a chroma in range comes.
JND = 0.02
EPSILON = 0.0001

_NAME = re.compile(r"^step\(([^,()]+),([^,()]+),(0|1|[1-9][0-9]*/[1-9][0-9]*)\)$")

#: The paints of an element, and of a run of a text, that may name a step.
_PAINTS = ("fill", "stroke", "ground")


@dataclass(frozen=True)
class Step:
    """A step of an order: the roles of its first end and its last, and its place's share of
    the way from the first to the last, from 0 to 1."""

    first: str
    last: str
    share: Fraction

    @property
    def name(self) -> str:
        """The step as a scene's paint names it."""
        share = self.share
        shown = str(share.numerator) if share.denominator == 1 else f"{share}"
        return f"step({self.first},{self.last},{shown})"


def placed(first: str, last: str, place: int, count: int) -> Step:
    """The step of the place `place`, from 1, of a list that draws `count` places, spread
    evenly from the end `first` to the end `last` (DEC-032 point 4)."""
    share = Fraction(place - 1, count - 1) if count > 1 else Fraction(0)
    return Step(first, last, share)


def read(name: object) -> Step | None:
    """The step a paint names; None where it names a role, or nothing."""
    found = _NAME.match(name) if isinstance(name, str) else None
    if found is None:
        return None
    first, last, share = found.groups()
    shared = Fraction(share)
    if shared > 1 or str(shared) != share:
        return None  # a share past the last end, or not in lowest terms, names no step
    return Step(first, last, shared)


def is_step(name: object) -> bool:
    """Whether a paint names a step."""
    return read(name) is not None


def members(name: str, text: str) -> dict[str, str]:
    """The members of the step `name` as a colour family's: its fill and its line its own
    colour, and its text the order's text, the role `text`."""
    return {**dict.fromkeys(COLOURED, name), TEXT: text}


# --- what a scene paints --------------------------------------------------------------------


def painted(scene: Mapping[str, Any]) -> list[Step]:
    """Each step `scene` (`Scene.to_dict()`) paints, once, in the order first met: by an
    element's fill or stroke, or by a run's fill or ground."""
    found: dict[str, Step] = {}
    for paint in _paints(scene.get("children", [])):
        step = read(paint)
        if step is not None:
            found.setdefault(paint, step)
    return list(found.values())


def _paints(elements: Sequence[Mapping[str, Any]]) -> Iterator[Any]:
    for element in elements:
        for prop in _PAINTS:
            yield element.get(prop)
        for runs in element.get("paragraphs", []) if element.get("type") == "text" else []:
            for run in runs:
                for prop in _PAINTS:
                    yield run.get(prop)
        yield from _paints(element.get("children", []))


def values_at(scene: Mapping[str, Any], colours: Mapping[str, Any]) -> dict[str, Any]:
    """The value of each step `scene` paints, by its name, in the one combination whose
    colour roles `colours` gives, each spread from that combination's own ends. A step one
    of whose ends has no colour there has none, None, as such a role has; one whose ends
    `colours` does not hold is left out, as a role the brand lacks."""
    found: dict[str, Any] = {}
    for step in painted(scene):
        if step.first not in colours or step.last not in colours:
            continue
        first, last = colours[step.first], colours[step.last]
        unlit = first is None or last is None
        found[step.name] = None if unlit else spread(first, last, step.share)
    return found


# --- the spread -------------------------------------------------------------------------------


def spread(first: Mapping[str, Any], last: Mapping[str, Any], share: Fraction) -> dict[str, Any]:
    """The colour `share` of the way from `first` to `last`, each an sRGB colour in canonical
    form, in canonical form: in Oklab, premultiplied by alpha, mapped into sRGB's range where
    it falls outside, and rounded. The share 0 is `first` as given, and 1 `last`."""
    if share <= 0:
        return _canonical(first)
    if share >= 1:
        return _canonical(last)
    t = float(share)
    starts, ends = _oklab(first["components"]), _oklab(last["components"])
    alpha_first, alpha_last = float(first.get("alpha", 1)), float(last.get("alpha", 1))
    alpha = _between(alpha_first, alpha_last, t)
    if alpha > 0:
        lab = tuple(
            _between(start * alpha_first, end * alpha_last, t) / alpha
            for start, end in zip(starts, ends, strict=True)
        )
    else:  # nothing shows, and premultiplied components hold no hue: spread them as given
        lab = tuple(_between(start, end, t) for start, end in zip(starts, ends, strict=True))
    components = _mapped((lab[0], lab[1], lab[2]))
    return {
        "colorSpace": "srgb",
        "components": [_rounded(c) for c in components],
        "alpha": _rounded(alpha),
    }


def _canonical(colour: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "colorSpace": "srgb",
        "components": list(colour["components"]),
        "alpha": colour.get("alpha", 1),
    }


def _between(start: float, end: float, t: float) -> float:
    return start + (end - start) * t


def _rounded(value: float) -> float:
    return fm.rounded(value, PLACES) + 0.0  # no negative zero


# --- Oklab (Björn Ottosson, 2020), and CSS Color 4's gamut mapping into sRGB ------------------

Lab = tuple[float, float, float]


def _linear(c: float) -> float:
    """An sRGB component without its transfer function, its sign kept."""
    magnitude = abs(c)
    if magnitude <= 0.04045:
        return c / 12.92
    return math.copysign(((magnitude + 0.055) / 1.055) ** 2.4, c)


def _encoded(c: float) -> float:
    """A linear sRGB component with sRGB's transfer function, its sign kept."""
    magnitude = abs(c)
    if magnitude <= 0.0031308:
        return c * 12.92
    return math.copysign(1.055 * magnitude ** (1 / 2.4) - 0.055, c)


def _cube_root(x: float) -> float:
    """The real cube root of `x`, its sign kept. The scripts run on Python 3.10, which has no
    `math.cbrt`."""
    return math.copysign(abs(x) ** (1 / 3), x)


def _oklab(components: Sequence[float]) -> Lab:
    """An sRGB colour's components in Oklab."""
    r, g, b = (_linear(float(c)) for c in components)
    long = _cube_root(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b)
    medium = _cube_root(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b)
    short = _cube_root(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b)
    return (
        0.2104542553 * long + 0.7936177850 * medium - 0.0040720468 * short,
        1.9779984951 * long - 2.4285922050 * medium + 0.4505937099 * short,
        0.0259040371 * long + 0.7827717662 * medium - 0.8086757660 * short,
    )


def _srgb(lab: Lab) -> Lab:
    """A colour in Oklab as sRGB's components, unbounded."""
    lightness, a, b = lab
    long = (lightness + 0.3963377774 * a + 0.2158037573 * b) ** 3
    medium = (lightness - 0.1055613458 * a - 0.0638541728 * b) ** 3
    short = (lightness - 0.0894841775 * a - 1.2914855480 * b) ** 3
    return (
        _encoded(4.0767416621 * long - 3.3077115913 * medium + 0.2309699292 * short),
        _encoded(-1.2684380046 * long + 2.6097574011 * medium - 0.3413193965 * short),
        _encoded(-0.0041960863 * long - 0.7034186147 * medium + 1.7076147010 * short),
    )


def _inside(rgb: Lab) -> bool:
    return all(0 <= c <= 1 for c in rgb)


def _clipped(rgb: Lab) -> Lab:
    low, mid, high = (min(max(c, 0.0), 1.0) for c in rgb)
    return (low, mid, high)


def _difference(rgb: Lab, lab: Lab) -> float:
    """deltaEOK: how far the sRGB colour `rgb` lies from the colour `lab`, in Oklab."""
    other = _oklab(rgb)
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(other, lab, strict=True)))


def _mapped(lab: Lab) -> Lab:
    """The colour `lab` as sRGB's components, in sRGB's range: CSS Color 4's gamut mapping,
    which keeps its lightness and hue and lowers its chroma, by halves, until clipping it
    moves it by less than the difference no reader sees (CSS Color 4, "CSS gamut mapping to
    an RGB destination")."""
    lightness, a, b = lab
    if lightness >= 1:
        return _clipped(_srgb((1.0, 0.0, 0.0)))
    if lightness <= 0:
        return _clipped(_srgb((0.0, 0.0, 0.0)))
    rgb = _srgb(lab)
    if _inside(rgb):
        return rgb
    clipped = _clipped(rgb)
    if _difference(clipped, lab) < JND:
        return clipped
    chroma = math.sqrt(a * a + b * b)
    low, high, low_inside = 0.0, chroma, True
    while high - low > EPSILON:
        middle = (low + high) / 2
        scale = middle / chroma
        current = (lightness, a * scale, b * scale)
        rgb = _srgb(current)
        if low_inside and _inside(rgb):
            low = middle
            continue
        clipped = _clipped(rgb)
        difference = _difference(clipped, current)
        if difference < JND:
            if JND - difference < EPSILON:
                return clipped
            low_inside = False
            low = middle
        else:
            high = middle
    return clipped
