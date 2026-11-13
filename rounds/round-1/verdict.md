# Verdict: FAIL

## Page 1: How pkit fits together — FAIL
Scores: message 4, form 3, hierarchy 4, grid 4, colour 3, legibility 3, craft 4
- [block] **Contrast failure: the pyramid's base fades into the page.**
  - In light mode, "Your code and documents" is #D9F2E6 on white, 1.18:1, and the layer above it is 1.81:1. In dark mode the base is #002F1F on #121416, 1.25:1.
  - The widest step carries the whole argument: a narrow source over a broad base. Projected, the base will read as floating text with no step under it.
  - Principle: WCAG 1.4.11 asks 3:1 for graphics a reader needs to understand the content.
  - Fix at the brand: rebuild the green ramp so every step holds at least 3:1 against the page in both modes. Light mode has room for five steps between 11.8:1 and 3.1:1. Otherwise, give each step under 3:1 an outline at 3:1. The same ramp fails on page 3.
- [block] **Holds form at 3: the two relations are not drawn between the layers.**
  - The brief puts both relations between layers. The page draws them in the left margin, as two loose grey arrows (85 and 113 px long) beside paragraphs, tied to no layer.
  - A reader sees notes with decorations, not "each layer carries out the one above it, and is checked against it".
  - Principle: Mackinlay's expressiveness. A relation between layers belongs on the layers.
  - Fix on this page: draw both on the stack. A down arrow runs along one stepped side, labelled "carried out", and an up arrow along the other, labelled "checked". The left column keeps the ideas note and one line of explanation for each relation.
- [block] **Holds legibility at 3: the notes and layer descriptions are 20 px.** That is below the 24 px body text a reader at the back of the room needs. Fix at the type scale (see Deck).
- [polish] The up arrow ends 5 px below the pyramid's foot. A near miss reads as an error: end it level with the base, or with its text block.
- [polish] The footer cites "COR-065", an identifier this audience cannot read. Say what the record is, or keep the citation for the handout.
- [polish] Czech fits. The second layer's label leaves 29 px of side padding, against 41 px in English. Recheck the padding against the Czech text when the type grows.
- Dark mode is designed, not inverted: the ramp reverses so the source keeps the strongest contrast against the ground. Only its base fails, as above.

## Page 2: Install pkit — FAIL
Scores: message 3, form 3, hierarchy 3, grid 4, colour 3, legibility 3, craft 3
- [block] **The form contradicts the meaning: the listing is labelled as `tree` output but is not.**
  - It is introduced as `$ tree -a -L 2 your-project`, but `tree` prints nothing like what follows:
    - two directories on one line (`agents/  ● core/  ○ project/`);
    - `.claude/settings.json` collapsed into a single entry;
    - third-level entries under `-L 2`;
    - trailing slashes without `-F`.
  - Developers know `tree` output on sight. A diagram presented as a transcript costs the page its credibility with exactly this audience.
  - Fix on this page: drop the prompt line and present the listing as an annotated diagram. Otherwise, show real, cropped `tree` output and put the annotations outside the panel.
- [block] **Holds message and form at 3: nothing marks the two steps as steps.**
  - The page's point is two steps, yet:
    - Step 2, the "one command" (`pkit init`), is the narrowest panel.
    - It sits in the right column, above the alternative card, so proximity groups it with the alternative rather than with step 1.
    - Under the squint test the page is four rectangles of one tone, and the eye lands on the densest one, the listing.
    - The panels are generic code blocks, so the page reads as a README, not a slide.
  - Principles: Duarte's glance test; Gestalt proximity.
  - Fix on this page:
    - Number the two steps and set them as one row of equal panels across the full width, wrapping the URL.
    - Put the listing under them, as the result of step 2.
    - Make the alternative a small aside.
- [block] **Holds hierarchy at 3: the aside outranks the message.**
  - The alternative's heading, "Don't want pkit in your repository?", set in 24 px semibold, is the loudest type on the page after the title.
  - The two main steps carry only grey 18 px comments.
  - Principle: Refactoring UI, emphasis follows importance.
  - Fix on this page: give each step a short label at heading level, and set the alternative at body size.
