# Ledger: the design decisions round 5 settled, each with its reason

Each entry states one decision, then the reason for it, then where it applies. Once an entry is settled here, it holds on every page. A later round changes it here first and the pages follow. Values are in slide pixels (1280 × 720).

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
  - page 3: the spine and "Refused";
  - page 4: the `fixers` slot and its name in the status output.

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
- **Terminal:** a code fill (cooler and a step deeper than a surface) with no line and mono text.
- **Note:** a qualification. A 2 px rule at its left, with the text 16 px right of it.
- *Not decided yet* is a block drawn as a dashed outline.
- *Reason:* round 4 had four container languages and outlined white boxes that read as a default flowchart. Each kind now differs in kind of mark: a solid fill, a quiet tint, an outline, a cool tint, a rule. Two kinds never differ only by a near-equal grey (Carbon tiles, Stripe's documentation diagrams).

**L10. Only an opening carries an outline.** Blocks, frames and terminals are fills.
- *Reason:* a boundary drawn as a line is the strongest claim a box makes. It belongs where the boundary means something: a slot is where a tie lands. Elsewhere, quiet tinted surfaces and spacing group things (task brief; Refactoring UI).

**L11. A meaningful boundary holds 3:1.** A slot's outline is 4.27:1, a block's fill is at least 5.06:1, and the dashed outline is 4.27:1. A frame's tint (1.10:1) and a terminal's tint (1.16:1) are not boundaries a reader needs: what is inside each, and the space around it, already group it.
- *Reason:* WCAG 1.4.11 asks for 3:1 where a graphic is needed to understand the content.

**L12. A capability in its role is one block, the same for all three capabilities: columns 0–3 (352 × 72).**
- The first line is the role: the label "role" in 20 px, then the role id in mono.
- The second line is the capability's name.
- *Reason:* round 4 drew the same thing two ways, and nothing on the left said which line was the role (page 4 finding, Nielsen's consistency). One fill with two lines lets a tie attach at the middle of the block's face with no seam behind it. A two-colour box would put its seam exactly where the tie leaves.

**L13. The opener's block is the base of its frame.** It sits at the frame's bottom-left corner, under the slots it opens, with "opens 3 slots" on its second line's baseline.
- *Reason:* with the block at the foot, both fillers sit level with the slot that only they fill. Their ties then run straight, the top filler is flush with the frame's top, and the bottom filler is flush with the slots' foot. With the block at the head, the left column would start 72 px low under a hole.
- *Where:* page 4. The status line `pkit::work-tracking:fixers` sits right under the block that names that role.

## Lines and relations

**L14. One stroke weight (2 px) and one line tone for every neutral line:** outlines, dashes, rules, tree guides and ties.
- *Reason:* round 4's outlines and connectors differed in colour and weight for no meaning (page 4 finding).
- *Where:* proof lines take proof ink at the same weight.

**L15. A tie attaches to the middle of a face, or at one fixed offset clear of the corner.** Its tip lands on the target's edge. It passes 16 px or more from any shape, 12 px or more from any text, and crosses nothing.
- *Reason:* round 4's arrows jammed into corners (page 1 finding). These are Ware's rules for reading lines as relations.
- *Where:* page 1's relations meet Decisions 16 px above its bottom edge on both sides.

**L16. A relation that follows a shape keeps one distance from it.** On page 1 that is 24 px, down the middle of each 48 px tread. Outer corners turn on concentric arcs of 32 (8 + 24), and inner corners are sharp.
- *Reason:* "parallel" means one distance (round 3 finding, kept). Measured at 24.00 px over 252 points, both relations, every render.

**L17. A tie that turns uses a 16 px bend.** A second tie to a shared slot branches off the straight tie and turns twice.
- *Reason:* page 4's channel is 140 px, and the drop to the shared slot is 46. Two 16 px turns leave a straight run between them, which a 32 px turn (page 1's) would not. Page 1's arcs are a level's radius plus the rail's offset, a different geometry.

## Code

**L18. One terminal component.**
- A code fill with no line, at column widths.
- Text sits 24 px in from the sides. The first baseline is 32 px down, the last 20 px up, and lines are 28 apart.
- The prompt is muted, the command in ink, and arguments soft.
- A comment, muted, may end line 1 flush right.
- *Reason:* round 4's panels looked like a default Markdown block and took content widths (page 2 finding). A terminal now has a defined fill, padding, width and palette, which keeps it distinct from a frame.

**L19. Each command stays on one line, and real output is cut by whole lines and dedented together.** On page 4 the cut keeps the slot line and its two `bound` lines. The source command is a muted comment, `# pkit status`.
- *Reason:* a copied command must run. Output cropped to what proves the point (round 4 page 4 finding).

**L20. In a cell or a sentence, each line is one face.** Code lines are all mono, and prose lines are all sans.
- *Reason:* round 4's page 3 mixed the two faces in one line and read lumpy.
- *Exception:* one inline command in a benefit ("`pkit validate` checks the wiring"), where the command is the subject.

## Words

**L21. Relation labels are worded the way their lines read.**
- "Carried out / by each layer below" goes with the downward line.
- "Checked first / against the one above" goes with the upward line, so the two read as a pair.
- *Reason:* round 4's "the layer is checked first" beside an upward arrow could read as "go change the decision" (page 1 finding).

**L22. Tags are the lead's own words.** On page 2 the tags are "pkit's" and "yours" ("pkitu" and "vaše" in Czech).
- *Reason:* the lead says "Upgrades replace pkit's files, never yours". The tree answers in the same words, at each entry (Mayer's spatial contiguity).
- *Why there is one tag per entry rather than one label per category:* the two owners alternate inside each folder, so no single bracket can hold either category.

**L23. Page 3's scopes are parallel prepositional phrases, set in the soft tone under "Refused":** "in every mode", "for any other tool" and "for raw GitHub changes".
- *Reason:* round 4's qualifiers were three different grammatical kinds, and they were the loudest text on the page.
