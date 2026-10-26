---
id: UC-022
title: Add my own operational rules, the harness's settings, grants and agent paths beside the methodology's
status: active
actor: ACT-adopter
other-actors:
  - ACT-ai-agent
  - ACT-operator
after:
  - [UC-014, UC-049]
  - [UC-014, UC-019, UC-049]
requirements:
  - REQ-002
  - REQ-009
  - REQ-010
  - REQ-012
  - REQ-013
shortfalls:
  - at: 4
    issue: "#1765"
    record: ADR-034#1
  - at: "8a"
    issue: "#1884"
    record: COR-004
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/cli.py
        - src/project_kit/merge.py
        - src/project_kit/permissions.py
        - src/project_kit/agents_overlay.py
        - src/project_kit/install.py
        - .pkit/permissions/decide.py
      record:
        - COR-001
        - COR-002
        - COR-013
        - COR-028#1
        - COR-028#2
        - COR-004
        - ADR-034#1
      artefact:
        - ACT-adopter
        - ACT-ai-agent
        - ACT-operator
        - REQ-002
        - REQ-009
        - REQ-010
        - REQ-012
        - REQ-013
---

# UC-022 — Add my own operational rules, the harness's settings, grants and agent paths beside the methodology's

**Goal:** Add my own operational rules, the harness's settings, permission grants and agent paths beside the methodology's, never editing its files.

**Other actors:**

