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
        - .pkit/adapters/claude-code/permission-enforcement.yaml
        - src/project_kit/visibility.py
      record: [COR-002, COR-005, COR-028, ADR-002, ADR-004, ADR-009, ADR-014, ADR-052, ADR-060, "project-management:DEC-030"]
    revalidated:
      at: 2026-09-29T17:31:43Z
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
├── _resolve_agent.py                  # resolves one agent: overlay placeholders, model and effort, storyboard paths
├── permission-enforcement.yaml        # which permission dimensions this harness realizes, and via which layer
└── permission-hook.py                 # the PreToolUse enforcement hook (registered by `pkit permissions enable`)
```

### `settings/`

The kit's permissions story for Claude Code — what allows and denies are pre-configured in adopters' `.claude/settings.json`. Two halves per the universal area pattern (COR-005):

- **`core/settings.json`** — kit baseline. Universal allows (`gh`, `git`, `ssh`, common UNIX tools, kit-shipped script execution, agent-tool allows, `Skill(update-config)`) and universal safety denies (`git push --force` variants, `git reset --hard`, `rm -rf` family, `sudo`). The discriminator is "would every project-kit adopter benefit?"
- **`project/settings.json`** — adopter's project-specific additions on top of the baseline (language tooling, enterprise hosts, project-specific paths). Adopters typically add allows here; denies stay in the kit baseline.

The file Claude Code actually reads is the adopter's `.claude/settings.json`, merged from these two by `merge-settings.sh`, which `pkit init`, `pkit sync` and `pkit merge` run (COR-002 / COR-004). See **How adopters use this adapter** below.

Top-level keys outside `permissions` (e.g. `agent`, `model`) in either `core/settings.json` or `project/settings.json` flow through to `.claude/settings.json` with last-write-wins precedence (project overrides core; an existing adopter entry overrides both). Permissions keep their existing union-deduped semantics.

**Ownership modes (COR-002 authoritative-region tier).** By default (`ownership_mode: additive`) the merge is append/union/baseline-enforce — it only ever *adds* to `permissions` and re-asserts the safety denies, never removing adopter entries. Under `ownership_mode: managed` (set via `pkit permissions mode managed`), the realizer **owns the `permissions` region** and regenerates it **wholesale** from its model projection: the merge replaces `.permissions` with the projection supplied per-run (via `$PKIT_MANAGED_REGION_FILE`, written by `pkit permissions apply`) instead of unioning it, so a grant removed from the model vanishes (drift heals down to empty) — everything *outside* `.permissions` stays byte-for-byte adopter-owned. This needs no in-file markers and no strip-logic: `permissions` is already stripped from every source and recomputed each run, so managed mode only swaps the *source* of that recompute. The owned region is the fixed realizer constant `.permissions` (the hook rides the separate top-level `hooks` key); the gate is the `ownership_mode` config flag, never file-presence, so a stray region file can't reactivate managed behaviour. Managed mode only replaces when a projection is actually supplied: a plain `pkit sync` in managed mode with no projection in hand falls through to the additive default (it never blanks the region). *(The `apply` realizer that generates the projection is a later increment; this section documents the merge-primitive tier it builds on.)*

**Capability-contributed overlays** (per [project-management:DEC-030]). Installed capabilities can ship per-harness overlay templates and adopter-toggled live overlays under `.pkit/capabilities/<cap>/adapters/claude-code/overlay.template.json` (core-owned) and `.pkit/capabilities/<cap>/project/adapter-overlays/claude-code.json` (adopter-owned). `merge-settings.sh` walks manifest-registered capabilities; each capability whose adopter-owned overlay file is *present* contributes its top-level keys into the merge chain between `project/settings.json` and the existing target. The opt-in flow is the capability's own `enable-*` / `disable-*` CLI subcommand pair; for project-management, see `pkit project-management enable-default-agent`. Overlay `permissions` keys are reserved — silently stripped at merge time so overlays cannot influence allow/deny.

### `merge-claude-md.sh`

Ensures the adopter's root `CLAUDE.md` loads the kit-shipped rules (`@.pkit/rules/core.md`) and project rules (`@.pkit/rules/project.md`) via Claude Code's `@<path>` include mechanism. Per the COR-002 merge contract (insert-if-absent / create-if-none posture):

- **No CLAUDE.md:** creates a minimal one with an H1 and the `@`-includes.
- **CLAUDE.md without the include:** inserts the `@`-include block after the first H1 (per core.md rule 13's authoring convention — included sections must nest under the host's heading, not appear at line 1). If no H1 is found, prepends a minimal header + includes above the existing content.
- **CLAUDE.md already has the include:** no-op (idempotent).

Adopter content is never clobbered. Both `@.pkit/rules/core.md` (kit-owned, refreshed on sync) and `@.pkit/rules/project.md` (adopter-owned, never overwritten) are wired together so their rules compose in the agent's context.

`merge-claude-md.sh` is an adapter primitive: `pkit init` and `pkit sync` invoke it (alongside `merge-settings.sh`, `deploy-skills.sh`, `deploy-agents.sh`) so the wiring is maintained automatically. Running it by hand is always safe.

### `deploy-skills.sh`

Walks `.pkit/skills/{core,project}/<name>/` and creates relative symlinks at `.claude/skills/<name>/` so Claude Code can discover and load the skills. Idempotent; safe to re-run; skips non-kit-managed content under `.claude/skills/`. Per COR-005's adapter pattern, this is the Claude-Code-specific deployment for the harness-agnostic skill content stored at `.pkit/skills/`.

A listed skill whose canonical file doesn't resolve — most commonly a composite skill folder mid-build (per COR-020): sub-procedures present but no `<name>/<name>.md` dispatcher yet — is **skipped loudly** (a `skipped` status line naming the skill and defect, plus a remediation hint), not treated as fatal. The rest of the skills deploy and the run exits 0 with an end-of-run summary. This is deliberate: one half-built incubated skill must never abort a whole-project `pkit sync`/`upgrade`. `deploy-agents.sh` applies the same degrade-loudly discipline to an agent folder with no canonical `<name>/<name>.md` (and to an overlay category left undefined in a **hard** channel — `owns`/`needs`/`answers`/`reads.paths`/`reads.records`; a category referenced *only* via `reads.patterns` is an optional read per [ADR-052](../../../tech-docs/architecture/decisions/ADR-052-optional-read-category-empty-tolerance.md), whose absence drops the item and still deploys the agent; a *bare* optional key — present with no value — deploys the same way but prints a `warning` status line naming it).

### `deploy-agents.sh`

Writes each kit-shipped agent as a **resolved copy** at `.claude/agents/<name>.md` — copies, not symlinks, because the source carries overlay placeholders the deploy substitutes (the agents README, "Deploy mechanics"). `_resolve_agent.py` resolves one agent: it substitutes the `<category>` placeholders from `.pkit/agents/project/overlay.yaml` and carries the agent's execution policy into the deployed front matter.

**Name collisions.** When more than one location ships an agent of one name, the project's is deployed, else an installed capability's (the first by capability name), else core's — a capability's agent is the discipline's specialisation of a core default ([COR-026](../../decisions/core/COR-026-agent-placement-by-discipline.md)). The agents README, "Name-collision precedence", states the rule and the collisions between capabilities.

**Model and effort** (#1047). Claude Code reads a `model:` and an `effort:` key from an agent definition's front matter (verified against Claude Code 2.1.283: `effort` takes `low`, `medium`, `high`, `xhigh`, `max`, or an integer; `model` takes `inherit`, an alias or a full model name). The resolver writes both under those names, taking each from the overlay's `overrides.<agent>.model` / `.effort` when set, else from the agent's front matter. It writes **nothing** for an absent or `inherit` value — so a shipped agent that sets neither deploys exactly as before, and the harness default applies: a dispatched agent inherits its caller's model and effort. A value outside the accepted set (the named effort levels only; the integer form is not part of the methodology's vocabulary) is not written: the agent still deploys, inherits, and the run prints a `warning` line naming the value. The accepted values, the precedence and the `pkit agents` report are specified in the agents README, "Model and effort".

**Precedence with `review-pr --effort`.** A run-time effort resolved by `review-pr` (the project-management capability's `--effort` flag, `PKIT_REVIEW_AGENT_EFFORT`, or `review.agents.effort`) wins over the agent's deployed `effort:` — a run-time knob over a declaration. `review-pr` realises it by passing the value as the reviewer session's `--effort`, the harness's session-level setting (the same shape by which a `--model` flag wins over an `--agent`'s `model:`). When `review-pr` resolves none it passes nothing, and the deployed value applies.

**Storyboard references** (#1101). An agent that drives scripted scenarios declares its storyboards (COR-016) in `storyboards:` and cites them in its body. The source names a storyboard by its bare sibling filename (`storyboard.md`), which stays right wherever the agent's folder lives — core, project or a capability. The deployed copy lives in `.claude/agents/`, where that name resolves to nothing, so the resolver rewrites each entry naming a file beside the source to the storyboard's project-root-relative source path, in the list and wherever the body cites the entry as a whole path; the runtime reads the storyboard from there with its `Read` tool. An entry already written as a source path deploys unchanged. The convention is stated in the agents README, "Frontmatter declaration" under "Storyboards".

### Live permission enforcement (`permission-hook.py`)

The realizer that makes declared permissions *bite* at runtime (per [COR-028](../../decisions/core/COR-028-permission-model-realization.md) / [ADR-002](../../../tech-docs/architecture/decisions/ADR-002-permission-realizer-ownership.md)). It's **opt-in** — see *enable / disable* below.

`permission-hook.py` runs under the **system `python3`** interpreter — no `uv`, no PEP-723 metadata, no third-party deps at startup. This is required so the hook starts inside macOS Seatbelt, where `uv` panics on a fixed `SCDynamicStore` denial (ADR-014). On each matched tool call Claude Code pipes a PreToolUse payload to its stdin; the hook builds the model through the shared, harness-neutral decision core (`.pkit/permissions/decide.py`) and either prints a `permissionDecision` (`allow` / `deny`) or **abstains** (exit 0, no stdout → the harness's normal permission flow proceeds). It imports the *same* `decide.load_model` + `decide.decide` the `pkit permissions` CLI uses, so the hook and the CLI can never decide differently (ADR-002's same-code invariant).

**Zero-dep shebang + stdlib YAML fallback.** The hook's shebang is `#!/usr/bin/env python3` (bare, no `uv`). The shared loader in `decide.py` (`load_yaml`) tries `ruamel.yaml` when available and falls back to a stdlib-only YAML-subset parser when not — handling the full file subset (block mappings/sequences, single/double-quoted strings, flow sequences, block scalars, booleans). **The fallback lives in the shared `decide.py` loader, not in the hook**, so both the hook and the `pkit permissions` CLI parse via the same code path — the same-code invariant is mechanically preserved, not aspirational.

