# Changes: each round 2 finding, and what round 3 did

Order follows `round-2/verdict.md`. Where a fix is at the root (the system), every page took it and the page entries say only what was left. "Agreed" means the finding's fix was taken as stated; "differs" says how and why.

## The three changes with the most impact

| Change | What round 3 did |
|---|---|
| 1. One colour system with defined roles | **System.** One role table (`design-system.md` section 4): the order ramp (pages 1 and 3), the ownership pair, violet for pkit's against ink for yours (page 2), one accent for the proof (pages 3 and 4), neutral for everything else. Page 4's blue frames and orange names are gone; the white-to-ink flips on pages 1 and 3 are gone. Agreed, with one addition: an accent role, because the verdict's own page 3 and page 4 fixes ask for "the accent". |
| 2. Page 2: steps full width in order, one line each; one tree after step 2 | **Page.** Step 1 full width on one line; step 2 below it; one tree with `core/` beside `project/` and `core.md` beside `project.md`. Differs on the tree's place: beside step 2, not under it (see page 2). |
| 3. Page 4: one shape each; slots inset evenly; labels clear; `fixers` named; terminal cut and highlighted | **Notation and page.** Role = tag, capability = block, slot = socket. Agreed in full, except that the terminal sits under the diagram, not beside the slot (see page 4). |

## Deck

| Finding | What round 3 did |
|---|---|
| Colour changes meaning from page to page (green, violet, blue, brown for "pkit's part") | **System.** As change 1 above. Each hue now appears only where its one meaning does: green on 1 and 3, violet on 2, blue on 3 and 4. |
| Three diagram vocabularies (blocks, chevrons, outlined frames) | **System.** One grammar (`design-system.md` section 6): block, socket, tag, dashed outline, highlight, wire. Page 3's chevrons became order blocks joined by the deck's wire; page 4's frames and legends became blocks, tags and sockets. One wire rule (16 px clearance, measured), one label rule (24 px, measured). Agreed. |
| Each page's point set at body size in grey | **Foundations.** The lead is the point: 30 px, the next step of the scale, in ink, on every page. The title keeps naming the subject. Agreed (the verdict's first option). Making the title the assertion was the other option; the briefs give the point as the lead, so the lead carries it. |
| Code notation varies (partial mono on page 3, sans paths on page 2, greyed URL) | **System.** One rule: mono for what is written in a file or typed or printed in a terminal, at 22 px everywhere, inline too; grey only for the prompt, tree guides and placeholders. Agreed. |

## Page 1: How pkit fits together

| Finding | What round 3 did |
|---|---|
| Diagonal arrows come within about 1 px of the corners of layers 3–5; "Checked first" tip 2 px from layer 2 | **Page.** Each arrow is now parallel to the stair line through the levels' outer top corners and 20 px outboard of it at right angles, so it clears every corner by the same 20 px (measured by the generator's check: minimum 20.0). Round 2 offset the line at the wrong height, which put it through the corners. Agreed with the verdict's second option (keep the diagonals, offset them); differs from its first (short vertical arrows), because round 1's verdict failed arrows that span no layer, and a relation between layers belongs on the layers (Mackinlay). |
| Labels sit unevenly from their arrows (70–100 px against 30–60) | **Shared pattern.** The notes are mirrored: each beside its arrow's middle, flush toward it, nearest ink 24 px from the line on both sides (measured). Agreed. |
| "Where ideas start" box wider than its text; Czech "ve" ends a line | **Page.** The box is sized to its words (24 px each side); Czech takes three lines with "ve scratchpadu." together. Agreed. |
| Mid-phrase breaks in the notes | **Engine and page.** Narrow blocks are broken by phrase, by hand, and each line is measured. Agreed. |
| White text on layers 1–4, ink on layer 5 | **Brand.** The light ramp is retuned so every step holds 4.5 to 1 against white (L .30 to .55): white on all five. Agreed. |

## Page 2: Install pkit

