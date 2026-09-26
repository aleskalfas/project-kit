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
| walkthrough | an event: checking use cases or journeys against a version of the system (proposed design or actual code); its report is a walkthrough record |
| journey | an end-to-end path an actor takes across several use cases |
| user story | a need in one sentence (who / wants / so that): the actor's `needs` entry, a use case's Goal |
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

- **2026-09-26 — Q1 carrier: the backbone project config holds two documentation roots (option B).** `.pkit/project/config.yaml` gains a `docs` block (`internal:`, `user:`); the overlay's doc categories (`architecture-docs`, `adr-records`, …) default from the internal root and stay overridable; commands, capabilities, CI and agents all derive from one source. Rejected: two new overlay categories (A) — the overlay is an agent-body substitution mechanism, and every non-agent reader would have to learn its resolution. Needs a core record (two documentation roots by audience) with refinement notes on COR-013 (overlay defaults) and COR-025 (ADR location default); a schema for `.pkit/project/config.yaml` (cf. #689). Decided by Aleš Kalfas.
- **2026-09-26 — Activation model.** The `docs` block is a backbone concept, independent of any capability: optional to declare, absent ⇒ conventional defaults; read always by the backbone (overlay defaults, ADR stamp location, `pkit status` shows resolved roots and their source); read by software-analysis / living-docs when installed. A capability never writes the block silently — on install / first run it shows the resolved roots and offers to record them; uninstall never removes it. Decided by Aleš Kalfas.
- **2026-09-26 — Existing projects: record, don't move.** The upgrade migration only makes the current layout explicit (writes the `docs` block reflecting what exists, creating `.pkit/project/config.yaml` if absent); nothing moves, every existing path keeps working. Moving ADRs (and other docs) into the internal root happens as part of living-docs onboarding, proposed per file with its reason, link rewrites and unrewritable references, human-confirmed, landed as one reviewable PR in the adopter's own session. Rejected: an automatic move on upgrade — acts on project-owned content, breaks links outside the repo, and cannot judge ambiguous files. Decided by Aleš Kalfas.
- **2026-09-26 — Brownfield onboarding is transformation, driven by friction detection.** Onboarding is not a separate process: it is friction detection on a project where nothing is anchored yet — every statement is friction on day one. An agent transforms rather than moves: derives actors / use cases / glossary from the code and existing docs (brownfield reverses the planned order: code → analysis first), anchors or challenges each statement (true → anchor; stale → fix; unanchorable → human question), and rewrites pages for their readers into their spaces. Tooling is deterministic (detection, bookkeeping, validation); interpretation is agentic; judgments ("analysis stale or code regressed", "which space") are human-confirmed. Onboarding is complete when friction reaches zero, and the same mechanism keeps it there. Carry-over from EPIC #234's spike: propose with cited evidence, never auto-apply. Decided by Aleš Kalfas.

