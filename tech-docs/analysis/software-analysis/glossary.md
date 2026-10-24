---
builds-on:
  - analysis: core
    version: 2.0.0
    terms:
      - {id: TERM-adapter, name: adapter}
      - {id: TERM-agent-definition, name: agent definition}
      - {id: TERM-agent-workspace, name: agent workspace}
      - {id: TERM-anchor, name: anchor}
      - {id: TERM-answer, name: answer}
      - {id: TERM-artefact, name: artefact}
      - {id: TERM-artefact-type, name: artefact type}
      - {id: TERM-backbone, name: backbone}
      - {id: TERM-backbone-configuration, name: backbone configuration}
      - {id: TERM-base, name: base}
      - {id: TERM-capability, name: capability}
      - {id: TERM-change, name: change}
      - {id: TERM-change-check, name: change check}
      - {id: TERM-component, name: component}
      - {id: TERM-debt, name: debt}
      - {id: TERM-decision-record, name: decision record}
      - {id: TERM-default-branch, name: default branch}
      - {id: TERM-documentation-root, name: documentation root}
      - {id: TERM-friction, name: friction}
      - {id: TERM-head, name: head}
      - {id: TERM-install, name: install}
      - {id: TERM-place, name: place}
      - {id: TERM-project, name: project}
      - {id: TERM-pull-request, name: pull request}
      - {id: TERM-reviewer, name: reviewer}
      - {id: TERM-rule, name: rule}
      - {id: TERM-rule-set, name: rule set}
      - {id: TERM-skill, name: skill}
      - {id: TERM-stamp, name: stamp}
      - {id: TERM-storyboard, name: storyboard}
      - {id: TERM-system, name: system}
      - {id: TERM-validation, name: validation}
      - {id: TERM-whole-repository-check, name: whole-repository check}
    actors:
      - id: ACT-developer
        name: Developer
        needs:
          - Revise the analysis before a proposed change is built, naming the design I reviewed and pinning the text I read.
          - Revalidate the analysis after a change, from an agent's proposed outcome for each flagged artefact, and never rewrite the analysis to match broken code.
          - Describe my existing project from its code, documents and decisions, with an agent deriving candidates that I confirm.
          - Free the ids of artefacts nothing cites, such as an abandoned pilot, so new artefacts may take those ids again.
      - id: ACT-adopter
        name: Adopter
        needs:
          - Choose the parts of each kind of analysis artefact as I adopt software analysis, keeping, relabelling or adding to the shipped ones.
      - id: ACT-ai-agent
        name: AI agent
      - id: ACT-operator
        name: Operator
TERM-analysis:
  name: analysis
  status: active
  definition: "account of what one component must do and for whom, kept as anchored artefacts under the project's internal documentation root"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/software-analysis/schemas/config.schema.json
          - .pkit/capabilities/software-analysis/scripts/_lib/analyses.py
        record:
          - software-analysis:DEC-001#2
TERM-artefact-kind:
  name: artefact kind
  noun-forms: [artefact kinds]
  status: active
  definition: "category of an analysis's anchored entries and files, such as its actors or use cases, sharing one schema, place and layout of parts"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/software-analysis/schemas/artefact-kinds.yaml
        record:
          - software-analysis:DEC-001#1
TERM-candidate:
  name: candidate
  noun-forms: [candidates]
  status: active
  definition: "artefact or revalidation record of an analysis, written but not yet committed, which a person confirms or discards"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/software-analysis/skills/analysis-author/choose-templates.md
          - .pkit/capabilities/software-analysis/skills/analysis-author/build-analysis.md
        record:
          - software-analysis:DEC-001#1
          - software-analysis:DEC-001#9
      revalidated:
        at: 2026-10-24T01:59:05Z
        outcome: unchanged
        unchanged-because: The change adds where brownfield onboarding starts and ends to the build. A candidate is still an artefact or a record written but not yet committed, which a person confirms or discards.
