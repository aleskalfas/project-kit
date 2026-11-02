---
variant: universal
reader: act-ai-agent
kind: reference
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/agents.py
        - src/project_kit/agents_overlay.py
        - src/project_kit/agent_policy.py
        - src/project_kit/refs.py
        - src/project_kit/friction_check.py
        - src/project_kit/docs_roots.py
        - src/project_kit/install.py
        - src/project_kit/sync.py
        - src/project_kit/capabilities.py
        - .pkit/lifecycle/ownership.py
        - .pkit/adapters/claude-code/deploy-agents.sh
        - .pkit/adapters/claude-code/_resolve_agent.py
        - .pkit/agents/core/rule-set-reviewer.md
        - .pkit/agents/core/methodology-reviewer.md
        - .pkit/adapters/claude-code/harness-support.yaml
        - .pkit/agents/project/overlay.yaml
      record: [COR-001, COR-005, COR-006, COR-011, COR-013, COR-014, COR-015, COR-024, COR-026, COR-028, COR-049, COR-050, COR-051, COR-053, COR-057, COR-058, COR-060, COR-062, COR-064, COR-068, ADR-051, ADR-052, "ADR-065#11"]
      artefact:
        - .pkit/agents/hooks.md#
        - .pkit/agents/storyboards.md#
        - .pkit/agents/hooks.md#declaration
        - .pkit/agents/hooks.md#provider-value-syntax
        - .pkit/agents/hooks.md#hook-signature
        - .pkit/agents/hooks.md#naming
        - .pkit/agents/hooks.md#provider-precedence
        - .pkit/agents/hooks.md#unsatisfied-needs
        - .pkit/agents/storyboards.md#when-a-definition-takes-one
        - .pkit/agents/storyboards.md#structure
        - .pkit/agents/storyboards.md#location-and-lifecycle
        - .pkit/agents/storyboards.md#frontmatter-declaration
        - .pkit/agents/storyboards.md#authoring
        - .pkit/lifecycle/README.md#seed-paths
        - .pkit/decisions/README.md#citing
        - .pkit/adapters/README.md#primitives-the-lifecycle-calls
---

<a id="agents"></a>
# Agent definitions

<a id="where-this-content-came-from"></a>

