"""Measure the rules of DEC-067, the check of edges that nearly line up between groups, on the
pieces of the repository the capability is authored in, and on planted cases.

It follows the record's words, not the check's code, which the work the record names writes.
It reads the pieces through the capability's own modules, and the record's figures were
measured at the commit it names. Run it from the root of that repository, where the pieces
lie, with `M` this file's path, `.pkit/capabilities/visual-communication/decisions/`
followed by `DEC-067-measure.py`:

    uv run python $M showcase sockets [-v]
    uv run python $M --planted [-v]

For each page, and in total for each piece and language, it prints what the record's rule
finds, and what each alternative the record weighs would find under the same reading:

- `sib_lines`, `sib_gaps`: the findings among siblings, of lines or insets and of spacings;
- `own`, `pairs_own`, `own_insets`: the findings of their own between groups, the pairs they
  name, and how many of them compare insets;
- `named`, `pairs_named`: the findings among siblings that name pairs of leaves of different
  groups, and those pairs;
- `lists`: the findings of two lists' spacings;
- `split`: the pairs placed in more than one finding on one axis, which the rule never does;
- `alt_*`: the findings of their own, or of the lists, under each alternative;
- `room_*`: against whole boxes, the pairs whose comparison left to right a text's room
  changes, among siblings (`sib`) and between groups (`cross`), and the gaps it takes into no
  spacing; `fill`: the texts that fill their widths; `start`, `middle`, `end`: the texts by
  where they stand their lines.

Options, which change how the record's rule reads a text or a tie:

- `--fill box`: a text is read by its whole box; `--fill widest`: a text fills its width where
  its widest line stops within a pixel short of it, or runs past it, whatever its number of
  lines; `--fill reach`: a text of one line fills its width where its line does so, whether or
  not its component gave it that width;
- `--ties`: a tie's parts are compared with the parts of other groups;
- `--texts`: each text of one line given its width, with how far short of it its line ends;
- `--ids`: full trace ids; `-v`: each finding.
"""

from __future__ import annotations

import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / ".pkit/capabilities/visual-communication/scripts"))

from _lib import boxes  # noqa: E402

ROUNDING = boxes.ROUNDING
AXES = ("across", "down")
LINE_NAMES = boxes.LINES
ANCHOR_LINE = {"start": 0, "middle": 1, "end": 2}
ROOM_SIDES = {"start": {"end"}, "middle": {"start", "end"}, "end": {"start"}}
#: An item's trace id ends so (the components page, "Trace ids").
ITEM = re.compile(r"(\[[^\]]*\]|#\d+)$")
VERBOSE = "-v" in sys.argv
FULL_IDS = "--ids" in sys.argv


def _option(name: str, default: str) -> str:
    if name in sys.argv:
        return sys.argv[sys.argv.index(name) + 1]
    return default


@dataclass(frozen=True)
class Reading:
    """How a text and a tie are read: `fill` is `record`, `box`, `widest` or `reach`."""

    fill: str = "record"
    ties: bool = False


WHOLE_BOXES = Reading(fill="box")


@dataclass(eq=False)
class Node:
    el: dict
    parent: Node | None
    x: float
    y: float
    w: float
    h: float
    order: int
    children: list[Node] = field(default_factory=list)

    @property
    def id(self) -> str:
        return str(self.el.get("id", ""))

    @property
    def short(self) -> str:
        return self.id if FULL_IDS else self.id.split("/")[-1]

    @property
    def type(self) -> str:
        return str(self.el.get("type", ""))

    def start(self, axis: str) -> float:
        return self.x if axis == "across" else self.y

    def size(self, axis: str) -> float:
        return self.w if axis == "across" else self.h

    def end(self, axis: str) -> float:
        return self.start(axis) + self.size(axis)

    def lines(self, axis: str) -> tuple[float, float, float]:
        start, size = self.start(axis), self.size(axis)
        return (start, start + size / 2, start + size)

    def chain(self) -> list[Node]:
        node, out = self, []
        while node is not None:
            out.append(node)
            node = node.parent
        return out

    def anchor(self) -> str:
        return str(self.el.get("text-anchor", "start"))

    def text_lines(self) -> list[dict]:
        return self.el.get("lines") or []

    def widest(self) -> float:
        return max((float(line.get("width", 0)) for line in self.text_lines()), default=0.0)

    def given_no_width(self) -> bool:
        return (self.el.get("sources") or {}).get("width") == "engine"

    def fills(self, reading: Reading) -> bool:
        one_line = len(self.text_lines()) == 1
        if reading.fill == "box":
            return True
        if reading.fill == "widest":
            return self.widest() >= self.w - ROUNDING
        if reading.fill == "reach":
            return one_line and self.widest() >= self.w - ROUNDING
        return one_line and self.given_no_width()

    def has_room(self, axis: str, reading: Reading) -> bool:
        return axis == "across" and self.type == "text" and not self.fills(reading)

    def kept(self, axis: str, reading: Reading) -> set[int]:
        """The lines of `axis` this part is compared on (DEC-067 point 3)."""
        if self.has_room(axis, reading):
            return {ANCHOR_LINE.get(self.anchor(), 0)}
        return {0, 1, 2}

    def room_at(self, axis: str, reading: Reading) -> set[str]:
        if not self.has_room(axis, reading):
            return set()
        return ROOM_SIDES.get(self.anchor(), {"end"})


