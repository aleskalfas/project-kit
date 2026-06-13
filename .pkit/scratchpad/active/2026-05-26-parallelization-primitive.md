---
authors:
  - Ales Kalfas <kalfas.ales@gmail.com>
started: 2026-05-26
---

# Parallelization primitive for the project-management capability

This scratchpad is an **inbound proposal for `pkit`** authored in an adopter project (`interaction-gateway`). The intent is to hand it to the project-management capability when the design has matured enough that a decision record (DEC-NNN) can crystallise from it.

## The question

How should the project-management capability support **systematic parallel execution of issue work** — i.e. give adopters and their agents a way to decide which issues are safe to pick up at the same time — given that:

- **Workstreams** are defined in [project-management:DEC-018-workstream-taxonomy-and-lifecycle] as *long-lived domain areas* (categorisation, reporting). Overloading them as parallel-lane locks muddies that semantic and breaks when a workstream is renamed / merged / split.
- **Dependencies** between issues are defined in [project-management:DEC-005-linking-and-containment] as **textual prose** in an optional `## Dependencies` body section. The substrate is unparsed; the graph cannot be queried, validated, or reported on.
- **Native sub-issues** (DEC-005) handle parent ↔ child *containment* only — not "blocked by" / "follow-up to" / "see also."

The capability today gives adopters no systematic way to answer two questions a parallel-execution model has to answer:

1. **Can issues A and B be in flight at the same time?**
2. **Given the in-flight set, what is the unblocked frontier — what is safe to pick up next?**

## Forces

- **Adopter efficiency.** Real adoption (this project + AUJ + others) runs multiple issues concurrently across worktree branches. Without a primitive, every adopter improvises the discipline and the answers drift.
- **DEC-018 semantic integrity.** Workstreams are *durable domain areas*. They must not be re-purposed as ephemeral code-area locks; the moment a workstream is renamed (DEC-018 rename op), the lock partition breaks.
- **DEC-005 dependency weakness.** Textual prose is the *only* substrate for non-containment links. Adopters can write `Blocked by #N` in any form they like; tooling cannot grep it reliably; lifecycle ops (close, reopen) do not consult it.
- **GitHub-bound substrate (DEC-003).** Whatever primitive we propose must project onto GitHub's existing surfaces — labels, issue bodies, sub-issues, Projects v2 fields, assignees — not require a side database.
- **Two distinct conflicts to disambiguate.** "Cannot be parallel" has two unrelated causes that the primitive must distinguish:
  - **Code-surface conflict** — both issues touch overlapping files; merging will conflict; only one can hold the surface at a time. Static; geography-based.
  - **Sequence conflict** — issue A's outcome is an input for issue B; B cannot start until A lands. Dynamic; outcome-based.
- **"Don't bake conventions" (project library promotions principle).** The primitive should compose — adopters with different workflows (solo dev, small team, large org, agent-driven) should reach the same primitive at different layers.
- **Agent-driven workflows.** A growing share of adoption is agent-mediated. The primitive must be machine-readable enough that an orchestrator can compute the ready frontier without prose parsing.

## What is already known

- [project-management:DEC-018-workstream-taxonomy-and-lifecycle] — workstreams as long-lived domain areas; 5-attribute model; eight lifecycle scripts; mutually exclusive on issues.
- [project-management:DEC-005-linking-and-containment] — native sub-issues for parent↔child; textual `## Dependencies` body section for everything else.
- [project-management:DEC-012-classification-axes] — Type, Priority, Workstream as the three classification axes. A new primitive would either extend axes or live orthogonally.
- [project-management:DEC-003-github-bound-substrate] — substrate constraint; whatever ships must project onto GitHub surfaces.
- [project-management:DEC-017-prerequisites-bootstrap-migrate-discipline] — same-PR-as-surface-change discipline; schema bumps; migration manifest primitives.
- [project-management:DEC-020-methodology-as-executable-commands] — verb-subject scripts under `scripts/`; PEP 723; deterministic; exit-code contract.
- [project-management:DEC-022-methodology-mesh] — cross-repo coordination; relevant if the primitive needs to be consistent across team repos.
- [COR-007] — pattern extraction; the *recurrence* signal that justifies promotion from project-local convention to kit primitive.

## On the word itself

Before fixing on a name for the new primitive, the scratchpad interrogates the word *workstream* — because DEC-018 has already claimed it for the categorisation concept, and the word's etymology pulls in a different direction.

