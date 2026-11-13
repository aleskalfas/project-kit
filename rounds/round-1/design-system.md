# Design system: the showcase deck's target

The system comes first, and the pages follow from it. Every value below has a reason and the principle it rests on. The numbers are the ones the mock-ups use. `tools/system.py` holds them as code, and `tools/pages.py` draws each page from them alone, with no raw value in a page.

The system has two layers:

- **The neutral brand.** It ships to every project, so it carries only what any project needs: a calm base, one type scale, one spacing scale, tonal scales for each hue, and one accent. It knows nothing of pkit.
- **Project-kit's identity.** It lives in the `pkit` notation library, or in a project-kit brand if one is made. It holds what the colours *mean* in project-kit's pieces: the layer key, pkit's against yours, and capabilities.

Each section below says which layer it belongs to.

---

## 1. Grid (neutral brand)

| | Value | Reason |
|---|---|---|
| Page | 1280 × 720 | The deck's medium: a 16:9 slide, also a PDF page and a web page. |
| Columns | 12 × 64 px | Twelve divides into halves, thirds and quarters, so 8 \| 4, 5 \| 7 and 3 \| 3 \| 3 \| 3 all land on column edges (Müller-Brockmann). |
| Gutter | 32 px | One step of the spacing scale. It is wide enough to separate panels when projected. |
| Side margins | 80 px | 12 × 64 + 11 × 32 = 1120, so 80 px is what keeps every column, half, third and quarter on whole pixels. It is also above the 64 px floor. |
| Top margin | 64 px, to the title's cap height | The title's capitals sit on the margin line, which is optical alignment rather than the alignment of the line box. |
| Field | y 216 to 640 (424 px) | The one area every page's visual fills. It is the same on every page, so the visual starts where the eye expects it (Nielsen: consistency). |
| Bottom band | 80 px; the source line sits on a baseline 32 px above the edge | The source line is page furniture, like a page number. It sits in the margin band, so the field keeps its height. |
| Baseline grid | 8 px | The title's baseline is at 96, the lead's at 136 and 168, the field starts at 216, and the source line is at 688. All are multiples of 8 (an 8-point system). |

**The page frame, the same on every page.** The title is 48 px at the top left, with its cap height on the 64 margin. Under it sits the lead, two lines, each line broken where the sense breaks, and never as one long line. Under the lead, the field holds the visual. The source line sits at the foot. The point is read in order: title, lead, then the evidence (Alley: assertion and evidence).

## 2. Type (neutral brand)

The deck uses one family, Source Sans Pro, in two weights: Regular 400 and Semibold 600. It uses Source Code Pro Regular for code. These are the brand's shipped fonts, and nothing else is used. In SVG, the semibold is named `font-family="Source Sans Pro" font-weight="600"`, the typographic family its file declares. Its legacy family name, "Source Sans Pro Semibold", is not matched by resvg (see `gaps.md`).

**The scale** is a 1.25 modular scale (Tim Brown) on a 24 px body, rounded to whole even pixels: **20 · 24 · 30 · 38 · 48**. The deck uses 20, 24 and 48. The 30 and 38 steps are reserved for covers and section openers. Code has its own size, 18, because a monospace glyph is 0.6 em wide against the sans's 0.45, so 18 px code carries as much weight as 20 px text (see §6).

| Role | Size / line | Weight | Colour | Use |
|---|---|---|---|---|
| title | 48 / 56, −0.5 tracking | Semibold | ink | The page's anchor; one per page. |
| lead | 24 / 32 | Regular | ink-soft | The assertion, under the title. |
| head | 24 / 30 | Semibold | ink, or the concept's strong tone | The name of a level, a row, a card or a note. |
| body | 24 / 32 | Regular | ink | Text that must carry across the room, such as the why list. |
| small | 20 / 28 | Regular | ink or ink-soft | Descriptions, notes, table cells, the limit, the source line. |
| small-strong | 20 / 28 | Semibold | ink | A run-in label: "Limit". |
| code | 18 / 24 | Regular, mono | the code roles | Terminals and listings. |

