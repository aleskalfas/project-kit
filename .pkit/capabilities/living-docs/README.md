---
reader: user
kind: reference
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/living-docs/scripts/**
        - .pkit/capabilities/living-docs/schemas/**
        - .pkit/capabilities/living-docs/agents/**
        - .pkit/capabilities/living-docs/templates/**
        - .pkit/capabilities/living-docs/skills/**
      record: ["living-docs:DEC-001", COR-005, COR-023, COR-049, COR-050, COR-051, "COR-052#4", COR-053, COR-056]
      artefact: [RS-LDOC-001, RS-LDOC-002, RS-LDOC-003, RS-LDOC-004, RS-LDOC-005, RS-LDOC-006, ".pkit/schemas/README.md#the-friction-block"]
    revalidated:
      at: 2026-10-17T15:21:34Z
      outcome: unchanged
      unchanged-because: "COR-051 point 6 now names a capability's install, and its migration for an earlier install, as writers of the one project rule set a capability declares. living-docs declares none: its spaces' definitions are written by its own command, as its DEC-001 point 2 names it, and this page describes that, unchanged."
---

# living-docs capability

Keep your documentation **true for the people who read it**, even when an agent writes most of it. Documentation is organised into spaces by audience: user-facing docs for people who use the system, and technical docs for the people and agents who build it. Every page names its reader and is anchored to what makes it true. When those anchors change, drift is detected, and an agent proposes the fix for a person to review. The rule is in [living-docs:DEC-001-living-docs-discipline].

## How it works

- **Spaces.** A user space and a technical space, kept separate: neither root lies inside the other. You can add others. New pages go under each space's root. A space can also include places the project declares — inside a root, where they inherit that root's space, or outside every root, such as the repo's top-level README, where the capability's project configuration assigns them to a space. Where places nest, the backbone's order of places decides which one gives a page its space. A page is a document of this capability's page type ([Pages](#pages)). Decision records, rule sets, templates and anything another owner claims — by its type, by its place, or by a folder of documents it holds, such as an analysis capability's revalidation records — are anchor targets or their owner's, never pages. Each space's *definition* (its rules) lives in the technical space.
- **Rules.** The shared method rule set, `LDOC`, ships with this capability. Each space's definition inherits it, adds its own rules, and carries a scope that selects the space's pages. `LDOC`'s rules bind on a page only through such a scope (core rule sets, COR-051).
- **Anchors and friction.** Each page's anchors (code, decisions, [sources](#sources), analysis artefacts, the home of each fact it summarises) must ground everything it says. The core friction check (COR-050) flags a page when any of those changed and nobody revalidated it. When two branches revalidate the same page, its block conflicts on merge, and whoever resolves the conflict revalidates the page as merged: when you merge the check's base into your branch and the conflict lies only in the block, `pkit friction resolve` takes the base side's answer, keeps both sides' deferrals, and names the revalidation still owed (the CLI README, "friction resolve").
- **Proposals, never blind edits.** The agent, `living-docs` ("The agent" below), proposes each fix with its evidence, and a person reviews it.
- **Reader-review.** The agent reads a page as its declared reader and reports what that reader would miss or wouldn't need.

## Pages

A document is a **page** when it is of this capability's page type, `living-docs:page` ([Types](#types), below). Mostly, that means it lies in a documentation root, or in a place of yours that holds pages, and declares its page kind in `kind`. A page's front matter carries two fields of its own, beside the core's friction block in the `pkit:` container:

```yaml
---
reader: user          # who the page is for: an id of the readers point (user, maintainer, …)
kind: signpost        # the page's kind: the template it follows
pkit:
  friction:
    anchors: { path: [src/cli/**], record: [ADR-006] }
---
```

`reader` and `kind` are each a word (`[a-z][a-z0-9-]*`); their shape is `schemas/page.schema.json`, which the validator below applies: to `kind` on every page, and to `reader` where `RS-LDOC-003` binds. The friction block is the core's, and `pkit validate` checks it under `friction`. A document in a space's places that is no page, no decision record and no rule-set file, and that no other owner claims, is an *unclassified document*: counted for onboarding to classify, never failed. A document that names a reader but declares no kind is one.

**Anchoring one part.** A page that rests on one part of a record or of another document may anchor that part, so that a change to another point or section of it asks the page nothing (COR-050 point 5). How an anchor names a part is in [the schemas reference, "The friction block"](../../schemas/README.md#the-friction-block): a record's point as `COR-050#2`, a document's section by its heading's slug as `docs/cli.md#output`, and its lead as `docs/cli.md#`. A path and a `source` name no part. An anchor on one part grounds only what that part stands on (`RS-LDOC-001`), and a summary of a fact whose home is another page anchors the home's section (`RS-LDOC-002`).

**A kind's structure.** Pages of a kind follow one format (`RS-LDOC-004`). A kind's template is the starting shape you fill in; the part of the format the validator checks is the kind's *structure*: the sections every page of the kind carries, in order where order matters. Each kind this capability ships declares its structure once, in `schemas/page-kinds.yaml`, and that file is where to read what a kind's pages must carry: each section is a heading level and, where the kind fixes the wording, its text, in the order listed unless the kind sets `ordered: false`. A structure names only what every page of the kind must carry, so a template may show more, and a page may carry other sections.

A section is a heading written with one to six `#` at the start of a line. These are not read as one: a `#` line that is indented (under a list item, say) or that lies inside a block quote, fenced code or an HTML comment; an underlined (setext) heading; an HTML heading (`<h1>`). A section the kind leaves you to word needs words of its own, so an empty `#` and a template's unfilled `<placeholder>` do not count; fixed text is compared ignoring case, runs of white space and trailing punctuation. Where `RS-LDOC-004` binds on a page whose kind declares no structure — a kind your project adds, say — the page is reported with its kind and never failed.

### Types

The capability declares two types in its package metadata, under `friction.types` (DEC-001 points 2 and 4, COR-056). The backbone gives each document its type from the places that match it, and the validator reads that answer. A rule set's scope can select pages by their type, `types: [living-docs:page]`.

| Type | What it is | Kind field | On your own places |
|---|---|---|---|
| `living-docs:page` | a page of a documentation space | `kind` | admitted |
| `living-docs:template` | a writer's tool in the definitions location, never a page | none | not admitted |

- **The roots give the page type.** Each documentation root is a place of the capability's that gives `living-docs:page`. A document there takes the type only when it declares its page kind in `kind`, present and not empty. One that declares none takes no type and is no page.
- **The definitions location gives the template type.** It ranks ahead of the internal root, so a page template you copy there is a template, never a page, though it carries `reader` and `kind`. The definitions there are rule sets, and every rule takes the backbone's type for rules.
- **Your places outside the roots.** Give one the page type by writing it `{path: CONTRIBUTING.md, type: living-docs:page}` in `friction.places`. A place you leave untyped holds the pages that declare their kind there. They have no type, so a scope that selects by type misses them. Type such a place before a definition selects pages by type ([Declaring your spaces](#declaring-your-spaces)).
- **A type of your own.** A place inside a root that gives a type of your own, such as `{path: docs/changes, type: change-note}`, ranks ahead of the root. Its documents are yours, and their `kind` is never read as a page kind.
- **Another owner's documents.** A document of another component's type is that component's. So is one it holds in a folder it declares, and one of no type in a place it declares. The validator never reads their `reader` or `kind`. A place another component declares without a type shadows no other place (COR-056 point 3). So a document there that declares a page kind takes the page type from the root around it, and is a page. `pkit validate` reports, under `packages`, that the root typed the component's file. The component keeps such documents by typing its place.
- **A decision record that would otherwise be a page** fails validation: one of the page type, or one of no type that declares its page kind in an untyped place of yours outside the roots. A decision record is never a page. The validator reads a document's `id` only to tell a decision record.
- **A tie.** Where two typed places rank equal and give different types, the document counts as each (COR-056 point 3). One that counts as the page type is a page until the tie is mended, whatever other type it counts as.
- **Where to read it.** `pkit friction artefacts --json` gives each document its `type`, the place that gave it, and its matching places in the backbone's order.

## Sources

A page that rests on something outside the repository — a standard, a specification, another project's documentation — anchors it with the `source` kind, by the source's name:

```yaml
pkit:
  friction:
    anchors:
      path: [src/release/**]
      source: [keep-a-changelog]
```

**Capture each source once.** The friction checks read the repository alone and never reach the network, so each source is captured in a file of its own, `.pkit/capabilities/living-docs/project/sources/<name>.yaml`:

```yaml
# yaml-language-server: $schema=../../schemas/source.schema.json
title: Keep a Changelog
url: https://keepachangelog.com/en/1.1.0/
version: "1.1.0"
```

- `title` — what the source is called. Required.
- `url` — where it is found. Optional: a printed standard has none.
- `version` — which text of the source your pages were last checked against, as the source labels that text: its version, edition or revision. For Keep a Changelog that is the document's `1.1.0`, not the release its own changelog has reached. For a source that labels none, name the exact text another way, such as a commit of the repository it is published from. Only when nothing names it, write the date you read it, `YYYY-MM-DD` — which records when, not what, so a later reader has nothing to compare it with. Quote it: YAML reads `1.1` as a number and `2026-10-03` as a date, and the shape wants text. Required.

Write nothing else. The file is bound to its shape (`schemas/source.schema.json`) by its path, so it needs no `pkit_schema`. A `schema_version` would make any later version of the shape rewrite every captured source. If you want the editor directive comment, write it when you create the file. The name is lower-case words of letters and digits joined by single hyphens, starting with a letter, at most 64 characters (`rfc-9110`, `iso-8601`, `owasp-top-10`), so one name is one file on any disk. It cannot start with a digit (`twelve-factor-app`) or hold a dot; a version belongs in the file, not the name. Who captured a source, and when each version was recorded, is git's to say.

**What counts as the source changing: any change to its file, nothing else.** That is why the file holds only these fields: describe the source, and say why a page relies on it, on the page. Recording a new version, or correcting the title or the address, is then the only edit the file has reason to see, and each asks every page anchored to the source for its answer — updated, unchanged with its reason, or deferred. Other edits ask them too: a comment added later; a reformat (a repository-wide YAML formatter or line-ending change asks every source-anchored page at once); `1.1` rewritten as `1.1.0`. A new version asks every page resting on any part of the source. To narrow that, capture the parts you rely on separately (`owasp-top-10-a01`), knowing that nothing keeps their versions in step.

**Recording a new version.** When you read a new version of a source, edit `version` — and `url` if the address moved — in a pull request; the change check asks every page anchored to the source to answer in the same pull request. A change to the source that nobody records is not seen: nothing fetches it.

**Dead, or no answer.** A name no file captures is a dead anchor: the change check fails it where the pull request adds it, the whole-repository check reports it, and `pkit validate` reports it under `living-docs:spaces` without failing. Commit a source's file with the page that first anchors it: a file only your working tree holds is no answer to a check that reads HEAD. If where sources are kept cannot be read — a permission or disk error — the resolver gives no answer: the page is not judged, and the documentation check reports itself unresolved until a run succeeds (Connections, below).

**Rule-set origins** may cite a captured source as where a rule's words were said: `origin: {…, source: {kind: source, value: keep-a-changelog}}` (COR-051 point 5).

**Uninstalling living-docs** removes its project tier — captured sources with it; they stay in git history — and leaves every `source` anchor with no resolver. Remove those anchors in the same change: where friction is enforced, the change check fails a pull request that keeps them while taking their resolver away.

`pkit living-docs resolve-source <name>` prints the file a name resolves to. It is the resolver the friction checks run (`--json` prints `{"paths": [...]}`).

## The shared method: `LDOC`

`rule-sets/ldoc.md` is a method rule set (COR-051), cited `living-docs:LDOC`. Its rules are those point 3 of the decision states, each accepted, with the decision as its origin and its anchor:

| Rule | Statement |
|---|---|
| `RS-LDOC-001` | A page's anchors ground every statement it makes, and only what the page anchors grounds one. |
| `RS-LDOC-002` | Each fact has one home. For a page that anchors a decision record, the record is the home of the facts it decides. The page may state them with no link to another page. A page states a fact whose home is another page only as a summary that links to the home and anchors to its section, however short. A name that gives none of a thing's facts needs neither. |
| `RS-LDOC-003` | Each page names its reader and says only what that reader needs. |
| `RS-LDOC-004` | Pages of a kind follow one format, with a template per kind. |
| `RS-LDOC-005` | An index-like file is a signpost to what a folder holds, never a summary of its contents. |
| `RS-LDOC-006` | Nothing is created ahead of the need for it. |

You never edit `LDOC`; a space's definition inherits it, pinned to its major (`inherits: [living-docs:LDOC@1]`), and `pkit validate` tells you when a new major arrives. Rules about how rules are named and inherited are the core's (COR-051), so they are not repeated here.

**Where `LDOC` binds.** `LDOC` takes no scope, as no shipped rule set does, so its rules bind on a page only through a rule set of yours whose scope selects the page (DEC-001 points 2 and 3; COR-051 point 7). That set is the page's space definition, or a documentation rule set of yours that inherits `LDOC`. A page that no such scope selects is bound by none of `LDOC`'s rules. Neither is a page reached only through a pin behind `LDOC`'s major. So each definition's pin decides when a new major of `LDOC` starts binding on its space's pages. `pkit rule-sets reach` lists the rules that bind on each page.

**What validation settles.** `LDOC` declares, under `checks`, the parts of its rules that this capability's validator, `living-docs:validate`, enforces (COR-051 point 2, DEC-001 point 6):

- `RS-LDOC-003`: the page names its reader in its `reader` field, one the readers point holds.
- `RS-LDOC-004`: the page's body carries the sections its kind's structure declares, in order where order matters.

The agent's reader-review leaves those parts to the validator and judges the rest of each rule. A declaration is no part of a rule's content, so it flags nothing anchored to the rule. `pkit rule-sets reach` lists each part on the rule wherever `LDOC` binds. The validator checks each part only on the pages where its rule binds, as that answer gives it: a page's sections where `RS-LDOC-004` binds, and its reader where `RS-LDOC-003` binds. On any other page it reads neither.

## Templates

`templates/` holds the writers' tools:

- **`space-definition.md`** — a space's definition: a project rule set that inherits `LDOC`, carries a scope that selects the space's pages, and holds the space's own rules, each carrying its friction block in its own container. `pkit living-docs new space` writes it to `<definitions>/rule-sets/<space>.md` (below), with the set named and the scope's paths written, and names the file as the space's `definition` ([Authoring](#authoring-the-docs-author-skill)). The paths are the space's root, everything beneath it, and each place assigned to the space outside that root. The scope selects by the page type too, `types: [living-docs:page]`, so the definitions, records and rules under the root stay outside it. The user space adds one rule of its own: its readers' paths stay unbroken (DEC-001 point 3).
- **`signpost.md`** — the page template for the one page kind the decision names: an index-like file that says what a folder holds and where to go (`RS-LDOC-005`). A page of another kind arrives with its template and its declared structure.
- **`reference.md`** — the page template for a reference page: the page that describes one surface — an area, a capability, an adapter — to the reader who uses it, anchored to the code and decisions it describes.

`pkit living-docs new page` stamps a page from its kind's template. A page of a kind your project adds is written by hand from that kind's template.

A template you copy into the definitions location takes the template type there, so it is never a page ([Types](#types)).

## Declaring your spaces

Where your documentation lives is declared in two files, joined by path:

- **The backbone configuration** (`.pkit/project/config.yaml`) names the two documentation roots (`docs.user`, `docs.internal`) and every place outside them that holds pages (`friction.places`), and the paths the friction checks leave out (`friction.exclude`). The CLI reference's "Configuration file" section documents those keys.
- **This capability's project configuration** (`.pkit/capabilities/living-docs/project/config.yaml`) holds what only living-docs needs: each space's entry point and definition, and which space each place belongs to.

```yaml
pkit_schema: living-docs:config
schema_version: 1
spaces:
  user:                                        # the page a user starts from, and the space's rules
    entry-point: README.md
    definition: docs/living-docs/rule-sets/user.md
  technical:
    entry-point: CONTRIBUTING.md
    definition: docs/living-docs/rule-sets/technical.md
places:                                        # place → space, the place written as in friction.places
  README.md: user
  CONTRIBUTING.md: technical
```

A place inside a root belongs to that root's space; list it under `places` only to assign it elsewhere. A place outside every root must be listed. Each place names exactly one space. A project place never equals or encloses a root. The file's shape is `schemas/config.schema.json`, which `pkit validate` applies. Trees a sync copies into your repository are never places; in a repository where those trees are the authored source, they may be (the lifecycle README, "The ownership predicates"). The backbone's friction validation enforces this for every declared place, yours or a capability's, as its `synced-place` finding (the schemas README, "The friction block"), and this capability's place validation relies on that finding rather than checking a second time.

**Each definition's scope.** A space's definition carries a scope that selects the space's pages, written with the definition (DEC-001 point 2). Through it, `LDOC` and the space's own rules bind on those pages, and the validator checks the parts of them it enforces as soon as the definition exists. Until then — and no space has a definition when you install the capability — no rule binds on the space's pages, and the validator reports the space instead. A definition with no scope selects no page, so no rule binds on the space's pages through it. `pkit living-docs validate` reports such a definition and names the scope to give it: the space's root and the places assigned to it, by the page type. It also reports the pages of a space that the definition's scope leaves out, unless the join with the assignment, below, fails them. A placeholder left in the scope's paths, the template's `<root>`, names no file, and is reported as soon as the definition exists. A scope may leave part of a space out on purpose, with `exclude`, so a page it leaves out is reported, never failed.

**Your definitions' scopes and the assignment.** Where a space's definition carries a scope, which selects artefacts by path and by type (COR-051 point 2), the scope and the assignment both say where the space's pages lie. Validation holds them to each other (DEC-001 point 1):

- Each page an assigned place gives a space lies in that space definition's scope, and in no other space definition's scope. The validator reads the scopes covering each page from `in_scope_of` in `pkit friction artefacts --json`.
- Where a definition selects by type, `types` in its scope, each assigned place outside every root gives the page type: `{path: CONTRIBUTING.md, type: living-docs:page}` in `friction.places`. Such a place that names no type fails, before it holds any page.

A definition with no scope selects nothing itself, so nothing is held to it. The places assigned to its space are checked only against the scopes of the other spaces' definitions. A space with no definition yet is checked the same way. The validator's summary names the spaces whose definitions carry a scope.

**What the capability declares for you**, in its package metadata: the two roots, as the default places of their spaces (everything under each), each giving the page type, and its **definitions location**, `living-docs/` under the internal root — `docs/living-docs/` with the default root — which gives the template type. The spaces' definitions go in its `rule-sets/` folder, where the core reads them as your project's rule sets. The location is recorded the first time a definition is placed there, in `.pkit/capabilities/living-docs/project/docs-locations.yaml` (`locations: {definitions: docs/living-docs}`). So changing a root later moves nothing already written (COR-049 point 5). `pkit living-docs new space` records it. For a definition you write by hand, `pkit docs record-location living-docs definitions` records it. It says what it recorded, the root it was derived from, and where to change it.

## Authoring: the `docs-author` skill

`pkit living-docs new` stamps a page or a space's definition. The `docs-author` skill pairs with it (COR-005). It walks you through the choices the command does not make. `pkit sync` deploys it with the other skills, in Claude Code as `.claude/skills/docs-author/`.

```
pkit living-docs new space <space> [--set <NAME>] [--dry-run]
pkit living-docs new page <file> --space <space> --kind <kind> --reader <id> --title "<Title>"
    [--path <glob>]... [--record <id>]... [--artefact <id>]... [--source <name>]... [--dry-run]
```

**One check decides.** Each command runs the validator's own check before and after it writes. That is the check `pkit living-docs validate` runs.

- **A write that breaks validation is put back.** When the write brings an error your project did not have, the command puts back every file it wrote, refuses and quotes the error. So what it stamps passes `pkit living-docs validate` wherever your project passed it before.
- **What the check cannot read refuses too.** That is your places, where the rules bind, the readers point, or the kinds' structures.
- **`--dry-run`** makes the checks before the write, prints each file it would write and writes nothing.

**`new space`** makes the three writes of creating a space (DEC-001 point 2):

- **The definition,** `<definitions>/rule-sets/<space>.md`. It is a project rule set that inherits `LDOC` at its current major. Its scope selects the space's pages, the scope `pkit living-docs validate` names for a definition without one. The set is named after the space in upper case, its hyphens dropped, unless you name it with `--set`.
- **Its path,** as the space's `definition` in `.pkit/capabilities/living-docs/project/config.yaml`. Every other byte of the file is kept. The entry declares a space your project adds. Without the file, the command creates it.
- **The definitions location,** recorded the first time.

The user space's definition carries its one rule, `RS-<SET>-001`, reader paths stay unbroken. It is written accepted, so the review of the change that carries it accepts it (COR-051 point 4).

- **It refuses** a space that has a definition, and a set name another rule set has. It refuses a space no scope can select yet, with no root of its own and no place assigned to it.
- **It refuses a write that breaks validation,** such as a place outside every root, assigned to the space, that gives no page type.
- **It reports, without refusing,** each page of the space that the space's rules fail once they bind.
- **It refuses when the check cannot read what it judges** once the rules bind, such as a readers point that does not resolve while the space's pages name readers.
- **It writes nothing else:** nothing of the backbone configuration, and no other space's definition.

**`new page`** writes one new page into a space of your project, from the template of a kind this capability declares, `signpost` or `reference`.

- **Its front matter** names the reader and the kind. Its friction block lists the anchors you give, and is empty with none: the page then counts as unanchored for onboarding.
- **Its anchors:** code by `--path`, decisions and their points by `--record`, and captured sources by `--source`. `--artefact` takes rules, analysis artefacts and the home section of a fact it summarises.
- **Its body** is the template's. The title fills the level-1 heading. The command lists the lines that still hold the template's other placeholders.
- **It refuses** an unknown space or kind, a file that exists, and a path that is no Markdown file of the repository. It refuses a path reached through a link, a reader that is not a word, and an empty or placeholder title.
- **It refuses a file the check does not read as a page of the space you named.**
- **It warns** when the space has no definition yet, since no rule binds on the page then.

**A fresh project.** Both roots default to `docs/`. Two roots that are one folder give no space (DEC-001 point 1). So until you separate them, `new space` finds no scope for the user or technical space. Nor does `new page` write a page under them. Separate the roots first, as onboarding's first step says.

## Validation

`pkit living-docs validate` checks your spaces against the decision; `pkit validate` runs the same check as its `living-docs:spaces` member (`--json` prints the findings document it reads). It is a query: read-only, offline, and `pkit sync` provisions its dependencies.

**What it reads.** Where your documents are, it reads from the core, through `pkit friction artefacts --json` — the same discovery `pkit validate` and the friction checks read: your documentation roots, the places your configuration and every installed capability declare, the files each place matches, each file's front matter, each document's type with its matching places in the backbone's order, the scopes covering each page, and the documents a capability holds that are not artefacts, with their owner. A held document — an analysis capability's revalidation records, say — is walked by no place, so it is never an unclassified document: it is claimed by its owner and counted in the summary as "of another component" wherever it sits under your roots (DEC-001 point 1). It never reads the declarations or walks the places itself, so it can never disagree with the core about which files a place holds; a synced copy, a place outside the repository and a malformed declaration are skipped exactly as the core skips them. Nor does it rank the places: where places nest, the first root or project place in the backbone's order gives a document its space (COR-056 point 3). A place that equals or encloses a root comes after every other, the longer literal part wins, and at equal length an exact file beats a glob, which beats a folder. The answer ranks the places of artefacts only. A file that holds no artefact — no front matter the backbone reads — comes without ranks: where its places would give it different spaces, or one of them is a place outside every root with no assignment, which place holds it cannot be told, so the validator reports it and counts it unclassified. Where every one of its places is such an unassigned place, whichever holds it needs an assignment, which fails. What it decides over that answer is this capability's: which space a place serves, and what a document is to your spaces. Besides, it reads its own project configuration, where the rules bind — only when there is a page — through `pkit rule-sets reach --json`, and the readers point — only when some page names a reader where `RS-LDOC-003` binds — through `pkit connections resolve`. When the core gives no reading of the places, or a reading without each document's type, that is its one error, and no space is checked. It fails on:

- the sources folder, `.pkit/capabilities/living-docs/project/sources/`, or a folder on its path, that is a file or a link, or is named in another case (`Sources/`): no source is read from it, on any disk; the sources folder unreadable — a permission or disk error — so no source is checked;
- an entry of the sources folder that is not a captured source: a `.yaml` file not named `<name>.yaml` with a name of the grammar in Sources, a folder, or a link. An entry whose name begins with `.` — `.gitkeep`, an editor's or a desktop's file — is left alone: no source's name begins with one. A captured source's shape — the three fields, nothing else, each text — is `schemas/source.schema.json`, which `pkit validate` applies under `data`, bound by the file's path (COR-023);
- a place outside every root that holds a document nothing else claims, with no assignment — for a file without front matter, where every place it lies in is such a place; an assignment naming a place `friction.places` does not declare, or a space nobody declares; a place assigned twice;
- a project place equal to or enclosing a root; a file two project places claim at equal rank, ahead of every other place of your spaces, in the backbone's order;
- where a space's definition carries a scope: a page an assigned place gives that space outside that scope, or inside another space definition's scope; where it selects by type, an assigned place outside every root that does not give the page type ([Declaring your spaces](#declaring-your-spaces));
- a decision record that would otherwise be a page — of the page type, or declaring its page kind in an untyped place of yours outside every root — since a decision record is never a page. Another owner's document is never read for `reader` or `kind` ([Types](#types)), so carrying them fails nothing;
- where the rules bind, unreadable — `pkit rule-sets reach --json` gives no answer: one error, and no page's structure or reader is checked;
- a page whose `kind` does not fit `schemas/page.schema.json`; where `RS-LDOC-003` binds on a page, a `reader` it lacks or that does not fit the schema;
- where `RS-LDOC-003` binds on a page, a `reader` the readers point does not hold — the message names the readers it does (Connections, below);
- a page whose body lacks a section its kind's structure declares, or carries one out of order (Pages, above) — the message names the page, its kind, the section and the declared structure. It is an error where `RS-LDOC-004` binds on the page. A page no rule set of yours reaches is not checked, nor one reached only through a pin behind `LDOC`'s major, nor any page while the rule is not accepted (COR-051 points 4 and 7);
- the declaration of the kinds' structures, `schemas/page-kinds.yaml`, absent, unparsable or not fitting its schema — one error, "structures unreadable", and no page's body is checked. The file is read only where `RS-LDOC-004` binds on some page, or while you have no page and the rule is accepted;
- where `RS-LDOC-004` binds on a page whose kind declares a structure, a body that cannot be read;
- an entry point that is not a document of its space — under its root or in a place assigned to it. An entry point without front matter whose places cannot be told apart (above) fails only when none of them gives its space;
- a definition outside `<definitions>/rule-sets/`, or one that does not inherit `living-docs:LDOC`.

It reports, without failing: a `source` anchor, or a rule origin citing a `source`, that no captured file answers (the whole-repository check reports it dead); a captured source nothing anchors or cites; a captured source carrying `schema_version` or `binds_to`, which its shape permits only for its own carrier; a file in the sources folder whose name does not end in `.yaml` — notes, an editor's backup — which captures nothing; a space with no definition yet, a definition with no scope, or with the template's placeholder in its scope, naming the scope to give it, the pages of a space its definition's scope leaves out, a file without front matter whose places cannot be told apart, unless every one of them is an unassigned place outside every root, which fails (above), roots that are the same folder or nested (onboarding separates them), each kind that declares no structure, with the pages that name it where `RS-LDOC-004` binds and the kinds that do declare one, and — in its summary — the unclassified documents and the documents of a type of your own, whether each entry point is a page yet, the spaces whose definitions carry a scope, the readers each page's reader was checked against, how many pages were checked against their kind's structure and how many were not because their kind declares none, how many pages each check left out because its rule does not bind on them, and the pages left unanchored: those without an accepted reason, onboarding's work still to do, and apart from them those whose friction block gives one as `unanchored-because` (DEC-001 point 8; COR-050 point 1). The human view lists both, each accepted page with its reason; an excluded page is in neither. A synced tree declared as a place is the core's `synced-place` finding, under `friction` (above).

**Pages are checked** for their front matter — `kind`, and `reader` against the readers point where `RS-LDOC-003` binds, and the friction block, which `pkit validate` checks under `friction` — and for their body's structure, against the structure their kind declares, where `RS-LDOC-004` binds. Everything else a page owes `LDOC` is judgment, left to the agent's reader-review (below): whether each section says what its kind's template asks, whether the anchors ground every statement, whether each fact has one home, and whether the page says only what its reader needs.

## Connections

The capability provides the `pkit::documentation` role (COR-053); `pkit::` is this distribution's literal for the methodology's publisher qualifier ([the lifecycle README, "The methodology's literals"](../../lifecycle/README.md#the-methodologys-literals)). Under it, it accepts two data points, and it contributes to the work-tracking role's documentation check. `pkit status` shows how each point resolved, and `pkit connections resolve <point>` prints one.

**Accepts `pkit::documentation:readers`** (version 1): who reads the documentation and what they need. Each entry is an `id`, which a page names as its `reader`, and a `description` of what that reader needs (`schemas/readers.schema.json`). A `user` and a `maintainer` are built in and always included. The point is `union`, so you add readers, replace one by its id, or drop one with `remove` and a reason, in the point's [project file](../../lifecycle/README.md#where-a-project-filler-file-lives-the-address-to-path-mapping) — `docs/pkit/fillers/pkit/documentation/readers.yaml` with the default internal root:

```yaml
schema_version: 1
value:
  - id: operator
    description: Runs the service in production, and needs its settings and what to do when it fails.
```

A capability that keeps an analysis of the software can supply readers too, under ids of its own. The validator checks a page's `reader` against the resolved point wherever `RS-LDOC-003` binds on the page. Its inert policy is `fail`: if a capability's readers fall out of step with the point's version, the whole point is unresolved rather than checked against whichever readers survived. The validator then reports "readers unresolved" once, not once per page, and `pkit validate` names the fix under `connections`.

**Accepts `pkit::documentation:reading-evidence`** (version 1): results of executed checks that follow the documentation, such as a simulated user running a guide. Each entry is one result: an `id`, `<path>@<commit>#<check>`, with the `path` it followed, the `commit` by its full name (40 hexadecimal digits, or 64 under SHA-256), the `check`, the `outcome` (`passed` or `failed`) and an optional `description` (`schemas/reading-evidence.schema.json`). The `check` is the name its filler gives one executed check, kept from commit to commit — lower-case words of letters, digits and hyphens joined by dots, the first beginning with a letter — and by convention opens with the filler's own name: a capability's, or `project` for your own. A filler gives each result it reports for a page or path at a commit its own check, since one filler never supplies an id twice. So two fillers' results for one page or path at one commit stand side by side, and only two that claim one check collide: the point is then unresolved until your filler gives that id or removes it (COR-052 point 4). Nothing in this capability reads the point's entries, so the schema's patterns hold the shape of the id and the check, and nothing warns on the opening name. `union`, with no default. This capability runs no such check: a capability that does, or your project file, supplies the evidence, and until one does the point shows as unfilled. It is advisory (inert policy `fallback`): a filler that cannot answer is warned about, and the rest still count.

**Contributes to `pkit::work-tracking:doc-check`**, the documentation check of a work-tracking capability such as project-management ([project-management:DEC-053-doc-check-slot]). Its command, `fill-doc-check`, reads the core's whole-repository friction check at HEAD (`pkit friction check --all --json`) and prints obligations with the source `friction`. It declares that it reads history (`reads: [history]` on its `commands:` entry), so `pkit validate` and `pkit status` name the commit it read HEAD at; it reads no base — the base a pull request is compared with bounds the work-tracking check's diff, never this command:

- `page-stale` — one per page the check reports stale, naming the page as `document`. The page's answer in the pull request's diff meets it. A deferred page gives none: its deferral is the answer ([project-management:DEC-053-doc-check-slot] point 4), and `pkit friction debt` keeps reporting it until someone revalidates the page.
- `code-undocumented` — one per path of the declared surface that nothing anchors, naming the code as `path` and no `document`: no page's change meets it, only a page anchoring the path. The command reads HEAD, so the obligation leaves the point once a page on the branch anchors the code; until then the check reports it unmet, with the fix — anchor the path from a page.

The work-tracking capability decides whether `friction` obligations block. With project-management they are advisory until you set `doc_check.sources.friction: enforcing`. A repository with no commit yet owes nothing. The command asks git nothing itself: whether HEAD has a commit it reads from the core (`head` in `pkit repository base --json`). If git cannot read a commit that is there — a repository git refuses as unsafe, or a missing object — the command gives no answer, never "nothing owed". If a page's friction lies beyond a shallow clone's history, the command gives no answer either: the check then reports itself unresolved rather than pass on fewer obligations, so fetch the full history. Nor does it answer for a page whose anchor's resolver gave no answer (`no-answer`, state `unresolved`), or a page in a state this capability does not know, which it never takes for current: `pkit friction explain <page>` says why. A page left unjudged only by an anchor of a kind nothing installed resolves (`unresolved-kind`) is different. That anchor is a declaration to mend — correct or remove it, install the capability that registers the kind, or mend a refused registration — not an obligation of this change. So the command answers for the page with what its other anchors owe, and names the anchor in its human view. `pkit validate` reports such an anchor under `friction`, and the change check fails it where a pull request adds it or takes its resolver away (COR-050 point 12). It gives none either when the friction check answers a `schema_version` other than 1, which it does not read; a document without the key, from a backbone before it, reads as 1 (the CLI README, "Friction checks"). `pkit living-docs fill-doc-check` lists the obligations, and `--json` prints what the backbone reads. The contribution is inert when no work-tracking capability is installed.

## The agent: `living-docs`

The checks above tell you *that* a page drifted and *which* documents are not pages yet. Deciding what that means for a page is judgment, and the capability's agent, `living-docs`, does it — always as a proposal you review, never as an edit (DEC-001 points 5, 6 and 8). `pkit sync` deploys it with the other agents; in Claude Code it is `.claude/agents/living-docs.md`. Ask it in plain words; it picks one of three intents from what you ask:

| Ask it to… | It reads | It gives you |
|---|---|---|
| **fix a stale or deferred page** | `pkit friction explain <page>`: the anchors that changed and the commits behind them; then those commits and the page | a diff of the page and a pull-request body, citing each commit and the anchor it changed, and naming the answer you give once it is applied (`pkit friction revalidate … --outcome updated`). An anchor it re-points or adds names the one part a statement rests on, where it rests on one. When nothing in the page needs to change, it proposes the `unchanged` answer with a draft reason for you to confirm. For a page `explain` reports `unresolved`, it says why from the anchor's finding and proposes nothing for the prose: for `no-answer`, run again, then `pkit sync`, or the resolver needs mending; for `unresolved-kind`, where the kind misspells a registered one (`pkit validate` names the nearest), a one-line anchor correction with the revalidation a changed anchor list needs, otherwise the capability to install or the registration to mend. |
| **review a page as its reader** | the page's `reader`, resolved through `pkit::documentation:readers`; the rules that bind on the page, `LDOC`'s and its space's own, from `pkit rule-sets reach` | a findings record, each finding citing the rule the page breaks (`RS-LDOC-003`, or the space's own rule) and quoting the passage, and each passage a rule leaves to your judgement, such as a fact the page repeats, listed as a question — **only when something was found**. Nothing found: one line, no file. As a pull-request comment if you ask for one. |
| **onboard existing documentation** | the validator's unclassified documents and findings, the friction check's measures, your code-to-doc mapping if you keep one | one plan behind one approval gate (below) |

What it will not do:

- **Apply anything.** It is read-only on your repository: it never edits, moves or deletes a tracked file, never changes configuration, and never runs a friction writer (`revalidate`, `defer`, `record-status`) — the answer a page carries is a person's decision (COR-050 point 3), and this agent has no tool for asking you and judges pages besides; who may run a writer is in the agents README, "Friction writers". Its proposals land in the agent workspace, under `.agent-workspace/living-docs/`, as diffs you apply with `git apply` and pull-request bodies you open with. The one thing it writes outside the workspace is a reader-review posted as a pull-request comment, when you ask for it.
- **Repeat validation.** What `pkit living-docs validate` and `pkit validate` already judge, it names rather than re-judges.
- **Review a change for missing docs.** That is change review, the code-review panel's documentation reviewer where one is installed; reader-review looks at the page, not the diff.
- **Test the docs by running the product.** Such results arrive through the reading-evidence point, and the agent reads them when they are there.
- **Revalidate what is not a page** — a decision record, a rule, another capability's artefact. Its own component does that.
- **Fetch a source.** For a page stale on a `source` anchor it reads the versions recorded and the address from the source file's history (`git show <commit> -- <file>`), names the source, both versions and the link, and asks you what changed in the source that bears on the page's statements. It never rewrites a page from a version change alone.
- **Read a friction document of a version it does not read.** The `explain`, `debt` and `check --all` documents carry a `schema_version`; one other than 1 it refuses, naming the command and the version, and proposes nothing from it. One without the key, from a backbone before it, reads as 1.

Until the readers point resolves, the agent reads a page as the audience DEC-001 gives its space — users for the user space, maintainers for the technical one — and says so. Its scripted flows (a fix proposed, a reader-review that finds nothing, an onboarding plan rejected and revised, a page stale on a source) are in [`agents/living-docs/storyboard.md`](agents/living-docs/storyboard.md); the agent itself is [`agents/living-docs/living-docs.md`](agents/living-docs/living-docs.md).

## Onboarding an existing project

On a project that already has documentation, nothing is anchored yet, so onboarding is not moving files: it is friction work on that starting point (DEC-001 point 8). The path:

1. **Declare where your documentation lives** — the roots and any places outside them, each assigned to a space ("Declaring your spaces" above) — until `pkit living-docs validate` reports no errors. Its summary counts the **unclassified documents**: documents in your spaces' places that are not pages yet. They are the onboarding's input.
2. **Ask the agent to onboard.** It drafts **one plan**, each line citing its evidence, in four parts:
   - **spaces** — which space each unclassified document becomes a page of, with its `reader` and `kind`, or why the spaces' rules do not govern it; roots still shared are separated, and a space with no definition gets one from `pkit living-docs new space`, which you run, with the scope that selects its pages;
   - **splits and rewrites** — pages that serve two readers, or that state another page's fact with no link to its home or no anchor on the home's section (`RS-LDOC-002`), split, merged or rewritten for their reader;
   - **anchors** — the anchors each page's statements need, each on the one part a statement rests on where it rests on one ("Anchoring one part", in Pages above), and the statements nothing grounds, raised as questions rather than kept;
   - **mapping** — if you keep a code-to-doc mapping (the project-management capability's, read through the work-tracking role's documentation-check point), which of its rules become path anchors on the pages they name, narrowed where an anchor would match most of the repository. Retiring the mapping is a separate change, for whoever owns it.
3. **Review the plan at its single gate**: approve, revise, or reject. Nothing is drafted before you approve; a revision comes back to the gate; a rejection drafts nothing.
4. **Review the changes it drafts.** On approval it writes one reviewable change per step into `.agent-workspace/living-docs/onboarding/` — diffs and pull-request bodies — and stops. You apply them and open the pull requests. A page new in its change counts as revalidated there, so it needs no writer.
5. **Repeat until done.** Onboarding is complete when the declared surface is covered and no page is left unanchored without a reason you accepted. A page that has nothing to anchor to carries that reason in its friction block, `unanchored-because: <why>` instead of anchors — the core's key (COR-050 point 1), which the core refuses beside anchors. `pkit friction check --all` shows both measures, listing the pages accepted with a reason apart and counting only those without one; `pkit living-docs validate` counts the pages of your spaces each way in its summary and lists them.

From then on, the friction check flags pages as their anchors change, and the agent proposes each fix.

## What's shipped now, what's next

Shipped: the decision, the project configuration's schema, the declaration of the roots as places and of the definitions location, the page and template types they give, the validator, the `LDOC` rule set with the parts the validator enforces where they bind, the space-definition template with its scope and the signpost and reference page templates with the page's schema and each page kind's declared structure, the connections (the readers and reading-evidence points, and the contribution to the documentation check), the `source` anchor kind with its resolver and the shape of a captured source, and the `living-docs` agent that proposes fixes, performs reader-review and onboards existing documentation. Shipped too: the authoring command for a page and a space, `pkit living-docs new`, with its `docs-author` skill.

## Citing this capability's decisions

`[living-docs:DEC-001-living-docs-discipline]`; a rule of the shared method, `[living-docs:RS-LDOC-003]`.

## Dependencies

None. It works without analysis, work-tracking or testing capabilities, and each can enrich it.
