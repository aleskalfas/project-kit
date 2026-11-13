# Verdict: PASS

All sizes are in slide pixels (image ÷ 1.5).

- **Type.** The scale is 47 / 30 / 24 / 20 on every page, measured from cap heights. Nothing is under 20, and the small "role" label on page 4 measures about 20.
- **Contrast.** Every pair measured passes WCAG 1.4.3 and 1.4.11 in both modes. The lowest text pair is white on the bottom pyramid step, at 5.06:1. The lowest graphic is the grey connector on white, at 4.27:1.
- **Grid.** The pages now sit on a real 12-column grid with 80 px margins: 64 px columns and 32 px gutters. On every page the content starts at y 224 and ends at about y 600, and the footnote sits at the same baseline. Every box has the same corner radius (8). Outlines and connectors share one stroke, 2 px in #767b80.
- **Czech and dark.** Czech fits everywhere, with no clipping and no lone last words. Each dark mode is designed: page 1's ramp turns lightest-at-top, and page 4's slots become holes darker than their group.

The faults left are polish.

## Page 1: How pkit fits together — PASS
Scores: message 5, form 5, hierarchy 4, grid 4, colour 5, legibility 4, craft 4
- [polish] Each relation line has one sharp corner and one rounded corner at every step. At each jog the inner corner is a hard 90° and the outer corner a 31 px curve. The line traces the pyramid's offset outline, which is geometrically correct, but a reader sees a connector drawn in two corner styles. It breaks the craft rule of one corner treatment. Fix (notation): give the inner corners the same radius as the outer ones, or one small radius for all, so each line reads as one drawn stroke.
- [polish] At the left face of "Decisions", the incoming ideas arrow (y 259) and the outgoing green line (y 277) run in parallel only 19 px apart for about 60 px. The apex's left side is the tightest spot on the page. Fix (this page): bring the ideas arrow into the apex's top face, as the original did. Or drop it to the face's upper third and start the green line lower, at least 32 px apart.

