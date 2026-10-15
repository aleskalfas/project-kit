---
# An actor (software-analysis DEC-001 points 1, 3 and 4): a named role that
# uses the system, one file each in `use-case-model/actors/` under the analysis
# location. Its needs sit in this front matter, beside the description below.
# Stamp it, never copy it: `pkit analysis new actor <slug>` writes
# `ACT-<slug>.md` with its id, its name and its anchors. Its heading is its id
# and name, as the front matter gives them. Its body is rendered from the
# actor's declared structure (`schemas/artefact-kinds.yaml`). Each part, and
# each of its needs, holds its hint until you write in its place what it asks
# for. An actor anchors to where the software or a decision embodies it. One
# that nothing embodies carries `unanchored-because:` in its friction block
# instead of anchors (--unanchored-because). Its own fields' shape is
# `schemas/actor.schema.json`, and the friction block is the core's.
id: ACT-actor                     # stamped from the slug, and never reused
name: <Display name>              # --name. The heading below repeats it after the id.
status: active                    # or withdrawn: the file stays and its id is never reused
needs:                            # each need's hint is its placeholder, as a part's is
  - "<!-- pkit:hint What the actor needs from the system, each in one sentence in their own voice. Start with the verb, or with *Never* and the verb, with *I* and *my* where they refer to themselves. Example: Export my report as a file. -->"
pkit:
  friction:
    anchors:
      path: ["<code that embodies it>"]        # --path
      record: ["<decision that names it>"]     # --record
---

# ACT-actor — <Display name>

<!-- pkit:hint What this role is, and what it does with the system. Example: Someone who builds reports from their team's figures. -->

**Occasions:** <!-- pkit:hint On what occasions the actor comes to the system. Write `None.` when there is none. Example: At the end of each week, and whenever a manager asks for figures. -->

**Context:** <!-- pkit:hint What the actor comes with, such as data, authority or a limit. Write `None.` when there is none. Example: A spreadsheet of their team's figures, and no right to publish a template. -->
