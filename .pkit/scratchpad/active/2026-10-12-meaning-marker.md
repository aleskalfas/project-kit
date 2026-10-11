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

A document others anchor may carry a marker that moves only when its meaning changes. Each edit to it either moves the marker or gives a reason why the meaning held. A dependant is asked only about an edit that changed, or may have changed, the meaning of the text it stands on.

- **The shape follows `at`'s (COR-050 point 3):** a timestamp `meaning.at` and a sentence `meaning.kept-because`, in the document's friction block. Each takes its point from the history, as `at` does.
- **An edit that writes neither** counts as a change of meaning, as every edit does today. It fails the change check in enforcing mode, and no later reason covers it.
- **The test of a kept meaning:** in the whole document and in each part the edit changes, no claim, term or citation changes, no reading is chosen, no text moves between parts, no heading a reader can name is removed or renamed, and nothing changes whether or how the document binds. Doubt moves the marker, as it does for W3C. The change check refuses a reason beside the structural changes it can see.
- **Who decides:** a person accepts each reason before it is written, since a reason spares dependants that person never sees (question 2).
- **What a dependant reads:** an edit with a reason asks nothing of a part it rewords. An edit that moves the marker, or gives neither, asks the dependants of each part whose text it changed. A marker moved with no text changed is a correction, and asks every dependant.
- **Where it lives:** in the friction block of whatever carries the methodology's container, a document or a collection entry such as a rule. Decision records gain the container for it. A part of a document reads its document's marker (question 3).
- **Across projects:** a received document is read by the same rule over the receiving project's own history, where it changes only at version transitions. Reasons spare a project's artefacts by default only for documents of the methodology's own release, which refuses to ship an edit that gave neither. A project can turn that off in its friction settings (question 1).
- **What a receiving project sees:** the latest reason on the list of the change that brings it, and every reason since its version in the release notes.
- **A wrong reason** is fixed forward: the receiving project revalidates what it doubts and reports it, and the authoring project's correction asks every dependant again.
- **It reopens** COR-050 points 1, 3 to 6, 9, 12, 13 and 15, its terms, three passages of its rationale and its Implications, COR-053 point 10, COR-051 points 2 and 7, core rule 20, the decisions README, and software-analysis DEC-001 point 6. The settings key also reopens COR-050 point 14.
- **It is a record of its own,** recommended (question 6), with refinements in place where it reaches other records.

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
- **Points are commits, so landing matters there already:** "where a line of work revalidates and then changes an anchor again, how it lands still decides the point" (COR-050, "Why a change is a difference between two states").

### A person decides every answer

- **The rule:** an answer is a person's decision when that person was shown it word for word and accepted it (COR-050 point 3, core rule 20).
- **Two timings:** an agent may write first the answers the change check asks of its change, and the person who authorises the merge is then shown the change check's list (`friction_check._written_answers`). Every other answer, and every reason for having no anchors, is accepted before it is written. COR-050's rationale gives the second timing to what "waives a measure".
- **The list holds** revalidations, deferrals and reasons for having no anchors. It is defined within one project's merge.

### Where an upstream author's word already acts in a receiving project

- **A shipped rule set's class of change.** A rule set's major moves when a rule is added, withdrawn, superseded or tightened (COR-051 point 7). Any other change binds through an inheriting set's pin without review.
  - **But the project opts in first.** A shipped rule set binds only through a set of the project's own with a scope (COR-051 point 7, refined on 11 October). The rationale rejects anything that "would take away a project's choice not to inherit the set".
  - **And friction stays as a second net.** A rule's dependants see any edit to it as friction (COR-051 point 2), and "a change to the inherited rule flags the fill" (point 7).
- **A shipped rule's own revalidation.** In a receiving project, method rule sets are walked as artefacts. A rule-set place is no declared place, so the synced-copy test does not skip it (`friction_discovery.discover_artefacts`, `rule_set_places`). So the revalidation written upstream on a rule of `LDOC` answers that rule's friction in the receiving project, on an upstream artefact only.
- **Code and migrations.** A project that chooses a target release runs that release's code and migrations (#1429, question 2).
- **No upstream answer clears friction on a project's own artefact today.**

### What a document others anchor is today

- **Decision records** carry no container. They are no artefacts unless they sit in a declared place (COR-050 point 1).
  - **Record front matter is read line by line** for its required keys (`validate._validate_decision_record`). An added `pkit` key breaks nothing there.
  - **The revision-marker warnings** read the body only, never the front matter (`decisions_validate.find_revision_narration`).
- **ADRs are artefacts too in project-kit.** All 61 sit under `tech-docs/`, inside living-docs' internal-root place. Discovery lists each as a document with no container.
- **Pages and analysis artefacts** are artefacts in places, with friction blocks.
- **Rules** are collection entries, each with its own friction block (COR-051 point 2).
- **The friction block's schema** refuses unknown keys (`.pkit/schemas/backbone/container.schema.json`, `friction`). It is bound to documents and entries in declared places.

### Counts

- **Shipped records:** 54 core records and 66 capability records reach adopters.
- **Anchored here:** 57 of them are anchored by project-kit's own artefacts, through 137 anchor values. 199 of 391 anchor values are record anchors.
- **Edits:** 53 commits on main touched a shipped record since 27 September.
- **Kept edits measured:** of the 182 answers a document's edit caused from 27 September to `30cfb15a`, 4 followed an edit that kept the meaning (the versioning note, "What history shows").
- **One coming:** #1421 converts 86 records' points to headings word for word, 40 of them shipped. Every whole-record dependant here, 28 artefacts, answers once.

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
- **The two checks agree:** what a change leaves unanswered is what the whole-repository check reports once it merges (COR-050, "Why the pull-request rule is local").
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

### The marker and the reason

A **marked document** is a document others anchor whose friction block holds a `meaning` block. It carries a marker, and after an edit that kept its meaning, a reason.

```yaml
pkit:
  friction:
    meaning:
      at: 2026-10-14T09:00:00Z
      kept-because: Writes the points as headings, word for word. No claim, term, citation or heading a reader can name changes.
```

