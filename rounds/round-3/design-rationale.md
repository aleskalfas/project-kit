# Design rationale: the four showcase pages (round 3)

Each page runs: structure → form (the alternatives weighed) → hierarchy → type → colour → space → words. Each line names the principle it rests on. The system is in `design-system.md`; what each round 2 finding led to is in `changes.md`; what the engine and libraries would need is in `gaps.md`.

**Shared brief.** Developers new to pkit; a 1280 × 720 slide projected in a room, a PDF handout and a web page; English and Czech; light and dark. So: body at 24 px, nothing under 20, code at 22, no hover, and the point read in about three seconds (Duarte's glance test).

**Shared frame.** The title names the subject; the lead states the point, word for word from the brief, at 30 px in ink; the field is the evidence; the source line is one fact from project-kit itself (Alley: assertion and evidence). The lead is the deck's one way to state a point: on every page it is the second thing the eye meets and the loudest text in the field.

---

## 1. How pkit fits together

**Structure.** An ordered stack of five, the source on top. Three relations: ideas enter at the top; each layer carries out the ones above (down); where a layer and a decision disagree, the layer is checked first (up).

**Form: the stepped pyramid, its two relations parallel to its flanks.**
- *Alternatives weighed.*
  - Short vertical arrows set beside each note (round 2 verdict's first suggestion): each note and arrow would form a unit, but the arrows would span no layers, which is what round 1's verdict failed as "decorations tied to no layer". A relation between layers belongs on the layers (Mackinlay: expressiveness).
  - Both relations as one loop on one side: two parallel arrows of one length cannot be told apart at a glance, and one note would sit beside both.
  - Equal bars (the starter's `layers` today): an order with no shape; the narrow source over the broad base is lost (the brief's original).
- *Chosen.* The original stepped pyramid, narrow and darkest at the top. Each relation runs the whole height of the lower four levels, parallel to the stair line through the levels' outer top corners, **20 px outboard at right angles**, so it clears every corner by the same distance (measured: 20.0 px, against round 2's 0.8). Down on the left, up on the right: together they read as one cycle around the stack. Ideas, not yet decided, sit in a dashed box sized to their words and enter the apex.

**Hierarchy.** Title, then the lead, then the apex: the darkest, narrowest shape, where the squint test lands. Then the levels in order; then the three notes in semibold heads over ink-soft text; then the source line. Three levels of emphasis.

**Type.** Each level's name (24 semibold) over its description (24 regular), centred on the pyramid's axis, since flush-left text in a symmetric shape reads off balance. The notes break by phrase, by hand ("An agent reads / the reasons first."). The widest Czech name, "Pracovní pravidla · schémata · procesy", is checked against its level in the generator.

**Colour.** The order ramp by place, one green: deep to mid in light, pale to mid in dark (Bertin; Brewer, sequential). The levels name no concept, so the pattern shades them by place, which is visual-communication DEC-001 point 6's own example ("a pyramid with no notation still shades its levels by their place"). They drop the content's five concepts because five hues would draw one order as five unrelated kinds, and every layer but the top holds pkit's files and yours side by side, so an ownership hue per level would be false. *Round 3:* white text on all five light steps (every step at 4.5 to 1 or more), so no level looks like another kind. Arrows and the dashed box take no hue: relations, not things.

**Space.** The pyramid stands on the page's axis and fills the field from 224 to 606. Levels 8 apart: one object. The ideas box sits on the 80 px margin with the title. *Round 3:* the two notes are mirror images: each sits beside the middle of its own arrow, flush toward it, its nearest ink 24 px from the line (measured, both sides), so the two relations are drawn alike (Gestalt proximity, Mayer's spatial contiguity). The arrow leans outward as it falls, so a note's top line sits further from it than its bottom line; that lean is the same on both sides.

**Words.** Ideas: "In conversation, / or a scratchpad note." (two lines, so the box fits its words and clears the left arrow; Czech takes three). "Checked first": "Decisions never / bend to the code." (a phrase break, and a measure that fits the right side at 24 px).

---

## 2. Install pkit

