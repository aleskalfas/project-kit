---
reader: user
kind: reference
pkit:
  friction:
    anchors:
      path:
        - .pkit/adapters/claude-code/*.sh
        - .pkit/adapters/claude-code/*.py
        - .pkit/adapters/claude-code/settings/core/**
        - .pkit/adapters/claude-code/settings/project/settings.json
        - .pkit/adapters/claude-code/permission-enforcement.yaml
        - src/project_kit/visibility.py
      record: [COR-002, COR-005, COR-028, ADR-002, ADR-004, ADR-009, ADR-014, ADR-052, ADR-060, ADR-066, "project-management:DEC-030"]
    revalidated:
      at: 2026-10-20T03:23:21Z
      outcome: updated
---

# Claude Code adapter

Translates kit content for the [Claude Code](https://docs.claude.com/en/docs/claude-code/) harness. This adapter is what makes a project-kit-adopting project usable from Claude Code — sets up its permissions and deploys its skills and agents.

## What this adapter ships

```
.pkit/adapters/claude-code/
├── README.md                          # this file
├── settings/
│   ├── core/settings.json             # kit baseline — universal allows + denies
│   └── project/settings.json          # adopter's project-specific additions
├── merge-settings.sh                  # merges the settings baseline + project additions into .claude/settings.json
├── merge-claude-md.sh                 # ensures root CLAUDE.md loads the kit rules via @-includes
├── deploy-skills.sh                   # creates .claude/skills/ symlinks pointing back at .pkit/skills/
├── deploy-agents.sh                   # writes resolved agent copies into .claude/agents/
├── undeploy-capability.sh             # removes one capability's deployed skills and agents from .claude/
├── _resolve_agent.py                  # resolves one agent: overlay placeholders, model and effort, storyboard paths
├── run-agent.py                       # the agent runner: starts one agent in Claude Code for `pkit agents run`
├── probe-confined-run.py              # the probe of the runner's confined form; a person runs it, never a test
├── permission-enforcement.yaml        # which permission dimensions this harness realizes, and via which layer
└── permission-hook.py                 # the PreToolUse enforcement hook (registered by `pkit permissions enable`)
```

### `settings/`

The kit's permissions story for Claude Code — what allows and denies are pre-configured in adopters' `.claude/settings.json`. Two halves per the universal area pattern (COR-005):

- **`core/settings.json`** — kit baseline. Universal allows (`gh`, `git`, `ssh`, common UNIX tools, kit-shipped script execution, agent-tool allows, `Skill(update-config)`) and universal safety denies (`git push --force` variants, `git reset --hard`, `rm -rf` family, `sudo`). The discriminator is "would every project-kit adopter benefit?"
- **`project/settings.json`** — adopter's project-specific additions on top of the baseline (language tooling, enterprise hosts, project-specific paths). Adopters typically add allows here; denies stay in the kit baseline.

The file Claude Code actually reads is the adopter's `.claude/settings.json`, merged from these two by `merge-settings.sh`, which `pkit init`, `pkit sync` and `pkit merge` run (COR-002 / COR-004). See **How adopters use this adapter** below.

Top-level keys outside `permissions` (e.g. `agent`, `model`) in either `core/settings.json` or `project/settings.json` flow through to `.claude/settings.json` with last-write-wins precedence (project overrides core; an existing adopter entry overrides both). Keys under `permissions` merge as **What the merge keeps under `permissions`** below says.

**Ownership modes (COR-002 authoritative-region tier).** By default (`ownership_mode: additive`) the merge is append/union/baseline-enforce — it only ever *adds* to `permissions` and re-asserts the safety denies, never removing adopter entries. Under `ownership_mode: managed` (set via `pkit permissions mode managed`), the realizer **owns the `permissions` region** and regenerates it **wholesale** from its model projection: the merge replaces `.permissions` with the projection supplied per-run (via `$PKIT_MANAGED_REGION_FILE`, written by `pkit permissions apply`) instead of unioning it, so a grant removed from the model vanishes (drift heals down to empty) — everything *outside* `.permissions` stays byte-for-byte adopter-owned. This needs no in-file markers and no strip-logic: `permissions` is already stripped from every source and recomputed each run, so managed mode only swaps the *source* of that recompute. The owned region is the fixed realizer constant `.permissions` (the hook rides the separate top-level `hooks` key); the gate is the `ownership_mode` config flag, never file-presence, so a stray region file can't reactivate managed behaviour. Managed mode only replaces when a projection is actually supplied: a plain `pkit sync` in managed mode with no projection in hand falls through to the additive default (it never blanks the region). *(The `apply` realizer that generates the projection is a later increment; this section documents the merge-primitive tier it builds on.)*

**Capability-contributed overlays** (per [project-management:DEC-030]). Installed capabilities can ship per-harness overlay templates and adopter-toggled live overlays under `.pkit/capabilities/<cap>/adapters/claude-code/overlay.template.json` (core-owned) and `.pkit/capabilities/<cap>/project/adapter-overlays/claude-code.json` (adopter-owned). `merge-settings.sh` walks manifest-registered capabilities; each capability whose adopter-owned overlay file is *present* contributes its top-level keys into the merge chain between `project/settings.json` and the existing target. The opt-in flow is the capability's own `enable-*` / `disable-*` CLI subcommand pair; for project-management, see `pkit project-management enable-default-agent`. Overlay `permissions` keys are reserved — silently stripped at merge time so overlays cannot influence any key under `permissions`.

### `merge-claude-md.sh`

Ensures the adopter's root `CLAUDE.md` loads the kit-shipped rules (`@.pkit/rules/core.md`) and project rules (`@.pkit/rules/project.md`) via Claude Code's `@<path>` include mechanism. Per the COR-002 merge contract (insert-if-absent / create-if-none posture):

- **No CLAUDE.md:** creates a minimal one with an H1 and the `@`-includes.
- **CLAUDE.md without the include:** inserts the `@`-include block after the first H1 (per core.md rule 13's authoring convention — included sections must nest under the host's heading, not appear at line 1). If no H1 is found, prepends a minimal header + includes above the existing content.
- **CLAUDE.md already has the include:** no-op (idempotent).

Adopter content is never clobbered. Both `@.pkit/rules/core.md` (kit-owned, refreshed on sync) and `@.pkit/rules/project.md` (adopter-owned, never overwritten) are wired together so their rules compose in the agent's context.

`merge-claude-md.sh` is an adapter primitive: `pkit init` and `pkit sync` invoke it (alongside `merge-settings.sh`, `deploy-skills.sh`, `deploy-agents.sh`) so the wiring is maintained automatically. Running it by hand is always safe.

### `deploy-skills.sh`

Walks `.pkit/skills/{core,project}/` and creates relative symlinks at `.claude/skills/<name>/` so Claude Code can discover and load the skills. Idempotent; safe to re-run; skips non-kit-managed content under `.claude/skills/`. Per COR-005's adapter pattern, this is the Claude-Code-specific deployment for the harness-agnostic skill content stored at `.pkit/skills/`.

**Capability skills: registered capabilities only.** A capability's `skills/` folder deploys when the capability is registered in `.pkit/manifest.yaml`, not because its directory sits under `.pkit/capabilities/` — a capability unregistered in place (an incubated one, or one in the methodology's source repository) keeps its subtree on disk, and its skills must stop deploying all the same. On a name collision the project's skill wins, then core's, then a registered capability's (the first by name).

**Stale removal.** Each run removes a deployed skill whose name no longer resolves — its source gone, or its capability no longer registered — so the deploy after an unregister drops that capability's skills. It also removes a deployed sub-procedure link the winning source no longer has. Only the deploy's own entries are removed — symlinks into `.pkit/skills/` or `.pkit/capabilities/`; a real file or directory, or a symlink pointing elsewhere, is adopter content and is left alone.

A listed skill whose canonical file doesn't resolve — most commonly a composite skill folder mid-build (per COR-020): sub-procedures present but no `<name>/<name>.md` dispatcher yet — is **skipped loudly** (a `skipped` status line naming the skill and defect, plus a remediation hint), not treated as fatal. The rest of the skills deploy and the run exits 0 with an end-of-run summary. This is deliberate: one half-built incubated skill must never abort a whole-project `pkit sync`/`upgrade`. `deploy-agents.sh` applies the same degrade-loudly discipline to an agent folder with no canonical `<name>/<name>.md` (and to an overlay category left undefined in a **hard** channel — `owns`/`needs`/`answers`/`reads.paths`/`reads.records`; a category referenced *only* via `reads.patterns` is an optional read per [ADR-052](../../../tech-docs/architecture/decisions/ADR-052-optional-read-category-empty-tolerance.md), whose absence drops the item and still deploys the agent; a *bare* optional key — present with no value — deploys the same way but prints a `warning` status line naming it).

### `deploy-agents.sh`

Writes each kit-shipped agent as a **resolved copy** at `.claude/agents/<name>.md` — copies, not symlinks, because the source carries overlay placeholders the deploy substitutes (the agents README, "Deploy mechanics"). `_resolve_agent.py` resolves one agent: it substitutes the `<category>` placeholders from `.pkit/agents/project/overlay.yaml` and carries the agent's execution policy into the deployed front matter.

**Name collisions.** When more than one location ships an agent of one name, the project's is deployed, else an installed capability's (the first by capability name), else core's — a capability's agent is the discipline's specialisation of a core default ([COR-026](../../decisions/core/COR-026-agent-placement-by-discipline.md)). The agents README, "Name-collision precedence", states the rule and the collisions between capabilities.

**Model and effort** (#1047). Claude Code reads a `model:` and an `effort:` key from an agent definition's front matter (verified against Claude Code 2.1.283: `effort` takes `low`, `medium`, `high`, `xhigh`, `max`, or an integer; `model` takes `inherit`, an alias or a full model name). The resolver writes both under those names, taking each from the overlay's `overrides.<agent>.model` / `.effort` when set, else from the agent's front matter. It writes **nothing** for an absent or `inherit` value — so a shipped agent that sets neither deploys exactly as before, and the harness default applies: a dispatched agent inherits its caller's model and effort. A value outside the accepted set (the named effort levels only; the integer form is not part of the methodology's vocabulary) is not written: the agent still deploys, inherits, and the run prints a `warning` line naming the value. The accepted values, the precedence and the `pkit agents` report are specified in the agents README, "Model and effort".

**Precedence with `review-pr --effort`.** A run-time effort resolved by `review-pr` (the project-management capability's `--effort` flag, `PKIT_REVIEW_AGENT_EFFORT`, or `review.agents.effort`) wins over the agent's deployed `effort:` — a run-time knob over a declaration. `review-pr` passes the value to the reviewer's run, and the agent runner (`run-agent.py`, below) passes it as the reviewer session's `--effort`, the harness's session-level setting (the same shape by which a `--model` flag wins over an `--agent`'s `model:`). When `review-pr` resolves none it passes nothing, and the deployed value applies.

**Storyboard references** (#1101). An agent that drives scripted scenarios declares its storyboards (COR-016) in `storyboards:` and cites them in its body. The source names a storyboard by its bare sibling filename (`storyboard.md`), which stays right wherever the agent's folder lives — core, project or a capability. The deployed copy lives in `.claude/agents/`, where that name resolves to nothing, so the resolver rewrites each entry naming a file beside the source to the storyboard's project-root-relative source path, in the list and wherever the body cites the entry as a whole path; the runtime reads the storyboard from there with its `Read` tool. An entry already written as a source path deploys unchanged. The convention is stated in the agents README, "Frontmatter declaration" under "Storyboards".

### `undeploy-capability.sh`

`undeploy-capability.sh <capability-name>` removes one capability's deployed skills and agents from `.claude/` — the inverse of the two deploy scripts above, for that capability alone. The lifecycle runs it when it unregisters a capability whose subtree stays on disk (an incubated capability's uninstall, or any capability's in the methodology's source repository): the deploy scripts drop what they deployed only once its source file is gone, and here it is not. The lifecycle passes the capability's name and knows nothing of `.claude/` (the adapters README, "Primitives the lifecycle calls").

It removes only what the deploy scripts created for the capability, recognised by the mark each leaves:

- **a skill** — a `.claude/skills/<skill>/` whose `SKILL.md` is the relative symlink `deploy-skills.sh` writes into `.pkit/capabilities/<name>/`. Every symlink in that folder pointing into the capability goes, and the folder goes once empty; an adopter's file left in it keeps the folder (a `kept` line says so).
- **an agent** — a `.claude/agents/<agent>.md` carrying `deploy-agents.sh`'s marker, for an agent the capability ships in its `agents/` folder (flat or folder form). A copy is kept when a project agent of the same name exists: project agents outrank every other source (the agents README, "Name-collision precedence"), so the copy is the project's.

Adopter content — a file that is not such a symlink, a symlink pointing anywhere else, an agent without the marker — and the capability's own subtree are never touched. The script removes what exists for the capability whatever its registration, so it runs the same before or after the unregister; it is idempotent (`Done. Nothing deployed for capability <name>.` on a second run) and exits 2 on anything but one capability name. Status lines: `removed`, `kept`.

### The agent runner (`run-agent.py`)

The one place `claude` is started for an agent nobody watches ([ADR-066](../../../tech-docs/architecture/decisions/ADR-066-unattended-agent-runner.md) points 1 to 4, 6, 8 to 10 and 12). The adapter registers it in its `package.yaml` under `commands:` as `run-agent`, and the backbone's `pkit agents run` starts it. No command calls `claude` itself: project-management's `review-pr` starts its reviewers through it, and its drift command its fixers. The contract every adapter's runner answers is [the adapters README's, "The agent runner"](../README.md#the-agent-runner). This section is how this one answers it.

It runs under the system `python3` with the standard library only, as the permission hook does, so it needs nothing to provision. In the confined form it runs the deploy's resolver, which runs on `uv`, as the deploy does.

**Two forms.** A request with `folder` takes the unconfined form, the one the review command's runs take (ADR-066 point 10). A request with `confined` takes the confined form, the one the drift command's runs take. A request with both, or with any other key the runner does not run, is refused.

**The marker** (ADR-066 point 8). The runner refuses every request when `PKIT_AGENT_RUN` is in its own environment, even empty, and starts nothing. It sets `PKIT_AGENT_RUN=1` in the harness's environment for every run, of either form. So every process of a run inherits it, and a run cannot start another agent through the runner.

#### The unconfined form

- It refuses the run when `claude` is not on `PATH`, or when the agent is not deployed. Deployed means `.claude/agents/<agent>.md` exists in the run's folder or a folder above it, or in the person's own agents folder (`$CLAUDE_CONFIG_DIR/agents`, else `~/.claude/agents`).
- It starts `claude` in the run's folder, in a session of its own, and writes the brief to its standard input. So no word of the brief is read as a flag.
- The harness gets the runner's environment, less the backbone's own variables for its run of the runner (`PKIT_COMMAND_DEADLINE`, `PKIT_COMMAND_STRAYS`, `PKIT_RUN_CACHE`), and with the marker set.
- It starts the `claude` it found on `PATH`, made absolute. So a relative `PATH` entry never runs a `claude` that the run's folder holds.
- Its answer's `output` is the harness's standard output.

**The unconfined form's closed set of flags** (ADR-066 point 4). The runner passes only these, and refuses to build a command line with any other:

| Flag | Passed |
|---|---|
| `-p` | always |
| `--agent <agent>` | always |
| `--effort <level>` | where the run sets an effort |

None of them approves a call by itself. `--agent` makes the agent's definition the session's agent, so a field that definition carries, such as a permission mode, hooks or MCP servers, applies as in any session started with it. The unconfined form checks no definition. Among the flags it never passes are `--dangerously-skip-permissions`, `--allow-dangerously-skip-permissions`, `--permission-mode`, `--permission-prompt-tool`, `--allowedTools`, `--add-dir`, `--settings`, `--agents` and `--mcp-config`.

**What the unconfined form leaves open.** The run takes the person's and the project's settings in its folder, as a session started there would. It starts in the mode those settings or the harness choose, and the runner passes no settings of its own. So a run may write in the folder, and may start in a mode that approves calls no rule allows (ADR-066 point 11). The hook judges a run's calls as it judges a person's session. `--agent` does not change the `agent` key the hook reads, so which subject it judges there is not yet known ([the permissions README, "Default-agent subject resolution"](../../permissions/README.md#default-agent-subject-resolution)).

#### The confined form

**The request.** It carries the unconfined form's keys without `folder`, and `confined`, an object of these keys. Any other key, or a missing one, refuses the run.

| Key | What it is |
|---|---|
| `working_copy` | the run's clone at the pinned commit |
| `workspace` | the folder in the clone that the run's shell writes; the harness starts there |
| `temp` | the shell's temp folder, inside the workspace |
| `pkit_folder` | the folder of the run's `pkit`, first on the run's `PATH`, outside the workspace |
| `project_root` | the person's checkout, whose settings' denies the run carries |
| `rules` | `allow` and `deny`, each a list of rules in the three forms below |
| `excluded` | the allowed command prefixes the platform runs outside the sandbox |

Each folder must be an absolute directory. The workspace must lie inside the working copy and be no link, the temp folder inside the workspace, and the `pkit` folder outside it. Each excluded prefix must be a command the allow list holds.

**The rules,** in Claude Code's terms:

| Form | Rule |
|---|---|
| `{"tool": T}` | `T`, the whole tool |
| `{"tool": T, "folder": F}` | the tool on F and everything under it, in T's rule family: `Read(//F/**)` for `Read`, `Grep` and `Glob`, `Edit(//F/**)` for `Write`, else `T(//F/**)`. F's absolute path follows `//` without its own leading slash |
| `{"command": [token, …]}` | `Bash(<the tokens, joined by one space>:*)` |

A token that holds whitespace, a quote, `*`, `(`, `)` or a control character refuses the run, since it could widen its rule. So does a folder that holds a character a path rule reads as a pattern, or that is not a plain absolute path.

Claude Code matches the path of a tool that reads only against `Read(...)` rules, and of a tool that writes only against `Edit(...)` rules. So a folder rule is written in that family's name, and the same rule is written once.

**The denies.** A deny of a tool that is not among the run's tools, such as `Edit`, `MultiEdit` or `NotebookEdit`, is held by the tool list and is not written as a native rule. A bare `Edit` rule would take `Write` away from the workspace too. Any other deny that reaches a call an allow reaches, in the same rule family, refuses the run, naming both. A deny of a whole tool reaches all of its family; a folder reaches the folders inside it and above it; a command reaches the commands it starts, and those that start it.

**Refused before the start.** Each refusal names its cause (ADR-066 point 2):

- **The tested version range.** The runner refuses a harness whose version lies outside `TESTED_RANGE`. The range ships empty, so every confined run is refused today. It stays empty until the adapter's author runs the probe below on a harness and it passes. Only that author widens it (COR-047 point 2).
- **The platform's sandbox.** macOS needs its own `/usr/bin/sandbox-exec`. Linux needs `bwrap` and `socat` on the run's `PATH`. Any other platform has no sandbox the harness can use.
- **The runner's own copy.** The runner must lie in the working copy's adapter folder. The backbone runs the clone's copy, so the resolution it applies is the pinned commit's.
- **The agent's definition** fails its check, below.
- **The run's settings** fail the part of the harness's settings schema the runner writes. The runner keeps that part as data (`SETTINGS_SCHEMA`), since a `-p` run skips a value it rejects. They are refused too where they miss a value the confined form always holds, or where a settings file whose denies they carry cannot be read.

**The agent's definition** (ADR-066 point 3). The runner always passes the definition itself, with `--agents`.

- **The file the deploy picks.** The runner looks in the working copy as `deploy-agents.sh` does: the project's agent, then an installed capability's (the first by name), then core's, each flat form before folder form. A file that leads outside the working copy is refused.
- **As the deploy resolves it.** The resolver beside the runner, `_resolve_agent.py`, resolves the file against the working copy's overlay. It applies the overlay, carries the model and the effort, and names each storyboard by its path from the clone's root.
- **Refused where the deploy would not carry it.** The run is refused where the resolver fails, and where it warns that it drops the model or the effort. Any other warning refuses too, except the one for an optional read set with no value: nobody watches the run to read it.
- **Only the methodology's shape.** Every front-matter field must be `name`, `description`, `tools`, `model`, `effort`, or a field of the reference graph: `reads`, `owns`, `needs`, `answers`, `gates`, `storyboards` and `composes`. A field outside that shape, such as `hooks`, `mcpServers`, `permissionMode`, `memory`, `skills` or `isolation`, refuses the run rather than being trimmed. A test holds the set to the backbone's own (`refs.Declared`).
- **Passed:** the description, the body as the prompt, the tools, the model and the effort. The caller's effort, where it sets one, wins over the definition's. The other fields are read and never passed.
- **The name is replaced** by `pkit-run-` and sixteen hex digits, unique to the run. So no other agent answers to it.
- **Read with the standard library.** The runner reads the resolved front matter with a narrow reader of its own. A form it does not read, such as an anchor, a tag or a nested list, refuses the run.

**The run's settings,** passed inline with `--settings`, so no file holds them:

| Key | Value |
|---|---|
| `permissions.allow` | the request's allow list, rendered |
| `permissions.deny` | the request's denies the run holds natively, as "The denies" says, then the deny rules of each settings file the run leaves out, copied as written: the person's user settings (`$CLAUDE_CONFIG_DIR/settings.json`, else `~/.claude/settings.json`), the working copy's `.claude/settings.json`, and the person's checkout's `.claude/settings.json` and `.claude/settings.local.json`. A copied deny the tool list already holds is left out: a tool outside the run's alone, such as `Edit`, or with content no tool of the run is matched against, such as `WebFetch(domain:…)`. `Edit(path)` is copied, since `Write` is matched against it. A copied deny that would take part of an allow away is held natively, and not refused: it takes only that part |
| `permissions.defaultMode` | `dontAsk` |
| `permissions.disableBypassPermissionsMode` | `disable` |
| `permissions.blockReadsOutsideWorkingDirectories` | `true`: the file tools read nothing outside the workspace that a rule does not open; the run's `Read` rule opens the clone |
| `sandbox.enabled` | `true` |
| `sandbox.failIfUnavailable` | `true`: the harness stops at start when the sandbox cannot start |
| `sandbox.autoAllowBashIfSandboxed` | `false`: no sandboxed command runs without a rule |
| `sandbox.allowUnsandboxedCommands` | `false`: no retry outside the sandbox |
| `sandbox.excludedCommands` | the request's excluded prefixes, each joined by one space |
| `sandbox.network.allowedDomains` | `[]`: no host |
| `autoMemoryEnabled` | `false`: the harness's memory is off |

**The confined form's closed set of flags** (ADR-066 point 4). Each flag takes the one value shown. The runner refuses to build a command line with any other flag, any flag twice, or another value.

| Flag | Passed |
|---|---|
| `-p` | always |
| `--setting-sources ""` | always: no settings file of the person's or the project's loads |
| `--settings <json>` | always: the run's settings |
| `--agents <json>` | always: the checked definition, under the run's name |
| `--agent <the run's name>` | always |
| `--permission-mode dontAsk` | always |
| `--permission-prompts none` | always |
| `--tools Read,Glob,Grep,Write,Bash` | always |
| `--strict-mcp-config` | always: no MCP server connects |
| `--disable-slash-commands` | always: no skill runs |
| `--no-session-persistence` | always |
| `--output-format stream-json` and `--verbose` | always: the stream the runner reads |
| `--include-hook-events` | always: so a hook that runs shows |
| `--effort <level>` | where the run sets an effort |

Never passed to a confined run: `--add-dir`, `--allowedTools`, `--mcp-config`, `--permission-prompt-tool`, `--dangerously-skip-permissions`, `--allow-dangerously-skip-permissions`, or a mode other than `dontAsk`. ADR-066 point 3 leaves `--restricted` or `--setting-sources` to the probe. The runner passes `--setting-sources ""`: `--restricted` confines the file tools to the working folders, and with no `--add-dir` the run could not read its clone.

**The environment** (ADR-066 point 4) holds only what the harness and the run's commands need:

- `PATH`: the run's `pkit` folder first, then the folder the harness was found in, then git's, then `/usr/bin`, `/bin`, `/usr/sbin` and `/sbin`
- `HOME`, `USER`, `LOGNAME`, `SHELL`, `LANG` and each `LC_*`
- `TMPDIR` and `CLAUDE_CODE_TMPDIR`, both set to the run's temp folder, so the shell's temp folder lies in the workspace
- the proxy and gateway variables the harness reaches its model through: `HTTPS_PROXY`, `HTTP_PROXY` and `NO_PROXY`, each in either case, and `ANTHROPIC_BASE_URL`
- the harness's sign-in variables: `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN` and `CLAUDE_CODE_OAUTH_TOKEN`; for Amazon Bedrock `CLAUDE_CODE_USE_BEDROCK`, `AWS_REGION`, `AWS_PROFILE`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN` and `AWS_BEARER_TOKEN_BEDROCK`; for Google Vertex AI `CLAUDE_CODE_USE_VERTEX`, `CLOUD_ML_REGION`, `ANTHROPIC_VERTEX_PROJECT_ID` and `GOOGLE_APPLICATION_CREDENTIALS`; for Microsoft Foundry `CLAUDE_CODE_USE_FOUNDRY`, `ANTHROPIC_FOUNDRY_API_KEY` and `ANTHROPIC_FOUNDRY_RESOURCE`
- `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1`, so the harness keeps the sign-in variables from every command it starts
- `PKIT_AGENT_RUN=1`

Nothing else reaches the harness: no `CLAUDE_CONFIG_DIR`, no `UV_*`, and no variable that changes the harness's permissions or the folder it reads its configuration from. The one variable that touches its sandbox, `CLAUDE_CODE_TMPDIR`, only moves the shell's temp folder into the workspace. The run's `pkit` sets the `uv` settings it needs itself.

**The start report** (ADR-066 point 9). The harness starts in the workspace, in a session of its own, with the brief on its standard input. The runner reads the stream line by line. The first `system` event of subtype `init` is the start report. The run ends at once when:

- the mode is not `dontAsk`
- the harness offers a tool outside the five
- the report lists any MCP server or any plugin, or does not list them
- a hook event, a `system` event of subtype `hook_…`, appears at any time
- the harness reports work before its start report

The answer is then `refused`, with what did not match as the reason and the report, where one came, in `start_report`. A run that ends with no start report is refused too, since nothing shows it was confined.

**The answer.** For a confined request it adds two keys, even to a refusal:

- `refused_calls`: each call the harness refused, as `{"tool", "input"}`, from the result's `permission_denials`
- `start_report`: the start report as the runner read it, or `null`

`output` is the result's text, the agent's final message, never a tool's result. `diagnostics` is the harness's standard error.

#### The limit, for both forms

At the limit the runner ends the harness and every process still descended from it. A confined run's limit counts from the runner's start, so the checks before the harness starts count against it.

- Claude Code starts each shell command in a session of its own, which a kill of the harness's process group would not reach. So the runner first stops the harness's group, so it starts nothing more. It then reads the process table with `ps`, and stops the group of each process descended from the harness, until a reading finds no new one. Then it kills every group it stopped.
- **What it cannot reach.** A process that left the harness's tree before the limit is not found: one that daemonises, or whose parent ended and left it to the system. Where the system's own `ps` (`/bin/ps` or `/usr/bin/ps`) cannot be read, the runner ends the harness's own group alone.
- Asked to stop (`SIGTERM`, `SIGHUP`, `SIGINT`), it ends the harness the same way, and exits with no answer.

#### The probe (`probe-confined-run.py`)

A script a person runs, never a test (ADR-066 point 12). It starts one real run, which signs in and spends, so it refuses to start unless given `--start-claude`:

```
python3 .pkit/adapters/claude-code/probe-confined-run.py --start-claude
```

It makes a scratch git repository in a new folder under `~/.cache` (or `--root`), outside every working tree and the harness's shared temp folder. It copies this runner and the resolver into it, adds a small probe agent, and starts one confined run through the runner's own functions, with a fixed brief. It tests the harness it finds, so it holds the tested range at that harness's version for its own run only. It prints one line for each fact it checks from outside the run, `pass` or `FAIL`, and exits 0 only when all pass:

- with only the run's settings and the passed definition, the agent starts and the harness signs in
- the start report gives the mode, `dontAsk`; the tools, the run's own; and the MCP servers and plugins, none
- the shell and the file tools write the workspace, and nothing outside it, the clone's git folder included
- with reads outside the working folder blocked, the run's `Read` rule opens the clone, and a file-tool read outside the clone is refused
- a call outside the run's settings is refused, with no prompt, and the run goes on
- the marker reaches the run's shell
- the shell's temp folder lies in the workspace

Only when every line passes does the adapter's author widen `TESTED_RANGE` to that version.

**What rests on the documentation until the probe runs.** These come from Claude Code's documentation and its 2.1.302 release:

- the settings' names and types in `SETTINGS_SCHEMA`, and the form of a permission rule the runner checks
- that `--setting-sources ""` loads no settings file, and that `--agents` takes `description`, `prompt`, `tools`, `model` and `effort`
- that `TMPDIR` and `CLAUDE_CODE_TMPDIR` place the shell's temp folder in the workspace
- that the harness matches a reading tool's path against `Read(...)` rules and a writing tool's against `Edit(...)` rules, and that a bare `Edit` deny would take `Write` away
- that the run's `Read` rule opens the clone while `blockReadsOutsideWorkingDirectories` is on. The schema says the block holds "in every permission mode", and does not say a rule reopens it
- the start report's fields (`permissionMode`, `tools`, `mcp_servers`, `plugins`), the hook events' subtypes, and the result's `result` and `permission_denials`
- the sign-in variables, and what the sandbox needs on each platform
- that the start report does not say whether the sandbox started. `failIfUnavailable` stops the harness at start instead.
- that an allow rule such as `Bash(git -C <clone> log:*)` matches no command that sets a variable before it, such as `GIT_EXTERNAL_DIFF=… git -C <clone> log`. A variable a command sets could make git run another program, so a rule that matched it would let the run do what the rules refuse
- that `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1`, which the runner sets, keeps the sign-in variables from every command the run's shell starts

#### What stays open

The confined form holds what the harness can hold. This is what it cannot, stated rather than hidden (ADR-066 point 11):

- **Network egress.** No host is allowed. But the sandbox checks the host a client names, so it does not stop data leaving. An excluded command has the person's full network access. The harness's own connection to its model carries what the run reads.
- **Commands that start `uv`.** On macOS they run outside the sandbox under the platform's exclusion, held by the run's rules alone. Their writes outside the clone, and their network access, go unseen. On Linux they fail inside the sandbox.
- **The harness's read-only commands** run under `dontAsk` with no rule. The set is the harness's, and it changes between releases.
- **The shell's reads.** The file tools read only the workspace and what a rule opens. The shell reads what the sandbox's defaults let it read, most of the machine. The 2.1.302 schema has `sandbox.filesystem.denyRead`, and `allowRead`, which "takes precedence over denyRead". So the person's home could be denied, with the clone, the run's `pkit` folder and the installed tool reopened. But the request does not name the installed tool's folders (the interpreter the run's `pkit` runs, and its base), so the runner sets neither key yet. A probe fact, and a question for the request's shape.
- **What the hook sees.** A confined run loads no project settings, so the hook does not run in it. The start report and the backbone's check after the run stand in for it.
- **The person's instructions.** The harness reads the person's own `CLAUDE.md`, and any above the folder it starts in.
- **An organisation's managed settings** reach every run, and nothing drops them. They may allow more, or run hooks of their own.
- **What the limit reaches**, as "The limit, for both forms" says. A run that finishes on its own is not ended either: a process it left running in a session of its own runs on while the backbone checks the clone and copies the run's files. The copy reads the workspace by file descriptors, so such a process cannot swap a link in under it, but what it writes before the copy goes into the run's files, which are untrusted data in any case.
- **What an allowed command's options do.** A rule allows a command with any arguments after its words. No allowed form has an option that runs another program, as `git grep --open-files-in-pager` does, which is why the rules leave it out. An option that writes a file, such as `--output`, is held by the sandbox, which writes only the workspace.
- **The review command's runs** take the unconfined form, and nothing checks them.

### Live permission enforcement (`permission-hook.py`)

The realizer that makes declared permissions *bite* at runtime (per [COR-028](../../decisions/core/COR-028-permission-model-realization.md) / [ADR-002](../../../tech-docs/architecture/decisions/ADR-002-permission-realizer-ownership.md)). It's **opt-in** — see *enable / disable* below.

`permission-hook.py` runs under the **system `python3`** interpreter — no `uv`, no PEP-723 metadata, no third-party deps at startup. This is required so the hook starts inside macOS Seatbelt, where `uv` panics on a fixed `SCDynamicStore` denial (ADR-014). On each matched tool call Claude Code pipes a PreToolUse payload to its stdin; the hook builds the model through the shared, harness-neutral decision core (`.pkit/permissions/decide.py`) and either prints a `permissionDecision` (`allow` / `deny`) or **abstains** (exit 0, no stdout → the harness's normal permission flow proceeds). It imports the *same* `decide.load_model` + `decide.decide` the `pkit permissions` CLI uses, so the hook and the CLI can never decide differently (ADR-002's same-code invariant).

**Zero-dep shebang + stdlib YAML fallback.** The hook's shebang is `#!/usr/bin/env python3` (bare, no `uv`). The shared loader in `decide.py` (`load_yaml`) tries `ruamel.yaml` when available and falls back to a stdlib-only YAML-subset parser when not — handling the full file subset (block mappings/sequences, single/double-quoted strings, flow sequences, block scalars, booleans). **The fallback lives in the shared `decide.py` loader, not in the hook**, so both the hook and the `pkit permissions` CLI parse via the same code path — the same-code invariant is mechanically preserved, not aspirational.

**The double-lock.** The non-negotiable guardrail denies — every privilege the catalog flags `guardrail: true` (currently `privilege-escalation`, `destructive-fs`, `vcs-history-rewrite`) — are enforced in two independent layers:

1. **fail-open hook half** — synthesized as `{subject: all, effect: deny}` grants in the model, derived from the privileges the catalog flags `guardrail: true` (the catalog is the single source of truth). The hook **fails open on decision faults** (malformed payload, ambiguous model): any such fault yields a silent abstain, never a silent block. Set `PKIT_PERMISSIONS_DEBUG=1` to surface decision fault reasons on stderr.
2. **fail-closed native half** — the catastrophic `deny` patterns in `settings/core/settings.json`. These hold even if the hook is absent, faults, or is version-skewed, so failing open in layer 1 can never bypass them.

**Enforcement-runtime fault taxonomy (ADR-002 point 4).** The fail-open contract covers *decision faults* (hook ran, couldn't resolve). A distinct class — *enforcement-runtime faults* — means the hook **cannot start at all** (python3 missing, decide.py absent, syntax error). This class is **fail-loud**, not fail-open: `pkit permissions enable` and `pkit permissions sandbox enable` run a startup self-check after registering the hook and warn loudly if the hook cannot start, so the operator learns enforcement is not running rather than believing a dead hook is gating calls. `pkit permissions overview` also surfaces this state when enforcement is registered-but-dead: it runs the self-check and reports "ENFORCEMENT-RUNTIME FAULT — hook CANNOT START" with the diagnosed reason.

**enable / disable** (the opt-in toggle, per issue #247's "Option B" — mirroring the [project-management:DEC-030] default-agent precedent). Because the hook fires per tool call, registering it is the adopter's explicit choice, not an install default:

```
pkit permissions enable
```

Registers the hook under the top-level `hooks.PreToolUse` key in `.claude/settings.json` (command `${CLAUDE_PROJECT_DIR}/.pkit/adapters/claude-code/permission-hook.py`, matcher `*`) and ensures the fail-closed native guardrail denies are present. Refuses if the claude-code adapter isn't installed. Idempotent.

After registering, runs the **enforcement-runtime self-check** (per ADR-002 point 4): drives the hook script under `python3` with a probe payload to verify it can start. If the hook cannot start (python3 missing, decide.py absent, etc.), outputs a loud WARNING naming the fault and the remediation — rather than silently proceeding with a dead hook that fail-opens on every call.

```
pkit permissions disable
```

Strips *only* the pkit hook registration (matched by its command path), preserving any other adopter hooks, and leaves the native guardrail denies in place. The explicit strip is required because the merge primitive treats existing top-level settings keys as last-write-wins survivors — the DEC-030 strip-logic pattern. Idempotent; leaves no orphaned registration.

The hook **script** itself is a propagated adapter file — `pkit sync` owns its lifecycle, so `enable`/`disable` manage only its *registration*, never deploy or remove the file (there is no orphaned-script failure mode). The registration is written only to the live `.claude/settings.json`, never to a merge source, so it survives re-merge and is removable by strip (the `hooks` key lives outside any realizer-owned region per ADR-002).

**`pkit permissions sandbox enable`** sets `failIfUnavailable: true` always (the ADR-004 / ADR-014 §6 fail-closed invariant), so Claude Code refuses to start an unconfined session rather than silently running without a box. It also runs the enforcement-runtime self-check (same as `enable`) AND verifies **actual confinement** — attempts a write outside the workspace that Seatbelt/bubblewrap must deny. If the write succeeds, it warns "sandbox configured ON but NOT actually confining" loudly (box may not have initialized, or the session hasn't been restarted). `pkit permissions sandbox status` and `pkit permissions overview` report the same actual-confinement probe result so the operator never believes confinement is active when it is not.

### Prompt-free command shape under the sandbox

This is the Claude Code realization of the universal "work with the permission layer, not around it" rule (`.pkit/rules/core.md`). With the sandbox on, `.claude/settings.json` carries `sandbox.autoAllowBashIfSandboxed: true` — so a **single, simple Bash command auto-allows** because it runs inside the box, no prompt. What still prompts is the command *shape* the parser can't statically vet: a leading `cd`, statements chained with `;`, pipelines (`| grep | head`), and command substitution. Those fall back to a confirmation even under the sandbox, and an allow-list entry for the inner tool does not help (the parser keys on the outer/first token). So the agent's discipline is: **one clean command per call; the harness's `Read` / `Grep` / `Glob` / `Write` tools for inspection and file I/O — not `cat`/`sed`/heredocs/pipelines.**

For a genuinely multi-step diagnostic, compose the complexity into a file and run it as one invocation: author the script with the `Write` tool in the agent workspace (prompt-free, and the call shows its contents), then run a single `bash .agent-workspace/<file>`. The parser sees only that one clean command; the box auto-allows it; the multi-step logic runs *inside* the sandbox.

**Caveat — this is for read-only diagnostics only.** Wrapping commands in a script **bypasses the PreToolUse hook**: the hook inspects the outer `bash <file>` invocation, not the script's contents, so a gated mutation hidden inside a script (e.g. a raw `gh issue edit` the model denies) slips past the check. The OS sandbox still bounds the script at the OS level, but the hook's *intent* denies are policy, not OS-enforced (ADR-004, Alternatives considered, "Relabel `network-egress` as natively enforced…": the allowlist is not a security boundary). So never use the script-wrap mechanic to run mutations the model gates; those go through the validated capability scripts, which the hook sees and the model checks.

When a diagnostic recurs, it graduates from a workspace throwaway into a committed project command (or a `pkit` subcommand for repo-agnostic ones) per the core rule's COR-007 extraction.

### The agent workspace

The harness-neutral contract is the permissions README's (*The agent workspace*: one `.agent-workspace/` per checkout, excluded from git, granted to every agent for the file tools, a prompt there a defect); this is its Claude Code realization. In short: **no allow rule is needed, and the adapter emits none.**

**What Claude Code already approves inside its working directory.** The working directory is the project root for the main session and the worktree root for a subagent working in a worktree — and every checkout's `.agent-workspace/` sits at that root. Inside it, the harness's own permission modes approve the work: `Read`, `Grep` and `Glob` never prompt; file edits (`Write`, `Edit`, `NotebookEdit`) are approved once the operator accepts edits for the session — the accept-edits mode, or the session-wide approval the first edit prompt offers; and with the sandbox on, `autoAllowBashIfSandboxed` runs a sandboxed command without a prompt, the working directory being inside the sandbox's default write set. So `settings/core/settings.json` carries nothing for the folder, and `pkit permissions apply` writes nothing: the projection reports the `workspace` grant as `runtime` (and `permission-enforcement.yaml` declares `path-scoped-allow` as hook-enforced — not a confinement boundary; shell reach is `filesystem-confinement`; the file tools run outside the sandbox, so the recogniser's precision is the gate, the sandbox's), because a session-wide `Write` or `Edit` rule would reach far beyond the folder.

**What the hook adds.** With enforcement on (`pkit permissions enable`) and a shipped profile active, the hook allows the file tools — `Read`, `Write`, `Edit`, `MultiEdit`, `NotebookEdit` — on a target in the folder, in any permission mode, the default one included, where an edit would otherwise ask. Outside the folder the grant has no opinion and the harness's normal flow applies. A shell command is never the workspace's: a here-document or redirect into the folder (`cat > .agent-workspace/body.md <<'EOF'`) is judged like any other shell write and may still prompt — write the file with `Write` instead. With enforcement off, only the harness's own approvals above hold.

**Outside the working directory, none of this holds.** The per-session scratch directory the harness itself offers (its system prompt names one) lies outside a subagent's working directory — a worktree ten levels deep reaches it as `../../../../../../../../../../private/tmp/claude-…` — and absolute `Write` / `Edit` / `Read` allow rules for it in the machine-local settings did not stop the prompts ([#1043](https://github.com/aleskalfas/project-kit/issues/1043)'s field note). The workspace rule in `rules/core.md` takes precedence over that suggestion: intermediate files go in `.agent-workspace/`.

### `permission-enforcement.yaml`

The per-adapter enforcement-capability declaration (per COR-028): which dimensions of the permission model this harness realizes natively, via the hook (runtime, fail-open), or not at all (reported for the OS/container layer). `pkit permissions diff` reads it to label declared intent the harness cannot faithfully enforce.

## How adopters use this adapter

The install/sync runtime (`pkit init` / `pkit sync`) automates all adapter primitives, invoking them in order. When running manually, the steps are:

1. **Permissions.** Hand-merge `settings/core/settings.json` + `settings/project/settings.json` into your project's `.claude/settings.json`. Per COR-002's merge contract: append-only for adopter content, baseline-enforce for safety denies, idempotent. Or just run `merge-settings.sh`.
2. **Rules include.** Run `.pkit/adapters/claude-code/merge-claude-md.sh`. Ensures the root `CLAUDE.md` includes `@.pkit/rules/core.md` so the kit-shipped hard rules and tool-hygiene conventions load into the agent. Idempotent; never clobbers adopter content.
3. **Skills.** Run `.pkit/adapters/claude-code/deploy-skills.sh`. Creates the `.claude/skills/` symlinks (tracked in git per the project's `.gitignore`, so a fresh clone has the same environment).
4. **Agents.** Run `.pkit/adapters/claude-code/deploy-agents.sh`.
5. **Undeploy one capability.** Not a setup step: `pkit capabilities uninstall` runs `.pkit/adapters/claude-code/undeploy-capability.sh <name>` where the capability's files stay. Running it by hand is safe, but a capability still registered is deployed again by the next sync.
6. **Permission enforcement (opt-in).** Run `pkit permissions enable` to register the PreToolUse hook; `pkit permissions disable` to remove it. See *Live permission enforcement* above.

### What the merge keeps under `permissions`

The merge keeps every key under `permissions`. It reads three files: the baseline `settings/core/settings.json`, the project's additions `settings/project/settings.json`, and the existing `.claude/settings.json`. Each key merges in one of two ways.

- **Unioned.** `allow`, `deny`, `ask` and `additionalDirectories` hold the entries of all three files, each entry once. `allow` also gets a `Skill(<name>)` grant for every deployed skill. `allow` and `deny` are always written. `ask` and `additionalDirectories` are written only when one of the three files has them.
- **One value wins.** Every other key, such as `defaultMode`, keeps one value. The additions win over the baseline. The existing `.claude/settings.json` wins over both. This is the same precedence top-level keys have.

A union only adds. Taking an entry out of the additions leaves it in `.claude/settings.json`, so remove it there too. An entry the baseline ships, such as a safety deny, comes back on the next merge if you remove it.

A key that keeps one value behaves the same way once `.claude/settings.json` has it. Changing it in the additions, or taking it out, does not reach the file. Change or remove it in `.claude/settings.json` too.

Two cases stay as they were. A capability overlay cannot set any key under `permissions`: the merge drops an overlay's `permissions` before it runs ([project-management:DEC-030]). In managed ownership mode, a supplied projection (`$PKIT_MANAGED_REGION_FILE`) replaces `permissions` whole, and none of the keys above survives it (ADR-002).

### Git footprint (per ADR-009)

This adapter declares its out-of-`.pkit/` deploys as a `footprint:` list in its `package.yaml` (`.claude/skills`, `.claude/agents`, `CLAUDE.md`). `pkit visibility private` aggregates that with the backbone's `.pkit/` and routes the whole set into the per-clone `.git/info/exclude` — so a developer can run pkit on a repo whose team hasn't adopted it, with no committed trace. `pkit visibility shared` (the default, and what project-kit itself uses) keeps the deploys committed so a fresh clone shares the environment.

## Project-kit's own use

project-kit self-hosts: it's the first adopter of its own kit. The `.claude/settings.json` at the repo root, the symlinks under `.claude/skills/` and the agent copies under `.claude/agents/` are deployed by `pkit sync`, which on self-host runs the steps above instead of propagating (the CLI reference, `sync`).

## Codex / other harnesses

A separate adapter under `.pkit/adapters/<harness-name>/` would carry equivalent translations for that harness — potentially different file formats, different deployment paths, different scripts. The kit's own content (skills, agents, decisions, workflow) is portable across harnesses; only this adapter layer is harness-specific.
