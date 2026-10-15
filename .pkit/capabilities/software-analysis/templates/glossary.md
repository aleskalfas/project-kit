---
# The glossary (software-analysis DEC-001 points 1, 3 and 4): one collection
# file, `glossary.md` under the analysis location, serving everything — one
# entry per term keyed by its stable id, each with a body section headed by
# that id. Stamp entries, never copy them: `pkit analysis new term <slug>` adds
# `TERM-<slug>` and its section, creating the file the first time with the
# head below. The head and each section are rendered from the term's declared
# structure (`schemas/artefact-kinds.yaml`). Each part, and each entry's
# definition, holds its hint until you write in its place what it asks for.
# Renaming a term keeps its id: write the new `name`, and put the old one
# first in `replaces:`. A term anchors to where the software or a decision
# embodies it; one nothing embodies carries `unanchored-because:` in its
# friction block instead of anchors (--unanchored-because). Each entry's own fields' shape is
# `schemas/term.schema.json`.
TERM-term:
  name: <Term>                    # as it is written today; may change, the id does not
  status: active                  # or withdrawn: the entry stays and its id is never reused
  definition: "<!-- pkit:hint What the term means, in a phrase of the same part of speech that could replace it. Start with its broader kind, with no article, then say what sets it apart. End with no full stop, and never repeat the term. Example: layout an administrator publishes, from which an analyst builds a report -->"
  pkit:
    friction:
      anchors:
        path: ["<code that embodies it>"]        # --path
        record: ["<decision that defines it>"]   # --record
---

# Glossary

The words of the domain and what each means. A term's id is stable, and its name may change. The names it replaces are kept.

## TERM-term — <Term>

**Example:** <!-- pkit:hint One case of the term, in a sentence or two that use it as the analysis would. Write `None.` when the definition needs none. Example: the analyst builds the weekly report from the template the administrator published. -->

**Distinctions:** <!-- pkit:hint Each word the term could be confused with, labelled with that word, and how the two differ. Include a word the project avoids for this thing, or a working name that now means something else. Write `None.` when there is none. Example: **Report:** what an analyst builds from a template. A template holds no figures. -->
