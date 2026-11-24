---
id: DEC-083
title: A pace setting counts as a person's only where a user's account posts it
status: accepted
date: 2026-11-22
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** a person may set any seat's pace, and that setting bounds the seat: it outranks what the seat's directing seat set before it, and voids it ([project-management:DEC-082-pace-of-subagents] point 6). This record says whose setting that is. A setting, or a clear, counts as a person's only where the account that posts it is a user's account. Posted by a bot's account, such as an app's, it counts for nothing. So under a credential that names no user's account, the command that sets a pace writes no person's setting, even on the person's word. It refuses, and names what works for what was asked: the worker's directing seat, which sets a pace as its own, the ceiling in the committed configuration, or the command run under the person's own account. A directing seat's setting counts as DEC-082 has it.

## Context

DEC-082 point 6 lets two setters write a seat's pace on its state issue. The worker's directing seat writes its setting from the clone that holds that seat. A person writes for any seat, at a terminal or through the command run with its consent flag on the person's word. A person's setting stands until a person clears it or sets another, and voids every setting the directing seat wrote before it. A planner's or a lead's seat names no directing seat, since the person directs it, and a worker's seat may name none ([project-management:DEC-081-delegation-between-seats] point 3). Only a person sets the pace of a seat that no seat directs.

Three accepted records bear on who acts when a comment is posted:

- **The posting account is the act's actor** ([project-management:DEC-078-one-actor-per-act]). No comment the commands post names an authoriser beside the account that posts it.
- **A bot's account stands for no person** ([project-management:DEC-079-bots-are-no-person]). No claim on work counts from it, and in human mode no approval counts from it as a person's.
- **Under a credential that names no user's account, no person stands for the acting account** ([project-management:DEC-076-app-credentials]). Such a credential is an app's, a workflow's, or one the service gives no answer about. An app's clone may still hold a planner's seat, or the organizer seat, behind a closed membership gate (DEC-076 point 6). What passes on the caller's word under every credential passes the same under such a credential (DEC-076 point 5).

DEC-082's fold counts a setting where its author may write ([project-management:DEC-058-state-issues] point 4), and puts no condition on the kind of account that posts a person's setting. So under an app's credential, the setting command run on a person's word posts, under the app's bot account, a setting whose setter is a person, and the fold ranks it as a person's bound on the seat.

## Decision

**A pace setting, or a clear, counts as a person's only where a user's account posts it, and under a credential that names no user's account the setting command writes none.**

### 1. Only a user's account writes a person's setting

- **What counts.** The fold of a seat's pace counts a setting or a clear whose setter is a person only where its author is a user's account, the kind of account DEC-079 point 3 asks first of an approval. The fold reads the author's kind from the comment's own record, as the state-issue seam gives it for every counted comment ([pkit:ADR-071] point 3).
- **What counts for nothing.** Such a setting or clear from a bot's account counts for nothing, neither as a person's nor as a directing seat's. It voids nothing, and a clear from it ends nothing.
- **An account of a kind unknown** never reaches the fold: its comment either does not count or leaves the read incomplete, as DEC-058 point 4 has it.
- **What stays as DEC-082 has it.** A directing seat's setting counts as DEC-082 point 6 has it, whatever kind of account its clone works under. A person's setting from a user's account counts only where that account may write. The rule is a guard, not a boundary: an agent that posts under a user's account writes a setting that counts as a person's, and only the procedure keeps it from doing so (DEC-082 point 6).

### 2. Under a credential that names no user's account, the command writes no person's setting