An agent definition gives an AI agent a standing role ([COR-013](../decisions/core/COR-013-agent-architecture.md)). Its front matter declares what the agent reads, owns and needs, and its body says how the agent works. Definitions come from core, from an installed capability and from the project. Why they exist, and how people dispatch the reviewers and write their own, is in [the agents guide](https://github.com/aleskalfas/project-kit/blob/latest/docs/agents/README.md).

## Contents

<!-- pkit:contents -->
- [Layout](#layout)
- [Frontmatter schema](#frontmatter-schema)
- [Body conventions](#body-conventions)
- [The reference graph](#the-reference-graph)
- [Adopter overlay](#adopter-overlay)
- [Model and effort](#model-and-effort)
- [Deploy mechanics](#deploy-mechanics)
- [The rule-set reviewer](#the-rule-set-reviewer)
- [Authoring a definition](#authoring-a-definition)
- [The pages beside this one](#the-pages-beside-this-one)
<!-- /pkit:contents -->

## Layout

The area holds the definitions core ships and those the project writes, each in one of two forms (COR-015):

```
.pkit/agents/
├── README.md                    # this file
├── hooks.md                     # a page beside it ("The pages beside this one")
├── storyboards.md               # a page beside it
├── core/                        # core's definitions, refreshed by every sync
│   ├── <name>.md                # flat form: a definition with no helper
│   └── <name>/                  # folder form: a definition with helpers beside it
│       ├── <name>.md            #   the definition, named after its folder
│       └── storyboard.md        #   a helper, such as a storyboard
└── project/                     # the project's own, which no sync writes
    ├── overlay.yaml             # the project's paths for each category ("Adopter overlay")
    ├── <name>.md
    └── <name>/
        └── <name>.md
```

- **The flat form** is the default. A definition takes the folder form once a helper sits beside it.
- **`core/`** is core's. Sync refreshes it, and the project never edits it (COR-001).
- **`project/`** is the project's own. Sync reads it to deploy the definitions, and never writes it.
- **`overlay.yaml`** stands at the top of `project/`. Its per-agent overrides sit inside it, under `overrides:`.
- **A capability's definitions** take the same two forms in its own `agents/` folder, `.pkit/capabilities/<capability>/agents/` (COR-026).

## Frontmatter schema

Agents and skills share one front-matter shape for the fields of the reference graph (COR-013 point 2). Each leaves out the fields that do not apply to it:

```yaml
---
name: release-checker
description: Checks a release before it is tagged.
tools: [Read, Grep, Bash]
model: sonnet                         # optional; absent is inherit ("Model and effort")
effort: high                          # optional; absent is inherit
reads:
  paths:                              # files and folders
    - .pkit/decisions/README.md
    - CLAUDE.md
  records:                            # decision records, by id
    - COR-013
  patterns:                           # overlay categories, each an optional read
    - <project-conventions>
owns:                                 # the paths the agent answers for
  - <release-notes>
needs:                                # the hooks the agent invokes (hooks.md)
  - project.render-notes
---

# Release Checker

You are the **release checker** for this project. …
```

What each field holds:

- **`name`, `description`:** the agent's name, and the one line that tooling shows of it.
- **`tools`:** the tools the harness grants the agent, by the harness's names, such as Claude Code's `Read`, `Edit` and `Bash`. The adapter writes them in the harness's form at deploy.
- **`model`, `effort`:** the model the agent runs on, and the effort it reasons at. Both are optional, and absent means inherit ("Model and effort" below). Agents only.
- **`reads`:** what the agent consults at task time, in three channels:
  - **`paths`** names files and folders, and **`records`** names decision records by id, such as `COR-013`. A category named in either is a required read: while the overlay leaves it undefined, the deploy skips the agent.
  - **`patterns`** names overlay categories, each written as its placeholder, `<category>`. A category named only here is an optional read: while it is undefined, the deploy drops the item and deploys the agent without it.
  - **Which to use:** a read the agent cannot work without goes in `paths` or `records`. A read whose absence is a normal early state goes in `patterns`, such as a corpus of the project's conventions.
- **`owns`:** the paths the agent answers for, each a literal path or a `<category>` placeholder the overlay resolves. Agents only.
  - Each path is meant to have one owning agent, and `pkit refs validate` reports two ("Exactly-one-owner over `owns:`" below).
  - A category core declares write-carrying, which a core definition writes and the project names, follows four more rules ("Write-carrying categories" below).
  - A definition whose `owns:` resolves to decision records cites the rule for editing them, the decisions README's "Refining an accepted record". It does not restate the rule, since agents reference rather than embed (COR-006).
  - **A command's writes** are the command's, where one of the methodology's mutating commands makes them, and `owns:` does not declare them. The agent's body, or a skill it hands the work to, names the command and when to run it (COR-013 point 2). A write the agent makes itself, with a file tool or any program through a shell, is never a command's write.
- **`needs`:** the hooks the agent invokes ([`hooks.md`](hooks.md)).
- **`answers`:** the hooks a skill provides. Skills only.
- **`gates`:** the records whose acceptance a skill needs before it runs. Skills only, and each entry counts as a `reads.records` entry too.
- **`storyboards`:** the storyboards the agent drives, each by its file name beside the definition ([`storyboards.md`](storyboards.md)).

## Body conventions

A body cites what its front matter declares, in forms the validator reads without parsing free prose (COR-013 point 3). What counts as a citation:

- **A path** in backticks, where it holds a `/` or a known file extension, such as `` `.pkit/decisions/README.md` ``. A Markdown link's target counts too, unless it is a URL.
- **A record id** as a bare token: `COR-NNN`, `PRJ-NNN` or `ADR-NNN`.
- **A capability's decision** in brackets, `[<capability>:DEC-NNN-<slug>]`. It is not declared in the front matter, and must name a decision file of an installed capability.
- **A rule id,** `RS-<SET>-NNN`, an extension point, `RS-<SET>-NNN#<point>`, or a component's rule with its component, `[<component>:RS-<SET>-NNN]` (COR-051). It is not declared in the front matter either, and must name a rule of an installed rule set.
- **A role or point address** in brackets, such as `[pkit::documentation]` or `[pkit::documentation:readers]` (COR-053). It must name a role or point an installed capability declares. A bracketed token that holds `::` and is no address is reported as malformed.
- **A hook name:** `<topic>.<operation>` or `<topic>.<provider>.<operation>` ([`hooks.md`](hooks.md)).
- **An operational rule** by its layer and number, such as "core rule 16", or by its id in a loaded set, such as `RS-OPS-NNN` (COR-068). `pkit refs validate` warns, without failing, of one that is missing or retired.
- **A point of a record,** such as `COR-NNN point N`, `COR-NNN#N` or `[<capability>:DEC-NNN] point N` (COR-058). `pkit refs validate` warns, without failing, of a point its record neither holds nor retires ([the decisions README, "Citing"](../decisions/README.md#citing)).
- **Not counted:** anything inside a fenced code block, an HTML comment or strikethrough.

So cite a path in backticks, a record by its id and a hook by its name.

**Intermediate files.** Every shipped definition's body ends with the same section, `## Intermediate files`, which the authoring command stamps ("Authoring a definition" below). It tells the agent to keep its intermediate files in the agent workspace, `.agent-workspace/` at the repository root, and nowhere else outside the repository. It says to write them with the file tools, since a shell redirect there is judged as any shell write is (core rule 16). Keep its words the same in every body, so that one search finds every definition that carries it.

**Reviewers.** A reviewer is an agent that judges work and returns a verdict or findings, such as COR-024's reviewers or a capability's review panel. What its read-only means:

- **It changes nothing it judges.** It never changes the work under review or the repository the work lives in. It edits no tracked file, and stages, commits and pushes nothing, since its verdict is worth only its independence. That is the whole claim.
- **It may still write.** A reviewer with a shell among its tools may need working files to review well, such as these:
  - a dumped diff
  - a script
  - captured output
  - a reproduction that runs a payload to prove a defect
- **Its working files** go in the agent workspace, never loose in the repository, where an author's `git add` sweeps them into a commit. They never go in `/tmp/` either. A review leaves no file of its own outside the workspace.
- **One section for the role.** Every reviewer that can run commands carries the same section, `## What read-only covers`, word for word, just before its `## Intermediate files`. Copy it from a shipped reviewer, such as `.pkit/agents/core/methodology-reviewer.md`. State any read-only claim elsewhere in its body or its description with the same scope.

**Friction writers.** An answer on an artefact is decided as COR-050 point 3 sets out. It is a revalidation, a deferral, or a revisit entry for a target of the artefact's links (COR-050 point 16). The writers put it in an answer file of the change's own (COR-062 point 1).

A project's existing answers move out of the artefacts' blocks once (COR-062 point 11). The CLI reference's "Friction checks" says where the writers write until then.

An answer a change owes may be written by the agent making the change, and is then checked by a reviewer other than that agent. Where a person skipped that review on record, or the project chose no such reviewer, it stands unchecked.

Any other answer is a person's decision, and so is a reason for having no anchors (COR-050 point 1). A delegate may decide them in a person's place, where a person who decides what reaches the default branch named one (COR-064). Which agent may write one, and when, depends on whether its own change owes the answer:

- **An agent making a change** may run `pkit friction revalidate`, `pkit friction defer` and `pkit friction revisit` for answers its own change owes: those the change check (`pkit friction check`) asks of it. It asks nobody first. Its body names the commands it may run and what this item asks of it (COR-013).
  - **The reviewer.** A reviewer other than this agent, one the project chooses, checks every `unchanged` and `deferred` reason among those answers against the change. It checks them from the change check's own list, and blocks the merge when one does not hold. The reviewer also checks that each target the change revisited by changing it meets the change to the source (COR-050 point 16).
  - **Deferrals.** Each deferral, and each `deferred` revisit entry, the agent writes names an open follow-up in its reason.
  - **The change check's list.** It states its question once: these documents rely on something the change modifies, and each answer says whether the document is still true. One flag marks a revalidation that replaces revalidations answered apart, and the reviewer checks that its reason judges their combined state (COR-062 point 7). Each line of the list names:
    - the document
    - the anchors the change modified that it relies on
    - the outcome in plain words, such as "still accurate", with its words quoted in full
    - every flag the check puts on it
  - **Committing.** The agent commits what the writers write with its change, a new answer file among it.
  - **An `updated` artefact.** For each artefact the change revalidated as `updated`, the agent says in one sentence what changed in it. It says so in the pull request or, on a direct commit, to the person it works for. The reviewer checks that sentence against the diff. It blocks the merge, or the direct commit, when an `updated` artefact has no sentence or one that does not match what changed.
  - **The person.** The merge authoriser is told those sentences and what is left out of date, until which follow-up, as information, not a gate (COR-050 point 3). On a direct commit to the default branch, the reviewer, where the project chose one, checks before the commit. The person the agent works for is told before it.
  - **A session without an agent body.** A session the person works in without an agent body follows the core rules, "Answers on artefacts".
- **An agent whose task is the answer itself,** resolving friction that no change of its own raised, runs a writer only when all four hold:
  1. **Its body, or a skill its body hands the work to, names the writers it may run and these conditions.** `owns` covers no command's write (COR-013).
  2. **It can ask the person, or the delegate decided.** The decision is the person's, or the delegate's where the default branch's configuration names one (COR-064 point 2). So the agent runs a writer only in the first two cases below, and the last two say how it tells whether it can ask:
     - in a session where its question reaches the person and the answer comes from them
     - once the delegate decided the answer
     - **Telling whether it can ask.** It tells from the question itself, never from the wording of its task. With no tool for asking, or when the question fails, is refused or goes unanswered, it cannot ask. Then, unless the delegate decided the answer, it returns the commands and runs none.
     - **Dispatched by another agent.** An agent another agent dispatched does the same, unless the adapter in use declares that its question reaches the person. Where an adapter names no such tool, no agent of this kind runs a writer but for an answer the delegate decided.
  3. **The person, or the delegate, was shown every word before it is written.** That is the artefact, the outcome, and the justification or reason exactly as the command will write it. Several answers may be shown together and accepted together, and whoever decides may refuse any. A reworded answer is shown to the person again, but for a rewording the delegate made itself, whose words are written as it gave them.
  4. **It is not a reviewer.** An agent that judges work writes nothing on what it judges ("Reviewers" above), so a reviewer runs no writer.
- **An agent named as the delegate** decides, in a person's place, the answers no change owes (COR-064 point 1). The paragraph after this list names them. Its body says when it decides as the delegate (COR-013).
  - **Where.** Only where the default branch's configuration names it, and under its definition as the default branch holds it.
  - **Whose drafts.** Only an answer another agent drafted. Never one of these:
    - one it proposed
    - one its own change found unasked
    - one a component's record keeps for a person
  - **How.** It reads every word, as condition 3 asks of the person. Where what the artefact rests on changed after it decided, it decides again before the answer is written. With each answer it does one of these:
    - accepts it
    - declines it
    - rewords its words without changing its outcome or its content
  - **From the files.** It judges from what the artefact and its anchors hold. An account, such as a commit message, a pull request's text or a drafter's evidence, is a lead, never a ground. It refers to a person any answer only such an account could settle, whether a change was meant among them.
  - **Never** what COR-064 point 6 leaves to a person.
  - **No reviewer.** Deciding an answer is no review: the delegate judges a draft before anything writes it, not work under review. So condition 4 does not bar it from writing an answer it decided.
  - **Only where a reviewer checks.** Where the project chose no reviewer of the answers, or chose the delegate itself, it decides nothing.
  - **The person is told** each answer it decided, with the change that writes it, and each it declined. The person is told in the delegate's own report and with that change, as information.

Any agent writes any other answer, on an artefact or for a target a change was not asked about, only under the four conditions above. The same holds for every reason for having no anchors. A reviewer checks every such answer and reason a change writes, whoever decided it, from the change check's own list (COR-064 point 4). That reviewer is neither the delegate nor the answer's drafter, and blocks the merge when one does not hold.

Commands an agent returns are run by one of these:

- the person
- a session the person works in without an agent body, once the person has accepted them
- an agent, once the delegate decided them
- the agent making the change, for answers its own change owes

`pkit friction record-status` is the after-merge job's (COR-050 point 10), and no agent's. Nothing at run time stops an agent from running a writer outside these conditions. As with `owns`, the rule is stated in the agents' files and honoured as discipline.

<a id="reference-graph-and-bidirectional-consistency"></a>
## The reference graph

`pkit refs validate` builds the reference graph from every agent's and skill's front matter and body, and checks it in both directions (COR-013 point 3):

- **Forward:** each entry of `reads`, `owns`, `needs` and `answers` appears in the body. An unused declaration is reported.
- **Backward:** each path, record id and hook the body cites is declared in the front matter. An undeclared citation is reported.
- **How a command grades it:** `pkit refs validate` fails on a finding of either direction, and exits 1. `pkit validate` reports the same finding as a warning in its `refs` member, and passes, since the body is read by a heuristic.
- **Every other finding** of the graph fails both commands, such as these:
  - a path with two owners
  - a hook with no provider
  - a storyboard one side leaves out
- **The exceptions** warn in both commands: a cited point its record does not hold, and a cited operational rule that is missing or retired.

**What the backward check leaves out.** It is meant for reads whose place an overlay can move, so three kinds of path in a body need no declaration:

- **A path that opens with `#` or `./`,** such as a link to a section or to a file beside the body.
- **A path to a decision record,** one under a `decisions/` folder or named as a record's file, such as `[COR-026](../decisions/core/COR-026-agent-placement-by-discipline.md)`. The record's id is the reference, checked through `reads.records`, and `refs rot` still checks that the file exists.
- **A path inside the citing capability,** in a capability's agent or skill, such as `scripts/move-issue.py` or a sibling sub-procedure. A path outside the capability, or into another tier, is still reported.
- **Never exempt:** a record id or a hook name, even inside a link.

The CLI reference describes the other commands of the `refs` family, which read or rewrite the graph.

<a id="the-matrix"></a>
### Exactly-one-owner over `owns:`

`pkit refs validate` also checks who answers for each path. It compares the resolved paths of each agent's `owns:`, with each placeholder expanded through the overlay as the deploy expands it (COR-013 point 5):

- **Overlap** is one path containing another, or two equal paths, between two distinct agents. Nesting inside one agent's own set is fine, such as a folder and a file in it.
- **Reported, never settled.** The finding names both agents, both paths, and the overlay category a resolved path came from. No precedence picks a winner. Resolve it by reassigning an `owns:`, or by pointing the category elsewhere.
- **Clean:** an entry that resolves to no path, such as one of `code-paths: []`. An entry whose category the overlay does not define is clean too, since the deploy skips that agent and `pkit agents` names the category.
- **One owner for each name.** Only the definition that deploys counts as an owner ("Name-collision precedence" below).
- **What it leaves out:** whether a resolved path exists, which `refs rot` checks. Nothing at run time stops an agent from editing outside its `owns:`. Ownership is checked at validation, and kept as discipline at run time.
- **Placeholders in the body.** The bidirectional check finds a `<category>` entry by its placeholder in the body, not by its resolved paths. A core definition that cited a project's real paths would break project-neutrality, so its body carries the placeholder.

## Adopter overlay

The overlay, `.pkit/agents/project/overlay.yaml`, names the project's paths for each category that a definition names by a placeholder, `<category>` (COR-013 point 5). The project writes it, and the deploy reads it:

```yaml
# .pkit/agents/project/overlay.yaml

# Categories: each applies to every agent unless an override replaces it.
code-paths:
  - src/myproject/
test-paths:
  - tests/
project-root-docs:
  - CLAUDE.md
  - README.md

# A write-carrying category, which ships as an explicit empty list.
process-authoring-targets: []

# A category of the project's own, for its own agents.
acme-deploy-configs:
  - deploy/staging/

# Per-agent overrides: each replaces the value for the named agent only.
overrides:
  qa-engineer:
    code-paths:
      - tests/integration/
      - tests/unit/
  critic:
    model: sonnet     # not a category: the agent's model and effort ("Model and effort")
    effort: medium
```

**How a value resolves:**

1. Start from the top-level categories.
2. For the agent named under `overrides.<agent>:`, each category there replaces the top-level value whole, never merged with it. To extend a value, copy the top-level entries into the override. Two keys there are not categories: `model` and `effort` ("Model and effort" below).
3. Write the resolved paths in place of each placeholder in the front matter, and the deployed copy into the harness's place. The body keeps its placeholders as written.

**An unknown override** is ignored: a category under `overrides:` for an agent no source ships, or one no definition of that agent names. Nothing reports it. A `model` or `effort` there that the harness does not accept is still reported ("Model and effort" below).

**The first install** writes the overlay with a value for each category core's definitions name, so they deploy before the project names a path. A missing overlay comes back as "Diagnosing + repairing the overlay" below says.

### An undefined category

What the deploy does with a category the overlay does not define depends on the channel that names it:

- **In a required channel,** `owns`, `needs`, `answers`, `reads.paths` or `reads.records`, the deploy skips the agent, loudly, and deploys the rest.
- **Only in `reads.patterns`,** an optional read: the deploy drops the item, and deploys the agent without it. A category named in both channels is required.
- **A bare key,** `category:` with no value, is undefined. An explicit empty list, `category: []`, resolves to no path. A bare optional key still deploys its agent, with a warning, since it is usually a stub left unfilled.

### Write-carrying categories

Core declares a category write-carrying where a core definition edits its paths and only the project can list them. The architect's categories are not among them, since each has a conventional folder. A write-carrying category follows four rules. One ships today:

| Category | Consumer | Meaning |
|---|---|---|
| `process-authoring-targets` | the core `process-author` agent | the project's own process-definition files and predicate-script locations, the paths that agent may edit |

The four rules:

1. **It ships as an explicit empty list,** `process-authoring-targets: []`.
   - `[]` resolves to an empty `owns:`, so the agent deploys inert, owning nothing. A bare or absent key does not resolve, so the agent is skipped.
   - The first install writes the `[]`. An install from before the category upgrades into the skipped state, since sync adds no key to the project's overlay. `pkit agents reconcile --write` fills the `[]` ("Diagnosing + repairing the overlay" below).
2. **Files, not subtrees.** List definition files and predicate-script folders, not a capability's whole subtree. Never list a capability's `package.yaml`, since registering a predicate is the process commands' stamp.
3. **Nothing sync manages.** No entry may resolve into content the next sync overwrites, which is the no-shared-files invariant at the agent's surface (core rule 1). The deploy's resolver refuses such an entry, names the path, and skips the agent. `.pkit/lifecycle/ownership.py` decides what sync manages, and every adapter's resolver imports it:
   - core's areas, and a shipped capability's own subtree: managed
   - that capability's `project/` folder: the project's
   - an incubated or unregistered capability's subtree: the project's
   - every other declared project-tier position, such as an adapter's `settings/project/`: the project's
4. **One consumer.** A category a core record introduces is named by exactly the agent that record names. A core definition naming a write-carrying category another record introduced is a red flag in review. Categories the project defines are its own to share across its agents.

The `adopt` command cannot serve a write-carrying category, since core cannot know the project's paths, and it says so. Run `reconcile --write`, then name the project's paths.

### Diagnosing + repairing the overlay

Three commands diagnose and repair the overlay, each described below (COR-013). The two that write fill a category with its conventional folder where it has one.

**Where a conventional folder lies.** It is a sub-path of the project's internal documentation root (COR-049 point 4):

- `architecture-docs` is `<root>/architecture`, and `adr-records` is `<root>/architecture/decisions`. With the default root, `docs/`, they are `docs/architecture/` and `docs/architecture/decisions/`.
- **A recorded path stays.** `reconcile --write` and `adopt` write the path uncommented, with a `recorded by` note, and a later change of the root never moves it (COR-049 point 5).

#### `pkit agents`

`pkit agents` reports each definition as deployable or skipped, with each category it lacks, and its effective model and effort. It writes nothing, since the deploy is the sync's.

#### `pkit agents adopt <agent> [--yes]`

`pkit agents adopt` fills each undefined category of the agent that has a conventional folder, in one command:

1. It creates the folder if absent, with a seed README on its purpose. A folder that exists but holds nothing gets the README too.
2. It writes the category into the overlay, uncommented, with that path, and never over a value the project set.
3. It runs the adapter's deploy, so the agent lands in `.claude/agents/` at once.

**What it asks.** A category recorded over a folder that holds documents puts them within the reach of the category's agents. So it takes consent (COR-049 point 5):

- **Before it writes,** `adopt` reads which folders already hold documents, for every category at once.
- **Where one does,** a terminal is asked once for the run. The question lists each `category = path` with the agents that reach it, and the rest of the run beside it. `--yes` consents without a prompt.
- **Off a terminal without `--yes`,** the run refuses with exit 1. It names the command with `--yes`, and `reconcile` to see the change first.
- **A "no" or a refusal** writes nothing at all: no folder, no overlay line and no deploy. A folder `adopt` creates, or one that holds nothing, is recorded without asking.
- **Each recording** prints these:
  - what it recorded
  - the root its path came from
  - where to change it

**When it stops.** A second run on an adopted agent changes nothing, asks nothing, and deploys again. It errs on these:

- an unknown agent
- an agent that names no overlay category
- a required category with no conventional folder, for which it names `reconcile`
- a write-carrying category, since core cannot list the project's paths for it

An optional category with no conventional folder is no prerequisite: `adopt` leaves it undefined, names it as optional, and deploys the agent.

#### `pkit agents reconcile [--write]`

`pkit agents reconcile` surfaces each category a definition names and the overlay leaves undefined. It is a dry run by default, and `--write` writes. For each category, it acts by state:

1. **Missing and write-carrying:** written uncommented as `<category>: []`. The agent then deploys inert rather than being skipped, as on a fresh install.
2. **Missing, with its conventional folder present:** written uncommented with that path, so the next sync deploys the agent. An example is `adr-records` with `docs/architecture/decisions/`.
3. **Missing, only an optional read, with no conventional folder:** a commented stub is appended, framed as an optional read. The agent deploys without it, so uncomment it only to give the agent the project's corpus.
4. **Missing, required, with no conventional folder:** a commented stub is appended, such as `# architecture-docs:`, with guidance on the path to give. The agent stays skipped until a path is set and sync runs, or until `adopt` creates the conventional folder.
5. **A commented stub already there:** nothing is appended again. For a required stub it reports that a path is needed, and for an optional one that the agent deploys already.
6. **Defined,** with paths or an explicit `[]`: nothing is written, and no value the project set is overwritten.

More of `reconcile`:

- **A missing overlay.** With `--write`, `reconcile` creates the overlay from the seed the first install writes, and writes nothing else in that run. The next dry run shows each category the seed leaves undefined.
- **Only it writes a seed path.** Sync creates no seed path, so a deleted overlay otherwise returns only at the next upgrade to a new release ([the lifecycle README, "Seed paths"](../lifecycle/README.md#seed-paths)). `adopt` names this repair where the overlay is missing.
- **When to run it:** for an overlay older than a newly shipped agent's categories. The repair is an explicit command, never a write by sync.
- **`--write` is the consent.** The dry run lists each fill as `category = path`, with the agents that reach it, as `adopt`'s question does. A command that shows what it would record until told to write takes `--write` as its consent (COR-049 point 5). So `--write` records over a folder that holds documents without a prompt.

## Model and effort

An agent runs on its caller's model and effort, unless its definition or the overlay says otherwise. Dispatched from a session, it inherits the session's. Started headless, it reads the operator's user settings.

| Key | Accepted values | Absent |
|---|---|---|
| `model` | `inherit`, a harness alias or a full model name. The aliases are `sonnet`, `opus`, `haiku`, `fable`, `best`, `opusplan`, `sonnet[1m]`, `opus[1m]` and `fable[1m]`. A full name is `claude-…`, and may name its provider first, such as `us.anthropic.claude-…`. | inherit |
| `effort` | `inherit`, `low`, `medium`, `high`, `xhigh` or `max` | inherit |

The values are those of Claude Code, the one harness an adapter ships for today.

**Precedence,** for each key on its own:

1. the overlay's `overrides.<agent>.model` or `overrides.<agent>.effort`, which is the project's, so it wins over a shipped value without an edit of a core file
2. the agent's front matter
3. inherit

**What is written.**

- **`inherit`,** like an absent or bare key, writes no key into the deployed copy, so the harness's default applies. An override of `inherit` is how a project resets a shipped value.
- **The shipped definitions** set neither key. This is the mechanism, not a policy.
- **A value outside the vocabulary** is never written:
  - The deploy drops it, and the agent deploys and inherits.
  - The run prints a `warning` line naming the value.
  - The reference graph's checks report it as an error in both commands ("The reference graph" above). They report it at the agent's file for a front-matter value, and at `overlay.yaml` for an override.
- **Reported by `pkit agents`.** Each row shows the effective value and where it came from, such as `model inherit`, `model sonnet` or `effort high (overlay)`, and a refused value as refused.

## Deploy mechanics

Each adapter deploys the definitions its own way (COR-005). For Claude Code, `.pkit/adapters/claude-code/deploy-agents.sh` does it, and `pkit init` and `pkit sync` run it:

1. It lists each name in `.pkit/agents/core/`, `.pkit/agents/project/` and each capability's `agents/` folder, in either form.
2. It takes one source for each name ("Name-collision precedence" below).
3. It resolves the source's front matter through the overlay ("Adopter overlay" above), and carries its model and effort ("Model and effort" above).
4. It rewrites each storyboard the source names by its file name to the storyboard's path from the project's root ([`storyboards.md`](storyboards.md)).
5. It ends the body with one sentence, which replaces the session scratch directory the harness's environment names with `.agent-workspace/`.
6. It writes the copy to `.claude/agents/<name>.md`, with a deploy mark as the front matter's first line: `# managed-by: project-kit (deploy-agents.sh) — do not edit; regenerated on sync`.

What it reports, a line for each definition, such as `created`, `updated`, `exists`, `skipped`, `removed` or `warning`:

- **A file without the mark** at the copy's path is left as it is, and reported `skipped`. It is the project's own, or a copy from before the mark. To have the deploy write its own, delete the file and deploy again.
- **A marked copy that no source ships any more** is removed. To keep one, delete its mark line, and it reads as the project's.
- **A folder with no definition named after it,** such as one half written, is skipped, and the rest deploy.
- **A skipped definition** never stops the others. A copy an earlier deploy wrote stays as it was. The run ends with the count skipped, and the remedies.

Beside the deploy:

- **The undeploy.** The adapter's `undeploy-capability.sh <name>` removes one capability's deployed agents and skills, where the capability is unregistered and its files stay. The lifecycle calls it by name, and knows no harness path ([the adapters README, "Primitives the lifecycle calls"](../adapters/README.md#primitives-the-lifecycle-calls)).
- **Grants.** Where the adapter's permission hook is registered, the permission model decides each call of a dispatched agent for the subject `agent:<name>`. It applies that subject's grants and those to `all` (COR-028). The permissions reference says how a call's subject is found.
- **Dispatching.** A session dispatches an agent by its definition's name, and gives it no name of its own. While Claude Code's agent teams are on, a named one's result arrives cut at 4064 characters, as the adapter declares.

### Name-collision precedence

Three places can ship a definition of one name, and the deploy takes one, in this order:

1. **The project's,** in `.pkit/agents/project/`, wins over every other. The project keeps the last word on its agents.
2. **A capability's,** in `.pkit/capabilities/<name>/agents/`, wins over core's. A capability ships a core agent's name on purpose, as its discipline's specialisation of the core default.
3. **Core's,** in `.pkit/agents/core/`, is the fallback.

More on the order:

- **Read the same way** by each command that names the definition that deploys. These are `pkit agents`, the ownership check of `pkit refs validate`, and `pkit new storyboard` without `--namespace` ([`storyboards.md`](storyboards.md#authoring)). So where a capability ships a core agent's name, the capability's is the one deployed.
- **Between two capabilities** there is no precedence. A capability's install names each agent another capability ships under the same name, and asks for each: `override`, `skip` or `inspect`. `skip` keeps the installed agent.
- **A collision that reaches the deploy** is not refused: the first capability by name wins. Resolve it in one of these ways:
  - rename an agent
  - skip it at install
  - uninstall a capability
  - ship a project agent of that name
- **Rare by design.** An agent that implies a discipline belongs in its capability, not in core (COR-026). A capability and core share a name only to override on purpose.

### Why copies, not symlinks

A deployed definition is a resolved copy of its source, never a symlink to it. Skills deploy as symlinks, since a skill's deployed text is its source's.

- **Why:** the copy differs from its source. Its front matter holds the overlay's paths for the placeholders, the model and effort, each storyboard's path and the deploy mark. Its body ends with the workspace sentence.
- **What follows:** an edit of a source in `.pkit/agents/` reaches the harness only once the deploy runs again, such as at the next sync.

## The rule-set reviewer

The core agent `rule-set-reviewer` judges one change against the accepted rules that bind on each artefact the change alters or brings under a rule ([COR-057](../decisions/core/COR-057-rule-set-reviewer.md)). It reviews the diff, beside `convention-compliance-reviewer` in the reviewer stack (COR-024).

- **What it judges.** It reads the rules only from the rule sets, through the command that lists what a change alters and brings under a rule. It judges only the text the change owns, and only the parts of a rule that no check enforces. Its body holds no rule.
- **What a change brings under a rule.** A change that makes a rule bind on an artefact owns the whole artefact for that rule. It may do so by widening a set's scope, accepting a rule, updating a pin or typing a place. The reviewer judges all of the artefact under that rule, even where the change edits none of it.
- **A break there** is a settled break where the rule's text settles it, whatever brought the artefact under the rule. [COR-060](../decisions/core/COR-060-brought-under-breaks.md) names the author's ways out of one. The reviewer's answer names those rules on each artefact, and lists apart each artefact brought under a rule unaltered.
- **Its form** comes from whoever dispatches it: the verdict line, and the mark of each kind of finding. With none named, it states its verdict and each finding's kind in words.
- **Advisory.** Its verdict holds a change only where a gate requires it.
- **Dispatching it** on a change from a base to a head: run the command below to see what it will judge. Then dispatch it, naming the same base and head and the form. An artefact no rule binds on leaves it nothing to judge.

```
pkit rule-sets altered --base <base> --head <head>
```

<a id="authoring-an-agent"></a><a id="core--project-split"></a>
## Authoring a definition

Stamp a definition with the command below, through its paired skill, `agent-author` (COR-005, core rule 3). The skill carries the choice of namespace and name, the drafting of the body, and the citation discipline.

```
pkit new agent <namespace> <name> [--with-storyboard]
```

The namespace says where the definition lives, by the universal-applicability test (COR-014):

| Namespace | Stamps at | For |
|---|---|---|
| `core` | `.pkit/agents/core/<name>.md` | a role any project can use, whatever it installs, such as reviewing records or conventions |
| `project` | `.pkit/agents/project/<name>.md` | a role tied to the project's own stack, such as a QA engineer or a domain reviewer |
| a capability's name | `.pkit/capabilities/<capability>/agents/<name>.md` | a role that implies the capability's discipline (COR-026), such as `software-engineering`'s `software-engineer` |

What the command does:

- **Refuses an unknown capability,** listing those that exist. It creates the capability's `agents/` folder on first use.
- **Refuses a taken name,** in core, the project or any capability, since the deploy keeps one definition for each name.
- **Refuses a namespace the project receives by sync:** `core`, outside the methodology's source, and a capability that is not the project's own. Such an agent is authored where its source is kept, since the next sync would overwrite it (core rule 1).
- **Refuses a name that is not kebab-case,** and writes nothing.
- **Stamps** the front matter, with `tools: [Read, Glob, Grep, Bash]` and empty lists, the body's sections, and the `## Intermediate files` section ("Body conventions" above).
- **`--with-storyboard`** stamps the folder form, with a storyboard beside the definition, each declaring the other ([`storyboards.md`](storyboards.md)).

## The pages beside this one

Each part of the agent definitions is described here, or on one of the pages beside this one:

- [`hooks.md`](hooks.md) — how an agent declares the operations it invokes, and how one provider is chosen for each.
- [`storyboards.md`](storyboards.md) — storyboards: when a definition takes one, their structure, their place and their front matter.

**Where each section that left this page went:**

- <a id="hooks"></a>"Hooks" is [`hooks.md`](hooks.md).
- <a id="declaration"></a>"Declaration" is [`hooks.md`, under the same heading](hooks.md#declaration).
- <a id="provider-value-syntax"></a>"Provider value syntax" is [`hooks.md`, under the same heading](hooks.md#provider-value-syntax).
- <a id="hook-signature"></a>"Hook signature" is [`hooks.md`, under the same heading](hooks.md#hook-signature).
- <a id="naming"></a>"Naming" is [`hooks.md`, under the same heading](hooks.md#naming).
- <a id="provider-precedence"></a>"Provider precedence" is [`hooks.md`, under the same heading](hooks.md#provider-precedence).
- <a id="unsatisfied-needs"></a>"Unsatisfied needs" is [`hooks.md`, under the same heading](hooks.md#unsatisfied-needs).
- <a id="storyboards"></a>"Storyboards" is [`storyboards.md`](storyboards.md).
- <a id="when-storyboards-apply"></a>"When storyboards apply" is [`storyboards.md`, "When a definition takes one"](storyboards.md#when-a-definition-takes-one).
- <a id="storyboard-structure"></a>"Storyboard structure" is [`storyboards.md`, "Structure"](storyboards.md#structure).
- <a id="location-and-lifecycle"></a>"Location and lifecycle" is [`storyboards.md`, under the same heading](storyboards.md#location-and-lifecycle).
- <a id="frontmatter-declaration"></a>"Frontmatter declaration" is [`storyboards.md`, under the same heading](storyboards.md#frontmatter-declaration).
- <a id="authoring"></a>"Authoring", of storyboards, is [`storyboards.md`, under the same heading](storyboards.md#authoring).
