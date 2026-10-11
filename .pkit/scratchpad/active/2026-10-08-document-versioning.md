---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-10-08
---

# Document versions — declared numbers, pointers or a meaning marker

A design for #1383. It asks whether pkit's documents should carry versions their authors declare, while pkit has no adopters to migrate.

- **Raised by:** the template round's revalidation-record question 1 (#1362, PR #1374). A planned record's `reviewed-against` must point at the design it reviewed.
- **Read from main at `30cfb15a`:** the records, the code and the history counts below.
- **Citations:** records and rules by permanent id and point. Code by file and line at `30cfb15a`, since code has no permanent ids.
- **Reviewed:** by the critic and the architect. Their findings and the answers are in "Review", at the end.
- **Decided:** by the maintainer on 8 October. Questions 1 to 3 are answered in PR #1384's comments. Question 4 went to a design of its own, #1387, decided on 9 October. What the pointer check fails on, the stamp's warning, and that a rule set's version is checked were decided on 11 October ("Slicing"). Question 2 was reopened the same day: the meaning marker is designed before adopters, in #1451.
- **Filed:** #1448, #1449, #1450 and #1451 on 11 October, with edits to #1363, #1365 and #1366 ("Slicing").

## The question

Should pkit's documents carry versions their authors declare, and how does a record point at the version of a design it reviewed?

## In short

No semantic versions for documents. Friction's cost comes from what a dependant rests on, not from how an author classes a change. The maintainer decided so, and chose to anchor to parts now ("Decisions"). The meaning marker, first left for later, is designed before adopters (#1451), as the maintainer decided on reopening question 2.

- **Why not semver:** a minor spares no dependant, and a major asks no more than today. pkit's rule sets already make an added rule a major (COR-051 point 7).
- **What semver reduces to:** one fact, whether the meaning changed. Alternative D carries it as a marker that moves only when the meaning changes.
  - **It compares states, as `at` does.** So it holds across many changes: a squash, the stretch since a revalidation, or an adopter's sync.
- **Why D can wait:** of 182 answers that a document's edit caused since 27 September, 4 followed an edit that kept the meaning. None was on a record adopters receive.
  - **It adds, and migrates no data:** a document without a marker keeps today's reading, so D can come later.
