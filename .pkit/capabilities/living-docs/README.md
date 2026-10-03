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
      record: ["living-docs:DEC-001", COR-049, COR-050, COR-051, COR-053]
      artefact: [RS-LDOC-001, RS-LDOC-002, RS-LDOC-003, RS-LDOC-004, RS-LDOC-005, RS-LDOC-006]
    revalidated:
      at: 2026-10-03T12:32:07Z
      outcome: updated
---

# living-docs capability

Keep your documentation **true for the people who read it**, even when an agent writes most of it. Documentation is organised into spaces by audience: user-facing docs for people who use the system, and technical docs for the people and agents who build it. Every page names its reader and is anchored to what makes it true. When those anchors change, drift is detected, and an agent proposes the fix for a person to review. The rule is in [living-docs:DEC-001-living-docs-discipline].

## How it works

- **Spaces.** A user space and a technical space, kept separate: neither root lies inside the other. You can add others. New pages go under each space's root. A space can also include places the project declares — inside a root, where they inherit that root's space, or outside every root, such as the repo's top-level README, where the capability's project configuration assigns them to a space. Where places nest the most specific one wins. Decision records, rule sets, and anything another capability claims — through a place, or a folder of documents it holds, such as an analysis capability's revalidation records — are anchor targets or that capability's own, never pages. Each space's *definition* (its rules) lives in the technical space.
- **Rules.** The shared method rule set, `LDOC`, ships with this capability. Each space's definition inherits it and adds its own rules (core rule sets, COR-051).
- **Anchors and friction.** Each page's anchors (code, decisions, sources, analysis artefacts) must ground everything it says. The core friction check (COR-050) flags a page when any of those changed and nobody revalidated it. When two branches revalidate the same page, its block conflicts on merge, and whoever resolves the conflict revalidates the page as merged: when you merge the check's base into your branch and the conflict lies only in the block, `pkit friction resolve` takes the base side's answer, keeps both sides' deferrals, and names the revalidation still owed (the CLI README, "friction resolve").
- **Proposals, never blind edits.** The agent, `living-docs` ("The agent" below), proposes each fix with its evidence, and a person reviews it.
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

**A kind's structure.** Pages of a kind follow one format (`RS-LDOC-004`). A kind's template is the starting shape you fill in; the part of the format the validator checks is the kind's *structure*: the sections every page of the kind carries, in order where order matters. Each kind this capability ships declares its structure once, in `schemas/page-kinds.yaml`, and that file is where to read what a kind's pages must carry: each section is a heading level and, where the kind fixes the wording, its text, in the order listed unless the kind sets `ordered: false`. A structure names only what every page of the kind must carry, so a template may show more, and a page may carry other sections.

A section is a heading written with one to six `#` at the start of a line. These are not read as one: a `#` line that is indented (under a list item, say) or that lies inside a block quote, fenced code or an HTML comment; an underlined (setext) heading; an HTML heading (`<h1>`). A section the kind leaves you to word needs words of its own, so an empty `#` and a template's unfilled `<placeholder>` do not count; fixed text is compared ignoring case, runs of white space and trailing punctuation. A page whose kind declares no structure — a kind your project adds, say — is reported with its kind and never failed.

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
- **`signpost.md`** — the page template for the one page kind the decision names: an index-like file that says what a folder holds and where to go (`RS-LDOC-005`). A page of another kind arrives with its template and its declared structure.
- **`reference.md`** — the page template for a reference page: the page that describes one surface — an area, a capability, an adapter — to the reader who uses it, anchored to the code and decisions it describes.

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

**What the capability declares for you**, in its package metadata: the two roots, as the default places of their spaces (everything under each), and its **definitions location**, `living-docs/` under the internal root — `docs/living-docs/` with the default root. The spaces' definitions go in its `rule-sets/` folder, where the core reads them as your project's rule sets. When you place the first definition there, record the location in `.pkit/capabilities/living-docs/project/docs-locations.yaml` (`locations: {definitions: docs/living-docs}`), so changing a root later moves nothing already written (COR-049 point 5): `pkit docs record-location living-docs definitions` records where it lies now and says so — what it recorded, the root it was derived from, and where to change it.

## Validation

`pkit living-docs validate` checks your spaces against the decision; `pkit validate` runs the same check as its `living-docs:spaces` member (`--json` prints the findings document it reads). It is a query: read-only, offline, and `pkit sync` provisions its dependencies.

