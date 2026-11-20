# Suspending and resuming a cycle

A *suspension* is a stretch in which the person's life, not the work, stopped a cycle (DEC-001 point 7). Its days count toward no window, so the cycle gets back the days it had left. A window is never extended for any other reason (DEC-003 point 4). Suspending is the person's act, and resuming is the person's move.

## When a suspension fits

- **Life stopped the work:** illness, family, a job's crunch, travel. Results that disappoint are no reason, and time that simply ran out goes to the review.
- **A cycle running, or one in review** whose window ran out while the person was away (DEC-003 point 4).
- **From today or earlier.** An absence still to come is recorded when it begins, or on return. One known when planning was sized into the window.
- **The whole cycle.** No experiment is suspended alone.

## 1. Ask, and say what it would do

Ask the person whether life stopped the work, since which day they were away, and whether they are back, and since which day. The days are their word. Then say what recording it would do (DEC-002 point 12):

- **The window:** its end moves later by the days the suspension covers.
- **An experiment not yet started** by the first day away moves with it, by the days covered from its start on.
- **An experiment already running** keeps its dates, since the world went on answering it. It comes due on its end, and its result waits for the person.
- **No day with recorded work** can be covered. A suspension gives back only days on which nothing on the cycle was recorded.

## 2. Record it

Run the command without the flag to get its question, ask it, and on their yes run one of these.

- **The absence is over,** the usual case on return. Record it whole, its first day and the day the cycle resumed, which counts again:

  ```
  pkit lean suspend <cycle> --reason "<their reason>" --since <first day away> --resumed <day back> --person-decided
  ```

- **The person is leaving now,** and the absence goes on:

  ```
  pkit lean suspend <cycle> --reason "<their reason>" --since <day> --person-decided
  ```

The command refuses a suspension that breaks its rules, and says which. Such are a first day outside the window or ahead of today, a covered day with recorded work, or one that would make an act already recorded read as refused. Read the reason to the person, and ask for other days. Never record around it.

## 3. While the cycle is suspended

- **Nothing is recorded on it but resuming:** no declaration, estimate, stopping rule, result or decision (DEC-003 point 4).
- **Drafts may still be written,** and the commands warn.
- **The desk is not the cycle's,** so canvases may still be judged.

## 4. Resume it

When the person is back, ask on which day they resumed, today unless they name an earlier one. On their answer:

```
pkit lean resume <cycle> [--on <day>] --person-decided
```

It goes back to running, or into review where the window, moved by the suspension, ended before today. Then take what came due while they were away (`result.md`). Where the absence spoiled a result, it is recorded as spoiled there.

## Example

The person was away from 8 January 2027 and came back on 22 January, as `return.md` found. You tell them what it would do. The window's end moves from 30 March to 13 April. The clubs page, declared to start on 11 January, has not started, so it moves to start on 22 January. The cafés offer, running since 4 January, keeps its dates, and came due when it ended on the 17th. They answer yes:

```
pkit lean suspend board-game--first --reason "Family matters" --since 2027-01-08 --resumed 2027-01-22 --person-decided
```

The cycle is running again, and the cafés offer waits for its result.
