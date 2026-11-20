# Judging a variant's viability

Viability asks whether the variant's model can reach the idea's goal. A rough estimate, worked out in minutes, runs the goal through the customer factory (DEC-002 point 4). It shows how many customers the goal needs, how many leave each year, and how many leads it takes to win them. Its numbers are never stored. They are worked out from the goal and the canvas's inputs each time.

The step comes after desirability has a yes, and judges the idea's goal, the revenue streams and the estimate's inputs (DEC-003 point 2).

## Before you start

- **The goal is set.** Viability judges the variant against it. Where none is, take `goal.md` first.
- **A revenue stream is on the canvas.** The step cannot be judged without one.

## 1. Give the estimate its inputs

The inputs are the person's guesses, so ask for each, one side at a time in a model with several, and write the number they give, never one of yours. The file holds each as a plain number, and nothing in it marks it as a guess: the inputs the estimate rests on most become the variant's assumptions (step 3), where their risk is ranked and tested.

- **The price:** what the business keeps from one active customer, on average, each month or year, in the idea's currency.
  - A one-off sale counts what a customer pays over their lifetime, spread over that lifetime.
  - A marketplace's side counts what the business keeps from it, not what flows through it.
  - A side that pays nothing counts at nothing.
- **The lifetime:** how long a customer stays, in months or years.
- **The conversion:** the share of the people reached who become customers.
- **The referral share:** the share of new customers who come because another sent them.

Write them as they are given:

```
pkit lean set-inputs <variant> [--side <side>] --price <amount> month|year --lifetime <length> month|year --conversion <share> --referral-share <share>
```

What turns a pricing into the price, such as how often a customer buys, or the share kept of a sale, is itself a guess. Note it for the variant's assumptions (`assumptions.md`).

## 2. Work out the estimate, and read it with the person

```
pkit lean estimate <variant>
```

Read each number to the person in plain words, for each side that pays:

- **A year's revenue from one customer,** and so **the active customers** the goal needs.
- **The customers lost each year** as their lifetime runs out, and as many won to replace them.
- **Those won by referral,** and the rest won through the channels.
- **The leads needed each year** to win the rest.
- **The active customers on the way,** year by year, growing by the traction multiplier.

Where an input is missing, the estimate names it, and works out the numbers that rest on none. Ask the person for it, and run the estimate again.

## 3. Find what breaks it

Ask the person which input, if it were a little worse, would put the goal out of reach. Work a what-if out in the conversation, from the formulas in the README. Change an input only when the person's belief about it changed, since a change makes the verdicts that judged it stale.

The inputs that break the estimate, and the ones that would mend it, are the variant's first risky assumptions. Offer to write them now with `add-assumption --input` (`assumptions.md`).

## 4. The verdict

Whether each number is within reach is the person's judgement, not the command's. Help them ask it against the channels on the canvas and the time they have. For example: can those channels bring that many leads in a year? Is that lifetime what they see among such customers?

Take it as the dispatcher's "Asking a judgement" says:

1. Set out the numbers and what breaks them.
2. Ask the person's verdict, yes or no, with a sentence of why in their words. Give your own lean once they have answered, or when they ask.
3. Run the command with their answer and their note, first without the flag, showing them its question, and on their confirmation with it:

   ```
   pkit lean judge <variant> viability yes|no --note "<their words>" --person-decided
   ```

A yes moves the variant to viable, and you go on to `feasibility.md`. A no is recorded, moves nothing, and the canvas or the inputs are revised. A goal changed later makes the verdict stale (DEC-002 point 13).

## Example

For `meal-plan--households`, you ask for each input. The person gives a price of 8 EUR a month, a lifetime of two years, a conversion of 5% and a referral share of 20%:

```
pkit lean set-inputs meal-plan--households --price 8 month --lifetime 2 year --conversion 0.05 --referral-share 0.2
pkit lean estimate meal-plan--households
```

You read it to them. A household brings 96 EUR a year, so the goal of 240,000 EUR needs 2,500 active households. With a lifetime of two years, 1,250 leave each year, and as many must be won. Referrals bring 250 of them, and the channels the other 1,000. At a conversion of 5%, that is 20,000 households reached each year, about 55 a day. On the way, the variant needs 25 households in its first year and 250 in its second.

You ask which input they trust least. The person names the lifetime: families they know drop such plans after a few months. You work it out with them: at a lifetime of one year, 2,500 leave each year, the channels must win 2,000, and 40,000 households must be reached. The person thinks the parents' groups and their workplaces could reach 20,000, not 40,000, so the lifetime is the leap of faith. You offer to write it as an assumption, and the conversion with it, and they agree.

You ask for their verdict. They answer yes, in their words "reachable if families stay two years, and that is what we test first". You confirm it through the command's question, and run:

```
pkit lean judge meal-plan--households viability yes --note "Reachable if families stay two years, and that is what we test first" --person-decided
```

For `meal-plan--grocers`, the cooks' side pays nothing and the shops' side 200 EUR a month. The goal needs 100 grocers. The person judges that within reach across their region, and answers yes.
