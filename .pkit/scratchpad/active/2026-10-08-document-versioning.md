---
authors:
  - Aleš Kalfas <kalfas.ales@gmail.com>
started: 2026-10-08
---

# Document versions — declared numbers, pointers or baselines

A design for #1383. It asks whether pkit's documents should carry versions their authors declare, while pkit has no adopters to migrate.

- **Raised by:** the template round's revalidation-record question 1 (#1362, PR #1374). A planned record's `reviewed-against` must point at the design it reviewed.
- **Read from main at `30cfb15a`:** the records, the code and the history counts below.
- **Citations:** records and rules by permanent id and point. Code by file and line at `30cfb15a`, since code has no permanent ids.
- **Reviewed:** by the critic and the architect. Their findings and the answers are in "Review", at the end.
- **Next:** the maintainer answers the four questions. The issues in "Slicing" are filed on the maintainer's go.

## The question

Should pkit's documents carry versions their authors declare, and how does a record point at the version of a design it reviewed?

## In short

Documents need pointers, not declared numbers. Friction stays the reader's answer.

- **A number serves friction with one bit:** whether a change keeps the meaning. A minor or a major spares no dependant, and only the meaning test can be judged without knowing the readers.
- **History shows a small gain:** at most 13 of 353 `unchanged` answers since 27 September followed an editorial change to a record. Most followed an addition, which only each reader could judge.
- **The larger lever is elsewhere:** 51 of the 78 answers that a record's change caused name one point of that record. The dependant rested on another point.
- **`reviewed-against` needs pointers under every alternative:** most of a reviewed design sits in issue bodies and comments, which no document version covers.
- **Practice agrees:** it numbers contracts that others pin, flags links that a person clears, and lets only an editorial change skip review.

## Today

Each mechanism answers one question, and none gives a document a version of its own.

### Friction: does a dependant still hold? (COR-050)

The reader classifies a change after the fact. Each flagged artefact answers `updated`, or `unchanged` with a reason, or defers (COR-050 points 4 and 5).

- **What "changed" means:** a difference between two states, never a content hash or a number (COR-050 point 5, and its rationale on states).
  - **A path anchor:** any file the diff changes that the anchor matches, in content or mode (`src/project_kit/friction_check.py:943-952`). Only a rename with identical content is no change (`src/project_kit/friction_git.py:158-160`).
  - **A record anchor:** the record's whole file (`friction_check.py:911-914`). A typo fixed in COR-050 flags all eight artefacts anchored to it.
  - **An artefact anchor:** its content. That is its body compared as text and its own fields compared parsed, never the methodology's container (`src/project_kit/friction_discovery.py:1867-1870`, `friction_check.py:915-917`).
- **What it costs:** main took 186 commits from 27 September, when COR-050 was accepted, to `30cfb15a`. 112 of them wrote an `unchanged-because`, 403 lines in all, 353 of them distinct.
- **Who decides an answer:** a person, shown it word for word (COR-050 point 3, and core rule 20). An agent's answers in a change are shown once, on the change check's list, before the merge is authorised.
- **Note:** the marker `at` is a timestamp whose commit git finds. A commit id cannot be written into its own commit, and it leaves main on a squash (COR-050, rationale on the timestamp).

### Rule-set versions: may an inheriting set keep its pin? (COR-051)

A rule set carries a semantic version because other sets pin its major, as `living-docs:LDOC@1` (COR-051 point 7).

- **Who declares:** the set's author. A major is due when an accepted rule is added, withdrawn, superseded or tightened. It is also due when an offered extension point is removed (COR-051 point 7).
- **What a script checks:** that each pin names the inherited set's current major (`src/project_kit/rule_sets.py:1453-1502`).
- **What no script checks:** that the version moved when a rule changed. The rule-set module touches no git (`rule_sets.py:35-39`).
- **Two schemes already sit side by side:** each rule is an artefact too, so a changed rule flags its dependants whatever the version says (COR-051 point 2, "Anchoring").
- **In use:** `TECH` and `USER` pin `living-docs:LDOC@1`. `WRITE` is at 1.0.0, and nothing pins it yet.

