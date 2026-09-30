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
          at: 2026-09-30T08:02:18Z
          outcome: unchanged
          unchanged-because: DEC-001 point 8 now says an accepted reason for a page with no anchors is the core's unanchored-because, written on a person's decision, and that the measure lists such a page apart without counting it; that onboarding may accept a page with none was already point 8's, and a page's anchors still ground every statement it makes
  RS-LDOC-002:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001"]}
        revalidated:
          at: 2026-09-30T08:02:23Z
          outcome: unchanged
          unchanged-because: DEC-001 point 8 now says an accepted reason for a page with no anchors is the core's unanchored-because, written on a person's decision, and listed apart by the measure; stating each fact once and linking to it is untouched by where and by whom that reason is written
  RS-LDOC-003:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001"]}
        revalidated:
          at: 2026-09-30T08:02:25Z
          outcome: unchanged
          unchanged-because: DEC-001 point 8 now says an accepted reason for a page with no anchors is the core's unanchored-because, written on a person's decision, and listed apart by the measure; a page still names the one reader it is for, anchored or accepted without anchors
  RS-LDOC-004:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001"]}
        revalidated:
          at: 2026-09-30T08:02:27Z
          outcome: unchanged
          unchanged-because: DEC-001 point 8 now says an accepted reason for a page with no anchors is the core's unanchored-because in the friction block, inside the container, written on a person's decision; pages of a kind still follow one format and name their kind in their own fields
  RS-LDOC-005:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001"]}
        revalidated:
          at: 2026-09-30T08:02:29Z
          outcome: unchanged
          unchanged-because: DEC-001 point 8 now says an accepted reason for a page with no anchors is the core's unanchored-because, written on a person's decision, and listed apart by the measure; an index-like file is still a signpost to what a folder holds, whatever it gives for its anchors
  RS-LDOC-006:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001"]}
        revalidated:
          at: 2026-09-30T08:02:31Z
          outcome: unchanged
          unchanged-because: DEC-001 point 8 now says an accepted reason for a page with no anchors is the core's unanchored-because, written on a person's decision when a page has nothing to anchor to, and listed apart by the measure; creating nothing ahead of the need for it holds
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
