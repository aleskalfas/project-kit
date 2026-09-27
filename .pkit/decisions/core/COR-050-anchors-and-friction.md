---
id: COR-050
title: Artefacts declare what makes them true, and drift is detected as friction
status: accepted
date: 2026-09-27
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Context

A document describing a system is true only *against* something: the code it explains, a decision it applies, a source it quotes, or another description it builds on. When that something changes and the description does not, the description goes stale. Nobody notices until a reader is misled. People forget to update what depends on what they changed.

Reviews do not catch this reliably. A review looks at the change in front of it, and the stale description is usually somewhere else. What catches it is a recorded link from the description to what makes it true, plus a check that fires when the target of that link changes and the description is not revalidated.

Several parts of a project need this: descriptions of what the system must do, the project's documentation, and the checks that ask whether a change needs documentation work. They are served by different components that must not depend on one another, so the mechanism has to be shared.

## Decision

**Any artefact may declare its anchors (what makes it true) and when it was last revalidated against them. The backbone reports *friction* whenever an anchor has changed since that revalidation. The answer to friction lives in the artefact itself — never in a pull-request description.**

Three terms recur. The **revalidation point** of an artefact is the last commit in which the parsed value of its `at` field changed (point 3). The **deferral point** of a deferral entry is the commit that first introduced that entry (point 4). An artefact's **content** is its body text, compared textually, and its own front-matter fields, compared parsed — excluding everything in the methodology's container (point 5). **The diff** of a pull request is the set of paths changed between its up-to-date base and its head, and the parsed before-and-after of every artefact in a declared place.

### What an artefact carries

1. **Artefacts.** An artefact is either a document with front matter, or one keyed entry in a collection file whose front matter maps entries by id. Each artefact carries its own anchors and its own revalidation. A collection entry's content is its data entry together with the body section headed by its id, if there is one, so that editing an entry's prose is a change to it. The backbone looks for artefacts only in the **places declared to hold anchored artefacts**, so unrelated front matter elsewhere is never misread. Components declare their places in their own package metadata, relative to the document locations they resolve under COR-049; a project declares its own in the backbone configuration.

   Everything this record owns in an artefact sits in **one functionality block, named `friction`**, inside the methodology's front-matter container (refinement per COR-053, point 10). For a document the container is in its front matter; for a collection entry it is inside the entry, so each entry carries its own block. The artefact's own fields — its id, status, whatever defines it — stay outside the container and belong to the component that defines the artefact. The functionality's key is the same word as its command group, so a reader sees one name in the file, in the command and in the configuration (the one-name-per-functionality rule of COR-053). The keys this record names are decided here because people write them; layout and casing beyond them belong to the schema the backbone ships.

2. **Anchors.** An artefact lists its anchors in its block, grouped by kind. The backbone resolves three kinds:
   - a **path**: a file or glob, relative to the repository root, where `**` matches across folders;
   - an identified **record**, such as a decision;
   - **another artefact**, by its id.

   Capabilities may register further kinds, each with a resolver: a command registered in the capability's package metadata. A resolver runs with a bounded time, no network access, and deterministic output for the same inputs. It fails closed: if it exits abnormally, times out, or returns output the backbone cannot read, the anchor is reported as unresolved, never as resolved. An artefact without anchors is *unanchored*: a state the backbone reports, not an error.

   The block's fields are owned by this record. Their shape, for single documents and for collection entries, is fixed by a schema the backbone ships and validation applies strictly — a revalidation marked `unchanged` without its justification, or an empty revalidation, fails there. The friction check never skips an artefact it cannot parse. In a declared place, an unparsable or malformed block is reported the same way as a dead anchor.

3. **The revalidation.** An artefact records its last revalidation in a `revalidated` block, **written on a person's decision** — by hand, or through the revalidate and defer commands run on that person's branch — and never by the after-merge job of point 10:
   - **`at`** — a UTC timestamp, the marker. The timestamp is for people; the **revalidation point** is the last commit, following file renames, in which the parsed value of `at` changed. Reformatting, reordering or moving the front matter is not a revalidation. `at` changes on every revalidation. An artefact with no `at` has as its revalidation point the commit that introduced its block. Because rename detection is a guess that can hide earlier changes behind a later point, **moving an artefact** — renaming its file, or moving an entry between collection files — **requires a revalidation in the same change**.
   - **`outcome`** — `updated` (the content changed with the revalidation) or `unchanged` (the content did not need to change). With `unchanged`, **`unchanged-because`** is required and must itself change in the same diff: the sentence saying why the content still holds against *this* change. It is the one piece of judgment the tool cannot supply, and the only safeguard against a blind marker bump.
   - The outcome is a record of what happened, checked against the diff at the time (point 5); it is never read to compute staleness, which is always recomputed from git.
   - When two lines of work both revalidate the same artefact and conflict, the person resolving the conflict **revalidates the combined state**. This is a rule for people that the check cannot verify; there is no automatic merge, because one would claim a revalidation that never happened.

