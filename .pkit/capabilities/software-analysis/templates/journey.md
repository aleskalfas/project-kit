---
# A journey (software-analysis DEC-001 points 1, 3 and 4): an end-to-end path
# one actor takes across several use cases, and the seams between them where
# the path can break. Stamp it, never copy it: `pkit analysis new journey
# <slug> --actor <ACT-id> --step <UC-id> --step <UC-id> …` numbers it, writes
# its title, `steps` and, from them, its use-case anchors, and writes it to
# `use-case-model/journeys/` under the analysis location. `steps` is the
# source: `pkit analysis validate` requires the use-case anchors to match it,
# and the heading to be the id and title the front matter gives. Its own
# fields' shape is `schemas/journey.schema.json`.
id: JRN-000                       # stamped: the next free number, never reused
title: <Title>                    # --title; the heading below repeats it after the id
status: active                    # or withdrawn: the file stays and its id is never reused
actor: ACT-actor                  # the actor who takes the journey
steps: [UC-000, UC-001]           # the use cases it passes through, in order
pkit:
  friction:
    anchors:
      path: ["<code at a seam between two steps>"]   # --path
      artefact: [UC-000, UC-001]                     # written from steps; never edit one without the other
---

# JRN-000 — <Title>

**Starts:** <where the actor begins, and what they want by the end>

**Steps:**

1. UC-000 — <what the actor achieves in this use case>
2. UC-001 — <what the actor achieves in this use case>

**Seams to watch:** where the path passes from one use case to the next — what must carry over, and how it could break.

- **UC-000 → UC-001:** <what carries over, and how it could break>

**Done when:** <the state that shows the whole path succeeded>
