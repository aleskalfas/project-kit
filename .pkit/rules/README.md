---
variant: specialized
reader: user
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
      record: [COR-001, COR-014, "COR-051#6", "COR-064#1", "COR-064#2", COR-068, COR-069, COR-070, ADR-075, ADR-076, ADR-077]
      artefact:
        - .pkit/schemas/README.md#rule-set-files
        - .pkit/cli/README.md#rule-sets-altered---base-ref---head-rev---json
        - .pkit/cli/README.md#configuration-file
---

# Rules

Operational rules and tool hygiene patterns the kit ships for any project that adopts it. Every agent session loads three files: `core.md`, the kit's rules; `capabilities.md`, an index of the rules each installed capability ships; and `project.md`, your project's own, which you own (COR-014, COR-070).

## Layout

```
.pkit/rules/
├── README.md                             # this file
├── core.md                               # kit's universal hard rules + tool hygiene, generated
├── capabilities.md                       # the capabilities' rules index, rendered for your project
└── project.md                            # your project's own operational rules (adopter-owned)

.pkit/rule-sets/
├── README.md                             # the folder's signpost
└── ops.md                                # OPS, the set core.md is generated from

.pkit/capabilities/<name>/
├── rule-sets/<file>.md                   # a capability's loaded set, where it ships one
└── rules.md                              # the capability's loaded file, generated from it
```

`core.md` is **kit-owned** (propagation per COR-001): refreshed on every sync, not editable by adopters. To extend the rules in your project, add them to `project.md` — sync never touches it — and your root `CLAUDE.md` includes `@.pkit/rules/core.md`, `@.pkit/rules/capabilities.md` and `@.pkit/rules/project.md`, in that order, so kit, capability and project rules compose naturally.

## How the layers stand

Every layer's rules bind at once: core's, each installed capability's and your project's. A capability's rules and your project's add to core's and never loosen them, and your project's never loosen a capability's. Where two cannot both be kept, the upper layer's rule binds: core's above a capability's, and both above your project's. Where rules of two capabilities cannot both be kept, the session stops the step and reports the clash, rather than choose between them (COR-070 point 4). A project that wants less proposes the change where the rule is kept, or uninstalls the capability.

## A capability's rules

A capability may ship operational rules of its own, as one loaded rule set in its `rule-sets/` folder: rules that bind on a session's work wherever the capability is installed (COR-070). Installing the capability is your consent to them, as it is to the project rule set its install declares, and install, sync and upgrade say which rules they newly bind, change or retire, core's among them. That is information, not a gate.

- **Its loaded file** is `.pkit/capabilities/<name>/rules.md`, generated from the set where the capability is authored, by `pkit rule-sets generate`, and checked there as `core.md` is. In your project it arrives with the capability, by install, sync or upgrade, and you edit neither.
- **Its preface** names the capability and says how its rules stand, in this sentence, its names filled in: "*These are the `<capability>` capability's operational rules, kept as its loaded rule set `<SET>` (COR-070). They bind on the work of every session in a project where `<capability>` is installed. They add to core's rules and never loosen them, and where one cannot be kept with a rule of core's, core's binds. A project's rules add to these and never loosen them. Where one of these rules cannot be kept with a rule of another capability's, stop the step and report the clash, rather than choose between them. Where a project's rule cannot be kept with one of these, this one binds.*" A session reads the file, not the records, so the file says whose rules they are. Validation fails a capability's loaded set whose preface does not name the capability, where the set is authored.
- **Its rules are cited** by their ids with the capability's name, such as `project-management:RS-PM-001`, never by a form of capability and number.
- **Its origins** cite a record of the capability's own, a core record, or give the decider's words, since the set is validated in every project that installs it.

## The capabilities' rules index

`.pkit/rules/capabilities.md` is how a session reaches each installed capability's loaded file (ADR-076 point 2). The backbone renders it whole for your project, from the capabilities your manifest registers and the form your adapter declares (`pkit rule-sets loaded` lists the same answer). It opens with a marker line, an HTML comment the harness drops, then holds one entry per registered capability that ships a loaded set, by the capabilities' names. It holds no rules of its own, and nothing else.

- **Rendered** at first install, sync, upgrade, and each capability's install, register, upgrade and uninstall. It is committed with `.pkit/`, so every checkout that holds `core.md` holds it too.
- **Nobody edits it.** A hand edit is overwritten at the next render, and `pkit validate` fails it until then. A file at its path without the marker is not the index: sync and upgrade refuse to run until you move it.
- **Reached by one line** your `CLAUDE.md` keeps after core's include, `@.pkit/rules/capabilities.md`, which the adapter's merge inserts wherever it is absent. The line never needs removing: uninstalling a capability changes the index alone.
- **Checked.** `pkit validate` fails an index out of step with the registered capabilities, an entry whose file is missing, and a `CLAUDE.md` without the line (the CLI reference, `validate`).

## Where the rules are kept

The kit's rules are a *loaded rule set*: a rule set whose accepted rules bind on the work of every session that loads the file generated from it ([COR-068](../decisions/core/COR-068-loaded-rule-sets.md)). Each rule has what a rule of any set has: a permanent id, a status, an origin, and a successor when it retires.

- **The set** is `OPS`, at `.pkit/rule-sets/ops.md`, shipped and synced with the backbone. Its front matter carries `loaded: true`, and each rule's status and origin. Each rule keeps the number it had: core rule 19 is `backbone:RS-OPS-019`, cited either way (the schemas README, "Rule-set files").
- **The loaded file** is `core.md`, where the include reads it. It holds the set's accepted rules under the set's sections, each headed `### N. Title (RS-OPS-0NN)` with its statement, and none of the set's data: no front matter, no origin, no retired rule.
- **It is generated.** `pkit rule-sets generate` writes `core.md` from `OPS` where the set is authored, in the methodology's source. A change to a rule regenerates the file in the same change, and `pkit validate` fails there on a `core.md` that differs from its set. In your project the two arrive together by sync. You neither generate nor edit `core.md`, and the command refuses to.
- **Citations of a rule** by layer and number, such as "core rule 19", or by id are read by `pkit validate`. One that names a missing, superseded or withdrawn rule is a warning (the CLI reference, `validate`).