## Page 2: Install pkit — PASS
Scores: message 4, form 4, hierarchy 4, grid 5, colour 4, legibility 4, craft 4
- [polish] The listing proves who owns each file, but not what an upgrade does to it. The heading is "Then each project holds", and the labels say only "pkit's" and "yours". The lead's second sentence ("Upgrades replace pkit's files, never yours") is left for the reader to connect (Alley: the visual proves the assertion). Fix (this page): name the consequence once in the panel, for example a heading "On upgrade" or a key line "pkit's: replaced · yours: kept". The per-row labels can stay.
- [polish] The terminal tint (#e8eff5) and the listing panel tint (#f3f4f6) stand side by side and differ by 1.05:1, by hue alone. At this distance, two near-identical greys read as an accident rather than as "command" against "result". Fix (foundations): either use one tint for both, or make the terminal clearly its own surface, for example one step darker.
- [polish] The mint row band on pkit's entries is 1.02:1 against its panel, so it holds by hue only and will fade on a projector. The meaning survives, because the green text and the "pkit's" label carry it. Fix (brand): a slightly deeper band tint, or a 2 px green left rule on each pkit's row.

## Page 3: Where permissions come from — PASS
Scores: message 4, form 4, hierarchy 4, grid 5, colour 4, legibility 4, craft 4
- [polish] Under a squint, the darkest masses are the bold black row heads on the left: "Guardrails", "An agent's own tools", "One agent's rule". The evidence for the lead's claim, "Refused" at every row, is green in a regular weight. It is lighter than the row heads, so the outcome column does not lead. The page passes the glance test through the column heads and the spine, but the payoff is the quietest thing in it. Fix (this page): give the outcome column the lead without adding a fourth voice. For example, set "Refused" semibold and bring the row heads down to semibold in the same step. Or lay a pale accent band behind the last column.
- [polish] The spine's last segment runs to the margin with no end mark. Its two arrowheads say "flows into", and the last column is the outcome. Fine as it is. Ending the line at the column's text width (about 1170) instead of the margin would tie it to the column rather than to the page edge.

## Page 4: How capabilities work together — PASS
Scores: message 4, form 4, hierarchy 4, grid 4, colour 4, legibility 4, craft 4
- [polish] Inside the owner's grey group, the slots are inset 12 px, but the project-management chip sits flush on the group's left and bottom edges. The page gains two left edges 12 px apart (560 and 572), a near-miss that reads as an error rather than as a tab. Fix (this page): inset the chip 12 px like the slots, or set the slots flush to 560 as well.
- [polish] The `pkit status` panel labels itself with a trailing comment, "# pkit status", on the first output line. Page 2 shows commands with a "$" prompt. The same terminal component then follows two conventions. Fix (shared pattern): open the panel with a "$ pkit status" line in the page-2 treatment, with the output below it.
- [polish] The connector bends here have a radius of about 14 px. Page 1's connectors use about 31 px. Fix (notation): one connector radius for the deck (see Deck).

## Deck
Consistency 4
- What holds:
  - The same meaning looks the same on every page. A slate or navy fill marks a part of pkit: the layers on page 1 and the capability chips on page 4.
  - A blue-grey tinted panel is a terminal, on pages 2 and 4. A neutral grey panel groups things that belong together, on pages 2 and 4.
  - A white outlined box is an open slot. A grey 2 px line is a connector or rule.
  - Green marks the evidence for the page's claim: the carried-out relation, pkit's files, the "Refused" outcome and the filled slot. A text label always repeats it, so colour is never alone.
  - Title, lead, content band and footnote sit at identical positions, on one grid and one radius.
- [polish] Connector notation is not yet one thing. Stroke and arrowhead already match: 2 px, and a filled head about 10 px tall on pages 1, 3 and 4. But there are two bend radii (31 and 14), and page 1's lines mix sharp and round corners. Fix (foundations): one connector spec, with a stroke of 2, one bend radius (for example 16), every corner rounded alike, and the current arrowhead.
- [polish] The terminal component appears with a "$" prompt on page 2 and with a "#" caption on page 4. Fix (foundations): the terminal shows the command line first, always.

## The three changes with the most impact
1. **Make page 3's outcome lead.** "Refused", at every row, is the evidence for "they hold when an agent forgets them", yet it is the lightest element in the table. Give the outcome column the strongest voice under the title, with semibold or a pale accent band, and bring the row heads down to match. That page goes from a well-set table to one that makes its argument in a glance.
2. **Write one connector spec into the foundations.** Use one stroke, one bend radius and one arrowhead, with every corner of a line rounded alike. That cleans up page 1's mixed corners and its tight apex, and aligns page 4's bends with page 1's. It removes the last visible "two hands drew this" signal in the deck.
3. **Tie page 2's listing to the upgrade claim, and settle its two panel tints.** One line, "pkit's: replaced · yours: kept", makes the panel prove the lead's second sentence rather than imply it. One clear decision on the terminal tint against the group tint removes a difference that reads as an accident.

## Round 4 findings

### Page 1
- [block] Relation labels asymmetric and captioning the bottom layer — **fixed.** Both labels now stand 24 px from their lines, at the middle step's height. Their outer edges align to the fourth step's edges (320 and 960).
- [polish] Line ends jammed in Decisions' corners — **fixed.** Both lines meet the apex's side faces 16 px above its bottom edge, outside the radius. The bottom ends land on the bottom step's exposed ledge.
- [polish] Relation strokes 1.3 px — **fixed.** They are now 2 px.
- [polish] Up-arrow label read as "change the decision" — **fixed.** It now reads "Checked first / against the one above".
- [polish] White on the lightest step at 4.57:1 — **fixed.** It is now 5.06:1.

### Page 2
- [block] Panels of three unrelated widths — **fixed.** Step 1 runs 80–1200. Step 2 and the alternative share 80–528. The listing sits at 656–1200, with its top on step 2's disc and its bottom on the last terminal's bottom.
- [block] URL bar as the focal point instead of the ownership split — **fixed.** The URL is set grey in a quiet panel. The ownership listing is the largest mass and holds the page's only colour. The wording that would tie it to "upgrades" is still missing (now a polish above).
- [block] Default-looking code blocks — **fixed.** One designed terminal component, with a tint, 24 px padding, a grey prompt, a dark command and grey arguments. It sits on column widths, is reused on page 4, and no longer collides with green.
- [polish] Ownership labels repeated four times — **partly fixed.** The labels are shorter ("pkit's" and "yours") but still per row. As an ownership column this reads as a table and is acceptable.
- [polish] Right column aligned with nothing — **fixed.** It starts at grid column 7 (656), and its top and bottom align with the left column.

### Page 3
- [block] Green qualifiers loudest — **fixed.** The accent now sits only on the spine and on "Refused". The qualifiers are regular dark grey.
- [block] Four bold voices — **fixed.** Bold now marks column heads, row heads and the "Limit:" run-in label, all one level. The green outcome is regular. The weight of that outcome is now on the quiet side (see the polish above).
- [polish] Arrowheads grey on green lines — **fixed.** Each segment and its arrowhead are one colour.
- [polish] Mono and sans mixed within a line — **fixed.** Code and prose sit on separate lines.

### Page 4
- [block] Capability-in-role drawn two ways — **fixed.** One chip for all three: a small "role" label, the mono role name, and the capability beneath.
- [block] 49 px channel with cramped S-bends — **fixed.** The channel is now 128 px (432–560). The bends are clean, nothing crosses, and the two arrows into "fixers" sit symmetrically about its centre.
- [block] Oversized status panel with an empty field — **fixed.** The indentation is stripped, the panel sits on the 7-column width under the diagram, and it is visibly subordinate.
- [block] Default flowchart boxes, with box and connector strokes differing — **fixed.** Box outlines and connectors now share one colour and weight. The outline now carries a meaning: an open slot, a hole in the owner's tinted group, against the filled capability chips. The page reads as one notation, not as a default flowchart.
- [polish] Benefits run together — **fixed.** They are single lines at a 40 px pitch under a bold head.
- [polish] Mint highlight vanishing — **fixed.** The "fixers" slot now has a 2 px green outline (5.07:1), and the green name repeats in the status output.

### Deck
- [block] No right margin or column grid — **fixed.** Pages 2–4 end at 1200 on a 12-column grid. Page 1 is a composition centred on 640, with its outer elements at 80 and 1179.
- [block] Four container languages — **fixed.** Each container now has one meaning: a fill is a part, a blue tint is a terminal, a grey tint is a group, and an outline is an open slot. One radius runs throughout. Page 3 needs no container.
- [block] Green meaning a different thing on each page — **fixed.** Green is the evidence for each page's claim, and a text label always carries the same meaning alongside it.
