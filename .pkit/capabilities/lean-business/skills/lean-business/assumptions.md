# Drawing and ranking a variant's assumptions

An *assumption* is something the model takes for granted that no evidence supports yet: a leap of faith (DEC-001 point 7). Each comes from an entry of the canvas, or from an input of the estimate. The method tests the riskiest first, not the easiest, so the list is ranked by risk, and the ranking is the person's (DEC-002 point 8).

Draw them once a variant has passed the desk, or as the estimate shows what breaks it (`viability.md`). Rank them before the first experiment on the variant.

## 1. Find them

Look for the beliefs the model stands on. Most live in a few places:

- **The customer side:** the early adopters' trigger, the top problem and its alternative, and the value proposition. Would the early adopters feel the problem, and switch for the promise?
- **The estimate's inputs:** the price, the lifetime, the conversion and the referral share. Those that break the goal when a little worse are the first to draw.
- **Reaching customers:** the early channels, and the first stage's target.
- **What turns a pricing into the price,** such as how often a customer buys, or the share kept of a sale (DEC-002 point 4).

## 2. Write each as the leap of faith it is

An assumption states one belief the model rests on, plainly, as the person holds it (DEC-002 point 8). It names who does what, specifically enough that a test of it can be designed. It is not yet the test. The form that could be shown false, one action, a number expected and a time box, is the experiment's declaration (`experiment.md`).

- **Too vague to test:** "People like planning their meals."
- **A leap of faith a test can be built on:** "Parents back at work lose an evening a week to planning meals."

Give its kind, the desk step whose risk it carries: `desirability`, `viability` or `feasibility`. Then write it, from the entry or the input it comes from:

```
pkit lean add-assumption <variant> "<statement>" --kind desirability|viability|feasibility --entry <entry>
pkit lean add-assumption <variant> "<statement>" --kind viability --input price|lifetime|conversion|referral-share [--side <side>]
```

Each is content, and its statement is in words the person agrees to. The command gives its id, and places it one past the highest rank, which judges nothing. Show the person the list as it stands.

- **To change one:** `edit-assumption <assumption>`, which keeps its id, and warns where a declared experiment tests it.
- **To remove one:** `remove-assumption <assumption>`.

## 3. Rank them, with the person

The order is the person's. The question is which would hurt the model most if it turned out wrong, and two things are weighed together:

- **How likely it is wrong,** given what the person knows today.
- **How much of the model falls with it.** A belief the whole canvas rests on, such as the top problem, outranks one that a change of price could mend.

Customer risks usually come before technical ones: whether people want it before whether it can be built. An assumption that cannot be tested until later still takes its place by risk.

Offer an order of your own, with a sentence for each place, and ask for theirs. They take it, move what they weigh otherwise, or give their own. Take the ranking as the dispatcher's "Asking a judgement" says, and run it as they gave it:

```
pkit lean rank <variant> <assumption> <assumption> ... --person-decided
```

The assumptions named take the first ranks, in the order given. Those left out follow as they were ranked. A rank records no who or when, and keeps no fingerprint, so the person may change it whenever they learn something (DEC-002 point 8).

## 4. Read where each stands

An assumption stores no state of its own. Whether it is untested, being tested, supported, refuted or inconclusive follows from the experiments that test it, and is worked out each time (DEC-003 point 8). Read it from the status, never from memory.

## Example

For `meal-plan--households`, you draft four statements from the canvas and the estimate, and write each once the person agrees its words:

```
pkit lean add-assumption meal-plan--households "Parents back at work lose an evening a week to planning meals" --kind desirability --entry planning-takes-long --id planning-burden
pkit lean add-assumption meal-plan--households "A paying household stays two years" --kind viability --input lifetime --id two-year-stay
pkit lean add-assumption meal-plan--households "Five in a hundred households reached pay 8 EUR a month" --kind viability --input conversion --id five-percent-pay
pkit lean add-assumption meal-plan--households "Groups of new parents reach households who would pay" --kind feasibility --entry parent-groups --id groups-reach-parents
```

You offer an order: the planning burden first, since the whole canvas rests on it; then the conversion, since five in a hundred is a high share for a page nobody has seen yet; then the two-year stay; and the parents' groups last, since the person is in two of them already. The person moves the stay before the conversion: it is the input that put the goal out of reach when the estimate tried it worse, so more of the model falls with it. You add that no fourteen-day test can show a two-year lifetime. They keep the stay where they put it, since when a belief can be tested does not change how much rests on it. You run the ranking as they gave it, without the flag, show them its question, and on their confirmation run:

```
pkit lean rank meal-plan--households planning-burden two-year-stay five-percent-pay groups-reach-parents --person-decided
```