| Finding | What round 3 did |
|---|---|
| [block] File lists in the step columns, so pkit's files read as step 1's result | **Page.** Step 1 spans the full width with nothing under it but step 2. The tree sits beside step 2, on its line, headed "Then each project holds". **Differs** from "under step 2": with body 24 and code 22, two full-width step rows leave about 110 px of the field, four lines of tree, too few to show `core/` beside `project/` in two folders. Beside step 2 keeps the order (top to bottom, then left to right) and gives the tree seven lines. |
| URL broken with `\` and `>` | **Page.** One line, full width, 22 px: the real command copies and runs. Agreed. |
| The URL greyed like the prompt | **System.** Everything typed literally in ink; grey only for the prompt and the placeholder `your-project`. Agreed. |
| Step 2 panel carries an empty third line | **Page.** Panels hold only their lines. Agreed. |
| The footer sets `core/` and `project/` in the sans | **Page.** The source line names no path now ("69 of pkit's decisions sit beside 13 of the project's own, in the same folder"), so it needs no code type at 20 px. |
| Code panels at 1.1 to 1 disappear on a projector | **System.** A 1 px keyline at 1.5 to 1 on every panel and block. Agreed (the verdict's second option). |
| Install steps: side by side (round 1) or stacked (round 2)? | **Principle.** Stacked. A command must stay one line so a copy runs (legibility in the medium, and the handout), and step 1's real command is the longest line in the deck. Reading order carries the sequence either way (Ware). |

## Page 3: Where permissions come from

| Finding | What round 3 did |
|---|---|
| A 3 × 3 grid of equal weight; the outcome not emphasised | **Page and shared pattern.** Each outcome is a highlighted cell: the accent's tint, a no-entry mark, "Refused" in semibold, a one-line qualifier. The middle column is quietened to ink-soft. The three marks in one column are the squint test's focal point. Agreed. |
| Code font inconsistent (`rm -r` mono, `sudo`, `gh`, tool names in sans) | **System.** Every command, tool name and agent id in mono, quoting the files. Agreed. |
| Header text white on two chevrons, ink on the third | **Brand.** The retuned ramp: one text colour on every step. Agreed. |
| Mid-phrase breaks; Czech single last word; English cell flush to the right edge | **Page.** Cells set by hand, by phrase; every line measured against its column; equal stage columns of 264 with 32 gutters, taking width from the label column (232). Agreed. |
| Faint rules | **Page.** Dropped on purpose: the outcome cells set the rows' rhythm and two shared baselines group each row. Agreed (the verdict's second option). |
| Chevrons | **System.** Replaced by order blocks joined by the deck's wire, so the page draws its flow in the same grammar as pages 1 and 4. |

## Page 4: How capabilities work together

| Finding | What round 3 did |
|---|---|
| [block] Slot boxes start at the frame's border; the bar above is inset | **Notation.** The slots are sockets cut into project-management's edge, open toward their fillers, as the verdict's second option describes. Every text edge in a block, tag, name and socket text alike, is 24 px from its left edge (measured). Agreed. |
| Roles and slots share one blue outline; arrows leave from frame edges with no logic; no slot ids | **Notation.** Role = a filled tag on a block's top edge; capability = a block; slot = an outlined socket. Each filler's wires leave its block's right edge, 12 px either side of its middle; the slots carry their real ids (`doc-check`, `fixers`, `use-cases`). Agreed. |
| No focal point; the terminal the largest mass | **Page.** The terminal is three real lines, dedented together, in a plain panel under the diagram; its two `bound` lines are highlighted in the accent, as is the `fixers` socket. **Differs** on the place ("beside that slot"): the real line is 853 px at 22 px, too wide to sit beside a diagram; under it, with the same accent on both, keeps the link (Gestalt similarity). |
| Five styles at one size | **Notation.** Three: role ids in mono on their tags, capability names in semibold, slot text in ink. The benefits and caption are ink-soft. Agreed. |
| Role labels' descenders 2 px above the bars | **Page.** Tags straddle the block edge with the name 40 px under the top; the generator checks a 12 px minimum between any text and the side of what holds it. Agreed. |
| ✓ marks read as "done"; mono `pkit validate` larger than the sans; Czech "ve" | **Page and system.** The marks are gone; inline mono is 22 in 24 px text; Czech copy rebroken. Agreed. |
| The limit | Kept in the source line as a fact about project-kit (round 2's choice, not faulted). The note column's second slot names the evidence: "What `pkit status` prints for this slot." |

## Disagreements, in short

1. **Page 1:** the diagonal relations stay, offset 20 px at right angles, against the first suggestion of short vertical arrows: a relation between layers is drawn on the layers (round 1's verdict failed the short arrows).
2. **Page 2:** the tree sits beside step 2, not under it: under it, the field holds only four lines of tree.
3. **Page 4:** the terminal sits under the diagram, not beside the slot: its real line is wider than the space beside any diagram.
4. **Deck:** an accent role is added to the verdict's "ramp, ownership pair, neutral", because its own page 3 and page 4 fixes need one emphasis colour that means neither order nor ownership.
