---
rule-set: LDOC
version: 1.0.0
rules:
  RS-LDOC-001:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001#3"]}
        revalidated:
          at: 2026-10-19T16:10:31Z
          outcome: unchanged
          unchanged-because: living-docs DEC-001 point 3 names the two rules a later major of LDOC brings, a successor of the rule on one home and a rule on text alternatives, and adds diagrams' text alternatives to what validation checks where its rule binds. Its paragraph on what grounds a statement is as it was, only what a page anchors grounds one, so this rule holds.
  RS-LDOC-002:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001#3"]}
        revalidated:
          at: 2026-10-19T16:10:32Z
          outcome: unchanged
          unchanged-because: living-docs DEC-001 point 3 names the two rules a later major of LDOC brings, a successor of the rule on one home and a rule on text alternatives, and adds diagrams' text alternatives to what validation checks where its rule binds. Its passage on a fact's home is as it was until that major, which supersedes this rule, so this rule holds as written meanwhile.
  RS-LDOC-003:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001#3", "living-docs:DEC-001#4"]}
        revalidated:
          at: 2026-10-19T16:10:33Z
          outcome: unchanged
          unchanged-because: living-docs DEC-001 point 3 names the two rules a later major of LDOC brings, a successor of the rule on one home and a rule on text alternatives, and adds diagrams' text alternatives to what validation checks where its rule binds. Its bullet that each page names its reader and says only what that reader needs is as it was, so this rule holds.
  RS-LDOC-004:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001#3", "living-docs:DEC-001#4"]}
        revalidated:
          at: 2026-10-19T16:10:34Z
          outcome: unchanged
          unchanged-because: living-docs DEC-001 point 3 names the two rules a later major of LDOC brings, a successor of the rule on one home and a rule on text alternatives, and adds diagrams' text alternatives to what validation checks where its rule binds. Its bullet that pages of a kind follow one format, with a template per kind, and its paragraph on a kind's structure are as they were, so this rule holds.
  RS-LDOC-005:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001#3"]}
        revalidated:
          at: 2026-10-19T16:10:35Z
          outcome: unchanged
          unchanged-because: living-docs DEC-001 point 3 names the two rules a later major of LDOC brings, a successor of the rule on one home and a rule on text alternatives, and adds diagrams' text alternatives to what validation checks where its rule binds. Its bullet that an index-like file is a signpost to what a folder holds, never a summary of its contents, is as it was, so this rule holds.
  RS-LDOC-006:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001#3"]}
        revalidated:
          at: 2026-10-19T16:10:36Z
          outcome: unchanged
          unchanged-because: living-docs DEC-001 point 3 names the two rules a later major of LDOC brings, a successor of the rule on one home and a rule on text alternatives, and adds diagrams' text alternatives to what validation checks where its rule binds. Its bullet that nothing is created ahead of the need for it is as it was, so this rule holds.
  RS-LDOC-007:
    status: proposed
    origin: {decision: "living-docs:DEC-002"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001#3", "living-docs:DEC-002#3"]}
  RS-LDOC-008:
    status: proposed
    origin: {decision: "living-docs:DEC-002"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-002#8"]}
# The parts of these rules that this capability's validation enforces (COR-051
# point 2; DEC-001 point 6), each only where its rule binds: a reader-review
# leaves them to it and judges the rest.
checks:
  RS-LDOC-003:
    - check: "living-docs:validate"
      part: The page names its reader in its `reader` field, a word that names a reader the readers point holds.
  RS-LDOC-004:
    - check: "living-docs:validate"
      part: The page's body carries the sections its kind's declared structure names, in order where order matters (`schemas/page-kinds.yaml`).
  RS-LDOC-008:
    - check: "living-docs:validate"
      part: Each `mermaid` fence in the page's body carries an `accTitle` and an `accDescr`, each followed by text that is not blank.
---

# LDOC — the shared documentation method

The rules every documentation space's pages follow, whatever the project ([living-docs:DEC-001-living-docs-discipline] point 3). Each space's definition inherits this set, pinned to its major (`inherits: [living-docs:LDOC@1]`), and adds rules of its own; it never edits or relaxes these (COR-051 point 7). This set takes no scope, so its rules bind on a page only through a set of the project's own whose scope selects the page, such as the page's space definition (DEC-001 points 2 and 3). How rules are named, grounded and inherited is the rule-set record's (COR-051), and where an artefact comes from is carried by its anchors (COR-050), so neither is repeated here.

RS-LDOC-007 and RS-LDOC-008 are proposed, and bind nothing yet (COR-051 point 4). A major of this set accepts both, and RS-LDOC-007 then supersedes RS-LDOC-002 ([living-docs:DEC-002-visual-elements] point 10).

## RS-LDOC-001 — A page's anchors ground every statement

Every statement a page makes is grounded by the page's anchors: the code it describes, the decisions and rules it applies, the captured sources it quotes, the analysis artefacts it builds on, and the home of each fact it summarises (RS-LDOC-002). The page is anchored, not each sentence, and inline citations are optional where a page mixes sources.

Only what the page anchors grounds a statement.

- **A record the page mentions or cites** but does not anchor grounds nothing. An inline citation tells the reader where a sentence's ground lies, and grounds the sentence only where the page anchors what it cites.
- **Code reached only through a call** from a file the page anchors grounds nothing either.
- **An anchor on one part** of a record or a document grounds only what that part stands on.

A statement that rests on anything else breaks this rule until the page anchors what it rests on.

## RS-LDOC-002 — Each fact has one home

Each fact a page states has one home for that page.

- **A fact a decision record decides** has the record as its home for a page that anchors the record. The anchor may be on the whole record, or on a part that stands on what decides the fact. The page may state the fact. It needs no link to another page that states it, and no anchor on one.
- **Every other fact a page states** has its home among the pages: the one page that states it in full, or for a decided fact, a page that states it in full. A fact that only one page states has that page as its home.
- **A summary of a fact whose home is a page,** on another page, links to the home. That page anchors to the home's section that states the fact. An anchor on the whole home is not that anchor.
- **A statement of such a fact on another page** that lacks the link or the anchor breaks this rule, however short it is. Words that give the fact state it, a phrase as much as a clause. Whether one with both summarises the home, or states the fact in full again, is a passage for a person to judge.
- **A name,** such as a command's, a page's or a record's, needs no link to a home and no anchor on one. That holds where the name gives none of the named thing's facts.
- **A fact a page states more than once,** each time in agreement, is a passage for a person to judge, not a settled break. This rule leaves to that person whether the repeat serves the page's reader, as an opening summary or a recap may.
- **Two statements of one fact that disagree** break this rule on each page that holds one of them, on one page or on two. Two statements disagree where one says what the other rules out. A statement that leaves out detail the other gives does not disagree with it.
- **A page of the user space** never has a fact's home on a page of the technical space, since user-facing navigation never leads into technical material.

## RS-LDOC-003 — Each page names its reader

Each page names its reader, in its `reader` field, and says only what that reader needs.

## RS-LDOC-004 — Pages of a kind follow one format

Pages of a kind follow one format, with a template per kind; a page names its kind in its `kind` field.

## RS-LDOC-005 — An index-like file is a signpost

An index-like file is a signpost to what a folder holds, never a summary of its contents.

## RS-LDOC-006 — Nothing ahead of the need for it

Nothing is created ahead of the need for it.

## RS-LDOC-007 — Each fact has one home, and a diagram is never it

Each fact a page states has one home for that page, and a diagram is never that home.

- **A home the page anchors.** A fact's home may be something the page anchors that decides or states the fact. The kinds come in this order:
  - an accepted decision record or an accepted rule
  - another artefact in force that is no page, such as an analysis artefact or a section of one
  - a captured source, for what the source it captures says
  - code: a file the software is built or configured from, such as its source, its schemas or its configuration
- **One home among them.** Where the page anchors more than one of them for a fact, the first in that order is the fact's home.
- **Such a home and the page.** The anchor may be on the whole home, or on the part of it that decides or states the fact. The page may state the fact. It needs no link to another page that states it, and no anchor on one.
- **A home under the internal root,** for a page of the user space, is anchored, and the page links nothing under the internal root.
- **Never such a home:** a page, which is a home only among the pages (below), and a diagram in any form, such as a fence, a diagram's source file or an image.
- **Every other fact a page states** has its home among the pages: the one page that states it in full, in prose. A page that does not anchor the home above that holds a fact takes, as that fact's home, a page that states it in full, in prose. A fact that only one page states in prose has that page as its home.
- **A diagram is never a fact's home.** Each fact a diagram shows has its home in what the page anchors, or in prose on a page. A fact that only a diagram states breaks this rule.
- **A diagram of its own page's prose** is a view of that prose, not a second statement of its facts. A diagram of another page's fact is a summary of it, as below.
- **A summary of a fact whose home is a page,** on another page, links to the home. That page anchors to the home's section that states the fact. An anchor on the whole home is not that anchor.
- **A statement of such a fact on another page** that lacks the link or the anchor breaks this rule, however short it is. Words that give the fact state it, a phrase as much as a clause, and so does a diagram that shows it. Whether one with both summarises the home, or states the fact in full again, is a passage for a person to judge.
- **A name,** such as a command's, a page's or a record's, needs no link to a home and no anchor on one. That holds where the name gives none of the named thing's facts.
- **A fact a page states more than once,** each time in agreement, is a passage for a person to judge, not a settled break. This rule leaves to that person whether the repeat serves the page's reader, as an opening summary or a recap may.
- **Two statements of one fact that disagree** break this rule on each page that holds one of them, on one page or on two. A diagram that shows the fact counts as one of them. Two statements disagree where one says what the other rules out. A statement that leaves out detail the other gives does not disagree with it.
- **A page of the user space** never has a fact's home on a page of the technical space, since user-facing navigation never leads into technical material.

## RS-LDOC-008 — A visual element that carries meaning has a text alternative

A diagram, an image or a recording that carries meaning has a text alternative, and a decorative image has an empty one.

- **A Mermaid diagram:** its `mermaid` fence carries an `accTitle`, which names the diagram, and an `accDescr`, which says what it shows. Each is followed by text that is not blank.
- **An image:** its alt text, as in `![alt](path)`, says what the image shows that the page's reader needs. A decorative image has an empty alt text, as in `![](path)`, so a screen reader passes over it. A diagram in another language is shown as an image, and takes an image's alternative.
- **A recording,** an animated image included: an alternative of its own, such as a transcript, or the storyboard it was recorded from.