**What it reads.** Where your documents are, it reads from the core, through `pkit friction artefacts --json` — the same discovery `pkit validate` and the friction checks read: your documentation roots, the places your configuration and every installed capability declare, the files each place matches, each file's front matter, and the documents a capability holds that are not artefacts, with their owner. A held document — software-analysis's revalidation records, say — is walked by no place, so it is never an unclassified document: it is claimed by its owner and counted in the summary as "of another component" wherever it sits under your roots (DEC-001 point 1). It never reads the declarations or walks the places itself, so it can never disagree with the core about which files a place holds; a synced copy, a place outside the repository and a malformed declaration are skipped exactly as the core skips them. What it decides over that answer is this capability's: which place wins where places nest, which space a place serves, and what a document is. Besides, it reads its own project configuration, and the readers point — only when some page names a reader — through `pkit connections resolve`. When the core gives no reading of the places, that is its one error, and no space is checked. It fails on:

- a place outside every root that holds a document nothing else claims, with no assignment; an assignment naming a place `friction.places` does not declare, or a space nobody declares; a place assigned twice;
- a project place equal to or enclosing a root; a file two project places claim with equal specificity;
- a decision record, a rule-set file, or another capability's artefact or held document carrying `reader` or `kind` — none is ever a page;
- a page whose `reader` or `kind` does not fit `schemas/page.schema.json`;
- a page whose `reader` the readers point does not hold — the message names the readers it does (Connections, below);
- a page whose body lacks a section its kind's structure declares, or carries one out of order (Pages, above) — the message names the page, its kind, the section and the declared structure. It is an error while `RS-LDOC-004` is accepted; under any other status the rule binds nothing and no page's body is checked (COR-051 point 4);
- the declaration of the kinds' structures, `schemas/page-kinds.yaml`, absent, unparsable or not fitting its schema — one error, "structures unreadable", and no page's body is checked; a page whose body cannot be read;
- an entry point that is not a document of its space — under its root or in a place assigned to it;
- a definition outside `<definitions>/rule-sets/`, or one that does not inherit `living-docs:LDOC`.

It reports, without failing: a space with no definition yet, roots that are the same folder or nested (onboarding separates them), each kind that declares no structure, with the pages that name it and the kinds that do declare one, and — in its summary — the unclassified documents, whether each entry point is a page yet, the readers each page's reader was checked against, how many pages were checked against their kind's structure and how many were not because their kind declares none, and the pages left unanchored: those without an accepted reason, onboarding's work still to do, and apart from them those whose friction block gives one as `unanchored-because` (DEC-001 point 8; COR-050 point 1). The human view lists both, each accepted page with its reason; an excluded page is in neither. A synced tree declared as a place is the core's `synced-place` finding, under `friction` (above).

**Pages are checked** for their front matter — `reader` and `kind`, the reader against the readers point, and the friction block, which `pkit validate` checks under `friction` — and for their body's structure, against the structure their kind declares. Everything else a page owes `LDOC` is judgment, left to the agent's reader-review (below): whether each section says what its kind's template asks, whether the anchors ground every statement, whether each fact is stated once, and whether the page says only what its reader needs.

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

**Accepts `pkit::documentation:reading-evidence`** (version 1): results of executed checks that follow the documentation, such as a simulated user running a guide. Each entry is one result: an `id`, `<path>@<commit>#<check>`, with the `path` it followed, the `commit` by its full name (40 hexadecimal digits, or 64 under SHA-256), the `check`, the `outcome` (`passed` or `failed`) and an optional `description` (`schemas/reading-evidence.schema.json`). The `check` is the name its filler gives one executed check, kept from commit to commit — lower-case words of letters, digits and hyphens joined by dots, the first beginning with a letter — and by convention opens with the filler's own name: a capability's, or `project` for your own. A filler gives each result it reports for a page or path at a commit its own check, since one filler never supplies an id twice. So two fillers' results for one page or path at one commit stand side by side, and only two that claim one check collide: the point is then unresolved until your filler gives that id or removes it (COR-052 point 4). Nothing in this capability reads the point's entries, so the schema's patterns hold the shape of the id and the check, and nothing warns on the opening name. `union`, with no default. This capability runs no such check: a capability that does, or your project file, supplies the evidence, and until one does the point shows as unfilled. It is advisory (inert policy `fallback`): a filler that cannot answer is warned about, and the rest still count.

