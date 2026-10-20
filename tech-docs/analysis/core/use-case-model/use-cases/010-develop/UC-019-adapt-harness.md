---
id: UC-019
title: Adapt the system to another harness
status: active
actor: ACT-component-author
other-actors:
  - ACT-ai-agent
after:
  - [UC-014]
requirements: []
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/scaffolds.py
        - src/project_kit/capabilities.py
        - src/project_kit/cli.py
        - src/project_kit/install.py
        - src/project_kit/package_validate.py
        - .pkit/schemas/harness-requirements.yaml
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
---

# UC-019 — Adapt the system to another harness

**Goal:** Adapt the system to another harness, and say how far that harness meets the methodology's needs and what of the methodology's permissions it cannot enforce.

**Other actors:**

- **AI agent** (`ACT-ai-agent`): runs the stamp of step 1 for the author through the `adapter-author` skill, which pairs with it (COR-005). In the new harness, its sessions find the skills and agent definitions the adapter deploys.

**Preconditions:**

- **From UC-014:** The methodology's source repository runs the system as written.

**Assumptions:**

- An adapter is authored in the methodology's source repository, and ships with the methodology (COR-005). In a project the system is installed in, sync manages `.pkit/adapters/` (`.pkit/lifecycle/ownership.py`).
- The harness is installed where the author tries the adapter, and the author can watch how it behaves (COR-047).

**Trigger:** The author wants the methodology to work in a harness that no adapter serves yet.

**Main path:**

1. The author runs `pkit new adapter <name>`, or has an AI agent run it through the `adapter-author` skill.
2. The system checks the name. It must be kebab-case and not `backbone`. No capability may hold it, and no adapter may have it already.
3. The system writes the adapter's folder, `.pkit/adapters/<name>/`, with `package.yaml`, a `README.md` and `migrations/`. The package metadata gives `version: 0.1.0`, and a range on the backbone from the version the source repository records.
4. The system records the adapter in the manifest as `kit-shipped`, and prints `Stamped: .pkit/adapters/<name>/`.
5. The author writes the scripts that the system runs, each found by its name and each optional: `merge-settings.sh`, `merge-claude-md.sh`, `deploy-skills.sh` and `deploy-agents.sh`. A fifth, `undeploy-capability.sh`, takes back what the adapter deployed for one capability (COR-005 and COR-013).
6. The author writes the adapter's `permission-enforcement.yaml`. For each kind of permission, such as `command-deny` or `network-egress`, it says where the harness enforces it. It also says whether the harness does so `native`, at `runtime` or `none` (COR-028 point 3).
7. In the adapter's README, the author states how far the harness meets each need that `.pkit/schemas/harness-requirements.yaml` lists, such as `delegated-result-complete` (COR-047 point 2).
8. The author runs `pkit sync` in the source repository.
9. The system runs the scripts of every adapter in the order of the adapters' names (UC-014). So the new adapter's scripts deploy the skills and agent definitions where the new harness reads them.
10. The author runs `pkit validate`. Its `packages` member checks the adapter's package metadata: its name, its version and its range.

**Variants:**

- **2a.** The name is no kebab-case word or is `backbone`, a capability holds it, or an adapter of that name exists. The system refuses with the reason, such as `adapter '<name>' already exists at .pkit/adapters/<name>.`, and writes nothing. The path rejoins at step 1.
- **5a.** The adapter has no `undeploy-capability.sh`. Where a capability is unregistered and its subtree stays, the system warns that the adapter `ships no undeploy-capability.sh`, and that the capability stays deployed in its harness.
- **9a.** A script exits with an error. The system stops with `adapter primitive <script> exited with status <n>. See the output above for details.` The author mends the script, and the path rejoins at step 8.

**Postconditions:**

- The adapter is recorded in the source repository's manifest, and its package metadata gives its version and its range on the backbone.
- Sync runs the adapter's scripts, which deploy the skills and agent definitions where the harness reads them.
- The adapter's README says how far its harness meets each need the methodology states of it. Its `permission-enforcement.yaml` says what of the methodology's permissions the harness enforces, and what it cannot.

**Minimal guarantees:**

- A refused name leaves nothing written, since the system checks the name before it writes the folder (`scaffolds.py`).
- An adapter never takes a name a capability holds (`capabilities.py`).
- A script that fails stops sync with its exit status, so a partial deploy never reads as a whole one (`install.py`).
