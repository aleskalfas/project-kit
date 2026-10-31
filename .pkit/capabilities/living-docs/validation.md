---
reader: act-ai-agent
kind: reference
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/living-docs/scripts/validate.py
        - .pkit/capabilities/living-docs/scripts/_lib/spaces.py
        - .pkit/capabilities/living-docs/scripts/_lib/binding.py
        - .pkit/capabilities/living-docs/scripts/_lib/backbone.py
        - .pkit/capabilities/living-docs/scripts/_lib/artefacts.py
        - .pkit/capabilities/living-docs/scripts/_lib/declarations.py
        - .pkit/capabilities/living-docs/scripts/_lib/readers.py
        - .pkit/capabilities/living-docs/scripts/_lib/formats.py
        - .pkit/capabilities/living-docs/scripts/_lib/mentions.py
        - .pkit/capabilities/living-docs/scripts/_lib/sources.py
        - .pkit/capabilities/living-docs/scripts/_lib/source_layout.py
        - .pkit/capabilities/living-docs/schemas/page.schema.json
        - .pkit/capabilities/living-docs/schemas/page-kinds.yaml
        - .pkit/capabilities/living-docs/schemas/source.schema.json
      record: ["living-docs:DEC-001", "living-docs:DEC-002", COR-023, COR-050, COR-051, COR-056]
      artefact:
        - RS-LDOC-001
        - RS-LDOC-003
        - RS-LDOC-004
        - RS-LDOC-008
        - .pkit/cli/README.md#validate
        - .pkit/cli/README.md#friction-artefacts---at-rev---json
        - .pkit/cli/README.md#rule-sets-reach-path---at-rev---preview---json
        - .pkit/cli/README.md#connections-resolve-address---json
        - .pkit/capabilities/living-docs/pages.md#a-pages-fields
        - .pkit/capabilities/living-docs/pages.md#a-kinds-format
        - .pkit/capabilities/living-docs/pages.md#types
        - .pkit/capabilities/living-docs/pages.md#sources
        - .pkit/capabilities/living-docs/spaces.md#declaring-the-spaces
        - .pkit/capabilities/living-docs/spaces.md#each-definitions-scope
        - .pkit/capabilities/living-docs/spaces.md#the-shared-method-ldoc
        - .pkit/cli/README.md#sync
        - .pkit/cli/README.md#friction-check---base-ref---head-rev---json
---

# Validation

What `pkit living-docs validate` reads, fails on and reports, a page's unanchored mentions included ([living-docs:DEC-001-living-docs-discipline] points 1 to 4 and 6).

## Contents

