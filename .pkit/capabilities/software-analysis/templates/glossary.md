---
# The glossary (software-analysis DEC-001 points 1, 3 and 4): one collection
# file, `glossary.md` under the analysis location, serving everything — one
# entry per term keyed by its stable id, each with a body section headed by
# that id. Stamp entries, never copy them: `pkit analysis new term <slug>` adds
# `TERM-<slug>` and its section, creating the file from this template the
# first time. Renaming a term keeps its id: write the new `name`, and put the
# old one first in `replaces:`. A term anchors to where the software or a
# decision embodies it; one nothing embodies carries `unanchored-because:`.
# Each entry's own fields' shape is `schemas/term.schema.json`.
TERM-term:
  name: <Term>                    # as it is written today; may change, the id does not
  status: active                  # or withdrawn: the entry stays and its id is never reused
  definition: <what the term means, in one sentence>
  pkit:
    friction:
      anchors:
        path: ["<code that embodies it>"]        # --path
        record: ["<decision that defines it>"]   # --record
---

# Glossary

The words of the domain and what each means. A term's id is stable; its name may change, and the names it replaces are kept.

## TERM-term — <Term>

<More on the term when one sentence is not enough: where it applies, what it is not, an example.>
