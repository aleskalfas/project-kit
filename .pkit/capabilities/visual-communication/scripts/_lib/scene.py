"""The scene: every element's final frame, values and source (visual-communication DEC-005
point 5), and `compute_scene`, which computes it from a piece's content and libraries.

- **A tree of groups.** Each element has a frame, `x y width height`, relative to its
  parent, in px, rounded to 1/100 px half away from zero (`formula.rounded`). A group
  says which component drew it, with its library's version and its options; a page's
  group says it is a page. Draw order is the tree's order.
- **Primitives at the leaves:** `box`, `ellipse`, `text`, `line` and `image`, their
  properties under SVG's names. Colours stay role names; a renderer takes their values
  from the document of resolved values, so one scene serves every mode of the value axes.
- **A text** holds its text, its line height, the greatest among the typography roles
  its runs take, its paragraphs of runs, its lines and its measured height. Each run
  holds its text, its typography role and font properties, its paint, the font files
  that measured it (file name and sha256), how it was measured, and the source of each.
  Each line holds its text, its width, its baseline below its top, its paragraph, and
  its spans: each the part of one run of its paragraph that lies on it, with its width
  (DEC-012 points 4 and 7).
- **An image** is drawn whole, centred, as large as its frame allows (`FIT`). One of a
  produced output holds the output, its variants by key and its exposed points, mapped into
  the image's frame. One of a picture file holds the file's bare name, `file`, and where it
  lies, `library`: `piece` for the piece's own `pictures/`, else `<library>@<version>`. Its
  name's source is the content's field that names it, or the component's default, and it
  holds no variants and no points (DEC-025 point 7). One of a picture role holds the role,
  `role`, as a paint holds its colour's, so one scene serves every value mode; its source is
  the brand's value, `role:<token path>`. A renderer is handed the file each image shows in each
  combination, whatever its source, never the scene's names.
- **A line** holds its two ends, `x1 y1 x2 y2`, and an arrowhead at either, `marker-start`
  and `marker-end`, where it draws one. A tie's connector also holds, where its route
  turns, every point of it, `points`, its ends first and last, and `attached`: for each
  end, the trace id of the element it meets with the side it meets, or the image part
  and the point it ends at (DEC-011 point 1). Its ends' sources are the end fields that
  name them. A connector whose route cannot be computed, such as one through a loop, is
  left out, its finding recorded.
- **Traces.** Each element's id is its trace: the path of instances, parts and items
  from the top, joined by `/`; an item is `<list>[<id>]`, or `<list>#<place>` (from 1)
  where it has no id. A page of a top whose layouts are its pages' forms is traced as an
  item of the field that holds the pages, `<field>[<id>]`, and lies at the top's origin,
  as large as the top. Each drawn property names its source: `content:<field path>`, a
  run of a list of runs by its place, `<field path>#<place>`, as an item with no id,
  `fact:<word>`, `option:<name>`, `size:<axis>`, a size axis a switch chose by,
  `default:<library>/<component>`, `role:<token path>` or `engine`. A value the
  component leaves to the engine, such as a text's `text-anchor` where it gives none, is
  the engine's.
- **The root** holds the piece, its lock, the language, the key over its size axes, the
  seam's version, and the trace ids of its pages in order.

Computed, never committed: `Scene.to_dict()` gives one ordered value, so under one
release the same files and facts give the same scene on every machine, and two such
scenes compare. Two scenes with one root differ only in the text of an export's facts
(DEC-016 point 5). A renderer still gets plain text, so the seam's version stands.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Any

from _lib import formula as fm
from _lib import names
from _lib.env import Env
from _lib.findings import ATTENTION, Finding
from _lib.layout import (
    ENDS,
    ENDS_OF_LINE,
    TOLERANCE,
    Context,
    Facts,
    Instance,
    Node,
    Sizes,
    TextRun,
    place_top,
    source_of_choice,
)
from _lib.text import MEASURED, Broken, paragraphs

#: Lengths are rounded to this many decimal places of a px.
PLACES = 2

#: How an image is fitted into its frame: whole, centred, as large as it allows.
FIT = "xMidYMid meet"

ENGINE = "engine"

#: A line's arrowheads, each drawn where it is not `none`.
MARKERS = ("marker-start", "marker-end")


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
    """A scene, what computing it found, and which facts of its export it shows: each fact's
    word with the trace of every element that shows it."""

    scene: Scene
    findings: list[Finding]
    facts: dict[str, list[str]]


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
    facts: Facts,
    sizes: Sizes | None = None,
) -> SceneResult:
    """The scene of a piece in one language and size combination, with what computing it
    found. `facts` fills the facts of its export, and no caller takes one by default (DEC-016
    point 5). `sizes` gives the size axes a piece can name, each at its mode at `size_key`
    (DEC-021 point 3); none where it is not given. Raises `MissingFont`, or `MissingGlyph`,
    before anything is laid out."""
    ctx = Context(env, language, facts, sizes)
    root = place_top(ctx, top, content)
    pages: list[str] = []
    children = []
    emitter = _Emitter(ctx, pages)
    if root is not None:
        for trace, node in root.texts():
            for run in node.runs:
                run.style.check(run.text, trace)
        children.append(emitter.root(root))
    scene = Scene(piece, dict(lock), language, size_key, seam_version, pages, children)
    return SceneResult(scene, list(ctx.findings), emitter.facts)


class _Emitter:
    """Turns placed instances into the scene's elements, computing each value as it goes."""

    def __init__(self, ctx: Context, pages: list[str]) -> None:
        self.ctx = ctx
        self.pages = pages
        self.facts: dict[str, list[str]] = {}

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
            drawn = self.part(instance, name, node) if node.present else None
            if drawn is not None:
                element.children.append(drawn)
        # The pages of a top whose layouts are its pages' forms, each at the top's origin.
        for page in instance.pages:
            element.children.append(
                self.group(page, (0.0, 0.0), (ENGINE, ENGINE), (ENGINE, ENGINE))
            )
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
            # A stretch its instance passes on sets the size, beside what the child asks.
            passed = self.ctx.attempt(lambda: instance.passed_on(node.part.name, key), 0.0)
            return ENGINE if passed > TOLERANCE else f"default:{node.child.component.use}"
        return ENGINE

    def _frame(self, element: Element, instance: Instance, node: Node) -> None:
        for key in ("x", "y", "width", "height"):
            value = self.ctx.attempt(lambda k=key: instance.get("part", node.part.name, k), 0.0)
            element.set(key, length(value), self._source(instance, node, key))

    def part(self, instance: Instance, name: str, node: Node) -> Element | None:
        """The element a part draws. None for a tie's connector whose route cannot be
        computed, such as one through a loop: it is left out, so no line is drawn to a
        guessed place, and its finding was recorded where its ends were computed."""
        kind = node.part.kind
        if kind == "line" and "connect" in node.part.spec:
            if not self.ctx.attempt(lambda: instance.get("route", name), []):
                return None
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
        name, spec = node.part.name, node.part.spec
        if "connect" in spec:
            self._connector(element, instance, node)
        else:
            for end in ENDS_OF_LINE:
                value = self.ctx.attempt(lambda e=end: instance.get("part", name, e), 0.0)
                element.set(
                    end, length(value), instance.source(f"parts.{name}.{end}", spec.get(end))
                )
        self._paints(element, instance, node, ("stroke",))
        self._lengths(element, instance, node, ("stroke-width",))
        for prop in MARKERS:
            if prop in node.part.props:
                where, raw = f"parts.{name}.line.{prop}", node.part.props[prop]
                word = instance.word(where, raw, "none")
                if word != "none":
                    element.set(prop, word, instance.source(where, raw))

    def _connector(self, element: Element, instance: Instance, node: Node) -> None:
        """A tie's connector (DEC-011 point 1): its ends, each from the end field that names
        it, every point of its route where it turns, and which element each end meets,
        and where (DEC-005 points 2 and 5). Its route is computed: `part` leaves out a
        connector whose route is not."""
        name = node.part.name
        route = instance.get("route", name)
        sources = {which: instance.ends[which].source for which in ENDS}
        for end, (x, y) in (("1", route[0]), ("2", route[-1])):
            which = "start" if end == "1" else "end"
            element.set(f"x{end}", length(x), sources[which])
            element.set(f"y{end}", length(y), sources[which])
        if len(route) > 2:
            element.set("points", [{"x": length(x), "y": length(y)} for x, y in route], ENGINE)
        attached = self.ctx.attempt(lambda: instance.attached(name), {})
        if attached:
            element.set("attached", attached)
            for which in attached:
                element.sources[f"attached.{which}"] = sources[which]

    def _text(self, element: Element, instance: Instance, node: Node) -> None:
        name, props = node.part.name, node.part.props
        empty = Broken((), (), False)
        broken = self.ctx.attempt(lambda: instance.get("lines", name), empty)
        where = f"parts.{name}.text"
        # Where the component gives no anchor, the engine's default, `start`, is the engine's.
        anchor_raw = props.get("text-anchor")
        _, _, chosen = instance.pick(f"{where}.text-anchor", anchor_raw)
        anchor = instance.word(f"{where}.text-anchor", anchor_raw, "start")
        given = f"default:{instance.component.use}" if anchor_raw is not None else ENGINE
        element.set("text-anchor", anchor, source_of_choice(chosen) if chosen else given)
        tallest = max(node.runs, key=lambda run: run.style.line_height).style
        element.set("line-height", length(node.line_height), f"role:{tallest.role}")
        element.set("text", node.text, instance.source_of_text(node.part))
        if "fact" in props:
            self.facts.setdefault(props["fact"], []).append(element.id)
        split = broken.paragraphs or paragraphs([run.text for run in node.runs])
        element.set(
            "paragraphs",
            [
                [self._run(instance, node, node.runs[index], text) for index, text in parts]
                for parts in split
            ],
            ENGINE,
        )
        lines = [
            {
                "text": line.text,
                "width": length(line.width),
                "baseline": length(line.baseline),
                "paragraph": line.paragraph,
                "spans": [
                    {"run": span.run, "text": span.text, "width": length(span.width)}
                    for span in line.spans
                ],
            }
            for line in broken.placed
        ]
        element.set("lines", lines, ENGINE)
        element.set("measured-height", length(len(broken.lines) * node.line_height), ENGINE)
        for run in node.runs:
            why = instance.unpainted(name, run)
            if why is not None:
                self.ctx.add(
                    Finding(
                        "concept-uncoloured",
                        ATTENTION,
                        f"{element.id}: the run {run.place} names the concept `{run.concept}`, "
                        f"which shows in no colour: {why} paints it with a role",
                        where=element.id,
                        fix="give the run a style its component paints from its colour family, "
                        "or drop the override; or ask the owner of what paints the style to "
                        "paint it from a colour family",
                        who="the piece's author",
                    )
                )
        if broken.overflow:
            element.set("overflow", True, ENGINE)
            self._overflow(element, instance, node, broken)

    def _run(self, instance: Instance, node: Node, run: TextRun, text: str) -> dict[str, Any]:
        """A run of a text as the scene holds it, within one paragraph: its part of the
        run's text, its typography role and font properties, its paint, the font files
        that measured its text, how it was measured, and the source of each (DEC-012
        points 3, 4 and 7)."""
        style, part = run.style, node.part
        _, _, chosen = instance.pick(
            f"parts.{part.name}.text.style", part.props.get("style"), run.word
        )
        if chosen and chosen in instance.component.runs:
            style_source = run.word_source
        else:
            style_source = (
                source_of_choice(chosen) if chosen else f"default:{instance.component.use}"
            )
        role = f"role:{style.role}"
        held: dict[str, Any] = {"text": text}
        sources = {"text": run.source, "style": style_source}
        fill, fill_source = self.ctx.attempt(
            lambda: instance.paint(part.name, "fill", run), (None, "")
        )
        if fill is not None:
            held["fill"], sources["fill"] = fill, fill_source
        held["style"] = style.role
        held["font-family"], sources["font-family"] = list(style.families), role
        held["font-size"], sources["font-size"] = length(style.size), role
        if style.weight is not None:
            held["font-weight"], sources["font-weight"] = style.weight, role
        faces = style.faces_used(run.text)
        held["fonts"] = [
            {"family": f.family, "file": f.path.name, "sha256": f.sha256} for f in faces
        ]
        held["measured"] = style.measured
        held["sources"] = dict(sorted(sources.items()))
        return held

    def _overflow(self, element: Element, instance: Instance, node: Node, broken: Broken) -> None:
        """A text that overflows its width: it fails where each of its runs is measured from
        a font file, and asks for attention where some run is measured from a table or by an
        estimate, which may be wider than it is drawn (DEC-005 point 14). A fact's text lies
        in no content file, so its overflow lies in the component that gives it its width,
        which it names (DEC-016 point 5)."""
        width = element.properties["width"]
        use = instance.component.use if "fact" in node.part.props else ""
        source = instance.source_of_text(node.part)
        shown = f"{source} in `{use}`" if use else source
        found = self.ctx.finding(
            "text-overflow",
            f"{element.id}: a word of {shown} is wider than the text's width {width} px: "
            f"{length(broken.natural)} px",
            where=element.id,
            use=use,
        )
        if use:
            found = replace(found, fix=f"give the text `{node.part.name}` of `{use}` more width")
        estimated = sorted({run.style.measured for run in node.runs} - {MEASURED})
        if estimated:
            found = replace(
                found,
                level=ATTENTION,
                message=f"{found.message}, measured in part {', '.join(estimated)}, "
                "not from a font file",
                who="the piece's author",
            )
        self.ctx.add(found)

    def _image(self, element: Element, instance: Instance, node: Node) -> None:
        if node.role:
            self._picture_role(element, instance, node)
            return
        if node.read is not None:
            self._picture_file(element, instance, node)
            return
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

    def _picture_file(self, element: Element, instance: Instance, node: Node) -> None:
        """An image of a picture file (DEC-025 point 7): its bare name, from the content's
        field or the component's default, and where it lies, the piece or the library
        version of the component that names it. It holds no variants and no points."""
        props = node.part.props
        if "content" in props:
            source = instance.source_of_field(props["content"])
            lies = names.PIECE
        else:
            source = f"default:{instance.component.use}"
            lies = instance.library or names.PIECE
        element.set("file", node.file, source)
        element.set("library", lies, ENGINE)
        element.set("preserveAspectRatio", FIT, ENGINE)

    def _picture_role(self, element: Element, instance: Instance, node: Node) -> None:
        """An image of a picture role (DEC-025 point 7): the role, which stays a role, as a
        paint's colour does, since its file may follow a value axis, its source the brand's
        value. It holds no file, no variants and no points: the engine hands each renderer
        the file the brand gives the role in each combination."""
        element.set("role", node.role, f"role:{node.role}")
        element.set("preserveAspectRatio", FIT, ENGINE)

    def _items(self, element: Element, instance: Instance, node: Node) -> None:
        name, part = node.part.name, node.part
        for item in node.items:
            frame = self.ctx.attempt(
                lambda i=item: instance.item_frame(name, i.position), (0.0, 0.0, 0.0, 0.0)
            )
            group = self.group(item, (frame[0], frame[1]), (ENGINE, ENGINE), (ENGINE, ENGINE))
            element.children.append(group)
        if instance.component.ties(part) is not None:
            return  # each tie lies in the part's whole frame, asking for none
        cross = "height" if part.main == "width" else "width"
        for axis, size in (("main", part.main), ("cross", cross)):
            if size in part.spec:
                gets = self.ctx.attempt(lambda s=size: instance.get("part", name, s), 0.0)
                asks = self.ctx.attempt(lambda a=axis: instance.get(a, name).asked, 0.0)
                if asks - gets > TOLERANCE:
                    self._short(element.id, size, gets, asks)
