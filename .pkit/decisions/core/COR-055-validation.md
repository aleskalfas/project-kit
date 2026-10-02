---
id: COR-055
title: Validation is one check that installed components join; one severity fails it
status: proposed
date: 2026-10-02
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

Core records say that a defect in a project's files "fails validation" or is "reported, never an error" (COR-050 point 12 and COR-053 point 10 are two of several), and a capability's records promise the same of its own artefacts. No record says what validation is, how a component's checks become part of it, or which findings fail it. A capability's author and a project that gates on validation both need the answer.

## Decision

**In plain terms:** a project has one command that checks whether its own files are in order. Each functionality of the backbone and each installed component adds its checks to it. Every finding says how serious it is, and the command fails in two cases only: a finding says an invariant is broken, or a check that owed an answer gave none.

**Validation is the project's one check of its own state against the invariants its records own. The backbone's functionalities and installed components join it by registering validators; every finding carries a severity from one shared set; exactly one severity fails.**

1. **What validation owns.** Validation judges the project's state against the invariants its records own. A finding that fails it says one of two things: an invariant is broken, or a validator that owed an answer gave none (point 6). It is not every check of state. A check stays outside when failing on it would fail the project for what it cannot correct in its own files — debt that was already there, the harness, a subject in motion — or when its own record puts it elsewhere. Three examples: the whole-repository friction check, which reports and never fails (COR-050 point 12); the process engine's check of one subject against a process's declared invariants (COR-035) and process health (COR-042), which answer about subjects in motion and are commands of their own; the harness requirement report, whose truth shows only where the harness is observed and which has a surface of its own (COR-047).
2. **State, not a change.** A validator answers about the project's state and takes no base named for one run; a check that compares a change with a base (COR-054 point 3) is a command of its own. A validator reads the working tree. History and settled state reach validation only through a slot whose filler declares them (COR-052 point 6), so beyond the working tree validation's answer varies with those states and with nothing else, and the report names them (COR-052 point 7). The backbone keeps a run's base from reaching a validator; that a validator reads nothing else beyond the working tree is its component's obligation, trusted as those of COR-050 point 2 are.
3. **A component joins by naming a command.** An installed component registers each validator in its package metadata by naming a command it registers there (COR-021). Validation runs that command as a query with no subject, as it runs a slot's filler (COR-052 point 6), under the limits of COR-050 point 2, and reads its findings in machine-readable form. The command stays runnable by itself.
4. **Severity is on the finding.** Each finding carries one severity from a closed set shared by every validator, the backbone's and a component's alike; a validator cannot add one. The record that owns a check decides which of its findings takes which severity.
5. **Exactly one severity fails.** Validation fails when a finding carries the failing severity, and only then. A finding takes it when an invariant is broken or an owed answer is missing (point 6); what other records call a validation error is a finding at this severity. Every other severity — one that asks for attention, one that states a fact, one that marks what an owning record says is reported rather than judged, for example — prints and never fails. A command run by itself, outside validation, may keep a stricter exit.
6. **A validator that gives no answer fails.** A registered validator that cannot be run, ends abnormally, overruns its time or prints anything but its findings yields a failing finding, never a clean pass. No policy turns a validator's missing answer into a warning, as a slot's inert policy can for a filler; a filler or a resolver that gives no answer inside validation follows its own record (COR-052 point 6, COR-050 point 2).

## Rationale

**Why one check.** A gate that calls one command forgets nothing registered, and "fails validation", said of a project's files, means one thing in every record that says it.

**Why checks of what the project cannot fix stay outside.** A gate that fails on what the project cannot correct in its files — debt that was already there, the harness, a subject in motion — teaches people to bypass it. COR-050 point 12 reasons so for its own findings; the same reasoning decides which checks join.

**Why a validator names a registered command.** A component registers what it can run in one place; that place carries the command's declared limits. A second registry would be a second place for both.

**Why severity on the finding, classified by the owning record.** The same finding must mean the same wherever it prints, and only the record that owns a check knows whether its finding breaks an invariant.

**Why exactly one fails, and why the set's names are not here.** A gate needs a rule it can state in one sentence, and a warning read heuristically from prose must not fail it. What the severities are called decides nothing (COR-046), and beyond the failing one neither does how many there are; both are the CLI reference's.

**Why no answer fails.** Silence must not read as health: COR-047 point 3 makes it indeterminate, and this record decides the consequence. A missing answer is not always the project's to fix in a file — a validator can overrun its time — and a failure of that kind costs a re-run. A pass nobody earned costs more: the gate reports the project in order when a check never ran, and nothing prompts anyone to look.

**Why core.** A capability's author writes against these rules and a project gates on them, and neither reads the records of the project where the backbone is built (COR-025). What that author must also know but which is no choice among alternatives — how the declaration is spelt, the form of the findings, the value of the time bound — belongs to the references synced with the backbone, not to a record.

### Alternatives considered

- **A validation command per capability.** The gate must list each, and forgets one.
- **A second registry of validator scripts.** Two places for what a component can run.
- **Every check of state inside validation.** It would fail on what the project cannot fix.
- **Failing on warnings, or a strictness setting.** A gate would fail on a heuristic reading; with a setting, "fails validation" would mean something different in each project.
- **Severity decided by the surface that prints.** One finding, two meanings.
- **Fixing the severities' names here.** Inventory; renaming one changes no decision.
- **Validators declaring their own reads beyond the working tree.** Two places to report what an answer depends on.
- **Skipping a validator that gives no answer.** A clean pass nobody earned.
- **A policy per validator for a missing answer, as slots have.** A validator's findings are its whole contribution; a policy that downgraded its silence would let a check drop out with a warning.
- **Leaving the rule with the realisation's own records.** They reach neither reader.

## Implications

- The package-metadata reference names the registration block, the declaration and the form of the findings; the CLI reference names the severities and the members with their order. None is this record's.
- A capability whose records say a defect in the project's files fails validation registers a validator that raises it at the failing severity.
- COR-052 point 6 is refined to name the validator beside the filler as a query with no subject.
- Nothing migrates: the behaviour has shipped.
