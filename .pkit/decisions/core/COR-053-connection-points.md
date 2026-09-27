---
id: COR-053
title: Components connect through role-named connection points, declared by the side that needs something
status: proposed
date: 2026-09-27
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** when one capability needs something from another — readers for its documentation, a process to wait on, a signal that an artefact was created — it does not name the other capability. It declares a *connection point* under a **role** (`pkit::documentation:readers`), and any installed capability that *provides that role* answers it. Nothing is required of the other side; every connection is optional unless it says, with a reason, that it is mandatory. The data slots already decided (COR-052), the process connections already decided (COR-036, COR-038, COR-042) and a new kind, *events*, are the three kinds of one mechanism, drawn in one wiring graph and validated by one resolver. Swapping one documentation capability for another that provides the same role is invisible to everything connected to it.

## Context

Capabilities need to exchange knowledge and to react to each other without depending on each other (COR-030 makes a dependency the exception). Two mechanisms already do part of this. Data *slots* let a consumer declare an input others fill (COR-052). Process *connections* let a process declare, inertly, which other process it relies on (COR-038), with an opt-in hand-off contract that the health surface evaluates (COR-042) and a public interface a parent may embed (COR-036). Both were designed with the dependent side declaring the connection, which is right. Both address the other side **by implementation** — `<consumer>:<slot>`, `<capability>:<process-id>` — which is wrong for the case that motivated them: replacing one capability with another that does the same job must not touch anything connected to it. Records name roles, not the thing currently playing them (COR-046); the connection machinery should too.

A third need appeared while designing the disciplines that keep analysis and documentation true: a command in one capability finishing should let a connected capability act — without the first ever naming the second, and without agents orchestrating the flow. That is neither a slot nor a process connection.

Finally, nothing so far tells a user what a capability would connect to *in this project* before installing it, which points are unfilled, or what an uninstall would leave dangling.

## Decision

**A connection point is declared by the side that needs something, named under a role qualified by the publisher of its definition, versioned per point, optional by default, resolved and validated by the backbone, and drawn in one wiring graph. Slots, process connections and events are its three kinds.**

1. **Roles.** A capability declares, in its package metadata, the role or roles it *provides*. A role is an open name; there is no registry. The methodology documents the role names its own capabilities use as recommendations only.
   - A role name is qualified by the **publisher of its definition**: `<publisher>::<role>` — `pkit::documentation` for a role the methodology defines, a third party's own name for theirs, the project's name for a project-defined role. The qualifier names the origin of the definition, never the installed implementation, so `super-living-docs` may provide `pkit::documentation` and be interchangeable with the capability that defined it, while `super-docs::documentation` is a different role that shares a word.
   - **One active provider per qualified role.** Two installed capabilities providing the same qualified role is an error until the project selects one. A role's points are never split across providers, so it is always clear who answers `pkit::documentation:*`.
   - A capability may provide several roles.

2. **Points, addressed `<publisher>::<role>:<point>`, and their kinds.** The provider of a role defines the role's points. Three kinds:
   - **data** — an input the definer *accepts* and others may contribute to. This is the slot of COR-052; every rule there (combination policy, precedence, project filler, defaults, inert policy, command fillers) stands, with the slot's name replaced by the role-qualified address and "the consumer" read as "the role's provider".
   - **process** — a process the definer *offers* through its interface (COR-036), which others may embed or declare a connection to (COR-038, COR-042). Process addresses gain the role form as an additive refinement; the implementation form keeps working where a specific implementation is genuinely meant.
   - **event** — a signal the definer *offers* when one of its commands completes, with a versioned payload schema. Others *subscribe* with a command of their own. The backbone runs subscribers after the producing command finishes; the producer never names a subscriber, and whichever capability provides the subscribing role receives it.

