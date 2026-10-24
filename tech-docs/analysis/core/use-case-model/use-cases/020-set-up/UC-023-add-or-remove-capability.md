---
id: UC-023
title: Add or remove a capability, and be told of a name collision
status: active
actor: ACT-adopter
other-actors:
  - ACT-operator
after:
  - [UC-014, UC-049]
  - [UC-015, UC-048, environment]
  - [UC-014, UC-019, UC-049]
requirements:
  - REQ-002
  - REQ-009
  - REQ-010
  - REQ-012
shortfalls:
  - at: 2
    issue: "#1765"
    record: ADR-034#1
  - at: "3d"
    issue: "#131"
    record: COR-041
  - at: 13
    issue: "#1765"
    record: ADR-034#1
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/cli.py
        - src/project_kit/capabilities.py
        - src/project_kit/declared_rule_sets.py
        - src/project_kit/point_questions.py
        - src/project_kit/manifest.py
      record:
        - COR-017
        - COR-030
        - COR-031
        - COR-041
        - COR-051#3
        - COR-053#6
        - COR-053#8
        - COR-061
        - ADR-059
        - ADR-034#1
      artefact:
        - ACT-adopter
        - ACT-operator
        - REQ-002
        - REQ-009
        - REQ-010
        - REQ-012
---

# UC-023 — Add or remove a capability, and be told of a name collision

**Goal:** Add or remove a capability, one shared from another of my repositories included, and be told of a name collision instead of being overwritten.

**Other actors:**

- **Operator** (`ACT-operator`): is asked before the install or the uninstall writes in another repository than the session's own. So no such write happens silently (REQ-012).

**Preconditions:**

- **From UC-014 or UC-049:** The project runs the system: it is the methodology's source repository, or the system is installed in it.
- **From UC-015 or UC-048, or Environment:** The capability is on hand. The source repository authors it, the distribution of the running CLI ships it, or another repository of the adopter's authors it (COR-017 and COR-041).
- **From UC-014, UC-019 or UC-049:** An adapter for the project's harness deploys skills and agent definitions where that harness reads them.

**Assumptions:** None.

**Trigger:** The project comes to need a discipline a capability packages, or no longer needs one it installed (COR-017).

**Main path:**

1. The adopter runs `pkit capabilities install <name>`.
2. At its entry, before it reads anything, the system checks that the repository it would change is the session's own. Where it is another, the system asks the operator, and with nobody to ask it refuses (REQ-012).

> [!WARNING]
> **Not built yet:** `pkit capabilities install` runs no such check, and writes in whatever repository holds its working directory. ADR-034 point 1 decides that every `pkit` command that writes runs it, and #1765 tracks it.

