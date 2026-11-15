---
id: DEC-071
title: Filing refuses a board other than the configured one in every project
status: proposed
date: 2026-11-15
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** every issue belongs on the configured board, and every command but filing reads and writes that board alone. A filing whose board option names another board puts the issue there in the configured board's place, so the issue starts with no card where every command looks for one, and nothing the capability does after filing reaches the card it does have. Where the board holds the state, [project-management:DEC-070-filing-another-board] already refuses such a filing. This record refuses it in every project, a project with no board included, the same way: before anything is written or asked, saying how to file the issue instead. A filing that names the configured board's own number still goes on. No caller of the option is known. The record says what was weighed, and how a person could learn more.

## Context

**The terms.**

- *The configured board*, *the board holds the state* and *a filing that names another board* are as DEC-070 defines them.
- *The override* is the one [project-management:DEC-019-mandatory-issue-state] gives a filing in "Multi-board adopters at v1": a board option that names a board in place of the configured one, for that filing alone.
- *The Status is the state's projection* where a board is configured and the state is carried off it, and *the state degrades* where a present substrate map leaves the state out or marks it unsupported, so that the capability writes no Status ([project-management:DEC-062-axes-chosen-in-the-map] point 5).

**What the records say.**

- **DEC-019 puts every issue on the configured board from its filing.** It rejects at filing an issue with no card there, and calls a missing card on an existing issue drift, at warning severity. Its override is the one exception, and it defers several boards for one project until one is asked for.
- **DEC-070 refuses the override where the board holds the state,** because the issue's position would be one no command reads. It leaves the override as it stands in every other project, and leaves to [project-kit#3241](https://github.com/aleskalfas/project-kit/issues/3241) whether it should stand there.
- **Every other command reads and writes the configured board alone.** A move writes the Status of the issue's card there. The command that brings the board's Status in line reads every card there. The membership check reads the issue's card there, once [pkit:ADR-096] point 5 is built.

**What the override costs where the board does not hold the state.**