- **The refusal.** Run as a person's, at a terminal or with its consent flag, the command that sets or clears a pace refuses under a credential that names no user's account, as DEC-076 defines one. Under a bot's account, what it would write counts for nothing (point 1). Where the service gave no answer about the credential, the command cannot tell that its posting account is a user's (DEC-076 point 1), and the refusal says that a second run passes once the service answers with a user's account.
- **What it names instead,** for what was asked:
  - **a pace that the worker's directing seat may set,** at or below the ceiling and below a person's setting that stands: that directing seat sets it as its own, and where this clone holds the directing seat, the command run as that seat;
  - **a lower pace for every seat:** the ceiling, changed in the committed configuration through a change a person authorises;
  - **anything else,** such as raising past or clearing a person's setting that stands, or setting the pace of a seat that no seat directs: the command run from a clone under the person's own account.
- **Its override.** The refusal is a firm precondition of the command, which takes `--force` as [project-management:DEC-046-override-flag-convention] point 3 has it. A setting written by force still counts for nothing (point 1), and the command says so as it writes.
- **A directing seat's setting** from a clone under such a credential is written as DEC-082 has it, after the command confirms the seat.
- **What it leaves to another record.** This record decides which posting account a person's setting needs. Who may give a person's word in an agent's turn stays with the record DEC-076 point 5 leaves it to.

## Rationale

**Why only a user's account writes a person's setting.** A person's setting is a person's bound on a seat: it outranks the directing seat's, voids what that seat set before it, and only a person lifts or clears it (DEC-082, "Why a person's setting outranks the directing seat's"). Its rank rests on who acted. The act's actor is the account that posts it (DEC-078), and a bot's account stands for no person (DEC-079). So a setting posted under a bot's account names as its setter a role that its actor cannot hold. This record extends DEC-078's reasoning to that setter: the fold ranks a setting by the account the service records, never by what the caller says of it. Counted, such a setting would lift or clear a person's bound, or void a directing seat's settings, with no person's account ever acting.

**Why the test is the account's kind alone.** DEC-079 point 3 also leaves out an account the project registers as a reviewer agent's. That list is configuration, which the state-issue seam never reads (ADR-071 point 7), and no reviewer agent runs the setting command in any procedure. So a registered reviewer agent's user account falls within the guard's limit, as any agent's user account does (point 1).

**Why an account of a kind unknown is left to DEC-058.** DEC-058 point 4 already keeps such an author's comment from counting, which grants nothing and frees nothing ([pkit:ADR-094] point 3). Counting it for nothing would free the slots that a lower setting held, so this record adds no rule of its own there.

**Why the command refuses rather than writes.** A setting that counts for nothing would read on the issue as set, while the seat runs at another pace. Refusing writes nothing misleading, and names the ways that work. An operator who forces it is told what the setting counts for.

**Why a release by force passes on the caller's word, and a person's setting does not.** A person's release by force passes on the caller's word under such a credential ([project-management:DEC-059-topology-of-seats] point 5). It names no authoriser, only a reason, which stays the caller's report, and whether its author may release by force is its caller's check. A pace setting carries a setter, and the fold ranks it by that setter: a person's outranks a directing seat's. That rank is a statement of who acted, and under a bot's account the actor the service records is no person. Under DEC-082 point 6 and DEC-076 point 5 together, a person's setting passed on the caller's word under every credential. This record refuses it under a credential that names no user's account, so "passes the same" no longer holds for it, and DEC-076 point 5 is overturned for this act alone.

**Why this record does not decide who may give a person's word.** DEC-076 point 5 leaves to a record of its own who may give the caller's word in an agent's turn. This record's test is the posting account, which the service records, not whether the word was the person's. So it holds whatever that record decides, and decides nothing of it.

**What it costs.**

- **A person whose session runs under an app's credential** cannot set a pace there, even one they asked for. A worker's pace they set through its directing seat, below any setting of theirs that stands. A lower pace for every seat they set through the ceiling. Anything else needs a clone under their own account.
- **A seat that no seat directs,** such as a planner's seat that an app's clone holds, moves only by the ceiling, which moves every seat, or by a person's setting from a clone under the person's own account.
- **The guard separates kinds of account, not a person from an agent.** An agent that works under a user's account writes a setting that counts as a person's, as DEC-082 point 6 already says of an agent under the person's own account.

