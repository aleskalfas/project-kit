---
id: UC-026
title: Start every session with the project's rules loaded
status: active
actor: ACT-ai-agent
other-actors:
  - ACT-operator
  - ACT-adopter
after:
  - [UC-014, UC-049]
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
pkit:
  friction:
    anchors:
      path:
        - src/project_kit/sync.py
        - src/project_kit/install.py
        - .pkit/adapters/README.md
        - .pkit/rules/core.md
        - .pkit/rules/README.md
      record:
        - COR-001
        - COR-002
        - COR-005
        - COR-014
        - ADR-059
        - ADR-034#1
      artefact:
        - ACT-ai-agent
        - ACT-operator
        - ACT-adopter
        - REQ-002
        - REQ-009
        - REQ-010
        - REQ-012
    revalidated:
      at: 2026-10-24T20:55:38Z
      outcome: updated
---

# UC-026 — Start every session with the project's rules loaded

**Goal:** Start every session with the project's rules and conventions loaded.

**Other actors:**

- **Operator** (`ACT-operator`): runs `pkit sync` in the clone. The operator is asked before [sync](../../../glossary.md#term-sync--sync) writes in another repository than the session's own, so no such write happens silently (REQ-012).
- **Adopter** (`ACT-adopter`): writes the [project](../../../glossary.md#term-project--project)'s own [operational rules](../../../glossary.md#term-operational-rule--operational-rule) in `.pkit/rules/project.md`, which sync never writes (COR-001 and `.pkit/rules/README.md`).

**Preconditions:**

- **From UC-014 or UC-049:** The [project](../../../glossary.md#term-project--project) runs the [system](../../../glossary.md#term-system--system): it is the [methodology](../../../glossary.md#term-methodology--methodology)'s [source repository](../../../glossary.md#term-source-repository--source-repository), or the system is installed in it.
- **From UC-014, UC-019 or UC-049:** An [adapter](../../../glossary.md#term-adapter--adapter) for the project's [harness](../../../glossary.md#term-harness--harness) runs [merge delivery](../../../glossary.md#term-merge-delivery--merge-delivery) into the files that harness reads, its instruction file among them.

**Assumptions:**

- The [harness](../../../glossary.md#term-harness--harness) reads its instruction file when a session starts, and follows each include in it. Claude Code, for one, reads the root `CLAUDE.md` and its `@` includes. Nothing in the [system](../../../glossary.md#term-system--system) checks that the harness loads them (COR-001 and COR-005).

**Trigger:** The operator runs `pkit sync` in a clone, such as after pulling a [change](../../../glossary.md#term-change--change).

**Main path:**

1. The operator runs `pkit sync`.
2. At its entry, before it reads anything, each writing command of this use case checks that the repository it writes in is the session's own. Those are `pkit sync`, and `pkit init` and `pkit upgrade` in variant 1a. Where the repository is another, the [system](../../../glossary.md#term-system--system) asks the operator, and with nobody to ask it refuses (REQ-012).

> [!WARNING]
> **Not built yet:** none of those three commands runs such a check, and each writes in whatever repository holds its working directory. ADR-034 [point](../../../glossary.md#term-point--point) 1 decides that every `pkit` command that writes runs it, and #1765 tracks it.

3. The system checks that the running CLI is at the [version](../../../glossary.md#term-version--version) the [project](../../../glossary.md#term-project--project) records, and that no [version transition](../../../glossary.md#term-version-transition--version-transition) is incomplete (REQ-010).
4. The system refreshes the [methodology](../../../glossary.md#term-methodology--methodology)'s [operational rules](../../../glossary.md#term-operational-rule--operational-rule), `.pkit/rules/core.md`, at the [recorded version](../../../glossary.md#term-recorded-version--recorded-version). It leaves the project's own, `.pkit/rules/project.md`, as it is (COR-001, COR-014 and `install.py`).
5. The system runs each [adapter](../../../glossary.md#term-adapter--adapter)'s deploy primitives, the scripts the lifecycle finds by name, in the order `.pkit/adapters/README.md` gives. The second, `merge-claude-md.sh`, includes both files of operational rules in the instruction file its [harness](../../../glossary.md#term-harness--harness) reads (COR-002).
6. The adapter's script finds that the instruction file includes the methodology's operational rules already, and changes nothing. Claude Code's adapter, for one, finds `@.pkit/rules/core.md` in the root `CLAUDE.md`, and prints `exists     CLAUDE.md (already includes @.pkit/rules/core.md)`.
7. A session starts in the project.
8. The harness loads its instruction file, and with it both files of operational rules that the file includes.
9. The agent starts its work with both sets of operational rules in its context, beside the project's own instructions. The methodology's carry the conventions of tool hygiene that every agent follows.

**Variants:**

- **1a.** The adopter installs the [system](../../../glossary.md#term-system--system) with `pkit init`, or upgrades it with `pkit upgrade`. Each checks the repository as step 2 says, writes the [methodology](../../../glossary.md#term-methodology--methodology)'s files and runs the same deploy primitives. The path goes on at step 5.
- **1b.** The operator passes `--dry-run`. The system runs every refusal, names each script it would run with `would run`, and runs none of them (REQ-009). The use case ends.
- **3a.** The [project](../../../glossary.md#term-project--project) is not the methodology's [source repository](../../../glossary.md#term-source-repository--source-repository). The running CLI is at another [version](../../../glossary.md#term-version--version) than the project records, or a [version transition](../../../glossary.md#term-version-transition--version-transition) is incomplete. [Sync](../../../glossary.md#term-sync--sync) stops before it writes, under `--dry-run` too, names the remedy, and the use case ends (REQ-010).
- **4a.** The project is the methodology's source repository, where `.pkit/rules/core.md` is the methodology's own source. Sync copies nothing into the repository, and the path goes on at step 5 (UC-014 and ADR-059).
- **5a.** An [adapter](../../../glossary.md#term-adapter--adapter)'s script exits with an error. The system stops with `adapter primitive <script> exited with status <n>. See the output above for details.`, and the use case ends (`.pkit/adapters/README.md`).
- **6a.** The instruction file is missing. The adapter's script creates it with both includes. Claude Code's adapter writes a `CLAUDE.md` with a heading, an opening paragraph and both includes, and prints `created    CLAUDE.md (minimal host with @-includes)`. The path goes on at step 7.
- **6b.** The instruction file does not include the methodology's [operational rules](../../../glossary.md#term-operational-rule--operational-rule), so the adapter's script adds both includes and removes nothing (COR-002). Claude Code's adapter puts them right after the first level-one heading of `CLAUDE.md`, and prints `insert`. Where `CLAUDE.md` has no such heading, it puts a heading and both includes above the text, and prints `prepend`. The path goes on at step 7.
- **8a.** The project has written no operational rules of its own, as after a first [install](../../../glossary.md#term-install--install), so `.pkit/rules/project.md` does not exist. The adopter writes it as UC-022 says. Until then the include names a missing file, which Claude Code's [harness](../../../glossary.md#term-harness--harness) skips without a word. So the session starts with the methodology's operational rules alone.

**Postconditions:** Each session the [harness](../../../glossary.md#term-harness--harness) starts in the [project](../../../glossary.md#term-project--project) begins with both files of [operational rules](../../../glossary.md#term-operational-rule--operational-rule) in its context. Those are the [methodology](../../../glossary.md#term-methodology--methodology)'s, with their conventions, and the project's own.

**Minimal guarantees:**

- [Merge delivery](../../../glossary.md#term-merge-delivery--merge-delivery) never removes or rewrites what the instruction file already holds. It adds only the includes, with a heading where the file has none (COR-002).
- [Sync](../../../glossary.md#term-sync--sync) never writes `.pkit/rules/project.md` (COR-001 and `install.py`).
- A second run of an [adapter](../../../glossary.md#term-adapter--adapter)'s script changes nothing (`.pkit/adapters/README.md`).
- A script that fails stops sync with its exit status, so a partial deploy never reads as a whole one (`install.py`).
