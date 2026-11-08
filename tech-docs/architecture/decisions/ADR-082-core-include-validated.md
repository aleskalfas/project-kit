---
id: ADR-082
title: Validation fails a host file that does not include core's rules
status: proposed
date: 2026-11-08
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** `pkit validate` fails a project whose `CLAUDE.md`, or the host file another adapter declares, does not hold the line that includes core's operational rules. It fails it as it fails one without the line that reaches the capabilities' rules index ([ADR-076](ADR-076-capability-rules-index.md) point 5).
- **What fails:** a host file the checkout holds that lacks core's include on a line of its own, outside fenced code. The finding names the line and says that the next sync inserts it. Where the include sits only in fenced code or a code span, it says that the project moves it out of the code.
- **How severe:** an `error`, of the kind the index's finding has, `loaded-rules-undelivered`.
- **Where the check lives:** in the backbone, in the one function that checks the index's line, not in a validator the adapter registers. It takes core's include from the line the adapter declares.
- **Where it runs:** wherever the checkout holds the host file, whether or not it holds the index.

## Context

Core's loaded file reaches a session through one include in the project's host file, `@.pkit/rules/core.md` in Claude Code's `CLAUDE.md`. The adapter's merge primitive inserts it wherever it is absent ([COR-002](../../../.pkit/decisions/core/COR-002-merge-delivery.md)). Where the include stands only in fenced code or a code span, the primitive inserts nothing and says so, since only the project can say where its include belongs (ADR-076 point 3). Core's set binds in every project, from its first session ([COR-068](../../../.pkit/decisions/core/COR-068-loaded-rule-sets.md) point 4).

The check of the index's line reads core's include only to word that finding's remedy (ADR-076 point 5). By itself, it passes a `CLAUDE.md` that lost core's include, whose sessions then load none of core's rules (#2445).

The check of a capability's delivery is decided ([COR-070](../../../.pkit/decisions/core/COR-070-capability-loaded-rules.md) point 6), and no earlier record decides one for core's include. Two homes are open for it:
- the backbone's delivery check, which reads the host file each registered adapter declares (ADR-076 point 5);
- a validator the adapter registers, as an installed component may ([ADR-058](ADR-058-validator-registry.md) point 4).

## Decision

**Validation's `rule-sets` member fails, as an `error` of the kind `loaded-rules-undelivered`, a host file the checkout holds that does not hold core's include. The backbone's delivery check gives the finding. It takes the include from each registered adapter's `loaded_rules:` key, and reads the host file as it reads it for the index's line (ADR-076 point 2).**

### 1. What fails

- **The finding:** for each registered adapter that declares `loaded_rules:`, an `error` where the checkout holds its `host:` file and that file does not hold core's include, by the definition of holding a line (ADR-076 point 2).
- **What it names:** the host file, the line, core's loaded file and the adapter.
- **What mends it, named in the finding:**
  - where the include stands only in fenced code or a code span, the project's own edit, moving it out of the code, since the merge inserts nothing there (ADR-076 point 3);
  - otherwise, the next sync, whose merge inserts the include.
- **Several adapters that declare one host file and one form of core's include** get one finding for it, naming each adapter.
- **A host file that holds neither line** fails once for each line, where the index's line is checked (ADR-076 point 5). Each line carries another layer's rules, so each finding says which layer's a session misses.
- **What the reading misses:** it judges the host file's lines, not what the harness imports. It fails a host that includes core's rules some other way, such as in a sentence, and the sync then inserts the line. It passes a line the harness may skip, such as one inside an HTML comment. Both come from the definition of holding a line (ADR-076 point 2), which this record keeps.

### 2. One reading of the host file for both lines

The host file is read once, the same way for core's include and for the index's line (refinement of ADR-076 points 2, 3 and 5):
- **Its bytes:** a byte that is not UTF-8 is kept rather than refused, so the backbone reads the same lines as the merge primitive, which reads bytes.
- **No file:** a host path the checkout holds that is no readable file, such as a folder, fails for each line that is checked, and the finding says to make it a file that holds the line.
- **Only in code:** where an include stands only in fenced code or a code span is the merge primitive's reading, by which it refuses (ADR-076 point 3). The backbone reads it the same way, for core's finding and for the remedy the index's finding names. One table of test cases holds the primitive and the backbone to it, as one table does for holding a line (ADR-076 point 2).

