---
id: DEC-071
title: Filing refuses a board other than the configured one in every project
status: proposed
date: 2026-11-15
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** every issue belongs on the configured board, and every command but filing reads and writes that board alone. Where the board holds the state, [project-management:DEC-070-filing-another-board] already refuses a filing whose board option names another board. This record refuses it in every other project with a board too. By a choice of its own, it also refuses a board option in a project with no board, where the option silently does nothing. The refusal comes before anything is written or asked, and names the way out: leave the option out, and add a card to the other board afterwards by the host's own means. A filing that names the configured board's own number goes on. The record rests on what the option costs, not on an absence of callers: no project with a board was read, so whether anyone passes the option is unknown, and the refusal may break a call.

## Context

**The terms.**

- *The configured board*, *the board holds the state* and *a filing that names another board* are as DEC-070 defines them.
- *The override* is the one [project-management:DEC-019-mandatory-issue-state] gives a filing in "Multi-board adopters at v1": a board option that names a board in place of the configured one, for that filing alone. DEC-019's rules on the board apply only where a board is configured (its "Substrate scope"), the override among them.
- *The Status is the state's projection* where a board is configured and the state is carried off it, and *the state degrades* where a present substrate map leaves the state out or marks it unsupported, so that the capability writes no Status ([project-management:DEC-062-axes-chosen-in-the-map] point 5).
- *The board sync* is the command that brings the board's Status in line with the issues' states (DEC-062 point 5).

**What the records say.**

