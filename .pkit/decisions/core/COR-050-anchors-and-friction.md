---
id: COR-050
title: Artefacts declare what makes them true, and drift is detected as friction
status: accepted
date: 2026-09-27
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

A document describing a system is true only *against* something: the code it explains, a decision it applies, a source it quotes, or another description it builds on. When that something changes and the description does not, the description goes stale. Nobody notices until a reader is misled. People forget to update what depends on what they changed.

Reviews do not catch this reliably. A review looks at the change in front of it, and the stale description is usually somewhere else. What catches it is a recorded link from the description to what makes it true, plus a check that fires when the target of that link changes and the description is not rechecked.

Several parts of a project need this: descriptions of what the system must do, the project's documentation, and the checks that ask whether a change needs documentation work. They are served by different components that must not depend on one another, so the mechanism has to be shared.

## Decision

**Any artefact may declare its anchors (what makes it true) and when it was last rechecked against them. The backbone reports *friction* whenever an anchor has changed since that recheck.**

1. **Artefacts.** An artefact is either a document with front matter, or one keyed entry in a collection file whose front matter maps entries by id. Each artefact carries its own anchors and its own marker. A collection entry's content is its data entry together with the body section headed by its id, if there is one, so that editing an entry's prose is a change to it. The backbone looks for artefacts only in the **places declared to hold anchored artefacts**, so unrelated front matter elsewhere is never misread. Components declare their places in their own package metadata, relative to the document locations they resolve under COR-049; a project declares its own in the backbone configuration.

2. **Anchors.** An artefact lists its anchors in its front matter. The backbone resolves three kinds:
   - a **path**: a file or glob, relative to the repository root, where `**` matches across folders;
   - an identified **record**, such as a decision;
   - **another artefact**, by its id.

   Capabilities may register further kinds, each with a resolver: a command registered in the capability's package metadata. A resolver fails closed. If it exits abnormally or returns output the backbone cannot read, the anchor is reported as unresolved, never as resolved. An artefact without anchors is *unanchored*: a state the backbone reports, not an error.

   The anchor and marker fields are owned by this record. Their shape, for single documents and for collection entries, is fixed by a schema the backbone ships and validation applies strictly. The friction check never skips an artefact it cannot parse. In a declared place, an unparsable or malformed anchor list is reported the same way as a dead anchor.

3. **The recheck marker.** An artefact carries a recheck marker holding a UTC timestamp.
   - The timestamp is for people. Its **recheck point** is the last commit, following file renames, in which the artefact's *parsed* marker value changed. Reformatting, reordering or moving the front matter is not a recheck.
   - The timestamp changes on every recheck.
   - When two lines of work both recheck the same artefact and conflict, either timestamp may be kept, and the merge becomes the new recheck point.

4. **When an anchor has changed.**
   - **A path anchor** has changed when a commit after the recheck point modified any file it matches: one reachable from the current history and not from the recheck point.
   - **A record anchor** has changed when the record's file changed in the same way.
   - **An artefact anchor** has changed when that artefact's content changed, meaning anything other than its own marker. An upstream correction is exactly what dependants must see.
   - **Cycles** between artefacts are errors, because a cycle has no order in which it could be rechecked.

5. **Friction, in three modes.**
   - **Pull request:** every artefact with an anchor that changed in the pull request must have its marker changed in the pull request too. An artefact anchored to another artefact is included when that artefact's content changed in the pull request (point 4). The cascade continues only where a recheck itself changes content. An artefact new in the pull request counts as rechecked. Changing an artefact's own anchor list also requires a marker change, because the artefact now claims different grounds. Deleting an artefact turns its dependants' anchors dead (point 6).
   - **Sweep:** checks every artefact against the current history with the rule in point 4.
   - **Local:** runs either on demand.

   Clearing friction means rechecking and updating the marker. *How* to recheck belongs to the component that owns the artefact.

6. **Dead anchors are errors, never silence.** A path that matches nothing (or only excluded paths), or an identifier that does not resolve, is an error. When no installed component resolves a kind, that is reported separately from an identifier that does not resolve. Dead anchors are reported by the friction check in every mode, and by validation. Excluded paths, such as generated or vendored code, are ignored for anchoring and for the measures in point 7. An anchor broad enough to match most changes is warned about, because it would make every change a recheck and teach people to update markers blindly.