4. **Deferrals.** Inside `revalidated`, a **`deferred`** list holds one entry per anchor whose friction is deliberately postponed: the anchor, written as its kind and value, and a reason.
   - An entry defers the friction of one anchor up to its **deferral point**, the commit that first introduced the entry; rewording the reason does not move it. A later change to that anchor is new friction.
   - Only the reason is stored; the entry's origin — author, date, change — comes from git. Entries are kept sorted by anchor, so parallel branches deferring different anchors merge cleanly.
   - Adding a deferral does not change `at`: it is not a revalidation. An artefact never yet revalidated may carry `deferred` without `at`.
   - A revalidation **re-states the deferrals it keeps**: the block is rewritten, and an entry the person keeps is kept deliberately and keeps its deferral point. The check warns about kept entries so that keeping them is a conscious act, not a habit. Removing an entry without revalidating brings that anchor's friction back. Removing an anchor removes its entry; a dangling entry, one naming no anchor of the artefact, is a validation error. Removing the artefact (point 6) removes its entries. Deferrals never expire on their own; their age is shown.

### What the checks compute

5. **When an anchor has changed, and what answers it.**
   - **A path anchor** has changed when a commit after the revalidation point modified any file it matches: one reachable from the current history and not from the revalidation point.
   - **A record anchor** has changed when the record's file changed in the same way.
   - **An artefact anchor** has changed when that artefact's **content** changed — its body, or its own fields, but nothing inside the methodology's container, whichever functionality's block it is. An upstream correction is exactly what dependants must see; another functionality's bookkeeping is not.
   - **Cycles** between artefacts are errors, because a cycle has no order in which they could be revalidated.
   - **Three answers**, judged from the diff, clear friction: the artefact's content changed and `at` changed (*updated*); only `at` changed, with a new `unchanged-because` (*unchanged*); or a deferral covers the anchor (*deferred*). A change to `at` with none of these behind it, or an `outcome` the diff contradicts, is reported as a bump with nothing behind it.

6. **Friction, in two checks.**
   - **The change check** works on the diff alone: every artefact with an anchor that changed in the pull request must carry one of the three answers in the same pull request. An artefact anchored to another artefact is included when that artefact's content changed in the pull request. The cascade continues only where a revalidation itself changes content. An artefact new in the pull request counts as revalidated. Changing an artefact's own anchor list also requires a revalidation, because the artefact now claims different grounds. **Removing** an artefact — deleting it, or moving it out of the declared places — turns its dependants' anchors dead (point 7); what a component's own status values mean for an artefact that stays in place is the component's decision.
   - **The whole-repository check** checks every artefact against the current history with the rule in point 5.
   - Either runs locally on demand. A pull-request result depends on the base it is compared against, so **friction results are valid only against an up-to-date base**: the check reports, as far as the repository it runs in can tell, when the base has moved on, and a project that enforces friction requires branches to be up to date, or merges through a queue that re-runs the check on the merge it is about to make.

   Clearing friction means revalidating. *How* to revalidate belongs to the component that owns the artefact. A pull-request description may *render* the artefacts' answers — a work-tracking component may build its own documentation-impact section from them — but the check reads the artefacts, never the description, so it works for a pull request from any tool, with no description at all, and locally.

7. **Dead anchors are errors, never silence.** A path that matches nothing (or only excluded paths), or an identifier that does not resolve, is an error. When no installed component resolves a kind, that is reported separately from an identifier that does not resolve. Dead anchors are reported by both checks and by validation. Excluded paths, such as generated or vendored code, are ignored for anchoring and for the measures in point 8. An anchor broad enough to match most changes is warned about, because it would make every change a revalidation and teach people to update markers blindly.

### What is reported, and what fails

