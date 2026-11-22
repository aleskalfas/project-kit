# Coming back to an idea

A person may leave an idea for a day or for months. This sub-procedure opens every session on an idea, and is the whole of it after a long silence. The files alone say where things stand, so neither the person's memory nor yours is needed (DEC-001 point 10).

## 1. Read the briefing

Run the status, first for every idea, then for the one the person works on:

```
pkit lean status
pkit lean status <idea>
```

- **Without an idea,** it gives one line for each: whether it has a goal, its variants by where they stand, whether it is dropped, and how many things wait on the person.
- **With one,** it gives the briefing: whether the idea is dropped, the goal, each cycle, variant and experiment with where it stands, each assumption with its outcome, the canvas of each variant in play, and what waits on the person, each with the command that takes it. Its layout is the README's.
- **`--json`** prints its structured form, which you may read for exact values. Show the person the plain form.

Read the briefing before you propose anything. You and the person then start from one account of where things stand.

Where the person brings an idea the status does not list, nothing waits yet. Settle the three things the dispatcher's "A new idea" names before anything is written, then start from the goal or the sketch.

## 2. Offer to record a long silence, first

After a long silence, the briefing first offers to record the gap as a suspension of the cycle. The README gives how long a silence must be. Take this offer before any other work, since a suspension covers no day on which work on the cycle was recorded (DEC-002 point 12).

1. **Say what it offers.** The suspension would start on the day after the person's last recorded act on the cycle. Say what it would do to the window's end, as the briefing gives it.
2. **Ask whether life stopped the work.** A silence while an experiment ran is usually the wait for its result, not an absence: nothing was recorded because nothing was due yet. Say so as you ask, so the offer reads as a question and not as a guess that they were away. Only the person knows whether the silence was time away, or work the files do not show (DEC-001 point 10). Where they were away, ask on which day they were first away, and on which day they came back.
3. **On their yes,** record it through `suspend.md`. On their no, record nothing, and go on to where things stand.

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

Ask one question at a time. Where the person wants to stop after one item, stop: the rest keeps. Before the session ends, suggest that they commit the idea's files (the dispatcher, "Ending a session").

## Example

The person last worked on `meal-plan` on 7 January 2027, when they declared the employers page. They come back on 28 January, after three weeks of silence. The briefing opens with its offer, in words like these:

> Nothing has been recorded on `meal-plan--first` since 2027-01-07. If you were away, the gap can be recorded as a suspension from 2027-01-08, which would move the window's end, 2027-03-30, later by the days you were away: to 2027-04-19, were you back today.

You say that the gap may be no more than the wait for the grocers offer, which ran until the 17th, and ask whether they were away. They were: from the 8th, in their words "for family matters", and they came back today. You record it through `suspend.md`. The window's end moves to 19 April, and the employers page, which had not started, now starts today.

Then you tell them the rest. The grocers offer ran from 4 to 17 January and is due: it expected at least 2 grocers to pay for a trial month, and waits for its result. The employers page runs from today for fourteen days. The window is on its day 39 of 120, the days away not counted. What waits first is the grocers offer's result, so you open `result.md`.
