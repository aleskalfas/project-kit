---
id: ADR-097
title: A command's machine-readable output keeps its keys for its callers, and never reuses one
status: proposed
date: 2026-11-15
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** a command that prints a document for a program to read, as `--json` does, makes a contract with each caller that reads it. The contract is the document's keys, what each means, the values a key may take where the document lists them, and the document's version where it has one. A sentence written for people is not in it, and neither is the human view. A key or a value added breaks no caller, since a caller ignores a key it does not read and never reads a value it does not know as one it knows. A key or a value that goes, or changes its meaning, breaks a caller: it is a breaking change of the component, and the document's version rises where it has one. A key that went never comes back to mean something else. It would pass as an addition, which declares nothing, and a caller that still holds it would read the new meaning as the old one. A new key for the new meaning costs no caller anything.

Five contracts stated parts of this rule, each for its own document, and differed in what each left out. This record states it once, for every command of the backbone and of the capabilities project-kit ships. One accepted record, project-management's reading of a data point's document, reads a value it does not know as one it knows, and this record refines it.

**Why an ADR.** The documents commands print are how project-kit's components reach each other ([ADR-057](ADR-057-backbone-engines-and-command-limits.md) point 1). An interface others use is what the project built, which is an architecture record's question ([COR-025](../../../.pkit/decisions/core/COR-025-adr-decision-space.md), "Distinct from PRJ"). The rule must bind the records and references that define each document, as well as the code that prints it. The conventions corpus binds only the code ([PRJ-013](../../../.pkit/decisions/project/PRJ-013-coding-conventions.md) point 4), so it can point to this record but cannot hold it. The rule spans the backbone and several capabilities, so it is no one capability's record.

## Context

**The callers.** A capability's script never imports the backbone. It reaches the backbone's engines through their machine-readable reading commands (ADR-057 point 1), and the configuration recorder by running it ([ADR-084](ADR-084-capability-config-contract.md) point 2). Agents, a project's pipeline and a person's own tooling read the same documents, and capabilities' commands print documents of their own, such as project-management's pre-check report. Each caller keys on the document: it finds what it needs by a key and decides on the value there.

**Each contract states its own rule.**
- **The process status document** ([ADR-024](ADR-024-cli-prose-wrapping.md) point 4) is the surface a script keys on, never the human narrative. No presentation choice reaches it: it is byte-identical on a terminal of any width and in a pipe.
- **The landing check's document** ([ADR-081](ADR-081-landing-check.md) point 8) has a version of its own, raised when a key a reader relies on changes its meaning or goes, never for a key added.
- **The configuration recorder's document** (ADR-084 point 2) is what a capability's script decides on, and carries a schema version.
- **A data point's document,** as project-management reads it ([project-management:DEC-054-use-case-validation] point 3): a caller decides on its `outcome` and its fillers' `state`, never on the sentence in `why`. An outcome or a version it does not know reads as could not check.
- **Pre-check's report,** in the record that issue #3193 drafts, which is proposed and binds nothing: each check has a key that stays whatever its outcome or its wording. A key added breaks no caller. A key that goes or comes to name another check, and a changed outcome value, break one. A key is never reused.
- **The CLI reference** states the version rule for each reading document of the friction checks and for a data point's document. It adds there that a value added to a listed set raises no version, since a reader reads a value it does not know as not judged, or as could not tell.

**Where they differ.** They agree on what they share, and differ in what each leaves out. Only #3193's draft says that a key is never reused. Only DEC-054 and the CLI reference say how a caller reads a value it does not know, and the CLI reference names that reading for some sets and not for others. None says whether a key that no caller is known to read is in the contract. The author of a new document finds the rule only by reading whichever of these they happen to know. The architect's review of #3193's draft found the recurrence ([COR-007](../../../.pkit/decisions/core/COR-007-pattern-extraction.md)), and issue #3250 asked for one rule.

## Decision

**A command's machine-readable output is a contract with each caller that reads it: its keys, their meanings and the values of their sets, never its prose. A key or a value added breaks no caller. One that goes or changes its meaning breaks callers, and is a breaking change of its component. A key or a value that went never comes back with another meaning.**

### 1. What the rule covers

- **A command's document.** The rule covers each document a command prints for a program to read, on the command's request for machine-readable output. It covers every command of the backbone and of each capability project-kit ships. This record calls that output the command's *document*.
- **Its callers** are whatever reads it: another component's script, an agent, a project's pipeline or a person's own tooling. Point 3 binds each caller project-kit ships. A caller outside project-kit learns the contract where the command is documented (point 6).
- **Not covered:**
  - What a command prints for the backbone as a query's answer, such as a data point's value or an anchor resolver's answer. Its shape and its version are the core's ([COR-052](../../../.pkit/decisions/core/COR-052-slots.md) point 5 for a data point's value, [COR-050](../../../.pkit/decisions/core/COR-050-anchors-and-friction.md) point 2 for a resolver's answer).
  - A command's exit codes, which each command's record sets.
  - A file a command writes, whose format is decided apart.

