---
variant: specialized
reader: act-ai-agent
kind: reference
pkit:
  friction:
    anchors:
      path:
        - .pkit/rules/core.md
        - .pkit/rule-sets/ops.md
        - .pkit/adapters/claude-code/merge-claude-md.sh
        - src/project_kit/install.py
        - src/project_kit/loaded_rule_sets.py
        - src/project_kit/loaded_rules.py
      record: [COR-001, COR-014, "COR-051#5", "COR-051#6", "COR-066#1", COR-068, COR-069, COR-070, ADR-075, ADR-076, ADR-077]
      artefact:
        - .pkit/schemas/README.md#rule-set-files
        - .pkit/decisions/README.md#rule-sets--a-separate-family-with-the-same-guarantees
        - .pkit/lifecycle/README.md#the-capabilities-rules-index
        - .pkit/lifecycle/README.md#what-a-step-newly-binds
        - .pkit/adapters/claude-code/README.md#harness-support-harness-supportyaml
        - .pkit/cli/README.md#init
        - .pkit/cli/README.md#validate
        - .pkit/cli/README.md#rule-sets-generate
        - .pkit/cli/README.md#rule-sets-loaded---index-adapter---json
        - .pkit/cli/README.md#rule-sets-altered---base-ref---head-rev---json
        - .pkit/cli/README.md#configuration-file
---

# Operational rules