3. **Declared in package metadata, in a block named for the functionality: `connections`.** It holds `roles`; `extension-points` — what this capability *defines*, split `accepts` (data in) and `offers` (processes and events out); and `extensions` — where this capability *plugs into others*, split `contributes` (data it supplies to another role's point), `subscribes` (events it reacts to) and `depends-on` (processes it relies on). Whose point it is and which way it flows are both visible from the key. The definer of a point is always the provider of the role in its name, so no further marker is needed. Every extension point carries a required prose `description` (what it means and what one may rely on); every extension may carry one. Nothing parses descriptions; people read them in plans, in the graph and in the capability view.

4. **`depends-on` is generated, never hand-written.** Its single source is the process definitions' `depends_on` (COR-038). A refresh command regenerates it, marks it generated, and validation fails a stale copy with the instruction to refresh. The process definition always wins.

5. **Versions per point; roles unversioned.** A point's version is an integer, increased only on a change that breaks existing counterparts; additive changes leave it alone. In metadata it is a field; in displays it is written `@N`. A counterpart states the version it targets. A fundamental redefinition of a role is a new role name. A schema **fingerprint** is kept as an integrity check only — two providers of the same qualified point and version must define the same shape — never as the point's identity.

6. **Optional by default; mandatory only with a reason, on the individual connection.** Any connection may carry `mandatory: {reason}`, and validation rejects the mark without a reason. On an accepted data point it means the point must be filled by something other than the default. On a contribution or subscription it means the target point must exist at a compatible version. On a process connection it is marked at its source, the process definition, and means the offered process must exist. Installation refuses to violate a mandatory connection, and so does uninstalling the provider it depends on. Self-contained capabilities remain the norm; nothing here replaces `requires_capabilities` (COR-030), which stays for the rare case where one specific implementation is meant.

7. **One resolver, one graph, one selection key.**
   - The backbone resolves the wiring: which provider answers each role, which counterparts match each point at a compatible version, what is unfilled, what is inert, what is mandatory and unmet.
   - The selection of one provider per qualified role lives in the backbone configuration under `connections.providers` (COR-048's duties apply: empty by default, written with consent by configuration commands or when a conflict is reported, validated against what is installed, cleared on uninstall with consent). It replaces the per-slot selection key of COR-052.
   - The status report shows the resolved wiring; a dedicated graph command draws it; the health surface reports unmet mandatory connections, role conflicts, stale generated lists and inert counterparts.

8. **Discovery at four moments.** A capability's connections are readable from its package metadata without installing it, and plans are computed by the same resolver that builds the live wiring, so a plan predicts exactly what happens.
   - *Exploring:* the capability view lists a capability's roles, points and extensions, and what it would connect to in this project.
   - *Deciding:* an install plan lists the connections it would make, role conflicts and how to resolve them, and what it needs.
   - *Noticing gaps:* status and the graph show unfilled points and **suggest** available capabilities that would fill them, drawing only on the catalogs the project already uses. A suggestion is never an action.
   - *Removing:* an uninstall plan lists the fillers lost, processes and events left without a provider, and project-owned artefacts whose role-named blocks would be orphaned.

9. **Events: bounded, visible, cascading with a guard, no separate consent model.**
   - Subscribers run under the limits already set for capability commands the backbone runs on someone's behalf (COR-050, COR-052): bounded time, no network, deterministic, fail closed. A failing subscriber never undoes the producer; it is reported.
   - Consent already exists twice — the project installed the subscribing capability, and the user ran the producing command — so no third consent is asked. Predictability comes from visibility: the install plan shows what a capability subscribes to and what it writes; every run lists the subscriber effects it caused; a plan option previews them and an opt-out runs the command alone; non-interactive runs behave the same; everything lands in the diff.
   - Cascades are allowed. An event already handled for the same subject within one command's chain is not delivered again and is reported as a loop; a depth limit backstops it; the whole chain is reported when the command ends.
   - Edits made by hand emit no events; friction (COR-050) covers them.

10. **Not everything is a process.** The process substrate carries *position*; domain data lives elsewhere (COR-033). Data points are that "elsewhere", made shareable; events are the reaction to a completed command. The kinds share one addressing scheme, one versioning rule, one compatibility check, one command runner, one graph and one status view — the mechanisms are shared, not duplicated.

## Rationale

**Why the needing side declares.** It knows what it needs and what the data or signal means. Its counterparts each map their own model once. Because nothing is ever required of the other side, mutual connections never form a lock: documentation may connect to analysis and analysis to documentation with neither depending on the other.

**Why roles, qualified by publisher.** Addressing by implementation is the one thing that defeats replacement. Roles fix that, and the publisher qualifier keeps role names from being reserved globally while making it plain which ecosystem a point belongs to — a fully qualified interface name keeps its name whichever class implements it. Qualifying by the *implementing* capability was rejected for breaking replacement; fingerprints as the identity were rejected as unreadable.

**Why one mechanism with three kinds.** Slots and process connections already share the paradigm and differed only in addressing; keeping them separate would mean two resolvers, two graphs and two versioning rules for one idea. Events are a third kind, not a fourth mechanism, because a subscriber is a command counterpart exactly as a command filler is.

**Why `extension-points` / `extensions`, split by direction.** Two classic vocabularies each answer one question: Eclipse's extension points versus extensions says *whose point is it*; UML's provided versus required says *which way it flows*. Together they make the metadata self-explaining. `requires`/`provides` for points was rejected: "requires" sounds mandatory and collides with COR-030's key. Plain UML hides the definer; plain Eclipse hides the direction; exports/imports reads backwards for data.

**Why mandatory on the connection, with a reason.** A mandatory *role* only restated connections already listed; marking the connection names exactly what is needed, in one place. Requiring a reason keeps optional the norm.

**Why per-point versions.** Compatibility is decided per connection; one version per role would break contributors to points that did not change, and two levels would be two numbers to keep consistent.

**Why generate `depends-on`.** A hand-written copy of what the process definitions already say drifts silently (COR-006). Generating it keeps the list visible in the package without a second source, like the tool-written fields on anchored artefacts (COR-050).

**Why no consent model for events.** The methodology asks consent for writes to project-owned files (COR-048); it has no consent model for a capability acting once installed and invoked, and inventing one here would gate the common case to guard a rare one. Visibility — plans, per-run reports, the diff — is what makes behaviour predictable.

**Why core.** Three capabilities that must not depend on each other need it, the process substrate already carries half of it, and nothing here names a discipline (COR-007, COR-014).

### Alternatives considered

- **A separate contract package per role, which capabilities implement.** Rejected. "Contract" proved too strong: requiring one capability to implement another's contract creates loops, and a separate component was more machinery than the idea needs.
- **Aligning slots only and recording process connections as a known gap; or keeping the two mechanisms separate.** Rejected. Two copies of one idea.
- **A registered list of roles.** Rejected: friction for third parties. **No roles at all.** Rejected: names collide, and nothing groups a capability's points.
- **One version per role; versions at both levels.** Rejected (see Rationale).
- **`requires-roles` and `must-be-filled` as separate mandatory marks.** Rejected in favour of one mark on the connection.
- **Hand-written `depends-on`; or derived for display only.** Rejected: the first drifts, the second is invisible in the file.
- **Slots as process inputs.** Rejected. A process input is passed by an embedding parent per run; a data point is standing knowledge read by many, often outside any process.
- **Commands calling connected capabilities by name; agents as the only flow.** Rejected. The first re-couples what roles decoupled; the second makes the flow depend on who is driving.

## Implications

- **COR-052 is refined, not superseded**: a slot is the data kind of connection point; its name is role-qualified; "the consumer owns the slot" reads "the role's provider defines the point"; its selection key is replaced by `connections.providers`. **COR-036, COR-038 and COR-042** gain role addressing as an additive refinement; **COR-038's `depends_on`** becomes the source of the generated `depends-on`. Each refinement is a pointer in the affected record to this one.
- **The backbone ships** the resolver, the wiring graph, the status and health lines, the `connections.providers` key with its schema (COR-048), the package-metadata schema for the `connections` block, the refresh command, the event runner with its loop guard, and the plan options on install and uninstall. Validation of all of it is part of the umbrella validation command from the first increment.
- **Capabilities** declare roles, points and extensions in their package metadata; capability records that name points switch to the role-qualified form.
- **Artefacts** carry role-named blocks inside the `pkit:` container (the front-matter convention COR-050 records), so an artefact's data for a role survives a change of provider.
- **Existing process definitions** are unchanged until their authors adopt role addresses; the implementation form stays valid.