### 2. The contract is the keys, never the prose

- **Every key.** Each key a command prints in a release is one a caller may rely on, documented or not, with its meaning, the type of its value included. The command's author cannot see which keys a caller outside the repository reads.
- **Every set of values.** Where the contract lists the values a key may take, such as an outcome or a state, those values are the key's *set*, and each value's meaning is in the contract.
- **The version,** where the document carries one of its own.
- **Not prose.** A value written for people, such as a reason, a label or a message, is in the contract by its key and its purpose, never by its words, which may change in any release. The order of the keys is not in the contract, and neither is the human view.
- **Not where it is printed.** What a document holds is the same on a terminal of any width, with colour or without, and in a pipe. ADR-024 point 4 pins that for the process status document.

### 3. A caller reads by key, and never takes what it does not know for what it knows

- **By key.** A caller finds what it needs by its key. It decides on keys and on the values of their sets, never on a sentence for people, the order of the keys or the human view. It may show a sentence to people.
- **A key it does not read,** it ignores.
- **A value it does not know** it reads as the contract says for that set. Where the contract says nothing, it reads the value as *could not tell*: it learns nothing from it, and what rests on it stops or says that it could not check. It never reads the value as one it knows.
- **A version it does not know** it refuses. It reads nothing from the document, and says which version it found.
- **A run that gives no document** tells it nothing, and it never reads that as an answer.

### 4. What breaks a caller, and what does not

- **Added: no break.** A key added, or a value added to a set, breaks no caller, which reads it as point 3 says. It raises no version, and is no breaking change.
- **Gone or changed: a break.** A key that goes or changes its meaning, and a value of a set that goes or changes its meaning, each break a caller that relied on it.
  - **Declared.** It is a breaking change of the component that ships the command, and its changeset says so, under the project's bump policy ([PRJ-002](../../../.pkit/decisions/project/PRJ-002-version-bump-policy.md)).
  - **The version rises** in the same change, where the document carries one of its own, and for no other change.
- **A meaning may change in place** only as such a break. Its author may instead add a key for the new meaning, which breaks nothing until the old key goes.

### 5. A key or a value that went never comes back with another meaning

A key a document held never names anything else in that document later, at any version. A value a set held never means anything else in that set. Either may come back with the meaning it had.

An addition breaks no caller only because no caller knows the key yet. A key that went is known to each caller written while it stood, in its code, its configuration or the documents it kept. Brought back with another meaning, it would pass as an addition, so no version would rise and no break would be declared. Such a caller would read the new meaning as the old one, with nothing to tell it otherwise. A new key for that meaning is an addition, which breaks no caller, so a reused key saves no caller anything.

### 6. Where each contract is stated

- **Where its command is documented:** the CLI reference for a backbone command, and the capability's README for a capability's command. It names each key with its meaning, each set with its values, the reading of a value a caller does not know where that is not could not tell, and the document's version where it has one.
- **In a record:** a record that decides a document decides what the document holds. For how the document stays stable, it cites this record rather than state a rule of its own.

## Rationale

**Why every key, documented or not.** A caller reads what it sees in the document, not only what the reference names. The author of a command cannot see which keys a caller outside the repository reads, so a key the author judged unused may be one a pipeline decides on. Counting every key costs the author a declared break for each key removed. Counting only the keys the author knows to be read would break callers the author cannot see, without a word.

**Why prose stays out.** A sentence is written for its readers and reworded for them, in any release, by an edit nobody counts as a change of contract. A caller that matched it would break on such an edit. So each fact a caller needs has a key and a value of its own, as `outcome` sits beside `why` in a data point's document.

**Why an addition is free.** Commands grow. If each key added broke a caller, every caller would have to move with every release of the component it reads, and a capability that runs on a range of backbones could read none of them for long. A caller that ignores the keys it does not read, and never reads a value it does not know as one it knows, lets the document grow under it. The cost falls on the caller, which must know what a value it does not know means to it. Could not tell is the default because it fails safe: what rests on the answer stops or says that it could not check, as a check that gives no answer never passes (ADR-081 point 6).

**Why a value a caller does not know is never read as one it knows.** A value added may mean anything its author needed. Read as a known value, it is a guess that fails silently. An outcome read as resolved draws findings from a set that may be partial, and a state read as taken takes a filler's silence for an answer.

**Why a break is declared twice.** The changeset tells the people who upgrade the component that a caller may break. The document's version tells a caller at run time, where it may meet a component of another version than the one it was written for, as a capability meets a backbone within its range. Since the version rises only for a break, a caller that knows a version reads every later document at that version, whatever keys it gained.

**Why a key is never reused.** Point 5 gives the reason. A version cannot help there: it rises with a break, and a key brought back would come as an addition. Even declared as a break, the return breaks each caller that still holds the key, silently where a caller reads no version, while a new key breaks none. Rules' ids and records' points are kept for good for the same reason, since whatever names them keeps them as data ([COR-051](../../../.pkit/decisions/core/COR-051-rule-sets.md) point 3, [COR-058](../../../.pkit/decisions/core/COR-058-record-points.md) point 3).

