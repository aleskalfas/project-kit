---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-10-12
---

# A document marks an edit that keeps its meaning

A design for #1451. It decides how a document that others anchor marks an edit that keeps its meaning, so that its dependants are not asked to revalidate, here and in every project that receives the document.

- **The starting point:** alternative D of the document-versioning note (`2026-10-08-document-versioning.md`, #1383, PR #1384), and its question 2. The maintainer decided "not now" on 8 October, and reopened it on 11 October: designed before the first adopter.
- **What it works with:** part anchors (#1387, `2026-10-08-part-anchors.md`), the version transition (#1429, `2026-10-10-sync-versions.md`), and COR-051 point 7 as refined on 11 October.
- **Read from main at `a4576af8`:** the records, the code and the counts below.
- **Citations:** records and rules by permanent id and point. Code by file and function.
- **Reviewed:** by the critic and then the architect. Their findings and the answers are in "Review", at the end.

## The question

How does a document that others anchor say that an edit kept its meaning, who decides that, and what do its dependants read, in its own project and in a project that receives it?

## In short

A document others anchor may carry markers that move only when its meaning changes: one for the document, and one for each part whose meaning has changed. Each edit to it either moves a marker or gives a reason why the meaning held. A dependant is asked only about an edit that moved a marker it reads, or that declared nothing.

- **The shape follows `at`'s (COR-050 point 3):** timestamps under `meaning`, and a sentence `meaning.kept-because`, in the document's friction block.
- **The reading stays a comparison of two states,** as COR-050's is: a dependant is asked where its text differs and a marker it reads differs. Only an edit that declared nothing needs the history.
- **An edit that writes neither a marker nor a reason** counts as a change of meaning, as every edit does today. It fails the change check in enforcing mode, and no later reason covers it.
- **The test of a kept meaning:** in the whole document and in each part the edit changes, no claim, term or citation changes, no reading is chosen, no text moves between parts, no heading a reader can name is removed or renamed, and nothing changes whether or how the document binds. Doubt moves a marker, as it does for W3C. The change check refuses a reason beside the structural changes it can see.
- **Who decides:** a person accepts each reason before it is written, since a reason spares dependants that person never sees (question 2).
- **Where it lives:** in the friction block of whatever carries the methodology's container, a document or a collection entry such as a rule. Decision records gain the container for it (question 4).
- **Across projects:** a received document is read by the same rule, at version transitions. Reasons spare a project's artefacts by default only in content of a tagged methodology release, which refuses to ship an edit that declared nothing. A project can narrow that in its friction settings (question 1).
- **What a receiving project sees:** each received reason on the list of the change that brings it, and every reason since its version in the release notes.
- **A wrong reason** is fixed forward: the receiving project revalidates what it doubts and reports it, and the authoring project's correction asks every dependant again.
- **Records:** a new core record holds the document's side, the declaration and the trust (question 6). COR-050 holds the reading, refined in place. It also reopens COR-053 point 10, COR-051 points 2 and 7, core rule 20, the decisions README, software-analysis DEC-001 point 6 and project-management DEC-055.

## Today

### Friction reads a change as a difference between two states

An anchor changed when what it stands on differs between two states (COR-050 point 5). Nothing a target says about its own edit is read.

- **A record anchor** stands on the record's file.
  - **The change check** asks only whether the record's file is in the diff, and treats a rename with identical content as no change (`friction_check._anchor_changed`, `friction_git.DiffEntry.changes_content`).
  - **The whole-repository check** compares the file's object at each revalidation point with the latest commit (`friction_repository._Judge.since`).
- **An artefact anchor** stands on the artefact's content: its body and its own fields, never the container (`friction_discovery.content`, `friction_repository._Judge._target_since`).
- **The revalidation point** is the commit where the artefact first carried the parsed value of `at`. A value written back keeps its old point (`friction_history.Walker.carried`, `Walker.points`).
- **An answer** is `updated`, `unchanged` with a new `unchanged-because`, or a deferral (`friction_check._revalidation`, `_judge`).
- **The change check reads history behind the base** already: to tell a written-back `at` from a new one, and to find a deferral's point (`friction_check._Behind`).
- **The cascade** goes on only where a revalidation changes the artefact's content (COR-050 point 6).

### A person decides every answer

- **The rule:** an answer is a person's decision when that person was shown it word for word and accepted it (COR-050 point 3, core rule 20).
- **Two timings:** an agent may write first the answers the change check asks of its change, and the person who authorises the merge is then shown the change check's list (`friction_check._written_answers`). Every other answer, and every reason for having no anchors, is accepted before it is written. COR-050's rationale gives the second timing to what "waives a measure".
- **The list in a pull request:** project-management writes it into the description, and its landing command holds a merge until the list for that head is there (project-management DEC-055). The hold fires where a change wrote answers or altered the settings that decide what the check asks.

### Where an upstream author's word already acts in a receiving project

- **A shipped rule set's class of change.** A rule set's major moves when a rule is added, withdrawn, superseded or tightened (COR-051 point 7). Any other change binds through an inheriting set's pin without review.
  - **But the project opts in first.** A shipped rule set binds only through a set of the project's own with a scope (COR-051 point 7, refined on 11 October). The rationale rejects anything that "would take away a project's choice not to inherit the set".
  - **And friction stays as a second net.** A rule's dependants see any edit to it as friction (COR-051 point 2), and "a change to the inherited rule flags the fill" (point 7).
- **A shipped rule's own revalidation.** In a receiving project, method rule sets are walked as artefacts. A rule-set place is no declared place, so the synced-copy test does not skip it (`friction_discovery.discover_artefacts`, `rule_set_places`). So the revalidation written upstream on a rule of `LDOC` answers that rule's friction in the receiving project, on an upstream artefact only.
- **Code and checks.** A project that chooses a target release runs that release's code, its migrations and its checks (#1429, question 2). The release's code already decides what friction asks there.
- **No upstream answer clears friction on a project's own artefact today.**

### What a document others anchor is today

- **Decision records** carry no container. They are no artefacts unless they sit in a declared place (COR-050 point 1).
  - **Record front matter is read line by line** for its required keys (`validate._validate_decision_record`). An added `pkit` key breaks nothing there.
  - **The revision-marker warnings** read the body only, never the front matter (`decisions_validate.find_revision_narration`).
- **ADRs are artefacts too in project-kit.** All 61 sit under `tech-docs/`, inside living-docs' internal-root place. Discovery lists each as a document with no container. So `record: [ADR-049]` and `artefact: [ADR-049]` both resolve, and read it two ways.
- **Pages and analysis artefacts** are artefacts in places, with friction blocks.
- **Rules** are collection entries, each with its own friction block (COR-051 point 2).
- **The friction block's schema** refuses unknown keys (`.pkit/schemas/backbone/container.schema.json`, `friction`). It is bound to documents and entries in declared places.
- **Under private visibility,** `.pkit/` is excluded from git (ADR-009 point 3), so a project has no history of its synced records.

### Counts

- **Shipped records:** 54 core records and 66 capability records reach adopters.
- **Anchored here:** 57 of them are anchored by project-kit's own artefacts, through 137 anchor values. 199 of 391 anchor values are record anchors.
- **Edits:** 53 commits on main touched a shipped record since 27 September.
- **Kept edits measured:** of the 182 answers a document's edit caused from 27 September to `30cfb15a`, 4 followed an edit that kept the meaning (the versioning note, "What history shows").
- **One coming:** #1421 converts 86 records' points to headings word for word, 40 of them shipped. Every whole-record dependant here, 28 artefacts, answers once.
- **What one transition brings, measured for question 3:**
  - **The method:** for two release tags, each shipped record that existed at both was compared point by point. A point is a top-level numbered item, a bold number or label, or a numbered heading in the Decision. Whether each point's edit kept its meaning was not classed, which needs a person's judgment per edit.
  - **From `v1.149.0`, the last release, to main:** 38 such records changed. 25 of them have points, and 6 of those had two or more points changed.
  - **Between consecutive releases, `v1.134.0` to `v1.149.0`:** 14 such record changes in 25 pairs of tags, 2 with two or more points changed.

### Dependants that rest on more than the claims

- **A fold that "changed no claim":** on 11 October, `c2b98094` folded the amendment sections of PRJ-008 and of project-management's DEC-028, DEC-032 and DEC-046 into their decisions. Each message says "No claim is added, dropped or changed".
  - **Yet a dependant changed in the same commit.** The software-engineering README anchors DEC-028 and DEC-032 whole, and it named "the `type`-axis + `touches-code` floor amendment", a section the fold removed.
  - **What a test per part catches:** the fold moved the amendment's claims into DEC-032's D1, so D1 gained claims. A test applied to each part refuses that edit as kept.
  - **What it shows besides:** a dependant may name structure, a heading, that no claim test reads.
- **A dependant that quotes the words:** `.pkit/lifecycle/README.md` anchors COR-053 whole and quotes its point 10 word for word, "owned by the methodology, named for it". A rewording that keeps the meaning still makes the quote wrong.

## Forces

- **The maintainer's reason to design it now:** a wording edit to a shipped record lands on every adopter anchored to it, and changing friction's rules is cheapest before adopters rely on them.
- **Nothing may be hidden:** an edit nobody classed must still ask its dependants (the versioning note, alternative D).
- **A person decides each answer** (core rule 20). A reason that spares many dependants is the strongest answer there is, and the costs are lopsided: a wrong "kept" is silent everywhere, a wrong "changed" only asks more.
- **Two states:** friction compares two states, so a change's landing never decides an answer (COR-050, "Why a change is a difference between two states"). The two checks agree.
- **A receiving project holds only its own history.** Upstream edits reach it at version transitions, many at once (#1429).
- **A project keeps its choice** about what shipped content does to its own artefacts (COR-051 point 7).
- **Part anchors:** a dependant may stand on one point or section (#1387).
- **No numbers on documents:** the maintainer decided no semantic versions for documents (#1383, question 1, software-analysis DEC-001 point 6).
- **Cost per edit:** every edit to a marked document asks its author one choice.

## What practice does

Practice lets one party propose the class of a change and another accept it, treats doubt as substantive, and corrects forward.

- **W3C's Process Document** ([§6.2.3, Classes of Changes](https://www.w3.org/policies/process/20250818/#correction-classes)) sorts every change to a specification into five classes. The first two, "No changes to text content" and "Changes that do not functionally affect interpretation of the document", are editorial.
  - **Doubt:** "If there is any doubt or disagreement as to whether a change functionally affects interpretation, that change does not fall into this class."
  - **The consequence:** "Editorial changes to a Recommendation require no technical review of the intended changes" (§6.3.10.1). Publishing one still takes a Working Group decision.
- **The RFC Editor's errata** ([errata types and statuses](https://www.rfc-editor.org/errata-definitions/)) never change a published RFC. Each erratum is published beside it, typed Technical or Editorial, with a status: Reported, Verified, Rejected or Held for Document Update.
  - **Editorial:** "a spelling, grammar, punctuation, syntax, or formatting error that does not affect the technical content of the RFC."
  - **Who classes it:** anyone reports an erratum, and the stream's authority verifies it. For the IETF stream the Area Directors are responsible, and errata "should not be used to change what the community meant when it approved the RFC" ([IESG statement of 7 May 2021](https://datatracker.ietf.org/doc/statement-iesg-iesg-processing-of-rfc-errata-for-the-ietf-stream-20210507/)).
- **Semantic Versioning's patch** ([semver.org](https://semver.org/), item 6) is declared by the author: "Patch version Z (x.y.Z | x > 0) MUST be incremented if only backward compatible bug fixes are introduced."
  - **Consumers accept it by a range they hold:** npm's caret range "Allows changes that do not modify the left-most non-zero element" ([node-semver, caret ranges](https://github.com/npm/node-semver#caret-ranges-123-025-004)). npm writes a caret range by default, and a consumer may pin exactly instead.
  - **A wrong class is corrected forward:** "the contents of that version MUST NOT be modified" (item 3). The FAQ says to release a new version that restores compatibility and document the offending version.
- **What follows for pkit:**
  - **A second party accepts each class.** Here it is the person who accepts the reason, and in a receiving project the person who authorises the transition.
  - **Doubt makes the edit a change of meaning,** as for W3C.
  - **Trust across projects is the consumer's default, which it can narrow,** as npm writes a caret range a project can replace with a pin.
  - **The reader sees each class with where it came from,** as an erratum is published beside its RFC.
  - **A wrong class is fixed by a later change,** never by rewriting what shipped.
  - **Nobody checks a class mechanically,** beyond what is visible in the text's structure.

## The design

### The markers and the reason

A **marked document** is a document others anchor whose friction block holds a `meaning` block.

```yaml
pkit:
  friction:
    meaning:
      at: 2026-10-14T09:00:00Z
      parts:
        "5": 2026-10-20T10:00:00Z
      outside-parts: 2026-10-21T08:00:00Z
      kept-because: Rewords point 11's second sentence. No claim, term, citation or heading a reader can name changes.
```

- **A part:** what an anchor can name inside a document, a record's point or a page's section or lead, each with what it stands on (#1387, "What a point stands on").
- **`at`, the document's marker:** moves when the meaning of what every part stands on changes. For a record that is its `status`, supersession and `title`, its preamble, Summary and the Decision's text outside every point (#1387). For a page it is its own fields.
- **`parts`, each part's own marker:** an entry appears the first time a part's meaning changes, and moves on each later change. A part without an entry has kept its meaning since the block was added.
- **`outside-parts`:** moves when the meaning of the text outside every part changes, such as a record's Context, Rationale and Implications. Only an anchor on the whole document reads it.
- **`kept-because`, the reason:** a sentence, read with its whitespace folded, written on each edit that keeps the meaning of the parts it changes.
- **Each marker is a UTC timestamp,** read parsed, as `revalidated.at` is. A value written back is no new value, as for `at` (COR-050 point 3).
- **A document without parts,** such as a collection entry or a record still in list form, carries `at` alone.
- **Adding the block** changes no content, since the container is not content. It asks no dependant.
- **Why a timestamp:** it is `at`'s shape, readable, and new on every move. A commit id cannot name the commit it lands in, and a stored hash was rejected (COR-050, "Why a timestamp whose point comes from git").
- **Why one reason, not a list:** the check needs only the reason of the latest step to tell a kept step. A list adds entries no check reads, which two lines of work would both append to. The release notes give a receiving project every reason ("How a receiving project sees a reason").
- **Why part markers:** they keep a part's meaning change apart from a rewording of another part, in this project and across a version transition. The reading then stays a comparison of two states (question 3).

### What a dependant reads

- **The markers an anchor reads:**
  - **an anchor on a part:** `at`, and its part's entry in `parts`
  - **an anchor on the whole document:** `at`, every entry in `parts`, and `outside-parts`
  - **an anchor on a document without parts:** `at`
- **The rule:** an anchor on a marked document has changed between two states when its text differs between them and a marker it reads differs between them.
- **The exception, an undeclared step:** where a step since the newest point of the markers an anchor reads changed its text and declared nothing, the anchor reads as on an unmarked document. It has changed wherever its text differs, as today ("Steps").
- **A part missing at either state** reads as #1387 says. An anchor on a retired point stands on nothing, and one on a part not there yet is flagged.
- **A dependant that rests on the words,** such as a quotation, anchors the document's file by path. A path anchor compares the file and reads no marker.
- **Several revalidation points** compose as COR-050 point 3 sets: the anchor has changed only where it has changed against every one of them.

**The cases,** for a dependant of point 11 of a marked COR-050:

| What happened since the dependant revalidated | Asked? |
|---|---|
| an edit with a reason rewords point 11 | no |
| two such edits, a week apart | no |
| point 5's marker moves, and point 11 is untouched | no |
| a reason rewords point 11, then point 5's marker moves | no |
| one edit moves point 5's marker and rewords point 11 under a reason | no |
| one edit changes points 5 and 11, and moves both markers | yes |
| `at` moves for a new status | yes, since the status is in point 11's text |
| an undeclared edit touches point 5 only | no |
| an undeclared edit touches point 11, then a reason touches it again | yes |
| the block is added, with no content change | no |
| point 11's marker moves with no text changed, as a correction | yes, unless the text it stood on is the text now |

- **The same table holds in a receiving project,** where a transition brings many upstream edits as one: point 11 changed, its marker held, and the reason is new, so its dependant is not asked.

### Steps, and what each one declares

Only the exception, an undeclared step, and whether a value is new, read history.

- **A step** is one change along the first-parent line of the history read: a commit on that line, or a merge taken against its first parent. In the change check, the change from base to head is one step. With a squash landing, each pull request is one step on the default branch.
- **What a step declares,** for each part whose text it changed:
  - **meaning changed:** it moved a marker that part's anchors read
  - **meaning kept:** it wrote a new reason, and moved no such marker
  - **nothing:** an *undeclared step* for that part
- **A correction** moves a marker and changes no text. Every dependant whose text differs from the text now is asked, by the rule above.
- **Removing the block** is read as a correction of every marker, and the document reads as unmarked after it.
- **Reverts:** a revert writes back an earlier marker or reason, which is not new. So a revert declares afresh: the revert of a kept edit gives a new reason, and the revert of a meaning change moves the markers to new values. A conflict on a marker or on the reason is resolved the same way, with a new value for the combined state, as COR-050 point 3 asks of a conflicting revalidation.
- **Where history is cut:** a value whose newness cannot be established reads as not new. So a reason written back from beyond a shallow clone's cut reads as an undeclared step and asks. The reading fails closed.
- **Where a project has no history of a document,** under private visibility, a received document reads as unmarked.
- **Landing:** a squash or a merge landing is one step for both checks. With a rebase landing, a line of work's commits become steps. An undeclared commit followed by a commit that adds the reason makes the anchor read as unmarked in the whole-repository check, while the change check saw one kept step. The whole-repository check then asks more, as in COR-050's "Where the two checks part".

### The test of a kept meaning

An edit keeps the meaning when, in the whole document and in each part it changes, it:

- adds, drops, weakens or narrows no claim
- changes no term and no citation, and splits no claim into parts that disagree
- chooses no reading of a text that had two
- moves no text from one existing part to another, and removes, renames or splits no heading a reader or an anchor can name
- changes nothing that says whether or how the document binds

Doubt moves a marker.

- **The source:** project-kit's RS-WRITE-013 lists the first three. A core record states the test in its own words, since a core record suits any project (COR-014). WRITE binds project-kit's analysis and software-analysis's templates and structures, and no record (`.pkit/rules/project.md` rule 3).
- **"The whole document":** a whole-record anchor also stands on Context, Rationale and Implications, which are no parts. An added rejected alternative adds a claim there.
- **A title** is a claim. A retitle keeps the meaning only where the test holds for it.
- **What says whether or how a document binds** is named by its defining component: a record's `status`, `supersedes`, `superseded_by` and a "Partially superseded by" line, a rule's status, successor and extension points (COR-051 points 2, 4 and 7), an artefact's status field.
- **#1421's conversion keeps the meaning.** It turns each point into a heading with the same id, and creates parts where the list form had none, so no existing part loses text.
- **What the change check refuses mechanically,** as a finding beside a reason: a change to a field that says whether or how the document binds, an added "Partially superseded by" line, a heading removed or renamed, a point id the record held in neither form before, and a new `retired-points` entry. Each is visible from the two states. The rest of the test is judgment.

### Who decides

A person decides each reason. Question 2 asks when.

- **Recommended: accepted before it is written,** as a reason for having no anchors is (COR-050 point 3). A reason waives questions for dependants in every receiving project, which the person authorising this merge never sees. Edits that keep the meaning are rare, 4 of 182 answers in the count, so asking first interrupts little.
- **An agent with nobody to ask moves the markers.** A wrong "changed" only asks more.
- **The reason is still listed** on the change check's list, as an accepted reason for having no anchors is.
- **A moved marker needs no showing.** It spares nobody.
- **The writer:** a command of its own, named here `pkit friction meaning <document> [--changed [<part>...]] [--kept-because <reason>]`. It writes one block and names what it writes (COR-050 point 13).
  - **`--changed`** moves the markers of the parts named, or of every part the change altered when none is named. On a document the change did not alter, it is a correction.
  - **`--kept-because`** writes the reason for the parts the change altered whose markers it does not move.
  - **It refuses** a reason the document carried before, reading the document's history as the check does.
- **A tool that converts word for word,** such as #1437's conversion, proposes the reason, and the person accepts it with the reviewed diff, before it is written.
- **A recorded reason is never reworded.** It is a person's decision, so a later edit replaces it whole.
- **A marked artefact that is also a dependant** may answer twice in one change: its revalidation, which an agent may write first, and its own step, whose reason is accepted first. The cascade follows its declared step, not its `updated` outcome.

### Where it lives

- **An artefact in a place:** in its friction block, beside its anchors and its revalidation.
- **A decision record:** in the methodology's container in its front matter, which records gain for this, with a friction block that holds `meaning` alone (question 4).

  ```yaml
  ---
  id: COR-050
  title: Artefacts declare what makes them true, and drift is detected as friction
  status: accepted
  date: 2026-09-27
  author: Aleš Kalfas <kalfas.ales@gmail.com>
  pkit:
    friction:
      meaning:
        at: 2026-10-14T09:00:00Z
  ---
  ```

  - **A record anchor then stands on the record's content,** its container left out, as an artefact anchor does. Writing the block changes nothing a dependant reads.
  - **A decision record is anchored as a record, never as an artefact.** An ADR in a place is an artefact too, but `artefact: [ADR-049]` is refused, so each document has one namespace for its parts.
  - **Why the container, not the record's own fields:** the markers are friction's data, and COR-053 point 10 puts a functionality's data in the container and the artefact's own in its fields. `retired-points` sits outside, since it describes the record's own structure (#1387).
  - **A third kind of document:** a record outside a place is neither an artefact nor a held document, yet carries a container that is read and checked.
  - **ADRs never cross projects** (COR-025, "Propagation isolation"), so only the half of this design within one project applies to them.
- **Which documents carry it:** only those whose owner adds the block. A document without one reads as today. Which of project-kit's documents carry one is question 5.
- **A marked document is never dormant:** an edit to it that declares nothing fails the change check in enforcing mode, whether or not anything here anchors it, since a receiving project's anchors are unknown.
- **The decisions README's ban on revision markers:** the block is data a tool reads, and the reason is the current step's answer, as `unchanged-because` is. Neither is in the body, and neither is added to. The README's steps 2 and 3 still forbid "a block stamped with a date" and a note that the record was amended in place, so their sentences change ("Settled positions").
- **A supersession** changes `status`, so it moves `at`. A superseded record then keeps its block as it stood.
- **A renamed page section** leaves a stale entry in `parts`, which validation reports. A record's point ids are permanent (#1387), so records leave none.

### Across projects

A received document is read by the same rule, over the receiving project's own history.

- **Where it changes there:** only at version transitions, which bring the target release's methodology files (#1429). Each transition is one step of many upstream edits.
- **What a transition declares,** read like any step, part by part:
  - **a moved marker:** a meaning change of the parts that read it
  - **a new reason, the part's markers held:** kept
  - **new text under the old reason and the old markers:** undeclared. On a synced copy it is never a finding of the receiving project's.
- **What a received reason claims:** that every upstream edit since the project's last transition kept the meaning of the parts whose markers held, not only the edit it was written for.
- **The shipping duty that makes that true:** a project that ships a marked document moves the markers past every undeclared step before it ships. Its change check fails an undeclared step in enforcing mode, and its whole-repository check reports one that landed anyway, until the markers move. Where an undeclared step may already have reached receivers, the fix is a correction, a marker moved with no text changed.
- **project-kit's release refuses** to release while a shipped marked document has an undeclared step (slice M7). `pkit release check-shareable` runs the same check for an author who shares a capability by its own source (COR-041).
- **Whose reasons a project trusts:** a key in its friction settings, named here `received-reasons`, lists them (question 1).
  - **Absent, it means `[methodology]`:** content of a tagged methodology release, the backbone and the capabilities it ships, whose release enforces the shipping duty. A tagged release is what a project's recorded version names (ADR-033, #1429 question 10).
  - **A development install of main** is no tagged release, so its reasons spare nothing.
  - **A project narrows it,** to `[]` for instance, and every received edit then asks as today.
  - **An externally-sourced capability** (COR-041) is trusted only where the project adds its name, since nothing here knows its release.
  - **An untrusted document reads as unmarked.**
  - **Entries are checked against what is installed,** and uninstalling a named capability offers to clear its entry, with consent, or validation reports it as stale (COR-048 point 2).
- **Why trust by default:** a receiving project already runs the release's code, which decides what friction asks there (#1429, question 2). Trusting the same release's reasons adds no new party to trust. COR-051 point 7's opt-in protects a project's choice of which rules bind, not whom it trusts.
- **Synced copies:** the receiving project cannot edit them. So nothing about a synced document's own declaration is a finding there: an undeclared step, a reason beside a refused change, and a malformed block are reported and never fail. A malformed block reads as no marker.

#### How a receiving project sees a reason

- **On the change check's list,** for the change that brings it: the document, the latest reason word for word, the component and version it came from, and the project's artefacts it spares. The list reports it, as it reports the answers a change wrote (COR-050 point 12).
- **In a pull request,** project-management's list carries it, and its landing command holds a change that brings received reasons as it holds one that wrote answers (DEC-055).
- **In the release notes:** project-kit's release step lists, for each shipped marked document, every reason and marker move since the previous release (slice M7). A transition across several releases reads several entries. The latest reason alone does not describe every edit a transition brings.
- **In `pkit friction explain`,** for each anchor a reason spared.

#### Whose decision it is there

- **Nobody in the receiving project writes a received reason,** so it is no answer of that project's, and core rule 20 stays about answers written.
- **The trust is placed by the settings key,** and the list makes each reason visible within the receiving project's merge. What the person authorising it accepts is the authoring project's process: one reason per document, the diff, and the release notes.

#### What it does about a wrong one

- **Before authorising the transition:** it revalidates each artefact the reason spared, in the same change. A revalidation that nothing asked for is always allowed, and is reported as such (`friction_check._judge`, "revalidated with no changed anchor").
- **After the merge:** the same, once noticed. It reports the reason upstream (`pkit report bug`).
- **For good:** it narrows `received-reasons`.
- **Upstream corrects forward:** a correction moves the markers of the parts concerned without changing their text. Every dependant whose text differs from the text now is asked, in every project, at its next transition.
- **Upstream never rewrites a reason it shipped** to fix it, as a released version is never modified (Semantic Versioning, item 3).

### The checks

What a script checks that an edit wrote, and what it never checks.

- **Validation,** from the working tree (COR-055 point 2):
  - **the friction member checks every meaning block:** `at` and the entries are UTC timestamps, `kept-because` is non-empty text, there is no other key, and a `parts` entry names a part the document has. A record outside a place is read through the home of a record's points (#1412).
  - **on a record outside a declared place:** a container that holds anything but `friction.meaning` is reported as inert, as COR-053 point 10 says of a container elsewhere
  - **in a held document:** a `meaning` block is an error, as any friction block is (COR-050 point 12)
  - **on a synced copy:** reported, never failing
  - **the configuration member checks `received-reasons`** against what is installed
- **The change check,** for each marked document whose content the change altered:
  - **each step's declaration, part by part,** as above
  - **undeclared:** a finding owned by the change, failing in enforcing mode, and the dependants are asked
  - **a reason beside a refused change** ("The test"): a finding owned by the change, and the step reads as a meaning change
  - **on a synced copy:** none of these is a finding
  - **the list** gains each reason the change wrote and each reason it brought from another project, with the artefacts each spares
  - **where it reads history:** for a dependant whose `at` the change writes back or whose deferral it judges, to tell a new value from one carried before, to see whether the base already held an undeclared step, and for a correction or a removed block, where it judges each dependant against its own revalidation point
- **The whole-repository check:**
  - each anchor on a marked document read by the rule above
  - **a marked document with an undeclared step since its markers moved,** reported where it is authored, whatever depends on it, never on a synced copy
- **The release (project-kit):** `pkit release plan` and `apply` refuse a shipped marked document with an undeclared step, and the whole-repository check is the net between releases. `pkit release check` runs on pull-request heads, whose first-parent line holds the branch's own commits, so it is the wrong home.
- **Never checked:** that an edit kept the meaning, beyond the refused changes. That is the person's judgment, as `unchanged-because` is.

### The engine

- **Parsing:** an artefact's meaning block in artefact discovery, with the rest of its friction block. A record's container in the home of a record's points (#1412).
- **A new friction home over `friction_history`** computes a step's declaration, whether a part has an undeclared step since its markers moved, and whether a value was carried before. It derives the first-parent line from the one log, which already holds each commit's parents, so there is no second walk of git. Its callers: the change check, the whole-repository check, debt, explain, the writer's refusal, the release refusal, `check-shareable` and #1450.
- **Existing homes reused:** whether a file is a synced copy (`is_synced_copy` in the ownership module), and which component a synced path belongs to.
- **Two walking models:** debt and revalidation points follow every line of history, as today. The undeclared-step test follows the first-parent line. The realising ADR names both and where each applies.
- **Debt:** an anchor on a marked document is stale from the oldest step after the point it is measured from that moved a marker it reads while its text differed, or that changed its text and declared nothing. A point off the first-parent line, on a merged branch, is measured from the steps of the later state's line that it does not reach.
- **Cost:** the markers are read at two states, as content is today. The undeclared-step test depends on the later state only, so it runs once per document and part per run, and every dependant shares it. With about 130 marked documents of tens of versions each, that is a few thousand parses, cached by object as `Walker` caches.

### The records it touches

- **A new core record,** "A document others anchor marks an edit that keeps its meaning" (title provisional), recommended in question 6. It holds the document's side:
  - the markers, the reason, steps and their declarations, the test and its refusals
  - who decides and when
  - the container on decision records
  - received reasons, the trust setting, the shipping duty and synced copies
- **COR-050 holds the reading,** refined in place: when an anchor on a marked document has changed, deferrals, the cascade, debt, the findings, the writer, the key and the rationale ("Settled positions this reopens").
- **Refined in place too:** COR-053 point 10, COR-051 points 2 and 7, core rule 20, the decisions README, software-analysis DEC-001 point 6 and project-management DEC-055.
- **A realising ADR,** by the architect, refining ADR-057 point 2 for the new home (slice M1b).
- **The release README** documents the release refusal and the digest. PRJ-002 is untouched, since it leaves the mechanics to the README.
- **COR-025's ADR schema** takes the README's schema by reference. Its illustrative block is refined by #1422 already, and at most gains the container line.
- **Untouched:** COR-010 and PRJ-002. COR-048's text is untouched, and its duties apply to the key.
- **No migration is due (COR-010):** the block and the key are optional additions, and the reading only asks less. A document without a block reads as today. An adopter's dependants are asked at most once more, by a transition that brings a first marker with other edits.

## Alternatives weighed

- **For the markers:**
  - **One marker per document, two states.** The simplest. A rewording is asked again at the next meaning change anywhere in the document, in every project. Not taken.
  - **One marker per document, read through steps.** Each anchor walks the steps back to its part's last meaning change, and stands on any text the document held since. It keeps a part apart in this project, loses it across a transition that brings a meaning change anywhere in the record, and makes every reader walk steps. The first draft's recommendation, and question 3's alternative.
  - **A marker per part, with the document's own and one for the text outside every part.** Taken. Two states, and a part kept apart in every project.
  - **Reasons with no marker.** A receiving project could not see a meaning change hidden behind a later reason. Rejected.
  - **A number, moved by one on each meaning change.** Two lines of work that each change the meaning write the same number for two texts, as PRJ-002 found for components. Rejected.
- **For an undeclared step:**
  - **Covered by a later reason.** It would hide an edit nobody classed, and a receiving project could not tell. Rejected.
  - **Each commit a step.** Two commits on a branch, an undeclared edit and then the reason, would read differently after a merge landing and a squash. Not taken.
  - **Each step on the first-parent line.** Taken. It parts from the change check only for a rebase landing.
- **For the reason's form:** a list of every reason since the markers moved, in the front matter. Not taken ("Why one reason"). The release notes carry the list instead.
- **For who answers:** the dependants, in bulk. The upstream reason is offered as each dependant's `unchanged-because`, and one command writes every spared artefact's answer quoting it.
  - **Gains:** COR-050's reading stays, and every answer is the receiving project's own.
  - **Costs:** every edit rewrites a block on each dependant in every project, and each rewrite is a new revalidation point that conflicts with parallel work. A list of N copies of one sentence is easier to accept unread than one sentence.
  - **Not recommended,** but it is what remains for a project that trusts no received reason.
- **For path anchors:** a path anchor that matches a marked document's file still compares the file. It is how a dependant that rests on the words keeps every edit.

## Questions for the maintainer

One decision each, in order of consequence.

### 1. Do reasons written upstream spare a receiving project's artefacts by default?

- **The question:** project-kit writes a reason on a shipped record. Is an adopter's artefact anchored to that record then not asked, by default, or only once the adopter opts in?
- **Example:** an adopter's use case `UC-012` anchors `COR-050`. project-kit's next release rewords COR-050 point 11 under the reason "Rewords point 11's second sentence. No claim, term, citation or heading changes." The adopter runs `pkit upgrade`. The change check on its pull request lists "received: COR-050 — Rewords point 11's second sentence … (backbone 2.1.0). Spares: UC-012."
- **Recommended: by default,** for content of a tagged methodology release, with a key in the friction settings, `received-reasons`, that a project narrows or empties. The project already runs that release's code, so trusting its reasons adds no new party.
  - **Its cost:** an upstream author's reason clears friction on artefacts that author never saw. The receiving person sees the latest reason on the list and every reason in the release notes, and can accept them unread. The second net COR-051 keeps, friction on a rule's edit, goes for kept edits. COR-050 point 14 gains the key.
- **Alternative: only where the project opts in,** as a shipped rule set binds only through a set of the project's own (COR-051 point 7). `pkit init` could seed the key.
  - **Its cost:** a project without the key gets nothing, and seeding it at a transition is a configuration write COR-048 point 5 allows only where the owning record names it.

### 2. Is a reason accepted before it is written, or written first and shown before the merge?

- **The question:** an agent edits a marked record and judges that the meaning held. Does it ask the person before it writes the reason, or write it and show it on the change check's list before the merge is authorised?
- **Example:** an agent fixes a typo in COR-017 point 4. It asks "Kept: Fixes a typo in point 4. No claim, term, citation or heading changes. Accept?", or it writes that reason and it appears among the answers the change wrote.
- **Recommended: accepted before it is written,** as a reason for having no anchors is. A reason waives questions in projects the merge's authoriser never sees, and kept edits are rare. An agent with nobody to ask moves the markers.
  - **Its cost:** an agent stops to ask on each kept edit, and core rule 20's list of what is accepted first grows.
- **Alternative: written first,** as the answers the change check asks of a change, shown on the list before the merge.
  - **Its cost:** the strongest answer there is gets the weaker timing, in a list where it can be accepted unread with the rest.

### 3. Does a part carry a marker of its own?

- **The question:** each part whose meaning changed gets its own marker, or the document carries one marker that every part reads through the history?
- **Example:** one release of project-kit carries two pull requests. One changes what COR-050 point 5 requires. The other rewords point 11 under a reason. A journey anchored to `COR-050#11`, here or in an adopter that upgrades across that release.
- **Recommended: a marker per part,** with the document's own marker and one for the text outside every part. The first pull request moves point 5's marker. The journey is not asked, here or in the adopter.
  - **Its cost:** the writer moves the markers of the parts a change altered unless the author keeps some under a reason, so every author meets the parts. One more map in the block, and a renamed page section leaves a stale entry that validation reports.
- **Alternative: one marker per document,** read through the steps. In project-kit the journey is not asked, since each pull request is a step. In the adopter the transition is one step with the marker moved, so the journey is asked.
  - **Its cost:** every reader walks steps back to each part's last meaning change, which reopens COR-050's comparison of two states for every anchor on a marked document. Across a transition that brings a meaning change anywhere in a record, every reworded part's dependants are asked. Measured, 6 of the 38 shipped records changed since the last release had two or more points changed, so the loss is bounded by those.
  - **Not "later" for free:** the data could gain part markers later without a migration, but the engine would then carry two readings or be rewritten.

### 4. Where does a decision record carry the markers?

- **The question:** in the methodology's container, as an artefact does, or as the record's own fields?
- **Example:** COR-050's front matter gains either `pkit: {friction: {meaning: {at: …}}}` or top-level fields such as `meaning-at`.
- **Recommended: the container.** The markers are friction's data, and COR-053 point 10 keeps the methodology's data in the container. A record anchor then reads the record without it, as an artefact anchor reads an artefact.
  - **Its cost:** records gain the container, a third kind of document beside artefacts and held documents. COR-053 point 10 and COR-050's "for a record, the record's file" change.
- **Alternative: the record's own fields,** outside the container, as `retired-points` is.
  - **Its cost:** friction's data among a record's own fields, against COR-053 point 10's split. An ADR in a place would have two spellings for one fact, and a record anchor must leave out the named fields.

### 5. Which of project-kit's documents carry the block before the first adopter?

- **The question:** a marked document asks its author one choice on every edit. Which documents take that cost?
- **Example:** a maintainer fixes a typo in COR-017. If COR-017 is marked, the pull request fails the change check until the edit gives a reason or moves a marker.
- **Recommended:** every accepted record project-kit ships, of 54 core and 66 capability records, and the rules of `LDOC`. Adopters' anchors are unknown. A proposed record gains the block when it is accepted, since nothing anchors it before. A superseded one is not edited.
  - **Its cost:** one choice on each edit of those records. 53 commits on main touched a shipped record since 27 September.
- **Alternative:** only the 57 shipped records project-kit's own artefacts anchor today, and others as adopters ask.
  - **Its cost:** an adopter that anchors an unmarked record is asked on every edit to it, and marking it later spares only what follows.

### 6. Is the document's side a record of its own?

- **The question:** a new core record for the markers, the declaration and the trust, or all of it in COR-050?
- **Example:** the rule "a received reason spares a project's artefacts only for the components its settings trust" lives either in a new record, with COR-050 pointing at it, or as further sentences in COR-050.
- **Recommended: a record of its own** for the document's side: the markers, the declaration, the test, who decides, the container on records, the trust and the shipping duty. COR-050 keeps the reading, refined in place, since when an anchor has changed is already its concern.
  - **Its cost:** one more core record, and the answer to "when is a dependant asked" split across two records.
- **Alternative:** all of it in COR-050, refined in place.
  - **Its cost:** COR-050, 167 lines and refined for parts by #1419 and #1423, gains the declaration and the trust beside anchors and answers.

## Settled positions this reopens

Each accepted sentence below changes, for the maintainer's authorisation. The refinements land in M1, after the new record is accepted, each in a commit of its own.

1. **COR-050's terms and point 5, what a record anchor stands on:** "What an anchor **stands on** is, for a path, the files it matches (point 7 says which the excluded paths leave in); for a record, the record's file" and "**A record anchor** has changed when the record's file differs, followed across a rename."
   - **The change:** a record anchor stands on the record's content, its container left out. A record without a container reads as before, except that an edit to its front matter's layout alone is no change.
2. **COR-050's term "The diff":** "**The diff** of a pull request is the set of paths changed between its up-to-date base and its head, and the parsed before-and-after of every artefact in a declared place."
   - **The change:** and of every marked record, wherever it lives.
3. **COR-050 point 1, where the container is read:** "Everything this record owns in an artefact sits in **one functionality block, named `friction`**, inside the methodology's front-matter container" and "The backbone looks for artefacts only in the **places declared to hold anchored artefacts**, so unrelated front matter elsewhere is never misread."
   - **The change:** a decision record's friction block, which holds the meaning block alone, is read wherever the record lives.
4. **COR-050 point 2, an artefact anchor:** "**another artefact**, by its id."
   - **The change:** a decision record is anchored as a record, never as an artefact, even where it sits in a place.
5. **COR-050 point 5, when an anchor changed:** "**An artefact anchor** has changed when that artefact's **content** changed" and "**Three answers**, judged from the diff [...] clear friction".
   - **The change:** an anchor on a marked document has changed where its text differs and a marker it reads differs, or where an undeclared step changed its text since those markers moved. A kept step is no answer of the dependant's. It keeps the dependant from being asked.
6. **COR-050 point 4, deferrals:** "Where the anchor has changed since — what it stands on differs from what it stood on there (point 5) — that is new friction."
   - **The change:** for an anchor on a marked document, "changed" is read by point 5's rule.
7. **COR-050 point 6, the cascade:** "An artefact anchored to another artefact is included when that artefact's content changed in the pull request. The cascade continues only where a revalidation itself changes content."
   - **The change:** for a marked artefact, the cascade follows its declared step, not its `updated` outcome.
8. **COR-050 point 9, debt:** "*stale* debt originates in the oldest commit from which a part of what the anchor stands on [...] has differed, without returning, from what it was at the point it is measured from".
   - **The change:** for an anchor on a marked document, at the oldest step after that point that moved a marker it reads while its text differed, or that changed its text and declared nothing.
9. **COR-050 point 3, a person's decision:** "Every other answer an agent writes, on an artefact its change was not asked about, and every reason for having no anchors (point 1), is written only after a person was shown it and accepted it."
   - **The change, under question 2:** a reason an edit keeps a document's meaning joins the answers accepted before they are written.
10. **Core rule 20:** "A revalidation, a deferral or a reason for having no anchors (COR-050 points 1 and 3) is written only after a person was shown it and accepted it, with one exception."
    - **The change, under question 2:** the list gains a reason an edit keeps a document's meaning. The rule stays about answers written, so received reasons are not in it.
11. **COR-050 point 12, findings and failures:** "**The change check finds:** friction of the pull request, dead anchors of the pull request, a bump with nothing behind it, [...]", "In **enforcing mode** it fails on the first five", "**Reported only, in every mode:** [...] the answers the change wrote, each with its words (point 3)", and "**Validation owns:** a malformed block, [...]".
    - **The change:** the change check also finds an undeclared step and a reason beside a refused change, owned by the change and failing in enforcing mode, never on a synced copy. Reported only: the reasons written and the reasons received. Validation owns the meaning block's shape.
12. **COR-050 point 13 and its Implications, the writers:** "Writing is always a separate, explicit command that names what it writes: revalidate, defer, record the status." and "**The backbone ships the writing commands** for revalidating, deferring and recording the status".
    - **The change:** a fourth writer declares a document's meaning.
13. **COR-050's Implications, the history CI needs:** "**Continuous integration** needs each artefact's history back to where it was last added (point 3) for the whole-repository check and the debt listing, since only there is it known where a value was first carried."
    - **The change:** and each marked document's first-parent line back to its markers' points, and the values it carried before. A value whose newness a cut history hides reads as not new.
14. **COR-050 point 14, project settings:** "It holds the friction mode (default: warning), when the status job runs (default: never), the project's own anchored places, its declared surface, and its excluded paths (all default: none)."
    - **The change, under question 1:** it also holds `received-reasons`, by default `[methodology]`.
15. **COR-050 point 15, dormancy:** "Where no artefact declares anchors, the check finds nothing and demands nothing."
    - **The change:** a marked document's undeclared step is a finding even where nothing is anchored.
16. **COR-050's rationale:**
    - "Why the pull-request rule is local to the pull request": "Both checks ask the same question — does what an anchor stands on differ between two states [...]". For a marked document they also compare its markers, and read the steps for an undeclared one.
    - "Where the two checks part": "The two checks part in a few cases." It gains the rebase landing.
    - "Why a change is a difference between two states": "Which commits touched an anchor depends on how a change lands: a merge keeps them, a squash or a rebase folds them into one." The undeclared-step test counts steps on the first-parent line, and the passage says why that is safe for a squash and a merge landing.
17. **COR-053 point 10:** "An artefact's front matter — for a collection entry, the entry itself — may hold **one** key owned by the methodology, named for it" and "Any artefact may carry the container; validation reaches only the artefacts in declared places (COR-050 point 1), so a container elsewhere is inert."
    - **The change, under question 4:** a decision record may carry the container too, with a friction block holding the meaning block alone, which friction reads and validation checks wherever the record lives.
18. **COR-051 point 2, "Anchoring":** "Editing a statement, or accepting, superseding or withdrawing a rule, is therefore a change that the rule's dependants see as friction. Nothing keeps silently obeying a rule that has changed."
    - **The change:** an edit of a marked rule's statement in a kept step asks its dependants nothing. A change of its status always does.
19. **COR-051 point 7, fills:** "A filling rule anchors to the rule it fills, so a change to the inherited rule flags the fill."
    - **The change:** a kept step on a marked inherited rule flags no fill, where the fill's project trusts the rule's component.
20. **The decisions README:**
    - **"Schema":** "Each record is a Markdown file with YAML frontmatter and four required sections:". The front matter may also hold the container with its meaning block.
    - **"Refining an accepted record", step 2:** "**Add no revision marker** — no amendment heading, no block stamped with a date or an issue number, no note that the record was amended in place rather than superseded." The meaning block is data a tool reads, and the reason is the current step's answer, replaced on each step. The step names both as no revision marker.
    - **Step 3:** "**Leave no residue of the change.** A word that makes sense only against the old text — "now", "no longer", "still", "corrected above" — is restated as plain fact." The reason describes the step, in the front matter only, and the step says so.
    - **The same section gains** that an edit to a marked record declares its step, and that a supersession moves its `at`.
21. **software-analysis DEC-001 point 6:** "the capability's artefacts and records carry no declared versions", and its rationale: "A version an author declares on a document would tell a dependant one fact, whether the meaning changed [...] So the capability's artefacts and records carry no declared versions".
    - **The change:** the sentence allows a declared meaning marker, the one fact the rationale names, and still no version number.
22. **project-management DEC-055:** its decision, "merges a change that wrote answers, or altered the settings that decide what the check asks, on an authorisation given up front only when the list for the head it merges was already in the description", its point 1, "The list is the change check's own list of the answers the change wrote", and its point 3, "An entry flagged as not asked for, and a reason for having no anchors, needed the person's acceptance before it was written; authorising the merge does not give it."
    - **The change:** the list gains the reasons a change wrote and those it brought. The hold also fires on a change that brings received reasons, and `received-reasons` is among the settings that decide what the check asks. Under question 2, a kept reason joins the class point 3 names.

**Not reopened:**

- **COR-050's rejected alternatives:** "A commit identifier or a content hash as the marker" stays rejected, since the markers are timestamps. "A bare marker change as an answer" stays rejected, since a moved marker answers nothing and spares nobody.
- **COR-050's "Why the container is not content":** its reason holds for records as written.
- **COR-051 point 7's majors:** a rule edited in a kept step makes no major due, since the test forbids tightening.
- **COR-025's ADR schema:** by reference to the README's.

**Decided designs it changes,** not yet accepted records:

- **#1387's first case,** "The part's text changes: its dependants are flagged." A part changed in a kept step flags nobody.
- **#1383's question 2,** "not now", which the maintainer reopened on 11 October.

## Slicing

A draft of the build, for filing after the maintainer decides. Each record is accepted before the work that cites it. Each slice says whether it is safe if a release is cut after it. The build lands before the first adopter.

- **M1, [Docs] A core record says a document others anchor marks an edit that keeps its meaning:**
  - authored with `pkit new decision core` through the decision-author skill, and reviewed by the critic, the architect and the methodology-reviewer
  - the refinements in place of "Settled positions" 1 to 22 in the same change, each in a commit of its own, COR-050's reading among them
  - **after the refinements of COR-050 by #1419 and #1423 are accepted,** so they do not race. Names #1422, which edits the decisions README's refining and schema sections and COR-025's block: whichever lands second builds on the other.
  - **Held from a release until M4 ships,** as #1387 held its COR-050 refinement until friction for points shipped, since the refined records describe behaviour M3 and M4 build.
  - a `none` changeset for each component whose records it edits (PRJ-002)
- **M1b, [Docs] The realising ADR, by the architect:** the new friction home and ADR-057 point 2's refinement, the two walking models, cut history and private visibility, the validation member, the release refusal in `plan` and `apply` and the digest beside changesets, and which commands call the undeclared-step test. After M1 and #1412, before M2.
- **M2, [Task] The meaning block, its schema, validation and its writer:**
  - the container schema gains `meaning` in the friction block, and binds records too
  - validation's friction member checks every meaning block, reading records through the home of a record's points, and reports and never fails on a synced copy
  - `pkit friction meaning`, with consent as the other writers, refusing a reason carried before
  - **Safe alone:** no check reads the block yet, so dependants read as today.
  - **Docs:** the schemas README's "The friction block", the CLI reference. A backbone minor.
- **M3, [Task] The whole-repository check, debt and explain read the markers:**
  - the new friction home: steps, declarations, the undeclared-step test and values carried before
  - each anchor on a marked document read by the rule, deferrals and debt by it, and `explain` naming the reason that spared an anchor
  - the document finding, an undeclared step since the markers moved, never on a synced copy
  - **after M1b, M2 and #1419.** Names #1423: whichever lands second reads page sections.
  - **Safe alone:** the change check still asks as today, so it asks more than the whole-repository check reports, a direction COR-050 accepts. A backbone minor.
- **M4, [Task] The change check reads a marked document's step:**
  - a record anchor reads the record without its container, and refuses the artefact form on a record
  - each step's declaration, the undeclared step, the refused changes, and synced copies
  - dependants spared by a kept step, and the cascade
  - the list's written and received reasons, in its human and JSON forms, and project-management's list and hold for them (DEC-055)
  - `received-reasons` with its reader, checked by the configuration member, and offered for clearing on uninstall
  - **after M3 and #1408.** A backbone minor, and a minor for project-management.
- **M5, [Task] The skills and agents that edit a marked document ask for its declaration:**
  - the decision-author skill when it refines a marked record, the analysis-author skill, living-docs' agent, and the agents README's "Friction writers", including an artefact that answers twice in one change
  - the guidance that a dependant resting on the words anchors the file by path
  - after M2
- **M6, [Docs] project-kit marks the documents it ships,** as question 5 decides:
  - the block, with `at` alone, on each document, through the writer. No dependant is asked, since no content changes
  - `.pkit/lifecycle/README.md`, which quotes COR-053 point 10, anchors COR-053's file by path
  - CONTRIBUTING.md says that an edit to a marked record declares its step
  - **after M4, and after #1421,** so the conversion of project-kit's records lands as planned. Marking first would spare the conversion's 28 answers, but would hold the part-anchor build behind this one.
  - a changeset for each component whose records it marks, its segment the maintainer's judgment (PRJ-002)
- **M7, [Task] project-kit's release refuses an undeclared step, and lists every reason:**
  - `pkit release plan` and `apply` refuse while a shipped marked document has an undeclared step
  - the release notes list, for each shipped marked document, every reason and marker move since the previous release
  - `pkit release check-shareable` runs the same test
  - **Docs:** the release README. After M3.

**Order:** M1, M1b, then M2, M3 and M4 in turn, then M5 and M7, then M6, then the first adopter.

**Against the filed builds:**

- **Part anchors, #1403 to #1427:** M1 after the refinements of #1419 and #1423, beside #1422. M1b after #1412. M3 after #1419. M4 after #1408. M6 after #1421.
- **Conversions, #1431 to #1444:** #1438 converts an adopter's records. Once markers exist, a conversion of a marked record declares its step, with the reason proposed and accepted with the reviewed diff (#1437). Whichever of #1438 and M4 lands second handles the other.
- **The version transition, #1455 to #1465:** independent. A received reason is read over whatever brings the document, today's sync or the transition after #1460. The trust default reads the recorded version #1459 writes.
- **Rule-set versions, #1449 and #1450:** #1450's check may call the new home (Found on the way 3).

## Found on the way

1. **A receiving project's checks judge upstream rules.** Method rule sets are walked as artefacts there ("Today"). An upstream rule left stale upstream would be reported in every receiving project, which cannot edit it. Whether a receiving project should judge rules it cannot edit is a question of its own.
2. **Quotations of records** exist in project-kit's pages, such as `.pkit/lifecycle/README.md`'s of COR-053 point 10. A check that a quotation still matches its source would be a rule of LDOC's, not friction's.
3. **A rule edited in a kept step makes no major due** (COR-051 point 7), since the test forbids tightening. #1450's check could skip such edits. #1449 decides what each part of a set's version means.
4. **PRJ-002's paragraph on pull requests that touch decisions** could say that a kept edit to a record needs no changeset, as any refinement that changes no surface needs none.

## Review

### The critic

The critic found four red flags, twelve gaps, nine weak arguments and six counter-alternatives, with notes on the questions, the settled positions, the slicing and the code claims. Each finding is answered below, numbered as the critic numbered them. Where the architect's round then changed an answer, the answer says so.

**Red flags:**

1. **A marker move reset every part, but the change check asked only the changed ones, so the checks disagreed.** **Answer:** accepted, with the critic's fix (b): a meaning change asks only the dependants of parts whose text it changed. The architect's round then made each part's marker its own (its finding 1), so the reading is a comparison of two states and needs no history for this. A correction still judges each dependant against its revalidation point.
2. **An undeclared edit was defined per commit, so landing decided it.** **Answer:** accepted. A step is one change on the first-parent line, so a squash and a merge landing read alike. A rebase landing parts the checks, and COR-050's rationale is among the settled positions (16). After the architect's round, steps serve only the undeclared-step test.
3. **The trust argument did not hold: one reason covers many edits, and only project-kit enforces the shipping duty.** **Answer:** accepted in both parts.
   - **What is shown:** the release notes list every reason and marker move since the previous release (M7). The note says plainly that the receiving person accepts the authoring project's process.
   - **Whose reasons:** by default only a tagged methodology release, which enforces the duty. The architect's round added the tag. An externally-sourced capability is trusted only where the project names it.
4. **COR-051 point 7's fill sentence changes, though the note said point 7 was not reopened.** **Answer:** accepted. Settled position 19 quotes it.

**Gaps:**

5. **Findings on synced copies would fail a receiving project on files it cannot edit.** **Answer:** accepted. Nothing about a synced document's own declaration is a finding there. A malformed block reads as no marker.
6. **"The change check needs no history" was false.** **Answer:** accepted. "The checks" says where it reads history.
7. **Removing the block was undefined.** **Answer:** accepted. It is read as a correction of every marker.
8. **Debt was dated from the wrong meaning change.** **Answer:** accepted. It is dated from the oldest step after the point that moved a marker the anchor reads while its text differed (settled position 8).
9. **Reverts and conflicts on `at` were not covered.** **Answer:** accepted. A revert declares afresh, and a conflict is resolved with a new value ("Steps").
10. **The test had holes.** **Answer:** accepted in each part: the whole document and each part, citations, a "Partially superseded by" line, a split heading, a title, and #1421's conversion.
11. **Dependants that rest on the words exist.** **Answer:** accepted. Such a dependant anchors the file by path. M5 carries the guidance and M6 re-anchors `.pkit/lifecycle/README.md`.
12. **The settled positions were incomplete.** **Answer:** accepted. Each sentence named is quoted. The architect's round added more (its findings 13 to 15).
13. **The writer and the check disagreed on a valid reason.** **Answer:** accepted. The writer refuses any reason the document carried before.
14. **Proposed and superseded records.** **Answer:** accepted. Question 5 marks accepted records.
15. **#1422 and #1423 touch the same records.** **Answer:** accepted. M1 waits for #1423's refinement too, and names #1422.
16. **"In short" overstated.** **Answer:** fixed.

**Weak reasoning:**

17. **The reading of practice was confirming.** **Answer:** accepted. Practice reads as one party proposing a class and another accepting it.
18. **Placing a reason under core rule 20's exception was circular.** **Answer:** accepted. It is question 2, recommending acceptance first.
19. **COR-051 point 7's precedent points to opt-in.** **Answer:** accepted. "Today" says so. After the architect's round, question 1 also says why the opt-in does not carry over: it protects which rules bind, not whom a project trusts.
20. **Question 1's alternative cost was overstated.** **Answer:** accepted. The alternative names seeding by `pkit init`.
21. **`c2b98094` supports the per-part clause, not the heading clause.** **Answer:** accepted. "Today" says both.
22. **software-analysis DEC-001 point 6 was redefined, not changed.** **Answer:** accepted. Settled position 21 says the sentence changes.
23. **Question 3's alternative was undersold.** **Answer:** accepted. After the architect's round, the part markers are the recommendation.
24. **RS-WRITE-013 was used as authority for a core rule.** **Answer:** accepted. The note says it in its own words.
25. **One reason passes where a list was rejected as a change log.** **Answer:** accepted. "Why one reason" rests on what the check reads, and the README's steps 2 and 3 are reopened for the one reason too.

**Counter-alternatives:**

26. **Refuse more reasons mechanically.** **Answer:** adopted, and stated generically after the architect's round.
27. **Answer on the dependant's side, in bulk.** **Answer:** weighed in "Alternatives". Not recommended.
28. **The first-parent line.** **Answer:** adopted.
29. **A release digest of reasons.** **Answer:** adopted in M7.
30. **Opt-in seeded by `pkit init`.** **Answer:** named in question 1's alternative.
31. **Sparse per-part markers.** **Answer:** adopted after the architect's round.

**The questions:**

32. **Ordering.** **Answer:** accepted. The rollout question is below the ones that shape the data.
33. **Questions settled silently.** **Answer:** (a) is question 2. (b) is question 3 after the architect's round. (c) is settled: each reason on the list and every reason in the release notes. (d) is settled: a marked document's undeclared step fails even with nothing anchored (settled position 15).
34. **Question 3's example stated something false.** **Answer:** rewritten.
35. **Question 1's cost should name more.** **Answer:** accepted.
36. **What works.** **Answer:** noted.

**Settled positions:**

37. **The quotes are accurate.** **Answer:** noted. Each added quote was checked against its record.

**Slicing:**

38. **M1 races other builds.** **Answer:** accepted (finding 15).
39. **M3 alone made the checks disagree.** **Answer:** accepted. After the architect's round the whole-repository check comes first, which is safe alone.
40. **#1438 is not independent.** **Answer:** accepted. Whichever of #1438 and M4 lands second handles the other.
41. **M1 contradicted "Settled positions".** **Answer:** fixed.
42. **Smaller gaps.** **Answer:** M6's segment is the maintainer's judgment. M7's home is the release README.

**Accuracy and agreement:**

43. **The code claims verified.** **Answer:** noted. `c2b98094`'s messages and the README's diff were read from git.
44. to 50. **Agreement:** noted.

### The architect

The architect found the direction sound, and the block's place in `friction` and the container on records right. It raised two concerns, ten fit issues, six drifts and four points worth recording, and an escalation. The largest change: question 3 now recommends a marker per part, so the reading stays a comparison of two states. Each finding is answered below, numbered as the architect numbered them.

**Architectural concerns:**

1. **Question 3 decides the engine's shape, and its alternative was undersold.** **Answer:** accepted. The recommendation is now a marker per part, with the document's own marker and one for the text outside every part. The reading compares two states, and only the undeclared-step test reads steps. The cases table and the settled positions are reworked. The measure asked for is reported ("Counts"): of the 38 shipped records changed since the last release, 25 have points and 6 had two or more points changed. Whether each point's edit kept its meaning was not classed, since that needs a person's judgment per edit.
2. **Question 1's default rested on a release that an untagged install never receives.** **Answer:** accepted. Trust by default covers content of a tagged methodology release only, and a development install's reasons spare nothing. Question 1 gains the argument that the project already runs the release's code, so no new party is trusted. Core rule 20 stays about answers written, and received reasons are listed under COR-050 point 12 and DEC-055. The duty's fix for a gap that reached receivers is a correction.

**Fit issues:**

3. **COR-050 should hold the reading.** **Answer:** accepted. COR-050 is refined in place for when an anchor has changed, deferrals, the cascade and debt. The new record holds the document's side. Question 6 says so.
4. **The homes.** **Answer:** accepted. A new friction home over `friction_history`, the reused homes, and the cost are in "The engine". ADR-057 point 2's refinement is due, in M1b.
5. **Composition with several revalidation points and debt.** **Answer:** accepted. Both are stated, and the two walking models are named.
6. **Cut and missing history.** **Answer:** accepted. A value whose newness cannot be established reads as not new, and a document with no history under private visibility reads as unmarked. Settled position 13 carries the CI sentence.
7. **Which validation member.** **Answer:** accepted. The friction member validates every meaning block, and the configuration member the key.
8. **COR-048's duties for the key.** **Answer:** accepted. Entries are checked against what is installed, uninstall offers to clear one, and `methodology` names the class.
9. **The mechanical refusals.** **Answer:** accepted. A point id is refused only where the record held it in neither form, so conversions pass. What binds is named generically, by the defining component.
10. **"The release check" named the wrong command.** **Answer:** accepted. The refusal is in `pkit release plan` and `apply`.
11. **Slice order and release safety.** **Answer:** accepted. The whole-repository check (M3) comes before the change check (M4), each safe alone. The key ships with its reader in M4. M1 is held from a release until M4 ships.
12. **A marked artefact that is also a dependant answers twice.** **Answer:** accepted. "Who decides" says so, M5 covers it, and the cascade follows the declared step (settled position 7).

**Drift:**

13. **project-management DEC-055 is touched.** **Answer:** accepted. Settled position 22 quotes it, and M4 builds its list and hold.
14. **COR-050's term "The diff".** **Answer:** accepted (settled position 2).
15. **COR-050's Implications on CI history.** **Answer:** accepted (settled position 13).
16. **The release refusal belongs in the realising ADR.** **Answer:** accepted. M1b holds it, and the release README the mechanics.
17. **ADR-057 point 2's refinement is due.** **Answer:** accepted (M1b).
18. **The untouched claims.** **Answer:** accepted. "Where it lives" says ADRs never cross projects, and COR-048's duties apply to the key.

**Worth recording:**

19. **The realising ADR gets a slice of its own.** **Answer:** accepted: M1b, after M1 and #1412, before M2.
20. **`check-shareable` should run the shipping-duty test.** **Answer:** accepted (M7).
21. **Settle the artefact form on a record now.** **Answer:** accepted. A decision record is anchored as a record only (settled position 4).
22. **PRJ-002 could say a kept edit declares `none`.** **Answer:** noted in "Found on the way" 4, not taken now, since a refinement that changes no surface needs no changeset already.

**Escalation:** the maintainer authorises the settled positions, among them the two foundational changes: COR-050 reads markers beside its two states (positions 5, 8 and 16), and a decision acts across projects (positions 11, 14 and 22, and question 1). Question 3 is decided first, since the reach of the reading depends on it. Records gaining the container is question 4.
