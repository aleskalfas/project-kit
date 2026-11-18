---
rule-set: GRAPHIC
version: 3.0.0
rules:
  RS-GRAPHIC-001:
    status: proposed
    origin: {decision: "visual-communication:DEC-068"}
    pkit:
      friction:
        anchors: {record: ["visual-communication:DEC-028#3", "visual-communication:DEC-028#4", "visual-communication:DEC-028#8", "visual-communication:DEC-029#2", "visual-communication:DEC-029#3", "visual-communication:DEC-068#1", "visual-communication:DEC-068#2", "visual-communication:DEC-068#3", "visual-communication:DEC-068#4", "visual-communication:DEC-068#8", "visual-communication:DEC-068#10"], artefact: ["visual-communication:RS-COMM-001", "visual-communication:RS-GRAPHIC-003"]}
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
        anchors: {record: ["visual-communication:DEC-028#1", "visual-communication:DEC-028#3", "visual-communication:DEC-028#4", "visual-communication:DEC-028#9", "visual-communication:DEC-068#4", "visual-communication:DEC-068#6"]}
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
        anchors: {record: ["visual-communication:DEC-001#6", "visual-communication:DEC-004#10", "visual-communication:DEC-028#3", "visual-communication:DEC-028#4", "visual-communication:DEC-028#9", "visual-communication:DEC-028#10", "visual-communication:DEC-028#11", "visual-communication:DEC-032#3", "visual-communication:DEC-046#6", "visual-communication:DEC-068#4", "visual-communication:DEC-068#5"], artefact: ["visual-communication:RS-GRAPHIC-001", "visual-communication:RS-GRAPHIC-003"]}
  RS-GRAPHIC-008:
    status: accepted
    origin: {decision: "visual-communication:DEC-046"}
    pkit:
      friction:
        anchors: {record: ["visual-communication:DEC-028#3", "visual-communication:DEC-028#4", "visual-communication:DEC-046#4"]}
---

# GRAPHIC — how a piece looks

The rules on whether a piece of visual work looks right, each taken from the canon of its field, with its source named in [visual-communication:DEC-028-principles-of-visual-communication], or, for `RS-GRAPHIC-008`, in [visual-communication:DEC-046-faults-lower-grades]. Each rule judges every piece, whatever its purpose (DEC-028 point 3). Each names what can be judged from the content's text, and what only the drawn page shows (DEC-028 point 4). The capability's operational rules are another set, `VIS`, which binds on a session's work, never on a piece.

This set takes no scope. Its rules bind on an artefact only through a set of the project's own that inherits it, pinned to its major, as in `inherits: [visual-communication:GRAPHIC@3]` (COR-051 point 7). Where they bind, and how they guide while they bind nothing, is DEC-028 point 5.

## RS-GRAPHIC-001 — One focal point

Each page that has a title or a lead has a head, its title and its lead where it has them. Each page has one focal point: what bears its point out, or, on a page with no single point, what its job needs most. Where the page's content gives nothing beyond its head that could be its focal point, as on a statement slide, a typographic poster or a cover with nothing but its title, its head is its focal point. The head, the focal point and the action the page asks of its reader stand above the rest of the page, in any order among them, and a part of the rest that ties with one of them breaks the rule. A page with no title and no lead has no head, and the three become two. Size, weight, colour, position and the space around a part rank the rest below them.

