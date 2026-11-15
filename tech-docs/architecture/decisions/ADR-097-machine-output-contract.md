---
id: ADR-097
title: A command's machine-readable output keeps its keys for its callers, each with one meaning for good
status: proposed
date: 2026-11-15
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** a command that prints a document for a program to read, as `--json` does, makes a contract with each caller that reads it. The contract is the document's own keys, what each means, and the values a key may take where the document lists them. A sentence written for people is not in it. Nor is a key that is data, such as a path, or a payload the document carries for another owner. A key or a value added misleads no caller: a caller ignores a key it does not read, and reads a value it does not know as *could not tell*, never as one it knows. A key or a value that goes breaks callers, so it is a declared breaking change of its component. A key or a value means one thing for good: a new meaning takes a new key, never an old one, in place or after it went.

The rule binds every command project-kit ships. Five contracts each stated part of it, and differed in what they left out. One accepted record reads a value it does not know as one it knows, and another lets a key change its meaning in place. This record refines both. Whether every component of every project owes the rule is raised for a core record.

**Why an ADR.** The documents commands print are how project-kit's components reach each other ([ADR-057](ADR-057-backbone-engines-and-command-limits.md) point 1). An interface between components is what the project built, which is an architecture record's question ([COR-025](../../../.pkit/decisions/core/COR-025-adr-decision-space.md), "Distinct from PRJ"). Only part of the rule binds code. The rest binds the records and references that decide each document, and the changesets that ship a break. The rule spans the backbone and several capabilities, so it is no one capability's record.

## Context

**The callers.** A capability's script never imports the backbone. It reaches the backbone's engines through their machine-readable reading commands (ADR-057 point 1). Agents, a project's pipeline and a person's own tooling read the same documents, and capabilities' commands print documents of their own, such as project-management's pre-check report. Each caller keys on the document: it finds what it needs by a key and decides on the value there.

**Each contract states its own rule.**
- **The process status document** ([ADR-024](ADR-024-cli-prose-wrapping.md) point 4) is the surface a script keys on, never the human narrative. No presentation choice reaches it: it is byte-identical on a terminal of any width and in a pipe.
- **The landing check's document** ([ADR-081](ADR-081-landing-check.md) point 8) has a version of its own, raised when a key a reader relies on changes its meaning or goes, never for a key added.
- **The configuration recorder's document** ([ADR-084](ADR-084-capability-config-contract.md) point 2) is what a capability's script decides on, and carries a schema version. The recorder is decided and not yet built, so its document will first be printed under this record.
- **A data point's document,** as project-management reads it ([project-management:DEC-054-use-case-validation] point 3): a caller decides on its `outcome` and its fillers' `state`, never on the sentence in `why`. An outcome or a version it does not know reads as could not check. A filler's state is read as `inert` or not, so a state it does not know reads as one that answered. The manifest reference gives every consumer the same advice: check that no filler's state is `inert`.
- **Pre-check's report,** in the record that issue #3193 drafts, which is proposed and binds nothing: each check has a key that stays whatever its outcome or its wording. A key added breaks no caller. A key that goes or comes to name another check, and a changed outcome value, break one. A key is never reused.
- **The CLI reference** states the version rule of the friction checks' reading documents and of a data point's document, in ADR-081's words. A value added to a listed set raises no version where the reference names how a reader reads one it does not know, as it does for an outcome, a finding kind and an artefact state. It names no such reading for a filler's state, the cross-repository guard's verdicts or the default branch's sources. It calls the outcomes "a closed set", though they may grow.

**Where they differ.** They agree on what they share, and differ in what each leaves out. Only #3193's draft says that a key is never reused, yet it, ADR-081 and the CLI reference each let a key change its meaning in place. Only DEC-054 and the CLI reference say how a caller reads a value it does not know, and the CLI reference says it for some sets and not others. None says which keys are in the contract: one no caller is known to read, one that is data, or one whose reading an added key changes. The author of a new document finds the rule only by reading whichever of these they happen to know. The architect's review of #3193's draft found the recurrence ([COR-007](../../../.pkit/decisions/core/COR-007-pattern-extraction.md)), and issue #3250 asked for one rule.

