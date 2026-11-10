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
        - .pkit/adapters/claude-code/deploy-skills.sh
        - .pkit/agents/core/rule-set-reviewer.md
        - .pkit/agents/core/methodology-reviewer.md
        - .pkit/adapters/claude-code/harness-support.yaml
        - .pkit/agents/project/overlay.yaml
        - .pkit/agents/tool_access.py
        - src/project_kit/agent_tool_access.py
        - .pkit/agents/definition_source.py
        - .pkit/lifecycle/capability_records.py
        - src/project_kit/agent_definitions.py
        - .pkit/rules/core.md
      record: [COR-001, COR-003, COR-005, COR-006, COR-007, COR-011, COR-013, COR-014, COR-015, COR-017, COR-019, COR-024, COR-026, COR-028, COR-049, COR-050, COR-051, COR-053, COR-057, COR-058, COR-060, COR-062, COR-064, COR-068, ADR-051, ADR-052, "ADR-065#11", ADR-085, ADR-086, ADR-087]
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
        - .pkit/lifecycle/upgrade-flow.md#seed-paths
        - .pkit/decisions/README.md#citing
        - .pkit/adapters/README.md#primitives-the-lifecycle-calls
        - .pkit/adapters/README.md#what-an-adapter-declares-as-data
        - .pkit/adapters/claude-code/README.md#harness-support-harness-supportyaml
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
├── README.md                    # this file (core-owned; propagated by sync)
├── hooks.md                     # a page beside it ("The pages beside this one")
├── storyboards.md               # a page beside it
├── tool_access.py               # the reader of an agent's tool access ("Tool access")
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

- **The flat form** is the default for a new definition. Promote it to the folder form only when a helper materialises.
- **`core/`** is core's. Sync refreshes it, and the project never edits it (COR-001).
- **`project/`** is the project's own. Sync reads it to deploy the definitions, and never writes it.
- **Both `core/` and `project/`** follow COR-003's universal pattern.
- **`tool_access.py`** is code, not a definition, so it sits at the area's root rather than in `core/` or `project/`. Sync copies the file with the area, and the adapters find the file at `.pkit/agents/tool_access.py` ("Tool access" below).
- **`overlay.yaml`** stands at the top of `project/`. Its per-agent overrides sit inside it, under `overrides:`.
- **A capability's definitions** take the same two forms in its own `agents/` folder, `.pkit/capabilities/<capability>/agents/` (COR-017, COR-026).

## Frontmatter schema

Agents and skills share one front-matter shape for the fields of the reference graph (COR-013 point 2). Each leaves out the fields that do not apply to it:

```yaml
---
name: release-checker
description: Checks a release before it is tagged.
tools: [Read, Grep, Bash]             # or withheld: […], never both ("Tool access")
model: sonnet                         # optional; absent is inherit ("Model and effort")
effort: high                          # optional; absent is inherit
reads:
  paths:                              # files and folders
    - .pkit/decisions/README.md
    - CLAUDE.md
  records:                            # decision records, resolved by id, not slug
    - COR-013
  patterns:                           # overlay placeholders, resolved at deploy; each an optional read
    - <project-conventions>
owns:                                 # paths whose modification is the agent's responsibility
  - <release-notes>
needs:                                # the hooks the agent invokes (hooks.md)
  - project.render-notes
---

# Release Checker

You are the **release checker** for this project. …
```

What each field holds:

- **`name`, `description`:** the agent's name, and the one line that tooling shows of it.
- **`tools` or `withheld`:** the agent's tool access, the tools it is granted or withheld. Each names the harness's tools, such as Claude Code's `Read`, `Edit` and `Bash`. A definition names one of the two keys or neither, never both. The adapter writes the tool access in the harness's form at deploy ("Tool access" below).
- **`model`, `effort`:** the model the agent runs on, and the effort it reasons at. Both are optional, and absent means inherit ("Model and effort" below). Agents only.
- **`reads`:** what the agent consults at task time, in three channels:
  - **`paths`** names files and folders, and **`records`** names decision records by id, such as `COR-NNN` or `PRJ-NNN`. A category named in either is a required read: while the overlay leaves it undefined, the deploy skips the agent.
  - **`patterns`** names overlay categories, each written as its placeholder, `<category>`. A category named only here is an optional read: while it is undefined, the deploy drops the item and deploys the agent without it.
  - **Which to use:** a read the agent cannot work without goes in `paths` or `records`. A read whose absence is a normal early state goes in `patterns`, such as a corpus of the project's conventions. The split is a load-bearing authoring lever, not just a filing convention, and the optional-read contract fixes its semantics ("An undefined category" below).
