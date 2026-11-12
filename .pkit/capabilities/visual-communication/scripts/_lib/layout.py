"""Components as data, and the values of one scene computed in reference order
(visual-communication DEC-001 points 4 and 6, DEC-005 points 1 to 3, DEC-010, DEC-011,
DEC-012).

**A component** is a mapping. Beside its binding (`pkit_schema`, `schema_version`) it holds:

- `status` and `about`;
- `fields`: the JSON Schema of the content it takes. The engine reads its `properties`. A
  field whose `type` is `array`, or a list of types holding it, is a list field. A field
  whose `type` is `string` alone, with no `enum`, `const` or `$ref`, may be marked
  `x-pkit-runs: [<word>, ...]`, the words of its run styles, the first the default: a
  field of runs, whose content is text, read as one run of the first word, or a list of
  runs, each text or `{text, style?, concept?}` (DEC-012 points 1 and 2). The mark lies on
  no schema below a field, and no `$ref` leads to it;
- `options`: each a list of words, the first the default; or `{item: <list field>}`,
  which names an item of that list by its id; or `{item: <list field>, point: true}`,
  which names an item and one of its exposed points, `{item: <id>, point: <name>}`. Such
  an option needs exactly one part that repeats over its list;
- `states`: each `{colour: <family>}`, or `{}` to keep the family;
- `colour`: the component's default colour family;
- `values`: named formulas, read by their name alone;
- `preferred`: `width` and `height`, the size it asks for;
- `physical-size`, on a page alone or a top whose layouts are its pages' forms alone:
  `{width: <mm>, height: <mm>}`, the trim size its pages print at, each a positive number
  (DEC-034 point 3). No formula reads it. The top asks for its height through it, never
  under `preferred`: the engine sets the height from the width it asks for and the size's
  proportion, wherever the top lies, and names itself as the height's source;
- `parts`: drawn in order (below);
- `lists`: for each list field a `repeat` part of its own repeats over, the fields DEC-010
  gives that list, `{component: <field>, arrangement: {<field>: {words: [<word>, ...],
  shares: {<word>: <number>, ...}}}, ends: [<field>, <field>]}`. `component` names the
  list's component field, a field of its own that no part places or passes on and that
  takes no runs, in which content names the component that draws each item that names
  none, as it places a component. Each arrangement field is a key an item of the list
  may carry, taking one of its `words`, the first the default; one with `shares`, a
  number above zero for each word, is the list's weight, of which a list holds one at
  most (DEC-010 points 1 to 4). `ends` makes the list a list of ties: its two end fields,
  where each tie starts and where it ends, keys every tie gives as `{item: <key path>}`
  or `{item: <key path>, point: <name>}`. Each is a name, no reserved key's and no
  arrangement field's of its list (DEC-011 points 1 and 2);
- `ends: true`: the component takes ends. Drawn as a tie, it is given two, `start` and
  `end`: each the element drawn for the item its end names, or that item's point, its
  frame mapped into the component's own frame (DEC-011 point 1). A formula reads an end
  as `{start}` or `{end}`, then a measure, and a line part draws a connector between them
  with `connect`. It declares no option `start` or `end`;
- `exposes`: the parts a component that places it may read. An exposed image part
  exposes its picture's points too, as parts of zero size of the component itself;
- `tokens`: its component tokens, each by its name, `{type, default}`, at
  `component.<library>.<component>.<name>` (DEC-035 points 1 and 2). The scope reads and
  judges each declaration (`tokens.read_component_tokens`). Here, only the component that
  declares a token reads it, by its full path, wherever it reads a role: a role a part,
  a formula or a top's drawing of a layout reads under `component` that the component does
  not declare is `component-token-undeclared`. A piece's own component declares none
  (`component-token-local`, DEC-035 point 5). What it reads is kept (`token_reads`), so a
  token its file reads nowhere is found (`unread_tokens`);
- `layouts`, on a top component. Format 1's form is one layout, `{<layout>: {slots:
  {<field>: {pages: true}?}}}`, whose slots name fields of the top and whose drawing is
  the top's parts. What a slot of pages places is a page. A top component with no slot of
  pages is a page alone, and part of the page that holds it (DEC-005 point 5). A top whose
  layouts are its pages' forms (DEC-010 point 5) marks one list field of its own
  `x-pkit-pages: true`, holds no parts, and declares each layout as `{slots: {<slot>:
  <field schema>}, required: [<slot>, ...], preferred: {height: <formula>}, parts: {...},
  lists: {...}}`: the fields a page in it fills, a slot marked as a field of runs as a
  field is, the height of its page, by a formula on its parts, the layout's own drawing,
  its default (DEC-009 point 1), and the fields of each list among its slots that the
  drawing repeats over, as a pattern's `lists` (DEC-011 point 5). A layout says no width,
  and says its page's height where the top asks for none, by a formula or through its
  physical size (DEC-022 point 3). Each page
  names its layout with `layout`, or its component with `use`, and is drawn as a page of
  its own. It gets the top's width, and the top's height where the top asks for one, else
  the height it asks for: its layout's, or its component's. A top that asks for no height
  is as tall as its tallest page.
- `draws: {top: <library>/<component>, layout: <layout>}`, on a brand's component: it is a
  *drawing* of that layout of that top (DEC-009 point 2, DEC-034 point 1). It carries no
  `status`, since nothing names it (DEC-034 point 8). It declares nothing the content
  gives, none of `GIVEN_BY_TOP`, and takes the top's: its fields, options, states and
  colour, and the layout's slots and lists. It holds its parts, its values, its exposed
  parts, its component tokens and the size its instance asks for: of a layout that is a
  page's form, its page's height alone, which it says where the top asks for none, by a
  formula or through its physical size; of a top whose one layout is the whole top, its
  `preferred` whole, but for a height the top's physical size sets (DEC-034 points 2 and
  3). It reads none of its top's component tokens. A brand's drawings reach the
  engine as a `Choice`: where one is chosen, it draws each instance of its layout in place
  of the top's own drawing, and keeps the instance's trace. One that does not fit an
  instance in every language and at every key over the size axes leaves that instance to
  the top's own drawing in all of them (DEC-034 point 6), which the caller works out from
  each scene's `Context.misfits`. Content, or a component, that places a drawing by `use`
  is `drawing-placed` (DEC-009 point 5). A drawing of a top a brand holds is
  `drawing-held-top`, which the brand's check alone finds (DEC-034 point 4).

**A part** is one of:

- a primitive, `box`, `ellipse`, `text`, `line`, `image` or `sign`, whose own mapping
  holds its properties under SVG's names: `fill`, `stroke`, `stroke-width`, `rx`,
  `text-anchor`;
  a text's `content` (a field), or `fact` (a fact of its export, one of `FACTS`, which
  takes no switch), and `style` (a typography role); an image's source, exactly one of
  `produced` (a field naming a produced output), `content` (a field whose text is the bare
  name of a picture file of the piece), `file` (the bare name of a picture file of the
  component's own library version, or of the piece for a local component) and `role` (a
  picture role, whose file the brand gives; DEC-025 points 1 to 4). Only a text part shows
  a field of runs: its `style`
  and `fill` may switch on the run styles of the field it shows, `{by: <field>, <word>:
  <value>, ...}`, naming every word, and give each run the role and the paint its word
  chooses. Such a part alone may take `sign`, `true` or `false`, whether a run that names a
  concept with a sign draws it before its text, and `ground`, a paint or none, drawn behind
  the run, and either may switch on the run styles too (DEC-036 point 3). Their lengths
  come from the foundations' roles `SIGN_GAP`, `GROUND_ROOM` and `GROUND_CORNER`;
- `use: <library>/<component>`, a component the part places, with `fields` (its field ->
  a field of this component) and `options` (its option -> a word, or a switch);
- `slot: <field>`, the component the content places in that field;
- `repeat: <list field>`, each item drawn by the item's own `use`, else by the one its
  list's component field names, else by `draw` (a use). An item that names none takes
  each key the field gives that it does not give itself, and names the field as its
  source. A key that both an item's component and its list declare is read by neither.
  Items are arranged by `row` or `column` with `gap`, `align-items` (`stretch start
  center end`), `justify-content` (`start center end space-between`) and `sizes` (`own`,
  each item its preferred size along the line, `equal`, the line shared equally, or
  `shares`, the line shared in proportion to the shares its list's weight gives its
  items, equally where they are all the same). An item that `stretch` makes larger
  across than it asks for passes the rest on to the last part it draws, where that part
  places a component and gives no size across (`passed_on`). `colour` gives
  the items' default family. A part over a list of ties takes neither `row` nor
  `column`: each tie is drawn in the part's whole frame, by default the component's, and
  given its ends (`find_ends`). A tie whose component takes no ends is left out.

**A sign** draws the sign of the concept whose colour family its instance takes: the
concept the instance names, or, where it takes its family from the instance it sits in,
that instance's (DEC-036 point 2). It is painted as a box is, with `fill`, `stroke` and
`stroke-width`, and an `override` reaches its fill. Where the instance takes its family
from no concept, or the concept has no sign, it is not drawn, at zero size. A state that
changes the family changes the paint alone, never the sign.

**An image** shows a produced output, its variants by key and its exposed points; or a
picture file, found by its bare name and read through the environment, which judges it
(`Env.picture_file`); or the file the brand gives a picture role at the scene's key over
the size axes, read through the environment too (`Env.picture_role`). A picture file and a
picture role have no points. A finding on a file's name lies in what named it, the content
or the component; one on the file, at the file. A `role` that names no role is
`unknown-role`, and one that names a role of another type `role-type`, each in the
component. A field the content leaves empty, a picture file that cannot be read, and a
picture role the brand gives no file, draw no image, at zero size, and only the file that
cannot be read is a finding: no brand owes a picture role (DEC-025 point 4).

A part may carry `when`: a field the content fills, a field of runs where one of its
runs holds text, `{<option>: [<word>, ...]}`, or a switch on a size (below) whose each
branch is `true`, `false`, or one of those. A missing part has zero size at its
place. Its place is `x` and `y` (zero if absent), its
size `width` and `height`, each a formula. A line has `x1 y1 x2 y2`; or, in a component
that takes ends, `connect: straight` or `connect: corners`, the connector tool, which
runs from its start to its end, straight or with corners, never around anything, and
spreads the ends that meet one side of an item evenly (DEC-005 point 2). A line's
`marker-start` and `marker-end` are `none`, the default, or `arrow`. A text's height is
its measured text's, and its width, where none is given, its widest paragraph's. An
image's height, where none is given, keeps its picture's proportions, a produced output's
first variant's, a picture file's, or a picture role's file's at the scene's key. Any
property
value may be a switch, `{by: <option>, <word>: <value>, ...}`, naming every word. A
switch on a field's run styles serves only a text part's `style`, `fill`, `sign` and
`ground`, and no part
passes a field of runs on, or reads one but in `when`. A colour is a role's token path,
or `:colour.<member>`: the role the foundations map that member of the instance's colour
family to (DEC-004 point 10). The instance's family is the one a notation maps the
content's `concept: <notation>/<concept>` to, else the `colour` of the `repeat` part
that draws it, else its component's, else its container's; a state may change it. A run
that names a concept takes that concept's family before its instance's, and a state
that changes the instance's family replaces it too. Content's `override: {<part>:
<role>}` points a part's paint at another role, each run's included. `:index` and
`:count` are an item's place among the items its list draws, from 1, and how many it
draws.

**A size** reaches a component by a marked name, `:<axis>`: a switch or a `when` by it
reads the mode of that size axis the scene's key holds, else the axis's default (DEC-021
point 3). Such a switch names the axis's default, which takes each mode it leaves out, so
a new mode draws as the default does. The axis is one of the size axes a piece can name,
which the context holds (`Sizes`), and a mode it names is one of the axis's. A part a
size hides is a missing part. Two parts that repeat over one list, whose `when`s by a
size each say yes or no, say yes exactly once at each mode, so each item is drawn once
at every size (point 4). A value a size chose names the axis as its source, `size:<axis>`.

**Ties.** Once every instance is built, and before any value is computed, `find_ends`
finds each tie's two ends (DEC-011 points 3 and 4). An end's key path starts in the
content mapping that holds the tie's list, in the keys the content file writes, and
names each item on the way by its id. The end is found where the item is drawn exactly
once below the pattern, on the tie's page. A tie whose end is not found, or that does
not lie on one page with both its ends, is left out and reported in the content. One
whose end the check of the content refuses, by its shape or its path, is left out
unreported, as the check reports it.

**Computed value by value.** Every value is a cell computed on first use, in the order
the references give, as a spreadsheet computes its cells: a loop is refused naming every
element in it. A value has one owner: a part's formula, its measured text, or its
parent's layout. The frames of a tie's ends are cells too. Each problem is a finding; a
value that cannot be computed is zero.

**Where a finding lies** is the file a person edits to mend it. A finding in a component,
or in what a component's part gave the component it places, names that component as
`component`, and its library's version as `library`, empty for the piece's own. The
finding on a component whose file cannot be read names it so too, and what names that
component takes none. A finding in what the content gave names neither. A top that names
no component lies in the piece, which names it: the finding says so as `piece`. So does
a part that reads a library's own role the brand leaves with no value, where neither the
brand nor a brand it builds on names the library: neither alone is at fault, so it lies
at the piece's lock, which combines them (DEC-008 point 9). Where one names the library,
that brand's own finding says what it owes, and the part takes none.
"""

from __future__ import annotations

import itertools
import math
import re
from collections.abc import Callable, Collection, Iterator, Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any, TypeVar

from _lib import formula as fm
from _lib import names
from _lib.env import Env, PictureInfo, UnknownConcept, UnreadableComponent, UnvaluedRole
from _lib.findings import ATTENTION, FAILS, Finding
from _lib.findings import FACT as STATED
from _lib.keys import AxisLike, key_order
from _lib.outlines import Outline
from _lib.pictures import Judged, Picture
from _lib.text import Broken, Faces, Marks, Run, Style, break_runs

PRIMITIVES = ("box", "ellipse", "text", "line", "image", "sign")
PLACING = ("use", "slot", "repeat")
KINDS = PRIMITIVES + PLACING

#: The keys each kind of part takes beside its kind and `when`.
PART_KEYS: Mapping[str, tuple[str, ...]] = {
    "box": ("x", "y", "width", "height"),
    "ellipse": ("x", "y", "width", "height"),
    "text": ("x", "y", "width"),
    "line": ("x1", "y1", "x2", "y2", "connect"),
    "image": ("x", "y", "width", "height"),
    "sign": ("x", "y", "width", "height"),
    "use": ("x", "y", "width", "height", "fields", "options"),
    "slot": ("x", "y", "width", "height"),
    "repeat": ("x", "y", "width", "height", "draw", "colour", "row", "column"),
}

#: The keys of a part that hold a formula: a place, a size or a line's end.
GEOMETRY = ("x", "y", "width", "height", "x1", "y1", "x2", "y2")

#: The keys each kind of part needs beside its kind. A line that connects its component's
#: ends needs none of its ends (`ENDS_OF_LINE`).
REQUIRED: Mapping[str, tuple[str, ...]] = {
    "box": ("width", "height"),
    "ellipse": ("width", "height"),
    "line": ("x1", "y1", "x2", "y2"),
    "image": ("width",),
    "sign": ("width", "height"),
    "repeat": ("draw",),
}

#: A line's ends, which a line that connects gives none of.
ENDS_OF_LINE = ("x1", "y1", "x2", "y2")

#: Each primitive's properties, in its own mapping, under SVG's names.
PROPERTIES: Mapping[str, tuple[str, ...]] = {
    "box": ("fill", "stroke", "stroke-width", "rx"),
    "ellipse": ("fill", "stroke", "stroke-width"),
    "text": ("content", "fact", "style", "fill", "text-anchor", "sign", "ground"),
    "line": ("stroke", "stroke-width", "marker-start", "marker-end"),
    "image": ("produced", "content", "file", "role"),
    "sign": ("fill", "stroke", "stroke-width"),
}
REQUIRED_PROPERTIES: Mapping[str, tuple[str, ...]] = {
    "text": ("style",),
    "line": ("stroke",),
}

#: What an image shows, of which it names exactly one (DEC-025 point 1): a produced output,
#: by a field; a picture file of the piece, by a field; a picture file of the component's own
#: library, by its bare name; the file a brand gives a picture role, by the role.
IMAGE_SOURCES = ("produced", "content", "file", "role")

#: The paint content's `override` points at another role, by kind of part.
OVERRIDDEN = {"box": "fill", "ellipse": "fill", "text": "fill", "line": "stroke", "sign": "fill"}

PAINTS = ("fill", "stroke")
LENGTHS = ("stroke-width", "rx")

#: What a text part that shows a field of runs may choose for each run beside its role and
#: its paint (DEC-036 point 3): whether it draws its concept's sign, and its ground, a paint.
RUN_MARKS = ("sign", "ground")

#: The roles the foundations declare for a run's sign and ground (DEC-036 point 3): the gap
#: between a sign and the character after it, the room at each end of a ground, and the
#: radius of a ground's corners where it starts and ends.
SIGN_GAP = "space.sign-gap"
GROUND_ROOM = "space.ground-room"
GROUND_CORNER = "space.ground-corner"

#: The roles each choice of a run's sign or ground reads.
MARK_ROLES: Mapping[str, tuple[str, ...]] = {
    "sign": (SIGN_GAP,),
    "ground": (GROUND_ROOM, GROUND_CORNER),
}
OPERATORS = ("row", "column")

#: The words a property takes, the first its default.
WORDS: Mapping[str, tuple[str, ...]] = {
    "text-anchor": ("start", "middle", "end"),
    "align-items": ("stretch", "start", "center", "end"),
    "justify-content": ("start", "center", "end", "space-between"),
    "sizes": ("own", "equal", "shares"),
    "marker-start": ("none", "arrow"),
    "marker-end": ("none", "arrow"),
    "connect": ("straight", "corners"),
}
OPERATOR_WORDS = ("align-items", "justify-content", "sizes")

#: The facts of its export a text part may show (DEC-006 point 7). They are no entry of
#: `WORDS`, since a fact takes no switch.
FACTS = ("version", "date", "language", "state")

#: The text a scene takes for each fact no file holds (DEC-016 point 5). One form serves
#: every language: a number as an exported file's name writes it, and a date as
#: `YYYY-MM-DD`. Each digit is one that sets wide, so a usual real value fits.
STAND_INS: Mapping[str, str] = {"version": "v88", "date": "2088-08-28"}

COMPONENT_KEYS = (
    "pkit_schema", "schema_version", "status", "about", "fields", "options", "states",
    "colour", "values", "preferred", "parts", "lists", "exposes", "ends", "tokens",
    "physical-size", "layouts", "draws",
)  # fmt: skip

#: The key under which a top whose pages print at one size declares it, its trim width and
#: height in millimetres (DEC-034 point 3), and the code of every finding on it.
PHYSICAL_SIZE = "physical-size"

#: The key under which a component declares its component tokens (DEC-035 point 1).
TOKENS = "tokens"

#: The key under which a top component declares its layouts (DEC-001 point 4).
LAYOUTS = "layouts"

#: The key by which a brand's component names the top and the layout it draws, which makes
#: it a drawing (DEC-034 point 1); the key of a component's status, which a drawing never
#: carries (DEC-034 point 8); the keys of what the content gives, which a drawing takes
#: from its top and never declares; and the keys a drawing holds of its own.
DRAWS = "draws"
STATUS = "status"
GIVEN_BY_TOP = ("fields", "options", "states", "colour", "lists", "layouts", "ends")
DRAWING_KEYS = ("parts", "values", "preferred", "exposes", TOKENS)

#: The findings on a drawing (DEC-034 points 1, 2, 4, 5 and 8, DEC-009 point 5): one that
#: is no brand's component, carries a status, holds what the content gives, or draws no
#: layout a top declares; one that writes a size its top writes, or none its page needs; a
#: field it shows by no part named after it, or a part named after a field that shows
#: another thing; content or a component that places one by `use`; and one whose top a
#: brand holds.
DRAWING_SHAPE = "drawing-shape"
DRAWING_SIZE = "drawing-size"
FIELD_PART = "drawing-field-part"
DRAWING_PLACED = "drawing-placed"
DRAWING_HELD_TOP = "drawing-held-top"

#: The fact a piece states for each instance its top's own drawing draws, since the brand's
#: drawing does not fit it (DEC-034 point 6, DEC-009 point 9).
DRAWING_MISFIT = "drawing-misfit"

#: What a brand's version checked alone shows of the forms it draws (DEC-009 points 2, 3, 4
#: and 9, DEC-034 point 8): a drawing of a top whose library the brand does not name; two
#: drawings of one layout; a drawing of a top a brand nearer the root of its chain serves,
#: which a piece under the brand also states; what a drawing does not take of what its top
#: declares; and each top the brand serves, with the layouts it leaves to the top's own
#: drawing.
DRAWING_UNNAMED = "drawing-unnamed"
DRAWING_TWICE = "drawing-twice"
DRAWING_BASE_SERVES = "drawing-base-serves"
DRAWING_LACKS = "drawing-lacks"
BRAND_SERVES = "brand-serves"

#: The findings on a component's reading of component tokens (DEC-035 points 3, 5 and 9): a
#: token it reads and does not declare, a token in a piece's own component, and a token
#: its file reads nowhere.
TOKEN_UNDECLARED = "component-token-undeclared"
TOKEN_LOCAL = "component-token-local"
TOKEN_UNREAD = "component-token-unread"

#: The statuses whose components a library promises, so that a token it reads nowhere is
#: kept until a major (DEC-003 point 7, DEC-035 point 6).
PROMISED = ("stable", "deprecated")

#: The keys of a list's entry under `lists`, and of an arrangement field's (DEC-010,
#: DEC-011).
LIST_KEYS = ("component", "arrangement", "ends")
ARRANGEMENT_KEYS = ("words", "shares")

#: The names by which a component that takes ends reads them: where its tie starts, and
#: where it ends, in the order of its list's end fields (DEC-011 point 1).
ENDS = ("start", "end")

#: The keys of an end's value: the item, by its key path, and perhaps its point (DEC-011
#: point 2).
END_KEYS = ("item", "point")

#: The sides of a frame an end of a connector meets.
SIDES = ("left", "right", "top", "bottom")

#: The keys a list's component field gives each item that names no component of its own:
#: its component's options, and these (DEC-010 point 1).
GIVEN_BY_FIELD = ("concept", "state", "override")

#: The key of a switch, which no option takes as a word.
SWITCH = "by"

#: The mark of a name the engine hands a component, such as `:width`. A switch or a `when`
#: by `:<axis>` reads the mode of that size axis (DEC-021 point 3), and one by `:as`
#: whether the instance is a page (`AS`).
MARKED = ":"

#: The start of the source of a value a switch by a size axis chose (DEC-021 point 7).
SIZE = "size:"

#: The finding on a switch or a `when` by a marked name that reads no size axis a piece
#: can name, names a mode the axis lacks, or leaves out its default; and on two parts over
#: one list that do not draw each item once at every size (DEC-021 point 7).
SIZE_SWITCH = "size-switch"
SIZE_REPEAT = "size-repeat"

#: The marked name by which a drawing of a layout reads whether its instance is a page, or
#: part of a page, and its values, the default first. The engine sets it from where the
#: instance lies in its piece, never from content, and a value a switch by it chose names
#: it as its source, a kind of its own (DEC-034 point 7).
AS = ":as"
PLACED_AS = ("page", "part")

#: The finding on a switch or a `when` by `:as` in a component that is no drawing of a
#: layout, or that names a value `:as` does not take, or no branch for its default
#: (DEC-034 points 7 and 10).
AS_SWITCH = "as-switch"

#: The key by which a page of a top whose layouts are its pages' forms names its layout,
#: which the format fixes on such a page alone (DEC-010 point 5).
LAYOUT = "layout"

#: The mark of the field that holds such a top's pages.
PAGES = "x-pkit-pages"

#: The mark of a field of runs, which holds the words of its run styles (DEC-012 point 1).
RUNS = "x-pkit-runs"

#: The keys the format fixes on a run, and no other (DEC-012 point 1).
RUN_KEYS = ("text", "style", "concept")

#: The engine's mark for a member of the instance's colour family.
FAMILY = ":colour."

#: The start of the source of a value the content gave.
CONTENT = "content:"

#: The start of the source of a text that shows a fact of its export.
FACT = "fact:"

#: A size this much less than the size asked for is not short of it: half the scene's
#: rounding step.
TOLERANCE = 0.005

_ONLY_ROLE = re.compile(r"^=@([a-z0-9.-]+)$")

T = TypeVar("T")


class Fault(Exception):
    """A value that cannot be computed, with the finding that says why, or none where
    that was reported already."""

    def __init__(self, finding: Finding | None = None) -> None:
        super().__init__(finding.message if finding else "reported already")
        self.finding = finding


class _Missing(Exception):
    """A path that reaches no exposed part, point or item; the formula reading it turns
    it into a finding."""


_FAILED = object()


def _is_use(value: Any) -> bool:
    if not isinstance(value, str) or value.count("/") != 1:
        return False
    library, component = value.split("/")
    return names.is_name(library) and names.is_name(component)


