# Reviewing a cycle

A cycle reaches its review when its window ends, as its suspensions moved it (DEC-003 point 4). The review sets what the cycle reached against what it planned, and names the variant that did best. It ends in the person's decision for that variant: persevere, pivot or pause. The method has no fourth decision.

## Before you start

- **The cycle is in review,** as the status shows. A suspended cycle is resumed first (`suspend.md`).
- **The review waits on no experiment.** Experiments still undecided are listed in the report, and the decision does not wait for them.

## 1. Put the progress report together

Lay out, from the files and the person's word:

- **Each key result:** its variant, its step and its target, and what it reached. Ask the person for each number reached.
- **Each experiment** of the cycle: its assumption, what it expected, what it measured, and whether it passed, failed or gave neither. List those still undecided apart.
- **Each assumption** the cycle tested, as it now reads: supported, refuted or inconclusive (DEC-003 point 8).
- **Each suspension,** with its reason, its days and the day it was recorded. One recorded late stands apart from one recorded as it began (DEC-002 point 12).
- **What changed in each canvas** during the window, read from version control, such as `git log --since <window start>` over the idea's folder (DEC-002 point 11).

Read it to the person whole before you ask anything.

## 2. The winning variant

Where the cycle explored several variants, the person names the one that did best. Say which you think did, and why. Where it explored one, that one is the winner, and you need not ask. The review decides nothing for the others (DEC-003 point 4).

## 3. The decision

Explain the three, for the winning variant, and say which you would take and why:

- **Persevere:** its model goes on into the next cycle, as the method has it where the objective was met. Persevering where it was missed draws a warning, and stays the person's call: a near miss with a clear cause may justify it.
- **Pivot:** its model changes, on an insight that could reach the objective in one more cycle. A pivot names at least one decided experiment as its evidence, of any variant the cycle explored. A pivot without evidence is a guess.
- **Pause:** the work on the idea stops for now, at a dead end or out of resources. The idea's record stays whole, and it can be taken up again.

Persevering and pivoting need a winner neither shelved nor split. Ending an idea is not a decision of the review: it is shelving its variants (`outcome.md`).

## 4. Record it

Run the command without the flag to get its question, ask it, and take the person's reasons in their words. On their answer:

```
pkit lean review-cycle <cycle> --reached <number> [--reached <number>]... [--winning <variant>] --decision persevere|pivot|pause --reasons "<their reasons>" [--evidence <experiment>]... --person-decided
```

Give `--reached` once for each key result, in the plan's order. The command refuses a winner the cycle did not explore, a count of reached numbers that differs from the key results, and a pivot with no decided experiment as evidence.

## 5. After the review

Take each of these as its own question, one at a time:

- **The other variants** keep their outcomes. One left shortlisted may be explored again by a later cycle. Where the person no longer believes in one, offer to shelve it (`outcome.md`).
- **The goal** may change now, since no cycle is open (`goal.md`).
- **A pivot** changes the winning variant's canvas (`sketch.md`). Its verdicts go stale, so judge them again and shortlist it again (`outcome.md`).
- **The next cycle,** for persevere or a pivot, is planned next (`plan-cycle.md`). For a pause, nothing waits, and the idea keeps until the person comes back (`return.md`).

## Example

The window of `board-game--first` ends on 13 April 2027, moved two weeks by the January suspension. On 14 April, you lay out the report:

- **Hosts:** 6 paying of the 10 planned. The interviews passed. The price page failed, 3 of 6. The clubs page passed: three clubs paid for their members.
- **Venues:** 0 paying cafés of the 2 planned. The first offer was spoiled by the suspension, and the second, in February, failed.
- **The suspension:** 8 to 21 January, for family matters, recorded on 22 January.

You say hosts did best, and the person agrees. Hosts missed the objective, so you explain that persevering would draw a warning. Clubs paid where single hosts would not, so you lean to a pivot toward clubs. The person decides to pivot, in their words "Single hosts will not pay alone, but clubs will":

```
pkit lean review-cycle board-game--first --reached 6 --reached 0 --winning board-game--hosts --decision pivot --reasons "Single hosts will not pay alone, but clubs will" --evidence board-game--host-interviews --evidence board-game--price-page --evidence board-game--club-page --person-decided
```

Then, one question at a time, the person shelves `board-game--venues` because "no café paid in two offers". You rewrite the hosts' segments and price around clubs. The person judges the variant again and shortlists it again, and you plan the next cycle together.
