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

A document others anchor may carry a **meaning marker**. Each edit to it either moves the marker, because the meaning changed, or gives a reason why the meaning held. A dependant is asked only about an edit that changed the meaning of what it stands on.

- **The shape follows `at`'s (COR-050 point 3):** a timestamp `meaning.at` and a sentence `meaning.kept-because`, in the document's friction block. Their points are the commits that first carried them.
- **The test of a kept meaning:** in every part the edit changes, no claim is added, dropped, weakened or narrowed, no term is changed, no reading is chosen, and no heading a reader can name is removed, renamed or moved. A change of status never keeps the meaning. Doubt moves the marker, as it does for W3C.
- **Who decides:** a person. A reason answers for every dependant, so it joins the answers a change wrote, shown word for word before the merge is authorised (core rule 20).
- **What a dependant reads:** the document *vouches* for the text it held at its last meaning change and at each kept edit since. A dependant is asked only where the text it stood on is no longer vouched for.
- **An edit that declares nothing** is a meaning change, as today. It fails the change check in enforcing mode, and is never hidden by a later reason.
- **Where it lives:** in the friction block of whatever carries the methodology's container: a document, or a collection entry such as a rule. Decision records gain the container for it. A part of a document, such as a record's point, reads its document's marker.
- **Across projects:** a received document is read by the same rule over the receiving project's own history, where it changes only at version transitions. A reason it brings is shown on that change's list, so it becomes the receiving project's decision as an agent's answer does.
- **A wrong reason** is fixed forward: the receiving project revalidates what it doubts and reports it, and the authoring project moves the marker, which asks every dependant the reason spared.
- **It reopens** COR-050 points 3, 5, 6, 9, 12 and 13 and its terms, COR-053 point 10, COR-051 point 2, core rule 20, the decisions README, and software-analysis DEC-001 point 6. COR-025's schema and COR-050 point 14 stay as they are under the recommendations.
- **It is a record of its own,** recommended, with refinements in place where it reaches other records.

## Today

### Friction reads a change as a difference between two states

An anchor changed when what it stands on differs between two states (COR-050 point 5). Nothing a target says about its own edit is read.

- **A record anchor** stands on the record's file.
  - **The change check** asks only whether the record's file is in the diff, and treats a rename with identical content as no change (`friction_check._anchor_changed`, `friction_git.DiffEntry.changes_content`).
  - **The whole-repository check** compares the file's object at each revalidation point with the latest commit (`friction_repository._Judge.since`).
- **An artefact anchor** stands on the artefact's content: its body and its own fields, never the container (`friction_discovery.content`, `friction_repository._Judge._target_since`).
- **The revalidation point** is the commit where the artefact first carried the parsed value of `at`. A value written back keeps its old point (`friction_history.Walker.carried`, `Walker.points`).
- **An answer** is `updated`, `unchanged` with a new `unchanged-because`, or a deferral (`friction_check._revalidation`, `_judge`).
- **The cascade** goes on only where a revalidation changes the artefact's content (COR-050 point 6).

### A person decides every answer

- **The rule:** an answer is a person's decision when that person was shown it word for word and accepted it (COR-050 point 3, core rule 20).
- **The exception for a change:** an agent may write first the answers the change check asks of its change. The person who authorises the merge is then shown the change check's list of every answer the change wrote (`friction_check._written_answers`, `WrittenAnswer`).
- **The list holds** revalidations, deferrals and reasons for having no anchors. It is defined within one project's merge.

### Where an upstream author's word already acts in a receiving project

Three mechanisms already let a project that ships content decide something for the projects that receive it.

- **A shipped rule set's class of change.** A rule set's major moves when a rule is added, withdrawn, superseded or tightened (COR-051 point 7). A change the author does not class as a major binds through every inheriting set's pin without review.
  - **Since 11 October,** a shipped rule set binds only through a set of the project's own with a scope (COR-051 point 7). So the project opts in per set, and then trusts its author's class.
- **A shipped rule's own revalidation.** In a receiving project, method rule sets are walked as artefacts. A rule-set place is no declared place, so the synced-copy test does not skip it (`friction_discovery.discover_artefacts`, `rule_set_places`).
  - **So the revalidation written upstream** on a rule of `LDOC` answers that rule's friction in the receiving project. The change that brings it lists it as an answer the change wrote.
  - **It acts only on upstream artefacts.** No upstream answer clears friction on a project's own artefact today.
- **Code and migrations.** A project that chooses a target release runs that release's code and migrations (#1429, question 2).

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

