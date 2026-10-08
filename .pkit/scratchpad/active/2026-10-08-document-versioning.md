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
- **Next:** the maintainer answers the four questions, one at a time. The issues in "Slicing" are filed on the maintainer's go.

## The question

Should pkit's documents carry versions their authors declare, and how does a record point at the version of a design it reviewed?

## In short

No semantic versions for documents, and no meaning marker yet. Friction's cost comes from what a dependant rests on, not from how an author classes a change.

- **Why not semver:** a minor spares no dependant, and a major asks no more than today. pkit's rule sets already make an added rule a major (COR-051 point 7).
- **What semver reduces to:** one fact, whether the meaning changed. Alternative D carries it as a marker that moves only when the meaning changes.
  - **It compares states, as `at` does.** So it holds across many changes: a squash, the stretch since a revalidation, or an adopter's sync.
- **Why D can wait:** of 182 answers that a document's edit caused since 27 September, 4 followed an edit that kept the meaning.
  - **It adds, and migrates nothing:** a document without a marker keeps today's reading, so D can come later.
- **Where the cost is:** 97 of the 182 came from two dependants anchored to whole documents while resting on a part.
  - **Finer anchors (alternative E) are the lever.** Their design is the one to do now, before adopters anchor pkit's records whole.
- **`reviewed-against` takes pointers under every alternative:**
  - **Text in a repository:** a commit on its default branch. A pull request's head is no pointer, since a rebase loses it.
  - **Text in the tracker:** the tracker's link, with the time of the version read.
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
  - **Every other record edit behind them changed the meaning.** Each added a paragraph, corrected a claim or restated a limit, judged one by one from its word diff.
  - **The READMEs' edits were not all judged one by one.** Those read added commands, names or steps.
- **97 of the 182 came from two dependants of whole documents:**
  - **62 from the area index, `.pkit/README.md`:** it anchors ten area READMEs whole, so each edit of one asked it. None of those edits touched what the index says.
  - **35 from the seven rules anchored to living-docs DEC-001:** five edits each asked all seven rules. Each answer found the edit irrelevant to its rule.
- **So the lever is what a dependant rests on.** A meaning marker would have spared 4 answers. Anchors on the part a dependant rests on could have spared most of the 97.
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
- **For an adopter:** a synced record brings its marker. An adopter's artefact is asked only when the marker moved since its revalidation. It trusts that the source held every edit to the rule, as project-kit's enforcing mode does.
- **Gains:**
  - An edit that keeps the meaning stops asking dependants, here and in every adopter.
  - A reader, and a `reviewed-against`, see when a document's meaning last changed.
  - One fact that holds across changes, with no segment and no number to conflict over.
- **Costs:**
  - One choice on each edit of a marked document, much as a changeset is.
  - A wrong reason clears friction for every dependant, adopters' included, and no dependant can contest it. The diff stays readable, and the reason sits on the list the merge authoriser reads.
  - COR-050 needs a refinement: the marker, the reason, the record anchor's new reading, the list and the walk.
  - Decision records gain the methodology's container.
  - **It would have spared 4 of the 182 answers a document caused** (What history shows).
- **What a script checks:** that each edit of a marked document moves the marker or gives a new reason, and that the marker moves forward. Never that the meaning was kept.
- **Per edit:** one choice on each edit of a marked document. Nothing on any other.
- **A reason with no marker was weighed and dropped:** a state shows only its latest reason. So it cannot say what lies between two states, which is what both checks compare.

### E — Finer anchors: rest on the part, not the whole document

A dependant anchors to the part of a document it rests on, so an edit to another part asks it nothing.

- **What history shows:** 97 of the 182 answers a document caused came from dependants that anchor a whole document and rest on a part of it.
  - **The area index** rests on what each area README is for. It was asked about 62 edits that left that alone.
  - **The seven rules anchored to living-docs DEC-001,** six in `LDOC` and one in `USER`, rest on its point 3. They were asked 35 times.
- **What carries over from COR-050's rejected alternative:** parsing a numbered list out of markdown, and the upkeep that made it reject anchors on every statement (COR-050, alternatives).
- **What does not carry over:** "a second convention". A record's points are already how records are cited, as "COR-050 point 5".
- **Ways in through existing machinery:**
  - **Rule sets:** a point that others must follow becomes a rule, with a permanent id that is already an artefact (COR-051 points 2 and 3).
  - **Collection files:** a document kept as entries, each its own artefact (COR-050 point 1).
