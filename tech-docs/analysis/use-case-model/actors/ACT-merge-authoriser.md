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
      at: 2026-10-18T12:33:08Z
      outcome: unchanged
      unchanged-because: Point 3 now also has the reviewer check each target a change revisited by changing it, and tells the person which targets of a link the change leaves out of date (point 16). The actor still needs to be told what changed in each updated document and which documents wait for which follow-up, and to leave the check of an agent's answers to a reviewer, which point 3 still says.
---

# ACT-merge-authoriser — Merge authoriser

The person who authorises a change's merge into the default branch. Where work is committed there directly, it is the person the agent works for, before the commit.

- **Human role:** they authorise the merge after they are told what the change updated and what it leaves out of date. The same person's review turns a record or rule an agent drafted into a binding one.
- **Occasions:** at the end of each change, and whenever a drafted record or rule waits for acceptance.
- **Context:** the authority to land the change.
- **Core:** two core rules make this role, and neither needs a work tracker. COR-050 point 3 covers being told what a change updated before its merge or direct commit. The acceptance gate covers accepting a record or rule.
- **Note:** the name is not "approver", because project-management uses that word for a reviewer agent (DEC-028).
