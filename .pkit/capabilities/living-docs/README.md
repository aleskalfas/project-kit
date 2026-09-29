# living-docs capability

Keep your documentation **true for the people who read it**, even when an agent writes most of it. Documentation is organised into spaces by audience: user-facing docs for people who use the system, and technical docs for the people and agents who build it. Every page names its reader and is anchored to what makes it true. When those anchors change, drift is detected, and an agent proposes the fix for a person to review. The rule is in [living-docs:DEC-001-living-docs-discipline].

## How it works

- **Spaces.** A user space and a technical space, kept separate: neither root lies inside the other. You can add others. New pages go under each space's root. A space can also include places the project declares — inside a root, where they inherit that root's space, or outside every root, such as the repo's top-level README, where the capability's project configuration assigns them to a space. Where places nest the most specific one wins. Decision records, rule sets, and anything another capability claims are anchor targets or that capability's artefacts, never pages. Each space's *definition* (its rules) lives in the technical space.
- **Rules.** The shared method rule set, `LDOC`, ships with this capability. Each space's definition inherits it and adds its own rules (core rule sets, COR-051).
- **Anchors and friction.** Each page's anchors (code, decisions, sources, analysis artefacts) must ground everything it says. The core friction check (COR-050) flags a page when any of those changed and nobody revalidated it.
- **Proposals, never blind edits.** The agent proposes each fix with its evidence, and a person reviews it.
- **Reader-review.** The agent reads a page as its declared reader and reports what that reader would miss or wouldn't need.

## Pages

A document is a **page** when its front matter carries two fields of its own, beside the core's friction block in the `pkit:` container:

```yaml
---
reader: user          # who the page is for: an id of the readers point (user, maintainer, …)
kind: signpost        # the page's kind: the template it follows
pkit:
  friction:
    anchors: { path: [src/cli/**], record: [ADR-006] }
---
```

`reader` and `kind` are each a word (`[a-z][a-z0-9-]*`); their shape is `schemas/page.schema.json`, which the validator below applies. The friction block is the core's, and `pkit validate` checks it under `friction`. A document in a space's places that carries neither field is an *unclassified document*: counted for onboarding to classify, never failed.

## The shared method: `LDOC`

`rule-sets/ldoc.md` is a method rule set (COR-051), cited `living-docs:LDOC`. Its rules are those point 3 of the decision states, each accepted, with the decision as its origin and its anchor:

| Rule | Statement |
|---|---|
| `RS-LDOC-001` | A page's anchors ground every statement it makes. |
| `RS-LDOC-002` | Each fact is stated once, and other pages link to it. |
| `RS-LDOC-003` | Each page names its reader and says only what that reader needs. |
| `RS-LDOC-004` | Pages of a kind follow one format, with a template per kind. |
| `RS-LDOC-005` | An index-like file is a signpost to what a folder holds, never a summary of its contents. |
| `RS-LDOC-006` | Nothing is created ahead of the need for it. |

You never edit `LDOC`; a space's definition inherits it, pinned to its major (`inherits: [living-docs:LDOC@1]`), and `pkit validate` tells you when a new major arrives. Rules about how rules are named and inherited are the core's (COR-051), so they are not repeated here.

## Templates

`templates/` holds the writers' tools:

- **`space-definition.md`** — a space's definition: a project rule set that inherits `LDOC` and holds the space's own rules, each carrying its friction block in its own container. Copy it to `<definitions>/rule-sets/<space>.md` (below), rename the set, and name the file as the space's `definition`. The user space adds one rule of its own: its readers' paths stay unbroken (DEC-001 point 3).
- **`signpost.md`** — the page template for the one page kind the decision names: an index-like file that says what a folder holds and where to go (`RS-LDOC-005`). A page of another kind arrives with its template.

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

**What the capability declares for you**, in its package metadata: the two roots, as the default places of their spaces (everything under each), and its **definitions location**, `living-docs/` under the internal root — `docs/living-docs/` with the default root. The spaces' definitions go in its `rule-sets/` folder, where the core reads them as your project's rule sets. When you place the first definition there, record the location in `.pkit/capabilities/living-docs/project/docs-locations.yaml` (`locations: {definitions: docs/living-docs}`), so changing a root later moves nothing already written (COR-049 point 5); no command writes it yet.

## Validation

`pkit living-docs validate` checks your spaces against the decision; `pkit validate` runs the same check as its `living-docs:spaces` member (`--json` prints the findings document it reads). It is a query: read-only, offline, and `pkit sync` provisions its dependencies. It fails on:

