---
id: COR-039
title: A session mutates its own repo's context; cross-repo mutation is operator-gated, never silent
status: accepted
date: 2026-06-30
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

*An agent session is rooted in one project's repo and carries that project's governance — its rules, conventions, deployed agents, permission model. This record fixes the principle that a session **mutates only the repo it is rooted in**: changing directory into, or redirecting a command at, a **different** project's repo and mutating it there is forbidden by default, because the second repo's governance never loads and the mutation runs under the wrong project's context. A genuinely-intended cross-repo mutation is a legitimate but **operator-gated** exception — surfaced and confirmed per change, never performed silently. Enforcement is layered and honest about its reach: the program that owns a mutation detects the context-mismatch and refuses-or-prompts; a discipline rule covers the paths no methodology code interposes on; and **no layer claims a boundary it does not actually hold**.*

## Context

A session is launched rooted in one repo, and everything that governs how work is done in that session — the loaded instructions, the operational rules, the project conventions, the deployed agents, the permission/confinement model — belongs to **that** repo. That context is what makes a mutation correct: a decision authored, an issue filed, a commit made, a state change applied is governed by the rules of the repo it lands in.

The failure mode this record closes: a session rooted in repo A can reach into a **different** project's repo B — by changing the working directory into B, or by redirecting a command at B — and *mutate* B from inside A's session. The mechanics succeed (the tools operate on whatever path they are pointed at), but B's own governance **never loads**. The mutation to B is performed under A's rules, A's conventions, A's agents, A's permission model — i.e. under the wrong project's context entirely. This is a governance-bypass at the session level: the session-scoped analogue of editing a file a repo does not own, one altitude up. (It occurred concretely: a session rooted in one repo filed issues, authored decisions, and committed into a separate adopter repo by changing directory into it — landing correct artifacts in the right place mechanically, but with none of that repo's context governing the work.)

Two prior structures bound the shape of any fix and must be honoured rather than re-litigated:

- **The realization layer cannot supply a hard mechanical boundary for this.** The intent/permission layer is defeated by directory-change and path-redirection (a command can always be pointed elsewhere); and on some platforms the very tools that perform these mutations run *outside* the confinement box by necessity, so a filesystem-confinement fence is **partial** there — and a partial boundary advertised as whole is the believed-but-absent-boundary trap ([COR-028](COR-028-permission-model-realization.md)'s honesty discipline forbids it). The honest mechanism is therefore an **interlock at the program that owns the mutation**, not a claimed wall — consistent with the advisory-not-gating posture of [COR-024](COR-024-critic-and-architect-agents.md).
- **Cross-repo mutation is a legitimate future shape, not something to forbid outright.** Coordinated work across a team's repos is a real, sanctioned pattern; the established stance for it is *detect-and-operator-gate*, never a blanket block — because cross-repo writes carry real blast radius and want a per-change human decision. A guardrail that *blocked* cross-repo mutation would forbid that pattern by construction. The right framing is therefore an **operator-gated exception**, the same per-change-human-gate shape, applied at mutation time.

## Decision

**A session's mutating context must match the repo it mutates.** By default, a session mutates only the repo it is rooted in. A cross-repo mutation — mutating a *different* project's repo from within this session — is a legitimate but **operator-gated** exception: it is surfaced to the operator and confirmed per change, and is **never** performed silently.

Three properties make this real and honest:

1. **Operator-gated, not blocked.** When a context-mismatch is detected, the default is to **refuse-with-explanation (under autonomy) or prompt the operator (interactively)** — not a hard deny. An operator who genuinely intends the cross-repo mutation confirms and proceeds. This preserves coordinated cross-repo work as a sanctioned, deliberate, per-change gesture rather than outlawing it.

2. **Enforced at the program that owns the mutation, where it can see both sides.** The honest place to detect the mismatch is the layer that *performs* the mutation and runs as itself — the methodology CLI and its capability scripts — because that layer holds both the session anchor (the repo the session is rooted in) and the mutation target (the repo about to be changed), and can compare them. This is the reliable lever precisely because the layers *around* it cannot carry the check: the intent layer is defeated by directory-change/redirection, and confinement is partial where the mutating tools run unconfined.

3. **Honest about reach — an interlock, not a security boundary.** The mechanism catches the realistic failure: an *accidental* cross-repo mutation performed through the methodology's own validated path while the session is misdirected. It does **not** claim to stop a determined bypass that routes around the methodology entirely (a raw tool invocation, or unsetting the session anchor). No layer advertises a boundary it does not hold ([COR-028](COR-028-permission-model-realization.md)). A discipline rule (the operational realization) carries the principle on the paths no methodology code interposes on — teaching where mechanism cannot reach.

The principle is harness-neutral and universal ([COR-014](COR-014-universal-applicability.md)); the *how* — the session-anchor signal, the detection point in the CLI, the per-platform confinement story — is realization detail recorded by the permission-model realization (an ADR) and the operational discipline (a rule), not here.

## Rationale

**Why operator-gated rather than blocked.** A blanket block would make legitimate coordinated cross-repo work illegal by construction. The blast-radius-aware stance for cross-repo writes is a per-change human gate; an operator-gated exception *is* that gate, applied at mutation time. Surfacing-and-confirming preserves the deliberate path while killing the silent one.

**Why the mutating program is the honest lever.** The program performing the mutation is the only layer that runs as itself and knows both the session's root and the mutation's target. The intent layer sees only a (defeasible) command string; the confinement layer is, on some platforms, not even in the path for the mutating tools. Putting the check where both facts are in hand avoids relying on a layer the platform has already shown cannot carry it.

**Why honest-about-reach, not a claimed wall.** A guardrail sold as a boundary it cannot hold is worse than none — the operator stops watching, trusting a wall that leaks. The platform genuinely cannot supply a hard mechanical wall for arbitrary cross-repo mutation (directory-change and path-redirection defeat command inspection; required tool-exclusions defeat confinement). The defensible artifact is an honest interlock against the *accidental-handoff* shape — the realistic mistake — paired with a discipline rule, with the residual gap declared, not hidden.

### Alternatives considered

- **Block cross-repo mutation outright.** Rejected — forbids the sanctioned coordinated-cross-repo pattern by construction; the right shape is an operator-gated exception (a per-change human gate), not a wall.
- **Enforce in the intent/permission layer (deny on a foreign-target command).** Rejected — command inspection is defeated by directory-change and path-redirection; a deny there is security theater (already an established rejected alternative for confinement claims at that layer).
- **Rely on filesystem confinement (a write-scope fence at the session root).** Rejected as the *general* lever — on platforms where the mutating tools run unconfined by necessity, the fence is partial for exactly the commands at issue, and a partial fence advertised as whole is the believed-but-absent-boundary trap. (Where a platform *does* confine the mutating tools, write-scoping is a legitimate per-platform reinforcement — a realization detail, not the principle.)
- **A discipline rule alone.** Rejected as *sufficient* — teaching without mechanism where mechanism is available is weaker than pairing the two; the rule is necessary (it reaches the non-methodology paths) but is backed by the interlock where the interlock can reach.

## Implications

- **Two realization carriers, named here, authored separately:** an **operational rule** (in the methodology's core rules) stating the handoff discipline — recognize when the session is directed at a foreign repo, route a genuine cross-repo mutation through the operator gate, never mutate silently — and a **permission-model realization record** (an ADR) recording *how* the principle is realized — the mismatch detection at the mutating program, the per-platform confinement stance (including why a write-scope fence is **not** introduced as a foreign-repo boundary where the mutating tools run unconfined), and the honest residual-gap declaration.
- **The mechanism extracts a recurring check, not a per-script reimplementation** ([COR-007](COR-007-pattern-extraction.md)): "is the repo I am about to mutate the one this session is rooted in?" is computed once at the mutation seam, not re-derived in every script.
- **Honesty discipline** ([COR-028](COR-028-permission-model-realization.md)) governs the realization: the interlock is reported as an interlock against accidental handoff, never as a security boundary; the residual gap (a determined bypass routing around the methodology) is stated, not papered over. The realization ADR therefore carries an operator sign-off gate, because it makes a load-bearing claim about what is *not* protected.
- **Surface change** ([COR-006](COR-006-artifact-roles.md) carrier discipline; the project's versioning policy): a new principle bumps the version. Implementation of the interlock does not begin until this record is `accepted` and the realization ADR is signed off.
- **Coordinated cross-repo work stays reachable.** The operator-gated framing is deliberately compatible with sanctioned cross-repo coordination patterns: such a write is the confirmed exception, performed under the operator's per-change decision — exactly the gate those patterns already call for.
