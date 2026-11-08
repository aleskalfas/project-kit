---
id: ADR-082
title: Release notes lead with what an adopter must do, give each change one line, and count internal changes
status: proposed
date: 2026-11-08
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

## Summary

**In plain terms:** a release's notes are for adopters, so they hold what an adopter needs and little else.
- **What needs action comes first.** A changeset may say, in a field of its own, who must do what. A `major` must say it. The change is marked "Action required" and listed first. A short digest of the release opens its GitHub Release and its pull request.
- **One line per change.** `CHANGELOG.md` prints the first paragraph of each changeset. The release keeps every changeset it consumes in git, and each line links to it, so the detail stays one click away.
- **A component's first release is one line.**
- **Changes no adopter sees are counted.** Each component's `none` changesets become one count line, which links to them. A change is internal by the `none` judgment its author makes and a reviewer checks, not by a second judgment.
- **Whose rules these are.** `pkit release` does all of this for every project that runs it, and a page the CLI area ships describes it. How a line is worded, and how project-kit judges what an adopter sees, are project-kit's own.

**What this leaves listed.** A change an adopter sees stays listed, one line each, even where few adopters care. The list loses record amendments and other changes nobody sees, and first-release history.

**Why an ADR.** It decides what the release step builds: its fields, the files it keeps, the changelog it writes and the notes it publishes ([COR-025](../../../.pkit/decisions/core/COR-025-adr-decision-space.md)). Every project that runs `pkit release` gets them. The policy half, which changes are surface changes and how they are judged, is [PRJ-002](../../../.pkit/decisions/project/PRJ-002-version-bump-policy.md)'s. This change edits PRJ-002 once this record is accepted.

## Context

