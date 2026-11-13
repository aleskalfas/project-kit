# Verdict: PASS

All sizes are in slide pixels (image ÷ 1.5).

Round 7 changed what it said it changed and nothing else. Pages 1 and 2 and page 3's English are byte-identical to round 6. Only page 4 (all four variants) and page 3's Czech differ.

Nothing that held in round 6 has regressed:

- **Type.** The scale is still 48 / 30 / 24 / 20, with 22 for monospace. Nothing is under 20.
- **Contrast.** I measured the page-4 pairs again in both modes, and all are unchanged.
  - The lowest text pair is still the green "fixers" on the light terminal, at 4.66:1. It now sits on the first output line, still at 22 px, so it passes.
  - In dark mode the green on the terminal is 8.98:1 and on the slot fill 8.42:1.
  - The slot outline on the group is 3.88:1 in light mode and 4.25:1 in dark.
- **Grid.** It is unchanged: 12 columns, 80 px margins, content from y 224, footnote baseline 656. Page 4 ends at 600 again, so every page now meets the floor.
- **Radius, stroke and arrowheads.** There is still one radius (8), one stroke (2 px) and one arrowhead.
  - Page 4's connectors were re-routed to the new slot centres (258, 310 and 362). The two arrows into "fixers" land 14 px inside its top and bottom edges, symmetric about its centre.
  - Nothing crosses, and every arrow ends on the slot's outer edge at 572.
- **Dark modes** are still designed, not inverted. In dark mode, page 4's group and terminal now read as two panels.
- **Czech** fits everywhere. Nothing is clipped, and there are no lone last words.

## Page 1: How pkit fits together — PASS
Scores: message 5, form 5, hierarchy 4, grid 4, colour 5, legibility 4, craft 5
- Unchanged since round 6, so I carry its scores. I see no reason to move them.

## Page 2: Install pkit — PASS
Scores: message 4, form 4, hierarchy 4, grid 5, colour 4, legibility 4, craft 5
- Unchanged since round 6, so I carry its scores.
- [polish] Round 6's optional polish still stands. In light mode the mint row band is 1.02:1 against its panel, so on a projector the rule and the green text carry the meaning. Fix (brand, the band tint): deepen the band one step, or leave it.

## Page 3: Where permissions come from — PASS
Scores: message 5, form 4, hierarchy 4, grid 5, colour 5, legibility 4, craft 5
- **The Czech break is fixed.** The last row's middle cell now reads "hook, / před každým voláním". The preposition now starts its phrase, and the comma ends the first line where a reader pauses.
  - The longer second line ends at 871, 57 px clear of the outcome band's rule at 928.
  - No other cell moved. Dark mode matches.
- No faults left.
- Why three dimensions stay at 4:
  - Form: the flow through the three stages lives only in the header spine, and the rows read as a table. That is the right economy for three rows.
  - Hierarchy: the row heads stay bold while "Refused" stays regular, and the band carries the lead.
  - Legibility: the row sub-labels and the footnote sit on the scale's floor of 20.

## Page 4: How capabilities work together — PASS
Scores: message 4, form 4, hierarchy 4, grid 4, colour 4, legibility 4, craft 5
- **What is now right:**
  - The terminal has its own space. The group ends at 476, and the terminal runs from 492 to 600.
  - The proof is the first line pkit prints: `pkit::work-tracking:fixers` with a green "fixers", and the two `bound` lines indented under it. The indent shows containment, a slot holding its bindings. A developer reads "pkit reports two capabilities bound to this slot", and the green ties it to the green slot above.
  - The group has one text edge, at 596. The three slot names, the "role" label and "project-management" all start there, and the three descriptions share one column at 738.8.
  - All three chips are now 68 px tall, on both sides of the page.
  - Every container is 8-radius with 2 px strokes. Each box's text sits 24 px inside that box.
  - Craft moves up to 5.
- [polish] **Nothing on the page says what printed the panel.** The page names one command, `pkit validate`, in the left column, and its last line shares the terminal's last baseline at 580. So a reader of the PDF or the web page, where no presenter speaks, may take the panel for `pkit validate`'s output. The brief calls this evidence real `pkit status` output, and that is now invisible. A developer who wants to see it for themselves also does not know what to run. The dropped prompt is not the fault (see the next point). The missing source is.
  - Fix (shared pattern, terminal): an output-only panel names the command that printed it, as a quiet label. Right-align the label on the panel's first line at 1176. Set it in the chips' label idiom: a sans 20 grey word, then the mono 22 command ("from `pkit status`"; Czech "výstup `pkit status`").
  - It costs no height. It starts about 59 px clear of "fixers" (about 41 px in Czech).
  - The sans face shows it is the page's label, not shell text. That is the difference from the `#` comment of rounds 5 and 6.
  - Do not buy back a `$ pkit status` line by spending the 16 px gap or the 600 floor. A fourth line needs 28 px, which the page has only by cramping the group. The crowding and the floor were the bigger faults.
