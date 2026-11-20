# Reviewing a variant's desirability

Desirability asks whether the variant's customers would want it enough to change what they do today. It is the first desk step, and judges the customer side of the canvas (DEC-003 point 2). That side is five boxes: the segments, the early adopters, the existing alternatives, the problems and the unique value proposition. The verdict is a desk note, a cheap filter before any evidence, never a result (DEC-001 point 7).

Unlike the first sketch, this review has a fixed order. Each box rests on the one before it, so take them in the order below, and do not skip ahead. The commands do not hold this order, so you do.

## Before you start

- **The boxes.** Each of the five boxes must hold at least one entry by the verdict, or its gate refuses a yes. Fill a blank one when the review reaches it.
- **Sides.** In a multisided or marketplace model, take the review once for each side, since each has its own customers and its own value proposition (DEC-002 point 6).
- **Revise as you go.** The review is meant to change the canvas. Write each change through a command as the person makes it, in their words (`sketch.md`, "Revising a canvas").

## The review, in order

### 1. The customer segments

Keep each segment simple and broad: one kind of customer, named by what they are or do. Who to find first, and where, belongs to the early adopters, the next box.

- **Check** that each segment is one kind of customer, not a mix, and not yet narrowed to the first who would take it up.
- **Ask, where several sides share the model:** Who uses it, and who pays? Is each in a segment of the right side?

### 2. The early adopters

An early adopter is the part of a segment who would take it up first. They are known by what happened to them, not by a profile such as age or job title, and they are specific enough to find. Each needs at least one trigger: the event that made the old way stop working for them.

- **Ask:** Think of the last person who went looking for something better than what they had. What had just happened to them?
- **Ask:** Could you name ten such people, or say where you would meet them this week?
- **Write** each trigger with `--trigger` on its early adopter.

### 3. The existing alternatives

Look past products of the same kind. Customers get the job done today with whatever they have: a spreadsheet, a favour, paid help, or doing without.

- **Ask:** When that event happens, what do they reach for today? What would they use if your kind of product did not exist?
- **Check** that doing nothing, or putting up with it, has been considered.

### 4. The problems

Each problem is what is broken in an existing alternative. A problem stated as the lack of the person's own product, such as "no app does this", names the answer and hides the problem.

- **Ask:** What does the old way cost them, in time, money or worry? Which of these would they pay to be rid of first?
- **Write** each problem's link to the alternative it faults, `--alternative`. Keep at most three for each side, the most pressing first, and reorder with `move-entry`.

### 5. The unique value proposition

The headline answers the top problem, and promises a change large enough to make someone switch. A small improvement seldom moves anyone off a habit.

- **Ask:** Read the headline as someone who has the top problem. Would it make them stop using the old way?
- **Check** that it names the first problem with `--problem`, and that its headline stays within about 120 characters, with detail in its sub-headline.

## Lenses for a hard question

Where an answer above stays vague, look at it through one of these:

- **The switching story.** For one real customer, tell who they are and what they were trying to get done. Then tell what they used, what set them looking, what was wrong with the old way, and what they took up instead. A story about someone the person knows weighs more than one they imagine.
- **The job.** The progress the customer wants in their life or work, apart from any product. Two very different products can do the same job, so they compete.
- **The four forces.** The *push* of what goes wrong in the old way, and the *pull* of the new, work toward a switch. The *inertia* of habit, and the *friction* of the effort and the worry of changing, work against it. A switch happens only where push and pull together outweigh inertia and friction.

## The verdict

Take it as the dispatcher's "Asking a judgement" says:

1. **Set out what you found,** box by box. A weak box is a reason for a no, and for another pass on the canvas.
2. **Ask the person's verdict,** yes or no, with a sentence of why in their words. Give your own lean once they have answered, or when they ask.
3. **Confirm it, then record it.** Run the command with their answer and their note, first without the flag, showing them the question it prints, and then with it:

   ```
   pkit lean judge <variant> desirability yes|no --note "<their words>" --person-decided
   ```

What the verdict does (DEC-003 point 2):

- **A yes** moves the variant to desirable. Go on to `viability.md`.
- **A no** is recorded, as a yes is, and moves nothing. The canvas is revised, and the step judged again.
- **Judged again after a change,** a yes replaces the verdict and makes a stale one fresh. A no on a step already passed takes the variant back, clears the verdicts after it and withdraws a shortlisting. Say so before you ask.

## Example

You review `meal-plan--households` with the person, in order.

1. **The segments.** "Households that cook every evening" is one kind of customer, broad as a segment should be, so it stands.
2. **The early adopters.** They first wrote "Busy young parents", a profile. You ask what happened to the last parent they know who looked for help with the week's meals. The person recalls a colleague who came back to work after leave, and whose evenings fell apart in the first week. You ask how they would put that in the entry. They word it "Parents of a first child, back at work", with the trigger "The first week back at work after leave". They can name the parents' group at their own workplace as a place to meet ten of them. You write it in their words:

   ```
   pkit lean edit-entry meal-plan--households--busy-young-parents --text "Parents of a first child, back at work" --trigger "The first week back at work after leave"
   ```

3. **The alternatives.** Lists on paper. You ask about doing without, and the person says some of these parents order takeaway most evenings. They add "Takeaway, most evenings" as an alternative.
4. **The problems.** "Planning the week's meals takes all of Sunday evening" faults the paper lists. The person adds "Takeaway most evenings costs more than the food would", which faults the takeaway. Both now name their alternative.
5. **The value proposition.** The box was blank. The person words a headline, "The week's meals planned in a minute", and you write it, naming the first problem with `--problem planning-takes-long`. It is within the length.

You ask for their verdict. They answer yes: "every parent in my group dreads Sunday's planning". Asked for your view, you say you would have held back a little, since the early adopters rest on one colleague's story so far. The person keeps their yes: the interviews will tell. You run the command with their yes and their note, without the flag, and show them its question. They confirm, and you run:

```
pkit lean judge meal-plan--households desirability yes --note "Every parent in my group dreads Sunday's planning" --person-decided
```
