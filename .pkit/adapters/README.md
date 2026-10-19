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
      record: [COR-005, COR-006, COR-047, ADR-066]
      artefact: [.pkit/adapters/claude-code/README.md]
    revalidated:
      at: 2026-10-14T08:38:50Z
      outcome: unchanged
      unchanged-because: "The claude-code README changes in one sentence: its caveat on script-wrapped diagnostics cites ADR-004's alternative \"Relabel `network-egress` as natively enforced…\" where it cited a line of ADR-004. This page names merge-settings.sh as a deploy primitive and its run order, and says nothing of that caveat or of ADR-004, so nothing it says changes."
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
    └── (harness-specific content)   # settings, deploy scripts, runtime artifacts
```

Per COR-005's bundle/adapter pattern: each adapter is an alternative implementation of "translate kit content for a specific harness." Adopters install the adapter that matches their AI tooling.

## Currently shipped

- **`claude-code/`** — the Claude Code adapter. Ships permissions baseline (settings/), the deploy scripts for skills and agents (deploy-skills.sh, deploy-agents.sh), the undeploy script for one capability (undeploy-capability.sh), the agent runner (run-agent.py, "The agent runner" below), and the runtime conventions Claude Code expects.

## Primitives the lifecycle calls

The lifecycle drives an adapter through scripts it finds **by name** in the adapter's directory: `pkit init`, `pkit sync` and the capability verbs walk `.pkit/adapters/<name>/` and run each script present. That name is the whole contract — the lifecycle carries no knowledge of where a harness keeps its skills, agents or settings; the adapter does ([COR-005](../decisions/core/COR-005-bundle-pattern.md), [COR-013](../decisions/core/COR-013-agent-architecture.md)). Every primitive is idempotent: run twice, it changes nothing the second time.

- **Deploy primitives** — `merge-settings.sh`, `merge-claude-md.sh`, `deploy-skills.sh`, `deploy-agents.sh`, run in that order with no arguments whenever the harness side needs (re-)materialising: init, sync, and a capability's install, register, upgrade and uninstall. They deploy what the tree ships and drop what they deployed from a source that is gone. Each is optional; a harness that loads skills from their canonical paths needs no `deploy-skills.sh`, and an absent one is skipped.
- **Undeploy primitive** — `undeploy-capability.sh <capability-name>`, run when a capability is unregistered but its subtree stays on disk: an incubated capability's uninstall, and any capability's uninstall in the methodology's source repository. The deploy primitives cannot help there — the source files still exist, so a deploy re-run does not see the capability as gone. The script removes what the adapter deployed for that one capability, recognised by the adapter's own deploy mark, and never adopter content. An adapter that deploys nothing per capability can ship one that does nothing. Its absence is **reported**, not skipped: the lifecycle names the adapter in a `warning` line, because that harness keeps the unregistered capability active.

## The agent runner

Some commands start an agent with nobody watching: project-management's `review-pr` starts its reviewers that way. No such command calls a harness. It asks the backbone's run command, `pkit agents run`, and the backbone starts the runner the project's adapter registers. The runner starts the harness ([ADR-066](../../tech-docs/architecture/decisions/ADR-066-unattended-agent-runner.md) point 1). So the tie to a harness's command line lives in its adapter, as every other tie does.

**What makes a runner.** Unlike the primitives above, the lifecycle never runs it, and the backbone never finds it by file name:

- **A registered command.** The adapter registers it in its package's `commands:` tree under the one reference `run-agent`. The backbone finds it through its one lookup of that tree (the lifecycle README, "How a registered command is run"). A capability's command of that name is no runner.
- **Run once for each run.** Each call starts one agent, so a runner is not idempotent. The backbone runs it under the agent-run policy of its one command runner: no arguments, the request on standard input, from the project root.
- **One runner for a project.** Where no registered adapter registers one, the run is refused, and the command that asked starts no agent and says why. Where more than one does, the run is refused too, until a record says how a project names its harness.

**The request**, one JSON document on standard input: `schema_version` (`1`), `agent`, `brief`, `folder` (an absolute path), `limit_seconds` and `effort` (a level, or `null`). A runner refuses a request with any other key, rather than run it without that key. The confined form, and its keys, arrive with the drift command (ADR-066, Implications).

**The answer**, one JSON document on standard output, exit 0: `schema_version` (`1`), `ending`, `exit_code`, `output`, `diagnostics` and `reason`. The endings:

| `ending` | When | `exit_code` |
|---|---|---|
| `finished` | the harness ran and exited | the harness's |
| `not-started` | the harness could not be started | `null` |
| `timed-out` | the harness was ended at the limit, with every process it started | `null` |
| `refused` | the run was refused before it started, with the reason: the harness or the agent is not found, or the request is one the runner does not run | `null` |

Anything else the runner prints, or an exit other than 0, is a run with no answer.

**What a runner owes:**

- **No bypass.** It passes the harness only flags from a closed set, which its adapter's README lists. No member of the set approves a call, or loads configuration other than the run's own (ADR-066 point 4).
- **The limit.** At `limit_seconds` it ends the harness and every process the harness started. The backbone gives it thirty seconds past the limit to do that and answer. Then it asks the runner to stop with `SIGTERM`, and kills it two seconds later. So a runner that started the harness in a session of its own ends that session when asked to stop.
- **The environment.** It does not pass on the backbone's own variables for its run of the runner. So a `pkit` the agent runs starts as a run of its own.

**Not yet built.** A run's marker makes a runner refuse inside a run, and it arrives with the drift command (ADR-066 point 8). So does the confined form: its clone, its settings and the check after the run. Until then, every run takes the unconfined form the review command's runs take (ADR-066 point 10).

The Claude Code adapter's runner is `claude-code/run-agent.py` (its README, "The agent runner"). The command is the CLI README's ("Agent runs").

## Harness requirements

The methodology depends on properties of the harness that hosts it — behaviour it cannot set, only require. Those requirements are declared once, as data, in `.pkit/schemas/harness-requirements.yaml` (companion `harness-requirements.schema.json`), governed by [COR-047](../decisions/core/COR-047-harness-requirement-declaration.md). Each entry states one requirement as **observable behaviour any harness could satisfy** — never as one harness's key, flag, or tool — names its **observation point** (where its truth is visible: outside a session, at the harness's own runtime hook points, or only to an agent inside a session), and cites the **evidence** that admitted it. Admission is demand-driven: an entry needs a demonstrated defect or a concrete design dependency, and a transient one names its retirement condition.

**What an adapter owes.** Each adapter answers the requirements for its own harness with a *support declaration*: a graded answer per requirement — the grading must distinguish "not achievable on this harness at all" from "achievable at a cost" — optionally bounded to a range of harness versions, and never widened automatically. The grade labels and the observation-point set are shared vocabulary owned by this area, so answers stay comparable across harnesses. An adapter that declares nothing owes nothing to exist: **silence resolves indeterminate, never satisfied**, so an incomplete declaration set never masquerades as a passing one.

**What the report says.** A verification pass resolves every requirement to `satisfied`, `unsatisfied`, or `indeterminate`, carrying the adapter's declared grade and whether the answer was `observed` or `computed`. A requirement whose observation point the pass cannot reach resolves `indeterminate` and names what could resolve it — a check that quietly passes what it did not examine is worse than no check. The layer **detects**; it does not alter the harness's configuration or duplicate a harness-owned value into methodology state. It runs on demand and at lifecycle boundaries, never on a per-operation path.

**Status.** The requirement set ships with its first entry (`delegated-result-complete`). The support-declaration shape, each adapter's answers, and the on-demand report are not yet shipped; until an adapter declares, every requirement resolves `indeterminate` for it — which is the honest state, not a defect.

## Adding a new harness

1. Create `.pkit/adapters/<new-harness-name>/`.
2. Add a `README.md` describing what the harness expects and how this adapter satisfies that.
3. Author the harness-specific content — typically some combination of settings/config files (matching the harness's format), deploy scripts (translating kit-shipped skills/agents to the harness's expected paths), an `undeploy-capability.sh` removing one capability's deployed skills/agents (see "Primitives the lifecycle calls" above), and any runtime artifacts the harness needs.
4. Update this README's "Currently shipped" list.

The structural rule is light because adapters are heterogeneous by nature — Codex's settings format differs from Claude Code's; Cursor may not need a deploy script at all if it loads skills from canonical paths directly. Each adapter ships what's needed; the README of the adapter explains.
