---
id: JRN-001
title: Restart every clone after all sessions died
status: active
actor: ACT-operator
steps:
  - UC-001
  - UC-004
  - UC-003
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/project-management/scripts/_lib/instance_ownership.py
      artefact:
        - UC-001
        - UC-004
        - UC-003
---

# JRN-001 — Restart every clone after all sessions died

**Starts:** Every session in every clone has been killed. The operator wants every clone working again, each in the direction it had, and none idle that could take work.

**Steps:**

1. UC-001 — each clone's new session recovers what the clone owns and where it was heading.
2. UC-004 — the operator sees every clone's position at once, and spots a clone with nothing to do.
3. UC-003 — that clone finds free or reclaimable work and claims it.

**Seams to watch:** where the path passes from one use case to the next — what must carry over, and how it could break.

- **UC-001 → UC-004:** each clone and the overview read ownership through the same fold (ADR-041). If one of them read it another way — a label search on the default comment-log substrate, say — the overview would disagree with what a clone calls its own.
- **UC-004 → UC-003:** an unstarted item the overview shows in another clone's realm must appear in the idle clone's reclaimable list. It breaks if the idle clone's workstream routing filters that item out.

**Done when:** Every clone is working, each in its own direction, and no clone that could take work is idle.
