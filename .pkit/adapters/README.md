---
variant: adapter-umbrella
reader: act-ai-agent
kind: reference
pkit:
  friction:
    anchors:
      path:
        - .pkit/schemas/harness-requirements.yaml
        - .pkit/schemas/harness-requirements.schema.json
        - .pkit/schemas/harness-support.yaml
        - .pkit/schemas/harness-support.schema.json
        - .pkit/schemas/tool-access.yaml
        - .pkit/schemas/tool-access.schema.json
        - .pkit/adapters/claude-code/permission-enforcement.yaml
        - .pkit/agents/tool_access.py
        - .pkit/lifecycle/ownership.py
        - src/project_kit/agent_policy.py
        - src/project_kit/agent_runs.py
        - src/project_kit/agent_tool_access.py
        - src/project_kit/capabilities.py
        - src/project_kit/cli.py
        - src/project_kit/harness_support.py
        - src/project_kit/install.py
        - src/project_kit/loaded_rules.py
        - src/project_kit/permissions.py
        - src/project_kit/schemas_validate.py
        - src/project_kit/sync.py
        - src/project_kit/upgrade.py
      record: [COR-001, COR-002, COR-005, COR-006, "COR-013#1", "COR-013#7", COR-028, COR-047, COR-070, ADR-066, ADR-073, ADR-076, ADR-083, ADR-085, ADR-086]
      artefact:
        - .pkit/adapters/claude-code/README.md
        - .pkit/adapters/claude-code/README.md#what-this-adapter-ships
        - .pkit/adapters/claude-code/README.md#deploy-agentssh
        - .pkit/adapters/claude-code/README.md#the-agent-runner-run-agentpy
        - .pkit/adapters/claude-code/README.md#harness-support-harness-supportyaml
        - .pkit/adapters/claude-code/README.md#permission-enforcementyaml
        - .pkit/lifecycle/manifest.md#how-a-registered-command-is-run
---

# Adapters

An adapter translates the methodology's content for one AI harness, and holds every tie to that harness ([COR-005](../decisions/core/COR-005-bundle-pattern.md)).

<a id="adding-a-new-harness"></a>

