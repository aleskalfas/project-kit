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
      record: [COR-001, COR-003, COR-005, COR-006, COR-013, COR-015, COR-017, COR-020, "COR-066#1"]
      artefact:
        - RS-OPS-001
        - RS-OPS-003
        - RS-OPS-012
        - .pkit/decisions/README.md#the-acceptance-gate
        - .pkit/adapters/claude-code/README.md#deploy-skillssh
        - .pkit/lifecycle/README.md#install-pre-flight-checks
        - .pkit/lifecycle/README.md#a-new-collision
        - .pkit/cli/README.md#init
        - .pkit/cli/README.md#sync
        - .pkit/cli/README.md#status
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
  records: [<record id>]           # records its body cites
gates: [<record id>]               # records that must be accepted before it runs
answers: [<hook>]                  # hooks it provides
composes: [<file>]                 # a composite's files beside its dispatcher
---
```

- **`name` and `description`** are what the harness reads to offer the skill. Claude Code chooses a skill for a task by its `description`, so the description names the task ([Claude Code's skills docs](https://code.claude.com/docs/en/skills)).
- **`metadata.wraps_command`** names the command the skill pairs with ("Pairing a skill with a command" below). A skill that runs several commands lists them under `metadata.wraps_commands` instead.
- **`reads`** lists what the body cites: files under `paths`, records under `records`. `reads.patterns`, an overlay category, is not filled in a skill, since the adapter deploys a skill's text unchanged.
- **`gates`** lists the records the procedure rests on, which must be accepted before it runs ("The acceptance gate a skill declares" below).
- **`answers`** lists the hooks the skill provides, each of which an agent definition may name in its `needs` (COR-013 point 4).
- **`composes`** is a composite skill's alone ("A composite skill" below).
- **Fields that do not apply** are left out.

What the body cites is checked against the front matter, in both directions (COR-013 point 3):

- **A citation** is a path in backticks or a link that holds a `/`, or a record's id, such as `COR-005`. Text in a code fence, an HTML comment or a strikethrough is none, and neither is a path with a `<placeholder>`.
- **The checks.** `pkit validate` warns where the body cites a record or a file that the front matter does not declare. It also warns where the front matter declares one that the body never cites. A record under `gates` counts as declared. `pkit refs validate` gives the same findings alone.
- **What has gone.** `pkit refs rot` lists a skill that cites a superseded record, or a file that does not exist.

## The body

The body is the procedure: the steps an agent runs, in order ([COR-006](../decisions/core/COR-006-artifact-roles.md)).

- **Steps, not principles.** Each step says what to do. A principle that a record or a document holds is cited, never restated, so the skill reads its current text.
- **The gates first.** Where the skill declares `gates`, its first section checks each record's status ("The acceptance gate a skill declares" below).
- **The command, not the file.** Where the skill pairs with a command, a step runs it. No step writes the file by hand ("Pairing a skill with a command" below).

## A composite skill

A family of operations that share their framing, such as authoring, extending and renaming one kind of file, ships as one composite skill ([COR-020](../decisions/core/COR-020-skill-folder-form.md)).

- **Its folder,** `<family>/`, holds a dispatcher, `<family>.md`, and one file per operation, `<operation>.md`. Other helpers, such as templates and scripts, sit beside them.
- **The dispatcher** holds the family's framing and sends each operation to its file. Its front matter is the composite's only front matter.
- **An operation's file** starts with its `# Title`, with no front matter. Its citations count as the skill's body, checked against the dispatcher's front matter.
- **The dispatcher's front matter** covers the whole family:
  - `gates` and `reads.paths`: the union of every operation's
  - `composes`: every file of the folder but the dispatcher, each a path from the folder, and `pkit validate` reports one that does not exist
  - `metadata.wraps_commands`: the commands the operations run
- **A single operation** stays flat, or takes the folder form only for its helpers (COR-015).

## The acceptance gate a skill declares

A skill refuses to run unless each record its `gates` names is accepted (COR-013 point 2). Nothing at run time checks it for the skill, so the skill's body checks it.

- **What it lists:** each record whose acceptance the procedure rests on. A proposed record binds nothing, so no work may rest on it ([the decisions README, "The acceptance gate"](../decisions/README.md#the-acceptance-gate)).
- **What the body does:** its first section names each gate. Where one is not `accepted`, the agent stops, and reports the gate, rather than running any step.
- **What an agent running a skill does:** it reads each gate's `status` before the skill's first step.
- **What a check finds:** `pkit refs rot` lists a gate on a superseded record. A gate on a proposed record is found only by the skill's own check.
- **A composite:** its gates are the union of its operations' (COR-020).

## Pairing a skill with a command

Every authoring command of the methodology's command line ships with a paired skill. The command stamps the file, and the skill carries the disciplines, the slug's choice, the body's drafting and the gates ([COR-005](../decisions/core/COR-005-bundle-pattern.md)).

- **An agent that writes a methodology file** does it through the paired skill. It never writes the file by hand, nor runs the bare command alone (core rule 3).
- **The skill runs the command.** The command gives the file what it can compute, such as an id, a place and front matter. The skill does the rest.
- **`metadata.wraps_command`** names the command, so a skill's pairing can be looked up. Nothing reads the field at run time. Find a command's skill by searching the skills' front matter for the command, in `.pkit/skills/` and each capability's `skills/` folder.
- **A new authoring command** lands in the change that brings its skill.
- **A project's own command,** such as a script that stamps the project's files, pairs with the project's own skill in the same way.

## Deployment

A skill runs from where its harness reads skills, never from `.pkit/`. The adapter deploys each skill there at `pkit init`, at each sync and upgrade, and at a capability's install, register, upgrade and uninstall.

- **Where Claude Code reads it:** `.claude/skills/<name>/SKILL.md`, a link to the skill's file. A folder-form skill has a link to each of its other files beside it ([the Claude Code adapter's README, `deploy-skills.sh`](../adapters/claude-code/README.md#deploy-skillssh)).
- **Which skills:** the project's, core's, and those of each capability the manifest registers. Where two of them ship one name, the project's is deployed, then core's, then a capability's, the first by name ([the same section](../adapters/claude-code/README.md#deploy-skillssh)).
- **A project skill with a core skill's name** replaces the core skill in the harness, and nothing reports it.
- **A capability's install or upgrade** asks a person about each skill whose name the project already uses ([the lifecycle reference, "A new collision"](../lifecycle/README.md#a-new-collision)). The answers are override, skip or inspect. With nobody to answer, it refuses.
- **Edit the source, never the deployed link** (core rule 12). An edit to the source reaches the harness with no new deploy, since the link leads to it.
- **A new or removed skill** reaches the harness at the next `pkit sync`, which removes the deploy's own links to a skill that has gone. A file that is no link of the deploy's is left alone.
- **What is deployed:** `pkit status` lists each deployed skill under where it was deployed from, and the project's own files in the harness's folder apart.
- **A folder with no `<name>/<name>.md`** is skipped by the deploy, which names it, and the other skills deploy.

<a id="today"></a><a id="authoring-a-new-skill"></a>
## Adding a skill

No command stamps a skill, so the agent writes it whole. The steps:

1. Take a name in lowercase words joined by hyphens, which no skill of core's, the project's or a registered capability's uses. `pkit status` lists the deployed ones.
2. Write `.pkit/skills/project/<name>.md`, with the front matter above and the procedure as its body. In a capability the project authors, write it in that capability's `skills/` folder instead.
3. Run `pkit sync`, which deploys it.
4. Run `pkit validate`, and mend each finding it reports on the skill.
