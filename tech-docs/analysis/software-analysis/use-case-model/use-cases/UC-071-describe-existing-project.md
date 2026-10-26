---
id: UC-071
title: Describe my existing project from its code, documents and decisions
status: active
actor: core:ACT-developer
other-actors:
  - core:ACT-ai-agent
  - core:ACT-operator
requirements:
  - REQ-050
  - REQ-051
  - REQ-053
after:
  - [UC-070]
shortfalls:
  - at: 5
    issue: "#1765"
    record: ADR-034#1
  - at: "3b"
    issue: "#1765"
    record: ADR-034#1
  - at: "3c"
    issue: "#1884"
    record: COR-004
  - at: "4b"
    issue: "#1884"
    record: COR-004
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/software-analysis/skills/analysis-author/build-analysis.md
        - .pkit/capabilities/software-analysis/skills/analysis-author/analysis-author.md
        - .pkit/capabilities/software-analysis/scripts/new.py
        - .pkit/capabilities/software-analysis/scripts/_lib/stamp.py
        - .pkit/capabilities/software-analysis/scripts/link.py
        - .pkit/capabilities/software-analysis/scripts/validate.py
      record:
        - software-analysis:DEC-001#1
        - software-analysis:DEC-001#9
        - software-analysis:DEC-001#12
        - software-analysis:DEC-004#7
        - ADR-034#1
        - COR-004
        - COR-005
        - COR-013
        - COR-017
        - COR-031
        - COR-050#1
        - COR-050#6
        - COR-050#8
        - COR-050#14
      artefact:
        - REQ-050
        - REQ-051
        - REQ-053
---

# UC-071 — Describe my existing project from its code, documents and decisions

**Goal:** Describe my existing project from its code, documents and decisions, with an agent deriving candidates that I confirm.

**Other actors:**

