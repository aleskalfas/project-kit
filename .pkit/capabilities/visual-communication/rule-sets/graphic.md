---
rule-set: GRAPHIC
version: 3.0.0
rules:
  RS-GRAPHIC-001:
    status: proposed
    origin: {decision: "visual-communication:DEC-068"}
    pkit:
      friction:
        anchors: {record: ["visual-communication:DEC-028#3", "visual-communication:DEC-028#4", "visual-communication:DEC-028#8", "visual-communication:DEC-029#2", "visual-communication:DEC-068#1", "visual-communication:DEC-068#2", "visual-communication:DEC-068#3", "visual-communication:DEC-068#4"]}
  RS-GRAPHIC-002:
    status: accepted
    origin: {decision: "visual-communication:DEC-028"}
    pkit:
      friction:
        anchors: {record: ["visual-communication:DEC-028#3", "visual-communication:DEC-028#4", "visual-communication:DEC-028#8", "visual-communication:DEC-046#2", "visual-communication:DEC-046#3"]}
  RS-GRAPHIC-003:
    status: proposed
    origin: {decision: "visual-communication:DEC-068"}
    pkit:
      friction:
        anchors: {record: ["visual-communication:DEC-028#1", "visual-communication:DEC-028#3", "visual-communication:DEC-028#4", "visual-communication:DEC-028#9", "visual-communication:DEC-030#7", "visual-communication:DEC-068#4", "visual-communication:DEC-068#6"]}
  RS-GRAPHIC-004:
    status: accepted
    origin: {decision: "visual-communication:DEC-028"}
    pkit:
      friction:
        anchors: {record: ["visual-communication:DEC-028#3", "visual-communication:DEC-028#4", "visual-communication:DEC-028#9", "visual-communication:DEC-046#2"], artefact: ["visual-communication:RS-GRAPHIC-007"]}
  RS-GRAPHIC-005:
    status: accepted
    origin: {decision: "visual-communication:DEC-028"}
    pkit:
      friction:
        anchors: {record: ["visual-communication:DEC-001#3", "visual-communication:DEC-028#3", "visual-communication:DEC-028#4", "visual-communication:DEC-028#10", "visual-communication:DEC-046#2", "visual-communication:DEC-046#5"]}
  RS-GRAPHIC-006:
    status: accepted
    origin: {decision: "visual-communication:DEC-028"}
    pkit:
      friction:
        anchors: {record: ["visual-communication:DEC-028#3", "visual-communication:DEC-028#4", "visual-communication:DEC-028#10"]}
  RS-GRAPHIC-007:
    status: proposed
    origin: {decision: "visual-communication:DEC-068"}
    pkit:
      friction:
        anchors: {record: ["visual-communication:DEC-001#6", "visual-communication:DEC-004#10", "visual-communication:DEC-028#3", "visual-communication:DEC-028#4", "visual-communication:DEC-028#9", "visual-communication:DEC-028#10", "visual-communication:DEC-028#11", "visual-communication:DEC-032#3", "visual-communication:DEC-046#6", "visual-communication:DEC-068#4", "visual-communication:DEC-068#5"]}
  RS-GRAPHIC-008:
    status: accepted
    origin: {decision: "visual-communication:DEC-046"}
    pkit:
      friction:
        anchors: {record: ["visual-communication:DEC-028#3", "visual-communication:DEC-028#4", "visual-communication:DEC-046#4"]}
---

# GRAPHIC — how a piece looks

The rules on whether a piece of visual work looks right, each taken from the canon of its field, with its source named in [visual-communication:DEC-028-principles-of-visual-communication], or, for `RS-GRAPHIC-008`, in [visual-communication:DEC-046-faults-lower-grades]. The reasons for the words of `RS-GRAPHIC-001`, `RS-GRAPHIC-003` and `RS-GRAPHIC-007` are [visual-communication:DEC-068-focal-point-in-the-content]'s, the origin of the three. What a page's frame is, which those three rules name, is DEC-068's (point 4). Each rule judges every piece, whatever its purpose (DEC-028 point 3). Each names what can be judged from the content's text, and what only the drawn page shows (DEC-028 point 4). The capability's operational rules are another set, `VIS`, which binds on a session's work, never on a piece.