**Contributes to `pkit::work-tracking:doc-check`**, the documentation check of a work-tracking capability such as project-management ([project-management:DEC-053-doc-check-slot]). Its command, `fill-doc-check`, reads the core's whole-repository friction check at HEAD (`pkit friction check --all --json`) and prints obligations with the source `friction`. It declares that it reads history (`reads: [history]` on its `commands:` entry), so `pkit validate` and `pkit status` name the commit it read HEAD at; it reads no base — the base a pull request is compared with bounds the work-tracking check's diff, never this command:

- `page-stale` — one per page the check reports stale, naming the page as `document`. The page's answer in the pull request's diff meets it. A deferred page gives none: its deferral is the answer ([project-management:DEC-053-doc-check-slot] point 4), and `pkit friction debt` keeps reporting it until someone revalidates the page.
- `code-undocumented` — one per path of the declared surface that nothing anchors, naming the code as `path` and no `document`: no page's change meets it, only a page anchoring the path. The command reads HEAD, so the obligation leaves the point once a page on the branch anchors the code; until then the check reports it unmet, with the fix — anchor the path from a page.

The work-tracking capability decides whether `friction` obligations block. With project-management they are advisory until you set `doc_check.sources.friction: enforcing`. A repository with no commit yet owes nothing. The command asks git nothing itself: whether HEAD has a commit it reads from the core (`head` in `pkit repository base --json`). If git cannot read a commit that is there — a repository git refuses as unsafe, or a missing object — the command gives no answer, never "nothing owed". If a page's friction lies beyond a shallow clone's history, the command gives no answer either: the check then reports itself unresolved rather than pass on fewer obligations, so fetch the full history. Nor does it answer for a page whose anchor's resolver gave no answer (`no-answer`, state `unresolved`), or a page in a state this capability does not know, which it never takes for current: `pkit friction explain <page>` says why. A page left unjudged only by an anchor of a kind nothing installed resolves (`unresolved-kind`) is different. That anchor is a declaration to mend — correct or remove it, install the capability that registers the kind, or mend a refused registration — not an obligation of this change. So the command answers for the page with what its other anchors owe, and names the anchor in its human view. `pkit validate` reports such an anchor under `friction`, and the change check fails it where a pull request adds it or takes its resolver away (COR-050 point 12). It gives none either when the friction check answers a `schema_version` other than 1, which it does not read; a document without the key, from a backbone before it, reads as 1 (the CLI README, "Friction checks"). `pkit living-docs fill-doc-check` lists the obligations, and `--json` prints what the backbone reads. The contribution is inert when no work-tracking capability is installed.

## The agent: `living-docs`

The checks above tell you *that* a page drifted and *which* documents are not pages yet. Deciding what that means for a page is judgment, and the capability's agent, `living-docs`, does it — always as a proposal you review, never as an edit (DEC-001 points 5, 6 and 8). `pkit sync` deploys it with the other agents; in Claude Code it is `.claude/agents/living-docs.md`. Ask it in plain words; it picks one of three intents from what you ask:

