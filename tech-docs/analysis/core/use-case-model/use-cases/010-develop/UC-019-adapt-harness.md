---
id: UC-019
title: Adapt the system to another harness
status: active
actor: ACT-component-author
other-actors:
  - ACT-ai-agent
after:
  - [UC-014]
requirements:
  - REQ-008
  - REQ-009
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/scaffolds.py
        - src/project_kit/capabilities.py
        - src/project_kit/cli.py
        - src/project_kit/install.py
        - src/project_kit/package_validate.py
        - src/project_kit/harness_support.py
        - src/project_kit/schemas_validate.py
        - .pkit/schemas/harness-requirements.yaml
        - .pkit/schemas/harness-support.schema.json
        - .pkit/adapters/README.md
        - .pkit/skills/core/adapter-author.md
        - .pkit/lifecycle/ownership.py
      record:
        - COR-005
        - COR-013
        - COR-028#3
        - COR-047
      artefact:
        - ACT-component-author
        - ACT-ai-agent
        - REQ-008
        - REQ-009
    revalidated:
      at: 2026-10-25T14:34:45Z
      outcome: unchanged
      unchanged-because: The change alters only the install command pkit init prints at its end, to the tag latest. Registering an adapter and running its primitives are unchanged, so the use case holds.
---

# UC-019 — Adapt the system to another harness

**Goal:** Adapt the system to another harness, and say how far that harness meets the methodology's needs and what of the methodology's permissions it cannot enforce.

**Other actors:**

