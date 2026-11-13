# Design system: the showcase deck's target (round 4)

The system comes first, and the pages follow from it. `tools/system.py` holds every value below as code. `python tools/system.py` prints every colour pair the pages put one on another, each with its WCAG floor, and counts the failures (0). `tools/pages.py` draws each page from those values alone. `tools/build.py` measures each drawn page with `svg.check` and prints any fault: 0 on all 16 renders.

Round 4 settles four things once for the deck, each a fix at the root for a round 3 finding:

1. **One accent, set at the brand, with fixed meanings** (section 4). There is one hue in the deck, green, in two forms: *order* and *focus*. Each form has one meaning on every page. Everything else is neutral, and outcomes take an icon and a word, not a hue.
2. **One look per kind** (section 6). A block is a fill, a container is a 2 px outline at 3:1 or more, a terminal is a fill with no line, and focus is a tint. No two kinds share a look.
3. **One stroke weight** (section 5). Every line on every page is 2 px.
4. **A check for each round 3 fault** (section 9): arrow parallelism, alignment edges, the outline contrast of every container, and highlight clearance. Round 3's checks stay.

The two layers stay as before. **The neutral brand** carries what any project needs: the grid, the type scale, spacing, the neutrals, one accent in two forms, one radius and one stroke. **Project-kit's identity** lives in the `pkit` notation library: what a role, a slot and a capability look like, and which of pkit's things take the focus form.

---

## 1. Grid (neutral brand)

| | Value | Reason |
|---|---|---|
| Page | 1280 × 720 | A 16:9 slide, also a PDF page and a web page. |
| Columns | 12 × 64 px, gutters 32 | Halves, thirds and quarters land on column edges (Müller-Brockmann). |
| Side margins | 80 px | 12 × 64 + 11 × 32 = 1120 on whole pixels; above the 64 px floor. |
| Top margin | 64 px to the title's cap height | Optical alignment: the capitals sit on the margin. |
| Bottom margin | 64 px to the source line's baseline (656) | Equal to the top, so the page is framed evenly and clears projector overscan. |
| Field | y 224 to 608 (384 px) | It starts 46 px under the lead's last baseline (178). Inside the header the gap is 24, so the header reads as one group and the evidence as another (Gestalt proximity). |

A page may divide the field by its content's own measure where the content sets one. Page 3's table is 232 + 3 × 264 with 32 px gutters. Page 4's columns are 854 | 234, set by the terminal's real line width. Both keep the 80 px margins and the 32 px gutter.

**Alignment edges.** *Round 4.* Each column of a page has one left edge for its top-level things. A box and a free text in the same column start on the same x (Müller-Brockmann: few alignment edges). The generator counts the edges in each named column and fails the page past the column's limit. Measured: page 1's left column [80] and right column [992]; page 4's note column [966]; page 4's evidence column [80, 427], its two sub-columns: the fillers and the role they fill.

## 2. Type (neutral brand)

One family, Source Sans Pro, in Regular 400 and Semibold 600, and Source Code Pro Regular for code. These are the brand's shipped fonts and nothing else.

**The scale** is a 1.25 modular scale on a 24 px body (Tim Brown): **20 · 24 · 30 · 38 · 48**, plus 22 for monospace.

| Role | Size / line | Weight, colour | Use |
|---|---|---|---|
| title | 48 / 56, −0.5 tracking | Semibold, ink | The page's anchor; names the subject. |
| lead | 30 / 38 | Regular, ink | The page's point, two lines broken by sense. |
| head | 24 / 32 | Semibold, ink | The name of a level, a step, a row, a stage, a column of notes. |
| body | 24 / 32 | Regular, ink or ink-soft | Everything read across the room. |
| small | 20 / 28 | Regular, ink-soft or ink-muted | Page furniture only: the source line, a row's tag, a caption. |
| code | 22 / 28 | Regular, mono | Every monospace run, in a panel or inside a sentence. |

