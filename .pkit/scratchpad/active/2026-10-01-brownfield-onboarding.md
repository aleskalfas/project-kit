---
authors:
  - Aleš Kalfas
started: 2026-10-01
---

# Brownfield onboarding of analysis and documentation, tried on project-kit

## The question

In what order, in what units, behind which gates and with whose judgment does an existing project get to a covered declared surface?

- **The starting point:** code, decisions and documents are already there. There is no analysis, and nothing is anchored. The project installs software-analysis and living-docs.
- **On project-kit:** what running that looks like, since project-kit is exactly such a project.
- **The maintainer's order:** analysis first, for the whole of pkit, from the basics to the particular capabilities. Documentation comes only afterwards.
- **Why that order:** done together, the documentation would be rewritten every time the analysis under it moves. That rewriting is the token cost to avoid.

## Where it stands on 6 October

The core's actors are merged, and the glossary is next.

- **Done:** area 0's actors for the core. Eight actors were merged on 5 October (#1344, PR #1345).
- **Next:** the glossary, whose first term is "the system". Then come the use cases of area 1, the backbone lifecycle, once #1352 lands.
- **Waiting on #1352:** a declared structure for each kind of analysis artefact. The analysis's own rule set waits for it too.
- **After area 1:** record the onboarding decision that software-analysis DEC-001 point 11 leaves open, from what areas 0 and 1 showed.

## What is already decided

The records settle the principle and the engine, and they leave the onboarding lifecycle open.

- **The principle for analysis** (software-analysis DEC-001 point 9). On a brownfield project, the code, the existing documents and the decisions are the ground truth.
  - **The order is reversed:** an agent derives candidate actors, use cases and terms from them, and a person confirms.
  - **The signal is *uncovered surface*:** the paths the project declares its analysis should cover, against what the artefacts anchor to.
  - **The end:** onboarding needs a non-empty declared surface, and it is complete when that surface is covered. An artefact nothing embodies carries `unanchored-because`.
- **The onboarding lifecycle is explicitly not decided** (software-analysis DEC-001 point 11): "lifecycles on the process substrate (a planned revalidation; onboarding) … each needs its own decision when a real need arrives." The need has arrived.
- **The path for documentation** (living-docs README, "Onboarding an existing project", and living-docs DEC-001 point 8):
  1. Declare where documentation lives.
  2. Ask the agent to onboard.
  3. The agent drafts *one plan* in four parts behind a single gate: spaces, splits and rewrites, anchors, mapping.
  4. On approval, the agent drafts one reviewable change per step into the agent workspace, and stops.
  5. Repeat until the declared surface is covered and no page is unanchored without an accepted reason.
- **The engine underneath** (COR-050): anchors, the change check, the declared surface (point 8), `unanchored-because` (point 1) and enforcing mode. It has been live on project-kit as a required status since 1 October.

## What changed since 1 October

The pilot analysis is gone, and the full analysis of pkit has begun with the core's actors.

