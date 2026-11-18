---
rule-set: COMM
version: 2.0.0
rules:
  RS-COMM-001:
    status: proposed
    origin: {decision: "visual-communication:DEC-068"}
    pkit:
      friction:
        anchors: {record: ["visual-communication:DEC-001#3", "visual-communication:DEC-028#3", "visual-communication:DEC-028#4", "visual-communication:DEC-028#6", "visual-communication:DEC-046#2", "visual-communication:DEC-068#10"]}
  RS-COMM-002:
    status: accepted
    origin: {decision: "visual-communication:DEC-028"}
    pkit:
      friction:
        anchors: {record: ["visual-communication:DEC-001#3", "visual-communication:DEC-028#3", "visual-communication:DEC-028#4", "visual-communication:DEC-028#6"]}
  RS-COMM-003:
    status: proposed
    origin: {decision: "visual-communication:DEC-068"}
    pkit:
      friction:
        anchors: {record: ["visual-communication:DEC-001#3", "visual-communication:DEC-028#3", "visual-communication:DEC-028#4", "visual-communication:DEC-028#6", "visual-communication:DEC-068#7"], artefact: ["visual-communication:RS-COMM-001", "visual-communication:RS-COMM-002"]}
  RS-COMM-004:
    status: accepted
    origin: {decision: "visual-communication:DEC-028"}
    pkit:
      friction:
        anchors: {record: ["visual-communication:DEC-001#3", "visual-communication:DEC-028#3", "visual-communication:DEC-028#4", "visual-communication:DEC-028#7"]}
  RS-COMM-005:
    status: accepted
    origin: {decision: "visual-communication:DEC-028"}
    pkit:
      friction:
        anchors: {record: ["visual-communication:DEC-001#3", "visual-communication:DEC-028#3", "visual-communication:DEC-028#4", "visual-communication:DEC-028#7"]}
---

# COMM — what a piece says

The rules on whether a piece of visual work says the right thing, each taken from the canon of its field ([visual-communication:DEC-028-principles-of-visual-communication]). Each rule judges only a piece that explains, as its piece file's `explains` field says (DEC-028 point 3). Each names what can be judged from the content's text, and what only the drawn page shows (DEC-028 point 4).

This set takes no scope. Its rules bind on an artefact only through a set of the project's own that inherits it, pinned to its major, as in `inherits: [visual-communication:COMM@2]` (COR-051 point 7). Where they bind, and how they guide while they bind nothing, is DEC-028 point 5.

## RS-COMM-001 — A page makes one point, and shows it

On a piece whose `explains` field is true, on each page but one whose job is not to make a point, where the page has a lead, its main visual shows the point the lead states, and where it has a title too, the lead answers the title. Where it has no lead, its title states the page's point, and its main visual, where it draws one, shows the title's point.

- **Its title and its lead.** A page's title names what the page is about. Its lead is the sentence under the title that states the page's point, such as what fills a deck's `lead` slot. A figure's caption counts as its lead.
- **Which pages.** A page whose job is not to make a point is one whose job is to open, divide, list, close or stand outside the pages that make the piece's points, such as a cover, an agenda, a section's opening page, a page of references, a page of questions or thanks, or an appendix's divider. Its kind tells it, and it is not judged by this rule. Any other page is judged, whether or not a sentence on it states a point, such as a page that draws a chart, a table or a picture, and a backup page that shows evidence. Such a page breaks the rule where it has no lead, whether its lead slot is empty or its layout has none, unless its title states the page's point.
- **From the text:** which pages the rule judges, by their kind; on each of them, where it has a title and a lead, whether the lead answers the title; where it has no lead, whether its title states the page's point; and whether the main visual's content holds the point its lead or its title states.
- **On the drawn page:** whether the main visual shows that point.

## RS-COMM-002 — The big picture comes first

On a piece whose `explains` field is true, the piece, and each part of it, says what a thing is and why it matters before any detail of it. For something the audience has never seen, the big picture shows it through something they already know.

- **From the text:** whether what the pages say, in their order, gives what a thing is and why it matters before its detail. Also whether a thing new to the audience is shown through one it knows.
- **On the drawn page:** whether each picture shows the whole before its parts.

## RS-COMM-003 — The pages tell the story in order

On a piece whose `explains` field is true and whose pages are read in order, as a deck's are, its pages' statements, read one after another, tell its story. A page's statement is its lead, or its title where it has no lead, as `RS-COMM-001` says what each is. Through each group of pages, the sections and the pages within each section, runs one reasoned order: a deductive order, one of time, of structure or of rank, or a story's, which opens on what is, moves back and forth between what is and what could be, and ends on what the audience is asked to do and what could be. Each statement follows from the one before in that order. A statement that cannot be understood without a later page, a statement whose place that order does not explain, or a section whose place it does not explain, breaks it. A page outside that order, such as an appendix or a backup slide, says so in its content, such as in its title.

- **Which pieces.** A piece of one page, such as a single figure or a poster, is not judged by this rule. Nor is a piece whose reader picks the pages, such as a site.
- **Its groups.** A piece with no sections has one group, its pages. The sections' order is read through the titles of the pages that open them.
- **A page whose job is not to make a point,** as `RS-COMM-001` defines it, stands where its kind does. A page that introduces others, such as a cover or an agenda, stands before them. A section's opening page stands by its kind, before its section's pages, and its title carries the order of the sections, as "Its groups" says. A page that closes others, such as one of questions or thanks, stands after them.
- **A page that sums up** the pages before it stands after them, and breaks nothing by repeating them.
- **What following asks.** A statement follows from the one before where the order that runs through its group places it next. A statement that names something an earlier one named does not follow from it by that alone. A statement that gives an answer before the pages that bear it out, as `RS-COMM-002` asks, can be understood without them, and breaks nothing.
- **From the text:** the whole rule.
- **On the drawn page:** nothing.

## RS-COMM-004 — The words fit the audience

On a piece whose `explains` field is true, the words fit the audience its `audience` field names. They use the terms that audience knows, explain once the ones it does not, and are as plain as that audience needs. The audience of a figure in a documentation page is the reader of its page.

- **From the text:** whether the words of the content fit that audience.
- **On the drawn page:** whether the words in a picture made elsewhere, such as a screenshot, fit it.

## RS-COMM-005 — Each fact names its source

On a piece whose `explains` field is true, each fact the piece shows is true against a source the piece names, on the page or elsewhere in its content. For a number, a quote or a command's output, the source is where it was measured. For a claim of how something works, it is what decides or describes it, such as a record or a file for the project's own system, or a standard or a paper for anything else. Made-up data is marked as an example. A piece marked final holds as of the day it was handed out, and any other piece holds now.

- **From the text:** whether each fact the content states, its values included, is true against the source named for it.
- **On the drawn page:** whether each fact a picture made elsewhere shows, such as a screenshot, is true against the source named for it.
