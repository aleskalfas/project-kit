---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-07-02
---

# Agent dispatch privilege model — govern subagent spawning by an authored per-agent allowlist, not a posture ceiling

## The question

How should the permission model govern **subagent dispatch** — the harness `Agent` / `Task` tool one agent uses to spawn another? Specifically: which agents may spawn which, what posture does the spawned agent run under, and how is escalation-by-spawn prevented without blocking legitimate delegation?

## What surfaced it

An adopter observation, recorded in a **different repo** — `trip-planner-agent-data`'s `.pkit/scratchpad/active/2026-07-02-agent-dispatch-permission-gap.md`. There, under the `autonomous` posture, the last remaining operator prompt for an otherwise-native flow was `Agent (1×)` — the `project-manager` spawning a translator subagent. The durable fix does **not** live in that adopter repo: the permission catalog and the `claude-code` adapter are project-kit-owned, so the design belongs here. This note is the upstream crystallisation of that observation.

## The gap (what is known)

- **Dispatch prompts even in the autonomous posture, while more consequential tools do not.** `Edit`, `Write`, `MultiEdit` (which mutate the filesystem) are auto-approved; `Agent` (which, for a read-only reviewer, mutates nothing) prompts. That is backwards on a risk basis and is the immediate itch.
- **The catalog models CLI/Bash privileges, not harness tools.** The ~13 privileges are shell-oriented (`recognize.bash` matchers for git, gh, pkit, …). The first-class harness tools — `Edit`, `Write`, `MultiEdit`, `Grep`, `Skill(...)`, `Agent` — live *outside* the catalog as raw `permissions.allow` entries in `.claude/settings.json`. `Read` is the lone exception (mapped to `repo-read`).
- **`Agent`/`Task` is doubly uncovered** — not a Bash command (no catalog matcher) and not in the direct-allow baseline. So `permissions diagnose` classifies it "genuinely-missing".
- **It is not one of the guardrails.** The real guardrails are `destructive-fs`, `privilege-escalation`, `vcs-history-rewrite`. Dispatch — especially of a read-only reviewer — is core orchestration for autonomous multi-agent work, not a safety boundary in itself.

## The resolved design

Three decisions, reached by working the examples below.

### D1 — Non-inheritance: a spawned subagent runs under its OWN defined posture, not the parent's

The child does not inherit the parent's posture; it comes up under whatever its own definition specifies. This is *desirable*, and two cases prove it necessary:

- An **autonomous orchestrator** wants to spawn deliberately-**weaker** read-only reviewers (`critic`, `architect`, `methodology-reviewer`). Pure inheritance would wrongly force those reviewers to the parent's autonomous level.
- A **role-limited orchestrator** — `project-manager`, which must *not* write code — wants to spawn a **more-capable** worker (`software-engineer`, which can). Pure inheritance would forbid the very delegation that is the point of the role split.

So the child's posture must be free to differ from the parent's in *either* direction.

### D2 — `agent-dispatch` is a MODELED catalog privilege (not a raw settings.json allow)

Because D1 makes dispatch a privilege-affecting action, the model has to *see and reason about it* — `permissions explain` / `diff` must show who may spawn whom. A raw `settings.json` allow is invisible to that introspection, so it is the wrong home. Modelling `agent-dispatch` implies the catalog **learns to recognise harness tools**, not just `recognize.bash` commands — a small extension to the catalog's matcher model. That decision governs `Edit` / `Write` / `Skill` too (today all unmodeled); rolling their modelling out incrementally is fine, but the *framework* answer is "yes, the catalog models tools."

### D3 — The escalation control is a PER-AGENT DISPATCH ALLOWLIST, not a posture ceiling

The tempting control — "a spawned agent's posture ≤ its spawner's" — is **wrong**, because it conflates two different reasons an agent is constrained:

- **Trust-limited.** Read-only *because we do not trust it* (untrusted input, injection risk). Here, spawning-something-more-powerful *is* escalation.
- **Role-limited.** Can't write code *because that is not its job* (separation of duties). The agent is fully trusted; it just shouldn't be the one touching code. Here, spawning a code-writer is legitimate delegation.

A single posture-ceiling rule cannot tell these apart — it blocks both, killing the `project-manager → software-engineer` case. The right control is instead an **explicit, human-authored, per-agent allowlist**: *agent X may spawn agent types {A, B, C}*. Then:

- `project-manager` carries `may-dispatch: {software-engineer, critic, architect, qa-engineer, …}`. It can't write code itself, but `software-engineer` is on its list → it spawns one, which runs under *its own* code-writing posture. ✅ legitimate delegation.
- An **injected auditor** carries `may-dispatch: {}` (or only read-only reviewers). It tries to spawn a destructive autonomous helper → not on its list → refused. ✅ escalation blocked.

The security boundary thus moves from *"how powerful is the parent"* to *"what has a human explicitly authorised this agent to spawn."* That is curated and auditable; an untrusted agent simply carries a narrow or empty allowlist and cannot manufacture privilege regardless of its own posture.

**Recursion falls out of the same graph.** Whether a spawned agent may spawn *further* is just whether *its* definition carries a dispatch allowlist. A `software-engineer` with an empty one is a leaf — recursion is bounded by the **allowlist graph**, not a numeric depth cap and not a prompt.

**Two-lines-of-defence corollary (why pm→engineer is safe but auditor→rm is not).** Delegated code work is also **gated downstream** — the engineer's output goes through review + the merge gate before it lands. The injected-auditor attack (spawn a helper to `rm ci/secrets.env`) is **direct and irreversible**. So `pm → engineer` is safe on *two* counts (authorised *and* gated), while `auditor → rm` fails *both* — it is neither on an authored allowlist nor downstream-gated. The allowlist is the primary control; the downstream gate is the reason legitimate delegation carries little residual risk.

## Candidate realisation

- Model `agent-dispatch` in the permission catalog, parameterised by the per-agent spawnable-type allowlist (D2 + D3).
- Seed the `claude-code` adapter so `Agent` is covered (today it is a raw-allow gap).
- Auto-allow **top-level** dispatch under the `autonomous` posture — this kills the benign reviewer-dispatch prompt the trip-planner note started from — while recursion stays governed by the allowlist graph.

## Open questions

- **Do the OTHER harness tools get modelled too** (`Edit` / `Write` / `Skill`), so `permissions explain` / `diff` stop reporting them as unmodeled? D2 says the framework answer is yes; the rollout order and whether `Read`'s existing `repo-read` mapping is the template are open.
- **The exact schema for a per-agent dispatch allowlist.** Where does `may-dispatch` live — the agent's own frontmatter (per COR-013 agent shape), a catalog grant, or both? How does it compose with profiles/postures?
- **Platform reality.** Claude Code often gates *subagent-spawns-subagent* at the platform level already, so **parent-mode dispatch is the realistic case**. The model should codify "top-level dispatch allowed, recursion gated" in a way that aligns with (rather than fights) that platform behaviour — and degrade gracefully where the platform blocks recursion regardless.

## Next / crystallisation

Crystallises into: a **permission-capability decision** (the `agent-dispatch` privilege + the allowlist-not-ceiling control), an **ADR** on the catalog modelling harness tools generally (the D2 framework decision, since it governs `Edit`/`Write`/`Skill` and is architecturally load-bearing), and a **`claude-code` adapter change** seeding the coverage. Workstream: `permissions`.