def _is_field(value: Any, fields: Mapping[str, Any] | set[str]) -> bool:
    return isinstance(value, str) and value in fields


def _is_list(schema: Any) -> bool:
    """Whether a field's schema makes it a list field: its `type` is `array`, or a list of
    types that holds `array`, such as `[array, null]`."""
    kind = schema.get("type") if isinstance(schema, Mapping) else None
    return kind == "array" or (isinstance(kind, list) and "array" in kind)


def _positive(value: Any) -> bool:
    """Whether a value is a finite number above zero, and no boolean."""
    is_number = isinstance(value, int | float) and not isinstance(value, bool)
    return is_number and math.isfinite(value) and value > 0


def run_problem(name: str, schema: Any) -> str | None:
    """Why a field's schema marked `x-pkit-runs` is no field of runs (DEC-012 points 1, 2
    and 8): it takes more than text, or holds `enum`, `const` or `$ref`; or its mark
    declares no word, a word that is no name, or one twice. None where it is one."""
    if not isinstance(schema, Mapping):
        return f"the field `{name}` is no schema"
    kind = schema.get("type")
    if (kind if isinstance(kind, list) else [kind]) != ["string"]:
        return f"the field of runs `{name}` takes more than text: its `type` is `string` alone"
    held = [key for key in ("enum", "const", "$ref") if key in schema]
    if held:
        return f"the field of runs `{name}` holds `{held[0]}`, and takes any text"
    words = schema.get(RUNS)
    if not isinstance(words, list) or not words:
        return (
            f"the field of runs `{name}` declares no word of its run styles: `{RUNS}` takes a "
            "list of words, the first the default"
        )
    for word in words:
        if not names.is_name(word) or word == SWITCH:
            return f"the field of runs `{name}` declares `{word}`, which is no word of a run style"
    if len(set(words)) != len(words):
        return f"the field of runs `{name}` declares a word twice"
    return None


def runs_of(fields: Mapping[str, Any]) -> dict[str, tuple[str, ...]]:
    """The fields of runs among a component's fields, each with the words of its run
    styles, the first the default (DEC-012 points 1 and 2). A mark of another shape marks
    no field of runs, and the component's reading reports it."""
    return {
        name: tuple(schema[RUNS])
        for name, schema in fields.items()
        if isinstance(schema, Mapping) and RUNS in schema and run_problem(name, schema) is None
    }


def _marks_below(schema: Any, path: str) -> list[str]:
    """The key path of each mark of a field of runs below a schema: in a list's items or an
    object's properties, at any depth."""
    found: list[str] = []
    if not isinstance(schema, Mapping):
        return found
    below: list[tuple[str, Any]] = [(f"{path}.items", schema.get("items"))]
    properties = schema.get("properties")
    if isinstance(properties, Mapping):
        below.extend((f"{path}.properties.{key}", each) for key, each in properties.items())
    for at, each in below:
        if isinstance(each, Mapping):
            if RUNS in each:
                found.append(f"{at}.{RUNS}")
            found.extend(_marks_below(each, at))
    return found


def _refs(schema: Any, path: str) -> list[tuple[str, str]]:
    """Each local `$ref` within a schema, at any depth, with its key path."""
    found: list[tuple[str, str]] = []
    if not isinstance(schema, Mapping):
        return found
    if isinstance(schema.get("$ref"), str):
        found.append((f"{path}.$ref", schema["$ref"]))
    found.extend(_refs(schema.get("items"), f"{path}.items"))
    properties = schema.get("properties")
    if isinstance(properties, Mapping):
        for key, each in properties.items():
            found.extend(_refs(each, f"{path}.properties.{key}"))
    return found


def _target(ref: str, root: Any) -> Any:
    """What a local `$ref` (`#/...`) leads to within `root`; None where it leads nowhere."""
    if not ref.startswith("#"):
        return None
    target = root
    for step in [step for step in ref[1:].split("/") if step]:
        step = step.replace("~1", "/").replace("~0", "~")
        target = target.get(step) if isinstance(target, Mapping) else None
    return target


@dataclass(frozen=True)
class PageForms:
    """What a top whose layouts are its pages' forms declares of its pages (DEC-010 point
    5): the fields it marks as holding them, one where it is well formed, and each
    layout's slots, by name with the schema of what a page fills each with, and the slots
    a page in it must fill."""

    fields: tuple[str, ...]
    layouts: Mapping[str, tuple[Mapping[str, Any], tuple[str, ...]]]


def page_forms(data: Any) -> PageForms | None:
    """What a component's data declares of its pages, where its layouts are its pages'
    forms: it marks a field `x-pkit-pages: true`, or a layout of it holds a drawing of its
    own, its `parts`. None where neither holds, as of every component format 1 accepted.
    The engine and the check of the content both read a page so."""
    if not isinstance(data, Mapping):
        return None
    fields = data.get("fields")
    properties = fields.get("properties") if isinstance(fields, Mapping) else None
    properties = properties if isinstance(properties, Mapping) else {}
    marked = tuple(
        name
        for name, schema in properties.items()
        if isinstance(schema, Mapping) and schema.get(PAGES) is True
    )
    layouts = data.get("layouts")
    layouts = layouts if isinstance(layouts, Mapping) else {}
    if not marked and not any(isinstance(d, Mapping) and "parts" in d for d in layouts.values()):
        return None
    declared = {}
    for name, decl in layouts.items():
        slots = decl.get("slots") if isinstance(decl, Mapping) else None
        required = decl.get("required") if isinstance(decl, Mapping) else None
        declared[name] = (
            slots if isinstance(slots, Mapping) else {},
            tuple(str(slot) for slot in required) if isinstance(required, list) else (),
        )
    return PageForms(marked, declared)


@dataclass(frozen=True)
class ArrangementField:
    """An arrangement field a pattern declares for a list (DEC-010 points 2 to 4): the
    words an item of the list may give it, the first the default, and, where it is the
    list's weight, the share each word stands for, a number with no unit."""

    words: tuple[str, ...]
    shares: Mapping[str, float] | None = None

    @property
    def default(self) -> str:
        return self.words[0]


@dataclass(frozen=True)
class ListFields:
    """What a component declares for a list it repeats (DEC-010 points 1 to 4, DEC-011
    point 1): its component field, in which content may name the component that draws
    each item that names none, its arrangement fields, by name, and, for a list of ties,
    its two end fields, where each tie starts and where it ends."""

    component: str | None
    arrangement: Mapping[str, ArrangementField]
    ends: tuple[str, str] | None = None

    @property
    def weight(self) -> tuple[str, ArrangementField] | None:
        """The list's weight, by its name: its first arrangement field that gives shares."""
        return next(
            ((name, each) for name, each in self.arrangement.items() if each.shares is not None),
            None,
        )

    @property
    def keys(self) -> tuple[str, ...]:
        """The keys an item of the list carries for its pattern: its arrangement fields and
        its end fields, which the item's component never reads."""
        return (*self.arrangement, *(self.ends or ()))


def list_fields(data: Any) -> dict[str, ListFields]:
    """What a component's data declares under `lists`, by list, as far as it is of its
    shape: a component field that is a name, each arrangement field whose `words` are
    names, each once, with its shares where each word has a number above zero, and two end
    fields (`ends_problem`). What is of another shape is left out here, and the
    component's reading reports it. The engine and the check of the content both read a
    list's fields so."""
    lists = data.get("lists") if isinstance(data, Mapping) else None
    found: dict[str, ListFields] = {}
    for name, decl in (lists if isinstance(lists, Mapping) else {}).items():
        if not isinstance(decl, Mapping):
            continue
        component = decl.get("component")
        raw = decl.get("arrangement")
        arranged = {}
        for field_name, each in (raw if isinstance(raw, Mapping) else {}).items():
            words = each.get("words") if isinstance(each, Mapping) else None
            if (
                _words_problem(words) is not None
                or not names.is_name(field_name)
                or field_name in names.RESERVED_PLACING_KEYS
            ):
                continue
            arranged[str(field_name)] = ArrangementField(tuple(words), _shares(words, each))
        ends = decl.get("ends")
        found[str(name)] = ListFields(
            str(component) if names.is_name(component) else None,
            arranged,
            (str(ends[0]), str(ends[1])) if ends_problem(ends, arranged) is None else None,
        )
    return found


def ends_problem(ends: Any, arrangement: Collection[str] = ()) -> str | None:
    """Why a list's `ends` are no two end fields (DEC-011 points 1 and 8): not two, a name
    that is no name or a reserved key's, the same name twice, or the name of an
    arrangement field of the list. None where they are two end fields."""
    if not isinstance(ends, list) or len(ends) != 2:
        return "takes two end fields, where each tie starts and where it ends"
    for name in ends:
        if not names.is_name(name) or name in names.RESERVED_PLACING_KEYS:
            return f"names `{name}`, which is no name, or a reserved key's"
        if name in arrangement:
            return f"names `{name}`, an arrangement field of the list too"
    if ends[0] == ends[1]:
        return f"names `{ends[0]}` twice: a tie starts and ends at two fields"
    return None


#: A step of a key path: a key, and the id of an item of the list it holds (DEC-011 point 3).
_KEY_STEP = re.compile(r"^(?P<key>[^.\[\]]+)(?:\[(?P<id>[^.\[\]]+)\])?$")


def key_path(text: Any) -> list[tuple[str, str | None]] | None:
    """The steps of an end's key path (DEC-011 point 3): each a key of the content file and,
    where it steps into a list, the id of the item, as `<key>[<id>]`, joined by `.`. None
    where it is no key path: no text, a key that is no name, or an id that is no id. The
    engine and the check of the content both read an end's path so."""
    if not isinstance(text, str) or not text:
        return None
    steps: list[tuple[str, str | None]] = []
    for each in text.split("."):
        match = _KEY_STEP.match(each)
        if match is None or not names.is_name(match["key"]):
            return None
        if match["id"] is not None and not names.is_id(match["id"]):
            return None
        steps.append((match["key"], match["id"]))
    return steps


def through(first: str, second: str) -> bool:
    """Whether two key paths name one item, or one leads through the other's item."""
    return first == second or second.startswith(f"{first}.") or first.startswith(f"{second}.")


def _words_problem(words: Any) -> str | None:
    """Why an arrangement field's `words` are no list of words it may take, or None."""
    if not isinstance(words, list) or not words:
        return "declares no word"
    if not all(names.is_name(word) and word != SWITCH for word in words):
        return f"declares a word that is no name, or `{SWITCH}`"
    if len(set(words)) != len(words):
        return "declares a word twice"
    return None


