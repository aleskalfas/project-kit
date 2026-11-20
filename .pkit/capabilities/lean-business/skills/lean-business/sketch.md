# Sketching a variant's canvas

A *variant* is one story of how the idea makes a business, told on one canvas of twelve boxes (DEC-001 point 7). The first sketch is quick and rough: one sitting, the boxes in any order, blanks allowed. A canvas is never finished. It changes each cycle, as the person learns (DEC-002 point 4).

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

The command prints each id it gives. Keep the person's words, shortened only with their agreement.

The boxes, and a question of the capability's own that fills each:

| Box | What it holds | A question that fills it |
|---|---|---|
| `customer-segments` | the kinds of customer served | Which kinds of people or businesses would use it, and which would pay? |
| `early-adopters` | who would switch first, by what happened to them | Who would take it up first, and what happened to them that made the old way fail? |
| `problem` | up to three, the most pressing first | What goes wrong for them today, and which of it hurts most? |
| `existing-alternatives` | how they cope today | What do they do about it now, including nothing at all? |
| `unique-value-proposition` | why a customer would switch, as a headline | In one line, why would they change what they do? |
| `high-level-concept` | the business in a few words | How would you tell a friend what it is like? |
| `solution` | what the business offers for each problem | What would the business give them, problem by problem? |
| `channels` | how customers are reached | How would the first ten hear of it, and how would the next thousand? |
| `revenue-streams` | how the business earns | What would a customer pay, for what, and how often? |
| `cost-structure` | what running it costs | What would it cost to run, each month? |
| `key-metrics` | the few numbers to watch | Which few numbers would you watch, and at which step of the customer factory does each count? |
| `unfair-advantage` | an edge rivals lack | What would a well-funded rival lack that you have? |

Three things the method asks of a first sketch:

- **Blanks are fine.** A box the person cannot fill yet stays empty. The check's guidelines count only boxes that hold entries (DEC-002 point 14).
- **Pricing is not deferred.** Ask for at least a guessed price. Once desirability has a yes, a canvas without revenue streams draws a warning, and viability cannot be judged without one.
- **The unfair advantage is better blank than weak.** Write one only where the person can say why a rival could not match it.

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

Then ask whether the canvas tells one story. Where it holds two kinds of customer paying for different things, or two archetypes, propose a split (`outcome.md`). Each variant is then judged on its own.

## 5. Revising a canvas

Every change is content, made through a command:

- **An entry:** `edit-entry <entry>` changes its words, side or links, and its id stays. `remove-entry <entry>` takes it out. `move-entry <entry> --to <position>` changes its place, a problem's place being its rank.
- **The model:** `set-archetype <variant> <archetype>`, refused toward direct while a side is named. `add-side` and `remove-side`, the second refused while an entry or an input names the side.
- **The authors:** `set-authors <variant> <name>...`.

A change to what a verdict judged makes it stale, and the command names each verdict it leaves stale (DEC-002 point 13). A stale verdict holds the variant where it stands until the person judges again (DEC-003 point 2). Tell the person, and offer the step's sub-procedure.

## Example

The person starts with a broad sketch, `board-game--platform`, direct. They talk in no order. First come the cafés near them that host game nights, then a friend who spends a dozen messages fixing each game night's date. You place each in its box:

```
pkit lean new-variant board-game--platform --archetype direct
pkit lean add-entry board-game--platform customer-segments "People who host a game night for friends at least twice a month"
pkit lean add-entry board-game--platform customer-segments "Game cafés that run open play evenings"
pkit lean add-entry board-game--platform existing-alternatives "A group chat and a shared sheet of who owns which game" --id chat-and-sheet
pkit lean add-entry board-game--platform problem "Settling a date takes a dozen messages" --id dates-take-messages --alternative chat-and-sheet
pkit lean add-entry board-game--platform revenue-streams "Hosts pay 4 EUR a month"
pkit lean add-entry board-game--platform revenue-streams "Cafés pay 60 EUR a month to list their evenings"
```

You leave the unfair advantage empty, since the person names nothing a rival would lack. When you show the grid, you point out two stories in it. Hosts pay for their own use, and cafés pay to reach players who use it free. The person agrees, and you open `outcome.md` to split it.
