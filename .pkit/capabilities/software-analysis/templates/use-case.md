---
# A use case (software-analysis DEC-001 points 1, 3 and 4): one actor's goal
# and how the system fulfils it. Stamp it, never copy it: `pkit analysis new
# use-case <slug> --actor <ACT-id>` numbers it, fills its actor and the actor
# anchor, and writes it to `use-case-model/use-cases/` under the analysis
# location (`--area <area>` for a folder per functional area). Its own fields'
# shape is `schemas/use-case.schema.json`; the friction block is the core's.
id: UC-000                        # stamped: the next free number, never reused
status: active                    # or withdrawn: the file stays and its id is never reused
actor: ACT-actor                  # the actor whose goal this is
pkit:
  friction:
    anchors:
      path: ["<code it exercises>"]           # --path: a change there asks whether the use case still holds
      record: ["<decision it relies on>"]     # --record: a change to one asks the same
      artefact: [ACT-actor]                   # its actor: a changed actor flags this use case
---

# UC-000 — <Title>

**Goal:** <what the actor wants to achieve, in one sentence>

**Starts when:** <what triggers it>

**Main path:**

1. <what the actor or the system does>
2. <…>

**Variants:** each lettered after the step it branches from; steps and variants are only ever added, never renumbered.

- **1a.** <the condition at step 1, what happens instead, and where the path rejoins or ends>

**Done when:** <the state that shows the goal is met>
