# Gaps: what the engine and libraries would need to draw these pages (round 7)

Each item names its owner: the foundations, the neutral brand, the starter library, the `pkit` notation, or the engine. Round 5's marks against round 4 (*new*, *changed*, *withdrawn*) stay as they were. What round 6 adds or changes is marked **Round 6** in the item, and items 54 to 56 are new in round 6. Round 7, a narrow fix of page 4 and one Czech line, is marked **Round 7**. Unmarked items stand as round 4 had them. Records that bound a change are named where they apply. Each change to a shipped library declares a changeset for the capability (DEC-013 point 4, PRJ-002).

## Foundations: roles every brand fills

1. *Changed.* **An ordered ramp, outside the accent:** `order.1`–`5`, one set per mode.
   - Each step holds 3:1 or more against the paper, and 4.5:1 against one text tone shared by all five steps (5.06 at the lightest step here).
   - Round 5 adds a contract: the ramp must not be the accent's hue. Order and proof never share a colour.
   - A brand fills the ramp from its neutral family, as neutral does (item 12), or from a second hue it keeps for order alone.
2. *Changed.* **A proof role, in place of round 4's focus:** `proof.ink` and `proof.tint`.
   - It means one thing on every page: what proves the title's claim. The page names that thing; the role says only what it looks like.
   - `proof.ink` holds 4.5:1 on the paper, on the tint, on the code fill and on the surface.
   - The tint is never the only cue: it always holds a word in `proof.ink`, or carries an outline in it.
   - It is never weight.
   - **Round 6:** a region of `proof.tint` always carries a 2 px rule in `proof.ink` on its left edge, its left corners square, so the region holds 3:1 where the tint alone (1.02:1 on a group, 1.13:1 on paper) washes out. The role therefore also promises `proof.ink` at 3:1 as a line on the surface and the paper.
3. *Changed.* **Type roles, with an emphasis contract.** Title 48/56; lead 30/38; head 24/32 semibold; body 24/32; small 20/28 (furniture); code 22/28.
   - Under the lead, the head is the only bold level, and it is never set in `proof.ink`.
4. **A spacing scale:** 4, 8, 12, 16, 24, 32, 48, 64.
5. **A tertiary text tone:** `text-muted`, for prompts, comments and the source line. It holds 4.5:1 on the code fill too.
6. *Changed.* **One line role at 3:1:** `border-strong` is now the one line tone.
   - It draws a slot's outline, the dashed outline, a note's rule, tree guides and ties.
   - It holds 3:1 on the paper and on the surface.
   - Round 4's separate relation role is merged into it (item 9).
7. *Withdrawn from these pages.* **The keyline role** (`border-subtle`). The deck draws no divider, because a frame is a fill and a note has its own rule. The foundations may keep the role for other media; nothing here needs it.
8. *Withdrawn* (round 4). The tag fill role.
9. *Withdrawn.* **A separate relation role.** Ties take the line role (item 6), because a second grey line tone differed from the first for no meaning (round 4 finding, page 4).
10. **Radius and stroke tokens:** radius 8; one stroke, 2 px, for every line; arrow-head 12.
    - **Round 6:** a `bend` token, 16, the one radius on which every connector turns every corner, outer and inner alike. It is separate from the box radius, because a line's turn and a box's corner do different work. The smallest drop a deck's connectors make sets it (`ledger.md` L17).
11. *Changed.* **A code role:** `surface-code`, a terminal's fill. It is cooler than a group's surface and a step deeper. In dark mode it is lighter than the paper. A terminal takes no line.
    - **Round 6:** the surfaces are a ramp of equal steps. `surface-code` stands as far off `surface-group` as the group stands off the paper (about 1.1:1 each, in both modes). A brand fills both from one ramp, so a terminal beside a group never differs by hue alone.
