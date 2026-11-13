# Design rationale: the four showcase pages (round 2)

Each page runs: brief → structure → form (with the alternatives weighed) → hierarchy → type → colour → space → words cut. Each line names the principle it rests on. The system is in `design-system.md`; what each verdict finding led to is in `changes.md`; what the engine and libraries would need is in `gaps.md`.

**Shared brief.** Developers new to pkit; a 1280 × 720 slide projected in a room, also a PDF handout and a web page; English and Czech; light and dark. So: nothing under 20 px, body at 24, no hover, and each point read in about three seconds (Duarte's glance test).

**Shared frame.** The title names the subject; the lead is the assertion, kept word for word; the field is the evidence; the source line is one fact from project-kit itself, "In project-kit: …", on every page (Alley: assertion and evidence).

**How to cut.** Where a page was full at 24 px, the copy was cut, never the type shrunk. The title and lead are untouched on every page.

---

## 1. How pkit fits together

**Structure.** An ordered stack of five, the source on top. Three relations on it: ideas enter at the top; each layer carries out the ones above (down); where a layer and a decision disagree, the layer is checked first (up).

**Form: a stepped pyramid with its two relations drawn along its flanks.**
- *Alternatives weighed.*
  - Round 1's pyramid with the relations as notes in a left column, each with a short arrow: the arrows were tied to no layer, so they read as decorations (verdict, form 3).
  - Equal bars, as the starter's `layers` draws them: an order with no shape, and the "few decisions, much work" proportion is lost.
  - Both relation arrows in one lane on the left flank: two parallel arrows the same length cannot be told apart at a glance, and each note would sit beside both.
- *Chosen.* The relations are relations *between layers*, so they are drawn *on the stack* (Mackinlay: expressiveness). "Carried out" runs down the left flank and "checked first" up the right, both from the second level to the base. Together they read as one loop around the stack: down, then back up to the decisions. Each note sits beside the middle of its own arrow (Mayer: spatial contiguity), clear of it along its whole height.
- *Ideas* sit in a dashed box, because an idea is not decided yet, and enter the apex from the left: the reading order is the idea, then the decision, then the stack.
- *Width* says proportion: the narrow top holds the few decisions, the broad base the large body of work. Each level is 32 px wider on each side than the one above.

**Hierarchy.** The title; then the apex, the darkest shape, where the eye lands after the lead (the squint test finds it first); then the levels in order; then the three notes in ink-soft; then the source line. Three levels of emphasis.

**Type.** Each level holds its name (24 semibold) over its description (24 regular), centred on the pyramid's axis, because a symmetric shape with flush-left text reads off balance. Notes are a 24 semibold head over one 24 px sentence. The widest Czech text, "Pracovní pravidla · schémata · procesy", sets the second level's width with 26 px to spare on each side.

**Colour.**
- The green ordered ramp by place: deep to mid in light, light to mid in dark (Bertin; Brewer, sequential). Every step now holds 3 to 1 against the page, so the base no longer fades (round 1's contrast block).
- The levels drop the concepts the content gave them (decision, rule, skill, core, yours). Colour says what a thing is (visual-communication DEC-001 point 6), and a pyramid that shades by place must name no concept, which is DEC-001's own example. Five concept hues would draw one order as five unrelated kinds, and the lower layers each hold pkit's files and yours, so one ownership hue per level would be false.
- The arrows and the dashed outline take no hue: they are relations, not things.

**Space.** The pyramid stands on the page's axis and fills the field from 208 to 600, so no band is left at the foot. Levels are 8 apart (one object). The ideas box and the left note share the 80 px margin with the title. The two notes sit on one horizontal line, mirrored across the stack.

**Words cut.**
- "Carried out": "Each layer carries out the decisions above it. The reasons stay in one place, where an agent reads them before it changes anything." → "An agent reads the reasons first." The first sentence is the lead, word for word; the drawn arrow says "down".
- "Checked": "If a layer and a decision disagree, the layer is checked first, so decisions never drift to match the code. Only you change a decision." → head "Checked first", text "Decisions never drift to match the code." The head carries the rule; the sentence carries why it matters. "Only you change a decision" was cut: it is true, but it is a second point.
- "Where ideas start": "In conversation, and in a scratchpad note when one needs longer." → "In conversation, or in a scratchpad note."
- Level descriptions: level 2 "for every session and tool" → "in every session"; level 3 "How agents act, in which role, with what rights" → "How agents act, and with what rights"; level 4 "Carry out what is decided, and check every change" → "Carry out decisions, and check each change". At 24 px the full texts touched their levels' edges.
- The source line drops "COR-065", an identifier this audience cannot read.

---

## 2. Install pkit

**Structure.** A sequence of two steps (once on your machine, then in each project); what a project then holds, split into pkit's files and yours; an option (keep pkit out of the repository).

**Form: two numbered steps as equal panels, then the two kinds of file apart by position, then the option as one line.**
- *Alternatives weighed.*
  - Round 1's 8 | 4 brick, with step 2 in the narrow panel above the option card: step 2 grouped with the option, not with step 1 (Gestalt proximity), and the eye landed on the listing (verdict, block).
  - The two steps as stacked full-width rows: the real URL fits on one line, but the rows push the result into a strip a third of the field high.
  - A real `tree` listing, cropped, with annotations outside it: honest, but `tree` interleaves pkit's files and yours line by line, which is the opposite of the point.
- *Chosen.*
  - The steps are two equal panels in one row across the full width, each under a numbered disc and its name, so a sequence of two reads as two (Duarte's glance test).
  - The result is not a command's output, so it is drawn as a diagram, never under a prompt. pkit's files on the left, yours on the right, each a labelled list with a rule. Each row is one place split in two (`.pkit/decisions/core/` beside `.pkit/decisions/project/`), so the rows read across as "pkit's half, your half". Yours has one row more, `src/`, where pkit has nothing: the gap says it.
  - The option is an option, not a step, so it is one quiet line in body type.

**Hierarchy.** The title; then the two discs, the darkest marks on the page, with the step names; then the commands; then the two lists, where violet is the only hue; then the aside and the source line. The aside is no longer louder than the steps: it is body-size ink-soft.

**Type.**
- Commands are Source Code Pro 22 / 28.
- The real install URL is 58 characters, and half the page holds 37 at 22 px. It is broken with the shell's own line continuation: a backslash ends each line, and each continued line shows bash's `> ` prompt. The command, pasted, runs unchanged. It is broken at its slashes, so each line is a whole part of the address.
- The labels are one phrase each, the owner in semibold: "pkit's files, replaced by each upgrade"; "Your files, never touched by pkit".

**Colour.**
- Violet means pkit's: the label, the paths and a 4 px rule (5.45 to 1). Yours is ink with an outline-grey rule (3.96 to 1). The two differ in position, label, lightness and hue, so colour only confirms (WCAG 1.4.1; Bertin: value separates at a distance where hue alone does not).
- The step discs are ink, not a hue: in this deck every hue means a kind of thing, and a step is not one.
- Commands are ink, arguments ink-soft, prompts ink-muted, so the scaffolding recedes.

**Space.** One 6 | 6 split for the steps and the lists, so the page has four vertical edges: 80, 624, 656, 1200 (Müller-Brockmann). Disc to panel 16; steps to lists 40; lists to the aside 52, because the aside is a separate group (proximity).

**Words cut.**
- `$ pkit --version` dropped: a check, not a step.
- The listing: 17 lines → 4 rows a side. Permissions, schemas, scratchpad, the manifest, `.claude/settings.json` and `CLAUDE.md` dropped, with their comments. The point needs the split shown three times, not the inventory. `settings.json`, the one file that merges both, would need a third kind and a key to say so honestly; it is the deck's footnote, not its point.
- The ●/○ marks and the key line dropped: position and the labels now carry what they carried, legibly.
- The aside: "Don't want pkit in your repository? … pkit stays only in your clone, hidden by git's exclude file. Nothing of it is committed, and your agent still uses all of it." → "Not in your repository? `pkit visibility private` keeps pkit in your clone only."
- The source line: "pkit status shows what pkit set up in a project. Optional parts, called capabilities, come later." → a fact from project-kit that shows the split: "69 of pkit's decisions sit in core/, beside 13 of the project's own in project/." (counted in the repository).

---

## 3. Where permissions come from

**Structure.** Three kinds of permission, each passing through the same three stages: a matrix whose columns are a sequence. One limit.

**Form: a table headed by a flow.** Kept from round 1, which scored form 4.
- *Alternatives weighed.* Three cards, each holding its three stages: the stage names repeat nine times, and nothing aligns across the kinds. A swimlane of nine boxes and six arrows: arrows for an order the column position already gives. One vertical flow per kind: the comparison across kinds, that one mechanism serves all three, is lost.
- *Chosen.* The stages are said once, as chevron column heads: notched where a stage receives, pointed where it hands on, flat at both ends of the flow. The rows are unboxed, with hairlines between them, so each row reads across as one story.

**Hierarchy.** The title; the chevrons, the strongest marks, because they carry the structure; the row heads; the cells in ink; the limit; the source line.

**Type.** Cells are now 24 px, at most two lines each in both languages (the build asserts it). Real commands (`rm -r`, `sudo`, `gh`) are monospace at the cell's size, so they read as commands within the sentence. Row tags are 20 px: a tag qualifies its head, and nothing in the point rests on it. The limit is one pattern, shared with any page that states one: "Limit:" with a colon, semibold, then the limit in ink-soft.

**Colour.**
- The chevrons take ramp steps 3, 4 and 5, the shades of the layers each stage belongs to on page 1: permissions are written in layer 3; what the AI tool is given belongs to layer 4, pkit's commands and checks; the call lands on layer 5, your work. Each step now holds 3 to 1 against the page (round 1's contrast block).
- "project-management" in the third row's tag is now ink-soft, like the other tags. Orange means a capability, and this page does not key it.

**Space.** Row heads 3 columns, each stage 3: 3 | 3 | 3 | 3. Rows 96 tall. The table and limit fill the field to 600.

**Words cut.**
- Cells to phrases: "rm -r, sudo and force-push, denied to all" → "rm -r, sudo, force-push: denied" (the row's tag already says "for you and every agent"); "that agent's list of tools" → "its list of tools"; "the hook, before each call" → "a hook, before each call". Czech: "project-manager: žádné změny přímým gh" → "project-manager: bez přímého gh".
- The limit: "A command hidden behind another can slip past." → "One hidden behind another can slip past."
- The source line repeated row 3. It now gives a different fact: "Claude Code's settings, written by pkit from this data, hold 14 denies and 63 allows." (counted in project-kit's `.claude/settings.json`).

---

## 4. How capabilities work together

**Structure.** A mapping. project-management plays the role `pkit::work-tracking` and opens three slots under it; living-docs and software-analysis fill them, four fillings in all. Evidence in `pkit status`. What it gives you. One limit.

**Form: roles as frames, capabilities as their occupants, slots on the role's edge.**
- *Alternatives weighed.*
  - Round 1's cards with role chips inside and slots in project-management's card: the wires ran from capability to capability, the very naming the lead denies (verdict, block).
  - A vertical layout, the role on top with its slots as a row of sockets along its foot and the fillers below: every wire runs straight, but the diagram needs 290 px of height, and the terminal and the benefits would not fit.
  - Slots as small ports on the frame with their text beside them: the UML idiom, but the slot, the thing the lead is about, shrinks to a 16 px square.
- *Chosen.*
  - A role is a frame with its name on its top edge, in monospace, as pkit prints it. The capability that plays it sits inside as a card: the occupant, which a swap would replace.
  - The three slots sit on the left edge of the `pkit::work-tracking` frame, outlined like the frame, because they belong to the role: living-docs' own package names `pkit::work-tracking:fixers`, never project-management.
  - Each wire leaves the frame of the capability that fills, and ends on the slot's edge. No wire touches the project-management card; no arrow runs from capability to capability (Mackinlay: draw the relation the page claims).
  - Fillers are level with the slot each fills alone, so those two wires run straight. Each one's wire to the shared middle slot turns twice in one lane, from opposite sides, so none cross (Ware). One wire per filling: no junction dots.
- *The terminal* shows `pkit status`'s real lines for the shared slot, in their own indentation: the slot named by the role, and the two capabilities bound to it. Their colours match the drawing (blue role, orange capabilities), so the two halves of the page are visibly the same facts. The real indent is 25 columns, so the panel takes the page's full width.

**Hierarchy.** The title; the `pkit::work-tracking` frame, the largest shape; the wires and the other frames; the terminal; the benefits in ink-soft, now quieter than the diagram (round 1's block); the source line.

**Type.** Capability names 24 semibold; slot purposes 24 regular; role names 22 monospace; benefits 24 regular ink-soft with `pkit validate` in monospace; terminal 22.

**Colour.**
- Blue is a role: frames, slots, and the slot's name in the terminal. Orange is a capability: the names, on the deck's grey card. Wires are the neutral relation colour, as on page 1.
- Round 1's peach containers and muddy dark brown are gone: capabilities sit in the deck's one panel (verdict, block). Violet no longer appears here, so it keeps its single meaning, pkit's files (verdict, Deck).

**Space.** The diagram takes 9 columns, the benefits 3, the terminal all 12. The benefits' first line sits on the role frame's name line, one top edge. The diagram and the terminal are 24 apart; the field is full to 608.

**Words cut.**
- The fillers' descriptions ("docs for each reader", "what the software must do") dropped: the role frame says what each is; the point is the wiring.
- "Swap a capability for one in the same role." → "Swap one for another in the same role."
- The limit moved into the source line, merged with project-kit's evidence: "each of its 3 roles has one capability so far, so a swap is designed, not yet shown." It is a fact about project-kit's present state, so it belongs in the line that states such facts. A separate limit block would have crowded the field.
- The terminal keeps four real lines of `pkit status` (the command, the slot, two bindings). The roles summary, the points count and the "data v1 · project-management — filled" line are cut by whole lines.
