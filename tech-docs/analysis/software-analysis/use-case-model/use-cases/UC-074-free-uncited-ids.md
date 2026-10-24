---
id: UC-074
title: Free the ids of artefacts nothing cites
status: active
actor: core:ACT-developer
other-actors:
  - core:ACT-ai-agent
requirements:
  - REQ-050
  - REQ-051
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/software-analysis/scripts/_lib/numbering.py
        - .pkit/capabilities/software-analysis/scripts/check-numbers.py
        - .pkit/capabilities/software-analysis/schemas/config.schema.json
        - .pkit/capabilities/software-analysis/skills/analysis-author/analysis-author.md
      record:
        - software-analysis:DEC-001#3
        - COR-017
        - COR-031
        - COR-054#3
        - COR-054#5
      artefact:
        - REQ-050
        - REQ-051
---

# UC-074 — Free the ids of artefacts nothing cites

**Goal:** Free the ids of artefacts nothing cites, such as an abandoned pilot, so new artefacts may take those ids again.

**Other actors:**

- **AI agent** (`core:ACT-ai-agent`): may look for what cites the ids, and propose the entry that frees them. It never writes one to make a check pass, so the declaration stays the developer's (REQ-050).

**Preconditions:** None.

**Assumptions:**

- The project has software-analysis installed, or registered in place where software-analysis is developed (COR-017 and COR-031).
- What may cite an id is open-ended, such as other repositories, trackers and code, so no tool can check it all. A person judges that nothing cites the ids (DEC-001 point 3).
- The backbone resolves the default branch, whose history the stamp and `pkit analysis check-numbers` read, and the base that `check-numbers` compares with (COR-054 points 3 and 5).

**Trigger:** Artefacts that nothing cites, such as an abandoned pilot, hold ids that the developer wants the analysis to give again.

**Main path:**

1. The developer looks for what cites each id, such as:
   - a friction anchor, in this repository or another
   - a revalidation record, or an evidence entry
   - code, a test, or a page anchored to the artefact
   - a work item's list of the use cases it serves, or an open issue or pull request that names the id
2. The developer finds nothing that cites them.
3. The developer deletes the artefacts' files in one commit, and lands it on the default branch.
4. The developer adds an entry under `numbering.freed-by` in `.pkit/capabilities/software-analysis/project/config.yaml`. The entry names that commit by its full id, and lists the ids (DEC-001 point 3).
5. The developer runs `pkit analysis check-numbers`.
6. The system checks that the entry can be honoured. The commit lies on the default branch's history, and the default branch lost each listed file by it last. Every file an id was ever given is freed. The system lists the ids each entry frees, one line for each entry, and writes nothing (core:REQ-005).
7. The developer opens the pull request that adds the entry. The pull request says where the developer looked and what they found, so a reviewer can judge the declaration.
8. Once the entry lands, the stamp gives each freed id again, as though it was never given. Where a freed id is the number the stamp would have followed, the stamp says so, naming the commit (REQ-051).

**Variants:**

- **1a.** An AI agent looks for what cites the ids. It proposes the entry with the ids, where it looked and what it found, and never writes one to make a check pass (REQ-050).
- **2a.** Something cites an id. The developer deletes nothing and writes no entry, and withdraws the artefacts instead, so the analysis numbers past them. Artefacts already removed are restored as withdrawn. The use case ends.
- **3a.** The artefacts were removed from the default branch long ago, as the pilot of project-kit's first analysis was. The developer names the commit that removed them, and the path goes on at step 4.
- **3b.** The commit moved a file rather than deleting it, such as into another folder, or git pairs the file with a similar new one. The file keeps its id, so the developer deletes it instead.
- **6a.** The entry cannot be honoured, such as for a commit off the default branch's history, or an id the commit does not free. `pkit analysis check-numbers` fails on every run, and the stamp refuses to number a use case, a journey or a requirement. Each names the entry and says why. The developer mends the entry, and the path rejoins at step 5.
- **6b.** The clone is too shallow to hold the commit's parent, or git is older than 2.31. Both tools say that the fault is the clone's or git's, not the entry's.
- **6c.** The commit frees an id that no entry lists. The id stays taken, and both tools report it, never failing on it.
- **8a.** A file in the working tree or on the default branch still holds a freed id. The id stays taken while the file holds it.

**Postconditions:** Each id the entry lists is free again: the stamp may give it, and `pkit analysis check-numbers` reports no collision for it.

**Minimal guarantees:**

- Only an id the project lists is freed, and no tool infers one (DEC-001 point 3 and REQ-051).
- An entry that cannot be honoured stops the stamp from numbering, so no id is given again on a wrong declaration (`numbering.py`).
- `pkit analysis check-numbers` is a query, which changes no file of the project (core:REQ-005 and `check-numbers.py`).