- **Where the cost is:** 97 of the 182 came from two dependants anchored to whole documents while resting on a part.
  - **The maintainer chose to anchor to parts now,** through a design of its own (#1387). It reopens settled decisions, which the maintainer authorised.
  - **Its precondition is decided too:** a record's points keep their numbers for good. Records and adopters cite points, and refining in place renumbered them.
  - **The two dependants re-point to the parts they rest on,** in place of the fixes on the dependant's side this note proposed.
- **`reviewed-against` takes pointers under every alternative:**
  - **Text in a repository:** a commit on its default branch, or the change the record lands in. A pull request's head is no pointer, since a rebase loses it.
  - **Text in the tracker:** an absolute link, with the time of the version read.
- **Practice agrees:** it numbers contracts that others pin, and flags links that a person clears. It lets an editorial change skip review only where nobody doubts it is editorial.

## Today

Each mechanism answers one question, and none gives a document a version of its own.

### Friction: does a dependant still hold? (COR-050)

The reader classifies a change after the fact. Each flagged artefact answers `updated`, or `unchanged` with a reason, or defers (COR-050 points 4 and 5).

- **What "changed" means:** a difference between two states, never a content hash or a number (COR-050 point 5, and its rationale on states).
  - **A path anchor:** any file the diff names that the anchor matches, on either side of a rename (`src/project_kit/friction_check.py:493-498` and `:943-952`).
  - **A record anchor:** the record's whole file, where a rename with identical content is no change (`friction_check.py:911-914`, `src/project_kit/friction_git.py:158-160`). A typo fixed in COR-050 flags all eight artefacts anchored to it.
  - **An artefact anchor:** its content. That is its body compared as text and its own fields compared parsed, never the methodology's container (`src/project_kit/friction_discovery.py:1867-1870`, `friction_check.py:915-917`).
- **What it costs:** COR-050 was accepted on 27 September. From then to `30cfb15a`, main wrote 403 `unchanged-because` lines, 353 of them distinct.
- **Who decides an answer:** a person, shown it word for word (COR-050 point 3, and core rule 20). An agent's answers in a change are shown once, on the change check's list, before the merge is authorised.
- **Mode:** project-kit runs the change check in enforcing mode, so friction fails a pull request here (its backbone configuration, the `friction` key).
- **Note:** the marker `at` is a timestamp whose commit git finds. A commit id cannot be written into the commit it names, and the squash drops the id from main (COR-050, rationale on the timestamp).

### Rule-set versions: may an inheriting set keep its pin? (COR-051)

A rule set carries a semantic version because other sets pin its major, as `living-docs:LDOC@1` (COR-051 point 7).

- **Who declares:** the set's author. A major is due when an accepted rule is added, withdrawn, superseded or tightened. It is also due when an offered extension point is removed (COR-051 point 7).
- **An addition is a major here:** a set that inherits must conform to an added rule, so the addition can break it.
- **What a script checks:** that each pin names the inherited set's current major (`src/project_kit/rule_sets.py:1453-1502`).
- **What no script checks:** that the version moved when a rule changed. The rule-set module touches no git (`rule_sets.py:35-39`).
- **Two schemes already sit side by side:** each rule is an artefact too, so a changed rule flags its dependants whatever the version says (COR-051 point 2, "Anchoring").
- **In use:** `TECH` and `USER` pin `living-docs:LDOC@1`. `WRITE` is at 1.0.0, and nothing pins it yet.

### Changesets: what moves in the next release? (PRJ-002)

A pull request declares a component's segment, and the release step writes the numbers on main (PRJ-002 D1 and D3).

- **Who declares:** the change's author, per component, as a judgment of the surface (PRJ-002 D2).
- **What a script checks:** that a surface change carries a changeset, by a path heuristic. The guard checks presence, never truth (release README, "The surface-without-changeset CI guard").
- **Why numbers wait for the release:** branches that each wrote a version cell conflicted at merge (PRJ-002 rationale, PR #360).
- **Cadence:** 22 releases from 4 July to 24 August, then a pause. 326 changesets wait in `.changes/unreleased/` since `v1.149.0`.
- **Note:** a decision's segment measures its effect on adopters, not on its dependants. A design-ahead decision declares `none`, however much its meaning changed (PRJ-002, on decision-touching pull requests).

### Records: refined in place, or superseded (the decisions README)

A record is edited in place for a refinement that does not overturn it, and superseded when it is overturned. Git history is its change log.

- **So a "major" for records exists already:** supersession, with a new id. It is the IETF's split, where a new RFC obsoletes an old one.
- **What is open is how to class an edit in place.** Some keep the meaning, and some refine it. Dependants cannot tell which today.
- **No revision marker in a record:** no amendment heading, no block stamped with a date or an issue, no change-log narration (the decisions README, "Refining an accepted record").

### Captured sources: which version of an outside text did the pages read? (living-docs DEC-001 point 4)

One file per source records the version the pages were last checked against. A change to that file flags the pages.

- The two captured today use the two forms a version can take:
  - `keep-a-changelog.yaml` records the source's own number, `"1.1.0"`.
  - `common-changelog.yaml` records a commit, `bed3ea69…`, since that source publishes no number.

### Dependants that another project owns

An adopter's artefacts will anchor pkit's records: a core record, or a capability's decision (COR-050 point 2). project-kit's own pages already anchor `living-docs:DEC-001` and `software-analysis:DEC-001`.

- **Each sync is one change of many upstream edits.** The adopter's change check compares the copy before the sync with the copy after.
- **The adopter's answerer has the diff, not the author's intent.** Today every upstream edit asks every such artefact, editorial ones included.
- **The adopter holds only the sync commits,** not the upstream's history.
- **This load does not show in project-kit's own history:** one owner writes both the records and their dependants.
- **A component's version is no help here:** it moves with every surface change of its component, and a design-ahead decision moves it by `none`.

### Pointers: where can a text be read again?

A pointer returns a text. How long it lasts depends on what keeps it.

- **A commit on the default branch:** a squash merge puts one commit per pull request there (COR-009 point 1). It stays reachable, and a script can check it where the clone's history reaches it.
- **A branch commit:** gone from main after the squash, and the branch is deleted (COR-009 point 4). PR #1353's head `297cdae8` is not an ancestor of main, and its branch no longer exists.
- **A pull request's head:** `refs/pull/N/head` names the latest head only.
  - **A final head survives:** GitHub still serves `refs/pull/1353/head` at `297cdae8`, after the branch's deletion.
  - **A head reviewed mid-way does not:** a rebase or a force-push leaves it behind, and the squash keeps none of the branch's commits. Branches are kept up to date with their base (COR-050 point 6), which invites rebases.
  - **A plain clone does not fetch `refs/pull/*`:** its fetch rule takes `refs/heads/*` only.
- **A tag:** keeps its commit reachable, and a plain clone fetches it. Releases tag main (PRJ-002 D3), 26 times so far.
- **An issue body or a comment, with the time of the version read:** GitHub keeps each edit with its time. #1346's body lists two, on 5 and 6 October.
  - **Limits:** only the hosting service answers, over the network. An edit's history can be deleted, and a move to another service loses it.

## What "a version of a document" could mean

Three things go by the name, and each answers a different question.

- **A number the author declares:** says how much changed between two versions. It cannot return the text.
- **A pointer:** returns the text. It says nothing of how much changed.
- **A baseline:** a named set of pointers taken at one moment, such as a release tag. It returns many texts under one name.
- **Note:** a number can lead to a pointer. Git finds the commit that first carried it, as COR-050 point 3 finds the commit behind `at`. That holds only once the number reaches main, and only while one number names one text.

## What practice does

Practice numbers the documents others implement against, and flags a link when anything under it changes. It lets an editorial change skip review, and only where nobody doubts that it is editorial.

- **Semantic Versioning** (semver.org): major, minor and patch are defined against a public API the software must declare. The specification is written for software, and leaves the bump to the author.
  - **A minor is safe for callers, not for implementers.** Code that calls an API ignores an addition. A dependant that must describe or conform to the document cannot ignore it.
  - **Documents with numbers of their own are contracts.** The AWS Encryption SDK specification gives each document a semantic version and a changelog of its own (its `VERSIONING.md`). OpenAPI's `info.version` is a string the API document's author declares.
  - **An adaptation to prose exists, with no adoption seen.** SemVerNL ties a major to the meaning of an abstract. It ties a patch to no significant effect on meaning (`ptsteadman/semver-for-natural-language` on GitHub).
- **Versioned documentation sites** version a whole set, never one page.
  - **Docusaurus** copies the docs folder into a versioned folder when someone cuts a version. It advises versioning only when needed (docusaurus.io, "Versioning").
  - **Read the Docs** builds a version from each git tag or branch. `latest` follows the default branch, and `stable` follows the highest release (Read the Docs, "Versions").
- **Requirements tools** mark a link suspect on any change, and a person clears it. That is friction's shape.
  - **DOORS Next:** "If you change the contents of either artifact, the status of the link becomes suspect." A team member then sets it valid or invalid (IBM documentation, "Link validity").
  - **The status sits on the link, with no version number.** Each requirement's revisions are kept, and a baseline freezes a configuration at a milestone (IBM documentation and jazz.net).
  - **DOORS Classic narrows what counts as a change by attribute.** Only attributes set to affect change dates make a link suspect (a jazz.net forum archive of 2012, quoting the DOORS help).
  - **ReqIF** gives each element a `LAST-CHANGE` timestamp and no version number (the ReqIF 1.0 schema). COR-050's `at` is the same kind of marker.
- **Standards bodies** class each change, and the editorial class needs no review.
  - **W3C names five classes.** "The first two classes of change are considered editorial changes": no change to text content, and changes that do not functionally affect interpretation.
  - **Doubt makes a change substantive:** "If there is any doubt or disagreement as to whether a change functionally affects interpretation", the change is not in the editorial class.
  - **W3C's consequence:** "Editorial changes to a Recommendation require no technical review of the intended changes." Publishing one still takes a Working Group decision with no votes against (W3C Process Document of 18 August 2025).
  - **W3C also points by address:** each specification has a dated "This version" address beside a "Latest version" one, as WCAG 2.2 has.
  - **The IETF never changes what an RFC means.** A correction comes as a new RFC that obsoletes or updates the old one (RFC 2026 and RFC 7322). RFC 9720 allows a reissue only where the semantic content is preserved.
  - **ISO** reviews each standard every five years, and confirms, amends, revises or withdraws it (ISO/TC 211's good practice on systematic review).
- **Document control:** ISO 9001:2015 asks for control of changes, with version control only as an example (clause 7.5.3.2, read through a secondary source).
- **GitHub:** `refs/pull/` is read-only. A commit removed from the branches "may still be accessible" through a pull request that references it (GitHub Docs, "Removing sensitive data from a repository"). That describes a side effect, not a promise.
- **What follows for pkit:**
  - **Numbers go to contracts that others pin.** pkit already numbers its rule sets (COR-051) and its components (PRJ-002).
  - **A dependant of a change gets a flag that a person clears.** pkit's friction is that mechanism (COR-050).
  - **An editorial class spares review only without doubt.** W3C's line is alternative D's line below, doubt included.
  - **Sets get versions at releases and milestones.** That is alternative C, which pkit's release tags already give.
  - **Pointers are dated addresses.** W3C's dated address and an RFC that never changes are alternative A's pointers.
- **Not verified:**
  - what ISO/IEC/IEEE 29148 and ISO/IEC/IEEE 15289 say on baselines, traceability and revision history, since both are paywalled
  - any source that gives the bump to a role other than the author
  - a GitHub statement that `refs/pull/N/head` outlives the branch. PR #1353 shows it does for a final head (Today, "Pointers").

## What history shows

A version can spare only the answers a document's edit causes, and those are half of today's. Few of them followed an edit that kept the meaning.

- **The sample:** every `unchanged` answer main wrote from 27 September to `30cfb15a`.
  - **Covered:** 367 of the 403 answers. The change check could not be rerun on 11 of the commits.
- **The method:** for each commit, the change check was rerun against its parent, and listed the answers the commit wrote (`pkit friction check --base C~1 --head C --json`).
  - **The anchors:** each answer's artefact was read at that commit (`pkit friction artefacts --at C --json`). Its anchors were matched against the files the commit changed.
  - **A limit:** an anchor on a collection entry is matched by its whole file. So 21 answers are counted as a document's that may not be, and code changed for all 21.
- **What caused the 367 answers:**
  - **code alone:** 182
  - **a document alone:** 144
  - **both:** 38
  - **neither, such as a moved artefact:** 3
- **Of the 182 that a document caused, 4 followed an edit that kept the meaning.** These were ADRs losing their dated trailers (#860).
  - **ADRs stay in project-kit.** So every edit to a record that adopters receive, among those behind an answer, changed the meaning.
  - **Every other record edit behind them changed the meaning.** Each added a paragraph, corrected a claim or restated a limit, judged one by one from its word diff.
  - **The READMEs' edits were not all judged one by one.** Those read added commands, names or steps.
- **97 of the 182 came from two dependants of whole documents:**
  - **62 from the area index, `.pkit/README.md`:** it anchors ten area READMEs whole, so each edit of one asked it. None of those edits touched what the index says.
  - **35 from the seven rules anchored to living-docs DEC-001:** five edits each asked all seven rules. Each answer found the edit irrelevant to its rule.
- **So the lever is what a dependant rests on.** A meaning marker would have spared 4 answers. Anchors on the part a dependant rests on could have spared up to 90.
  - **Why 90, not 97:** one of the five edits to living-docs DEC-001 was to point 3, which all seven rules rest on. It would have asked them anyway.
- **Adopters would meet the same mix of edits:** their artefacts anchor the same records. A sync of several edits moves a marker if any one of them changed the meaning.
- **Note:** the window is eleven days in one repository, while records mostly grew. The method can be rerun on a later window.

## The alternatives

Each is weighed by what it gains, what it costs on every edit, and what a script can check.

### A — No document versions, pointers only

Friction stays as it is. A record names what it reviewed by pointers.

- **Gains:**
  - Nothing new on any edit, and nothing new in COR-050.
  - A pointer returns the exact text reviewed, which no number does.
- **Costs:**
  - Every edit of a depended-on document still asks every dependant, editorial ones included. That holds for every adopter's sync too.
  - A reader learns how far a design moved since a review by reading the diff.
- **What a script checks:**
  - **A commit on the default branch:** that it is an ancestor of the branch, where the clone's history reaches it. The branch resolves as COR-054 point 2 says.
  - **A tag:** that it exists and names a commit on the default branch.
  - **Text in the tracker:** its form only. Whether the tracker holds it needs the network.
- **Per edit:** nothing.

### B — Author-declared semantic versions per document

Each depended-on document carries `version: X.Y.Z`. Each change moves it, and friction reads the move.

- **What friction would read:** only whether the meaning changed. Minor and major ask the same.
  - **A minor cannot spare the dependants.** An addition may contradict what a dependant says is absent, and COR-051 point 7 already makes an added rule a major.
  - **A softer minor adds nothing.** One that asks a dependant only to read the addition asks what the diff already shows. One cleared by a bare acknowledgement is the bare marker change COR-050 rejects (COR-050, alternatives).
  - **A major could ask more than today:** forbid an agent's `unchanged` before a person accepts it, say, or carry the cascade on. Nothing in this note's history asks for that.
- **What would change:**
  - **COR-050 points 5 and 6:** a record or artefact anchor changes where its target's major or minor moved. A move of the patch alone is no change, and neither is a move of no part.
  - **Undeclared changes:** a content change that moves no part flags in both checks. The whole-repository check compares the content too, not only the number.
  - **The change check:** fails a change to a versioned document that does not move its version, or moves it back.
  - **Schemas:** a decision record has no version field. Each record, page and artefact that others anchor would gain one.
  - **Changesets:** unchanged. A document's segment and a component's segment answer different questions.
- **Where the number is written:**
  - **On the branch:** two lines of work that edit different parts of one record both write its version line. They conflict, as PRJ-002 found for components (PR #360), or both write `1.2.4` for two texts.
  - **At the release:** the release cadence was days apart until August, then paused. A number lags its text by the time to the next release.
  - **After the merge, by a job on main:** no conflict and no lag, in the way COR-050 point 10's status job writes. The job needs a declaration on each change to compute from, which is D's marker.
- **Which documents:** only those others anchor through a record or artefact anchor. 217 of today's 391 anchor values point at a record or an artefact, across 114 distinct targets.
- **Gains:**
  - An edit that keeps the meaning stops flagging dependants.
  - A reader sees at a glance how far a document moved since a version they read.
- **Costs:**
  - A three-way judgment on every edit of a depended-on document, where friction reads one bit.
  - The author judges for readers they may not know. A wrong patch silently clears friction for all of them.
  - The number still needs a pointer to return the text.
- **What a script checks:** that a changed document moved its version, forward, by one step. Never that a patch kept the meaning.
- **Per edit:** one judgment of the segment, and one line, on every change to a depended-on document.
- **Note:** a number for readers can still be had later. A job on main can count D's marker moves, if readers ask for a number.

### C — Baselines: a tag for a set of documents at a moment

Someone tags a commit, for a set of documents or for one review, and a record points at the tag.

- **What exists:** every release tags main, so `v1.149.0` is already a baseline of every document (PRJ-002 D3).
- **Gains:**
  - One name covers many documents.
  - A tag keeps its commit reachable, and a plain clone fetches it. A script checks it offline.
  - **A tag per review keeps a branch commit for sure.** It is the one pointer that keeps a design reviewed mid-way through a pull request.
- **Costs:**
  - Who cuts a tag, and when, is a new duty.
  - A tag per planned record adds a tag that every clone fetches.
  - A review that reads tracker text needs A's tracker pointer anyway.
  - Friction gains nothing, since a baseline says nothing of how much changed.
- **Per edit:** nothing. Per tag: one tag, and the decision to cut it.

### D — A meaning marker on a depended-on document

A document others anchor may carry a marker that moves only when its meaning changes. Every other edit to it says why the meaning holds.

- **Its shape follows `at`'s (COR-050 point 3):**
  - **The marker:** a timestamp in the document's friction block, whose point is the commit that first carried it.
  - **The reason:** for an edit that keeps the meaning, a sentence that changes in the same diff, as `unchanged-because` must.
  - **An edit to a marked document writes one of the two.** One that writes neither is a finding of the change check, and its dependants are asked as today.
- **What a dependant reads:** its anchor on a marked document changed when the marker's point is not reached by its revalidation point. An edit with a reason asks it nothing.
- **It compares states, so it holds across many changes:** one comparison covers a squash, the stretch since a revalidation, or an adopter's sync.
- **An edit with no reason is never hidden.** The whole-repository check walks the document's reason points after the dependant's revalidation point. A reason moves the dependant on only where the content before it is the content the dependant last stood on.
- **The test of a kept meaning:** RS-WRITE-013's list in full. The edit adds, drops, weakens or narrows no claim, swaps no term, splits nothing into parts that disagree, and chooses no reading.
  - **Choosing a reading cannot be judged without the readers:** an edit that settles an ambiguity moves the marker.
  - **Doubt moves the marker,** as doubt makes a change substantive for W3C.
- **Who decides:** a person. A reason answers for every dependant, so it is shown word for word on the change check's list (COR-050 point 3, core rule 20).
- **Where it lives:**
  - **An artefact in a place:** in its friction block, inside the container. The container is not content (COR-050 point 5), so writing the marker changes nothing a dependant reads.
  - **A decision record:** records carry no container today, so they would gain one. A record anchor would then compare the record without it.
  - **The decisions README's ban on revision markers:** the marker is front-matter data that a tool reads, not narration in the body. It records no discarded belief, and git cannot tell a meaning change from a rewording.
- **Which documents:** a document carries a marker only when its owner adds one. One without behaves as today. Records synced to adopters would gain the most.
- **For an adopter:** a synced record brings its marker. An adopter's artefact is asked only when the marker moved since its revalidation.
  - **It runs on trust.** The adopter holds only the sync commits, so it cannot walk the reasons. It trusts that the source held every edit to the rule.
  - **It moves a decision across projects.** An upstream author's reason clears an adopter's friction, while a person's decision is defined within one project's merge (COR-050 point 3).
  - **A first marker costs one round:** a dependant revalidated before the marker existed is asked once more, unless the design says otherwise.
- **Gains:**
  - An edit that keeps the meaning stops asking dependants, here and in every adopter.
  - A reader, and a `reviewed-against`, see when a document's meaning last changed.
  - One fact that holds across changes, with no segment and no number to conflict over.
- **Costs:**
  - One choice on each edit of a marked document, much as a changeset is.
  - A wrong reason clears friction for every dependant, adopters' included, and no dependant can contest it. The diff stays readable, and the reason sits on the list the merge authoriser reads.
  - COR-050 needs a refinement: the marker, the reason, the record anchor's new reading, the list and the walk.
  - Decision records gain the methodology's container.
  - **A new kind of document:** a container outside a declared place is inert today (COR-053 point 10). A record would be no artefact, yet carry a block that is read and checked.
  - **It would have spared 4 of the 182 answers a document caused, and none on a record adopters receive** (What history shows).
- **What a script checks:** that each edit of a marked document moves the marker or gives a new reason, and that the marker moves forward. Never that the meaning was kept.
- **Per edit:** one choice on each edit of a marked document. Nothing on any other.
- **A reason with no marker was weighed and dropped:** a state shows only its latest reason. So it cannot say what lies between two states, which is what both checks compare.
- **When it is reopened:** it touches COR-050 points 3, 5 and 14, COR-053 point 10, the decisions README and COR-025's ADR schema. That is likely a record of its own, not a refinement.
- **A trigger that can be measured now:** classify the edits to synced records between consecutive release tags, as if an adopter anchored every record. A sync that holds only edits that keep the meaning is what D would spare.

### E — Finer anchors: rest on the part, not the whole document

A dependant anchors to the part of a document it rests on, so an edit to another part asks it nothing.

- **What history shows:** 97 of the 182 answers a document caused came from dependants that anchor a whole document and rest on a part of it.
  - **The area index** rests on what each area README is for. It was asked about 62 edits that left that alone.
  - **The seven rules anchored to living-docs DEC-001,** six in `LDOC` and one in `USER`, rest on its point 3. They were asked 35 times, 7 of them about an edit to point 3.
- **What it would reopen:**
  - **What an anchor rests on:** whole files (COR-050 points 2 and 5). A resolver answers with files, and a capability gets precision by keeping one value in one file (ADR-057, "Why a resolver answers files").
  - **Precision kept at a file:** living-docs rejected counting only some fields of a source's file, since it "would grow the backbone for one consumer" (living-docs DEC-001, alternatives).
  - **Two alternatives COR-050 rejected:** anchors per section parsed out of prose, and anchors on every statement. COR-051 rejects markers in prose parsed by pattern, as fragile.
  - **Stable point numbers:** refining in place puts a new point where it belongs among the others (the decisions README, "Refining an accepted record"). That renumbers every later point, in every project's records.
- **Why stability is a precondition:** both checks and the debt listing must find the part at any commit. If a renumbering moves an anchor onto another point, the two checks can disagree.
- **What does not carry over from COR-050's rejection:** "a second convention". A record's points are already how records are cited, as "COR-050 point 5".
- **Fixes on the dependants' side, with what exists:**
  - **DEC-001 point 3 restates the seven rules.** The record could cite the rules instead. The rules would then rest on no text of the record, and need not anchor it whole.
  - **The area index restates each README's role.** The table could be generated from each README's role, checked by a validator, so the index need not anchor the READMEs whole.
- **The ways in through existing machinery reach neither case:** the living-docs dependants are rules already, and the area READMEs are no entries of one file.
- **Placement:** only the backbone can do it, so it is core. It touches COR-050, ADR-057, living-docs DEC-001 and the decisions README.
- **Note:** this is a question of anchoring, not of versions. It is listed because the history points at it.

### Side by side

| | A pointers | B semantic versions | C baselines | D meaning marker | E finer anchors |
|---|---|---|---|---|---|
| Spares the dependants of | nothing | a patch | nothing | an edit with a reason | an edit to another part |
| Answers spared in the sample, of 182 | 0 | at most 4 | 0 | 4 | up to 90 |
| Holds across many changes | not applicable | yes | not applicable | yes | yes |
| Cost on each edit | none | a segment, always | none | a marker or a reason, on marked documents | none |
| What `reviewed-against` adds to pointers | nothing | a version per document | a tag per review | the marker's time | nothing |
| Changes COR-050 | no | yes | no | yes | yes |

## `reviewed-against` under each alternative

`reviewed-against` takes pointers under every alternative, since text in the tracker has no version any alternative gives. A version or a marker can only add to them.

- **A, recommended:** a list of sources, each a mapping with the keys a captured source's file uses (living-docs DEC-001 point 4):
  - **`title`:** what the source is, for the reader, such as "part 6 of #1352's note"
  - **`url`:** the absolute link to an issue or a comment, or to another repository. It is left out for this repository.
  - **`version`:** a commit on the source's default branch, or the time of the tracker version read
- **A design reviewed in the same change as its record:** the record cannot name the commit it lands in. Its `version` names the change itself, and the commit is found from the history, as `at`'s is (COR-050 point 3).
- **A design that lands before its record:** named by the commit where it landed, once the reviewer confirms nothing changed after the review.
- **No pull request's head:** a rebase loses a head reviewed mid-way.
- **B:** the same, plus a version for a versioned document.
- **C:** a tag per review keeps a design reviewed on a branch, in place of waiting for it to land.
- **D:** the same as A. The marker's time at the reviewed commit tells a later reader whether the meaning moved since.
- **E:** the same as A.
- **What a script checks:**
  - **The form, in the capability's validator:** the keys, an absolute link, and a commit id or a time. A validator reads the working tree only (COR-055 point 2).
  - **Reachability, in a command of its own beside `check-numbers`:** that a commit of this repository is on the default branch. It places each commit on the default branch only, so no base named for a run reaches that (COR-054 point 3). Which records a change adds is read against the run's base, as decided on 11 October ("Slicing").
  - **Offline in both:** validators and such commands run under the limits of COR-050 point 2 (COR-055 point 3).
  - **What it cannot place, it reports as unknown,** such as a commit beyond a shallow clone's history (COR-054 point 4).
  - **Why unknown and not failed:** the numbering setting treats a commit off the default branch as a problem, since freeing an id is a gate. `reviewed-against` is provenance, not a gate.
- **No tracker in the form:** an absolute link names no tracker, so checking the form needs no knowledge of one (software-analysis DEC-001 point 10).
- **Capture was weighed:** a planned record could copy the tracker text it read, as a record copies the evidence it drew on (software-analysis DEC-001 point 7). The copy is exact and offline, but it doubles the design in every record that reads it.
- **The template round's example uses these pointers already, as one line** (#1362's note, on PR #1374):

  ```yaml
  reviewed-against: "#1346's body on 8 October 2026, part 6 of #1352's note at 0192e5fc, and the maintainer's decisions in PR #1374's comments of 7 and 8 October"
  ```

  - `0192e5fc` is PR #1353's squash commit on main, so it stays reachable.
  - The comments are pointed at by pull request and day. Each comment's own link, with its time, would be exact.
- **Note:** the maintainer answered yes to the template round's question 1, so the field exists (#1362's note, "Decided: the revalidation record").

## Interactions

- **Friction's answers:** under B and D, one declaration on the changed document replaces each dependant's `unchanged` answer for that change. It never replaces `updated`, since a dependant that must change still changes.
- **Core rule 20, a person's decision:** a declaration that spares dependants answers for them.
  - **Under B:** a patch is a person's decision, shown word for word on the change check's list. A minor or a major spares nobody, so it needs no showing.
  - **Under D:** the reason is shown in the same way. COR-050 point 3's list holds the answers the change check asks for, so the refinement adds the reasons nobody asked for.
- **WRITE's RS-WRITE-013, keeping the meaning:** its list gives D's test.
  - **It is project-kit's rule:** WRITE binds `tech-docs/analysis/` only. A core refinement states the test in its own words, since a core record suits any project (COR-014).
  - **Text a person decided is never reworded for style** (RS-WRITE-013). So a recorded answer is never edited under a reason.
- **Rule sets' semantic versions:** kept, as a second scheme for a second question.
  - **A set's number serves pins across owners** (COR-051 point 7). No document is pinned.
  - **One scheme for both** would put numbers on documents nobody pins, or drop the pins inheriting sets need.
  - **Under D,** a rule's edit that keeps its meaning gives a reason. Such an edit needs no new major.
- **Records:** supersession stays the record's major. D classes the edits in place, which the decisions README already allows.
- **The release step:** untouched by A, C, D and E.
- **Changesets:** untouched. A design-ahead decision declares `none` however much it changes for its dependants (PRJ-002). So no document's class can be read off a changeset.

## Recommendation

The decided design: pointers for `reviewed-against`, no semantic versions on documents, the meaning marker later, and part anchors now, through a design of their own.

- **A for `reviewed-against`:** a planned record lists the sources of the design it reviewed, in its front matter. Each source is a mapping with `title`, `url` and `version`.
  - **Text in this repository:** a commit on the default branch, or `this change` when the design lands with the record. It has no `url`.
  - **Text in the tracker:** its link and the time it was read.
  - **Never a pointer:** a pull request's head, or a commit the default branch does not hold.
  - **Two checks:** the validator checks the form. A command of its own checks offline that each named commit is on the default branch, and reports "unknown" when it cannot tell.
- **Not B:** friction reads one bit of the number. A minor and a major ask the same, and the segment is a judgment nobody reads.
- **D later:**
  - **The history shows little for it:** 4 of 182 answers, and none on a record adopters receive.
  - **It adds, and migrates no data.** A document without a marker keeps today's reading.
  - **When to reopen it:** between two releases, the edits to records adopters receive are measured. A sync whose edits all keep the meaning is what D would spare.
  - **It ships as a surface change then,** likely a record of its own. It lets an upstream author clear an adopter's friction.
- **E now, by #1387's design:**
  - **A record's points** become headings that keep their numbers for good. A retired point keeps its id, with a stub where it was.
  - **An anchor can name a part:** a record's point, or a page's section or lead. Friction then compares only that part.
  - **The two costly dependants** re-point to the parts they rest on, and are counted again by part.
- **Not C now:** release tags already baseline the repository. A tag per review is the fallback where a design must be reviewed before it lands.
- **Rule sets keep their versions,** since inheriting sets pin them. What each part of a set's version means, and a check that it moves, were found on the way (items 2 and 3).

## Decisions

The maintainer decided questions 1 to 3 on 8 October, in comments on PR #1384. Question 4 went to a design of its own, #1387, which the maintainer decided on 9 October.

1. **Do documents carry semantic versions their authors declare?** **Decided: no,** as recommended, by the maintainer on 8 October.
   - **Why:** friction reads one fact from a version, whether the meaning changed. A minor and a major ask the same, so the segment is a judgment nobody reads.
   - **Where it stands:** software-analysis DEC-001 point 6 says the capability's artefacts and records carry no declared versions (PR #1391).
   - **What keeps its number:** rule sets and components, since others pin them (COR-051 point 7, PRJ-002).
   - **Not taken:** B for documents others anchor, where a patch spares the dependants.
2. **Does a depended-on document carry a meaning marker (D) now?** **Decided: not now,** as recommended, by the maintainer on 8 October.
   - **What it means:** a change cannot yet mark a document's meaning as unchanged. Every edit to an anchored document asks its dependants, as today.
   - **Why:** it would have spared 4 of 182 answers, and none on a record adopters receive. It can come later without a data migration.
   - **The trigger to revisit,** as the maintainer recorded it: between two releases, measure how many edits to records adopters receive kept the meaning (D, "A trigger that can be measured now").
   - **No issue:** this note keeps the measure, the trigger and the list of records D would touch.
   - **Not taken:** designing D now, as a record of its own.
   - **Reopened on 11 October: designed before adopters,** by the maintainer, in #1451, after #1429's design.
     - **Why:** the cost of a wording edit lands on every adopter anchored to the record, and the count above saw eleven days while records mostly grew. Changing friction's rules is cheapest before adopters rely on them. Practice has separated editorial from substantive changes from the start, as W3C and the IETF do.
     - **What the design must settle first:** trust across projects, since a reason written upstream would clear an adopter's friction.
     - **The trigger above is no longer needed.**
3. **What form does `reviewed-against` take?** **Decided: a list of mappings,** as recommended, by the maintainer on 8 October.
   - **The answer:** a planned revalidation record names the version of the design it reviewed, in its front matter. It is a list of mappings with `title`, `url` and `version`, the keys a captured source uses.
   - **Text in this repository:** pinned by a commit on the default branch, or by `this change` when the design lands with the record.
   - **Text in the tracker:** pinned by its link and the time it was read.
   - **Never a pointer:** a pull request's head, or a bare branch commit.
   - **The checks:** the validator checks the form. A separate command checks offline that each named commit is reachable from the default branch, and reports "unknown" when it cannot tell. It fails only on records the change adds, as the maintainer decided on 11 October ("Slicing").
   - **Why:** a pointer returns the text reviewed, which no number does. Text in the tracker has no version any alternative gives, and a list lets a script check each source.
   - **Not taken:** one line of text, as the template round proposed, which no script checks. Nor capturing the tracker text in the record.
4. **How is anchoring to part of a document (E) taken forward?** **Decided: design the mechanism now,** the alternative, by the maintainer on 8 October.
   - **Why:** 97 of the 182 answers a document caused came from two dependants that rest on a part. Anchors on the part could have spared up to 90 of them.
   - **What it reopens:** the settled positions E lists, and others #1387's design found. The maintainer chose it knowing that, and authorised all seven on 9 October.
   - **Where it was designed:** #1387, in its note `2026-10-08-part-anchors.md` (PR #1392). The maintainer decided its questions on 9 October.
   - **What that design decided:** a record's points become headings with permanent ids, and a retired point keeps its id with a stub. An anchor can name a record's point, or a page's section or lead.
   - **The two costly dependants:** they re-point to the parts they rest on, in place of the fixes this note proposed. living-docs DEC-001 point 3 keeps restating the rules, and the area index is trimmed to its sources' leads, not generated.
   - **The issues that carry it:** #1401, #1407, #1412, #1414, #1416, #1417, #1419, #1421, #1422, #1423, #1424, #1425, #1426 and #1427.
   - **Not taken:** fixing the two cases with what exists, and letting a backbone mechanism wait until the need recurs.

## Slicing

Each change the decisions need is carried by a filed issue, a merged change, or a draft to file. Where an issue carries a change only in part, the missing part is named.

- **`reviewed-against`, the field:** a list of mappings with `title`, `url` and `version` in the revalidation record's schema, required when `trigger` is `planned`.
  - **Carried by #1363, in part.** The template round's note gives the field to #1363 ("For the build"), but #1363's body names neither the field nor the record's schema.
  - **Edited on 10 October:** #1363 adds the field, its hint and example, and its form.
- **The form, checked by validation:** the keys, an absolute link, and a full commit id, `this change` or a time, each with or without a link as its source needs.
  - **The round gave it to #1364,** whose body checks only a body's structure.
  - **Edited on 10 October:** in #1363, in the record's schema. Validation applies that schema whatever the format rule's status, and the stamp, the validator and the reachability command then read one definition.
- **Reachability, a command of its own beside `check-numbers`:** each commit of this repository that a planned record names is on the default branch. It places commits on the default branch only, offline, and reports a commit it cannot place as unknown.
  - **Decided: it fails only on a record the change adds,** by the maintainer on 11 October. On a record the base already holds, it reports and never fails.
    - **Why:** a squash merge leaves a reviewed branch commit off the default branch, so naming one is an easy slip, caught where it can still be fixed. A record is never rewritten, so after a history rewrite, such as removing a secret, failing on older records would fail every change for good.
    - **Its cost:** it reads which records are new against the run's base, as the change check reads its change. The base reaches only that.
    - **Not taken:** failing on every record, and reporting only, which would let the usual slip through.
  - **The round gave it to #1364 too,** whose body does not name it.
  - **Filed:** #1448, "pkit analysis check-pointers fails a change that adds a record pointing off the default branch". It is a Task of its own, since it needs only #1363 while #1364 waits on #1360 and #1361.
- **The stamp:** `--reviewed-against` repeats, one source each.
  - **Carried by #1366, in part.** The round gave it the flag, but its body does not name it.
  - **Edited on 10 October:** #1366 adds the flag.
  - **Decided: the stamp warns on a commit off the default branch, and still writes,** by the maintainer on 11 October. It places the commit as #1448 does. Refusing would leave no way to write the record while the design's pull request is open. Added to #1366.
- **DEC-001's refinement:** point 6 names where the design a planned record reviewed stood, by pointer. A design that lands with its record is named by the change, and its commit is found from the history, as `at`'s is.
  - **Merged:** PR #1391, which closed #1358, as `839f7ef`. Point 6 says so on main.
  - **It also says** that the capability's artefacts and records carry no declared versions (question 1).
- **A record's points as stable identifiers:** carried by #1387's build.
  - **The decisions:** a core record that fixes a record's points for good (#1407), and ADR-057's two homes (#1412). The decisions README follows (#1422).
  - **The reading, validation and the numbering command:** #1414, #1416 and #1417.
  - **Friction for points:** #1419. Page sections follow (#1423), and living-docs learns part anchors (#1424).
  - **project-kit's records:** six amendment sections are folded first (#1401), and the records are converted (#1421).
  - **Until then:** project-kit's operational rules keep every point at its number (#1399, merged in PR #1400).
- **The two costly dependants:** carried by #1387's slice G, in the shape that design decided.
  - **The seven rules:** each anchors to the points of living-docs DEC-001 it rests on (#1426). DEC-001 point 3 keeps restating them.
  - **The area index:** says no more than its sources' leads, and anchors to them and two sections (#1425). It is not generated.
  - **The count again, by part:** #1427.
- **Found on the way, item 1, a commit range:** merged in PR #1391. Point 6 reads "a range of commits on the default branch", as the maintainer decided.
  - **Carried in part:** the texts that describe `change` still say "a range of commits". They are the record's schema, the stamp's help, the analysis-author skill, the template and the README's example.
  - **Edited on 10 October:** #1363 and #1366.
- **Found on the way, items 2 and 3, a rule set's version:** the rule-set reviewer's issues do not name them.
  - **Decided: a change's version is checked,** by the maintainer on 11 October. A set's major is the only signal an inheriting set's owner gets, and `LDOC` reaches every adopter, so a missed bump reaches them all. Practice checks a version others pin, as Elm's package manager and `cargo-semver-checks` do.
  - **Filed:** #1449, "Decide what each part of a rule set's version means and which sets it binds", a refinement of COR-051 point 7.
  - **Then:** #1450, "pkit rule-sets check-diff fails a change that makes a rule set's major due without moving it", after #1449 is accepted and #1408 lands.
  - **Not taken:** deciding the check with the refinement, and leaving the rule in prose.
- **Question 2, the meaning marker:** reopened on 11 October. Filed #1451, "Design how a document marks an edit that keeps its meaning", after #1429's design and before the first adopter. It starts from D, and from the list of records D would touch.

## Found on the way

1. **A commit range in a record's `change`:** software-analysis DEC-001 point 6 lets a record name "a range of commits", and the schema's example is `abc1234..def5678`. A range of branch commits leaves main with the squash (COR-009 point 1).
2. **A rule set's version is declared and never checked:** nothing checks that it moved when an accepted rule changed. The schemas README states the rule only in prose.
   - **Where a check would run:** it compares a change with a base, so it is a command of its own, not validation (COR-055 point 2).
   - **Not the friction change check:** it only warns in warning mode, and is dormant where nothing is anchored (COR-050 points 12 and 15). #1387's design placed its numbering check the same way.
3. **COR-051 point 7 defines only the major,** and a minor or a patch of a rule set has no stated meaning.
   - **The argument against B applies here too:** every change that matters to an inheriting set is a major, and pins read only the major. A major alone may be the honest form, and it is cheapest to change before adopters.

## Review

The critic and the architect reviewed the draft. Each finding is answered below, with what changed in the note.

### The critic

The critic found three red flags, eight gaps, eight weak arguments and five counter-alternatives. The largest change: the history was measured again, and the recommendation moved away from D.

**Red flags:**

1. **R1, a pull request's head does not last.** `refs/pull/N/head` names the latest head, so a rebase loses a head reviewed mid-way. A tag per review was undervalued.
   - **Answer:** accepted. A pull request's head is no longer a pointer, and a design reviewed before it lands is named where it lands.
   - **Also:** C now counts a tag per review as the one pointer that keeps a branch commit. The GitHub quote reads as a side effect, not a promise.
2. **R2, the count pushed the editorial share down.** It removed duplicates, put restatements with additions, classed only records, and used the wrong denominator.
   - **Answer:** accepted, and measured again. Each commit's change check was rerun, and each answer traced to the anchors its commit changed (What history shows).
   - **The result:** the editorial share fell further, to 4 of the 182 answers a document caused.
3. **R3, dependants another project owns were missing.** Adopters will anchor pkit's records, and their load cannot show in this history.
   - **Answer:** accepted. A section now covers them (Today, "Dependants that another project owns").
   - **The history still bears on them:** they meet the same mix of edits. A sync moves a marker if any one edit changed the meaning.

**Gaps:**

4. **G1, B's whole-repository rule missed an undeclared change.** **Answer:** fixed. Both checks now compare the content too.
5. **G2, a declaration per change let later friction hide earlier friction.** **Answer:** accepted. D is now the critic's meaning marker. A reason moves a dependant on only where the content before it is what the dependant last stood on.
   - **The three gaps beside it** are each answered in D: the record anchor's reading without the container, the decisions README's ban on revision markers, and point 3's list.
6. **G3, D's test dropped two of RS-WRITE-013's ways.** **Answer:** fixed. The test lists all seven, and doubt moves the marker, as for W3C.
7. **G4, gaps in `reviewed-against`'s shape.** **Answer:** each part accepted.
   - Items are mappings, and a tracker source carries its link and the time read.
   - Another repository is named, and a clone too shallow to tell reports unknown.
   - Offline is this design's own choice, and the forms name no tracker. Question 3 assumes the template round's yes.
8. **G5, "most of a design sits in the tracker" rested on one case.** **Answer:** fixed. The note now says text in the tracker has no version, which holds whatever the share.
9. **G6, the table's row on returning the text favoured A.** **Answer:** replaced by what each alternative adds to pointers.
10. **G7, the commit range comes from software-analysis DEC-001 point 6 itself.** **Answer:** fixed in "Found on the way", and it rides on #1358.
11. **G8, an identical rename does change a path anchor.** **Answer:** fixed. The rename rule now sits under the record anchor.

**Weak reasoning:**

12. **W1, a number holds across many changes, and a declaration does not.** **Answer:** accepted. It is why D is now a marker, and why a reason without one was dropped.
13. **W2, "a major asks no more than today" was asserted.** **Answer:** B now names the two softer minors and the stronger major, and why none was taken.
14. **W3, the strongest support for "a minor spares nobody" was missing.** **Answer:** added. COR-051 point 7 makes an added rule a major, and a minor is safe for callers, not implementers.
15. **W4, "now is the best time" sat in a Note, and "no migration later" was unshown.** **Answer:** moved into "In short".
    - **D:** a document without a marker keeps today's reading, so D migrates nothing.
    - **E:** what is due now is whether a record's points are stable identifiers, after the architect's review. The mechanism waits.
16. **W5, C was dismissed on a paused cadence, and a third place for numbers was missed.** **Answer:** fixed. The cadence reads 22 releases in seven weeks, then a pause. B names a job on main.
17. **W6, naming the changed point does not show what the dependant rests on.** **Answer:** accepted. The new count shows it: the index and the seven rules rest on parts their anchors do not name.
18. **W7, COR-050's reason against section anchors does not carry over.** **Answer:** accepted. E now says what carries over and what does not.
19. **W8, records already have a major, supersession.** **Answer:** added (Today, "Records"). What is open is how to class an edit in place.

**Counter-alternatives:**

20. **C1, capture the reviewed text.** **Answer:** weighed in `reviewed-against`, and offered as question 3's else. Not recommended, since it doubles a design in every record that reads it.
21. **C2, a meaning marker.** **Answer:** adopted as D's shape. Not recommended now, on the new count.
22. **C3, numbers written after the merge by a job.** **Answer:** named in B. The job needs D's marker to count, so C3 is D with a number for display.
23. **C4, E through rule sets or collection files.** **Answer:** weighed in E. The architect then found that neither reaches the two costly cases.
24. **C5, A now and D as an option, to start recording.** **Answer:** not taken. The new count needs no declarations, so D need not ship to measure its case.

**Writing and process:**

- **WRITE:** the elided verbs, the series in one sentence, the Note, the pronoun and "artifact" are fixed. The `reviewed-against` section now opens with its point.
- **Rule 17:** the questions are to be put to the maintainer one at a time.
- **The forms for #1358:** the methodology-reviewer checks them for tracker neutrality once the refinement is drafted.

### The architect

The architect found one architectural concern, three fit issues, two drifts and two points worth recording. It raised one escalation: question 4 needs the maintainer's leave before E's mechanism is designed.

**Architectural concern:**

1. **C1, E reopens three settled positions, and the draft named none.** Anchors rest on whole files (COR-050, ADR-057, living-docs DEC-001). COR-050 and COR-051 rejected parsing parts out of prose. The decisions README renumbers points on refinement.
   - **Answer:** accepted. E now lists what it would reopen, and why stable points are a precondition for the two checks to agree.
   - **The recommendation changed:** fix the two cases on the dependants' side, decide point stability now, and let the mechanism wait (COR-007). Question 4 states the stakes.

**Fit issues:**

2. **F1, reachability cannot sit in the validator, and offline is not a choice.** A validator reads the working tree only, and runs under COR-050 point 2's limits (COR-055 points 2 and 3).
   - **Answer:** accepted. The form stays in the validator, and reachability moves to a command of its own beside `check-numbers`. The claim that offline was this design's choice is gone.
   - **The severities differ on purpose:** an unplaced commit is unknown for provenance, and a problem for the numbering setting's gate. The note says so.
3. **F2, a record cannot name the commit it lands in.** **Answer:** accepted, option b. A design in the same change is named by the change, and its commit is found from the history, as `at`'s is.
4. **F3, a rule set's version check compares a change with a base.** **Answer:** accepted. "Found on the way" places it in a command of its own, and weighs a major alone.

**Drift:**

5. **D1, D touches more than the draft listed:**
   - It makes a new kind of document.
   - It moves a decision across projects, and runs on trust in an adopter.
   - It costs one round of friction when a marker is first added.
   - **Answer:** accepted. D lists each, and the records it would touch when reopened.
   - **The trigger is now measurable:** the edits to synced records between consecutive release tags.
6. **D2, "up to 97" overcounted.** One of the five edits to living-docs DEC-001 was to point 3, which all seven rules rest on. **Answer:** fixed, to up to 90.

**Worth recording:**

7. **W1, whether a record's points are stable identifiers cannot wait for adopters.** **Answer:** accepted. It became the first decision of #1387's design (Decisions, question 4).
8. **W2, several components record which version of a text was read.** **Answer:** accepted in part. `reviewed-against` takes a captured source's keys, and requires an absolute link. Moving the form into core waits for a further case (COR-007).

**No concern:** rejecting B, A as software-analysis's own, dropping pull-request heads, any merge style, and no growth in the configuration.
