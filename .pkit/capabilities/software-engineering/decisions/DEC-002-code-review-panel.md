---
id: DEC-002
title: Code-review panel shipped from software-engineering
status: accepted
date: 2026-08-19
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

> Ship a **code-review panel** from the `software-engineering` capability — a generalist **`code-reviewer`** (the headline: a general "review this PR"), plus **`security-reviewer`** and **`docs-reviewer`** — registered through the reviewer-contribution socket ([project-management:DEC-032]) so it gates code-carrying PRs through the *existing* binary all-must-approve gate ([project-management:DEC-028]). This closes bug #715: today the merge gate assesses conventions but nothing reviews the code. Each agent **blocks only on objective failures** (softer findings are advisory comments), and the panel lives in `software-engineering` to share one knowledge base with the producer. The gate *mechanics* this relies on — activation on code-carrying diffs, a per-reviewer override, and an honest gate summary — are **pm-owned companion decisions** cited here, not decided here.

## Context

The `software-engineering` capability ships exactly one agent — `software-engineer`, a *producer* that emits no verdicts ([software-engineering:DEC-001]). [project-management:DEC-032]'s reviewer-contribution socket lets a capability contribute required reviewers into the merge gate, but **no capability ships a code reviewer**, so in agent mode the gate is satisfied by the pm `reviewer`, which is conventions-only. Report #715 documented the consequence: a real PR with two security defects (an auth token passed as a subprocess argv; `shell=True` interpolating a remote-fetched tag) passed the gate `APPROVED`, because nothing in the shipped stack reviews code.

The design space was explored in the scratchpad note `2026-08-12-code-review-discipline.md` and reviewed by `critic` and `architect`. This DEC records the **`software-engineering`-owned half** — the panel, its home, and its authoring discipline. The **pm-owned half** — the activation-predicate extension, the per-reviewer override, and the honest gate summary — is a set of companion decisions (sibling Tasks under the same EPIC), kept on the pm side of the boundary per the architect's Fit-1 ruling (pm owns the gate mechanism; capabilities supply the reviewers).

## Decision

**Ship a three-agent code-review panel from `software-engineering`, registered via the reviewer-contribution socket, folding through the existing all-must-approve gate.**

1. **The panel.** Three reviewer agents, each emitting the standard [project-management:DEC-028] verdict grammar (`APPROVED`/`CHANGES_REQUESTED` + the `<!-- pkit-verdict -->` marker — the block token is `CHANGES_REQUESTED`; DEC-028 deliberately declined `REJECTED` as too terminal), registered through the reviewer-contribution declaration (the pm-owned schema):
   - **`code-reviewer`** — the generalist headline: correctness/logic at its core, plus general code quality; the "review this PR" an operator reaches for.
   - **`security-reviewer`** — illustratively: auth, secrets-in-argv, `shell=True`/injection, crypto, dependency hygiene (its contract lives in the agent body, not this record).
   - **`docs-reviewer`** — documentation completeness, understandability, and docs-match-behaviour (leaning on [project-management:DEC-015]'s doc obligations).
2. **Home: `software-engineering`.** Co-located with the producer (rationale below). Recorded here as the boundary call per [COR-026].
3. **Block-threshold discipline (per-agent).** Each agent withholds `APPROVED` **only on objective failures** within its remit; softer or subjective findings are posted as `APPROVED`-with-comments (advisory). This keeps the binary all-must-approve gate from becoming a subjective merge-blocking veto.
4. **Knowledge split.** Each agent body carries only **universal** review knowledge; project-specific rules are read from the overlay-resolved `<project-conventions>` corpus (ADR-013), mirroring DEC-001's producer discipline — so a later generation-side sharing (feeding `software-engineer`) is a non-breaking addition, not a body-extraction migration.
5. **Composability.** `code-reviewer` alone = *basic* review; adding specialists = *complex* review. Install-driven per DEC-032.
6. **Aggregation is unchanged.** Verdicts fold through DEC-028/DEC-032 binary all-must-approve. This DEC introduces **no** new aggregation.
7. **Increment 1 is human-triggered** (local identity, via `review-pr`); the fully-autonomous remote-contributed path is deferred.

**Required pm-side companion decisions (cited, decided in sibling Tasks — not here):** (a) the reviewer-contribution predicate keyed on the `type` axis **plus a diff-touches-code floor**, so the panel activates on any code-carrying PR regardless of the closing issue's classification (closes #715's mislabeled/unclassified escape); (b) a **per-reviewer override** — override one agent's block with an audited reason, without discarding the whole gate; (c) an honest **`done-work` gate summary** enumerating which perspectives reviewed and any required-but-missing one.

## Rationale