12. *New.* **A group role:** `surface-group`, a frame's fill, with no line. It is distinct from `surface-code` by hue and lightness, so a group is never read as a terminal.
13. *New.* **A colour table every brand fills.** Neutral, order and proof, each with its one meaning, its second cue and where it may appear: order only as a block's fill; proof only as a line, a word or a tint region (`design-system.md` section 4).

## Neutral brand: the values it ships

14. *Changed.* **The ink ramp:** OKLCH lightness .28 → .54 in light and .90 → .64 in dark, chroma .032, hue 255. White text on all five light steps, paper text on all five dark steps.
15. *Changed.* **The proof pair:**
    - light: ink `#047554`, tint `#dcf8ea`;
    - dark: ink `#82d9b4`, tint `#113124`.
16. *Withdrawn.* **The green ramp** (round 4's order). Green now has one form, proof.
17. **Tonal scales** in OKLCH, one lightness per step across hues; **a designed dark mode**; **font naming** for the semibold; **no new font**.
18. Neutral declares `open: []`. None of the above opens a role to a brand built on neutral. Making any of them overridable is a change to neutral's contract (COR-014; DEC-001 point 9) and the maintainer's call.
19. *New, open.* **The group tint for projection.** At 1.10:1, a frame's surface may wash out on a weak projector.
    - Nothing a reader needs rests on it (WCAG 1.4.11): the frame's content and the space around it group it.
    - A brand that projects often may want a deeper surface, at about 1.2:1. That stays inside the role.

## Foundations, `deck`: the slide frame

20. *Changed.* **A slide grid, checked:** 12 × 64, gutters 32, side margins 80. Column *i* starts at 80 + 96*i*.
    - Every box edge, and every free line of text, sits on a column edge. A line set flush left starts on a column's start; a line set flush right ends on a column's end.
    - One right margin, at 1200.
    - The frame stands as round 4 set it: title cap on 64, lead baselines 140 and 178, field 224–608, source baseline 656.
21. *New.* **Declared edges.** A page may name an edge off the grid, with its reason, only where its own geometry makes it (page 1's half-module steps). The check prints each one. **Round 6:** page 3 declares one more, its proof region's left edge, 16 before the outcome column's text.
22. **A lead set as given lines,** broken by sense, measured against the frame.
23. **One source line role:** "In project-kit: …", 20 px muted, one line, no code runs.

## Starter library: patterns and their options

Each is a DEC-007 decision for the starter's owner. One job per pattern (point 2) decides between an option and a new pattern. The entry bar (point 3) asks for reference renders of each option, one in a text-heavy language. The README's boundaries table changes with it.

24. *New.* **Five containers, one look each.** It replaces round 4's "container with compartments" (item 38).

    | Container | Look | Meaning |
    |---|---|---|
    | Block | an order fill with on-order text; no line | a thing |
    | Frame | `surface-group`; no line; named by a head or by a block at its corner | a group |
    | Slot | the paper inside a 2 px line at 3:1, in a frame's tray 12 in; its text 24 in, as in any box that holds text (**Round 7**) | an opening |
    | Terminal | see item 31 | |
    | Note | a 2 px rule, its text 16 right of it, a head | a qualification |

    An undecided block is the block's shape with a dashed line.
25. *Changed.* **`layers` stepped.** Centred levels, each 48 wider on each side than the one above, so a five-level stack spans columns 2–9 with two levels on declared half-module edges. They are shaded from the order ramp by place.
26. *Changed.* **`layers` stepped relations.**
    - Up to two relations walk the steps 24 outside the stepped edge, down the middle of each 48 tread. **Round 6:** every corner, outer and inner, turns on the `bend` token (item 10), in place of concentric arcs of 32 on outer corners and sharp inner ones. The offset is held beside each face, and no turn comes closer.
    - **Round 6:** a tie into the first level from beside it stands 32 or more from a relation that leaves the same face.
    - Each leaves the first level 16 above its foot, clear of the radius.
    - Their labels sit beside the middle riser, 24 from the line on each side, centred on it.
    - Round 4's labels at the foot are withdrawn.
27. *Changed.* **An outcome cell:** the outcome's word, then its scope under it in the soft tone. No mark. The word takes `proof.ink` when the outcome is the page's proof, never weight. **Round 6:** when it is the proof, the outcome column also lies on a proof region (item 2), 16 around its text, so the evidence leads by area rather than by weight.
28. *Changed.* **A flow-headed table:**
    - stage names at the head level, over one spine in one colour, with a head at each hand-over and none at the margin, where the outcome region ends (round 6);
    - rows on two shared baselines, every cell on its column's start;
    - one face per line in a cell.

    Round 4's rules from a ramp are withdrawn.
29. *Changed.* **A caveat under a table** is the note container (item 24), 48 or more under the last row and more than the row gap (checked). Round 4's divider is withdrawn.
30. *Changed.* **A numbered step:** an ink disc of 36 with its number in paper, and the step's name hung beside it. Its terminal sits 12 under the disc. Steps sit 32 apart.
31. *Changed, reversed.* **The terminal component:**
    - the code fill on a column span (round 4 sized panels to content);
    - text 24 in, the first baseline 32 down and the last 20 up, lines 28 apart;
    - prompt and comments muted, command in ink, arguments soft;
    - an optional comment flush right on line 1;
    - a command is never broken;
    - real output is cut by whole lines and dedented together;
    - **Round 6:** line 1 is always the command, with a `$` prompt; output follows flush with the prompt. A comment may name what a cut keeps, and a word in it may take its role from elsewhere on the page (`proof.ink`).
    - **Round 7, open:** page 4's terminal opens on its output, because the field holds three lines there (`ledger.md` L18, L19). If the maintainer keeps that, the component needs a stated case for an output-only terminal; if not, page 4 needs a re-layout.
32. *Changed.* **A proof word in a terminal:** the word takes `proof.ink`. Round 4's tinted bands across output lines are withdrawn: the word ties the output to the drawing by itself.
33. *Changed.* **A tree in tree notation:**
    - a frame with a head;
    - names in mono;
    - guides drawn as 2 px lines in the line tone, the last ending on the deck's radius;
    - proof rows on a line-highlight band the height of the line pitch;
    - one tag per entry, **round 6:** set flush right on the frame's text edge;
    - **Round 6:** a key on the root's line, flush right on the tags' edge, that gives each owner its verb ("pkit's: replaced · yours: kept"), each owner in its tag's colour;
    - **Round 6:** proof rows carry the region rule (item 2);
    - never drawn under a prompt.
34. *Changed.* **`connector` attachment rules.**
    - A connector meets a face at its middle, or at one fixed offset clear of the corner radius.
    - A second connector to a shared target branches off the first and turns twice on the `bend` token (16; round 6: one radius for every turn of every connector).
    - It keeps 16 from any shape and 12 from any text, and no two connectors cross.
35. **Inline code at the code size** (22 inside 24 px text), at most once in a list, where the command is the subject.
36. *New.* **A frame with a tray of slots:** slots 12 in from the frame and 8 apart. The opener's block sits at the frame's bottom-left, its label on the block's second baseline. **Round 6:** the block takes the tray's inset too, 12 from the frame's left and foot, so everything a frame holds shares one inner left edge. **Round 7:** slots are 44 tall and hold their text 24 in, so the frame has one text edge too; the block is a slot's height plus its tray above and below (68).
37. *Withdrawn* (round 4, item 26). Lines in focus in `code`, as tinted bands.
38. *Withdrawn* (round 4, item 30). A container with compartments: a slot is now a slot in a frame (item 24).

## The `pkit` notation

39. *Changed.* **What is proof, per page.**
    - The notation names which of pkit's things take the brand's proof form on each page: the "carried out" relation, pkit's files where ownership is the point, the stages and the refusal, and the slot filled by two together with its status line. **Round 6:** the refusal as a region over its column, and the slot's name in the status comment. **Round 7:** the slot's name back in the status output, its first line.
    - Yours take ink.
    - The notation has no hue of its own.
40. *Changed.* **The layers as the neutral ramp,** by place, naming no concept, since each lower layer holds pkit's and yours (DEC-001 point 6). Changing DEC-001 itself is the maintainer's call.
41. *Changed.* **A capability in its role, as one block for every capability:**
    - line 1 is "role" (small) and the role id (mono);
    - line 2 is the capability's name;
    - one fill, so a tie attaches at a face's middle with no seam behind it;
    - ramp step 1 for all, since capabilities have no rank;
    - **Round 7:** as tall as the slot it fills plus the frame's tray above and below (68 for a 44 slot), so a filler centred on its slot is flush with the frame's top.
42. *Changed.* **A slot as a slot in its opener's frame:** its real id in mono, its purpose in the soft tone, and a tie landing on its edge.
43. **Second cues for ownership:** the owner's word beside the entry, and position, rather than marks.
44. *New.* **The opener at the base of its frame,** under the slots it opens, with "opens N slots" beside it. **Round 6:** the status terminal sits 8 under the frame, opening on `$ pkit status`, its comment naming the slot. **Round 7:** it sits 16 under the frame, more than any space inside it, and opens on the slot's line, with its two `bound` lines under it.

## Engine: typesetting and measurement

45. **Czech binding:** one-letter words bound to the next; "ve" kept with its noun. **Round 7:** a preposition stays with the phrase it opens at a hand-set break too ("hook, / před každým voláním"). The binding could cover the short prepositions (před, nad, pod, přes, za, na, do, od) as it covers one-letter words.
46. **No lone last word** in a wrapped block.
47. **Glyph fallback by run:** split a run at any glyph its font lacks.
48. **Measured text in patterns:** size boxes from the shipped fonts' advance widths.
49. **Arrowheads that meet their target:** the line stops at the head's base.
50. **No-break space in commands** (`rm -r`, `git push -f`).
51. **Elbows on arcs with a set radius per corner,** 0 for a sharp one, drawn as true arcs. **Round 6:** the deck now uses one radius, the `bend` token, and a check fails any other. The engine keeps a per-corner radius, but no pattern here needs it.
52. *New.* **Held text:** text a container holds is placed and judged with that container, not with the page's grid.
53. *Changed.* **Craft checks on every render** (`tools/svg.py`, `check`).
    - *Added in round 5:*
      - the grid check: box edges, and free text on column starts or ends, with declared edges printed;
      - the one-bold-level check: bold only at 24, never in `proof.ink`;
      - an accent listing per page.
    - *Kept from round 4:* wire clearance (16 to shapes, 12 to text), wire ends on edges and clear of the radius, follow offset ±0.6, no crossings, one stroke weight, 3:1 for every meaningful line and block fill, no line on a terminal or frame, text 12 from its holder's sides, left edges per named column, and the margins.
    - *Withdrawn:* the 12 px highlight clearance. A line highlight is the height of the line pitch, as in a code editor.
    - *Added in round 6:*
      - the one-bend check: every turn of every line, ties, relations and guides, on the `bend` token;
      - the follow check judges the offset beside each face (±0.6), and at a turn only that the line comes no closer.
    - All 16 renders pass with no fault.
54. *Round 6, new.* **Comment runs in a terminal:** a comment is a run list, not one string, so one word may take another role. Its width counts against line 1's room.
55. *Round 6, new.* **A proof region as a mark:** a tint rectangle with its rule, square on the rule's side, that the checks treat as neither a container nor a box on the grid. Its edge is declared where it is off the grid.
56. *Round 6, new.* **A key line in a listing:** runs of tag-coloured owners and soft verbs, set flush right on the tags' edge on the root's line, measured so that it never crowds the root.
