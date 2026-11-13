# Design rationale: the four showcase pages (round 5)

Each page runs: structure → form (the alternatives weighed) → hierarchy → type → colour → space → words, and each point names the principle it rests on.

Related files:
- `design-system.md` holds the system.
- `ledger.md` holds each decision this round settled, with its reason.
- `changes.md` records what each round 4 finding led to.
- `gaps.md` lists what the engine and libraries would need.

**Shared brief.** The readers are developers new to pkit. The page is a 1280 × 720 slide projected in a room, a PDF handout and a web page, in English and Czech, light and dark. That sets the floor: body text at 24 px, nothing under 20, code at 22, no hover. The point must read in about three seconds (Duarte's glance test).

**Shared frame.**
- The title names the subject.
- The lead states the point, word for word from the brief.
- The field is the evidence.
- The source line is one fact from project-kit itself (Alley: assertion and evidence).

The frame is kept from round 4 (ledger L4).

**Shared system (round 5).** This round made one pass at the root, and every page follows from it.
- **The grid.** Twelve columns with one right margin, at 1200. Every box edge and free line sits on a column edge (checked).
- **One bold level** under the lead: the 24 px head.
- **One accent, green, with one meaning:** what proves the title's claim. Order moves to the ink ramp.
- **Five containers, one look each:** block, frame, slot, terminal, note. Only a slot has an outline.

On a page, the green answers "where is the proof?" (Mayer's signalling). Weight answers "what is this called?". Containers answer "what kind of thing is this?" (Bertin: one visual variable, one job).

---

## 1. How pkit fits together

**Structure.** An ordered stack of five, with the source on top, and three relations:
- ideas enter at the top;
- each layer carries out the ones above it (down);
- each layer is checked first against the one above (up).

**Form: the stepped pyramid, its two relations walking the steps.** Kept from round 4, which the critic praised.
- *Alternatives weighed this round (the grid).*
  - **Steps of a whole module (96 px).** Every edge would land on a column. But the base would be 1120 wide, the full measure, and the labels would lose their place beside the lines. A pyramid that fills the page reads as a wall, not a stack.
  - **Four levels on the grid, one level off it.** Five levels with equal steps give ten edges. Forcing one level onto the grid breaks the equal step, which is what makes the shape read as one stair (Gestalt similarity).
  - **Chosen.** Equal steps of half a module (48 per side).
    - Levels 1, 3 and 5 sit on columns 4–7, 3–8 and 2–9. Levels 2 and 4 step out half a module, and the page declares those four edges with their reason (ledger L2).
    - The stack is symmetric on the page's axis, so it reads as one object.
- *Alternatives weighed for the labels.*
  - **At the foot, as in round 4.** The critic failed it: by proximity, both labels read as captions of the bottom layer.
  - **Inside the treads.** At 48 px, a tread has no room for a 24 px line beside a rail.
  - **Chosen.** Each label stands beside its line's middle run, on the third level's riser.
    - It is 24 px from the line on both sides: the left label set flush right to 320, the right one flush left from 960.
    - It is centred on the riser: ink spans 367 to 421, centred on 395, the riser's middle (Gestalt proximity and symmetry).
- *The relations.*
  - Each runs 24 px outside the stepped edge, down the middle of each 48 px tread.
  - Each turns each outer corner on an arc of 32 (the level's radius 8 plus the offset 24) and goes sharp into each inner corner. Measured at 24.00 px over 252 points, both lines, every render (Gestalt continuity).
  - Each leaves the apex 16 px above its foot, clear of the corner radius, and lands on the base's top tread (Ware: a line's ends say what it relates).
  - Ideas, not yet decided, sit in a dashed block as tall as the apex. Its tie meets the apex at the middle of both faces.

**Hierarchy.**
1. The title and the lead.
2. The apex: the darkest, narrowest shape, where the squint test lands.
3. The levels, in order.
4. The two relations, one of them green: the proof.
5. Their labels and the ideas block, then the source line.

Under the lead there is one bold level, the 24 px head: each level's name, "Where ideas start", "Carried out", "Checked first". Descriptions are regular, and the labels' second lines are set in ink-soft (Refactoring UI: emphasise by de-emphasising).

**Type.** Names and descriptions are centred on the pyramid's axis, because flush-left text in a symmetric shape reads off balance. The generator checks that the widest Czech name, "Pracovní pravidla · schémata · procesy", fits its level 16 px clear on each side.

**Colour.**
- *Order: the ink ramp by place* (ledger L7). Light mode runs deep to mid, dark mode pale to mid, so in both modes the source stands out most from its paper (Bertin: lightness is ordered; Brewer, sequential).
  - The ramp is the ink's own slate, so the levels read as one chain, not as kinds, and green is left for one job.
  - White text holds 5.06 on the lightest light step, up from 4.57 (critic's polish).
- *Proof:* the "Carried out" line, in proof ink. It is the lead's own claim, "each carries out the ones above it", drawn.
- The up relation and the ideas tie take the line tone: they are relations, not the proof (60-30-10).

**Space.**
- The stack fills the field from 224 to 606. The levels sit 8 apart, so they read as one object.
- The ideas block hangs on the 80 margin, and its right edge is the fourth level's left edge (320), so it lines up with the stack.
- The labels sit on those same two edges (320 and 960). The page has four vertical edges outside the stack, and each is one the stack makes (Müller-Brockmann: few alignment edges).

**Words.**
- "Carried out / by each layer below" goes with the downward line. "Checked first / against the one above" goes with the upward line (ledger L21). Each reads in its line's direction, and the up arrow no longer suggests "go back and change the decision".
- In Czech, "Provádění / každou vrstvou níž" and "Kontrola / nejdřív proti té nad ní". The ideas line is "In conversation." / "V rozhovoru.", since round 4's two-line version did not fit the apex's height.

---

## 2. Install pkit

**Structure.** A sequence of two steps: once on your machine, then in each project. Then what a project holds, pkit's files beside yours in the same folders. Then an option: keep pkit out of the repository.

**Form: the steps in order, top to bottom; the tree to the right of step 2, as its result.** Kept: the one-line commands and the single tree split pkit's/yours, both praised.
- *Alternatives weighed this round.*
  - **One bracket per category** ("pkit's: replaced on upgrade", "yours: untouched"), as the critic suggested. The owners alternate inside each folder (core, project, core, project). So a bracket around pkit's entries would span one of yours, and two brackets would cross. The page keeps one tag per entry, two words, in the lead's own words (ledger L22). The four tags are now two words, not four phrases, and only pkit's take colour.
  - **The tree as text glyphs** (`├──`, `└──`). At a 32 px pitch the box-drawing glyphs leave gaps between rows. Drawn as 2 px lines in the line tone, the guides are continuous, and they end in a rounded corner on the deck's radius.
  - **The tree as terminal output under `$ tree`.** `tree` would not print the tags, so the page would claim output that is not real. The tree is a frame, a group, with a head.
- *Chosen.* Step 1's terminal spans all twelve columns, because its command is the deck's longest line and is never broken. Step 2's terminal and the option's share columns 0–4. The tree's frame takes columns 6–11.

**Hierarchy.**
1. The title and the lead.
2. The two ink discs and step names.
3. The green bands on pkit's two entries: the page's only colour, and the evidence for the lead's second sentence.
4. The commands.
5. The option and the source line.

The URL no longer dominates. Its argument is set in ink-soft, and its terminal is the deck's quiet code tint (1.16:1), so the squint test lands on the green bands.

**Type.**
- Step names, the option's label and the frame's head are the head level.
- Commands are mono 22:
  - the prompt in muted;
  - the command in ink;
  - the argument (`git+ssh://…`, `your-project`, `private`) in soft (ledger L18).
- Tree names are mono 22. Tags are 24 sans.

**Colour.**
- *Proof:* pkit's entries (`decisions/core/`, `rules/core.md`).
  - Each takes a proof-tint band the height of the line pitch, with its name and "pkit's" in proof ink. These are the files an upgrade replaces.
  - Yours stay ink, tagged "yours" in ink-soft.
- The band is a line highlight, as in a code editor, so it touches its neighbours' pitch but clears their text by 5.9 px. The word "pkit's" and its place carry the meaning without the colour (WCAG 1.4.1).
- The discs are ink, not green: order of steps is told by the number, and green is spent on proof.

**Space.**
- 12 from a disc to its terminal, 32 between steps, and 32 from step 2 to the option's label, whose baseline sits 16 above its terminal (Gestalt proximity).
- The frame starts level with step 2's head (356) and ends level with the option's terminal (601), so the two halves of the page start and end together (Müller-Brockmann).
- Column 5 is left empty as the gutter between the two halves.
- The tree's frame has a 24 px head pad and a 26 px foot pad, optically even.

**Words.** The tags are "pkit's" and "yours" (Czech "pkitu" and "vaše"), the lead's own words, so the evidence answers the claim in its terms (Mayer: spatial contiguity).

---

## 3. Where permissions come from

**Structure.** Three kinds of permission, each through the same three stages, each ending refused. One limit, one fact.

**Form: a flow-headed table.** Kept: the critic praised it.
- *Alternatives weighed this round.*
  - **The qualifiers as the payoff, in bold green** (round 4). They were the loudest text on the page and three different grammatical kinds. Failed.
  - **The outcome as an icon** (a no-entry mark with the word). A second mark beside a word that already says it is decoration (Tufte).
  - **The stage rules in three ramp steps** (round 4). The ramp now means order of layers, and the stages are a flow, not three ranks. Mixed with a grey arrowhead, they also read as two strokes butted together.
- *Chosen.* One proof idea, the path from data to refusal. The spine is one green 2 px line at y 259, with a head at each hand-over and none at the right margin. The outcome is "Refused" in proof ink, regular weight, with its scope under it in ink-soft. The eye runs along the spine and down the green column: written as data, applied, refused (Alley: the evidence proves the claim).

**Hierarchy.**
1. The title and the lead.
2. The spine and the three "Refused".
3. The stage and row heads (the one bold level).
4. The cells, in ink.
5. The scopes, the row tags and the limit's text, in ink-soft.
6. The source line.

Under the lead there are three degrees of emphasis and one bold level. "Limit:" is a head of the same level, naming the note.

**Type.**
- Each line is one face (ledger L20). Data cells are pure mono lines (`rm -r, sudo,` / `git push -f`; `Read, Glob,` / `Grep, WebFetch`). The rule's cell is `project-manager:` in mono, then "only pkit's commands" in sans.
- Row tags are 20 px furniture.
- Commands keep a no-break space (`rm -r`, `git push -f`).

**Colour.** Proof only: the spine and the outcome word. Every other mark is neutral. The outcome is told by its word and its column, and the green confirms (WCAG 1.4.1).

**Space.**
- A label column (columns 0–2) and three stages (columns 3–5, 6–8, 9–11), each 256 wide, every cell on its column's start.
- Rows sit 88 apart on two shared baselines, 34 px between rows.
- The note stands 48 px under the last row, more than the row gap (checked), so the caveat reads as one on the whole table (Gestalt proximity).
- Round 4's keyline divider is gone: the note's own rule does the work.

**Words.**
- The scopes are parallel phrases (ledger L23): "in every mode", "for any other tool", "for raw GitHub changes". In Czech: "v každém režimu", "u jiného nástroje", "u přímé změny GitHubu".
- The stages are "Written as data", "Your AI tool gets" and "A call meets", which read in a row as the lead's sentence.

---

## 4. How capabilities work together

**Structure.** One capability, in its role, opens three slots. Two others, each in its own role, fill them, and both fill the shared `fixers` slot. The evidence is what `pkit status` prints for that slot. The page also says what this gives you.

**Form: the opener's frame of slots, its block at the base; the fillers wired in from the left; the proof cropped under the frame; the benefits under the fillers.**
- *Alternatives weighed this round.*
  - **A two-fill capability box** (a role band over a name band), as the critic suggested. A tie attaches at the middle of a face, which is exactly where the seam between the bands would fall. The chosen block keeps the two parts as two lines on one fill: line 1 is "role" and the role id, line 2 is the name. The same block is used for all three (ledger L12; Nielsen: consistency).
  - **The opener's block at the frame's head** (round 4's order). Each filler then sits level with the slot only it fills, so its tie runs straight, but the left column starts 72 px low under a hole. With the block at the base, the top filler is flush with the frame's top and the bottom filler with the slots' foot (ledger L13).
  - **The terminal beside the frame.** At columns 9–11 the real line `pkit::work-tracking:fixers` would wrap. Under the frame on columns 5–11, it is cropped to three whole lines and 108 px tall. It is smaller than the diagram, and it sits right under the block that names the role.
  - **Ties from block to block.** The lead says a capability names only a role, so ties land on slots, never on the opener.
- *Ties.*
  - The channel between fillers and frame is 140 px, against 49 in round 4.
  - Each filler's tie to the slot only it fills is straight. Its tie to `fixers` branches off at x 492 and turns twice on 16, landing on the slot 10 px either side of its middle.
  - No ties cross, and every tip lands on a slot's edge (checked).
  - The turn is 16, not page 1's 32, because the drop is 46 px: two 32 turns would leave no straight run between them (ledger L17).

**Hierarchy.**
1. The title and the lead.
2. The three capability blocks, the same block, so they read as three of a kind.
3. The slots: the only outlined shapes on the page, and `fixers` the only green.
4. The ties.
5. The status lines, with `fixers` again in green.
6. The benefits and the source line.

**Type.**
- Role and slot ids are mono 22. Capability names are sans 24. "role" is 20 px, a label.
- In the slots, the id is in ink and the purpose in ink-soft.
- "What it gives you" is the head level, and its three items are single lines.

**Colour.**
- Blocks take ramp step 1: no order here, so no rank between them (ledger L7).
- The frame is surface, with no line.
- *Proof:* the `fixers` slot, with a tint fill, a 2 px outline and the id in proof ink, and `fixers` in the status line. The only slot two capabilities fill, and the printed fact that both are bound to it. The same green in both places ties the drawing to its evidence (Gestalt similarity).
- The tint is never the only cue: the outline and the word carry it at 5.07:1 (WCAG 1.4.1, 1.4.11). This answers the critic's 1.13:1 tint finding.

**Space.**
- Fillers take columns 0–3, and the frame and terminal columns 5–11, with one shared right margin at 1200.
- Slots sit in a tray 12 in from the frame, 8 apart.
- The terminal sits 16 under the frame: one evidence unit.
- The benefits' head sits 39 under the lower filler. Items run 40 apart, and the last item's baseline is level with the terminal's last line (584), so the two columns end together.

**Words.**
- The benefits are three single lines: "Swap one for another in the same role.", "Install only what you need.", "`pkit validate` checks the wiring."
- "opens 3 slots" sits on the opener's name line.
- The source line keeps the limit: "each of its 3 roles has one capability so far, so a swap is designed, not yet shown."