| Ask it to… | It reads | It gives you |
|---|---|---|
| **fix a stale or deferred page** | `pkit friction explain <page>`: the anchors that changed and the commits behind them; then those commits and the page | a diff of the page and a pull-request body, citing each commit and the anchor it changed, and naming the answer you give once it is applied (`pkit friction revalidate … --outcome updated`). When nothing in the page needs to change, it proposes the `unchanged` answer with a draft reason for you to confirm. |
| **review a page as its reader** | the page's `reader`, resolved through `pkit::documentation:readers`; `LDOC` and the space's own rules | a findings record, each finding citing the rule the page breaks (`RS-LDOC-003`, or the space's own rule) and quoting the passage — **only when something was found**. Nothing found: one line, no file. As a pull-request comment if you ask for one. |
| **onboard existing documentation** | the validator's unclassified documents and findings, the friction check's measures, your code-to-doc mapping if you keep one | one plan behind one approval gate (below) |

What it will not do:

- **Apply anything.** It is read-only on your repository: it never edits, moves or deletes a tracked file, never changes configuration, and never runs a friction writer (`revalidate`, `defer`, `record-status`) — the answer a page carries is yours to give (COR-050 point 3). Its proposals land in the agent workspace, under `.agent-workspace/living-docs/`, as diffs you apply with `git apply` and pull-request bodies you open with. The one thing it writes outside the workspace is a reader-review posted as a pull-request comment, when you ask for it.
- **Repeat validation.** What `pkit living-docs validate` and `pkit validate` already judge, it names rather than re-judges.
- **Review a change for missing docs.** That is change review, the code-review panel's documentation reviewer where one is installed; reader-review looks at the page, not the diff.
- **Test the docs by running the product.** Such results arrive through the reading-evidence point, and the agent reads them when they are there.
- **Revalidate what is not a page** — a decision record, a rule, another capability's artefact. Its own component does that.
- **Read a friction document of a version it does not read.** The `explain`, `debt` and `check --all` documents carry a `schema_version`; one other than 1 it refuses, naming the command and the version, and proposes nothing from it. One without the key, from a backbone before it, reads as 1.

Until the readers point resolves, the agent reads a page as the audience DEC-001 gives its space — users for the user space, maintainers for the technical one — and says so. Its scripted flows (a fix proposed, a reader-review that finds nothing, an onboarding plan rejected and revised) are in [`agents/living-docs/storyboard.md`](agents/living-docs/storyboard.md); the agent itself is [`agents/living-docs/living-docs.md`](agents/living-docs/living-docs.md).

## Onboarding an existing project

On a project that already has documentation, nothing is anchored yet, so onboarding is not moving files: it is friction work on that starting point (DEC-001 point 8). The path:

1. **Declare where your documentation lives** — the roots and any places outside them, each assigned to a space ("Declaring your spaces" above) — until `pkit living-docs validate` reports no errors. Its summary counts the **unclassified documents**: documents in your spaces' places that are not pages yet. They are the onboarding's input.
2. **Ask the agent to onboard.** It drafts **one plan**, each line citing its evidence, in four parts:
   - **spaces** — which space each unclassified document becomes a page of, with its `reader` and `kind`, or why the spaces' rules do not govern it; roots still shared are separated, and a space with no definition gets one from the template;
   - **splits and rewrites** — pages that serve two readers, or state a fact another page states, split, merged or rewritten for their reader;
   - **anchors** — the anchors each page's statements need, and the statements nothing grounds, raised as questions rather than kept;
   - **mapping** — if you keep a code-to-doc mapping (the project-management capability's, read through the work-tracking role's documentation-check point), which of its rules become path anchors on the pages they name, narrowed where an anchor would match most of the repository. Retiring the mapping is a separate change, for whoever owns it.
3. **Review the plan at its single gate**: approve, revise, or reject. Nothing is drafted before you approve; a revision comes back to the gate; a rejection drafts nothing.
4. **Review the changes it drafts.** On approval it writes one reviewable change per step into `.agent-workspace/living-docs/onboarding/` — diffs and pull-request bodies — and stops. You apply them and open the pull requests. A page new in its change counts as revalidated there, so it needs no writer.
5. **Repeat until done.** Onboarding is complete when the declared surface is covered and no page is left unanchored without a reason you accepted. A page that has nothing to anchor to carries that reason in its friction block, `unanchored-because: <why>` instead of anchors — the core's key (COR-050 point 1), which the core refuses beside anchors. `pkit friction check --all` shows both measures, listing the pages accepted with a reason apart and counting only those without one; `pkit living-docs validate` counts the pages of your spaces each way in its summary and lists them.

From then on, the friction check flags pages as their anchors change, and the agent proposes each fix.

## What's shipped now, what's next

Shipped: the decision, the project configuration's schema, the declaration of the roots as places and of the definitions location, the validator, the `LDOC` rule set, the space-definition template and the signpost and reference page templates with the page's schema and each page kind's declared structure, the connections (the readers and reading-evidence points, and the contribution to the documentation check), and the `living-docs` agent that proposes fixes, performs reader-review and onboards existing documentation.

## Citing this capability's decisions

`[living-docs:DEC-001-living-docs-discipline]`; a rule of the shared method, `[living-docs:RS-LDOC-003]`.

## Dependencies

None. It works without analysis, work-tracking or testing capabilities, and each can enrich it.
