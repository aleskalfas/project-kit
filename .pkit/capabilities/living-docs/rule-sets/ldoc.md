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
          at: 2026-10-13T00:44:29Z
          outcome: unchanged
          unchanged-because: DEC-001 now tells a page by the page type, ranks places by the backbone's order, holds assigned places to the definitions' scopes, and names the parts of LDOC that validation enforces. None of it touches what grounds a page's statements, so a page's anchors ground every statement it makes.
  RS-LDOC-002:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001"]}
        revalidated:
          at: 2026-10-13T00:44:30Z
          outcome: unchanged
          unchanged-because: DEC-001 now tells a page by the page type, ranks places by the backbone's order, holds assigned places to the definitions' scopes, and names the parts of LDOC that validation enforces. It says nothing about stating a fact on more than one page, so each fact is stated once and other pages link to it.
  RS-LDOC-003:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001"]}
        revalidated:
          at: 2026-10-13T00:44:41Z
          outcome: unchanged
          unchanged-because: "DEC-001 point 6 names a page naming its reader in its reader field, one the readers point holds, as the part of this rule that validation enforces, and reader-review judges the rest. Point 4 tells a page by the page type. Neither changes what the rule asks: each page names its reader in its reader field and says only what that reader needs."
  RS-LDOC-004:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001"]}
        revalidated:
          at: 2026-10-13T00:44:42Z
          outcome: unchanged
          unchanged-because: "DEC-001 point 6 names a page's sections against its kind's structure as the part of this rule that validation enforces, and point 4 makes the kind field the page type's kind field. Neither changes what the rule asks: pages of a kind follow one format, with a template per kind, and a page names its kind in its kind field."
  RS-LDOC-005:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001"]}
        revalidated:
          at: 2026-10-13T00:44:43Z
          outcome: unchanged
          unchanged-because: DEC-001 now tells a page by the page type, ranks places by the backbone's order, holds assigned places to the definitions' scopes, and names the parts of LDOC that validation enforces. It says nothing of what an index-like file tells its reader, so such a file is a signpost to what a folder holds, never a summary of its contents.
  RS-LDOC-006:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001"]}
        revalidated:
          at: 2026-10-13T00:44:44Z
          outcome: unchanged
          unchanged-because: DEC-001 now tells a page by the page type, ranks places by the backbone's order, holds assigned places to the definitions' scopes, and names the parts of LDOC that validation enforces. It asks for nothing to be created ahead of its need, so nothing is created ahead of the need for it.
# The parts of these rules that this capability's validation enforces (COR-051
# point 2; DEC-001 point 6): a reader-review leaves them to it and judges the rest.
checks:
  RS-LDOC-003:
    - check: "living-docs:validate"
      part: The page names its reader in its `reader` field, a word that names a reader the readers point holds.
  RS-LDOC-004:
    - check: "living-docs:validate"
      part: The page's body carries the sections its kind's declared structure names, in order where order matters (`schemas/page-kinds.yaml`).
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
