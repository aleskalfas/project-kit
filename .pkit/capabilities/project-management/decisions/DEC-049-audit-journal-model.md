---
id: DEC-049
title: Audit/journal model — engine journal is canonical, GitHub comments are a configurable provenance-stamped projection
status: accepted
date: 2026-08-12
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

> pkit records what it does to an issue/PR in two roles with a clear hierarchy. The **engine journal** — substrate-neutral, append-only, one entry per pkit-governed mutation with actor + pkit/capability version — is the **canonical audit trail**. **GitHub comments are a configurable, provenance-stamped *projection* of it**, never a second source of truth: intensity `off` / `audit` *(default)* / `full`. Override/authorisation justifications (a DEC-014 bypass, a `--force`) are the `audit` floor — the *why* that must survive even a failed mutation and be visible to a reviewer. `full` stamps **every** governed mutation with the pkit + capability versions, making the **governance boundary** visible: a GitHub timeline event with **no matching pkit record** is an out-of-band (ungoverned) change — also machine-detectable via `pkit pm history <N> --check-drift`. One canonical comment format from a single schema field, exactly **one** audit comment per audited mutation, a uniform `<!-- pkit-audit -->` marker.

## Context

The pm capability mutates issues/PRs — state transitions, closures, PR reviews — and records them three inconsistent ways today: (1) **GitHub labels + timeline** (native; records *every* change including manual ones, with actor + timestamp); (2) a **local engine journal** via `pkit process move` (best-effort, invisible on GitHub); (3) **audit comments** posted only for bypassed/authorised transitions.

#672 exposed the incoherence: a `Todo→Backlog` produced **two** comments in divergent formats (a wrapper hook comment *and* a `move-issue` `[audit]` line whose reason literally said "(audit comment already posted)"); a `Backlog→In Progress` produced **none** and looked unlogged; and the posted `[audit]` line did not match the schema's own `audit_comment_template`. The root cause is the absence of a stated model for what an audit comment is *for*, when it is needed, and how it is formatted.

The load-bearing observation: **the timeline already logs label changes**, so a comment that merely restates a transition is redundant — but comments carry two things the timeline cannot: the **why** of an override, and the **provenance** (which pkit version made the change). Provenance is the only way to distinguish, *on the issue itself*, a pkit-governed change from an ungoverned one.

## Decision

**1. The engine journal is the canonical audit trail.** Substrate-neutral (the COR-042 process engine), append-only, one entry per pkit-governed mutation with actor + pkit/capability version. It is promoted from best-effort to **reliable-and-complete**: a move that fails to journal is surfaced, not silently dropped. GitHub's timeline and comments are **projections** of this trail, never the source of truth.

**2. GitHub comments are a configurable, provenance-stamped projection with three intensities:**

- **`off`** — no journal comments (engine journal only).
- **`audit`** *(default)* — only override/authorisation justifications: a `bypassable-with-audit` bypass (DEC-014), a `--force` override (DEC-046), a user-authorised transition carrying a reason. The *why* that must survive a failed mutation and be visible to a reviewer.
- **`full`** — every pkit-governed mutation, each stamped with the pkit + capability versions.

The engine journal records everything regardless of level; the knob controls only the GitHub projection.

**3. The governance boundary.** At `full`, provenance-stamped comments make governed-vs-ungoverned changes visible on the issue: a timeline event with no matching pkit comment is an out-of-band mutation (a manual label flip, a raw `gh` edit) — the issue-tracker analogue of the COR-039 cross-repo interlock. It is also machine-detectable at any level via **`pkit pm history <N> --check-drift`**, which diffs the engine journal against the GitHub timeline and flags events pkit did not author.

**Format + single-poster rules.** Exactly **one** audit comment per audited mutation — the underlying mutator (`move-issue`) is the sole audit-comment writer; wrappers pass the reason through rather than posting their own. **One** canonical format, sourced from a single schema field (`validation-severity.yaml`'s `audit_comment_template`), carrying a `<!-- pkit-audit -->` marker + actor + transition + reason, and — at `full` — provenance. Consistent with the existing `<!-- pkit-verdict -->` / `<!-- pkit-provenance -->` / `<!-- pkit-hook -->` markers.

## Rationale

- **Why the engine journal, not the timeline, is canonical.** The timeline is substrate-specific (GitHub), un-exportable, un-greppable, and cannot distinguish governed from manual changes — leaning on it as *the* journal contradicts the methodology's neutrality (COR-014). The engine journal is neutral and complete; making it reliable is the load-bearing move.
- **Why comments at all, given the timeline.** Two things the timeline can't give: the *why* of an override, and *provenance* (which pkit version governed the change). The latter yields the governance boundary — the single strongest reason to project pkit's actions onto the issue.
- **Why configurable intensity.** The tension is noise-vs-completeness, and it is project-specific: a solo repo wants quiet (`audit`); a regulated / multi-person adopter wants the full governed trail (`full`). A knob dissolves the tension without a one-size policy.
- **Why `audit` is the default.** Override justifications are load-bearing (DEC-014's survive-failure / visible-to-reviewer property) and low-volume; the full governed trail is opt-in for those who need the boundary.
- **Why one poster / one format.** #672's double-post and template divergence came from two writers (wrapper + mutator) and a hardcoded `[audit]` line ignoring the schema. A single writer + a single schema-sourced format removes both.

### Alternatives considered

- **Timeline is the journal, comments only for overrides** (the first strawman). Rejected: substrate-locked, undiscoverable, and it throws away provenance / the governance boundary.
- **A single append-updated "audit log" comment per issue.** Considered; deferred as an option the implementation may adopt for at-a-glance completeness. Downside: edit-in-place races (this repo runs concurrent instances). The `full` level + the `history` read cover the need without it initially.
- **No comments at all; engine journal + read only.** Rejected as the *floor*: it loses DEC-014's on-issue, survives-failure justification visible to any reviewer without the CLI.

## Implications

- **`move-issue` becomes the sole audit-comment writer;** the wrappers (`promote-issue`, `start-work`, …) stop posting their own audit/hook comment for the transition and pass the reason to `move-issue` — killing the #672 double-post.
- **`validation-severity.yaml`'s `audit_comment_template`** becomes the single format source, extended to marker + actor + transition + reason (+ provenance at `full`); every poster renders from it. The current hardcoded `[audit] transition …` line in `move-issue` is corrected to the template.
- **New config:** a pm project-config key `audit.projection: off | audit | full` (default `audit`) per the adopter-config pattern, read by the mutators.
- **Engine journal reliability:** `_journal_move`'s best-effort no-op becomes a surfaced failure (the trail is load-bearing now); the engine entry records actor + version.
- **New read:** `pkit pm history <N>` renders the journal; `--check-drift` diffs journal vs timeline for the governance boundary.
- **Marker vocabulary** gains `<!-- pkit-audit -->`.
- **Autonomous transitions** get a comment only at `full` (provenance); at `audit`/`off` they live in the engine journal + timeline — resolving #672's "looked unlogged" by making the level explicit and adding the `history` read.
- **Relationship to DEC-014:** this is the model DEC-014's audit-comment mechanic plugs into; DEC-014's `bypassable-with-audit` remains the `audit`-floor trigger, now rendered through the single canonical format.
- **Tracking:** implementation slices under EPIC #690 (format reconciliation / single-poster / intensity config / engine-journal reliability / `history` + `--check-drift`); the #672-noted format-fix folds in as one slice.
- **Acceptance gate:** `proposed`; needs maintainer sign-off before the implementation Features are built.
