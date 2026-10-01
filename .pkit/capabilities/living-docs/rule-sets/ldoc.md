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
          at: 2026-10-01T23:31:30Z
          outcome: unchanged
          unchanged-because: DEC-001 point 7 keys a reading-evidence entry by page or path, commit and check; executed results are evidence a reader-review may read, not anchors, so a page's anchors still ground every statement it makes
  RS-LDOC-002:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001"]}
        revalidated:
          at: 2026-10-01T23:31:32Z
          outcome: unchanged
          unchanged-because: DEC-001 point 7 keys a reading-evidence entry by page or path, commit and check, so two providers' results stand side by side; that shapes the evidence point's entries, not a page, and each fact is still stated once and linked to
  RS-LDOC-003:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001"]}
        revalidated:
          at: 2026-10-01T23:31:35Z
          outcome: unchanged
          unchanged-because: DEC-001 point 7 keys a reading-evidence entry by page or path, commit and check; the readers point, which a page's reader field names, is untouched, so a page still names the one reader it is for
  RS-LDOC-004:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001"]}
        revalidated:
          at: 2026-10-01T23:31:37Z
          outcome: unchanged
          unchanged-because: DEC-001 point 7 keys a reading-evidence entry by page or path, commit and check; an evidence entry is no page and has no kind, so pages of a kind still follow one format and name their kind
  RS-LDOC-005:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001"]}
        revalidated:
          at: 2026-10-01T23:31:40Z
          outcome: unchanged
          unchanged-because: DEC-001 point 7 keys a reading-evidence entry by page or path, commit and check; nothing about what an index-like file is changes with the evidence point's key, so it is still a signpost to what a folder holds
  RS-LDOC-006:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001"]}
        revalidated:
          at: 2026-10-01T23:31:42Z
          outcome: unchanged
          unchanged-because: DEC-001 point 7 keys a reading-evidence entry by page or path, commit and check, while no filler of the point has shipped; the key is settled before the first one needs it, and nothing is created ahead of that need
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