- **work** — effort, output, the doing.
- **stream** — a *continuous flow*, a *current*, a *channel of movement* with direction.

Compound: *a continuous flow of work moving in a direction*. A flow, not a bucket. A track, not a tag.

The word's native usage (large-program / consulting / multi-team delivery contexts) is **"parallel concurrent tracks of flowing delivery work"** — each track with its own velocity, dependencies, and roll-up. The canonical sentence is *"the API workstream is two weeks behind the infra workstream."* Primary connotations:

1. **Parallelism** — multiple streams running concurrently.
2. **Flow over time** — work moves through the stream; the stream has direction and rate.
3. **Containment** — work belongs to one stream at a time; the parallel tracks are visible.

The "stable domain area" reading exists but is secondary — it's the container the stream flows *through*, not the stream itself.

**DEC-018's choice.** DEC-018 defines workstream as *"a long-lived domain area the project (or portfolio) invests in over multiple outcomes"* — picking the static-container reading and dropping the flow reading. The natural emphasis on parallel concurrent delivery is demoted to a side effect.

**The mismatch.** The word evokes parallelization; DEC-018 assigns it to categorisation. So the parallelization primitive currently has no name, and the categorisation thing has a name that overreaches its actual meaning.

## Terminology — Direction X with `lane` (recommended)

Two directions emerged from the etymological analysis:

- **Direction X — keep DEC-018's assignment; name the new primitive something else.** Categorisation stays `workstream`; parallelization gets a different word.
- **Direction Y — re-cut to match etymology.** `workstream` becomes the parallel-track primitive (its native meaning); DEC-018's static-categorisation concept gets renamed.

Initially the linguistic analysis pointed at **Direction Y** as the cleaner shape. **Field evidence reverses that conclusion** — see the next subsection. The recommendation lands at **Direction X**, with **`lane`** as the proposed name for the parallelization primitive.

### Why Direction Y is blocked: shared-board substrate

The trigger case for adopting pkit (IGW + AUJ) reveals a constraint the original etymological analysis missed:

- IGW and AUJ both feed an **org-level Projects v2 board** (Team Planning, owned by `ai-platform-incubation`) — see the sibling scratchpad `declarative-pm-hooks.md` for the field IDs.
- That board carries a `Workstream` single-select field with portfolio-scale values (`Spyre`, `llm-d`, `Agent Platform`, `Storage`, `Kagenti`).
- The board, not either repo's config, is authoritative for the workstream taxonomy. DEC-022 line 76 makes this explicit: *"when both peers use board substrate, the board IS the shared substrate and per-repo comparison is meaningless."*
- Direction Y would require **renaming the board's field** — not just label vocabulary in each repo. The board owner (a separate org-level role) would have to coordinate the rename across every peer repo's adopter config and every existing issue's board item. This is multi-team, multi-repo, multi-environment coordination for what is fundamentally a linguistic cleanup.

For board-substrate adopters in shared-board topologies, **Direction Y is infeasible**, not just expensive. The substrate vetoes the rename regardless of pkit's willingness to migrate. Label-substrate adopters could in principle do Direction Y, but a methodology can't ship a primitive that works for some substrates and breaks for others.

So Direction Y stays in the doc as **the linguistic ideal that the substrate forbids**, and the recommendation is Direction X.

### Direction X — `lane` as the parallelization primitive name

Candidate names (single-word, slug-friendly), ranked by linguistic fit + substrate-friendliness:

| Slug | Notes |
|---|---|
| **`lane`** *(recommended)* | Short; PM-vocab native ("swim lane"); immediately evokes "things in different lanes don't collide"; no namespace conflicts. Reads cleanly as `lane:<area>`. |
| `track` | Also clean; "parallel-track" lineage matches the etymology discussion. Mild overlap with "track an issue" (verb). |
| `flow` | Captures the *stream* semantic without taking the word `workstream`. Risk: overlaps with pkit's `workflow.yaml` and "workflow" as a state-machine concept. |
| `swim-lane` | Explicit, well-understood, but compound — two-token slug is heavier in labels. |
| `work-lane` | Explicit, but redundant; `lane` alone already implies the work context. |

**Recommendation: `lane`.** *"At most one in-flight issue per lane"* reads unambiguously. `lane:<area>` is greppable, validatable, and projects cleanly onto GitHub labels.

### Implications for the existing DEC-018

Direction X is *additive*, not destructive:

- DEC-018's `workstream` semantic stays exactly as written. No rename, no migration manifest entry, no cross-repo coordination.
- A new label series `lane:<slug>` is introduced under a sibling decision (DEC-NNN, this scratchpad's eventual crystallisation).
- DEC-005's `## Dependencies` extension (`Blocked by: #N`) lands separately, also additive.
- DEC-012's classification axes gain a fourth axis (parallel-lane), distinct from the existing three (type, priority, workstream). Or `lane` lives outside the axis model as a "lifecycle marker" — open question.
- DEC-022 methodology-mesh gains a `lane:*` comparison (label substrate). For board adopters this works naturally because lanes are *repo-local* (ephemeral, area-bound) where workstreams are *portfolio-wide* (durable, shared).
- The eight workstream lifecycle scripts (DEC-018) become a template for the lane lifecycle. Probably a leaner set is sufficient (`add-lane`, `remove-lane`, `list-lanes`, `show-lane` — lanes are ephemeral by intent, so rename/merge/split may be deferred per COR-007).

Net cost to pkit: a new label series + lifecycle scripts + schema + axis-or-marker placement decision. No migration for existing adopters; the surface lands as an opt-in.

## Candidate alternatives

### A1 — Overload workstreams as code-area lanes

Re-cut workstreams so each names a non-overlapping code surface; "parallel-safe" becomes a side effect of the partition.

**Rejected at this stage.** Breaks DEC-018's semantic. Workstream renames/merges/splits would break the lane partition for ephemeral reasons. Adopters whose code does not partition by topic cleanly (cross-cutting libraries, monorepos with mixed concerns) have nowhere to land.

### A2 — `lane:<area>` label series + one-in-flight rule

A new label series, parallel to but distinct from `workstream:<slug>`. Each label names an ephemeral lock domain (file area, deployment target, fixture set — adopter's call). Lifecycle rule: at most one in-flight issue per lane.

**Covers:** code-surface conflict.
**Does not cover:** sequence conflict.
**Cost:** new label series; lifecycle scripts (`add-lane`, `rename-lane`, …) mirroring DEC-018's eight; in-flight detection (probably: open + assignee non-null, or open + linked draft PR).

### A3 — Typed `Blocked by:` body line + graph validation

Promote `Blocked by:` from prose to a typed line inside the `## Dependencies` section, with a fixed shape the validator can parse (`Blocked by: #<N>` or `Blocked by: <owner/repo#N>` cross-repo). The validator + lifecycle scripts (close, reopen) consult the graph.

**Covers:** sequence conflict.
**Does not cover:** code-surface conflict.
**Cost:** body-format schema extension; validator update; an `unblocks` op surfaced on close.

### A4 — Both A2 + A3 + `pkit pm parallel-status` command

The combined primitive: lanes (code-surface) + typed Blocked-by (sequence) + a reporting command that reads the current state (open issues, lanes occupied, blocked-by graph) and surfaces the **ready frontier** — the set of open issues that are unblocked AND whose lane is free.

**Covers:** both conflicts; gives the orchestrator a single query for "what is safe to start now."
**Cost:** the highest. New label series + body-format extension + new command + same-PR migration.

### A5 — Status quo: diligent body discipline + manual coordination

Adopters use the existing `## Dependencies` section diligently. Parallelisation discipline is project-local convention; no capability-level surface change.

**Why it stays in the candidate list:** it is the implicit baseline. The proposal must justify the cost of adding a primitive against just running the discipline manually for longer.

## Recommended direction (tentative — to refine in exploration)

**A4 as the destination + Direction X with `lane` on terminology, A5 as the bridge.**

Concretely, the destination primitive is:

- New `lane:<slug>` label series, additive to DEC-018's workstream taxonomy. One in-flight issue per lane is the lock rule. Lifecycle scripts mirror DEC-018's pattern but probably with a leaner set (lanes are ephemeral by intent).
- DEC-018's `workstream` semantic stays unchanged — categorisation, portfolio-scale where boards exist.
- Typed `Blocked by: #N` line inside the `## Dependencies` body section — validator-parsed; consulted by close + reopen.
- A reporting command (`pkit pm next` or similar) that reads lane-occupancy + Blocked-by graph and surfaces the **ready frontier**.

This project will run **A5 manually** while authoring the primitive — capture the discipline that works in practice, watch where the prose substrate breaks, then crystallise A4 from the lived evidence.

The empirical record collected during the A5 phase becomes the *Rationale* and *Implications* sections of the eventual DEC. This follows the DEC-018 pattern: real adoption surfaces the gaps, then the decision pins the contract.

## Open questions to refine before crystallising

1. **Lane attribute model.** Mirror DEC-018's 5-attribute shape (slug / name / description / status / deprecated_reason), or keep lanes lighter (slug + description only)? Lanes are more ephemeral than workstreams — maybe a leaner model.
2. **In-flight state.** Computed from what?
   - issue state machine (`in_progress`)?
   - presence of a linked draft PR?
   - non-null assignee?
   - explicit `in-flight: true` label?
   Each has different reliability + ease of mutation.
3. **Could lane lock project onto `assignee` instead of a new label?** GitHub natively enforces no two issues with the same assignee being "first in line." Tempting reuse; risk is overloading assignee for a different semantic.
4. **`Blocked by:` validation shape.** What patterns does the validator accept — `#N`, `owner/repo#N`, both? How does it interact with native sub-issues (a child of an unclosed parent is implicitly blocked; should we even need to type it)?
5. **Cardinality.** One lane per issue (mirrors workstream's mutual-exclusion), or multi-lane (an issue that touches two code areas locks both)? Multi-lane gives accurate locking but explodes the "is anything ready?" query.
6. **Ready-frontier command shape.** `pkit pm parallel-status`? `pkit pm next`? `pkit pm frontier`? What output — table, JSON, both?
7. **Interaction with milestones / time-containers** ([project-management:DEC-???] time-containers): does a milestone gate the parallel frontier (i.e. issues outside the current milestone are excluded from the ready set)?
8. **Cross-repo dependencies** (DEC-022 methodology-mesh): does the Blocked-by graph cross repo boundaries? If yes, how does `parallel-status` resolve cross-repo state?
9. **Lifecycle ops on lanes.** Do lanes need the full eight verb-subject scripts that workstreams have (DEC-018), or can a leaner set suffice (`add-lane`, `remove-lane`, `list-lanes`, `show-lane` — no rename/merge/split because lanes are ephemeral by intent)?
10. **Discipline-first evidence — what is the success criterion for promoting from A5 to A4?** How many parallel-issue weeks of operation count as enough lived data?
11. **Lane axis placement.** Does `lane` join DEC-012's classification axes as a fourth axis (type, priority, workstream, lane), or live outside the classification model as a "lifecycle marker" (similar to milestone in spirit — orthogonal to the axes)?
12. **Lane lifecycle scope.** Do lanes need the full eight verb-subject scripts of DEC-018 (add/rename/merge/split/edit/remove/show/list), or a leaner set (`add-lane`, `remove-lane`, `list-lanes`, `show-lane`) reflecting their ephemeral nature? Per COR-007, ship the leaner set and let recurrence force the rest.
13. **In-flight detection in board mode.** Label-substrate adopters can detect lane occupancy from `lane:*` labels on open issues. Board-substrate adopters might use a board-state field instead. Does the primitive support both, or does it require label substrate? (Most likely: label-substrate-only, since lanes are ephemeral and label substrate is the lighter-weight choice — even when other classification axes live on the board.)

## Notes on this project's A5-phase discipline

While the primitive is being designed, this project runs a manual convention. Internally we speak Direction X vocabulary — *"the workbench lane is occupied"* means a code-area lock; *"the Spyre workstream"* (when relevant) refers to the org-board categorisation. The lived experiment validates the lane vocabulary too.

- Use `## Dependencies` body section with a `Blocked by: #N` line per dependency, one per line. (No tooling enforces this; the discipline is the experiment.)
- Treat code-area locking informally: at most one in-flight issue per recognised area (`workbench`, `gateway`, `recorder`, `replay`, `agent-run`, `examples`). Worktree branch naming carries the area informally (`feat/<n>-<area>-...`).
- IGW is **board-substrate** with `workstreams: []` locally — the workstream taxonomy lives at the org Team Planning board (see `declarative-pm-hooks.md` for IDs). Internally we treat workstream as a portfolio-categorisation field set on the board; lanes are the local parallelization concept and live only as discipline today (no label or YAML yet).
- When a parallel collision happens (or almost happens), capture it as an entry in this scratchpad's `## Field notes` section below. Those entries are the empirical input for the eventual DEC.

## Field notes

*Entries added as the discipline runs. Each entry: date, situation, what the primitive should have caught.*

— (empty until the first incident or near-miss)
