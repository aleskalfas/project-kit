# Verdict: PASS

All sizes are in slide pixels (image ÷ 1.5).

Nothing the round-5 verdict said holds has regressed:

- **Type.** The scale is still 48 / 30 / 24 / 20, with 22 for monospace. Nothing is under 20. The smallest items are the footnotes, page 3's row sub-labels and page 4's "role" label, all at 20.
- **Contrast.** Every pair I measured passes WCAG 1.4.3 and 1.4.11 in both modes.
  - The lowest text pair is now the green "fixers" on page 4's terminal tint, at 4.66:1. That passes for 22 px text, but it is the one pair the darker terminal tint brought down. Next lowest is white on the bottom pyramid step, at 5.06:1.
  - The lowest graphic pairs are the slot outline on the grey group, at 3.88:1, and, in dark mode, the tree lines across the green band, at 3.59:1.
- **Grid.** The grid is unchanged: 12 columns, 80 px margins, content from y 224, footnote at the same baseline on every page. One drift: page 4's content now ends at 608, where the other pages end at about 600.
- **Radius and stroke.** There is one radius (8) and one stroke (2 px). The new accent band is square on the side where its rule sits, and it is drawn the same way on pages 2 and 3.
- **Containers and colour.** Each container kind keeps its meaning: a fill is a part, a blue tint is a terminal, a grey tint is a group, an outline is an open slot. The pale band with a 2 px rule marks a highlight: green for the evidence, grey for the limit. Green still marks only the evidence, and a label always repeats it.
- **Dark modes** are still designed, not inverted.
- **Czech** fits everywhere, with no clipping and no lone last words.

The round-5 polish was acted on carefully. Page 4 picked up two small side effects from its fix, and those are the main faults left. None of them blocks.

## Page 1: How pkit fits together — PASS
Scores: message 5, form 5, hierarchy 4, grid 4, colour 5, legibility 4, craft 5
- No faults left that a reader would notice.
  - Both relation lines now trace the pyramid's offset outline with every corner rounded at 16, so each reads as one drawn stroke.
  - The ideas arrow enters the apex at the height of the "Decisions" heading, 33 px above where the green line leaves it. A reader sees the idea arrive and then get carried down.
  - The labels sit 24 px from their lines, and their outer edges align with the dashed box and the fourth step.

## Page 2: Install pkit — PASS
Scores: message 4, form 4, hierarchy 4, grid 5, colour 4, legibility 4, craft 5
- No faults left.
  - The key line "pkit's: replaced · yours: kept" sits on the `.pkit/` row, right-aligned with the per-row labels. It reads as a true sentence about that folder, so the panel now proves the lead's second sentence.
  - The terminal is visibly its own surface: 1.11:1 against the listing and 1.22:1 against the page.
- Why message stays at 4: the point has two halves, and under a squint the step discs and the full-width install terminal lead, with the listing second. That reading order fits the steps, so it is not a fault.
- [polish] In light mode the mint band itself is 1.02:1 against its panel, so on a projector the 2 px green rule and the green text carry all of the meaning. Nothing is lost, because a label carries the meaning too. If you want the band to count, deepen it one step. Otherwise leave it. Fix: brand (the band tint), optional.

## Page 3: Where permissions come from — PASS
Scores: message 5, form 4, hierarchy 4, grid 5, colour 5, legibility 4, craft 5
- The outcome now leads. The pale band with its green rule behind "A call meets" is the page's one tinted area. Under a squint the eye goes from the title, along the spine, to that column. The band ends at 1200, where the spine ends, so the line now ends on the column's field rather than on the page edge.
- [polish] In Czech, the middle cell of the last row breaks "hook, před / každým voláním". The preposition "před" stays at the line end, apart from its phrase, which a careful Czech setter avoids. Fix (this page, Czech copy): break as "hook, / před každým voláním".

## Page 4: How capabilities work together — PASS
Scores: message 4, form 4, hierarchy 4, grid 4, colour 4, legibility 4, craft 4
- [polish] The owner's grey group and the `pkit status` terminal are now only 8 px apart.
  - Where: the group ends at 492 and the terminal starts at 500.
  - Why it matters: 8 px is less than the 12 px inset inside the group and equal to the gap between its slots. By proximity the terminal reads as one more row of the group, and in dark mode the two dark panels read as one block split by a hairline. The terminal's foot also moved to 608, below the deck's ~600 floor.
  - Cause: the chip's new 12 px bottom inset grew the group by 12, and the terminal moved down only 4.
  - Fix (this page): win the 12 px back inside the group, for example 4 px off each slot row (48 → 44, with the left chips re-centred on their slots). The group then ends at 480, the terminal sits 16–24 px below it, and the page ends on the deck's floor.
- [polish] The evidence moved out of the output. The panel now opens "$ pkit status", but the slot's name, "pkit::work-tracking:fixers", with the green "fixers", now sits in a trailing shell comment on the command line.
  - What a developer reads: a `#` comment is the author's note, not something pkit printed. So the green proof of a filled slot reads as a caption, and the two "bound" lines lose their heading.
  - Fix (shared pattern, terminal): the command line first, then the output as printed. Make the slot name the first output line, with the bound lines under it. If the panel has no room for a fourth line, take that room from the group fix above.
