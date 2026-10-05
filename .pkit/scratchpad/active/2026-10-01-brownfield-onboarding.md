---
authors:
  - Aleš Kalfas
started: 2026-10-01
---

# Brownfield onboarding of analysis and documentation, tried on project-kit

## The question

An existing project — code, decisions and documents already there, no analysis, nothing anchored — installs software-analysis and living-docs. In what order, in what units, behind which gates, and with whose judgment does it get from that starting point to "the declared surface is covered"? And what does running that on project-kit itself look like, since project-kit is exactly such a project?

The operator's constraint: analysis first, for the whole of project-kit from the basics to the particular capabilities; user documentation only afterwards. Done together, the documentation would be rewritten every time the analysis under it moves, and that rewriting is the token cost to avoid.

## What is already decided

- **The principle for analysis** (software-analysis DEC-001 point 9). On a brownfield project the code, the existing documents and the decisions are the ground truth, so the usual order is reversed: an agent derives candidate actors, use cases and terms from them, a person confirms. The signal is *uncovered surface* — the paths the project declares its analysis should cover against what the artefacts anchor to. Onboarding needs a non-empty declared surface and is complete when that surface is covered; an artefact nothing embodies carries `unanchored-because`.
- **The onboarding lifecycle is explicitly not decided** (DEC-001 point 11): "lifecycles on the process substrate (a planned revalidation; onboarding) … each needs its own decision when a real need arrives." The need has arrived.
- **The path for documentation** (living-docs README, "Onboarding an existing project"; DEC-001 point 8): declare where documentation lives; ask the agent to onboard; it drafts *one plan* in four parts (spaces, splits and rewrites, anchors, mapping) behind a single gate; on approval it drafts one reviewable change per step into the agent workspace and stops; repeat until the declared surface is covered and no page is unanchored without an accepted reason.
- **The engine underneath** (COR-050): anchors, the change check, the declared surface (point 8), `unanchored-because` (point 1), enforcing mode — live on project-kit as a required status since 1 October.

## What exists to do it with