- **`owns`:** the paths whose modification is the agent's responsibility, each a literal path or a `<category>` placeholder the overlay resolves. Agents only, since skills own no path.
  - Each path that matters to the methodology is meant to have exactly one owning agent. `pkit refs validate` enforces that by reporting overlaps between agents over resolved paths ("Exactly-one-owner over `owns:`" below).
  - A category core declares write-carrying, which a core definition writes and the project names, follows four more rules ("Write-carrying categories" below).
  - A definition whose `owns:` resolves to decision records cites the rule for editing them where it describes editing records: `.pkit/decisions/README.md`, "Refining an accepted record". It does not restate the rule, since agents reference rather than embed (COR-006).
  - **A command's writes** are the command's, where one of the methodology's own mutating commands makes them, and `owns:` does not declare them. That holds for the backbone's commands and an installed capability's. The agent's body, or a skill it hands the work to, names the command and the conditions for running it.
  - **A write the agent makes itself,** with a file tool or any program through a shell, is never a command's write (COR-013). For the friction writers, see "Friction writers" below.
- **`needs`:** the hooks the agent invokes ([`hooks.md`](hooks.md)).
- **`answers`:** the hooks a skill provides. Skills only.
- **`gates`:** the records whose acceptance a skill needs before it runs. Skills only, and each entry counts as a `reads.records` entry too.
- **`storyboards`:** the storyboards the agent drives, each by its file name beside the definition ([`storyboards.md`](storyboards.md)).

**Any other key** in an agent's definition is none of these fields. `pkit refs validate`, and the `refs` member of `pkit validate`, warn of such a key at the agent's file, without failing. The deploy copies the key through unread, and a confined run of the agent refuses the key. A harness's own key is such a key, as Claude Code's `disallowedTools` is, and no check reads one as the agent's tool access.

### Tool access

An agent's tool access takes one of three forms (COR-013 point 7):

- **A grant,** `tools`, names the tools the agent is given, and the agent has only those. A grant with no entries gives no tools.
- **A withheld list,** `withheld`, names the tools the agent is withheld, and the agent has every other tool the harness would give it. A list with no entries withholds none.
- **Neither:** the agent has what the harness gives it. Run as a whole session's agent, the agent has the session's tools. Run as a helper, the agent has those the session gives a helper.

How the tool access is written:

- **Holding a key names its form,** whatever the key holds. So a definition that holds both keys is refused, even where one of them is empty.
- **An entry** names one of the harness's tools. It may narrow the tool with one argument in parentheses after the name, in the harness's own terms, such as `Bash(git status)`.
- **A value** is a list, on one line or one entry to a line, or one string whose entries are separated by commas outside parentheses. A key with no value holds no entries, and a value written any other way is refused.

**Grant or withhold.** A grant fails closed: a tool it does not name is not given. A withheld list fails open: a tool it does not name is given, a tool a later harness release adds among them. So a withheld list never shows that an agent lacks a tool. An agent that must lack a tool, such as one that must change no file, is granted its tools.

**The reader.** `tool_access.py` is the one reader of a definition's tool access. The deploy, the agent runner and the reference validator each call it, and none reads the two keys itself. What the reader does:

- **It reads the front matter's text,** not another parser's answer. It refuses a front matter with a top-level line it cannot read as a key, or with a key written twice. So no key the reader misses reaches the harness.
- **It answers** with the definition's form and the form's entries, each with its argument, or with why the definition is refused.
- **It answers two questions.** An agent holds a tool where its grant names the tool, or where the agent names no grant and does not withhold the tool. An agent lacks a tool only where its grant leaves the tool out. Each question reads the tool an entry names, whatever the entry's argument.
- **It uses only the standard library,** since the adapter's scripts run the reader under the system's Python. A caller loads it from the reader's own file, and writes no bytecode into the tree.
- **A function of the reader keeps its name and its answer.** One whose answer changes takes a new name, so an older command never reads a newer reader's answer as the command's own.
- **A command that cannot reach the reader** refuses that step, where the tree lacks the reader or the function the command calls. Inside the validator, that is an error finding. The message says which side is behind. A project at the command's backbone version or older needs `pkit sync`, and a newer one needs the command upgraded.

**The adapter** writes the reader's answer in the keys of the adapter's harness, never the author's text. The adapter declares that harness's terms as data, in `tool-access.json` in the adapter's folder. Those terms are the harness's keys, the forms a tool's name takes and the harness's built-in tools. The terms also give the withheld entries the harness was measured to withhold.