- **My call on the opening line: acceptable, not a fault in form or in consistency.**
  - In a terminal, `$` marks what you type, and a line without it is what the tool printed. Page 2's panels hold only input, so every line opens on `$`. Page 4's panel holds only output, so no line does.
  - That is one rule applied twice, not two styles. Developers read it exactly that way.
  - Round 6's "every terminal opens on `$`" was true only because page 2 happens to hold only commands. The stricter version of the rule would have forced a fake prompt line, or cost the page its spacing.
- Checked and holding, not faults:
  - **The 16 px gap against the group's 12 px inset.** The step is small, 4 px. But a white band and a change of tint (1.11:1 between the panels in both modes) separate the panels, and they read as two in light and dark mode. 24 px would be cleaner, but there is no room for it without breaking the floor.
  - **The terminal's text at 584 against the group's at 596.** Each text sits 24 px inside its own box. The terminal is a sibling of the group, not of the slots, so its text follows its own edge. Moving it to 596 would break the terminal's 24 px inset on page 2.
  - **The left heading's baseline at 460, 8 px under the owner chip's last line at 452.** In round 6 the two were 2 px apart. The left block moved up 8 px to keep its last line on the terminal's last baseline at 580. That is the alignment to keep, because those two lines sit side by side, while the heading and the chip are 300 px apart across the gutter with a dark block between. A designer can find the near-miss, but a reader does not see it.

## Deck
Consistency 5
- **One terminal, one rule.** Pages 2 and 4 share the tint (#e2e9f0 light, #22272d dark), the mono 22, the 24 px inset, the 32 px to the first baseline, the 28 px pitch and the 20 px below the last line. The rule now visible across both pages is that a `$` line is input and an unprefixed line is output.
  - [polish] Write that rule into the terminal pattern, with its corollary: an output panel names its command (page 4 above). Fix (shared pattern).
- **The floor holds on every page.** Content ends at about 600 everywhere again.
  - [polish] Round 6 asked that the floor be stated with the grid, so a local fix cannot push past it unnoticed. That still applies if it is not stated yet. Fix (foundations).
- **Same meaning, same look still holds.**
  - A navy fill is a part of pkit, light blue in dark mode.
  - A grey tint is a group, a blue tint is a terminal, and an outline is an open slot.
  - Green marks the part of each page that proves its lead, and a label always repeats it. On page 4 the green "fixers" now appears in the slot and in pkit's own output, which is that rule at its best.
- [polish] The light tints still sit between 1.10 and 1.22:1 against white. Every meaning they carry is repeated by a rule, an outline or a label, so nothing breaks. A washed-out projector may still flatten them. Check the deck on the room's projector once before the talk.

## The three changes with the most impact
1. **Name the source on page 4's terminal.** Add a quiet right-aligned label on the first line, "from `pkit status`", in the chips' sans-word-plus-mono idiom. Then the evidence is attributable in the handout and on the web page, and nobody takes it for `pkit validate`'s output. It costs no height and keeps the round-7 spacing.
2. **Check the tints on the room's projector, and deepen page 2's mint band one step if they wash out.** The light tints are the only thing in the deck that the medium, not the design, could break.
3. **Write the terminal rule and the 600 floor into the foundations.** The rule is: `$` marks input, no prefix marks output, and an output panel names its command. Both rules were settled by fixing pages. Stating them keeps the next page from re-opening them.

## Round 6 findings

### Page 2
- [polish] Mint band 1.02:1 against its panel — **open, optional.** The page is unchanged, and the polish stands as stated.

### Page 3
- [polish] Czech "hook, před / každým voláním" — **fixed.** It now breaks as "hook, / před každým voláním" in light and dark mode, with nothing else moved.

### Page 4
- [polish] Terminal 8 px from the owner's group, with its foot at 608 — **fixed.**
  - The group shrank by 16 px: slots 46 → 42 with their stroke inside a 44 px box, and the chip 72 → 68. It now ends at 476.
  - The terminal sits 16 px below it, at 492–600: more than the group's 12 px inset and its 8 px slot gap. The page meets the 600 floor.
  - The left chips were shrunk to 68 as well, so all three chips match.
- [polish] Proof in a trailing `#` comment on the command line — **fixed.**
  - `pkit::work-tracking:fixers` is now the first output line, with the two `bound` lines indented under it as pkit prints them.
  - To fit, the `$ pkit status` line was dropped. As notation that is acceptable (see page 4). The one loss is that the source is now unnamed, which is a new, smaller polish item with a zero-height fix.
- [polish] Text edges jog inside the group (584 against 596) — **fixed.**
  - The slot names and the chip's text all start at 596, and the slot descriptions share one column at 738.8.
  - The group now has one text edge. Each box's text sits 24 px inside its own box.

### Deck
- [polish] Content floor drifted to 608 on page 4 — **fixed on the page.** Whether the floor is now stated with the grid cannot be seen from the images, so that half of the note stands.
- [polish] Light tints 1.10–1.22:1 may wash out on a projector — **open.** This is a check before the talk, not a design change.
