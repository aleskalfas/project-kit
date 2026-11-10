---
rule-set: GRAPHIC
version: 1.1.0
rules:
  RS-GRAPHIC-001:
    status: accepted
    origin: {decision: "visual-communication:DEC-028"}
    pkit:
      friction:
        anchors: {record: ["visual-communication:DEC-028#3", "visual-communication:DEC-028#4", "visual-communication:DEC-028#8"]}
  RS-GRAPHIC-002:
    status: accepted
    origin: {decision: "visual-communication:DEC-028"}
    pkit:
      friction:
        anchors: {record: ["visual-communication:DEC-028#3", "visual-communication:DEC-028#4", "visual-communication:DEC-028#8"]}
  RS-GRAPHIC-003:
    status: accepted
    origin: {decision: "visual-communication:DEC-028"}
    pkit:
      friction:
        anchors: {record: ["visual-communication:DEC-028#3", "visual-communication:DEC-028#4", "visual-communication:DEC-028#9"]}
  RS-GRAPHIC-004:
    status: accepted
    origin: {decision: "visual-communication:DEC-028"}
    pkit:
      friction:
        anchors: {record: ["visual-communication:DEC-028#3", "visual-communication:DEC-028#4", "visual-communication:DEC-028#9"], artefact: ["visual-communication:RS-GRAPHIC-007"]}
  RS-GRAPHIC-005:
    status: accepted
    origin: {decision: "visual-communication:DEC-028"}
    pkit:
      friction:
        anchors: {record: ["visual-communication:DEC-001#3", "visual-communication:DEC-028#3", "visual-communication:DEC-028#4", "visual-communication:DEC-028#10"]}
  RS-GRAPHIC-006:
    status: accepted
    origin: {decision: "visual-communication:DEC-028"}
    pkit:
      friction:
        anchors: {record: ["visual-communication:DEC-028#3", "visual-communication:DEC-028#4", "visual-communication:DEC-028#10"]}
  RS-GRAPHIC-007:
    status: accepted
    origin: {decision: "visual-communication:DEC-028"}
    pkit:
      friction:
        anchors: {record: ["visual-communication:DEC-001#6", "visual-communication:DEC-004#10", "visual-communication:DEC-028#3", "visual-communication:DEC-028#4", "visual-communication:DEC-028#9", "visual-communication:DEC-028#10", "visual-communication:DEC-028#11", "visual-communication:DEC-032#3"]}
---

# GRAPHIC — how a piece looks

The rules on whether a piece of visual work looks right, each taken from the canon of its field ([visual-communication:DEC-028-principles-of-visual-communication]). Each rule judges every piece, whatever its purpose (DEC-028 point 3). Each names what can be judged from the content's text, and what only the drawn page shows (DEC-028 point 4). The capability's operational rules are another set, `VIS`, which binds on a session's work, never on a piece.

This set takes no scope. Its rules bind on an artefact only through a set of the project's own that inherits it, pinned to its major, as in `inherits: [visual-communication:GRAPHIC@1]` (COR-051 point 7). Where they bind, and how they guide while they bind nothing, is DEC-028 point 5.

## RS-GRAPHIC-001 — One focal point

Each page has one focal point: what matters most is what is seen first. Size, weight, colour and position rank the rest below it.

- **From the text:** nothing, since what is seen first shows only once the page is drawn.
- **On the drawn page:** the whole rule.

## RS-GRAPHIC-002 — What belongs together is grouped and lined up

What belongs together is placed together and lined up, and what is separate is set apart. Steps are joined in the order they are read.

- **From the text:** whether what belongs together lies in one list or one component, and whether the steps lie in reading order.
- **On the drawn page:** whether those parts stand together and lined up, apart from the rest, and are joined in reading order.

## RS-GRAPHIC-003 — Nothing extra

Everything on a page helps it do its job, and what does not is left out. Decoration never competes with the content.

- **From the text:** whether each part the content places helps the page do its job.
- **On the drawn page:** whether a decoration competes with the content.

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
- **Emphasis** only where the page's point needs it, or its job on a page with no single point.

The strongest of these differences goes to what the page's point is about. Where that point is an order, the parts of the items that show the order do not take each concept's hue: they share one colour, or step in one shade. Each concept an item names keeps its colour on a mark of its own, such as its icon.

- **What it does not judge.** The page's frame, such as its title bar and its footer, and what lies inside a picture made elsewhere, such as a screenshot.
- **From the text:** on a page whose point is an order, whether the content points the parts that show the order at one role, or gives their list the steps of an order with no item naming a concept, rather than each at its concept's.
- **What the text gives the drawn page.** The differences the content has: the order of a list its pattern draws in order, its quantities, the concepts and states it names, and what it marks.
- **On the drawn page:** whether each difference the content has shows as what it is, and whether the page shows one the content lacks.