### Alternatives considered

- **Accept a person's setting on the caller's word under every credential,** keeping DEC-076 point 5 whole. Rejected: the fold would rank as a person's bound a setting whose actor the service records as a bot's account, so a person's bound could be lifted or cleared with no person's account acting.
- **Name the person by `PM_INVOKER_LOGIN`.** Rejected: that variable serves only where naming a person grants nothing (DEC-076 point 3), and a person's setting grants: it outranks and voids.
- **Count such a setting only where it lowers the pace.** Rejected: a person's setting voids the directing seat's earlier settings, which stay void once it is cleared, so even a lower setting reaches past its own value. Two kinds of person's setting would also split the fold.
- **Not taken here: a lowering on a person's word,** which voids nothing and is no person's setting, as DEC-082 point 8 lets a person lower a session's pace in words. It would serve a seat that no seat directs, such as an app's planner, short of the ceiling. It needs a third setter in the fold, with its own rules for how it ends, and that is a design of its own. This record keeps DEC-082's two setters, and names the planner's cost.
- **Not taken here: a person's rank for the organizer seat's setting,** granted by the reviewed topology as its release by force is. It would give a seat the rank DEC-082 keeps for a person, which reaches past what this record decides.

## Implications

- **Edits to accepted records,** made in this change once a person accepts this record ([COR-066](../../../decisions/core/COR-066-accepted-before-landing.md) point 5):
  - **Overturned in part.** DEC-082 gains this line at the top of its body, before "In plain terms", and its words stay as they stood under it:

    > **Partially superseded by [DEC-083](DEC-083-person-pace-account.md).** A pace setting or clear counts as a person's only where a user's account posts it, and under a credential that names no user's account the command that sets a pace writes no person's setting or clear. Overturned: point 6's "A person, for any seat, at a terminal or through the command run with its consent flag on the person's word, as a person authorises a release by force (DEC-059 point 5)", so far as it reaches such a credential. The rest stands.

  - **Overturned in part.** DEC-076 gains this line at the top of its body, before "In plain terms", and its words stay as they stood under it:

    > **Partially superseded by [DEC-083](DEC-083-person-pace-account.md).** Under a credential that names no user's account, the command that sets a seat's pace writes no person's setting or clear, even on the person's word. Overturned: point 5's "passes the same under a credential that names no user's account", so far as it reaches a person's setting or clear of a seat's pace. The rest stands.

  - **Refined in place, narrowed.** In DEC-082, point 6's "The fold" bullet, whose "A setting counts only where its author may write (DEC-058 point 4)." gains, after it, the sentence: "A setting or clear whose setter is a person counts only where its author is a user's account (refinement per [project-management:DEC-083-person-pace-account])."
  - **Refined in place, completed.** In DEC-076, point 7's list of what stays unmet gains a bullet after "A planner's seat behind an open gate":

    > - **A person's setting of a seat's pace** (refinement per [project-management:DEC-083-person-pace-account]): lifting or clearing a person's setting that stands, and setting the pace of a seat that no seat directs, but through the ceiling. Meeting it would rank as a person's a setting whose actor is a bot's account, or one the commands cannot tell is a user's, which DEC-083 rules out.

  - **An edit that changes no decision:** none.
- **What stands.** DEC-079, whose first test for an approval this record applies to a pace setting. DEC-058 point 4, which keeps an account of a kind unknown from counting. ADR-071, whose reader gives each counted comment's author with its kind (point 3), and whose fold returns the person's setting where it counts.
- **Acceptance.** A person accepts this record in this change. The pace's events, fold and setting command rest on it, and DEC-082's build, [project-kit#3462](https://github.com/aleskalfas/project-kit/issues/3462), builds them only once this record is accepted.
- **The build** is that Task's: the fold's test of the author's kind, the command's refusal and the ways it names, and their tests. This record files no build Task of its own.
- **No behaviour changes until the build,** so this record needs no changeset and no migration.
