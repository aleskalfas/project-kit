"""The SVG renderer: a scene drawn as SVG files, one for each page, language and
combination of modes, or, in the format `svg-modes`, one *switching file* for each page,
language and set of combinations that share one (visual-communication DEC-005 points 4, 5, 9
and 10, DEC-018 points 1 and 4).

- **What it draws** is its declaration (`svg_declaration.py`): every primitive of format
  1's scene but the path. It draws only what it declares, so the losses the capability
  reads from the declaration before it runs are the ones it makes.
- **How it draws** is the canvas's (`_lib/canvas.py`), with nothing replaced: a picture is
  embedded whole, as PNG or JPEG data, so it keeps the colour profile it carries.
- **One call for each file.** In the format `svg`, `render` is handed one key, with its
  colours and pictures. In `svg-modes`, it is handed every key the file holds with its
  combination, the first naming the file, and each key's colours and pictures (DEC-023
  point 2). The keys share the scene's size, so one scene serves them all.

**A switching file** (`Switching`) is the file of its first key, with its paints made open to
a rule, and a rule for each other key (DEC-018 point 1):

- **The plain drawing** is the first key's, attribute for attribute, so a tool that reads no
  rule draws a whole figure in that combination.
- **A paint a rule reaches.** Each element painted by a role that has a colour in some key
  carries the role as a mark, `data-fill` or `data-stroke`, beside its paint. A rule repaints
  every element of that mark: its colour and its opacity, `none` where the role has no colour
  in that key. A paint the first key leaves out is marked all the same, `fill="none"` or no
  stroke, and a stroke keeps its width, which paints nothing with no stroke.
- **An arrowhead for each paint a rule can change**: one for each end and each role a line's
  stroke takes, its triangle marked with that role as a fill, so the rule that repaints the
  role repaints it. A line whose role has no colour in the first key keeps its markers,
  which paint nothing there.
- **A picture** the keys show alike is drawn once. One that another key shows otherwise, or
  not at all, is drawn once for each picture it shows, each marked `data-shown-in` with the
  keys it shows in, and each the first key does not show hidden by `display="none"`. A rule
  hides every such picture, then shows those of its key.
- **The rules** lie in a second `<style>`, after the canvas's own. Each other key's lies under
  the reader's signals that part it from the first, as the declaration pairs them, fewer
  signals first. Every selector is one attribute's, so a later rule wins.
- **A loss in one key** names that key (DEC-005 point 9), as a role with no colour there, or
  an image with no picture there.

Output is fixed for a version: the same scene and values give the same bytes. A change that
could give another output, here or in the canvas, raises the version, and the reference
outputs pinned to it in the tests catch one made without it (DEC-005 point 9).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from _lib.canvas import ENDS, Canvas, colour_text, css_string, find, number, unshown
from _lib.plugins import seam
from _lib.plugins.css import name_of
from _lib.plugins.svg_declaration import DECLARATION

NAME: str = DECLARATION["name"]
VERSION: str = DECLARATION["version"]

#: The paints a rule of a switching file reaches, each with the attribute of its opacity.
PAINTS = {"fill": "fill-opacity", "stroke": "stroke-opacity"}

#: The mark of the paint `prop` an element takes from a role: the role's name.
MARKS = {prop: f"data-{prop}" for prop in PAINTS}

#: The mark of a picture a switching file shows in some keys alone: those keys, a space apart.
SHOWN_IN = "data-shown-in"


@dataclass(frozen=True)
class Page:
    """One page drawn: its trace id and its SVG text."""

    id: str
    svg: str


@dataclass(frozen=True)
class Drawn:
    """What one scene drawn in one combination, or in the combinations one switching file
    holds, gives: its pages, and what the renderer could not draw as given."""

    pages: list[Page]
    losses: list[seam.Loss]


def render(
    scene: Mapping[str, Any],
    *,
    key: str | None = None,
    form: str | None = None,
    keys: Mapping[str, Mapping[str, str]] | None = None,
    colours: Mapping[str, Any],
    font_file: Callable[[str], Path],
    pictures: Mapping[str, Any],
) -> Drawn:
    """`scene` (`Scene.to_dict()`) drawn in the combination `key`, or, where `form` names the
    format that holds modes, as switching files that hold each of `keys`: each key with its
    combination, every axis's mode, in key order, the first naming the file.

    For one key, `colours` gives each colour role's value there, in canonical form, and
    `pictures` the picture each image shows there, by the image's trace id (`seam.Shown`),
    whatever its source. For several, each gives that by key. `font_file` gives the
    committed file of a font family. Raises ValueError for a format the declaration does not
    name, or keys that differ in a mode it pairs with no signal."""
    if form is None:
        if key is None:
            raise ValueError("the svg renderer draws one key, or a format that holds modes")
        canvas = Canvas(DECLARATION, scene, key, colours, font_file, pictures)
    else:
        canvas = Switching(DECLARATION, scene, form, keys or {}, colours, font_file, pictures)
    pages = []
    for trace in scene.get("pages", []):
        element = find(scene.get("children", []), trace)
        if element is not None:
            pages.append(Page(trace, canvas.page(element)))
    return Drawn(pages, canvas.losses)


class Switching(Canvas):
    """The pages of one scene as switching files, each holding the combinations `keys` holds.
    The canvas draws the first key, which the plain drawing shows; what a rule reaches is
    gathered over each page, since each page is a file of its own."""

    def __init__(
        self,
        declaration: Mapping[str, Any],
        scene: Mapping[str, Any],
        form: str,
        keys: Mapping[str, Mapping[str, str]],
        colours: Mapping[str, Mapping[str, Mapping[str, Any]]],
        font_file: Callable[[str], Path],
        pictures: Mapping[str, Mapping[str, seam.Shown]],
    ) -> None:
        if form not in declaration.get("holds-modes", {}):
            raise ValueError(f"the {declaration['name']} renderer writes no format `{form}`")
        if not keys:
            raise ValueError("a switching file holds at least one key")
        first = next(iter(keys))
        super().__init__(declaration, scene, first, colours[first], font_file, pictures[first])
        self.pairs: Mapping[str, Mapping[str, Any]] = declaration["holds-modes"][form]
        self.keys = dict(keys)
        self.colours_of = colours
        self.pictures_of = pictures
        self._parted = {key: self._parting(key) for key in self.keys if key != first}
        # What the page being drawn paints by a role, as (paint, role), and each arrowhead it
        # defines, by its id, with its end and its role.
        self._painted: set[tuple[str, str]] = set()
        self._heads: dict[str, tuple[str, str]] = {}
        # Whether the page draws a picture that some key shows otherwise.
        self._apart = False

    def _parting(self, key: str) -> dict[str, str]:
        """The signals that part `key` from the first key, each with its value: one for each
        axis whose mode differs. Raises ValueError where that mode pairs with no signal."""
        first = self.keys[self.key]
        found = {}
        for axis, mode in self.keys[key].items():
            if mode == first.get(axis):
                continue
            pair = self.pairs.get(axis, {})
            if mode not in pair.get("pairs", {}):
                raise ValueError(
                    f"`{key}` and `{self.key}` differ in `{axis}`, whose mode `{mode}` pairs "
                    f"with no signal, so no file holds both"
                )
            found[pair["signal"]] = pair["pairs"][mode]
        return found

    def _lose_in(self, key: str, what: str, did: str, why: str) -> None:
        """A loss in the one combination `key`, which names it where the file holds several."""
        loss = seam.Loss(
            self.declaration["name"], what, did, why, key if len(self.keys) > 1 else None
        )
        if loss not in self.losses:
            self.losses.append(loss)

    # -- a page

    def page(self, element: Mapping[str, Any]) -> str:
        self._painted = set()
        self._heads = {}
        self._apart = False
        return super().page(element)

    # -- paint

    def _paint(self, element: Mapping[str, Any], prop: str) -> list[tuple[str, Any]]:
        """The paint `prop` of `element` as the first key paints it, with its role's mark where
        some key gives the role a colour. Each key that gives it none reports the loss."""
        role = element.get(prop)
        if role is None:
            return self._paint_attributes(prop, None)
        missing = [key for key in self.keys if self.colours_of[key].get(role) is None]
        for key in missing:
            self._lose_in(
                key,
                element["id"],
                seam.LEFT_OUT,
                f"the brand gives the role `{role}` of its {prop} no colour in `{key}`",
            )
        if len(missing) == len(self.keys):
            return self._paint_attributes(prop, None)
        self._painted.add((prop, role))
        plain = self._paint_attributes(prop, None if self.key in missing else role)
        return [*plain, (MARKS[prop], role)]

    def _markers(
        self, element: Mapping[str, Any], stroke: list[tuple[str, Any]]
    ) -> list[tuple[str, Any]]:
        """The arrowheads a line draws, each a marker the page defines once for its end and its
        stroke's role, which a rule repaints with the role. A line whose stroke no key paints
        draws none."""
        role = dict(stroke).get(MARKS["stroke"])
        if role is None:
            return []
        found = []
        for which in ENDS:
            if element.get(f"marker-{which}") == "arrow":
                marker = f"pkit-arrow-{which}{name_of(role)}"
                self._heads[marker] = (which, role)
                self._painted.add(("fill", role))
                found.append((f"marker-{which}", f"url(#{marker})"))
        return found

    def _arrow_markers(self) -> str:
        """The arrowheads the page draws, in the order of their ids, each painted as the first
        key paints its role, and marked with the role as a fill."""
        markers = []
        for marker, (which, role) in sorted(self._heads.items()):
            shown = role if self.colours.get(role) is not None else None
            plain = self._paint_attributes("fill", shown)
            markers.append(self._marker(marker, which, [*plain, (MARKS["fill"], role)]))
        return "".join(markers)

    # -- a picture

    def _image(self, element: Mapping[str, Any]) -> str:
        """An image as each key shows it. A picture every key shows alike is drawn once. Any
        other is drawn once for each picture the keys show, marked with the keys it shows in,
        and hidden where the first key does not show it. Each key that shows none reports the
        loss."""
        trace = str(element["id"])
        shown: dict[str, seam.Shown] = {}
        for key in self.keys:
            each = self.pictures_of[key].get(trace)
            if each is None or not each.file.is_file():
                self._lose_in(
                    key, trace, seam.LEFT_OUT, unshown(element, key, self.scene.get("piece"))
                )
            else:
                shown[key] = each
        held: dict[bytes, tuple[seam.Shown, list[str]]] = {}
        for key, each in shown.items():
            held.setdefault(each.file.read_bytes(), (each, []))[1].append(key)
        if len(held) == 1 and len(shown) == len(self.keys):
            return self._picture(element, shown[self.key])
        self._apart = self._apart or bool(held)
        return "".join(
            self._picture(
                element,
                each,
                (SHOWN_IN, " ".join(served)),
                ("display", None if self.key in served else "none"),
            )
            for each, served in held.values()
        )

    # -- the rules

    def _rules(self) -> str:
        """A rule for each key but the first, under the signals that part it from the first,
        fewer signals first, so the rule of a reader's own key comes after every other they
        meet. Each repaints every paint the page marks, at the key's value, and shows the
        pictures of the key. Nothing where the file holds one key, or marks nothing."""
        if not self._painted and not self._apart:
            return ""
        others = sorted(self._parted, key=lambda key: len(self._parted[key]))
        rules = []
        for key in others:
            signals = " and ".join(
                f"({signal}:{value})" for signal, value in sorted(self._parted[key].items())
            )
            rules.append(f"@media {signals}{{{self._key_rules(key)}}}")
        return f"<style>{''.join(rules)}</style>" if rules else ""

    def _key_rules(self, key: str) -> str:
        """What the rule of `key` holds: each marked paint at its value there, its colour as
        `#rrggbb` and its opacity, 1 where it is opaque, as the canvas rounds one, or `none`
        where the role has no colour there; then, where the page shows a picture apart, every
        such picture hidden and those of `key` shown."""
        colours = self.colours_of[key]
        held = []
        for prop, role in sorted(self._painted):
            colour = colours.get(role)
            if colour is None:
                paint = f"{prop}:none"
            else:
                text, alpha = colour_text(colour)
                paint = f"{prop}:{text};{PAINTS[prop]}:{number(alpha)}"
            held.append(f"[{MARKS[prop]}={css_string(role)}]{{{paint}}}")
        if self._apart:
            held.append(f"[{SHOWN_IN}]{{display:none}}")
            held.append(f"[{SHOWN_IN}~={css_string(key)}]{{display:inline}}")
        return "".join(held)
