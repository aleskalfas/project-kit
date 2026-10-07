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

- **Occasions:** on every pull request, queued merge and push to the default branch, and on a schedule.
- **Context:** a clean checkout, a base to compare with, and no person to answer a prompt.