**Why a meaning may still change in place.** A key whose meaning must change breaks the callers that read it either way, once the old meaning goes. A change in place declares the break in the change that makes it, so a caller that reads the version, and a person who reads the changeset, learn of it. The landing check's record and the CLI reference already allow it as a break.

**Why an ADR, not a convention entry.** The rule must bind where a document's contract is decided and stated, in records and references, before any code prints the document. The conventions corpus binds the code, read by the producer and the code-review panel, and holds coding conventions only (PRJ-013 point 4). A convention that later work builds on starts with its record anyway ([COR-065](../../../.pkit/decisions/core/COR-065-records-and-projection.md) point 3). So this record holds the rule, and the corpus points to it for the code.

**Why not a core record yet.** By COR-025's first test, a component authored elsewhere that reads a backbone document needs point 3, and one whose document other components read needs the rest. This record decides for the components project-kit ships, as ADR-084 point 8 did for its recorder. The CLI reference reaches every project that installs the methodology, and carries the contract to a component authored elsewhere. Whether every component of every project owes the rule is a core question, which this record leaves open.

### Alternatives considered

- **A convention entry in the corpus, with no record.** Rejected: a convention starts with its record (COR-065 point 3), and the corpus binds only the code.
- **A PRJ record, its rule stated in the corpus.** Rejected: an interface between components is architecture (COR-025, "Distinct from PRJ"), and the authors of the records that decide each document do not read the corpus.
- **Each contract keeps its own rule.** Rejected: five statements already differ on reuse and on values a caller does not know, and the author of a new document finds none of them by looking.
- **A version raised for every change, additions included.** Rejected: each caller would refuse each release for a key it never reads. The landing check's record and the CLI reference already rule it out.
- **Each document carries a version of its own, as part of the rule.** Not taken: many documents carry none, and the component's version marks a break for a caller that pins it. Whether a document needs a version of its own is left to the record that decides the document.
- **A key may come back with another meaning, declared as a break.** Rejected: a new key gives the same meaning as an addition, which breaks no caller (point 5).
- **A key never changes its meaning in place, so a new meaning always takes a new key.** Not taken: it would refine each contract that allows the change as a break, and it spares only a caller that reads neither the version nor the changeset. A later record can take it.
- **A set marked closed, whose added value is a break.** Not taken: each set listed so far has a reading for a value a caller does not know, and one rule for every set leaves a caller nothing to look up.
- **A core record now.** Not taken, as "Why not a core record yet" says.

## Implications

- **One accepted record is edited:** [project-management:DEC-054-use-case-validation] point 3 reads a filler `state` it does not know as it reads `inert`, so the point is at most partly checked, never judged in full on a state it cannot place. Its reading of an `outcome` or a version it does not know already agrees. In point 3:
  - the "Partly checked" bullet's "`resolved`, with a filler whose state is `inert`." becomes "`resolved`, with a filler whose state is `inert` or one this capability does not know (refinement per [pkit:ADR-097])."
  - that bullet's last sub-bullet, "Under `single` with no default, this state arises only where", becomes "Under `single` with no default, an inert filler makes this state only where".
  - the "Empty and has entries" bullet's "`resolved`, with no inert filler." becomes "`resolved`, with no filler `inert` or in a state this capability does not know."
- **The other contracts agree, and stay as they are.** ADR-024 point 4, ADR-081 point 8 and ADR-084 point 2 hold under this record. ADR-081 point 8's "a key a reader relies on" reads as every key (point 2). The CLI reference's sentences on its reading documents agree too.
- **#3193's draft** agrees, and leaves out how a caller reads an outcome it does not know. Before it is accepted, its point 4 may add: "A caller reads an outcome it does not know as could not tell, never as passed." Once both records are accepted, it may cite this record in place of its own statement of the rule.
- **project-management's reading of a data point's document** reads a filler state it does not know as inert, once the edit above is made. It changes the capability's behaviour only where a backbone adds a state, and ships with a changeset of its own.
- **The CLI reference,** once this record is accepted, states the rule under "Command output conventions" for callers outside project-kit, citing this record, as ADR-084 point 8 has it carry that record's contract. Its entry for a data point's document says that its fillers' `state` may gain a value without a raise, and how a reader reads one it does not know.
- **The conventions corpus,** `tech-docs/coding-conventions.md`, points to this record for code that prints a document or reads one (PRJ-013 point 4).
- **Each capability's README** states the contract of each document of its commands that a caller keys on (point 6). Where one does not yet, the shortfall is open work for a follow-up ([COR-065](../../../.pkit/decisions/core/COR-065-records-and-projection.md) point 4).
- **Not decided here:** whether a document must carry a version of its own, and how a command's exit codes stay stable.
- **No migration, and no changeset for this record.** It changes no command. The follow-ups above that change one carry their own.
