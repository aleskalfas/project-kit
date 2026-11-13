# Design rationale: the four showcase pages

Each page follows the same order: the brief, then structure → form → hierarchy → type → colour → space, each step with the principle it rests on. Then come the alternatives rejected, and the words changed and why. The system each page draws from is in `design-system.md`, and what the engine would need to draw it is in `gaps.md`.

**The brief shared by all four pages:**
- **Audience:** developers new to pkit. They know git, a terminal and an AI coding tool, but not pkit's words.
- **Medium:** 1280 × 720, projected in a room, also read as a PDF and on a web page.
- **Consequences:** text no smaller than 18 px, nothing that depends on hover, and every point readable in a glance of a few seconds (Duarte's glance test).

**The frame shared by all four pages:**
- The title states the subject.
- The lead is the assertion, kept word for word from the content (Alley: assertion and evidence).
- The field shows the evidence.
- The source line grounds the page in project-kit itself.

Rendered files: `<n>-<slug>.<en|cs>.<light|dark>.svg` and `.png` beside this file.

---

## 1. How pkit fits together

**Brief.**
- **Point:** pkit is five layers. Each one carries out the ones above it, and the decisions sit on top.
- **Structure:** an ordered stack of five, plus three relations: where ideas enter, the downward relation (carried out) and the upward one (checked).
- **Audience need:** a mental model to hang everything else on.

**Structure.**
- The content is an order, not a set. So the order must be the first thing seen, and it must be seen from position alone (Mackinlay: position is the most effective channel for ordered data).
- The three notes are relations on that order, not more items in it, so they sit apart from the stack.

**Form.** A **stepped pyramid**, centred, of five levels:
- **Width.** Each level is 32 px wider on each side than the one above, so the levels read as one object. The narrow top holds the few decisions, and the broad base holds the large body of work that carries them out.
- **The notes,** in the left five columns, are the relations:
  - "Where ideas start" is a **dashed** card, because an idea is not decided yet. Its arrow runs, level with the apex's middle, into "Decisions": ideas enter at the top and nowhere else.
  - "Carried out" and "Checked" are directions. Each is a note whose left edge is a drawn arrow, down and up, so the direction is drawn, not typed as a glyph.
- **Reading order.** The notes sit left of the pyramid, so they are read in order: an idea, then the decision it enters, then the stack.

**Hierarchy.**
- The title comes first.
- Then the pyramid, whose darkest level is "Decisions": the focal point, at the top, where the eye lands after the lead.
- Then the notes, in ink-soft at 20 px.
- The source line comes last.
- Three levels of emphasis, no more.

**Type.**
- Each level holds its name as a head (24 semibold) and its description below (20 regular), both centred on the pyramid's axis. Centred, because the level is a symmetric shape, and text set flush left inside a centred step reads as off balance.
- Notes are left-aligned, with heads at 24 semibold.
- The longest Czech head, "Pracovní pravidla · schémata · procesy", fits its level at 24 px, which set the level widths.

**Colour.**
- The levels are the **green ordered ramp**, steps 1 to 5, darkest at the top in light mode and lightest at the top in dark mode: lightness for order (Bertin; Brewer, sequential).
- The concepts the content gave each level (decision, rule, skill, core, yours) are dropped, because the decisions require it:
  - Colour says *what a thing is* (DEC-001 point 6), and shading by place needs levels that name no concept.
  - Five concept hues made a rainbow that read as five unrelated kinds, not one order.
  - The bottom levels hold both pkit's files and yours, so a single ownership colour on a level would be false. Page 2 uses violet and blue for ownership, and they must mean only that.
- Arrows and the dashed outline are ink-soft and ink-muted. They are relations, not things, so they carry no hue.

**Space.**
- The pyramid takes the right seven columns (560 to 1200), and the notes the left five.
- Levels are 8 apart: one object, close-set (Gestalt proximity).
- Notes are 48 apart: separate thoughts.
- The pyramid's top starts on the field's top, 216, the same line on which every page's evidence starts.

**Rejected alternatives.**
- **Equal-width stacked cards**, as the content's `layers` draws today: an order without shape reads as a list, and the "few decisions, much work" proportion is lost.
- **Each level in its concept's colour**, as the content declares: a rainbow with no order, and it contradicts page 2's violet and blue.
- **Concentric rings:** the order reads inside-out with no clear direction, and text must curve or crowd.
- **Notes on the right:** ideas would enter against reading order, and the "Carried out" arrow would point away from the levels it describes.
- **↓ and ↑ glyphs in the note heads:** a typed arrow is a word-sized hint, and a drawn one, the note's height, says direction to the whole note.

**Words changed.**
- **The run-in heads of levels and notes** ("Decisions. Choices you…") became a head on its own line above its text. A level is read as a name first, and the run-in made every level one long line.
- **"↓" and "↑" dropped** from "Carried out" and "Checked": the drawn arrows say them.
- **"Each layer carries out the decisions above it." dropped** from "Carried out": the lead says it word for word, two lines above.

---

## 2. Install pkit

**Brief.**
- **Point:** install the tool once, add pkit to a project with one command, and pkit's files live apart from yours, so an upgrade replaces only pkit's.
- **Structure:** a sequence of two steps (once, then per project), then the result (the files pkit leaves), then an optional choice (keep pkit out of the repository).
- **Audience need:** commands they can type, and trust that pkit will not overwrite their work.

**Structure.**
- Steps come before the result, and the result before the option, so that is the reading order: top row, then bottom row; left, then right.

**Form.**
- **The commands as code panels:** real, copyable commands, because a developer trusts a command more than a description of one.
  - "Once, on your machine" and "in each project" are two panels, so the once / each split is seen, not read.
- **The result as a real `tree` listing:** a form every developer knows, which proves the lead's second sentence.
  - Each of pkit's files is marked ●, and each of yours ○.
  - The folders that hold both are split on one line (`agents/ ● core/ ○ project/`), so "apart" is visible in each line.
- **The option as an outlined card,** a takeaway set apart from the main path. Its head is the developer's own question, and its command sits in a chip.

**Grid.**
- The URL under `uv tool install \` is a real 62-character line. At 18 px it needs eight columns, so step 1 takes eight and step 2 the remaining four.
- The bottom row keeps the same split, with the tree in eight columns and the card in four, so the two rows form one 8 | 4 brick and every edge aligns (Müller-Brockmann).

**Hierarchy.**
- The commands are first in reading order.
- The tree is the largest and the visual focus. The marks ● and ○ are the only colour in it.
- The card is quietest: an outline, not a fill. It is an option, not a step.

**Type.**
- Code is Source Code Pro 18/24, the floor, set by the URL (see `design-system.md` §6).
- The card's head is broken by sense: "Don't want pkit / in your repository?" and "Nechcete mít pkit / v repozitáři?".
- The card's text is 20 px.
- In the Czech lead, each sentence takes its own line.

**Colour.**
- **Violet** means pkit's (●), and **blue** means yours (○). The mark is a second cue, so ownership survives greyscale, forced colours and colour-vision deficiency (WCAG 1.4.1).
- The last line of the tree is the key, set in the same notation, so the colours are explained where they are used (Mayer: spatial contiguity).
- Commands are ink, arguments ink-soft, and prompts, comments and the tree's branches ink-muted, so the scaffolding recedes.

**Space.**
- The panels are 32 apart across the gutter and 24 apart between rows. The rows are one group of steps and their result.
- Inside the tree, comments start at one column (32), so they read as a second column of meaning.
- The card's head, chip and text are 28 apart.

**Rejected alternatives.**
- **One tall code panel holding both steps**, as the content declares: the once / each split becomes a comment line, and the panel takes a full column the tree needs.
- **A boxes-and-lines file diagram:** it loses the real command a developer can run, and it would draw more than it explains.
- **Colour without the ● / ○ marks:** it fails WCAG 1.4.1, and the marks are already in the content.
- **The card under the commands in a left column**, as the content nests it: the tree, the page's evidence, was pushed into a narrow column at the right.

**Words changed.**
- **`$ pkit --version` dropped.** It is a check, not a step. It cost a line in the panel that sets the grid, and the footer already points to `pkit status`.
- **The tree is cut from 17 lines to 11:**
  - It keeps the three split folders (agents, decisions, rules), one line of the rest, `.claude/settings.json`, `CLAUDE.md`, `src/` and the key.
  - It drops permissions, schemas, scratchpad, skills and the manifest, with their comments.
  - "● …  # and more of pkit's" becomes "● ○ …  # and more of both" ("a další, obou druhů"), because the lines cut hold both kinds.
  - `.claude/` and `settings.json` are joined onto one line.
  - The page's point needs the split, shown three times. It does not need the inventory.
- **The run-in key moved into its own line** at the tree's foot, unchanged in words.

---

## 3. Where permissions come from

**Brief.**
- **Point:** permissions are rules your project writes down as data. The AI tool applies them to every call, so they hold even when an agent forgets them.
- **Structure:** three kinds of permission, each passing through the same three stages: a matrix whose columns are a sequence.
- **Audience need:** to see that one mechanism covers all three kinds.

**Structure.**
- The three stages are the same for every kind, so they are said once, as columns, and each kind is a row.
- The table's two axes are the page's two ideas: what is guarded (the rows), and how a rule gets from data to a call (the columns).

**Form.** A **table headed by a flow**:
- The column heads are **chevrons**. Each is notched where it receives and pointed where it hands on, and the flow is flat at both ends. They read as one flow from data to the call.
- The rows are unboxed, with hairlines between them. Each row's three cells share one baseline, so a row reads across as one story: "rm -r … denied to all → a deny in its settings → refused, in every mode".

**Hierarchy.**
- The chevrons are the strongest marks on the page, because they carry the structure.
- Next come the row heads, 24 semibold.
- Then the cells, 20 regular in ink.
- The limit line is quietest, below the table.

**Type.**
- **Cells are 20 px.** Three stage columns of 256 px each, at 24 px, would break several cells onto three lines, and the rows would no longer line up. At 20 px, every cell in both languages fits in two lines, which the build asserts.
- Row heads take a 20 px tag in ink-soft beneath them.
- Cells start 28 px inside their column, so they align with the chevrons' labels above them.

**Colour.**
- The chevrons are steps 3, 4 and 5 of the green ramp, from strong to light, in the order of the flow (lightness for order). The steps are the shades of the layers each stage belongs to on page 1:
  - the permissions, written as data, are layer 3;
  - what the AI tool is given to check calls against belongs to layer 4, the checks;
  - the call itself acts on layer 5, your work.

  So the ramp has one meaning across the deck.
- **"project-management" is orange,** because it names a capability.
- No other colour: the cells are ink, so the matrix stays calm.

**Space.**
- Row heads take three columns, and each stage takes three: 3 + 3 + 3 + 3.
- Rows are 100 tall, which fits a two-line cell with room above and below.
- The chevrons sit 16 above the first row.
- The limit's baseline sits 45 below the last hairline, apart from the table but read with it.

**Rejected alternatives.**
- **Three cards side by side, each holding its three run-in lines,** as the content's `groups` draws them: the stage names repeat nine times, and across the cards nothing aligns, so the kinds cannot be compared.
- **A swimlane diagram, with nine boxes and six arrows:** it draws arrows for an order that column position already gives.
- **One vertical flow per kind:** the comparison across kinds, the point that one mechanism serves all three, is lost.
- **Stage heads as plain text:** the columns read as three facts, not one flow.

**Words changed.**
- **The run-in labels** "Written as data:", "Your AI tool gets:" and "A call meets:" became the three column heads, said once.
- **A label "Limit" ("Omezení")** now leads the limit's text. The content gives the limit as a field with no label, and on the page it must say what kind of sentence it is.

---

## 4. How capabilities work together

**Brief.**
- **Point:** a capability never names another, only a role. A capability that needs something opens a slot, and any other can fill it.
- **Structure:** a network (two contributors, one provider with three slots, four ties), its evidence in `pkit status`, then what it buys you, and its limit.
- **Audience need:** to see the slot, the thing that makes capabilities swappable, and to see that pkit reports it.

**Structure.**
- The diagram is the main evidence.
- The terminal proves the diagram is real, so it sits directly under it (Mayer: spatial contiguity).
- The benefits and the limit are consequences, so they sit in a column of their own.

**Form.** A **slot diagram**:
- **The provider** (project-management) is a card holding its three slots as inset, paper-coloured rows: the places a tie can land.
- **The contributors** sit on the left. Each is level with the slot it fills alone, so those two ties run dead straight.
- **The shared middle slot** takes one tie from each contributor. Each tie branches at a dot and turns once.
- All ties are orthogonal, end in an arrowhead on the slot's edge, and never cross (Ware; Tufte).

**The terminal.**
- The terminal is cut to the one slot whose two ties the diagram shows meeting: `pkit::work-tracking:fixers`, bound to software-analysis and to living-docs.
- So the evidence matches the picture line for line.

**Grid.**
- The diagram and the terminal take eight columns.
- The ✓ list and the limit take four.
- Within the diagram, the contributors take three columns and the provider four, with one column for the ties.

**Hierarchy.**
- The provider is the largest shape.
- The ties, in pkit's violet, are the strongest lines on the page.
- The role chips name what the lead names.
- The ✓ list is at 24 px, and the limit is at 20 px in ink-soft, level with the terminal.

**Type.**
- Capability names are 24 semibold in orange's strong tone.
- Roles are monospace chips, because they are the identifiers a developer types and reads in `pkit status`.
- Slot texts are 20 px in ink.

**Colour.**
- **Orange** cards are capabilities.
- **Violet** is pkit's wiring: role chips and ties. The content gives the ties the concept `pkit/core`, so the roles are pkit's vocabulary, not any capability's.
- The terminal repeats both: the slot in violet, the capabilities in orange. So the two halves of the page are visibly the same facts.

**Space.**
- The slots are 10 apart, and the ties land at the middle slot 7 above and 7 below its centre, so the two arrowheads do not touch.
- The terminal sits 26 below the diagram.
- The ✓ items are 24 apart.

**Known weaknesses.**
- The geometry that makes the ties straight leaves the left columns empty above living-docs (y 216 to 282).
- The right column has a gap between the list and the limit.

**Rejected alternatives.**
- **The content's two panels side by side, network beside the full terminal:** a 12-line terminal at 18 px needs eight columns and crowds the diagram into four.
- **Free ties from each contributor to each slot:** they converge at angles and cross.
- **The full `pkit status` output:** the role summary and the "data v1" line do not carry the point, and at full length the terminal outweighs the diagram.
- **A legend for orange and violet:** the names and the chips label themselves, and a legend is a detour (Mayer: coherence).

**Words changed.**
- **"plays pkit::work-tracking" became the chip "pkit::work-tracking",** so every role is drawn the same way. The lead's "only a role" carries the verb.
- **The contributors' descriptions dropped** ("docs for each reader", "what the software must do"). The role chip says what each contributor is, and the point is the wiring, not their purpose.
- **The terminal is cut** to `$ pkit status`, the slot line and its two `bound` lines. The roles summary, the points count and the "data v1" line are gone. The excerpt keeps the output's own indentation, which shows where it starts.
- **The panel head "What pkit status shows" dropped:** the `$ pkit status` prompt says it, and the head cost a line the geometry did not have.
