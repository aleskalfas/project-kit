---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-09-28
---

# Living documentation — the concept, as concluded

## What this note is

The answer to the hand-off that started this work: [#949](https://github.com/aleskalfas/project-kit/issues/949), in which Mockingbird's documentation rewrite produced a set of invariants and rules for keeping documentation true, and asked for them to live once in pkit rather than be copied between repositories. Between 2026-09-26 and 2026-09-28 project-kit worked the hand-off through to accepted records and an implementation plan. This note states **what was concluded about how living documentation should work** — as a concept, independent of any tool — traces every part of the hand-off to its conclusion, and pairs each idea with what pkit provides, so that a presentation of the concept arrives at pkit as its last link rather than its first.

It is written for whoever builds that presentation, including an assistant session that receives only this link. Its statements summarise accepted records, cited throughout and listed at the end; the record wins wherever this note paraphrases it. Record ids and issue numbers here are for the builder, not for slides. States marked *shipped*, *in progress* or *planned* are a snapshot of 2026-09-28; the live state is on [Milestone 5](https://github.com/aleskalfas/project-kit/milestone/6).

It retires into project-kit's first user-facing concept page, once the living-docs capability ships its page templates.

## The audience and the ask

What the hand-off says, and what a builder should confirm with the maintainer before the first slide:

- **Known.** The work began in Mockingbird's documentation rewrite: partner teams are onboarding, and the docs are spread across a README, `docs/`, per-package READMEs, two guides and a separate site. The team's own requirement is that any change to code results in the affected docs being updated, with no manual step. pkit is installed in the maintainer's Mockingbird checkout but its folder is excluded from git, so the team does not use it. The hand-off says "adoption is not decided by the Mockingbird team" and that the case is presented "as a causal chain … without naming pkit until the last link".
- **Confirm.** Who is in the room; what the ask is (approve the documentation approach, adopt pkit, or both); the length and format; and whether "not decided by the team" means *not yet decided* or *not theirs alone to decide*.

## The story in one breath

The hand-off's chain, sharpened by the conclusions. It opens on the team's own words.

1. **The team already wrote down what documentation must keep**: true after every change, one format, each fact once, a known reader, unbroken user paths; rules with names and reasons; a known cause for everything.
2. **A statement is true only against something** — the code it describes, a decision, a captured source, or the product knowledge it builds on: who uses the product and what they try to achieve.
3. **So every page says what it rests on, and a check flags the page when any of that changes.** A page is watched as well as it says what it rests on. The answer to a flag is recorded in the page itself.
4. **Pages serve declared readers**, in spaces kept apart by audience, following a method written down as named, checkable rules.
5. **People skip manual steps**, so the flagging is automatic, an agent drafts the fix, and a person approves it. That only works when the method is explicit and the checks are deterministic.
6. **The need is the same in every repository; only the content differs.** The method and the machinery belong in one shared place that every project installs — the last link, and the first time pkit is named.

## The problem — the opening evidence

A documentation spike on another project the maintainer works on (IGW, June 2026; [the audit](https://github.com/aleskalfas/project-kit/blob/main/.pkit/scratchpad/active/2026-06-20-igw-docs-consolidation-audit.md)) found, among others:

- one topic split across two documents, the second mirroring the first section by section;
- an integration guide re-documenting a tool another document owns, including a byte-identical copy;
- a guide claiming "four modes" while its own table — and the owning document — listed three;
- one page saying a key is required with no fallback, three others saying it falls back to a default;
- three sections in one file with the same heading, so cross-references were ambiguous.

Its sharpest lesson: **when the docs disagreed, the code decided — and the wrong side was the majority.**

Review does not catch this: a review looks at the change in front of it, and the stale page is somewhere else. The usual remedies fail for structural reasons, and two of them are pkit's own work-tracking features today, which stay — the first as a prompt, the second as a transitional source until pages carry their own anchors ([project-management DEC-053][pm053]):

- a **"documentation impact" section** on each change depends on the author remembering which pages exist;
- a **map from code paths to documents** is a guess made from the code's side; broad entries fire on most changes, so people stop reading them;
- a **registry of documents** has to be maintained as carefully as the documents it lists — pkit's own [June attempt](https://github.com/aleskalfas/project-kit/blob/main/.pkit/scratchpad/active/2026-06-20-documents-registry-and-onboarding.md), which the design below replaced.

## The concept — eleven ideas

Each idea says what it is and why. The *Behind it* line under each — what part of the hand-off it answers and what pkit provides — is for the builder and the closing slide, not for the concept slides.

### 1. Documentation lives in spaces, one per audience

A *space* is a body of documentation with one audience, one entry point and one definition of how its pages are made. Every project has at least a **user space** (what the system does and how to use it) and a **technical space** (why, from where, by which rules — for maintainers and for the agents that write and check the docs). A project may add others, such as an interface reference.

- **Separate, not secret.** User-facing navigation and search never lead into technical material. The technical space is in the same repository and visible to anyone; the separation is audience and entry point.
- **Which space a document belongs to.** The user and technical spaces each have a root folder; documents outside the roots (a top-level README, a contributing guide) are assigned to a space explicitly; where places nest, the most specific wins. Decisions and rules inside a space are what pages *rest on*, not pages themselves.
- **Why.** A user who meets maintainers' material is lost; a maintainer who cannot find the grounds of a user page cannot keep it true; and the writing agent gets a checkable boundary instead of a judgement call.

*Behind it:* hand-off §4, I4, R1, R3 · pkit declares two documentation roots per project (both `docs/` until a project splits them); a location chosen afterwards derives from the right root and is recorded when first used, so a later root change never moves existing files — *shipped* ([COR-049][cor049]). Place assignment and precedence are decided ([living-docs DEC-001][ld001] point 1) and applied by the living-docs capability — *planned*.

### 2. Every page says what it rests on

A page lists its *anchors*: the code it describes, the decisions and rules it applies, the other artefacts it builds on (a use case, another page), and captured sources. Anchors are per page, not per sentence; the reviewer — person or agent — connects each statement to the page's anchors.

- **Why per page.** Anchoring every sentence is precise and so expensive to maintain that people stop, which recreates the drift. Per page keeps the cost bearable; precision comes from whoever re-checks the page against the actual change.
- **Unanchored is visible, not an error.** A document that rests on nothing is counted and shown, so a project sees how much of its documentation stands on nothing.
- **An anchor that points at nothing is an error.** A path, decision or artefact that no longer exists is reported, never ignored — silence would look like health.

*Behind it:* I1; the hand-off's "truth has three anchors" became four grounds — code, decisions and rules, product knowledge and other pages, sources; CMN-003 · pkit keeps the anchors in a small block in the page's front matter, with three core kinds (paths, identified records, other artefacts) and strict validation — *shipped* ([COR-050][cor050] points 1–2). Sources need an anchor kind a capability provides; none does yet — see gap 7.

### 3. Drift is flagged, not remembered

When anything a page rests on changes, the page is flagged until someone re-checks it. The check runs on every change wherever a project wires it into its pipeline, and locally on demand; a second view covers the whole repository. It reports upstream first: what others depend on is re-checked before what depends on it.

- **Watched as well as anchored.** The check flags a page for the anchors it declared. A page that depends on a file it does not name goes stale unseen — so the whole-repository view also shows the code that nothing describes, within the part of the code the project says ought to be described.
- **How strict is a project's choice.** In *warning* mode the check reports; in *enforcing* mode a change that leaves a flag unanswered fails its check, and cannot merge where the project requires that check.
- **Why.** Only a check that fires at the moment of the change is reliable; it tells the author "you changed what this page rests on" when the fix is cheapest.

*Behind it:* I1 ("when an anchor changes, every statement pointing at it is found and re-checked" — the check finds every *page*; the statements are the reviewer's) · pkit calls a flag *friction*: the change check, the whole-repository check, warning and enforcing modes — change check *in progress*, whole-repository check *planned* (COR-050 points 5–8, 12).

### 4. The answer lives in the page, not in the pull request

A flag is answered in the page itself, in one of three ways:

- **updated** — the page changed;
- **still true** — the page did not need to change, with one sentence saying why it holds against *this* change; a new sentence every time, so a blind "yes" is visible;
- **postponed** — for one anchor, with a reason; each re-check keeps the postponement deliberately or drops it, and a later change to the same thing flags the page again.

- **Why.** A pull-request description is one tool's format; a change made by another tool, by hand, or checked locally has none. An answer in the page works everywhere, and the next reader finds the justification next to the thing it justifies.
- **Debt comes from history.** What is stale and what is postponed — with who, when and in which change — is derived from the repository's history, never kept in a separate ledger that would drift from it.

*Behind it:* new since the hand-off; it closes the gap between "re-checked" and "recorded that it was re-checked" · pkit keeps the answer beside the anchors (the block's shape is *shipped*), with commands to re-check and to postpone and a debt listing — *planned* (COR-050 points 3–4, 9, 13). A work tracker may *render* the answers into its pull-request template; it never reads the template instead of the pages.

### 5. Every page is written for a declared reader

Every project has two readers without declaring anything — a *user* and a *maintainer* — and may add its own, each with what they need. Each page names its reader and its kind, and says only what that reader needs. A *reader-review* reads the page as that reader and reports what they would miss or not need.

- **Readers can come from the product knowledge**: the actors and their needs (idea 9) are added alongside the two defaults, when a project keeps that knowledge.
- **The product can test its own docs.** Executed checks — a simulated user following a guide against the running product — are evidence the review uses, not something the documentation method runs itself. For Mockingbird this is the product doing what it is for: persona × task over its own docs.

*Behind it:* I4, I5; hand-off §10 "reader-review as an agent vs as a run of the product" — both, in these two roles · pkit: declared readers with the defaults, fillable from the product knowledge; a reader-review agent; executed results arriving as reading evidence — *planned* (living-docs DEC-001 points 4, 6, 7).

### 6. The method is written down as named, checkable rules

A *rule* is a statement every artefact in its scope must satisfy, caused by a decision, checkable by a tool, an agent or a reviewer. Rules have permanent identifiers, never renumbered or reused; each records its origin — when, by whom and why, in the decider's words, or a decision record that explains it at length. A rule is **proposed** until accepted, and a proposed rule binds nothing; accepted rules bind; superseded and withdrawn rules stay in place with their ids.

- **Extend, never relax.** A project inherits a shared set of rules and adds its own, or fills the extension points a shared rule offers. It may not contradict an inherited rule: what a tool can check mechanically is checked, the rest is review. Inheriting someone else's rules pins their major version, so a tightened rule never arrives unreviewed.
- **A rule can be relied on explicitly.** A page may anchor to a single rule, so changing, superseding or withdrawing that rule flags everything anchored to it.
- **Light enough to use.** A whole set of rules is one short document — a paragraph per rule — not one formal record per rule.
- **The shared documentation method.** A page's anchors ground every statement it makes; each fact is stated once and other pages link to it; each page names its reader and says only what that reader needs; pages of a kind follow one format, with a template per kind; an index-like file is a signpost to what a folder holds, never a summary; nothing is created ahead of the need for it. The user space's own definition adds one more: the reader paths stay unbroken.

*Behind it:* T1, I2, I3, CMN-001, CMN-006, CMN-008; hand-off §6 "a lightweight rule-list form" · pkit: rule-set files with deterministic checks of ids, statuses, origins, successors and inheritance, and citable rule ids — *in progress*; the shared documentation method (*LDOC*) ships with the documentation capability — *planned* ([COR-051][cor051]; living-docs DEC-001 point 3).

### 7. The method is kept apart from the content

Content is what the project knows — its pages, its readers, its product knowledge. The method is how pages are made from it — the rules, templates and space definitions. Each space's definition lives in the technical space; the shared method names nothing project-specific.

- **Why.** A method written once can change in one place and apply to every project; a method mixed into content can never be separated again.

*Behind it:* hand-off §5, R4 · pkit ships the method with the documentation capability, and upgrades it like any installed component; nothing the project wrote is touched by an upgrade — *planned* (living-docs DEC-001 point 2).

### 8. Fixes are proposed, never applied blind

An agent resolves a flag by *proposing* the change to the page, citing the change that caused it and the anchors it rests on; a person reviews it through the project's usual approval path. A statement the page's anchors do not ground is grounded by a new anchor, taken out, or raised as a question — never left standing as if it were true.

- **Why.** An agent that rewrites pages directly will eventually rewrite them wrongly — misjudge a file's audience, or "fix" a page to match a bug. Proposals with evidence keep the speed and keep the judgement.
- **Who starts the agent** — a person, or a job that runs on each flagged change and opens the proposal for review — is the project's choice; see gap 1.

*Behind it:* hand-off §5 "agents do the work, checks verify it"; the June spike's "propose with cited evidence, never auto-apply" · pkit: the documentation capability's agent; every proposal lands as a reviewable change — *planned* (living-docs DEC-001 point 5).

### 9. Product knowledge comes first, then code, then documentation

What the software must do — its **actors** (who uses it, with their needs), **use cases** (an actor's goal and how the system fulfils it), **journeys** (an end-to-end path across use cases) and **glossary** — is kept true too, as artefacts that say what they rest on. A change is planned in that order: product knowledge first, then code, then docs, each checked against the one before. The anchors point the other way — a use case rests on code, a page rests on the use case — so a code change flags the use case, and the use case flags its pages.

- **Stale or regressed.** When code and a use case disagree, either the change was intended (the use case is updated, then the docs) or the code regressed (the use case stands and a defect is reported). The product knowledge is never rewritten to match broken code; when the intent is unclear, a person decides. That judgement is what reconciles the planned order with the direction of the anchors.
- **Membership test** (the hand-off's, kept): an artefact belongs to the product knowledge if a change to the software can make it false and we want to find out when it does.

*Behind it:* hand-off §7 · pkit's software-analysis capability — the artefacts and their checks; re-check records written only when there is something to say; an authoring skill that guides the re-check, which a person or an agent performs — *planned* ([software-analysis DEC-001][sa001]). An executed run is evidence and never clears a flag by itself (point 7), so the hand-off's "revalidation and I5 become one test" was not adopted.

### 10. Adopting on an existing project is a transformation, not a move

On day one nothing is anchored and no document has declared its reader, so a quiet check means nothing. The honest signals are the **unclassified documents** — everything that is not yet a page of some space — and, once the project says which code ought to be described, the **uncovered surface**: that code, where nothing describes it. An agent proposes which space each document belongs to, how pages should be split, merged or rewritten for their readers, which anchors each statement needs, and which existing code-to-document mappings become page anchors. Every proposal is reviewed; files move only as ordinary reviewed changes.

- **Done means** the declared surface is covered and no page is left unanchored without an accepted reason — and the same mechanism keeps it there.

*Behind it:* hand-off §9 · pkit: the measures in the whole-repository check and the documentation capability's check; onboarding proposals by its agent — *planned* (living-docs DEC-001 points 4, 8; COR-050 point 8).

### 11. The pieces stay independent, and combine when present

Documentation works with no product knowledge and no work tracker; each enriches it when installed — the product knowledge supplies readers, the tracker asks each change what documentation it owes — and none depends on another. A piece is addressed by the *role* it plays, not by its name, so a different documentation implementation could replace the shipped one without anything else noticing.

- **Why.** A team that wants only part of it adopts only that part, and nobody is locked into an implementation.

*Behind it:* hand-off §7 "two capabilities joined by a slot, not a dependency", and its open question on the slot mechanism — answered by one mechanism generalising the contribution patterns pkit already had; the hand-off's separate *anchors* slot was dropped, since the core anchors cover it (living-docs DEC-001 point 4) · pkit: role-named connection points — resolver *shipped*, data connections *planned* ([COR-052][cor052], [COR-053][cor053]).

## Where each part of the hand-off ended up

*Met:* **yes** — the concept keeps it as asked; **partly** — kept, with the gap named; **changed** — the conclusion differs, for the reason given.

| Hand-off item | Met | Concluded | Record |
|---|---|---|---|
| §1 "any change to code results in the agent updating the affected docs, no manual step" | changed | the flag is automatic; the fix is an agent's proposal a person approves; what starts the agent is open (gap 1) | living-docs DEC-001 point 5 |
| §1 docs spread across a separate site | partly | anchors are repository paths; a site outside the repository is out of reach (gap 12) | COR-050 point 2 |
| §2 grouping (common invariants + per-space extensions) | changed | T1 and T2 became shared machinery for every artefact — product knowledge too — not rules of the technical space | COR-050, COR-051 |
| I1 docs stay true after every change | partly | ideas 2–4; a page is watched as well as its anchors are complete (gap 2) | COR-050 |
| I2 unified format | partly | the method's format rule, a page kind, a template per kind; no automatic check of a page body (gap 5) | living-docs DEC-001 points 3, 4 |
| I3 stated once | partly | the method's rule; duplicates are found by review, not by a check (gap 4) | living-docs DEC-001 point 3 |
| I4 readers | yes | idea 5 | living-docs DEC-001 points 4, 6, 7 |
| I5 user paths | partly | the user space's rule; executed runs are advisory evidence (gap 6) | living-docs DEC-001 points 3, 6, 7 |
| T1 rules | yes | idea 6 | COR-051 |
| T2 causes, for any file or folder | partly | the anchors say why each *page* exists; files and folders in general are not covered (gap 10) | living-docs DEC-001 point 3 |
| "Truth has three anchors" (code, decision, source) | changed | four grounds — code, decisions and rules, product knowledge and other pages, sources; sources wait for an anchor kind (gap 7) | COR-050 point 2 |
| §4 two spaces, R1 | yes | idea 1 | living-docs DEC-001 point 1; COR-049 |
| §4 contents: "where each fact lives" | partly | no artefact records a fact's owner (gap 4) | — |
| §4 contents: "simulated users and scenarios" | changed | journeys are product knowledge; simulated runs are whatever produces reading evidence — pkit keeps no simulated users | software-analysis DEC-001 point 1; living-docs DEC-001 point 7 |
| §5 method apart from content, R4 | yes | idea 7 | living-docs DEC-001 point 2 |
| §5 inheritance, no contradiction | yes | idea 6; the mechanical part is checked, the rest reviewed | COR-051 point 7 |
| CMN-001 inherit, extend at declared points | yes | rule-set inheritance and extension points | COR-051 point 7 |
| CMN-002 nothing without an input | partly | the method's "nothing ahead of the need" — judged, not checked (gap 11) | living-docs DEC-001 point 3 |
| CMN-003 every artefact names its cause | changed | anchors are optional: an artefact without them is counted, and onboarding ends when each is anchored or accepted with a reason; every rule carries an origin | COR-050 point 2; living-docs DEC-001 point 8; COR-051 point 5 |
| CMN-004 the process is the index | changed | the anchors are the index of why each page exists | living-docs DEC-001 point 3 |
| CMN-005 a README is a signpost | partly | the method's signpost rule — judged, not checked (gap 11); the `readme-exceptions` extension point has no counterpart until the method is written | living-docs DEC-001 point 3 |
| CMN-006 permanent ids, `ID:name` extension points | changed | ids `RS-<SET>-NNN`, permanent and never reused; extension points `#name`, so they never clash with a namespace colon. Mockingbird's CMN ids gain the `RS-` prefix once, on adoption | COR-051 point 3 |
| CMN-007 the method's root exists by decision | yes | the method ships with the capability; each space's definition sits at a sub-path the capability declares and records when first used | living-docs DEC-001 point 2; COR-049 point 5 |
| CMN-008 origin line | yes | origin fields — when, who, why in the decider's words, or a decision record — checked deterministically | COR-051 point 5 |
| "Decisions cause rules; steps cause data" | changed | the first half stands; the second is replaced by anchors. Whether a planned re-check becomes a step-based lifecycle is left to a later decision | COR-050; software-analysis DEC-001 point 11 |
| §6 "a lightweight rule-list form" | yes | one short document per set of rules | COR-051 point 2 |
| §7 two capabilities joined by a slot | yes | idea 11; readers are filled from the product knowledge, neither side names the other | COR-052, COR-053 |
| §7 where the CMN rules live | yes | split by nature: the rule machinery and anchors in the shared core, the documentation rules in the method | COR-051 (rationale, why core); living-docs DEC-001 point 3 |
| §7 software-analysis scope | yes | actors, use cases, glossary as proposed, plus journeys; constraints, quality requirements, architecture views and executable use cases left to later decisions | software-analysis DEC-001 points 1, 11 |
| §7 "revalidation and I5 become one test" | changed | a run is evidence; it never clears a flag by itself | software-analysis DEC-001 point 7 |
| §7 the name | yes | living-docs, after Cyrille Martraire's *Living Documentation* | — |
| §8 R2 decisions as internal docs | yes | as the hand-off concluded: project decisions stay outside pkit's folder, at a configurable location | COR-025 |
| §8 R3 a first-class internal root | changed | two roots in the project's backbone configuration, not in the agent overlay; a location chosen afterwards derives from the internal root and is recorded; placeholders already set stay, and do not follow a later root change | COR-049 points 3, 5, 6 |
| §8 "inside `.pkit/` is fine" for agent-maintained projects | changed | a root always lies outside pkit's own folder, whoever maintains it; the record gives no reason (gap 15) | COR-049 point 1 |
| §8 warn when `.pkit/` is excluded from git | no | not decided or planned (gap 13) | — |
| §9 Mockingbird's migration shape | changed | see "What adopting means for Mockingbird" | COR-049; living-docs DEC-001 points 1, 8 |
| §10 statuses and supersession for light rules | yes | proposed, accepted, superseded, withdrawn | COR-051 point 4 |
| §10 evidence for rules vs for data | yes | origins stay inline and may cite a captured source | COR-051 point 5 |
| §10 the process substrate for doc steps | changed | no — the flags come from a check over the anchors | COR-050; software-analysis DEC-001 point 11 |
| §10 default internal root: dotfolder or not | yes | the project's choice; both default to `docs/`; outside pkit's own folder | COR-049 point 1 |
| §10 reader-review: agent or product run | yes | both: the agent reads, the product's runs arrive as evidence | living-docs DEC-001 point 6 |

## What adopting means for Mockingbird, concretely

- **Commit pkit's folder.** It is excluded from git today, and three things adoption needs live there: the project's backbone configuration (roots, places, what ought to be described, warning or enforcing), the installed method, and the check itself. Without it, the pipeline cannot run the check, and a changed rule flags nothing.
- **Declare the two roots**: `docs/` for users and `tech-docs/` for maintainers — both folders already exist.
- **The hand-built method** in `tech-docs/.meta/` becomes the shared method, installed with the capability, plus the two spaces' definitions under `tech-docs/`. The team's CMN rules live on as a project set of rules that inherits the shared method and withdraws what the method or pkit's core already provides.
- **The planned `tech-docs/users/`** (actors, journeys, needs, stories) becomes the product knowledge under `tech-docs/`, if the team adopts software-analysis.
- **Today's `docs/` mixes both audiences**: guides and onboarding pages for users, and the architecture decisions, `ARCHITECTURE.md`, `CONTRIBUTING.md`, `RELEASING.md` for maintainers. Onboarding proposes moving the technical ones to `tech-docs/` or assigning them to the technical space; the existing location of the architecture decisions stays until a reviewed change moves it.
- **Wire the change check into the pipeline**, in warning mode first, and enforce it when the anchors are trusted.
- **Fill the reading evidence with the product itself** — persona × task runs over its own docs, the team's own I5 idea.

## Why not build it in each project

Every idea above is universal, and the machinery behind it is neither trivial nor different between projects:

- **Strict validation of every file the method uses**, with "did you mean" messages: the configuration, each page's anchors and answers, the rule files, the reader declarations.
- **Re-check points derived from the repository's history** that hold across squash merges and parallel branches — with the rule that moving a page means re-checking it — and a change check any pipeline can run without a database.
- **A rule system** with permanent ids, recorded origins, statuses, inheritance and version pins.
- **A connection model** that lets documentation, product knowledge and work tracking enrich each other without depending on each other.
- **Agents that propose** and a review loop that keeps a person in charge.
- **Upgrades that reach every project**: the method improves once, every project receives it, and nothing a project wrote is touched.

A project keeps only what is genuinely its own: its content (pages, product knowledge, its own rules) and a few choices (where its two roots are, which documents outside them belong to a space, what code ought to be described, warning or enforcing). The machinery **demands nothing until the first page is anchored**, and it can be adopted one piece at a time. That is the last link: **pkit gives every project this machinery for free, so each project writes only its content.**

## The commitment: project-kit adopts it first

project-kit is its own first adopter, ahead of Mockingbird ([ADR-055][adr055]). **Done:** its architecture decisions have moved under what will be its technical root. **Decided, being built:** user root `docs/` and technical root `tech-docs/`; the change check in **enforcing mode from the day it exists**, because every page and anchor here is produced by the tooling under test; its first product knowledge will be the use cases of its own multi-clone coordination work; its code-to-document mapping becomes page anchors during onboarding.

## Status on 2026-09-28

| Idea | State |
|---|---|
| 1 spaces and roots | roots *shipped*; place rules *decided*, applied with living-docs (*planned*) |
| 2 anchors | block and its validation *shipped*; source anchors *not yet filed* (gap 7) |
| 3 flags | change check *in progress*, with project-kit's enforcing gate; whole-repository check *planned* |
| 4 answers in the page | shape *shipped*; re-check and postpone commands, debt listing *planned* |
| 5 readers | *planned* |
| 6 rules | rule files *in progress*; the shared method (LDOC) *planned* |
| 7 method apart | *planned*, with living-docs |
| 8 proposals | *planned*, the living-docs agent |
| 9 product knowledge | *planned*, software-analysis |
| 10 onboarding | *planned* |
| 11 independence | connection resolver *shipped*; data connections *planned* |
| project-kit as first adopter | architecture decisions moved (*done*); roots and places *planned*; enforcing gate *in progress* |

All eleven ideas are **decided** in accepted records. Live state: [Milestone 5](https://github.com/aleskalfas/project-kit/milestone/6), with the EPICs [#974](https://github.com/aleskalfas/project-kit/issues/974) (anchors, flags, rules), [#804](https://github.com/aleskalfas/project-kit/issues/804) (configuration, validation, connections), [#234](https://github.com/aleskalfas/project-kit/issues/234) (living-docs), [#885](https://github.com/aleskalfas/project-kit/issues/885) (software-analysis), and the Umbrella [#979](https://github.com/aleskalfas/project-kit/issues/979) (project-kit's own adoption).

## Where the concept and pkit do not yet meet

So that no slide promises what the tool will not deliver, and so that pkit can close what the concept asks for. Items marked *(internal)* are not for slides.

1. **No unattended fix.** The flag is automatic; the fix is drafted by an agent someone starts, and a person approves it. The team asked for "no manual step". A job that runs the agent on each flagged change and opens the proposal for review would fit the concept; it is not decided or filed. Say it plainly: *the flag is automatic, the fix is a proposal you approve.*
2. **A page is watched only as well as its anchors are complete.** A page that depends on a file it does not name goes stale unseen. The uncovered-surface view shows code nothing anchors, and only within the part the project declared. Say *every page says what it rests on, and the check holds it to that* — not *docs are always true*.
3. **Sentences are judged, pages are checked.** "Every statement grounded" is a reviewer's or agent's judgement; the tool sees pages and their anchors. Say *every page*, not *every sentence*.
4. **Duplicates and owners** (I3). Duplicates are found by review and the agent, not by a check; nothing records which page owns a fact. The June spike found that a declared owner made "one owner per topic" enforceable.
5. **Format** (I2). Templates and a page kind are planned; checking a page body against its template is not.
6. **User paths** (I5, "a break fails loudly"). A rule plus executed runs as evidence; the evidence is advisory, so a broken path informs the review but fails nothing by itself. No path or link check is planned, and executed runs need something to perform them — the product itself, as Mockingbird can, or a future testing capability.
7. **Sources as anchors.** The anchor block accepts only the three core kinds until capabilities can register further kinds; nothing filed builds that registry yet, so source anchors — most likely from the evidence capability — are not deliverable.
8. **Docs checked against the tool itself** (commands, flags, examples actually run) arrive as executed evidence; nothing performs it yet.
9. **Code checked against the product knowledge** is testing, which the product-knowledge capability deliberately leaves out; a re-check reads, and executed results only inform it.
10. **Files and folders in general** (T2). The anchors explain why each page exists; not why an arbitrary file or folder does.
11. **Two method rules are judgement only**: "nothing ahead of the need" and "a signpost, not a summary".
12. **Docs outside the repository** — a separate site — are out of reach of anchors.
13. **pkit's folder must be tracked.** The configuration, the method and the check live there; nothing warns when it is excluded from git, which the hand-off asked for.
14. *(internal)* **A flag result is only as fresh as its base.** Two changes landing back to back can each pass while the second made the first's page stale; the whole-repository view catches it afterwards. project-kit does not yet gate on an up-to-date base; a merge queue is the planned end state.
15. *(internal)* **The roots rule has no recorded reason.** COR-049 keeps roots outside pkit's own folder but does not say why; the hand-off had allowed agent-maintained docs inside it.
16. *(internal)* **Commands a capability supplies to the checks** must run bounded in time, deterministic and offline; the time bound and the output check are enforceable, how "offline" is realised is not yet decided — the backbone does not own confinement.
17. *(internal)* **The work tracker's "documentation impact" section** keeps satisfying the tracker's own code-to-document mapping until a project converts that mapping into page anchors; obligations raised by the documentation capability are met only by the pages' answers.

**Candidates for pkit** — the "vice versa" this note surfaces, not yet decided: an unattended agent trigger (1), a declared owner per fact (4), the anchor-kind registry (7), a warning when pkit's folder is untracked (13), and the reason behind the roots rule (15). If the presentation work finds more — a concept pkit misses, or pkit behaviour that contradicts the concept — raise it to project-kit as a change request from the Mockingbird side, the way #949 arrived, rather than editing project-kit from a Mockingbird session.

## Words

**Words the team already uses, and pkit uses the same way:** anchors, spaces, readers, reader-review, re-checking (pkit writes *revalidation*), rules and rule sets, extension points, actors, use cases, journeys, glossary.

**pkit's own words**, to introduce once, near the end, if at all:

| pkit's word | What it means |
|---|---|
| friction | a flagged page: something it rests on changed since it was last re-checked |
| deferral | a postponed answer, for one anchor, with its reason |
| debt | everything flagged or postponed, with who, when and which change |
| LDOC | the shared documentation method |
| role | the part a component plays (documentation, product knowledge, work tracking) |
| connection point | where one role plugs into another without depending on it |

## Notes for building the presentation

- **Shape.** Open on the team's own invariants and the IGW evidence; walk the chain; present the eleven ideas; show why not to build it in each project; name pkit only then. Keep the *Behind it* lines off the concept slides — one closing slide can show the traceability table.
- **Avoid.** Record ids, issue numbers and dates on slides. The phrases *automatic doc updates*, *every statement verified*, *costs nothing*, *project-kit runs on it*. Presenting "living documentation" as a new term — it is Cyrille Martraire's, and the name was chosen for that reason.
- **Honest status.** Most ideas are decided and being built; the first adopter enforces from the day the check exists. That is a stronger story than an overclaim.
- **The team's rules shaped the method.** CMN-001 to CMN-008 were not discarded: each became shared machinery or a rule of the shared method, or was replaced for a stated reason (the table above). On adoption they live on as the team's own rules, inheriting the shared method. Worth a slide.
- **At most one "what it looks like" slide**, at the end — for example this page front matter. The `pkit:` block's keys are decided; the page's own `reader` and `kind` fields are illustrative until the capability ships their schema:

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

## Canonical sources

- The hand-off: [#949](https://github.com/aleskalfas/project-kit/issues/949).
- The reasoning trail, question by question: [the design note](https://github.com/aleskalfas/project-kit/blob/main/.pkit/scratchpad/done/2026-09-26-software-analysis-living-docs-design.md) (retired history; the records supersede it where they differ).
- Documentation: [living-docs DEC-001][ld001]. Product knowledge: [software-analysis DEC-001][sa001].
- Shared foundations: configuration [COR-048][cor048], documentation roots [COR-049][cor049], anchors and flags [COR-050][cor050], rules [COR-051][cor051], slots [COR-052][cor052], connection points [COR-053][cor053]; the work tracker's side [project-management DEC-053][pm053].
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

Active. Retires into project-kit's user-space concept page once living-docs ships its page templates, `--produced` naming that page and any change requests the presentation raises.
