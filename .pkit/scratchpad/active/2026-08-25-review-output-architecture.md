---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-08-25
---

# Review output architecture

> **INPUT NOTE — needs reconciliation with #757 (do not treat as settled).**
> Authored independently on 2026-08-25 in a separate design conversation, *before* discovering that EPIC #756 / Feature #757 already own the comment-house-style + aggregated-review-format work (with its own scratchpads on this branch). Landed here as an input for the #757 author to integrate. Assessment vs the existing #757 notes:
> - **Overlap:** the "aggregated review format" territory is already rendered more concretely in the `2026-08-24-code-review-round-{1,2,3}` and `code-review-surface-template` notes.
> - **Divergence (a real fork to resolve):** this note argues for **one combined comment** (panel sub-reviewers merged into a single review); `code-review-surface-template.md` renders the opposite — **each reviewer posts its own native GitHub review** with inline findings. Pick one.
> - **Distinct value this note adds:** the *data-model* half the presentation notes don't pin — source of truth moving from comment → **structured data**, the `format(data)→string` **seam** (swappable formatter; review is its main consumer), the **review data schema**, the **multi-actor** model (agents + humans + remote), and **tamper-evidence moving to the data artifact** (DEC-047/ADR-042 guarantee re-homed).
> Retire this note by folding its distinct-value points into #757's converging DEC (or dropping it if superseded).

*Exploratory note (COR-012). Explores how code-review output should be modelled, aggregated across actors, and formatted — moving the source of truth for a review from the posted comment to structured data. Seeded from a design conversation on 2026-08-25; not yet a decision. Expected to crystallise into a project-management DEC (the review-data / gate-read model) and likely an ADR (the review↔format seam + tamper-evidence boundary).*

## The question

Today each reviewer posts its own verdict comment and the merge gate reads those comments (latest-per-agent). We want to restructure review output so that:

1. reviewers share a common **review process** (one prompt template) and each emit a **structured review** conforming to a shared schema;
2. the local agent panel's individual reviews **combine into one final review → one comment**, rather than N separate agent comments;
3. review output is **structured data (JSON)** that a **formatting feature** renders into the comment string — review calls `format(data) → string`;
4. the model supports **multiple review actors** (agents *and* humans, and independent/remote reviewers), whose reviews mix.

The central architectural shift: **move the source of truth for a review from the comment to the data.** The comment becomes a *rendering* of the data; the gate reads the data.

## Forces

- **The formatter feature is in flux, and review is its main consumer.** We must not block review on it. → Review ships its *own* temporary formatter behind a swappable `format(data) → string` seam; the general formatter drops in later. The durable artifact is the **data schema**, not the formatter.
- **Multi-actor is a standing assumption, not a later add.** "When I produce something I want to run the review functionality *and* let colleagues review too, so the reviews mix." Humans and independent/remote reviewers are separate actors; the local agent panel is *one* actor whose sub-reviewers combine.
- **The gate must stay trustworthy.** Today the anti-forgery guarantee lives in the verdict comment's marker (DEC-047) and the read surface (ADR-042) — a human can't hand-type an approval the gate counts. Moving the source of truth to data means the *data artifact* must become the tamper-evident thing.
- **Don't reinvent composition.** All-must-approve over a per-PR resolved required set (DEC-032) works; the question is *where the verdicts are read from*, not how they compose.

## What is already known (current architecture)

- **DEC-028** — a reviewer's verdict *is* a comment: first-line grammar `Reviewer agent (local, <name>): APPROVED|CHANGES_REQUESTED`, two paths (local attestation / remote bot identity).
- **DEC-047 / ADR-042** — the verdict carries a `<!-- pkit-verdict -->` marker; the gate counts a verdict only when the marker is present (anti-spoofing on the read side). The read surface annotates, never fabricates.
- **DEC-032** — the required reviewer set is resolved per-PR (baseline ∪ contributed-matching), AND-composed (all-must-approve). `review-pr` and `done-work` share the resolver so invoke-set == gate-set.
- **`review-pr.py`** — builds the invocation prompt ad-hoc in `_invoke_agent`, runs each agent as `claude -p "<prompt>" --agent <name>` (300s timeout — see the separate fix, item 1), scans stdout for the verdict line, posts *one comment per agent*.
- **`done-work`** — reads latest-per-agent verdict comments, requires all required reviewers APPROVED (or satisfied-by-override, DEC-050).