## Decision

**A command's machine-readable output is a contract with each caller that reads it: its own keys, what each means, and the values of its sets, never its prose. A key or a value added misleads no caller. One that goes breaks callers, and is a breaking change of its component. A key or a value means one thing for good.**

### 1. What the rule covers

- **A command's document.** The rule covers each document a command prints for a program to read, on the command's request for machine-readable output. It covers every command project-kit ships: the backbone's, each capability's and each adapter's. This record calls that output the command's *document*. A document may have several *forms*, such as the one a run with no answer prints, or one an option selects.
- **Its callers** are whatever reads it: another component's script, an agent, a project's pipeline or a person's own tooling. Point 3 binds each caller project-kit ships. A caller outside project-kit learns the contract where the command is documented (point 6).
- **Not covered:**
  - What a command prints for the backbone as a query's answer, such as a data point's value or an anchor resolver's answer. Its shape and its version are the core's ([COR-052](../../../.pkit/decisions/core/COR-052-slots.md) point 5 for a data point's value, [COR-050](../../../.pkit/decisions/core/COR-050-anchors-and-friction.md) point 2 for a resolver's answer).
  - A document whose shape a protocol outside project-kit sets, such as the decision a harness's permission hook returns. The protocol is its contract.
  - A verdict an agent writes for a program to read, whose form its own record sets ([project-management:DEC-028-agent-as-approver-paths]). An agent is no command.
  - A command's exit codes, which each command's record sets, and a file a command writes, whose format is decided apart.

### 2. The contract is the document's own keys, never its prose

- **Its own keys.** A key is the document's own when the command names it whatever the project holds. Each own key a final release prints is in the contract, documented or not, with its meaning. A key's meaning includes the type of its value, when that value is null, and when, and in which forms, the key is present.
- **A key that is data is a value.** In a mapping keyed by what the project holds, such as paths, ids, or the names of capabilities or types, the keys are values. They come and go with what they name. The mapping's own key, and the fields of each entry, are own keys.
- **A payload keeps its owner's contract.** A document may carry a value whose shape another owner sets, such as a data point's value under its definer's schema (COR-052 point 5), or an artefact's front matter. The contract holds the key that carries the payload, and that the payload is carried as its owner gave it. The keys inside it are its owner's.
- **Every set of values.** Where the contract lists the values a key may take, such as an outcome or a state, those values are the key's *set*, and each value's meaning is in the contract. Every set may gain a value (point 4).
- **The version,** where the document carries one of its own.
- **Order and framing, where stated.** A list's order is in the contract where the reference states one, or where another key indexes the list. The order of a mapping's keys, and how the document is framed on its stream, such as one line of JSON or several documents one per line, are in it where the reference states them. A caller still finds a key by its name, never by its place.
- **Not prose.** A value written for people, such as a reason, a label or a message, is in the contract by its key and its purpose, never by its words, which may change in any release. The human view is not in it either.
- **Not where it is printed.** What a document holds is the same on a terminal of any width, with colour or without, and in a pipe, as ADR-024 point 4 pins for the process status document.
- **From a final release.** A key or a value enters the contract when a final release first prints it. A release candidate previews what a release would ship ([PRJ-016](../../../.pkit/decisions/project/PRJ-016-candidates-hold-no-release.md) point 3), so a key that a later candidate or the final release drops or changes breaks nothing.

### 3. A caller reads by key, and never takes what it does not know for what it knows

- **By key.** A caller finds what it needs by its key. It decides on keys and on the values of their sets, never on a sentence for people, the place of a key or the human view. It may show a sentence to people.
- **A key it does not read,** it ignores.
- **A key it needs and does not find** tells it nothing. It reads that as *could not tell*, never as a default such as zero, false or empty.
- **A value it does not know** it reads as the contract says for that set. Where the contract says nothing, it reads the value as could not tell: it learns nothing from it, and what rests on it stops or says that it could not check. It never reads the value as one it knows.
- **A version it does not know** it refuses. It reads nothing from the document, and says which version it found.
- **A run that gives no document** tells it nothing, and it never reads that as an answer.