- **DEC-019 puts every issue on the configured board from its filing,** wherever a board is configured. It rejects at filing an issue with no card there, and calls a missing card on an existing issue drift, at warning severity. Its override is the one exception, and it defers several boards for one project until one is asked for.
- **DEC-070 refuses the override where the board holds the state,** because the issue's position would be one no command reads. It leaves the override in every other project with a board, for three reasons: there the override leaves no issue unworkable, removing it would change every call that uses it, and that change wants evidence of the option's use, left to [project-kit#3241](https://github.com/aleskalfas/project-kit/issues/3241).
- **Every other command reads and writes the configured board alone.** A move writes the Status of the issue's card there. The board sync reads every card there. The membership check reads the issue's card there, once [pkit:ADR-096] point 5 is built.

**What the override costs where a board is configured and does not hold the state.**

- **An issue the capability's own check reports.** Under ADR-096 point 5, the membership check reads the issue's card on the configured board, and reports an issue with none as the drift DEC-019 names. The capability's own filing then makes, on purpose, an issue its own check reports.
- **A card nothing keeps.** Where the Status is the state's projection, filing writes the first Status on the named board's card, and no move updates it, so the card keeps a state the issue left at its first move. Where the state degrades, filing writes no Status, so the named board's card is the card a host command run after filing would give.
- **A missing card until someone repairs it.** Where the Status is the state's projection, the board sync gives the issue its card on the configured board, once someone runs it. [project-management:DEC-072-sync-gives-missing-cards] has the sync give it in every project with a board.
- **Board fields written against the wrong board.** The write that seeds a board field's default pairs the named board's card with the configured board's field once ADR-096 is built, and with the configured board's project before then. Either way it fails, and is passed over ([project-kit#3240](https://github.com/aleskalfas/project-kit/issues/3240)).
- **A filing that does less than it was asked, or is refused for the wrong cause.** Before ADR-096 is built, an option naming 0 adds the issue to no board, after the filing announced the add, with no warning. Once it is built, filing reads the named board first, by its number, so an option naming 0 finds no board. The filing is then refused as one whose board did not answer, with the code of a broken tool, for a mistake in its options. That lasts until the check of a number below 1 runs before the read (Implications).

**In a project with no board.** The filing adds the issue to no board, and a board option changes nothing it does: the option is read, and dropped with no word. Nothing is left wrong, since DEC-019's rules on the board do not apply there. The cost is a filing that does less than it was asked, silently.

**What was read of the option's use, and what it shows.**

- **In this capability:** none of its commands, skills, agents, tests or workflow templates passes the option, and none has since the repository's first commit, where the option already stood. The filing procedure lists it in the command's synopsis, and says nothing of when to use it.
- **In the tracker:** no issue reports using it, or asks for it. The defect of project-kit#3240, which reaches every such filing in a project whose hooks seed a board field, was found in the capability's own work, not reported by a caller.
- **In the projects that adopt the capability:** no project with a board was read. The one adopting project whose files were read configures no board, nor does the project that builds the capability. The capability keeps no record of a filing's options: the comment it posts on each new issue records the versions it was filed under and the date ([project-management:DEC-041-version-provenance-stamp]).
- **What it shows:** nothing of whether anyone passes the option. Each finding above is what one would see whether callers exist or not, since no project the override could serve was read, and a caller it serves has nothing to report. DEC-019 kept the override as its interim for projects with several boards, so that no one asks for several boards may mean the interim works. This record therefore rests on the costs above alone.

**How a person could learn more,** before accepting this record or after it. Only the last way is in the maintainer's own hands, and the others need the adopting projects.

- ask the projects that adopt the capability;
- in each adopting project with a board, list its open issues that have a card on another board and none on the configured one. Each use of the option leaves that trace until someone adds the missing card, and a card moved by hand leaves it too, so the count bounds the use from above;
- search an adopting project's scripts, CI workflows and agent definitions for the option;
- ship a warning on each use first, naming how to report it upstream, and decide after a release (an alternative below).

## Decision

**Wherever a board is configured, the filing command refuses a filing that names a board other than the configured one, as DEC-070 refuses it where the board holds the state: before it writes anything or asks the person anything. Where no board is configured, it refuses a board option the same way. A filing that names the configured board's own number goes on. DEC-019's override stands in no project.**

### 1. Wherever a board is configured, the refusal reaches every project

- **Where.** Where the board holds the state, as DEC-070 has it. Where the Status is the state's projection, and where the state degrades, by this record.
- **What counts as another board, when it comes, and its code:** as DEC-070 has them.

### 2. Where no board is configured, the filing refuses a board option

- **What.** A board option, whatever number it names, since the project gives no board to compare it with. The filing refuses it as point 1 refuses another board: before it writes anything or asks anything, in a dry run too, with the same code.
- **A choice of its own.** DEC-019's override never reached such a project, so this point overturns nothing. Its alternative, a warning with the filing going on, is weighed below.

### 3. What the refusal says

Each message gives the reason that holds in the project's own case, and no other.

- **Where the board holds the state:** DEC-070's message.
- **Where a board is configured and does not hold the state:** that every issue belongs on the configured board, which every command reads and writes, so an issue filed onto the named board would have no card where every command looks for one. It names DEC-070's two ways out: leave the option out, to file onto the configured board, or, where the issue should be on the other board too, add a card there after filing by the host's own means, which the message names. That card is the project's own: no command reads or writes it.
- **Where the configuration declares a board and gives no number:** that it gives no board number, so there is no configured board to file onto, and that this is the fault to mend. It says that the board holds the state only where the map binds the state to the board, as DEC-070's message does there.
- **Where no board is configured:** that the project configures none, so a filing adds the issue to no board. The way out is to leave the option out, and, where the issue should be on the named board, to add a card there after filing by the host's own means.

### What this overturns, and what stands

- **Overturned in DEC-019:** the override, "per-invocation override at filing time via `create-issue.py --board=<N>`" in "Multi-board adopters at v1", in every project with a board where DEC-070 left it. Between them, DEC-070 and this record leave it standing nowhere. A project with no board was never within it.
- **Overturned in DEC-070:** that the override stands where the state is carried off the board or degrades. Its plain terms' last sentence says so, as do the Decision's last sentence, its "Where" bullet's last sentence, the first item of its "Stands in DEC-019", and its test that the option is not refused there. So does the conclusion that its Rationale "Why only where the board holds the state" and its rejected alternative "Refuse wherever the map binds any axis to the board" draw: that a filing naming another board goes on where the board does not hold the state.
- **Stands in DEC-070:**
  - the refusal where the board holds the state, with what counts as another board, when it comes, what it says and its code;
  - the premises of that Rationale and that alternative. Where the board does not hold the state, the override leaves no issue unworkable. And a refusal for a missing value of priority or workstream would settle ADR-053's open question for one route alone. This record refuses there on other grounds, membership and the costs under the Context, as its Rationale's "What it answers of DEC-070's reasons for stopping short" says;
  - its alternative "Remove the override in every project", as DEC-070's account of why it left that question open. This record decides the question, and the same part of its Rationale answers each of those reasons.
- **Corrected in DEC-070,** as a fact is: its Context's account of the post-check workflow, which adds no missing card (Implications).
- **Stands in DEC-019:** every issue's card on the configured board from filing, the severities of an issue without one, and the single default board, with several boards for one project deferred.
- **Refined in ADR-096:** the room it makes for the override, which no filing reaches once the refusal is built (Implications).

## Rationale

**Why refuse wherever a board is configured.**

- **The override makes the issue DEC-019 rejects.** At every other filing, an issue with no card on the configured board is a reject. The override is the one route by which the capability's own command makes that issue, on purpose, and once ADR-096 point 5 is built, the capability's own check reports it.
- **What the override gives, a host command gives, or it goes stale.** Nothing after filing reads or writes the named board. Where the state degrades, the override's card there carries no Status, as a card a host command adds after filing carries none. Where the Status is the state's projection, it carries a first Status as well, which goes stale at the issue's first move.
- **A refusal costs a caller little, and says so at once.** Nothing is written before it, so nothing is left to undo, and its message names the way out. A project that needs an issue on two boards at filing then has a reason to say so, and a later record can design several boards for one project, as DEC-019 defers it until one is asked for.

**What it answers of DEC-070's reasons for stopping short.** DEC-070 refused only where the board holds the state, since elsewhere the issue stays workable, and since refusing wherever an axis is bound to the board would settle, for one route alone, the board read-path contract's open question of whether a value of priority or workstream must be present ([pkit:ADR-053], "Boundaries").

- **Workability.** This record grants it: where the board does not hold the state, the override leaves no issue unworkable. It refuses for membership and for the costs above, none of which makes an issue unworkable, and it breaks a call for them knowingly.
- **ADR-053's open question.** This record's ground is membership, which is the board flag's question and never carriage's (ADR-096 point 5). It refuses alike in a project that binds no axis to its board, so it says nothing of whether a value of priority or workstream must be present.
- **Every call that uses the option changes.** It does, and the build's changeset declares the break.
- **Evidence.** It was gathered as far as the readable projects allow, and shows nothing of callers either way. So the record rests on the costs, which the capability's own records and code show.

**Why it holds where the sync gives the missing card.** Wherever the board sync gives the missing card on the configured board, the missing card lasts only until a sync. It does so where the Status is the state's projection, and DEC-072 has it do so in every project with a board. Each ground above stands: the filing still makes, on purpose, an issue DEC-019 rejects and its own check reports until a sync, and the named board's card still gives no more than a host command gives, or a Status that goes stale. An issue filed onto another board also gets its card on the configured board at the next sync, so a caller who meant "in place of" gets "as well as" all the same.

**What a caller who meant "in place of" loses.** A project that files a team's issues onto that team's board alone, and keeps them off the configured board, can no longer do so through filing. The way out gives "as well as", and an issue kept off the configured board is the drift DEC-019 names. That use was drift by DEC-019's own rule, made on purpose, and where the Status is the state's projection, the board sync already gives such an issue its card on the configured board. A project that needs it has the reason for a record on several boards for one project.

**Why a project with no board too.** The option does nothing there: it is read, and dropped with no word. So a refusal takes from a caller only a clean exit, and leaves nothing wrong behind. It keeps one rule for the option in every project, the rule by which DEC-070 rejects filing onto the configured board while ignoring the option: a filing never does less than it was asked with no sign. The cost is a call that went on before, refused for an option that did nothing, which the warning below would spare.

**Why refuse rather than delete the option.** A filing that names the configured board's own number asks for what the filing does anyway, so it goes on, and a caller that passes it keeps working. A refusal also names the way out, where a parser that no longer knows the option names none.

**Why not warn first.** A warning learns only from a caller who reads it and reports it, and holds the decision open for a release at least, while the costs stand. What it would learn is whether the break reaches someone, which is the other side of the weighing: what the override gives its callers. Resting on the costs alone, the refusal bets that this benefit is small, a bet no evidence read settles either way (Context). The record takes that bet. The costs are the capability's own, shown by its records and code, and a caller the bet loses is told at its first filing, as a warning would tell it, with the way out, and nothing half done. Where the maintainer will not take the bet, the warning is the choice to make.

### Alternatives considered

- **Keep the override as DEC-019 has it.** Not taken. Each cost under the Context stands. Keeping the option sound needs the defect of project-kit#3240 fixed and an option naming 0 refused, and even then the membership check reports each issue so filed as drift the capability made on purpose. Wherever the board sync gives a missing card, the next sync would give the issue its card on the configured board anyway, so "in place of" would last only until then.
- **Refuse by default, with a setting of the project's that keeps the override.** A caller that needs the override gets it back with one line of its configuration. Not taken. Wherever the setting is on, every cost under the Context stands, and the defect of project-kit#3240 needs fixing. The option keeps two behaviours to build, test and document, for a use no one is known to make, and the setting could not reach a project whose board holds the state (DEC-070). A later record can add it once a caller shows, and the refusal's message tells such a caller at once.
- **Make the option add a second card in every project, with no Status written on it.** The issue keeps its card on the configured board, and the second card carries no Status from the capability to go stale. Not taken, for four reasons:
  - the option would come to mean "as well as" for every caller that used it to mean "in place of", with nothing to tell such a caller its meaning changed;
  - filing would owe two adds, each a write that can fail after the issue exists, and under ADR-096 point 4 each would need its board read before the issue is created, and a code saying the issue was filed where it fails after;
  - a board's own automation may set a Status on the second card when it is added, or when its issue is closed, and the capability does not control that, so the second card can still show a state no command keeps;
  - it gives in one command what filing and one host command give in two.

  Under it, DEC-070's refusal would lose its ground where the board holds the state, since the issue would keep its card on the configured board, and a record choosing it would have to decide whether the refusal gives way. That record would weigh the same automation on a board that holds the state.
- **Warn on each use, and decide once the evidence is in.** Not taken, as "Why not warn first" says. It costs a release at least of the costs under the Context, and leaves the defect of project-kit#3240 to fix or to wait on. It is the choice to make where the maintainer will not break a call whose callers are unknown.
- **In a project with no board, warn, and let the filing go on.** No call breaks, and the silence ends: the filing says that it adds the issue to no board. Not taken, as "Why a project with no board too" says: the option would be refused in a project with a board and only warned of in one without, and a filing would do less than it was asked with a line read once as the only sign. It is the choice to make where the maintainer weighs the break above the one rule.
- **In a project with no board, leave the option as it is.** Rejected: the filing drops what it was asked with no sign.
- **Delete the option from the filing command.** Rejected: a caller that names the configured board breaks for nothing, and the parser's error names no way out.
- **File onto the configured board, ignoring the option, and warn.** Rejected, as DEC-070 rejects it: the filing would do other than it was asked, with a warning read once as the only sign.

## Implications

- **The filing command** refuses a board option naming a board other than the configured one wherever a board is configured, and any board option where none is, with the message point 3 gives for the project's case. It refuses before it writes anything or asks the person anything, in a dry run too, as DEC-070 has it where the board holds the state. Its tests hold:
  - the refusal where the Status is the state's projection, where the state degrades, and where no board is configured, and that nothing is written and nothing asked before it;
  - that an option naming the configured board's own number goes on, the two compared as numbers;
  - that the message for a board declared with no number says that the board holds the state only where the map binds it there.

  The build of DEC-070's refusal ([project-kit#3254](https://github.com/aleskalfas/project-kit/issues/3254)) can take this reach where this record is accepted before that build lands.
- **A board option naming a number below 1** names no board. Refusing it before anything is written, in every project, is a check of the option's value that [project-kit#3241](https://github.com/aleskalfas/project-kit/issues/3241) asks for whatever this record decides, and it rests on no record. Its message says that no board has such a number. It runs first: before the option is compared with the configured board, and before any read of a board. So where an option names a number below 1, its message is the one given, in every project, in place of the message point 3 gives for the project's case. Once ADR-096 is built, running before the read also keeps such an option from being refused as a board that did not answer (Context).
- **project-kit#3240** fixes a defect that arises only in a filing that names another board, which the refusal stops in every project. Its build waits on this record. If this record is accepted, it closes as not planned, naming this record. If it is refused, it is built as it stands.
- **The reference for the board option,** the option's own help and the procedure the capability gives an agent for filing an issue, says that the option is refused unless it names the configured board. It changes with the build, once this record is accepted.
- **The edits to accepted records,** made in this change once this record is accepted:
  - **DEC-019:** its top line reads *Partially superseded by [project-management:DEC-070-filing-another-board] and [project-management:DEC-071-filing-only-configured-board]*, and says in the line itself: "Wherever a board is configured, filing refuses a board other than the configured one: where the substrate map binds the state to the board (DEC-070), and in every other project with a board (DEC-071). Overturned: the per-invocation override at filing in 'Multi-board adopters at v1'." The rest of DEC-019 stays as it stood.
  - **DEC-070:** two edits.
    - Its top line reads *Partially superseded by [project-management:DEC-071-filing-only-configured-board]*, and says in the line itself: "Filing refuses a board other than the configured one in every project with a board. Overturned: that the override stands where the state is carried off the board or degrades, wherever this record says so, the conclusion its Rationale 'Why only where the board holds the state' and its rejected alternative 'Refuse wherever the map binds any axis to the board' draw for those projects, and the test that the option is not refused there. Their premises stand, as does the refusal where the board holds the state, with what counts as another board, when it comes, what it says and its code."
    - In its Context, "The gap between them", one sentence is corrected as a fact is, since the post-check workflow's remediation runs only on a finding that blocks, and the membership check's drift never blocks ([pkit:ADR-096], its Implications on the workflow). The sentence "DEC-019 calls its missing card drift, which it warns of on an existing issue for a person to fix, and the post-check workflow it offers adds a card missing at filing to the configured board, where a project installs the workflow and turns on its remediation." reads "DEC-019 calls its missing card drift, which it warns of on an existing issue for a person to fix, and the post-check workflow it offers does not add the card, even where a project installs the workflow and turns on its remediation, since that remediation runs only on a finding that blocks, and drift never blocks." The sentence after it, "That card gets no Status from DEC-019", then speaks of the card once someone adds it, and stays as it is.

    The rest of DEC-070 stays as it stood.
  - **ADR-096,** named here for the architect, who keeps it, to make in this change once this record is accepted. Each edit refines it in place: its account of what counts as the board's answer stands whole, and only the room it makes for the override goes, since no filing reaches it.
    - In the Context's terms, "The configured board" loses its last two sentences: "Where one filing names another board in its place, as DEC-019 lets it, that board is the configured board for that filing's own reads and writes, and for nothing else. It is read by its number, since no node is stored for it."
    - In the Boundaries, the bullet "Not the override at filing" is replaced by a bullet whose text is the one below, its three citations written as ADR-096 writes a capability's record, a link relative to ADR-096's own place: `**Not another board a filing names.** Filing refuses a board option naming a board other than the configured one before any read of a board ([project-management:DEC-070](../../../.pkit/capabilities/project-management/decisions/DEC-070-filing-another-board.md), [project-management:DEC-071](../../../.pkit/capabilities/project-management/decisions/DEC-071-filing-only-configured-board.md)), so the only board this record's reads and writes ask about is the configured one (refinement per [project-management:DEC-071](../../../.pkit/capabilities/project-management/decisions/DEC-071-filing-only-configured-board.md)).` The clause says "ask about", not "are of", since a read of an issue's own cards spans every board the issue is on.
    - In the Rationale, "So filing refuses first: it files no issue DEC-019 rejects, save one that names another board, as DEC-019's own override lets it (Boundaries), and leaves no partial state." reads "So filing refuses first: it files no issue DEC-019 rejects, and leaves no partial state."
    - In the Implications' "Standing unedited", DEC-019's item loses the sentence "The override at filing stays its own, its board standing in for the configured one in that filing's own reads and writes (the terms)."
    - In the Implications' tests, "filing's read first" loses its last sentence, "A filing that names another board reads that board first, by its number", and ends at "reports the Status not written in one line;". No filing names another board once the refusal is built, and the refusal's own tests are the filing command's, above and in DEC-070.

    Until this record is accepted, ADR-096 stands as it is, that test with it, for the projects where DEC-070 leaves the override. The build of ADR-096 ([project-kit#3256](https://github.com/aleskalfas/project-kit/issues/3256)) builds that read: a branch of the filing command that reads a named board in the configured one's place, by its number, two passages of the command's documentation that cite ADR-096's Boundaries for it, the module's and that branch's own, and ADR-096's test of it. The refusal's build rebases on that build, and removes all three, since no filing reaches them.
- **A surface change** for the capability, once built. A call that succeeded before is refused, so the change breaks every project's use of the option to name another board, and a project with no board's use of it at all. The build's changeset declares it, and weighs its segment as such a break. It changes no state a project holds, and the option keeps its signature, so it owes no migration.
- **Acceptance:** this record partially supersedes the accepted DEC-019 and DEC-070, corrects a fact in DEC-070, and refines the accepted ADR-096 in place, so accepting it needs the maintainer's sign-off. The architect makes the edits to ADR-096 in this change.