8. **Two measures, not failures.**
   - **Unanchored artefacts**, within the declared places.
   - **Uncovered surface:** paths within the *declared surface* that no artefact anchors to. The declared surface is what a component (in its package metadata) or the project (in the backbone configuration) says ought to be described.

   Both are reported and neither fails a check. Friction alone reads zero where nothing is anchored yet; these two measures show what remains.

9. **Debt is derived from git, never kept in a ledger.** *Deferred* debt originates at the deferral point; *stale* debt originates in the first commit that changed an anchor after the revalidation point. A debt listing shows both with their author, date and change, oldest first. Deriving them walks each artefact's file history back to the oldest point in question — per file, and no further.

10. **A tool-written status, on separate lines.** The block may carry a **`last-check`** sub-block that only the after-merge job writes: the state found — `current`, `stale` or `deferred`, where stale wins over deferred — the commit it was checked against, and where any staleness came from. It exists so that the debt is visible in the file and in git history, dated with its commit so it is never read as "true now". It is never read for friction — the check always recomputes. It is named for what it is rather than *status*, which is the defining component's own lifecycle field. It is written only when it changes, by a job the project runs after merges to its default branch, through one small reviewed change kept open and updated in place; that change passes the change check because the sub-block is inside the container and so is not content. The change check itself writes nothing, so branches see neither churn nor conflicts. Tool-written and people-written data sit on different lines, so they rarely conflict. The project configures when the job runs, including never.

11. **Truth-chain order.** Friction is reported upstream first, following the anchors between artefacts, so that what others depend on is revalidated first.

12. **Warning or enforcing, and who owns which finding.** The checks are read-only.
    - **The change check finds:** friction of the pull request, dead anchors of the pull request, a bump with nothing behind it, and an outdated base. In **warning mode** it reports them and passes. In **enforcing mode** it fails on the first three; an outdated base is reported, never failed, since the fix is to update the branch and run again.
    - **Reported only, in every mode:** the two measures, over-broad anchors, kept deferrals and their age, the whole-repository check's findings — it does not fail other work on friction that was already there.
    - **Validation owns:** a malformed block, a dangling deferral, a cycle between artefacts, an invalid mode value, a settings path outside the repository. These fail validation wherever the project runs it, in either mode, because the project can fix them.

    The check only becomes binding when the project makes it a required status in its continuous integration. That is the project's choice. An invalid mode value is a validation error, so enforcement is never switched off silently.

### Commands and settings

13. **Commands.** Everything this functionality does is reached through one command group named for it. Reading commands — the two checks, the debt listing, an explanation of one artefact's friction — never write. Writing is always a separate, explicit command that names what it writes: revalidate, defer, record the status. No writing happens as a side effect of checking — one operation per command, as the command-line design rules require (COR-004).

14. **Project settings.** This record owns one key in the backbone configuration (COR-048), named for the functionality. It holds the friction mode (default: warning), when the status job runs (default: never), the project's own anchored places, its declared surface, and its excluded paths (all default: none). The key is written by the project's own edits, or by backbone configuration commands under COR-048's consent rule. Validation checks that every path in it stays inside the repository.

15. **Dormant until used.** Where no artefact declares anchors, the check finds nothing and demands nothing.

## Rationale

**Why declared anchors, not inferred ones.** Inferring what a description is about, from filenames or text similarity, is guesswork that fails silently in both directions. A declared anchor is a claim someone made and can be checked. Where declarations are missing, the unanchored measure says so honestly.

**Why a timestamp whose point comes from git.** A commit identifier cannot be written into the commit it identifies. It also disappears from the main history on a squash merge or rebase. A content hash of the anchored inputs conflicts on every parallel change under a glob, and nobody can read it. A timestamp is readable and changes on every revalidation, while the commit that last changed it is exactly the point git can answer questions about.

**Why the answer lives in the artefact.** A pull-request description is one tool's format: another tool, a hand-made pull request, or a local run has none. Working from the diff alone needs nothing but the repository, and it puts the justification next to the thing it justifies, where the next reader finds it.

**Why an outcome is stored even though it is derivable.** It is a presentation layer: a reader of the file, or of its history, sees what the last revalidation found without running anything. It is not memory; staleness is always recomputed, so a wrong outcome misleads nobody about the state of the artefact. Requiring the justification to change each time is what keeps `unchanged` from becoming a rubber stamp.

**Why deferrals are per anchor and are re-stated on revalidation.** A deferral is a judgment about one anchor's change; a later change to the same anchor is a new question. Several reasons coexist and merge cleanly because each has its own line. Nesting them under the revalidation says what they are — postponements *since* that revalidation — and re-stating them makes every revalidation look at what it is still postponing.

