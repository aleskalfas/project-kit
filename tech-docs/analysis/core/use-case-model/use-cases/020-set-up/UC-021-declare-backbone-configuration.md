---
id: UC-021
title: Declare my project's backbone configuration once, and have it validated
status: active
actor: ACT-adopter
other-actors:
  - ACT-operator
after:
  - [UC-014, UC-049]
requirements:
  - REQ-002
  - REQ-005
  - REQ-009
  - REQ-012
  - REQ-014
  - REQ-015
shortfalls:
  - at: "1a"
    issue: "#1884"
    record: COR-004
  - at: 2
    issue: "#1765"
    record: ADR-034#1
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/cli.py
        - src/project_kit/project_config.py
        - src/project_kit/config_validate.py
        - src/project_kit/docs_roots.py
        - .pkit/schemas/backbone/config.schema.json
      record:
        - COR-048
        - COR-049
        - COR-054#1
        - COR-050#14
        - COR-051#6
        - COR-004
        - ADR-034#1
      artefact:
        - ACT-adopter
        - ACT-operator
        - REQ-002
        - REQ-005
        - REQ-009
        - REQ-012
        - REQ-014
        - REQ-015
---

# UC-021 — Declare my project's backbone configuration once, and have it validated

**Goal:** Declare my project's backbone configuration once (name, default branch, documentation roots, friction mode, anchored places, declared surface, excluded paths) and have it validated.

**Other actors:**

- **Operator** (`ACT-operator`): is asked before `pkit config set` writes in a repository other than the session's own, so no such write happens silently ([REQ-012](../../../requirements/functional/REQ-012-ask-before-another-repository.md)).