def build(el: dict, parent: Node | None, ox: float, oy: float, out: list[Node], order=0) -> Node:
    x, y = ox + float(el.get("x", 0)), oy + float(el.get("y", 0))
    node = Node(el, parent, x, y, float(el.get("width", 0)), float(el.get("height", 0)), order)
    out.append(node)
    for index, child in enumerate(el.get("children") or []):
        node.children.append(build(child, node, x, y, out, index))
    return node


def pages_of(scene: dict) -> list[tuple[dict, float, float]]:
    ids = set(map(str, scene.get("pages", [])))
    found = []

    def walk(el: dict, ox: float, oy: float) -> None:
        if str(el.get("id", "")) in ids:
            found.append((el, ox, oy))
            return
        x, y = ox + float(el.get("x", 0)), oy + float(el.get("y", 0))
        for child in el.get("children") or []:
            walk(child, x, y)

    for child in scene.get("children") or []:
        walk(child, 0, 0)
    return found


def compared(node: Node) -> bool:
    return boxes._compared(node.el)


def is_leaf(node: Node) -> bool:
    return compared(node) and node.type != "group"


def tie_groups(nodes: list[Node]) -> set[int]:
    """The groups a tie's component draws: the nearest item above each connector (point 1)."""
    found = set()
    for node in nodes:
        if node.type == "line" and node.el.get("attached"):
            for group in node.chain()[1:]:
                if ITEM.search(group.id):
                    found.add(id(group))
                    if group is not node.parent:
                        print(f"    a connector lies deeper than its item: {node.id}")
                    break
    return found


def holds_box(a: Node, b: Node) -> bool:
    return all(
        a.start(axis) - ROUNDING <= b.start(axis) and b.end(axis) <= a.end(axis) + ROUNDING
        for axis in AXES
    )


def near(difference: float, step: float) -> bool:
    return ROUNDING < abs(difference) < step


def below(a: Node, b: Node) -> bool:
    return any(node is b for node in a.chain()[1:])


@dataclass
class Miss:
    """A near miss of two parts on one axis: by lines or by insets, with each near line."""

    first: Node
    second: Node
    axis: str
    kind: str
    near: list[tuple[str, float]]


def pair_misses(a: Node, b: Node, step: float, reading: Reading) -> list[Miss]:
    """The near misses of `a` and `b` on each axis, as DEC-046 point 3 and DEC-067 point 3
    compare them: the offset on a line is `b`'s value less `a`'s."""
    out = []
    if holds_box(a, b) or holds_box(b, a):
        outer, inner = (a, b) if holds_box(a, b) else (b, a)
        for axis in AXES:
            if axis == "across" and any(
                part.has_room(axis, reading) and part.anchor() != "middle"
                for part in (inner, outer)
            ):
                continue
            insets = (inner.start(axis) - outer.start(axis), outer.end(axis) - inner.end(axis))
            if min(insets) <= ROUNDING:
                continue
            offset = insets[0] - insets[1]
            if near(offset, step):
                out.append(Miss(a, b, axis, "insets", [("insets", offset)]))
        return out
    for axis in AXES:
        kept = sorted(a.kept(axis, reading) & b.kept(axis, reading))
        if not kept:
            continue
        la, lb = a.lines(axis), b.lines(axis)
        apart = {i: lb[i] - la[i] for i in kept}
        if any(abs(d) <= ROUNDING for d in apart.values()):
            continue
        found = [(LINE_NAMES[axis][i], d) for i, d in apart.items() if near(d, step)]
        if found:
            out.append(Miss(a, b, axis, "lines", found))
    return out


def sibling_misses(nodes: list[Node], step: float, reading: Reading) -> list[Miss]:
    found = []
    for node in nodes:
        kids = [k for k in node.children if compared(k)]
        for i, a in enumerate(kids):
            for b in kids[i + 1 :]:
                found.extend(pair_misses(a, b, step, reading))
    return found


# --- spacings -------------------------------------------------------------------------------


