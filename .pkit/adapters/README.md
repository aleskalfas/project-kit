---
variant: adapter-umbrella
reader: user
kind: reference
pkit:
  friction:
    anchors:
      path:
        - .pkit/schemas/harness-requirements.yaml
        - .pkit/schemas/harness-requirements.schema.json
        - src/project_kit/agent_runs.py
        - src/project_kit/capabilities.py
        - src/project_kit/cli.py
        - src/project_kit/install.py
        - src/project_kit/sync.py
        - src/project_kit/upgrade.py
      record: [COR-005, COR-006, COR-047, ADR-066]
      artefact: [.pkit/adapters/claude-code/README.md, ".pkit/lifecycle/README.md#how-a-registered-command-is-run"]
    revalidated:
      at: 2026-10-21T15:44:42Z
      outcome: updated
---

# Adapters

Each AI harness — Claude Code, Codex, Cursor, etc. — has its own way of loading skills, agents, and configuration. The kit's own content (skills, agents, decisions, workflow) is harness-agnostic by design (per COR-006), but at some point the kit's content has to be **translated** for the harness an adopter is using: settings ported into the harness's expected file format and location, skills symlinked to the harness's expected directory, and so on.

That translation work lives here. Each harness has its own adapter directory, self-contained: `.pkit/adapters/<harness-name>/`.

## Layout

```
.pkit/adapters/
├── README.md                        # this file
└── <harness-name>/                  # one directory per supported harness
    ├── README.md                    # what this adapter handles, how to deploy it
    ├── package.yaml                 # component metadata (per COR-010)
    ├── migrations/                  # the adapter's version migrations (per COR-010)
    └── (harness-specific content)   # settings, the scripts the lifecycle calls, runtime artifacts
```

Per COR-005's bundle/adapter pattern: each adapter is an alternative implementation of "translate kit content for a specific harness." Adopters install the adapter that matches their AI tooling.

## Currently shipped

