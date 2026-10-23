---
id: UC-021
title: Ground a claim in its source
status: active
actor: core:ACT-developer
other-actors:
  - core:ACT-ai-agent
requirements: []
shortfalls:
  - at: 7
    issue: "#1910"
    record: evidence:DEC-003
  - at: "6b"
    issue: "#1910"
    record: evidence:DEC-003
  - at: "7a"
    issue: "#1910"
    record: evidence:DEC-002
pkit:
  friction:
    anchors:
      path:
        - .pkit/capabilities/evidence/scripts/validate.py
        - .pkit/capabilities/evidence/skills/evidence/add.md
        - .pkit/capabilities/evidence/skills/evidence/validate.md
        - .pkit/capabilities/evidence/package.yaml
      record:
        - evidence:DEC-001
        - evidence:DEC-002
        - evidence:DEC-003
        - COR-004
        - COR-005
        - COR-013
        - COR-017
        - COR-021
        - COR-031
---

# UC-021 — Ground a claim in its source

**Goal:** Ground each claim about an outside fact in a recorded excerpt of its source, with each citation checked against the evidence records.

**Other actors:**

- **AI agent** (`core:ACT-ai-agent`): carries out steps 1 to 5 where the developer directs it, through the `evidence` skill's add and validate operations (COR-013). An outside fact it restates from memory with no citation is the failure the capability exists to prevent (evidence DEC-001).

**Preconditions:** None.

**Assumptions:**

- The project has the evidence capability installed, or registered in place where it is developed (COR-017 and COR-031). The adapter of the project's harness deploys the `evidence` skill where the harness reads it (COR-005). The CLI registers `pkit evidence validate` from the capability's package metadata (COR-021).
- `uv` is on the developer's `PATH`. It runs the check, a script that declares what it needs, and installs that on the first run (evidence DEC-003).
- Each excerpt holds the source's words as the source gave them. Nothing checks it, since its fidelity is the discipline of whoever captured it, and the system never fetches a source (evidence DEC-002 and DEC-003).
- Each claim about an outside fact carries a citation. Nothing finds a claim without one, since text with no citation states no outside fact by convention alone (evidence DEC-001).

**Trigger:** The developer, or an AI agent writing for them, is about to state an outside fact in a document of the project (evidence DEC-001).

**Main path:**

