---
id: COR-032
title: A process may track many keyed subjects under one definition
status: accepted
date: 2026-06-21
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

The process substrate ([COR-031](COR-031-process-substrate.md)) shipped `singleton`-only — one journey per process — and *named* `keyed` (many subjects under one definition) as a deferred extension point, to be shipped by its own decision when a real binding demands it (COR-031 P5). A binding now demands it: the issue lifecycle tracks many issues, each at its own position. This record ships the `keyed` slot — minimally.

## Decision

**In plain terms:** a process can track many subjects (e.g. one per issue), each at its own position, by telling the engine *which* subject to act on — without the engine ever enumerating them.

A process declares `subject.cardinality: singleton | keyed`. A **keyed** process tracks many subjects under one definition; the engine operates **per a supplied subject identifier** — it resolves that subject's position, validates and executes its moves, and writes its journal, threading the identifier through every predicate it runs. The identifier is **required** for a keyed process (no singleton default).

- **No enumeration.** The engine never lists a keyed process's subjects; it only ever acts on the one it is given. Enumerating subjects, and cascading across a containment tree, are *breadth* (altitude-2) and **remain deferred** — a binding that needs them carries them capability-local.
- **`key` is descriptive.** A keyed subject declares a `key` naming what identifies a unit (e.g. an issue number). The engine does not interpret it; subject identifiers must be safe to use in the per-subject journal path.
- **Detection stays orthogonal.** A keyed subject's position is resolved the same way a singleton's is (inferred, per COR-031); cardinality and detection mode are independent axes.

## Rationale

This is name-broad / ship-narrow (COR-016) applied as COR-031 P5 intended: un-defer a named slot when a real binding needs it (COR-007's recurrence test), not speculatively. The minimal `keyed` is small — "operate per the supplied subject" plus the cardinality value and the descriptive `key`; the engine already resolves position and journals per-subject, so the change is threading the identifier rather than a new mechanism. Excluding enumeration and cross-subject cascade is what keeps `keyed` on the ship-narrow line and the substrate content-free: a process that tracks many independent subjects is a different, smaller thing than one that reasons across them. The latter (breadth) ships when a binding genuinely needs it.

### Alternatives considered

- **Ship enumeration / cross-subject cascade with `keyed`.** Rejected — that is altitude-2 breadth; bundling it would over-ship past the demanding binding's need (the COR-007 failure) and pull domain structure (a containment tree) into the content-free engine.
- **Model each subject as its own singleton process.** Rejected — it is one process over many subjects; collapsing that into many singletons loses the shared definition and the single source of position truth.

## Implications

- The shape contract widens: `subject.cardinality` admits `keyed`, plus an optional descriptive `key`. The engine threads the supplied subject identifier through the predicate runner and requires it for keyed processes. This is a surface change; the affected backbone component's version bumps per the project's version policy.
- The **first keyed binding** carries its own conforming instance (and any migration) in its own capability decision — it is the binding that drives this slot, not pre-authorised here.
- **Future keyed bindings** cite this record. Cross-subject **enumeration and cascade remain deferred** breadth; they each become real, with their own decision, when a binding demands them.
- Relationship to records: implements the `keyed` slot named in COR-031 (P5); applies name-broad / ship-narrow (COR-016) and extract-on-recurrence (COR-007).
