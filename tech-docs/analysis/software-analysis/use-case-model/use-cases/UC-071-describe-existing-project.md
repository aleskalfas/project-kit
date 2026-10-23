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
  - REQ-052
after:
  - [UC-070]
shortfalls:
  - at: 2
    issue: "#1930"
    record: software-analysis:DEC-001#9
  - at: 6
    issue: "#1765"
    record: ADR-034#1
  - at: 12
    issue: "#1930"
    record: software-analysis:DEC-001#9
  - at: "3b"
    issue: "#1765"
    record: ADR-034#1
  - at: "3c"
    issue: "#1884"
    record: COR-004
  - at: "5b"
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
        - REQ-052
---

# UC-071 — Describe my existing project from its code, documents and decisions

**Goal:** Describe my existing project from its code, documents and decisions, with an agent deriving candidates that I confirm.

**Other actors:**

- **AI agent** (`core:ACT-ai-agent`): derives the candidates through the `analysis-author` skill, and stamps each only once the developer confirms it (REQ-050).
- **Operator** (`core:ACT-operator`): is asked before `pkit analysis new` or `pkit analysis link` writes in a repository other than the session's own, so no such write happens silently (core:REQ-012).

**Preconditions:** **From UC-070:** Each kind of artefact the candidates hold has its parts chosen.

**Assumptions:**

- The project has software-analysis installed, or registered in place where software-analysis is developed (COR-017 and COR-031). The adapter deploys the `analysis-author` skill (COR-005 and COR-013).
- The core's whole-repository check measures the declared surface that no artefact anchors. It lists apart each artefact whose reason for having no anchors a person accepted (COR-050 points 1, 8 and 14).
- An artefact new in a change counts as revalidated there (COR-050 point 6).

**Trigger:** The developer adopts software-analysis on a project that has code, documents and decisions, and no analysis yet.

**Main path:**

1. The developer asks an AI agent to describe the project, following the `analysis-author` skill's `build-analysis.md`.
2. The agent reads the surface the project declares its analysis ought to cover, in the friction key of its backbone configuration. Where none is declared, it asks the developer to declare one first (DEC-001 point 9).

> [!WARNING]
> **Not built yet:** the skill names no declared surface, so the agent derives candidates whether or not one is declared. DEC-001 point 9 decides that onboarding needs a declared surface, and #1930 tracks it.

3. The agent derives candidates from the code, the existing documents and the project's decisions, in the order of DEC-001 point 12. It starts with the terms, then the domain-model views where the analysis keeps them, then the actors.
4. The agent shows the developer each candidate, with the code, the document or the record it is drawn from. The developer confirms it (REQ-050).
5. The agent stamps each confirmed candidate with `pkit analysis new`, anchored with `--path` and `--record` to what embodies it.
6. At its entry, before it writes, the system checks that the repository it would change is the session's own. Where it is another, the system asks the operator, and with nobody to ask it refuses (core:REQ-012).

> [!WARNING]
> **Not built yet:** `pkit analysis new` runs no such check, and writes in whatever repository holds its working directory. ADR-034 point 1 decides that every `pkit` command that writes runs it, and #1765 tracks it.

7. The system gives a use case, a journey or a requirement the next free number, past every number the default branch's history gave (REQ-052). It writes the candidate whole, and rewrites the analysis's overview (REQ-051).
8. The agent fills each part as its hint says, and runs `pkit analysis validate --preview`. The system holds each artefact to its kind's declared structure where the format rule binds, and reports what a proposed rule would find.
9. The agent goes on with the requirements that bind the whole system, then the use cases, then the journeys (DEC-001 point 12). It shows each candidate to the developer as in step 4, and stamps it as in step 5.
10. Where an accepted decision record decides behaviour the code lacks, the candidate use case describes it as the record decides. The step takes its box and its entry in `shortfalls`, naming the record and the issue that tracks building it (DEC-001 points 1 and 9).
11. The developer runs the whole-repository check, `pkit friction check --all`, and reads its measures. They show the declared surface no artefact anchors, and each artefact with neither anchors nor an accepted reason.
12. The agent ends onboarding once the declared surface is covered, and every artefact is anchored or carries a reason a person accepted (DEC-001 point 9).

> [!WARNING]
> **Not built yet:** the skill ends each step on `pkit analysis validate --preview` and `pkit analysis check-numbers`, and never reads the uncovered surface. DEC-001 point 9 decides that onboarding is complete when the declared surface is covered, and #1930 tracks it.

13. The developer runs `pkit analysis check-numbers`, which passes, and commits the analysis.

**Variants:**

- **3a.** Two words name one concept, or one word names two. The agent proposes one term for each concept, and gives two concepts of one word qualified names (DEC-001 point 1).
- **3b.** The analysis keeps a domain model. After each term and each view, the agent runs `pkit analysis link`. The system writes the links between terms and views, in each file where one changes (DEC-004 point 7). At its entry, the command checks the repository as step 6 does (core:REQ-012).

> [!WARNING]
> **Not built yet:** `pkit analysis link` runs no such check, and writes in whatever repository holds its working directory. ADR-034 point 1 decides that every `pkit` command that writes runs it, and #1765 tracks it.

- **3c.** On the path of 3b, the developer asks to see the links before they are written. The agent runs `pkit analysis link --dry-run`, and the system names each link it would write and writes nothing (core:REQ-009).

> [!WARNING]
> **Not built yet:** `pkit analysis link` takes no `--dry-run`, and refuses the flag. COR-004 decides that a command whose widest effect reaches past what the person named offers one, and #1884 tracks it.

- **4a.** The developer rejects a candidate, or corrects it. The agent drafts it again or drops it, and stamps nothing for it until the developer confirms it.
- **5a.** A candidate actor, term or requirement has nothing to anchor, such as a word of the business that the code never names. The agent shows the developer its reason for having no anchors, word for word. It stamps the candidate with `--unanchored-because` only once the developer accepts the reason (COR-050 point 1).
- **5b.** The developer asks to see what the stamp would write first. The agent runs it with `--dry-run`, and the system names the file it would write and the overview it would rewrite, and writes nothing (core:REQ-009).

> [!WARNING]
> **Not built yet:** `pkit analysis new` takes no `--dry-run`, and refuses the flag. COR-004 decides that a command whose widest effect reaches past what the person named offers one, and #1884 tracks it.

- **7a.** The stamp refuses, such as for an id already held, an actor or a requirement not in force, or a title still holding a placeholder. It writes nothing, and says why (REQ-051). The agent mends the request, and the path rejoins at step 5.
- **7b.** The overview cannot be drawn in full. The stamp warns, naming `pkit analysis overview`, and writes the candidate all the same.
- **12a.** Declared surface stays uncovered, or an artefact has neither anchors nor an accepted reason. The path rejoins at step 3, for what the measures name.

**Postconditions:** The analysis describes the project from its concepts up, each artefact confirmed by the developer. The declared surface is covered, and every artefact is anchored or carries a reason a person accepted (DEC-001 point 9).

**Minimal guarantees:**

- The skill has the agent stamp no candidate before the developer confirms it (REQ-050).
- A refused stamp leaves every file as it was (REQ-051).
- An id the stamp gives was never given before, save a freed id (REQ-052).
- An artefact left unanchored stays counted until it carries anchors or an accepted reason, and is never hidden (COR-050 point 8).