- **The marker, `at`:** a UTC timestamp, read parsed, as `revalidated.at` is. It moves only when the meaning changes.
- **The reason, `kept-because`:** a sentence, read with its whitespace folded. It is replaced on each edit that keeps the meaning, and removed when the marker moves.
- **Why both:** within one project, an edit that classes nothing shows in the history. A receiving project holds only the states its transitions brought, so there it would hide behind a later reason. The authoring project moves the marker past such an edit before it ships ("Across projects"), so the marker carries every change of meaning across.
- **Why a timestamp:** it is `at`'s shape, readable, and new on every move. A commit id cannot name the commit it lands in, and a stored hash was rejected (COR-050, "Why a timestamp whose point comes from git").
- **Why one reason and not a list:** the check needs only the reason of the latest step to tell a kept step. A list adds entries no check reads, which two lines of work would both append to. The release notes give a receiving project every reason ("How a receiving project sees a reason").
- **Adding the block** changes no content, since the container is not content. It asks no dependant.

### Steps, and what each one declares

- **A step** is one change along the first-parent line of the history read: a commit on that line, or a merge taken against its first parent. In the change check, the change from base to head is one step. With a squash landing, each pull request is one step on the default branch.
- **What a step declares,** for a marked document whose content it changed:
  - **meaning changed:** the parsed marker is new. A value the document carried before is not new, as for `at`.
  - **meaning kept:** the marker held, and the folded reason is new in the same sense.
  - **nothing:** an *undeclared step*. It counts as a change of meaning.