### Changesets: what moves in the next release? (PRJ-002)

A pull request declares a component's segment, and the release step writes the numbers on main (PRJ-002 D1 and D3).

- **Who declares:** the change's author, per component, as a judgment of the surface (PRJ-002 D2).
- **What a script checks:** that a surface change carries a changeset, by a path heuristic. The guard checks presence, never truth (release README, "The surface-without-changeset CI guard").
- **Why numbers wait for the release:** branches that each wrote a version cell conflicted at merge (PRJ-002 rationale, PR #360).
- **Cadence:** the last release, `v1.149.0`, was tagged on 24 August. 326 changesets wait in `.changes/unreleased/`.
- **Note:** a decision's segment measures its effect on adopters, not on its dependants. A design-ahead decision declares `none`, however much its meaning changed (PRJ-002, on decision-touching pull requests).

### Captured sources: which version of an outside text did the pages read? (living-docs DEC-001 point 4)

One file per source records the version the pages were last checked against. A change to that file flags the pages.

- The two captured today use the two forms a version can take:
  - `keep-a-changelog.yaml` records the source's own number, `"1.1.0"`.
  - `common-changelog.yaml` records a commit, `bed3ea69…`, since that source publishes no number.

### Pointers: where can a text be read again?

A pointer returns a text. How long it lasts depends on what keeps it.

- **A commit on the default branch:** a squash merge puts one commit per pull request there (COR-009 point 1). It stays reachable, and a script can check it offline.
- **A branch commit:** gone from main after the squash, and the branch is deleted (COR-009 point 4). PR #1353's head `297cdae8` is not an ancestor of main, and its branch no longer exists.
- **A pull request's head:** GitHub still serves `refs/pull/1353/head` at `297cdae8`. A plain clone does not fetch `refs/pull/*`, so a check that needs no network cannot read it (COR-050 point 2).
- **A tag:** keeps its commit reachable, and a plain clone fetches it. Releases tag main (PRJ-002 D3), 26 times so far.
- **An issue body or a comment, with its date:** GitHub keeps each edit. #1346's body lists two, on 5 and 6 October. Only the hosting service answers, over the network.

## What "a version of a document" could mean

Three things go by the name, and each answers a different question.

- **A number the author declares:** says how much changed between two versions. It cannot return the text.
- **A pointer:** returns the text. It says nothing of how much changed.
- **A baseline:** a named set of pointers taken at one moment, such as a release tag. It returns many texts under one name.
- **Note:** a number can lead to a pointer. Git finds the commit that first carried it, as COR-050 point 3 finds the commit behind `at`. That holds only once the number reaches main, and only while one number names one text.

## What practice does

Practice numbers the documents others implement against, and flags a link when anything under it changes. The one class of change it lets skip review is the editorial one.

- **Semantic Versioning** (semver.org): major, minor and patch are defined against a public API the software must declare. The specification is written for software, and leaves the bump to the author.
  - **Documents with numbers of their own are contracts.** The AWS Encryption SDK specification gives each document a semantic version and a changelog of its own (its `VERSIONING.md`). OpenAPI's `info.version` is a string the API document's author declares.
  - **An adaptation to prose exists, with no adoption seen.** SemVerNL ties a major to the meaning of an abstract, and a patch to no significant effect on meaning (`ptsteadman/semver-for-natural-language` on GitHub).
- **Versioned documentation sites** version a whole set, never one page.
  - **Docusaurus** copies the docs folder into a versioned folder when someone cuts a version. It advises versioning only when needed (docusaurus.io, "Versioning").
  - **Read the Docs** builds a version from each git tag or branch. `latest` follows the default branch, and `stable` the highest release (Read the Docs, "Versions").
- **Requirements tools** mark a link suspect on any change, and a person clears it. That is friction's shape.
  - **DOORS Next:** "If you change the contents of either artifact, the status of the link becomes suspect." A team member then sets it valid or invalid (IBM documentation, "Link validity").
  - **The status sits on the link, with no version number.** Each artifact's revisions are kept, and a baseline freezes a configuration at a milestone (IBM documentation and jazz.net).
  - **DOORS Classic narrows what counts as a change by attribute.** Only attributes set to affect change dates make a link suspect (a jazz.net forum archive of 2012, quoting the DOORS help).
  - **ReqIF** gives each element a `LAST-CHANGE` timestamp and no version number (the ReqIF 1.0 schema). COR-050's `at` is the same kind of marker.
- **Standards bodies** class each change, and the editorial class needs no review.
  - **W3C names five classes.** "The first two classes of change are considered editorial changes": no change to text content, and changes that do not functionally affect interpretation.
  - **W3C's consequence:** "Editorial changes to a Recommendation require no technical review of the intended changes." (W3C Process Document of 18 August 2025)
  - **W3C also points by address:** each specification has a dated "This version" address beside a "Latest version" one, as WCAG 2.2 has.
  - **The IETF never changes what an RFC means.** A correction comes as a new RFC that obsoletes or updates the old one (RFC 2026 and RFC 7322). RFC 9720 allows a reissue only where the semantic content is preserved.
  - **ISO** reviews each standard every five years, and confirms, amends, revises or withdraws it (ISO/TC 211's good practice on systematic review).
- **Document control:** ISO 9001:2015 asks for control of changes, with version control only as an example (clause 7.5.3.2, read through a secondary source).
- **GitHub:** `refs/pull/` is read-only, and a commit stays reachable through any pull request that references it (GitHub Docs, "Removing sensitive data from a repository").
- **What follows for pkit:**
  - **Numbers go to contracts that others pin.** pkit already numbers its rule sets (COR-051) and its components (PRJ-002).
  - **A dependant of a change gets a flag that a person clears.** pkit's friction is that mechanism (COR-050).
  - **The one class that practice lets an author settle alone is the editorial one.** W3C's line between editorial and substantive is alternative D's line below.
  - **Sets get versions at releases and milestones.** That is alternative C, which pkit's release tags already give.
  - **Pointers are dated addresses.** W3C's dated address and an RFC that never changes are alternative A's pointers.
- **Not verified:**
  - what ISO/IEC/IEEE 29148 and ISO/IEC/IEEE 15289 say on baselines, traceability and revision history, since both are paywalled
  - any source that gives the bump to a role other than the author
  - a GitHub statement that `refs/pull/N/head` outlives the branch. PR #1353 shows it does (Today, "Pointers").

## What a declaration could spare

A declared version can spare only the answers a change to a document causes. Code carries no version. This section counts those answers on main's history.

- **The sample:** the 353 distinct `unchanged-because` texts written on main from 27 September to `30cfb15a`.
- **The method:** a keyword count over the texts, not a measurement. A text was counted as a record's when it opens by naming the record that changed.
- **78 open with a changed record.** The other 275 follow a change to code, a page or several things at once.
- **13 of the 78 follow an editorial-looking change.** Examples: the ADRs losing their dated trailers (#860), one rationale sentence, an edit that was reverted.
  - **Not all 13 keep the meaning.** One renames "provider" to "filler", which RS-WRITE-013 counts as swapping a term.
- **55 of the 78 follow an addition or a restatement,** such as "DEC-001 point 3 gains a paragraph …". Semantic versioning calls an addition minor.
  - **Each dependant judged the addition itself.** For example: "it says nothing of where a fact is stated, so each fact is still stated once". Only the reader could tell.
- **51 of the 78 name the one point that changed.** The dependant rested on another point of the same record.
  - **An example:** one edit to living-docs DEC-001 point 8 drew seven answers. Each came from a rule or the README anchored to the whole record.

## The alternatives

Each is weighed by what it gains, what it costs on every edit, and what a script can check.

### A — No document versions, pointers only

Friction stays as it is. A record names what it reviewed by pointers.

- **Gains:**
  - Nothing new on any edit, and nothing new in COR-050.
  - A pointer returns the exact text reviewed, which no number does.
- **Costs:**
  - Every edit of a depended-on record still asks every dependant, editorial ones included.
  - A reader learns how far a design moved since a review by reading the diff, not a number.
- **What a script checks:**
  - **A commit on the default branch:** that it is an ancestor of the branch, offline. The branch resolves as COR-054 point 2 says.
  - **A tag:** that it exists and names a commit on the default branch, offline.
  - **A pull request's head:** its form only, offline. Whether GitHub holds it needs the network.
  - **An issue body or a comment, with a date:** its form only.
- **Per edit:** nothing.

### B — Author-declared semantic versions per document

Each depended-on document carries `version: X.Y.Z`. Each change moves it, and friction reads the move.

- **The rule friction would need:** a patch spares the dependants, and any other move asks them as today.
  - **A minor cannot spare them.** An addition may contradict what a dependant says is absent. The 55 answers above each had to read the addition.
  - **A major asks no more than today.** Today's flag already demands an answer, and a dependant may still hold after a major.
  - **So friction reads one bit of the number:** a patch or not.
- **What changes:**
  - **COR-050 points 5 and 6:** a record or artefact anchor changes only where its target moved past a patch. That is a fourth way to clear friction, so COR-050 needs a refinement.
  - **The whole-repository check:** stale where the target's major and minor at the latest commit differ from those at the revalidation point. Git finds both, as for `at`.
  - **The change check:** fails a change to a versioned document that does not move its version, or moves it back.
  - **Undeclared changes:** a change that moves no version still flags, as today.
  - **Schemas:** a decision record has no version field. Each record, page and artefact that others anchor would gain one.
  - **Changesets:** unchanged. A document's segment and a component's segment answer different questions.
- **Which documents:** only those others anchor through a record or artefact anchor. A path carries no version, so path anchors stay as they are.
  - **Today:** 217 of the 391 anchor values point at a record or an artefact, across 114 distinct targets. The other 174 point at paths and sources.
- **Where the number is written:**
  - **On the branch:** two lines of work that edit different parts of one record both write its version line. They conflict, which PRJ-002 removed for components (PR #360). Both may also write `1.2.4` for two different texts.
  - **At the release:** the numbers then lag the text by weeks, and friction could not wait for them. The last release was on 24 August.
- **Gains:**
  - An editorial change stops flagging dependants.
  - A reader sees at a glance how far a document moved since a version they read.
- **Costs:**
  - A declaration on every edit of 114 depended-on documents.
  - The author judges for readers they may not know. A wrong patch silently clears friction for all of them.
  - The version line conflicts between lines of work, or one number names two texts.
  - The number still needs a pointer to return the text.
- **What a script checks:** that a changed document moved its version, forward, by one step. Never that a patch kept the meaning.
- **Per edit:** one judgment of the segment, and one line, on every change to a depended-on document.

### C — Baselines: a tag for a set of documents at a moment

Someone tags the analysis, or a design's documents, at a moment. A record points at the tag.

- **What exists:** every release tags main, so `v1.149.0` is already a baseline of every document (PRJ-002 D3).
- **Gains:**
  - One name covers many documents.
  - A tag keeps its commit reachable, and a plain clone fetches it. A script checks it offline.
- **Costs:**
  - Who cuts a baseline, and when, is a new duty. Release tags are too rare for it: the last is six weeks old.
  - A tag per review adds a tag per planned record. On a branch commit, it repeats what `refs/pull/N/head` already keeps.
  - A planned review reads a design that is mostly outside the repository. #1346's design is an issue body and pull-request comments, and no tag holds them.
  - Friction gains nothing, since a baseline says nothing of how much changed.
- **Per edit:** nothing. Per baseline: one tag, and the decision to cut it.

### D — A declaration that a change keeps the meaning

The author of a change to a depended-on document may declare that it keeps the meaning, with a reason. The declaration spares the dependants, and no number is kept.

- **Its shape follows COR-050's:** a marker and a reason in the changed document's friction block, as `at` and `unchanged-because` are. The reason must change in the same diff.
- **The test belongs to the text alone:** the change adds, drops, weakens or narrows no claim, and swaps no term. That is RS-WRITE-013's list, which an author applies without knowing the readers.
- **Practice draws the same line:** W3C's editorial changes do not functionally affect interpretation, and need no technical review (What practice does).
- **Gains:**
  - An editorial change stops flagging dependants. One author's answer replaces one answer per dependant.
  - Optional: an author who does not declare gets today's behaviour.
  - Additive: no field becomes required, and no installed project needs a migration.
- **Costs:**
  - The declaration answers for others. So it is a person's decision, shown word for word on the change check's list (COR-050 point 3, core rule 20).
  - A decision record carries no friction block today. It would need the methodology's container, which the decisions specification governs.
  - The whole-repository check must tell a declared change from an undeclared one. Comparing the content at the last declaration with the latest content keeps that a comparison of states.
  - On the sample, it would spare at most 13 of 353 answers.
- **What a script checks:** that the reason is new in the diff. Never that the meaning was kept.
- **Per edit:** nothing, unless the author chooses to declare.

### E — Finer anchors: rest on the point, not the record

A dependant anchors to the point of a record it rests on, so a change to another point asks it nothing.

- **What the history shows:** 51 of the 78 answers a record caused name the one point that changed, and the dependant rested on another.
- **Gains:** the largest share of the answers a record causes.
- **Costs:**
  - COR-050 rejected anchors per section that are parsed out of prose (COR-050, alternatives). A record's points are numbered list items, which are still prose.
  - A resolver names files, not parts of files (COR-050 point 2). Only a collection entry is narrower than its file today (COR-050 point 1).
  - A point anchor needs permanent point numbers, as rule ids are permanent (COR-051 point 3). Nothing forbids renumbering a record's points today.
- **Per edit:** nothing. Per anchor: the author names points instead of a record.
- **Note:** this is a question of anchoring, not of versions. It is listed because the history points at it.

### Side by side

| | A pointers | B semantic versions | C baselines | D meaning kept | E finer anchors |
|---|---|---|---|---|---|
| Spares the dependants of | nothing | a patch | nothing | a declared change | a change to another point |
| Answers spared on the sample | 0 | at most 13 | 0 | at most 13 | up to 51 |
| Cost on each edit | none | a segment, always | none | a reason, when declared | none |
| Returns the reviewed text | yes | no | yes | no | no |
| Changes COR-050 | no | yes | no | yes, additively | yes, additively |

## `reviewed-against` under each alternative

The field says where a design stood when a planned record reviewed it. It needs pointers under every alternative, since most of a design is not a versioned document.

- **A:** a list of sources, each with a pointer in one of three forms:
  - **a commit on the default branch,** for what reached it, such as `part 6 of #1352's note at 0192e5fc`
  - **a pull request with its head,** for what a branch held, such as `PR #1374 at 36ed934f`
  - **an issue or a comment with its date,** for text in the tracker, such as `#1346's body on 8 October 2026`
- **B:** the same, plus a version for a versioned document. The version tells how far that document moved since. It adds nothing for an issue body or a comment.
- **C:** a baseline tag where one exists. A design spread over an issue and comments still needs A's forms.
- **D and E:** as A. Neither gives a document an identity beyond its pointer.
- **What a script checks in A's forms:** a commit on the default branch, offline. A pull request's head and an issue's text on a day, only through the hosting service.
- **The template round's example already uses A's forms** (#1362's note, on PR #1374):

  ```yaml
  reviewed-against: "#1346's body on 8 October 2026, part 6 of #1352's note at 0192e5fc, and the maintainer's decisions in PR #1374's comments of 7 and 8 October"
  ```

  - `0192e5fc` is PR #1353's squash commit on main, so it stays reachable.
  - The comments are pointed at by pull request and day. A comment's own link would be exact.

## Interactions

- **Friction's answers:** under B and D, one declaration on the changed document replaces each dependant's `unchanged` answer for that change. It never replaces `updated`, since a dependant that must change still changes.
- **Core rule 20, a person's decision:** a declaration that spares dependants answers for them.
  - **Under B:** a patch is a person's decision, shown word for word on the change check's list. A minor or a major spares nobody, so it needs no showing.
  - **Under D:** the declaration and its reason are shown in the same way.
- **WRITE's RS-WRITE-013, keeping the meaning:** its list gives the test for a change that keeps the meaning.
  - **It is project-kit's rule:** WRITE binds `tech-docs/analysis/` only. A core refinement would state the test in its own words, since core rules suit any project (COR-014).
  - **Text a person decided is never reworded for style** (RS-WRITE-013). So a recorded answer is never a candidate for a patch.
- **Rule sets' semantic versions:** kept, as a second scheme for a second question.
  - **A set's number serves pins across owners** (COR-051 point 7). No document is pinned.
  - **One scheme for both** would put numbers on documents nobody pins, or drop the pins inheriting sets need.
  - **Under D,** a rule's edit that keeps its meaning could declare so. Such an edit needs no new major.
- **The release step:** untouched by A, C, D and E. Under B, numbers written at the release are weeks late for friction. Numbers written on branches bring back the conflicts PRJ-002 removed.
- **Changesets:** untouched. A design-ahead decision declares `none` however much it changes for its dependants (PRJ-002). So no document segment can be read off a changeset.

## Recommendation

Choose A: documents carry no declared numbers, and `reviewed-against` names pointers.

- **A for `reviewed-against`:** a list of sources, each with a pointer in one of A's three forms. No tag and no number.
- **Not B:** friction reads one bit of the number. Minor and major spare nobody, and the version line conflicts across lines of work.
- **Not C now:** release tags already baseline the repository, and a planned review's design lies mostly outside it.
- **D later, if editorial changes keep flagging many dependants:** it is additive, so deciding later costs no migration. The sample shows at most 13 answers it would spare (COR-007).
- **E as a question of its own:** it is the larger lever in the history. It needs its own design under EPIC #234.
- **Note:** "now is the best time" applies to B alone. B would add a field to every depended-on document. D and E only add, and need no migration later either.

## Questions for the maintainer

Each question is one decision, with a recommendation.

1. **Do documents carry versions their authors declare?**
   - **Recommendation:** no. A record names what it read by pointers, and friction stays the reader's answer.
   - **Else:** B for documents others anchor, where a patch spares the dependants.
2. **What form does `reviewed-against` take?**
   - **Recommendation:** a list in the front matter, one source per item. Each item names a commit on the default branch, a pull request with its head, or an issue or a comment with its date. A script checks the commits offline.
   - **Else:** one line of text, as the template round proposes, which no script checks.
3. **Is a declaration that a change keeps the meaning (D) designed now?**
   - **Recommendation:** not now. Record the measure in an issue, with the count that would reopen it.
   - **Else:** a refinement of COR-050 now, with the declaration on rule 20's list.
4. **Does anchoring to one point of a record (E) get a design of its own?**
   - **Recommendation:** yes, as its own issue under EPIC #234. 51 of the 78 answers a record caused point there.
   - **Else:** wait until the friction load is felt.

## Slicing

On the recommended answers, the work rides on issues the template round already planned, plus three new ones.

- **#1363, the field:** `reviewed-against` is a list of sources, each with a pointer in one of three forms. It is required when `trigger` is `planned`.
- **#1364, the check:** checks each item's form, and that a commit it names is an ancestor of the default branch. It reports a pull request's head and an issue's date as unchecked.
- **#1366, the stamp:** `--reviewed-against` repeats, one source each.
- **#1358, DEC-001's refinement:** point 6 says a planned record names where the design it reviewed stood, by pointer.
- **New, on question 3:** an issue that records this note's count and the count that would reopen D.
- **New, on question 4:** a design note for anchoring a dependant to one point of a record.
- **New, found on the way:** a record's `change` names commits that stay reachable (below, item 1).

## Found on the way

1. **A commit range in a record's `change`:** the record schema allows `abc1234..def5678`. A range of branch commits leaves main with the squash (COR-009 point 1).
2. **A rule set's version is declared and never checked:** nothing checks that it moved when an accepted rule changed. The schemas README states the rule only in prose.
3. **COR-051 point 7 defines only the major:** a minor or a patch of a rule set has no stated meaning.

## Review

REVIEW-TBD
