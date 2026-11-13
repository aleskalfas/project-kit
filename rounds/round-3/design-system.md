# Design system: the showcase deck's target (round 3)

The system comes first, and the pages follow from it. `tools/system.py` holds every value below as code, and `python tools/system.py` prints every contrast pair the pages use and counts the failures (0). `tools/pages.py` draws each page from those values alone. `tools/build.py` measures each drawn page with `svg.check` and prints any fault (0 on all 16 renders).

Round 3 settles three things once for the deck, each a fix at the root for a round 2 deck finding:

1. **One colour role table** (section 4): every hue has one meaning on every page.
2. **One diagram grammar** (section 6): one shape per kind, one wire, one label rule.
3. **One way to state the point** (section 2): the lead is the page's assertion, set at 30 px in ink.

The two layers stay as in round 2. **The neutral brand** carries what any project needs: grid, type scale, spacing, surfaces, one ordered ramp, one accent, one radius, two strokes. **Project-kit's identity** (what violet means, what a role, a slot and a capability look like) lives in the `pkit` notation library.

---

## 1. Grid (neutral brand)

| | Value | Reason |
|---|---|---|
| Page | 1280 × 720 | A 16:9 slide, also a PDF page and a web page. |
| Columns | 12 × 64 px, gutters 32 | Halves, thirds and quarters land on column edges (Müller-Brockmann). |
| Side margins | 80 px | 12 × 64 + 11 × 32 = 1120 on whole pixels; above the 64 px floor. |
| Top margin | 64 px to the title's cap height | Optical alignment: the capitals sit on the margin. |
| Bottom margin | 64 px to the source line's baseline (656) | Equal to the top: the page is framed evenly and clears projector overscan. |
| **Field** | **y 224 to 608 (384 px)** | *Round 3.* It starts 46 px under the lead's last baseline (178). Inside the header the gap is 24 (title baseline to lead cap), so the header is one group and the evidence another (Gestalt proximity). |

A page may divide the field by its content's own measure where the content sets one: page 3's table is 232 + 3 × 264 with 32 gutters; page 4's columns are 853 | 235, set by the terminal's real line width. Both keep the 80 px margins and the 32 px gutter.

## 2. Type (neutral brand)

One family, Source Sans Pro, in Regular 400 and Semibold 600, and Source Code Pro Regular for code: the brand's shipped fonts, nothing else.

**The scale** is a 1.25 modular scale on a 24 px body (Tim Brown): **20 · 24 · 30 · 38 · 48**, plus 22 for monospace.

| Role | Size / line | Weight, colour | Use |
|---|---|---|---|
| title | 48 / 56, −0.5 tracking | Semibold, ink | The page's anchor; names the subject. |
| **lead** | **30 / 38** | **Regular, ink** | *Round 3.* **The page's point.** One step up the scale from the body, in full ink, two lines broken by sense. |
| head | 24 / 32 | Semibold, ink | The name of a level, a step, a row, a capability. |
| body | 24 / 32 | Regular, ink or ink-soft | Everything read across the room. |
| small | 20 / 28 | Regular | Page furniture only: the source line and a table row's tag. |
| code | 22 / 28 | Regular, mono | *Round 3.* **Every** monospace run, in a panel or inside a sentence. |

