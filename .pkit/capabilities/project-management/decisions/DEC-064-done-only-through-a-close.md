---
id: DEC-064
title: An issue reaches Done only by closing, so a move to Done of an open issue is refused
status: proposed
date: 2026-10-31
author: Aleš Kalfas <kalfas.ales@gmail.com>
---

**In plain terms:** an issue reaches Done only once it is closed, by the merge of its pull request or by a close the person authorises. Asked to move an open issue to Done, `move-issue` refuses before it writes anything, and names the commands that close the issue. It refuses wherever the state lives. A move to Done of a closed issue stays allowed, and a command that closes an issue makes that move only after the close.

## Context

Five paths reach Done, and each is a close ([project-management:DEC-006-state-machine-and-cascade], "Closure triggers"). The workflow declares every move into Done for a command that closes: `done-work` for a merge, and `close-issue` for the others. `move-issue`, the command that moves an issue between states, finds a declared move by its two states and the issue's type alone. So asked to move an open issue to Done, it makes the move without closing the issue ([#2304](https://github.com/aleskalfas/project-kit/issues/2304)).

What the move leaves behind depends on where the state lives.

- **On the board** ([project-management:DEC-062-axes-chosen-in-the-map] point 5), it sets the card's Status to Done. That Status names no open state, so the issue's position is undetermined ([project-management:DEC-051-axis-carriage-activation] point 6). A move of it is refused, and a seat choosing work skips it. Nothing the capability writes sets the card back, so the issue stays there until a person sets the card or it closes.
- **On labels,** it writes the Done label. An open issue reads as the state its label names, so it reads as Done while it is open. The closure cascade then counts it as a done child, and can offer its container for closing over open work.
- **Nowhere,** where a present map leaves the state out, it writes nothing. Yet where a journal is kept, it records a move to Done of an issue that stayed open.
- **Derived from open or closed,** an open issue stands in no state of the lifecycle, so the move is refused as undeclared.

In each case the close's own safeguards are skipped. The checkbox gate is one, which [project-management:DEC-007-checkbox-validation] makes a hard stop on every move to Done. So are the comment giving the reason or the result, the release of the owner and the closure cascade. The person's `--yes` authorises a move whose meaning is unsaid, since a won't-do close and a completed close are different ends (DEC-006).

A variant in the project's analysis moves a Task in Review to Done directly ([the use case of moving an issue](../../../../tech-docs/analysis/project-management/use-case-model/use-cases/020-file-and-move/UC-061-move-issue.md), variant 7a). There the system checks the checkboxes before it writes, and the variant's warning counts leaving the issue open among what is not built. No record decides that variant. DEC-007 decides the gate, and DEC-006 gives the move from Review to the merge.

One command takes this path by design: after a merge, `done-work` moves its issue to Done before it closes each issue the merge left open. Its issue can be open at that move. The base may be one the tracker closes no issue on, or the pull request may not name the issue. Or the tracker's close may not have landed yet.

## Decision

**An issue reaches Done only by closing. `move-issue` moves no open issue to Done: it refuses before writing anything, and names the commands that close the issue. This holds wherever the state lives. A move to Done of a closed issue stays allowed, and a command that closes an issue and moves it to Done closes it first.**

### 1. Every path into Done is a close

Each path into Done is a close (DEC-006): the merge of the issue's pull request, or a close the person authorises. No move the capability makes writes Done for an open issue, on a label or on a card. The command that closes owns the close's safeguards: the checkbox gate, the comment, the release of the owner and the closure cascade.

### 2. A move to Done of an open issue is refused before anything is written

Asked to move an open issue to Done, `move-issue` refuses. It writes no label and no Status, posts no comment, records no move, fires no hook and moves no ancestor. Neither `--yes` nor a named merged pull request changes that.

The refusal names each command the workflow declares for a move into Done of the issue's type. The workflow's command line for each such move names what its close needs, such as a reason, a result or a merged pull request. The refusal shows that line.

The refusal turns on two facts the command holds before it reads the issue's position: the issue is open, and the target is Done. So it reads nothing on the board, and is the same whether the card places the issue or the board cannot be read.

### 3. The refusal is the same wherever the state lives

The refusal does not depend on where the state lives, or on whether it lives anywhere. Where a board is kept as the state's projection, its Status is not written either, since no move is made.

### 4. A move to Done of a closed issue stays allowed

On a closed issue, a move to Done is the close's move on the state. It brings the label or the card in line with the close. What it writes, what it records and what it cascades stay as DEC-006 and the records that refine it decide.

### 5. A command that closes an issue and moves it to Done closes it first

A command that closes an issue and moves it to Done makes the move once the issue is closed, as the completed close does (DEC-006). Where `done-work` finds its issue open after the merge, whatever kept it open, it first closes the issue through the merged pull request. That is the close it makes of each other issue the merge left open, with the issue's cascades held until the move. The move to Done follows.

The forward cascade runs before the closure cascade, and each runs once, as DEC-006 orders them for a completed close. Where the close through the pull request is refused, the issue stays open where it stood, and `done-work` names the command that closes it.

## Rationale