### A kept edit that still asked something of a dependant

On 11 October, `c2b98094` folded the amendment sections of PRJ-008 and of project-management's DEC-028, DEC-032 and DEC-046 into their decisions.

- **Each message says** "No claim is added, dropped or changed". That sentence is the reason this design would ask for.
- **Yet the software-engineering README changed in the same commit.** It is anchored to DEC-028 and DEC-032, and it named "the `type`-axis + `touches-code` floor amendment", a section the fold removed.
- **With a marker and that reason,** the README would not have been asked. Its words would name a section that no longer exists.
- **So a test of claims alone misses a dependant that names structure.** The test below also covers a heading removed, renamed or moved.

## Forces

- **The maintainer's reason to design it now:** a wording edit to a shipped record lands on every adopter anchored to it, and changing friction's rules is cheapest before adopters rely on them.
- **Nothing may be hidden:** an edit nobody classed must still ask its dependants (the versioning note, alternative D).
- **A person decides each answer** (core rule 20). A reason that spares many dependants is the strongest answer there is.
- **The two checks agree:** what a change leaves unanswered is what the whole-repository check reports once it merges (COR-050, "Why the pull-request rule is local").
- **A receiving project holds only its own history.** Upstream edits reach it at version transitions, many at once (#1429).
- **Part anchors:** a dependant may stand on one point or section (#1387).
- **No numbers on documents:** the maintainer decided no semantic versions for documents (#1383, question 1, software-analysis DEC-001 point 6).
- **Cost per edit:** every edit to a marked document asks its author one choice.

## What practice does

Practice lets the author class a change, treats doubt as substantive, trusts the class across projects, and corrects forward.

- **W3C's Process Document** ([§6.2.3, Classes of Changes](https://www.w3.org/policies/process/20250818/#correction-classes)) sorts every change to a specification into five classes. The first two, "No changes to text content" and "Changes that do not functionally affect interpretation of the document", are editorial.
  - **Doubt:** "If there is any doubt or disagreement as to whether a change functionally affects interpretation, that change does not fall into this class."
  - **The consequence:** "Editorial changes to a Recommendation require no technical review of the intended changes" (§6.3.10.1).
- **The RFC Editor's errata** ([errata types and statuses](https://www.rfc-editor.org/errata-definitions/)) never change a published RFC. Each erratum is published beside it, typed Technical or Editorial, with a status: Reported, Verified, Rejected or Held for Document Update.
  - **Editorial:** "a spelling, grammar, punctuation, syntax, or formatting error that does not affect the technical content of the RFC."
  - **Who classes it:** the stream's authority. For the IETF stream the Area Directors are responsible, and errata "should not be used to change what the community meant when it approved the RFC" ([IESG statement of 7 May 2021](https://datatracker.ietf.org/doc/statement-iesg-iesg-processing-of-rfc-errata-for-the-ietf-stream-20210507/)).
- **Semantic Versioning's patch** ([semver.org](https://semver.org/), item 6) is declared by the author: "Patch version Z (x.y.Z | x > 0) MUST be incremented if only backward compatible bug fixes are introduced."
  - **Consumers take it unreviewed:** npm's caret range "Allows changes that do not modify the left-most non-zero element" ([node-semver, caret ranges](https://github.com/npm/node-semver#caret-ranges-123-025-004)), and npm writes caret ranges by default.
  - **A wrong class is corrected forward:** "the contents of that version MUST NOT be modified" (item 3). The FAQ says to release a new version that restores compatibility and document the offending version.
- **What follows for pkit:**
  - **The author classes the edit,** in all three. Nobody checks a class mechanically.
  - **Doubt makes the edit a meaning change,** as for W3C.
  - **The class is trusted across projects,** as a caret range trusts a patch, and as COR-051 point 7 already trusts a rule set's author.
  - **The reader sees each class beside the document, with where it came from,** as an erratum is published beside its RFC.
  - **A wrong class is fixed by a later change,** never by rewriting what shipped.

## The design

### The marker and the reason

A **marked document** is a document others anchor whose friction block holds a `meaning` block. It carries a marker, and after an edit that kept its meaning, a reason.

```yaml
pkit:
  friction:
    meaning:
      at: 2026-10-14T09:00:00Z
      kept-because: Writes the points as headings, word for word. No claim, term or heading a reader can name changes.
```

- **The marker, `at`:** a UTC timestamp, read parsed, as `revalidated.at` is. Its **meaning point** is the commit where the document first carried that value. A value written back keeps its old point (COR-050 point 3).
- **The reason, `kept-because`:** a sentence, read with its whitespace folded. Its **reason point** is the commit where the document first carried that text.
- **A declaration** is what each edit to a marked document writes:
  - **meaning changed:** the edit moves the marker to a new value, and removes the reason
  - **meaning kept:** the edit writes a new reason, and leaves the marker
- **An undeclared edit** changes the document's content and writes neither. It is a meaning change for every reading below.
- **Why both a marker and reasons:** within one project, an undeclared edit shows in the history. A receiving project holds only the states its transitions brought. Without a marker, an undeclared upstream edit followed by a reason would be invisible there. The marker carries a meaning change across projects ("Across projects").
- **Why a timestamp:** it is `at`'s shape, readable, and new on every move. A commit id cannot name the commit it lands in, and a stored hash was rejected (COR-050, "Why a timestamp whose point comes from git").
- **Adding the block** is no edit to the content, since the container is not content. It asks no dependant ("What a dependant reads").
- **Removing the block** makes the document unmarked. Its dependants read it as today from then on.

### The test of a kept meaning

An edit keeps the meaning when, in every part it changes, it:

- adds, drops, weakens or narrows no claim
- changes no term, and splits no claim into parts that disagree
- chooses no reading of a text that had two
- removes, renames or moves no heading a reader or an anchor can name, and moves no text from one part to another
- changes no field that says whether or how the document binds: its `status`, what supersedes it, or what it supersedes

Doubt moves the marker.

- **The source:** project-kit's RS-WRITE-013 lists the first three. A core record states the test in its own words, since a core record suits any project (COR-014). WRITE binds project-kit's analysis and software-analysis's templates and structures, and no record (`.pkit/rules/project.md` rule 3).
- **"In every part":** a part is what an anchor can name, a record's point, a page's section or lead, or a collection entry (#1387). A claim moved from point 3 to point 7 is dropped from one and added to the other. A dependant of point 3 must be asked, so that it can re-point.
- **Headings:** `c2b98094` shows why ("Today"). A fold that removes an amendment heading moves the marker. Converting points to headings adds headings and removes none, so #1421's conversion keeps the meaning.
- **Status:** accepting, superseding or withdrawing a record or a rule changes what binds. The change check refuses a reason beside such a change ("The checks").

### Who decides

A person decides each reason, as each answer.

- **A reason is an answer.** The change check asks a marked document's edit for a declaration ("The checks"). So a reason is one of the answers the change check asks of a change, and core rule 20's exception applies.
  - **An agent may write it first,** in the change it is making.
  - **The person who authorises the merge** is shown it word for word on the change check's list, with the dependants it spares in this repository, before authorising.
- **A moved marker needs no showing.** It spares nobody, as a major spared nobody under alternative B of the versioning note.
- **The writer:** a command of its own, named here `pkit friction meaning <document> (--changed | --kept-because <reason>)`. It writes one block and names what it writes (COR-050 point 13). With `--changed` it writes a new `at` and removes the reason. It refuses a reason equal to the current one.
- **Text a person decided is never reworded for style** (RS-WRITE-013). So no edit rewords a recorded reason, and a later edit replaces it whole.

### What a dependant reads

A dependant is asked about an edit to a marked document only where the text it stood on is no longer one the document vouches for.

- **The text an anchor stands on:** the document's content without its container, or the part the anchor names with what that part stands on (#1387, "What a point stands on").
- **An anchor's last meaning change:** the newer of the document's meaning point and the last undeclared edit that changed what the anchor stands on.
- **Vouched text:** what the anchor stood on at its last meaning change, and at each reason point since.
- **The rule:** an anchor on a marked document has changed between an earlier and a later state when what it stands on differs between them, and the earlier text is not vouched for at the later state.
- **The later state's own text is always vouched for.** The last change to it was a reason, a meaning change or none since the meaning point.
- **A part missing at either state** is never vouched for across. An anchor on a retired point, or on a part not there yet, reads as #1387 says.

**The cases,** for a dependant of point 11 of a marked COR-050:

| What happened since the dependant revalidated | Asked? |
|---|---|
| A reason reworded point 11 | no |
| Two reasons reworded point 11, a week apart | no |
| The marker moved for a change to point 5, and point 11 is untouched | no: point 11's text at the meaning point is the text it stood on |
| One change moved the marker for point 5 and reworded point 11 | yes |
| An undeclared edit touched point 5 only | no: point 11 is untouched |
| An undeclared edit touched point 11, and a later reason touched it again | yes: the undeclared edit is point 11's last meaning change |
| The marker block was added, with no content change | no |
| The marker moved with no content change, as a correction | yes, unless it revalidated after the edit the correction is about |

- **The change check needs no history for it.** In a diff that writes a new reason and leaves the marker, the base's text is vouched for at the base, and the head vouches for everything the base did. So the dependants are not asked. A diff that moves the marker, or declares nothing, asks them as today.
- **The whole-repository check walks the document's file back to each anchor's last meaning change.** It reads what the anchor stood on at the meaning point and at each reason point since, as the part walk of #1419 reads a part at each version.
- **The two checks agree:** what a change spares is vouched for once it merges, and what it asks stays unvouched until revalidated.
- **Debt** of an anchor on a marked document originates at its last meaning change after the revalidation point (COR-050 point 9).
- **The cascade** goes on from a marked artefact only where its content changed under no reason. An artefact that revalidates `updated` and declares its own edit kept asks its own dependants nothing.
- **Over a history with merges,** reason points and meaning points follow COR-050 point 3's rule for values first carried on lines that do not descend from one another. Two lines that each write a reason conflict on the `kept-because` line, and the person resolving it writes one reason for the combined state.

### One marker per document, read per part

The marker belongs to whatever carries the methodology's container: a document, or a collection entry. A part of a document has no container of its own, so it reads its document's marker through what it stands on.

- **A record's point** reads the record's marker. An edit that kept the meaning spares the point's dependants, and a meaning change asks only those whose point changed.
- **A page's section** reads the page's marker.
- **A rule** is a collection entry, so it carries its own marker, in its entry's block. So does any entry, such as a use case.
- **What one marker costs:** a change that changes the meaning of one point and rewords another asks the reworded point's dependants too. Splitting the change in two spares them.
- **Why not a marker per part:** it would put a block per point into the record's front matter, a list that repeats every heading, which #1387 rejected. A retired point would have to carry one too.

### Where it lives

- **An artefact in a place:** in its friction block, beside its anchors and its revalidation.
- **A decision record:** in the methodology's container in its front matter, which records gain for this, with a friction block that holds `meaning` alone.

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
- **Which documents carry it:** only those whose owner adds the block. A document without one reads as today. Which of project-kit's documents carry one is question 2.
- **The decisions README's ban on revision markers:** the block is data a tool reads in the front matter, replaced on each edit, never added to. It holds no narration of a discarded belief. The README's step 2 still names "a block stamped with a date", so its sentence changes ("Settled positions").
- **A supersession** changes `status`, so it moves the marker. A superseded record then keeps its block as it stood.

### Across projects

A received document is read by the same rule, over the receiving project's own history.

- **Where it changes there:** only at version transitions, which bring the target release's methodology files (#1429). Each transition is one change of many upstream edits.
- **What each transition reads as:**
  - **a new reason under the same marker:** an edit that kept the meaning. It spares what the reason covers.
  - **a moved marker:** a meaning change. It asks every dependant whose text changed.
  - **new content under the old reason:** an undeclared edit. It asks, as today.
- **What a received reason claims:** that the document still means what it meant at its meaning point. So it covers every upstream edit since the receiving project's last transition, not only the edit it was written for.
- **The shipping duty that makes that true:** a project that ships a marked document moves its marker past every undeclared edit before it ships. Its change check fails an undeclared edit in enforcing mode, and its whole-repository check reports one that landed anyway, until the marker moves.
- **project-kit's release** refuses to release while a shipped marked document has an undeclared edit since its meaning point (slice M7).

#### How a receiving project sees a reason

- **On the change check's list,** for the change that brings it: the document, the reason word for word, the component and version it came from, and the project's artefacts it spares.
- **In `pkit friction explain`,** for each anchor a reason spared.
- **In the document's front matter,** where it arrived.

#### Whose decision it is there

A received reason becomes the receiving project's decision the way an agent's answer does (COR-050 point 3).

- **The person who authorises the merge** of the change that brings it is shown it on the change check's list, word for word, with the artefacts it spares. Where the change is committed straight to the default branch, the person the agent works for is shown it before the commit.
- **The authorisation covers the reasons shown,** and nothing written after.
- **So no decision moves silently across projects.** The upstream person decided the reason within the upstream merge, and the receiving person accepts it within theirs. This is question 1.

#### What it does about a wrong one

- **Before authorising the transition:** it revalidates each artefact the reason spared, in the same change. A revalidation that nothing asked for is always allowed, and is reported as such (`friction_check._judge`, "revalidated with no changed anchor").
- **After the merge:** the same, once noticed. It reports the reason upstream (`pkit report bug`).
- **Upstream corrects forward:** it moves the marker without changing the content. Every dependant that stood on text from before the wrongly reasoned edit is then asked, in every project, at its next transition. One that revalidated after that edit is not.
- **Upstream never rewrites a reason it shipped** to fix it, as a released version is never modified (Semantic Versioning, item 3).
- **Not offered now:** a setting that turns received reasons off (question 1's alternative), and an anchor that rests on the words (Found on the way 4).

### The checks

What a script checks that an edit wrote, and what it never checks.

- **Validation,** from the working tree (COR-055 point 2):
  - **the block's shape:** `at` a UTC timestamp, `kept-because` non-empty text, no other key, and no `kept-because` without `at`
  - **on a record outside a declared place:** a container that holds anything but `friction.meaning` is reported as inert, as COR-053 point 10 says of a container elsewhere
  - **in a held document:** a `meaning` block is an error, as any friction block is (COR-050 point 12)
- **The change check,** for each marked document whose content the diff changed:
  - **meaning changed:** the parsed marker is new, never one the document carried before, read from the file's history behind the base as for a written-back `at` (`friction_check._Behind.written_back`)
  - **meaning kept:** the folded reason is new in the same way, and the marker held
  - **neither:** a finding, *an undeclared edit*, owned by the change. It fails in enforcing mode, and the dependants are asked as today
  - **a reason beside a change of status or supersession:** a finding owned by the change, and the dependants are asked
  - **a reason left beside a moved marker:** reported, since it describes an edit before the meaning change
  - **the list** gains each reason the change wrote, and each reason it brought from another project, with the artefacts each spares
- **The whole-repository check:**
  - each anchor on a marked document read by the rule above, per part
  - **a marked document with an undeclared edit since its meaning point,** reported where it is authored, whatever depends on it. It is never reported on a synced copy, which the receiving project cannot edit
- **Never checked:** that an edit kept the meaning. That is the person's judgment, as `unchanged-because` is.

### The records it touches

- **A new core record,** "A document others anchor marks an edit that keeps its meaning" (title provisional), recommended in question 5:
  - the marker, the reason, the declaration on every edit and the test
  - who decides, and that a reason is an answer
  - the reading by vouched text, per part, and the cascade
  - the container on decision records
  - the received reason, its showing, the shipping duty and the correction
- **Refined in place, with a pointer to it:** COR-050 (terms, points 3, 5, 6, 9, 12 and 13), COR-053 point 10, COR-051 point 2, core rule 20, the decisions README, and software-analysis DEC-001 point 6 ("Settled positions this reopens").
- **ADR-057 point 2:** the architect places the readings. The meaning block is likely read in artefact discovery, and a record's container in the home of a record's points (#1412).
- **Untouched:** COR-025's ADR schema, which takes the README's schema by reference. At most its illustrative block gains the container line, as #1387 judged for `retired-points`. COR-050 point 14, unless question 1's alternative is taken. COR-051 point 7, COR-010 and PRJ-002.
- **No migration is due (COR-010):** the block is optional and added. A document without one reads as today, and a receiving project's dependants are asked at most once more by a transition that brings the first marker with other edits.

## Alternatives weighed

- **For what a reason covers:**
  - **One edit, from the base it was written against.** Simple within one project. A receiving project sees several upstream edits at once and only the latest reason, so it could never be spared. Not taken.
  - **Since the document's last meaning change,** chained through earlier reasons. Taken. It reads the same in both projects.
- **For an undeclared edit:**
  - **Covered by the next reason.** It would hide an edit nobody classed, and a receiving project could not tell. Rejected.
  - **A meaning change for the parts it changed.** Taken.
- **For the reason's form:**
  - **A list of every reason since the marker last moved,** so a receiving project sees each one. It is a change log in the front matter, which the decisions README forbids, and two lines of work would both append to it. Not taken.
  - **A timestamp for each reason beside its text.** It adds a field for a case the text already covers: a reason written back keeps its old point. Not taken.
- **For the marker:**
  - **Reasons with no marker.** A receiving project could not see a meaning change hidden behind a later reason. Rejected.
  - **A number, moved by one on each meaning change.** Two lines of work that each change the meaning write the same number for two texts, as PRJ-002 found for components. Rejected.
- **For who may class an edit:**
  - **The dependant, by revalidating:** what friction does today. Every dependant pays for every edit. Not taken.
  - **A reviewer other than the author,** as an Area Director verifies errata. The merge's authoriser already sees each reason. A second role is not proposed.
- **For path anchors:** a path anchor that matches a marked document's file still compares the file. A marker is read only through record and artefact anchors, which name a document.

## Questions for the maintainer

One decision each, in order of consequence.

### 1. Does a reason written upstream spare a receiving project's artefacts?

- **The question:** project-kit writes a reason on a shipped record. Is an adopter's artefact anchored to that record then not asked, or only where the adopter opted in?
- **Example:** an adopter's use case `UC-012` anchors `COR-050`. project-kit's next release rewords COR-050 point 11 and gives the reason "Rewords point 11's second sentence. No claim, term or heading changes." The adopter runs `pkit upgrade`. The change check on its pull request lists "received: COR-050 — Rewords point 11's second sentence … (backbone 2.1.0). Spares: UC-012."
- **Recommended:** yes, by default. The reason is shown on the change's list, and the authorisation of the merge accepts it, as for an agent's answer (COR-050 point 3).
  - **Doubt** is answered by revalidating what the reason spared, in the same change.
  - **A wrong reason** is corrected upstream by moving the marker.
  - **Its cost:** an upstream author's reason clears friction on artefacts that author never saw. The receiving person sees each reason, but can accept a list unread, as with any list. COR-050 point 3 and core rule 20 change.
- **Alternative:** a received reason spares nothing unless the project's friction settings name the component whose reasons it trusts, as a shipped rule set binds only through a set of the project's own (COR-051 point 7).
  - **Its cost:** a key in COR-050 point 14. A project that never sets it gets no benefit, so the cost #1451 exists to remove stays with most adopters.

### 2. Which of project-kit's documents carry a marker before the first adopter?

- **The question:** a marked document asks its author one choice on every edit. Which documents take that cost?
- **Example:** a maintainer fixes a typo in COR-017. If COR-017 is marked, the pull request fails the change check until the edit gives a reason or moves the marker.
- **Recommended:** every record project-kit ships, 54 core and 66 capability records, and the rules of `LDOC`. Adopters' anchors are unknown, so every shipped record may be anchored.
  - **Its cost:** one choice on each edit of 120 records. 53 commits on main touched one since 27 September.
- **Alternative:** only the 57 shipped records project-kit's own artefacts anchor today, and others as adopters ask.
  - **Its cost:** an adopter that anchors an unmarked record is asked on every edit to it, and marking it later spares only what follows.

### 3. Does the marker belong to the document, or to each part an anchor can name?

- **The question:** one marker per document, read through each part, or one marker per point and section?
- **Example:** one pull request changes what COR-050 point 5 requires and fixes a typo in point 11. A journey anchors `COR-050#11`.
- **Recommended:** one per document. The change moves the marker, so the journey is asked, since its point changed in a change that moved the marker. Split into two pull requests, the typo's reason spares it.
  - **Its cost:** a mixed change asks the dependants of a part whose meaning held.
- **Alternative:** a marker per part, in a map keyed by point id in the record's front matter.
  - **Its cost:** a block per point, the list of every heading #1387 rejected, and a retired point that must carry one too.

### 4. Where does a decision record carry the marker?

- **The question:** in the methodology's container, as an artefact does, or as the record's own fields?
- **Example:** COR-050's front matter gains either `pkit: {friction: {meaning: {at: …}}}` or two top-level fields, `meaning-at` and `meaning-kept-because`.
- **Recommended:** the container. The marker is friction's data, and COR-053 point 10 keeps the methodology's data in the container. A record anchor then reads the record without it, as an artefact anchor reads an artefact.
  - **Its cost:** records gain the container. COR-053 point 10's "a container elsewhere is inert" and COR-050's "for a record, the record's file" change.
- **Alternative:** the record's own fields, outside the container, as `retired-points` is.
  - **Its cost:** friction's data among a record's own fields, against COR-053 point 10's split. An ADR in a place would have two spellings for one fact, and a record anchor must leave out two named fields.

### 5. Is it a record of its own?

- **The question:** a new core record, or a refinement of COR-050 in place?
- **Example:** the rule "a received reason is shown on the change's list" lives either in a new record, with COR-050 point 3 pointing at it, or as a further sentence in COR-050 point 3.
- **Recommended:** a record of its own. It holds a new principle, a document's own declaration about its edits, with its own rationale and alternatives, and the trust across projects. COR-050 is refined in place where the new record reaches it, with a pointer.
  - **Its cost:** one more core record, and pointers in COR-050.
- **Alternative:** refine COR-050 in place.
  - **Its cost:** COR-050, 167 lines and refined for parts by #1419, gains a third concern beside anchors and answers.

## Settled positions this reopens

Each accepted sentence below changes, for the maintainer's authorisation. Each lands through its own reviewed change, after the new record is accepted.

1. **COR-050's terms and point 5, what a record anchor stands on:** "What an anchor **stands on** is, for a path, the files it matches (point 7 says which the excluded paths leave in); for a record, the record's file" and "**A record anchor** has changed when the record's file differs, followed across a rename."
   - **The change:** a record anchor stands on the record's content, its container left out. A record without a container reads as before, except that an edit to its front matter's layout alone is no change.
2. **COR-050 point 5, when an anchor changed:** "**An artefact anchor** has changed when that artefact's **content** changed" and "**Three answers**, judged from the diff [...] clear friction".
   - **The change:** an anchor on a marked document has changed only where the earlier text is no longer vouched for. A new reason is no answer of the dependant's. It keeps the dependant from being asked.
3. **COR-050 point 6, the cascade:** "An artefact anchored to another artefact is included when that artefact's content changed in the pull request. The cascade continues only where a revalidation itself changes content."
   - **The change:** for a marked artefact, only where its content changed under no reason.
4. **COR-050 point 9, debt:** "*stale* debt originates in the oldest commit from which a part of what the anchor stands on [...] has differed, without returning, from what it was at the point it is measured from".
   - **The change:** for an anchor on a marked document, debt originates at its last meaning change after that point.
5. **COR-050 point 3, a person's decision:** "An answer is a person's decision when that person was shown it — the artefact, the outcome, and the justification or the deferral's reason, word for word — and accepted it." and "What they are shown is the change check's list of those answers (point 12)".
   - **The change:** a reason is an answer the change check asks for. A reason a change brings from another project becomes this project's decision when the person who authorises the change is shown it on the same list.
6. **Core rule 20:** "A revalidation, a deferral or a reason for having no anchors (COR-050 points 1 and 3) is written only after a person was shown it and accepted it, with one exception."
   - **The change:** the list gains a reason an edit keeps a document's meaning, and the rule names the reasons a change brings from another project.
7. **COR-050 point 12, what the change check finds:** "friction of the pull request, dead anchors of the pull request, a bump with nothing behind it, [...]" and, reported only, "the answers the change wrote, each with its words (point 3)".
   - **The change:** it also finds an undeclared edit and a reason beside a change of status, owned by the change. The answers reported include the reasons written and received.
8. **COR-050 point 13, the writers:** "Writing is always a separate, explicit command that names what it writes: revalidate, defer, record the status."
   - **The change:** a fourth writer declares a document's meaning.
9. **COR-053 point 10:** "Any artefact may carry the container; validation reaches only the artefacts in declared places (COR-050 point 1), so a container elsewhere is inert."
   - **The change:** a decision record may carry the container, with a friction block holding the meaning block alone, which friction reads and validation checks wherever the record lives. Under question 4's alternative this stays.
10. **COR-051 point 2, "Anchoring":** "Editing a statement, or accepting, superseding or withdrawing a rule, is therefore a change that the rule's dependants see as friction. Nothing keeps silently obeying a rule that has changed."
    - **The change:** an edit of a marked rule's statement under a reason asks its dependants nothing. A change of its status always does.
11. **The decisions README:**
    - **"Schema":** the record's front matter may hold the container with its meaning block.
    - **"Refining an accepted record", step 2:** "Add no revision marker — no amendment heading, no block stamped with a date or an issue number, no note that the record was amended in place rather than superseded." The meaning block is data a tool reads, replaced on each edit, so the step names it as no revision marker.
    - **The same section gains** that an edit to a marked record declares whether it kept the meaning, and that a supersession moves the marker.
12. **software-analysis DEC-001 point 6:** "the capability's artefacts and records carry no declared versions", and its rationale: "A version an author declares on a document would tell a dependant one fact, whether the meaning changed [...] So the capability's artefacts and records carry no declared versions".
    - **The change:** a meaning marker is that one fact, and no version. The capability's artefacts may carry it.

**Not reopened:**

- **COR-050's rejected alternatives:** "A commit identifier or a content hash as the marker" stays rejected, since the marker is a timestamp. "A bare marker change as an answer" stays rejected, since a moved marker answers nothing and spares nobody.
- **COR-051 point 7:** a set's major is unchanged. A rule edited under a reason makes no major due.
- **COR-050 point 14,** under question 1's recommendation.
- **COR-025's ADR schema:** by reference to the README's.

**Decided designs it changes,** not yet accepted records:

- **#1387's first case,** "The part's text changes: its dependants are flagged." A part whose change kept the meaning under a reason flags nobody.
- **#1383's question 2,** "not now", which the maintainer reopened on 11 October.

## Slicing

A draft of the build, for filing after the maintainer decides. Each record is accepted before the work that cites it. The build lands before the first adopter.

- **M1, [Docs] A core record says a document others anchor marks an edit that keeps its meaning:**
  - authored with `pkit new decision core` through the decision-author skill, and reviewed by the critic, the architect and the methodology-reviewer
  - with it, the refinements in place of "Settled positions" 1 to 12, each with a pointer to the new record
  - **after #1419's refinement of COR-050 for points is accepted,** so two refinements of COR-050 do not race
  - a `none` changeset for each component whose records it edits (PRJ-002)
- **M2, [Task] The meaning block, its schema, validation and its writer:**
  - the container schema gains `meaning` in the friction block, and binds records too
  - validation's friction member checks an artefact's block, and its decisions member a record's
  - `pkit friction meaning`, with consent as the other writers
  - the architect names the readings' homes, and refines ADR-057 point 2 first if they change it
  - **Docs:** the schemas README's "The friction block", and the CLI reference. A backbone minor.
- **M3, [Task] The change check reads a marked document's declaration:**
  - a record anchor reads the record without its container
  - the declaration of each edit, the undeclared edit and the reason beside a change of status
  - dependants spared by a new reason, per part, and the cascade
  - the list's written and received reasons, in its human and JSON forms
  - **after M2, #1408 and #1419.** Names #1423: whichever lands second reads page sections. A backbone minor.
- **M4, [Task] The whole-repository check, debt and explain read vouched text:**
  - each anchor's last meaning change and vouched text, per part
  - debt from the last meaning change, and `explain` naming the reason that spared an anchor
  - the document finding, an undeclared edit since the meaning point, never on a synced copy
  - **after M3.** A backbone minor.
- **M5, [Task] The skills and agents that edit a marked document ask for its declaration:** the decision-author skill when it refines a marked record, the analysis-author skill, living-docs' agent, and the agents README's "Friction writers". After M2.
- **M6, [Docs] project-kit marks the documents it ships,** as question 2 decides:
  - the block, with no reason, on each document, through the writer. No dependant is asked, since no content changes
  - CONTRIBUTING.md says that an edit to a marked record declares
  - **after M4, and after #1421,** so the conversion of project-kit's records lands as planned. Marking first would spare the conversion's 28 answers, but would hold the part-anchor build behind this one.
- **M7, [Task] project-kit's release refuses a shipped document with an undeclared edit:** the release check refuses while a shipped marked document has an undeclared edit since its meaning point. After M4.

**Order:** M1, then M2, M3 and M4 in turn, then M5 and M7, then M6, then the first adopter.

**Against the filed builds:**

- **Part anchors, #1403 to #1427:** after #1408, #1419 and #1421, and alongside #1423.
- **Conversions, #1431 to #1444:** independent. #1438's conversion of an adopter's records meets the marker (Found on the way 3).
- **The version transition, #1455 to #1465:** independent. A received reason is read by the change check over whatever brings the document, today's sync or the transition after #1460.
- **Rule-set versions, #1449 and #1450:** #1450's check may read a rule's marker (Found on the way 5).

## Found on the way

1. **An ADR in project-kit is both a record and an artefact.** The 61 ADRs sit inside living-docs' `tech-docs/**` place. An anchor `record: [ADR-049]` reads the file, and `artefact: [ADR-049]` reads its content without the container. Under this design both read the content without the container. Whether one form should be refused is a question of its own.
2. **A receiving project's checks judge upstream rules.** Method rule sets are walked as artefacts there ("Today"). An upstream rule left stale upstream would be reported in every receiving project, which cannot edit it. Whether a receiving project should judge rules it cannot edit is a question of its own.
3. **A conversion that converts word for word could write its reason itself** (#1435, #1438). A reason is a person's decision (core rule 20), but a person reviews the conversion's whole diff. Whether a tool may write a stock reason there is #1438's to settle.
4. **A dependant that rests on the words** wants every edit, such as a page that quotes a record, or a translation. An anchor could say so, and ignore reasons. No such dependant exists in project-kit today, so it waits for one (COR-007).
5. **A rule edited under a reason makes no major due** (COR-051 point 7), since the test forbids tightening. #1450's check could skip such edits. #1449 decides what each part of a set's version means.

## Review

Pending: the critic, then the architect.
