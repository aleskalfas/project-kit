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
          at: 2026-10-03T14:01:31Z
          outcome: unchanged
          unchanged-because: DEC-001 point 4 gains the source kind through which a page anchors a source outside the repository, each source captured as one file holding the version read; the rule already counts the captured sources a page quotes among its anchors, so a page's anchors still ground every statement it makes
  RS-LDOC-002:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001"]}
        revalidated:
          at: 2026-10-03T14:01:33Z
          outcome: unchanged
          unchanged-because: DEC-001 point 4 gains how a page anchors a captured source, and keeps what the source says and why a page relies on it on the pages rather than in the captured file; it says nothing about stating a fact in more than one page, so each fact is still stated once and other pages link to it
  RS-LDOC-003:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001"]}
        revalidated:
          at: 2026-10-03T14:01:36Z
          outcome: unchanged
          unchanged-because: DEC-001 point 4 gains how a page anchors a source outside the repository through the source kind; it touches neither the reader field nor the readers point, so a page still names its reader and says only what that reader needs
  RS-LDOC-004:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001"]}
        revalidated:
          at: 2026-10-03T14:01:39Z
          outcome: unchanged
          unchanged-because: DEC-001 point 4 gains how a page anchors a source outside the repository through the source kind, and the shape of a captured source's file; it says nothing of a page's kind, its template or its format, so pages of a kind still follow one format
  RS-LDOC-005:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001"]}
        revalidated:
          at: 2026-10-03T14:01:41Z
          outcome: unchanged
          unchanged-because: DEC-001 point 4 gains how a page anchors a source outside the repository through the source kind; it says nothing of what an index-like file tells its reader, so such a file is still a signpost to what a folder holds, never a summary of its contents
  RS-LDOC-006:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001"]}
        revalidated:
          at: 2026-10-03T14:01:44Z
          outcome: unchanged
          unchanged-because: "DEC-001 point 4 gains how a page anchors a source outside the repository: a source is captured once a page rests on it, and its file records a new version only when someone reads one; that asks for nothing to be created ahead of its need, so nothing is created ahead of the need for it"
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
