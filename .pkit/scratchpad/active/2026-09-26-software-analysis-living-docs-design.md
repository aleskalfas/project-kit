---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-09-26
---

# Software analysis and living documentation — capability design

## The question

How should pkit ship two opt-in capabilities — **software-analysis** (durable, checkable knowledge about a project's software) and **living-docs** (documentation kept true against that knowledge, the code, decisions and sources) — so that they work both for projects that plan and build through pkit and for projects that don't (Mockingbird's case), catch the drift humans inevitably leave behind, and let an agent repair it?

Tracked by #951 (Milestone 5; EPICs #885 and #234). Retires as produced by the two capabilities' founding records.

## Inputs

- **#949** — Mockingbird's hand-off: invariants I1–I5 / T1–T2, three anchors of truth (code, decision, source), two documentation spaces by audience, method kept apart from content, the foundation rule set CMN-001…008 ("decisions cause rules; steps cause data"), the software-analysis / living-docs split joined by slots, a first-class internal-docs root (R3), a lightweight rule-list form, open questions (§10).
- **EPIC #234's earlier design** — `2026-06-20-documents-registry-and-onboarding.md` (docs registry with declared intent, reusing the workstreams registry shape; living-documents rules widened to project docs; brownfield onboarding) and `2026-06-20-igw-docs-consolidation-audit.md` (manual spike). Carry-overs: **propose with cited evidence, never auto-apply**; doc status is rarely binary.
- **The multi-clone coordination walk** (`2026-09-24-multi-clone-coordination-arc.md`) — where the need for durable use cases was first felt: walking nine situations through a design found gaps two reviewer passes missed.
- **The first software-analysis draft** (PR #945, draft) — per-design use-case sets; superseded by the model below, but its seams-crossed trigger, append-only numbering, mandatory gap log, and "sets live outside the capability so uninstall cannot delete them" still stand as candidates.

## Settled so far (session 2026-09-25/26)

1. **Two capabilities joined by slots, not a dependency.** software-analysis *produces* knowledge (actors, use cases, glossary); living-docs *consumes* it and keeps documentation spaces true. living-docs declares slots (readers + needs, anchors) that plain project files or software-analysis fill; living-docs never names a provider.
2. **Use cases are product knowledge** — an actor's goal and the path to it, true of the product for as long as it supports it; one id each; durable; revalidated when the software changes. *(Replaces the per-design sets of the first draft.)* Membership test for software-analysis (#949): *an artefact belongs here if a change to the software can make it false and we want to find out when it does.*
3. **Change, walk.** A *change* is a proposed alteration of behaviour (adds, modifies or retires use cases). A *walk* validates the use cases a change touches against the proposed or actual system and records the gaps found. Walk records live in the repository and cite whatever carried the change — an EPIC when project-management is used, otherwise a pull request or a commit range.
4. **Truth runs downstream:** analysis → code → docs; decisions and sources carry the *why* for all three.
5. **Two perspectives, one mechanism.**
   - *Planned (forward):* change the analysis first, then the code, then the docs — each checked against its upstream.
   - *Drift (reactive):* someone changes code (or analysis, or a doc) without updating its dependants.
   - *Mechanism:* **anchors** (every downstream statement points at what makes it true) + **friction** (an anchor changed and something anchored to it was not revalidated since). Each use case carries a *last revalidated against* marker the check compares.
   - *Detection points:* on pull requests (CI over the diff), on a schedule (full sweep), locally on demand.
   - *Resolution:* an agent proposes one of two outcomes — **analysis stale** (the change was intended: update the use case, then the docs) or **code regressed** (the use case still holds: report a defect) — and a human confirms when ambiguous. Never rewrite the analysis silently to match broken code.
   - A planned walk and a post-drift revalidation are the same act, triggered before or after the code; one record shape covers both.
6. **Nothing depends on project-management.** pm enriches both capabilities when installed (e.g. mirroring a walk onto an EPIC's timeline).

## Vocabulary (working)

| Term | Meaning |
|---|---|
| actor | a named role that uses the system |
| use case | an actor's goal, main path, variants, done-criteria; anchored; revalidated |
| glossary entry | a domain term and its meaning |
| change | a proposed alteration of behaviour |
| walk | a validation pass of a change's use cases; records gaps |
| anchor | what makes a statement true: code, a decision, a source (for docs: also a use case) |
| friction | an anchor changed; a dependant was not revalidated since |
| space | a documentation space with its own audience, entry point and definition |
| slot | a named input a capability declares and another source fills |

## Open questions — to resolve one at a time, in this order

Order follows dependency: where things live → how rules are written → how capabilities connect → how truth is checked → formats → the rest.

1. **Internal-docs root.** A first-class, configurable root (and a user-docs root) that both capabilities derive their locations from — #949 R3. Extend today's per-category overlay placeholders, or a new top-level setting? Default path; dotfolder or not; relation to decision/ADR locations.
2. **Foundation rule set placement.** CMN-001…008 govern analysis outputs as much as docs — a shared foundation (core? a third capability?) or inside living-docs?
3. **Lightweight rule-list form and its statuses.** One paragraph + one Origin line per rule alongside four-section records; borrow proposed/accepted/superseded and supersession; how they render in a list; how rule ids relate to existing id-spaces.
4. **Evidence for rules.** Is an Origin line an inline evidence record, or do rules cite `[ev:…]`?
5. **Slot mechanism.** Existing overlay placeholders, capability dependencies, adopter data references — or a new provides/consumes declaration?
6. **Anchor syntax and the friction check.** How a use case / doc statement names its anchors (paths, symbols, commands, decision ids, evidence slugs) so a diff can be matched against them; granularity; cost on large repos.
7. **Formats for actors, use cases, glossary.** Fields, ids, file layout; what carries over from the first draft (append-only ids, gap log → walk record).
8. **Walk record.** Shape, location, how it cites its change; pm mirroring.
9. **Process substrate per documentation space.** Singleton per space or keyed per artefact; how "steps cause data" (CMN-002/004) maps onto process definitions.
10. **Reader-review.** An agent reviewing pages through a reader's eyes, and/or a run of the product (persona × task) — and how that relates to walking use cases.

## Decision log

*(Append one entry per resolved question: date, question, answer, alternatives rejected, who decided.)*

## Records this should produce (draft)

- software-analysis: a founding decision (artifacts, walks, anchors/friction, pm-independence, readers slot) — rewrites the draft on #886 / PR #945.
- living-docs: a founding decision (spaces, anchors, slots, reader-review, propose-never-apply).
- Wherever question 2 lands: the foundation rule set.
- Wherever question 1 lands: the internal-docs root (likely a core record or an amendment of the overlay records).

## Status

Active. Next: question 1 — the internal-docs root.
