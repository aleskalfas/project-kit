# Changes: each round 3 finding, and what round 4 did

Order follows `round-3/verdict.md`. Where a fix is at the root (the system), every page took it, and the page entries say only what was left. "Agreed" means the finding's fix was taken as stated; "differs" says how and why. Every render passes the generator's checks with no fault, round 3's checks and the four new ones (`design-system.md` section 9).

## The three changes with the most impact

| Change | What round 4 did |
|---|---|
| 1. One accent with fixed meanings, at the brand | **Brand.** One hue, green, in two forms. *Order* (the solid ramp) means a place in the chain from your decisions. *Focus* (green text, a pale tint behind a region) means what the page's point is about. Everything else is neutral. Outcomes are an ink mark and a word. Violet and blue are gone. Every hue has one meaning deck-wide, stated in `design-system.md` section 4. Agreed, with the verdict's own example nearly word for word: green for pkit's parts and nearness to the source, ink for yours and for structure, one pale tint for the thing in focus. |
| 2. Page 4 shows the role, in a designed container style | **Notation and page.** The role is the container: "Role `pkit::work-tracking`", then "project-management opens 3 slots", then its three slots wall to wall. The fillers take the same form, role over name. Arrows land on slots. Containers are a 2 px outline at 4.3:1, the terminal a fill with no line. Insets are even (24, measured), and every line is 2 px. Agreed. |
| 3. Page 3's labels quieter than its content | **Page and shared pattern.** Stage names are semibold text on 2 px order rules. The reason is semibold, "Refused" regular. Column 2 is in body ink. The limit has its own band, 54 px under the last row against 34 between rows. Agreed. |

## Deck

| Finding | What round 4 did |
|---|---|
| Colour meanings drift: green for layers and stages, violet for pkit's files, blue for both "refused" and "the slot in focus"; "pkit's" green, violet and grey | **Brand.** As change 1. pkit's files on page 2 take the focus form, the same form as the proven slot on page 4 and the reasons on page 3. Green means only order (as a fill) or focus (as text or tint). Agreed. |
| The container language drifts: solid tiers, solid bars, tinted tiles, terminals reused as diagram boxes | **Foundations.** One look per kind (`design-system.md` section 6): block (an order fill), container (a 2 px outline at 3:1), panel (a terminal: a fill, no line), focus (text and tint), outcome (mark and word). Page 3's tiles and page 4's grey boxes are gone. Agreed: the verdict's four looks, with "tier" generalised to "block" so page 3's rules are the same fill as page 1's levels. |
| [polish] The source line at 20 px grey is the least legible text | **Kept at 20 px** in ink-muted (6.0:1 light, 6.9:1 dark). 20 is the scale's step under the body; 22 would sit off the scale, and 24 would make the source line read as body. The source line stays furniture by design, and it is above the 18 px floor. |

## Page 1: How pkit fits together

| Finding | What round 4 did |
|---|---|
| [block] The relation arrows float free of the stack and are not parallel to the steps (gap 23 → 47 px) | **Page and shared pattern.** Each relation now walks the steps, 16 px outside the stepped edge. It runs down the middle of each tread, rounds each outer corner on a concentric arc of radius 24 and goes sharp into each inner corner. Measured: 16.00 to 16.00 px from the levels over 224 points, both relations, every variant, and the check fails any drift over 0.6 px. "Carried out" leaves the Decisions level's left side and lands on the code level's top tread; "If they disagree" runs the reverse on the right. Each end is on its layer's edge (checked). Agreed: truly parallel at a constant offset and anchored to the layers it relates. The verdict's "straight, from tier to tier" cannot be both straight and parallel to a stepped edge, so the line takes the steps' own shape. |
| [block] The left column uses three alignment logics | **Page.** The "Carried out" note hangs on the 80 px margin under the ideas box: the left column has one edge, [80] (checked). The right note hangs on one edge, [992], one gutter outside the base. Both notes' last lines share the code level's last baseline. Agreed. |
| [polish] "Checked first" does not say what is checked; Czech loses "first" | **Words.** "If they disagree / the layer is / checked first." Czech: "Když se neshodnou / kontroluje se / nejdřív vrstva." The note carries the brief's relation by itself. Agreed. |
| [polish] Keep the stack and its tiers exactly | Kept: one hue, ordered lightness, darkest at the source, the ideas arrow into the apex. |

## Page 2: Install pkit (passed)

