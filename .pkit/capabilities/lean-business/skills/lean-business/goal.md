# Setting the idea's goal

An idea has one goal, which every variant's viability and feasibility is judged against. It is the least the business must earn to be worth the person's next years (DEC-002 point 3). It names a recurring revenue, each month or year, in the idea's currency, and the years to reach it in. It sits above the variants, so that no variant's story bends it.

Set it before any variant's viability is judged. The person may set it first, or after the first sketch.

## 1. Before the first write

A first goal creates the idea's folder. So for a new idea, the location, who may read the idea and its id are settled first, as the dispatcher's "A new idea" says.

## 2. Ask for the goal

The goal is the person's own measure of success, so ask for each part of it, and propose none, the span included. Help them reach it with questions such as:

- **The amount:** what yearly revenue would make this worth leaving other work for, or worth keeping up beside it?
- **The span:** in how many years would they need to see it?
- **The currency:** which currency do they think in? It is the unit of every sum the idea holds, and no sum is converted.

A goal is counted as revenue that recurs. A one-off price is spread over a customer's life when its inputs are given (`viability.md`), so the goal stays one figure for every kind of model.

## 3. Record it

The goal is the person's act, taken as the dispatcher's "Asking a judgement" says: with their figures, run the command without the flag, show them the question it prints, and on their confirmation run it again with the flag:

```
pkit lean set-goal <idea> --revenue <amount> --per month|year --currency <code> --years <n> --person-decided
```

A first goal needs every flag, and creates the idea's folder where none is.

## 4. Changing it later

The goal changes only while none of the idea's cycles is planned, running or suspended (DEC-002 point 3). That is before the first cycle is planned, and after it, in the method's rhythm, at a cycle's review: from the end of its window, while it is in review or once it is decided, until the next cycle is planned.

- **The currency stays** while a declared experiment is undecided, since its sums were declared in it (DEC-002 point 3).
- **A change makes stale** each viability and feasibility verdict, and each shortlisting, that used the goal. The command names each one. Offer to judge them again (`viability.md`, `feasibility.md`, `outcome.md`), since no experiment rests on a stale shortlisting.
- **Give only what changes.** `set-goal` takes the flags that change, and keeps the rest.

## Example

The person starts `meal-plan`, the location, its privacy and its id settled. You ask what yearly revenue would make the service worth their evenings for the next years, in how many years, and in which currency. They answer 240,000 EUR a year, within three years. You run the command with those figures and without the flag, and show them the question it prints. They confirm, and you run:

```
pkit lean set-goal meal-plan --revenue 240000 --per year --currency EUR --years 3 --person-decided
```

The command creates `lean-business/meal-plan/` with its `goal.yaml`, and records the location.
