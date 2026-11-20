# Shortlisting, shelving or splitting a variant

A variant ends its desk stage in one of three outcomes, each the person's (DEC-002 point 5):

- **shortlisted:** chosen to be tested in a cycle. It keeps its moves, so the person can judge it again or shelve it later.
- **shelved,** with a reason: put aside, for good.
- **split** into the variants it names: its stories go on in them, and it is closed.

Shelved and split are final (DEC-003 point 2). Each of these is a move of the person's. Take it with the steps of "Asking a judgement" in the dispatcher, and run it with `--person-decided` only on the answer.

## Shortlisting

A variant may be shortlisted once all three desk steps have a yes, none stale. The person may shortlist several variants of the idea, and a cycle may explore more than one (`plan-cycle.md`).

1. **Set out the variants** that are feasible, each with its verdicts and their notes, and its estimate. Say which you would test first, and why.
2. **Ask** whether to shortlist each, one at a time.
3. **On a yes:**

   ```
   pkit lean shortlist <variant> --person-decided
   ```

The shortlisting keeps a fingerprint of the canvas and the goal it was made on.

### Shortlisting again

A change to the canvas, or to the goal, makes the shortlisting stale. No new experiment is declared on a variant whose shortlisting is stale (DEC-003 point 7). The commands say so, louder where an open cycle explores the variant.

1. **Judge again each stale verdict.** A yes on a step already passed replaces the verdict and moves nothing (`desirability.md`, `viability.md`, `feasibility.md`).
2. **Ask** whether to shortlist it again on the canvas and the goal as they now stand, and on a yes run `shortlist` as above.

A no on a passed step instead takes the variant back, and withdraws its shortlisting.

## Shelving

The person shelves a variant whose story they no longer believe in, or will not test. Its reason is their own.

1. **Ask** whether to shelve it, and why. Say that it is final.
2. **On their answer:**

   ```
   pkit lean shelve <variant> --reason "<their reason>" --person-decided
   ```

Its content stays editable, and nothing more rests on it. An idea whose every variant that was not split is shelved reads as dropped (DEC-003 point 8). Ending an idea is shelving its variants, and there is no other way.

## Splitting

Split a variant whose canvas tells more than one story, such as two kinds of customer paying for different things. Each new variant tells one story, of one archetype. A variant may be split while it is sketched or holds verdicts, but not once shortlisted.

1. **Name the stories** you see in the canvas, and propose a short name for each new variant.
2. **Ask** whether to split it into those variants. Say that the variant split is final.
3. **On their answer:**

   ```
   pkit lean split <variant> --into <name> --into <name> --person-decided
   ```

Each new variant starts as a copy of the canvas and its assumptions, its ids given anew, naming the split variant as the one it comes from. No verdict and no outcome is copied. Then trim each copy to its own story through the content commands (`sketch.md`): remove what belongs to the other story, and set its archetype and sides.

## Taking a shelved story up again

A shelved variant stays shelved. To take its story up again, start a new variant that names it:

```
pkit lean new-variant <idea>--<variant> --archetype <archetype> --comes-from <shelved variant>
```

It starts empty, and is sketched and judged from the start (DEC-003 point 2).

## Example

The broad sketch `board-game--platform` holds two stories. You propose `hosts` and `venues`, and tell the person the broad sketch will be closed. They answer yes:

```
pkit lean split board-game--platform --into hosts --into venues --person-decided
```

In `board-game--hosts`, you remove the cafés' segment and their revenue stream. In `board-game--venues`, you set the archetype and name the two sides, then tag each entry with its side:

```
pkit lean set-archetype board-game--venues multisided
pkit lean add-side board-game--venues players
pkit lean add-side board-game--venues cafes
```

Once both variants are feasible, you show them side by side, and say you would test hosts first, since its early channel is the person's own circle. The person shortlists both, one question at a time:

```
pkit lean shortlist board-game--hosts --person-decided
pkit lean shortlist board-game--venues --person-decided
```
