# Ledger: the design decisions rounds 5 to 7 settled, each with its reason

Each entry states one decision, then the reason for it, then where it applies. Once an entry is settled here, it holds on every page. A later round changes it here first and the pages follow. Values are in slide pixels (1280 × 720).

Round 6 is polish on round 5's passed system. It changed L6, L9, L11, L13, L15, L16, L17, L18, L19 and L22, and added L24 to L26. Each changed entry ends with a *Round 6* line that says what moved and why.

Round 7 is a narrow fix of page 4, and one Czech line on page 3. It changed L12, L13, L17, L18 and L19, and added L27. Each changed entry ends with a *Round 7* line.

## Foundations

**L1. A 12-column grid binds every page.** Columns are 64 px with 32 px gutters, and the side margins are 80. Column *i* starts at 80 + 96*i* and ends 64 later.
- *Reason:* round 4 had no right margin, and content ended anywhere from 1131 to 1200. A grid gives few edges and one shared right margin at 1200 (Müller-Brockmann). 64 + 32 is a multiple of the 8-point scale.
- *Where:* every box edge, and every free line of text, which starts on a column's start (or ends on a column's end when set flush right). The generator fails any edge off the grid.

**L2. A page may declare an edge of its own, by name and reason, and only from its own geometry.**
- *Reason:* a stepped stack of five levels with equal steps cannot put all ten edges on twelve columns. Steps of a whole module would make the base 1120 wide and leave no room for the labels.
- *Where:* page 1 only. Its second and fourth levels step out half a module (416/864 and 320/960). The other three levels sit on columns 4–7, 3–8 and 2–9. The check prints each declared edge with its reason.

**L3. One shared right margin at 1200.** Panels, frames, the spine and the terminal end on it. Ragged text ends inside it.
- *Reason:* round 4's deck finding.
- *Where:* pages 2, 3 and 4 reach 1200. Page 1 is symmetric about the page's axis, so its stack ends on column 9 and its right label ends where its words end.

**L4. The frame stays as round 4 set it.** Title baseline 96, lead baselines 140 and 178, field 224–608, source line at baseline 656.
- *Reason:* the round 4 critic named this as what holds.

## Emphasis

**L5. Under the title and lead there is one bold level: the 24 px head, semibold, never in the accent.**
- *Reason:* round 4's page 3 had four bold voices. Three degrees of emphasis is the ceiling: title and lead, the head level, and body. Weight and colour must not both shout (Refactoring UI: emphasise by de-emphasising).
- *Where:* the head names a thing: a level, a step, a row, a stage, a frame, a list, "Limit:". The generator fails bold at any other size, and bold in the accent.

**L6. One accent, green, with one meaning on every page: it marks what proves the title's claim.** It appears as a line or a word in proof ink, or as a region in proof tint, and never as weight. Each page uses it on one idea.
- *Reason:* round 4's green meant order on page 1, ownership on page 2, structure on page 3 and focus on page 4 (deck finding). An accent signals only if it keeps one job (Mayer's signalling, Albers).
- *Where:*
  - page 1: the "Carried out" relation;
  - page 2: pkit's entries, which upgrades replace;
  - page 3: the spine, and the outcome column: a region behind it and "Refused" in each row (L26);
  - page 4: the `fixers` slot and its name in the status output.
- *Round 6:* page 3's outcome column gained a region of proof tint, so the evidence leads under a squint. The region is the accent's own third form, so this entry did not change to allow it, and L5 still holds.

**L7. Order takes the ink ramp, not the accent.** The ramp is five steps of the ink's own slate, darkest at the source in light mode and lightest at the source in dark mode. Only blocks take it.
- *Reason:* once green means proof, it cannot also mean order. Lightness is the ordered variable (Bertin), and a ramp of one hue says "one chain".
- *Where:* page 1's levels. On page 4, which has no order, every block takes step 1, so equal fills claim no rank.

**L8. Everything that is neither order nor proof is neutral.** That covers paper, surface, code, ink, ink-soft, ink-muted and one line tone. No other hue appears in the deck.
- *Reason:* 60-30-10, with a calm base and one accent. A colour the content does not need is noise (Tufte).

## Containers

