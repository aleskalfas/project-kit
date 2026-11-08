---
id: COR-071
title: The deploy names each suspension it applies
status: proposed
date: 2026-11-08
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a project's own file can take the name of a skill or an agent definition that core or a capability ships, and so replace it in the harness. Each time the adapter's deploy runs, it names both files: the shipped one it leaves out, and the project's one that takes its name. Its report ends with how many it left out. The naming is a report, not a warning, and validation reports no suspension.

## Context

Skills and agent definitions are runtime instructions, so they are suspendable ([COR-003](COR-003-artifact-mechanisms.md)). A project's file that takes a shipped one's name replaces it, by a precedence rule each type documents. A suspension is a stronger commitment than an extension, and a project needs to know that it overrides rather than adds ([COR-001](COR-001-content-mechanisms.md)). The adapter's deploy puts them where its harness reads them, and chooses one source for each name ([COR-013](COR-013-agent-architecture.md)).

A suspension can start without anyone choosing it:

- **A new file of the project's:** a project writes a skill under a name it did not know a shipped skill already holds.
- **A new shipped file:** a later release ships a skill or an agent definition under a name the project already uses.

Either way the shipped file reaches no session, and none of its later updates does. A capability's install and upgrade ask a person at a new collision with the project's artefacts ([COR-017](COR-017-capability-pattern.md); [COR-059](COR-059-version-transition.md) point 7). Nothing names a suspension that holds. The deploy reports the file it deploys as it reports any other.

A shipped file is kept out of the harness in a second way too. A file the deploy did not write can stand at the place where the deploy would put a shipped name, such as one a project kept there by hand before it adopted the methodology. That place is a deployment path, owned by neither party (COR-003), so the file is no suspension. The deploy leaves it in place, and the shipped file is not deployed.

Two steps could name these: the deploy, which applies the precedence, and validation, which checks the project's state against its invariants ([COR-055](COR-055-validation.md)).

## Decision

**Each run of a deploy that applies a suspendable type's precedence names each suspension it applies: the shipped file it leaves out, and the project's file that takes its name. It names a shipped file that a file it did not write keeps out in the same way. The naming is a report, not a warning, and validation reports no suspension.**

### 1. The deploy names each suspension, on each run

- **What it names:** where a project's file of a suspendable type takes the name of one that core's files or an installed capability's files hold, the deploy names the shipped file it leaves out and the project's file. Where several shipped files carry the name, it names each.
- **A file the run skips:** a project's file that this run skips, for a defect of its own, keeps the shipped file out all the same, so the deploy names both.
- **When:** on each run, for as long as the suspension holds, not only on the run that first applies it. So the run after a release that ships a name the project already uses names it, as does every later run.
- **The count:** the deploy's report ends with how many shipped files it left out, where it left any. A reader who reads only the end of a long run still learns of one.
- **The form:** each adapter names a suspension in the form of its own deploy's report, and its documentation gives that form ([COR-005](COR-005-bundle-pattern.md)).

### 2. A file the deploy did not write is named the same way

- **What it names:** where a file the deploy did not write stands at the place of a name that core's or an installed capability's files hold, the deploy names the shipped file it leaves out, and that file.
- **Not a suspension:** the file sits at a deployment path, not a project-owned one (COR-003). The deploy names it as it names a suspension, and the rest of this record applies to it alike.

### 3. A report, not a warning, and no finding of validation

- **A report:** a suspension is permitted (COR-003), so its naming asks for nothing to be mended. It is an ordinary line of the deploy's report, no warning, and it never fails the run.
- **No finding of validation:** validation may read the same precedence for checks of its own. A suspension takes effect in the harness only through the deploy, so the deploy is the fact's one home.
- **Ending a suspension:** the project removes or renames its file, and the next deploy deploys the shipped one.

## Rationale

**Why the deploy.** The deploy applies the precedence, so it is where a suspension takes effect. A project's new file under a shipped name changes nothing in the harness until the deploy runs, and each operation that changes what the harness loads runs it. So the run that first applies a suspension names it, to whoever started that run.

**Why on each run.** A naming given once is lost to whoever did not read that run. The deploy cannot name only a new suspension: it would have to tell one from a standing one, and it keeps no record of what it saw before. The cost is one line for each suspension in each run, and the count at the end.

**Why not a warning.** A suspension is permitted, whether or not the project chose it, and only the project can tell which. A warning asks for a mend. One that a deliberate suspension can never clear is read past, with the warnings beside it.

**Why skills and agent definitions alike.** Both are runtime instructions that a precedence rule makes suspendable, and both reach a harness through a deploy. A project told of one kind's suspensions and not the other's would read the silence as none.

**Why a file the deploy did not write is named too.** It keeps the shipped file out of the harness as surely as a suspension does, and the project meets it in the same way: a shipped name it already uses. A project that kept its own skills where the harness reads, before it adopted the methodology, meets a new shipped name there first.

**Why the installed files decide.** The deploy reads what core's and each installed capability's files hold. A shipped file the project chose to skip at a collision question was left out of the copy, and the skip is recorded where that question records it (COR-017). The deploy has nothing to name for it.

### Alternatives considered

- **Validation reports each suspension.** Rejected. As a warning, a permitted suspension never clears it. At a severity that never fails, it states again what the deploy states, from a step that does not decide what the harness loads.
- **Name a suspension only on the run that starts it.** Rejected. The deploy would need a record of what it had reported, and a run nobody read would lose the naming for good.
- **Ask a person at the deploy, as a capability's install asks.** Rejected. The deploy runs where nobody can answer, and asking there would stop that run.
- **A declaration that silences the naming of a deliberate suspension.** Rejected. One line for each suspension costs less than a declaration the project keeps and validation checks.

## Implications

- **Each adapter's deploy** that applies a suspendable type's precedence names each suspension, and each shipped file a file it did not write keeps out, in its report. One that does not is a defect of the adapter.
- **Each adapter's documentation** gives the form its deploy names them in. Each suspendable type's area README, which documents its precedence rule (COR-003), says that the deploy names a suspension, and points to that form.
- **No accepted record is edited.** This record refines, overturns and replaces none.
- **Not decided here:**
  - how the precedence between two shipped files, core's and a capability's, is named;
  - whether a transition tells a suspension it newly starts from a standing one, or asks a person before it starts one;
  - how a suspension that disables a shipped file rather than replacing it is named, where a type comes to allow one;
  - how a harness that applies the precedence itself, with no deploy, names a suspension;
  - the precedence among the providers of a hook (COR-013), which a skill or an agent definition can take by answering the hook.