## The emerging design (candidate, not decided)

**Actor model with two aggregation levels.**

- An **actor** produces review data. Actors: the **local agent panel** (one actor), **humans** (each an actor), **remote/independent reviewers** (each an actor).
- **Level 1 — within the local pass:** the panel's sub-reviewers (pm-reviewer, code-reviewer, security-reviewer, docs-reviewer) each fill the structured review template; their data is **combined into one review → one comment**. They are *not* independent actors relative to each other.
- **Level 2 — across actors:** the combined agent review + human reviews + remote reviews **mix** into the overall code review the gate judges.

**Data as source of truth.**

- Each sub-reviewer emits data conforming to a **review data schema** (the durable contract: sub-reviewer fills it, formatter renders it, gate reads it).
- The local pass combines the sub-reviewers' data, formats it (temporary formatter now), and posts **one comment** that *carries or references* the combined structured data.
- The gate reads the **data** to confirm each required sub-reviewer approved — not N separate comments. Human/remote actors compose as they do today (native reviews / their own verdicts).

**Swappable formatter seam.**

- Review depends on an interface `format(review_data) → string`, implemented by a temporary in-review formatter, replaced later by the general pkit comment-formatting feature. The seam + schema are what make the swap non-breaking.

**Shared reviewer prompt template.**

- One template describing the common review process, replacing the ad-hoc prompt in `_invoke_agent`; per-reviewer specialisation stays in each agent's `.md` body. "Fill the template" == "emit data conforming to the schema".

## Open questions (what the crystallising decisions must resolve)

1. **The review data schema.** What attributes does a single reviewer's structured review carry (reviewer name, verdict, findings with severity, remit, evidence/locations, advisory-vs-blocking)? What does the *combined* review carry (per-sub-reviewer entries + an overall verdict)? This is the load-bearing contract.
2. **Where the combined data lives, and how it stays tamper-evident.** Options: embedded in the comment as a marked/fenced JSON payload; a separate committed data file; a PR artifact. Whichever it is must preserve the DEC-047/ADR-042 guarantee that a human can't forge a gate-counted approval — the tamper-evidence has to move from "marked comment first line" to "the data artifact".
3. **Cross-actor gate composition.** How does `done-work` compose the combined agent-pass (all required sub-reviewers approved, read from data) with human reviews and remote reviews? Likely: DEC-032's resolved set stays per-required-reviewer, but the *read* moves from per-agent comments to the combined data; DEC-028/DEC-026's human/remote paths unchanged. Confirm.
4. **Migration / back-compat.** N-separate-comments → one-combined-comment changes what `done-work` reads and what `show-pr --field review` displays. Does the read surface need to understand both during a transition?

## Relationships

- **Depends on / co-designs with** the in-flux pkit **comment-formatting feature** (review is its main consumer; the `format(data)` interface is the shared seam). Review proceeds now with a temporary formatter; the schema is the contract the formatter later conforms to.
- **Amends/extends** DEC-028 (verdict-as-comment → verdict-as-data + rendered comment), DEC-047 / ADR-042 (tamper-evidence moves to the data artifact), DEC-032 (read source of the verdicts), DEC-050 (per-reviewer override composes with the combined pass).
- **Independent of** items 1–3 in the review-fixes batch (timeout config; `project-conventions` discoverability; `reviewer` → `pm-reviewer` rename) — those land on today's model; item 3's `<name>` becomes a data attribute here but the rename is orthogonal.

## Retires by

Producing a project-management **DEC** (the review-data / gate-read model + the actor/aggregation model) and, if the data/format seam and tamper-evidence boundary prove architecturally significant, an **ADR** — plus the implementing Tasks. Or being dropped if the direction changes.