- a place outside every root that holds a document nothing else claims, with no assignment; an assignment naming a place `friction.places` does not declare, or a space nobody declares; a place assigned twice;
- a project place equal to or enclosing a root; a file two project places claim with equal specificity;
- a decision record, a rule-set file or another capability's artefact carrying `reader` or `kind` — none is ever a page;
- a page whose `reader` or `kind` does not fit `schemas/page.schema.json`;
- a page whose `reader` the readers point does not hold — the message names the readers it does (Connections, below);
- an entry point that is not a document of its space — under its root or in a place assigned to it;
- a definition outside `<definitions>/rule-sets/`, or one that does not inherit `living-docs:LDOC`.

It reports, without failing: a space with no definition yet, roots that are the same folder or nested (onboarding separates them), and — in its summary — the unclassified documents, whether each entry point is a page yet, and the readers each page's reader was checked against. A synced tree declared as a place is the core's `synced-place` finding, under `friction` (above).

## Connections

The capability provides the `pkit::documentation` role (COR-053); `pkit::` is this distribution's literal for the methodology's publisher qualifier ([the lifecycle README, "The methodology's literals"](../../lifecycle/README.md#the-methodologys-literals)). Under it, it accepts two data points, and it contributes to the work-tracking role's documentation check. `pkit status` shows how each point resolved, and `pkit connections resolve <point>` prints one.

**Accepts `pkit::documentation:readers`** (version 1): who reads the documentation and what they need. Each entry is an `id`, which a page names as its `reader`, and a `description` of what that reader needs (`schemas/readers.schema.json`). A `user` and a `maintainer` are built in and always included. The point is `union`, so you add readers, replace one by its id, or drop one with `remove` and a reason, in the point's [project file](../../lifecycle/README.md#where-a-project-filler-file-lives-the-address-to-path-mapping) — `docs/pkit/fillers/pkit/documentation/readers.yaml` with the default internal root:

```yaml
schema_version: 1
value:
  - id: operator
    description: Runs the service in production, and needs its settings and what to do when it fails.
```

An analysis capability, such as software-analysis, can supply readers too, under ids of its own. The validator checks every page's `reader` against the resolved point. Its inert policy is `fail`: if a capability's readers fall out of step with the point's version, the whole point is unresolved rather than checked against whichever readers survived. The validator then reports "readers unresolved" once, not once per page, and `pkit validate` names the fix under `connections`.

**Accepts `pkit::documentation:reading-evidence`** (version 1): results of executed checks that follow the documentation, such as a simulated user running a guide. Each entry is an `id`, `<path>@<commit>`, with the `path` it followed, the `commit`, the `outcome` (`passed` or `failed`) and an optional `description` (`schemas/reading-evidence.schema.json`). `union`, with no default. This capability runs no such check: a capability that does, or your project file, supplies the evidence, and until one does the point shows as unfilled. It is advisory (inert policy `fallback`): a filler that cannot answer is warned about, and the rest still count.

**Contributes to `pkit::work-tracking:doc-check`**, the documentation check of a work-tracking capability such as project-management ([project-management:DEC-053-doc-check-slot]). Its command, `fill-doc-check`, reads the core's whole-repository friction check at HEAD (`pkit friction check --all --json`) and prints obligations with the source `friction`:

- `page-stale` — one per page the check reports stale or deferred. The page's answer in the pull request's diff meets it.
- `code-undocumented` — one per path of the declared surface that nothing anchors, naming the code as `path` and the internal root as `document`. It leaves the point once a page anchors the code.

The work-tracking capability decides whether `friction` obligations block. With project-management they are advisory until you set `doc_check.sources.friction: enforcing`. A repository with no commit yet owes nothing. If a page's friction lies beyond a shallow clone's history, the command gives no answer: the check then reports itself unresolved rather than pass on fewer obligations, so fetch the full history. `pkit living-docs fill-doc-check` lists the obligations, and `--json` prints what the backbone reads. The contribution is inert when no work-tracking capability is installed.

## Adopting it on an existing project

Onboarding is transformation, not moving files. The agent proposes which space each page belongs to, how pages should be split or rewritten for their readers, and which anchors each statement needs. Every proposal lands as a reviewable change.

## What's shipped now, what's next

Shipped: the decision, the project configuration's schema, the declaration of the roots as places and of the definitions location, the validator, the `LDOC` rule set, the space-definition template and the signpost page template with the page's schema, and the connections (the readers and reading-evidence points, and the contribution to the documentation check). Next comes the agent that proposes fixes, performs reader-review and onboards existing documentation.

## Citing this capability's decisions

`[living-docs:DEC-001-living-docs-discipline]`; a rule of the shared method, `[living-docs:RS-LDOC-003]`.

## Dependencies

None. It works without analysis, work-tracking or testing capabilities, and each can enrich it.
