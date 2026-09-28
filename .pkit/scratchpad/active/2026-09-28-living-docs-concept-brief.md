---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-09-28
---

# Living documentation — the concept, as concluded

## What this note is

The answer to the hand-off that started this work: [#949](https://github.com/aleskalfas/project-kit/issues/949), in which Mockingbird's documentation rewrite produced a set of invariants and rules for keeping documentation true, and asked for them to live once in pkit rather than be copied between repositories. Between 2026-09-26 and 2026-09-28 project-kit worked the hand-off through to accepted records and an implementation plan. This note states **what was concluded about how living documentation should work** — as a concept, independent of any tool — and pairs every idea with what pkit provides, so that a presentation of the concept arrives at pkit as its last link rather than its first.

It is written for whoever builds that presentation, including another assistant session that receives only this link. Everything it states is decided in the records listed at the end; where it says *shipped*, *in review* or *planned*, that is a snapshot of 2026-09-28 — the live state is on [Milestone 5](https://github.com/aleskalfas/project-kit/milestone/6).

It retires into project-kit's first user-facing concept page, once the living-docs capability ships its page templates — and that page then becomes the first document the concept itself keeps true.

## The story in one breath

The hand-off presented its case as a causal chain and named pkit only at the last link. The chain still holds; the conclusions sharpen each link.

1. **Documentation is about to carry real weight, and an agent can write it.** Written without rules, it is fluent and untrustworthy: wrong, repeated, aimed at nobody, stale after the next change.
2. **A statement is true only against something** — the code it describes, a decision, a captured source, or the product knowledge it builds on.
3. **So every page says what makes it true, and a check notices when that changes.** The answer to the change is recorded in the page itself, not remembered by people.
4. **Pages serve declared readers**, in spaces kept apart by audience, and follow a method that is written down as named, checkable rules.
5. **People skip manual steps**, so agents do the work, checks verify it, and a person reviews what the agent proposes. That only works if the method is explicit and the checks are deterministic.
6. **Product knowledge sits upstream**: what the software must do is kept true first, then the code, then the documentation.
7. **The need is the same in every repository; only the content differs.** The method and the machinery belong in one shared place that every project installs — which is what pkit is.

## The problem — the opening evidence

A real documentation spike in a sibling project ([the consolidation audit](https://github.com/aleskalfas/project-kit/blob/main/.pkit/scratchpad/active/2026-06-20-igw-docs-consolidation-audit.md)) found, among others:

- one topic split across two documents, the second mirroring the first section by section;
- an integration guide re-documenting a tool another document owns, including a byte-identical copy;
- a guide claiming "four modes" while its own table — and the owning document — listed three;
- one page saying a key is required with no fallback, another saying the same key falls back;
- three sections in one file with the same heading, so cross-references were ambiguous.

None of these is exotic, and review does not catch them: a review looks at the change in front of it, and the stale page is somewhere else. The usual remedies fail for structural reasons:

- a **"documentation impact" checklist** on each change depends on the author remembering which pages exist;
- a **map from code paths to documents** is a guess made from the code's side; broad entries fire on most changes, so people stop reading them;
- a **registry of documents** has to be maintained as carefully as the documents it lists (project-kit tried this model first, in [June](https://github.com/aleskalfas/project-kit/blob/main/.pkit/scratchpad/active/2026-06-20-documents-registry-and-onboarding.md), and replaced it).

## The concept — eleven ideas

Each idea: what it says, why it is this way, which part of the hand-off it answers, and what pkit provides.

### 1. Documentation lives in spaces, one per audience

- **The idea.** A *space* is a body of documentation with one audience, one entry point and one definition of how its pages are made. Every project has at least a **user space** (what the system does and how to use it) and a **technical space** (why, from where, by which rules — for maintainers and for the agents that write and check the docs). A project may add others, such as an interface reference.
- **Separate, not secret.** User-facing navigation and search never lead into technical material. The technical space is in the same repository and visible to anyone; the separation is audience and entry point.
- **Which space a page belongs to.** The user and technical spaces each have a root folder; files outside the roots (a top-level README, a contributing guide) are assigned to a space explicitly; where places nest, the most specific wins. Decision records and rule sets inside a space are what pages *rest on*, not pages themselves.
- **Why.** A user who meets maintainers' material is lost; a maintainer who cannot find the grounds of a user page cannot keep it true; and the writing agent gets a checkable boundary instead of a judgement call.
- **Answers:** hand-off §4 (two spaces), invariant I4, requirement R1, R3.
- **In pkit:** two documentation roots declared once per project (user and internal, both `docs/` until a project splits them); every location the method or a capability chooses derives from the right root and is recorded the first time it is used, so a later change never moves existing files. *Shipped.* Place assignment and precedence are decided; applied by the living-docs capability (*planned*).

### 2. Every page says what makes it true

- **The idea.** A page lists its *anchors*: the code it describes (files or patterns), the decisions and rules it applies, other artefacts it builds on (a use case, another page), and captured sources. Anchors are per page, not per sentence; the reviewer — person or agent — connects each statement to the page's anchors.
- **Why per page.** Anchoring every sentence is precise and so expensive to maintain that people stop, which recreates the drift. Per page keeps the cost bearable; precision comes from whoever revalidates the page against the actual change.
- **Unanchored is visible, not an error.** A page with no anchors is counted and shown, so a project sees how much of its documentation rests on nothing.
- **A link to nothing is an error.** An anchor that points at a path, decision or artefact that no longer exists is reported, never silently ignored — silence would look like health.
- **Answers:** invariant I1 and "truth has three anchors" (code, decision, source); rule CMN-003 (every artefact names its cause).
- **In pkit:** a small block in the page's front matter, three core anchor kinds (paths, identified records, other artefacts) with room for capabilities to add kinds (sources), strict validation of the block. *Shape and validation shipped.*

### 3. Drift is detected, not remembered

- **The idea.** When anything a page rests on changes, the page is flagged — this is *friction* — until someone revalidates it. The check runs on every change (a pull request, or locally before committing) and across the whole repository. It reports upstream first: what others depend on is rechecked before what depends on it.
- **Why.** Only a check that fires at the moment of the change is reliable; it tells the author "you changed what this page rests on" when the fix is cheapest. The whole-repository check shows what was already stale.
- **How strict is a project's choice.** In *warning* mode the check reports; in *enforcing* mode a change that leaves friction behind fails its check, and cannot merge where the project requires that check. A project turns enforcement on when it trusts its anchors.
- **Answers:** invariant I1 ("when an anchor changes, everything pointing at it is found and re-checked").
- **In pkit:** the change check, a whole-repository check, warning and enforcing modes, wired into any CI as a required status. *Change check in review; whole-repository check planned.*

### 4. The answer lives in the page, not in the pull request

- **The idea.** Friction is answered in the page itself, in one of three ways: **updated** — the page changed with the revalidation; **still true** — the page did not need to change, with one sentence saying why it holds against *this* change (a new sentence every time, so a blind "yes" is visible); or **deferred** — postponed for one anchor, with a reason; each revalidation either keeps the postponement deliberately or drops it, and a later change to the same thing is new friction.
- **Why.** A pull-request description is one tool's format; a change made by another tool, by hand, or checked locally has none. An answer in the page works everywhere, and the next reader finds the justification next to the thing it justifies.
- **Debt comes from history.** What is stale and what is deferred — with who, when and in which change — is derived from the repository's history, never kept in a separate ledger that would drift from it.
- **Answers:** new since the hand-off; it closes the gap between "re-checked" and "recorded that it was re-checked".
- **In pkit:** the revalidation record in the page's front matter, commands to revalidate and to defer, a debt listing. *Shape shipped; commands planned.* A work-tracking tool may *render* the answers into its pull-request template — it never reads the template instead of the pages.

### 5. Every page is written for a declared reader

- **The idea.** A project declares its readers and what each needs (by default: a *user* and a *maintainer*). Each page names its reader and its kind, and says only what that reader needs. A *reader-review* reads the page as that reader and reports what they would miss or not need.
- **The product can test its own docs.** Executed checks — a simulated user following a guide against the running product — are evidence the review uses, not something the documentation method runs itself. (For Mockingbird this is the product doing what it is for: persona × task over its own docs.)
- **Readers can come from the product analysis**: the actors and their needs (idea 9) are the readers, when a project keeps that analysis.
- **Answers:** invariants I4 and I5; hand-off §10 "reader-review as an agent vs as a run of the product" — both, in these two roles.
- **In pkit:** declared readers with the two defaults, fillable by the analysis capability; a reader-review agent; executed results arriving as reading evidence. *Planned.*

### 6. The method is written down as named, checkable rules

- **The idea.** A *rule* is a statement every artefact in its scope must satisfy, caused by a decision, checkable by a tool, an agent or a reviewer. Rules have permanent identifiers, never renumbered or reused; each records its origin — when, by whom and why, in the decider's words, or a decision record that says it at length. A rule is **proposed** until accepted, and a proposed rule binds nothing; accepted rules bind; superseded and withdrawn rules stay in place with their ids.
- **Extend, never relax.** A project inherits a shared rule set and adds its own rules, or fills the extension points a shared rule offers; it cannot contradict or quietly override an inherited rule. Inheriting someone else's rule set pins its major version, so a tightened rule never arrives unreviewed. A page may anchor to a single rule, so changing, superseding or withdrawing that rule flags everything that relied on it.
- **Light enough to use.** One file holds a whole rule set: the data per rule at the top, each rule's statement as a short section below — not one formal record per rule.
- **The shared documentation method** (*LDOC*): a page's anchors ground every statement it makes; each fact is stated once and other pages link to it; each page names its reader and says only what that reader needs; pages of a kind follow one format, with a template per kind; an index-like file is a signpost to what a folder holds, never a summary; nothing is created ahead of the need for it; and in the user space, the reader paths stay unbroken.
- **Answers:** rule T1; invariants I2, I3; rules CMN-001, CMN-006, CMN-008; hand-off §6 "a lightweight rule-list form".
- **In pkit:** rule-set files with a schema, deterministic checks of ids, statuses, origins, successors and inheritance, citable rule ids; the LDOC set ships with the documentation capability. *Rule sets in review; LDOC planned.*

### 7. The method is kept apart from the content

- **The idea.** Content is what the project knows — its pages, its readers, its product knowledge. The method is how pages are made from it — the rules, templates and space definitions. Each space's definition lives in the technical space; the shared method names nothing project-specific.
- **Why.** A method written once can change in one place and apply to every project; a method mixed into content can never be separated again.
- **Answers:** hand-off §5, requirement R4.
- **In pkit:** the method (LDOC, templates) ships with the documentation capability and upgrades like any installed component; the project's content and its own rules are never touched by an upgrade. *Planned.*

### 8. Fixes are proposed, never applied blind

- **The idea.** An agent resolves friction by *proposing* the change to the page, citing the change that caused it and the anchors it rests on; a person reviews it through the project's usual approval path. A statement the page's anchors do not ground is grounded by a new anchor, taken out, or raised as a question — never left standing as if it were true.
- **Why.** An agent that rewrites pages directly will eventually rewrite them wrongly — misjudge a file's audience, or "fix" a page to match a bug. Proposals with evidence keep the speed and keep the judgement.
- **Answers:** hand-off §5 "agents do the work, checks verify it"; the earlier spike's lesson "propose with cited evidence, never auto-apply".
- **In pkit:** the documentation capability's agent; every proposal lands as a reviewable change. *Planned.*

### 9. Truth runs downstream: product knowledge, then code, then documentation

- **The idea.** What the software must do — its **actors** (who uses it, with their needs), **use cases** (an actor's goal and how the system fulfils it), **journeys** (an end-to-end path across use cases) and **glossary** — is kept as anchored artefacts too. It is revalidated before a change (planned) and after one (friction). Documentation anchors to it; a changed use case flags the pages built on it.
- **Stale or regressed.** When code and a use case disagree, either the change was intended (the use case is updated, then the docs) or the code regressed (the use case still stands and a defect is reported). The analysis is never rewritten to match broken code; when the intent is unclear, a person decides.
- **Membership test** (from the hand-off, kept): an artefact belongs to the product knowledge if a change to the software can make it false and we want to find out when it does.
- **Answers:** hand-off §7 (the software-analysis scope, "one use case, two consumers").
- **In pkit:** the software-analysis capability — the artefacts, their stamping and checks, revalidation records written only when there is something to say, and an agent that proposes the outcome. *Planned.*

### 10. Adopting on an existing project is a transformation, not a move

- **The idea.** On day one nothing is anchored, so "no friction" means nothing. The honest measures are **unanchored pages** and **uncovered surface** — the code the project says ought to be described and no page anchors to. An agent proposes which space each existing page belongs to, how pages should be split, merged or rewritten for their readers, which anchors each statement needs, and which existing code-to-document mappings become page anchors. Every proposal is reviewed; files move only as ordinary reviewed changes.
- **Done means** the declared surface is covered and no page is left unanchored without an accepted reason — and the same mechanism keeps it there.
- **Answers:** hand-off §9 (the migration shape of Mockingbird's layout).
- **In pkit:** the two measures in the whole-repository check; onboarding proposals by the documentation agent. *Planned.*

### 11. The pieces stay independent, and combine when present

- **The idea.** Documentation works with no product analysis and no work tracker; each enriches it when installed — the analysis supplies readers, the tracker asks each change what documentation it owes — and none depends on another. A piece is addressed by the *role* it plays, not by its name, so a different documentation implementation could replace the shipped one without anything else noticing.
- **Why.** A team that wants only part of it adopts only that part; and nobody is locked into an implementation.
- **Answers:** hand-off §7 "two capabilities joined by a slot, not a dependency", and its open question on the slot mechanism.
- **In pkit:** role-named connection points shared by every capability. *Resolver in review; the data connections planned.*

## Where each part of the hand-off ended up

| Hand-off item | Concluded | Decided in |
|---|---|---|
| I1 anchors — docs stay true after every change | ideas 2–4 | [COR-050][cor050] |
| I2 unified format | LDOC rule: one format per page kind, a template per kind; the page names its kind | [living-docs DEC-001][ld001] point 3 |
| I3 stated once | LDOC rule: each fact stated once, others link to it | living-docs DEC-001 point 3 |
| I4 readers | idea 5 | living-docs DEC-001 points 4, 6, 7 |
| I5 user paths | LDOC user-space rule; executed runs arrive as reading evidence | living-docs DEC-001 points 3, 6, 7 |
| T1 rules | idea 6 | [COR-051][cor051] |
| T2 causes | anchors: what a file rests on says why it exists — "the anchor graph is the index"; LDOC: nothing ahead of the need | COR-050; living-docs DEC-001 point 3 |
| Three anchors of truth (code, decision, source) | core kinds: paths, records, other artefacts; sources through a kind a capability registers | COR-050 point 2 |
| §4 two spaces, R1 | idea 1 | living-docs DEC-001 point 1; [COR-049][cor049] |
| R2/R3 a first-class internal root | two roots (user, internal), derived locations recorded on first use, roots outside the methodology's own folder | COR-049; [COR-048][cor048] |
| R4 method apart from content | idea 7 | living-docs DEC-001 point 2 |
| §5 rules CMN-001 inherit and extend at declared points | rule-set inheritance, extension points, no relaxing | COR-051 point 7 |
| CMN-002 nothing without an input | LDOC: nothing is created ahead of the need for it | living-docs DEC-001 point 3 |
| CMN-003 every artefact names its cause | anchors on every artefact; origins on every rule | COR-050; COR-051 point 5 |
| CMN-004 the process is the index | replaced: the anchor graph is the index | design log, 2026-09-27 |
| CMN-005 a README is a signpost | LDOC: an index-like file is a signpost, never a summary | living-docs DEC-001 point 3 |
| CMN-006 permanent rule ids, `ID:name` extension points | `RS-<SET>-NNN`, never reused; extension points written `#name` so they never clash with a namespace colon | COR-051 point 3 |
| CMN-007 the root exists by decision | the roots are declared in the project's configuration | COR-048, COR-049 |
| CMN-008 origin line | origin fields — when, who, why in the decider's words, or a decision record — checked deterministically | COR-051 point 5 |
| "Decisions cause rules; steps cause data" | the first half stands (origins); the second is replaced by anchors — a step-based process is kept only for real lifecycles such as a planned revalidation | design log, 2026-09-27 |
| §7 two capabilities joined by a slot | idea 11; readers are filled from the analysis, neither side names the other | [COR-052][cor052], [COR-053][cor053] |
| §7 where the CMN rules live | split by nature: the rule machinery and anchors in the shared core, the documentation rules in LDOC | design log, 2026-09-26 (Q2) |
| §10 statuses and supersession for light rules | proposed / accepted / superseded / withdrawn | COR-051 point 4 |
| §10 evidence for rules vs for data | origins stay inline and may cite a captured source | design log (Q4); COR-051 point 5 |
| §10 process substrate for doc steps | no — friction is a check over the anchors | design log, 2026-09-27 (Q9 reversed) |
| §10 default internal root, dotfolder or not; §8 "inside `.pkit/` is fine" for agent-maintained projects | the project chooses its roots (both default to `docs/`), but a root never lies inside the methodology's own folder, whoever maintains it | COR-049 point 1 |
| §10 reader-review: agent or product run | both: the agent reads, the product's runs arrive as evidence | design log (Q10); living-docs DEC-001 point 6 |
| §7 layers: foundation = decisions · evidence · causality rules | the foundation is the shared core — decisions, documentation roots, anchors and friction, rule sets, connection points; evidence is an optional provider of source anchors | COR-048 to COR-053 |
| §9 Mockingbird's `tech-docs/.meta/` | becomes the shared method (LDOC) plus each space's definition under the internal root; the planned `tech-docs/users/` becomes the product knowledge, under the internal root's analysis folder | [software-analysis DEC-001][sa001] point 2; living-docs DEC-001 point 2 |

## Why not build it in each project

Every idea above is universal, and none of the machinery behind it is trivial — nor does it differ between projects:

- **Strict validation of every file the method uses**, with "did you mean" messages: the configuration, each page's block, rule-set files, reader declarations.
- **Revalidation points derived from history** that survive file renames, squash merges and parallel branches, and a change check any CI can run without a database.
- **A rule system** with permanent ids, recorded origins, statuses, inheritance and version pins.
- **A connection model** that lets documentation, product analysis and work tracking enrich each other without depending on each other.
- **Agents that propose** and a review loop that keeps a person in charge.
- **Upgrades that reach every project**: the method improves once, every project receives it, and nothing a project wrote is touched.

A project keeps only what is genuinely its own: its content (pages, product knowledge, its own rules) and a few choices (where its two roots are, which files outside them belong to a space, what code ought to be described, warning or enforcing). The machinery is **dormant until used** — installing it costs nothing until the first page is anchored — and it can be adopted one piece at a time. That is the last link of the chain: **pkit gives every project this machinery for free, so each project writes only its content.**

## The proof: project-kit runs on it

project-kit is its own first adopter, ahead of Mockingbird ([ADR-055][adr055]): its user documentation root is `docs/` and its technical root `tech-docs/`; its architecture decisions have already moved under the technical root; the friction check runs in **enforcing mode from the day it exists**, because every page and anchor here is produced by the tooling under test; its first product knowledge will be the use cases of its own multi-clone coordination work; its existing code-to-document mapping is converted into page anchors during onboarding.

## Status on 2026-09-28

| Idea | State |
|---|---|
| 1 spaces and roots | roots *shipped*; place rules *decided*, applied with living-docs (*planned*) |
| 2 anchors | block shape and validation *shipped* |
| 3 friction | change check *in review* (together with project-kit's enforcing gate); whole-repository check *planned* |
| 4 answers in the page | shape *shipped*; revalidate / defer commands and the debt listing *planned* |
| 5 readers | *planned* |
| 6 rule sets | rule-set files *in review*; LDOC *planned* |
| 7 method apart | *planned* (ships with living-docs) |
| 8 proposals | *planned* (living-docs agent) |
| 9 product knowledge | *planned* (software-analysis) |
| 10 onboarding | *planned* |
| 11 independence | connection resolver *in review*; data connections *planned* |

All eleven are **decided** in accepted records. The live state is on [Milestone 5](https://github.com/aleskalfas/project-kit/milestone/6); the EPICs are [#974](https://github.com/aleskalfas/project-kit/issues/974) (anchors, friction, rule sets), [#804](https://github.com/aleskalfas/project-kit/issues/804) (configuration, validation, connections), [#234](https://github.com/aleskalfas/project-kit/issues/234) (living-docs), [#885](https://github.com/aleskalfas/project-kit/issues/885) (software-analysis), and the Umbrella [#979](https://github.com/aleskalfas/project-kit/issues/979) (project-kit's own adoption).

## Where the concept and pkit do not yet meet

So that no slide promises what the tool will not deliver, and so that pkit can close what the concept asks for:

1. **"Every statement grounded" is judgement, not a check.** The tool sees pages and their anchors; a reviewer or agent connects each sentence to them. Say *every page*, not *every sentence*.
2. **Duplicate detection** (I3, "duplicates detected, not discovered by readers") — a rule, applied by the agent and reader-review; no deterministic duplicate check is planned yet.
3. **Format checks** (I2, "an automatic check on every docs change") — templates and a page-kind field are planned; checking a page's body against its template is not.
4. **User paths unbroken** (I5, "a break fails loudly") — a rule, plus executed runs as evidence. The evidence is advisory: a broken path informs the review but fails nothing by itself. No deterministic path or link check is planned, and executed runs need something to perform them (the product itself, as Mockingbird can, or a future testing capability).
5. **Sources as anchors** — need an anchor kind that some capability registers, most likely evidence; none does yet.
6. **"Docs checked against the tool itself"** — commands, flags and examples actually run — arrives as executed evidence; nothing performs it yet.
7. **A friction result is only as fresh as its base.** Two changes landing back to back can each pass while the second made the first's page stale; the whole-repository check catches it afterwards. project-kit does not gate on an up-to-date base yet; a merge queue is the planned end state.
8. **Commands a capability supplies to the checks** (resolving a new anchor kind, answering a data connection) must run bounded in time, deterministic and without network access. The time bound and the output check are enforceable; how "no network" is realised is not yet decided — the backbone does not own confinement.
9. **The work tracker's "documentation impact" section** keeps satisfying the tracker's own code-to-document mapping until a project converts that mapping into page anchors; obligations raised by the documentation capability are met only by the pages' answers, which the section may render.

If the presentation work finds more — a concept pkit misses, or pkit behaviour that contradicts the concept — that is the "vice versa". Raise it back to project-kit as a change request from the Mockingbird side (the way #949 arrived), rather than editing project-kit from a Mockingbird session.

## Words for the audience, and their pkit names

| In the presentation | In pkit's records |
|---|---|
| what makes a page true | anchors |
| drift | friction |
| re-check | revalidation |
| still true, and why | outcome *unchanged*, with its justification |
| postponed, with a reason | deferral |
| what is stale or postponed | debt |
| the documentation method | a rule set (the shared one is LDOC) |
| audience, documentation area | space |
| product knowledge | the analysis: actors, use cases, journeys, glossary |
| plugs into each other without depending | connection points, addressed by role |

## Notes for building the presentation

- **Audience.** The hand-off says adoption is not decided by the Mockingbird team, and that the case is presented as a causal chain without naming pkit until the last link. Keep that shape: the problem, the chain, the eleven ideas, why not build it in each project, and only then pkit.
- **Concepts, not implementation.** No field names, command names or file layouts in the concept part. At most one closing "what it looks like" slide, for example this page front matter — the `pkit:` block's keys are decided, the page's own `reader` and `kind` fields are illustrative until the capability ships their schema:

  ```yaml
  ---
  reader: user            # illustrative
  kind: guide             # illustrative
  pkit:
    friction:
      anchors:
        path: [src/cli/run.py]
        record: [ADR-006]
        artefact: [UC-003]
      revalidated:
        at: 2026-10-02T09:40:12Z
        outcome: unchanged
        unchanged-because: "only the result writer's internals changed"
  ---
  ```

- **Honest status.** Use the status table: most ideas are decided but not yet built. "Decided, being built, first adopter enforcing from day one" is a stronger story than an overclaim.
- **Mockingbird's own rules survive.** CMN-001 to CMN-008 were not discarded: each is now either shared machinery or a rule of the shared method (see the table above). That is worth a slide — the team's work became the method every project uses.

## Canonical sources

- The hand-off: [#949](https://github.com/aleskalfas/project-kit/issues/949).
- The reasoning trail, question by question: [the design note](https://github.com/aleskalfas/project-kit/blob/main/.pkit/scratchpad/done/2026-09-26-software-analysis-living-docs-design.md) (retired; history).
- Living documentation: [living-docs DEC-001][ld001]. Product knowledge: [software-analysis DEC-001][sa001].
- The shared foundations: configuration [COR-048][cor048], documentation roots [COR-049][cor049], anchors and friction [COR-050][cor050], rule sets [COR-051][cor051], slots [COR-052][cor052], connection points [COR-053][cor053]; the work tracker's side [project-management DEC-053][pm053].
- project-kit as first adopter: [ADR-055][adr055].

[cor048]: https://github.com/aleskalfas/project-kit/blob/main/.pkit/decisions/core/COR-048-backbone-configuration.md
[cor049]: https://github.com/aleskalfas/project-kit/blob/main/.pkit/decisions/core/COR-049-documentation-roots.md
[cor050]: https://github.com/aleskalfas/project-kit/blob/main/.pkit/decisions/core/COR-050-anchors-and-friction.md
[cor051]: https://github.com/aleskalfas/project-kit/blob/main/.pkit/decisions/core/COR-051-rule-sets.md
[cor052]: https://github.com/aleskalfas/project-kit/blob/main/.pkit/decisions/core/COR-052-slots.md
[cor053]: https://github.com/aleskalfas/project-kit/blob/main/.pkit/decisions/core/COR-053-connection-points.md
[ld001]: https://github.com/aleskalfas/project-kit/blob/main/.pkit/capabilities/living-docs/decisions/DEC-001-living-docs-discipline.md
[sa001]: https://github.com/aleskalfas/project-kit/blob/main/.pkit/capabilities/software-analysis/decisions/DEC-001-software-analysis-discipline.md
[pm053]: https://github.com/aleskalfas/project-kit/blob/main/.pkit/capabilities/project-management/decisions/DEC-053-doc-check-slot.md
[adr055]: https://github.com/aleskalfas/project-kit/blob/main/tech-docs/architecture/decisions/ADR-055-first-adopter-analysis-and-living-docs.md

## Status

Active. Retires into project-kit's user-space concept page once living-docs ships its page templates, `--produced` naming that page.
