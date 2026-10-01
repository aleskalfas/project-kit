---
id: COR-052
title: Components exchange knowledge through slots, without depending on each other
status: accepted
date: 2026-09-27
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

Components often need knowledge that another component, or the project itself, is better placed to provide. A documentation discipline needs to know who the readers are. A merge gate needs to know what documentation a change owes. Some other component may know the answer, but the consumer must also work when that component is absent, and the provider must not need the consumer installed either.

Capability dependencies (COR-030) make one capability require another, which is right when it cannot work without it. It is wrong when the second capability merely makes the first *better*: users who want only one of them would be forced to install both. Meanwhile the same "consumer defines an interface, providers contribute to it" pattern has been built several times for single purposes, each with its own rules for precedence, collisions and failure.

## Decision

**A component that needs an input declares a *slot*. Project files, installed capabilities and the component's own default fill it. The backbone resolves and validates what fills it, with no dependency in either direction.**

1. **The slot belongs to its consumer** — read, since slots became the data kind of connection point, as *the provider of the role defines the point* (refinement per [COR-053](COR-053-connection-points.md)).
   - A capability declares a slot in its package metadata.
   - The slot is named by its role-qualified point address, `<publisher>::<role>:<point>`, so slot names cannot collide (refinement per [COR-053](COR-053-connection-points.md)).
   - The declaration gives a versioned schema for the slot's data, a combination policy (point 3), how the consumer's default takes part, and an inert policy (point 6).
   - The consumer owns the interface: what the data means, and what shape it has.

2. **Three kinds of filler.**
   - **A project file.** Its location is derived under the internal documentation root (COR-049), from a sub-path the backbone owns for slot files, keyed by the slot's name.
     - It holds the slot's entries in the slot's shape, inside an envelope the backbone defines. The envelope carries the schema version the file targets, plus any suppressions or removal overrides, each with its reason.
     - The project owns the file and writes it through its own reviewed changes.
     - A malformed file, or one targeting the wrong version, is a validation error whatever the slot's inert policy, because the project can fix it.
   - **An installed capability** that declares it fills the slot. It maps its own knowledge onto the slot's shape, keeping whatever richer model it has internally.
   - **The consumer's default**, if it has one. The slot declares whether the default is **always included**, in which case it contributes like any other filler, or **used only when no other filler is declared**.

   A filler for a slot whose consumer is not installed is inert. It is not an error, and nobody depends on anybody.

3. **Combination policy, declared per slot.**
   - **`single`**: one filler answers alone.
   - **`union`**: entries from all fillers are merged by id. The project may override an entry, or suppress one explicitly.
   - **`additive`**: entries are merged, and any collision is an error, including a collision with the project. Removing an entry needs a removal override recorded with its reason. This policy is for slots whose entries carry requirements, where silently dropping one would defeat its purpose.

4. **Precedence and collisions.**
   - **Precedence**, in `single` and `union` slots: a project file beats a capability, which beats the default.
   - **Whole entries:** an override replaces a whole entry, never individual fields.
   - **Two capabilities, same id, `union` slot:** an error naming both, which the project resolves by overriding that id.
   - **Two capabilities filling one `single` slot:** an error until the project selects one.
   - **The selection key.** The selection lives in a key this record owns in the backbone configuration (COR-048). It maps a slot name to a capability name — the contributor-selection key, beside the provider-selection key that picks one capability per role (refinement per [COR-053](COR-053-connection-points.md)).
     - Its default is empty.
     - Its writers are the backbone's configuration commands and the command that reports the ambiguity, which offers to write the selection. Both act under COR-048's consent rule.
     - Validation checks that each entry names a declared `single` slot, and a capability that is installed and fills it.
     - Uninstalling a capability offers, with consent, to clear its entries; otherwise validation reports the stale entry with the fix.
     - Install order never decides.

5. **Schemas and versions.** A slot's schema is a companion schema of the consumer (COR-018), named after the slot and bound in the usual way (COR-022). Its schema version is the integer that companion schemas already carry. For slots, that integer increases only on a change that breaks existing fillers; additive changes leave it alone. A capability filler states the version it targets and is accepted when the version matches. When the consumer increases the version, capability fillers still targeting the old one go inert until they catch up. That is intended.

