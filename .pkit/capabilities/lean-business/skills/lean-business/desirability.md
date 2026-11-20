# Reviewing a variant's desirability

Desirability asks whether the variant's customers would want it enough to change what they do today. It is the first desk step, and judges the customer side of the canvas (DEC-003 point 2). That side is five boxes: the segments, the early adopters, the existing alternatives, the problems and the unique value proposition. The verdict is a desk note, a cheap filter before any evidence, never a result (DEC-001 point 7).

Unlike the first sketch, this review has a fixed order. Each box rests on the one before it, so take them in the order below, and do not skip ahead.

## Before you start

- **The boxes.** Each of the five boxes holds at least one entry, or the verdict's gate refuses a yes. A blank box is the first thing to fill.
- **Sides.** In a multisided or marketplace model, take the review once for each side, since each has its own customers and its own value proposition (DEC-002 point 6).
- **Revise as you go.** The review is meant to change the canvas. Write each change through a command as the person makes it (`sketch.md`, "Revising a canvas").

## The review, in order

### 1. The customer segments

Check that each segment is one kind of customer the person could go and find, not everyone.

- **Ask:** Could you name ten people in this segment, or where you would meet them this week?
- **Ask, where several sides share the model:** Who uses it, and who pays? Is each in a segment of the right side?

### 2. The early adopters

An early adopter is known by what happened to them, not by a profile such as age or job title. Each needs at least one trigger: the event that made the old way stop working for them.

- **Ask:** Think of the last person who went looking for something better than what they had. What had just happened to them?
- **Write** each trigger with `--trigger` on its early adopter.

### 3. The existing alternatives

Look past products of the same kind. Customers get the job done today with whatever they have: a spreadsheet, a favour, paid help, or doing without.

- **Ask:** When that event happens, what do they reach for today? What would they use if your kind of product did not exist?
- **Check** that doing nothing, or putting up with it, has been considered.

### 4. The problems

Each problem is what is broken in an existing alternative, not the absence of the person's solution. "There is no app for this" is a solution in disguise.

- **Ask:** What does the old way cost them, in time, money or worry? Which of these would they pay to be rid of first?
- **Write** each problem's link to the alternative it faults, `--alternative`. Keep at most three for each side, the most pressing first, and reorder with `move-entry`.

### 5. The unique value proposition

The headline answers the top problem, and promises a change large enough to make someone switch. Clearly better wins a customer, and a little better rarely does.

- **Ask:** Read the headline as someone who has the top problem. Would it make them stop using the old way?
- **Check** that it names the first problem with `--problem`, and that its headline stays within about 120 characters, with detail in its sub-headline.

## Lenses for a hard question

Where an answer above stays vague, look at it through one of these:

- **The switching story.** For one real customer, tell who they are and what they were trying to get done. Then tell what they used, what set them looking, what was wrong with the old way, and what they took up instead. A story about someone the person knows weighs more than one they imagine.
- **The job.** The progress the customer wants in their life or work, apart from any product. Two very different products can do the same job, so they compete.
- **The four forces.** The *push* of what goes wrong in the old way, and the *pull* of the new, work toward a switch. The *inertia* of habit, and the *friction* of the effort and the worry of changing, work against it. A switch happens only where push and pull together outweigh inertia and friction.

## The verdict

1. **Get the question.** Run the command without the flag, and it prints the process's own question:

   ```
   pkit lean judge <variant> desirability yes
   ```

2. **Set out what you found,** box by box, and say which way you lean and why. A weak box is a reason for a no, and for another pass on the canvas.
3. **Ask,** and wait for the person's yes or no, and a sentence of why.
4. **Record their answer:**

   ```
   pkit lean judge <variant> desirability yes|no --note "<their reason>" --person-decided
   ```

What the verdict does (DEC-003 point 2):

- **A yes** moves the variant to desirable. Go on to `viability.md`.
- **A no** is recorded and moves nothing. The canvas is revised, and the step judged again.
- **Judged again after a change,** a yes replaces the verdict and makes a stale one fresh. A no on a step already passed takes the variant back, clears the verdicts after it and withdraws a shortlisting. Say so before you ask.

## Example

You review `board-game--hosts` with the person, in order.

1. **The segments.** "People who host a game night for friends at least twice a month." The person can name six such hosts, so it stands.
2. **The early adopters.** They first wrote "young professionals who like games", a profile. You ask what happened to the last host who looked for a better way. The person recalls a friend whose group grew to fourteen, and whose sessions fell apart. You rewrite the entry as "Hosts whose group grew past what a chat can organise", with the trigger "a session cancelled because nobody knew who was coming".
3. **The alternatives.** A group chat and a shared sheet. You ask about doing without: some hosts simply stop inviting newcomers. The person adds that as an alternative.
4. **The problems.** "Settling a date takes a dozen messages" faults the chat. "Nobody remembers which games the group owns" faults the sheet. Both now name their alternative.
5. **The value proposition.** "Game night settled in one tap" answers the first problem, within the length.

You lean to a yes, with the early adopters still a guess. The person answers yes, because "every host I know complains about the dates", and you run:

```
pkit lean judge board-game--hosts desirability yes --note "Every host I know complains about fixing dates" --person-decided
```
