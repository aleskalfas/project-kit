---
id: REQ-012
title: The system asks the operator before its command changes another repository
status: active
statement: The system asks the operator before its command changes a repository other than the session's own, or its hosting service.
measure: Run with the session anchor in one repository and its target in another, the command asks at a terminal before its first write. It changes something only on a yes, or on a confirmation passed with the call. With nobody to ask and no confirmation, it refuses and changes nothing.
applies-to: "Every `pkit` command that writes, whether its write lands in files, in a repository's history or on the hosting service (ADR-034 point 1). A report is outside it, a write of another kind to the repository of the distribution (ADR-047 point 1). Where the harness gives no session anchor, such as in a pipeline, there is nothing to compare, and the check does not fire."
obligation: v1:sha256:733ebab1206e7a12d7abd746681ba23d38fa3a226e684a4550749c84ff7c30dd
actors:
  - ACT-operator
refines: []
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/session_guard.py
        - tests/test_session_guard.py
        - tests/test_pull_request_land.py
        - tests/test_pull_request_landing.py
        - tests/test_versioning.py
        - tests/test_release.py
        - tests/test_release_merge.py
        - tests/test_release_publish_notes.py
      record:
        - COR-039
        - ADR-034#1
        - ADR-047#1
      artefact:
        - ACT-operator
---

# REQ-012 · Functional · The system asks the operator before its command changes another repository

**Verified by:** Tests of the check find that the session's own repository passes silently. Another repository, with no terminal and no confirmation, is refused unasked. At a terminal the check asks on standard error, and only a yes passes. A dry run never asks.

Tests run a [pull request](../../glossary.md#term-pull-request--pull-request)'s landing and its deletion of a branch from another repository. Tests run `pkit version tag --push`, `pkit release apply`, `release merge` and `release publish-notes` there too. Each refuses before its first write, and a confirmation passed with the call lets it go on. No test covers any other command that writes, since none of them runs the check yet (#1765).

**Rationale:** A session carries the governance of the repository it is rooted in. So a write it makes in another repository runs under the wrong [project](../../glossary.md#term-project--project)'s rules ([COR-039](../../../../../.pkit/decisions/core/COR-039-session-repo-mutation-boundary.md)). The operator confirms each such write, and none happens silently ([COR-039 point 1](../../../../../.pkit/decisions/core/COR-039-session-repo-mutation-boundary.md#1-operator-gated-not-blocked)).

[ADR-034 point 1](../../../../architecture/decisions/ADR-034-foreign-repo-mutation-guard.md#1-the-pkit-self-guard-is-the-honest-reliable-lever) puts the check in `pkit` itself. It compares the [session anchor](../../glossary.md#term-session-anchor--session-anchor), which does not move with `cd`, with the repository the command would write in. Today only the commands that write to the hosting service run it, and #1765 tracks the rest.

The check is an interlock against an accidental write, not a security boundary ([COR-039 point 3](../../../../../.pkit/decisions/core/COR-039-session-repo-mutation-boundary.md#3-honest-about-reach--an-interlock-not-a-security-boundary)). A raw `git` or `gh` command, or an unset session anchor, routes around it.
