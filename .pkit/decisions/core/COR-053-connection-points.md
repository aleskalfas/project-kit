---
id: COR-053
title: Components connect through role-named connection points, declared by the side that needs something
status: proposed
date: 2026-09-27
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** when one capability needs something from another — readers for its documentation, a process to wait on, a signal that an artefact was created — it does not name the other capability. It declares a *connection point* under a **role**, and whichever installed capability *provides that role* answers it. A role is written `<publisher>::<role>`, the publisher being whoever defined the role; a point is `<publisher>::<role>:<point>`. Nothing is required of the other side; every connection is optional unless it says, with a reason, that it is mandatory. The data slots already decided (COR-052), the process connections already decided (COR-036, COR-038, COR-042) and a new kind, *events*, are the three kinds of one mechanism, drawn in one wiring graph and checked by one resolver. Swapping one documentation capability for another that provides the same role is invisible to everything connected to it.

The examples below write the methodology's own qualifier as `pkit::` and the methodology-owned front-matter container as `pkit:`, the names this distribution uses; the record decides the grammar, not those literals.

## Context

Capabilities need to exchange knowledge and to react to each other without depending on each other (COR-030 makes a dependency the exception). Two mechanisms already do part of this. Data *slots* let a consumer declare an input others fill (COR-052). Process *connections* let a process declare, inertly, which other process it relies on (COR-038), with an opt-in hand-off contract that the report-only health surface evaluates (COR-042) and a public interface a parent may embed (COR-036). Both were designed with the dependent side declaring the connection, which is right. Both address the other side **by implementation** — `<consumer>:<slot>`, `<capability>:<process-id>` — which is wrong for the case that motivated them: replacing one capability with another that does the same job must not touch anything connected to it. Records name roles, not the thing currently playing them (COR-046); the connection machinery should too.

A third need appeared while designing the disciplines that keep analysis and documentation true: a command in one capability finishing should let a connected capability act — without the first ever naming the second, and without agents orchestrating the flow. That is neither a slot nor a process connection.

Finally, nothing so far tells a user what a capability would connect to *in this project* before installing it, which points are unfilled, or what an uninstall would leave dangling.

## Decision

**A connection point is declared by the side that needs something, named under a role qualified by the publisher of its definition, versioned per point, optional by default, resolved and validated by the backbone, and drawn in one wiring graph. Slots, process connections and events are its three kinds.**

Vocabulary used below. The **publisher** of a role coins its name and is a namespace only. The **provider** of a role is the installed capability that supplies the role's points and their schemas. A **counterpart** is whatever sits at the other end of a connection: a contributor to a data point, a subscriber to an event, a process that depends on an offered process. Two versions are **compatible** when their integers are equal.

1. **Roles.** A capability declares, in its package metadata, the role or roles it *provides*. A role is an open name; there is no registry. The methodology documents the role names its own capabilities use as recommendations only.
   - A role name is qualified by its **publisher**: `<publisher>::<role>`. The methodology reserves one qualifier for the roles it defines; a third party uses its own name. The qualifier names the origin of the definition, never the installed implementation, so another capability may provide `pkit::documentation` and be interchangeable with the one that first defined it, while `super-docs::documentation` is a different role that shares a word. Project-published roles are left to a later refinement; the grammar leaves room for them.
   - **One active provider per qualified role.** Two installed capabilities providing the same qualified role is an error until the project selects one (point 7). An installed but unselected provider's connections are inert — its points are not defined, its contributions and subscriptions are not delivered — while its own commands still run. A role's points are never split across providers, so it is always clear who answers `pkit::documentation:*`.
   - A capability may provide several roles, and may provide the same role under two publishers' names if it is compatible with both definitions.
   - **The honest limit of publisher qualification.** Because there is no definition artefact, the schema of a point lives in whichever provider is installed. The fingerprint (point 5) catches two providers of one qualified point disagreeing only when both are present, or when catalogs are compared; a single divergent provider is caught by nothing but its counterparts' validation failing.

