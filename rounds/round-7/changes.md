# Changes: each round 6 finding acted on, and what round 7 did

Round 6 passed. Round 7 is a narrow fix: the verdict's three changes with the most impact, all on page 4, and its Czech note on page 3. Nothing else was touched.

- "Agreed" means the fix was taken as the finding stated it.
- "Differs" says how the fix differs, and why.

**What did not move.** Pages 1 and 2, and page 3 in English, render byte for byte as in round 6. Page 3 in Czech differs only in one cell's two lines. All 16 renders pass the generator's checks with no fault. `system.py` reports 0 contrast failures in both modes, and no colour, size, radius or stroke changed. The ledger changed L12, L13, L17, L18 and L19, and added L27.

**One thing regresses, and it is open for the maintainer.** Page 4's terminal no longer opens on its command. The verdict's deck section counts "one terminal, opening on a `$` line" among what holds. The page 4 entry below gives the arithmetic: under the frame the field holds three terminal lines, and the proof needs all three.

## The three changes with the most impact

| Change | What round 7 did |
|---|---|
| 1. Give page 4's terminal its own space again | **Page.** Each slot is 44 tall, not 48. Each capability block is 68, not 72, because a block is a slot's height plus the tray above and below it. That keeps each filler centred on its slot, the upper one flush with the frame's top (224) and the lower one with the opener's top (396). The frame ends at 476, not 492. The terminal sits 16 under it, more than the tray's 12 and the slots' 8, and ends at 600. The page code asserts both. Agreed, and it differs in one detail: the verdict's "left chips re-centred on their slots" with 72 px blocks would have put the upper filler at 222, 2 px above the field's top. So the blocks shrink with the slots, and the frame wins back 16, not 12 (ledger L12, L13). |
| 2. Put page 4's proof back into the output | **Page.** The slot's own line, `pkit::work-tracking:fixers`, with `fixers` in proof ink, is the terminal's first line again. The two `bound` lines hang under it, 2 in, as `pkit status` prints them, so the slot heads them. The `#` comment is gone. **Differs: the `$ pkit status` line is cut.** Four lines are 136 px. The frame cannot be shorter than 252 without cramping it: a slot needs 44 to take two arrowheads 14 from its edges, and a block needs 68 to hold its two lines. 224 + 252 + 16 + 136 = 628, which is 28 below the floor and 14 px above the source line's capitals. Three lines end on 600. Two four-line versions were rendered and declined, and both are in `tools/review/`. `r7-alt-command-line-ends-628.png` keeps the frame and crowds the source line. `r7-alt-command-line-cramped.png` squeezes the frame to 224 (tray 8, slots 4 apart, blocks 60), which puts the blocks' descenders 3 px from their edge. Cutting a `bound` line instead would show one filler where the drawing shows two. Keeping the command with the slot in a comment is round 6. **Open for the maintainer:** keeping the command needs 28 px more in the right column, which only a re-layout of page 4 gives (ledger L18, L19). |
| 3. One text edge inside page 4's group | **Notation.** A slot holds its text 24 in, as a block does: one inner padding for every box that holds text. The slots' ids and the opener's lines now start on one edge, 596, and the slots' descriptions moved right by 12. The page code asserts the one edge (ledger L27). Agreed. The terminal's text stays at 584, its own 24 in from 560, the frame's box edge. It is 12 left of the frame's text by the frame's tray, because the terminal is the frame's report and not inside it. Moving it to 596 would take a 36 px padding on one side of one terminal, or a terminal off the grid that ends short of the margin. |

## Page 3: Where permissions come from

| Finding | What round 7 did |
|---|---|
| [polish] In Czech, the last row's middle cell breaks "hook, před / každým voláním", leaving the preposition at the line's end | **Words.** It now breaks "hook, / před každým voláním". The second line is 216 px, inside the stage's 256, and 56 px clear of the outcome region. Agreed. The rule is written into the system's line-break rule: a preposition stays on the line of the phrase it opens (`design-system.md`, section 2). The engine gap that would make it automatic is in `gaps.md`, item 45. |

## Page 4: How capabilities work together

| Finding | What round 7 did |
|---|---|
| [polish] Group and terminal only 8 px apart; the page ends at 608 | As change 1. Frame 224 to 476, terminal 492 to 600, 16 apart. The benefits' last line stays on the terminal's last baseline (580), and their head is 47 under the lower filler. |
| [polish] The evidence moved out of the output into a `#` comment | As change 2. The slot's line is output again. The command line could not be kept (open). |
| [polish] Box edges align at 572, but the text jogs: 584 against 596 | As change 3. One text edge inside the frame at 596. |
| Side effect of the shorter slot | **Notation.** The two ties into `fixers` land 8 px either side of its middle, not 10, so each tip stays 14 px from the slot's edge, the corner clearance the check asks for. The two heads stand 16 apart. The branch's drop is 44 px, so the two 16 px turns leave a 12 px straight run, where round 6 had 14 (ledger L17). |

## Not acted on, because round 7 was asked to change nothing else

| Finding | Status |
|---|---|
| Page 2 [polish, optional]: deepen the mint band one step, or leave it | Left, as the verdict allows. The rule and the green text carry the meaning. |
| Deck [polish]: state the floor (600) with the grid in the foundations | Not done in the foundations. Page 1 ends at 606, so a deck-wide check at 600 would fail it, and that is a separate change. Page 4's code asserts its own foot on 600. |
| Deck [polish]: light tints may flatten on a washed-out projector | No change. Check the deck on the room's projector once before the talk. |
