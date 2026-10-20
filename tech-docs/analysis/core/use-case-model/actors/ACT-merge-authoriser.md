---
id: ACT-merge-authoriser
name: Merge authoriser
status: active
needs:
  - Be told, before I authorise a merge, what changed in each document the change updated, and which documents wait for which follow-up.
  - Leave the check of an agent's answers to a reviewer other than that agent, and authorise the merge as I authorise any other.
  - Be told the same before an agent commits straight to the default branch for me.
  - Have a decision record or rule an agent drafted become binding only through my own review of it.
pkit:
  friction:
    anchors:
      record:
        - COR-050#3
        - project-management:DEC-028
    revalidated:
      at: 2026-10-20T01:36:56Z
      outcome: unchanged
      unchanged-because: It moved into the core's analysis, tech-docs/analysis/core/use-case-model/actors/, with no word changed, so the role and its needs still hold.
---

# ACT-merge-authoriser — Merge authoriser

The person who authorises a change's merge into the default branch. Where work is committed there directly, it is the person the agent works for, before the commit.

- **Human role:** they authorise the merge after they are told what the change updated and what it leaves out of date. The same person's review turns a record or rule an agent drafted into a binding one.
- **Occasions:** at the end of each change, and whenever a drafted record or rule waits for acceptance.
- **Context:** the authority to land the change.
- **Core:** two core rules make this role, and neither needs a work tracker. COR-050 point 3 covers being told what a change updated before its merge or direct commit. The acceptance gate covers accepting a record or rule.
- **Note:** the name is not "approver", because project-management uses that word for a reviewer agent (DEC-028).