- **The pilot is removed** (#1340). The maintainer decided to delete the pilot analysis outright, as an exception to the append-only rule.
  - **Its ids are free:** a declared setting names the removal commit and the ids that it frees (#1342, PR #1343).
  - **Records refined in place:** software-analysis DEC-001 point 3 and project-management DEC-054 point 2.
  - **Numbering:** the full analysis restarts at UC-001 and JRN-001.
- **Layering** (the maintainer, 5 October). The core comes first, which is pkit with no capability installed.
  - Each capability's actors come with that capability's area.
  - No category field marks the layer. The layer shows in what an actor rests on.
  - The use-case areas follow the same split, `core/…` against `<capability>/…`.
- **Rules for actors**, settled while the core's actors were drafted:
  - The primary actor is the role whose goal it is.
  - An agent appears only in steps.
  - A system is an actor only when it starts work on its own trigger, as the CI pipeline does.
  - An actor anchors to records, and to code only where the code embodies the role.
- **The writing rules** (`WRITE` 1.0.0, #1348, PR #1349). They came from a style trial of ISO 24495-1 against ASD-STE100 (`.pkit/scratchpad/done/2026-10-05-writing-style-trial.md`).
  - Ten rules are accepted. RS-WRITE-002, on labels, and RS-WRITE-006, on one idea per sentence, are held back.
  - The analysis follows WRITE through `.pkit/rules/project.md`.
  - RS-WRITE-014, cite by permanent id, is proposed (#1354, PR #1355).
  - Documentation pages adopt WRITE later, in stages (#1350).
- **A declared structure per kind** (#1352, design note on PR #1353). The design covers declared structures, templates with hints, and a meta rule.
  - It folds in #1346, one file per actor. No migration is needed, since software-analysis is installed nowhere else.
  - It folds in #1351, the text the stamp writes.
  - The analysis's own rule set waits for it. That set, drafted as `ANALYSIS`, holds the rule on needs and goals and the lists of labels, and its name is still open.

## What exists to do it with

The analysis side has a principle but no written procedure, and the documentation side has a procedure nobody has run.

| | software-analysis | living-docs |
|---|---|---|
| Principle | DEC-001 point 9 | DEC-001 point 8 |
| Procedure | **None written.** The `analysis-author` skill adds one artefact at a time. Nothing says how to go from a codebase to a set of candidates. | README section, five steps |
| Agent | `analysis-resolver`, for drift. Its body says it is *not* for onboarding. | `living-docs`. "Onboard existing documentation" is one of its flows. |
| Exercised | The pilot (coordination, #890), removed by #1340. Then area 0's core actors (#1344), the first artefacts of the full analysis. | never end to end |
| Declared surface on project-kit | The project's one surface, `friction.surface`. The capability declares none of its own (DEC-001 point 2). | the same surface: the code the old code-to-doc mapping obliged documentation for |

So the gap is on the analysis side: a principle without a written procedure, and an agent that excludes the job. Area 0 ran a procedure by hand (see "Candidate shapes for the analysis onboarding").

## Project-kit as the brownfield

Project-kit has rich ground truth, and its analysis has only just begun.

- **Analysis:** one file, the eight core actors (`tech-docs/analysis/use-case-model/actors.md`, #1344). The pilot's 15 files were removed (#1340).
- **Decisions:** 61 ADRs, the core and project records, and the capability DECs. They are rich ground truth, mostly accepted.
- **Documents:**
  - 19 READMEs under `.pkit/` and the root README are declared as user-space pages.
  - CONTRIBUTING and the release README are declared as technical pages.
  - `docs/` does not exist, and none of these was written for a reader the spaces define.
- **Code:** `src/project_kit/` (the backbone and engines), six capabilities and one adapter.

The area map runs basics first, in two layers:

- **The core**, pkit with no capability installed:
  0. Vocabulary: the core's actors (done) and the glossary (next). Every later artefact cites them.
  1. Backbone lifecycle: init/install, sync, upgrade and pinning, migrations, validate, status.
  2. Records: decisions, the acceptance gate, rule sets, scratchpad.
  3. CLI and configuration: the dispatcher, project config, consent, documentation roots.
  4. Engines: anchors and friction, the process substrate, the permission model, and connections and data points.
  5. Release and versioning: changesets, the release step, the changelog.
  6. Adapters: claude-code's deploy, settings merge, hooks and sandbox.
- **The capabilities**, each with its own actors:
  7. One area for each capability: project-management (with the pm and reviewer actors), software-engineering, software-analysis, living-docs, evidence and demo-recording.
- **Coordination** (8): the pilot's area, removed with the pilot (#1340). Its use cases will be written afresh.

## Forces

These forces shape the procedure, from what it costs to who confirms each step.

- **Cost.** Deriving candidates means reading code and records, and an area is tens of files. The expensive failure is writing bodies for use cases that the person then rejects or regroups. So the list must be approved before any body is written.
- **Enforcing friction.** Every accepted artefact is under the gate from the commit it lands in. Anchoring early is cheap to state, and costly to maintain while the area's code is still moving. That argues for onboarding stable areas first, and for anchoring at the grain the code actually changes at.
- **Existing documents are both input and output.** The READMEs are the best description of intent the project has, and the analysis is derived from them. Later they are rewritten as pages anchored to that analysis. Onboarding must not rewrite them on the way in.
- **Order.** Vocabulary comes before use cases. The backbone comes before what builds on it, and analysis comes before documentation. Within that, areas are independent module families and can run in parallel (the same-module rule, pm skill `batch-plan`).
- **Who confirms.** Software-analysis DEC-001 says a person. With per-area gates, that is roughly ten approvals of a list plus ten of the result. The maintainer's attention is the scarce resource, more than tokens.
- **It must be a procedure an adopter can run**, not project-kit's private effort. What is learned here becomes the capability's README section, a skill or agent flow, the brownfield demo (#397) and the adoption fast-path (#389).

## Evidence from 1 October: page grain is a cost, not only a style

Three pages, each anchored to a whole tree, took almost every stamp conflict of the day.

- **The pages:** `.pkit/cli/README.md`, `.pkit/capabilities/project-management/README.md` and `.pkit/README.md`.
- **Their anchors:** each is one page anchored to a whole tree. The CLI reference anchors most of `src/project_kit/`. The pm README anchors the capability's `scripts/**`, `schemas/**` and `decisions/**`.
- **The effect:** nearly every pull request changes one of their anchors, and must answer it. That pull request then collides with every other open pull request that did the same. About a dozen merges of `main` on 1 October were for these three files alone.
- **The contrast:** take a page that describes one command group or one sub-system, anchored to that code only. The changes that touch that code answer it, and no others do.

So the documentation onboarding's "splits and rewrites" step is not cosmetic for project-kit.

- **The split:** each tree-wide page splits by the unit its readers look things up by, such as a command group or a lifecycle verb family.
- **Why it matters:** that split is what makes the enforcing gate affordable with several changes in flight.
- **The same for analysis:** a use case anchored to a directory is answered by everything. A use case anchored to the command it describes is answered by little.
- **So:** anchor grain belongs among the things each area's gate reviews.

## Evidence from 2 October: sentence grain is a cost too

Once tooling handled the stamp conflicts, the conflicts left were in single long lines of body text.

- **The setting:** eight to ten changes were in flight. Tooling (`pkit friction resolve`) handled the stamp conflicts of 1 October.
- **What remained:** four **body** conflicts in one day that needed a person. All four had one shape: a single very long line that several changes each extend.
- **Three were table rows** in `.pkit/cli/README.md`:
  - the `packages` and `connections` rows of the validate members table
  - the one row that documents every `pull-request` subcommand
  - the `repository base` row
- **One was a paragraph:** the capability README's forward-cascade paragraph. It is a single paragraph of some four hundred words, and three pull requests in a row each added a clause to it.
- **Why:** Git merges by line. So a row or paragraph that is one line conflicts whenever two changes touch it, however unrelated their clauses.

So the unit to split is not only the page, one page per command group, but the line:

- one subcommand per row
- one member per row, with its details in a sub-list below the table
- a long rule as a lead sentence plus a short list

A reviewer asked for exactly that split of the forward-cascade paragraph, for readability. Mergeability is the second reason.

This belongs in the documentation onboarding's "splits and rewrites" step, and as a rule for the reference pages' format. A row or paragraph that keeps growing is a sign that it holds more than one thing.

## Candidate shapes for the analysis onboarding

Area 0 ran shape A, with agents drafting behind a gate.

- **A. A sub-procedure of the authoring skill**, "onboard an area":
  1. Read the area's surface, its documents and its decisions.
  2. List candidates with evidence, and stop for approval.
  3. Stamp each with `pkit analysis new`, and write bodies.
  - **Weight:** the lightest. The session's own agent does the reading, and nothing persists between sessions except the artefacts.
- **B. A propose-only agent flow**, mirroring living-docs. One plan per area goes behind one gate. Then one reviewable change per step is written to the agent workspace.
  - **The plan holds:**
    - the candidates, each citing the code, document or decision it comes from
    - what each would anchor to
    - what stays unanchored, and why
  - **Fit:** it is consistent with how both capabilities' agents already work. They propose, and never apply.
  - **Weight:** it costs a new agent, or widening `analysis-resolver`, whose body draws the line the other way today.
- **C. A process definition** on the process substrate (COR-033). Onboarding becomes a lifecycle with states, so it survives sessions and its position is detected, not remembered.
  - **States:** surface declared, area map approved, and per area: candidates approved, authored, covered.
  - **Weight:** the heaviest, and arguably premature before the procedure has been run once.
  - **Note:** it is the only shape that software-analysis DEC-001 point 11 names.

A and B differ in who reads. C is orthogonal, and can wrap either later. The cheap way to find out is to run one area by hand under A's shape, and measure it. Only then comes the choice between A and B.

What area 0 ran:

- **The reading:** dispatched agents read the sources and drafted the candidates in the agent workspace. A critic reviewed two of the four drafts.
- **The list:** the maintainer shaped it in chat. He asked for the layering, which took the list from ten actors to eight.
- **The gate:** he chose to review the stamped actors in a pull request rather than approve them in chat. He approved them there for merge.

## Area 0: the core actors

The drafting took six agent runs and about 1.2 million tokens, and the review ran in a pull request.

- **Candidates:** the derivation proposed 9. Draft 2 held 10 after the first critic, and draft 3 held 8 core actors after the layering. The pm and reviewer actors wait for the project-management area.
- **Result:** all eight were merged (#1344, PR #1345). They are adopter, operator, developer, merge-authoriser, component-author, methodology-maintainer, ai-agent and ci-pipeline.
- **The derivation's reading:** it touched about 50 files, and read about 25 of them in substance.

| Step | Tokens | Tool uses | Wall-clock |
|---|---:|---:|---:|
| Derivation: 9 candidates, 6 open questions | 221,698 | 68 | 12.5 min |
| Critic on draft 1: 4 red flags | 200,498 | 74 | 12 min |
| Draft 2: 10 actors, 2 open questions | 187,620 | 67 | 12 min |
| Draft 3, core only: 8 actors | 215,930 | 57 | 12 min |
| Critic on draft 3: 1 red flag, 6 layer gaps | 199,793 | 48 | 10 min |
| Draft 4: 8 actors, 52 needs | 186,856 | 67 | 12 min |
| **Total** | **1,212,395** | **381** | **70.5 min** |

- **Approvals:** up to draft 4, the maintainer took three turns. On the pull request, he answered 12 questions one by one, then approved the merge.
- **The 12 questions:** the rewrite by WRITE held back pronouns, term pairs and splits, under RS-WRITE-013. They went on the pull request as a comment. Two answers set terms:
  - "Change" is the core's unit of work. The project-management area will extend the developer with the Task.
  - "The system" is the term for the system under discussion. It will be the glossary's first entry, and the word is reserved.
- **Friction on existing pages:** none. PR #1345 wrote no friction answers.
- **Uncovered surface:** unchanged. All eight actors anchor to records only, and a record anchor covers no path.
- **Not measured:** the stamping, the style trial, the rewrite by WRITE and the review. The measures stop at draft 4.

Lessons for the process:

- **Drafts:** they go on a branch with a draft pull request from the start, not in the agent workspace.
- **Held questions:** questions that RS-WRITE-013 holds back go on the pull request as a comment.
- **Review:** the maintainer reviews in the pull request.

## What to measure on the next areas

The measures set for the first areas still stand, and area 0 recorded only those of its drafting.

- tokens and wall-clock per step
- candidates proposed against candidates accepted
- artefacts per area
- uncovered surface before and after
- friction that the new artefacts raise on existing pages
- how many approvals the maintainer gave, and how long each waited

## Settled questions

Five of the note's questions are settled by what area 0 did and by the maintainer's answers.

- **Shape A or B:** shape A, with agents drafting behind a gate (see "Candidate shapes for the analysis onboarding"). No onboarding decision is recorded yet.
- **The declared surface for analysis:** the same paths as for documentation.
  - Project-kit has one declared surface, `friction.surface` in `.pkit/project/config.yaml`. Software-analysis declares none of its own (software-analysis DEC-001 point 2).
  - The actors' derivation read that surface as the code the analysis should eventually cover.
  - A use case's coarser anchor, a command rather than every module behind it, is a question of anchor grain. Each area's gate reviews it.
- **The area map:** the map above, in two layers. The core's areas come first, and each capability is an area of its own, with that capability's actors. The question's risk still stands: a cut by code tree may give an analysis that mirrors the implementation.
- **The vocabulary pass:** it grows by layer. The core's eight actors came before any use case, and each capability's actors come with its area. The glossary starts next, with "the system".
- **One gate or two:** two, in practice. The maintainer shaped the list in chat, then reviewed the stamped bodies in the pull request. The regrouping showed at the list, where ten actors became eight.

## Open questions

- Does the documentation onboarding wait for *all* areas? Or can a space be onboarded once the areas it describes are covered, such as the technical space after areas 0–5? The maintainer's rule is sequence, and a per-space sequence may still honour it.
- What happens to the 19 READMEs? Do they stay in-tree pages for adopters reading the installed kit, with `docs/` added for the user space? Or does `docs/` replace them?
- Should the result be a milestone of its own ("Brownfield onboarding, proven on project-kit"), with the documentation as the milestone after it? So far, none of the onboarding's issues carries a milestone.
