---
# An actor (software-analysis DEC-001 points 1, 3 and 4): a named role that
# uses the system, one file each in `use-case-model/actors/` under the analysis
# location. Its needs sit in this front matter, beside the description below.
# Stamp it, never copy it: `pkit analysis new actor <slug>` writes
# `ACT-<slug>.md` with its id, its name and its anchors. Its heading is its id
# and name, as the front matter gives them. An actor anchors to where the
# software or a decision embodies it. One that nothing embodies carries
# `unanchored-because:` in its friction block instead of anchors
# (--unanchored-because). Its own fields' shape is `schemas/actor.schema.json`,
# and the friction block is the core's.
id: ACT-actor                     # stamped from the slug, and never reused
name: <Display name>              # --name. The heading below repeats it after the id.
status: active                    # or withdrawn: the file stays and its id is never reused
needs:
  - <what this actor needs from the system, in one sentence>
pkit:
  friction:
    anchors:
      path: ["<code that embodies it>"]        # --path
      record: ["<decision that names it>"]     # --record
---

# ACT-actor — <Display name>

<Who this is, when they come to the system, and what they bring with them.>
