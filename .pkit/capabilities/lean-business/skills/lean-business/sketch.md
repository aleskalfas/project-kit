# Sketching a variant's canvas

A *variant* is one story of how the idea makes a business, told on one canvas (DEC-001 point 7), whose twelve boxes are nine boxes and three sub-boxes (DEC-002 point 4). The first sketch is quick and rough: one sitting, the boxes in any order, blanks allowed. A canvas is never finished. It changes each cycle, as the person learns (DEC-002 point 4).

## 1. Start the variant

Agree with the person on a short name for the variant and on its archetype, which says who pays:

- **direct:** the customer who uses it pays.
- **multisided:** one side pays for another side's use, as advertisers pay for what readers get free.
- **marketplace:** the business brings buyers and sellers together, and keeps a share.

Where unsure, start with direct. A first sketch may mix stories, and splitting it later is cheap (`outcome.md`). Then run:

```
pkit lean new-variant <idea>--<variant> --archetype direct|multisided|marketplace [--author <name>]...
```

It creates the canvas and an empty list of assumptions. The authors default to the person running it. In a team, each member sketches alone first, then the team writes one canvas together and names them all as its authors.

For a multisided or marketplace model, name each side once you know them, with `pkit lean add-side <variant> <side>`. Each entry then names its side, and so does each set of the estimate's inputs (DEC-002 point 6).

## 2. Sketch in any order

Let the person start where their thinking is. Take what they say, place it in its box, and write it as you go:

```
pkit lean add-entry <variant> <box> "<text>" [--side <side>] [links]
```

The command prints each id it gives. Write the person's words, shortened only with their agreement (the dispatcher, "The person's words").

What each box holds is described once, in the canvas schema's box descriptions: `.pkit/capabilities/lean-business/schemas/canvas.schema.json`, under `boxes`. Read it there. The questions below are the capability's own, one to fill each box:

| Box | A question that fills it |
|---|---|
| `customer-segments` | Which kinds of people or businesses would use it, and which would pay? |
| `early-adopters` | Who would take it up first, and what happened to them that made the old way fail? |
| `problem` | What goes wrong for them today, and which of it hurts most? |
| `existing-alternatives` | What do they do about it now, including nothing at all? |
| `unique-value-proposition` | In one line, why would they change what they do? |
| `high-level-concept` | How would you tell a friend what it is like? |
| `solution` | What would the business give them, problem by problem? |
| `channels` | How would the first ten hear of it, and how would the next thousand? |
| `revenue-streams` | What would a customer pay, for what, and how often? |
| `cost-structure` | What would it cost to run, each month? |
| `key-metrics` | Which few numbers would you watch, and at which step of the customer factory does each count? |
| `unfair-advantage` | What would a well-funded rival lack that you have? |

Three things the method asks of a first sketch:

- **Blanks are fine.** A box the person cannot fill yet stays empty. The check's guidelines count only boxes that hold entries (DEC-002 point 14).
- **Pricing is not deferred.** Ask for at least a guessed price. Once desirability has a yes, a canvas without revenue streams draws a warning, and viability cannot be judged without one.
- **An unfair advantage only once it is real.** Leave the box empty until the person can say why a rival with money could not simply match it. An empty box shows an open question. A filler entry hides one.

## 3. Draw the links as you go

The commands hold the links data can carry, and the check warns where one is missing (DEC-002 point 14). Add them as flags of `add-entry` or `edit-entry`:

- **A problem** names each existing alternative it is a failure of: `--alternative <entry>`.
- **A value proposition** names the problem it answers, normally the first: `--problem <entry>`. Its sub-headline is `--sub-headline`.
- **A solution** names its problem: `--problem <entry>`.
- **An early adopter** names each event that made such customers switch: `--trigger "<text>"`.
- **A channel** is `--kind early` or `--kind scalable`.
- **A key metric** names its step: `--step acquisition|activation|retention|revenue|referral`.

Whether a link is apt is the person's judgement, and yours to question. The command only holds that it exists.

## 4. Show the sketch

Draw it, whole, with its credit line:

```
pkit lean canvas <variant>
```

Relay each warning the commands gave. They are guidelines, never refusals:

- more than three problems for a side
- fewer than three key metrics, or more than five
- a headline over about 120 characters
- a missing link

Then ask the person whether the canvas tells one story. Where they see two, or once they have answered and you see two, such as two kinds of customer paying for different things, or two archetypes, say so and offer a split (`outcome.md`). Each variant is then judged on its own.

## 5. Revising a canvas

Every change is content, made through a command:

- **An entry:** `edit-entry <entry>` changes its words, side or links, and its id stays. `remove-entry <entry>` takes it out. `move-entry <entry> --to <position>` changes its place, a problem's place being its rank.
- **The model:** `set-archetype <variant> <archetype>`, and `add-side` and `remove-side`.
- **The authors:** `set-authors <variant> <name>...`.

A change to what a verdict judged makes it stale, and the command names each verdict it leaves stale (DEC-002 point 13). A stale verdict holds the variant where it stands until the person judges again (DEC-003 point 2). Tell the person, and offer the step's sub-procedure.

## Example

The person starts with a broad sketch, `meal-plan--service`, direct. They talk in no order. First comes a grocer on their street who delivers, and who asked whether his offers could go into the plans. Then come their own Sunday evenings, spent planning the week's meals, and a colleague back at work after leave. You place each in its box, in their words:

```
pkit lean new-variant meal-plan--service --archetype direct
pkit lean add-entry meal-plan--service customer-segments "Households that cook every evening"
pkit lean add-entry meal-plan--service customer-segments "Grocers that deliver"
pkit lean add-entry meal-plan--service early-adopters "Busy young parents"
pkit lean add-entry meal-plan--service existing-alternatives "Lists on paper, written each weekend" --id paper-lists
pkit lean add-entry meal-plan--service problem "Planning the week's meals takes all of Sunday evening" --id planning-takes-long --alternative paper-lists
pkit lean add-entry meal-plan--service channels "Groups of new parents" --kind early --id parent-groups
pkit lean add-entry meal-plan--service revenue-streams "Households pay 8 EUR a month"
pkit lean add-entry meal-plan--service revenue-streams "Grocers pay 200 EUR a month to have their offers in the plans"
```

They told the paper lists at length, so you proposed "Lists on paper, written each weekend", and wrote it once they agreed. You leave the unfair advantage empty, since the person names nothing a rival would lack. When you show the grid, you ask whether it tells one story. The person sees two: households pay for their own plans, and grocers pay to reach cooks who use it free. You open `outcome.md` to split it.