**Structure.** A sequence of two steps (once on your machine, then in each project); what a project then holds, pkit's files beside yours in the same folders; an option (keep pkit out of the repository).

**Form: the steps in order, top to bottom; the tree to the right of step 2, as its result; the option as two quiet lines.**
- *Alternatives weighed.*
  - Steps side by side, as round 1's verdict asked: the real URL cannot fit half a page at 22 px, so it must break, and round 2's shell-continuation break gave the reader a command that fails when copied.
  - Both steps stacked full width, the tree under step 2, as round 2's verdict asked: at 24 px body and 22 px code the field holds two step rows and leaves about 110 px, four lines of a tree.
  - The tree in a code panel under a prompt: round 1's verdict failed a listing presented as `tree` output that `tree` would not print.
- *Chosen.* Step 1 takes the full width, because its command is the longest line in the deck and must stay one line. Step 2, whose commands are short, takes the left five columns; the tree takes the right half, headed "Then each project holds", on step 2's own line. Order reads top to bottom, then left to right (Ware: flow follows reading order). The tree is the result of step 2 alone: nothing sits under step 1 but step 2. It is a diagram in tree notation, with no prompt over it, so it claims to be no command's output.

**Hierarchy.** Title and lead; then the two ink discs and step names, the darkest marks; then the commands; then the tree, where violet is the only hue; then the option and the source line, in ink-soft and muted. The option is no longer louder than the steps.

**Type.** Step names 24 semibold; commands 22 mono, the whole typed text in ink and only the prompt and the placeholder `your-project` muted (round 2 greyed the URL, the part that must be typed exactly). The tree's names 22 mono; its tags 24: the owner in semibold, what that means in regular.

**Colour.** pkit's entries (`core/`, `core.md`) and their tag in violet; yours in ink. Ownership is also told by the tag's word and by position in each pair, so colour only confirms (WCAG 1.4.1). Violet appears on no other page.

**Space.** Step 1's panel spans the field. Step 2's head and the tree's head share one baseline; the tree's first line is level with step 2's first command; the tree's last line and the option's last line share one baseline (604), so the two columns start and end together. The option sits 54 px under step 2's panel: a separate group, not a third step (Gestalt proximity).

**Words.** The option: "To keep pkit out of your repository:" then the command, so the intent comes first and the command stands alone on its line, copyable. The tags echo the lead: "pkit's, replaced" and "yours, untouched". The source line names no path, so it needs no code type at 20 px.

---

## 3. Where permissions come from

**Structure.** Three kinds of permission, each passing through the same three stages, each ending refused; one limit; one fact.

**Form: a flow-headed table whose last column is the evidence.**
- *Alternatives weighed.*
  - Three separate flows, one per kind: three times the arrows for one shared sequence; the shared stages would have to be read three times.
  - A 3 × 3 grid of equal cells (round 2): the outcome that proves the point sat as plain text in the last column (round 2 verdict, message).
- *Chosen.* The stages head the columns as three order blocks joined by wires, the deck's one block and wire, in place of round 2's chevrons. The kinds name the rows. The outcome column is the evidence, so each outcome is a highlighted cell: the accent's tint, a no-entry mark, "Refused" in semibold. The three marks in one column are what the squint test finds: every kind ends refused, whether or not the agent remembers.

**Hierarchy.** Title and lead; then the outcome column (the only accent, the only boxed cells); then the row heads and the stage blocks; then the data column in ink; then the middle column, quietened to ink-soft, so the eye runs from the kind to its outcome; then the limit and the source line.

**Type.** Row heads 24 semibold, their tags 20 (furniture). Cells two lines at most, broken by phrase, by hand. *Round 3:* every command, tool name and agent id is mono (`rm -r`, `sudo`, `git push -f`, `critic`, `Read`, `Glob`, `Grep`, `WebFetch`, `project-manager`, `gh`), quoting the files as they are written; names in prose ("from project-management") stay in the sans. "Limit:" with a colon in semibold, the page's one limit pattern.