The operational rules are the instructions an agent session loads at its start, through the project's `CLAUDE.md` ([COR-068](../decisions/core/COR-068-loaded-rule-sets.md)). Core's and each installed capability's are kept as loaded rule sets, and the project's own as a plain file or a set of its own. Why they exist, and how people add their own, is in [the operational rules' guide](https://github.com/aleskalfas/project-kit/blob/latest/docs/rules/README.md).

## Contents

<!-- pkit:contents -->
- [Layout](#layout)
- [How the layers stand](#how-the-layers-stand)
- [Where the rules are kept](#where-the-rules-are-kept)
- [A capability's rules](#a-capabilitys-rules)
- [The capabilities' rules index](#the-capabilities-rules-index)
- [Each rules file's budget](#each-rules-files-budget)
- [Which file a rule goes in](#which-file-a-rule-goes-in)
- [Converting `project.md` into a loaded set](#converting-projectmd-into-a-loaded-set)
<!-- /pkit:contents -->

## Layout

A session reaches each layer's rules through the project's `CLAUDE.md`, which includes three files of this folder:

```
.pkit/rules/
├── README.md                             # this file
├── core.md                               # core's rules, generated from OPS
├── capabilities.md                       # the capabilities' rules index, rendered for the project
└── project.md                            # the project's own rules

.pkit/rule-sets/
├── README.md                             # the folder's signpost
└── ops.md                                # OPS, the set core.md is generated from

.pkit/capabilities/<name>/
├── rule-sets/<file>.md                   # a capability's loaded set, where it ships one
└── rules.md                              # the capability's loaded file, generated from it
```

- **`core.md` and `ops.md`** are core's, refreshed by every sync. A project never edits them (COR-001).
- **`capabilities.md`** is rendered by the backbone, and nobody edits it ("The capabilities' rules index" below).
- **`project.md`** is the project's own, and no sync, install or upgrade writes it. `pkit init` writes none, so the project creates it with its first rule.
- **A capability's two files** arrive with it, by install, sync or upgrade, and the project edits neither. A capability the project authors itself is the exception: there the project writes the set and generates `rules.md` ("A capability's rules" below).
- **The includes:** `CLAUDE.md` holds `@.pkit/rules/core.md`, `@.pkit/rules/capabilities.md` and `@.pkit/rules/project.md`, in that order. The adapter's merge keeps the first two present, and inserts the third only together with the first.
- **Sessions that load none of them:** some kinds of session load no rules file, such as Claude Code's built-in Explore and Plan agents. So hand the methodology's work to an agent whose definition does not set `omitClaudeMd` ([the Claude Code adapter's README, "Harness support"](../adapters/claude-code/README.md#harness-support-harness-supportyaml)).

## How the layers stand

Every layer's rules bind at once: core's, each installed capability's and the project's.

- **None loosens another.** A capability's rules add to core's and never loosen them. The project's add to both, and never loosen either.
- **A clash with an upper layer:** where two rules cannot both be kept, the upper layer's binds. Core's stands above a capability's, and both stand above the project's.
- **A clash between two capabilities:** the session stops the step and reports the clash, rather than choose between them (COR-070 point 4).
- **Wanting less:** a project proposes the change where the rule is kept, or uninstalls the capability.

## Where the rules are kept

Core's rules are a *loaded rule set* (COR-068). Its accepted rules bind on the work of every session that loads the file generated from it. Each rule has what a rule of any set has: a permanent id, a status, an origin, and a successor when it retires.

- **The set** is `OPS`, at `.pkit/rule-sets/ops.md`, shipped and synced with the backbone. Its front matter carries `loaded: true`, and each rule's status and origin. A rule's number is its id's number: core rule 19 is `backbone:RS-OPS-019`, cited either way (the schemas README, "Rule-set files").
- **The loaded file** is `core.md`, where the include reads it. It holds the set's accepted rules under the set's sections, each headed `### N. Title (RS-OPS-0NN)` with its statement. It holds none of the set's data: no front matter, no origin, no retired rule.
- **It is generated.** `pkit rule-sets generate` writes `core.md` from `OPS` where the set is authored, in the methodology's source. A change to a rule regenerates the file in the same change, and `pkit validate` fails there on a `core.md` that differs from its set. In a project the two arrive together by sync, and the command refuses to write `core.md`.
- **Citations of a rule** by layer and number, such as "core rule 19", or by id are read by `pkit validate`. One that names a missing, superseded or withdrawn rule is a warning (the CLI reference, `validate`).

## A capability's rules

A capability may ship operational rules of its own, as one loaded rule set in its `rule-sets/` folder (COR-070). They bind on a session's work wherever the capability is installed.

- **Consent:** installing the capability is the project's consent to its rules, as it is to the project rule set its install declares. No rule is accepted again in the project.
- **What a step says:** install, sync and upgrade name, for each loaded set they deliver, core's among them, the rules they newly bind, change or retire. That is information, not a gate ([the lifecycle reference, "What a step newly binds"](../lifecycle/README.md#what-a-step-newly-binds)).
- **Its loaded file** is `.pkit/capabilities/<name>/rules.md`. `pkit rule-sets generate` writes it from the set where the capability is authored, and validation checks it there as it checks `core.md`.
- **Its preface** names the capability and says how its rules stand, since a session reads the file, not the records. Validation fails a capability's loaded set whose preface does not name the capability, where the set is authored. The preface includes these sentences, its names filled in:

  ```markdown
  *These are the `<capability>` capability's operational rules, kept as its loaded rule set `<SET>` (COR-070). They bind on the work of every session in a project where `<capability>` is installed. They add to core's rules and never loosen them, and where one cannot be kept with a rule of core's, core's binds. A project's rules add to these and never loosen them. Where one of these rules cannot be kept with a rule of another capability's, stop the step and report the clash, rather than choose between them. Where a project's rule cannot be kept with one of these, this one binds.*
  ```

- **Its rules are cited** by their ids with the capability's name, `<capability>:RS-<SET>-NNN`, never by a form of capability and number.
- **Its origins** cite a record of the capability's own or a core record, or give the decider's words. The set is validated in every project that installs it.

## The capabilities' rules index

The index, `capabilities.md` beside this file, is how a session reaches each installed capability's loaded file. The backbone renders it whole for the project, from the capabilities the manifest registers and the form the adapter declares. `pkit rule-sets loaded` lists the same answer.

- **What it holds:** a marker line, an HTML comment the harness drops. Then one entry per registered capability that ships a loaded set, in the order of the capabilities' names. It holds no rules of its own, and nothing else.
- **When it is rendered:** at first install, sync and upgrade, and at each capability's install, register, upgrade and uninstall. It is committed with `.pkit/`, so every checkout that holds `core.md` holds it too.
- **Nobody edits it.** A hand edit is overwritten at the next render, and `pkit validate` fails it until then. A file at its path that is not the index stops sync and upgrade before they write. What counts as the index there is the lifecycle reference's ([its "The capabilities' rules index"](../lifecycle/README.md#the-capabilities-rules-index)).
- **Reached by one line,** `@.pkit/rules/capabilities.md`, which `CLAUDE.md` keeps after core's include. The adapter's merge inserts it wherever it is absent. The line never needs removing, since uninstalling a capability changes the index alone.
- **Checked.** `pkit validate` fails an index out of step with the registered capabilities, an entry whose file is missing, and a `CLAUDE.md` without the line (the CLI reference, `validate`).

## Each rules file's budget

Each rules file may have a budget, the most words it may hold ([COR-069](../decisions/core/COR-069-rules-word-budget.md)). `pkit validate` reports each file's count against its budget in every project. It fails a file past its budget where the file's owner can shorten it. How a word is counted, and what the check says, are the CLI reference's (`validate`, the `rule-sets` member).

- **A component's budget:** `core.md`'s is `budget` in `OPS`'s front matter, beside `loaded: true`, and a capability's `rules.md` takes its own set's (the schemas README, "Rule-set files"). A component's loaded set must give one. A project receives each such file with its budget, and is never failed for it.
- **`project.md`'s budget,** while the file is a plain file, is `rule-sets.plain-file-budget` in the project's configuration (the CLI reference, ["Configuration file"](../cli/README.md#configuration-file)). Without the key, the file has no budget, and nothing is checked. No install or upgrade sets it.
- **A key with no plain file** bounds nothing, and `pkit validate` warns of it.
- **Raising a budget is a person's decision.** A new rule that needs room raises the budget in the change in which a person accepts the rule. Any other raise lands only in a change a person authorises. An agent whose change would take a file past its budget trims the file instead, or brings the raise to that person.
- **A raise is listed.** `pkit rule-sets altered` lists each budget a change raises, so whoever reviews the change sees it (the CLI reference, `rule-sets altered`).
- **Lowering one** is any change's to make. A budget is a ceiling, not a target, so a change that trims a file may lower its budget, keeping what room it chooses.

## Which file a rule goes in

<a id="what-goes-in-coremd"></a>
<a id="what-does-not-go-in-coremd"></a>

A rule goes in the file of the layer where it must bind. Every session loads each rules file whole, so a rule holds what it requires, not why.

- **Core's set,** `OPS`: a rule that must bind on a session's work in every project, in words that fit any project (COR-014). A rule tied to one project's own tooling goes in that project's file.
- **A capability's loaded set:** a rule that binds only where the capability is installed. It goes neither in core's set, whose rules bind in every project, nor in the capability's documentation, which no session loads (COR-070 point 5).
- **`project.md`:** the project's own rules.
- **An ordinary rule set:** a rule a project chooses to bind on its own files, not on a session's work (COR-068 point 1). Core rule 24 has every session follow the rules such sets bind on what its change owns ([the decisions README, "Rule sets"](../decisions/README.md#rule-sets--a-separate-family-with-the-same-guarantees)).

How a rule reads:

- **What it holds:** what it requires, in as few sentences as it needs, and a pointer to the record, area README or issue that holds its reason. A rule of a loaded set that cites none of them leaves its reason to its origin in the set.
- **No first-level heading.** A rules file is included into `CLAUDE.md`, which owns the heading, so the file's sections start at the second level (core rule 13). `core.md` opens with an italic preface.
- **No import token.** Outside code, a rules file holds no token that starts with the harness's import form, such as a bare `@name`. A session could read it as an import. Validation refuses one in a loaded set's statements and prose, and does not read a plain `project.md` for one.

## Converting `project.md` into a loaded set

<a id="converting-your-projectmd-into-a-loaded-set"></a>

The project's `project.md` is a plain file. It is loaded as it stands, and nothing checks its numbers, its origins or a citation such as "project rule 4" (COR-068 point 7). The project may convert it into a loaded set of its own, when it chooses:

1. Write the set as a rule-set file in `rule-sets/` under the internal documentation root, `docs/rule-sets/` by default. Give it a name of its own and `loaded: true`, and copy the rules into it, one section per rule, `### RS-<SET>-NNN — Title`. Keep each rule's number. The folder, its default and the form of a rule's heading are the schemas reference's ([Rule-set files](../schemas/README.md#rule-set-files)).
2. If the configuration sets `rule-sets.plain-file-budget`, move its value into the set as `budget`, beside `loaded: true`, and remove the key. `pkit validate` warns of a key left behind.
3. Give each rule its origin: the record that decides it, or the decider's words (COR-051 point 5). Only the project knows who decided each rule and why, so no command or migration converts the file.
4. Give a rule the status `accepted` only once a person accepts it, in the change that converts the file ([COR-066](../decisions/core/COR-066-accepted-before-landing.md) point 1). A rule with no status is proposed, and binds nothing.
5. Run `pkit rule-sets generate`. It writes `project.md` over the plain file, from the set's accepted rules alone, and prints its count against the set's budget. A rule still proposed is left out of it.
6. Run `pkit validate`. From then on it fails on a `project.md` out of step with the set. It also reads each citation of the project's rules by "project rule N".

A project has one loaded set of its own, beside core's. It takes no scope, inheritance or extension point, since its rules bind on a session's work, not on files.