| Finding | What round 4 did |
|---|---|
| [polish] `pkit visibility private` in bare mono, not the terminal notation | **Page.** It takes the `$` prompt in a panel, like the steps. It is quieter by place and label (under the steps, no number, an ink-soft label), not by notation. Agreed. |
| [polish] The step 2 panel half empty | **Shared pattern.** Every panel is sized to its longest line plus 48. Step 2's panel holds its two real lines, `cd your-project` and `pkit init`, so it carries the step's weight. Agreed (the verdict's first option). |
| [polish] The ownership split is the page's quietest element | **Brand and page.** pkit's entries and their tags take the focus form, lifted to L .50 so they read plainly green. A first round 4 try at L .45 read near-black at a glance. **Differs** on the tint behind pkit's rows: at the tree's 28 px line pitch, a band 12 px clear of its text would cover the next line, and the field has no room to open the tree up. |
| [polish] Czech lead breaks mid-sentence; `your-project` not localised | **Words.** One sentence a line in Czech too. The placeholder is `vas-projekt`. Agreed. |
| Do not regress | The structure, the tree and its place, and the header-to-tree alignment are unchanged. The rhythm is tightened to 12 inside a step and 24 between steps, so step 2's second line and the option's panel fit the field. The tree's last line and the option's command share one baseline (584). |

## Page 3: Where permissions come from

| Finding | What round 4 did |
|---|---|
| [block] Solid header bars outweigh content; "Refused" bold three times, the reason regular; column 2 grey | **Shared pattern.** Stage names are semibold ink on a 2 px rule from the order ramp, the rules joined by the deck's wire. Each outcome is an ink mark and "Refused" in regular ink, then the reason in semibold focus text. Column 2 is in body ink. Agreed. **Differs** on moving "refused" into the head ("A call is refused"): the mark and word stay in each cell, quiet, because they are the outcome cell's second cue (WCAG 1.4.1), and the head "A call meets" names the stage as the other two heads do. |
| [block] The limit reads as part of the last row; two alignment logics in the table | **Page.** The limit has its own band: a 2 px keyline divider across the table, then the limit's cap height 54 px under the last row's text, against 34 between rows (checked: at least 48, and 12 more than the row gap). Every cell's text hangs on its column's edge, the stage name's and the rule's edge: one alignment. Agreed. |
| [block] Two accents compete: green bars and blue tiles | **Brand.** One accent. The rules are the order form at label weight; the reasons are the focus form; the outcome mark is ink. No tile and no blue. Agreed. |
| [polish] Keep the green ramp's link to page 1, at label weight | Kept: the rules take ramp steps 3, 4 and 5 (layers 3, 4, 5), at 2 px. |

## Page 4: How capabilities work together

| Finding | What round 4 did |
|---|---|
| [block] Default-looking boxes at 1.15:1 fill and 1.5:1 border; a terminal looks like a capability | **Foundations and notation.** A container is a 2 px outline at 4.3:1 on the paper in both modes (checked for every container), with paper inside. The terminal is the panel fill with no line, as on page 2 (checked: a panel has no line). Agreed. |
| [block] The point, that a capability names only a role, is not drawn; nothing says "role" or "slot" | **Page.** The arrows land on slots of the role's container. The container is headed "Role `pkit::work-tracking`", with "project-management opens 3 slots" second. The fillers show their roles (`pkit::documentation`, `pkit::analysis`) over their names. "Role" and "slot" are each named once in the drawing. Agreed. |
| [block] Everything at 24 px; role chips outrank names; benefits and caption in one grey | **Page.** Role ids in mono ink, capability names in the sans in ink-soft: one level for roles, a quieter one for names, the same in all three containers. **Differs** on which ranks higher: the role does, because the page's point is that capabilities see only roles, and the verdict's own fix heads the container with the role. The benefits have the head "What it gives you" and are set in ink. The caption is a caption: 20 px muted, beside the lines it names. Agreed. |
| [block] Slots flush left and short right; mixed stroke weights; the status band 3–4 px from its text | **Page and checks.** The slots are compartments, wall to wall, so there is no inset to be uneven. Text inset is 24 in every container (checked). Every line is 2 px (checked). The `fixers` tint clears its text by 12.7 px, and the status band clears the line above and the lines inside by 12.0 (checked, floor 12). The band runs to the panel's foot, so no grey strip is left under it. Agreed. |
| [polish] Keep the link between the highlighted slot and the highlighted lines | Kept, in the focus form: the `fixers` row's tint and the `bound` lines' tint, and `fixers` as the focus word in both. |
| [polish] Czech slot text 19 px from the right border | Every slot's text is measured to stay 24 px or more from the container's right wall (checked). |

## Disagreements, in short

1. **Page 1:** the relations follow the steps rather than running straight. A straight line cannot hold one distance from a stepped edge, and the verdict's first demand is a constant offset.
2. **Page 2:** no tint behind pkit's rows. At the tree's line pitch it would cover the neighbouring line; the brighter focus text carries the split instead.
3. **Page 3:** "Refused" stays in each cell, quiet, as the outcome's word beside its mark, rather than moving into the column head.
4. **Page 4:** the role outranks the capability's name, in line with the verdict's own heading fix and the page's point.
5. **Deck:** the source line stays at 20 px, the scale's furniture step.
