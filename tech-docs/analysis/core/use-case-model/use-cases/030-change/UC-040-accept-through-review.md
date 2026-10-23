---
id: UC-040
title: Have a drafted record or rule become binding only through my own review
status: active
actor: ACT-merge-authoriser
other-actors:
  - ACT-developer
  - ACT-ai-agent
requirements:
  - REQ-005
after:
  - [UC-037, UC-038]
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/rule_sets.py
        - src/project_kit/rule_set_reading.py
        - src/project_kit/cli.py
        - .pkit/decisions/README.md
        - .pkit/rules/core.md
        - .pkit/skills/core/decision-author.md
      record:
        - COR-051#4
        - COR-051#5
        - COR-051#7
        - COR-060#1
        - COR-060#2
      artefact:
        - ACT-merge-authoriser
        - ACT-developer
        - ACT-ai-agent
        - REQ-005
---

# UC-040 — Have a drafted record or rule become binding only through my own review

**Goal:** Have a decision record or rule an agent drafted become binding only through my own review of it.

**Other actors:**

- **Developer** (`ACT-developer`): holds the draft in their change, and builds nothing on it until it is accepted.
- **AI agent** (`ACT-ai-agent`): drafts a decision record or a rule, and may propose its acceptance. It never accepts the draft on its own (COR-051 point 4).

**Preconditions:** **From UC-037 or UC-038:** A change holds a decision record drafted as `proposed`, or a rule with no status, so the draft binds nothing.

**Assumptions:**

- An agent writes `accepted` on a record or a rule only on the merge authoriser's word. Nothing at run time stops it writing the status unasked (COR-051 point 4 and core rule 2).
- Who accepts a decision record is open. The acceptance gate asks only for a reviewed status flip (core rule 2). COR-051 point 4 gives a rule's acceptance to a person's review, and #1674 tracks a record that says the same of a decision record.

**Trigger:** A change that holds a drafted record or rule comes to the merge authoriser for review.

**Main path:**

1. The merge authoriser reads the draft in the change, with the records it cites and the work the change builds on it.
2. For a rule, the merge authoriser runs `pkit rule-sets reach --preview`. The system answers where each proposed rule would bind if it were accepted, and marks what holds only under the preview (COR-051 point 7).
3. The merge authoriser accepts the draft. Its status moves from `proposed` to `accepted` in a commit of the change, made by the merge authoriser or for them on their word.
4. An accepted rule's entry carries its origin: the date, who decided and why, in the decider's words. Or its origin cites the decision record that holds the reasoning (COR-051 point 5).
5. The developer runs `pkit validate`. Its `rule-sets` pass fails on an accepted rule whose origin is incomplete, or cites a record that is not accepted (COR-051 point 5).
6. The merge authoriser authorises the merge of the change at its head (UC-034).
7. Once the change lands, the accepted rule binds on each artefact that a set of the project's own reaches, as `pkit rule-sets reach` answers. Work may build on the accepted record from then on.

**Variants:**

- **1a.** The merge authoriser holds the draft wrong. The change revises it, and the path rejoins at step 1. A draft the merge authoriser rejects is deleted before it lands, since no status marks a record rejected.
- **2a.** The draft is a decision record. No command shows where a record binds, so the merge authoriser reads what the change builds on it. The path goes on at step 3.
- **3a.** Accepting the rule brings each artefact its sets reach under it. The change owns each break of the rule there, and the rule-set reviewer withholds its approval for each settled one (COR-060 point 1). The change mends the text, or narrows a scope to leave a file out until it is mended (COR-060 point 2).
- **3b.** A set of the project's own inherits the rule's set. A rule newly accepted needs a new major of its set (COR-051 point 7). So the same change raises the set's version, and re-pins each set that inherits it. Otherwise validation fails on each pin left behind its set.
- **3c.** The merge authoriser approved the record's addition and its acceptance together, as UC-037 variant 9a says. The record lands `accepted` in the commit that adds it.
- **5a.** The rule's origin cites a decision record that is still proposed. Validation fails, naming the rule. The cited record is accepted first, through this same use case, and the path rejoins at step 5.
- **6a.** The merge authoriser works alone, and the change is committed straight to the default branch, as UC-034 variant 1a says. That commit carries the acceptance.

**Postconditions:** The record or the rule is accepted on the default branch, through the merge authoriser's review. An accepted rule carries a complete origin, and binds where a set of the project's own reaches it.

**Minimal guarantees:**

- A proposed rule binds nothing, whatever inherits or cites it (COR-051 point 4 and `rule_sets.py`).
- Validation fails on an accepted rule whose origin is incomplete, or cites a record that is not accepted (COR-051 point 5).
- What `pkit rule-sets reach --preview` answers never reaches validation or a gate (`cli.py`).
- `pkit rule-sets reach` writes nothing (REQ-005).
