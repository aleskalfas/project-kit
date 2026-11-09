---
rule-set: COMM
version: 1.0.0
rules:
  RS-COMM-001:
    status: accepted
    origin: {decision: "visual-communication:DEC-028"}
    pkit:
      friction:
        anchors: {record: ["visual-communication:DEC-001#3", "visual-communication:DEC-028#3", "visual-communication:DEC-028#4", "visual-communication:DEC-028#6"]}
  RS-COMM-002:
    status: accepted
    origin: {decision: "visual-communication:DEC-028"}
    pkit:
      friction:
        anchors: {record: ["visual-communication:DEC-001#3", "visual-communication:DEC-028#3", "visual-communication:DEC-028#4", "visual-communication:DEC-028#6"]}
  RS-COMM-003:
    status: accepted
    origin: {decision: "visual-communication:DEC-028"}
    pkit:
      friction:
        anchors: {record: ["visual-communication:DEC-001#3", "visual-communication:DEC-028#3", "visual-communication:DEC-028#4", "visual-communication:DEC-028#6"]}
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

This set takes no scope. Its rules bind on an artefact only through a set of the project's own that inherits it, pinned to its major, as in `inherits: [visual-communication:COMM@1]` (COR-051 point 7). Where they bind, and how they guide while they bind nothing, is DEC-028 point 5.

## RS-COMM-001 — A page makes one point, and shows it

On a piece whose `explains` field is true, where a page's layout has a title and a lead, the lead answers the title, and the main visual shows that answer.

- **Its title and its lead.** A page's title names what the page is about. Its lead is the sentence under the title that states the page's point, such as what fills a deck's `lead` slot. A figure's caption counts as its lead.
- **Which pages.** A page whose layout has no lead, such as a cover, the page that opens a section or the questions, is not judged by this rule. A page whose layout has a lead and leaves it empty breaks it.
- **From the text:** whether the lead answers the title, and whether the main visual's content holds that answer.
- **On the drawn page:** whether the main visual shows that answer.

## RS-COMM-002 — The big picture comes first

On a piece whose `explains` field is true, the piece, and each part of it, says what a thing is and why it matters before any detail of it. For something the audience has never seen, the big picture shows it through something they already know.

- **From the text:** whether what the pages say, in their order, gives what a thing is and why it matters before its detail. Also whether a thing new to the audience is shown through one it knows.
- **On the drawn page:** whether each picture shows the whole before its parts.

## RS-COMM-003 — The pages tell the story in order

On a piece whose `explains` field is true and whose pages are read in order, as a deck's are, its leads, read one after another, tell its story. Each follows from the one before. A page outside that order, such as an appendix or a backup slide, says so in its content, such as in its title.

- **Which pieces.** A piece of one page, such as a single figure or a poster, is not judged by this rule. Nor is a piece whose reader picks the pages, such as a site.
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