def _is_share(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def _shares(words: list[str], decl: Mapping[str, Any]) -> dict[str, float] | None:
    """A weight's share for each of its words, where `shares` gives each a number above
    zero and names no other word; None otherwise."""
    shares = decl.get("shares")
    if not isinstance(shares, Mapping) or set(shares) != set(words):
        return None
    if not all(_is_share(share) for share in shares.values()):
        return None
    return {word: float(shares[word]) for word in words}


def _leaves(value: Any) -> list[Any]:
    """The values a value may take: itself, or each branch of its switch, at any depth."""
    if isinstance(value, Mapping) and SWITCH in value:
        return [leaf for key, each in value.items() if key != SWITCH for leaf in _leaves(each)]
    return [value]


def _by_marked(value: Any) -> bool:
    """Whether `value` is a switch by a marked name: by a size (DEC-021 point 3), or by
    `:as` (DEC-034 point 7)."""
    by = value.get(SWITCH) if isinstance(value, Mapping) else None
    return isinstance(by, str) and by.startswith(MARKED)


def _by_size(value: Any) -> bool:
    """Whether `value` is a switch by a size, whose `by` is a marked name other than `:as`
    (DEC-021 point 3)."""
    return _by_marked(value) and value[SWITCH] != AS


def _as_branch(switch: Mapping[str, Any], placed_as: str) -> str:
    """The branch a switch by `:as` takes where its instance lies as `placed_as`, one of
    `PLACED_AS`: that value, where the switch names it, else the default (DEC-034 point
    7)."""
    return placed_as if placed_as in switch else PLACED_AS[0]


def _may_draw(when: Any, modes: Mapping[str, str], axes: Mapping[str, AxisLike]) -> bool:
    """Whether a part whose `when` is `when` may be drawn where each size axis takes the mode
    `modes` gives it, as `Instance._when` draws it: with no `when`, always; by a field or an
    option's words, on some content, so it may; by a size, by the branch of that mode, else
    of the axis's default (DEC-021 points 3 and 5); by `:as`, by the branch of either of
    its values, since its instance may lie as either (DEC-034 point 7). A branch draws it
    where it is `true` or a `when` of those forms. A `false`, and a `when` of no form,
    never draws it."""
    if when is None:
        return True
    if not _by_marked(when):
        return _may_hold(when)
    if when[SWITCH] == AS:
        taken = [when.get(_as_branch(when, placed_as)) for placed_as in PLACED_AS]
    else:
        axis = str(when[SWITCH])[len(MARKED) :]
        taken = [when.get(modes[axis], when.get(axes[axis].default))]
    return any(branch if isinstance(branch, bool) else _may_hold(branch) for branch in taken)


def _may_hold(when: Any) -> bool:
    """Whether a `when` by a field or an option's words may hold, on some content: one of
    either form."""
    return isinstance(when, str) or (isinstance(when, Mapping) and len(when) == 1)


def source_of_choice(chosen: Any) -> str:
    """The source of a value a switch chose: `:as`, which is a kind of its own (DEC-034
    point 7), the size axis it reads, `size:<axis>`, or the option it names,
    `option:<name>` (DEC-005 point 5, DEC-021 point 7)."""
    if chosen == AS:
        return AS
    if isinstance(chosen, str) and chosen.startswith(MARKED):
        return f"{SIZE}{chosen[len(MARKED) :]}"
    return f"option:{chosen}"


@dataclass(frozen=True)
class Sizes:
    """The size axes a piece can name, as one scene reads them (DEC-021 point 3): each by
    its name, with its modes and its default, as the foundations declare it, and the mode
    of each that the scene's key holds, an axis the key leaves out at its default. A
    context that knows no size axis reads none, and a switch by a size is refused there."""

    axes: Mapping[str, AxisLike] = field(default_factory=dict)
    modes: Mapping[str, str] = field(default_factory=dict)

    def mode(self, axis: str) -> str:
        """The mode the scene reads on `axis`, one of `axes`."""
        return self.modes.get(axis, self.axes[axis].default)


@dataclass(frozen=True)
class Choice:
    """Which drawing draws each instance of a layout in one piece (DEC-009 points 2 and 6,
    DEC-034 point 6): the brand's drawings, each by its use under the top and the layout it
    draws, and each instance left to its top's own drawing, by its trace, with why. One
    choice serves every scene of the piece, so an instance is drawn by one drawing in every
    language and at every key. A context given none draws every layout by its top's own
    drawing, as before."""

    drawings: Mapping[tuple[str, str], str] = field(default_factory=dict)
    refused: Mapping[str, str] = field(default_factory=dict)


# --- components ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Option:
    """An option a component declares: words, or an item (and its point) of a list."""

    name: str
    words: tuple[str, ...] = ()
    items: str | None = None
    point: bool = False


@dataclass(frozen=True)
class Part:
    name: str
    kind: str
    spec: Mapping[str, Any]

    @property
    def props(self) -> Mapping[str, Any]:
        value = self.spec.get(self.kind) if self.kind in PRIMITIVES else None
        return value if isinstance(value, Mapping) else {}

    @property
    def operator(self) -> str:
        return next((name for name in OPERATORS if name in self.spec), OPERATORS[0])

    @property
    def settings(self) -> Mapping[str, Any]:
        value = self.spec.get(self.operator)
        return value if isinstance(value, Mapping) else {}

    @property
    def shows(self) -> str | None:
        """The field the part shows (DEC-034 point 5): the one a slot places, a repeat
        repeats over, a text draws, or an image names the picture of; None where it shows
        none."""
        spec, props = self.spec, self.props
        shown = {
            "slot": spec.get("slot"),
            "repeat": spec.get("repeat"),
            "text": props.get("content"),
            "image": props.get("produced", props.get("content")),
        }.get(self.kind)
        return shown if isinstance(shown, str) else None

    @property
    def passes(self) -> set[str]:
        """The fields a `use` part passes on to the component it places, which it shows one
        level down (DEC-034 point 5)."""
        fields = self.spec.get("fields") if self.kind == "use" else None
        if not isinstance(fields, Mapping):
            return set()
        return {ours for ours in fields.values() if isinstance(ours, str)}

    @property
    def main(self) -> str:
        """The size along the line a list's items lie on."""
        return "width" if self.operator == "row" else "height"


class Component:
    """A component as data, read once per scene and checked as it is read: its names, its
    switches, and every formula's references and dimensions. `issues` lists what is
    wrong, as `(code, key path, message)`."""

    def __init__(
        self,
        use: str,
        data: Mapping[str, Any],
        ctx: Context,
        *,
        layout: str | None = None,
        draws: tuple[str, str] | None = None,
    ) -> None:
        self.use = use
        self.data = data
        # The top and the layout it draws, where it is a brand's drawing, and the parts its
        # top exposes, which it exposes by the same names (DEC-034 point 1).
        self.draws = draws
        self.top_exposes: tuple[str, ...] = ()
        # Each option a switch or a `when` of it reads, with the words it reads.
        self.option_reads: dict[str, set[str]] = {}
        # In a brand's drawing, each option or field of runs a switch of it reads, with each
        # word a switch on it leaves out, by the key path of the first such switch; and each
        # field of runs a part passes on, by the key path where it does (DEC-009 point 9,
        # DEC-012 point 8). Each asks the brand's owner for attention, never failing.
        self.switch_gaps: dict[str, dict[str, str]] = {}
        self.runs_passed: dict[str, str] = {}
        # The one layout of a top whose one layout is the whole top.
        self._whole: str | None = None
        self.issues: list[tuple[str, str, str]] = []
        self.options: dict[str, Option] = {}
        self.states: dict[str, str | None] = {}
        self.parts: dict[str, Part] = {}
        self.formulas: dict[str, fm.Formula | None] = {}
        self.repeats_over: dict[str, str] = {}
        # Format 1's slots of pages.
        self.pages: frozenset[str] = frozenset()
        self.top = "layouts" in data
        # A top whose layouts are its pages' forms: the field it marks as holding its
        # pages, and each layout's own drawing, a component that draws one page.
        self.forms = False
        self.pages_field: str | None = None
        self.drawings: dict[str, Component] = {}
        # The layout this component draws, where it is a top's own drawing of one.
        self.layout = layout
        # Whether it is a drawing of a layout, the top's own or a brand's, which alone reads
        # `:as` (DEC-034 point 7): a brand's drawing, a layout's drawing of a page, or a top
        # whose one layout is the whole top, whose parts are that layout's drawing (DEC-009
        # point 1).
        self.draws_layout = (
            draws is not None or layout is not None or (self.top and page_forms(data) is None)
        )
        self._ctx = ctx
        self._value_dims: dict[str, int | None] = {}
        self._roles_reported: set[str] = set()
        fields = data.get("fields")
        properties = fields.get("properties") if isinstance(fields, Mapping) else None
        self.fields: Mapping[str, Any] = properties if isinstance(properties, Mapping) else {}
        self.lists = {name for name, schema in self.fields.items() if _is_list(schema)}
        # Each field of runs, with its words; and those some text part chooses by.
        self.runs = runs_of(self.fields)
        self.chosen_by: set[str] = set()
        self.colour: str | None = data.get("colour")
        self.values = self._mapping(data, "values")
        self.preferred = self._mapping(data, "preferred")
        # The trim width and height its pages print at, in millimetres, as declared, read
        # before its layouts, whose pages' heights may follow it (DEC-034 point 3).
        self.physical_size = self._physical_size(data)
        exposes = data.get("exposes") or []
        self.exposes: tuple[str, ...] = tuple(exposes) if isinstance(exposes, list) else ()
        # Whether it takes ends: drawn as a tie, it is given two (DEC-011 point 1). One that
        # declares `ends` of another shape is refused for that alone.
        self.takes_ends = data.get("ends") is True
        self._declares_ends = "ends" in data
        self.status = data.get("status")
        # The path of each component token it declares, and each it reads (DEC-035 points 1
        # to 3).
        self.tokens = self._declared_tokens(data)
        self.token_reads: set[str] = set()
        self._read(data)
        self._read_runs(data)

    @property
    def drawn(self) -> tuple[str, str] | None:
        """The top and the layout this component draws as that top's own drawing (DEC-009
        point 1): a drawing of a layout that is a page's form, or a top whose one layout is
        the whole top. None for a brand's drawing, and for a component that draws no
        layout, a top whose layouts are its pages' forms among them."""
        if self.draws is not None:
            return None
        if self.layout is not None:
            return (self.use, self.layout)
        return (self.use, self._whole) if self._whole is not None else None

    @property
    def shown(self) -> set[str]:
        """The fields a part of it shows, or passes on to a component it places: the fields
        it takes (DEC-009 point 6)."""
        found: set[str] = set()
        for part in self.parts.values():
            found |= part.passes | ({part.shows} if part.shows else set())
        return found

    def field_breaks(self) -> list[tuple[str, str]]:
        """Where this drawing of a layout breaks the rule that names what shows a field
        after the field (DEC-034 point 5), each as a key path and why: a part named after a
        field that does not show it, and a field it shows, or passes on, that no part named
        after it shows. A field is a slot of the layout, or another field of the top."""
        found = []
        for name, part in self.parts.items():
            if name in self.fields and part.shows != name:
                found.append(
                    (
                        f"parts.{name}",
                        f"the part `{name}` is named after the field `{name}`, and does not "
                        "show it: a part named after a field shows that field",
                    )
                )
        directly = {part.shows for part in self.parts.values() if part.shows}
        for name in sorted((self.shown & set(self.fields)) - set(self.parts)):
            how = (
                "shows `{0}` by no part named after it"
                if name in directly
                else "passes `{0}` on to a component it places, and shows it no other way"
            ).format(name)
            found.append(
                (
                    "parts",
                    f"{how}: a part at its top level named `{name}` shows it, so it keeps one "
                    "trace id under every drawing",
                )
            )
        return found

    def takes_word(self, option: str, word: str) -> bool:
        """Whether this brand's drawing takes the word `word` of the option `option`: a
        switch or a `when` of it reads the word, and no switch on the option leaves it out
        (DEC-009 point 6)."""
        return word in self.option_reads.get(option, ()) and word not in self.switch_gaps.get(
            option, {}
        )

    def run_words(self, name: str) -> tuple[str, ...]:
        """The words of the field of runs `name` this brand's drawing takes (DEC-012 point
        2): those a text part that shows the field chooses by, each a switch on it leaves
        out but; the first alone where none chooses by them; and none where a part passes
        the field on, so it then takes only text."""
        words = self.runs.get(name, ())
        if name in self.runs_passed:
            return ()
        if name not in self.chosen_by:
            return words[:1]
        gaps = self.switch_gaps.get(name, {})
        return tuple(word for word in words if word not in gaps)

    def untaken(self) -> list[tuple[str, str]]:
        """What this brand's drawing does not take of what its top declares, each as the
        key path in its file that it lies at and what it is, in words (DEC-009 points 5 and
        9, DEC-012 points 2 and 8): a field no part shows or passes on, at `parts`; a word of
        an option it does not take (`takes_word`), at the first switch that leaves it out,
        else at `parts`; a field of runs it passes on, at the part that does; a word of a
        field of runs it does not take (`run_words`), at the first switch that leaves it
        out, else at `parts`; and a part its top exposes that it does not, at `exposes`. It
        takes every state, since a state gives its colour by the top's states. An instance
        that gives what it does not take is drawn by the top's own drawing
        (`Instance.misfit`). Nothing, for any other component."""
        if self.draws is None:
            return []
        found: list[tuple[str, str]] = []
        shown = self.shown
        for name in self.fields:
            if name not in shown:
                found.append(("parts", f"the field `{name}`"))
        for name, option in self.options.items():
            gaps = self.switch_gaps.get(name, {})
            for word in option.words:
                if not self.takes_word(name, word):
                    what = f"the word `{word}` of the option `{name}`"
                    found.append((gaps.get(word, "parts"), what))
        for name, words in self.runs.items():
            if name not in shown:
                continue
            if name in self.runs_passed:
                found.append(
                    (self.runs_passed[name], f"the runs of `{name}`, since it passes them on")
                )
                continue
            gaps, taken = self.switch_gaps.get(name, {}), self.run_words(name)
            for word in words:
                if word not in taken:
                    where = gaps.get(word, "parts")
                    found.append((where, f"the word `{word}` of the runs of `{name}`"))
        for name in self.top_exposes:
            if name not in self.exposes:
                found.append(("exposes", f"the exposed part `{name}`"))
        return found

    def drawn_data(
        self, layout: str, own: Mapping[str, Any]
    ) -> tuple[dict[str, Any], list[tuple[str, str, str]]] | None:
        """What a brand's drawing of this top's layout `layout` is read as, given what its
        file holds of its own, `own` (`DRAWING_KEYS`), with each finding on a size it writes
        (DEC-034 points 1 and 2); None where this top declares no such layout.

        It takes the top's fields, options, states and colour, and the layout's slots and
        lists, as the top's own drawing does, and holds its own parts, values, exposed
        parts and tokens. Of a layout that is a page's form, it says its page's height
        alone, and says it where the top asks for none, by a formula or through its physical
        size. Of a top whose one layout is the whole top, its `preferred` is its own, whole,
        but for a height the top's physical size sets (DEC-034 point 3): such a height is a
        finding, and is not read."""
        if self.forms:
            page = self._page_data(layout)
            if page is None:
                return None
            sizes: list[tuple[str, str, str]] = []
            preferred = own.get("preferred")
            if isinstance(preferred, Mapping) and "width" in preferred:
                sizes.append(
                    (
                        DRAWING_SIZE,
                        "preferred.width",
                        f"draws `{layout}`, a page's form, and writes a width: a page gets its "
                        "top's width, so a drawing writes its page's height alone",
                    )
                )
            says = isinstance(preferred, Mapping) and "height" in preferred
            if not self.asks_for("height") and not says:
                sizes.append(
                    (
                        DRAWING_SIZE,
                        "preferred",
                        f"the top asks for no height, so a drawing of `{layout}` writes its "
                        "page's height under `preferred`, by a formula on its parts",
                    )
                )
            data = {
                **{
                    key: self.data[key]
                    for key in ("options", "states", "colour")
                    if key in self.data
                },
                **page,
                **{key: value for key, value in own.items() if key != "preferred"},
            }
            if isinstance(preferred, Mapping):
                data["preferred"] = {s: f for s, f in preferred.items() if s != "width"}
            return data, sizes
        if layout != self._whole:
            return None
        kept = {key: value for key, value in self.data.items() if key not in DRAWING_KEYS}
        preferred = own.get("preferred")
        writes_height = isinstance(preferred, Mapping) and "height" in preferred
        if self.physical_size is None or not writes_height:
            return {**kept, **own}, []
        height = (
            DRAWING_SIZE,
            "preferred.height",
            f"draws `{layout}`, and writes a height, which its top's physical size sets: the "
            "engine sets it from the width the drawing asks for, in the size's proportion",
        )
        unread = {s: f for s, f in preferred.items() if s != "height"}
        return {**kept, **own, "preferred": unread}, [height]

    def _page_data(self, layout: str) -> dict[str, Any] | None:
        """What a drawing of the layout `layout`, a page's form, takes of what its top
        declares: as its fields, the layout's slots and the top's other fields; and the
        fields of each list among its slots that it repeats over (DEC-009 point 5, DEC-011
        point 5). None where the top declares no such layout."""
        forms = page_forms(self.data)
        if forms is None or layout not in forms.layouts:
            return None
        slots, _ = forms.layouts[layout]
        others = {name: s for name, s in self.fields.items() if name not in forms.fields}
        fields = {
            **others,
            **{
                slot: {k: v for k, v in s.items() if k != PAGES} if isinstance(s, Mapping) else s
                for slot, s in slots.items()
            },
        }
        decl = self.data["layouts"][layout]
        lists = {"lists": decl["lists"]} if isinstance(decl, Mapping) and "lists" in decl else {}
        return {"fields": {"type": "object", "properties": fields}, **lists}

    def _declared_tokens(self, data: Mapping[str, Any]) -> frozenset[str]:
        """The path of each component token the component declares, by the names `tokens`
        maps, whatever their declarations, which the scope judges (DEC-035 points 1 and
        2). A piece's own component declares none, so its `tokens` is a finding and
        declares nothing (DEC-035 point 5)."""
        declared = data.get(TOKENS)
        if declared is None:
            return frozenset()
        library, _, name = self.use.partition("/")
        if library == names.PIECE:
            self._issue(
                TOKEN_LOCAL,
                TOKENS,
                "declares component tokens, and a piece's own component declares none: no "
                "brand reaches it, so its part reads the role the token would alias",
            )
            return frozenset()
        if not isinstance(declared, Mapping):
            return frozenset()
        return frozenset(f"{names.COMPONENT}.{library}.{name}.{token}" for token in declared)

    def _physical_size(self, data: Mapping[str, Any]) -> tuple[float, float] | None:
        """The trim width and height, in millimetres, at which the component's pages print,
        as it declares them under `physical-size` (DEC-034 point 3). None where it declares
        none, or a value that is not two positive numbers, which is a finding. Whether the
        component may declare one is judged once its layouts are read
        (`_read_physical_size`)."""
        declared = data.get(PHYSICAL_SIZE)
        if declared is None:
            return None
        if isinstance(declared, Mapping) and set(declared) == {"width", "height"}:
            width, height = declared["width"], declared["height"]
            if _positive(width) and _positive(height):
                return width, height
        self._issue(
            PHYSICAL_SIZE,
            PHYSICAL_SIZE,
            f"`{PHYSICAL_SIZE}` takes `{{width: <mm>, height: <mm>}}`, each a positive number",
        )
        return None

    def asks_for(self, size: str) -> bool:
        """Whether the component asks for `size`: by a formula under `preferred`, or its
        height through its physical size, whose proportion the engine sets it by (DEC-034
        point 3)."""
        return size in self.preferred or (size == "height" and self.physical_size is not None)

    @property
    def unread_tokens(self) -> list[str]:
        """The path of each component token the component declares that its file reads
        nowhere, a top's drawings of its layouts included (DEC-035 point 9)."""
        reads = set(self.token_reads)
        for drawing in self.drawings.values():
            reads |= drawing.token_reads
        return sorted(self.tokens - reads)

    def _read_role(self, where: str, path: Any) -> None:
        """Notes a role the component reads at the key path `where`. A component token is
        read only by the component that declares it (DEC-035 point 3)."""
        if not isinstance(path, str) or path.split(".")[0] != names.COMPONENT:
            return
        self.token_reads.add(path)
        top = self.draws[0].replace("/", ".") if self.draws is not None else None
        if (
            path not in self.tokens
            and top is not None
            and path.startswith(f"{names.COMPONENT}.{top}.")
        ):
            self._issue(
                TOKEN_UNDECLARED,
                where,
                f"reads `{path}`, a component token of the top it draws: a drawing reads none "
                "of its top's tokens, and gives what it draws its own",
            )
        elif path not in self.tokens:
            self._issue(
                TOKEN_UNDECLARED,
                where,
                f"reads `{path}`, a component token it does not declare: only the component "
                "that declares a token reads it",
            )

    def ties(self, part: Part) -> ListFields | None:
        """What the component declares for the list of ties `part` repeats over; None where
        the part repeats over no list of ties."""
        listed = part.spec.get("repeat") if part.kind == "repeat" else None
        declared = self.list_fields.get(listed) if isinstance(listed, str) else None
        return declared if declared is not None and declared.ends is not None else None

    def _issue(self, code: str, where: str, message: str) -> None:
        self.issues.append((code, where, f"{self.use}: {message}"))

    def _shape(self, where: str, message: str) -> None:
        self._issue("component-shape", where, message)

    def _mapping(self, data: Mapping[str, Any], key: str) -> Mapping[str, Any]:
        value = data.get(key)
        if value is None:
            return {}
        if not isinstance(value, Mapping):
            self._shape(key, f"`{key}` is not a mapping")
            return {}
        return value

    def _read(self, data: Mapping[str, Any]) -> None:
        for key in data:
            if key not in COMPONENT_KEYS:
                self._shape(str(key), f"takes no key `{key}`")
        if "ends" in data and data["ends"] is not True:
            self._shape("ends", "`ends` takes `true`, where the component takes ends")
        self._read_options(self._mapping(data, "options"))
        for name in ENDS:
            if self.takes_ends and name in self.options:
                self._shape(
                    f"options.{name}",
                    f"takes ends, and declares an option `{name}`, the name a formula reads "
                    "one of its ends by",
                )
        for state, decl in self._mapping(data, "states").items():
            self.states[state] = decl.get("colour") if isinstance(decl, Mapping) else None
        for name, spec in self._mapping(data, "parts").items():
            self._read_kind(name, spec)
        # What it declares for each list it repeats, known before any `repeat` part is
        # read, which may share its line by the list's weight (DEC-010).
        self.list_fields: dict[str, ListFields] = list_fields(data)
        # The lists it declares end fields for, of whatever shape: a part over one lays
        # nothing along a line, though its `ends` are refused.
        lists = data.get("lists")
        self._tie_lists = {
            name
            for name, decl in (lists if isinstance(lists, Mapping) else {}).items()
            if isinstance(decl, Mapping) and "ends" in decl
        }
        self._read_lists(data)
        for name, value in self.values.items():
            if name in self.parts:
                self._shape(f"values.{name}", f"names `{name}` both a value and a part")
            self._number(f"values.{name}", value, None)
        for size, value in self.preferred.items():
            if size in ("width", "height"):
                self._number(f"preferred.{size}", value, fm.LENGTH)
            else:
                self._shape(f"preferred.{size}", f"asks for no size `{size}`")
        for part in self.parts.values():
            self._read_part(part)
        for name in self.exposes:
            if name not in self.parts:
                self._shape("exposes", f"exposes `{name}`, which is no part of it")
        for option in self.options.values():
            if option.items is not None and not self.repeats_over.get(option.items):
                self._shape(
                    f"options.{option.name}",
                    f"the option `{option.name}` names an item of `{option.items}`, "
                    "over which not exactly one part repeats",
                )
        self._read_size_repeats()
        if self.top:
            self._read_layouts(data)
        elif any(isinstance(s, Mapping) and PAGES in s for s in self.fields.values()):
            self._shape("fields", f"marks a field `{PAGES}`, and declares no layouts")
        self._read_physical_size(data)

    def _read_physical_size(self, data: Mapping[str, Any]) -> None:
        """Whether the component may declare its physical size (DEC-034 point 3): a page
        alone, or a top whose layouts are its pages' forms, may. A top whose slot holds pages
        gives each page its size by the parts that place it, and no other component prints
        at one, so their physical size is a finding, and the engine reads none. A brand's
        drawing declares none either (`Context._drawing`): one of a page alone is read with
        its top's, and prints at it. A top that declares one asks for its height through it,
        so a height under its `preferred` is a finding too."""
        if PHYSICAL_SIZE not in data:
            return
        if not self.top or self.pages:
            what = "a top whose slot holds pages" if self.top else "no top component"
            self._issue(
                PHYSICAL_SIZE,
                PHYSICAL_SIZE,
                f"declares a physical size, and is {what}: only a page alone, or a top whose "
                "layouts are its pages' forms, prints at one",
            )
            self.physical_size = None
        elif "height" in self.preferred:
            self._issue(
                PHYSICAL_SIZE,
                "preferred.height",
                "declares a physical size, and asks for a height by a formula: the engine sets "
                "its height from the width it asks for, in the physical size's proportion",
            )

    def _read_options(self, options: Mapping[str, Any]) -> None:
        for name, decl in options.items():
            where = f"options.{name}"
            if name in self.fields or name in names.RESERVED_PLACING_KEYS:
                self._shape(where, f"`{name}` is an option and a field or a reserved key")
            if isinstance(decl, list) and decl and all(names.is_name(word) for word in decl):
                if SWITCH in decl or len(set(decl)) != len(decl):
                    self._shape(where, f"the option `{name}` repeats a word or takes `{SWITCH}`")
                self.options[name] = Option(name, words=tuple(decl))
            elif isinstance(decl, Mapping) and "item" in decl and set(decl) <= {"item", "point"}:
                if not _is_field(decl["item"], self.lists):
                    self._shape(where, f"the option `{name}` names no list field `{decl['item']}`")
                if decl.get("point", True) is not True:
                    self._shape(where, f"the option `{name}` takes `point: true` or no point")
                self.options[name] = Option(name, items=decl["item"], point="point" in decl)
            else:
                self._shape(where, f"the option `{name}` is neither words nor an item of a list")

    def _read_kind(self, name: str, spec: Any) -> None:
        where = f"parts.{name}"
        if not names.is_name(name):
            self._shape(where, f"`{name}` is not a name")
            return
        kinds = [kind for kind in KINDS if isinstance(spec, Mapping) and kind in spec]
        if len(kinds) != 1:
            self._shape(where, f"the part `{name}` is not exactly one of {', '.join(KINDS)}")
            return
        self.parts[name] = Part(name, kinds[0], spec)
        # Every list's repeat is known before any formula is read, so a formula may read an
        # item option whose list a later part repeats over.
        listed = spec.get("repeat")
        if kinds[0] == "repeat" and _is_field(listed, self.lists):
            # Where two parts repeat over a list, no option names its items.
            self.repeats_over[listed] = "" if listed in self.repeats_over else name

    def _read_part(self, part: Part) -> None:
        where = f"parts.{part.name}"
        kind, spec = part.kind, part.spec
        for key in spec:
            if key == "height" and kind == "text":
                self._issue(
                    "two-owners",
                    f"{where}.height",
                    f"the height of the text `{part.name}` has two owners: the part gives "
                    "it, and its measured text sets it",
                )
            elif key not in (kind, "when", *PART_KEYS[kind]):
                self._shape(f"{where}.{key}", f"the {kind} `{part.name}` takes no `{key}`")
        connects = kind == "line" and "connect" in spec
        for key in REQUIRED.get(kind, ()):
            if key not in spec and not connects:
                self._shape(where, f"the {kind} `{part.name}` needs `{key}`")
        if connects:
            self._read_connect(part)
        if "when" in spec:
            self._read_when(f"{where}.when", spec["when"])
        for key in GEOMETRY:
            if key in spec and key in PART_KEYS[kind]:
                self._number(f"{where}.{key}", spec[key], fm.LENGTH)
        if kind in PRIMITIVES:
            self._read_properties(part)
        elif kind == "use":
            self._read_use(part)
        elif kind == "slot" and not _is_field(spec["slot"], self.fields):
            self._shape(f"{where}.slot", f"the slot `{part.name}` names no field `{spec['slot']}`")
        elif kind == "slot" and spec["slot"] in self.runs:
            self._shape(
                f"{where}.slot",
                f"the slot `{part.name}` places the field of runs `{spec['slot']}`, which only a "
                "text part shows",
            )
        elif kind == "repeat":
            self._read_repeat(part)

    def _read_connect(self, part: Part) -> None:
        """A line that connects the component's two ends, straight or with corners, the
        connector tool (DEC-005 point 2, DEC-011 point 1): only in a component that takes
        ends, and with none of a line's own ends, which the connector sets."""
        where = f"parts.{part.name}"
        if not self._declares_ends:
            self._shape(
                f"{where}.connect",
                f"the line `{part.name}` connects the component's ends, and it takes none: "
                "declare `ends: true`",
            )
        given = [key for key in ENDS_OF_LINE if key in part.spec]
        if given:
            self._shape(
                f"{where}.{given[0]}",
                f"the line `{part.name}` connects its component's ends, so it gives no "
                f"`{given[0]}`: the connector sets its ends",
            )
        self._switched(f"{where}.connect", part.spec["connect"], self._words(WORDS["connect"]))

    def _read_properties(self, part: Part) -> None:
        where = f"parts.{part.name}.{part.kind}"
        raw = part.spec[part.kind]
        if raw is not None and not isinstance(raw, Mapping):
            self._shape(where, f"the {part.kind} `{part.name}` holds no mapping of properties")
            return
        for key in REQUIRED_PROPERTIES.get(part.kind, ()):
            if key not in part.props:
                self._shape(where, f"the {part.kind} `{part.name}` needs `{key}`")
        if part.kind == "text" and ("content" in part.props) == ("fact" in part.props):
            self._shape(where, f"the text `{part.name}` names one of `content` and `fact`")
        if part.kind == "image" and sum(key in part.props for key in IMAGE_SOURCES) != 1:
            sources = ", ".join(f"`{source}`" for source in IMAGE_SOURCES)
            self._shape(where, f"the image `{part.name}` names exactly one of {sources}")
        # A text part that shows a field of runs may choose its role and paint by the
        # field's run styles (DEC-012 point 2), and each run's sign and ground (DEC-036
        # point 3).
        shown = part.props.get("content") if part.kind == "text" else None
        runs = shown if isinstance(shown, str) and shown in self.runs else None
        for key, value in part.props.items():
            at = f"{where}.{key}"
            if key not in PROPERTIES[part.kind]:
                self._shape(at, f"the {part.kind} `{part.name}` takes no property `{key}`")
            elif key in RUN_MARKS:
                self._read_run_mark(part, key, value, runs)
            elif key in PAINTS:
                self._switched(at, value, self._paint, nothing=True, runs=runs)
            elif key in LENGTHS:
                self._number(at, value, fm.LENGTH)
            elif key in WORDS:
                self._switched(at, value, self._words(WORDS[key]))
            elif key == "style":
                self._switched(at, value, self._role, runs=runs)
            elif key == "fact":
                if value not in FACTS:
                    self._shape(at, f"`fact` takes {', '.join(FACTS)}, and no `{value}`")
            elif key == "file":
                continue  # a picture file's bare name, judged where it is drawn
            elif key == "role":
                self._role(at, value)  # a picture role, judged where it is drawn
            elif not _is_field(value, self.fields):  # content, produced
                self._shape(at, f"`{key}` names no field `{value}`")
            elif part.kind == "image" and value in self.runs:
                self._shape(
                    at,
                    f"the image `{part.name}` names the field of runs `{value}`, which only a "
                    "text part shows",
                )

    def _read_run_mark(self, part: Part, key: str, value: Any, runs: str | None) -> None:
        """A text part's choice of each run's sign, `true` or `false`, or of its ground, a
        paint or none (DEC-036 point 3). Only a text part that shows a field of runs makes
        either, and each reads its lengths from roles the foundations declare."""
        at = f"parts.{part.name}.text.{key}"
        if runs is None:
            self._shape(
                at,
                f"the text `{part.name}` chooses a run's {key}, and shows no field of runs",
            )
            return
        if key == "sign":
            self._switched(at, value, self._yes_or_no, runs=runs)
        else:
            self._switched(at, value, self._paint, nothing=True, runs=runs)
        for role in MARK_ROLES[key]:
            dimension, problem = self._ctx.role_dimension(role)
            if problem is None and dimension != fm.LENGTH:
                problem = "takes a number, not a length"
            if problem is not None and role not in self._roles_reported:
                self._roles_reported.add(role)
                code = "unknown-role" if "no value" in problem else "role-type"
                self._issue(code, at, f"a run's {key}, reading `@{role}`, {problem}")

    def _yes_or_no(self, where: str, value: Any) -> None:
        if not isinstance(value, bool):
            self._shape(where, f"`{value}` is neither `true` nor `false`")

    def _read_use(self, part: Part) -> None:
        where = f"parts.{part.name}"
        if not _is_use(part.spec["use"]):
            self._shape(f"{where}.use", f"`{part.spec['use']}` is not `<library>/<component>`")
        bound = part.spec.get("fields") or {}
        if not isinstance(bound, Mapping):
            self._shape(f"{where}.fields", "`fields` is not a mapping")
        else:
            for theirs, ours in bound.items():
                if not _is_field(ours, self.fields):
                    self._shape(f"{where}.fields.{theirs}", f"passes no field `{ours}` of its own")
                elif ours in self.runs and self.draws is not None:
                    # A brand's drawing that passes it on takes none of its runs, which asks
                    # the brand's owner for attention (DEC-012 points 2 and 8).
                    self.runs_passed.setdefault(ours, f"{where}.fields.{theirs}")
                elif ours in self.runs:
                    self._shape(
                        f"{where}.fields.{theirs}",
                        f"passes the field of runs `{ours}` on to a component it places, which "
                        "no part does for now: only a text part of its own shows it",
                    )
        chosen = part.spec.get("options") or {}
        if not isinstance(chosen, Mapping):
            self._shape(f"{where}.options", "`options` is not a mapping")
        else:
            for theirs, word in chosen.items():
                self._switched(f"{where}.options.{theirs}", word, self._words(None))

    def _read_repeat(self, part: Part) -> None:
        where = f"parts.{part.name}"
        listed = part.spec["repeat"]
        if not _is_field(listed, self.lists):
            self._shape(f"{where}.repeat", f"repeats over `{listed}`, which is no list field")
        if "draw" in part.spec and not _is_use(part.spec["draw"]):
            self._shape(f"{where}.draw", f"`{part.spec['draw']}` is not `<library>/<component>`")
        operators = [name for name in OPERATORS if name in part.spec]
        if isinstance(listed, str) and listed in self._tie_lists:
            for name in operators:
                self._shape(
                    f"{where}.{name}",
                    f"the list `{part.name}` repeats over the ties of `{listed}`, each drawn "
                    "between its ends, so it lays nothing along a row or a column",
                )
            return
        if len(operators) != 1:
            self._shape(where, f"the list `{part.name}` takes one of `row` and `column`")
            return
        settings = part.spec[operators[0]] or {}
        if not isinstance(settings, Mapping):
            self._shape(f"{where}.{operators[0]}", "the operator holds no mapping")
            return
        for key, value in settings.items():
            at = f"{where}.{operators[0]}.{key}"
            if key == "gap":
                self._number(at, value, fm.LENGTH)
            elif key in OPERATOR_WORDS:
                self._switched(at, value, self._words(WORDS[key]))
            else:
                self._shape(at, f"`{operators[0]}` takes no `{key}`")
        declared = self.list_fields.get(listed) if isinstance(listed, str) else None
        if "shares" in _leaves(settings.get("sizes")) and (declared is None or not declared.weight):
            self._shape(
                f"{where}.{operators[0]}.sizes",
                f"shares the line by the weight of `{listed}`, and declares no weight for it "
                "under `lists`",
            )

    def _read_lists(self, data: Mapping[str, Any]) -> None:
        """What the component declares under `lists` (DEC-010 points 1 to 4, and 9, DEC-011
        points 1 and 8). Each entry is for a list field that a `repeat` part of its own
        repeats over, never the field that holds a top's pages. Its component field is a
        field of its own that holds no list and takes no runs, and that no part places or
        passes on. Each arrangement field is a name and no reserved key's, with its words,
        each once, and, for a weight, a share above zero for each word. A list takes one
        weight at most. A list of ties declares two end fields (`ends_problem`)."""
        for listed, decl in self._mapping(data, "lists").items():
            where = f"lists.{listed}"
            schema = self.fields.get(listed)
            if isinstance(schema, Mapping) and schema.get(PAGES) is True:
                self._shape(
                    where,
                    f"declares fields for `{listed}`, the list of its pages: a page's content is "
                    "its layout's or its component's, so the list takes no component field, "
                    "no arrangement field and no end field",
                )
                continue
            if listed not in self.repeats_over:
                self._shape(
                    where, f"declares fields for `{listed}`, over which no part of it repeats"
                )
            if not isinstance(decl, Mapping):
                self._shape(
                    where,
                    f"`{listed}` holds no mapping of `component`, `arrangement` and `ends`",
                )
                continue
            for key in decl:
                if key not in LIST_KEYS:
                    self._shape(f"{where}.{key}", f"the entry of `{listed}` takes no `{key}`")
            if "component" in decl:
                self._read_component_field(f"{where}.component", listed, decl["component"])
            arrangement = decl.get("arrangement", {})
            if "ends" in decl:
                words = arrangement if isinstance(arrangement, Mapping) else {}
                problem = ends_problem(decl["ends"], [str(name) for name in words])
                if problem is not None:
                    self._shape(f"{where}.ends", f"the end fields of `{listed}`: `ends` {problem}")
            if not isinstance(arrangement, Mapping):
                self._shape(f"{where}.arrangement", "`arrangement` is not a mapping")
                continue
            weights = [
                name
                for name, each in arrangement.items()
                if self._read_arrangement(f"{where}.arrangement.{name}", name, each)
                and "shares" in each
            ]
            for name in weights[1:]:
                self._shape(
                    f"{where}.arrangement.{name}",
                    f"`{listed}` has the weight `{weights[0]}` already: an item takes one share "
                    "of its line",
                )

    def _read_component_field(self, where: str, listed: str, name: Any) -> None:
        """A list's component field: a field of the component's own that holds no list,
        which no part places or passes on, since it places nothing (DEC-010 point 1)."""
        if not _is_field(name, self.fields):
            self._shape(where, f"the component field of `{listed}` names no field `{name}`")
            return
        if name in self.lists:
            self._shape(
                where,
                f"the component field `{name}` is a list field: it holds one mapping, which "
                "names a component",
            )
        if name in self.runs:
            self._shape(
                where,
                f"the component field `{name}` is a field of runs: it holds one mapping, which "
                "names a component, never runs",
            )
        for part in self.parts.values():
            bound = part.spec.get("fields") if part.kind == "use" else None
            if part.kind == "slot" and part.spec.get("slot") == name:
                done = "places"
            elif isinstance(bound, Mapping) and name in bound.values():
                done = "passes on"
            else:
                continue
            self._shape(
                where,
                f"the part `{part.name}` {done} the component field `{name}`, which places "
                f"nothing: it names the component of each item of `{listed}`",
            )

    def _read_arrangement(self, where: str, name: Any, decl: Any) -> bool:
        """An arrangement field of a list (DEC-010 points 2 to 4): a name and no reserved
        key's, which takes one of its `words`, the first the default; a weight also gives
        `shares`, a number above zero for each word and no other. True where its words
        may be read."""
        if not names.is_name(name) or name in names.RESERVED_PLACING_KEYS:
            self._shape(where, f"the arrangement field `{name}` is no name, or a reserved key's")
            return False
        if not isinstance(decl, Mapping):
            self._shape(where, f"the arrangement field `{name}` holds no mapping of `words`")
            return False
        for key in decl:
            if key not in ARRANGEMENT_KEYS:
                self._shape(f"{where}.{key}", f"an arrangement field takes no `{key}`")
        problem = _words_problem(decl.get("words"))
        if problem is not None:
            self._shape(f"{where}.words", f"the arrangement field `{name}` {problem}")
            return False
        if "shares" in decl and _shares(decl["words"], decl) is None:
            self._shape(
                f"{where}.shares",
                f"the weight `{name}` gives each of its words a share above zero, and names no "
                "other word",
            )
        return True

    def _read_when(self, where: str, when: Any, *, by: str = "") -> None:
        """A part's `when`: a field, an option's words, or a switch by a size, or by `:as`,
        whose each branch is `true`, `false` or one of those, never a switch again (DEC-021
        point 3, DEC-034 point 7). Given `by`, the marked name of such a switch, it reads
        one of its branches."""
        if _by_marked(when) and not by:
            for value in self._marked_branches(where, when, "`when` switches"):
                if not isinstance(when[value], bool):
                    self._read_when(f"{where}.{value}", when[value], by=str(when[SWITCH]))
            return
        if isinstance(when, str):
            if when not in self.fields:
                self._shape(where, f"`when` names no field `{when}`")
            return
        if isinstance(when, Mapping) and len(when) == 1:
            ((name, words),) = when.items()
            option = self.options.get(name)
            listed = words if isinstance(words, list) else [words]
            if option is None or not option.words:
                self._shape(where, f"`when` names no option of words `{name}`")
            elif not all(word in option.words for word in listed):
                self._shape(where, f"`when` names a word the option `{name}` lacks")
            else:
                self.option_reads.setdefault(name, set()).update(listed)
            return
        if by:
            self._shape(
                where,
                f"a branch of a `when` by {'`:as`' if by == AS else 'a size'} takes `true`, "
                "`false`, a field, or `{<option>: [<word>, ...]}`",
            )
            return
        self._shape(
            where,
            "`when` takes a field, `{<option>: [<word>, ...]}`, or a switch on a size, "
            "`{by: :<axis>, <mode>: ...}`",
        )

    def _read_size_repeats(self) -> None:
        """Two parts or more that repeat over one list, a `when` by a size among theirs: at
        each combination of the modes of the axes those read, exactly one of them may be
        drawn, so each item is drawn once at every size (DEC-021 points 4, 5 and 7). Every
        part over the list counts, whatever its `when` (`_may_draw`). The finding lies at the
        first `when` by a size. One that reads no size axis is reported already."""
        over: dict[str, list[Part]] = {}
        for part in self.parts.values():
            listed = part.spec.get("repeat")
            if part.kind == "repeat" and isinstance(listed, str):
                over.setdefault(listed, []).append(part)
        known = self._ctx.sizes.axes
        for listed, parts in over.items():
            sized = [part for part in parts if _by_size(part.spec.get("when"))]
            read = sorted({str(part.spec["when"][SWITCH])[len(MARKED) :] for part in sized})
            if len(parts) < 2 or not sized or any(axis not in known for axis in read):
                continue
            for modes in itertools.product(*(known[axis].modes for axis in read)):
                at = dict(zip(read, modes, strict=True))
                drawn = [part for part in parts if _may_draw(part.spec.get("when"), at, known)]
                if len(drawn) == 1:
                    continue
                shown = " and ".join(f"`{mode}` of `{axis}`" for axis, mode in at.items())
                self._issue(
                    SIZE_REPEAT,
                    f"parts.{sized[0].name}.when",
                    f"the parts {', '.join(f'`{p.name}`' for p in parts)} repeat over "
                    f"`{listed}`, and at {shown} {len(drawn)} of them may be drawn: exactly "
                    "one may be drawn at each mode, so each item is drawn once",
                )
                break

    def _read_layouts(self, data: Mapping[str, Any]) -> None:
        layouts = data.get("layouts")
        forms = page_forms(data)
        if forms is not None:
            self._read_forms(data, forms)
            return
        if not isinstance(layouts, Mapping) or len(layouts) != 1:
            self._shape(
                "layouts",
                "a top component declares one layout, unless its layouts are its pages' "
                "forms, each with its own drawing",
            )
            return
        self._whole = str(next(iter(layouts)))
        pages = set()
        for layout, decl in layouts.items():
            slots = decl.get("slots") if isinstance(decl, Mapping) else None
            if isinstance(decl, Mapping) and "preferred" in decl:
                self._shape(
                    f"layouts.{layout}.preferred",
                    f"the layout `{layout}` says its page's height, as only a layout that is "
                    "a page's form does: this top's own `preferred` says the size it asks for",
                )
            if not isinstance(slots, Mapping):
                self._shape(f"layouts.{layout}", f"the layout `{layout}` declares no slots")
                continue
            for slot, slot_decl in slots.items():
                if slot not in self.fields:
                    self._shape(f"layouts.{layout}.slots.{slot}", f"the slot `{slot}` is no field")
                if isinstance(slot_decl, Mapping) and slot_decl.get("pages") is True:
                    pages.add(slot)
                if isinstance(slot_decl, Mapping) and RUNS in slot_decl:
                    self._shape(
                        f"layouts.{layout}.slots.{slot}.{RUNS}",
                        f"marks the slot `{slot}` as taking runs: the slot names a field of the "
                        "top, and the field takes the mark",
                    )
        self.pages = frozenset(pages)

    def _read_forms(self, data: Mapping[str, Any], forms: PageForms) -> None:
        """A top whose layouts are its pages' forms (DEC-010 point 5): one list field of its
        own marked as holding its pages, no parts of its own, and for each layout its slots
        and its own drawing (DEC-009 point 1). Each drawing is read as a component of its
        own that draws one page: its fields are the layout's slots and the top's other
        fields, and it shares the top's options, states, colour, values and size (DEC-009
        point 5). What it finds lies in the top's file, its parts' under
        `layouts.<layout>`."""
        self.forms = True
        if len(forms.fields) != 1:
            marked = ", ".join(f"`{name}`" for name in forms.fields) or "none"
            self._shape(
                "fields",
                f"a top whose layouts are its pages' forms marks one field `{PAGES}: true`, "
                f"the list of its pages; it marks {marked}",
            )
        elif forms.fields[0] not in self.lists:
            self._shape(
                f"fields.properties.{forms.fields[0]}",
                f"the field `{forms.fields[0]}` holds pages, and is no list field",
            )
        else:
            self.pages_field = forms.fields[0]
        if self.parts:
            self._shape(
                "parts",
                "a top whose layouts are its pages' forms draws nothing around its pages: "
                "each layout's `parts` draw a whole page",
            )
        # A layout's drawing lies in the top's file, so it reads the top's tokens (DEC-035
        # point 3).
        shared = ("options", "states", "colour", "values", TOKENS)
        others = {name: s for name, s in self.fields.items() if name not in forms.fields}
        layouts = data.get("layouts")
        if not isinstance(layouts, Mapping) or not layouts:
            self._shape("layouts", "a top whose layouts are its pages' forms declares no layouts")
            return
        for layout, decl in layouts.items():
            where = f"layouts.{layout}"
            slots, required = forms.layouts[layout]
            if not isinstance(decl, Mapping) or not isinstance(decl.get("slots"), Mapping):
                self._shape(where, f"the layout `{layout}` declares no slots")
            for slot, schema in slots.items():
                self._read_slot(f"{where}.slots.{slot}", layout, slot, schema)
                if slot in others:
                    self._shape(
                        f"{where}.slots.{slot}",
                        f"the slot `{slot}` is also a field of the top, which the layout's "
                        "drawing takes too",
                    )
            for slot in required:
                if slot not in slots:
                    self._shape(f"{where}.required", f"requires `{slot}`, which is no slot of it")
            parts = decl.get("parts") if isinstance(decl, Mapping) else None
            if not isinstance(parts, Mapping):
                self._shape(
                    where,
                    f"the layout `{layout}` has no drawing of its own: each layout of a top "
                    "whose layouts are its pages' forms draws a page with its `parts`",
                )
                continue
            preferred = self._page_height(where, layout, decl)
            drawing = Component(
                self.use,
                {
                    **{key: data[key] for key in shared if key in data},
                    **(self._page_data(layout) or {}),
                    "parts": parts,
                    **preferred,
                },
                self._ctx,
                layout=layout,
            )
            for code, at, message in drawing.issues:
                own = at.partition(".")[0] in ("parts", "lists", "preferred")
                at = f"{where}.{at}" if own else at
                if (code, at, message) not in self.issues:
                    self.issues.append((code, at, message))
            self.drawings[layout] = drawing

    def _page_height(self, where: str, layout: str, decl: Mapping[str, Any]) -> dict[str, Any]:
        """What a layout that is a page's form asks for its page, as its drawing's
        `preferred` (DEC-022 point 3): its height alone, by a formula on its parts. A width
        is refused, since a page gets the top's width. Where the top asks for no height, by
        a formula or through its physical size (DEC-034 point 3), a layout that says none is
        refused, since its page would get no height."""
        preferred = decl.get("preferred")
        if isinstance(preferred, Mapping) and "width" in preferred:
            self._shape(
                f"{where}.preferred.width",
                f"the layout `{layout}` says a width, and a page gets the top's width: a "
                "layout says its page's height alone",
            )
        says = isinstance(preferred, Mapping) and "height" in preferred
        if not self.asks_for("height") and not says:
            self._shape(
                f"{where}.preferred",
                f"the top asks for no height, so the layout `{layout}` says its page's "
                "height under `preferred`, by a formula on its parts",
            )
        if not isinstance(preferred, Mapping):
            return {} if preferred is None else {"preferred": preferred}
        return {"preferred": {size: f for size, f in preferred.items() if size != "width"}}

    def _read_slot(self, where: str, layout: str, slot: str, schema: Any) -> None:
        """A slot of a layout that is a page's form: a page's field, so no reserved key's
        name nor `layout`, and never a list of pages, which would be a page inside a
        page."""
        if slot == LAYOUT:
            self._shape(
                where,
                f"the layout `{layout}` declares a slot `{LAYOUT}`, the key by which a page "
                "names its layout",
            )
        elif slot in names.RESERVED_PLACING_KEYS:
            self._shape(where, f"the slot `{slot}` takes a reserved key's name")
        if isinstance(schema, Mapping) and (schema.get("pages") is True or PAGES in schema):
            self._shape(
                where,
                f"the slot `{slot}` holds pages in a layout that is a page's form: a page "
                "inside a page",
            )

    # -- fields of runs

    def _read_runs(self, data: Mapping[str, Any]) -> None:
        """The component's fields of runs (DEC-012 points 1, 2 and 8), judged once every
        part and layout is read. Each mark lies directly on one of its fields, or on a slot
        of a layout that is a page's form, never below one, and no `$ref` leads to a
        marked schema. A marked field takes text alone, and declares its words, each a
        name, once. A field of more than one word is one that some text part of the
        component, a top's own drawing included, chooses its role or paint by. A top's own
        drawing of a layout, and a brand's, leave all of this to the top that declares it."""
        if self.layout is not None or self.draws is not None:
            return
        fields = data.get("fields")
        if isinstance(fields, Mapping) and RUNS in fields:
            self._shape(f"fields.{RUNS}", "marks the schema of all its fields as taking runs")
        drawn = set(self.chosen_by)
        for drawing in self.drawings.values():
            drawn |= drawing.chosen_by
        self._read_marks("fields", self.fields, fields, drawn)
        layouts = data.get("layouts") if self.forms else None
        for layout, decl in (layouts if isinstance(layouts, Mapping) else {}).items():
            slots = decl.get("slots") if isinstance(decl, Mapping) else None
            if isinstance(slots, Mapping):
                drawing = self.drawings.get(layout)
                chosen = drawing.chosen_by if drawing is not None else set()
                root = {"type": "object", "properties": slots}
                self._read_marks(f"layouts.{layout}.slots", slots, root, chosen, slots=True)

    def _read_marks(
        self,
        where: str,
        properties: Mapping[str, Any],
        root: Any,
        chosen: set[str],
        *,
        slots: bool = False,
    ) -> None:
        """The marks of fields of runs among `properties`, the fields or a layout's slots
        at `where`, whose `$ref`s lead within `root`; `chosen`, the fields of runs some
        text part chooses by."""
        for name, schema in properties.items():
            at = f"{where}.{name}" if slots else f"{where}.properties.{name}"
            for below in _marks_below(schema, at):
                self._shape(
                    below,
                    f"marks a schema below the field `{name}` as taking runs: only a field "
                    "itself, or a layout's slot, takes runs",
                )
            for path, ref in _refs(schema, at):
                target = _target(ref, root)
                if isinstance(target, Mapping) and RUNS in target:
                    self._shape(
                        path,
                        f"`$ref: {ref}` leads to a field of runs, so another field would take "
                        "runs through it",
                    )
            if not isinstance(schema, Mapping) or RUNS not in schema:
                continue
            problem = run_problem(str(name), schema)
            if problem is not None:
                self._shape(f"{at}.{RUNS}", problem)
            elif len(schema[RUNS]) > 1 and name not in chosen:
                self._shape(
                    f"{at}.{RUNS}",
                    f"the field of runs `{name}` declares {len(schema[RUNS])} words, and no "
                    "text part chooses its role, its paint, a run's sign or its ground by them",
                )

    # -- values, which may switch on an option

    def _switched(
        self,
        where: str,
        value: Any,
        check: Callable[[str, Any], None],
        *,
        nothing: bool = False,
        runs: str | None = None,
    ) -> None:
        """Checks a value, or each branch of its switch; `nothing` lets a branch be null.
        A switch names an option of words, or, where `runs` names the field of runs a text
        part shows, that field's run styles: a text part's role and paint alone choose by
        them (DEC-012 point 2), and its runs' signs and grounds (DEC-036 point 3). It names
        each of their words and no other. In a brand's
        drawing, a word it leaves out is one the drawing does not take, which asks the
        brand's owner for attention and never fails (`switch_gaps`, DEC-009 point 9, DEC-012
        point 8); a word the top does not declare still fails."""
        if not (isinstance(value, Mapping) and SWITCH in value):
            check(where, value)
            return
        by = value[SWITCH]
        if _by_marked(value):
            for branch in self._marked_branches(where, value, "switches"):
                if not (nothing and value[branch] is None):
                    self._switched(
                        f"{where}.{branch}", value[branch], check, nothing=nothing, runs=runs
                    )
            return
        if isinstance(by, str) and by in self.runs:
            if by != runs:
                self._shape(
                    where,
                    f"chooses by the run styles of `{by}`, which only the role, the paint, "
                    f"the sign and the ground of a text part that shows `{by}` choose by",
                )
                return
            self.chosen_by.add(by)
            words, named = self.runs[by], f"the run styles of `{by}`"
        else:
            option = self.options.get(by) if isinstance(by, str) else None
            if option is None or not option.words:
                self._shape(where, f"switches on `{by}`, which is no option of words")
                return
            words, named = option.words, f"`{option.name}`"
            self.option_reads.setdefault(option.name, set()).update(w for w in words if w in value)
        branches = {key for key in value if key != SWITCH}
        if self.draws is not None:
            for word in words:
                if word not in branches:
                    self.switch_gaps.setdefault(str(by), {}).setdefault(word, where)
            others = sorted(map(str, branches - set(words)))
            if others:
                self._shape(
                    where,
                    f"the switch on {named} names {', '.join(others)}, which the top does not "
                    f"declare for it: its words are {', '.join(words)}",
                )
        elif branches != set(words):
            self._shape(
                where,
                f"the switch on {named} names {', '.join(sorted(map(str, branches)))}, not each "
                f"word of it: {', '.join(words)}",
            )
        for word in words:
            if word in value and not (nothing and value[word] is None):
                self._switched(f"{where}.{word}", value[word], check, nothing=nothing, runs=runs)

    def _marked_branches(self, where: str, value: Mapping[str, Any], what: str) -> list[str]:
        """The branches of a switch or a `when` by a marked name that are read in turn: by
        `:as`, those that name its values (`_as_branches`); by a size, those that name its
        axis's modes (`_size_axis`, `_size_branches`). `what` says which it is, in a
        finding."""
        if value[SWITCH] == AS:
            return self._as_branches(where, value, what)
        axis = self._size_axis(where, value[SWITCH], what)
        return self._size_branches(where, value, axis)

    def _as_branches(self, where: str, value: Mapping[str, Any], what: str) -> list[str]:
        """The branches of a switch or a `when` by `:as` that name its values, each read in
        turn (DEC-034 point 7). Only a drawing of a layout reads `:as`, so elsewhere none is
        read. The switch names the default, `page`, which takes `part` where it leaves it
        out, and names no other value. Each break is reported."""
        if not self.draws_layout:
            self._issue(
                AS_SWITCH,
                where,
                f"{what} on `{AS}`, which only a drawing of a layout reads, the top's own or a "
                "brand's: whether its instance is a page or part of one",
            )
            return []
        default = PLACED_AS[0]
        branches = [str(key) for key in value if key != SWITCH]
        if default not in branches:
            self._issue(
                AS_SWITCH,
                where,
                f"the switch on `{AS}` names no branch for `{default}`, its default, which "
                "takes each value it leaves out",
            )
        for branch in branches:
            if branch not in PLACED_AS:
                self._issue(
                    AS_SWITCH,
                    f"{where}.{branch}",
                    f"the switch on `{AS}` names `{branch}`, which is no value of it (its "
                    f"values: {', '.join(PLACED_AS)})",
                )
        return [branch for branch in branches if branch in PLACED_AS]

    def _size_axis(self, where: str, by: str, what: str) -> AxisLike | None:
        """The size axis that the marked name `by`, `:<axis>`, of a switch or a `when` reads
        (DEC-021 point 3); None where it reads none a piece can name, a value axis or a name
        the engine holds included, which is reported."""
        axis = self._ctx.sizes.axes.get(by[len(MARKED) :])
        if axis is None:
            known = ", ".join(f"`{MARKED}{name}`" for name in sorted(self._ctx.sizes.axes))
            self._issue(
                SIZE_SWITCH,
                where,
                f"{what} on `{by}`, which reads no size axis a piece can name (the size axes: "
                f"{known or 'none'})",
            )
        return axis

    def _size_branches(
        self, where: str, value: Mapping[str, Any], axis: AxisLike | None
    ) -> list[str]:
        """The branches of a switch by a size that name a mode of its axis, each read in
        turn. The switch names the axis's default, which takes each mode it leaves out, and
        names no other word (DEC-021 point 3); none where it reads no size axis."""
        if axis is None:
            return []
        by = value[SWITCH]
        branches = [str(key) for key in value if key != SWITCH]
        if axis.default not in branches:
            self._issue(
                SIZE_SWITCH,
                where,
                f"the switch on `{by}` names no branch for `{axis.default}`, the axis's "
                "default, which takes each mode it leaves out",
            )
        for branch in branches:
            if branch not in axis.modes:
                self._issue(
                    SIZE_SWITCH,
                    f"{where}.{branch}",
                    f"the switch on `{by}` names `{branch}`, which is no mode of the axis "
                    f"(its modes: {', '.join(axis.modes)})",
                )
        return [branch for branch in branches if branch in axis.modes]

    def _number(self, where: str, value: Any, expected: int | None) -> None:
        self._switched(where, value, lambda at, text: self._formula(at, text, expected))

    def _paint(self, where: str, value: Any) -> None:
        if isinstance(value, str) and value.startswith(FAMILY):
            if names.is_segment(value[len(FAMILY) :]):
                return
        if not names.is_token_path(value):
            self._shape(where, f"`{value}` is not a role's token path, nor `{FAMILY}<member>`")
            return
        self._read_role(where, value)

    def _role(self, where: str, value: Any) -> None:
        if not names.is_token_path(value):
            self._shape(where, f"`{value}` is not a role's token path")
            return
        self._read_role(where, value)

    def _words(self, words: tuple[str, ...] | None) -> Callable[[str, Any], None]:
        def check(where: str, value: Any) -> None:
            if not names.is_name(value) or (words is not None and value not in words):
                self._shape(
                    where, f"`{value}` is not {'one of ' + ', '.join(words) if words else 'a word'}"
                )

        return check

    # -- formulas

    def _formula(self, where: str, text: Any, expected: int | None) -> None:
        """Reads a formula at its key path and checks it; `formulas` holds it, or `None`."""
        self.formulas[where] = None
        if not fm.is_formula(text):
            self._issue(
                "formula-unreadable", where, f"`{text}` is not a formula, which starts with `=`"
            )
            return
        try:
            formula = fm.parse(text)
        except fm.FormulaError as error:
            self._issue("formula-unreadable", where, str(error))
            return
        for ref in formula.references():
            if isinstance(ref, fm.Role):
                self._read_role(where, ref.path)
        for ref in formula.references():
            problem = self._unreachable(ref)
            if problem:
                self._issue("formula-reach", where, f"the formula `{text}` {problem}")
                return
        try:
            result = fm.dimension(formula, lambda ref: self._dimension(ref, where))
        except fm.FormulaError as error:
            self._issue("formula-dimension", where, str(error))
            return
        if expected is not None and result is not None and result != expected:
            self._issue(
                "formula-dimension",
                where,
                f"the formula `{text}` gives {fm.dimension_name(result)} where "
                f"{fm.dimension_name(expected)} belongs",
            )
            return
        self.formulas[where] = formula

    def _unreachable(self, ref: fm.Reference) -> str | None:
        """Why a formula of this component may not read `ref`, as far as reading the
        component alone tells; the rest is found when the scene is computed."""
        if isinstance(ref, fm.Value):
            return None if ref.name in self.values else f"names no value `{ref.name}`"
        if not isinstance(ref, fm.Path):
            return None
        if ref.option in ENDS and self.takes_ends:
            # An end is the element drawn for its item, which names no part (DEC-011 point 4).
            return f"reads below the end `{{{ref.option}}}`" if ref.steps else None
        if ref.option is not None:
            option = self.options.get(ref.option)
            if option is None or option.items is None:
                return f"reads `{{{ref.option}}}`, which is no option naming an item"
            if not self.repeats_over.get(option.items):
                return (
                    f"reads `{{{ref.option}}}`, an item of `{option.items}`, over which not "
                    "exactly one part repeats"
                )
            return (
                f"reads below the point `{{{ref.option}}}` gives"
                if option.point and ref.steps
                else None
            )
        first = ref.steps[0]
        part = self.parts.get(first.name)
        if part is None:
            return f"reads `{ref}`: there is no part `{first.name}`"
        if first.item is not None and part.kind != "repeat":
            return f"reads `{ref}`: `{first.name}` is no list"
        if part.kind == "repeat" and first.item is None and len(ref.steps) > 1:
            return (
                f"reads `{ref}` with no item of `{first.name}`: name `:first`, `:last` or `[<id>]`"
            )
        if part.kind in ("box", "ellipse", "text", "line", "sign") and len(ref.steps) > 1:
            return f"reads `{ref}`: the {part.kind} `{first.name}` exposes nothing"
        if part.kind == "image" and len(ref.steps) > 2:
            return f"reads `{ref}`: a point has no parts"
        return None

    def _dimension(self, ref: fm.Reference, where: str) -> int | None:
        """The dimension of what `ref`, in the formula at the key path `where`, reads. A
        role it cannot read is reported once, in the component; a library's own role the
        brand leaves with no value is reported where `Context.unvalued_at_lock` places it."""
        if isinstance(ref, fm.Engine):
            return fm.LENGTH if ref.name in ("width", "height") else fm.NUMBER
        if isinstance(ref, fm.Path):
            return fm.LENGTH
        if isinstance(ref, fm.Value):
            return self._value_dimension(ref.name)
        dimension, problem = self._ctx.role_dimension(ref.path)
        if problem and ref.path not in self._roles_reported:
            self._roles_reported.add(ref.path)
            unvalued = self._ctx.unvalued(ref.path)
            if unvalued is not None:
                self._ctx.unvalued_at_lock(unvalued, f"`{self.use}`, at `{where}`,")
                return dimension
            code = (
                "unknown-role"
                if dimension is None and "no value" in problem
                else "formula-dimension"
            )
            self._issue(code, f"@{ref.path}", f"a formula reading `@{ref.path}` {problem}")
        return dimension

    def _value_dimension(self, name: str) -> int | None:
        if name in self._value_dims:
            return self._value_dims[name]
        self._value_dims[name] = None  # a loop of values is reported when one is computed
        found: set[int | None] = set()

        def read(ref: fm.Reference) -> int | None:
            return self._dimension(ref, f"values.{name}")

        def collect(value: Any) -> None:
            if isinstance(value, Mapping) and SWITCH in value:
                for key, branch in value.items():
                    if key != SWITCH:
                        collect(branch)
                return
            try:
                found.add(fm.dimension(fm.parse(value), read))
            except (fm.FormulaError, TypeError, AttributeError):
                found.add(None)

        collect(self.values.get(name))
        if len(found) > 1 and None not in found:
            self._issue(
                "formula-dimension",
                f"values.{name}",
                f"the value `{name}` switches between dimensions",
            )
        self._value_dims[name] = found.pop() if len(found) == 1 else None
        return self._value_dims[name]


def unread_token_findings(component: Component, *, file: str, library: str) -> list[Finding]:
    """A finding for each component token `component` declares that its file reads nowhere
    (DEC-035 point 9), in its file `file` of the library version `library`. A brand's value
    for it is only wasted, so none fails. In an experimental component it asks the
    library's owner for attention, since the component may drop the token at once; in a
    stable or deprecated one it states a fact, since the token stays until the library's
    next major (DEC-035 point 6)."""
    name = component.use.partition("/")[0]
    promised = component.status in PROMISED
    found = []
    for path in component.unread_tokens:
        message = (
            f"`{component.use}` declares the component token `{path}`, and its file reads it "
            "nowhere, so a brand's value for it changes nothing"
        )
        if promised:
            message += f": a {component.status} component keeps it until the library's next major"
        found.append(
            Finding(
                TOKEN_UNREAD,
                STATED if promised else ATTENTION,
                message,
                file=file,
                where=f"{TOKENS}.{path.rpartition('.')[2]}",
                fix="" if promised else "read it where a part draws, or take it out of `tokens`",
                library=library,
                who="" if promised else f"the owner of `{name}`",
            )
        )
    return found


def held_drawing_finding(use: str, *, file: str, library: str) -> Finding:
    """The finding on a component of a library that is no brand that declares `draws`, in
    its file `file` of the version `library` (DEC-034 point 1): only a brand's component
    draws a layout."""
    return Finding(
        DRAWING_SHAPE,
        FAILS,
        f"{use}: declares `draws`, and only a brand's component draws a layout",
        file=file,
        where=DRAWS,
        fix="take `draws` out, or move the drawing into a brand, in a version of its own",
        library=library,
    )


def held_top_drawing_finding(
    use: str, draws: tuple[str, str], holder: str, *, file: str, library: str
) -> Finding:
    """The finding on the brand's drawing `use` whose `draws` names a top that the brand
    `holder`, by its label, holds, in its file `file` of the version `library` (DEC-034
    points 4 and 10): that brand draws each of the top's layouts by the top's own drawing,
    and no brand declares a drawing of it."""
    top, drawn = draws
    return Finding(
        DRAWING_HELD_TOP,
        FAILS,
        f"{use}: draws `{drawn}` of `{top}`, a top the brand {holder} holds: that brand draws "
        "each of its layouts by the top's own drawing, and no brand declares a drawing of it",
        file=file,
        where=DRAWS,
        fix="take the drawing out, in a version of its own",
        library=library,
    )


def own_drawing_findings(component: Component, *, file: str, library: str) -> list[Finding]:
    """A call for attention for each break, in a top's own drawing of a layout, of the rule
    that names what shows a field after the field (`Component.field_breaks`, DEC-034 point
    5), in its file `file` of the version `library`: what the field shows would take
    another trace id under a brand's drawing. It names the top's owner, and never fails,
    since the drawing was accepted before the rule."""
    drawings = [("", component)] if component.drawn is not None else []
    drawings += [(f"layouts.{name}.", each) for name, each in sorted(component.drawings.items())]
    return [
        Finding(
            FIELD_PART,
            ATTENTION,
            f"{component.use}: {why}",
            file=file,
            where=f"{at}{where}",
            fix="name the part that shows each field after the field, in a version of its own",
            who="the top's owner",
            library=library,
        )
        for at, drawing in drawings
        for where, why in drawing.field_breaks()
    ]


# --- one scene's context ------------------------------------------------------------------


@dataclass(frozen=True)
class Facts:
    """What fills the facts of an export in a scene, as the scene shows them: the version's
    number, its date and the piece's state. The fourth fact, the language, is the scene's
    own (DEC-006 point 7, DEC-016 point 5)."""

    version: str
    date: str
    state: str


def stand_ins(state: str) -> Facts:
    """The facts of a scene no export fills: the piece's state as its file holds it, and the
    stand-in for each fact no file holds (DEC-016 point 5)."""
    return Facts(STAND_INS["version"], STAND_INS["date"], state)


class Context:
    """What computing one scene shares: the environment, its language, what fills the facts
    of its export, the size axes a piece can name with the mode of each at the scene's key
    (`Sizes`), the faces, the components read, the findings, and the cells being computed.
    A context that computes no scene takes the stand-ins and no state: what it judges reads
    no text. One given no sizes knows no size axis. Its `choice` says which drawing draws
    each instance of a layout, and `misfits` keeps, by its trace, what each instance a
    brand's drawing drew gives that the drawing does not take (`Instance.misfit`)."""

    def __init__(
        self,
        env: Env,
        language: str,
        facts: Facts | None = None,
        sizes: Sizes | None = None,
        choice: Choice | None = None,
    ) -> None:
        self.env = env
        self.language = language
        self.facts = facts if facts is not None else stand_ins("")
        self.sizes = sizes if sizes is not None else Sizes()
        self.choice = choice if choice is not None else Choice()
        self.misfits: dict[str, str] = {}
        self.faces = Faces(env.font_file)
        self.findings: list[Finding] = []
        self.stack: list[tuple[Instance, tuple[str, ...]]] = []
        self.active: set[tuple[int, tuple[str, ...]]] = set()
        self._seen: set[tuple[str, str, str, str, str]] = set()
        self._components: dict[str, Component | None] = {}
        self._unreadable: set[str] = set()
        self._roles: dict[str, Any] = {}
        self._pictured: dict[str, Picture | None | Exception] = {}
        self._families: dict[str, Mapping[str, str] | None] = {}
        self._concepts: dict[str, str | UnknownConcept | None] = {}
        self._signs: dict[str, Outline | None] = {}

    def fact(self, word: str) -> str:
        """The text of the fact `word`, one of `FACTS`."""
        return self.language if word == "language" else getattr(self.facts, word)

    def size_branch(self, switch: Mapping[str, Any]) -> str | None:
        """The branch a switch by a size takes in this scene (DEC-021 point 3): the mode the
        scene's key holds on its axis, where the switch names it, else the axis's default.
        None where it reads no size axis, which was reported when its component was read."""
        axis = str(switch[SWITCH])[len(MARKED) :]
        if axis not in self.sizes.axes:
            return None
        mode = self.sizes.mode(axis)
        return mode if mode in switch else self.sizes.axes[axis].default

    def finding(self, code: str, message: str, *, where: str, use: str = "") -> Finding:
        """A finding that fails, at `where`: in the file of the component `use`, which it
        names with its library's version; with none, in the content."""
        if not use:
            return Finding(code, FAILS, message, where=where)
        library = self.library(use)
        return Finding(code, FAILS, message, where=where, library=library, extra={"component": use})

    def report(self, code: str, message: str, *, where: str, use: str = "") -> None:
        """Records a finding that fails, once: in the component `use`, or in the content."""
        self.add(self.finding(code, message, where=where, use=use))

    def add(self, finding: Finding) -> None:
        key = (finding.code, finding.file, finding.where, finding.message, finding.library)
        if key not in self._seen:
            self._seen.add(key)
            self.findings.append(finding)

    def take_back(self, code: str, where: str, use: str) -> None:
        """Takes back each finding of `code` at `where` in the component `use`, where a
        finding that names the fault's cause takes its place, so one fault has one
        finding."""
        self.findings = [
            finding
            for finding in self.findings
            if (finding.code, finding.where, finding.extra.get("component")) != (code, where, use)
        ]

    def attempt(self, compute: Callable[[], T], default: T) -> T:
        """A value, or `default` where it cannot be computed, its finding recorded."""
        try:
            return compute()
        except Fault as fault:
            if fault.finding is not None:
                self.add(fault.finding)
            return default

    def picture_file(
        self, holder: str, name: object, *, named: str, where: str, use: str
    ) -> Judged:
        """The picture file `name` names, of the piece where `holder` is `piece`, else of the
        version the lock names of the library `holder`, judged through the environment
        (`Env.picture_file`), its findings recorded. One on the file lies at the file. One on
        the name lies at `where` in the component `use`, which names the file, or, with no
        `use`, in the content, as every finding on what the content gave."""
        judged = self.env.picture_file(holder, name, named=named, where=where)
        for finding in judged.findings:
            if not finding.file and use:
                finding = replace(finding, extra={**finding.extra, "component": use})
            self.add(finding)
        return judged

    def library(self, use: str) -> str:
        """`<library>@<version>` of the library a component lies in; empty for the piece's
        own, which lies in the piece. A finding in a component names it beside this, as
        `component`, so the check finds the component's file in either."""
        library = use.split("/")[0]
        if library == names.PIECE:
            return ""
        try:
            return f"{library}@{self.env.library_version(library)}"
        except KeyError:
            return library

    def component(self, use: str) -> Component | None:
        """A component, read and checked once, its issues recorded; `None` where there is none,
        or where its file cannot be read, which is a finding in that file (`unreadable`)."""
        if use not in self._components:
            try:
                data = self.env.component(use)
            except UnreadableComponent as unreadable:
                self._unreadable.add(use)
                self.report("component-unreadable", str(unreadable), where="", use=use)
                data = None
            except KeyError:
                data = None
            # Not found while it is read, so a drawing whose top names it reads no loop.
            self._components[use] = None
            component = None
            if isinstance(data, Mapping):
                component = (
                    self._drawing(use, data) if DRAWS in data else Component(use, data, self)
                )
            self._components[use] = component
            for code, where, message in component.issues if component else ():
                self.report(code, message, where=where, use=use)
        return self._components[use]

    def _drawing(self, use: str, data: Mapping[str, Any]) -> Component:
        """A component that declares `draws`, read as a drawing of the layout of the top it
        names (DEC-034 point 1): what it holds of its own read with what it takes of the top
        (`Component.drawn_data`). Its findings lie in its own file: a piece's own component
        that declares `draws`, a status, a key of what the content gives, a physical size,
        which its top alone declares (DEC-034 point 3), a top or a layout there is none of, a
        size it may not write, and a field it shows by no part named after it.
        What the top declares is the top's to answer for, so no finding on it is repeated
        here. One that draws no layout a top declares draws nothing."""
        issues: list[tuple[str, str, str]] = []
        if use.partition("/")[0] == names.PIECE:
            issues.append(
                (DRAWING_SHAPE, DRAWS, "declares `draws`: a piece's own component draws no layout, "
                 "only a brand's does")
            )  # fmt: skip
        if STATUS in data:
            issues.append(
                (DRAWING_SHAPE, STATUS, "is a drawing, and carries a status: nothing names a "
                 "drawing, so its library promises nothing of it")
            )  # fmt: skip
        held = [key for key in GIVEN_BY_TOP if key in data]
        if held:
            listed = ", ".join(f"`{key}`" for key in held)
            issues.append(
                (DRAWING_SHAPE, held[0], f"is a drawing, and holds {listed}: a drawing declares "
                 "nothing the content gives, and takes its top's")
            )  # fmt: skip
        if PHYSICAL_SIZE in data:
            issues.append(
                (PHYSICAL_SIZE, PHYSICAL_SIZE, "declares a physical size, and is a drawing: its "
                 "top alone declares the size its pages print at")
            )  # fmt: skip
        draws = data.get(DRAWS)
        top_use = draws.get("top") if isinstance(draws, Mapping) else None
        layout = draws.get("layout") if isinstance(draws, Mapping) else None
        key = (str(top_use), str(layout))
        top = self.component(top_use) if isinstance(top_use, str) and top_use != use else None
        own = {name: data[name] for name in DRAWING_KEYS if name in data}
        drawn = None
        if top is not None and top.draws is None and isinstance(layout, str):
            drawn = top.drawn_data(layout, own)
        if top is None or drawn is None:
            issues.append(
                (DRAWING_SHAPE, DRAWS, f"draws `{layout}` of `{top_use}`, which is no layout of "
                 "a top: it draws nothing")
            )  # fmt: skip
            component = Component(use, {}, self, draws=key)
        else:
            combined, sizes = drawn
            component = Component(
                use, combined, self, layout=layout if top.forms else None, draws=key
            )
            component.top_exposes = top.exposes
            component.issues = [
                *(i for i in component.issues if i[1].partition(".")[0] in DRAWING_KEYS),
                *sizes,
                *((FIELD_PART, where, why) for where, why in component.field_breaks()),
            ]
        component.issues = [
            (code, where, message if message.startswith(f"{use}: ") else f"{use}: {message}")
            for code, where, message in [*issues, *component.issues]
        ]
        return component

    def drawn_by(self, component: Component, trace: str) -> Component:
        """What draws the instance at `trace` that `component` would draw as its top's own
        drawing of a layout: the brand's drawing of that layout the choice holds, unless the
        choice leaves the instance to the top's own; else `component` (DEC-009 points 2 and
        6). A drawing whose top or layout is another draws nothing."""
        key = component.drawn
        use = self.choice.drawings.get(key) if key is not None else None
        if use is None or trace in self.choice.refused:
            return component
        drawing = self.component(use)
        return drawing if drawing is not None and drawing.draws == key else component

    def unreadable(self, use: Any) -> bool:
        """Whether `use` names a component whose file is present and cannot be read. What
        names it is not at fault, so it takes no finding."""
        return use in self._unreadable

    def asked(self) -> set[str]:
        """The library of each component read or looked for, found or not, the piece's own
        left out. No other library's version can change how the piece is placed."""
        return {use.split("/")[0] for use in self._components} - {names.PIECE}

    def role(self, path: str) -> Any:
        """A role's resolved value. Raises `UnvaluedRole` for a library's own role the brand
        leaves with none, and `KeyError` for a path that holds no role."""
        if path not in self._roles:
            try:
                self._roles[path] = self.env.role(path)
            except KeyError as missing:
                self._roles[path] = missing
        found = self._roles[path]
        if isinstance(found, UnvaluedRole):
            raise UnvaluedRole(found.role, found.library, named=found.named)
        if isinstance(found, KeyError):
            raise KeyError(path)
        return found

    def picture_role(self, path: str) -> Picture | None:
        """The picture the brand gives the picture role at `path` at the scene's key over the
        size axes, read once (`Env.picture_role`); None where it gives none. Raises
        `KeyError` for a path that holds no role, and `ValueError` for a role of another
        type."""
        if path not in self._pictured:
            try:
                self._pictured[path] = self.env.picture_role(path)
            except (KeyError, ValueError) as error:
                self._pictured[path] = error
        found = self._pictured[path]
        if isinstance(found, KeyError):
            raise KeyError(path)
        if isinstance(found, Exception):
            raise ValueError(str(found))
        return found

    def unvalued(self, path: str) -> UnvaluedRole | None:
        """Why the role at `path` has no value, where it is a library's own role the brand
        leaves with none; None for a role with a value, or a path that holds no role."""
        try:
            self.role(path)
        except UnvaluedRole as unvalued:
            return unvalued
        except KeyError:
            return None
        return None

    def unvalued_at_lock(self, unvalued: UnvaluedRole, part: str) -> None:
        """Records that `part` reads a library's own role the brand leaves with no value
        (DEC-008 points 8 and 9). Where the brand, or a brand it builds on, names the
        library, that brand owes the role a value, which is its own finding, so the part
        takes none. Where none does, neither the brand nor the library alone is at fault:
        the finding lies at the lock that combines them, which the piece names, so it says
        so as `piece`. It names no version, so it fails."""
        if unvalued.named:
            return
        library, role = unvalued.library, unvalued.role
        message = (
            f"under this lock, {part} reads `@{role}`, a role of {self.library(library)} that "
            f"has no value: its chain of defaults reaches none, and the brand does not name "
            f"`{library}` to give it one"
        )
        fix = (
            f"lock a brand that names `{library}` and gives `@{role}` a value, or a version "
            f"of `{library}` whose `@{role}` has a default that reaches a shared role"
        )
        self.add(
            Finding("unknown-role", FAILS, message, where="lock", fix=fix, extra={"piece": True})
        )

    def family(self, name: str) -> Mapping[str, str] | None:
        """The members of a colour family the foundations declare, each mapped to a colour
        role (DEC-004 point 10); `None` where they declare no such family."""
        if name not in self._families:
            try:
                self._families[name] = self.env.family(name)
            except KeyError:
                self._families[name] = None
        return self._families[name]

    def concept(self, name: str) -> str | None:
        """The colour family a concept maps to, `<notation>/<concept>` (DEC-004 point 10);
        `None` where its notation, or the concept in it, cannot be read, which is a finding
        in the notation. Raises `UnknownConcept` where the piece's notations do not hold
        it."""
        if name not in self._concepts:
            try:
                self._concepts[name] = self.env.concept(name)
            except UnknownConcept as unknown:
                self._concepts[name] = unknown
        found = self._concepts[name]
        if isinstance(found, UnknownConcept):
            raise UnknownConcept(found.concept, found.why)
        return found

    def sign(self, name: str) -> Outline | None:
        """The sign of a concept `concept` has read, `<notation>/<concept>` (DEC-036 point
        1); `None` where it has none."""
        if name not in self._signs:
            self._signs[name] = self.env.sign(name)
        return self._signs[name]

    def role_dimension(self, path: str) -> tuple[int | None, str | None]:
        """A role's dimension in a formula, or why it has none."""
        try:
            value = self.role(path)
        except KeyError:
            return None, "names a role the brand gives no value"
        if isinstance(value, Mapping) and "value" in value and "unit" in value:
            if value["unit"] != "px":
                return None, f"reads a length in {value['unit']}; format 1 measures in px"
            return fm.LENGTH, None
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return fm.NUMBER, None
        return None, "reads a role that is not a length or a number"

    def role_number(self, path: str) -> float:
        dimension, problem = self.role_dimension(path)
        if problem:
            raise Fault()  # recorded when the formula's component was read
        value = self.role(path)
        return float(value["value"] if dimension == fm.LENGTH else value)


# --- instances ----------------------------------------------------------------------------


@dataclass(frozen=True)
class Arrangement:
    """A list's items along one axis: each item's offset and size, and the size they ask
    for together."""

    offsets: tuple[float, ...]
    sizes: tuple[float, ...]
    asked: float


@dataclass(frozen=True)
class TextRun:
    """A run of a text as its text part draws it (DEC-012): its text, the word of its
    style, which a field that takes no runs has none of, the typography role that word
    chooses, the concept it names, its colour family, and where each comes from: its
    text, its word and its family. `place` is its key path in the content file, where it
    has one, else its text's trace. `outline` is the sign of the concept it names, where
    the piece's notations hold the concept and give it one (DEC-036 point 3)."""

    text: str
    word: str | None
    style: Style
    concept: Any
    family: str | None
    family_source: str
    source: str
    word_source: str
    place: str
    outline: Outline | None = None


@dataclass
class Node:
    """A part as one instance draws it: a text holds its text and its runs."""

    part: Part
    present: bool = True
    child: Instance | None = None
    items: list[Instance] = field(default_factory=list)
    text: str = ""
    runs: list[TextRun] = field(default_factory=list)
    # An image of a produced output: the output, as its record keeps it, and its name.
    picture: PictureInfo | None = None
    output: str = ""
    # An image of a picture file: its bare name, where it lies, `piece` or a library's
    # name, and the file as the reader read it (DEC-025 points 2 and 3). An image of a
    # picture role: the role, and the file the brand gives it at the scene's key, as read
    # (point 4).
    file: str = ""
    holder: str = ""
    role: str = ""
    read: Picture | None = None
    # An image of a picture role the brand gives no file at the scene's key, which is not
    # drawn: the role, so a move onto that brand can name it (DEC-025 point 8).
    unvalued: str = ""
    # A sign: the outline of its instance's concept's sign (DEC-036 point 2).
    outline: Outline | None = None

    @property
    def line_height(self) -> float:
        """A text's line height: the greatest among the roles its runs take (DEC-012 point
        4)."""
        return max((run.style.line_height for run in self.runs), default=0.0)


def _join(path: str, key: str) -> str:
    return f"{path}.{key}" if path else key


def _filled(value: Any, *, runs: bool = False) -> bool:
    """Whether a field holds something: not missing, empty text, an empty list or an empty
    mapping. A list of runs, where `runs`, is filled where one of its runs holds text
    (DEC-012 point 1)."""
    if runs and isinstance(value, list):
        return any(_run_text(run) for run in value)
    return value not in (None, "", [], {})


def _run_text(run: Any) -> str:
    """The text a run holds: the run itself, or its `text`; empty where it holds none."""
    text = run.get("text") if isinstance(run, Mapping) else run
    return text if isinstance(text, str) else ""


def _run_style(run: Any, words: Sequence[str]) -> str:
    """The word of its field's `words` a run is set in, as it is drawn: its `style` where
    the field declares it, else the first word (DEC-012 point 2)."""
    style = run.get("style") if isinstance(run, Mapping) else None
    return style if isinstance(style, str) and style in words else words[0]


@dataclass(frozen=True)
class TieEnd:
    """An end of a tie as its pattern finds it (DEC-011 points 2 to 4): the instance drawn
    for the item its key path names, the exposed image part and the point where it names
    one, and its source, the end field of the tie."""

    item: Instance
    point: tuple[str, str] | None
    source: str


@dataclass(frozen=True)
class Anchor:
    """Where a connector meets one end, in its pattern's frame: the point, and the side of
    the end's frame it lies on, none for a point the end names."""

    x: float
    y: float
    side: str | None


def first_variant(picture: PictureInfo) -> str:
    """The variant whose pixels and points a scene reads: the first key in key order, the
    default first. Every variant one scene holds shares them (DEC-005 point 5)."""
    return min(picture.variants, key=key_order)


class Instance:
    """A component placed once: its fields and options, its colour family, its parts as
    built from the content, and its values, each computed on first use."""

    def __init__(
        self,
        ctx: Context,
        component: Component,
        given: Mapping[str, Any],
        *,
        trace: str,
        content_path: str | None,
        paths: Mapping[str, str] | None = None,
        sources: Mapping[str, str] | None = None,
        parent: Instance | None = None,
        part: str = "",
        is_item: bool = False,
        place_colour: tuple[str, str] | None = None,
        chain: tuple[str, ...] = (),
        through_pages: bool = False,
        by_content: bool = True,
        tie: ListFields | None = None,
    ) -> None:
        self.ctx = ctx
        # A brand's drawing draws it in place of its top's own, where the choice says so.
        component = ctx.drawn_by(component, trace)
        self.component = component
        self.given = given
        self.trace = trace
        # Where it is a tie, what its list declares, the value each of its end fields
        # gives, by `start` and `end`, and its two ends once found.
        self.tie = tie
        self.end_values: dict[str, Any] = {}
        self.ends: dict[str, TieEnd] = {}
        # The ties it draws that `find_ends` left out, each with the ends it found.
        self.left_out: list[Instance] = []
        # Where it is an item, each key it carries that both its component and its list
        # declare, which neither reads (DEC-010 point 2).
        self.clashed: tuple[str, ...] = ()
        # The key path of the mapping in the content file that holds what it was given; None
        # where no mapping does, as where a `use` part placed it: `paths` then holds the key
        # path of each field the part passes on.
        self.content_path = content_path
        self._paths = dict(paths or {})
        self.parent = parent
        self.part_name = part
        self.is_item = is_item  # an item its parent's list draws
        self.position = 0  # its place among the items its list draws, from 0
        # The word each arrangement field of its list takes on it, where it is an item.
        self.arranged: dict[str, str] = {}
        self.chain = chain or (component.use,)
        self.cells: dict[tuple[str, ...], Any] = {}
        self.nodes: dict[str, Node] = {}
        self.options: dict[str, Any] = {}
        self.option_sources: dict[str, str] = {}
        self.overrides: dict[str, tuple[str, str]] = {}
        self.library = ctx.library(component.use)
        # The instance whose part placed it with what it was given, where no content did.
        self._placer = None if by_content else parent
        self._sources = dict(sources or {})
        # What a slot of pages places is a page, and so is each page a top whose layouts
        # are its pages' forms holds. A top component with no slot of pages is a page
        # alone, and part of the page that holds it (DEC-005 point 5); a top whose layouts
        # are its pages' forms is none.
        inside = any(above.is_page for above in self._ancestors())
        alone = component.top and not component.pages and not component.forms
        self.is_page = through_pages or (alone and not inside)
        if self.is_page and inside:
            self._note("page-in-page", f"{trace}: {component.use} is a page inside a page")
        # What `:as` reads for it, from where it lies in its piece: `part` inside a page,
        # else `page`, the default (DEC-034 point 7).
        self.placed_as = PLACED_AS[1] if inside else PLACED_AS[0]
        if component.layout is not None and parent is not None:
            # A page in a layout gives no option: its drawing takes the top's (DEC-009
            # point 5).
            self.options, self.option_sources = dict(parent.options), dict(parent.option_sources)
        else:
            self._read_options()
        # The concept whose colour family it takes, by its name, and where it comes from: its
        # own, or the one of the instance it sits in where it takes its family from that.
        self.concept: str | None = None
        self.concept_source = ""
        self.family, self.family_source = self._colour(place_colour)
        self._read_overrides()
        for name, each in component.parts.items():
            self.nodes[name] = self._build(each)
        self.pages: list[Instance] = self._build_pages() if component.forms else []

    # -- findings

    def _note(self, code: str, message: str, where: str = "", given: str = "") -> None:
        """Records a finding on what this instance was given, at the trace of the element
        it concerns: `where`, else the instance's own. It lies where `given`, the key of
        what it concerns, came from: in the content, where the content placed this
        instance, or gave that value for a part to pass on; else in the component whose
        part placed it, and gave the value or left it out."""
        passed_on = self._sources.get(given, "").startswith(CONTENT)
        placer = None if passed_on else self._placer
        use = placer.component.use if placer is not None else ""
        self.ctx.report(code, message, where=where or self.trace, use=use)

    def _fail(self, code: str, message: str, where: str = "") -> Fault:
        """A fault, with its finding, in this instance's component."""
        where = where or self.trace
        return Fault(self.ctx.finding(code, message, where=where, use=self.component.use))

    # -- what it was given

    def _ancestors(self) -> list[Instance]:
        found, above = [], self.parent
        while above is not None:
            found.append(above)
            above = above.parent
        return found

    def field_path(self, name: str) -> str | None:
        """The key path of the field `name` in the content file, by the keys the file
        writes: the path of a field handed on under that name, by a `use` part that placed
        this instance or by the top that holds this page, else below the mapping that holds
        what this instance was given. None where no key of the content file gives the
        field."""
        if name in self._paths:
            return self._paths[name]
        if self.content_path is not None:
            return _join(self.content_path, name)
        return None

    def source_of_text(self, part: Part) -> str:
        """Where what a text part shows comes from: the fact it names, else its field."""
        if "fact" in part.props:
            return f"{FACT}{part.props['fact']}"
        return self.source_of_field(part.props["content"])

    def source_of_field(self, name: str) -> str:
        """Where the field or option `name` comes from: the source the part that placed
        this instance gave it, else the field's key path in the content file. A field no key
        of the content file gives, such as one a `use` part does not pass on, is the
        component whose part placed the instance's to give, and it gives none."""
        if name in self._sources:
            return self._sources[name]
        path = self.field_path(name)
        if path is not None:
            return f"{CONTENT}{path}"
        placer = self.parent if self.parent is not None else self
        return f"default:{placer.component.use}"

    def _read_options(self) -> None:
        use = self.component.use
        for name, option in self.component.options.items():
            raw = self.given.get(name)
            if not option.words:
                self.options[name] = self._item_option(name, option, raw)
                self.option_sources[name] = self.source_of_field(name)
            elif raw in option.words:
                self.options[name], self.option_sources[name] = raw, self.source_of_field(name)
            else:
                if raw is not None:
                    words = ", ".join(option.words)
                    self._note(
                        "option-word",
                        f"{self.trace}: `{name}` of {use} takes {words}, not `{raw}`",
                        given=name,
                    )
                self.options[name], self.option_sources[name] = option.words[0], f"default:{use}"

    def _item_option(self, name: str, option: Option, raw: Any) -> Mapping[str, str] | None:
        use = self.component.use
        if raw is None:
            self._note(
                "option-missing", f"{self.trace}: {use} needs the option `{name}`", given=name
            )
            return None
        if not isinstance(raw, Mapping) or set(raw) != (
            {"item", "point"} if option.point else {"item"}
        ):
            shape = "{item: <id>, point: <name>}" if option.point else "{item: <id>}"
            self._note(
                "option-word",
                f"{self.trace}: the option `{name}` of {use} takes {shape}",
                given=name,
            )
            return None
        listed = self.given.get(option.items or "")
        ids = (
            [each.get("id") for each in listed if isinstance(each, Mapping)]
            if isinstance(listed, list)
            else []
        )
        if raw["item"] not in ids:
            self._note(
                "unknown-item",
                f"{self.trace}: `{name}` names `{raw['item']}`, no item of `{option.items}`",
                given=name,
            )
            return None
        return raw

    def _colour(self, place: tuple[str, str] | None) -> tuple[str | None, str]:
        """The instance's colour family (DEC-001 point 6): its concept's, else its place's
        default in a list, else its component's, else its container's; then its state's.
        Sets the concept it takes its family from, which its state leaves (DEC-036 point
        2)."""
        concept = self._concept()
        if concept is not None:
            family, source = concept, self.source_of_field("concept")
            self.concept, self.concept_source = self.given["concept"], source
        elif place is not None:
            family, source = place
        elif self.component.colour:
            family, source = self.component.colour, f"default:{self.component.use}"
        elif self.parent is not None:
            family, source = self.parent.family, self.parent.family_source
            self.concept, self.concept_source = self.parent.concept, self.parent.concept_source
        else:
            family, source = None, ""
        state = self.given.get("state")
        if state is not None:
            if state not in self.component.states:
                self._note(
                    "unknown-state",
                    f"{self.trace}: {self.component.use} declares no state `{state}`",
                    given="state",
                )
            elif self.component.states[state]:
                family, source = self.component.states[state], self.source_of_field("state")
        return family, source

    def _concept(self) -> str | None:
        """The colour family of the concept the instance names, `<notation>/<concept>`
        (DEC-004 point 10); None where it names none, or none gives it a family. A concept
        of another shape, or one the piece's notations do not hold, is reported; one its
        notation cannot read is a finding in that notation alone."""
        raw = self.given.get("concept")
        if raw is None:
            return None
        # A concept is read with its notation's name, as a use is with its library's.
        if not _is_use(raw):
            self._note(
                "unknown-concept",
                f"{self.trace}: `concept` takes `<notation>/<concept>`, not `{raw}`",
                given="concept",
            )
            return None
        try:
            return self.ctx.concept(raw)
        except UnknownConcept as unknown:
            self._note("unknown-concept", f"{self.trace}: {unknown}", given="concept")
            return None

    def _read_overrides(self) -> None:
        raw = self.given.get("override")
        if raw is None:
            return
        if not isinstance(raw, Mapping):
            self._note(
                "override", f"{self.trace}: `override` takes {{<part>: <role>}}", given="override"
            )
            return
        for name, role in raw.items():
            part = self.component.parts.get(name)
            if part is None or part.kind not in OVERRIDDEN:
                self._note(
                    "override",
                    f"{self.trace}: `override` names `{name}`, no painted part of it",
                    given="override",
                )
            elif not names.is_token_path(role):
                self._note(
                    "override",
                    f"{self.trace}: `override` points `{name}` at `{role}`, not a role",
                    given="override",
                )
            elif role.split(".")[0] == names.COMPONENT:
                self._note(
                    "override",
                    f"{self.trace}: `override` points `{name}` at `{role}`, a component token, "
                    "which only its component reads: point it at a role",
                    given="override",
                )
            else:
                self.overrides[name] = (role, f"{self.source_of_field('override')}.{name}")

    def pick(self, where: str, value: Any, run: str | None = None) -> tuple[str, Any, str | None]:
        """A value through its switches: the key path of the branch taken, the value, and
        the option, the field of runs, or the marked name, that chose it. A switch on a
        field's run styles takes `run`, the word of the run drawn, else the field's first
        word. A switch by a marked name takes its branch for this instance
        (`_marked_branch`)."""
        chosen = None
        while isinstance(value, Mapping) and SWITCH in value:
            chosen = value[SWITCH]
            words = self.component.runs.get(chosen) if isinstance(chosen, str) else None
            if _by_marked(value):
                word = self._marked_branch(value)
            elif words is not None:
                word = run if run in words else words[0]
            else:
                word = self.options.get(chosen)
            where, value = f"{where}.{word}", value.get(word)
        return where, value, chosen

    def _marked_branch(self, switch: Mapping[str, Any]) -> str | None:
        """The branch a switch by a marked name takes for this instance: by `:as`, where its
        component is a drawing of a layout, the branch of where the instance lies (DEC-034
        point 7); by a size, the scene's (`Context.size_branch`). None where the marked name
        reads nothing, which was reported when its component was read."""
        if switch[SWITCH] != AS:
            return self.ctx.size_branch(switch)
        return _as_branch(switch, self.placed_as) if self.component.draws_layout else None

    def _when(self, part: Part) -> bool:
        """Whether the part is drawn: no `when`, or a `when` that holds. A `when` by a
        marked name holds by its branch for this instance (`_marked_branch`): `true`,
        `false`, or the `when` it gives."""
        when = part.spec.get("when")
        if when is None:
            return True
        if _by_marked(when):
            when = when.get(self._marked_branch(when))
            if isinstance(when, bool):
                return when
        if isinstance(when, str):
            return _filled(self.given.get(when), runs=when in self.component.runs)
        if isinstance(when, Mapping) and len(when) == 1:
            ((name, words),) = when.items()
            return self.options.get(name) in (words if isinstance(words, list) else [words])
        return False

    # -- its parts, built from the content

    def _build(self, part: Part) -> Node:
        # A connector is drawn only where the instance is a tie, which is given ends.
        connects = part.kind == "line" and "connect" in part.spec
        node = Node(part, present=self._when(part) and not (connects and self.tie is None))
        if node.present:
            trace = f"{self.trace}/{part.name}"
            build = {
                "text": self._build_text,
                "image": self._build_image,
                "sign": self._build_sign,
                "use": self._build_use,
                "slot": self._build_slot,
                "repeat": self._build_items,
            }.get(part.kind)
            if build is not None:
                build(node, trace)
        return node

    def _build_text(self, node: Node, trace: str) -> None:
        """The text a text part shows: a fact of its export (`_build_fact`), or its field's
        text, one run, or, in a field of runs, its runs (DEC-012 point 1). Each run takes the
        typography role its word chooses. A field given as text is one run of the field's
        first word. A part that names neither is recorded when the component was read."""
        props = node.part.props
        if "fact" in props:
            self._build_fact(node, trace)
            return
        if "content" not in props:
            node.present = False
            return
        content = props["content"]
        words = self.component.runs.get(content)
        value = self.given.get(content)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            value = str(value)
        given = self._given_runs(content, words, value) if isinstance(value, list) else []
        if not isinstance(value, list) or words is None:
            if value is not None and not isinstance(value, str):
                self._note(
                    "content-shape",
                    f"{trace}: the field `{content}` holds no text",
                    where=trace,
                    given=content,
                )
                value = None
            given = [(value or "", words[0] if words else None, False, None, None)]
        styles: dict[str, Style] = {}
        for text, word, named, concept, place in given:
            style = self._style_of(node, word, styles, trace)
            if style is None:
                return
            node.runs.append(
                self._text_run(content, text, word, named, concept, place, style, trace)
            )
        node.text = "".join(run.text for run in node.runs)

    def _build_fact(self, node: Node, trace: str) -> None:
        """The text of a fact of the export, as what fills it gives it: one run, in the role
        `style` names, which takes no run styles (DEC-006 point 7). A word no fact takes is
        recorded when the component was read."""
        word = node.part.props["fact"]
        if word not in FACTS:
            node.present = False
            return
        style = self._style_of(node, None, {}, trace)
        if style is None:
            return
        node.text = self.ctx.fact(word)
        node.runs.append(
            TextRun(
                node.text,
                None,
                style,
                None,
                self.family,
                self.family_source,
                self.source_of_text(node.part),
                f"default:{self.component.use}",
                trace,
            )
        )

    def _style_of(
        self, node: Node, word: str | None, styles: dict[str, Style], trace: str
    ) -> Style | None:
        """The style of a run of `word` in a text part, each role read once into `styles`.
        None where the role cannot be read, and the part is then not drawn."""
        name, props = node.part.name, node.part.props
        _, role, _ = self.pick(f"parts.{name}.text.style", props.get("style"), word)
        if not isinstance(role, str):
            node.present = False  # recorded when the component was read
            return None
        if role not in styles:
            try:
                styles[role] = Style.of_role(role, self.ctx.role(role), self.ctx.faces)
            except UnvaluedRole as unvalued:
                use = self.component.use
                self.ctx.unvalued_at_lock(unvalued, f"the text `{trace}` of `{use}`")
                node.present = False
                return None
            except KeyError:
                message = f"{trace}: the brand gives the role @{role} no value"
                self._lose(node, "unknown-role", message, trace)
                return None
            except ValueError as error:
                self._lose(node, "role-type", f"{trace}: {error}", trace)
                return None
        return styles[role]

    def _given_runs(
        self, content: str, words: tuple[str, ...] | None, value: list[Any]
    ) -> list[tuple[str, str | None, bool, Any, int | None]]:
        """The runs a field of runs holds, each its text, its word, whether it names it, its
        concept and its place among the field's runs, from 1. A run that is neither text
        nor a mapping with text is left out, and a word its field does not declare is the
        first, as the check of the content reports. A list that gives no run is one empty
        run."""
        if words is None:
            return []
        found: list[tuple[str, str | None, bool, Any, int | None]] = []
        for place, run in enumerate(value, start=1):
            if isinstance(run, str):
                found.append((run, words[0], False, None, place))
            elif isinstance(run, Mapping) and isinstance(run.get("text"), str):
                named = run.get("style") in words
                word = run["style"] if named else words[0]
                found.append((run["text"], word, named, run.get("concept"), place))
        return found or [("", words[0], False, None, None)]

    def _text_run(
        self,
        content: str,
        text: str,
        word: str | None,
        named: bool,
        concept: Any,
        place: int | None,
        style: Style,
        trace: str,
    ) -> TextRun:
        """A run as its text part draws it. Its source names its field and, in a list, its
        place among the field's runs, as a source names an item with no id (DEC-012,
        Implications). A run that names a concept takes its concept's family before the
        instance's own, and a state that gives the instance a family replaces it (point 3).
        It keeps its concept's sign under any state (DEC-036 point 3)."""
        source = self.source_of_field(content)
        path = self.field_path(content)
        at = trace
        if place is not None:
            source = f"{source}#{place}" if source.startswith(CONTENT) else source
            at = f"{path}#{place}" if path is not None else trace
        word_source = f"{source}.style" if named else f"default:{self.component.use}"
        family, family_source = self.family, self.family_source
        outline = None
        if concept is not None:
            found = self._run_concept(content, concept, at, trace)
            state = self.given.get("state")
            stated = isinstance(state, str) and bool(self.component.states.get(state))
            if found is not None and not stated:
                family, family_source = found, f"{source}.concept"
            if found is not None:
                outline = self.ctx.sign(concept)  # a state changes the paint, never the sign
        return TextRun(
            text, word, style, concept, family, family_source, source, word_source, at, outline
        )

    def _run_concept(self, content: str, raw: Any, at: str, trace: str) -> str | None:
        """The colour family of the concept a run names, read with its notation's name as an
        item's is (DEC-012 point 3); None where it names none the piece's notations hold,
        which is reported at the run."""
        if not _is_use(raw):
            self._note(
                "unknown-concept",
                f"{trace}: a run of `{content}` names the concept `{raw}`, not "
                "`<notation>/<concept>`",
                where=at,
                given=content,
            )
            return None
        try:
            return self.ctx.concept(raw)
        except UnknownConcept as unknown:
            self._note(
                "unknown-concept",
                f"{trace}: a run of `{content}`: {unknown}",
                where=at,
                given=content,
            )
            return None

    def _lose(self, node: Node, code: str, message: str, where: str) -> None:
        """Records why the component cannot draw the part at `where`, which then has zero
        size."""
        self.ctx.report(code, message, where=where, use=self.component.use)
        node.present = False

    def _build_image(self, node: Node, trace: str) -> None:
        """The picture an image shows (DEC-025 points 1 to 4): a produced output, by the field
        `produced` names; a picture file of the piece, by the bare name the field `content`
        names holds, whichever component draws it; a picture file of the component's own
        library version, or of the piece for a local component, by `file`; or the file the
        brand gives the picture role `role` names (`_show_role`). A field the content leaves
        empty draws nothing, at zero size, with no finding; so does a picture file that
        cannot be read, which is its finding. An image that names none of them is recorded
        when its component was read."""
        props = node.part.props
        if "produced" in props:
            self._build_produced(node, trace)
        elif "content" in props:
            shown = props["content"]
            name = self.given.get(shown)
            if not isinstance(name, str) or not name:
                node.present = False
                return
            source = self.source_of_field(shown)
            where = source[len(CONTENT) :] if source.startswith(CONTENT) else trace
            named = f"the content's `{where}`"
            self._show_file(node, names.PIECE, name, named=named, where=where, use="")
        elif "file" in props:
            use = self.component.use
            where = f"parts.{node.part.name}.image.file"
            named = f"{use}: the image `{node.part.name}`"
            library = use.partition("/")[0]
            self._show_file(node, library, props["file"], named=named, where=where, use=use)
        elif "role" in props:
            self._show_role(node, trace)
        else:
            node.present = False

    def _build_sign(self, node: Node, trace: str) -> None:
        """The outline a sign part draws: the sign of the concept whose colour family the
        instance takes (DEC-036 point 2). Where it takes its family from no concept, or the
        concept has no sign, the part is not drawn, at zero size, with no finding."""
        if self.concept is not None:
            node.outline = self.ctx.sign(self.concept)
        node.present = node.outline is not None

    def _show_role(self, node: Node, trace: str) -> None:
        """The file the brand gives the picture role the image's `role` names, at the scene's
        key over the size axes (DEC-025 point 4). Where the brand gives it none the image is
        not drawn, at zero size, with no finding, since no brand owes a picture role; the
        node keeps the role, so a move onto that brand can name it (DEC-025 point 8). A
        `role` that names no role, or a role of another type, is the component's finding,
        and the image is not drawn either."""
        role = node.part.props["role"]
        if not isinstance(role, str):
            node.present = False  # recorded when the component was read
            return
        where = f"parts.{node.part.name}.image.role"
        try:
            read = self.ctx.picture_role(role)
        except KeyError:
            message = f"{trace}: no library locked with the brand declares the role @{role}"
            self._lose(node, "unknown-role", message, where)
            return
        except ValueError as error:
            self._lose(node, "role-type", f"{trace}: {error}", where)
            return
        if read is None:
            node.present, node.unvalued = False, role
            return
        node.role, node.read = role, read

    def _show_file(
        self, node: Node, holder: str, name: object, *, named: str, where: str, use: str
    ) -> None:
        """The picture file `name` of `holder` an image shows, judged (`Context.picture_file`);
        the image is not drawn where it cannot be read."""
        judged = self.ctx.picture_file(holder, name, named=named, where=where, use=use)
        if judged.picture is None or not isinstance(name, str):
            node.present = False
            return
        node.file, node.holder, node.read = name, holder, judged.picture

    def _build_produced(self, node: Node, trace: str) -> None:
        """A produced output's picture, from its record: missing where the piece has no such
        output; its variants of one pixel size and one set of points, as one scene holds
        them (DEC-005 point 5)."""
        produced = node.part.props.get("produced", "")
        output = self.given.get(produced)
        if not isinstance(output, str):
            node.present = False
            return
        try:
            picture = self.ctx.env.picture(output)
        except KeyError:
            picture = None
        if picture is None or not picture.variants:
            self._note(
                "missing-picture",
                f"{trace}: the piece has no produced output `{output}`",
                where=trace,
                given=produced,
            )
            node.present = False
            return
        first = first_variant(picture)
        for key, variant in picture.variants.items():
            moved = any(places.get(key) != places.get(first) for places in picture.points.values())
            if moved or variant.get("pixels") != picture.variants[first].get("pixels"):
                self._note(
                    "picture-variants",
                    f"{trace}: the variants of `{output}` differ in pixels or points, and one "
                    "scene holds them all",
                    where=trace,
                    given=produced,
                )
                break
        node.picture, node.output = picture, output

    def _component(self, node: Node, use: Any, trace: str, *, by_content: bool) -> Component | None:
        """The component `use` names, to draw a part or an item; `None` where there is none,
        with a finding in what named it: the content where `by_content`, else this
        instance's component. A component whose file cannot be read is a finding in that
        file alone (`Context.component`)."""
        component = self.ctx.component(use) if isinstance(use, str) else None
        named_in = "" if by_content else self.component.use
        if component is None:
            if not self.ctx.unreadable(use):
                self.ctx.report(
                    "unknown-component", f"{trace}: no component `{use}`", where=trace, use=named_in
                )
            node.present = False
        elif component.draws is not None:
            placed(self.ctx, component, where=trace, use=named_in)
            node.present = False
            return None
        return component

    def _build_use(self, node: Node, trace: str) -> None:
        spec = node.part.spec
        use = spec["use"]
        if use in self.chain:
            loop = " → ".join([*self.chain, use])
            self.ctx.report(
                "places-itself",
                f"{trace}: {use} places itself: {loop}",
                where=trace,
                use=self.component.use,
            )
            node.present = False
            return
        component = self._component(node, use, trace, by_content=False)
        if component is None:
            return
        given: dict[str, Any] = {}
        sources: dict[str, str] = {}
        # Each field it passes on keeps the key path the content file writes for it.
        paths: dict[str, str] = {}
        ties = {name for name, each in component.list_fields.items() if each.ends is not None}
        for theirs, ours in (spec.get("fields") or {}).items():
            if theirs in ties:
                # A list of ties is drawn where its end fields are declared (DEC-011 point 1).
                self.ctx.report(
                    "component-shape",
                    f"{self.component.use}: the part `{node.part.name}` passes `{ours}` on to "
                    f"`{theirs}`, a list of ties of {use}, which only the component that "
                    "declares its end fields draws",
                    where=f"parts.{node.part.name}.fields.{theirs}",
                    use=self.component.use,
                )
                continue
            path = self.field_path(ours)
            if path is not None:
                paths[theirs] = path
            if ours in self.given:
                given[theirs], sources[theirs] = self.given[ours], self.source_of_field(ours)
        for theirs, raw in (spec.get("options") or {}).items():
            _, word, chosen = self.pick(f"parts.{node.part.name}.options.{theirs}", raw)
            given[theirs] = word
            sources[theirs] = (
                source_of_choice(chosen) if chosen else f"default:{self.component.use}"
            )
        node.child = Instance(
            self.ctx, component, given, trace=trace, content_path=None, paths=paths,
            sources=sources, parent=self, part=node.part.name, chain=(*self.chain, use),
            by_content=False,
        )  # fmt: skip

    def _build_slot(self, node: Node, trace: str) -> None:
        name = node.part.spec["slot"]
        placed = self.given.get(name)
        if not _filled(placed):
            node.present = False
            return
        if not isinstance(placed, Mapping) or "use" not in placed:
            self._note(
                "content-shape",
                f"{trace}: the slot `{name}` takes a component, `{{use: ...}}`",
                where=trace,
                given=name,
            )
            node.present = False
            return
        component = self._component(node, placed["use"], trace, by_content=True)
        if component is not None:
            node.child = Instance(
                self.ctx, component, placed, trace=trace, content_path=self.field_path(name),
                parent=self, part=node.part.name, through_pages=name in self.component.pages,
            )  # fmt: skip

    def _build_items(self, node: Node, trace: str) -> None:
        """Each item of the list the part repeats over, drawn in the content's order. What
        draws an item is the component its own `use` names, else the one its list's
        component field names, else the part's `draw` (DEC-010 point 1). An item that names
        none takes each key the field gives that it does not give itself, which names the
        field as its source. The item's component never reads an arrangement field of its
        list: the item keeps the word each takes in `arranged`. A key that both the item's
        component and its list declare is read by neither, so the component's field stays
        unfilled and the arrangement field takes its default (point 2). An item that is no
        mapping, repeats an id, or names no component is left out: it takes no place among
        the items drawn, so `:index` and `:count` never count it. Its trace keeps its place
        in the content's list, and so does its key path, which names the list as the
        content file writes it.

        In a list of ties, the tie keeps the value of each end field in `end_values`, and an
        end field that its component also declares gives no end (DEC-011 point 1). A tie
        whose component takes no ends is left out, as the check reports: in the content,
        where the content names it; checking alone the library of the pattern, where the
        part's `draw` does. A piece's own pattern is judged where it is drawn."""
        spec = node.part.spec
        name = spec["repeat"]
        listed = self.given.get(name)
        listed = listed if isinstance(listed, list) else []
        place = (spec["colour"], f"default:{self.component.use}") if spec.get("colour") else None
        path = self.field_path(name)
        declared = self.component.list_fields.get(name, ListFields(None, {}))
        ties = declared if declared.ends is not None else None
        chosen = self._list_component(node, declared, trace)
        seen: set[str] = set()
        for index, item in enumerate(listed, start=1):
            key = item.get("id") if isinstance(item, Mapping) else None
            step = f"[{key}]" if key is not None else f"#{index}"
            at = f"{trace}{step}"
            if not isinstance(item, Mapping) or key in seen:
                self._note(
                    "content-shape",
                    f"{at}: an item of `{name}` is no mapping, or repeats its id",
                    where=at,
                    given=name,
                )
                continue
            if key is not None:
                seen.add(key)
            given: Mapping[str, Any] = item
            sources: dict[str, str] = {}
            if "use" in item:
                component = self._component(node, item["use"], at, by_content=True)
            elif chosen is not None:
                component, by_field, field_source = chosen
                taken = {k: v for k, v in by_field.items() if k not in item}
                given = {**taken, **item}
                sources = {k: f"{field_source}.{k}" for k in taken}
            else:
                component = self._component(node, spec.get("draw"), at, by_content=False)
            if component is None:
                node.present = True  # the list stays; the item is left out
                continue
            if ties is not None and not component.takes_ends:
                self._no_ends(node, component, by_default="use" not in item and chosen is None)
                continue
            claimed = {*component.fields, *component.options}
            instance = Instance(
                self.ctx, component,
                {k: v for k, v in given.items() if k not in declared.keys},
                trace=at, content_path=None if path is None else f"{path}{step}",
                sources=sources, parent=self, part=node.part.name, is_item=True,
                place_colour=place, through_pages=name in self.component.pages, tie=ties,
            )  # fmt: skip
            instance.position = len(node.items)
            instance.clashed = tuple(sorted(k for k in claimed & {*declared.keys} if k in item))
            for field_name, each in declared.arrangement.items():
                word = item.get(field_name)
                read = field_name not in claimed and word in each.words
                instance.arranged[field_name] = word if read else each.default
            for which, field_name in zip(ENDS, declared.ends or (), strict=False):
                if field_name not in claimed:
                    instance.end_values[which] = item.get(field_name)
            node.items.append(instance)

    def _no_ends(self, node: Node, component: Component, *, by_default: bool) -> None:
        """A tie whose component takes no ends, which is left out (DEC-011 points 1 and 8).
        Where the part's `draw` names that component, and the pattern is the piece's own,
        the pattern is reported here; a library's pattern is judged when its version is
        checked alone, and a component content names, in the check of the content."""
        node.present = True  # the list stays; the tie is left out
        if not by_default or self.library:
            return
        listed = node.part.spec["repeat"]
        self.ctx.report(
            "tie-default",
            f"{self.component.use}: `{component.use}` draws the ties of `{listed}` by default, "
            "and takes no ends: every item of a list of ties is a tie",
            where=f"parts.{node.part.name}.draw",
            use=self.component.use,
        )

    def _list_component(
        self, node: Node, declared: ListFields, trace: str
    ) -> tuple[Component | None, dict[str, Any], str] | None:
        """The component a list's component field names (DEC-010 point 1), with the keys
        the field gives each item that names none, its component's options, `concept`,
        `state` and `override`, and the field's source. None where the component declares
        no component field for the list, or the content names no component in it, so the
        part's `draw` draws such an item; the check of the content reports a field of
        another shape. A component the field names that there is none of is reported once,
        at the part's trace, and draws no item."""
        raw = self.given.get(declared.component) if declared.component is not None else None
        if not isinstance(raw, Mapping) or not isinstance(raw.get("use"), str):
            return None
        component = self._component(node, raw["use"], trace, by_content=True)
        node.present = True  # the list stays
        if component is None or declared.component is None:
            return None, {}, ""
        given = {k: v for k, v in raw.items() if k in component.options or k in GIVEN_BY_FIELD}
        return component, given, self.source_of_field(declared.component)

    def _build_pages(self) -> list[Instance]:
        """The pages of a top whose layouts are its pages' forms, in the content's order
        (DEC-010 point 5), each placed by the top and as large as it. A page that names its
        layout is drawn by that layout's drawing (DEC-009 point 1); one that names its
        component by `use`, by that component, as a page. A page that is no mapping, or
        repeats an id, or names a component there is none of, is left out, and reported.
        One that names neither, or a layout the top does not declare, is left out, and the
        check of the content reports it. Its trace is the top's, the field and its id, or
        its place where it has no id, as an item's; so is its key path."""
        name = self.component.pages_field
        listed = self.given.get(name) if name is not None else None
        path = self.field_path(name) if name is not None else None
        pages: list[Instance] = []
        seen: set[str] = set()
        for index, page in enumerate(listed if isinstance(listed, list) else [], start=1):
            key = page.get("id") if isinstance(page, Mapping) else None
            step = f"[{key}]" if key is not None else f"#{index}"
            at = f"{self.trace}/{name}{step}"
            if not isinstance(page, Mapping) or key in seen:
                self._note(
                    "content-shape",
                    f"{at}: a page of `{name}` is no mapping, or repeats its id",
                    where=at,
                    given=str(name),
                )
                continue
            if key is not None:
                seen.add(key)
            if "use" in page:
                use = page["use"]
                component = self.ctx.component(use) if isinstance(use, str) else None
                if component is None and not self.ctx.unreadable(use):
                    self.ctx.report("unknown-component", f"{at}: no component `{use}`", where=at)
                elif component is not None and component.draws is not None:
                    placed(self.ctx, component, where=at, use="")
                    component = None
            else:
                component = self.component.drawings.get(page.get(LAYOUT))
            if component is None:
                continue
            given, sources, paths = dict(page), {}, {}
            if component.layout is not None:
                # Its drawing takes the top's other fields, as the top was given them, each
                # at its own key path in the content file.
                for other in self.component.fields:
                    if other != name and other in self.given and other not in page:
                        given[other], sources[other] = (
                            self.given[other],
                            self.source_of_field(other),
                        )
                        handed = self.field_path(other)
                        if handed is not None:
                            paths[other] = handed
            pages.append(
                Instance(
                    self.ctx,
                    component,
                    given,
                    trace=at,
                    content_path=None if path is None else f"{path}{step}",
                    paths=paths,
                    sources=sources,
                    parent=self,
                    part=str(name),
                    through_pages=True,
                )
            )
        return pages

    def from_the_top(self) -> list[str]:
        """The trace of each part of this page that draws a field its top handed it: a part
        that places it, repeats over it, shows it, or passes it on (DEC-010 point 5). Every
        page drawn in a layout draws such a field alike, so what is found there is read once
        (DEC-022 point 8). None for a page drawn by its own component, which takes no field
        of the top."""
        handed = set(self._sources) if self._is_forms_page and self.component.layout else set()
        found = []
        for name, node in self.nodes.items():
            spec, props = node.part.spec, node.part.props
            read = {spec.get("slot"), spec.get("repeat"), props.get("content")}
            read.add(props.get("produced"))
            fields = spec.get("fields") if node.part.kind == "use" else None
            read.update(fields.values() if isinstance(fields, Mapping) else ())
            if node.present and handed & {each for each in read if isinstance(each, str)}:
                found.append(f"{self.trace}/{name}")
        return found

    def misfit(self) -> str | None:
        """What this instance gives that the brand's drawing that draws it does not take,
        in words; None where it takes all of it, or no brand's drawing draws it (DEC-009
        point 6). The drawing takes:

        - a field that a part of it shows, or passes on to a component it places;
        - the word the content chose of an option, where a switch or a `when` of it reads
          that word, and no switch on the option leaves it out; and any word of the option,
          the default included, where a switch on it leaves that word out
          (`Component.takes_word`);
        - a part the content's `override` points at another role, where it paints that part;
        - each part its top exposes, where another component places the top, and so may
          read it;
        - a run's word of a field of runs, where a text part that shows the field chooses
          by its words and no switch on them leaves it out, and the first word alone where
          none chooses; and the runs of none, where it passes the field on
          (`Component.run_words`, DEC-012 point 2);
        - each end of the ties it draws, found under it (DEC-011 point 5).

        A state gives the instance its colour by the top's own states, so every drawing
        takes every state."""
        component = self.component
        if component.draws is None:
            return None
        # A part a `when` leaves out here, such as one a size hides, takes nothing here.
        shown: set[str] = set()
        for part in component.parts.values():
            if self._when(part):
                shown |= part.passes | ({part.shows} if part.shows else set())
        for name in component.fields:
            given = self.given.get(name)
            if _filled(given, runs=name in component.runs) and name not in shown:
                return f"the field `{name}`"
        for name, source in sorted(self.option_sources.items()):
            word = self.options.get(name)
            if not isinstance(word, str):
                continue
            left_out = word in component.switch_gaps.get(name, {})
            chosen = source.startswith(CONTENT)
            if left_out or (chosen and not component.takes_word(name, word)):
                return f"the word `{word}` of the option `{name}`"
        override = self.given.get("override")
        for name in override if isinstance(override, Mapping) else {}:
            part = component.parts.get(str(name))
            if part is None or part.kind not in OVERRIDDEN:
                return f"the part `{name}`, which `override` points at another role"
        if self.parent is not None and not self._is_forms_page:
            for name in component.top_exposes:
                if name not in component.exposes:
                    return f"the exposed part `{name}`"
        texts = {part.shows for part in component.parts.values() if part.kind == "text"}
        for name, words in component.runs.items():
            runs = self.given.get(name)
            if isinstance(runs, list) and runs:
                if name not in texts or name in component.runs_passed:
                    return f"the runs of `{name}`, which it passes on and shows as text alone"
                styles = [_run_style(run, words) for run in runs]
            elif isinstance(runs, str) and runs and name not in component.runs_passed:
                # Text is one run in the first style.
                styles = list(words[:1])
            else:
                continue
            taken = component.run_words(name)
            for word in styles:
                if word in words and word not in taken:
                    return f"the word `{word}` of the runs of `{name}`"
        if self.left_out:
            return f"an end of the tie `{self.left_out[0].trace}`"
        return None

    def texts(self) -> list[tuple[str, Node]]:
        """Every text this instance and those below it draw, its pages' included, with its
        trace id."""
        found = []
        for name, node in self.nodes.items():
            if not node.present:
                continue
            if node.part.kind == "text":
                found.append((f"{self.trace}/{name}", node))
            for child in ([node.child] if node.child else []) + node.items:
                found.extend(child.texts())
        for page in self.pages:
            found.extend(page.texts())
        return found

    # -- cells

    def label(self, cell: tuple[str, ...]) -> str:
        """A cell, named for a message."""
        kind = cell[0]
        if kind == "size":
            return f"{self.trace} :{cell[1]}"
        if kind == "stretch":
            return f"{self.trace} stretch of :{cell[1]}"
        if kind in ("preferred", "value"):
            return f"{self.trace} {kind} {cell[1]}"
        if kind == "part":
            return f"{self.trace}/{cell[1]}.{cell[2]}"
        if kind == "end":
            return f"{self.trace} {{{cell[1]}}}"
        if kind == "anchors":
            return f"{self.trace} ties"
        return f"{self.trace}/{cell[1]} {kind}"

    def get(self, *cell: str) -> Any:
        """A cell's value, computed on first use. Raises `Fault`."""
        if cell in self.cells:
            if self.cells[cell] is _FAILED:
                raise Fault()
            return self.cells[cell]
        key = (id(self), cell)
        if key in self.ctx.active:
            start = next(i for i, (at, c) in enumerate(self.ctx.stack) if at is self and c == cell)
            loop = [at.label(c) for at, c in self.ctx.stack[start:]] + [self.label(cell)]
            raise self._fail("loop", f"a loop of references: {' → '.join(loop)}")
        self.ctx.stack.append((self, cell))
        self.ctx.active.add(key)
        try:
            value = self._compute(cell)
        except Fault:
            self.cells[cell] = _FAILED
            raise
        finally:
            self.ctx.stack.pop()
            self.ctx.active.discard(key)
        self.cells[cell] = value
        return value

    def _compute(self, cell: tuple[str, ...]) -> Any:
        kind, name = cell[0], cell[1]
        if kind == "size":
            return self._size(name)
        if kind == "stretch":
            return self._stretch(name)
        if kind == "preferred":
            physical = self.component.physical_size
            if name == "height" and physical is not None:
                # Wherever it lies, its height follows the width it asks for in the physical
                # size's proportion (DEC-034 point 3).
                return self.get("preferred", "width") * physical[1] / physical[0]
            if name not in self.component.preferred:
                use = self.component.use
                raise self._fail(
                    "no-size", f"{self.trace}: {use} asks for no {name}, and is given none"
                )
            return self.number(f"preferred.{name}", self.component.preferred[name])
        if kind == "value":
            return self.number(f"values.{name}", self.component.values[name])
        if kind == "part":
            return self._geometry(name, cell[2])
        if kind == "lines":
            return self._lines(name)
        if kind == "points":
            return self._mapped_points(name)
        if kind == "end":
            return self._end_frame(name)
        if kind == "anchors":
            return self._anchors()
        if kind == "route":
            return self._route(name)
        return self._arrange(name, kind)

    def number(self, where: str, raw: Any) -> float:
        """The value of the component's formula at a key path. Raises `Fault`."""
        where, _, _ = self.pick(where, raw)
        formula = self.component.formulas.get(where)
        if formula is None:
            raise Fault()  # recorded when the component was read
        try:
            return fm.evaluate(formula, self._read)
        except fm.DivisionByZero as error:
            message = f"{self.trace}: {where} of {self.component.use}: {error}"
            raise self._fail("division-by-zero", message) from error

    def source(self, where: str, raw: Any) -> str:
        """Where a formula's value comes from: the option that chose it, the one role it
        reads, or the component's own default."""
        _, value, chosen = self.pick(where, raw)
        if chosen:
            return source_of_choice(chosen)
        only = _ONLY_ROLE.match(value) if isinstance(value, str) else None
        return f"role:{only.group(1)}" if only else f"default:{self.component.use}"

    def _read(self, ref: fm.Reference) -> float:
        if isinstance(ref, fm.Engine):
            if ref.name in ("width", "height"):
                return self.get("size", ref.name)
            if not self.is_item or self.parent is None:
                message = f"{self.trace}: {self.component.use} reads :{ref.name} but is no item"
                raise self._fail("formula-reach", message)
            drawn = self.parent.nodes[self.part_name].items
            return float(self.position + 1 if ref.name == "index" else len(drawn))
        if isinstance(ref, fm.Role):
            return self.ctx.role_number(ref.path)
        if isinstance(ref, fm.Value):
            return self.get("value", ref.name)
        try:
            return self.measure(ref)
        except _Missing as missing:
            message = f"{self.trace}: {self.component.use} reads `{ref}`: {missing}"
            raise self._fail("missing-exposed", message) from missing

    # -- sizes and places

    def _size(self, size: str) -> float:
        """The size this instance gets: from its parent's part or list, or, at the top,
        the size it asks for. A page of a top whose layouts are its pages' forms gets the
        top's width, and the top's height where the top asks for one, by a formula or
        through its physical size, else the height it asks for (`takes_own`). Such a top
        that asks for no height is as tall as its tallest page (DEC-022 point 3, DEC-034
        point 3). A component its parent's last part places gets, beside its part's size,
        the stretch its parent passes on (`passed_on`)."""
        if self.parent is None:
            if self.component.forms and size == "height" and not self.component.asks_for(size):
                heights = [
                    self.ctx.attempt(lambda p=p: p.get("size", size), 0.0) for p in self.pages
                ]
                return max(heights, default=0.0)
            return self.get("preferred", size)
        if self.takes_own(size):
            return self.get("preferred", size)
        if self._is_forms_page:
            return self.parent.get("size", size)
        if self.tie is not None:
            # A tie is drawn in its part's whole frame (DEC-011 point 1).
            return self.parent.get("part", self.part_name, size)
        if self.is_item:
            part = self.parent.nodes[self.part_name].part
            axis = "main" if size == part.main else "cross"
            return self.parent.get(axis, self.part_name).sizes[self.position]
        placed = self.parent.get("part", self.part_name, size)
        return placed + self.parent.passed_on(self.part_name, size)

    def takes_own(self, size: str) -> bool:
        """Whether this instance is a page of a top whose layouts are its pages' forms that
        takes the `size` it asks for: its height, where the top asks for none, by a formula
        or through its physical size (DEC-022 point 3, DEC-034 point 3). A page always gets
        the top's width."""
        return (
            self._is_forms_page
            and size == "height"
            and self.parent is not None
            and not self.parent.component.asks_for(size)
        )

    @property
    def _is_forms_page(self) -> bool:
        """Whether this instance is a page of a top whose layouts are its pages' forms."""
        parent = self.parent
        return (
            parent is not None
            and bool(parent.component.forms)
            and self.part_name == parent.component.pages_field
        )

    def _stretch(self, size: str) -> float:
        """How much more of `size` a stretch gives this instance than it asks for. An item
        that its list's `align-items: stretch` makes larger across its line than it asks
        for is stretched by the difference. A component its parent's last part places
        takes the stretch its parent passes on (`passed_on`). Nothing else is stretched:
        a size a part's formula gives is no stretch, nor is a page's or a tie's frame."""
        parent = self.parent
        if parent is None or self.tie is not None or self._is_forms_page:
            return 0.0
        if not self.is_item:
            return parent.passed_on(self.part_name, size)
        part = parent.nodes[self.part_name].part
        if size == part.main or parent.setting(self.part_name, "align-items") != "stretch":
            return 0.0
        if not self.component.asks_for(size):
            return 0.0  # it asks for no such size, so none is more than it asks
        return max(self.get("size", size) - self.get("preferred", size), 0.0)

    def passed_on(self, name: str, size: str) -> float:
        """The stretch this instance passes on along `size` to its part `name`: the whole
        of its own (`_stretch`) where that part is the last it draws, places a component
        by `use` or `slot`, and gives no `size`; else none. The component that part places
        then ends where this instance ends, as a panel that holds panels of its own ends
        with the row's other panels. The part's own frame, which this instance's formulas
        read, stays the size it asks for, so what this instance asks for is unchanged."""
        node = self.nodes[name]
        drawn = [each for each, other in self.nodes.items() if other.present]
        if drawn[-1:] != [name] or node.child is None or size in node.part.spec:
            return 0.0  # only a `use` or a `slot` part places a component, its `child`
        return self.get("stretch", size)

    def _geometry(self, name: str, key: str) -> float:
        node = self.nodes[name]
        part, spec = node.part, node.part.spec
        where = f"parts.{name}.{key}"
        if part.kind == "line" and "connect" in spec:
            # A connector's ends are its route's first and last points, and its frame bounds
            # every point of the route (DEC-005 points 2 and 5).
            route = self.get("route", name)
            if key in ENDS_OF_LINE:
                x, y = route[0] if key in ("x1", "y1") else route[-1]
                return x if key in ("x1", "x2") else y
            along = [point[0 if key in ("x", "width") else 1] for point in route]
            return min(along) if key in ("x", "y") else max(along) - min(along)
        if part.kind == "line":
            if key in ("x1", "y1", "x2", "y2"):
                return self.number(where, spec[key])
            ends = ("x1", "x2") if key in ("x", "width") else ("y1", "y2")
            first, second = (self.get("part", name, end) for end in ends)
            return min(first, second) if key in ("x", "y") else abs(second - first)
        if key in ("x", "y"):
            return self.number(where, spec[key]) if key in spec else 0.0
        if not node.present:
            return 0.0
        if part.kind == "text" and not (key == "width" and "width" in spec):
            lines = self.get("lines", name)
            return lines.natural if key == "width" else len(lines.lines) * node.line_height
        if key in spec:
            return self.number(where, spec[key])
        if part.kind == "image" and key == "height" and node.picture is not None:
            pixels = node.picture.variants[first_variant(node.picture)]["pixels"]
            return self.get("part", name, "width") * pixels["height"] / pixels["width"]
        if part.kind == "image" and key == "height" and node.read is not None:
            return self.get("part", name, "width") * node.read.height / node.read.width
        if node.child is not None:
            return node.child.get("preferred", key)
        if part.kind == "repeat" and self.component.ties(part) is not None:
            return self.get("size", key)  # a part of ties takes the component's whole frame
        if part.kind == "repeat":
            return self.get("main" if key == part.main else "cross", name).asked
        raise Fault()  # a size the part needs, recorded when the component was read

    def _lines(self, name: str) -> Broken:
        """A text's lines, broken across its runs (DEC-012 point 4), each run with the sign
        and the ground its part chooses for it, measured with the lengths the foundations'
        roles give them (DEC-036 point 3)."""
        node = self.nodes[name]
        width = self.get("part", name, "width") if "width" in node.part.spec else None
        runs = [
            Run(run.text, run.style, self.run_sign(name, run), self.run_ground(name, run)[0])
            for run in node.runs
        ]
        marks = None
        if any(run.sign is not None or run.ground is not None for run in runs):
            gap, room = (
                self.ctx.attempt(lambda path=path: self.ctx.role_number(path), 0.0)
                for path in (SIGN_GAP, GROUND_ROOM)
            )
            marks = Marks(gap, room)
        return break_runs(runs, width, self.ctx.language, marks)

    def run_sign(self, name: str, run: TextRun) -> str | None:
        """The concept whose sign the text `name` draws before `run`, where it chooses one for
        the run's word, and the run names a concept with a sign (DEC-036 point 3)."""
        part = self.nodes[name].part
        _, value, _ = self.pick(f"parts.{name}.text.sign", part.props.get("sign"), run.word)
        return str(run.concept) if value is True and run.outline is not None else None

    def run_ground(self, name: str, run: TextRun) -> tuple[str | None, str]:
        """The paint the text `name` draws behind `run`, as a role, and where it comes from;
        none where it chooses none for the run's word (DEC-036 point 3)."""
        if "ground" not in self.nodes[name].part.props:
            return None, ""
        return self.ctx.attempt(lambda: self.paint(name, "ground", run), (None, ""))

    def word(self, where: str, raw: Any, default: str) -> str:
        _, value, _ = self.pick(where, raw)
        return value if isinstance(value, str) else default

    def setting(self, name: str, key: str) -> str:
        """A list's operator setting, or its default."""
        part = self.nodes[name].part
        where = f"parts.{name}.{part.operator}.{key}"
        return self.word(where, part.settings.get(key), WORDS[key][0])

    def _arrange(self, name: str, axis: str) -> Arrangement:
        """A list's items laid out along its line (`main`) or across it (`cross`). Along
        it, with `sizes: shares`, the items share the part's size, less the gaps, in
        proportion to the share its list's weight gives each, and equally where every
        share is the same (DEC-010 point 4)."""
        node = self.nodes[name]
        part, items = node.part, node.items
        count = len(items)
        cross = "height" if part.main == "width" else "width"
        size = part.main if axis == "main" else cross
        given = self.get("part", name, size) if size in part.spec else None
        if axis == "cross":
            align = self.setting(name, "align-items")
            stretched = align == "stretch" and given is not None
            asked = None if stretched else [item.get("preferred", size) for item in items]
            line = given if given is not None else max(asked or [0.0])
            sizes = [line] * count if align == "stretch" else list(asked or [])
            shift = {"center": 0.5, "end": 1.0}.get(align, 0.0)
            offsets = tuple((line - each) * shift for each in sizes)
            return Arrangement(offsets, tuple(sizes), max(asked) if asked else line)
        raw = part.settings.get("gap")
        gap = self.number(f"parts.{name}.{part.operator}.gap", raw) if raw is not None else 0.0
        gaps = gap * max(count - 1, 0)
        sharing = self.setting(name, "sizes")
        shares = self._item_shares(name, items) if sharing == "shares" else []
        if sharing == "own":
            sizes = [item.get("preferred", size) for item in items]
        elif given is None:
            how = "equally" if sharing == "equal" else "by its items' weights"
            message = f"{self.trace}/{name}: the list shares its {size} {how}, and is given none"
            raise self._fail("no-size", message, where=f"{self.trace}/{name}")
        elif len(set(shares)) > 1:
            total = sum(shares)
            sizes = [(given - gaps) * share / total for share in shares]
        else:
            sizes = [(given - gaps) / count] * count if count else []
        asked = sum(sizes) + gaps
        free = given - asked if given is not None else 0.0
        justify = self.setting(name, "justify-content")
        if justify == "space-between" and count > 1 and free > 0:
            gap, free = gap + free / (count - 1), 0.0
        at = {"center": free / 2, "end": free}.get(justify, 0.0)
        offsets = []
        for each in sizes:
            offsets.append(at)
            at += each + gap
        return Arrangement(tuple(offsets), tuple(sizes), asked)

    def _item_shares(self, name: str, items: list[Instance]) -> list[float]:
        """The share each item of a list takes of its line: the one its list's weight gives
        the word it carries. A list with no weight, reported when the component was read,
        gives each item the same."""
        listed = self.nodes[name].part.spec["repeat"]
        declared = self.component.list_fields.get(listed)
        weight = declared.weight if declared is not None else None
        if weight is None or weight[1].shares is None:
            return [1.0] * len(items)
        field_name, each = weight
        return [each.shares[item.arranged.get(field_name, each.default)] for item in items]

    def item_frame(self, name: str, position: int) -> tuple[float, float, float, float]:
        """An item's frame within its list's part: x, y, width, height. A tie lies in its
        part's whole frame."""
        if self.component.ties(self.nodes[name].part) is not None:
            return 0.0, 0.0, self.get("part", name, "width"), self.get("part", name, "height")
        main, cross = self.get("main", name), self.get("cross", name)
        along = (main.offsets[position], main.sizes[position])
        across = (cross.offsets[position], cross.sizes[position])
        (x, width), (y, height) = (
            (along, across) if self.nodes[name].part.main == "width" else (across, along)
        )
        return x, y, width, height

    # -- ties (DEC-011)

    def children(self) -> list[Instance]:
        """The instances placed directly below this one: by its drawn parts, its items and
        its pages."""
        found: list[Instance] = []
        for node in self.nodes.values():
            if node.present:
                found.extend([node.child] if node.child else [])
                found.extend(node.items)
        return [*found, *self.pages]

    def below(self) -> Iterator[Instance]:
        """Every instance below this one, at any depth."""
        for child in self.children():
            yield child
            yield from child.below()

    def page(self) -> Instance | None:
        """The page this instance lies on: itself where it is one, else the nearest above;
        None where it lies on none."""
        at: Instance | None = self
        while at is not None and not at.is_page:
            at = at.parent
        return at

    def origin(self, above: Instance) -> tuple[float, float]:
        """This instance's origin in the frame of `above`, an instance above it. Raises
        `Fault`."""
        x = y = 0.0
        at = self
        while at is not above and at.parent is not None:
            parent, part = at.parent, at.part_name
            if parent.component.forms and part == parent.component.pages_field:
                dx = dy = 0.0  # a page lies at its top's origin
            else:
                dx, dy = parent.get("part", part, "x"), parent.get("part", part, "y")
                if at.is_item:
                    frame = parent.item_frame(part, at.position)
                    dx, dy = dx + frame[0], dy + frame[1]
            x, y, at = x + dx, y + dy, parent
        return x, y

    def find_ends(self) -> None:
        """Finds the two ends of each tie drawn at or below this instance, once every part
        is built: first those of the ties each instance below it draws, but its own ties,
        so that what a tie left out there holds counts toward no end here; then those of
        its own ties; then those of the ties below each tie it keeps. Each end is found
        among the instances below this one by the key path of what content gave it
        (`_tie_found`). A tie whose end is not found is left out, and takes no place among
        the ties drawn; `left_out` keeps it, with the ends it found. What lies below this
        instance's own ties still counts while their ends are found, since which of them
        are left out is what that finding decides."""
        for child in self.children():
            if child.tie is None:
                child.find_ends()
        drawn = [
            node
            for node in self.nodes.values()
            if node.present and self.component.ties(node.part) is not None
        ]
        if not drawn:
            return
        index = self.by_path()
        for node in drawn:
            kept = []
            for tie in node.items:
                (kept if self._tie_found(tie, index) else self.left_out).append(tie)
            for position, tie in enumerate(kept):
                tie.position = position
            node.items = kept
        for node in drawn:
            for tie in node.items:
                tie.find_ends()

    def by_path(self) -> dict[str, list[Instance]]:
        """The instances below this one by the key path in the content file of what content
        gave each; an instance no key of the content file gives is in none."""
        index: dict[str, list[Instance]] = {}
        for each in self.below():
            if each.content_path is not None:
                index.setdefault(each.content_path, []).append(each)
        return index

    def _tie_found(self, tie: Instance, index: Mapping[str, list[Instance]]) -> bool:
        """Whether both ends of `tie` are found, each kept in `tie.ends`, and the tie lies on
        one page with them (DEC-011 points 3 and 4). An end the check of the content
        refuses is left out unreported: one of another shape, whose path does not lead to
        an item the content holds, that names a tie, or two ends of which one names the
        other's item or leads through it. An end drawn other than once, a point its item
        does not expose, and a tie off its ends' page are reported in the content, at the
        tie."""
        fields = tie.tie.ends if tie.tie is not None else None
        if fields is None or tie.content_path is None:
            # A tie has no key path only where its list reached the pattern through a `use`
            # part, and such a part passes no list of ties on: `_build_use` reports it, as
            # `component-shape`, and builds no tie of it.
            return False
        named: dict[str, tuple[str, str | None]] = {}
        held: dict[str, str] = {}
        for which in ENDS:
            raw = tie.end_values.get(which)
            if not isinstance(raw, Mapping) or "item" not in raw or set(raw) - set(END_KEYS):
                return False
            point = raw.get("point")
            if point is not None and not names.is_name(point):
                return False
            reached = self._held(raw["item"], index)
            if reached is None:
                return False  # the content holds no such item, or it is a tie
            named[which], held[which] = (raw["item"], point), reached
        if through(named["start"][0], named["end"][0]):
            return False
        for which, field_name in zip(ENDS, fields, strict=True):
            (text, point), at = named[which], _join(tie.content_path, field_name)
            drawn = index.get(held[which], [])
            if len(drawn) != 1:
                self._end_lost(tie, at, text, len(drawn))
                continue
            item = drawn[0]
            part = _point_part(item, point) if point is not None else None
            if point is not None and part is None:
                if _pictured(item):
                    self._end_lost(tie, f"{at}.point", text, 1, point=point, item=item)
                continue  # a picture not found is reported where it is drawn
            place = (part, point) if part is not None and point is not None else None
            tie.ends[which] = TieEnd(item, place, f"{CONTENT}{at}")
        if len(tie.ends) != 2:
            return False
        page = tie.page()
        off = [end.item for end in tie.ends.values() if page is None or end.item.page() is not page]
        if off:
            on = f"on the page `{page.trace}`" if page is not None else "on no page"
            self.ctx.add(
                Finding(
                    "tie-page",
                    FAILS,
                    f"{tie.trace}: the tie lies {on}, and its end `{off[0].trace}` does not: a "
                    "tie is drawn only on one page with both its ends",
                    where=tie.content_path,
                    fix="tie items that lie on the tie's own page, or change the content's "
                    "options; or move the lock to versions that draw them there",
                )
            )
            return False
        return True

    def _held(self, text: Any, index: Mapping[str, list[Instance]]) -> str | None:
        """The key path in the content file of the item an end's key path `text` leads to,
        from this instance's own mapping, `index` holding the instances below it by their
        key paths (`by_path`). None where `text` is no key path or ends at no list's item,
        the content holds no such item, it is a tie, or a step names a key that no
        component on the way declares as a field. A mapping that no instance below draws
        is read by its keys alone. The check of the content walks a path by its own code
        (`checks._Fields._end_path`), and a test runs both on the same paths."""
        steps = key_path(text)
        if not steps or steps[-1][1] is None:
            return None
        mapping: Any = self.given
        path = self.content_path or ""
        reader: Instance | None = self
        tie = False
        for key, item_id in steps:
            if not isinstance(mapping, Mapping):
                return None
            if reader is not None and key not in reader.component.fields:
                return None
            value, path = mapping.get(key), _join(path, key)
            if item_id is None:
                mapping, tie = value, False
            elif not isinstance(value, list):
                return None
            else:
                entry = next(
                    (e for e in value if isinstance(e, Mapping) and e.get("id") == item_id), None
                )
                if entry is None:
                    return None
                listed = reader.component.list_fields.get(key) if reader is not None else None
                tie = listed is not None and listed.ends is not None
                mapping, path = entry, f"{path}[{item_id}]"
            drawn = index.get(path, [])
            reader = drawn[0] if drawn else None
        return None if tie else path

    def _end_lost(
        self,
        tie: Instance,
        where: str,
        text: str,
        count: int,
        *,
        point: str | None = None,
        item: Instance | None = None,
    ) -> None:
        """Reports an end that is not found: its item drawn other than once below this
        instance, or a point its item does not expose (DEC-011 points 4 and 8). It lies in
        the content, at the tie, and names both mends: the content and the lock."""
        if point is not None and item is not None:
            code = "end-point"
            what = f"names the point `{point}`, which `{item.component.use}` does not expose"
        else:
            code = "end-not-found"
            drawn = "nowhere" if count == 0 else f"{count} times"
            what = f"is drawn {drawn} below `{self.trace}`, and an end is found only once"
        self.ctx.add(
            Finding(
                code,
                FAILS,
                f"{tie.trace}: the end `{text}` {what}",
                where=where,
                fix="name an item drawn once on the tie's page, or change the content's "
                "options; or move the lock to versions under which the end is found",
            )
        )

    def _end_frame(self, which: str) -> tuple[float, float, float, float]:
        """The frame of one of this tie's ends in its own frame: the element drawn for the
        end's item, or the point the end names, of no size. Computed from the cells it
        reads, so a loop through it is refused (DEC-011 point 4). Raises `Fault`."""
        end, pattern = self.ends.get(which), self.parent
        if end is None or pattern is None:
            raise Fault()
        x, y = end.item.origin(pattern)
        if end.point is not None:
            part, point = end.point
            try:
                px, py = end.item._point(part, point)
            except _Missing as missing:
                raise self._fail("missing-exposed", f"{self.trace}: {missing}") from missing
            x += end.item.get("part", part, "x") + px
            y += end.item.get("part", part, "y") + py
            width = height = 0.0
        else:
            width, height = end.item.get("size", "width"), end.item.get("size", "height")
        dx, dy = (pattern.get("part", self.part_name, axis) for axis in ("x", "y"))
        return x - dx, y - dy, width, height

    def _anchors(self) -> dict[tuple[int, str], Anchor]:
        """Where each tie this instance draws meets each of its ends, in this instance's
        frame, by the tie and the end: the connector tool's (DEC-005 point 2). A tie leaves
        an end's frame on the side that faces its other end: across, where the two frames
        lie further apart across than down, else down. The ties that meet one side of one
        item spread evenly along it, ordered by where their other ends' centres lie along
        it, then in the order of their lists. A tie ends at a point an end names. A tie
        whose ends cannot be computed has no anchors, and its finding is recorded."""
        frames: dict[Instance, dict[str, tuple[float, float, float, float]]] = {}
        for node in self.nodes.values():
            if node.present and self.component.ties(node.part) is not None:
                for tie in node.items:
                    ends = self.ctx.attempt(lambda t=tie: _shifted(self, t), None)
                    if ends is not None:
                        frames[tie] = ends
        anchors: dict[tuple[int, str], Anchor] = {}
        sides: dict[tuple[int, str], list[tuple[float, int, Instance, str]]] = {}
        for order, (tie, ends) in enumerate(frames.items()):
            across = _across(ends["start"], ends["end"])
            for which, other in zip(ENDS, reversed(ENDS), strict=True):
                if tie.ends[which].point is not None:
                    anchors[(id(tie), which)] = Anchor(*ends[which][:2], None)
                    continue
                side = _side(ends[which], ends[other], across)
                ox, oy, ow, oh = ends[other]
                along = oy + oh / 2 if side in ("left", "right") else ox + ow / 2
                key = (id(tie.ends[which].item), side)
                sides.setdefault(key, []).append((along, order, tie, which))
        for (_, side), members in sides.items():
            members.sort(key=lambda member: (member[0], member[1]))
            for place, (_, _, tie, which) in enumerate(members, start=1):
                x, y, width, height = frames[tie][which]
                share = place / (len(members) + 1)
                if side in ("left", "right"):
                    at = (x if side == "left" else x + width, y + height * share)
                else:
                    at = (x + width * share, y if side == "top" else y + height)
                anchors[(id(tie), which)] = Anchor(at[0], at[1], side)
        return anchors

    def _route(self, name: str) -> list[tuple[float, float]]:
        """The points of the connector the line part `name` draws, in this tie's frame, from
        its start to its end: straight, or with corners, leaving and meeting each end
        square to its side, never around anything (DEC-005 point 2). Raises `Fault`."""
        pattern = self.parent
        if pattern is None or self.tie is None:
            raise Fault()
        found = pattern.get("anchors", "")
        start, end = (found.get((id(self), which)) for which in ENDS)
        if start is None or end is None:
            raise Fault()  # recorded where its ends were computed
        dx, dy = (pattern.get("part", self.part_name, axis) for axis in ("x", "y"))
        (sx, sy), (ex, ey) = (start.x - dx, start.y - dy), (end.x - dx, end.y - dy)
        spec = self.nodes[name].part.spec
        if self.word(f"parts.{name}.connect", spec["connect"], "straight") == "straight":
            return [(sx, sy), (ex, ey)]
        sides = {start.side, end.side} - {None}
        across = bool(sides & {"left", "right"}) if sides else abs(ex - sx) >= abs(ey - sy)
        if across and abs(ey - sy) > TOLERANCE:
            middle = (sx + ex) / 2
            return [(sx, sy), (middle, sy), (middle, ey), (ex, ey)]
        if not across and abs(ex - sx) > TOLERANCE:
            middle = (sy + ey) / 2
            return [(sx, sy), (sx, middle), (ex, middle), (ex, ey)]
        return [(sx, sy), (ex, ey)]

    def attached(self, name: str) -> dict[str, dict[str, str]]:
        """Which element each end of this tie's connector meets, and where: the trace id of
        the element drawn for its item, with the side it meets, or the point it ends at.
        A hint for a medium with connectors of its own (DEC-005 point 5). Raises
        `Fault`."""
        pattern = self.parent
        if pattern is None:
            raise Fault()
        found = pattern.get("anchors", "")
        out = {}
        for which in ENDS:
            end, anchor = self.ends[which], found.get((id(self), which))
            if end.point is not None:
                out[which] = {"id": f"{end.item.trace}/{end.point[0]}", "point": end.point[1]}
            elif anchor is not None and anchor.side is not None:
                out[which] = {"id": end.item.trace, "side": anchor.side}
        return out

    # -- reading the frames below

    def measure(self, path: fm.Path) -> float:
        """A path's measure in this instance's frame. Raises `_Missing` and `Fault`."""
        if path.option in ENDS and self.component.takes_ends:
            if self.tie is None:
                raise _Missing(f"it is given no `{{{path.option}}}`, since it is drawn as no tie")
            x, y, width, height = self.get("end", path.option)
            frame = {"x": x, "y": y, "width": width, "height": height}
            if path.measure in frame:
                return frame[path.measure]
            if path.measure in ("right", "bottom"):
                return x + width if path.measure == "right" else y + height
            return x + width / 2 if path.measure == "center" else y + height / 2
        steps = list(path.steps)
        if path.option:
            steps = self._option_steps(path.option) + steps
        axis = "x" if path.measure in ("x", "width", "right", "center") else "y"
        if path.measure in ("width", "height"):
            return self._extent(steps, axis)
        place = self._position(steps, axis)
        if path.measure in ("x", "y"):
            return place
        share = 1.0 if path.measure in ("right", "bottom") else 0.5
        return place + share * self._extent(steps, axis)

    def _option_steps(self, name: str) -> list[fm.Step]:
        chosen = self.options.get(name)
        if chosen is None:
            raise Fault()  # recorded when the content was read
        option = self.component.options[name]
        steps = [fm.Step(self.component.repeats_over[option.items or ""], chosen["item"], True)]
        return [*steps, fm.Step(chosen["point"])] if option.point else steps

    def _item(self, node: Node, step: fm.Step) -> int:
        items = node.items
        if items and not step.by_id and step.item in ("first", "last"):
            return 0 if step.item == "first" else len(items) - 1
        for position, item in enumerate(items):
            if step.by_id and item.given.get("id") == step.item:
                return position
        raise _Missing(f"the list `{step.name}` draws no item {step}")

    def _position(self, steps: list[fm.Step], axis: str) -> float:
        first, rest = steps[0], steps[1:]
        node = self.nodes[first.name]
        base = self.get("part", first.name, axis)
        if node.part.kind == "repeat" and first.item is not None:
            position = self._item(node, first)
            x, y, _, _ = self.item_frame(first.name, position)
            inner = node.items[position]._exposed_position(rest, axis) if rest else 0.0
            return base + (x if axis == "x" else y) + inner
        if not rest or not node.present:
            return base
        if node.child is not None:
            return base + node.child._exposed_position(rest, axis)
        return base + self._point(first.name, rest[0].name)[0 if axis == "x" else 1]

    def _extent(self, steps: list[fm.Step], axis: str) -> float:
        first, rest = steps[0], steps[1:]
        node = self.nodes[first.name]
        size = "width" if axis == "x" else "height"
        if node.part.kind == "repeat" and first.item is not None:
            item = node.items[self._item(node, first)]
            return item._exposed_extent(rest, axis) if rest else item.get("size", size)
        if not rest:
            return self.get("part", first.name, size)
        if not node.present:
            return 0.0
        if node.child is not None:
            return node.child._exposed_extent(rest, axis)
        self._point(first.name, rest[0].name)
        return 0.0

    def _exposer(self, steps: list[fm.Step]) -> tuple[str, str | None]:
        """What an exposed name reaches: a part, or an exposed image part and its point."""
        step = steps[0]
        if step.name in self.component.exposes:
            return step.name, None
        for name in self.component.exposes:
            node = self.nodes.get(name)
            picture = node.picture if node and node.part.kind == "image" else None
            if picture and step.name in picture.points and step.item is None and len(steps) == 1:
                return name, step.name
        raise _Missing(f"{self.component.use} exposes no part or point `{step}`")

    def _exposed_position(self, steps: list[fm.Step], axis: str) -> float:
        name, point = self._exposer(steps)
        if point is None:
            return self._position(steps, axis)
        return self.get("part", name, axis) + self._point(name, point)[0 if axis == "x" else 1]

    def _exposed_extent(self, steps: list[fm.Step], axis: str) -> float:
        _, point = self._exposer(steps)
        return self._extent(steps, axis) if point is None else 0.0

    def _point(self, name: str, point: str) -> tuple[float, float]:
        points = self.get("points", name)
        if point not in points:
            raise _Missing(f"the picture of `{name}` exposes no point `{point}`")
        return points[point]

    def _mapped_points(self, name: str) -> dict[str, tuple[float, float]]:
        """The picture's exposed points mapped into its part's frame: the picture drawn
        whole, centred, as large as the frame allows."""
        picture = self.nodes[name].picture
        if picture is None:
            return {}
        first = first_variant(picture)
        pixels = picture.variants[first]["pixels"]
        width, height = self.get("part", name, "width"), self.get("part", name, "height")
        scale = min(width / pixels["width"], height / pixels["height"])
        left = (width - pixels["width"] * scale) / 2
        top = (height - pixels["height"] * scale) / 2
        return {
            point: (left + places[first]["x"] * scale, top + places[first]["y"] * scale)
            for point, places in sorted(picture.points.items())
            if first in places
        }

    # -- what is drawn

    def paint(self, name: str, prop: str, run: TextRun | None = None) -> tuple[str | None, str]:
        """A part's paint, as a role, and where it comes from; a text's, for its `run`, by
        the run's word, from the run's family (DEC-012 point 3). `:colour.<member>` paints
        with the role the foundations map that member of the instance's colour family to
        (DEC-004 point 10); an instance with no family, a family the foundations do not
        declare, or one that lacks the member paints nothing. Raises `Fault`."""
        part = self.nodes[name].part
        if name in self.overrides and OVERRIDDEN.get(part.kind) == prop:
            return self.overrides[name]
        word = run.word if run is not None else None
        raw = part.props.get(prop)
        _, value, chosen = self.pick(f"parts.{name}.{part.kind}.{prop}", raw, word)
        if not isinstance(value, str):
            return None, ""
        if chosen and chosen in self.component.runs and run is not None:
            source = run.word_source
        else:
            source = source_of_choice(chosen) if chosen else f"default:{self.component.use}"
        if not value.startswith(FAMILY):
            return value, source
        family = run.family if run is not None else self.family
        family_source = run.family_source if run is not None else self.family_source
        where = f"{self.trace}/{name}"
        if family is None:
            message = f"{where}: paints `{value}`, and has no colour family"
            raise self._fail("no-colour", message, where)
        members = self.ctx.family(family)
        if members is None:
            message = (
                f"{where}: paints `{value}` of the colour family `{family}`, which the "
                "foundations do not declare"
            )
            raise self._fail("no-colour", message, where)
        member = value[len(FAMILY) :]
        if member not in members:
            message = (
                f"{where}: paints `{value}`, and the colour family `{family}` has no "
                f"member `{member}`"
            )
            raise self._fail("no-colour", message, where)
        return members[member], family_source or source

    def unpainted(self, name: str, run: TextRun) -> str | None:
        """Why a run that names a concept shows it in no colour, where it does: the
        `override` its part is pointed by, or its style, which its part paints with a role
        (DEC-012 point 3). None where the run names no concept, or its paint reads its
        family."""
        if run.concept is None:
            return None
        if name in self.overrides:
            return f"the `override` of its part `{name}`"
        part = self.nodes[name].part
        _, value, _ = self.pick(f"parts.{name}.text.fill", part.props.get("fill"), run.word)
        if isinstance(value, str) and value.startswith(FAMILY):
            return None
        return f"its style `{run.word}`" if run.word is not None else "its part's paint"

    def shortfalls(self) -> list[tuple[str, float, float]]:
        """Each size this instance gets that is less than it asks for: size, gets, asks.
        Raises `Fault`."""
        if self.parent is None:
            return []
        short = []
        for size in ("width", "height"):
            if self.component.asks_for(size):
                gets, asks = self.get("size", size), self.get("preferred", size)
                if asks - gets > TOLERANCE:
                    short.append((size, gets, asks))
        return short


def _point_part(item: Instance, point: str) -> str | None:
    """The image part `item` exposes whose picture holds the point `point`, as format 1
    reads an exposed point; None where none does."""
    for name in item.component.exposes:
        node = item.nodes.get(name)
        picture = node.picture if node is not None and node.part.kind == "image" else None
        if node is not None and node.present and picture is not None and point in picture.points:
            return name
    return None


def _pictured(item: Instance) -> bool:
    """Whether every image part of a produced output `item` exposes and draws has its
    picture: where one has none, the missing picture is the finding. A picture file has no
    points, so an end at one is its own finding (DEC-025 point 7)."""
    nodes = [item.nodes.get(name) for name in item.component.exposes]
    return all(
        node.picture is not None
        for node in nodes
        if node is not None
        and node.present
        and node.part.kind == "image"
        and "produced" in node.part.props
    )


def _shifted(pattern: Instance, tie: Instance) -> dict[str, tuple[float, float, float, float]]:
    """The frames of both ends of `tie` in its pattern's frame. Raises `Fault`."""
    dx, dy = (pattern.get("part", tie.part_name, axis) for axis in ("x", "y"))
    frames = {}
    for which in ENDS:
        x, y, width, height = tie.get("end", which)
        frames[which] = (x + dx, y + dy, width, height)
    return frames


def _across(
    first: tuple[float, float, float, float], second: tuple[float, float, float, float]
) -> bool:
    """Whether two frames lie further apart across than down, so a tie between them leaves
    each by its left or right side."""
    (ax, ay, aw, ah), (bx, by, bw, bh) = first, second
    across = max(bx - (ax + aw), ax - (bx + bw))
    down = max(by - (ay + ah), ay - (by + bh))
    return across >= down


def _side(
    frame: tuple[float, float, float, float],
    other: tuple[float, float, float, float],
    across: bool,
) -> str:
    """The side of `frame` that faces `other`: left or right where a tie leaves it across,
    else top or bottom."""
    (x, y, width, height), (ox, oy, ow, oh) = frame, other
    if across:
        return "right" if ox + ow / 2 >= x + width / 2 else "left"
    return "bottom" if oy + oh / 2 >= y + height / 2 else "top"


def place_top(ctx: Context, top: str, content: Mapping[str, Any]) -> Instance | None:
    """The piece's top component placed with its content, every part below it built;
    `None`, with a finding, where the top names no component, or one whose file cannot be
    read (`Context.component`), or a drawing. The piece itself names its top, so the finding
    on a top that names no component, or a drawing, lies there, at `top`, and says so as
    `piece`. Once every tie's ends are found, what each instance a brand's drawing drew
    gives that the drawing does not take is kept in the context (`Instance.misfit`)."""
    trace = top.split("/")[-1]
    component = ctx.component(top)
    if component is None:
        if not ctx.unreadable(top):
            message = f"the piece's top names no component `{top}`"
            ctx.add(
                Finding("unknown-component", FAILS, message, where="top", extra={"piece": True})
            )
        return None
    if component.draws is not None:
        placed(ctx, component, where="top", use="", piece=True)
        return None
    if not component.top:
        ctx.report("not-top", f"the piece's top `{top}` declares no layouts", where=trace, use=top)
    instance = Instance(ctx, component, content, trace=trace, content_path="")
    instance.find_ends()
    for each in (instance, *instance.below()):
        what = each.misfit()
        if what is not None:
            ctx.misfits.setdefault(each.trace, f"`{each.component.use}` does not take {what}")
    return instance


def placed(ctx: Context, drawing: Component, *, where: str, use: str, piece: bool = False) -> None:
    """Reports content, or the component `use`, that places a brand's drawing by `use`
    (DEC-009 points 5 and 9): a drawing draws only in place of its top's own drawing. It
    lies where the drawing is named: in the component `use`, else in the content, or, as
    the piece's top, in the piece."""
    top, layout = drawing.draws or ("", "")
    message = (
        f"{where}: places `{drawing.use}`, a drawing of the layout `{layout}` of `{top}`, which "
        f"draws only in place of the top's own drawing: place `{top}`, or name the layout"
    )
    if piece:
        ctx.add(Finding(DRAWING_PLACED, FAILS, message, where=where, extra={"piece": True}))
    else:
        ctx.report(DRAWING_PLACED, message, where=where, use=use)