This set takes no scope. Its rules bind on an artefact only through a set of the project's own that inherits it, pinned to its major, as in `inherits: [visual-communication:GRAPHIC@3]` (COR-051 point 7). Where they bind, and how they guide while they bind nothing, is DEC-028 point 5.

## RS-GRAPHIC-001 — One focal point

Each page has one focal point: what shows its point, the part that bears that point out. The rule ranks the page's content: its title, its lead, what shows the point and the rest. On a page with a title and a lead, the two state the point, and nothing outranks them but what shows the point, or the action the page asks of its reader. Among the rest of the page, what shows the point is seen first, and size, weight, colour and position rank the rest below it.

- **Its title and its lead.** A page's title names what the page is about. Its lead is the text its content gives to state the page's point, such as a slide's lead under its title. No field declares it, so whether a page has one is read from its content alone, never from its layout's slots ([visual-communication:DEC-029-piece-brief] point 2).
- **What may outrank them.** What shows the point, such as a big number, a hero picture or a dominant chart that shows it. The action the page asks of its reader, where its job or its brief's goal names one, such as a landing page's call to sign up. Nothing else, such as a label, a decoration or body text, each where it does not show the point.
- **A band or a ground that holds the title** is judged with the title.
- **A figure.** On a figure with a title, its caption is its lead. On a figure with no title, the caption is judged with the rest.
- **One part, one group or one ordered list.** A group the content gives as one may be the focal point as one: equal parts, such as three equal options, small multiples or the steps of a process, or a list whose point is its order, where the page shows that order.
- **Not by the order of reading alone.** A part's place on the page gives it weight of itself, as its size, weight and colour do. Where the content ranks its parts, coming first in the order of reading does not by itself make a part the focal point: a part whose only weight is that it stands where reading starts is met first as any part there would be.
- **A page where nothing beyond its title and its lead bears the point out,** such as a statement slide or a typographic poster: the two are its focal point, and the rule asks only that nothing outranks them.
- **A page with no lead.** On a page whose content gives no lead, the title is judged with the rest. It may be the focal point itself only where it is the page's content, as on a cover or a section's opening page, or where it states the page's takeaway.
- **A page with no single point,** a page whose content states no point, such as an agenda, an appendix, a page of questions, or any page of a piece that does not explain, such as a map of a system: its focal point is what its job needs most.
- **The page's frame,** as [visual-communication:DEC-068-focal-point-in-the-content] point 4 defines it, is no part of the content, and `RS-GRAPHIC-003` judges it.
- **From the text:** nothing, since what is seen first shows only once the page is drawn.
- **On the drawn page:** the whole rule.

## RS-GRAPHIC-002 — What belongs together is grouped and lined up

What belongs together is placed together and lined up, and what is separate is set apart. Steps are joined in the order they are read.

- **From the text:** whether what belongs together lies in one list or one component, and whether the steps lie in reading order.
- **On the drawn page:** whether those parts stand together and lined up, apart from the rest, and are joined in reading order.

## RS-GRAPHIC-003 — Nothing extra

Everything on a page helps it do its job, and what does not is left out. Decoration never competes with the content.

- **Decoration** is what a page draws that carries none of its content: it shows no part of the content, and groups, parts or marks nothing the content gives. It is decoration whether the piece draws it or a component does, such as a component's lines, fills and borders.
- **Louder than its job.** A part that carries content but is drawn louder than its job needs, such as a heavy grid or border, competes as decoration does.
- **The piece's identity.** Marking whose piece it is, such as by a brand's mark, is part of a page's job, where the mark does not compete with the content.
- **The page's frame,** as [visual-communication:DEC-068-focal-point-in-the-content] point 4 defines it, such as a footer, a page number or a site's shared header, is judged by this rule alone, as any part is: by whether it competes with the content.
- **The page as drawn.** The rule judges the page a reader meets, whatever drew each part of it.
- **From the text:** whether each part the content places helps the page do its job.
- **On the drawn page:** whether a decoration, a part drawn louder than its job needs, or the frame competes with the content.

## RS-GRAPHIC-004 — The same meaning looks the same

The same meaning looks the same everywhere. A concept keeps the colour, icon and shape its notation gives it. Where a library has a component for the job, the piece uses it rather than drawing its own. A new message may look new, and is not forced into the picture of the one before.

- **Beside an order.** On a page whose point is an order, `RS-GRAPHIC-007` says which parts of an item keep its concept's colour.
- **From the text:** whether the content names a library's component for each job one does, rather than a local component.
- **On the drawn page:** whether one meaning looks the same on every page, and whether a new message is forced into the picture of the one before.

