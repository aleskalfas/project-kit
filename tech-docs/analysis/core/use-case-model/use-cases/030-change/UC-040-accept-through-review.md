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

- **Developer** (`ACT-developer`): holds the draft in their [change](../../../glossary.md#term-change--change), and builds nothing on it until it is accepted.
- **AI agent** (`ACT-ai-agent`): drafts a [decision record](../../../glossary.md#term-decision-record--decision-record) or a [rule](../../../glossary.md#term-rule--rule), and may propose its acceptance. Where the path involves a person, that person's review accepts the draft, never the agent ([COR-051 point 4](../../../../../../.pkit/decisions/core/COR-051-rule-sets.md#4-statuses-and-the-gate)).

**Preconditions:** **From UC-037 or UC-038:** A [change](../../../glossary.md#term-change--change) holds a [decision record](../../../glossary.md#term-decision-record--decision-record) drafted as `proposed`, or a [rule](../../../glossary.md#term-rule--rule) with no status, so the draft binds nothing.

**Assumptions:**

- An agent writes `accepted` on a record or a [rule](../../../glossary.md#term-rule--rule) only on the merge authoriser's word. Nothing at run time stops it writing the status unasked ([COR-051 point 4](../../../../../../.pkit/decisions/core/COR-051-rule-sets.md#4-statuses-and-the-gate) and core rule 2).
- Who accepts a [decision record](../../../glossary.md#term-decision-record--decision-record) is open. The [acceptance gate](../../../glossary.md#term-acceptance-gate--acceptance-gate) asks only for a reviewed status flip (core rule 2). COR-051 point 4 gives a rule's acceptance to a person's review, and #1674 tracks a record that says the same of a decision record.
- Whoever accepts a rule gives its set the new major [COR-051 point 7](../../../../../../.pkit/decisions/core/COR-051-rule-sets.md#7-inheritance-and-where-rules-bind) asks for. No check compares a set's `version` with the rules it accepts.

**Trigger:** A drafted [decision record](../../../glossary.md#term-decision-record--decision-record) or [rule](../../../glossary.md#term-rule--rule) waits for acceptance.

**Main path:**

1. The merge authoriser reads the draft, with the records it cites.
2. For a [rule](../../../glossary.md#term-rule--rule), the merge authoriser runs `pkit rule-sets reach --preview`. The [system](../../../glossary.md#term-system--system) answers where each proposed rule would bind if it were accepted, and marks what holds only under the preview ([COR-051 point 7](../../../../../../.pkit/decisions/core/COR-051-rule-sets.md#7-inheritance-and-where-rules-bind)).
3. The merge authoriser accepts the draft. Its status becomes `accepted` in a commit of its own, made by the merge authoriser or for them on their word. That commit comes before any work that builds on the draft (core rule 2).
4. An accepted rule's entry carries its origin: the date, who decided and why, in the decider's words. Or its origin cites the [decision record](../../../glossary.md#term-decision-record--decision-record) that holds the reasoning ([COR-051 point 5](../../../../../../.pkit/decisions/core/COR-051-rule-sets.md#5-origins-checked-deterministically)).
5. The developer runs `pkit validate`. Its `rule-sets` pass fails on an accepted rule whose origin is incomplete, or cites a record that is not accepted (COR-051 point 5).
6. From the commit that accepts it, the rule binds on each [artefact](../../../glossary.md#term-artefact--artefact) that a set of the [project](../../../glossary.md#term-project--project)'s own reaches, as `pkit rule-sets reach` answers there. From that commit, work may build on the accepted record (core rule 2).
7. The merge authoriser authorises the merge of the [change](../../../glossary.md#term-change--change) that holds the acceptance (UC-034).

**Variants:**

- **1a.** The merge authoriser holds the draft wrong. The [change](../../../glossary.md#term-change--change) revises it, and the path rejoins at step 1. A draft rejected before it lands is deleted, since no status marks a record rejected. A [rule](../../../glossary.md#term-rule--rule) that already landed proposed is withdrawn instead, and keeps its id ([COR-051 point 4](../../../../../../.pkit/decisions/core/COR-051-rule-sets.md#4-statuses-and-the-gate)).
- **2a.** The draft is a [decision record](../../../glossary.md#term-decision-record--decision-record). No command shows where a record binds, so the merge authoriser reads its decision and its rationale. The path goes on at step 3.
- **3a.** Accepting the rule brings each [artefact](../../../glossary.md#term-artefact--artefact) its sets reach under it. The change owns each break of the rule there, and the rule-set [reviewer](../../../glossary.md#term-reviewer--reviewer) withholds its approval for each settled one ([COR-060 point 1](../../../../../../.pkit/decisions/core/COR-060-brought-under-breaks.md#1-one-kind-whatever-brings-the-text-under-the-rule)). The change mends the text, or narrows a scope to leave a file out until it is mended ([COR-060 point 2](../../../../../../.pkit/decisions/core/COR-060-brought-under-breaks.md#2-no-exception-of-its-own)).
- **3b.** A set of the [project](../../../glossary.md#term-project--project)'s own inherits the rule's set. Accepting the rule needs a new major of that set. Each pin on the old major then holds back every rule of the set ([COR-051 point 7](../../../../../../.pkit/decisions/core/COR-051-rule-sets.md#7-inheritance-and-where-rules-bind)). [Validation](../../../glossary.md#term-validation--validation) fails on each such pin until the project reviews the new major and updates the pin.
- **3c.** The merge authoriser approved the record's addition and its acceptance together, as UC-037 variant 9a says. The record lands `accepted` in the commit that adds it.
- **5a.** The rule's origin cites a decision record that is still proposed. Validation fails, naming the rule. The cited record is accepted first, through this same use case, and the path rejoins at step 5.
- **7a.** The merge authoriser works alone, and commits the acceptance straight to the [default branch](../../../glossary.md#term-default-branch--default-branch), as UC-034 variant 1a says. No [pull request](../../../glossary.md#term-pull-request--pull-request) carries it.

**Postconditions:** The record or the [rule](../../../glossary.md#term-rule--rule) is accepted, through the merge authoriser's review. An accepted rule carries a complete origin, and binds where a set of the [project](../../../glossary.md#term-project--project)'s own reaches it.

**Minimal guarantees:**

- A proposed [rule](../../../glossary.md#term-rule--rule) binds nothing, whatever inherits or cites it ([COR-051 point 4](../../../../../../.pkit/decisions/core/COR-051-rule-sets.md#4-statuses-and-the-gate) and `rule_sets.py`).
- [Validation](../../../glossary.md#term-validation--validation) fails on an accepted rule whose origin is incomplete, or cites a record that is not accepted ([COR-051 point 5](../../../../../../.pkit/decisions/core/COR-051-rule-sets.md#5-origins-checked-deterministically)).
- What `pkit rule-sets reach --preview` answers never reaches validation or a gate (`cli.py`).
- `pkit rule-sets reach` writes nothing (REQ-005).
