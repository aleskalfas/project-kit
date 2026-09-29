---
# A revalidation record (software-analysis DEC-001 points 5 and 6): one check
# of some artefacts against one version of the system, kept only when there is
# something to say — a planned revalidation, or one that finds a gap or a
# regression. A routine one that finds everything holds writes no record: each
# artefact's own revalidation block is the record. Copy it to
# `revalidations/<date>-<subject>.md` under the analysis location. It is an
# act, not an anchored artefact, so it carries no friction block. It may cite
# executed results from the evidence point as support for an outcome (DEC-001
# point 7) — never in place of one. Its front matter's shape is
# `schemas/revalidation-record.schema.json`.
change: "#000"                    # the work item, pull request or range of commits that carried it
trigger: planned                  # planned | drift | scheduled | close | onboarding
date: "2026-01-01"                # the day it was performed
by: <who performed it — a person, or an agent>
confirmed-by: <the person who confirmed an agent's outcomes>   # optional
outcomes:                         # each artefact covered, by id, withdrawn ones included
  UC-000: holds                   # holds | analysis-stale | code-regressed | gap-found
# evidence:                       # optional: executed results drawn on, `<artefact>@<commit>`, the commit's full name
#   - UC-000@0000000000000000000000000000000000000000   # supports an outcome above, never stands in for one
---

# <Date> — <Subject>

## Outcomes

- **UC-000 — holds.** <why the description still stands against this version of the system; the evidence it drew on, if any>

## Gaps

- <behaviour nothing describes, or a description with no behaviour — and what resolved it: the artefact written, or the defect reported>
