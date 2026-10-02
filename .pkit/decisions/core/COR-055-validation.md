---
id: COR-055
title: Validation is one check that capabilities join; only a broken invariant fails it
status: proposed
date: 2026-10-02
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

Core records say that a defect "fails validation", "is a validation error" or is "reported, never an error" (COR-048, COR-050 point 12, COR-052 point 2, COR-053 points 6 and 10), and a capability's records promise the same of its own artefacts. No record says what validation is, how a capability's checks become part of it, or which findings fail it. A capability's author and a project that gates on validation both need the answer, and neither reads the architecture records of the project where the backbone is built (COR-025, the scope test).

## Decision

**In plain terms:** a project has one command that checks whether its own files are in order. Each functionality of the backbone and each installed capability adds its checks to it. Every finding says how serious it is, and the command fails only when a finding says an invariant is broken — something the project can fix in its own files.

**Validation is the project's one check of what the project can fix in its own state. The backbone's functionalities and installed capabilities join it by registering validators; every finding carries a severity from one shared set; exactly one severity fails.**

1. **What validation owns.** Validation judges the project's state against the invariants its records own. A failing finding is one the project can fix by correcting its own files (COR-050 point 12). It is not every check of state. A check that its own record keeps outside validation stays where that record puts it: the whole-repository friction check, which reports and never fails (COR-050 point 12); process health, which answers about subjects in motion and is a command of its own (COR-042); the harness requirement report (COR-047).
2. **State, not a change.** A validator answers about the project's state and takes no base named for one run; a check that compares a change with a base (COR-054 point 3) is a command of its own. A validator reads the working tree. History and settled state reach validation only through a slot whose filler declares them (COR-052 point 6), so validation's answer varies with those states and with nothing else, and its report names them in one place. The backbone keeps a run's base from reaching a validator; that a validator reads nothing else beyond the working tree is its capability's obligation, trusted as those of COR-050 point 2 are.
3. **A capability joins by naming a command.** A capability registers each validator in its package metadata by naming a command it registers there (COR-021). Validation runs that command as a query with no subject, as it runs a slot's filler (COR-052 point 6), under the limits of COR-050 point 2, and reads its findings in machine-readable form. The command stays runnable by itself.
4. **Severity is on the finding.** Each finding carries one severity from a closed set shared by every validator, the backbone's and a capability's alike; a validator cannot add one. The record that owns a check decides which of its findings takes which severity.
5. **Exactly one severity fails.** Validation fails when a finding carries the severity that marks a broken invariant, and only then. Every other severity — asking for attention, stating a fact, or marking what an owning record says is reported rather than judged — prints and never fails. A command a capability also offers by itself may keep a stricter exit.
6. **A validator that gives no answer fails.** A registered validator that cannot be run, ends abnormally, overruns its time or prints anything but its findings yields a failing finding, never a clean pass. A filler or a resolver that gives no answer inside validation follows its own record (COR-052 point 6, COR-050 point 2).

## Rationale

**Why one check.** A gate that calls one command forgets nothing registered, and "fails validation" means one thing in every record that says it.

**Why only what the project can fix.** A gate that fails on what the project cannot correct in its files — debt that was already there, the harness, a subject in motion — teaches people to bypass it. This is COR-050 point 12's reasoning, stated once for every validator.

**Why a validator names a registered command.** A capability registers what it can run in one place; that place carries the command's declared limits. A second registry would be a second place for both.

**Why severity on the finding, classified by the owning record.** The same finding must mean the same wherever it prints, and only the record that owns a check knows whether its finding breaks an invariant.

**Why exactly one fails, and why the set's names are not here.** A gate needs a rule it can state in one sentence, and a warning read heuristically from prose must not fail it. Beyond the failing severity, how many grades there are and what they are called decides nothing (COR-046); that is the reference's.

**Why no answer fails.** Silence would read as health (COR-047 point 3).

**Why core.** A capability's author writes against these rules and a project gates on them (COR-025). What that author must also know but which is no choice among alternatives — how the declaration is spelt, the form of the findings, the value of the time bound — belongs to the synced reference, not to a record.

### Alternatives considered

- **A validation command per capability.** The gate must list each, and forgets one.
- **A second registry of validator scripts.** Two places for what a capability can run.
- **Every check of state inside validation.** It would fail on what the project cannot fix.
- **Failing on warnings, or a strictness setting.** A gate would fail on a heuristic reading.
- **Severity decided by the surface that prints.** One finding, two meanings.
- **Fixing the severities' names here.** Inventory; renaming one changes no decision.
- **Validators declaring their own reads beyond the working tree.** Two places to report what an answer depends on.
- **Skipping a validator that gives no answer.** A clean pass nobody earned.
- **Leaving this in the architecture records of the project where the backbone is built.** Those do not propagate.

## Implications

- The package-metadata reference names the registration block, the declaration and the form of the findings; the command reference names the severities and the members with their order. None is this record's.
- A capability whose records say "validation fails" on a defect registers a validator that raises it at the failing severity.
- COR-052 point 6 names the validator as the third kind of query.
- Nothing migrates: the behaviour has shipped.