**The double-lock.** The non-negotiable guardrail denies — every privilege the catalog flags `guardrail: true` (currently `privilege-escalation`, `destructive-fs`, `vcs-history-rewrite`) — are enforced in two independent layers:

1. **fail-open hook half** — synthesized as `{subject: all, effect: deny}` grants in the model, derived from the privileges the catalog flags `guardrail: true` (the catalog is the single source of truth). The hook **fails open on decision faults** (malformed payload, ambiguous model): any such fault yields a silent abstain, never a silent block. Set `PKIT_PERMISSIONS_DEBUG=1` to surface decision fault reasons on stderr.
2. **fail-closed native half** — the catastrophic `deny` patterns in `settings/core/settings.json`. These hold even if the hook is absent, faults, or is version-skewed, so failing open in layer 1 can never bypass them.

**Enforcement-runtime fault taxonomy (ADR-002 amendment).** The fail-open contract covers *decision faults* (hook ran, couldn't resolve). A distinct class — *enforcement-runtime faults* — means the hook **cannot start at all** (python3 missing, decide.py absent, syntax error). This class is **fail-loud**, not fail-open: `pkit permissions enable` and `pkit permissions sandbox enable` run a startup self-check after registering the hook and warn loudly if the hook cannot start, so the operator learns enforcement is not running rather than believing a dead hook is gating calls. `pkit permissions overview` also surfaces this state when enforcement is registered-but-dead: it runs the self-check and reports "ENFORCEMENT-RUNTIME FAULT — hook CANNOT START" with the diagnosed reason.

**enable / disable** (the opt-in toggle, per issue #247's "Option B" — mirroring the [project-management:DEC-030] default-agent precedent). Because the hook fires per tool call, registering it is the adopter's explicit choice, not an install default:

```
pkit permissions enable
```

Registers the hook under the top-level `hooks.PreToolUse` key in `.claude/settings.json` (command `${CLAUDE_PROJECT_DIR}/.pkit/adapters/claude-code/permission-hook.py`, matcher `*`) and ensures the fail-closed native guardrail denies are present. Refuses if the claude-code adapter isn't installed. Idempotent.

After registering, runs the **enforcement-runtime self-check** (per the ADR-002 amendment): drives the hook script under `python3` with a probe payload to verify it can start. If the hook cannot start (python3 missing, decide.py absent, etc.), outputs a loud WARNING naming the fault and the remediation — rather than silently proceeding with a dead hook that fail-opens on every call.

```
pkit permissions disable
```

Strips *only* the pkit hook registration (matched by its command path), preserving any other adopter hooks, and leaves the native guardrail denies in place. The explicit strip is required because the merge primitive treats existing top-level settings keys as last-write-wins survivors — the DEC-030 strip-logic pattern. Idempotent; leaves no orphaned registration.

The hook **script** itself is a propagated adapter file — `pkit sync` owns its lifecycle, so `enable`/`disable` manage only its *registration*, never deploy or remove the file (there is no orphaned-script failure mode). The registration is written only to the live `.claude/settings.json`, never to a merge source, so it survives re-merge and is removable by strip (the `hooks` key lives outside any realizer-owned region per ADR-002).

**`pkit permissions sandbox enable`** sets `failIfUnavailable: true` always (the ADR-004 / ADR-014 §6 fail-closed invariant), so Claude Code refuses to start an unconfined session rather than silently running without a box. It also runs the enforcement-runtime self-check (same as `enable`) AND verifies **actual confinement** — attempts a write outside the workspace that Seatbelt/bubblewrap must deny. If the write succeeds, it warns "sandbox configured ON but NOT actually confining" loudly (box may not have initialized, or the session hasn't been restarted). `pkit permissions sandbox status` and `pkit permissions overview` report the same actual-confinement probe result so the operator never believes confinement is active when it is not.

### Prompt-free command shape under the sandbox

This is the Claude Code realization of the universal "work with the permission layer, not around it" rule (`.pkit/rules/core.md`). With the sandbox on, `.claude/settings.json` carries `sandbox.autoAllowBashIfSandboxed: true` — so a **single, simple Bash command auto-allows** because it runs inside the box, no prompt. What still prompts is the command *shape* the parser can't statically vet: a leading `cd`, statements chained with `;`, pipelines (`| grep | head`), and command substitution. Those fall back to a confirmation even under the sandbox, and an allow-list entry for the inner tool does not help (the parser keys on the outer/first token). So the agent's discipline is: **one clean command per call; the harness's `Read` / `Grep` / `Glob` / `Write` tools for inspection and file I/O — not `cat`/`sed`/heredocs/pipelines.**

For a genuinely multi-step diagnostic, compose the complexity into a file and run it as one invocation: author the script with the `Write` tool in the agent workspace (prompt-free, and the call shows its contents), then run a single `bash .agent-workspace/<file>`. The parser sees only that one clean command; the box auto-allows it; the multi-step logic runs *inside* the sandbox.

**Caveat — this is for read-only diagnostics only.** Wrapping commands in a script **bypasses the PreToolUse hook**: the hook inspects the outer `bash <file>` invocation, not the script's contents, so a gated mutation hidden inside a script (e.g. a raw `gh issue edit` the model denies) slips past the check. The OS sandbox still bounds the script at the OS level, but the hook's *intent* denies are policy, not OS-enforced (ADR-004 §61 — the allowlist is not a security boundary). So never use the script-wrap mechanic to run mutations the model gates; those go through the validated capability scripts, which the hook sees and the model checks.

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
5. **Permission enforcement (opt-in).** Run `pkit permissions enable` to register the PreToolUse hook; `pkit permissions disable` to remove it. See *Live permission enforcement* above.

### Git footprint (per ADR-009)

This adapter declares its out-of-`.pkit/` deploys as a `footprint:` list in its `package.yaml` (`.claude/skills`, `.claude/agents`, `CLAUDE.md`). `pkit visibility private` aggregates that with the backbone's `.pkit/` and routes the whole set into the per-clone `.git/info/exclude` — so a developer can run pkit on a repo whose team hasn't adopted it, with no committed trace. `pkit visibility shared` (the default, and what project-kit itself uses) keeps the deploys committed so a fresh clone shares the environment.

## Project-kit's own use

project-kit self-hosts: it's the first adopter of its own kit. The `.claude/settings.json` at the repo root, the symlinks under `.claude/skills/` and the agent copies under `.claude/agents/` are deployed by `pkit sync`, which on self-host runs the steps above instead of propagating (the CLI reference, `sync`).

## Codex / other harnesses

A separate adapter under `.pkit/adapters/<harness-name>/` would carry equivalent translations for that harness — potentially different file formats, different deployment paths, different scripts. The kit's own content (skills, agents, decisions, workflow) is portable across harnesses; only this adapter layer is harness-specific.