- [block] **Holds colour at 3: pkit's files and yours differ in hue only.**
  - Light mode: purple #6E44B0 at 6.1:1 and blue #125FB3 at 5.8:1 on the panel. Dark mode: #C6AFFA at 9.6:1 and #93C1FC at 9.9:1 against the page, so their lightness is the same.
  - The ●/○ marks that should back the colour up are 8 px across on the slide, which is unreadable from the room.
  - Principles: WCAG 1.4.1; Bertin, where value, not hue, separates two kinds at a distance.
  - Fix: separate the two groups by position, pkit's files in one block and yours in another, each with its own label, so that colour only confirms. If both hues stay, set them apart in lightness.
- [block] **Holds legibility at 3: the code is 18 px across an 11-line listing.** That is the floor. The card body is 20 px.
  - Fix at the type scale.
  - Crop the listing to the lines that make the point: one pkit file, one of yours, and the merged settings file.
- [block] **Holds craft at 3: three inconsistencies.**
  - The page uses two container languages: grey filled panels, and an outlined white card with a grey chip nested inside. The card's border is 1.43:1 and disappears when projected.
  - The ●/○ marks sit in different columns. For `.pkit/`'s children they are mid-line; for `CLAUDE.md` and `src/` they are in the tree's gutter.
  - The `● ○ …` row says nothing.
  - Fix on this page: one panel style, the marks in one column, and the ellipsis row cut.
- [polish] The key line comes last, after the reader has already needed it. Put the legend above the listing, or label the groups directly.
- [polish] The footer sets `pkit status` in prose type. Elsewhere, commands are monospace.
- Czech fits, and the panels hold the longer comments. Dark mode is designed, but there the purple/blue pair is weaker still, as above.

## Page 3: Where permissions come from — FAIL
Scores: message 4, form 4, hierarchy 4, grid 4, colour 3, legibility 3, craft 4
- [block] **Contrast failure: the stage chevrons fade into the page.**
  - "A call meets" is #D9F2E6 on white, 1.18:1, and "Your AI tool gets" is 1.81:1. In dark mode they are 1.25:1 and 2.20:1.
  - The arrow points and notches are what say "this flows left to right", and on a projector the last one disappears.
  - Principle: WCAG 1.4.11.
  - Fix at the brand ramp, as on page 1.
- [block] **Holds legibility at 3: the cells, the row sub-labels, the Limit line and the evidence line are all 20 px.**
  - Fix at the type scale.
  - At 24 px, cut the cells to phrases: "denied to all", "a deny in settings", "refused in every mode".
- [polish] Several cells end on a lone last word: "written" and "WebFetch" in English, "režimu" and "pkitu" in Czech. Rebalance the line breaks or widen the third column.
- [polish] "**Limit** A deny stops…": the bold run-in label has no separator, so it reads as one sentence. Give it a colon, or set the label on its own line. Page 4 uses the same pattern, so fix it once, as a shared pattern.
- [polish] The evidence line repeats row 3 almost word for word, and runs about 125 characters on one line. Give a different fact or cut it. Keep any single line under about 90 characters.
- [polish] "project-management" is the only coloured word in the table, and nothing on this page says what its orange means. Key it as "capability", or set it in the text colour.
- Czech: the third column's text comes within 5 px of the right margin ("odmítnuto, použije příkazy"). Dark mode is designed; the only fault there is the ramp.

## Page 4: How capabilities work together — FAIL
Scores: message 3, form 3, hierarchy 3, grid 4, colour 3, legibility 3, craft 3
- [block] **Holds form and message at 3: the diagram shows capabilities naming each other, which the title denies.**
  - The point is "a capability never names another, only a role". Yet the wires leave the capability cards and land in a list framed by project-management's card.
  - What a reader sees is "living-docs and software-analysis plug into project-management", which is exactly the naming the title denies.
  - The role chips sit inside the cards as labels, not as the contract.
  - Principle: Mackinlay's expressiveness, draw the relation the page claims.
  - Fix on this page: make the role the socket.
    - Hang the three slots off the `pkit::work-tracking` role. The role is the frame; the capability is its current, swappable occupant.
    - Start each wire at the filling capability's role chip.
    - Draw a slot as an open socket, outlined rather than a white tile, so that a filled slot is visible as filled.
- [block] **Holds hierarchy at 3: the benefit list outranks the evidence.**
  - The benefits are set at 24 px, the largest body text on the page.
  - The diagram's slots are 20 px, the limit 20 px, and the status output 18 px.
  - So a secondary list outranks the evidence and competes with the diagram for focus.
  - Fix on this page: set the benefits at body size, and give the diagram's labels the larger step.
