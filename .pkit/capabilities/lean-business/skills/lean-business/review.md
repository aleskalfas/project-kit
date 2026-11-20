# Reviewing a cycle

A cycle reaches its review when its window ends, as its suspensions moved it (DEC-003 point 4). The review sets what the cycle reached against what it planned, and names the variant that did best. It ends in the person's decision for that variant: persevere, pivot or pause. The method has no fourth decision.

## Before you start

- **The cycle is in review,** as the status shows. A suspended cycle is resumed first (`suspend.md`).
- **The review waits on no experiment.** Experiments still undecided are listed in the report, and the decision does not wait for them.

## 1. Put the progress report together

First ask the person for each number a key result reached, before you read its target back, so each count is taken from the evidence. Then lay out, from the files and the person's word:

- **Each key result:** its variant, its step and its target, and what it reached.
- **Each experiment** of the cycle: its assumption, what it expected, what it measured, and whether it passed, failed or gave neither. List those still undecided apart.
- **Each assumption** the cycle tested, as it now reads: supported, refuted or inconclusive (DEC-003 point 8).
- **Each suspension,** with its reason, its days and the day it was recorded. One recorded late stands apart from one recorded as it began (DEC-002 point 12).
- **What changed in each canvas** during the window, read from version control, such as `git log --since <window start>` over the idea's folder (DEC-002 point 11).

Read it to the person whole before you ask anything else.

## 2. The winning variant

Where the cycle explored several variants, the person names the one that did best. Ask them first, and say which you think did, and why, once they have answered or when they ask. Where it explored one, that one is the winner, and you need not ask. The review decides nothing for the others (DEC-003 point 4).

## 3. The decision

Explain the three, for the winning variant, and ask which the person takes:

- **Persevere:** its model goes on into the next cycle, as the method has it where the objective was met. Persevering where it was missed draws a warning, and stays the person's call: a near miss with a clear cause may justify it.
- **Pivot:** its model changes, on an insight that could reach the objective in one more cycle. A pivot names at least one decided experiment as its evidence, of any variant the cycle explored. A pivot without evidence is a guess.
- **Pause:** the work on the idea stops for now, at a dead end or out of resources. The idea's record stays whole, and it can be taken up again.

Persevering and pivoting need a winner neither shelved nor split. Ending an idea is not a decision of the review: it is shelving its variants (`outcome.md`). Give your own lean once the person has answered, or when they ask.

## 4. Record it

Take it as the dispatcher's "Asking a judgement" says, with the person's reasons in their words: run the command without the flag, show them its question, and on their confirmation run:

```
pkit lean review-cycle <cycle> --reached <number> [--reached <number>]... [--winning <variant>] --decision persevere|pivot|pause --reasons "<their words>" [--evidence <experiment>]... --person-decided
```

Give `--reached` once for each key result, in the plan's order.

## 5. After the review

Take each of these as its own question, one at a time:

- **The other variants** keep their outcomes. One left shortlisted may be explored again by a later cycle. Where the person no longer believes in one, offer to shelve it (`outcome.md`).
- **The goal** may change at the review, while the cycle is in review or once it is decided, since no cycle of the idea is then planned, running or suspended (DEC-002 point 3; `goal.md`).
- **A pivot** changes the winning variant's canvas (`sketch.md`). Its verdicts go stale, so judge them again and shortlist it again (`outcome.md`).
- **The next cycle,** for persevere or a pivot, is planned next (`plan-cycle.md`). For a pause, nothing waits, and the idea keeps until the person comes back (`return.md`).

## Example

The window of `meal-plan--first` ends on 13 April 2027, moved two weeks by the January suspension. On 14 April, you first ask what each key result reached: 26 households came back for a second planned week, and no grocer paid. Then you lay out the report:

- **Households:** 26 back for a second week, of the 40 planned. The interviews passed. The price page failed, 3 of 6. The employers page passed: two employers paid for their staff's plans.
- **Grocers:** 0 paying, of the 2 planned. The first offer was spoiled by the suspension, and the second, in February, failed.
- **The suspension:** 8 to 21 January, for family matters, recorded on 22 January.

You ask which variant did best, and the person names households. You ask what they decide for it. They want to pivot toward employers, in their words "Parents will not pay alone, but their employers will". Asked for your view, you say the pivot rests on two employers so far, a thin base, and that persevering on the missed objective would draw a warning. They keep the pivot. You run the command without the flag, show them its question, and on their confirmation run:

```
pkit lean review-cycle meal-plan--first --reached 26 --reached 0 --winning meal-plan--households --decision pivot --reasons "Parents will not pay alone, but their employers will" --evidence meal-plan--parent-interviews --evidence meal-plan--price-page --evidence meal-plan--employers-page --person-decided
```

Then, one question at a time, the person shelves `meal-plan--grocers` because "no grocer paid in two offers", and keeps the goal as it is. With them, in their words, you rewrite the households' segments and price around employers. The person judges the variant again and shortlists it again, and you plan the next cycle together.
