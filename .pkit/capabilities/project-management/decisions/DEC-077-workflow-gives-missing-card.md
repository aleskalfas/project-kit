---
id: DEC-077
title: The post-check workflow gives a card missing at filing through the board sync
status: proposed
date: 2026-11-16
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** an issue filed outside the capability's commands, or whose add to the board failed at filing, opens with no card on the configured board. The post-check workflow, which a project copies from the capability's template, checks each issue opened and reports the missing card, yet adds none, even where the project turned its remediation on: that remediation runs only on a finding that blocks, and a missing card never blocks. This record has the workflow give the card at filing, where the project turned its remediation on and gave it a credential the board answers. The workflow makes no add of its own. It runs the board sync for that one issue, so the sync's rules hold in each kind of project. Where the board's Status is the state's projection, the card gets the Status the issue's state gives. Where the state degrades, it gets none. Where the board holds the state, it gets none, and is added only where the project turned on the sync's switch for runs with no terminal, the consent to the board's own automation setting a Status that every command would read as the issue's position. The workflow's comment on the issue says what the sync did. The workflow adds no card on an edit or a reopening, or for any other finding.

## Context

**The terms.**

- *The configured board*, *the board holds the state*, *the Status is the state's projection*, *the state degrades*, *the board sync*, *a missing card*, *a run with no terminal* and *the maintainer*: as [project-management:DEC-072-sync-gives-missing-cards] defines them. *The project's switch* is the setting DEC-072 point 3 decides, which lets the board sync's runs with no terminal add cards where the board holds the state.
- *The post-check workflow* is the workflow [project-management:DEC-019-mandatory-issue-state] offers as a template. A project copies it into its own repository, and the host runs it on each issue opened, edited or reopened, with no terminal and nobody watching. *Its remediation* is the toggle DEC-019 gives it, off as the template ships, which the project turns on in its own copy to have the workflow mend what it finds.
- *The membership check* is the check, among an issue's validation, that the issue has its card on the configured board. It finds a card missing only where the same request shows the board answered, and otherwise reports that the board did not answer ([pkit:ADR-096] point 5).
- *At filing* means in the workflow's run on the event of the issue's opening.

**What the records say.**

- **Every issue belongs on the configured board from its filing** (DEC-019). The workflow is the layer that catches an issue filed outside the capability's commands ([project-management:DEC-020-methodology-as-executable-commands], "Three-layer defence model"). DEC-019 has the workflow, where its remediation is on, invoke the analogous mutation on a finding that rejects the issue at filing, and only comment on drift on an existing issue.
- **As the template ships,** the membership check reports a missing card at the drift severity in every run, at filing too, so it never blocks. The remediation runs only on a finding that blocks, so it never adds the missing card. It adds a card, by an add of the template's own, whenever another finding blocks (ADR-096, its Implications on the workflow).
- **The workflow's own token reaches no board,** so the template has a setting for a credential the board answers, unset as it ships. Whether a copy remediates, on an issue off the board or on one the board did not answer for, ADR-096 leaves to this capability. Where one does, a card it adds is a witness for the repository's later reads (ADR-096 point 1, and its Implications on the workflow).
- **The board sync** gives every missing card in every project with a board, and writes a Status only where the Status is the state's projection. Where the board holds the state, it adds cards only in a run at a terminal or with the project's switch on, and reads each card it added back. A run can be limited to the issues it names (DEC-072 points 1 to 3).
- **[project-management:DEC-069-when-fixers-start] point 4** gives a switch of the same form for runs nobody watches of another kind: a fixer, an agent, started in its unconfined form.