- **AI agent** (`core:ACT-ai-agent`): derives the [candidates](../../glossary.md#term-candidate--candidate) through the `analysis-author` [skill](../../../core/glossary.md#term-skill--skill). The developer confirms each before it is committed (REQ-050).
- **Operator** (`core:ACT-operator`): is asked before `pkit analysis new` or `pkit analysis link` writes in a repository other than the session's own, so no such write happens silently (core:REQ-012).

**Preconditions:** **From UC-070:** Each kind of [artefact](../../../core/glossary.md#term-artefact--artefact) the [candidates](../../glossary.md#term-candidate--candidate) hold has its parts chosen.

**Assumptions:**

- The [project](../../../core/glossary.md#term-project--project) has software-analysis installed, or registered in place where software-analysis is developed (COR-017 and COR-031). The [adapter](../../../core/glossary.md#term-adapter--adapter) deploys the `analysis-author` [skill](../../../core/glossary.md#term-skill--skill) (COR-005 and COR-013).
- The core's [whole-repository check](../../../core/glossary.md#term-whole-repository-check--whole-repository-check) measures the declared surface that no [artefact](../../../core/glossary.md#term-artefact--artefact) anchors. It lists apart each artefact whose reason for having no anchors a person accepted (COR-050 points 1, 8 and 14).
- An artefact new in a [change](../../../core/glossary.md#term-change--change) counts as revalidated there (COR-050 point 6).

**Trigger:** The developer starts describing a [project](../../../core/glossary.md#term-project--project) that has code, documents and decisions, which its [analysis](../../glossary.md#term-analysis--analysis) does not describe yet.

**Main path:**

1. The developer asks an AI agent to describe the [project](../../../core/glossary.md#term-project--project), following the `analysis-author` [skill](../../../core/glossary.md#term-skill--skill)'s `build-analysis.md`.
2. The agent runs the [whole-repository check](../../../core/glossary.md#term-whole-repository-check--whole-repository-check), and reads the surface the project declares its [analysis](../../glossary.md#term-analysis--analysis) ought to cover. The project declares the surface in the [friction](../../../core/glossary.md#term-friction--friction) key of its [backbone configuration](../../../core/glossary.md#term-backbone-configuration--backbone-configuration). Where none is declared, the agent asks the developer for one, and derives no [candidate](../../glossary.md#term-candidate--candidate) until the project declares one (DEC-001 point 9).
3. The agent derives candidates from the code, the existing documents and the project's decisions, in the order of DEC-001 point 12. It starts with the terms, then the domain-model views where the analysis keeps them, then the actors.
4. The agent stamps each candidate with `pkit analysis new`, anchored with `--path` and `--record` to what it is drawn from.
5. At its entry, before it writes, the [system](../../../core/glossary.md#term-system--system) checks that the repository it would write in is the session's own. Where it is another, the system asks the operator, and with nobody to ask it refuses (core:REQ-012).

> [!WARNING]
> **Not built yet:** `pkit analysis new` runs no such check, and writes in whatever repository holds its working directory. ADR-034 point 1 decides that every `pkit` command that writes runs it, and #1765 tracks it.

6. The system gives a [use case](../../glossary.md#term-use-case--use-case), a journey or a requirement the next free number, past every number the [default branch](../../../core/glossary.md#term-default-branch--default-branch)'s history gave (REQ-051). It writes the candidate whole, and rewrites the analysis's overview.
7. The agent fills each part as its [hint](../../glossary.md#term-hint--hint) says, and runs `pkit analysis validate --preview`. The system holds each candidate to its kind's [declared structure](../../glossary.md#term-declared-structure--declared-structure) where the format [rule](../../../core/glossary.md#term-rule--rule) binds, and reports what a proposed rule would find (REQ-053).
8. The agent shows the developer each candidate, with the code, the document or the record it is drawn from. The developer confirms it, and only a confirmed candidate is committed (DEC-001 point 9 and REQ-050).
9. The agent goes on with the requirements that bind the whole system, then the use cases, then the journeys (DEC-001 point 12). It stamps each as in step 4, and shows it to the developer as in step 8.
10. Where an accepted [decision record](../../../core/glossary.md#term-decision-record--decision-record) decides behaviour the code lacks, the candidate use case describes it as the decision record decides. The step takes its box and its entry in `shortfalls`, naming that record and the issue that tracks building it (DEC-001 points 1 and 9).
11. The agent runs the whole-repository check again, and ends onboarding only once the check measures the declared surface covered (DEC-001 point 9). Every [artefact](../../../core/glossary.md#term-artefact--artefact) of the analysis is then anchored, or carries a reason a person accepted.
12. The developer runs `pkit analysis check-numbers`, which passes, and commits the confirmed candidates.

**Variants:**

- **3a.** Two words name one concept, or one word names two. The agent proposes one term for each concept, and gives two concepts of one word qualified names (DEC-001 point 1).
- **3b.** The [analysis](../../glossary.md#term-analysis--analysis) keeps a domain model. The agent runs `pkit analysis link` after each [artefact](../../../core/glossary.md#term-artefact--artefact) it stamps. The [system](../../../core/glossary.md#term-system--system) writes the links to the terms, and those to and from each view, in each file where a link changes (DEC-004 point 7). At its entry, the command checks the repository as step 5 does (core:REQ-012).

> [!WARNING]
> **Not built yet:** `pkit analysis link` runs no such check, and writes in whatever repository holds its working directory. ADR-034 point 1 decides that every `pkit` command that writes runs it, and #1765 tracks it.

- **3c.** On the path of 3b, the developer asks to see the links before they are written. The agent runs `pkit analysis link --dry-run`, and the system names each link it would write and writes nothing (core:REQ-009).

> [!WARNING]
> **Not built yet:** `pkit analysis link` takes no `--dry-run`, and refuses the flag. COR-004 decides that a command whose widest effect reaches past what the person named offers one, and #1884 tracks it.

- **4a.** A [candidate](../../glossary.md#term-candidate--candidate) actor, term or requirement has nothing to [anchor](../../../core/glossary.md#term-anchor--anchor), such as a word of the business that the code never names. The agent shows the developer its reason for having no anchors, word for word. It stamps the candidate with `--unanchored-because` only once the developer accepts the reason (COR-050 point 1).
- **4b.** The developer asks to see what the [stamp](../../../core/glossary.md#term-stamp--stamp) would write first. The agent runs it with `--dry-run`, and the system names the file it would write and the overview it would rewrite, and writes nothing (core:REQ-009).

> [!WARNING]
> **Not built yet:** `pkit analysis new` takes no `--dry-run`, and refuses the flag. COR-004 decides that a command whose widest effect reaches past what the person named offers one, and #1884 tracks it.

- **6a.** The stamp refuses, such as for an id already held, an actor or a requirement not in force, or a title still holding a placeholder. It writes nothing, and says why (`stamp.py`). The agent mends the request, and the path rejoins at step 4.
- **6b.** The overview cannot be drawn in full. The stamp warns, naming `pkit analysis overview`, and writes the candidate all the same.
- **8a.** The developer rejects a candidate, or corrects it. The agent revises the candidate, or deletes it before it is committed, so a deleted one takes no id.
- **11a.** Declared surface stays uncovered, or an artefact has neither anchors nor an accepted reason. The path rejoins at step 3, for what the measures name.

**Postconditions:** The [analysis](../../glossary.md#term-analysis--analysis) describes the [project](../../../core/glossary.md#term-project--project) from its concepts up, each [artefact](../../../core/glossary.md#term-artefact--artefact) confirmed by the developer. The declared surface is covered, and every artefact is anchored or carries a reason a person accepted (DEC-001 point 9).

**Minimal guarantees:**

- The [skill](../../../core/glossary.md#term-skill--skill) has a person confirm each [candidate](../../glossary.md#term-candidate--candidate) before it is committed (REQ-050).
- A refused [stamp](../../../core/glossary.md#term-stamp--stamp) leaves every file as it was (`stamp.py`).
- An id settled on the [default branch](../../../core/glossary.md#term-default-branch--default-branch) is never given to another [artefact](../../../core/glossary.md#term-artefact--artefact), save a [freed id](../../glossary.md#term-freed-id--freed-id) (REQ-051).
- An artefact left unanchored stays counted until it carries anchors or an accepted reason, and is never hidden (COR-050 point 8).