**Preconditions:** **From [UC-014](../010-develop/UC-014-develop-methodology.md) or [UC-049](../050-adopt/UC-049-install-system.md):** The [project](../../../glossary.md#term-project--project) runs the [system](../../../glossary.md#term-system--system): it is the [methodology](../../../glossary.md#term-methodology--methodology)'s [source repository](../../../glossary.md#term-source-repository--source-repository), or the system is installed in it.

**Assumptions:** None.

**Trigger:** The adopter sets the [project](../../../glossary.md#term-project--project) up, or the project comes to need another value, such as a [default branch](../../../glossary.md#term-default-branch--default-branch) other than `main`.

**Main path:**

1. The adopter runs `pkit config set <key> <value>` for each key that holds one value, such as `pkit config set repository.default-branch trunk`. Such keys include `name`, `repository.default-branch`, `docs.internal`, `docs.user` and `friction.mode` (COR-048, COR-049 [point](../../../glossary.md#term-point--point) 1 and COR-054 point 1).
2. At its entry, before it reads anything, the [system](../../../glossary.md#term-system--system) checks that the repository it would write in is the session's own. Where it is another, the system asks the operator, and with nobody to ask it refuses ([REQ-012](../../../requirements/functional/REQ-012-ask-before-another-repository.md)).

> [!WARNING]
> **Not built yet:** `pkit config set` runs no such check, and writes in whatever repository holds its working directory. ADR-034 point 1 decides that every `pkit` command that writes runs it, and #1765 tracks it.

3. The system finds the key in the [backbone configuration](../../../glossary.md#term-backbone-configuration--backbone-configuration)'s schema, `.pkit/schemas/backbone/config.schema.json`, and converts the value to the key's type, such as `true` for a boolean.
4. The system applies the value to the contents of `.pkit/project/config.yaml`, and validates the whole result against the schema before it asks anything (COR-048 point 4).
5. The system asks once, `Set <key> = '<value>' in .pkit/project/config.yaml? [Y/n]` (COR-048 point 5).
6. On a yes, the system writes only the lines of that key, so the rest of the file stays as the adopter wrote it. A [project](../../../glossary.md#term-project--project) without the file gains it at its first key (COR-048 point 7).
7. The system prints `set <key> = <value>  (.pkit/project/config.yaml)`. It renders `.pkit/.gitignore` again, since that render reads the configuration.
8. The adopter writes the keys that hold a list in the file by hand, since `pkit config set` sets single values only. They are the places, `friction.places`, the declared surface, `friction.surface`, and the excluded paths, `friction.exclude` (COR-050 point 14).
9. The adopter runs `pkit validate`. Its member `configuration` checks the whole file against the schema and against the records that own its keys, and changes no file ([REQ-005](../../../requirements/quality/REQ-005-reading-writes-nothing.md)).
10. The system checks each [documentation root](../../../glossary.md#term-documentation-root--documentation-root) against COR-049 point 1: its resolved path lies inside the repository and outside the [methodology](../../../glossary.md#term-methodology--methodology)'s tree, `.pkit/`.
11. The system prints `.pkit/project/config.yaml: valid.`, and the check passes.

**Variants:**

- **1a.** The adopter passes `--dry-run`, to see first each edit the command would make. The [system](../../../glossary.md#term-system--system) names each edit, and writes nothing ([REQ-009](../../../requirements/quality/REQ-009-preview-before-change.md)).

> [!WARNING]
> **Not built yet:** `pkit config set` takes no `--dry-run`, and refuses the flag. COR-004 decides that it offers one, and #1884 tracks it.

- **1b.** The adopter passes `--yes`. The system asks nothing at step 5, and the path goes on at step 6.
- **3a.** The key is unknown, such as `doc`. The system refuses with `at the top level: unknown key 'doc'; did you mean 'docs'?`, and writes nothing. The path rejoins at step 1.
- **3b.** The key holds a list or a mapping, such as `friction.places`. The system refuses, saying that `config set` sets single values only, and names the file to edit. It writes nothing, and the path goes on at step 8.
- **3c.** The key lies under the reserved `project` block, which the [project](../../../glossary.md#term-project--project)'s own records own. The system refuses, since the [backbone](../../../glossary.md#term-backbone--backbone) never writes there, and writes nothing (COR-048 [point](../../../glossary.md#term-point--point) 2).
- **4a.** The result would break the schema, such as `friction.mode` set to `loud`. The system refuses with `refusing to write .pkit/project/config.yaml: the result would not validate against the backbone configuration schema. Nothing was written.` It adds one line for each error, such as `/friction/mode: 'loud' is not one of ['warning', 'enforcing']`. The path rejoins at step 1.
- **4b.** The key holds that value already. The system prints `<key> is already <value>; nothing to write.`, writes nothing, and the use case ends.
- **4c.** The file does not parse as YAML, or holds no mapping of keys to values. The system refuses to write over it, says to fix it first, and names `pkit validate` for the details. It writes nothing.
- **5a.** Standard input is no terminal, and the adopter gave no `--yes`. The system refuses with `refusing to write .pkit/project/config.yaml without consent: stdin is not a terminal and --yes was not given (COR-048 point 5).` It names the command to run with `--yes`, and writes nothing.
- **5b.** The adopter declines. The system writes nothing, and the use case ends.
- **6a.** The key is `docs.internal`, and a [rule set](../../../glossary.md#term-rule-set--rule-set) of the project's own lies in the folder the old root gives the rule sets. In the same write, the system records that folder among the places, under the same [consent](../../../glossary.md#term-consent--consent) (COR-051 point 6). It prints `recorded project rule sets = <folder>  (.pkit/project/config.yaml)`, and how to move them.
- **6b.** The key is a [documentation root](../../../glossary.md#term-documentation-root--documentation-root), and documentation locations are recorded already. No document moves, and each recorded location stays as it is. Only a location chosen afterwards derives from the new root ([REQ-014](../../../requirements/functional/020-set-up/REQ-014-root-change-moves-nothing.md)). For `docs.internal`, the system prints each recorded location the old root held and the new one does not, with how to move it.
- **8a.** The adopter changes `docs.internal` by hand, and a rule set of the project's own lies in the folder the old root gave the rule sets. At step 9, [validation](../../../glossary.md#term-validation--validation) fails on each such rule set, since no [place](../../../glossary.md#term-place--place) finds it. It names three ways to mend it, such as adding its folder to `friction.places` (COR-051 point 6).
- **9a.** A key written by hand is unknown, or its value breaks the schema. Validation reports an error, naming the nearest known key for an unknown one, such as `unknown key 'doc'; did you mean 'docs'?`. It fails (COR-048 point 4), and the adopter mends the file. The path rejoins at step 9.
- **9b.** The file is missing or empty. Validation prints `.pkit/project/config.yaml: absent or empty: defaults apply.`, and passes, since each key's owning record gives its default (COR-048 point 3).
- **10a.** A documentation root lies outside the repository, or inside `.pkit/`. Validation fails on it (COR-049 point 1). The adopter mends the root, and the path rejoins at step 1.
- **10b.** A declared documentation root does not exist yet. Validation warns with `documentation root '<root>' does not exist yet; the default applies to readers until it is created (COR-049 point 7).`, and passes ([REQ-015](../../../requirements/functional/REQ-015-missing-root-warns.md)).

**Postconditions:**

- The [backbone configuration](../../../glossary.md#term-backbone-configuration--backbone-configuration), `.pkit/project/config.yaml`, holds the [project](../../../glossary.md#term-project--project)'s declarations, and [validation](../../../glossary.md#term-validation--validation) passes it. Every command reads its keys from it, and a key it leaves out takes its owning record's default (COR-048 [point](../../../glossary.md#term-point--point) 3).
- The file is the project's own. [Sync](../../../glossary.md#term-sync--sync) never writes it, and no upgrade or uninstall removes it (COR-048 point 1).

**Minimal guarantees:**

- A value that would make the file break its schema is never written (COR-048 [point](../../../glossary.md#term-point--point) 4 and `project_config.py`).
- With nobody to ask and no `--yes`, nothing is written (COR-048 point 5 and `project_config.py`).
- An edit of a [documentation root](../../../glossary.md#term-documentation-root--documentation-root) moves no document (COR-049 point 6 and `docs_roots.py`).
