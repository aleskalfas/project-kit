---
id: DEC-050
title: A gate never passes an axis it could not read — four outcomes, and unverified is not missing
status: proposed
date: 2026-08-20
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

*When a gate checks a classification axis carried by a Projects v2 field, four things can happen and none of them may collapse into another: the field **has** a value; it is **empty**; the issue has **no card** on the board; or the board **could not be read**. A gate never reports satisfied on a value it could not read — that is the same falsehood as marking a richly-encoded axis `unsupported`. But it never reports "you forgot a value" when the truth is "the tracker did not answer" either: an unreadable board is **unverified**, a distinct verdict, and its two causes are told apart — a **configuration** fault refuses loudly and is pushed earlier to the prerequisite check, while a **transient** fault says so and clears on a re-run.*

## Context

A board-carried axis is now writable — the field-setting verb resolves the board field and its option by name at runtime (shipped for the board-substrate work) — which closes the root cause behind a reported unsatisfiable gate. The read side is the other half: until a gate can *check* a board-carried value, such an axis can be declared and populated but never verified, so the methodology's "every issue carries these three axes" claim is unenforced wherever the board carries one.

Reading a board value is not like reading a label. A label arrives with the issue in the same payload the gate already fetched; a board value requires the project, the field, the option set, and the issue's card — a live call that can fail for reasons that have nothing to do with the issue being classified. That makes the failure mode the load-bearing decision, not an implementation detail, and it is the decision that must be made *before* code exists to discover it accidentally:

- **Fail closed on any read failure** and a rate limit or a five-second network blip blocks merges on work that is correctly classified.
- **Fail open on any read failure** and a token permanently missing the `project` scope yields an axis that reports as checked and is never checked once — the precise deceit that made `unsupported: true` the wrong way to describe a board-carried axis.

Neither is acceptable as a blanket rule, and choosing between them is a false binary: the two failures differ in *kind*, and the gate can tell them apart.

## Decision

**In plain terms:** the gate distinguishes "no value", "not on the board", and "couldn't look" — and only the first two are the adopter's classification problem. If it couldn't look, it says so, and says whether that is something to fix or something to retry.

1. **Four outcomes, never collapsed.** A board-carried axis check resolves to exactly one of:
   - **value present** — the gate is satisfied;
   - **value absent** (the read succeeded; the field is empty) — the axis is genuinely unclassified, refused exactly as a missing label is refused today;
   - **no card** (the read succeeded; the issue is not on the board) — refused, naming the membership operation that fixes it, consistent with the field-setting verb's own choice not to add a card as a side effect;
   - **unverified** (the read did not succeed) — a **distinct verdict**, never rendered as either satisfaction or absence.
2. **A gate never passes an unverified axis.** Unverified does not satisfy the check. The claim "this issue carries a priority" may only be made from a value actually read.
3. **Unverified is not "missing".** The adopter is told the tracker did not answer, not that they forgot something. Wording and remediation differ, because the fix differs.
4. **The two causes of unverified are told apart.**
   - A **configuration** fault — the token lacks the board scope, the configured board does not resolve, the named field does not exist on it — is an adopter-fixable error. It refuses loudly, names what was looked for and what the board actually offers, and — load-bearing — the **prerequisite check** detects this class *before work starts*, so a gate meets it only when someone skipped that gate.
   - A **transient** fault — network failure, rate limit, a server error — reports unverified-retry. It blocks the claim without accusing the adopter, and a re-run clears it.
5. **One resolver answers "what is this axis's value?"** — routing to labels or to the board behind a single accessor every consumer asks, so a writer and a reader cannot form different beliefs about where an axis lives. The pure label seam stays pure: it remains a function over label names with no live dependency, and the board read stays in its own read module. *Where* that composition lives is an architectural contract and is settled in the architecture record for the read path, not here.

## Rationale

**Why a four-way answer rather than a policy knob.** An adopter-tunable fail-open/fail-closed switch would be a third source of truth about correctness, and it would be set once, wrongly, and forgotten. The four outcomes are not a matter of taste: they are four genuinely different states of the world, and each already has an obviously correct response. Collapsing them is what produces both bad blanket rules.