**L9. Five container kinds, one look each, distinct by their means rather than by shades of grey.**
- **Block:** a thing. A ramp fill with paper text.
- **Frame:** a group. A surface fill with no line, named by a head or a block at its corner.
- **Slot:** an opening that something fills. Paper inside a 2 px outline at 3:1.
- **Terminal:** a code fill (cooler, and one full surface step deeper than a frame, L24) with no line and mono text.
- **Note:** a qualification. A 2 px rule at its left, with the text 16 px right of it.
- *Not decided yet* is a block drawn as a dashed outline.
- *Reason:* round 4 had four container languages and outlined white boxes that read as a default flowchart. Each kind now differs in kind of mark: a solid fill, a quiet tint, an outline, a cool tint, a rule. Two kinds never differ only by a near-equal grey (Carbon tiles, Stripe's documentation diagrams).
- *Round 6:* a frame and a terminal stood side by side on page 2 at 1.05:1, by hue alone, and read as an accident. The terminal is now a full step deeper (L24).

**L10. Only an opening carries an outline.** Blocks, frames and terminals are fills.
- *Reason:* a boundary drawn as a line is the strongest claim a box makes. It belongs where the boundary means something: a slot is where a tie lands. Elsewhere, quiet tinted surfaces and spacing group things (task brief; Refactoring UI).

**L11. A meaningful boundary holds 3:1.** A slot's outline is 4.27:1, a block's fill is at least 5.06:1, and the dashed outline is 4.27:1. A frame's tint (1.10:1) and a terminal's tint (1.22:1) are not boundaries a reader needs: what is inside each, and the space around it, already group it. A proof region's tint is not one either; its rule is (L25).
- *Round 6:* the terminal's tint moved from 1.16:1 to 1.22:1 (L24).
- *Reason:* WCAG 1.4.11 asks for 3:1 where a graphic is needed to understand the content.

**L12. A capability in its role is one block, the same for all three capabilities: columns 0–3 (352 × 68).**
- The first line is the role: the label "role" in 20 px, then the role id in mono.
- The second line is the capability's name.
- *Reason:* round 4 drew the same thing two ways, and nothing on the left said which line was the role (page 4 finding, Nielsen's consistency). One fill with two lines lets a tie attach at the middle of the block's face with no seam behind it. A two-colour box would put its seam exactly where the tie leaves.
- *Round 7:* the block is as tall as a slot and the tray above and below it (2 × 12 + 44 = 68), so it follows the slot from 48 to 44 (L13). That keeps each filler centred on its slot and flush with the frame's top or the opener's top. The two lines keep their 28 px pitch, centred: their baselines are 28 and 56, where they were 30 and 58.

**L13. The opener's block is the base of its frame, and the frame holds it as it holds the slots: 12 px in from its left and its foot.** It sits at the frame's bottom-left, under the slots it opens, with "opens 3 slots" on its second line's baseline. Its top is on the lower filler's foot (396), 12 under the last slot.
- *Reason:* with the block at the foot, both fillers sit level with the slot that only they fill. Their ties then run straight, the top filler is flush with the frame's top, and the bottom filler is flush with the slots' foot. With the block at the head, the left column would start 72 px low under a hole.
- *Where:* page 4. The status terminal sits 16 px under the frame, more than any space inside it (the tray's 12, the slots' 8).
- *Round 6:* round 5 set the block flush on the frame's left and bottom edges while the slots sat 12 in, so the frame showed two left edges 12 px apart (560 and 572). That near miss read as an error. Now everything inside the frame starts at 572. The block's top falls on the lower filler's foot, so the two blocks of the same fill share one horizontal line. The 12 px this added to the frame came out of the gap to the terminal (16 to 8).
- *Round 7:* at 8 px the terminal stood closer to the frame than the frame's own tray (12), so by proximity it read as one more row of the group, and in dark mode the two panels read as one block split by a hairline. The page also ended at 608, below the other pages' floor (599 to 606). Each slot is now 44 tall, not 48, and each block 68, not 72 (L12). The frame ends at 476, not 492. The terminal sits 16 under it and ends at 600, and the page code asserts both: the gap larger than any space inside the frame, and the foot on 600.

**L27. One inner padding for every box that holds text: 24 from its side to its text.** A block, a slot and a terminal all hold their text 24 in. Where boxes nest, the edges follow the nesting: on page 4 the frame is at 560, the slots and the opener's block 12 inside it at 572, and their text at 596, one text edge for the whole frame. The terminal under the frame starts at 560, so its text is at 584.
- *Reason:* round 6 set a slot's text 12 in and a block's 24 in. The two boxes lined up at 572, but their text jogged by 12 px, 584 against 596, inside one group (page 4 finding). One padding gives the group one text edge (Müller-Brockmann: few alignment edges), and equal padding is the brief's craft rule.
- *Where the text edges differ:* the terminal is not inside the frame. It is the frame's report, set 16 below it, on the same box edge (560) and the same 24 padding. Its text therefore sits 12 left of the frame's, by the frame's tray. Moving it to 596 would take either a 36 px padding on one side of one terminal or a terminal off the grid and short of the margin (L1, L3).
- *Round 7:* new.

## Lines and relations

**L14. One stroke weight (2 px) and one line tone for every neutral line:** outlines, dashes, rules, tree guides and ties.
- *Reason:* round 4's outlines and connectors differed in colour and weight for no meaning (page 4 finding).
- *Where:* proof lines take proof ink at the same weight.

**L15. A tie attaches to the middle of a face, or at one fixed offset clear of the corner.** Its tip lands on the target's edge. It passes 16 px or more from any shape, 12 px or more from any text, and crosses nothing.
- *Reason:* round 4's arrows jammed into corners (page 1 finding). These are Ware's rules for reading lines as relations.
- *Where:* page 1's relations meet Decisions 16 px above its bottom edge on both sides. The ideas tie meets its left face at the height of the head's middle line (245), 33 px above the relation that leaves the same face.
- *Round 6:* the ideas tie met the face at its middle (259), only 19 px above the green relation (277). For 60 px the two lines ran parallel, the tightest spot on the page. The tie now leaves "Where ideas start" and enters "Decisions" on one line, level with both heads. Lines that share a face stand at least 32 px apart, and the generator asserts it.

**L16. A relation that follows a shape keeps one distance from each face it runs beside.** On page 1 that is 24 px, down the middle of each 48 px tread. At its turns the line takes the deck's one bend (L17), like every other line.
- *Reason:* "parallel" means one distance (round 3 finding, kept). Measured at 24.00 px beside the faces, over 138 points on each relation, in every render. At the turns the line stands up to 30.6 px off the step's corner. The generator fails any turn that comes closer than 24.
- *Round 6:* round 5 turned outer corners on concentric arcs of 32 and left inner corners sharp. The line was geometrically true to the outline, but a reader saw one connector drawn with two corner styles. A line now turns every corner alike. It gives up exact concentricity at the outer turns, which no reader measures, for one drawn stroke, which every reader sees.

**L17. One connector spec for the deck.** The stroke is 2 px. Every line that turns, whether a tie, a relation that follows a shape or a tree's guide, turns every corner on one radius, 16 px, outer and inner corners alike. Where direction matters, the line ends in the 12 px filled head. A second tie to a shared slot branches off the straight tie and turns twice. The generator fails any bend that is not 16.
- *Reason:* round 5 had two bend radii, about 31 on page 1 and 14 on page 4, and page 1 mixed sharp and round corners. Together these were the last sign that two hands drew the deck (deck finding).
- *Why 16:* the tightest turns in the deck set the radius. Page 4's drop to the shared slot is 44 px (46 in round 6), so two turns of 16 leave a straight run of 12. Two of 24 would overrun it. Page 1's treads are 48, so two turns of 16 leave a straight run of 16. Page 2's tree guide turns once into its last entry, on the same 16. On 16 px a turn reads as a turn and not as a curve, at the deck's 2 px stroke.
- *Where:* page 1's three lines, page 2's tree guide and page 4's branched ties. Straight lines, such as page 3's spine and page 4's direct ties, have no bend.
- *Round 6:* new as one spec. It replaces round 5's "a tie that turns uses a 16 px bend", which held for page 4 only, and page 1's arcs of 32 with sharp inner corners.
- *Round 7:* the two ties into the shared `fixers` slot land 8 px either side of its middle, not 10, because the slot is 4 px shorter. Each tip stays 14 px from the slot's top or bottom edge, the corner clearance the check asks for (L15). The two heads stand 16 apart, with 5 px of slot between them.

## Code

**L18. One terminal component, and it shows its command first.** Round 7 leaves one exception open, page 4 (below).
- A code fill with no line, at column widths.
- Text sits 24 px in from the sides. The first baseline is 32 px down, the last 20 px up, and lines are 28 apart.
- Line 1 is a command: a `$` prompt, muted, then the command in ink and its arguments soft. Output follows below it, flush with the prompt.
- A comment, muted, may end line 1 flush right. It says what a cut of the output keeps, and a word of it may take the role that word has elsewhere on the page.
- *Reason:* round 4's panels looked like a default Markdown block and took content widths (page 2 finding). A terminal now has a defined fill, padding, width and palette, which keeps it distinct from a frame.
- *Round 6:* page 4's terminal opened on output, with the command as a trailing comment, while page 2's opened on `$`. One component followed two conventions (deck finding). Now every terminal opens on its command.
- *Round 7, open for the maintainer:* page 4's terminal opens on its output, the slot's own line, and has no command line. The field has room for three lines under the frame there, and the proof needs all three (L19). Page 2's terminals, whose job is a command to run, still open on `$`. Everything else in the component is unchanged: fill, padding, type and tones. This is the one finding in round 7 that a fix could not meet in full, and the trade is set out in L19.

**L19. Each command stays on one line, and real output is cut by whole lines and dedented together.** On page 4 the terminal reads `pkit::work-tracking:fixers`, the slot's own line as `pkit status` prints it, with `fixers` in proof ink as on the slot. Under it come the slot's two `bound` lines, set 2 in so that the slot heads them. The cut drops the line `pkit status` prints between them (the point's kind, version and provider) and every other point.
- *Reason:* a copied command must run. Output cropped to what proves the point (round 4 page 4 finding).
- *Round 6:* the slot's own line moved into the comment. A terminal with the command and all three output lines is 136 px tall. The frame above it is 268, so the two would need 404 px plus a gap, and the field is 384. Its first line, the command and the comment, is 574 px of mono, so with its padding the terminal needs 7 columns. It cannot sit beside the frame or in the left column, which has 5. The two `bound` lines are the proof that two capabilities fill one slot. The comment keeps the slot's name, so no fact was lost.
- *Round 7:* the round 6 critic read the comment as the author's caption, not as something pkit printed, so the proof read as a note and the two `bound` lines lost their heading. The slot's line is output again, the first line, and the `bound` lines hang under it.
  - *Why the command line went:* four lines (the command, the slot, two `bound` lines) are 136 px. The frame cannot be shorter than 252 without cramping it: a slot needs 44 to take two arrowheads 14 from its edges, and a block 68 to hold two lines. 224 + 252 + 16 + 136 = 628, which runs 28 below the floor, to 14 px above the source line's capitals. Three lines (108) end on 600.
  - *Weighed and rendered* (`tools/review/r7-alt-command-line-ends-628.png`, `tools/review/r7-alt-command-line-cramped.png`): the four lines under the 252 frame, which crowds the source line, and the four lines under a frame squeezed to 224 (tray 8, slots 4 apart, blocks 60), which puts the blocks' descenders 3 px from their edge. Keeping the command and cutting one `bound` line would show one filler where the drawing shows two. Keeping the command with the slot in a comment is round 6, the caption this round removes.
  - *What would keep the command:* 28 px more for page 4's right column, which only a re-layout of the page can give. Round 7 was asked for a narrow fix, so it leaves that choice to the maintainer.

**L20. In a cell or a sentence, each line is one face.** Code lines are all mono, and prose lines are all sans.
- *Reason:* round 4's page 3 mixed the two faces in one line and read lumpy.
- *Exception:* one inline command in a benefit ("`pkit validate` checks the wiring"), where the command is the subject.

## Words

**L21. Relation labels are worded the way their lines read.**
- "Carried out / by each layer below" goes with the downward line.
- "Checked first / against the one above" goes with the upward line, so the two read as a pair.
- *Reason:* round 4's "the layer is checked first" beside an upward arrow could read as "go change the decision" (page 1 finding).

**L22. Tags are the lead's own words, and a key says what each owner means for an upgrade.** On page 2 the tags are "pkit's" and "yours" ("pkitu" and "vaše" in Czech). The key, "pkit's: replaced · yours: kept" ("pkitu: nahradí se · vaše: zůstanou"), stands on the root's line, flush right on the tags' own edge (1176), each owner in its tag's colour.
- *Reason:* the lead says "Upgrades replace pkit's files, never yours". The tree answers in the same words, at each entry (Mayer's spatial contiguity). The key carries the verb, so the listing proves the lead's second sentence instead of leaving the reader to connect it (Alley: the visual proves the assertion).
- *Why there is one tag per entry rather than one label per category:* the two owners alternate inside each folder, so no single bracket can hold either category.
- *Why the key sits on the root's line:* the root's line becomes the listing's header row. The root heads the tree column and the key heads the tag column. A key in a line of its own under the frame's head was also tried. It cost the tree its 32 px pitch (28) and the bands their height, and it put the key 400 px left of the tags it explains.
- *Round 6:* the key is new, and the tags moved from column 10's start to flush right, so they and the key share one edge.

**L23. Page 3's scopes are parallel prepositional phrases, set in the soft tone under "Refused":** "in every mode", "for any other tool" and "for raw GitHub changes".
- *Reason:* round 4's qualifiers were three different grammatical kinds, and they were the loudest text on the page.

## Surfaces and proof

**L24. The surfaces are one ramp of equal steps: paper, then a frame, then a terminal.** In light mode a frame is 1.10:1 on paper and a terminal 1.22:1, which puts a terminal 1.11:1 off a frame, as far as a frame is off the paper. Dark mode is designed the same way, lighter for higher: 1.11 and 1.23 on paper, 1.11 between them. The terminal keeps its cooler hue (248).
- *Reason:* round 5's terminal stood 1.05:1 against a frame, by hue alone. Side by side on page 2, two near-equal greys read as an accident rather than as "command" against "result" (page 2 finding). A full step makes the difference intended, and the two still read as one family.
- *Where:* page 2, where a terminal and a frame stand side by side, and page 4, where the status terminal stands under the frame. All text on the deeper code fill still passes: muted 4.87:1 and proof ink 4.66:1 in light mode.

**L25. A region of proof tint carries a 2 px rule of proof ink on its left edge, and its left corners are square.**
- *Reason:* the proof tint is 1.02:1 on a frame and 1.13:1 on paper. A projector washes either out (page 2 finding). The rule holds 5.19:1 on a frame and 5.71:1 on paper, so the region keeps its mark, with no deeper tint and no new colour. It is the gutter mark a code editor sets beside a changed line.
- *Where:* page 2's bands on pkit's entries, and page 3's outcome region. Page 4's `fixers` slot is a slot, so its whole outline is already in proof ink (L10).

**L26. The page's evidence leads by area and colour, never by weight.** On page 3 a region of proof tint lies behind the outcome column's rows. It runs from 16 px before the column's text (928, a declared edge) to the margin, and from 16 above the first row's cap height to 16 below the last row's descender. "Refused" stays in regular weight and proof ink. The spine's last segment ends at 1200, the region's right edge.
- *Reason:* under a squint the bold row heads were the darkest mass, and the outcome, the evidence for "they hold when an agent forgets them", was the quietest thing on the page (page 3 finding). The verdict offered two fixes: semibold "Refused", or a pale band.
- *Why not semibold:* semibold "Refused" is bold in the accent, which L5 forbids. Weight and colour would both shout, and the page would carry four bold uses (stages, row heads, "Limit:", the outcome) where round 5 cut four voices to one. The row heads are already the one bold level, so there is no lower bold to bring them down to.
- *Why the region:* the region is the accent's own third form (L6), so no rule changes. It adds area, the strongest cue under a squint, without adding a voice. It also turns the column into one unit that the spine leads into.
- *The spine's end:* it ends on the region's right edge, which is the margin, and not at the column's text width (about 1170). The region gives that edge a meaning, so the line is tied to its column. The text ends at 1179 in English and 1181 in Czech, so ending at the text would give a different end in each language.
