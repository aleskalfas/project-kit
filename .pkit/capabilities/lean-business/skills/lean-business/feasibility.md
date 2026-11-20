# Judging a variant's feasibility

Feasibility asks whether the first stage of the variant's growth can be reached. It is not whether the product can be built. It is whether the person can get from nothing to the first stage's target, with the channels on the canvas and the time they have. The step comes after viability has a yes, and needs the traction target (DEC-003 point 2).

## 1. Set the traction target

The traction target splits the goal into yearly steps.

- **The multiplier:** how many times the active customers grow each year on the way to the goal. Ten is the default. A lower one means a slower climb with more customers needed early.
- **The first stage's target:** a step of the customer factory and the number to reach there, such as paying customers, the step `revenue`. A natural first target is the first year's number on the way, as the estimate works it out.

Read the year-by-year numbers from `pkit lean estimate <variant>`, propose a first target from them, and let the person set it:

```
pkit lean set-traction <variant> [--multiplier <n>] --first-stage-metric acquisition|activation|retention|revenue|referral --first-stage-target <n>
```

The traction target is content, and a change to it makes the verdicts that judged it stale. The key results of a cycle are later taken from it (`plan-cycle.md`).

## 2. The verdict

Help the person see what the first stage asks:

- **The first customers.** Where would the first target's customers come from, through which early channel?
- **The person's time.** How many hours a week can they give, and is that enough to reach the target in the first year?
- **What comes first.** What must exist before a first customer pays, and can it be shown or sold before it is built?

Then take the verdict as every verdict is taken:

1. Run `pkit lean judge <variant> feasibility yes` without the flag, which prints the process's question.
2. Set out what you found, and say which way you lean.
3. Ask, and wait for the person's yes or no, with a sentence of why.
4. Record their answer:

   ```
   pkit lean judge <variant> feasibility yes|no --note "<their reason>" --person-decided
   ```

A yes moves the variant to feasible, and the person may shortlist it (`outcome.md`). A no moves nothing, and the target or the canvas is revised.

## Example

The estimate of `board-game--hosts` gives 25 active hosts in the first year, 250 in the second and 2,500 in the third. You propose the first year's number as the first stage's target, counted at the step where hosts pay. The person agrees:

```
pkit lean set-traction board-game--hosts --multiplier 10 --first-stage-metric revenue --first-stage-target 25
```

You ask where 25 paying hosts would come from. The person knows two forums and six hosts in person, and can give eight hours a week. You lean to a yes, since the early channels are within their reach. They answer yes:

```
pkit lean judge board-game--hosts feasibility yes --note "Two forums and six hosts I know can bring the first 25" --person-decided
```

For `board-game--venues`, the first stage is 2 paying cafés. The person knows the owners of three, and answers yes.
