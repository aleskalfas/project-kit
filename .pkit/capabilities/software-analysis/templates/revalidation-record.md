---
# A revalidation record (software-analysis DEC-001 points 5 and 6): one check
# of some artefacts against one version of the system, kept only when there is
# something to say. When is the capability README's "Revalidation records".
# What each outcome records on its artefact is its "Revalidation: four
# outcomes, two answers".
# Stamp it, never copy it: `pkit analysis new revalidation <slug> --change <ref>
# --trigger <trigger> --outcome <id>=<outcome> … --because <id>=<why> …
# [--reviewed-against "<title> @ <version> [@ <link>]"]…
# [--gap "<ids>: <gap> => <resolution>"]…` writes
# `revalidations/<date>-<slug>.md` under the analysis location, and refuses a
# record with nothing to say. It is an act, not an anchored artefact, so it
# carries no friction block. Its body is rendered from the record's declared
# structure (`schemas/artefact-kinds.yaml`) with no hints, since the stamp
# writes every part. This record shows each part's declared example: a planned
# revalidation of a use case against a redesign. A record may copy executed
# results from the evidence point as support for an outcome, never in place of
# one (DEC-001 point 7). It copies each entry whole, as the record is history
# and the point holds only what its fillers report now. Its front matter's
# shape is `schemas/revalidation-record.schema.json`.
change: "#42"                     # the work item, the pull request, or a range of commits on the default branch that carried it
trigger: planned                  # planned | drift | scheduled | close | onboarding
reviewed-against:                 # a planned record's only: each source of the design it reviewed
  - title: "#42's body"
    url: https://tracker.example/issues/42   # its link, left out for a source in this repository
    version: "2026-01-05T10:00:00Z"          # with a link: the time it was read, or a commit's full id
  - title: the redesign note
    version: "4c1d2e9a7b3f5d8e0c6a2b4f9e1d3c5a7b9f0e2d"   # without a link: a commit's full id on the default branch, or `this change`
date: "2026-01-05"                # the day it was performed, in UTC
by: <who performed it — a person, or an agent>
confirmed-by: <the person who confirmed an agent's outcomes, or decided stale>   # optional
outcomes:                         # each artefact covered, by id, withdrawn ones included
  UC-007: gap-found               # holds | analysis-stale | code-regressed | gap-found
# evidence:                       # optional: the executed results drawn on, each copied whole from the evidence point
#   - id: UC-007@0000000000000000000000000000000000000000#project.check   # <artefact>@<commit>#<check>: its own three fields below
#     artefact: UC-007            # an artefact given its outcome above: evidence never stands in for one
#     commit: "0000000000000000000000000000000000000000"    # the commit's full name
#     check: project.check        # the executed check, as its filler names it — opening with its own name
#     result: passed              # passed | failed — passed supports holds, failed a regression
#     ran: <what was run>         # and optionally `steps`, `where` and `by`, as the point gives them
---

# 2026-01-05 — Export to a chosen folder

## Outcomes

- **UC-007 — gap-found.** The redesign lets the analyst choose the folder, and step 2 now says so. Variant 2b is new, as the gap says.

## Gaps

- **UC-007:** a read-only folder makes the export write nothing, and no variant described it. **Resolution:** variant 2b written.
