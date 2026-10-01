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
          at: 2026-10-01T23:53:23Z
          outcome: unchanged
          unchanged-because: DEC-001 point 7 now calls whoever reports a reading-evidence result its filler, not a provider, and says nothing in the capability reads the entries; the key is unchanged, and a page's anchors still ground every statement it makes
  RS-LDOC-002:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001"]}
        revalidated:
          at: 2026-10-01T23:53:24Z
          outcome: unchanged
          unchanged-because: DEC-001 point 7 now calls whoever reports a reading-evidence result its filler rather than a provider; the evidence key and the one-check-per-result rule are unchanged, and each fact on a page is still stated once and linked to
  RS-LDOC-003:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001"]}
        revalidated:
          at: 2026-10-01T23:53:25Z
          outcome: unchanged
          unchanged-because: DEC-001 point 7 now says filler, not provider, for whoever reports a reading-evidence result; the readers point that a page's reader field names is untouched, so a page still names the one reader it is for and says only what that reader needs
  RS-LDOC-004:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001"]}
        revalidated:
          at: 2026-10-01T23:53:31Z
          outcome: unchanged
          unchanged-because: DEC-001 point 7 now says filler, not provider, for whoever reports a reading-evidence result; an evidence entry is still no page and has no kind, so pages of a kind still follow one format and name their kind
  RS-LDOC-005:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001"]}
        revalidated:
          at: 2026-10-01T23:53:32Z
          outcome: unchanged
          unchanged-because: DEC-001 point 7 now says filler, not provider, for whoever reports a reading-evidence result; the key and the rule are unchanged, and nothing about an index-like file turns on that wording, so it is still a signpost to what a folder holds
  RS-LDOC-006:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001"]}
        revalidated:
          at: 2026-10-01T23:53:32Z
          outcome: unchanged
          unchanged-because: DEC-001 point 7 now says filler, not provider, for whoever reports a reading-evidence result, and still no filler of the point has shipped; the wording only names who will report, and nothing is created ahead of that need
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
