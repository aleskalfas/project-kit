# Gaps: what the engine would need to draw these pages

Each item takes one sentence and names who owns the change: the foundations, the neutral brand, the starter library, the `pkit` notation, or the engine. They are ordered within each group by how much the pages depend on them.

## Foundations: roles every brand fills

1. **An ordered ramp per family:** the foundations need a role `family.<hue>.ramp.1`–`5`, with one designed set for each mode, because a pattern that shades by place has no ordered colour to use today, and families give only fill, line and text.
2. **A strong text tone per family:** a `family.<hue>.strong` role is needed for text on the family's own fill, at 7:1 or more, because `text` is tuned for the paper.
3. **Type roles beyond body, heading, strong and code:** the foundations need title, lead, head, body, small and code, each with a size, line height, weight and tracking, because a slide needs a 48 / 24 / 20 / 18 hierarchy that the shipped sizes 24 / 16 / 14 cannot express.
4. **A spacing scale:** it needs 24, 48, 64 and 96 beside 4, 8, 16 and 32, because the gaps between groups and the page margins have no token today.
5. **A tertiary text tone:** a `text-muted` role (ink-muted) is needed beside text-primary and text-secondary, because code comments, prompts and the source line need a third step that recedes yet still meets 4.5:1.
6. **Radius and stroke tokens:** `radius` 8, `stroke.hair` 1 and `stroke.connector` 2, so that shapes and lines are one family across the patterns.

## Neutral brand: the values it ships

7. **Tonal scales:** an 11-step scale for each hue and for the neutral grey, built in OKLCH with one lightness per step in every hue (`design-system.md` §4.2), from which the families' roles and ramps are drawn.
8. **A designed dark mode:**
   - near-black paper, a surface raised above it, and family fills that are low-chroma tints at L .27, not deep shades, which go muddy;
   - a ramp whose step 1 is the lightest, so the order of salience holds.
9. **An accent that collides with no notation:** the neutral accent is blue, which project-kit's notation uses for *yours*, so the brand should let a notation declare which family the accent must avoid, or offer the accent as a role a project can re-point.
10. **Font naming for the semibold:** the brand's semibold must be named `Source Sans Pro` at weight 600, the typographic family (name ID 16), because resvg does not resolve "Source Sans Pro Semibold" and falls back silently.
11. **No new font needed:** every page is set in the three shipped faces. A Source Code Pro Semibold would let a command stand out from its arguments by weight as well as colour, but it is optional.

## Foundations, `deck`: the slide frame

12. **A slide grid:** 12 columns of 64 px with 32 px gutters, 80 px side margins, the title's cap height on a 64 px top margin, a field from 216 to 640, and a source line at baseline 688, so that patterns place by column span and every page starts its evidence on one line.
13. **A lead set as given lines:** a lead takes a list of lines broken by sense, so the author's break survives, rather than one string the engine wraps.

## Starter library: patterns and their options

14. **`layers` stepped:** a stepped form of `layers` (centred levels, each one step wider than the level above, filled from the ordered ramp by place) needs a DEC-007 entry, because no pattern shades by place today.
15. **A head and text inside a level:** `layers` must set a level's name and description on two centred lines inside its shape, and size the levels to the longest name.
16. **A flow-headed table:** a `table` whose column heads are chevron steps (notched in, pointed out, flat at both ends, filled from a ramp), with a row head plus tag, and cells on a shared baseline.
17. **A slot diagram:** a `network` whose target is a card with slot rows needs ties that land on a slot's edge, run orthogonally, branch at a junction dot when one source fills two slots, never cross, and align each source with the slot it fills alone.
18. **Note markers:** a `card` variant with no box whose left edge is a drawn arrow, up or down, and a dashed-outline variant for what is not decided yet.
19. **A limit:** a one-line pattern (or `aside` variant) with a run-in semibold label and ink-soft text, placed under the evidence it qualifies.
20. **An aside with a command:** the `aside` needs an outlined form (hairline, no fill) with a head broken by given lines, a command chip on the surface colour, and its text.
21. **Code roles:** `code` needs the roles prompt, command, argument, comment and output, each with its own tone, plus concept runs in the notation's colours.
22. **A mark per concept in code:** `code` should draw the notation's mark (● for pkit's, ○ for yours) before a concept run, so the content stops carrying the glyphs by hand (project-kit#2843).
23. **A key line in code:** a listing needs a closing key line set in the listing's own notation, so its colours are explained where they are used, until a legend pattern exists (project-kit#2576).
24. **A check-marked list:** `list` needs a marker option (✓ in a muted tone) and a body size for slides.
25. **Panels on a grid:** `panels` needs to take column spans (8 | 4, 3 | 3 | 3 | 3) and a two-row brick whose rows share their column edges.

## The `pkit` notation

26. **The layers as a ramp:** the five layers should map to the steps of one family's ordered ramp (green, the decision's hue, steps 1–5), not to five concept hues, because a level holds both pkit's and yours and colour must say one thing (DEC-001 point 6).
27. **A second cue for ownership:** `pkit/core` and `pkit/yours` should declare their marks (● filled, ○ hollow), so that ownership is not carried by colour alone (WCAG 1.4.1).
28. **Roles as identifiers:** `pkit/role` should be drawn as a monospace chip in pkit's violet, because a role is a name a developer types.
29. **pkit's wiring:** a tie drawn by pkit (`pkit/core` on a connector) should take the violet line tone, and the ties of one diagram should take one colour.

## Engine: typesetting

30. **Czech binding:** when wrapping Czech text, the engine should bind the one-letter words (v, k, s, z, o, u, a, i) to the next word, so they never end a line.
31. **Glyph fallback by run:** Source Sans Pro lacks ● and ○, and resvg then sets the whole text run in the fallback font, so the engine must split a run at any glyph its font lacks, or the notation's marks must stay in monospace runs.
32. **Measured text in patterns:** patterns must size boxes from measured advance widths of the shipped fonts (as `tools/measure.py` does), so that levels, chips and cells fit their text in both languages.
33. **Arrowheads that meet their target:** the canvas's marker places the tip at the line's end with the stroke running on under the head, which blunts the tip by the stroke's width, so the line should stop at the head's base and leave the tip sharp on the edge it enters.
