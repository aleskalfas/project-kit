---
# A revalidation record (software-analysis DEC-001 points 5 and 6): one check
# of some artefacts against one version of the system, kept only when there is
# something to say — when is the capability README's "Revalidation records";
# what each outcome records on its artefact is its "Revalidation: four
# outcomes, two answers".
# Stamp it, never copy it: `pkit analysis new revalidation <slug> --change <ref>
# --trigger <trigger> --outcome <id>=<outcome> … --because <id>=<why> …
# [--gap "<gap> => <resolution>"]…` writes `revalidations/<date>-<slug>.md`
# under the analysis location, and refuses a record with nothing to say. It is
# an act, not an anchored artefact, so it carries no friction block. It may copy
# executed results from the evidence point as support for an outcome (DEC-001
# point 7) — never in place of one — each entry whole, as the record is history
# and the point holds only what its fillers report now. Its front matter's
# shape is `schemas/revalidation-record.schema.json`.
change: "#000"                    # the work item, pull request or range of commits that carried it
trigger: planned                  # planned | drift | scheduled | close | onboarding
date: "2026-01-01"                # the day it was performed, in UTC
by: <who performed it — a person, or an agent>
confirmed-by: <the person who confirmed an agent's outcomes, or decided stale>   # optional
outcomes:                         # each artefact covered, by id, withdrawn ones included
  UC-000: holds                   # holds | analysis-stale | code-regressed | gap-found
# evidence:                       # optional: the executed results drawn on, each copied whole from the evidence point
#   - id: UC-000@0000000000000000000000000000000000000000   # <artefact>@<commit>: its own two fields below
#     artefact: UC-000            # an artefact given its outcome above: evidence never stands in for one
#     commit: "0000000000000000000000000000000000000000"    # the commit's full name
#     result: passed              # passed | failed — passed supports holds, failed a regression
#     ran: <what was run>         # and optionally `steps`, `where` and `by`, as the point gives them
---

# <Date> — <Subject>

## Outcomes

- **UC-000 — holds.** <why the description still stands against this version of the system; the evidence it drew on, if any, by its id>

## Gaps

- <behaviour nothing describes, or a description with no behaviour> — **resolved:** <the artefact written, or the defect reported>
