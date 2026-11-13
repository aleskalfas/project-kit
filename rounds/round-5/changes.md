# Changes: each round 4 finding, and what round 5 did

Order follows `round-4/verdict.md`. Round 5 is one pass at the root: the grid, the emphasis rule and the containers changed first, and every page took them. The page entries say only what was left.

- "Agreed" means the finding's fix was taken as stated.
- "Differs" says how the fix differs, and why.

Each settled decision, with its reason, is in `ledger.md` (L1–L23). Every render passes the generator's checks with no fault, including the three new ones (`design-system.md` section 10).

## The three changes with the most impact

| Change | What round 5 did |
|---|---|
| 1. Put a grid in the foundations | **Foundations, checked.** Twelve columns of 64, gutters of 32, margins of 80. Every box edge and every free line of text sits on a column edge, and `svg.check` fails any that does not. One right margin, 1200, reached by pages 2, 3 and 4. Page 1 is symmetric on the page's axis and declares its two half-module levels (ledger L1–L3). Agreed. |
| 2. Write one emphasis rule into the foundations | **Foundations and brand, checked.** Under the lead there is one bold level, the 24 px head, never in the accent. There is one accent, green, with one meaning on every page: *what proves the title's claim*. Order moves to the ink ramp, so green never means order. The colour table is in `design-system.md` section 4. The check fails bold at any other size, and bold in green. It also lists where the accent went on each page: one idea per page (ledger L5–L8). Agreed. |
| 3. Rebuild page 4 on one notation | **Notation and page.** One capability block, the same for all three. One container system for the deck. A 140 px channel. The status output cropped to three whole lines, 108 tall, under the frame. Agreed. Differs only in the block's form: two lines on one fill rather than two fills (page 4, first finding). |

## Deck

| Finding | What round 5 did |
|---|---|
| [block] There is no right margin or column grid: content ends at 1149, 1131, 1200 and 1181 | **Foundations.** As change 1. Content now ends at 1180, 1200, 1200 and 1200. Page 1's 1180 is where its right label's words end; its stack and labels hang on the grid's edges and the declared ones. Agreed. |
| [block] Four container languages: filled blocks, flat grey panels, outlined white boxes, bare rules | **Foundations.** Five kinds, one look each, distinct by kind of mark rather than by shades of grey (ledger L9, L10). A block is a solid fill, a frame a quiet tint, a slot the only outline, a terminal a cooler tint, a note a rule. The rule, after Carbon tiles and Stripe's documentation diagrams: quiet tinted surfaces, with a line only where a boundary means something. Agreed, extended from the verdict's "one container component" to one *system*. The pages hold five kinds of thing, and one look for all would hide the difference. |
| [block] Green means order on page 1, ownership on page 2, structure on page 3, focus on page 4 | **Brand.** As change 2. Green is proof on every page: the "carried out" relation (1), pkit's replaced files (2), the spine and "Refused" (3), the slot filled by two and its status word (4). Agreed, with the verdict's own wording, "the evidence for this page's claim". |
| What holds: the frame's positions, the 80 margin, the type scale, designed dark modes | Kept (ledger L4). Page 1's dark ramp still turns lightest at the source. |

## Page 1: How pkit fits together

| Finding | What round 5 did |
|---|---|
| [block] The relation labels sit in the bottom corners, not beside their lines, at unequal distances; the top-right quadrant is empty | **Page.** Each label stands beside its line's middle run, on the third level's riser. It is 24 px from the line on both sides: the left label flush right to 320, the right one flush left from 960. Both are centred on the riser's middle: ink spans 367 to 421, centred on 395, measured. The empty top-right shrinks from about 230 × 290 to the strip beside the apex. Agreed. |
| [polish] The ends jam into the corners of "Decisions" | **Notation and check.** Both relations meet the apex 16 px above its bottom edge, clear of the radius. The ideas tie meets the middle of both faces. The check fails a tie that ends inside a corner's radius (ledger L15). Agreed. |
| [polish] The relation lines are 1.3 px | **Foundations.** One stroke, 2 px, for every line in the deck (checked). Agreed. |
| [polish] The up label reads as "go change the decision" | **Words.** "Checked first / against the one above", which reads in the line's direction and pairs with "Carried out / by each layer below" (ledger L21). Agreed. |
| [polish] White on the lightest step is 4.57 | **Brand.** The order ramp is now the ink's own slate. White holds 5.06 on its lightest step. Agreed. |