### 3. An error, of the kind the index's finding has

- **The severity** is `error`, the one severity that fails (ADR-058 point 2).
- **The kind** is `loaded-rules-undelivered`, which names a loaded file that does not reach a session through the delivery (ADR-076 point 5). The message names the layer, core's here.

### 4. The backbone's check, beside the index's line

The one function that compares what an adapter declares it delivers with what the checkout holds gives this finding too (refinement of ADR-076 point 5). An adapter whose harness reaches core's file another way needs a key of its own or a validator it registers, decided with that adapter, as for a capability's files (ADR-076 point 4).

### 5. The check runs wherever the checkout holds the host file

- **Where it runs:** the check reads core's include wherever the checkout holds the host file, whether or not it holds the index, and whether or not the registered adapters' `entry:` forms differ.
- **A host file the checkout does not hold** is a summary line, not a finding, on every path of the check: its sessions load no layer's rules through it, and the next sync writes it with every include.
- **An adapter that declares no `loaded_rules:`** gives the backbone no host file or form to read, so core's include goes unchecked for its harness. The warning for such an adapter says so (ADR-076 point 5).

### 6. Core's include is the declared line, read for core's file

- **What `line:` gives:** the host's form of a line that includes the index or core's loaded file, `{index}` standing for that file's path read from the host file's folder (refinement of ADR-076 point 4). Read for the index's path, it is the index's line. Read for core's loaded file's path, it is core's include, `@.pkit/rules/core.md` for Claude Code. The slot keeps its name.
- **What declaring it commits an adapter to:** its merge primitive keeps core's include present in `host:`, in that form, as it keeps the index's line. Otherwise the finding's remedy, the next sync, would not mend it.
- **Held to the primitive:** the merge primitive keeps its own copy of core's include, and a test holds that copy equal to the line the key renders, as a test holds its copy of the index's line (ADR-076 point 3).

## Rationale

**Why validation checks core's include.** Core's rules keep the methodology's invariants, and bind in every project from its first session (COR-068 point 4). A host file without their include reaches none of them. A check that fails a missing index line and passes a missing core include fails the narrower loss and passes the wider one.

**Why an error.** A finding fails where an invariant is broken ([COR-055](../../../.pkit/decisions/core/COR-055-validation.md) point 5). Here the invariant is that the host file holds core's include, which the merge keeps present wherever it is absent (COR-002; ADR-076 point 3). The project owns the file and can correct it, by the next sync or, where the include stands only in code, by its own edit.

**Why the backbone's check.** Core's include and the index's line are two lines of one host file. The reading of a line is kept in one function, held to the merge primitive's by one table of cases (ADR-076 point 2). The delivery check reads each declared host file by that function, and words the remedy for the index's line from core's include. A validator the adapter registered would read the same file by a second implementation, for one adapter only. The backbone sees nothing where an adapter declares no key, which the warning for that adapter names (point 5).

**Why one reading for both lines.** Each line's finding tells the project what the next sync does. The finding is true only where the backbone reads the file as the merge primitive does, byte for byte and code for code.

**Why whether or not the index is there.** The index's absence is a summary line, since the index is committed with `.pkit/` and its absence means no render ran (ADR-076 point 5). The index's line arrives with that render's sync ("Why the line is inserted whenever the adapter is installed", ADR-076), so a checkout without the index may lack the line for the same reason, and neither fails. Core's include arrives with the adapter's first install, so no state of the index explains its absence.

**Why a missing host file is a summary line.** A checkout without the host file is one where no install or sync wrote it, or whose project keeps it out of version control, as a continuous-integration checkout may be. The next sync writes it with every include. The same reason makes an absent delivery of a capability's rules a report rather than a failure ("Why validation reports, rather than fails, where the delivery is absent", COR-070).

