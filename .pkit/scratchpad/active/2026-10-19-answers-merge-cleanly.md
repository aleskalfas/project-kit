---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-10-19
---

# Answers merge cleanly — two pull requests that answer on one document both land

A design for #1779. Today a change's answer on a stale document is written in that document's front matter. Two open pull requests that answer on one document edit the same lines there. Whichever lands second is then in conflict, and GitHub runs no checks on it until someone merges the base in by hand. This note weighs where an answer could live instead.

- **Raised by:** 18 October. Every one of the 35 pull requests merged that day needed at least one merge round, 94 in all.
- **Read from main at `e673bf03`:** the records, the code and the counts below.
- **Citations:** records by permanent id and point, code by file at `e673bf03`.
- **Reviewed:** by the architect, the critic on its recommendation, the architect again on the critic's points and the replay of 18 October, and the critic on the revised recommendation. Their findings are in "Review".
- **Decided:** not yet. The decision is in "For the maintainer".

## The question

Where does a change's answer live, so that two changes answering on one artefact merge with no conflict, on a host that runs no tool of ours?

## In short

- **The cause.** Two revalidations of one document rewrite the same three lines of its front matter. The host merges with plain git, so they conflict, and no tool of ours can step in there.
- **The only fix on the host.** Each change writes its answers into a new file of its own, which no other change writes. Git never conflicts on two new files.
- **The recommendation (A1, the architect's, after review).**
  - **The file.** A change's answers go in one new file of the change's own, not in the document. Each answer names the other answers on that artefact that it read.
  - **What stays in the document.** Its anchors stay in its front matter.
  - **A combined state.** Two answers made apart on one artefact are reported as debt until the next answer reads both, instead of forcing a merge round.
- **What it removes.** On 18 October, 38 of the 51 conflicting rounds lay only in answers. It also removes the clean rounds the landing command forced because the base had touched an answered file. Anchor lists and bodies still conflict.
- **What it costs.** A new core record partially supersedes COR-050, and refines points 6 and 9 beside it. Answers move once, by a migration, and project-management's landing command reads the new files.
- **Beside it.** A short CI run for a head whose only changes are answers, as its own change, with the maintainer's leave.

## What happens today

- **The answer's lines.** A revalidation rewrites the `revalidated` block's `at`, `outcome` and `unchanged-because` (COR-050 point 3). So any two revalidations of one artefact conflict. A deferral (point 4) and a revisit entry (point 16) leave `at` alone.
- **The lists.** Deferrals and revisit entries are kept sorted by anchor. Two changes merge cleanly there only when their entries land apart, with an untouched line between.
- **What the host asks.** The main branch's ruleset requires the `checks` status and a linear history, but not an up-to-date branch. So a pull request with no conflict merges on the checks it already has.
- **What the landing command asks.** It refuses to land when the base changed any file that carries one of the change's listed answers since the head left it, conflict or not (project-management DEC-055 point 3, `_refuse_moved_base` in `land-work.py`). It reads the whole file, so a base edit to the document's body forces a round too.
- **A round.** Merge the base in, run `pkit friction resolve` (it takes the base side's answer), revalidate again, push, wait for checks. DEC-055 point 3 covers the new head, so the person is not asked again.

### 18 October, replayed

Each merge of main into the 35 branches merged that day was merged again with `git merge-tree`, from the commit's two parents. The conflict markers were then placed in front matter or body.
- **94 rounds.** Every pull request had at least one.
- **43 merged cleanly.** The landing command's firm stop forced them, or the branch was brought up to date by choice. Git alone cannot tell which.
- **51 conflicted.**
  - **38 only inside answers** in front matter: `at`, `outcome`, `unchanged-because`, deferral or revisit lines.
  - **3 in anchor lists**, with no conflict in a body.
  - **10 reached a body**, of prose or code.
- **20 files.** The answer conflicts fell on 20 files. The most frequent:

  | File | Rounds |
  |---|---|
  | `.pkit/cli/README.md` | 22 |
  | `.pkit/capabilities/software-analysis/README.md` | 20 |
  | `.pkit/agents/README.md` | 8 |
  | `.pkit/lifecycle/README.md` | 7 |
  | `.pkit/capabilities/living-docs/README.md` | 7 |
  | `CONTRIBUTING.md` | 6 |
  | `tech-docs/analysis/use-case-model/actors/ACT-ci-pipeline.md` | 6 |

- **Two hub documents are not the cause.** Only 8 of the 51 conflicting rounds had every conflicted file among the CLI reference and the lifecycle README.

### What the conflict buys today

The conflict also makes the second change answer for the combined state, as COR-050 point 3 asks of whoever resolves it. That protection is partial:
- **It holds only when both changes revalidated.** A change that edits a document's body without answering on it merges cleanly beside one that answers. Nobody judges the combined state then.
- **It does not always guard a parallel deferral.** Where the block already holds a `deferred` list, a new deferral on one side merges cleanly beside a revalidation on the other (probed below). Under a squash, the revalidation's point then reaches the deferral, so it answers no friction (point 4), though nobody judged it. In project-kit the landing command's firm stop catches it, since both edits are in one file.

## The constraint every option meets

The host merges with git's own merge, on its side. It never reads a clone's git configuration, so it runs no merge driver a clone registers. In one file, git merges two changes cleanly only where their edits sit apart, with untouched lines between. Two revalidations of one artefact edit the same three lines.

So on the host, the only answer that never conflicts is one written to a path no other change writes.

Probed with `git merge-tree` (git 2.49) on trees alone:
- **Each side adds a file of its own:** clean.
- **Each side rewrites the block in the document:** conflict.
- **One side removes an old file, the other adds its own:** clean.
- **Each side removes one old file and adds its own:** conflict, *rename/rename*. Git pairs a removed file with a similar added one as a rename. A revalidation that re-states a kept deferral makes the two files alike.
- **Each side takes the same lines out of the document and adds its own file:** clean. The two edits to the document are identical.
- **A revalidation on one side, a new deferral on the other, where a `deferred` list exists:** clean, whether the new entry sorts before or after the kept one.

So a change that answers in a file must only add files. Removing old ones is a separate change.

## The options

Each option is read under the same six labels: what it is, what it keeps of COR-050 point 3, the records it changes, the migration it needs (COR-010), what it costs adopters, and how it behaves when the host merges with no tool of ours. E and F were added by the architect's review.

### A. Answers in a file of the change's own

- **What it is.** A change writes its answers into one new file whose name no other change uses, such as `.pkit/project/friction/answers/<random>.yaml`. That covers revalidations, deferrals and revisit entries. The artefact's block keeps its anchors, `unanchored-because` and `last-check`. The change check reads the file the diff adds. A change that answers only adds files.
  - **A1, the file is the answer's home.** It stays until later answers on each of its artefacts supersede it. A separate change, run by a command or a job, removes what is superseded.
  - **A2, a staging file, folded later.** A job run after merges moves landed answers into the artefacts' blocks and removes the files. The move writes no new answer, since each value keeps the point where it was first carried.
- **COR-050 point 3.** The answer is still the change's, in its own diff. The reviewer still works from the change check's list, which reads the file. The person is still told the `updated` sentences, as DEC-055 writes them. Lost: the answer beside the artefact's text (in A1), and the forced answer for the combined state (in both). "What answers in files of their own must settle", item 2, turns the second into a finding.
- **Records it changes.** A new core record partially supersedes COR-050. It overturns where the lead puts an answer (keeping "never in a pull-request description"), points 3, 4 and 16 on where answers live and on conflicts, and the Rationale "Why the answer lives in the artefact". It also reaches:
  - COR-050 point 5 (the folder lies outside what any anchor stands on, as the container does), points 7 and 8 (outside the measures), 9, 12 (new findings), 13 (the writers' target, a prune command) and the Implications.
  - COR-051 point 2, for rules that arrive by sync (below).
  - Project-management DEC-055 point 3 and its rationale: the cover's unit and the firm stop read answer files.
  - ADR-057 point 2 gains one home, where an artefact's answers are. A new ADR records project-kit's realisation.
  - A2 also changes point 10 and point 3's rule that no after-merge job writes an answer. ADR-055 point 5 rejected after-merge writes in project-kit, since the hot documents are shipped trees.
- **Migration.** A backbone migration moves every artefact's `revalidated` and `revisited` into answer files, one per artefact, keeping each parsed `at`, so no revalidation point moves. The architect prefers this to draining, where readers accept the old block until each artefact's next answer takes it out. Draining keeps two homes in every reader for as long as some artefact is never answered again.
- **Cost to adopters.** A new folder the project owns. A command or job that removes superseded files, or the folder grows by one file per answering change. One large mechanical diff at the upgrade. Readers that parse `at` from front matter must switch to the backbone's machine-readable output. Software-analysis is one: its `_revalidated_on` reads `REVALIDATED_AT` from the file. `pkit friction resolve` loses its work. `pkit friction since` keeps its role for DEC-055's cover, as a check on paths: only answer files this branch added changed.
- **On the host.** New paths no other change writes never conflict. With the firm stop retargeted to answer files, which the base never changes, a pull request keeps its checks and lands, with no round. In A2, the fold needs the job. Without it, A2 is A1 with two homes.

### B. A merge driver for the friction block

- **What it is.** `.gitattributes` names a driver for artefacts' files. `pkit init` and `pkit sync`, or the adapter, register it in each clone's git configuration. The driver makes `friction resolve`'s decisions inside `git merge`.
- **COR-050 point 3.** All kept, as long as the driver leaves the answer for the combined state to the change. It cannot write that answer itself, since point 3 rejects an automatic merge. So the change still owes a new answer after every merge.
- **Records it changes.** No core record. It is backbone or adapter tooling. `.gitattributes` goes through the merge primitive (core rule 6).
- **Migration.** None. It is an addition.
- **Cost to adopters.** Every clone registers the driver, CI runners included. A clone without it gets the plain conflict. The registration is not versioned, so it drifts.
- **On the host.** The host runs no driver. The pull request still shows a conflict, and no checks run. Someone merges locally and pushes, and the checks run again. The round stays. It saves one command a round.

### C. Answers outside the document until the change lands, or written by the merge

- **What it is.** Three forms:
  - **C1:** answers in the pull request's description, or in commit trailers that a squash carries into its message.
  - **C2:** answers staged in a file on the branch, folded into the document by the landing command just before it merges.
  - **C3:** answers written by the merge itself.
- **COR-050 point 3.** C1 breaks it: point 3's rationale and Alternatives reject reading an answer from a pull-request description. A host builds a squash message as it is set up to, and a message edited by hand drops trailers silently. C2 and C3 keep it.
- **Records it changes.** C1: COR-050's lead, Rationale and Alternatives, and DEC-055 point 4, which reads nothing from the description. C2: DEC-055 points 2 and 3. C3: COR-050 point 3, and the host's rules.
- **Migration.** C1 moves every answer out of the tree. C2 and C3 need none.
- **Cost to adopters.** C1 ties friction to one host's merge settings. C2 adds a commit at every landing. C3 needs a bot that merges locally and pushes, which a ruleset requiring pull requests refuses.
- **On the host.** C1 merges cleanly, if the host keeps the trailers. C2 makes a new head, so checks run again, and a landing in that window conflicts with it. The round moves rather than goes. C3 is not possible, since a merge on the host writes no files.

### D. Fewer documents that everyone answers on

- **What it is.** Project-kit splits its CLI reference and its lifecycle README into separate pages, each anchoring less. Separate files, not collection entries: the landing command's firm stop reads whole files, so entries of one file would still force a round.
- **COR-050 point 3.** All kept.
- **Records it changes.** None, but the pages are shipped trees. They are cited from the core rules, from records, from skills and from the CLI's help text, so the split is a surface change with a backbone changeset (PRJ-002). Each anchor on their sections is re-pointed with a revalidation (COR-050 point 6).
- **Migration.** None. Adopters' own links into those sections break silently.
- **Cost to adopters.** The broken links above. Project-kit restructures two documents and the anchors on them.
- **On the host.** Fewer conflicts, not none, and fewer than it looks. The answer conflicts of 18 October fell on 20 files, and only 8 of 51 conflicting rounds lay wholly in these two. The hot spot also moves:
  - **Shared code.** Every page that anchors `src/project_kit/cli.py`, which holds every command, is flagged by each change to it.
  - **Siblings.** A page anchoring `.pkit/cli/**` leaves out only its own file, so every edit to a sibling page flags it.
  - **A shared index.** The table of commands lands on one page, which every new command changes.

### E. A short CI run for a head whose only changes are answers

- **What it is.** When every head since the pull request's most recent full run changed only answers, and that full run passed, CI runs `scripts/check.sh` without its test step. A clean merge of the base counts as no change. The full run's head must lie on the new head's first-parent line, which `pkit friction since` already requires. The short run is for `pull_request` events only, never `merge_group` or `push`.
- **COR-050 point 3.** All kept. The round still judges the combined state.
- **Records it changes.** No core or capability record. An ADR, or a refinement of ADR-055 point 5, records project-kit's CI policy. Project rule 2, "the full suite is the pre-push hook's and CI's", is reworded, and the ADR says what the pre-push hook does.
- **Migration.** None.
- **Cost to adopters.** None. It is project-kit's CI.
- **On the host.** The round stays, but takes minutes rather than about 20. It changes what the required status means: a head's own full run is skipped, though its combination with the base was never tested before either. So the maintainer authorises it. How CI reads "the most recent full run" from the Actions app's own check run, and tells short runs from full ones, belongs to the ADR.

### F. A narrower firm stop in the landing command

- **What it is.** The landing command refuses only when the base changed something inside the `revalidated` blocks or `revisited` lists of an artefact the change answers on, not anything in its file. That needs a backbone reading, the inverse of `pkit friction since`, in the same home. (The first draft said "the text of a listed answer or a kept deferral". The critic showed that misses a parallel deferral the base wrote.)
- **COR-050 point 3.** All kept. The list still shows the words that land.
- **Records it changes.** DEC-055 point 3's firm stop and its rationale, refined in place.
- **Migration.** None.
- **Cost to adopters.** A backbone changeset for the reading, and a project-management one that sets `requires_backbone: release` (PRJ-002 D4).
- **On the host.** Rounds forced by a base edit to a document's body go. Rounds forced by two revalidations stay. Under A1 it is wasted work, since the stop then reads answer files.

### Not options

- **A merge queue.** It builds the merge it is about to make, so it cannot build one that conflicts. It fixes the outdated base (ADR-055), not this.
- **One answer per anchor inside the block.** COR-050 rejects organising the block per anchor. A broad anchor makes many changes answer on one anchor anyway, and two entries inserted at one place still conflict.
- **A list of answers in the block, one entry per change.** Two entries inserted at one place conflict. Any order that spreads them collides by chance.
- **`merge=union` in `.gitattributes`.** It is built into git and needs no registration. But it applies to a whole file, so it would join body conflicts and repeat YAML keys. Whether the host honours it is unverified.
- **Planning around it.** The batch planner could run tasks on one hot document one after another. That gives up the parallel work, and stacking the branches does not help: after a squash, the `at` lines still conflict.

## What answers in files of their own must settle

Option A removes the conflict, and with it the forced answer for the combined state. The record that takes it must settle these. The critic's second pass found items 1, 2 and 5 wrong as first drafted. They are reworked here, and are checked again in the record's own review.

1. **What an answer read: `supersedes`.** Each answer names the other answer files on its artefact that it read. The critic proposed it, and the architect adopted it over the alternatives below.
   - **What it must name.** Every other answer file on the artefact present in the tree of the change's own head, live or not. That tree is the branch's head, not the merge the host builds. So an answer that lands on main in parallel never fails the branch's checks.
   - **A merge of the base.** A branch that merges the base in takes on the answers the merge brings, as COR-050 point 3 asks of whoever merges today. A stacked branch names its parent's file.
   - **Present, not only live.** Naming only live files would bring a superseded answer back to life when a middle answer goes. In a chain X, Y, W, reverting Y or pruning it would revive X beside W.
   - **What it replaces, by kind.** A revalidation replaces the revalidations it read, and every deferral it read that it does not re-state. A deferral or a revisit entry replaces only the entry on its own anchor that it read. So an answer that only defers need not re-state a revalidation to keep it.
   - **Names that history agrees with.** The whole-repository check honours a name only where the named file was added in an ancestor of the commit that added the naming file. Any other name is void, and what it named stays live, toward more friction. A cherry-pick to a release branch then reads correctly. So the check verifies `supersedes` from git, and it is no ledger (point 9's Rationale).
   - **Point 4 through what was read.** A revalidation reaches a deferral only where it read the file that holds it, not by ancestry. Under a squash, ancestry would let it reach a parallel deferral it never saw.
   - **Rubber stamps.** An `unchanged-because` must differ from every reason the answer read (point 3), and a revisit entry's reason from the one it replaces (point 16).
   - **Not taken:** a revalidation that names the deferrals it drops, and `based-on`, where each answer records the default-branch commit it was answered against. `based-on` is a claim about ancestry that the check could not verify from the tree.
2. **Answered apart, as a finding.** Two live revalidations on one artefact, neither of which read the other, were made apart. Nobody judged their combined state.
   - **Any two, not only those on one anchor.** Telling that both changes moved one anchor needs each change's bounds, and a rebase-merge or a direct push loses them. It would also miss two `updated` edits whose bodies merge cleanly. So every such pair is a finding.
   - **Reported, then cleared by the next answer.** The whole-repository check reports it as debt, in its tracking issue (ADR-055 point 5). The next answer on the artefact reads both, judges the combined state, and clears it. The judgment a round forces on the second change to land moves to the next change that answers.
   - **Staleness measured as today.** With two live revalidations, an anchor has changed only where it differs from what it stood on at each of them, point 3's rule for points on lines apart. The finding, not staleness, carries the unjudged combined state. The Rationale's "Where the two checks part" gains these cases.
   - **The person is told.** The landing command derives the finding against the base's tip, not the fork point, and prints it before it stops ready (COR-050 point 3, DEC-055 point 3).
   - **Not a stop, to start with.** Whether the landing command stops on it is the project's choice under DEC-055. A stop would bring the rounds back.
   - **18 October.** Each of the 38 rounds that conflicted only in answers would instead have left this finding on its artefact, until the next answer there.
   - **The test of criterion 2.** Two pull requests answer on one document, apart. The second's checks run again after the first lands. Both land with no conflict and no round, the finding is reported, and a third answer that reads both clears it.
3. **The revalidation point across homes.** A value first carried in the old block, or in an answer file, keeps its point when it moves. The migration, reverts and write-backs rely on it.
4. **Add-only, as a check finding.** A change that answers only adds answer files, so git never pairs them as a rename. The change check fails one that also removes one. A revert that owes a new answer is the stated exception.
5. **Reverts and pruning.** An answer names every file present, so a revert or a prune revives nothing a later answer read. Pruning removes a file once every artefact it answers has a landed answer that read it. Reverting the only answer that read a pruned file leaves the artefact unanswered: an over-report, toward more friction, which the record states. Reverting a prune puts back values carried before, so they keep their points (item 3). History is read back to where the artefact was last added, not its answer file.
6. **The folder lies outside every anchor.** A path anchor such as `.pkit/**` must not stand on answer files, or each answer flags it and its own answer adds another file. The folder lies outside the measures and the declared surface too. It sits on the project-owned side, named for the functionality, as a literal of the distribution. It is never a place, never synced, and no setting moves it (COR-048 point 2).
7. **Never code, for review.** Project-management counts a `.yaml` file as code unless `review.floors.not_code` lists it, and its default lists only `.changes/**` (DEC-032). Unlisted, every answering change would pull in the code-review panel, and every push that changes only answers would stale its approvals (DEC-028). So the default gains the answer folder.
8. **Rules that arrive by sync.** A method rule set an adopter receives is an artefact there (COR-051 point 2), and today it carries its source's answers. With answers in the source's own folder, the adopter would owe answers on rules it does not own. The architect prefers asking no answer of a synced artefact, as for an excluded path (COR-050 point 7). This is open. Either way, a project never answers on a file it does not own.
9. **Failure, moves and whose file.**
   - An answer file that does not read answers nothing and is a validation error.
   - An answer whose artefact moved in a parallel change is reported, not failed, and the debt shows. `supersedes` follows a move, or a moved artefact's old answers could never be pruned.
   - A writer writes only into a file it can tell is its own. Two uncommitted answers on one artefact are refused.
   - A collection entry's answer names `path#id`.
10. **The upgrade's own costs.** Branches open at the migration conflict once each. The record's *Partially superseded* line sits in COR-050's preamble, which every point of it stands on. So it flags once every dependant of an anchor on a COR-050 point, and those are answered the old way.
11. **What still conflicts.** Anchor lists and bodies. On 18 October that was 13 of the 51 conflicting rounds, all real content conflicts. A1 removes neither kind.
12. **A gain for adopters.** Answers leave the shipped files. So a revalidation in the methodology's source no longer changes a file adopters receive. That ends the churn COR-050's Rationale describes, where each sync that brings a revalidation flags the path anchors on the synced file.

## Review

### The architect, first

It recommended D, as separate files, with E, and F as optional, keeping A1 as a successor design. What it found in the first draft, folded into the sections above:
- **The landing command's firm stop also forces rounds,** for any base edit to an answered file.
- **"Guards a parallel deferral fully" was overstated.** Probed: it merges cleanly today where a `deferred` list exists.
- **Smaller corrections.** "Every answer rewrites those lines" held only for revalidations. The software-analysis sentence was backwards: it reads `at` from the file, so it must switch. `friction since` keeps its cover role under A.
- **A's records were incomplete,** and A2's missed point 3's rule on after-merge jobs and ADR-055 point 5.
- **A missed** the folder under path anchors, rules that arrive by sync, add-only as a finding, reverts of a prune, stacked branches and a stored base commit.
- **A precedent.** Software-analysis keeps revalidation records one file each, as held documents. A1 would be a second instance of that shape (COR-007), and the two should not diverge.

### The critic, on that recommendation

Its verdict: do not show it to the maintainer as it stands. Its red flags, each answered:
1. **E could hide a failed full run.** Keyed on the last green head, a clean base merge whose full run fails, then an answer-only push, would pass the short run. *Answered:* E now keys on the most recent full run, which must have passed, and never runs on `merge_group` or `push`.
2. **D was untested against shared code, siblings under one glob and a shared index,** and its cost was not counted. *Answered:* the replay confirms it. D would have removed at most 8 of 51 conflicting rounds. D is dropped.
3. **F as worded reopened the parallel-deferral hole.** *Answered:* F reworded. F is dropped if A1 is taken.
4. **The recommendation failed the issue's criterion and did not say so.** A successor design with no issue filed is a deferral with no open follow-up. *Answered:* the recommendation is now A1, decided now.

Its gaps and weak reasoning, answered:
- **The rounds were not broken down by cause.** *Answered:* "18 October, replayed".
- **E's gates were the builder's list.** *Answered:* E now runs `check.sh` without its test step, keeping every check that reads the diff.
- **Wrong citations.** COR-007 points to the structural fix, after three patches for one cause in two days (#1689, #1728, #1779). A1 adds one home to ADR-057 point 2 and breaks none. A1 is cheapest now, while friction is three weeks old.
- **`based-on`** is a stored claim the check would trust to clear friction. *Answered:* replaced by `supersedes`.
- **Counter-alternatives.** It offered `supersedes`, the combined state kept as a finding, and E fixed as its own change. All three are taken.

### The architect, again

It switched to A1, decided now, with E fixed as its own change, D dropped and F dropped if A1 is taken. Its reasons:
- **D cannot do the job.** The answer conflicts fall on 20 files.
- **A1 removes most of the rounds.** It takes away the 38 rounds that conflicted only in answers, and the firm stop's clean rounds. What is left is 3 anchor conflicts, 10 body conflicts and updates taken by choice.
- **COR-007 now points to the structural fix,** and A1 is cheapest now.

Where it holds the critic wrong or incomplete:
- **E is no boundary in the wrong layer.** Wiring a backbone mechanism into project-kit's own CI is what ADR-019 point 2 expects of a project. E does change what the required status means, so the maintainer authorises it and an ADR records it.
- **"One known front-matter reader"** leaves out synced method rule sets in adopters, the hardest sync question A1 settles (item 8).
- **Prune lag** was missing on both sides (item 5).

Its escalation: A1 needs the maintainer. It overturns COR-050's headline decision, turns point 3's merge-time rule into reported debt, reaches every adopter and needs a migration. E separately needs his leave to change what the required check means.

### The critic, on the revised recommendation

Its verdict: not yet, for three fixes, each a few sentences of design. All three are folded into "What answers in files of their own must settle", and the record's own review checks them again.
1. **Checking `supersedes` against the change check's base brought the round back.** In CI that base is main's tip, through the merge ref, so a parallel answer that landed would fail every later run of the branch. *Answered:* an answer names what the tree of the change's own head holds (item 1).
2. **Naming only live files brought superseded answers back to life** when a middle answer was reverted or pruned. *Answered:* an answer names every file present, live or not (items 1 and 5).
3. **The combined-state finding was narrower than the decision sentence said.** "Both changes moved the same anchor" cannot be told after a rebase-merge or a direct push, and it misses two `updated` edits whose bodies merge cleanly. *Answered:* every two revalidations made apart are a finding, cleared by the next answer that reads both (item 2).

Its gaps, answered in the same section:
- **Two live revalidations:** how the whole-repository check measures them.
- **Point 4's "reaches"** read through what an answer read, not ancestry.
- **An answer that only defers** replaces nothing but its own anchor's entry.
- **The rules against rubber stamps** defined in a new file.
- **`supersedes` as a stored claim:** each name is verified against history.
- **Cherry-picks and stacked branches.**
- **The review floors** that would count answer files as code.
- **The person told** of the finding before the ready stop.
- **The upgrade's own costs.**

It also named a gain the note had not claimed: no more sync churn for adopters (item 12).

On the decision sentence, it asked that the maintainer be told three things:
- **Which other records it reaches.** COR-051 point 2, point 9's Rationale and point 6's advice on an up-to-date base.
- **What "never conflict" covers.** Only the answers: anchor lists and bodies still conflict.
- **What A1 relaxes in point 3.** A1 keeps what #1779 asks of COR-050 point 3: the answer is the change's, and a reviewer checks it. It relaxes the point's rule that whoever merges two answers judges their combined state.

## Recommendation

1. **A1, decided now.**
   - **The files.** Answers go in add-only files of the change's own. Each answer names, in `supersedes`, the answer files it read. Two revalidations made apart are reported as a finding, not a stop.
   - **The record.** A new core record, authored through `decision-author` and reviewed by the critic and the architect, partially supersedes COR-050.
   - **The issue.** #1779 carries the build, its migration and the test of its criterion 2. The core record, once accepted, is the first slice.
2. **E, as its own change, now.** It brings relief while A1 is built. Whether to keep it after A1 lands is revisited then.
3. **D is dropped** from this issue. The CLI reference's breadth is a separate question, worth taking up only if a replay shows it helps.
4. **F is dropped,** since A1 retargets the firm stop.

What changes, if the maintainer takes A1:
- **Core records.** A new core record partially supersedes COR-050. COR-050 stays accepted, its top line reads *Partially superseded by …*, and the new record sets no `supersedes:`. What it overturns:
  - the lead's clause that the answer lives in the artefact, keeping "never in a pull-request description"
  - where points 3, 4 and 16 put answers, and their rules on conflicts
  - point 3's rule that whoever merges two answers judges their combined state, which becomes a reported finding
  - point 4's "reaches", read through what an answer read
  - the Rationale "Why the answer lives in the artefact"
- **Refined beside it.** COR-050 point 6 says the change check judges `supersedes` against the change's own head, in a merge ref or a queue merge too. Point 9's Rationale, "Why debt comes from git, not a ledger", says each name is verified against history. COR-051 point 2 is refined if a receiving project asks no answer of a synced rule, which is still open.
- **Capability records.** Project-management, refined in place:
  - DEC-055 point 3: the cover's unit and the firm stop read answer files, and the landing command prints the answered-apart finding.
  - DEC-032: the not-code default gains the answer folder.
- **ADRs.** ADR-057 point 2 gains the answers' home and the rule for points across homes. A new ADR records project-kit's realisation: the file naming, the prune command and where it writes, landing and CI. E has its own ADR.
- **Capabilities.** Software-analysis reads `at` through the backbone and declares the backbone it needs. Living-docs changes its wording.
- **Migration.** One backbone migration moves every answer eagerly, one file per artefact, keeping each `at`.
- **Changesets.** The backbone, project-management and software-analysis each declare one (PRJ-002).

## For the maintainer

**The decision:** should a new core record partially supersede COR-050, so that a change writes its answers in an add-only file of its own instead of the artefact's front matter, and two answers made apart are reported as debt rather than forcing a merge round?

Recommended: yes, as A1 above. What you would be agreeing to:
- **Answers no longer conflict.** Anchor lists and bodies still can.
- **Point 3 is kept where #1779 asks:** the answer is the change's, and a reviewer checks it. Its rule that whoever merges two answers judges their combined state is relaxed. That judgment moves to the next change that answers on the artefact, and until then the finding is reported as debt.
- **It reaches more than COR-050.** COR-050 points 6 and 9 are refined beside it. COR-051 point 2 is refined, or left open, for rules that arrive by sync.
- **A migration.** Every project moves its answers once, and each branch open at the upgrade takes one round.

Once that is settled, a second, smaller choice: may CI run a short check, with no test step, on a head whose only changes since a passing full run are answers (E)? It changes what the required `checks` status means, so it is yours to allow. Recommended: yes, as its own change, recorded in an ADR.