- **No card on the configured board.** When this record was written, the membership check read the issue's cards on every board, so it reported only an issue on no board, and passed this one. Under ADR-096 point 5 it reads the configured board's card, and reports the issue as the drift DEC-019 names. The capability's own filing then makes an issue its own check reports.
- **A card nothing keeps.** Where the Status is the state's projection, filing writes the first Status on the named board's card, and no move updates it, so the card keeps a state the issue left at its first move. The command that brings the board's Status in line gives the issue its card on the configured board, once someone runs it. Where the state degrades, no command gives the issue that card.
- **Board fields written against the wrong board.** The filing's hooks pair the named board's card with the configured board's project, so the write that seeds a board field's default fails ([project-kit#3240](https://github.com/aleskalfas/project-kit/issues/3240)).
- **A filing that does less than it was asked.** An option naming 0 adds the issue to no board, after the filing announced the add, with no warning. In a project with no board, an option naming any board adds the issue to none, and says nothing.

**What was weighed of the option's use.**

- **In this capability:** none of its commands, skills, agents, tests or workflow templates passes the option, and none has since the repository's first commit, where the option already stood. The filing procedure lists it in the command's synopsis, and says nothing of when to use it.
- **In the tracker:** no issue reports using it, or asks for it.
- **In the projects that adopt the capability:** the one adopting project whose files were read for this record configures no board, nor does the project that builds the capability.
- **What could not be read:** how other adopting projects use it. The capability keeps no record of the options a filing passed. The comment it posts on each new issue records the versions it was filed under and the date, and nothing of its options ([project-management:DEC-041-version-provenance-stamp]).

**How a person could learn more,** before accepting this record or after it:

- ask the projects that adopt the capability, through whatever channel the maintainer keeps with them;
- in each adopting project with a board, list its open issues that have a card on another board and none on the configured one. That is the trace each use of the option leaves until someone adds the missing card. A card added by hand to another board, and the configured one's removed, leaves the same trace, so the count bounds the use from above;
- search an adopting project's scripts, CI workflows and agent definitions for the option;
- ship a warning on each use first, naming how to report it upstream, and decide after a release (the third alternative below).

## Decision

**In every project, the filing command refuses a filing that names a board other than the configured one, as DEC-070 refuses it where the board holds the state: before it writes anything or asks the person anything. A filing that names the configured board's own number goes on. DEC-019's override stands in no project.**

### 1. The refusal reaches every project

- **Where.** Where the board holds the state, as DEC-070 has it. Where the Status is the state's projection, where the state degrades, and where the project configures no board, by this record.
- **What counts as another board, when it comes, and its code:** as DEC-070 has them. A project that configures no board gives no board number to compare with, so every board an option names is another.

### 2. What it says

- **Where the board holds the state:** DEC-070's message.
- **Where a board is configured and does not hold the state:** that every issue belongs on the configured board, which every command reads and writes, so an issue filed onto the named board would have no card where every command looks for one. It names DEC-070's two ways out: leave the option out, to file onto the configured board, or, where the issue should be on the other board too, add a card there after filing by the host's own means, which the message names. That card is the project's own: no command reads or writes it.
- **Where the configuration declares a board and gives no number:** DEC-070's message for that fault.
- **Where the project configures no board:** that it configures none, so a filing adds the issue to no board. The way out is to leave the option out, and to add a card to the named board after filing by the host's own means, where the issue should be on it.

### What this overturns, and what stands

- **Overturned in DEC-019:** the override, "per-invocation override at filing time via `create-issue.py --board=<N>`" in "Multi-board adopters at v1", in every project where DEC-070 left it. Between them, DEC-070 and this record leave it standing nowhere.
- **Overturned in DEC-070:** that the refusal does not apply where the state is carried off the board or degrades (its "Where" bullet), and that it leaves the override elsewhere as DEC-019 has it (its Decision's last sentence).
- **Stands in DEC-070:** the refusal where the board holds the state, with what counts as another board, when it comes, what it says and its code.
- **Stands in DEC-019:** every issue's card on the configured board from filing, the severities of an issue without one, and the single default board, with several boards for one project deferred.

## Rationale

**Why refuse in every project.**

- **The override makes the issue DEC-019 rejects.** At every other filing, an issue with no card on the configured board is a reject. The override is the one route by which the capability's own command makes that issue, on purpose, and after ADR-096 point 5 is built, the capability's own check reports it.
- **Nothing after filing reaches the other board.** Each command reads and writes the configured board alone. The named board's card is the one thing the override gives that a later step neither undoes nor leaves stale, and one command of the host's, run after filing, gives the same card.
- **No caller is known,** in the capability, its tracker, or the adopting projects that could be read.
- **A refusal costs a caller little, and says so at once.** Nothing is written before it, so nothing is left to undo, and its message names the way out. A project that needs an issue on two boards at filing then has a reason to say so, and a later record can design several boards for one project, as DEC-019 defers it until one is asked for.

**Why a project with no board too.** There the option asks the filing to add the issue to a board, and the filing adds it to none, silently. That is the same fault as the option naming 0, and a refusal says what the filing will not do.

**Why refuse rather than delete the option.** A filing that names the configured board's own number asks for what the filing does anyway, so it goes on, and a caller that passes it keeps working. A refusal also names the way out, where a parser that no longer knows the option names none.

**Why not warn first.** A warning gathers evidence only where a person reads it and reports it, and the capability counts nothing it could read instead. Meanwhile the costs above stand, or are fixed in code the removal then deletes, the defect of project-kit#3240 among them. The refusal tells each caller at its first filing, as the warning would, and leaves nothing half done. Where the maintainer wants the evidence first, the ways to gather it are listed under the Context, and accepting this record waits for them.

### Alternatives considered

- **Keep the override as DEC-019 has it.** Not chosen. Each cost under the Context stands. Keeping the option sound needs the defect of project-kit#3240 fixed and an option naming no board refused, and even then the membership check reports each issue so filed as drift the capability made on purpose. All of it serves a use no one is known to make, and the filing still makes an issue DEC-019 rejects.
- **Make the option add a second card in every project, with no Status written on it.** The issue keeps its card on the configured board, and the second card carries no Status from the capability to go stale. Not chosen, for four reasons:
  - the option would come to mean "as well as" for every caller that used it to mean "in place of", with nothing to tell such a caller its meaning changed;
  - filing would owe two adds, each a write that can fail after the issue exists, and under ADR-096 point 4 each would need its board read before the issue is created, and a code saying the issue was filed where it fails after;
  - a board's own automation may set a Status on the second card when it is added, or when its issue is closed, and the capability does not control that, so the second card can still show a state no command keeps;
  - it gives in one command what filing and one host command give in two.

  Under it, DEC-070's refusal would lose its ground where the board holds the state, since the issue would keep its card on the configured board, and a record choosing it would have to decide whether the refusal gives way. That record would weigh the same automation on a board that holds the state.
- **Warn on each use, and decide once the evidence is in.** Not chosen, as "Why not warn first" says. It is the choice to make where the maintainer judges the evidence too thin to break a call on, and it holds the decision open for at least one release.
- **Delete the option from the filing command.** Rejected: a caller that names the configured board breaks for nothing, and the parser's error names no way out.
- **Refuse wherever a board is configured, and leave a project with no board as it is.** Rejected: such a project's filing then ignores what it was asked, with no sign, as "Why a project with no board too" says.
- **File onto the configured board, ignoring the option, and warn.** Rejected, as DEC-070 rejects it: the filing would do other than it was asked, with a warning read once as the only sign.

## Implications

- **The filing command** refuses a board option naming a board other than the configured one in every project, with the message point 2 gives for the project's case, before it writes anything or asks the person anything, in a dry run too, as DEC-070 has it where the board holds the state. Its tests hold:
  - the refusal where the Status is the state's projection, where the state degrades, and where no board is configured, and that nothing is written and nothing asked before it;
  - that an option naming the configured board's own number goes on, the two compared as numbers.
- **A board option naming a number below 1** names no board. Refusing it before anything is written, in every project, is a check of the option's value that [project-kit#3241](https://github.com/aleskalfas/project-kit/issues/3241) asks for whatever this record decides, and it rests on no record. Its message says that no board has such a number.
- **The defect of project-kit#3240** arises only in a filing that names another board. Once the refusal is built, no filing reaches it.
- **The reference for the board option,** the option's own help and the procedure the capability gives an agent for filing an issue, says that the option is refused unless it names the configured board. It changes with the build, once this record is accepted.
- **The edits to accepted records,** made once this record is accepted:
  - **DEC-019:** its top line reads *Partially superseded by [project-management:DEC-070-filing-another-board] and [project-management:DEC-071-filing-only-configured-board]*, and says in the line itself: "Filing refuses a board other than the configured one, where the board holds the state (DEC-070) and in every other project (DEC-071). Overturned: the per-invocation override at filing in 'Multi-board adopters at v1'." The rest of DEC-019 stays as it stood.
  - **DEC-070:** its top line reads *Partially superseded by [project-management:DEC-071-filing-only-configured-board]*, and says in the line itself: "Filing refuses a board other than the configured one in every project. Overturned: that the refusal does not apply where the state is carried off the board or degrades, and that the override stands there. The refusal where the board holds the state stands, with what counts as another board, when it comes, what it says and its code." The rest of DEC-070 stays as it stood.
- **No other record is edited.** DEC-051 point 6, DEC-062 point 5 and ADR-096 read the configured board alone, and this record follows them.
- **A surface change** for the capability, once built. A call that succeeded before is refused, so the change breaks every project's use of the option to name another board. The build's changeset declares it, and weighs its segment as such a break. It changes no state a project holds, and the option keeps its signature, so it owes no migration.
- **Acceptance:** this record partially supersedes the accepted DEC-019 and DEC-070, so accepting it needs the maintainer's sign-off.
