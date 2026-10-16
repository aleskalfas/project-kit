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
          at: 2026-10-13T20:06:25Z
          outcome: unchanged
          unchanged-because: living-docs DEC-001's points are now headings, so the anchor names point 3, which states this rule's property, that a page's anchors ground every statement. Point 3's text is unchanged, so the rule holds.
  RS-LDOC-002:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001#3"]}
        revalidated:
          at: 2026-10-13T20:06:26Z
          outcome: unchanged
          unchanged-because: living-docs DEC-001's points are now headings, so the anchor names point 3, which states this rule's property, that each fact is stated once. Point 3's text is unchanged, so the rule holds.
  RS-LDOC-003:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001#3", "living-docs:DEC-001#4"]}
        revalidated:
          at: 2026-10-13T20:06:27Z
          outcome: unchanged
          unchanged-because: living-docs DEC-001's points are now headings, so the anchors name point 3, which states that each page names its reader, and point 4, which gives a page its `reader` field. Their text is unchanged, so the rule holds.
  RS-LDOC-004:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001#3", "living-docs:DEC-001#4"]}
        revalidated:
          at: 2026-10-13T20:06:28Z
          outcome: unchanged
          unchanged-because: living-docs DEC-001's points are now headings, so the anchors name point 3, which states that pages of a kind follow one format and how a kind's structure is checked, and point 4, which gives a page its `kind` field. Their text is unchanged, so the rule holds.
  RS-LDOC-005:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001#3"]}
        revalidated:
          at: 2026-10-13T20:06:29Z
          outcome: unchanged
          unchanged-because: living-docs DEC-001's points are now headings, so the anchor names point 3, which states this rule's property, that an index-like file is a signpost. Point 3's text is unchanged, so the rule holds.
  RS-LDOC-006:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001#3"]}
        revalidated:
          at: 2026-10-13T20:06:30Z
          outcome: unchanged
          unchanged-because: living-docs DEC-001's points are now headings, so the anchor names point 3, which states this rule's property, that nothing is created ahead of the need for it. Point 3's text is unchanged, so the rule holds.
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
---

# LDOC — the shared documentation method

The rules every documentation space's pages follow, whatever the project ([living-docs:DEC-001-living-docs-discipline] point 3). Each space's definition inherits this set, pinned to its major (`inherits: [living-docs:LDOC@1]`), and adds rules of its own; it never edits or relaxes these (COR-051 point 7). This set takes no scope, so its rules bind on a page only through a set of the project's own whose scope selects the page, such as the page's space definition (DEC-001 points 2 and 3). How rules are named, grounded and inherited is the rule-set record's (COR-051), and where an artefact comes from is carried by its anchors (COR-050), so neither is repeated here.

## RS-LDOC-001 — A page's anchors ground every statement

Every statement a page makes is grounded by the page's anchors: the code it describes, the decisions and rules it applies, the captured sources it quotes, the analysis artefacts it builds on, and the home of each fact it summarises (RS-LDOC-002). The page is anchored, not each sentence, and inline citations are optional where a page mixes sources.

Only what the page anchors grounds a statement.

- **A record the page mentions or cites** but does not anchor grounds nothing. An inline citation tells the reader where a sentence's ground lies, and grounds the sentence only where the page anchors what it cites.
- **Code reached only through a call** from a file the page anchors grounds nothing either.
- **An anchor on one part** of a record or a document grounds only what that part stands on.

A statement that rests on anything else breaks this rule until the page anchors what it rests on.

## RS-LDOC-002 — Each fact has one home

Each fact that pages state has one home: the one page that states it in full. A fact that only one page states has that page as its home.

- **A summary on another page** links to the home. That page anchors to the home's section that states the fact. An anchor on the whole home is not that anchor.
- **A statement of the fact on another page** that lacks the link or the anchor breaks this rule. Whether one with both summarises the home, or states the fact in full again, is a passage for a person to judge.
- **A fact a page states more than once,** each time in agreement, is a passage for a person to judge, not a settled break. This rule leaves to that person whether the repeat serves the page's reader, as an opening summary or a recap may.
- **Two statements of one fact that disagree** break this rule on each page that holds one of them, on one page or on two. Two statements disagree where one says what the other rules out. A statement that leaves out detail the other gives does not disagree with it.
- **A fact that a page of the user space and a page of the technical space both state** has its home on the user space's page, since user-facing navigation never leads into technical material.

## RS-LDOC-003 — Each page names its reader

Each page names its reader, in its `reader` field, and says only what that reader needs.

## RS-LDOC-004 — Pages of a kind follow one format

Pages of a kind follow one format, with a template per kind; a page names its kind in its `kind` field.

## RS-LDOC-005 — An index-like file is a signpost

An index-like file is a signpost to what a folder holds, never a summary of its contents.

## RS-LDOC-006 — Nothing ahead of the need for it

Nothing is created ahead of the need for it.