- **Costs:** permanent point numbers, which nothing requires today. A resolver names files, not parts of files (COR-050 point 2).
- **Why its design is due now:** it may change how records are written or cited. That is cheapest before adopters anchor pkit's records whole.
- **Note:** this is a question of anchoring, not of versions. It is listed because the history points at it, and needs a design of its own.

### Side by side

| | A pointers | B semantic versions | C baselines | D meaning marker | E finer anchors |
|---|---|---|---|---|---|
| Spares the dependants of | nothing | a patch | nothing | an edit with a reason | an edit to another part |
| Answers spared in the sample, of 182 | 0 | at most 4 | 0 | 4 | up to 97 |
| Holds across many changes | not applicable | yes | not applicable | yes | yes |
| Cost on each edit | none | a segment, always | none | a marker or a reason, on marked documents | none |
| What `reviewed-against` adds to pointers | nothing | a version per document | a tag per review | the marker's time | nothing |
| Changes COR-050 | no | yes | no | yes | yes |

## `reviewed-against` under each alternative

`reviewed-against` takes pointers under every alternative, since text in the tracker has no version any alternative gives. A version or a marker can only add to them.

- **A, recommended:** a list of sources, each a mapping a script reads:
  - **text in a repository:** the repository when it is not this one, and a commit on its default branch, such as `0192e5fc` for part 6 of #1352's note
  - **text in the tracker:** the link to the issue or the comment, and the time of the version read, such as #1346's body edited on 6 October
  - **what the source is,** in a few words, for the reader
- **A design reviewed before it lands:** it is pointed at by the commit where it lands, once the reviewer confirms nothing changed after the review. A pull request's head is not used, since a rebase loses a head reviewed mid-way.
- **B:** the same, plus a version for a versioned document.
- **C:** a tag per review keeps a design reviewed on a branch, in place of waiting for it to land.
- **D:** the same as A. The marker's time at the reviewed commit tells a later reader whether the meaning moved since.
- **E:** the same as A.
- **What a script checks in A's form:**
  - **A commit of this repository:** that the default branch holds it. A clone too shallow to tell reports it unknown, never failed, as COR-054 point 4 reports what it cannot resolve.
  - **Another repository's commit and the tracker's text:** their form only.
- **Offline is this design's own choice:** the record check is no resolver, so COR-050 point 2 does not bind it.
- **No tracker in the form:** the forms name a link and a time, not GitHub. software-analysis works with no work-tracking component (software-analysis DEC-001 point 10).
- **Capture was weighed:** a planned record could copy the tracker text it read, as a record copies the evidence it drew on (software-analysis DEC-001 point 7). The copy is exact and offline, but it doubles the design in every record that reads it.
- **The template round's example uses these forms already, as one line** (#1362's note, on PR #1374):

  ```yaml
  reviewed-against: "#1346's body on 8 October 2026, part 6 of #1352's note at 0192e5fc, and the maintainer's decisions in PR #1374's comments of 7 and 8 October"
  ```

  - `0192e5fc` is PR #1353's squash commit on main, so it stays reachable.
  - The comments are pointed at by pull request and day. Each comment's own link, with its time, would be exact.
- **Note:** the field exists only if the maintainer answers yes to the template round's question 1. Question 2 below assumes so.

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

Choose A for `reviewed-against`. Give documents no semantic versions, leave the meaning marker for later, and design finer anchors now.

- **A for `reviewed-against`:** a list of sources, each a commit on a default branch or the tracker's link with the time read.
- **Not B:** friction reads one bit of the number. A minor and a major ask the same, and the segment is a judgment nobody reads.
- **D later:**
  - **The history shows little for it:** 4 of 182 answers.
  - **It adds, and migrates nothing.** A document without a marker keeps today's reading.
  - **When to reopen it:** an adopter's syncs show edits that keep the meaning asking many artefacts, or a later window here shows more than a handful.
  - **It ships as a surface change then.** It lets an upstream author clear an adopter's friction, which a changeset announces.
- **E now, as its own design:** 97 of 182 answers point at it. It may change how records are written or cited, which is cheapest before adopters.
- **Not C now:** release tags already baseline the repository. A tag per review is the fallback where a design must be reviewed before it lands.

## Questions for the maintainer

