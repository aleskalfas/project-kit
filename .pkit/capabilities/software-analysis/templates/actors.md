---
# The actors (software-analysis DEC-001 points 1, 3 and 4): one collection
# file, `use-case-model/actors.md` under the analysis location, one entry per
# actor keyed by its stable id, each with a body section headed by that id.
# Stamp entries, never copy them: `pkit analysis new actor <slug>` adds
# `ACT-<slug>` and its section, creating the file from this template the first
# time. An actor anchors to where the software or a decision embodies it; one
# nothing embodies carries `unanchored-because:` instead. Each entry's own
# fields' shape is `schemas/actor.schema.json`.
ACT-actor:
  name: <Display name>            # may change; the id does not
  status: active                  # or withdrawn: the entry stays and its id is never reused
  needs:
    - <what this actor needs from the system, in one sentence>
  pkit:
    friction:
      anchors:
        path: ["<code that embodies it>"]        # --path
        record: ["<decision that names it>"]     # --record
---

# Actors

Who uses the system, and what each needs from it. Each actor's id is stable; its name may change.

## ACT-actor — <Display name>

<Who this is, when they come to the system, and what they bring with them.>
