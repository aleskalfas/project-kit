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
- **Suggest a length, and say what bears on it.** Ninety days suits someone working on it most days. A person giving evenings and weekends may need longer. A known absence is sized into the window now. Recommend one, and ask how long they want the window to be.
- **Say what happens at its end.** Time that runs out goes to the review, which may persevere into another cycle on the same key results. Only an absence life brings later is recorded as a suspension (`suspend.md`).

## 2. Draft the plan

Offer a draft of each part, with your recommendation where you see more than one way, and ask the person for each. They take it, change it, or give their own:

- **The variants** the cycle explores: shortlisted, one or several.
- **The start:** a day not yet reached, so the plan can still change. Experiments can be declared from the day it is planned.
- **The objective:** one sentence of what the cycle sets out to show, in the person's words.
- **The key results:** each a number to reach at a step of the customer factory, taken from the traction target of a variant it explores. Each explored variant needs at least one. Take what of each variant's first stage the window can hold, the whole of it where the stage fits the window.
- **The constraint:** the one step of the customer factory the cycle works on, the weakest, with the evidence that it is. Before any customer has come in, it is acquisition.

## 3. Record it

Show the whole plan, and take it as the dispatcher's "Asking a judgement" says: ask whether it stands, run the command without the flag to show its question, and on the person's confirmation run:

```
pkit lean plan-cycle <idea>--<cycle> --variant <variant> [--variant <variant>]... --start <day> [--days <n>] --objective "<text>" --key-result <variant>:<step>:<target> [--key-result ...]... --constraint-step <step> --constraint-evidence "<text>" --person-decided
```

## 4. Changing the plan before it starts

While the cycle is planned, the person may change any part. Each part given replaces that part whole, and the rest stays:

```
pkit lean change-plan <cycle> [plan-cycle's flags] --person-decided
```

It is the person's act, asked as the first plan was. A start moved by a change stays a day not yet reached. The one exception is the day the cycle was first planned: a change that day is part of the planning, and may move the start to that day. Once the window starts, the plan is frozen (DEC-002 point 11).

## What follows

The cycle starts running on its first day, with nobody acting, and reaches its review when its window ends, as worked out. In between, declare its experiments (`experiment.md`). Nothing is declared in a cycle that is suspended or in review (DEC-003 point 7).

## Example

You ask how much time the person can give. Eight hours a week, mostly evenings, and no absence known. You suggest 150 days, since eight hours a week is little time for two variants. The person sets 120: they want the cycle decided by spring. You draft the key results as the whole first stage of each variant, 40 households back for a second planned week and 2 grocers paying for a trial month, since each stage was sized to a few months, and they take them. Nobody has been reached yet, so you draft the constraint as acquisition. You draft an objective, and they reword it in their own words. The plan stands. You show the command's question, and on their confirmation run:

```
pkit lean plan-cycle meal-plan--first --variant households --variant grocers --start 2026-12-01 --days 120 --objective "Show that households come back for planned weeks, and that grocers pay to be in them" --key-result households:retention:40 --key-result grocers:revenue:2 --constraint-step acquisition --constraint-evidence "No household or grocer has been reached yet" --person-decided
```

The window runs from 1 December 2026 to 30 March 2027, unless a suspension moves its end.
