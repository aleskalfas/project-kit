"""The scene: every element's final frame, values and source (visual-communication DEC-005
point 5), and `compute_scene`, which computes it from a piece's content and libraries.

- **A tree of groups.** Each element has a frame, `x y width height`, relative to its
  parent, in px, rounded to 1/100 px half away from zero (`formula.rounded`). A group
  says which component drew it, with its library's version and its options; a page's
  group says it is a page. Draw order is the tree's order.
- **Primitives at the leaves:** `box`, `ellipse`, `text`, `line` and `image`, their
  properties under SVG's names. Colours stay role names; a renderer takes their values
  from the document of resolved values, so one scene serves every mode of the value axes.
- **A text** holds its text, its lines with their widths, its style role and font
  properties, its line height, the first baseline below its top, its measured height,
  the font files that measured it (file name and sha256), and how it was measured.
- **An image of a produced output** holds the output's variants by key and its exposed
  points, mapped into the image's frame.
- **Traces.** Each element's id is its trace: the path of instances, parts and items
  from the top, joined by `/`; an item is `<list>[<id>]`, or `<list>#<place>` (from 1)
  where it has no id. Each drawn property names its source: `content:<field path>`,
  `option:<name>`, `default:<library>/<component>`, `role:<token path>` or `engine`. A
  value the component leaves to the engine, such as a text's `text-anchor` where it gives
  none, is the engine's.
- **The root** holds the piece, its lock, the language, the key over its size axes, the
  seam's version, and the trace ids of its pages in order.

Computed, never committed: `Scene.to_dict()` gives one ordered value, so under one
release the same files give the same scene on every machine, and two scenes compare.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from _lib import formula as fm
from _lib.env import Env
from _lib.findings import Finding
from _lib.layout import TOLERANCE, Context, Instance, Node, place_top
from _lib.text import MEASURED, Broken

#: Lengths are rounded to this many decimal places of a px.
PLACES = 2

#: How an image is fitted into its frame: whole, centred, as large as it allows.
FIT = "xMidYMid meet"

ENGINE = "engine"


def length(value: float) -> float:
    """A length as the scene holds it."""
    return fm.rounded(value, PLACES) + 0.0  # no negative zero


@dataclass
class Element:
    """One element of the scene: a group or a primitive."""

    type: str
    id: str
    properties: dict[str, Any] = field(default_factory=dict)
    sources: dict[str, str] = field(default_factory=dict)
    children: list[Element] = field(default_factory=list)

    def set(self, name: str, value: Any, source: str = "") -> None:
        self.properties[name] = value
        if source:
            self.sources[name] = source

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"type": self.type, "id": self.id, **self.properties}
        out["sources"] = dict(sorted(self.sources.items()))
        if self.type == "group":
            out["children"] = [child.to_dict() for child in self.children]
        return out


@dataclass
class Scene:
    """One scene: one language and one combination of size-axis modes of a piece."""

    piece: str
    lock: Mapping[str, str]
    language: str
    size_key: str
    seam_version: int
    pages: list[str]
    children: list[Element]

    def to_dict(self) -> dict[str, Any]:
        return {
            "piece": self.piece,
            "lock": dict(sorted(self.lock.items())),
            "language": self.language,
            "size-key": self.size_key,
            "seam": self.seam_version,
            "pages": list(self.pages),
            "children": [child.to_dict() for child in self.children],
        }

    def find(self, trace: str) -> Element | None:
        """The element with a trace id."""
        stack = list(self.children)
        while stack:
            element = stack.pop()
            if element.id == trace:
                return element
            stack.extend(element.children)
        return None


@dataclass
class SceneResult:
    scene: Scene
    findings: list[Finding]


def compute_scene(
    *,
    piece: str,
    top: str,
    content: dict,
    language: str,
    lock: dict[str, str],
    size_key: str,
    seam_version: int,
    env: Env,
) -> SceneResult:
    """The scene of a piece in one language and size combination, with what computing it
    found. Raises `MissingFont`, or `MissingGlyph`, before anything is laid out."""
    ctx = Context(env, language)
    root = place_top(ctx, top, content)
    pages: list[str] = []
    children = []
    if root is not None:
        for trace, node in root.texts():
            if node.style is not None:
                node.style.check(node.text, trace)
        children.append(_Emitter(ctx, pages).root(root))
    scene = Scene(piece, dict(lock), language, size_key, seam_version, pages, children)
    return SceneResult(scene, list(ctx.findings))


class _Emitter:
    """Turns placed instances into the scene's elements, computing each value as it goes."""

    def __init__(self, ctx: Context, pages: list[str]) -> None:
        self.ctx = ctx
        self.pages = pages

    def root(self, top: Instance) -> Element:
        preferred = top.component.preferred
        sizes = tuple(top.source(f"preferred.{s}", preferred.get(s)) for s in ("width", "height"))
        return self.group(top, (0.0, 0.0), (ENGINE, ENGINE), sizes)

    def group(
        self,
        instance: Instance,
        place: tuple[float, float],
        place_sources: tuple[str, str],
        size_sources: tuple[str, str],
    ) -> Element:
        attempt = self.ctx.attempt
        element = Element("group", instance.trace)
        element.set("x", length(place[0]), place_sources[0])
        element.set("y", length(place[1]), place_sources[1])
        for size, source in zip(("width", "height"), size_sources, strict=True):
            element.set(size, length(attempt(lambda s=size: instance.get("size", s), 0.0)), source)
        element.set("component", instance.component.use)
        _, _, version = instance.library.partition("@")
        if version:
            element.set("version", version)
        if instance.options:
            element.set(
                "options", {name: instance.options[name] for name in sorted(instance.options)}
            )
            for name in sorted(instance.options):
                element.sources[f"options.{name}"] = instance.option_sources[name]
        if instance.is_page:
            element.set("page", True)
            self.pages.append(instance.trace)
        for name, node in instance.nodes.items():
            if node.present:
                element.children.append(self.part(instance, name, node))
        for size, gets, asks in attempt(instance.shortfalls, []):
            self._short(instance.trace, size, gets, asks)
        return element

    def _short(self, trace: str, size: str, gets: float, asks: float) -> None:
        self.ctx.report(
            "gets-less",
            f"{trace} gets {length(gets)} px of {size} and asks for {length(asks)}",
            where=trace,
        )

    def _source(self, instance: Instance, node: Node, key: str) -> str:
        spec = node.part.spec
        if key in spec and not (node.part.kind == "text" and key == "height"):
            return instance.source(f"parts.{node.part.name}.{key}", spec[key])
        if node.child is not None and key in ("width", "height"):
            return f"default:{node.child.component.use}"
        return ENGINE

    def _frame(self, element: Element, instance: Instance, node: Node) -> None:
        for key in ("x", "y", "width", "height"):
            value = self.ctx.attempt(lambda k=key: instance.get("part", node.part.name, k), 0.0)
            element.set(key, length(value), self._source(instance, node, key))

    def part(self, instance: Instance, name: str, node: Node) -> Element:
        kind = node.part.kind
        if node.child is not None:
            attempt = self.ctx.attempt
            place = tuple(
                attempt(lambda k=k: instance.get("part", name, k), 0.0) for k in ("x", "y")
            )
            places = (self._source(instance, node, "x"), self._source(instance, node, "y"))
            sizes = (self._source(instance, node, "width"), self._source(instance, node, "height"))
            return self.group(node.child, (place[0], place[1]), places, sizes)
        element = Element("group" if kind == "repeat" else kind, f"{instance.trace}/{name}")
        self._frame(element, instance, node)
        if kind == "repeat":
            self._items(element, instance, node)
        elif kind == "line":
            self._line(element, instance, node)
        elif kind == "text":
            self._text(element, instance, node)
        elif kind == "image":
            self._image(element, instance, node)
        else:
            self._shape(element, instance, node)
        return element

    def _paints(
        self, element: Element, instance: Instance, node: Node, paints: tuple[str, ...]
    ) -> None:
        for prop in paints:
            role, source = self.ctx.attempt(
                lambda p=prop: instance.paint(node.part.name, p), (None, "")
            )
            if role is not None:
                element.set(prop, role, source)

    def _lengths(
        self, element: Element, instance: Instance, node: Node, props: tuple[str, ...]
    ) -> None:
        name = node.part.name
        for prop in props:
            if prop in node.part.props:
                raw = node.part.props[prop]
                where = f"parts.{name}.{node.part.kind}.{prop}"
                value = self.ctx.attempt(lambda w=where, r=raw: instance.number(w, r), 0.0)
                element.set(prop, length(value), instance.source(where, raw))

    def _shape(self, element: Element, instance: Instance, node: Node) -> None:
        self._paints(element, instance, node, ("fill", "stroke"))
        self._lengths(element, instance, node, ("stroke-width", "rx"))

    def _line(self, element: Element, instance: Instance, node: Node) -> None:
        name = node.part.name
        for end in ("x1", "y1", "x2", "y2"):
            value = self.ctx.attempt(lambda e=end: instance.get("part", name, e), 0.0)
            element.set(
                end, length(value), instance.source(f"parts.{name}.{end}", node.part.spec.get(end))
            )
        self._paints(element, instance, node, ("stroke",))
        self._lengths(element, instance, node, ("stroke-width",))

    def _text(self, element: Element, instance: Instance, node: Node) -> None:
        name, props, style = node.part.name, node.part.props, node.style
        assert style is not None
        empty = Broken((), (), False)
        broken = self.ctx.attempt(lambda: instance.get("lines", name), empty)
        where = f"parts.{name}.text"
        default = f"default:{instance.component.use}"
        # Where the component gives no anchor, the engine's default, `start`, is the engine's.
        anchor_raw = props.get("text-anchor")
        _, _, chosen = instance.pick(f"{where}.text-anchor", anchor_raw)
        anchor = instance.word(f"{where}.text-anchor", anchor_raw, "start")
        given = default if anchor_raw is not None else ENGINE
        element.set("text-anchor", anchor, f"option:{chosen}" if chosen else given)
        self._paints(element, instance, node, ("fill",))
        _, _, chosen = instance.pick(f"{where}.style", props.get("style"))
        element.set("style", style.role, f"option:{chosen}" if chosen else default)
        role = f"role:{style.role}"
        element.set("font-family", list(style.families), role)
        element.set("font-size", length(style.size), role)
        if style.weight is not None:
            element.set("font-weight", style.weight, role)
        element.set("line-height", length(style.line_height), role)
        element.set("baseline", length(style.baseline), ENGINE)
        element.set("text", node.text, instance.source_of_field(props["content"]))
        lines = [
            {"text": text, "width": length(w)}
            for text, w in zip(broken.lines, broken.widths, strict=True)
        ]
        element.set("lines", lines, ENGINE)
        element.set("measured-height", length(len(broken.lines) * style.line_height), ENGINE)
        element.set("measured", MEASURED, ENGINE)
        faces = style.faces_used(node.text)
        fonts = [{"family": f.family, "file": f.path.name, "sha256": f.sha256} for f in faces]
        element.set("fonts", fonts, ENGINE)
        if broken.overflow:
            element.set("overflow", True, ENGINE)
            width = element.properties["width"]
            self.ctx.report(
                "text-overflow",
                f"{element.id}: a word of {instance.source_of_field(props['content'])} is wider "
                f"than the text's width {width} px: {length(broken.natural)} px",
                where=element.id,
            )

    def _image(self, element: Element, instance: Instance, node: Node) -> None:
        picture = node.picture
        assert picture is not None
        element.set("output", node.output, instance.source_of_field(node.part.props["produced"]))
        element.set("preserveAspectRatio", FIT, ENGINE)
        variants = {
            key: {
                "file": picture.variants[key]["file"],
                "pixels": {
                    "width": picture.variants[key]["pixels"]["width"],
                    "height": picture.variants[key]["pixels"]["height"],
                },
            }
            for key in sorted(picture.variants)
        }
        element.set("variants", variants, ENGINE)
        points = self.ctx.attempt(lambda: instance.get("points", node.part.name), {})
        element.set(
            "points",
            {p: {"x": length(x), "y": length(y)} for p, (x, y) in sorted(points.items())},
            ENGINE,
        )

    def _items(self, element: Element, instance: Instance, node: Node) -> None:
        name, part = node.part.name, node.part
        for item in node.items:
            frame = self.ctx.attempt(
                lambda i=item: instance.item_frame(name, i.position), (0.0, 0.0, 0.0, 0.0)
            )
            group = self.group(item, (frame[0], frame[1]), (ENGINE, ENGINE), (ENGINE, ENGINE))
            element.children.append(group)
        cross = "height" if part.main == "width" else "width"
        for axis, size in (("main", part.main), ("cross", cross)):
            if size in part.spec:
                gets = self.ctx.attempt(lambda s=size: instance.get("part", name, s), 0.0)
                asks = self.ctx.attempt(lambda a=axis: instance.get(a, name).asked, 0.0)
                if asks - gets > TOLERANCE:
                    self._short(element.id, size, gets, asks)