### 4. What is a breaking change, and what is not

- **Added: no breaking change.** A key added, or a value added to a set, misleads no caller that reads as point 3 says. It raises no version.
  - **Only where the rest stands.** An addition that changes how an existing key reads changes that key's meaning, which point 5 rules out. A key that qualifies another, such as one that says a list is partial, is such an addition. One that leaves an existing key out of a form it was in is that key going (below).
  - **A set that named no reading.** A set whose contract named no reading for a value a caller does not know, before the CLI reference states this rule, gains no value until a release after the one that states it.
- **Gone: a breaking change.** A key that goes, from the document or from a form it was in, and a value of a set that goes, each break a caller that relied on it.
  - **Declared.** It is a breaking change of the component that ships the command, and its changeset says so, at the `major` segment ([PRJ-002](../../../.pkit/decisions/project/PRJ-002-version-bump-policy.md) D2).
  - **The version rises** in the same change, where the document carries one of its own, and for no other change.
  - **No migration,** since a document is no installed state. Where a project's installed state names what goes, COR-010's test decides, as for any change ([COR-010](../../../.pkit/decisions/core/COR-010-resource-lifecycle.md), "Migrations are mandatory on adopter-breaking surface changes").
- **A fix changes no meaning.** A change that makes a key give what its contract states, where it gave something else, is a fix.

### 5. A key or a value means one thing for good

- **Never in place.** A key's meaning never changes, and neither does a value's in its set. A new meaning takes a new key, or a new value. The old one may stay beside it for as long as its callers need, and its going is then a break (point 4).
- **Never by return.** A key that went never comes back to name anything else in that document, at any version. A value that went never comes back to mean anything else in its set. Either may come back with the meaning it had.

### 6. Where each contract is stated

- **Where its command is documented:** the CLI reference for a backbone command, and the README of the capability or adapter for its own. For each document printed for a program, it names each own key with its meaning, each set with its values, the reading of a value a caller does not know where that is not could not tell, the order and framing a caller may rely on, and the document's version where it has one.
- **The rule itself** is stated in the CLI reference, for every command project-kit ships, a capability's and an adapter's included. The CLI reference reaches every project that installs the methodology, and this record does not (COR-025, "Propagation isolation").
- **In a record:** a record that decides a document decides what the document holds. For how the document stays stable, it cites this record and the CLI reference's statement, rather than state a rule of its own.

### 7. What checks it

- **A test for each document** pins, from the output the command prints, its own keys, the values of its sets, and each key and value that went. A change that removes one, or brings one back, fails the test until the same change updates it, beside the changeset that declares the break.
- **A test for each caller** project-kit ships gives it a document with a key it does not know, a value it does not know, a version it does not know, a key it needs left out, and no document at all. Each must read as point 3 says.
- **A meaning is review's.** No test sees that a key came to mean something else, so the reviewer of the change judges it.
- **Until the tests exist,** review alone checks. Building them is a follow-up (Implications).

### 8. The rule for components authored elsewhere is raised for a core record

- **What is universal here.** By COR-025's first test, a component authored elsewhere that reads a backbone document needs point 3, and one whose document other components read needs points 2, 4 and 5. A core record decides such rules.
- **Adopted for what project-kit ships.** This record binds the components project-kit ships, and raises the rest for a core decision, as ADR-084 point 8 did with its recorder's rules.
- **The carrier until then** is the CLI reference's statement of the rule (point 6).
- **When to revisit:** when that core decision is made, or sooner, when a component project-kit ships first reads a document that a component authored elsewhere prints. That caller's safety then rests on a rule this record cannot bind.

## Rationale

**Why the document's own keys, documented or not.** A caller reads what it sees in the document, not only what the reference names. The author cannot see which keys a caller outside the repository reads, so a key the author judged unused may be one a pipeline decides on. Counting only the documented keys would break such callers without a word. Counting every own key costs the author a declared break for each key removed: for a backbone document, a backbone `major`.