- [polish] Inside the group, the box edges now align at 572, but the text edges do not: the slot labels start at 584 and the chip's text at 596.
  - What a reader sees: the right column stacks three text blocks (slots, chip, terminal) with a 12 px jog in the middle. Round 5's near-miss has moved from the boxes to the text.
  - Fix (notation): one inner padding for boxes that hold text. Give the slots the chips' 24 px, so their labels start at 596 and the descriptions move right by 12. The group then has one text edge.

## Deck
Consistency 5
- **One connector spec.** Pages 1, 3 and 4, and the tree on page 2, all use a 2 px stroke, a 16 px bend with every corner rounded alike, and one filled arrowhead (12 × 10.8). The "two hands" signal from round 5 is gone.
- **One terminal.** It opens with a grey "$" prompt line and uses the same tint (#e2e9f0 light, #22272d dark) on pages 2 and 4.
- **One highlight component.** A pale band with a 2 px rule on its leading side, text 16 px after the rule. It marks pkit's rows on page 2 and the outcome column on page 3. The same rule, in grey and without a band, marks page 3's limit. Page 4's filled slot keeps the slot's own form, an outline, in green with the same mint fill. That is the right call, because the slot is a slot first.
- **Same meaning, same look.** Navy fill means a part of pkit on pages 1 and 4, light blue in dark. Grey tint is a group, blue tint a terminal, outline an open slot. Green is the evidence, always with a label.
- [polish] The content floor has drifted to 608 on page 4 (see page 4). Fix (foundations): state the floor (600) with the grid, so a local fix cannot push past it unnoticed.
- [polish] The light tints sit between 1.10 and 1.22:1 against white. That is fine on a screen and in the PDF, but a washed-out projector may flatten them. Every meaning they carry is repeated by a rule, an outline or a label, so nothing breaks. Check the deck on the room's projector once before the talk.

## The three changes with the most impact
1. **Give page 4's terminal its own space again.** Win back 12 px inside the owner's group so it ends at 480, with the terminal 16–24 px below it and ending on the deck's 600 floor. That removes the only crowding in the deck and the only page that breaks the shared floor.
2. **Put page 4's proof back into the output.** Make the slot name the first line pkit prints, with the two "bound" lines under it, not a `#` comment on the command. A developer then reads "pkit itself reports that two capabilities fill this slot", which is what the evidence is for.
3. **One text edge inside page 4's group.** Give the slots the 24 px inner padding the chips have, so "doc-check", "fixers", "use-cases" and "role pkit::work-tracking" start on one line. That finishes the alignment fix round 5 asked for: the box edges now meet, and this makes the text meet too.

## Round 5 findings

### Page 1
- [polish] Relation lines with one sharp and one rounded corner at every step — **fixed.** Every corner of both lines is now a 16 px arc, inner and outer alike, and each line reads as one stroke.
- [polish] Ideas arrow and green line 19 px apart on the apex's left face — **fixed.** The arrow now enters at y 245, in the face's upper third and level with "Decisions", and the green line leaves at 278: 33 px apart. The arrow still enters the side rather than the top. That was the second route offered, and it works.

### Page 2
- [polish] Listing proves ownership but not what an upgrade does — **fixed.** The key line "pkit's: replaced · yours: kept" (Czech "pkitu: nahradí se · vaše: zůstanou") sits on the `.pkit/` row, right-aligned with the per-row labels.
- [polish] Terminal and listing tints 1.05:1 apart — **fixed.** The terminal is one step darker and bluer (#e2e9f0): 1.11:1 against the listing and 1.22:1 against the page. It reads as its own surface in both modes. The green on it is still 4.66:1.
- [polish] Mint row band 1.02:1 against its panel — **fixed**, by the rule route. Each pkit's row has a 2 px green rule (5.07:1 or better against the band). The band tint itself is unchanged (see page 2's optional polish).

### Page 3
- [polish] "Refused" the quietest element; row heads the darkest masses — **fixed**, by the band route. A pale mint field with a green rule now sits behind the outcome column, and under a squint it is the column the eye ends on. The row heads stay bold and "Refused" stays regular. That is acceptable, because the band carries the lead without adding a fourth voice.
- [polish] Spine's last segment runs to the margin with no end — **declined, resolved another way.** The segment still ends at 1200, but the band now ends there too, so the line ends on the outcome column's field, not on the page edge. That holds.

### Page 4
- [polish] Project-management chip flush on the group's left and bottom while the slots are inset 12 — **fixed at the box level.** The chip is now inset 12 on both sides, at 572 like the slots. It has two side effects, now polish above: the text edges now jog (584 against 596), and the group grew 12 px, so the gap to the terminal shrank to 8.
- [polish] Status panel labelled by a trailing "# pkit status" comment — **partly fixed.** The panel now opens with "$ pkit status" in page 2's treatment. But the slot name moved into a trailing comment on that line, so the proof now reads as a caption (polish above).
- [polish] Connector bend radius 14 here against 31 on page 1 — **fixed.** Both pages are now 16.

### Deck
- [polish] Connector notation not yet one thing — **fixed.** One stroke, one 16 px bend with all corners alike, and one arrowhead, on every page.
- [polish] Terminal with a "$" prompt on page 2 and a "#" caption on page 4 — **fixed** as a convention: both open with the "$" command line. The page-4 output detail is above.