1. The developer, or an AI agent they direct through the `evidence` skill, finds the evidence scope of the document. It is the nearest directory, from the document's own upwards, that holds an `evidence.yaml` (evidence DEC-002, the `evidence` skill's add operation).
2. The developer fetches the source, and copies the words that ground the claim, verbatim. The copy holds no more than the claim needs (evidence DEC-002, the `evidence` skill's add operation).
3. The developer appends an evidence record to the scope's `evidence.yaml`. It holds an `id`, a slug that names the fact, with the `source_url`, the `fetched_at` and the `excerpt`. A `title`, a `note` or a `snapshot` is added where it helps (evidence DEC-001 and DEC-002).
4. The developer writes the claim in the document, with the citation `[ev:<id>]` right after it. In a YAML file, it stands in a comment at the end of the claim's line. It may also stand in a field of prose, such as `notes:` (evidence DEC-001).
5. The developer runs `pkit evidence validate <scope>`.
6. The system reads the scope's `evidence.yaml`. It checks that each evidence record holds an `id`, a `source_url`, a `fetched_at` and an `excerpt` (evidence DEC-002). It checks too that each `id` is of the slug's form, `^[a-z0-9][a-z0-9-]*$` (evidence DEC-001, `validate.py`).
7. The system finds each citation in the `.md`, `.yaml` and `.yml` files under the scope. It leaves out the scope's `evidence.yaml`, and the fenced code blocks and HTML comments of each Markdown file (evidence DEC-003).

> [!WARNING]
> **Not built yet:** `validate.py` skips a fence only where it opens at the start of its line. So a fence indented in a list item is read, and a citation in it counts. Evidence DEC-003 decides that fenced code is skipped, and #1910 tracks it.

8. The system checks that each citation names an evidence record of the scope (evidence DEC-003).
9. The system prints `evidence: <n> citation(s) validated against <file> — all resolved.`, and exits 0. Where evidence records stand that no citation names, it adds `(<n> orphan(s) — pass --strict to elevate to errors)` (evidence DEC-003).

**Variants:**

- **1a.** No directory from the document's upwards holds an `evidence.yaml`. The developer creates one in the directory of the work the claim belongs to, holding `schema_version: 1` and `records: []`. The path goes on at step 2 (evidence DEC-002, the `evidence` skill's add operation).
- **2a.** No public source bears the claim out. The developer writes it as the project's own conclusion, with no citation, and the use case ends (the `evidence` skill's add operation).
- **2b.** No public source bears the claim out, and the developer writes a working note of the project as its source. The record's `source_url` points at the note in the repository, and the path goes on at step 3 (the `evidence` skill's add operation).
- **3a.** The scope holds the evidence record the claim needs already. The developer cites that record, and the path goes on at step 4 (the `evidence` skill's add operation).
- **4a.** The claim stands in a file of another type, such as `.json` or `.toml`, which the system never reads. The developer cites the claim in prose the system reads beside it, such as a sibling `.md` file. That prose points to the file (evidence DEC-001).
- **5a.** The developer passes `--strict`. Each evidence record that no citation names is then a finding. Instead of step 9, the system prints `evidence.yaml — orphan record '<id>' — defined but no citation references it.` for each, as variant 8a prints its findings, and exits 1 (evidence DEC-003).
- **5b.** The directory named holds no `evidence.yaml`. Where a citation stands under it, the system reports that the citations have nowhere to resolve, and exits 1. Where none stands, it says so, and exits 0 (`validate.py`).
- **5c.** The path names no directory. The system prints `evidence: scope path is not a directory: <path>`, and exits 2 (evidence DEC-003).
- **5d.** The project holds several evidence scopes. The developer runs the command once for each, such as in a loop over each `evidence.yaml` the project holds (evidence DEC-003).
- **6a.** The `evidence.yaml` does not parse as YAML, its top level is no mapping, its `schema_version` is not 1, or its `records` is no list. The system names the fault, checks no citation, and exits 1 (evidence DEC-002 and DEC-003, `validate.py`).
- **6b.** An evidence record lacks a field that step 6 asks for, or its `id` is not of the slug's form. The system keeps a finding for each, and the path goes on at step 7. Instead of step 9, the system prints the findings as variant 8a does (evidence DEC-003).

> [!WARNING]
> **Not built yet:** an evidence record with no `id` crashes the check with a `KeyError`. Evidence DEC-003 decides that a missing required field is a finding, and #1910 tracks it.

- **7a.** A directory under the scope holds an `evidence.yaml` of its own. Its files belong to that evidence scope, which is checked on its own. So the system leaves them out, that `evidence.yaml` among them (evidence DEC-002 and DEC-003).

> [!WARNING]
> **Not built yet:** run on an outer scope, `validate.py` checks the citations of a nested scope against the outer scope's records. It reads the nested `evidence.yaml` as citing text too. Evidence DEC-002 decides that each scope is checked on its own, and #1910 tracks it.

- **8a.** A citation names no evidence record of the scope. For each, the system prints `<file>:<line> — cited slug '<slug>' has no record.`. It ends with `evidence: <n> violation(s); see above.`, and exits 1 instead of step 9 (evidence DEC-003). The developer adds the record, mends the citation's slug or removes the citation (the `evidence` skill's validate operation). The path rejoins at step 5.

**Postconditions:** The claim stands in its document with a citation. The citation names an evidence record of its scope, which keeps the source's words, where the source lies and when the words were fetched. So whoever reads the claim can follow it to its source (evidence DEC-001).

**Minimal guarantees:**

- The check writes no file of the project (`validate.py`). So it meets `core:REQ-005`, which asks this of each command whose one operation is a check (COR-004).
- A citation that names no evidence record of its scope never passes: the command exits 1 (evidence DEC-003).
- An `evidence.yaml` that does not parse fails the check, and never reads as a scope with no evidence records (evidence DEC-003, `validate.py`).
- The check fetches no source, and compares no excerpt with its source (evidence DEC-003).
