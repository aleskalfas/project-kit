---
reader: act-ai-agent
kind: reference
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/living-docs/scripts/new.py
        - .pkit/capabilities/living-docs/scripts/_lib/stamp.py
        - .pkit/capabilities/living-docs/scripts/fill-doc-check.py
        - .pkit/capabilities/living-docs/scripts/_lib/doc_check.py
        - .pkit/capabilities/living-docs/scripts/validate.py
        - .pkit/capabilities/living-docs/schemas/readers.schema.json
        - .pkit/capabilities/living-docs/schemas/config.schema.json
        - .pkit/capabilities/living-docs/schemas/reading-evidence.schema.json
        - .pkit/capabilities/living-docs/skills/**
      record: ["living-docs:DEC-001", COR-005, COR-030, COR-049, COR-050, COR-051, "COR-052#4", COR-053, "project-management:DEC-053", "project-management:DEC-056", "living-docs:DEC-002"]
      artefact:
        - RS-LDOC-003
        - .pkit/capabilities/living-docs/pages.md#
        - .pkit/capabilities/living-docs/pages.md#types
        - .pkit/capabilities/living-docs/pages.md#a-pages-fields
        - .pkit/capabilities/living-docs/pages.md#sources
        - .pkit/capabilities/living-docs/pages.md#visual-elements
        - .pkit/capabilities/living-docs/pages.md#the-kinds-templates
        - .pkit/capabilities/living-docs/spaces.md#the-space-definition-template
        - .pkit/capabilities/living-docs/spaces.md#the-shared-method-ldoc
        - .pkit/capabilities/living-docs/validation.md#the-command
        - .pkit/capabilities/living-docs/validation.md#what-a-page-mentions-and-does-not-anchor
        - .pkit/capabilities/living-docs/agent.md#the-review-contribution
        - .pkit/capabilities/living-docs/agent.md#onboarding
        - .pkit/capabilities/living-docs/spaces.md#
        - .pkit/capabilities/living-docs/spaces.md#declaring-the-spaces
        - .pkit/capabilities/living-docs/spaces.md#each-definitions-scope
        - .pkit/capabilities/living-docs/validation.md#
        - .pkit/capabilities/living-docs/agent.md#
        - .pkit/capabilities/living-docs/agent.md#what-it-does
        - .pkit/capabilities/living-docs/agent.md#as-the-fixer-of-pages
        - .pkit/capabilities/project-management/README.md#8-optional-grant-the-fixers-your-capabilities-declare
        - .pkit/lifecycle/README.md#the-methodologys-literals
        - .pkit/lifecycle/README.md#where-a-project-filler-file-lives-the-address-to-path-mapping
        - .pkit/adapters/claude-code/README.md#deploy-skillssh
        - .pkit/cli/README.md#capabilities--two-ways-in
        - .pkit/cli/README.md#config-set-key-value---yes
        - .pkit/cli/README.md#repository-base---base-ref---json
        - .pkit/cli/README.md#sync
        - .pkit/cli/README.md#status
        - .pkit/cli/README.md#validate
        - .pkit/cli/README.md#friction-check---base-ref---head-rev---json
        - .pkit/cli/README.md#friction-check---all---json
        - .pkit/cli/README.md#friction-debt---json
        - .pkit/cli/README.md#friction-explain-artefact---json
        - .pkit/cli/README.md#connections-resolve-address---json
---

# living-docs capability

<a id="how-it-works"></a><a id="adopter-setup"></a>

living-docs keeps each documentation space true for its readers, through anchored pages, declared readers and reviewed fixes ([living-docs:DEC-001-living-docs-discipline]). Pages, spaces, validation and the agent each have a page beside this one ("The pages beside this one" below). Why it exists, and how people set it up and do its tasks, is in [living-docs' guide](https://github.com/aleskalfas/project-kit/blob/latest/docs/capabilities/living-docs/README.md).

## Contents

<!-- pkit:contents -->
- [Installing it](#installing-it)
- [Authoring: the `docs-author` skill](#authoring-the-docs-author-skill)
- [Connections](#connections)
- [Citing this capability's decisions](#citing-this-capabilitys-decisions)
- [Dependencies](#dependencies)
- [The pages beside this one](#the-pages-beside-this-one)
<!-- /pkit:contents -->

## Installing it

`pkit capabilities install living-docs` copies the capability into `.pkit/capabilities/living-docs/`. It deploys the `docs-author` skill and the `living-docs` agent, and provisions the query commands ([the CLI reference, "Capabilities — two ways in"](../../cli/README.md#capabilities--two-ways-in)).

- **What it needs.** uv on the `PATH`, which runs the capability's commands, and no other capability. project-management is optional ("Dependencies" below).
- **What it writes.** Nothing of the project's configuration, apart from the answers to the questions it asks. One is project-management's question, where it is installed, about granting the `living-docs` agent. The install never sets the two roots apart.
- **A fresh project.** `pkit living-docs validate` then reports that neither space has a definition and that the two roots are one folder, and fails nothing.
- **What sets it up.** `pkit living-docs new space` creates each space ("Authoring" below). Declare a place outside both roots that holds pages before its space is created, so that the definition's scope takes it in. One assigned later is added to the scope by hand ([the page on spaces, "Each definition's scope"](spaces.md#each-definitions-scope)).
- **Enforcing friction, optionally.** `pkit config set` sets `friction.mode` to `enforcing`. With `pkit friction check` a required check of the project's continuous integration, a change that leaves an anchored page stale fails there.
- **With project-management installed,** the `living-docs` agent becomes the fixer of the project's pages once the project grants it ([project-management's README](../project-management/README.md#8-optional-grant-the-fixers-your-capabilities-declare)). The install's question may already have recorded that grant. project-management's documentation check treats stale pages as advisory until its configuration sets `doc_check.sources.friction: enforcing` ("Connections" below).

## Authoring: the `docs-author` skill

`pkit living-docs new` stamps a page or a space's definition. The `docs-author` skill pairs with it (COR-005), and walks through the choices the command does not make. `pkit sync` deploys the skill with the other skills, in Claude Code as `.claude/skills/docs-author/`, through the adapter's `deploy-skills.sh` ([the Claude Code adapter's README, `deploy-skills.sh`](../../adapters/claude-code/README.md#deploy-skillssh)).

```
pkit living-docs new space <space> [--set <NAME>] [--internal-root <path>] [--yes] [--dry-run]
pkit living-docs new page <file> --space <space> --kind <kind> --reader <id> --title "<Title>"
    [--path <glob>]... [--record <id>]... [--artefact <id>]... [--source <name>]...
    [--internal-root <path>] [--yes] [--dry-run]
```

**One check decides.** Each command runs validation's own check before and after it writes. That is the check `pkit living-docs validate` runs.

- **A write that breaks validation is put back.** When the write brings an error the project did not have, the command puts back every file it wrote, refuses and quotes the error. So what it stamps passes `pkit living-docs validate` wherever the project passed it before.
- **What the check cannot read refuses too.** That is any of these:
  - the places
  - where the rules bind
  - the readers point
  - the kinds' structures
- **`--dry-run`** makes the checks before the write, prints each file it would write, and writes nothing.

**`new space`** makes the three writes of creating a space (DEC-001 point 2):

- **The definition,** `<definitions>/rule-sets/<space>.md`. It is a project rule set that inherits `LDOC` at its current major. Its scope selects the space's pages, the scope `pkit living-docs validate` names for a definition without one. The set is named after the space in upper case, its hyphens dropped, unless `--set` names it.
- **Its path,** as the space's `definition` in `.pkit/capabilities/living-docs/project/config.yaml` <!-- unanchored: named as the file the command writes, whose shape is schemas/config.schema.json, which the page anchors -->. Every other byte of the file is kept. The entry declares a space the project adds. Without the file, the command creates it.
- **The definitions location,** recorded the first time.

The user space's definition carries its one rule, `RS-<SET>-001`, reader paths stay unbroken. It is written accepted, so the review of the change that carries it accepts it (COR-051 point 4).

- **It refuses** a space that has a definition, and a set name another rule set has. It refuses a space no scope can select yet, with no root of its own and no place assigned to it.
- **It refuses a write that breaks validation,** such as a place outside every root, assigned to the space, that gives no page type.
- **It reports, without refusing,** each page of the space that the space's rules fail once they bind.
- **It refuses when the check cannot read what it judges** once the rules bind. An example is a readers point that does not resolve while the space's pages name readers.
- **It writes nothing else itself:** no other space's definition, and nothing of the backbone configuration. Only `pkit config set` writes that, when the command sets the roots apart ("A fresh project" below).

**`new page`** writes one new page into a space of the project, from the template of a kind this capability declares, `signpost` or `reference`.

- **Where it goes.** A new page of the user or technical space goes under that space's root by default. A page of any space may go into a place assigned to that space (DEC-001 point 1).
- **Its front matter** names the reader and the kind. Its friction block lists the anchors given, and is empty with none: the page then counts as unanchored for onboarding.
- **Its anchors:** code by `--path`, decisions and their points by `--record`, and captured sources by `--source`. `--artefact` takes rules, analysis artefacts and the home section of a fact it summarises.
- **Its body** is the template's. The title fills the level-1 heading. The command lists the lines that still hold the template's other placeholders.
- **It refuses** these, and writes nothing:
  - an unknown space or kind
  - a file that exists
  - a path that is no Markdown file of the repository, or one reached through a link
  - a reader that is not a word
  - an empty or placeholder title
- **It refuses a file the check does not read as a page of the space named.**
- **It warns** when the space has no definition yet, since no rule binds on the page then.

### A fresh project: the first stamp sets the roots apart

Both roots default to `docs/`, and two roots that are one folder give no space (DEC-001 point 1). So before `new` stamps a space, or a page of the user or technical space, it offers to set the internal root apart. No step comes before the command. What an install placed in `docs/` before the first space stays there, so create that space before installing software-analysis.

- **The folder.** The internal root goes to `tech-docs/`, and the user root keeps `docs/`. `--internal-root <path>` names another folder. A folder that lies in the user root, or holds the user root, is refused.
- **The write.** `pkit config set docs.internal tech-docs` makes the write, and asks once at a terminal. Off a terminal, the stamp needs `--yes`. Without it, the stamp refuses, writes nothing and names the command to run. Declined, nothing is written or stamped.
- **What stays in `docs/`.** No document moves. A project rule set a capability's install created in `docs/rule-sets/` stays there, among the user documents, and is still found. The configuration command names each recorded location the old root held ([the CLI reference, "config set"](../../cli/README.md#config-set-key-value---yes)).
- **A dry run** says it would set the root first, and writes nothing.

Accepted, the roots stay apart even where the stamp then refuses. A space the project adds lies in places of its own, so a page of it needs no separation. Its definition still lies under the internal root, so `new space` for it offers the separation too.

## Connections

The capability provides the `pkit::documentation` role (COR-053), under which it accepts two data points. It contributes to two points of the work-tracking role: its documentation check and its fixers. `pkit status` shows how each point resolved, and `pkit connections resolve <point>` prints one.

- **`pkit::`** is this distribution's literal for the methodology's publisher qualifier ([the lifecycle README, "The methodology's literals"](../../lifecycle/README.md#the-methodologys-literals)).

### The readers point

**Accepts `pkit::documentation:readers`** (version 1): the readers of the documentation, each with their needs and the paths they take.

- **An entry** is an `id`, which a page names as its `reader`, and a `description` of what that reader needs (`schemas/readers.schema.json`).
- **Its paths.** An entry may also carry `paths`, the paths that reader takes through the pages. A path is the list of pages the reader reads in order, under `pages`, with an optional `description` of what they come to do. Each page is named by its Markdown file's path from the repository's root, never by a pattern of files.
- **The built-in readers.** A `user` and a `maintainer` are built in and always included, with no paths, since only the project knows its pages.
- **Its policy.** The point is `union`, so the project adds readers, replaces one by its id, or drops one with `remove` and a reason. It does so in the point's [project file](../../lifecycle/README.md#where-a-project-filler-file-lives-the-address-to-path-mapping), `docs/pkit/fillers/pkit/documentation/readers.yaml` with the default internal root:

```yaml
schema_version: 1
value:
  - id: operator
    description: Runs the service in production, and needs its settings and what to do when it fails.
    paths:
      - description: Restarts the service after a failure.
        pages: [docs/operations.md, docs/runbooks/restart.md]
```

- **Replacing an entry.** An entry replaces another of its id whole, so `user` takes paths only in an entry that writes its `description` with them.
- **Who reads the paths.** No check reads a path. The agent's reader-review takes a page's reader from the point, with the reader's description and paths. A rule may ask that reader paths stay unbroken, as the user space's own rule does. The review then follows each path that passes through the page.
- **Readers a capability supplies.** A capability that keeps an analysis of the software can supply readers too, under ids of its own.
- **When it is checked.** Validation checks a page's `reader` against the resolved point wherever `RS-LDOC-003` binds on the page.
- **Its inert policy is `fail`.** If a capability's readers fall out of step with the point's version, the whole point is unresolved, rather than checked against whichever readers survived. Validation then reports "readers unresolved" once, not once per page, and `pkit validate` names the fix under `connections`.

### The reading-evidence point

**Accepts `pkit::documentation:reading-evidence`** (version 1): results of executed checks that follow the documentation, such as a simulated user running a guide.

- **An entry** is one result (`schemas/reading-evidence.schema.json`):
  - an `id`, `<path>@<commit>#<check>`
  - the `path` it followed
  - the `commit` by its full name, 40 hexadecimal digits, or 64 under SHA-256
  - the `check`
  - the `outcome`, `passed` or `failed`
  - an optional `description`
- **The `check`** is the name its filler gives one executed check, kept from commit to commit. It is lower-case words of letters, digits and hyphens joined by dots, the first beginning with a letter. By convention it opens with the filler's own name: a capability's, or `project` for the project's own.
- **One check per result.** One filler never supplies an id twice. So it gives each of its results for one page or path at one commit a check of its own. So two fillers' results for one page or path at one commit stand side by side. Only two that claim one check collide, and the point is then unresolved until the filler gives that id or removes it (COR-052 point 4).
- **What validation reads of it:** none of its entries. So the schema's patterns hold the shape of the id and the check, and nothing warns on the opening name.
- **Its policy.** `union`, with no default. This capability runs no such check. A capability that does, or the project file, supplies the evidence, and until one does the point shows as unfilled.
- **Its inert policy is `fallback`,** since it is advisory: a filler that cannot answer is warned about, and the rest still count.

### The documentation check

**Contributes to `pkit::work-tracking:doc-check`**, the documentation check of a work-tracking capability such as project-management ([project-management:DEC-053-doc-check-slot]). Its command, `fill-doc-check`, reads the core's whole-repository friction check at HEAD (`pkit friction check --all --json`), and prints obligations with the source `friction`:

- **`page-stale`:** one per page the check reports stale, naming the page as `document`. The page's answer in the pull request's diff meets it. A deferred page gives none, since its deferral is the answer ([project-management:DEC-053-doc-check-slot] point 4), and `pkit friction debt` keeps reporting it until someone revalidates the page.
- **`code-undocumented`:** one per path of the declared surface that nothing anchors, naming the code as `path` and no `document`. No page's change meets it, only a page anchoring the path. The command reads HEAD, so the obligation leaves the point once a page on the branch anchors the code. Until then the check reports it unmet, with the fix: anchor the path from a page.

**What it reads.** It declares that it reads history, `reads: [history]` on its `commands:` entry, so `pkit validate` and `pkit status` name the commit it read HEAD at. It reads no base: the base a pull request is compared with bounds the work-tracking check's diff, never this command.

**Whether it blocks.** The work-tracking capability decides whether `friction` obligations block. With project-management they are advisory until `doc_check.sources.friction: enforcing` is set. A repository with no commit yet owes nothing.

**When it gives no answer,** never "nothing owed":

- **A commit git cannot read.** The command asks git nothing itself: whether HEAD has a commit it reads from the core (`head` in `pkit repository base --json`). Where git cannot read a commit that is there, the command gives no answer. Such is a repository git refuses as unsafe, or a missing object.
- **A shallow clone.** If a page's friction lies beyond a shallow clone's history, the check reports itself unresolved, rather than pass on fewer obligations. Fetch the full history.
- **A page left unjudged:** one whose anchor's resolver gave no answer (`no-answer`, state `unresolved`). The same holds for a page in a state this capability does not know, which it never takes for current. `pkit friction explain <page>` says why.
- **A friction document of another version.** The friction check's answer carries a `schema_version`. The command does not read one other than 1. One without the key, from a backbone before it, reads as 1 (the CLI README, "Friction checks").

**An anchor nothing resolves.** A page left unjudged only by an anchor of a kind nothing installed resolves (`unresolved-kind`) is different. That anchor is a declaration to mend, not an obligation of this change. It is mended in one of three ways:

- correct or remove it
- install the capability that registers the kind
- mend a refused registration

Of such a page:

- **What the command answers.** It answers for the page with what its other anchors owe, and names the anchor in its human view.
- **Who reports the anchor.** `pkit validate` reports it under `friction`, and the change check fails it where a pull request adds it, or takes its resolver away (COR-050 point 12).

`pkit living-docs fill-doc-check` lists the obligations, and `--json` prints what the backbone reads. The contribution is inert when no work-tracking capability is installed.

### The fixers

**Contributes to `pkit::work-tracking:fixers`**, which says which agent fixes the artefacts of each type, in a work-tracking capability such as project-management ([project-management:DEC-056-drift-fixers]). Its static value names the `living-docs` agent as the fixer of the page type, `living-docs:page` (DEC-001 point 5).

- **Only where granted.** The agent starts on its own only where the project grants it, as [project-management's README](../project-management/README.md#8-optional-grant-the-fixers-your-capabilities-declare) says. A work-tracking capability that starts granted fixers then starts it on the pages the default branch left stale. It brings the person what the agent proposes ([the page on the agent, "As the fixer of pages"](agent.md#as-the-fixer-of-pages)).
- **Keyed by type.** Only pages of the type `living-docs:page` are the agent's there. A page in a project place that lies outside the roots and gives no type, or one whose type is tied, is not started on. Giving the place the page type ([the page on pages, "Types"](pages.md#types)) brings its pages in.
- **Inert** when no work-tracking capability is installed.

## Citing this capability's decisions

`[living-docs:DEC-001-living-docs-discipline]` and `[living-docs:DEC-002-visual-elements]`, and a rule of the shared method as `[living-docs:RS-LDOC-003]`.

## Dependencies

No other capability is required. It works without analysis, work-tracking or testing capabilities, and each can enrich it.

- **uv.** Its commands are Python scripts that uv runs, each with the packages it declares, so uv must be on the `PATH`.
- **project-management** is an optional dependency, from its first release with the floor `touches-ruled-artefact` (DEC-001 point 9). Install and upgrade hold an installed project-management to that range, so the floor never meets a release that does not know it (COR-030). Without project-management, nothing reads the review contribution.

## The pages beside this one

<a id="whats-shipped-now-whats-next"></a>

Each part the capability ships is described here, or on one of the pages beside this one:

- [`pages.md`](pages.md) — a page's fields and anchors, a kind's format, the types of documents, captured sources and visual elements.
- [`spaces.md`](spaces.md) — declaring the spaces, each definition's scope, the definitions location, the space-definition template and the shared method, `LDOC`.
- [`validation.md`](validation.md) — what validation reads, fails on and reports, and what a page mentions and does not anchor.
- [`agent.md`](agent.md) — the `living-docs` agent, its fixer runs and onboarding, and the review contribution.

**Where each section that left this page went:**

- <a id="pages"></a>"Pages" is [`pages.md`, "A page's fields"](pages.md#a-pages-fields).
- <a id="types"></a>"Types" is [`pages.md`, "Types"](pages.md#types).
- <a id="sources"></a>"Sources" is [`pages.md`, "Sources"](pages.md#sources).
- <a id="visual-elements"></a>"Visual elements" is [`pages.md`, "Visual elements"](pages.md#visual-elements).
- <a id="templates"></a>"Templates" is [`pages.md`, "The kinds' templates"](pages.md#the-kinds-templates), and [`spaces.md`, "The space-definition template"](spaces.md#the-space-definition-template).
- <a id="the-shared-method-ldoc"></a>"The shared method" is [`spaces.md`, "The shared method"](spaces.md#the-shared-method-ldoc).
- <a id="declaring-your-spaces"></a>"Declaring your spaces" is [`spaces.md`, "Declaring the spaces"](spaces.md#declaring-the-spaces).
- <a id="validation"></a>"Validation" is [`validation.md`, "The command"](validation.md#the-command).
- <a id="what-a-page-mentions-and-does-not-anchor"></a>"What a page mentions and does not anchor" is [`validation.md`, under the same heading](validation.md#what-a-page-mentions-and-does-not-anchor).
- <a id="the-review-contribution"></a>"The review contribution" is [`agent.md`, under the same heading](agent.md#the-review-contribution).
- <a id="the-agent-living-docs"></a>"The agent" is [`agent.md`, "What it does"](agent.md#what-it-does).
- <a id="onboarding-an-existing-project"></a>"Onboarding an existing project" is [`agent.md`, "Onboarding"](agent.md#onboarding).