6. **Command fillers, and failure.**
   - **Command fillers.** A capability may supply its data through a command registered in its package metadata (COR-021). The command runs under the same limits as anchor resolvers (COR-050 point 2): a time bound the backbone enforces, and the obligations its capability declares for it — it needs no network, changes nothing in the project, and gives the same output for the same inputs. It fails closed: an abnormal exit, a timeout, or output that does not validate against the slot's schema counts as *no answer*, never as an empty answer.
   - **A filler takes no parameter.** A command filler is run with nothing but the request for machine-readable output, and prints the slot's value. A slot holds a *value*: the one thing the status report shows, a project file overrides, contributions merge into and the resolver may keep for the length of a run. A question that needs an input — which documentation does *this* change owe — is therefore not a slot. It belongs to the process kind of connection point (COR-053 point 2), whose predicates already take one subject, the identifier the engine threads through them (COR-032). A gate that asks what documentation one change owes is served either by a parameterless slot listing the obligations, which the gate applies to the change itself, or by a process point whose subject is the change. An anchor-kind resolver (COR-050 point 2) takes the anchor value as its one subject in the same way. A query command takes at most one subject: none for a filler, the anchor value for a resolver.
   - **A filler reads state, and never a base named for one run.** The inputs of a command filler are the state of the repository it runs in: the working tree, the current history, and — of settled state — only the default branch, as the backbone resolves it (COR-054 point 2). Settled state is the default branch whatever branch a change targets. A base named for one run belongs to a comparison (COR-054 point 3) and is no input: a value that followed it would be answered per run, a parameter by another route. Nor does a filler compare the branch at hand with settled state: that answers about a change, which is a process point's question, or the work of the consumer that applies the slot's value.
     - **Enforced by the backbone:** a base named for a run does not reach a filler, whichever command resolves the slot; and a filler that declares it reads settled state is not started while the default branch cannot be read (COR-054 point 4). It is inert, and the fixes are to fetch the branch or declare the right name, never to name a base.
     - **Declared by its capability, and trusted,** as the obligations of COR-050 point 2 are: which state the filler reads beyond the working tree — history, settled state, or both; that it reads them through the backbone's reading commands and resolves no reference itself; and that it compares nothing.
     - **Empty is an answer; unreachable is none.** State that does not exist yet — a repository with no commit, a default branch nothing has been committed to — holds nothing, and the filler answers with an empty value. State that exists and cannot be reached from this clone gives no answer, never an empty one. The backbone can tell that of the default branch, and refuses; only the filler knows how much history it needs, so a history cut short of that is the filler's to detect.
   - **The inert policy.** Each slot declares what happens when a filler that was meant to answer cannot: its version does not match, its command failed, or its output is invalid.
     - `fallback`: the slot resolves from the remaining fillers, with a warning naming the one that failed. If none remain, it is unresolved with a warning.
     - `fail`: the **whole** slot is unresolved, whatever its combination policy, so a gate never passes on the entries that happened to survive.
   - **Enforcing uses fail closed.** A consumer whose slot feeds a gate, a check or validation declares `fail`. That is the consumer's responsibility, since the backbone cannot tell how a slot is read. Where one slot serves both advisory and enforcing readers, the stricter use decides.
   - **A broken filler never promotes the default.** A default used only when no other filler is declared does not answer because a declared filler broke.

7. **Visible.** The status report shows, for each declared slot, how it resolved and why. That includes any filler that went inert, with the reason, and, for a filler that reads beyond the working tree (point 6), the state it declared and the commit it was read at. Validation's report names the same beside each such filler, since its answer for the slot depends on them. The health check flags whatever would make a slot's answer wrong or missing.

## Rationale

**Why the consumer owns the slot.** The consumer knows what it needs and what the data means. If providers defined the interface, each consumer would have to understand every provider's model. With the consumer defining it, each provider maps its own model once.

**Why no dependency in either direction.** A capability that merely improves another should not force its installation, and a consumer should keep working with project files alone. Inert fillers and consumer defaults make every combination of installed components valid.

**Why three policies.** Some inputs are answers, where one source should decide. Some are data merged from several sources. Some are requirements that no source may quietly remove. A single policy would get one of these wrong. The requirement case is the one where letting the project win silently would defeat the point.

**Why fail closed where enforcement happens.** If a filler goes inert and its consumer quietly falls back to a weaker default, a gate can pass on less than it was meant to check, and look as if it passed. For advisory uses a warning is enough. For gates and checks, an unresolved slot must say so.

**Why reuse the schema and command machinery.** Companion schemas, their versions, and fail-closed commands registered by capabilities already exist. Slot commands and anchor resolvers run under one set of limits, so there is one way of running a capability's data command, not two.

**Why a filler takes no parameter.** A slot answered per argument is a function, not a value: the status report could not show it, a project file could not override it, contributions could not be merged except for the same argument everywhere, and the resolver could keep nothing. The need that raised the question — what one change owes — already has a home in the process kind, whose predicates take exactly one subject.

**Why a filler reads state and never a run's base.** A slot's value is shown, overridden, merged and kept for the length of a run; that holds only if it depends on nothing chosen for the run. The working tree, the current history and the default branch are the same for every command run in a clone at one moment; a base a pipeline names for its comparisons is not. History and settled state are allowed because fillers need them — what is owed is read from history, and whether a thing exists for everyone is read from the default branch — and declared because they make a slot's answer depend on what a clone has fetched, which a reader of the report must be able to see.

**Why core.** Several components need to exchange knowledge without depending on each other, and nothing here names a discipline. The pattern has already been built several times as single-purpose contribution mechanisms, so extracting it follows the usual recurrence test (COR-007).

### Alternatives considered

- **Capability dependencies for every exchange.** Rejected. It forces installing components that are optional improvements.
- **Consumers reading providers' data directly, through shared data references.** Rejected. It forces every provider to store its data in the consumer's format, which couples their models.
- **A bespoke mechanism per pair of components.** Rejected. It adds a new copy of the same rules each time.
- **Silently falling back to the default everywhere.** Rejected. Gates would fail open while looking as if they passed.
- **Command fillers that take a parameter.** Rejected. The slot would stop being a value (see Rationale); a question with an input is a process point.
- **Fillers that read the working tree only.** Rejected. Each consumer would compute history and settled state for itself.
- **Fillers that follow the base a run names.** Rejected. A parameter by another route; see Rationale.
- **Letting install order decide between competing fillers.** Rejected. The answer would change without anyone choosing.

## Implications

- **The backbone ships** slot resolution and validation, the project-filler envelope, the status and health lines, and the selection key in the backbone configuration.
- **Components** declare their slots and their fills in their own package metadata.
- **Existing single-purpose contribution mechanisms** can move onto slots when convenient. Where a mechanism's entries carry a safety meaning, its separate failure rules stay; moving it would change how it fails, and would need a migration.
