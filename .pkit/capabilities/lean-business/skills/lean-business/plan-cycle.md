# Planning a cycle

A *cycle* is the window in which the experiments on one or more shortlisted variants run toward the idea's goal, ending in a review (DEC-001 point 7). An idea runs one cycle at a time. The plan holds the variants it explores, its window, an objective with key results, and one constraint (DEC-002 point 11). The plan is the person's act.

## Before you start

- **The goal is set** (`goal.md`).
- **The variants to explore are shortlisted,** and no shortlisting is stale (`outcome.md`).
- **No other cycle of the idea is undecided.** The next is planned once the last review is decided.
- **The assumptions are ranked** (`assumptions.md`), so the plan is made knowing what will be tested first.

## 1. Size the window

The window is the cycle's time box. It is sized now, to the time the person can give, and never extended once it starts (DEC-003 point 4).

- **Ask** how many hours a week they can give, and whether any absence is already known.
- **Propose a length.** Ninety days suits someone working on it most days. A person giving evenings and weekends may need longer. Size a known absence into the window now.
- **Say what happens at its end.** Time that runs out goes to the review, which may persevere into another cycle on the same key results. Only an absence life brings later is recorded as a suspension (`suspend.md`).

## 2. Draft the plan

Draft each part with the person:

- **The variants** the cycle explores: shortlisted, one or several.
- **The start:** a day not yet reached, so the plan can still change. Experiments can be declared from the day it is planned.
- **The objective:** one sentence of what the cycle sets out to show.
- **The key results:** each a number to reach at a step of the customer factory, taken from the traction target of a variant it explores. Each explored variant needs at least one. Propose a share of each variant's first stage that the window can hold.
- **The constraint:** the one step of the customer factory the cycle works on, the weakest, with the evidence that it is. Before any customer has come in, it is acquisition.

## 3. Record it

Show the whole plan. Run the command without the flag to get its question, ask it, and on the person's yes run:

```
pkit lean plan-cycle <idea>--<cycle> --variant <variant> [--variant <variant>]... --start <day> [--days <n>] --objective "<text>" --key-result <variant>:<step>:<target> [--key-result ...]... --constraint-step <step> --constraint-evidence "<text>" --person-decided
```

The command refuses a variant not shortlisted, an idea with no goal, a second undecided cycle, an explored variant without a key result, and a window that overlaps another cycle's.

## 4. Changing the plan before it starts

While the cycle is planned, the person may change any part. Each part given replaces that part whole, and the rest stays:

```
pkit lean change-plan <cycle> [plan-cycle's flags] --person-decided
```

It is the person's act, asked as the first plan was. It is refused once the window has started, for a start moved to today or before, and for a change that drops a variant an experiment tests. Once the window starts, the plan is frozen.

## What follows

The cycle starts running on its first day, with nobody acting, and reaches its review when its window ends, as worked out. In between, declare its experiments (`experiment.md`). Nothing is declared in a cycle that is suspended or in review (DEC-003 point 7).

## Example

The person can give eight hours a week, mostly evenings. You propose 120 days rather than 90, which they accept. For the key results, you propose ten of the first stage's 25 paying hosts, and both of its 2 paying cafés. Nobody has been reached yet, so the constraint is acquisition. The person answers yes to the whole plan:

```
pkit lean plan-cycle board-game--first --variant hosts --variant venues --start 2026-12-01 --days 120 --objective "Show that hosts and cafés pay for game nights organised through the platform" --key-result hosts:revenue:10 --key-result venues:revenue:2 --constraint-step acquisition --constraint-evidence "No host or café has been reached yet" --person-decided
```

The window runs from 1 December 2026 to 30 March 2027, unless a suspension moves its end.