**Why unverified must not satisfy.** This is the same discipline the process-health check settled for a report-only walk — an indeterminate answer is surfaced distinctly and never counted as clean — applied where something *does* ride on the answer. A gate that passes on an unread value is indistinguishable, in the adopter's repo, from a gate that does not exist; and the failure is silent, so it is discovered by the absence of classification months later rather than by a refusal today.

**Why unverified must not accuse.** Reporting "carries no priority" when the board was unreachable sends the adopter to fix a correctly-classified issue. The wrong diagnosis costs more than the delay: it teaches distrust of the gate, which is how gates come to be bypassed.

**Why the configuration class moves to the prerequisite check.** A missing scope or a mistyped field name is not a per-issue fact — it is true of the whole repo from the moment it is written, so discovering it at review time is discovering it at the most expensive moment. The prerequisite check already reads the board configuration and already refuses a self-contradictory substrate claim; extending it to "can this board actually be read, and does the named field exist" moves an entire failure class from mid-flight to setup, and leaves the gate facing only the transient case a retry resolves.

**What this costs, stated plainly.** A gate checking a board-carried axis makes a live call it does not make today: reviews are slower for those adopters, and they now require a token with board read access. Adopters carrying every axis on labels are unaffected — no new call, no new scope. The cost buys the only thing that makes a board-carried axis honest: a check that actually checks.

### Alternatives considered

- **Fail closed on every read failure.** Rejected — a transient failure becomes a merge blocker, which is how a gate earns a reputation for flakiness and then an override habit.
- **Fail open on every read failure.** Rejected — it manufactures the silent, permanently-unchecked axis that this whole arc exists to eliminate.
- **An adopter-configurable strictness knob.** Rejected — a third source of truth about correctness, set once and forgotten; the four states have correct answers that need no tuning.
- **Cache the last successfully-read value and gate on the cache when the board is unreachable.** Rejected — a stored copy of tracker truth drifts, and a gate reporting satisfaction from a stale cache is exactly the derive-don't-store failure the substrate avoids elsewhere. Worse, it would make the deceit intermittent and therefore harder to notice than a blanket fail-open.
- **Treat "no card" as unverified.** Rejected — the read succeeded and the answer is definite: the issue is not on the board. It is an adopter-fixable state with a one-command remedy, so it earns a refusal with that command, not a shrug.
- **Retry internally until success.** Rejected as the settlement — it converts a transient failure into a slow one and hides rate limiting from the operator. A distinct unverified verdict plus an ordinary re-run is honest and cheaper; a bounded retry is an implementation nicety that may ride along, not a semantic.

## Implications

- **The prerequisite check grows a board-readability check** (board resolves; named fields exist; token can read them), which is where the configuration class of unverified is meant to be caught. Its existing refusal of a two-substrate claim is untouched.
- **The gate paths gain a fourth verdict.** Consumers that today distinguish present / absent must carry unverified through to their output and exit codes without folding it into either — the same shape the health check's indeterminate already uses.
- **One resolver, asked by every consumer**, with the label seam's purity preserved; the placement contract is an amendment to the read-path architecture record, whose "fold the board-vs-label switch into the seam" alternative was rejected *for v1* explicitly for want of a second demanding consumer. That consumer now exists — the reported adopter — so the amendment records that the rejection's stated condition has expired rather than that its reasoning was wrong.
- **Reads cost a call and a scope** for board-carried axes only; label-only adopters see no change. Documented adopter-facing, since a token scope is a setup fact.
- **Unblocks the binding-kind record** (the still-open question of making the board a declarable binding kind, tracked on the board-substrate issue): with a board-carried axis both writable and checkable, declaring the board a first-class binding kind no longer requires inventing a stated-but-unpoliced middle state.
- **Acceptance gates the implementation**: the fourth verdict, the resolver, and the prerequisite extension may not land while this record is `proposed`.
- **Surface change** for the capability — a new verdict adopters can observe and a new setup requirement — so the change-set declares a changeset; version numbers are written by the release step.