TERM-declared-structure:
  name: declared structure
  noun-forms: [declared structures]
  status: active
  definition: "data listing in order the parts every member of an artefact kind, or every revalidation record, carries, each with its id, label and example"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/software-analysis/schemas/artefact-kinds.yaml
          - .pkit/capabilities/software-analysis/schemas/artefact-kinds.schema.json
          - .pkit/capabilities/software-analysis/scripts/_lib/structure.py
        record:
          - software-analysis:DEC-001#1
TERM-design-source:
  name: design source
  noun-forms: [design sources]
  status: active
  definition: "text stating a proposed change that a planned revalidation read, named in its revalidation record with a pointer to the exact text read"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/software-analysis/schemas/revalidation-record.schema.json
          - .pkit/capabilities/software-analysis/scripts/_lib/pointers.py
        record:
          - software-analysis:DEC-001#6
TERM-freed-id:
  name: freed id
  noun-forms: [freed ids]
  status: active
  definition: "number of a removed use case, journey or requirement that nothing cites, which the project declares the stamp may give again"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/software-analysis/scripts/_lib/numbering.py
        record:
          - software-analysis:DEC-001#3
TERM-hint:
  name: hint
  status: active
  definition: "one-line comment that the stamp leaves where a writer fills a part or a front-matter field, saying what goes there and giving an example"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/software-analysis/scripts/_lib/render.py
          - .pkit/capabilities/software-analysis/scripts/_lib/placeholder.py
        record:
          - software-analysis:DEC-001#1
TERM-revalidation:
  name: revalidation
  noun-forms: [revalidations]
  status: active
  definition: "review of some analysis artefacts against one state of the system, a proposed design or the code, that judges whether each description still holds"
  pkit:
    friction:
      anchors:
        record:
          - software-analysis:DEC-001#4
          - software-analysis:DEC-001#5
TERM-revalidation-outcome:
  name: revalidation outcome
  noun-forms: [revalidation outcomes]
  status: active
  definition: "judgement ending one analysis artefact's review: it holds, the analysis was stale, the code regressed, or a gap was found"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/software-analysis/scripts/_lib/resolve.py
          - .pkit/capabilities/software-analysis/scripts/_lib/answers.py
        record:
          - software-analysis:DEC-001#5
      revalidated:
        at: 2026-10-24T02:12:38Z
        outcome: unchanged
        unchanged-because: The term still names the four outcomes and how they map onto the two answers. The change makes pkit analysis propose answer a boxed regression updated, as its distinctions already say.
TERM-revalidation-proposal:
  name: revalidation proposal
  noun-forms: [revalidation proposals]
  status: active
  definition: "draft by the analysis-resolver agent that gives each flagged analysis artefact the result its evidence supports, and how a person records it, or a question"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/software-analysis/agents/analysis-resolver/analysis-resolver.md
        record:
          - software-analysis:DEC-001#5
      revalidated:
        at: 2026-10-24T02:12:40Z
        outcome: unchanged
        unchanged-because: The term still names what the agent drafts for a person to record. The change adds how the agent tells a boxed regression from one no record decides, which the term does not describe.
TERM-revalidation-record:
  name: revalidation record
  status: active
  definition: "file of an analysis logging a planned review of its artefacts, or one finding a regression, a gap or a stale artefact a person confirmed"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/software-analysis/schemas/revalidation-record.schema.json
          - .pkit/capabilities/software-analysis/scripts/_lib/revalidation.py
        record:
          - software-analysis:DEC-001#6
TERM-shortfall:
  name: shortfall
  noun-forms: [shortfalls]
  status: active
  definition: "step or variant of a use case that an accepted decision record decides and the system does not carry out yet, marked by a box"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/software-analysis/scripts/_lib/shortfalls.py
          - .pkit/capabilities/software-analysis/schemas/use-case.schema.json
        record:
          - software-analysis:DEC-001#1
TERM-tightening:
  name: tightening
  noun-forms: [tightenings]
  status: active
  definition: "group in a project's own data adding parts to an artefact kind's declared structure, or requiring more of it, naming the project's rule for it"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/software-analysis/schemas/structures.schema.json
          - .pkit/capabilities/software-analysis/scripts/_lib/project_structure.py
        record:
          - software-analysis:DEC-001#1