| | software-analysis | living-docs |
|---|---|---|
| Principle | DEC-001 point 9 | DEC-001 point 8 |
| Procedure | **none** — the `analysis-author` skill adds one artefact at a time; nothing says how to go from a codebase to a set of candidates | README section, five steps |
| Agent | `analysis-resolver` — for drift, and its body says it is *not* for onboarding | `living-docs` — "onboard existing documentation" is one of its flows |
| Exercised | one area, by hand (coordination: UC-001–010, JRN-001/002, #890) | never end to end |
| Declared surface on project-kit | **none found** for analysis (only its location, `tech-docs/analysis`) | set: the code the old code-to-doc mapping obliged documentation for |

So the gap is on the analysis side: a principle without a procedure, an agent that excludes the job, and no declared surface to measure against. The documentation side has a procedure nobody has run.

## Project-kit as the brownfield

- Analysis: 15 files — actors, glossary, one area (coordination), one revalidation record.
- Decisions: 59 ADRs, the core and project records, the capability DECs — rich ground truth, mostly accepted.
- Documents: 19 READMEs under `.pkit/` declared as user-space pages, the root README, CONTRIBUTING and the release README as technical pages; `docs/` does not exist; none was written for a reader the spaces define.
- Code: `src/project_kit/` (the backbone and engines), five capabilities, one adapter.

A first cut of the areas, basics first (to be confirmed, not decided here):

0. Vocabulary — actors and glossary across the whole system (every later artefact cites them)
1. Backbone lifecycle — init/install, sync, upgrade and pinning, migrations, validate, status
2. Records — decisions, the acceptance gate, rule sets, scratchpad
3. CLI and configuration — the dispatcher, project config, consent, documentation roots
4. Engines — anchors and friction; the process substrate; the permission model; connections and data points
5. Release and versioning — changesets, the release step, the changelog
6. Adapters — claude-code: deploy, settings merge, hooks, sandbox
7. Capabilities — project-management; software-engineering; software-analysis; living-docs; evidence; demo-recording
8. Coordination — exists; revalidate against the rest

## Forces

- **Cost.** Deriving candidates means reading code and records; an area is tens of files. The expensive failure is writing bodies for use cases the person then rejects or regroups — so the list must be approved before any body is written.
- **Enforcing friction.** Every accepted artefact is under the gate from the commit it lands in. Anchoring early is cheap to state and costly to maintain while the area's code is still moving — an argument for onboarding stable areas first and for anchoring at the grain the code actually changes at.
- **Existing documents are both input and output.** The READMEs are the best description of intent the project has; the analysis is derived from them — and later they are rewritten as pages anchored to that analysis. Onboarding must not rewrite them on the way in.
- **Order.** Vocabulary before use cases; backbone before what builds on it; analysis before documentation. Within that, areas are independent module families and can run in parallel (the same-module rule, pm skill `batch-plan`).
- **Who confirms.** DEC-001 says a person. With per-area gates that is roughly ten approvals of a list plus ten of the result — the operator's attention is the scarce resource, more than tokens.
- **It must be a procedure an adopter can run**, not project-kit's private effort: what is learned here becomes the capability's README section, a skill or agent flow, and the brownfield demo (#397) and adoption fast-path (#389).

## Evidence from 1 October: page grain is a cost, not only a style

Three pages took almost every stamp conflict of the day: `.pkit/cli/README.md`, `.pkit/capabilities/project-management/README.md` and `.pkit/README.md`. Each is one page anchored to a whole tree (the CLI reference anchors most of `src/project_kit/`; the pm README anchors the capability's `scripts/**`, `schemas/**` and `decisions/**`), so nearly every pull request changes one of its anchors, must answer it, and collides with every other open pull request that did the same — about a dozen merges of `main` on 1 October were for these three files alone. A page that describes one command group or one sub-system, anchored to that code only, is answered by the changes that touch it and by no others.

So the documentation onboarding's "splits and rewrites" step is not cosmetic for project-kit: splitting the three tree-wide pages by the unit their readers look things up by (a command group; a lifecycle verb family) is what makes the enforcing gate affordable with several changes in flight. The same holds for analysis artefacts: a use case anchored to a directory is answered by everything; anchored to the command it describes, by little. Anchor grain belongs among the things each area's gate reviews.

## Evidence from 2 October: sentence grain is a cost too

With eight to ten changes in flight, the stamp conflicts of 1 October were handled by tooling (`pkit friction resolve`), and what remained were **body** conflicts that needed a person — four in one day, all of one shape: a single very long line that several changes each extend. Three were table rows in `.pkit/cli/README.md` (the `packages` and `connections` rows of the validate members table; the one row that documents every `pull-request` subcommand; the `repository base` row), and one was the capability README's forward-cascade paragraph, a single paragraph of some four hundred words that three pull requests in a row each added a clause to. Git merges by line, so a row or paragraph that is one line conflicts whenever two changes touch it, however unrelated their clauses.

So the unit to split is not only the page (one page per command group) but the line: one subcommand per row, one member per row with its details in a sub-list below the table, a long rule as a lead sentence plus a short list. A reviewer asked for exactly that split of the forward-cascade paragraph for readability; mergeability is the second reason. This belongs in the documentation onboarding's "splits and rewrites" step, and as a rule for the reference pages' format (a row or paragraph that keeps growing is a sign it holds more than one thing).

## Candidate shapes for the analysis onboarding

- **A. A sub-procedure of the authoring skill** — "onboard an area": read the area's surface and its documents and decisions, list candidates with evidence, stop for approval, then stamp each with `pkit analysis new` and write bodies. Lightest; the session's own agent does the reading; nothing persists between sessions except the artefacts.
- **B. A propose-only agent flow**, mirroring living-docs: one plan per area behind one gate (candidates, each citing the code, document or decision it comes from; what it would anchor to; what stays unanchored and why), then one reviewable change per step written to the agent workspace. Consistent with how both capabilities' agents already work (propose, never apply); costs a new agent or widening `analysis-resolver`, whose body draws the line the other way today.
- **C. A process definition** on the process substrate (COR-033): onboarding as a lifecycle with states — surface declared, area map approved, per area: candidates approved, authored, covered — so it survives sessions and its position is detected, not remembered. Heaviest; the only one DEC-001 point 11 names; arguably premature before the procedure has been run once.

A and B differ in who reads; C is orthogonal and can wrap either later. Running one area by hand under A's shape, measuring it, and only then deciding between A and B is the cheap way to find out.

## What to measure on the first areas

Tokens and wall-clock per area; candidates proposed against accepted; artefacts per area; uncovered surface before and after; friction raised on existing pages by the new artefacts; how many approvals the operator gave and how long each waited.

## Open questions

- What is project-kit's declared surface for analysis — the same paths as for documentation, or coarser (a use case anchors to a command, not to every module behind it)?
- Is the area map above the right cut — by code tree, by CLI noun, or by actor's goal? Use cases are goals of actors; cutting by code tree risks an analysis that mirrors the implementation.
- Where does the vocabulary pass stop — every term in the glossary before any use case, or the terms the first areas need, growing per area?
- One gate per area (the list) or two (the list, then the bodies)? The second is where regrouping shows.
- Does the documentation onboarding wait for *all* areas, or can a space be onboarded once the areas it describes are covered (the technical space after areas 0–5, say)? The operator's rule is sequence; a per-space sequence may still honour it.
- What happens to the 19 READMEs: do they stay in-tree pages for adopters reading the installed kit, with `docs/` added for the user space, or does `docs/` replace them?
- Should the result be a milestone of its own ("Brownfield onboarding, proven on project-kit") with the documentation as the milestone after it?

## Status

Active. Next: confirm the area map and the declared surface with the operator, run area 0 (vocabulary) and area 1 (backbone lifecycle) under shape A while measuring, then decide A or B and record the onboarding decision DEC-001 point 11 leaves open.