**Why debt comes from git, not a ledger.** A ledger duplicates what git already answers and drifts from it whenever a change bypasses the check. The tool-written status is not a ledger: it is a dated snapshot for visibility, recomputed rather than trusted.

**Why the pull-request rule is local to the pull request.** "An anchor changed here, so the answer is here" explains itself to the author at the moment the fix is cheapest. The whole-repository check uses the same notion of "changed since the revalidation point", so the two agree after merging.

**Why the revalidation point follows the parsed value.** If formatting or file moves could advance the point, friction could be cleared without anyone revalidating. The point must move only when someone deliberately revalidates — and where a move could hide history, the move itself must revalidate.

**Why the container is not content.** The after-merge job, another functionality's block, a role's bookkeeping about the artefact: none of them changes what the artefact says. Excluding the container is what lets the job write without waking every dependant, and what keeps the change check from flagging its own bookkeeping.

**Why uncovered surface is declared, not everything.** Counting every file in the repository as needing description would make the measure pure noise on day one. The measure means something only against a surface someone has said ought to be described.

**Why dead anchors are errors.** A glob that matches nothing produces no friction, for ever. Silence would look like health.

**Why it is core.** Three kinds of component need it: those describing what the system must do, those keeping documentation true, and those checking whether a change owes documentation work. They must not depend on one another. Core is the only home that serves all three without one depending on another or each carrying its own copy. Its consumers are known, not speculative, so the usual wait for a pattern to recur before extracting it (COR-007) is not applied here. The mechanism names no discipline, so it makes sense in any project. Its first use needs no capability at all: an architectural decision record (COR-025) can anchor the code it governs today. Where nothing is anchored, it is dormant.

### Alternatives considered

- **Anchors on every statement inside a document.** Rejected. Precise, but the maintenance cost makes people stop, which recreates the drift. Precision comes instead from whoever revalidates the flagged artefact against the actual change.
- **Anchors per section, via markers inside the prose.** Rejected. It adds a second convention, parsed out of prose.
- **Storing each artefact's current-or-stale state as truth.** Rejected. Stored state duplicates what git already answers, and it drifts from git whenever a change bypasses the check. The tool-written status is a dated snapshot, not truth.
- **A commit identifier or a content hash as the marker.** Rejected; see Rationale.
- **Reading the answer from the pull-request description.** Rejected; see Rationale.
- **A bare marker change as an answer.** Rejected: it is indistinguishable from a blind bump; the justification, changed each time, is the answer.
- **A debt ledger, in one file or one file per entry.** Rejected. It duplicates git and drifts.
- **Recording stale debt as synthetic deferral entries.** Rejected. Deferral is deliberate postponement; stale debt is shown by the tool-written status instead, so the two are never confused.
- **Keeping either timestamp on a conflicting revalidation, the merge becoming the new point.** Rejected in favour of revalidating the combined state; the merge would claim a revalidation nobody made.
- **Organising the block per anchor, or splitting it strictly by writer.** Rejected. The first puts the tool and people on the same lines; the second adds a level that carries no meaning.
- **One copy per component.** Rejected. Separate engines drift apart, and the components would disagree about what is stale.

## Implications

- **The backbone ships the friction checks** — the change check and the whole-repository check, each runnable locally — reading the blocks in the declared places. Its output includes a machine-readable form, so that other components can consume friction, uncovered surface and the artefacts' answers.
- **The backbone ships the schema** for the block, for single documents and collection entries. It is a surface change adopters can see, and existing documents are unaffected.
- **The backbone ships the writing commands** for revalidating, deferring and recording the status, and the after-merge status job a project may wire in.
- **Components that keep anchored artefacts** declare their places and surface in their own package metadata. They register their own anchor kinds and resolvers, and define how their artefacts are revalidated — including how their own revalidation vocabulary maps onto the two outcomes here. They may also decide what to do when a revalidation finds that the description was right and the change was wrong. A work-tracking component may render the artefacts' answers into its pull-request format; it reads the machine-readable output for that, and its own obligations are met by the artefacts' answers, not by the rendering.
- **Continuous integration** needs enough history to reach the oldest revalidation or deferral point for the whole-repository check and the debt listing, per file. The change check needs only the diff and an up-to-date base.
- **The backbone configuration** gains the key from point 14.
- **The status report** can show friction, unanchored artefacts and uncovered surface.
