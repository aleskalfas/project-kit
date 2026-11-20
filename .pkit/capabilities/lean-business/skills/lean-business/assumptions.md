# Drawing and ranking a variant's assumptions

An *assumption* is something the model takes for granted that no evidence supports yet: a leap of faith (DEC-001 point 7). Each comes from an entry of the canvas, or from an input of the estimate. The method tests the riskiest first, not the easiest, so the list is ranked by risk, and the ranking is the person's (DEC-002 point 8).

Draw them once a variant has passed the desk, or as the estimate shows what breaks it (`viability.md`). Rank them before the first experiment on the variant.

## 1. Find them

Look for the beliefs the model stands on. Most live in a few places:

- **The customer side:** the early adopters' trigger, the top problem and its alternative, and the value proposition. Would the early adopters feel the problem, and switch for the promise?
- **The estimate's inputs:** the price, the lifetime, the conversion and the referral share. Those that break the goal when a little worse are the first to draw.
- **Reaching customers:** the early channels, and the first stage's target.
- **What turns a pricing into the price,** such as how often a customer buys, or the share kept of a sale (DEC-002 point 4).

## 2. Write each as a belief that could turn out false

A good statement names who does what, in a way an experiment could later show wrong. It holds one belief, and speaks of what people do rather than what they say.

- **Too vague:** "People like board games."
- **Testable:** "Hosts of regular game nights lose at least an hour a month settling dates."

Give its kind, the desk step whose risk it carries: `desirability`, `viability` or `feasibility`. Then write it, from the entry or the input it comes from:

```
pkit lean add-assumption <variant> "<statement>" --kind desirability|viability|feasibility --entry <entry>
pkit lean add-assumption <variant> "<statement>" --kind viability --input price|lifetime|conversion|referral-share [--side <side>]
```

Each is content. The command gives its id, and places it one past the highest rank, which judges nothing. Show the person the list as it stands.

- **To change one:** `edit-assumption <assumption>`, which keeps its id, and warns where a declared experiment tests it.
- **To remove one:** `remove-assumption <assumption>`, refused while an experiment tests it.

## 3. Rank them, with the person

Propose an order, the riskiest first, with a sentence for each place. Weigh two things together:

- **How likely it is wrong,** given what the person knows today.
- **How much of the model falls with it.** A belief the whole canvas rests on, such as the top problem, outranks one that a change of price could mend.

Customer risks usually come before technical ones: whether people want it before whether it can be built. An assumption that cannot be tested until later still takes its place by risk.

The order is the person's. Ask whether it stands, or how they would change it. On their answer, run the ranking as they gave it:

```
pkit lean rank <variant> <assumption> <assumption> ... --person-decided
```

The assumptions named take the first ranks, in the order given. Those left out follow as they were ranked. A rank keeps no fingerprint, so the person may change it whenever they learn something.

## 4. Read where each stands

An assumption stores no state of its own. Whether it is untested, being tested, supported, refuted or inconclusive follows from the experiments that test it, and is worked out each time (DEC-003 point 8). Read it from the status, never from memory.

## Example

For `board-game--hosts`, you propose four assumptions, and write them as the person agrees each statement:

```
pkit lean add-assumption board-game--hosts "Hosts of regular game nights lose at least an hour a month settling dates" --kind desirability --entry dates-take-messages --id dates-cost-hours
pkit lean add-assumption board-game--hosts "Four in a hundred hosts reached will pay 4 EUR a month" --kind viability --input conversion --id four-percent-pay
pkit lean add-assumption board-game--hosts "Board-game forums reach hosts who would pay" --kind feasibility --entry forums --id forums-reach-hosts
pkit lean add-assumption board-game--hosts "A paying host stays for two years" --kind viability --input lifetime --id two-year-hosts
```

You propose the order as written. Without the pain of settling dates nothing else matters, and the conversion breaks the goal soonest. The person agrees, but moves the forums last: they post there already, and trust them more than a two-year lifetime. You run:

```
pkit lean rank board-game--hosts dates-cost-hours four-percent-pay two-year-hosts forums-reach-hosts --person-decided
```