**The reasons:**
- One family in two weights keeps hierarchy in size and weight alone (Bringhurst; *Refactoring UI*).
- The title is twice the body size, so it anchors the page without competing with the visual.
- The lead is the body's size but softer in colour, so it reads second and never against the evidence. That gives three levels of emphasis on each page: the title, the visual's focal element, and everything else.
- Line height is 1.17 for the title and 1.33 for 24 px slide text, which runs short lines. It is 1.4 for 20 px text.
- Text is set in sentence case and ragged right.
- Headings are broken by sense, so there is never a lone last word.
- In Czech, a one-letter word (v, k, s, z, o, u, a, i) is bound to the next word, so it never ends a line. This is Czech typographic practice, and the mock-ups apply it to every wrapped line.
- Nothing is under 18 px. Prose is 20 px at least, and 24 px where the room allows.

## 3. Space (neutral brand)

The scale is **4 · 8 · 16 · 24 · 32 · 48 · 64 · 96**, an 8-point system with a 4 for optical work.

| Distance | Value | Principle |
|---|---|---|
| A head to its text | 8 (baseline to cap) | Proximity: a label belongs to what it labels (Gestalt; Mayer's spatial contiguity). |
| Inside a card | 20 to 24 padding; a code panel 24 at the sides, 22 to the cap height and from the last baseline | Equal optical padding: the visible gap is measured from the ink, not the line box. |
| Between parts of one group | 8 to 16 (levels 8, slots 10, list items 24) | Space inside a group is smaller than space between groups. |
| Between groups | 24 to 48 | The same rule, one level up. |
| Lead to field | 48 | The header and the evidence are separate groups. |

## 4. Colour

### 4.1 The base (neutral brand)

| Role | Light | Dark | Contrast | Reason |
|---|---|---|---|---|
| paper | `#ffffff` | `#121416` | | A calm base. Dark mode is near-black and cool, not pure black, which glares when projected (Material's dark theme). |
| surface | `#f2f4f6` | `#1e2124` | | Code panels and quiet fills. In light mode it is a shade below the paper. In dark mode it is raised: lighter than the paper, as Material does it, so it is not an inversion. |
| line | `#d5d8db` | `#35383c` | | Hairline rules and outlines. They group things and add no content. |
| ink | `#181b1f` | `#edeff1` | 17.3 / 16.0 | Primary text. It is a near-black, slightly cool, softer than pure black. |
| ink-soft | `#4f5358` | `#bbbec2` | 7.7 / 9.9 | Secondary text: the lead, descriptions, notes. |
| ink-muted | `#65696f` | `#9b9fa3` | 5.5 / 6.9; 5.0 on surface | Tertiary text: the source line, code comments and prompts. |
| accent | blue 600 `#266ec3` | blue 300 `#93c1fc` | 4.8 / 9.9 | The neutral brand's one accent, for emphasis in a piece with no notation. The showcase does not use it, because in project-kit blue already means *yours* (§4.4). |

Every text pair the pages use meets 4.5:1 (WCAG 1.4.3). Every connector and arrow meets 3:1 against its ground (WCAG 1.4.11). `python tools/system.py` prints each check.

### 4.2 Tonal scales (neutral brand; new)

Each hue the foundations declare (blue, violet, green, orange, red), and the neutral grey, gets an 11-step tonal scale built in OKLCH:

- **One lightness per step in every hue.** The neutral brand already keeps this principle: no hue stands out. It is also what lets a ramp mean the same thing in any hue.
- **Chroma peaks mid-scale and falls at both ends,** so pale tints stay calm and deep shades stay rich. The chroma is clipped to sRGB.

| step | L | neutral | blue | violet | green | orange | red |
|---|---|---|---|---|---|---|---|
| 50 | .975 | `#f4f7fb` | `#f2f7fe` | `#f8f5ff` | `#edfbf4` | `#fef5ee` | `#fff4f3` |
| 100 | .94 | `#e8ebef` | `#dfedff` | `#ede7ff` | `#d9f2e6` | `#fee6d5` | `#fee4e2` |
| 200 | .87 | `#d2d4d8` | `#b9d7fe` | `#d9cbfe` | `#b4e0cb` | `#f7caa9` | `#fec3be` |
| 300 | .80 | `#bbbec2` | `#93c1fc` | `#c6affa` | `#8dceb1` | `#eeae7e` | `#fda19a` |
| 400 | .72 | `#a2a5a8` | `#6ea7f0` | `#af91ee` | `#63b895` | `#de9051` | `#ef7f77` |
| 500 | .645 | `#8b8e91` | `#4c8fe2` | `#9a75df` | `#39a37c` | `#cc7420` | `#df5f5a` |
| 600 | .54 | `#6c6f72` | `#266ec3` | `#7c53c0` | `#07835e` | `#a45803` | `#bd3838` |
| 700 | .49 | `#5e6164` | `#125fb3` | `#6e44b0` | `#047252` | `#904c03` | `#ac262a` |
| 800 | .41 | `#484b4e` | `#004991` | `#56308e` | `#00593e` | `#703a02` | `#8b131a` |
| 900 | .33 | `#333638` | `#00346b` | `#3f1f6d` | `#03402d` | `#522900` | `#69010c` |
| 950 | .27 | `#242729` | `#002550` | `#2e1651` | `#002f1f` | `#3d1d00` | `#4e0308` |

Each family still gives the four roles a piece names, now drawn from the scale:

| Role | Light | Dark | Reason |
|---|---|---|---|
| fill | step 100 | L .27, low chroma (`#282335` violet, `#332215` orange) | A tinted card. In dark mode it is a raised surface with a little of the hue, not a deep shade of it, so the dark stays calm. |
| line | step 600 | step 400 | A connector or an outline in the hue: 4.5:1 or more against the paper. |
| text | step 700 | step 300 | Text in the hue on the paper or the surface: 5.4:1 or more. |
| strong | step 800 | step 200 | Text in the hue on its own fill: 7.5:1 or more. |

### 4.3 The ordered ramp (neutral brand; new)

**The new role.** Each family gets a five-step **ordered ramp**, where step 1 is the strongest. It is the colour of an order: a pattern that shades its items by place uses it (DEC-001 point 6's own case, "a pyramid with no notation still shades its levels by their place").

| | Step 1 | Step 2 | Step 3 | Step 4 | Step 5 |
|---|---|---|---|---|---|
| Light: scale steps | 900 | 700 | 500 | 300 | 100 |
| Light: green | `#03402d` | `#047252` | `#39a37c` | `#8dceb1` | `#d9f2e6` |
| Light: text on it | white 11.8 | white 5.9 | ink 5.5 | ink 9.5 | ink 14.6 |
| Dark: scale steps | 200 | 400 | 600 | 800 | 950 |
| Dark: green | `#b4e0cb` | `#63b895` | `#07835e` | `#00593e` | `#002f1f` |
| Dark: text on it | paper 12.7 | paper 7.8 | white 4.8 | ink 7.3 | ink 12.8 |

**The reasons:**
- The ramp is lightness alone in one hue, because lightness is ordered and hue is not (Bertin; Brewer's sequential schemes).
- The steps are spaced evenly in perceived lightness, about 0.15 L apart, so no step jumps out.
- In the dark, step 1 is the lightest, because what stands out from a dark paper is light. The ramp keeps its order of salience, so it is designed, not inverted.
- The text flips from light to dark where the contrast does. The steps avoid the band near L .57, where neither text colour reaches 4.5:1.

### 4.4 What colours mean in project-kit (project-kit identity, `pkit` notation)

| Meaning | Colour | Second cue | Where |
|---|---|---|---|
| **The layers**, ordered from decisions down to your work | the green ramp, steps 1 to 5 | position, width, labels | Page 1, the pyramid. Page 3, the steps of a call, in the shades of the layers they belong to (steps 3 to 5). |
| **pkit's**, files that pkit owns and each upgrade replaces, and pkit's own vocabulary (roles, its wiring) | violet | a filled ● on files; monospace on roles | Pages 2 and 4. |
| **Yours**, files you own and pkit never touches | blue | a hollow ○ | Page 2. |
| **A capability** | orange: a tinted card, a name in the strong tone | the name itself, and the card | Pages 3 and 4. |

**Why the layers are green, and not pkit's violet as in the Mural deck.** Every layer but the bottom two holds both pkit's and yours: COR beside PRJ, `core.md` beside `project.md`, `core/` beside `project/`. If the pyramid were violet, its bottom level, "your code", would be violet, while one page later violet means "pkit's, replaced by each upgrade". The deck's colours would then contradict each other. A hue of its own for the layers keeps each colour to one meaning on every page.

**Why green.** It is the hue `pkit/decision` already has, and the ramp starts at the decision. Each lower layer is a lighter tint of the decisions' own colour, so the colour itself says "carried out from the decisions above". The hue sits at 165°, a cool, slightly blue green, so it reads as calm rather than as "success".

There are at most three hues and one ramp per deck, all from the brand's scales. Each carries a second cue, so meaning never rests on colour alone (WCAG 1.4.1).

## 5. Shape and line (neutral brand)

| Token | Value | Reason |
|---|---|---|
| Corner radius | **8**, on everything that has corners: cards, panels, levels, chips, the flat ends of steps | One radius makes one family of shapes. 8 is on the spacing scale and survives projection, where 4 blurs to square. |
| Hairline | 1 px, `line` | It separates table rows and outlines a card. It is quiet, because it adds no content. |
| Stroke | 2 px | Connectors, arrows and the dashed outline. They read across a room. |
| Arrowhead | a filled triangle, 10 to 12 long. The line stops at the head's base, so the tip lands exactly on the edge it enters. | Arrows meet their boxes cleanly. |
| Dashed outline | 2 px, 8 on and 6 off, ink-muted | Only for what is not settled yet (a "not yet decided" state). Page 1 uses it for where ideas start. |
| Junction | a 4 px dot where a tie branches | A branch reads as one tie splitting, not as two lines touching. |

No shadows and no gradients. Fills and borders group things and nothing else (Tufte; Mayer's coherence principle).

## 6. Code and terminals (neutral brand; the hues from the notation)

- **Panel:** surface fill, radius 8, padding 24 at the sides, 22 from the edge to the cap height and from the last baseline to the edge. There is no border and no window chrome.
- **Type:** Source Code Pro 18 / 24. It is the floor the brief allows, chosen with a reason. The deck's longest real line (`git+ssh://…@latest` under `uv tool install \`) is 62 characters. A real command cannot wrap, and at 20 px it would not fit any half of the page.
- **Roles,** a restrained palette ordered by importance in lightness:

  | Role | Colour | Example |
  |---|---|---|
  | command | ink | `uv tool install`, `pkit init`, `tree` |
  | argument, output | ink-soft | `your-project`, the URL, `(contributes)` |
  | prompt `$`, comment `#`, a tree's branches | ink-muted | the scaffolding recedes |
  | a concept | its notation colour | `● core/` in violet, `○ project/` in blue, `software-analysis` in orange |

- **Cropping:** show only what carries the point, and say in the rationale what was cut. Inside a structure, such as a tree, mark a cut with `…`, because a missing line there hides something that exists. An excerpt of a command's output keeps the output's own indentation, which shows the depth it was cut from.
- **A chip of code inside prose** (a command in a card) uses the same panel style at chip size: 40 tall, with a 16 inset.

## 7. The components the pages use

| Component | Belongs to | Form |
|---|---|---|
| Page frame: title, lead, field, source line | foundations `deck` | §1 and §2. |
| Stepped levels | starter (`layers`, a new stepped form) | Centred levels, each 32 px narrower on each side than the one below. Filled with the ordered ramp by place. Head and description centred. |
| Note | starter (`card`, with a new marker) | A head and text with no box. Its left edge is a 2 px arrow when the note names a direction. |
| Unsettled thing | starter (`card`, dashed) | A dashed outline, for what is not decided yet. |
| Flow steps | starter (new) | Chevrons: notched where a step receives, pointed where it hands on, flat at both ends of the flow. Filled with ramp steps. |
| Table | starter (`table`) | Unboxed, with hairlines between rows, row heads in head type, cells in small, and one baseline across each row. |
| Card in a concept | starter (`card`) plus the notation | The concept's fill, its name in the strong tone. |
| Slot | starter (new) | A paper-coloured row inset in its owner's card, the place a tie lands. |
| Role chip | `pkit` notation | Monospace 18, violet on the paper, radius 8. |
| Tie | starter (`connector`) | Orthogonal, 2 px, in the notation's colour for what draws it. It branches at a dot, ends in an arrowhead on the slot's edge, and never crosses another tie. |
| Code panel | starter (`code`) | §6. |
| Limit | starter (new, or `aside` as a variant) | A run-in semibold label, then the limit in ink-soft at 20 px. |
| Takeaway | starter (`aside`) | An outlined card: a question as its head, a command chip, one short paragraph. |
| Benefit list | starter (`list`, with a marker) | A ✓ in ink-muted, items at 24 px. |