- **A part:** what an anchor can stand on, the whole document, or a record's point, a page's section or lead, or a collection entry, each with what it stands on (#1387, "What a point stands on").
- **A meaning change of a part** is a step that changed the part's text and either moved the marker or declared nothing.
- **A correction** is a step that moves the marker and changes no content. It is a meaning change of every part. Removing the block is read the same way, and the document reads as unmarked after it.
- **Reverts:** a revert writes back an earlier marker or reason, which is not new. So a revert declares afresh: the revert of a kept edit gives a new reason, and the revert of a meaning change moves the marker to a new value. A conflict on the `at` or the `kept-because` line is resolved the same way, with a new value for the combined state, as COR-050 point 3 asks of a conflicting revalidation.

### The test of a kept meaning

An edit keeps the meaning when, in the whole document and in each part it changes, it:

- adds, drops, weakens or narrows no claim
- changes no term and no citation, and splits no claim into parts that disagree
- chooses no reading of a text that had two
- moves no text from one existing part to another, and removes, renames or splits no heading a reader or an anchor can name
- changes nothing that says whether or how the document binds: its `status`, what supersedes it, what it supersedes, or a "Partially superseded by" line

Doubt moves the marker.

- **The source:** project-kit's RS-WRITE-013 lists the first three. A core record states the test in its own words, since a core record suits any project (COR-014). WRITE binds project-kit's analysis and software-analysis's templates and structures, and no record (`.pkit/rules/project.md` rule 3).
- **"The whole document":** a whole-record anchor also stands on Context, Rationale and Implications, which are no parts. An added rejected alternative adds a claim there.
- **A title** is a claim. A retitle keeps the meaning only where the test holds for it.
- **#1421's conversion keeps the meaning.** It turns each point into a heading with the same id, and creates parts where the list form had none, so no existing part loses text.
- **What the change check refuses mechanically,** as a finding beside a reason: a change of `status`, `supersedes` or `superseded_by`, an added "Partially superseded by" line, a heading removed or renamed, a new point id, and a new `retired-points` entry. Each is visible from the two states. The rest of the test is judgment.

### Who decides

A person decides each reason. Question 2 asks when.

- **Recommended: accepted before it is written,** as a reason for having no anchors is (COR-050 point 3). A reason waives questions for dependants in every receiving project, which the person authorising this merge never sees. Edits that keep the meaning are rare, 4 of 182 answers in the count, so asking first interrupts little.
- **An agent with nobody to ask moves the marker.** A wrong "changed" only asks more.
- **The reason is still listed** on the change check's list, as an accepted reason for having no anchors is.
- **A moved marker needs no showing.** It spares nobody.
- **The writer:** a command of its own, named here `pkit friction meaning <document> (--changed | --kept-because <reason>)`. It writes one block and names what it writes (COR-050 point 13). `--changed` writes a new `at` and removes the reason. It refuses a reason the document carried before, reading the document's history as the check does.
- **A tool that converts word for word,** such as #1437's conversion, proposes the reason, and the person accepts it with the reviewed diff, before it is written.
- **A recorded reason is never reworded.** It is a person's decision, so a later edit replaces it whole.

### What a dependant reads

A dependant is asked about an edit to a marked document only where the text it stood on is no longer vouched for.

- **An anchor's last meaning change:** the newest step, on the later state's first-parent line, that was a meaning change of the part the anchor stands on.
- **Vouched text:** what the part held at its last meaning change, and at each step since. Every step since was kept, by the definition.
- **The rule:** an anchor on a marked document has changed between an earlier and a later state when the text it stands on differs between them, and the earlier text is not vouched for at the later state.
- **A part missing at either state** is never vouched for across. An anchor on a retired point, or on a part not there yet, reads as #1387 says.
- **A dependant that rests on the words,** such as a quotation, anchors the document's file by path. A path anchor compares the file and reads no marker.

**The cases,** for a dependant of point 11 of a marked COR-050, in project-kit, where each pull request is one step:

| Steps since the dependant revalidated | Asked? |
|---|---|
| a step with a reason rewords point 11 | no |
| two such steps, a week apart | no |
| a step moves the marker for point 5, and point 11 is untouched | no |
| a step with a reason rewords point 11, then a step moves the marker for point 5 | no |
| one step moves the marker for point 5 and rewords point 11 | yes |
| an undeclared step touches point 5 only | no |
| an undeclared step touches point 11, then a step with a reason touches it again | yes |
| the block is added, with no content change | no |
| a correction | yes, unless the text it stood on is the text now |

- **The change check,** for a step that changed a part's text:
  - **kept:** the dependants of that part are not asked. The base's text was vouched for at the base, and the head vouches for everything the base did.
  - **meaning changed, or undeclared:** they are asked, as today.
- **Where the change check reads history,** as it does already: for a dependant whose `at` the change writes back, or whose deferral it judges, it reads the target's vouched text at the head. It also reads history to tell a new marker or reason from one carried before, and for a correction or a removed block, where it judges each dependant against its own revalidation point.
- **The whole-repository check** walks the document's file back along the first-parent line to each anchor's last meaning change, reading the part at each step, as #1419's part walk does.
- **The two checks agree** for a squash or a merge landing, since each pull request is one step for both.
- **Where they part:** with a rebase landing, a line of work's commits become steps. An undeclared commit followed by a commit that adds the reason reads as a meaning change in the whole-repository check, while the change check read one kept step. The whole-repository check then asks more, as it does where COR-050's rationale lists the two checks parting.
- **Deferrals:** a deferral covers its anchor until the anchor changes since its deferral point, read by this rule (COR-050 point 4).
- **Debt** of an anchor on a marked document originates at the oldest meaning change of its part after the point it is measured from, after which the text it stood on stays unvouched (COR-050 point 9).
- **The cascade** goes on from a marked artefact only where its own step was a meaning change of what a dependant stands on.

### One marker per document, read per part

The marker belongs to whatever carries the methodology's container: a document, or a collection entry. A part of a document has no container of its own, so it reads its document's marker through its steps (question 3).

- **A record's point** reads the record's marker. A kept step spares its dependants, and a meaning change asks only the dependants of parts whose text the step changed.
- **A page's section** reads the page's marker.
- **A rule** is a collection entry, so it carries its own marker in its entry's block. So does any entry, such as a use case.
- **What one marker costs in project-kit:** a single step that changes the meaning of one point and rewords another asks the reworded point's dependants too. Two pull requests spare them.
- **What it costs in a receiving project:** a transition is one step. A transition that brings a meaning change anywhere in a record, with the marker moved, asks the dependants of every part whose text changed since the project's last transition, reworded parts included.
- **The alternative is a part's own marker,** a map in the meaning block that holds a timestamp only for parts whose meaning changed. It keeps the part's attribution across projects. It is optional, so it can be added later without a migration.

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
  - **An ADR that sits in a place** is an artefact too, so its friction block may already hold the block. It is the same block.
  - **Why the container, not the record's own fields:** the marker is friction's data, and COR-053 point 10 puts a functionality's data in the container and the artefact's own in its fields. `retired-points` sits outside, since it describes the record's own structure (#1387).
- **Which documents carry it:** only those whose owner adds the block. A document without one reads as today. Which of project-kit's documents carry one is question 5.
- **A marked document is never dormant:** an edit to it that declares nothing fails the change check in enforcing mode, whether or not anything here anchors it, since a receiving project's anchors are unknown.
- **The decisions README's ban on revision markers:** the block is data a tool reads, and the reason is the current step's answer, as `unchanged-because` is. Neither is in the body, and neither is added to. The README's steps 2 and 3 still forbid "a block stamped with a date" and a note that the record was amended in place, so their sentences change ("Settled positions").
- **A supersession** changes `status`, so it moves the marker. A superseded record then keeps its block as it stood.

### Across projects

A received document is read by the same rule, over the receiving project's own history.

- **Where it changes there:** only at version transitions, which bring the target release's methodology files (#1429). Each transition is one step of many upstream edits.
- **What a transition declares,** read like any step:
  - **a new reason under the same marker:** kept. It spares the parts whose text changed.
  - **a moved marker:** a meaning change of every part whose text changed.
  - **new content under the old reason:** undeclared, so a meaning change. On a synced copy it is never a finding of the receiving project's.
- **What a received reason claims:** that every edit since the project's last transition kept the meaning, not only the edit it was written for.
- **The shipping duty that makes that true:** a project that ships a marked document moves its marker past every undeclared step before it ships. Its change check fails an undeclared step in enforcing mode, and its whole-repository check reports one that landed anyway until the marker moves.
- **project-kit's release refuses** to release while a shipped marked document has an undeclared step since its marker's point (slice M7).
- **Whose reasons a project trusts:** a key in its friction settings, named here `received-reasons`, lists the components whose reasons spare its artefacts (question 1).
  - **Absent, it means the methodology's own release:** the backbone and the capabilities it ships, whose release enforces the shipping duty.
  - **A project narrows it,** to none for instance, and then every received edit asks as today.
  - **An externally-sourced capability** (COR-041) is trusted only where the project names it, since nothing here knows its release.
  - **An untrusted document reads as unmarked:** every edit to it asks.
- **Synced copies:** the receiving project cannot edit them. So nothing about a synced document's own declaration is a finding there: an undeclared step, a reason beside a refused change, and a malformed block are reported and never fail. A malformed block reads as no marker.

#### How a receiving project sees a reason

- **On the change check's list,** for the change that brings it: the document, the latest reason word for word, the component and version it came from, and the project's artefacts it spares.
- **In the release notes:** project-kit's release step lists, for each shipped marked document, every reason and marker move since the previous release (slice M7). A transition across several releases reads several entries. The latest reason alone does not describe every edit a transition brings.
- **In `pkit friction explain`,** for each anchor a reason spared.

#### Whose decision it is there

- **The person who authorises the merge** of the change that brings a reason is shown it on the change check's list, with the artefacts it spares. Where the change is committed straight to the default branch, the person the agent works for is shown it before the commit.
- **What that person accepts** is the authoring project's process, not each upstream edit: one reason, the diff, and the release notes. The trust is placed by the settings key, and the showing makes it visible within the receiving project's merge.

#### What it does about a wrong one

- **Before authorising the transition:** it revalidates each artefact the reason spared, in the same change. A revalidation that nothing asked for is always allowed, and is reported as such (`friction_check._judge`, "revalidated with no changed anchor").
- **After the merge:** the same, once noticed. It reports the reason upstream (`pkit report bug`).
- **For good:** it narrows `received-reasons`.
- **Upstream corrects forward:** a correction moves the marker without changing the content. Every dependant whose text differs from the current text is then asked, in every project, at its next transition.
- **Upstream never rewrites a reason it shipped** to fix it, as a released version is never modified (Semantic Versioning, item 3).

### The checks

What a script checks that an edit wrote, and what it never checks.

- **Validation,** from the working tree (COR-055 point 2):
  - **the block's shape:** `at` a UTC timestamp, `kept-because` non-empty text, no other key, and no `kept-because` without `at`
  - **on a record outside a declared place:** a container that holds anything but `friction.meaning` is reported as inert, as COR-053 point 10 says of a container elsewhere
  - **in a held document:** a `meaning` block is an error, as any friction block is (COR-050 point 12)
  - **`received-reasons`:** each entry names a component
  - **on a synced copy:** reported, never failing
- **The change check,** for each marked document whose content the change altered:
  - **the step's declaration,** read as above
  - **undeclared:** a finding owned by the change, failing in enforcing mode, and the dependants are asked
  - **a reason beside a refused change** ("The test"): a finding owned by the change, and the step reads as a meaning change
  - **a reason left beside a moved marker:** reported
  - **on a synced copy:** none of these is a finding
  - **the list** gains each reason the change wrote, and each reason it brought from another project, with the artefacts each spares
- **The whole-repository check:**
  - each anchor on a marked document read by the rule above, per part
  - **a marked document with an undeclared step since its marker's point,** reported where it is authored, whatever depends on it, never on a synced copy
- **The release check (project-kit):** refuses a shipped marked document with an undeclared step since its marker's point.
- **Never checked:** that an edit kept the meaning, beyond the refused changes. That is the person's judgment, as `unchanged-because` is.

### The records it touches

- **A new core record,** "A document others anchor marks an edit that keeps its meaning" (title provisional), recommended in question 6:
  - the marker, the reason, steps and their declarations, the test and its refusals
  - who decides and when
  - the reading by vouched text, per part, the correction and the cascade
  - the container on decision records
  - received reasons, the trust setting, the showing, the shipping duty and synced copies
- **Refined in place, with a pointer to it:** COR-050, COR-053 point 10, COR-051 points 2 and 7, core rule 20, the decisions README, and software-analysis DEC-001 point 6 ("Settled positions this reopens").
- **ADR-057 point 2:** the architect places the readings. The meaning block is likely read in artefact discovery, and a record's container in the home of a record's points (#1412).
- **The release README** documents the release refusal and the digest. PRJ-002 is untouched.
- **COR-025's ADR schema** takes the README's schema by reference. Its illustrative block is refined by #1422 already, and at most gains the container line.
- **Untouched:** COR-010 and PRJ-002.
- **No migration is due (COR-010):** the block and the key are optional additions. A document without a block reads as today. An adopter's dependants are asked at most once more, by a transition that brings a first marker with other edits.

## Alternatives weighed

- **For what a meaning change resets:**
  - **Every part, whenever the marker moves.** The change check would then need history on every marker move to ask the dependants of untouched parts, or the checks would disagree. Not taken.
  - **The parts whose text the step changed.** Taken. A correction resets every part, since it changes no text and stands for none.
- **For what a step is:**
  - **Each commit.** Two commits on a branch, an undeclared edit and then the reason, would read as a meaning change after a merge landing and as kept after a squash. That is what COR-050's "Why a change is a difference between two states" rejects. Not taken.
  - **Each step on the first-parent line.** Taken. It parts from the change check only for a rebase landing.
- **For an undeclared step:** covered by a later reason, it would hide an edit nobody classed. Rejected.
- **For the reason's form:** a list of every reason since the marker moved, in the front matter. Not taken ("Why one reason"). The release notes carry the list instead.
- **For the marker:**
  - **Reasons with no marker.** A receiving project could not see a meaning change hidden behind a later reason. Rejected.
  - **A number, moved by one on each meaning change.** Two lines of work that each change the meaning write the same number for two texts, as PRJ-002 found for components. Rejected.
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
- **Recommended: by default,** for documents of the methodology's own release, with a key in the friction settings, `received-reasons`, that a project narrows or turns off.
  - **Its cost:** an upstream author's reason clears friction on artefacts that author never saw. The receiving person sees the latest reason on the list and every reason in the release notes, and can accept them unread. The second net COR-051 keeps, friction on a rule's edit, goes for kept edits. COR-050 points 3 and 14 and core rule 20 change.
- **Alternative: only where the project opts in,** as a shipped rule set binds only through a set of the project's own (COR-051 point 7). `pkit init` could seed the key with the methodology's components.
  - **Its cost:** a project without the key gets nothing, and seeding it at a transition is a configuration write COR-048 point 5 allows only where the owning record names it.

### 2. Is a reason accepted before it is written, or written first and shown before the merge?

- **The question:** an agent edits a marked record and judges that the meaning held. Does it ask the person before it writes the reason, or write it and show it on the change check's list before the merge is authorised?
- **Example:** an agent fixes a typo in COR-017 point 4. It asks "Kept: Fixes a typo in point 4. No claim, term, citation or heading changes. Accept?", or it writes that reason and it appears among the answers the change wrote.
- **Recommended: accepted before it is written,** as a reason for having no anchors is. A reason waives questions in projects the merge's authoriser never sees, and kept edits are rare. An agent with nobody to ask moves the marker.
  - **Its cost:** an agent stops to ask on each kept edit, and core rule 20's list of what is accepted first grows.
- **Alternative: written first,** as the answers the change check asks of a change, shown on the list before the merge.
  - **Its cost:** the strongest answer there is gets the weaker timing, in a list where it can be accepted unread with the rest.

### 3. Does the marker belong to the document, or to each part an anchor can name?

- **The question:** one marker per document, read through each part, or a marker of its own for each part whose meaning changed?
- **Example:** one release of project-kit carries two pull requests. One changes what COR-050 point 5 requires, and moves the marker. The other rewords point 11 under a reason. In project-kit, a journey anchored to `COR-050#11` is not asked. An adopter's transition brings both as one step with the marker moved, so the adopter's journey on point 11 is asked.
- **Recommended: one per document now.** It needs no part ids in the block, and the part map can be added later without a migration.
  - **Its cost:** in a receiving project, a transition that brings a meaning change anywhere in a record asks the dependants of every part whose text changed, reworded parts included.
- **Alternative: a part's own marker,** a map in the meaning block with a timestamp only for parts whose meaning changed, such as `parts: {"5": 2026-10-14T09:00:00Z}`.
  - **Its cost:** each meaning change names its parts in the writer, one more map, and a renamed section leaves a stale entry. Every reading and every check reads it.

### 4. Where does a decision record carry the marker?

- **The question:** in the methodology's container, as an artefact does, or as the record's own fields?
- **Example:** COR-050's front matter gains either `pkit: {friction: {meaning: {at: …}}}` or two top-level fields, `meaning-at` and `meaning-kept-because`.
- **Recommended: the container.** The marker is friction's data, and COR-053 point 10 keeps the methodology's data in the container. A record anchor then reads the record without it, as an artefact anchor reads an artefact.
  - **Its cost:** records gain the container. COR-053 point 10 and COR-050's "for a record, the record's file" change.
- **Alternative: the record's own fields,** outside the container, as `retired-points` is.
  - **Its cost:** friction's data among a record's own fields, against COR-053 point 10's split. An ADR in a place would have two spellings for one fact, and a record anchor must leave out two named fields.

### 5. Which of project-kit's documents carry a marker before the first adopter?

- **The question:** a marked document asks its author one choice on every edit. Which documents take that cost?
- **Example:** a maintainer fixes a typo in COR-017. If COR-017 is marked, the pull request fails the change check until the edit gives a reason or moves the marker.
- **Recommended:** every accepted record project-kit ships, of 54 core and 66 capability records, and the rules of `LDOC`. Adopters' anchors are unknown. A proposed record gains the block when it is accepted, since nothing anchors it before. A superseded one is not edited.
  - **Its cost:** one choice on each edit of those records. 53 commits on main touched a shipped record since 27 September.
- **Alternative:** only the 57 shipped records project-kit's own artefacts anchor today, and others as adopters ask.
  - **Its cost:** an adopter that anchors an unmarked record is asked on every edit to it, and marking it later spares only what follows.

### 6. Is it a record of its own?

- **The question:** a new core record, or a refinement of COR-050 in place?
- **Example:** the rule "a received reason spares a project's artefacts only for the components its settings trust" lives either in a new record, with COR-050 point 3 pointing at it, or as further sentences in COR-050.
- **Recommended: a record of its own.** It holds a new principle, a document's own declaration about its edits, with its own rationale and alternatives, and the trust across projects. COR-050 is refined in place where the new record reaches it, with a pointer.
  - **Its cost:** one more core record, and pointers in COR-050.
- **Alternative:** refine COR-050 in place.
  - **Its cost:** COR-050, 167 lines and refined for parts by #1419 and #1423, gains a third concern beside anchors and answers.

## Settled positions this reopens

Each accepted sentence below changes, for the maintainer's authorisation. The refinements land in M1, after the new record is accepted, each in a commit of its own.

1. **COR-050's terms and point 5, what a record anchor stands on:** "What an anchor **stands on** is, for a path, the files it matches (point 7 says which the excluded paths leave in); for a record, the record's file" and "**A record anchor** has changed when the record's file differs, followed across a rename."
   - **The change:** a record anchor stands on the record's content, its container left out. A record without a container reads as before, except that an edit to its front matter's layout alone is no change.
2. **COR-050 point 1, where the container is read:** "Everything this record owns in an artefact sits in **one functionality block, named `friction`**, inside the methodology's front-matter container" and "The backbone looks for artefacts only in the **places declared to hold anchored artefacts**, so unrelated front matter elsewhere is never misread."
   - **The change:** a decision record's friction block, which holds the meaning block alone, is read wherever the record lives.
3. **COR-050 point 5, when an anchor changed:** "**An artefact anchor** has changed when that artefact's **content** changed" and "**Three answers**, judged from the diff [...] clear friction".
   - **The change:** an anchor on a marked document has changed only where the earlier text is no longer vouched for. A kept step is no answer of the dependant's. It keeps the dependant from being asked.
4. **COR-050 point 4, deferrals:** "Where the anchor has changed since — what it stands on differs from what it stood on there (point 5) — that is new friction."
   - **The change:** for an anchor on a marked document, "changed" is read by the vouched-text rule.
5. **COR-050 point 6, the cascade:** "An artefact anchored to another artefact is included when that artefact's content changed in the pull request. The cascade continues only where a revalidation itself changes content."
   - **The change:** for a marked artefact, only where its step was a meaning change of what the dependant stands on.
6. **COR-050 point 9, debt:** "*stale* debt originates in the oldest commit from which a part of what the anchor stands on [...] has differed, without returning, from what it was at the point it is measured from".
   - **The change:** for an anchor on a marked document, at the oldest meaning change after that point from which its text stays unvouched.
7. **COR-050 point 3, a person's decision:** "An answer is a person's decision when that person was shown it — the artefact, the outcome, and the justification or the deferral's reason, word for word — and accepted it." and "Every other answer an agent writes, on an artefact its change was not asked about, and every reason for having no anchors (point 1), is written only after a person was shown it and accepted it."
   - **The change, under question 2:** a reason an edit keeps the meaning is accepted before it is written. A reason a change brings from another project is shown on the change check's list to the person who authorises it.
8. **Core rule 20:** "A revalidation, a deferral or a reason for having no anchors (COR-050 points 1 and 3) is written only after a person was shown it and accepted it, with one exception."
   - **The change:** the list gains a reason an edit keeps a document's meaning, and the rule names the reasons a change brings from another project.
9. **COR-050 point 12, findings and failures:** "**The change check finds:** friction of the pull request, dead anchors of the pull request, a bump with nothing behind it, [...]", "In **enforcing mode** it fails on the first five", "**Reported only, in every mode:** [...] the answers the change wrote, each with its words (point 3)", and "**Validation owns:** a malformed block, [...]".
   - **The change:** the change check also finds an undeclared step and a reason beside a refused change, owned by the change and failing in enforcing mode, never on a synced copy. The answers reported include reasons written and received. Validation owns the meaning block's shape and the key's entries.
10. **COR-050 point 13 and its Implications, the writers:** "Writing is always a separate, explicit command that names what it writes: revalidate, defer, record the status." and "**The backbone ships the writing commands** for revalidating, deferring and recording the status".
    - **The change:** a fourth writer declares a document's meaning.
11. **COR-050 point 14, project settings:** "It holds the friction mode (default: warning), when the status job runs (default: never), the project's own anchored places, its declared surface, and its excluded paths (all default: none)."
    - **The change, under question 1:** it also holds `received-reasons`, by default the methodology's own components.
12. **COR-050 point 15, dormancy:** "Where no artefact declares anchors, the check finds nothing and demands nothing."
    - **The change:** a marked document's undeclared step is a finding even where nothing is anchored.
13. **COR-050's rationale:**
    - "Why the pull-request rule is local to the pull request": "Both checks ask the same question — does what an anchor stands on differ between two states [...]". For a marked document, both also read the steps between.
    - "Where the two checks part": "The two checks part in a few cases." It gains the rebase landing.
    - "Why a change is a difference between two states": "Which commits touched an anchor depends on how a change lands: a merge keeps them, a squash or a rebase folds them into one." The marker reading counts steps on the first-parent line, and says why that is landing-safe for a squash and a merge.
14. **COR-053 point 10:** "An artefact's front matter — for a collection entry, the entry itself — may hold **one** key owned by the methodology, named for it" and "Any artefact may carry the container; validation reaches only the artefacts in declared places (COR-050 point 1), so a container elsewhere is inert."
    - **The change, under question 4:** a decision record may carry the container too, with a friction block holding the meaning block alone, which friction reads and validation checks wherever the record lives.
15. **COR-051 point 2, "Anchoring":** "Editing a statement, or accepting, superseding or withdrawing a rule, is therefore a change that the rule's dependants see as friction. Nothing keeps silently obeying a rule that has changed."
    - **The change:** an edit of a marked rule's statement in a kept step asks its dependants nothing. A change of its status always does.
16. **COR-051 point 7, fills:** "A filling rule anchors to the rule it fills, so a change to the inherited rule flags the fill."
    - **The change:** a kept step on a marked inherited rule flags no fill, where the fill's project trusts the rule's component.
17. **The decisions README:**
    - **"Schema":** "Each record is a Markdown file with YAML frontmatter and four required sections:". The front matter may also hold the container with its meaning block.
    - **"Refining an accepted record", step 2:** "**Add no revision marker** — no amendment heading, no block stamped with a date or an issue number, no note that the record was amended in place rather than superseded." The meaning block is data a tool reads, and the reason is the current step's answer, replaced on each step. The step names both as no revision marker.
    - **Step 3:** "**Leave no residue of the change.** A word that makes sense only against the old text — "now", "no longer", "still", "corrected above" — is restated as plain fact." The reason describes the step, in the front matter only, and the step says so.
    - **The same section gains** that an edit to a marked record declares its step, and that a supersession moves the marker.
18. **software-analysis DEC-001 point 6:** "the capability's artefacts and records carry no declared versions", and its rationale: "A version an author declares on a document would tell a dependant one fact, whether the meaning changed [...] So the capability's artefacts and records carry no declared versions".
    - **The change:** the sentence allows a declared meaning marker, the one fact the rationale names, and still no version number.

**Not reopened:**

- **COR-050's rejected alternatives:** "A commit identifier or a content hash as the marker" stays rejected, since the marker is a timestamp. "A bare marker change as an answer" stays rejected, since a moved marker answers nothing and spares nobody.
- **COR-051 point 7's majors:** a rule edited in a kept step makes no major due, since the test forbids tightening.
- **COR-025's ADR schema:** by reference to the README's.

**Decided designs it changes,** not yet accepted records:

- **#1387's first case,** "The part's text changes: its dependants are flagged." A part changed in a kept step flags nobody.
- **#1383's question 2,** "not now", which the maintainer reopened on 11 October.

## Slicing

A draft of the build, for filing after the maintainer decides. Each record is accepted before the work that cites it. The build lands before the first adopter.

- **M1, [Docs] A core record says a document others anchor marks an edit that keeps its meaning:**
  - authored with `pkit new decision core` through the decision-author skill, and reviewed by the critic, the architect and the methodology-reviewer
  - the refinements in place of "Settled positions" 1 to 18 in the same change, each in a commit of its own, with a pointer to the new record
  - **after the refinements of COR-050 by #1419 and #1423 are accepted,** so the refinements do not race. Names #1422, which edits the decisions README's refining and schema sections and COR-025's block: whichever lands second builds on the other.
  - a `none` changeset for each component whose records it edits (PRJ-002)
- **M2, [Task] The meaning block, its schema, validation, its writer and the trust key:**
  - the container schema gains `meaning` in the friction block, and binds records too
  - validation's friction member checks an artefact's block, and its decisions member a record's, reporting and never failing on a synced copy
  - `pkit friction meaning`, with consent as the other writers, refusing a reason carried before
  - `received-reasons` in the friction settings, as question 1 decides
  - the architect names the readings' homes, and refines ADR-057 point 2 first if they change it
  - **Safe alone:** no check reads the block yet, so dependants read as today.
  - **Docs:** the schemas README's "The friction block", the CLI reference. A backbone minor.
- **M3, [Task] The change check reads a marked document's step:**
  - a record anchor reads the record without its container
  - the step's declaration, the undeclared step, the refused changes, and synced copies
  - dependants spared by a kept step, per part, and the cascade
  - the history it reads for a written-back `at`, a deferral, a correction and a removed block
  - the list's written and received reasons, in its human and JSON forms
  - **after M2, #1408 and #1419.** Names #1423: whichever lands second reads page sections.
  - **Held from a release until M4 ships,** as #1387 held its COR-050 refinement until friction for points shipped, since alone it makes the two checks disagree. A backbone minor.
- **M4, [Task] The whole-repository check, debt and explain read vouched text:**
  - each anchor's last meaning change along the first-parent line, and vouched text, per part
  - deferrals and debt by the rule, and `explain` naming the reason that spared an anchor
  - the document finding, an undeclared step since the marker's point, never on a synced copy
  - **after M3.** A backbone minor.
- **M5, [Task] The skills and agents that edit a marked document ask for its declaration:**
  - the decision-author skill when it refines a marked record, the analysis-author skill, living-docs' agent, and the agents README's "Friction writers"
  - the guidance that a dependant resting on the words anchors the file by path
  - after M2
- **M6, [Docs] project-kit marks the documents it ships,** as question 5 decides:
  - the block, with no reason, on each document, through the writer. No dependant is asked, since no content changes
  - `.pkit/lifecycle/README.md`, which quotes COR-053 point 10, anchors COR-053's file by path
  - CONTRIBUTING.md says that an edit to a marked record declares its step
  - **after M4, and after #1421,** so the conversion of project-kit's records lands as planned. Marking first would spare the conversion's 28 answers, but would hold the part-anchor build behind this one.
  - a changeset for each component whose records it marks, its segment the maintainer's judgment (PRJ-002)
- **M7, [Task] project-kit's release refuses an undeclared step, and lists every reason:**
  - the release check refuses while a shipped marked document has an undeclared step since its marker's point
  - the release notes list, for each shipped marked document, every reason and marker move since the previous release
  - **Docs:** the release README. After M4.

**Order:** M1, then M2, M3 and M4 in turn, then M5 and M7, then M6, then the first adopter.

**Against the filed builds:**

- **Part anchors, #1403 to #1427:** M1 after the refinements of #1419 and #1423, beside #1422. M3 after #1408 and #1419. M6 after #1421.
- **Conversions, #1431 to #1444:** #1438 converts an adopter's records. Once markers exist, a conversion of a marked record declares its step, with the reason proposed and accepted with the reviewed diff (#1437). Whichever of #1438 and M3 lands second handles the other.
- **The version transition, #1455 to #1465:** independent. A received reason is read over whatever brings the document, today's sync or the transition after #1460.
- **Rule-set versions, #1449 and #1450:** #1450's check may read a rule's marker (Found on the way 4).

## Found on the way

1. **An ADR in project-kit is both a record and an artefact.** The 61 ADRs sit inside living-docs' `tech-docs/**` place. An anchor `record: [ADR-049]` reads the file, and `artefact: [ADR-049]` reads its content without the container. Under this design both read the content without the container. Whether one form should be refused is a question of its own.
2. **A receiving project's checks judge upstream rules.** Method rule sets are walked as artefacts there ("Today"). An upstream rule left stale upstream would be reported in every receiving project, which cannot edit it. Whether a receiving project should judge rules it cannot edit is a question of its own.
3. **Quotations of records** exist in project-kit's pages, such as `.pkit/lifecycle/README.md`'s of COR-053 point 10. Each anchors the record whole today, and is asked on every edit. A check that a quotation still matches its source would be a rule of LDOC's, not friction's.
4. **A rule edited in a kept step makes no major due** (COR-051 point 7), since the test forbids tightening. #1450's check could skip such edits. #1449 decides what each part of a set's version means.

## Review

### The critic

The critic found four red flags, twelve gaps, nine weak arguments and six counter-alternatives, with notes on the questions, the settled positions, the slicing and the code claims. The largest changes: a meaning change resets only the parts whose text it changed, steps follow the first-parent line, trust is placed by a settings key, and a new question asks when a reason is accepted. Each finding is answered below, numbered as the critic numbered them.

**Red flags:**

1. **A marker move reset every part, but the change check asked only the changed ones, so the checks disagreed.** **Answer:** accepted, with the critic's fix (b). A meaning change resets only the parts whose text the step changed, so the change check needs no history for it. A correction, a marker move with no text changed, resets every part, and the change check judges it against each dependant's revalidation point ("What a dependant reads"). The table's rows and question 3's example are rewritten, and the perverse incentive is gone, since an undeclared step and a marker move now reset the same parts.
2. **An undeclared edit was defined per commit, so landing decided it.** **Answer:** accepted. A step is one change on the first-parent line, so a squash and a merge landing read alike. A rebase landing parts the checks, and COR-050's "Where the two checks part" and "Why a change is a difference between two states" are among the settled positions (13). A merge from main into a branch is a step against its first parent, so main's new reason reads as kept there.
3. **The trust argument did not hold: one reason covers many edits, and only project-kit enforces the shipping duty.** **Answer:** accepted in both parts.
   - **What is shown:** the release notes list every reason and marker move since the previous release (M7). The note says plainly that the receiving person accepts the authoring project's process ("Whose decision it is there").
   - **Whose reasons:** by default only the methodology's own release, which enforces the duty. An externally-sourced capability is trusted only where the project names it, and an untrusted document reads as unmarked.
4. **COR-051 point 7's fill sentence changes, though the note said point 7 was not reopened.** **Answer:** accepted. Settled position 16 quotes it, and "Not reopened" keeps only the majors.

**Gaps:**

5. **Findings on synced copies would fail a receiving project on files it cannot edit.** **Answer:** accepted. Nothing about a synced document's own declaration is a finding there, in the change check or validation. A malformed block reads as no marker.
6. **"The change check needs no history" was false.** **Answer:** accepted. The note now says where it reads history: a written-back `at`, a deferral, a new value, a correction and a removed block.
7. **Removing the block was undefined.** **Answer:** accepted. It is read as a correction, a meaning change of every part, and the document reads as unmarked after it.
8. **Debt was dated from the wrong meaning change.** **Answer:** accepted. It originates at the oldest meaning change after the point from which the text stays unvouched (settled position 6).
9. **Reverts and conflicts on `at` were not covered.** **Answer:** accepted. A revert declares afresh, and a conflict on either line is resolved with a new value ("Steps").
10. **The test had holes.** **Answer:** accepted in each part.
    - It applies to the whole document and to each part, so Context, Rationale and Implications count.
    - Citations are in it, and so are a "Partially superseded by" line and a split heading.
    - A title is a claim.
    - #1421's conversion creates parts where none were, so no existing part loses text.
11. **Dependants that rest on the words exist.** **Answer:** accepted. `.pkit/lifecycle/README.md` quotes COR-053 point 10. Such a dependant anchors the file by path, which reads no marker. M5 carries the guidance and M6 re-anchors the README. The false claim is gone.
12. **The settled positions were incomplete.** **Answer:** accepted. Added, each quoted: COR-050 points 1, 4, 12 (enforcing and validation), 14 and 15, three passages of its rationale and its Implications, COR-053 point 10's first sentence, the decisions README's schema sentence and steps 2 and 3, and COR-051 point 7. "Why the container is not content" needs no change: its reason holds for records as written.
13. **The writer and the check disagreed on a valid reason.** **Answer:** accepted. The writer refuses any reason the document carried before.
14. **Proposed and superseded records.** **Answer:** accepted. Question 5 marks accepted records. A proposed record gains the block on acceptance, and a superseded one is not edited.
15. **#1422 and #1423 touch the same records.** **Answer:** accepted. M1 waits for #1423's refinement too, and names #1422.
16. **"In short" overstated.** **Answer:** fixed, with the reopened points listed and terms in plain words.

**Weak reasoning:**

17. **The reading of practice was confirming.** **Answer:** accepted. Practice now reads as one party proposing a class and another accepting it, and the note names the second party here.
18. **Placing a reason under core rule 20's exception was circular.** **Answer:** accepted. It is question 2, recommending acceptance before the reason is written, and an agent with nobody to ask moves the marker.
19. **COR-051 point 7's precedent points to opt-in.** **Answer:** accepted. "Today" says so, with friction as COR-051's second net. Question 1 now recommends a default a project can narrow, as npm writes a caret range a project can pin, and names the opt-in as the alternative.
20. **Question 1's alternative cost was overstated.** **Answer:** accepted. The alternative names seeding by `pkit init`, and the limit COR-048 point 5 sets on seeding at a transition.
21. **`c2b98094` supports the per-part clause, not the heading clause.** **Answer:** accepted. "Today" says the per-part test catches the fold, and the heading clause rests on dependants that name structure.
22. **software-analysis DEC-001 point 6 was redefined, not changed.** **Answer:** accepted. Settled position 18 says the sentence changes to allow a meaning marker.
23. **Question 3's alternative was undersold.** **Answer:** accepted. The alternative is a sparse map, and its strongest benefit, a part's attribution across projects, is the recommendation's cost.
24. **RS-WRITE-013 was used as authority for a core rule.** **Answer:** accepted. The note says in its own words that a recorded reason is never reworded, since it is a person's decision.
25. **One reason passes where a list was rejected as a change log.** **Answer:** accepted. "Why one reason" rests on what the check reads and on conflicts between lines of work, and the README's steps 2 and 3 are reopened for the one reason too.

**Counter-alternatives:**

26. **Refuse more reasons mechanically.** **Answer:** adopted: a status or supersession change, a "Partially superseded by" line, a removed or renamed heading, a new point id and a new `retired-points` entry.
27. **Answer on the dependant's side, in bulk.** **Answer:** weighed in "Alternatives". Not recommended, for the churn of a revalidation point per dependant per edit, and kept as what remains for a project that trusts no received reason.
28. **The first-parent line.** **Answer:** adopted (red flag 2).
29. **A release digest of reasons.** **Answer:** adopted in M7.
30. **Opt-in seeded by `pkit init`.** **Answer:** named in question 1's alternative.
31. **Sparse per-part markers.** **Answer:** question 3's alternative.

**The questions:**

32. **Ordering.** **Answer:** accepted. The rollout question moves below the two that shape the data.
33. **Questions settled silently.** **Answer:** (a) is question 2. (b) is settled in the design, since only resetting the changed parts lets the change check work without history, and question 3 states its cost. (c) is settled: the latest reason on the list and every reason in the release notes. (d) is settled: a marked document's undeclared step fails even with nothing anchored, since a receiving project's anchors are unknown (settled position 12).
34. **Question 3's example stated something false.** **Answer:** rewritten for both projects.
35. **Question 1's cost should name more.** **Answer:** accepted: the latest reason alone on the list, whose upstreams are trusted, and the opt-in precedent.
36. **What works.** **Answer:** noted.

**Settled positions:**

37. **The quotes are accurate.** **Answer:** noted. The added quotes were checked against the records the same way.

**Slicing:**

38. **M1 races other builds.** **Answer:** accepted (finding 15).
39. **M3 alone makes the checks disagree.** **Answer:** accepted. M3 is held from a release until M4 ships, and each slice says whether it is safe alone.
40. **#1438 is not independent.** **Answer:** accepted. A conversion declares its step, with the reason accepted with the reviewed diff, and whichever lands second handles the other. Whether a tool may propose a reason is in "Who decides".
41. **M1 contradicted "Settled positions".** **Answer:** fixed. The refinements land in M1, each in a commit of its own.
42. **Smaller gaps.** **Answer:** M6's segment is the maintainer's judgment by PRJ-002. M7's home is the release README.

**Accuracy and agreement:**

43. **The code claims verified.** **Answer:** noted. `c2b98094`'s messages and the README's diff were read from git for the note.
44. to 50. **Agreement:** noted. The terms used early in "In short" are now plain words.
