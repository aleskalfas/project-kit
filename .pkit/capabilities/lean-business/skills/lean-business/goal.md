# Setting the idea's goal

An idea has one goal, which every variant's viability and feasibility is judged against. It is the least the business must earn to be worth the person's next years (DEC-002 point 3). It names a recurring revenue, each month or year, in the idea's currency, and the years to reach it in. It sits above the variants, so that no variant's story bends it.

Set it before any variant's viability is judged. The person may set it first, or after the first sketch.

## 1. Where the ideas live, before the first idea

The ideas live in `lean-business/` at the repository's root, one folder for each idea, unless the project records another folder (DEC-002 point 1).

- **Ask once,** before the first idea, whether that folder suits the person.
- **For another folder,** run `pkit lean set-location <path>`. Running it is the consent, so run it only on their answer.
- **For the default,** do nothing. The first command that writes records it, and says so.

The idea's files are as public as the repository. Where the person wants the idea private, say so before the first write: it belongs in a private repository.

## 2. Ask for the goal

The goal is the person's own measure of success, so ask for it rather than proposing one. Help them reach it with questions such as:

- **The amount:** what yearly revenue would make this worth leaving other work for, or worth keeping up beside it?
- **The span:** in how many years would they need to see it? Three is a common span.
- **The currency:** which currency do they think in? It is the unit of every sum the idea holds, and no sum is converted.

A goal is counted as revenue that recurs. A one-off price is spread over a customer's life when its inputs are given (`viability.md`), so the goal stays one figure for every kind of model.

## 3. Record it

The goal is the person's act. Run the command without the flag to get its question, put the question to the person with the figures they gave, and on their yes run:

```
pkit lean set-goal <idea> --revenue <amount> --per month|year --currency <code> --years <n> --person-decided
```

A first goal needs every flag, and creates the idea's folder where none is.

## 4. Changing it later

The goal changes only between cycles: while none of the idea's cycles is planned, running or suspended (DEC-002 point 3). In the method's rhythm, that is after a cycle's review is decided.

- **The command refuses** a change while a cycle is planned, running or suspended, and a change of currency while a declared experiment is undecided.
- **A change makes stale** each viability and feasibility verdict, and each shortlisting, that used the goal. The command names each one. Offer to judge them again (`viability.md`, `feasibility.md`, `outcome.md`), since no experiment rests on a stale shortlisting.
- **Give only what changes.** `set-goal` takes the flags that change, and keeps the rest.

## Example

The person starts `board-game`. You ask whether `lean-business/` at the root suits them, and they say yes. You ask what yearly revenue would make the platform worth their evenings for the next years. They answer 120,000 EUR a year, within three years. You show the question the command printed with those figures, they say yes, and you run:

```
pkit lean set-goal board-game --revenue 120000 --per year --currency EUR --years 3 --person-decided
```

The command creates `lean-business/board-game/` with its `goal.yaml`, and records the location.
