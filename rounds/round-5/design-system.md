# Design system: the showcase deck's target (round 5)

The system comes first, and the pages follow from it.

- `tools/system.py` holds every value below as code. Run on its own, it prints every colour pair the pages put one on another, each with its WCAG floor, and counts the failures: 0.
- `tools/pages.py` draws the four pages from those values alone.
- `tools/build.py` measures each render with `svg.check` and prints any fault: 0 on all 16 renders.

Round 5 is one pass at the root, and it settles three things for the deck. Each decision, with its reason, is in `ledger.md`.

1. **A 12-column grid in the foundations, checked** (section 1). Every box edge and every free line of text sits on a column edge, and the right margin is 1200 on every page.
2. **One emphasis rule** (sections 2 and 4). Under the title and lead there is one bold level. There is one accent with one meaning, *proof of the title's claim*, written as a colour table every page obeys. Order moves to the ink ramp, so green never means order.
3. **One container system** (section 6). There are five kinds, each with a look of its own: block, frame, slot, terminal and note.

The two layers stay as before.
- **The neutral brand** carries what any project needs: the grid, the type scale, spacing, the neutrals, the ink ramp, one accent, one radius and one stroke.
- **Project-kit's identity** lives in the `pkit` notation library: what a role, a slot and a capability look like, and which of pkit's things are the proof on each page.

---

## 1. Grid (neutral brand)

| | Value | Reason |
|---|---|---|
| Page | 1280 × 720 | A 16:9 slide, which is also a PDF page and a web page. |
| Columns | 12 × 64 px, gutters 32 | Halves, thirds and quarters land on column edges (Müller-Brockmann). Column and gutter sum to 96, a multiple of 8. |
| Side margins | 80 px | 12 × 64 + 11 × 32 = 1120 on whole pixels, above the 64 px floor. |
| Column starts | 80, 176, 272, 368, 464, 560, 656, 752, 848, 944, 1040, 1136 | Where a box's left edge, or a free line of text, may start. |
| Column ends | 144, 240, 336, 432, 528, 624, 720, 816, 912, 1008, 1104, 1200 | Where a box's right edge, or a flush-right line, may end. |
| Top margin | 64 px to the title's cap height | Optical alignment: the capitals sit on the margin. |
| Bottom margin | 64 px to the source line's baseline (656) | Equal to the top, so the page is framed evenly. |
| Field | y 224 to 608 | 46 px under the lead's last baseline, against 24 inside the header, so the header reads as one group and the evidence as another (Gestalt proximity). |

**The grid check.** The generator fails a page when any of these is off the grid:
- a block, frame, slot, terminal, dashed box or note with a left edge that is not a column's start, or a right edge that is not a column's end;
- free text that is not on a column edge (a line set flush left starts on a column's start, a line set flush right ends on a column's end).

Two kinds of edge are exempt, because something else sets them:
- what a frame holds is set by the frame's inset: page 2's bands, page 4's slots;
- text inside a container is judged with its container.

A page may declare an edge of its own geometry, by name and reason. Only page 1 does: its second and fourth levels step out half a module, at 416/864 and 320/960 (ledger L2). The check prints every declared edge.

**Measured.** Every render has 0 grid faults.
- Content reaches 1200 on pages 2, 3 and 4.
- Page 1 is symmetric about the page's axis. Its stack spans columns 2–9, and its right label ends where its words end (1180).

## 2. Type (neutral brand)

The fonts are those the brand ships, and nothing else: Source Sans Pro in Regular 400 and Semibold 600, and Source Code Pro Regular.

**The scale** is a 1.25 modular scale on a 24 px body (Tim Brown): **20 · 24 · 30 · 38 · 48**, plus 22 for monospace.

| Role | Size / line | Weight | Use |
|---|---|---|---|
| title | 48 / 56, −0.5 tracking | Semibold | The page's anchor; names the subject. |
| lead | 30 / 38 | Regular | The page's claim, in two lines broken by sense. |
| **head** | **24 / 32** | **Semibold: the one bold level** | Names a thing: a level, a step, a row, a stage, a frame, a list, "Limit:". |
| body | 24 / 32 | Regular | Everything read across the room. |
| small | 20 / 28 | Regular | Furniture only: the source line, a row's tag, the "role" label. |
| code | 22 / 28 | Regular, mono | Every monospace run, in a terminal or inside a line. |

**The emphasis rule** (ledger L5, L6) gives three degrees of emphasis and no more:
1. the title and the lead;
2. under them, the head level, set in semibold 24;
3. everything else, in regular weight.

The accent is a colour and never a weight: the generator fails bold text in proof ink, and bold at any size but 24. What is secondary is set in the soft or muted tone rather than having the primary shouted (Refactoring UI).