2. **Points, addressed `<publisher>::<role>:<point>`, in three kinds.** The provider of a role defines the role's points.
   - **data** — an input the definer *accepts* and others may contribute to. This is the slot of COR-052; every rule there stands — combination policy, precedence, project filler, defaults, inert policy, command fillers — with the slot's name replaced by the role-qualified address and "the consumer" read as "the role's provider".
   - **process** — a process the definer *offers* through its interface (COR-036), which others may embed or declare a connection to (COR-038, COR-042). A process interface gains an integer version like any point. Process addresses gain the role form as an additive refinement; the implementation form keeps working, unversioned as today, where a specific implementation is genuinely meant. A role-addressed connection targets an offered process.
   - **event** — a signal the definer *offers* when one of its **writing** commands completes, with a versioned payload schema. Reading commands emit nothing. Others *subscribe* with a command of their own. The backbone runs subscribers after the producing command finishes; the producer never names a subscriber, and the active provider of the subscribing role receives it. This is the separate reactive layer COR-038 named and left outside the engine: it runs at command altitude, and the pull-only position engine is untouched.

3. **Declared in package metadata, in one block named for the functionality: `connections`.** Its keys answer two questions — *whose point is it* and *which way does it flow*:
   - `roles` — the qualified roles this capability provides;
   - `extension-points` — points this capability **defines**: `accepts` (data in), `offers` (processes and events out);
   - `extensions` — where this capability **plugs into others**: `contributes` (data it supplies to another role's point), `subscribes` (events it reacts to, with its command), `depends-on` (processes it relies on).
   Embedding edges are not listed: they are derived from `subprocess` declarations, exactly as COR-038 derives them. The definer of a point is always the provider of the role in its name, so no further marker is needed. Every extension point carries a required prose `description` — what it means and what one may rely on; every extension may carry one. Nothing parses descriptions; people read them in plans, in the graph and in the capability view.

4. **`depends-on` is generated, never hand-written.** Its single source is the process definitions' `depends_on` (COR-038). A refresh command regenerates it, marks it generated, and validation fails a stale copy with the instruction to refresh; the process definition always wins. This *is* a second copy of a fact, the thing COR-038's derive-don't-annotate rule forbids for hand-written annotations — it is allowed here because the copy is machine-written and a stale copy **fails validation** rather than lying quietly, the discipline lock files follow.

5. **Versions per point; roles unversioned.** A point's version is an integer, increased only on a change that breaks existing counterparts; additive changes leave it alone. A counterpart states the version it targets and connects only to a compatible point. A fundamental redefinition of a role is a new role name. A schema **fingerprint** is kept as an integrity check only — two providers of the same qualified point and version must define the same shape — never as the point's identity.

6. **Optional by default; mandatory only with a reason, on the individual connection.** A connection may carry `mandatory: {reason}`; validation rejects the mark without a reason.
   - On an accepted data point: it must be filled by something other than the default.
   - On a contribution or subscription: the target point must exist at a compatible version.
   - On a process connection: marked at its source, the process definition's `depends_on` entry, and meaning the offered process must exist. **This adds one reader of `depends_on`** to the set COR-042 fixed: a lifecycle gate that reads the `mandatory` mark alone and checks that the upstream *definition* exists — never position, never move-legality. The runtime engine and every move gate still never read `depends_on`. COR-042 asked that any further enforcing coupling be taken at supersession weight with explicit sign-off; this record takes it, and COR-038 and COR-042 carry the amendment note.
   - **Disposition follows COR-030.** Installing or upgrading the side that carries the mark against a missing or incompatible target refuses with a hint; upgrading or uninstalling the *target* past a mandatory counterpart warns, names each counterpart, and proceeds only under an explicit force — never a hard block, so no deadlock.
   - Two mandatory marks facing each other form a lock that could never be installed one capability at a time; validation rejects a mandatory cycle and the install plan reports it.
   - Self-contained capabilities remain the norm. Nothing here replaces `requires_capabilities` (COR-030), which stays for the rare case where one specific implementation is meant.

7. **One wiring resolver, one graph, two selection keys.**
   - The backbone resolves the wiring: which provider answers each role, which counterparts match each point at a compatible version, what is unfilled, what is inert, what is mandatory and unmet. It resolves wiring, not data: it never runs a command filler to plan.
   - Selection lives in the backbone configuration (COR-048's duties apply — empty by default, written with consent by configuration commands or when a conflict is reported, validated against what is installed, cleared on uninstall with consent), in one block also named `connections`: `providers` selects one capability per qualified role; `selections` selects one contributor per `single` data point when several capabilities contribute to it. The second is COR-052's selection key with a role-qualified address — the two conflicts are different (who defines the points versus who answers one of them), so one key cannot serve both.
   - The status report shows the resolved wiring; a dedicated graph command draws it; the health surface reports unmet mandatory connections, role conflicts, stale generated lists and inert counterparts.

8. **Discovery at four moments.** A capability's connections are readable from its package metadata without installing it, and plans are computed by the same wiring resolver that builds the live wiring, so a plan predicts the wiring exactly.
   - *Exploring:* the capability view lists a capability's roles, points and extensions, and what it would connect to in this project.
   - *Deciding:* an install plan lists the connections it would make, role conflicts and how to resolve them, and what it needs.
   - *Noticing gaps:* status and the graph show unfilled points and **suggest** capabilities that would fill them, drawing only on the sources the project already configures for capabilities. A suggestion is never an action.
   - *Removing:* an uninstall plan lists the fillers lost, processes and events left without a provider, and project-owned artefacts whose role blocks would be orphaned.

9. **Events: bounded, visible, cascading with a guard, no separate consent model.**
   - Subscribers run under the limits already set for capability commands the backbone runs on someone's behalf (COR-050 point 2, COR-052 point 6): bounded time, no network, deterministic, fail closed. A reaction that needs the network — posting to a work tracker, say — is therefore not an event subscriber; it belongs to suggested next steps or to an agent. A failing subscriber never undoes the producer; it is reported.
   - Consent already exists twice — the project installed the subscribing capability, and the user ran a writing command — so no third consent is asked. Predictability comes from visibility: the install plan shows what a capability subscribes to and what it writes; every run lists the subscriber effects it caused; a plan option lists the subscribers that would run and previews the effects of those that support a plan run; an opt-out runs the command alone; non-interactive runs behave the same; everything lands in the diff.
   - Cascades are allowed. The **subject** of an event is the identity its payload names; an event already handled for the same subject within one command's chain is not delivered again and is reported as a loop; a depth limit backstops it; the whole chain is reported when the command ends.
   - Edits made by hand emit no events; friction (COR-050) covers them.

10. **Role blocks in artefacts.** A project-owned artefact keeps the data a role needs about it in a block named after the role, inside the one methodology-owned container in its front matter (the container COR-050's refinement in this change-set records). The key is the role word alone, the qualifier being resolved from the active provider; when two active roles share a word, the qualified form is written as the key. A role block states the point version it targets, as a project filler does (COR-052 point 2). A block whose role has no active provider is **orphaned**: preserved and reported, never an error, and validated again when a provider is active — a later provider of the role adopts it.

11. **Not everything is a process.** The process substrate is content-free: a process carries position and points at its domain data rather than holding it (COR-033). Data points are that data made shareable; events are the reaction to a completed command. The kinds share one addressing scheme, one versioning rule, one compatibility check, one command runner, one graph and one status view — the mechanisms are shared, not duplicated.

## Rationale

**Why the needing side declares.** It knows what it needs and what the data or signal means. Its counterparts each map their own model once. Because nothing is required of the other side unless a connection is marked mandatory — and mandatory cycles are rejected — mutual connections never form a lock: documentation may connect to analysis and analysis to documentation with neither depending on the other.

**Why roles, qualified by publisher.** Addressing by implementation is the one thing that defeats replacement. Roles fix that, and the publisher qualifier keeps role names from being reserved globally while making it plain which ecosystem a point belongs to — a fully qualified interface name keeps its name whichever class implements it. Qualifying by the *implementing* capability was rejected for breaking replacement; fingerprints as the identity were rejected as unreadable.

**Why one mechanism with three kinds.** Slots and process connections already share the paradigm and differed only in addressing; keeping them separate would mean two resolvers, two graphs and two versioning rules for one idea. Events are a third kind, not a fourth mechanism, because a subscriber is a command counterpart exactly as a command filler is.

**Why `extension-points` / `extensions`, split by direction.** Two classic vocabularies each answer one question: Eclipse's extension points versus extensions says *whose point is it*; UML's provided versus required says *which way it flows*. Together they make the metadata self-explaining, which is why the key names are decided here rather than left to a reference. `requires`/`provides` for points was rejected: "requires" sounds mandatory and collides with COR-030's key. Plain UML hides the definer; plain Eclipse hides the direction; exports/imports reads backwards for data.

**Why mandatory on the connection, with a reason.** A mandatory *role* only restated connections already listed; marking the connection names exactly what is needed, in one place. Requiring a reason keeps optional the norm.

**Why per-point versions.** Compatibility is decided per connection; one version per role would break contributors to points that did not change, and two levels would be two numbers to keep consistent.

**Why generate `depends-on`.** The list belongs in the package so a reader — and the capability view for an uninstalled capability — sees it without opening process definitions; a hand-written copy would drift silently (COR-006, COR-038). Generating it with fail-closed validation keeps one source and one visible copy.

**Why no consent model for events.** The methodology asks consent where a command writes a file the project owns (the backbone configuration, COR-048; anchored artefacts, COR-050); it has no consent model for a capability acting once installed and invoked, and inventing one here would gate the common case to guard a rare one. Visibility — plans, per-run reports, the diff — is what makes behaviour predictable. Firing only from writing commands keeps reading commands side-effect-free.

**Why core.** Three capabilities that must not depend on each other need it, the process substrate already carries half of it, and nothing here names a discipline (COR-007, COR-014).

### Alternatives considered

- **A separate contract package per role, which capabilities implement.** Rejected. "Contract" proved too strong: requiring one capability to implement another's contract creates loops, and a separate component was more machinery than the idea needs.
- **Aligning slots only and recording process connections as a known gap; or keeping the two mechanisms separate.** Rejected. Two copies of one idea.
- **A registered list of roles.** Rejected: friction for third parties. **No roles at all.** Rejected: names collide, and nothing groups a capability's points.
- **One version per role; versions at both levels.** Rejected (see Rationale).
- **`requires-roles` and `must-be-filled` as separate mandatory marks.** Rejected in favour of one mark on the connection. **Deferring mandatory process connections.** Considered; rejected because the mark then lives in two places for two kinds and one for the third, and the added reader is narrow enough to state precisely.
- **One selection key for both role and contributor conflicts.** Rejected: they are different conflicts.
- **Hand-written `depends-on`; or derived for display only.** Rejected: the first drifts, the second is invisible in the file.
- **Slots as process inputs.** Rejected. A process input is passed by an embedding parent per run; a data point is standing knowledge read by many, often outside any process.
- **Commands calling connected capabilities by name; agents as the only flow.** Rejected. The first re-couples what roles decoupled; the second makes the flow depend on who is driving.
- **Treating orphaned role blocks as errors.** Rejected: the project can do nothing about them but delete data it may want back.

## Implications

- **COR-052 is refined, not superseded**: a slot is the data kind of connection point; its name is role-qualified; "the consumer owns the slot" reads "the role's provider defines the point"; its selection key becomes `connections.selections`. **COR-036** gains an interface version. **COR-038 and COR-042** gain role addressing as an additive refinement and carry the amendment note for the one added reader of `depends_on` (point 6); **COR-038's `depends_on`** becomes the source of the generated `depends-on`. Each refinement is a pointer in the affected record to this one.
- **Schema changes**, each a surface change with a migration where it breaks existing files (COR-010): the `connections` block in the package-metadata schema; the `connections` block with `providers` and `selections` in the backbone-configuration schema (COR-048); `mandatory` on a `depends_on` entry and `version` on a process interface in the process schema; the role-block shape inside the artefact container.
- **The backbone ships** the wiring resolver, the graph, the status and health lines, the refresh command, the event runner with its loop guard, and the plan options on install and uninstall. Validation of all of it belongs to the first increment that ships any of it.
- **Capabilities** declare roles, points and extensions in their package metadata; capability records that name points switch to the role-qualified form.
- **Existing process definitions** are unchanged until their authors adopt role addresses; the implementation form stays valid.