- **AI agent** (`ACT-ai-agent`): runs the [stamp](../../../glossary.md#term-stamp--stamp) of step 1 for the author through the `adapter-author` [skill](../../../glossary.md#term-skill--skill), which pairs with it (COR-005). In the new [harness](../../../glossary.md#term-harness--harness), its sessions find the skills and [agent definitions](../../../glossary.md#term-agent-definition--agent-definition) the [adapter](../../../glossary.md#term-adapter--adapter) deploys.

**Preconditions:**

- **From UC-014:** The [methodology](../../../glossary.md#term-methodology--methodology)'s [source repository](../../../glossary.md#term-source-repository--source-repository) runs the [system](../../../glossary.md#term-system--system) as written.

**Assumptions:**

- An [adapter](../../../glossary.md#term-adapter--adapter) is authored in the [methodology](../../../glossary.md#term-methodology--methodology)'s [source repository](../../../glossary.md#term-source-repository--source-repository), and ships with the methodology (COR-005). In a [project](../../../glossary.md#term-project--project) the [system](../../../glossary.md#term-system--system) is installed in, [sync](../../../glossary.md#term-sync--sync) manages `.pkit/adapters/` (`.pkit/lifecycle/ownership.py`).
- The [harness](../../../glossary.md#term-harness--harness) is installed where the author tries the adapter, and the author can watch how it behaves (COR-047).

**Trigger:** The author wants the [methodology](../../../glossary.md#term-methodology--methodology) to work in a [harness](../../../glossary.md#term-harness--harness) that no [adapter](../../../glossary.md#term-adapter--adapter) serves yet.

**Main path:**

1. The author runs `pkit new adapter <name>`, or has an AI agent run it through the `adapter-author` [skill](../../../glossary.md#term-skill--skill).
2. The [system](../../../glossary.md#term-system--system) checks the name. It must be kebab-case and not `backbone`. No [capability](../../../glossary.md#term-capability--capability) may hold it, and no [adapter](../../../glossary.md#term-adapter--adapter) may have it already.
3. The system writes the adapter's folder, `.pkit/adapters/<name>/`, with `package.yaml`, a `README.md` and `migrations/`. The [package metadata](../../../glossary.md#term-package-metadata--package-metadata) gives `version: 0.1.0`, and a [range](../../../glossary.md#term-range--range) on the [backbone](../../../glossary.md#term-backbone--backbone) from the [version](../../../glossary.md#term-version--version) the [source repository](../../../glossary.md#term-source-repository--source-repository) records.
4. The system records the adapter in the [manifest](../../../glossary.md#term-manifest--manifest) as `kit-shipped`, and prints `Stamped: .pkit/adapters/<name>/`.
5. The author writes the scripts that the system runs, each found by its name and each optional: `merge-settings.sh`, `merge-claude-md.sh`, `deploy-skills.sh` and `deploy-agents.sh`. A fifth, `undeploy-capability.sh`, takes back what the adapter deployed for one capability (COR-005 and COR-013).
6. The author writes the adapter's `permission-enforcement.yaml`. For each kind of permission, such as `command-deny` or `network-egress`, it says where the [harness](../../../glossary.md#term-harness--harness) enforces it. It also says whether the harness does so `native`, at `runtime` or `none` (COR-028 [point](../../../glossary.md#term-point--point) 3).
7. The author writes the adapter's support declaration, `harness-support.yaml`. It answers each need that `.pkit/schemas/harness-requirements.yaml` lists, such as `delegated-result-complete` (COR-047 point 2). Each need's entry gives a grade, its `harness_versions` and its evidence. The adapter's README states the same entries in prose.
8. The author runs `pkit sync` in the source repository.
9. The system runs the scripts of every adapter in the order of the adapters' names (UC-014). So the new adapter's scripts deploy the skills and [agent definitions](../../../glossary.md#term-agent-definition--agent-definition) where the new harness reads them.
10. The author runs `pkit validate`. Its `packages` member checks the adapter's package metadata: its name, its version and its range. Its `schemas` member checks the support declaration against its schema.
11. The author runs `pkit harness report --adapter <name>`. The system reads only the declaration, never the harness (COR-047 points 3 to 5). So it reports a need `unsatisfied` where its entry grades it `not-achievable` for every version, and it reports the need `indeterminate` otherwise. It exits with status `1` while any need is not `satisfied`.

**Variants:**

- **2a.** The name fails a check of step 2, in one of these ways:
  - the name is no kebab-case word, or is `backbone`
  - a [capability](../../../glossary.md#term-capability--capability) holds the name
  - an [adapter](../../../glossary.md#term-adapter--adapter) of that name exists

  The [system](../../../glossary.md#term-system--system) refuses with the reason, such as `adapter '<name>' already exists at .pkit/adapters/<name>.`, and writes nothing. The path rejoins at step 1.
- **3a.** Until #1600 is done, a test fails on the new adapter, since no [release](../../../glossary.md#term-release--release) may add one yet (REQ-008). The author can try the adapter in the checkout, and the path goes on at step 4. No [change](../../../glossary.md#term-change--change) that holds the adapter lands until then.
- **5a.** The adapter has no `undeploy-capability.sh`. Where a capability is unregistered and its subtree stays, the system warns that the adapter `ships no undeploy-capability.sh`, and that the capability stays deployed in its [harness](../../../glossary.md#term-harness--harness).
- **7a.** The declaration leaves a need out, or gives its entry an empty `harness_versions`. `pkit harness report` gives that need `indeterminate`, with no grade, so a missing entry never reads as a met one (COR-047 [point](../../../glossary.md#term-point--point) 3).
- **9a.** A script exits with an error. The system stops with `adapter primitive <script> exited with status <n>. See the output above for details.` The author mends the script, and the path rejoins at step 8.
- **10a.** The support declaration breaks its schema, such as an `at-cost` entry with no `cost`. [Validation](../../../glossary.md#term-validation--validation) reports it and fails, and `pkit harness report` exits with status `3`. The author mends the declaration, and the path rejoins at step 10.

**Postconditions:**

- The [adapter](../../../glossary.md#term-adapter--adapter) is recorded in the [source repository](../../../glossary.md#term-source-repository--source-repository)'s [manifest](../../../glossary.md#term-manifest--manifest), and its [package metadata](../../../glossary.md#term-package-metadata--package-metadata) gives its [version](../../../glossary.md#term-version--version) and its [range](../../../glossary.md#term-range--range) on the [backbone](../../../glossary.md#term-backbone--backbone).
- [Sync](../../../glossary.md#term-sync--sync) runs the adapter's scripts, which deploy the [skills](../../../glossary.md#term-skill--skill) and [agent definitions](../../../glossary.md#term-agent-definition--agent-definition) where the [harness](../../../glossary.md#term-harness--harness) reads them.
- The adapter's support declaration says how far its harness meets each need the [methodology](../../../glossary.md#term-methodology--methodology) states of it, and `pkit harness report` lists what the harness leaves unmet. The adapter's `permission-enforcement.yaml` says what of the methodology's permissions the harness enforces, and what it cannot.

**Minimal guarantees:**

- A refused name leaves nothing written, since the [system](../../../glossary.md#term-system--system) checks the name before it writes the folder (`scaffolds.py`).
- An [adapter](../../../glossary.md#term-adapter--adapter) never takes a name a [capability](../../../glossary.md#term-capability--capability) holds (`capabilities.py`).
- A script that fails stops [sync](../../../glossary.md#term-sync--sync) with its exit status, so a partial deploy never reads as a whole one (`install.py`).
- A need the declaration leaves out never reads as met: `pkit harness report` gives it `indeterminate` and exits with status `1` (`harness_support.py`).
