# living-docs capability

Keep your documentation **true for the people who read it**, even when an agent writes most of it. Documentation is organised into spaces by audience: user-facing docs for people who use the system, and technical docs for the people and agents who build it. Every page names its reader and is anchored to what makes it true. When those anchors change, drift is detected, and an agent proposes the fix for a person to review. The rule is in [living-docs:DEC-001-living-docs-discipline].

## How it works

- **Spaces.** A user space and a technical space, kept separate: neither root lies inside the other. You can add others. New pages go under each space's root. A space can also include places the project declares — inside a root, where they inherit that root's space, or outside every root, such as the repo's top-level README, where the capability's project configuration assigns them to a space. Where places nest the most specific one wins. Decision records, rule sets, and anything another capability claims are anchor targets or that capability's artefacts, never pages. Each space's *definition* (its rules) lives in the technical space.
- **Rules.** The shared method rule set, `LDOC`, ships with this capability. Each space's definition inherits it and adds its own rules (core rule sets, COR-051).
- **Anchors and friction.** Each page's anchors (code, decisions, sources, analysis artefacts) must ground everything it says. The core friction check (COR-050) flags a page when any of those changed and nobody revalidated it.
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

**What the capability declares for you**, in its package metadata: the two roots, as the default places of their spaces (everything under each), and its **definitions location**, `living-docs/` under the internal root — `docs/living-docs/` with the default root. The spaces' definitions go in its `rule-sets/` folder, where the core reads them as your project's rule sets. When you place the first definition there, record the location in `.pkit/capabilities/living-docs/project/docs-locations.yaml` (`locations: {definitions: docs/living-docs}`), so changing a root later moves nothing already written (COR-049 point 5); no command writes it yet.

## Validation

`pkit living-docs validate` checks your spaces against the decision; `pkit validate` runs the same check as its `living-docs:spaces` member (`--json` prints the findings document it reads). It is a query: read-only, offline, and `pkit sync` provisions its dependencies. It fails on:

- a place outside every root that holds a document nothing else claims, with no assignment; an assignment naming a place `friction.places` does not declare, or a space nobody declares; a place assigned twice;
- a project place equal to or enclosing a root; a file two project places claim with equal specificity;
- a decision record, a rule-set file or another capability's artefact carrying `reader` or `kind` — none is ever a page;
- a page whose `reader` or `kind` does not fit `schemas/page.schema.json`;
- an entry point that is not a document of its space — under its root or in a place assigned to it;
- a definition outside `<definitions>/rule-sets/`, or one that does not inherit `living-docs:LDOC`.

It reports, without failing: a space with no definition yet, roots that are the same folder or nested (onboarding separates them), and — in its summary — the unclassified documents and whether each entry point is a page yet. A synced tree declared as a place is the core's `synced-place` finding, under `friction` (above).

**Dormant: reader resolution.** Whether a page's `reader` names a reader of the readers point is not checked until that point ships (below); until then the reader's shape is checked, and the validator's summary says so.

## Connections (design-ahead)

Declared in the decision; the package metadata gains them with the next increment. The capability provides the `pkit::documentation` role (COR-053); `pkit::` is this distribution's literal for the methodology's publisher qualifier ([the lifecycle README, "The methodology's literals"](../../lifecycle/README.md#the-methodologys-literals)).

- **Accepts** `pkit::documentation:readers`: who reads and what they need. It starts with a built-in `user` and `maintainer`. You can add or override readers in a [project file](../../lifecycle/README.md#where-a-project-filler-file-lives-the-address-to-path-mapping), and an analysis capability, such as software-analysis, can supply them too.
- **Accepts** `pkit::documentation:reading-evidence`: results of executed checks that follow the docs, such as a simulated user running a guide. Advisory.
- **Contributes** to `pkit::work-tracking:doc-check` with page friction and uncovered surface. Inert when no work-tracking capability is installed.

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
5. **Repeat until done.** Onboarding is complete when the declared surface is covered and no page is left unanchored without a reason you accepted — `pkit friction check --all` shows both measures.

From then on, the friction check flags pages as their anchors change, and the agent proposes each fix.

## What's shipped now, what's next

Shipped: the decision, the project configuration's schema, the declaration of the roots as places and of the definitions location, the validator, the `LDOC` rule set, the space-definition template and the signpost page template with the page's schema, and the `living-docs` agent that proposes fixes, performs reader-review and onboards existing documentation. Next come the connections: the readers and reading-evidence points, and the contribution to the documentation check.

## Citing this capability's decisions

`[living-docs:DEC-001-living-docs-discipline]`; a rule of the shared method, `[living-docs:RS-LDOC-003]`.

## Dependencies

None. It works without analysis, work-tracking or testing capabilities, and each can enrich it.