**What the adapter refuses.** Against the adapter's declaration, the reader makes the adapter's refusals, since a withheld list fails open. The reader refuses a withheld list the harness cannot withhold, or whose names the adapter cannot translate. [The adapters README, "What an adapter declares as data"](../adapters/README.md#what-an-adapter-declares-as-data), says what the declaration holds. The adapter's README says what the adapter refuses, and "Deploy mechanics" below says what a refusal does at deploy.

**The validator** reports as an error each definition whose tool access the reader refuses. It makes the adapter's refusals too, reading the declaration of every registered adapter that deploys agents, and names the adapter that refuses. It also reports an error for such an adapter with no declaration the reader reads. It does so too for an adapter whose declaration admits a withheld entry that the adapter's support declaration does not answer as achievable.

## Body conventions

A body cites what its front matter declares, in forms the validator reads without parsing free prose (COR-013 point 3). What counts as a citation:

- **A path** in backticks, where it holds a `/`, does not end in one and carries no placeholder, such as `` `.pkit/decisions/README.md` ``. A bare file name, such as `README.md`, does not count. A Markdown link's target counts too, unless it is a URL or holds a placeholder.
- **A record id** as a bare token: `COR-NNN`, `PRJ-NNN` or `ADR-NNN`.
- **A capability's decision** in brackets, `[<capability>:DEC-NNN-<slug>]`. It is not declared in the front matter, and must name a decision file of an installed capability.
- **A rule id,** `RS-<SET>-NNN`, an extension point, `RS-<SET>-NNN#<point>`, or a method rule set's rule with its component, `[<component>:RS-<SET>-NNN]` (COR-051). It is not declared in the front matter either. It must name a rule of an installed rule set, and `pkit refs validate` reports one that does not.
- **A role or point address** in brackets, such as `[pkit::documentation]` or `[pkit::documentation:readers]` (COR-019, COR-053). It is not declared in the front matter either. It must name a role or point an installed capability declares, and `pkit refs validate` reports one that does not. It also reports a bracketed token that holds `::` and is no address as malformed.
- **A hook name:** `<topic>.<operation>` or `<topic>.<provider>.<operation>` ([`hooks.md`](hooks.md)).
- **An operational rule** by its layer and number, such as "core rule 16", or by its id in a loaded set, such as `RS-OPS-NNN` (COR-068). `pkit refs validate` warns, without failing, of one that is missing or retired.
- **A point of a record** is held to its record, such as `COR-NNN point N`, `PRJ-NNN DN`, `COR-NNN#N` or `[<capability>:DEC-NNN] point N` (COR-058). `pkit refs validate` warns, without failing, of a point its record neither holds nor retires ([the decisions README, "Citing"](../decisions/README.md#citing)).
- **Not counted:** anything inside a fenced code block, an HTML comment or strikethrough.

The discipline:

- cite paths in backticks
- cite records by id
- mention hooks by name

**Intermediate files.** Every shipped definition's body ends with the same one-sentence section, `## Intermediate files`, which `pkit new agent` stamps ("Authoring a definition" below). It tells the agent to keep its intermediate files in the agent workspace, `.agent-workspace/` at the repository root, and nowhere else outside the repository. It says to write them with the file tools: a shell redirect there is judged like any other shell write (the workspace rule in `.pkit/rules/core.md`). Keep its words the same in every body, so that one search finds every definition that carries it.

**Reviewers.** A reviewer is an agent that judges work and returns a verdict or findings, such as COR-024's reviewer stack or a capability's review panel. What its read-only means:

- **It changes nothing it judges.** It never changes the work under review or the repository the work lives in. It edits no tracked file, and stages, commits and pushes nothing, since its verdict is worth only its independence. That is the whole claim.
- **It may still write.** A reviewer with a shell among its tools may need working files to review well, such as these:
  - a dumped diff
  - a script
  - captured output
  - a reproduction that runs a payload to prove a defect
- **Its working files** go in the agent workspace, never loose in the repository, where an author's `git add` sweeps them into a commit. They never go in `/tmp/` either. A review leaves no file of its own outside the workspace.
- **One section for the role.** Every reviewer that can run commands carries the same section, `## What read-only covers`, word for word, just before its `## Intermediate files`. Copy it from a shipped reviewer, such as `.pkit/agents/core/methodology-reviewer.md`. State any read-only claim elsewhere in its body or its description with the same scope.

**Friction writers.** An answer on an artefact is decided as COR-050 point 3 sets out. It is a revalidation, a deferral, or a revisit entry for a target of the artefact's links (COR-050 point 16). The writers put it in an answer file of the change's own (COR-062 point 1).

A project's existing answers move out of the artefacts' blocks once (COR-062 point 11). The CLI reference's ["Friction checks"](../cli/README.md#friction-checks) <!-- unanchored: named as the section that says where the writers write, whose meaning rests on COR-062, which the page anchors --> says where the writers write until then.

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
  - a tool access the reader refuses, itself or by an adapter's declaration ("Tool access" above)
  - an adapter that deploys agents with no declaration the reader reads, or a reader the command cannot reach
  - a name whose winning place holds both layouts, or a definition whose front matter gives another name than its file's ("Name-collision precedence" below)
  - a name the picker cannot tell, or a picker the command cannot reach
- **The exceptions** warn in both commands:
  - a cited point its record does not hold
  - a cited operational rule that is missing or retired
  - an unknown override in the overlay ("Adopter overlay" below)
  - a key in an agent's definition that is none of the definition's fields ("Frontmatter schema" above)
  - a collision between two capabilities no choice of the project's settles, and a choice that decides nothing ("Name-collision precedence" below)

**What the backward check leaves out.** It is meant for reads whose place an overlay can move, so three kinds of path in a body need no declaration:

- **A path that opens with `#` or `./`,** such as a link to a section or to a file beside the body.
- **A path to a decision record,** one under a `decisions/` folder or named as a record's file, such as `[COR-026](../decisions/core/COR-026-agent-placement-by-discipline.md)`. The record's id is the load-bearing reference, checked through `reads.records` or the capability-citation graph, so the link is exempt. `pkit refs rot` still checks that the file exists.
- **A path inside the citing capability,** in a capability's agent or skill, such as `scripts/move-issue.py`, a sibling sub-procedure `create-issue.md` or `project/config.yaml`. These are implementation pointers, not external reads. A path outside the capability, or an absolute or target-root-relative path into another tier, is still reported.
- **Never exempt:** a record id or a hook name, even inside a link. An undeclared one is still reported.

The other graph operations live in the `pkit refs` family, which reads or rewrites the graph. See `.pkit/cli/README.md` <!-- unanchored: named as the reference that lists the family's commands, a pointer and no statement of them --> for the full surface.

<a id="the-matrix"></a>
### Exactly-one-owner over `owns:`

`pkit refs validate` also checks write authority. Per COR-013's overlay rule, it compares the resolved paths of each agent's `owns:`, not its placeholders. Each placeholder is expanded through the overlay exactly as the deploy expands it, a per-agent `overrides:` entry replacing the top-level value:

- **Overlap** is one path containing another, or two equal paths, between two distinct agents. Nesting inside one agent's own set is fine, such as a folder and a file in it.
- **Reported, never settled.** The finding names both agents, both paths, and the overlay category a resolved path came from. No precedence picks a winner, since no ordering makes two owners of one path correct. Resolve it by reassigning an `owns:`, or by pointing the category elsewhere.
- **Clean:** an entry that resolves to no path, such as one of `code-paths: []`. A category the project has not filled yet is a normal state, not a validation failure.
- **Clean too:** an entry whose category the overlay does not define. That gap already shows loudly: the deploy skips the agent, and `pkit agents` names the category. So validation does not fail an install upgraded but not yet repaired a second time for the same gap.
- **One owner for each name.** Only the definition that is the agent counts as an owner ("Name-collision precedence" below). A shadowed source of the same name is no second owner of its paths.
- **What it leaves out:** the check covers `owns:` overlap only, not whether a resolved path exists, which `pkit refs rot` checks. Nothing at run time stops an agent from editing outside its `owns:`. Resolved ownership is methodology metadata, enforced at validation and honoured as discipline at run time.
- **Placeholders in the body.** Resolution applies to the ownership comparison, not to citation coverage. The bidirectional check finds a `<category>` entry by its placeholder in the body, deliberately. A core definition that cited a project's real paths would break project-neutrality, so its body carries the placeholder.

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
2. For the agent named under `overrides.<agent>:`, each category there replaces the top-level value whole, not merged with it. To extend a value, copy the top-level entries into the override. Merge semantics are deferred per COR-007 until concrete needs surface. Two keys there are reserved and are not categories: `model` and `effort` set the agent's execution policy ("Model and effort" below).
3. Write the resolved paths in place of each placeholder in the front matter, and the deployed copy into the harness's place. The body keeps its placeholders as written. The deployed copy is what every downstream tool reads.

**An unknown override** is an entry under `overrides:` that the deploy ignores. It is one of these:

- a block for an agent no source ships, whatever keys it holds
- a category in an agent's block that the agent's definition does not name, the definition being the one that is the agent ("Name-collision precedence" below)

`pkit agents` and the `refs` member of `pkit validate` warn of each, naming its key, such as `overrides.critc` or `overrides.critic.code-pths`. A warning fails no command, `pkit refs validate` included. A `model` or `effort` there that the harness does not accept is still reported, as an error ("Model and effort" below).

**The first install** writes the overlay with a value for each category core's definitions name, so they deploy before the project names a path. A missing overlay comes back as "Diagnosing + repairing the overlay" below says.

### An undefined category

Every category a definition names resolves through the overlay, at the top level or in `overrides.<agent>:`. What the deploy does with one the overlay does not define depends on the channel that names it:

- **In a required channel,** `owns`, `needs`, `answers`, `reads.paths` or `reads.records`, the deploy skips the agent, loudly, and deploys the rest.
- **Only in `reads.patterns`,** an optional read: the deploy drops the item, and deploys the agent anyway, as a generalist working without that corpus. A category named in both channels is required: the required reference wins.
- **A bare key,** `category:` with no value, is undefined. An explicit empty list, `category: []`, resolves to no path. A bare optional key still deploys its agent, with a warning, since it is usually a stub left unfilled.

### Write-carrying categories

Most categories name paths an agent reads. Core declares a category write-carrying where a core definition edits its paths and only the project can list them. The architect's categories are not among them, since each has a conventional folder. One such category ships today:

| Category | Consumer | Meaning |
|---|---|---|
| `process-authoring-targets` | the core `process-author` agent | the project's own process-definition files and predicate-script locations, the paths that agent may edit |

Four rules apply to a write-carrying category:

1. **It ships as an explicit empty list,** `process-authoring-targets: []`.
   - The difference from a bare or absent key is mechanical, not cosmetic. `[]` resolves to an empty `owns:`, so the agent deploys inert, owning nothing. A bare or absent key does not resolve at all, so the agent is skipped.
   - The first install writes the `[]`. An install from before the category upgrades into the skipped state, since sync cannot add a key to the project's overlay. `pkit agents reconcile --write` fills the `[]` to restore parity ("Diagnosing + repairing the overlay" below).
2. **File granularity, not subtree grants.** List definition files and predicate-script folders, not a capability's whole subtree. Never list a capability's `package.yaml`, since registering a predicate belongs to the `pkit process` commands, which own that stamp.
3. **Nothing sync manages.** No entry may resolve into content the next sync overwrites, which is the no-shared-files invariant at the agent's surface (core rule 1). An agent must never be granted write authority over that content. The deploy's resolver refuses such an entry, names the path, and skips the agent rather than deploy an invalid grant. `.pkit/lifecycle/ownership.py` decides once what sync manages, and every adapter's resolver imports it, so a second harness cannot silently skip the check:
   - core's areas, and a shipped capability's own subtree: managed
   - that capability's `project/` folder: the project's
   - an incubated or unregistered capability's subtree: the project's
   - every other declared project-tier position: the project's, such as an adapter's `settings/project/`, which holds the project's harness permission additions, so a category may name it
4. **One consumer, by convention.** A category a core record introduces is named by exactly the agent that record names. A core definition naming a write-carrying category another record introduced is a red flag in review. Categories the project defines are its own to share across its agents.

`pkit agents adopt` cannot serve a write-carrying category, since there is no conventional folder to create for paths core cannot enumerate. It says so rather than fail obscurely. Run `pkit agents reconcile --write`, then name the project's paths.

### Diagnosing + repairing the overlay

Three commands diagnose and repair the overlay, each described below (COR-013). The two that write fill a category with its conventional folder where it has one.

**Where a conventional folder lies.** It is a sub-path of the project's internal documentation root ([COR-049](../decisions/core/COR-049-documentation-roots.md) point 4):

- `architecture-docs` is `<root>/architecture`, and `adr-records` is `<root>/architecture/decisions`. With the default root, `docs/`, they are `docs/architecture/` and `docs/architecture/decisions/`. A project that set `docs.internal: tech-docs` gets `tech-docs/architecture/…` instead.
- **A new category.** Adding a sub-path for it, in `src/project_kit/docs_roots.py`, is the authoring step that enables `reconcile`'s fill and `adopt` for that category. Its name goes in `.pkit/lifecycle/ownership.py` too, where the deploy reads which categories `adopt` serves.
- **A recorded path stays.** `reconcile --write` and `adopt` write the path uncommented, with a `recorded by` note, and a later change of the root never moves it (COR-049 point 5).

#### `pkit agents`

`pkit agents` reports each definition as deployable or skipped, with each category it lacks, and its effective model and effort. It warns of each unknown override too ("Adopter overlay" above). It is the discoverable surface for "why didn't my agent show up?". It writes nothing, since the deploy is the sync's.

#### `pkit agents adopt <agent> [--yes]`

`pkit agents adopt` fills each undefined category of the agent that has a conventional folder, in one command:

1. It creates the folder if absent, with a seed README on its purpose. A folder that exists but holds nothing gets the README too.
2. It writes the category into the overlay, uncommented, with that path, and never over a value the project set.
3. It runs the adapter's deploy, so the agent lands in `.claude/agents/` at once.

**What it asks.** A category recorded over a folder that already holds documents, any entry at all, puts them within reach of every agent that names the category. They may read them, or write them where the category grants that. So it takes consent ([COR-049](../decisions/core/COR-049-documentation-roots.md) point 5):

- **Before it writes,** `adopt` reads which folders already hold documents, for every category at once, since `adr-records` lies inside `architecture-docs`.
- **Where one does,** a terminal is asked once for the run. The question lists each `category = path` with the agents that reach it, and the rest of the run beside it. `--yes` consents without a prompt.
- **Off a terminal without `--yes`,** the run refuses with exit 1. It names the command with `--yes`, and `pkit agents reconcile` to see the change first.
- **A "no" or a refusal** writes nothing at all: no folder, no overlay line and no deploy. A folder `adopt` creates, or one that holds nothing, is recorded without asking.
- **Each recording** prints these:
  - what it recorded
  - the root its path came from
  - where to change it

**When it stops.** It is idempotent: a second run on an adopted agent changes nothing, asks nothing, and deploys again. It errs clearly on these:

- an unknown agent
- an agent that names no overlay category
- a required category with no conventional folder, for which it names `reconcile`
- a write-carrying category, where the refusal is structural and says so: core cannot enumerate the project's paths, so `adopt` has nothing to create

An optional category with no conventional folder is no prerequisite: `adopt` leaves it undefined, names it as optional, and deploys the agent.

#### `pkit agents reconcile [--write]`

`pkit agents reconcile` surfaces each category a definition names and the overlay leaves undefined into `overlay.yaml`. It is a dry run by default, and `--write` writes. It uses detect-then-fill logic, with six states for each missing category:

1. **Missing and write-carrying:** written uncommented as `<category>: []`. The agent then deploys inert rather than being skipped, as on a fresh install. The project names real paths when ready.
2. **Missing, with its conventional folder present:** written uncommented with that path, so the next sync deploys the agent with no manual step. Examples are `architecture-docs` with `docs/architecture/`, and `adr-records` with `docs/architecture/decisions/`.
3. **Missing, only an optional read, with no conventional folder:** a commented stub is appended, framed as an optional read. The agent deploys without it, so uncomment it only to give the agent the project's corpus, never as a prerequisite.
4. **Missing, required, with no conventional folder:** a commented stub is appended, such as `# architecture-docs:`, with `<path/relative/to/project/root>` guidance. The agent stays skipped until a path is set and sync runs, or until `adopt` creates the conventional folder.
5. **A commented stub already there:** nothing is appended again, and the guidance splits by channel. A required stub is reported as action needed, since the agent is skipped until a path is set or `adopt` creates the conventional layout. An optional stub gets the same guidance framed as optional, since the agent deploys already.
6. **Defined,** with paths or an explicit `[]`: nothing is written, and no value the project set is overwritten.

More of `reconcile`:

- **A missing overlay.** With `--write`, `reconcile` creates the overlay from the seed the first install writes, and writes nothing else in that run. The dry run says it would. The next dry run shows each category the seed leaves undefined, so `--write` never records one the person was not shown.
- **Outside the lifecycle, only it writes a seed path.** Sync creates no seed path, so a deleted overlay otherwise returns only at the next `pkit upgrade` to a new release ([the lifecycle reference, "Seed paths"](../lifecycle/upgrade-flow.md#seed-paths)). `pkit agents adopt` names this repair where the overlay is missing.
- **When to run it:** for an overlay older than a newly shipped agent's categories. The repair is an explicit, idempotent command, never an automatic write by sync.
- **`--write` is the confirmation.** The dry run lists each fill as `category = path`, with the agents that reach it once recorded, as `adopt`'s question does. A command that shows what it would record until told to write takes `--write` as its confirmation (COR-049 point 5). So `--write` records over a folder that holds documents without a prompt. Each recording prints the root its path was derived from and where to change it.

## Model and effort

An agent runs on its caller's model and effort, unless its definition or the overlay says otherwise. Dispatched from a session, it inherits the session's. Started headless, it reads the operator's user settings.

| Key | Accepted values | Absent |
|---|---|---|
| `model` | `inherit`, a harness alias or a full model name. The aliases are `sonnet`, `opus`, `haiku`, `fable`, `best`, `opusplan`, `sonnet[1m]`, `opus[1m]` and `fable[1m]`. A full name is `claude-…`, and may name its provider first, such as `us.anthropic.claude-…`. | inherit |
| `effort` | `inherit`, `low`, `medium`, `high`, `xhigh` or `max` | inherit |

The values are those of Claude Code, the one harness an adapter ships for today. The effort levels are the same list `review-pr --effort` accepts. The backbone holds the vocabulary in `src/project_kit/agent_policy.py`, and the adapter's resolver carries the same constants.

**Precedence,** for each key on its own:

1. the overlay's `overrides.<agent>.model` or `overrides.<agent>.effort`, which is the project's, so it wins over a shipped value without an edit of a core file
2. the agent's front matter
3. inherit

**What is written.**

- **`inherit`,** like an absent or bare key, writes no key into the deployed copy, so the harness's default applies. An override of `inherit` is how a project resets a shipped value.
- **The shipped definitions** set neither key. This is the mechanism, not a policy, and nothing changes for a project that sets nothing.
- **A value outside the vocabulary** is never written:
  - The deploy drops it, and the agent deploys and inherits.
  - The run prints a `warning` line naming the value.
  - `pkit validate`, in its `refs` member, reports it as an error, and so does `pkit refs validate` ("The reference graph" above). They report it at the agent's file for a front-matter value, and at `overlay.yaml` for an override, so a typo cannot pass silently.
- **Reported by `pkit agents`.** Each row shows the effective value and where it came from, such as `model inherit`, `model sonnet` or `effort high (overlay)`, and a refused value as refused.

## Deploy mechanics

Each adapter handles its own deploy (COR-005), and future adapters for other harnesses ship their own deploy primitives. For Claude Code, `.pkit/adapters/claude-code/deploy-agents.sh` does it, and `pkit init` and `pkit sync` run it:

1. It asks the picker which definition of each name is the agent ("Name-collision precedence" below). The picker reads the project's place, each capability folder's and core's ([COR-026](../decisions/core/COR-026-agent-placement-by-discipline.md)), in either form.
2. It refuses, before reading its text, an agent whose place holds both layouts, and one whose front matter gives another name than its file's.
3. It resolves the source's front matter through the overlay ("Adopter overlay" above), and carries its model and effort ("Model and effort" above).
   - It writes the agent's tool access from the reader's answer, in the harness's keys ("Tool access" above).
4. It rewrites each storyboard the source names by its file name to the storyboard's path from the project's root ([`storyboards.md`](storyboards.md)).
5. It ends the body with one sentence, which replaces the session scratch directory the harness's environment names with `.agent-workspace/`.
6. It writes the copy to `.claude/agents/<name>.md`, with a deploy mark as the front matter's first line: `# managed-by: project-kit (deploy-agents.sh) — do not edit; regenerated on sync`. Three lines beside the mark record what the copy was written from. They are the definition's place (`# pkit-definition:`), the digest of the text read (`# pkit-digest: sha256:…`), and the tool access read from it (`# pkit-tool-access:`). So a check can say whether the copy that runs is of the current text.

What it reports, a line for each definition, such as `created`, `updated`, `exists`, `skipped`, `removed` or `warning`:

- **A file without the mark** at the copy's path is never written over, and is reported `skipped`. It is the project's own, or a copy from before the mark, and the harness may run it in the agent's place. To have the deploy write its own, delete the file and deploy again.
- **A marked copy that is not the agent's** is removed, and named. To keep one, delete its mark line, and it reads as the project's. A marked copy is not the agent's where any of these holds:
  - it was written from another definition than the agent's
  - its name has no agent
  - no place ships its name any more
- **A folder with no definition named after it,** such as one half written, ships none, and the rest deploy.
- **A refused agent** never stops the others, and stays the agent: no other definition's copy stands in for it (COR-013 point 8). What becomes of the copy written earlier from its definition depends on the cause:
  - **Refused for its tool access,** the earlier copy is removed. It may give tools the definition no longer gives (COR-013 point 7). The agent is missing until its definition is mended.
  - **Refused for another cause,** such as a gap in the overlay, the earlier copy stays only where its mark's tool access gives nothing more. It gives nothing more when it gives nothing the current text's does not, each entry read whole with its argument. The deploy then says the copy is not of the current text, and otherwise removes it.
  - **Refused because its place holds both layouts,** there is no one current text, and the earlier copy is removed.
  - A copy whose mark records no definition is read as the agent's only where one place ships the name. One whose mark records no tool access is never kept.

  The run ends with the count skipped, and the remedies.
- **A name the picker cannot tell,** since a record that decides it does not read, is left as it is. Nothing is written or removed for it, and an `error` line names the cause. The rest deploy, and the run exits without a failure. The validator holds the error until the record is mended.

Beside the deploy:

- **An uninstall.** Once a capability is unregistered, none of its definitions counts. The deploy the lifecycle runs after it removes each copy written from them, and writes the definition that now wins for each name. Without that deploy, the copies stay until the next sync's. The adapter's `undeploy-capability.sh <name>` removes no agent: it keeps its role for skills ([the adapters README, "Primitives the lifecycle calls"](../adapters/README.md#primitives-the-lifecycle-calls)).
- **Grants.** Where the adapter's permission hook is registered, the permission model decides each call of a dispatched agent. It applies the agent's own grants and the shared baseline (COR-028). The permissions reference says how a call's subject is found.
- **Dispatching.** A session dispatches an agent by its definition's name, and gives it no name of its own. While Claude Code's agent teams are on, a named one's result arrives cut at 4064 characters, as [the adapter declares](../adapters/claude-code/README.md#harness-support-harness-supportyaml).

### Name-collision precedence

The project, an installed capability and core may each ship a definition of one name. At most one of them is the agent of that name (COR-013 point 8).

One picker decides which, `.pkit/agents/definition_source.py`, and every part that deploys, runs, checks or names an agent asks it. They are the deploy, the agent runner, `pkit agents`, `pkit refs validate`, `pkit new agent` and `pkit new storyboard` without `--namespace`. So are `pkit status`, the delegate's check and the capabilities' collision checks. The picker learns the installed capabilities, their skips and the project's choices from the lifecycle's reader of capability records, `.pkit/lifecycle/capability_records.py`.

**A definition** is its place and its name. A place ships it as the canonical file alone, `<name>.md`, or in a folder, `<name>/<name>.md` (COR-015). A folder without its canonical file ships none.

**The order of the places:**

1. **The project's,** in `.pkit/agents/project/`, wins over every other. The project keeps the last word on its agents.
2. **A capability's,** in `.pkit/capabilities/<name>/agents/`, wins over core's. A capability that ships a core agent's name overrides core in the projects that install it. Its agent is its discipline's specialisation of the universal core default.
3. **Core's,** in `.pkit/agents/core/`, is the fallback, used when no project or capability ships the name.

**A capability's definition counts** while the component registry records the capability, whatever its folder holds, and the project has not skipped that definition (COR-017). So the folder of an incubated capability that was uninstalled ships nothing, though its files stay.

**Between two capabilities,** the one the project chose for the name wins, else the first by name. Names compare by their characters' code points, so every machine takes the same one:

- **The project's choice** is kept once for each agent's name, in the backbone manifest's `agent_choices` (the lifecycle reference, ["The component registry"](../lifecycle/component-registry.md)). An `override` at the collision prompt of `pkit capabilities install`, `pkit capabilities upgrade --interactive` or `pkit upgrade` against another capability's agent records it, and removes nothing. `pkit agents choose <agent> <capability>` records it at any other time. Uninstalling a capability drops its choices.
- **A choice counts** only while it names an installed capability whose definition of the name counts. One that decides nothing, and a collision no choice settles, are warned of by the validator.
- **A collision can also be resolved** by renaming an agent, skipping it at install, uninstalling a capability, or shipping a project agent of that name.

**A refused agent stays the agent.** A definition whose front matter gives another name than its file's is refused, and so is the agent of a place that holds both layouts. No other definition stands in for it, and the deploy says why ("Deploy mechanics" above).

**What cannot be told.** Where a record that decides a name cannot be read, the picker says so, rather than reading it as recording nothing:

- **An unreadable registry** leaves it unable to tell any name a capability's folder ships.
- **Unreadable choices** leave it unable to tell any name two or more counting capabilities ship.
- **One capability's unreadable manifest** leaves it unable to tell the names that capability's folder ships.

A name the project ships is told in each case, since it wins whatever the records say. The validator reports each name it cannot tell as an error.

**Rare by design.** An agent that implies a discipline belongs in its capability, not in core ([COR-026](../decisions/core/COR-026-agent-placement-by-discipline.md)). A capability and core share a name only to override on purpose.

### Why copies, not symlinks

A deployed definition is a resolved copy of its source, never a symlink to it. Skills under `.claude/skills/` deploy as symlinks, and agents cannot. A skill's front matter holds no placeholder today, so a symlink works there and gives authors live-edit during development. If a skill ever grows placeholders, it would switch to the same copy-based mechanism at that point.

- **Why:** the copy differs from its source. Its front matter holds the overlay's paths for the placeholders, the model and effort, and the tool access in the harness's keys. The front matter holds each storyboard's path and the deploy mark too. The copy's body ends with the workspace sentence.
- **What follows:** an edit of a source in `.pkit/agents/` reaches the harness only once the deploy runs again, such as at the next sync. Nothing keeps the copy in step with its source automatically without running the deploy again.

## The rule-set reviewer

The core agent `rule-set-reviewer` judges one change against the accepted rules that bind on each artefact the change alters or brings under a rule. It reviews the diff, beside `convention-compliance-reviewer` in the reviewer stack (COR-024). Its contract, including the kinds of finding it gives, is [COR-057](../decisions/core/COR-057-rule-set-reviewer.md).

- **What it judges.** It reads the rules only from the rule sets, through `pkit rule-sets altered` (the CLI reference, "Rule-set commands"). It judges only the text the change owns, and only the parts of a rule that no check is there to enforce. Its body holds no rule.
- **What a change brings under a rule.** A change that makes a rule bind on an artefact owns the whole artefact for that rule. It may do so by widening a set's scope, accepting a rule, updating a pin or typing a place. The reviewer judges all of the artefact under that rule, even where the change edits none of it.
- **A break there** is a settled break where the rule's text settles it, whatever brought the artefact under the rule. [COR-060](../decisions/core/COR-060-brought-under-breaks.md) names the author's ways out of one. The command's answer names those rules on each artefact, and lists apart each artefact the change brings under a rule without altering it.
- **Its form** comes from whoever invokes it: the verdict line, and the mark of each kind of finding. With none named, it states its verdict and each finding's kind in words.
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
| `core` | `.pkit/agents/core/<name>.md` | a universal role useful to any project, such as record review, citation audit, convention-compliance review or a coordinator template specialised through the overlay |
| `project` | `.pkit/agents/project/<name>.md` | a domain-specific role tied to the project's stack, such as an implementer (`ui-ux-designer`, `qa-engineer`), a domain reviewer or a customised coordinator |
| a capability's name | `.pkit/capabilities/<capability>/agents/<name>.md` | a role that implies the capability's discipline ([COR-026](../decisions/core/COR-026-agent-placement-by-discipline.md)), such as the code-authoring `software-engineer`, which ships opt-in in `software-engineering` |

What the command does:

- **Refuses a capability that does not exist under `.pkit/capabilities/`,** listing those that do, the same refusal `pkit new decision <capability>` gives. It creates the capability's `agents/` folder on first use.
- **Refuses a taken name,** in core, the project or any capability, since the deploy keeps one definition for each name.
- **Refuses a namespace the project receives by sync:** `core`, outside the methodology's source, and a capability that is not the project's own. Such an agent is authored where its source is kept, since the next sync would overwrite it (core rule 1). The refusal names the `project` namespace instead.
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