- **AI agent** (`ACT-ai-agent`): works under the [project](../../../glossary.md#term-project--project)'s [operational rules](../../../glossary.md#term-operational-rule--operational-rule) beside the [methodology](../../../glossary.md#term-methodology--methodology)'s, and by [agent definitions](../../../glossary.md#term-agent-definition--agent-definition) that reach the paths the [overlay](../../../glossary.md#term-overlay--overlay) names. A [grant](../../../glossary.md#term-grant--grant) of the project's never widens a deny the methodology sets ([REQ-013](../../../requirements/functional/020-set-up/REQ-013-deny-wins.md)).
- **Operator** (`ACT-operator`): is asked before a command of this use case writes in another repository than the session's own. So no such write happens silently ([REQ-012](../../../requirements/functional/REQ-012-ask-before-another-repository.md)).

**Preconditions:**

- **From [UC-014](../010-develop/UC-014-develop-methodology.md) or [UC-049](../050-adopt/UC-049-install-system.md):** The [project](../../../glossary.md#term-project--project) runs the [system](../../../glossary.md#term-system--system): it is the [methodology](../../../glossary.md#term-methodology--methodology)'s [source repository](../../../glossary.md#term-source-repository--source-repository), or the system is installed in it.
- **From UC-014, [UC-019](../010-develop/UC-019-adapt-harness.md) or UC-049:** An [adapter](../../../glossary.md#term-adapter--adapter) for the project's [harness](../../../glossary.md#term-harness--harness) runs [merge delivery](../../../glossary.md#term-merge-delivery--merge-delivery) into the files that harness reads, and deploys [skills](../../../glossary.md#term-skill--skill) and [agent definitions](../../../glossary.md#term-agent-definition--agent-definition) there.

**Assumptions:** None.

**Trigger:** The [project](../../../glossary.md#term-project--project) needs rules, settings, grants or paths of its own that the [methodology](../../../glossary.md#term-methodology--methodology) does not ship. An example is an [operational rule](../../../glossary.md#term-operational-rule--operational-rule) on its own tooling.

**Main path:**

1. The adopter writes the [project](../../../glossary.md#term-project--project)'s own [operational rules](../../../glossary.md#term-operational-rule--operational-rule) in `.pkit/rules/project.md`, beside the [methodology](../../../glossary.md#term-methodology--methodology)'s `.pkit/rules/core.md`. [Sync](../../../glossary.md#term-sync--sync) rewrites `core.md` at the [recorded version](../../../glossary.md#term-recorded-version--recorded-version), and never writes `project.md` ([COR-001](../../../../../../.pkit/decisions/core/COR-001-content-mechanisms.md)).
2. The adopter writes the project's own settings for the [harness](../../../glossary.md#term-harness--harness) in the project side of an [adapter](../../../glossary.md#term-adapter--adapter)'s settings. An example is `claude-code`'s `.pkit/adapters/claude-code/settings/project/settings.json`, which first [install](../../../glossary.md#term-install--install) seeded empty.
3. The adopter runs `pkit permissions grant <subject> <privilege>`, such as `pkit permissions grant agent:architect web-fetch`, with `--deny` for a deny [grant](../../../glossary.md#term-grant--grant).
4. At its entry, before it reads anything, each writing command of this use case checks that the repository it writes in is the session's own. Those are `pkit permissions grant` and `revoke`, and later `pkit agents reconcile --write`, `pkit sync` and `pkit merge`. Where the repository is another, the [system](../../../glossary.md#term-system--system) asks the operator, and with nobody to ask it refuses ([REQ-012](../../../requirements/functional/REQ-012-ask-before-another-repository.md)).

> [!WARNING]
> **Not built yet:** none of those five commands runs such a check. [ADR-034 point 1](../../../../../architecture/decisions/ADR-034-foreign-repo-mutation-guard.md#1-the-pkit-self-guard-is-the-honest-reliable-lever) decides that every `pkit` command that writes runs it, and #1765 tracks it.

5. The system checks that the subject is `all`, `operator` or `agent:<name>`, and finds the [privilege](../../../glossary.md#term-privilege--privilege) in the catalog ([COR-028 point 1](../../../../../../.pkit/decisions/core/COR-028-permission-model-realization.md#1-the-model-is-the-source-of-truth)).
6. The system writes the grant to the project's own grants, `.pkit/permissions/project/grants.yaml`, and prints `granted: <subject> allow <privilege>`. The permission model decides each call with the project's grants beside the methodology's, and a deny wins over an allow ([REQ-013](../../../requirements/functional/020-set-up/REQ-013-deny-wins.md)).
7. The adopter names, in the agents' [overlay](../../../glossary.md#term-overlay--overlay) `.pkit/agents/project/overlay.yaml`, the paths each placeholder of an [agent definition](../../../glossary.md#term-agent-definition--agent-definition) stands for, such as `<adr-records>` ([COR-013](../../../../../../.pkit/decisions/core/COR-013-agent-architecture.md)).
8. The adopter runs `pkit agents reconcile`. The system lists each category an agent definition refers to that the overlay does not define, with what it would write, and writes nothing.
9. The adopter runs `pkit agents reconcile --write`, which is the [consent](../../../glossary.md#term-consent--consent). The system adds each missing category, and never writes over a value the adopter set. It fills a category whose conventional folder exists with that folder.
10. The adopter runs `pkit sync`.
11. The system runs each adapter's [merge delivery](../../../glossary.md#term-merge-delivery--merge-delivery) into the files its harness reads ([COR-002](../../../../../../.pkit/decisions/core/COR-002-merge-delivery.md)). The methodology's baseline settings, the project's side and the entries already in the harness's file are joined, and no entry the project wrote is removed.
12. The same merge includes `.pkit/rules/project.md` in the harness's instruction file, after the methodology's `.pkit/rules/core.md`, such as in `claude-code`'s `CLAUDE.md`.
13. Each adapter deploys the agent definitions where its harness reads them, with each placeholder replaced by the paths the overlay gives it (COR-013).

**Variants:**

- **5a.** The subject is none of the three forms, such as `agent:Architect`. The [system](../../../glossary.md#term-system--system) refuses, naming the three forms, and writes nothing. The path rejoins at step 3.
- **5b.** The catalog holds no such [privilege](../../../glossary.md#term-privilege--privilege). The system refuses with ``privilege '<privilege>' is not in the catalog — run `pkit permissions catalog`.``, and writes nothing. The path rejoins at step 3.
- **5c.** The adopter passes `--scope` for a privilege that takes no scope. The system refuses, and writes nothing. The path rejoins at step 3.
- **6a.** The [project](../../../glossary.md#term-project--project)'s grants hold one for that subject and privilege already. The system changes it in place, and prints `updated: <subject> <effect> <privilege>`.
- **6b.** The [grant](../../../glossary.md#term-grant--grant) allows what a [guardrail](../../../glossary.md#term-guardrail--guardrail) or a [capability](../../../glossary.md#term-capability--capability)'s grant denies. The grant is written, and each call that the deny covers stays denied ([REQ-013](../../../requirements/functional/020-set-up/REQ-013-deny-wins.md)).
- **6c.** The adopter takes a grant back with `pkit permissions revoke <subject> <privilege>`. The system removes it, and prints `revoked: <subject> <privilege>`. Where no grant matches, it says there is nothing to revoke, and writes nothing.
- **8a.** The adopter passes `--dry-run`, as to each command whose edit reaches past what the person named. The system shows the same list, and writes nothing ([REQ-009](../../../requirements/quality/REQ-009-preview-before-change.md)).

> [!WARNING]
> **Not built yet:** `pkit agents reconcile` takes no `--dry-run`. It previews by default, and writes with `--write`. [COR-004](../../../../../../.pkit/decisions/core/COR-004-cli-surface.md) decides that it offers the flag, and #1884 tracks it.

- **8b.** The [overlay](../../../glossary.md#term-overlay--overlay) defines every category the [agent definitions](../../../glossary.md#term-agent-definition--agent-definition) refer to. The system prints `overlay is complete — every referenced category is defined.`, and the path goes on at step 10.
- **8c.** The overlay is missing. The system says so, and step 9 creates it from the seed that first [install](../../../glossary.md#term-install--install) writes.
- **9a.** A category carries writes, such as `process-authoring-targets`. The system fills it with an empty list, so the agent definition deploys with no path to write until the adopter names one.
- **9b.** A missing category has no conventional folder in the project. The system appends it commented out, for the adopter to set. Until the adopter sets it, the [adapter](../../../glossary.md#term-adapter--adapter) skips each agent definition that needs it, and names `pkit agents adopt <agent>` ([UC-020](../010-develop/UC-020-own-skill-or-agent.md) variant 9a).
- **10a.** The adopter changed only the [harness](../../../glossary.md#term-harness--harness)'s settings, and runs `pkit merge` instead. The system runs each adapter's merge of the settings alone, and prints `Merge complete.`.
- **10b.** The adopter runs `pkit merge --dry-run`. The system prints `would run` and each adapter's merge script, and runs none of them (REQ-009).
- **10c.** The adopter runs `pkit merge <adapter>` for an adapter the project does not hold. The system refuses with `no installed adapter matches the requested target(s): <names>`, and runs nothing.
- **10d.** The project is not the [methodology](../../../glossary.md#term-methodology--methodology)'s [source repository](../../../glossary.md#term-source-repository--source-repository). The running CLI is at another [version](../../../glossary.md#term-version--version) than the project records, or a [version transition](../../../glossary.md#term-version-transition--version-transition) is incomplete. [Sync](../../../glossary.md#term-sync--sync) stops before it writes, names the remedy, and the use case ends ([REQ-010](../../../requirements/functional/REQ-010-stop-under-another-version.md)).
- **11a.** The adopter removed a safety entry of the methodology's baseline from the harness's settings, such as an explicit deny for a destructive operation. [Merge delivery](../../../glossary.md#term-merge-delivery--merge-delivery) adds it back, since safety wins over the project's preference ([COR-002](../../../../../../.pkit/decisions/core/COR-002-merge-delivery.md)).

**Postconditions:**

- The [project](../../../glossary.md#term-project--project)'s own [operational rules](../../../glossary.md#term-operational-rule--operational-rule), [harness](../../../glossary.md#term-harness--harness) settings, grants and agent paths sit in project-owned files beside the [methodology](../../../glossary.md#term-methodology--methodology)'s. The adopter edited none of the methodology's files ([COR-001](../../../../../../.pkit/decisions/core/COR-001-content-mechanisms.md)).
- The harness's instruction file includes the project's operational rules after the methodology's, and the harness's settings hold the baseline's entries and the project's own.
- The permission model decides each call with the project's grants beside the methodology's, and a deny wins over an allow.
- Each [agent definition](../../../glossary.md#term-agent-definition--agent-definition) whose placeholders the [overlay](../../../glossary.md#term-overlay--overlay) sets is deployed with those paths.

**Minimal guarantees:**

- [Sync](../../../glossary.md#term-sync--sync) never writes `.pkit/rules/project.md`, and writes the [project](../../../glossary.md#term-project--project)'s other own files only through [merge delivery](../../../glossary.md#term-merge-delivery--merge-delivery) ([COR-001](../../../../../../.pkit/decisions/core/COR-001-content-mechanisms.md) and `install.py`).
- Merge delivery never removes an entry the project wrote ([COR-002](../../../../../../.pkit/decisions/core/COR-002-merge-delivery.md)).
- A refused [grant](../../../glossary.md#term-grant--grant) leaves the project's grants as they were (`permissions.py`).
- Reconcile never writes over a value the adopter set in the [overlay](../../../glossary.md#term-overlay--overlay) (`agents_overlay.py`).
- No grant of the project's widens a deny ([COR-028 point 1](../../../../../../.pkit/decisions/core/COR-028-permission-model-realization.md#1-the-model-is-the-source-of-truth) and `decide.py`).
