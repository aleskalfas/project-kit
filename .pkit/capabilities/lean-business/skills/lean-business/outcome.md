# Shortlisting, shelving or splitting a variant

A variant ends its desk stage in one of three outcomes, each the person's (DEC-002 point 5):

- **shortlisted:** chosen to be tested in a cycle. It keeps its moves, so the person can judge it again or shelve it later.
- **shelved,** with a reason: put aside, for good.
- **split** into the variants it names: its stories go on in them, and it is closed.

Shelved and split are final (DEC-003 point 2). Each of these is a move of the person's. Take it as the dispatcher's "Asking a judgement" says: ask in the conversation, confirm through the command's question without the flag, and run it with `--person-decided` only on their confirmation.

## Shortlisting

A variant may be shortlisted once all three desk steps have a yes, none stale. The person may shortlist several variants of the idea, and a cycle may explore more than one (`plan-cycle.md`).

1. **Set out the variants** that are feasible, each with its verdicts and their notes, and its estimate.
2. **Say which you would shortlist,** and which you would test first, and why. Then ask whether to shortlist each, one at a time.
3. **On their yes,** confirmed through the command's question:

   ```
   pkit lean shortlist <variant> --person-decided
   ```

The shortlisting keeps a fingerprint of the canvas and the goal it was made on. A variant the person leaves unshortlisted for now needs nothing run.

### Shortlisting again

A change to the canvas, or to the goal, makes the shortlisting stale. No new experiment is declared on a variant whose shortlisting is stale (DEC-003 point 7). The commands say so, louder where a cycle not yet reviewed explores the variant.

1. **Judge again each stale verdict.** A yes on a step already passed replaces the verdict and moves nothing (`desirability.md`, `viability.md`, `feasibility.md`).
2. **Ask** whether to shortlist it again on the canvas and the goal as they now stand, and on their yes run `shortlist` as above.

A no on a passed step instead takes the variant back, and withdraws its shortlisting.

## Shelving

The person shelves a variant whose story they no longer believe in, or will not test. Its reason is their own, in their words.

1. **Say whether you would shelve it,** and why, with its reason drafted from what the person told you. Say that it is final, and ask.
2. **On their answer,** confirmed through the command's question:

   ```
   pkit lean shelve <variant> --reason "<their words>" --person-decided
   ```

Its content stays editable, and nothing more rests on it. An idea whose every variant that was not split is shelved reads as dropped (DEC-003 point 8). Ending an idea is shelving its variants, and there is no other way.

## Splitting

Split a variant whose canvas tells more than one story, such as two kinds of customer paying for different things. Each new variant tells one story, of one archetype. A variant may be split while it is sketched or holds verdicts, but not once shortlisted (DEC-003 point 2).

1. **Name the stories you see** in the canvas, with a name for each new variant, and ask which the person sees and what to call each.
2. **Ask** whether to split it into those variants. Say that the variant split is final.
3. **On their answer,** confirmed through the command's question:

   ```
   pkit lean split <variant> --into <name> --into <name> --person-decided
   ```

Each new variant starts as a copy of the canvas and its assumptions, its ids re-qualified by the new variant, naming the split variant as the one it comes from. No verdict and no outcome is copied. Then trim each copy to its own story through the content commands (`sketch.md`): remove what belongs to the other story, and set its archetype and sides.

## Taking a shelved story up again

A shelved variant stays shelved. To take its story up again, start a new variant that names it:

```
pkit lean new-variant <idea>--<variant> --archetype <archetype> --comes-from <shelved variant>
```

It starts empty, and is sketched and judged from the start (DEC-003 point 2).

## Example

The broad sketch `meal-plan--service` holds two stories, as you and the person saw. You suggest calling them `households` and `grocers`, and they agree. You tell them the broad sketch will be closed, and ask whether to split it. They answer yes, and confirm the command's question:

```
pkit lean split meal-plan--service --into households --into grocers --person-decided
```

In `meal-plan--households`, you remove the grocers' segment and their revenue stream. In `meal-plan--grocers`, you set the archetype and name the two sides, then tag each entry with its side:

```
pkit lean set-archetype meal-plan--grocers multisided
pkit lean add-side meal-plan--grocers cooks
pkit lean add-side meal-plan--grocers shops
```

Once both variants are feasible, you show them side by side. You suggest shortlisting both, and testing households first, since its early channel is the person's own circle. They take both, and would start with the grocers, since a grocer already asked. They shortlist each, one question at a time:

```
pkit lean shortlist meal-plan--households --person-decided
pkit lean shortlist meal-plan--grocers --person-decided
```