<!-- pkit:contents -->
- [The command](#the-command)
- [What it reads](#what-it-reads)
- [What fails](#what-fails)
- [What it reports](#what-it-reports)
- [What a page is checked for](#what-a-page-is-checked-for)
- [What a page mentions and does not anchor](#what-a-page-mentions-and-does-not-anchor)
<!-- /pkit:contents -->

## The command

`pkit living-docs validate` checks the project's spaces against the decision. `pkit validate` runs the same check as its `living-docs:spaces` member, and `--json` prints the findings document it reads. It is a query: read-only and offline, and `pkit sync` provisions its dependencies.

## What it reads

It reads where the project's documents are from the core, through `pkit friction artefacts --json`. That is the same discovery `pkit validate` and the friction checks read. The answer holds:

- the documentation roots, the places the configuration and every installed capability declare, and which of them are declared to hold rule sets
- the files each place matches, and each file's front matter
- each document's type, with its matching places in the backbone's order
- the scopes covering each page
- the documents a capability holds that are not artefacts, with their owner

**A held document,** such as an analysis capability's revalidation records, is walked by no place. So it is never an unclassified document. It is claimed by its owner, and counted in the summary as "of another component", wherever it sits under the roots (DEC-001 point 1).

**It never reads the declarations or walks the places itself,** so it can never disagree with the core about which files a place holds. A synced copy, a place outside the repository and a malformed declaration are skipped exactly as the core skips them.

**Nor does it rank the places.** Where places nest, the first root or project place in the backbone's order gives a document its space (COR-056 point 3).

- A place that equals or encloses a root comes after every other.
- Otherwise the longer literal part wins.
- At equal length, an exact file beats a glob, which beats a folder.

**A file that holds no artefact,** with no front matter the backbone reads, comes without ranks. The answer ranks the places of artefacts only.

- **Places that disagree.** Its places may give it different spaces, or one of them may be an unassigned place outside every root. Then which place holds it cannot be told. Validation reports it, and counts it unclassified.
- **Only unassigned places.** Where every one of its places is such an unassigned place, whichever holds it needs an assignment, which fails.

**What it decides over that answer** is this capability's: which space a place serves, and what a document is to the spaces.

**What else it reads:**

- its own project configuration
- where the rules bind, only when there is a page, through `pkit rule-sets reach --json`
- the readers point, only when some page names a reader where `RS-LDOC-003` binds, through `pkit connections resolve`

The core may give no reading of the places, or a reading without each document's type. That is then its one error, and no space is checked.

## What fails

It fails on each of these:

- **The sources folder,** `.pkit/capabilities/living-docs/project/sources/`, or a folder on its path, that is a file or a link. So is one named in another case, such as `Sources/`. No source is read from it, on any disk. It fails too when the folder cannot be read, through a permission or disk error, so no source is checked.
- **An entry of the sources folder that is not a captured source:** a `.yaml` file whose name is not a source's name ([the page on pages, "Sources"](pages.md#sources)), a folder, or a link. An entry whose name begins with `.`, such as `.gitkeep` or an editor's file, is left alone, since no source's name begins with one. A captured source's shape is `schemas/source.schema.json`, which `pkit validate` applies under `data`, bound by the file's path (COR-023).
- **An unassigned place outside every root** that holds a document nothing else claims. A place declared to hold rule sets that gives no type owes no assignment (DEC-001 point 1). For a file without front matter, it fails where every place it lies in is such a place.
- **An assignment** naming a place `friction.places` does not declare, or a space nobody declares, and a place assigned twice.
- **A project place equal to or enclosing a root.**
- **A file two project places claim at equal rank,** ahead of every other place of the spaces, in the backbone's order.
- **A page outside its definition's scope.** Where a space's definition carries a scope, a page an assigned place gives that space outside that scope, or inside another space definition's scope. Where it selects by type, an assigned place outside every root that does not give the page type ([the page on spaces, "Each definition's scope"](spaces.md#each-definitions-scope)).
- **A decision record that would otherwise be a page:** one of the page type, or one that declares its page kind in an untyped project place outside every root. A decision record is never a page. Another owner's document is never read for `reader` or `kind`, so carrying them fails nothing ([the page on pages, "Types"](pages.md#types)).
- **Where the rules bind, unreadable,** when `pkit rule-sets reach --json` gives no answer. That is one error, and no page's structure, reader or diagram is checked.
- **A page's fields.** A page whose `kind` does not fit `schemas/page.schema.json`. Where `RS-LDOC-003` binds on a page, a `reader` it lacks or that does not fit the schema ([the page on pages, "A page's fields"](pages.md#a-pages-fields)).
- **A reader nobody declared.** Where `RS-LDOC-003` binds on a page, a `reader` the readers point does not hold. The message names the readers it does.
- **A page's sections.** A page whose body lacks a section its kind's structure declares, or carries one out of order ([the page on pages, "A kind's format"](pages.md#a-kinds-format)). The message names the page, its kind, the section and the declared structure.
  - It is an error where `RS-LDOC-004` binds on the page.
  - No page is checked that no rule set of the project's reaches, or that is reached only through a pin behind `LDOC`'s major. Nor is any page while the rule is not accepted (COR-051 points 4 and 7).
- **The kinds' structures unreadable.** The declaration of the kinds' structures, `schemas/page-kinds.yaml`, absent, unparsable or not fitting its schema, is one error, "structures unreadable", and no page's body is checked. The file is read only where `RS-LDOC-004` binds on some page, or while the project has no page and the rule is accepted.
- **A body that cannot be read,** where `RS-LDOC-004` binds on a page whose kind declares a structure.
- **A diagram with no text alternative.** Where `RS-LDOC-008` binds on a page, a `mermaid` fence in its body that lacks an `accTitle` or an `accDescr`. Each is followed by text that is not blank. The message names the page and the fence's line.
  - A fence is read as a section's heading is: below the front matter and outside an HTML comment. It is read in a callout or under a list item too.
  - A Mermaid comment, a line that opens with `%%`, holds neither.
  - While the rule is proposed, it binds on no page, and the summary says so.
- **An entry point that is not a document of its space,** under its root or in a place assigned to it. An entry point without front matter whose places cannot be told apart fails only when none of them gives its space.
- **A definition** outside `<definitions>/rule-sets/`, or one that does not inherit `living-docs:LDOC`.

## What it reports

It reports each of these, without failing:

- **Mentions and marks.** Each page whose anchors do not cover what it mentions. Each mark that passes nothing over ("What a page mentions and does not anchor" below).
- **Sources.** A `source` anchor, or a rule origin citing a `source`, that no captured file answers, which the whole-repository check reports dead. A captured source nothing anchors or cites. A captured source carrying `schema_version` or `binds_to`, which its shape permits only for its own carrier. A file in the sources folder whose name does not end in `.yaml`, such as notes or an editor's backup, which captures nothing.
- **Definitions.** A space with no definition yet, and a definition with no scope or with the template's placeholder in its scope. Each report names the scope to give it. The pages of a space its definition's scope leaves out.
- **Places that cannot be told apart.** A file without front matter whose places cannot be told apart. Where every one of them is an unassigned place outside every root, it fails instead ("What fails" above).
- **The roots.** Roots that are the same folder, naming the stamp that sets them apart and the folder it recommends. Roots that are nested, which onboarding separates.
- **A page in an unassigned place of rule sets.** A document that declares its page kind and lies only in an untyped place of rule sets outside every root. No assignment gives that place a space, and the report names the assignment that would make the document a page.
- **Kinds with no structure.** Each kind that declares no structure, with the pages that name it where `RS-LDOC-004` binds, and the kinds that do declare one.
- **A synced tree declared as a place,** which is the core's `synced-place` finding, under `friction`.

**Its summary** holds:

- the unclassified documents, and the documents of a type of the project's own
- whether each entry point is a page yet, and the spaces whose definitions carry a scope
- the readers each page's reader was checked against
- how many pages were checked against their kind's structure, and how many were not because their kind declares none
- how many pages each check left out, because its rule does not bind on them
- the pages left unanchored without an accepted reason, which is onboarding's work still to do
- apart from them, the pages whose friction block gives a reason as `unanchored-because` (DEC-001 point 8, COR-050 point 1)

The human view lists both kinds of unanchored page, each accepted page with its reason. An excluded page is in neither.

## What a page is checked for

Validation checks a page for three things, each where its rule binds:

- **Its front matter:** `kind`, and `reader` against the readers point where `RS-LDOC-003` binds. `pkit validate` checks the friction block under `friction`.
- **Its body's structure,** against the structure its kind declares, where `RS-LDOC-004` binds.
- **Its diagrams' text alternatives,** where `RS-LDOC-008` binds.

These are the parts `LDOC` declares under `checks` ([the page on spaces, "The shared method"](spaces.md#the-shared-method-ldoc)). Everything else a page owes `LDOC` is judgment, left to the agent's reader-review:

- whether each section says what its kind's template asks
- whether the anchors ground every statement
- whether each fact has one home
- whether the page says only what its reader needs

The report below shows the mentions a page's anchors leave uncovered, as input to that judgment.

## What a page mentions and does not anchor

Only what a page anchors grounds what it says (`RS-LDOC-001`). So a page that names a file, a record, a rule or a command it does not anchor is never asked when that thing changes. Where `RS-LDOC-001` binds on a page, validation reports each such mention, and never fails on one (DEC-001 point 6). Each report gives an anchor that would cover the mention.

`pkit validate` shows one report per page, and `pkit living-docs validate` lists each mention with its line:

```
mention(s) a page's anchors do not cover, each with an anchor that would cover it (2):
  docs/guide.md
    12: path `src/app.py` → path: [src/app.py]
    30: record `COR-050#5` → record: [COR-050#5]
```

**What it reads:** the page's body below its front matter, outside fenced code, HTML comments and strikethrough.

- **A path:** an inline code span that holds a `/` and no space, or a link's target, naming a file the repository holds.
  - A code span is read from the repository's root, and failing that from the page's folder.
  - A link is read from the page's folder, or from the root where it opens with `/`.
  - A placeholder such as `<name>`, a glob, an ellipsis, a URL, a folder and an image are not read. A link's `#fragment` names a section.
- **A record:** `COR-NNN`, `PRJ-NNN`, `ADR-NNN`, or a capability's decision.
  - A capability's decision is read as `<capability>:DEC-NNN`, with its slug or without, or as `<capability> DEC-NNN`. A bare `DEC-NNN` is read on a page in that capability's folder.
  - The points written after the id count: `COR-050#5`, `COR-050 point 5`, `COR-050 points 2 and 5`.
  - A link to a record's file mentions the record.
- **A rule:** `RS-<SET>-NNN`, bare or after its component, as in `[living-docs:RS-LDOC-003]`.
- **A command:** an inline code span that opens with `pkit`, or `uv run pkit`, and a word. Its words run to the first that is not a word of lowercase letters, digits and hyphens, so `pkit friction check --base main` is `pkit friction check`.

An id that names no record or rule is not read, and a page never mentions itself.

**What covers each.** A mention is covered by an anchor of the page that stands on what it names:

| Mention | Covered by an anchor on | The finding suggests |
|---|---|---|
| a path | its file: a path anchor standing on it, or an artefact or record anchor on it. For a link with a fragment, the whole file or that section | an `artefact` anchor for a document of the project's places, a `path` anchor otherwise |
| a record | the whole record. For a mention with points, each point it names, and without, any part | `record: [COR-050#5]` |
| a rule | the rule, or its rule set's whole file | `artefact: [RS-LDOC-003]` |
| a command | the script that implements it, or what documents it: the whole file, or the section that names it | that section, by its heading, and the script |

**Marking a passage.** A name that gives none of the named thing's facts needs no anchor (DEC-001 point 3). Where a passage only names a thing, it is marked right after the mention, on its line, with the reason:

```markdown
Run `pkit sync` <!-- unanchored: named as the next step, not described --> after upgrading.
```

- **One passage.** A mark passes over the path, id or command it follows: the last before it on its line, after any earlier comment. A later passage that rests on the same thing is still read.
- **A person's decision.** A mark is written on a person's decision, and the `living-docs` agent proposes one as it proposes any change to a page.
- **A mark that passes nothing over is reported:** one that follows no mention, one that gives no reason, and one after a mention the page's anchors cover. A mark after a file since removed, or a record that no longer exists, follows no mention. It is reported, never moved to an earlier mention.

A page accepted with no anchors (`unanchored-because`) has its mentions read like any other. The report settles no part of `RS-LDOC-001`. Whether a statement rests on what it mentions stays a judgment, the agent's reader-review's and the rule-set reviewer's, so `LDOC` declares no check for it.