**Where the question came from.** DEC-072 left it to a record of its own ("Not decided here"), in [project-kit#3271](https://github.com/aleskalfas/project-kit/issues/3271).

## Decision

**At filing, where the project turned the post-check workflow's remediation on and gave it a credential the board answers, the workflow gives an issue the membership check finds without its card, or for which the board did not answer, its card by running the board sync for that issue alone. What the sync writes, and when it may add a card with no terminal, then hold for the workflow as for every run of the sync. The workflow makes no add of its own, adds no card on any other event or for any other finding, and says on the issue what the sync did.**

### 1. At filing, the workflow runs the board sync for the issue

- **When.** In its run at the issue's opening, where the membership check finds that the issue has no card on the configured board, or that the board did not answer for it, whatever severity the finding takes.
- **How.** It runs the board sync, named for that issue alone, with the option that skips the question. The sync decides from its own whole walk of the board whether the issue has a card (ADR-096 point 2), so the workflow decides nothing of the card itself.
- **Only where the project asked.** Only where the project turned the remediation on in its copy, and only under the credential the project set for the board. With none set, the workflow runs no sync, and its comment says that it adds a card only under a credential the board answers.
- **At filing alone.** On an edit or a reopening, the workflow adds no card, and reports a missing card as the membership check does, naming the sync. No other finding, one that blocks among them, leads it to add a card.

### 2. What the card gets follows what the sync does in each kind of project

- **Where the Status is the state's projection,** the sync adds the card and writes the Status the issue's state gives, on the option that skips the question alone (DEC-072 point 2).
- **Where the state degrades,** it adds the card and writes no Status, on that option alone.
- **Where the board holds the state,** it adds the card only where the project's switch is on, writes no Status, and reads the card back (DEC-072 point 3). With the switch off, it adds nothing, and refuses as it refuses a run it cannot ask.
- **Where no board is configured,** the membership check makes no call to a board and finds nothing, so the workflow runs no sync.

### 3. The consent where nobody watches

- **Where the sync guesses nothing,** where the Status is the state's projection or the state degrades, the consent is the project's own: the remediation it turned on in its copy, and the credential it set. These are the writes the sync makes in any run with no terminal on the option that skips the question (DEC-072 point 3).
- **Where the board holds the state,** the consent is the project's switch as well, whose consent covers each run of the sync the workflow makes at filing (Implications). The workflow has no switch of its own, and DEC-069's switch is no consent to it.
- **A switch turned on before** counts for the workflow's runs too. The workflow adds under it only where the project also turned the remediation on, in a copy of the template whose words say that it adds under the switch, so that act brings the workflow's runs under the switch.
- **As the template ships,** the remediation is off and no credential is set. A project's copy is its own (DEC-019), so a copy made earlier keeps its own steps until the project copies the template again.

### 4. The workflow says on the issue what the sync did

- **Its comment** on the issue carries what the sync reported for the issue: the card added, or not added, in the sync's words. Where the board holds the state, that is what the read-back found and that the card's Status is set on the board, or the refusal, with the switch it needs and the command to run at a terminal.
- **A card not added fails nothing.** The issue's check ends as the validation's findings make it, whatever the sync's exit code.

### 5. What this leaves open

- **Filing's own add in flight.** The capability's filing command creates the issue before it adds the card, so the workflow can read the board before that add, and both then add. That the host answers an add of an issue already on the board with the card it has was not measured (DEC-072, Context). Where it does not, the filing can report a failed add for an issue the workflow gave its card. Where the board holds the state, the read-back can name the Status filing wrote as one the sync did not write.
- **An issue moved into the repository.** Whether the host reports an issue transferred into the repository as opened was not measured. Where it does, that run counts as at filing, and the sync guesses nothing of the issue, as of any other.
- **Anyone who can open an issue starts the run,** so an issue anyone opens gets its card, as DEC-019 puts every issue on the board. Where the board holds the state and the switch is on, the board's automation may give that card a Status every command reads as the issue's position, which the comment then names.
- **The membership gate.** Where the project's member list closes the gate, the gate meets the sync's run as it meets the check's ([project-kit#3290](https://github.com/aleskalfas/project-kit/issues/3290)), and this record decides nothing of how either passes.
- **The cost.** Each filing whose card is missing costs the sync's whole walk of the board, and its read of every open issue.

### What this refines, and what stands

- **Refined in DEC-019:** the mutation its workflow invokes for an issue that opens with no card on the configured board, which is the board sync, run for that issue on the membership check's finding at filing, whatever its severity (Implications).
- **Refined in DEC-072 point 3:** the switch's consent, which covers each run of the sync the post-check workflow makes at filing, and where that run's read-back names reach (Implications).
- **Stands:** DEC-019's severities, DEC-069, ADR-096, and DEC-072 save those two bullets of its point 3.
- **Not decided here:** whether a missing card at filing fails the issue's check, which DEC-019's schema rejects and the check as shipped warns of; and whatever else the remediation mends.

## Rationale

**Why the workflow gives the card at filing.** DEC-019 puts every issue on the configured board from its filing, and the workflow is the layer that catches the filings the capability's commands do not make (DEC-020). As the template ships, its remediation never reaches a missing card. At filing, a missing card is nobody's choice: the issue was filed outside the capability's commands, or filing's add failed. A card given then also gives a repository with none of its issues on the board a witness for its later reads (ADR-096 point 1).

**Why through the board sync.** DEC-072 keeps one command that gives missing cards, and rejects a second, since each would decide which issue has a card, and each would need to meet ADR-096's tests. The sync already writes what each kind of project asks, holds the consent where the board holds the state, reads back what it added, and limits a run to the issues it names. An add of the template's own would have to restate each of those rules, or break them: a card with no Status where the projection wants one, or an add with no consent where the board holds the state. It would also reach past the command that owns the write, which DEC-020's layer discipline warns against. Limited to the issue, the run writes nothing on another issue with nobody watching, and two runs for issues opened together each write only their own.

**Why where the board did not answer too.** The membership check reads the issue's own cards, and finds a card absent only where it sees another issue's card from the same repository as a witness (ADR-096 point 1). Where the repository has no card on the board yet, as with its first issues on a shared board, it reports that the board did not answer. The sync decides from a whole walk of the board, which reads the board itself and needs no witness (ADR-096 points 1 and 2), so it gives the card there. Where the board truly did not answer, the sync fails and says so.

**Why only under the credential the project set.** The workflow's own token reaches no board (ADR-096), so a sync under it would fail on every filing.

**Why at filing alone.** On an edit or a reopening, a missing card may be a person's act, a card removed, or an older failure, and the workflow cannot tell which. DEC-019 keeps such drift for a person to mend, and the sync is the command a person runs for it (DEC-072, "Why only when someone runs it"). An edit is no act on the board, and a card added again on each edit would undo a person's removal with nobody watching.

**Why no other finding.** The add mends one finding, the missing card. A finding that blocks for another reason, such as a missing label, says nothing of the board, and a card added for it mends nothing that finding names.

**Why the project's remediation is the consent where the sync guesses nothing.** DEC-072 lets any run with no terminal make these writes on the option that skips the question, since none of them sets a Status a command reads as a position it did not know. The remediation is a more deliberate act than that option: a setting in the project's own copy, which the host reads from the default branch for each issue's events, and which only a change of the project's turns on. It needs no hold at the merge, as that option has none.

**Why the project's switch where the board holds the state, and no switch of the workflow's own.** The risk there is the one DEC-072 weighs: the board's automation setting a Status on a card a run with no terminal adds, which every command then reads as the issue's position. It is the same whoever starts the run, so one consent covers it, and a second switch for it could disagree with the first. The workflow's runs keep every guard the sync's other runs keep, and its comment puts what the read-back found on the issue, where a person meets it, which another run with no terminal leaves in its output alone. DEC-069's switch consents to something else: a fixer's unconfined run, which may do whatever its settings let a session do. It says nothing of a board's automation, so it carries no consent here, and the project's switch carries none to a fixer.

**Why the comment carries the sync's words.** The workflow already comments on an issue whose check found anything, and a missing card is such a finding, so the comment adds no write the run would not make. Without the sync's words, the comment would report an issue off the board that the workflow then gave its card.

**Why a card not added fails nothing.** A missing card is drift, which never blocks as the template ships, and an add the board did not make, or the switch kept back, is no fault of the issue's, as a board that did not answer is none of the issue's under the membership check (ADR-096 point 5).

### Alternatives considered

- **Keep the workflow reporting only.** Not taken. Where the Status is the state's projection or the state degrades, the add guesses nothing, and is the write the sync makes in any run with no terminal. A project that turned the remediation on asked for it, and a card missing at filing is what DEC-019's layer is for. Where the board holds the state, the switch keeps the guess behind the person's consent. It is the choice to make where the maintainer would keep every write to the board out of the runs anyone who can open an issue starts.
- **Keep the template's own add, and run it on the membership check's finding.** The workflow would make one add and no walk of the board. Not taken, as "Why through the board sync" says: a second command that gives cards, with the sync's rules restated in the template, or broken there.
- **At filing, where the board holds the state, add the card and write the first Status filing would: Backlog for an issue with a milestone, Todo otherwise.** At filing the issue was just opened, as filing knows of the issue it files, so the Status would not be the guess DEC-072 refuses where a run cannot tell how an issue lost its card, and the issue would be placed with no person. Not taken. The event does not prove the issue new: whether a transferred issue arrives as opened was not measured, and a person may set a Status by hand between the workflow's read and its write, which the write would erase. It makes the workflow a third writer of the state's source, beside a move and filing, from a state it infers. And it needs a write the sync refuses where the board holds the state (DEC-072 point 2), so either DEC-072 is overturned there, or the workflow writes the Status outside the sync. It is the choice to make where the maintainer would place an issue filed outside the capability with no person, at that cost.
- **A switch of the workflow's own, in the form of DEC-069's, held at each merge.** Not taken. Where the sync guesses nothing, no run with no terminal is asked a consent beyond the option that skips the question, and the project's remediation is more than that. Where the board holds the state, the consent is the one the project's switch already gives, so a second switch would hold one consent in two places.
- **DEC-069's switch as the consent.** Not taken, as "Why the project's switch" says: it consents to a fixer's unconfined runs, not to a board's automation.
- **Give the card on every event the workflow runs on, edits and reopenings too.** An issue whose run at filing failed would get its card at its next edit. Not taken, as "Why at filing alone" says. The sync, run by a person, gives such a card.
- **Give the card only where the membership check finds it missing, not where the board did not answer.** No walk would be made where the board did not answer. Not taken, as "Why where the board did not answer too" says: a repository's first issues on a shared board would get no card, though only a card gives their later reads a witness.
- **Run the sync for the whole board at filing.** Every missing card would be given as issues are opened. Not taken: it writes on issues the event is not about, with nobody watching, and the sync is the command a person runs to bring the whole board level (DEC-072).
- **Fail the issue's check where the card is not added.** Not taken, as "Why a card not added fails nothing" says.

## Implications

- **Edits to accepted records,** made in this change once this record is accepted. Accepting this record accepts them (COR-066 point 5):
  - **DEC-019's "The post-check workflow template,"** its third bullet, reads ``On `hard-reject` severity at filing, posts a comment + a status check failure; in `auto-remediate` mode (adopter-configured), invokes the analogous mutation to fix the issue.``, in place of ``On `hard-reject` severity at filing, posts a comment + a status check failure; in `auto-remediate` mode (adopter-configured), invokes the analogous mutation (`gh project item-add`, etc.) to fix the issue.`` A bullet after it reads ``For an issue that opens with no card on the configured board, in `auto-remediate` mode, the template runs the board sync for that issue alone, on the membership check's finding at filing, whatever its severity, and makes no add of its own. The sync adds the card only where it adds one in a run with no terminal (refinement per [project-management:DEC-077-workflow-gives-missing-card]).``
  - **DEC-019's Implications,** the bullet that opens "Adopters opt into auto-remediation by toggle", ends ``With `AUTO_REMEDIATE: true`, the template also invokes the relevant mutation, which for an issue that opens with no card on the configured board is the board sync, run for that issue (refinement per [project-management:DEC-077-workflow-gives-missing-card]).``, in place of ``With `AUTO_REMEDIATE: true`, the template also invokes the relevant `gh` mutation.``
  - **DEC-072 point 3,** the switch's bullet that opens "turning it on is the consent", reads `turning it on is the consent to the board's own automation setting a Status on each card a run with no terminal adds, which every command then reads as the issue's position, named only in that run's output. It consents for every session that runs the sync in the project, a person's or an agent's, and for each run of the sync the post-check workflow makes at an issue's filing, where the project turned the workflow's remediation on (refinement per [project-management:DEC-077-workflow-gives-missing-card]);`, in place of the same text ending `It consents for every session that runs the sync in the project, a person's or an agent's;`.
  - **DEC-072 point 3,** the bullet that opens "the read-back's names wait nowhere", reads `the read-back's names wait nowhere the sync keeps them, by a choice of this record's: where DEC-069 has a run nobody watches leave its reports where the person meets them (its point 4), the names here stay in the run's output alone, which a run the post-check workflow makes carries into its comment on the issue (refinement per [project-management:DEC-077-workflow-gives-missing-card]). Turning the switch on consents to that too;`, in place of `the read-back's names wait nowhere, by a choice of this record's: where DEC-069 has a run nobody watches leave its reports where the person meets them (its point 4), the names here stay in the run's output alone. Turning the switch on consents to that too;`.
  - **DEC-072's "Not decided here,"** its first bullet reads `**Whether the post-check workflow adds a missing card,** which ADR-096 leaves to this capability, is decided by [project-management:DEC-077-workflow-gives-missing-card]: at an issue's filing, through this sync, run for that issue.`, in place of the bullet that opens "Whether the post-check workflow adds a missing card on drift". This edit and the next change nothing DEC-072 decides.
  - **DEC-072's rejected alternative "Have the membership check add the card,"** its last sentence reads `Whether the workflow adds a missing card is decided by [project-management:DEC-077-workflow-gives-missing-card].`, in place of `Whether the workflow should add a missing card is left open above.`
- **The build,** in a Task of its own, changes these documents:
  - **The post-check workflow's template.** Its remediation runs the board sync for the issue at filing, on either finding of the membership check, only with the remediation on and under the credential the project set, and never on another event or for another finding (point 1). Its comment carries what the sync reported (point 4). Its account of the remediation toggle says what points 1 to 4 decide. The template's tests hold each of these, and that a card not added fails nothing.
  - **The project-management README:** "The post-check workflow's credential", which says what the remediation does at filing in each kind of project (point 2), and "Bringing a whole board level", where it says whom the switch consents for.
  - **The switch's words at each merge** that turns it on (DEC-072 point 3, "held at every merge"), which name the workflow's runs at filing among those the switch consents for, with the tests that hold those words.
  - **DEC-070's Context, "The gap between them,"** where it says what the workflow as the capability ships it does: corrected as a fact once the build ships, which changes nothing DEC-070 decides.
- **The build checks a premise** before it relies on point 2 where the board holds the state: that the workflow's job can read the switch, which counts only as the shared remote's copy of the default branch holds it, read through the backbone (DEC-072 point 3). Where the job cannot make that read, the switch reads as off there, so the workflow adds no card where the board holds the state, and the template's words say so.
- **ADR-096 stands** with no edit: it leaves the remediation to this capability, which this record decides.
- **A surface change** for the capability, once built. A project that copies the template again, with its remediation on, gets a card at filing where it got none, and no card for a finding that blocks for another reason. The build declares it, by the versioning of the project that builds the capability. It owes no migration: a project's copy of the workflow is its own, and the remediation is off as the template ships.