**Why the delivery check's kind.** Both findings are about one thing: a loaded file that does not reach a session through the host file. One kind lets a reader find every layer's, and the message names the layer.

**Why from `line:`.** A capability's loaded file reaches a session by the route that carries core's (COR-070 point 2). An adapter that reaches the index by `line:` in `host:` reaches core's file by the same route, so the same form gives both lines. The key gives that form as data, so the backbone holds no harness's syntax (ADR-076 point 4). A key of its own for core's include would be a second form that every adapter declares and keeps equal to `line:`, with no adapter yet whose two lines differ. The cost of the shared form is that a wrong reading of it fails a project, not just one remedy's wording, and the test that holds the primitive's copy to the key guards it.

### Alternatives considered

- **A validator the Claude Code adapter registers** (ADR-058 point 4). Not taken, as "Why the backbone's check" says.
- **The merge primitive, run as a process of its own in a mode that only reports,** registered as the adapter's validator. Not taken: each `pkit validate` would run the adapter's primitive, while one table of cases already holds the two readings together.
- **The lines each merge target declares, read as data,** one check for every line the merge keeps present. Not taken: it needs the merge targets' declarations in a schema, which an adapter that needs it decides.
- **A warning.** Rejected, as "Why an error" says.
- **A kind of its own,** such as `core-rules-undelivered`. Not taken, as "Why the delivery check's kind" says.
- **Checking core's include only where the checkout holds the index.** Rejected, as "Why whether or not the index is there" says.
- **Failing a missing host file where the project commits it.** Not taken: the check would need to know what the project keeps in version control, and the next sync writes the file with every include.
- **One finding for a host file that holds neither line.** Not taken: a finding for each line says which layers' rules a session misses.
- **Checking the project's include, `@.pkit/rules/project.md`.** Not taken: the merge inserts it only together with core's, so a project may remove it (ADR-076 point 3).

## Implications

- **ADR-076** is refined in place, each edit with a forward pointer to this record:
  - **The Summary:** its "The check" bullet names a `CLAUDE.md` without core's include among what fails.
  - **The Decision's top line:** names a `CLAUDE.md` without core's include among what fails.
  - **Point 2:** its "Holds the line" says that a host file's bytes are read as the merge primitive reads them, a byte that is not UTF-8 kept rather than refused.
  - **Point 3:** its "Outside a fence" says that the backbone reads "only in code" as the primitive does, and that one table of cases holds the two to it.
  - **Point 4:** its `line:` bullet says that the same form, read for core's loaded file's path, is core's include. Its "What it says, and no more" says that the key also gives that include's form, and that the adapter's merge keeps the include present in it.
  - **Point 5:** its "What fails" list gains a host file the checkout holds that does not hold core's include, whether or not it holds the index, with its remedy. Its item on the index's line names the remedy for an include in fenced code or a code span. It gains "Where the host file is not", a summary line on every path. Its "One function for it" says that function gives this finding too. Its "No declaration" says the warning also names that core's include goes unchecked for that adapter's harness.
- **The documents:** the CLI reference's `validate`, the rules reference, the rules guide, the adapters' reference, the Claude Code adapter's README, its package metadata's comment on `loaded_rules:`, and the package schema's description of the key say that validation fails a host file without core's include.
- **What newly fails:** a project whose `CLAUDE.md` holds core's include nowhere outside code fails `pkit validate`, where it passed. The next sync mends it, except where the include stands only in code. The changeset says so. Nothing is renamed or removed, so no migration is due ([COR-010](../../../.pkit/decisions/core/COR-010-resource-lifecycle.md)).
- **A sync that adds a line the host file holds:** that the merge inserts only the lines a host lacks, so that no line stands twice once the sync mends this finding, is #2443's.
- **Not decided here:** a host file that holds core's include while the checkout lacks core's loaded file. A capability's file in that state fails (ADR-076 point 5). A follow-up issue takes it up for core's.
- **Stands on these records, all accepted:** COR-002, COR-010, COR-055, COR-068, COR-070, ADR-058 and ADR-076.
