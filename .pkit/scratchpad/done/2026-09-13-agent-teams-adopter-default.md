---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-09-13
retired: 2026-09-21
produced:
  - COR-047
  - DEC-029
---

# Agent teams adopter default

> **Spike resolved 2026-09-13 (next session).** The gating verification spike **passed** — see below. The design is unblocked; next step is `critic` → `architect` on the *mechanism choice*, which the spike's side-findings have re-weighted.

## ✅ Spike result — CONFIRMED (teams-off restores the subagent path)

Ran at the start of the following session in this repo, with `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=0` live in the session's process env (confirmed via `env`), i.e. the interim `.claude/settings.local.json` guard took effect at session start as predicted.

**Method.** Spawned `critic` (a named reviewer type) on a small self-contained prompt; observed the return path.

**Observed.** The spawn launched on the ordinary **async-subagent** path and returned a `task-notification` with `status: completed` carrying the **full result inline** plus usage stats. **No `SendMessage` was required to receive the result.** No truncated teammate `idle_notification`, no "ask … via SendMessage" tail. Matches the documented teams-off behaviour exactly.

**Do not conflate:** the launch metadata *does* still advertise `SendMessage` for *resuming* the finished subagent. That is ordinary async-subagent resumability, not teammate promotion. The discriminator is whether the result **arrives on its own**; it did.

### Side-finding (stronger than expected): teams-off withholds the promotion knob entirely

With teams off, the `Agent` tool schema exposes **no `name` parameter at all** — only `description` / `prompt` / `subagent_type` / `model` / `isolation`. Teammate naming is **not expressible**. So under teams-off, "named spawn" collapses to `subagent_type` (a *type selector*, not a teammate name), and the docs' "launches as a subagent again" is realized by the promotion parameter simply being **withheld**.

This matters for the mechanism choice:

- The **incoherent middle state is structurally unreachable** with teams off — it is not a convention a dispatching agent must remember. That is a real argument for a config mechanism over a behavioural one.
- Correspondingly it **further weakens (A)**: there is nothing for an agent to remember, because the knob is gone.
- It does **not** touch (B)'s fragility — that objection is about flag stability and adopter override, not about payoff.

## The question

How should pkit handle Claude Code's **agent-teams** feature so a lead agent's spawned reviewers/helpers are always **drivable** — and what, if anything, should pkit ship as an **adopter default** (vs. leave to the adopter)?

## What's established

From a `claude-code-guide` consult of `sub-agents.md` / `agent-teams.md` / `cross-session-messaging.md`, plus this session's direct observations:

- **Teammate promotion is an AND:** a spawn becomes a persistent teammate only with a `name` **and** `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`. Drop either → fire-once subagent.
- **`SendMessage`** is auto-added to in-process teammates; the `project-manager` agent's tool grant **lacks** it. So under teams-on, a *named* spawn becomes an **undriveable teammate**. Observed: named `critic`/`architect` came back as truncated teammate `idle_notification`s; an **anonymous** docs-consult came back clean via the subagent path.
  - **Quantified from the originating transcript (session `46de3249`, 2026-09-12) — see "Transcript forensics" below.** The break is real and measurable: teammate results are **hard-truncated at 4064 characters**, ending in the literal marker `[result truncated — ask the agent for the rest via SendMessage]`. Three teammates (`critic-caps-docs`, `critic-caps-docs-2`, `arch-caps-docs`) each hit exactly that cap. Substantive reviews run 8–12 KB, so **more than half of a review is silently lost** — and the loss is *plausible-looking*, because the surviving prefix reads as a complete opening.
