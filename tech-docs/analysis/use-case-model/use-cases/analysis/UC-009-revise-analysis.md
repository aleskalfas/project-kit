---
id: UC-009
title: Revise the analysis ahead of a change
status: active
actor: ACT-developer
other-actors:
  - ACT-ai-agent
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/software-analysis/skills/analysis-author/analysis-author.md
        - .pkit/capabilities/software-analysis/skills/analysis-author/revalidation-record.md
        - .pkit/capabilities/software-analysis/scripts/new.py
        - .pkit/capabilities/software-analysis/scripts/_lib/stamp.py
        - .pkit/capabilities/software-analysis/scripts/_lib/revalidation.py
        - .pkit/capabilities/software-analysis/scripts/check-pointers.py
        - .pkit/capabilities/software-analysis/scripts/check-numbers.py
        - .pkit/capabilities/software-analysis/scripts/fill-use-cases.py
        - src/project_kit/friction_check.py
        - .pkit/rules/core.md
      record:
        - software-analysis:DEC-001#3
        - software-analysis:DEC-001#5
        - software-analysis:DEC-001#6
        - software-analysis:DEC-001#8
        - software-analysis:DEC-001#11
        - project-management:DEC-054#5
        - project-management:DEC-055#3
        - COR-050#3
        - COR-050#8
      artefact:
        - ACT-developer
        - ACT-ai-agent
---

# UC-009 — Revise the analysis ahead of a change

**Goal:** Revise the analysis before a proposed change is built, naming the design I reviewed and pinning the text I read.

**Other actors:**

- **AI agent** (`ACT-ai-agent`): an agent with the `analysis-author` skill drafts the revision and stamps each artefact. It writes no goal, guarantee or requirement it cannot source, and asks the person who decides instead (the `analysis-author` skill).

**Preconditions:** The project has installed software-analysis, and its analysis describes the part of the system the change alters.

**Assumptions:**

- What the system must do is the person's decision. An agent quotes that person's answer where neither a record nor existing code is the source (the `analysis-author` skill). In project-kit, the rule that asks for a source, RS-SAN-007, is proposed and binds nothing.
- Nothing tells a reader that a revised use case describes behaviour not built yet. Only the planned record names the gap and the task that builds it (software-analysis DEC-001 point 6). A lifecycle for a planned revalidation is left to a later decision (software-analysis DEC-001 point 11).
- The revision anchors the records it rests on, and no record anchors the analysis back (software-analysis DEC-001 point 11). No check finds such an anchor in general.
- Where an anchor's code is not written yet, nothing makes the building change add it. Code no artefact anchors shows only as uncovered surface, where the project declares one (COR-050 point 8).

**Trigger:** A change is proposed that alters what users do, such as an issue a plan filed (UC-008) or a design note.

**Main path:**

1. The developer reads the proposed design, and the use cases the issue names in its `## Use cases` section.
2. The developer, or an agent with the `analysis-author` skill, revises each artefact the design changes, and stamps each new one with `pkit analysis new`. Each goal and minimal guarantee names its source.
3. The developer runs `pkit analysis validate --preview`, then `pkit friction check`, and answers what the revision made stale, such as a journey through a revised use case (UC-002).
4. The developer records each covered artefact's answer on it, such as `pkit friction revalidate <id> --outcome updated` for one whose content changed (the `analysis-author` skill).
5. The developer stamps the planned record: `pkit analysis new revalidation <slug> --change "#<issue>" --trigger planned`, with these for each artefact and each source:
   - `--outcome <id>=<outcome>` and `--because <id>=<why>`, for each artefact the revision covers
   - `--reviewed-against "<title> @ <version>"`, for each source of the design, with ` @ <link>` after it for a source outside the repository
   - `--gap "<ids>: <gap> => <resolution>"`, for each behaviour the code lacks, naming the task that builds it
6. The system writes `revalidations/<date>-<slug>.md`. It names the change, the trigger, each source of the design at its version, each outcome and each gap (software-analysis DEC-001 point 6).
7. The developer runs `pkit analysis check-numbers` and `pkit analysis check-pointers`, and both pass.
8. The revision lands on the default branch (UC-012). The planning of later work reads its use cases from there (UC-008, and software-analysis DEC-001 point 8).

**Variants:**

- **1a.** The change alters nothing users do, such as a refactor. The analysis needs no revision, and the use case ends (project-management DEC-054 point 5).
- **2a.** The design gives no source for a goal or a guarantee. The developer writes no such item, and asks the person who decides. That person's answer is quoted in the artefact, with their name and the date (the `analysis-author` skill). The path rejoins at step 2.
- **2b.** A step of a revised use case no longer happens. It stays under its number, and a new step takes a number past every other (software-analysis DEC-001 point 3).
- **2c.** No actor pursues a use case any more. The use case is withdrawn, its file kept and its id never used again (software-analysis DEC-001 point 3).
- **4a.** No anchor of the artefact changed in this change. The change check lists the answer `not asked for by this change`. An agent writes such an answer only once the person accepted it (core rule 20). An authorisation for an earlier head never covers it (project-management DEC-055 point 3).
- **5a.** The developer gives no `--reviewed-against`. The stamp refuses, saying a planned record names each source of the design it reviewed, and writes nothing. The path rejoins at step 5.
- **5b.** A source names a commit the default branch does not hold, such as the head of the design's branch. The stamp writes the record, and warns that `pkit analysis check-pointers` fails the change until the source names a commit the default branch holds, or `this change`.
- **5c.** A source lies outside the repository, such as an issue's body. Its version is the time its text was read, in UTC, and its link follows it.
- **5d.** An outcome has no `--because`, or a gap found names no `--gap`. The stamp refuses and writes nothing, and the path rejoins at step 5.
- **7a.** `pkit analysis check-pointers` fails on a source whose commit the default branch does not hold. The developer corrects the source to name the commit where the design landed, or `this change` where the design lands with the record. The path rejoins at step 7.
- **7b.** `pkit analysis check-numbers` finds that the default branch gave the number of a new use case to another one since the branch left it. The developer renumbers it with the stamp before the merge, and the path rejoins at step 7 (software-analysis DEC-001 point 3).

**Postconditions:** The analysis describes the change as proposed. A planned record names the design it was reviewed against, pinned at its version, and each gap with the task that fills it.

**Minimal guarantees:**

- A refused stamp writes nothing, since each file it writes is written whole or not at all (`_lib/stamp.py`).
- A planned record that names no source of its design is never written (software-analysis DEC-001 point 6, and `_lib/revalidation.py`).
- Where `pkit analysis check-pointers` runs, a change that adds a record naming a commit the default branch does not hold fails. A commit it cannot place is reported as unknown, and never fails (software-analysis DEC-001 point 6, and `check-pointers.py`).
- No step or variant of a use case is renumbered or removed where `pkit analysis check-numbers` runs (software-analysis DEC-001 point 3, and `check-numbers.py`).
