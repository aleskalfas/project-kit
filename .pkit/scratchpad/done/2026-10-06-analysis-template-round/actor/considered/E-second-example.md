---
id: ACT-ci-pipeline
name: CI pipeline
status: active
needs:
  - Run every check with no terminal and no person to answer, and gate the merge on its exit status.
  - Compare a change with its real base, the pull request's target or the queued merge's base, named once for all the checks.
  - Run the checks offline once the checkout is provisioned.
  - Get findings in a machine-readable form, to publish them where people look.
  - Be told when a shallow clone lacks history a check needs, rather than get a misleading result.
  - Have the whole-repository check report its findings without failing, so the check can run after merges and on a schedule.
  - Tag a release once it lands, from the version it declares, with no one there to confirm the push.
pkit:
  friction:
    anchors:
      record:
        - COR-054
        - COR-050
---

# ACT-ci-pipeline — CI pipeline

A project's continuous integration, acting on the system from outside. It is an actor because it starts work on its own trigger with no person in the session.

- **Comes:** on every pull request, queued merge and push to the default branch, and on a schedule.
- **Brings:** a clean checkout, a base to compare with, and no person to answer a prompt.
- **In the model:** its needs are what the system must give an unattended runner. The goals its runs serve belong to people:
  - The change check serves the developer and the merge authoriser.
  - The whole-repository report serves the developer (a change to what a document rests on reaches them).
  - A release tag serves the methodology maintainer.
- **Core:** the backbone ships no workflow. It ships only checks made to run unattended, and one base a pipeline names for all of them (COR-054 point 3). The checks bind once the project makes them a required status (COR-050 point 12).
- **Note:** project-kit's workflows are one wiring of these. Two of their steps are project-kit's alone: the changeset guard and the release tag (PRJ-002).