- With teams **off**, named subagents "launch as subagents again" — addressable-by-name, not persistent teammates; both anonymous and named subagent spawning keep working.
- **The real defect is the incoherent middle state:** teams *enabled* while the lead has *no* `SendMessage`. Two coherent states both make naming safe — **(a)** teams off → fire-once named subagents (matches pkit's dispatch pattern); **(b)** teams on + lead has `SendMessage` → drivable teammates. **Anonymous dispatch only bypasses the middle; it is not a fix.**

## Candidate mechanisms (enumerate, don't decide)

- **(A) Behavioral** — pkit's dispatching agents spawn reviewers *anonymously* (no `name`). A bypass; defense-in-depth at best. Fragile (relies on agents remembering), and gives up addressability.
- **(B) Config default** — ship `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=0` in the claude-code adapter baseline (`.pkit/adapters/claude-code/settings/core/settings.json`) so it flows to adopters' `.claude/settings.json`. Caveats:
  - overrides an adopter who **deliberately enabled** teams (project-level would win over their user-global opt-in, in every pkit project);
  - ~~the adapter's top-level non-`permissions` merge is whole-key last-write-wins, so any adopter `env` block knocks the default out~~ — **corrected by the spike session:** `merge-settings.sh` reduces sources with jq's `*`, which is a **recursive** merge (deep-merge for nested objects; last-write-wins only for scalars and arrays). An adopter `env` block carrying unrelated keys therefore does **not** knock out a baseline `env` key. The real constraint is different: source order is core → project → **target**, so an existing `.claude/settings.json` value wins over the baseline. Net effect: a baseline `=0` lands on **first install only**, and is thereafter **un-revisable** for any adopter who has set the key themselves — so the guarantee is not fragile-by-clobber, it is *one-shot*;
  - rides an `EXPERIMENTAL_` flag that may be renamed/removed.
- **(A + B)** — both.

**Open fact — RESOLVED by the spike session:** agent-teams is **opt-in, not on-by-default**. This machine's `~/.claude/settings.json` `env` block carries `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` — a deliberate **user-global** opt-in, which is why teams was on in the originating session. Two consequences, both pointing the same way:

- Since Claude Code resolves project settings **over** user settings, a baseline `=0` would override precisely the adopters who *chose* teams — in every pkit project, silently, including this repo's own maintainer.
- The adapter baseline (`.pkit/adapters/claude-code/settings/core/settings.json`) currently carries **only** a `permissions` key — **no `env` block at all**. (B) would introduce the first one, i.e. open a new baseline surface for a vendor-experimental flag.

This is the argument the note anticipated against forcing B, and it now has facts behind it: **lean documented-opt-in over baseline override.**

**Independent `critic` objections** (raised unprompted during the spike, against the claim that a baseline `=0` is a safe default):

1. **An `EXPERIMENTAL_`-named vendor flag is not a stable surface for a framework baseline.** The vendor may rename it, invert its default, or make `0` a no-op with no deprecation obligation. Pinning it framework-side propagates a silent dependency to every adopter; when it stops meaning what we assume, behaviour reverts everywhere at once with **no signal**. A framework default should encode an invariant we own, not a bet on someone else's knob.
2. **"Restores fire-once" is validated only on the confirming case.** Untraced: unnamed spawns, nested spawns, resumed sessions, and adopters who *want* team behaviour and must now fight a framework-imposed `0` the no-shared-files invariant makes awkward to override.

## Transcript forensics — R1 resolved, the note's causal claim CONFIRMED

`critic` (2026-09-13) hypothesised that the originating session was the **main session** (which under teams-on holds the full tool set including `SendMessage`), which would have refuted the note's causal chain. **Checked against the transcript; the hypothesis is wrong.**

Session `46de3249-0d0a-4ed3-838d-ec681761adab` (project-kit, 2026-09-12):

- `agentSetting: "project-manager"`, `isSidechain: false` — the lead **was** `project-manager` booted top-level, not the main session, and not a subagent.
- The spawns were **explicitly named**: `critic-caps-docs`, `critic-caps-docs-2`, `arch-caps-docs` — confirming teammate promotion via the `name` parameter.
- Every teammate `result` payload is **exactly 4064 chars**, terminated by `[result truncated — ask the agent for the rest via SendMessage]`.
- One teammate self-reported the other half of the defect: *"SendMessage isn't available in this session, so the team lead reads my final output directly."* — so **neither** side held the tool.

**Conclusion:** line 40's attribution stands, and the defect is more severe than the note claimed — not "undriveable", but **silently lossy at a 4 KB cap**, with the harness itself naming `SendMessage` as the only recovery path.

## Docs facts (verified 2026-09-13 via `claude-code-guide`)

Confirmed:

- **Teams is experimental and disabled by default** — verbatim from `agent-teams.md`. So the flag is a **no-op for the default adopter population** and load-bearing only for those who opted in.
- **Precedence** (`settings.md`): managed > CLI > **local project `settings.local.json`** > **shared project `settings.json`** > user global. So project-scope beats user-global; and `settings.local.json` beats project-scope.
- **No deprecation path or non-experimental successor** is documented for the flag. Still `EXPERIMENTAL_` as of v2.1.178.

Unspecified — **docs don't say** (four consecutive gaps, all load-bearing for the dropped hardening below):

- whether `SendMessage` is a valid *explicit* entry in a `tools:` list (no example exists; it is described as **injected** by the harness for in-process teammates, never user-declared);
- how a **lead** acquires it;
- what granting it does when teams is **off**;
- whether a lead can complete a send-and-receive round-trip **without a human in the loop**.

The guide's own recommendation: **leave `SendMessage` out of explicit tool lists.**

## Hardening considered and DROPPED: grant `SendMessage` to the dispatcher

Proposed mid-session as "defense-in-depth" (flag honoured → fire-once works; flag broken → teams on but lead can drive). **Dropped.** Reasons, in order of force:

1. **Rests on four documented unknowns** (above). Shipping it to third-party adopters would be a guarantee built on unverified behaviour — the same defect as trusting the bare flag, one layer down.
2. **Not independent, so not defense-in-depth.** `SendMessage` is a tool of the *same* vendor-experimental feature as the flag. The hedged scenario ("vendor churns agent-teams surface") is exactly the scenario in which the tool name is also at risk. pkit owns the *file* containing the string, not the *name's meaning*.
3. **A tool with no procedure, contradicting the contract leg 1 enforces.** No skill procedure (COR-006), no storyboard scenario (COR-016), no completion detection, no timeout, no failure semantics. It would trade a **loud** failure for a **quiet** one: a lead improvising a message loop with no termination condition. That manufactures a *new* incoherent middle — tool present, procedure absent.
4. **Wrong population.** `project-manager` is the **only** agent in the kit granting the `Agent` tool (verified: `critic`, `architect`, `methodology-reviewer`, `convention-compliance-reviewer`, `process-author` all lack it). So the grant reaches exactly one lead — and the main session, which also dispatches reviewers per `CLAUDE.md`'s reviewer table, **has no agent file to harden**.

## ⛔ BLOCKING FINDING — collides with accepted ADR-032

[ADR-032](../../../docs/architecture/decisions/ADR-032-per-machine-activation-routing-axis.md) (`status: accepted`) already governs *where a harness settings key lives*, and mechanism (B) violates its **Rule B, defer branch** head-on:

> **Harness-co-owned key (the defer branch) → the harness's own local file; pkit defers.** When the harness already owns and writes a per-machine key, the entry lands where the harness writes it, and **pkit never authors a parallel key**. This is the split-brain fix: pkit writing its own copy of a harness-owned toggle is exactly what produced the believed-off-but-actually-on disable bug.

The `sandbox.enabled` worked instance is **structurally identical**: operator activation (Rule A) + harness-co-owned (Rule B defer) → pkit *retired* its parallel committed key. (B) would re-create precisely that shape for teams: pkit writes `=0` in the committed floor while the operator's user-global writes `=1` and a gitignored `settings.local.json` may write either — three writers, one toggle, effective value decided by a precedence chain **`merge-settings.sh` cannot observe** (it sources only `.claude/settings.json`; the local file is gitignored and never enters the chain).

**Already true in this repo:** the interim guard sits in `.claude/settings.local.json` — the *higher-precedence* file. Ship (B) and this repo's effective value still comes from the gitignored file, not from the thing shipped. The validation environment would not be testing the shipped mechanism.

**Two legitimate doors** (the proposal must take one, explicitly):

- **(a) Argue the portable-floor classification.** Rule A's test: *per-operator state whose correct value varies by who is at the machine* routes local; its complement — **identical for every operator everywhere** — commits. The available argument: "teams off" is not operator taste but a **project dispatch requirement**, operator-invariant. This argument is plausible and must be *made in the record* against Rule A's test, not assumed.
- **(b) Discharge ADR-032's deferred enforcement-policy layer.** ADR-032 explicitly defers "a committable *this project requires X*, distinct from operator activation — **deferred, not rejected** per COR-007: build it when a team concretely needs to mandate it." **This matches the owner's stated intent exactly** ("pkit needs to guarantee that it will work as designed" is an enforcement requirement, not an operator activation), and the sandbox is the first consumer while this is the **second** — so COR-007's recurrence test is **met** and the deferral is discharge-able. Carrier: a committed pkit-side *requirement* that the per-machine activation must satisfy, with mismatch **surfaced**, rather than a raw vendor key smuggled into the merged baseline.

## Corrections to earlier reasoning in this note

- **A value-rewriting migration is NOT required and would be harmful.** Adding a baseline key is a *pure addition* under COR-010 (no rename/removal, no `schema_version` bump, no CLI signature change); `pkit sync`'s deep-merge **is** the propagation for every adopter who hasn't set the key. The only population needing anything is those who set `=1` — and silently rewriting their value during an upgrade is exactly the confiscation to avoid. What's missing is **observability**, not a migration: a `pkit status` / doctor check reporting the **resolved effective** state across all reachable layers. Key it on the **observable capability** (does the `Agent` tool expose `name`?) rather than the flag name, so it survives a vendor rename.
- **Overriding is easy, not hard — the problem is that it is silent.** The earlier carried-forward objection ("adopters must fight a framework-imposed `0` the no-shared-files invariant makes awkward to override") is **wrong**. `merge-settings.sh` orders sources core → project → overlays → target, so a one-key `env` addition in `.pkit/adapters/claude-code/settings/project/settings.json` beats the baseline — the invariant-sanctioned extension path. Per-operator override via `settings.local.json` (precedence level 3) also beats it, and pkit never writes that file (gitignored, verified).
- **The spike's side-finding *rehabilitates* (A) rather than weakening it.** Under teams-off the `name` parameter is **absent from the tool schema** — nothing to remember. Under teams-on an agent can **observe** whether its own `Agent` tool exposes `name` and behave accordingly. That is a **capability check, not a memory check**, and it is immune to flag renames in *both* directions — the exact property the dropped hardening could not deliver. The note's "(A) is fragile, relies on agents remembering" is therefore mis-stated.
- **`(A) gives up addressability` is priced at zero.** No pkit agent uses `name` today; no pkit procedure requires it; the reviewer stack is fire-once by construction. Either name a concrete pkit use case or drop the objection.
- **`env` propagates to every child process**, not just the session — inherited by every `Bash` invocation, every `.pkit/**/*.sh`, every nested `claude -p`, and CI. (B)'s blast radius is wider than "dispatch behaviour", and it would be the **first `env` key** in a baseline that currently carries only `permissions`. The precedent matters more than the key.
- **Changesets:** two components, two tiers — the claude-code adapter (baseline) and project-management (DEC-029 amendment) each need their own `.changes/unreleased/` entry per PRJ-002. For an adopter who deliberately opted into teams, a baseline flip changes every session's runtime behaviour — that reads heavier than `patch`.
- **Do not ship the word "guarantee."** With three silent override paths above pkit's one writable layer, it misleads. State the resolution order and what pkit actually controls.

## Still unexplored (the spike is one confirming instance)

Nested spawns at depth 2–3; `--resume` of a session created under teams-on (pre-existing teammates in the transcript); `claude -p` non-interactive; the `/agents` team UI under `=0`; adopters whose own agents deliberately use names; whether a *subagent* `project-manager` can promote teammates at all (couples to the DEC-029 nesting-premise fix). One named spawn, one session, one machine, one CLI version is good evidence the mechanism works and **no** evidence about where it stops working.

## Adjacent, do-not-conflate

- **DEC-029 nesting-premise correction:** current docs say subagents **can** nest up to 3 layers (`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`, default 3), contradicting DEC-029's "subagents cannot spawn subagents." This is context the DEC-029 amendment (below) must fold in — but it is a **different axis** (nesting) than teammate promotion.
- The **recursion/escalation-gating** design (whether pkit should set `MAX_SUBAGENT_SPAWN_DEPTH`) belongs to the `2026-07-02-agent-dispatch-privilege-model` note's "top-level dispatch allowed, recursion gated" question — its own decision, not this one.

## Retires by producing

*(Updated 2026-09-13: the baseline-change half is now gated on the ADR-032 door choice above; an **ADR-032-derived record** — either the portable-floor classification or the discharged enforcement-policy layer — is the likelier carrier than a raw baseline edit.)*

A **DEC-029 amendment** (revisit parent-mode-only against current docs; state the dispatch/naming discipline) and **possibly** a claude-code adapter baseline change — or being dropped. Cross-refs: [project-management:DEC-029-project-manager-agent-shape]; `2026-07-02-agent-dispatch-privilege-model` (shared `MAX_SUBAGENT_SPAWN_DEPTH` touchpoint); the interim `.claude/settings.local.json` toggle applied in this repo.