- [block] **Holds colour at 3: page 4 uses a palette no other page uses.**
  - The peach-and-brown container palette covers most of the diagram, so an accent has become the base (60-30-10).
  - In dark mode it turns a muddy #332215 brown, with page-coloured slots inside it at 1.21:1.
  - Fix at the brand:
    - Draw capabilities in the deck's neutral panel.
    - Keep orange for capability names and purple for roles, as the status output already does.
- [block] **Holds craft at 3: the wiring and the card padding are rough.**
  - Two elbow wires nest into the middle slot. Their arrowheads are 13 px apart and their junction dots stand at different x positions, which reads as a tangle at a glance.
  - The `pkit::documentation` chip runs to 7 px from its card's right edge, against 20 px on the left. The wire leaves the card at the chip's top corner.
  - The cards' padding is uneven:
    - project-management: 21 px above the name, 26 px below the last slot;
    - living-docs: 21 px above, 16 px below.
  - Fix on this page: one wire per filling, from chip to slot, and equal padding all round.
- [block] **Holds legibility at 3: the slots are 20 px, and the chips and status output 18 px.** Fix at the type scale.
- [polish] "pkit validate checks the wiring" sets the command in prose type. Set it in mono, as in the status panel.
- [polish] The right column leaves an empty band of about 150 px between the benefits and the limit. Once the benefits shrink, align the limit with the status panel and end the column there.
- [polish] Czech: all three benefits wrap, and two of them end on a lone last word ("potřebujete.", "zkontroluje."). Widen the column or shorten the text. Dark mode: as above.

## Deck
Consistency 3
- Sizes are in slide pixels, on the 1280 × 720 frame. The renders are 1.5×.
- **What holds:** the deck has a system's skeleton.
  - one margin (80 px) and one title-and-lead block;
  - one footer baseline;
  - the same two-column split on pages 2 and 4, and one code panel;
  - the green ramp meaning "source, then downstream" on pages 1 and 3;
  - orange for a capability on pages 3 and 4.
- **Four pages, four container languages.** Page 4 reads as if it came from another deck.
  - Page 1: solid green blocks and a dashed box.
  - Page 2: grey panels and an outlined card.
  - Page 3: chevrons over a hairline table.
  - Page 4: peach cards with white tiles.

  Fix at the brand: one card, one panel, one stroke, one radius, and colour only where it carries a meaning.
- **Purple means two things.** It marks pkit's files on page 2, but a role and its wiring on page 4. Blue appears only once. Fix: one written meaning per hue, and only the hues the deck needs.
- **The type scale is 48 / 24 / 20 / 18 (code).** Body text sits at 20 px on every page, below the 24 px a projected slide needs. Fix it in the foundation, not page by page: body 24, nothing under 20, code 22. Then cut the copy to fit.
- **The bottom margin is about 33 px, against 80 at the sides.** The footer line sits low on every page and risks being cut off by projector overscan. Raise it, or make the bottom margin equal the side margins.
- **The footer line has a different job on each page:** a record identifier, a pointer to a command, and evidence twice. Give it one role, evidence from project-kit, in one form.
- **Dark mode is designed.** The ramp reverses so the source keeps the strongest contrast, and the panels lift off the ground. But the ramp's far end sinks into the ground on pages 1 and 3, and page 4's brown is muddy.

## The three changes with the most impact
1. **Raise the type scale in the foundation:** body 24 px, nothing under 20, code 22. Then cut the copy to fit: page 1's notes to one sentence each, page 2's listing to about five lines, page 3's cells to phrases. Legibility scores 3 on every page, and this one change lifts all four.
2. **Rebuild the colour foundation.**
   - Make every step of the green ramp hold 3:1 against the page in both modes, with outlines where a step cannot.
   - Give each hue one meaning across the deck, and replace page 4's peach and brown with that palette.

   This clears the blocking faults on pages 1 and 3, and lifts colour on pages 2 and 4 and the deck's consistency.
3. **Rebuild page 2 around its two steps.**
   - Number the steps and set them as equal panels, side by side across the top.
   - Under them, put an honest listing, split by position into pkit's files and yours.
   - Make the private alternative an aside.

   This clears page 2's blocking fault and lifts five of its seven scores.
