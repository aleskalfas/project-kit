---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-06-17
---

# User feedback capability

> Parked design from a 2026-06-17 session. The shape is largely settled; **one decision is open** (issue lifespan) and the build has a **prerequisite** (capability→capability dependency). Resume from "Open decision" + "Next steps".

## Intent

A developer hands an adopter project (e.g. `trustworthy-summarizer`) to a **non-technical end-user** who will *use* it. That person needs (a) help using it and (b) a channel to report problems — by running Claude Code in a constrained "feedback mode" where the agent does **all** the git/GitHub mechanics invisibly. The user never sees a branch, PR, or `gh`.

## Settled shape

- **A new, separate capability** (working name `user-feedback`) that **depends on** project-management — *not* folded into it. Reasoning: different audience (end-user vs developer); avoids distorting PM's role model (DEC-008 PM/Implementer, DEC-027/028 review modes) to fit an end-user role; installs/versions/uninstalls independently. The strongest pillar is audience-distinction (an end-user is not a PM role); the "install-bloat" pillar is weak (it's opt-in either way).
- **It consumes PM's tracker, doesn't reimplement it.** Feedback lands as project-management issues; a constrained end-user agent **translates** plain feedback into the structured artifacts.
- **Feedback model (chosen Option 2 + a reframe):**
  - A single auto-created **`[EPIC] Feedback`** bucket.
  - Under it, lightweight **`feedback`-type** issues, titled by reporter, e.g. `[Feedback] Aleš Kalfas <kalfas.ales@gmail.com> — session start 2026-06-17`. This needs a small PM extension: a lightweight `feedback` issue type with relaxed body rules (no acceptance-criteria/doc-impact/parent-beyond-the-EPIC).
  - Individual problems = **comments** on that issue (the issue is the thread/holder).
- **Identity is solved by the title.** Reporter name/email is plain text in the title → no GitHub account needed for the end-user; the developer's token does the writing. (This dissolved the critic's R2 identity concern.)

## Open decision (resume here)

**Issue lifespan** — two options, undecided:
- **(i) one issue per session** — fresh issue each time the user starts the feedback agent; accumulates many over time.
- **(ii) one long-lived issue per user, with rollover** — created at a session start (hence the title), accrues comments across sittings until the *developer* closes it; closing triggers the agent to open the next one.

The title "session start …" reads naturally for either. Pick one before building.

## Prerequisite

**Capability→capability dependency does not exist in pkit yet** (capabilities declare only `requires_backbone`). `user-feedback`→`project-management` would be a concrete consumer. There is a parked exploration of the general mechanism: `.pkit/scratchpad/active/2026-05-22-modular-install-surface.md` (Concern 4 / Option E). Resolve that note's mechanism (general `dependencies:` block; install-order/cycle/upgrade-cascade/uninstall-refusal) before building this.

## Open questions from the critic pass (2026-06-17)

- **Threat model (R3):** an "innocent user + autonomous agent on their own machine" is a larger attack surface than a developer who understands the agent — prompt-injection via the feedback text the agent treats as instructions; the agent's filesystem reach; the blast radius of the credential it uses. Needs a threat-model section, not a hand-wave. (Note: ties to the permission/sandbox model — the OS sandbox bounds the agent; the intent-layer denies don't fully, per ADR-004 §61.)
- **PM-issue-fit:** confirmed PM validation is a hard gate; the `feedback` lightweight type is the resolution (a small, contained PM extension — a new *type*, far less invasive than a new *role*).
- **Mapping:** the durable thread is closer to an Umbrella-style bucket than a Task — make the containment mapping explicit when building.

## Reframe — trustworthy-notes hand-off (2026-06-17)

The `tn feedback` design (`2026-06-17-tn-feedback-design.md`) is a *settled, concrete* instance of this pattern, and it reshapes the capability — for the better. It dissolves the critic's fatal findings:

- **Shape: a deterministic `feedback` *command/flow*, not a free autonomous agent.** The LLM is ONE structuring step (raw-text fallback if it fails) inside a fixed pipeline: capture diagnostics → build a repro bundle → AI-structure → file → confirm. This dissolves the critic's RF-1 — a fixed pipeline can't be hijacked into arbitrary tool calls, and injected feedback text at worst garbles the structured title/summary; it can't make the flow *do* something else.
- **Credential: a separate PRIVATE feedback repo + a fine-grained PAT scoped to that one repo** (Issues + Contents, with expiry), delivered **out-of-band** (1Password), stored in local config — **never in the shipped artifact**. Blast radius if leaked = one private feedback repo, instantly revocable. Dissolves RF-2.
- **The private repo dissolves the PII/data concern (G-1)** and is *required* because the repro bundle carries sensitive source excerpts. Plus an explicit **consent boundary**: the user sees and acknowledges exactly what is uploaded before it's sent.
- **Graceful fallback** — offline / missing / expired token → write a local `feedback.txt`; feedback is never lost.
- **Isolation** — the feedback module is never imported by the core pipeline (`cli → feedback`, never `pipeline → feedback`), keeping the deterministic path network- and second-credential-free.
- **Identity by name-tag** ("Reported by: \<name\>") since the PAT authors as the maintainer — no GitHub account for the end user.

**Consequences for the earlier open items:**
- The **lifespan / rollover / per-session-issue** machinery (including the (b) decision) is **largely moot** — feedback is issues in a separate feedback repo the maintainer triages; no per-session rollover to manage (the critic's CA-3 holds).
- The PM **`feedback`-type extension** is likely **not needed** — feedback lands in its own repo as plain issues, not in the project's PM tracker with a new type.
- So the **`requires_capabilities: [project-management]` dependency may not be load-bearing for *filing*** — this shape files independently to a feedback repo; the maintainer pulls worthy items into the PM tracker by hand. COR-030 was the prerequisite for the original *agent-uses-PM-scripts* shape; re-examine whether the reframed shape needs it at all.
- The **serverless-proxy** alternative (tn rejected-but-deferred) is the critic's CA-1 intermediary — kept as the **v2 target** if PAT rotation becomes a burden.

## Next steps (when resumed)

1. **Re-run `architect`** on the *reframed* shape (deterministic command + AI-structure step; separate private feedback repo + scoped out-of-band PAT; consent + fallback + isolation). The earlier critic+architect passes were on the agent-with-PM-dependency shape; this is materially different and safer.
2. **Generalize the `tn feedback` pattern into the pkit capability** — separate the reusable parts (the flow, the credential/repo model, consent, fallback, isolation) from the project-specific parts (the repro-bundle contents). Decide whether it still depends on project-management.
3. **Trust-boundary ADR** — the data-exfiltration / second-credential boundary (tn's docs Task #13 obligation) generalizes to a pkit ADR.
4. Author via `capability-author` once the shape + the dependency question are settled.
