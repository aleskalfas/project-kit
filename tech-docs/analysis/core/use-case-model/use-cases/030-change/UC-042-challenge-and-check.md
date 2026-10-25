---
id: UC-042
title: Have my draft challenged and my diff checked against the conventions
status: active
actor: ACT-developer
other-actors:
  - ACT-ai-agent
requirements:
  - REQ-005
  - REQ-021
after:
  - [UC-014, UC-049]
  - [UC-027]
pkit:
  friction:
    anchors:
      path:
        - .pkit/agents/core/critic.md
        - .pkit/agents/core/architect.md
        - .pkit/agents/core/convention-compliance-reviewer.md
        - .pkit/agents/core/rule-set-reviewer.md
        - src/project_kit/rule_set_reading.py
        - src/project_kit/cli.py
      record:
        - COR-024
        - COR-001
        - COR-008
        - COR-047#2
        - COR-051#7
        - COR-057#1
        - COR-057#2
        - COR-057#3
        - COR-057#5
        - COR-060#1
      artefact:
        - ACT-developer
        - ACT-ai-agent
        - REQ-005
        - REQ-021
    revalidated:
      at: 2026-10-25T01:38:31Z
      outcome: unchanged
      unchanged-because: pkit refs lookup now takes several ids, and this change adds pkit friction move-plan and says in the help of the writers where they write. No step here looks a record up, and the commands this use case runs do what it says.
---

# UC-042 — Have my draft challenged and my diff checked against the conventions

**Goal:** Have a substantive draft challenged before I adopt it, and have my diff checked against the methodology's conventions before I commit it.

**Other actors:**