- **Its title and its lead.** A page's title is the heading the page's own content gives to name the page, wherever it places it, such as above a picture, below it or beside it: what fills its title slot, or a heading its content sets. A heading names the page where its content gives it to the page as a whole, rather than to one of its sections: a display heading that is a slogan or a greeting, with a sentence under it that states the point, is a title over a lead. The content shows that scope by the heading's role or level, such as the page's first heading level, and by its standing apart from the sections' headings in the content, never by how it is drawn. Its words and its place are evidence of it, and neither alone decides. A small caption set above a page's heading that names what the page belongs to, such as the part of a site or a service it belongs to, is neither its title nor its lead. Text the piece draws the same over every page, such as a site's name in its header, is no title. Where a reader takes a part the piece gives once for every page for a page's opening rather than for a part of the piece met alike on every page, as on a one-page site whose header holds its hero, that part's heading is the page's title. A page has a lead where a sentence under its title states its point, in a lead slot, such as a deck's `lead` slot, or in what its content places there. A layout with no lead slot does not by itself leave a page no lead. A text that states the point elsewhere on the page, such as in a footer, is no lead. A figure's caption counts as its lead. A page with no lead has its title alone as its head. By these words a cover has no lead, since its job is not to make a point, so its subtitle is among the rest.
- **The head as one.** It ranks by its stronger part. Its lead is grouped with the title and read with it. A strip or a ground drawn behind the head is part of it, since a strip or a ground drawn behind some of a page's parts ranks with what it holds, as `RS-GRAPHIC-003` says.
- **The action** is a part the page draws that asks its reader to act, such as a button or a link to sign up. It counts where the page's job, or a goal the brief gives that page, names the act, or, on a piece of one page, a goal the brief gives the piece. On a piece of many pages, a goal of the whole piece is a goal the brief gives a page only where it names that page. A part the piece gives once for every page, such as a link in a site's header, counts by these words too, and is then content, as `RS-GRAPHIC-003` says. Drawn more than once, it ranks by its strongest instance, as the head ranks by its stronger part.
- **The rest** is every other part of the page, such as a label, a decoration, a small caption set above the page's heading, or body text that does not bear the point out. This rule leaves out the page's frame, as `RS-GRAPHIC-003` defines it.
- **One part, one group or one ordered list.** The focal point may be a group the content gives as one: equal parts, such as three equal options or small multiples, or a list whose point is its order, such as the steps of a process, where the page shows that order. Running text that bears the point out, such as an article's body, may be the focal point too.
- **What a focal point holds.** Its own parts, such as the headings that part a running text, a pull quote drawn from it, or a chart's labels, are part of it, not of the rest. A heading against its text breaks nothing here either, as `RS-GRAPHIC-007` says.
- **A page of sections.** Where a reader scrolls through a page, such as a site's page, and its content gives its sections as a list, met one after another, each section is judged as a page of its own, with its heading, and the lead under it where it has one, as its head. The page's head, the heading that names the page wherever its content places it, with the lead under it where it has one, is drawn apart from every other section's head, by size, weight, colour, ground or the space around it, never by its place alone, so that a reader takes it for the page's. It need not stand above those heads. A page none of whose headings names it has no head apart from its sections'. The page's action stands above the rest of each section and above every other action on the page, and need not stand above a section's head or its focal point. A page seen at once, such as a slide, a poster or a figure, is judged whole, sections and all, and has one focal point.
- **Not by the order of reading alone.** A part's place on the page gives it weight of itself, as its size, weight, colour and the space around it do. Where the content ranks its parts, coming first in the order of reading does not by itself make a part the focal point: a part whose only weight is that it stands where reading starts is met first as any part there would be.
- **A page with no single point** is a page whose job is not to make a point, as `RS-COMM-001` defines it, in its words: one whose job is to open, divide, list, close or stand outside the pages that make the piece's points, such as a cover, an agenda, a section's opening page or a page that sums up the pages before it by listing their statements, as text or in a table. Its kind tells it, and a backup page or an appendix page that shows evidence is none, nor a page that sums up the pages before it by drawing evidence, theirs again or its own, such as in a chart, since each makes a point. Any page of a piece that does not explain, such as a map of a system, is one too. Its focal point is what its job needs most: its head, or a part its content gives to carry the page, such as a cover's picture or a section's number. Where that part is the focal point, the head stands above the rest beside it too, in either order.
- **From the text:** nothing.
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
- **The page's frame,** on every piece, of one page or many, is what its layout or its brand draws around each page's content, the same on each page it would lay out, or what the piece gives once for every page, such as the ground under a deck's slides, a running footer, a site's header and footer, or a mark a cover's layout draws by its title, such as a short line. What the piece gives once for every page is frame, though its content places it, but a part of it that holds a page's head, focal point or action, as `RS-GRAPHIC-001` names them, is content. It holds the head where a reader takes it for a page's opening rather than for a part of the piece met alike on every page, as on a one-page site whose header holds its hero: the hero is content, and the header's logo and navigation stay frame. It holds a page's action only where `RS-GRAPHIC-001`'s words count the act it asks as that page's. Elsewhere it stays frame, and this rule judges whether it competes with the content. A ground the layout or the brand draws behind every part of a page is frame. A picture a page's content gives is content wherever it lies, full bleed among them. A strip or a ground drawn behind some of a page's parts ranks with what it holds, though a layout draws it the same on each page, as a strip behind the title and the lead ranks with the head, and a tinted section behind a hero with the hero. What a page's own content fills is content, though it reads the same on each page, such as a slide's footer slot. The frame is judged as any part is: by this rule, by whether it competes with the content, and by each other rule that reaches a part, such as those on alignment, reading and colour. Only `RS-GRAPHIC-001` and `RS-GRAPHIC-007` leave it out.
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
- **Emphasis** where the page's point, or the action the page asks of its reader, needs it, and nowhere else. On a page with no single point, emphasis goes where the page's job needs it, and nowhere else.

