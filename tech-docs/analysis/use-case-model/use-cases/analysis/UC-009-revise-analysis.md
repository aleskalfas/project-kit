---
id: UC-009
title: Revise the analysis ahead of a change
status: active
actor: ACT-developer
other-actors:
  - ACT-ai-agent
  - ACT-planner
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/software-analysis/skills/analysis-author/analysis-author.md
        - .pkit/capabilities/software-analysis/skills/analysis-author/revalidation-record.md
        - .pkit/capabilities/software-analysis/scripts/new.py
        - .pkit/capabilities/software-analysis/scripts/validate.py
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
        - COR-050#3
        - COR-050#8
      artefact:
        - ACT-developer
        - ACT-ai-agent
        - ACT-planner
---

# UC-009 — Revise the analysis ahead of a change

**Goal:** Revise the analysis before a proposed change is built, naming the design I reviewed and pinning the text I read.

**Other actors:**

- **AI agent** (`ACT-ai-agent`): an agent with the `analysis-author` skill drafts the revision and stamps each artefact. It writes no goal, guarantee or requirement it cannot source (the `analysis-author` skill).
- **Planner** (`ACT-planner`): decides what the system must do, where neither an accepted record nor existing code sources a goal or a guarantee. An agent writes no such item before the planner decides, and quotes the planner's words (the `analysis-author` skill).

**Preconditions:** The project has installed software-analysis.

**Assumptions:**

- Nothing tells a reader that a revised use case describes behaviour not built yet. Only the planned record names the gap, and the issue that builds the missing behaviour (software-analysis DEC-001 point 6). software-analysis DEC-001 point 11 leaves a lifecycle for planned reviews of the analysis to a later decision.
- The revision anchors the records it rests on, and no record anchors the analysis back (software-analysis DEC-001 point 11). No check finds such an anchor in general.
- A revised use case can anchor no code that is not written yet. No check asks the building change to add that anchor. Code no artefact anchors shows only as uncovered surface, where the project declares one (COR-050 point 8).

**Trigger:** A change is proposed, such as an issue a plan filed (UC-008) or a design note.

**Main path:**

1. The developer reads the proposed design, and the use cases the issue names in its `## Use cases` section.
2. The developer, or an agent with the `analysis-author` skill, revises each artefact the design changes, and stamps each new one with `pkit analysis new`. Each goal and minimal guarantee names its source (the `analysis-author` skill).
3. The developer runs `pkit analysis validate --preview`, then `pkit friction check`, and answers what the revision made stale, such as a journey through a revised use case (UC-002).
4. The developer records each covered artefact's answer on the artefact, such as `pkit friction revalidate <id> --outcome updated` for one whose content changed (the `analysis-author` skill). Where none of the artefact's anchors changed, the change check lists that answer `not asked for by this change`. So an agent writes such an answer only once the person the agent works for has accepted it (core rule 20).
5. The developer stamps the planned record: `pkit analysis new revalidation <slug> --change "#<issue>" --trigger planned`, with these for each artefact and each source:
   - `--outcome <id>=<outcome>` and `--because <id>=<why>`, for each artefact the revision covers
   - `--reviewed-against "<title> @ <version>"`, for each source of the design, with ` @ <link>` after it for a source outside the repository
   - `--gap "<ids>: <gap> => <resolution>"`, for each behaviour the code lacks, naming the issue that will build that behaviour
6. The system writes `revalidations/<date>-<slug>.md`, naming these (software-analysis DEC-001 point 6):
   - the change and the trigger
   - each source of the design, at its version
   - each artefact's outcome, and each gap
7. The developer runs `pkit analysis check-numbers` and `pkit analysis check-pointers`, and both pass.
8. The revision lands on the default branch (UC-012), ahead of the code that builds it. The planning of later work reads the revised use cases from there (UC-008, and software-analysis DEC-001 point 8).

**Variants:**

- **1a.** The change alters nothing users do, such as a refactor. The analysis needs no revision, and the use case ends (project-management DEC-054 point 5).
- **2a.** The design gives no source for a goal or a guarantee. The developer writes no such item, and asks the planner. The planner's words are quoted in the artefact, with the planner's name and the date (the `analysis-author` skill). The path rejoins at step 2.
- **2b.** A step of a revised use case no longer happens. It stays under its number, and a new step takes a number past every other (software-analysis DEC-001 point 3).
- **2c.** No actor pursues a use case any more. The use case is withdrawn, its file kept and its id never used again (software-analysis DEC-001 point 3).
- **2d.** No use case describes the part the change alters yet, as when none has settled (UC-008 variant 3a). The developer stamps each use case new, and the path goes on at step 3.
- **4a.** An anchor of the artefact changed in this change too, such as one the revision added. The change check asks for the answer, so an agent writes it without asking (COR-050 point 3).
- **5a.** The developer gives no `--reviewed-against`. The stamp refuses with ``a planned record names each source of the design it reviewed, in `reviewed-against`: …``, and writes nothing. The path rejoins at step 5.
- **5b.** A source names a commit the default branch does not hold, such as the head of the design's branch. The stamp writes the record, and warns that `pkit analysis check-pointers` fails the change until the source names a commit the default branch holds, or `this change`.
- **5c.** A source lies outside the repository, such as an issue's body. Its version is the time its text was read, in UTC, and its link follows it.
- **5d.** An outcome has no `--because`, or a gap found names no `--gap`. The stamp refuses and writes nothing, and the path rejoins at step 5.
- **7a.** `pkit analysis check-pointers` fails on a source whose commit the default branch does not hold. The developer corrects the source in the record. It names the commit where the design landed, or `this change` where the design lands with the record. The path rejoins at step 7.
- **7b.** `pkit analysis check-numbers` finds that the default branch gave a new use case's number to another use case since the branch left the default branch. The developer renumbers the new use case with the stamp before the merge, and the path rejoins at step 7 (software-analysis DEC-001 point 3).

**Postconditions:** The analysis describes the change as proposed. A planned record names the design the revision was reviewed against, pinned at its version. The record names each gap too, with the issue that builds the missing behaviour.

**Minimal guarantees:**

- A refused stamp writes nothing, since each file it writes is written whole or not at all (`_lib/stamp.py`).
- The stamp refuses a planned record that names no source of its design. `pkit analysis validate` fails one written by hand without `reviewed-against` (software-analysis DEC-001 point 6, `_lib/revalidation.py` and `validate.py`).
- Where `pkit analysis check-pointers` runs, a change that adds a record naming a commit the default branch does not hold fails. A commit it cannot place is reported as unknown, and never fails (software-analysis DEC-001 point 6, and `check-pointers.py`).
- `pkit analysis check-numbers` fails on a step or a variant whose text now stands under another number or letter, or whose number or letter is gone. It does so where RS-SAN-002 binds (software-analysis DEC-001 point 3, and `check-numbers.py`).
