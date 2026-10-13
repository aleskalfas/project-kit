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
          at: 2026-10-13T11:36:49Z
          outcome: unchanged
          unchanged-because: "DEC-001 points 2 and 3 say where LDOC binds: through a set of the project's own whose scope selects the page, such as its space's definition, and a check enforces its part only there. Point 4 describes the page's reader and kind fields. None of it changes what this rule asks: a page's anchors ground every statement it makes."
  RS-LDOC-002:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001"]}
        revalidated:
          at: 2026-10-13T11:37:00Z
          outcome: unchanged
          unchanged-because: DEC-001 points 2 and 3 say where LDOC binds, through a scoped set of the project's own such as a space's definition, and point 7 resolves a reader only where the rule on readers binds. Nothing in them touches stating a fact on one page, so each fact is stated once and other pages link to it.
  RS-LDOC-003:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001"]}
        revalidated:
          at: 2026-10-13T11:37:01Z
          outcome: unchanged
          unchanged-because: "DEC-001 point 3 enforces this rule's checked part, the reader field resolving against the readers point, only where the rule binds, and point 4 describes the field. Where the rule binds it asks the same: each page names its reader in its reader field and says only what that reader needs."
  RS-LDOC-004:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001"]}
        revalidated:
          at: 2026-10-13T11:37:02Z
          outcome: unchanged
          unchanged-because: "DEC-001 point 3 checks a page's structure only where this rule binds, through a set of the project's own whose scope selects the page. Where it binds the rule asks the same: pages of a kind follow one format, with a template per kind, and a page names its kind in its kind field."
  RS-LDOC-005:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001"]}
        revalidated:
          at: 2026-10-13T11:37:03Z
          outcome: unchanged
          unchanged-because: DEC-001 points 2 and 3 say where LDOC binds, through a scoped set of the project's own such as a space's definition. They say nothing of what an index-like file tells its reader, so such a file is a signpost to what a folder holds, never a summary of its contents.
  RS-LDOC-006:
    status: accepted
    origin: {decision: "living-docs:DEC-001"}
    pkit:
      friction:
        anchors: {record: ["living-docs:DEC-001"]}
        revalidated:
          at: 2026-10-13T11:37:04Z
          outcome: unchanged
          unchanged-because: DEC-001 point 2 has a space's definition written with its scope, so no scope is written ahead of the definition that needs it, and points 3, 4 and 7 say where LDOC's checks run. None of it creates anything ahead of its need, so nothing is created ahead of the need for it.
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
