---
id: UC-001
title: Build my change under my project's conventions
status: active
actor: core:ACT-developer
other-actors:
  - core:ACT-ai-agent
  - core:ACT-merge-authoriser
requirements:
  - REQ-060
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/software-engineering/agents/software-engineer.md
        - .pkit/adapters/claude-code/_resolve_agent.py
        - .pkit/rules/core.md
        - .pkit/rules/project.md
      record:
        - software-engineering:DEC-001
        - software-engineering:DEC-002#4
        - software-engineering:DEC-004
        - project-management:DEC-060#2
        - project-management:DEC-028
        - project-management:DEC-032#D1
        - COR-024
        - COR-050#3
        - ADR-052#3
        - ADR-052#6
        - COR-013
        - COR-017
        - COR-031
        - COR-009
        - ADR-061#3
        - PRJ-002#D1
        - PRJ-002#D2
        - COR-050#6
        - COR-050#9
        - COR-051#4
        - COR-066#1
        - COR-066#2
        - COR-044#2
        - COR-057#5
        - COR-068
        - COR-066#3
        - COR-028
        - COR-039
        - COR-057#2
        - ADR-078
      artefact:
        - REQ-060
---

# UC-001 — Build my change under my project's conventions

**Goal:** Build my change with an agent that writes the change's code to my project's own conventions, read from wherever I keep them.

**Other actors:**

