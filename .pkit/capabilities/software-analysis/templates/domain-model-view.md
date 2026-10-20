---
# A domain-model view (software-analysis DEC-004): a group of related concepts,
# each explained in a section of its own, and drawn as they relate. Stamp it,
# never copy it: `pkit analysis new view <slug> --number <number> --explains
# <TERM-id> …` writes `<number>-<slug>.md` in `domain-model/` under the analysis
# location. The number gives the view's place in the domain model's order, and
# is no part of its id. The stamp writes its title, `explains`, an anchor to each
# term it explains, one section for each, and each term's link to its section in
# the glossary. `explains` is the source: `pkit analysis validate` requires the
# term anchors to match it, and each section's heading to be its term's name
# with its first letter capitalized, such as `## Order` for the term `order`.
# A diagram labels each concept's box the same way.
# A view anchors the records its statements cite or apply (`--record`), and no
# code. Its body is rendered from the view's declared structure
# (`schemas/artefact-kinds.yaml`). Each part holds its hint until you write in
# its place what it asks for. Its own fields' shape is
# `schemas/domain-model-view.schema.json`.
id: VIEW-view                     # stamped from the slug, and never reused
title: <Title>                    # --title; the heading below repeats it after the id
status: active                    # or withdrawn: the file stays and its id is never reused
explains: [TERM-term]             # --explains: each term whose concept it explains, in the order of its sections
pkit:
  friction:
    anchors:
      record: ["<record it rests on>"]   # --record: each record its statements cite or apply
      artefact: [TERM-term]              # each term `explains` lists, written by the stamp
---

# VIEW-view — <Title>

<!-- pkit:hint What the group of concepts covers, then its class diagram. Draw the concepts, how they relate and the attributes that matter, in a Mermaid fence with an `accTitle`, an `accDescr` and no styling. Label each concept's box by its term's name with its first letter capitalized. Example: The concepts of ordering goods and paying for them, and how a payment settles an order. -->

## <Term>

<!-- pkit:hint What the concept is, in plain words for a newcomer. What it says fits exactly what the term's definition fits. Example: An order is what a customer asks the shop to send, before anything is paid or sent. -->

**Attributes:** <!-- pkit:hint What each instance of the concept holds, in words. Write `None.` when there is none. Example: Each order holds its lines, the customer who placed it and the day it was placed. -->

**Relations:** <!-- pkit:hint How the concept relates to other concepts, such as those of this group or of a view numbered before it. Write `None.` when there is none. Example: An order belongs to one customer, and one payment or more settle it. -->

**States:** <!-- pkit:hint The concept's states, and the events that move it from one to the next. Add a state diagram after the text where it has a life cycle. Write `None.` when it has none. Example: An order is open until a payment settles it, and settled until it is sent. -->

**Always true:** <!-- pkit:hint What holds of every instance, as a record decides it, naming the record. Write `None.` when no record decides one. Example: An order once settled is never changed (DEC-007). -->