def gaps(group: Node, axis: str, reading: Reading) -> list[float]:
    """Each gap on `axis` from a part `group` holds to the nearest one after it that stands
    beside it, less a gap that starts or ends at a text's room (point 3)."""
    kids = [k for k in group.children if compared(k)]
    other = "down" if axis == "across" else "across"
    out = []
    for k in kids:
        after = [
            e
            for e in kids
            if e is not k
            and e.start(axis) >= k.end(axis) - ROUNDING
            and min(k.end(other), e.end(other)) - max(k.start(other), e.start(other)) > ROUNDING
        ]
        if after:
            n = min(after, key=lambda e: e.start(axis))
            if "end" in k.room_at(axis, reading) or "start" in n.room_at(axis, reading):
                continue
            out.append(n.start(axis) - k.end(axis))
    return out


def clusters(values: list[float]) -> list[list[float]]:
    out: list[list[float]] = []
    for value in sorted(values):
        if out and value - out[-1][0] <= ROUNDING:
            out[-1].append(value)
        else:
            out.append([value])
    return out


def spacings(group: Node, axis: str, reading: Reading) -> list[float]:
    return [c[0] for c in clusters(gaps(group, axis, reading))]


def sibling_spacing_findings(nodes: list[Node], step: float, reading: Reading) -> list[tuple]:
    found = []
    for node in nodes:
        if node.type != "group":
            continue
        for axis in AXES:
            own = spacings(node, axis, reading)
            for i, s1 in enumerate(own):
                for s2 in own[i + 1 :]:
                    if near(s2 - s1, step):
                        found.append((node.id, axis, s1, s2))
    return found


def items_component(group: Node) -> str | None:
    """The component that draws each of a list's items, or None where `group` is no list."""
    kids = [k for k in group.children if compared(k)]
    if len(kids) < 2 or any(k.type != "group" for k in kids):
        return None
    drawn_by = {k.el.get("component") for k in kids}
    if len(drawn_by) != 1 or None in drawn_by:
        return None
    return drawn_by.pop()


def list_findings(groups: list[Node], step: float, reading: Reading, mode: str) -> list[tuple]:
    """Two groups' spacings that nearly agree (point 5). `record`: two lists whose items one
    component draws, neither below the other; `nested`: such lists, one below the other too;
    `every`: every two groups neither below the other; `every-nested`: every two groups."""
    found = []
    for i, g1 in enumerate(groups):
        for g2 in groups[i + 1 :]:
            nested = below(g1, g2) or below(g2, g1)
            if nested and mode in ("record", "every"):
                continue
            if mode in ("record", "nested"):
                drawn_by = items_component(g1)
                if drawn_by is None or drawn_by != items_component(g2):
                    continue
            for axis in AXES:
                own1, own2 = spacings(g1, axis, reading), spacings(g2, axis, reading)
                for s1 in own1:
                    for s2 in own2:
                        if not near(s2 - s1, step):
                            continue
                        if any(abs(x - s2) <= ROUNDING for x in own1) or any(
                            abs(x - s1) <= ROUNDING for x in own2
                        ):
                            continue
                        found.append((g1.id, g2.id, axis, s1, s2))
    return found


def nested_lists(groups: list[Node]) -> int:
    """How many two lists whose items one component draws lie one below the other."""
    count = 0
    for i, g1 in enumerate(groups):
        for g2 in groups[i + 1 :]:
            drawn_by = items_component(g1)
            if drawn_by and drawn_by == items_component(g2) and (below(g1, g2) or below(g2, g1)):
                count += 1
    return count


# --- between groups ---------------------------------------------------------------------------


def sides_of(a: Node, b: Node) -> tuple[Node, Node, bool]:
    """The two sides of `a` and `b`, the first drawn first, and whether `b` lies at it."""
    chain_a = a.chain()
    in_a = {id(n): i for i, n in enumerate(chain_a)}
    previous = b
    for node in b.chain()[1:]:
        if id(node) in in_a:
            side_a, side_b = chain_a[in_a[id(node)] - 1], previous
            if side_a.order <= side_b.order:
                return side_a, side_b, False
            return side_b, side_a, True
        previous = node
    raise AssertionError("no common group")


@dataclass(eq=False)
class Pair:
    """A near miss of two leaves of different groups on one axis, the first at the first side."""

    first_side: Node
    second_side: Node
    axis: str
    kind: str
    first: Node
    second: Node
    near: list[tuple[str, float]]

    @property
    def key(self) -> tuple:
        return (id(self.first_side), id(self.second_side), self.axis, self.kind)

    @property
    def offset(self) -> float:
        """Its offset on the axis: the least in size of its near lines' offsets, the first in
        line order where two are as small to a hundredth of a pixel."""
        return min((o for _, o in self.near), key=lambda o: round(abs(o), 2))