- **AI agent** (`core:ACT-ai-agent`): the `software-engineer` agent, and the reviewer agents that judge its change. Outside a walking skeleton (variant 2b), the engineer never invents a convention the conventions corpus lacks ([software-engineering DEC-001 point 5](../../../../../../.pkit/capabilities/software-engineering/decisions/DEC-001-producer-agent-and-conventions-seam.md#5-empty-tolerance)).
- **Merge authoriser** (`core:ACT-merge-authoriser`): settles each finding a reviewer marks for a person, before authorising the merge ([project-management DEC-028](../../../../../../.pkit/capabilities/project-management/decisions/DEC-028-agent-as-approver-paths.md)).

**Preconditions:** None.

**Assumptions:**

- The project has the software-engineering capability installed, and the adapter has deployed its `software-engineer` agent definition. The core provides both: a capability is installed, or registered in place where it is developed ([COR-017](../../../../../../.pkit/decisions/core/COR-017-capability-pattern.md), [COR-031](../../../../../../.pkit/decisions/core/COR-031-capability-origin.md)), and an adapter deploys its agents ([COR-013](../../../../../../.pkit/decisions/core/COR-013-agent-architecture.md)).
- The running agent finds the conventions corpus the project names. The adapter writes its path into the deployed definition's front matter only, and the agent definition's text keeps `<project-conventions>` (ADR-052 points [3](../../../../../architecture/decisions/ADR-052-optional-read-category-empty-tolerance.md#3-undefined-optional-resolves-to-a-dropped-item-the-agent-deploys) and [6](../../../../../architecture/decisions/ADR-052-optional-read-category-empty-tolerance.md#6-the-agents-return-to-the-angle-bracket-form)).
- Nothing at run time holds the agent to the corpus. Where the project runs the code-review panel, its agents read the corpus too ([software-engineering DEC-002 point 4](../../../../../../.pkit/capabilities/software-engineering/decisions/DEC-002-code-review-panel.md#4-knowledge-split)).
- project-management's merge gate decides which reviewers a pull request needs ([project-management DEC-032 point D1](../../../../../../.pkit/capabilities/project-management/decisions/DEC-032-conditional-reviewer-requirements.md#d1--the-required-local-reviewer-set-resolves-from-the-prs-closing-issues)). The gate leaves a finding marked for a person to the merge authoriser ([project-management DEC-028](../../../../../../.pkit/capabilities/project-management/decisions/DEC-028-agent-as-approver-paths.md)).
- The change builds only on accepted decision records ([RS-OPS-002](../../../../../../.pkit/rule-sets/ops.md#rs-ops-002--the-acceptance-gate) and COR-066 points [1](../../../../../../.pkit/decisions/core/COR-066-accepted-before-landing.md#1-a-proposal-lives-only-in-its-change) and [3](../../../../../../.pkit/decisions/core/COR-066-accepted-before-landing.md#3-the-person-sees-what-the-change-makes-accepted)).
- The agent asks before a destructive operation, such as `git push --force` or deleting files outside `project/` ([RS-OPS-008](../../../../../../.pkit/rule-sets/ops.md#rs-ops-008--pause-and-confirm-before-destructive-operations)).
- The agent works within the permission model, never around it ([RS-OPS-014](../../../../../../.pkit/rule-sets/ops.md#rs-ops-014--dont-escalate-past-the-permission-model), [RS-OPS-015](../../../../../../.pkit/rule-sets/ops.md#rs-ops-015--work-with-the-permission-layer-not-around-it) and [COR-028](../../../../../../.pkit/decisions/core/COR-028-permission-model-realization.md)).
- The agent changes no other repository, unless the person it works for confirms it ([RS-OPS-019](../../../../../../.pkit/rule-sets/ops.md#rs-ops-019--a-session-changes-only-its-own-repository) and [COR-039](../../../../../../.pkit/decisions/core/COR-039-session-repo-mutation-boundary.md)).
- The agent retries once a step that failed for a cause outside its own work, such as a locked signing key. It first checks that the step did not take effect. If it fails again, the agent stops and reports ([RS-OPS-021](../../../../../../.pkit/rule-sets/ops.md#rs-ops-021--retry-once-then-stop)).
- Before it changes files, the agent looks up the accepted records their anchors lead to, and reads those tied to them directly ([RS-OPS-022](../../../../../../.pkit/rule-sets/ops.md#rs-ops-022--read-the-records-a-changes-files-lead-to-first)).
- Before its last commit, the agent follows the rules `pkit rule-sets altered` lists as binding on what its change owns ([RS-OPS-024](../../../../../../.pkit/rule-sets/ops.md#rs-ops-024--follow-the-rule-sets-rules-on-what-your-change-owns) and [COR-057 point 2](../../../../../../.pkit/decisions/core/COR-057-rule-set-reviewer.md#2-what-the-change-owns)).
- In project-kit, the agent runs the tests of what it changed (project rule 2). It leaves the full suite to the pre-push hook and CI ([ADR-078](../../../../../architecture/decisions/ADR-078-ci-suite-parallel-jobs.md)).
- In project-kit, every commit is signed, and signing is never switched off. A commit that fails to sign waits a minute before its one retry (project rule 4).

**Trigger:** The developer asks the `software-engineer` agent to make a change, such as the code an issue asks for.

**Main path:**

1. The developer asks the `software-engineer` agent to make the change.
2. The agent reads the conventions corpus the project names, before it writes any code.
3. The agent writes the change's code, applying the corpus to each choice it settles, such as naming, layout and error handling.
4. The agent reads its diff again against the corpus, and corrects what does not conform.
5. The agent hands the change on for review, and invokes no reviewer itself ([COR-024](../../../../../../.pkit/decisions/core/COR-024-critic-and-architect-agents.md)).
6. The reviewers judge the change: COR-024's stack where the change calls for it, and the reviewers the merge gate requires ([project-management DEC-032 point D1](../../../../../../.pkit/capabilities/project-management/decisions/DEC-032-conditional-reviewer-requirements.md#d1--the-required-local-reviewer-set-resolves-from-the-prs-closing-issues)). Where the project runs the code-review panel, the panel's `security-reviewer` judges the change's code against [REQ-060](../../../requirements/quality/REQ-060-secret-off-command-line.md): a secret never goes on a command line.
7. The agent fixes each finding its reviewer marked blocking, and records each advisory in the pull request with how it was answered. A finding marked for a person waits for the merge authoriser ([project-management DEC-028](../../../../../../.pkit/capabilities/project-management/decisions/DEC-028-agent-as-approver-paths.md)).

**Variants:**

- **2a.** The project names no conventions corpus, or the corpus is empty or silent on a choice. The agent says so, as in "no project conventions found for X; proceeding as a careful generalist", and works by ordinary judgement. The path rejoins at step 3.
- **2b.** The change builds a walking skeleton ([project-management DEC-060 point 2](../../../../../../.pkit/capabilities/project-management/decisions/DEC-060-foundation-before-slices.md#2-the-foundation-is-one-feature-built-one-task-at-a-time)). The path rejoins at step 3, where the agent also writes into the corpus each convention that building the skeleton settles ([software-engineering DEC-004](../../../../../../.pkit/capabilities/software-engineering/decisions/DEC-004-skeleton-conventions-in-corpus.md)). The developer accepts the entries with the skeleton's change, apart from authorising its merge, and the change merges only once they are accepted. Where the corpus offers no single location the project owns, the agent writes none and lists the conventions in its hand-off.
- **3a.** A design fork arises that the corpus does not settle. The agent names it and its trade-off, rather than choosing silently. The developer decides, asked one decision at a time with the agent's recommendation ([RS-OPS-017](../../../../../../.pkit/rule-sets/ops.md#rs-ops-017--discuss-one-decision-at-a-time)), and the path rejoins at step 3.
- **3b.** The change makes an anchored artefact owe an answer. The agent writes the answers its own change owes, as `core:UC-002` describes, and says in its hand-off that the change wrote answers. It composes no list of them, and the path goes on at step 4.

**Postconditions:** The change's code conforms to the project's conventions corpus wherever the corpus speaks, and its reviewers have judged it, with each blocking finding fixed.

**Minimal guarantees:**

- A project that names no conventions corpus still gets the agent definition deployed. The deployed definition drops the read, and the agent works as a generalist (ADR-052 points [3](../../../../../architecture/decisions/ADR-052-optional-read-category-empty-tolerance.md#3-undefined-optional-resolves-to-a-dropped-item-the-agent-deploys) and [6](../../../../../architecture/decisions/ADR-052-optional-read-category-empty-tolerance.md#6-the-agents-return-to-the-angle-bracket-form), and `_resolve_agent.py`).