3. The system refuses a name that is reserved, or that an adapter holds. It finds the capability in the methodology's tree, `.pkit/capabilities/<name>/`.
4. The system checks the capability against the backbone the project records, and against the capabilities installed (COR-017 and COR-030). Its range on the backbone, each capability it requires and each range an installed capability declares on it must hold.
5. The system checks that no rule set of the capability takes a name a project rule set declares (COR-051 point 3).
6. The system finds that the project is the methodology's source repository, run by its own code, where the capability's subtree is its source (ADR-059). So it registers the capability in place, as UC-014's variant 2d does.
7. The system checks that none of the capability's skills or agent definitions collides with other content the project holds.
8. The system records the capability in the manifest with the component origin `kit-shipped`, and copies nothing (COR-031). It prints `Registered capability '<name>' v<version> in place at .pkit/capabilities/<name>/: it is authored in this repository, the methodology's source, so nothing was copied (ADR-059).`
9. The capability may declare a project rule set. Where no rule set of the project's own inherits its method set, the system creates that set (COR-017). Running install is the consent. It prints `created the project rule set <set> at <path>, inheriting <pin> (COR-017): it is the project's own, to edit or remove`.
10. The system runs each adapter's scripts, which deploy the capability's skills and agent definitions, and sets up each command the capability registers.
11. Where a person can answer, the system runs in turn each question the capability's data points declare (COR-061). It prints `<n> question(s) the data points declare (COR-061):`, then a line for each.
12. Later, the adopter runs `pkit capabilities uninstall <name>`.
13. At its entry, the uninstall checks the repository as step 2 does (REQ-012).

> [!WARNING]
> **Not built yet:** `pkit capabilities uninstall` runs no such check. ADR-034 point 1 decides that every `pkit` command that writes runs it, and #1765 tracks it.

14. The system checks that no installed capability requires the capability, and that no installed process waits on it as mandatory. It also checks that nothing in the project refers to it (COR-017). A citation `[<name>:DEC-001]` refers to it, and so does a rule set that inherits its method set.
15. The system says that the subtree is the capability's source, and asks `Unregister '<name>' and keep .pkit/capabilities/<name>/?` (ADR-059).
16. On a yes, the system has each adapter take back what it deployed for the capability, and takes the capability out of the manifest. It deletes nothing, and prints `Unregistered capability '<name>'; nothing was deleted: its source stays at .pkit/capabilities/<name>/.`

**Variants:**

- **1a.** The adopter passes `--plan`. The system shows what the install would connect to and the conflicts it would leave, and writes nothing (UC-024).
- **1b.** The adopter passes `--dry-run`. The system runs every check, says what it would register, create and ask, and writes nothing (REQ-009).
- **1c.** The project is not the methodology's source repository. The running CLI is at another version than the project records, or a version transition is incomplete. The system stops before it reads anything, under `--dry-run` and `--plan` too, names the remedy, and writes nothing (REQ-010). The use case ends.
- **1d.** The project is the methodology's source repository, and the running code is not its own (UC-014 variants 3a and 3b). The system refuses, since the install would copy the capability from that code's tree into the one it is built from. It names the checkout's own code to run instead, and writes nothing (ADR-059). The uninstall refuses the same way.
- **3a.** The name is reserved, or an adapter holds it. The system refuses, saying which, and writes nothing. The use case ends.
- **3b.** No capability of that name ships with the running CLI. The system refuses, naming `pkit capabilities list`, and writes nothing. A capability the project authors is registered instead (UC-016).
- **3c.** The capability is installed already. The system refuses, naming `pkit capabilities upgrade <name>`, and writes nothing. The use case ends.
- **3d.** The capability is authored in another repository, from which the adopter shares it, such as an organisation's own (COR-041). The system pulls it whole, at a ref of that repository the project pins, and checks it as steps 4 and 5 do. It settles each collision as variant 7b does, and records the capability with the component origin `externally-sourced`. The path goes on at step 9.

> [!WARNING]
> **Not built yet:** the system installs only a capability that ships with the running CLI, or one the project authors. COR-041 decides that a capability from another repository is pulled whole at a pinned ref, and #131 tracks it.

- **4a.** The backbone lies outside the capability's range, or a capability it requires is missing or outside its range. The system refuses, naming what to install or upgrade first, and writes nothing (COR-017 and COR-030).
- **4b.** The capability's version lies outside a range an installed capability declares for it. The system warns, naming each such dependent and its range, and refuses unless the adopter passes `--force` (COR-030).
- **4c.** A process connection the capability marks mandatory has no installed upstream, or none at a compatible version. The system refuses with `capability '<name>' v<version> has <n> unmet mandatory process connection(s):`, and lists them. It ends with `Install or upgrade the upstream first, then retry (COR-053 point 6).`, and writes nothing.
- **5a.** A rule set of the capability takes a name a project rule set declares. The system refuses, naming the set and both files, and writes nothing (COR-051 point 3).
- **6a.** The project is not the methodology's source repository. The system takes the capability from the distribution of the running CLI, and copies it, as variants 7b and 8a say (COR-017).
- **7a.** In the source repository, a skill or an agent definition of the capability collides with other content of the project. The system lists each, refuses with `rename the colliding artifact(s) in your capability tree, then retry.`, and writes nothing.
- **7b.** The project is not the source repository (6a), and a skill or an agent definition of the capability collides with one the project holds. For each, the system prints `<kind> '<name>' collides with existing <path>`, and asks `[override / skip / inspect]` (COR-017):
  - **override:** the capability's file replaces the project's once the copy is in place. Git holds the project's file, so the adopter can get it back.
  - **skip:** the project's file stays, and the rest of the capability installs without that artefact.
  - **inspect:** the system shows how the two files differ, and asks again.
- **7c.** The adopter chooses override for a file git does not hold as it stands. The system refuses the override, since git could not give the file back, and asks again.
- **7d.** Nobody can answer the question of variant 7b, since standard input is no terminal. The install stops before anything is copied, and writes nothing.
- **8a.** The project is not the source repository (6a). The system copies the subtree into `.pkit/capabilities/<name>/`, and records the capability in the manifest as `kit-shipped`, with each artefact skipped. It prints `Installed capability '<name>' v<version> at .pkit/capabilities/<name>/`, and removes each file the adopter overrode. The path goes on at step 9.
- **9a.** A rule set of the project's own inherits the capability's method set already. The system creates none, and names the set that inherits it.
- **9b.** The set's file exists, or another rule set declares its name. The system creates none, since install never writes over the project's content, and warns, saying why (COR-017). It names `pkit capabilities project-rule-set <name>`, which shows the set install declares.
- **11a.** Nobody can answer, since standard input and standard output are not both terminals. The system runs no question, and records nothing. It prints each question's command, for a person to run later (COR-061).
- **12a.** The capability is one the adopter authored in the project, registered as `incubated-in-repo`. Its uninstall keeps the subtree, as UC-016 says.
- **12b.** The adopter passes `--plan`. The system lists what the uninstall would leave without a provider, and each entry of the backbone configuration that still names the capability. It writes nothing (COR-053 point 8).
- **12c.** The adopter passes `--dry-run`. The system says what the uninstall would unregister or remove, and writes nothing (REQ-009).
- **14a.** An installed capability requires the capability. The system refuses with `Refusing to uninstall '<name>': <n> installed capability(ies) declare a required dependency on it:`, names each, and writes nothing. `--force` overrides the refusal.
- **14b.** An installed capability's mandatory process connection waits on the capability. The system warns, naming each connection the uninstall would leave unmet, and refuses unless the adopter passes `--force` (COR-053 point 6).
- **14c.** Something in the project refers to the capability. The system refuses with `Refusing to uninstall '<name>': <n> reference(s) found:`, and lists them. It ends with `Clean references first, or pass --force to override.`, and writes nothing (COR-017).
- **15a.** The project is not the methodology's source repository. The system asks nothing, deletes the subtree, and takes the capability out of the manifest. It prints `Removed capability '<name>' from <path>`, and each adapter's scripts drop what they deployed for it.
- **15b.** In the source repository, the adopter passes `--purge`. The system refuses, since uninstall never deletes a capability's source, and names `git rm -r .pkit/capabilities/<name>` (ADR-059).
- **15c.** The adopter declines. The system writes nothing, and the use case ends.

**Postconditions:**

- Once installed, the manifest records the capability, and its skills and agent definitions are deployed where the harness reads them. Where it declares a project rule set and none of the project's own inherits its method set, the project holds that set as its own.
- In the source repository, the capability's subtree is its source, and nothing was copied. Elsewhere, the project holds a copy at the version it records, and the manifest records each artefact skipped.
- Once uninstalled, the manifest no longer records the capability, and none of its skills or agent definitions is deployed. In the source repository its subtree stays.

**Minimal guarantees:**

- Every check runs before the first write, so an install that refuses leaves the manifest and the project's files as they were (`cli.py`).
- No collision is settled silently: the source repository refuses it, and elsewhere the adopter chooses for each (COR-017 and `capabilities.py`).
- An override removes only a file that git holds as it stands, so git can give it back (`capabilities.py`).
- The install never writes over a file of the project's to create its rule set (COR-017 and `declared_rule_sets.py`).
- Uninstall never deletes a capability's subtree in the source repository (ADR-059 and `cli.py`).