Why adapters exist, and how a component author adapts the system to another harness, is in [the adapters guide](https://github.com/aleskalfas/project-kit/blob/latest/docs/adapters/README.md).

## Contents

<!-- pkit:contents -->
- [Layout](#layout)
- [Currently shipped](#currently-shipped)
- [Primitives the lifecycle calls](#primitives-the-lifecycle-calls)
- [What an adapter declares as data](#what-an-adapter-declares-as-data)
- [How a capability's rules reach a session](#how-a-capabilitys-rules-reach-a-session)
- [The agent runner](#the-agent-runner)
- [Harness requirements](#harness-requirements)
<!-- /pkit:contents -->

## Layout

Each adapter is one folder under `.pkit/adapters/`, named after its harness:

```
.pkit/adapters/
├── README.md                        # this file
└── <harness-name>/                  # one folder per harness
    ├── README.md                    # what the adapter ships, and how a project uses it
    ├── package.yaml                 # its version and backbone range, its loaded_rules: and commands:
    ├── migrations/                  # its version migrations
    ├── harness-support.yaml         # its support declaration
    ├── permission-enforcement.yaml  # its enforcement declaration
    ├── tool-access.json             # its declaration of tool access, where it deploys agents
    ├── <scripts>                    # the scripts the lifecycle calls, and the files they read
    └── settings/
        ├── core/                    # a settings baseline, merged into its harness's settings
        └── project/                 # the project's additions to that baseline
```

- **What it holds:** only what is specific to its harness. Skills, agent definitions and rules are written in no harness's form, in their own areas, and the adapter translates them ([COR-006](../decisions/core/COR-006-artifact-roles.md)).
- **What reaches a project:** sync copies each file at an adapter's top level, and its `settings/core/`. It copies no other folder, `migrations/` included, so each file a script reads sits at the top level.
  - A file ending in `.sh` or `.py` keeps its executable bit.
  - Sync removes a file at a shipped adapter's top level that the methodology no longer ships.
- **Every shipped adapter is installed.** `pkit init` copies each adapter the methodology ships, and registers each in `.pkit/manifest.yaml` <!-- unanchored: names the file the step reads or writes, not its content -->.
- **Who owns what:** in a project, an adapter's `settings/project/` and `project/` folders are the project's, and no sync writes them. Everything else under `.pkit/adapters/` is the methodology's ([COR-001](../decisions/core/COR-001-content-mechanisms.md)). So an adapter is written in the methodology's source repository, never in a project.

## Currently shipped

- **`claude-code/`**, the Claude Code adapter. [Its README, "What this adapter ships"](claude-code/README.md#what-this-adapter-ships), lists its files and what each does.

## Primitives the lifecycle calls

The lifecycle drives an adapter through scripts it finds by their names in the adapter's folder. `pkit init`, `pkit sync`, `pkit upgrade` and the capability verbs walk each folder under `.pkit/adapters/` in name order, and run each script present. The name is the lifecycle's whole contract with a script, so the backbone holds no harness's paths ([COR-005](../decisions/core/COR-005-bundle-pattern.md) and [COR-013](../decisions/core/COR-013-agent-architecture.md)). The Claude Code adapter's scripts are the worked example ([its README, "What this adapter ships"](claude-code/README.md#what-this-adapter-ships)).

What the lifecycle relies on, for every script:

- **It runs as a program.** The lifecycle starts the file itself, from the project's root. So the file is executable, and opens with an interpreter line.
- **It is idempotent.** Run twice, it changes nothing the second time.
- **Its exit status counts.** A script that exits with a status other than 0 stops the lifecycle command, with `adapter primitive <script> exited with status <n>`. The script's own output says what failed.

The scripts:

| Script | Arguments | What it does | When the lifecycle runs it | If the adapter has none |
|---|---|---|---|---|
| `merge-settings.sh` | none | merges the adapter's settings baseline and the project's additions into its harness's settings file ([COR-002](../decisions/core/COR-002-merge-delivery.md)) | first of the deploy primitives | skipped silently |
| `merge-claude-md.sh` | none | keeps core's include and the index's line in its harness's instruction file, whatever that file is called ("How a capability's rules reach a session" below) | second | skipped silently |
| `deploy-skills.sh` | none | deploys the skills where its harness reads them | third | skipped silently |
| `deploy-agents.sh` | none | deploys the agent definitions where its harness reads them | fourth | skipped silently |
| `undeploy-capability.sh` | the capability's name | removes what the adapter deployed for that one capability | when a capability is unregistered but its folder stays | **reported** in a `warning` line naming the adapter |

- **Deploy primitives:** the first four, run in that order whenever the harness's side needs deploying again.
  - **When:** at init, sync and upgrade, and at a capability's install, register, upgrade and uninstall.
  - **Settings first,** since a skill may rely on the settings being in place.
  - **What each deploys:** what the tree ships. Each drops what it deployed from a source that is gone.
  - **Each is optional.** A harness that loads skills from their own paths needs no `deploy-skills.sh`.
  - **How a skill is deployed** is [the skills reference's](../skills/README.md#deployment) <!-- unanchored: points the reader on to a page that anchors this one, so an anchor back would make a cycle -->. How an agent definition is deployed, with the project's paths and the agent's grants, is [the agents reference's](../agents/README.md#deploy-mechanics) <!-- unanchored: points the reader on to a page that anchors this one, so an anchor back would make a cycle -->.
- **Undeploy primitive:** `undeploy-capability.sh <capability-name>`, run when a capability is unregistered and its folder stays. That is an incubated capability's uninstall, and any capability's uninstall in the methodology's source repository.
  - **Why the deploys cannot help:** the capability's files still exist, so a deploy run again does not see the capability as gone.
  - **What it removes:** what the adapter deployed for that one capability, known by the adapter's own deploy mark, and never the project's own files. An adapter that deploys nothing for a capability can ship one that does nothing.
  - **Its absence is reported,** not skipped. The uninstall goes on, and a `warning` line names the adapter, since its harness keeps the capability active.

## What an adapter declares as data

Beside its scripts, an adapter states what its harness does in declarations, files of fixed names in its folder. The backbone's commands read them, and run none of the adapter's code:

- **Its support declaration,** `harness-support.yaml`: how far its harness meets each harness requirement the core declares ("Harness requirements" below). It detects, and never drives what a command does ([COR-047](../decisions/core/COR-047-harness-requirement-declaration.md)).
- **Its enforcement declaration,** `permission-enforcement.yaml`: where its harness enforces each dimension of the permission model ([COR-028](../decisions/core/COR-028-permission-model-realization.md) point 3).
  - **Its form:** no schema shapes it, so it follows the Claude Code adapter's file. Under `dimensions`, each dimension names its `layer` and its `enforcement`, which is `native`, `runtime` or `none`.
  - **Who reads it:** `pkit permissions diff` reads the Claude Code adapter's, at that adapter's path. No command reads another adapter's yet.
- **Its declaration of tool access,** `tool-access.json`: its harness's terms for an agent's tool access. An adapter that deploys agents declares it ("The declaration of tool access" below).
- **How its harness reaches a capability's rules:** `loaded_rules:`, a key of its `package.yaml` ("How a capability's rules reach a session" below).
- **Its agent runner:** the command its `package.yaml` registers as `run-agent` ("The agent runner" below).

### The declaration of tool access

An agent's definition names its tool access in the methodology's terms. What a harness takes is its adapter's to know. So an adapter that deploys agents declares its harness's terms in `tool-access.json`, and the agents area's reader, `.pkit/agents/tool_access.py`, makes the adapter's refusals against them.

- **Which adapter declares it:** one that deploys agents, that is, one that ships `deploy-agents.sh` or registers an agent runner.
- **Its format:** JSON, since the agent runner reads it under the system's Python. Its shape is `.pkit/schemas/tool-access.schema.json`, and `.pkit/schemas/tool-access.yaml` says what each field holds.

Its fields:

- `schema_version`: the version of the shape. The reader refuses a version it does not read, naming its own, and a key it does not know.
- `harness`: the harness's name, as a refusal says it.
- `keys`: the harness's key for each form, the one the deploy writes a grant (`tools`) or a withheld list (`withheld`) under.
- `name_forms`: the forms a tool's name may take. An entry whose name takes none of them is refused. So is an entry narrowed by an argument, where its form takes none.
- `known_tools`: the harness's built-in tools, by name. A withheld name outside them is refused, since it would withhold nothing.
- `withheld_admits`: the withheld entries the harness was measured to withhold, which may be none. A withheld entry outside them is refused.

How the fields are read:

- **Each form and each admitted entry** is a shape of three keys. A `pattern` is a regular expression in Python's dialect that matches a whole name. `argument` says whether an argument in parentheses may narrow the tool. A `description` is what a refusal names.
- **A name the reader cannot read as an entry** is refused before any declaration is read, so no pattern widens the reader's grammar.
- **A harness's own key beside its form:** a definition is refused that holds the harness's own key beside the form that translates to it, such as Claude Code's `disallowedTools` beside `withheld`.
- **A new adapter starts from `.pkit/schemas/tool-access.yaml`,** which admits no withheld entry. It admits one only once its harness was measured to withhold it.

**Who reads it.** The adapter's deploy and its runner give the reader their own adapter's declaration. `pkit refs validate`, and `pkit validate` in its `refs` member, give it the declaration of every registered adapter that deploys agents. Each fails a definition any of them refuses, naming the adapter and the cause.

- **What follows:** a definition passes only where every such adapter takes it. So registering a second harness's adapter can fail definitions that passed before.
- **What validation also fails:**
  - an adapter that deploys agents and declares no tool access, or whose declaration the reader cannot read
  - an adapter whose declaration admits a withheld entry, while its support declaration does not answer `session-agent-withheld-tools` as achievable for some version

What the Claude Code adapter declares, and what it refuses, are in [its README](claude-code/README.md), "Tool access" under `deploy-agents.sh`.

## How a capability's rules reach a session

A capability may ship operational rules of its own, as a loaded file at `.pkit/capabilities/<name>/rules.md` ([COR-070](../decisions/core/COR-070-capability-loaded-rules.md)). Each adapter delivers every installed capability's loaded file to the sessions its harness starts. It takes the route that carries core's rules, where the harness offers one, so every session that loads core's rules loads them too.

**An adapter declares its delivery** in its `package.yaml`, under `loaded_rules:`. The key says that its harness reaches the capabilities' loaded files through one index, which the host file reaches by one line:

- `entry`: the index's line for one capability's loaded file, with `{file}` for its path read from the index's folder. The part before `{file}` is the harness's import token.
- `host`: the file that reaches the index, a path relative to the project's root and inside it.
- `line`: the line the host keeps, with `{index}` for the index's path read from the host's folder. With core's loaded file's path in place of the index's, it is core's include.

**The merge keeps both lines.** Declaring the key commits the adapter's merge primitive to keep `line` present in `host`, and core's include too, each in that form. So no adapter names a path under `.pkit/`, and the backbone names no harness's syntax. What the index holds, and when the backbone renders it, is [the rules reference's, "The capabilities' rules index"](../rules/README.md#the-capabilities-rules-index) <!-- unanchored: points the reader on to a page that anchors this one, so an anchor back would make a cycle -->.

**Validation checks each registered adapter's delivery.** `pkit validate` reports these:

- **An error:** a host the checkout holds without `line`, or without core's include.
- **An error:** a word outside code in a loaded set's body that opens with a registered adapter's import token. The harness could read it as an import.
- **An error, while the forms differ:** registered adapters that declare different `entry` forms. The index is not rendered until the record that adds the second adapter decides how one index serves both.
- **A warning:** an adapter that declares no `loaded_rules:`. Its harness's sessions then load no capability's rules, and core's include goes unchecked for its harness.

An adapter whose harness reaches the files another way needs a key of its own, or a validator it registers.

## The agent runner

A command that starts an agent with nobody watching never calls a harness. It asks the backbone's run command, `pkit agents run`, which starts the runner the project's adapter registers. The runner starts the harness, so the tie to a harness's command line lives in its adapter, as every other tie does. project-management's `review-pr` starts its reviewers this way, and its `fix-drift` starts the fixers a project granted, confined.

**What makes a runner.** Unlike the primitives above, the lifecycle never runs it, and the backbone never finds it by a file's name:

- **A registered command.** The adapter registers it in its package's `commands:` tree, under the one reference `run-agent`. The backbone finds it through its one lookup of that tree ([the lifecycle reference's manifest schema, "How a registered command is run"](../lifecycle/manifest.md#how-a-registered-command-is-run)). A capability's command of that name is no runner.
- **Run once for each run.** Each call starts one agent, so a runner is not idempotent. The backbone runs it under the agent-run policy that the manifest schema states, with no arguments and the request on standard input.
- **Where it runs:** from the project's root, or from the clone's root for a confined run.
- **One runner for a project.** Where no registered adapter registers one, the run is refused, and the command that asked starts no agent and says why. Where more than one does, the run is refused too, until a record says how a project names its harness.

**The request** is one JSON document on standard input: `schema_version` (`1`), `agent`, `brief`, `limit_seconds` and `effort`, a level or `null`. A runner refuses a request with any other key, rather than run it without that key. So a runner that does not know the confined form refuses it.

**The levels of `effort`** are `low`, `medium`, `high`, `xhigh` and `max`, the named levels Claude Code takes ([the Claude Code adapter's README, "`deploy-agents.sh`"](claude-code/README.md#deploy-agentssh)). A runner passes a level, where one is set, to its harness in that harness's own terms. That level wins over the effort the agent's definition sets.

The request then takes one of two forms:

- **Unconfined,** the form of the review command's runs: `folder`, an absolute path, where the run runs under the person's and the project's settings.
- **Confined,** the form of the drift command's runs: no `folder`, and `confined`, an object the backbone fills in once it has made the run's clone.

A confined request's `confined` holds these keys:

- `working_copy`: the clone at the pinned commit, which the run reads.
- `workspace`: the one folder below the clone that the run writes, where the harness starts.
- `temp`: the shell's temp folder, inside the workspace.
- `pkit_folder`: the folder that holds the run's `pkit`, to put first on the run's path.
- `project_root`: the person's checkout, whose settings files the run leaves out.
- `rules`: the run's rules, projected through the shared decision core. `allow` is the whole allow list, and `deny` holds the denies to keep as native rules.
- `excluded`: each allowed command the platform requires outside the sandbox, as its words. It is empty off macOS.

What else a runner takes from a confined request:

- **A rule** takes one of three forms. The backbone has already refused a run whose rules no native rule could hold.
  - `{"tool": T}`: the whole tool.
  - `{"tool": T, "folder": F}`: the tool on `F` and everything below it.
  - `{"command": [...]}`: a shell command whose words start with these.
- **The agent's definition:** the runner reads it from the working copy, as the deploy resolves it, and refuses a definition that fails its check. It passes the agent's tool access in its harness's keys. It refuses a definition whose tool access the agents area's reader, or its adapter's declaration, refuses.
- **The brief's markers:** by the time the runner reads the brief, the backbone has put each folder's path in place of its marker. The markers are `{{pkit:working-copy}}`, `{{pkit:workspace}}`, `{{pkit:temp}}` and `{{pkit:commit}}`.

**The answer** is one JSON document on standard output, with exit 0: `schema_version` (`1`), `ending`, `exit_code`, `output`, `diagnostics` and `reason`. The endings:

| `ending` | When | `exit_code` |
|---|---|---|
| `finished` | the harness ran and exited | the harness's |
| `not-started` | the harness could not be started | `null` |
| `timed-out` | the harness was ended at the limit, as "The limit" below says | `null` |
| `refused` | the run was refused, with the reason, as the list below says | `null` |

A run is `refused` for one of these reasons. The first four refuse it before it starts:

- the harness or the agent is not found
- the request is one the runner does not run
- the marker of a run is set
- the harness cannot confine a confined run
- the harness's start report did not match the run's settings

What the answer's three texts hold, in either form of request unless an item names one:

- `output`: for a `finished` run, the agent's text.
  - In the unconfined form, what the harness printed on its standard output.
  - In the confined form, the agent's final message, never a tool's result.
- `diagnostics`: what the harness wrote on its standard error, which may be empty.
- `reason`: for each ending but `finished`, why the run ended so, naming the cause the table or the list above gives. A `finished` run's `reason` is empty.

Each of the three is a string, and the backbone reads one the answer leaves out as empty. Anything else the runner prints, or an exit other than 0, is a run with no answer.

A confined run's answer adds two keys:

- `refused_calls`: each call the harness refused, as `{"tool", "input"}`, or `[]` where the harness reports none.
- `start_report`: what the harness reported at its start, or `null`.

A start report that does not match the run's settings ends the run at once, as `refused`, with the mismatch as its reason.

**What a runner owes:**

- **No bypass.** It passes the harness only flags from a closed set, which its adapter's README lists. No member of the set approves a call, or loads configuration other than the run's own.
- **The limit.** At `limit_seconds`, the runner ends the harness, and every process still descended from the harness, one in a session of its own included.
  - **What it misses:** a process that left that tree before the limit, as a daemon does. The adapter's README says so.
  - **The backbone's margin:** thirty seconds past the limit, for the runner to end the harness and answer. Then the backbone asks the runner to stop with `SIGTERM`, and kills it two seconds later.
  - **Asked to stop,** a runner ends the harness the same way.
- **The environment.** It does not pass on the backbone's own variables for its run of the runner.
- **The marker.** It refuses when `PKIT_AGENT_RUN` is in its own environment, even empty. It sets `PKIT_AGENT_RUN=1` in the harness's environment, in both forms. So no route around the backbone's run command starts an agent from a run.
- **For a confined run,** each of these, as its adapter's README states:
  - the harness's version within the range its author tested the confined form on, and the platform's sandbox, or a refusal
  - only its own settings, and a checked definition
  - no flag, setting, definition field or variable that bypasses the run's rules
  - the run's rules as native rules, which fail closed
  - the shell writing only the workspace, and reaching no host

What the backbone does around a confined run, and the command itself, are [the CLI reference's, "Agent runs"](../cli/README.md#agent-runs) <!-- unanchored: points the reader on to a page that anchors this one, so an anchor back would make a cycle -->. The Claude Code adapter's runner is `run-agent.py` ([its README, "The agent runner"](claude-code/README.md#the-agent-runner-run-agentpy)).

## Harness requirements

The methodology depends on properties of the harness that hosts it, which it cannot set, only require. The core declares those requirements once, as data, in `.pkit/schemas/harness-requirements.yaml`, beside its companion `harness-requirements.schema.json` ([COR-047](../decisions/core/COR-047-harness-requirement-declaration.md)). Each entry gives these:

- **The requirement,** as behaviour any harness could show, never as one harness's key, flag or tool.
- **Its observation point,** where its truth is visible:
  - `out-of-session`: outside a session
  - `interposed-runtime`: at the harness's own hook points
  - `in-session`: only to an agent inside a session
- **Its evidence,** which admitted it. An entry needs a defect shown, or a design that depends on it. A transient entry names when it retires.

**What an adapter owes: its support declaration.** Each adapter answers the requirements for its own harness in `harness-support.yaml`, in its folder, shaped by `.pkit/schemas/harness-support.schema.json` (COR-047 point 2). It holds one answer per requirement, keyed by the requirement's id. Each answer has four fields:

- `grade`: how far the harness meets the requirement, in the vocabulary below.
- `cost`: what an `at-cost` answer asks of the project, such as a setting, a discipline or a platform. Only an `at-cost` answer has one.
- `harness_versions`: the versions the answer holds for.
  - `unbounded` means every version, as the author asserts.
  - `[lowest, highest]` means the versions the author tested it on, both included.
  - `[]` means none yet, so the answer covers no version.
  - The field is required, so an edit that drops it never widens an answer to every version. Only an author who has tested the claim widens a bound, never a tool.
- `evidence`: how the author knows the answer, such as a measurement, a test or the harness's documentation.

**Silence is indeterminate.** A requirement an adapter leaves out resolves `indeterminate`, never `satisfied`, so an incomplete declaration never reads as a passing one (COR-047 point 3). An adapter's README states its answers in prose. The Claude Code adapter's are in [its README, "Harness support"](claude-code/README.md#harness-support-harness-supportyaml).

**The grades.** COR-047 point 2 gives every adapter one vocabulary, so answers stay comparable across harnesses. The grades keep "not achievable on this harness" apart from "achievable at a cost":

| Grade | Meaning |
|---|---|
| `supported` | The harness provides the behaviour, and asks nothing more of the project. |
| `at-cost` | The harness can provide it, at the cost the answer names. |
| `not-achievable` | The harness cannot provide it at all, whatever its configuration. |

**What the report says.** `pkit harness report` resolves every requirement to `satisfied`, `unsatisfied` or `indeterminate`, for each adapter the backbone manifest registers. A result carries the adapter's grade where its answer covers some version. It carries `computed` where the pass derived the result from inputs it read in full (COR-047 points 4 and 5).

- **What the pass reads:** files only. It starts no harness, and reads no harness's configuration, environment or version, so it reaches no requirement's observation point.
- **How an answer resolves:** by the first of these that applies.
  1. No answer, or an answer for no version (`[]`): `indeterminate`, with no grade, since nothing covers the harness.
  2. An answer bounded to tested versions: `indeterminate`, since the pass does not read the harness's version.
  3. `not-achievable` for every version: `unsatisfied`, `computed`. The answer says no configuration helps, so the declaration is the whole input.
  4. `supported` or `at-cost` for every version: `indeterminate`, since nothing was read to confirm the grade. A project's own configuration can undo what the harness does by default, so a grade alone never reads as `satisfied`.
- **No `satisfied` yet:** the report gives none until a pass can read what the harness does. That needs an adapter to give the pass a way to observe it, which none does yet.
- **Its exit and its JSON** are [the CLI reference's, "`harness report`"](../cli/README.md#harness-report---adapter-name---json) <!-- unanchored: points the reader on to a page that anchors this one, so an anchor back would make a cycle -->.

**What the layer does not do.** It detects, and never alters the harness's configuration or copies a value the harness owns into the methodology's state. It runs when asked, never on each operation.

**What validation checks.** `pkit validate` checks each declaration against its schema. Validation also warns of an answer to a requirement the core does not declare: one retired, or one newer than the backbone.

**The permission dimensions stay apart.** Where an adapter's harness enforces each dimension of the permission model is its enforcement declaration's, the permission domain's case of COR-047's rule (COR-028 point 3). The support declaration does not repeat it ([the Claude Code adapter's README, "`permission-enforcement.yaml`"](claude-code/README.md#permission-enforcementyaml)).

**Status.** The core declares six requirements:

- `delegated-result-complete`: a delegated helper's full result reaches the agent that delegated to it.
- `unattended-confined-run`: a process can start an agent unattended, confined for that one run. The drift command depends on it.
- `unattended-working-run`: a process can start an agent unattended that edits and builds in a folder the process names. The build command depends on it.
- `session-loads-rules`: every session holds every layer's loaded rules from its start to its end ([COR-070](../decisions/core/COR-070-capability-loaded-rules.md) point 6). An answer names apart each kind of session the adapter's own way of starting one leaves without the files.
- `session-agent-withheld-tools`: a whole session's agent withheld named tools has none of them, and keeps every other tool its session holds. It is observed from outside a session.
- `helper-withheld-tools`: a helper withheld named tools has none of them. It is observed only inside a session.

The Claude Code adapter answers the first five. It leaves `helper-withheld-tools` unanswered until Claude Code is measured against that requirement, so the report resolves the requirement `indeterminate`. The report surfaces at no lifecycle boundary yet, such as install or upgrade (COR-047 point 8), and runs only when asked.