7. **Two measures, not failures.**
   - **Unanchored artefacts**, within the declared places.
   - **Uncovered surface:** paths within the *declared surface* that no artefact anchors to. The declared surface is what a component (in its package metadata) or the project (in the backbone configuration) says ought to be described.

   Both are reported and neither fails a check. Friction alone reads zero where nothing is anchored yet; these two measures show what remains.

8. **Truth-chain order.** Friction is reported upstream first, following the anchors between artefacts, so that what others depend on is rechecked first.

9. **Warning or enforcing.** The check is read-only.
   - In **warning mode** it reports and passes.
   - In **enforcing mode** the pull-request check fails on friction or dead anchors in that pull request.
   - A sweep reports; it does not fail other work on friction that was already there.

   The check only becomes binding when the project makes it a required status in its continuous integration. That is the project's choice. An invalid mode value is a validation error, so enforcement is never switched off silently.

10. **Project settings.** This record owns one key in the backbone configuration (COR-048). It holds the friction mode (default: warning), the project's own anchored places, its declared surface, and its excluded paths (all default: none). The key is written by the project's own edits, or by backbone configuration commands under COR-048's consent rule. Validation checks that every path in it stays inside the repository.

11. **Dormant until used.** Where no artefact declares anchors, the check finds nothing and demands nothing.

## Rationale

**Why declared anchors, not inferred ones.** Inferring what a description is about, from filenames or text similarity, is guesswork that fails silently in both directions. A declared anchor is a claim someone made and can be checked. Where declarations are missing, the unanchored measure says so honestly.

**Why a timestamp whose point comes from git.** A commit identifier cannot be written into the commit it identifies. It also disappears from the main history on a squash merge or rebase. A content hash of the anchored inputs conflicts on every parallel change under a glob, and nobody can read it. A timestamp is readable and changes on every recheck, while the commit that last changed it is exactly the point git can answer questions about.

**Why the pull-request rule is local to the pull request.** "An anchor changed here, so the marker changes here" explains itself to the author at the moment the fix is cheapest. The sweep uses the same notion of "changed since the recheck point", so the two agree after merging.

**Why the recheck point follows the parsed value.** If formatting or file moves could advance the point, friction could be cleared without anyone rechecking. The point must move only when someone deliberately rechecks.

**Why uncovered surface is declared, not everything.** Counting every file in the repository as needing description would make the measure pure noise on day one. The measure means something only against a surface someone has said ought to be described.

**Why dead anchors are errors.** A glob that matches nothing produces no friction, for ever. Silence would look like health.

**Why it is core.** Three kinds of component need it: those describing what the system must do, those keeping documentation true, and those checking whether a change owes documentation work. They must not depend on one another. Core is the only home that serves all three without one depending on another or each carrying its own copy. Its consumers are known, not speculative, so the usual wait for a pattern to recur before extracting it (COR-007) is not applied here. The mechanism names no discipline, so it makes sense in any project. Its first use needs no capability at all: an architectural decision record (COR-025) can anchor the code it governs today. Where nothing is anchored, it is dormant.

### Alternatives considered

- **Anchors on every statement inside a document.** Rejected. Precise, but the maintenance cost makes people stop, which recreates the drift. Precision comes instead from whoever rechecks the flagged artefact against the actual change.
- **Anchors per section, via markers inside the prose.** Rejected. It adds a second convention, parsed out of prose.
- **Storing each artefact's current-or-stale state.** Rejected. Stored state duplicates what git already answers, and it drifts from git whenever a change bypasses the check.
- **A commit identifier or a content hash as the marker.** Rejected; see Rationale.
- **One copy per component.** Rejected. Separate engines drift apart, and the components would disagree about what is stale.

## Implications

- **The backbone ships the friction check,** with pull-request, sweep and local modes, reading anchors and markers in the declared places. Its output includes a machine-readable form, so that other components can consume friction and uncovered surface.
- **The backbone ships the schema** for the anchor and marker fields. It is a surface change adopters can see, and existing documents are unaffected.
- **Components that keep anchored artefacts** declare their places and surface in their own package metadata. They register their own anchor kinds and resolvers, and define how their artefacts are rechecked. They may also decide what to do when a recheck finds that the description was right and the change was wrong.
- **Continuous integration** needs enough history to reach the oldest recheck point for sweeps. Pull-request checks need only the diff.
- **The backbone configuration** gains the key from point 10.
- **The status report** can show friction, unanchored artefacts and uncovered surface.
