# Design system: the showcase deck's target (round 2)

The system comes first, and the pages follow from it. `tools/system.py` holds every value below as code, `tools/pages.py` draws each page from those values alone, and `python tools/system.py` prints every contrast pair the pages use and counts the failures (0).

The system has two layers, as in round 1:

- **The neutral brand** ships to every project, so it carries only what any project needs: a calm base, one type scale, one spacing scale, tonal scales, an ordered ramp, one corner radius and two strokes. It knows nothing of pkit.
- **Project-kit's identity** lives in the `pkit` notation library. It holds what each hue *means* in project-kit's pieces (section 4.4).

What changed from round 1, in one line each, is in `changes.md`.

---

## 1. Grid (neutral brand)

| | Value | Reason |
|---|---|---|
| Page | 1280 × 720 | A 16:9 slide, also a PDF page and a web page. |
| Columns | 12 × 64 px, gutters 32 px | Halves, thirds and quarters land on column edges (Müller-Brockmann). The pages use 6 \| 6, 9 \| 3, 3 \| 3 \| 3 \| 3 and the full 12. |
| Side margins | 80 px | 12 × 64 + 11 × 32 = 1120, so 80 keeps every column on a whole pixel. Above the 64 px floor. |
| Top margin | 64 px, to the title's cap height | Optical alignment: the capitals sit on the margin. |
| **Bottom margin** | **64 px, to the source line's baseline** | *Round 2.* It equals the top margin, so the page is framed evenly, and the source line clears projector overscan. Round 1 left 33 px. |
| **Field** | **y 208 to 608 (400 px)** | *Round 2.* Every page's evidence starts and ends on these two lines. It starts 40 px under the lead's last baseline, so the header is one group and the evidence another (Gestalt proximity: title to lead 14 px of white, lead to field 34). |
| Source line | baseline 656 | Page furniture, outside the field. |

**The frame, the same on every page:** the title, then a two-line lead broken where the sense breaks, then the field, then one source line. The point is read in that order (Alley: assertion and evidence).

## 2. Type (neutral brand)

One family, Source Sans Pro, in Regular 400 and Semibold 600, and Source Code Pro Regular for code. These are the brand's shipped fonts; nothing else is used.

**The scale** is a 1.25 modular scale on a 24 px body (Tim Brown): **20 · 24 · 30 · 38 · 48**. The pages use 48, 24 and 20. 30 and 38 are reserved for covers and section openers.

| Role | Size / line | Weight | Use |
|---|---|---|---|
| title | 48 / 56, −0.5 tracking | Semibold | One per page, the anchor. |
| lead | 24 / 32 | Regular, ink-soft | The assertion. Same size as the body, softer, so it reads second. |
| head | 24 / 32 | Semibold | The name of a level, a step, a row, a note, a capability. |
| body | 24 / 32 | Regular | Everything a reader must read across the room. |
| small | 20 / 28 | Regular | Page furniture only: the source line, and a table row's tag. Never content a point depends on. |
| code | 22 / 28 | Regular, mono | Terminal panels and listings. |

**The reasons:**