**Why the `software-engineering` home.** The load-bearing reason is the *deferred generation-side feedback loop*: the producer (`software-engineer`) and the generalist (`code-reviewer`) will share one knowledge base — the producer reads it to generate, the reviewers apply it as verdicts. Co-locating keeps that a capability-internal seam rather than a cross-capability mutual dependency. Note what does *not* justify the home: "share the conventions corpus" — ADR-013 already decouples `<project-conventions>` from any capability, so a dedicated capability could read the identical corpus. COR-007 (one instance of a review discipline — a dedicated capability is premature) and avoiding a second [COR-030] dependency edge round it out. **The cost, named honestly:** install-granularity ([COR-017]) — installing `software-engineering` for code-generation help also acquires the review gate. Accepted as low (an un-invoked reviewer is opt-in-to-run), with the **split-later seam** recorded: extract a dedicated `code-review` capability if review grows its own release cadence, a large specialist set, or independent adopter demand.

**On the two specialists' home.** `security-reviewer` rides the same code-knowledge loop as the generalist — security review *is* code review. `docs-reviewer`'s tie to that loop is weaker: its trigger is [project-management:DEC-015]'s doc obligations (pm-owned), not the code-conventions corpus the producer reads. Its home here is therefore a deliberate **panel-coherence** call, distinct from the shared-knowledge argument: the three are one code-review panel — authored under one block-threshold discipline, shipped and versioned as one contribution, composable together — and splitting doc review into pm or a separate capability would fracture that for a single instance (COR-007). If doc review later grows its own weight it follows the same split-later seam.

**Why the panel (three), not one.** A maintainer call, over the `critic`'s ship-one lean: the generalist `code-reviewer` is the most-wanted deliverable, and shipping the specialists alongside gives real multi-perspective coverage at once. The critic's compounding-false-block risk is real and is **actively mitigated**, not ignored: the per-agent block-threshold (D3), the universal/project knowledge split (D4), and the required per-reviewer override companion decision together keep the panel from becoming a merge-halting nuisance.

**Why block-only-on-objective.** Binary all-must-approve ANDs identical tokens; a subjective lens that hard-blocks on taste becomes a veto that trains the `--bypass` reflex — reintroducing #715's "green means nothing" from the other side. Pushing "block vs advise" into each agent body keeps the gate binary and the reviewers useful.

**Why `security` and `docs` specifically.** Security is #715's demonstrated harm (a correctness generalist plausibly misses `shell=True` injection). Docs leans on existing DEC-015 doc-obligation machinery, which applies to any adopter that installs project-management.

### Alternatives considered

- **Ship one reviewer first (security-first).** The critic's lean (compounding false-blocks; #715's harm was security). Rejected by maintainer: the generalist is the headline, and the false-block risk is mitigated (above).
- **A dedicated `code-review` capability.** Rejected for increment 1 (COR-007 — one instance; a second COR-030 edge; splits the producer⇄reviewer knowledge loop). Recorded as the split-later seam.
- **Register the panel as *baseline* reviewers** (project config) rather than contributed. Rejected — reintroduces the project↔capability coupling DEC-032 exists to remove ([COR-014]/[COR-026]).
- **Invent a per-finding severity aggregation.** Rejected — reuse DEC-028/DEC-032 all-must-approve untouched; the block-vs-advise distinction lives per-agent instead.

## Implications

- **Three agent files** under `software-engineering/agents/`, plus the **reviewer-contribution declaration** (the pm-owned schema) declaring them and their activation predicates. The declaration depends on the pm-side DEC-032 `type`-axis + diff-touch-floor amendment (sibling Task) to resolve.
- **`requires_capabilities: project-management`** ([COR-030]) — the capability declares the pm dependency for the socket + gate.
- **Block-threshold and knowledge-split are authoring disciplines** for the agent bodies. They are currently *convention*, not a validated contract; a testable expression of the objective/advisory line is flagged as future work (the `critic`'s G1).
- **Verdict grammar, freshness, all-must-approve: unchanged** (DEC-028/DEC-032).
- **Surface change** ([PRJ-002]) → `software-engineering` capability + backbone bump; ships via `pkit upgrade`. **No migration** — additive (new agents, new declaration; a project without the capability, or a PR the predicate doesn't match, behaves as today).
- **Companion pm decisions / sibling Tasks:** DEC-032 amendment (`type` axis + diff-touch floor); per-reviewer override; `done-work` gate-summary attribution. ADR-013 gains a forward-pointer (architect-owned) noting the panel realises its predicted review consumer.
- **Implementation is gated with those companions (acceptance-gate honesty).** DEC-002 records the panel *decision*; the panel's activation cannot resolve without the pm resolver extension, so **no panel code ships until the companion decisions are also accepted.** They accept as one EPIC-level set under #725 — DEC-002 does not build against an unaccepted companion.
- **Deferred (not this increment):** the remote-contributed (autonomous) path; a structured `review-rules` knowledge corpus; the generation-side sharing wiring; `testing`/`performance` reviewers; the review-to-file preview and native-GitHub-review companion Tasks.
- **Retires** the scratchpad note `2026-08-12-code-review-discipline.md` (this DEC + EPIC #725 are what it produced).