**Why a key that is data, and a payload, stay out.** A path or an id that keys a mapping comes and goes with the project's content. Held to the contract, deleting a file would break a caller, and a deleted path could never return. A payload's keys are set by its owner, such as a data point's definer, whose own contract governs them (COR-052 point 5). The command only carries them.

**Why prose stays out.** A sentence is written for its readers and reworded for them, in any release, by an edit nobody counts as a change of contract. A caller that matched it would break on such an edit. So each fact a caller needs has a key and a value of its own, as `outcome` sits beside `why` in a data point's document.

**Why an addition misleads no caller.** Commands grow. If each key added broke a caller, every caller would have to move with every release of the component it reads, and a capability that runs on a range of backbones could read none of them for long. A caller that ignores the keys it does not read, and never reads a value it does not know as one it knows, lets the document grow under it.
- **What it costs.** An addition may still stop a caller: a pipeline that meets a value it does not know says it could not tell, and goes red. The cost falls safe, as a check that gives no answer never passes (ADR-081 point 6).
- **Why only where the rest stands.** A caller that predates a key reads no key that qualifies another. It reads the other key as it always did, so a list marked partial, or a form that leaves a total out, has it take part of an answer for the whole. The CLI reference warns of this in the process health report's interpretation form. So whether a key is present, and when its value is null, are part of its meaning.

**Why a value a caller does not know is never read as one it knows.** A value added may mean anything its author needed. Read as a known value, it is a guess that fails silently. An outcome read as resolved draws findings from a set that may be partial, and a state read as taken takes a filler's silence for an answer.

**Why every set may grow.** A set that may never grow makes each new value a break for every caller, though each can read it safely as could not tell. The cost of a set that grows falls on callers that read it as complete. Within project-kit, project-management's reading of a filler's state is one, and is refined below. A caller outside project-kit learns that a set may grow from the release that states this rule, so a set whose contract named no reading waits one release for its first new value.

**Why a key that goes is declared.** The changeset tells the people who upgrade the component that a caller may break. The document's version tells a caller at run time, where the document has one. Neither reaches every caller. Each release widens each shipped capability's range on the backbone to cover the backbone it ships (PRJ-002 D4), and agents, pipelines and a person's own tooling pin nothing. So the safety at run time rests on point 3: a caller that needs a key that went finds it missing, and reads could not tell.

**Why a key means one thing for good.** A key whose meaning changed reads, to a caller written before the change, as the meaning it knew. Nothing in the document tells it otherwise, unless the document carries a version the caller checks, and many carry none. A key that goes instead, beside a new key for the new meaning, is met as missing, which point 3 reads as could not tell. The old key may stay while its callers move, so no caller breaks at once. A key brought back with another meaning harms the same caller in the same way, and would pass as an addition besides. A record's point may be amended under its id ([COR-058](../../../.pkit/decisions/core/COR-058-record-points.md) point 3), since the friction checks flag each artefact anchored on it (COR-050). A document's caller has no such check, so a key keeps its meaning as a rule's id keeps its rule ([COR-051](../../../.pkit/decisions/core/COR-051-rule-sets.md) point 3).

**Why an ADR, not a convention entry.** How code prints a document, and how it reads one, are coding conventions, and the corpus may point to a convention a record holds ([PRJ-013](../../../.pkit/decisions/project/PRJ-013-coding-conventions.md) point 4). The rest of the rule binds what no code holds: the records and references that decide a document before any code prints it, and the changesets that ship a break. The corpus holds coding conventions only, so it cannot hold that part. A convention that later work builds on starts with its record anyway ([COR-065](../../../.pkit/decisions/core/COR-065-records-and-projection.md) point 3). So this record holds the rule, and the corpus points to it for the code.

**Why raised for a core record, rather than decided there now or left open.** By COR-025's first test, points 2 to 5 bind any component's author, and scope decides the carrier. A core record now would bind every adopter's components on a rule project-kit has not yet checked on its own, since the tests of point 7 are not built. Leaving the question open would leave the rule's reach unstated: an author elsewhere reads the rule in the CLI reference, cannot tell whether it binds their own component, and finds nothing that says when that is decided. Raising it, as ADR-084 point 8 did, binds what project-kit ships, carries the rule to everyone through the CLI reference, and names when to revisit.

