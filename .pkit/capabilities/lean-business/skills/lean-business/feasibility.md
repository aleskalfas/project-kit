# Judging a variant's feasibility

Feasibility asks whether the first stage of the variant's growth can be reached. It is not whether the product can be built. It is whether the person can get from nothing to the first stage's target, with the channels on the canvas and the time they have. The step comes after viability has a yes, and needs the traction target (DEC-003 point 2).

## 1. Set the traction target

The traction target splits the goal into steps on the way.

- **The multiplier:** how many times the active customers grow each year on the way to the goal. Ten is the default. A lower one means a slower climb with more customers needed early.
- **The first stage's target:** a step of the customer factory and the number to reach there. The first stage spans a few months, not a year, so scale the target to what those months can hold. It need not be the first year's number of paying customers: it may count an earlier step, or a first form of paying, such as leads gathered, trials begun or preorders taken.

Read the year-by-year numbers from `pkit lean estimate <variant>`, propose a first target the stage's few months can hold, and let the person set it:

```
pkit lean set-traction <variant> [--multiplier <n>] --first-stage-metric acquisition|activation|retention|revenue|referral --first-stage-target <n>
```

The traction target is content, and a change to it makes the verdicts that judged it stale. The key results of a cycle are later taken from it (`plan-cycle.md`).

## 2. The verdict

Help the person see what the first stage asks:

- **The first customers.** Where would the first target's customers come from, through which early channel?
- **The person's time.** How many hours a week can they give, and is that enough to reach the target within the stage?
- **What comes first.** What must exist before a first customer pays, and can it be shown or sold before it is built?

Then take the verdict as the dispatcher's "Asking a judgement" says:

1. Set out what you found.
2. Ask the person's verdict, yes or no, with a sentence of why in their words. Give your own lean once they have answered, or when they ask.
3. Run the command with their answer and their note, first without the flag, showing them its question, and on their confirmation with it:

   ```
   pkit lean judge <variant> feasibility yes|no --note "<their words>" --person-decided
   ```

A yes moves the variant to feasible, and the person may shortlist it (`outcome.md`). A no is recorded, moves nothing, and the target or the canvas is revised.

## Example

The estimate of `meal-plan--households` gives 25 active households in the first year, 250 in the second and 2,500 in the third. You propose a first stage the next few months can hold, at a step before paying: 30 households that try a planned week and come back for a second, the step `retention`. The person raises it to 40, since their two parents' groups hold some sixty parents:

```
pkit lean set-traction meal-plan--households --multiplier 10 --first-stage-metric retention --first-stage-target 40
```

You ask where 40 such households would come from. The person names the two groups and the newsletter at their workplace, and can give eight hours a week. You ask for their verdict. They answer yes, in their words "the two groups and the newsletter can bring forty households to try it". You confirm it through the command's question, and run:

```
pkit lean judge meal-plan--households feasibility yes --note "The two groups and the newsletter can bring forty households to try it" --person-decided
```

For `meal-plan--grocers`, the first stage is 2 grocers paying for a trial month, at the step `revenue`. The person knows the owners of three, and answers yes.