- **2026-09-26 — Q1 defaults: both roots default to `docs/` (unsplit).** A project that declares nothing resolves exactly as today (derived `adr-records` = `docs/architecture/decisions/`), so the record-only migration mostly writes nothing. *Separation of concerns:* the backbone knows *that* two audience roots may exist and where; *why* to separate them (I4 — each page serves a known reader; users never meet internal material) is a documentation rule, so the rule and the recommended split layout live in **living-docs' founding decision**, applied when a project adopts living-docs. Rejected: `tech-docs/` default (the backbone would enforce a living-docs rule without the capability, and break every undeclared project's derived ADR path); `.docs/` dotfolder (same breakage, and hides what developers must review). Decided by Aleš Kalfas.
- **2026-09-26 — project-kit is the first adopter**, ahead of Mockingbird. It has user-facing docs (`README.md`, the CLI reference, adopter-facing area READMEs) mixed with maintainer-only material (`CONTRIBUTING.md`, the COR corpus, scratchpad) — the same brownfield shape. Dogfooding here finds rough edges before Mockingbird adopts. Decided by Aleš Kalfas.
- **2026-09-26 — Q2 foundation rules: split by nature, no third capability (option A).** The CMN set is three layers, not one. *Rule machinery* (CMN-001 inheritance + extension points, CMN-006 permanent ids, CMN-007 root by decision, CMN-008 origin line) extends the **core decision system** — its missing pieces (a lightweight form, extension points) are Q3. *Causality of data* (CMN-002 nothing without an input, CMN-003 every artefact names its cause, CMN-004 the process is the index) is a principle both capabilities apply through the **core process substrate** — mapping is Q9. *Documentation-specific* (CMN-005 README as signpost) goes to **living-docs**. Mockingbird's rules survive as content: living-docs' shared space definition, citing the core pieces rather than restating them. Rejected: a third foundation capability (re-implements ids/statuses/steps beside core's, and turns slots back into a hard dependency); everything inside living-docs (software-analysis would depend on it or duplicate it). Decided by Aleš Kalfas.
- **2026-09-26 — What rules are, and who provides them.** A *rule* is a statement every artefact in its scope must satisfy, caused by a decision, checkable by a tool, an agent or a reviewer. Not a decision (which chooses and records why), not a template (a starting shape), not a schema (the mechanically checkable subset of some rules). Needed for: (1) instructions a writing agent follows; (2) criteria checks and reviewers judge against; (3) citations in findings, and finding what relied on a retired rule; (4) inheritance and extension across spaces and projects. Two kinds: **method rules** (ship with a capability, versioned with it) and **project rules** (adopter-owned, extend method rules at declared points, survive upgrades). **pkit's backbone provides the rule machinery** (ids, origins, statuses, supersession, inheritance, validation) — both capabilities use it; neither re-implements it. Confirms Q2's placement of rule machinery in core. Decided by Aleš Kalfas.
- **2026-09-26 — Q4 evidence: origins stay inline and may cite evidence; everything checkable is checked deterministically (option A).** Evidence is the provider of the *source* anchor for doc statements, use cases and rule origins; through the anchors slot, so neither capability requires it (plain links otherwise). A rule's origin keeps its quote inline and may cite `[ev:slug]`. **Deterministic gates** (check gate: pre-commit, CI, every PR): every rule has an origin; the origin has date + who + a reason, or "proposed and accepted", or a decision-record citation; a cited `[ev:slug]` resolves (exists: evidence validate); the evidence record has its required fields (exists); a cited decision record exists and is accepted when the rule is (partly exists: refs validate + new status check); rule ids unique, never reused, supersession targets exist; optional per-project strictness: origins must cite evidence. **Not deterministic** (agent / reviewer): that an excerpt really appears at its source (tool can check against a stored snapshot; online re-fetch opt-in only), and that a quote supports its rule. Gap noted: quotes from working sessions need a durable capture (issue comment, PR, committed note) to be citable. Rejected: every origin as a separate evidence record (splits reason from rule, kills readability); evidence left out (source anchors would be reinvented). Decided by Aleš Kalfas.
- **2026-09-26 — Q3 rule-set form: front matter holds the data, the body holds the prose (option B).** One file per rule set. YAML front matter: `rule-set` (permanent prefix), optional `inherits`, and a `rules:` map keyed by id carrying the machine fields — `status` (absent = accepted; `proposed`; `superseded` + `superseded_by`), `origin` (`decided`/`proposed` date, `by`, `reason` quote, optional `evidence` slug, or a decision-record citation), `fills` (extension points filled). Markdown body: one `## <ID> — <title>` section per rule with its statement, and extension points declared in prose on the rule that offers them (to be decided whether they also get a data field). Validated with pkit's existing data machinery (JSON Schema companion per COR-018, bound via COR-022), plus a join check: every body rule has data and every data entry has a body rule. Rule ids permanent, never reused; superseded rules stay in place. Method rule sets ship in a capability; project rule sets live under the internal docs root. Rejected: markdown conventions parsed by regex (fragile — the class of bug behind the issue-body parser failures); all-YAML with a generated view (build step, drift, poor for prose). Needs a core record: the rule-set kind, its schema and validator, and the rule-id space in the id checks. Decided by Aleš Kalfas.
- **2026-09-26 — Q5 slots: a backbone slot primitive generalising the existing contribution pattern (option A).** pkit already runs the pattern three times — reviewer contributions (pm DEC-032), privilege fragments (ADR-021), label contributions — each: the consumer owns an interface, providers drop a declaration in their own subtree, a collector walks installed components. The primitive: a consumer declares a **slot** (name + schema, e.g. `living-docs:readers`, `living-docs:anchors`); **fillers** are (1) a project-owned file under the internal docs root (always available) and (2) any installed capability declaring it fills the slot, mapping its own richer model onto the slot's shape; the backbone resolves and validates the filled data. What differs from the three existing sockets: **no dependency in either direction** — a filler declaration for an absent consumer is inert, and a consumer with no capability filler falls back to project files. The existing sockets may migrate onto it later (not in scope). Rejected: schema namespaces as slots via COR-029 data references (forces the provider to store its data in the consumer's format); bespoke per-pair provides/consumes (the fifth copy of the same pattern). Needs a core record + backbone code. Decided by Aleš Kalfas.
- **2026-09-26 — Q6 anchors: per artefact, in front matter (option A).** Every anchored artefact (use case, doc page, and later other analysis artefacts) carries `anchors:` — `code` (paths/globs; symbols a later refinement if path-level proves noisy), `decisions` (record or rule ids), `sources` (evidence slugs), and for docs `use-cases` / `glossary` — plus `revalidated: <commit>`. **Friction** = any anchor changed in git between `revalidated` and now: one `git log` per anchor; no database. On a PR the check runs over the diff and lists anchored artefacts not revalidated in the same PR (bumping `revalidated` after actually checking clears it); on a schedule it runs repo-wide against HEAD. Inline citations (`[ADR-004]`, `[ev:slug]`, `[UC-012]`) stay available where a page mixes sources but are not required. Precision comes from the agent's resolution step (reads the flagged artefact against the actual diff and narrows to the statements), not from tagging every sentence. Resolution order follows the truth chain: upstream first (use case), then downstream (pages). Known limit: a marker bumped without real checking — caught by the walk record and review, not by a tool. Rejected: per-statement inline anchors (maintenance cost makes people stop — recreates the drift); per-section hidden markers (a second convention, parsed from prose). Decided by Aleš Kalfas.
- **2026-09-26 — Q7 formats and layout (RUP-inspired).** Borrowed from RUP's Requirements discipline: actors and use cases are **one** Use-Case Model; the Glossary serves everything and sits outside it; a Supplementary Specification (constraints / quality) is a later module. Layout under the internal docs root:
  ```
  analysis/
  ├── glossary.md                 collection file: front-matter map keyed by stable term id
  └── use-case-model/
      ├── actors.md               collection file: front-matter map keyed by actor id; fills living-docs' readers slot
      ├── UC-NNN-<slug>.md        one file per use case, flat while small
      └── <package>/UC-NNN-….md   optional functional-area packages when the model grows
  ```
  **Use case** front matter: `id` (UC-NNN, global — moving between packages never changes it), `status` (`active` | `withdrawn`: file kept, number never reused), `actor`, `anchors`, `revalidated`; body: goal, starts-when, main path, variants, done-when. **Actor** entry: `needs`, `anchors`, `revalidated`; body section per actor. **Glossary** entry: stable id separate from display term, `replaces:` for old names (a rename flags pages still using the old word), `anchors`, `revalidated`. Folders appear only when something goes into them (CMN-002). Carried over from the first draft: append-only numbering, withdrawal over deletion, seams-crossed as the guidance for when a change needs a walk; the per-design gap log moves into the walk record (Q8). Rejected: flat `analysis/` (actors and glossary lost among many use cases, no place for packages or modules); one file per artefact everywhere; one collection file for use cases. Decided by Aleš Kalfas.