- **One way to state the point** (Alley: assertion and evidence; Duarte's glance test). The title names the subject, the lead states the claim, and the field is the evidence.
- **Mono at 22 inside 24 px text**, so it reads as the same size as the sans around it.
- **What is set in mono:** text as it is written in a file, typed, or printed in a terminal. That covers commands, tool names, agent ids, role and slot ids, and paths. Names of things (a capability's name, "pkit") stay in the sans.
- **Three degrees of emphasis on every page:** the title and lead; the focal element; everything else. The secondary is de-emphasised (ink-soft), never the primary shouted (Refactoring UI). *Round 4:* labels are quieter than content. Page 3's stage names are semibold text on a 2 px rule, not solid slabs. The repeated word in a column ("Refused") is regular, and the part that differs (the reason) carries the weight.
- **Line breaks are set by hand, by phrase,** in every narrow block, and each line is measured against its column. No line ends on a lone word; in Czech no line ends on a one-letter word or "ve" (Bringhurst).

## 3. Space (neutral brand)

The scale is **4 · 8 · 12 · 16 · 24 · 32 · 48 · 64**.

| Distance | Value | Principle |
|---|---|---|
| Inside a container or panel, at the sides | 24, measured from the ink, the same at every container (checked) | Equal padding. |
| Inside a panel, top and bottom | 20 from the edge to the cap height, 22 from the last baseline | Optical padding, not line-box padding. |
| A highlight around its text | 12 at least, from the tint's edge to the cap height or descender inside it, and to the text beside it (checked) | *Round 4.* Text needs room inside its band (round 3 verdict, page 4). |
| A wire to any shape it does not attach to | 16 at least; to any text, 12 (checked) | Ware: connectors read as relations only when they clear what they pass. |
| A relation that follows a shape | a constant 16, held to ±0.6 px (checked) | *Round 4.* Parallel means one distance (Gestalt continuity). |
| Between parts of one group | 8 to 16 (a step's disc to its panel: 12) | Space inside a group is smaller than space between groups (Gestalt proximity). |
| Between groups | 24 to 48 (step to step: 24) | The same rule, one level up. |
| Before a page-wide caveat | 48 at least, and 12 more than between the rows above it (checked) | *Round 4.* A caveat that covers the whole table stands apart from its last row. |

## 4. Colour: one accent, two forms, one meaning each

*Round 4.* Round 3 had three accent hues and none kept one meaning: green meant layers and stages, violet meant pkit's files, and blue meant both "refused" and "the slot in focus" (round 3 verdict, Deck). Now the brand has **one accent, green, in two forms**. Each form has one meaning on every page. Everything else is neutral (60-30-10; Albers: one colour, one job).

| Form | What it looks like | Means, on every page | Second cue (WCAG 1.4.1) | Pages |
|---|---|---|---|---|
| **order** | a solid fill from the green ramp, five steps of lightness, text on it in one tone | **a place in the chain that starts at your decisions**; the step nearest the source stands out most | position and size; each step's name | 1 (the five layers); 3 (the three stages, as layers 3, 4 and 5, on 2 px rules) |
| **focus** | green text on the key word; where the evidence is a region, the pale green tint behind it | **what the page's point is about: the evidence to look at** | the word itself, and position | 2 (pkit's files: the ones an upgrade replaces); 3 (each reason a call is refused); 4 (the `fixers` slot, and the status lines that prove who fills it) |
| neutral | paper, panel, keyline, outline, ink, ink-soft, ink-muted, relation | structure, text, relations, and everything not in focus | | all |
| **outcome** | an ink mark and a word: no hue | a result (page 3: refused) | the word beside the mark | 3 |

**The two forms never cross.** Order is only ever a fill, with text set on it. Focus is only ever a text tone, or a pale tint behind ink text. A reader who learns "solid green is the chain" on page 1 and "green words are the point" on page 2 reads pages 3 and 4 without a key. Both forms are the same hue because both mean "pkit's point is here", and a second hue would spend the reader's attention on a difference that carries nothing.

**What left the palette, and why.** Violet (round 3: pkit's files, page 2 only) is now the focus form: pkit's files are the evidence that page is about. Blue (round 3: refused on page 3, the slot in focus on page 4) split in two. "Refused" is an outcome, so it takes the ink mark and word. "The slot in focus" takes the focus form. The surface fill of blocks and the tag fill are gone: a capability is a container and a role is its heading (section 6).

### 4.1 The neutrals (neutral brand)

| Role | Light | Dark | Use |
|---|---|---|---|
| paper | `#ffffff` | `#121416` | The page. Dark is a cool near-black (Material's dark theme). |
| panel | `#e3e5e7` (1.26 to 1) | `#27292c` (1.27) | A terminal: a fill, no line. Raised in dark: lighter than the paper. |
| keyline | `#c8cbce` | `#3a3d41` | A divider inside a container (page 4's slot rows) and page 3's caveat divider: structure only, never the only boundary of a thing. |
| **outline** | **`#777b7f` (4.3 to 1)** | **`#777b7f` (4.3)** | *Round 4.* A container's 2 px line, and the dashed "undecided" line. 3:1 or more on the paper (WCAG 1.4.11), 3.8 and 3.5 on the focus tint. |
| ink | `#181b1f` | `#edeff1` | Primary text, 17.3 and 16.0 to 1. Also the outcome mark. |
| ink-soft | `#4f5358` | `#bbbec2` | Secondary text, 7.8 and 9.9 to 1. |
| ink-muted | `#5f6469` | `#9b9fa3` | Prompts, tree guides, placeholders, captions, the source line: 6.0 and 6.9 to 1, and 4.7 and 5.5 on the panel. |
| relation | = ink-soft | = ink-soft | Arrows and wires. A relation is not a thing, so it takes no hue. |

### 4.2 The order form: the green ramp (neutral brand)

| | Step 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| Light (OKLCH L .30 → .55) | `#013726` | `#004933` | `#015c41` | `#036f4f` | `#078661` |
| against white; white text on it | 13.3 | 10.5 | 8.1 | 6.2 | 4.6 |
| Dark (L .89 → .615) | `#bee5d3` | `#9cd2ba` | `#79bfa1` | `#57ac89` | `#369974` |
| against the paper; paper text on it | 13.5 | 10.9 | 8.6 | 6.7 | 5.3 |

- One text colour on every step in each mode: white in light, the paper's tone in dark.
- Step 1 stands out most from its paper in both modes: deep in light, pale in dark. The order of salience survives the mode, so dark is designed, not inverted.
- The steps sit 0.06 to 0.07 apart in lightness, in one hue: an order, not kinds (Bertin; Brewer's sequential schemes).

### 4.3 The focus form (neutral brand)

| | Light | Dark |
|---|---|---|
| text (the key word) | `#047554`: 5.7 on paper, 5.1 on the tint, 4.5 on the panel | `#91debc`: 11.8, 9.4, 9.3 |
| tint (a region in focus) | `#dff7eb` | `#112d21` |

- *Round 4.* The light text tone is OKLCH L .50, not round 3's .45. At .45 the green read near-black at a glance, so page 2's ownership split was weak. At .50 it is plainly green and still holds 4.5 to 1 on all three grounds it sits on.
- The tint is never the only cue. It always holds the key word in the focus text, so a reader who cannot see the tint still sees the green word and its place (WCAG 1.4.1).

### 4.4 Which of pkit's things take focus (`pkit` notation)

The notation names what is in focus on each page. The brand only says what focus looks like.
- On page 2, **pkit's files** (`core/`, `core.md`) and their tag ("pkit's, replaced"). Yours take no hue: ink.
- On page 3, **the reason** each call is refused.
- On page 4, **the slot that is proven** (`fixers`: its id, the tint on its row) and **the lines that prove it** (the tint on the `bound` lines, and `fixers` in the status heading).

## 5. Shape and line (neutral brand)

| Token | Value | Use |
|---|---|---|
| Corner radius | 8 | Every corner. A wire's elbow is 8 too. A relation that follows an outer corner turns on a concentric arc of 8 + its offset (page 1: 24). |
| **Stroke** | **2 px, the only line weight** | *Round 4.* Container outlines, the dashed outline, dividers, wires, and page 3's stage rules. Round 3 mixed a 0.7 px hairline with 2 px lines (round 3 verdict, page 4). |
| Arrowhead | 12 long, 11 wide, filled | The line stops at its base, and the tip lands exactly on the target's edge. |
| Dashed outline | 2 px, 8 on 6 off, `outline` | Only for what is not decided yet. |

No shadows, no gradients, no window chrome, no hairlines.

## 6. The diagram grammar: one look per kind

*Round 4.* Round 3 drew a capability, a terminal and a page-3 tile in the same grey fill and hairline, so a terminal and a capability looked alike (round 3 verdict, page 4 and Deck). Now every kind has its own look, and nothing else.

| Form | Looks like | Means | Pages |
|---|---|---|---|
| **Block** | a fill of the order ramp, radius 8, text on it | a step of an order. A level is the full block; a stage's rule is the same fill drawn 2 px tall under its name | 1, 3 |
| **Container** | a 2 px outline at 4.3 to 1, paper inside, radius 8 | a thing that holds parts: a capability in its role. Its parts are compartments, wall to wall, split by keyline dividers; its heading is split from them by an outline divider | 4 |
| **Panel** | the panel fill, no line, radius 8, monospace inside | a terminal | 2, 4 |
| **Dashed outline** | a 2 px dashed outline | not decided yet | 1 |
| **Focus** | the focus text on the key word; the tint behind a region | what the point is about | 2, 3, 4 |
| **Outcome** | an ink no-entry disc and its word | a result | 3 |
| **Wire** | 2 px, the relation tone, straight or orthogonal, elbows on radius 8, a filled head where direction means something | a relation | 1, 3, 4 |

**Wire rules,** measured by `svg.check` on every render:
- It starts on its source's edge and its tip lands on its target's edge. Each wire names both, and the check fails an end that is not on that edge.
- It passes no closer than 16 px to any other shape, or 12 px to any text.
- *Round 4.* A wire that **follows** a shape keeps one distance from it all the way: page 1's two relations hold exactly 16.00 px from the steps over 224 sampled points each.
- No two wires cross.
- *Round 4.* A wire into a container lands on the part it relates to. Page 4's wires land on the container's wall at a slot's row. The slots run wall to wall, so the wall there is the slot's own edge.

## 7. Code and terminals

- **A terminal is a panel:** the panel fill, no line, radius 8, 24 px at the sides. It is as wide as its longest line plus 48, so no panel carries a half-empty box (round 3 verdict, page 2). It is 20 px from its top to the first cap height and 22 px under the last baseline.
- **Every command takes the terminal notation:** the `$` prompt, in a panel. Page 2's option, `pkit visibility private`, is now a panel like the two steps. It is made quieter by its place and its label (no number, ink-soft), not by a different notation (round 3 verdict, page 2).
- **Tones by role:** typed text (the command, its arguments) in ink. The prompt `$`, tree guides and a placeholder (`your-project`, Czech `vas-projekt`) in ink-muted. Output labels (`bound`, `(contributes)`) in ink-soft. The word in focus in the focus text.
- **A command is never broken.** It is set on one line at 22 px, so a copy runs.
- **Real output, cut by whole lines,** keeps its real relative indentation. A common indent is removed from all kept lines at once: a crop of the terminal, not a change to it.
- **Lines in focus** take the focus tint edge to edge inside the panel. The band clears the text above it and the text inside it by 12 px or more (measured: 12.0). It runs to the panel's foot, and its bottom corners follow the panel's radius.
- **A diagram is never shown under a prompt.** Page 2's tree is a diagram in tree notation, with no `$ tree` over it.

## 8. The components the pages use

| Component | Belongs to | Form |
|---|---|---|
| Page frame | foundations `deck` | Sections 1 and 2: title, lead, field, source line. |
| Stepped levels | starter (`layers`, a stepped form) | Centred blocks, each 32 px wider on each side than the one above, from the order ramp by place, head and description centred. |
| Stepped relations | starter (`layers`, an option) | *Round 4.* Up to two relations that walk the steps, 16 px outside the stepped edge: down the middle of each 32 px tread, round each outer corner on a concentric arc (radius 24), sharp into each inner corner. Each leaves the first level's side and lands on the last level's top tread: down on the left, up on the right. Their notes stand at the foot, each in its own column, its last line on the last level's last baseline. |
| Undecided note | starter (`card`, dashed) | A dashed box sized to its words. |
| Numbered step | starter (new) | An ink disc (36) with the number in paper, the step's name beside it, and its panel 12 under it. Steps sit 24 apart. |
| Tree | `pkit` notation over starter `list` | Guides in ink-muted, names in mono. Each owned entry is tagged with its owner and what that means; pkit's entries and tags take the focus text, yours stay in ink. |
| Flow-headed table | starter (`table` option) | *Round 4.* Stage names in semibold ink, each on a 2 px rule from the order ramp, the rules joined by wires. Unboxed rows on two shared baselines; every cell's text on its column's edge, the stage name's edge. |
| Outcome cell | starter (new) | *Round 4.* An ink no-entry disc (22) and the outcome's word in regular ink, then the reason in semibold focus text. The repeated word is quiet; the reason that differs carries the weight. |
| Limit band | starter (one pattern) | *Round 4.* Its own band: a 2 px keyline divider across the table, 48 or more above the limit's cap height. "Limit:" semibold ink with a colon, then the limit in ink-soft, body size. |
| Role container | `pkit` notation over the container | *Round 4.* A container headed by the role: "Role" in semibold, the role id in mono ink. The capability that plays it sits second in ink-soft, with what it does ("project-management opens 3 slots"). Then its slots as compartments, wall to wall: the slot id in mono, what it holds in ink, on two shared edges. |
| Filler | `pkit` notation over the container | *Round 4.* The same container in small: the role id in mono ink over the capability's name in ink-soft. One look for "a capability in its role", wherever it stands. |
| Source line | foundations `deck` | "In project-kit: …", 20 px ink-muted, one fact from project-kit itself, no code. |

## 9. The checks every render passes

`svg.check` measures each drawn page; `build.py` prints every fault. All 16 renders pass with none.

| Check | Rule | Measured |
|---|---|---|
| Wire clearance | 16 px from any shape it does not attach to; 12 px from any text | all pass |
| Wire ends | each end on the edge of the shape it names | all pass |
| *New.* **Arrow parallelism** | a wire that follows a shape holds its offset ±0.6 px over every sampled point more than 16 px from its ends | page 1: 16.00 to 16.00 px, both relations, every variant |
| *New.* **No crossings** | no two wires cross | all pass |
| *New.* **One stroke weight** | every stroke on the page is 2 px | all pass |
| *New.* **Container contrast** | every container's line, and every block's fill, at 3:1 or more on the paper; a panel has no line | containers 4.3; the order blocks 4.6 to 13.5 |
| *New.* **Highlight clearance** | 12 px from a tint's edge to the text inside it and to the text beside it | page 4: 12.7 (the `fixers` slot), 12.0 (the status band) |
| *New.* **Even insets** | every container's and panel's nearest text 24 px from its left side, and no text nearer than 24 to its right side | all pass |
| *New.* **Alignment edges** | each named column has at most its stated number of left edges | page 1: [80], [992]; page 4: [966], [80, 427] |
| Text in its holder | 12 px from the sides of what holds it | all pass |
| Margins | everything inside the 80 px side margins | all pass |
| Contrast pairs (`system.py`) | 4.5:1 for every text pair, 3:1 for every line or fill a reader needs | 0 failures, both modes |