Each question is one decision, with a recommendation. Ask them one at a time.

1. **Do documents carry semantic versions their authors declare?**
   - **Recommendation:** no. Friction reads one fact from a version, whether the meaning changed, and minor and major ask the same.
   - **Else:** B for documents others anchor, where a patch spares the dependants.
2. **Does a depended-on document carry a meaning marker (D) now?**
   - **Recommendation:** not now. It would have spared 4 of 182 answers, and it can come later without a migration.
   - **Else:** refine COR-050 now, and build the marker for core and capability records first.
3. **What form does `reviewed-against` take?**
   - **Recommendation:** a list of mappings, one source each. A source is a commit on a default branch, or the tracker's link with the time read. A script checks this repository's commits.
   - **Else:** one line of text, as the template round proposes, which no script checks. Or capture the tracker text in the record.
4. **Does anchoring to a part of a document (E) get its design now?**
   - **Recommendation:** yes, as its own issue under EPIC #234, before adopters anchor pkit's records.
   - **Else:** wait until an adopter's friction load is felt.

## Slicing

On the recommended answers, the work rides on issues the template round already planned, plus two new ones.

- **#1363, the field:** `reviewed-against` is a list of mappings, one source each, required when `trigger` is `planned`.
- **#1364, the check:** checks each item's form, and that a commit of this repository is on the default branch. It reports what it cannot reach as unknown.
- **#1366, the stamp:** `--reviewed-against` repeats, one source each.
- **#1358, DEC-001's refinement:** point 6 says a planned record names where the design it reviewed stood, by pointer. It also settles item 1 of "Found on the way".
- **New, on question 4:** a design note for anchoring a dependant to a part of a document. The area index and the seven rules are its first cases.
- **New, found on the way:** a rule set's version, checked when its accepted rules change, and the meaning of its minor and patch (items 2 and 3).
- **On question 2, no issue:** this note keeps the measure and the trigger that would reopen D.

## Found on the way

1. **A commit range in a record's `change`:** software-analysis DEC-001 point 6 lets a record name "a range of commits", and the schema's example is `abc1234..def5678`. A range of branch commits leaves main with the squash (COR-009 point 1).
2. **A rule set's version is declared and never checked:** nothing checks that it moved when an accepted rule changed. The schemas README states the rule only in prose.
3. **COR-051 point 7 defines only the major:** a minor or a patch of a rule set has no stated meaning.

## Review

The critic and the architect reviewed the draft. Each finding is answered below, with what changed in the note.

### The critic

The critic found three red flags, eight gaps, eight weak arguments and five counter-alternatives. The largest change: the history was measured again, and the recommendation moved from D to E.

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
    - **E:** its design is the one due now, since it may change how records are written or cited.
16. **W5, C was dismissed on a paused cadence, and a third place for numbers was missed.** **Answer:** fixed. The cadence reads 22 releases in seven weeks, then a pause. B names a job on main.
17. **W6, naming the changed point does not show what the dependant rests on.** **Answer:** accepted. The new count shows it: the index and the seven rules rest on parts their anchors do not name.
18. **W7, COR-050's reason against section anchors does not carry over.** **Answer:** accepted. E now says what carries over and what does not.
19. **W8, records already have a major, supersession.** **Answer:** added (Today, "Records"). What is open is how to class an edit in place.

**Counter-alternatives:**

20. **C1, capture the reviewed text.** **Answer:** weighed in `reviewed-against`, and offered as question 3's else. Not recommended, since it doubles a design in every record that reads it.
21. **C2, a meaning marker.** **Answer:** adopted as D's shape. Not recommended now, on the new count.
22. **C3, numbers written after the merge by a job.** **Answer:** named in B. The job needs D's marker to count, so C3 is D with a number for display.
23. **C4, E through rule sets or collection files.** **Answer:** added to E as its ways in.
24. **C5, A now and D as an option, to start recording.** **Answer:** not taken. The new count needs no declarations, so D need not ship to measure its case.

**Writing and process:**

- **WRITE:** the elided verbs, the series in one sentence, the Note, the pronoun and "artifact" are fixed. The `reviewed-against` section now opens with its point.
- **Rule 17:** the questions are to be put to the maintainer one at a time.
- **The forms for #1358:** the methodology-reviewer checks them for tracker neutrality once the refinement is drafted.

### The architect

ARCHITECT-TBD