def cross_pairs(parts: list[Node], ties: set[int], step: float, reading: Reading) -> list[Pair]:
    def tie_part(node: Node) -> bool:
        return not reading.ties and any(id(g) in ties for g in node.chain()[1:])

    out = []
    for i, a in enumerate(parts):
        for b in parts[i + 1 :]:
            if a.parent is b.parent or tie_part(a) or tie_part(b):
                continue
            s1, s2, swapped = sides_of(a, b)
            first, second = (b, a) if swapped else (a, b)
            for miss in pair_misses(first, second, step, reading):
                out.append(Pair(s1, s2, miss.axis, miss.kind, first, second, miss.near))
    return out


@dataclass(frozen=True)
class Grouping:
    """How pairs are placed in findings.

    - `start`: `lines`, a finding a pair starts takes its offsets on each near line; `axis`,
      its offset on the axis alone; `clusters`, pairs gathered by their offsets on the axis,
      within a pixel of the least of them.
    - `order`: by the size of each pair's offset on the axis, or by its sign, after the pairs
      of fewest near lines; pairs as small stay in drawing order.
    - `join`: a later pair joins a finding on `any` of its near lines, or on the `same` line.
    - `siblings`: a pair is named in the siblings' finding by the `same` line, by `any` line
      with any of that finding's, or with its offset on the `axis` alone.
    """

    start: str = "lines"
    order: str = "size"
    join: str = "any"
    siblings: str = "same"


RECORD = Grouping()
ALTERNATIVES = {
    "by_sign": Grouping(order="sign"),
    "join_same_line": Grouping(join="same"),
    "start_axis": Grouping(start="axis", order="sign"),
    "by_axis_offset": Grouping(start="clusters"),
    "siblings_any": Grouping(siblings="any"),
    "siblings_axis": Grouping(siblings="axis"),
}


def _matches(
    near_lines: list[tuple[str, float]], offsets: list[tuple[str, float]], same: bool
) -> bool:
    return any(
        (not same or name == other) and abs(value - offset) <= ROUNDING
        for name, value in near_lines
        for other, offset in offsets
    )


def shows_siblings(pair: Pair, offsets: list[tuple[str, float]], how: str) -> bool:
    if not offsets:
        return False
    if how == "axis":
        least = min((o for _, o in offsets), key=lambda o: round(abs(o), 2))
        return _matches(pair.near, [("axis", least)], same=False)
    return _matches(pair.near, offsets, same=how == "same")


def grouped(
    pairs: list[Pair], sibling_lines: dict[tuple, list[tuple[str, float]]], how: Grouping
) -> tuple[list[list[Pair]], list[list[Pair]]]:
    """The findings of their own, and the pairs each finding among siblings names (point 4)."""
    by_key: dict[tuple, list[Pair]] = defaultdict(list)
    for pair in pairs:
        by_key[pair.key].append(pair)
    own: list[list[Pair]] = []
    named: list[list[Pair]] = []
    for key, members in by_key.items():
        offsets = sibling_lines.get(key, [])
        shown = [p for p in members if shows_siblings(p, offsets, how.siblings)]
        if shown:
            named.append(shown)
        rest = [p for p in members if all(p is not s for s in shown)]
        if how.start == "clusters":
            for group in clusters([p.offset for p in rest]):
                least = group[0]
                own.append([p for p in rest if least <= p.offset <= least + ROUNDING])
            continue
        if how.order == "size":
            rest.sort(key=lambda p: (len(p.near), round(abs(p.offset), 2)))
        else:
            rest.sort(key=lambda p: (len(p.near), p.offset))
        findings: list[tuple[list[tuple[str, float]], list[Pair]]] = []
        for pair in rest:
            for starting, found in findings:
                if _matches(pair.near, starting, same=how.join == "same"):
                    found.append(pair)
                    break
            else:
                starting = pair.near if how.start == "lines" else [("axis", pair.offset)]
                findings.append((starting, [pair]))
        own.extend(found for _, found in findings)
    return own, named


def split_pairs(own: list[list[Pair]]) -> int:
    seen: Counter = Counter()
    for finding in own:
        for key in {(id(p.first), id(p.second), p.axis) for p in finding}:
            seen[key] += 1
    return sum(1 for count in seen.values() if count > 1)


def line_clusters(parts: list[Node]) -> dict[tuple, int]:
    out = {}
    for axis in AXES:
        for index, name in enumerate(LINE_NAMES[axis]):
            values = sorted((p.lines(axis)[index], id(p)) for p in parts)
            label, least = -1, None
            for value, ident in values:
                if least is None or value - least > ROUNDING:
                    label, least = label + 1, value
                out[(axis, name, ident)] = label
    return out


