---
rule-set: LDOC
version: 1.0.0
rules:
  RS-LDOC-001:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001"]}
        revalidated:
          at: 2026-10-02T20:37:21Z
          outcome: unchanged
          unchanged-because: "DEC-001 point 3 gains a paragraph on a page kind's structure: where it is declared and what validation makes of a departure from it; it concerns the sections a page's body carries, not what grounds the page's statements, so a page's anchors still ground every statement it makes"
  RS-LDOC-002:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001"]}
        revalidated:
          at: 2026-10-02T20:37:23Z
          outcome: unchanged
          unchanged-because: DEC-001 point 3 gains a paragraph on a page kind's structure, declared once with the kind and checked by validation; it says nothing about where a fact is stated, so each fact is still stated once and other pages link to it
  RS-LDOC-003:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001"]}
        revalidated:
          at: 2026-10-02T20:37:25Z
          outcome: unchanged
          unchanged-because: DEC-001 point 3 gains a paragraph on a page kind's structure; a declared structure names the sections a page carries, not its reader, and the reader field and the readers point are untouched, so a page still names its reader and says only what that reader needs
  RS-LDOC-004:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001"]}
        revalidated:
          at: 2026-10-02T20:37:16Z
          outcome: unchanged
          unchanged-because: DEC-001 point 3 says where a kind's structure is declared and what a departure costs; the structure is the checkable part of this rule, whose statement is unchanged
  RS-LDOC-005:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001"]}
        revalidated:
          at: 2026-10-02T20:37:28Z
          outcome: unchanged
          unchanged-because: DEC-001 point 3 gains a paragraph on a page kind's structure; the structure the signpost kind declares asks only for a title and says nothing of what a signpost tells its reader, so an index-like file is still a signpost to what a folder holds, never a summary of its contents
  RS-LDOC-006:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001"]}
        revalidated:
          at: 2026-10-02T20:37:31Z
          outcome: unchanged
          unchanged-because: DEC-001 point 3 gains a paragraph on a page kind's structure; the capability declares a structure only for the two kinds it ships, both of which pages already follow, and a structure names only what every page of the kind must carry, so nothing is created ahead of the need for it
---

# LDOC — the shared documentation method

The rules every documentation space's pages follow, whatever the project ([living-docs:DEC-001-living-docs-discipline] point 3). Each space's definition inherits this set, pinned to its major (`inherits: [living-docs:LDOC@1]`), and adds rules of its own; it never edits or relaxes these (COR-051 point 7). How rules are named, grounded and inherited is the rule-set record's (COR-051), and where an artefact comes from is carried by its anchors (COR-050), so neither is repeated here.

## RS-LDOC-001 — A page's anchors ground every statement

Every statement a page makes is grounded by the page's anchors: the code it describes, the decisions and rules it applies, the captured sources it quotes, the analysis artefacts it builds on. The page is anchored, not each sentence; inline citations are optional where a page mixes sources.

## RS-LDOC-002 — Each fact is stated once

Each fact is stated once, and other pages link to it.

## RS-LDOC-003 — Each page names its reader

Each page names its reader, in its `reader` field, and says only what that reader needs.

## RS-LDOC-004 — Pages of a kind follow one format

Pages of a kind follow one format, with a template per kind; a page names its kind in its `kind` field.

## RS-LDOC-005 — An index-like file is a signpost

An index-like file is a signpost to what a folder holds, never a summary of its contents.

## RS-LDOC-006 — Nothing ahead of the need for it

Nothing is created ahead of the need for it.
