# Judging a variant's viability

Viability asks whether the variant's model can reach the idea's goal. A rough estimate, worked out in minutes, runs the goal through the customer factory (DEC-002 point 4). It shows how many customers the goal needs, how many leave each year, and how many leads it takes to win them. Its numbers are never stored. They are worked out from the goal and the canvas's inputs each time.

The step comes after desirability has a yes, and judges the idea's goal, the revenue streams and the estimate's inputs (DEC-003 point 2).

## Before you start

- **The goal is set.** Viability judges the variant against it. Where none is, take `goal.md` first.
- **A revenue stream is on the canvas.** The step cannot be judged without one.

## 1. Give the estimate its inputs

Ask the person for each input, one side at a time in a model with several. Each is a guess, and is marked as one.

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

Where an input is missing, the estimate names it, and works out the numbers that rest on none. Give it, and run the estimate again.

## 3. Find what breaks it

Ask which input, if it were a little worse, would put the goal out of reach. Work a what-if out in the conversation, from the formulas in the README. Change an input only when the person's belief about it changed, since a change makes the verdicts that judged it stale.

The inputs that break the estimate, and the ones that would mend it, are the variant's first risky assumptions. Offer to write them now with `add-assumption --input` (`assumptions.md`).

## 4. The verdict

Whether each number is within reach is the person's judgement, not the command's. Ask it against the channels on the canvas and the time the person has. For example: can those channels bring that many leads in a year? Is that lifetime what they see among such customers?

1. Run `pkit lean judge <variant> viability yes` without the flag, which prints the process's question.
2. Set out the numbers and what breaks them, and say which way you lean.
3. Ask, and wait for the person's yes or no, with a sentence of why.
4. Record their answer:

   ```
   pkit lean judge <variant> viability yes|no --note "<their reason>" --person-decided
   ```

A yes moves the variant to viable, and you go on to `feasibility.md`. A no moves nothing, and the canvas or the inputs are revised. A goal changed later makes the verdict stale (DEC-002 point 13).

## Example

For `board-game--hosts`, the person gives a price of 4 EUR a month, a lifetime of two years, a conversion of 4% and a referral share of 20%:

```
pkit lean set-inputs board-game--hosts --price 4 month --lifetime 2 year --conversion 0.04 --referral-share 0.2
pkit lean estimate board-game--hosts
```

You read it to them. A host brings 48 EUR a year, so the goal of 120,000 EUR needs 2,500 active hosts. With a lifetime of two years, 1,250 leave each year, and as many must be won. Referrals bring 250 of them, and the channels the other 1,000. At a conversion of 4%, that is 25,000 hosts reached each year, about seventy a day. On the way, the variant needs 25 hosts in its first year and 250 in its second.

You ask what would break it. At 2% conversion, the leads double to 50,000 a year. The person thinks the forums could bring 25,000, not 50,000, so the conversion is the leap of faith. You add it as an assumption, and the lifetime with it. The person answers yes, and you record:

```
pkit lean judge board-game--hosts viability yes --note "Forums could bring 25,000 hosts a year, if 4% pay" --person-decided
```

For `board-game--venues`, the players' side pays nothing and the cafés' side 60 EUR a month. The goal needs 167 cafés. The person judges that within reach across the country, and answers yes.