- **One way to state the point** (Alley: assertion and evidence; Duarte's glance test). In round 2 the lead sat at body size in grey, quieter than the bold labels under it, so a glance landed on the topic. Now the title names the subject, the lead states the claim at 30 px in ink, and the field is the evidence. The title still anchors (48 against 30, and semibold against regular), and the lead outranks everything in the field.
- **Mono at 22 inside 24 px text.** A Source Code Pro glyph is 0.6 em wide against the sans's ~0.45, so at one size the mono looks a size larger (round 2 verdict, page 4). At 22 it reads as the same size as the 24 px sans around it, and it is the same 22 as in every panel: one code size on every page.
- **What is set in mono**: text as it is written in a file or typed or printed in a terminal. Commands, tool names, agent ids, role and slot ids, paths. Names of things in prose and in diagrams (a capability's name on its block, "pkit") stay in the sans.
- **Three levels of emphasis** on every page: the title and lead; the visual's focal element; everything else. The secondary is de-emphasised (ink-soft), never the primary shouted (Refactoring UI).
- **Line breaks are set by hand, by phrase,** in every narrow block (notes, cells, benefits), and each line is measured against its column in the generator. No line ends on a lone word; in Czech no line ends on a one-letter word or "ve" (Bringhurst).

## 3. Space (neutral brand)

The scale is **4 · 8 · 12 · 16 · 24 · 32 · 48 · 64**.

| Distance | Value | Principle |
|---|---|---|
| A label to the line it labels | 24, nearest ink | Mayer's spatial contiguity; one distance for every arrow label. |
| A wire to any shape it does not attach to | 16 at least (measured: 20 or more on every page) | Ware: connectors read as relations only when they clear what they pass. |
| Inside a block or panel, at the sides | 24 (a tag's pill: 12) | Equal padding, measured from the ink. |
| Inside a panel, top and bottom | 20 from the edge to the cap height, 20 from the last baseline | Optical padding, not line-box padding. |
| Between parts of one group | 8 to 16 | Space inside a group is smaller than space between groups. |
| Between groups | 24 to 48 | The same rule, one level up. |

## 4. Colour: one role table for the deck

*Round 3.* Round 2 gave "pkit's part" a different hue on each page (green, violet, blue, brown). Now each hue has one meaning, on every page where that meaning appears, and nowhere else (Nielsen: consistency; 60-30-10).

| Role | Colour | Means | Second cue (WCAG 1.4.1) | Pages |
|---|---|---|---|---|
| **order** | one green, five steps of lightness | a place in the chain from decisions (step 1) down to your work (step 5) | position and size; the level's name | 1 (the five layers); 3 (the three stages, as layers 3, 4, 5) |
| **pkit's** | violet | a file pkit owns, which each upgrade replaces | the tag "pkit's" beside it | 2 |
| *yours* | no hue: ink | your file, never touched | the tag "yours" beside it | 2 |
| **accent** | one blue: a tint, a 2 px line, a mark | **the proof the page rests on** | a word ("Refused", the slot's id) and a highlight shape | 3 (each outcome); 4 (the `fixers` slot and the status lines that prove it) |
| neutral | paper, surface, keyline, tag fill, outline, ink, ink-soft, ink-muted, relation | everything else: structure, text, relations | | all |

### 4.1 The base (neutral brand)

| Role | Light | Dark | Use |
|---|---|---|---|
| paper | `#ffffff` | `#121416` | The page. Dark is a cool near-black (Material's dark theme). |
| surface | `#edeff1` | `#212326` | A block or a panel. Raised in dark: lighter than the paper. |
| **keyline** | **`#ced1d5`** | **`#35383c`** | *Round 3.* A panel's or block's 1 px edge, 1.5 to 1 against the paper, so a container holds on a projector (round 2's panels were 1.1 to 1). |
| **tag fill** | **`#d2d4d8`** | **`#3a3d41`** | *Round 3.* A role's tag. Ink on it 11.6 and 9.5 to 1. |
| outline | `#7d8085` | `#777b7f` | An outline that carries meaning (a socket, the dashed "undecided" box): 4.0 and 4.3 to 1. |
| ink | `#181b1f` | `#edeff1` | Primary text, 17.3 and 16.0 to 1. |
| ink-soft | `#4f5358` | `#bbbec2` | Secondary text, 7.8 and 9.9 to 1. |
| ink-muted | `#65696f` | `#9b9fa3` | Prompts, tree guides, placeholders, the source line: 5.5 and 6.9 to 1. |
| relation | = ink-soft | = ink-soft | Arrows and wires. A relation is not a thing, so it takes no hue. |

### 4.2 The order ramp (neutral brand), retuned

| | Step 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| Light (OKLCH L .30 → .55) | `#013726` | `#004933` | `#015c41` | `#036f4f` | `#078661` |
| against white; white text on it | 13.3 | 10.5 | 8.1 | 6.2 | 4.6 |
| Dark (L .89 → .615) | `#bee5d3` | `#9cd2ba` | `#79bfa1` | `#57ac89` | `#369974` |
| against the paper; paper text on it | 13.5 | 10.9 | 8.6 | 6.7 | 5.3 |

- *Round 3.* **One text colour on every step, in each mode.** In light every step holds 4.5 to 1 against white, so white text sits on all five; in dark every step holds 4.5 to 1 against the paper, so paper-coloured text sits on all five. Round 2 flipped to ink on its last light step, which made "your code" and "a call meets" look like different kinds (round 2 verdict, pages 1 and 3).
- Step 1 always stands out most from its paper: deep in light, pale in dark, so the order of salience survives the mode (designed, not inverted).
- The steps are 0.06 to 0.07 apart in lightness, one hue: an order, not kinds (Bertin; Brewer's sequential schemes).

### 4.3 The accent (neutral brand)

| | Light | Dark |
|---|---|---|
| tint (a highlighted area) | `#e8f1ff` | `#18273c` |
| line and mark | `#2068cb` (5.4 on paper, 4.7 on the tint) | `#74a6ef` (7.4, 6.1) |
| text | `#0850ab` (7.7 on paper, 6.7 on the tint) | `#a4c6f8` (10.6, 8.6) |

Blue is the accent because it is the hue the deck's two meaningful hues leave free: green is order and violet is ownership. It is Carbon's interactive and selection colour, so a blue-tinted line reads as "marked" to a developer, as a highlighted line in an editor does.

### 4.4 The notation's colour (`pkit` notation)

| | Light | Dark |
|---|---|---|
| pkit's text | `#6e44b0` (6.7 on paper) | `#c6affa` (9.6) |

Yours takes no hue: ink. pkit marks only what is its own.

## 5. Shape and line (neutral brand)

| Token | Value | Use |
|---|---|---|
| Corner radius | 8 | Every corner and every wire's elbow. A tag's pill is fully rounded (half its height). |
| Keyline | 1 px | A block's or panel's edge. |
| Stroke | 2 px | Wires, sockets, the dashed outline, the highlight's line. |
| Arrowhead | 12 long, 11 wide, filled | The line stops at its base; the tip lands exactly on the target's edge. |
| Dashed outline | 2 px, 8 on 6 off, `outline` | Only for what is not decided yet. |

No shadows, no gradients, no window chrome, no hairline rules.

## 6. The diagram grammar: one shape per kind

*Round 3.* Round 2 drew page 1 in filled blocks, page 3 in chevrons, and page 4 in outlined frames with fieldset legends (round 2 verdict, Deck). Now every diagram uses these, and nothing else.

| Form | Means | Pages |
|---|---|---|
| **Block**: a filled rounded rectangle | a thing. Its fill says which kind: an order step (a layer, a stage) or the neutral surface (a capability, a terminal) | 1, 3, 4; 2 (panels) |
| **Socket**: a 2 px outline cut into a block's edge, open on that edge, paper inside | a slot: a place a block opens for another to fill | 4 |
| **Tag**: a filled pill straddling a block's top edge, monospace | a role: what a block plays | 4 |
| **Dashed outline** | not decided yet | 1 |
| **Highlight**: the accent tint with a 2 px accent line (a socket's outline, or a 4 px rule on highlighted lines) | the proof the page rests on | 3, 4 |
| **Wire**: 2 px, the relation tone, straight or orthogonal, elbows on radius 8, a filled head where direction means something | a relation | 1, 3, 4 |

**Wire rules,** measured by `svg.check` on every render:
- it starts on its source's edge and its tip lands on its target's edge;
- it passes no closer than 16 px to any other shape (measured minimum: page 1, 20.0; page 3, 40.0; page 4, 23.0) or 12 px to any text (measured minimum: 20.0);
- two wires leaving one block leave 12 px either side of its middle, so every attachment is alike;
- no two wires cross.

**Label rule:** a label sits beside the middle of its line, its nearest ink 24 px from the line, flush toward it (page 1's notes, both sides, measured).

## 7. Code and terminals

- **Panel:** the surface with a 1 px keyline, radius 8, 24 px at the sides, 20 px above the first cap height and below the last baseline.
- **Tones by role,** ordered in lightness: everything typed literally (command, URL, arguments) in ink; the prompt `$`, tree guides and a placeholder (`your-project`) in ink-muted; output labels (`bound`, `(contributes)`) in ink-soft; a concept in its role colour (pkit's in violet; the slot that is the proof in the accent).
- **A command is never broken.** It is set on one line at 22 px in a panel as wide as it needs (page 2's step 1 is full width). Round 2's `\` and `>` continuation is gone: a reader who copies the line gets a command that runs.
- **Real output, cut by whole lines.** Lines kept together keep their real relative indentation; a common indent is removed from all of them at once, which is a crop of the terminal, not a change to it.
- **Highlighted lines** take the accent tint edge to edge inside the panel, with a 4 px accent rule on the left, as an editor marks lines.
- **A diagram is never shown under a prompt.** Page 2's tree is a diagram in tree notation, with no `$ tree` over it.

## 8. The components the pages use

| Component | Belongs to | Form |
|---|---|---|
| Page frame | foundations `deck` | Section 1 and 2: title, lead (the point), field, source line. |
| Stepped levels | starter (`layers`, a stepped form) | Centred levels, each 32 px wider on each side than the one above, filled from the order ramp by place, head and description centred. |
| Flank relations | starter (`layers`, an option) | Two straight arrows parallel to the stair line through the levels' outer top corners, 20 px outboard at right angles: down on the left, up on the right. Each note beside its middle, mirrored, flush toward its arrow, 24 px from it. |
| Undecided note | starter (`card`, dashed) | A dashed box sized to its words. |
| Numbered step | starter (new) | An ink disc (36) with the number in paper, the step's name beside it, its panel under it. |
| Tree | `pkit` notation over starter `list` | Tree guides in ink-muted, names in mono; each owned entry tagged with its owner ("pkit's" in violet, "yours" in ink) and what that means. |
| Flow-headed table | starter (`table` option) | Stage blocks from the order ramp joined by wires; unboxed rows aligned on two baselines; the last column highlighted as the outcome. |
| Outcome cell | starter (new) | The highlight's tint, a 22 px no-entry mark in the accent, the outcome's word in semibold ink, its qualifier in ink-soft. |
| Limit | starter (one pattern) | "Limit:" semibold ink with a colon, then the limit in ink-soft, body size. |
| Capability | `pkit` notation over starter `card` | A block (surface, keyline), the name in semibold ink 40 px under its top, its role as a tag on its top edge. |
| Role tag | `pkit` notation | A pill in the tag fill, the role id in mono ink, its text on the capability name's left edge. |
| Slot socket | `pkit` notation | A socket cut into the opening capability's edge, facing its fillers; the slot's real id in mono and what it holds in ink, both on the block's text edge. |
| Source line | foundations `deck` | "In project-kit: …", 20 px ink-muted, one fact from project-kit itself, no code. |