### Alternatives considered

- **A convention entry in the corpus, with no record.** Rejected: a convention starts with its record (COR-065 point 3), and the corpus holds coding conventions only, where most of the rule binds records, references and changesets.
- **A PRJ record, its rule stated in the corpus.** Rejected: an interface between components is architecture (COR-025, "Distinct from PRJ"), and the authors of the records that decide each document do not read the corpus.
- **This record, with its rule in a rule set scoped over the CLI reference, the READMEs and the code that prints documents.** Not taken: the rule-set reviewer would be drawn onto each change to the CLI reference, which most backbone changes touch, and onto each change to that code, the cost PRJ-013 weighed against a rule set for conventions. Most of what it would judge, a key or a value that went, point 7's test checks mechanically. A meaning, which no test sees, is judged by the change's reviewer either way.
- **Each contract keeps its own rule.** Rejected: five statements already differ on reuse and on values a caller does not know, and the author of a new document finds none of them by looking.
- **A version raised for every change, additions included.** Rejected: each caller would refuse each release for a key it never reads. The landing check's record and the CLI reference already rule it out.
- **Any change of meaning, in place or by return, as a declared break.** Rejected. It is one rule, and it keeps precedent: ADR-081 point 8, the CLI reference and #3193's draft allow a change in place as a break, and the friction checks' `since` document took one, at its version 2. Its cost is each caller that reads no version: it reads the new meaning as the old, silently, and many documents carry no version.
- **A meaning changed in place as a declared break, while a key that went never comes back with another.** Rejected: a change in place and a return harm the same caller in the same way, so allowing one and ruling out the other rests on precedent alone.
- **A set marked closed, so that a value added to it is a break, as the filler states could stay.** Not taken. It would spare DEC-054's refinement and the manifest reference's edit. Its cost is a `major` for each value such a set ever gains, or a new key for each under point 5, and a mark, open or closed, that each caller looks up for each set.
- **The first value added to a set that named no reading, declared as a break.** Not taken: one release's notice tells the same callers, where this costs a `major` for each such set.
- **A version on every document, as part of the rule.** Not taken: under point 5, every break is a key or a value that goes, which a caller meets through point 3 with no version. Many documents carry none, and whether one needs it is left to the record that decides it.
- **A version on each document first printed after this record.** Not taken, for the same reason: once no key changes its meaning, a version spares a caller nothing that point 3 does not. It would also split the documents into two kinds by their age.
- **A schema for each document, with the keys that went, tested against its output.** Not taken as the rule's form: point 7's test pins the same keys at less cost. A document's record may give it a schema, which can serve as that test, and gives a caller outside project-kit an artefact to check against.
- **A marked place for keys outside the contract,** such as keys for debugging. Not taken: no document needs one yet, and a caller that can see a key may read it whatever its mark. The first document that needs one brings it, through a change to this record.
- **Exit codes under the same rule.** Not taken: a command's record sets its exit codes, and several make them the whole contract of a gate ([project-management:DEC-017-prerequisites-bootstrap-migrate-discipline]). Issue #3250 asks about machine-readable output. How exit codes stay stable is a question of its own.
- **A core record now, or the core question left open.** Not taken, as "Why raised for a core record" says.

## Implications