**What an analysis of the changelog found** (#2879). It read the release notes as they stood after 2.0.0, and the pending 2.1.0 changesets.
- **Size.** 2.0.0's section holds 573,512 characters in 568 entries, about six sentences an entry. Only 6% are one sentence, though the release reference asks for one.
- **Value.** In a sample of 36 entries, about one asked a plain adopter to act. About three asked one who writes their own components or scripts. None of them was a `major`, and none was marked.
- **Buried breaks.** The seven `major` entries were not marked either. The first begins 253,877 characters into the section.
- **History nobody could use.** 21% of 2.0.0's entries, and 56% of 2.1.0's, describe how a capability that no release had shipped was built.
- **Reach.** The 2.0.0 Release showed a short notice and a link to a 632 KB file that GitHub's page did not render.

**What the maintainer chose.** The analysis weighed three options and recommended the second. The maintainer chose the third, which also leaves out what no adopter sees.

**The maintainer's reason:** "Changelog is mainly for adopters so it should be readable and tell what is important for them. They dont care about internal changes or decision amendments."

**What the release does today** (the release reference, `.pkit/release/README.md`).
- **A changeset** names a component, a segment and a body. A `none` changeset moves no version and gets no line (PRJ-002).
- **`pkit release apply`** writes each body whole as one entry, grouped under Keep a Changelog's six categories, and deletes the changesets it consumes. A run with only `none` changesets deletes them and writes nothing.
- **`pkit release publish-notes`** makes the tagged version's section the GitHub Release's body. A section longer than a Release keeps becomes short notes and a link.
- **Tags.** Only a release that moves the backbone cuts a tag ([PRJ-004](../../../.pkit/decisions/project/PRJ-004-distribution-channel.md)). So no Release shows any other release, and an adopter's own releases, which never move the backbone, cut none.
- **The lint** refuses a `###` heading outside the six categories. Its escape hatch passes its format checks, but not the checks the release itself refuses on.
- **Programs that read the changelog.** Two read a component's releases from entries that open with `**<component> X.Y.Z**`: the short notes, and the lint's check of an explicit capability floor. visual-communication's reader of shipped libraries finds the tag anywhere in the file.
- **Where it is described.** The reference treats the format as the tool's behaviour for every adopter, and an entry's language as project-kit's editorial policy. Yet the reference stays in project-kit, and the CLI reference, which adopters receive, points at it.

**What the records ask of the notes.** The lifecycle record has a release's notes say when a replayed migration may restore a default a project removed ([COR-010](../../../.pkit/decisions/core/COR-010-resource-lifecycle.md)). The lifecycle reference has a change that widens an adapter's settings say so in its changeset. Both are sentences inside an entry today.

**What practice does.** Keep a Changelog, Common Changelog, Kubernetes, Python and Rust share one shape:
- an upgrade layer apart from the list
- one line per change, breaking changes marked and first
- the detail one link away
- a mark for an action that does not depend on the kind of change

## Decision

**A release's notes put first what an adopter must do, give each change one line that links to its kept changeset, and count the changes no adopter sees. `pkit release` builds them for every project that runs it. The words of a line, and the judgment of what an adopter sees, are the project's own policy.**

### 1. A change that needs action carries it, and is listed first

- **The field.** `action:` is an optional field of a changeset. It says who must do what, before the upgrade or after it. An example is "If you wrote your own capability, rename each key `pkit validate` names as unknown."
- **What it means.** An action is something an adopter must do or decide, or else something they rely on stops working or changes under them. A suggestion they may ignore is no action. Whether a change needs one is its author's judgment.
- **Whatever the segment.** An action may ride on a `patch` or a `minor`. A 0.x component may ship a breaking change as a `minor`, and project-kit ships a new refusal as one.
- **What the release refuses,** in `plan`, in `apply` and early in the lint, past its escape hatch:
  - a `major` with no action, except in a component's first release (point 4)
  - an action on a `none` changeset, since a change that asks something of an adopter is one an adopter sees (point 5)
- **The notes the records ask for are actions.** A replay that may restore a default the project removed is one (COR-010). An adapter's settings that allow more are another ([the lifecycle reference, "What the settings merge widens"](../../../.pkit/lifecycle/README.md#what-the-settings-merge-widens)). Each says what to check.
- **In `CHANGELOG.md`:**
  - **The mark.** `**Action required:**` follows the entry's component tag, or opens a backbone entry. The action follows the entry's line.
  - **The order.** Such an entry comes first in its category.
  - **The notice.** A section with any such entry opens with one sentence, such as "Three changes below, marked **Action required:**, ask something of you when you upgrade."

### 2. A digest of what an upgrade brings opens a release's pull request and its GitHub Release

The *digest* is a short account of one or more releases, for someone deciding whether to upgrade.
- **What it holds,** in this order:
  - each action, with its component and version
  - each floor and each upper bound a changeset declared, as the release wrote it
  - each component released for the first time, and each `Security`, `Deprecated` and `Removed` entry
  - each component that moved, from its old version to its new one
- **What it leaves out:** what asks nothing of an adopter, such as the migrations the upgrade runs, and each upper bound the release widens unasked.
- **What it covers.** The digest of a release that cuts a tag covers every release since the previous tag. A release that cuts no tag reaches adopters only with the next tag (PRJ-004), so that tag's digest covers it. Its own digest, before then, covers that release alone.
- **Where it goes:**
  - **`plan` and `apply`** print it, and `plan --json` carries it, in every project.
  - **The GitHub Release.** Where a tag is cut, its body is the digest, then the sections the digest covers where they all fit. Where they do not, it is the digest and a link to each section.
  - **The release pull request** opens with it (point 7 says whose that is).
  - **Not `CHANGELOG.md`,** which holds only point 1's notice above its categories.
- **One home for each computation** ([ADR-057](ADR-057-backbone-engines-and-command-limits.md) point 2):
  - **One reader** turns a released release's folder (point 3) into the value a release is. `plan` gives the same value for the release it computes.
  - **One function** makes the digest from such values. So `plan`, `apply`, the release pull request and the published notes show one digest, read from no network.
  - **The digest itself** is kept in no file, since the values it is made from are kept.

### 3. Each change is one line, and its changeset is kept

- **The line** is the first paragraph of the changeset's body. A body takes the shape of a commit message: the line, a blank line, then any detail. A body with no blank line prints whole.
- **The kept changeset.** The release moves each changeset it consumes, unchanged, into a folder for that release and, inside it, a folder for its component.
- **The release's folder name** is computed by `plan`, so the links are known before `apply` writes:
  - **A release that moves the backbone** takes its new version, such as `2.2.0`.
  - **Any other release** takes the backbone it ran under, its date and its order that day, such as `2.1.0+2026-11-08.1`.
  - So no two releases share a folder. The tag that first carries a release is the first above the backbone its name gives, found without git.
- **The release's record.** Beside its changesets, the release keeps a record of what it wrote: each component's version before and after, and each range it raised or widened. `apply` writes it from the same plan.
- **History.** No release command reads a kept changeset as pending, or rewrites one. Review keeps other edits out, as for any record of history.
- **A run that moves no version** consumes nothing. Its `none` changesets wait for the next release that moves one.
- **The link.** Each line links to its kept changeset by the file's path in the repository. The link then resolves in a clone and on the host at any ref, with no remote and no network.
- **Outside the repository** the section's links are made absolute. A Release makes them absolute at its tag, and a release pull request at its release commit.
- **The pull request's link** stays: a changeset's `pr` still adds its `([#N])`.
- **The component tag opens the entry.** A moved component's entries keep `**<component> X.Y.Z**` first, and no other line carries it. So the programs that read the changelog read it as before.

### 4. A component's first release is one line

A component's *first release* is the release its project marks as the first to ship it to adopters.
- **The mark.** `first_release: true` on one of the component's version-moving changesets. The release does not infer it, since two components were in a release's tree before any section named them.
- **The line.** One tagged line under `Added` names the component and what it is, from its own description. It links to where the component describes itself. It ends with the component's floor and bound sentences, as any entry of it would (PRJ-002 D4).
- **In place of the rest.** That line takes the place of every other line of the component in that release, its count line included. Its changesets are kept like any other.
- **Actions.** None is required, even on a `major`, since most adopters hold no earlier release. One given is listed after the line. It serves whoever held the component before, as the project that incubated a promoted capability does ([COR-031](../../../.pkit/decisions/core/COR-031-capability-origin.md)).
- **What the release refuses,** past the lint's escape hatch: the mark on a `none` changeset. It also refuses the mark on a component that the changelog already records a release of.

### 5. A change no adopter sees is counted, not listed

An *internal change* is one its project judged to be no surface change, declared by a `none` changeset. Each project judges by its own policy, and project-kit's is PRJ-002.
- **One judgment, not two.** A version moves only for a surface change, which an adopter could observe (PRJ-002). So the list holds every change that moves a version, and the count holds the changes that move none.
- **The count.** The release counts each component's `none` changesets in one line, such as "project-management: 23 internal changes". The line links to the component's folder of kept changesets.
- **Which components.** Each component whose `none` changesets the release consumes gets one, whether or not its version moves.
- **Where the lines go.** They close the section under a heading of their own, `### Internal`. The release alone writes it, and the lint accepts it as a section's last heading. No changeset names it as a category.
- **No version.** A count line names no version, so no program takes it for a release.
- **Its line is checked.** The lint checks a `none` changeset's line as it checks any other, as a format check its escape hatch passes. The line is kept, and read where the count links.

### 6. A change an adopter sees stays listed, and one counted by mistake is still found

No check can prove that an adopter sees nothing of a change, so the judgment stays a person's. A default, a review and a second look keep a seen change in the list, and the kept file keeps one counted by mistake.
- **What the release does for every project:**
  - It refuses an action on a `none` changeset (point 1).
  - Each internal change keeps its file and its line, which the count line links to.
- **What project-kit adds** is PRJ-002's, in the words its edits give (Implications). The author judges whether a change is seen, by what it changes that an adopter runs, is asked or promised, or gets. A reviewer checks each `none` from the diff, and doubt goes to a line. A mislabel found later is listed in the next release.

### 7. What is the tool's, and what is project-kit's own

- **The tool's.** Points 1 to 5, and the release's half of point 6, are what `pkit release` does for every project that runs it.
  - **Its description** is a page of its own in the CLI area, which every project receives. It gives the changeset fields, the body's shape, the kept folders and record, the changelog's format and the lint's checks.
  - **A project that cuts no tag,** as an adopter releasing its own components, sees the digest in what `plan` and `apply` print.
- **project-kit's own editorial policy:**
  - **The words.** A line is one plain sentence that says the outcome for the reader, with no record, issue or module id. An action says who must act and what they do. The release reference keeps these rules, and project-kit's review applies them.
  - **The judgments** of whether a change is seen and whether it needs an action, with their review and default, in PRJ-002.
  - **The release pull request,** which project-kit's own workflow opens. It shows the digest, and lists the line of each internal change for whoever merges the release.
- **The lint gains no language check.** Its new checks look only at a field's shape and at how changesets agree. A check of the words would push project-kit's policy on every project. It would also misfire on a line that must name an id adopters see.

## Rationale

**Why an action is marked whatever the segment.** In the sample, every change that asked something of an adopter was a `minor` or a `patch`. A mark tied to `major` would have missed all of them. So Kubernetes marks "action required" apart from the kind of change too. Requiring an action on a `major` keeps the strongest signal from shipping unexplained.

**Why "Action required", not "Breaking".** An action is what the reader must do, and a break is one reason for it. A settings widening, or a replay that may restore a default, asks for a check and breaks nothing. One mark for every action keeps "Breaking" from meaning less.

**Why the release refuses what the lint finds in the fields.** A `major` with no action would ship the strongest signal unexplained. An action on a `none` changeset, or a mark the release cannot honour, would be dropped without a word. So the release refuses each, as it refuses a malformed floor, and the escape hatch passes only the format checks.

**Why the digest lives outside `CHANGELOG.md`.** It is computed from the releases and repeats their most important parts, so inside the file it would add size and a second copy. The GitHub Release and the release pull request are where an adopter deciding on an upgrade, and the maintainer reviewing a release, already look.

**Why a tag's digest covers every release since the previous tag.** Installs and upgrades go by release tags, so a release that cuts no tag reaches adopters with the next one. A digest of the tag's own section alone would leave out what those releases ask of them.

**Why the release keeps a record of what it wrote.** A digest that covers earlier releases needs their versions and ranges. The package files at a tag give only the latest, and a changelog sentence read back would make prose a program's input. The record holds what `apply` wrote, from the plan it wrote it from. It is also what a later decision on showing actions during an upgrade would carry.

**Why the line is a paragraph the author writes.** A first sentence is short, but 45% of 2.0.0's first sentences cite a record or rule id. Some say nothing a reader can use, and a cut at a full stop breaks on "e.g.". So the author writes the line, as a commit's subject, and keeps the detail below it. A body with no blank line printing whole keeps every pending changeset valid.

**Why the changesets are kept in git.** The detail is what someone who writes their own components needs, and what the maintainer traces later. A pull request's description holds it too, but it runs long, can be edited, and lives outside git. A kept changeset is small, renders on the host, is found by a search of a clone, and stays as it was released. Python keeps the same two layers: a short "What's New", and a changelog built from one file per change.

**Why a folder for each component.** A count line then links to that component's changesets alone, and a reader who follows a line finds its neighbours from the same component.

**Why the folder's name carries the backbone.** A date alone collides when two releases fall on one day, and says nothing of which tag carries the release. With the backbone in the name, the digest finds every release a tag covers from the folder names alone, offline.

**Why a line links by path.** The changelog then needs no remote and no host to link, so a project without a GitHub `origin` links as well as one with it. Only notes shown outside the repository need absolute links, and they are made where the ref is known.

**Why a first release is marked, not inferred.** Inference fails where it matters. demo-recording and evidence were in the 1.149.0 tree, though no section named them before 2.0.0. A capability promoted from a project's own into the shipped set would be misread the same way.

**Why "internal" is the `none` judgment.** PRJ-002 moves no version for a change that is no surface change, and that is the change no adopter sees. A second mark beside the segment would add a judgment to every changeset, finer than `none` and more often contested. It would also let a change that moves a version be counted, though the version moves only because an adopter could observe the change. One judgment keeps the review where it already is.

**Why "seen", not "important".** Importance depends on the reader. In the sample, a plain adopter and one who writes their own components judged 6 of 36 entries differently. Two of them asked one of the two to act, and were not worth the other's time.

A mark of importance would hide such an action from the reader it is for. What an adopter sees is a fact a reviewer can check from the diff.

**Why internal changes are counted, not dropped.** Keep a Changelog warns that a changelog which mentions only some changes can be as dangerous as none. A count keeps the list honest about what it leaves out, and its link keeps each left-out change one click away. Rust's "Internal Changes" section keeps such changes apart under a heading of their own, and the count keeps their detail one link away too.

**Why a heading for the count lines.** The lines then stand apart from the last category, where a paragraph after it would read as part of it. The lint must learn the one heading, which it holds to the section's end.

**Why the default leans to a line.** A change listed in error costs a reader one line, and perhaps a `patch` nobody needed. A change an adopter sees, counted as internal, costs them a surprise after the upgrade. The notes exist to prevent that surprise, so doubt goes to the line.

**Why the split between the tool and project-kit.** The release reference already draws it: the format is the tool's for every adopter, and the language is project-kit's layer above it. A project that releases its own capability judges its own changes by its own policy. So the test of what an adopter sees, and the words of a line, stay project-kit's. The tool checks only what any project would accept.

**Why a page in the CLI area.** Every project that runs `pkit release` gets its behaviour, so its description must reach them, and the release reference does not. A page in an area every project already receives adds a file, not an area. So the hold on new core areas does not apply ([ADR-065](ADR-065-upgrade-runs-the-transition.md) point 13).

### Alternatives considered

- **Marking the actions and lifting them into a digest, with the entries left as they are.** Rejected: `CHANGELOG.md` keeps its size, and still spends a fifth to a half of a release on first-release history.
- **That, plus one line per change and kept changesets, with no count.** Not taken: the maintainer chose to leave out what no adopter sees. That option drops a `none` change without a trace, and lists every record amendment its author declared surface.
- **A mark for internal changes, or for unimportant ones, beside the segment.** Rejected: a second judgment, and one that depends on the reader ("Why 'seen', not 'important'").
- **Dropping internal changes altogether, as Common Changelog advises.** Rejected: nothing would show what the list leaves out.
- **A summary field beside the body.** Rejected: every pending changeset would lack it, and the commit-message shape gives the same split with no new field.
- **The body's first sentence, cut by the release.** Rejected: many first sentences cite ids, and a cut at a full stop is unreliable.
- **`**Breaking:**` for every action, as Common Changelog marks a break.** Rejected ("Why 'Action required'").
- **The digest as a heading in `CHANGELOG.md`.** Rejected: it repeats the sections it covers, and Common Changelog forbids it.
- **The digest kept as a file of the release.** Rejected: a second home for what the kept changesets and the release's record hold, which could come to disagree with them.
- **The digest's earlier releases read back from the changelog's sentences.** Rejected ("Why the release keeps a record of what it wrote").
- **One detail file a release, as changie's own batch step writes.** Rejected: the release would rewrite the author's files rather than keep them.
- **A folder named by the changelog's heading.** Rejected: two releases on one day would share it ("Why the folder's name carries the backbone").
- **The count lines as a paragraph after the last category.** Rejected ("Why a heading for the count lines").
- **Links to each pull request, looked up through the host's API.** Rejected: a network call for each changeset in `plan` and `apply`, which are offline today. It works on one host only, and overrides an author's `pr`.
- **A link to the issue a body names, where it gives no `pr`.** Not taken: the kept changeset is one link away and names its issue.
- **A first release inferred from the changelog or the tags.** Rejected: it fails for components that shipped before a section named them.
- **Language checks in the shipped lint.** Rejected (point 7).
- **Propagating the release reference whole.** Rejected: it holds project-kit's own flow and workflows, and no core area may be added before #1600 (ADR-065 point 13).
- **A changelog per component.** Rejected: `pkit upgrade` moves every component at once, so one reading would split into eight.

## Implications

- **Edits to PRJ-002,** made in this change once this record is accepted ([COR-066](../../../.pkit/decisions/core/COR-066-accepted-before-landing.md) point 5). PRJ-002 then holds the test in its own words:
  - **Its list of surface changes** names, in place of any new COR, a new principle of an accepted COR. It is one adopters must follow once it syncs.
  - **Its paragraph on non-surface changes** says such a change is one no adopter sees:
    - It changes nothing an adopter runs, nothing a shipped rule or reference asks of them or promises them, and nothing they get.
    - Wording that keeps the meaning is no change, in a record, a page or a message.
    - The paragraph keeps its present items, and says the release counts such changes and lists none.
  - **Its paragraph on decision-touching pull requests** takes the same test. A record is self-executing when an adopter must do or get something different once it syncs.
    - A record's wording, or an amendment that leaves what it asks of an adopter, declares `none`.
    - A design-ahead record is counted among its component's internal changes, never listed.
    - A self-executing record's line says what changes for the adopter, not which record changed.
  - **D2** says who judges and how it is checked:
    - The author declares the segment and any action.
    - The reviewer who checks the pull request's changesets judges each `none` from the diff.
    - A change its author is unsure of is a surface change.
    - A mislabel found after a release is listed by a changeset in the next one.
  - **Its Implications on capability promotion** say the promotion's changeset carries the first-release mark. It gives an action where the project that incubated the capability must do something.
  - **Its paragraph "Policy, not mechanics"** points at this record for the shape of the notes.
- **An edit to PRJ-004,** made with them. Its Implications say the Release body is the digest and the sections it covers, or the digest and links to them. It is still never an artifact.
- **No edit to COR-010.** The note on a replay becomes an action (point 1), and COR-010 leaves the form of the notes open.
- **Until Task 4 lands,** PRJ-002's reviewer duty binds before any reviewer's instructions name it. Reviewers of surface declarations read PRJ-002 meanwhile.
- **The Tasks that carry it out,** to file once this record is accepted. The first three share the release step's code, so they are built one after another, in this order. Each is a separate review of one concern: the fields, the changelog and kept files, then the digest.
  1. **Changesets carry an action and a first-release mark, and the changelog shows the action.**
     - The two fields, the release's refusals on them, the mark, the order and the notice of point 1. changie's prompts, a body of more than one paragraph among them.
     - The CLI area's page for the tool's format (point 7), with the CLI reference's rows and the lint's messages pointing at it. The release reference's sections on the fields, the lint, the replay and where the format departs from its sources.
     - The lifecycle reference's note on the settings merge. The software analysis: UC-003 and its variant 3a, JRN-008 and JRN-009, and UC-008's precondition on the replay.
     - A backbone `minor`, whose own action asks a project with a pending `major` to give it one.
  2. **The release keeps each changeset, writes one line per change, and counts internal changes.**
     - Points 3 to 5: the line and the lint's check of it, the kept folders and record, the first-release line, the count and its heading. A run that moves no version consumes nothing. The folders' naming rule has one home, beside the pending folder's.
     - The changeset guard reads a release's diff without rename detection. It pairs each kept file with a pending one of the same content, and a move out of the pending folder declares nothing.
     - The CLI area's page, the CLI reference and the release reference's sections on changesets, grouping and fields. The software analysis: UC-008 variant 1b, UC-009, and the domain-model view of changes and releases.
     - A backbone `minor`. Its action says a project's consumed changesets now stay in its tree, and that the project may leave their folder out of anchoring.
  3. **The release writes a digest for its pull request and its GitHub Release.**
     - Point 2's reader and function, printed by `plan` and `apply` and carried in `plan --json`. `pkit release publish-notes` publishes it with the sections it covers, their links absolute at the tag.
     - project-kit's release workflow commits before it writes the pull request's body, opens it with the digest, and lists each internal change's line from `plan --json`. A body too long for its host links the list, as it links a long section.
     - The release reference's sections on release notes and the automated flow. The CLI reference's `plan` and `publish-notes` rows and section. The software analysis: UC-008 steps 6 and 13, and its variants 13a and 13b.
     - A backbone `minor`.
  4. **project-kit writes and reviews its changesets for the new notes.** It can land once Task 1 has.
     - The release reference's "Language" section gives the line, the action and the detail below. The changesets folder's README, `CLAUDE.md`'s versioning line and the pull-request template say the same.
     - project-kit's conventions, which its reviewers read, have them check each `none` against PRJ-002's test, and each line and action against the language rules.
     - No changeset, since nothing an adopter sees moves.
- **Each Task mends project-kit's pending changesets in its own change,** so its own checks pass. Task 1 gives each pending `major` an action, and Task 2 gives each pending changeset a line the lint accepts.
- **No migration.** No tree the methodology ships is renamed or removed, and no schema's version or command's signature changes. `.changes/` is the project's own, and a changeset with no blank line prints as before. `plan --json` only gains keys. Each Task confirms it with `pkit migrations check-diff`.
- **For a project that runs `pkit release`:** its consumed changesets and each release's record are kept in its tree. Its changelog gains the marks, the lines and the counts, and the release refuses a `major` with no action. Tasks 1 to 3 each say so in their changeset's action.
- **Anchoring of the kept folders.** project-kit already leaves its changesets' folder out of anchoring, as history ([ADR-075](ADR-075-generated-operational-rules.md) point 8). The CLI area's page tells another project to do the same.
- **Left open:**
  - Whether `pkit upgrade`, and its dry run, show the actions of each release it crosses. That is a decision of its own, which would read the kept changesets and records, and say how they reach the bundle.
  - Releasing more often, which the analysis recommends beside any option.
- **Stands on these records, all accepted:** COR-010, COR-025, COR-031, COR-066, PRJ-002, PRJ-004, ADR-057, ADR-065 and ADR-075.
