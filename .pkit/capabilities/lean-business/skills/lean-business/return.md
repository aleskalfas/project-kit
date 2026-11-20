# Coming back to an idea

A person may leave an idea for a day or for months. This sub-procedure opens every session on an idea, and is the whole of it after a long silence. The files alone say where things stand, so neither the person's memory nor yours is needed (DEC-001 point 10).

## 1. Read the briefing

Run the status, first for every idea, then for the one the person works on:

```
pkit lean status
pkit lean status <idea>
```

- **Without an idea,** it gives one line for each: whether it has a goal, its variants by where they stand, and how many things wait on the person.
- **With one,** it gives the briefing: the goal, each variant, cycle and experiment with where it stands, and what waits on the person, each with the command that takes it. Its layout is the README's.
- **`--json`** prints its structured form, which you may read for exact values. Show the person the plain form.

Read the briefing before you propose anything. You and the person then start from one account of where things stand.

## 2. Offer to record a long silence, first

After a long silence, the briefing first offers to record the gap as a suspension of the cycle. The README gives how long a silence must be. Take this offer before any other work, since a suspension covers no day on which work on the cycle was recorded (DEC-002 point 12).

1. **Say what it offers.** The suspension would start on the day after the person's last recorded act on the cycle. Say what it would do to the window's end, as the briefing gives it.
2. **Ask whether life stopped the work.** Only the person knows whether the silence was time away, or work the files do not show (DEC-001 point 10). Ask on which day they were first away, and on which day they came back.
3. **On their yes,** record it through `suspend.md`. On their no, record nothing, and say that the window's days were spent.

It is an offer, never an act. Never record a gap because the dates suggest one.

## 3. Walk the person through where things stand

Tell it in this order, in plain words:

1. **Their last act,** and its day.
2. **The plan:** the goal, and the cycle's objective, key results and constraint, with how far each has come.
3. **What runs and is unfinished:** each experiment with its days. Set each declared expectation beside the result it waits for, so the person reads the expectation fixed before the run, not the one memory gives.
4. **What waits on them,** in the briefing's order, what others wait on first.

Say plainly what moved while they were away: an experiment whose time box ended is now due, and a cycle whose window ended is in review. Nothing was decided for them.

## 4. Take what waits, one at a time

For each item, open the sub-procedure its command leads to, and take it as that sub-procedure says. Such items are:

| What waits | Sub-procedure |
|---|---|
| A goal to set | `goal.md` |
| A variant's next desk step to judge | `desirability.md`, `viability.md` or `feasibility.md` |
| A feasible variant to shortlist, or a stale shortlisting to take again | `outcome.md` |
| A shortlisted variant no cycle explores yet | `plan-cycle.md` |
| A draft to declare | `experiment.md` |
| A due experiment's result and next action | `result.md` |
| A suspended cycle to resume | `suspend.md` |
| A cycle in review | `review.md` |

Ask one question at a time. Where the person wants to stop after one item, stop: the rest keeps.

## Example

The person last worked on `board-game` on 7 January 2027, when they declared the clubs page. They come back on 22 January. The briefing opens with its offer, in words like these:

> Nothing has been recorded on `board-game--first` since 2027-01-07. If you were away, the gap can be recorded as a suspension from 2027-01-08, which would move the window's end, 2027-03-30, later by the days you were away.

You ask whether they were away, and since when. They say they were away from the 8th, for family reasons, and came back today. You record it through `suspend.md`. The window's end moves to 13 April, and the clubs page, which had not started, now starts today.

Then you tell them the rest. The cafés offer ran from 4 to 17 January and is due: it expected at least 2 cafés to pay for a listing, and waits for its result. The clubs page runs from today for fourteen days. The window has run 38 of its 120 days. What waits first is the cafés offer's result, so you open `result.md`.