def lines_of_the_page(parts: list[Node], own: list[list[Pair]]) -> tuple[int, int, int]:
    """(lines) one finding for each two lines of the page that nearly agree, insets by two
    sides and offset; (joined) the record's findings joined where they share two lines of the
    page; (ungrouped) every pair and axis."""
    lines = line_clusters(parts)
    pairs = [p for finding in own for p in finding]
    by_lines = set()
    for p in pairs:
        if p.kind == "lines":
            for name, _ in p.near:
                la, lb = lines[(p.axis, name, id(p.first))], lines[(p.axis, name, id(p.second))]
                by_lines.add((p.axis, name, min(la, lb), max(la, lb)))
        else:
            by_lines.add((*p.key, round(p.offset)))
    parent = list(range(len(own)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    seen: dict[tuple, int] = {}
    for index, finding in enumerate(own):
        for p in finding:
            if p.kind != "lines":
                continue
            for name, _ in p.near:
                la, lb = lines[(p.axis, name, id(p.first))], lines[(p.axis, name, id(p.second))]
                key = (p.axis, name, min(la, lb), max(la, lb))
                if key in seen:
                    parent[find(index)] = find(seen[key])
                else:
                    seen[key] = index
    joined = {find(i) for i in range(len(own))}
    return len(by_lines), len(joined), len(pairs)


def say(finding: list[Pair]) -> str:
    return ", ".join(
        f"{p.first.short}~{p.second.short} " + "/".join(f"{n} {o:+.2f}" for n, o in p.near)
        for p in finding
    )


# --- a text's room ----------------------------------------------------------------------------


def room_changes(
    nodes: list[Node], parts: list[Node], ties: set[int], step: float, reading: Reading
) -> dict[str, int]:
    """Against whole boxes, the pairs whose comparison left to right `reading`'s room changes:
    `unmasked`, whole boxes line up on a line `reading` does not compare, and `reported`, of
    those, the pairs `reading` then reports; `dropped`, whole boxes name a near miss and
    `reading` names none. Then the gaps left to right it takes into no spacing."""
    out = dict.fromkeys(
        (f"{where}_{what}" for where in ("sib", "cross") for what in ("unmasked", "reported")),
        0,
    )
    out.update(sib_dropped=0, cross_dropped=0)

    def judge(a: Node, b: Node, where: str) -> None:
        by_box = [m for m in pair_misses(a, b, step, WHOLE_BOXES) if m.axis == "across"]
        by_reading = [m for m in pair_misses(a, b, step, reading) if m.axis == "across"]
        if not (holds_box(a, b) or holds_box(b, a)):
            la, lb = a.lines("across"), b.lines("across")
            kept = a.kept("across", reading) & b.kept("across", reading)
            lined = [i for i in range(3) if abs(lb[i] - la[i]) <= ROUNDING]
            if lined and not any(i in kept for i in lined):
                out[f"{where}_unmasked"] += 1
                if by_reading:
                    out[f"{where}_reported"] += 1
        if by_box and not by_reading:
            out[f"{where}_dropped"] += 1

    for node in nodes:
        kids = [k for k in node.children if compared(k)]
        for i, a in enumerate(kids):
            for b in kids[i + 1 :]:
                judge(a, b, "sib")
    for i, a in enumerate(parts):
        for b in parts[i + 1 :]:
            if a.parent is b.parent:
                continue
            if any(id(g) in ties for n in (a, b) for g in n.chain()[1:]):
                continue
            judge(a, b, "cross")
    dropped, groups = 0, 0
    for node in nodes:
        if node.type == "group":
            lost = len(gaps(node, "across", WHOLE_BOXES)) - len(gaps(node, "across", reading))
            dropped += lost
            groups += 1 if lost else 0
    out.update(gaps_dropped=dropped, groups_with_gaps_dropped=groups)
    return out


# --- a page -----------------------------------------------------------------------------------


def study(page_el: dict, ox: float, oy: float, step: float, reading: Reading, label: str) -> dict:
    nodes: list[Node] = []
    root = build(page_el, None, ox, oy, nodes)
    ties = tie_groups(nodes)
    parts = [n for n in nodes if n is not root and is_leaf(n)]
    groups = [n for n in nodes if n.type == "group" and n is not root]
    texts = [n for n in nodes if n.type == "text" and compared(n)]
    if "--texts" in sys.argv:
        for t in texts:
            if len(t.text_lines()) == 1 and not t.given_no_width():
                short = t.w - t.widest()
                print(f"    text {t.id}: given {t.w:.2f}, its one line {short:.2f} short of it")
    sib = sibling_misses(nodes, step, reading)
    sibling_lines: dict[tuple, list[tuple[str, float]]] = defaultdict(list)
    for miss in sib:
        key = (id(miss.first), id(miss.second), miss.axis, miss.kind)
        sibling_lines[key].extend(miss.near)
    pairs = cross_pairs(parts, ties, step, reading)
    own, named = grouped(pairs, sibling_lines, RECORD)
    sib_gaps = sibling_spacing_findings(nodes, step, reading)
    lists = list_findings(groups, step, reading, "record")
    by_lines, joined, ungrouped = lines_of_the_page(parts, own)
    row = {
        "sib_lines": len(sib),
        "sib_gaps": len(sib_gaps),
        "own": len(own),
        "pairs_own": sum(len(f) for f in own),
        "own_insets": sum(1 for f in own if f[0].kind == "insets"),
        "named": len(named),
        "pairs_named": sum(len(f) for f in named),
        "lists": len(lists),
        "split": split_pairs(own),
    }
    for name, how in ALTERNATIVES.items():
        alt_own, alt_named = grouped(pairs, sibling_lines, how)
        row[f"alt_{name}"] = len(alt_own)
        row[f"alt_{name}_named"] = len(alt_named)
    row.update(
        alt_lines_of_page=by_lines,
        alt_joined=joined,
        alt_ungrouped=ungrouped,
        alt_lists_nested=len(list_findings(groups, step, reading, "nested")),
        alt_lists_every=len(list_findings(groups, step, reading, "every")),
        alt_lists_every_nested=len(list_findings(groups, step, reading, "every-nested")),
        nested_lists=nested_lists(groups),
    )
    for key, value in room_changes(nodes, parts, ties, step, reading).items():
        row[f"room_{key}"] = value
    row["fill"] = sum(1 for t in texts if t.fills(reading))
    for anchor in ("start", "middle", "end"):
        row[anchor] = sum(1 for t in texts if t.anchor() == anchor)
    if VERBOSE:
        for m in sib:
            print(f"    sib {m.axis} {m.kind} {m.first.short}~{m.second.short} {m.near}")
        for g in sib_gaps:
            print(f"    sib gap {g}")
        for f in own:
            sides = f"{f[0].first_side.short}|{f[0].second_side.short}"
            print(f"    own {f[0].axis} {f[0].kind} {sides}: {say(f)}")
        for f in named:
            sides = f"{f[0].first_side.short}|{f[0].second_side.short}"
            print(f"    named {f[0].axis} {f[0].kind} {sides}: {say(f)}")
        for e in lists:
            print(f"    lists {e}")
        for e in list_findings(groups, step, reading, "nested"):
            print(f"    lists, nested compared {e}")
    print(f"{label} {root.id}: " + ", ".join(f"{k}={v}" for k, v in row.items()))
    return row


def run_piece(name: str, reading: Reading) -> None:
    from _lib import checks, viewing

    project = viewing.opened(ROOT, name)
    for language, result in project.scenes(facts=project.piece.stand_ins):
        scene = result.scene.to_dict()
        step = checks._space_step(project, result.scene.size_key)
        totals: Counter = Counter()
        for page_el, ox, oy in pages_of(scene):
            totals.update(study(page_el, ox, oy, step.value if step else 0, reading, name))
        print(f"  total {name} {language}: " + ", ".join(f"{k}={v}" for k, v in totals.items()))


# --- planted cases ----------------------------------------------------------------------------


def el(
    kind: str,
    ident: str,
    x: float,
    y: float,
    w: float,
    h: float,
    children: list[dict] | None = None,
    component: str | None = None,
    widest: float | None = None,
    anchor: str = "start",
    lines: list[float] | None = None,
    given: bool = True,
) -> dict:
    out: dict = {"type": kind, "id": ident, "x": x, "y": y, "width": w, "height": h}
    if children is not None:
        out["children"] = children
    if component:
        out["component"] = component
    if kind == "text":
        out["text-anchor"] = anchor
        widths = lines if lines is not None else [w if widest is None else widest]
        out["lines"] = [{"width": width} for width in widths]
        if not given:
            out["sources"] = {"width": "engine"}
    return out


def page(*children: dict) -> dict:
    return el("group", "page", 0, 0, 800, 600, list(children))


def header_and_body(
    *body: dict, title: dict | None = None, body_x: float = 43, body_w: float = 717
) -> dict:
    """The Context's margin: a header 40 px from the page's left edge, 720 px wide, and a body
    `body_x` from it and `body_w` wide, by default 43 px and 717 px, so their right edges
    agree."""
    title = title or el("text", "title", 0, 0, 720, 40, widest=300)
    return page(
        el("group", "header", 40, 20, 720, 60, [title]),
        el("group", "body", body_x, 100, body_w, 400, list(body)),
    )


def planted() -> dict[str, dict]:
    cases: dict[str, dict] = {}
    cases["margin, texts take the width, lines shorter"] = header_and_body(
        el("text", "paragraph", 0, 0, 717, 100, widest=600),
        el("text", "list", 0, 120, 717, 100, widest=500),
    )
    cases["margin, the paragraph and the list wrapped, widest lines at the width"] = (
        header_and_body(
            el("text", "paragraph", 0, 0, 717, 100, lines=[716.6, 690, 412]),
            el("text", "list", 0, 120, 717, 100, lines=[700, 716.2]),
        )
    )
    cases["margin, the paragraph's one line reaches its width"] = header_and_body(
        el("text", "paragraph", 0, 0, 717, 100, widest=717),
    )
    cases["margin, both of one line reaching their widths, right edges agree"] = header_and_body(
        el("text", "paragraph", 0, 0, 717, 100, widest=716.5),
        title=el("text", "title", 0, 0, 720, 40, widest=720),
    )
    cases["margin, both wrapped, widest lines at their widths, right edges agree"] = (
        header_and_body(
            el("text", "paragraph", 0, 0, 717, 100, lines=[716.6, 690, 412]),
            title=el("text", "title", 0, 0, 720, 40, lines=[719.6, 380]),
        )
    )
    cases["margin, the paragraph overflows, the title's line reaches its width"] = header_and_body(
        el("text", "paragraph", 0, 0, 717, 30, widest=731),
        title=el("text", "title", 0, 0, 720, 40, widest=720),
    )
    cases["two labels given no width, 3 px apart at their left"] = page(
        el("group", "a", 40, 20, 300, 40, [el("text", "label", 0, 0, 120, 30, given=False)]),
        el("group", "b", 43, 100, 300, 40, [el("text", "label", 0, 0, 150, 30, given=False)]),
    )
    cases["insets: a title in a card, 16 px in on the left and 18 px on the right"] = page(
        el(
            "group",
            "card",
            20,
            20,
            240,
            200,
            [
                el("box", "box", 0, 0, 240, 200),
                el("text", "title", 16, 16, 206, 30, widest=120),
            ],
        ),
    )
    for name, label in (
        ("given no width", el("text", "label", 8, 4, 82, 22, given=False)),
        ("given its width, its line reaching it", el("text", "label", 8, 4, 82, 22)),
        ("that overflows", el("text", "label", 8, 4, 82, 22, widest=95)),
    ):
        cases[f"insets: a label {name}, 8 and 10 px in its tag"] = page(
            el("group", "tag", 20, 20, 100, 30, [el("box", "box", 0, 0, 100, 30), label]),
        )
    cases["header 40..760 beside body 43.5..761.5"] = header_and_body(
        el("text", "paragraph", 0, 0, 718, 100, lines=[700, 650]), body_x=43.5, body_w=718
    )
    cases["header 40..760 beside body 43.5..761.5, a box 2.2 px right of the title"] = (
        header_and_body(el("box", "box", -1.3, 0, 200, 60), body_x=43.5, body_w=718)
    )
    cases["room edge only"] = page(
        el("group", "header", 40, 20, 700, 60, [el("text", "title", 10, 0, 300, 40, widest=200)]),
        el(
            "group",
            "body",
            43,
            100,
            717,
            400,
            [
                el("text", "paragraph", 0, 0, 600, 100, widest=500),
            ],
        ),
    )

    def plain_card(i: int, y: float) -> dict:
        return el(
            "group",
            f"k{i}",
            20 + i * 260,
            y,
            240,
            200,
            [
                el("box", f"k{i}/box", 0, 0, 240, 200),
                el("text", f"k{i}/title", 16, 16, 208, 30, widest=150),
            ],
            component="card",
        )

    cases["row, one card set 2 px lower"] = page(
        el("group", "row", 0, 0, 800, 300, [plain_card(0, 40), plain_card(1, 42)])
    )

    def card(i: int, dy: float) -> dict:
        return el(
            "group",
            f"card{i}",
            20 + i * 260,
            40,
            240,
            200,
            [
                el("box", f"card{i}/box", 0, 0, 240, 200),
                el(
                    "group",
                    f"card{i}/content",
                    16,
                    16 + dy,
                    208,
                    168,
                    [
                        el("text", f"card{i}/title", 0, 0, 208, 30, widest=150),
                        el("text", f"card{i}/text", 0, 40, 208, 60, widest=190),
                    ],
                ),
            ],
            component="card",
        )

    cases["row, one card's content 2 px low"] = page(
        el("group", "row", 0, 0, 800, 300, [card(0, 0), card(1, 2), card(2, 0)])
    )

    def footed(i: int, dy: float, title: float, foot: float) -> dict:
        return el(
            "group",
            f"f{i}",
            20 + i * 260,
            40,
            240,
            200,
            [
                el("box", f"f{i}/box", 0, 0, 240, 200),
                el(
                    "group",
                    f"f{i}/content",
                    16,
                    16 + dy,
                    208,
                    168,
                    [
                        el("text", f"f{i}/title", 0, 0, 208, title, widest=150),
                        el("text", f"f{i}/foot", 0, 168 - foot, 208, foot, widest=100),
                    ],
                ),
            ],
            component="card",
        )

    cases["two cards, the second's content 2 px low, its title and its foot taller"] = page(
        el("group", "row", 0, 0, 800, 300, [footed(0, 0, 30, 20), footed(1, 2, 60, 40)])
    )
    cases["a row of three texts 200 px wide, 16 px and 19 px apart"] = page(
        el(
            "group",
            "row",
            20,
            20,
            700,
            40,
            [
                el("text", "a", 0, 0, 200, 30, widest=120),
                el("text", "b", 216, 0, 200, 30, widest=90),
                el("text", "c", 435, 0, 200, 30, widest=150),
            ],
        ),
    )

    def section(ident: str, y: float, dx: float = 0) -> dict:
        return el(
            "group",
            ident,
            40,
            y,
            720,
            80,
            [
                el("text", f"{ident}/title", dx, 0, 720 - dx, 30, widest=200),
                el("text", f"{ident}/text", 0, 40, 720, 30, widest=400),
            ],
        )

    cases["header, three sections, footer; one title 3 px in"] = page(
        section("header", 0),
        section("s1", 100),
        section("s2", 200, dx=3),
        section("s3", 300),
        section("footer", 400),
    )

    def dotted(i: int) -> dict:
        return el(
            "group",
            f"c{i}",
            20 + i * 150,
            40,
            140,
            100,
            [
                el("box", f"c{i}/box", 0, 0, 140, 100),
                el("path", f"c{i}/dot", 67, -3, 6, 6),
            ],
        )

    cases["a row of four cards, a dot on each top edge"] = page(
        el("group", "row", 0, 0, 800, 300, [dotted(i) for i in range(4)])
    )

    def items(ident: str, x: float, gap: float) -> dict:
        return el(
            "group",
            ident,
            x,
            40,
            200,
            300,
            [
                el(
                    "group",
                    f"{ident}#{i}",
                    0,
                    i * (30 + gap),
                    200,
                    30,
                    [
                        el("text", f"{ident}#{i}/text", 0, 0, 200, 30, widest=120),
                    ],
                    component="item",
                )
                for i in range(4)
            ],
        )

    cases["two lists of one component, 12 px and 14 px apart"] = page(
        items("listA", 20, 12), items("listB", 400, 14)
    )

    def node(ident: str, y: float, width: float, gaps_below: list[float]) -> tuple[dict, float]:
        """An item a tree's component draws, which draws its children with itself: two of
        them, `gaps_below[0]` apart, the first holding the next level."""
        parts = [el("text", f"{ident}/text", 0, 0, width, 24, widest=120)]
        height = 24.0
        if gaps_below:
            kids, top = [], 0.0
            for i in range(2):
                deeper = gaps_below[1:] if i == 0 else []
                child, tall = node(f"{ident}/kids#{i + 1}", top, width - 24, deeper)
                kids.append(child)
                top += tall + gaps_below[0]
            inner = top - gaps_below[0]
            parts.append(el("group", f"{ident}/kids", 24, 32, width - 24, inner, kids))
            height = 32 + inner
        return el("group", ident, 0, y, width, height, parts, component="node"), height

    first, tall = node("tree#1", 0, 300, [14, 16])
    second, _ = node("tree#2", tall + 12, 300, [])
    cases["a tree of three levels, its lists 12 px, 14 px and 16 px apart"] = page(
        el("group", "tree", 20, 20, 300, 560, [first, second])
    )
    cases["a box and a label beside a sign, its middle 1.60 px below theirs"] = page(
        el(
            "group",
            "g1",
            0,
            0,
            300,
            300,
            [
                el("box", "box", 0, 86.40, 100, 40),
                el("box", "label", 120, 95.21, 60, 22.38),
            ],
        ),
        el("group", "g2", 400, 0, 300, 300, [el("path", "sign", 100, 100, 16, 16)]),
    )
    g1 = el(
        "group",
        "g1",
        0,
        0,
        300,
        300,
        [
            el("text", "label", 120, 95.21, 60, 22.38, given=False),
            el("path", "dot", 200, 103.00, 6.80, 6.80),
        ],
    )
    g2 = el("group", "g2", 400, 0, 300, 300, [el("path", "sign", 100, 100, 16, 16)])
    cases["a label and a dot beside a sign, the label's group drawn first"] = page(g1, g2)
    cases["a label and a dot beside a sign, the sign's group drawn first"] = page(g2, g1)
    return cases


def main() -> None:
    reading = Reading(fill=_option("--fill", "record"), ties="--ties" in sys.argv)
    if "--planted" in sys.argv:
        for label, page_el in planted().items():
            study(page_el, 0, 0, 4.0, reading, f"planted: {label}:")
        return
    for piece in sys.argv[1:]:
        if piece.startswith("-") or piece in ("box", "widest", "reach", "record"):
            continue
        run_piece(piece, reading)


if __name__ == "__main__":
    main()
