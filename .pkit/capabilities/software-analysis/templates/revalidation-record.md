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
# an act, not an anchored artefact, so it carries no friction block. Its front
# matter's shape is `schemas/revalidation-record.schema.json`.
change: "#000"                    # the work item, pull request or range of commits that carried it
trigger: planned                  # planned | drift | scheduled | close | onboarding
date: "2026-01-01"                # the day it was performed, in UTC
by: <who performed it — a person, or an agent>
confirmed-by: <the person who confirmed an agent's outcomes, or decided stale>   # optional
outcomes:                         # each artefact covered, by id, withdrawn ones included
  UC-000: holds                   # holds | analysis-stale | code-regressed | gap-found
---

# <Date> — <Subject>

## Outcomes

- **UC-000 — holds.** <why the description still stands against this version of the system>

## Gaps

- <behaviour nothing describes, or a description with no behaviour> — **resolved:** <the artefact written, or the defect reported>
