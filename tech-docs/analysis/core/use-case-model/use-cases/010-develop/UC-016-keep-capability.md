---
id: UC-016
title: Keep a capability I wrote in my own repository
status: active
actor: ACT-component-author
other-actors: []
after:
  - [UC-015]
  - [UC-014, UC-019]
requirements: []
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/cli.py
        - src/project_kit/capabilities.py
        - src/project_kit/sync.py
        - src/project_kit/manifest.py
      record:
        - COR-031
        - COR-030
        - ADR-059
      artefact:
        - ACT-component-author
---

# UC-016 — Keep a capability I wrote in my own repository

**Goal:** Keep a capability I wrote in my own repository, where sync never overwrites it and uninstall never deletes it.

**Other actors:** None.

**Preconditions:**

- **From UC-015:** The project holds the capability's subtree, `.pkit/capabilities/<name>/`, with package metadata that gives its version and its range on the backbone.
- **From UC-014 or UC-019:** An adapter for the project's harness deploys skills and agent definitions where that harness reads them.

**Assumptions:** None.

**Trigger:** The author has written the capability, and wants the project to use it.

**Main path:**

1. The author runs `pkit capabilities register <name>`.
2. The system finds the capability authored in the project, at `.pkit/capabilities/<name>/`.
3. The system checks the capability against its own tree: its package metadata, its README and its own schemas (COR-031 point D1).
4. The system checks the capability's range on the backbone the project records, and the capabilities it depends on (COR-030).
5. The system checks that none of the capability's skills or agent definitions collides with one the project already holds.
6. The system records the capability in the manifest with the component origin `incubated-in-repo`, and copies nothing (COR-031 points D2 and D3).
7. The system prints `Registered incubated capability '<name>' v<version> (in-repo) at .pkit/capabilities/<name>/`.
8. The system runs each adapter's scripts, which deploy the capability's skills and agent definitions, and sets up each command the capability registers. Then it asks each question the capability's data points declare.
9. Later, the author runs `pkit sync` in the project, where the system is installed. For the capability, the system prints `incubated   '<name>' — in-repo capability; skipping source-reconciliation.`, and copies nothing over it. It deploys the capability's skills and agent definitions again (COR-031 point D1).
10. Later still, the author runs `pkit capabilities uninstall <name>`. The system takes the capability out of the manifest, and drops its deployed skills and agent definitions (COR-031 point D4).
11. The system keeps the subtree on disk. It prints `Unregistered incubated capability '<name>' in place; your authored files are kept at .pkit/capabilities/<name>/` and `(pass --purge to delete the authored subtree as well.)`.

**Variants:**

- **2a.** No capability of that name is authored in the project. The system refuses with `no capability named '<name>' is authored in this repo at .pkit/capabilities/<name>/.`, names `pkit capabilities install <name>` for a shipped one, and writes nothing. The use case ends.
- **2b.** The capability is already registered as `incubated-in-repo`. The system prints `capability '<name>' is already registered as incubated-in-repo; nothing to do.`, and the use case ends.
- **2c.** The capability is registered with the component origin `kit-shipped`, or with none. After steps 3 and 4, the system changes the origin alone, and deploys nothing again. It prints `Adopted '<name>' v<version> as incubated-in-repo (was kit-shipped); pkit sync will now leave it untouched.`, and the path goes on at step 9.
- **2d.** Outside its source repository, the distribution also ships a capability of that name. The system prints `Note: a capability named '<name>' also ships from kit source.`, registers the project's own, and leaves the shipped one uninstalled (COR-031). At step 9, sync prints a `collision` line for the two, and still leaves the project's own untouched.
- **3a.** The capability breaks its own tree, such as with a range that is no range. The system prints `capability '<name>' is structurally invalid (<n> problem(s)):` and lists each problem. It refuses with `fix the structural problems in your capability tree, then retry.`, and writes nothing. The path rejoins at step 1.
- **4a.** The backbone the project records lies outside the capability's range, or a capability it depends on is missing or outside its range. The system refuses, naming the range it needs and what to install or upgrade, and writes nothing (COR-030). The path rejoins at step 1.
- **5a.** A skill or an agent definition of the capability collides with one the project holds. The system lists each collision, refuses with `rename the colliding artifact(s) in your capability tree, then retry.`, and writes nothing. The path rejoins at step 1.
- **9a.** The project is the methodology's source repository. Sync there copies nothing at all, and prints no line for the capability (UC-014). It deploys the capability's skills and agent definitions again, and the path goes on at step 10.
- **10a.** The author passes `--purge`. The system asks first, since the subtree is `the only copy of this incubated capability's work`, and deletes it only on a yes.
- **10b.** The project is the methodology's source repository. The system refuses `--purge`, since the subtree is the capability's source, and names `git rm -r .pkit/capabilities/<name>` to remove it (ADR-059).

**Postconditions:**

- While it is registered, the manifest records the capability as `incubated-in-repo`, and its skills and agent definitions are deployed. Sync and a version transition leave its subtree as the author wrote it.
- Once it is uninstalled, the manifest no longer records it, and none of its skills or agent definitions is deployed. Its subtree stays on disk as the author wrote it, and `pkit capabilities register` records it again.

**Minimal guarantees:**

- A registration that refuses leaves the manifest as it was, since every check runs before the system records the capability (`cli.py`).
- Sync never copies over a capability recorded as `incubated-in-repo` (COR-031 point D1 and `sync.py`).
- Uninstall deletes the subtree only on `--purge`, once the author confirms it by a reply or `--yes` (COR-031 point D4 and `capabilities.py`).
- Uninstall never deletes a capability's subtree in the methodology's source repository (ADR-059 and `cli.py`).