- **`claude-code/`** — the Claude Code adapter. Ships permissions baseline (settings/), the deploy scripts for skills and agents (deploy-skills.sh, deploy-agents.sh), the undeploy script for one capability (undeploy-capability.sh), the agent runner (run-agent.py, ["The agent runner"](#the-agent-runner) below), and the runtime conventions Claude Code expects.

## Primitives the lifecycle calls

The lifecycle drives an adapter through scripts it finds **by name** in the adapter's directory: `pkit init`, `pkit sync`, `pkit upgrade` and the capability verbs walk `.pkit/adapters/<name>/`, one adapter after another in name order, and run each script present. That name is the whole contract — the lifecycle carries no knowledge of where a harness keeps its skills, agents or settings; the adapter does ([COR-005](../decisions/core/COR-005-bundle-pattern.md), [COR-013](../decisions/core/COR-013-agent-architecture.md)). `pkit new adapter` stamps none of these scripts: an adapter provides the ones its harness needs, and the Claude Code adapter's are the worked example ([its README, "What this adapter ships"](claude-code/README.md#what-this-adapter-ships)).

What the lifecycle relies on, for every script:

- **It runs as a program.** The lifecycle starts the file itself, from the project root, so the file is executable and opens with an interpreter line.
- **It is idempotent.** Run twice, it changes nothing the second time.
- **Its exit status counts.** A script that exits non-zero stops the lifecycle command, with an error naming the script; the script's own output says what failed.

The scripts:

| Script | Arguments | When the lifecycle runs it | If the adapter has none |
|---|---|---|---|
| `merge-settings.sh` | none | first of the deploy primitives | skipped silently |
| `merge-claude-md.sh` | none | second | skipped silently |
| `deploy-skills.sh` | none | third | skipped silently |
| `deploy-agents.sh` | none | fourth | skipped silently |
| `undeploy-capability.sh` | the capability's name | when a capability is unregistered but its subtree stays on disk | **reported** in a `warning` line naming the adapter |

- **Deploy primitives** — the first four, run in that order whenever the harness side needs (re-)materialising: init, sync, upgrade, and a capability's install, register, upgrade and uninstall. The settings merge comes first, since a skill may rely on the settings being in place. They deploy what the tree ships and drop what they deployed from a source that is gone. Each is optional; a harness that loads skills from their canonical paths needs no `deploy-skills.sh`.
- **Undeploy primitive** — `undeploy-capability.sh <capability-name>`, run when a capability is unregistered but its subtree stays on disk: an incubated capability's uninstall, and any capability's uninstall in the methodology's source repository. The deploy primitives cannot help there — the source files still exist, so a deploy re-run does not see the capability as gone. The script removes what the adapter deployed for that one capability, recognised by the adapter's own deploy mark, and never adopter content. An adapter that deploys nothing per capability can ship one that does nothing. Its absence is **reported**, not skipped: the lifecycle names the adapter in a `warning` line, because that harness keeps the unregistered capability active, and the uninstall goes on.

## The agent runner

Some commands start an agent with nobody watching: project-management's `review-pr` starts its reviewers that way, and its `fix-drift` starts the fixers a project granted, confined. No such command calls a harness. It asks the backbone's run command, `pkit agents run`, and the backbone starts the runner the project's adapter registers. The runner starts the harness ([ADR-066](../../tech-docs/architecture/decisions/ADR-066-unattended-agent-runner.md) point 1). So the tie to a harness's command line lives in its adapter, as every other tie does.

**What makes a runner.** Unlike the primitives above, the lifecycle never runs it, and the backbone never finds it by file name:

- **A registered command.** The adapter registers it in its package's `commands:` tree under the one reference `run-agent`. The backbone finds it through its one lookup of that tree ([the lifecycle README, "How a registered command is run"](../lifecycle/README.md#how-a-registered-command-is-run)). A capability's command of that name is no runner.
- **Run once for each run.** Each call starts one agent, so a runner is not idempotent. The backbone runs it under the agent-run policy of its one command runner, which the lifecycle README states: no arguments, the request on standard input, from the project root.
- **One runner for a project.** Where no registered adapter registers one, the run is refused, and the command that asked starts no agent and says why. Where more than one does, the run is refused too, until a record says how a project names its harness.

**The request**, one JSON document on standard input: `schema_version` (`1`), `agent`, `brief`, `limit_seconds` and `effort` (a level, or `null`). A runner refuses a request with any other key, rather than run it without that key, so a runner that does not know the confined form refuses it. Then one of two forms:

- **Unconfined,** the form the review command's runs take (ADR-066 point 10): `folder`, an absolute path, where the run runs under the person's and the project's settings.
- **Confined,** the form the drift command's runs take (ADR-066 points 3 to 8): no `folder`, and `confined`, an object the backbone fills in once it has made the run's clone:
  - `working_copy`, the clone at the pinned commit, which the run reads; `workspace`, below it, the one folder the run writes, where the harness starts; `temp`, the shell's temp folder inside the workspace
  - `pkit_folder`, the folder holding the run's `pkit`, to put first on the run's path; `project_root`, the person's checkout, whose settings files the run leaves out
  - `rules`, the run's rules projected through the shared decision core: `allow`, the whole allow list, and `deny`, the denies to hold as native rules. Each rule takes one of three forms: `{"tool": T}`, the whole tool; `{"tool": T, "folder": F}`, the tool on `F` and everything below it; `{"command": [...]}`, a shell command whose words start with these. The backbone has already refused a run whose rules no native rule could hold.
  - `excluded`, the allowed commands the platform requires outside the sandbox (ADR-066 point 6), each as its words; empty off macOS

  The runner reads the agent's definition from the working copy, as the deploy resolves it, and refuses where it fails its check (ADR-066 point 3). By the time the runner reads the brief, the backbone has put each folder's path in place of its marker: `{{pkit:working-copy}}`, `{{pkit:workspace}}`, `{{pkit:temp}}` and `{{pkit:commit}}`.

**The answer**, one JSON document on standard output, exit 0: `schema_version` (`1`), `ending`, `exit_code`, `output`, `diagnostics` and `reason`. The endings:

| `ending` | When | `exit_code` |
|---|---|---|
| `finished` | the harness ran and exited | the harness's |
| `not-started` | the harness could not be started | `null` |
| `timed-out` | the harness was ended at the limit, as "The limit" below says | `null` |
| `refused` | the run was refused before it started, with the reason: the harness or the agent is not found, the request is one the runner does not run, the marker of a run is set, or the harness cannot confine a confined run; or its start report did not match its settings | `null` |

Anything else the runner prints, or an exit other than 0, is a run with no answer.

A confined run's answer adds two keys: `refused_calls`, each call the harness refused as `{"tool", "input"}`, or `[]` where it reports none; and `start_report`, what the harness reported at start, or `null`. Its `output` is the agent's final message, never a tool's result. A start report that does not match the run's settings ends the run at once, as `refused`, with the mismatch as the reason (ADR-066 point 9).

**What a runner owes:**

- **No bypass.** It passes the harness only flags from a closed set, which its adapter's README lists. No member of the set approves a call, or loads configuration other than the run's own (ADR-066 point 4).
- **The limit.** At `limit_seconds` it ends the harness and every process still descended from the harness, one the harness started in a session of its own included. A process that left that tree before the limit, as one that daemonises leaves it, is not reached, and the adapter's README says so. The backbone gives the runner thirty seconds past the limit to do this and answer. Then it asks the runner to stop with `SIGTERM`, and kills it two seconds later ([the lifecycle README, "How a registered command is run"](../lifecycle/README.md#how-a-registered-command-is-run)). Asked to stop, a runner ends the harness the same way.
- **The environment.** It does not pass on the backbone's own variables for its run of the runner.
- **The marker** (ADR-066 point 8). It refuses when `PKIT_AGENT_RUN` is in its own environment, even empty, and sets `PKIT_AGENT_RUN=1` in the harness's, for both forms. So no route around the backbone's run command starts an agent from a run.
- **For a confined run, as its adapter's README states:** the harness's version within the range its author tested the confined form on, and the platform's sandbox, or a refusal (ADR-066 point 2); only its own settings and a checked definition (point 3); no flag, setting, definition field or variable that bypasses the run's rules (point 4); the run's rules in native rules, which fail closed (point 5); and the shell writing only the workspace, with no host allowed (point 6).

**What the backbone does around a confined run** (ADR-066 point 7): it makes the clone at the pinned commit, sharing no object with the person's repository, in a folder of its own outside every working tree; provisions it as the project's checks are; makes the workspace; and records the clone's state. After the run, and after a failed start, it checks that nothing changed outside the workspace and that no reference moved, reading git as hostile. It then copies the run's files to the folder the caller named, and removes the clone. A breach comes back with what changed, and the caller sets the run's files aside. The [CLI README, "Agent runs"](../cli/README.md#agent-runs) states the command.

The Claude Code adapter's runner is `claude-code/run-agent.py` ([its README, "The agent runner"](claude-code/README.md#the-agent-runner-run-agentpy)). The command is the [CLI README's, "Agent runs"](../cli/README.md#agent-runs).

## Harness requirements

The methodology depends on properties of the harness that hosts it — behaviour it cannot set, only require. Those requirements are declared once, as data, in `.pkit/schemas/harness-requirements.yaml` (companion `harness-requirements.schema.json`), governed by [COR-047](../decisions/core/COR-047-harness-requirement-declaration.md). Each entry states one requirement as **observable behaviour any harness could satisfy** — never as one harness's key, flag, or tool — names its **observation point** (where its truth is visible: outside a session, at the harness's own runtime hook points, or only to an agent inside a session), and cites the **evidence** that admitted it. Admission is demand-driven: an entry needs a demonstrated defect or a concrete design dependency, and a transient one names its retirement condition.

**What an adapter owes.** Each adapter answers the requirements for its own harness with a *support declaration*: a graded answer per requirement — the grading must distinguish "not achievable on this harness at all" from "achievable at a cost" — optionally bounded to a range of harness versions, and never widened automatically. The grade labels and the observation-point set are shared vocabulary owned by this area, so answers stay comparable across harnesses. An adapter that declares nothing owes nothing to exist: **silence resolves indeterminate, never satisfied**, so an incomplete declaration set never masquerades as a passing one.

**What the report says.** A verification pass resolves every requirement to `satisfied`, `unsatisfied`, or `indeterminate`, carrying the adapter's declared grade and whether the answer was `observed` or `computed`. A requirement whose observation point the pass cannot reach resolves `indeterminate` and names what could resolve it — a check that quietly passes what it did not examine is worse than no check. The layer **detects**; it does not alter the harness's configuration or duplicate a harness-owned value into methodology state. It runs on demand and at lifecycle boundaries, never on a per-operation path.

**Status.** The requirement set holds two entries: `delegated-result-complete`, and `unattended-confined-run`, which the drift command depends on (ADR-066 point 13). The support-declaration shape, each adapter's answers, and the on-demand report are not yet shipped; until an adapter declares, every requirement resolves `indeterminate` for it — which is the honest state, not a defect.

## Adding a new harness

1. Run `pkit new adapter <new-harness-name>`, through the `adapter-author` skill. It stamps `.pkit/adapters/<new-harness-name>/` with `package.yaml`, `README.md` and `migrations/`, and registers the adapter. It stamps no script and no settings: those depend on the harness.
2. Fill in the stamped `README.md`: what the harness expects and how this adapter satisfies that.
3. Author the harness-specific content — typically some combination of settings/config files (matching the harness's format), deploy scripts (translating kit-shipped skills/agents to the harness's expected paths), an `undeploy-capability.sh` removing one capability's deployed skills/agents (see "Primitives the lifecycle calls" above), and any runtime artifacts the harness needs.
4. Update this README's "Currently shipped" list.

The structural rule is light because adapters are heterogeneous by nature — Codex's settings format differs from Claude Code's; Cursor may not need a deploy script at all if it loads skills from canonical paths directly. Each adapter ships what's needed; the README of the adapter explains.