## RS-GRAPHIC-005 — Readable where it is shown

Everything on a page can be read where the piece is shown, as its `shown` field names, such as projected in a room, on a screen, or printed. A page is taken in at a glance.

- **From the text:** whether a page holds more text than can be taken in at a glance there.
- **On the drawn page:** whether everything on the page can be read there, and the page taken in at a glance.

## RS-GRAPHIC-006 — Colour is never the only signal

Colour is never the only signal. Whatever a colour tells apart is also told by a label, an icon, a shape or a line style.

- **From the text:** whether each concept and state the content names has a label, an icon, a shape or a line style beside its colour, from its notation, its component or the content itself.
- **On the drawn page:** whether each difference of colour is also told another way.

## RS-GRAPHIC-007 — The form says what the content says

Every difference a reader takes for meaning is one the content has, and every difference the content has shows as what it is:

- **An order** by position, size, numbering or arrows, and by steps of one shade only beside one of them.
- **A quantity** by position or length, or by angle or area where neither serves.
- **Kinds** by hue, with a label, an icon, a shape or a line style.
- **Emphasis** where the page's point needs it, and nowhere else. On a page with no single point, emphasis goes where the page's job needs it, and nowhere else.

The strongest difference in the page's content, apart from its title and its lead, goes to what its point is about, or, on a page with no single point, to what its job needs most. Where that point is an order, the parts of the items that show the order do not take each concept's hue: they share one colour, or step in one shade. Each concept an item names keeps its colour on a mark of its own, such as its icon.

- **What a difference is.** A page draws a difference by a visual variable of its marks: their position in the plane, size, value (how light or dark they are), texture, hue, orientation or shape. A reader takes a difference for meaning where it sets some of the parts the content gives as alike apart from the others, such as one item of a list drawn larger than the rest, or one of two parts that name one concept drawn in another hue. A difference between parts the content gives as kinds of their own, such as a heading and its text, or one a component gives every part of its kind alike, shows those kinds, which the content has.
- **What it does not judge.** The page's frame, as [visual-communication:DEC-068-focal-point-in-the-content] point 4 defines it, such as a footer or a page number, since its differences are the layout's or the brand's, and carry none of the content's. What lies inside a picture made elsewhere, such as a screenshot. Whether what shows the point is seen first, which is `RS-GRAPHIC-001`'s.
- **From the text:** on a page whose point is an order, whether the content points the parts that show the order at one role, rather than each at its concept's, or the list of their items is given the steps of an order with no item naming a concept.
- **What the text gives the drawn page.** The differences the content has: the order of a list its pattern draws in order, its quantities, the concepts and states it names, and what it marks.
- **On the drawn page:** whether each difference the page draws is one the content has; whether a difference a reader would take for meaning sets apart parts the content gives as alike; whether each difference the content has shows as what it is; and which part the strongest difference in the content goes to. A heading against its text breaks nothing.

## RS-GRAPHIC-008 — Running text is set to be read

Running text is text meant to be read continuously, line after line, such as a paragraph. It is set so that a reader keeps their place. Its lines are neither too long nor too short to read with ease, for its typeface, its size and the number of columns it stands in. The space between its lines suits their length. Where its lines share a straight edge on one side only, their other ends look pleasantly uneven: neither almost straight nor ragged, with no line much longer or shorter than the rest, and forming no regular shape, such as a wedge or a curve.

- **What it does not judge.** A heading, a title, a label, a cell of a table and an item of a list, however many lines each takes. A text whose lines the content breaks, such as code. Placeholder lines that stand for text in a drawing of a screen, and what lies inside a picture made elsewhere. A text in a script written without spaces between words. How short the last line of a paragraph is, since it ends where the text ends. The ends of the lines of a centred text. The gaps between the words of a text set with two straight edges. Which text ranks first, which is `RS-GRAPHIC-001`'s. Whether a kind of text keeps one look, which is `RS-GRAPHIC-004`'s. Whether a text can be read at all where it is shown, which is `RS-GRAPHIC-005`'s.
- **From the text:** nothing, since a line's length and its spacing show only once the page is drawn.
- **On the drawn page:** the whole rule, on each image, so in each language and at each size the piece is drawn in.