- **2026-09-26 — Terms and layout refined: walkthrough, journeys, grouping rule.** (1) The activity formerly called *walk* is a **walkthrough** (IEEE 1028 review type; "use-case walkthrough"), its report a **walkthrough record**. (2) **User story vs use case vs walkthrough:** a user story is a *need* in one sentence (who / wants / so that) — in this model the actor's `needs` entry and a use case's Goal line; a use case is how the system fulfils it (durable, anchored); a walkthrough is an *event* checking use cases or journeys against a version of the system — test requirement / test specification / test run. (3) **Journeys** join the use-case model: an end-to-end path an actor takes across several use cases (#949's I5 user paths). One file per journey, `JRN-NNN-<slug>`, global append-only ids, `actor`, ordered `steps` (use-case ids), anchors (its use cases + the code at the seams between them), `revalidated`, starts / done-when / seams to watch. A changed use case flags the journeys through it, in truth-chain order. (4) **Grouping rule:** a kind with many files gets its own folder; a singleton kind is a file. Layout:
  ```
  analysis/
  ├── glossary.md
  ├── use-case-model/
  │   ├── actors.md
  │   ├── use-cases/UC-NNN-<slug>.md  (+ optional <package>/ subfolders)
  │   └── journeys/JRN-NNN-<slug>.md
  └── walkthroughs/<date>-<slug>.md
  ```
  Decided by Aleš Kalfas.
## Reference adopter — Mockingbird (read-only observation, 2026-09-26)

- `docs/` mixes two spaces: user-facing (`guides/`, `EVALUATION.md`, `CLUSTER_ONBOARDING.md`, `INSTALL_ENV_CACHE.md`, `assets/`) and technical (`architecture/decisions/ADR-001…009`, `ARCHITECTURE.md`, `CONTRIBUTING.md`, `RELEASING.md`, `BUILDING_IMAGES.md` — the last possibly serving operators too: a human call).
- `tech-docs/.meta/` holds the hand-built method (CMN rules, two space definitions); `tech-docs/` data is nearly empty.
- Overlay: `adr-records: docs/architecture/decisions/`, `architecture-docs: README.md`; no `.pkit/project/config.yaml` yet — created by the record-only upgrade migration.
- Target: `docs.internal: tech-docs/`, `docs.user: docs/`; onboarding proposes the split and the transformation.

## Records this should produce (draft)

- software-analysis: a founding decision (artifacts, walks, anchors/friction, pm-independence, readers slot) — rewrites the draft on #886 / PR #945.
- living-docs: a founding decision (spaces, anchors, slots, reader-review, propose-never-apply).
- Wherever question 2 lands: the foundation rule set.
- Wherever question 1 lands: the internal-docs root (likely a core record or an amendment of the overlay records).

## Status

Active. Q1–Q7 decided; walkthrough/journeys/grouping refined. Next: Q8 — where walkthrough records live (option A offered: a file only when planned or when gaps/regressions are found; routine clean revalidation = the `revalidated` bump in its commit).