The strongest difference in the page's content, apart from its head, goes to what its point is about or to that action, or, on a page with no single point, to what its job needs most, where that part lies outside the head. Where what the point is about, or, on a page with no single point, what its job needs most, lies in its head, as on a statement slide or a cover with nothing but its title, this sentence stands in place of the one before: no part of the rest takes a stronger difference than the head. Where that point is an order, the parts of the items that show the order do not take each concept's hue: they share one colour, or step in one shade. Each concept an item names keeps its colour on a mark of its own, such as its icon.

- **The head, the action, the rest and a page with no single point** are those `RS-GRAPHIC-001` names.
- **A page of sections,** as `RS-GRAPHIC-001` names it, has each section weighed as a page of its own, with its heading, and the lead under it where it has one, as its head. The difference by which the page's head is drawn apart from every other section's head, as `RS-GRAPHIC-001` asks, shows a kind the content has.
- **What a difference is.** A page draws a difference by a visual variable of its marks: their position in the plane, size, value (how light or dark they are), texture, hue, orientation or shape. A reader takes a difference for meaning where it sets some of the parts the content gives as alike apart from the others, such as one item of a list drawn larger than the rest, or one of two parts that name one concept drawn in another hue. A difference between parts the content gives as kinds of their own, such as a heading and its text, or one a component gives every part of its kind alike, shows those kinds, which the content has.
- **What it does not judge.** The page's frame, as `RS-GRAPHIC-003` defines it. What lies inside a picture made elsewhere, such as a screenshot. Whether the head, the focal point and the action stand above the rest in rank, which is `RS-GRAPHIC-001`'s: this rule judges which part the strongest difference goes to.
- **From the text:** on a page whose point is an order, whether the content points the parts that show the order at one role, rather than each at its concept's, or the list of their items is given the steps of an order with no item naming a concept.
- **What the text gives the drawn page.** The differences the content has: the order of a list its pattern draws in order, its quantities, the concepts and states it names, and what it marks.
- **On the drawn page:** whether each difference the page draws is one the content has; whether each difference the content has shows as what it is; and which part the strongest difference in the content goes to. A heading against its text breaks nothing.

## RS-GRAPHIC-008 — Running text is set to be read

Running text is text meant to be read continuously, line after line, such as a paragraph. It is set so that a reader keeps their place. Its lines are neither too long nor too short to read with ease, for its typeface, its size and the number of columns it stands in. The space between its lines suits their length. Where its lines share a straight edge on one side only, their other ends look pleasantly uneven: neither almost straight nor ragged, with no line much longer or shorter than the rest, and forming no regular shape, such as a wedge or a curve.

- **What it does not judge.** A heading, a title, a label, a cell of a table and an item of a list, however many lines each takes. A text whose lines the content breaks, such as code. Placeholder lines that stand for text in a drawing of a screen, and what lies inside a picture made elsewhere. A text in a script written without spaces between words. How short the last line of a paragraph is, since it ends where the text ends. The ends of the lines of a centred text. The gaps between the words of a text set with two straight edges. Which text ranks first, which is `RS-GRAPHIC-001`'s. Whether a kind of text keeps one look, which is `RS-GRAPHIC-004`'s. Whether a text can be read at all where it is shown, which is `RS-GRAPHIC-005`'s.
- **From the text:** nothing, since a line's length and its spacing show only once the page is drawn.
- **On the drawn page:** the whole rule, on each image, so in each language and at each size the piece is drawn in.