**Why refuse, rather than close.** A move to Done cannot say which close it is. From Review only the merge closes the issue, and `move-issue` cannot merge. From the other states, a Task closes as completed, naming its result, or as won't-do, naming its reason. A container closes as won't-do, or once its children are done and its boxes ticked.

So to close in the move, `move-issue` would have to guess the close the person meant, or take each close's inputs. The second is a generic transition command with a flag for each close, which [project-management:DEC-026-work-ownership-lifecycle] rejects. The analysis's variant asks for that, and this record decides against it.

**Why the same wherever the state lives.** The fault is the move, not where the state lives. On the board it leaves the issue where no command can place it, and on labels it reads as Done with nothing reported. A closure cascade that counts an open child as done can then close a container over open work. Refusing on the board alone would leave the labels' way in place.

**Why the refusal reads no position.** Whether the move is a close needs only that the issue is open. A refusal that read the card first would answer an unreadable board or a misplaced card, and leave the close unnamed. Naming the closing commands at once points the person at the close, and each closing command then reads the position for itself.

**Why the move to Done of a closed issue stays.** On a closed issue the move is the close's move on the state. It brings the label or the card to Done and records the close a merge made ([#2307](https://github.com/aleskalfas/project-kit/issues/2307)). The commands that close compose over it, so removing it would move that work into each of them.

**Why a command that closes moves after the close.** The move's job is to bring the state in line with a close that has happened. Made before the close, it writes Done on an open issue, the state this record forbids, and leaves it there if the close fails. Closing first means a failure leaves the issue open where it was, a position every command reads.

`done-work` makes its move right after the merge, so that no step stands between the merge and the lifecycle's move. On an open issue, the close through the pull request comes first, as the start of that move rather than a step beside it. A close the tracker makes meanwhile is no conflict, since an issue closes once.

### Alternatives considered

- **Close the issue in the move, as the lifecycle allows from where it stands.** Rejected: the move cannot say which close is meant, as "Why refuse, rather than close" says.
- **Close through the merged pull request the move names, and refuse otherwise.** Rejected: the commands that close compose over `move-issue`, and the completed close calls it. A move that closed would turn that layering upside down, and the two would call each other.
- **Refuse only where the board carries the state.** Rejected: on labels the same move makes an open issue read as Done, as "Why the same wherever the state lives" says.
- **Read the position first, and name the one command that closes the issue from there.** Rejected: on the board the read can fail, and the refusal would then name a broken board instead of the close. The closing command reads the position, and refuses for its own reason.
- **Keep the move, and have later commands treat an open issue at Done as where it stood before.** Rejected: a position no read gives would be guessed, which DEC-051 point 6 refuses.
- **Take Done out of `move-issue`'s targets.** Rejected: on a closed issue the move does work the closing commands need, as "Why the move to Done of a closed issue stays" says.

## Implications

- **`move-issue` refuses** a move to Done of an open issue as a usage error, as it refuses a move the workflow does not declare. The refusal comes before the issue's position is read. It comes before every step that could write, such as the guard that refuses a move of an issue another instance owns ([project-management:DEC-035-instance-ownership] point 6).
- **The workflow's command line for each move into Done** names what its close needs (point 2). The build adds that where the line is bare.
- **`done-work` reads its issue after the merge.** Where it is open, it closes it through the merged pull request with neither cascade, then moves it to Done. Each issue the merge closed, its own included, then runs its closure cascade once. A close the tracker makes in between must not fail the run.
- **Tests** cover the refusal wherever the state lives, and that nothing is written or recorded in any of them. They cover a move to Done of a closed issue under the board and under labels. They cover `done-work` on an issue its merge left open, for each reason it can stay open, under both.
- **The analysis's variant** of a direct move to Done of a Task goes, with the build. The example of an engine gate that only warns, which [#1215](https://github.com/aleskalfas/project-kit/issues/1215) gives, is such a move with unticked boxes, and cannot arise. Its own question, whether `move-issue` asks the engine before it writes, stands.
- **Every account the capability gives** of two behaviours goes stale, and changes with the build. These are a move to Done of an open issue, and the order of `done-work`'s close and move.
- **An issue left open at Done** is repaired by the paths that exist for it. On the board a person sets the card's Status, as the refusal of an unplaced card says. On labels `reopen-issue` resets the state.
- **Not decided here:**
  - How an open issue that carries Done anyway, by a hand-written label or a reopen made outside the capability, is read under labels. The closure cascade counts such an issue as done, and a board kept as the projection is brought to Done for it. That is a question of its own.
  - What the forward cascade does at an ancestor it cannot place, which is [#2305](https://github.com/aleskalfas/project-kit/issues/2305)'s question. Under this record every move to Done follows a close, and that question's answer has to hold there too.
  - What a card a person drags to Done means, which stays the question DEC-006 leaves open.
- **DEC-006 and DEC-026 carry this refinement,** each with a pointer to this record. In DEC-006 it is in "Closure triggers" and in the Implication on how a requested move is dispatched. In DEC-026 it is in the `done-work` row.
- **A surface change** for the capability: a call `move-issue` accepted is refused. The build declares it in a changeset. No migration is owed, since nothing an adopter holds is renamed, removed or restructured.
