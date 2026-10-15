---
# A journey (software-analysis DEC-001 points 1, 3 and 4): an end-to-end path
# one actor takes across several use cases, and the seams between them where
# the path can break. Stamp it, never copy it: `pkit analysis new journey
# <slug> --actor <ACT-id> --step <UC-id> --step <UC-id> …` numbers it, writes
# its title, `steps` and, from them, its use-case anchors and its step lines,
# and writes it to `use-case-model/journeys/` under the analysis location.
# `steps` is the source: `pkit analysis validate` requires the use-case anchors
# to match it, and the heading to be the id and title the front matter gives.
# Its body is rendered from the journey's declared structure
# (`schemas/artefact-kinds.yaml`). Each part holds its hint until you write in
# its place what it asks for. Its own fields' shape is
# `schemas/journey.schema.json`.
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

**Goal:** <!-- pkit:hint What the actor wants from the whole path, in one sentence in their own voice. Start with the verb, or with *Never* and the verb, with *I* and *my* where they refer to themselves. Example: Build my first report and export it as a file. -->

**Steps:** <!-- pkit:hint One line for each use case in `steps`, in order: its id and its title as the use case states it. Under a step, add one line for each hand-over it needs from an earlier step or from a use case outside the journey. Say what it receives and how that can break. Example: `3. UC-007 — Export the report as a file`, with one hand-over under it. `**Needs from step 2 (UC-005):** the report the analyst saved. A report left unsaved is not offered for export.` -->

**Variants:** <!-- pkit:hint One for each branch of the whole path, lettered after the step it leaves. Say where the path rejoins or ends. Write `None.` when there is none. Example: 3a. The analyst wants a second report, and the path rejoins at step 2. -->

**Postconditions:** <!-- pkit:hint The state that shows the whole path succeeded. Example: The analyst holds a file with their first report. -->

**Minimal guarantees:** <!-- pkit:hint What still holds when the path stops before its end. Name the record or code each rests on. Write `None.` when there is none. Example: Stopping after any step leaves every saved report as it was (DEC-003). -->
