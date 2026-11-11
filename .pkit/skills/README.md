---
variant: universal
reader: act-ai-agent
kind: reference
pkit:
  friction:
    anchors:
      path:
        - .pkit/skills/core/**
        - .pkit/adapters/claude-code/deploy-skills.sh
        - src/project_kit/refs.py
        - src/project_kit/install.py
        - src/project_kit/capabilities.py
      record: [COR-001, COR-003, COR-005, COR-006, COR-013, COR-015, COR-017, COR-020, "COR-066#1"]
      artefact:
        - RS-OPS-001
        - RS-OPS-003
        - RS-OPS-012
        - .pkit/decisions/README.md#the-acceptance-gate
        - .pkit/adapters/claude-code/README.md#deploy-skillssh
        - .pkit/lifecycle/component-registry.md#install-pre-flight-checks
        - .pkit/lifecycle/upgrade-flow.md#a-new-collision
        - .pkit/cli/README.md#init
        - .pkit/cli/README.md#sync
        - .pkit/cli/README.md#status
        - .pkit/cli/README.md#surface
        - .pkit/cli/README.md#validate
      source: [claude-code-skills]
---

# Skills

A skill is a procedure an AI agent loads while it does a matching task ([COR-006](../decisions/core/COR-006-artifact-roles.md)). It is written in no harness's form, and the adapter deploys it where its harness reads skills. Why skills exist, and how people choose and write one, is in [the skills guide](https://github.com/aleskalfas/project-kit/blob/latest/docs/skills/README.md).

## Contents

<!-- pkit:contents -->
- [Layout](#layout)
- [Front matter](#front-matter)
- [The body](#the-body)
- [A composite skill](#a-composite-skill)
- [The acceptance gate a skill declares](#the-acceptance-gate-a-skill-declares)
- [Pairing a skill with a command](#pairing-a-skill-with-a-command)
- [Deployment](#deployment)
- [Adding a skill](#adding-a-skill)
<!-- /pkit:contents -->

## Layout

A skill's source sits in one of three places, in one of two forms:

```
.pkit/skills/
├── README.md                     # this file
├── core/                         # the methodology's skills
│   ├── <name>.md                 # flat form: the skill alone
│   └── <name>/                   # folder form: the skill with its helpers
│       ├── <name>.md             #   the skill, named as its folder
│       └── <helper>              #   a template, a script, or an operation's procedure
└── project/                      # the project's own skills, in either form

.pkit/capabilities/<capability>/skills/   # a capability's skills, in either form
```

- **`core/`** is the methodology's. Each sync refreshes it, so the project never edits a skill there (core rule 1).
- **`project/`** is the project's own, and no sync writes it ([COR-001](../decisions/core/COR-001-content-mechanisms.md)). A capability's install or upgrade replaces a skill there only where a person chooses to, at a name collision ("Deployment" below).
- **A capability's skills** sit in its own `skills/` folder, and arrive with its install ([COR-017](../decisions/core/COR-017-capability-pattern.md)).
- **The flat form** is the default. A skill takes the folder form once it needs a helper file beside it. It returns to the flat form when its last helper goes ([COR-015](../decisions/core/COR-015-artifact-file-layout.md)).
- **The file's name** is the skill's name, `<name>.md`, in both forms. No source file is named `SKILL.md`, a harness's name, which the adapter gives the deployed link.

<a id="frontmatter"></a>
## Front matter

Every skill file opens with YAML front matter, in the shape agent definitions share ([COR-013](../decisions/core/COR-013-agent-architecture.md) point 2):

```yaml
---
name: <name>                       # the skill's name, as its file's
description: <what it does>. Use when <its task comes up>.
metadata:
  wraps_command: <command>         # the command it pairs with, if any
reads:
  paths: [<file>]                  # files its body cites
  records: [<record id>]           # records its body consults
gates: [<record id>]               # records whose acceptance the procedure rests on
needs: [<hook>]                    # hooks it runs
answers: [<hook>]                  # hooks it provides
composes: [<file>]                 # a composite's files beside its dispatcher
---
```

- **`name` and `description`** are what the harness reads to offer the skill. Claude Code chooses a skill for a task by its `description`, so the description names the task (Claude Code's skills documentation).
- **`metadata.wraps_command`** names the command the skill pairs with ("Pairing a skill with a command" below). A skill that runs several commands lists them under `metadata.wraps_commands` instead.
- **`reads.paths` and `reads.records`** list the files and records the body cites. `reads.patterns`, an overlay category, is not filled in a skill, since the adapter deploys a skill's text unchanged.
- **`gates`** lists only the records whose acceptance the procedure rests on, so the skill must not run while one is not accepted. A record the body only consults goes under `reads.records` ("The acceptance gate a skill declares" below).
- **`needs` and `answers`** list the hooks the skill runs and provides. An agent definition may name a hook that a skill answers in its own `needs` (COR-013 point 4).
- **`composes`** is a composite skill's alone ("A composite skill" below).
- **Fields that do not apply** are left out.
- **A harness's own fields,** such as Claude Code's `allowed-tools`, reach the harness, since the deployed link leads to the skill's own file. A skill that sets one is written for that harness, and the methodology's skills set none.

What the body cites is checked against the front matter, in both directions (COR-013 point 3):

- **A path:** text in backticks that holds a `/`, and the target of a link that is no web address. A link that starts with `#` or `./`, or that leads to a decision record, needs no declaration. Nor does a path in a capability's skill that, read from the skill's folder or from the capability's, stays inside `.pkit/capabilities/<capability>/`. So of such a skill's paths, the check reads only those that start with `.pkit/` or climb out with `..`.
- **A record:** an id of the form `COR-`, `PRJ-` or `ADR-` and its number, in backticks or in prose. A capability's decision is cited as `[<capability>:DEC-NNN]`, and validation checks that it resolves, with no declaration.
- **A hook:** a word with one or two dots, such as `topic.operation`, in backticks or in prose. So a domain name or a dotted key in prose reads as a hook, and warns. Put it in a code fence, or reword it: declared under `needs`, it fails, since nothing answers it.
- **Not counted:** text in a code fence, an HTML comment or a strikethrough, and a path that holds `<`, `>`, `...`, `{`, `}` or `*`.
- **The checks.** `pkit validate` warns where the body cites a record, a file or a hook that the front matter does not declare. It also warns where the front matter declares a record, a file or a hook that the body never cites. A record under `gates` counts as declared. `pkit refs validate` gives the same findings, and fails on them ([the CLI reference, `validate`](../cli/README.md#validate)).
- **A declared file the body cites another way.** A path in the body cites it where the path leads to that file, such as a relative link. A decision record's file is cited by the record's id. A declared file counts, too, where its text stands anywhere in the body, as a bare name such as `CONTRIBUTING.md` does. The front matter is never searched for it.
- **What has gone.** `pkit refs rot` lists a skill that cites a superseded record, a dropped scratchpad note or a missing file ([the CLI reference, "Surface"](../cli/README.md#surface)).

## The body

The body is the procedure: the steps an agent runs, in order ([COR-006](../decisions/core/COR-006-artifact-roles.md)).

- **Steps, not principles.** Each step says what to do. A principle that a record or a document holds is cited, never restated, so the skill reads its current text.
- **The gates first.** Where the skill declares `gates`, its first section checks each record's status ("The acceptance gate a skill declares" below).
- **The command, not the file.** Where the skill pairs with a command, a step runs it. No step creates the file by hand ("Pairing a skill with a command" below).

## A composite skill

A family of operations that share their framing, such as authoring, extending and renaming one kind of file, ships as one composite skill ([COR-020](../decisions/core/COR-020-skill-folder-form.md)).

- **Its folder,** `<family>/`, holds a dispatcher, `<family>.md`, and one file per operation, `<operation>.md`. Other helpers, such as templates and scripts, sit beside them.
- **The dispatcher** holds the family's framing and sends each operation to its file. Its front matter is the composite's only front matter.
- **An operation's file** starts with its `# Title`, with no front matter.
- **The body, for the checks,** is the dispatcher and every other Markdown file of the folder. A template's example ids and paths are checked too, so keep them in a code fence.
- **The dispatcher's front matter** covers the whole family:
  - `gates` and `reads.paths`: the union of every operation's
  - `composes`: every file of the folder but the dispatcher, each a path from the folder, and `pkit validate` reports one that does not exist
  - `metadata.wraps_commands`: the commands the operations run
- **A single operation** stays flat, or takes the folder form only for its helpers (COR-015).

## The acceptance gate a skill declares

A skill refuses to run unless each record its `gates` names is accepted (COR-013 point 2). Nothing at run time checks the gates for the skill, so the skill's body checks them.

- **What it lists:** each record whose acceptance the procedure rests on. A proposed record binds nothing, so no work may rest on it ([the decisions README, "The acceptance gate"](../decisions/README.md#the-acceptance-gate)).
- **What the body does:** its first section names each gate. Where one is not `accepted`, the agent stops, and reports the gate, rather than running any step.
- **What an agent running a skill does:** it reads each gate's `status` before the skill's first step.
- **What a check finds:** `pkit refs rot` lists a gate on a superseded record ("Front matter" above). A gate on a proposed record is found only by the skill's own check.
- **A composite:** its gates are the union of its operations' (COR-020).

## Pairing a skill with a command

Every authoring command of the methodology's command line ships with a paired skill. The command stamps the file, and the skill carries the disciplines, the slug's choice, the body's drafting and the gates ([COR-005](../decisions/core/COR-005-bundle-pattern.md)).

- **A methodology artefact that a `pkit new` command stamps,** such as a decision record, is written through its paired skill or the command. It is never stamped by hand (core rule 3). The skill carries the disciplines the bare command does not.
- **The skill runs the command.** The command gives the file what it can compute, such as its place, its front matter, and for some kinds its number. The skill does the rest.
- **`metadata.wraps_command`** names the command, so a skill's pairing can be looked up. Nothing reads the field at run time. Find a command's skill by searching the skills' front matter for the command, `wraps_commands` included, in `.pkit/skills/` and each capability's `skills/` folder.
- **A project's own command,** such as a script that stamps its files, may pair with a skill of the project's own in the same way.

## Deployment

A skill runs from where its harness reads skills, never from `.pkit/`. The adapter deploys each skill there at `pkit init`, at each sync and upgrade, and at a capability's install, register and upgrade. A capability's uninstall runs the deploy again, which drops the capability's skills.

- **Where Claude Code reads it:** `.claude/skills/<name>/SKILL.md`, a link to the skill's file. A folder-form skill has a link to each of its other files beside it ([the Claude Code adapter's README, `deploy-skills.sh`](../adapters/claude-code/README.md#deploy-skillssh)).
- **Which skills:** the project's, core's, and those of each capability the manifest registers. Where two ship one name, the project's is deployed first, then core's is, then a capability's is, the first by name ([the same section](../adapters/claude-code/README.md#deploy-skillssh)).
- **Suspension.** Skills are suspendable ([COR-003](../decisions/core/COR-003-artifact-mechanisms.md)). A project skill that takes the name of core's skill, or of a capability's, replaces it in the harness by the order above. Updates of the replaced skill then reach no session. No project file disables a skill without replacing it.
- **What warns of a suspension:** only a capability's questions below. Otherwise the deploy prints the link it makes, and `pkit status` lists the skill as the project's.
- **A capability's upgrade** asks a person about each skill new in its version whose name the project already uses ([the lifecycle reference, "A new collision"](../lifecycle/upgrade-flow.md#a-new-collision)). A skill its installed copy holds, or one the project skipped, is not new. The answers are override, skip or inspect. With nobody to answer, it refuses.
- **A capability's install** asks the same about each of its skills whose name is already in use ([the lifecycle reference, "Install pre-flight checks"](../lifecycle/component-registry.md#install-pre-flight-checks)). It reads both forms of a skill, the capability's and those installed. A project skill that takes the name of a skill the capability already holds is asked about by neither.
- **Edit the source, never the deployed link** (core rule 12). An edit to the source needs no new deploy, since the link leads to it.
- **A new or removed skill** reaches the harness at the next `pkit sync`. The sync removes the deploy's own links to a skill that has gone ([the adapter's README](../adapters/claude-code/README.md#deploy-skillssh)).
- **A file the deploy did not make,** such as a hand-kept `.claude/skills/<name>/SKILL.md`, is left alone ([the adapter's README](../adapters/claude-code/README.md#deploy-skillssh)). No skill of that name is deployed over it, and the deploy reports it skipped.
- **Claude Code's own skills:** a personal skill of the same name, in `~/.claude/skills/`, wins over the project's (Claude Code's skills documentation). `pkit status` warns of each deployed skill a personal skill hides, and names the personal skill's folder ([the CLI reference, `status`](../cli/README.md#status)).
- <a id="today"></a>**What is deployed:** `pkit status` lists each deployed skill under where it was deployed from. It lists the project's own files in the harness's folder apart ([the CLI reference, `status`](../cli/README.md#status)).
- **A folder with no `<name>/<name>.md`** is skipped by the deploy, which names it, and the other skills deploy ([the adapter's README](../adapters/claude-code/README.md#deploy-skillssh)).

<a id="authoring-a-new-skill"></a>
## Adding a skill

No command stamps a skill, so the agent writes it whole. The steps:

1. Take a name no deployed skill uses, unless the project means to replace that skill ("Suspension" above). `pkit status` lists the deployed ones, and the files in the harness's folder that pkit did not deploy.
2. Write `.pkit/skills/project/<name>.md`, with the front matter above and the procedure as its body. In a capability the project authors, write it in that capability's `skills/` folder instead.
3. Run `pkit sync`, which deploys it.
4. Run `pkit validate`, and mend each finding it reports on the skill.