- **Body is 24 px and nothing is under 20** (round 1's verdict, change 1). A projected 1280 × 720 slide is read from the back of a room; 24 px is the size the brief asks for "where it can be", and here it can be everywhere, because the copy was cut to fit (Reynolds: signal over noise). Every cut is listed per page in `design-rationale.md`.
- **Code is 22 px.** A monospace glyph is 0.6 em wide against the sans's ~0.45, so a 22 px command is as wide per character as 29 px text. 24 px code would push the real commands off any half page. Code inside a sentence (`pkit validate`, `rm -r`, `gh`) is set at the sentence's own size, because Source Code Pro and Source Sans Pro share an x-height (480 and 486 units): at one size the two read as one line.
- **Three levels of emphasis** on every page: the title; the visual's focal element (the darkest level, the numbered steps, the flow, the role frame); everything else. Hierarchy is carried by size, weight and colour, and the secondary is de-emphasised rather than the primary shouted (Wathan and Schoger, *Refactoring UI*).
- **Line height** 1.17 for the title, 1.33 for 24 px text, 1.27 for code, so terminal lines stay one block.
- **Sentence case, ragged right.** No wrapped line ends on a lone word: the wrapper (`tools/svg.py`) brings the word before it down (Bringhurst). In Czech a one-letter word is bound to the next.

## 3. Space (neutral brand)

The scale is **4 · 8 · 16 · 24 · 32 · 48 · 64**, an 8-point system with a 4 for optical work.

| Distance | Value | Principle |
|---|---|---|
| A label to what it labels | 8 to 16 | Proximity; Mayer's spatial contiguity. |
| Inside a panel | 24 at the sides; 20 from the edge to the cap height, and from the last baseline to the edge | Equal optical padding, measured from the ink, not the line box. |
| Between parts of one group | 8 to 16 (levels 8, slots 10, list items 16) | Space inside a group is smaller than space between groups. |
| Between groups | 24 to 48 | The same rule, one level up. |

## 4. Colour

### 4.1 The base (neutral brand)

| Role | Light | Dark | Use |
|---|---|---|---|
| paper | `#ffffff` | `#121416` | The page. Dark is a cool near-black, not pure black, which glares when projected (Material's dark theme). |
| surface | `#f2f4f6` | `#212326` | The one container: code panels and capability cards. In dark it is raised, lighter than the paper, so dark mode is designed, not inverted. |
| line | `#d5d8db` | `#35383c` | Hairline rules between table rows only. They group and carry nothing. |
| **outline** | **`#7d8085`** | **`#717579`** | *Round 2.* An outline a reader must see: the dashed "not yet decided" box and the rule beside your files. 3.96 and 3.98 to 1 against the paper (WCAG 1.4.11). Round 1 outlined an aside at 1.43 to 1. |
| ink | `#181b1f` | `#edeff1` | Primary text, 17.3 and 16.0 to 1. |
| ink-soft | `#4f5358` | `#bbbec2` | Secondary text and the lead, 7.8 and 9.9 to 1. |
| ink-muted | `#65696f` | `#9b9fa3` | Tertiary: the source line, prompts and comments, 5.5 and 6.9 to 1 (5.0 and 5.9 on the surface). |
| **relation** | **`#4f5358`** | **`#bbbec2`** | *Round 2, named.* Arrows and wires. A relation is not a thing, so it takes no hue, on every page. |

### 4.2 Tonal scales (neutral brand)

Unchanged from round 1: an 11-step scale per hue (blue, violet, green, orange, red) and for the greys, built in OKLCH with one lightness per step in every hue, chroma peaking mid-scale. Each family gives `fill` (step 100), `line` (600), `text` (700) and `strong` (800) in light, and `line` 400, `text` 300, `strong` 200 in dark.

### 4.3 The ordered ramp (neutral brand), rebuilt

The colour of an order: a pattern that shades its items by place uses it. **Round 2 rule: every step holds 3 to 1 against the paper in both modes**, because a level or stage that fades into the page drops out of the order it belongs to (WCAG 1.4.11; round 1's two contrast blocks). Lightness alone carries the order, in one hue (Bertin; Brewer's sequential schemes).

| | Step 1 | Step 2 | Step 3 | Step 4 | Step 5 |
|---|---|---|---|---|---|
| Light L | .32 | .395 | .47 | .54 | .645 |
| Light green | `#013d2a` | `#03543b` | `#016c4d` | `#07835e` | `#47a17e` |
| against the paper | 12.3 | 9.0 | 6.5 | 4.8 | 3.2 |
| text on it | white 12.3 | white 9.0 | white 6.5 | white 4.8 | ink 5.5 |
| Dark L | .885 | .815 | .745 | .675 | .605 |
| Dark green | `#bde4d1` | `#9bd1b8` | `#78be9f` | `#55aa88` | `#329671` |
| against the paper | 13.4 | 10.7 | 8.5 | 6.6 | 5.0 |
| text on it | paper 13.4 | 10.7 | 8.5 | 6.6 | 5.0 |

- **Light runs deep to mid; dark runs light to mid.** Step 1 is always the step that stands out most from its paper, so the order of salience survives the mode change: designed, not inverted.
- **The steps skip L .57 to .62**, the band where neither white nor ink text reaches 4.5 to 1. In light, the text flips once, between steps 4 and 5; in dark it never flips.
- **Chroma falls toward the light end** (0.40 to 0.90 of the hue's peak), so the pale steps stay calm and the dark mode stays quiet (Material's dark theme).

### 4.4 What each hue means in project-kit (`pkit` notation)

One meaning per hue, on every page (Nielsen: consistency). Four hues, each with a second cue, so meaning never rests on colour alone (WCAG 1.4.1).

| Meaning | Colour | Second cue | Pages |
|---|---|---|---|
| **The layers**, ordered from decisions down to your work | the green ramp, steps 1 to 5 | position, width, the names | 1 (the levels); 3 (the stages, in the shades of the layers they belong to: steps 3, 4, 5) |
| **pkit's**: files pkit owns and each upgrade replaces | violet | position (the left list), the label "pkit's files", a violet rule | 2 |
| **A role**: what a capability plays, and where slots hang | blue | a frame with the role's name on its edge, in monospace, as pkit prints it | 4 (the frames, the slots, and the slot's name in the terminal) |
| **A capability**: an optional part of pkit | orange | the name itself, on the deck's card | 4 (the cards, and the names in the terminal) |
| *Yours* | no hue: ink | position (the right list), the label "Your files", a neutral rule | 2 |
| *A relation* (an arrow or a wire) | no hue: `relation` | the arrowhead | 1, 4 |

- **Why roles take blue, not violet.** In round 1 violet meant pkit's files on page 2 and roles on page 4, two meanings for one hue (verdict, Deck). Roles now take the hue no other meaning uses.
- **Why yours takes no hue.** Your files are the ordinary case; pkit marks only what is its own. That frees blue for roles and leaves the deck four hues, not five.
- **Why the layers are green, not violet.** Every layer but the top holds pkit's and yours side by side (COR beside PRJ, `core.md` beside `project.md`), so a violet stack would contradict page 2. Green is the hue of `pkit/decision`, and the ramp starts at the decisions: each lower layer is a lighter shade of the decisions' own colour.
- **60-30-10.** Each page is mostly paper and ink; its one hue (or, on page 4, its blue frames and orange names) takes the visual and nothing else.

## 5. Shape and line (neutral brand)

| Token | Value | Use |
|---|---|---|
| Corner radius | 8 | Every corner: levels, panels, cards, frames, slots, chevron ends. 4 for the 4 px rules. |
| Hairline | 1 px, `line` | Table rows. |
| Stroke | 2 px | Arrows, wires, frames, slots, the dashed outline. They read across a room. |
| Arrowhead | 12 long, 11 wide, filled; the line stops at its base | The tip lands exactly on what it enters. |
| Dashed outline | 2 px, 8 on 6 off, `outline` | Only for what is not decided yet (page 1's ideas). |
| Rule | 4 px, radius 2 | Marks a list as one group, in its group's colour (page 2). |

No shadows, no gradients, no window chrome. Fills and borders group things and say what they are, and nothing else (Tufte; Mayer's coherence).

## 6. Containers: one per meaning

Round 1 had four container languages (verdict, Deck). Round 2 has one per kind of thing, the same on every page:

| Form | Means | Pages |
|---|---|---|
| Surface panel, no border | a container of content: a terminal, or a capability | 2, 4 |
| Ramp fill | a layer, or a stage of a layer | 1, 3 |
| 2 px outline in a hue | a boundary that is part of the meaning: a role and its slots | 4 |
| Dashed outline | not decided yet | 1 |
| A rule and a label, no box | a list of files | 2 |
| Hairlines, no box | rows of a table | 3 |

## 7. Code and terminals

- **Panel:** surface, radius 8, 24 px sides, 20 px from the edge to the first cap height and from the last baseline to the edge.
- **Roles,** ordered by importance in lightness: the command in ink; arguments and output in ink-soft; the prompt `$`, the continuation prompt `>` and comments in ink-muted; a concept in its notation colour (a role in blue, a capability in orange, pkit's files in violet).
- **Real output only, cropped by whole lines,** in the output's own indentation. A listing that no command prints is drawn as a diagram, never under a prompt (round 1's `tree` block).
- **A real command never wraps typographically.** Where a line is too long for the column, it is broken with the shell's own continuation, a backslash at the end of the line, and each continued line shows the terminal's `> ` prompt, as bash prints it. The pasted command still runs.

## 8. The components the pages use

| Component | Belongs to | Form |
|---|---|---|
| Page frame | foundations `deck` | Sections 1 and 2. |
| Stepped levels | starter (`layers`, a stepped form) | Centred levels, each 32 px narrower on each side than the one below, filled from the ramp by place, head and description centred. |
| Flank arrows | starter (`layers`, an option) | Two straight arrows parallel to the stack's flanks, 28 px out, from the second level to the base: down on the left, up on the right. Each has its note beside its middle. |
| Note | starter (`card`, no box) | A head and one sentence, no box. |
| Undecided thing | starter (`card`, dashed) | Dashed outline. |
| Numbered step | starter (new, or `panels` option) | An ink disc (36) with the number in the paper colour, the step's name beside it, then its panel. |
| File list | `pkit` notation over starter `list` | A label (the owner in its colour, then what that means in ink-soft), a 4 px rule in the owner's colour, paths in mono. |
| Flow-headed table | starter (`table` option) | Chevron column heads from the ramp; unboxed rows with hairlines; row head plus 20 px tag; cells in body type, at most two lines. |
| Limit | starter (new, one pattern) | "Limit:" in semibold ink, with a colon, then the limit in ink-soft, in body type. |
| Role frame | `pkit` notation | A 2 px blue outline; the role's name on its top edge in blue monospace; the playing capability inside as a card; slots on its left edge. |
| Slot | `pkit` notation | A 2 px blue outline row on the role frame's own edge, paper inside, its purpose in body type. A wire that fills it ends on that edge. |
| Capability card | `pkit` notation over starter `card` | The surface panel, the name in orange semibold. |
| Wire | starter (`connector`) | Orthogonal, 2 px, `relation`, one per filling, an arrowhead on the slot's edge; none cross. |
| Benefit list | starter (`list`, ✓ marker) | ✓ in ink-muted, items in ink-soft body type. |
| Source line | foundations `deck` | "In project-kit: …", 20 px ink-muted, one fact from project-kit itself. |