- **Two accepted records are refined in place,** each edit made once this record is accepted.
  - **[project-management:DEC-054-use-case-validation]** reads a point as wholly answered only where every filler is `taken` or `passed over`, so a state it does not know makes the point at most partly checked. Its reading of an `outcome` or a version it does not know already agrees. Each edit carries the pointer "(refinement per [pkit:ADR-097])" on the sentence it rewrites:
    - **point 1, the inert policy's second condition:** "no finding is drawn from an id the point lacks unless the point resolved with every filler `taken` or `passed over` (point 3; refinement per [pkit:ADR-097]);" in place of "no finding is drawn from an id the point lacks unless the point resolved with no inert filler (point 3);".
    - **point 3, the "Partly checked" bullet:** "**Partly checked**: `resolved`, with a filler whose state is neither `taken` nor `passed over`, such as `inert` or a state this capability does not know (refinement per [pkit:ADR-097]). The point answered, and a filler meant to answer may not have." in place of "**Partly checked**: `resolved`, with a filler whose state is `inert`. The point answered without a filler that was meant to answer."
    - **that bullet's last sub-bullet:** "Under `single` with no default, an inert filler makes this state only where" in place of "Under `single` with no default, this state arises only where", the rest standing.
    - **point 3, the "Empty and has entries" bullet:** "`resolved`, with every filler `taken` or `passed over`." in place of "`resolved`, with no inert filler.", the rest standing.
    - **point 5, the "Partly checked" bullet:** "The plan says that the set may be incomplete, and which filler did not answer or is in a state the agent does not know (refinement per [pkit:ADR-097])." in place of "The plan says that the set may be incomplete, and which filler did not answer."
  - **ADR-081 point 8, the "One document of its own" bullet:** "Its version is its own, raised when one of its own keys, or a value of one of its sets, goes, never for one added, and no key or value comes to mean anything else (refinement per ADR-097)." in place of "Its version is its own, raised when a key a reader relies on changes its meaning or goes, never for a key added." Every own key counts as one a reader relies on (point 2).
- **The other contracts agree, and stand.** ADR-024 point 4 pins for one document what point 2 asks of every document. ADR-084 point 2 asks a version of the recorder's document, which will first be printed under this record.
- **#3193's draft,** before it is accepted, may align its point 4: a check that asks something else takes a new key, never an old one, and "A caller reads an outcome it does not know as could not tell, never as passed." Once both records are accepted, it may cite this record and the CLI reference's statement in place of its own.
- **Documents that follow,** once this record is accepted:
  - **The CLI reference** states the rule under "Command output conventions", for every command project-kit ships, citing this record (point 6). The change carries a backbone changeset: a convention adopters are expected to follow is a surface change (PRJ-002). Its sentences that speak to the rule change to agree:
    - the friction checks' reading documents: "It is raised when one of the document's own keys goes, never for a key added, and no key comes to mean anything else." in place of "It is raised when a key a reader relies on changes its meaning or goes, never for a key added."
    - a data point's document: "one value from the set below" in place of "one value from the closed set below"; "One value from the set below" in place of "One value from a closed set"; and "a value removed does, and no value is given another meaning" in place of "a value removed or given another meaning does".
    - the same document's fillers: a sentence that `state` may gain a value, and that a reader reads one it does not know as could not tell what that filler gave, never as `taken` or `passed over`.
  - **The manifest reference,** "Reading one point from a script": "So a consumer that only reports checks that every `fillers[].state` is `taken` or `passed over` before it draws a finding from an entry's absence." in place of "So a consumer that only reports checks that no `fillers[].state` is `inert` before it draws a finding from an entry's absence."; and "as one value from a listed set" in place of "as one value from a closed set".
  - **The conventions corpus,** `tech-docs/coding-conventions.md`, points to this record for code that prints a document or reads one (PRJ-013 point 4).
  - **Each capability's and adapter's README** states the contract of each document its commands print for a program (point 6). Where one does not yet, the shortfall is open work for a follow-up (COR-065 point 4).
- **Follow-ups that change code,** each with a changeset of its own:
  - **project-management's reading of a data point's document** reads a filler state other than `taken` and `passed over` as it reads `inert`, once DEC-054 is refined. It changes what the capability does only where a backbone adds a state.
  - **The tests of point 7,** for each document and each caller project-kit ships.
- **A core decision is raised** for points 2 to 5, for components authored elsewhere (point 8), by an issue filed once this record is accepted.
- **Not decided here:** whether a document must carry a version of its own, and how a command's exit codes stay stable.
- **No migration, and no changeset for this record.** It changes no command, and an ADR reaches no project that installs the methodology. The edits to DEC-054 carry a project-management changeset at `none`, since they record what a later change to its code ships (PRJ-002). The follow-ups that change a command carry their own.