**Faces.** Mono is for text as it is written, typed or printed: commands, paths, tool, agent, role and slot ids. Names of things stay in the sans. Each line holds one face. The only exception is one command that is the subject of a sentence ("`pkit validate` checks the wiring"), set at 22 inside 24 so the two read as one size.

**Line breaks** are set by hand, by phrase, and each line is measured against its column. No line ends on a lone word. In Czech, no line ends on a one-letter word (Bringhurst).

## 3. Space (neutral brand)

The scale is **4 · 8 · 12 · 16 · 24 · 32 · 48 · 64**.

| Distance | Value | Principle |
|---|---|---|
| Inside a block, frame or terminal, at the sides | 24 to the text | Equal padding. |
| Inside a terminal, top and bottom | first baseline 32 down, last baseline 20 up | Optical: about 16 from the edge to the cap height, and 15 under the descender. |
| A frame's inset around what it holds | 12 (page 4's slots); 8 (page 2's bands) | A tray is tighter than a frame's text padding, so the parts read as the frame's contents. |
| Inside a slot, to its text | 12 | So each slot's id shares an edge with the block text above it (584). |
| A tie to any shape it does not attach to | 16 or more; to any text, 12 or more | A line reads as a relation only when it clears what it passes (Ware). |
| A relation that follows a shape | a constant 24, held to ±0.6 | Parallel means one distance (Gestalt continuity). |
| A disc to its terminal; a label to its terminal | 12; 16 from the label's baseline | Parts of one group sit close (Gestalt proximity). |
| Between steps, and between a list and what is above it | 32 | Groups stand apart. |
| Between table rows | 34 from descender to cap | |
| Before a note that covers a whole table | 48, and at least 12 more than between the rows (checked) | A caveat on the whole table stands apart from its last row. |

## 4. Colour: the colour table every page obeys

| Role | What it looks like | Means, on every page | Second cue (WCAG 1.4.1) | Pages |
|---|---|---|---|---|
| **neutral** | paper, surface, code, ink, ink-soft, ink-muted, and one line tone | structure, text, relations, and everything that is not proof | | all |
| **order** | a block's fill from the ink ramp: five steps of the ink's own slate | **a place in an order**, the step at the source standing out most. Only blocks take it. With no order, every block takes step 1. | position, size, each step's name | 1 (five levels); 4 (step 1 for all three capabilities: no rank) |
| **proof** | a line or a word in proof ink; a region in proof tint | **what proves the title's claim.** One idea per page. Never weight. | the word itself, its place, its label | 1: the "Carried out" relation. 2: pkit's entries, which upgrades replace. 3: the spine of stages and "Refused". 4: the `fixers` slot and `fixers` in the status output. |

Order and proof never cross. Order is only ever a block's fill. Proof is only ever a line, a word or a tint region, and never a block's fill. One accent in one role is the whole budget (60-30-10; Albers: one colour, one job). A reader who sees green on any page looks there for the evidence.

### 4.1 The neutrals

| Role | Light | Dark | Use |
|---|---|---|---|
| paper | `#ffffff` | `#121416` | The page. Dark mode uses a cool near-black (Material's dark theme). |
| surface | `#f3f4f6` (1.10) | `#1c1e21` (1.11) | A frame: a group's quiet ground. |
| code | `#e8eff5` (1.16) | `#1f252a` (1.19) | A terminal: cooler and a step deeper than a surface, so a terminal is never mistaken for a group. |
| line | `#767b80`: 4.27 on paper, 3.88 on surface | `#7c8186`: 4.70, 4.25 | Every neutral line: a slot's outline, the dashed outline, the note's rule, tree guides, ties. |
| ink | `#171b20` (17.3) | `#edeff1` (16.0) | Primary text; the step disc. |
| ink-soft | `#4b5056` (8.1) | `#bbbec2` (9.9) | Secondary text: descriptions, tags, arguments, scopes. |
| ink-muted | `#5f646a` (6.0; 5.1 on code) | `#9ea2a6` (7.2; 6.0 on code) | Prompts, comments, the source line. |

### 4.2 The order form: the ink ramp

| | Step 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| Light (OKLCH L .28 → .54, C .032, h 255) | `#1e2a39` | `#2e3a4a` | `#3f4b5c` | `#505d6e` | `#627081` |
| white text on it | 14.5 | 11.5 | 8.9 | 6.7 | 5.1 |
| Dark (L .90 → .64) | `#d0e0f4` | `#bbcade` | `#a7b6c9` | `#93a1b4` | `#7f8ea0` |
| paper text on it | 13.8 | 11.1 | 9.0 | 7.0 | 5.5 |

- There is one text colour on every step in each mode. The lightest light step holds 5.1, up from round 4's 4.57.
- Step 1 stands out most from its paper in both modes: deep in light and pale in dark. The order of salience survives the change of mode, so dark mode is designed, not inverted.
- The ramp has one hue at a low chroma, so it reads as one chain and not as kinds (Bertin; Brewer's sequential schemes). It also leaves green free to be the only hue on the page.

### 4.3 The proof form

| | Light | Dark |
|---|---|---|
| ink (a line, a word) | `#047554`: 5.71 on paper, 5.07 on the tint, 4.92 on code, 5.19 on surface | `#82d9b4`: 11.0, 8.4, 9.2, 10.0 |
| tint (a region) | `#dcf8ea` | `#113124` |

The tint is never the only cue. It always holds a word in proof ink, and on page 4 it also has a 2 px outline in proof ink. A reader who cannot see the tint still sees the green word or line, and its place.

### 4.4 What is proof on each page (`pkit` notation)

The notation names the proof on each page. The brand says only what proof looks like.

| Page | Claim | Proof |
|---|---|---|
| 1 | each layer carries out the ones above it | the relation "Carried out" |
| 2 | upgrades replace pkit's files, never yours | pkit's entries in the tree (`decisions/core/`, `rules/core.md`) and their word "pkit's" |
| 3 | your AI tool applies the rules to every call, so they hold | the spine from data to call, and "Refused" |
| 4 | any other capability can fill a slot | the `fixers` slot, filled by two, and `fixers` in `pkit status` |

## 5. Shape and line (neutral brand)

| Token | Value | Use |
|---|---|---|
| Corner radius | 8 | Every box corner. |
| Stroke | 2 px, the only weight | Every line: outlines, dashes, rules, guides, ties, the spine (checked). |
| Line tone | `line` (section 4.1) | Every neutral line. A proof line takes proof ink at the same weight. |
| Arrowhead | 12 long, 11 wide, filled | The line stops at its base, so the tip lands on the target's edge. |
| A tie's turn | radius 16 | Page 4's ties. |
| A following relation's turn | 8 + its offset on an outer corner (page 1: 32); sharp on an inner corner | Concentric with the shape it follows, so the offset holds. |
| Dashed outline | 2 px, 8 on 6 off | Only for what is not decided yet. |

There are no shadows, no gradients and no window chrome.

## 6. Containers: one look per kind

| Kind | Looks like | Means | Pages |
|---|---|---|---|
| **Block** | a ramp fill, radius 8, paper text, no line | a thing. Its step is its place in an order; with no order, step 1 | 1 (levels), 4 (capabilities) |
| *undecided block* | the same shape with a 2 px dashed outline, no fill | a thing not decided yet | 1 (where ideas start) |
| **Frame** | the surface fill, no line, radius 8; named by a semibold head 24 in, or by a block at its corner | a group: what belongs together | 2 (what a project holds), 4 (project-management with its slots) |
| **Slot** | paper inside a 2 px outline at 3:1, radius 8, inside a frame | an opening that something fills; the tie lands on its edge | 4 |
| **Terminal** | the code fill, no line, radius 8, mono 22/28 | what is typed or printed in a shell | 2, 4 |
| **Note** | a 2 px rule at its left in the line tone; its text 16 right of it; "Limit:" as its head | a qualification of what is above it | 3 |

Kinds differ by their means, not by shades of one grey:
- a block is a solid fill;
- a frame is a quiet tint;
- a slot is the only thing with an outline;
- a terminal is a cooler tint;
- a note is a rule.

A boundary is drawn as a line only where it means something: a slot is where a tie lands (ledger L10). Everything else is grouped by tints and spacing, in the way Carbon tiles and Stripe's documentation diagrams group things.

## 7. Relations

- A tie is a 2 px line in the line tone, or in proof ink when it is the proof. It is straight or orthogonal, and has a head only where direction means something.
- It starts on its source's edge and its tip lands on its target's edge: at the middle of a face, or at one fixed offset clear of the corner radius (checked).
- It passes 16 px or more from any shape it does not attach to, and 12 px or more from any text (checked).
- No two ties cross (checked).
- A relation that follows a shape keeps one distance from it all the way. Page 1's two relations measure 24.00 px from the steps over 252 sampled points each, on every render.
- A second tie to a shared target branches off the straight tie and turns twice on 16 (page 4).

## 8. Code and terminals

- **One component** (ledger L18):
  - the code fill, with no line and radius 8;
  - on column spans: page 2's step 1 spans all twelve columns, step 2 and the option columns 0–4, and page 4's status columns 5–11;
  - text 24 px in, the first baseline 32 down, the last 20 up, lines 28 apart.
- **Tones by role:**
  - the prompt `$` and comments in ink-muted;
  - the command in ink;
  - an argument or placeholder (the URL, `your-project`, `private`) in ink-soft;
  - output labels (`bound`, `(contributes)`) in ink-soft;
  - the proof word in proof ink.
- **A command is never broken.** It stays on one line at 22 px, so a copy runs.
- **Real output is cut by whole lines and dedented together.** On page 4 the cut keeps the slot line and its two `bound` lines, with their real 2-space nesting. The command that printed them ends line 1 as a muted comment, `# pkit status`.
- **A diagram is never set under a prompt.** Page 2's tree is in a frame, with its guides drawn as 2 px lines and no `$ tree` above it.

## 9. The components the pages use

| Component | Belongs to | Form |
|---|---|---|
| Page frame | foundations `deck` | Sections 1 and 2: title, lead, field, source line. |
| Stepped levels | starter (`layers`, stepped) | Centred blocks from the ink ramp by place. Each is 48 wider on each side than the level above, so the apex spans columns 4–7 and the base columns 2–9. The head and description are centred. |
| Stepped relations | starter (`layers`, an option) | Up to two relations that walk the steps 24 px out, down the middle of each tread. Each leaves the apex 16 px above its bottom edge and lands on the base's top tread. Their labels sit beside the middle riser, 24 from the line on each side, centred on it. |
| Undecided block | starter (`card`, dashed) | A block's shape with a dashed outline. Page 1's sits as tall as the apex, and its right edge is on the fourth level's left edge. |
| Numbered step | starter (new) | An ink disc (36) with its number in paper and the step's name hung beside it. Its terminal sits 12 under the disc. |
| Owned tree | `pkit` notation over a frame | Mono names, with guides drawn as 2 px lines that end in a rounded corner. pkit's entries take a proof-tint band the height of the line pitch (32), with the name and the word "pkit's" in proof ink. Yours are ink, with "yours" in ink-soft. Tags sit on column 10. |
| Flow-headed table | starter (`table` option) | Stage names in semibold, over one 2 px spine with a head at each hand-over. A label column (columns 0–2) and three stages (columns 3–5, 6–8, 9–11). Rows have no boxes, two lines each, and every cell sits on its column's start. |
| Outcome cell | starter (new) | The outcome's word, then its scope under it in ink-soft. On page 3 the word is the proof, so it takes proof ink, in regular weight. |
| Note | starter (new) | The note container: a rule, "Limit:", the text. |
| Capability in its role | `pkit` notation over a block | A block of columns 0–3 (352 × 72). Line 1 is "role" (20 px) and the role id (mono). Line 2 is the capability's name. The same block for every capability. |
| Role's slots | `pkit` notation over a frame | A frame with its slots in a tray 12 in, and the opener's block at its bottom-left corner, with "opens 3 slots" on the block's second baseline. |
| Source line | foundations `deck` | "In project-kit: …", 20 px ink-muted, one fact, no code. |

## 10. The checks every render passes

`svg.check` measures each drawn page, and `build.py` prints every fault. All 16 renders pass with none.

| Check | Rule | Measured |
|---|---|---|
| *New.* **Grid** | every box edge on a column edge; every free line on a column's start, or its end when flush right; declared edges printed with their reasons | 0 faults; page 1 declares 4 edges |
| *New.* **One bold level** | bold only at 24 px; never in proof ink | 0 faults |
| *New.* **Where the accent went** | every proof-ink run and every tint region, listed per page | one idea per page (section 4.4) |
| Tie clearance | 16 from any shape it does not attach to; 12 from any text | all pass |
| Tie ends | each end on the edge of the shape it names, and clear of its corner radius | all pass; page 1 meets the apex 16 above its foot |
| Parallelism | a following relation holds its offset ±0.6 | 24.00 to 24.00 px, both relations, every render |
| No crossings | no two ties cross | all pass |
| One stroke weight | every stroke 2 px | all pass |
| Boundary contrast | a slot's and a dashed line at 3:1; a block's fill at 3:1; a terminal or a frame has no line | lines 4.27 (light), 4.70 (dark); blocks 5.06 and up |
| Text in its holder | 12 from the sides of what holds it (16 when centred) | all pass |
| Alignment edges | at most the stated left edges per named column | page 2: [80]; page 4: [80] |
| Margins | everything inside 80 to 1200 | all pass |
| Contrast pairs (`system.py`) | 4.5 for every text pair; 3 for every line or fill a reader needs | 0 failures in both modes |

Round 4's highlight-clearance check (12 px around a tint's text) is withdrawn. Page 2's bands are line highlights, the height of the line pitch, as in a code editor: 5.9 px clear of the lines above and below. Page 4's slot tint is the slot itself, bounded by its outline.
