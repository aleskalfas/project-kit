---
id: UC-xxx
title: Think a question through in a scratchpad note
status: active
actor: ACT-developer
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/scratchpads.py
      record: [COR-012, COR-043]
      artefact: [ACT-developer]
---

# UC-xxx — Think a question through in a scratchpad note

**Goal:** Think a question too big for a decision through in a scratchpad note, and retire the note once it has produced something.

**Starts when:** the developer meets a question too large to settle in one decision record.

**Main path:**

1. The developer picks a slug of two to four words that names the question.
2. The developer runs `pkit new scratchpad <slug>`.
3. The system writes `.pkit/scratchpad/active/<date>-<slug>.md`, with the authors from git, today's date as `started`, and a heading from the slug.
4. The developer maps the question in the note: its forces, what is known, the alternatives and the open questions.
5. Once the note has produced records or documents, the developer runs `pkit scratchpad done <slug> --produced <ref>`.
6. The system moves the note to `done/`, and adds `retired` and `produced` to its front matter.

**Variants:**

- **2a.** A note in any state already uses the slug. The system refuses and writes nothing, and the path rejoins at step 1.
- **4a.** The developer sends the note as a report with `pkit report`. Once the post succeeds, the system moves the note to `reported/` and records the issue it became (COR-043). The note is then frozen, and later thinking goes in a new note. The path rejoins at step 5.
- **5a.** The line of thought does not pan out. The developer adds why to the note and runs `pkit scratchpad drop <slug>`. The system moves the note to `dropped/` and adds `retired`, and the use case ends.

**Done when:** the note sits in `done/`, naming what it produced.