## Page 2: Install pkit

| Finding | What round 5 did |
|---|---|
| [block] Three panels take their content's widths, and their right edges meet nothing | **Foundations and page.** Terminals take column spans. Step 1 spans all twelve columns to 1200. Step 2 and the option share columns 0–4. Agreed, as the verdict wrote it. |
| [block] The URL bar is the heaviest object; the ownership evidence is small | **Page.** The URL is set as an argument, in ink-soft, and the terminal is the deck's quiet code tint (1.16:1). pkit's two entries take frame-wide green line bands with green names and tags: the page's only colour, and where the squint test lands. Agreed in aim. Differs in labelling (next row). |
| [block] The panels look like a default Markdown block | **Foundations.** One terminal component, used on pages 2 and 4 (ledger L18): the code fill on column spans; padding 24 in, first baseline 32 down, last 20 up; prompt muted, command ink, argument soft; an optional muted comment. Green is never used for a command, so the terminal cannot collide with proof. Agreed. |
| [polish] Four labels for two categories | **Words.** Each tag is now one word in the lead's own terms: "pkit's" or "yours". Only pkit's take colour. Differs: one tag per entry stays, not one label per category. The owners alternate inside each folder (core, project, core, project), so a bracket around either category would span the other (ledger L22). |
| [polish] The right column starts at 985, aligned with nothing | **Page.** The frame starts on column 6 (656), and the tags on column 10 (1040). The frame's top is level with step 2's head and its foot with the option's terminal. Agreed. |

## Page 3: Where permissions come from

| Finding | What round 5 did |
|---|---|
| [block] The bold green qualifiers are the loudest text and are not parallel | **Foundations and page.** As change 2. The proof is the spine and "Refused", in green at regular weight. The scopes sit under it in ink-soft as parallel phrases: "in every mode", "for any other tool", "for raw GitHub changes" (ledger L23). Agreed. |
| [block] Four bold voices under the title | **Foundations.** One bold level, the 24 px head, for the stage heads, the row heads and "Limit:" (checked). Everything else is regular. Agreed in substance. Differs on "Limit:", which keeps the head weight: it is the same style and level, naming the note as a row head names its row. A run-in head is the note container's form. |
| [polish] The header rule is green, but its arrow turns grey | **Page.** One spine in one colour, green, with heads in the same colour. Agreed. |
| [polish] Mono and sans mixed in one line | **Type.** Each line is one face (ledger L20). The agent rule's cell is `project-manager:` on its own mono line, then "only pkit's commands" in sans. Agreed. |

## Page 4: How capabilities work together

| Finding | What round 5 did |
|---|---|
| [block] A capability in its role is drawn two ways | **Notation.** One block for all three capabilities, columns 0–3 (352 × 72): "role" and the role id on line 1, the capability's name on line 2, ramp step 1 for all (ledger L12). Agreed in substance. Differs in form: two parts as two lines on one fill, not two fills. A tie attaches at the middle of a face, exactly where a two-fill box's seam would fall. |
| [block] The channel is 49 px with tight S-bends | **Page.** The channel is 140 px (432 to 572). Straight ties go to the slot each filler alone fills. Branched ties go to `fixers`, each turning twice on 16. Differs from "page 1's radius": page 1's 32 is a level's radius plus the rail's offset, and a 46 px drop with two 32 turns would leave no straight run (ledger L17). |
| [block] The status panel is the heaviest block, with a 301 px empty field | **Page.** Cropped to three whole lines, dedented together, with a muted `# pkit status` comment flush right on line 1. It is 640 × 108 on columns 5–11, under the frame, and smaller than the diagram (640 × 256). Agreed. |
| [block] Outlined white boxes read as a default flowchart; strokes differ in colour and weight | **Foundations.** The container system: blocks are fills, the role is a frame (a tint), and only the slots carry an outline, because a slot is where a tie lands (ledger L10). One line tone and one weight for every line (ledger L14). Agreed. |
| [polish] The benefits read as one ragged paragraph | **Page.** Three single-line items 40 apart under a head, the last level with the terminal's last line. Agreed. |
| [polish] The `fixers` tint is 1.13:1 and will vanish | **Notation.** The `fixers` slot now has a 2 px outline in proof ink (5.07 on its tint) and its id in proof ink, so the tint is never the only cue. Agreed, with the verdict's second option (a green rule). |
