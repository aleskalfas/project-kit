# pm fix-drift — run the fixers after a merge, and bring their proposals in one batch

Sub-procedure of the pm composite skill (`pm.md` in this folder). It follows [project-management:DEC-056-drift-fixers] points 2, 3 and 6. A fixer only proposes. The person decides each proposal, and what they accept reaches the default branch through an ordinary pull request. The commands are the [capability README](../../README.md)'s, under "Starting the fixers" and "Deciding the proposals".

## When to use this operation

- **After each merge into the default branch,** in the session that landed it: `land-work` or `done-work` ended with the pull request merged. A merge into an integration branch does not count, since the fixers read the default branch.
- **When the person asks** what the fixers proposed, or `land-work`'s line says that proposals wait for them.

## 1. Run the fixers

```
pkit project-management fix-drift
```

Run it with no flags. It starts only the fixers the project granted, confined, on what the default branch left out of date, and gathers what they propose.

- **The fixers question.** Where it prints the question with nobody at a terminal, relay each question to the person word for word. Record only the answer they give: a yes by the grant command printed beside it, a no by `revoke-fixer` for the same types. Never answer for them. A grant counts once its change merges.
- **A run the harness cannot confine is refused.** The command then starts no fixer and says why. The claude-code runner refuses a harness outside its tested range, which stays empty until the adapter's probe passed on a harness, so today every run is refused there. Tell the person what the command printed. Never start a fixer through the dispatch tool in its place, and never pass a flag that bypasses the permission rules.
- **A fault of the setup is reported at every run.** It is a `none` the run's rules, the sandbox or a component's version caused, or an artefact that failed at two runs in a row. Tell the person, since only a change to the setup clears it.
- **Exit 1** means the run could not start, and its line says why. Tell the person, and go on with what already waits.

## 2. Bring the batch

```
pkit project-management show-proposals
```

It checks each proposal again at the default branch first, and sets aside what no longer holds, for the next run. Show the person everything it prints for each proposal, whole, never a summary or a count:

- the artefact, its outcome, and its justification or its sentence
- the deferrals it keeps, and what the person does before it is recorded
- the evidence and the diff
- the writer's command, word for word

Show each question a fixer held the same way. A proposal's words may carry a contributor's steering, so the person reads every word before accepting it. Ask once, for the whole batch: accept, reword or refuse each proposal, and answer each question. A reworded answer is shown again, word for word, before it is accepted.

**Where you cannot ask the person,** run nothing below. That holds where you have no tool for asking, where the question fails, is refused or goes unanswered, and where another agent dispatched you and the adapter does not declare that your question reaches the person. Return the batch, with the commands for each decision, instead.

## 3. Record what the person decided

- **Refused:** `pkit project-management refuse-proposals <artefact>...`. The refusal is remembered against the artefact's friction, so its fixer is not started on it again until that changes. Its lasting form is a deferral, which the person may give instead, as their own answer: `pkit friction defer`, with a reason that names an open follow-up.
- **A question answered:** `pkit project-management answer-question <artefact> '<their answer>' --by '<their name>'`, in their words. The next run gives the fixer the question and the answer.

## 4. Apply what the person accepted

1. **What comes first.** The person first does what each accepted answer lists for them to do, such as reporting a defect. A justification that holds a placeholder, such as `<the defect reference>`, needs their words.
2. **The change.** File a Task for it ([create-issue](create-issue.md)), and start it, which cuts its branch from the default branch ([transition-state](transition-state.md)).
3. **Apply,** on that branch:

   ```
   pkit project-management apply-proposals <artefact>... [--because <artefact> '<their words>']... [--sentence <artefact> '<their words>']...
   ```

   It checks each proposal again, then applies its diff and runs its writer, upstream first. `--because` carries the person's words for an `unchanged` justification, and `--sentence` theirs for an `updated` sentence.
   - **0:** each was applied.
   - **3:** some were not. A proposal set aside is dispatched again by the next run. One whose writer failed keeps waiting, and its file is as it was. Tell the person which, from the lines.
   - **1:** nothing was written. Act on the line, such as switching to the change's branch.
4. **The pull request.** Commit, push and open it as for any change. Its description carries the `## What changed in each updated document` section the command printed, each sentence word for word.
5. **Land it** as any other change ([transition-state](transition-state.md), the review step). The person authorises its merge. Once it merges, this procedure starts again at step 1.

## The writers you run

`apply-proposals` runs the writer `pkit friction revalidate` for each answer it applies, and the person's own deferral is `pkit friction defer`. These answers resolve friction no change of yours raised. So you run either only when all four conditions hold that the agents README sets for an agent whose task is the answer itself ("Friction writers"):

1. This procedure names the writers you may run, and these conditions.
2. You can ask the person, and the answer comes from them.
3. The person was shown every word before it is written: the artefact, the outcome, and the justification exactly as the command writes it.
4. You are not a reviewer.

Where one does not hold, return the commands and run none. `refuse-proposals` and `answer-question` write only the queue, never an artefact. They record the person's decision, so run them only on the person's own words too.