**Colour.** The stage blocks take the order ramp's steps 3, 4 and 5: the stages are where the permissions live (layer 3), what pkit's commands write for the AI tool (layer 4), and the call on your work (layer 5), so the green means here what it means on page 1. White text on all three. The outcome cells take the accent, and nothing else on the page does. The no-entry mark has its word beside it, so the meaning never rests on colour (WCAG 1.4.1).

**Space.** A 4-column table: labels 232, three equal stages of 264, gutters 32 (equal stages, because the stages are equals). Rows are 80 high with 16 between; the rows' text sits on the cells' two baselines. *Round 3:* the hairline rules are dropped on purpose: the outcome cells set the rows' rhythm, and alignment groups each row (Gestalt; Tufte: less non-data ink). The limit sits 40 px under the last row, ending at 600.

**Words.** "Refused" once per row, with a one-line qualifier: "in every mode", "any tool not listed", "uses pkit's commands". The data cells quote the real deny list and the real agent file (`git push -f` is in the project's deny list; `critic`'s tools are `[Read, Glob, Grep, WebFetch]`). The fact: 14 denies and 62 allows, counted in the project's `.claude/settings.json`.

---

## 4. How capabilities work together

**Structure.** A mapping: two capabilities, each in its role, fill three slots that a third opens under its role. Evidence: `pkit status`. What it gives you: three short benefits. The limit: one capability per role so far.

**Form: fillers on the left, wired into sockets cut into the opener's edge; the proof under it; the benefits beside it.**
- *Alternatives weighed.*
  - Round 2's outlined role frames with slots on the frame: role and slot shared one blue outline, and the slots started at the frame's border while the card above was inset (round 2 verdict, block).
  - Straight wires only, by making the shared slot twice as tall: it needs four slot rows and pushes the proof off the page.
  - The terminal beside the slot: its real line is 853 px wide at 22 px, so it cannot sit beside a diagram.
- *Chosen.* *One shape per kind* (round 2 verdict, change 3): a **capability is a block**; its **role is a tag** on the block's top edge; a **slot is a socket** cut into the opener's left edge, open toward whatever fills it. A filler's wire ends in the socket's mouth, so the picture says "fills the slot that project-management opens under `pkit::work-tracking`", never "names project-management". Each slot shows its real id (`doc-check`, `fixers`, `use-cases`) and what it holds. Each filler sits level with the slot only it fills, so that wire is straight; its wire to the shared `fixers` slot leaves 12 px from its middle, mirrored on the other filler, and turns twice on the deck's radius. No wires cross.
- *The proof.* The real `pkit status` lines for `fixers`, cut by whole lines and dedented together, in a plain panel under the diagram, with the two `bound` lines highlighted in the accent. The `fixers` socket takes the same accent, and its id is the accent word in both places (Gestalt similarity).

**Hierarchy.** Title and lead; then the diagram, its one accent on the `fixers` socket; then the proof, its accent limited to the highlighted lines; then the benefits and the caption in ink-soft. Round 2's terminal was the page's largest mass; now it is three lines under the diagram.

**Type.** Three styles, one each: role ids in mono ink on their tags; capability names in semibold ink; slot text in ink (id in mono, purpose in sans). `pkit validate` and `pkit status` in mono at 22.

**Colour.** Neutral and one accent. No capability colour and no role colour any more: everything on this page is pkit's, so ownership has nothing to tell apart, and the page's shapes carry the kinds. The accent marks only the slot that is proven and the lines that prove it (60-30-10).

**Space.** Two columns: 853 (the terminal's real line, and the diagram above it) and 235, with the 32 gutter. The note column's first line and the opener's tag start on the field's top line; the caption's first baseline is level with the terminal's first. Every text edge inside a block is 24 px from its left edge: tags, names and socket text share it (measured; the round 2 block was a 14 px mismatch). Wires clear every other shape by 23 px or more.

**Words.** The benefits drop the ✓ marks (they read as "done", round 2 verdict) and stand as three two-line items. The caption names the command: "What `pkit status` prints for this slot." The limit becomes the source line, a fact about project-kit: "each of its 3 roles has one capability so far, so a swap is designed, not yet shown."