TERM-use-case:
  name: use case
  noun-forms: [use cases]
  status: active
  definition: "description of how the system fulfils one actor's goal, in a main path of steps and the variants that branch from it"
  pkit:
    friction:
      anchors:
        path:
          - .pkit/capabilities/software-analysis/schemas/use-case.schema.json
        record:
          - software-analysis:DEC-001#1
          - software-analysis:DEC-001#3
---

# Glossary

The words of the domain and what each means. A term's id is stable, and its name may change. The names it replaces are kept.

- **From core at 2.0.0:** the areas up to `030-change`. No release holds the core's analysis yet, so the links name the next release, 2.0.0, rather than software-analysis's floor, 1.149.0.
  - **Term:** [adapter](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-adapter--adapter)
  - **Term:** [agent definition](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-agent-definition--agent-definition)
  - **Term:** [agent workspace](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-agent-workspace--agent-workspace)
  - **Term:** [anchor](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-anchor--anchor)
  - **Term:** [answer](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-answer--answer)
  - **Term:** [artefact](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-artefact--artefact)
  - **Term:** [artefact type](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-artefact-type--artefact-type)
  - **Term:** [backbone](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-backbone--backbone)
  - **Term:** [backbone configuration](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-backbone-configuration--backbone-configuration)
  - **Term:** [base](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-base--base)
  - **Term:** [capability](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-capability--capability)
  - **Term:** [change](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-change--change)
  - **Term:** [change check](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-change-check--change-check)
  - **Term:** [component](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-component--component)
  - **Term:** [debt](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-debt--debt)
  - **Term:** [decision record](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-decision-record--decision-record)
  - **Term:** [default branch](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-default-branch--default-branch)
  - **Term:** [documentation root](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-documentation-root--documentation-root)
  - **Term:** [friction](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-friction--friction)
  - **Term:** [head](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-head--head)
  - **Term:** [install](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-install--install)
  - **Term:** [place](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-place--place)
  - **Term:** [project](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-project--project)
  - **Term:** [pull request](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-pull-request--pull-request)
  - **Term:** [reviewer](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-reviewer--reviewer)
  - **Term:** [rule](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-rule--rule)
  - **Term:** [rule set](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-rule-set--rule-set)
  - **Term:** [skill](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-skill--skill)
  - **Term:** [stamp](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-stamp--stamp)
  - **Term:** [storyboard](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-storyboard--storyboard)
  - **Term:** [system](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-system--system)
  - **Term:** [validation](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-validation--validation)
  - **Term:** [whole-repository check](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/glossary.md#term-whole-repository-check--whole-repository-check)
  - **Actor:** [Developer](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/use-case-model/actors/ACT-developer.md)
    - Revise the analysis before a proposed change is built, naming the design I reviewed and pinning the text I read.
    - Revalidate the analysis after a change, from an agent's proposed outcome for each flagged artefact, and never rewrite the analysis to match broken code.
    - Describe my existing project from its code, documents and decisions, with an agent deriving candidates that I confirm.
    - Free the ids of artefacts nothing cites, such as an abandoned pilot, so new artefacts may take those ids again.
  - **Actor:** [Adopter](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/use-case-model/actors/ACT-adopter.md)
    - Choose the parts of each kind of analysis artefact as I adopt software analysis, keeping, relabelling or adding to the shipped ones.
  - **Actor:** [AI agent](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/use-case-model/actors/ACT-ai-agent.md)
  - **Actor:** [Operator](https://github.com/aleskalfas/project-kit/blob/v2.0.0/tech-docs/analysis/core/use-case-model/actors/ACT-operator.md)

## TERM-analysis — analysis

Explained in [VIEW-analyses-and-use-cases](domain-model/010-analyses-and-use-cases.md#analysis).

**Example:** project-kit keeps one analysis for its core, in `tech-docs/analysis/core/`, and one for each [capability](../core/glossary.md#term-capability--capability) that keeps one, such as `tech-docs/analysis/software-analysis/`.

**Distinctions:**

- **Documentation for users:** what the [system](../core/glossary.md#term-system--system) does and how to use it, for whoever receives a [component](../core/glossary.md#term-component--component). An analysis is internal documentation for those who develop its component, and never ships with it (DEC-001 point 2).
- **Decisions and architecture:** how the system is built to do what it must, and why. An analysis states what the system must do, and points at them by anchors, never the reverse (DEC-001 point 11).
- **Testing:** running the software to see whether it does what a description says. An analysis is judged by reading, and runs nothing (DEC-001 point 7).

## TERM-artefact-kind — artefact kind

Explained in [VIEW-kinds-and-structures](domain-model/030-kinds-and-structures.md#artefact-kind).

**Example:** `use-case` is an artefact kind. Each of its members is a file under `use-case-model/use-cases/`, and its [place](../core/glossary.md#term-place--place) gives each the type `software-analysis:use-case`.

**Distinctions:**

- **Artefact type:** the name a place gives each [artefact](../core/glossary.md#term-artefact--artefact) in it, such as `software-analysis:use-case`, for a [rule set](../core/glossary.md#term-rule-set--rule-set)'s scope to select. Each artefact kind lies in a place of its own, which gives one type (DEC-001 point 2).
- **The revalidation record's kind:** declared beside the artefact kinds, though a [revalidation record](#term-revalidation-record--revalidation-record) is no artefact. It has a [declared structure](#term-declared-structure--declared-structure), but no place, no type and no [tightening](#term-tightening--tightening), and the [capability](../core/glossary.md#term-capability--capability) checks its structure always (DEC-001 point 1).

## TERM-candidate — candidate

Explained in [VIEW-kinds-and-structures](domain-model/030-kinds-and-structures.md#candidate).

**Example:** on a brownfield [project](../core/glossary.md#term-project--project), an agent derives the term `invoice` from the billing code and a record, and stamps it. The developer confirms it before it is committed. On adoption, the adopter fills a [use case](#term-use-case--use-case) with a real case of the project, to judge the parts of that [artefact kind](#term-artefact-kind--artefact-kind).

**Distinctions:**

- **An artefact in force:** one committed to the [analysis](#term-analysis--analysis), whose id is taken for good. A candidate takes no id until it is committed (DEC-001 point 3).
- **A proposed decision record:** a record whose status is `proposed`, which binds nothing yet. A candidate is an [artefact](../core/glossary.md#term-artefact--artefact) or a [revalidation record](#term-revalidation-record--revalidation-record) of the analysis, never a [decision record](../core/glossary.md#term-decision-record--decision-record).

## TERM-declared-structure — declared structure

Explained in [VIEW-kinds-and-structures](domain-model/030-kinds-and-structures.md#declared-structure).

**Example:** the declared structure of `use-case`, in `schemas/artefact-kinds.yaml`, lists the heading, then *Goal*, *Other actors*, *Preconditions*, *Assumptions*, *Trigger*, *Main path*, *Variants*, *Postconditions* and *Minimal guarantees*.

**Distinctions:**

- **Template:** the file a writer may read. It is rendered from the declared structure, and shows that structure exactly. Nothing reads a declared structure out of a template (DEC-001 point 1).
- **Schema:** the check of a member's front matter, which holds whatever any [rule](../core/glossary.md#term-rule--rule)'s status. A declared structure binds an [artefact](../core/glossary.md#term-artefact--artefact)'s body only where the format rule binds (DEC-001 point 1).

## TERM-design-source — design source

Explained in [VIEW-revalidations](domain-model/020-revalidations.md#design-source).

**Example:** a planned record names `#42's body`, with its link and the time it was read, `2026-01-05T10:00:00Z`. It names the redesign note at `this change`, the [change](../core/glossary.md#term-change--change) the record lands in.

**Distinctions:**

- **A version number:** a version a document's author declares. The [analysis](#term-analysis--analysis)'s [artefacts](../core/glossary.md#term-artefact--artefact) and records carry none, so a design source is pinned by a pointer to its text (DEC-001 point 6).
- **A pull request's head:** never a pointer, since a rebase loses a [head](../core/glossary.md#term-head--head) reviewed mid-way. Nor is any other commit the [default branch](../core/glossary.md#term-default-branch--default-branch) does not hold (DEC-001 point 6).

## TERM-freed-id — freed id

Explained in [VIEW-analyses-and-use-cases](domain-model/010-analyses-and-use-cases.md#freed-id).

**Example:** project-kit's settings free `UC-001` to `UC-010`, `JRN-001` and `JRN-002`, which commit `6107ae77` removed with the pilot [analysis](#term-analysis--analysis). So the core's analysis numbers from `UC-001`.

**Distinctions:**

- **A withdrawn artefact's id:** the id of an [artefact](../core/glossary.md#term-artefact--artefact) withdrawn, never deleted. Its file keeps it, and the [stamp](../core/glossary.md#term-stamp--stamp) never gives it again (DEC-001 point 3).
- **The id of an artefact deleted with no declaration:** taken still, since nothing frees an id but the [project](../core/glossary.md#term-project--project)'s declaration. The stamp numbers past it (DEC-001 point 3).

## TERM-hint — hint

Explained in [VIEW-kinds-and-structures](domain-model/030-kinds-and-structures.md#hint).

**Example:** a new [use case](#term-use-case--use-case)'s *Goal* holds `<!-- pkit:hint … Example: … -->` until its writer states there the need it meets.

**Distinctions:**

- **Placeholder:** the text a writer replaces. A hint is a part's placeholder, and [validation](../core/glossary.md#term-validation--validation) refuses one left in, whatever any [rule](../core/glossary.md#term-rule--rule)'s status (DEC-001 point 1).
- **Rule:** what binds a part. A hint is advice and binds nothing, so a [project](../core/glossary.md#term-project--project) replaces one without a rule (DEC-001 point 1).

## TERM-revalidation — revalidation

Explained in [VIEW-revalidations](domain-model/020-revalidations.md#revalidation).

**Example:** a [change](../core/glossary.md#term-change--change) renames `--out` to `--output`, and the developer reviews the [use case](#term-use-case--use-case) that quotes `--out`. The rename was meant, so the use case is updated to match.

**Distinctions:**

- **The core's answer:** the statement on one [artefact](../core/glossary.md#term-artefact--artefact), `updated` or `unchanged`, that records a revalidation's result there and clears its [friction](../core/glossary.md#term-friction--friction) (COR-050 point 3).
- **Testing:** running the software to see whether it still does what a description says. A revalidation reads, and usually mends the description (DEC-001 point 7).
- **A deferral:** friction put off with a reason, which is no result of a revalidation (DEC-001 point 5).

## TERM-revalidation-outcome — revalidation outcome

Explained in [VIEW-revalidations](domain-model/020-revalidations.md#revalidation-outcome).

**Example:** a commit removes `export_report`, and the person says it was a bug. The [use case](#term-use-case--use-case) that quotes it ends `code-regressed`, its step kept as it was, and a defect is reported.

**Distinctions:**

- **The core's two answers:** `unchanged` and `updated`, which record a revalidation outcome on its [artefact](../core/glossary.md#term-artefact--artefact). `holds` and a regression map to `unchanged`, and a stale [analysis](#term-analysis--analysis) maps to `updated` (DEC-001 point 5).
- **A regression whose step an accepted record decides:** the step takes a box, which changes the use case, so it maps to `updated` (DEC-001 point 5).
- **Ambiguous:** no revalidation outcome yet. Only a person knows whether the [change](../core/glossary.md#term-change--change) was meant, so nothing is recorded until they say (DEC-001 point 5).

## TERM-revalidation-proposal — revalidation proposal

Explained in [VIEW-revalidations](domain-model/020-revalidations.md#revalidation-proposal).

**Example:** `.agent-workspace/analysis-resolver/1234/proposal.md` proposes `holds` for a [use case](#term-use-case--use-case) that quotes nothing the [change](../core/glossary.md#term-change--change) touched. It proposes `analysis-stale`, with a diff, for one that quotes the renamed `--out`, and asks whether removing `export_report` was meant.

**Distinctions:**

- **Revalidation:** the review itself. The proposal drafts a [revalidation](#term-revalidation--revalidation)'s results, and a person records each (DEC-001 point 5).
- **A run a command starts:** project-management's run of the agent with nobody watching. There the agent writes each [answer](../core/glossary.md#term-answer--answer) as fields, never as a command (project-management DEC-056 point 6).

## TERM-revalidation-record — revalidation record

Explained in [VIEW-revalidations](domain-model/020-revalidations.md#revalidation-record).

**Example:** `revalidations/2026-10-02-export-dropped.md` logs a [revalidation](#term-revalidation--revalidation) that drift triggered and `#231` carried. It gives each [artefact](../core/glossary.md#term-artefact--artefact) it covered its [revalidation outcome](#term-revalidation-outcome--revalidation-outcome), and names the gap a regression left.

**Distinctions:**

- **An artefact's own answer:** the only record of a routine revalidation that finds everything still holds (DEC-001 point 6).
- **Decision record:** a choice and why it was made. A revalidation record logs what one revalidation found, and decides nothing.
- **Artefact:** a revalidation record is none. It carries no anchors and lies in no [place](../core/glossary.md#term-place--place), and no [rule](../core/glossary.md#term-rule--rule) binds on it (DEC-001 points 1 and 2).

## TERM-shortfall — shortfall

Explained in [VIEW-revalidations](domain-model/020-revalidations.md#shortfall).

**Example:** step 2 of an export's [use case](#term-use-case--use-case) signs each file, as an accepted architecture record decides. The box below it says the file is written unsigned, and names the issue that tracks the signing, as its entry in `shortfalls` does.

**Distinctions:**

- **A regression no record decides:** a step the [system](../core/glossary.md#term-system--system) no longer carries out, with no accepted record behind it. It keeps its words and takes no box, and its [revalidation](#term-revalidation--revalidation) names the defect (DEC-001 point 5).
- **A step the code alone gives:** a step no accepted record decides. It follows the code, and never takes a box (DEC-001 point 1).
- **The issue:** the work item that tracks building the step. The [change](../core/glossary.md#term-change--change) that builds the step removes the box, in the [pull request](../core/glossary.md#term-pull-request--pull-request) that closes the issue (DEC-001 point 1).

## TERM-tightening — tightening

Explained in [VIEW-kinds-and-structures](domain-model/030-kinds-and-structures.md#tightening).

**Example:** a [project](../core/glossary.md#term-project--project) adds the part *The setup* to its actors, in a group under `tighten` in `project/structures.yaml` that names its [rule](../core/glossary.md#term-rule--rule) `RS-LOC-001`. The part binds where that rule and the format rule both bind.

**Distinctions:**

- **A relabel:** a new label, [hint](#term-hint--hint) or example for a shipped part. It tightens nothing, so it needs no rule (DEC-001 point 1).
- **A change to a shipped part:** dropping, loosening or reordering it. No project makes one, and a part it finds wrong is a [change](../core/glossary.md#term-change--change) it proposes to the [capability](../core/glossary.md#term-capability--capability) (DEC-001 point 1).

## TERM-use-case — use case

Explained in [VIEW-analyses-and-use-cases](domain-model/010-analyses-and-use-cases.md#use-case).

**Example:** the core's UC-014 says how the methodology maintainer develops the methodology in its source repository, with variant 2c for a pin the [system](../core/glossary.md#term-system--system) refuses.

**Distinctions:**

- **Journey:** one actor's path across several use cases, with the seams between them where the path can break (DEC-001 point 1).
- **User story:** a need in one sentence. It is an actor's need and a use case's goal, never an [artefact](../core/glossary.md#term-artefact--artefact) of its own (DEC-001 point 1).
- **Step and variant:** a numbered part of a use case's main path, and a lettered branch from one step. Neither is ever renumbered or removed (DEC-001 point 3).
