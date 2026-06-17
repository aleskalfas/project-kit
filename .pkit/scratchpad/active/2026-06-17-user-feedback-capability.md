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

## Next steps (when resumed)

1. Settle the **lifespan** decision (one-per-session vs long-lived-rollover).
2. Resolve the **capability-dependency** prerequisite (the parked modular-install-surface note).
3. Run `critic` then `architect` on the *full* revised design (the first critic pass was on the pre-reframe shape; architect has not reviewed the revised shape).
4. Author the capability via `capability-author`; ship the `feedback` issue type + the constrained end-user agent + the session lifecycle.