## Each rules file's budget

Every session reads `core.md` and `project.md` whole, so every word in them is paid for in every session. Each may have a budget, the most words it may hold ([COR-069](../decisions/core/COR-069-rules-word-budget.md)). `pkit validate` reports each file's count against its budget in every project, and fails a file past its budget where its owner can shorten it. How a word is counted, and what the check says, are the CLI reference's (`validate`, the `rule-sets` member).

- **`core.md`'s budget** is `budget` in `OPS`'s front matter, beside `loaded: true` (the schemas README, "Rule-set files"). A component's loaded set must give one. You receive the file and its budget by sync, and are never failed for it: you see its count, and what it costs each session.
- **Your `project.md`'s budget,** while it is a plain file, is `rule-sets.plain-file-budget` in `.pkit/project/config.yaml`, if you set one (the CLI reference, ["Configuration file"](../cli/README.md#configuration-file)). Without the key, the file has no budget, and nothing is checked. No install or upgrade sets it: a budget you set bounds the size you chose.
- **Raising a budget is a person's decision.** A new rule that needs room raises the budget in the change in which a person accepts the rule. Any other raise lands only in a change a person authorises. An agent whose change would take a file past its budget trims the file instead, or brings the raise to that person. `pkit rule-sets altered` lists each budget a change raises, so whoever reviews the change sees it (the CLI reference, `rule-sets altered`).
- **Lowering one** is any change's to make. A budget is a ceiling, not a target: a change that trims a file may lower its budget, keeping what room it chooses.

## Converting your `project.md` into a loaded set

Your `project.md` is a plain file. It is loaded as it stands, and nothing checks its numbers or its origins, nor a citation such as "project rule 4" (COR-068 point 7). You may convert it into a loaded set of your own, when you choose:

1. Write the set as a rule-set file in `rule-sets/` under your internal documentation root (`docs/rule-sets/` by default). Give it a name of its own and `loaded: true`, and copy your rules into it, one section per rule, `### RS-<SET>-NNN — Title`, keeping each rule's number. The folder, its default and the form of a rule's heading are the schemas reference's, [Rule-set files](../schemas/README.md#rule-set-files).
2. If your configuration sets `rule-sets.plain-file-budget`, move its value into the set as `budget`, beside `loaded: true`, and remove the key. Its budget then sits beside the rules that need its room, and `pkit validate` warns of a key left behind, which bounds nothing.
3. Give each rule its origin: the record that decides it, or the decider's words (COR-051 point 5). Only you know who decided each rule and why, so no command or migration converts the file for you.
4. Run `pkit rule-sets generate`. It writes `.pkit/rules/project.md` from your set, and prints its count against the set's budget.
5. Run `pkit validate`. From then on it fails on a `project.md` out of step with your set, and reads each citation of your rules by "project rule N".

A project has one loaded set of its own, beside the kit's. It takes no scope, inheritance or extension point: its rules bind on sessions' work, not on files.

## What goes in `core.md`

Seven categories:

- **Hard rules** — invariants whose violation breaks the methodology. The no-shared-files invariant, the acceptance gate, paired-skill / `pkit new` for kit-shipped artifacts, migrations idempotency, etc.
- **Tool hygiene** — operational practices that keep work consistent. Pause for destructive ops, conventional commits, surface-change → version-bump, validate before assuming state, work with the permission layer, keep intermediate files in the agent workspace.
- **Communicating with the user** — one decision at a time, with a recommendation. Reference by meaning, then identifier.
- **Working across repositories** — a session mutates only its own repository's context.
- **Answers on artefacts** — a reviewer checks the answers your change owes, and a person, or the delegate they named, decides any other answer on an artefact.
- **When a step fails** — retry once a step that failed for a cause outside your own work, then stop and report.
- **Before changing files** — look up the accepted records their anchors lead to, and read those tied to them directly; and before a choice later work will build on, draft the record that decides it, for a person to accept.

Each rule is terse — one statement plus a pointer to the COR / area README that owns the rationale, or, where none does, to the issue that decided the rule. The rules file is read by every agent at session start (via `CLAUDE.md`'s `@<path>` include); it is operational, not expository. A loaded set's statements and prose hold no token outside code that opens with the harness's import form, such as a bare `@name`, since a session that loads the file could read it as an import of its own; validation refuses one.

`core.md` itself follows core rule 13 (the `@`-include authoring convention): no top-level heading, opens with an italic preface, sections start at H2. The host `CLAUDE.md` owns the H1 and places the `@<path>` line after its intro paragraph, so the included sections become natural sub-sections of the host. This pattern applies to any future kit-shipped file intended for `@`-include.

## What does NOT go in `core.md`

- **Rationale.** That lives in the cited COR / PRJ / area README. A rule none of them holds cites the issue that decided it. The rules file points; it does not re-state.
- **Project-kit-internal mechanics.** Things like the project-kit's own version-bump policy (PRJ-002) belong in the project's own records and CLAUDE.md, not in the kit-shipped rules adopters receive. The rules file uses project-neutral phrasing — adopters never see project-kit-specific content there.
- **Adopter-specific rules.** Those go in the adopter's `project.md`.
- **A rule that binds only where a capability is installed.** That goes in the capability's loaded set, not in core's, whose rules bind in every project, and not in the capability's documentation, which no session loads (COR-070 point 5).