- **AI agent** (`ACT-ai-agent`): each [reviewer](../../../glossary.md#term-reviewer--reviewer) is an AI agent that a session dispatches by its [agent definition](../../../glossary.md#term-agent-definition--agent-definition). It judges the draft or the diff, and changes nothing it judges (REQ-021). The agent making the [change](../../../glossary.md#term-change--change) may dispatch the reviewers for the developer.

**Preconditions:**

- **From UC-014 or UC-049:** The [project](../../../glossary.md#term-project--project) runs the [system](../../../glossary.md#term-system--system): it is the [methodology](../../../glossary.md#term-methodology--methodology)'s [source repository](../../../glossary.md#term-source-repository--source-repository), or the system is installed in it.
- **From UC-027:** The [agent definitions](../../../glossary.md#term-agent-definition--agent-definition) of the critic, the `convention-compliance-reviewer` and the `rule-set-reviewer` are deployed where the [harness](../../../glossary.md#term-harness--harness) reads them.

**Assumptions:**

- The [harness](../../../glossary.md#term-harness--harness) hands each [reviewer](../../../glossary.md#term-reviewer--reviewer)'s whole result back to the session that dispatched it, as UC-029 describes. It does so at the cost the [adapter](../../../glossary.md#term-adapter--adapter)'s support declaration names (COR-047 [point](../../../glossary.md#term-point--point) 2).
- A reviewer keeps to the remit its [agent definition](../../../glossary.md#term-agent-definition--agent-definition) gives it, read-only included. Nothing at run time checks what a reviewer changed, beyond the tools the harness grants it (COR-024 and COR-057 point 1).
- The rule-set reviewer judges under no [rule](../../../glossary.md#term-rule--rule) but those the [backbone](../../../glossary.md#term-backbone--backbone)'s one <!-- pkit:not-the-term -->answer gives. It approves no [change](../../../glossary.md#term-change--change) it could not judge, nor one in which it found a settled break. Nothing checks its verdict against the rules (COR-057 points 1 and 3).

**Trigger:** The developer, or the agent making the [change](../../../glossary.md#term-change--change), has a substantive draft to adopt, or a diff to commit.

**Main path:**

1. Before the developer adopts a substantive draft, the developer or the agent making the [change](../../../glossary.md#term-change--change) dispatches the critic on it. Such a draft is a [decision record](../../../glossary.md#term-decision-record--decision-record), a plan across [components](../../../glossary.md#term-component--component) or an architectural rework (COR-024).
2. The critic reads the draft and its context. It returns its critique as red flags, gaps, weak reasoning, overlooked alternatives and agreements worth stating (COR-024).
3. The critic edits nothing and runs nothing, since its [agent definition](../../../glossary.md#term-agent-definition--agent-definition) grants it only tools that read (COR-024 and REQ-021).
4. The developer revises the draft, or answers each critique held wrong, and adopts the draft.
5. Before committing, the developer dispatches the `convention-compliance-reviewer` on the diff, and on the commits the branch holds already.
6. The [reviewer](../../../glossary.md#term-reviewer--reviewer) checks them against the conventions every [project](../../../glossary.md#term-project--project) shares (COR-008 and COR-001):
   - the form of each commit message the branch holds, `<type>(<scope>): <description>`, and one logical unit for each commit
   - the branch's name, `<type>/<issue-number>-<slug>`
   - no edit of a [synced copy](../../../glossary.md#term-synced-copy--synced-copy), in a project that receives the [methodology](../../../glossary.md#term-methodology--methodology) by [sync](../../../glossary.md#term-sync--sync)
   - each [surface change](../../../glossary.md#term-surface-change--surface-change) declared as the project's own policy asks
   - each cited record accepted
7. The reviewer reports each violation, with the record it breaks and what to do, and changes nothing (REQ-021).
8. Beside it, the developer dispatches the `rule-set-reviewer` on the change. The developer names the form of its verdict and the marks of its [findings](../../../glossary.md#term-finding--finding) (COR-057 [point](../../../glossary.md#term-point--point) 3).
9. The reviewer runs `pkit rule-sets altered`. The [system](../../../glossary.md#term-system--system) lists each [artefact](../../../glossary.md#term-artefact--artefact) the change alters or brings under a [rule](../../../glossary.md#term-rule--rule). It gives the accepted rules that bind on each, at the [base](../../../glossary.md#term-base--base) and at the [head](../../../glossary.md#term-head--head) (COR-057 point 1).
10. The reviewer judges the text the change owns in each listed artefact, under those rules. It leaves each part of a rule that a declared check enforces to that check (COR-057 points 1 and 2).
11. The reviewer reports each finding with its rule's id, the artefact, the line and the passage. Each is a settled break, a passage for a person or a finding that informs. It approves only where it found no settled break, and changes nothing it judged (COR-057 point 3 and REQ-021).
12. The developer mends each violation and each settled break, and commits the change.

**Variants:**

- **1a.** The draft is trivia, such as a reply to a question, an edit of one file or a decision of one line. Nobody dispatches the critic (COR-024), and the path goes on at step 5.
- **1b.** The developer asks for a contrary view of a conclusion that feels settled, or sweeps an open question. The critic runs on it as steps 2 and 3 say (COR-024).
- **4a.** The draft touches the big picture, such as a new abstraction, an edit to a foundational record or a concern across [components](../../../glossary.md#term-component--component). Where the architect's [agent definition](../../../glossary.md#term-agent-definition--agent-definition) is deployed, the developer dispatches it after the critic, and the architect flags where an authorisation is needed. It advises, and refuses nothing. It edits only the architecture documents and [decision records](../../../glossary.md#term-decision-record--decision-record) that the [overlay](../../../glossary.md#term-overlay--overlay) gives it (COR-024).
- **4b.** The draft is an [artefact](../../../glossary.md#term-artefact--artefact) once written, such as a decision record, a [skill](../../../glossary.md#term-skill--skill) or an agent definition. The developer dispatches the `methodology-reviewer` on it, as UC-041 does for a core record.
- **5a.** The developer has committed the [change](../../../glossary.md#term-change--change) already, and dispatches the [reviewer](../../../glossary.md#term-reviewer--reviewer) before pushing it. The reviewer walks the branch's commits as step 6 says.
- **7a.** The reviewer finds a violation. The developer mends it, and the path rejoins at step 5.
- **8a.** Nobody names the form. The reviewer states its verdict, and each [finding](../../../glossary.md#term-finding--finding)'s kind, in plain words (COR-057 [point](../../../glossary.md#term-point--point) 3).
- **9a.** The command gives no result, such as where the [base](../../../glossary.md#term-base--base) resolves to no commit. The reviewer cannot judge the change, so it does not approve, and says why (COR-057 point 3).
- **10a.** The change brings an artefact under a [rule](../../../glossary.md#term-rule--rule) without altering it, such as by accepting the rule or widening a set's scope. For that rule, the change owns the whole artefact, and a settled break there withholds approval (COR-060 point 1).
- **10b.** A rule reaches the artefact only through a pin behind its set, so it binds nothing. The reviewer may name a break of it as a finding that informs (COR-057 point 3).
- **11a.** A finding needs a reading the rule does not settle, or a fact the rule does not name. It is a passage for a person, which withholds no approval and waits for a person's judgement (COR-057 point 3).
- **11b.** A gate requires the reviewer, such as one a component contributes it to. Its verdict holds the change only as that gate says. Elsewhere the reviewer advises, and holds nothing (COR-057 point 5).

**Postconditions:** The draft was challenged before the developer adopted it. The diff was checked against the shared conventions and the accepted rules before its commit, and each violation and settled break is mended.

**Minimal guarantees:**

- `pkit rule-sets altered` lists only accepted rules that bind, and names each [rule](../../../glossary.md#term-rule--rule) a pin behind its set holds back (COR-051 [point](../../../glossary.md#term-point--point) 7).
- `pkit rule-sets altered` writes nothing (REQ-005).
